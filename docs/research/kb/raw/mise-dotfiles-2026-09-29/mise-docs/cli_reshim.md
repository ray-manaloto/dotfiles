[Skip to content](https://mise.jdx.dev/cli/reshim.html#VPContent)

On this page

# `mise reshim` [​](https://mise.jdx.dev/cli/reshim.html\#mise-reshim)

- **Usage:**`mise reshim [-f --force] [--system]`
- **Effect:** modifies state
- **Source code:** [`src/cli/reshim.rs`](https://github.com/jdx/mise/blob/main/src/cli/reshim.rs)

Create shims for executables provided by installed tools

Run this when an executable was added to an existing installation outside mise, for example after a language package manager installed a CLI globally. It rebuilds the user shim directory by default; `--system` selects the shared system shim farm.

Shims are created for all installed versions. The shim resolves which version to run from the current configuration when invoked. `--force` rebuilds mise-owned shims; it does not turn unrelated files into mise-owned shims.

## Flags [​](https://mise.jdx.dev/cli/reshim.html\#flags)

- **`-f --force`** — Rebuild all mise-owned shims
- **`--system`** — Rebuild the system shim farm
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/reshim.html\#examples)

Rebuild shims, then check node. Example output: `v20.0.0`.

```
mise reshim
~/.local/share/mise/shims/node -v
```

## Related documentation [​](https://mise.jdx.dev/cli/reshim.html\#related-documentation)

- [Shims](https://mise.jdx.dev/dev-tools/shims.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)