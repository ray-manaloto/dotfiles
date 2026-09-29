[Skip to content](https://mise.jdx.dev/cli/bootstrap/repos/exec.html#VPContent)

On this page

# `mise bootstrap repos exec` [​](https://mise.jdx.dev/cli/bootstrap/repos/exec.html\#mise-bootstrap-repos-exec)

- **Usage:**`mise bootstrap repos exec [-c --continue-on-error] [-n --dry-run] [PATH]… <-- COMMAND>…`
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Run a command in each configured git repo

Place the executable and its arguments after `--`, for example `mise bootstrap repos exec -- git status --short`. Arguments before `--` select repository paths; use `--continue-on-error` to visit remaining repos after a failure.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/repos/exec.html\#arguments)

- **`[PATH]…`** — Run only in matching configured or expanded paths
- **`<-- COMMAND>…`** — Command and arguments to run in each repo

## Flags [​](https://mise.jdx.dev/cli/bootstrap/repos/exec.html\#flags)

- **`-c --continue-on-error`** — Continue running in other repos after a command fails
- **`-n --dry-run`** — Print the commands that would run without running them
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/repos/exec.html\#related-documentation)

- [Repository checkouts](https://mise.jdx.dev/bootstrap/repos.html).
- [`mise bootstrap repos <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/repos.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)