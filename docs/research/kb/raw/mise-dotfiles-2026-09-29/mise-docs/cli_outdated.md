[Skip to content](https://mise.jdx.dev/cli/outdated.html#VPContent)

On this page

# `mise outdated` [​](https://mise.jdx.dev/cli/outdated.html\#mise-outdated)

- **Usage:**`mise outdated [FLAGS] [TOOL@VERSION]…`
- **Effect:** read-only
- **Source code:** [`src/cli/outdated.rs`](https://github.com/jdx/mise/blob/main/src/cli/outdated.rs)

Show outdated tool versions

See `mise upgrade` to upgrade these versions.

## Arguments [​](https://mise.jdx.dev/cli/outdated.html\#arguments)

- **`[TOOL@VERSION]…`** — Tool(s) to show outdated versions for e.g.: node@20 python@3.10 If not specified, all tools in global and local configs will be shown

## Flags [​](https://mise.jdx.dev/cli/outdated.html\#flags)

- **`-b --bump`** — Compare against the latest versions available, not just those matching the current config

For example, with `node = "20"` in your config, `mise outdated` normally only reports newer 20.x versions. With this flag it reports the newest version overall, such as 22.x.

- **`-J --json`** — Output in JSON format

- **`--inactive`** — Show outdated tools including installed-but-inactive tools not present in the current config

By default, `mise outdated` only shows tools that come from the current config.

- **`--local`** — Only show outdated tools defined in local config files

This will only show tools that are defined in project-local mise.toml and will skip tools defined in the global config (~/.config/mise/config.toml).

- **`--monorepo`** — Placeholder for future monorepo outdated checks; `mise outdated --monorepo` is not implemented yet.

- **`--no-header`** — Don't show table header

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/outdated.html\#examples)

```
mise outdated
Plugin  Requested  Current  Latest
python  3.11       3.11.0   3.11.1
node    20         20.0.0   20.1.0
```

```
mise outdated node
Plugin  Requested  Current  Latest
node    20         20.0.0   20.1.0
```

```
mise outdated --json
{"python": {"requested": "3.11", "current": "3.11.0", "latest": "3.11.1"}, ...}
```

```
mise outdated --local
Plugin  Requested  Current  Latest
node    20         20.0.0   20.1.0
```

Deprecation:

The `-l` shorthand for `--bump` is deprecated and will be removed in mise 2027.8.5. After removal, `-l` will become shorthand for `--local`. Use `-b` or `--bump` instead.

## Related documentation [​](https://mise.jdx.dev/cli/outdated.html\#related-documentation)

- [Upgrading tools](https://mise.jdx.dev/dev-tools/).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)