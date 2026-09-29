[Skip to content](https://mise.jdx.dev/cli/tasks/ls.html#VPContent)

On this page

# `mise tasks ls` [​](https://mise.jdx.dev/cli/tasks/ls.html\#mise-tasks-ls)

- **Usage:**`mise tasks ls [FLAGS]`
- **Effect:** read-only
- **Source code:** [`src/cli/tasks/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/tasks/ls.rs)

List available tasks

Tasks come from config files and from task directories such as `.mise/tasks`. Tasks from all parent directories are merged into this list.

So if you have global tasks in `~/.config/mise/tasks/*` and project-specific tasks in ~/myproject/.mise/tasks/\*, then they'll both be available but the project-specific tasks will override the global ones if they have the same name.

## Flags [​](https://mise.jdx.dev/cli/tasks/ls.html\#flags)

- **`-g --global`** — Only show global tasks

- **`-J --json`** — Output in JSON format

- **`-l --local`** — Only show non-global tasks

- **`-x --extended`** — Show all columns

- **`--all`** — Load all tasks from the entire monorepo, including sibling directories. By default, only tasks from the current directory hierarchy are loaded.

- **`--hidden`** — Show hidden tasks

- **`--name-only`** — Only show task names, one per line. Useful for piping to fzf and similar tools.

- **`--no-header`** — Do not print table header

- **`--sort <COLUMN>`** — Sort by column. Default is name.

**Choices:**`name`, `alias`, `description`, `source`

- **`--sort-order <SORT_ORDER>`** — Sort order. Default is asc.

**Choices:**`asc`, `desc`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/tasks/ls.html\#examples)

```
mise tasks ls
```

## Related documentation [​](https://mise.jdx.dev/cli/tasks/ls.html\#related-documentation)

- [Task configuration](https://mise.jdx.dev/tasks/task-configuration.html).
- [`mise tasks [FLAGS] [TASK] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tasks.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)