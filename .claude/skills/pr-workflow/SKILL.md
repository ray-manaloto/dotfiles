---
name: pr-workflow
description: Ship and land PRs via `mise run ship` / `mise run land` — the full gated loop from committed work to merged-and-locally-validated main. Use whenever committing work that should become a PR, when asked to merge a green PR, or when validating that the ship/land wiring is intact. Never hand-roll commit→push→PR→merge sequences.
user-invocable: true
---

# PR Workflow: ship / land

The full PR loop lives in `python/src/dotfiles_setup/pr.py`
(zero-bash-logic); `mise run ship` and `mise run land` are thin callers.
These tasks ARE the canonical workflow — do not hand-roll
`git push` + `gh pr create` + `gh pr merge` sequences when they apply
(mise-tasks-only policy).

## Commands

```bash
mise run ship                      # gates → push → PR open/update → enable native auto-merge, return
mise run ship -- --title "..."     # override the PR title (default: gh --fill)
mise run land -- <PR#>             # (after it auto-merges) confirm merged → main CI → local verify
```

## What ship does

1. **Preflight**: refuses `main`/detached HEAD and dirty trees (commit
   first — the gates must validate exactly what ships).
2. **Path-aware gate matrix, cheap-first** (from
   `.claude/rules/verify-before-advancing.md`): `mise run lint` →
   pytest → `dotfiles-setup verify run` → `hook-selfcheck` (always-run:
   drives the wired host-side hooks end-to-end — see
   `.claude/rules/mise-tasks-only.md`); + `pin-actions` when `.github/**`
   changed; + `lint-docs` when agent docs changed; + **`mise run sync --
   --full` (hard gate, no override)** when the diff touches the
   devcontainer/image/validation surface (`SURFACE_PATTERNS` in pr.py:
   `.devcontainer/**`, `docker-bake.hcl`, smoke/workspace scripts,
   `container.py`/`sync.py`/`image.py`/`docker.py`/`pr.py`,
   `python/verification/*`).
   **Base-image input changes DEFER the container gate to CI**
   (`BASE_INPUT_PATTERNS` — the mise-system/runtime toml+lock, `shared.toml`,
   the shared `hk` pkl fragments, `Dockerfile`, `docker-bake.hcl`): the new base is
   built ONLY by the PR's own CI, so the local `:dev` base can't validate it
   (a chezmoi/gcc bump can even make the stale base's `onCreate` fail). ship
   runs lint/pytest/verify locally, skips the impossible local convergence,
   and gates on CI's base-build + smoke instead. Non-base surface changes
   (`sync.py`/`pr.py`/`container.py`, smoke script, `devcontainer.json`)
   still run the full local sync gate.
3. Push, open (or reuse) the PR, **enable GitHub-native auto-merge, and
   return** — `gh pr merge --auto --squash --match-head-commit HEAD`
   (`enable_auto_merge`). GitHub then merges the PR **server-side** the
   instant the required `ci-gate` check goes green — no client poll, no
   timeout, tolerant of multi-hour base builds (a fixed-timeout or
   hand-rolled watch was the wrong shape). `--match-head-commit` pins the
   gated SHA and GitHub auto-disables auto-merge on new pushes, closing the
   verify-then-merge race. A short bounded retry covers the transient
   March-2026 422 enable regression. ship prints the `mise run land`
   follow-up for post-merge Mac validation.

## What land does

land is the **post-merge validation** step (ship's auto-merge does the merge):

1. Confirms the PR is **MERGED** + main-based. If still OPEN, auto-merge is
   pending `ci-gate` — land says so and exits (re-run once it has merged).
2. Verifies the main `ci.yml` run for the merge commit concluded `success`
   (`gh run view --json conclusion`), path-aware per `CI_PUSH_PATHS` (#178).
3. Fast-forwards local main, then **local validation on this Mac**:
   `sync` (digest fast-path); full `verify-local` tier automatically when
   the PR touched the devcontainer surface — the arm64 R1/R2/R3 checks that
   can't run in CI. `land` is idempotent (safe to re-run); the `--resume`
   flag is accepted for compatibility but has no separate effect.

The **merge approval is enabling auto-merge at ship** (`main` requires only
`ci-gate`, no review); GitHub merges when green. `--match-head-commit`
scopes it to the SHA the local gates validated.

## Failure modes

| Output | Meaning | Next step |
|---|---|---|
| `ship: refusing to ship from main` | On main/detached HEAD | Create a feature branch first |
| `ship: working tree not clean` | Uncommitted changes | Commit (or stash) so gates validate the shipped tree |
| `FAIL gate <name>` | A local gate failed | That failure IS the task (zero-skip); fix, rerun ship |
| `ship: could not enable auto-merge` | The 422 regression outlasted the bounded retry, or "Allow auto-merge"/`ci-gate` isn't configured | Check the repo's auto-merge setting + branch protection; re-run `ship` (it reuses the PR) |
| `land: PR #N is OPEN, not yet MERGED` | Auto-merge is still pending `ci-gate` (CI running). **Expected right after ship — not a failure**, though `land` does exit non-zero | Wait for the merge, then re-run `land` for the post-merge Mac validation. `land` has no `--wait` and `gh pr checks --watch` is guard-denied, so poll the blessed one-shot read, keeping the turn engaged: `until [ "$(gh pr view <N> --json state --jq .state)" = MERGED ]; do sleep 60; done` |
| CI check failed (PR never auto-merges) | A required check went red, so auto-merge never fires | Triage the run; autofix "✅ Autofix task started" means the bot pushed a fix → new checks run → auto-merges when green |
| land failed AFTER the merge (CI watch / sync) | Merged-but-unvalidated PR | `mise run land -- <PR#> --resume` replays the idempotent post-merge steps |
| `land: no main ci.yml run appeared` | A merge that SHOULD trigger a run didn't register (~10 min) | Check Actions; land only expects a run when the diff matches `CI_PUSH_PATHS` (ci.yml on.push.paths) — a merge matching none passes without one (#179) |

## Wiring audit (meta-validation)

Machine-enforced by `workflow.ship-land-wiring` in
`python/verification/suites.toml`. By hand: `[tasks.ship]`/`[tasks.land]`
delegate to `dotfiles-setup pr ...`; `tests/test_pr.py` passes; the
surface list in `pr.py` covers every path class whose change demands
full local verification (extend it when new validation code lands).

## See also

- `.claude/skills/devcontainer-sync/SKILL.md` — the sync workflow land calls.
- `.claude/rules/verify-before-advancing.md` — the check matrix ship encodes.
- `.claude/rules/gh-cli-watch.md` — why buckets, never watch exit codes.
