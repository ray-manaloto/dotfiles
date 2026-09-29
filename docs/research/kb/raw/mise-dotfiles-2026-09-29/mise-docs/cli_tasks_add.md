[Skip to content](https://mise.jdx.dev/cli/tasks/add.html#VPContent)

On this page

# `mise tasks add` [​](https://mise.jdx.dev/cli/tasks/add.html\#mise-tasks-add)

- **Usage:**`mise tasks add [FLAGS] <TASK> [-- RUN]…`
- **Effect:** modifies state
- **Source code:** [`src/cli/tasks/add.rs`](https://github.com/jdx/mise/blob/main/src/cli/tasks/add.rs)

Create a new task

Adds a task to the local mise.toml file. See [https://mise.jdx.dev/configuration.html#target-file-for-write-operations](https://mise.jdx.dev/configuration.html#target-file-for-write-operations)

## Arguments [​](https://mise.jdx.dev/cli/tasks/add.html\#arguments)

- **`<TASK>`** — Name of the task to add
- **`[-- RUN]…`** — Command to run, given after `--`

## Flags [​](https://mise.jdx.dev/cli/tasks/add.html\#flags)

- **`-a --alias <ALIAS>`** — Other names for the task
- **`-d --depends <DEPENDS>`** — Add dependencies to the task
- **`-D --dir <DIR>`** — Run the task in a specific directory
- **`-f --file`** — Create a file task instead of a toml task
- **`-H --hide`** — Hide the task from `mise tasks` and completions
- **`-q --quiet`** — Do not print the command before running
- **`-r --raw`** — Directly connect stdin/stdout/stderr
- **`-s --sources <SOURCES>`** — Glob patterns of files this task uses as input
- **`-w --wait-for <WAIT_FOR>`** — Wait for these tasks to finish if they are also being run
- **`--depends-post <DEPENDS_POST>`** — Dependencies to run after the task runs
- **`--description <DESCRIPTION>`** — Description of the task
- **`--outputs <OUTPUTS>`** — Glob patterns of files this task creates, used to skip it when they are up to date
- **`--run-windows <RUN_WINDOWS>`** — Command to run on Windows
- **`--shell <SHELL>`** — Run the task in a specific shell
- **`--silent`** — Do not print the command or its output
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tasks/add.html\#examples)

```
mise tasks add pre-commit --depends "test" --depends "render" -- echo pre-commit
```

## Related documentation [​](https://mise.jdx.dev/cli/tasks/add.html\#related-documentation)

- [TOML tasks](https://mise.jdx.dev/tasks/toml-tasks.html).
- [`mise tasks [FLAGS] [TASK] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tasks.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)