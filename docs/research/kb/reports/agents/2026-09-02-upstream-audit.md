# Upstream audit: OthmanAdi/planning-with-files

Started 2026-09-02.


## Part 1 — Inventory

Retrieved via `gh api --paginate "repos/OthmanAdi/planning-with-files/issues?state=all&per_page=100"` (returns issues+PRs, `pull_request` key distinguishes).

- Total items: **214** (numbers 1–236, with gaps for deleted/spam-removed entries)
- Issues (non-PR): 126 total — 9 open, 117 closed
- PRs: 88 total — 0 open, 88 closed (all resolved one way or another; merged count TBD below)
- **Completeness check**: repo metadata `open_issues_count=9` (GitHub API rolls PRs into this count too, but open PR count here is 0, so it's a clean match) — confirms the open set is fully retrieved. Paginated fetch did not truncate: last page returned 14 items (<100), not exactly the page size, so no silent truncation.

Full numbered list (number, kind, state, merged-flag, title) saved to `issues_list.txt` in this scratchpad dir.

Open issues (9): #19, #50, #176, #196, #213, #219, #225, #230, #236 (ours).


## Part 2 — Direct overlaps with the 7 items

### #236 is NOT a duplicate

Fetched #236's own body verbatim (it's our filed issue). Grepped every other
issue/PR body+title for `plan-doctor`, `PLAN TAMPERED`, `substring` — the only
other hits are #234 (different bug: `attest-plan.sh` writes to the wrong file
when run from `.planning/<slug>/`, not a substring-match defect), #150 (the
original attestation feature proposal, context not overlap), #231 (CRLF line
endings breaking `/plan-attest`, unrelated), #157/#216 (unrelated PRs matching
`substring` incidentally in diff text). **No comments exist on #236 yet.**
Zero prior art for the two `plan-doctor.sh:76-95`/`:92` defects. Confirmed
clean — nothing to link or close.

### Item 3 (multi-session collision on task_plan.md) — #217, CLOSED, SHIPPED, NOT what its title suggests

#217 "Add protection against stale or conflicting planning files after
parallel tasks" proposed a `plan_id`/`revision`/`updated_by` header + reread-
before-write rule. **What actually shipped (v3.10.0, commit `60209e9`) is
different from the proposal**, per OthmanAdi's own closing comment:

- Comparing raw content hashes (the original plan) was tried and rejected —
  it fires on the *same* agent's own sequential edits (every phase advance
  changes the hash), which is noise, not signal.
- The shipped guard instead tracks **two monotonic counters**: checked-item
  count and completed-phase count. Since normal work only increases them, a
  **decrease** between two hook fires ("turn-start" reads) means a stale
  write clobbered newer work. On detection it emits an advisory (never
  blocking — `inject-plan.sh` always exits 0):
  ```
  [planning-with-files] PLAN REGRESSED: task_plan.md lost N checked item(s)
  and N completed phase(s) since these hooks last read it. ... 'git diff --
  task_plan.md' shows what changed.
  ```
- **On by default in every mode, including legacy** — a deliberate exception
  to the project's "no `.mode` file ⇒ byte-identical output" rule. Off
  switches: `PWF_PLAN_GUARD=0` env var, or a `plan-guard-off` token in
  `.mode`.
- Explicitly named limits (stated by the maintainer, not inferred): (a) the
  marker is keyed on **plan path, not session**, so the warning reaches
  whichever session fires next, not necessarily the one holding the stale
  copy — per-session keying would need `PWF_SESSION_ID`, "which most hosts
  never set"; (b) **archiving completed phases also trips it** (a legitimate
  decrease reads identically to a regression).
- Tests: `tests/test_plan_regression_guard.py` — legacy silence, forward-
  progress silence, the regression warning with exact loss counts, no
  repeat once new state is observed, both off-switches, pretool silence.
  "Suite 411 to 417."
- Reusable existing machinery it built on: `inject-plan.sh:419-458` already
  ran an mtime+SHA-256 cache keyed on the plan's absolute path (previously
  gated behind attestation only).

