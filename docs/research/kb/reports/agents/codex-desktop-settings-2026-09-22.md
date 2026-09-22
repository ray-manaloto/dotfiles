# Codex CLI, app-server daemon and ChatGPT Desktop: settings and env vars (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message (its own Write was refused by the harness). Raw probe
> outputs were left in the session scratchpad: `doctor-*.txt`, `doctor-*.json`,
> `codex-src/`, `codex-0155/`, `appcast.xml`, `manage-app-updates.md`,
> `live-envvars.md`. HTML entities introduced in transit restored.

## TL;DR
- **Four codex copies, four versions.**
  - mise pin: **0.154.0**.
  - Standalone `~/.local/bin/codex`: **0.151.0**.
  - ChatGPT Desktop's bundled copy: **0.155.0-alpha.9.2**.
  - Latest stable upstream: **0.155.1**, published 2026-09-18T20:03Z (`gh api repos/openai/codex/releases/latest`).
- **No managed daemon is running.** `~/.codex/app-server-daemon/app-server.pid` names pid 61145, started Aug 29, and that process is gone. The control socket file exists, but no process holds it. `codex app-server daemon version` fails with `Connection refused (os error 61)` on 0.154 and on the Desktop's bundled binary.
- **The daemon always runs the standalone binary, whichever codex you invoke it from.** That binary is `$CODEX_HOME/packages/standalone/current/bin/codex`. So the mise pin can never govern the daemon.
- **Daemon auto-update is structurally impossible on this install.** The updater needs `~/.codex/packages/standalone/auto-update-version`, and that file is absent. The installers at tags 0.151.0–0.154.0 never wrote it. One fresh latest-channel install creates it.
- **The Desktop app can be pointed at an external codex** through two undocumented env vars read from its `app.asar`:
  - `CODEX_CLI_PATH` replaces the bundled binary.
  - `CODEX_APP_SERVER_USE_LOCAL_DAEMON=1` connects to the daemon socket instead of spawning its own server.
  - The two are mutually exclusive.
  - The app imports your interactive login-shell environment before it spawns codex, so an export in the shell rc files reaches it.
- **The Desktop's bundled codex updates only through the app's own updater (Sparkle), and it ships alpha builds.** It cannot be held on stable 0.155.1 by itself. A newer app build (26.917.51856) was published today at 17:18Z, 14 minutes after the app's last update check at 17:04Z.

## 1. Settings and env vars by topic (with evidence)

### A. Which binary the daemon runs
| Item | Fact | Evidence |
|---|---|---|
| Binary path | Hard-coded to `CODEX_HOME/packages/standalone/current/bin/codex`. Falls back to the legacy flat `current/codex`. No config key or env var overrides it; only `CODEX_HOME` moves it. | `codex-rs/app-server-daemon/src/managed_install.rs:22-34`; `lib.rs:302-316` (`managed_codex_bin(codex_home)`); README:115 "lifecycle commands always use the standalone managed binary path" (all @ `rust-v0.155.1`) |
| Non-standalone installs | `start`/`bootstrap` fail with "managed standalone Codex install not found … requires the standalone install managed by the Codex installer". | `lib.rs:870-891` |
| Upstream request | "Support externally managed app-server daemon executables" is **OPEN**. | openai/codex#41188 (live `gh api`) |
| Environment | A running daemon keeps the environment it started with. Clients don't change it. | README:22-24 |

