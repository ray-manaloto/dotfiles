---
okf_version: "0.2"
type: "report"
title: "Disk-watch with monit"
description: "Why the low-disk alert is brew's monit and not our own Python, the tools compared, and the monit 6.0.0 behaviour the config relies on, each checked in source and in a real run."
---

# Disk-watch with monit

Research of 2026-11-12. The owner's ruling: use an existing native tool (Rust, C, C++, Zig) with commits in the
last two months instead of code we keep ourselves, and manage it from dotfiles. This replaces the Python watcher
of PRs #648 to #650.

## Tools compared

| Tool | Language | Fit |
| --- | --- | --- |
| monit (github.com/MMonit/monit) | C | Watches free space with alert, exec and repeat built in. Last commit 2026-11-09. brew 6.0.0; not in the mise registry. Chosen. |
| dust (bootandy/dust) | Rust | A disk-usage tree, not a watcher. mise registry `aqua:bootandy/dust`. Added as the tool to find what fills the disk. |
| dua, gdu, duf | Rust, Go, Go | Usage viewers; no alerting. |
| Beszel, Netdata | Go, C | Need a hub or a heavy agent for one Mac. |
| Glances | Python | Not native. |

No maintained native daemon other than monit alerts on low disk space by itself.

Real configurations used as a starting point:

- Homebrew's formula runs monit in the foreground: `run [opt_bin/"monit", "-I", "-c", etc/"monitrc"]`
  (homebrew-core `Formula/m/monit.rb`).
- Filesystem rules in the Hetzner community tutorial and the Linode monit guide (`check filesystem ... if space
  usage > 85% then alert`).
- dust in mise: disrupted/dotfiles and aymericbeaumet/dotfiles `.config/mise/config.toml` both have `dust = "latest"`. We
  pin an exact version instead. No public mise config installs monit (GitHub code search, 2026-11-12).

## monit 6.0.0 behaviour the config relies on

Read at tag `release-6.0.0` of MMonit/monit, then confirmed with a scratch monit on macOS.

- The control file must not be a symlink, must be owned by the user running monit and must be mode 0700 or less
  (`src/p.y:3615`). So the global mise config writes monitrc as a `[bootstrap.files]` entry with mode 0600, not
  as a linked dotfile.
- On macOS, `space free` is `f_bavail`, the space a normal user can still write (`src/device/sysdep_DARWIN.c:84`).
  `GB` is 1024^3 bytes (`src/monit.h:356`): 100 GB in monitrc is about 107 decimal GB. APFS purgeable space
  counts as used, so the alert can fire a little early.
- Check `/System/Volumes/Data`: on macOS `/` is the sealed system volume.
- An exec string is split on spaces into arguments: `exec "/usr/bin/touch a b"` touched two files in the run. So
  the notification text can't go through `osascript -e '...'`. The AppleScript file reads monit's
  `MONIT_DESCRIPTION` with `system attribute`.
- `repeat every 16 cycles` with `set daemon 900` repeats the exec every 4 hours while the volume stays low.
  `else if succeeded then exec` fired once on recovery in a run with a toggled probe; the config doesn't need it,
  since nothing is left to clear.
- `monit status` reaches the daemon through `set httpd`. The httpd won't start without an allow rule
  (`src/http.c:101-106`). `allow localhost` on a unix socket with permission 0600 lets the owner's
  `monit -c ~/.config/monit/monitrc status` work with no password in the file. A socket path of 104 bytes or more
  fails (`Could not change unix socket permission`), so the socket stays under `~/.local/state/monit/`.

## Gaps

- Whether the banner shows depends on the notification permission for Script Editor/osascript, which the owner
  confirms by eye.
- Linux machines get no disk watch: every monit entry is `os = "macos"`, and the LaunchAgent is macOS only.
