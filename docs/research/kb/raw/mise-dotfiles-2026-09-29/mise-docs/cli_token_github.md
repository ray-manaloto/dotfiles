[Skip to content](https://mise.jdx.dev/cli/token/github.html#VPContent)

On this page

# `mise token github` [​](https://mise.jdx.dev/cli/token/github.html\#mise-token-github)

- **Usage:**`mise token github [FLAGS] [HOST]`
- **Effect:** read-only
- **Source code:** [`src/cli/token/github.rs`](https://github.com/jdx/mise/blob/main/src/cli/token/github.rs)

Display the GitHub token mise will use for a given host

Shows which token source mise would use, useful for debugging authentication issues. The token is masked by default.

## Arguments [​](https://mise.jdx.dev/cli/token/github.html\#arguments)

- **`[HOST]`** — GitHub hostname

**Default:**`github.com`


## Flags [​](https://mise.jdx.dev/cli/token/github.html\#flags)

- **`--oauth`** — Resolve only via the native GitHub OAuth source (cache, refresh, or device-code flow), bypassing other token sources
- **`--raw`** — Print only the token value
- **`--refresh`** — Mint a fresh OAuth token even if the cached one has not expired, via the refresh-token grant or a new device-code flow. Use after changing the GitHub App's installations or permissions: cached tokens keep their original access until they expire
- **`--unmask`** — Show the full unmasked token
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/token/github.html\#examples)

```
mise token github
github.com: ghp_…xxxx (source: GITHUB_TOKEN)
```

```
mise token github --unmask
github.com: ghp_xxxxxxxxxxxx (source: GITHUB_TOKEN)
```

```
mise token github github.mycompany.com
github.mycompany.com: (none)
```

```
mise token github --oauth --refresh
github.com: gho_…xxxx (source: GitHub OAuth)
```

## Related documentation [​](https://mise.jdx.dev/cli/token/github.html\#related-documentation)

- [Git provider authentication](https://mise.jdx.dev/dev-tools/github-tokens.html).
- [`mise token <SUBCOMMAND>`](https://mise.jdx.dev/cli/token.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)