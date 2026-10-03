# Durability proposals for unpushed coordinator/lane branches (2026-10-03)

> Persisted verbatim by coordinator 28f1a8f7 from old-coordinator 27e2bf5c's transcript line L1008 (19:42:32Z), as quoted
> by the handoff-review subagent (`handoff-review-27e2bf5c-2026-10-03g.md`). Producer: Plan subagent a752d09153c6334db of
> 27e2bf5c. **Ray's rulings (2026-10-03, ~14:50 CDT, to coordinator 28f1a8f7): Q1 = A, Q2 = A, Q3 = A, Q4 = A.**

Read-only lane: I wrote nothing to findings.md or progress.md, so the coordinator needs to save this report. I checked the stated facts with git and gh. Where a lookup came back empty, I ran a control lookup that should succeed (`origin/main:AGENTS.md` and the lane branch's remote ref), and both did.

## Verified state
- `docs/coordinator-2026-10-03e` @38312a3c: 1 commit ahead of origin/main (984d3571), 9 files, all `docs/**.md`. Not on origin (ls-remote returned only lane-completion). **Second unpushed ref at the same commit:** local `docs/handoff-2026-10-03g` → 38312a3c.
- `research/session-handoff-automation` @076ac999: 1 commit, 4 files, including `docs/specs/session-handoff-automation.md`, which is still being drafted. Not on origin.
- `docs/lane-completion-protocol` @b487c3ad is 5 commits ahead; origin/docs/lane-completion-protocol is 1dcf0d4b and has no PR.
- `git merge-tree` is clean for every pair of the three branches (rc=0).
- **The 03f handoff (`docs/handoffs/session-2026-10-03f.md`, de9575bd) exists only on the lane branch.** So ruling (b) itself cites a dead path. #1606 is an issue (OPEN); its fix is branch `fix/1606-enterworktree-guard`.
- **Mis-cited branch:** #1616, #1618 and #1619 cite `apply-998ab91b-findings-proposals-2026-10-03.md` and name the branch `docs/lane-completion-protocol`. That file exists only on `docs/coordinator-2026-10-03e`. The lane branch has `event-driven-self-healing…md`.
- **Push mechanics:**
  - The pre-push hook always runs the full suite: `hk.pkl:872-890` calls `test-hook-isolated`, which runs `heavy-gate run --label pre-push … pytest tests/` (`mise.toml:310-314`).
  - So a bare `git push` queues on the host-wide heavy-gate lock, the one test slot (wait up to 1h, `host_lock.py:20`).
  - Skipping it is denied: `--no-verify` (`mise-tasks-only.md:31`, `do-not.md:67`) and `HK_SKIP_STEPS` (ADR-0001, `pr.py:385-386`).
- **Ship has no docs-only fast path.** `gate_matrix` (`pr.py:377-441`) always runs lint, verify-contracts, hook-selfcheck and eval, plus lint-docs for docs paths. pytest moves to the push (`pr.py:689-707`), and one lock covers both the gates and the push (`pr.py:671-686`). The suite takes about 6-11 minutes and dominates the cost (`pr-workflow/SKILL.md:128`).
- **Pushing from `.claude/worktrees/` is expected to fail.** `tests/test_session_review.py:1106` fails only inside `.claude/worktrees/` (#1614 OPEN; `session-2026-10-03e.md:14-16`). Two of the three branches live in that tree.
- **Handoff census:** it covers processes only (`HEAVY_COMMAND_RE`, `coordinator_handoff.py:115,453-620`). The skill covers only its own handoff branch (`coordinator-handoff/SKILL.md:45-50`). Nothing takes a census of unpushed coordinator or lane branches.
- **Worktree removal risk (inferred from the man page, not tested):**
  - `git worktree remove` refuses only on untracked or modified files. Ignored files are deleted with the directory.
  - What is at risk: `coord-docs/.agent/issue-drafts/*` (23 issue/comment drafts), `handoff-automation-research/.agent/kb/raw/research-fanout/*`, and `lane-completion/findings.md`.
  - `claude rm` deletes `~/.claude/jobs/<id>`, inferred from the "copy before any `claude rm`" warning at `session-2026-10-03e.md:27`.
  - Committed branches survive both.

## Q1. Making the work durable now
- **A (Recommended): ship coordinator + 03g as ONE docs PR from the main checkout; ship lane-completion as its own PR once its gates pass; leave research local until the spec is committed.**
  - PRO: one suite per PR, about the same cost as a bare push, and you also get a PR plus auto-merge (#1604/#1608/#1615 precedent).
  - PRO: shipping from the main checkout avoids the #1614 failure.
  - CON: the coordinator branch has to be detached from its worktree first (one shipper, `.agent/plans/main-checkout-ship-queue.md`).
- **B: push-only backup refs.**
  - PRO: no PR review needed.
  - CON: still costs the full suite and the slot, so it saves nothing.
  - CON: from `.claude/worktrees/` it hits #1614.
  - CON: pushing by ref name from the main checkout runs the hook against the main checkout's tree, so the suite passes without ever testing the branch being pushed.
- **C: fold all three into one PR.**
  - PRO: one suite total.
  - CON: mixes the unratified spec and the lane's ungated audits into one review, and blocks the coordinator docs on both.

## Q2. Ordering relative to #1606
- **A (Recommended): #1606 ships first (ruled, `session-2026-10-03e.md:11-30`). The coordinator docs PR goes next, ahead of #1614 (2b′).**
  - PRO: matches the skill's "handoff ship at the head of the queue" rule (`SKILL.md:49`).
  - PRO: nothing conflicts.
  - CON: pushes #1614 back by one suite.
- **B: ship the docs PR before #1606.**
  - PRO: links work about 15 minutes sooner.
  - CON: overrides Ray's ruled order.
- **C: wait until after #1614.**
  - PRO: worktree pushes become safe.
  - CON: one or two more auto-handoffs pass with the work only on local branches.

## Q3. Making it structural (#1617, D3)
- **A (Recommended): add a check to `coordinator-handoff launch` that lists unpushed branches.**
  - It lists every branch that is ahead of origin or has no upstream, for the coordinator's own worktrees, plus local `.agent/` draft directories.
  - It writes them into the handoff and the successor brief as owed ships. It does not refuse and does not auto-push.
  - PRO: never blocks an unattended handoff.
  - CON: the work stays local until the successor ships it.
- **B: refuse handoff (rc 2) while unpushed branches exist.**
  - PRO: strict.
  - CON: blocks the handoff at 30% context with nobody to unblock it, which defeats the zero-human goal.
  - CON: the push needs the slot.
- **C: auto-push at handoff.**
  - CON: needs the heavy slot mid-handoff.
  - CON: the #1614 failure.
  - CON: SKILL.md already says push the handoff branch only when another ship holds the slot.
- **Coverage gap in the research branch:**
  - The research report names the risk ("a stranded branch strands its handoff", `session-handoff-automation-research-2026-10-03.md:99,195`) but adds no census.
  - The spec line `docs/specs/session-handoff-automation.md:88` ("Push only if the branch is already pushed") makes it worse.
  - Recommend putting the census into #1617's spec under D3 = M1 (`spec:16`).

## Q4. Dead links in the new issues
- **A (Recommended): fix the links by shipping, then edit once to name the merged commit and correct the branch.**
  - PRO: one edit, stable content links.
  - PRO: it also fixes the lane-completion mis-cite in #1616, #1618 and #1619.
  - CON: links stay dead until the merge.
- **B: edit now to point at local SHAs or state "unpushed".**
  - PRO: honest immediately.
  - CON: still not something a reader can open.
- **C: paste the key excerpts into comments.**
  - PRO: durable now.
  - CON: duplicates the reports and drifts from them.

### Critical Files for Implementation
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/coordinator_handoff.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/coordinator-handoff/SKILL.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pr.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/docs/specs/session-handoff-automation.md

## GitHub repos touched
- ray-manaloto/dotfiles: read-only `gh issue view` (#1606, #1614, #1616-#1619) and `gh pr list` (none for lane-completion). Nothing posted or edited.
- knowledge-base: not touched.
