---
name: pr-workflow
description: Ship, automerge and land PRs via `mise run ship` / `mise run automerge -- <PR#>` / `mise run land -- <PR#>` — the full gated loop from committed work to merged-and-locally-validated main. Use whenever committing work that should become a PR, when asked to merge a green PR, when a bot-opened PR (Renovate / the refresh bot / a dependency bump) needs merging, or when validating that the ship/land wiring is intact. Never hand-roll commit→push→PR→merge sequences.
user-invocable: true
---

# PR Workflow: ship / automerge / land

The full PR loop lives in `python/src/dotfiles_setup/pr.py`
(zero-bash-logic); `mise run ship`, `mise run automerge` and `mise run land`
are thin callers. These tasks ARE the canonical workflow — do not hand-roll
`git push` + `gh pr create` + `gh pr merge` sequences when they apply
(mise-tasks-only policy).

**One verb per PR provenance.** Merging is *armed*, never performed by hand:
`ship` arms your own branch (after gating it), `automerge` arms a **bot-opened**
PR (which never runs ship), and `land` is the post-merge validation for either.
Picking between them is a lookup, not a judgement call.

## Commands

```bash
mise run ship                      # gates → push → PR open/update → enable native auto-merge, return
mise run ship -- --title "..."     # override the PR title (default: gh --fill)
mise run automerge -- <PR#>        # BOT PR only: arm native auto-merge and exit (no local gates)
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

## What automerge does (#369)

`mise run automerge -- <PR#>` is the missing verb for a **bot-opened** PR. Only
ship armed auto-merge, and a bot PR never runs ship; `land` refuses an OPEN PR;
`gh pr merge` is guard-denied. So #138, #236 and #386 sat green with no
sanctioned way to merge — *a guard whose redirect target cannot perform the
redirected action is not enforcement, it is an outage.*

1. Reads `state`, `author`, `isDraft`, `baseRefName`, `headRefOid` and refuses
   unless the PR is **OPEN**, **non-draft**, **main-based**, and authored by one
   of `BOT_PR_AUTHORS` (`app/renovate`, `app/dotfiles-refresh-bot-org`). A
   **human PR is refused** and pointed at `ship`: ship gates the tree before
   arming and automerge does not, so the split keeps that from being a call the
   operator has to make.
2. Arms through the **same** `enable_auto_merge` ship uses — squash,
   `--delete-branch`, pinned with `--match-head-commit` to the head SHA it just
   read — then **prints the `land` follow-up and exits**. It does not wait:
   waiting would turn a seconds-long verb into a 20-40min Mac-side op that gets
   reaped when the turn goes idle.
3. **Staleness is deliberately not checked.** Renovate branches sit behind main,
   but `ci-gate` and the other required checks run against the **merge result**
   and auto-merge waits for them. A local freshness gate would be a second,
   weaker opinion about a question GitHub has already answered (and pushes
   against #257, rebase churn).

Per-PR by construction — nothing is armed unless it is named, which is what
keeps a deliberately HELD bot PR (e.g. #386) held.

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

The **merge approval is enabling auto-merge at ship** (`main` requires
`ci-gate` and no review); GitHub merges when green. `--match-head-commit`
scopes it to the SHA the local gates validated.

**A PR is now mandatory, server-side** (#400, 2026-07-27): the repository
ruleset `main: require a pull request` is active with **0 required approvals
and no bypass actors**, so a direct push to `main` is refused by GitHub — the
one layer an agent cannot skip. It costs these verbs nothing, because all three
already go through a PR; verified end-to-end when PR #401 armed auto-merge under
the active ruleset and squash-merged itself 181s after `ci-gate` went green,
with `reviewDecision` empty throughout. If a future ruleset change ever demanded
an approval, `ship` and `automerge` would arm and then sit — that is the
symptom to look for, and the fix is the ruleset, not the verb.

## Failure modes

| Output | Meaning | Next step |
|---|---|---|
| `ship: refusing to ship from main` | On main/detached HEAD | Create a feature branch first |
| `ship: working tree not clean` | Uncommitted changes | Commit (or stash) so gates validate the shipped tree |
| `FAIL gate <name>` | A local gate failed | That failure IS the task (zero-skip); fix, rerun ship |
| `ship: could not enable auto-merge` | The 422 regression outlasted the bounded retry, or "Allow auto-merge"/`ci-gate` isn't configured | Check the repo's auto-merge setting + branch protection; re-run `ship` (it reuses the PR) |
| `land: PR #N is OPEN, not yet MERGED` | Auto-merge is still pending `ci-gate` (CI running). **Expected right after ship — not a failure**, though `land` does exit non-zero | Wait for the merge, then re-run `land` for the post-merge Mac validation. `land` has no `--wait` and `gh pr checks --watch` is guard-denied, so poll the blessed one-shot read, keeping the turn engaged: `until [ "$(gh pr view <N> --json state --jq .state)" = MERGED ]; do sleep 60; done` |
| CI check failed (PR never auto-merges) | A required check went red, so auto-merge never fires | Triage the run; autofix "✅ Autofix task started" means the bot pushed a fix → new checks run → auto-merges when green |
| **ship reports OK, but no CI run ever starts and the PR sits** | `mergeStateStatus=DIRTY` — the branch conflicts with main. Happens when a branch is **reused after its earlier PR was squash-merged**: main holds the squash, the branch still holds the originals, so a file created on both sides conflicts. **ship does not catch this** — it gates the local tree and the PR creation, not the resulting mergeability | `gh pr view <N> --json mergeStateStatus`. Fix by replaying only the new commits: `git rebase --onto origin/main <last-already-merged-sha>` then `git push --force-with-lease`. Verify first that main really carries the old content (compare the file blob's `md5`), or the rebase drops work. DIRTY → BLOCKED means fixed |
| land failed AFTER the merge (CI watch / sync) | Merged-but-unvalidated PR | `mise run land -- <PR#> --resume` replays the idempotent post-merge steps |
| `land: no main ci.yml run appeared` | A merge that SHOULD trigger a run didn't register (~10 min) | Check Actions; land only expects a run when the diff matches `CI_PUSH_PATHS` (ci.yml on.push.paths) — a merge matching none passes without one (#179) |
| `automerge: PR #N was opened by '<login>', which is not one of the bots…` | A human/ship-able PR (or a bot not on the allowlist) | Use `mise run ship` from the branch — it gates the tree before arming. Adding a bot means editing `BOT_PR_AUTHORS` + its test, deliberately |
| `automerge: PR #N is MERGED, not OPEN` | Already merged (auto-merge fired, or it was hand-merged) | `mise run land -- <PR#>` for the post-merge Mac validation |
| `automerge: could not enable auto-merge` | Same 422 regression / auto-merge-not-configured cause as ship's | Check the repo's auto-merge setting + branch protection, then re-run; if the bot force-pushed a rebase since, re-run anyway (the arming is pinned to the SHA it read) |

## Wiring audit (meta-validation)

Machine-enforced by `workflow.ship-land-wiring` and
`workflow.automerge-wiring` in `python/verification/suites.toml`. By hand:
`[tasks.ship]`/`[tasks.automerge]`/`[tasks.land]` delegate to
`dotfiles-setup pr ...`; `tests/test_pr.py` passes; the surface list in `pr.py`
covers every path class whose change demands full local verification (extend it
when new validation code lands).

## See also

- `.claude/skills/devcontainer-sync/SKILL.md` — the sync workflow land calls.
- `.claude/rules/verify-before-advancing.md` — the check matrix ship encodes.
- `.claude/rules/gh-cli-watch.md` — why buckets, never watch exit codes.
