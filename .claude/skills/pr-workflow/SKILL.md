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
mise run ship                      # gates → push → PR open/update → watch checks
mise run ship -- --title "..."     # override the PR title (default: gh --fill)
mise run land -- <PR#>             # verify green → pinned squash-merge → main CI → local sync
```

## What ship does

1. **Preflight**: refuses `main`/detached HEAD and dirty trees (commit
   first — the gates must validate exactly what ships).
2. **Path-aware gate matrix, cheap-first** (from
   `.claude/rules/verify-before-advancing.md`): `mise run lint` →
   pytest → `dotfiles-setup verify run`; + `pin-actions` when `.github/**`
   changed; + `lint-docs` when agent docs changed; + **`mise run sync --
   --full` (hard gate, no override)** when the diff touches the
   devcontainer/image/validation surface (`SURFACE_PATTERNS` in pr.py:
   `.devcontainer/**`, `docker-bake.hcl`, smoke/workspace scripts,
   `container.py`/`sync.py`/`image.py`/`docker.py`/`pr.py`,
   `python/verification/*`).
   The full-sync gate's smoke tier-1 base-currency (config-hash AND
   tool-set) validates against the **merge-base** for a branch that
   changed an image build input — the local base can't be built from the
   branch (its base is built by that branch's own PR CI), so branch-config
   validation defers to CI. Without this, an image-input bump deadlocks the
   gate (#179/#180).
3. Push, open (or reuse) the PR, wait for the **`ci-gate` aggregator to
   register** (it `needs` every job), then `gh pr checks --watch
   --fail-fast`, then **verify via `--json` buckets** — green means every
   check `pass`/`skipping`. The ci-gate wait stops a build PR being called
   green on an early check wave before build-publish's matrix jobs register
   (#181); a watch exit code alone is never trusted.

## What land does

1. Verifies the PR is OPEN and every check bucket is green (API, not
   watch exit codes).
2. **Pinned merge**: `gh pr merge --squash --delete-branch
   --match-head-commit VERIFIED_SHA` — GitHub refuses if the branch
   moved after verification (closes the verify-then-merge race).
3. Watches the main `ci.yml` run for the merge commit; conclusion must
   be `success` via `gh run view --json conclusion`.
4. Fast-forwards local main, then **local validation on this Mac**:
   `sync` (digest fast-path); full `verify-local` tier automatically
   when the PR touched the devcontainer surface.

Invoking `land` IS the merge approval — nothing auto-merges without it.

## Failure modes

| Output | Meaning | Next step |
|---|---|---|
| `ship: refusing to ship from main` | On main/detached HEAD | Create a feature branch first |
| `ship: working tree not clean` | Uncommitted changes | Commit (or stash) so gates validate the shipped tree |
| `FAIL gate <name>` | A local gate failed | That failure IS the task (zero-skip); fix, rerun ship |
| `pr-checks: <name>=fail` | CI check failed after watch | Triage the run; autofix "✅ Autofix task started" failures mean the bot pushed a fix commit — re-watch |
| `land: merge refused` | Head moved since verification / protection unmet | Re-run land (it re-verifies) |
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
