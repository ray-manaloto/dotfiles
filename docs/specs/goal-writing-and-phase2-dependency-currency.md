# `/goal` mechanics, and the Phase 2 dependency-currency goal

Two things, deliberately in one file: the **reusable mechanics** of writing a
`/goal` in this repo, and the **current Phase 2 goal text** as a worked
instance. The mechanics were re-derived twice and cost an advisor consult to
establish; writing them down once is what stops a third re-derivation.

Established 2026-09-14. Archive of the pre-edit text and the full verdict that
produced it: `docs/research/kb/reports/agents/adv-goal-revision-2026-09-14.md`
(and its brief, `adv-goal-revision-brief-2026-09-14.md`).

**Issue twin: #1060**, carrying the same goal text. Two carriers with different
failure modes — this file survives offline and a lost network, the issue
survives a fresh clone and is what `gh issue list` actually surfaces. **This
file is authoritative if the two ever disagree.** Close #1060 when Phase 2
lands.

## The mechanics — true for EVERY goal, not just this one

1. **`/goal` is a Stop hook, and its evaluator runs no commands and reads no
   files.** It judges **only the session transcript**. This is the fact that
   decides how every clause must be phrased.
2. **Therefore a criterion naming a command the evaluator cannot run is
   unverifiable by construction.** "The automation works" is not a criterion.
   "The canary's non-zero rc appears in the same block as a known-good rc=0"
   is, because the evaluator can see both.
3. **Every clause must demand its evidence be PRINTED** in the transcript.
4. **The limit is 4,000 characters.** Measured 2026-09-14 against the harness
   corpus `goal.md` line 64, with a control arm. Count before pasting.
5. **One paragraph, no markdown, no newlines** — it is pasted after `/goal `.
6. **`/goal` is NOT model-invocable.** The operator types it. An agent can
   draft and measure the text; it cannot set the goal.

### Failure shapes this repo has already hit

- **A grep-for-existence clause that the ALREADY-LANDED code satisfies.** The
  first draft demanded a skill + mise task + python module "exist, shown via
  grep output" — which `mise.toml:1627` `[tasks.dependency-currency]` and
  `python/src/dotfiles_setup/dependency_currency.py` already satisfied with zero
  new work. A check that can only pass is not a check
  (`.claude/rules/probes-need-a-control-arm.md`).
- **An exception that contradicts the goal's own delivery.** The first draft
  excepted a known-failing test from the gate while also requiring the work to
  ship — but `mise run ship` runs the full unfiltered suite as a hard gate
  (`python/src/dotfiles_setup/pr.py:324` -> `:370` -> `:581`, no path
  excepts it), so the permitted state was one `ship` can never pass through.
- **A clause naming an outcome the transcript cannot show.** "Image bumps get
  their own PR" is not verifiable from two PR numbers; it needs the per-PR
  `gh pr view --json ...files...` output plus an assertion that the other PR
  contains none of the image-input paths.
- **`ship rc=0` is not "merged".** It means auto-merge was ARMED
  (`python/src/dotfiles_setup/pr.py:608`). Report pending CI as pending.
- **Mocks and self-authored receipts do not count** as evidence
  (`.claude/rules/real-integration-evidence.md`).

## The Phase 2 goal — paste-ready

**3,532 characters** of the 4,000 budget (measured; pure ASCII, so bytes and
characters agree). Five clauses.

⚠️ This is the CURRENT text. The prior six-clause version carried a `#1053`
precondition as clause (1); **#1053 was fixed and closed on 2026-09-14**, so
that clause is dropped and the rest renumbered. Dropping it loses no evidence:
clause (4) below already demands `mise run lint`, `pytest` and
`mise run verify` printed with rc=0 and zero failures.

Paste this after `/goal `:

