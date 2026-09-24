# Session review — dotfiles-20260901.005 (2026-09-02)

Reviewed against: `.agent/notepad.md` (tail ~250 lines), `.agent/plans/session-2026-09-02.md`,
live `gh`/`git` state, `mise.toml`/`shared.toml` source. All claims below are probed
directly against the repo, not repeated from the digest.

## Part 1 — Findings

1. **[SHOULD-FIX] The "mise run sync liveness gap" is confirmed NOT filed anywhere.**
   Probe: `gh issue list --state all --search "sync liveness"` and `"digest-comparison"`
   → 0 hits relevant to this (one unrelated #299 hit). Control arm: same search shape
   for `"persistence gate"` → correctly returns #907 and 13 others, so the search
   mechanism discriminates; the 0-result was a real absence, not a broken probe.
   `file:line`: the bug itself is described in `.agent/notepad.md` around
   "⚠️ `mise run sync` reports OK on a CORRUPT `:dev`" — `mise run sync`'s currency
   check is digest-comparison only (`mise.toml`'s `[tasks.sync]`/converge path), with
   no `docker run --pull=never <tag> true` liveness check. It returned rc=0 on an
   image that could not `docker run` at all (`f8821f9a1636`, 4.62GB, missing content
   digest). This is a **repo-fixable gap** distinct from the Docker Desktop store fault
   itself — worth its own issue even though the store fault is external.

2. **[SHOULD-FIX] `mise.toml:88-95`'s comment is stale in a way not previously stated
   precisely.** The memory index says "mise.toml:88-95 still says otherwise" re: codex
   consolidation, but reading the current text (`mise.toml:88-90`) shows it now
   correctly narrates the MOVE to `shared.toml`. The real remaining defect is narrower:
   line 89 says *"the #613 in-container review lane's `npm:@openai/codex` in
   mise-runtime.toml"* — but `npm:@openai/codex` does **not** appear anywhere in
   `.devcontainer/mise-runtime.toml`. Probe: `grep -rn "openai/codex" mise.toml
   .devcontainer/mise-runtime.toml .config/mise/conf.d/shared.toml` → the only real
   declaration is `.config/mise/conf.d/shared.toml:38`. Control arm: the same grep for
   a term known present in `mise-runtime.toml` (`agents-lint`) returns a hit, so the
   grep isn't blind to that file. **So the comment misattributes the current file, not
   just the historical registry short-name** — the "owed one-line fix" from the handoff
   is real but its correct target is narrower than "codex was consolidated"; it needs
   to say "consolidated into `shared.toml` alone" and drop the `mise-runtime.toml`
   mention, or say why it's still named there (it shouldn't be — no such line exists).

3. **[NICE-TO-HAVE] `.agent/plans/session-2026-09-02.md` NEXT TASK 1 is already
   half-obsolete text for the next reader.** It says "wait for [#905] to merge, then
   `mise run land -- 905`" — #905 is CONFIRMED merged (`edd4219a`, per notepad) and
   `land` already ran (rc=0, main run 33603276201 success, per notepad item 4). The
   handoff file itself is stale relative to the session that consumed it; not
   corrected in-place. Low severity since the digest and notepad both carry the true
   state, but a resuming session reading only the handoff file (as instructed, "read
   these first, in this order") would start by re-doing a already-done step before
   discovering it's stale three paragraphs later in the digest. Recommend: the next
   session's first action should append a one-line "SUPERSEDED — done" marker at the
   top of NEXT TASK 1, matching the pattern already used for the prior handoff
   ("Supersedes `session-2026-09-01-e.md`").

4. **[BLOCKER — for next steps, not a defect] `fix/image-lock-pr-control-arms-887`
   (commit `e9495e5`) is NOT pushed and has no PR.** Probe: `git ls-remote origin
   refs/heads/fix/image-lock-pr-control-arms-887` → empty output. Control arm: the
   same command against a branch known to exist on origin (`docs/agent-briefs-887`
   tracks `origin/main`, not itself, confirming it too is unpushed — consistent with
   digest). This is real, uncommitted-to-remote work carrying the "5 vs 7 node ID"
   fix for #905's known gap. It cannot be lost locally (branch + commit exist), but a
   `git gc`, a stale worktree cleanup, or simply forgetting the branch name would
   strand it. **This is the single most important "don't lose work" item for the next
   session.**

5. **[SHOULD-FIX] `docs/agent-briefs-887` (commit `fcc99c1`) is unpushed and now
   3 commits behind main** (`origin/main: ahead 1, behind 3` per `git branch -vv`).
   Contains the five persisted agent briefs from the #887 session — required by
   `agent-report-persistence.md`. Not yet exposed via a PR; per
   `agent-report-persistence.md` these are meant to be durable/tracked, and right now
   they exist only in a local, unpushed branch.

6. **[BLOCKER for #821] PR #821 (`chore/lock-refresh`) is RED on `contract-preflight`
   and `ci-gate`, exactly matching issue #908's description.** Probe:
   `gh pr checks 821` → `ci-gate fail`, `contract-preflight fail`; job log
   (`gh run view --job 100192716621 --log`) shows
   `AssertionError: stale mise.lock entries for removed tools: ['node']` at
   `tests/test_lock_coverage.py:205`, matching #908's quoted excerpt verbatim.
   Auto-merge is armed on #821 (per digest) but cannot fire while red. This blocks
   itself indefinitely until #908 is resolved — every day's refresh re-triggers the
   same failure on a re-opened/updated PR.

7. **[SHOULD-FIX — ambiguity, Q2] Issue #908's hypothesis is well-hedged textually
   ("Hypothesis (evidence below, NOT yet proven)", explicit "What would confirm or
   refute it" section with a NEGATIVE control arm called out) — this is NOT a
   mis-stated-confidence problem.** Verified by reading the full issue body. No
   correction needed here; flagging it as checked-and-clean rather than a gap, since
   the team-lead's brief specifically asked to verify this reads as a hypothesis.

8. **[NICE-TO-HAVE] Session's #6 finding, "sync-full failing signature" — the
   record correctly warns a retry means nothing, but the SAME caveat is not repeated
   for #908/#821.** Once #908 is fixed and #821 is regenerated, a next day's
   refresh could still intermittently reproduce a similar-shaped issue if the
   `npm:` backend / node-resolution mechanism is genuinely runner-environment-
   dependent (per #908's own hypothesis) rather than deterministic. Not urgent,
   but the task-plan item for #908 should explicitly say "verify BOTH control arms
   in #908 before merging any fix" — currently nothing enforces that the fixer runs
   step 1 AND step 2 rather than picking a fix on hunch. This is exactly the
   "retry produces a green that means nothing" pattern the brief asked to hunt for,
   found in the *next* likely session rather than this one.

9. **[BLOCKER] `/plan-attest` still owed; PLAN TAMPERED fires every prompt, and
   its claimed tracking issue (#881) does not mention it — see 9b below for the
   control-armed confirmation.** (digest, confirmed present verbatim in
   `.agent/notepad.md`: "expected `6eb5c90b…`, actual `26cc6daf…`"). Handoff cites
   "Tracked by #881", but #881 is titled "Session skills should NOT carry
   planning-with-files state — five cold reviews, two defective designs", labelled
   `wontfix`, and its body never says "plan-attest" or "PLAN TAMPERED".

9b. **[BLOCKER — confirmed] #881's body contains ZERO mentions of "plan-attest"
    or "PLAN TAMPERED".** Probe: `gh issue view 881 --json body -q .body | grep -ic
    "plan.attest\|plan tampered"` → 0. Control arm: same body, `grep -ic "cold
    review"` → 1 (a term known present, since #881's title itself says "five cold
    reviews") — so the grep discriminates and the 0 is real. **This upgrades
    Finding 9 from ambiguity to confirmed gap**: the handoff's "Tracked by #881"
    claim (`.agent/plans/session-2026-09-02.md`) points at an issue that does not
    mention the thing it is claimed to track, and #881 carries a `wontfix` label.
    If #881 closes as wontfix, PLAN TAMPERED has no tracking issue at all.

10. **[NICE-TO-HAVE] `task_plan.md`/`findings.md`/`progress.md` in the repo root
    are confirmed gitignored** (`.gitignore:125-127`) and confirmed from a DIFFERENT,
    older session (`dotfiles-20260830.003`) per the digest's own note — I did not
    independently re-derive their session-of-origin (would require reading 106KB),
    but their gitignored status removes any risk they'd leak into a commit. Not a
    blocker; noting only because the team-lead's brief flagged them as inputs and a
    resuming session could confuse them for today's planning state if opened without
    checking the header/date.

## Part 2 — Proposed task-plan items

Ordered by dependency; #821/#908 chain is the true blocker for anything else on
main, so it leads.

---

**Task**: Fix #908 (`chore/lock-refresh` #821 red on stray `node` lock entry) —
run BOTH control arms named in the issue before choosing test-vs-generator as the
fix site.
**Why**: Finding 6 + 8. #821 has auto-merge armed but cannot land while red; every
day's cron re-triggers the same failure.
**Done when**: `mise run land -- <fix PR>` rc=0 AND #821 (or its next day's
re-generation) shows `contract-preflight`/`ci-gate` green AND the issue's step-1
(clean-env repro) and step-2 (negative/`npm:`-removed) control arms both ran and
are recorded in the PR description, not just "the test now passes".
**Gotcha**: Do not fix by allowlisting `node` or suppressing the assertion — #908
explicitly calls this out as a non-fix, and it would keep the same silent hole
open. Also: a green run tomorrow does NOT confirm the fix if only step 1 was run
(possible the mechanism is coincidental to this particular runner state).

---

**Task**: Push `fix/image-lock-pr-control-arms-887` (`e9495e5`) and open its PR.
**Why**: Finding 4 — real, reviewed work sitting only on local disk with the fix
for #905's known "5 vs 7 node ID" gap, plus the push-step and re-check tokens.
**Done when**: `git ls-remote origin refs/heads/fix/image-lock-pr-control-arms-887`
returns a ref, AND a PR exists (`mise run ship` from that branch, or `gh pr view`
after), AND its gates are read from real rc (lint/pytest/verify-contracts/
hook-selfcheck/eval/pin-actions — all reported 0 as of `e9495e5` per notepad, but
re-verify post-rebase since main has moved).
**Gotcha**: Rebase onto CURRENT main first — main has moved at least 3 commits
since `e9495e5` was cut (`e85c35b` #904, `e6458ed` #906, plus whatever landed for
#908/#821). Re-run mutation + contract-mutation evidence after rebase if the diff
in `refresh.yml`/`suites.toml` shifts at all — don't assume a clean rebase leaves
the pinned tokens unaffected.

---

**Task**: Push `docs/agent-briefs-887` (`fcc99c1`) and land it (docs-only, low risk).
**Why**: Finding 5 — durable persistence of five findings-bearing agent reports,
currently only local.
**Done when**: PR opened, `mise run land` succeeds, and the five reports are
visible via `git show origin/main:docs/research/kb/reports/agents/...`.
**Gotcha**: Rebase first — it's 3 commits behind main. No code touched, so this
should be a fast, low-conflict rebase; verify `mise run lint-docs` still passes
post-rebase (agnix size budgets can shift if any sibling doc changed upstream).

---

**Task**: File an issue for the `mise run sync` liveness gap (Finding 1) and,
separately, decide whether the underlying Docker Desktop content-store decay
(image losing layers while keeping its ID) needs its own tracked issue distinct
from the repo-fixable liveness check.
**Why**: Finding 1 — confirmed absent from the tracker via a control-armed search.
This is the gap that made 3 of 4 `ship` failures this session hard to diagnose:
`sync` reported "OK" on a corrupt image every time.
**Done when**: An issue exists describing (a) `sync`'s currency check has no
`docker run --pull=never <tag> true`-style liveness probe, (b) reproduction steps
from this session's notepad, (c) explicitly separates "repo can add a liveness
check" from "Docker Desktop's content store is externally decaying images" so a
fix PR doesn't try to solve the second inside the repo.
**Gotcha**: Don't conflate the two. A liveness check would have *caught* the decay
faster, but cannot *prevent* Docker Desktop from losing layers — the issue must
say so explicitly or a future session may scope a fix that promises more than a
repo-side check can deliver.

---

**Task**: Fix `mise.toml:88-90`'s comment to stop citing `npm:@openai/codex` as
present in `.devcontainer/mise-runtime.toml`.
**Why**: Finding 2 — narrower and more precise than the handoff's "owed one-line
fix"; the current wording is factually wrong about which file holds the
declaration (only `shared.toml:38` does).
**Done when**: `grep -n "openai/codex" mise.toml .devcontainer/mise-runtime.toml
.config/mise/conf.d/shared.toml` shows the comment referencing only
`shared.toml`, and `mise run lint-docs`/`mise run lint` pass.
**Gotcha**: Per the handoff's own note, this must be its OWN branch — "must NOT
ride on #905" (already merged) applies equally to any branch carrying #908's
fix or the image-lock-pr-control-arms branch; keep it isolated so a docs-only
change doesn't block on an unrelated gate.

---

**Task**: Run the mise-config-tier clarity task (handoff NEXT TASK 3).
**Why**: Explicitly the next operator-ordered task once #905's follow-ups land;
fully specified in `.agent/plans/session-2026-09-02.md:64` onward — not
re-derived here, just confirmed still queued and un-started (Finding: session
notepad has zero entries referencing it).
**Done when**: Per the handoff's own detailed spec at that line — not restated
here to avoid drift between two copies of the same spec.
**Gotcha**: Blocked only in the sense of priority ordering, not technically — the
handoff places it after #905 follow-ups and #821, but nothing prevents starting
it in parallel if the #908/#821 fix is handed to a separate lane.

---

**Task**: Correct or supersede NEXT TASK 1 in `.agent/plans/session-2026-09-02.md`.
**Why**: Finding 3 — the handoff instructs "wait for #905 to merge, then
`mise run land -- 905`", but this is already done (confirmed: `edd4219a` on main,
`land -- 905` rc=0 per notepad). A resuming session following the file verbatim
wastes a step before discovering staleness three paragraphs later.
**Done when**: The handoff file (or its replacement, if a new session-handoff is
written per the usual pattern) marks NEXT TASK 1 as done at the top, consistent
with how this file itself marked its predecessor "Supersedes ... DONE".
**Gotcha**: Per project convention this is normally done by writing a NEW handoff
file (`session-2026-09-02-b.md` or similar) rather than editing the old one in
place — check `.claude/skills/session-handoff` convention before editing history.

---

**Task**: File a new issue naming the PLAN TAMPERED warning specifically
(expected/actual hash mismatch) and stop treating #881 as tracking it.
**Why**: Finding 9/9b — confirmed via control-armed grep that #881's body never
mentions "plan-attest" or "PLAN TAMPERED"; #881 is `wontfix`-labelled and scoped
to a different, larger design question. The handoff's "Tracked by #881" claim is
false as written.
**Done when**: A new issue exists naming the exact warning text and hash values,
and `.agent/plans/session-2026-09-02.md` (or its successor) stops citing #881 for
this.
**Gotcha**: `/plan-attest` is user-invoked (per `.claude/rules/clarify-before-acting.md`
protocol-verb conventions elsewhere in this repo) — an agent cannot run it to
verify the fix; the new issue should say so explicitly so nobody assigns it to an
unattended agent lane.

---

**Task**: `mise run automerge -- 901` (dependabot pypdf bump).
**Why**: Explicit handoff NEXT TASK 5, still unexecuted (session digest ends
before reaching it — the session was consumed entirely by #905 follow-ups and the
Docker Desktop fault).
**Done when**: `gh pr view 901 --json mergeStateStatus` shows it merged or
auto-merge armed and its checks are green.
**Gotcha**: `automerge` is bot-PR-only per `mise-tasks-only.md`'s provenance
table — do not use `ship`/`land` for this PR.

## Part 3 — Ambiguities to resolve before the next session starts

1. **Exact wording to replace** — `.agent/plans/session-2026-09-02.md:6-7`:
   > 1. **#905** — wait for it to merge, then `mise run land -- 905`. If it is RED,
   >    investigate (mind the non-blocking arm64 leg — see gotcha 4).

   Replace with (or supersede via a new handoff file per convention):
   > 1. ~~#905 — wait for it to merge, then `mise run land -- 905`.~~ **DONE**:
   >    merged as `edd4219a` 07:22:50Z; `land -- 905` rc=0 (main run 33603276201
   >    success). See `dotfiles-20260901.005` digest for the follow-up commit review.

2. **Exact wording to replace** — the memory index line (MEMORY.md, session
   2026-09-02 entry): *"mise.toml:88-95 still says otherwise"*.
   This is imprecise about WHAT still says otherwise. Replace with:
   > `mise.toml:89` still mis-cites `npm:@openai/codex` as present in
   > `.devcontainer/mise-runtime.toml`; it is not — only `shared.toml:38` declares
   > it. The consolidation narrative itself (lines 88-90) is otherwise accurate.

   Without this correction, a session tasked with "the mise.toml:88-95 staleness
   fix" could read the whole comment, find the consolidation narrative accurate,
   and conclude there's nothing to fix — missing the one factually wrong clause.

3. **Exact wording to replace** — `.agent/plans/session-2026-09-02.md`'s
   "Tracked by #881" claim for `/plan-attest`/PLAN TAMPERED (exact location:
   search the file for "#881"). Replace with a pointer to the new issue filed
   per the task-plan item above, since #881 does not mention this warning.

4. **Missing "when"/"only if"** — none of the remaining task-plan items required
   fabricating a missing condition; the handoff's own NEXT TASK list already
   states its ordering explicitly ("in order").

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues
  #907/#908/#881/#899/#903/#905, PR #821/#901, workflow run logs, `git`/`gh`
  state for branches `fix/image-lock-pr-control-arms-887` and
  `docs/agent-briefs-887`.

_None._ (no other repos consulted)
