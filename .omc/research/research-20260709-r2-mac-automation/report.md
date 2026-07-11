# Run F — Automated macOS pull/verify + community trends sweep

Run: `research-20260709-r2-mac-automation` · Synthesized 2026-07-10 · Domain: after CI publishes a new `:dev` image, automate Ray's Mac-side `mise run sync` + `mise run verify-local`, alert on failure, plus a community-trends digest. Sources: five angle reports (launchd-cron, claude-scheduled, pitchfork-runner, alerting, community-sweep) under `.omc/research/research-20260709-r2-mac-automation/agents/`, adversarial verification of 10 load-bearing claims (3-vote each), and the grounding inventory at `.omc/research/research-20260709-r2-inventory/report.md`. The verification pass's final auto-synthesis step hit a usage-credit wall after completing all 10 verifications — the verdicts below are the real, completed output (only the report auto-write failed), reused here.

## Executive summary

**Recommended venue: a native macOS `gui/<uid>` **launchd LaunchAgent** with `StartCalendarInterval`, running a thin bash `exec` into a new `mise run maintain` task backed by a python module (`dotfiles_setup.maintain`, house-styled on `lint.py`).** This is the only venue that is simultaneously (a) zero new dependencies, (b) confirmed by three independent primary-source votes to catch up after sleep (cron cannot), and (c) has direct, verified prior art in this exact problem shape (`Homebrew/homebrew-autoupdate`). All three Claude Code scheduling surfaces are disqualified or contraindicated for this deterministic job (cloud routines literally cannot reach the Mac; Desktop-app surfaces add an LLM supervisor, cost, and availability coupling for zero benefit); a self-hosted GHA runner is mechanically viable but ruled out on security grounds because `ray-manaloto/dotfiles` is a **public** repo (GitHub's own hardening docs: self-hosted runners on public repos "almost never" recommended). **jdx/pitchfork is a credible secondary option** — it is launchd-booted itself, adds native cron + overlap control (`retrigger="finish"`) + mise wrapping + failure hooks — but it is young (v1.0.0 shipped 2026-01-19, still shipping "cron reliability fixes" in v2.15.0) and not yet pinned anywhere in the repo. Recommendation: **ship plain launchd now; revisit pitchfork via the `tool-currency-check` skill in a future cycle** once its cron path has more mileage, rather than betting a credential-bearing unattended job on a fast-moving young daemon today.

**Alerting: layer three independent channels**, none of which is skippable:

1. **ntfy.sh** (primary, phone-visible push) — `curl -H "Priority: urgent" -d "verify-local FAILED rc=1"` idiom, zero infra, zero account.
2. **healthchecks.io** (dead-man switch) — the *only* layer that fires when the job never ran at all (Mac asleep through the window, or wedged) — ping `/start` then `/<rc>`, grace time sized to the worst-case multi-hour pull.
3. **`gh issue create`/comment**, best-effort, deduped by label — durable record where Claude sessions already look, but only after explicitly resolving `GH_TOKEN` (launchd's non-TTY context breaks `gh`'s default keychain lookup silently).

An optional fourth layer — a local toast via `alerter` (not `terminal-notifier`, which is unmaintained and has a live report of total failure on current macOS) — is a nicety only, since it's invisible whenever Ray is away from the Mac, which is exactly the unattended scenario.

### Design sketch

```
Trigger:  ~/Library/LaunchAgents/com.raymanaloto.dotfiles.maintain.plist
          StartCalendarInterval Hour=6 Minute=30 (America/Chicago, ~4.5h after
          ci.yml's 02:00 nightly publish + its multi-stage build-publish
          pipeline)
          RunAtLoad=true (catches "Mac was off overnight"; see F1 below —
          gated by the staleness check so a redundant login-time fire no-ops
          in seconds instead of re-pulling)
          ProgramArguments: /bin/zsh -lc 'exec ~/dotfiles/scripts/maintain.sh'
          StandardOutPath / StandardErrorPath -> ~/Library/Logs/dotfiles-maintain/

Wrapper (thin bash, zero-bash-logic — logic lives in python):
  export PATH="$HOME/.local/share/mise/shims:$PATH"   # gui-domain LaunchAgents
                                                        # get ONLY /usr/bin:/bin:
                                                        # /usr/sbin:/sbin — CONFIRMED
  exec mise run maintain

mise run maintain -> dotfiles-setup maintain (python/src/dotfiles_setup/maintain.py,
  modeled on lint.py's bounded-subprocess + rc-to-file house style):
  1. hc_ping(start)
  2. staleness check: compare registry :dev digest vs local image digest;
     fast-exit 0 if unchanged (community norm is weekly/monthly rebuilds —
     this repo's NIGHTLY cadence makes digest-awareness load-bearing, see
     community F1)
  3. assert `docker context show` == desktop-linux; abort+alert on mismatch,
     NEVER switch (do-not.md item 8)
  4. Docker Desktop up? prefer `docker desktop start` (docs.docker.com/
     desktop/features/desktop-cli — the "open bug" cited in the original
     angle report, docker/cli#6837, was REFUTED by verification: it was
     transferred to docker/desktop-feedback#238 and closed 2026-07-08,
     with a fix in DD 4.70.0, current 4.81.0 as of 2026-07-06). Fall back
     to `open -a Docker --background` + bounded `docker info` poll (~120s)
     only if `docker desktop start` still misbehaves on Ray's actual
     installed version — verify locally with `docker desktop version`
     before finalizing which is primary.
  5. `mise run sync` under the repo's timeout wrapper (hours are fine —
     "slow pull is acceptable, never fall back to a stale base" per
     verify-before-advancing.md — but never blind; rc -> file)
  6. `mise run verify-local` under the same bound; rc -> file
  7. hc_ping(rc, body=last ~64kB of log)  # dead-man + result in one call
  8. rc != 0: ntfy_publish(priority=urgent) + gh_issue_upsert(
       label="mac-maintain-failure", GH_TOKEN resolved explicitly first)
     rc == 0: optional `alerter` local toast + ntfy_publish(priority=min)
              or just rely on the HC success ping

Manual parity: launchctl kickstart gui/$(id -u)/com.raymanaloto.dotfiles.maintain
```

Config (`HC_PING_KEY`, `NTFY_TOPIC`) via `DotfilesConfig(BaseSettings)` per `python/AGENTS.md`'s existing env-var centralization, sourced from `mise.local.toml [env]` (gitignored, per-clone) rather than Doppler — Doppler's own CLI auth is itself keychain-backed and untested under launchd's non-TTY context (flagged as an open uncertainty in the launchd angle report), so the alert secrets shouldn't inherit that same risk.

---

## PART 1 — Venue evaluation

### Q1. launchd LaunchAgent vs cron

**CONFIRMED (3/3 votes each, two independent claims):** a user LaunchAgent with `StartCalendarInterval` is the only native macOS scheduler that catches up after sleep — missed firings coalesce into **exactly one** run on wake — while cron silently skips a sleep-missed run entirely. Apple's own docs state it verbatim: *"If you schedule a launchd job... and the computer is asleep when the job should have run, your job will run when the computer wakes up... If multiple intervals transpire before the computer is woken, those events will be coalesced into one event upon wake from sleep"* vs cron: *"If the system is turned off or asleep, cron jobs do not execute; they will not run until the next designated time occurs."* (developer.apple.com/library/archive/.../ScheduledJobs.html; corroborated by the shipping `launchd.plist(5)` man page). **Scope caveat surfaced during verification**: the catch-up applies to *sleep* only — a powered-off Mac still misses the window entirely for either scheduler; this is why the design sketch also uses `RunAtLoad=true` gated by a staleness check, not `StartCalendarInterval` alone.

**CONFIRMED:** cron is officially deprecated on macOS in favor of launchd (*"Although it is still supported, cron is not a recommended solution. It has been deprecated in favor of launchd"*) and picks up Full-Disk-Access/TCC friction on protected paths — though verification correctly notes this job's file surface is not TCC-protected, so TCC isn't the deciding factor here; the sleep/wake semantics are.

**CONFIRMED:** a `gui/<uid>` LaunchAgent inherits `SSH_AUTH_SOCK` (macOS's stock `com.openssh.ssh-agent` is itself a launchd socket exposed in the gui domain's inherited environment) and runs with the login keychain unlocked, but gets only the bare default PATH `/usr/bin:/bin:/usr/sbin:/sbin` — no Homebrew, no mise shims. Verified via `launchctl print gui/$(id -u)` transcripts plus the repo's own mintlify cache confirming mise's shims-for-non-interactive guidance (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:16,2543`). This is why the wrapper explicitly prepends the mise shims dir to PATH.

**CONFIRMED:** `Homebrew/homebrew-autoupdate` is direct, current prior art for exactly this job shape — a per-user LaunchAgent with `StartInterval`, `StandardOutPath`/`StandardErrorPath` logs, `ProcessType=Background`, `LowPriorityIO`, loaded via `launchctl load`, with a `--notify-on-error` flag. One recency nuance: the tap's canonical home moved from the Homebrew org back to `DomT4` in late 2023/Homebrew 4.3.0 — the URL still redirects to the live repo, so the citation holds, just note the org attribution is stale.

### Q2. Claude Code scheduling surfaces (cloud routines / Desktop scheduled tasks / `/loop`)

**CONFIRMED:** cloud routines definitively **cannot** touch the Mac. They execute on Anthropic-managed cloud infrastructure against a fresh clone (*"Access to local files: No (fresh clone)"* — code.claude.com/docs/en/scheduled-tasks.md; *"Routines execute on Anthropic-managed cloud infrastructure"*). This is a hard disqualifier, not a design tradeoff.

Desktop scheduled tasks (the local, GUI-app-dependent surface) mechanically *can* run `mise run sync && mise run verify-local` — they inherit the Mac's GUI login session — but every firing pays for a fresh LLM session to re-derive "run these two mise tasks," is gated on "the Desktop app was open and the Mac awake," and an Ask-mode permission stall can wedge the run unattended with nobody to approve it. **The right integration point for Claude is the failure boundary, not the schedule**: `channels` (v2.1.80+) can push CI/verify-local events into a standing local session, or the launchd failure handler can fire a one-shot `claude -p "read the verify-local log, diagnose, file a gh issue"` — Claude spends tokens only on red nights.

### Q3. jdx/pitchfork

Well-sourced from the local mintlify cache and cross-checked against live releases. Pitchfork has **native 6-field cron scheduling** with a documented `retrigger` mode — the doc's own headline example is `cron = { schedule = "0 0 2 * * *", retrigger = "finish" }` — and `retrigger = "finish"` gives free overlap control for the multi-hour buildkit pull. `mise = true` wraps daemon commands in `mise x --`, satisfying `mise-tasks-only.md`. `pitchfork boot enable` installs its own `~/Library/LaunchAgents/dev.jdx.pitchfork.plist`, so **pitchfork is launchd underneath**. `on_fail` lifecycle hooks receive `PITCHFORK_EXIT_CODE`/`PITCHFORK_EXIT_REASON` and slot an ntfy/gh-issue call directly. Gaps: **no per-run wall-clock timeout** (same as plain launchd — the bound must live in the python wrapper regardless of venue), and it is young: `v1.0.0` on 2026-01-19, `v2.16.0` on 2026-07-09, with `v2.15.0` still shipping "cron reliability fixes." Same trusted author as mise/hk, which lowers the adoption-risk bar somewhat, but the maturity signal argues for waiting.

### Q4. Self-hosted GHA runner

**Mechanically viable, security-inappropriate — ruled out.** Everything works: `./svc.sh install` installs a user-domain LaunchAgent, it reaches Docker Desktop and the launchd SSH agent, `workflow_run: completed` gives a free event-driven trigger off `ci.yml`'s nightly publish, native `timeout-minutes` covers the multi-hour pull, Actions UI failure notifications are free. But `ray-manaloto/dotfiles` is confirmed **Public**, and GitHub's own hardening docs are explicit: self-hosted runners *"should almost never be used for public repositories"* because any fork-PR can compromise the runner environment. On Ray's personal Mac the blast radius is maximal — Doppler auth, the SSH agent, the Docker socket, the whole home directory. **If the repo ever goes private, re-evaluate** — the `workflow_run` trigger is strictly better than any local polling design.

### Q5. Failure alerting

- **osascript `display notification` is disqualified.** It exits 0 while silently dropping the notification when the calling process lacks a Notification-permission entry — a chicken-and-egg that never resolves for a background launchd process (`gsd-build/gsd-2#2632`). This violates the repo's evidence-discipline rule by construction: a false-green exit code is exactly what `verify-before-advancing.md` forbids trusting.
- **ntfy.sh is the primary push channel**: zero dependency, phone-visible (note: the exact `||`-chained failure example lives on `docs.ntfy.sh/examples/`, a citation-location correction).
- **healthchecks.io is the dead-man switch, and is not optional.** Push channels only fire when the job *runs and fails*; nothing on the Mac can alert about a run that never started because the Mac was asleep. healthchecks.io inverts control — the job pings, the *service* alerts on a missing ping. Free tier (20 checks) covers it.
- **`gh issue create`, deduped by label, is the durable record** — but under launchd (non-TTY), `gh`'s default keychain-backed OAuth can silently fall back to unauthenticated (`cli/cli#13317`). Mitigation: resolve `GH_TOKEN` explicitly once and pass it into the child environment.
- **Local toast**: prefer `vjeantet/alerter` (maintained, signed) over `terminal-notifier` (unmaintained; open failure report on M4 + Sequoia, `julienXX/terminal-notifier#312`). **Not** one of the 10 adversarially re-verified claims — treat as well-sourced but unconfirmed.

---

## PART 2 — Community trends digest

1. **Devcontainer prebuild republish is mainstream, but weekly/monthly, not nightly** — a GH code search for `devcontainers/ci` + `cron` returns 224 files; examples all weekly (`freqtrade`, `ladybird`, `serenity`, `flood`, `webstatus.dev`) or monthly (`oracle-enhanced`). *Why it matters*: this repo's **nightly** 02:00 CT republish (`ci.yml:10`) is more aggressive than the field — which is exactly why the Mac-side consumer must be strictly digest-aware.
2. **The canonical GHA prebuild recipe's main pain point is arm64 emulation time** — `devcontainers/ci@v0.3` + buildx + QEMU "about an hour" for a simple image. *Why it matters*: validates this repo's amd64-only + CI-only-base-build decisions.
3. **Codespaces prebuilds bill per core-hour + per-GB-month storage even when idle** ([GitHub Docs](https://docs.github.com/en/codespaces/prebuilding-your-codespaces/about-github-codespaces-prebuilds)). *Why it matters*: for a ~38GB image, prebuild storage would be prohibitive — the GHCR-publish + local-pull architecture this repo uses is the economically sane variant.
4. **mise's 2025-2026 community momentum is broad and strong** — HN front-page hits, and a 2026 comparison calls it *"the closest thing to an obvious default in the polyglot version-manager space"* ([PkgPulse 2026](https://www.pkgpulse.com/guides/mise-vs-proto-vs-asdf-polyglot-version-managers-2026)). *Why it matters*: the mise-tasks-only convention rides the community direction.
5. **Supply-chain security (cosign/SLSA via mise's aqua/ubi backends) is now the headline mise-vs-asdf differentiator, with corporate adoption** — Kong ([Kong/jdx-mise-action](https://github.com/Kong/jdx-mise-action)) and StepSecurity ([step-security/mise-action](https://github.com/step-security/mise-action)) ship mirrors/forks. *Why it matters*: mise-in-CI has passed early-adopter stage; the repo's exact-pin + `mise.lock` posture matches the trajectory.
6. **`jdx/renovate-config` (the preset this repo extends) is niche** — 22 code-search hits, nearly all `jdx/*` plus this repo. *Why it matters*: well-aligned today but watch for preset-driven behavior changes since it tracks one maintainer's needs; `jdx/aube` is worth a future mintlify-catalog queue entry.
7. **The mature reference design for self-updating repos is exactly what `refresh.yml` already does** — mirroring `DeterminateSystems/update-flake-lock`. *Why it matters*: no CI-side redesign needed — the gap the pattern doesn't cover is the host-side consumer (Part 1's whole question).
8. **Unattended host-side refresh in the dotfiles world converges on "status-gate → act → alert"** — chezmoi's own FAQ: *"call `chezmoi status` and only `apply` if..."* ([discussion #3513](https://github.com/twpayne/chezmoi/discussions/3513)). *Why it matters*: the same shape as the design sketch, independently converged-on.
9. **Renovate-on-dotfiles with native managers is now normal practice** ([Renovate docs](https://docs.renovatebot.com/)). *Why it matters*: confirms PR #161's native-managers-over-customManagers direction is the community default.
10. **The best longitudinal dataset on agentic maintenance: mechanical tasks succeed, judgment tasks don't, prep beats model quality** — Microsoft's 10-month `dotnet/runtime` writeup: 878 agent PRs, 67.9% merged, success jumped 38%→69% after investing in build/test instructions ([devblogs, 2026-03-23](https://devblogs.microsoft.com/dotnet/ten-months-with-cca-in-dotnet-runtime/)). *Why it matters*: validates the AGENTS.md investment; realistic agentic scope for the Mac job is mechanical follow-up, not autonomous R1/R2/R3 remediation.
11. **Headless "CI babysitter" agents are productized, but GitHub's human-approval gate keeps them supervised** — `anthropics/claude-code-action` v1 on CI-failure, but a human must "Approve and run workflows" per agent push. *Why it matters*: an agentic triage layer belongs on the CI side, human-supervised.
12. **Counter-trend: the AI-slop backlash pushes maintainer norms toward throttles + narrow write-scopes** — curl ended its bug bounty (Jan 2026, ~20% AI-slop); Jazzband shut down citing AI-spam ([RedMonk, 2026-02-03](https://redmonk.com/kholterhoff/2026/02/03/ai-slopageddon-and-the-oss-maintainers/)). *Why it matters*: keep agentic automation self-repo-scoped, evidence-attached, merge-gated.
13. **Docker Bake is GA (Feb 2025) and is the community-standard multi-image fan-out mechanism** ([Depot deep-dive](https://depot.dev/blog/buildx-bake-deep-dive)). *Why it matters*: if a future base/runtime two-image topology is forked, bake's target inheritance is the incremental path.

---

## Refuted / unverified claims

1. **REFUTED — "docker/cli#6837 is an open reliability bug in `docker desktop start`."** Stale: transferred to `docker/desktop-feedback#238` and **closed 2026-07-08**; fix in DD 4.70.0, current 4.81.0. **Correction applied above**: prefer first-party `docker desktop start`, fall back only if a local probe shows the fix hasn't reached Ray's install.
2. **REFUTED — "Dispatch is human-initiated / not schedulable."** The Remote-Control half holds (outbound-polling only), but Dispatch's own docs say scheduled tasks exist — they're just **local** (Desktop app open, Mac awake). Cite "no cloud surface can reach or wake an idle Mac," not "Dispatch cannot be scheduled."
3. **REFUTED — the blanket "Claude routines cannot execute locally at all."** False: Desktop scheduled tasks and `/loop` run **on your machine**. Doesn't undermine the recommendation — Q2 already treats Desktop tasks as working-but-inferior; the refutation only matters if the over-broad phrasing were reused.
4. **Unverified (not in the 10-claim sample) — "`terminal-notifier` is broken; prefer `alerter`."** Well-sourced but not independently re-verified; local `brew install vjeantet/tap/alerter` sanity check before finalizing.
5. **Unverified — the exact ntfy.sh citation location** (`/examples/` not `/publish/`). Substance unaffected.

---

## Open questions for Ray

1. **Venue: ship plain launchd now, or adopt pitchfork immediately?** *(Recommended: plain launchd now — zero new dependency for a credential-bearing job; revisit pitchfork via `tool-currency-check` once its cron path has more field mileage.)*
2. **Cadence: is 06:30 local (~4.5h after the 02:00 CT publish) the right buffer given the full pipeline can run long?** *(Recommended: 06:30 as a start, widen if the staleness check regularly finds the pipeline still mid-flight.)*
3. **Docker Desktop auto-start (`docker desktop start`, now believed fixed) vs skip-with-alert?** *(Recommended: auto-start; skip-with-alert only if a local probe shows the fix hasn't landed on Ray's version.)*
4. **Alert secrets: `mise.local.toml [env]` vs Doppler?** *(Recommended: `mise.local.toml [env]` — avoids stacking Doppler's keychain-under-launchd uncertainty onto the alert path.)*
5. **`gh issue create` alerting: keep it (with explicit `GH_TOKEN`) or rely on ntfy + healthchecks only?** *(Recommended: keep it, best-effort/non-blocking, after the primary ntfy alert.)*
6. **Local toast `alerter`: worth a 5-minute local sanity install before committing?** *(Recommended: yes.)*
7. **Given the repo is public today, is a future move to private on the table — which would reopen the self-hosted-GHA-runner venue?** *(No recommendation — scope question for Ray; Q4's ruling depends entirely on repo visibility.)*

---

## GitHub repos touched

- [Homebrew/homebrew-autoupdate](https://github.com/Homebrew/homebrew-autoupdate) — prior-art LaunchAgent plist keys, scheduling/notification behavior.
- [docker/cli](https://github.com/docker/cli) — issue #6837, `docker desktop start` failure; verification found it stale (transferred, closed).
- [docker/desktop-feedback](https://github.com/docker/desktop-feedback) — issue #238, the closed successor to docker/cli#6837.
- [docker/for-mac](https://github.com/docker/for-mac) — issue #6504, headless Docker Desktop limitations on macOS.
- [binwiederhier/ntfy](https://github.com/binwiederhier/ntfy) — docs.ntfy.sh publish/examples (curl POST alert idiom).
- [gsd-build/gsd-2](https://github.com/gsd-build/gsd-2) — issue #2632, osascript notification silently dropped without TCC permission.
- [jdx/mise](https://github.com/jdx/mise) — shims for non-interactive environments; community-momentum discussions.
- [jdx/mise-action](https://github.com/jdx/mise-action) — CI action inputs/caching.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — preset extender census.
- [jdx/aube](https://github.com/jdx/aube) — new jdx project spotted in preset census, unresearched.
- [jdx/pitchfork](https://github.com/jdx/pitchfork) — maturity signals; scheduling/mise-integration/lifecycle-hooks docs via local mintlify cache.
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — upgrade-automation examples; discussion #3513 (cron guard pattern).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding inventory, rules, verified repo visibility (Public).
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — code.claude.com docs (routines, scheduled-tasks, remote-control, channels); issue #67087 (gh keychain failure under background invocation).
- [anthropics/claude-code-action](https://github.com/anthropics/claude-code-action) — headless agentic CI automation mode.
- [actions/runner](https://github.com/actions/runner) — macOS LaunchAgent plist template; issue #947.
- [github/docs](https://docs.github.com) — self-hosted runner concepts/security/limits/workflow_run docs.
- [julienXX/terminal-notifier](https://github.com/julienXX/terminal-notifier) — issue #312, Sequoia/M4 breakage report.
- [vjeantet/alerter](https://github.com/vjeantet/alerter) — maintained local-toast alternative.
- [cli/cli](https://github.com/cli/cli) — issues #13317/#10108/#13330, gh keychain + silent unauthenticated fallback in non-TTY.
- [healthchecks/healthchecks](https://github.com/healthchecks/healthchecks) — dead-man-switch service docs.
- [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade), [LadybirdBrowser/ladybird](https://github.com/LadybirdBrowser/ladybird), [SerenityOS/serenity](https://github.com/SerenityOS/serenity), [jesec/flood](https://github.com/jesec/flood), [GoogleChrome/webstatus.dev](https://github.com/GoogleChrome/webstatus.dev), [rsim/oracle-enhanced](https://github.com/rsim/oracle-enhanced) — devcontainer prebuild cadence evidence.
- [devcontainers/ci](https://github.com/devcontainers/ci), [devcontainers/cli](https://github.com/devcontainers/cli) — prebuild action + `--prebuild` docs.
- [Kong/jdx-mise-action](https://github.com/Kong/jdx-mise-action), [step-security/mise-action](https://github.com/step-security/mise-action) — corporate adoption signals.
- [DeterminateSystems/update-flake-lock](https://github.com/DeterminateSystems/update-flake-lock) — reference self-updating-repo action mirroring `refresh.yml`.
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — automerge guidance, native managers.