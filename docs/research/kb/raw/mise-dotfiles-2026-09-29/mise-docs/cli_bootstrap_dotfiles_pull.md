[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/pull.html#VPContent)

On this page

# `mise bootstrap dotfiles pull` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/pull.html\#mise-bootstrap-dotfiles-pull)

- **Usage:**`mise bootstrap dotfiles pull [FLAGS] [PATH]…`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/dotfiles/pull.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/pull.rs)

Pull incoming shared changes into the live files

Writes the changes the last `mise dot sync` recorded as pending (`apply` keeps deploying your own `[dotfiles]` declarations; `pull` writes what other machines shared), as one recoverable transaction: a protective checkpoint first, every file written and journaled one at a time, reload hooks only afterwards, and `mise dot undo` to reverse it. Configuration and the sources it references apply together; an incoming configuration file that does not parse, a path with unsaved local edits, staged git changes in your own checkout, or a genuine local edit pauses the complete application. Conflicts pause both publication and application for the whole setup; local history and fetching continue. Decisions are recorded per path with `--take-remote` or `--keep-local`; sharing resumes only after all conflicts are resolved and the plan has been recomputed.

In `sync` mode the watcher pulls conflict-free setups on its own; this command writes what is pending right now and decides conflicts. When an incoming configuration declares more tracked files, their shared versions follow in the same run.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/pull.html\#arguments)

- **`[PATH]…`** — Partial pulls are unsupported; omit PATH and apply the complete setup

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/pull.html\#flags)

- **`-n --dry-run`** — Show the plan without changing anything

- **`-y --yes`** — Pull without prompting

- **`--take-remote <PATH>`** — Resolve a conflict with the repository's version

- **`--keep-local <PATH>`** — Resolve a conflict by keeping this machine's version (published next)

- **`--take-remote-all`** — Resolve every remaining conflict with the repository's version

Paths named by --keep-local keep this machine's version; every other conflict takes the repository's. Useful on a newly adopted machine, where each pre-existing file that differs is a separate conflict.

- **`--keep-local-all`** — Resolve every remaining conflict by keeping this machine's version

Paths named by --take-remote take the repository's version; every other conflict keeps this machine's. Each kept path must already be saved.

- **`-h --help`** — Print help


Examples:

```
mise dot pull --dry-run
mise dot pull --yes
mise dot pull --take-remote ~/.zshrc
mise dot pull --keep-local ~/.zshrc
mise dot pull --take-remote-all
mise dot pull --take-remote-all --keep-local ~/.zshrc
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/pull.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)