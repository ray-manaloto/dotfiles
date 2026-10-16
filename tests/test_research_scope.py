# Copyright (c) 2026 Raymond Manaloto
"""Public caller research-scope directive controls."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec, research_scope, sdlc_team
from dotfiles_setup.research_scope import directive, near_miss


@pytest.mark.parametrize(
    "prompt",
    [
        "Research Codex hooks",
        "> [research-scope: local-only]\nResearch Codex hooks",
        "Quoted:\n[research-scope: local-only]\nResearch Codex hooks",
        "```\n[research-scope: local-only]\n```\nResearch Codex hooks",
        " [research-scope: local-only]\nResearch Codex hooks",
        "[research-scope: local-only] trailing text\nResearch Codex hooks",
    ],
)
def test_only_exact_caller_first_line_can_declare_scope(prompt: str) -> None:
    assert directive(prompt) is None


@pytest.mark.parametrize(
    ("prompt", "scope"),
    [
        ("[research-scope: implementation]\nResearch uv", "implementation"),
        ("[research-scope: text-edit]\nReword the README", "text-edit"),
        ("[research-scope: research]\nImplement the bump", "research"),
        ("[research-scope: research]\r\nImplement the bump", "research"),
        ("[research-scope: local-only]\nInvestigate", "local-only"),
        ("[research-scope: anything]\nResearch uv", None),
        ("> [research-scope: implementation]\nResearch uv", None),
        ("Research uv\n[research-scope: implementation]", None),
        (" [research-scope: implementation]\nResearch uv", None),
    ],
)
def test_directive_is_read_only_from_exact_caller_first_line(
    prompt: str, scope: str | None
) -> None:
    assert directive(prompt) == scope


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("[research-scope: research]\nFix it.", False),
        ("Fix it.\n[research-scope: researc]", False),
        ("[research] notes", False),
        ("﻿ [Research-Scope: research]\nFix it.", True),
        ("[research-scope: bogus]\nFix it.", True),
    ],
)
def test_near_miss_flags_only_an_inexact_first_line_directive(
    prompt: str, *, expected: bool
) -> None:
    assert near_miss(prompt) is expected


# --- cg36b (D246 item 3): research intent in the caller's own prose ----------
#
# Seam: `research_scope.intent(prompt) -> bool`. True only when the human's own
# prose holds an imperative research request aimed at the assistant, at a
# sentence or clause start, optionally after "please", "kindly", "go",
# "can you", "could you", "I need you to" or "let's". The directive is read
# separately by `directive()`; intent never reads it.
#
# Only the human's own prose counts. Ignored: fenced blocks (``` and ~~~,
# unclosed fences to the end), inline code, blockquote lines (`>`), quoted
# strings (straight double, curly double, curly single), JSON lines, YAML
# `key: value` data lines (`title:`, `name:`, `TASK:`...), pasted logs and
# tracebacks, and everything after a quoted-ticket marker line. The marker set
# is exactly these bare lines: `Ticket:`, `Issue:`, `Spec:`,
# `Acceptance criteria:` and `---` (any run of three or more hyphens).
#
# Straight single quotes (round 2, lead decision): an apostrophe is not a
# quote delimiter (`Let's`, `what's`, `'tis`, `users'`). A straight
# single-quoted span exists only when the quote opens at a line start, after
# whitespace or `(`, closes before whitespace, punctuation or the line end,
# and holds no `;`, `.`, `!` or `?` followed by whitespace. A clause that
# starts inside any quote span is never a clause start, so
# `Rename the 'Research the latest uv releases' heading.` has no intent.
#
# Statements and suggestions are not requests (round 2, lead decision):
# `We should research ...` has no intent; `investigate` never binds.

_FIXTURES = Path(__file__).parent / "fixtures" / "codex_research_gate"
_CORPUS = _FIXTURES / "intent-corpus.jsonl"
_BODY = "Research the latest uv releases."
_LEAD = "Fix the README typo.\n"


def _corpus() -> list[dict[str, str]]:
    rows = [
        json.loads(line)
        for line in _CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        assert set(row) == {"prompt", "expect", "kind"}
        assert row["expect"] in {"research", "none"}
    return rows


def test_intent_corpus_is_large_and_varied() -> None:
    rows = _corpus()
    positives = [row for row in rows if row["expect"] == "research"]
    negatives = [row for row in rows if row["expect"] == "none"]
    assert len(positives) >= 30
    assert len(negatives) >= 60
    assert any("\n" in row["prompt"] for row in positives)
    assert sum("\n" in row["prompt"] for row in negatives) >= 10
    assert len({row["prompt"] for row in rows}) == len(rows)


def test_intent_corpus_has_zero_false_positives_and_full_recall() -> None:
    """Precision and recall of `intent` over the whole labelled corpus."""
    rows = _corpus()
    got = [research_scope.intent(row["prompt"]) for row in rows]
    want = [row["expect"] == "research" for row in rows]
    tp = sum(g and w for g, w in zip(got, want, strict=True))
    fp = [i for i, (g, w) in enumerate(zip(got, want, strict=True)) if g and not w]
    fn = [i for i, (g, w) in enumerate(zip(got, want, strict=True)) if w and not g]
    precision = tp / (tp + len(fp)) if tp + len(fp) else 0.0
    recall = tp / (tp + len(fn)) if tp + len(fn) else 0.0
    sys.stdout.write(
        f"intent corpus: n={len(rows)} tp={tp} fp={len(fp)} fn={len(fn)} "
        f"precision={precision:.3f} recall={recall:.3f}\n"
    )
    assert fp == [], [(i, rows[i]["kind"], rows[i]["prompt"]) for i in fp]
    assert fn == [], [(i, rows[i]["kind"], rows[i]["prompt"]) for i in fn]


@pytest.mark.parametrize(
    "prompt",
    [
        _BODY,
        _LEAD + _BODY,
        "research how Codex loads project hooks",
        "Please research the newest mise release.",
        "Can you research the current Clang P2996 status?",
        "Could you look up the uv changelog online?",
        "I need you to find the latest stable ruff version.",
        "Go research the newest Codex release.",
        "Find the latest hk release notes.",
        "Look up the fnox docs online.",
        "What is the current version of the GitHub CLI?",
        "What's new in mise 2.0?",
        "Compare the uv and Poetry docs on workspaces.",
        "Search the web for Codex Stop hook reports.",
        "Search GitHub for prior art on research gates.",
        "Fix nothing yet. Research the newest uv release first.",
        "Is that right? Search the web for the uv 0.9 notes.",
    ],
)
def test_intent_binds_an_imperative_research_request(prompt: str) -> None:
    assert research_scope.intent(prompt) is True


@pytest.mark.parametrize(
    "prompt",
    [
        "Fix the research gate.",
        "Update the research-workflow doc.",
        "After research, the parser drops rows; fix it.",
        "Rename research_fanout.py to fanout.py.",
        "Write release notes for v2.3 in CHANGELOG.md.",
        "Bump uv to the latest version.",
        "Look up the function parse_args in foo.py and add a docstring.",
        "Find the bug in the version check.",
        "Find the latest commit in this repo.",
        "Investigate the failing test.",
        "Look into the crash.",
        "Compare the two functions.",
        "Document best practices for hooks in docs/hooks.md.",
        "Do not research anything; fix the lint error.",
        "We should research the newest mise releases.",
        "We should research the latest uv releases before pinning.",
        "Can someone investigate the newest mise release?",
        "Don't search the web. Fix the test.",
        "We use research_scope.directive here.",
        "",
        "   \n\n  ",
    ],
)
def test_intent_never_binds_a_mention_or_code_local_object(prompt: str) -> None:
    assert research_scope.intent(prompt) is False


_QUOTED = {
    "backtick-fence": f"```\n{_BODY}\n```",
    "tilde-fence": f"~~~markdown\n{_BODY}\n~~~",
    "unclosed-fence": f"```text\n{_BODY}\nMore pasted text.",
    "unclosed-tilde-fence": f"~~~\n{_BODY}",
    "inline-code": f"`{_BODY}`",
    "unclosed-inline-code": f"`{_BODY}",
    "blockquote": f"> {_BODY}",
    "indented-blockquote": f"  >> {_BODY}",
    "straight-quotes": f'"{_BODY}"',
    "curly-double-quotes": f"\u201c{_BODY}\u201d",
    "curly-single-quotes": f"\u2018{_BODY}\u2019",
    "straight-single-quotes": f"'{_BODY}'",
    "json-object": f'{{"title": "{_BODY}", "id": "CG-12"}}',
    "json-array": f'["{_BODY}"]',
    "yaml-title": f"title: {_BODY}",
    "yaml-list": f"- name: {_BODY}\n  run: ./scripts/check.sh",
    "dispatch-task": f"TASK: {_BODY}\nSPEC FILE: docs/spec.md\nMODE: implement",
    "traceback": (
        "Traceback (most recent call last):\n"
        '  File "gate.py", line 3, in <module>\n'
        f"ValueError: {_BODY}"
    ),
    "log-line": f"2026-10-16T10:00:01Z INFO {_BODY}",
    "marker-ticket": f"Ticket:\n{_BODY}",
    "marker-issue": f"Issue:\n{_BODY}",
    "marker-spec": f"Spec:\n{_BODY}",
    "marker-acceptance": f"Acceptance criteria:\n- {_BODY}",
    "marker-rule": f"---\n{_BODY}",
    "marker-long-rule": f"-----\nNotes.\n\n{_BODY}",
}


@pytest.mark.parametrize("wrapped", list(_QUOTED.values()), ids=list(_QUOTED))
def test_intent_ignores_a_request_inside_quoted_material(wrapped: str) -> None:
    """The bare request binds (control); the same request quoted never does."""
    assert research_scope.intent(_LEAD + _BODY) is True
    assert research_scope.intent(_LEAD + wrapped) is False


@pytest.mark.parametrize(
    "prompt",
    [
        f"```\npasted\n```\n{_BODY}",
        f"> quoted reviewer note\n\n{_BODY}",
        f'Our pin is "0.8.0". {_BODY}',
        f'The 27" monitor is fine. {_BODY}',
        f"'tis urgent; {_BODY.lower()} See the users' guide.",
    ],
    ids=["after-fence", "after-blockquote", "after-quote", "inch-mark", "apostrophes"],
)
def test_intent_still_binds_the_caller_prose_around_quoted_material(
    prompt: str,
) -> None:
    assert research_scope.intent(prompt) is True


_BRIEF_NAMES = (
    "json-ticket-brief.txt",
    "fenced-ticket-brief.txt",
    "blockquote-ticket-brief.txt",
    "acceptance-list-brief.txt",
    "text-edit-brief.txt",
)


@pytest.mark.parametrize("name", _BRIEF_NAMES)
def test_round_fixture_briefs_quoting_research_words_have_no_intent(name: str) -> None:
    prompt = (_FIXTURES / name).read_text(encoding="utf-8")
    assert research_scope.intent(prompt) is False


def test_request_above_a_quoted_bypass_has_intent() -> None:
    prompt = (_FIXTURES / "research-with-quoted-bypass.txt").read_text(encoding="utf-8")
    assert research_scope.intent(prompt) is True


@pytest.mark.parametrize("mode", ["implement", "review"])
@pytest.mark.parametrize(
    "task",
    [
        "Implement ticket CG-36 test-first; keep research failures.",
        "Investigate the retained Codex research receipt.",
        "Implement CG-12. Ticket title: Research the latest versions of uv.",
    ],
)
def test_sdlc_brief_without_its_directive_line_has_no_intent(
    tmp_path: Path, mode: str, task: str
) -> None:
    """A rendered dispatch brief, line 1 stripped, never binds by intent."""
    request = codec.decode(
        json.dumps(
            {"spec_file": str(tmp_path / "spec.md"), "task": task, "mode": mode}
        ).encode(),
        sdlc_team.SdlcTeamRequest,
    )
    prompt = sdlc_team.build_prompt(request, tmp_path)
    first, _, body = prompt.partition("\n")
    assert first == "[research-scope: implementation]"
    assert research_scope.intent(body) is False


def _best_of_three(prompt: str) -> float:
    best = float("inf")
    for _ in range(3):
        started = time.perf_counter()
        research_scope.intent(prompt)
        best = min(best, time.perf_counter() - started)
    return best


@pytest.mark.parametrize(
    "unit",
    [
        " ",
        "\n",
        '"',
        "'",
        "`",
        "``` ",
        "~~~\n",
        "```\n",
        "Ticket:\n",
        "---\n",
        "> ",
        ">\n",
        "{[",
        "\u201c",
        "\u2018",
        "a",
        "research ",
        "Research the latest ",
        '"x ',
        "title: ",
        "- ",
        ": ",
        "\\",
    ],
)
@pytest.mark.xdist_group(name="research_scope_timing")
def test_intent_cost_is_linear_on_adversarial_input(unit: str) -> None:
    """About 200 KB stays under 0.5 s, and doubling at most about triples it."""
    small = unit * (200_000 // len(unit))
    large = small + small
    elapsed_small = _best_of_three(small)
    elapsed_large = _best_of_three(large)
    assert elapsed_small < 0.5
    assert elapsed_large < 1.0
    assert elapsed_large <= 3 * elapsed_small + 0.05


# --- round 2: straight single quotes and apostrophes ------------------------


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Rename the 'Research the latest uv releases' heading.", False),
        ("Rename the 'Research the latest uv releases.' heading.", False),
        ("Rename the heading ('Research the latest uv releases').", False),
        ("Let's research the newest mise releases.", True),
        ("what's new in mise 2.0?", True),
        ("Fix the README typo. It's urgent: research the latest uv releases.", True),
        ("'tis urgent; research the latest uv releases, see the users' guide", True),
    ],
    ids=[
        "single-quoted-heading",
        "single-quoted-sentence",
        "single-quoted-in-parens",
        "lets",
        "whats",
        "its",
        "tis-and-plural-possessive",
    ],
)
def test_straight_single_quotes_are_spans_only_around_whole_text(
    prompt: str, *, expected: bool
) -> None:
    assert research_scope.intent(prompt) is expected


# --- round 2: anti-overfit, generated from names absent from the corpus -----
#
# Every quoted-material wrapper crossed with research bodies from six verb
# families. Tool and file names are invented and asserted absent from the
# corpus, so a rule tuned to corpus words cannot pass by memory.
_UNSEEN_TOOLS = ("Plonkit", "Varnowa", "Tessaline", "Gribbleton", "Quorvex")
_UNSEEN_FILES = ("kestrel_map.py", "src/brindle/loom.rs", "tests/test_quill.py")
_UNSEEN_IDENTS = ("fold_vortex", "merge_tallow", "pack_sorrel")
_BODIES = {
    "research": "Research the newest {a} releases.",
    "find-latest": "Find the latest {a} release notes.",
    "look-up-online": "Look up the {a} changelog online.",
    "current-version": "What is the current version of {a}?",
    "compare-docs": "Compare the {a} and {b} docs on caching.",
    "search-web": "Search the web for {a} startup timeouts.",
}
_WRAPPERS = {
    "backtick-fence": "```\n{body}\n```",
    "tilde-fence": "~~~text\n{body}\n~~~",
    "unclosed-fence": "```\n{body}\nmore pasted text",
    "inline-code": "`{body}`",
    "blockquote": "> {body}",
    "straight-double": '"{body}"',
    "curly-double": "\u201c{body}\u201d",
    "straight-single": "'{body}'",
    "json-body": '{{"title": "{body}", "id": "X-9"}}',
    "yaml-body": "title: {body}\nowner: someone",
    "yaml-list": "- name: {body}\n  run: ./x.sh",
    "traceback": (
        "Traceback (most recent call last):\n"
        '  File "{file}", line 9, in <module>\n'
        "RuntimeError: {body}"
    ),
    "log-line": "2026-10-16T11:02:03Z WARN {body}",
    "marker-ticket": "Ticket:\n{body}",
    "marker-issue": "Issue:\n{body}",
    "marker-spec": "Spec:\n{body}",
    "marker-acceptance": "Acceptance criteria:\n- {body}",
    "marker-rule": "---\n{body}",
}


def _generated_cases() -> list[tuple[str, str, str]]:
    cases = []
    for index, (family, template) in enumerate(_BODIES.items()):
        tool = _UNSEEN_TOOLS[index % len(_UNSEEN_TOOLS)]
        other = _UNSEEN_TOOLS[(index + 1) % len(_UNSEEN_TOOLS)]
        body = template.format(a=tool, b=other)
        file = _UNSEEN_FILES[index % len(_UNSEEN_FILES)]
        lead = f"Fix the typo in {file}.\n"
        for name, wrapper in _WRAPPERS.items():
            wrapped = wrapper.format(body=body, file=file)
            cases.append((f"{family}-{name}", lead + body, lead + wrapped))
    return cases


_GENERATED = _generated_cases()


def test_generated_names_are_absent_from_the_corpus() -> None:
    text = _CORPUS.read_text(encoding="utf-8").casefold()
    for name in (*_UNSEEN_TOOLS, *_UNSEEN_FILES, *_UNSEEN_IDENTS):
        assert name.casefold() not in text
    assert len(_GENERATED) >= 5 * len(_WRAPPERS)


@pytest.mark.parametrize(
    ("bare", "wrapped"),
    [(bare, wrapped) for _, bare, wrapped in _GENERATED],
    ids=[case_id for case_id, _, _ in _GENERATED],
)
def test_generated_request_binds_bare_and_never_when_quoted(
    bare: str, wrapped: str
) -> None:
    assert research_scope.intent(bare) is True
    assert research_scope.intent(wrapped) is False


_NEGATIVE_TEMPLATES = (
    "Fix the {a} research gate.",
    "Update the {a} research-workflow doc.",
    "After research, {file} drops empty rows; fix it.",
    "Rename research_{ident}.py to {ident}.py.",
    "Bump {a} to the latest version.",
    "Write release notes for {a} 2.1 in CHANGELOG.md.",
    "Look up the function {ident} in {file} and add a docstring.",
    "Find the bug in {file}.",
    "Find the latest commit in this repo that touched {file}.",
    "Investigate the failing test for {ident}.",
    "Look into the crash in {a}.",
    "Compare the two functions in {file}.",
    "What is the current version of the schema in {file}?",
    "Search the codebase for callers of {ident}.",
    "We should research the newest {a} releases.",
    "Do not look up the {a} docs; just fix {file}.",
)


@pytest.mark.parametrize(
    "prompt",
    [
        template.format(
            a=_UNSEEN_TOOLS[index % len(_UNSEEN_TOOLS)],
            file=_UNSEEN_FILES[index % len(_UNSEEN_FILES)],
            ident=_UNSEEN_IDENTS[index % len(_UNSEEN_IDENTS)],
        )
        for index, template in enumerate(_NEGATIVE_TEMPLATES)
    ],
)
def test_generated_mention_or_code_local_prompt_never_binds(prompt: str) -> None:
    assert research_scope.intent(prompt) is False


# --- cg36b round 2 (lead decisions 1-4) -------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "Implement CG-12: Research the latest versions of uv and poetry.",
        "Ticket: Research the latest uv releases and pin them.",
        "Issue #12: Research the latest uv releases.",
        "Fix as specified.\nSpec: research the latest Codex hooks schema; update it.",
        "Fix the import order.\n// TODO: research the newest ruff release",
        "Fix the import order.\n- FIXME: research the newest ruff release",
        "story: Research the newest mise release.",
        "BUG: research the latest hk release",
        "Note: research the latest hk release before the next pin.",
        "Acceptance: research the newest uv release.",
        (
            "Here is the plan from the ticket\n- [ ] Research the latest uv releases\n"
            "- [x] Pin uv in mise.toml"
        ),
    ],
)
def test_text_after_an_inline_ticket_label_is_quoted_material(prompt: str) -> None:
    """Decision 1: a ticket id or a closed label word quotes the rest of its line."""
    assert research_scope.intent(prompt) is False


@pytest.mark.parametrize(
    "prompt",
    [
        "- Research the latest uv releases.",
        "Two things: research the latest gitleaks release.",
        "Research: latest mise releases and their breaking changes.",
        "Research the latest uv releases: focus on breaking changes.",
    ],
)
def test_plain_bullets_and_other_labels_stay_caller_prose(prompt: str) -> None:
    assert research_scope.intent(prompt) is True


@pytest.mark.parametrize(
    "prompt",
    [
        "Research findings:\n- uv 0.9 dropped Python 3.8.\nPin uv to 0.8.",
        "Implement the pin.\n\nResearch:\n- uv 0.9 is out",
        "Research plan:\n1. Read the spec.\n2. Implement.",
        "Research question: why does the parser drop rows? Fix it.",
        "Research the newest uv releases:\n- 0.9\n- 0.8",
        "## Research the latest uv releases",
        "Research done, now fix the parser.",
        "Research complete. Implement option B.",
        "Research isn't needed; fix the parser.",
        "Research notes are in the wiki; fix the parser.",
        "Research notes",
        "Research done",
    ],
)
def test_headings_and_status_lines_are_never_requests(prompt: str) -> None:
    """Decision 2: a line ending in `:`, a `#` heading or a status line."""
    assert research_scope.intent(prompt) is False


@pytest.mark.parametrize(
    "prompt",
    [
        "Research the failing test in tests/test_currency.py.",
        "Research the crash in handoff.py.",
        "Research why test_currency fails and fix it.",
        "Research the flaky retry logic in this repo.",
        "Do some research on the parser in the codebase.",
        "Search the web for the error that scripts/check.sh prints.",
        "Search GitHub for the message in the PR.",
        "Look up the latest uv pin in mise.toml.",
        "Check the latest uv pin in the branch.",
        "Compare the uv and Poetry docs in the repo.",
        "What's new in docs/hooks.md?",
        "Check the latest review comments and address them.",
        "Find the latest handoff note and read it.",
        "Check the current status of the lanes.",
        "Compare expected and actual.",
        "Compare before and after.",
        "Compare red and green runs in the log.",
    ],
)
def test_a_local_object_never_binds_any_verb_family(prompt: str) -> None:
    """Decision 3: a path, an identifier or `in this repo` makes the object local."""
    assert research_scope.intent(prompt) is False


@pytest.mark.parametrize(
    "prompt",
    [
        "Fix the README example.\n````md\n```\nResearch the latest uv releases.\n````",
        "Fix the snippet.\n```\ncode\n```python\nResearch the latest uv releases.\n```",
        "Fix it.\n~~~~\n~~~\nResearch the latest uv releases.\n~~~~",
        "Fix it.\n```\n~~~\nResearch the latest uv releases.\n```",
    ],
    ids=["short-closer", "info-string-closer", "short-tilde-closer", "other-char"],
)
def test_a_fence_closes_only_per_commonmark(prompt: str) -> None:
    """Decision 4: same character, at least the opener's length, no info string."""
    assert research_scope.intent(prompt) is False


