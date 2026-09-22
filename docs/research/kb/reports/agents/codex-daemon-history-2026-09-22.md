# Codex CLI pin vs. app-server daemon auto-update: history, primary sources and how to get both to latest

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. HTML entities introduced in transit restored.

This lane was read-only and changed no repo files. The report was written as it went to `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/b72c95e0-c9b0-4405-9c38-6bd9885f2f71/scratchpad/report-codex-daemon-history.md`. That file holds the raw log, and its fetched sources are under `scratchpad/src/`. This message is the full report.

## TL;DR

- **Ray has made two rulings that conflict, and nobody has named the conflict to him yet.**
  - **2026-09-16 (user-global mise track):** "Match the mise pin exactly" and "Wait for a safe checkpoint".
  - **2026-09-21 (dotfiles):** "yes to auto-update".
  - Codex's own daemon auto-updater cannot satisfy both. It only follows the `latest` channel, and it has no way to target a specific version.
- **On stable 0.155.x the daemon never runs the mise binary.** It always launches `$CODEX_HOME/packages/standalone/current/codex`, which on this Mac is **0.151.0**. The daemon updater and `daemon update` only work when the official installer's latest-channel marker exists, and it does not exist here.
- **Nobody has ever run `codex app-server daemon update` for real, or written the schedule config.** Every recorded invocation was `--help`. Two lanes explicitly listed it as forbidden.
- **There is a way to make both equal, but only in prereleases.** From 0.156.0-alpha, `codex app-server daemon update --from-cli -y` copies the invoking CLI package (the mise npm package) into the daemon slot and pins it there. Scheduled updates respect that pin. I found this by reading the source; it has never been run, and it is not in any stable release. The latest stable is 0.155.1.

---

## 1. Prior session discussions (AgentsView)

### Searches

- **Semantic search is down.** `--hybrid` returned *"semantic search not available … index is building: 9% complete"*, so everything below used full-text search or plain substring search in tool calls.
- **Child sessions are hidden by default.** The C0 thread did not appear under `--project mise`. Adding `--include-children --include-automated --include-one-shot` returned it, so the filter was hiding it and the thread itself is real. Every C0 result below used those flags.
- **The knowledge-base's `mise run kb-session-search` failed (rc=1).** It reported *"agentsview sync FAILED — refusing to search a stale or absent index … server exited before becoming ready"*. That second route was not available, so all history evidence comes from the remote AgentsView server.
- **I excluded this lane's own session (`agent-ad3b08ac…`) from the results.** It kept echoing its own probes.

### A. Origin of the dotfiles ruling: `dd442cf4-4469-4773-9f50-6f6c2584afae`

This is a dotfiles Claude session from 2026-09-21. `codex:01a0c74d…` is an import of the same session: identical text, all timestamps 2026-09-22T04:09:28.

- **Ray's artifact comment, 21:02** (thread 2447140d on artifact RwUfffidCMAYdPJ49jYgQc, read via ArtifactComments @448, range #440-460):
  > "muse also ensure the codex daemon is correct and at the correct version / see 0.155.0 of codex release notes … Added configurable daemon update schedules and codex app-server daemon update; saved threads and active goals can recover after daemon restarts."
- **Claude's reply, 21:02:**
  > "Should the daemon auto-update on a schedule, or stay pinned to whatever mise locks? Auto-update could move the daemon ahead of the pinned CLI, so I'd default to pinned unless you rule otherwise."
- **Ray, 21:10** (recorded in the @476 tool result): **"yes to auto-update"**
- **Measured on pinned 0.154.0 (@450, 21:03:07):**
  - `codex app-server daemon --help` listed bootstrap, start, restart, enable-remote-control, disable-remote-control, stop and version. There was **no `update`**.
  - `daemon version` (@452, 21:03:14) returned *"failed to connect to …/app-server-control.sock … Connection refused (os error 61)"*.
  - The only app-server processes were `/Applications/ChatGPT.app/Contents/Resources/codex`.
