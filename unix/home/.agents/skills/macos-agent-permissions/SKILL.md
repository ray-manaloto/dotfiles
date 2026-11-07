---
name: macos-agent-permissions
description: >-
  Find and fix the macOS privacy grant (Accessibility / Device Control and Data Access, Screen Recording, Automation) that a desktop-automation CLI such as agent-desktop needs, by asking macOS which app it actually checked. Use whenever agent-desktop reports PERM_DENIED or "accessibility: denied", its permissions --guide popup is stuck on STEP 1 OF 2, a grant "doesn't take" after dragging a binary in, after upgrading agent-desktop or Herdr, or when starting desktop automation from a new launcher (Herdr tab, Codex app, Claude app, a terminal, an IDE).
---

# macOS agent permissions

macOS privacy (TCC) does not judge a command-line tool by its own binary. It judges the
**responsible app**: the app that launched the process chain. Dragging the tool's binary into
System Settings does nothing when the responsible app is something else, which is why
agent-desktop's guide can sit on step 1 forever with its own row switched on.

## Steps

1. Ask macOS who it checked. The script runs the real agent-desktop binary once (not the
   mise shim, which is a link to mise) and reads tccd's own log lines for that pid:

   ```
   python3 -I ~/.agents/skills/macos-agent-permissions/scripts/tcc_who.py --reveal
   ```

   It prints JSON with `result` (`granted` | `needs_grant` | `unknown`), a `message`, and one
   entry per service with the app macOS checked (`app` bundle id, `path`) and `auth`
   (`allowed`, `denied`, `unknown` = no entry). With `--reveal` it opens Finder on each app
   that still needs a grant. Exit 0 means everything checked is granted.

2. If `needs_grant`, tell the user exactly what to do. The user changes privacy settings; the
   agent never does (no `tccutil`, no TCC database edits, no clicking the switches):
   - Open System Settings > Privacy & Security > the pane named in `message`
     (Accessibility is called **Device Control and Data Access** on macOS 27+).
   - Drag the app Finder is showing (the `.app` bundle, not a binary inside it) into the list
     and turn it on; approve the Touch ID / password prompt.
   - Click **Not Now** on any agent-desktop guide popup that was started from the same
     launcher: its probe is attributed to the same app, so it can't pass until step 2 is done.

3. Re-run the script until `result` is `granted`. A new grant applies to the next process; the
   launching app does not need a restart.

4. When the desktop work is finished, remind the user they can turn the grant off: it gives
   every process started from that app the same control of the Mac.

## Who needs what (verified 2026-11-05, agent-desktop 1.2.0, macOS 27)

| Launcher | App macOS checks | Drag in |
|---|---|---|
| Herdr tab (herdr-core runs under launchd) | `dev.herdr.core` | `~/.local/share/herdr-core/active/Herdr Core.app` (the real folder; `current` and `Herdr Core.app` beside it are links to it) |
| Codex app, Claude app, Terminal, iTerm, an IDE terminal | that app | the app itself |
| agent-desktop detached with no app parent | the agent-desktop binary | the exact installed file from `mise which agent-desktop` (ad-hoc signed, so every new version needs a new grant) |

Run the script rather than trusting this table: it reports the app macOS really checked.

| Permission (TCC service) | Needed for | agent-desktop state |
|---|---|---|
| Accessibility / Device Control and Data Access (`kTCCServiceAccessibility`) | every snapshot, click, type, scroll and read | `accessibility` |
| Screen Recording (`kTCCServiceScreenCapture`) | `screenshot`, `session start --screenshots` | `screen_recording` |
| Automation > System Events (`kTCCServiceAppleEvents`) | only actions that send Apple Events to System Events; `unknown` is fine until one fails | `automation` |

## Why the guide misleads under Herdr

`agent-desktop permissions --guide` offers the app bundle of the nearest parent process. A
Herdr tab's parent chain ends at herdr-core under launchd, so the guide offers the bare
agent-desktop binary. tccd still attributes the call to Herdr Core.app
(`AUTHREQ_ATTRIBUTION ... responsible_path=.../Herdr Core.app/Contents/MacOS/herdr-core`,
`AUTHREQ_SUBJECT subject=dev.herdr.core`), so granting the binary changes nothing. The
upstream troubleshooting reference says the same in general terms: "The grant belongs to the
launching app, not to the shell" (`skills get agent-desktop-macos troubleshooting`).

Herdr Core is signed by a team ID, so its grant should survive a Herdr update; re-run the
script after one to confirm. The agent-desktop binary is ad-hoc signed, so its own row (only
used outside Herdr) must be re-added after every agent-desktop upgrade.

## If the script returns `unknown`

`message` says why. `/usr/bin/log` failed (inside a sandbox it exits 64, "Cannot run while
sandboxed": run the script outside it). Or no tccd lines were found for the probe's pid: the log
may have rotated or the call never reached tccd. Or the lines were cut short, or agent-desktop
reports a grant as not given that tccd's lines do not show as denied. Read the raw lines yourself:

```
/usr/bin/log show --last 1m --style compact --predicate 'process == "tccd" AND eventMessage CONTAINS "AUTHREQ_"'
```

Use `/usr/bin/log`: in zsh, a bare `log` is a builtin and fails with "too many arguments".
