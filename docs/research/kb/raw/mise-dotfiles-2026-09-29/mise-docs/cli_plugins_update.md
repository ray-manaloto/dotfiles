[Skip to content](https://mise.jdx.dev/cli/plugins/update.html#VPContent)

On this page

# `mise plugins update` [​](https://mise.jdx.dev/cli/plugins/update.html\#mise-plugins-update)

- **Usage:**`mise plugins update [-j --jobs <JOBS>] [PLUGIN]…`
- **Aliases:**`up`, `upgrade`
- **Effect:** modifies state
- **Source code:** [`src/cli/plugins/update.rs`](https://github.com/jdx/mise/blob/main/src/cli/plugins/update.rs)

Update a plugin to the latest version

With no names, updates every installed plugin. This updates plugin source, not the tool versions it manages. Linked local plugins are skipped; archive installations cannot be updated with Git.

## Arguments [​](https://mise.jdx.dev/cli/plugins/update.html\#arguments)

- **`[PLUGIN]…`** — Plugin(s) to update

## Flags [​](https://mise.jdx.dev/cli/plugins/update.html\#flags)

- **`-j --jobs <JOBS>`** — Number of jobs to run in parallel Values below 1 are treated as 1 Defaults to the `jobs` setting
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/plugins/update.html\#examples)

```
mise plugins update              # update all installed plugins
mise plugins update my-tool      # update one Git plugin
mise plugins update my-tool#main # select an upstream ref
```

## Related documentation [​](https://mise.jdx.dev/cli/plugins/update.html\#related-documentation)

- [Plugin selection and maintenance](https://mise.jdx.dev/plugin-usage.html).
- [`mise plugins [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/plugins.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)