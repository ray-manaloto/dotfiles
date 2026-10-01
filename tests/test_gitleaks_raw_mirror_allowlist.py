# Copyright (c) 2026 Raymond Manaloto
"""Tests for the raw-mirror allowlist entries in `.gitleaks.toml` (#1472).

Vendored mirrors under `docs/research/kb/raw/` are committed byte-verbatim, so
their judged false positives are allowlisted by CONTENT. The trap these tests
exist for: a GLOBAL `[[allowlists]]` entry (no `targetRules`) that carries
`paths` blinds gitleaks 8.30.1 to EVERY finding under that path, even with
`condition = "AND"` and `regexes`. Each test plants a real-shaped token so that
"simplifying" an entry into a global one fails here.

Every fixture value is built at runtime from fragments, never written as one
token, so this file stays clean to the hk gitleaks and betterleaks steps that
scan `tests/`. Only gitleaks is exercised: it is pinned in the shared mise
fragment (host, image and CI), betterleaks is host-only (`mise.toml`).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import string
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / ".gitleaks.toml"
MIRROR = Path("docs/research/kb/raw/fixture-mirror")
CAPTURE = MIRROR / "docs-source/.vitepress/theme/showreel/test/captures/x.json"

# Judged public values, split so no complete one is a literal in this file.
_MINISIGN = "RWTC3g8W3z4RZK" + "3V3qv7fa1QY4JE" + "WyBtqIHW+85QlJ" + "pZc5yG+uNYNBSZ"
_DOCSEARCH = "ad09b96a7d2a" + "30eddc277180" + "0da7a1cf"
_SHA1 = hashlib.sha1(b"fixture-commit", usedforsecurity=False).hexdigest()
_SHA256 = hashlib.sha256(b"fixture-capture").hexdigest()
# The rule only fires in a file that also contains one of its keywords
# (`sourcegraph`, `sgp_`); link-4.md, the real mirror, does.
_COMMIT_LINE = (
    "Compare the sourcegraph integration:\n"
    f"See https://github.com/DeusData/codebase-memory-mcp/commit/{_SHA1} for the fix.\n"
)


def _planted_token() -> str:
    """A real-shaped GitHub PAT: the prefix, then 36 mixed-case alphanumerics."""
    vendor = "gh"
    return vendor + "p_" + (string.ascii_letters + string.digits)[7:43]


def _write(root: Path, rel: Path, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def _judged_fp_tree(root: Path) -> None:
    """One file per allowlist entry, laid out where the real mirrors live."""
    _write(root, MIRROR / "link-4.md", _COMMIT_LINE)
    _write(root, MIRROR / "docker.md", f"ARG MISE_MINISIGN_KEY={_MINISIGN}\n")
    _write(root, MIRROR / "config.ts", f'          apiKey: "{_DOCSEARCH}",\n')
    _write(root, CAPTURE, f'{{\n  "key": "{_SHA256}",\n  "n": 1\n}}\n')
    _write(
        root, MIRROR / "environments.md", "PASS" + "WORD" + ' = "my' + '_password"\n'
    )


def _scan(root: Path, config: Path) -> tuple[int, list[dict]]:
    exe = shutil.which("gitleaks")
    assert exe is not None, "gitleaks (shared.toml pin) is not on PATH"
    report = root.parent / f"{root.name}-report.json"
    proc = subprocess.run(
        [
            exe,
            "dir",
            "--no-banner",
            "--redact",
            "-c",
            str(config),
            "-f",
            "json",
            "-r",
            str(report),
            ".",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in {0, 1}, proc.stderr
    return proc.returncode, json.loads(report.read_text())


def _hits(findings: list[dict]) -> set[tuple[str, str]]:
    return {(f["RuleID"], f["File"]) for f in findings}


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    _judged_fp_tree(root)
    return root


def test_fixture_trips_the_default_rules(tree: Path, tmp_path: Path) -> None:
    """Control arm: without the repo allowlists, the fixture really is flagged."""
    defaults = tmp_path / "defaults.toml"
    defaults.write_text("[extend]\nuseDefault = true\n")
    rc, findings = _scan(tree, defaults)
    assert rc == 1
    assert _hits(findings) >= {
        ("sourcegraph-access-token", str(MIRROR / "link-4.md")),
        ("generic-api-key", str(MIRROR / "docker.md")),
        ("generic-api-key", str(MIRROR / "config.ts")),
        ("generic-api-key", str(CAPTURE)),
    }


def test_judged_false_positives_are_allowlisted(tree: Path) -> None:
    rc, findings = _scan(tree, CONFIG)
    assert (rc, findings) == (0, [])


def test_planted_token_in_mirror_is_still_reported(tree: Path) -> None:
    _write(tree, MIRROR / "planted.md", f"token = {_planted_token()}\n")
    rc, findings = _scan(tree, CONFIG)
    assert rc == 1
    assert _hits(findings) == {("github-pat", str(MIRROR / "planted.md"))}


def test_planted_token_in_showreel_capture_is_still_reported(tree: Path) -> None:
    body = f'{{\n  "key": "{_SHA256}",\n  "note": "{_planted_token()}"\n}}\n'
    _write(tree, CAPTURE, body)
    rc, findings = _scan(tree, CONFIG)
    assert rc == 1
    assert ("github-pat", str(CAPTURE)) in _hits(findings)


def test_commit_sha_outside_raw_mirrors_is_still_reported(tree: Path) -> None:
    outside = Path("docs/research/kb/reports/x.md")
    _write(tree, outside, _COMMIT_LINE)
    rc, findings = _scan(tree, CONFIG)
    assert rc == 1
    assert _hits(findings) == {("sourcegraph-access-token", str(outside))}


def test_no_global_entry_combines_paths_with_regexes() -> None:
    """The trap: `paths` + `regexes` without `targetRules` blinds a whole path."""
    entries = tomllib.loads(CONFIG.read_text())["allowlists"]
    offenders = [
        e["description"]
        for e in entries
        if "paths" in e and "regexes" in e and not e.get("targetRules")
    ]
    assert offenders == []
