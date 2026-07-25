# Angle 2 — Claude Code scheduled agents/routines: cloud vs local reality

Run F, domain "Automated macOS pull/verify + community trends sweep".
Researched 2026-07-09 from the live code.claude.com docs (Claude Code CLI at
2.1.206 per CHANGELOG head, fetched same day). Question: can ANY Claude Code
scheduling surface drive `mise run sync` + `mise run verify-local` on Ray's
local Mac (Docker Desktop, desktop-linux context, launchd SSH agent, Doppler
auth), and is a Claude-agent venue sensible for that deterministic job at all?

## Findings

### F1. Claude Code today has exactly three scheduling surfaces, and the docs publish an official comparison table

Both `scheduled-tasks.md` and `desktop-scheduled-tasks.md` carry the same
canonical table (fetched 2026-07-09):

| | Cloud (routines) | Desktop scheduled tasks | `/loop` (session-scoped) |
|---|---|---|---|
| Runs on | Anthropic cloud | Your machine | Your machine |
| Requires machine on | No | Yes | Yes |
| Requires open session | No | No | Yes |
| Access to local files | **No (fresh clone)** | Yes | Yes |
| Permission prompts | No (runs autonomously) | Configurable per task | Inherits from session |
| Minimum interval | 1 hour | 1 minute | 1 minute |

Source: https://code.claude.com/docs/en/scheduled-tasks.md and
https://code.claude.com/docs/en/desktop-scheduled-tasks.md ("Compare
scheduling options"). Scheduled tasks require Claude Code v2.1.72+; `/schedule`
(routine creation from CLI) requires v2.1.81+.

### F2. Cloud routines CANNOT touch the Mac — confirmed precisely

