[Skip to content](https://mise.jdx.dev/cli/bootstrap/plan.html#VPContent)

On this page

# `mise bootstrap plan` [​](https://mise.jdx.dev/cli/bootstrap/plan.html\#mise-bootstrap-plan)

- **Usage:**`mise bootstrap plan [FLAGS]`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Show the changes declarative bootstrap resources would make

Covers declarative resources, not every hook, package installation, or task in a full bootstrap run. Use `bootstrap --dry-run` to preview the complete workflow. `--detailed-exitcode` distinguishes unchanged (0), changes (2), and errors (1).

## Flags [​](https://mise.jdx.dev/cli/bootstrap/plan.html\#flags)

- **`-J --json`** — Output a stable machine-readable plan in JSON format
- **`--detailed-exitcode`** — Exit 2 when the plan contains changes, 0 when unchanged, and 1 on errors
- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/plan.html\#related-documentation)

- [Bootstrap workflow](https://mise.jdx.dev/bootstrap.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)