```text
Build and autonomously ship the NEW pin-update workflow. Met only when ALL evidence below comes from commands Claude actually ran and printed in this transcript, with real captured exit codes, worktree, baseline and tested commit SHA; final evidence must match each shipped PR head. (1) Print the version-controlled diff from the session baseline and line-numbered skill, mise-task, CLI-dispatch and python/src/dotfiles_setup/ module excerpts identifying the NEW mutation entrypoint; then execute exactly the mise invocation documented by that skill. Its Python orchestration must apply bumps, gate them, drop and report red pins, partition image bumps and invoke ship. Existing dependency-currency or renovate-dryrun reporting alone does not count. Reuse native mechanisms and canonical lock, lock-shared and lock-image tasks as appropriate; print invocations and results. (2) Through that same public mutation entrypoint, run a disposable repository fixture with a green baseline, a compatible stale pin and an upstream-resolvable but gate-failing pin. Print commands and child results, the actual old-to-new pin patch, and parsed before/after manifest and lock values. Print acceptance assertions showing the compatible bump retained after green gates, the other candidate's gate rc nonzero, its pin and associated locks restored, and the final retained set green. Read and print the report CONTENT containing the dropped name, attempted version, failing command, rc and reason; test -f alone is insufficient. Print named acceptance-test results and rc=0; mocks or self-authored success receipts alone do not count. (3) MANDATORY CANARY on every workflow run before applying updates: use the actual acceptance/resolution path and same executable/environment for two versions of the same package, one known-good and one demonstrably nonexistent upstream. Print both inputs, resolver output and captured rc values together in one block: good rc=0, nonexistent rc nonzero for version rejection. Unavailable tools, authentication/network errors or timeouts do not count. Missing or wrong arms must block the workflow and its acceptance tests. (4) Run that same workflow on the real repository and print its complete candidate/applied/dropped inventory and retained pin diffs. Print mise run lint, uv run --project python pytest tests/ -q and mise run verify with actual rc=0 and their passing summaries, zero test failures/errors and zero failed contracts, on each final PR head; every additional applicable ship gate must pass. (5) Ship the implementation and retained bumps autonomously through mise run ship per nonempty branch; print each real ship rc=0 and its PR-number/AUTO-MERGE-enabled output. For each PR print gh pr view -R ray-manaloto/dotfiles <number> --json number,url,baseRefName,headRefName,headRefOid,files,state,autoMergeRequest and its pin diff. If any image bumps survive, a distinct image PR must contain them and their required companion locks, including applicable changes to .config/mise/conf.d/shared.toml, .devcontainer/mise-system.lock and .devcontainer/mise-runtime.lock; the other PR must contain none of those image-input changes. Print complete PR file lists and verified pin-to-PR assignments, with no mixed or omitted retained bumps. If none survive, print the inventory establishing that fact. Each PR must show autoMergeRequest non-null or state MERGED; report pending CI as pending, never as merged. File existence, issue references or prose without the specified output cannot satisfy this goal.
```

## What the goal encodes (the settled design — do not re-litigate)

- Shape: **skill -> mise task -> python module**
  (`.claude/rules/mise-tasks-only.md`, `.claude/rules/zero-bash-logic.md`).
- Fully autonomous; ships via `mise run ship` and **accepts auto-merge on
  green**.
- **Image-build-input bumps get their own PR** — `.config/mise/conf.d/shared.toml`,
  `.devcontainer/mise-system.lock`, `.devcontainer/mise-runtime.lock`.
- On a red gate: **drop that pin, keep the rest, report it.**
- **A canary is mandatory**: feed a version that does not exist upstream and
  print its non-zero rc in the same block as a known-good pin's rc=0, through
  the same acceptance path and executable. Rationale:
  `.claude/rules/probes-need-a-control-arm.md` rule 9.

⚠️ **The read-only half is already landed** (`decf0aa`): `mise.toml:1627`
`[tasks.dependency-currency]` plus `python/src/dotfiles_setup/dependency_currency.py`,
which states outright "Never a recommendation to bump". Phase 2 is the
**mutating** half. Do not rebuild the reporter, and do not let an
existence check pass on it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo this goal governs.
