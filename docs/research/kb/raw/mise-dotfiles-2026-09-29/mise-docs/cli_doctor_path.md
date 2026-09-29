[Skip to content](https://mise.jdx.dev/cli/doctor/path.html#VPContent)

On this page

# `mise doctor path` [​](https://mise.jdx.dev/cli/doctor/path.html\#mise-doctor-path)

- **Usage:**`mise doctor path [-f --full]`
- **Aliases:**`paths`
- **Effect:** read-only
- **Source code:** [`src/cli/doctor/path.rs`](https://github.com/jdx/mise/blob/main/src/cli/doctor/path.rs)

Print the current PATH entries mise is providing

## Flags [​](https://mise.jdx.dev/cli/doctor/path.html\#flags)

- **`-f --full`** — Print all entries including those not provided by mise
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/doctor/path.html\#examples)

Get the PATH entries mise provides, such as `/home/user/.local/share/mise/installs/node/24.0.0/bin`, `/home/user/.local/share/mise/installs/rust/1.90.0/bin`, and `/home/user/.local/share/mise/installs/python/3.10.0/bin`.

```
mise doctor path
```

## Related documentation [​](https://mise.jdx.dev/cli/doctor/path.html\#related-documentation)

- [Troubleshooting](https://mise.jdx.dev/troubleshooting.html).
- [`mise doctor [-J --json] [SUBCOMMAND]`](https://mise.jdx.dev/cli/doctor.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)