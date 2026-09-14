# Graphify real feature surface, from source (2026-09-13)

Read-only research lane. Objective: enumerate graphify's actual feature
surface by reading the installed package source (argparse/dispatch tables,
entry points), not `--help` — this project has previously found CLI-invisible
capabilities (a `--budget` flag was one). No installers were run, no graph was
rebuilt, no destructive/network command was executed.

## 1. Installed package identity

- **Installed**: `graphifyy` **0.9.53**, at
  `python/.venv/lib/python3.14/site-packages/graphify/` (dist-info:
  `graphifyy-0.9.53.dist-info`). Confirmed via `importlib.metadata.distributions()`
  (not a bare `pip show`, which would have read the wrong env).
- `graphify --version` → `graphify 0.9.53` (self-reports installed dist version).
- **This is what `mise run graphify-query`/`graphify-update`/`graphify-health`
  actually invoke** — `mise.toml` runs `uv run --project python dotfiles-setup
  graphify <verb>`, which imports this exact project-venv package.
- ⚠️ **Version drift confirmed, not just alleged.** `~/.config/mise/config.toml:303`
  pins the **user-global** `pypi:graphifyy` at **0.9.61** — a different, newer
  version than the 0.9.53 this repo's tasks actually run. `graphify_health`'s
  "installed runtime == pinned" check (`python/src/dotfiles_setup/graphify.py`)
  compares against 0.9.53 and is therefore checking the *right* thing for THIS
  repo's tasks — but a bare `graphify` on PATH (banned by `graphify-first.md`,
  and correctly so) would resolve 0.9.61, a version whose CLI this report never
  read. Everything below is 0.9.53's surface only.
- `python/pyproject.toml` pins `graphifyy[all]==0.9.53` with an
  `override-dependencies` note explaining the version is held back from KB's own
  pin (0.9.42) deliberately.

## 2. Method

1. Located package dir, confirmed version (above).
2. `cli.py` (4706 lines) uses **no argparse subparsers** for its command
   dispatch — `grep -c "add_parser("` → 0. It is a hand-rolled `if cmd ==
   "x": ... elif cmd == "y":` chain over `sys.argv` in `dispatch_command()`
   (`cli.py:1064`), reached from `__main__.main()` (`__main__.py:486-751`)
   after `dispatch_install_cli()` (`install.py:2058`) has first refused the
   command.
3. Enumerated every `cmd ==` / `cmd in (...)` branch in `cli.py` (30 top-level
   commands) and every entry in `install.py`'s `_PLATFORM_CONFIG` dict (21
   platform keys) and `_CLI_INSTALL_COMMANDS` frozenset (24 direct-dispatch
   command names).
4. Ran `graphify --help` (174 lines, saved at `/tmp/graphify-help-full.txt`)
   and diffed every source-found name against it by literal grep.
5. **Control arm**: grepped the help output for a freshly-invented string
   (`zzqxvbn7arm`) → 0 hits, and for the 5 confirmed-invisible command names
   together → 0 hits, then for known-present tokens (`query|extract|export`)
   → 24 hits. The probe discriminates; the absences are real, not a grep bug.

## 3. Full command table (from `cli.py` `dispatch_command`)

