# Consolidated Phase 17 review — one cross-lane ranking

Scope: consolidated ranking of the devcontainer/image, repeated-issue,
context-loss, and Codex-lane reviews against Phase 17
(`task_plan.md:1418-1458`). Ranking is by recurrence prevention first, then
value per effort; a documented instruction ranks below a machine boundary that
can reject the recorded failing case.

## 1. Reprioritised ranking across all four themes

### 1. Add a CAS-safe, scoped exact-pin repair on Renovate PR synchronization

- **Action:** Derive changed exact pins and their lock owner, repair only those
  named tools through Linux `lock-shared` plus a named-tool image-lock mode,
  require the Renovate head to remain unchanged before push, and prove every
  unrelated lock byte stays fixed.
- **Lanes:** **Merged duplicate** — devcontainer action 5
  (`.agent/logs/plan-review-devcontainer.md:17`) and repeated-issues action 1
  (`.agent/logs/plan-review-repeated-issues.md:7-15`).
- **Evidence:** #887 is explicitly recurrent (`task_plan.md:1435`); the
  existing gate distinguishes stale and matching exact pins
  (`tests/test_lock_coverage.py:358-402`), but the only refresh trigger is
  schedule/manual and wholesale refresh deliberately re-resolves floating pins
  (`.github/workflows/refresh.yml:12-18,32-41`). A Renovate force-push already
  overwrote two unpushed repair commits (`task_plan.md:1436`), and a nominally
  read-only `mise outdated` already mutated `mise.lock`
  (`task_plan.md:1431`), so head compare-and-swap and a clean-tree control are
  required parts of the repair, not optional hardening.
- **Why #1:** It closes the missing repair edge for a replay-proven recurrent
  CI failure while reusing a detector that already has red and green arms
  (`.agent/logs/plan-review-repeated-issues.md:9-15`). It outranks the one-off
  #822 closeout because it prevents the next Renovate PR from recreating the
  same split (`.agent/logs/plan-review-devcontainer.md:17`).

### 2. Make terminal PR state and prior obligations first-class handoff data

- **Action:** Query `gh pr list --state all`, model `MERGED`/`CLOSED` plus
  0/1/many rows, render the owed post-merge verb, and require every successor
  handoff to mark each prior `OWED` item `DONE`, `STILL OWED`, or
  `SUPERSEDED (reason)`.
- **Lanes:** **Merged within the context-loss lane** — actions 1 and 2
  (`.agent/logs/plan-review-context-loss.md:11-21`); no other lane raised this
  loss class (`.agent/logs/plan-review-context-loss.md:73`).
- **Evidence:** The current implementation explicitly asks only for open PRs,
  maps an empty result to `NONE`, takes `rows[0]`, and renders “open PR: none”
  (`python/src/dotfiles_setup/session_state.py:194-229,273-286`); its enum test
  admits only `none/open/unverifiable` (`tests/test_session_state.py:348-353`).
  Independently, `land -- 890` disappears between two successor handoffs
  without a disposition (`.agent/logs/plan-review-context-loss.md:17-21`).
- **Why #2:** This is a silent omission at the point where a merged PR should
  become an owed local gate, so it can skip work while still producing a
  plausible orientation report (`.agent/logs/plan-review-context-loss.md:13-15`).
  One end-to-end state/obligation contract prevents both observed losses.

### 3. Split deterministic background jobs from reasoning-lane verdicts

- **Action:** Reject `codex-operator`; run an already-authorized `mise` task as
  the background process and capture its exit directly, while allowing review
  or advisory work to advance only from a schema-valid verdict artifact.
- **Lanes:** **Merged duplicate with a resolved design tension** —
  repeated-issues action 2 (`.agent/logs/plan-review-repeated-issues.md:17-25`)
  and Codex-lanes action 1 (`.agent/logs/plan-review-codex-lanes.md:11-15,79-81`).
- **Evidence:** The recorded failure was wrapper rc 0 over inner rc 2
  (`task_plan.md:1443-1444`). `codex-lane` intentionally returns 0 for
  launch-and-settle even when Codex is nonzero
  (`python/src/dotfiles_setup/codex_lane.py:569-612`), while missing or invalid
  verdicts correctly become `NEEDS_HUMAN`
  (`python/src/dotfiles_setup/codex_verdict.py:159-170,502-535`). The proposed
  operator adds a `danger-full-access` reasoning principal merely to relay one
  command's status (`.agent/logs/plan-review-codex-lanes.md:11-15`).
