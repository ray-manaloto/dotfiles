[Skip to content](https://mise.jdx.dev/cli/token/forgejo.html#VPContent)

On this page

# `mise token forgejo` [​](https://mise.jdx.dev/cli/token/forgejo.html\#mise-token-forgejo)

- **Usage:**`mise token forgejo [--unmask] [HOST]`
- **Effect:** read-only
- **Source code:** [`src/cli/token/forgejo.rs`](https://github.com/jdx/mise/blob/main/src/cli/token/forgejo.rs)

Display the Forgejo token mise will use for a given host

Shows which token source mise would use, useful for debugging authentication issues. The token is masked by default.

## Arguments [​](https://mise.jdx.dev/cli/token/forgejo.html\#arguments)

- **`[HOST]`** — Forgejo hostname

**Default:**`codeberg.org`


## Flags [​](https://mise.jdx.dev/cli/token/forgejo.html\#flags)

- **`--unmask`** — Show the full unmasked token
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/token/forgejo.html\#examples)

```
mise token forgejo
codeberg.org: a180…61f6 (source: FORGEJO_TOKEN)
```

```
mise token forgejo --unmask
codeberg.org: a18099ca69064be387fbe37b8ad1d333758361f6 (source: FORGEJO_TOKEN)
```

```
mise token forgejo forgejo.mycompany.com
forgejo.mycompany.com: (none)
```

## Related documentation [​](https://mise.jdx.dev/cli/token/forgejo.html\#related-documentation)

- [Git provider authentication](https://mise.jdx.dev/dev-tools/github-tokens.html).
- [`mise token <SUBCOMMAND>`](https://mise.jdx.dev/cli/token.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)