[Skip to content](https://mise.jdx.dev/cli/tasks/deps.html#VPContent)

On this page

# `mise tasks deps` [​](https://mise.jdx.dev/cli/tasks/deps.html\#mise-tasks-deps)

- **Usage:**`mise tasks deps [FLAGS] [TASKS]…`
- **Effect:** read-only
- **Source code:** [`src/cli/tasks/deps.rs`](https://github.com/jdx/mise/blob/main/src/cli/tasks/deps.rs)

Display a tree visualization of a dependency graph

The graph is built from declared dependencies: `depends`, `depends_post`, and `wait_for`. Task references inside a `run` or `run_windows` array (`{ task = "..." }` or `{ tasks = [...] }`) are execution steps, not graph edges, so they do not appear here. Those nested tasks still run, including their own `depends`.

## Arguments [​](https://mise.jdx.dev/cli/tasks/deps.html\#arguments)

- **`[TASKS]…`** — Tasks to show dependencies for Can specify multiple tasks by separating with spaces e.g.: mise tasks deps lint test check

## Flags [​](https://mise.jdx.dev/cli/tasks/deps.html\#flags)

- **`--compact`** — Collapse repeated dependencies after their first occurrence
- **`--dot`** — Display dependencies in DOT format
- **`--hidden`** — Show hidden tasks
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tasks/deps.html\#examples)

Show dependencies for all tasks

```
mise tasks deps
```

Show dependencies for the "lint", "test" and "check" tasks

```
mise tasks deps lint test check
```

Show dependencies in DOT format

```
mise tasks deps --dot
```

Collapse repeated dependencies

```
mise tasks deps --compact
```

## Related documentation [​](https://mise.jdx.dev/cli/tasks/deps.html\#related-documentation)

- [Task dependency graph](https://mise.jdx.dev/tasks/architecture.html).
- [`mise tasks [FLAGS] [TASK] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tasks.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)