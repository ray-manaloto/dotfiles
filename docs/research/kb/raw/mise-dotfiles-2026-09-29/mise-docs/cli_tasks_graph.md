[Skip to content](https://mise.jdx.dev/cli/tasks/graph.html#VPContent)

On this page

# `mise tasks graph` [​](https://mise.jdx.dev/cli/tasks/graph.html\#mise-tasks-graph)

- **Usage:**`mise tasks graph [FLAGS]`
- **Effect:** read-only
- **Source code:** [`src/cli/tasks/graph.rs`](https://github.com/jdx/mise/blob/main/src/cli/tasks/graph.rs)

\[experimental\] Inspect the workspace project graph

## Flags [​](https://mise.jdx.dev/cli/tasks/graph.html\#flags)

- **`-J --json`** — Output the project graph as JSON
- **`--explain`** — Explain provider attribution for inferred projects and tasks
- **`--no-header`** — Do not print table headers
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tasks/graph.html\#examples)

Inspect projects and their dependency edges

```
mise tasks graph
```

Emit the project graph as JSON

```
mise tasks graph --json
```

Explain where inferred projects and task fields came from

```
mise tasks graph --explain
```

## Related documentation [​](https://mise.jdx.dev/cli/tasks/graph.html\#related-documentation)

- [Monorepo projects](https://mise.jdx.dev/tasks/monorepo.html).
- [`mise tasks [FLAGS] [TASK] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tasks.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)