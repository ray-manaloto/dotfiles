# First-class Omarchy backup / restore / check workflow

- URL: https://github.com/omacom/omarchy/discussions/5588
- author: andresreibel (NONE) created: 2026-05-05T10:53:08Z upvotes: 2
- fetched: 2026-09-29 via gh api graphql (lane X)

## Body

I’ve built a local Omarchy workflow that has been very useful across updates and reinstalls, and I think a version of it could fit well upstream.

The idea is not generic dotfile sync. It is an Omarchy-aware workstation backup/restore contract.

My local commands:

- `buomarchy`: back up current Omarchy/workstation state into a git repo
- `setupomarchy`: selectively restore pieces by category
- `checkomarchy`: compare current config against the last known-good backup after updates
- `updateomarchy`: back up first, update, then inspect drift

Why this helped:

During the 3.7 update, Hypr/Waybar/Nvim had expected migration diffs. Because I had `checkomarchy`, I could see those diffs and avoid blindly restoring old configs over the new 3.7 command names.

Examples of useful categories I back up and restore:

- Hyprland config, custom bindings, and power-aware hypridle behavior
- Waybar config and battery status/warning behavior
- Ghostty config plus local overrides loaded after Omarchy theme files
- Walker, Mako, Fastfetch, Btop, Nvim, Starship
- `~/.config/omarchy/hooks`, `bin`, current theme state, active wallpaper
- installed theme Git URLs and a `my-themes.txt` allowlist
- webapp desktop entries and icons
- browser bookmarks/preferences/extension URL list
- selected `~/.local/bin` scripts
- selected systemd user services
- package manifests from `pacman -Qeq` and `yay -Qmq`
- zram config, power profile rules, SDDM login state
- battery charge threshold sudoers template for ThinkPads
- saved `efibootmgr -v` output and direct Omarchy EFI boot with Limine fallback

The restore side is selective, not all-or-nothing:

- restore only Hypr
- restore only Waybar
- restore only Ghostty
- restore webapps
- restore themes
- restore packages
- restore boot-flow state

Potential upstream shape:

- `omarchy backup`
- `omarchy restore [category]`
- `omarchy check`

Important behavior:

- Backups should be migration-aware, so restoring an old backup does not reintroduce renamed Omarchy commands such as `omarchy-lock-screen` after 3.7 migrated it to `omarchy-system-lock`.
- `omarchy check` should show drift after updates, so users can decide whether to accept new upstream defaults or restore their local version.
- If Snapper snapshot creation fails during update, Omarchy could optionally continue after creating an Omarchy backup, instead of aborting the whole update.

This would give users a practical middle ground between full system snapshots and manually managing dotfiles. It would also make reinstalls and laptop migrations much easier while staying aligned with Omarchy’s opinionated defaults.

## Comments
### EFrMG (CONTRIBUTOR) @ 2026-07-26T04:26:06Z

The issue I have with scripts for managing dotfiles is how tedious it is to change the dotfiles and keep track of them. It is alright for initial setups or whole migrations in practice, but there are also better tools for it such as Chezmoi.

The main thing to consider would be that you mention **some** things in Omarchy for a backup / migration to a new system or update, not all of them. So doing it with a set of scripts would be very tedious, while as something like Chezmoi could help add things to the source directory in a simple set of commands.

I like the `omarchy [ARG]` form, although why reinvent the wheel again, when dotfiles go way past what Omarchy defaults are. People use all sorts of programs, and I even backup things that are not configs, such as the nvim dictionary file.

### jensenojs (NONE) @ 2026-09-08T07:58:53Z

https://github.com/nixfred/imprint

