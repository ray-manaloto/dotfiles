# Spec — codex-takeover Phase E: CODEX TAKES OVER ALL WORK NOW (2026-10-05)

Ray, verbatim: "/codex-sdlc-team to handle this and then have codex take over all the work now".
Claude's budget is at about 95% or more. This run is the codex coordinator. Claude may be
unavailable for the whole run.

Read first, in order:

1. `docs/handoffs/codex-takeover-START-HERE.md`.
2. `docs/agents/session-orchestration.md`. It documents the claim, queue, SLOT, ship and hand-back.
3. `docs/specs/codex-takeover-2026-10-05.md`, the rounds and "Lane state". Ray's rulings there
   are binding.
4. The main checkout `task_plan.md`, `.agent/plans/main-checkout-ship-queue.md` and
   `.agent/plans/handoff-inbox/`.

Main checkout: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`. This worktree:
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/codex-takeover`, branch
`feat/codex-takeover`.

## 1. Objective

Codex owns coordination and execution until Claude returns, with no human reconstruction. The
failure this prevents: all work stalls when the Claude coordinator and lanes stop.

## 2. Work, in strict order

**E-1. Wait for Phase D before touching anything.** Phase D (sdlc run `92ea87dc94ca461587cc81fc7272892f`)
owns this worktree until it settles.

1. Run `mise run bounded-wait -- --deadline 3900 --file
   /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/codex-takeover/.agent/sdlc-runs/92ea87dc94ca461587cc81fc7272892f/settlement.json`.
2. Then read that settlement and `git log`.
3. If Phase D did not commit, finish its spec first: `docs/specs/codex-takeover-phaseD-commit-spec.md`.

**E0. Become coordinator.**

1. Find the current newest coordinator: the newest `dotfiles-*.coordinator` name across
   `claude agents --json --all` AND the claims store.
2. Run, from THIS worktree (B2a lives here until it ships):
   `mise run handoff-inbox -- coordinator-claim --name dotfiles-<YYYYMMDDTHHMMSS>-05.codex-coordinator.coordinator --supersedes <that name>`.
   The name must match `^dotfiles-.+\.coordinator$`.
3. Record the rc.
4. Append an ownership notice to every live lane's inbox via `mise run handoff-inbox -- append`
   (lanes are listed by `mise run lane-cards -- --json`), naming yourself as coordinator.

**E1. Ship codex-takeover.**

1. Confirm the Phase D commit SHA, from the `codex-takeover` inbox "B2a SETTLED <sha>" line and
   `git log`.
