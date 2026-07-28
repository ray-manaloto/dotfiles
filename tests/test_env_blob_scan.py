"""Tests for the env-dump gate.

Every credential literal here is SYNTHETIC and is built by concatenation, never
written as one token — so this file is clean to gitleaks, to betterleaks, and
to the very scanner it tests. A test fixture that trips the repo's own secret
gates is a test that gets deleted.
"""

from __future__ import annotations

import base64
import subprocess
import zlib
from pathlib import Path

import pytest
from dotfiles_setup import env_blob_scan
from dotfiles_setup.env_blob_scan import (
    ENV_DIFF_NAME,
    MIN_BLOB_CHARS,
    decode_blob,
    env_blob_scan_main,
    find_violations,
)

# Split so no complete credential ever appears as a literal in this file.
FAKE_AWS_KEY = "AKIA" + "3QZ7WTVB2NKLDXPR"
FAKE_GH_PAT = "gh" + "p_9fK2mQ8xR4tV6yB1nC3dE5gH7jL0pS2wX4zA"
FAKE_GOOGLE_SECRET = "GOCSPX-" + "kL9mN2pQ4rS6tU8vW0xY2zA4bC6d"
# Split for the same reason: the whole marker in one literal would trip the
# very gate under test when it scans this repo.
FAKE_KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY-----"

ENV_DUMP = (
    "\n".join(f"VAR_{i}=value{i}" for i in range(40))
    + f"\nAWS_ACCESS_KEY_ID={FAKE_AWS_KEY}"
    + "\nAWS_SECRET_ACCESS_KEY=wJalr9XUtnFEMI0K7MDENG2bPxRfiCYnotreal"
    + f"\nGITHUB_TOKEN={FAKE_GH_PAT}\n"
)


def _blob(text: str) -> str:
    return base64.b64encode(zlib.compress(text.encode())).decode()


def _write(tmp_path: Path, name: str, body: str) -> list:
    (tmp_path / name).write_text(body)
    return find_violations(tmp_path, [name])


def test_a_named_mise_diff_assignment_is_a_finding(tmp_path: Path) -> None:
    hits = _write(tmp_path, "log.txt", f"{ENV_DIFF_NAME}={_blob(ENV_DUMP)}\n")
    assert [h.kind for h in hits] == ["env-dump-blob"]


def test_a_bare_blob_with_no_variable_name_is_still_caught(tmp_path: Path) -> None:
    """The hardest case: someone pastes the value alone, without its name."""
    hits = _write(tmp_path, "log.txt", _blob(ENV_DUMP) + "\n")
    assert [h.kind for h in hits] == ["compressed-env-dump"]


def test_a_long_base64_run_that_is_not_compressed_data_is_ignored(
    tmp_path: Path,
) -> None:
    """The negative control. Without it, the gate could be flagging any base64."""
    body = "signature=" + base64.b64encode(b"x" * 400).decode() + "\n"
    assert _write(tmp_path, "sig.txt", body) == []


def test_a_compressed_blob_naming_only_one_secret_var_is_not_enough(
    tmp_path: Path,
) -> None:
    """One name is a coincidence; the gate wants two before it calls it a dump."""
    single = "\n".join(f"VAR_{i}=value{i}" for i in range(60)) + "\nMY_TOKEN=abc\n"
    assert _write(tmp_path, "one.txt", _blob(single)) == []


# Explicit ids: pytest derives a node id from the parameter VALUE otherwise, and
# writes it into `.pytest_cache/v/cache/nodeids` — where gitleaks, which scans
# the whole working tree, finds a credential-shaped string in a generated file.
# Naming the cases keeps the values out of every artifact pytest writes.
@pytest.mark.parametrize(
    ("value", "kind"),
    [
        pytest.param(FAKE_AWS_KEY, "aws-access-key-id", id="aws-key"),
        pytest.param(FAKE_GH_PAT, "github-pat", id="github-pat"),
        pytest.param(FAKE_GOOGLE_SECRET, "google-client-secret", id="google"),
        pytest.param(FAKE_KEY_HEADER, "private-key-header", id="private-key"),
    ],
)
def test_literal_credential_values_are_caught(
    tmp_path: Path, value: str, kind: str
) -> None:
    hits = _write(tmp_path, "creds.txt", f"secret = {value}\n")
    assert [h.kind for h in hits] == [kind]