- **Why #3:** It removes an unnecessary high-privilege model boundary and fixes
  the exact status-translation class, while preserving typed semantic outcomes
  where a raw process code is insufficient
  (`.agent/logs/plan-review-repeated-issues.md:19-25`).

### 4. Decouple Ubuntu `BASE_IMAGE` updates from `BUILDER_IMAGE` updates

- **Action:** Scope the Renovate regex to the two `BASE_IMAGE` sites and add a
  regression proving a base update changes both base pins, changes neither
  builder pin, and leaves the P2996 hash unchanged.
- **Lanes:** Devcontainer action 3 only
  (`.agent/logs/plan-review-devcontainer.md:13`); the other lanes did not review
  the image dependency boundary.
- **Evidence:** The manager describes a base-image dependency but matches every
  Ubuntu version/digest token (`renovate.json:137-147`). The Dockerfile and bake
  comments explicitly make `BUILDER_IMAGE` separate, manual, and rarely bumped
  because it invalidates the roughly two-hour compiler build
  (`.devcontainer/Dockerfile:16-23`; `docker-bake.hcl:88-95`). Thus the defect is
  that one unanchored rule couples **both** `BASE_IMAGE` and `BUILDER_IMAGE`, not
  a one-sided builder-only bump.
- **Why #4:** This is a small configuration-and-test change that prevents every
  routine base refresh from triggering a deliberately exceptional rebuild
  (`.agent/logs/plan-review-devcontainer.md:13,36`). It ranks above the current
  #822 review because it is the recurrence barrier for that coupling.

### 5. Enforce role-specific writer containment

- **Action:** Keep ordinary reviewers read-only, run hostile mutations only in
  the registered temporary mutation-sentinel candidate, and place every
  concurrent implementation writer in a managed worktree with an explicit
  feature-branch `baseRef`.
- **Lanes:** **Merged related work** — repeated-issues action 4
  (`.agent/logs/plan-review-repeated-issues.md:35-41`) and Codex-lanes action 4
  (`.agent/logs/plan-review-codex-lanes.md:29-37`).
- **Evidence:** Phase 17 records a 90-second two-writer window caused by
  misclassifying a mutation reviewer (`task_plan.md:1447`). Codex review lanes
  already hardcode read-only, and the mutation runner copies registered targets
  to a temporary candidate and requires a typed rejection receipt
  (`python/src/dotfiles_setup/codex_lane.py:112-118`;
  `python/src/dotfiles_setup/session_gate.py:267-310,395-445`). Native managed
  worktrees require an explicit base because their default can omit unmerged
  prerequisite commits (`.agent/logs/plan-review-codex-lanes.md:29-35`).
- **Why #5:** It turns the repeated “second writer” failure into three
  observable, rejectable role boundaries. It is below #4 because the worktree
  base/provisioning decision is broader and needs runtime validation
  (`.agent/logs/plan-review-codex-lanes.md:31-37`).

### 6. Repair the pre-push hook's unset-root failure and reverse its pinning test

- **Action:** Give the pre-push `mise --cd` invocation a repository-root
  fallback when `MISE_PROJECT_ROOT` is absent, then test the hook from both a
  plain shell and `mise exec` while retaining the isolated-test boundary.
- **Lanes:** None; this is a Phase 17 item every review lane omitted
  (`task_plan.md:1426-1427`).
- **Evidence:** The live hook dereferences `$MISE_PROJECT_ROOT` without a
  fallback (`hk.pkl:769-783`), and the current wiring test asserts that exact
  broken string (`tests/test_process_env.py:271-284`). Phase 17 records the
  resulting bare-`git push` failure in both a plain shell and `mise exec`
  (`task_plan.md:1426-1427`).
- **Why #6:** This is a deterministic, low-effort fix to a mandatory boundary
  that blocks ordinary agent-driven pushes. It ranks just below the top five
  because it repairs one hook edge rather than a multi-surface state model.

### 7. Reject unavailable lanes at dispatch and make parity cover runtime semantics

- **Action:** Resolve one authoritative lane roster at the repository-owned
  dispatcher, reject unavailable executables before launch, remove `grok` from
  the positive evaluator, and extend parity to sandbox, lifecycle, unique
  outputs, and structured-result requirements.
