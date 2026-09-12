# Copyright (c) 2026 Raymond Manaloto
"""Machine-readable verdict for ``claude doctor``.

``claude doctor`` has **no JSON output**. Measured on Claude Code 2.1.270:
``claude doctor --help`` lists exactly one option, ``-h, --help``. There is no
``--json`` and no ``--format``, so a machine-readable contract has to be built
by parsing its text. That is a deliberate, reviewed decision with a cost, and
the cost is handled by :data:`Verdict.UNKNOWN` below.

The check answers two questions, both settled by the 2026-09-12 grilling:

1. is the running version the newest release, and
2. does ``claude doctor`` itself report no installation issues?

Why parsing unowned text is survivable here
-------------------------------------------
``.claude/rules/probes-need-a-control-arm.md`` #9 warns that binding a check to
a string you do not own turns it into a silent no-op the day upstream rewords
it. The mitigation is the three-way verdict rather than a boolean:

* :attr:`Verdict.OK` — every assertion was made and passed.
* :attr:`Verdict.INVALID` — an assertion was **made and failed**. Only this
  state is enforcement-eligible.
* :attr:`Verdict.UNKNOWN` — the question could not be asked: output did not
  parse, the binary is missing, or the version oracle failed.

An upstream rewording moves the check to ``UNKNOWN``, which warns. It never
becomes a check that silently passes, and it never blocks on a fact that was
never established. That is the "answered no" versus "never asked" distinction
of ``probes-need-a-control-arm.md`` #4, made structural.

The version oracle
------------------
``mise latest github:anthropics/claude-code`` — which needs no declaration in
any mise config (verified against the undeclared ``github:junegunn/fzf``).

It is cached: ``mise settings --all`` carries
``fetch_remote_versions_cache = "1h"``. :data:`_NO_CACHE_ENV` overrides that TTL
for this one subprocess so the comparison is against the true newest release.
Measured both arms on the cache file mise actually reads: default 0.023s with
the cache mtime unchanged; with the override 0.514s and the mtime updated, i.e.
a genuine refetch.

``mise cache clear <tool>`` is **not** the way to do this. It prints a success
message, exits 0, and leaves every URL-keyed HTTP entry in place.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

#: The tool spec the version oracle resolves. ``github:`` is Anthropic's own
#: prebuilt native release asset set, which is what the native installer ships.
ORACLE_SPEC: Final = "github:anthropics/claude-code"

#: Overrides ``fetch_remote_versions_cache`` (default ``"1h"``) for one
#: subprocess, forcing a live lookup. Scoped to the child environment so no
#: global mise setting changes.
_NO_CACHE_ENV: Final = {"MISE_FETCH_REMOTE_VERSIONS_CACHE": "0s"}

#: ``Running: native (2.1.270)`` / ``Running: npm-global (2.1.269)``.
#: The install METHOD is captured because it is the field that exposed a
#: shadowing install on 2026-09-12, when the answer read ``npm-global`` while a
#: newer native build sat on disk.
_RUNNING_RE: Final = re.compile(
    r"^Running:\s*(?P<method>[\w-]+)\s*\((?P<version>[^)]+)\)\s*$",
    re.MULTILINE,
)

#: The summary line whose presence is the "no errors" assertion.
_CLEAN_MARKER: Final = "No installation issues found."

#: Bound on every subprocess. `.claude/rules/long-running-command-hangs.md`
#: requires a hard bound on anything that can block on network or IO, and this
#: runs at SessionStart where a hang delays every session.
_TIMEOUT_S: Final = 20.0


class Verdict(StrEnum):
    """Three-way outcome. Only ``INVALID`` is enforcement-eligible."""

    OK = "ok"
    INVALID = "invalid"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DoctorVerdict:
    """What the check established, and what it could not."""

    verdict: Verdict
    findings: list[str] = field(default_factory=list)
    running_version: str | None = None
    install_method: str | None = None
    latest_version: str | None = None
    clean_marker_present: bool | None = None

    @property
    def enforcement_eligible(self) -> bool:
        """True only when an assertion was made and failed.

        ``UNKNOWN`` deliberately returns False: a question that could not be
        asked must never block.
        """
        return self.verdict is Verdict.INVALID

    def to_json(self) -> str:
        """Serialise the verdict for a hook or a log."""
        return json.dumps(
            {
                "verdict": self.verdict.value,
                "enforcement_eligible": self.enforcement_eligible,
                "running_version": self.running_version,
                "install_method": self.install_method,
                "latest_version": self.latest_version,
                "clean_marker_present": self.clean_marker_present,
                "findings": self.findings,
            },
            indent=2,
            sort_keys=True,
        )


def _run(
    argv: list[str], *, extra_env: dict[str, str] | None = None
) -> tuple[int, str]:
    """Run ``argv``, returning ``(rc, combined output)``.

    A missing binary, a timeout and a crash all collapse to a non-zero rc with
    the reason as output, so every caller reaches the same ``UNKNOWN`` path
    rather than raising out of a SessionStart hook.
    """
    if shutil.which(argv[0]) is None:
        return 127, f"{argv[0]}: not found on PATH"
    env = {**os.environ, **(extra_env or {})}
    try:
        # Fixed argv, no shell: nothing here is user-controlled.
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"{argv[0]}: timed out after {_TIMEOUT_S:g}s"
    except OSError as exc:
        return 126, f"{argv[0]}: {exc}"
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def parse_doctor(text: str) -> tuple[str | None, str | None, bool]:
    """Extract ``(version, install_method, clean_marker_present)``.

    A ``None`` version means the output did not parse — the caller must treat
    that as ``UNKNOWN``, never as a failed assertion.
    """
    match = _RUNNING_RE.search(text)
    if match is None:
        return None, None, _CLEAN_MARKER in text
    return match["version"].strip(), match["method"].strip(), _CLEAN_MARKER in text


def latest_version(*, force_refresh: bool = True) -> tuple[str | None, str | None]:
    """Newest published release, or ``(None, reason)``.

    ``force_refresh`` bypasses mise's 1h ``fetch_remote_versions_cache`` so the
    comparison is against the true newest release rather than a cached one.
    """
    rc, out = _run(
        ["mise", "latest", ORACLE_SPEC],
        extra_env=_NO_CACHE_ENV if force_refresh else None,
    )
    if rc != 0:
        return None, f"version oracle failed (rc={rc}): {out.strip()[:200]}"
    version = out.strip().splitlines()[-1].strip() if out.strip() else ""
    if not version:
        return None, "version oracle returned no version"
    return version, None


def evaluate(*, force_refresh: bool = True) -> DoctorVerdict:
    """Run both probes and decide.

    Order matters: ``claude doctor`` failing to run at all is ``UNKNOWN``, not
    ``INVALID`` — a missing binary is a question that could not be asked.
    """
    rc, text = _run(["claude", "doctor"])
    if rc != 0:
        return DoctorVerdict(
            verdict=Verdict.UNKNOWN,
            findings=[f"`claude doctor` did not run (rc={rc}): {text.strip()[:200]}"],
        )

    running, method, clean = parse_doctor(text)
    if running is None:
        return DoctorVerdict(
            verdict=Verdict.UNKNOWN,
            findings=[
                (
                    "could not parse a `Running: <method> (<version>)` line "
                    "from `claude doctor` — upstream may have changed its "
                    "output. Treating as UNKNOWN rather than asserting anything."
                )
            ],
            clean_marker_present=clean,
        )

    latest, oracle_error = latest_version(force_refresh=force_refresh)
    if latest is None:
        return DoctorVerdict(
            verdict=Verdict.UNKNOWN,
            findings=[
                (
                    "cannot determine latest version, so currency is unknown "
                    f"(NOT 'current'): {oracle_error}"
                )
            ],
            running_version=running,
            install_method=method,
            clean_marker_present=clean,
        )

    findings: list[str] = []
    if running != latest:
        findings.append(
            f"claude on PATH is {running} but {latest} is published "
            f"(install method: {method}). Run `claude install latest`."
        )
    if not clean:
        findings.append(
            f"`claude doctor` did not report {_CLEAN_MARKER!r} — it found "
            f"installation issues."
        )

    return DoctorVerdict(
        verdict=Verdict.INVALID if findings else Verdict.OK,
        findings=findings,
        running_version=running,
        install_method=method,
        latest_version=latest,
        clean_marker_present=clean,
    )
