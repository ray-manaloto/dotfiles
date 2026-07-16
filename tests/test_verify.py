"""Tests for the verification engine (dotfiles_setup.verify).

Scoped to the behaviour spec #299 changed — path strictness and token binding
— NOT a retrofit of every handler; untested handlers this PR does not touch
are not its debt (spec, Out of Scope).

Every check here pins its FAIL direction next to its pass. That is the whole
subject: the bug being fixed was a contract that *passed* when the thing it
guarded had vanished, so a test that only ever asserts PASSED would reproduce
the defect rather than catch it (`.claude/rules/probes-need-a-control-arm.md`).

The suite entries are literal dicts and the handler map is injected, so these
tests need no fixture files on disk. Paths that must exist resolve against the
real project root; paths that must NOT exist are named under a directory that
has never existed in this repo.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import verify

# A real, tracked file — the independent source of truth for "this path
# exists" is the repo itself, not something the engine computes.
_REAL = "mise.toml"
_ALSO_REAL = "python/verification/suites.toml"

# Never existed in this repo; the engine must treat it as missing.
_GONE = "no/such/dir/ABCD1234.toml"

# A handler that always passes. It makes the runner's own precondition the
# only thing under test: any failure below came from run_suite, not a handler.
_ALWAYS_PASS = {"nop": lambda _entry: {"status": "passed"}}


def _entry(**over: object) -> dict[str, object]:
    base: dict[str, object] = {"name": "t.suite", "handler": "nop"}
    return base | over


def test_paths_required_defaults_to_strict() -> None:
    """A missing path fails with no `paths_required` key present at all.

    This is the default that spec #299 inverted: 82 of 97 suites named no
    `paths_required`, so the engine's default IS their behaviour.
    """
    result = verify.run_suite(_entry(paths=[_GONE]), handlers=_ALWAYS_PASS)
    assert result["status"] == "failed"
    assert _GONE in result["reason"]


def test_existing_paths_pass_under_the_strict_default() -> None:
    """Control arm: strict-by-default must not fail a suite that is fine.

    Without this, `test_paths_required_defaults_to_strict` is satisfied by an
    engine that fails everything.
    """
    result = verify.run_suite(_entry(paths=[_REAL, _ALSO_REAL]), handlers=_ALWAYS_PASS)
    assert result["status"] == "passed"


def test_explicit_false_opts_out_of_strictness() -> None:
    """`paths_required = false` is the visible, reviewable opt-out."""
    result = verify.run_suite(
        _entry(paths=[_GONE], paths_required=False), handlers=_ALWAYS_PASS
    )
    assert result["status"] == "passed"


def test_partial_path_loss_fails() -> None:
    """THE regression. One of two declared paths gone must FAIL.

    Proven on 2026-07-16 against the pre-#299 engine: deleting one of two
    declared files left the contract PASSED, because every handler resolves
    paths through `_resolve_paths`, which silently drops what is gone. The
    surviving file carried the contract, and a guarded file could be renamed
    or deleted without any contract noticing (`fc8af71` did exactly this and
    went unnoticed for ~3.5 months).
    """
    result = verify.run_suite(_entry(paths=[_REAL, _GONE]), handlers=_ALWAYS_PASS)
    assert result["status"] == "failed"
    assert _GONE in result["reason"]
    # The surviving file is not the complaint — only the missing one is.
    assert _REAL not in result["reason"]


def test_all_paths_gone_fails() -> None:
    """Total path loss fails too — strictness is not partial-only.

    Note precisely whose behaviour this is. `require_tokens` already rejected
    a fully-empty path list pre-#299 via its own "no target files found"
    check, so *for that one handler* total loss was always caught. This test
    runs the always-pass handler, so it pins the ENGINE — which pre-#299 had
    no such check, and where the guarantee now holds for every handler
    regardless of what the handler itself does. (Verified by reintroducing the
    old default: this test fails against it.)
    """
    result = verify.run_suite(_entry(paths=[_GONE]), handlers=_ALWAYS_PASS)
    assert result["status"] == "failed"


def test_strictness_is_enforced_before_the_handler_runs() -> None:
    """The precondition belongs to the runner, not to any one handler.

    Pre-#299 only `require_tokens` honoured `paths_required`, so a
    `regex_forbid` or `forbid_tokens` suite could lose a guarded file
    silently. A handler that would blow up if reached proves the check is
    upstream of dispatch — and therefore covers every handler at once.
    """

    def _explode(_entry: dict[str, object]) -> dict[str, object]:
        msg = "handler must never be reached when a required path is missing"
        raise AssertionError(msg)

    result = verify.run_suite(_entry(paths=[_GONE]), handlers={"nop": _explode})
    assert result["status"] == "failed"
    assert "missing" in result["reason"]


def test_per_path_tokens_binds_a_token_to_its_file() -> None:
    """A token bound to a file that does not carry it must FAIL.

    `mise.toml` does not contain `def sync_main` — sync.py does. Binding is
    what gives a contract an opinion about each file it names.
    """
    result = verify.run_suite(
        _entry(
            handler="require_tokens",
            paths=[_REAL],
            per_path_tokens={_REAL: ["def sync_main"]},
        )
    )
    assert result["status"] == "failed"
    assert "def sync_main" in result["reason"]


def test_bare_tokens_are_a_union_across_paths() -> None:
    """Control arm documenting WHY `per_path_tokens` exists.

    The identical token+paths pair from the test above passes under bare
    `tokens`, because combined-text semantics let ANY listed file satisfy the
    contract for all of them. Same inputs, opposite verdict: that difference
    is the silent-false-negative class spec #299 closes. If this ever starts
    failing, `require_tokens`'s union semantics changed and the four converted
    wiring suites need re-reading, not this test "fixing".
    """
    result = verify.run_suite(
        _entry(
            handler="require_tokens",
            paths=[_REAL, "python/src/dotfiles_setup/sync.py"],
            tokens=["def sync_main"],
        )
    )
    assert result["status"] == "passed"