### B. Daemon update schedule
| Key / var | Default | Evidence |
|---|---|---|
| `~/.codex/app-server-daemon/settings.json` → `updater.autoUpdateEnabled` | `true` | `settings.rs:25-33, 81-83`; README:48-58 |
| `updater.updateIntervalMinutes` | 60. The first check runs after 5 minutes. No upper cap. | `settings.rs:13`; README:48-58 |
| `shutdownGraceSeconds` | 60, max 300 | `settings.rs:14-15`; README |
| `remoteControlEnabled` | false | `settings.rs:28` |
| Updater gate | Requires auto-update on, **and** the release dir named `x.y.z-<target>`, **and** `packages/standalone/auto-update-version` equal to that release name, **and** the binary supporting `app-server daemon pid-update-loop` | `managed_install.rs:37-73, 76-92`; `lib.rs:788-825, 849-857` |
| `codex app-server daemon update` | Present in the 0.155 builds only. On this host only the Desktop's bundled alpha has it. | Probe: `update --help` exit code 0 on the Desktop's alpha, 2 on 0.151 and 0.154. A bogus subcommand also returns 2, so the probe discriminates. |
| Reboot | The updater loop does not survive a reboot. A managed `start` restarts it. | README:130 |
| Known hazard | Auto-update force-kills active turns after the 60 s drain. **OPEN.** | openai/codex#40969 |

### C. CODEX_HOME and config location
- `CODEX_HOME`: default `~/.codex`, and the directory must already exist. `CODEX_SQLITE_HOME` is overridden by the `sqlite_home` config key. Evidence: offline `config-file__environment-variables.md:17-18`.
- Control socket path: `CODEX_HOME/app-server-control/app-server-control.sock`. It is derived only from `CODEX_HOME` (`codex-rs/app-server-transport/src/transport/mod.rs:67-73`).
- The Desktop preserves an explicitly set `CODEX_HOME` over the shell import (`app.asar` byte offset ~7206106: `…Object.assign(process.env,s.userEnv),OE!=null&&(process.env.CODEX_HOME=OE)`).
- Two app-server env vars can relocate managed config: `CODEX_APP_SERVER_MANAGED_CONFIG_PATH` and `CODEX_APP_SERVER_DISABLE_MANAGED_CONFIG` (`codex-rs/app-server/src/main.rs:27-28`).

### D. Release pinning (standalone installer)
- `install.sh` reads these env vars:
  - `CODEX_RELEASE` (default `latest`; `--release` overrides it)
  - `CODEX_NON_INTERACTIVE`
  - `CODEX_INSTALL_DIR` (default `~/.local/bin`)
  - `CODEX_INSTALLER_USE_RELEASES_OPENAI_COM`
  - `CODEX_HOME`
  - `CODEX_INSTALL_IF_LATEST` and `CODEX_UPDATE_FROM_RELEASE`, which the updater uses internally.
  - Evidence: `scripts/install/install.sh:5-22, 84-91, 1157-1195` @ `rust-v0.155.1`.
- **Pinning an explicit release deletes the auto-update marker; `latest` writes it.** Evidence: `install.sh:1228-1233`.
- The marker code is absent from the installers at `rust-v0.151.0`, `0.152.0`, `0.153.0` and `0.154.0` (0 hits for `auto-update-version`). Control arm: `CODEX_INSTALL_DIR` gets 1 hit at 0.151.0. This explains why the Aug 29 install has no marker.
- **Installer hazard in a shell where mise's codex comes first on PATH:**
  - `classify_existing_codex` sees mise's `#!/usr/bin/env node` wrapper and reports "npm".
  - It then prompts to run `npm uninstall -g @openai/codex` (`install.sh:799-826, 909-933`).
  - `CODEX_NON_INTERACTIVE=1` answers No by default (`install.sh:831-837`).

### E. Hook trust
- Trust is stored per hook hash in `~/.codex/config.toml` as `[hooks.state."<source>:<event>:<i>:<j>"] trusted_hash = "sha256:…"` (observed, `~/.codex/config.toml:383-527`). Changing a hook requires re-trusting it via `/hooks` (offline `hooks.md:57-72`).
- `--dangerously-bypass-hook-trust` is **CLI-only**:
  - It is a `ConfigOverrides` field (`codex-rs/core/src/config/mod.rs:2614, 3278-3285`).
  - It does not exist as a key in `schemas/codex-config.json`: 0 hits, while `check_for_update_on_startup` is present.
  - It **disables implicit daemon reuse**, so the TUI falls back to its own embedded server (`codex-rs/tui/src/startup_orchestration.rs:153-160`).
