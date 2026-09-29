[Skip to content](https://mise.jdx.dev/cli/plugins/link.html#VPContent)

On this page

# `mise plugins link` [​](https://mise.jdx.dev/cli/plugins/link.html\#mise-plugins-link)

- **Usage:**`mise plugins link [-f --force] <NAME> [DIR]`
- **Aliases:**`ln`
- **Effect:** modifies state
- **Source code:** [`src/cli/plugins/link.rs`](https://github.com/jdx/mise/blob/main/src/cli/plugins/link.rs)

Link a local plugin directory into mise for development

Edits in the source directory take effect without reinstalling the plugin. Pass both a name and directory, or only a directory to infer the name after stripping a known prefix such as `mise-` or `vfox-`. This does not install a tool version.

## Arguments [​](https://mise.jdx.dev/cli/plugins/link.html\#arguments)

- **`<NAME>`** — The name of the plugin With one argument, this is the plugin directory and the name is inferred
- **`[DIR]`** — The local path to the plugin e.g.: ./mise-my-tool

## Flags [​](https://mise.jdx.dev/cli/plugins/link.html\#flags)

- **`-f --force`** — Overwrite existing plugin
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/plugins/link.html\#examples)

```
mise plugins link my-tool ./mise-my-tool
```

Alternative: infer the name "my-tool"

```
mise plugins link ./mise-my-tool
```

List versions through the linked plugin

```
mise ls-remote my-tool
```

## Related documentation [​](https://mise.jdx.dev/cli/plugins/link.html\#related-documentation)

- [Developing tool plugins](https://mise.jdx.dev/tool-plugin-development.html).
- [`mise plugins [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/plugins.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)