[Skip to content](https://mise.jdx.dev/cli/generate/git-pre-commit.html#VPContent)

On this page

# `mise generate git-pre-commit` [​](https://mise.jdx.dev/cli/generate/git-pre-commit.html\#mise-generate-git-pre-commit)

- **Usage:**`mise generate git-pre-commit [FLAGS] [-- MISE_ARG]…`
- **Aliases:**`pre-commit`
- **Effect:** modifies state
- **Source code:** [`src/cli/generate/git_pre_commit.rs`](https://github.com/jdx/mise/blob/main/src/cli/generate/git_pre_commit.rs)

Generate a git pre-commit hook

This command generates a git pre-commit hook that runs a mise task like `mise run pre-commit` when you commit changes to your repository.

Staged files are passed to the task as `STAGED`.

Hooks that git hands a message file — `commit-msg`, `prepare-commit-msg`, `applypatch-msg` and `sendemail-validate` — pass that file to the task. git's other arguments are not forwarded, so a `pre-push` hook's remote name and URL are not appended to the task's command.

For more advanced pre-commit functionality, see mise's sister project: [https://hk.jdx.dev/](https://hk.jdx.dev/)

## Arguments [​](https://mise.jdx.dev/cli/generate/git-pre-commit.html\#arguments)

- **`[-- MISE_ARG]…`** — mise flags to embed in the generated hook, given after `--`

These are inserted between `mise` and `run`, so the hook carries the same context you would pass on the command line. Useful when the config is not at the repository root, since git runs hooks from the top level: `-- -C subdir` makes the hook find it.


## Flags [​](https://mise.jdx.dev/cli/generate/git-pre-commit.html\#flags)

- **`-t --task <TASK>`** — The task to run when the pre-commit hook is triggered

**Default:**`pre-commit`

- **`-w --write`** — Write to .git/hooks/pre-commit and make it executable

- **`--hook <HOOK>`** — Which hook to generate (saves to .git/hooks/$hook)

**Default:**`pre-commit`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/generate/git-pre-commit.html\#examples)

Install the hook; committing then runs `mise run pre-commit`.

```
mise generate git-pre-commit --write --task=pre-commit
git commit -m "feat: add new feature"
```

config lives in a subdirectory, so the hook has to change into it first

```
mise generate git-pre-commit --write -- -C subdir
```

## Related documentation [​](https://mise.jdx.dev/cli/generate/git-pre-commit.html\#related-documentation)

- [Tasks and automation](https://mise.jdx.dev/tasks/).
- [`mise generate <SUBCOMMAND>`](https://mise.jdx.dev/cli/generate.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)