- **Lanes:** **Merged duplicate** — repeated-issues action 5
  (`.agent/logs/plan-review-repeated-issues.md:43-49`) and Codex-lanes action 5
  (`.agent/logs/plan-review-codex-lanes.md:39-45`).
- **Evidence:** The static suite requires a no-grok route
  (`python/verification/suites.toml:1840-1851`), while the evaluator explicitly
  declares `grok` and its test expects PASS
  (`python/src/dotfiles_setup/eval_cases.py:42-52`;
  `tests/test_eval_cases.py:83-97`). Current parity can certify file pairing,
  model, effort, and prose while omitting sandbox/lifecycle/result behavior
  (`.agent/logs/plan-review-codex-lanes.md:39-45`).
- **Why #7:** A green evaluator currently blesses the motivating unavailable
  route, so replacing it with an attempted-dispatch rejection prevents
  recurrence. Interception of generic harness Agent dispatch remains
  **UNVERIFIED**; the existing PreToolUse matcher does not include Agent
  (`.claude/settings.json:40-43`).

### 8. Clear the measured listing-budget failure using the gate that already exists

- **Action:** Reduce the enabled skill/agent listing below the declared total
  ceiling and shorten every individual description below the hard truncation
  cap; keep `listing-budget` red until both conditions hold.
- **Lanes:** None; Phase 17 records this active failure directly
  (`task_plan.md:1438`).
- **Evidence:** `doctor` already registers `listing-budget`
  (`python/src/dotfiles_setup/doctor.py:1195-1209`), and its tests exercise both
  an over-ceiling failure and a truncating individual description
  (`tests/test_listing_budget.py:154-168,189-223`). The measured state is
  38,848 characters against 34,000, with `antigravity-delegate` 1,789
  characters above the 1,536 hard cap (`task_plan.md:1438`).
- **Why #8:** The detector and red/control arms already exist, so this is
  inexpensive and restores lost matcher keywords. It ranks below #7 because it
  resolves current context pressure but does not close an execution-authority
  boundary.

### 9. Bind handoff review claims to an exact-SHA receipt that exists on disk

- **Action:** Permit “receipt exists” only with the exact HEAD SHA and verified
  receipt path; otherwise render “review reported clean; receipt unverified.”
- **Lanes:** Context-loss action 3 only
  (`.agent/logs/plan-review-context-loss.md:23-27`).
- **Evidence:** A sending handoff claimed a cold-review receipt, but the next
  session's land gate found none for exact HEAD and had to rerun review and
  create the receipt (`.agent/logs/plan-review-context-loss.md:23-27`). The
  current handoff self-check covers paths, task names, and rc values but not
  exact-SHA receipt identity (`.agent/logs/plan-review-context-loss.md:25-27`).
- **Why #9:** This prevents expensive review re-derivation and false readiness
  at a machine-verifiable artifact boundary. It ranks below #8 because its
  observed cost is rework rather than an unsafe mutation or skipped gate.

### 10. Make the Claude/Fable settlement layer the sole commit owner

- **Action:** Keep Codex implementation lanes in `workspace-write`, remove the
  impossible inner “commit” instruction, and let the Claude-side settlement
  step make the scoped commit only after verification.
- **Lanes:** Codex-lanes action 2 only
  (`.agent/logs/plan-review-codex-lanes.md:17-21`).
- **Evidence:** Fable launches Codex with `workspace-write` while its prompt
  tells Codex to commit; the same wrapper later performs a backstop commit
  (`.agent/logs/plan-review-codex-lanes.md:17-21,65-67`). Phase 17 records that
  this sandbox recursively protects Git metadata (`task_plan.md:1432-1434`).
- **Why #10:** This is a frequent deterministic mismatch and a small prompt /
  ownership correction. It is below exact-receipt binding because the wrapper
  already contains the successful fallback commit path
  (`.agent/logs/plan-review-codex-lanes.md:19-21`).

### 11. Replay the two pipe-to-`tail` incidents through the actual guard boundary

- **Action:** Determine whether each historical command reached PreToolUse; if
  not, cover that execution surface with the guard/audit boundary, and if it
  did, treat execution after deny as a hook-runtime defect.
- **Lanes:** Repeated-issues action 3 only
  (`.agent/logs/plan-review-repeated-issues.md:27-33`).
