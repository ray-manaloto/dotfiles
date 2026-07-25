# Angle 1 — launchd LaunchAgents vs cron on macOS (native venues for the Mac-side sync/verify job)

Run: research-20260709-r2-mac-automation · Agent: launchd-cron · Date researched: 2026-07-09
Grounding: `docs/research/runs/research-20260709-r2-inventory/report.md` (nightly `ci.yml` publish 02:00 America/Chicago; job = `mise run sync` (~38GB buildkit pull, possibly hours) + `mise run verify-local` (R1/R2/R3 + persistence); Docker Desktop context `desktop-linux` mandatory; user env needs mise, uv, SSH agent via launchd, Doppler CLI).

## Findings

### F1. Scheduling semantics: StartCalendarInterval survives sleep (coalesced catch-up run on wake); cron does not

- Apple's official launchd documentation ("Scheduling Timed Jobs", BPSystemStartup): *"If you schedule a launchd job by setting the StartCalendarInterval key and the computer is asleep when the job should have run, your job will run when the computer wakes up. However, if the machine is off when the job should have run, the job does not execute until the next designated time occurs."* And for cron: *"If the system is turned off or asleep, cron jobs do not execute; they will not run until the next designated time occurs."*
  Source: <https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html>
- launchd.info (the standard community reference mirroring the `launchd.plist(5)` man page) confirms the coalescing wording for `StartInterval`: *"If the system is asleep, the job will be started the next time the computer wakes up. If multiple intervals transpire before the computer is woken, those events will be coalesced into one event upon wake from sleep."* `StartCalendarInterval` follows the same coalesce-to-one-run-on-wake pattern. Source: <https://www.launchd.info/>
- Implication for this job: a Mac that is asleep at the nightly 02:00 CT publish + a morning-scheduled LaunchAgent gives exactly one catch-up `sync+verify` on lid-open — no missed-night backlog, no duplicate storms. Plain cron silently skips the night entirely.

### F2. cron is officially deprecated on macOS and has extra TCC friction; launchd is the documented replacement

- Apple, same page: *"The preferred way to add a timed job is to use launchd"* and *"Note: Although it is still supported, cron is not a recommended solution. It has been deprecated in favor of launchd."* Source: <https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html>
- cron jobs touching TCC-protected paths (~/Documents, ~/Library, external volumes) fail with silent "Operation not permitted" unless `/usr/sbin/cron` itself is granted Full Disk Access — a broad grant to a system binary. Documented across: <https://osxdaily.com/2020/04/27/fix-cron-permissions-macos-full-disk-access/>, <https://nono.ma/operation-not-permitted-macos-sonoma>, <https://www.runxbuild.com/blog/mac-crontab/> (2025-era summary: "Full Disk Access breaks cron in non-obvious ways... use launchd when the job is critical, has to survive sleep/wake, needs to run in the user's GUI session").
- Mitigating note for THIS job: the sync/verify workload touches `~/dotfiles`, `~/.local/state`, Docker's socket, and mise/uv caches — none of which are TCC-protected locations — so TCC friction is low for either venue. It becomes relevant only if the job ever reads ~/Documents/Desktop/Downloads or sends AppleEvents (see F6).

### F3. GUI-session environment: a gui/<uid> LaunchAgent inherits SSH_AUTH_SOCK; PATH does NOT include mise — set it explicitly

