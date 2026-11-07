---
status: accepted
---

# jbctl starts and stops IDEs through Toolbox's own protocols

jbctl's `start` launches an install the way Toolbox's background mode does: it runs the install's own
`launchCommand` from Toolbox's `state.json` directly, with a project folder as its argument when one is given.
`stop` sends the station socket's `/exit {userInitiated:true, force:false}`, the same request Toolbox's Quit
sends. `restart` is the IDE's own `/exit` with `restart:true`, because Toolbox has no restart. We chose this
because the owner wants jbctl built on what JetBrains already provides, with accessibility automation
(agent-desktop, rea) only where it leaves a gap. Toolbox offers no supported CLI, MCP or API to open or close a
tool, but these are the routes it uses itself (decided 2026-11-06, issue #502, Q5).

## Considered options

- **A `jetbrains://<channelId>.tool/` link through the Toolbox binary** (chosen first, then dropped): Toolbox
  launches the right install, but passes the link on to the IDE as its argument. The IDE rejects it and shows
  "Cannot Open URI" on every start (measured on RustRover). The link forms Toolbox consumes itself
  (`navigate`, `checkout`) open only projects Toolbox already knows, and no link form takes a folder path.
- **`open -n -g <app>`**: Toolbox's normal launch plus macOS's "don't activate" flag. It is not what Toolbox's
  background mode does, and the IDE took the front in every measured launch anyway.
- **Pressing Toolbox's UI** (Open, Quit, Force Quit) through agent-desktop: it would activate Toolbox, its
  Compose UI's accessibility tree is unverified, and its Quit ends in the same `/exit` request anyway.
- **Toolbox's Force Quit for `--force`**: that is a SIGKILL. `--force` is instead the IDE's own forced quit
  (`/exit force:true`), which dismisses dialogs and skips vetoes but still shuts the IDE down normally.

## Consequences

- `start` does not need Toolbox running; it reads Toolbox's `state.json` for the install's `launchCommand`.
- `start` and `restart` are foreground actions, so they act only with `--foreground` or
  `JETBRAINS_FOREGROUND=1`, the opt-in the menu-bar route uses. Every measured launch took the front: three
  Toolbox link launches and one IDE restart, all on RustRover. The direct `launchCommand` launch, with or without a project
  folder, and `open -g` were not run.
- `start` and `restart` refuse while another install of the same product runs, or while the target config
  directory's `.lock` names a live process. For `restart`, only the IDE being restarted is exempt; any other
  live owner still blocks. Installs of one product can share a config directory, and the IDE
  lets an install from a different app replace that marker. No outside source proves which config a running
  IDE uses, so this is a collision guard, not a proof.
- `stop` and `restart` refuse while the IDE has any window other than a project frame or the Welcome screen,
  any modal window, or a window whose state cannot be read, or when its windows cannot be inspected at all.
  Settings is not AX-modal (measured), so the check rests on jbax's window kinds, which come from the AX subrole
  rather than the title and so hold in any language. A forced quit dismisses every modal, so it is sent
  only when none is observed, checked again right before the request: an exit question shown as a dialog is
  left for its user to answer. A dialog opened between that check and the request is a race only an IDE-side
  guard could close.
