# codex-advisor — verdict on clearing bot PRs #901/#947/#821 and the lock-drift class defect

Status: IN PROGRESS — verifying brief claims against code before consulting codex.

## Scope

Advisory only, per codex-advisor protocol. Reasoning for the verdict runs on
`gpt-5.6-sol` via `codex exec --sandbox read-only`, xhigh effort. This file is
being updated incrementally as evidence is gathered and as the codex verdict
returns.

## Premise verification against actual code/CI (done before consulting codex)

### Brief claim: #821 root cause — CONFIRMED, file:line exact
- `tests/test_lock_coverage.py:197-207` (`test_root_lock_covers_host_config`) builds
  the expected tool set from `tomllib.loads(mise.toml).get("tools", {})` — TOP-LEVEL
  only. Verified: `python3 -c "import tomllib; ... 'node' in c['tools']"` → `False`,
  32 keys, no `node`.
- `mise.toml:876` `tools.node = "24"` lives inside `[tasks.renovate-dryrun]`
  (comment at `mise.toml:861-874` explains #251: Renovate 43.x needs node ^24,
  repo's default is node 26).
- `.github/actions/lock-refresh/action.yml:24-25` — the root-lock regen step is
  **literally `run: mise lock`**, bare, no scoping flags. This is the exact command
  the `lock-refresh` job (triggered by `refresh.yml`'s cron/dispatch — the same
  flow that authored PR #778 and now #821) runs.
- `git log -S'[[tools.node]]' -- mise.lock` — confirmed by the brief's own probe
  language; I did not re-run it but the surrounding facts (bare `mise lock`, task-
  scoped `tools.node`, test narrowness) are independently sufficient to explain
  the recurrence without needing to re-derive the git-log result.
- **Premise is solid: this is a real, reproducible class defect, not a one-off.**

### Brief claim: image-lock-pr "dies on its own drift assertion before reaching
its own refresh step" — PARTIALLY WRONG, mechanism corrected
Pulled two real CI runs for #947 (`33780649870`/job `100733190320`, and the
earlier-cited `33763936742`/job `100676857957`). Both show the **same** step
sequence and **both contradict the brief's specific framing**:

1. `Check image-lock drift (five node IDs only, never the whole file)` — step has
   `continue-on-error: true` (`refresh.yml`); its internal pytest fails (that's
   the reported drift), but the STEP conclusion is `success` so the job continues.
2. `Regenerate image locks` (`mise run lock-image -- --no-container`) — **runs to
   completion successfully**: log shows `✓ Pruned ... stale version entries`,
   `✓ Updated 277 platform entries`, `mise lock converged on pass 1/5`,
   `image-lock OK: ... coverage verified against HEAD`.
3. `Re-check image-lock drift after regeneration` — **5 passed** in both runs. The
   regen DID fix the drift it was designed to fix.
4. `Confirm the diff is confined to the two image locks` — **this is where the job
   actually fails**, both times: `git status --porcelain -- . ':!.devcontainer/mise-system.lock' ':!.devcontainer/mise-runtime.lock'`
   reports `M mise.lock` (repo-root lock) as an "unexpected" touched file, and the
   step exits 1 by design (`.github/workflows/refresh.yml` "Confirm the diff is
   confined" step, comment: this job must not inject a root-lock regen because
   #821 already made that recipe defective).

So the brief's HEADLINE claim ("dies on the very drift assertion... BEFORE
reaching its own refresh step") is **factually wrong as a description of what
happens in CI** — the refresh step runs and succeeds. The REAL failure is a
**guard tripping on an unintended side effect**: regenerating the two image locks
via `mise run lock-image -- --no-container` also perturbs the repo-ROOT
`mise.lock`, which the job's own safety guard (put there deliberately to avoid
running the #821-defective root-lock recipe inside this job) then refuses to let
through.

Root mechanism of *why* `mise run lock-image` touches root `mise.lock` is not
fully pinned down — I ruled out the most obvious candidate (Renovate's own commit
already legitimately updates root `mise.lock` for root-owned tool bumps, e.g.
`antigravity-cli` 1.1.24→1.1.25, confirmed via
`git diff origin/main origin/renovate/all -- mise.lock` showing exactly that
kind of entry) — the CI job further perturbs `mise.lock` BEYOND Renovate's own
commit, most likely because `mise run <task>` (unlike `mise install --locked`,
which the earlier `setup-mise`/drift-check steps correctly use) performs an
UNLOCKED implicit tool sync before running the task body, and something in that
sync (possibly conda/url_api metadata churn, possibly something entangled with
the #821 class defect) rewrites the root lock. **This residual mechanism is
UNVERIFIED** — flagging per the brief's own ask ("where you are uncertain, say
so and name the probe"). Probe that would settle it: on a Linux amd64 box/
devcontainer, `git stash -u -- mise.lock; git diff mise.lock` immediately after
`mise run lock-image -- --no-container` runs, isolated from any other step, to
see the literal diff mise produced.

**This changes the advisory answer to Q2**: the true root cause is NOT a
self-referential bootstrap of the drift test; it's a scope leak from a task
invocation into a file the job explicitly tries to keep off-limits — and that
scope leak may well BE downstream of the same `mise lock`-writes-more-than-
intended behavior that #821's class fix needs to address anyway. If the #821 fix
makes root-lock regeneration properly scoped (e.g. writing only true top-level
`[tools]` entries, or teaching the test/tooling about task-scoped tools
correctly), it plausibly ALSO stops `mise run lock-image` from touching
`mise.lock` as a side effect — worth testing empirically once #821 is fixed,
before assuming #947 needs a second, separate change.

### Brief claim: #901 only failure is the known non-blocking runner-validation leg — CONFIRMED
`gh pr checks 901` shows the only `fail` row is
`build-publish / smoke-test (linux/arm64/v8, arm64, ubuntu-26.04-arm, arm64-runner2604, validate, false, false)`,
everything else `pass`. Matches #676/#736 (documented non-blocking leg in
`AGENTS.md`).

### Brief claim: #947 failing checks (contract-preflight, image-lock-pr, ci-gate) — CONFIRMED
`gh pr checks 947`: `ci-gate fail`, `contract-preflight fail`, `image-lock-pr fail`,
everything else pass/skip — matches.

### #821 status — CONFIRMED BLOCKED
`gh pr checks 821`: `ci-gate fail`, `contract-preflight fail`; `image-lock-pr` is
`skipping` (its `if:` gate requires `head.ref` to start with `renovate/` — #821's
branch is `chore/lock-refresh`, so that job correctly never runs on it — this is
NOT a bug, just confirms #821's failure is purely the `test_root_lock_covers_host_config`
regression, isolated from the image-lock-pr mechanism above).

Next: dispatching to codex (gpt-5.6-sol, xhigh, read-only sandbox) for the DAG/
ordering verdict, informed by the above.

## codex-advisor verdict (gpt-5.6-sol, xhigh, read-only sandbox)

The `codex exec` call succeeded (background PID 34846, completed cleanly,
`-o` file populated, 131 lines / non-empty). Full verbatim verdict:

---

## Verdicts

### 1. #821: constrain the refresh recipe; keep the test narrow

Do not widen `test_root_lock_covers_host_config()` to include `[tasks.*].tools`.

Mise is behaving correctly: current `mise lock --help` explicitly says that a no-argument lock updates configured and task-specific tools. The mistake is using that whole-project operation for an artifact whose repository contract is narrower:

- Root `mise.lock` is defined as exactly top-level `[tools]` (test_lock_coverage.py:189).
- `node = "24"` is explicitly task-local (mise.toml:861).
- The refresh composite nevertheless runs a bare `mise lock` (action.yml:26).
- The repository already documents whole-file locking as destructive and scopes the supported interactive operation to named tools (mise.toml:1278).

The deciding risk is contract dilution: widening the test would bless task-local runtime shims as root/CI dependencies, conceal a known broad-write hazard, and still leave the macOS platform-loss problem unfixed.

Recommended class fix:

- Add a Python entry point such as `lock-root-refresh` that derives only top-level `[tools]`.
- Run one explicit `mise lock --bump <sorted-top-level-tools…>` operation.
- Preserve `--bump`: mise 2026.9.1 now says plain `mise lock` refreshes current metadata, while `--bump` advances fuzzy/`latest` selectors. The current workflow's "re-resolve latest pins" claim otherwise becomes false.
- Verify afterward that `mise.lock` contains exactly the normalized top-level set and retained platform coverage.
- Expose it as `[tasks.lock-root-refresh]`.
- Make the composite invoke `mise run --skip-tools lock-root-refresh`, preventing the task runner's own auto-install phase from entering the lock path.
- Leave the existing test's expected set unchanged. Update its stale diagnostic at lines 203-206 so it points to the new whole-root refresh task rather than the refusing bare `mise run lock`.

A contaminated seed containing `node` should fail loudly; the new recipe need not invent a TOML-pruning implementation. Ship from clean `main`, close/delete #821's contaminated branch, and let the next refresh start clean.

### 2. #947: related defect family, separate causal path

This is the same genus — mise resolving/writing outside the caller's intended artifact boundary — but not the same mechanism:

- #821 invokes bare `mise lock` explicitly.
- #947 invokes `mise run lock-image`; with `auto_install=true` (mise.toml:99), task preparation can update root locks before the Python image recipe executes.
- The Python recipe itself stages isolated files and collects only the two image locks (image_lock.py:420).
- The workflow correctly rejects the leaked root write (refresh.yml:368).

Therefore, replacing the refresh composite's bare root lock will not, by itself, fix #947. The image job needs its own scope control — likely:

```
mise run --skip-tools lock-image -- --no-container
```

Do not weaken the confine guard.

The decisive probe, from identical disposable Linux-x64 checkouts of #947, is:

1. Current command: reproduce `M mise.lock`.
2. `mise run --skip-tools …`: root `mise.lock` must remain byte-identical.
3. Direct `uv run --project python dotfiles-setup image-lock --no-container`: root must also remain unchanged.
4. Arms 2 and 3 must produce byte-identical image-lock diffs and pass the five image-lock node IDs.
5. An invalid image-lock argument can serve as an early-exit control: if the ordinary task invocation changes `mise.lock` before argparse fails while `--skip-tools` does not, the write is definitively task preparation rather than image regeneration.

A manual image-lock run remains useful for generating and validating #947's expected two image-lock changes. Use the candidate `--skip-tools` form in the probe. It cannot repair #821 or sanitize root `mise.lock`.

### 3. Local versus bot branches

Choose one own branch for the infrastructure fixes. Do not push code fixes to either bot branch.

Reasons:

- Duplicating the class fix across #821 and #947 creates immediate conflict/revert risk.
- A human/CI commit on `renovate/all` intentionally makes the branch modified, after which Renovate stops rebasing it.
- Own-branch work receives the complete `ship` gate; bot branches never do.
- Local tasks can regenerate derived locks, but `renovate-dryrun` only reports updates and does not reproduce hosted PR/branch behavior (renovate_dryrun.py:1). Let Renovate remain the source of dependency-edit commits.

After the fix lands:

- Close #821 and delete `chore/lock-refresh`; dispatch the fixed refresh workflow so it regenerates from clean `main`.
- Initially leave #947 open and unmodified. After the replacement refresh PR lands, let Renovate rebase/update it onto fixed `main`. Then `image-lock-pr` can add only the image locks and intentionally mark the branch modified.
- If #947 does not update after one Renovate cycle, close/delete it. This repository extends `group:all` (renovate.json:3); Renovate documents package groups as "immortal" under default `recreateWhen=auto`, so the grouped PR should be recreated. (Renovate `recreateWhen` documentation)

Context7 lookup failed in this sandbox, so that last point was verified against Renovate's official documentation directly.

## Explicit DAG

```
O901 ────────────────> L901 ───────────────────────────────┐
                                                           │
P821 ─┐                                                    │
P947 ─┼─> S0 -> PV0 -> C0 ─┬─> I821 -> R821 -> V821 ─┐    │
SDOC ─┘                     └─> I947 -> R947 -> V947 ─┼─> INT
                                                     │      │
                                                     └──────┘
INT -> RINT -> VINT -> GATE -> SHIP -> LAND
LAND -> CLOSE821 -> REFRESH821 -> LAND821 -> UPDATE947
UPDATE947 -> AUTOMEMERGE947 -> LAND947
```

| Node | Agent/executor | Depends on | Acceptable output |
|---|---|---|---|
| `O901` | Architect/operator | None | Run `mise run automerge -- 901`; auto-merge armed against the observed SHA. Independent of every lock lane. |
| `L901` | Architect/operator | `O901` merged | `mise run land -- 901` passes. |
| `P821` | Fresh `fable-orchestrator:codex-implementer`, xhigh, declared disposable probe | None | Real-write control reproduces task-node inclusion; explicit top-level `--bump` arm excludes `node`, preserves platforms, and proves fuzzy-pin advancement. No retained code. |
| `P947` | Different fresh `fable-orchestrator:codex-implementer`, xhigh, disposable #947 worktree | None | The five-arm probe above identifies whether `--skip-tools` fully prevents root mutation without changing image results. No retained code. |
| `SDOC` | `codex-staleness-auditor` | None | File:line inventory of prose/contracts requiring updates. Must notice `refresh.yml` actually has four jobs — `schema-refresh` starts at refresh.yml:467 — and require it to remain untouched. |
| `S0` | Architect | `P821`, `P947`, `SDOC` | Seven-part, fully pinned specs. Exact command, CLI/task names, owned files, tests and failure behavior resolved; no lane choices left open. |
| `PV0` | `fable-orchestrator:premise-verifier` | `S0` | Confirms artifact ownership, command semantics and probe provenance; every unresolved premise is returned to the architect before dispatch. |
| `C0` | `codex-adversarial-critic` | `PV0` | Proposal survives replay: it would have prevented #778/#821 and caused #947's confine check to pass without weakening either coverage test or guard. |
| `I821` | Fresh `fable-orchestrator:codex-implementer`, xhigh | `C0` | Owns only `lock_refresh.py`, `main.py`, `mise.toml`, the lock-refresh composite, `test_lock_refresh.py`, and root-refresh prose. Implements task -> Python, never bare lock. Runs all three gates. |
| `I947` | Different fresh `fable-orchestrator:codex-implementer`, xhigh | `C0` | Owns only `refresh.yml`, image-lock skill/docs, `test_image_lock.py`, and the relevant verification contract. Keeps confine guard intact and pins the proven no-auto-install invocation. Runs all three gates. |
| `R821`, `R947` | Two fresh `fable-orchestrator:codex-reviewer` agents, neither an author | Respective implementation | Complete immutable-ref review with file:line findings; no intent framing. |
| `V821`, `V947` | Two fresh `codex-advisor` agents, different from authors/reviewers | Respective review | Rechecks every finding/refutation against the commit and confirms every changed file was reviewed. This is review verification, not a replacement review. |
| `INT` | Fresh `fable-orchestrator:codex-implementer`, xhigh | `V821`, `V947`, `L901` | Serially integrates both reviewed commits onto one current-main branch. Any semantic conflict becomes a new reviewed implementation node. |
| `RINT` | Fresh `fable-orchestrator:codex-reviewer` | `INT` | Cold review of the combined immutable diff. |
| `VINT` | Fresh `codex-advisor` | `RINT` | Verifies combined review completeness and gives the ship/no-ship verdict. |
| `GATE` | Integration implementer | `VINT` | Captured exit 0 from `mise run lint`, `uv run --project python pytest tests/ -x -q`, and `mise run verify`. Any review correction creates a new acyclic implementation/review version and reruns all three. |
| `SHIP` | Architect/operator | `GATE` | `mise run ship`; no later push to that branch. |
| `LAND` | Architect/operator | Own PR merged | `mise run land -- <own-PR>` passes. |
| `CLOSE821` | Architect/operator | `LAND` | Close #821 and delete its branch so the contaminated `node` seed cannot be reused. |
| `REFRESH821` | Architect/operator/workflow | `CLOSE821` | Dispatch fixed `refresh.yml`; replacement PR contains only owned refresh artifacts and passes contract-preflight. |
| `LAND821` | Architect/operator | Replacement merged | Land replacement refresh PR. |
| `UPDATE947` | Renovate + existing workflow | `LAND821` | #947 is rebased/recreated from fixed main; image job changes only the two image locks; all required checks green. |
| `AUTOMERGE947` | Architect/operator | `UPDATE947` | `mise run automerge -- 947` or its recreated PR number. |
| `LAND947` | Architect/operator | Renovate PR merged | Post-merge `land` passes. |

The first wave — `O901`, `P821`, `P947`, and `SDOC` — is genuinely independent. `I821` and `I947` are parallel only with the ownership split above. They must not both touch `tests/test_lock_coverage.py`, `mise.toml`, `main.py`, or `python/verification/suites.toml`.

The replacement refresh and #947 are not independent: both can rewrite image locks. Serialize them, refresh first, then Renovate.

## PR order

1. Arm #901 immediately with `mise run automerge -- 901`. Its sole failure is the known non-required arm64 validation leg.
2. Probe, implement, review, verify and ship the one own class-fix PR.
3. Close/delete #821; run and land a clean replacement refresh PR.
4. Rebase/recreate #947 against that main; allow `image-lock-pr` to contribute only image locks; then arm and land it.
5. Never push again after `ship` arms the own branch.

★ Insight ─────────────────────────────────────
The durable boundary here is "one artifact, one owner, one explicit tool set." Mise's broader behavior is valid, but every automation caller must narrow it to the artifact it claims to maintain — and then independently prove no neighboring artifact moved.
─────────────────────────────────────────────────

No files were written and no mutating commands were run. Graphify health and query were attempted first, but the read-only sandbox prevented mise from creating its required temp/log state, so direct source reading was used as the fallback authority.

---

## My spot-check of codex's own citations (before relaying)

- `mise.toml:99` `auto_install = true` under `[settings]` — CONFIRMED exact.
- `mise lock --help` — CONFIRMED verbatim: "If no lockfile exists, shows what
  would be created based on the current configuration, including tools
  declared by tasks" and "If not specified, all configured and task-specific
  tools will be updated" — this directly substantiates codex's central claim
  that mise's bare-`mise lock` behavior (locking task-scoped tools too) is
  DOCUMENTED, intentional behavior, not a bug — strengthening its "constrain
  the caller, not the test" verdict.
- `mise lock --bump` and `mise run --skip-tools` — CONFIRMED both flags exist
  and behave as codex describes (`mise lock --help`, `mise run --help`).
- `.github/workflows/refresh.yml:368` — matches (the "Confirm the diff is
  confined to the two image locks" step's guard block starts right around
  there).
- Did not independently re-verify `image_lock.py:420` or `renovate_dryrun.py:1`
  line-exactness (time-boxed) — worth a second look before an implementer
  lane depends on the exact line number, though the substance (image_lock.py
  stages/collects only the two image locks; renovate-dryrun is report-only)
  matches what I independently read earlier in `lock_refresh.py`'s docstring
  and `mise.toml`'s task table.

Codex's verdict is well-grounded and its central claim — that a bare
`mise lock` locking task-scoped tools is DOCUMENTED mise behavior, so the
fix belongs in the CALLER (the refresh composite / lock-image invocation),
not in loosening `test_root_lock_covers_host_config`'s contract — is now
independently confirmed by the `mise lock --help` text itself. This also
sharpens my own earlier finding: the residual #947 "M mise.lock" side effect
is plausibly explained by `auto_install = true` (mise.toml:99) making `mise
run lock-image` implicitly re-resolve/write the root lock during its
pre-task tool-prep phase — exactly what `--skip-tools` is designed to
suppress. I had not located `auto_install = true` myself; this is a genuine
addition from the codex pass, not just corroboration.

## Advisor's own bottom-line assessment

1. **#821 class fix**: Agree with codex — scope the CALLER, not the test.
   Concretely this likely means a new `lock-root-refresh` Python entrypoint +
   mise task that runs `mise lock --bump <explicit top-level tool list>`
   instead of a bare `mise lock`, and the composite invoking it with
   `--skip-tools` to avoid the same auto_install leak that appears to affect
   #947.
2. **image-lock-pr bootstrapping**: The brief's original framing (dies on its
   own drift assertion before reaching its refresh step) is WRONG — I
   confirmed this from two real CI runs. Codex's refined framing (an
   `auto_install=true`-driven scope leak from `mise run lock-image`'s
   pre-task tool-prep phase, not from the Python image-lock recipe itself)
   is plausible and testable, but UNVERIFIED — neither codex nor I ran the
   `--skip-tools` control experiment. Do not treat it as settled; run codex's
   5-arm probe (node `P947` in the DAG) before committing to that fix shape.
