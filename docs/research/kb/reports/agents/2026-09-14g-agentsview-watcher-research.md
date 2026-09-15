# agentsview as the substrate for a parallel rule-compliance watcher (2026-09-14)

**Lane:** read-only research. No edits to source, no `--reveal`, no reads of
`~/.agentsview/config.toml` (credential file; `.claude/settings.json:42-56`
denies it and `secrets-out-of-the-shell-env.md` §8 records the leak). Every
command below is a read; the one caveat is noted in §"Side effects".

**Status:** COMPLETE.

## 1. Install and version

| Fact | Evidence |
|---|---|
| Bare `agentsview` on PATH is an **ORPHAN mise shim** | `which -a agentsview` -> `/Users/rmanaloto/.local/share/mise/shims/agentsview` (single hit); running it -> `mise ERROR No version is set for shim: agentsview` |
| NOT pinned in this repo | `grep -rn agentsview` over `*.toml` in the repo: only a *comment* at `mise.toml:138` naming agentsview as an example of exactly this orphan-shim failure shape |
| NOT pinned user-global either | `grep -n agentsview ~/.config/mise/config.toml` -> **0 hits, rc=1**. Control arm, same command shape: `grep -c graphify` on the same file -> **2**. So the probe discriminates; the absence is real. |
| Two versions installed | `ls ~/.local/share/mise/installs/github-kenn-io-agentsview/` -> `0.41.1`, `0.42.0`, symlinks `0`, `0.41`, `0.42`, `latest` -> `0.42.0` |
| Working invocation | `/Users/rmanaloto/.local/share/mise/installs/github-kenn-io-agentsview/0.42.0/agentsview` -> `agentsview v0.42.0 (commit ff8fb4e8, built 2026-09-01T19:37:18Z)` |

⚠️ **Consequence for a watcher:** a watcher may NOT invoke bare `agentsview` —
it exits non-zero with a mise error. It must use the absolute install path, or
the repo must pin the tool first (`mise.toml [tools]`), which is the shape
`mise.toml:138` already describes for `firecrawl`.

## 2. Command surface — ENUMERATED, not asserted

`agentsview --help` at v0.42.0 prints every command. Full list, verbatim from
the help's own groupings (86 lines of command rows; nothing filtered):

**Core:** `daemon` (`restart`/`start`/`status`/`stop`), `health`, `projects`,
`prune`, `serve` (`restart`/`status`/`stop`), `sync`

