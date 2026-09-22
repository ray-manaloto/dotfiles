# graphify feature inventory for deep-extracting planning-with-files into the KB

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message (its own Write was refused by the harness). Everything
> was read-only: no graphify build or update ran, and no repo file changed. Scratch
> evidence is in the session scratchpad. HTML entities introduced in transit restored.

## 0. The pin: what the KB actually runs (checked 2026-09-22)

| Fact | Value | Evidence |
|---|---|---|
| Declared pin | `graphifyy[all]==0.9.57` | KB `pyproject.toml:32` |
| Where it installs from | fork `ray-manaloto/graphify`, rev `3c9b930f386f80c393fe658e1afb685030828c6a` | `pyproject.toml:303`, `uv.lock:656-658` |
| What the installed package reports | 0.9.57, `direct_url.json` commit_id `3c9b930f…` | `uv run python -c "…distribution('graphifyy')…"` |
| Vendored clone | HEAD `3c9b930f…`, same as the manifest `commit` | `git -C sources/graphify rev-parse HEAD`; `sources/graphify.manifest` |
| Upstream | `Graphify-Labs/graphify`; its default branch is `v8` | `currency.toml:21`; manifest comment |
| Latest upstream | **v0.9.65** (2026-09-20) on both PyPI and GitHub. The KB is **8 releases behind** (0.9.58 to 0.9.65). | `gh api repos/Graphify-Labs/graphify/releases`; PyPI JSON |
| Why the fork exists | the `openai-cli` backend (fork patch). Upstream PR #3073 is still **OPEN** (`merged=false`), so moving the pin means a fork rebase. | `gh api …/pulls/3073` |
| `sources/graphify.dispositions.json` | Not a feature catalog. It lists 20 file-detection dispositions (11 unsupported-file, 5 zero-node-file, 3 excluded-ast-fixture, 1 compatibility-correction), checked by `kb-graphify-catalog`. | parsed JSON; `mise.toml:1141-1161` |

The CLI help (`uv run graphify --help`, rc 0, 177 lines) is saved at `scratchpad/gh-help.txt`.

## 1. Feature inventory at the pinned 0.9.57, with KB exposure

Citations are file:line in `knowledge-base/sources/graphify/graphify/`, the pinned clone, unless noted.

### 1a. Extraction