def test_prose_that_merely_names_a_variable_is_not_a_finding(tmp_path: Path) -> None:
    body = (
        "The guard exports AWS_SECRET_ACCESS_KEY and GITHUB_TOKEN into the\n"
        "environment, which is why __MISE_DIFF matters.\n"
    )
    assert _write(tmp_path, "doc.md", body) == []


def test_the_vendor_doc_cache_is_the_only_exemption(tmp_path: Path) -> None:
    """Exempt by prefix — and the exemption must not extend to a sibling path."""
    body = f"key = {FAKE_AWS_KEY}\n"
    exempt = tmp_path / "docs/research/mintlify-cache/vendor"
    exempt.mkdir(parents=True)
    (exempt / "llms.txt").write_text(body)
    tracked = tmp_path / "docs/research/kb"
    tracked.mkdir(parents=True)
    (tracked / "report.md").write_text(body)

    exempt_rel = "docs/research/mintlify-cache/vendor/llms.txt"
    assert find_violations(tmp_path, [exempt_rel]) == []
    # docs/research/kb is allowlisted in .gitleaks.toml AND is tracked — the
    # exact hole this gate exists to close. It must NOT be exempt here.
    assert len(find_violations(tmp_path, ["docs/research/kb/report.md"])) == 1


def test_a_dump_just_over_the_length_floor_is_caught(tmp_path: Path) -> None:
    """Pins the floor the first draft got wrong.

    MIN_BLOB_CHARS was 200; a small synthetic dump compressed to ~180 chars and
    slipped under it, so the probe's own fixture was invisible to the gate.
    """
    # Padding must be VARIED, not repeated: 12 identical lines compress to an
    # 88-char blob, which would have made this test assert the wrong thing.
    body = "AWS_SECRET_ACCESS_KEY=x\nGITHUB_TOKEN=y\n" + "".join(
        f"PAD_{i}=q{i * 7919:x}z\n" for i in range(5)
    )
    blob = _blob(body)
    assert MIN_BLOB_CHARS <= len(blob) < 200, f"fixture is {len(blob)} chars"
    assert len(_write(tmp_path, "small.txt", blob)) == 1


def test_decode_blob_returns_none_for_anything_that_is_not_compressed() -> None:
    assert decode_blob("not base64 at all !!!") is None
    assert decode_blob(base64.b64encode(b"plain, uncompressed").decode()) is None
    assert decode_blob(_blob("hello")) == "hello"


def test_main_returns_zero_on_a_clean_tree_and_one_on_a_dirty_one(
    tmp_path: Path,
) -> None:
    (tmp_path / "clean.md").write_text("nothing to see\n")
    assert env_blob_scan_main(tmp_path, ["clean.md"]) == 0
    (tmp_path / "dirty.txt").write_text(f"{ENV_DIFF_NAME}={_blob(ENV_DUMP)}\n")
    assert env_blob_scan_main(tmp_path, ["dirty.txt"]) == 1


def test_the_real_repo_is_clean() -> None:
    """The gate must pass on the tree it ships in — or it would never be run."""
    root = Path(__file__).resolve().parent.parent
    assert find_violations(root) == []


def test_tracked_files_reads_the_repo_and_not_an_empty_list() -> None:
    """Control arm for the default scope: an empty list would mean scanning nothing."""
    root = Path(__file__).resolve().parent.parent
    tracked = env_blob_scan.tracked_files(root)
    assert "python/verification/suites.toml" in tracked
    assert len(tracked) > 100


def test_untracked_files_are_out_of_scope(tmp_path: Path) -> None:
    """The gate guards what a PUSH carries, so gitignored files are irrelevant."""
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    (tmp_path / ".gitignore").write_text("secret.log\n")
    (tmp_path / "secret.log").write_text(f"{ENV_DIFF_NAME}={_blob(ENV_DUMP)}\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".gitignore"], check=True)
    assert find_violations(tmp_path) == []
