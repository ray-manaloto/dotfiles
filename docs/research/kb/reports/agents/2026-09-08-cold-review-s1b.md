# Cold review — commit 2669d64 (fix/smoke-test-always-runs-s1b)

REF: `git show 2669d64` on branch `fix/smoke-test-always-runs-s1b`,
repo `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`.

Files changed: `.github/workflows/build-publish.yml`,
`python/verification/suites.toml`.

## 1. Does the added `if:` do what the YAML says, under real GHA job-condition semantics? Any failure path let through? `cancelled()`?

New `smoke-test.if`:
```
always()
&& needs.build.result == 'success'
```
(`.github/workflows/build-publish.yml:822-824`)

Enumeration of `plan`/`build` outcomes and the resulting `smoke-test`
conclusion, compared against the PRE-COMMIT behavior (no `if:`, i.e.
implicit `success()` over `needs: [plan, build]`):

| plan | build | smoke-test (OLD, implicit `success()`) | smoke-test (NEW) | Correct? |
|---|---|---|---|---|
| success | success | run | run | yes, unchanged |
| success | failure | skipped | skipped (`build.result` != success) | yes, unchanged |
| success | skipped (e.g. base-prep/p2996-prep failed) | skipped | skipped | yes, unchanged |
| success | cancelled | cancelled* | skipped (`build.result` != success) | **behavior narrows from `cancelled` to `skipped`, but still does not run — no failure path let through** |
| failure | skipped (base-prep/p2996-prep skip because `plan` is a direct `needs` and their implicit `success()` sees `plan` failed) | skipped | skipped | yes, unchanged |

\* Without `always()`, GitHub does not evaluate a downstream job's `if:`
at all when an upstream job in its `needs` chain is cancelled — the
downstream job's conclusion is forced to `cancelled` directly, bypassing
the expression. This is corroborated by the vendor docs fetched below,
which describe `always()` as the way to make a job/step "always execute
… even when canceled" and explicitly warn against it for that reason.

**No FAILURE path is newly let through.** Every combination that
previously skipped `smoke-test` still results in `smoke-test` not
running (as `skipped`, sometimes where it used to be `cancelled` — a
distinction without a consequence for gating).

**`cancelled()` — real, but NOT novel, risk the commit does not mention:**
GitHub's own docs (fetched from
`https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions`)
say of `always()`: *"causes the step to always execute, and returns
`true`, even when canceled… Avoid using `always` for any task that
could suffer from a critical failure… If you want to run a job or step
regardless of its success or failure, use the recommended alternative:
`if: ${{ !cancelled() }}`."*

Applied here: if a user cancels the workflow run in the window **after
`build` has already reported `success`** but **before `smoke-test`
starts**, `always()` makes GitHub still attempt to start `smoke-test`
(cancellation does not gate the job the way it would under an implicit
`success()` condition), and the second operand
(`needs.build.result == 'success'`) is already true, so `smoke-test`
**will start and run to completion** (up to its 45-minute timeout)
despite the user's cancel request — new steps/minutes spent on a run
the user tried to stop.

This is a real, vendor-documented gotcha and the commit message never
mentions it. **However it is not a new pattern this commit invents** —
`build` itself already carries the identical `always()` shape
(`.github/workflows/build-publish.yml:539-546`), so the same
"cancel-after-success-still-runs" exposure already existed for `build`
relative to its own upstream jobs before this commit. This commit
*propagates* that exposure to `smoke-test` (and by extension increases
its blast radius — a real docker pull + smoke run, not just a bake), it
does not originate the pattern. GitHub's recommended fix
(`!cancelled()` combined with the specific result checks) is not used
anywhere in this file.

Source fetched and cited above:
https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions

## 2. Matrix `build` job, `continue-on-error: ${{ !matrix.target.blocking }}`, one leg known-red — does `needs.build.result == 'success'` still hold?

**Yes — confirmed, and this is documented/intentional in-repo, not a
side effect of this commit.**

