# hk v2 global git hooks: is the global install wrong, or should our setup adapt? (2026-09-27)

Question (Ray, 2026-09-27): do due diligence and cited research before claiming the global/user-level change is wrong, as opposed to us needing to support newer dependency behaviour and global/user-level changes.

This corrects the framing in `hk-v2-migration-research-2026-09-27.md` § Q3 "Verdict" and in #1397 item 1. Those called the global install "the real problem" or "not a fit" before reading *why* upstream designed it that way.

## Answer

**The global install is not wrong. It is hk's documented, recommended v2 setup, and our setup is what needs to adapt.** Every failure we hit traces to one of three things on our side, not to the global hooks themselves:

1. **A stale environment variable.** `HK_PKL_BACKEND=pkl` was inherited by this long-lived session. hk v2 refuses it. The same commit passes with it unset (rc=1 → rc=0, measured).
2. **Our postinstall recipe.** Upstream removed `postinstall = "hk install --mise"` from its mise integration docs, because it mutates `.git/config` during mise tool installs and races under concurrent or lazy evaluation. Our `mise.toml:180` still uses it.
3. **Our pytest git fixtures are not isolated from global git config.** Git documents `GIT_CONFIG_GLOBAL=/dev/null` for exactly this, and this repo already does it in one test.

The local-hook deletion that I flagged as a hazard is deliberate upstream behaviour ("single source of truth… doesn't fire twice"). It only bites us because of item 2.

## Evidence

| Claim | Source | Verbatim |
|---|---|---|
| Global install is upstream's recommended setup | jdx/hk `docs/cli/install.md@v2.3.0` (raw: `.agent/kb/raw/hk-global-hooks/cli-install-v2.3.0.md`) | "The recommended setup is `hk install --global`, which installs hooks once into the user's `~/.gitconfig` so every repository on the machine picks them up automatically." |
| Repos without config are a designed no-op | same file | "In a project without an `hk.pkl`, the installed hook exits silently — no-op — so it's safe to enable everywhere. Requires Git 2.54+." |
| Local-hook cleanup is deliberate | same file | "If hk is already configured globally (any `hook.hk-*` entry in `~/.gitconfig`), the per-repo install is skipped — and any stale local hooks are cleaned up — so the global install remains the single source of truth and hk doesn't fire twice per event. Pass `--force-local` to install local hooks anyway." |
| Global is the "golden path" for mise users; postinstall recipe removed | https://github.com/jdx/hk/pull/1376 (merged 2026-09-13) | "Make `hk install --global --mise` the golden path for mise-backed Git hooks on Git 2.54 and newer… repositories without hk configuration remain no-ops." / "remove the project `postinstall` recipe from the main setup flow" |
| Why the postinstall recipe was removed: it races | https://github.com/jdx/hk/discussions/1375 | "it makes tool installation mutate the repository's `.git/config`… `could not lock config file .git/config: File exists`". Maintainer: "Yes — `hk install --global --mise` should be the golden path on Git 2.54 and newer. `hk install --mise` remains supported for users who want a repository-scoped installation." |
| Current v2.3.0 mise docs match | jdx/hk `docs/mise_integration.md@v2.3.0:36-61` (raw saved) | "The global launcher is the recommended setup… Use one installation scope at a time… `hk uninstall` / `hk install --global --mise`" |
| Users asked for the local-skip behaviour | https://github.com/jdx/hk/discussions/933 | "it would be great if the configured hooks would not be overwritten locally on the repositories" |
| Git's own mechanism for isolating from global config | `git help git` (git 2.54.0), ENVIRONMENT | "if GIT_CONFIG_GLOBAL is set, neither $HOME/.gitconfig nor $XDG_CONFIG_HOME/git/config will be read. Can be set to /dev/null to skip reading configuration files of the respective level." |
| This repo already uses that pattern | `tests/test_safe_directory.py:61-62` | isolates `GIT_CONFIG_GLOBAL` / `GIT_CONFIG_NOSYSTEM` (per `hk-v2-migration-research-2026-09-27.md` Q3) |
| The failure was the stale env, not the hooks | measured this session (`findings.md` 2026-09-26) | throwaway-repo commit with the global hook: rc=1 with `HK_PKL_BACKEND=pkl`; rc=0 with `env -u HK_PKL_BACKEND`; a fresh `zsh -lic` has it ABSENT |

