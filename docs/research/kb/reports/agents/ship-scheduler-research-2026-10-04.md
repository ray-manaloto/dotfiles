# Ship/land scheduler research (2026-10-04)

Status: COMPLETE (2026-10-04).
Scope: read-only research. Ray's ruling (2026-10-04) is an **executing** scheduler, the only thing that decides when ship/land runs.
Scratch data from this run: `/tmp/shipsched/` (`df_prs.json`, `kb_prs.json`, `df_runs.json`, `logs.txt`, `humfiles.jsonl`). It is machine-local and not durable. Every number below names the command that produced it.

## 1. Measured statistics

### 1.1 Merge volume (GitHub)

Source: `gh pr list -R ray-manaloto/<repo> --state merged --limit 300 --json number,title,headRefName,createdAt,mergedAt,author`.

| Repo | Rows | Span covered | Condition |
|---|---|---|---|
| dotfiles | 300 (hit the limit) | 2026-09-14T11:33Z .. 2026-10-04T18:11Z | 09-14 is partial because of the limit |
| knowledge-base | 275 (below the limit, so this is all of them) | 2026-07-22 .. 2026-10-04 | complete |

**dotfiles merges per day** (UTC date of `mergedAt`): 09-15 6 · 09-16 19 · 09-17 17 · 09-18 16 · 09-19 4 · 09-20 5 · 09-21 9 · 09-22 18 · 09-23 9 · 09-24 8 · 09-25 9 · 09-26 6 · 09-27 11 · 09-28 20 · 09-29 20 · 09-30 12 · 10-01 9 · 10-02 26 · 10-03 21 · 10-04 25 (partial day).
- Over the last 3 days that is **21–26 merges/day**.
- The busiest clock hour since 09-28 had 4 merges (09-28T05Z). Most busy hours had 3.

**Who authors dotfiles merges (n=300):** Renovate 154 (51%), Ray/agents (`sortakool`) 136, refresh bot 9, dependabot 1. Branch prefixes: `renovate/` 154, `docs/` 61, `fix/` 44, `feat/` 20, `chore/` 18, `codex/` 2.
- **Half the dotfiles merge traffic is Renovate.** It never passes through `ship`/`land`; it goes through `automerge` (`mise-tasks-only.md` table). A scheduler that owns only ship/land does not see half the merges that move `main`. Every one of those merges still forces a rebase and a re-validation on the queued human branches.

**knowledge-base merges per day** in the most recent window: 10-02 6 · 10-03 4 · 10-04 6. Earlier peaks were 08-29 21 and 08-30 15. All 275 are by `sortakool`, and there are no bot PRs. Prefixes: `feat` 91, `chore` 71, `fix` 38, `round` 19, `codex` 18, `docs` 17.

**PR open→merge (createdAt→mergedAt, minutes):**

| Population | n | p10 | p50 | p90 | max |
|---|---|---|---|---|---|
| dotfiles all | 300 | 5 | 7 | 41 | 25308 |
| dotfiles human | 136 | 4 | 7 | 41 | 777 |
| dotfiles Renovate | 154 | 6 | 7 | 30 | 25308 |
| KB (all human) | 275 | 0 | 4 | 78 | 1504 |

- Condition: `ship` opens the PR only **after** the local gates and push succeed (`pr.py:671-707`).
- So open→merge measures *remote CI plus GitHub*, not the session's total ship latency. The local part is in §1.3.

### 1.2 CI (dotfiles `ci.yml`)

Source: `gh run list -R ray-manaloto/dotfiles --workflow ci.yml --limit 200 --json databaseId,createdAt,updatedAt,conclusion,event,headBranch,status`.
- Window: 2026-09-30T10:49Z .. 2026-10-04T18:04Z (4.3 days).
- Duration is `updatedAt − createdAt`. That is an upper bound when a run was re-run.

| Event / conclusion | n | p10 | p50 | p90 | max (min) |
|---|---|---|---|---|---|
| pull_request success | 92 | 4.6 | 7.3 | 35.4 | 58.6 |
| pull_request failure | 38 | 1.6 | 3.3 | 4.1 | 12.3 |
| pull_request cancelled | 34 | – | – | – | – |
| push (main) success | 31 | 5.5 | 7.0 | 8.2 | 39.7 |
| schedule success | 5 | – | – | – | – |

**Failures by branch prefix** (pull_request events): Renovate 36 failure + 34 cancelled + 31 success. Human prefixes (`docs`/`fix`/`feat`/`chore`): **60 success, 2 failure**, and both failures were `chore/lock-refresh`, a bot-style branch.
- **A human PR that reached CI essentially never failed there in this window.** `ship`'s local gates (and the pre-push suite) catch failures before the push.
- Sampled Renovate failure jobs, from `gh run view <id> --json jobs`:
  - `lint` (37219724211, 37204181026, 36972175916);
  - `contract-preflight` (37159115800);
  - `build-publish / base-prep` ×3 legs (36854670352, chore/lock-refresh).
- The 34 cancellations come from `ci.yml:47-49`, `concurrency: … cancel-in-progress` on non-main refs: Renovate force-pushes supersede in-flight runs.
- Implication: CI time-to-green for a human PR is **~7 min p50 and ~35 min p90**, and the p90 is the base-build path (`feedback_ci_build_duration_baseline`: about 10 min warm and about 2.5 h cold, inherited and not re-derived here). Remote CI is not the bottleneck.

### 1.3 Local ship/land wall time (the real bottleneck)

