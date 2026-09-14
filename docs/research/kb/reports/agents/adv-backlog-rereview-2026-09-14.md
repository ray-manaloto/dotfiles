# adv-backlog-rereview — 2026-09-14 (advise-only)

Re-review of `docs/research/kb/reports/agents/backlog-triage-2026-09-14.md`
against repo state that moved after it was written. Advisory only — no
source edited, no issue filed/closed, nothing shipped.

## Verdict, first line

**The triage's verdict stands: rank 1 (hk currency → 2.0 readiness) is still
rank 1, and its `/goal` clause 2 (group the 3 pkl files into
`packageRules[0]`) is the correct next action — confirmed by NEW evidence the
triage didn't have (the ci.yml build filter and the file lists of #1079/#1090
vs #1063).** One operational fact has changed that the next session must
notice on its own: **PR #1094 (the pin-parity gate itself) MERGED at
2026-09-14T21:07:26Z**, after the triage and after the coordinator's brief to
this lane was written (which still called it "open, on final smoke tests").
The working branch `feat/pin-parity` is now 4 commits behind `origin/main`
and its own PR is `MERGED` — the next session must branch fresh off
`origin/main`, not continue on this branch (`do-not.md` #9,
`feedback_amend_after_ship_races_automerge`).

## The one deciding risk

**None of the triage's ranking or `/goal` is invalidated.** The single risk
worth flagging is procedural, not substantive: if the next session resumes
on `feat/pin-parity` (the CWD's current branch) instead of branching fresh
off `origin/main`, it inherits a branch whose own PR already merged — any
further commit on it either won't reach `main` cleanly or risks a second,
confusing PR against an already-closed branch. This is a "before you touch
anything" check, not a blocker to the ranking.

---

## Q1 — Is rank 1 still rank 1?

**Yes, unchanged, and the coordinator's premise for asking is itself wrong.**
`gh pr view 1091 --json body` confirms #1091 = `npm:typescript` `5.9.3` →
`7.0.2`, merged as `1c78e65`. But **the triage never lists this as an
outstanding major** — grepped `docs/research/kb/reports/agents/backlog-triage-2026-09-14.md`
for `typescript`/`major`: zero hits outside an unrelated TS-hook item (U6).
So "a MAJOR the triage listed as outstanding" (finding 1 in the brief) is a
misreading of the triage, not a fact about it — nothing in the ranked table
changes on account of #1091. #1087/#1095/#1088 are routine bot bumps,
likewise untouched by the ranking. Rank 1 (hk chain) still has, by a wide
margin, the largest unblock count (5 PRs + 8 tool bumps inside #1063 + the
hk-builtin-adoption issues) and the largest blast radius (hk IS the lint
gate; `HK_PKL_BACKEND=pkl` still live — see Q3).

## Q2 — Any ranked row whose unblock count the triage itself now shows wrong?

**No new breakage found.** Re-derived, not inherited:

- Row 1 (hk chain): `gh pr checks 1063` → `autofix fail`, `ci-gate fail`,
  `image-lock-pr fail`, `lint fail`, all still red; `gh run view 34839072681
  --log | grep lockfile` → `hk@1.58.1: hk@1.58.1 is not in the lockfile`
  repeated 4x — the exact cause the triage's own follow-up
  (`adv-hk-1581-2026-09-14.md`) named, unresolved. `gh pr checks 1079` →
  `lint pending` only (still the `hk_version_parity` deadlock class). Both
  counts hold.
- Row 6 (retrieval/graph): `mise run graphify-health` → `fresh
  (runtime=0.9.61)` — unchanged, #1054's defect (zero markdown nodes) is
  about node coverage, not freshness; still open.
- Row 3 (#678 stale-blocked): `gh issue view 676 677 --json state,stateReason`
  still `CLOSED`/`COMPLETED`; #678's body still lists them as blockers
  (re-verified by direct read, not re-quoted from the triage).

The triage's own caveat ("ranked, not measured", §7 of "WHAT I COULD NOT
DETERMINE") still holds and is the honest position — I did not find a
counter-example that overturns any row's *relative* order.

## Q3 — Are any of U1–U12 now filed, stale, or non-reproducing?

- **U9 (fnox versioned-path crash) does NOT reproduce in a new shell** —
  re-confirmed independently: `zsh -lc 'fnox --version'` → clean `fnox
  1.35.2`, and the shell function baked at
  `~/.zshrc.d/50-mde-secrets.zsh:27-28` now resolves `.../1.35.2/...`. This
  matches finding 4 in the brief AND matches the triage's own text verbatim
  ("a NEW shell's `fnox activate zsh` emits …/1.35.2/…") — the triage already
  called this correctly as "stale long-lived shell, cleared by a new shell",
  not a live defect. No disposition change needed; U9 was never claimed
  live-blocking.
- **U8 (`HK_PKL_BACKEND=pkl` in user-global mise config) is CONFIRMED still
  live**: `grep HK_PKL_BACKEND ~/.config/mise/config.toml` →
  `82:HK_PKL_BACKEND = "pkl"`. Unchanged, matches finding 5.
- **U1–U5 re-checked against `gh issue list --search` with a fresh probe.**
  Caveat: GitHub's search API is fuzzy/stemmed, not substring — the control
  arm (`pin-parity`) returned 17 loosely-related issues, so a "search hit"
  alone is weak evidence either way. Given that noise, I did not find a
  clean exact-title/body match for U1 ("guard stderr discarded"), U3
  (`.codex/hooks.json` untracked), U4 (superset matcher), or U5 (graphify
  guard has zero wiring coverage) that would supersede the triage's own
  control-armed per-item check (which was done closer to real-time and with
  narrower per-item queries). No disposition changes.
- One correction worth recording: **U4 and U5's rank-2 item is corroborated
  by a THIRD live instance of the same structural gap** — #1090 (hk.pkl ×3,
  the v2.0.0 pkl-amends bump) and #1093 (shared.toml+lock, the v2.0.0 tool
  bump) are **currently split exactly the way #1079/#1063 were split** for
  1.58.1 (`gh pr diff 1090/1093 --name-only`). This is new evidence that the
  matchFileNames gap (Q4) will keep recurring at every future hk major, not
  just the current backlog — strengthens, does not change, the ranking.

