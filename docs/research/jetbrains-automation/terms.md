---
okf_version: "0.2"
type: "glossary"
title: "Terms"
description: "The words this bundle and jbctl/jbax use for how an IDE is reached and named."
resource: "python/jbctl and swift/"
version: "2026-11-07"
timestamp: "2026-11-07T00:00:00Z"
status: "draft"
stale_after: "2026-12-06T00:00:00Z"
tags: [glossary, jbctl, jbax]
---

# Terms

**Headless run**:
A run in which no step brings the IDE forward or takes the front app from the person at the machine. The
IDE may show a window, but it stays behind. agent-desktop's `--headed` flag is a different, narrower thing.
_Avoid_: headless (for an IDE launched with no UI at all).

**Debug route**:
Opening Settings from the menu bar, which brings the IDE forward. It is only for debugging a failed
headless route, and only with `JETBRAINS_FOREGROUND=1` (mise `--foreground`).
_Avoid_: headed test, foreground test.

**Station route**:
Opening Settings in the background through the IDE's station socket, which leaves the front app as it was.

**Toolbox script name**:
How `--ide` names one install: the shell-script name Toolbox gives it (`clion`, `clion1`, `pycharm`). It
names an install, not a product: several installs of one product get numbered names.
_Avoid_: product name, app name.

**Toolbox IDE**:
A Toolbox install of an IntelliJ-platform IDE: one whose app carries `product-info.json` and the station
plugin (CLion, PyCharm, IntelliJ IDEA, GoLand, RustRover, ...). Other Toolbox tools (Fleet, dotTrace, Junie
CLI, ...) are not Toolbox IDEs.
_Avoid_: tool, product.

**Running IDE**:
A Toolbox IDE whose process is up: a process with a live station socket whose executable is inside that
install's `.app`. An IDE that Toolbox did not install is not a running IDE in this sense.
_Avoid_: instance, open IDE.

**Ready**:
A running IDE whose built-in web server answers `/api/about`, with or without an open project. Its MCP
server is not part of it: an IDE can have MCP switched off.
_Avoid_: started, up, loaded.

**Not ready**:
A running IDE whose built-in web server has not yet answered `/api/about` with its build. jbctl may have
started or restarted it, or it may still be starting on its own. Not an error: it can become ready later, or be
stopped.
_Avoid_: stuck, hung, failed.

**Tool ID**:
How Toolbox names a product (`CLion`, `PyCharm-P`, `IDEA-U`, `Goland`), shared by every install of it. It
picks a product where a Toolbox script name picks one install.
_Avoid_: product code (`CL`, `PY`), display name (`IntelliJ IDEA`).

**Quit request**:
Asking a running IDE to quit the way Toolbox's Quit does: the IDE saves, closes its projects and may first
ask its user a question, which can keep it running. Nothing is killed.
_Avoid_: kill, terminate.

**Forced quit**:
A quit request that dismisses the IDE's open dialogs and skips the checks that could keep it running, but
still lets the IDE shut itself down. Not Toolbox's Force Quit, which kills the process.
_Avoid_: force kill, Force Quit.

**Config directory**:
Where an install keeps its settings (`idea.config.path`). Several installs of one product can share one,
as the three CLion installs here do, and then a setting one of them saves applies to all of them.
_Avoid_: profile, settings folder.

**Bundled skill**:
An agent skill that ships inside a Toolbox IDE (CLion's `clion-debugger`, for one): a folder with a
`SKILL.md`, carried in the IDE's plugins. Each install carries its own version of it.
_Avoid_: built-in skill, plugin skill.

**Skill copy**:
A bundled skill's files, copied out of one install into the folder where Claude Code or Codex looks for the
user's skills. jbctl looks after a skill copy it wrote that nobody has changed since; it leaves alone a copy
someone has changed and one it did not write.
_Avoid_: export, install, vendored copy.