Source: a python parse of every `/Users/rmanaloto/.claude/jobs/*/tmp/{ship,land}-*.log`.
- Wall time is file `st_mtime − st_birthtime`.
- `rc=` is the line the coordinator's `…; echo rc=$? >> LOG` wrapper appended.
- 83 logs; the earliest is 2026-10-01T21:12 local and the latest is 2026-10-04T13:01.
- **Control arm for the glob:** a broader `*ship*|*land*` listing found 30 more logs with other name shapes. Those are the KB shippers' logs (`kb837-ship*.log`, `a0d2bdd6/tmp/kb3-ship.log`, …) and are parsed separately in §1.4. The `wait-*`/`launch-*` logs are excluded because they are waits, not ship/land runs.
- Condition: these are the runs that the coordinator and its lanes captured to job-dir logs. A ship run by hand in a terminal leaves no log here.

**dotfiles `ship`** (50 logs):
- rc=0: **n=39, p50 4.2 min, p90 39.8, max 73.4, sum 505 min**.
  - Bimodal. The **fast** mode (<10 min) is n=25, p50 2.7, p90 4.7: docs/python-only ships, where the gates plus the pre-push suite take about 1–5 min.
  - The **slow** mode (≥10 min) is n=14, p50 16.4, p90 61.5, max 73.4.
  - 12 of the 14 slow ships ran the `sync-full` gate, a devcontainer-surface diff (`pr.py:283-288`, `:439-440`, tag `[devcontainer surface → full-sync gate]`). The list: ship-1329, ship-1502(×2), ship-1606, ship-1614b, ship-audit000, ship-autohandoff, ship-cap, ship-hostload, ship-g2, ship-autostart, ship-L0. The two slow ships without it were `ship-fanout-2` (24.5 min) and `ship-lane-completion` (13.9 min).
  - Inside a sync-full ship, the in-container pytest runs take **150–1548 s each, 2–4 times per ship**. Example: ship-autostart had runs of 946, 1188 and 1024 s, against 88 s for the host pre-push suite (§1.5).
- Non-zero: **11 of 50 (22%)**.

  | Cause | Count | Logs |
  |---|---|---|
  | pre-push suite assertion `tests/test_session_review.py:1106` | 3 | ship-coord-28f1a8f7, ship-handoff-l, ship-hermetic (all `git push rc=1`) |
  | sync-full container failure (`converge: dev-rebuild rc=1` + a test failure) | 2 | ship-cap, ship-1502@328111a4 |
  | linked-worktree refusal for a sync-full diff (`pr.py:612-622`, rc=2, 0 min) | 2 | ship-1614, ship-bgiso |
  | real test failure (`test_session_gate.py:307`) | 1 | ship-g |
  | missing worktree venv tool (`datamodel-codegen` FileNotFoundError) | 1 | ship-coord-…-b |
  | dirty tree refusal | 1 | ship-coord-97ffeddb |
  | `git push rc=141`, ssh idle drop during a long pre-push (fixed by keepalive, queue file 15:45 entry) | 1 | ship-fanout |

  **Every failure was retried by a human or the coordinator**, and the retry mostly succeeded within minutes (handoff-l → l2 at +3 min; coord → -c at +4 min; 1614 → 1614b at 0 min; bgiso was re-shipped from MAIN).

**dotfiles `land`** (28 logs; excludes the 4 KB `land-8xx` logs in 80dc41fe and `998ab91b/tmp/land-wait.log`, which is a wait):
- rc=0: **n=24, p50 19.1 min, p90 49.8, max 63.7, sum 651 min**.
  - Bimodal by tier (`pr.py:1056-1059`). Under 20 min: n=12, p50 11.6, p90 17.3. **20 min or more: n=12, p50 40.2, p90 52.6, max 63.7.**
  - The full tier (`post-merge local validation (full`) ran in 9 logs: land-1510, 1570, 1573, 1583, 1622, 1630, 1633, 1644 and 1647.
  - The in-container suite inside land took 150–1229 s per run.
- Non-zero: 2 of 26 completed.
  - **land-1662 rc=1, after 47.7 min**: `TimeoutExpired … devcontainer-smoke.sh timed out after 1800.0 seconds`. That is `container.py:49` `_SMOKE_TIMEOUT_S = 1800.0`, reached after `CONTAINER OUTDATED → dev-rebuild`.
  - land-1589 rc=1: `fatal: Cannot fast-forward to multiple branches`. The retry 1589b was rc=0.
  - 2 more logs are the current session's in-flight runs, with no rc yet.
- **The land smoke is the longest single serial step in the system.** Its 1800 s timeout is reachable, and when the base is stale a `dev-rebuild` is added in front of it.

**Per day** (local logs, both kinds; source `logs.txt` grouped by the birth date of each log; includes 4 KB `land-8xx` logs from job dir 80dc41fe):

| Date | ship logs | land logs |
|---|---|---|
| 10-01 (from 21:12) | 1 | 1 |
| 10-02 | 11 | 5 |
| 10-03 | 27 | 17 |
| 10-04 (to 13:01) | 11 | 10 |

Summed rc=0 wall time over 3 days: **505 min ship + 651 min land ≈ 19.3 h**, or more than 6 h of ship/land wall time per day. Runs partly overlapped, so this is wall time, not proof of serial occupancy.

### 1.4 knowledge-base kb-ship / kb-land

