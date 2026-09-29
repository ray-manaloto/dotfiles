# Proposal: give Omarchy dotfiles automatic history, easy restore, and optional sync with mise

- URL: https://github.com/omacom/omarchy/discussions/11029
- author: jdx created: 2026-09-09T18:59:06Z

## Body

**Proposal:** let Omarchy remember changes to personal configuration files, show what changed, and restore an earlier version from the config menu. Sharing those settings with another machine would be optional.

Keep editing files where they are—with the config menu, your editor, or an agent. A background service saves their history in Git, without moving them or turning them into symlinks.

**The mise functionality is available today; the built-in Omarchy experience is still a proposal.** Omarchy already ships mise. I'd be happy to build the integration and maintain the history and synchronization machinery behind it.

## The Omarchy experience I'd like to build

Someone changes a keybinding, adjusts their terminal, or asks an agent to edit their Hyprland config. If the result is wrong, they open the config menu, choose the file, inspect the change, and restore it. Restoring saves the version being replaced, so that decision can be undone too.

Omarchy updates and migrations would get labeled before/after history. “What changed during the last update?” becomes something the machine can show. Ordinary hand edits are saved even when no update runs.

I'd start with three things:

1. **Local autosave** for a small, explicit set of personal configuration files, enabled during provisioning and offered through a skippable migration for existing installations.
2. **History, diff, and restore in the menu**, backed by the proposed `omarchy dots` commands from the [Dots plan](https://github.com/jdx/omarchy/blob/022f6993ba94669902ea8361fd21a6266061459c/plans/dots.md).
3. **Labeled capture around migration batches and config refreshes**, including migrations run at login. Keep existing `.bak` behavior during the initial rollout, and report history failures without blocking updates.

This gives a single-machine user something useful immediately, with no remote repository or account setup. File history covers tracked configuration; Omarchy's system snapshots remain responsible for operating-system recovery.

### Keep defaults separate from personal configuration

History should accompany a broader effort to minimize changes to user files during updates. Where an application supports system defaults and user overrides, Omarchy should update its defaults and leave personal overrides to the user.

My open [lazy-tools PR](https://github.com/omacom/omarchy/pull/9596) follows that pattern: Omarchy declares default tools in `/etc/mise/config.toml`, and users override them in `~/.config/mise/config.toml`. The defaults can evolve independently. Some migrations will still need to touch user files; those are the changes history should make visible and recoverable.

### Choose the files deliberately

These examples come from Omarchy's **`quattro` branch**, rather than assuming every installed version has the same paths. Its [dotfiles guide](https://github.com/omacom/omarchy/blob/quattro/manual/31-dotfiles.md) describes the personal configuration surfaces.

| Configuration | What history protects |
| --- | --- |
| `~/.config/hypr/bindings.lua` | Personal keybindings and overrides |
| `~/.config/hypr/looknfeel.lua` | Gaps, borders, animations, and layout |
| `~/.config/omarchy/shell.json` | Bar, widgets, lock, and idle preferences |
| `~/.config/omarchy/extensions/omarchy-menu.jsonc` | Personal menu entries |
| `~/.config/foot/foot.ini` | Terminal preferences; choose the user's actual terminal config |
| `~/.bashrc` and `~/.config/starship.toml` | Shell customizations and prompt styling |

Monitor settings are useful for local recovery but often differ between a desktop and laptop. Input settings mix portable keyboard preferences with device-specific mouse and trackpad settings. Autostart entries and menu actions may depend on locally installed programs. These need an explicit sharing decision; mise supports separate variants selected by OS or a mise environment when different contents are needed.

Track individual personal files. Leave browser profiles, tokens, caches, generated theme output, and plugin checkouts outside the default set. People using Stow, chezmoi, or yadm should keep their setup: the integration needs detection and stand-down behavior. Tracking a symlink records the link itself, so enrolling it silently would not protect its target's contents.

## Try local history today

The examples below target **mise 2026.9.9 or newer**. Check `mise --version` first. Start with one existing file:

```sh
mise dot track ~/.bashrc
```

That leaves `.bashrc` in place, saves its current contents as a **checkpoint**—a version you can restore—and adds its tracking declaration to `~/.config/mise/config.toml`.

Add the watcher to that config, then start it:

```toml
[bootstrap.services.mise-history]
builtin = "history-watch"
```

```sh
mise bootstrap services apply
mise dot status
```

On Omarchy, this runs as a systemd user service. History lives in a separate Git store; there is no `.git` directory added to your home directory.

Edit the file normally. To save immediately and try recovery:

```sh
mise dot save ~/.bashrc
mise dot history --path ~/.bashrc
mise dot rollback ~/.bashrc --dry-run
mise dot rollback ~/.bashrc
```

Rollback restores the latest saved version that differs from the live file. Use `mise dot undo` to reverse the restore.

You can also inspect what an update changes today:

```sh
mise dot capture --label "omarchy update" -- omarchy-update
mise dot history diff --operation --patch
```

This captures tracked files before and after the command and preserves its exit status. The comparison includes other edits made during that interval. Automatically adding those capture boundaries and presenting them in the menu would be Omarchy integration work.

## Share with a second machine

Once local recovery is working, connect an empty private Git repository. Track the mise configuration too if the second machine should inherit its tool and watcher declarations:

```sh
mise dot track ~/.config/mise/config.toml
mise dot origin set git@github.com:me/dotfiles.git --sync sync
```

Substitute your own repository URL, including your Gitea instance. Review the connection preview. Automatic mode pushes saved edits and periodically fetches and applies incoming changes. For manual sharing, choose `--sync manual`; then `mise dot sync` exchanges commits and `mise dot pull` applies incoming files.

On the other machine, install Git and a current mise, configure repository authentication, then:

```sh
mise bootstrap --adopt git@github.com:me/dotfiles.git
mise settings set history.sync sync
mise dot status
```

Shared configuration and required sources must be tracked for bootstrap to install the declared tools and services. See the [setup guide](https://mise.jdx.dev/bootstrap/setup.html) for the full workflow.

### Existing files and conflicts

Adoption now accepts identical existing files without inventing a competing local history. If files differ, inspect `mise dot status` and `mise dot conflicts PATH`, then choose `mise dot pull --take-remote PATH` or `mise dot pull --keep-local PATH`. Resolve every reported conflict, then rerun `mise bootstrap` if adoption paused.

If the machine already has **unrelated local history** that you intend to discard, preview the explicit replacement:

```sh
mise bootstrap --adopt git@github.com:me/dotfiles.git --replace-history --dry-run
```

Only proceed without `--dry-run` if that is the history you want to replace. This is a separate adoption decision; ordinary sync never replaces unrelated history automatically.

### Encrypted files

For a file that should be encrypted in Git from its first save:

```sh
mise dot track ~/.config/app/credentials --encrypt
```

First configure `[history.encryption].recipients` with **public age recipients** for your machines and an independent recovery key. These are recipient strings, not filenames or private keys. Configure private identities locally using `settings.age.identity_files` or `settings.age.key_file`, keep them outside tracking, and store the private recovery key somewhere safe, such as a password vault. The [encryption guide](https://mise.jdx.dev/history.html#encrypted-shared-files) covers the configuration.

The live file stays readable; its contents are encrypted before entering Git. Filenames remain visible. Adding encryption later does not remove older plaintext commits, and mise blocks publishing that history by default.

## The sharing policy still needs a decision

The Dots plan proposes sharing only the current state. mise shares **saved history, including intermediate edits**. Manual sync changes when those commits are published, not which commits are included. Deleting a credential from a live file does not remove it from earlier saves.

I'd keep one history initially. Keeping some files' history local while sharing others is not currently a per-file option; it would require separate stores. Likewise, machine-specific variants separate file contents but still belong to the shared history. We should settle these choices before offering remote sync for Omarchy's default tracked set.

My proposed first release is local autosave, labeled update history, and restoring a file from the menu. Then add sharing with clear choices about what travels. Omarchy would own the defaults and user experience; I'd maintain the mise machinery and make the changes needed to support it.

This builds on the broader [machine-configuration proposal](https://github.com/jdx/mise/discussions/12709), but dotfiles can ship independently. [Dotfiles That Save Themselves](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/) explains the underlying approach. Would this be a useful first version of Omarchy's dots feature?

## What's changed in mise

*Updated September 15, 2026. The examples below target **mise 2026.9.9 or newer**.*

Recent releases address several of the questions in this thread:

- **Shorter commands:** `mise dot` now exposes the complete dotfiles workflow. `mise dotfiles` and the existing `mise bootstrap dotfiles` spelling work too. The short name arrived in [2026.9.8](https://github.com/jdx/mise/releases/tag/v2026.9.8); installations on 2026.9.7 still need the older spelling.
- **Encrypted tracking from the CLI:** `mise dot track PATH --encrypt` saves an encrypted first checkpoint and writes the tracking declaration for you. Configure encryption recipients first.
- **Better adoption of an existing machine:** matching files can adopt the incoming history without an unrelated-history error. Different files still require a decision. For deliberately replacing unrelated local history, there is now an explicit `--replace-history` option with a dry-run preview.
- **Conflict inspection:** `mise dot conflicts PATH` shows the saved local and incoming versions; `--difftool` opens the comparison in Git's configured tool.
- **Watcher and sync fixes:** [2026.9.9](https://github.com/jdx/mise/releases/tag/v2026.9.9) fixes a race that could record untouched files as deleted and propagate those deletions to another machine. It also detects stale watchers using the wrong history store. **Upgrade both machines before testing sync**, then run `mise bootstrap services apply` and check `mise dot status`. Files affected by the deletion bug can be recovered from earlier history.

GitHub is optional: the sync remote can be a private repository on **Gitea, Forgejo, GitLab, or another Git host**. mise uses your Git authentication, which must also work for the background service.

*AI-assisted — Tool: Codex; model: OpenAI/GPT-6; version: unavailable.*


## Comments
### shawnyeager @ 2026-09-13T16:36:55Z

Would love to see this. Out of the box is already excellent. Being able to trivially clone my tweaks is the next step. 
#### reply jdx @ 2026-09-13T16:50:34Z

If you get a chance to use it inside omarchy I'd love your input 

#### reply shawnyeager @ 2026-09-13T19:57:09Z

Have a brand new XPS 14 I'm working to setup now. Is there an early release I can test? If I read you correctly, it's not in GA yet?

#### reply jdx @ 2026-09-13T20:05:46Z

Yes! You can try it today with the latest mise release. The dotfile history and sync features shipped in 2026.9.2; what’s still a proposal is the built-in Omarchy integration—menus, automatically selecting files, and capturing updates. Sorry, I should have made that distinction clearer.

My [blog post](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/) explains the approach, and the [setup guide](https://mise.jdx.dev/bootstrap/setup.html) walks through testing it and connecting another machine.

For a small test on your XPS, check `mise --version` and update mise if needed, then:

```sh
mise bootstrap dotfiles track ~/.bashrc
```

Add this to `~/.config/mise/config.toml`:

```toml
[bootstrap.services.mise-history]
builtin = "history-watch"
```

Then start the background service:

```sh
mise bootstrap services apply
mise bootstrap dotfiles status
```

Keep editing normally. It saves changes locally, and you can inspect or restore them:

```sh
mise bootstrap dotfiles history --path ~/.bashrc
mise bootstrap dotfiles rollback ~/.bashrc --dry-run
mise bootstrap dotfiles rollback ~/.bashrc
```

For cloning your tweaks, follow the guide’s sharing steps on your existing machine first, then adopt that repository on the XPS. Use a private repository, since sync includes saved history.

I’d start with aliases, keybindings, and terminal preferences. Keep the XPS’s monitor and trackpad settings separate initially, since those may differ from your other machine. Track individual personal files rather than all of `~/.config`.

It’s newly released, so I’d love feedback on where the setup feels rough—especially getting your existing tweaks onto the XPS.

*AI-assisted — Tool: Codex; model: OpenAI/GPT-6; version: unavailable.*

### CaffeinatedTech @ 2026-09-15T13:16:43Z

I've just set up mise dotfiles sync between my desktop and my laptop including an encrypted file.  It works well once you get it set up.

the docs need a bit more explaining around what actually goes in the recipients array when setting up encryption and how to generate the age files, as well as generating the recovery file and storing is some place safe like your password vault.

I'd like to be able to use a different git provider like my gitea instance instead of trusting a private repo in github for syncing my dotfiles.

I know you've been working on this in mise, and I'm not on the latest version yet, as Omarchy hasn't adopted it yet, I'm still on 2026.9.7.  So the docs mention using `mise dot sync` for example while the version I have it is still `mise bootstrap dotfiles sync`.  I much prefer the new command :)

The adopt command on my laptop threw a huge warning about the two files I started with `.bashrc` and `~/.config/mise/config.toml` - existing files.  The warning wasn't clear about what I had to do to force adopt those remote files.  That could have changed in newer versions.

Is there, or will there be a way to add a new encrypted file to track from the cli instead of adding it manually in the config with the `encrypt = true`

I'm excited to get my neovim configuration properly synchronising, and I can't wait for full Omarchy adoption of this.
#### reply jdx @ 2026-09-15T13:31:48Z

Thanks for trying this across both machines, including encryption! The setup friction you describe is useful feedback. You're right that the docs need a clearer walkthrough of generating age keys, what goes in `recipients`, and storing a separate recovery key in a password vault. `recipients` takes **public recipient strings**, not key-file paths or private keys; the private identities stay local and outside tracking.

A few answers and updates:

- **Your Gitea instance already works.** mise accepts Git remote URLs and uses your Git authentication; GitHub isn't required. The background watcher needs access to those credentials too. Since you already have shared history, preserve that history when moving repositories so both machines retain the same ancestry.
- **`mise dot` arrived in 2026.9.8.** On 2026.9.7, `mise bootstrap dotfiles` is still the right spelling, and it remains supported in newer releases.
- **Encrypted enrollment is now available in 2026.9.9:** with `[history.encryption].recipients` configured, run:

  ```sh
  mise dot track ~/.config/app/credentials --encrypt
  ```

  That writes `encrypt = true` and encrypts the first checkpoint. Adding encryption to a previously tracked file doesn't remove older plaintext history.
- **Adoption also improved in 2026.9.9.** Identical existing files can adopt the incoming history without an unrelated-history error. For differing files, `mise dot status` shows what needs attention, `mise dot conflicts PATH` shows the comparison, and `mise dot pull --take-remote PATH` selects the repository's version. Resolve all reported conflicts, then run `mise bootstrap` if adoption paused. If the problem is genuinely unrelated local history that you intend to discard, `mise bootstrap --adopt <url> --replace-history --dry-run` previews that separate decision; it isn't needed for ordinary file conflicts.

**Please upgrade both machines to 2026.9.9 or newer before continuing sync.** That release fixes a race that could record untouched files as deleted and sync those deletions to the other machine. After upgrading, run:

```sh
mise bootstrap services apply
mise dot status
```

This also handles stale history watchers using the wrong store. If you've seen unexpected deletions, the files can be restored from an earlier checkpoint. Details are in the [2026.9.9 release notes](https://github.com/jdx/mise/releases/tag/v2026.9.9).

I've updated the proposal above with the current commands and a clearer distinction between the mise features you can use today and the Omarchy integration still to build. I'd love to hear how the Neovim setup goes.

*AI-assisted — Tool: Codex; model: OpenAI/GPT-6; version: unavailable.*

#### reply CaffeinatedTech @ 2026-09-15T20:32:41Z

> Please upgrade both machines to 2026.9.9 or newer before continuing sync.

I believe the Omarchy package repository is still on mise version 2026.9.7, and I'm on the edge channel.  So I think I'll have to remove mise with pacman, then re-install it with the mise.run script.  I hope it doesn't tear out my configuration when I remove it.  

#### reply jdx @ 2026-09-15T20:41:54Z

i believe it's set to auto-bump every 24h

#### reply CaffeinatedTech @ 2026-09-15T21:03:18Z

> i believe it's set to auto-bump every 24h

Ah, thanks.  I'll wait until tomorrow :)

#### reply CaffeinatedTech @ 2026-09-18T09:59:28Z

I've got my neovim config syncing with mise.  I installed the [mason-lock](https://github.com/zapling/mason-lock.nvim) plugin with a autocmd script for automatic Mason package installation and updates without trying to sync the ~/.local/share/nvim/mason directory.  Here's a [gist](https://gist.github.com/CaffeinatedTech/9e4e1e2a63781256483701b6e334b298) about it.

mise dotfile sync is working well, thank you.

