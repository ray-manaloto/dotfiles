[Skip to content](https://mise.jdx.dev/cli/doctor.html#VPContent)

On this page

# `mise doctor` [​](https://mise.jdx.dev/cli/doctor.html\#mise-doctor)

- **Usage:**`mise doctor [-J --json] [SUBCOMMAND]`
- **Aliases:**`dr`
- **Effect:** read-only
- **Source code:** [`src/cli/doctor/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/doctor/mod.rs)

Check mise installation for possible problems

## Flags [​](https://mise.jdx.dev/cli/doctor.html\#flags)

- **`-J --json`** — Output in JSON format
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/doctor.html\#examples)

```
mise doctor
mise doctor --json
mise doctor path --full
```

## Subcommands [​](https://mise.jdx.dev/cli/doctor.html\#subcommands)

- [`mise doctor path [-f --full]`](https://mise.jdx.dev/cli/doctor/path.html)
- [`mise doctor project [-J --json]`](https://mise.jdx.dev/cli/doctor/project.html)

## Related documentation [​](https://mise.jdx.dev/cli/doctor.html\#related-documentation)

- [Troubleshooting](https://mise.jdx.dev/troubleshooting.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)