def test_a_longer_closer_ends_the_fence() -> None:
    prompt = "Fix it.\n```\ncode\n`````\nResearch the latest uv releases."
    assert research_scope.intent(prompt) is True


def test_intent_reads_only_the_first_32_kib() -> None:
    """Decision 4: a request past 32 KiB of other prose is never read."""
    filler = "Fix the typo.\n"
    inside = filler * (30_000 // len(filler))
    outside = filler * (33_000 // len(filler))
    assert research_scope.intent(inside + _BODY) is True
    assert research_scope.intent(outside + _BODY) is False


# --- cg36b round 3 (lead items 2 and 4) -------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "fix(hooks): research the latest hk release",
        "feat: research the newest uv release",
        "chore(deps)!: research the latest uv pin",
        "Fix the import order.\n- docs: research the latest ruff release",
        "Squash these.\nrefactor(scope): research the newest mise release",
    ],
)
def test_a_conventional_commit_subject_is_quoted_material(prompt: str) -> None:
    """Item 2: `type(scope)!:` at a line start quotes the rest of the line."""
    assert research_scope.intent(prompt) is False


@pytest.mark.parametrize(
    "prompt",
    [
        "Goal: research the latest uv releases.",
        "Plan: research the newest mise release.",
    ],
)
def test_goal_and_plan_labels_stay_caller_prose(prompt: str) -> None:
    assert research_scope.intent(prompt) is True


