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
import sys
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Final

from dotfiles_setup.path_drift import Provenance, resolve_ambient_path

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

#: The install method grilling decision Q1 settled on: "Native installer owns
#: claude. Not mise."
#:
#: Asserted, not merely captured. The 2026-09-12 session observed a shadowing
#: install, wrote :data:`_RUNNING_RE`'s ``method`` group to expose it, and then
#: asserted only on the two facts that were *symptoms* of it — so when the class
#: recurred within a day, the check described it as a missed update. A field
#: captured but never asserted on is documentation, not a gate.
#:
#: The recurrence was self-inflicted: ``mise.toml`` pinned
#: ``npm:@anthropic-ai/claude-code`` so :mod:`dotfiles_setup.fnhook_gates` could
#: name an exact ``claude@<version>``, and a ``[tools]`` pin necessarily puts a
#: competing ``claude`` on PATH. That pin is now ``github:anthropics/claude-code``
#: (#1043), which removes the npm failure mode — but NOT the need for this
#: assertion: a mise-provided claude still lands on PATH, it simply reports
#: ``package-manager`` instead of ``npm-global``. Either way it is not ``native``,
#: and that is exactly what this catches.
#:
#: Binding a third upstream string is the cost. It is bounded the same way the
#: other two are: an output that does not parse never reaches this comparison,
#: because :func:`parse_doctor` returns ``None`` and the caller routes to
#: ``UNKNOWN``. A rewording therefore warns; it cannot pass silently.
NATIVE_METHOD: Final = "native"

#: What the check reports when it cannot see the shell's own ``claude``.
#:
#: Measured 2026-09-13, both arms from one fresh login shell: resolving against
#: the captured ambient ``PATH`` finds ``~/.local/bin/claude`` (native 2.1.270),
#: while the ``PATH`` inherited inside ``uv run`` finds
#: ``~/.local/share/mise/installs/npm-anthropic-ai-claude-code/2.1.269/bin/claude``.
#: Reporting on the second one is not a smaller answer, it is an answer about a
#: different binary — and while today it produced a false INVALID, the same
#: mechanism yields a false OK the moment the mise pin happens to be current.
#: Blindness is therefore a finding, never a pass, exactly as in
#: :mod:`dotfiles_setup.path_drift`.
_BLIND_ADVICE: Final = (
    "claude-doctor check is BLIND: mise already rewrote PATH for this process, "
    "so the claude this shell would actually run is not visible here. This is "
    "NOT 'claude is fine'. Have the caller capture it: "
    'DOTFILES_AMBIENT_PATH="$PATH" mise run <task>'
)

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
    argv: list[str],
    *,
    extra_env: dict[str, str] | None = None,
    path: str | None = None,
) -> tuple[int, str]:
    """Run ``argv``, returning ``(rc, combined output)``.

    A missing binary, a timeout and a crash all collapse to a non-zero rc with
    the reason as output, so every caller reaches the same ``UNKNOWN`` path
    rather than raising out of a SessionStart hook.

    ``path`` is the ``PATH`` the binary is resolved against **and** the one the
    child inherits. Both halves matter: resolving against it picks the binary the
    operator's shell would run, and handing it down means ``claude doctor``
    reports on the installation it would report on there.
    """
    resolved = shutil.which(argv[0], path=path) if path else shutil.which(argv[0])
    if resolved is None:
        return 127, f"{argv[0]}: not found on PATH"
    argv = [resolved, *argv[1:]]
    env = {**os.environ, **({"PATH": path} if path else {}), **(extra_env or {})}
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


def latest_version(
    *, force_refresh: bool = True, path: str | None = None
) -> tuple[str | None, str | None]:
    """Newest published release, or ``(None, reason)``.

    ``force_refresh`` bypasses mise's 1h ``fetch_remote_versions_cache`` so the
    comparison is against the true newest release rather than a cached one.
    """
    rc, out = _run(
        ["mise", "latest", ORACLE_SPEC],
        extra_env=_NO_CACHE_ENV if force_refresh else None,
        path=path,
    )
    if rc != 0:
        return None, f"version oracle failed (rc={rc}): {out.strip()[:200]}"
    version = out.strip().splitlines()[-1].strip() if out.strip() else ""
    if not version:
        return None, "version oracle returned no version"
    return version, None


