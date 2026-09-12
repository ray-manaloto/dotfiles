# Known-Workaround Backfill Evidence (#1025)

Evidence gathering for whether each currently-open `bug`-labeled issue in
`ray-manaloto/dotfiles` documents a workaround someone is actually relying on
today, per #1025 (parent spec #1024, canonical example #877).

Enumerated via `gh issue list --state open --limit 500 --label bug -R ray-manaloto/dotfiles`
→ **27 open issues** carrying `bug`. All 27 were read (body + every comment).
Total comments read across the corpus: **20** (most issues have 0 comments;
#715 has 15, #995/#986/#985/#852/#745 have 1 each).

Status: **COMPLETE** — all 27 issues read and classified.

## Summary table

| Issue | Title (short) | Classification | Comments read |
|---|---|---|---|
| 1000 | .agents/skills twins byte-diverged | NO-WORKAROUND | 0 |
| 996 | Renovate stopped proposing graphifyy bumps | NO-WORKAROUND | 0 |
| 995 | Verify S1b on schedule-event ci.yml | UNCLEAR (mixed) | 1 |
| 986 | Exit-code-masking gates don't scan workflow YAML | NO-WORKAROUND | 1 |
| 985 | `:dev` amd64 unpullable on GHA runner | NO-WORKAROUND (borderline) | 1 |
| 981 | CI: 16 `always()` conditions ignore cancellation | NO-WORKAROUND | 0 |
| 963 | image-lock-pr `--no-container` perturbs root mise.lock | NO-WORKAROUND | 0 |
| 948 | `${CLAUDE_PROJECT_DIR:-.}` reopens #343 class | NO-WORKAROUND | 0 |
| 888 | Branch protection lets owner merge with ci-gate red | NO-WORKAROUND | 0 |
| 883 | `pin-actions` can only pass (pinact --verify exits 0) | NO-WORKAROUND | 0 |
| 870 | Reproduce/fix two failing tier-3 exec tests | NO-WORKAROUND | 0 |
| 863 | KB build receipt rejected by links schema | NO-WORKAROUND | 0 |
| 862 | do-not.md invariant 8 states two facts a probe refutes | NO-WORKAROUND | 0 |
| 860 | arm64 platform triple asserts a variant containerd erases | NO-WORKAROUND | 0 |
| 859 | graphify-update task advertises a removed version stamp | NO-WORKAROUND | 0 |
| 858 | Declared-tools parser raises TypeError on bare-string os | NO-WORKAROUND | 0 |
| 852 | un-investigated ubuntu-26.04-arm smoke failure | NO-WORKAROUND | 1 |
| 745 | ARM64 CI disk cleanup warning-free | NO-WORKAROUND | 1 |
| 724 | Require atomic dirty-tree attribution before session-end | NO-WORKAROUND | 1 |
| 723 | Track and validate the generated feature lock | NO-WORKAROUND | 0 |
| 716 | Isolated worktree tool probes rewrite shared hk hooks | **WORKAROUND-DOCUMENTED** | 0 |
| 715 | Session transcript review requirement-complete | NO-WORKAROUND | 15 |
| 479 | tmux-extended-keys skill prescribes lines file never had | NO-WORKAROUND | 0 |
| 370 | `mise install` destructively re-locks mise.lock | **WORKAROUND-DOCUMENTED** | 1 |
| 298 | Agent spawn/liveness unreliable both directions | **WORKAROUND-DOCUMENTED** (caveated) | 0 |
| 103 | rtk held at 0.37.2 — github backend omits url_api | **WORKAROUND-DOCUMENTED** | 0 |
| 7 | Bootstrap paradox: run_before may find no config | NO-WORKAROUND | 0 |

**Headline counts:** WORKAROUND-DOCUMENTED = 4 (716, 370, 298, 103); UNCLEAR = 1
(995); NO-WORKAROUND = 22; FIX-DESCRIBED-NOT-APPLIED = 0 as a standalone
top-level classification (one sub-case inside #995, see detail); ALREADY-FIXED
= 0.

## Per-issue detail

### #1000 — .agents/skills twins byte-diverged, dead .Codex/rules/* pointers

**Classification: NO-WORKAROUND**

Body is a findings/ask list from an audit (part of #994 program). 0 comments.
No sentence in the body describes a workaround in use — it lists an "Ask" (4
items to widen the audit, decide the twin model, retire find-docs, add a gate)
and a "Done when" bar. Nothing indicates anyone is doing something today to
route around the drift.

### #996 — Renovate stopped proposing graphifyy bumps

**Classification: NO-WORKAROUND**

Body states: *"Every bump since has been by hand (0.9.42 → 0.9.53 in #885)."*
This is arguably a workaround-shaped fact (manual bumping instead of relying on
Renovate), but the issue frames it as evidence of the underlying defect, not as
an endorsed ongoing practice — the "Done when" section asks for either Renovate
to resume proposing PRs *or* the pin to be "documented as deliberately manual
with the reason in `renovate.json`" (not yet done, per the issue's own
phrasing "or"). 0 comments. Classified NO-WORKAROUND because no comment
confirms the manual-bump practice is the accepted ongoing state; the issue is
still framed as unresolved.

### #995 — Verify S1b (#982) on a schedule-event ci.yml run

**Classification: UNCLEAR (mixed — original ask verified success; comment surfaces a NEW, undocumented residual bug with a fix plan, not yet applied)**

Body: tracking issue asking to prove S1b via a schedule-event `ci.yml` run.

Comment 0 (sortakool): *"The nightly fired — S1b is proven for `smoke-test`, but `dev-tag` still skips"* — reports `smoke-test` succeeded (original ask met) but found a **new** transitive-skip bug on `dev-tag`: *"`dev-tag` declares `needs: [plan, build, smoke-test]` and `if: needs.smoke-test.result == 'success'` (`.github/workflows/build-publish.yml:1054-1056`). All three needs read `success`, yet the job skipped ... So on the nightly `:dev` was **not** retagged."*

The comment proposes a fix, not a workaround: *"fix in a **new PR citing #982** (and #981) ... `if: !cancelled() && needs.smoke-test.result == 'success'` on `dev-tag`, with the S1b contract ... extended ... Scheduled into the 2026-09-10 session after PR A (#994) lands."* This is FIX-DESCRIBED-NOT-APPLIED in shape for the residual `dev-tag` bug specifically — no interim workaround is described (e.g., nobody says "until fixed, manually retag `:dev`"). Reported as UNCLEAR/mixed rather than forcing into one bucket, since the issue's original defect is resolved but the issue remains open because of a newly discovered, unfixed, un-worked-around sub-defect.

### #986 — Exit-code-masking gates don't scan workflow YAML

**Classification: NO-WORKAROUND**

Body documents two real defects that were already fixed in PR #984 (*"Both closed"* — commits `1c835d3` defects introduced, `22a88af` both closed) but the *gate gap* itself (no shell-aware check over workflow YAML `run:` blocks) remains open. Body suggests a direction (extract `run:` blocks, run existing shell-aware checks) but this is a suggestion, not a workaround anyone runs today.

Comment 0 (sortakool) is a scoping/triage comment for "PR B" from a larger audit (#993): narrows 151 findings down to 14 in-scope ones for one class, defers 137 to #993's checklist. It describes *what will be built*, not a workaround in use. No sentence claims anyone manually re-checks workflow YAML for these shapes today as an interim measure.

### #985 — `:dev`'s amd64 half unpullable on a GHA runner

**Classification: NO-WORKAROUND** (borderline — see note)

Body states existing consumers happen not to trigger the bug: *"Both existing consumers route around it: `smoke-test` pulls the **per-arch tag** ... — a single manifest, so no platform matching happens at all. `mise run sync` on the maintainer's Mac resolves the **arm64** half. So the amd64 half of the moving tag is exercised by nothing, and any amd64 user doing the documented `docker pull …:dev` would fail."*

This is presented as an *accidental* non-triggering of the bug by existing code paths, not a deliberate, adopted workaround for the defect — nobody added a guard or changed behavior *because of* this bug; the paths simply never exercised the broken one. Not counted as WORKAROUND-DOCUMENTED because it does not describe something someone does *in response to* the known defect.

Comment 0 (sortakool) upgrades the cause "from hypothesis to grounded in source," citing `platform_target.py:119` and explaining the `_MICROARCH_LEVEL` asymmetry. Ends: *"What remains genuinely open is only the matcher-version question ... Either way the decision belongs with whoever owns the `_MICROARCH_LEVEL` choice."* No workaround stated — this is root-cause narrowing, not a fix or workaround.

### #981 — CI: 16 `always()` job conditions ignore run cancellation

**Classification: NO-WORKAROUND**

Body is an audit scope declaration: *"Scope — this is an AUDIT, not a blanket rewrite"* with judgement criteria per-site. 0 comments. No workaround described — the issue is explicitly pre-fix, and even flags itself as needing case-by-case judgment before any change.

### #963 — image-lock-pr `--no-container` perturbs the root mise.lock

**Classification: NO-WORKAROUND**

Body is a narrowing/measurement writeup: confirms the container-routed path is byte-identical (not the cause), and CI's `--no-container` path does perturb `mise.lock`. Ends with "Also relevant: #958 has landed" (better diagnostics for *next* failure) and refutes an "auto_install" hypothesis. 0 comments. No workaround stated — nothing describes bypassing or avoiding the `--no-container` path today; it is purely diagnostic narrowing.

### #948 — The `${CLAUDE_PROJECT_DIR:-.}` hook default re-opens #343

**Classification: NO-WORKAROUND**

Body proposes "Two independent halves" as a *suggested fix* (strengthen `_unanchored_hooks`; decide loud-fail behavior) — explicitly unapplied ("Suggested fix"). 0 comments. No interim workaround described; the issue frames itself as "a live risk with precedent, not a proven break," i.e., open and unaddressed.

### #888 — Branch protection lets owner merge with ci-gate red

**Classification: NO-WORKAROUND**

Body is a configuration-state dump (classic protection vs. ruleset) demonstrating the gap, ending mid-sentence describing the failure path ("It is..."). 0 comments. No workaround (e.g., a manual discipline "always wait for ci-gate before merging as owner") is stated anywhere in the issue.

### #883 — `mise run pin-actions` can only pass

**Classification: NO-WORKAROUND**

Body documents the defect with a reproducible control arm and lists "Candidate fixes (not yet evaluated)" — explicitly marked unevaluated/unapplied. 0 comments. No workaround (e.g., "manually run `pinact run --verify` and read stdout instead of the exit code") is documented as an ongoing practice.

### #870 — Reproduce and fix the two failing tier-3 exec tests

**Classification: NO-WORKAROUND**

Body: "Inherited from the session record and not independently reproduced. Reproduce first." Acceptance criteria are all unchecked. 0 comments. Nothing describes a workaround; the issue hasn't even reached reproduction yet.

### #863 — Knowledge-base build receipt rejected by links schema

**Classification: NO-WORKAROUND**

Body: "Inherited from the session record and not independently reproduced — reproduce before fixing." Acceptance criteria unchecked, "Blocked by: None — can start immediately." 0 comments. No workaround stated.

### #862 — do-not.md invariant 8 states two facts a probe refutes

**Classification: NO-WORKAROUND**

Body describes a documentation-correctness defect (wrong CLI form + wrong flag/subcommand spelling documented in `do-not.md`) with unchecked acceptance criteria. 0 comments. No workaround described — this is a doc-accuracy fix not yet made; nothing says people currently use a different correct form as an interim measure (though the correct form is *named* in the body as what should replace the wrong one — that is a proposed correction, not a described-in-use workaround).

### #860 — The arm64 platform triple asserts a build variant containerd erases

**Classification: NO-WORKAROUND**

Body: "This is a seam to widen, not a concept to introduce" — references an existing test that already asserts the correct mapping in one place, but frames the issue as needing that seam widened to every call site. 0 comments. No workaround for callers today is described.

### #859 — graphify-update task advertises a removed version stamp

**Classification: NO-WORKAROUND**

Body is a doc/comment-accuracy defect (task description contradicts what the module actually does). Unchecked acceptance criteria, 0 comments. No workaround described.

### #858 — Declared-tools parser raises TypeError on bare-string os

**Classification: NO-WORKAROUND**

Body documents a parser defect with 3-armed measurement (bare string, list, integer) but no workaround — acceptance criteria unchecked, "Blocked by: None — can start immediately," 0 comments. Nothing describes how users currently avoid the crash (e.g., "always use list form"); the body's own framing is that "valid configuration crashes the smoke" without qualification of a safe form.

### #852 — Un-investigated ubuntu-26.04-arm smoke failure

**Classification: NO-WORKAROUND** (structural non-blocking status predates the issue, not an adopted workaround)

Body: leg failing, cause unknown, explicitly states it "cannot be promoted to blocking" until understood.

Comment 0 (sortakool): *"Recurred 2026-09-02 on PR #914 ... Everything else on that run passed, including `ci-gate` and both publishing legs — the `validate, false, false` parameters mark this as the non-blocking runner-validation leg, so it behaved exactly as designed and did not gate the merge."* This confirms the leg's non-blocking status prevents impact, but that status is the leg's pre-existing design (from #736), not something adopted *because of* this bug — nobody added anything in response to the failure; the comment simply notes recurrence and classifies it as "a repeating signal rather than a one-off." No new mitigation is described.

### #745 — Make ARM64 CI disk cleanup warning-free and effective

**Classification: NO-WORKAROUND**

Body documents an upstream-tracked action defect (`jlumbroso/free-disk-space#41`) with required-outcome/acceptance criteria, all unmet. Comment 0 (sortakool): *"Exact recurrence on PR #755 ... The run still completed successfully across both architecture builds ... This retains the warning as incomplete cleanup evidence under this existing carrier; it does not relabel the annotation cosmetic or create a duplicate issue."* This explicitly states nothing has changed — no workaround, just continued tracking of recurrence.

### #724 — Require atomic dirty-tree attribution before session-end and ship

**Classification: NO-WORKAROUND** (for #724 itself; a related workaround exists for the *spun-off* issue #725, which is out of scope here)

Body describes a large protocol gap (dirty checkouts, missing terminal disposition) with a required-protocol design, all acceptance criteria unchecked.

Comment 0 (sortakool) describes work done for a **different, spun-off issue** (#725): *"The accepted isolated prevention derives the complete scrub set from `git rev-parse --local-env-vars` ..."* and explicitly says: *"Keep #724 open until the prevention branch is published and its ship/land evidence is attached; #725 owns the underlying inherited-environment defect."* So the workaround-shaped content in this thread belongs to #725 (not in this `bug`-labeled list as enumerated — not checked separately here), and #724's own defect (atomic dirty-tree attribution) has no workaround described.

### #723 — Track and validate the generated feature lock

**Classification: NO-WORKAROUND**

Body documents a `.gitignore` vs. required-file conflict causing `main` pytest to fail, with a "Required fix" list, none applied. 0 comments. No workaround (e.g., "manually copy the generated lock before it's ignored") is described.

### #716 — Isolated worktree tool probes can rewrite shared hk hooks

**Classification: WORKAROUND-DOCUMENTED**

Body contains an explicit "## Immediate rule" section, stated as currently binding practice:

> *"Until this is fixed, isolated-worktree validation must use the repository's declared tasks and pinned environments. Do not use an ad-hoc version-qualified `mise exec` command against a linked worktree."*

This is a concrete, named substitute behavior (use declared tasks/pinned environments; never an ad-hoc version-qualified `mise exec` in a linked worktree) presented as the standing practice until the underlying fix lands, not merely a suggestion for a future fix. 0 comments — the workaround lives entirely in the issue body.

### #715 — Session transcript review requirement-complete

**Classification: NO-WORKAROUND**

This is by far the longest thread (15 comments, spanning 2026-08-11 to 2026-08-13), documenting an extensive, still-incomplete implementation effort (typed `RequirementCoverage` lane, semantic disposition tracking, incremental parsing, etc.). Every comment reports iterative *progress toward a fix* — e.g., the final comment: *"Two new non-authoritative promise claims were discovered and remain OPEN because no exact terminal fulfillment receipt is bound in the review packet ... Both remain part of the typed semantic backlog; issue existence is a carrier, not proof of satisfaction."* Repeated phrasing throughout: *"Issue remains open pending independent review/publication,"* *"This does **not** close #715,"* *"remains honestly INCOMPLETE."* No comment describes an interim workaround users rely on while the full requirement-coverage tooling is built — this is active construction of the fix itself, not a workaround for its absence. (Note: the issue body says *"This is why the user continues to restore requirements manually after transcript reviews"* — describing the user's current forced behavior in the *absence* of a fix, but this is presented as the painful symptom motivating the issue, not as an accepted/endorsed workaround with instructions for how to do it. No comment elevates it to a documented practice.)

### #479 — tmux-extended-keys skill prescribes lines the file never had

**Classification: NO-WORKAROUND**

Body: *"The failure is currently **masked**, and un-masks the moment dotfiles' source takes over the Mac (#431) ... This Mac behaves correctly only because **mde is the live chezmoi source today**"* — the masking is a coincidental fact about which repo is the active chezmoi source, not an action taken in response to this bug. 0 comments. No deliberate workaround described.

### #370 — `mise install` destructively re-locks mise.lock

**Classification: WORKAROUND-DOCUMENTED**

Comment 0 (sortakool) is headed *"Workaround found, measured today: `mise lock <TOOL>` locks surgically."* It gives the exact command and caveat:

> *"Naming the tool gives: ... **+70, no deletions**, 11 platform entries written for the new tool and nothing else touched ... This does not close the issue — the whole-lockfile path is still destructive, and `mise install` re-locking is a separate trigger. But it does mean adding a tool no longer requires accepting the rewrite: **lock the tool, not the file**, and diff before committing."*

Explicit, in-use workaround (scope `mise lock` to the specific tool's full backend name rather than running it bare) with a stated caveat about what it does *not* fix. Cross-referenced by two active auto-memory entries (`feedback_mise_lock_reuses_locked_version`, `feedback_mise_lock_whole_file_is_destructive`), corroborating this is a practice actually followed, not merely proposed once.

### #298 — Agent spawn/liveness unreliable in both directions

**Classification: WORKAROUND-DOCUMENTED** (with an explicit caveat that it does not reliably prevent recurrence)

Body's "What exists today" section:

> *"Memory `feedback_agent_spawn_liveness` — the correct probe + the deadline heuristic ... `.claude/rules/probes-need-a-control-arm.md` — carries the mode-2 case as a headline example. Both are doc-level. Neither prevents a session from inventing a fourth broken probe."*

This names a concrete workaround in active use today (the documented correct liveness probe + deadline heuristic in the memory file), but the issue itself immediately qualifies it: the workaround is doc-level only and "Neither prevents a session from inventing a fourth broken probe" — i.e., it is a known, named, currently-relied-upon practice, but the issue is explicitly about that practice's insufficiency. Reported as WORKAROUND-DOCUMENTED (a real workaround exists and is cited) rather than NO-WORKAROUND, but flagged with this caveat since the workaround's own reliability is the subject of the bug. 0 comments.

### #103 — rtk held at 0.37.2 — github backend omits url_api

**Classification: WORKAROUND-DOCUMENTED**

Body's "Current state" section: *"Held at `0.37.2` (restored its known-good lock block). See `mise.toml` comment on the rtk line and the `project_ci_unblock_2026-06-28` memory."* This is a concrete, currently-applied workaround (pin the tool at the last version whose lock entry works, rather than upgrading) with a pointer to where it is recorded in the actual config (`mise.toml` comment) and in memory. 0 comments — the workaround is stated in the body and is the issue's present, active state.

### #7 — Bootstrap paradox: run_before may find no config on fresh machines

**Classification: NO-WORKAROUND**

Body raises the risk and lists "Investigation Needed" steps, none resolved. It mentions *"The existing `install.sh` bootstrap flow may mitigate this via the `chezmoi init` -> `chezmoi apply` sequence, but this has not been verified on a truly fresh machine"* — explicitly speculative and unverified, not a confirmed workaround. 0 comments. No workaround confirmed as in use.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the issue corpus classified here