Routines (research preview; API beta header `experimental-cc-routine-2026-04-01`,
i.e. an April-2026-era feature) are "a saved Claude Code configuration …
packaged once and run automatically. **Routines execute on Anthropic-managed
cloud infrastructure, so they keep working when your laptop is closed.**"
Each run clones the selected GitHub repos fresh ("Each repository is cloned
at the start of a run, starting from the default branch") inside "an
isolated, Anthropic-managed VM" (claude-code-on-the-web.md § Security and
isolation). Docker IS available in the cloud sandbox ("Docker is available
for running containerized services … `docker compose up`"), but that is
dockerd inside the Anthropic VM — it is not, and cannot reach, Ray's Docker
Desktop, the `desktop-linux` context, the ~38GB local image cache, the
launchd SSH agent, or `/run/host-services/ssh-auth.sock`. The comparison
table states it flatly: local-file access = "No (fresh clone)".

Triggers: schedule (min interval 1 hour, presets + custom cron via
`/schedule update`, "runs may start a few minutes after the scheduled time
due to stagger"), API (`POST …/routines/<id>/fire` with per-routine bearer
token), and GitHub events (PR/release). Runs "draw down subscription usage
the same way interactive sessions do" plus "a daily cap on how many runs can
start per account".

Sources: https://code.claude.com/docs/en/routines.md;
https://code.claude.com/docs/en/claude-code-on-the-web.md.

**Consequence for Run F:** the nightly-pull/verify job is definitionally
un-runnable as a cloud routine. The only legitimate routine role here is
downstream: e.g. CI (or the Mac's failure handler) POSTs the `/fire` endpoint
to spawn a *cloud* triage session over the repo — useful for log analysis,
useless for touching the Mac.

### F3. Remote Control and Dispatch execute locally but provide no scheduler — there is no cloud→Mac trigger bridge

- Remote Control (v2.1.51+): "Claude keeps running locally the entire time,
  so nothing moves to the cloud … The web and mobile interfaces are just a
  window into that local session." It is strictly a viewing/steering surface
  over an **already-running** local `claude` process ("Remote Control runs
  as a local process. If you close the terminal … the session ends"). The
  local process makes "outbound HTTPS requests only and never opens inbound
  ports" — it polls; nothing on the cloud side can *start* it. A cloud
  routine therefore cannot reach the Mac via Remote Control.
  Source: https://code.claude.com/docs/en/remote-control.md.
- Dispatch (Desktop/Cowork, Pro/Max only): "You message Dispatch a task, and
  it decides how to handle it" — human-initiated from the phone, spawning a
  session on the Desktop app; it is not schedulable and not routine-drivable.
  Source: https://code.claude.com/docs/en/desktop.md § Sessions from Dispatch.

### F4. Desktop scheduled tasks are the ONE native Claude scheduler that runs on the Mac — but their semantics are wrong for this job

Desktop app → Routines → New routine → **Local** creates a scheduled task
that "runs on your machine with direct access to your files and tools, but
**only fires while the app is open and your computer is awake**." Details
that matter for a 02:00-publish-chasing pull/verify job
(https://code.claude.com/docs/en/desktop-scheduled-tasks.md):

- "Desktop checks the schedule every minute **while the app is open**";
  "If your computer sleeps through a scheduled time, the run is skipped."
  Mitigation is a **Keep computer awake** setting ("Closing the laptop lid
  still puts it to sleep").
- Missed-run semantics are catch-up-once: "Desktop starts exactly one
  catch-up run for the most recently missed time and discards anything
  older … A task scheduled for 9am might run at 11pm if your computer was
  asleep all day." (launchd's `StartCalendarInterval` has effectively the
  same fire-on-wake coalescing, but without the LLM around it.)
- Every run is a **fresh LLM session interpreting a prompt** (the prompt is
  stored as `~/.claude/scheduled-tasks/<task-name>/SKILL.md`), with a
  per-task permission mode. "If a task runs in Ask mode and needs to run a
  tool it doesn't have permission for, **the run stalls until you approve
  it**" — the documented workaround is to pre-approve tools via "Run now"
  + "always allow".
- Alerting exists but is presence-oriented: "When a task fires, you get a
  desktop notification" — it notifies on *start*, and success/failure lives
  in the session transcript, not in a failure-only alert channel.
- Tasks run against "whatever state your working directory is in, including
  uncommitted changes" unless the isolated-worktree toggle is on.

So Desktop scheduled tasks CAN in principle run `mise run sync && mise run
verify-local` on the Mac (they inherit the GUI login session, so Docker
Desktop and the launchd SSH agent are reachable). But each nightly firing
pays an LLM session (subscription usage) to re-derive "run these two mise
tasks", is only as reliable as "the Desktop app was open", and a multi-hour
38GB buildkit pull sits inside an agent turn — the exact "blind long-running
wait" the repo's `long-running-command-hangs.md` rule exists to prevent, now
with a nondeterministic supervisor.

### F5. Session-scoped `/loop`/CronCreate is disqualified by design

"Tasks are session-scoped … stop when you start a new one"; "Tasks only fire
while Claude Code is running and idle"; "Recurring tasks automatically expire
7 days after creation"; recurring fires get deterministic jitter "up to 30
minutes after the scheduled time". Fine for babysitting a PR inside a
session; unusable as durable nightly infrastructure.
Source: https://code.claude.com/docs/en/scheduled-tasks.md.

### F6. launchd-wrapped `claude -p` is fully supported and documented — but it inserts an LLM where none is needed

Headless mechanics (https://code.claude.com/docs/en/headless.md):

- `claude -p "<prompt>"` runs non-interactively; `--bare` "skips
  auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and
  CLAUDE.md" and "is the recommended mode for scripted and SDK calls, and
  will become the default for `-p` in a future release". Note the tradeoff
  in THIS repo: without `--bare`, a launchd-spawned `claude -p` loads
  `.claude/settings.json`'s PreToolUse hook (`dotfiles-setup hook
  pretooluse`), which itself needs Ray's uv/python env; with `--bare`, the
  mise-tasks-only guard is silently absent.
- Permission control for unattended runs: `--allowedTools "Bash(mise run
  sync*)…"`, `--permission-mode dontAsk` ("fully non-interactive for CI
  pipelines"), or `bypassPermissions`/`--dangerously-skip-permissions` —
  which the docs scope hard: "**Only use this mode in isolated environments
  like containers, VMs, or dev containers without internet access**", refuses
  to start as root, and "offers no protection against prompt injection". In
  headless auto mode, "repeated blocks abort the session since there is no
  user to prompt." (https://code.claude.com/docs/en/permission-modes.md)
- Auth under launchd: subscription OAuth creds come from the keychain (a
  user LaunchAgent in the GUI session can access it); `--bare` "skips OAuth
  and keychain reads" and needs `ANTHROPIC_API_KEY`/apiKeyHelper; long-lived
  `claude setup-token` tokens are "limited to inference-only" (remote-control.md
  troubleshooting) — sufficient for `-p`, insufficient for Remote Control.
- Cost is per-run LLM spend: `--output-format json` "includes
  `total_cost_usd` and a per-model cost breakdown"; on a subscription login
  the run draws down plan usage like any session. A daily multi-turn agent
  run babysitting an hours-long pull is the worst-shaped consumer of a
  5-hour-window rate limit (long wall-clock, trivial reasoning content).
- Community precedent exists and is exactly this pattern: crontab/launchd
  `StartCalendarInterval` plists invoking `claude -p` with `--allowedTools`
  / `--max-turns` / budget caps (e.g. claudeguide.io/claude-code-scheduled-tasks,
  jeangalea.com/claude-code-overnight, runclauderun.com — a purpose-built
  macOS scheduler app for Claude Code; all 2025-2026 material). Which shows
  it works — for jobs that need judgment each run. Pull+verify does not.

### F7. The right Claude integration point is the FAILURE path, not the schedule

Two documented mechanisms let a plain launchd script escalate into Claude
only when something breaks:

- **Channels** (v2.1.80+, research preview): "A channel is an MCP server
  that pushes events into your running Claude Code session … Forward CI
  results … so Claude can react while you're away." Requires an
  already-open local session started with `--channels` ("Events only arrive
  while the session is open, so for an always-on setup you run Claude in a
  background process or persistent terminal"). Official Telegram/Discord/
  iMessage plugins (iMessage is macOS-native: reads `~/Library/Messages/
  chat.db`, needs Full Disk Access + Automation TCC grants); a custom
  webhook-receiver channel is a documented build target.
  Source: https://code.claude.com/docs/en/channels.md.
- **One-shot triage**: the launchd failure handler runs
  `claude -p "read /path/verify-local.log, diagnose, file a gh issue"
  --allowedTools …` — Claude spends tokens only on red nights — or fires a
  cloud routine's `/fire` API endpoint for repo-side triage.
- Remote Control mobile push notifications (v2.1.110+) notify Ray's phone,
  but again presuppose a running session; ntfy/terminal-notifier from the
  script is strictly simpler.

### F8. Verdict for the domain recommendation

**A Claude-agent venue is over-engineering for this job.** `mise run sync`
and `mise run verify-local` are deterministic, already bounded, already
alert-shaped (rc + logs). Every Claude scheduling surface either (a) cannot
reach the Mac at all (cloud routines — hard disqualifier, confirmed), (b) is
session-scoped/ephemeral (`/loop`), or (c) can run it but adds an LLM
supervisor whose only contributions are cost, nondeterminism, a permission
surface (`bypassPermissions` explicitly contraindicated on a host; Ask mode
stalls unattended runs), and an availability dependency (Desktop app open /
claude process alive) on top of the same sleep/wake constraints launchd
already handles natively. The sensible architecture is: **launchd
LaunchAgent → plain bounded script (mise tasks) → alert on failure**, with
Claude entering only at the failure boundary (ntfy/iMessage/gh-issue alert,
optionally a one-shot `claude -p` triage or a channel push into a standing
session) — i.e., use Claude where judgment is needed, never as the cron.

## Uncertainties / gaps

- The raw CHANGELOG fetch (anthropics/claude-code, main) was summarized
  lossily by the fetch model; version anchors above are instead taken from
  the docs' explicit min-version annotations (scheduled tasks v2.1.72,
  `/schedule` v2.1.81, Remote Control v2.1.51, channels v2.1.80, push
  notifications v2.1.110; latest release 2.1.206 on 2026-07-09). A native
  "launchd export" or OS-level scheduler feature was not found in docs or
  the CHANGELOG excerpt, but absence is proven only to the depth of the
  llms.txt index + CHANGELOG summarization.
- Routines' exact daily run cap is not published ("See your current limits
  at claude.ai/code/routines"); routines/channels/Remote Control are all
  research preview, so semantics may shift.
- Whether the Desktop app's scheduled-task sessions inherit the full GUI
  login environment (specifically `SSH_AUTH_SOCK` from Ray's launchd agent
  and PATH-resolved mise) is inferred from Desktop being a GUI-session app,
  not verified empirically — a "Run now" probe on the Mac would settle it.
- Community tools (runclauderun.com, gruckion/claude-scheduler plugin) were
  identified but not source-audited; cited only as precedent that the
  launchd-wraps-`claude -p` pattern is in real use.
- Rate-limit arithmetic (what fraction of a Max plan a daily Opus headless
  run consumes) was not quantified; docs confirm the accounting model
  (subscription drawdown + `total_cost_usd` on API) but publish no numbers.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — code.claude.com docs pages (routines, scheduled-tasks, desktop-scheduled-tasks, remote-control, claude-code-on-the-web, headless, permission-modes, channels, desktop, llms.txt) + raw CHANGELOG.md.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding inventory `docs/research/runs/research-20260709-r2-inventory/report.md` and repo rules constraining the design (mise-tasks-only, long-running-command-hangs).