Source: the same parse over `80dc41fe/tmp/*-ship*.log`, `a0d2bdd6/tmp/*-{ship,land}*.log` and `a2ccbbc5/tmp/bw-ship.log` (n=33).
- **kb-ship: 29 runs, 11 non-zero (38%)**, wall time about 5–14 min, typically 5–6 min.
  - Failure causes:
    - **4 load-induced timeouts** (`timed out waiting for reply id=1`; `graphify query rc=-1: timed out after 180s`): kb3, kb838, a000, a000b. All four happened on 10-02, while dotfiles ships and lands were running concurrently. The queue file entries at 17:55 and 22:00 record load 84 and load 107.
    - lint: 2 (mrb, wrap).
    - `kb-manifest-audit` DRIFT: 2 (kb837-3, kb837-4). This one is content-caused, per `proposals-heavy-slot-overlap-2026-10-03.md` TL;DR.
    - test rc=2: 1 (kb837-2).
    - funnel: 1 (kb838b).
    - dirty tree: 1 (kb837).
- **kb-land: 0.2–3.2 min.** It has no container smoke. Of 9 runs, 3 failed:
  - 865: `base branch policy prohibits the merge`, because KB `strict=true` requires up-to-date; see §2.3.
  - k748: `refusing — PR #853 is not green`.
  - mra-land: `merged, but local sync failed at git pull --ff-only`.
- **KB has no host lock at all** (`proposals-heavy-slot-overlap-2026-10-03.md:93`, citing `kb_setup/currency/sync.py:809`). Its 4 timeout failures are the measured cost of that gap.

### 1.5 Host heavy-slot contention

- Source: `/usr/bin/grep -hE 'lock acquired after|^==> waiting for heavy-gate' /Users/rmanaloto/.claude/jobs/*/tmp/*`. Bare `grep` on this host is aliased to `ugrep`, so `/usr/bin/grep` is used.
- **Measured waits: 2 real ones**, both in push logs, not ship logs:
  - `28f1a8f7/tmp/push-coord-h.log`: 775 s, behind `ship fix/1606-enterworktree-guard`;
  - `2498695d/tmp/push-04f.log`: 393 s.
  - A third, 2 s, came from a test-fixture lock directory (`53b8d22d/tmp/locks`).
- **0 of the 50 ship logs waited on the lock.** Control arm: the same pattern does match in the push logs, so the probe can see waits.
- **Interpretation:** the lock almost never queues, because **the coordinator already serialises by hand** through `.agent/plans/main-checkout-ship-queue.md` (506 lines; the "HEAVY-SLOT QUEUE", "GATES GO", "SLOT <lane>" protocol). The human-maintained queue is the real scheduler today. The lock is a backstop.
- The queue file records what the hand protocol costs:
  - host load reached **128** (10-02, `host_lock.py:6-8`) and **206** (queue file, 22:50 entry), after which "ANY test run (targeted too) needs a 'SLOT <lane>' — one at a time host-wide";
  - a 57 s KB run took about 13 min under load;
  - KB3 started at load 17 and failed at load 84;
  - the order was rewritten **at least 8 times** in 3 days (every "Ship queue — CURRENT" block plus the "ORDER/QUEUE NOW/DOTFILES SHIP ORDER" lines).
- Host pre-push suite time ranges from **43 s to 296 s** for the same suite. The pytest durations in §1.3 logs (ship-handoff-l 43.5 s, ship-04g 296 s) show how sensitive it is to load.
- **Paths outside the lock** (re-verified in this tree): `host_lock.held` is called only at `pr.py:682`, `gate_result.py:168` and `command_audit.py:812`. `land_main` → `sync_main` (`pr.py:1031-1062`) takes no lock. The container work is outside its scope anyway (`host_lock.py:29-32`).

### 1.6 File overlap between concurrently open PRs

Source: `gh pr view <n> --json files` for every human dotfiles PR merged since 2026-09-28 (n=78; 13 files per PR median).
- Time-overlapping pairs, meaning PRs whose open intervals intersect: **18 pairs. 1 shared a file** (`python/verification/suites.toml`).
- Condition: PR open windows are short (p50 7 min) because `ship` opens the PR last. **Branch lifetime in worktrees is far longer**, and this PR-level number under-counts branch-level overlap. The conflicts the queue file records (`suites.toml` merge-tree rc=1, "rebase each", "SHIP LAST (after all mise.toml-touching branches)") happen at the branch level.
- **Hot files** across the 78 PRs:
  - `mise.toml` 15, `python/verification/suites.toml` 15;
  - `python/src/dotfiles_setup/main.py` 9;
  - `session-handoff/SKILL.md` (both mirrors) 8, `docs/agents/goal-history.md` 8;
  - `tests/TEST-INDEX.md` 6.
- These are append-mostly registries. Any branch-level conflict model should treat them as the conflict surface.
- **Docs/md-only PRs: 30 of 78 (38%).** These never need the container and take the fast ship path. **Devcontainer-surface PRs: 5 of 78**, but those 5 dominate wall time.

### 1.7 Origin (sessions/lanes)

- By job dir (source `logs.txt`): 33 distinct job dirs wrote ship/land logs in 3 days. The most were 7541ae79 (11), 97ffeddb (6), and 98eb9783, 2dffefaf and 1debf341 (5 each); most other dirs wrote 1–3.
  - The queue file shows the coordinator role passing through a successor chain every ~30% of context (e.g. 1b6fac → f9467b → d07ade → 5a11da), so many of these dirs are successive coordinators, not distinct lanes.
  - **I could not map job dir → role reliably** (no manifest records it). That is a finding in itself.
