[Skip to content](https://mise.jdx.dev/cli/doctor/project.html#VPContent)

On this page

# `mise doctor project` [​](https://mise.jdx.dev/cli/doctor/project.html\#mise-doctor-project)

- **Usage:**`mise doctor project [-J --json]`
- **Source code:** [`src/cli/doctor/project.rs`](https://github.com/jdx/mise/blob/main/src/cli/doctor/project.rs)

Run the project's diagnostic checks

Checks are declared in \[doctor.checks.<name>\] in mise.toml. Each command runs with the project's installed tools and environment. Checks should inspect state; mise does not sandbox them or run their suggested remedies.

## Flags [​](https://mise.jdx.dev/cli/doctor/project.html\#flags)

- **`-J --json`** — Output the complete report as JSON
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/doctor/project.html\#related-documentation)

- [Project diagnostics](https://mise.jdx.dev/configuration/project-diagnostics.html).
- [`mise doctor [-J --json] [SUBCOMMAND]`](https://mise.jdx.dev/cli/doctor.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)