- **Evidence:** The exact matcher already rejects a gate followed by `head` or
  `tail` (`python/src/dotfiles_setup/hook_guard.py:422-447`), yet Phase 17 says
  the mistake happened twice (`task_plan.md:1443`). The repository warns that
  125 measured commands bypassed the hook by never reaching it
  (`.claude/rules/mise-tasks-only.md:67-85`).
- **Why #11:** Adding another regex would not improve the recorded case; reach
  is the remaining causal unknown. This ranks below #10 because the failing
  invocation surface is still **UNVERIFIED**.

### 12. Remove the invalid `--full-auto` recipe and make an executable launcher canonical

- **Action:** Correct the immediate rule, then route project lane invocation
  through the enabled helper or a version-probed launcher instead of copying
  CLI strings into prose.
- **Lanes:** Codex-lanes action 6 only
  (`.agent/logs/plan-review-codex-lanes.md:47-51`).
- **Evidence:** Phase 17 records Codex 0.152.0 rejecting `--full-auto`
  (`task_plan.md:1422-1423`), while the live central rule still recommends it
  (`.agent/logs/plan-review-codex-lanes.md:47-51`). All four specialty wrappers
  already avoid and prohibit that flag
  (`.agent/logs/plan-review-codex-lanes.md:49-51`).
- **Why #12:** The immediate repair is cheap, but the bad command is stale
  central guidance rather than the invocation used by the four shipped lanes;
  executable version checking is the recurrence-prevention part.

### 13. Prototype one specialty lane on `codex-companion`, including concurrency controls

- **Action:** Move `codex-advisor` first to a thin role adapter over the enabled
  official runtime; compare output, sandbox, cancellation, inner-exit handling,
  unique same-role concurrency, persistence, and visibility before migrating
  any other lane.
- **Lanes:** Codex-lanes action 3 plus its missed same-lane collision and
  ephemeral-policy findings (`.agent/logs/plan-review-codex-lanes.md:23-27,63-77`).
- **Evidence:** Four wrappers duplicate fixed prompt/result paths and
  `codex exec --ephemeral`, while the enabled companion supplies lifecycle and
  structured-output machinery (`.agent/logs/plan-review-codex-lanes.md:23-27`).
  Fixed per-role paths can collide under two concurrent calls
  (`.agent/logs/plan-review-codex-lanes.md:75`), and companion turn status does
  not by itself prove an inner wrapped command succeeded
  (`.agent/logs/plan-review-codex-lanes.md:25-27`).
- **Why #13:** This may retire duplicated lifecycle code, but it is deliberately
  a prototype: status semantics and visibility remain **UNVERIFIED**, so it
  must not outrank fixes with replayed failing arms.

### 14. Conditionally cold-review/land #822's live head, without treating that as prevention

- **Action:** If #822 is still unmerged, review its exact live range with the
  Ubuntu **BASE/BUILDER coupling** and lock removals called out; if it has
  merged, run the repository `land` path and retain R1/R2/R3 evidence.
- **Lanes:** **Merged instance closeout** — devcontainer actions 1 and 2
  (`.agent/logs/plan-review-devcontainer.md:9-11`).
- **Evidence:** The plan requires a cold review and successful local gates
  before completion (`.agent/logs/plan-review-devcontainer.md:9-11`), while its
  last recorded state is #822 head `da84cc3`, auto-merge armed, CI running
  (`task_plan.md:1458`). `land` is the path that drives the full local
  devcontainer criteria (`.agent/logs/plan-review-devcontainer.md:11,31`).
- **Why #14:** This looks operationally urgent, but its live GitHub/head state
  is **UNVERIFIED** and it closes one in-flight PR. Ranks 1 and 4 are the
  recurrence fixes for the lock split and image coupling respectively.

### 15. Put timestamps and transition actions on volatile state, then close stale phase prose

- **Action:** Record `observed_at`, probe scope, and next transition action for
  PR/CI, dependency, count, branch, and SHA facts; re-probe them on resume, then
  reconcile Phase 16 and `.devcontainer/AGENTS.md` with the shipped #896/#897
  state.
- **Lanes:** **Merged related state-fidelity work** — context-loss action 4
  (`.agent/logs/plan-review-context-loss.md:29-33`) and devcontainer action 6
  (`.agent/logs/plan-review-devcontainer.md:19,25-31`).
