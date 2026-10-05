**Review complete: partial failure under licensed dissent.** All four specialists finished. Two fan-out lanes are viable, but #1554’s unconditional ship readiness is held pending a test-policy contradiction. No checkout changes, report files, repository gates, containers, commits, pushes, ships, or lands ran.

### SHIP/LAND list

All listed branches and full head SHAs were verified from `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` using `git rev-parse --verify`, rc=0. Each PR view returned rc=0.

| Branch / PR | Verified head SHA | Observed status | Coordinator action from MAIN |
|---|---|---|---|
| `fix/ops-sync-1478-1481` / [#1570](https://github.com/ray-manaloto/dotfiles/pull/1570) | `60fc34ce966b8d6977a7bc6d4eda6b48356f2758` | MERGED; land receipt rc=0 | Complete; do not reship |
| `docs/lane-g-reports` / [#1589](https://github.com/ray-manaloto/dotfiles/pull/1589) | `52d8a07cdef97e21bf7053fd9fa56b51debc8f9e` | MERGED; first land failed rc=1, retry rc=0 | Complete; do not reship |
| `fix/1631-install-doctor-newer` / [#1663](https://github.com/ray-manaloto/dotfiles/pull/1663) | `4c2691c5d9d87cfd1a47adb03e58487a767de6c6` | MERGED; land completion unverified | Finish/adopt existing `land -- 1663`; capture rc |
| `docs/brief-review-field` / [#1664](https://github.com/ray-manaloto/dotfiles/pull/1664) | `ff310d4564f1e1084beb60cc9d97481e2326ea96` | MERGED; land completion unverified | Finish/adopt existing `land -- 1664`; capture rc |
| `fix/1554-container-image-id` / issue [#1554](https://github.com/ray-manaloto/dotfiles/issues/1554) | `15c1061dafae16076ba1590827a9cb05d9eab903` | No PR found; G records re-lens CLEAN; **readiness held by this review** | Reconcile test-policy finding, then ship from MAIN with required gates and sync-full |

Recorded land evidence: [#1570 receipt](/Users/rmanaloto/.claude/jobs/7541ae79/tmp/land-1570.log:11570), [#1589 failed attempt](/Users/rmanaloto/.claude/jobs/2dffefaf/tmp/land-1589.log:9), [#1589 successful retry](/Users/rmanaloto/.claude/jobs/2dffefaf/tmp/land-1589b.log:5740). These are historical receipts inspected during this review.

Controls were armed: an absent Git ref returned rc=128, `fatal: Needed a single revision`; nonexistent PR `2147483647` returned rc=1, `Could not resolve to a PullRequest`.

Shipping remains serial under `dotfiles-20261004T120251.264509000-05.coordinator`. Complete existing lands before supplying the refreshed implementation baseline. Do not repeat an in-flight land operation.

### Contradictions and stale claims

1. **#1554 introduces prohibited internal mocks.** At the candidate SHA, the new test beginning at `tests/test_sync.py:599` patches `observe`, `_report_inflight`, `resolve_names`, `local_image_id`, `_stream`, and `verify_latest` at lines 608–615. Both candidate and current `tests/AGENTS.md:92–100` require mocks at system boundaries and prohibit mocking internal collaborators. Existing tests use similar scaffolding, but no applicable exception was found. G’s fake-Docker ruling does not waive this rule. Stop the readiness assessment until the new test is reconciled while preserving its post-lifecycle daemon-failure fail arm. [Candidate test](https://github.com/ray-manaloto/dotfiles/blob/15c1061dafae16076ba1590827a9cb05d9eab903/tests/test_sync.py#L599), [candidate rule](https://github.com/ray-manaloto/dotfiles/blob/15c1061dafae16076ba1590827a9cb05d9eab903/tests/AGENTS.md#L92).

2. **The mount specification and branch still bundle #1554.** `fix/1554-1555-worktree-mount` exists at `41aa326383a455559d1295fb335dcae3a5509c19`. It contains older `sync.py` and test changes alongside the draft specification. Its combined implementation/commit instructions contradict the later split. Carry forward and correct the specification only; base implementation on MAIN after resolved #1554 lands. [Draft specification](https://github.com/ray-manaloto/dotfiles/blob/41aa326383a455559d1295fb335dcae3a5509c19/docs/specs/1554-1555-worktree-git-mount.md#L8), [current remaining work](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-G-20261002/.agent/kb/raw/lanes/G.md:201).

3. **#1540/#1555 issue bodies retain the earlier refusal design.** Their live bodies request early refusal, whereas Ray’s later ruling requires a read-write common-dir mount and retirement of ship refusal. Reconcile the existing issues before implementation; do not file another ticket. [#1540](https://github.com/ray-manaloto/dotfiles/issues/1540), [#1555](https://github.com/ray-manaloto/dotfiles/issues/1555), [mount ruling](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-G-20261002/.agent/kb/raw/lanes/G.md:115).

4. **The mount does not resolve lane-local `land`.** `land_main` runs `git checkout main` in the caller’s workspace. MAIN already owns that branch; mounting Git metadata does not remove this checkout collision. Record explicit acceptance criteria under #1540/#1555 and preserve coordinator-owned landing from MAIN. [pr.py:1050](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/pr.py:1050).

5. **Graphify is no longer a #1555 dependency.** Round 6 explicitly decouples it. Graphify memory research remains coordinator-owned and outside this split. [G.md:197](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-G-20261002/.agent/kb/raw/lanes/G.md:197).

6. **#1632 still says “fix after TRIM.”** A quota reset and earlier MEMORY.md curation do not establish release of that instruction. Hold implementation until the coordinator establishes that prerequisite. Dedicated #1632 and #1553 specifications are owed. [#1632](https://github.com/ray-manaloto/dotfiles/issues/1632), [G.md:212](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-G-20261002/.agent/kb/raw/lanes/G.md:212).

7. **MAIN’s fallback inbox is inaccessible to isolated lanes.** Use a lane-local `.agent/plans/handoff-inbox/<lane>.md` and require coordinator harvest. Writing that file does not establish delivery. [G.md:149](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-G-20261002/.agent/kb/raw/lanes/G.md:149).

### Blast radius and merge evidence

| Work | Principal file ownership | Scheduling consequence |
|---|---|---|
| #1554 | `sync.py`, `tests/test_sync.py` | Resolve and land before dependent implementation |
| #1555/#1540 | Devcontainer mount configuration; selected host preparation seam; `pr.py`; affected Git/config tests and skills | Container slot and post-probe design decision required |
| #1553 | Shared probe module; `doctor.py`, `sync.py`, `pr.py`; corresponding tests | Same sole-writer lane as #1555; separate ordered deliverable |
| #1632 | `memory_index.py`, its tests, focused `main.py` wiring, curation skills/mirrors | Independent lane after TRIM clearance; coordinate hot-file registrations |

#1555 and #1553 share non-hot files, so they belong in one serial lane under the [parallel-work-split grouping rule](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/.agents/skills/parallel-work-split/SKILL.md:72).

The read-only conflict control was:

```text
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles merge-tree \
  b9a027f63982b33d9acf326cc9a604544bfa1dbc \
  fix/1554-container-image-id fix/1554-1555-worktree-mount
```

It returned **rc=0 while emitting conflict markers** in `sync.py` and `tests/test_sync.py`. The old branch retains running-only selection against #1554’s running/paused/restarting behavior. Do not merge it wholesale.

Main-versus-branch outputs were complete and showed no conflict markers. Of 45 inventory comparisons, 32 outputs were complete and 13 were truncated; those 13 remain **UNKNOWN**. Legacy merge-tree rc=0 alone establishes no merge-safety conclusion.

Graph freshness was not established. Read-only co-change history returned rc=0 and reinforced hot-file treatment for `mise.toml`, `mise.lock`, `suites.toml`, and `main.py`. Predicted unwritten changes remain untested for merge conflicts.

### FAN-OUT plan

Names and worktrees below are proposed; none were created or launched.

| Field | Mount and shared probes | Memory index |
|---|---|---|
| Lane | `dotfiles-20261004T120251.264509000-05.worktree-mount-probes` | `dotfiles-20261004T120251.264509000-05.memory-index` |
| Worktree | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/worktree-mount-probes-20261004` | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/memory-index-20261004` |
| Branch | `fix/1555-worktree-mount-probes` | `fix/1632-memory-index` |
| Base | Coordinator-confirmed MAIN after resolved #1554 lands; record actual SHA | Coordinator-confirmed MAIN at launch; record actual SHA |
| Issues | #1555, existing #1540 acceptance gap, then #1553 | #1632 |
| Specification | Correct branch-held `docs/specs/1554-1555-worktree-git-mount.md`; #1553 spec owed | Spec owed: `docs/specs/1632-memory-index.md` |
| First actions | Correct stale scope; reserve next container slot; design isolated probe matrix | Establish TRIM clearance; define settings precedence, missing-state rc, and dropped-lesson coverage |
| Sequence | Both mount-design probes → one decision to Ray → #1555 deliverable → coordinator ship/land → #1553 behavior-preserving extraction | Independent after clearance; coordinate registration ownership |
| Container slot | Required for probes and linked-worktree validation | Conditional if verification registrations require sync-full |
| Future gates | Lint, full pytest, verify, lint-docs; #1555 also real linked-worktree verify-local and image verification | Lint, full pytest, verify, lint-docs |

For #1555, scratch probes must arm broken/missing mounts, explicit pruning with and without locks, and aged-metadata GC with and without the expiry guard. Measure image Git/tool compatibility, preserve R1/R2/R3 and persistence, and retire `_RC_LINKED_WORKTREE` only with successful real linked-worktree verification.

For #1632, use isolated memory/configuration and real main/linked Git fixtures. Exercise missing directory/index—including `--refs`—and covered, uncovered, and explicitly waived dropped lessons. Reverting each requested behavior must fail its corresponding assertion.

### Ready-to-paste launch briefs

Each brief is within 25 lines.

```text
LANE dotfiles-20261004T120251.264509000-05.worktree-mount-probes; #1555/#1540 then #1553.
WORKTREE: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/worktree-mount-probes-20261004
BRANCH: fix/1555-worktree-mount-probes
BASE: coordinator-confirmed MAIN after resolved #1554 lands; record exact SHA.
CWD: coordinator launches inside your worktree; do not create another or enter MAIN.
SPEC: carry only docs/specs/1554-1555-worktree-git-mount.md from 41aa3263; correct to #1555-only.
Reconcile existing #1540/#1555 acceptance criteria, including the land checkout collision.
#1553 SPEC OWED: define behavior-preserving probe extraction before its implementation.
OWN ONLY: approved mount/probe files, tests, specs, applicable skills/mirrors, and lane reports.
Do not edit task_plan.md, other lanes' files, or unassigned hot-file registrations.
#1555 is decoupled from Graphify; request the next coordinator-granted container slot.
Probe BOTH mount layouts using disposable repositories/worktrees/containers.
Arm broken mounts, prune with/without locks, aged GC with/without expiry guard, and image Git compatibility.
Bring Ray ONE evidence-backed design decision before implementing the rw mount.
Preserve R1/R2/R3 and persistence; real linked-worktree verify-local must prove refusal retirement.
After coordinator ships/lands #1555, rebase and implement #1553 as a separate ordered deliverable.
Use public interfaces and realistic revert fail arms; preserve probe behavior and typed errors.
NATIVE-FIRST: use required research routes for implementation research; record failed routes.
FUTURE GATES: lint, full pytest, verify, lint-docs, verify-local, verify-container-latest as applicable.
Run heavy/container gates only in granted slots; record real rc and tested HEAD.
PERSIST incrementally: docs/research/kb/reports/agents/worktree-mount-probes-20261004.md.
REPORT TO dotfiles-20261004T120251.264509000-05.coordinator; successor by recency after handoff.
FALLBACK: lane-local .agent/plans/handoff-inbox/worktree-mount-probes.md; coordinator must harvest.
STOP AT reviewed branch commits; never push, ship, land, or open a PR; coordinator ships from MAIN.
Licensed dissent: stop affected contradictory work and report anchored evidence.
```

```text
LANE dotfiles-20261004T120251.264509000-05.memory-index; #1632.
WORKTREE: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/memory-index-20261004
BRANCH: fix/1632-memory-index
BASE: coordinator-confirmed MAIN at launch; record exact SHA.
CWD: coordinator launches inside your worktree; do not create another or enter MAIN.
HOLD implementation until coordinator establishes the “after TRIM” prerequisite.
SPEC OWED: docs/specs/1632-memory-index.md; resolve semantics before coding.
OWN ONLY: memory_index.py, its tests, approved CLI wiring, spec, curation mirrors, and lane reports.
Coordinate main.py and any verification/test-index registrations with their existing owners.
Do not edit mount/probe files, actual user memory, task_plan.md, or unrelated hot files.
FIRST: define main/worktree memory resolution, autoMemoryDirectory precedence, and missing-state rc.
Define deterministic dropped-lesson coverage and explicit waiver handling; do not guess prose semantics.
NATIVE-FIRST: reuse existing main-checkout/settings helpers where their interfaces fit.
TEST through public CLI interfaces with isolated memory/config and real main/linked Git fixtures.
Arm worktree equality, missing directory/index including --refs, and covered/uncovered/waived lessons.
Every requested behavior needs a realistic fail arm when reverted.
FUTURE GATES: lint, full pytest, verify, lint-docs; record real rc and tested HEAD.
Request granted heavy-run slots; request container slot if delivery-surface registrations require it.
Review BASE with cold/standards review; /code-review receives TARGET HEAD.
PERSIST incrementally: docs/research/kb/reports/agents/memory-index-1632-20261004.md.
REPORT TO dotfiles-20261004T120251.264509000-05.coordinator; successor by recency after handoff.
FALLBACK: lane-local .agent/plans/handoff-inbox/memory-index.md; coordinator must harvest.
STOP AT reviewed branch commits; never push, ship, land, or open a PR; coordinator ships from MAIN.
Licensed dissent: stop affected contradictory work and report anchored evidence.
```

### Specialist verification and routes

| Specialist | Ownership | Gate result |
|---|---|---|
| Python | Candidate tests, probe extraction, memory-index behavior | pytest **NOT RUN — review mode** |
| Configuration | File overlap, refs, merge-tree controls, hot files | lint **NOT RUN — review mode** |
| Image | Mount safety, container acceptance, land gap | verify-container-latest **NOT RUN — review mode** |
| Documentation | Stale instructions, prerequisites, launch briefs | lint-docs **NOT RUN — review mode** |

No gate failure occurred because gates were prohibited. The partial-failure disposition reflects specification/policy contradictions.

Actual routes: collaboration tools; `exec_command`; `git`, `gh`, `rg`, `cat`, and Python for read-only text formatting; `codex-sdlc-team` and `parallel-work-split` skills. No external research-provider apps/plugins or CLIs ran.

Failed read routes were retained: nonexistent `.agent/gates` and working-copy handoff reads returned rc=2; the handoff was recovered through `git show`, rc=0. Documentation’s incorrect persistence-rule filename returned rc=1, then the corrected file read succeeded. Its combined `--comments`/`--json` query returned rc=1; a subsequent empty comments read was not used as authorization.

## GitHub repos touched

`ray-manaloto/dotfiles` only, through read-only PR/issue queries. No GitHub mutations occurred.

No others were spawned.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-image-specialist` — `/root/image_review`
- `sdlc-documentation-specialist` — `/root/documentation_review`

