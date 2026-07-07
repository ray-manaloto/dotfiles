---
name: devcontainer-sync
description: Converge the local devcontainer onto the latest CI-built image and verify it, via `mise run sync`. Use after a merge to main (promote retags :dev), when unsure whether the local container/base is current, or to pre-validate a PR image with --tag pr-NNN. Also carries the wiring audit checklist for the sync workflow itself.
user-invocable: true
---

# Devcontainer Sync

`mise run sync` is the one entrypoint for "make my devcontainer run the
newest image `ci.yml` published and prove everything works". Logic lives
in `python/src/dotfiles_setup/sync.py` (zero-bash-logic); the mise task
is a thin caller of `dotfiles-setup docker sync`.

## When to run

- After a PR merges to `main` (the `promote` job retagged registry `:dev`).
- After any `ci.yml` run that published new image bytes.
- When unsure whether the local container or its base is current.
- Pre-merge validation of a PR image: `mise run sync -- --tag pr-NNN`.

## Commands

```bash
mise run sync                     # observe → converge → smoke-verify
mise run sync -- --check          # dry-run staleness report (rc 1 if stale)
mise run sync -- --full           # verify-local chain (R1/R2/R3, persistence, secrets)
mise run sync -- --tag pr-169     # sync/validate against a PR image
mise run sync -- --force          # rebuild even when digests match
mise run sync -- --wait           # await an in-flight ci.yml run first
```

## What it does (action matrix)

Staleness = the **local docker tag's** digest differs from the registry
manifest digest (`docker buildx imagetools inspect`, no pull). Comparing
the local *tag* matters: after PR #169's promote, registry `:dev` moved
while the local `:dev` tag silently kept the pre-merge digest.

| stale? | container | action |
|---|---|---|
| yes (or `--force`) | any | buildkit tag refresh + `dev-rebuild` |
| no | running | verify only (digest fast-path) |
| no | stopped/absent | `mise run up` |

Then the verification gate: default = `verify_latest` (bind-mount
currency + smoke tiers 1-3, incl. tier-1 image-identity base-currency);
`--full` = the whole `mise run verify-local` chain.

## Interpreting failures

| Output | Meaning | Next step |
|---|---|---|
| `registry: UNREACHABLE` warning | Network/auth to ghcr.io failed; staleness unknown | Check `docker login ghcr.io` state, DNS (`dscacheutil -q host -a name ghcr.io`); sync continues against the local tag only — do NOT treat a green run as base-currency evidence |
| `NOTE ci.yml run … in progress` | The target image may be superseded shortly | Fine to continue for a devloop; rerun sync (or use `--wait`) after the run completes |
| `FAIL converge: buildkit tag refresh failed` | `docker buildx build --pull` could not fetch the manifest | Registry auth/manifest issue; never fall back to classic `docker pull` (wedges on the ~38GB image) |
| `FAIL converge: dev-rebuild rc=…` | Lifecycle rebuild failed | Read the streamed devcontainer-cli output; `getaddrinfo ENOTFOUND ghcr.io` = transient DNS, retry once per `.claude/rules/persistence-gate-retry.md` |
| `FAIL smoke-tiers-1-3 … stale base?` | Tier-1 image identity: in-image config hash ≠ repo `mise-system.toml` | The registry image predates your branch's `mise-system.toml` — wait for CI to publish, then rerun sync |
| `WARN rebuilding: in-container sessions will be killed` | Expected on stale+running | Workspace bind-mount and home volume persist; running shells die by design |
| rc 1 from `--check` | Stale — a real sync would rebuild | Run `mise run sync` when ready for the rebuild |

Evidence discipline: trust the printed `PASS`/`FAIL` lines and the task's
exit code read from a file/API — never a piped tail
(`.claude/rules/verify-before-advancing.md`).

## Wiring audit (meta-validation)

Machine-enforced by the `workflow.sync-wiring` contract in
`python/verification/suites.toml` (`dotfiles-setup verify run`). When
auditing by hand, confirm:

1. `mise.toml` has `[tasks.sync]` delegating to `dotfiles-setup docker sync`
   (zero-bash-logic: no orchestration in the task body).
2. `python/src/dotfiles_setup/sync.py` exists and `main.py` wires the
   `docker sync` subparser (`--tag/--force/--check/--full/--wait`).
3. `tests/test_sync.py` passes:
   `uv run --project python pytest tests/test_sync.py -x -q`.
4. Staleness compares the LOCAL TAG digest to the registry digest
   (`local_digest` matches the repo of the ref, not bake-stage aliases).
5. No classic `docker pull` anywhere in the sync path (buildkit only).
6. Long operations stream (never captured into a pipe); quick probes are
   timeout-bounded.

## See also

- `.claude/skills/devcontainer-workflow/SKILL.md` — up/down/smoke basics.
- `.claude/rules/verify-before-advancing.md` — when a synced container is
  a valid validation environment.
- `.claude/rules/persistence-gate-retry.md` — transient-DNS retry heuristic.