| Feature | What it does | Citation | KB exposure |
|---|---|---|---|
| **AST structural pass** (tree-sitter) | Code files become nodes and edges. Local, free. Covers `.py .ts .mjs .sh .bash .ps1 .json` and many more. | `detect.py:44` CODE_EXTENSIONS; `extract.py:5693-5769` | **Yes**: `kb-build` runs `graphify extract sources/<name> --code-only --force` (`kb_setup/graph.py:986-988`) |
| **`--code-only`** | Skips every doc, paper and image file, and prints the skip count | `cli.py:3620-3632` | Always on in `kb-build` |
| **Markdown quick-scan** (structural, no LLM) | Headings, links and file nodes for `.md/.mdx/.qmd/.skill`. Runs inside `update` and `watch`. | `extract.py:5756-5759`; `watch.py:1447-1452`; `build.py:770` | **Partly.** `kb-update` (`graph.py:3607`, `graphify update`) reaches it; `kb-build` does not (see gap G1) |
| **Semantic extraction, skill path** | Host-agent subagents read docs, papers and images and write JSON chunks | `skill.md:151-260`; `skills/claude/references/extraction-spec.md` | **Yes, but with the KB's own prompt**: `.claude/workflows/kb-extract.js`, then `kb-validate-chunks`, `kb-assemble`, `kb-merge`. The prompt differs from upstream (G2). |
| **Semantic extraction, headless** `extract --backend B` | `extract_corpus_parallel`, with chunking, token budget and adaptive retry | `cli.py:3222-3440`; `llm.py:101-236` BACKENDS | **Yes, only on a side tree**: `kb-graphify-native-extract` (G3) |
| **`--mode deep`** | More aggressive INFERRED edges; uses its own `cache/semantic-deep/` namespace | `cli.py:3413-3425, 3633`; `extraction-spec.md:29-30` | Native-extract only (`graphify_native_extract.py:476-481`) |
| Backends | claude, kimi, ollama, gemini, openai, deepseek, azure, bedrock, **claude-cli**, **openai-cli** (fork only) | `llm.py:102-236` | Explicit `--backend claude-cli` (default) or `openai-cli` (`graphify_native_extract.py:298`). `clean_env()` strips the other key triggers. |
| `--token-budget` (60k default), `--max-concurrency`, `--api-timeout`, `--max-workers` | Tuning knobs | help lines 102-105 | native-extract passes the first two (`:483-486`) |
| `--dedup-llm` / `--no-dedup` | LLM tie-break during entity dedup / dedup off | `cli.py:3260, 3343-3412` | **No** |
| `--exclude <glob>` (not in `--help`) | Path excludes, saved as build excludes | `cli.py:3381-3384, 3456` | **No** (G4) |
| `--no-gitignore`, and `.graphifyignore` handling | Ignore control | help line 108; `detect.py:987-1183` | No flag. `source_groups.py:469-477` has a graphifyignore policy, but only for the ecosystem registry. |
| `--postgres DSN`, `--cargo`, `--google-workspace` | Schema, crate and Workspace ingestion | help 107-115 | No (not applicable here) |
| `--directed` | DiGraph build | `skill.md:20`; `cli.py:1570+` | No |
| `--allow-partial`, `--timing`, `--force` | Shrink guard override, per-stage timings, full re-scan | `cli.py:109, 215, 635-652, 3236` | `--force` yes (kb-build); the other two no |
| **Hyperedges** (3 or more nodes, at most 3 per chunk) | Group relations | `extraction-spec.md:38-42` | **Yes**: `kb-extract.js:189-231`; `hyperedges.py`; `assert_composition` |
| `semantically_similar_to` edges, AMBIGUOUS tier, discrete INFERRED rubric (0.95/0.85/0.75/0.65/0.55, "never 0.5") | Edge quality contract | `extraction-spec.md:13-15, 32-58` | **No**: `kb-extract.js:170` says "0.5 for INFERRED" (G2) |
| Semantic cache with prompt fingerprint | Re-extraction is cheap and prompt-attributed | `skill.md` Step B0; `cli.py:4680-4690` `cache-check` | **No** for the host-agent path (G2) |
| `merge-chunks`, `merge-semantic`, `cache-check` (not in `--help`) | Plumbing for the skill path | `cli.py:4680, 4740, 4821` | No. The KB uses `kb-assemble` and `_merge_docs.py` (via `build_merge`) instead. |
| Video and audio: `add <yt-url>` plus faster-whisper `transcribe` | Local transcription | `transcribe.py`; `skill.md:147` | **Yes**: `kb-add`, `kb-transcribe` (`mise.toml:1348-1354`) |
| `add <url>` | Fetches into `./raw` with frontmatter | help 27-30 | **Yes**: `kb-add`. The KB prefers `kb-fetch` because `add` truncates at 12,000 chars (`mise.toml:1320-1326`). |

### 1b. Graph build, clustering, labeling

| Feature | Citation | KB exposure |
|---|---|---|
| `build_merge` (N-ary, replace-on-re-extract, `ast_sources`) | `graphify_sdk.py` PublicSymbol (KB) | Yes: `_merge_docs.py`, `kb-merge`, `kb-build` |
| `merge-graphs` (cross-repo, no dedup) | help 23-24 | Yes, internally (`graph.py:2856`); the guard redirects raw use |
| `cluster-only` (Leiden, falling back to Louvain on py3.14), `--no-viz`, `--no-label` | help 39-46 | Yes: `kb-label` / `kb-artifacts` report (`artifacts.py:22`) / study graph |
| `cluster-only --resolution`, `--exclude-hubs`, `--min-community-size` (not in `--help`) | `cli.py:2050-2083`; upstream README | **No** |
| `label` (LLM naming, `--missing-only`, `--backend`, `--batch-size`) | help 47-52 | Yes: `kb-label`. Deterministic hub labels by default; `--claude-cli` is opt-in. |
| Analysis sidecar (god nodes, surprises, suggested questions, cohesion) | `.graphify_analysis.json` | Yes: `kb-insights` (`mise.toml:975-988`) |