def evaluate(
    *, force_refresh: bool = True, expected_method: str = NATIVE_METHOD
) -> DoctorVerdict:
    """Run both probes and decide.

    Order matters: ``claude doctor`` failing to run at all is ``UNKNOWN``, not
    ``INVALID`` — a missing binary is a question that could not be asked.

    ``expected_method`` is the install method :data:`NATIVE_METHOD` documents.
    Pass ``""`` to skip that assertion entirely — a host that deliberately runs a
    non-native build should say so in ``doctor.toml`` rather than read a standing
    finding it has decided to accept.
    """
    path, provenance = resolve_ambient_path(os.environ)
    if provenance is Provenance.BLIND:
        return DoctorVerdict(
            verdict=Verdict.UNKNOWN,
            findings=[_BLIND_ADVICE],
        )

    rc, text = _run(["claude", "doctor"], path=path)
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

    latest, oracle_error = latest_version(force_refresh=force_refresh, path=path)
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
    if expected_method and method != expected_method:
        # The shim advice is only true when the NATIVE install is the one being
        # displaced. Appending it unconditionally made the finding blame a mise
        # pin for shadowing the native build in the very case where the install
        # on PATH *was* native — advice that contradicts the fact beside it.
        detail = (
            " Check `which -a claude` — but note it inherits this process's "
            "PATH; `mise env -C <dir>` is the inheritance-free question. A mise "
            "`[tools]` pin of claude puts one on PATH (reported as "
            "'package-manager'), and a leftover npm global reports 'npm-global'. "
            "Repair with `claude install latest`; `claude doctor` names a "
            "leftover npm install and its uninstall command directly."
            if expected_method == NATIVE_METHOD
            else ""
        )
        findings.append(
            f"claude on PATH is a {method!r} install, not the expected "
            f"{expected_method!r}.{detail}"
        )
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


#: The reviewed baseline, relative to the repository root.
_BASELINE_FILE: Final = "doctor.toml"

#: What a deliberately disabled check reports.
#:
#: ``UNKNOWN`` rather than ``OK`` on purpose: ``doctor.toml`` warns that "a
#: disabled check reports nothing, which reads exactly like a healthy host".
#: Routing to ``UNKNOWN`` keeps the off-switch honest — it warns, and because
#: only ``INVALID`` is enforcement-eligible it still never blocks.
_DISABLED_ADVICE: Final = (
    "claude-doctor is disabled: doctor.toml [claude] sets enabled = false. "
    "This is NOT a clean bill of health - the question was not asked."
)


def load_baseline(project_root: Path | None = None) -> tuple[bool, str]:
    """Read ``[claude]`` from ``doctor.toml`` as ``(enabled, expected_method)``.

    The ENFORCING path must read the same reviewed baseline the advisory one
    does. It did not until 2026-09-13: :func:`claude_doctor_main` defaulted
    ``expected_method`` to :data:`NATIVE_METHOD` and never opened the file, so
    ``doctor.toml``'s two documented levers moved
    :func:`doctor.check_claude_doctor`'s advisory finding while the
    ``classic.PreToolUse`` half of the ``claude-doctor`` plugin - the only path
    that can BLOCK a tool call - went on asserting a hardcoded constant.

    Measured that day, one session, same config: editing
    ``expected_install_method`` removed the doctor's finding and changed the
    hook's behaviour not at all. A documented off-switch wired to a different
    consumer is worse than no off-switch, because it reads as configurable.

    An unreadable or absent file falls back to ``(True, NATIVE_METHOD)``: a
    missing baseline asserts the documented default rather than silently
    disabling the check, which is the failure direction that reads as healthy.
    """
    root = project_root or Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    try:
        parsed = tomllib.loads((root / _BASELINE_FILE).read_text())
    except OSError, tomllib.TOMLDecodeError:
        return True, NATIVE_METHOD
    block = parsed.get("claude")
    if not isinstance(block, dict):
        return True, NATIVE_METHOD
    expected = block.get("expected_install_method")
    return (
        block.get("enabled") is not False,
        expected if isinstance(expected, str) else NATIVE_METHOD,
    )


def claude_doctor_main(
    *,
    force_refresh: bool = True,
    expected_method: str | None = None,
    project_root: Path | None = None,
) -> int:
    """Print the verdict as JSON and return an exit code.

    This is the seam the function-hook module calls. ``zero-bash-logic.md``
    keeps the judgement in python, so ``hooks/register.ts`` only shells out to
    this and renders the answer.

    The exit code encodes **enforcement eligibility, not success**: non-zero
    only for :attr:`Verdict.INVALID`. ``UNKNOWN`` returns 0 on purpose — it is a
    question that could not be asked, and per this module's docstring such a
    question must warn rather than block. A caller wanting the distinction reads
    ``verdict`` from the JSON, which is always emitted.
    """
    enabled, configured = load_baseline(project_root)
    if not enabled:
        disabled = DoctorVerdict(verdict=Verdict.UNKNOWN, findings=[_DISABLED_ADVICE])
        sys.stdout.write(disabled.to_json() + "\n")
        return 0
    verdict = evaluate(
        force_refresh=force_refresh,
        expected_method=configured if expected_method is None else expected_method,
    )
    sys.stdout.write(verdict.to_json() + "\n")
    return 1 if verdict.enforcement_eligible else 0
