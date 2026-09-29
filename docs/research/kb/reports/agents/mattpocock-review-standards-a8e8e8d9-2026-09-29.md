# Standards review — a8e8e8d9 (S28b-1 p2996 single literal)

Reviewer: mattpocock code-review Standards lane (read-only). Diff: `git diff a8e8e8d9~1...a8e8e8d9`, 16 files. Tool-enforced checks skipped (lint/pytest/verify/pin-actions reported rc=0).

## Documented-standard violations

1. **`tests/test_p2996_single_literal.py:14,20` — private import used as the source of truth.** It uses `from dotfiles_setup.p2996_hash import _extract_bake_variable`. A public `p2996_refresh.read_pinned_ref(repo_root)` (`p2996_refresh.py:127`) already does exactly this. Standard: `tests/AGENTS.md` § "What a good test is here" says tests go "through a public interface … never through implementation details". **Moderate.** `test_p2996_hash.py` sets a precedent for importing it, but that file is the unit test of `p2996_hash`; this one isn't.
2. **`p2996_refresh.py` kept as a second writer next to Renovate (judgement call, leaning violation).** The docstring change relabels it as a "manual/emergency path", but it doesn't say why Renovate's native routes can't cover that case (a Dependency Dashboard checkbox or a manual run). Standard: `.claude/rules/tool-currency-and-native-first.md` rules 3 and 6 say to retire custom code a native feature supersedes, or justify keeping it in writing.

## Probe / control-arm judgement calls (`probes-need-a-control-arm.md`, `tests/AGENTS.md`)

3. **`test_no_file_assigns_a_sha_literal_to_clang_p2996_ref` only asserts `matches == []`.** Nothing in the test proves the regex hits a known-bad line such as `ARG CLANG_P2996_REF=<sha>`. It was mutation-armed once during implementation, but that arm isn't carried on every run (rule 9). Tests 5 and 6 do carry fixture arms, so this is inconsistent.
4. **`_tracked_nondoc_files` silently skips files.** `except OSError: continue` plus `errors="ignore"` is a silent bound: unreadable means unchecked (rule 3).

## Smells

5. **Duplicated Code / Shotgun Surgery.** The "Renovate is the automatic path; don't re-wire a second writer" story is restated in seven places: the Dockerfile comment, `refresh.yml`, the `p2996_refresh` docstring, `P2996-CACHE.md` (twice), the `workflows/AGENTS.md` row, the `mise.toml` description and the `renovate.json` descriptions. The next policy change has to touch all of them, and this is the same drift class that caused #904 (stale "lockstep" comments).
6. **Duplicated work.** `_tracked_nondoc_files` reads each file to test readability and throws the text away; both callers then read it again. `renovate.json` is also parsed twice (in `_clang_manager` and in test 8).
7. **Mysterious Name / Primitive Obsession.** In `test_clang_package_rule_leaves_the_image_group_after_it`, the `digest_index` rule is found by an exact list: `rule.get("matchUpdateTypes") == ["minor", "patch", "digest"]`. That breaks on reorder. The test name also reads ambiguously.
8. **Speculative config (low).** `"automergeType": "pr"` and `"platformAutomerge": true` are Renovate defaults. They are pinned by test 8, which makes the defaults look load-bearing.
9. **Obscure construct (low).** In `image.py:665`, the shell echo is split as `"…REF "\` followed by a new line starting `"(build==pin …)"`. It works through Python's backslash-newline elision plus shell string concatenation. A shorter message would read more clearly.

No `2>/dev/null`, bash-budget or `do-not.md` breaches. The Dockerfile's fail-loud `test -n` guard follows the build-time self-check convention.

## GitHub repos touched

_None._ (Local repository only.)
