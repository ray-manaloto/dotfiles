# LLVM fix round 1 — execution report

Commit: `4b56cf59798ce18bf31ec6b685bde02041f3e643` (`fix(llvm): validate snapshot pins and refuse ambiguous bump plans`).
Branch: `feat/llvm-23-detect-bump`. Exactly one commit relative to dispatch HEAD `21b0b4ee9a4da07ed0e5d3939bc50fcb1a923627`. Normal pre-commit and commit-msg hooks passed for commit and amendment. Never pushed; clean worktree.

## Implementation

- F1/F2: LLVM membership uses the exact ratified apt.llvm.org signature; mixed signature-bearing versions and name majors fail. `llvm_pins` first validates with `pinned_major`.
- F3: prefix/comment/assignment whitespace is restricted to spaces and tabs.
- F4: public planner checks parity before planning; every rewrite has a required count, including per-name pin counts. ARG trailing whitespace is preserved.
- F5/F6: comments distinguish current-major apt-repo regeneration from llvm-bump, describe dual-arch checking at bump time, and name the toolchain without a fixed major.
- F10: tied newest IWYU builds must agree on their libllvm major, independent of API order, on each architecture.
- F12: apt-repo default major resolves from its dispatched root.
- Only four specified files changed. TOML changes are comments only. All pin values/keys, _.path, Dockerfile ARG and Renovate bytes are unchanged. Assertions in all 28 existing test functions are AST-identical; fixture data now includes snapshot signatures. 42 new parametrized cases bring targeted pytest to 108 passing tests.

## Exit codes — all attempts

Every code below was written to its `.rc` file and read back. Command logs, where present, share the corresponding filename stem. Staging and invariant results also appear in the tool transcript; the mutation driver code is recorded from its tool result.

| Receipt | rc |
|---|---|
| `llvm23-fix1-amend.rc` | 0 |
| `llvm23-fix1-assertions.rc` | 0 |
| `llvm23-fix1-commit.rc` | 0 |
| `llvm23-fix1-detect.rc` | 4 |
| `llvm23-fix1-diff-check.rc` | 0 |
| `llvm23-fix1-diff-check2.rc` | 0 |
| `llvm23-fix1-format-apply.rc` | 0 |
| `llvm23-fix1-format-apply2.rc` | 0 |
| `llvm23-fix1-format-apply3.rc` | 0 |
| `llvm23-fix1-format-check.rc` | 0 |
| `llvm23-fix1-format-final.rc` | 0 |
| `llvm23-fix1-format-final2.rc` | 0 |
| `llvm23-fix1-invariants.rc` | 0 |
| `llvm23-fix1-mutation-driver.rc` | 1 |
| `llvm23-fix1-mutation.rc` | 2 |
| `llvm23-fix1-parity.rc` | 0 |
| `llvm23-fix1-plan22.rc` | 0 |
| `llvm23-fix1-postcommit.rc` | 0 |
| `llvm23-fix1-pytest-final.rc` | 0 |
| `llvm23-fix1-pytest-final2.rc` | 0 |
| `llvm23-fix1-pytest.rc` | 0 |
| `llvm23-fix1-receipt-validation.rc` | 1 |
| `llvm23-fix1-research.rc` | 1 |
| `llvm23-fix1-ruff-final.rc` | 0 |
| `llvm23-fix1-ruff-final2.rc` | 0 |
| `llvm23-fix1-ruff.rc` | 1 |
| `llvm23-fix1-ruff2.rc` | 1 |
| `llvm23-fix1-stage.rc` | 0 |
| `llvm23-fix1-stage2.rc` | 0 |
| `llvm23-fix1-ty-final.rc` | 0 |
| `llvm23-fix1-ty-final2.rc` | 0 |
| `llvm23-fix1-ty.rc` | 0 |

## Final results and intermediate failures

- Final targeted pytest: 108 passed, rc 0. Ruff, format check and ty: rc 0. Only tests/test_llvm_major.py ran.
- llvm-parity: rc 0. llvm-detect --json: rc 4, pinned/target 22, newest GA 23, 23 served and held on IWYU. llvm-bump --dry-run --major 22: rc 0, 58 pins (52 active, 6 commented), both arches, empty diff.
- F1 mutation added a name filter excluding libbolt. New raising cases failed with DID NOT RAISE; pytest rc 2 reflects xdist interruption with -x. Source restored byte-for-byte and independently checked. The mutation driver initially assumed rc 1 and therefore exited 1; this was an exit-code assumption error, not an undetected mutation.
- Initial Ruff rc 1 came from forcing package config and bypassing root test configuration, plus local style issues. Second Ruff rc 1 found a non-raw regex expectation. Both causes were fixed; all subsequent checks passed without suppressions.
- First commit was amended after restoring two existing expected-version assertions; final history still contains one commit. New F4 tests opt into the realistic snapshot fixture without changing old assertions.
- Native hk_audit --check passed in both commit attempts. No hk-audit regeneration was needed.
- Full pytest, mise run lint, mise run verify, verify-apt-pins, and Docker were not run. Native pre-commit additionally ran its normal checks, including whole-project ty. No hook bypass or HK_SKIP setting was used.

