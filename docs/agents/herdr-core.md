# herdr-core: checking it without starting one

herdr-core (`hc`) is the background program that owns every terminal and agent session; Herdr.app is
the window that shows them. They find each other through one Unix socket. This page is for an agent
that has to check or talk to that core. The design is
[docs/designs/herdr-core-socket-cutover.md](../designs/herdr-core-socket-cutover.md).

## Never press "Install it for me"

When the window can't reach a core it shows "Herdr needs herdr-core … Install it for me". The
sessions are usually still running at another socket. Don't press the button and don't tell anyone
to: run the doctor and report what it shows.

## How hc picks its socket

In this order (hc `paths.rs:28-34`):

1. `HC_SOCKET`;
2. the `socket` key in `~/.config/herdr-core/config.toml`;
3. `$XDG_RUNTIME_DIR/herdr-core/<session>.sock`;
4. otherwise `~/.local/state/herdr-core/default/default.sock`.

The default path is the goal: no routing input set anywhere, so the Dock, a login shell, `env -i`
and every agent shell all reach the same core. A core keeps the environment it started with, and
so does every program it starts, so one stray `XDG_RUNTIME_DIR` at start time splits the paths
until that core stops. Nothing guards the core's automatic start: after a crash, reboot or hc
update, whichever client connects first starts the next core with its own environment. The
doctor's V2 and the `/verify` herdr section show when that happened.

## Why nothing here runs hc

An hc client starts a core itself when it can't connect, and `HC_SOCKET` doesn't stop that
(hc `client.rs:85-99`). A check that runs `hc` can start the very second core it is meant to
find. So:

- **The doctor never runs hc, herdr-core or herdr-app.** It reads sockets, processes and files from
  outside. Its V15 check enforces this on its own source, `python/home/src/hometools/herdr.py`.
- **Versions come from Info.plist**, not `hc --version`: hc from
  `~/.local/share/herdr-core/current/Contents/Info.plist` (`current` links to the active build) and
  the app from `~/Applications/Herdr.app/Contents/Info.plist`.
- **Any other hc call goes through `hc-safe`** (below).

## The doctor

```
mise run herdr:doctor
```

It reads with `lsof`, `pgrep -a`, `ps`, `launchctl getenv`, the kernel's copy of the app's
environment (`sysctl` KERN_PROCARGS2), one clean login shell (`env -i … /bin/zsh -lic`), `git
ls-files` and the files themselves. It writes nothing. The task runs the package's own
environment's python directly (`-I -B`, no bytecode), never uv, which sets up its cache on every
run, and never syncs: run `mise run //home:sync` once first, or it exits 2 saying so. It prints
one JSON line:

- `observation`: what it read. `cores` are processes whose argv is `hc` or `herdr-core` followed by
  `--hc-launchd` (started by launchd) or `serve` (started directly); holders (`hold`) and the
  window's client (`connect`) are not cores. `listeners` hold the default socket, `lock_path` is
  what `core.lock` advertises (a socket path, not a pid), `old_path_holders` hold anything under
  `~/.local/run/herdr-core`, `routing` lists every routing input set to a value other than its
  default, and `unknown` names each input it could not read. Home folders print as `~`.
- `checks`: `pass`, `fail` or `unknown` for V1, V2, V3, V4, V5, V7, V10, V11 and V15 (the design's
  check table). A check fails only on what was read, and a failure read wins: one stale reference
  fails V11 even when another file can't be read, and no skills-lock tag fails V10 even when hc's
  version can't be read. Otherwise, when an input it needs could not be read (lsof or pgrep
  missing or failing, an unreadable or malformed `core.lock`, plist, skills lock, herdr config,
  repository file, skill folder or socket folder), the check is `unknown`, never passed or failed:
  an unread input is not an absence. Every presence check is an explicit `stat`. Only a missing
  path or a dangling link counts as absent, because `Path.exists`, `is_file`, `is_dir` and `glob`
  read a permission error or a link loop as "not there".
- V15's socket check is per folder. The doctor lists the `*.sock` files in the default socket folder
  and in `~/.local/run/herdr-core` before and after its run, and compares each folder only when it
  read that folder both times. A folder it can't read is the unknown `sockets ~/<folder>`; a change
  seen in the other, readable folder still fails V15, since a failure read wins.

| Exit | Meaning |
|---|---|
| 0 | every check passes |
| 1 | at least one check fails |
| 2 | a usage error, or hometools could not start (one JSON error on stderr) |
| 3 | at least one check is unknown, and none failed |

Unknown blocks green: treat exit 3 as not done. With no Herdr window running, V7 is unknown: there
is no window environment to read.

`pgrep -a` matters: macOS `pgrep` leaves out its own ancestors, and inside an hc terminal the core
is one, so a plain `pgrep -f` from there finds no core. The app's environment comes from the
kernel, each `NAME=value` exact; `ps -E` joins them with spaces and can't be split back. The kernel
gives none for a platform binary, so an empty environment is unknown for V7 and V2, never a pass.

The login shell runs your startup files, so it runs under `sandbox-exec`. It may not start any
herdr program (the links in `~/.local/bin` and the install folders), nor `open`, `osascript` or
`launchctl`, which have launchd start a program outside the sandbox, and it may write only to the
temp folders (`/private/tmp` and `/private/var/folders`, never an inherited `TMPDIR`). A refused
start makes V1 and V2 unknown. The doctor sees it from the "not permitted" message naming the
program. macOS logs no sandbox denial, so a startup file that throws that message away
(`2>/dev/null`, `exec 2>/dev/null`, a test of the exit status) hides it. The program still does
not run.

