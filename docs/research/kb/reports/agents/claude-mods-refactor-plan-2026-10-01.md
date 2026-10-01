# Claude Mods (2.1.287) refactor plan for dotfiles + knowledge-base

Synthesis report, 2026-10-01 (Fable 5.1, synthesis lane; read-only — no source edited, nothing
installed or enabled). Written for Ray's grilling.

Inputs: offline mirror of all 225 code.claude.com/docs/en pages (native `.md`) at
`<scratch>/mods/ccdocs/` — cited as `ccdocs/<page>.md:<line>`; release notes cited as
`rel-v2.1.285.md`, `rel-v2.1.286.md`, `rel287.md:<line>` (same scratch dir); the research
sweep `docs/research/kb/reports/agents/claude-code-mods-2-1-287-sweep-2026-10-01.md` (cited
`sweep.md:<line>`); both repos' working trees (dotfiles branch `fix/s29-00b-bot-pr-regenerate`,
knowledge-base `main`); the installed `claude` (`2.1.287 (Claude Code)`, `claude --version`).

Convention: **DOCS SAY** = the vendor page states it; **OBSERVED** = we ran it or read our own
file in this session. Every table row says which.

## Answer

1. **Mods are our function hooks, renamed and on by default.** A mod is "a plugin whose code
   registers event handlers" via `hooks/hooks.json` `"modules"` + `register(on)`
   (`ccdocs/plugins__mods__overview.md:103-116`); that is byte-for-byte the shape of our
   `claude-doctor`, `plugin-health` and KB `kb-settings-guard` plugins (OBSERVED). Nothing in the
   module format has to change. What changes is the *switching*: the early-access flag is dead —
   "Claude Code v2.1.287 and later ignores it, so setting it to `0` doesn't keep mods off"
   (`ccdocs/plugins__mods__overview.md:94`). Both repos still set
   `"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"` in project settings (dotfiles
   `.claude/settings.json:7`; KB `.claude/settings.json:4`, OBSERVED) — remove it, and rewrite KB's
   G04 ticket (#757), whose design is "the tracked flag".

2. **What mods retire in our machinery (all OBSERVED against 2.1.287):**
   - `/plugin-types` **no longer exists** — `claude -p "/plugin-types"` answers "`/plugin-types`
     isn't installed in this session … closest available command is `/plugin-authoring`" (scratch
     `pt/out.log`), and 0 of 225 doc pages mention it. KB's `kb-mod-runtime-check` is built on it
     and now returns **rc=127 NOT_RUN every run** (`mise run kb-mod-runtime-check`, scratch
     `kb-modrt.log`). Retire it; the docs' replacement is declarations written automatically into
     `<mod>/.claude-plugin/types/` whenever a session loads the mod with `--plugin-dir`
     (`ccdocs/plugins__mods__create.md:272-282`), plus the public
     `mods/types/claude-code.d.ts` — which is what dotfiles already vendors.
   - Our hand-rolled Bun test harness (`tests/fixtures/claude_doctor_hook/harness.ts`, 83 arms)
     has a native successor: `claude plugin test` with the `claude-code/testing` kit runs "with no
     session, sign-in, or network" and "exits with status 1 when a test fails, so it works in CI"
     (`ccdocs/plugins__mods__test.md:13,55`). Proved on a scratch copy of `plugin-health`: 1 pass,
     1 deliberately-wrong control arm fails, rc=1 (scratch `ptest-ph.log`). This is the answer to
     dotfiles #1042 ("No TypeScript test tier").
   - The `claude plugin validate --strict` + `tsc` build gates (`fnhook_gates.py`) **stay** — the
     docs make `validate` the review tool for mods (`ccdocs/plugins__mods__admin.md:104-117`).
     Keep vendoring the `.d.ts`: a `--plugin-dir` load that is not a session writes no types
     (OBSERVED: `claude --plugin-dir <copy> plugin list` wrote nothing into `.claude-plugin/`), so
     CI cannot generate them. Bump the pin 2.1.284 → 2.1.287: the upstream file changed (501,401 B
     → 507,444 B, 142 diff lines; both headers still read "Written by Claude Code 2.1.277"; bogus
     tag control → 404).

3. **`claude-doctor` is broken only at `validate`, not at load.** DOCS SAY: "`claude plugin init`
   and `claude plugin tag` refuse a name that draws the error. Only these commands check the name.
   Claude Code still installs and loads a plugin whose name they refuse"
   (`ccdocs/plugins__manifest-reference.md:173`). OBSERVED: `claude plugin validate
   .claude/skills/claude-doctor` → rc=1 "Plugin name "claude-doctor" is reserved"; `claude plugin
   list --json` → `claude-doctor@skills-dir project enabled`. So the hook still runs today, but
   hk's `fnhook_gates` step (which shells to `validate --strict`) is red on every commit touching
   the plugin, and the docs reserve the right to refuse at load later. **Rename** (recommended
   `install-doctor`; the sweep's `doctor-verdict` also passed validate) in both identical copies,
   plus every wiring site listed in § claude-doctor.

4. **Settings/env deltas are small but two of them are already-dead config:** besides the flag,
   KB's project-settings OTel block (`CLAUDE_CODE_ENABLE_TELEMETRY`, `OTEL_LOG_USER_PROMPTS`,
   `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT`,
   `OTEL_LOG_RAW_API_BODIES=file:…`, KB `.claude/settings.json:5-10`) is **ignored in project and
   local settings since 2.1.282** — "Claude Code drops each one … and logs a warning"
   (`ccdocs/settings-reference.md:2887-2903`). Only off-values survive, and `OTEL_LOG_RAW_API_BODIES`
   is not even in the off-value exception list, so dotfiles' `"OTEL_LOG_RAW_API_BODIES": "0"`
   (`.claude/settings.json:13`) is dropped too. Anything OTel must move to the shell, user
   settings, or a `--settings` file — all of which are **Ray's call**, outside the repo.

