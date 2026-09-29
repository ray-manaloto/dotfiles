[Skip to content](https://mise.jdx.dev/cli/generate/task-stubs.html#VPContent)

On this page

# `mise generate task-stubs` [​](https://mise.jdx.dev/cli/generate/task-stubs.html\#mise-generate-task-stubs)

- **Usage:**`mise generate task-stubs [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/generate/task_stubs.rs`](https://github.com/jdx/mise/blob/main/src/cli/generate/task_stubs.rs)

Generate shims to run mise tasks

By default, this will build shims like ./bin/<task>. These can be paired with `mise generate install-script` so contributors to a project can execute mise tasks without installing mise into their system. When a parent and nested task both exist, the parent stub is written to `<parent>/_default`.

## Flags [​](https://mise.jdx.dev/cli/generate/task-stubs.html\#flags)

- **`-d --dir <DIR>`** — Directory to create task stubs inside of

**Default:**`bin`

- **`-m --mise-bin <MISE_BIN>`** — Path to a mise bin to use when running the task stub.

Use `--mise-bin=./bin/mise` to use a mise bin generated from `mise generate install-script`

On Windows a path is run as written, so that script needs its own launcher beside it: generate it with `mise generate install-script --write ./bin/mise --windows`. The default `mise` is a bare name and resolves off PATH, which needs nothing extra.

**Default:**`mise`

- **`--windows-launcher <WINDOWS_LAUNCHER>`** — What to write beside each stub for Windows to launch

`cmd` writes `<task>.cmd`. cmd.exe re-parses the whole line before `%*` expands, so an argument containing `& ^ | " %VAR%` does not reach the task intact when the launcher is called from PowerShell.

`exe` writes a native `<task>.exe` instead, which receives its arguments unchanged from every shell. It is a copy of the mise-shim.exe that ships with the Windows build, so it can only be generated on Windows, and it adds ~220KB per task to a directory that is normally committed.

**Choices:**`cmd`, `exe`

**Default:**`cmd`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/generate/task-stubs.html\#examples)

```
mise tasks add test -- echo 'running tests'
mise generate task-stubs
./bin/test
running tests
```

## Related documentation [​](https://mise.jdx.dev/cli/generate/task-stubs.html\#related-documentation)

- [Tasks and automation](https://mise.jdx.dev/tasks/).
- [`mise generate <SUBCOMMAND>`](https://mise.jdx.dev/cli/generate.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)