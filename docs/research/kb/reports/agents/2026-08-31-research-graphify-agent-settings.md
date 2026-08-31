# Research: graphify + ty agent settings (in progress)

Started 2026-08-31. Read-only research, no repo edits.

## Version actually read

This checkout's `python/.venv` has **graphifyy 0.9.42** installed (package
import name `graphify`; dist-info `graphifyy-0.9.42.dist-info`), matching
`python/pyproject.toml:9` (`"graphifyy[all]==0.9.42"`) at time of reading. The
concurrent bump-lane's move to 0.9.53 had not landed in this venv as of this
read. All findings below are from **graphify 0.9.42** source, package dir:
`python/.venv/lib/python3.14/site-packages/graphify/`.

## Q1 — `GRAPHIFY_HOOK_STRICT`: REAL, confirmed in source

`GRAPHIFY_HOOK_STRICT` exists and does something concrete.
`graphify/cli.py:517-527` (`_hook_strict_enabled`):

```python
def _hook_strict_enabled(flag: bool) -> bool:
    """Resolve strict mode: GRAPHIFY_HOOK_STRICT env overrides the baked-in flag
    (truthy forces on without a reinstall, falsy is the kill switch); unset defers
    to the flag the installed hook command carried."""
    v = os.environ.get("GRAPHIFY_HOOK_STRICT", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return flag
```

What it does: gates whether `graphify hook-guard read` (the PreToolUse hook
graphify installs on `Read|Glob`) **blocks** the first raw file read of a
session (once — `_mark_session_denied` claims a one-shot O_EXCL marker per
session id, so an agent can never be permanently stranded), forcing the agent
to run a graphify query/explain/path first. Soft/default mode only ever
**nudges** (prints advisory text); strict mode actually denies the tool call
once. `GRAPHIFY_HOOK_STRICT_TTL` (default 1800s, `cli.py:541-548`) is the
grace window: if a query/explain/path ran within the TTL (stamped by
`_touch_query_stamp` at `out_path("cache", "last_query_stamp")`), strict mode
does not block — "recent orientation" satisfies it.

`install.py:1741` and `install.py:312` confirm the same var is documented at
install time: passing `--strict` at `graphify claude-install` bakes
`--strict` into the installed hook command (`_claude_pretooluse_hooks`,
`install.py:1723`), and `GRAPHIFY_HOOK_STRICT` can force it on/off at
**runtime** without reinstalling.

**Is it set in this repo? NO — confirmed off, by design, in a code comment.**
This repo does **not** use graphify's own installed hook-guard command at all.
`.claude/settings.json:52-71` wires `Bash|Grep` and `Read|Glob` to a **custom**
wrapper, `scripts/graphify-hook-guard.sh`, which execs
`dotfiles-setup graphify hook-guard <kind>` (a repo-owned reimplementation in
`python/src/dotfiles_setup/graphify.py`), not `graphify hook-guard`. The
script's own header comment says explicitly:

> `# Advisory, soft mode. Strict mode (GRAPHIFY_HOOK_STRICT/_TTL, graphify/cli.py)`
> `# is an env var, not a code change — set it in .claude/settings.json's env`
> `# block if ever needed.`

Control arm: `grep -rn "GRAPHIFY_HOOK_STRICT" .claude/ scripts/ mise.toml
.config/mise/conf.d/shared.toml` in this repo returns **zero** hits for the
var being *set* — only the one comment mentioning its name. A known-present
var (`GRAPHIFY_WHISPER_PROMPT`) DOES show up via the same grep shape in
`.claude/skills/graphify/references/transcribe.md`, so the probe
discriminates: absence here is real, not a blind grep.

