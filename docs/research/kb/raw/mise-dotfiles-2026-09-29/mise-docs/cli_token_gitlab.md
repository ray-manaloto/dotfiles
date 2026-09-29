[Skip to content](https://mise.jdx.dev/cli/token/gitlab.html#VPContent)

On this page

# `mise token gitlab` [​](https://mise.jdx.dev/cli/token/gitlab.html\#mise-token-gitlab)

- **Usage:**`mise token gitlab [--unmask] [HOST]`
- **Effect:** read-only
- **Source code:** [`src/cli/token/gitlab.rs`](https://github.com/jdx/mise/blob/main/src/cli/token/gitlab.rs)

Display the GitLab token mise will use for a given host

Shows which token source mise would use, useful for debugging authentication issues. The token is masked by default.

## Arguments [​](https://mise.jdx.dev/cli/token/gitlab.html\#arguments)

- **`[HOST]`** — GitLab hostname

**Default:**`gitlab.com`


## Flags [​](https://mise.jdx.dev/cli/token/gitlab.html\#flags)

- **`--unmask`** — Show the full unmasked token
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/token/gitlab.html\#examples)

```
mise token gitlab
gitlab.com: glpa…xxxx (source: GITLAB_TOKEN)
```

```
mise token gitlab --unmask
gitlab.com: glpat-xxxxxxxxxxxx (source: GITLAB_TOKEN)
```

```
mise token gitlab gitlab.mycompany.com
gitlab.mycompany.com: (none)
```

## Related documentation [​](https://mise.jdx.dev/cli/token/gitlab.html\#related-documentation)

- [Git provider authentication](https://mise.jdx.dev/dev-tools/github-tokens.html).
- [`mise token <SUBCOMMAND>`](https://mise.jdx.dev/cli/token.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)