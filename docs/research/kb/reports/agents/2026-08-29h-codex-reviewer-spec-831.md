# Agent report: codex-reviewer — cold review of the #831 SPEC (not a diff)

Session: 2026-08-29h.

## Brief

Cold review task — a SPEC review, not a diff review. Read the spec at
`gh issue view 831`. Read the actual current source of
`session_state.py`/`handoff_check.py` and their tests to ground the review.
No implementation exists yet. Critique for: internal inconsistency vs real
code, underspecified decisions, testability of Testing Decisions, scope
gaps between User Stories and Implementation Decisions, and whether Out of
Scope is actually clean. Report findings as severity + claim + citation.

## Report (verbatim, draft-1 review — before the respec)

# Spec Review — Issue #831

Grounded against `python/src/dotfiles_setup/session_state.py`, `python/src/dotfiles_setup/handoff_check.py`, `tests/test_session_state.py`, `tests/test_handoff_check.py` (all read in full above). No implementation exists yet; this critiques the spec text only.

## Findings

**HIGH — the regex change as specified mechanically breaks the exact regression test the spec says stays "unchanged".**
Implementation Decisions bullet 2 says: make the citation pattern's `\.[A-Za-z]\w*` extension requirement optional (`?`), leaving `[\w./-]+(?:\.[A-Za-z]\w*)?:digits`. Testing Decisions then says to "re-run the existing false-positive guards (`test_check_ignores_numeric_ratios_as_path_citations` …) unchanged, since they're the regression guard for widening this regex." These two statements are internally inconsistent: with the extension made fully optional, the string `"load 13.5:2, ratio 2.5:1"` (the literal fixture in `tests/test_handoff_check.py:87`) now satisfies `[\w./-]+` (which already includes `.`) immediately followed by `:digits`, with no extension segment needed — so `13.5` and `2.5` become citation matches producing `MISSING_PATH` findings, and the existing assertion `== []` fails. The spec's own hedge ("recheck them against the widened pattern since making the extension optional changes what the pattern can match at its start") acknowledges the risk but doesn't resolve it, and the Testing Decisions section states the wrong expected outcome (unchanged) for a test that the chosen mechanism guarantees will need to change or the mechanism itself needs to change. Citation: spec "Implementation Decisions" bullet 2 vs "Testing Decisions" bullet 2, against `tests/test_handoff_check.py:84-87`.

**HIGH — underspecified disambiguation mechanism; two implementers would build incompatible fixes.**
The spec never states *how* to distinguish an intended extensionless-file citation (`Makefile:10`) from the same shape occurring in ordinary prose that isn't a citation at all: aspect ratios (`13.5:2`), clock times (`14:30`), and `host:port` pairs (`localhost:3000`, common in this repo's own docs about devcontainer SSH ports) all match `bareword:digits` exactly as well as `Makefile:10` does. "Recheck them against the widened pattern" names the risk but pins no mechanism (e.g., require a path separator, maintain an explicit extensionless allowlist, require the bareword to contain a letter and not be purely numeric, etc.). Each of those produces a materially different set of accepted/rejected citations. This is exactly the "two implementers could build different, incompatible things" case. Citation: spec "Implementation Decisions" bullet 2 (no allowlist, no disambiguation rule given).

**MEDIUM — User Story 1 claims the whole snapshot is protected; the Implementation Decision only touches `_git`, leaving the PR read (`_gh`) unscrubbed.**
User Story 1: "I want the snapshot to describe the actual repo I'm standing in, so that a handoff built from it isn't silently describing the wrong branch/commits/**PR**." But Implementation Decisions only modifies `_git`'s `subprocess.run` call; `_gh` (`session_state.py:141-159`) is a separate function with its own `subprocess.run(["gh", *args], cwd=repo_root, ...)` and is never mentioned. `gh pr list` resolves repo/remote context partly through the local git state, so a `GIT_DIR`/`GIT_WORK_TREE` pointing at a decoy repo can plausibly still redirect the PR lookup even after `_git` is fixed. The Testing Decision for this story matches the narrower (branch/commits-only) implementation ("asserts the snapshot still describes the target repo (branch/commits), not the decoy" — PR state not mentioned), so the spec is internally consistent with itself on this narrower scope, but that scope contradicts the "PR" clause in its own User Story 1. Citation: spec "User Stories" #1 vs "Implementation Decisions" bullet 1 and "Testing Decisions" bullet 1, against `session_state.py:141-159`.

**LOW/informational — env-var scrub list may be incomplete for the stated threat model.**
The fix removes only `GIT_DIR`/`GIT_WORK_TREE`. Git also honors `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, and `GIT_COMMON_DIR` for redirecting reads to a different repo's data even with `GIT_DIR`/`GIT_WORK_TREE` absent. The spec may be deliberately scoped to the two vars named in the linked cold-review finding (unverified — I did not read #829 itself), but the spec text doesn't say so explicitly, so a reader can't tell "deliberately scoped" from "incomplete enumeration." Citation: spec "Implementation Decisions" bullet 1.

**LOW — the OSError widening in `main()` has a larger blast radius than User Story 3 describes, undocumented.**
User Story 3 frames the gap narrowly: the *handoff file itself* "gets deleted or becomes unreadable between the tool's existence check and its read." But `check(repo_root, text)` (`handoff_check.py:153-155`) also calls `candidate.read_text(errors="replace")` inside `_path_findings` (`handoff_check.py:89`) for every *cited* file, not just the handoff file — and that call sits inside the same widened `try/except` in `main()`. So the fix as specified also silently converts a permission error or race on a *cited* file into the same one-line message, which may be desirable but is a behavior the spec doesn't claim, test, or flag as intentional. Citation: spec "Implementation Decisions" bullet 3 vs `handoff_check.py:89,193-197`.

**Non-issue, checked and passed:** all four "prior art" test names cited in Testing Decisions (`test_gather_reads_real_git_state_without_pr`, `test_check_reports_missing_paths_and_bad_line_ranges`, `test_check_ignores_numeric_ratios_as_path_citations`, `test_check_ignores_mise_flags_and_documented_cross_repo_tasks`, `test_session_state_main_reports_git_log_failure_without_traceback`) exist verbatim in the two test files. The "Out of Scope" boundary (the 5 unverified #829 findings) is clean — nothing in the three in-scope items depends on them.

## Summary for the caller

The two HIGH findings both concentrate on the same Implementation Decision (the citation-regex change) and are the ones worth resolving before implementation starts — the spec currently describes a fix that, taken literally, breaks its own regression test and leaves the disambiguation mechanism to the implementer's judgment. The MEDIUM finding is a real scope question (does "the snapshot" in User Story 1 include PR state or not) that should be resolved explicitly one way or the other rather than left implicit in the asymmetry between the story and the implementation/testing decisions.

## Architect's refutation pass — all confirmed, respec issued

Refuted none of the 5 findings — all checked out on re-read. #831 corrected in
one respec round (allowlist/subdirectory-scoped regex, `_gh` brought into
scope, env-var scrub list widened, new boundary test added). See the
corrected #831 body itself for the resulting text.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — reviewed issue #831 (draft 1) against real source