- `continue-on-error: true` on a failing matrix leg makes that leg's
  conclusion report as `success` for the purposes of the parent job's
  aggregate conclusion and, therefore, for `needs.<job>.result` read by
  downstream jobs. Confirmed via GitHub community discussion
  ["failed matrix jobs with continue-on-error count as success for subsequent jobs" (#45546)](https://github.com/orgs/community/discussions/45546),
  found via WebSearch (official docs excerpts I could fetch did not
  spell this out explicitly, so this is the best available citation;
  labeling it accordingly rather than as a first-party doc quote).
- The repository's own code agrees and states the same conclusion as a
  design decision, not a discovery of this diff: `.github/workflows/build-publish.yml:145-147`
  (mirrored at lines 283, 439, 551, 833, 1019 — six copies, one per job
  that reads a matrix result):
  > `#840: a leg with blocking: false (the arm64/ubuntu-26.04-arm
  > validation runner) never fails a merge — its result still counts as
  > success for needs.<job>.result in downstream jobs.`
- `build`'s own `continue-on-error` line is at
  `.github/workflows/build-publish.yml:551`.

So: yes, `needs.build.result == 'success'` still holds when the known-red
non-blocking leg fails — by the pre-existing, documented #840 design.
This commit does not change that behavior; `smoke-test`'s new `if:`
inherits it exactly as `build`'s own `if:` (line 542) and `manifest`'s
`if:` (line 1120) already did.

## 3. The two contract tokens in `suites.toml` — how many places does each match, and could the contract be satisfied elsewhere?

Measured with a Python substring count over the full text of
`.github/workflows/build-publish.yml` (`text.count(token)`):

```
t1 = "\n  smoke-test:\n    needs: [plan, build]"   -> count = 1, at line 806
t2 = "always()\n      && needs.build.result == 'success'\n    strategy:" -> count = 1, at line 822
```

Control arm for the anchoring claim in the commit message ("the
`strategy:` anchor is load-bearing… `manifest` carries a byte-identical
`always() && needs.build.result == 'success'` clause"): I re-ran the
count with the anchor **stripped** (just
`"always()\n      && needs.build.result == 'success'"`, no trailing
`\n    strategy:`) and got **count = 2**, matching at line 822
(`smoke-test`) **and** line 1120 (`manifest`, which has the
byte-identical two-line fragment inside its longer `if:` block at
`.github/workflows/build-publish.yml:1118-1123`). This directly confirms
the commit message's claim is correct and the anchor is load-bearing:
without the `strategy:` suffix, `token2` would be satisfiable by
`manifest` alone even if `smoke-test`'s own `if:` were deleted, which is
exactly the false-pass the commit is trying to avoid. With the anchor,
count is back to 1 and it can only be `smoke-test` — `manifest` has no
`strategy:` block (goes straight to `runs-on: ubuntu-latest` at line
1124), so it cannot satisfy the anchored token.

Could either token be satisfied by a comment instead of real code? No —
I grepped the surrounding comment lines (806-821) and none contains
either exact string; the nearby prose comment at lines 810-811 mentions
`` `always()` `` in backticks but never the two-line
`always()\n      && needs.build.result == 'success'\n    strategy:`
sequence with matching indentation, so a comment cannot spoof it.

**Neither token is over- or under-anchored** as shipped. `t1` is
inherently unique (job names are unique in a workflow). `t2` is unique
only because of the `strategy:` suffix — remove that suffix and it
becomes under-anchored (2 matches, satisfiable by `manifest`). As
committed, both are correctly anchored.

## 4. Downstream (`dev-tag`, `manifest`) — does a state now let a downstream job proceed wrongly, or stay skipped when it should run?

`dev-tag.if` (`.github/workflows/build-publish.yml:1008`):
```
needs.smoke-test.result == 'success'
```
No `always()` here, so GitHub implicitly ANDs this with `success()`
over `needs: [plan, build, smoke-test]`. Since the explicit clause
already requires `smoke-test.result == 'success'` (not `skipped`, not
`cancelled`, not `failure`), `dev-tag` cannot run unless `smoke-test`
genuinely succeeded — unaffected by whether `smoke-test`'s own
conclusion arrived via `skipped` (old default) or the new explicit
`if:`. No finding: this job's gating is unchanged and correct.

`manifest.if` (`.github/workflows/build-publish.yml:1118-1123`) was
**not touched by this diff** (confirmed: the diff in `git show 2669d64`
touches only lines 806-824 of the workflow file, plus the new
`suites.toml` entry — `manifest`'s block at line 1117 onward is outside
the changed hunk). It already carried the same
`always() && needs.build.result == 'success' && needs.smoke-test.result
== 'success' && …` shape before this commit, so its gating behavior is
unaffected by this change. No finding.

**Net effect on downstream is exactly the intended one:** previously,
on the nightly path (`dev-prep` skipped), `smoke-test` always skipped,
so `dev-tag` and `manifest` always skipped too (their explicit
`== 'success'` checks on `smoke-test`/`dev-tag` could never be
satisfied) — matching the commit's stated motivation (`:dev` never
advanced on 6/6 nightlies). Now that `smoke-test` can reach `success` on
the nightly path, `dev-tag` and `manifest` can run when they should.

I found no state where `smoke-test` ends `failure` or `cancelled` and a
downstream job proceeds anyway (both downstream jobs require literal
`'success'` from `smoke-test`, never `skipped`-tolerant for that
specific field), and no state where `smoke-test` should run but stays
`skipped` post-fix, beyond the `cancelled()`-window caveat noted in §1
(which causes over-running, not under-running).

## Summary of findings

1. **No new failure-path leak.** The explicit `if:` correctly restores
   failure/skip gating for `smoke-test`. There IS a real,
   vendor-documented `always()`-vs-cancellation gap (job can start and
   run to completion in the window after `build` succeeds but before a
   user's mid-run cancellation is honored) that the commit message does
   not mention — but it mirrors an identical pre-existing exposure on
   `build`'s own `if:`, not a new pattern invented here.
2. **No finding** — `needs.build.result == 'success'` does hold with a
   known-red non-blocking leg, by design (#840, six in-repo comments
   confirm it), unrelated to this diff.
3. **No finding on the tokens as shipped** — both are uniquely anchored
   (count = 1 each), and the `strategy:` suffix on `t2` is proven
   load-bearing by a direct count-without-anchor control arm (2 matches
   without it, `manifest` being the second).
4. **No finding** — `dev-tag`/`manifest` gating is unchanged and correct;
   `manifest`'s block falls outside the diff entirely.

## GitHub repos touched

- No GitHub repository source was read for this review beyond this
  repo's own working tree (`git show`, file reads). Two GitHub.com pages
  were consulted for vendor semantics, not as source-code repos:
  - https://docs.github.com/en/actions/reference/workflows-and-actions/expressions — `always()`/`cancelled()`/`success()` semantics.
  - https://github.com/orgs/community/discussions/45546 — community confirmation that `continue-on-error: true` on a failing matrix leg reports as `success` to downstream `needs.<job>.result`.
