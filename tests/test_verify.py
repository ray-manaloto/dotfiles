# Copyright (c) 2026 Raymond Manaloto
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

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

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


# ---------------------------------------------------------------------------
# require_lines (#354 PR 1) — a SENTENCE is not a substring
# ---------------------------------------------------------------------------
#
# The bug that opened #354 was an absent orchestrator trigger LINE. A substring
# `require_tokens` would notice its absence, but it would equally accept the
# sentence buried in a longer line, split across a paraphrase, or quoted inside
# prose that narrates it rather than declares it. A declaration is a whole line
# or it is not that declaration, so `require_lines` binds the whole line and
# normalises only whitespace.

_MODE_LINE = "- fable-orchestrator: implementation lane = codex"

_TRIGGER = (
    "- When the session model is Fable, without being reminded: non-trivial "
    "implementation runs the fable-orchestrator architect-as-orchestrator flow"
)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    target = tmp_path / name
    target.write_text(text)
    return target


def test_require_lines_matches_a_whole_line(tmp_path: Path) -> None:
    """The baseline pass: an exact line is found."""
    doc = _write(tmp_path, "a.md", f"intro\n{_TRIGGER}\noutro\n")
    assert verify.require_lines([doc], [_TRIGGER])["status"] == "passed"


def test_require_lines_rejects_a_substring_of_a_longer_line(tmp_path: Path) -> None:
    """THE distinction from `require_tokens`.

    A declaration quoted inside a narrating sentence is a *mention*, not a
    declaration. `require_tokens` cannot tell those apart; this handler exists
    because that difference is exactly what went uncaught in #354.
    """
    doc = _write(
        tmp_path, "a.md", f"Until 2026-07-24 the line `{_TRIGGER}` was absent.\n"
    )
    with pytest.raises(verify.VerificationError):
        verify.require_lines([doc], [_TRIGGER])


def test_require_tokens_accepts_that_same_substring(tmp_path: Path) -> None:
    """Control arm: same input, opposite verdict, so the probe discriminates.

    Without this, the test above is satisfied by a handler that fails
    everything, and the claim "substring binding is too weak here" is asserted
    rather than shown.
    """
    doc = _write(
        tmp_path, "a.md", f"Until 2026-07-24 the line `{_TRIGGER}` was absent.\n"
    )
    assert verify.require_tokens([doc], [_TRIGGER])["status"] == "passed"


def test_require_lines_normalises_whitespace(tmp_path: Path) -> None:
    """Indentation and internal runs of whitespace must not decide a verdict.

    A markdown formatter re-indenting a list item changes bytes, not meaning.
    Normalising is what keeps this handler from being a formatter tripwire.
    """
    doc = _write(tmp_path, "a.md", "   -   When   the  session model is Fable   \n")
    assert (
        verify.require_lines([doc], ["- When the session model is Fable"])["status"]
        == "passed"
    )


def test_require_lines_rejects_a_paraphrase(tmp_path: Path) -> None:
    """Normalising whitespace must not soften into normalising words."""
    doc = _write(tmp_path, "a.md", "- When the session model is Fable 5\n")
    with pytest.raises(verify.VerificationError):
        verify.require_lines([doc], ["- When the session model is Fable"])


def test_require_lines_requires_the_line_in_every_path(tmp_path: Path) -> None:
    """The union footgun is closed BY CONSTRUCTION, not by remembering to bind.

    `require_tokens`'s bare `tokens` is a union over the combined text, which
    is why `per_path_tokens` had to be retrofitted (#299) — a contract naming
    two files had no opinion about either. This handler is new, so it takes
    the strict reading as its default: a bare `lines` list must hold in EVERY
    listed path. Binding per file stays available for the asymmetric case.
    """
    present = _write(tmp_path, "a.md", f"{_TRIGGER}\n")
    absent = _write(tmp_path, "b.md", "unrelated\n")
    with pytest.raises(verify.VerificationError) as exc:
        verify.require_lines([present, absent], [_TRIGGER])
    # The file that carries it is not the complaint — only the one that does not.
    assert "b.md" in str(exc.value)
    assert "a.md" not in str(exc.value)