- The queue file shows that lanes normally do not ship themselves. They report "ready" and wait for a grant ("lane waits for SLOT L1 GRANTED", "SLOT MR-B-D", "SLOT kb-ship"). The coordinator then ships or GOes the lane's ship.
- Branch-prefix attribution (§1.1): `docs/handoff-*`, `docs/session-*` and `docs/*-research*` together are about 40% of human PRs. Handoff docs alone appear as ship-handoff-{,c,d,e,g,l,l2,m,r,s,04b,04c,04f,04g,04h}: **15 of 50 ship logs are handoff-doc ships**, all on the fast path.
- Not attributable: the merged-PR `author` is always `sortakool`, and lanes do not stamp a lane id into the branch or PR. **A scheduler must record the requester, because GitHub cannot reconstruct it.**

### 1.8 `.agent/gate-results/`

- Source: `ls -la` and `head -c 400 *.json` in the main checkout's `.agent/gate-results/`.
- The directory holds **one record per gate name, overwritten in place**: `lint.json`, `pytest.json`, `verify.json`, … with mtimes from 09-15 to 10-03. **It is not a time series, so it cannot feed duration statistics.**
- Last values: lint 20.4 s; pytest 365 s (10-01 15:55; the host suite under `gate run`); verify 0.66 s; pin-actions 4.2 s.
- `report.json` (10-03 13:40) records a pytest rc=1 (`test_mise_requirement_task_exposes_required…`, the nested-worktree test the queue file mentions at its 18:20 entry).
- **Design consequence:** an executing scheduler must append its own duration ledger (one line per run: kind, repo, tier, start, end, rc, waited_s). Without it, "use measured durations when available" (a3d6e816 Q3 priority rule 6) has nothing to read.

### 1.9 What the numbers say, in one paragraph

- **Remote CI is cheap and almost never fails for human PRs**: p50 7 min, 60/62 green (§1.2).
- **The scarce resources are all local** (§1.3–1.5), and they are three different resources, not one:
  1. **host CPU** for the pre-push suite (43–296 s) and the KB tests (180 s hard timeouts);
  2. **the dotfiles main checkout**: land does `git checkout main && pull` (`pr.py:1046-1052`), and a sync-full ship must run from MAIN (`pr.py:612-622`);
  3. **the dotfiles devcontainer**, used by the land smoke, a sync-full ship, and `dev-rebuild` (which kills in-container sessions; land-1662 log `WARN rebuilding`).
- Job durations are **bimodal and predictable by class**:
  - fast ship p50 2.7 min;
  - sync-full ship p50 about 40 min;
  - smoke land p50 11.6 min;
  - full land p50 40.2 min;
  - kb-ship about 5–6 min;
  - kb-land under 3.5 min.
- **KB tests are the only measured victims of overlap**: 4 timeouts on 10-02, all while dotfiles container work ran.
- Today one human-maintained queue serialises every one of these, so a 3-minute docs ship waits behind a 50-minute land that uses none of the resources the docs ship needs. That is Ray's inefficiency, and the data confirms it.

## 2. Algorithms and existing tools

### 2.1 The problem shape

This is **online, non-preemptive, multi-resource admission with precedence and priority**:
- a few exclusive capacity-1 resources (host CPU, main checkout, devcontainer, KB checkout);
- an unbounded remote resource (GitHub CI);
- jobs that each need a *subset* of the resources;
- DAG edges ("ship B after A merges", "SHIP LAST", stacked branches);
- uncertain but class-predictable durations.

Volume is about 20–40 jobs/day.
- Classical names for it: resource-constrained project scheduling (RCPSP), or a job shop with renewable resources.
- At this size, and with **online arrivals and uncertain durations**, the textbook offline optimum (CP-SAT makespan) is the wrong tool. The standard practice for online clusters is **priority list scheduling with backfilling**. Examples:
  - Slurm's backfill;
  - Kubernetes Kueue's `BestEffortFIFO`, where "older Workloads that can't be admitted will not block newer Workloads that fit in the available quota" (`kubernetes-sigs/kueue` `site/content/en/docs/concepts/cluster_queue.md:195-209`), against `StrictFIFO`, where they do block.

### 2.2 Approaches surveyed

