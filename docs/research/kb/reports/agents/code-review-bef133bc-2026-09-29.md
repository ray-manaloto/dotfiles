# /code-review medium bef133bc (session dcb0b106, 2026-09-29)

Verbatim final message. Disposition: both CONFIRMED (F2 reproduced by the reviewer). Third round on this diff — surfaced to Ray per the two-round cap.

---

I found two real bugs in `bef133bc`. I couldn't submit them through ReportFindings because that tool isn't available in this session, so they are only in this reply. The review was read-only: I wrote nothing to `findings.md`, so please persist this report yourself.

## Findings

1. **`.github/workflows/gcc-sha-repair.yml:114-117` — medium.** When the branch is rewritten under the job, the new ancestry guard exits 0 without pushing and relies on a premise that is often false. The comment says "the rewrite changed the Dockerfile, so its own push run repairs it." But for pushes to an existing branch, GitHub evaluates the `paths:` filter with a two-dot diff of the old tip against the new tip.
   - **Scenario:** Renovate rebases or recreates `renovate/*` onto a newer `main` that did not touch `.devcontainer/Dockerfile`. The old and new tips then have the same Dockerfile, still with the stale sha.
   - **What goes wrong:** the rewrite push does not re-trigger this workflow, so nothing cancels this run. This run exits 0 (green) without pushing its repair. The sha stays stale and the image build fails, which is the exact outcome this workflow exists to prevent.
   - **Why this is avoidable:** the new `git rebase --onto FETCH_HEAD "${GITHUB_SHA}"` already replays only the repair commit. On a rewrite, the repair would either apply cleanly onto the new tip or conflict loudly (if the `.deb` line changed). So the guard throws away a repair that would have worked.
   - **Better handling:** rebase the repair onto the rewritten tip anyway, or re-run `dotfiles-setup gcc-sha` against `FETCH_HEAD`, rather than exiting 0.

2. **`.github/workflows/gcc-sha-repair.yml:119` — low.** On the second retry, `--onto FETCH_HEAD "${GITHUB_SHA}"` uses the original checkout SHA as the upstream. That is no longer the repair commit's parent, because attempt 1 already rebased HEAD onto the first fetched tip (say, lock commit L1). So `GITHUB_SHA..HEAD` now contains L1 as well as the repair, and L1 is replayed onto the new tip.
   - **Reproduced** in scratch repos (`scratchpad/sim2`): with a depth-1 clone, push L1 (lock A→B), then L2 (lock B→C), and run the loop's fetch and rebase twice. The second rebase reports `CONFLICT (content): Merge conflict in lock` / `could not apply … L1` and exits rc=1, so the job fails.
   - **Control arm:** the first retry in the same simulation rebased cleanly (repair on top of L1), so the setup can produce both outcomes.
   - **Fix:** keep the upstream moving. Use `git rebase --onto FETCH_HEAD HEAD~1`, since the repair is a single commit, or record the previous onto point after each rebase.

## One-line summary
- `.github/workflows/gcc-sha-repair.yml:114` — a rewrite that leaves the Dockerfile unchanged (a Renovate rebase onto `main`) doesn't re-trigger the workflow, yet the job exits 0 without pushing, so the stale sha is never repaired.
- `.github/workflows/gcc-sha-repair.yml:119` — the second retry rebases from the fixed `${GITHUB_SHA}` and replays the previously fetched lock commit, which conflicts and fails the run (reproduced).

## GitHub repos touched

_None._
