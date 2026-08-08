# Copyright (c) 2026 Raymond Manaloto
"""Env-dump detection — the one leak shape no secret scanner can see.

## Why this exists (2026-07-27)

`fnox activate` exports real credentials into the interactive shell, and mise
then records the whole environment delta in **`__MISE_DIFF`** — zlib-compressed
and base64-encoded — which every child process inherits. Decoded, the live blob
on this machine carried an AWS access key id and secret, several API tokens, an
app password, and a Google client secret. Nothing ever reached a public remote
(verified by pickaxing the exact values across the full history of both repos,
0 commits each against a control term returning 339 / 94), but the shape is one
commit away: any tool that writes its environment into a file — an agent
transcript, a research artifact, a CI log, a bug report — writes those
credentials in a form that looks like opaque noise.

**Measured, both arms, with synthetic secrets:**

| scanner | plaintext env dump | the same content as a blob |
|---|---|---|
| gitleaks 8.30.1 | 2 leaks | **0** |
| betterleaks 1.7.1 | 1 leak | **0** |

The control arm fires on the plaintext, so the zero is a real negative, not a
blind probe. That measurement is this module's justification under
`.claude/rules/use-tool-builtins.md`: gitleaks and betterleaks both run in this
repo and both stay — this covers only what neither can do, which is **decode**.

## What it checks

1. A `__MISE_DIFF` (or any env-var) assignment followed by a long opaque run.
2. **Any** long base64 run that actually zlib/gzip-decompresses to text naming
   two or more secret-bearing environment variables. Random base64 does not
   decompress, so this is precise rather than noisy.
3. High-confidence secret *values* in tracked files. gitleaks is configured
   here with a path allowlist covering `docs/research/kb/` and
   `docs/research/runs/` — both of which are **tracked** — so an env dump
   landing there today is committed with the scanner deliberately looking away.
   This check has no such exemption.

The source-side fix is fnox's own `env = "exec"` (v1.30.0+, and fnox is already
at 1.31.1 here), which keeps secrets out of the interactive shell entirely.
See `.claude/rules/secrets-out-of-the-shell-env.md`. This module is the
commit-boundary net under that, not a substitute for it.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import logging
import re
import subprocess
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Third-party documentation caches ship vendor EXAMPLE credentials (the single
# `AKIA` in this repo's history is one). They are not ours, they are already
# committed, and re-flagging them forever would train the reader to ignore this
# gate. Nothing else is exempt — that is the point.
EXEMPT_PREFIXES: tuple[str, ...] = ("docs/research/mintlify-cache/",)

# How long a base64 run must be before decoding is attempted. The first draft
# used 200 and the control arm caught it: a synthetic 157-byte dump compresses
# to ~180 chars, so the probe's own fixture slipped under the floor. 120 keeps
# the scan cheap while covering a dump far smaller than any real one (mise's
# live `__MISE_DIFF` here is ~7 KB), and the decompress step — not the length —
# is what keeps it precise.
MIN_BLOB_CHARS = 120

# A `__MISE_DIFF` assignment needs no decode and no length argument: mise sets
# it to a compressed env delta and nothing else, so its presence in a tracked
# file IS the finding.
MIN_NAMED_BLOB_CHARS = 40

_B64_RUN = re.compile(r"[A-Za-z0-9+/_-]{" + str(MIN_BLOB_CHARS) + r",}={0,2}")

# An env-var assignment whose value is an opaque run — `__MISE_DIFF=eJx…` as it
# appears in `env` output, an exported shell snippet, or a pasted log.
_ENV_ASSIGNMENT = re.compile(
    r"\b([A-Z_][A-Z0-9_]{2,})\s*[=:]\s*[\"']?"
    r"([A-Za-z0-9+/_-]{" + str(MIN_NAMED_BLOB_CHARS) + r",}={0,2})"
)

# The variable whose very presence is the leak.
ENV_DIFF_NAME = "__MISE_DIFF"

# Names that mark decoded text as an environment dump carrying credentials.
_SECRET_NAME = re.compile(
    r"\b[A-Z][A-Z0-9_]*"
    r"(?:SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY|CREDENTIAL)"
    r"[A-Z0-9_]*\b"
)

# How many distinct secret-bearing names a decoded blob must name before it is
# called an env dump. One is a coincidence; two is a dump.
MIN_DECODED_NAMES = 2

# High-confidence secret VALUES. Deliberately few: gitleaks and betterleaks own
# the general case, and every pattern here is one whose format is unambiguous,
# so it cannot fire on prose.
_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-client-secret", re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{20,}\b")),
    ("github-pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github-fine-grained-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("private-key-header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


@dataclass(frozen=True)
class Violation:
    """One finding. Carries the SHAPE of the leak, never the value."""

    path: str
    line: int
    kind: str
    detail: str

    def render(self) -> str:
        """One line naming the file, the line, and the leak SHAPE."""
        return f"{self.path}:{self.line}: {self.kind} — {self.detail}"


def decode_blob(candidate: str) -> str | None:
    """Decode a base64 run to text if it really is compressed data.

    Returns None for anything that is not base64-of-compressed-text, which is
    almost everything: random base64 fails the decompress step, so this is the
    filter that keeps the scan precise.
    """
    padded = candidate.rstrip("=")
    padded += "=" * (-len(padded) % 4)
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            raw = decoder(padded)
        except binascii.Error, ValueError:
            continue
        for decompress in (zlib.decompress, gzip.decompress):
            try:
                return decompress(raw).decode("utf-8", errors="replace")
            except zlib.error, gzip.BadGzipFile, EOFError, OSError:
                continue
    return None


def _secret_names(text: str) -> set[str]:
    return set(_SECRET_NAME.findall(text))


def _scan_text(rel: str, text: str) -> list[Violation]:
    violations: list[Violation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in _VALUE_PATTERNS:
            if pattern.search(line):
                violations.append(
                    Violation(rel, lineno, kind, "a literal credential value")
                )

        assignment = _ENV_ASSIGNMENT.search(line)
        if assignment:
            name, blob = assignment.group(1), assignment.group(2)
            names = _secret_names(decode_blob(blob) or "")
            if name == ENV_DIFF_NAME or len(names) >= MIN_DECODED_NAMES:
                violations.append(
                    Violation(
                        rel,
                        lineno,
                        "env-dump-blob",
                        f"{name} assigned an opaque {len(blob)}-char run"
                        + (
                            f" that decodes to {len(names)} secret names"
                            if names
                            else ""
                        ),
                    )
                )
                continue

        for run in _B64_RUN.findall(line):
            names = _secret_names(decode_blob(run) or "")
            if len(names) >= MIN_DECODED_NAMES:
                violations.append(
                    Violation(
                        rel,
                        lineno,
                        "compressed-env-dump",
                        f"a {len(run)}-char blob decompresses to text naming "
                        f"{len(names)} secret-bearing variables",
                    )
                )
    return violations


def tracked_files(root: Path) -> list[str]:
    """Every file git tracks — i.e. everything a push would carry."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("git ls-files failed: %s", result.stderr.strip())
        return []
    return [p for p in result.stdout.split("\0") if p]


def find_violations(root: Path, paths: list[str] | None = None) -> list[Violation]:
    """Scan the given paths (default: every tracked file) for env dumps."""
    candidates = paths if paths is not None else tracked_files(root)
    violations: list[Violation] = []
    for rel in candidates:
        if rel.startswith(EXEMPT_PREFIXES):
            continue
        target = root / rel
        if not target.is_file():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError, OSError:
            continue  # binary or unreadable — no env dump lives there
        violations.extend(_scan_text(rel, text))
    return violations


def env_blob_scan_main(root: Path, paths: list[str] | None = None) -> int:
    """CLI entrypoint: report every env-dump finding; 1 if any."""
    violations = find_violations(root, paths)
    if not violations:
        return 0
    for violation in violations:
        logger.error("%s", violation.render())
    logger.error(
        "%d env-dump finding(s). A committed environment dump publishes every "
        "credential in it. See .claude/rules/secrets-out-of-the-shell-env.md",
        len(violations),
    )
    return 1