| Approach | What it is | Fit here | Evidence |
|---|---|---|---|
| **GitHub merge queue** | Native. Temp `gh-readonly-queue/main/pr-N` branches combine main with every PR ahead in the queue; **speculative** CI runs in parallel up to "Build concurrency" 1–100; a failing PR is ejected and the groups behind it are rebuilt; min/max group size plus wait time give batching. | **Partial, dotfiles only.** It replaces merge ordering, combined-state testing and rebase churn. It does **not** touch the local host/container work (gates, push, land), which is where §1 puts the time. | `github/docs` `content/repositories/…/managing-a-merge-queue.md:32-45, 55-78, 84-110`. Availability: "any public repository owned by an organization" (`data/reusables/gated-features/merge-queue.md`). Both repos are public and org-owned (`gh api repos/ray-manaloto/<r>` → `visibility: public, owner.type: Organization`). |
| **Zuul dependent pipeline** | Speculative execution: "assumes that all jobs will succeed and tests them in parallel"; on failure, it re-tests the changes behind without the failing one. **Window** is AIMD, "inspired by the Transmission Control Protocol's flow control", default 20. | Its idea (an AIMD window on speculative parallelism) is the right model for *remote* CI. It is not a tool to adopt: it is heavyweight and Gerrit/GitHub-app based. | `zuul-ci.org/docs/zuul/latest/gating.html` § Testing in parallel, § Pipeline Window |
| **Bors-ng** | Batching merge bot. | **Deprecated**: "new features will not be accepted… use GitHub's built-in merge queue". | `bors-ng/bors-ng` `README.md:1-2` |
| **Mergify** | Hosted merge queue with `max_parallel_checks` speculative batches, priority queues and culprit ejection. | It adds a third-party service, and its value over the native queue (priorities, partitions) is not needed at this volume. | `docs.mergify.com/merge-queue/parallel-checks/` |
| **Kodiak** | Auto-update plus auto-merge bot. | It is superseded by native auto-merge, which `ship` already uses (`pr.py` `enable_auto_merge`). | `chdsbd/kodiak` `README.md:5-11` |
| **Kueue-style admission** | Per-resource quota queues; `BestEffortFIFO` backfill; cohorts borrow unused quota. | **The right mental model for the local half**: a ClusterQueue per local resource, with jobs admitted only when all their quota is free. | `kueue … cluster_queue.md:61-71, 195-209` |
| **Slurm-style EASY backfill** | The highest-priority waiting job gets a reservation; a lower one may start now only if it finishes before that reservation (it needs duration estimates). | It fits, because §1.3 durations are class-predictable. It is what turns "3-min docs ship waits 50 min" into "the docs ship runs now". | `slurm.schedmd.com/sched_config.html`: the backfill plugin "considers job run time and resources required to determine if lower-priority jobs would actually take resources needed by higher-priority jobs" |
| **Priority + aging** | Effective priority = base + age/τ, so nothing starves under backfill. | Required, because backfill alone can starve a long full-tier land. a3d6e816 Q3 asks for the same thing ("finite bypass limit", `sdlc-review-coordinator-roles-a3d6e816.md:106`). | Classic OS scheduling |
| **OR-Tools CP-SAT** | Exact RCPSP via interval vars + `AddCumulative`/`AddNoOverlap`. | **Rejected.** Offline makespan optimisation assumes known durations, but ours are bimodal and noisy (pytest 43–296 s for the same suite). Re-solving per event buys nothing over list scheduling at 20–40 jobs/day, and it adds a heavy wheel. | PyPI `ortools` 9.15.6755 (2026-01-14) |

### 2.3 Can GitHub's native merge queue replace part of it?

**dotfiles: yes, for the merge-ordering half. Nothing local.**
- Today `required_status_checks.strict` is **false**, with `contexts: ["ci-gate"]` (`gh api repos/ray-manaloto/dotfiles/branches/main/protection`).
  - So two green PRs that both touch `python/verification/suites.toml` or `mise.toml` (15/78 PRs each, §1.6) can merge without their *combination* ever having run CI.
  - The queue file records exactly that conflict class ("conflicts with origin/main … in suites.toml (merge-tree rc=1)").
  - A merge queue closes it without the rebase churn of `strict=true`.
- Cost and prerequisites:
  - `ci.yml` has **no `merge_group` trigger** (`ci.yml:2-37`; also `codex-advisor-promote-staleness-guard.md:226`). The docs say "You **must** use the `merge_group` event" (`managing-a-merge-queue.md:32`).
  - The `changes`/base-build path filters must work on merge groups, or every queued batch could pay the 35–58 min base path.
  - Renovate (51% of merges) would also queue.
  - The `promote` job must keep tagging correctly from a merge-group merge.
- It **does not** replace:
  - the host slot;
  - the push gates;
  - land's container smoke;
  - the decision of *when* a ship's local gates run.
- `proposals-heavy-slot-overlap-2026-10-03.md:114` says merge queue/auto-merge "are not applicable". That is correct for the **CPU** question, and too strong for the **ordering and combined-testing** question.

**knowledge-base: not as configured.**
- `strict: true`, required check `Verify signed exact-head live evidence`, run from `pull_request_target` against `github.event.pull_request.head.sha` (`knowledge-base/.github/workflows/graphify-live-receipt.yml:3-24`). A merge-group commit has a different SHA (`managing-a-merge-queue.md:49`), so the exact-head evidence cannot be satisfied in a queue without redesigning that check.
- KB also has `allow_auto_merge: false` and merges with `kb-land` (`gh pr merge … pinned to <sha>`).
- The measured KB cost of `strict` is kb-land 865 ("base branch policy prohibits the merge").

### 2.4 Library and tool fit

