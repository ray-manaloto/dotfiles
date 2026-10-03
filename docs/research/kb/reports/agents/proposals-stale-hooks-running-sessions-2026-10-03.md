# Proposals — stale hooks in running sessions (2026-10-03)

Read-only review (no source edited, no /reload-plugins run, no session touched). Report written incrementally.

## Evidence log (incremental)

- E1 `.claude/skills/session-start/hooks/register.ts:221-224` — on `session.start` (interactive) the mod already queues
  `/reload-skills` then `/reload-plugins --force` via `$.command.run` when python's decide says `reload: true` (once per session id).
- E2 live arms report arm A (`docs/research/kb/reports/agents/live-arms-coordinator-auto-handoff-2026-10-02.md`): a module-queued
  `/reload-plugins --force` really ran ("Prompt from the session-start plugin", `Reloaded: 17 plugins · 87 skills · 33 agents · 15 hooks`)
  => a hooks module CAN trigger a reload of itself (positive arm measured on 2.1.288).
- E3 coordinator-handoff mod heartbeat strings: `handoff N%/30%`, `handoff fired @N%`, `handoff n/a (not coordinator)`, `handoff ERROR:` (register.ts header + belowStatus).
- E4 `$CC/plugins-reference.md:407` + `$CC/skills.md:253-255`: skill dirs are watched, but live change detection covers `SKILL.md` text ONLY;
  a skills-dir plugin's `hooks/` changes need `/reload-plugins` or restart. => NO native hot-reload for our function-hook modules on file change.
- E5 `$CC/commands.md:122`: `/reload-plugins [--force]` warns+skips only "when the reload would change which MCP tools are loaded and invalidate
  the prompt cache"; `--force` applies anyway. `$CC/prompt-caching.md:124-126`: "Claude Code never invalidates the cache for a plugin's skills,
  commands, agents, hooks, monitors, or themes" (appended after the conversation). `:128-133`: only MCP-providing plugins whose tools load into the
  prefix force a full re-read. `$CC/plugins-reference.md:197`: reload keeps live connections of MCP servers whose config is unchanged.
- E6 `$CC/settings.md:584`: settings files (incl. `hooks` in `.claude/settings.json`) ARE watched and hot-reloaded => command hooks in settings.json
  are NOT subject to this staleness; only `@skills-dir` function-hook plugins (and monitors: restart only, `plugins-reference.md:736`) are.
- E7 d.ts (2.1.277 vendored) `.claude/types/claude-code.d.ts:3541-3546`: `session.start` re-fires on "a reload (changed modules only ...)";
  `:2854-2855` store survives hot reloads; `:2889-2891` a hot reload cancels pending clock waits; `:2020-2028` `$.plugin.root` = the plugin's absolute dir;
  `:2738+` `$.fs.read`; `:2893+` `$.clock.every`; `:2629-2639` `$.command.run` "as if the person typed", queued until idle, rejects "inside a hook the
  turn is waiting on". No file-watch noun for modules (control: grep `watch` in d.ts hits only SessionStart `watchPaths` output fields, 1009-1011).
- E8 Native file watch exists for COMMAND hooks: `FileChanged` event + `watchPaths` (`$CC/hooks.md:60,1192,2859-2934`), but "no decision control",
  output only `watchPaths`/`systemMessage` (a terminal notification). It cannot run a slash command or reload.
- E9 Live CHANGELOG (fetched 2026-10-03, top = 2.1.288, saved `.agent/kb/raw/cc-changelog-2.1.288.md`): no entry adds hot-reload of hooks modules
  or skills-dir plugin hooks on file change. Relevant: 2.1.0 skills hot-reload; 2.1.69 `/reload-plugins`; 2.1.229 marketplace `command` sources
  "re-resolved each session and applied without a restart"; 2.1.268 `/plugin` menu auto-reload; 2.1.288 "Fixed background sessions ending when a
  plugin was reloaded or disabled while one of its timers or reads was still running" (=> reloads in bg sessions were unsafe before 2.1.288).
