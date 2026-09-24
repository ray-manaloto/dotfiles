# Session audit — dismissed errors and repeated mistakes (Brief M′), 2026-09-24

**Scope.** Session `94aea797`: the main transcript (2467 lines) plus 7 subagents. `aded8784` is this lane. Probes run
over tool results: `is_error`, `rc=[1-9]`, `DRIFT|WARN|denied`, and dismissive wording in assistant blocks.
**Control.** The deny grep matched the session's deliberate guard-deny probe (L2312) and found 0 real denials.

## Dismissed, unrecorded, or recorded wrongly

**F1: MEDIUM. A glob gap let a lint-red commit through.**
- **Claim.** The `agnix` hk step's glob (`hk.pkl:555-561`) omits `tests/**/*.md`, so pre-commit let `d4b0b5c4`
  commit a lint-red tree: an agnix warning at `tests/TEST-INDEX.md:66` (L2272; fixed at L2280).
- **What the report records.** Only the symptom ("the pre-commit did not catch"). It records no cause and no fix.
- **Control.** `mise run lint` (check --all) caught it (L2263, rc=1).
- **FIX-NOW.** Add `"**/*.md"` to that glob. The check is already `agnix .`, which scans the whole repo.
- **Arm.** Stage only a `TEST-INDEX.md` line containing `~/.claude/`. `hk run pre-commit` must then fail.

**F2: LOW. The session left the dotfiles graph stale and did not record it.**
- **Claim.** The graph was `fresh` at the start (L147). It is `stale` at the end. Neither the report nor the Owed
  actions mention it.
- **Evidence.** Subagent `a5c9176b` L34 and `a5f7d315` L60 got rc=3. Live, now: rc=3 at `15662741`, 43 corpus files.
- **Control.** The same task returned `fresh` at L147.
- **PLAN** (add to Owed actions): "After land, run `mise run graphify-rebuild`. The graph has been stale since
  `3db81d8e`."

**F3: LOW. A repeated mistake that was never recorded.** Scripted string-surgery edits went to the gate without
being formatted first.
- **How often.** At least 9 lint, format or ty failures across both repos: L566, L581, L1261, L1270, L1408, L1603,
  L1630, L2176 and L2185.
- **The worst case is L1408.** A block cut deleted `REDACTION_CANARY`, which caused F821 and a `NameError`.
- **A related slip.** The session ran `kb-check` on a `tests/test_cli.py` that does not exist (L2176, then L2184).
- **Status.** Every instance was fixed before commit.
- **PLAN** (Standing traps): "After a scripted edit, run `mise run fmt` in dotfiles or
  `mise run kb-check -- <paths>` in knowledge-base before the full gate. After cutting a block, grep for the names it
  defined." No /grilling is needed.

**F4: LOW. Recorded, but mapped wrong.**
- **Claim.** The report's knowledge-base gate table credits kb-gates runs to commits. The artifacts are all
  `dirty: true`, and each is keyed to the parent HEAD:
  - `gates-e8fe42ae…json` holds the `76f95cfa` tree and permanently records test **rc=2**;
  - `gates-76f95cfa…json` holds the `d94b0e82` tree;
  - `gates-d94b0e82…json` holds the code-fix tree of `0fd45960`.
- **Gaps.** No artifact exists for `0fd45960`. Its doc-only follow-ups ran only lint, lint-docs and three test files.
- **FIX-NOW.** Name these files in the gate table. State that `kb-ship` owes the clean-tree run.

**F5: LOW. A probe that never ran.**
- **Claim.** `kb-plugin-health` returned rc=1 "(task may not exist)" at L2355. The task does not exist, so the probe
  never asked anything.
- **Arm.** `mise tasks ls`: 0 matches for that name, 1 for `kb-plugin-validate`.
- **Why it causes no gap.** The knowledge-base plugin state was covered by `claude plugin list --json`.
- **Disposition.** No action.

## Checked and not dismissed

| Item | Where it is handled |
|---|---|
| SessionStart doctor, 5 DRIFT | listing-budget is gone (L2371); the other four are at `task_plan.md:709-712` |
| `[currency]` lines | `task_plan.md:711` |
| ponytail `plugin-health` rc=1 | report Q3 |
| codex `--base` with a prompt, rc=2 | report |
| knowledge-base MCP timeout | report; rc=0 when re-run alone (L1315, L1324) |
| `gh` exit 1 | retried at L360 |
| graphify query truncated, rc=3 | the session fell back to `git grep` with a control (L152) |
| mirror `diff -r` rc=1 (`ae6c7a42` L97) | an intended path rewrite; `skills-mirror --check` rc=0 |
| knowledge-base review on npm codex 0.154.0 | the knowledge-base pin; the knowledge-base mirror PR is planned at `task_plan.md:496` |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): transcript, hk.pkl, report, plan, issue search
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): gate artifacts, codex pin, mise tasks
