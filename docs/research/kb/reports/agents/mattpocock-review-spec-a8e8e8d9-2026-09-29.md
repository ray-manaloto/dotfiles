# Spec review — a8e8e8d9 vs docs/specs/s28b-1-p2996-single-literal.md (2026-09-29)

Lens: spec conformance (mattpocock code-review "Spec" axis). Read-only except this file.
Diff: `git diff a8e8e8d9~1...a8e8e8d9` (one commit). Ratified rulings Q1–Q5 applied.

## Progress log

- Read spec (386 lines) and full non-doc diff.
- renovate.json: clang packageRule is the LAST entry of `packageRules` (after `image-build inputs` [0] and the
  digest-automerge rule [3]); matches §3.3 placement "the end of `packageRules`".

- Ran the new gate: `pytest tests/test_p2996_single_literal.py` gave 8 passed, rc=0.
- Fail arms, run in a scratch copy with `REPO_ROOT` patched: rule moved to index 0 FAIL; rule moved between the image
  group and the digest rule FAIL; old matchString FAIL; Dockerfile default re-added FAIL (baseline all PASS).
- `mise run token-check -- .devcontainer/Dockerfile "\nARG CLANG_P2996_REF\n"`: binds 1x, rc=0.
- `gh api .../commits/p2996` returns `f17c8d6c…b51b6e` (rc=0), which equals the bake default. The bogus-branch control
  returned rc=1, so the probe discriminates. That SHA appears in only one non-doc file (`docker-bake.hcl:102`).
- Dockerfile: the `ARG CLANG_P2996_REF` (`:428`) and the guard RUN (`:465`) are both in stage `clang-builder-cold`
  (`:417`), with no FROM between them. The guard is the first command of the fetch RUN, and its text is byte-identical
  to Q1.
- The rendered OK line in `_TIER3_COMPILER_BODY` echoes the exact §3.6 text, and the `matches pinned CLANG_P2996_REF`
  substring is intact.
- Stale-prose grep (`git grep` for `lockstep|auto-bump|scheduled|untracked|ARG only` near p2996, docs excluded). The
  control is that the same grep also hits the NEW lines in the Dockerfile, refresh.yml and AGENTS.md.

## Findings

**(a) Missing / partial**

1. Objective: "Correct every piece of prose that claims a scheduled refresh or two-file lockstep."
   `.claude/skills/tool-currency-check/SKILL.md:74` and its mirror `.agents/skills/tool-currency-check/SKILL.md:74`
   still say: "Renovate `git-refs` datasource — Dockerfile `ARG` only; bake's default is untracked (#1434)". After this
   commit that statement is exactly inverted: bake only, and the Dockerfile has no literal. The row also still lists
   `refresh.yml` `p2996-refresh` as the custom thing being replaced. §2's F-list missed this file, so the gap is in the
   spec as well as the diff. It still fails the stated objective and tool-currency rule 5, which Q4 cites.
2. I6: "records the command, its rc and its output in the PR body". There is no PR yet. The commit message gives only
   a summary ("gh api + p2996-refresh agree; bogus-branch control 422"). Carry the evidence into the `ship` PR body.

**(b) Scope creep**

3. F12 asked only to change the `CLANG_P2996_REF` clause. The diff also rewrites the rest of the `refresh.yml` row:
   "its platform set is derived from the committed lock, never fixed at one" became "derives its platforms", and
   "**auto-merges**" became "opens auto-merging PRs". The Q4 size-neutral ruling explains this (11,979 → 11,926 chars),
   but it loses the "never fixed at one" invariant. Minor.
4. F11 adds "Do not re-wire a second scheduled writer here." It is harmless and consistent with §3.8.

**(c) Implemented but looks wrong**

5. None that are behavioural. §3.6 specifies a single-line `echo "…"`. The code splits it with a Python `\`
   continuation, so the generated shell reads `…CLANG_P2996_REF ""(build==pin…)"`. The shell output is identical, but
   the generated script has a cosmetic `""` seam. Cosmetic only.

Everything else matches the spec: renovate rule order (last packageRule, after `[0]` and the digest rule `[3]`),
manager JSON, suites token, tests 1–8 including fixtures, TEST-INDEX, the p2996_refresh docstring, mise.toml,
P2996-CACHE.md, and pyproject unchanged (Q5).

## GitHub repos touched

- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996): `gh api commits/p2996` head check, plus the
  bogus-branch control.