2. Run the full gates under your own SLOT GO, in queue order: the first two queued ships
   (r2, #1673) go first if still pending.
   - Gates: `mise run gate -- run lint`, `mise run gate -- run pytest`,
     `mise run gate -- run verify`, `mise run gate -- run lint-docs`.
   - Read the real rc of each.
   - On a red gate: fix the CODE, commit, re-gate. At most 2 rounds, then stop and write the
     residue to START-HERE.
3. Review lens: the codex review lens from `.claude/skills/codex-sdlc-team/SKILL.md` § Review
   tiers, pinned model and effort, `--commit <literal SHA>`. Refute or fix the findings.
4. Ship from the MAIN checkout via `mise run ship` (the docs-only worktree exception does not
   apply; this has code). Then `mise run bounded-wait` for the merge, then `mise run land -- <PR>`.
   Record the rcs.

**E2. Fix the issue planner, then file the per-session issues.**

- `session_registry.py:639-644` blocks EVERY create when ANY omission exists. Change it to
  block only the rows actually affected, keep the reason per row, and add tests with a realistic
  red mutation.
- Then file one issue per working/blocked/stopped session or role chain lacking one, in its own
  repo. Link umbrella `ray-manaloto/dotfiles#1721`.
- Write a `task_plan.md` delta, and apply it yourself as coordinator via
  `mise run handoff-inbox -- plan-apply`, then `mise run plan-attest`.
- Ship this like E1, as its own branch/PR from a new worktree under `.claude/worktrees/`.

**E3. Project priorities (Ray), then continuous work.**

1. docker images and devcontainers;
2. project repo dependencies;
3. graphify fork integration.

- Use `task_plan.md` and `gh issue list -R ray-manaloto/dotfiles` (and knowledge-base) to find
  the open items. For each, follow the repo's own workflow: branch/worktree, spec, implement,
  gates, review lens, ship, land.
- Other meta and orchestration lanes stay READ-ONLY: keep their cards current, do not resume
  them.

**E4. Stay handoff-ready (Ray: "claude should always be ready to handoff to codex and vice versa").**

- At every milestone, update `docs/handoffs/codex-takeover-START-HERE.md`, the lane cards and the
  ship queue.
- At each milestone and at most every 30 min, probe for Claude with a bounded `claude -p "reply OK"`.
- When Claude is back:
  - finish or park the current step;
  - write the handoff;
  - run `coordinator-release`;
  - append a hand-back record to the inbox.
- The automatic Claude-coordinator LAUNCH is a known BLOCKED seam:
  `coordinator_handoff._launch_identity` accepts only a Claude predecessor, `:818-834`. So the
  hand-back record must ask Ray to start a Claude coordinator. Do not hand-roll a launch.

## 3. Scope

The whole repository, under the repo's rules.

- Implementation edits go in worktrees, never on main.
- Main-checkout writes go only through `mise run handoff-inbox` and `mise run ship`/`land`.

## 4. Constraints (hook_guard does NOT see codex; these are the guard)

Never use, run or do any of these:

- `--no-verify`, `HK_SKIP_*`, inline suppressions, `--ephemeral`;
- `gh pr create`/`merge` (use `mise run ship`/`land`/`automerge`);
- `gh run watch`, `gh pr checks --watch`;
- an unbounded wait loop;
- `cmd | tail` to capture a gate (redirect to a file and read the rc);
- `chezmoi apply` on the host;
- `git add .`;
- writes on the default branch;
- edits to user-level files (`~/.claude`, `~/.codex`, LaunchAgents);
- printing secret values;
- a local base-image build (`mise run build` / `bake dev-load`);
- a force-push;
- merging a red PR.

Also:

- One heavy gate on the host at a time.
- Persist every finding and report as you go, to
  `docs/research/kb/reports/agents/codex-takeover-phaseE-2026-10-05.md`.

## 5. Verification

Every claim carries a real rc or an API `conclusion`:

- the claim rc;
- each gate's rc;
- the review lens result;
- the PR number and its merged state;
- the land rc;
- issue numbers;
- the plan-apply/attest rc.

## 6. Commit

`lane`, on the appropriate branch, with each commit gated by the pre-commit hook.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | I | `coordinator-claim --name --supersedes`, `coordinator-release` exist (worktree, uncommitted until Phase D) | `docs/research/kb/reports/agents/codex-takeover-phaseB2a-validation-2026-10-05.md:77` |
| 2 | L | The issue planner blocks all creates on any omission | `session_registry.py:639-644` per the phaseC report:99 |
| 3 | L | Hand-back launch accepts only a Claude predecessor | `coordinator_handoff.py:818-834` per the phaseC report:103 |
| 4 | P | Codex review lens command | `.claude/skills/codex-sdlc-team/SKILL.md` § Review tiers |
| 5 | A | Phase D commits successfully — VERIFY first; if it did not, finish Phase D's spec (`docs/specs/codex-takeover-phaseD-commit-spec.md`) before E0 | — |

## Amendments r2 — Ray's grilling answers (2026-10-05, after the auto-mode block)

The auto-mode classifier refused to dispatch r1 as "Create Unsafe Agents": no timeout, whole-repo
scope, autonomous claim/ship/merge. Ray's rulings, verbatim:

- Launch: **"Permission rule, I dispatch"**. Ray adds the permission rule himself; the architect
  then dispatches. The run is BOUNDED: `timeout_s` = 14400 (4 h), no self-chaining. At the end it
  updates START-HERE with exactly where to resume.
- Merge rights: **"Normal ship path, auto-merge on green (Recommended)"**.
  - `mise run ship` arms auto-merge and merges only on a green ci-gate; then `mise run land`.
  - Never merge a red PR, and never use a raw `gh pr merge`.
- Claim timing: **"Claim only once Claude is out (Recommended)"**. This overrides E0 above:
  - Do NOT claim at the start.
  - Work as a lane first: Phase D completion, E2's planner fix in its own worktree, and the E1
    gates once the live coordinator grants the SLOT via the inbox.
  - Claim with `--supersedes` only when the newest Claude coordinator stops responding (no inbox
    or queue activity for 30 min) AND the bounded `claude -p "reply OK"` probe fails.
- More notes: **"No ambiguity — proceed (Recommended)"**.