**Data:** `duckdb` (`push`/`quack`/`serve`/`status`), `embeddings`
(`activate`/`build`/`list`/`retire`), `export` (`day`/`digest`/`hour`/
`sessions`/`status`), `import`, `mcp`, `parse-diff`, `pg` (`push`/`serve`/
`service`/`status`/`vectors`), `raw-sync` (`status`/`watch`), `recall`
(`brief`/`extract`/`get`/`import`/`list`/`query`/`stats`), `secrets`
(`list`/`scan`), **`session`** (`export`/`get`/`list`/`messages`/`search`/
`sync`/**`tool-calls`**/`usage`/**`watch`**), `stats`, `token-use`

**Usage:** `activity report`, `capture` (`report`/`run`), `usage`
(`cursor`/`daily`/`statusline`)

**Other:** `completion`, `doctor` (+`doctor sync`), `openapi`, `skills`
(`install`/`list`), `update`, `version`

`session tool-calls` **exists** (memory was right) — `agentsview session
tool-calls <id>`, "List tool calls made during a session".

### Global flags on every `session` subcommand

```
--format human|json          Output format: human or json (default human)
--json                       Emit JSON output (alias for --format json)
--pg                         Read session data from configured PostgreSQL
--server string              Remote daemon URL
--server-token-file string   File containing bearer token for explicit --server requests
```

So **yes, machine-readable output**: `--json`. (`--format json`; there is no
NDJSON flag on the query commands — `session watch` is NDJSON natively.)

## 3. Data source — multi-agent, file-derived, synced into SQLite

`agentsview --help` ends with an env-var block that names every supported
harness's source directory:

```
CLAUDE_PROJECTS_DIR, CODEX_SESSIONS_DIR, COPILOT_DIR, GEMINI_DIR,
OPENCODE_DIR, CURSOR_PROJECTS_DIR, IFLOW_DIR, AMP_DIR, ZED_DIR,
QWEN_PROJECTS_DIR, QWENPAW_DIR, OMP_DIR, DEEPSEEK_TUI_SESSIONS_DIR,
DEEPSEEK_HARNESS_SESSIONS_DIR
```

It parses those transcript trees into `~/.agentsview/sessions.db` (SQLite,
**5.3 GB** here) and answers every query from that DB.

**Sync happens INLINE on a plain CLI query — no daemon required.** Measured:
`serve status` -> "No agentsview server is running." and `daemon status` ->
"No agentsview daemon is running." and `pgrep -fl agentsview` -> no matches;
`sessions.db` mtime was `Sep 14 18:13`; after one `session list` it was
`Sep 14 21:08`. A subsequent `session get` on THIS live session returned
`ended_at 2026-09-15T02:07:29Z` against a wall clock of `02:08:14Z` — i.e.
**~45s stale, self-refreshing per invocation.**

⚠️ **Side effect to declare:** any query command therefore WRITES to
`~/.agentsview/sessions.db`. It is not a pure read. (The database is
host-global and outside the repo.)

## 4. Streaming / follow — YES, `session watch`

```
agentsview session watch <id>      # "Stream NDJSON events as the session updates"
```

Measured against a LIVE codex session for 58s (`codex:01a0a1bb-…`), the stream
blocks and emits exactly three event types:

| Event | Payload | Count in 58s |
|---|---|---|
| `session_updated` | `{"event":"session_updated","data":"<session-id>"}` | 3 |
| `session.timing` | a JSON-encoded string: per-turn timing, `slowest_call`, `by_category`, and a `turns[]` array of `{tool_use_id, tool_name, category, duration_ms, is_parallel, input_preview}` | 3 |
| `heartbeat` | `{"event":"heartbeat","data":"2026-09-15T02:11:20Z"}` | 1 |

⚠️ **`session watch` is a TRIGGER, not a content feed.** `input_preview` is
truncated for Claude (`"which -a agentsview 2>&1; echo …"`) and **empty string
for codex** on every call in the stream. Do not build the rule matcher on the
watch payload.

⚠️ **`session watch` takes a session id — it does NOT discover new sessions.**
Discovery still needs a `session list` poll.

## 5. Can it see CODEX lanes? — **YES, fully.** This is the load-bearing result.

`session list --since 2d --include-children --include-automated --include-one-shot`
over the last 2 days returned **247 sessions: 186 `claude`, 59 `codex`, 2
`antigravity-cli`**, with `--agent` documented as "Filter by agent (claude,
codex, cursor, ...)".

Codex rows carry `parent_session_id` + `relationship_type: "subagent"`, so the
codex **lane tree** is reconstructable, and `cwd` pins each to a repo.

**Full codex command text is available** — `session tool-calls
codex:01a09c57-363e-7a52-9ddd-9e1874b94b2e --json` returned 3,336 calls,
**2.33 MB in 0.2s**, with `input_json` populated on **0 of 3336 empty**:

```
{"ordinal":1,"timestamp":"2026-09-13T19:55:57.009Z",
 "tool_use_id":"call_ctVFoOb8PosyhrSGd4aMosHB",
 "tool_name":"exec","category":"Bash",
 "input_json":"const r = await Promise.allSettled([\n  tools.exec_command({cmd:\"cat …\",workdir:\"…\"}) …",
 "result_length":40556}
```

Codex's `exec` tool wraps the shell command inside a JS `tools.exec_command({cmd:"…"})`
call, so a rule matcher must look **inside** `input_json`, not assume a bare
command string. Claude rows instead carry `input_json` as the tool's own JSON
(`{"command":"…"}` for `Bash`).

**Claude Code SUBAGENTS are visible individually and by name.** This session's
own team showed up live:

```
agent-aagentsview-research-6391fd94c5066fac  claude  subagent  dotfiles
agent-adiscovery-sweep-06b6c7a33ae85115      claude  subagent  dotfiles
agent-agates-55be83a0f470da84                claude  subagent  dotfiles
d5e77df3-1b6e-447e-8d3f-9b4a26c96f51         claude  (parent)  dotfiles
```

## 6. Freshness — ~30-60s, self-syncing, no daemon

| Probe | Result |
|---|---|
| `session get d5e77df3-…` (this session) at wall clock `02:08:14Z` | `ended_at: 2026-09-15T02:07:29.680Z` -> **45s stale** |
| `session tool-calls agent-aagentsview-…` at `02:13:0xZ` | newest call `ordinal 49, 2026-09-15T02:12:29.541Z` with the FULL command text of a probe issued ~30s earlier |

Good enough for "near-realtime". It is **not** sub-second, and it depends on the
harness having flushed the transcript file.

## 7. Output format

`--json` / `--format json` on every `session` subcommand; `session watch` is
NDJSON natively. `agentsview openapi` prints an OpenAPI 3.1 schema for the same
surface, and `agentsview mcp` exposes read-only MCP tools
(`search_sessions`, `list_sessions`, `get_session_overview`, `get_messages`,
`search_content`, `get_usage_summary`, `query_recall`).

⚠️ Per `.claude/rules/research-doc-sources.md` § "MCP: two lanes", the MCP
server is **lane 2** (our own automation) -> use the **CLI**, not `agentsview mcp`.

## 8. Traps a watcher MUST encode (each measured, both arms)

### T1 — `--include-one-shot` is mandatory, or the watcher sees NOTHING

A Claude Code session with few user turns is classified **one-shot** and
excluded by default. Measured on this very session's project:

| Flags on `session list --resume --project dotfiles` | total |
|---|---|
| `--include-children` | **0** |
| `--include-children --include-automated` | **0** |
| `--include-children --include-one-shot` | **4** |
| all three | **4** |

The 4 are `d5e77df3-…` (the live parent, 68 messages) plus its three named
subagents. **A watcher that omits `--include-one-shot` is a probe that can only
report "no violations".** Always pass
`--include-children --include-automated --include-one-shot`.

### T2 — `ended_at` is not "active"; `--active-since` is the right filter, and it discriminates

Control arms on `session list --active-since <t> --include-*`:

| window | total |
|---|---|
| 2 min | 6 |
| 20 min | 14 |
| 6 h | 87 |

So the filter is real. But sessions whose `ended_at` is hours old still appear
inside a 20-minute window — "active" tracks transcript activity, not `ended_at`.
Sort/scope on the returned `ended_at` yourself if you need a strict window.

### T3 — regex is **RE2**; no lookahead. Two arms:

```
pattern 'mise run (?!lint)'  -> HTTP 400 {"error":"search: invalid regex: … unsupported Perl syntax: `(?!`"}
pattern 'mise run lint'      -> matches returned
```

### T4 — a pattern starting with `-` is parsed as a flag; `--` does NOT rescue it

```
agentsview session search -- '--no-verify' …   -> fatal: accepts 1 arg(s), received 12
agentsview session search '\-\-no-verify' --regex …  -> 8 matches
```
Escape the dashes inside the regex instead.

### T5 — the watcher WILL match itself and every discussion of the rule

`'\-\-no-verify'` returned 8 matches, **all `claude`**, and they were the
briefing text (`tool_name: Agent`), this lane's own probe (`tool_name: Bash`),
and a sibling's summary — **not a single actual `git commit --no-verify`.**
Mitigate by (a) restricting to `tool_name in {Bash, exec}`, (b) excluding the
watcher's own `session_id` and its parent, and (c) matching the command field
inside `input_json` rather than the whole blob.

### T6 — `session tool-calls` has NO `--since`/pagination

It returns the entire session (3,336 calls / 2.33 MB for one codex lane). The
watcher must keep a per-session `ordinal` high-water mark and diff.

### T7 — bare `agentsview` does not run here (§1). Use the absolute path or pin it.

### T8 — control-arm hygiene for the negative direction

Fresh nonsense string `vrunklebitz9903` over `--in tool_input --since 3d` -> **0
matches**, while `mise run` -> **200 (limit-capped)** on the identical command
shape. The probe discriminates in both directions.

## 9. Side effects this research caused (declared, per real-integration-evidence)

1. Every query command **syncs and writes** `~/.agentsview/sessions.db`
   (mtime moved `18:13` -> `21:08` on the first call).
2. The first query **auto-started a background daemon**. Before:
   `daemon status` -> "No agentsview daemon is running", `pgrep -fl agentsview`
   -> no matches. After: `agentsview running at http://127.0.0.1:8080, pid
   24376, uptime 5m44s`, and `pgrep -fl agentsview` -> `24376 … agentsview serve`.
   Control arm for the pgrep: `pgrep -fl claude` -> 3 live processes, so the
   probe was never blind.

   This also reveals the real transport: the CLI is a **client of a local HTTP
   API** (`GET /api/v1/search/content?...` appeared verbatim in an error), which
   `agentsview openapi` documents. A watcher may hit that API directly.

No secret file was read; no `--reveal`; no `secrets scan` (which persists).

## 10. The recipe — a working watcher poll cycle, RUN end-to-end

`AV=/Users/rmanaloto/.local/share/mise/installs/github-kenn-io-agentsview/0.42.0/agentsview`

**(a) discover the live lanes (both vendors, both tiers):**

```bash
SINCE=$(date -u -v-30M '+%Y-%m-%dT%H:%M:%SZ')
"$AV" session list --active-since "$SINCE" \
      --include-children --include-automated --include-one-shot \
      --limit 500 --json
```
-> `{"sessions":[{id, project, agent, cwd, parent_session_id, relationship_type,
    ended_at, message_count, health_grade, secret_leak_count, …}], "total":N}`

Scope with `--project dotfiles` and/or `--agent codex`. Measured: 15 live lanes
in a 30-minute window during this research (claude parent + 3 named Claude
subagents + 11 codex lanes).

**(b) pull the calls for one lane, with full command text:**

```bash
"$AV" session tool-calls "<session-id>" --json
```
-> `{"tool_calls":[{ordinal, timestamp, tool_use_id, tool_name, category,
    input_json, result_length}], "count":N}`. Keep a per-session `ordinal`
high-water mark; there is no `--since` (T6).

**(c) extract the command, per vendor — THE step that decides correctness:**

- **claude**: `json.loads(input_json)["command"]` (tool_name `Bash`).
- **codex**: `input_json` is **JavaScript**, and the shell command sits inside
  `tools.exec_command({cmd:"…"})`. Extract with
  `cmd\s*:\s*"((?:[^"\\]|\\.)*)"` (also handle the backtick form), then
  `json.loads('"'+m+'"')` to unescape.

**(d) match with the repo's OWN rule corpus, not new regexes:**

```python
from dotfiles_setup import hook_guard
rule = hook_guard.match(command_text)   # -> Rule | None ; 20 rules
```

**(e) ad-hoc grep instead of a poll (for one-off questions):**

```bash
"$AV" session search '\-\-no-verify' --regex --in tool_input \
      --since 3d --include-children --include-automated --include-one-shot \
      --limit 200 --json
```
`--in` accepts `messages,tool_input,tool_result`; `--context N` adds surrounding
messages; `--fts`/`--semantic`/`--hybrid` exist. RE2 only (T3).

### Measured result of running (a)-(d) for real

| Matcher | commands scanned | hits | verdict |
|---|---|---|---|
| hand-written regexes (6 rules) | 15 lanes, Bash calls | **11** | **all 11 FALSE POSITIVES** — heredoc bodies and `echo` strings discussing the rules |
| `hook_guard.match()`, claude only | 1,193 | 0 | true negative |
| `hook_guard.match()`, codex raw `input_json` | 10,543 | **0** | **BLIND — see below** |
| `hook_guard.match()`, codex **unwrapped** | 548 real shell cmds in one lane | 0 | true negative (arms below) |
| `hook_guard.match()`, claude, 45-min window | 1,193 | **5** | **REAL violations** |

The 5 real hits were all rule `gate command piped to head/tail` in Claude
subagent lanes, e.g.
`uv run --project python pytest tests/test_codex_schema.py -x -q 2>&1 | tail -40`
and `mise run lint 2>&1 | tail -100 | tee /tmp/lint.log`.

⚠️ **Caveat on those 5:** `session tool-calls` records the tool call, not whether
the PreToolUse guard **denied** it. A watcher must not report an attempt as an
execution — cross-check `--in tool_result` for the deny text before escalating.

### The codex-blindness arm (do not skip this in an implementation)

```
hook_guard.match('git commit --no-verify -m x')                       -> "git --no-verify"
hook_guard.match('…tools.exec_command({cmd:"git commit --no-verify -m x"…})') -> None      # BLIND
hook_guard.match(<same, after unwrapping cmd:"…">)                    -> "git --no-verify"
```

`hook_guard._inert_masked` deliberately blanks quoted strings, and for codex the
command **is** a quoted string. **Feeding codex `input_json` straight into
`hook_guard.match()` produces a gate that can only pass.**

### Control arms for the codex unwrapper

- Sampled unwrapped output is real shell (`rg -n -i "graphify|…" …`,
  `git status --short --branch; git remote -v; …`, `sed -n '1,260p' pyproject.toml`).
- Injected violation through the same path:
  `tools.exec_command({cmd:"cd /x && git add . && git commit --no-verify -m y"})`
  -> unwrapped -> matched rule `git --no-verify`.

### Shape census of one 3,336-call codex lane (why the 0 is honest)

| shape | count |
|---|---|
| `category == "Bash"` | 2,858 |
| contains `cmd:"…"` (double-quoted) | 548 |
| contains ``cmd:`…` `` (template literal) | 3 |
| `cmd:'…'` (single-quoted) | 0 |
| **no `cmd:` at all** | **2,306** |

The 2,306 are not shell: they are codex's own inter-agent MCP calls
(`tools.mcp__codex_app__send_message_to_thread`, `…wait_threads`) that
agentsview still labels `category: "Bash"` because the tool name is `exec`.

Two consequences: **(i)** `category` is not a reliable "is this a shell command"
filter for codex — gate on `cmd:` extraction instead; **(ii)** a bonus the user
did not ask for — **codex lane-to-lane messages are visible**, so the watcher can
observe the codex team's orchestration, not only its commands.

⚠️ A command codex builds **dynamically** (template literal with `${repo}`, a
loop pushing strings) is **not statically recoverable** from `input_json`. 3 of
552 here. That is an irreducible blind spot of this approach.

## 11. VERDICT — Can agentsview support the watcher the user wants?

### **YES — with one mandatory adapter and one honest blind spot.**

| Requirement | Verdict | Evidence |
|---|---|---|
| Observes **Claude** lanes | **YES** | 186 claude sessions/2d; this session and its 3 named subagents seen live |
| Observes **codex** lanes | **YES** | 59 codex sessions/2d; full command text; parent/subagent tree |
| **Near-realtime** | **YES** | ~30-60s; a probe issued at `02:12:29` was queryable by `02:13:0x` |
| **Event-driven** | **PARTIAL** | `session watch <id>` streams NDJSON `session_updated`/`heartbeat`, but only for a KNOWN id and without payload content -> **watch as trigger + `tool-calls` as fetch**, plus a `session list` poll for discovery |
| **Machine-readable** | **YES** | `--json` everywhere; NDJSON on watch; `openapi`; local HTTP API |
| **Enough detail to check a rule** | **YES** | full `input_json` (command text, file paths), `tool_name`, `ordinal`, `timestamp`, `cwd`, `project` |
| Rule matching | **NOT agentsview's job** | use `dotfiles_setup.hook_guard.match()` — hand-rolled regexes were **11/11 false positives** on the same corpus |

**The mandatory adapter:** unwrap codex's `tools.exec_command({cmd:"…"})`
before matching. Without it the codex half of the watcher is a probe that can
only report "clean" — the exact failure `probes-need-a-control-arm.md` §9 warns
about, and it is the failure that matters most here, because codex is precisely
the lane `hook_guard` cannot gate at call time.

**The honest blind spot:** dynamically-constructed codex commands (3/552 in the
sampled lane) cannot be recovered statically. Report them as `UNRECOVERABLE`,
never as clean.

**No fallback mechanism is needed.** Direct transcript polling
(`~/.claude/projects/**/*.jsonl` + `~/.codex/sessions/**`) would re-implement
what agentsview already does — parsing, subagent-tree reconstruction, `cwd`
attribution, cross-vendor normalisation — and `use-tool-builtins.md` makes that
the last resort, not the first reach. agentsview *is* the built-in here.

### Required before building

1. **Pin agentsview in `mise.toml`** — bare `agentsview` currently exits with a
   mise shim error (§1). Host-only, same shape as the `firecrawl` pin at
   `mise.toml:138-145`.
2. Ship the logic as a `python/` module + a `mise run` task
   (`zero-bash-logic.md`, `mise-tasks-only.md`) that **imports `hook_guard`** —
   one rule corpus, two enforcement points (deny at call time for Claude,
   detect after the fact for codex).
3. Exclude the watcher's own `session_id` and its parent, or it reports itself
   (T5).
4. Distinguish **attempted-and-denied** from **executed** before escalating.

## GitHub repos touched

- [kenn-io/agentsview](https://github.com/kenn-io/agentsview) — the tool under
  study; version, command surface and behaviour probed from the locally
  installed v0.42.0 binary (mise backend `github:kenn-io/agentsview`).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo;
  `mise.toml`, `.claude/settings.json`, `.claude/rules/*`, and
  `python/src/dotfiles_setup/hook_guard.py` read as the rule corpus and matcher.

_No remote source or docs site was fetched; every claim above comes from the
installed binary's own help/output or from files in this repository._