**What actually enforces graphify-first in this repo today is the
`PreToolUse:Bash` additionalContext message** you can see attached to every
Bash call in this very session ("MANDATORY: graphify-out/graph.json exists.
You MUST run `mise run graphify-query`…") — that's the soft-mode nudge text
from `dotfiles-setup graphify hook-guard`, rewritten to point at the repo's
mise tasks (per the script comment: "rewriting its bare-binary nudge text to
this repo's mise tasks"). It is advisory only — nothing currently blocks a
Bash/Grep/Read/Glob call for skipping graphify.

## Q2 — Full env var / setting enumeration (graphify 0.9.42 source)

Enumerated via `grep -rhoE "\bGRAPHIFY_[A-Z0-9_]+"` over the installed package
(`python/.venv/lib/python3.14/site-packages/graphify/`), then each name traced
to its read site to confirm it is a real, live env var (not a docstring/dead
reference). Non-`GRAPHIFY_`-prefixed vars the LLM backends read (`OPENAI_*`,
`ANTHROPIC_*`, `AWS_*`, `GEMINI_API_KEY`, etc.) are omitted — those are
provider credentials, not graphify behaviour knobs.

| Var | File:line | What it does | Set in this repo? |
|---|---|---|---|
| `GRAPHIFY_HOOK_STRICT` | `cli.py:520` | forces the installed `Read\|Glob` PreToolUse hook to block (1) or never block (0) the first raw file read per session, overriding whatever `--strict` the hook was installed with | No — repo bypasses graphify's own hook entirely (see Q1) |
| `GRAPHIFY_HOOK_STRICT_TTL` | `cli.py:545` | seconds (default 1800) a prior query/explain/path orientation stays "fresh" enough to exempt strict mode from blocking | No |
| `GRAPHIFY_ALLOW_LOCAL_PROVIDERS` | `llm.py:275` | opts in to unauthenticated local LLM backends (ollama etc.) without an API key | No |
| `GRAPHIFY_API_KEY` | `serve.py:2382` | bearer-auth key for the `graphify serve` MCP/HTTP server itself | No |
| `GRAPHIFY_API_TIMEOUT` | `llm.py:409,1794` | per-request LLM client timeout (used by `extract --api-timeout` too) | No |
| `GRAPHIFY_AZURE_MODEL` / `GRAPHIFY_BEDROCK_MODEL` / `GRAPHIFY_DEEPSEEK_MODEL` / `GRAPHIFY_GEMINI_MODEL` / `GRAPHIFY_OPENAI_MODEL` | `llm.py` | per-backend default model override for semantic extraction/labeling | No |
| `GRAPHIFY_CLAUDE_CLI_MODEL` | `llm.py:1725` | model passed to the `claude` CLI backend for extraction | No |
| `GRAPHIFY_CLAUDE_CLI_PARALLEL` | `llm.py:2622,3354` | opt-in to run the claude-cli backend with concurrency >1 (defaults to serial to avoid CLI rate/lock contention) | No |
| `GRAPHIFY_DEBUG` | `extract.py:178` | verbose extraction diagnostics | No |
| `GRAPHIFY_DISABLE_THINKING` | `llm.py:476` | disable extended-thinking mode on backends that support it | No |
| `GRAPHIFY_FORCE` | `hooks.py:163,209` | same as CLI `update --force` / `extract --force`: full re-scan, skip incremental gate | No |
| `GRAPHIFY_GOOGLE_WORKSPACE` / `GRAPHIFY_GOOGLE_WORKSPACE_TIMEOUT` | `google_workspace.py` | Google Docs/Sheets/Slides export toggle + timeout for `extract --google-workspace` | No |
| `GRAPHIFY_MAX_CONTEXTS` | `serve.py:103` | cap on contexts returned per MCP query call | No |
| `GRAPHIFY_MAX_GRAPH_BYTES` | `security.py:49` | hard size cap enforced before parsing any graph.json (DoS/corruption guard — every loader path calls `check_graph_file_size_cap`) | No |
| `GRAPHIFY_MAX_OUTPUT_TOKENS` | `llm.py:310` | LLM output token cap for extraction/labeling calls | No |
| `GRAPHIFY_MAX_RETRIES` | `llm.py:428,1387` | LLM call retry count | No |
| `GRAPHIFY_MAX_WORKERS` | `cli.py:3337`, `extract.py:5726` | AST-extraction subprocess parallelism (same as `extract --max-workers`) | No |
| `GRAPHIFY_MTIME_GRANULARITY_MS` | `cache.py:228` | filesystem mtime-comparison granularity for the incremental cache (works around coarse mtime resolution on some filesystems) | No |
| `GRAPHIFY_NO_BACKUP` | `export.py:48` | skip writing a `.bak` before overwriting an export | No |
| `GRAPHIFY_NO_INCREMENTAL_CACHE` | `llm.py:2631` | disable the semantic-extraction incremental cache | No |
| `GRAPHIFY_NO_TIPS` | `cli.py:2435` | suppress the CLI's "did you know" tip lines | No |
| `GRAPHIFY_OUT` | `hooks.py:165,214` | override the `graphify-out/` directory name the git hooks target | No (repo uses the default `graphify-out/`, confirmed present at repo root) |
| `GRAPHIFY_QUERY_LOG` / `_DISABLE` / `_ENABLE` / `_RESPONSES` | `querylog.py:24-35` | enable/disable persisted query logging under `graphify-out/`, and whether to log full responses | No |
| `GRAPHIFY_REBUILD_LOG` | `hooks.py:263` | path for the git-hook background rebuild's log (default `~/.cache/graphify-rebuild.log`) | No |
| `GRAPHIFY_REBUILD_MEMORY_LIMIT_MB` | `watch.py:232` | memory ceiling for `graphify watch`'s rebuild subprocess | No |
| `GRAPHIFY_REBUILD_TIMEOUT` | `hooks.py:151,197` | timeout (default 600s) for the git-hook-triggered background rebuild | No |
| `GRAPHIFY_REPO_ROOT` | `watch.py:1204` | override repo root autodetection for `graphify watch` | No |
| `GRAPHIFY_VIZ_NODE_LIMIT` | `exporters/html.py:24` | node cap before the interactive `graph.html` export degrades/truncates | No |
| `GRAPHIFY_TRIAGE_BACKEND` / `GRAPHIFY_TRIAGE_MODEL` | `prs.py:566,568` | LLM backend/model used by `graphify prs --triage`'s Opus-style ranking | No |
| `GRAPHIFY_WHISPER_MODEL` / `GRAPHIFY_WHISPER_PROMPT` | (transcribe path, per skill doc) | Whisper model + domain-hint prompt for audio/video transcription ingestion | No — but this repo's own `.claude/skills/graphify/references/transcribe.md` documents setting these transiently for a transcription run |
| `GRAPHIFY_BIN`, `GRAPHIFY_OUT_NAME`, `GRAPHIFY_PYTHON`, `GRAPHIFY_SKIP_HOOK` | — | **NOT found as a live `os.environ` read anywhere in the 0.9.42 package.** `GRAPHIFY_BIN` appears only in `.claude/skills/graphify/SKILL.md` shell snippets as a *local shell variable* (`GRAPHIFY_BIN=$(which graphify …)`), not an env var graphify itself reads — this repo's own `scripts/graphify-hook-guard.sh` comment already flags this ("GRAPHIFY_BIN is NOT a binary override"). Treat all four as **not real settings**. |

Control arm for the "not found" row: the same grep shape
(`grep -rn "\"$v\"\|'$v'" ` over the package) returns 2+ hits for every var in
the table above it, and a known-real one two rows up
(`GRAPHIFY_WHISPER_PROMPT`) returns a hit outside this repo's own skill doc
too — so the null result for `GRAPHIFY_BIN`/`GRAPHIFY_OUT_NAME`/`GRAPHIFY_PYTHON`/`GRAPHIFY_SKIP_HOOK` is a real absence, not a grep miss.

**None of the above are set anywhere in this repo** (`mise.toml`,
`.config/mise/conf.d/shared.toml`, `.claude/settings.json`'s `env` block, or
`scripts/graphify-hook-guard.sh`) — confirmed by
`grep -rn "GRAPHIFY_" .claude/ scripts/ mise.toml .config/mise/conf.d/shared.toml`.
Every graphify invocation in this repo runs on pure defaults.

## Q3 — graphify AST-level queries: what's exposed, how an agent uses them

graphify does not expose "raw AST" to an agent directly — it exposes a
**pre-built knowledge graph** (`graphify-out/graph.json`, built from AST
extraction + optional LLM semantic passes) queried via CLI subcommands (all
confirmed via `graphify --help`, package `python/.venv/…/graphify/`):

| Command | Answers | Mechanism |
|---|---|---|
| `graphify query "<question>"` | free-form BFS traversal question over the graph | `--dfs` for depth-first, `--context` to filter by edge type, `--budget` token cap |
| `graphify affected "X"` | **"what does changing X break"** — reverse traversal over `calls`, `indirect_call`, `references`, `imports`, `imports_from`, `dynamic_import`, `re_exports`, `inherits`, `extends`, `implements`, `uses`, `mixes_in`, `embeds`, `requires` edges (`affected.py:12-31`, `DEFAULT_AFFECTED_RELATIONS`) | `--relation` to scope to specific edge types, `--depth` (default 2) |
| `graphify path "A" "B"` | shortest relationship path between two named nodes | graph shortest-path |
| `graphify explain "X"` | plain-language summary of a node + its neighbors | single-node lookup + neighbor dump |
| `graphify god-nodes` | most-connected nodes = architectural hubs (`--json` for machine-readable) | degree-centrality ranking |
| `graphify diagnose multigraph` | reports same-endpoint edge-collapse risk in the graph (a correctness check on the graph itself, not the code) | — |

For "what calls X": `graphify query "who calls X"` or, more precisely,
`graphify affected "X" --relation calls --depth 1` — the `affected` command
IS the blast-radius primitive. This repo's `graphify-first.md` rule already
directs agents to `mise run graphify-query -- "<question>"` — that task wraps
`graphify query`, not `affected`; **`mise.toml` has no task wrapping
`graphify affected`, `explain`, `path`, or `god-nodes`** (confirmed:
`grep -n "graphify" mise.toml` shows only `graphify-query`, `graphify-update`,
`graphify-health`). An agent that wants blast radius today has to invoke
`uv run --project python graphify affected …` directly, bypassing the
mise-task convention this repo otherwise enforces.

graphify also ships an **MCP server mode** (`graphify serve`, `serve.py`)
exposing `query_graph`, `get_node`, `get_neighbors`, `get_community`,
`god_nodes`, `graph_stats`, `shortest_path`, plus the PR tools below, as MCP
tools — but this repo does **not** register it (no `.mcp.json` entry, no
`claude mcp add` history for graphify), consistent with
`research-doc-sources.md`'s "avoid MCP for our own tooling" doctrine: the CLI
+ mise-task path already covers the same capability at lower cost.

## Q4 — `graphify prs` / blast radius for PRs

**Correction to the operator's framing**: `list_prs`, `triage_prs`, and
`get_pr_impact` are not CLI subcommands — the CLI's single `graphify prs`
command (dashboard/deep-dive/`--triage`/`--worktrees`/`--conflicts`) is what a
human runs; `list_prs`/`get_pr_impact`/`triage_prs` are the **MCP tool names**
for the same functionality (`serve.py:1699,1714,1730`), reachable only if
graphify's MCP server is registered (it is not, in this repo — see Q3).

What they need: **`gh` CLI, authenticated** — `prs.py:_gh()` shells out to
`gh` and every fetch path (`fetch_prs`, `fetch_pr_files`,
`_detect_default_branch`) raises/returns None on failure, with
`fetch_prs` raising `RuntimeError("gh CLI not found or not authenticated. Run: gh auth login")`
explicitly. No graphify-specific auth or provider config — `gh`'s own auth is
the only requirement.

**`get_pr_impact` DOES answer blast radius**, confirmed reading
`serve.py:1909-1935` (`_tool_get_pr_impact`) and `prs.py:252-284`
(`compute_pr_impact`): given a PR number, it calls `gh pr diff --name-only`
for the changed files, then walks the **already-loaded in-memory graph** `G`
to compute `(communities_touched, nodes_affected)` — same graph community
structure `god-nodes`/`affected` use, so a PR's blast radius is expressed in
the identical currency as a local code-change's blast radius. Output line
example from the implementation: `"Graph impact: {nodes} nodes across {len(comms)} communities"`.

The CLI equivalent (`graphify prs <number>`, `render_pr_detail`) computes the
same `compute_pr_impact` but only when `pr_number is not None or do_triage or
do_conflicts` (`cmd_prs`, comment: "Graph impact is expensive (concurrent gh
pr diff calls) — only fetch when the user actually needs it").

## Q5 — "Graphify Formal Verification" CI check

**This is NOT the local `graphifyy` pip package** (0.9.42, the thing this repo
pins and runs via `mise run graphify-*`). It is a **separate hosted product**:
the **`Graphify` GitHub App** (details link `https://graphify.com` on every
check), already installed on `ray-manaloto/dotfiles` and posting two PR
checks — `Graphify` (a code-review/coupling-regression comment) and
`Graphify Formal Verification`. Confirmed by reading the live check-run data
for PR #880 via `gh api repos/ray-manaloto/dotfiles/commits/<sha>/check-runs`:

- No workflow file in `.github/workflows/` names either check
  (`grep -rn "Formal Verification" .github/workflows/*.yml` → 0 hits) — it is
  not something CI triggers, it is the GitHub App reacting to the PR webhook
  independently.
- The check's own output on PR #880 (head `91ab94547520d76ccfe5e3c04d58a5f1dc39506f`
  vs base `d8e028176d02b532496e34340f9b9b7b30e5f664`):
  > "Compared … | equivalent (proved) 0 | distinguished 0 | may-equivalent
  > (sampled) 0 | unsupported 0 | error 0 | … No divergences or abstentions
  > to report. … Formal verification is advisory: `equivalent` is a proof
  > over a bounded sound subset; `may_equivalent` is sampled, not proven;
  > `unsupported` and `error` are honest abstentions."
- Raw check-run `status` was `"completed"`, `conclusion` `"neutral"` — but
  `gh pr checks 880`'s human-readable bucket view reports this as
  **`skipping`**. That is a `gh` display quirk (it maps `conclusion=neutral`
  into the same bucket as an actually-skipped job), not evidence the check
  never ran. **Control arm**: the raw API disagrees with the friendly CLI
  view on the same fact — per `probes-need-a-control-arm.md`, that
  disagreement is itself the finding, and the raw API (closer to the source)
  is the one to trust. "Skipping" here means *"ran, found nothing to prove or
  disprove"* (0 comparable function pairs in this diff's blast radius), not
  *"never executed."*
- The companion `Graphify` check on the same PR reported "107 functions in
  the blast radius were not formally verified this run (proofs are advisory
  here)" — so formal verification's proof coverage is itself bounded/partial
  by design, separate from whether the check ran at all.

**Is it worth enabling here?** It already IS enabled — it's a GitHub App
installed on the repo, not a toggle in this repo's config. There is nothing
in `.devcontainer/**`, `mise.toml`, or `.github/workflows/**` that gates it.
What would change its output from "neutral/no divergence" to something
substantive is a PR whose diff touches function bodies within graphify's
"bounded sound subset" for equivalence proving — i.e., it is already doing
its job; nothing here needs local action. **This is a separate product from
the local `graphifyy` package research questions 1-4 covered** — do not
conflate "graphify" (this repo's pinned Python package + CLI) with "Graphify"
(the hosted GitHub App). I could not determine graphify.com's pricing/opt-out
mechanism or how to configure which diffs it attempts to prove — that would
require reading graphify.com's own docs, which are outside this repo's
offline mintlify cache and were not fetched (out of scope for a read-only,
primary-source-in-this-repo research pass; flagging as **not determined**).

## Q6 — `ty` LSP server, and how an agent would consume it

**`ty` (Astral, pinned via `python/pyproject.toml`'s dev group, version 0.0.76
read live) ships a real LSP server: `ty server`** (`ty server --help` →
"Start the language server", stdio transport, no flags). Confirmed via the
upstream README (`github.com/astral-sh/ty` `README.md`, fetched live):
"Language server with code navigation, completions, code actions, auto-import,
inlay hints, on-hover help, etc." The feature-support table in
`docs/features/language-server.md` (fetched live from
`raw.githubusercontent.com/astral-sh/ty/main/…`) confirms, among LSP methods:
**`callHierarchy/*` ✅, `textDocument/references` ✅, `textDocument/definition`
✅, `textDocument/rename` ✅, `typeHierarchy/*` ✅, `workspace/symbol` ✅** —
i.e. real call-hierarchy and find-references, not just type diagnostics.

**Claude Code / MCP integration path — concrete, first-party, and NOT MCP.**
Per the offline harness docs (`$CC/plugins-reference.md:195-261`, where
`$CC = knowledge-base/sources/agent-harness-docs/docs/claude-code`), Claude
Code plugins can register an LSP server directly via a `.lsp.json` file or an
inline `lspServers` block in `plugin.json` — a distinct mechanism from MCP.
Claude Code spawns the server over stdio itself (config fields: `command`,
`args`, `extensionToLanguage`, plus `env`/`initializationOptions`/`settings`/
`restartOnCrash`/`diagnostics`, etc.) and surfaces "real-time code
intelligence" — go-to-definition, find-references, diagnostics pushed into
context after edits — without the agent invoking a CLI tool call per lookup.

**This repo already has the exact plugin for `ty`, currently disabled.**
`.claude/settings.json`'s `enabledPlugins` block lists
`"astral@astral-sh": false`. It is already downloaded locally at
`~/.claude/plugins/marketplaces/astral-sh/plugins/astral/`, and its
`.claude-plugin/plugin.json` declares exactly this:

```json
"lspServers": {
  "ty": {
    "command": "uvx",
    "args": ["ty@latest", "server"],
    "extensionToLanguage": { ".py": "python", ".pyi": "python" }
  }
}
```

(That plugin also bundles `skills/ruff`, `skills/ty`, `skills/uv` — CLI-usage
skills, separate from the LSP registration.) Two OTHER LSP plugins are also
present-but-disabled for the same language class:
`"pyright-lsp@claude-plugins-official": false` and
`"pyright@claude-code-lsps": false` — both would collide with `astral`'s `ty`
registration on the `.py`/`.pyi` extensions (per the harness doc's "first
server registered wins" rule), so enabling more than one of the three
Python LSP plugins would only be useful for that first-registered one, and
which one wins depends on plugin/marketplace enumeration order — not
determined here (would need `claude --debug` to observe on this machine).

**Concretely what an agent would invoke:** nothing, directly — once
`astral@astral-sh` is enabled, Claude Code itself calls the LSP methods
(definition/references/callHierarchy/hover) as part of its own file-editing
and code-reading tool flow; there is no user-facing "run this command" step.
The `uvx ty@latest server` invocation floats to whatever `ty` version `uvx`
resolves at spawn time — **not this repo's dev-group pin** — worth flagging:
if version pinning matters here, the plugin's `args` would need
`["ty@<pinned-version>", "server"]` or a repo fork of the plugin, since the
shipped config hardcodes `@latest`.

## Ranked recommendations

Legend: **measured** = ran/read live this session; **documented** = read from
upstream source/docs but not exercised; **inferred** = reasoned from adjacent
evidence, flagged as such.

1. **Adopt: wire a `mise run graphify-affected` task.** [measured — `affected`
   exists in CLI, no task wraps it] This is the single highest-value cheap
   fix for the operator's stated goal (c) blast radius: `graphify affected`
   already does exactly what was asked, it's just not in the canonical
   task-map (`mise-tasks-only.md`), so agents don't reliably reach for it over
   a grep. Cost: near zero — same pattern as the existing `graphify-query`
   task in `mise.toml:723-730`.

2. **Adopt (with a caveat): enable `astral@astral-sh` for `ty`'s LSP call
   hierarchy / find-references.** [documented: LSP feature table + plugin
   config, both read live; NOT measured running in this session] This gives
   real code-navigation (go-to-definition, find-references, call hierarchy)
   as ambient Claude Code capability, not a manually-invoked tool — directly
   serves the operator's "understand blast radius... conserving tokens" goal,
   and is complementary to graphify (graph = pre-computed cross-file
   semantic/architectural view; ty LSP = precise, always-current
   symbol-level navigation). Caveat: it hardcodes `uvx ty@latest server`, not
   this repo's pinned dev-group version — decide whether that drift is
   acceptable or fork the plugin's `.lsp.json`. Also disable/leave off the two
   competing `pyright*` plugins (already disabled) to avoid the
   first-registered-wins ambiguity.

3. **Skip: `GRAPHIFY_HOOK_STRICT`.** [measured: real var, real mechanism] It
   would only matter if this repo used graphify's own installed
   `hook-guard` command — it deliberately doesn't (a custom
   `dotfiles-setup graphify hook-guard` wrapper exists instead, per
   `scripts/graphify-hook-guard.sh`'s own comments). Setting the env var with
   no code path reading it in this repo's wrapper would be a no-op. If the
   operator wants a hard block instead of the current advisory nudge, the
   correct lever is adding `--strict` handling to
   `python/src/dotfiles_setup/graphify.py`'s `hook_guard_main`, not the env
   var — a repo-owned decision, out of scope for this read-only pass.

4. **Skip, mostly: the other ~30 `GRAPHIFY_*` env vars.** [measured: full
   list enumerated] Nearly all are LLM-backend tuning (model overrides,
   timeouts, retries, concurrency) or export/cache internals irrelevant to
   the stated goal. Two worth a second look if extraction cost/latency ever
   becomes a problem: `GRAPHIFY_MAX_WORKERS` (AST extraction parallelism) and
   `GRAPHIFY_NO_INCREMENTAL_CACHE`/`GRAPHIFY_MTIME_GRANULARITY_MS` (cache
   correctness on this repo's filesystem) — neither is currently a known
   problem here, so leave unset until one is observed.

5. **No action needed: "Graphify Formal Verification" CI check.** [measured:
   read live via `gh api`] Already installed and running as a GitHub App;
   nothing in this repo configures it, and its "skipping" bucket in
   `gh pr checks` is a display artifact of `conclusion=neutral`, not evidence
   it isn't running. Not determined: how to tune what it attempts to prove,
   or its cost/plan — would need graphify.com's own docs (outside this
   session's primary-source scope).

6. **Optional, low priority: register graphify's MCP server (`graphify
   serve`) for `list_prs`/`triage_prs`/`get_pr_impact`.** [documented from
   source; not exercised] `get_pr_impact` genuinely answers PR-level blast
   radius (file diff → graph community/node counts), and needs only `gh`
   auth, no separate credential. But per this repo's own
   `research-doc-sources.md`/`do-not.md` doctrine (avoid MCP for our own
   tooling, prefer CLI/API), the equivalent — `graphify prs <number>` — is
   already reachable without paying the MCP schema tax. Recommend adding a
   `mise run graphify-prs` task wrapping the CLI form instead of registering
   MCP, consistent with recommendation 1's pattern, only if PR-level blast
   radius becomes a recurring need.

## What I could NOT determine

- graphify.com's (the GitHub App, distinct from the pip package) pricing,
  opt-out mechanism, or exactly which diffs qualify for the "bounded sound
  subset" it can formally verify — its own docs are outside this repo's
  offline mintlify cache and outside this task's scope (read-only,
  primary-sources-in-this-repo pass).
- Which of `astral@astral-sh` / `pyright-lsp@claude-plugins-official` /
  `pyright@claude-code-lsps` would win the `.py`/`.pyi` extension collision if
  more than one were enabled on this machine — the harness doc states
  "first server registered" wins but doesn't define registration order across
  plugins/marketplaces; would need `claude --debug` on a live session to
  observe, which this read-only research task should not do.
- Whether the concurrent version-bump lane's move to graphify 0.9.53 changes
  any of the Q1-Q4 findings — this read was against 0.9.42 (confirmed live in
  this checkout's venv at read time). Re-verify the env-var table if the
  bump changes signatures.

## GitHub repos touched

- [astral-sh/ty](https://github.com/astral-sh/ty) — README + `docs/features/language-server.md`, `docs/editors.md` fetched live to confirm the LSP feature-support table and editor integration
- [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) — the `astral` plugin's `.claude-plugin/plugin.json` (`lspServers.ty`), read from this machine's local plugin cache under `~/.claude/plugins/marketplaces/astral-sh/`
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: `.claude/settings.json`, `mise.toml`, `scripts/graphify-hook-guard.sh`, PR #880's live check-runs via `gh api`
