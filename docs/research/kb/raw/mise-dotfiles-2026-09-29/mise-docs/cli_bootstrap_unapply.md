[Skip to content](https://mise.jdx.dev/cli/bootstrap/unapply.html#VPContent)

On this page

# `mise bootstrap unapply` [​](https://mise.jdx.dev/cli/bootstrap/unapply.html\#mise-bootstrap-unapply)

- **Usage:**`mise bootstrap unapply [FLAGS] <ENV>…`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Remove the resources a config environment contributes

Remove managed files, directories, user services, and dotfile entries and edits contributed by the named environments. Environments are selected for this command even if they are no longer in your normal selection.

Removal uses the current configuration, not a history of bootstrap runs. Keep the environment files on disk until cleanup is complete. Resources still declared present elsewhere are kept, as are changed targets unless `--force` is given. Directories must be empty after the planned removals; source files and configuration entries are preserved.

Use `--dry-run` to preview the plan. Removal requires confirmation unless `--yes` or mise's `yes` setting is enabled, including in CI.

Packages, repositories, and Compose projects require separate cleanup; the output provides guidance for those declarations. Other bootstrap sections, including system services, are outside this command's scope.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/unapply.html\#arguments)

- **`<ENV>…`** — Config environment(s) whose resources should be removed

## Flags [​](https://mise.jdx.dev/cli/bootstrap/unapply.html\#flags)

- **`-f --force`** — Remove targets that changed since they were applied
- **`-n --dry-run`** — Print what would be removed without removing anything
- **`-y --yes`** — Skip the confirmation prompt
- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/bootstrap/unapply.html\#examples)

```
mise bootstrap unapply ssh --dry-run
mise bootstrap unapply ssh
mise bootstrap unapply ssh gpg --yes
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/unapply.html\#related-documentation)

- [Bootstrap workflow](https://mise.jdx.dev/bootstrap.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)