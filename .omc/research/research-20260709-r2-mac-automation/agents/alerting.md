# Angle 4 — Failure alerting from unattended Mac jobs (Run F, r2-mac-automation)

Researched 2026-07-09 (remote session; Bash unavailable — evidence via WebSearch/WebFetch
+ repo file reads). Scope: reliable alert paths from an unattended launchd/cron/runner
job on Ray's macOS host after `mise run sync` / `mise run verify-local`, including the
dead-man-switch pattern for schedules the Mac sleeps through. Complements the sibling
report `agents/launchd-cron.md` §F6 (this is the deep dive it defers to).

## Findings

### F1. macOS-native notifications: osascript is fragile; terminal-notifier is decaying; `alerter` is the live option

- **osascript `display notification` silently drops from background contexts.** The
  notification is attributed to the *calling process* (TCC attribution chain): run from
  Terminal it needs Terminal's Notification permission; from launchd the responsible
  binary often never appears in System Settings → Notifications until it has delivered a
  notification — a chicken-and-egg where the command exits 0 but nothing shows. Documented
  in [gsd-build/gsd-2#2632](https://github.com/gsd-build/gsd-2/issues/2632) ("exits 0 …
  notification is silently dropped by macOS if the calling terminal app doesn't have
  notification permissions") and community threads
  ([latenightsw forum](https://forum.latenightsw.com/t/trying-to-use-terminal-for-display-notification/5068),
  [MacScripter](https://www.macscripter.net/t/trying-to-use-terminal-for-display-notification/76593)).
  Sequoia 15 additionally shipped general banner-display regressions
  ([Apple discussions](https://discussions.apple.com/thread/255766920)). Verdict:
  **never the alert path of record**; exit-0-on-drop violates the repo's evidence
  discipline (`.claude/rules/verify-before-advancing.md`) by design.
- **terminal-notifier is effectively unmaintained.** Last release 2.0.0; open report of
  total failure on M4 + Sequoia 15.3.1 ("nothing happens"),
  [julienXX/terminal-notifier#312](https://github.com/julienXX/terminal-notifier/issues/312)
  (opened 2025-02-23, no maintainer response as of this session; 44 open issues). The
  sibling report's F6 recommendation of terminal-notifier for local toasts should be
  downgraded on this evidence.
- **vjeantet/alerter is the maintained replacement** for a local toast: v26.x is a 2025/26
  Swift rewrite, **signed and notarized by Apple** (registers as its own app with its own
  Notification-Center permission entry — one one-time "Allow"), installed via
  `brew install vjeantet/tap/alerter`; supports `--message/--title/--json`, reply/action
  buttons. Sources: [vjeantet/alerter](https://github.com/vjeantet/alerter),
  [releases](https://github.com/vjeantet/alerter/releases).
- Positioning: a local toast is a **nicety only** — it is invisible when Ray is away from
  the Mac, which is precisely the unattended scenario. Optional layer, not the alert path.

### F2. ntfy.sh — the right primary push channel (phone-visible, zero-dependency, curl/HTTP)

- Publishing is a bare HTTP POST: `curl -d "Backup successful" ntfy.sh/mytopic`; rich
  alerts via headers `Title:`, `Priority:` (1–5, `urgent`=5), `Tags:` — e.g.
  `curl -H "Title: verify-local FAILED" -H "Priority: urgent" -H "Tags: warning" -d "rc=1; log: ~/.local/state/dotfiles/maintain.log" ntfy.sh/<topic>`.
  Source: [docs.ntfy.sh/publish](https://docs.ntfy.sh/publish/).
- **Topic = password** on the public server ("the topic is essentially a password, so pick
  something that's not easily guessable"; ≤64 chars, `[A-Za-z0-9_-]`). Access tokens exist
  for protected topics. Same source.
- iOS/Android apps receive via APNs/Firebase. Caveat that matters only if self-hosting:
  iOS instant delivery requires `upstream-base-url: "https://ntfy.sh"` forwarding poll
  requests to the APNs-connected upstream; without it delivery "can take hours".
  Sources: [ntfy config docs](https://docs.ntfy.sh/config/),
  [binwiederhier/ntfy#1377](https://github.com/binwiederhier/ntfy/issues/1377),
  [docs.ntfy.sh/known-issues](https://docs.ntfy.sh/known-issues/). **Use hosted ntfy.sh**
  → no caveat, no infra.
- **Pushover** is the paid equivalent: $4.99 one-time per platform, 10,000 messages/month
  free per API application (limit regime confirmed for 2026:
  [blog.pushover.net app-limits](https://blog.pushover.net/posts/2026/4/app-limits),
  [pushover.net/pricing](https://pushover.net/pricing)). Fine product, but ntfy's
  no-account/no-cost curl surface wins for a single personal alert stream.

### F3. healthchecks.io — the dead-man switch (the only class that catches "the job never ran")

Push channels (F1/F2) only fire when the job *runs and fails*. A `StartCalendarInterval`
job on a sleeping/powered-off Mac may be **skipped entirely** (sleep-missed schedules —
see sibling launchd report); nothing on the Mac can alert about a run that never started.
The dead-man pattern inverts control: the job pings an external service; **the service
alerts when the ping does NOT arrive on time**
([healthchecks.io docs](https://healthchecks.io/docs/): "It raises an alert as soon as a
ping does not arrive on time").

Pinging API ([healthchecks.io/docs/http_api](https://healthchecks.io/docs/http_api/)):

- success: `https://hc-ping.com/<uuid>`
- start (duration tracking): `https://hc-ping.com/<uuid>/start`
- explicit failure: `https://hc-ping.com/<uuid>/fail`
- **exit-status reporting**: `https://hc-ping.com/<uuid>/<exit-status>` — 0 = success,
  non-zero = failure. One URL pattern carries the job's real `rc`.
- log without status change: `https://hc-ping.com/<uuid>/log`
- POST body is stored (first **100 kB**) → attach the log tail to the ping itself.
- slug addressing + auto-provision: `https://hc-ping.com/<ping-key>/<slug>?create=1`
  creates the check on first ping — checks-as-code, no dashboard clicking.
- `rid=<uuid>` query param pairs start/finish of a specific run.

Semantics that fit this workload
([monitoring_cron_jobs](https://healthchecks.io/docs/monitoring_cron_jobs/),
[FAQ](https://healthchecks.io/faq/)):

- **Grace Time** = extra wait before alerting when a check is late; with `/start` signals
  it also bounds start→success ("If a job sends a 'start' signal but does not send a
  'success' signal within grace time, Healthchecks.io will assume failure") — this is a
  server-side watchdog on the multi-hour 38 GB pull, independent of the Mac.
- Recommended client flags: `curl -fsS -m 10 --retry 5 -o /dev/null <url>` (their own
  crontab example) — bounded, retrying, loud on error; matches
  `.claude/rules/long-running-command-hangs.md`.
- Pricing/hosting: free hosted tier = **20 checks**, 3-month log history; open source
  (BSD-3, Python/Django) and self-hostable
  ([pricing](https://healthchecks.io/pricing/), [self-hosted docs](https://healthchecks.io/docs/self_hosted/)).
  2–3 checks needed here → free tier is ample.

### F4. GitHub issue via gh CLI — best durable record, but has a real launchd trap

- **Why it belongs in the stack**: an issue in ray-manaloto/dotfiles is where Claude
  sessions already look (repo workflow is gh-centric; zero-skip-policy rule 4 already
  mandates `gh issue create` for deferred items — `.claude/rules/zero-skip-policy.md`).
  An alert that lands as an issue becomes actionable context for the next agent session.
- **The trap**: gh stores its OAuth token in the macOS Keychain by default ("secure
  storage", default since 2023 — [cli/cli#10108](https://github.com/cli/cli/issues/10108),
  [#13330](https://github.com/cli/cli/issues/13330)). In **non-TTY/background contexts**
  the Keychain lookup can fail (stale "ask before access" ACLs whose approval dialog
  can't render; a 3-second keyring timeout), and `gh api` then **silently sends
  unauthenticated requests** — surfacing only as 401/403 rate-limit errors
  ([cli/cli#13317](https://github.com/cli/cli/issues/13317), repro on gh 2.92.0,
  2026-04). A launchd job is exactly this context. Anthropic hit the same class of
  failure ([anthropics/claude-code#67087](https://github.com/anthropics/claude-code/issues/67087)).
- **Mitigations** (from #13317 + docs): resolve the token once and pass it explicitly —
  `GH_TOKEN="$(gh auth token)" gh issue create …` (in our python wrapper: read the token
  via one guarded subprocess call, then set `GH_TOKEN` in the child env), or source
  `GITHUB_TOKEN` from Doppler (already provisioned on the host:
  `.devcontainer/devcontainer.json:198` initializeCommand runs the doppler CLI on the
  Mac; smoke tier-2 lists `GITHUB_TOKEN` among Doppler canaries,
  `scripts/devcontainer-smoke.sh:91-104`). **Treat gh-under-launchd as untrusted until
  the token is explicitly resolved**; a failed `gh issue create` must not mask the
  primary ntfy alert (order: ntfy first, gh best-effort second).
- **Dedup pattern** (GitHub's documented scheduled-issue idiom): filter by a unique
  label before creating —
  `gh issue list --label mac-maintain-failure --state open --json number` → if present,
  `gh issue comment`; else `gh issue create --label mac-maintain-failure …`. Source:
  [GitHub Docs — Scheduling issue creation](https://docs.github.com/en/actions/use-cases-and-examples/project-management/scheduling-issue-creation)
  ("To avoid closing the wrong issue, use a unique label or combination of labels").

### F5. Email (msmtp) and Shortcuts — viable but dominated

- **msmtp**: supports the macOS Keychain natively (`security add-internet-password …`) and
  `passwordeval security find-generic-password -s msmtp-icloud -a <addr> -w`
  ([msmtp manual](https://marlam.de/msmtp/msmtp.html),
  [iCloud gist](https://gist.github.com/bradhowes/e4db684fa782f913d0454750bb103c72),
  [ArchWiki](https://wiki.archlinux.org/title/Msmtp)). But under launchd it inherits the
  **same Keychain-in-background friction class as gh** (F4), plus SMTP credentials to
  manage and no delivery guarantee visible to the sender. Dominated by ntfy (no secret
  beyond a topic string, push not pull) — keep as a non-recommended fallback.
- **Shortcuts**: `shortcuts run <name>` works from launchd
  ([Apple launchd guide](https://support.apple.com/guide/terminal/script-management-with-launchd-apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/mac),
  [scheduling write-up](https://medium.com/@richardmoult75/macos-shortcut-scheduling-using-launchctl-131b8b25567d)),
  and a Shortcut can post a notification. But it adds a GUI-app dependency, logic lives in
  the Shortcuts app (violates zero-bash-logic's spirit — logic must live in `python/`),
  and it has no failure semantics of its own. Not recommended.

### F6. Recommended combo + concrete design sketch

**Primary: ntfy.sh push (failure = urgent; success = optional min-priority).
Dead-man: healthchecks.io check per scheduled job, pinged with `/start` + `/<rc>` + log
tail. Durable record: best-effort deduped GitHub issue. Optional local toast: alerter.**

Rationale: ntfy reaches Ray's phone wherever he is; healthchecks is the only layer that
fires when the Mac slept through the schedule or the job wedged (server-side start→grace
watchdog); the gh issue puts the failure where Claude sessions operate; each layer fails
independently of the others.

Shape under repo conventions (zero-bash-logic; mise-tasks-only; bounded commands):

- **`python/src/dotfiles_setup/alert.py`** — new module modeled on `lint.py` (which
  already demonstrates the house style: module-docstring rationale, bounded
  subprocesses, process-group kill, rc preserved to file — `python/src/dotfiles_setup/lint.py:1-39`).
  Stdlib `urllib.request` with explicit timeout (~10 s) + small retry loop (mirror
  healthchecks' `-m 10 --retry 5` guidance); no curl, no pipes, exit codes never masked.
  Functions:
  - `hc_ping(check: str, kind: Literal["start","success","fail"] | int, body: bytes | None)`
    → POST `https://hc-ping.com/$HC_PING_KEY/<slug>[/start|/fail|/<rc>]?create=1&rid=<run-uuid>`,
    body = last ~64 kB of the run log (limit 100 kB, F3).
  - `ntfy_publish(title: str, message: str, priority: str, tags: str)` → POST
    `https://ntfy.sh/$NTFY_TOPIC` with Title/Priority/Tags headers.
  - `gh_issue_upsert(label: str, title: str, body: str)` → resolve `GH_TOKEN` explicitly
    (Doppler `GITHUB_TOKEN` or one `gh auth token` call), then list-by-label →
    comment-or-create (F4). Never allowed to raise past the ntfy step.
  - Alert-failure policy: if ntfy itself fails, still write the rc file and let the
    healthchecks miss fire — the dead-man layer is the backstop for the alerter too.
- **Config**: `HC_PING_KEY` / `NTFY_TOPIC` via `DotfilesConfig(BaseSettings)`
  (`python/AGENTS.md` — 16 env vars already centralized there), values from Doppler
  (host-side doppler CLI already authed) or `mise.local.toml` `[env]` (gitignored,
  per-clone — root `AGENTS.md`). Both are secrets-ish (topic is a password, F2): keep
  out of tracked files.
- **Wiring** into the maintenance job (whatever venue Run F picks): the orchestrator
  (`dotfiles-setup maintain`, exposed as `mise run maintain`) does
  `hc_ping(start)` → run `sync` → run `verify-local` (each bounded, rc→file per
  `long-running-command-hangs.md`) → `hc_ping(rc, body=log_tail)` → on rc≠0:
  `ntfy_publish(urgent)` + `gh_issue_upsert("mac-maintain-failure", …)`; on rc==0:
  optional `ntfy_publish(priority=min)` or just the HC success ping.
- **Checks & cadence** vs the nightly 02:00 America/Chicago publish
  (`ci.yml:10` cron; inventory report `research-20260709-r2-inventory/report.md:51-53`):
  two slug checks, `mac-sync` and `mac-verify-local` (or one `mac-maintain` composite),
  period 24 h, schedule the Mac job ~03:00 CT, **grace sized to the worst-case pull**
  (hours on a slow link — `verify-before-advancing.md` "slow base pull is acceptable"),
  e.g. 6–8 h grace on the composite check. 2 checks ≪ free-tier 20 (F3).
- **Alert content** honors evidence discipline: the `rc=` line, which gate failed
  (R1/R2/R3/persistence/base-currency), and the log file path — the same artifacts
  `verify-before-advancing.md` demands; the HC ping body carries the log tail itself.

## Uncertainties / gaps

- **healthchecks.io → ntfy/Pushover integration**: healthchecks.io lists many
  notification integrations and likely can deliver its "check is down" alert *via* ntfy
  or Pushover directly (which would unify both layers onto one phone channel). Not
  verified this session — confirm on
  <https://healthchecks.io/integrations/> before finalizing the design.
- **terminal-notifier on current macOS**: #312 is a single unresolved report (M4 +
  15.3.1); not independently reproduced. The safe conclusion is "unmaintained, prefer
  alerter", not "provably broken everywhere".
- **gh keyring failure frequency**: #13317 documents the silent-unauthenticated failure
  mode and non-TTY trigger conditions, but how often a *fresh* gh install on Ray's Mac
  hits the stale-ACL variant is unknown; the explicit-GH_TOKEN mitigation removes the
  question, so the design should just always use it.
- **ntfy.sh hosted-service rate limits** for free anonymous topics (requests/day) were
  not pulled this session; a nightly 1–3 message volume is far below any published
  limit, but check <https://docs.ntfy.sh/publish/#limitations> if success-pings are
  enabled.
- **Doppler token availability in the launchd context** (doppler CLI auth is
  keychain-backed too) is Run F's launchd angle to confirm; if it shares the F4 keychain
  class of problem, `mise.local.toml [env]` is the fallback for the two alert secrets.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding facts (lint.py house style, Doppler wiring, rules, ci.yml cron) read from the working tree.
- [julienXX/terminal-notifier](https://github.com/julienXX/terminal-notifier) — issue #312, Sequoia/M4 breakage + maintenance status.
- [vjeantet/alerter](https://github.com/vjeantet/alerter) — maintained, signed/notarized CLI notifier (Swift v26.x rewrite).
- [cli/cli](https://github.com/cli/cli) — issues #13317/#10108/#13330: keychain secure storage + silent unauthenticated requests in non-TTY contexts.
- [gsd-build/gsd-2](https://github.com/gsd-build/gsd-2) — issue #2632: osascript notification silently dropped without TCC permission (chicken-and-egg).
- [binwiederhier/ntfy](https://github.com/binwiederhier/ntfy) — publish docs, config (`upstream-base-url`), known-issues (iOS delivery), issue #1377.
- [healthchecks/healthchecks](https://github.com/healthchecks/healthchecks) — healthchecks.io docs (http_api, monitoring_cron_jobs, pricing, self-hosted); open-source project behind the hosted service.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issue #67087: gh keychain reads failing from background/non-interactive invocations (corroborating F4).
- [bradhowes gist](https://gist.github.com/bradhowes/e4db684fa782f913d0454750bb103c72) — msmtp + macOS Keychain passwordeval pattern (gist, listed for completeness).
