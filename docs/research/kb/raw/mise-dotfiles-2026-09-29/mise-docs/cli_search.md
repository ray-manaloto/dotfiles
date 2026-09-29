[Skip to content](https://mise.jdx.dev/cli/search.html#VPContent)

On this page

# `mise search` [​](https://mise.jdx.dev/cli/search.html\#mise-search)

- **Usage:**`mise search [FLAGS] [NAME]`
- **Effect:** read-only
- **Source code:** [`src/cli/search.rs`](https://github.com/jdx/mise/blob/main/src/cli/search.rs)

Search for available tools

Searches the registry and installed backend catalogs for tools matching NAME.

Prefix NAME with a backend to also search that backend's package registry: `npm:`, `cargo:`, `gem:`, or `dotnet:`. Use `--all` to search every backend, including all of those package registries. Otherwise, unprefixed searches do not query package registries.

By default, it will show all tools that fuzzy match the search term. For non-fuzzy matches, use the `--match-type` flag.

## Arguments [​](https://mise.jdx.dev/cli/search.html\#arguments)

- **`[NAME]`** — The tool to search for

## Flags [​](https://mise.jdx.dev/cli/search.html\#flags)

- **`-a --all`** — Search every backend: the registry, aqua, installed backend plugins, and the npm, cargo, gem, and dotnet package registries

- **`-i --interactive`** — Show an interactive search menu

- **`-m --match-type <MATCH_TYPE>`** — Match type: equal, contains, or fuzzy

**Choices:**`equal`, `contains`, `fuzzy`

**Default:**`fuzzy`

- **`--no-header`** — Don't display headers

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/search.html\#examples)

```
mise search jq
Tool  Description
jq    Command-line JSON processor. https://github.com/jqlang/jq
jqp   A TUI playground to experiment with jq. https://github.com/noahgorstein/jqp
jiq   jid on jq - interactive JSON query tool using jq expressions. https://github.com/fiatjaf/jiq
gojq  Pure Go implementation of jq. https://github.com/itchyny/gojq
```

```
mise search --match-type equal npm:typescript-language-server
Tool                            Description
npm:typescript-language-server  Language Server Protocol (LSP) implementation for TypeScript using tsserver
```

```
mise search --interactive
Tool
Search a tool
❯ jq    Command-line JSON processor. https://github.com/jqlang/jq
  jqp   A TUI playground to experiment with jq. https://github.com/noahgorstein/jqp
  jiq   jid on jq - interactive JSON query tool using jq expressions. https://github.com/fiatjaf/jiq
  gojq  Pure Go implementation of jq. https://github.com/itchyny/gojq
/jq
esc clear filter • enter confirm
```

## Related documentation [​](https://mise.jdx.dev/cli/search.html\#related-documentation)

- [Registry and explicit backends](https://mise.jdx.dev/registry.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)