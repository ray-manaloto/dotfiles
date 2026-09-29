[Skip to content](https://mise.jdx.dev/cli/tasks/edit.html#VPContent)

On this page

# `mise tasks edit` [​](https://mise.jdx.dev/cli/tasks/edit.html\#mise-tasks-edit)

- **Usage:**`mise tasks edit [-p --path] <TASK>`
- **Effect:** modifies state
- **Source code:** [`src/cli/tasks/edit.rs`](https://github.com/jdx/mise/blob/main/src/cli/tasks/edit.rs)

Edit a task with $EDITOR

The task will be created as a standalone script if it does not already exist.

## Arguments [​](https://mise.jdx.dev/cli/tasks/edit.html\#arguments)

- **`<TASK>`** — Task to edit

## Flags [​](https://mise.jdx.dev/cli/tasks/edit.html\#flags)

- **`-p --path`** — Display the path to the task instead of editing it
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tasks/edit.html\#examples)

```
mise tasks edit build
mise tasks edit test
```

## Related documentation [​](https://mise.jdx.dev/cli/tasks/edit.html\#related-documentation)

- [File tasks](https://mise.jdx.dev/tasks/file-tasks.html).
- [`mise tasks [FLAGS] [TASK] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tasks.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)