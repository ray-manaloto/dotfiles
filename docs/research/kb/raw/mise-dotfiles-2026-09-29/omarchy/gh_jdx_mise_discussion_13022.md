# Proposal: give Omarchy dotfiles automatic history, easy restore, and optional sync with mise

- URL: https://github.com/jdx/mise/discussions/13022
- author: jdx created: 2026-09-09T18:43:30Z

## Body

**TL;DR:** Dropbox for individual configuration files, backed by Git. Keep editing files where they are; mise automatically saves their history, lets you restore earlier versions, and optionally syncs changes both ways between machines. Omarchy could make this built in through its config menu, starting with local autosave and restore.

I'd like Omarchy to save people's configuration changes automatically, let them restore an earlier version from the config menu, and offer to carry their setup to another machine. Keep editing the same files, with the same editor. Omarchy remembers.

Omarchy already ships mise, and mise now has most of the machinery for this. I'd be happy to do the remaining work and help with the Omarchy integration.

This follows the broader machine-configuration proposal in #12709, but dotfiles can ship independently. I wrote up the existing mise workflow in [Dotfiles That Save Themselves](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/). This proposal also builds on the [Dots plan in my Omarchy branch](https://github.com/jdx/omarchy/blob/022f6993ba94669902ea8361fd21a6266061459c/plans/dots.md), with a few differences around sharing that need deciding.

**The everyday experience**

Someone changes a key binding, adjusts their terminal, or asks an agent to edit their Hyprland config. A background service saves the change. If the result is wrong, they open *Update > Config*, pick the file, see what changed, and restore it. Restoring also saves the version being replaced, so they can undo that decision.

An Omarchy migration or config refresh gets a labeled before/after pair. “What changed during the last update?” becomes something the machine can show. Hand edits get saved too, even if the user never runs an update afterwards.

