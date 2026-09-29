[Skip to content](https://mise.jdx.dev/cli/deps/install.html#VPContent)

On this page

# `mise deps install` [​](https://mise.jdx.dev/cli/deps/install.html\#mise-deps-install)

- **Usage:**`mise deps install [FLAGS] [PROVIDER]`
- **Effect:** modifies state
- **Source code:** [`src/cli/deps/install.rs`](https://github.com/jdx/mise/blob/main/src/cli/deps/install.rs)

Install all project dependencies

Uses each provider's freshness rules to compare configured inputs and outputs, then runs its installation command when needed. `--force` bypasses that check; `--explain PROVIDER` shows why a provider is considered fresh or stale.

## Arguments [​](https://mise.jdx.dev/cli/deps/install.html\#arguments)

- **`[PROVIDER]`** — Provider to operate on (runs only this provider, or use with --explain)

## Flags [​](https://mise.jdx.dev/cli/deps/install.html\#flags)

- **`--explain`** — Show why a provider is fresh or stale (requires a provider argument)

- **`-f --force`** — Force run all deps steps even if outputs are fresh

- **`-n --dry-run`** — Only check if deps install is needed, don't run commands

- **`--list`** — Show what deps providers are available

- **`--monorepo`** — Install dependencies from every \[monorepo\].config\_roots config root

Requires monorepo\_root = true plus explicit \[monorepo\].config\_roots in the monorepo root config. Providers are named like //apps/api:uv.

**Environment Variable:**`MISE_MONOREPO`

- **`--only <ONLY>`** — Run specific deps rule(s) only

- **`--skip <SKIP>`** — Skip specific deps rule(s)

- **`-h --help`** — Print help


## Related documentation [​](https://mise.jdx.dev/cli/deps/install.html\#related-documentation)

- [Project dependencies](https://mise.jdx.dev/dev-tools/deps.html).
- [`mise deps [FLAGS] [PROVIDER] [SUBCOMMAND]`](https://mise.jdx.dev/cli/deps.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)