**Implication for our plan:** don't propose a header-based `plan_id`/
`revision` scheme — it was considered and explicitly rejected (every other
mutation path in this codebase writes state to a sidecar next to the plan,
never into `task_plan.md` itself — "the plan file is the user-owned
contract"). If we want to test or extend concurrency protection, the real
target is the checked-item/phase-count regression guard and its
`PWF_PLAN_GUARD` toggle, not a from-scratch design.

### Item 4 (legacy root → slug-mode migration; `.active_plan` adequacy) — #77 (shipped), #165 (docs), #234 (bug), #217 (context)

- **#77**, MERGED, is the PR that *introduced* slug mode: `.planning/{plan_id}`
  isolated folders, UUID generation per plan session, `.planning/.active_plan`
  as the shared default pointer, `PLAN_ID` env var for explicit per-terminal
  pinning, `resolve-plan-dir.sh`/`.ps1`, `set-active-plan.sh`/`.ps1`. This is
  the origin of the exact mechanism item 4 asks about.
- **#165** (closed, docs task) explicitly frames `.active_plan`/slug-mode as
  the **recommended fix for the flock-fallback gap**, not fully adequate on
  its own: "point users at slug-mode as the canonical parallel-session
  pattern (not legacy-mode flock) ... each slug has its own `.attestation`
  file under `.planning/<slug>/`, so writers don't contend." So slug-mode
  solves attestation-file contention specifically, not the general
  concurrent-write-to-one-plan-file problem (that's #217's regression guard).
- **#234** (closed via fix) is a real gap in `.active_plan`/slug-mode: running
  `attest-plan.sh` from *inside* `.planning/<slug>/` (rather than the project
  root) silently falls back to writing a legacy `./.plan-attestation` file in
  the wrong place, exits 0, and looks like success — the next hook fire then
  reports `[PLAN TAMPERED]`. Root cause: `resolve-plan-dir.sh:18`'s
  `PLAN_ROOT="${1:-${PWD}/.planning}"` is cwd-relative with no "project I'm
  actually in" concept beyond cwd, absent an explicit `PWF_PLAN_ROOT` pin.
  **Confirms `.active_plan`/slug-mode is NOT fully adequate for concurrent
  worktrees** — cwd-relative resolution is a real, already-reported footgun.
- **#212** and **#195** (both closed/fixed) are the *shared-cwd* failure mode
  of `.active_plan`: multiple Codex threads/sessions sharing one cwd get the
  wrong plan auto-selected via `.planning/.active_plan`, hijacking an
  unrelated task. #146 is the earlier, already-fixed ancestor of this same
  class (session-attachment guard for the legacy `.codex/hooks` path).
  #212 shows the fix didn't fully extend to the Agent-Skills/skill-only
  Codex install route as of v3.7.0–v3.8.2 (fixed since, but worth noting the
  fix surface was incomplete more than once).

**Implication:** `.active_plan` + slug-mode is the documented recommended
migration target, but it has TWO known-and-fixed footguns worth citing if we
write migration guidance: (a) cwd-relative attestation-path resolution from
inside the slug dir (#234), (b) shared-cwd `.active_plan` misattachment
across concurrent sessions/threads (#146/#212/#195, iteratively patched, not
a one-shot fix).

### Item 5 (`PWF_*` env vars) — confirmed inventory, no separate tracking issue

Grepped every issue/PR for `PWF_INJECT`, `PWF_PLAN_ROOT`, `PWF_SESSION_ID`,
`PWF_PLAN_GUARD`. Findings:
- `PWF_PLAN_ROOT` — appears only in #236 (ours) and #234 (the cwd-relative
  bug above). No dedicated issue about `PWF_PLAN_ROOT` itself; it is
  mentioned as the escape hatch ("absent an explicit PWF_PLAN_ROOT pin") in
  #234's root-cause analysis.
- `PWF_SESSION_ID` — mentioned only inside #217's shipped-fix comment as a
  **documented but unimplemented** future upgrade path for per-session
  keying of the regression guard ("which most hosts never set" — i.e. it is
  aspirational, not a working env var today).
- `PWF_PLAN_GUARD` — the real, shipped (v3.10.0) off-switch for #217's
  regression guard. Not mentioned anywhere else.
- `PWF_INJECT` — **zero hits anywhere in the corpus.** Not a real env var in
  this project as far as issues/PRs show; if we were planning to reference it
  in local docs, that reference has no upstream basis and should be verified
  against the actual script source, not assumed from an issue thread.

### Item 6 (plan-doctor.sh as diagnostic-only / best-effort) — no explicit maintainer statement found

No issue or PR body contains a maintainer statement characterizing
`plan-doctor.sh`'s status/reliability tier. #231 (CRLF breaking
`/plan-attest`) and #236 (ours) are the only two issues that treat
`plan-doctor.sh`/`/plan-attest` output as something users rely on for a
real signal, which argues against treating it as merely diagnostic in
practice — users file bugs against wrong doctor output as real defects, and
the maintainer fixes them as real defects (e.g. #233 for `init-session.sh
--help`, though that's a different script).

### Item 7 (file-role split: task_plan.md / findings.md / progress.md) — #148, #202, #203

- **#148** (closed, feedback thread, pre-v2.0.0 hooks) is a maintainer/user
  design discussion about where planning files should live under parallel
  multi-agent use (their v1.x convention: `docs/tasks/<task-name>/` via a
  `CLAUDE.md` line) versus what v2.0.0's hooks assume. Useful prior-art
  context for any local guidance on file placement conventions, though
  superseded in practice by slug-mode (#77).
- **#202** (closed) is a direct "why is there no archiving step" design-
  rationale question, referencing an earlier duplicate **#14** ("should the
  remaining .md files be deleted or archived?") that was closed without a
  visible resolution comment per the reporter. Confirms: **no archiving
  mechanism exists upstream** — plans are simply superseded/overwritten, not
  archived, and this is being treated by the maintainer as (at minimum)
  unresolved-by-design rather than a stated feature. Worth flagging if our
  local guidance implies archiving is supported.
- **#203** (closed/fixed) documents a stale-nag bug where a fully-closed,
  4/4-complete plan kept emitting "Task incomplete (N/M)" follow-ups for
  multiple turns after completion — a `readPlanStatus()`/`agent_end` early-
  out bug, now fixed. Relevant if our guidance describes the completion
  signal as instantaneous; it wasn't, in a documented past bug (now closed).

## Part 3 — Context we lacked

1. **The concurrency-protection design space was already explored and a
   specific approach (content-hash / revision-header) was explicitly
   rejected** in favor of monotonic-counter regression detection (#217).
   Any local proposal along header/hash lines should address why the
   maintainer's rejection doesn't apply, or adopt the counter approach.
2. **`.active_plan` has a documented history of shared-cwd misattachment**
   across Codex sessions/threads (#146→#212→#195), patched iteratively over
   multiple releases rather than fixed once — this is a live risk class, not
   a one-off bug, worth treating as "watch for regressions in this area"
   rather than "fixed and done."
3. **No archiving mechanism exists** (#202, referencing unresolved #14) —
   if any local doc or plan implies plans get archived after completion,
   that's describing aspirational rather than actual behavior.
4. **`PWF_SESSION_ID` is aspirational, not implemented** — do not treat it as
   a real usable env var; it's a named-but-unbuilt future upgrade path per
   the maintainer's own comment on #217.
5. `PWF_INJECT` has no basis in the upstream corpus at all — verify directly
   against script source before using it in any local documentation.

## Part 4 — Recommended actions (ranked)

1. **Ship #236 as-is** — confirmed zero duplication, zero prior art, real
   two-part defect (false WARN + false PASS) that the maintainer has not
   seen before. No action needed beyond what's already filed.
2. **If we write local guidance on multi-session/parallel plan safety**,
   cite the shipped `PLAN REGRESSED` guard (v3.10.0, `PWF_PLAN_GUARD`) and
   its two named limits (path-keyed not session-keyed; archiving triggers a
   false regression) rather than re-deriving a scheme from scratch — the
   revision-header idea was tried in the issue thread and rejected.
3. **If we document `.active_plan`/slug-mode migration**, include the two
   known footguns: cwd-relative attestation resolution when invoked from
   inside `.planning/<slug>/` (#234, fixed but instructive about the
   resolver's design), and the shared-cwd active-plan misattachment history
   for Codex specifically (#146/#212/#195) if Codex is in our tool matrix.
4. **Do not reference `PWF_INJECT`** in any local doc/skill without first
   verifying it exists in the current script source — it has zero upstream
   presence and may be a misremembered or aspirational name.
5. Low priority: no action needed on items 1, 2, 6 — no direct overlaps
   found beyond what's already covered above.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — full issue/PR audit via `gh api`, direct reads of #217, #234, #232, #233, #77, #150, #151, #165, #208, #209, #212, #195, #202, #203, #148, #146, #236 bodies and comments