So V2 reports what a sandboxed login shell sets. A value a herdr program would compute there can't
be seen. Before the probe, the doctor scans your zsh config as a **tripwire, not a proof**. A static
scan can't prove what zsh runs (sourcing, PATH lookup, expansion, compiled `.zwc` files), so the scan
follows no `source` and claims nothing about files outside its set. The authoritative routing check
is **V9 login**: a real login shell running hc at each cutover gate.

The set is read as plain text, with no shell:
- `~/.zshenv`, `~/.zprofile`, `~/.zshrc`, `~/.zlogin` and `~/.zlogout`;
- every regular file at any depth under `~/.zshrc.d`, `~/.zprofile.d` and `~/.config/zsh`. A link to
  a file is read. A linked folder is entered only when it resolves inside HOME.

`$ZDOTDIR` isn't consulted: the probe starts zsh with a clean environment, so zsh reads from HOME.

V2 is unknown when any of these holds:
- A line names a herdr program. With quotes and backslashes removed, a line counts when any word is
  `hc`, `herdr-core`, `herdr-app`, `hc-safe`, `Herdr`, `Herdr.app`, `open`, `osascript` or
  `launchctl`, or a path ending in one. So `"hc"`, `command hc`, `if hc` and `$HOME/.local/bin/hc`
  all count. A full-line comment doesn't. The entry reads `startup-files ~/<file>:<line> may run a
  herdr program; startup files are scanned as a tripwire; V9 login proves routing`.
- A `.zwc` is a startup file's compiled sibling (such as `~/.zshrc.zwc`) or lies under one of the
  three folders. Other `.zwc` files in HOME, such as the `~/.zcompdump-*.zwc` completion caches, are
  not startup code.
- A file or folder in the set can't be read.

A false alarm only costs an unknown. What the scan can't see still can't start in the sandbox, and
V9 login proves routing.

## hc-safe

```
hc-safe [--own-env] <expected-core-pid> <socket> -- <hc args...>
```

It refuses unless `lsof` shows exactly one process holding `<socket>` and it is the expected pid;
runs `hc` with `HC_SOCKET=<socket>` under `sandbox-exec` with `(deny process-fork)`, so a core that
vanished in between can't be restarted by the call; then checks the listener again.
`--own-env` keeps the caller's environment, to test that shell's own routing.

| Exit | Meaning |
|---|---|
| 0 | hc succeeded and the listener is unchanged |
| 80 | core-gone: the check before failed, hc exited 5 (unavailable), or the listener changed |
| 81 | a usage error in hc-safe's own arguments |
| 82 | `sandbox-exec` is missing or could not apply (a Codex `-s read-only` shell): report BLOCKED |
| other | hc's own exit code |

## Updating herdr

- **A new Mac: open Herdr first.** No package ships herdr-core; Herdr.app's first run installs it,
  `hc` included. Until then the post-tools skill hook prints "herdr-core is not installed yet; open
  Herdr once, then rerun mise bootstrap", installs no herdr-core skill and lets bootstrap go on, so
  the doctor's V10 shows the gap. Open Herdr once, then run `mise bootstrap` again.
- **The core: `hc update` from a clean shell.** Run it from a shell started with `env -i`, for
  example `env -i HOME="$HOME" USER="$USER" /bin/zsh -lc 'hc update'`, and run it again when hc asks
  you to. An update keeps the terminals running; `hc server stop` followed by a start ends them.
  From herdr-core 0.1.19, updates and `hc server restart` keep the environment the core started with.
  The update to 0.1.19 itself still takes the updater's environment once, which is why the clean shell
  matters (herdr-core CHANGELOG, 0.1.19).
- **Herdr.app: only its own updater.** The `brew-cask:herdr-app` entry in the mise config only adopts
  the app, and the Homebrew cask can lag behind the app's releases: on 2026-11-08 the cask offered
  0.1.13 while the app had already updated itself to Herdr 0.1.14. Never update the app through brew.
- **The doctor's V10 after a core update.** V10 stays red until the post-tools skill hook runs again.
  The hook installs the herdr-core skill tag that matches `hc --version`, so the rerun brings it back
  to green.
- **Detached programs outlive their tab.** From herdr-core 0.1.19 on macOS and Linux, a program that a
  terminal started with `nohup`, `setsid` or as a daemon keeps running after its tab closes, so its
  port may stay busy until you stop it. Terminals opened before the update keep the old behavior, which
  ends such programs with the tab, until they are reopened (herdr-core CHANGELOG, 0.1.19).
- **Local network prompt.** After a core update, macOS may ask once more to let Herdr Core reach the
  local network. Allow it (herdr-core CHANGELOG, 0.1.18).

## Test cores stay isolated

A test or scratch core never shares a socket or state folder with the real one. Run it under
`env -i` with a private `HOME`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_DATA_HOME`,
`XDG_CACHE_HOME` and `TMPDIR` under one scratch folder, a unique `HC_SESSION` and
`SSH_CONNECTION=hc-scratch`, and check before every command that the socket it resolves lies under
that folder. Never touch launchd from a scratch run. The doctor's own tests use stand-ins and never
reach a core.