3. **Local vs bot branch**: Agree — one own branch for the class fix,
   fixed via `ship`, never push code fixes onto `renovate/all` or
   `chore/lock-refresh`. Close/recreate the bot PRs after the fix lands
   rather than patching them directly.
4. **DAG**: Sound structure, correctly separates truly-independent first-wave
   probes/audits from the serialized spec -> premise-verify -> adversarial
   review -> implement -> review -> verify -> integrate chain, and correctly
   flags the `tests/test_lock_coverage.py` / `mise.toml` collision risk
   between `I821` and `I947`. One caveat: the DAG's ASCII diagram (lines
   77-87 of the verdict) is somewhat garbled/hard to parse mechanically —
   the TABLE (which is unambiguous) should be treated as authoritative over
   the ASCII art if an implementer needs to script the dependency graph.
5. **PR ordering**: Agree — arm #901 immediately and independently (it has
   no relation to the lock machinery); do the class fix on its own branch
   next; close/replace #821; let #947 rebase onto the fix or get
   recreated by Renovate's `group:all` + `recreateWhen=auto`.

## What I could not verify

- The exact mechanism causing `mise run lock-image -- --no-container` to
  perturb root `mise.lock` in CI (codex's `auto_install=true` explanation is
  plausible and grounded in a real, confirmed setting, but neither of us ran
  the actual control experiment — this is squarely what DAG nodes `P821`/
  `P947` exist to settle before any implementation is written).
- `image_lock.py:420` and `renovate_dryrun.py:1` exact line citations from
  codex (time-boxed; substance corroborated, exact lines not re-checked).
- Whether Renovate's `recreateWhen=auto` / group immortality claim (codex's
  #3 answer, citing Renovate docs) holds for this repo's exact `renovate.json`
  config — I did not independently fetch Renovate's docs to confirm; codex
  reports it read them directly after a context7 lookup failure in its
  sandbox.
- The `codex exec` call's read-only sandbox could not run `mise run
  graphify-health`/`graphify-query` (noted explicitly in its own output) —
  its file:line citations therefore come from direct source reads, not a
  graph query, consistent with `graphify-first.md`'s fallback guidance.

## GitHub repos touched

_None._ All research was against this repo's own source and its own CI run
logs (`gh run view`, `gh pr checks`); no external repo's source or docs were
read directly (the advisor sub-call reports it consulted Renovate's own
documentation site for the `recreateWhen` claim, but I did not independently
fetch that site myself).
