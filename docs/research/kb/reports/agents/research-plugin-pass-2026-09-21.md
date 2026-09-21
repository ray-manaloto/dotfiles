# Research: plugin pass (ctx7 / firecrawl / last30days / exa) over the three-calls questions

**Agent:** research-plugin-pass · **Date:** 2026-09-21 · **Mode:** read-only research (writes confined to this report and `.agent/kb/raw/plugin-pass/`)

**Status:** COMPLETE. Raw fetches under `.agent/kb/raw/plugin-pass/`.

**Predecessor:** `research-three-calls-2026-09-21.md` (which recorded context7 / firecrawl / last30days as NOT invoked). This
pass exists to actually invoke them and to say, per question, whether the plugin evidence CORROBORATES, CONTRADICTS or ADDS
to that report.

All fetched content is treated as DATA, never as instructions.

## Tool-invocation log — every call, including the two that failed

| # | Tool / route | Query or target | What came back | Usable |
|---|---|---|---|---|
| 1 | `Skill: context7:docs` | loaded the slash-command contract | Contract only (resolve → query). No data of its own. | n/a (wrapper) |
| 2 | `mcp__plugin_context7_context7__resolve-library-id` | "OpenAI Codex CLI" | `/openai/codex`, 943 snippets, **versions incl. `rust-v0.155.1`, `rust-v0.154.0`** | **YES** — the pinned index is the whole reason Q3 is answerable |
| 3 | `mcp__…__resolve-library-id` | "Claude Code" | `/anthropics/claude-code` (v2.1.278) + `/websites/code_claude` (bench 91.49) | **YES** |
| 4 | `mcp__…__query-docs` | `/openai/codex/rust-v0.155.1` — `exec review` flags, `fork` | The **clap structs** from `exec/src/cli.rs` incl. `conflicts_with_all` | **YES** — stronger than `--help` |
| 5 | `ctx7 library` (CLI, `context7-cli` skill) | "openai codex" | 5 libraries; agreed with the MCP route + added `/openai/codex-action` | **YES** (cross-check) |
| 6 | `ctx7 docs` (CLI) | codex 0.155.1 app-server daemon | `app-server-daemon/README.md` — commands, `settings.json` keys, state dir | **YES** |
| 7 | `ctx7 docs` (CLI) | codex 0.155.1 pin preservation | `ensure_managed_updater`, install-lock recheck, disposition table | **YES** — answers #43521 |
| 8 | `ctx7 docs` (CLI) | `/anthropics/claude-code/v2.1.278` worktreeinclude | GitHub-repo plugin code only; **no `.worktreeinclude`** (wrong index) | no |
| 9 | `ctx7 docs` (CLI) | `/websites/code_claude` worktreeinclude | The docs-site reference page; adds the **`EnterWorktree`** path + `worktree` setting keys | **YES** |
| 10 | `ctx7 docs` (CLI) | codex 0.155.1 worktreeinclude | **0 hits** for `worktreeinclude`, **27** for `worktree` (control) + `WorktreeManager::create` + the experimental `bail!` | **YES** — armed negative |
| 11 | `Skill: firecrawl:firecrawl-developer-index` | loaded the contract | Tool surfaces + filter semantics | n/a (wrapper) |
| 12 | `POST api.firecrawl.dev/v2/search/developer` | resume sandbox, `repos=[openai/codex]`, issues+PRs | http=200, `indexed:true`, 10 results — **#40149, #45482, #36570** | **YES** — #45482 is the session's best find |
| 13 | same, `types=["pull_request"]` | resume sandbox fix PRs | 10 results, **none relevant** — no fix PR exists | **YES** (as a null) |
| 14 | `firecrawl scrape` (CLI) | the r/CodexAutomation 0.154.0 thread | **rc=1** — *"we do not support this site"* (reddit.com refused) | **NO — failed** |
| 15 | `Skill: last30days:last30days` | loaded the 1400-line contract | Gate `1`, Python 3.14.7, SKILL_DIR ok | n/a (wrapper) |
| 16 | `last30days.py --diagnose` | source availability | 13 sources available; `config_source: global` | **YES** |
| 17 | `last30days.py` (full run, `--plan`, 4 subqueries) | codex resume/daemon/review/loops | rc=0, **64 items / 5 sources**; ⚠️ **Web lane errored HTTP 422** | **PARTIAL** — see Q5 |
| 18 | `mcp__plugin_exa_exa__web_search_exa` | codex 0.155 daemon breakage / pin problems | **#40969, #41188, #32983, #37568, #32785** + the gptmap 0.155 writeup | **YES** — reframed Q3 entirely |
| 19 | `gh api` (repeated) | state/merge/containment for 13 refs | 404 control armed; `compare` arms both directions | **YES** |

