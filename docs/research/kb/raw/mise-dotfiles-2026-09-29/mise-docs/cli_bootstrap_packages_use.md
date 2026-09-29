[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/use.html#VPContent)

On this page

# `mise bootstrap packages use` [​](https://mise.jdx.dev/cli/bootstrap/packages/use.html\#mise-bootstrap-packages-use)

- **Usage:**`mise bootstrap packages use [FLAGS] <PACKAGE>…`
- **Aliases:**`u`
- **Effect:** modifies state
- **Source code:** [`src/cli/system/use.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/use.rs)

Add bootstrap packages to \[bootstrap.packages\] and install them

Like `mise use` for tools: writes `"manager:package" = "version"` entries to mise.toml (the local config by default, the global one with `-g`) and then installs whatever is missing.

Versions are pinned with `@`: `mise bootstrap packages use apt:curl@8.5.0-2`. Without `@` (or with `@latest`) no pin is written. brew formulae and casks version through their names instead (for example `brew:postgresql@17`, `brew-cask:temurin@17`), where `@` is part of the Homebrew name rather than a mise version selector. mas uses numeric ADAM IDs and does not support pins.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/packages/use.html\#arguments)

- **`<PACKAGE>…`** — Packages in `manager:package[@version]` form

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/use.html\#flags)

- **`-e --env <ENV>`** — Write to the config file for this environment (mise.<ENV>.toml)

- **`-g --global`** — Write to the global config (~/.config/mise/config.toml) instead of the local one

- **`-n --dry-run`** — Print the commands that would run without writing config or installing

- **`-p --path <PATH>`** — Write to this config file or directory

**Aliases:**`--file`

- **`-y --yes`** — Skip the confirmation prompt

- **`--no-install`** — Write the package declarations without checking or installing packages

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/use.html\#examples)

```
mise bootstrap packages use brew:jq brew-cask:firefox winget:BurntSushi.ripgrep.MSVC
mise bootstrap packages use -g brew:postgresql@17
mise bootstrap packages use apt:curl@8.5.0-2
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/use.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).