- E10 Tree-hash probe discriminates: `git rev-parse <rev>:.claude/skills/coordinator-handoff` = `f57ba294` at HEAD, origin/main and 4e2c9395;
  at `4e2c9395^` => `fatal: Needed a single revision` (absent pre-merge). Last origin/main commit touching `.claude/skills` = 4e2c9395 (#1583).
- E11 Main checkout is BEHIND origin/main right now (HEAD 4cf89eb8 vs origin/main 3bb0b54a); only `land` fast-forwards it
  (`python/src/dotfiles_setup/pr.py:1047-1052`, `git checkout main` + `pull --ff-only` in the workspace it runs in). `.claude/skills` diff between
  the two is empty, so no current skew — but a `/reload-plugins` reloads whatever is ON DISK at `$.plugin.root`, so a reload cannot fix a stale
  main checkout.
- E12 Heartbeat-state cross-check over `~/.claude/jobs/*/state.json` (name contains "coordinator") vs `<main>/.agent/state/coordinator-handoff/<sid>.json`:
  pre-merge coordinator `98eb9783` (created 2026-10-02T17:56Z, cli 2.1.287) => no-state; every post-merge coordinator (30d222ef, a8d7baf5, 2dffefaf,
  a2ccbbc5, 27e2bf5c, 28f1a8f7, 97ffeddb, 125da665) => STATE. Known-broken positive: `5990b71c` (live-arm B, bogus UV_PYTHON) => no-state.
  False-positive traps: lane `79921362` (`…coordinator-auto-handoff`, not the coordinator role) => no-state by design; `7541ae79` created
  2026-10-02T21:33Z (PRE-merge) yet has STATE (it acquired the hook later) => job `createdAt` alone is NOT a staleness signal.
- E13 Upstream issues (gh search/issues; fresh control `zzqvplkx7731 reload` => 0 while `reload-plugins` => 468):
  #24057 (open, auto-reload hooks/plugins on change — not shipped), #84320 (open: queued input runs BEFORE an earlier-queued `/reload-plugins`,
  turn runs on stale plugin state), #90135 (open: re-materialized marketplace plugin silently kills pinned hooks; "undetectable from inside the plugin"),
  #93657 (open: auto-apply reload when no user turns yet), #95924 (open: reload in a coordinator thread).

## Is any of this moot? (native hot-reload)

No. Three layers can be stale, and native covers none of the one that bit us:

