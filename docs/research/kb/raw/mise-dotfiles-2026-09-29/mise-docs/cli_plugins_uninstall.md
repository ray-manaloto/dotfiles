[Skip to content](https://mise.jdx.dev/cli/plugins/uninstall.html#VPContent)

On this page

# `mise plugins uninstall` [​](https://mise.jdx.dev/cli/plugins/uninstall.html\#mise-plugins-uninstall)

- **Usage:**`mise plugins uninstall [-a --all] [-p --purge] [PLUGIN]…`
- **Aliases:**`remove`, `rm`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/plugins/uninstall.rs`](https://github.com/jdx/mise/blob/main/src/cli/plugins/uninstall.rs)

Remove an installed plugin

Tool installations are retained by default. Pass `--purge` to also remove installs, downloads, and cache associated with the selected plugins.

## Arguments [​](https://mise.jdx.dev/cli/plugins/uninstall.html\#arguments)

- **`[PLUGIN]…`** — Plugin(s) to remove

## Flags [​](https://mise.jdx.dev/cli/plugins/uninstall.html\#flags)

- **`-a --all`** — Remove all plugins
- **`-p --purge`** — Also remove the plugin's installs, downloads, and cache
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/plugins/uninstall.html\#examples)

```
mise plugins uninstall my-tool
```

## Related documentation [​](https://mise.jdx.dev/cli/plugins/uninstall.html\#related-documentation)

- [Plugin selection and maintenance](https://mise.jdx.dev/plugin-usage.html).
- [`mise plugins [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/plugins.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)