# LLVM release freeze gate, fix round 5

Branch: `feat/llvm-23-detect-bump`. Starting HEAD:
`b12247006a05ddc6caea2e57331cfeb82b04a7f4`. Commit:
`f2f163a96789e0bd7af2ae46c463f6393726fb58`.
Exactly one new commit was created. The pre-commit and commit-msg hooks succeeded
on the first attempt (git commit rc 0); the specified two attribution lines were
verified in the committed message. The final working tree is clean. No push.
The extra commit beyond the spec's `09e968a4` is documentation only; no code
contradiction was found. LLVM pins remain at 22. Only the two specified Python
files and the gate comment in `.devcontainer/mise-system.toml` changed.

## Final verification

| Gate | rc | Evidence |
| --- | --- | --- |
| `uv run --project python pytest tests/test_llvm_major.py -x -q -n 0` | 0 | `pytest-final.log`: 192 passed |
| `uv run --project python ruff check python/src/dotfiles_setup/llvm_major.py tests/test_llvm_major.py` | 0 | `ruff-check-3.log` |
| `uv run --project python ruff format --check python/src/dotfiles_setup/llvm_major.py tests/test_llvm_major.py` | 0 | `ruff-format-check.log` |
| `uv run --project python ty check --project python python/src/dotfiles_setup/llvm_major.py tests/test_llvm_major.py` | 0 | `ty-3.log` |
| `mise run llvm-parity` | 0 | `llvm-parity.log` |
| `mise run llvm-detect -- --json` | 4 | `live-detect-final.log`, expected held status |
| Direct live `freeze_state(22, "resolute", default_fetcher, default_gh, now=UTC now)` | 0 | `live-freeze22-final.log`, frozen true |
| Remove freeze conjunct, rerun the exact permitted pytest command | 1 | `pytest-freeze-conjunct-mutation.log`: target 23 wrongly selected instead of 22 |
| `git diff --check` | 0 | `diff-check.log` |

The mutation failed specifically in
`test_detect_requires_both_gates[23-False-22-freeze]`, after 43 passing cases.
The original conjunct was restored before the final 192-test passing run.
All invocations of pytest used the exact lane command, with no xdist workers.

## Live freeze evidence

| Major | Branch head | Latest GA | Peeled tag commit | Ahead | Apt build | Release Date UTC | Frozen |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 22 | ca7933e47d3a3451d81e72ac174dcb5aa28b59d1 | llvmorg-22.1.8 | ca7933e47d3a3451d81e72ac174dcb5aa28b59d1 | 0 | ca7933e47d3a | 2026-07-14T18:49:42+00:00 | true |
| 23 | 21ef2ddb806006eba611b8a769ae72e5f86f9418 | llvmorg-23.1.2 | 85ac560262434c9ccfc0c183ec22d4138ed647fb | 27 | 67f4a076a097 | 2026-09-22T11:37:22+00:00 | false |

Live reason:

```text
23 GA+served, held: IWYU, freeze; release/23.x 27 ahead of llvmorg-23.1.2; apt build 67f4a076a097 ≠ tag/head; built 2026-09-22
```

## Every recorded exit code

| Invocation file stem | rc |
| --- | --- |
| graphify-health | 3 |
| research-fanout | 1 |
| research-fanout-retry | 1 |
| primary-tag22 | 0 |
| primary-head23 | 0 |
| primary-compare23 | 0 |
| github-code-hit | 0 (initial expected-hit query returned 0 results) |
| github-code-absent | 0 (absent control returned 0 results) |
| github-code-hit-2 | 0 (README LLVM positive control returned 55 results) |
| ruff-format-apply | 0 |
| ruff-format-apply-2 | 0 |
| ruff-format-apply-3 | 0 |
| ruff-check-1 | 1 |
| ruff-check-2 | 1 |
| ruff-check-3 | 0 |
| ruff-format-check | 0 |
| ty-1 | 1 |
| ty-2 | 1 |
| ty-3 | 0 |
| pytest-1 | 0 (188 passed before additional HTTP status controls) |
| pytest-2 | 1 (undefined fallback diagnostic name introduced during helper cleanup, fixed) |
| pytest-3 | 0 (192 passed) |
| pytest-freeze-conjunct-mutation | 1 (expected mutation kill) |
| pytest-final | 0 (192 passed) |
| llvm-parity | 0 |
| live-detect | 4 |
| live-detect-final | 4 |
| live-freeze22 | 0 |
| live-freeze22-final | 0 |
| diff-check | 0 |
| git-add | 0 |
| git-commit-1 | 0 (registered pre-commit and commit-msg hooks both succeeded) |

Initial static failures were argument-count constraints, tuple inference, and
then the fallback diagnostic name and unused fixture parameters. All were fixed
without inline suppressions or configuration changes. Every gate rc is saved
as its own `.rc` file; output was saved without piping to tail.

## Research routes and deviations

RESEARCH INCOMPLETE: strict-five-v1 receipt rc 1, request
`01a10889-07cb-7561-894c-cc60b73ffa81`.

- GitHub issues: `empty_verified`; positive control succeeded.
- GitHub discussions: `empty_unverified`; exact blocker: `canary returned 0 items`.
- GitHub releases: `empty_verified`; positive control succeeded. Actual GA tags,
  branch heads, and comparisons were separately verified using authenticated gh.
- Exa: `ok`, 10 results, HTTP API ran.
- Context7: `ok`, 5 results, `ctx7` library/docs CLI ran.
- Firecrawl developer route: first invocation `error`, exact blocker: `HTTP 502`;
  retry `ok`, 10 results.
- Firecrawl search CLI: `error`, exact blocker: `exited 1: Error: Request failed with status code 402`.
- Last30Days: `ok`, 6 results, cached plugin Python engine with explicit plan,
  GitHub scope, and Exa web backend ran.

Stop-hook retry used the same required native strict-five command and request
ID. Latest manifest generated at `2026-10-04T20:38:16.094324+00:00`, retry rc 1.
All five provider groups were checked: GitHub discussions still failed its
canary (`canary returned 0 items`); Firecrawl search still returned HTTP 402.
Exa, Context7, Last30Days, and Firecrawl developer search succeeded; GitHub
issues/releases retained verified empty results. Research remains incomplete.

The required native fnox profile, mise research-fanout, uv, gh, curl, ruff, ty,
pytest, git, and hk ran. No app connector, MCP tool, or sub-agent ran. No separate
interactive skill workflow was invoked; the Last30Days plugin supplied its
engine to research-fanout. No credential value was printed or persisted.

Graphify returned missing (rc 3), so source files were used. Web open attempts
for both apt Release documents returned Internal Error; the native curl-backed
live checks succeeded. The research manifest records all required source arms
and the same-turn request ID; primary GitHub and apt facts were verified live.
Its directory is the output path required by the global research hook:
`/Users/rmanaloto/.codex/research-coverage/01a10888-e005-7e53-830b-86528aecf3be/01a10889-07cb-7561-894c-cc60b73ffa81/`.

No implementation deviation from the freeze spec. Lane verification overrides
were honored. No full lint, verify, other pytest path, apt-pin check, Docker,
lock-image, pin change, workflow change, or push was performed. Git 2.54's
registered config hooks run hk 2.3.0 for pre-commit and commit-msg; no hook
bypass was used.
