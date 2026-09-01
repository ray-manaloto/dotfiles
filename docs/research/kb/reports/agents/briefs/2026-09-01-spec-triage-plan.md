# SPEC — triage the repo-hygiene backlog and record it in `task_plan.md`

## 1. Objective

The operator has five outstanding cleanup decisions and 27 undecided branches,
and they currently live only in a chat transcript. Turn them into a reviewed,
written plan phase with a recommendation and honest trade-offs per item, so the
work survives a `/clear` and the operator can decide from evidence rather than
from branch names.

The failure this prevents: 23 of those 27 branches exist ONLY on this machine.
A wrong "delete" is unrecoverable, and a blanket "keep" leaves the repo
permanently cluttered. Both failure modes come from deciding without reading
what the branch actually contains.

You are NOT executing any cleanup. You are producing the reviewed plan.

## 2. Files

Modify exactly one file:

    task_plan.md          (repo root; gitignored, machine-local, 366 lines)

Do not touch anything else. Do not delete a branch, a worktree, or a stash. Do
not run `git branch -D`, `git worktree remove`, `git stash drop`, `gh pr close`,
or any push.

## 3. Inputs — read these first

    /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/ec02aa30-c480-4828-8d9c-3d7872e23daf/scratchpad/branch-detail.md   — evidence pack: for each of the 27 branches,
                                 its commit subjects, files touched, commits
                                 ahead, last-commit date, and whether a copy
                                 exists on origin.

That pack is generated, not authored — treat it as raw data. Where a branch's
purpose is unclear from it, read the actual diff yourself
(`git diff $(git merge-base origin/main <b>) <b>`) before recommending anything.

Cross-check each branch against what is already on `main`. A branch whose idea
shipped by another route is superseded even though its commits never merged —
that is the single most common case here, and it is the judgement the evidence
pack cannot make for you.

## 4. What to produce

### 4a. Fix the stale phase statuses

`task_plan.md` predates today's merges. Correct these from the live record, do
not guess:

- Phase 8 (issue #884, codex lanes) is marked NOT STARTED. It is **COMPLETE** —
  merged as PR #886 (`d4f8436`), which shipped four `codex-*` agent pairs, a
  `codex_agent_parity` hk gate with a sentinel, and a `suites.toml` contract.
- Phase 2 says PR #885; that PR is **MERGED** (`0feb411`).
- Phase 3 "Owed lands" — `land -- 885` ran; main CI passed; the local converge
  initially failed on a macOS keychain authorization dialog and succeeded on
  retry after the operator granted access. Record the outcome accurately,
  including that the failure was environmental and not a code defect.

Verify each of these against `git log`/`gh` yourself rather than trusting this
spec — if any is wrong, say so in your report.

### 4b. Add a new phase: the repo-hygiene backlog

Append a new phase covering these five items. For EACH, give:

- what it is, in one or two sentences an operator can act on;
- **at least two options**, each with an explicit `PRO:` and `CON:`;
- a recommendation, and the one risk that decides it;
- whether it is reversible, stated plainly.

The five:

1. **2 leftover worktrees** — scratch checkouts from background agents, both
   measured clean.
2. **1 stash** — `PR-B: settings.json + doctor.toml + .omc`, stranded on a
   branch that no longer exists. Inspect what it contains before recommending;
   a stash whose content already shipped is different from one that did not.
3. **The 27 branches** — this is the substantial one, see 4c.
4. **Renovate PR #822** (`renovate/all`, OPEN) — prior sessions concluded
   "harvest 3 bumps, then close". Verify whether those bumps are still
   outstanding against current `main`, since main has moved twice today; if they
   already landed, say so and recommend a plain close.
5. **The dependency follow-up PR** — aws-cli 2.36.36, pydantic 2.13.5, ty
   0.0.77, the ubuntu digest, MISE_VERSION 2026.8.16, and enabling
   `astral@astral-sh` (which hardcodes `ty@latest` and conflicts with the
   dev-group ty pin — that conflict must be resolved in the same change).
   ⚠️ Re-derive every version number before writing it down; a previous session
   shipped on inherited numbers and was wrong. Touching image inputs costs a
   ~2.5h cold base rebuild, so note what else is worth batching into it.

### 4c. Per-branch verdicts for all 27

A table with one row per branch: name, last date, commits, `local-only` or
`on-origin`, a one-line summary of what it does, a verdict
(`DELETE` / `KEEP` / `HARVEST` / `NEEDS-OPERATOR`), and a one-line reason.

Rules for the verdicts:

- `local-only` branches carry an unrecoverable delete. Do not recommend DELETE
  on one unless you can say WHY its content is superseded or worthless — "it is
  old" is not a reason, "its change is already on main via <path/commit>" is.
- `HARVEST` means the branch has one worth-keeping idea and the rest is stale;
  name the specific thing worth taking.
- `NEEDS-OPERATOR` is the honest verdict when the branch encodes an intent only
  the operator knows. Use it rather than guessing — but if you use it more than
  about five times, you are not reading hard enough.

Group the table so the operator can act in one pass: the few that need thought
first, the bulk-deletable ones last.

Also state, once and prominently, the safe alternative: pushing the 23
local-only branches to origin before deleting makes the whole operation
reversible, at the cost of 23 remote refs someone must later clean up.

## 5. Constraints

- **`task_plan.md` is gitignored** — editing it is not a repo change and needs
  no branch. Do not create a branch or a commit for it.
- Preserve the file's existing structure and voice: `## Phase N — <name> —
  **STATUS**` headings, tables with `|` pipes, and the ⚠️ convention for traps.
  Add your phase in the existing numbering sequence; do not renumber what is
  already there.
- Do not delete existing content. The "Traps that bite immediately" and
  "Decisions Made" sections stay; append to them if you have something to add.
- Keep it scannable. This file is read at the START of a session by someone with
  no context — long prose is worse than a dense table.

## 6. Verification

    mise run lint

`task_plan.md` is gitignored, so hk will not see it; run lint anyway to prove
you changed nothing else. Also run `git status --porcelain` and show that it is
empty (a gitignored edit must not appear).

Paste into your report: the new phase's per-branch verdict table, and your
counts by verdict (how many DELETE / KEEP / HARVEST / NEEDS-OPERATOR).

## 7. Commit

COMMIT: caller — make NO commit. `task_plan.md` is gitignored; leave the edit in
the working tree. Do not create a branch, do not push.

## 8. PREMISES

- L1 `task_plan.md` exists at the repo root, is 366 lines, and is gitignored (`git ls-files --error-unmatch task_plan.md` fails) — read this session.
- L2 Its headings follow `## Phase N — <name> — **STATUS**`; the highest existing phase number is 11, and Phase 8 sits after Phase 11 in file order — read this session.
- L3 `origin/main` is at `d4f8436` ("feat/codex agent lanes 884 (#886)"), whose parent is `0feb411` ("chore/deps currency 20260831 (#885)") — read this session. Both PRs are MERGED.
- L4 There are 37 local branches; 27 are UNTRIAGED (no PR ever opened), of which 23 are `local-only` and 4 are `on-origin` — measured this session via `git ls-remote --heads origin` cross-referenced with `gh pr list --state all`.
- L5 `renovate/all` has had **14** PRs over its life (#228 MERGED … #822 OPEN). A branch→PR lookup that takes the first match gets a MERGED one and hides the OPEN PR — measured this session. When you map a branch to a PR, prefer OPEN over MERGED over CLOSED.
- L6 There is exactly 1 stash: `PR-B: settings.json + doctor.toml + .omc`, created on `chore/deps-currency` — read this session; that branch has since been deleted locally.
- L7 There are 2 worktrees besides the primary checkout, both measured CLEAN (0 uncommitted files) — one under another session's scratchpad, one left by a dissenting lane.
- L8 181 branches were deleted earlier today with a recovery record at `.agent/logs/branch-cleanup-20260901.txt` holding every SHA — written this session.
- L9 `mise run land -- 885` returned rc=1 on its first run: main CI passed (run 33462308743, conclusion=success) but the local `dev-rebuild` died with `DeadlineExceeded: context deadline exceeded`, caused by a macOS keychain authorization dialog that a background process cannot answer (`~/.docker/config.json` has `credsStore: osxkeychain`). After the operator granted access, a credential read returned in 0.07s and the retry succeeded with smoke tiers 1-3 OK — all measured this session.
- A1 ASSUMPTION: the prior sessions' conclusion that PR #822 needs "3 bumps harvested then close" is still accurate. Held without re-reading #822 — main has moved twice since that conclusion was recorded, so verify it against current `main` rather than repeating it.
