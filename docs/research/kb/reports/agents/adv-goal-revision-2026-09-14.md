# Advisory verdict: /goal draft for dependency-currency automation (2026-09-14)

Advisor lane: codex-astra-advisor (this session, Claude Sonnet 5, orchestrating a
`codex exec` call on `gpt-6-astra` at `model_reasoning_effort=xhigh`, read-only
sandbox). Per the lane's protocol, the reasoning below is codex's own verdict,
relayed — not this session's in-model reasoning.

## VERDICT

**DRAFT NEEDS REVISION** (codex called it "UNSOUND" — see note below on
terminology; the substance is "needs revision," not "cannot be fixed").

**The single deciding risk:** the draft's clause (4) carves out an exception
for issue #1053 ("except the known pre-existing failure in #1053"), but
`mise run ship` — which the settled design requires for delivery — runs the
full pytest suite as an unconditional hard gate with no such exception
(`python/src/dotfiles_setup/pr.py:324` builds the pytest gate,
`pr.py:370`'s `run_gates` stops at the first failure, `pr.py:581` returns
before push/PR-creation on any gate failure). So the draft goal can be
satisfied by a transcript state ("gates green except #1053") that the
project's own `ship` command can never actually reach while #1053 is open.
The goal as drafted would let the evaluator mark "met" on a state that
structurally cannot produce a shipped PR — directly contradicting the settled
design that the deliverable ships.

## Answers to the four questions (codex-astra, each grounded in file:line)

### Q1 — Does clause (1) get trivially satisfied by the already-landed read-only reporter?

**Yes**, and codex's read confirms it precisely: the mise task at
`mise.toml:1627` already names a `python/src/dotfiles_setup/` module
in its own description/comment, and its CLI dispatch already reaches
`dependency_currency_main` at `python/src/dotfiles_setup/main.py:2607`. That
function's `CurrencyReport` docstring literally states "Never a recommendation
to bump" (`python/src/dotfiles_setup/dependency_currency.py:76` and `:299`,
confirmed independently by this session's own read at the top of
`dependency_currency.py`). A grep-based existence check (clause 1 as
drafted) is satisfied today, on the current HEAD, with zero new work.
Adding a trivial skill file that merely *invokes* the existing reporter would
also satisfy the clause's literal wording without implementing any mutation.

Correction to this session's own supplied context: `update:all` and
`update:check` are **global** mise config (`~/.config/mise/config.toml:598`,
`:638`), not in this repo's `mise.toml` — they run machine-tool updates and
report drift respectively, neither of which performs a repo-pin bump/PR
transaction. `renovate-dryrun` (`mise.toml:891`) is also reporting-only.

**Rewording to bind the NEW capability**, per codex: require the transcript
to show (a) the version-controlled diff introducing a NEW mutation entrypoint
(skill → mise task → CLI dispatch → python module, all four layers, with
line-numbered excerpts), and (b) that entrypoint actually invoked and
observed applying a retained compatible bump, a gate-triggered rollback and
report of an incompatible one, and partitioned shipping. Existence of the
existing read-only reporter must be explicitly disqualified as satisfying the
clause.

### Q2 — Is the goal internally contradictory re: #1053 and shipping?

**Yes, confirmed.** The gate chain is unconditional:

- `ship`'s gate matrix always includes the full pytest run —
  `python/src/dotfiles_setup/pr.py:324`
  (`("uv", "run", "--project", "python", "pytest", "tests/", "-x", "-q")`).
- `run_gates` stops at the first nonzero-rc gate — `pr.py:370`.
- A failed gate matrix returns before push/PR creation — `pr.py:581`
  (`if not run_gates(...): return 1`).

There is no code path by which `ship` treats #1053 as excepted. So "tests
green except #1053" is a state the evaluator could be shown in the transcript
(by running `pytest` with `--deselect` or similar), but it is NOT a state
`ship` itself will ever pass through, because `ship` runs the unfiltered
suite. A goal permitting completion on the excepted-test transcript state
while also requiring "shipped" is therefore internally contradictory: the
excepted state can never causally lead to the shipped state via the project's
own tooling.