| Candidate | Version / health | Fit |
|---|---|---|
| **stdlib `graphlib.TopologicalSorter`** | Python ≥3.9 stdlib; its `prepare()`/`get_ready()`/`done()` API is built for online DAG execution (docs.python.org/3/library/graphlib.html) | **Use for precedence.** It has no dependency. |
| **stdlib `heapq` + `sqlite3`** | stdlib | **Use for the priority queue and the durable state.** A single-host, single-writer queue does not need a broker. |
| **networkx** | 3.7 (2026-09-21); 3.6.1 already in this venv through graphify (`graphify.py:153`) | Only needed if graph queries go beyond topo order, e.g. transitive holds. Optional. |
| **pueue** (`Nukesor/pueue`) | v4.0.4 (2026-03-02), 6.3k stars, last push 2026-09-09, **feature-complete / maintenance mode** (`README.md:20`) | It provides groups with per-group parallelism, `--after` dependencies, crash-persistent logs, `restart`, `wait`, and full macOS support (`README.md:35-59`). **Gap:** a task sits in ONE group, so it cannot require host CPU **and** main checkout **and** devcontainer at once, and it has no priority aging. It is not in mise's short-name registry (`mise registry` 1057 rows; the controls `jq` and `ripgrep` are found, `pueue` is absent). It **is** in the aqua registry at `pkgs/Nukesor/pueue/pueue/registry.yaml` (`gh api search/code q=repo:aquaproj/aqua-registry+pueue` → 6 hits), so it can be pinned as `aqua:Nukesor/pueue`. My first probe at `pkgs/Nukesor/pueue/registry.yaml` returned 404, while the control `pkgs/jqlang/jq/registry.yaml` returned 200, so that probe had the wrong path depth. It is a credible *executor* under our own admission policy, not a scheduler. |
| huey 3.4.0 (SqliteHuey) / procrastinate 3.10.0 (Postgres) / APScheduler 3.11.3 | maintained | Task queues for *worker pools*. They add a consumer process model without solving multi-resource admission. Not recommended. |
| OR-Tools 9.15 | maintained | Rejected in §2.2. |
| `fcntl.flock` (`host_lock.py`) + `/usr/bin/lockf -k` | in tree, two cold reviews | **Keep it as the enforcement floor.** The scheduler should *hold* the locks it admits against, so an out-of-band run still serialises (`proposals-heavy-slot-overlap-2026-10-03.md:65-80`). |

**Conclusion for §2:** no single existing tool covers multi-resource admission with priority aging and DAG precedence for local jobs. The established algorithm is **priority list scheduling with aging and EASY backfill over per-resource exclusive quotas** (Kueue `BestEffortFIFO` semantics plus Slurm-style reservation), which is about 150–250 lines of policy on stdlib `heapq`/`graphlib`/`sqlite3`. Delegate everything else:
- merge ordering and combined testing → the GitHub merge queue (dotfiles);
- CI waiting → native auto-merge;
- mutual exclusion → the existing `flock`;
- optionally, process supervision and logs → pueue.

## 3. Recommended design: an executing scheduler

### 3.1 Shape

- One **host-wide daemon**, `dotfiles-setup ship-scheduler serve`, spans **both repos**, because they share the CPU (§1.4).
- It runs under launchd the same way the existing `dag-tick` LaunchAgent does (`dag_tick.py:1-10`, `mise.toml [bootstrap.macos.launchd.agents]`). That makes it an out-of-session executor that survives coordinator handoffs, which matches the auto-handoff memory lesson that this needs an out-of-session trigger.
- State lives in one SQLite file under `$XDG_STATE_HOME/dotfiles/ship-scheduler.db`, with WAL mode and a single writer: the daemon.
- It is the **only** process that invokes `pr.ship_main`, `pr.land_main` and the KB `kb-ship`/`kb-land`. It calls them as in-process functions or as `mise run` children it supervises; it does not re-implement them.
- Logs go to `…/ship-scheduler/runs/<id>.log`, with the real rc recorded in the DB. That ends the `echo rc=$? >> LOG` pattern and its notification-lies trap (`feedback_background_task_notification_can_lie`).
- Option B, for Ray: pueue as the process supervisor. The daemon admits a job, then `pueue add --group <class> …`. This trades our ~50 lines of subprocess supervision for a second daemon (§2.4).

### 3.2 Request interface (what lanes and the coordinator call)

```
mise run ship-request -- --repo dotfiles|knowledge-base --kind ship|land \
     --branch <b> --sha <expected-head> --worktree <abs path> \
     [--pr <n>] [--after <request-id|pr#>]... [--priority normal|high|handoff] \
     [--requester <lane name>]            # → prints request id, returns immediately
mise run ship-queue                       # read-only: queue, running jobs, held resources, reasons
mise run ship-status -- <id> [--wait <s>] # bounded wait on one request (bounded-wait semantics)
mise run ship-cancel -- <id> / ship-hold -- <id> / ship-release -- <id>
```