- **Evidence:** Consecutive handoffs inherited a stale dependency DoD and
  divergent branch counts (`.agent/logs/plan-review-context-loss.md:31-33`). The
  plan still labels Phase 17 `NOT STARTED` immediately above shipped results
  (`task_plan.md:1418,1452-1458`), and the devcontainer instructions still name
  the superseded bare Doppler file despite the workspace/architecture-scoped
  implementation (`.agent/logs/plan-review-devcontainer.md:19,39-40`).
- **Why #15:** This reduces duplicate dispatch and stale orientation, but much
  of the immediate closeout is documentation. It follows the machine-enforced
  recurrence barriers above.

### 16. Choose one handoff lineage model and run `handoff-check` before clear

- **Action:** Either make every newest handoff self-sufficient or declare and
  mechanically load its predecessor chain; in both cases run
  `mise run handoff-check -- <new-handoff>` on the sending side before the clear
  prompt.
- **Lanes:** **Merged within context-loss** — actions 5 and 6
  (`.agent/logs/plan-review-context-loss.md:35-45`).
- **Evidence:** The writer contract requires a self-sufficient artifact, but a
  real successor calls itself a delta and outsources detail to its predecessor
  (`.agent/logs/plan-review-context-loss.md:35-39`). The current checker validates
  citations/tasks while explicitly declining completeness and cross-version
  reconciliation (`python/src/dotfiles_setup/handoff_check.py:2-7,155-169`), and
  the reader invokes it while the sender does not
  (`.agent/logs/plan-review-context-loss.md:41-45`).
- **Why #16:** This prevents lineage-dependent context loss and catches stale
  citations earlier, but it is less direct than rank 2's observed skipped-verb
  failure and still needs a policy choice between consolidation and chaining.

### 17. Require a structured control-arm receipt for automated absence claims

- **Action:** Record corpus, target query, same-shaped known-present control,
  both rc/count results, and parse errors; block report advancement when that
  receipt is missing or the control is empty.
- **Lanes:** Repeated-issues action 8 only
  (`.agent/logs/plan-review-repeated-issues.md:67-73`).
- **Evidence:** Phase 17 records the false zero caused by querying `latest`
  against `latest_version` (`task_plan.md:1445`), and the control-arm rule says
  a zero-result query is not evidence without a same-corpus, same-shape positive
  control (`.agent/logs/plan-review-repeated-issues.md:69-73`).
- **Why #17:** The receipt can reject a missing/failed control and parse errors,
  but it cannot know the author's intended token; a wrong target plus unrelated
  valid control can still pass structurally
  (`.agent/logs/plan-review-repeated-issues.md:71-73`).

### 18. Permit liveness actions only from the typed DAG classifier

- **Action:** Require stop/respawn/reap callers to consume
  `classify_background_rows`; keep `WEDGED` log-only until a separate recovery
  contract exists.
- **Lanes:** Repeated-issues action 7 only
  (`.agent/logs/plan-review-repeated-issues.md:59-65`).
- **Evidence:** Phase 17 records a mid-write tree misdiagnosed as stalled
  (`task_plan.md:1446`). The classifier requires active tempo plus a readable
  stale age (`python/src/dotfiles_setup/dag_tick.py:415-431`), and current tests
  prevent WEDGED from invoking recovery verbs
  (`.agent/logs/plan-review-repeated-issues.md:63-65`).
- **Why #18:** It can block a harmful action, not a prose-only diagnosis; whether
  the historical lane was represented in this DAG is **UNVERIFIED**
  (`.agent/logs/plan-review-repeated-issues.md:63-65`).

### 19. Add the legacy-file hostile arm to the shipped Doppler race fix

- **Action:** Seed the old host-wide `doppler.env` with clone A's value, run
  clone B's current staging path, and assert the legacy bytes are neither
  imported nor selected.
- **Lanes:** Repeated-issues action 6 only
  (`.agent/logs/plan-review-repeated-issues.md:51-57`).
- **Evidence:** Workspace/architecture-specific paths, atomic writes, and a
  two-clone arm already exist, while no test seeds the legacy filename
  (`.agent/logs/plan-review-repeated-issues.md:53-57`). Phase 17 records that the
  rejected migration instruction would have reopened the race
  (`task_plan.md:1448`).
- **Why #19:** This is a precise, cheap red arm, but the product fix is already
  shipped and the current source has no legacy migration branch
  (`.agent/logs/plan-review-repeated-issues.md:55-57`).

