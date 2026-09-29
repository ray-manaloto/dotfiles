[Skip to content](https://mise.jdx.dev/cli/plugins/ls-remote.html#VPContent)

On this page

# `mise plugins ls-remote` [​](https://mise.jdx.dev/cli/plugins/ls-remote.html\#mise-plugins-ls-remote)

- **Usage:**`mise plugins ls-remote [-u --urls] [--only-names]`
- **Aliases:**`list-remote`, `list-all`
- **Effect:** read-only
- **Source code:** [`src/cli/plugins/ls_remote.rs`](https://github.com/jdx/mise/blob/main/src/cli/plugins/ls_remote.rs)

List all available remote plugins

These are the shorthand names from the registry: [https://github.com/jdx/mise/blob/main/registry/](https://github.com/jdx/mise/blob/main/registry/)

## Flags [​](https://mise.jdx.dev/cli/plugins/ls-remote.html\#flags)

- **`-u --urls`** — Show the git url for each plugin, e.g. [https://github.com/mise-plugins/mise-poetry.git](https://github.com/mise-plugins/mise-poetry.git)
- **`--only-names`** — Only show the name of each plugin, without the "\*" marking installed plugins
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/plugins/ls-remote.html\#examples)

```
mise plugins ls-remote
```

## Related documentation [​](https://mise.jdx.dev/cli/plugins/ls-remote.html\#related-documentation)

- [Plugin selection and maintenance](https://mise.jdx.dev/plugin-usage.html).
- [`mise plugins [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/plugins.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)