### 1c. Query, memory, exports, server

| Feature | Citation | KB exposure |
|---|---|---|
| `query` (BFS/DFS, `--budget`, `--context`) | help 53-57 | Yes: `kb-query` (plus the KB's own `--prose` and `--idf`) |
| `path`, `explain`, `god-nodes`, `diagnose multigraph` | help 7-20, 62-65 | Allowed as raw read-only commands (`kb_setup/hook_guard.py:91-100`) |
| `affected` (reverse traversal) | help 58-61 | Yes: `kb-affected` |
| `save-result` (with `--outcome` and `--correction`) | help 67-74 | Yes: `kb-remember` |
| `reflect` (`--half-life-days`, `--min-corroboration`, `--if-stale`, `--analysis/--labels`) | help 75-82; `cli.py:1508` | **Partly**: `kb-reflect` passes only `--graph` (`mise.toml:1387`) |
| Exports: `export html/callflow-html/obsidian/wiki/svg/graphml/neo4j/falkordb`, plus `tree` | help 84-90, 124-135 | Yes via `kb-artifacts` (`artifacts.py:21-30`): report and html, tree, callflow, graphml, cypher, wiki, obsidian, svg. svg is skipped above 5,000 nodes. `neo4j --push`, `falkordb` and `export html --node-limit` are not wrapped. |
| **MCP server** (`graphify-mcp` = `graphify.serve:_main`): stdio or streamable-http. 10 tools: `query_graph, get_node, get_neighbors, get_community, god_nodes, graph_stats, shortest_path, list_prs, get_pr_impact, triage_prs`. 6 resources: `graphify://report, stats, god-nodes, surprises, audit, questions`. All read-only; there is **no add/write tool**. | `serve.py:1695-1813, 2094-2099, 2223-2426`; `pyproject.toml:106` | Yes: `kb-serve` (optional tool/resource allowlist relay), plus `kb-serve-memory` as a separate server |
| `benchmark`, `global add/remove/list/path`, `check-update`, `provider`, `prs`, `clone`, `merge-driver` | help 21-26, 66, 83, 117-123 | **No** (`clone` is used internally by kb-build) |
| `watch`, `hook install`, `install`, platform installers (`claude install` and so on), `hook-check`/`hook-guard` | help 4-6, 31-34, 136-176; `cli.py:2503-2508` | **Deliberately banned** (`hook_guard.py:84-89`; KB `do-not.md`) |

## 2. What applies to planning-with-files, and the exact KB task sequence

**The source, measured.** `OthmanAdi/planning-with-files`, default branch `master`, pushed 2026-09-22T17:51Z, 27,070 stars, MIT, 732 blobs:
- 206 `.sh`, 196 `.md`, 142 `.py`, 123 `.ps1`, 21 `.json`, 17 `.ts`, 5 `.yml`, 5 `.svg`, 3 `.png`, 1 `.mp4`, plus `.webp/.jpg/.gif/.html/.prompt/.mjs`.
- 18 copies of `SKILL.md`: 12 platform mirrors (`.pi .codex .cursor .opencode .agents .hermes .gemini .factory .codebuddy .mastracode .continue .kiro`), 5 i18n variants, and 1 canonical `skills/planning-with-files/SKILL.md`.
- It is not in the KB yet: `git ls-files sources | grep -ic planning` returned 0. Control: `mattpocock-skills.manifest` found by the same kind of grep.

**Coverage by feature**
- **AST covers the code layer for free.** All of `.sh .py .ps1 .ts .json .mjs` are AST-supported (`detect.py:44`, `extract.py:2558-2559, 5693-5769`).
- **The hooks are not code files.** Claude Code's five lifecycle hooks (UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact) are inline shell inside the SKILL.md YAML frontmatter, according to the upstream README (via exa) and `.codebuddy/skills/…/SKILL.md`. No AST or markdown quick-scan reads that frontmatter shell. Only semantic extraction can capture the hook logic. This is my inference and I did not probe it.
- **Markdown, images and the one mp4 need the semantic/media path.**
- **Hyperedges fit naturally.** The 3-file pattern (`task_plan.md`, `findings.md`, `progress.md`) and the hook lifecycle are both cases where 3 or more nodes form one flow.

**Sequence.** Every step is a KB mise task. "FREE" means AST or deterministic; "TOKENS" means an LLM call.

1. `mise run kb-recall-work -- "planning-with-files"` (FREE). Phase 0: check for prior work.
2. `mise run graph-size` (FREE). **Measured today: 721.2 MiB of 1,024 MiB (70%), 302.8 MiB headroom, OK.**
3. Add a row to `sources/REGISTRY.md` (a hand edit, per kb-curator step 1). Tier T1.
4. `mise run kb-manifest-add -- https://github.com/OthmanAdi/planning-with-files --name planning-with-files --kind code` (FREE). Pins upstream HEAD. `scope` defaults to `corpus`; `study` would divert it to `study-graph.json` (`manifest.py:36-45, 159-163`).
5. `mise run kb-detect-census` (FREE, read-only). Look for unclassified files (`.prompt`, `.mp4`, images).
6. `mise run kb-build` (FREE, but slow: 180 min timeout, re-clones every manifest). Runs `extract --code-only --force` on the new clone, replays committed doc chunks, and ends with a deterministic `kb-label`. It **will not index the 196 `.md` files** (see G1).
7. **Prose (TOKENS, Claude host agent).** Invoke the saved `kb-extract` Workflow with `{scratchDir, capturedAt: "2026-09-22", sources:[…]}`. I recommend passing only the canonical doc set (root README, `docs/`, `skills/planning-with-files/**`, `commands/`, `templates/`, `MIGRATION.md`) rather than all 18 SKILL.md copies. That subset is my recommendation, not a measurement. Then:
   - `mise run kb-validate-chunks -- <scratch>/*.json`
   - `mise run kb-assemble -- planning-with-files <scratch>/*.json`, which writes `sources/extractions/planning-with-files-docs.json`
   - `mise run kb-merge -- sources/extractions/planning-with-files-docs.json`

   Every node must carry `_origin: "semantic"`, and ids must be prefixed with the source key (`kb-curator/SKILL.md`; `kb-extract.js:155-160`). Images go through the same workflow; the host agent reads them with vision.
8. **Media.** The single `.mp4`: `mise run kb-transcribe -- <file>`, then host-agent extract the transcript. **UNVERIFIED** whether `kb-transcribe` accepts an mp4 directly. The task is documented for `raw/yt_*.m4a` (`mise.toml:1349-1352`).
9. `mise run kb-label` (FREE). Deterministic hub labels. Relabel after every merge, because Louvain renumbers communities.
10. **Optional deep side graph (TOKENS, subscription-billed).**
    - `mise run kb-graphify-native-extract -- --target sources/planning-with-files --dry-run`
    - then the same command without `--dry-run`, which runs `graphify extract … --mode deep --backend claude-cli`
    - `claude-cli` is priced at 0.0 in the backends table because it bills to the plan (`llm.py:209-220`). Default model is `claude-opus-5` (`graphify_native_extract.py:271`). Runs serially unless `--allow-parallel-claude-cli`.
    - Then `-- --cluster` and `-- --artifacts`.
    - Output goes to `.agent/kb/native-extract`, **not the aggregate graph** (see G3). For scale: graphify's own corpus took 19 chunks and produced 13,442 nodes (`graphify_native_extract.py:113-118`).
11. `mise run kb-artifacts` (FREE, 60 min timeout). Report, tree, callflow, graphml, cypher, wiki, obsidian. svg is skipped at this graph size.
12. **Verify (FREE).**
    - `mise run kb-insights`
    - `mise run kb-query -- --prose "…"` and `-- --idf "…"`
    - `mise run kb-affected -- "<symbol>"`
    - raw read-only `graphify path/explain/god-nodes/diagnose multigraph`
13. **Self-learn (FREE).** `mise run kb-remember -- --question … --answer-file … --outcome …`, then `mise run kb-reflect`.
14. **Gates.** `mise run kb-manifest-audit`, `mise run lint`, `mise run test` (or `kb-gates`), then `mise run kb-ship`.

**Constraints**
- **Backend rule has moved.** Your brief says "Claude-only, never Gemini". KB `CLAUDE.md:66-72` (Ray, 2026-08-25) now reads "`claude-cli` **or** `openai-cli`, chosen by an EXPLICIT `--backend`". Gemini and every auto-detected key are still forbidden: `clean_env()` strips Gemini, Google, OpenAI, Kimi, DeepSeek, Azure, Bedrock (`AWS_REGION`) and Ollama triggers. `kb-curator/SKILL.md` still says the host-agent Workflow is "the ONLY LLM path".
- **#2076 status is stale.** Upstream closed #2076 as *completed* on 2026-07-22 ("Fixed in v0.9.24 (#2095)… pins a JSON schema"). But that fix applies to the **extraction** call: `_call_claude_cli` passes `--json-schema` at `llm.py:1832`. The **labeling** call (`_call_llm`'s `claude-cli` branch, `llm.py:3288-3302`) does **not** pass `--json-schema`. It relies on `_parse_label_response`, which salvages a brace-extracted object or regex-matched pairs (`llm.py:3655-3689`, #1690). So "broken for labeling" is **UNVERIFIED either way at 0.9.57**. The only decisive test is a live `mise run kb-label -- --claude-cli`, which spends tokens and rewrites `graph.json`; that is your call. The deterministic labeler stays the safe default.
- **Graph ceiling.** A 1 GiB cap with 302.8 MiB headroom. `kb-curator` says do not raise the cap again (#130, #120).

## 3. Gaps: graphify features the KB does not use or wrap

- **G1. `kb-build` misses the free markdown structure layer. Measured.** The `sources/graphify` subgraph that `kb-build` produced has **0 nodes whose `source_file` ends in `.md`** and 11,232 `.py` nodes (control), even though the clone tracks 363 `.md` files. The cause: `--code-only` drops every doc file (`cli.py:3620-3632`). Meanwhile `graphify update`, which `kb-update` calls at `graph.py:3607`, routes through `_rebuild_code`, and that function includes markdown files in its quick-scan (`watch.py:1447-1452`, confirmed at `cli.py:2479-2485`). So the same source can gain or lose free markdown heading/link nodes depending on which KB task last ran. Whether a kb-update'd source actually shows md nodes is **UNVERIFIED**; I did not probe one.
- **G2. The KB's extraction prompt diverges from upstream's `extraction-spec.md`.**
  - `file_type` is always `"concept"`; upstream allows six values including `document` and `rationale`.
  - `confidence_score` is 0.5 for INFERRED (`kb-extract.js:170, 215`). Upstream says "never 0.5" and uses a discrete rubric.
  - No AMBIGUOUS-edge guidance, no `semantically_similar_to`, and no DEEP_MODE switch (0 matches for `deep` and for `semantically_similar` in `kb-extract.js`; control: `hyperedge` matches the same file).
  - Node ids use a `<key>_` prefix. Upstream requires path-stem ids that "must match the ID the AST extractor generates" (`extraction-spec.md:~62`). With the prefix, doc nodes cannot join AST nodes for the same file. For planning-with-files that costs the SKILL.md-prose to `scripts/*.sh` / `*.py` links.
  - No use of graphify's prompt-fingerprinted semantic cache (`check_semantic_cache(..., prompt_file=...)`, `skill.md` Step B0), so re-extraction is always full price.
- **G3. Native deep extraction never reaches the aggregate.** "It does not touch the aggregate `graphify-out/graph.json`… Merging… is a separate, later decision" (`graphify_native_extract.py:120-126`). The SDK route (`extract_corpus_parallel`) is pinned but has no caller (`:61-67`).
- **G4. No path-exclude field in manifests**, although `extract --exclude` exists (`cli.py:3381-3384`). For planning-with-files, the 12 platform-mirror directories plus the i18n copies will duplicate AST nodes. The only KB-side options today are the whole-source `build = skip|defer` states.
- **G5. Commands and flags the KB does not wrap:**
  - `cluster-only --resolution / --exclude-hubs / --min-community-size`
  - `reflect --half-life-days / --min-corroboration / --if-stale`
  - `extract --directed / --dedup-llm / --timing`
  - `export neo4j --push`, `export falkordb`, `export html --node-limit`
  - `benchmark`, `global`, `check-update`, `prs` (dotfiles has `graphify-prs`; the KB has nothing), `provider`
  - MCP `--transport http` is only mentioned in a `kb-serve` comment
- **G6. Version drift: 8 releases, blocked on the fork rebase (#3073 still open).** Fixes in 0.9.58 to 0.9.65 that matter for this repo:
  - #3416 (0.9.58): a shell script run through a variable path (`"$SCRIPT_DIR/foo.sh"`) now resolves. Planning-with-files has 206 `.sh`.
  - #3430 (0.9.58): bare-name imports between sibling files in a flat script dir now resolve.
  - #3472 (0.9.58): `rationale` survives incremental rebuilds.
  - #3475 (0.9.58): labeling finds the `claude` CLI at run time.
  - #3477 (0.9.59): incremental rebuilds keep cross-file `concept` nodes.
  - #3511 (0.9.60): unclassified files are surfaced instead of silently dropped.
  - **#3562 (0.9.62): a markdown code span now emits a `references` edge to the symbol it names.** This is free doc-to-code linking. Absent at the pin: 0 code-span matches in `extractors/markdown.py`; control: `references` matches 6 times in the same file.
  - #3587 (0.9.63): those code-span edges survive incremental rebuilds.
  - #3655 (0.9.64): incremental markdown-family link reconciliation, including `.skill`.
- **G7. Stale KB prose.**
  - `kb-curator/SKILL.md` says `reflect --if-stale` and `extract --dedup-llm` are "Version-gated (0.9.24+, not in installed 0.9.23)"; both exist at 0.9.57 (`cli.py:1508, 3343`).
  - It says "graphify's only non-Gemini LLM backend is `claude-cli`", which is false (`llm.py:102-236`).
  - Its "BROKEN (#2076)" claim, and the one in `mise.toml:1339-1346`, need the nuance from section 2.
- **G8. Open upstream bug that affects the deep side graph.** #3189 (OPEN): "Deep-mode hyperedge formation is non-deterministic even under a full semantic-cache hit". So step 10 cannot be reproduced byte-for-byte.

## 4. What the external research tools surfaced

| Tool | Result | Relevance |
|---|---|---|
| **Context7** (`find-docs` skill, `ctx7` 0.5.11) | Resolved `/graphify-labs/graphify` (3,040 snippets, Medium reputation). README (v8) lists every extract backend including `bedrock`, `claude-cli`, `azure`; `--dedup-llm`; `--global --as`; `--timing`; `--no-gitignore` still honoring `.graphifyignore`. `watch.py` reconciles markdown links into deterministic doc-to-code `references` edges. | Confirms G1, G5 and the backend list |
| **Exa** (`exa:search`, handled directly) | Current `Graphify-Labs/graphify` README (2026-09-21): `cluster-only --resolution/--exclude-hubs`, `graphify prs --triage/--conflicts`, MCP `--transport http`, "Leiden, with LLM-free labels". `docs/how-it-works.md` has the INFERRED 0.95…0.55 rubric. Microsoft `hve-core` wraps graphify pinned at 0.5.4 (stale). planning-with-files README: 5 Claude Code hooks registered in SKILL.md frontmatter; v3.0.0 autonomous/gated modes and JSONL run ledger; `.planning/<slug>/` plus `.active_plan`. | Confirms the G2 rubric divergence and pwf structure |
| **last30days** (v3.25.0; engine rc 0 with `--plan` and `--github-repo`) | 39 items from 6 sources, 2026-08-23 to 2026-09-22. GitHub: Graphify-Labs/graphify has 120,475 stars and 1,453 open issues. YouTube demos claim about 40% token cost versus Explore agents (Chase AI transcript). HN "Show HN: Graphify C#" is a different project (zachsaw). No community discussion of deep mode, labeling or hyperedges; planning-with-files showed up only as its GitHub item. **The web lane failed with HTTP 422**, so coverage is partial. The first attempt failed because `timeout` is an unconfigured mise shim here (`mise ERROR No version is set for shim: timeout`). Raw output saved to `scratchpad/last30days/`. | Low signal; no new bugs |
| **Firecrawl developer index** (skill loaded; raw `curl` was permission-denied, so I used the `firecrawl developer` CLI) | #2076 (closed); **#3189 open**; **#1430 closed 2026-06-22** (the native prompt now asks for hyperedges); #2554 closed 2026-08-08 (claude-cli error text no longer lands as a community label); #1894 closed 2026-07-15 (deep-mode cache namespace); **#1710 open** (RFC for a native semantic-layer `update`). The index still keys the repo as `safishamsi/graphify`, the old owner. | Status checked with `gh api` for each |
| **Firecrawl search** (skill; 2 searches, feedback sent rc 0) | Reviews (kevinkinnett.com, wavect.io, augmentcode "v0.9.28 strict mode"), graphify.net, dev.to. No 0.9.58-0.9.65 coverage on the web. | Secondary only; GitHub releases were the primary source |

**Labels:** everything marked UNVERIFIED above is unverified. The "canonical doc subset" in step 7 is a recommendation. That the planning-with-files hooks are invisible to AST is an inference from the README and one SKILL.md mirror; I did not probe it. Two counts are inherited from KB source comments and I did not re-measure them: native-extract's 19 chunks / 13,442 nodes, and the 128k-node graph figure in `currency.toml`.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify): releases v0.9.51 to v0.9.65; issues #2076, #2095, #2286, #2880, #3189, #1430, #2554, #1894, #1710; PRs #3073 and #2981; README and docs via ctx7/exa/firecrawl
- [ray-manaloto/graphify](https://github.com/ray-manaloto/graphify): the pinned fork at `3c9b930f` (vendored clone `sources/graphify`), read for CLI, llm.py, serve.py, watch.py, extract.py, skill.md, extraction-spec.md
- [safishamsi/graphify](https://github.com/safishamsi/graphify): the old owner name, which the Firecrawl developer index and exa still use for issues and docs
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): repo metadata, full file tree census, README and SKILL.md mirrors (exa)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): local checkout; pin sites, `mise.toml` tasks, `kb_setup` modules, kb-curator skill, kb-extract workflow, CLAUDE.md
- [microsoft/hve-core](https://github.com/microsoft/hve-core) (TechPreacher fork branch): a third-party graphify wrapper surfaced by exa, pinned at 0.5.4
- [zachsaw/graphify-csharp](https://github.com/zachsaw/graphify-csharp): an unrelated same-name project found by last30days on HN
