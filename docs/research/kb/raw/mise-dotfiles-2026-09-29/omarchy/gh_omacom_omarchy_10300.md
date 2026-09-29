# omarchy-mise-install wrappers in ~/.local/bin are shadowed by `mise activate` after first run

- URL: https://github.com/omacom/omarchy/issues/10300
- state: open | author: YotamPeled | created: 2026-09-05T09:35:47Z | closed: null | merged_pr: n/a
- labels: bug

## Body

## Description

`omarchy-mise-install` writes a self-updating wrapper to `~/.local/bin/<command>`:

```bash
#!/bin/bash
export MISE_MINIMUM_RELEASE_AGE=0
mise use -g --quiet "claude" || exit 1
exec mise x "claude" -- "claude" "$@"
```

The wrapper's whole purpose (per its own comment) is to bypass mise's release cooldown so these fast-moving tools update on every launch.

It works exactly once. The first run's `mise use -g` adds the tool to `~/.config/mise/config.toml`. From then on `mise activate bash` (sourced from `default/bash/init`) prepends that tool's install dir to `PATH` on every prompt and every `cd` — ahead of `~/.local/bin`, which `default/bash/env-bootstrap` deliberately *appends* ("appended so system binaries keep precedence").

The wrapper is shadowed by a directory entry that the wrapper itself caused to exist. It is self-defeating by construction.

## Steps to reproduce

```bash
omarchy-mise-install claude
command -v claude          # ~/.local/bin/claude          ✅ wrapper
claude --version           # runs once, adds claude to the global mise config
# new shell
command -v claude          # ~/.local/share/mise/installs/claude/latest/claude   ❌ raw binary
```

## Expected

`command -v claude` keeps resolving to `~/.local/bin/claude`, so the tool self-updates on launch.

## Actual

It resolves to the mise install dir. The update step never runs. The tool sits on whatever version mise's cooldown last allowed, and Claude Code shows a permanent "Update available! Run: `mise upgrade claude`" banner — while `mise upgrade claude` correctly reports nothing to do, because the cooldown is still withholding the release. Two sources of truth disagreeing, with no way for the user to reconcile them short of `mup`.

On this machine, `claude`, `codex` and `gh` are affected (the wrappers that have been run). The other nine wrappers present in `~/.local/bin` — `copilot`, `crush`, `gemini`, `ghui`, `grok`, `hunk`, `omp`, `opencode`, `pi` — still resolve correctly only because they have never been launched. They break on second use.

## Root cause

Ordering conflict between two Omarchy-owned files:

| File | Effect |
|---|---|
| `default/bash/env-bootstrap` | appends `~/.local/bin` (low precedence, by design) |
| `default/bash/init` → `mise activate bash` | prepends each globally-active tool's install dir on every prompt/`cd` |

## Note on workarounds

A static `PATH="$HOME/.local/bin:$PATH"` in `~/.bashrc` does **not** hold — mise's prompt/`chpwd` hook rebuilds `PATH` on the next `cd` and re-shadows the wrapper. Verified:

```
after prepend:        ~/.local/bin/claude
after cd + mise hook: ~/.local/share/mise/installs/claude/latest/claude
```

An alias (`alias claude="$HOME/.local/bin/claude"`) does hold, since alias resolution precedes the `PATH` search — but that is a user-side patch, not a fix.

## Possible fixes

1. Have `omarchy-mise-install` emit a shell alias/function alongside the wrapper rather than relying on `PATH` precedence.
2. Don't use `mise use -g` in the wrapper — keep these tools out of the global config so `mise activate` never puts them on `PATH` (e.g. `mise x <tool>@latest` directly).
3. Re-prepend `~/.local/bin` from a mise `chpwd`/prompt hook that runs after mise's own.

## System details

- Omarchy `4.0.2-1`
- mise `2026.8.15 linux-x64` (`mise-bin` from the omarchy repo)
- bash, Arch, Hyprland


## Comments

### MyGuyArrow @ 2026-09-22T17:18:41Z

Still present on Omarchy `4.0.4-1` with mise `2026.9.10`. Adding three things the report doesn't have: a second shadowing path, a fix that doesn't fight `PATH` at all, and two diagnostic traps that make this expensive to debug.

## 1. `mise activate` isn't the only thing shadowing the wrapper

The shim directory does it too, and that one is pure `env-bootstrap` ordering — no activation, no prompt hook, no `cd`:

```bash
$ env -i HOME=/home/acs USER=acs PATH=/usr/local/sbin:/usr/local/bin:/usr/bin \
    bash --noprofile --norc -c 'source /usr/share/omarchy/default/bash/env-bootstrap
                                echo "$PATH"; command -v claude'
/usr/local/sbin:/usr/local/bin:/usr/bin:/home/acs/.local/share/mise/shims:/home/acs/.local/bin
/home/acs/.local/share/mise/shims/claude
```

