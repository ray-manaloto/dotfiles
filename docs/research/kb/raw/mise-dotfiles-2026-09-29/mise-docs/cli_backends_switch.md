[Skip to content](https://mise.jdx.dev/cli/backends/switch.html#VPContent)

On this page

# `mise backends switch` [​](https://mise.jdx.dev/cli/backends/switch.html\#mise-backends-switch)

- **Usage:**`mise backends switch [-n --dry-run] [-g --global] [TOOL@VERSION]…`
- **Effect:** modifies state
- **Source code:** [`src/cli/backends/switch.rs`](https://github.com/jdx/mise/blob/main/src/cli/backends/switch.rs)

Switch tools to the backend the registry now installs them from

When the registry moves a tool to another backend, mise keeps installing it from the backend recorded in mise.lock and warns that the registry has a newer one. This moves those lock entries to the registry's backend at the same versions, relocks them to record the new backend's checksums and URLs, and reinstalls installed versions so they come from the new backend.

It covers the lockfiles `mise lock` writes: the current project's, or the global config's with `--global`.

## Arguments [​](https://mise.jdx.dev/cli/backends/switch.html\#arguments)

- **`[TOOL@VERSION]…`** — Tools to switch

Defaults to every configured tool whose locked backend the registry has replaced. A version (`hk@1.58.1`) limits the switch to that version.


## Flags [​](https://mise.jdx.dev/cli/backends/switch.html\#flags)

- **`-n --dry-run`** — Show what would switch without changing the lockfile or installs
- **`-g --global`** — Switch tools in the global config's lockfile instead of the project's
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/backends/switch.html\#examples)

Move communique to the registry's current backend

```
mise backends switch communique
```

List every locked tool the registry now installs from another backend

```
mise backends switch --dry-run
```

## Related documentation [​](https://mise.jdx.dev/cli/backends/switch.html\#related-documentation)

- [Choosing backends](https://mise.jdx.dev/dev-tools/backends/).
- [`mise backends [SUBCOMMAND]`](https://mise.jdx.dev/cli/backends.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)