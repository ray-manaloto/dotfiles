[Skip to content](https://mise.jdx.dev/cli/generate/task-docs.html#VPContent)

On this page

# `mise generate task-docs` [​](https://mise.jdx.dev/cli/generate/task-docs.html\#mise-generate-task-docs)

- **Usage:**`mise generate task-docs [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/generate/task_docs.rs`](https://github.com/jdx/mise/blob/main/src/cli/generate/task_docs.rs)

Generate Markdown documentation for project tasks

Prints to stdout by default. Use `--output` to write a file, `--inject` to replace a marked section, or `--multi` for one file per task.

## Flags [​](https://mise.jdx.dev/cli/generate/task-docs.html\#flags)

- **`-i --inject`** — Insert the documentation into an existing file

This will look for a special comment, `<!-- mise-tasks -->`, and replace it with the generated documentation. It will replace everything between the comment and the next comment, `<!-- /mise-tasks -->` so it can be run multiple times on the same file to update the documentation. The file must already contain both comments; mise errors instead of modifying the file if they are missing.

- **`-I --index`** — Write only an index of tasks, intended for use with `--multi`

- **`-m --multi`** — Render each task as a separate document; requires `--output` to be a directory

- **`-o --output <OUTPUT>`** — Write the generated docs to a file or directory

- **`-r --root <ROOT>`** — Root directory to search for tasks

- **`-s --style <STYLE>`** — Documentation style: `simple` lists tasks, `detailed` documents each task's usage

**Choices:**`simple`, `detailed`

**Default:**`simple`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/generate/task-docs.html\#examples)

```
mise generate task-docs --style detailed
mise generate task-docs --output TASKS.md
```

README.md must already contain both mise-tasks marker comments

```
mise generate task-docs --inject --output README.md
```

## Related documentation [​](https://mise.jdx.dev/cli/generate/task-docs.html\#related-documentation)

- [Tasks and automation](https://mise.jdx.dev/tasks/).
- [`mise generate <SUBCOMMAND>`](https://mise.jdx.dev/cli/generate.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)