### 20. Reconcile the tracked devcontainer feature lock with its ignore policy

- **Action:** Rebase and re-evaluate the #723 reconciliation, then provide one
  local feature-lock task whose tracked/refresh behavior agrees with
  `.gitignore`.
- **Lanes:** Devcontainer action 8 only
  (`.agent/logs/plan-review-devcontainer.md:23`).
- **Evidence:** `.devcontainer/devcontainer-lock.json` is committed and the
  refresh workflow regenerates it, while `.gitignore` still describes it as
  per-machine churn that must remain untracked
  (`.agent/logs/plan-review-devcontainer.md:23`). No local feature-lock task was
  found in the lane's same-shaped control (`.agent/logs/plan-review-devcontainer.md:23`).
- **Why #20:** This is a real policy/tree contradiction, but no replayed runtime
  failure is cited and #896/#897 moved overlapping surfaces, so re-evaluation
  precedes implementation (`.agent/logs/plan-review-devcontainer.md:23`).

### 21. Give cross-surface `/resume` the same reconciliation contract

- **Action:** Run `session-state` and `handoff-check`, lead with disagreements,
  and make cross-surface `/handoff` include the same ambiguity-resolution step
  as the same-clone sender.
- **Lanes:** Context-loss action 7 only
  (`.agent/logs/plan-review-context-loss.md:47-51`).
- **Evidence:** Same-clone resume snapshots live state and reports
  contradictions, while cross-surface resume only pulls/reads/restates and its
  sender skips step 0 (`.agent/logs/plan-review-context-loss.md:47-51`).
- **Why #21:** The parity gap is concrete, but no measured cross-surface failure
  was found, so impact remains **UNVERIFIED**
  (`.agent/logs/plan-review-context-loss.md:49-51`).

### 22. Retire the stale one-PR batching instruction and finish Python currency separately

- **Action:** Let the expensive image PR finish without adding Python paths;
  move the remaining pydantic/ty bumps to a cheap non-image follow-up.
- **Lanes:** Devcontainer action 7 only
  (`.agent/logs/plan-review-devcontainer.md:21`).
- **Evidence:** Phase 17 records pydantic and ty still outdated
  (`task_plan.md:1437`) while #822 was already in CI
  (`task_plan.md:1458`); the #822 exact head contained no Python path in the
  lane's diff control (`.agent/logs/plan-review-devcontainer.md:21`).
- **Why #22:** This avoids restarting an expensive build for unrelated work,
  but it is scheduling cleanup rather than a new recurrence-prevention gate.

## 2. Contradictions and evidence verdicts

1. **One protocol for all background work vs a split protocol.** The
   repeated-issues lane says to route background review/agent work through the
   `codex-lane` producer/reaper shape
   (`.agent/logs/plan-review-repeated-issues.md:17-25`); the Codex lane says a
   deterministic `mise` task must not be wrapped in a reasoning lane at all
   (`.agent/logs/plan-review-codex-lanes.md:11-15`). **Evidence favours the
   split:** raw process rc is the complete result for one authorized command,
   whereas `codex-lane` deliberately makes launcher rc describe settlement and
   requires a separate verdict for semantic approval
   (`python/src/dotfiles_setup/codex_lane.py:569-612`;
   `python/src/dotfiles_setup/codex_verdict.py:502-535`).

2. **“Native `.worktreeinclude` replaces per-spec provisioning” vs separate
   lifecycle surfaces.** Phase 17 presents `.worktreeinclude` as a native Codex
   replacement for hand provisioning (`task_plan.md:1424-1425`); the Codex lane
   finds that Claude applies it globally to every Claude-created worktree, while
   Claude-launched raw Codex CLI lanes do not acquire Codex Desktop managed
   worktrees (`.agent/logs/plan-review-codex-lanes.md:29-37`). **Evidence favours
   the lane:** use explicit Claude worktree isolation/base selection for outer
   writers and retain per-spec handling for sensitive ignored files; globally
   copying `mise.local.toml` can propagate collision-prone port/Doppler settings
   (`.agent/logs/plan-review-codex-lanes.md:33-37`).

