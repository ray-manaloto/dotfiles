[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/apply.html#VPContent)

On this page

# `mise bootstrap packages apply` [​](https://mise.jdx.dev/cli/bootstrap/packages/apply.html\#mise-bootstrap-packages-apply)

- **Usage:**`mise bootstrap packages apply [FLAGS] [PACKAGE]…`
- **Aliases:**`i`, `install`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/system/install.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/install.rs)

Apply system packages from `[bootstrap.packages]`

Checks which configured packages are missing and installs them with the system package manager. Built-in system managers may elevate with sudo when not running as root (see `system_packages.sudo`); package plugins never do.

Packages can also be given explicitly in `manager:package` form (e.g. `apk:zlib-dev`, `apt:curl`, `brew:jq`, `winget:BurntSushi.ripgrep.MSVC`); they are installed whether or not they appear in the config. Explicit packages and `--manager` scope the run to packages only. `install` is accepted as an alias for this command.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/packages/apply.html\#arguments)

- **`[PACKAGE]…`** — Packages in `manager:package` form; defaults to everything configured in \[bootstrap.packages\]

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/apply.html\#flags)

- **`-m --manager <MANAGER>`** — Only install packages for this built-in or plugin manager
- **`-n --dry-run`** — Print the commands that would run without running them
- **`-y --yes`** — Skip the confirmation prompt
- **`--update`** — Refresh package manager metadata first (apk: `--update-cache`, apt: `apt-get update`, zypper: `refresh`, winget: `source update`)
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/apply.html\#examples)

```
mise bootstrap packages apply
mise bootstrap packages apply brew:jq brew-cask:firefox winget:BurntSushi.ripgrep.MSVC
mise bootstrap packages apply --dry-run
mise bootstrap packages apply --manager apt --yes
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/apply.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)