- **Any `-c` override also disables daemon reuse**, as do non-default loader overrides and `--strict-config` (`codex-rs/tui/src/lib.rs:988-999`).
- Reuse is also skipped when `CODEX_EXEC_SERVER_URL` is set (`lib.rs:946`; README:25).

### F. `features.multi_agent_v2`
- Stage: stable, `default_enabled: false`, described as "Enable task-path-based multi-agent routing" (`codex-rs/features/src/lib.rs:200-201, 1274-1279`).
- Effective state is `false` on all three binaries (`codex features list`).
- Schema: either a boolean or a table (`MultiAgentV2ConfigToml`) with keys `enabled`, `max_concurrent_threads_per_session`, `default_wait_timeout_ms`, `min_wait_timeout_ms`, `max_wait_timeout_ms`, `wait_agent_enabled`, `tool_namespace`, `usage_hint_*` and others (`schemas/codex-config.json`).
- It must be set in a config file. Passing it with `-c` would disable daemon reuse (section E).
- The earlier note that it is "unreachable from `codex exec`" (`task_plan.md` 9.1b(d)) is **inherited, not re-verified here**.

### G. Control socket, `~/.codex/app-server-control/`
- Contents: `app-server-control.sock` and `app-server-startup.lock`, both dated Aug 29 10:35.
- **Nothing is listening on the socket:**
  - `lsof -U` returned 575 rows with 0 matches for `app-server-control`.
  - Control arm: the same listing shows 134 `.sock` paths, including the Desktop's own `/tmp/codex-browser-use/*.sock`.
- `codex doctor` reports `status stale or unreachable`, `settings.json (missing)`, `app-server-updater.pid (missing)`, `mode ephemeral`.

### H. ChatGPT Desktop (`/Applications/ChatGPT.app`)
- **Identity:**
  - Bundle id `com.openai.codex`, version 26.915.31945 (build 9922).
  - Electron app containing `Sparkle.framework`, with an `SUPublicEDKey` entry.
  - `com.openai.chat` belongs to a separate app, `/Applications/ChatGPT Classic.app` (found with `mdfind`).
- **Updater state** (`defaults` domain `com.openai.codex`, key names only; update booleans shown):
  - `SUAutomaticallyUpdate=1`, `SUEnableAutomaticChecks=1`.
  - `SULastCheckTime=2026-09-22 17:04:58 +0000`.
  - `CodexSparkleSeenUpdateVersions`, `LastRunAppBundlePath=/Applications/ChatGPT.app`.