3. **No-grok contract vs a green evaluator that blesses grok.** The verification
   suite requires Codex/Claude-only routing
   (`python/verification/suites.toml:1840-1851`), but the evaluator declares
   `grok` and its test requires PASS
   (`python/src/dotfiles_setup/eval_cases.py:42-52`;
   `tests/test_eval_cases.py:83-97`). Both review lanes that touch this subject
   favour attempted-dispatch rejection and removal of the stale positive
   (`.agent/logs/plan-review-repeated-issues.md:43-49`;
   `.agent/logs/plan-review-codex-lanes.md:39-45`). **Evidence favours those
   lanes:** the static prose contract cannot fire when unchanged instructions
   are ignored at runtime (`.agent/logs/plan-review-repeated-issues.md:45-49`).

4. **“Drop `--state open`” vs GitHub CLI's open-only default.** Phase 15's
   proposed repair would still query only open PRs; the context lane establishes
   that explicit `--state all` is required and points to an existing repository
   use of that complete enumeration
   (`.agent/logs/plan-review-context-loss.md:13-15,63-67`). **Evidence favours
   explicit `--state all`:** the current source uses explicit `open` and its
   empty result becomes `NONE` (`python/src/dotfiles_setup/session_state.py:194-219`).

5. **“Parity 4 -> 5” vs the actual unshipped branch/current test.** Phase 17
   states that `eaf3cc6` moved parity from four to five lanes
   (`task_plan.md:1457`); the Codex lane reports that the commit adds the two
   operator files while the live test still asserts an exact four-name roster
   (`.agent/logs/plan-review-codex-lanes.md:39-45`). **Evidence favours the lane:**
   adding a fifth pair can satisfy dynamic filename pairing yet fail the exact
   roster test, so the Phase 17 completion wording is stale
   (`.agent/logs/plan-review-codex-lanes.md:43-45`).

6. **Self-sufficient newest handoff vs real delta handoffs.** The writer contract
   requires a self-sufficient artifact, while the reader selects only the newest
   file; an observed handoff nevertheless calls itself a delta and sends the
   reader to its predecessor (`.agent/logs/plan-review-context-loss.md:35-39`).
   **Evidence favours either strict consolidation or a mechanically loaded
   chain, not the present hybrid:** current selection/checking does not follow
   prose predecessor links (`python/src/dotfiles_setup/handoff_check.py:51-67`).

There is no substantive lane-to-lane disagreement on the two highest-value
machine boundaries: the devcontainer and repeated-issues lanes independently
converge on scoped same-branch lock repair
(`.agent/logs/plan-review-devcontainer.md:17`;
`.agent/logs/plan-review-repeated-issues.md:7-15`), and the repeated-issues and
Codex lanes converge on isolating writers by role
(`.agent/logs/plan-review-repeated-issues.md:35-41`;
`.agent/logs/plan-review-codex-lanes.md:29-37`).

## 3. What every lane missed

1. **The proposed same-branch Renovate repair needs two additional controls.**
   None of the four lane actions joined the recorded Renovate force-push loss
   (`task_plan.md:1436`) and the read-only-command lock mutation
   (`task_plan.md:1431`) to the proposed PR synchronization repair
   (`.agent/logs/plan-review-repeated-issues.md:7-15`). Rank 1 therefore adds:
   abort/recompute on head movement, and require both the repair workflow and
   every currency probe it invokes to leave unrelated bytes unchanged.

2. **The pre-push hook's test currently preserves the defect.** Phase 17 records
   the unset-root failure (`task_plan.md:1426-1427`), but no lane ranked it; the
   live hook dereferences the variable and its test asserts the same literal
   (`hk.pkl:780`; `tests/test_process_env.py:271-284`). Rank 6 promotes this
   because a passing regression currently means “the broken wiring is still
   present.”

3. **The listing budget is already a measured red gate, not a future design
   question.** No lane carried forward Phase 17's 38,848/34,000 finding or the
   over-cap `antigravity-delegate` description (`task_plan.md:1438`), even
   though the doctor check and both failure/control tests exist
   (`python/src/dotfiles_setup/doctor.py:1195-1209`;
   `tests/test_listing_budget.py:154-168,189-223`). Rank 8 makes the existing
   gate actionable rather than inventing a new one.

4. **`plan-attest` was unavailable for the entire session.** No lane proposes a
   reach/root-cause replay even though Phase 17 says every prompt was blocked
   (`task_plan.md:1439`). The cause, blocking interception point, and whether
   the task itself could run are **UNVERIFIED**; this is recorded as a miss but
   not promoted above evidence-backed repairs.

