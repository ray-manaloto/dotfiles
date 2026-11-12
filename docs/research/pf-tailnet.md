---
okf_version: "0.2"
type: "report"
title: "Tailscale-only pf anchor on the Mac"
description: "Why and how ssh, Screen Sharing and file sharing on the Mac answer only Tailscale peers: the pf anchor, its boot daemon, the load/confirm/unload/status tasks, the pf facts behind them and the gaps."
---

# Tailscale-only pf anchor on the Mac

Design agreed with the owner on 2026-11-12, after ssh and Screen Sharing to the Mac were shown to work over
Tailscale from another device.

## What it does

- Ports 22 (ssh), 88 (Kerberos), 445 (file sharing), 3031 (Remote Apple Events), 3283 (Apple Remote Desktop)
  and 5900 (Screen Sharing), tcp and udp, answer only Tailscale addresses (`100.64.0.0/10`,
  `fd7a:115c:a1e0::/48`) and loopback. Anyone else gets a refusal (`block return`): a quick, clear failure
  instead of a timeout. AirPlay and every other port are untouched.
- The rules match addresses, not the Tailscale interface, because its `utun` number changes across restarts. A
  spoofed 100.x source on the home network cannot finish a TCP handshake: the replies go out over Tailscale.
- The anchor is `com.apple/100.dotfiles-tailnet`. `/etc/pf.conf` already evaluates `anchor "com.apple/*"`, so
  nothing in Apple's files changes; `100` sorts before Apple's `200.AirDrop` and `250.ApplicationFirewall`.

## Where it lives (mise first)

- mise `[bootstrap.files]` in the global config writes `/etc/pf.anchors/dotfiles-tailnet` and
  `/Library/LaunchDaemons/dev.dotfiles.pf-tailnet.plist` (root:wheel 0644), as it already writes the sshd
  drop-in. Writing them changes nothing live; the plist ships `Disabled`.
- Global file tasks run `hometools` (`python/home/src/hometools/pf.py`):
  - `pf:load` parses the rules without root, arms a detached root revert, loads the anchor and turns pf on with
    `pfctl -E` if it is off. The revert flushes the anchor after 120 s unless `pf:confirm` ran. Every load arms it.
  - `pf:confirm` refuses if the revert already ran, marks the load confirmed, then `launchctl enable`s and
    bootstraps the boot daemon. So the boot daemon starts only after a confirmed load, never at bootstrap.
  - `pf:unload` boots the daemon out, disables it and flushes the anchor. pf itself stays on, with no rules of ours.
  - `pf:status` prints one JSON line (`enabled`, `rules`, `boot`) and exits 1 unless all three are on.
- mise has no macOS firewall or LaunchDaemon feature at v2026.11.7: `[bootstrap.firewall]` is Linux-only and
  `[bootstrap.macos.launchd]` covers user agents only. No upstream issue asks for either.

## pf facts it relies on

From Apple's kernel source (`apple-oss-distributions/xnu`, `bsd/net/pf_ioctl.c`, read 2026-11-12):

- `pfctl -E` (DIOCSTARTREF) adds an enable reference that stays after pfctl exits and does not fail when pf is
  already on; `pfctl -e` (DIOCSTART) returns EEXIST then.
- `pfctl -d` (DIOCSTOP) stops pf and drops every reference, whoever took it. Any program that runs it turns these
  rules off silently: `pf:status` is the check.
- Listing rules of an anchor that does not exist fails (DIOCGETRULES returns EINVAL), and pf removes an anchor
  once it is flushed, so `pf:status` reads `com.apple`'s anchors first.
- `pfctl -n -a <anchor> -f <file>` parses without root and loads nothing; the tests use it on the tracked rules.

## Owner steps after merge

1. From the home folder, `mise bootstrap files apply --dry-run`, then `mise bootstrap files apply` (sudo): it
   should list only the two files. Not a bare `mise bootstrap`: that applies every part, and run from the dotfiles
   checkout it first renders the repo's ssh template, which stops without the Doppler names
   (`src/cli/bootstrap.rs:2096-2099` at mise v2026.11.7, before any part runs).
2. At the Mac: `mise run pf:load`.
3. Within 120 s, from the iPhone over Tailscale: ssh, Screen Sharing and file sharing all connect; from the home
   network they are refused.
4. `mise run pf:confirm`, then `mise run pf:status`. After the next restart, `pf:status` again.

If anything fails, do nothing: the revert removes the rules at 120 s. `mise run pf:unload` removes them at once.

## Gaps

- Not verified: whether `pfctl -E -f` enables before or after it loads (Apple's pfctl source is not in the public
  `network_cmds` tags). Either order is safe: the window has only Apple's rules.
- Not verified: the boot order against Apple's `com.apple.pfctl`, which reloads `/etc/pf.conf` at boot. A
  sub-anchor is its own ruleset, so the reload should leave it; the post-restart `pf:status` checks this.
- Two loads less than 120 s apart: the first load's revert can flush the second load's rules early. It fails
  safe (rules off); run `pf:load` again.