| Command | What it does | In `--help`? | Source |
|---|---|---|---|
| `provider` (list/show/add/remove) | manage custom LLM providers for community-naming/extraction backends | Yes (one-liner only, no per-subcmd flags in help) | `cli.py:1065` |
| `prs` | PR dashboard: CI state, review status, worktree mapping (shells to `gh`) | Yes | `cli.py:1182`, `prs.py` |
| `hook install/uninstall/status` | git post-commit/post-checkout hooks, all platforms | Yes | `cli.py:1185` |
| `query "<question>"` | BFS/DFS traversal of `graph.json`, token-budgeted answer | Yes, incl. `--budget`, `--dfs`, `--context`, `--graph` | `cli.py:1202` |
| `affected "X"` | reverse traversal (blast-radius) | Yes | `cli.py:1323` |
| `god-nodes` / `god_nodes` | most-connected nodes (architectural hubs) | Yes | `cli.py:1391` |
| `save-result` | persist a Q&A outcome to `graphify-out/memory/` for the feedback loop | Yes | `cli.py:1446` |
| `reflect` | aggregate `memory/` outcomes into `LESSONS.md` | Yes | `cli.py:1477` |
| `path "A" "B"` | shortest path between two nodes | Yes | `cli.py:1534` |
| `explain "X"` | plain-language explanation of a node + neighbors | Yes | `cli.py:1701` |
| `diagnose multigraph` | same-endpoint edge-collapse risk report | Yes, fully | `cli.py:1835` |
| `add <url>` | fetch a URL, save to `./raw`, update graph | Yes | `cli.py:1929` |
| `watch <path>` | rebuild graph on file changes | Yes | `cli.py:1964` |
| `cluster-only <path>` | rerun clustering on existing `graph.json` | Yes | `cli.py:1977` |
| `label <path>` | (re)name communities via LLM backend | Yes | `cli.py:1977` (`force_relabel` branch) |
| `update <path>` | re-extract + update graph, no LLM | Yes | `cli.py:2385` |
| **`hook-check`** | **no-op, exit 0** — cross-platform PreToolUse shim so Codex Desktop (which rejects `additionalContext`) never breaks Bash calls | **No** | `cli.py:2445` |
| **`hook-guard [read\|write] [--strict]`** | shell-agnostic PreToolUse guard: prints an `additionalContext` nudge toward graphify when a fresh graph exists; `--strict` blocks the first raw read/session via `permissionDecision: deny` | **No** | `cli.py:2450`, `__main__.py:274-321` |
| `check-update <path>` | check `needs_update` flag, cron-safe notify | Yes | `cli.py:2462` |
| `tree` | D3 v7 collapsible-tree HTML | Yes | `cli.py:2470` |
| `merge-driver <base> <cur> <other>` | git merge driver for `graph.json` (union-merge) | Yes | `cli.py:2533` |
| `merge-graphs <g1> <g2>...` | merge multiple graphs into a cross-repo graph | Yes | `cli.py:2588` |
| `clone <github-url>` | clone a repo locally, print its path (**network**) | Yes | `cli.py:2734` |
| `export html\|callflow-html\|obsidian\|wiki\|svg\|graphml\|neo4j\|falkordb` | 8 export formats, 2 with `--push` to a live graph DB | Yes | `cli.py:2758` |
| `benchmark [graph.json]` | measure token reduction vs naive full-corpus approach | Yes | `cli.py:3065` |
| `global add/remove/list/path` | manage `~/.graphify/global-graph.json` (**writes outside repo/home**) | Yes | `cli.py:3082` |
| `extract <path>` | full headless extraction (AST + semantic LLM) — the "full run" command | Yes, extensively | `cli.py:3138` |
| **`cache-check <files_from> [--root] [--mode\|--deep] [--prompt-file]`** | reads a file list, checks the semantic cache (`cache/semantic/` or `cache/semantic-deep/`), writes `.graphify_cached.json` + `.graphify_uncached.txt` | **No** | `cli.py:4513` |
| **`merge-chunks <files...> --out <path>`** | concatenate `.graphify_chunk_*.json` fragments written by semantic subagents, dedup by node id, validates each chunk (`load_validated_semantic_fragment`) and fails closed if none valid | **No** | `cli.py:4573` |
| **`merge-semantic --cached <p> --new <p> --out <p>`** | merge cached + freshly-extracted semantic fragments, cached wins on id collision | **No** | `cli.py:4654` |
| *(bare path)* `graphify <path>` | re-enters as `graphify extract <path>` (documented as a README convenience, e.g. `graphify .`) | Implied, not itemized | `cli.py:4696` |

**30 top-level commands total; 5 are absent from `--help` anywhere** (`hook-check`,
`hook-guard`, `cache-check`, `merge-chunks`, `merge-semantic`). All 5 read as
**internal plumbing** for the incremental-extraction pipeline and the
installed hook JSON (`hook-check`/`hook-guard` are literally what the
installed `PreToolUse` hook's `"command"` field invokes — see
`_CODEX_HOOK` in `__main__.py:391-408` — not commands an interactive user is
expected to type), not hidden user-facing features. They are still real,
runnable, and worth knowing about if you're debugging the hook wiring or a
partial/incremental `extract` run.

## 4. Install-platform surface — a second, independent CLI-invisible set

Comparing `install.py`'s `_PLATFORM_CONFIG` dict (21 keys) against every
`--platform` value and per-platform bullet the `--help` text prints:

| Platform key | In the `--platform (...)` summary line? | Has its own `"<platform> install"` bullet? | Direct `graphify <platform> install` subcommand? (`_CLI_INSTALL_COMMANDS`) |
|---|---|---|---|
| claude, codex, opencode, aider, claw, droid, trae, trae-cn, hermes, kiro, pi, codebuddy, antigravity, devin | Yes | Yes | Yes |
| kilo | No | Yes | Yes |
| copilot | No | Yes | Yes |
| amp, agents | Yes (summary line) | No explicit bullet | Yes |
| windows | Yes (summary line) | No explicit bullet | **No** (not in `_CLI_INSTALL_COMMANDS`; only reachable via `graphify install --platform windows`) |
| **kimi** | **No** | **No** | **No** |
| **antigravity-windows** | **No** | **No** | **No** |

