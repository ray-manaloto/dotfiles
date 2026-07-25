# Run F / Angle 3 — Venue evaluations: jdx/pitchfork daemon vs self-hosted GHA runner on Ray's Mac

Research date: 2026-07-09 (remote session; Bash unavailable — all evidence via
local mintlify cache, WebFetch, WebSearch). Grounding baseline:
`docs/research/runs/research-20260709-r2-inventory/report.md`.

Task under evaluation: after CI publishes a new `:dev` image (nightly 02:00
America/Chicago + on merges), Ray's macOS host should automatically run
`mise run sync` (buildkit pull, ~38GB, digest-aware, possibly hours) and
`mise run verify-local` (R1/R2/R3 + persistence gates), then alert on failure.

---

## Findings

### A. jdx/pitchfork — NOT "supervisor only": it has first-class cron scheduling

**A1. Pitchfork has native cron scheduling with overlap control — it is a
scheduler, not just a process supervisor.** The cached docs
(`docs/research/mintlify-cache/jdx/pitchfork/llms-full.txt:3236-3381`, source
<https://www.mintlify.com/jdx/pitchfork/guides/scheduling>) document a
`cron = { schedule = "...", retrigger = "..." }` daemon option with a 6-field
cron format (seconds-first). The doc's own headline example is literally this
job shape: `cron = { schedule = "0 0 2 * * *", retrigger = "finish" }  # run
at 2 AM daily` (llms-full.txt:3248). Four `retrigger` modes govern what happens
when the schedule fires while a previous run is still active
(llms-full.txt:3290-3340):

- `finish` (default) — only start a new run if the previous finished. This is
  the exact semantics needed for a multi-hour 38GB pull: a slow sync that is
  still running at the next trigger is simply not re-triggered, so runs never
  overlap.
- `always` / `success` / `fail` — the `fail` mode is built-in retry ("keep
  re-running every 10 minutes until the task succeeds", llms-full.txt:3330-3340),
  useful as a retry lane after a failed sync.

The supervisor checks cron schedules every 10s by default
(`PITCHFORK_CRON_CHECK_INTERVAL`, llms-full.txt:4521, 4952-4954), and the
architecture doc shows a dedicated cron watcher task
(llms-full.txt:1367, 1426-1428, `src/supervisor/watchers.rs` at :1530).

**A2. First-class mise integration — directly satisfies the mise-tasks-only
rule.** Two documented mechanisms
(llms-full.txt:2866-2979, source
<https://www.mintlify.com/jdx/pitchfork/guides/mise-integration>):

- `mise = true` per-daemon or via `[settings.general]` wraps the command in
  `mise x --` so mise-managed tools are on PATH even in login-daemon/cron
  context — the docs explicitly call out that "Daemons started at boot or via
  cron don't have that luxury — they run without an interactive shell"
  (llms-full.txt:2879-2882) and that the cron+boot PATH problem is solved by
  `mise = true` (llms-full.txt:3368-3379).
- "Using mise tasks as daemon commands" is a documented pattern:
  `run = "mise run docs:dev"` (llms-full.txt:2946-2955). So the daemon body can
  be exactly `mise run sync && mise run verify-local` (or a single wrapper
  task), keeping mise tasks as the sole entry point per
  `.claude/rules/mise-tasks-only.md`.

**A3. launchd boot registration is built in.** `pitchfork boot enable` creates
`~/Library/LaunchAgents/dev.jdx.pitchfork.plist` on macOS; at login launchd
starts the supervisor, which starts all daemons with `boot_start = true`
(llms-full.txt:2140-2224, source
<https://www.mintlify.com/jdx/pitchfork/guides/boot-start>). Boot/cron daemons
must live in `~/.config/pitchfork/config.toml`, not project-level
`pitchfork.toml` (Note at llms-full.txt:2176-2180) — relevant because the
sync job is per-machine, matching the repo's `mise.local.toml`-style per-clone
override philosophy. Being a user LaunchAgent, the supervisor runs inside
Ray's GUI login session — the same session where Docker Desktop
(`desktop-linux` context, `~/.docker/run/docker.sock`) and the
launchd-provided `SSH_AUTH_SOCK` live (see C2).

**A4. Failure alerting via lifecycle hooks.** `[daemons.<name>.hooks]`
supports `on_ready` / `on_fail` / `on_retry` / `on_stop` / `on_exit`
(llms-full.txt:2535-2688, source
<https://www.mintlify.com/jdx/pitchfork/guides/lifecycle-hooks>). `on_fail`
fires when retries are exhausted and receives `PITCHFORK_EXIT_CODE`,
`PITCHFORK_EXIT_REASON`, `PITCHFORK_DAEMON_ID` env vars
(llms-full.txt:2613-2623); the doc's own example is a Slack-webhook alert on
failure (llms-full.txt:2636-2645). An `on_fail` of
`terminal-notifier`/`osascript`, an ntfy.sh curl, or `gh issue create` slots in
directly. Caveat: hooks are fire-and-forget and hook errors are only logged
(llms-full.txt:2627-2632), so the alert channel itself should be simple and
reliable. Observability beyond hooks: `pitchfork logs <name>` (SQLite-backed
log store with `--grep`/`--regex` filtering as of v2.16.0), TUI, and web UI.

**A5. No per-run wall-clock timeout — the hard bound must live in the wrapped
task.** A grep of the full cached reference finds resource limits
(`mem_limit`, `cpu_limit`, monitored per supervisor tick,
llms-full.txt:4395-4415) and IPC/stop/HTTP-check timeouts
(llms-full.txt:4502-4523), but **no max-runtime option for a daemon run**.
`retrigger = "finish"` prevents overlap but does not kill a wedged run. So the
repo's bounded-commands rule (`.claude/rules/long-running-command-hangs.md`)
is satisfied the same way it already is for lint: the python-library layer of
the wrapper task (skill → mise task → `python/src/dotfiles_setup/…`, precedent
`lint.py`) owns the hard timeout, and pitchfork owns scheduling, retry,
logging, and alerting.

**A6. Maturity signals — young but fast-moving, same trusted author as
mise/hk.** Latest release v2.16.0 published **2026-07-09** (release page shows
"09 Jul 15:35"; repo sidebar confirms "v2.16.0 (July 9, 2026)") —
<https://github.com/jdx/pitchfork/releases/tag/v2.16.0>. Cadence is roughly
weekly (v2.9.1 in early May 2026 → v2.16.0 in July 2026). Tag history shows
v0.1.x Dec 2024, dormancy, v0.2.x Oct 2025, **v1.0.0 on Jan 19, 2026**, and a
very fast v1→v2.16 run since — <https://github.com/jdx/pitchfork/tags>. Repo:
558 stars, 33 forks, Rust, MIT, sponsored by entire.io and 37signals —
<https://github.com/jdx/pitchfork>. Recent changelogs still fix cron
reliability (v2.15.0 "cron reliability fixes") — the scheduling feature is
actively hardened but young. jdx is the author of mise and hk, both already
load-bearing in this repo, and pitchfork's docs are already in the repo's
mintlify cache/catalog (`docs/research/mintlify-catalog.md`). Pitchfork is
installable via mise (llms.txt:38, installation page), but is **not currently
pinned anywhere in the repo's toml files** (grep of `*.toml` for `pitchfork`:
no matches) — adoption means adding a pin + a `~/.config/pitchfork/config.toml`
managed via chezmoi `home/` templates.

**Pitchfork verdict: viable.** It is a scheduler + supervisor + retry engine +
log store + alert-hook dispatcher in one user-session daemon, with documented
mise-task integration. Its gaps (no per-run timeout; staleness/digest logic)
land exactly where the repo convention wants them anyway: in the python
library under the mise task.

### B. Self-hosted GHA runner on Ray's personal Mac

**B1. Disqualifying-grade security posture: ray-manaloto/dotfiles is a PUBLIC
repo.** Verified: the repo page shows a **Public** badge
(<https://github.com/ray-manaloto/dotfiles>). GitHub's security hardening
guidance is unambiguous: self-hosted runners should "almost never be used for
public repositories" because "any user can open pull requests against the
repository and compromise the environment"; self-hosted runners "can be
persistently compromised by untrusted code in a workflow", and "anyone who can
fork the repository and open a pull request … are able to compromise the
self-hosted runner environment", including access to "secrets and the
GITHUB_TOKEN which, depending on its settings, can grant write access to the
repository" (<https://docs.github.com/en/actions/reference/security/secure-use>,
self-hosted runner hardening section). On Ray's personal Mac the blast radius
is maximal: Doppler CLI auth, the SSH agent (R2 outbound key), the Docker
Desktop socket, and the entire home directory. GitHub's recommended mitigation
is ephemeral runners ("GitHub recommends implementing autoscaling with
ephemeral self-hosted runners; autoscaling with persistent self-hosted runners
is not recommended"; `--ephemeral` deregisters after one job —
<https://docs.github.com/en/actions/reference/runners/self-hosted-runners>),
plus first-time-contributor approval gates — but ephemeral single-job runners
on a laptop defeat the always-on-schedule purpose, and approval gates only
throttle, not remove, the fork-PR attack path. **For a private repo this
venue's risk profile would be acceptable** (the same docs treat private-repo
self-hosted runners as the normal case, with residual risks around persistent
state); for this public repo it is effectively ruled out unless the repo goes
private or an isolated sacrificial machine is used.

**B2. Mechanically, the runner WOULD work in Ray's user session.**
`./svc.sh install && ./svc.sh start` on macOS installs a **user-domain
LaunchAgent** from `bin/actions.runner.plist.template` with `RunAtLoad=true`,
`SessionCreate=true`, `ProcessType=Interactive`
(<https://raw.githubusercontent.com/actions/runner/main/src/Misc/layoutbin/actions.runner.plist.template>;
service docs:
<https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application>).
As a LaunchAgent it runs only while Ray is logged into a GUI session
(LaunchAgents are per-login-session — community + AWS EC2 Mac guidance
consistently hits this: runner offline after reboot until login, e.g.
<https://medium.com/@virajpatoliya/configure-github-actions-runner-on-macos-using-launchagent-aws-ec2-mac-a29d9c46e9c9>,
<https://github.com/actions/runner/issues/947>). In that session it can reach
Docker Desktop's user socket (Docker Desktop itself is a per-user GUI app with
a "Start Docker Desktop when you sign in to your computer" setting —
<https://docs.docker.com/desktop/settings-and-maintenance/settings/>) and the
launchd-provided `SSH_AUTH_SOCK` (macOS's `com.openssh.ssh-agent` LaunchAgent
uses `SecureSocketWithKey: SSH_AUTH_SOCK`, which launchd injects into the
user's launch context so launchd-spawned processes inherit it —
<https://www.smop.co.uk/blog/2023/10/05/how-to-really-configure-mac-ssh-agent/>,
<https://www.packetmischief.ca/2016/09/06/ssh-agent-on-os-x/>). PATH would
lack mise, so workflow steps would invoke `~/.local/bin/mise run sync` etc. —
mise-tasks-only is satisfiable.

**B3. Free plumbing the runner venue would provide.** (i) Trigger:
`on: workflow_run: workflows: [ci], types: [completed]` with
`if: github.event.workflow_run.conclusion == 'success'` — exactly the
"after the nightly publish" shape; constraint: the triggered workflow file
must exist on the default branch; max 3 levels of workflow_run chaining
(<https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>).
(ii) Bounded commands: native `timeout-minutes` per job/step, and self-hosted
jobs may run up to **5 days** (vs 6h hosted), so a multi-hour 38GB pull fits
(<https://docs.github.com/en/actions/reference/limits>). (iii) Alerting/
visibility: the run appears in the Actions UI and GitHub's normal
failure-notification machinery for free. (iv) Maintenance: the runner
application self-updates by default ("Receive automatic updates for the
self-hosted runner application only"; `--disableupdate` opts out, but "If you
do not perform a software update within 30 days, the GitHub Actions service
will not queue jobs to your runner" —
<https://docs.github.com/en/actions/concepts/runners/self-hosted-runners>,
<https://docs.github.com/en/actions/reference/runners/self-hosted-runners>).
Communication is outbound-443 long-poll only, no inbound ports.

**Runner verdict: mechanically viable, security-inappropriate.** Everything
works — session env, Docker Desktop, SSH agent, workflow_run trigger, native
timeouts, free Actions UI alerting — but B1 (public repo + personal machine
holding Doppler/SSH/docker credentials) is the controlling fact. GitHub's own
docs say "almost never" for exactly this configuration.

### C. Cross-cutting comparison against the repo's rules

| Criterion | pitchfork | self-hosted runner |
|---|---|---|
| Scheduling vs nightly 02:00 publish | native 6-field cron, e.g. `0 0 3 * * *` local, `retrigger=finish` | `workflow_run: completed` on ci.yml — event-driven, no staleness window |
| mise-tasks-only | `run = "mise run sync-verify"` + `mise = true` (documented pattern) | workflow steps call `mise run …` (absolute path) |
| Bounded commands | NO native per-run timeout → bound lives in python wrapper (lint.py precedent) | native `timeout-minutes`; self-hosted job limit 5 days |
| Overlap control (hours-long pull) | `retrigger=finish` built-in | GHA `concurrency` group built-in |
| Needs GUI login session | yes (LaunchAgent supervisor) | yes (LaunchAgent runner) |
| Docker Desktop + SSH_AUTH_SOCK | inherited in user session | inherited in user session |
| Failure alert | `on_fail` hook (exit code env) → notifier/ntfy/gh | Actions UI + GH notifications free |
| Security exposure | none beyond the Mac itself (no inbound, no remote code) | public-repo fork-PR → arbitrary code on the Mac ("almost never" per GitHub docs) |
| Maturity | v1.0 Jan 2026, v2.16 Jul 2026, weekly releases, 558★, jdx | GA product, actions/runner, auto-updates |
| Repo-convention fit | jdx family (mise/hk/fnox/pklr all in-repo); docs already in mintlify cache | adds CI-machinery onto a personal machine |

**Bottom line for the domain recommendation:** pitchfork is the viable venue
of the two; the self-hosted runner is ruled out on public-repo security
grounds despite its superior trigger (event-driven workflow_run vs polling
cron) and free UI. Pitchfork's one real gap vs plain launchd
(StartCalendarInterval) is that it adds a supervisor daemon as a dependency —
but in exchange it provides retry, overlap control, mise env wrapping, log
storage, and failure hooks that raw launchd leaves to hand-rolled code. If
angle 1 (launchd) is chosen instead, pitchfork remains the strongest
"batteries included" alternative; either way the digest-staleness check, hard
timeout, and alert dispatch belong in a `dotfiles_setup` python module fronted
by a mise task, which any venue then merely schedules.

## Uncertainties / gaps

1. **Pitchfork cron-at-wake behavior is undocumented.** The cache does not say
   whether a cron tick missed while the Mac slept fires on wake (launchd
   StartCalendarInterval coalesces missed events; pitchfork's 10s cron watcher
   presumably just misses them until the next matching wall-clock time). Needs
   an empirical probe on Ray's Mac before adoption.
2. **Ray's specific SSH agent.** The inventory says "SSH agent via launchd";
   whether it's the stock `com.openssh.ssh-agent` (SSH_AUTH_SOCK auto-injected
   into the launchd user domain) or a custom agent that only exports
   SSH_AUTH_SOCK to interactive shells must be verified locally — it decides
   whether R2 verification passes under any launchd-spawned venue without a
   `launchctl setenv` shim.
3. **Pitchfork release dates via WebFetch summaries.** The releases index page
   returned dates without years (one fetch mis-attributed 2024); I
   cross-verified v2.16.0 = 2026-07-09 via the tag page + repo sidebar, and the
   v1.0.0 = 2026-01-19 via the tags page, but individual mid-series dates
   (v2.9–v2.15) are approximate.
4. **api.github.com was 403 through the session proxy**, so star/issue counts
   come from HTML fetches (558★ as of 2026-07-09) rather than the API.
5. **Runner-venue mitigations not exhaustively explored** (org-level runner
   groups restricted to selected workflows, environments with required
   reviewers, JIT runners via `gh api`): all reduce but do not eliminate the
   public-repo risk, and each adds setup burden that pitchfork/launchd avoid
   entirely. If the repo ever goes private, this venue deserves re-evaluation —
   the workflow_run trigger is strictly better than any local polling design.
6. **Doppler CLI auth under launchd-spawned processes** (keychain access for
   `doppler` token) was not probed; applies equally to all local venues and is
   flagged for the angle-1 (launchd) evaluation.

## GitHub repos touched

- [jdx/pitchfork](https://github.com/jdx/pitchfork) — releases/tags/repo pages for maturity signals; docs read from the local mintlify cache.
- [actions/runner](https://github.com/actions/runner) — macOS LaunchAgent plist template (`actions.runner.plist.template`); issue #947 (service-account/logged-in constraints).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — verified repo visibility (Public badge); baseline inventory + rule files read from the working tree.
- [github/docs](https://docs.github.com) — self-hosted runner concepts/security/limits/service/workflow_run pages (docs.github.com, source repo github/docs).
- [docker/docs](https://docs.docker.com/desktop/settings-and-maintenance/settings/) — Docker Desktop start-at-sign-in setting (per-user GUI app).
- [onmyway133/blog](https://github.com/onmyway133/blog) — EC2 Mac runner LaunchAgent write-up corroborating the logged-in-session requirement (search result; not deeply read).