| Layer | Stale when | Native refresh? |
|---|---|---|
| L1 remote | `origin/main` moved after the PR merged | `git fetch` (any worktree; refs are shared) |
| L2 disk | the plugin root (`$.plugin.root`, i.e. the main checkout's `.claude/skills/<p>`) is behind `origin/main` | only `mise run land` (`pr.py:1047-1052`) — E11 |
| L3 memory | the loaded module differs from the bytes on disk | **none for `@skills-dir` hooks** — `/reload-plugins` or restart (E4) |

Native hot-reload exists for SKILL.md text (E4), settings-file command hooks (E6), `--plugin-dir` folder add/remove (`$CC/plugins.md:320-322`),
and marketplace `command`-source plugins (`$CC/plugin-marketplaces.md:655-661`, auto-reload in interactive sessions unless the cache would be
invalidated). None of those reload a changed `hooks/register.ts` in a skills-dir plugin; the live changelog through 2.1.288 adds nothing that does
(E9), and #24057 asking for exactly that is still open (E13). Negative-claim control: the same changelog grep DOES find the skills hot-reload (2.1.0)
and settings hot-reload (2.1.139/140) entries, so the probe can see such features when they exist.

Partial mootness: if the trigger lived in `.claude/settings.json` as a command hook it would hot-reload (E6) — but command hooks have no
`session.measure`/context-percent event, so the coordinator trigger cannot move there.

## (1) Detection — how a running session knows its hooks are older than main

**1A (recommended): load-stamp + periodic compare, owned by python, called from the existing session-start mod.**
At module load (`session.start`, which also re-fires on a reload of a changed module — E7 `d.ts:3541-3546`), ask python for a stamp
`{plugin_root, tree: git rev-parse HEAD:.claude/skills, dirty: git status --porcelain -- .claude/skills}`; keep it in module memory (which a reload
resets — exactly the semantics wanted). On `session.measure`, rate-limited with `$.clock.now()` (e.g. every 10 min), ask python
`plugin-currency --loaded-tree <t>` to compare three things with no network: loaded tree vs disk tree (L3), disk tree vs `origin/main:.claude/skills` (L2),
and report which plugin dirs differ. Write the result to `<main>/.agent/state/plugin-currency/<sid>.json` and the status line (`hooks current` /
`hooks STALE: reload` / `hooks STALE: main checkout behind`).
- PRO: exact (tree hashes, E10 discriminates present/absent); offline; reuses the module→python pattern; a reload re-stamps automatically; the state file
  makes it externally checkable.
- CON: bootstrapping — only sessions that already LOAD this code are covered; it cannot rescue a session older than it (the #1583 case). Origin ref
  freshness depends on someone fetching (ship/land/lanes do constantly). Adds one subprocess per interval.
- Arms: (+) start a `--bg` probe session, commit a whitespace change to a scratch branch's `.claude/skills/session-start/hooks/register.ts` in a
  throwaway worktree used as primary dir => status flips to STALE within one interval; (-) unchanged tree => stays `current`; (bound) dirty tree
  counts as stale, not current.

**1B: hook-embedded version constant** (each `register.ts` carries `const MOD_VERSION`, compared with python's view of the file).
- PRO: no git dependency. CON: hand-maintained, drifts (rule `machine-check-not-hand-fix`); a forgotten bump certifies stale code. Not recommended.

**1C: heartbeat absence (already exists, partial).** `coordinator-handoff` writes `<main>/.agent/state/coordinator-handoff/<sid>.json` on its first
measurement (E12). Absence after the first turn = the hook is not loaded at all.
- PRO: zero new code; discriminates the exact #1583 failure (E12: 98eb9783 no-state vs all post-merge coordinators STATE).
- CON: detects "missing", not "older version"; the module skips python below the limit once role is known (`register.ts` measure(): "Once the role is
  known, below the limit needs no process"), so `last_seen.at` is not a liveness clock. Use it for Q4, not as the general detector.

**Native options:** none found — no module file-watch noun (E7), `FileChanged` command hooks can watch absolute paths (E8) but have no way to reload or
inject; at most a `systemMessage` notification. Usable only as a cheap human-visible nudge.

## (2) Remedy — auto reload vs watcher alert vs restart

Fact first: **a module CAN trigger a reload of itself** — `$.command.run({command:"reload-plugins", args:"--force"})` is already shipped in
session-start (E1) and was observed working live (E2). Constraints: `command.run` queues until idle and rejects inside a hook the turn is waiting on
(`d.ts:2629-2639`) — so `void` it as both mods do; a reload cancels the module's pending clock waits (`d.ts:2889-2891`); background sessions could END
on a reload with in-flight timers/reads before 2.1.288 (E9) — require `cliVersion >= 2.1.288`; queued user/inbox input can jump ahead of a queued
reload (#84320), so the turn after the trigger may still be stale — the next measure re-checks, which is self-correcting.

**2A (recommended): tiered, from the 1A result.**
- L3 only (disk newer than memory): the session-start mod queues `/reload-plugins` (no `--force`) once per new disk tree; if the returned text says it
  was held (MCP/prefix change), show `hooks STALE: run /reload-plugins --force` and toast — do not force mid-conversation automatically.
  Exception: a session with zero user turns forces (cache cost is nil there — the reasoning of #93657).
- L2 (disk behind origin/main): never auto-pull the main checkout from a hook (it may be on a branch/dirty; mutation belongs to `land`). Status
  `hooks STALE: main checkout behind origin/main` + a state file for the watcher.
- Coordinator role and stale for > N min: since for a coordinator "restart" == handoff, auto-submit `/coordinator-handoff` early (a fresh `--bg` successor
  loads current plugins). That reuses the shipped, armed path instead of inventing a restart.
- PRO: hooks-only reloads never invalidate the cache (E5, `prompt-caching.md:124-126`); no human step; reuses existing mechanisms.
- CON: bootstrapping as in 1A; one more automated slash command in the transcript; #84320 ordering race.
- Arms: (+) bg probe with an edited mod on disk => transcript shows the plugin-originated `/reload-plugins` and the new mod's status string;
  (-) unchanged disk => no reload queued (count `<command-name>/reload-plugins` = 0 after N turns); (held) a probe with a pending MCP change =>
  no forced reload, STALE status shown.

**2B: watcher alert only.** PRO: no new in-session automation. CON: needs a human; the watcher is itself a long-lived session subject to the same staleness.

**2C: unconditional periodic `/reload-plugins --force`.** CON: risks full re-reads for any active MCP-providing plugin (E5 `:128-133`) and module
memory loss every interval for nothing. Reject.

## (3) Cost and risk of `--force`

- Prompt cache: hooks/skills/agents/commands/monitors/themes never invalidate it; they are appended (`$CC/prompt-caching.md:124-126`). The ONLY full
  re-read is a reload that changes which MCP tools load into the prefix (`$CC/commands.md:122`, `$CC/prompt-caching.md:128-133,145`). `--force`
  just means "accept that re-read". For our MCP-free skills-dir plugins, plain `/reload-plugins` suffices; `--force` buys nothing and risks a
  full re-read if some other plugin has a pending MCP change.
- MCP: servers with unchanged config keep live connections (`$CC/plugins-reference.md:197`); changed ones reconnect; in non-interactive sessions plugin
  MCP changes wait for the next session (`$CC/discover-plugins.md:415+`).
- Module memory: wiped for reloaded (changed) modules — `session.start` re-fires for them (d.ts:3541-3546); `$.store` survives (2854-2855); clock waits
  cancelled (2889-2891). Both mods already keep authoritative state in python for this reason (spec E8, `register.ts` session-start header).
- Monitors need a restart regardless (`$CC/plugins-reference.md:736`); bg-session reload crash fixed only in 2.1.288 (E9).
- Recommendation: change session-start's own `reload-plugins --force` to `--force` only when the session has no user turns yet (it runs at
  session.start, so that already holds today — keep it), and use non-force for the mid-session trigger in 2A.

## (4) Should the watcher verify every coordinator's heartbeat and relaunch?

Yes for VERIFY, guarded for RELAUNCH. The status line is UI-only, but the heartbeat already has a durable shadow: the per-session state file (E12).
Proposed check (python, a `mise run` task the watcher calls; read-only):
for each live job in `~/.claude/jobs/*/state.json` (`state` working/idle), whose role python's own `coordinator_handoff` role predicate says is
coordinator (NOT a name substring — E12 lane `79921362` trap), and older than one turn: require `<main>/.agent/state/coordinator-handoff/<sid>.json`
AND (once 1A ships) `<main>/.agent/state/plugin-currency/<sid>.json` with `stale=false` and a recent `at`.
- Missing => alert (toast/issue comment) first. Relaunch only through `/coordinator-handoff`'s own launcher with `claude stop` of the old session,
  and only with Ray's standing approval: stopping a coordinator is irreversible-ish and `claude stop` does NOT kill its background tasks (live arm D),
  so a relaunch can orphan heavy runs — the census in the handoff skill exists for this.
- Do not use `createdAt < last .claude/skills merge` alone: E12 `7541ae79` was created pre-merge yet armed later (false positive).
- PRO: catches the exact #1583 failure with existing artifacts; covers sessions too old for 1A. CON: the watcher must itself be current (apply 1A to it);
  file-based heartbeat proves "ran once since load", not "running now".
- Arms: (+) a `--bg` probe with `UV_PYTHON=/nonexistent/python3` (live-arm B recipe) => flagged; (-) a healthy successor => not flagged;
  (role) a lane named `*.coordinator-auto-handoff` => not flagged.

## Recommended package (order)

1. Q4 watcher check now (cheap, no bootstrapping gap, catches today's failure class).
2. 1A detection + 2A tiered remedy inside the existing session-start mod (judgement in python; non-force reload; early handoff for coordinators).
3. Leave session-start's start-time `--force` as is (zero-turn => no re-read cost).
4. Track upstream #24057 / #93657 / #84320; retire 2A's reload half if a native skills-dir hook reload ships (rule tool-currency-and-native-first).

Unverified (no arm run, read-only lane): whether `$.command.run` resolves with the reload's report text for `/reload-plugins`; whether a `SendMessage`
inbox message beginning with `/` executes as a slash command in a `--bg` session; whether `EnterWorktree` moves `$.plugin.root` like `/cd` (2.1.246).

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — live CHANGELOG.md (2.1.288) for reload/hot-reload entries; issues #24057, #84320, #90135, #93657, #95924
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — session-start / coordinator-handoff mods, spec, live-arms report, pr.py land, vendored d.ts
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs corpus (`sources/agent-harness-docs/docs/claude-code`)