`kimi` and `antigravity-windows` are **completely absent from `--help`
output** — not in the summary line, not an explicit bullet, and not a direct
subcommand. They exist and are live: `dispatch_install_cli`'s generic
`install` handler (`install.py:2058-2119`) accepts any platform name via
`graphify install --platform <name>` and looks it up in `_PLATFORM_CONFIG` —
so `graphify install --platform kimi` and `graphify install --platform
antigravity-windows` work today, silently. (Not run — this is a read of the
dispatch code path, not an executed install.)

`_PLATFORM_ALIASES = {"skills": "agents"}` (`install.py:482`) is a further
undocumented alias: `graphify skills install` == `graphify agents install`.
`"skills"` is in `_CLI_INSTALL_COMMANDS` so it dispatches directly.

**Control arm for this section**: grepped `/tmp/graphify-help-full.txt` for
`antigravity-windows` and `kimi install` → 0 hits each; grepped for a platform
known to be documented (`cursor install`) → present. The gap is real.

## 5. MCP server — a third surface entirely outside the CLI

`entry_points.txt` declares **two console scripts**, not one:

```
graphify = graphify.__main__:main
graphify-mcp = graphify.serve:_main
```

`graphify-mcp` (or `python -m graphify.serve`) starts an MCP server
(`graphify/serve.py`, argparse-based, `_main()` at `serve.py:2351`) with its
own flags: `graph_path` positional / `--graph`, `--transport {stdio,http}`,
`--host`, `--port`, `--api-key` (env `GRAPHIFY_API_KEY`), `--path` (HTTP mount,
default `/mcp`), `--json-response`, `--stateless`, `--session-timeout` (default
3600s). **None of this appears in `graphify --help`** — it's a wholly separate
entry point, discoverable only by reading `entry_points.txt` or the source.

The server exposes **9 MCP tools** (`serve.py:1543` `_build_server`, `types.Tool`
calls at lines 1616-1730): `query_graph`, `get_node`, `get_neighbors`,
`get_community`, `god_nodes`, `graph_stats`, `shortest_path`, `list_prs`,
`get_pr_impact`, `triage_prs` — and **6 MCP resources**
(`graphify://report`, `graphify://stats`, `graphify://god-nodes`,
`graphify://surprises`, `graphify://audit`, `graphify://questions`).

This server is **not currently registered anywhere in this repo** —
`.mcp.json` is empty (per prior project memory,
`project_mcp_json_exception.md`), and nothing in `mise.toml` invokes
`graphify-mcp`/`graphify.serve`. It is dormant, reachable, undocumented
capability: registering it would put graph-query tools directly in an agent's
MCP tool list instead of behind the `mise run graphify-query` CLI wrapper —
a decision for the operator, not something to wire up here
(`.claude/rules/research-doc-sources.md` "MCP: two lanes" — this would be our
own tooling, lane 2, so the CLI/API path stays preferred unless a concrete
need argues otherwise).

## 6. Commands relevant to a full run over this repo

