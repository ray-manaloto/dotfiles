[Skip to content](https://mise.jdx.dev/cli/plugins.html#VPContent)

Return to top

# `mise plugins` [​](https://mise.jdx.dev/cli/plugins.html\#mise-plugins)

- **Usage:**`mise plugins [FLAGS] [SUBCOMMAND]`
- **Aliases:**`p`, `plugin`, `plugin-list`
- **Effect:** read-only
- **Source code:** [`src/cli/plugins/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/plugins/mod.rs)

Manage plugins

## Flags [​](https://mise.jdx.dev/cli/plugins.html\#flags)

- **`-c --core`** — Only show built-in (core) plugins These are hidden by default

- **`-u --urls`** — Show the git url for each plugin e.g.: [https://github.com/mise-plugins/vfox-cmake.git](https://github.com/mise-plugins/vfox-cmake.git)

- **`--user`** — List installed plugins

This is the default behavior but can be used with --core to show core and user plugins

- **`-h --help`** — Print help


## Subcommands [​](https://mise.jdx.dev/cli/plugins.html\#subcommands)

- [`mise plugins install [FLAGS] [NEW_PLUGIN] [GIT_URL]`](https://mise.jdx.dev/cli/plugins/install.html)
- [`mise plugins link [-f --force] <NAME> [DIR]`](https://mise.jdx.dev/cli/plugins/link.html)
- [`mise plugins ls [FLAGS]`](https://mise.jdx.dev/cli/plugins/ls.html)
- [`mise plugins ls-remote [-u --urls] [--only-names]`](https://mise.jdx.dev/cli/plugins/ls-remote.html)
- [`mise plugins uninstall [-a --all] [-p --purge] [PLUGIN]…`](https://mise.jdx.dev/cli/plugins/uninstall.html)
- [`mise plugins update [-j --jobs <JOBS>] [PLUGIN]…`](https://mise.jdx.dev/cli/plugins/update.html)

## Related documentation [​](https://mise.jdx.dev/cli/plugins.html\#related-documentation)

- [Plugin selection and maintenance](https://mise.jdx.dev/plugin-usage.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).