- **Update feed:** `https://persistent.oaistatic.com/codex-app-prod/appcast.xml`. Its newest item is **26.917.51856**, published 2026-09-22 17:18:25Z (arm64). The feed does not say which codex that build bundles.
- **Env vars the app reads** (extracted from `app.asar`; undocumented):
  - Absent from the live `learn.chatgpt.com/docs/config-file/environment-variables.md` (0 hits; control: `CODEX_HOME` gets 4).
  - Absent from the offline docs.

  | Var | Behavior | asar evidence (byte offset) |
  |---|---|---|
  | `CODEX_CLI_PATH` | Overrides the bundled `Resources/codex`. A bare name is resolved via PATH; a path is validated for existence. The app spawns `<bin> -c features.code_mode_host=true app-server --analytics-default-enabled …`. | ~10779673 (`CQ`), ~10780535 (`wQ`), ~10769182 (`ZZ`/`EQ` args) |
  | `CODEX_APP_SERVER_USE_LOCAL_DAEMON=1` | Macs only, local host. Honored only when `CODEX_CLI_PATH` is unset and `CODEX_APP_SERVER_FORCE_CLI≠1`. The app runs `<bundled codex> app-server daemon version` with a 2.5 s timeout and requires the server version ≥ **0.141.0**. It then talks JSON-RPC over a websocket on the unix socket; otherwise it falls back to stdio. | ~10776064; `ny`/`Wv=0.141.0` ~10091013-10092118 |
  | `CODEX_APP_SERVER_FORCE_CLI=1` | Forces a stdio CLI server. Disables the daemon and websocket paths. | ~10768495, ~7223109 |
  | `CODEX_APP_SERVER_WS_URL` | Overrides a host's websocket URL | ~10768558 |
  | `CODEX_APP_SERVER_CHATGPT_BASE_URL`, `CODEX_APP_SERVER_OPENAI_BASE_URL` | Mapped to `-c chatgpt_base_url` / `openai_base_url` | ~10769223 |
  | `SPARKLE_UPDATE_INTERVAL_MINUTES` | Sparkle check interval. Default 9e5 ms (15 min); ≤0 means 0. | ~4775430 |
  | `CODEX_ELECTRON_PRIMARY_RUNTIME_UPDATE_MODE=manual` | Only effective when `BUILD_FLAVOR=dev`, and governs the "primary runtime", not codex | ~8805721 |
  | `CODEX_ELECTRON_START_IN_BACKGROUND=1` | Start without focusing the window | ~9602584 |
- **Environment import:**
  - The app runs `$SHELL -il` with `CODEX_SHELL=1` and does `Object.assign(process.env, userEnv)` (~7206106, ~10225216).
  - Confirmed live without printing any values: the spawned codex (pid 51467) has `CODEX_SHELL` count=1 and `MISE_SHELL` count=2. The parent process's launch env (pid 51316) has `CODEX_SHELL` count=0.
- **Admin control of updates:** `[features] in_app_updates = false` in a **managed `requirements.toml`**, not `config.toml`. This only disables the app's built-in updater; it offers no version pinning (live doc `docs/enterprise/manage-app-updates.md`).

### I. CLI update check (TUI)
- `check_for_update_on_startup`: boolean, default true. Unset in `~/.codex/config.toml`; doctor shows `startup update check true`.
- The check runs in the TUI only when the cache is more than 20 h old. It queries `api.github.com/repos/openai/codex/releases/latest` (`codex-rs/tui/src/updates.rs:27-38, 62`).
- The cache lives in `~/.codex/version.json` and is shared by all copies: `latest_version 0.154.0`, `last_checked_at 2026-09-10T00:17Z`, `dismissed_version 0.152.1`.
- **The update action depends on how codex was installed:**
  - npm (which includes mise, because the wrapper sets `CODEX_MANAGED_BY_NPM`, `codex.js:225-233`; `install-context/src/lib.rs:124-133`): `npm install -g @openai/codex`. This **bypasses the mise pin**.
  - Standalone: `curl … install.sh | CODEX_NON_INTERACTIVE=1 sh`.
  - Desktop bundle: install method "Other", so no update action.
  - Evidence: `codex-rs/tui/src/update_action.rs:21-56`; `codex-rs/cli/src/main.rs:968-983`.
- `tui.show_server_version_notice` (default true) shows a notice when the connected daemon is an older release (schema; `tui/src/history_cell/tests.rs:67-87`).

## 2. Current host values
| Copy | Path | Version | Install method per `codex doctor` | Update action per doctor |
|---|---|---|---|---|
| mise (first on PATH) | `~/.local/share/mise/installs/npm-openai-codex/0.154.0/bin/codex` (a node wrapper) | 0.154.0 | npm | `npm install -g @openai/codex` |
| standalone | `~/.local/bin/codex` → `~/.codex/packages/standalone/releases/0.151.0-aarch64-apple-darwin` | 0.151.0 | standalone | standalone installer |
| Desktop bundle | `/Applications/ChatGPT.app/Contents/Resources/codex` | 0.155.0-alpha.9.2 | other | "manual or unknown"; doctor claims "current version is not older" than 0.155.1 |

