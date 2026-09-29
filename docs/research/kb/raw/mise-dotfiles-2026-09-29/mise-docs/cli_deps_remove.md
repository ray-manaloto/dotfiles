[Skip to content](https://mise.jdx.dev/cli/deps/remove.html#VPContent)

On this page

# `mise deps remove` [​](https://mise.jdx.dev/cli/deps/remove.html\#mise-deps-remove)

- **Usage:**`mise deps remove <PACKAGES>…`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/deps/remove.rs`](https://github.com/jdx/mise/blob/main/src/cli/deps/remove.rs)

Remove a dependency

Removes one or more packages from the project using the appropriate package manager. Package specs use the format `ecosystem:package`, e.g., `npm:lodash`.

## Arguments [​](https://mise.jdx.dev/cli/deps/remove.html\#arguments)

- **`<PACKAGES>…`** — Package(s) to remove (e.g., npm:lodash)

## Flags [​](https://mise.jdx.dev/cli/deps/remove.html\#flags)

- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/deps/remove.html\#related-documentation)

- [Project dependencies](https://mise.jdx.dev/dev-tools/deps.html).
- [`mise deps [FLAGS] [PROVIDER] [SUBCOMMAND]`](https://mise.jdx.dev/cli/deps.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)