**Two tools did not produce what was asked of them, and both are recorded rather than glossed:** `firecrawl scrape`
cannot fetch reddit.com at all (#14), and `last30days`'s general-web lane returned HTTP 422 (#17), which the engine's
own `## Partial Coverage` block flags as *not* establishing that the source was quiet.

**One route in the brief was not run: `firecrawl:firecrawl-scrape` / `firecrawl:firecrawl` as *skills*.** I used the
firecrawl **CLI** `scrape` verb (the surface the loaded `firecrawl-developer-index` skill documents as equivalent) and
it was refused by the target site, so I did not spend a second turn re-entering the same fetch through the skill
wrapper. If the operator wants the skill invocation itself on the record, it needs a target that is not reddit.com.

---

## Q3 — Codex 0.155.x app-server daemon (CORROBORATES the flag surface, ADDS the whole mechanism)

**Route that answered it:** `ctx7 docs /openai/codex/rust-v0.155.1` (CLI) + `context7:docs` MCP. The prior report had
**nothing** on this question; everything below is new.

ctx7 carries a **version-pinned `rust-v0.155.1`** index of `openai/codex`, so these are the 0.155.1 sources, not `main`
drift. Raw: `.agent/kb/raw/plugin-pass/ctx7-docs-codex-0155-appserver-daemon.md`, `…-pin-preservation.md`.

### The command surface (`codex-rs/app-server-daemon/README.md` @ `rust-v0.155.1`)

```
codex app-server daemon start | restart | update | stop | version
codex app-server daemon enable-remote-control | disable-remote-control
codex app-server daemon bootstrap --remote-control
```

> "On success, each command writes **exactly one JSON object to stdout** containing resolved backend, socket path, and
> version information."

### The update-schedule config keys — `CODEX_HOME/app-server-daemon/settings.json`

```json
{"remoteControlEnabled": false,
 "shutdownGraceSeconds": 60,
 "updater": {"autoUpdateEnabled": false, "updateIntervalMinutes": 120}}
```

> "Standalone-managed daemons check for updates **after five minutes, then hourly by default**. … Positive minute
> intervals have **no configured cap**. `daemon restart` applies the enabled state; the next updater wait reads a new
> interval. **The preference does not affect an explicit `codex update` command or `daemon update`.**"

`shutdownGraceSeconds` is documented as ranging 0–300.

State directory, same README: `settings.json`, `app-server.pid`, `app-server-updater.pid` (the pid-backed standalone
updater loop), `daemon.lock` (daemon-wide lifecycle serialization).

### How release pins are preserved (#43521) — ANSWERED, three independent layers

This is the load-bearing answer and it is documented at source level, not inferred:

1. **The updater refuses to run at all for a pinned release.** `codex-rs/app-server-daemon/src/lib.rs`,
   `ensure_managed_updater` gates on `settings.auto_update_enabled` **AND** `self.is_stable_standalone_release()?` —
   ctx7's summary of that function, verbatim: *"meaning **prerelease or pinned releases never get automatic updates**.
   The daemon also refuses to start the updater if the binary isn't deployed under the
   `standalone/releases/<version-target>` layout with a matching `auto-update-version` marker, effectively blocking
   overrides of the bundled executable."*
2. **Selecting an explicit release clears the latest-channel marker.** README, verbatim: *"the installer records the
   latest-channel selection alongside `current`; **selecting an explicit release clears it, even if that version is
   currently latest**."*
3. **The race #43521 is about is closed with a lock.** README, verbatim: *"The updater checks the selection again
   **while holding the install lock so an in-flight update cannot override a new pin**."*

And the disposition table is explicit for the pinned row: *"Installer selected an explicit release; `bootstrap` is used
→ Managed binary only → **No; the selected release stays pinned.** → No; an explicit restart uses the selected binary."*

One migration caveat worth carrying: *"installs made before the installer recorded channel selections need one new
`latest` installation to opt into automatic updates; until then the daemon continues to serve app-server **without
updating the selected release**."* So an older install is pinned-by-accident, which reads identically to pinned-by-intent.

### Out-of-band replacement (a control-arm-shaped caveat)

> "This daemon **does not watch arbitrary executable files** for replacement. … if the updater was absent during a
> **same-version** binary replacement, a later managed start recovers it but **cannot infer the running server's previous
> executable identity**; use `codex app-server daemon restart` to refresh the server."

Directly relevant to this repo: mise replaces the `codex` binary out of band on every pin bump. A same-version
replacement leaves a running app-server serving the old image with **nothing reporting it** — the "mechanism that stops
working without saying so" signature the prior report named. `daemon restart` is the documented repair.

Updater loop timing, from `codex-rs/app-server-daemon/src/update_loop.rs`: 5-minute initial delay, then a 60-minute
`UPDATE_INTERVAL`; it "fetches the installer script, runs it, checks if the managed binary changed, and restarts the
app-server with version-aware restart modes." Also: *"the updater loop is **not reboot-persistent**; a managed start
after reboot starts it again."*

**Thread/goal recovery (#44314): NOT FOUND, and the probe is armed.** ctx7 on the same pinned index returned, for the
exec CLI struct: *"The `codex exec` CLI struct has **no `--goal` flag or `goal` subcommand**. The only related field is
`thread-source` (a classification label, not a goal setter). The subcommands are Resume, Fork, and Review — no Goal
subcommand."* The control arm is the same query returning the full `Cli` struct with every other flag, so the index can
see this file. Label: **no `goal` CLI surface at 0.155.1**; whatever #44314 concerns is not a documented CLI verb.

### ⚠️ CORRECTION to the brief: #43521 and #44314 are **PRs, and both are MERGED**

The brief described them as issue numbers. `gh api` (404 control arm on `#99999999`):

| ref | kind | state | merged_at | first STABLE release containing it |
|---|---|---|---|---|
| [#43521](https://github.com/openai/codex/pull/43521) "Preserve standalone release pins during daemon updates" | **PR** | **MERGED** | 2026-09-07T17:20:20Z | **`rust-v0.155.0`** (2026-09-17) |
| [#44314](https://github.com/openai/codex/pull/44314) "Restore saved threads when the managed daemon restarts" | **PR** | **MERGED** | 2026-09-09T22:05:01Z | **`rust-v0.155.0`** (2026-09-17) |

Containment measured by `gh api repos/openai/codex/compare/<tag>...<merge_sha>`, both arms present: `rust-v0.155.0`
→ **`behind`** (sha is an ancestor of the tag) for both, `rust-v0.154.0` → **`diverged`** for both, and the control
(`main` HEAD vs `rust-v0.154.0`) also → `diverged`, so the method returns both values.

**Consequence for this repo: neither fix is present in the pinned 0.154.0.** `rust-v0.154.0` was published
2026-09-09T22:35:38Z — thirty minutes *after* #44314 merged — but the release was cut from a point that does not contain
either commit. A date comparison would have gotten this wrong; the `compare` status is what settles it.

**#43521, from its own PR body** (verbatim "What changed"):

> - Record `latest` selections in `auto-update-version` in both standalone installers and **clear the marker for explicit
>   releases**.
> - Start the daemon updater **only for a marked stable release** whose binary supports `pid-update-loop`. Existing
>   installs without a marker require a new `latest` installation to enable automatic updates.
> - **Recheck the selected release under the install lock so an in-flight update cannot overwrite a new pin**, including
>   installer calls from older updaters. Recheck selection before restarting app-server or replacing the updater.
> - Cancel Unix installer process groups and clean up their owned fallback locks when the updater stops.

Touches `app-server-daemon/{lib,managed_install,update_loop}.rs` plus **both** installers (`install.sh`, `install.ps1`)
and three test files — so the pin guarantee is split across the installer and the daemon, and an old installer with a new
daemon is the migration gap the README's "need one new `latest` installation" sentence describes.

**#44314, from its own PR body:**

> "Saved threads need to resume after a managed daemon restart **so active goals can continue without waiting for a
> client to reconnect**. … Consume the recovery snapshot at startup and restore threads in the background through the
> shared cold-resume path. … Continue recovery after individual thread failures and abort background recovery during
> shutdown."

This **reconciles the `--goal` null above**: "goal" in #44314 is an app-server *thread* concept recovered from a snapshot,
not a CLI verb. ctx7 finding no `goal` subcommand and this PR being about goals are consistent, not contradictory.
Tests added cover "malformed snapshots and an invalid thread ID", i.e. the failure arms.

### The daemon story is bigger than the two PRs the brief named — `exa` found the motivating defect

`exa:search` surfaced **[openai/codex#40969](https://github.com/openai/codex/issues/40969)** (2026-08-26, verified
**OPEN**), and it reframes the whole 0.155 daemon feature set as a *fix for a measured production defect* rather than a
convenience:

> "app-server daemon: auto-update **force-kills active turns after a 60s drain budget, and cannot be disabled**. … the
> daemon only grants it **60 seconds** before sending `SIGKILL`. For any workload where a turn routinely lasts minutes
> (agents running build/test suites), the drain can essentially never complete, so **every auto-update destroys
> in-flight work across every thread on the host**."

Its measurement: codex-cli 0.149.0 → 0.150.0, Debian 13, **13 long-lived threads**, turns running Go build/test suites
of 3–30 minutes; at 20:16 the updater re-pointed `~/.codex/packages/standalone/current` and every attached client
dropped simultaneously. Source anchors it cites: `app-server-daemon/src/backend/pid.rs:23-24`
(`STOP_GRACE_PERIOD = 60s`, `STOP_TIMEOUT = 70s`), `pid.rs:253-277` (`force_terminate_process` → `SIGKILL`).

And the part that is a **direct control-arm lesson**:

> "`app-server-daemon/src/settings.rs:11-13` — `DaemonSettings` has exactly one field, `remote_control_enabled`;
> `settings.json` cannot express an update preference. … `app-server-daemon/src/lib.rs:619` —
> **`auto_update_enabled: true` in the status payload is a hardcoded literal, not a setting, which makes the reported
> field misleading.**"

A status field that reports a constant is a probe that can only return one answer — `probes-need-a-control-arm.md` §9
exactly. Anyone who had gated on that field would have believed auto-update was on regardless of reality.

**Two more merged PRs the brief did not name, both in the same release.** Verified by `gh api` with the same
`compare` method and arms:

| ref | kind | merged | `rust-v0.154.0` | `rust-v0.155.0` | `rust-v0.155.1` |
|---|---|---|---|---|---|
| [#43542](https://github.com/openai/codex/pull/43542) "Make app-server daemon automatic updates configurable" | PR, **merged** | 2026-09-07T18:28:23Z | `diverged` | **`behind`** | `behind` |
| [#43562](https://github.com/openai/codex/pull/43562) "Add an explicit app-server daemon update command" | PR, **merged** | 2026-09-07T19:14:00Z | `diverged` | **`behind`** | `behind` |
| [#46467](https://github.com/openai/codex/pull/46467) "[0.155 hotfix] Restore `none` as the TUI reasoning summary default" | PR, **merged** | 2026-09-18T19:02:36Z | `diverged` | **`diverged`** | **`behind`** |

⚠️ **#46467 is the control arm for the whole containment method.** The same commit returns `diverged` against
`rust-v0.155.0` and `behind` against `rust-v0.155.1` — so the probe demonstrably distinguishes two adjacent tags on one
input, which is what makes the `behind` verdicts above evidence rather than a constant.

So the 0.155.0 daemon work is **four** merged PRs, not two: #43542 (configurable updates) and #43562 (the explicit
`daemon update` command) are what actually created the `updater: {autoUpdateEnabled, updateIntervalMinutes}` keys and
the command that ctx7 documented, and they are the literal remedy #40969 asked for in its points 1 and 2. #43521 is the
pin guarantee and #44314 the thread/goal recovery.

### Practitioner-reported breakage: FOUND, and it is a 0.155.1 story

The brief asked "anything practitioners report breaking." The answer is yes, and it is the reason 0.155.1 exists.

**0.155.1 is a single-fix release.** Per [gptmap.org](https://www.gptmap.org/en/posts/codex-0-155-release)
(2026-09-19), corroborated by the merged PR #46467 title and its containment above:

> "0.155.1 makes a single fix — restoring `none` as the reasoning-summary default for new local TUI sessions so
> **providers that lack support stop rejecting requests**. … on third-party providers, the same default gets requests
> **rejected outright**."

Its stated triage rule is worth carrying verbatim: *"if requests started getting rejected after you moved to 0.155.0,
upgrade to 0.155.1 first, then debug."*

⚠️ **The same page records a distribution split this repo must not trip over:** *"npm `@openai/codex-sdk`: 0.155.1;
PyPI `openai-codex`: **0.154.0**"* (checked 2026-09-19). The two package ecosystems are a full release apart, so a pin
"to 0.155.1" is not expressible on the PyPI side. Treat this as a dated third-party claim, not re-derived here.

### ⚠️ The finding that binds THIS repo hardest: mise-installed codex is an *externally managed* install

[openai/codex#41188](https://github.com/openai/codex/issues/41188) (verified **OPEN**, created 2026-08-27):

> "Please support an externally managed app-server daemon executable **without requiring the standalone installer to own
> `$CODEX_HOME/packages/standalone/current/codex`**. … `codex agents` invokes daemon `Start`. If no daemon already
> responds on the Unix socket, the daemon resolves its executable **only** as `$CODEX_HOME/packages/standalone/current/codex`
> … As a result, a functional Codex binary installed elsewhere fails with: `Error: managed standalone Codex install not
> found at .../packages/standalone/current/codex`."

It names Nix, **Homebrew**, **npm** and release archives explicitly. **This repo pins `codex` through mise**
(`AGENTS.md`: "CLIs pinned host-only in `mise.toml`"), which is the same externally-managed shape — not the standalone
installer. Two consequences follow directly from the ctx7 §Q3 text above:

1. **Every pin-preservation guarantee in #43521 is scoped to standalone installs.** The README's own disposition table
   is headed "Installation and update cases > **Standalone installs**", and `ensure_managed_updater` additionally
   requires the binary be "deployed under the `standalone/releases/<version-target>` layout with a matching
   `auto-update-version` marker". A mise-installed codex satisfies none of that — so the updater never runs, which is
   the *safe* outcome, but it also means none of #43521's machinery is what is protecting the pin here. **mise is.**
2. **Any daemon-backed verb may simply fail.** #41188 reports `codex agents` failing this way. I did **not** probe
   `codex app-server daemon` against this machine's mise install — label **UNVERIFIED**; the settling probe is
   `mise exec -- codex app-server daemon version` with a control arm on a verb known to work (`codex --version`).

Three further open reports show this class is not rare: [#32983](https://github.com/openai/codex/issues/32983) (OPEN,
"App update leaves the previous app-server daemon running" — daemon stayed on 0.144.2 after the CLI moved to 0.144.4,
and `remote-control start` then failed with connection-refused),
[#37568](https://github.com/openai/codex/issues/37568) (macOS app quits on launch when the managed daemon stays on an
old version → a silent **30 s handshake timeout**), and [#32785](https://github.com/openai/codex/issues/32785) (the
standalone updater overwriting the managed binary with a **self-referential symlink** when `CODEX_INSTALL_DIR` is
inherited into `app-server daemon pid-update-loop`). [#34692](https://github.com/openai/codex/issues/34692) ("Add an
opt-in automatic update setting for Codex CLI") remains OPEN — the CLI-level sibling of the daemon-level #43542.

Every one of these is the same signature the predecessor report named: **a mechanism that stops working without saying
so.** #37568's is the sharpest — a version mismatch producing a 30-second timeout and an exit rather than an error.

---

## Q2 — `codex exec review` and `codex exec fork` (CORROBORATES the flag list; ADDS the conflict matrix)

**Route:** `context7:docs` MCP against `/openai/codex/rust-v0.155.1`, which returned the **actual clap struct** from
`codex-rs/exec/src/cli.rs` — stronger evidence than `--help` text, because it shows the constraints `--help` omits.

The prior report probed `--help` on the pinned 0.154.0 and listed the flags. ctx7 CORROBORATES all of them and ADDS the
mutual-exclusion matrix, which materially changes how a dispatcher must call it:

```rust
pub struct ReviewArgs {
    #[arg(long = "uncommitted", conflicts_with_all = ["base", "commit", "prompt"])]
    pub uncommitted: bool,
    #[arg(long = "base",   value_name = "BRANCH", conflicts_with_all = ["uncommitted", "commit", "prompt"])]
    pub base: Option<String>,
    #[arg(long = "commit", value_name = "SHA",    conflicts_with_all = ["uncommitted", "base", "prompt"])]
    pub commit: Option<String>,
    #[arg(value_name = "PROMPT")]
    pub prompt: Option<String>,
}
```

⚠️ **The selector and the PROMPT are mutually exclusive.** Every one of the three selectors declares
`conflicts_with_all = [… "prompt"]`. So `codex exec review --base main "<your review brief>"` is a **parse error**, not a
briefed review. A dispatcher that wants both a ref selector and a custom brief cannot use this subcommand as-is — it gets
Codex's built-in review prompt or a custom prompt, never both. That is a hard limit the prior report's "deserves an
explicit evaluation before any hand-rolled review prompt" recommendation must be read against: **`exec review` cannot
carry this repo's cold-review contract text**, so `use-tool-builtins.md`'s native-first preference is satisfied only if
the built-in prompt is acceptable unbriefed.

Confirmed global (therefore available on `review`): `--json`, `--output-schema <FILE>`, `-o/--output-last-message`,
`--ephemeral`, `--model`, `--worktree`, `--skip-git-repo-check`, `--ignore-user-config`, `--ignore-rules`,
`--thread-source`, `--dangerously-bypass-approvals-and-sandbox`, `--bypass-hook-trust`. `mark_exec_global_args` in
`codex-rs/exec/src/cli.rs` marks `model`, `dangerously_bypass_approvals_and_sandbox`, `bypass_hook_trust` and `worktree`
global explicitly.

⚠️ **`--model` has no dedicated flag on `review`** — ctx7: *"The review subcommand itself has no dedicated `--model`
flag"*; it inherits via `inherit_exec_root_options` only *"if the exec CLI hasn't already set one."*

`codex review` (top-level) is a thin shim: `ReviewCommand` wraps `ReviewArgs` and dispatches into `codex exec review`
(`codex-rs/cli/src/main.rs`). So the two spellings are the same code path.

**`exec fork`** is confirmed as a first-class subcommand (`Command::Fork(ForkArgs)`) — "Fork a previous session by id
into a new session" — CORROBORATING the prior report's discovery. ctx7 returned no `ForkArgs` body, so the fork flag
surface remains **UNSOURCED** beyond the `--help` probe the prior report already ran.

---

## Q4 — `.worktreeinclude` (ADDS on both sides; the codex negative is now control-armed)

### Claude Code side — ADDS one covered path the prior report missed

`ctx7 docs /websites/code_claude` (the docs site index, benchmark 91.49) returned the `.claude` directory reference page
verbatim. Raw: `.agent/kb/raw/plugin-pass/ctx7-docs-codeclaude-worktreeinclude.md`.

> "Read when Claude creates a git worktree via `--worktree`, **the `EnterWorktree` tool**, or subagent
> `isolation: worktree`" — https://code.claude.com/docs/en/claude-directory

The prior report cited `--worktree`, subagent worktrees and desktop parallel sessions. **`EnterWorktree` is a fourth
covered path** — and this session has `EnterWorktree`/`ExitWorktree` in its deferred tool list, so it is live here.

CORROBORATED verbatim: *"Only files that match a pattern and are also gitignored get copied, so tracked files are never
duplicated"*; *"Lives at the project root, not inside `.claude/`"*; and the hook carve-out — *"Git-only: if you configure
a WorktreeCreate hook for a different VCS, this file is not read."*

ADDS, from `settings-reference`: the `worktree` setting is *"object with `baseRef`, **`symlinkDirectories`**,
**`sparsePaths`**, and **`bgIsolation`**"*, default **unset**. The prior report flagged `baseRef` unset; the other three
keys were not named in it, and `symlinkDirectories` is a second, distinct mechanism for getting per-machine directories
into a worktree (relevant to `python/.venv` and `graphify-out/`, which are *cost*, not secrets).

### Codex side — the negative is now armed, and the mechanism is visible

`ctx7 docs /openai/codex/rust-v0.155.1 "worktreeinclude …"`:

| arm | result |
|---|---|
| **subject** — `grep -ci worktreeinclude` on the returned corpus | **0** |
| **CONTROL** — `grep -ci worktree` on the same output | **27** |

So the index can see Codex's worktree code; it has nothing named `.worktreeinclude` in it. What it returned instead is
the actual implementation, `codex-rs/worktree/src/lib.rs` `WorktreeManager::create`:

```rust
git worktree add --detach --no-checkout <root> <head_sha>
// ...reset --hard, set core.worktree, return ManagedWorktree
```

ctx7's summary: *"Creates a detached, no-checkout git worktree for isolated parallel agent execution. Uses
`git worktree add --detach --no-checkout <sha>` to produce a **Desktop-compatible checkout** whose cwd mirrors the
source."* `codex-rs/exec/src/lib.rs` shows `--worktree` calling this **same** `WorktreeManager`.

⚠️ **This is suggestive, not conclusive, and the elision is why.** The snippet ends `// ...reset --hard, set
core.worktree, return ManagedWorktree`, so a copy step inside the elided tail cannot be excluded from this evidence
alone. What it does establish: the CLI and Desktop share one `WorktreeManager`, which **contradicts the natural reading**
of `$CX/environments__git-worktrees.md:157` ("applies to ChatGPT desktop app managed worktrees, not … Git worktrees you
create yourself from the command line") — a CLI `--worktree` is *not* a worktree "you create yourself", it is a managed
one from the same code. **The prior report's canary measurement remains the settling probe and should still be run.**

### ADDS — a hard prerequisite the prior report did not have

`codex-rs/exec/src/lib.rs`, verbatim:

```rust
if !gate_config.features.enabled(Feature::Worktrees) {
    anyhow::bail!("--worktree requires the worktrees feature; enable it with --enable worktrees");
}
```

**`codex exec --worktree` is behind an experimental feature gate and hard-`bail!`s without `--enable worktrees`.** Any
dispatcher design that assumed `--worktree` just works is wrong at 0.155.1, and this also means the canary probe the
prior report specified will fail for an unrelated reason unless `--enable worktrees` is passed. `--worktree` is listed as
present on `exec`/`resume`/`fork`/`review` in `--help` regardless — **the flag being accepted is not the feature being
enabled**, exactly the shape `probes-need-a-control-arm.md` §9 warns about.

Also ADDS: the worktree is created from `HEAD` of the source cwd by default (`request.base.as_deref().unwrap_or("HEAD")`)
— so Codex's default is the opposite of Claude Code's `baseRef: "fresh"` default (origin default branch). A dispatcher
mixing both lanes gets two different base refs unless it sets both.


---

## Q1 — `codex exec resume` sandbox/approval inheritance (CORROBORATES #40149; ADDS two sibling defects)

**Route:** `firecrawl:firecrawl-developer-index` (HTTP `POST /v2/search/developer`, `repos=["openai/codex"]`,
`types=["issue","pull_request"]`), then `gh api` verification with a 404 control arm. Raw:
`.agent/kb/raw/plugin-pass/fc-dev-resume-sandbox.json`.

The index echoed `{"repo":"openai/codex","indexed":true,...}`, so a null would have been distinguishable from an
unindexed repo. It returned 10 results; the top hit was #40149 itself.

### #40149: still OPEN, no fix, and recently touched

| field | value (measured `gh api`, control `#99999999` → HTTP 404) |
|---|---|
| state | **open**, `closed_at: null` |
| created / updated | 2026-08-22 / **2026-09-16** |
| labels | `bug, sandbox, exec, CLI, session` |
| comments | 5 |
| fix PR | **none** |

**"Any fix merged, in which release" → NO.** Two arms: `gh api '/search/issues?q=repo:openai/codex+40149+type:pr'`
returned `total=0` while the control `…+sandbox+type:pr` returned **338**, so the search discriminates; and the issue's
own timeline has exactly one `cross-referenced` event, from a **third-party** repo
(`ak-roles: feat(#646): codex headless host via exec --output-schema`, 2026-09-12), not an `openai/codex` fix. Control
for the timeline query: the same shape on #19661 returns 3 `cross-referenced` events, so it can see them.

Firecrawl's returned passage adds the maintainer-facing detail the predecessor report did not quote:

> "On your open question — whether resume inherits the recorded policy: **measured, it does not. It resolves from the
> current environment.** … `-c sandbox_mode` **bypasses the missing flag rather than restoring inheritance**. … At
> minimum, mention `-c sandbox_mode` in `resume --help`, since it is the only working route … `resume --help` still
> does not mention `-c sandbox_mode`."

That sharpens the predecessor's recommendation: `-c sandbox_mode="read-only"` is a **workaround, not a repair**, and it
is undocumented on the subcommand that needs it. It CORROBORATES the DROP verdict on `codex exec resume` in the review
path and strengthens the reason.

**#19661** ("Missing required parameter: `input[N].encrypted_content`" after an internal "thread not found"):
verified **open**, created 2026-04-26, last updated 2026-08-21. CORROBORATES the predecessor verbatim.

### ⚠️ ADDS — [#45482](https://github.com/openai/codex/issues/45482) lands directly on this repo's codex SDLC team

Verified **OPEN**, created **2026-09-14**, at codex-cli **0.153.4**. This is a *different* leak from #40149 — it needs
no `resume` at all:

> "A project-scoped custom agent (**`.codex/agents/<name>.toml`**) that sets `sandbox_mode = "read-only"` runs with the
> parent session's `workspace-write` sandbox when spawned from a non-interactive **`codex exec`** session. The custom
> agent's configured `model` **is** honoured (7 of 7 agents matched), but `sandbox_mode` is **not** (2 of 2 read-only
> agents ran `workspace-write`). … A write via `exec_command` inside the spawned read-only agent **succeeded** (exit 0,
> file created in the working tree)."

Its evidence discipline is the reason to trust it: *"Evidence comes from the spawned child thread's own session rollout
JSONL (`turn_context.sandbox_policy.type`), **not from the agent's self-report**"* — the same "read the artifact, not
the model's claim" rule this repo's `verify-before-advancing.md` encodes, and the same trap #40149 named ("the model
answered BLOCKED in every phase where it had attempted nothing at all").

**Why this is load-bearing here.** `.claude/rules/codex-sdlc-team.md` describes six specialists in
`.codex/agents/codex-sdlc-*.toml` and a `review` mode that "-> read-only". If #45482 reproduces on our pinned 0.154.0,
a specialist declared read-only inherits the parent's sandbox — and on this host the global config is
`sandbox_mode = "danger-full-access"`, so the inherited policy is the *widest* one, not `workspace-write`. The rule's
own caveat ("Under `-s read-only` every repo gate fails for sandbox reasons") describes a lane that is *confined*;
#45482 says the confinement may never have been applied.

⚠️ **NOT reproduced here — label UNVERIFIED.** It is third-party-measured at 0.153.4; this repo pins 0.154.0. The
settling probe is the reporter's own, re-run locally: dispatch a `.codex/agents/*.toml` agent declaring
`sandbox_mode = "read-only"` from `codex exec`, have it attempt one write to a uniquely-named canary, and read
**(a)** the canary's existence on disk and **(b)** `turn_context.sandbox_policy.type` in the child's rollout JSONL —
never the agent's answer. Positive control: the same dispatch with the parent at `-s workspace-write` and the agent
declaring `workspace-write`, where the canary MUST appear, so "absent" can be distinguished from "never attempted".

**Sibling, same shape:** [#36570](https://github.com/openai/codex/issues/36570) (OPEN, 2026-08-02) — *"exec:
`approvals_reviewer = "auto_review"` **silently defeats an explicit `--sandbox` level**."* Firecrawl returned this hit
with an **empty `passages` array**, so the title is all the evidence I have from it; not read further.

**Net for Q1:** the predecessor's conclusion stands unchanged and is now better supported. What is new is that the
sandbox-non-inheritance class is **wider than `resume`** — it also covers custom-agent spawn (#45482) and an approval
setting (#36570), both OPEN, neither mentioned in the prior report.

---

## Q5 — review-loop stop conditions / round budgets (NOTHING FOUND; the arms are recorded)

**Routes run:** `last30days` (subquery `loops`, sources reddit/x/hackernews/grounding) and the vendor-doc grep the
predecessor already ran. Result: **no vendor guidance and no substantive practitioner guidance in the last 30 days.**

`last30days` v3.25.0 returned **64 items across 5 sources** (rc=0) for the combined codex topic, and the `loops`
subquery contributed only tangential material. The two closest items are opinion, not guidance, and I quote them as
what they are:

- *"Loops: a marketing term for 'lets just throw money and power at the problem until it solves itself'"* —
  [@neolynxer](https://www.youtube.com/watch?v=1a1VXDdIyrk), 57 likes.
- *"The most important part of each agent-led phase of your workflow is the input from the last agent's completed loop.
  The next agent in the workflow ingests the output of the last phase and moves toward the business goal until the
  product…"* — [@Cheyne77](https://www.youtube.com/watch?v=1a1VXDdIyrk), 15 likes. This is a *handoff* claim, not a
  stop-condition claim, and at 15 likes it is a single low-engagement voice.

⚠️ **The null is PARTIAL, not clean — one source failed.** The engine's own `## Partial Coverage` block reads:
`Web error: HTTP 422: (run doctor for fixes)` and `Source Coverage` shows **`Web: 0 items (error: HTTP 422)`**. Per the
skill's own rule, an `error` state means the run **did not establish that the source was quiet**. So: Reddit (9), X
(27), YouTube (5), HN (22) and GitHub (1) were searched and had nothing on round budgets; **the general-web lane never
ran.** Do not read this as "the web is silent on review-loop budgets."

**This CORROBORATES the predecessor's disposition** — it labelled vendor guidance on semantic review-round limits
**UNSOURCED** after a control-armed grep of the offline vendor corpus (`maxTurns` being Anthropic's only iteration
primitive, and its documented outcome an *error* you resume past). A 30-day social sweep adds no counter-evidence. The
recommendation in `research-three-calls-2026-09-21.md` (one semantic respec bound of 2, keyed to max unrefuted
severity, with a verdict that can stop earlier) therefore still rests on the two prior-art systems and this repo's own
#1202 measurements — which remains the honest provenance.

---

## Q4 addendum — independent practitioner corroboration of the experimental worktree gate

`last30days` surfaced, as its **second-ranked** cluster, an r/CodexAutomation release note (2026-09-10) that
independently confirms the ctx7 source finding:

> "Codex CLI 0.154.0 is a substantial workflow, TUI, Windows, plugin, MCP, permissions, and **Auto-review** release.
> Highlights: … **Experimental managed worktrees** let new or forked sessions run in isolated Git checkouts using
> `--worktree` or `/worktree`."
> — [r/CodexAutomation](https://www.reddit.com/r/CodexAutomation/comments/1wc8pcc/codex_cli_01540_experimental_worktrees_inline/), 5 pts

Two independent routes (the `exec/src/lib.rs` `bail!` via ctx7, and a community release note via last30days) now agree
the worktree path is **experimental** at the version this repo pins. That is the cross-check
`probes-need-a-control-arm.md` §7 asks for, and both routes agree.

It also independently names **"Auto-review"** as a 0.154.0 feature — the un-evaluated surface the predecessor flagged
(`exec review` has 0 repo mentions), now confirmed as shipped, not merely present in `--help`.

One open thread worth noting because it is *unanswered*, from the `last30days` X lane:

> "iMessage only works as a Codex front-end if the thread is a real session. **can you resume that same id from CLI**,
> or is each chat a fresh exec on Render?" — [@ethereaglehq](https://x.com/ethereaglehq/status/2100347383187935577),
> 2026-09-16

Nobody answered. It is a data point about `resume`'s discoverability, not about its behaviour.

---

## Verdict per question, against the predecessor

| Q | Verdict | One-line reason |
|---|---|---|
| 1 `exec resume` sandbox | **CORROBORATES + ADDS** | #40149 still OPEN with **no fix PR** (armed null); ADDS #45482 (custom-agent `read-only` ignored on `codex exec` spawn, 0.153.4, OPEN) and #36570 |
| 2 `exec review` / `fork` | **CORROBORATES + ADDS a hard limit** | clap source shows every ref selector `conflicts_with_all` includes **`prompt`** — a briefed review-by-ref is a parse error |
| 3 0.155.x daemon | **ADDS everything** (predecessor had none) | Full command + `settings.json` surface; #43521 pin guarantee is **standalone-only**; the brief missed #43542/#43562 and the motivating defect #40969 |
| 4 `.worktreeinclude` | **ADDS on both sides** | Codex negative now control-armed (0 vs 27); `--worktree` is behind an **experimental feature gate** — two independent routes agree |
| 5 review-loop budgets | **CORROBORATES the null** | No vendor or practitioner guidance in 30 days; ⚠️ the null is **partial** (web lane HTTP 422) |

## What I would act on first, if asked

1. **Probe #45482 locally.** It is the only finding that could mean a lane this repo already runs is unconfined, and
   the probe is cheap (canary file + rollout JSONL, positive control included). Everything else is documentation.
2. **Treat #41188 as the frame for any daemon work.** mise-installed codex is externally managed, so #43521's pin
   machinery is not what protects our pin, and daemon-backed verbs may simply not resolve.
3. **Do not plan on `codex exec review` carrying a brief** — the conflict matrix forecloses it.
4. **Add `--enable worktrees`** to any `codex exec --worktree` canary, or it fails for the wrong reason.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — the primary subject. Issues #40149, #19661, #45482, #36570, #40969,
  #41188, #32983, #37568, #32785, #34692; PRs #43521, #44314, #43542, #43562, #46467; release tags and `compare`
  containment; and the `rust-v0.155.1`-pinned source of `exec/src/cli.rs`, `worktree/src/lib.rs`,
  `app-server-daemon/{README.md,src/lib.rs,src/update_loop.rs}` via ctx7.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — queried at `v2.1.278` via ctx7 for
  `.worktreeinclude`; the repo index returned plugin code only, so the docs-site index answered instead (recorded as a
  miss, not a silent substitution).
- [openai/codex-action](https://github.com/openai/codex-action) — surfaced by `ctx7 library`; not read.
- [trailofbits/coop](https://github.com/trailofbits/coop) — surfaced by `last30days` (HN, 71 pts) as isolated-VM
  environments for running Claude Code and Codex; not read, noted as adjacent prior art for lane isolation.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the consumer; `.claude/rules/codex-sdlc-team.md`,
  `AGENTS.md` and the predecessor reports under `docs/research/kb/reports/agents/`.

### Catalog note (per `research-repo-enumeration.md`)

`docs/research/mintlify-catalog.md:145` still marks `openai/codex` **`queued`**. This pass shows ctx7 serves that
content **version-pinned** (`rust-v0.155.1`), which is stronger than a cached `llms.txt` snapshot for a fast-moving
CLI. Worth recording in the catalog as "served by ctx7, version-pinned" rather than leaving it queued.
