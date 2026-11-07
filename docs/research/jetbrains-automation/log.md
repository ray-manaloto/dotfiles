# Directory Update Log

## 2026-11-05
* **Creation**: from the spike session's notes and local recordings (untracked), and the
  JBR / intellij-community source answers from dotfiles-c6. No dotfiles repo files were written.
* **Results**: DIRECT set three ways, each after the owner reset it to "All agents":
  * headed: a physical click on the dropdown, then Up/Up/Return;
  * foreground headless: Tab, then Space/Down/Return;
  * background: AXSelected on the dropdown's child 0, then AXPress OK.
  * Verified each time by MCP `tools/list` (1 tool → 88) and by `mcpToolFilter.xml` being removed.
* **Added**: rea installed and patched (launch-time fallback, same-size window disambiguation, Swing
  labels). Background Settings navigation found: rea key-entry into the Settings search field.
* **Added**: `jbctl` first cut. It runs `router-direct` end to end, with only the Settings opening
  bringing CLion forward.
* **Rejected**:
  * background keys (JBR rejects non-mouse focus requests while the app is inactive);
  * AXPress on popup rows (only selects);
  * tree-row AXPress for navigation (inert in the background);
  * `jetbrains://…/settings` as a background opener (always activates);
  * Frida on CLion (hardened runtime, SIP on).
* **Failed**:
  * menu-bar "Settings…" AXPress while CLion is inactive (AppKit drops it);
  * a CGEventPostToPid click on a popup row (ignored);
  * the first `--headed click @ref` on the dropdown (target point not proven; `mouse-click --xy`
    worked).
* **Added**: `--ide <Toolbox shell-script name>` for every IDE command and `jbctl resolve`. Toolbox channel
  file, then `product-info.json`, then the station-socket pid, then the one loopback listener that answers MCP
  `initialize`; it refuses when anything is ambiguous. This replaces "the first `com.jetbrains.*` app",
  which had only matched CLion by list order with PyCharm and WebStorm running. See [[tools]].