- macOS's stock ssh-agent is itself a launchd LaunchAgent (`com.openssh.ssh-agent`) exposing an on-demand launchd socket; `launchctl print gui/$(id -u)` shows `SSH_AUTH_SOCK => /private/tmp/com.apple.launchd.XXXX/Listeners` in the **inherited environment** of the gui domain — so any LaunchAgent bootstrapped into `gui/<uid>` inherits a working `SSH_AUTH_SOCK` without any wiring. Source (2023-10, with launchctl print transcripts): <https://www.smop.co.uk/blog/2023/10/05/how-to-really-configure-mac-ssh-agent/>
- The same inherited/default-environment split shows the **default PATH for launchd jobs is `/usr/bin:/bin:/usr/sbin:/sbin`** — no Homebrew, no `~/.local/bin`, no mise shims. The job script must either export PATH explicitly, invoke tools by absolute path, or use mise's non-interactive story. Sources: <https://www.smop.co.uk/blog/2023/10/05/how-to-really-configure-mac-ssh-agent/>, <https://thekodelab.com/en/posts/macos-gui-terminal-vs-ssh-session/>
- mise's own docs (local cache) prescribe **shims for non-interactive environments**: "Use `--shims` instead for non-interactive setups like CI/CD or IDEs"; comparison table "Works in non-interactive shells: PATH activation ❌ / shims ✅". Cache: `docs/research/mintlify-cache/jdx/mise/llms-full.txt:16,2478-2543`. Practical recipe for the wrapper script: `export PATH="$HOME/.local/share/mise/shims:$PATH"` (or call `~/.local/bin/mise run sync` by absolute path — `mise run` resolves its own toolchain).
- Domain matters: `gui/<uid>` vs `user/<uid>` are different launchd domains with different service sets, keychain-unlock state, and TCC inheritance; agents intended to see the Aqua session (keychain unlocked, SSH_AUTH_SOCK, GUI apps like Docker Desktop) should live in `gui/<uid>` — which is where `~/Library/LaunchAgents` plists load at login, and where `brew services` installs by default. Source: <https://thekodelab.com/en/posts/macos-gui-terminal-vs-ssh-session/>
- Keychain: agents in the gui domain run after login with the user's login keychain unlocked (same source). Doppler CLI auth and git credential helpers therefore behave as in an interactive terminal. Caveat: LaunchAgents run **only while the user is logged in** — logged-out Mac = no runs (launchd.info: agents load at user login; "only agents have access to the macOS GUI"). Source: <https://www.launchd.info/>

### F4. Plist mechanics: one-shot job, logging, manual trigger

