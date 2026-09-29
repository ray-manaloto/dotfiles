[Skip to content](https://mise.jdx.dev/cli/plugins/ls.html#VPContent)

On this page

# `mise plugins ls` [​](https://mise.jdx.dev/cli/plugins/ls.html\#mise-plugins-ls)

- **Usage:**`mise plugins ls [FLAGS]`
- **Aliases:**`list`
- **Effect:** read-only
- **Source code:** [`src/cli/plugins/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/plugins/ls.rs)

List installed external plugins

Use `--core` for built-in runtimes or `--core --user` for both groups. `--outdated` queries Git remotes for plugin updates; it does not compare installed tool versions. Use `mise plugins ls-remote` for registry plugin sources and `mise ls` for tools.

## Flags [​](https://mise.jdx.dev/cli/plugins/ls.html\#flags)

- **`-c --core`** — Only show built-in (core) plugins These are hidden by default

- **`-o --outdated`** — Show plugins with available updates Checks the remote for newer versions and only displays plugins that are outdated

- **`-u --urls`** — Show the git url for each plugin e.g.: [https://github.com/mise-plugins/vfox-cmake.git](https://github.com/mise-plugins/vfox-cmake.git)

- **`--user`** — List installed plugins

This is the default behavior but can be used with --core to show core and user plugins

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/plugins/ls.html\#examples)

```
mise plugins ls
mise plugins ls --urls
mise plugins ls --core --user
mise plugins ls --outdated
```

## Related documentation [​](https://mise.jdx.dev/cli/plugins/ls.html\#related-documentation)

- [Plugin selection and maintenance](https://mise.jdx.dev/plugin-usage.html).
- [`mise plugins [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/plugins.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)