* **Live runs** (owner's go, headless):
  * jbctl 9/9 at 100%. They found two bugs, both fixed: a second "Search" field on Exposed Tools, and a
    banner's Dismiss link in the breadcrumb.
  * jbax 2/2, but `select`'s commit path is not covered: headless, the dropdown cannot be put on "All
    agents" (row 1). The JBR source has only AXSelected, which highlights a list row or commits row 0, and
    the Swing `BasicComboPopup` commits only on a mouse release or Enter.
* **Changed**: `resolve` no longer probes every listener of the pid. It takes the port from the plugin's own
  order: forced port, then `mcpServer.xml`, then the platform-prefix default. It then checks that the pid
  listens there and answers `initialize`. Measured: CLion 64362 (default), PyCharm 64463 (saved, because its
  default 64462 was CLion's private port), WebStorm 64542 (default).
* **Found**: Settings opens in the background through the IDE's station socket (`POST /protocolHandler`,
  `jetbrains://idea/settings?name=...`); one live run kept the front app. See [[settings-open-and-navigation]].
  Reviewed with a Codex peer, and we agreed:
  * the station route is the default;
  * the menu route is kept only behind `JETBRAINS_FOREGROUND=1`;
  * `name=` and not `page_id=`, because `page_id=` can block on a modal dialog;
  * `check_background` fails closed on states that may activate the IDE.
* **Fixed** (peer review):
  * the JVM options now follow the launcher (`<app>.vmoptions` beside the bundle, else
    `<config>/<launcher>.vmoptions`, then `product-info` arguments; lines trimmed);
  * a `-Didea.config.path` option moves `mcpServer.xml`, read as PathManager does;
  * the Swift live tests are one ordered test, so the two can no longer run in parallel against the IDE.
* **Changed** (with a Codex peer and the owner): no code is marked to reach a coverage gate, except the debug route
  that brings the IDE forward.
  * jbctl marks only that route, with `# pragma: foreground` in `ide.py`, and `mise run //jbctl:markers` (part of
    `//jbctl:check`) fails on any other pragma. The old `no cover` guards are gone.
  * jbax keeps its foreground-only commands (`focus-owner`, `popup`) in `Foreground.swift`. That is the one file
    the gate skips, because llvm-cov can leave out files but not lines (llvm-project#33625). No line is marked.
  * `jbctl coverage-gate` requires every other `Sources/JBAXKit/*.swift` file to be in the export. A missing or
    empty file fails.
  * Everything else that a run cannot reach stays visible as uncovered, under measured #502 MVP floors: jbctl 98.08%
    (three guards, among them a jbax crash, and the move to the page asked for), jbax 87% of lines and regions (AX and JSON failure fallbacks, plus states no working IDE
    produces).
  * The owner rejected a stand-in `agent-desktop` for the debug route, so the real route is proven only by
    `--foreground` runs.

## 2026-11-06: Q5 lifecycle spike on RustRover (#502)

* **Measured** (with the owner's go): RustRover, not running before, started with the Toolbox binary and its
  channel link (`jetbrains-toolbox jetbrains://RustRover-<id>.tool/`). It was then restarted with the IDE's own
  `/exit restart:true` and stopped with the quit request (`/exit force:false`). `lsappinfo front` was logged
  every 50 ms throughout.
  * **The Toolbox link launch is a foreground action.** The binary handed the link to the running Toolbox and
    exited 0 in 2 s. RustRover came to the front 5 s after the launch and held it for 5 s, then the previous app
    got it back.
  * **The IDE's own restart is a foreground action.** The old pid ended 1.4 s after `/exit` (HTTP 200
    `{"immediate": false}`). The restarted IDE took the front for 1 s and had a new pid 13 s after the request.
  * **The quit request** ended the IDE in 1.1 s (HTTP 200). Nothing was killed, and the front did not change.
  * **The mixed-case channel id worked:** the pid's executable was inside RustRover.app. This install has only
    one channel, so picking one of several installs is still unproven.
  * **`/api/startUpMeasurement` never became ready** in 4 minutes, after either start. RustRover was on its
    Welcome screen with no project. `/api/about` answered within 3 s on each start (ports 63343, then 32366).
    Whether the measurement waits for a project to open is not yet known, so the Ready rule needs another
    signal for an IDE with no project.
* **Measured, second run** (with the owner's go): RustRover started through the same Toolbox link and stopped
  with the quit request. `lsappinfo front` was logged throughout.
  * **The Toolbox link launch took the front again:** RustRover was in front from 10 s to 15 s after the
    launch, then the previous app got it back. The quit request ended it in 1.2 s with no front change.
  * **MCP does not answer in this RustRover.** Nothing listened on its default MCP port (64522), from the
    configuration jbctl reads, in 2 minutes. The pid listened only on 32366 and 63343. Its MCP server
    appears to be switched off: CLion's is on only because it was enabled. So MCP cannot be the Ready signal
    for every IDE.
  * **`/api/about` answered 1.6 s after the pid appeared**, on port 32366, with `name`, `productName`,
    `edition`, `buildNumber` and `baselineVersion`.
  * **`/api/startUpMeasurement` on that port returned HTTP 400** (an HTML Bad Request page). A bug in the
    spike stopped it after that one sample, so the other port (63343) was not asked, and the run does not
    show whether the measurement depends on an open project.
* **Measured, third run** (with the owner's go): RustRover started through the same Toolbox link. jbctl polled
  `/api/startUpMeasurement` on both listening ports (32366 and 63343) for 150 s, then stopped it with the
  quit request. `lsappinfo front` was logged throughout.
  * **`/api/startUpMeasurement` never answered with a report.** Both ports returned HTTP 400 (an HTML Bad
    Request page) from the first request onwards. That was the same on the Welcome screen, so it is not
    "start-up in progress". From a script, this endpoint is not usable as a Ready signal in RustRover. The
    earlier "start-up in progress" reply came from CLion.
  * **The built-in server rate-limits:** polling both ports once a second drew HTTP 429 Too Many Requests
    after about 15 s, and again roughly every minute. A Ready check must ask rarely.
  * **`/api/about` answered on both ports** 5.9 s after the launch, with the same 145-byte reply.
  * **Front app:** RustRover took the front 1.6 s after the launch. The next change came 92 s later, and
    later changes between CLion, Zed and Herdr may have been the owner's. RustRover had the front again 113 s
    to 125 s after the launch. The log does not show whether the IDE or the owner caused that. The quit
    request ended it in 1 s and changed nothing.
* **Found** (from Toolbox's jars and CLion's classes; no link was opened): the "Cannot Open URI ...
  IllegalArgumentException: RustRover-<id>" notification after the link launch comes from the IDE. Toolbox
  passes any link path it does not consume (anything but `navigate`, `diogen`, `checkout`, `download`) to the
  IDE as its argument. The IDE's `JBProtocolCommand` needs `<host>/<command>/...` with a registered command,
  and `RustRover-<id>.tool/` has none. No link form launches a chosen install without that, and none opens a
  project by folder path: `navigate` and `checkout` match only projects Toolbox or the IDE already knows.
  Toolbox's background mode, and its `checkout` for a known project, run the install's executable with the
  project folder as its argument. That is the documented way to open a project at launch.
* **Changed** (owner's decision): `start` runs the install's `launchCommand` the way Toolbox's background mode
  does, with no link (ADR 0002 updated). Ready is `/api/about` answering, polled no faster than every 2 s.

## 2026-11-07: Q5 built: jbctl status, start, stop and restart (#502, ADR 0002)

* **Built**, after an adversarial review by Codex (GPT-6-Astra, xhigh) that ended SHARED, and the owner's three
  decisions:
  * **`jbctl status`** (read-only) lists running Toolbox IDEs, or `--ide`/`--product <tool id>`/`--all`. It shows
    each one's pid, its state (stopped, starting, running, ready) and MCP (answering, not-answering, unknown,
    with the port and a reason).
  * **`jbctl start`** runs the install's `launchCommand`, as Toolbox's background mode does, with `--project` as
    one argument. **`stop`** sends Toolbox's Quit request, and with `--force` a forced quit only when no dialog
    is open. **`restart`** is the IDE's own restart. `start` and `restart` bring the IDE forward, so they act
    only with `--foreground` or `JETBRAINS_FOREGROUND=1`. `stop --check` and `restart --check` run every guard
    and report `would-stop`/`would-restart` or the refusal, sending nothing. The headless live session uses only
    those, so a race that closed Settings first could not quit the working IDE. Each waits for its result: Ready is `/api/about` answering
    with the install's build, asked at most every 4 s, and every 30 s after an HTTP 429.
  * **Every request is pinned** to one process lifetime (pid, start time and owned station socket) and checked
    again just before it is sent. Nothing is ever killed.
  * **Guards:** stop and restart refuse while the IDE has any window other than a project frame or the Welcome
    screen, a modal one, or an unreadable one. start and restart refuse while another install of the product runs, or while the target config
    directory's `.lock` names a live pid. A file lock per product and per config directory (under
    `~/.local/state/jbctl/lifecycle/`) holds off a second jbctl. `--all` prints a plan and acts only with
    `--yes`, and a product with several installs is skipped, never guessed.
  * `station.py`, `mcp.py` and the process checks moved to httpx and psutil. The Settings ownership record now
    holds psutil's start time.
  * **Offline:** the stand-in IDE is a real process that owns a station socket, answers `/exit` (quit, relaunch
    through its launcher, stubborn, deaf, refusing) and serves `/api/about`. 29 lifecycle tests use it.
  * **Live:** the headless suite checks that stop and restart refuse jbctl's own open Settings dialog and send
    nothing. `//jbctl:lifecycle <spare ide>` runs start, restart and stop for real, on a throwaway worktree of
    the local mise checkout. The direct launch and the project-open check are NOT_RUN until the owner runs it.
* **Measured** (CLion 2026.3, headless, jbctl's own Settings opened and then cancelled, the front app unchanged):
  **Settings is not AX-modal.** `jbax windows` read it as `{"kind": "settings", "modal": false}`, and while it was
  open the four project frames read as `"kind": "other"`. A guard on the modal flag alone would have let `stop`
  quit the IDE with Settings open. The guard now refuses any window that is not a project frame or the Welcome
  screen. With that guard, `jbctl stop --ide clion --force` and `jbctl restart --ide clion` with Settings open
  both printed `refused` ("5 dialog or unreadable windows are open"), exited 1, and sent nothing. CLion kept its
  pid and the dialog stayed open until Cancel.
* **Measured** (headless, no `--foreground`, 2026-11-07, after the review fixes): `mise run //jbctl:coverage clion`
  passed with 90 tests and 2 skipped (the foreground and lifecycle-live tests) at 97.68%: 930 statements with 18
  missed, and 232 branches with 9 missed (in 7 partly covered branch points). The run did not reach the cli.py page move, so the floor is
  97.68%, down from 98.08%. It is lower because of the paths no run produces on demand: the lifecycle races and
  toolbox.snapshot's SystemError handling. The live session's `stop --check` and `restart --check` refused against
  the working CLion with jbctl's own Settings open, sending nothing, and CLion kept its pid. `lsappinfo front`
  never left the owner's app, and no Settings window was left open.
* **Found** (a live run): psutil 7.2.2 on Python 3.15 can raise `SystemError` from `proc_cmdline` for a process
  that exits while it is read. A scan of every process's command line therefore failed whenever another process
  exited. jbctl reads processes through one helper that treats NoSuchProcess and that SystemError as "not
  running".
* **Measured** (`mise run //jbctl:lifecycle rustrover`, with the owner's go, 2026-11-07 03:06): a real start,
  restart and stop of RustRover on a throwaway worktree of the local mise checkout. `lsappinfo front` was logged.
  * **start** (direct `launchCommand` launch with the project folder): ready in seconds. RustRover took the front
    3 s after the launch, so start is a foreground action, as the spikes measured.
  * **RustRover asked whether to trust the new folder** ("Trust and Open Project?", a dialog). **The project-open
    check passed wrongly:** it matched the project's name in the dialog's title. It now counts only a
    frame-sized project window.
  * **restart and stop refused** with "1 dialog or unreadable windows are open" and sent nothing. That is the
    guard working on a real dialog. The test then raised `KeyError: previous_pid` instead of reporting the
    refusal (fixed: it checks the action first). The worktree was kept, because the IDE still ran.
  * After the owner trusted the folder, the steps were finished through the CLI. `restart --foreground` gave a new
    pid, and the project frame reopened with the worktree's name (compared privately). `stop --check` gave
    would-stop, and `stop` quit RustRover with nothing killed. Then the worktree was removed. RustRover held the
    front for 13 s across the restart, then the owner's app had it again.
  * **For the next runs**, the test creates its worktree under `~/.local/state/jbctl/lifecycle-projects/`, which
    the owner adds once to RustRover's Trusted Locations. jbctl never changes the IDE's settings.