### New probe: a global pre-push hook in a repo that defines no pre-push (control-armed)

Worry being tested: if dotfiles installs the global hooks from its own checkout (the event set then includes pre-push), would a global pre-push break every other hk repo? Measured with hk 2.3.0, isolated `GIT_CONFIG_GLOBAL`, scratch repos only:

| Arm | Result |
|---|---|
| repo `hk.pkl` defines only pre-commit; global `hook.hk-pre-push` → `git push` | **rc=0**, debug: `hook 'pre-push' not defined in …/hk.pkl, skipping (--from-hook)` |
| CONTROL: same repo, `hk.pkl` defines a failing `pre-push` step | **rc=1**, `PREPUSH_FAIL_ARM` ×5 in the output (the hook really enforces) |

So an event that is globally installed but undefined in a repo is a no-op there, just as a repo with no config is.

## Conflicts resolved

- **Our prior report vs upstream docs:** Q3 of `hk-v2-migration-research-2026-09-27.md` judged the global install "not a fit". Upstream's merged PR, current docs and the maintainer's answer (primary sources) define it as the recommended path, so I trust upstream. The Q3 *measurements* stand; the *verdict* is withdrawn.
- **"Double-fire":** it only happens with a legacy `.git/hooks` shim plus a global hook. v2's local-skip exists precisely to prevent it, and same-named config hooks resolve to one (git `hook.adoc@v2.54.0:1-7`). This is not a defect of the global install.

## Real trade-offs that remain (costs, not defects)

- **About 1.5 s per commit** for the no-op in repos without hk (measured in Q3). This is the price of "one install per machine".
- **hk looks up config in ancestor directories up to `/`,** so a throwaway repo created inside an hk-configured tree runs that tree's config. Isolating tests with `GIT_CONFIG_GLOBAL` removes the exposure.
- **The global event set is fixed at install time** (the cwd's hooks). The current entries (pre-commit, commit-msg) came from another project, so dotfiles' pre-push is not installed globally. Reinstalling from the dotfiles checkout fixes that, and the probe above shows it is harmless elsewhere.

## Gaps

- The ~1.5 s figure was measured with two no-op hooks. With three (adding pre-push) it only matters on push, which I didn't measure.
- I haven't checked which project wrote the current global entries, or whether it relies on their exact event set.
- I haven't read hk's `test`/CI guidance for suites that create git repos. The git-level `GIT_CONFIG_GLOBAL` mechanism is sufficient and already has precedent here.

## Recommendation (adapt, don't roll back)

1. **Keep the global install** (upstream's golden path) and **reinstall it once from the dotfiles checkout**, so the event set includes pre-push: `hk uninstall` (local) then `hk install --global --mise`. This is a user-level operator step.
2. **Remove our `postinstall = "… hk install --mise"`** (`mise.toml:180`) and keep `mise reshim`. This follows upstream's removal and the .git/config race (#1375). The spec's `--force-local` alternative is also supported, but it keeps a second installation scope that upstream says to avoid.
3. **Isolate the pytest git fixtures** with an autouse `GIT_CONFIG_GLOBAL=/dev/null` (git's documented mechanism; precedent `tests/test_safe_directory.py:61-62`), so no global hook or identity reaches a throwaway repo.
4. **Restart long-lived shells and sessions** so the stale `HK_PKL_BACKEND` goes away.
5. **CI stays as is:** we run hk through `mise run lint` (read-only `hk check --all`) and never `hk install` in CI, which matches upstream's `mise exec -- hk check --all` guidance (`mise_integration.md@v2.3.0:115-121`).

## GitHub repos touched

- [jdx/hk](https://github.com/jdx/hk) — PR #1376, discussions #1375, #933, #1030 (plus #754 and #937 fetched, raw only), `docs/cli/install.md` and `docs/mise_integration.md` at v2.3.0
- [git/git](https://github.com/git/git) — via the installed `git help git` (2.54.0) for `GIT_CONFIG_GLOBAL`