> [!IMPORTANT]
> **We should minimize changes to user configuration during updates.** Wherever tooling supports system defaults and user overrides, Omarchy should put its defaults in the system configuration and leave personal configuration to the user. My open [lazy-tools PR](https://github.com/omacom/omarchy/pull/9596) is one example: it declares Omarchy's default tools in `/etc/mise/config.toml` instead of adding them to the user's global mise config. Users can override those defaults in `~/.config/mise/config.toml`, and Omarchy can update its own declarations independently.
>
> I'd like us to follow that pattern wherever possible. Some tools and migrations will still require changes to user files, but we should keep those exceptions small. History gives us visibility and recovery for the changes that remain; the goal is to need fewer of them.

This fits how Omarchy already encourages customization: personal files stay in their normal locations. Users can keep using the config menu, their editor, or an agent. They don't have to maintain a second copy or remember to commit each change.

**What already works in mise**

For one file, the setup is:

```sh
mise bootstrap dotfiles track ~/.bashrc
```

That saves a baseline and declares the file in the user's global mise config. Add the watcher there:

```toml
[bootstrap.services.mise-history]
builtin = "history-watch"
```

Then run `mise bootstrap services apply`. On Omarchy this starts a systemd user service. Edits are saved into a separate Git store; `.bashrc` remains a regular file, and no `.git` directory is added to the home directory.

The recovery commands already exist:

```sh
mise bootstrap dotfiles history --path ~/.bashrc
mise bootstrap dotfiles rollback ~/.bashrc --dry-run
mise bootstrap dotfiles rollback ~/.bashrc
mise bootstrap dotfiles undo
```

So does capturing an external operation:

```sh
mise bootstrap dotfiles capture --label "omarchy update" -- omarchy-update
mise bootstrap dotfiles history diff --operation --patch
```

The capture wrapper preserves the update's exit status; a history failure warns and lets the command run. Its comparison covers tracked files over that interval, including concurrent edits. File recovery covers those tracked configs; Omarchy's system snapshots still handle operating-system recovery.

**How I would bring this into Omarchy**

Omarchy would choose a small, audited set of personal configuration files and enable local history during provisioning, with a skippable migration for existing installations. These are concrete examples from the current `quattro` branch; select the files the user actually uses and customizes:

| File to track | What the user gets back or carries to another machine |
| --- | --- |
| `~/.config/hypr/bindings.lua` | Personal shortcuts and replacements for default bindings. |
| `~/.config/hypr/looknfeel.lua` | Preferred gaps, borders, window rounding, animations, and layout. |
| `~/.config/omarchy/shell.json` | Bar layout and widgets, plus screensaver and lock timings. |
| `~/.config/omarchy/extensions/omarchy-menu.jsonc` | Personal menu entries and overrides. |
| `~/.config/foot/foot.ini` | Font, padding, scrollback, and keyboard preferences for the default terminal. |
| `~/.bashrc` | Personal aliases, functions, and exports. |
| `~/.config/starship.toml` | The user's prompt layout and styling. |

The [Omarchy dotfiles guide](https://github.com/omacom/omarchy/blob/quattro/manual/31-dotfiles.md) describes these personal configuration surfaces; the shipped [foot config](https://github.com/omacom/omarchy/blob/quattro/config/foot/foot.ini) and [Starship config](https://github.com/omacom/omarchy/blob/quattro/config/starship.toml) show the terminal and prompt settings. Hyprland's [main config](https://github.com/omacom/omarchy/blob/quattro/config/hypr/hyprland.lua) already loads personal overrides after Omarchy's defaults, which is exactly the separation we should preserve.

For example, a user could start with their bindings and terminal:

```sh
mise bootstrap dotfiles track ~/.config/hypr/bindings.lua
mise bootstrap dotfiles track ~/.config/foot/foot.ini
```

For Ghostty or Alacritty users, substitute `~/.config/ghostty/config` or `~/.config/alacritty/alacritty.toml`. Those [terminal configs](https://github.com/omacom/omarchy/tree/quattro/config) import generated theme colors from `~/.local/state/omarchy/current/theme`; track the personal config file and let Omarchy regenerate the theme output.

Some files deserve a separate decision. [`~/.config/hypr/monitors.lua`](https://github.com/omacom/omarchy/blob/quattro/config/hypr/monitors.lua) is valuable for local recovery, but output names, resolution, position, and scaling usually belong to one machine. [`input.lua`](https://github.com/omacom/omarchy/blob/quattro/config/hypr/input.lua) mixes portable keyboard preferences with mouse and trackpad settings. In a shared setup, track these only if you want the same settings on both machines. `autostart.lua` and menu actions can depend on locally installed apps or scripts; review those dependencies before sharing. `~/.XCompose` is another useful opt-in, but Omarchy [seeds it with the user's name and email](https://github.com/omacom/omarchy/blob/quattro/install/user/xcompose.sh).

Use explicit paths for this initial set. Browser profiles, application tokens, caches, generated theme assets, and plugin checkouts should stay outside it; enrolling all of `~/.config` would include far more than personal preferences.

Users would see the proposed `omarchy dots` commands from the plan—`status`, `log`, `diff`, and `restore`—plus a menu for the common recovery operations. Those commands and menu entries are integration work. The mise commands above are available today.

I would put capture boundaries around migration batches and batch refreshes, including migrations run at login. That gives useful descriptions without a separate operation for every file copied. Keep the existing `.bak` behavior during the initial rollout, and make history failures visible without blocking updates.

People already using Stow, chezmoi, or yadm should keep their setup. The proposed integration needs the plan's detection and stand-down behavior. Tracking a symlink currently records the link itself, so silently enrolling it would not protect the contents users expect.

**A second machine**

Once local recovery is useful, offer to connect a private Git repository. Someone could share their preferred bindings and terminal configuration between a desktop and laptop, or bring them back after a reinstall.

mise already supports automatic sharing in both directions and a manual mode. With a shared setup repository, current mise can adopt it on another machine:

```sh
mise bootstrap --adopt git@github.com:me/dotfiles.git
```

That machine needs mise, Git, and repository authentication. Tool and service declarations come along only when their mise configuration is explicitly tracked too. Omarchy could wrap this with the proposed dots setup flow.

There are two policy gaps to settle before connecting the default Omarchy history to a remote:

- The Dots plan shares only the current state; mise shares saved history, including intermediate edits. **I'd keep one history for now.** Squashing local saves before sharing would complicate sync and recovery across machines. Manual sharing still lets users choose when to publish, but includes those earlier saves.
- Keeping some files' history local while sharing others would require a second Git repository. One user has already requested this, and it could come later. **I'd start with one history** so users have a simple model of what gets saved and shared.

These choices matter because an accidentally saved credential can remain in history after being deleted from the live file. A private repository helps with access, but selecting what gets recorded and published still matters. mise also supports encryption before capture for deliberately tracked private files.

**A first version worth shipping**

I would start with local autosave, labeled migration/refresh history, and restoring one file from the menu. That gives someone with one Omarchy machine an immediate benefit, with no GitHub account or repository setup. Then add sharing after settling publication policy and which settings should travel.

Omarchy would own the defaults and the experience; I would maintain the history and synchronization machinery in mise. I'd be happy to make changes to mise to make that fit. Would this be a useful direction for Omarchy's dots feature?

*AI-assisted — Tool: Codex; model: OpenAI/GPT-6; version: unavailable.*


## Comments
### jdx @ 2026-09-09T18:59:23Z

I've posted this proposal in [Omarchy's Discussions](https://github.com/omacom/omarchy/discussions/11029) for feedback on the Omarchy integration. Please continue that conversation there.

*AI-assisted — Tool: Codex; model: OpenAI/GPT-6; version: unavailable.*