def test_require_lines_passes_when_every_path_carries_it(tmp_path: Path) -> None:
    """Control arm for the match-all default — it must not fail everything."""
    one = _write(tmp_path, "a.md", f"x\n{_TRIGGER}\n")
    two = _write(tmp_path, "b.md", f"{_TRIGGER}\ny\n")
    assert verify.require_lines([one, two], [_TRIGGER])["status"] == "passed"


def test_require_lines_fails_on_an_empty_path_list() -> None:
    """No files is not "nothing to check" — it is a contract pointing at air."""
    with pytest.raises(verify.VerificationError):
        verify.require_lines([], [_TRIGGER])


def test_per_path_lines_binds_a_line_to_its_file() -> None:
    """The asymmetric form, driven through the real handler and manifest keys."""
    result = verify.run_suite(
        _entry(
            handler="require_lines",
            paths=[_REAL],
            per_path_lines={_REAL: [_MODE_LINE]},
        )
    )
    assert result["status"] == "failed"
    assert _REAL in result["reason"]


def test_require_lines_is_wired_into_the_handler_map() -> None:
    """A handler nothing dispatches to is the inert declaration one level up."""
    assert "require_lines" in verify.HANDLERS
    result = verify.run_suite(
        _entry(
            handler="require_lines",
            paths=[".claude/CLAUDE.md"],
            lines=[_MODE_LINE],
        )
    )
    assert result["status"] == "passed"


# ---------------------------------------------------------------------------
# skill_eval_corpus — parsed schema plus consumer control
# ---------------------------------------------------------------------------


def _eval_corpus() -> dict[str, Any]:
    return {
        "skill_name": "codex-task-orchestration",
        "evals": [
            {
                "id": 18,
                "prompt": "Recover from a thread limit without another writer.",
                "expected_output": (
                    "Reuse one confirmed-idle agent with bounded ownership."
                ),
                "files": [],
                "expectations": [
                    "The active writer is not reused.",
                    "The idle agent receives explicit bounded ownership.",
                ],
            }
        ],
    }


def test_skill_eval_corpus_parses_and_consumes_required_eval(tmp_path: Path) -> None:
    corpus = _write(tmp_path, "evals.json", json.dumps(_eval_corpus()))

    result = verify.skill_eval_corpus(
        corpus,
        skill_name="codex-task-orchestration",
        required_eval_ids=[18],
        min_expectations=2,
    )

    assert result["status"] == "passed"


def test_skill_eval_corpus_rejects_malformed_json(tmp_path: Path) -> None:
    corpus = _write(tmp_path, "evals.json", json.dumps(_eval_corpus())[1:])

    with pytest.raises(verify.VerificationError, match="invalid JSON"):
        verify.skill_eval_corpus(
            corpus,
            skill_name="codex-task-orchestration",
            required_eval_ids=[18],
            min_expectations=2,
        )


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda value: value.update(skill_name="other"), "skill_name"),
        (lambda value: value["evals"][0].pop("expectations"), "expectations"),
        (lambda value: value["evals"][0].update(prompt=""), "prompt"),
        (lambda value: value["evals"][0].update(extra=True), "unexpected field extra"),
        (lambda value: value.update(extra=True), "unexpected root field extra"),
        (lambda value: value.update(evals=[]), "required eval id 18"),
    ],
)
def test_skill_eval_corpus_rejects_wrong_shape_or_unconsumed_required_eval(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], object],
    reason: str,
) -> None:
    payload = _eval_corpus()
    mutation(payload)
    corpus = _write(tmp_path, "evals.json", json.dumps(payload))

    with pytest.raises(verify.VerificationError, match=reason):
        verify.skill_eval_corpus(
            corpus,
            skill_name="codex-task-orchestration",
            required_eval_ids=[18],
            min_expectations=2,
        )


def test_skill_eval_corpus_handler_is_publicly_wired() -> None:
    assert "skill_eval_corpus" in verify.HANDLERS