- **Standalone package directory:** contains `current`, `install.lock` and `releases/` only. No `auto-update-version`.
- **LaunchAgents:** none for codex. `~/Library/LaunchAgents` has 14 plists: `com.openai.atlas.*` ×2 and `com.opensymphony.codex-otel`. `launchctl` lists only the running app as `application.com.openai.codex…`.
- **What the Desktop runs now:**
  - Its bundled codex as a stdio app-server (pid 51467: `-c features.code_mode_host=true app-server --analytics-default-enabled`).
  - A second bundled `app-server --listen stdio://` whose parent is `cua_node/bin/node_repl`.
  - Its bundled `codex-code-mode-host`.
  - `CODEX_CLI_PATH`, `CODEX_APP_SERVER_USE_LOCAL_DAEMON` and `CODEX_HOME` are all absent from its env (count=0).
- **Doctor summary** (all three copies): `app-server background server socket is stale or unreachable`; `21 ok | 5 notes | 2 warn | 0 fail`. The 0.154 and 0.151 copies both report "0.155.1 available".
- **Repo pin:**
  - `.config/mise/conf.d/shared.toml:44` has `"npm:@openai/codex" = { version = "0.154.0" … }`, and `.config/mise/mise.lock:531-536` matches.
  - The 0.155.1 bump exists only inside Renovate's grouped PR **#1063** ("update image-build inputs", Dependency Dashboard #193:40, :231). It has no PR of its own.
  - The repo `.codex/config.toml` sets only `shell_environment_policy`.
- **User `~/.codex/config.toml`** (key names and non-secret values):
  - `[features]` sets `hooks=true`, `js_repl=false`, `memories=true`, `chronicle=true`.
  - No `multi_agent_v2`, no `check_for_update_on_startup`.
  - `approval_policy="never"`, `sandbox_mode="danger-full-access"`.
- **Stale repo doc:** `.claude/skills/codex-schema/SKILL.md` says "every doc in `schemas/v2/` is a JSON file", but `schemas/v2/` doesn't exist (`ls` → 0 entries).

## 3. Recommended configuration (nothing applied; every item is a proposal)

**Repo-reviewed (dotfiles; ship via PR)**
1. **Bump the mise copy (Phase 9.1).**
   - Run `mise run lock-shared -- "npm:@openai/codex"` for 0.154.0 → 0.155.1, then `mise run codex-schema-generate`.
   - Also consider a `renovate.json` packageRule that pulls `npm:@openai/codex` out of the image-build-inputs group so it gets its own PR. Otherwise every codex release waits on #1063.
   - A floating `latest` pin is ruled out by repo policy, not by any technical limit.
2. **Phase 9.1b gate as a mise task plus a python module.** It would check:
   - `daemon version` JSON ≥ the pin;
   - `packages/standalone/auto-update-version` exists and equals the `current` release;
   - `app-server-updater.pid` is live.

   It also needs a failing arm: a stale socket gives `Connection refused` today, which is a ready-made failing case.
3. **Setting `features.multi_agent_v2`:** use a config file (`.codex/config.toml` for the repo or `~/.codex/config.toml` globally), never `-c`. `-c` silently drops daemon reuse. Whether the project layer is honored for `features` is **UNVERIFIED**.
4. **Don't set `CODEX_HOME`.** All four copies should share `~/.codex`, and the socket path depends on it.

