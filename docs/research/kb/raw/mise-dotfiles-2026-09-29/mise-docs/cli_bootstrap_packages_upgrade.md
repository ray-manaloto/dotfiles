[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/upgrade.html#VPContent)

On this page

# `mise bootstrap packages upgrade` [​](https://mise.jdx.dev/cli/bootstrap/packages/upgrade.html\#mise-bootstrap-packages-upgrade)

- **Usage:**`mise bootstrap packages upgrade [FLAGS] [PACKAGE]…`
- **Aliases:**`up`
- **Effect:** modifies state
- **Source code:** [`src/cli/system/upgrade.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/upgrade.rs)

Upgrade installed bootstrap packages from `[bootstrap.packages]`

Refreshes package manager metadata and upgrades the configured packages that are already installed: apk/apt/aur/dnf/pacman/zypper upgrade to the newest available version (apk, apt, dnf, and zypper honor a version pinned in config), brew pours the formula's current bottle and replaces the old keg, brew-cask installs the current cask artifact, flatpak and flatpak-user update applications and runtimes, mas upgrades App Store apps, and winget upgrades Windows packages. Packages that are not installed yet are skipped — use `mise bootstrap packages apply` for those.

Packages can also be given explicitly in `manager:package` form.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/packages/upgrade.html\#arguments)

- **`[PACKAGE]…`** — Packages in `manager:package` form; defaults to everything configured in \[bootstrap.packages\]

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/upgrade.html\#flags)

- **`-m --manager <MANAGER>`** — Only upgrade packages for this built-in or plugin manager
- **`-n --dry-run`** — Print the commands that would run without running them
- **`-y --yes`** — Skip the confirmation prompt
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/upgrade.html\#examples)

```
mise bootstrap packages upgrade
mise bootstrap packages upgrade brew:postgresql@17
mise bootstrap packages upgrade --manager brew-cask
mise bootstrap packages upgrade --manager mas
mise bootstrap packages upgrade --manager winget
mise bootstrap packages upgrade --manager apt --yes
mise bootstrap packages upgrade --dry-run
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/upgrade.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)