[Skip to content](https://mise.jdx.dev/cli/latest.html#VPContent)

On this page

# `mise latest` [​](https://mise.jdx.dev/cli/latest.html\#mise-latest)

- **Usage:**`mise latest [-i --installed] [--minimum-release-age <MINIMUM_RELEASE_AGE>] <TOOL@VERSION>`
- **Effect:** read-only
- **Source code:** [`src/cli/latest.rs`](https://github.com/jdx/mise/blob/main/src/cli/latest.rs)

Resolve the latest matching version request for a tool

Supports prefixes such as `node@20`. The selected backend decides how channels, refs, and non-SemVer versions resolve; "latest" is not a generic sort of strings. This prints a version without installing it or changing configuration.

## Arguments [​](https://mise.jdx.dev/cli/latest.html\#arguments)

- **`<TOOL@VERSION>`** — Tool to get the latest version of

## Flags [​](https://mise.jdx.dev/cli/latest.html\#flags)

- **`-i --installed`** — Show latest installed instead of available version

- **`--minimum-release-age <MINIMUM_RELEASE_AGE>`** — Only consider versions released before this date or older than this duration

Supports absolute dates like "2024-06-01" and relative durations like "90d" or "1y". Overrides per-tool `minimum_release_age` options and the global `minimum_release_age` setting.

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/latest.html\#examples)

Resolve a Node 20 release, or the backend's latest stable release

```
mise latest node@20
mise latest node
```

Restrict resolution to installed versions

```
mise latest node@20 --installed
```

Exclude releases newer than the requested age

```
mise latest node --minimum-release-age 30d
```

## Related documentation [​](https://mise.jdx.dev/cli/latest.html\#related-documentation)

- [Version requests](https://mise.jdx.dev/dev-tools/).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)