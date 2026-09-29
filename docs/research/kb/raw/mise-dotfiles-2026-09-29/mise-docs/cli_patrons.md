[Skip to content](https://mise.jdx.dev/cli/patrons.html#VPContent)

On this page

# `mise patrons` [​](https://mise.jdx.dev/cli/patrons.html\#mise-patrons)

- **Usage:**`mise patrons [-J --json] [--refresh]`
- **Effect:** read-only
- **Source code:** [`src/cli/patrons.rs`](https://github.com/jdx/mise/blob/main/src/cli/patrons.rs)

Show the individuals supporting mise as Patron-tier members

Lists the individuals on the Patron tier from [https://jdx.dev/patrons.json](https://jdx.dev/patrons.json). The list refreshes daily; supporting terminals will render each patron's name as a clickable link via OSC 8 hyperlinks.

To appear here, become a patron at [https://jdx.dev/sponsors.html](https://jdx.dev/sponsors.html).

## Flags [​](https://mise.jdx.dev/cli/patrons.html\#flags)

- **`-J --json`** — Output in JSON format
- **`--refresh`** — Bypass the local cache and re-fetch
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/patrons.html\#examples)

```
mise patrons
mise patrons -J
mise patrons --refresh
```

## Related documentation [​](https://mise.jdx.dev/cli/patrons.html\#related-documentation)

- [Supporting mise](https://mise.jdx.dev/about.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)