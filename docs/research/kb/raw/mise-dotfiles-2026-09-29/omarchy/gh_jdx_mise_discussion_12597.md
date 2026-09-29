# Using managed tool-stub bundles for Omarchy’s lazy CLI layer

- URL: https://github.com/jdx/mise/discussions/12597
- author: jdx created: 2026-08-29T20:20:52Z

## Body

I want to use mise as the lazy CLI distribution layer for [Omarchy](https://github.com/omacom/omarchy), without making every CLI a global mise tool or maintaining a hand-written Bash wrapper for each command.

This is the concrete consumer motivating the managed tool-stub work in #12594, stacked on the safer upgrade/pruning lifecycle in #12593.

## What Omarchy does today

Omarchy ships a catalogue of developer and AI CLIs such as `codex`, `claude`, `gh`, `opencode`, `playwright`, and `ori`. It wants every command to be present on `PATH` immediately, but it does not want to download every tool during OS installation.

Today [`install/user/mise.sh`](https://github.com/omacom/omarchy/blob/quattro/install/user/mise.sh) invokes [`omarchy-mise-install`](https://github.com/omacom/omarchy/blob/quattro/bin/omarchy-mise-install) once for every command. That helper writes a Bash script to `~/.local/bin`; the script runs `mise use -g` on first invocation and then executes the tool with `mise x`.

The behavior is useful, but the implementation creates several sources of truth:

- the repeated installer calls
- one generated Bash file per command
- update behavior
- migrations for renamed or removed commands
- preinstall removal/restoration logic
- collision handling when a user already owns the command name

It also writes each invoked CLI into the user's global mise configuration even though Omarchy only needs a lazy executable.

## What I want to do

Ship a single manifest in the Omarchy package, probably at `/usr/share/omarchy/install/user/mise-tools.toml`:

```toml
[commands]
codex = "codex"
claude = "claude"
crush = "crush"
agy = "antigravity-cli"
gh = "gh"
copilot = "copilot"
opencode = "opencode"
playwright = { tool = "npm:playwright", version = "latest", bin = "playwright" }
pi = "pi"
omp = { tool = "github:can1357/oh-my-pi", version = "latest", bin = "omp" }
grok = { tool = "npm:@xai-official/grok", version = "latest", bin = "grok" }
ghui = { tool = "npm:@kitlangton/ghui", version = "latest", bin = "ghui" }
hunk = { tool = "aqua:modem-dev/hunk", version = "latest", bin = "hunk" }
hey = { tool = "github:basecamp/hey-cli", version = "latest", bin = "hey" }
ori = { tool = "github:OpenRouterLabs/ori-releases", version = "latest", bin = "ori" }
```

During user provisioning—or after a package update—Omarchy would synchronize it:

```bash
mise tool-stubs sync /usr/share/omarchy/install/user/mise-tools.toml
```

The result is the UX Omarchy wants:

1. Every declared command exists immediately in `~/.local/bin`.
2. Synchronization downloads no tools.
3. The first invocation installs only that command's selected tool.
4. The tool does not need to be added to the user's global `mise.toml`.
5. Package upgrades can add, rename, or remove commands by changing one manifest and syncing it again.

For example, after provisioning:

```bash
$ mise tool-stubs status /usr/share/omarchy/install/user/mise-tools.toml
current   codex                ~/.local/bin/codex
current   claude               ~/.local/bin/claude
current   gh                   ~/.local/bin/gh
# ...

$ gh auth status
# gh is installed on demand, then receives the original arguments
```

## Updates without defeating lazy installation

Omarchy's `omarchy update` should update only tools that users have already invoked. It should not install the entire catalogue merely because an OS update ran:

```bash
MISE_MINIMUM_RELEASE_AGE=0 \
  mise tool-stubs upgrade /usr/share/omarchy/install/user/mise-tools.toml
```

That is why the `upgrade` operation in #12594 skips uninstalled selections. The top-level alternative is useful for users who want tracked stubs from multiple sources included in their normal mise upgrade:

```bash
mise upgrade --tool-stubs
```

#12593 matters here because replacing a tool should not make the previous installation disappear immediately. The old version is kept for a configurable grace period (24 hours by default), with explicit `--prune` and `--no-prune` controls.

Omarchy currently sets `MISE_MINIMUM_RELEASE_AGE=0` in each generated wrapper so a first invocation is not held behind mise's release cooldown. The command above preserves that policy during `omarchy update`; the managed bundle format does not currently encode a per-command runtime environment override. I see that as a separate Omarchy policy/integration question rather than something to hide inside this initial implementation.

## Ownership and opt-out behavior

Omarchy must not silently replace a user's own `~/.local/bin/gh`, nor destroy a generated stub the user edited. Managed bundles record ownership and content hashes, so those cases are reported as conflicts and require an explicit `--force`.

The existing "Remove Preinstalls" feature could remove the commands owned by the Omarchy bundle without uninstalling any underlying tools:

```bash
mise tool-stubs remove /usr/share/omarchy/install/user/mise-tools.toml
```

Restoring preinstalls is the inverse operation:

```bash
mise tool-stubs sync /usr/share/omarchy/install/user/mise-tools.toml
```

That gives Omarchy one declarative CLI catalogue, preserves lazy installation, avoids modifying global tool configuration, and gives package upgrades a guarded synchronization and upgrade lifecycle.

Feedback is welcome on the bundle interface and on any distribution lifecycle that this shape does not cover.

*AI-assisted — Tool: Codex; model: OpenAI/GPT-5; version: unavailable.*


## Comments