5. **"You should know" needs Anthropic's *analytics* on, not OTel.** The built-in
   `cc-plugin-you-should-know` is "Disabled by default … Enable with `/plugin enable
   cc-plugin-you-should-know@builtin`" (`ccdocs/plugins__mods__overview.md:215`), and the release
   note scopes it to "first-party sessions with telemetry on" (`rel287.md:5`). Its sibling
   `cc-plugin-telemetry` runs "Wherever Claude Code's own analytics are on" and is turned off by
   `DISABLE_TELEMETRY` (`:214`). OBSERVED: `DISABLE_TELEMETRY`, `DO_NOT_TRACK`,
   `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` are absent from the shell, from both project
   settings, and from `~/.claude/settings.json` `env` (key names listed, no values); no managed
   settings directory exists; auth is `claude.ai` / `subscriptionType: max`. So this machine
   already satisfies the documented precondition; enabling is one interactive command that writes
   user-level state — **Ray's call**. "Enable all telemetry settings" concretely means two
   different things (§ Telemetry): keep Anthropic analytics/error-reporting on (nothing to add),
   and, separately, OTel export to a collector you run — which is a secrets decision under
   `secrets-out-of-the-shell-env.md`.

6. **One new exposure nobody set out to create:** on this machine the built-in guard
   `sec-default` does **not** load ("The guard loads when … The machine has managed settings [or]
   The user is signed in … with a Team or Enterprise plan", `ccdocs/plugins__mods__admin.md:58-63`;
   we are Max, no managed settings). Without it, "the mod can approve a call that a deny rule
   refuses" (`ccdocs/permissions.md:557`) and "A block from a `PreToolUse` hook: the mod can
   approve the call, unless the hook is in managed settings" (`:555`). Our 24 enabled marketplace
   plugins are therefore each one `hooks/hooks.json` `"modules"` key away from lifting both the
   credential-file `permissions.deny` rules (secrets rule 8) and the `hook_guard`. Mitigation that
   fits our rules: a `plugin-health` arm that runs `claude plugin validate` over every enabled
   plugin's cache and fails on any `tool.check` hook (§ Phase 2).

## What 2.1.285-287 change for us

| # | Change (version) | DOCS/REL SAY | Our affected file:line | Action |
|---|---|---|---|---|
| 1 | Mods GA, on by default; flag ignored (287) | `rel287.md:4`; `ccdocs/plugins__mods__overview.md:81,94` | dotfiles `.claude/settings.json:7`; KB `.claude/settings.json:4`; KB #757 design | Remove the env line in both; re-scope KB G04 |
| 2 | Reserved plugin names enforced by `validate`/`init`/`tag` (287 binary; docs undated) | `ccdocs/plugins__manifest-reference.md:165-173`; OBSERVED rc=1 | `.claude/skills/claude-doctor/.claude-plugin/plugin.json:2`, `.agents/skills/claude-doctor/…` (byte-identical, `tests/test_claude_doctor_hook.py:44-46`) | Rename; see § claude-doctor |
| 3 | `/plugin-types` gone (OBSERVED 287) | scratch `pt/out.log`; 0/225 doc hits | KB `python/src/kb_setup/mod_runtime.py:629` (`claude -p /plugin-types`), `mise.toml:1955` `kb-mod-runtime-check` in `GATE_TASKS` (`gates.py:214`); KB #754/#771/#784; dotfiles `fnhook_gates.py:7,463,522` docstrings | Retire the KB gate; adopt dotfiles' vendored-`.d.ts` route; fix stale docstrings |
| 4 | Types auto-written to `<mod>/.claude-plugin/types/` on `--plugin-dir` session load (287 docs) | `ccdocs/plugins__mods__create.md:272-282` | `.claude/types/README.md` ("never generated locally") ; `tsconfig.json` include `.claude/types` | No change to the gate; add a `.gitignore` for `**/.claude-plugin/types/` so a dev session's output never lands in a commit |
| 5 | `claude plugin test` + `claude-code/testing` kit (287 docs) | `ccdocs/plugins__mods__test.md:13-55` | `tests/fixtures/claude_doctor_hook/harness.ts`, `tests/test_claude_doctor_hook.py`; #1042 | Add `tests/*.test.ts` per plugin; run `claude plugin test` from hk/CI; retire harness once parity is proved |
| 6 | Upstream `mods/types/claude-code.d.ts` moved between v2.1.284 and v2.1.287 (OBSERVED 142 diff lines) | curl both tags | `schemas/sources.toml:51-56` (pin 2.1.284), `.claude/types/README.md` "Upstream version", `pin-parity.toml:84-121` | Bump pin to 2.1.287 via the documented two-file edit + `mise run schema-vendor-refresh` |
| 7 | OTel enable/content vars ignored in project/local settings (282; docs mirrored 287) | `ccdocs/settings-reference.md:2887-2903`; `ccdocs/monitoring-usage.md:65` | KB `.claude/settings.json:5-10`; dotfiles `.claude/settings.json:13` | Delete dead keys; if Ray wants OTel, user settings/shell (§ Telemetry) |
| 8 | OTel `user_prompt` gains `prompt_text` copy (287) | `rel287.md:7` | KB telemetry sink `.agent/telemetry/` (if OTel is ever re-enabled) | Mask `prompt_text` wherever `prompt` is masked |
| 9 | `verify` skill is now auto-suggested before commits (286) | `rel-v2.1.286.md:42` | dotfiles `.claude/skills/verify/` exists (skill list) | None required; note it supersedes the memory `feedback_verify_and_spec_review_before_ship` reminder partially |
| 10 | Built-in `cc-plugin-plugin-authoring` ships the `plugin-authoring` skill (287) | `ccdocs/plugins__mods__overview.md:212`; `ccdocs/plugins__mods__create.md:22` | (none — grep of both repos and `~/.claude/{skills,plugins}` for `plugin-authoring` → 0 hits, control: `claude-doctor` → hits) | This is where the session's `plugin-authoring` skill comes from; it writes to `~/.claude/dev-mods/<session>/` (`create.md:28`) — a protected user path, so never let a lane "make a mod" unattended |
| 11 | `--bare` now connects only CLI-named MCP servers, no system reminders, no background tasks (286) | `rel-v2.1.286.md:58` | any `claude -p --bare` lane (none found in `mise.toml`, control grep `--plugin-dir` 0 / `claude -p` hits in KB `mod_runtime.py`) | None |
| 12 | Background Bash stops at `timeout` (default 30 min, max 2 h) (285) | `rel-v2.1.285.md:88` | `.claude/rules/long-running-command-hangs.md` rule 2 (harness `run_in_background`) | Doc note only |
| 13 | `asyncRewake` hook with a missing script now reported once (287) | `rel287.md:13` | none of our hooks use `asyncRewake` (grep `.claude/settings.json`: 0, control `"type": "command"` hits) | None |
| 14 | `claude plugin configure <plugin>` / `pluginConfigs` for `userConfig` (285) | `rel-v2.1.285.md:6`; `ccdocs/settings-reference.md:4721-4745` | `plugin-health` reads `CLAUDE_PROJECT_DIR`/`PATH` via `$.env`; a future `userConfig` option would live in **user** settings only (`:4745` "ignores project and local entries") | Design constraint for Phase 3 |

## Mods vs our function hooks

The docs' own comparison (`ccdocs/plugins__mods__overview.md:192-198`): a mod = "Functions in a
plugin that Claude Code calls in its own process"; a settings hook = "A shell command, HTTP
request, or prompt". Our stack has both. "Settings hooks keep working … Nothing about them is
deprecated" (`ccdocs/plugins__mods__admin.md:75`).

| Our component | Kind today | Mods equivalent | Disposition | Why |
|---|---|---|---|---|
| dotfiles `claude-doctor` (`.claude/skills/claude-doctor/hooks/register.ts`, `classic.SessionStart` + `classic.PreToolUse`) | mod (skills-dir plugin) | same — `classic.*` events are first-class (`ccdocs/plugins__mods__events.md:237`) | **KEEP, rename** | Only the name fails; validate output lists `$.clock.now, $.env.get, $.fs.stat, $.process.run, $.session.root` (OBSERVED) — all still in the API table (`reference.md:166-186`) |
| dotfiles `plugin-health` (`classic.SessionStart`) | mod | same | **KEEP** (validate rc=0) | — |
| KB `kb-settings-guard` (`.claude/mods/kb-settings-guard`, `tool.call{tool=?}` ×3 write tools) | mod, **unregistered** (`register.ts:11` "NOT YET REGISTERED") | same; load it as a project skills-dir plugin | **KEEP, move** to `.claude/skills/kb-settings-guard/` | Project skills-dir plugins load "with no flag and no install step" from the primary cwd after trust (`ccdocs/plugins__loading.md:53,73`); `.claude/mods/` is not a loader path. `CLAUDE_CODE_PLUGIN_DIRS` is documented for environment or `~/.claude/settings.json` only (`reference.md:266`) — user-level. Its matcher is a loop variable (`register.ts:201-202`), which validate prints as `tool=?`; spell the three literals so the static listing works (`create.md:312` requires the *event* literal; matcher literalness is #96570's pitfall, `sweep.md:109`) |
| dotfiles `hook_guard` / `pretooluse-guard.sh` (`PreToolUse` command hook, `.claude/settings.json` hooks block) | settings hook | `tool.call` mod could do it in-process | **KEEP as settings hook** | zero-bash-logic already satisfied (python); a mod version would re-expose #92533 ("Any function-hook tool.call on Bash breaks Agent isolation", `sweep.md:108`; dotfiles #1041 bans it). Mods run **after** managed hooks but a user-tier mod can override a non-managed `PreToolUse` block (`permissions.md:555`) — so the guard's strength is unchanged by migrating, and migrating buys nothing |
| `permissions.deny` credential-file rules (secrets rule 8) | permission rules | n/a | **KEEP + add the Phase 2 mod-audit arm** | On this machine (no managed settings, Max plan) `sec-default` does not load, so an installed mod "can approve a call that a deny rule refuses" (`permissions.md:557`) |
| `fnhook_gates.py` validate + tsc + typed-register + escape-hatch gates; hk `fnhook_gates` step (`hk.pkl:252-262`) | build gate | `claude plugin validate --strict` is the documented review tool (`admin.md:104-117`) | **KEEP**; rename `fnhook`→`mod` only cosmetically, if at all | Still the only pre-load check; CI installs the pinned binary via `.github/actions/setup-claude-code` |
| `.claude/types/claude-code.d.ts` vendored at 2.1.284 (`schemas/sources.toml:51-56`) | codegen input | auto-written `.claude-plugin/types/` in a dev session (`create.md:272`) | **KEEP vendoring, bump to 2.1.287** | CI has no session; "trust these files over any page" (`create.md:284`) means the vendored file must track the running binary — currently 3 releases behind and the content moved |
| `tests/fixtures/claude_doctor_hook/harness.ts` (Bun, 83 arms) | hand-rolled test tier | `claude plugin test` (`test.md`) | **MIGRATE, then retire** | Native kit stubs `env.get`, `process.run`, `clock` (`mock.clock`), raises `$.classic.SessionStart`/`PreToolUse` (`test.md:61-62,109`); proven on our hook shape (OBSERVED). Keep the harness until every arm has a kit twin |
| KB `kb-mod-runtime-check` (`mod_runtime.py`; `/plugin-types` live probe) | runtime gate | vendored `.d.ts` + `claude plugin validate` | **RETIRE** | rc=127 NOT_RUN on 2.1.287 (OBSERVED); the command is gone; also leaked `~/.claude/projects/` entries (KB #784) |
| KB `sources/media/claude-code-function-hooks-types.d.ts` (2.1.267 corpus) | evidence | — | KEEP as corpus only (already "RETIRED AS THE RUNTIME CONTRACT", README) | — |
| `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` (both repos' project `env`) | switch | none — "remove it" (`overview.md:94`) | **RETIRE** | dead; KB `mod_runtime.py:600-601` also sets it for its subprocess |
| dotfiles `codex-sdlc` / `hook_selfcheck` `SubagentStart`+`PostToolUse(Agent)` hooks | settings hooks | `agent.spawn`, `session.receive` mod events exist (`reference.md:117-120,108`) | KEEP | no defect to fix; a mod here would be reinvention (`use-tool-builtins.md`) |

What a mod can do that no settings hook can — the only reasons to write a *new* one: draw a
pane/band, `/command` with no Claude turn, rewrite prompts/system-prompt sections, re-route
`turn.step` to another model, `agent.spawn` `{ model }`, `telemetry.*` observation
(`overview.md:19-23`; `reference.md:66-120,150`). None of our open tickets needs those today;
#1024/#1029 (session-start known-defect register) is a `classic.SessionStart` observer and could
equally be a settings hook — the mod shape was chosen for #1026's typed gates, which still holds.

## The claude-doctor reserved-name break

**Root cause (DOCS SAY).** `claude plugin validate` "checks that the name doesn't pass as one of
Anthropic's own": a name that "Starts with `claude-`, `anthropic-`, `anthropics-`, or
`cc-plugin-`" is an **Error**; `claude`/`anthropic`/`anthropics`/`claude-code`/`claude-mods` are
errors; `official` beside `claude`/`anthropic` is an error; `claude` as a whole word elsewhere
(`mcp-for-claude`) is a **Warning** (`ccdocs/plugins__manifest-reference.md:163-171`). Mods
shipped as `cc-plugin-*` built-ins (`overview.md:208-215`), which is why the namespace is now
fenced. The check is case-insensitive and collapses separator runs (`:163`).

**Blast radius (OBSERVED).** `validate` rc=1 with the full reserved-name text; `--strict` is what
hk's `fnhook_gates` runs, so every commit touching `**/.claude-plugin/plugin.json`,
`**/hooks/**` or the gate itself is red. Loading is unaffected today
(`claude plugin list --json`: `claude-doctor@skills-dir … enabled`), consistent with
`manifest-reference.md:173`. `plugin-health` (rc=0) is a clean control arm — the gate still
discriminates.

**Wiring sites the rename touches** (grep `claude-doctor|claude_doctor`, OBSERVED): both plugin
dirs (`.claude/skills/claude-doctor`, `.agents/skills/claude-doctor` — kept byte-identical by
`tests/test_claude_doctor_hook.py:44-46` and `mise run skills-mirror`), `tests/fixtures/claude_doctor_hook/harness.ts:14` import path,
`python/verification/suites.toml:2961` (`workflow.function-hook-build-gates` lists the register
path), `doctor.toml:244-247` (check named `claude-doctor` — that is the *doctor check*, not the
plugin; can stay), `python/src/dotfiles_setup/claude_doctor.py` (module name — stays; it is not a
plugin), `main.py:1688-1691` subcommand `claude-doctor` (stays), `currency.toml:36`,
`pin-parity.toml:88`, `docs/receipts/1319.md:42`, `.claude/skills/plugin-removal/SKILL.md:65`,
`.claude/agents/claude-code-expert.md`, `docs/specs/*`. Only the **plugin `name` and directory**
must change; python/doctor names may stay (they are not plugin ids) — but keeping two names for
one feature is the kind of drift `pin-parity` exists to catch, so decide deliberately.

| Option | PRO | CON |
|---|---|---|
| **A. Rename plugin to `install-doctor` (recommended)** — directory + `plugin.json` `name` + harness import + suites tokens; keep python module/doctor check names | Fixes the gate at its root; "Name it for what it does" is the validator's own advice (OBSERVED error text); no `claude` word → no warning either (`doctor-verdict` from the sweep is equally clean) | Two names for one feature (plugin vs python module) unless the module is renamed too (bigger diff: `claude_doctor.py`, `main.py`, `doctor.toml`, tests) |
| B. Rename plugin AND python/doctor surfaces to one name | One name everywhere | Touches `doctor.toml` `[claude]` section (reviewed config), `main.py` CLI, `suites.toml` tokens, receipts — a day of churn for no behaviour change |
| C. Keep the name, drop `--strict`/skip the name check | Zero diff | Zero-skip violation (`zero-skip-policy.md`); loader may refuse later; `validate` has no per-rule ignore (`ccdocs/plugins__cli-reference.md:540-596` lists `--strict`/`--json` only) |
| D. Keep name, move the plugin out of hk's glob | Gate stays green | A gate that no longer sees the production plugin is "a check that can only pass" (`probes-need-a-control-arm.md` rule 2) |

Fail arm for the fix: the current name must still return rc=1 after the gate change (it does
today), and the renamed copy rc=0 — both already measured (OBSERVED; sweep's independent run
`sweep.md:247` agrees, plus its own controls `anthropic-foo`, `cc-plugin-x`, `myclaude-x`).

## Settings & env-var deltas

Scope column per `ccdocs/settings-reference.md` and `ccdocs/plugins__mods__reference.md:264-274`.
Anything in `~/.claude/settings.json` or the shell is **Ray's call** (`feedback_no_user_level_file_updates`).

| Key / var | Where today (OBSERVED) | Scope DOCS SAY | Action |
|---|---|---|---|
| `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` | dotfiles project `env:7`; KB project `env:4`; KB `mod_runtime.py` subprocess env | ignored from 2.1.287 (`overview.md:94`, `admin.md:51`) | **Remove** (both repos). Control arm before removal: a session with the var unset still lists `plugin-health@skills-dir` as loaded — OBSERVED now (shell has it ABSENT; project settings inject it, so the clean arm is a `--settings '{"env":{}}'`-style run — see Gaps) |
| `CLAUDE_CODE_ENABLE_TELEMETRY`, `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT` = `1` | KB project `env:5-9` | **ignored in project/local** since 2.1.282; only off-values (`none`, `0`) apply (`settings-reference.md:2887-2903`); `/status` or `claude doctor` lists ignored names (`:2901`) | **Remove from KB project settings** (dead). If wanted: user settings / shell — Ray |
| `OTEL_LOG_RAW_API_BODIES` = `file:.agent/telemetry/` (KB) / `"0"` (dotfiles `:13`, added in #553) | project `env` | in the "export session content" group that project settings can't set (`:2890`); `0` is **not** in the surviving off-value list (`:2899`) | Remove both (dead); KB `kb-telemetry-prune` task + #400 become moot unless re-enabled at user level |
| `CLAUDE_CODE_PLUGIN_DIRS` | unset | "Environment, or `env` in `~/.claude/settings.json`" (`reference.md:266`); v2.1.280+ (`env-vars.md:338`) | Do **not** adopt for repo plugins — user-level; use project skills-dir instead |
| `prependPlugins` / `appendPlugins` | unset | "Repositories can't set them" (`admin.md:259`); user settings honoured only with no managed settings and not Team/Enterprise (`settings-reference.md:4751`) | Not available to the repo; **no policy mod** for us |
| `pluginConfigs` (`cc-plugin-sec-default@builtin` options `allowManagedModsOnly`, `allowModsToOverrideDenyRules`) | unset | managed settings only (`admin.md:171-174`) | Not applicable (no managed settings) |
| `disableAllHooks` | unset | any file; outside managed settings it stops user/project/local/plugin hooks AND installed mods (`settings-reference.md:3999-4020`; `overview.md:87`) | Keep unset — it would kill our own guard |
| `disableSideloadFlags` | unset | managed only (`:5891`) | n/a |
| `--safe-mode` / `--bare` | — | `--safe-mode` disables all customizations incl. plugins/hooks (`cli-reference.md:125`); `--bare` skips plugin discovery (`:72`) | Use `--safe-mode` as the "is a mod the cause" probe (`admin.md:82`) |
| `claudeMdExcludes`, `OTEL_*` interval vars, `OTEL_RESOURCE_ATTRIBUTES` | — | still honoured from project settings (`env-vars.md:513`) | none |
| `enabledPlugins` (24 entries, dotfiles) | project | each may now carry a mod; "A mod is a plugin, so the settings that restrict what users can install … decide whether it can be installed" (`admin.md:79`) | Phase 2 audit arm |

Nothing in either repo's `hooks` block changes: `classic.*` events keep firing for settings hooks
"alongside mods" (`hooks.md:15`), and a mod that calls `next(e)` sees the settings hooks' decision
(`events.md:274`).

## Telemetry

Three distinct things are called "telemetry"; conflating them is how a wrong setting lands.

**(a) Anthropic analytics + error reporting ("Claude Code's own analytics").** DOCS SAY: metrics
"never include your code, prompts, or file paths"; error reports are redacted stack traces; opt out
with `DISABLE_TELEMETRY=1` / `DISABLE_ERROR_REPORTING=1` / `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
(`ccdocs/data-usage.md:104-108`). `DISABLE_TELEMETRY` is presence-read — "`0` or `false` still
opts out" (`env-vars.md:441`); `DO_NOT_TRACK` is a normal boolean (`:444`). This is what
`cc-plugin-telemetry` and, per the release note, **You should know** key on (`overview.md:214-215`;
`rel287.md:5` "first-party sessions with telemetry on"). The `$.telemetry.log/mark` API sends "only
when Claude Code or a built-in mod raised it" (`reference.md:186`); a mod can observe or `deny`
`telemetry.log`/`telemetry.mark` (`:150`). OBSERVED: no opt-out is set anywhere we can read
(shell, both project settings, user `env` key names, no managed dir) → analytics are **on**.

**(b) OpenTelemetry export to your own collector.** `CLAUDE_CODE_ENABLE_TELEMETRY=1` + exporter
selectors + OTLP endpoint/protocol/headers (`monitoring-usage.md:16-34,106-127`); traces need
`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` (`:162`). Prompts/tool content are redacted unless the
`OTEL_LOG_*` gates are set (`:173`). It is **not** what YSK needs (the sweep's inference,
`sweep.md:42`, is consistent with every page read here; no page links YSK to OTel — see Gaps). It
must be configured in shell/user/managed settings (`env-vars.md:284,513`), never project.

**(c) The KB raw-body sink.** `OTEL_LOG_RAW_API_BODIES=file:<dir>` writes "the entire conversation
history" untruncated to disk and "implies consent to everything `OTEL_LOG_USER_PROMPTS`,
`OTEL_LOG_TOOL_DETAILS`, and `OTEL_LOG_TOOL_CONTENT` would reveal" (`monitoring-usage.md:125`).
Dead today from project settings; it filled 2.2 GB in one session when it worked (KB #400).

**What "enable all telemetry settings" would concretely mean, and the secrets consequences:**

| Option | What to set (and where) | PRO | CON / secrets rule |
|---|---|---|---|
| **T1. Analytics on, no OTel (recommended baseline)** | Nothing to add; ensure no opt-out var ever lands in `fnox`/shell/user settings; run `/plugin enable cc-plugin-you-should-know@builtin` interactively (user-level, Ray) | Meets YSK's documented precondition; zero new sinks | YSK "Runs a side agent" (`overview.md:215`) — spends plan usage; availability "if available for your org" is unverified until the `/plugin` Installed → Show disabled view is opened |
| T2. + OTel metrics/logs to a local collector, content gates OFF | user settings or shell: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=otlp`, `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_EXPORTER_OTLP_ENDPOINT` | Usage/cost metrics; prompts stay `<REDACTED>` (`monitoring-usage.md:173`) | A collector to run and pin (`mise-tasks-only.md`); the OTLP bearer token is itself a credential — use `otelHeadersHelper` not a literal header (`settings-reference.md:2876`); "Values here are plain text in the settings file and reach every subprocess" |
| T3. + content gates ON (`OTEL_LOG_USER_PROMPTS/TOOL_CONTENT/TOOL_DETAILS=1`) | user settings/shell | Full transcripts for session review | Tool content includes every command's stdout — the exact surface rule 7 says a probe must never print; a credential that leaks into a tool result is now **exported**. Mask `prompt_text` as `prompt` (`rel287.md:7`). Needs its own `doctor.toml` row per secrets rule 5 |
| T4. + raw API bodies to disk (`OTEL_LOG_RAW_API_BODIES=file:…`) | user settings/shell | What KB intended | Unbounded growth (KB #400); a plaintext conversation archive = a credential store under rule 8 ("a FILE can be the credential"); must be gitignored AND excluded from any mod's `$.fs` reach — not possible: mods "read and write files anywhere your user account can" (`overview.md:58`) |

Mods themselves widen the telemetry/secrets surface independently of OTel: a mod "can read your
secrets: environment variables and settings files" (`overview.md:59`), and every credential is
`env = true` by decision (`secrets-out-of-the-shell-env.md`). `claude plugin validate` prints
`env reads:` per module (`create.md:305`) — that line is the cheap audit (Phase 2).

## Phased refactor plan

Gates named are the repo's existing ones (`verify-before-advancing.md`). Each phase is one PR.

### dotfiles

| Phase | Objective | Files | Gates | Risk | Ticket title |
|---|---|---|---|---|---|
| **D0 — Flag + dead env cleanup** | Remove `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` and `OTEL_LOG_RAW_API_BODIES` from project `env`; add `**/.claude-plugin/types/` to `.gitignore`; fix `fnhook_gates.py:7,463,522` docstrings that cite `/plugin-types` | `.claude/settings.json`, `.gitignore`, `python/src/dotfiles_setup/fnhook_gates.py`, `.claude/types/README.md` | `mise run lint`, pytest, `mise run verify`, `mise run rule-sync` (settings.json is in the synced set), `mise run plugin-health-e2e` as the live arm (plugins still load with the var gone) | Low; control arm = `claude plugin list --json` still shows both skills-dir plugins enabled | "mods GA: drop the dead CLAUDE_CODE_ENABLE_FUNCTION_HOOKS flag and project-level OTel keys" |
| **D1 — Rename `claude-doctor` plugin** | Option A; both copies via `mise run skills-mirror`; harness import; `suites.toml:2961` token; `fnhook_gates` glob unchanged | `.claude/skills/install-doctor/**`, `.agents/skills/install-doctor/**`, `tests/fixtures/claude_doctor_hook/harness.ts`, `python/verification/suites.toml`, docs/receipts pointers | `mise run lint` (the red `fnhook_gates` step turns green — the fix's own arm), pytest (`test_claude_doctor_hook`), `mise run verify`, `mise run lint-docs` | Low; name-only. Fail arm: a fixture under `tests/fixtures/fnhook/` named `claude-x` must stay rc=1 (add it) | "Rename the claude-doctor plugin: `claude-` is a reserved prefix in 2.1.287" |
| **D2 — Pin bump + mod-audit arm** | `schemas/sources.toml` + `.claude/types/README.md` → 2.1.287, `mise run schema-vendor-refresh`; add to `plugin-health` (python side) a check that runs `claude plugin validate --json` over every enabled plugin's installed dir and reports any `hooks:` line naming `tool.check`, and any `env reads:` naming a credential from `doctor.toml` `[fnox].env_true` | `schemas/sources.toml`, `.claude/types/*.d.ts`, `python/src/dotfiles_setup/plugin_health.py`, `doctor.toml`, tests | `mise run pin-parity`, `mise run schema-vendor-check`, `mise run lint`, pytest, `mise run plugin-health` | Medium: the `.d.ts` diff may change `tsc` results for `register.ts` (the gate's purpose); the audit's fixture needs a plugin with a `tool.check` hook (write one under `tests/fixtures/fnhook/`) | "Bump vendored Claude Code declarations to 2.1.287; audit enabled plugins for mods that can lift deny rules" |
| **D3 — Native test tier** | Add `tests/<plugin>.test.ts` under each plugin using `claude-code/testing`; hk step `plugin_tests` → `claude plugin test <dir>`; migrate harness arms one by one; retire `harness.ts` when `arms == kit tests` | `.claude/skills/*/tests/*.test.ts`, `hk.pkl`, `python/src/dotfiles_setup/fnhook_gates.py` (or a new `plugin_tests.py`), `.github/actions/setup-claude-code` (already installs the binary), `suites.toml` | `mise run lint`, pytest, `mise run verify`, CI lint job | Medium: kit limits (5 s per test, `reference.md:258`); `$.ui.ask` stubs via `tool.call`; `classic.PreToolUse` result shape must match `ClassicResultOf` | "TypeScript test tier for mods via `claude plugin test` (#1042)" |
| **D4 — Docs/rules sync** | Rename "function hook" → "mod" where user-facing; add a `.claude/rules/mods.md` (eager? no — scope to `**/hooks/**`,`**/.claude-plugin/**`) carrying: mods are unsandboxed, Bash `tool.call` ban (#1041), reserved names, no `/plugin-types`, where types come from, secrets exposure, the deny-override fact | `.claude/rules/*.md`, `AGENTS.md` (budget!), `.claude/CLAUDE.md`, memory | `mise run lint-docs`, `md_size_budget`, `mise run rule-sync` | Low | "Document the mods contract (reserved names, deny-override, test kit)" |

### knowledge-base

| Phase | Objective | Files | Gates | Risk | Ticket title |
|---|---|---|---|---|---|
| **K0 — Dead config + broken gate** | Remove the flag and the six OTel keys from project `env`; retire `kb-mod-runtime-check` from `GATE_TASKS` (it is rc=127 on every run now), keep `mod_runtime.py` only if re-pointed at a vendored `.d.ts`; close/rescope #754, #771, #784; fix `hk.pkl` ("union property 'command' has no selected default" under hk 1.57.0 — OBSERVED in the same run, separate defect) | `.claude/settings.json`, `python/src/kb_setup/gates.py`, `mise.toml:1955`, `python/src/kb_setup/mod_runtime.py`, `hk.pkl` | `mise run kb-gates`, pytest (`tests/test_mod_runtime*.py` need their expectations inverted), `mise run lint` | Medium: `kb-gates` ordering; the hk.pkl break blocks `hk install` on this host already | "mods GA: `/plugin-types` is gone — retire kb-mod-runtime-check, drop the dead flag and project-level OTel keys" |
| **K1 — Vendor the declarations the dotfiles way** | Adopt `schema_vendor`-style pinning of `mods/types/claude-code.d.ts` (shared engine lives in KB already: `kb_setup.currency`); `tsc` gate for `kb-settings-guard` (#776 says it is untyped) | `sources.toml`-equivalent, `.claude/types/`, `tsconfig.json`, `mise.toml` | `kb-gates`, pytest | Low | "Vendor claude-code.d.ts at the running pin; type the settings guard (#776)" |
| **K2 — Register the settings guard as a project skills-dir plugin** | Move `.claude/mods/kb-settings-guard` → `.claude/skills/kb-settings-guard`; spell the three `tool.call` matchers as literals; `claude plugin validate --strict` + `claude plugin test` with the `agentId` arm (`register.ts:33-40` spelling trap) as a kit test; liveness task per #757 but without "the tracked flag" | `.claude/skills/kb-settings-guard/**`, `mise.toml`, `.claude/settings.json` (`enabledPlugins` entry `kb-settings-guard@skills-dir` optional, `loading.md:53`) | `kb-gates`, `claude plugin test`, live arm: a delegated lane's `Edit` of `.claude/settings.json` is denied, main thread allowed | Medium: project skills-dir plugins load only from the primary cwd after trust (`loading.md:73`) — worktree lanes start elsewhere; measure | "G04 rewrite: load kb-settings-guard as a skills-dir plugin; prove it behaves (#757, #773, #772)" |
| **K3 — Programme re-scope (G00-G12, #766)** | Re-read each G ticket against the GA docs: G05 "enforce the direction" must say mods, not the flag; G07/G08 migrations must respect the Bash `tool.call` ban and the deny-override fact (a user-tier mod cannot *strengthen* a managed deny, and here nothing is managed) | `docs/research/reports/2026-09-11-function-hooks-enforcement-programme.md`, issues | `kb-session-review` | Low (docs) | "function-hooks programme: GA re-baseline after 2.1.287" |

Shared sequencing: D0 → K0 (both one-line settings diffs, ship first); D1 unblocks dotfiles'
lint; D2 before D3 (tests type-check against the bumped declarations); K1 before K2.

## Open questions for Ray

1. **Rename `claude-doctor` → `install-doctor` (plugin only), keep python/doctor names? (Recommended: yes, Option A)**
   PRO: smallest diff that turns the gate green at its root; validator's own advice. CON: plugin
   and python module carry different names until a later tidy. Evidence: `ccdocs/plugins__manifest-reference.md:165-173`; OBSERVED rc=1/rc=0 arms.

2. **Remove `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` from both project settings now, without a runtime "flag=0 still loads" arm? (Recommended: yes — the docs are explicit, and our live arm is `plugin list` after removal)**
   PRO: dead config; `admin.md:51` says replace it. CON: no load test with the var at `0` was run
   (`sweep.md:207`); the clean arm needs a session started with `--settings` overriding `env`.

3. **Telemetry posture: T1 (analytics on, enable You should know interactively, no OTel)? (Recommended: T1)**
   PRO: zero new sinks or credentials; meets the documented precondition. CON: YSK spends usage
   and its org availability is unverified until the `/plugin` view is opened; nothing is learned
   about cost/usage that OTel would show. If T2+: user settings only, `otelHeadersHelper` for the
   token, `doctor.toml` row — evidence `settings-reference.md:2876,2887-2903`.

4. **Does the "mod can lift deny rules" exposure (`permissions.md:557`) warrant the D2 audit arm, or a stricter stance (no marketplace plugin that contains a `modules` key)? (Recommended: audit arm; refuse only `tool.check` hooks)**
   PRO: proportional; `validate --json` is cheap and offline. CON: an audit catches a mod *after*
   install; only managed settings (`allowManagedModsOnly`) prevent loading, and we have none.

5. **KB: retire `kb-mod-runtime-check` outright vs re-point it at a vendored `.d.ts`? (Recommended: retire; K1 replaces it)**
   PRO: the live-probe premise (`/plugin-types`) is gone; the dotfiles route is proven in CI. CON:
   loses the "runtime, not file" guarantee #754 wanted — but the docs now say the generated
   `.claude-plugin/types/` is *the* contract and only a session writes it.

6. **KB: load `kb-settings-guard` as a project skills-dir plugin (K2) rather than `CLAUDE_CODE_PLUGIN_DIRS` in `~/.claude/settings.json`? (Recommended: skills-dir)**
   PRO: tracked, no user-level edit, no per-user install (`loading.md:53`). CON: loads only when
   the session starts at the repo root after trust (`loading.md:73`) — codex/worktree lanes need a
   measured arm; `~/.claude/skills/<same name>` would shadow it (`loading.md:362`).

7. **Bump the vendored declarations to 2.1.287 now, and make the pin follow `claude --version` on this host via the doctor (DRIFT → PR)? (Recommended: bump now; keep DRIFT advisory as ruled 2026-09-21)**
   PRO: 142 upstream diff lines already; `create.md:284` says trust the build's types. CON: each
   bump can turn `tsc` red on `register.ts`; that is the gate working, not a regression.

8. **Adopt `claude plugin test` as the TS test tier and retire the Bun harness after parity? (Recommended: yes, D3)**
   PRO: native, no session, CI exit code; proven on our hook shape. CON: 5 s/test cap; the harness's
   filesystem arms (symlinks, case aliases) need `fs.stat` stubs rather than a real tmpdir —
   some arms may stay in Bun.

## Evidence

| Claim | Source | Verbatim |
|---|---|---|
| Mods on by default from 2.1.287 | `ccdocs/plugins__mods__overview.md:81` | "Mods require Claude Code v2.1.287 or later, and they're on by default." |
| Flag ignored | `ccdocs/plugins__mods__overview.md:94` | "If you set `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` during early access, remove it. Claude Code v2.1.287 and later ignores it, so setting it to `0` doesn't keep mods off." |
| Flag → replace with managed option | `ccdocs/plugins__mods__admin.md:51` | "If you set `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` to `0` during early access, replace it with this option." |
| A mod is a plugin with `modules` | `ccdocs/plugins__mods__reference.md:22` | "`modules`: an array with one path, relative to this file, to the hooks module" |
| Settings hooks not deprecated | `ccdocs/plugins__mods__admin.md:75` | "Nothing about them is deprecated." |
| `classic.*` events | `ccdocs/plugins__mods__events.md:237` | "Each settings hook event … is also an event named `classic.` followed by the settings hook event's name" |
| Where non-managed PreToolUse hooks run | `ccdocs/plugins__mods__events.md:274` | "run after the last mod calls `next` … A mod that answers `tool.call` without calling `next` keeps them from running" |
| Mod can override a PreToolUse block / deny rules | `ccdocs/permissions.md:555,557` | "the mod can approve the call, unless the hook is in managed settings" / "Anywhere else, the mod can approve a call that a deny rule refuses." |
| Guard loads only with managed settings or Team/Enterprise | `ccdocs/plugins__mods__admin.md:58-63` | "The guard loads when either of these is true: The machine has managed settings; The user is signed in to Claude Code with a Team or Enterprise plan" |
| Deny rules don't bind `$.fs`/`$.process` | `ccdocs/plugins__mods__admin.md:66` | "with `Read(.env)` denied, a mod can still read that file with `$.fs.read`" |
| Mods read secrets | `ccdocs/plugins__mods__overview.md:59` | "**Read your secrets**: environment variables and settings files, including an API key you keep in either" |
| Reserved names | `ccdocs/plugins__manifest-reference.md:168-169` | "Starts with `claude-`, `anthropic-`, `anthropics-`, or `cc-plugin-` \| Error" |
| Only validate/init/tag check; loader loads | `ccdocs/plugins__manifest-reference.md:173` | "Only these commands check the name. Claude Code still installs and loads a plugin whose name they refuse." |
| validate rc=1 (OBSERVED) | scratch `val-doctor.log` | "Plugin name \"claude-doctor\" is reserved: it passes as one of Anthropic's own … Name it for what it does." |
| validate controls (OBSERVED) | scratch `val-ph.log`, `val-kb.log` | "✔ Validation passed" (plugin-health rc=0; kb-settings-guard rc=0, `hooks: tool.call{tool=?}`) |
| Still loaded (OBSERVED) | `claude plugin list --json` | `claude-doctor@skills-dir project True 1.0.0` |
| Types written on session load | `ccdocs/plugins__mods__create.md:272` | "Each time Claude Code loads or reloads a mod from a directory you pass to `--plugin-dir` … it writes TypeScript declaration files … into `.claude-plugin/types/`" |
| Trust generated types over docs | `ccdocs/plugins__mods__create.md:284` | "trust these files over any page, this one included, when they disagree" |
| `/plugin-types` gone (OBSERVED) | scratch `pt/out.log` | "`/plugin-types` isn't installed in this session, so it didn't run. The closest available command is `/plugin-authoring`" |
| `/plugin-types` absent from docs (OBSERVED) | `grep -rn plugin-types ccdocs/*.md` → 0; control `plugin-authoring` → hits | — |
| KB gate NOT_RUN (OBSERVED) | scratch `kb-modrt.log` | "[mod-runtime-check] `/plugin-types` exited 1 at 2.1.287 (Claude Code) — the runtime was not described … Not logged in · Please run /login … rc=127" |
| KB hk.pkl eval failure (OBSERVED, same run) | scratch `kb-modrt.log` | "Eval error: union property 'command' has no selected default" |
| `--plugin-dir` non-session load writes no types (OBSERVED) | `ls pdcopy/.claude-plugin/` | only `plugin.json` |
| Upstream d.ts moved 284→287 (OBSERVED) | curl both tags | "v2.1.284 http=200 bytes=501401 … v2.1.287 http=200 bytes=507444 … DIFFERENT … 142"; bogus tag → 404 |
| Our pin | `schemas/sources.toml:53-54` | `version = "2.1.284"` / `…/v2.1.284/mods/types/claude-code.d.ts` |
| `claude plugin test` needs no session, exit 1 on fail | `ccdocs/plugins__mods__test.md:13,55` | "without a session, a sign-in, or a network" / "The command exits with status 1 when a test fails, so it works in CI." |
| Kit runs our hook (OBSERVED) | scratch `ptest-ph.log` | "(pass) SessionStart reports drift … (fail) control arm: a wrong expectation fails … 1 pass 1 fail" rc=1 |
| Mods-can-load probe (OBSERVED) | scratch `ptest.log` | "no hooks module to load; there is no hooks/hooks.json naming one" (rc=1) — DOCS SAY this means "Mods can load" (`troubleshoot.md:27`) |
| Built-ins table incl. YSK | `ccdocs/plugins__mods__overview.md:215` | "`cc-plugin-you-should-know` \| Runs a side agent … \| Disabled by default … Enable with `/plugin enable cc-plugin-you-should-know@builtin`" |
| telemetry built-in gating | `ccdocs/plugins__mods__overview.md:214` | "Wherever Claude Code's own analytics are on \| Disable it in `/plugin`, or turn analytics off, for example with `DISABLE_TELEMETRY`" |
| YSK release note | `rel287.md:5` | "Turn it on with `/plugin enable cc-plugin-you-should-know@builtin` (for first-party sessions with telemetry on)" |
| plugin-authoring is built-in | `ccdocs/plugins__mods__overview.md:212`; `create.md:22` | "Gives Claude the `plugin-authoring` skill for writing mods" / "Claude works from a built-in skill named `plugin-authoring`" |
| Claude-written mods path | `ccdocs/plugins__mods__create.md:28` | "`~/.claude/dev-mods/` followed by the session's ID" |
| OTel vars ignored in project settings | `ccdocs/settings-reference.md:2887,2893-2895,2899,2903` | "Project and local settings can't set variables that a checked-out repository shouldn't control … `CLAUDE_CODE_ENABLE_TELEMETRY` … `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_CONTENT`, and `OTEL_LOG_TOOL_DETAILS` … Only these values still apply … `none` … `0` … requires Claude Code v2.1.282 or later." |
| `OTEL_LOG_RAW_API_BODIES` in the dropped group | `ccdocs/settings-reference.md:2890` | "Variables that export session content: `OTEL_LOG_RAW_API_BODIES` and the detailed beta tracing pair" |
| KB project env (OBSERVED) | KB `.claude/settings.json:4-10` | `"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1", "CLAUDE_CODE_ENABLE_TELEMETRY": "1", "OTEL_LOG_USER_PROMPTS": "1", … "OTEL_LOG_RAW_API_BODIES": "file:.agent/telemetry/"` |
| dotfiles project env (OBSERVED) | `.claude/settings.json:7,13` | `"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"` / `"OTEL_LOG_RAW_API_BODIES": "0"` (added `e8116253`, #553) |
| `DISABLE_TELEMETRY` presence-read | `ccdocs/env-vars.md:441` | "**Setting it to `0` or `false` still opts out**" |
| Raw bodies = everything | `ccdocs/monitoring-usage.md:125` | "Bodies include the entire conversation history. Enabling this implies consent to everything `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, and `OTEL_LOG_TOOL_CONTENT` would reveal" |
| Collector token is plaintext in settings | `ccdocs/settings-reference.md:2876` | "Values here are plain text in the settings file and reach every subprocess Claude Code starts. For an OTLP bearer token that rotates, use `otelHeadersHelper`" |
| `prompt_text` masking | `rel287.md:7` | "drop or mask it wherever you drop or mask `prompt`" |
| Telemetry opt-outs absent (OBSERVED) | shell presence probe; user `env` keys `['CLAUDE_CODE_BRIEF','CLAUDE_CODE_FORK_SUBAGENT','CLAUDE_CODE_NEW_INIT','CLAUDE_CODE_NO_FLICKER','CLAUDE_PLUGIN_OPTION_TIER_PRO','ENABLE_TOOL_SEARCH']`; `ls '/Library/Application Support/ClaudeCode/'` → No such file | `DISABLE_TELEMETRY ABSENT … CLAUDE_CODE_ENABLE_TELEMETRY ABSENT` |
| Auth tier (OBSERVED) | `claude auth status` | `"authMethod": "claude.ai" … "subscriptionType": "max"` |
| Repos can't set prepend/append | `ccdocs/plugins__mods__admin.md:259` | "Claude Code reads both settings from managed settings and never from a repository's settings file." |
| `CLAUDE_CODE_PLUGIN_DIRS` is user-level | `ccdocs/plugins__mods__reference.md:266` | "Environment, or `env` in `~/.claude/settings.json`" |
| Project skills-dir plugin load rule | `ccdocs/plugins__loading.md:73` | "loads only from the `.claude/skills/` of the session's primary working directory, and only after you accept the workspace trust dialog" |
| KB guard unregistered (OBSERVED) | KB `.claude/mods/kb-settings-guard/hooks/register.ts:11` | "⚠️ NOT YET REGISTERED." |
| KB matcher loop (OBSERVED) | `register.ts:201-202` | `for (const tool of WRITE_TOOLS) { on("tool.call", { tool }, handler);` |
| Bash `tool.call` breaks worktree isolation | `sweep.md:108` (anthropics/claude-code#92533) | "Any function-hook tool.call on Bash breaks Agent isolation" |
| `disableAllHooks` reach | `ccdocs/settings-reference.md:4017-4018` | "In any other settings file: Claude Code disables user, project, local, and plugin hooks" |
| `verify` skill auto-run | `rel-v2.1.286.md:42` | "when your project or user skills include one named `verify`, Claude is now told to run it right before committing" |
| Hook time limit | `ccdocs/plugins__mods__reference.md:245` | "A hook's own running time for one event … \| 10 seconds" |
| Hand-rolled harness (OBSERVED) | `tests/test_claude_doctor_hook.py:21-41` | `["mise", "exec", "--", "bun", "run", str(HARNESS)]` … `assert payload["arms"] == 83 + …` |

## Gaps / unverified

- **Runtime proof the flag is ignored** at `0`: not run (would need a session with
  `--settings '{"env":{"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS":"0"}}'` and a `plugin list`/hook
  effect read). Docs-only, same as `sweep.md:207`.
- **YSK availability for this org** and the exact predicate it checks: the Installed → Show
  disabled view is interactive-only; not opened (would be a user-level enable if mis-clicked).
  No doc page ties YSK to OTel or to `cc-plugin-telemetry`; "telemetry on" is read as analytics-on
  (consistent with `overview.md:214`), still an inference.
- **Whether a user-tier mod on this Max/no-managed machine really lifts our deny rules**: documented
  (`permissions.md:557`), not exercised — exercising it means installing a mod that approves a
  `Read(~/.netrc)`, which the brief forbids and which is the wrong thing to do on a host with live
  credentials. A fixture-only arm under `claude plugin test` cannot answer it (the kit has no
  permission engine).
- **Whether `CLAUDE_CODE_PLUGIN_DIRS` is honoured from project settings**: the ignore list is
  "such as" (`settings-reference.md:2903` names `CLAUDE_CODE_PLUGIN_SEED_DIR`, not `_DIRS`); the
  mods reference lists user settings only. Not probed; moot if K2 uses skills-dir.
- **The 142-line `.d.ts` delta** was not read for content; the pin bump PR must run `tsc` on
  `register.ts` and read the diff.
- **`/status` / `claude doctor` "ignored variables" notice** (`settings-reference.md:2901`) was not
  captured for the KB project; it would be the cheapest confirmation that the OTel keys are dead
  there.
- **KB `hk.pkl` eval failure** under hk 1.57.0 appeared as a side effect of running the gate; its
  cause (hk pin vs pkl schema) is outside this report.
- `claude plugin list --json` shows no `cc-plugin-*` rows (OBSERVED), so the built-in roster could
  not be enumerated non-interactively; the docs table (`overview.md:208-215`) is the only source.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — raw `mods/types/claude-code.d.ts` at tags v2.1.284 / v2.1.287 (and a 404 control); release notes v2.1.285-287 via the scratch mirror; upstream issue #92533 via the sweep
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1020, #1024, #1026, #1029, #1041, #1042, #1101, #1225-#1230, #553, #1044 (bodies/titles via `gh`)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issues #754, #757, #766, #771-#773, #776, #784, #400 (bodies/titles via `gh`); working tree read