- **One-shot vs KeepAlive**: for a scheduled maintenance task, omit `KeepAlive` (or set false) — launchd runs the program at each trigger and lets it exit. `KeepAlive=true` is for supervised daemons and would restart the job forever. `RunAtLoad=true` additionally fires once at login/bootstrap — useful here as a "catch up if the Mac was off overnight" trigger, but it then runs at *every* login; gate it in-script with staleness detection (compare local image digest vs registry, or a last-success timestamp file) so redundant runs no-op in seconds. Source: <https://www.launchd.info/>
- **Logging**: `StandardOutPath`/`StandardErrorPath` redirect the job's output to files; launchd.info: "very important when it comes to debugging a job". This composes with the repo's bounded-run rule: the wrapper writes `rc=` into the log file, satisfying `long-running-command-hangs.md` rule 3 (trust file content, not a piped tail). Source: <https://www.launchd.info/>
- **Manual run**: `launchctl kickstart gui/$(id -u)/<label>` runs the service immediately regardless of its schedule (`-k` kills a running instance first) — this is the "run it now" story that keeps parity with `mise run sync` invoked by hand. Sources: <https://davidhamann.de/2018/03/13/setting-up-a-launchagent-macos-cron/>, <https://ss64.com/mac/launchctl.html>
- **Modern load/unload**: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<plist>` / `bootout` (legacy `load`/`unload` still work — homebrew-autoupdate still ships `launchctl load`).

### F5. Prior art: brew autoupdate is exactly this shape (user LaunchAgent updating a toolchain in the background)

- `Homebrew/homebrew-autoupdate` generates a per-user LaunchAgent with keys `Label`, `Program`/`ProgramArguments`, `StartInterval` (default 86400s), `StandardOutPath`+`StandardErrorPath` → `~/Library/Logs/com.github.domt4.homebrew-autoupdate`, `LowPriorityIO`/`LowPriorityBackgroundIO=true`, `ProcessType=Background`, `RunAtLoad` only under `--debug`; loads with `/bin/launchctl load <plist>`. Source (code): <https://github.com/Homebrew/homebrew-autoupdate/blob/24c4193f89280b3ec38722010623ae2971dc5072/lib/autoupdate/start.rb>; README: <https://github.com/Homebrew/homebrew-autoupdate> ("will run `brew update` in the background once every 24 hours... utilising launchd").
- Two transferable patterns: (a) `ProcessType=Background` + `LowPriorityIO` keeps a multi-hour 38GB pull from starving the interactive session — though for a pull we *want* network throughput, so consider omitting `LowPriorityIO` and keeping only `ProcessType=Background`; (b) notification UX: brew autoupdate ships a signed notifier app with `--notify-on-error` (alert only on failure) — the exact alert policy Ray wants.
- chezmoi's own docs show only cron + systemd-timer automation examples for `chezmoi upgrade` (no launchd example) — cache `docs/research/mintlify-cache/twpayne/chezmoi/llms-full.txt:5219-5252` — reinforcing that on macOS the community norm for this job class is launchd (brew autoupdate), not cron.

### F6. Alerting from an unattended launchd job

- **osascript `display notification` is fragile from background contexts**: since Big Sure the notification is attributed to the calling process, which needs Notification permission; terminal apps often never appear in the Notifications pane until a notification is delivered — a chicken-and-egg that makes osascript notifications silently vanish from launchd jobs. Documented: <https://github.com/gsd-build/gsd-2/issues/2632>, <https://forum.latenightsw.com/t/trying-to-use-terminal-for-display-notification/5068>.
- **terminal-notifier** registers as a standalone app with its own Notification-Center permission entry (one-time allow prompt), making it the reliable local-notification path from launchd. Source: <https://smallsharpsoftwaretools.com/tutorials/macos-notifications/> and the gsd-2 issue above. brew autoupdate's signed notifier app solves the same problem the same way (F5).
- **ntfy.sh (push-to-phone, zero-dependency)**: publishing is a bare HTTP POST — `curl -H "Priority: high" -d "verify-local FAILED rc=1" ntfy.sh/<topic>` — with a documented cron-failure idiom `job.sh && curl -d "OK" ... || curl -H "Priority: high" -d "FAILED" ...`; works headless, survives the Mac being the *source* (unlike macOS notifications, visible even when away from the Mac). Source: <https://docs.ntfy.sh/publish/>, <https://docs.ntfy.sh/examples/>. GitHub-issue creation via `gh issue create` is also viable since the gui-domain agent has keychain + gh auth (F3), and fits the repo's existing gh-centric workflow.
- Recommended layering for this repo: ntfy (or Pushover) for failure push + terminal-notifier for local success toast; alert content = the `rc=` line and log-tail path, honoring evidence discipline.

### F7. Docker Desktop detection/start from the job

- Detection: `docker desktop status` (Docker Desktop CLI, bundled with current Docker Desktop; commands `start|stop|restart|status|logs|update|diagnose`; `engine ls/use` are Windows-only). Source: <https://docs.docker.com/desktop/features/desktop-cli/>, <https://docs.docker.com/reference/cli/docker/desktop/status/>. Fallback probe that also validates the engine end-to-end: `docker info` exit code.
- Start: `docker desktop start` is the first-party path, but has an open reliability bug on macOS (docker/cli#6837 "docker desktop start -d fails to start Docker Desktop", 2025/2026). Robust fallback used community-wide: `open -a Docker --background` then poll `docker info` with a bounded loop (e.g., 12×10s, then fail). Sources: <https://github.com/docker/cli/issues/6837>, <https://www.tutorialpedia.org/blog/how-to-start-docker-from-command-line-in-mac/>. Note `open -a` requires a GUI login session — consistent with running as a gui/<uid> LaunchAgent (F3); fully headless DD on macOS is unsupported (docker/for-mac#6504).
- Context invariant: the job must **verify** `docker context show` == `desktop-linux` and abort-with-alert on mismatch, never switch (repo rule `do-not.md` item 8). "DD not running and won't start within the bound" → skip-with-alert, not blind wait (`long-running-command-hangs.md`).
- Policy choice to surface to Ray: auto-start DD (`open -a Docker --background` + bounded wait) vs skip-with-alert when DD is down. Auto-start is low risk since DD is the supported runtime and the agent runs in the GUI session; skip-with-alert is the conservative default.

### F8. macOS 13+ visibility/consent: LaunchAgents surface in System Settings

- Since macOS 13 Ventura, adding a LaunchAgent triggers a "Background item added" Notification Center banner, and the item appears in System Settings → General → Login Items & Extensions, where the user can toggle it off (disables without deleting the plist). For a personal machine this is a *feature* — the job is visible and one-click disable-able — not MDM friction. Sources: <https://support.apple.com/guide/deployment/manage-login-items-background-tasks-mac-depdca572563/web>, <https://mjtsai.com/blog/2022/10/27/venturas-open-at-login-vs-allow-in-the-background/>, <https://n8felton.wordpress.com/2022/10/24/login-and-background-item-management-in-macos-ventura-13/>.
- TCC note for the agent itself: if the wrapper ever needs a protected location, TCC attributes access through the attribution chain to the responsible executable — granting FDA to `/bin/bash` is the ugly workaround and a known security smell; keep the job's file surface outside TCC-protected paths (it naturally is, F2) or wrap in a dedicated signed app/`fdautil` if that ever changes. Sources: <https://eclecticlight.co/2018/10/02/how-privacy-protection-is-enforced-through-the-attribution-chain/>, <https://nunn.au/2023/11/28/tcc-launchd-woes>, <https://forums.macrumors.com/threads/getting-a-shell-script-full-disk-access-from-launchagent.2206368/>.

## Concrete design sketch (launchd venue)

```xml
<!-- ~/Library/LaunchAgents/com.raymanaloto.dotfiles.sync-verify.plist -->
<key>Label</key><string>com.raymanaloto.dotfiles.sync-verify</string>
<key>ProgramArguments</key>
<array><string>/bin/zsh</string><string>-lc</string>
  <string>exec ~/dotfiles/scripts/launchd-sync-verify.sh</string></array>