**User-global (your actions on this Mac; the repo doesn't manage these)**
1. **Refresh the standalone once on the latest channel.** Run `curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh`, or equivalently `~/.local/bin/codex update`.
   - This writes the `auto-update-version` marker.
   - Keep `CODEX_NON_INTERACTIVE=1` so the npm-uninstall prompt answers No.
   - **Never set `CODEX_RELEASE`**: it deletes the marker and turns auto-update off.
   - **UNVERIFIED:** that the script served at chatgpt.com matches the `rust-v0.155.1` tag.
2. **Start the managed daemon from the new binary:** `~/.codex/packages/standalone/current/bin/codex app-server daemon bootstrap` (or `start`). Add `--remote-control` only if you want it.
3. **Optional `~/.codex/app-server-daemon/settings.json`:** `{"shutdownGraceSeconds":300,"updater":{"autoUpdateEnabled":true,"updateIntervalMinutes":60}}`. Auto-update and 60 minutes are already the defaults, so the file is only worth writing to raise the grace period as a #40969 mitigation.
4. **Reboot persistence:** codex installs no LaunchAgent, and the updater does not survive a reboot. The options are a user LaunchAgent that runs `…/current/bin/codex app-server daemon start` at login, or the 9.1b mise task. Either is custom code, so its justification needs to be written down.
5. **Point the Desktop at the auto-updated copy** by exporting one of these in `~/.zshenv` or `~/.zshrc`, then fully quitting and reopening the app:
   - **(a)** `CODEX_APP_SERVER_USE_LOCAL_DAEMON=1`: one shared daemon on the standalone binary. Recommended if the daemon is running.
   - **(b)** `CODEX_CLI_PATH=$HOME/.codex/packages/standalone/current/bin/codex`: a private stdio server on the standalone binary.
   - Both are undocumented internals and could change without notice.
   - The Desktop's feature gates currently top out at `0.155.0-alpha.6`, so stable 0.155.1 meets them. A future Desktop build could require a newer server than stable.
   - Sibling `codex-code-mode-host` binaries exist in the standalone `bin/`.
6. **Leave Desktop auto-update on** (`SUAutomaticallyUpdate=1`). Don't set `in_app_updates=false`.

**Not possible**
- Putting stable 0.155.1 inside the Desktop bundle: the bundle is signed and Sparkle replaces it with alpha builds.
- Making the daemon run the mise-installed codex (#41188 is open).
- Setting hook-trust bypass as a config key.
- Having the mise pin follow latest automatically without Renovate.
- Keeping the updater loop alive across a reboot without an external launcher.

## Unverified / open
- Which codex version Desktop 26.917.51856 bundles.
- Whether pointing the Desktop at stable 0.155.1 regresses any alpha-only Desktop features.
- Whether a repo `.codex/config.toml` `[features]` block applies to threads served by the shared daemon.
- Whether `daemon start` cleans up the stale pid and socket by itself (not exercised; no daemon was started).
- The Desktop's handling of `CODEX_CLI_PATH` beyond the static reading of `app.asar`.

## Control arms run
- **Binary versions:** each copy's version was probed directly. `pid-update-loop --help` returned exit code 0 on all three, a bogus verb returned 2, and `update --help` returned 2 on 0.151/0.154 and 0 on the Desktop's alpha.
- **Socket listener:** 0 `lsof` matches for the control socket against 134 visible `.sock` paths.
- **CODEX_ string sweep of the source:** the first run returned 0 because zsh globbed `--include=*.rs`, and the control arm (`CODEX_HOME` count 0) exposed it. The re-run found 190 names, including `CODEX_HOME`.
- **Launch-env counts:** `PATH` count=1 served as the positive arm for the counts of 0.
- **Docs:** the `CODEX_CLI_PATH` doc search returned 0 hits, with `CODEX_HOME` returning 4 on the same page.
- **Installer history:** the `auto-update-version` history search returned 0 hits, with `CODEX_INSTALL_DIR` returning 1 at the same tag.
- **Graph:** `mise run graphify-health` returned exit code 3 (`stale`), so I used source grep instead.

## GitHub repos touched
- [openai/codex](https://github.com/openai/codex): releases, `app-server-daemon` src and README, `scripts/install/install.sh`, tui/cli/core/features/install-context source at `rust-v0.155.1`, and issues #41188 and #40969.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): mise pins, the Renovate dashboard (#193) and PR #1063, `task_plan.md` 9.1b, and `schemas/codex-config.json`.