## 4. Ordered top five — do next, with acceptance tests

1. **Scoped Renovate exact-pin repair.** Done only when a real synchronization
   fixture with two changed exact pins repairs every selected shared/image owner,
   an intentionally omitted changed tool still fails
   `test_system_lock_versions_match_pins`, every unrelated/floating lock byte is
   identical, a concurrent Renovate head advance causes no push and a recompute,
   and any invoked currency probe leaves a clean tree
   (`tests/test_lock_coverage.py:358-402`;
   `.github/workflows/refresh.yml:12-18`; `task_plan.md:1431,1435-1436`).

2. **Terminal PR state plus obligation continuity.** Done only when 0/1/many,
   OPEN/MERGED/CLOSED, malformed, and failed-query fixtures are distinct;
   MERGED renders `mise run land -- <PR#>`; a successor that drops any prior
   `OWED` item fails; and explicit DONE/STILL OWED/SUPERSEDED controls pass
   (`python/src/dotfiles_setup/session_state.py:194-229,273-286`;
   `.agent/logs/plan-review-context-loss.md:17-21,75-77`).

3. **Deterministic job rc plus typed reasoning verdict.** Done only when an
   authorized background `mise` command exiting 2 is reported as 2 without a
   model wrapper; a settled/nonzero reasoning lane with no verdict becomes
   `NEEDS_HUMAN`; a schema-valid approval advances; and no `danger-full-access`
   `codex-operator` route remains
   (`python/src/dotfiles_setup/codex_lane.py:569-612`;
   `python/src/dotfiles_setup/codex_verdict.py:159-170,502-535`;
   `.agent/logs/plan-review-codex-lanes.md:11-15`).

4. **BASE/BUILDER dependency decoupling.** Done only when a Renovate fixture
   updates both `BASE_IMAGE` occurrences, updates zero `BUILDER_IMAGE`
   occurrences, and leaves `p2996-hash` unchanged; a deliberate manual builder
   change remains possible and changes that hash
   (`renovate.json:137-147`; `.devcontainer/Dockerfile:10-23`;
   `docker-bake.hcl:76-95`;
   `.agent/logs/plan-review-devcontainer.md:35-36`).

5. **Role-specific writer containment.** Done only when an ordinary review write
   is denied, a hostile mutation changes only its temporary candidate and
   produces a typed gate-rejection receipt, and two parallel implementation
   writers start from the explicitly requested feature base without sharing
   worktree state; any `.worktreeinclude` entry is proven safe in every managed
   worktree (`python/src/dotfiles_setup/session_gate.py:267-310,395-445`;
   `.agent/logs/plan-review-codex-lanes.md:29-37`).

## 5. LOW-ranked items that look urgent

- **#822 exact-head review/land (rank 14):** “auto-merge armed, CI running” makes
  it look immediate (`task_plan.md:1458`), but the current live head/status is
  **UNVERIFIED**, and review/land closes one instance. The machine recurrence
  fixes are ranks 1 and 4
  (`.agent/logs/plan-review-devcontainer.md:9-17`).
- **Invalid `--full-auto` guidance (rank 12):** the documented command fails on
  Codex 0.152.0 (`task_plan.md:1422-1423`), but all four shipped specialty lanes
  already avoid it (`.agent/logs/plan-review-codex-lanes.md:47-51`). Correct it,
  but do not displace a replayed unsafe boundary.
- **Feature-lock reconciliation (rank 20):** tracked-vs-ignored policy is a real
  contradiction (`.agent/logs/plan-review-devcontainer.md:23`), but no runtime
  failure is cited and overlapping shipped changes require a rebase/recheck
  before reuse (`.agent/logs/plan-review-devcontainer.md:23`).
- **`plan-attest` blocked all session (unranked LOW/UNVERIFIED):** the symptom is
  session-wide (`task_plan.md:1439`), but every causal and interception claim is
  **UNVERIFIED**. It becomes actionable after a failing replay plus a same-path
  passing control identifies where the block occurs.
- **Remaining pydantic/ty currency (rank 22):** the versions are still outdated
  (`task_plan.md:1437`), but appending them to an image PR already in CI would
  restart the expensive lane; a separate non-image follow-up preserves both
  workstreams (`.agent/logs/plan-review-devcontainer.md:21`).