`default/bash/env-bootstrap` appends the two directories in this order:

```bash
case ":$PATH:" in
  *":$HOME/.local/share/mise/shims:"*) ;;
  *) PATH="${PATH:+$PATH:}$HOME/.local/share/mise/shims" ;;   # <- appended first
esac
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) PATH="${PATH:+$PATH:}$HOME/.local/bin" ;;                # <- always lands after
esac
```

So `~/.local/bin` is behind the shims in *every* shell, and behind the install dirs as well once `mise activate` runs. This matters for proposed fix 3 in the description — re-prepending from a mise `chpwd`/prompt hook fixes interactive shells and leaves login and non-interactive shells resolving to the shim.

## 2. A fix that sidesteps `PATH` entirely

All three fixes listed are `PATH`/invocation tricks. The cooldown half of the problem doesn't need one — mise will honour an exemption recorded in its own config no matter how the tool is invoked:

```bash
mise settings add minimum_release_age_excludes claude
```

which writes

```toml
[settings]
minimum_release_age_excludes = ["claude"]
```

Verified against a forced cooldown, caches cleared between every case (`gh`, chosen because it wasn't already exempt here):

| exemption | `MISE_MINIMUM_RELEASE_AGE=30d mise ls-remote gh \| tail -1` |
|---|---|
| none | `2.98.0` — held back |
| `minimum_release_age_excludes = ["gh"]` in a config file | **`2.101.0`** |
| `MISE_MINIMUM_RELEASE_AGE=0` (reference) | `2.101.0` |

In `omarchy-mise-install`, beside the wrapper it already writes:

```bash
# The wrapper below stops being reachable once the tool is installed (#10300),
# so the MISE_MINIMUM_RELEASE_AGE=0 it exports never runs. Record the exemption
# where mise will honour it regardless of how the tool is invoked.
mise settings add minimum_release_age_excludes "$command" 2>/dev/null || true
[[ $package != "$command" ]] &&
  mise settings add minimum_release_age_excludes "$package" 2>/dev/null || true
```

This doesn't fix the shadowing, and it isn't meant to — it decouples the two failures. The wrapper's *other* job (re-resolving to latest on launch) still needs one of the three fixes above; but the tools stop sitting on stale versions in the meantime, and the "Update available! Run: `mise upgrade claude`" banner in #12444 stops disagreeing with mise.

**Gotcha for whoever implements it:** the exemption matches the name the tool is *addressed* by, and fails silently otherwise. Caches cleared between each case:

| exemption | addressed as | newest offered |
|---|---|---|
| none | `claude` | `2.1.278` — held back |
| `["claude"]` | `claude` | **`2.1.280`** |
| none | `aqua:anthropics/claude-code` | `2.1.278` — held back |
| `["claude"]` | `aqua:anthropics/claude-code` | `2.1.278` — **exemption not applied** |
| `["aqua:anthropics/claude-code"]` | `aqua:anthropics/claude-code` | **`2.1.280`** |

Hence adding both `$command` and `$package` above: wrappers like `omarchy-mise-install npm:playwright playwright` put the *spec* in the global config, so the short name alone wouldn't cover them.

## 3. Two traps that make this expensive to diagnose

**`mise settings get minimum_release_age` reports the setting as unset while the filter is actively running.** It's a built-in default of mise 2026.9.10 — nothing in `/usr/share/omarchy/` sets it, and it doesn't appear in `mise settings ls --all` either:

```
$ mise settings get minimum_release_age
mise ERROR Setting [minimum_release_age] is not set
$ mise ls-remote aqua:anthropics/claude-code | tail -1
2.1.278
mise WARN  1 newer aqua:anthropics/claude-code release hidden by minimum_release_age
```

Read literally, that getter says there is no cooldown. There is. Only the full backend spec prints the warning — `mise ls-remote claude` filters silently.

**`fetch_remote_versions_cache` is `1h` and the cached list is the already-filtered one.** A run with the exemption in force caches an unfiltered list that a later run without it then serves, and vice versa, so consecutive tests contradict each other until you clear:

```bash
rm -rf ~/.cache/mise/{<tool>,github,aqua-<owner>-<repo>}
```

For reference, the current default cooldown is longer than ~8h and shorter than ~3.6d — bracketed by test, not pinned; an explicit `7d` pushed `claude` back six releases.

## System details

- Omarchy `4.0.4-1`
- mise `2026.9.10 linux-x64 (2026-09-16)`, `mise-bin 2026.9.10-1`
- bash, Arch, Hyprland
- Affected here: `claude`, `codex`, `gh` — all resolving to the install dir or shim, never to `~/.local/bin`

---

Filed by Claude Opus 5 (1M context) via Claude Code.

