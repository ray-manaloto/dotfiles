[Skip to content](https://mise.jdx.dev/cli/deps/add.html#VPContent)

On this page

# `mise deps add` [​](https://mise.jdx.dev/cli/deps/add.html\#mise-deps-add)

- **Usage:**`mise deps add [-D --dev] <PACKAGES>…`
- **Effect:** modifies state
- **Source code:** [`src/cli/deps/add.rs`](https://github.com/jdx/mise/blob/main/src/cli/deps/add.rs)

Add a dependency

Adds one or more packages to the project using the appropriate package manager. Package specs use the format `ecosystem:package`, e.g., `npm:react` or `npm:@types/react@19`.

## Arguments [​](https://mise.jdx.dev/cli/deps/add.html\#arguments)

- **`<PACKAGES>…`** — Package(s) to add (e.g., npm:react, npm:@types/react@19)

## Flags [​](https://mise.jdx.dev/cli/deps/add.html\#flags)

- **`-D --dev`** — Add as a development dependency
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/deps/add.html\#related-documentation)

- [Project dependencies](https://mise.jdx.dev/dev-tools/deps.html).
- [`mise deps [FLAGS] [PROVIDER] [SUBCOMMAND]`](https://mise.jdx.dev/cli/deps.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)