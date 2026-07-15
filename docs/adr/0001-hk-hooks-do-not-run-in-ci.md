# ADR-0001 — hk git hooks must not run in CI

**Status:** accepted · **Date:** 2026-07-15 · **PRs:** #274 (wrong), #275 (correct)

## Context

`mise.toml`'s `[hooks] postinstall = "mise reshim && hk install --mise"` runs on **every**
`mise install` — including on GitHub Actions runners. `hk install` writes three git hooks:
`commit-msg`, `pre-commit`, `pre-push`.

Any CI job that then commits or pushes fires them. `refresh.yml`'s lock-refresh job does both (via
`peter-evans/create-pull-request`), so hk ran its full step set on the runner, including two steps
that **cannot** pass there:

- `ghcr_publish_prereqs` (`hk.pkl:440`) → `GhcrCheckError: You are not logged into any GitHub hosts`
- `test` (`hk.pkl:444`) → `test_tool_reachable_in_login_shell[claude]`: `claude` is not on a
  runner's login-shell PATH

**Consequence:** the daily lockfile refresh failed 2026-07-14 and 2026-07-15, and **no lock-refresh
PR had ever opened** in the workflow's lifetime (`gh pr list --label lockfile` → `[]`).

**Why it hid for six days:** the failing step is conditional — *"Open PR **if any lock drifted**"*.
No drift ⇒ no commit ⇒ no hook ⇒ green. The bug only fires when the workflow has real work to do.
`gcc-sha-repair.yml` is exposed identically but stayed latent for two independent reasons: it exits
early when there's nothing to repair, and its `install_args: "python uv"` omits hk, so the
postinstall fails (warn-only) and no hook is written.

## Decision

**Skip the hooks; don't satisfy them.** `HK_SKIP_HOOKS: pre-commit,pre-push` at job level in every
workflow that commits or pushes (`refresh.yml`, `gcc-sha-repair.yml`).

CI runs its own lint job (`ci.yml`). A commit-time hook on a runner is an accident of tool
installation, not a gate anyone designed. Skipping it removes nothing that CI doesn't already do.

`skip_hooks` is hk's **native** mechanism (`HK_SKIP_HOOKS` / `hk.skipHook`: *"Hook names to skip
entirely. Values from all sources are unioned together."*), so this needs no custom code —
`use-tool-builtins.md`. hk has **no CI self-detection** (grepped the docs cache and all 100 releases
v0.7.0→v1.51.0: zero hits), so the skip must be explicit.

## Alternatives rejected

| Option | Why not |
|---|---|
| **Gate the postinstall** so `hk install` skips CI | Attacks the root cause, but `postinstall` also runs `mise reshim`, which CI genuinely needs (added for a real pipx shim bug — `mise.toml:64-65`), and mise documents no env-conditional postinstall ⇒ shell logic in `mise.toml`, against `zero-bash-logic.md`. |
| **hk `profiles`** — mark the two steps as local-only | Elegant, and `profiles` is a feature we don't use. But it changes step semantics everywhere, risking `ci-local-parity.md`. |
| **Make the two steps pass on a runner** | Biggest change, and wrong: a full pytest run has no business inside a lockfile-bump commit hook. |

## Consequences

- Any **new** workflow that commits or pushes must set `HK_SKIP_HOOKS` too. There is no global
  guard — the two known cases are fixed by name.
- Correctness now depends on remembering. A contract asserting "every workflow that commits sets
  `HK_SKIP_HOOKS`" would give this teeth; not written yet.
- `commit-msg` is deliberately **not** skipped: `check_conventional_commit` passes on the bots'
  messages and is cheap. Add it if that changes.

## The lesson worth keeping

**#274 set `HK_SKIP_HOOKS: pre-commit` and was merged with every gate green** — lint, 618 tests,
contracts, ship's five gates, `land`'s full container validation. **It was still broken.** The
failing steps are `pre-push`'s (`hk.pkl:438`), and `create-pull-request` pushes as well as commits.
#274 cited `hk.pkl:440`/`:444` while calling them pre-commit steps; the evidence never said which
hook.

Nothing we run could have caught it, because the interesting path is conditional and no gate
exercises it. **Only dispatching the workflow at real drift proved it** — which then also proved
#275:

```
hk WARN  pre-commit: skipping hook due to HK_SKIP_HOOK
hk WARN  pre-push:   skipping hook due to HK_SKIP_HOOK
→ PR #276 — the first lock-refresh PR that has ever existed
```

Corollary, learned the same hour: the first re-probe of the fix **passed for the wrong reason** —
its control arm showed the hook never fired at all (hk errors resolving `origin/HEAD` against a bare
remote). A probe without a control arm is not evidence.
