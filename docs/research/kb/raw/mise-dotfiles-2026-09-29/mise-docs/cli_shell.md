[Skip to content](https://mise.jdx.dev/cli/shell.html#VPContent)

On this page

# `mise shell` [​](https://mise.jdx.dev/cli/shell.html\#mise-shell)

- **Usage:**`mise shell [FLAGS] <TOOL@VERSION>…`
- **Aliases:**`sh`
- **Effect:** read-only
- **Source code:** [`src/cli/shell.rs`](https://github.com/jdx/mise/blob/main/src/cli/shell.rs)

Set a tool version for the current shell session

Only works in a session where mise is already activated.

This works by setting environment variables for the current shell session such as `MISE_NODE_VERSION=20` which is "eval"ed as a shell function created by `mise activate`.

## Arguments [​](https://mise.jdx.dev/cli/shell.html\#arguments)

- **`<TOOL@VERSION>…`** — Tool(s) to use

## Flags [​](https://mise.jdx.dev/cli/shell.html\#flags)

- **`-j --jobs <JOBS>`** — Number of jobs to run in parallel Values below 1 are treated as 1 Defaults to the `jobs` setting

**Environment Variable:**`MISE_JOBS`

- **`-u --unset`** — Remove a previously set version

- **`--raw`** — Connect backend install command stdin/stdout/stderr directly to the terminal. Implies `--jobs=1`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/shell.html\#examples)

```
mise shell node@20
node -v
v20.0.0
```

## Related documentation [​](https://mise.jdx.dev/cli/shell.html\#related-documentation)

- [Shell activation](https://mise.jdx.dev/getting-started.html#activate-mise).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)