- **Plan item 9.1b rewritten (@478, 21:11:31, range #473-519):**
  > "RULED (Ray, artifact 21:10): daemon AUTO-UPDATE = YES … daemon AT OR AHEAD of the mise pin and never stale … (b) find and record the update-schedule config keys on 0.155.x (`codex doctor` shows them per #43948) and verify #43521's claim that release pins survive a daemon update"
- **Drift handling (@494 and @500, later recorded as ruled in `task_plan.md` 9.1b):** notify and open a pin bump when the daemon is ahead. Block only when it is behind or stale, when threads or goals don't survive a restart, or when the flag contract changes.
- **Plugin research pass (@513/@519, 21:17):**
  > "#41188 (OPEN) says externally-managed installs are UNSUPPORTED — a mise-installed codex is not a standalone install, so #43521's pin preservation does not apply to us and MISE is what protects our pin. Ray's auto-update ruling may therefore be unimplementable as-is for a mise install: VERIFY on 0.155.1"
- **Measured in this session:** help output and `daemon version` only. There was no `daemon update` and no schedule config.

### B. Origin of the user-global exact-pin ruling: `codex:01a09c55-c7c2-75c0-9e94-414372f69f96`

AgentsView files this thread under project "graphify", but it is the user-global `update-all` track.

- **@6807, user, 2026-09-16T19:12:29:** "the native installer is needed though to run command 'codex agents'"
- **@6842, user, 19:23:33.** The Q1 question was *"Should the native Codex installation always match the exact version in your global `npm:@openai/codex` mise entry, or independently follow the newest stable release?"* Ray answered **"Match the mise pin exactly (Recommended)"**.
- **@6845, user, 19:23:57.** The Q2 question was about waiting before a daemon update or restart. Ray answered **"Wait for a safe checkpoint (Recommended)"**.
- **@7544, user `/goal`, 2026-09-17T01:20:**
  > "Use the exact global npm:@openai/codex mise pin as authority … Use the official exact-version installer. Verify npm CLI, native executable and daemon independently. Active or uncertain sessions produce durable PENDING, not success."
  >
  > Its acceptance criteria include "npm/native/daemon versions matching the global pin."
- **@9312, user, 2026-09-18T20:37:13 (range #9313-9695):**
  > "note the newest codex cli version is now **0.155.1** / try to automate the update to the latest version using zero to minimal agent/llm tokens"
- **@9317, 20:38:12, measured on the mise npm 0.155.0 binary:** `codex app-server daemon update --help` printed **"Update the standalone installation and restart the managed daemon (may interrupt work)"**. Its only options were `-c`, `--enable` and `--disable`.
- **@9319:**
  > "Codex already has a background updater, but it follows its own 'latest' channel and does not synchronize mise or repository pins."
- **@9613, 22:16:21:**
  > "The updater treats the npm CLI, native executable and running daemon as separate versions. A newer CLI does not upgrade an already-running daemon."
- **@9670:** defined three tasks:
  - `update:codex` checks for a newer stable release.
  - `update:codex:reconcile` "follows the exact global pin".
  - `update:codex:maintenance` "permits the reviewed daemon transition during an explicit maintenance checkpoint".
- **@9866, 2026-09-19T00:13 (range #9842-9867):** the work was stopped with these versions:

  | Surface | Version |
  |---|---|
  | mise npm CLI | 0.155.1 |
  | Native executable | 0.151.0 |
  | Native daemon | 0.151.0 |
  | ChatGPT Desktop bundled runtime | 0.155.0-alpha.9.2 |

- **@11804, user, 2026-09-21T18:14:27:** "review … #release-rust-v0.155.0 — as that changes to daemon that should be related to getting the codex runtime versions up to date"
- **@11815, 18:17:17 (range #11805-11817):**
  > "`codex app-server daemon update` follows the native **latest** channel, while your approved workflow requires the native runtime to match the **exact mise pin**. It also explicitly warns that it may interrupt work."
- **@11816–11817, measured on npm 0.155.1:**
  - `daemon update --help` returned rc=0.
  - `daemon version` returned rc=1 with "Connection refused".
  - The stale PID record `~/.codex/app-server-daemon/app-server.pid` pointed at pid 61145, which was not alive, with `executable_identity` null.
  - The ChatGPT.app codex reported `0.155.0-alpha.9.2`.
- **@11818, user:** Ray redirected the work to thread `01a0b72e…`, saying it "already did this research".

### C. The C0 thread: `codex:01a0b72e-85a0-7b03-b6a7-ce1bb930f636`

This is "C0 — Codex pin authority and runtime…", in project `~/.config/mise`, 2026-09-19 to 2026-09-22.

- **@281, 2026-09-21T18:03:30:**
  > "mise is already pinned and active at stable `0.155.1`; the shell still resolves `~/.local/bin/codex`, backed by the old standalone `0.151.0` … v0.155.0 does not automatically 'make all Codex versions current.' It adds a new independently updatable app-server lane."
- **@291, 18:08:54:**
  > "`daemon update` installs the latest stable daemon release independently of the CLI version that invoked it … Stable `0.155.1` does not yet expose the newer `--from-cli` behavior."

  Its recommendation:
  > "Do not quietly add `codex app-server daemon update` to `update-all`. It follows 'latest stable,' may restart live work, and can drift from the exact mise pin … If the daemon is adopted, initially use stable `0.155.1` with automatic updates disabled or an exact pin."
- **@737, 21:30:19:**
  > "the updater applies to an **installer-owned, latest-channel standalone installation**—not automatically to the npm CLI pinned by mise or to Codex Desktop. An explicit release pin is preserved."

  Its identity-capture proposal passed review as "code preparation only". No live capture was taken and no update was run.

### D. Capability review: `codex:01a0b5f3-0008-7ee3-a1b3-2d85620f9323` @217 (2026-09-18T20:40:14)

The review's decision was `'PARTIAL_REUSE_ONLY'`:
> "They cannot apply an immutable prequalified version: the updater invokes the installer with CODEX_RELEASE=latest and exposes no expected-version argument."

Its stated implication:
> "The current explicit-release standalone selection is not eligible for daemon update until an official latest-channel install creates the marker."

### Was `daemon update` or the schedule config ever measured on a mise or npm install?

**No.** I ran a regex search for `daemon.{1,6}update` over tool inputs for the last 20 days, including child sessions, and got 99 hits.

- **Control:** the same search found the known `--help` runs (01a09c55 @9317 and @11816, C0 @286, `01a0b5f2` @216), so it does find real invocations.
- **Result:** there were zero non-help invocations. C0 @1455 and `01a0b5f2` @176 list it as forbidden.
- **Schedule config:** nobody ever wrote `settings.json`. I found no live `codex doctor` output showing the updater rows (#43948); the only hits were reads of the doctor source code.

---

## 2. Primary sources (gh api, 2026-09-22)

Controls for the fetches below: a bogus tag (`rust-v0.999.0`) returned rc=1 and a missing README path returned rc=1, while the real ones returned rc=0.

### Releases

- **0.155.0**, published 2026-09-17T23:14:43Z:
  > "Added configurable daemon update schedules and `codex app-server daemon update`; saved threads and active goals can recover after daemon restarts. (#43542, #43562, #44314)"
- **0.155.1**, published 2026-09-18T20:03:04Z, contains only #46467, a TUI reasoning-summary fix. **It changes nothing about the daemon.**
- `releases/latest` is `rust-v0.155.1`. Anything newer is a prerelease: `0.156.0-alpha.*` and `0.157.0-alpha.*`.

### Issues and PRs

| # | State | What it says (verbatim where quoted) |
|---|---|---|
| #41188 | **OPEN** | The daemon resolves its executable only as `$CODEX_HOME/packages/standalone/current/codex`, so npm, Homebrew and Nix installs fail with "managed standalone Codex install not found". A 2026-09-07 comment reproduces this with **mise-managed codex 0.153.2**: *"the daemon starts and updates app-server from that fixed path."* |
| #40969 | **OPEN** | "auto-update force-kills active turns after a 60s drain budget, and cannot be disabled" (reported on 0.150; #43542 later added the disable switch). |
| #24034 | **OPEN** | "codex remote-control starts stale standalone app-server 0.132.0 while active CLI is npm-managed 0.133.0". This is the same situation as ours today. |
| #43521 | merged 09-07 | "Record `latest` selections in `auto-update-version` … clear the marker for explicit releases. Start the daemon updater only for a marked stable release … Existing installs without a marker require a new `latest` installation to enable automatic updates." |
| #43529 | merged | The updater runs after a managed start or restart, and is stopped when the latest-channel marker is removed. |
| #43542 | merged | "Read `updater.autoUpdateEnabled` and `updater.updateIntervalMinutes` from `CODEX_HOME/app-server-daemon/settings.json`, defaulting to enabled with a 60-minute interval. Keep the initial five-minute delay." |
| #43562 | merged | "check the latest stable release once, even when automatic updates are disabled. The command requires an installer-owned latest-channel standalone installation … `updated`, `noUpdate`, or `unsupported` … may interrupt active or queued work." |
| #43948 | merged | `doctor` reports the configured auto-update setting and interval from `settings.json`. |
| #43552 / #44314 | merged | The launched executable's BLAKE3 identity is stored in the PID file; saved threads are restored when the managed daemon restarts. |
| #45558 / #45780 | merged 09-15, **prerelease only** | Missing daemon installs can be seeded from a complete local CLI package, and `daemon update` can return pinned packages to latest stable. The second PR adds: "Scheduled updates and ordinary updater socket requests continue to respect pins." |

### Source code at `rust-v0.155.1`

- **How the daemon finds its binary:** `managed_install.rs:22-28` sets `managed_codex_bin` to `codex_home/packages/standalone/current/{bin/,}codex`. There is no override.
- **What the updater runs:** `update_loop.rs:454-457` calls `.env("CODEX_RELEASE","latest")`, `.env("CODEX_INSTALL_IF_LATEST","1")` and `.env("CODEX_UPDATE_FROM_RELEASE", …)`. It is latest-only.
- **Why `daemon update` refuses:** `manual_update.rs:127` has this message:
  > "This command requires a CLI-managed daemon and a stable latest-channel standalone install; update this installation with its owning installer."
- **Schedule settings:** `settings.rs` defaults the interval to 60, the shutdown grace to 60 and the maximum grace to 300. The keys are camelCase. The README example is:
  ```json
  {"remoteControlEnabled": false,
   "shutdownGraceSeconds": 60,
   "updater": {"autoUpdateEnabled": false, "updateIntervalMinutes": 120}}
  ```
  The README also says: *"The updater uses saved network settings; CLI `-c` overrides do not reach it."*
- **README table:** "Installer selected an explicit release; `bootstrap` is used | Managed binary only | **No; the selected release stays pinned.**"
- **Installer (`scripts/install/install.sh`):**
  - `RELEASE="${CODEX_RELEASE:-latest}"`, with usage `install.sh [--release VERSION]`.
  - After installing, it runs `if [ "$RELEASE" = "latest" ]; then …> "$AUTO_UPDATE_VERSION"; else rm -f "$AUTO_UPDATE_VERSION"; fi`.
  - So installing an exact version pins the daemon and turns its auto-update off. The installer also rewrites the visible `~/.local/bin/codex` command (`update_visible_command`).

### Source code at `rust-v0.156.0-alpha.17` (prerelease)

- **`cli/src/main.rs` adds a `--from-cli` flag to `daemon update`:**
  ```rust
  Update { /// Copy and pin this CLI package.
      #[arg(long)] from_cli: bool,
      #[arg(short = 'y', long, requires = "from_cli")] yes: bool }
  ```
  **Control:** the same grep finds 0 `from_cli` hits in `rust-v0.155.1` `main.rs`.
- **`prepare_install.rs`, `update_from_cli`:** "Select this CLI's complete package and pin it, restarting only a running daemon." On success it returns "The CLI package is selected and pinned. Run `codex app-server daemon update` to return to production updates."
  - The CLI package must provide `codex-package.json`, `bin/codex`, `bin/codex-code-mode-host` and `codex-path/rg`, all executable.
  - Package detection (`install-context` `CodexPackageLayout::from_exe`) looks for an executable inside a `bin` directory whose parent contains `codex-package.json`.
- **Local read-only check against the mise npm 0.155.1 install:** `…/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/` contains `codex-package.json` (`layoutVersion 1`, `version 0.155.1`, `target aarch64-apple-darwin`, `entrypoint bin/codex`), `bin/codex`, `bin/codex-code-mode-host` and an executable `codex-path/rg`.
  - That matches the validator's file list for macOS.
  - This is **inferred, not executed**. I did not look at the 0.156 npm package layout.

### Local state today (read-only)

| Item | Finding |
|---|---|
| `~/.codex/packages/standalone/current` | points at `releases/0.151.0-aarch64-apple-darwin` (2026-08-29) |
| Latest-channel marker `auto-update-version` | **absent** (control: `install.lock` is present, so the listing works) |
| `~/.codex/app-server-daemon/settings.json` | absent |
| `~/.codex/packages/app-server-daemon` | absent |
| dotfiles repo pin (`.config/mise/conf.d/shared.toml:44`) | `npm:@openai/codex` **0.154.0**; `mise exec -- codex app-server daemon update --help` says "unrecognized subcommand 'update'" |
| user-global pin (`~/.config/mise/config.toml:144`) | **0.155.1**, `minimum_release_age = "0s"` |

---

## 3. How can both the CLI pin and the daemon be at latest?

**The constraint behind every option:** on 0.155.x the daemon's version is whatever is installed in the standalone slot. It is never the mise binary, and today that slot holds 0.151.0. So "daemon at latest" means one of three things:

- a latest-channel standalone install,
- an exact-version standalone install kept equal to the pin, or
- (0.156 and later) a copy of the mise package.

| # | Mechanism | Daemon version | CLI version | Fits dotfiles "auto-update = yes, daemon ≥ pin" (9.1b) | Fits user-global "exact pin + safe checkpoint" (Q1/Q2) | Evidence |
|---|---|---|---|---|---|---|
| **A** | Run the official `install.sh` **without** `--release`, then `daemon start` or `bootstrap`. The native updater runs every `updater.updateIntervalMinutes` (default 60). The mise pin follows via Renovate or `update:codex`. | latest stable, within about an hour | the pin, which lags until it is bumped | **Yes** | **No.** The daemon can move ahead of the pin, and restarts happen whenever the updater decides. The wait is capped at `shutdownGraceSeconds ≤ 300`; #40969 is still open. | #43521, #43542, the README table, `update_loop.rs:454` |
| **B** | Run the official `install.sh --release <pin>` (which clears the marker, so no auto-update), then `codex app-server daemon restart` at a safe checkpoint, driven by `update:codex:reconcile`. "Latest" comes from bumping the pin automatically. | exactly the pin | the pin | Partly. Equality satisfies "≥ pin", but it is **not** daemon auto-update. | **Yes.** This is literally the 09-17 `/goal`. | install.sh marker logic; README "explicit release … stays pinned" |
| **C** | On 0.156 or later, after each pin bump, run `mise exec -- codex app-server daemon update --from-cli -y` at a safe checkpoint. The daemon package becomes a copy of the mise package, pinned; scheduled updates respect the pin. | exactly the pin | the pin | Same as B | **Yes, with no second installer.** This is what #41188 asks for. | #45558, #45780, `main.rs` / `prepare_install.rs` @0.156.0-alpha.17. **Unverified:** prerelease only and never executed. |
| D | `codex app-server daemon update` (manual) on 0.155.1 | — | — | — | — | Returns `unsupported` for our install: there is no marker, and the command is latest-only with no version argument. |

### Answer

- **Keeping the two equal:** there is exactly one version authority, the mise pin. Automation moves the pin to latest, and the daemon follows the pin. Use B on stable today and C once `--from-cli` reaches a stable release.
- **"Auto-update" then means** the pin auto-updates and the daemon auto-follows it. It does not mean the daemon's own updater.
- **The only way to keep the daemon's own updater (A)** is to accept a gap in which the daemon runs ahead of the pin. It also needs a second, latest-channel standalone installation. #41188 and the Omarchy comment describe running two installers for one tool as the thing to avoid.

### What needs Ray (the two rulings conflict)

The 2026-09-21 "yes to auto-update" was given in reply to a question that asked "auto-update vs pinned to mise". It did not mention the 2026-09-16 exact-match ruling, and the two cannot both be literally true.

Recommended framing: "auto-update = the mise pin is auto-bumped to latest, and the daemon is auto-reconciled to it at a safe checkpoint (B, then C)." That keeps both of Ray's stated goals, "latest" and "equal", and drops only the daemon's self-updater.

Two follow-ons, depending on his answer:
- **If he accepts that framing:** 9.1b's gate becomes daemon == pin, and "daemon ahead of pin" cannot happen.
- **If he wants A:** 9.1b's "BLOCK when behind" will also fire briefly. After a Renovate bump, the daemon lags until its next hourly check (first check after 5 minutes).

### Other things he needs to decide or know

- **Which pin is the authority?** There is one daemon per `CODEX_HOME` (one per user). The dotfiles repo pins 0.154.0 and the user-global config pins 0.155.1, so the daemon can match only one of them.
- **Correction to `task_plan.md` 9.1b.** "#41188 … MISE is what protects our pin" is only half right. On 0.155.x a mise install cannot *be* the daemon at all. A daemon started from mise 0.155.1 would launch the stale 0.151.0 standalone binary (the #24034 bug). So auto-update is not impossible, but it requires adding a latest-channel standalone installation.
- **The installer also takes over the shell command.** `install.sh` rewrites `~/.local/bin/codex`, which is already shadowing mise outside mise-activated directories. B and A both touch it; C does not.

---

## 4. Gaps and follow-ups (unverified)

1. `--from-cli` has never been run. It needs a stable release that includes #45558/#45780, then one run with a positive and a negative arm, and a look at the npm 0.156 package layout.
2. No live `codex doctor` updater rows have been observed, and no `settings.json` has been written or measured.
3. Nobody has checked that threads and goals are restored after a managed restart (#44314) on this Mac.
4. The ChatGPT Desktop runtime is a separate, fourth version surface. The `CODEX_CLI_PATH` override was never proven (01a09c55 @9867).
5. AgentsView semantic search was down (index 9% built) and `kb-session-search` failed, so there was no second search route. Some decision prose may have been missed by full-text search.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — releases rust-v0.155.0/0.155.1 and the release list; issues/PRs #41188, #40969, #24034, #43521, #43529, #43542, #43552, #43562, #43948, #44314, #45558, #45780 plus the #41188/#40969 comments; the daemon README at 0.155.1, 0.156.0-alpha.17, 0.157.0-alpha.8 and main; `managed_install.rs`, `settings.rs`, `manual_update.rs`, `update_loop.rs`, `scripts/install/install.sh` at 0.155.1; `prepare_install.rs`, `cli/src/main.rs`, `install-context/src/lib.rs` at 0.156.0-alpha.17
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `task_plan.md` 9.1b, `mise.toml`, `.config/mise/conf.d/shared.toml` (read-only, local clone)