Codex's recommendation, which this session concurs with: **do not except
#1053 at all.** Require #1053 resolved as a precondition — the regression
test itself must show `1 passed` and rc=0 in the shipping environment, plus
the full unfiltered suite green, before the goal can be met. "Unresolved
means blocked, not met" — not a silent scope-narrowing to "PR opened, gates
green except #1053," because that would require rewriting `ship`'s own
validation boundary (a different, out-of-scope change) rather than just the
goal text. This session's Q2 also asked "should shipping be removed from
scope" — codex's answer is implicitly no: since the settled design requires
autonomous shipping and #1053 is why it currently can't, the correct fix is
to make #1053-resolution a precondition of the goal rather than carve an
exception into either the goal or the tool.

### Q3 — Is "Image-build-input bumps get their own PR" transcript-verifiable as worded?

**No**, as a bare trailing sentence it names a design intent, not a command
whose output would appear in the transcript. Two PR numbers alone (e.g. from
`gh pr list`) only prove two PRs exist, not that the bumps were correctly
partitioned between them.

Codex's exact replacement wording: require, for each resulting PR, printing
`gh pr view -R ray-manaloto/dotfiles <number> --json
number,url,baseRefName,headRefName,headRefOid,files,state,autoMergeRequest`
plus its pin diff, and require that if image bumps survive, a distinct PR
contains them and their **companion locks** — codex confirmed the three real
image-build-input paths against `pr.py:130`
(`changes_base_image_inputs`), and that `lock-shared` (`mise.toml:1361`)
updates `.config/mise/mise.lock` while `lock-image` (`mise.toml:1393`) covers
only the two devcontainer locks — so a correct clause must name
`.config/mise/conf.d/shared.toml`, `.devcontainer/mise-system.lock`, and
`.devcontainer/mise-runtime.lock` explicitly and require the OTHER PR contain
none of them.

### Q4 — Other clauses the evaluator could not confirm from transcript output alone

Five gaps codex identified, verified by this session's spot-check of the
cited lines:

1. **`test -f` on a report artifact proves existence, not content.** The
   evaluator cannot open the file itself (`goal.md:56` in the KB corpus,
   confirmed this session's own earlier read: "It doesn't run commands or
   read files independently"). Clause must require the report's *content* —
   dropped pin name, attempted version, failing command, rc, reason — be
   printed into the transcript via `cat`/equivalent.
2. **A nonempty `git diff --stat` is not evidence of a correct bump.** It
   proves *some* change happened, not that the change is the right one.
   Require printed before/after manifest and lock values, or a named
   acceptance-test result with rc=0, mirroring `tests/AGENTS.md`'s no-mocks
   standard (`tests/AGENTS.md:53`).
3. **An arbitrary nonzero canary rc could be an infrastructure failure**
   (network unavailable, auth expired, tool missing) rather than a genuine
   version-rejection. Rule 9 of `probes-need-a-control-arm.md` requires the
   canary to run the *same acceptance path* as the real check, on every run,
   not as a one-off demonstration (`probes-need-a-control-arm.md:99`,
   `:127`). The clause needs to say "unavailable tools / network errors /
   timeouts do not count as a valid canary arm."
4. **`ship rc=0` means auto-merge was armed, not that the PR merged or CI
   went green.** `pr.py:608` — ship returns after enabling native
   auto-merge; "GitHub merges it the instant ci-gate goes green (no poll)."
   A goal claiming "shipped" on `ship rc=0` alone overclaims; it must
   require printed PR state (`autoMergeRequest` non-null, or `state
   MERGED`) and must never report a pending-CI PR as merged.
5. **Mocks or self-authored success receipts are insufficient** per
   `real-integration-evidence.md:3` — the goal should require execution
   through the real public entrypoint (`mise run <task>`), not a stub.

## REVISED GOAL TEXT

Below is codex-astra's revised text, reproduced verbatim (paste-ready after
`/goal `, single paragraph, no markdown/newlines in the pasted form — line
wraps below are presentational only):