<key>StartCalendarInterval</key>
<dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>30</integer></dict>
<key>RunAtLoad</key><true/>            <!-- catch-up at login; script no-ops if fresh -->
<key>ProcessType</key><string>Background</string>
<key>StandardOutPath</key><string>~/Library/Logs/dotfiles-sync-verify/out.log</string>
<key>StandardErrorPath</key><string>~/Library/Logs/dotfiles-sync-verify/err.log</string>
```

Wrapper (thin bash per zero-bash-logic; real logic → `python/` + a `mise run scheduled-sync` task per mise-tasks-only): export mise shims PATH → staleness check (registry `:dev` digest vs local; exit 0 "fresh" fast-path) → assert `docker context show`=desktop-linux → DD up? (`docker desktop status` || `docker info`; optional `open -a Docker --background` + ≤120s bounded poll) → `mise run sync` and `mise run verify-local` each under the repo's timeout wrapper, `rc=` to log → on failure `curl ntfy` (+ optional `gh issue create`); on success terminal-notifier toast. Cadence: 06:30 local ≈ 4.5h after the 02:00 CT publish (image is built and promoted by then); sleep coalescing (F1) turns any missed 06:30 into one run at wake, and `RunAtLoad` + staleness check covers the powered-off-overnight case cron cannot. Manual parity: `launchctl kickstart gui/$(id -u)/com.raymanaloto.dotfiles.sync-verify`.

## Uncertainties / gaps

- **launchd has no per-job timeout for a multi-hour pull** — the bound must live in the wrapper (repo already has `lint.py`-style timeout machinery; sync may legitimately run hours, so the bound should be generous, e.g. 6h, with progress logging). No source claims launchd kills long StartCalendarInterval jobs, but I found no authoritative statement of a *maximum* runtime either.
- **Overlap protection**: if a kickstart or RunAtLoad fires while a scheduled run is mid-pull, launchd will not start a second instance of the *same label* while one is running (one-instance-per-label is standard launchd behavior), but I did not find a citable current-man-page statement — the wrapper should still take a flock as belt-and-braces.
- **Exact `SSH_AUTH_SOCK` inheritance on macOS 15/26**: the smop.co.uk evidence is macOS 13/14-era (2023); the mechanism (`com.openssh.ssh-agent` launchd socket in gui-domain inherited env) is long-stable but should be probed on Ray's current OS with `launchctl print gui/$(id -u) | grep SSH_AUTH_SOCK`.
- **Doppler CLI token storage** (keychain vs `~/.doppler` config file) not verified; if file-based, no TCC/keychain concern at all; if keychain-based, gui-domain agents still see the unlocked login keychain (F3).
- **`docker desktop start` reliability** on current DD versions (docker/cli#6837 open) — prefer the `open -a Docker --background` + `docker info` poll until probed locally.
- **Docker Desktop version that GA'd the `docker desktop` CLI** not pinned down from the docs page (docs don't state it); needs a `docker desktop version` probe on Ray's install.
- cron findings are one-sided by design (this angle's brief): no scenario surfaced where cron beats a LaunchAgent for this job on macOS.

## GitHub repos touched

- [Homebrew/homebrew-autoupdate](https://github.com/Homebrew/homebrew-autoupdate) — prior-art LaunchAgent plist keys read from `lib/autoupdate/start.rb` + README scheduling/notification behavior
- [docker/cli](https://github.com/docker/cli) — issue #6837, `docker desktop start -d` failure on macOS
- [docker/for-mac](https://github.com/docker/for-mac) — issue #6504, headless Docker Desktop limitations on macOS
- [binwiederhier/ntfy](https://github.com/binwiederhier/ntfy) — docs.ntfy.sh publish/examples (curl POST alert idiom)
- [gsd-build/gsd-2](https://github.com/gsd-build/gsd-2) — issue #2632, osascript notification permission chicken-and-egg from background jobs
- [jdx/mise](https://github.com/jdx/mise) — local mintlify cache: shims for non-interactive environments
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — local mintlify cache: upgrade-automation examples (cron/systemd only)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding inventory report + rules (do-not.md, long-running-command-hangs.md, mise-tasks-only.md)