## Research provenance and primary verification

Skill applied: project research-sweep in-lane path. No subagents, connector apps, MCP routes, Exa MCP plugin, or Firecrawl MCP plugin were invoked. The fanout ran the required native fnox profile and prescribed dotfiles-research-gate checkout under this turn ID. Actual routes: GitHub gh REST/GraphQL issues/discussions/releases; Exa HTTP API; Context7 ctx7 library/docs CLI; Firecrawl developer HTTP API and firecrawl search CLI; Last30Days Python CLI with explicit web/github plan and Exa web backend.

Manifest: [manifest.json](/Users/rmanaloto/.codex/research-coverage/01a0ffd0-70c0-78a1-8848-25bcdace17cd/01a0ffd0-77b6-7de3-a1ce-5ca9e33ed0c8/manifest.json). Both fanout and independent strict-five validation returned rc 1.

| Source | Status | Items | Reason |
|---|---|---|---|
| github-issues | empty_verified | 0 |  |
| github-discussions | empty_unverified | 0 | canary returned 0 items |
| github-releases | empty_verified | 0 |  |
| exa | ok | 10 |  |
| context7 | ok | 5 |  |
| firecrawl-developer | ok | 10 |  |
| firecrawl-search | ok | 10 |  |
| last30days | ok | 5 |  |

RESEARCH INCOMPLETE: github-discussions did not complete. Exact route status: empty_unverified; exact blocker: canary returned 0 items. The failed receipt remains intact; it is not counted as a successful five-provider audit.

Primary verification: live project entrypoints consumed LLVM GitHub releases, apt.llvm.org dual-arch package indexes and Release files, Ubuntu metadata, and [conda-forge IWYU file metadata](https://api.anaconda.org/package/conda-forge/include-what-you-use/files). [Python re documentation](https://docs.python.org/3/library/re.html#re.subn) confirms counted substitutions; its whitespace documentation confirms that newline is included in \s. [apt.llvm.org](https://apt.llvm.org/) and [its build docs](https://apt.llvm.org/building-pkgs.php) were read.

Additional failed read routes: web reader returned Internal Error for the Anaconda files endpoint and LLVM issue 216102. The live detector successfully consumed Anaconda metadata through the actual curl entrypoint. The issue was not used for a final claim.

## Deviations

No final implementation, file-scope, pin, or gate-exclusion deviation. The required research receipt remains incomplete for the named Discussions blocker. Intermediate Ruff invocation/style failures and mutation-driver exit-code assumption are recorded above. The initial commit was amended to preserve existing assertions; the final branch contains exactly one attributed commit.

## Stop-hook research retry

Re-ran the prescribed native fnox/mise strict-five command for request `01a0ffd0-77b6-7de3-a1ce-5ca9e33ed0c8`. The prior full receipt is preserved at `.agent/kb/raw/llvm23-fix1-research-first-attempt/`; the prescribed manifest path now contains the retry.

- Fanout: `.agent/logs/llvm23-fix1-research-retry.rc` = 1.
- Independent strict-five validation: `.agent/logs/llvm23-fix1-receipt-retry-validation.rc` = 1.
- Native fnox + authenticated gh GraphQL repository Discussions control: `.agent/logs/llvm23-fix1-discussions-control.rc` = 0; `llvm/llvm-project` returned `discussions.totalCount = 0`.
- GitHub issues/releases: `empty_verified`; Discussions: `empty_unverified`, exact blocker `canary returned 0 items`.
- Exa: ok, 10 items; Context7: ok, 5; Firecrawl developer/search: ok, 10 each; Last30Days: ok, 4.
- All eight arms and five provider groups were inspected. GitHub group remains incomplete because its required Discussions positive canary is empty. No research-complete claim.
- Commit remains `4b56cf59798ce18bf31ec6b685bde02041f3e643`; worktree clean; no code or commit changes and no push.