- **`--sha` is mandatory.** The scheduler refuses to run if the branch head moved, the same "pinned to <sha>" idea `kb-land` already uses (KB land log: "merging PR #865 pinned to 3eb8255cb982").
- **`--requester` is recorded**, because GitHub cannot attribute lanes (§1.7).
- A `land` request is **auto-enqueued by the scheduler** when a PR it shipped reaches `MERGED`. It polls `gh pr view <n> --json state` at a low rate and owns that wait, so lanes never wait on it.
- Completion goes to `ship-status`. Optionally the daemon also delivers a notification through the lane's existing handoff-inbox file (`.agent/plans/handoff-inbox/<lane>.md`, per the queue file 18:05 ruling). It does not use SendMessage, which expires across sessions (queue file header).
- **Enforcement (machine, not prose):**
  - `ship_main`/`land_main` refuse unless they run under the scheduler, via an env token the daemon sets and verifies against its DB, plus the lock it holds.
  - Add a `hook_guard` redirect from `mise run ship|land|kb-ship|kb-land` to `ship-request`, following the `mise-tasks-only.md` "Extending" recipe.
  - The hook fails open (#343), so the in-tool refusal is the load-bearing layer.

### 3.3 Queue model: per-resource, not per-repo

The data supports per-resource queues (§1.9). Resources are all exclusive, capacity 1, and **held as real locks by the daemon while a job runs**, so a non-scheduler run still serialises.

| Resource | Lock | Held by |
|---|---|---|
| `cpu` (host heavy) | existing `heavy-gate` flock | dotfiles ship gates+push (incl. pre-push suite); kb-ship gates; `gate run` |
| `df-main` (dotfiles main checkout) | new flock | dotfiles land; sync-full ship (must be from MAIN, `pr.py:612`) |
| `df-container` (dotfiles devcontainer) | new flock | land smoke/full sync; sync-full ship; verify-local; dev-rebuild |
| `kb-main` (KB main checkout) | new flock | kb-land (`git pull --ff-only`) |
| GitHub CI | not a resource | unbounded; ship returns after arming auto-merge |

Job classes, with the resources each needs and its measured duration prior (§1.3/§1.4):

| Class | Needs | Prior p50 / p90 (min) |
|---|---|---|
| df-ship-fast (no devcontainer surface) | cpu | 2.7 / 4.7 |
| df-ship-full (`needs_full_sync`, `pr.py:283`) | cpu + df-main + df-container | ~40 / 61.5 |
| df-land-smoke | df-main + df-container (+ cpu, see decision D2) | 11.6 / 17.3 |
| df-land-full | df-main + df-container (+ cpu, D2) | 40.2 / 52.6 |
| kb-ship | cpu (+ "no df-container active", D2) | ~5.5 / ~12 |
| kb-land | kb-main | <3.5 |

**Algorithm**, in the order the daemon applies it each time an event arrives (a request, a completion, a merge observed, or a 60 s tick):

1. **Eligibility (hard filters first, as a3d6e816 Q3 rules 1–2 require):** a job is eligible only if:
   - it is not held;
   - every `--after` predecessor is done (`graphlib.TopologicalSorter`, cycle → refuse);
   - its `--sha` still matches the branch head;
   - its PR is mergeable or unknown (not CONFLICTING);
   - for a land, its PR is `MERGED`.
2. **Order** eligible jobs by effective priority = class base (`handoff` > `high` > `normal`) + age / τ (aging, so nothing starves), with ties broken by request time.
3. **Admit with EASY backfill:**
   - The head job takes a **reservation** for its resources at the earliest time they free, estimated from the p90 of running jobs.
   - Any later job whose resources are free **now** starts if its own p90 estimate ends before the head job's reservation, or if it shares no resource with the head job. Example: a 3-min docs ship (`cpu`) starts during a 40-min land (`df-main`+`df-container`).
   - A finite **bypass limit**: once a job has been backfilled past N times (default 3), it becomes non-bypassable, matching a3d6e816's "finite bypass limit, persisted across scheduler replacements" (`:106`). The counter lives in the DB, so it survives restarts.
4. **Coalesce lands (batching, merge-queue style):**
   - `land` is a per-PR cheap check (`_land_post_merge`, `pr.py:990-1029`) plus an expensive `sync_main` on the current main (`pr.py:1054-1059`). When several merged PRs are waiting, run the per-PR checks for all of them, then **one** `sync_main(full=any(surface))` on the newest main.
   - The queue-file chain "1662 → 1663 → 1664 → 1469 → 1666 → 1647, then 1658, 1665, 1667" is 9 syncs that would become 1–2.
   - On failure, bisect only if the failure is content-classed (see §3.5).
   - **This changes land's attribution semantics, so it is decision D3.**
5. **Duration ledger:** every run appends (class, repo, tier, start, end, rc, waited_s, failure signature). Priors come from the ledger's per-class p50/p90 once n ≥ 5, falling back to the table above. **An unknown duration uses the class p90, never zero** (a3d6e816 Q3 rule 6).

### 3.4 What may overlap safely, and what must not

| Pair | Overlap? | Evidence |
|---|---|---|
| any local job ∥ GitHub CI of other PRs | **yes** | CI is remote; `ship` returns after arming auto-merge |
| df-ship-fast ∥ df-land (smoke/full) | **yes if D2 = "container ≠ cpu"** | resource sets are disjoint except shared physical CPU; no dotfiles test failure attributed to that overlap was found in §1.3 (condition: no controlled A/B exists) |
| kb-ship ∥ df-land / df-ship-full | **no** (until KB timeouts are fixed) | 4/4 KB load timeouts on 10-02 coincided with dotfiles container work (§1.4) |
| kb-land ∥ anything except kb-land | **yes** | no CPU-heavy step; 0.2–3.2 min |
| df-land ∥ df-land | **no**: coalesce instead | both need `df-main` + `df-container` |
| df-ship-full ∥ df-land | **no** | both need `df-main` + `df-container` |
| two df-ship-fast | **no** | both need `cpu` (pre-push suite), and the suite time is load-sensitive (43–296 s) |
| dotfiles ship ∥ KB ship | **no** | both need `cpu` |

### 3.5 Failure handling

Failures are classified by **log signature** before any retry, reusing the existing table in `.claude/rules/persistence-gate-retry.md` and extending it with §1.3/§1.4 signatures.

| Class | Signatures (measured) | Action |
|---|---|---|
| environmental, retry once | `git push rc=141`; `getaddrinfo ENOTFOUND`; `parent snapshot … does not exist`; land smoke `TimeoutExpired … 1800.0 seconds` after `CONTAINER OUTDATED`; `Cannot fast-forward to multiple branches`; KB `timed out waiting for reply` / `timed out after 180s` | retry **once**, automatically, with the resource still reserved; a second identical failure → park + notify |
| precondition, no retry | dirty tree; linked-worktree refusal (`pr.py:612-622`); head moved; PR CONFLICTING | park at once and notify the requester with the exact message (it costs 0 min, §1.3) |
| content | pytest assertion (e.g. `test_session_review.py:1106` ×3, `test_session_gate.py:307`); lint; `kb-manifest-audit` DRIFT | **never auto-retry.** Park, notify the requester, and release resources immediately. |
| unknown | anything else | park + notify; never retry |

Further rules:
- **Crash and restart:** a running job's lock dies with its process (the `flock` kernel-release property, `host_lock.py:12-15`). On restart the daemon marks such jobs `interrupted` and treats them as environmental (retry once). Ship is safe to replay: `gh pr view` finds the open PR (`pr.py:640-643`). Land is idempotent (`pr.py:1031-1041`).
- **Holds and Ray rulings** are first-class rows (`ship-hold`), not prose in a markdown queue. They replace `.agent/plans/main-checkout-ship-queue.md` (506 lines, rewritten ≥8 times in 3 days).
- **Renovate:** the scheduler does not own bot merges. Each bot merge to `main` does, however, mark queued ship jobs whose branches touch the same hot files as "re-check mergeable" before admission.

### 3.6 Decisions for Ray

- **D1. GitHub merge queue on dotfiles.** Adopt it, which needs `merge_group` in `ci.yml`, path-filter work, and a check that Renovate and `promote` still behave? It gives combined-state testing for the `suites.toml`/`mise.toml` conflict class, and the scheduler then never orders merges. Recommended: **yes, as a separate PR after the scheduler**. KB stays as it is: the exact-head evidence check is incompatible (§2.3).
- **D2. Is container work a `cpu` holder?** This is the single biggest throughput lever.
  - "No" lets fast ships run during 40-min lands (§3.4).
  - "Yes" keeps today's effective serialisation.
  - Recommended: "no" for dotfiles ships, "yes" for kb-ship until the KB timeout fixes land. Validate first with one controlled A/B: the dotfiles suite alone vs. during a land smoke. That A/B has not been run.
  - This also answers the `host_lock.py:29-32` constraint: the scope gap is real, and the measured victims are KB only.
- **D3. Land coalescing.** One sync validates N merged PRs. Throughput gain: 9 syncs → 1–2 on the current backlog. Cost: a failure needs bisection to attribute.
- **D4. Hard enforcement.** Make `ship_main`/`land_main` refuse outside the scheduler, and redirect direct `mise run ship|land|kb-ship|kb-land` in `hook_guard`. Ray asked that the scheduler be "the only thing allowed to decide", so recommended: yes. Keep an operator escape that the DB records, not a bypass flag: `ship-scheduler drain`, then a direct run.
- **D5. Executor: pure-Python subprocess supervision vs pueue.** Recommended: pure Python. The supervision part is small, pueue cannot express multi-resource jobs, and it would be a new daemon, although it is pinnable as `aqua:Nukesor/pueue`.
- **D6. Docs-only ships and the pre-push suite.** 38% of human PRs are docs/md-only (§1.6) but still pay the full host suite under `cpu`. Exempting them, or giving them a lighter suite, is a policy change outside the scheduler. Flagged, not recommended either way.
- **D7. Does the KB shipper become a client of this daemon?** It lives in dotfiles but executes KB tasks. The alternative is a KB-side twin sharing the same lock files, which is the `lockf -k` interop measured in `proposals-heavy-slot-overlap-2026-10-03.md:104-112`. Recommended: **one daemon**, because the conflict is the shared CPU, not the repo.

### 3.7 Not measured / gaps (stated so the next pass does not redo the search)

- No controlled A/B of the dotfiles suite under concurrent container smoke (D2).
- Branch-level, as opposed to PR-level, file overlap between concurrent lanes. §1.6 under-counts because PR windows are short.
- Job dir → session role mapping: no manifest records it (§1.7).
- Ships run by hand outside `~/.claude/jobs/*/tmp/` are not in §1.3.
- CI duration is `updatedAt − createdAt`, which over-states re-run runs.
- `feedback_ci_build_duration_baseline` (about 10 min warm, about 2.5 h cold) is inherited and was not re-derived.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): merged PRs, CI runs, rulesets/branch protection, PR file lists; source `host_lock.py`, `pr.py`, `container.py`, `gate_result.py`, `dag_tick.py`, `ci.yml`
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): merged PRs, branch protection, `graphify-live-receipt.yml`
- [github/docs](https://github.com/github/docs): merge-queue page, gated-features and overview reusables
- [bors-ng/bors-ng](https://github.com/bors-ng/bors-ng): README deprecation notice
- [chdsbd/kodiak](https://github.com/chdsbd/kodiak): README feature list
- [Nukesor/pueue](https://github.com/Nukesor/pueue): README features, latest release, repo health
- [kubernetes-sigs/kueue](https://github.com/kubernetes-sigs/kueue): ClusterQueue queueing strategies and cohorts
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry): pueue package present at `pkgs/Nukesor/pueue/pueue/` (code search; an earlier wrong-depth path returned 404, and the jq control returned 200)
- Non-GitHub: zuul-ci.org gating docs; docs.mergify.com parallel checks; slurm.schedmd.com sched_config; docs.python.org graphlib; pypi.org JSON for ortools/huey/networkx/procrastinate/apscheduler/persist-queue (control: a bogus package returned 404)
