[Skip to content](https://mise.jdx.dev/cli/tasks/info.html#VPContent)

On this page

# `mise tasks info` [​](https://mise.jdx.dev/cli/tasks/info.html\#mise-tasks-info)

- **Usage:**`mise tasks info [-J --json] <TASK>`
- **Effect:** read-only
- **Source code:** [`src/cli/tasks/info.rs`](https://github.com/jdx/mise/blob/main/src/cli/tasks/info.rs)

Get information about a task

## Arguments [​](https://mise.jdx.dev/cli/tasks/info.html\#arguments)

- **`<TASK>`** — Name of the task to get information about

## Flags [​](https://mise.jdx.dev/cli/tasks/info.html\#flags)

- **`-J --json`** — Output in JSON format
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tasks/info.html\#examples)

Inspect the selected definition and its source file

```
mise tasks info test
```

Get the full structured task definition

```
mise tasks info test --json
```

## Related documentation [​](https://mise.jdx.dev/cli/tasks/info.html\#related-documentation)

- [Task configuration](https://mise.jdx.dev/tasks/task-configuration.html).
- [`mise tasks [FLAGS] [TASK] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tasks.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).