| Command | Inputs | Outputs / where they land | Cost/budget knobs | Network / destructive? |
|---|---|---|---|---|
| `extract <path>` | source tree at `<path>` | `<path>/graphify-out/graph.json` + `.graphify_manifest.json`, `cache/semantic/` (or `semantic-deep/`) entries, `GRAPH_REPORT.md` (via the auto-suggested follow-up) | `--token-budget` (default 60000/chunk), `--max-concurrency` (default 4), `--api-timeout` (default 600s), `--max-workers` (default cpu_count); **no total-cost cap flag exists** — budget/concurrency bound per-call size and parallelism, not spend | **Yes — network.** Calls an LLM backend (`gemini\|kimi\|claude\|openai\|deepseek\|ollama`, chosen by whichever API key is set, or `--backend`); `--postgres DSN` connects to a **live Postgres database**; `--google-workspace` exports `.gdoc/.gsheet/.gslides` via `gws` (network); `--cargo` is local-only |
| `cluster-only <path>` / `label <path>` | existing `graphify-out/graph.json` | rewrites `graph.json`'s community labels, regenerates `GRAPH_REPORT.md` | `--max-concurrency` (default 4, forced to 1 for ollama/claude-cli), `--batch-size` (default 100) | Network for community-naming LLM calls (`--backend`/`--model`), local otherwise |
| `update <path>` | existing graph + changed files | rewrites `graph.json` (AST-only re-extraction, **no LLM**) | none needed | Local only; `--force` overwrites even on a node-count regression |
| `reflect` | `graphify-out/memory/*.json` (from `save-result`) | `graphify-out/reflections/LESSONS.md` | none | Local only |
| `diagnose multigraph` | existing `graph.json` | stdout report or `--json` | none | Local, read-only |
| `benchmark [graph.json]` | existing graph | stdout metrics | none | Local, read-only |
| `merge-graphs` / `merge-driver` / `merge-chunks` / `merge-semantic` | multiple `graph.json`/chunk files | a merged output path (`--out`) | none | Local, but `merge-chunks`/`merge-semantic` are the internal fan-in for a parallelized `extract` — running one by hand only makes sense mid-debug |
| `export neo4j\|falkordb --push <URI>` | existing graph | writes Cypher to a **live graph database** over the network (`--user`/`--password` or `NEO4J_PASSWORD`/`FALKORDB_PASSWORD` env) | none | **Yes — network write to an external database** |
| `global add/remove` | a project `graph.json` | **`~/.graphify/global-graph.json`, outside the repo and outside any per-project sandbox** | none | Local disk write outside the repo tree — flagged per the operator's ask |
| `clone <url>` | a GitHub URL | `~/.graphify/repos/<owner>/<repo>` (or `--out <dir>`) | none | **Yes — network clone** |
| `add <url>` | a URL | `./raw/` + graph update | none | **Yes — network fetch** |
| `watch <path>` | a directory | continuously rebuilds the graph on change | none | Local, but long-running/backgroundable — mind `long-running-command-hangs.md` if ever run directly (not via a mise task) |
| `hook install` | — | writes git `post-commit`/`post-checkout` hooks + (per platform) `PreToolUse` hook JSON into `.claude/settings.json`-equivalent locations | none | Local write, mutates git hook files and agent-platform config — this is exactly the class `do-not.md` #8 already bans for `graphify install`/`<platform> install`; `hook install`/`hook-guard --strict` deserve the same caution even though they weren't named in that rule |

**No flag anywhere caps total LLM spend across an `extract` run.** The
operator set no cost bound; the closest levers are `--token-budget` (per-chunk
cap), `--max-concurrency` (parallelism, hence rate of spend), and choosing a
cheaper `--backend`/`--model`. A full run over this repo's size should budget
based on chunk count × `--token-budget`, not assume a silent ceiling exists.

## 7. Python API / exporters beyond CLI + MCP

`graphify/exporters/` is a small internal plugin set
(`base.py`, `html.py`, `graphdb.py`) backing the `export` subcommand — not a
documented public API, but importable (`from graphify.exporters import ...`)
by anything running in the same venv. `graphify/global_graph.py`,
`graphify/cross_repo_types.py`, `graphify/manifest.py`, `graphify/report.py`
are similarly internal modules with no `__all__`/public-API markers found —
treat any direct import beyond the two console scripts as unsupported,
version-fragile surface, not a stable API.

## 8. Summary — what's genuinely CLI-invisible

1. **5 top-level commands**: `hook-check`, `hook-guard`, `cache-check`,
   `merge-chunks`, `merge-semantic` — internal plumbing, safe to ignore for
   interactive use, useful to know when debugging hooks or an interrupted
   incremental `extract`.
2. **2 install platforms**: `kimi`, `antigravity-windows` — live via
   `graphify install --platform <name>`, invisible in every `--help` surface.
3. **1 alias**: `skills` → `agents` platform.
4. **A second console script + MCP server** (`graphify-mcp` / `python -m
   graphify.serve`, 9 tools + 6 resources) that `graphify --help` says
   nothing about at all — the biggest single invisible surface, and currently
   unregistered/dormant in this repo.
5. **Version drift**: the CLI actually driving `mise run graphify-*` is
   0.9.53, one version below the user-global mise pin (0.9.61) — everything
   above is 0.9.53's surface specifically, and would need re-verification
   against 0.9.61 before that pin is ever allowed to reach this repo's tasks.

None of the CLI-invisible commands found here are secretly powerful hidden
features (no undocumented `--budget`-class knob turned up beyond what
`--help` already lists for `query`/`extract`); the gap is entirely in
**plumbing commands and install targets**, not in withheld end-user
capability. The one exception worth flagging to the operator is item 4 — the
MCP server is a real, separate, fully-documented-in-source capability that
`--help` never mentions.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the package whose installed 0.9.53 source (CLI dispatch, install platforms, MCP server) this report enumerates.
