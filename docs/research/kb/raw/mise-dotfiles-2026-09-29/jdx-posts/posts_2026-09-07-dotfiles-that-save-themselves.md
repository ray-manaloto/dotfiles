[Skip to content](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/#main)

On this page

`mise bootstrap` already supported two common ways of managing dotfiles: keep them in a repository and symlink them into place, as [GNU Stow](https://www.gnu.org/software/stow/) does, or generate the live files from stored sources and templates, as [chezmoi](https://www.chezmoi.io/user-guide/frequently-asked-questions/design/#why-doesnt-chezmoi-use-symlinks-like-gnu-stow) normally does.

I wanted to add a third model: **automatic bidirectional syncing of the files I already edit, without symlinks**. Change `.zshrc` on my laptop and mise saves it, shares it, and applies it on my desktop. Edit it on the desktop and the change flows back. The live files stay where they are, and I don’t have to remember to copy edits back into a source directory or run a sync command after each change.

That’s what I added to [`mise bootstrap`](https://mise.jdx.dev/bootstrap.html) in **mise 2026.9.2**. It works locally or with a remote origin server for automatic syncing.

## How is this different from yadm, Stow, or chezmoi? [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#how-is-this-different-from-yadm-stow-or-chezmoi)

The difference is what happens after you edit a file. **Auto** means a background process handles changes from any editor or app, without another command. **External** means bringing your own Git or sync workflow.

| Tool | Live files | Git history | Two-way sync |
| --- | --- | --- | --- |
| **mise** | **Regular** | **Auto** | **Auto** |
| [yadm](https://yadm.io/docs/getting_started) | Regular | Manual | Manual |
| [Stow](https://www.gnu.org/software/stow/) | Symlinks | External | External |
| [chezmoi](https://www.chezmoi.io/user-guide/setup/) | Generated | On command | Manual |
| [DotState](https://github.com/serkanyersen/dotstate) | Symlinks | On command | On command |
| [Dotbot](https://github.com/anishathalye/dotbot) | Symlinks | External | External |
| [Mackup](https://github.com/lra/mackup) | Copies / links | External | Cloud¹ |

¹ Mackup’s automatic cloud sync requires symlinks. Its copy mode uses explicit backup and restore commands.

yadm already lets you edit regular files in place. chezmoi can [automatically commit and push](https://www.chezmoi.io/reference/configuration-file/variables/#git) changes made through its commands.

## Tracking a file [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#tracking-a-file)

You can start with a file you already have:

```sh
$ mise dot track ~/.zshrc
dotfiles: track ~/.zshrc? [Y/n] y
mise dotfiles: tracking ~/.zshrc (declared in ~/.config/mise/config.toml)
mise history: saved baseline checkpoint 1
```

This saves the current file immediately and adds the following to `~/.config/mise/config.toml`. Your `.zshrc` stays where it is, as a regular file:

```toml
[dotfiles]
"~/.zshrc" = { mode = "track" }
```

To save future edits automatically, add the history watcher to the same config:

```toml
[bootstrap.services.mise-history]
builtin = "history-watch"
```

Then install and start the service:

```sh
mise bootstrap
mise dot status
```

mise handles the LaunchAgent on macOS, systemd user service on Linux, or Scheduled Task on Windows.

Then just edit `.zshrc` with any editor or agent. mise saves your changes automatically. On Unix, the history repository defaults to `~/.local/state/mise/history/repo.git`, so you don’t need symlinks or a `.git` directory in your home directory.

## Autosave, like a video game [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#autosave-like-a-video-game)

I think video games have the right idea here. Save automatically and let me pick an earlier save if I need it. I don’t want to decide whether every change to a keyboard shortcut deserves a commit.

Of course a saved config might be broken. Autosave records what the file looked like; it doesn’t test whether your configuration works. That’s why you have history.

Say I add this alias to `~/.zshrc` in my editor:

```sh
alias ll='ls -lah'
```

A couple of seconds later, the watcher has saved it. I can inspect the file’s history and roll it back:

```sh
mise dot history --path ~/.zshrc
mise dot rollback ~/.zshrc
```

The rollback returns `.zshrc` to its most recent saved version that differs from what’s on disk. In this example, it removes the alias I just added:

```diff
-alias ll='ls -lah'
```

You can preview with `--dry-run` or select a particular checkpoint with `--to`.

Before replacing anything, mise saves the current contents. To reverse the rollback:

```sh
mise dot undo
```

That puts the alias back. Undo affects the files from that operation, not everything you’ve edited since.

## Share saved changes [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#share-saved-changes)

Everything so far stays on this machine. To share it with your other machines, create a repository and connect it. Use your own URL here, with Git credentials available to the watcher:

```sh
mise dot origin set git@github.com:jdx/dotfiles.git
```

mise previews what will leave the machine and asks whether to enable automatic sharing. The configured default is `sync`: the watcher publishes saved changes and periodically fetches and applies updates from your other machines. Pass `--sync manual` when connecting if you want autosaves to stay local until you explicitly sync. The [sharing documentation](https://mise.jdx.dev/history.html#sharing-across-machines) covers both modes.

Every tracked file is eligible to reach the repository, including its earlier saved versions. Untracking stops future capture but doesn’t erase old commits. Choose what you track with that in mind, and configure [encryption](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/#private-files-in-a-shared-repository) before capturing private contents.

Files can be shared across machines or have separate [macOS and Linux variants](https://mise.jdx.dev/dotfiles.html#variants), while you keep editing their usual paths.

## Bootstrap the next machine [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#bootstrap-the-next-machine)

The same repository can carry the tools, packages, and services you need. File changes sync automatically. Run `mise bootstrap` to apply updated tool, package, and service declarations or render changed templates.

Track the global mise config explicitly so those declarations come along. Here’s a macOS example:

```toml
[tools]
node = "lts"
python = "3.14"

[bootstrap.packages]
"brew:ffmpeg" = "latest"

[dotfiles]
"~/.zshrc" = { mode = "track" }
"~/.config/nvim" = { mode = "track" }
"~/.config/mise/config.toml" = { mode = "track" }

[bootstrap.services.mise-history]
builtin = "history-watch"
```

My repository is private. Setting up another machine locally requires an up-to-date mise installation, Git, and working Git authentication on that machine:

```sh
mise bootstrap --adopt git@github.com:jdx/dotfiles.git
```

`--adopt` makes the shared setup this machine’s own configuration: bootstrap restores its files, previews conflicts with existing files, and applies the selected configuration. The `config.toml` entry above brings the tool, package, and service declarations along. Tracking `.zshrc` alone doesn’t include those declarations.

For a remote box, [`mise bootstrap remote`](https://mise.jdx.dev/bootstrap/remote.html#private-configuration-repositories) can borrow my laptop’s GitHub access for setup over SSH, without copying the token to the box. Ongoing sync still needs Git credentials on that machine.

## Conflicts and history [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#conflicts-and-history)

If a conflict needs your decision, publication and incoming application pause for the whole setup. Local history keeps saving, and fetching continues. Nothing inserts conflict markers into your live configuration. Inspect the conflict and choose a version one file at a time:

```sh
mise dot status
mise dot pull --take-remote ~/.zshrc
```

`--keep-local` keeps this machine’s version instead. Sharing resumes after every conflict is resolved and mise checks that the decisions still match the current files.

Desktop notifications, enabled by default on macOS and Linux, are the main way to notice a pause. On Windows or a headless box, you need to check `mise doctor` or dotfiles status; otherwise you might first notice that your files are stale. I might change how conflicts are surfaced later, but so far I’m not sure what would work better.

My previous setup used a LaunchAgent and [rcm](https://github.com/thoughtbot/rcm). I ran that for years, and conflicts were rare.

A rollback also becomes a new commit, so correcting a bad alias on your laptop can reach your desktop through sync. The desktop’s own edits still have to be reconciled.

## On Omarchy [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#on-omarchy)

Omarchy already expects you to customize the files you use. Its [dotfiles guide](https://learn.omacom.io/2/the-omarchy-manual/65/dotfiles) puts personal configuration in `~/.config` and shell customizations in `~/.bashrc`; `~/.local/share/omarchy` holds Omarchy’s own files. Start by tracking a few personal files:

```sh
mise dot track ~/.bashrc
mise dot track ~/.config/hypr/bindings.conf
mise dot track ~/.config/hypr/input.conf
```

Add the `history-watch` service from above and run `mise bootstrap`. It runs as a systemd user service. Keep using your editor or Omarchy’s config menu, and mise saves the edits in place. Start with individual files so you can choose which settings travel between machines without also capturing theme assets, caches, or application state.

You can also record tracked files before and after an Omarchy update:

```sh
mise dot capture --label "omarchy update" -- omarchy-update
mise dot history --label "omarchy update"
mise dot history diff --operation --patch
```

The first command runs the update with a checkpoint on either side. The next two let you find the run and inspect what changed in your tracked files over that interval, including any concurrent edits. If you need an earlier version of one file, use `history show` to find the operation’s **Before** checkpoint and pass that reference to `rollback <path> --to <before-ref>`.

These checkpoints cover your tracked dotfiles. Package and operating-system recovery still belongs to [Omarchy’s system snapshots](https://learn.omacom.io/2/the-omarchy-manual/68/updates). The [capture documentation](https://mise.jdx.dev/history.html#capturing-an-external-command) explains the recovery options.

## Private files in a shared repository [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#private-files-in-a-shared-repository)

For files whose contents should stay private in Git, configure encryption **before their first capture**:

```toml
[history.encryption]
recipients = ["<mac-public-recipient>", "<linux-public-recipient>", "<recovery-public-recipient>"]

[dotfiles]
"~/.config/app/credentials" = { mode = "track", encrypt = true }
```

One public-recipient list covers all encrypted files. Each listed machine can decrypt with its own identity. Contents are encrypted before entering Git; filenames remain visible, and restored live files remain plaintext. Keep private identities outside the tracked repository and an independent recovery recipient in case you lose a device.

Suppose you save `~/.config/app/credentials` in plaintext, then add `encrypt = true`. The next save is encrypted, but Git would still send the earlier plaintext version along with it. Before pushing, mise walks the proposed branch’s history, including merge parents, and collects the paths declared encrypted in those commits. It checks every stored version of those paths for mise’s encrypted format. If it finds a plaintext or invalid version, it stops the push and identifies the path and commit. You must explicitly rewrite or replace that history; mise won’t do it automatically.

This enforces your encryption declarations. It doesn’t scan arbitrary files for secrets: a token accidentally saved in an ordinary, unencrypted `.zshrc` won’t be caught by this check. See the [encryption documentation](https://mise.jdx.dev/history.html#encrypted-shared-files) for configuration and identity setup.

For applications that read secrets from the environment, [mise’s environment secrets](https://mise.jdx.dev/environments/secrets/) or [fnox](https://fnox.jdx.dev/) may fit better.

## A few optional pieces [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#a-few-optional-pieces)

Track configuration selectively, especially when enrolling a directory. Logs, caches, databases, and constantly rewritten session state usually don’t belong here. Beyond that, a few options handle files that need different treatment:

- **Noisy files:** the watcher [spaces out saves for busy paths](https://mise.jdx.dev/history.html#adaptive-scheduling) without delaying other files. You can exclude paths or set `autosave = false` and save them explicitly. Sync publishes their saved version.
- **Generated config:** [templates](https://mise.jdx.dev/bootstrap/setup.html#use-a-template-optional) still work alongside tracking. Track the template sources, edit those, and run bootstrap to render each machine’s output.
- **Save descriptions:** mise generates them automatically, or you can [ask an agent such as Claude to write them](https://mise.jdx.dev/history.html#descriptions-from-an-agent). That sends change details, potentially including unencrypted configuration content, to the command you configure.

## Try it [\#](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/\#try-it)

You don’t need to migrate your whole setup to try it. Track a file, get the watcher running, make a few edits, and try rolling one back. The [setup guide](https://mise.jdx.dev/bootstrap/setup.html) walks through that workflow and connecting another machine, with notes for Omarchy and macOS.

Let me know what works for you and what still feels like too much setup.