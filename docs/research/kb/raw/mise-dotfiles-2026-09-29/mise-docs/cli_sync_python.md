[Skip to content](https://mise.jdx.dev/cli/sync/python.html#VPContent)

On this page

# `mise sync python` [​](https://mise.jdx.dev/cli/sync/python.html\#mise-sync-python)

- **Usage:**`mise sync python [--pyenv] [--uv]`
- **Effect:** modifies state
- **Source code:** [`src/cli/sync/python.rs`](https://github.com/jdx/mise/blob/main/src/cli/sync/python.rs)

Symlink python versions installed by pyenv or uv into mise

Use this to make versions installed by another version manager available to mise.

This won't overwrite managed installs, runtime aliases, or links from other providers.

## Flags [​](https://mise.jdx.dev/cli/sync/python.html\#flags)

- **`--pyenv`** — Get tool versions from pyenv
- **`--uv`** — Sync tool versions with uv (2-way sync)
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/sync/python.html\#examples)

```
pyenv install 3.11.0
mise sync python --pyenv
mise use -g python@3.11.0 # uses pyenv-provided python
```

```
uv python install 3.11.0
mise install python@3.10.0
mise sync python --uv
mise x python@3.11.0 -- python -V # uses uv-provided python
uv run -p 3.10.0 -- python -V # uses mise-provided python
```

## Related documentation [​](https://mise.jdx.dev/cli/sync/python.html\#related-documentation)

- [Python](https://mise.jdx.dev/lang/python.html).
- [`mise sync <SUBCOMMAND>`](https://mise.jdx.dev/cli/sync.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)