Build and autonomously ship the NEW pin-update workflow. Met only when ALL evidence below comes from commands Claude actually ran and printed in this transcript, with real captured exit codes, worktree, baseline and tested commit SHA; final evidence must match each shipped PR head. (1) Resolve shipping blocker #1053 before completion: print uv run --project python pytest tests/test_process_env.py::test_real_pre_push_poison_cannot_modify_outer_repository -q showing 1 passed and rc=0 in the shipping environment, plus the unfiltered full-suite result. A failing baseline blocks updates; it is not an incompatible pin. No #1053 exception, test suppression or gate bypass; unresolved means blocked, not met. (2) Print the version-controlled diff from the session baseline and line-numbered skill, mise-task, CLI-dispatch and python/src/dotfiles_setup/ module excerpts identifying the NEW mutation entrypoint; then execute exactly the mise invocation documented by that skill. Its Python orchestration must apply bumps, gate them, drop and report red pins, partition image bumps and invoke ship. Existing dependency-currency or renovate-dryrun reporting alone does not count. Reuse native mechanisms and canonical lock, lock-shared and lock-image tasks as appropriate; print invocations and results. (3) Through that same public mutation entrypoint, run a disposable repository fixture with a green baseline, a compatible stale pin and an upstream-resolvable but gate-failing pin. Print commands and child results, the actual old-to-new pin patch, and parsed before/after manifest and lock values. Print acceptance assertions showing the compatible bump retained after green gates, the other candidate's gate rc nonzero, its pin and associated locks restored, and the final retained set green. Read and print the report CONTENT containing the dropped name, attempted version, failing command, rc and reason; test -f alone is insufficient. Print named acceptance-test results and rc=0; mocks or self-authored success receipts alone do not count. (4) MANDATORY CANARY on every workflow run before applying updates: use the actual acceptance/resolution path and same executable/environment for two versions of the same package, one known-good and one demonstrably nonexistent upstream. Print both inputs, resolver output and captured rc values together in one block: good rc=0, nonexistent rc nonzero for version rejection. Unavailable tools, authentication/network errors or timeouts do not count. Missing or wrong arms must block the workflow and its acceptance tests. (5) Run that same workflow on the real repository and print its complete candidate/applied/dropped inventory and retained pin diffs. Print mise run lint, uv run --project python pytest tests/ -q and mise run verify with actual rc=0 and their passing summaries, zero test failures/errors and zero failed contracts, on each final PR head; every additional applicable ship gate must pass. (6) Ship the implementation and retained bumps autonomously through mise run ship per nonempty branch; print each real ship rc=0 and its PR-number/AUTO-MERGE-enabled output. For each PR print gh pr view -R ray-manaloto/dotfiles <number> --json number,url,baseRefName,headRefName,headRefOid,files,state,autoMergeRequest and its pin diff. If any image bumps survive, a distinct image PR must contain them and their required companion locks, including applicable changes to .config/mise/conf.d/shared.toml, .devcontainer/mise-system.lock and .devcontainer/mise-runtime.lock; the other PR must contain none of those image-input changes. Print complete PR file lists and verified pin-to-PR assignments, with no mixed or omitted retained bumps. If none survive, print the inventory establishing that fact. Each PR must show autoMergeRequest non-null or state MERGED; report pending CI as pending, never as merged. File existence, issue references or prose without the specified output cannot satisfy this goal.

Note: codex flagged that the local `/goal` docs mention a **4,000-character
limit** on the goal string; this revised paragraph should be checked against
that limit before pasting (it is long — count it before use).

## What could not be verified

- This session did not independently run `mise run ship` end-to-end against
  #1053 to reproduce the gate-blocking behavior; the verdict rests on reading
  `pr.py`'s gate-construction and control-flow code (`pr.py:324`, `:370`,
  `:581`), not on a live reproduction. Codex explicitly noted the same
  limitation: "I verified this gate logic; I did not reproduce the supplied
  runtime failure during this read-only review."
- The codex call succeeded (rc=0, 10,967-byte `-o` file, all cited
  `file:line` references checked against this session's own reads and found
  accurate). No codex-call failure to report.
- Codex noted the working tree was not completely clean at review time (an
  untracked `docs/research/kb/reports/agents/adv-goal-revision-2026-09-14.md`
  — this very report file, created before the consult per the persist-first
  protocol); codex made no edits, consistent with the read-only sandbox.
- The revised goal text's exact character count against the "4,000-character
  limit" codex flagged was not independently measured by this session.
- Graphify was STALE at review time (graph built at `5f965097`, HEAD
  `3744cea9`, 1 commit behind) — per `graphify-first.md` this was treated as
  unavailable and all evidence above came from direct file reads and the
  codex read-only sandbox, not from graph queries.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  subject repo; read `mise.toml`, `python/src/dotfiles_setup/main.py`,
  `dependency_currency.py`, `pr.py`, several `.claude/rules/*.md` files, and
  queried issue #1053 via `gh issue view`.