@pytest.mark.parametrize(
    "prompt",
    [
        "Look up the releases of astral-sh/uv.",
        "Look up https://docs.astral.sh/uv/ for the resolver flags.",
        "Compare Node.js and Deno docs.",
        "Could you find the latest version of the actions/checkout action?",
        "Research the @types/node 22 release.",
    ],
)
def test_a_slug_url_or_library_name_is_an_upstream_object(prompt: str) -> None:
    """Item 4: an owner/repo slug, a URL or a capitalised dotted name is upstream."""
    assert research_scope.intent(prompt) is True


@pytest.mark.parametrize(
    "prompt",
    [
        "Find the latest commit in src/app/main.py.",
        "Research the crash in ./tools/run.",
        "Research why ../shared/lib breaks the build.",
        "Research why ~/bin/fmt fails.",
        "Research the failure in /usr/local/bin/hk now.",
        "Research the failure in src/app/lib now.",
        "Research why config.toml rejects the key.",
        "Research why README.md renders badly.",
        "Research why Cargo.toml pins serde.",
        "Research the src/ layout.",
        "Research why .env is ignored.",
    ],
)
def test_a_rooted_deep_or_file_path_is_local(prompt: str) -> None:
    """Item 4: a rooted path, two slashes or a file name with an extension."""
    assert research_scope.intent(prompt) is False
