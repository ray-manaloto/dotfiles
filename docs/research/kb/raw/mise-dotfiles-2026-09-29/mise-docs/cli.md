[Skip to content](https://mise.jdx.dev/cli/#VPContent)

On this page

# `mise` [​](https://mise.jdx.dev/cli/\#mise)

**Author:** Jeff Dickey <@jdx>

**Usage:**`mise [FLAGS] [COMMAND | TASK] [ARGS]…`

Use `mise COMMAND --help` for the help shipped with your installed version. Put mise flags before a task name; arguments after the name are passed to that task. Square brackets mark optional input, angle brackets mark required input, and `…` means the argument can repeat. Do not type those notation characters.

## Arguments [​](https://mise.jdx.dev/cli/\#arguments)

- **`[TASK]`** — Task to run.

Shorthand for `mise tasks run <TASK>`.


## Global Flags [​](https://mise.jdx.dev/cli/\#global-flags)

These flags provide shared context. A command can define its own flag with the same name, so consult that command's page for placement and meaning. Effect labels describe the command's intended operation; configuration evaluation, caches, and required tool installation can still have side effects. They are not sandbox guarantees.

- **`-C --cd <DIR>`** — Change directory before running command

- **`-E --env <ENV>`** — Set the environment for loading `mise.<ENV>.toml`

- **`-j --jobs <JOBS>`** — How many jobs to run in parallel; values below 1 are treated as 1 \[default: 8\]

**Environment Variable:**`MISE_JOBS`

- **`-q --quiet`** — Suppress non-error messages

**Environment Variable:**`MISE_QUIET`

- **`-v --verbose`** — Show extra output (use -vv for even more)

- **`-y --yes`** — Answer yes to all confirmation prompts

- **`--raw`** — Read/write directly to stdin/stdout/stderr instead of by line

- **`--locked`** — Require lockfile URLs to be present during installation

Fails if tools don't have pre-resolved URLs in the lockfile for the current platform. This prevents API calls to GitHub, aqua registry, etc. Can also be enabled via MISE\_LOCKED=1 or settings.locked=true

- **`--silent`** — Suppress all task output and mise non-error messages


## Flags [​](https://mise.jdx.dev/cli/\#flags)

- **`--no-config`** — Do not load any config files

Can also use `MISE_NO_CONFIG=1`

- **`--no-env`** — Do not load environment variables from config files

Can also use `MISE_NO_ENV=1`

- **`--no-hooks`** — Do not execute hooks from config files

Can also use `MISE_NO_HOOKS=1`

- **`-h --help`** — Print help


## Subcommands [​](https://mise.jdx.dev/cli/\#subcommands)

Choose a command family below. Its page lists the available subcommands.

### Install and inspect tools [​](https://mise.jdx.dev/cli/\#install-and-inspect-tools)

- [`mise use`](https://mise.jdx.dev/cli/use.html) — Install a tool and add it to configuration
- [`mise install`](https://mise.jdx.dev/cli/install.html) — Install a tool version
- [`mise install-into`](https://mise.jdx.dev/cli/install-into.html) — Install a tool version to a specific path
- [`mise uninstall`](https://mise.jdx.dev/cli/uninstall.html) — Remove installed tool versions
- [`mise unuse`](https://mise.jdx.dev/cli/unuse.html) — Remove tool requests from configuration and prune unused installations
- [`mise upgrade`](https://mise.jdx.dev/cli/upgrade.html) — Upgrade outdated tools
- [`mise outdated`](https://mise.jdx.dev/cli/outdated.html) — Show outdated tool versions
- [`mise lock`](https://mise.jdx.dev/cli/lock.html) — Create or refresh lockfile versions, checksums, and download URLs
- [`mise latest`](https://mise.jdx.dev/cli/latest.html) — Resolve the latest matching version request for a tool
- [`mise ls`](https://mise.jdx.dev/cli/ls.html) — List installed and active tool versions
- [`mise ls-remote`](https://mise.jdx.dev/cli/ls-remote.html) — List tool versions available to install
- [`mise tool`](https://mise.jdx.dev/cli/tool.html) — Show information about a tool
- [`mise where`](https://mise.jdx.dev/cli/where.html) — Display the installation path for a tool
- [`mise which`](https://mise.jdx.dev/cli/which.html) — Show the path a tool's executable resolves to
- [`mise bin-paths`](https://mise.jdx.dev/cli/bin-paths.html) — List all the active runtime bin paths
- [`mise registry`](https://mise.jdx.dev/cli/registry.html) — List registry shorthand names and their backends
- [`mise search`](https://mise.jdx.dev/cli/search.html) — Search for available tools
- [`mise backends`](https://mise.jdx.dev/cli/backends.html) — Manage backends
- [`mise link`](https://mise.jdx.dev/cli/link.html) — Symlink a tool version into mise
- [`mise sync`](https://mise.jdx.dev/cli/sync.html) — Synchronize tools from other version managers with mise
- [`mise prune`](https://mise.jdx.dev/cli/prune.html) — Delete unused versions of tools
- [`mise reshim`](https://mise.jdx.dev/cli/reshim.html) — Create shims for executables provided by installed tools
- [`mise tool-stub`](https://mise.jdx.dev/cli/tool-stub.html) — Execute a tool stub
- [`mise packslip`](https://mise.jdx.dev/cli/packslip.html) — The signers mise accepts packslips from

### Shell and environment [​](https://mise.jdx.dev/cli/\#shell-and-environment)

- [`mise activate`](https://mise.jdx.dev/cli/activate.html) — Print the script to activate mise in an interactive shell
- [`mise deactivate`](https://mise.jdx.dev/cli/deactivate.html) — Print the script to disable mise in the current shell session
- [`mise completion`](https://mise.jdx.dev/cli/completion.html) — Generate shell completions
- [`mise en`](https://mise.jdx.dev/cli/en.html) — Start a new shell with the mise environment built from the current configuration
- [`mise env`](https://mise.jdx.dev/cli/env.html) — Print the environment for the current configuration
- [`mise exec`](https://mise.jdx.dev/cli/exec.html) — Execute a command with tool(s) set
- [`mise shell`](https://mise.jdx.dev/cli/shell.html) — Set a tool version for the current shell session
- [`mise set`](https://mise.jdx.dev/cli/set.html) — Set environment variables in mise.toml
- [`mise unset`](https://mise.jdx.dev/cli/unset.html) — Remove environment variable(s) from the config file
- [`mise shell-alias`](https://mise.jdx.dev/cli/shell-alias.html) — Manage shell aliases
- [`mise tool-alias`](https://mise.jdx.dev/cli/tool-alias.html) — Manage tool version aliases
- [`mise ssh`](https://mise.jdx.dev/cli/ssh.html) — Open an SSH session, optionally borrowing read-only GitHub access

### Tasks and project automation [​](https://mise.jdx.dev/cli/\#tasks-and-project-automation)

- [`mise run`](https://mise.jdx.dev/cli/run.html) — Run tasks and their dependencies
- [`mise tasks`](https://mise.jdx.dev/cli/tasks.html) — Manage tasks
- [`mise watch`](https://mise.jdx.dev/cli/watch.html) — Run task(s) and rerun them when files change
- [`mise deps`](https://mise.jdx.dev/cli/deps.html) — \[experimental\] Manage project dependencies
- [`mise generate`](https://mise.jdx.dev/cli/generate.html) — Generate files for various tools/services

### Machine setup and images [​](https://mise.jdx.dev/cli/\#machine-setup-and-images)

- [`mise bootstrap`](https://mise.jdx.dev/cli/bootstrap.html) — Set up a machine from the current configuration
- [`mise oci`](https://mise.jdx.dev/cli/oci.html) — \[experimental\] Build OCI container images from a mise.toml

### Configuration and diagnostics [​](https://mise.jdx.dev/cli/\#configuration-and-diagnostics)

- [`mise config`](https://mise.jdx.dev/cli/config.html) — Manage config files
- [`mise edit`](https://mise.jdx.dev/cli/edit.html) — Edit mise.toml interactively
- [`mise fmt`](https://mise.jdx.dev/cli/fmt.html) — Format mise TOML configuration
- [`mise settings`](https://mise.jdx.dev/cli/settings.html) — Manage settings
- [`mise trust`](https://mise.jdx.dev/cli/trust.html) — Mark a config file as trusted
- [`mise untrust`](https://mise.jdx.dev/cli/untrust.html) — Remove explicit trust for a config
- [`mise doctor`](https://mise.jdx.dev/cli/doctor.html) — Check mise installation for possible problems
- [`mise cache`](https://mise.jdx.dev/cli/cache.html) — Manage the mise cache
- [`mise version`](https://mise.jdx.dev/cli/version.html) — Display the version of mise
- [`mise self-update`](https://mise.jdx.dev/cli/self-update.html) — Update mise itself
- [`mise implode`](https://mise.jdx.dev/cli/implode.html) — Remove the mise CLI and all related data

### Integrations and community [​](https://mise.jdx.dev/cli/\#integrations-and-community)

- [`mise mcp`](https://mise.jdx.dev/cli/mcp.html) — Run the Model Context Protocol server over stdin/stdout
- [`mise skills`](https://mise.jdx.dev/cli/skills.html) — Agent skills the active tools ship, from their packslips
- [`mise patrons`](https://mise.jdx.dev/cli/patrons.html) — Show the individuals supporting mise as Patron-tier members
- [`mise sponsors`](https://mise.jdx.dev/cli/sponsors.html) — Show the companies sponsoring mise and the jdx.dev open source tools

### Other commands [​](https://mise.jdx.dev/cli/\#other-commands)

- [`mise daemons`](https://mise.jdx.dev/cli/daemons.html) — \[experimental\] Manage project daemons with pitchfork
- [`mise dotfiles`](https://mise.jdx.dev/cli/dotfiles.html) — Manage dotfiles from `[dotfiles]`
- [`mise plugins`](https://mise.jdx.dev/cli/plugins.html) — Manage plugins
- [`mise test-tool`](https://mise.jdx.dev/cli/test-tool.html) — Test that a tool installs and runs
- [`mise token`](https://mise.jdx.dev/cli/token.html) — Display git provider tokens mise will use

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)