## Q4 — Is `/goal` clause 2's `packageRules[0]` choice correct?

**Yes — confirmed correct, not just plausible.** New evidence the triage
didn't cite:

- `ci.yml:20-22` (trigger list) names all three pkl files, but the actual
  **build-path filter** at `ci.yml:288-292` includes `hk-common.pkl` and
  `hk-image.pkl` — **not `hk.pkl`**. So `hk-common.pkl`/`hk-image.pkl` are
  genuine image-build inputs today (`.devcontainer/Dockerfile:393` `COPY
  hk-image.pkl /etc/hk/hk.pkl`, content-hashed per
  `feedback_content_hash_must_cover_copy_inputs`), independent of any
  Renovate grouping decision. `hk.pkl` (host-only project config) is not.
- `gh pr diff 1079/1090 --name-only` → both already touch **all three** pkl
  files as a single Renovate branch (a pre-existing manager grouping, not a
  `packageRules[0]` effect). `gh pr diff 1063 --name-only` → `shared.toml` +
  `mise.lock` only, no pkl files.
- Consequence: today, a simultaneous hk bump produces **two independent
  cold-build-triggering PRs** (the shared.toml/#1063 one, and the
  hk-common/hk-image.pkl one bundled inside #1079/#1090) — exactly the
  redundant-cold-build cost `packageRules[0]`'s own stated rationale (a)
  exists to prevent. Adding all three pkl files to
  `packageRules[0].matchFileNames` does not introduce a *new* cold build
  (two of the three files already force one); it collapses two into one,
  which is the rule's own justification applied to a case it doesn't yet
  cover. `hk.pkl` riding along is free — it already travels with the other
  two on one branch.
- A **separate, hk-only packageRule** would not gain anything: it would
  still need `matchFileNames` covering `shared.toml` (for the version pin at
  `.config/mise/conf.d/shared.toml:37`) to fix #1063's actual failure
  (lockfile-not-regenerated), and once `shared.toml` is in scope it is
  functionally the same grouping `packageRules[0]` already does for every
  other image input — a second rule would just duplicate the first's
  mechanism for one dependency.

**Clause 2 is correct as written; no change recommended.**

## Q5 — Any `/goal` clause unsatisfiable, or satisfiable without doing the work?

Checked against `docs/specs/goal-writing-and-phase2-dependency-currency.md`'s
named failure shapes (grep-for-existence, contradicting-exception,
transcript-unshowable outcome, `ship rc=0` ≠ merged, mocks/receipts):

- No grep-for-existence clause — clause 2 demands the *regrouped PR's file
  list*, which only exists after real work; a `renovate-dryrun` result is
  offered as the alternative evidence, which is itself a real command run
  against real config, not a mock.
- No clause contradicts `ship`'s own gate; clause (5) explicitly requires
  `autoMergeRequest non-null or state MERGED` and forbids reporting pending
  CI as merged, matching the spec's stated fix for that exact failure shape.
- Clause 4's two-arm probe (hk 2.0 binary, `HK_PKL_BACKEND` set vs unset) is
  concretely executable without landing anything: `mise ls-remote
  aqua:jdx/hk` already lists `2.0.0` (re-confirmed: fetchable), so `mise exec
  aqua:jdx/hk@2.0.0 -- hk ...` run twice with the env var toggled is a
  self-contained, disposable probe — it does not require bumping the repo's
  pin first. This directly answers Q7 below.
- One gap, not fatal: clause 2's "print the regrouped Renovate PR's file list
  … in one PR" clause assumes Renovate will retroactively fold the
  **already-open** #1063/#1079/#1090 branches into one after the
  `renovate.json` edit lands — Renovate typically supersedes/recreates
  branches on its next run rather than merging two live PRs by hand, and the
  clause doesn't say what happens to the three stale PRs. The dryrun
  fallback already in the clause covers this if the live regroup doesn't
  happen inside the session window; worth the next session watching for
  explicitly rather than assuming.

**No clause is unsatisfiable or trivially satisfiable; the one gap above is a
timing risk, not a defect in the goal text.**

## Q6 — Branch/worktree hygiene: anything blocking?

- `git worktree list` → 2 detached-HEAD scratchpad worktrees (one already
  `prunable`) — neither touches this repo's tracked branches, not blocking.
- `git stash list` → one stash on `chore/deps-currency` referencing the
  retired `.omc` path — inert, not blocking.
- **New finding, not in the coordinator's brief**: the CWD's current branch,
  `feat/pin-parity`, is the branch whose own PR (#1094) **just merged**
  (`git log --oneline HEAD..origin/main` shows 4 commits including `2fbc33f
  feat(pin-parity)… (#1094)`; `git log --oneline main..HEAD` shows the
  identical commit `f5f2fb8` pre-merge, confirming it's the same work,
  already landed). Per `do-not.md` #9 and
  `feedback_amend_after_ship_races_automerge`, this branch is **closed** —
  any further work must be a fresh branch off `origin/main`, not a continued
  commit here. This is the one actionable item this re-review adds.
- The three PRs named in the brief (#1062, #1083, #1084) are confirmed
  merged by direct `git log -1` on their local branches, matching the
  brief's own verification — no correction needed there.

## Q7 — Is item 4 of "WHAT I COULD NOT DETERMINE" now determinable?

**Item 4 (hk 2.0's Config.pkl acceptance) remains genuinely undetermined —
but a two-arm probe absolutely could settle it, and `/goal` clause (4)
already specifies exactly that probe.** Arms, as clause 4 states and as I
verified are executable without side effects:

- **Arm A (suspect):** fetch hk 2.0.0 via mise (`mise ls-remote aqua:jdx/hk`
  confirms `2.0.0` is resolvable today), run it against this repo's
  `hk.pkl`/`hk-common.pkl`/`hk-image.pkl` with `HK_PKL_BACKEND=pkl` exported
  (the value `~/.config/mise/config.toml:82` currently sets).
- **Arm B (control):** the identical invocation with that variable unset.
- **Discriminating result:** Arm A fails naming a replacement/removed value;
  Arm B does not. If both fail identically or both pass, clause 4 already
  requires reporting that as NON-DISCRIMINATING rather than as a cleared or
  confirmed blocker — correctly anticipating the failure-mode this rule set
  (`probes-need-a-control-arm.md`) exists to prevent.

I did **not** run this probe myself — out of scope for an advise-only lane,
and clause 4 is written to be run by the session that owns the work.

---

## What I could not verify

- Whether Renovate will retroactively regroup the three already-open
  hk-related PRs (#1063, #1079, #1090) after the `renovate.json` edit lands,
  versus requiring them closed/superseded first (Q5's one gap).
- The exact GitHub search relevance ranking behind Q3's `gh issue list
  --search` results — confirmed it is fuzzy/stemmed via the control arm, but
  could not fully rule out a near-duplicate filing for U1/U3/U4/U5 beyond
  what the triage's own tighter per-item check already did.
- Whether hk 2.0's `Config.pkl` actually accepts this repo's config —
  unchanged from the original triage; Q7 names the probe, does not run it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  subject: PRs #1063/#1079/#1090/#1091/#1093/#1094/#1095, issues #676/#677/
  #678, `ci.yml`, `renovate.json`, source files cited above.
- [jdx/hk](https://github.com/jdx/hk) — v2.0.0 fetchability confirmed via
  `mise ls-remote aqua:jdx/hk`, cited by PRs #1090/#1093's bodies.
