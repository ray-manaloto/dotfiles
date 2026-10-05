# graphify for markdown-memory context reduction — follow-up research (2026-10-04)

Status: COMPLETE (written incrementally; progress log kept below the synthesis).
Ruling: Ray 2026-10-04 (relayed by lane G): "MORE RESEARCH FIRST" — cover (a) the 3 unread third-party pages,
(b) a measured LLM semantic mode on a copy of the real memory dir, (c) graphify's intended context-reduction uses,
(d) whether upstream plans frontmatter search.
Baselines: `docs/research/kb/reports/agents/graphify-markdown-memory-context-2026-10-03-run3.md` (main checkout) and
`dotfiles.worktrees/lane-G-20261002/.agent/kb/raw/lanes/G-graphify-memory.md`.
Pinned graphify: graphifyy 0.9.73 (`uv run --project python python -c 'importlib.metadata.version("graphifyy")'` → 0.9.73).
Path: in-lane (no Workflow tool in this subagent).

## Progress log
- (a) Firecrawl: all 3 scrapes rc=1 "Insufficient credits" (HTTP 402 class). Fallbacks: page 1 via raw.githubusercontent (200; bogus-path control 404), page 2 via curl 200 + defuddle, page 3 HTML blocked (429 Vercel checkpoint, curl and WebFetch both) → DeepWiki API via mcp2cli (rc=0). All 3 mirrored to `docs/research/kb/raw/graphify-memory-2026-10-04/links/{1,2,3}.md` + `README.md`. No named fetch gap remains; the firecrawl route itself is the gap.
- (b) Copied memory dir → `/Users/rmanaloto/.claude/jobs/bcc4b879/tmp/graphify-mem/memory-copy` (`cp -Rp`; 380 entries = 379 `.md` + `.consolidate-lock`; 2.2 MB; 205,934 words). Original memdir had no `graphify-out/` before the run.
- (b) Keyless baseline on the copy, the REAL CLI with absolute `GRAPHIFY_OUT` (closes lane G's "UNVERIFIED: CLI update + absolute GRAPHIFY_OUT"): `GRAPHIFY_NO_AUTO_REFRESH=1 GRAPHIFY_OUT=$S/keyless/graphify-out uv run --project <wt>/python graphify update $S/memory-copy --no-cluster` → rc=0, 2.87 s wall, "1168 nodes, 1593 edges", output only in `$S/keyless/graphify-out/{graph.json,manifest.json,cache}`; `memory-copy/graphify-out` absent (no leak).
- (a) Conflict found: DeepWiki 2.6 says `graphify-out/memory/` "is explicitly ignored by `detect.py`"; pinned 0.9.73 source says the opposite — `detect.py:1915-1919` "# Always include graphify-out/memory/ - query results filed back into the graph" (`scan_paths.append(memory_dir)`). Source wins; DeepWiki (generated from the old safishamsi slug) is wrong on this point.
- (d) Fan-out manifests (rc=0 each): `.agent/kb/raw/research-fanout/{frontmatter-search,frontmatter-query,memory-index}/manifest.json` in the handoff-2026-10-04h worktree; all three required sources ok/empty_verified (discussions control 10, releases control 1).
- (d) KEY FIND: upstream already tracks query-time search over node text other than the label: issue #3313 (OPEN, 2026-09-03, "Seeding ignores node attributes, so content stored on a node is unreachable by query") + PR #3636 (OPEN, unmerged, 2026-09-17, "Add a body attribute tier so query seeding can reach non-extraction content", `_BODY_MATCH_BONUS = 0.35`). Neither names markdown `frontmatter`. Also #3026/#3245 (OPEN: surface `node.description` on query/explain/MCP), #295 (OPEN: frontmatter+wikilink pre-extraction, 1 comment), #613 (OPEN: frontmatter-as-ground-truth connector), safishamsi#131 → redirects to Graphify-Labs#131 CLOSED 2026-04-09 (frontmatter-aware cache; shipped as `cache.py:443`), #2377 (OPEN PR: temporal session-memory hand-off), #2783 (OPEN PR: `GRAPHIFY_CLAUDE_CLI_MINIMAL=1` → `claude -p --safe-mode`, because each claude-cli spawn "boots a full Claude Code session with the user's global config, including SessionStart/SessionEnd hooks and plugins").
- (d) Search arms: `frontmatter searchable` → 0 vs `frontmatter in:title` → 13 (same repo qualifier; armed); fresh known-absent `vkqzrmplox` → 0; `"_node_search_text"` → 9.
- (b) Keyless recall (budget 2000, harness `$S/recall.py`, JSON `$S/recall-keyless-b2000.json`): body-only Q1/Q3/Q5 "No matching nodes"; Q2/Q4 matched only by token flood (Q2 expected files in output but 0 in top-10; Q4 2/7 in top-10); description-only Q6-Q9 4/4 "No matching nodes"; label control C+ hit (top-10); known-absent C- no match. grep finds every term question at 33-1282 output chars vs graphify's ~6.6 KB truncated outputs.
- (b) Semantic extract running since 12:32 local: "found 0 code, 379 docs … semantic extraction on 379 files via claude-cli … chunk 1/8 done" at ~4 min/chunk (serial, model sonnet via `GRAPHIFY_CLAUDE_CLI_MODEL=sonnet`).
- (c) Upstream default branch is `v8` (48d7c0e, 2026-10-04), not `main` (stale at 2026-05-14). On v8 `serve.py`: `_BODY_MATCH_BONUS` 0, `frontmatter` 0, `_node_attributes_text` 3 (control) → PR #3636 not merged. Code search: `filename:serve.py _BODY_MATCH_BONUS` 0 vs `filename:serve.py _node_rationale_text` 1 (armed); `memory_index` 0 vs `filename:reflect.py aggregate_lessons` 2 (armed); fresh absent `pqzvkmlrtw` 0; health `repo:cli/cli filename:README.md` 9.
- (b) Semantic extract DONE: rc=0, wall 877.7 s (14.6 min), 8 serial chunks, "WARNING: 35/379 dispatched file(s) produced no nodes and are absent from the graph", "wrote … graph.json — 448 nodes, 448 edges (no clustering)", "tokens: 1,424,938 in / 166,709 out, est. cost: $0.0000" (claude-cli is plan-billed; `llm.py:212-224` pricing 0). Original memdir and the copy: no `graphify-out/` (both checked after the run).
- (b) Semantic recall: see table in Answer (b). Every expected file of the missed questions IS in the semantic graph (coverage check), so the misses are LLM summarisation loss, not the 35 dropped files.

## Answer

**Verdict: the extra research does not change the decision. Tier 0 stays: grep over the memory dir, plus
`MEMORY.md`.**

- The measured LLM mode did worse than grep on every axis measured.
- Upstream has no shipped or merged way to search frontmatter.
- The nearest upstream work is an open PR that adds a `body` attribute tier (#3636).

### (a) The three unread third-party pages: read and mirrored, nothing contradicts the baseline

| page | what it says that matters here | tag |
|---|---|---|
| ai-brain-starter `skills/graphify/SKILL.md` (`links/1.md`) | A fork of the `/graphify` skill for personal vaults. Its own description says: "Not for simple file reads, vault edits, or plain text search." It adds an optional **Part A.5**, `wire_typed_relationships.py`, a zero-LLM pass that "walks markdown, reads frontmatter + body, and emits typed edges … Extracts ~80% of explicit edges (frontmatter + wikilinks)". That output is only a **skip list** for the LLM pass: "This JSONL is a skip list for Part B, nothing merges it into the graph automatically." It claims its wrappers "typically cut LLM token cost by 80–92%". It credits the pattern to garrytan/gbrain. | documented by others, not shipped by graphify |
| Agent Memory Atlas, graphify page (`links/2.md`) | graphify's memory is "a small layer bolted to the side of it", about 1,000 of 15,959 lines. `LESSONS.md` "is read wholesale at session start … no query, no ranking against the current question, and no token budget". On scope: "The unit of memory is 'how a graph query turned out' … Anyone looking for preferences, entities, a user profile … is in the wrong repository." | third-party analysis, cites source lines |
| DeepWiki "Work Memory & Reflection", `safishamsi/graphify` 2.6 (`links/3.md`) | Describes the same deterministic, no-LLM `save-result`/`remember` → `reflect` → `LESSONS.md` loop. **One claim is wrong for 0.9.73.** It says `graphify-out/memory/` "is explicitly ignored by `detect.py`", but the source says "Always include graphify-out/memory/" (`detect.py:1915-1919`). | generated wiki; source wins |

So for (a), all three pages describe either graphify's **own** Q&A work memory or vault-structure extraction.

- None indexes a Claude Code auto-memory dir for recall.
- None makes frontmatter or body text searchable by `graphify query`.
- ai-brain-starter confirms the baseline's split: structure (wikilinks and frontmatter) needs no LLM, prose needs the
  LLM.

### (b) Measured LLM semantic mode on a copy of the real memory dir

**Corpus:** 379 `.md` files, 1,495,999 chars, 205,934 words, about 374k tokens at 4 chars/token.

**Command:**
`GRAPHIFY_NO_AUTO_REFRESH=1 GRAPHIFY_CLAUDE_CLI_MODEL=sonnet GRAPHIFY_OUT=<abs scratch>/semantic/graphify-out uv run --project <worktree>/python graphify extract <copy> --backend claude-cli --out <abs scratch>/semantic --no-cluster`

- graphify version: pinned 0.9.73.
- Model: sonnet. The backend default is Opus (`llm.py:1767`).
- Baseline: keyless `graphify update` on the same copy.

| | keyless `update` | semantic `extract --backend claude-cli` |
|---|---|---|
| wall time | 2.9 s | 877.7 s (14.6 min; serial, `llm.py:2669`) |
| LLM tokens | 0 | **1,424,938 in / 166,709 out**, plan-billed (`$0.0000` API) |
| graph | 1,168 nodes / 1,593 edges | **448 nodes / 448 edges**; 344/379 files covered; **35 files produced no nodes** |
| what is stored | page, heading and wikilink structure; frontmatter stored but not searched | about 1.2 LLM-invented nodes per file, with a one-line `rationale` on 189 of them; no headings or page structure |

**Why so many input tokens.** The 1.42M input tokens are about **3.8× the corpus**. This ratio is derived, not
broken down by measurement. The likely cause:

- Each chunk spawns a full `claude -p` session that loads the user's global Claude Code config.
- The token count includes cache-read input (`llm.py:1814-1818`).
- Upstream PR #2783 (open) describes the same cost: each spawn "boots a full Claude Code session with the user's global
  config, including SessionStart/SessionEnd hooks and plugins". Its opt-in fix, `GRAPHIFY_CLAUDE_CLI_MINIMAL=1` →
  `--safe-mode`, is not in 0.9.73.

**Recall.** Ground truth for every question came from `grep` on the same copy, so grep's 9/9 on the term questions
holds by construction. The harness is `$S/recall.py`, with results in `$S/recall-{keyless,semantic}-b{2000,8000}.json`.
A budget of 8000 tokens gave the same hits as 2000.

| id | question (answer location) | keyless top-10 | semantic top-10 | grep |
|---|---|---|---|---|
| Q1 | `dubious ownership` (body, 2 files) | no match | 0/2 | 2/2, 262 chars |
| Q2 | `MISE_ENV_CACHE` (body, 2) | 0/2 (token flood) | 0/2 | 2/2 |
| Q3 | `ServerAliveInterval` (body, 2) | no match | **2/2** | 2/2 |
| Q4 | `minimum_release_age` (body, 7) | 2/7 (flood) | 1/7 | 7/7, 1,282 chars |
| Q5 | `virtiofs` (body, 3) | no match | no match | 3/3 |
| Q6 | `rebilling` (description-only, 1) | no match | no match | 1/1 |
| Q7 | `canonization` (description-only, 1) | no match | **1/1** | 1/1 |
| Q8 | `unpersisted` (description-only, 1) | no match | no match | 1/1 |
| Q9 | `decoupling` (description-only, 1) | no match | no match | 1/1 |
| P1 | paraphrase "why does git reject the workspace repo as not owned by me" (3) | 0/3 | 0/3 | `ownership` → 3/3 among 10 files; `owned by` → 0/3 |
| P2 | paraphrase "which env var silently bills the wrong organisation" (1) | 0/1 (beyond top-10) | 0/1, though node "Silent misbilling risk from stale OAuth token env" exists | `bill` → 1/1 |
| C+ | label control `gh search issues repo broken` | hit | hit | — |
| C− | fresh known-absent term | no match | no match | 0 files |

**Fully answered term questions (Q1–Q9): keyless 0/9, semantic 2/9, plus 1/7 partial.**

- The semantic misses are not caused by the 35 dropped files: every expected file is present in the semantic graph
  (coverage check). The LLM summary simply did not keep the fact.
- Paraphrases fail in both graphs because `graphify query` still scores lexically. "bills" does not match
  "misbilling", even when the right concept node exists.
- Output size: graphify returned 1.5–8.7 KB per query; grep answered in 0.03–1.3 KB.

**Verdict (b): measured, and it confirms the baseline.** Not viable as a recall layer.

- Cost: about 1.4M tokens and 15 minutes to reach 2/9 recall. Grep reaches 9/9 with a few hundred chars of output.
- Upkeep: the graph needs a full re-run every time the memory dir changes, and Claude Code changes it continuously.

### (c) What graphify itself intends for context reduction (source and upstream)

1. **Scoped subgraphs instead of reading files.**
   - `query`/`path`/`explain` and the MCP `query_graph` cut their output at `--budget` tokens. The default is 2000
     (`serve.py:1087`, `:1367`), at about 4 chars/token, and a cut is flagged `TRUNCATED`.
   - The always-on rules say to query first, because the subgraph is "usually much smaller than GRAPH_REPORT.md or raw
     grep output" (`always_on/claude-md.md:6-8`). These rules target **code** questions.
2. **PreToolUse nudge.** `graphify install` registers `hook-guard search|read` on `Bash|Grep` and `Read|Glob`
   (`install.py:445-478`). The hook adds an `additionalContext` nudge. With `--strict` it blocks the first raw read of
   each session.
3. **Session-start digest = `LESSONS.md`.**
   - The skill says: "At the **start** of graph work … run `graphify reflect --if-stale` … then read
     `graphify-out/reflections/LESSONS.md`" (`skills/claude/references/query.md:182`).
   - It is deterministic and uses no LLM.
   - It digests graphify's **own** saved Q&A outcomes, not arbitrary memory files.
   - The Atlas page notes it has no budget: it is "read wholesale".
4. **PR #1064 `export memory-index`: open, unmerged, 0 comments, last updated 2026-07-12.**
   - It summarises the **code graph**: "Key modules (top 15% by connectivity)", "97% token reduction (~55K → 2K tokens
     per session start)".
   - It does not query memory files.
   - Code search for `memory_index` on default branch `v8` returns 0; the must-hit `aggregate_lessons` returns 2.
5. **Adjacent open work, none merged:**
   - #2377: temporal session-memory hand-off to an *external* memory layer.
   - #3026 / #3245: show `node.description` in query output. That field holds LLM-written descriptions, not
     frontmatter.

None of these targets a directory of one-fact markdown memories. Their unit of reduction is "code graph → small
subgraph or digest".

### (d) Does upstream plan frontmatter search? Not as such; the nearest work is a generic `body` tier, still open

**What exists:**
- **#3313** (issue, open, 0 comments): "Seeding ignores node attributes, so content stored on a node is unreachable by
  query". It asks for either an opt-in list of attributes to score or a documented searchable-text attribute.
- **PR #3636** (open, merged=false, no maintainer response since 2026-09-17): "Add a body attribute tier so query
  seeding can reach non-extraction content".
  - It scores a `body` attribute at `_BODY_MATCH_BONUS = 0.35`; `rationale` scores 0.75.
  - It is not on default branch `v8` (48d7c0e, 2026-10-04). That branch's `serve.py` has 0 `_BODY_MATCH_BONUS` and 0
    `frontmatter`, against a control of 3 `_node_attributes_text`.

**What does not exist:**
- No issue or PR asks for the markdown page node's `frontmatter` (e.g. `description:`) to be searchable.
  - Searches: `frontmatter searchable` → 0, armed by `frontmatter in:title` → 13. `frontmatter query` → 28 hits, none
    about query-time search.
  - The frontmatter items that do exist cover other things: extraction (#295, #613), escaping (#360), Astro, and
    caching (#131, closed and shipped).
- Even if #3636 merges, `description:` stays unsearched. The markdown extractor writes `frontmatter`, not `body`
  (`extractors/markdown.py:408-413`). One of two changes is still needed: the extractor also writes `body`, or the new
  tier also reads `frontmatter`.

**Draft upstream comment (NOT filed).** A new issue would duplicate #3313/#3636, so the better venue is a comment on
them:

> Data point for #3313/#3636 from a markdown-memory use case. graphify 0.9.73 `extract_markdown` stores YAML frontmatter
> on the page node as `frontmatter` (`extractors/markdown.py:408-413`), but `_node_search_text` never reads it
> (`serve.py:437-448`).
>
> Measured on a 379-file memory vault (one fact per file, retrieval key in `description:`): 4/4 description-only terms
> return "No matching nodes found", while the same call finds label terms. With #3636 as written this stays true,
> because the markdown extractor writes no `body` attribute.
>
> Request, either of:
>
> 1. Have `extract_markdown` also emit a capped `body` from the frontmatter `description`/`summary` (and optionally the
>    first paragraph).
> 2. Let the #3636 tier read string values of `frontmatter` at the same lower weight.
>
> Option 1 keeps the single documented convention (`body`) that #3636 chose. Happy to provide a fixture.

## Evidence

| claim | URL or file:line | verbatim quote |
|---|---|---|
| ai-brain-starter disclaims plain text search | `links/1.md:3` (raw.githubusercontent HTTP 200) | "Not for simple file reads, vault edits, or plain text search." |
| Part A.5 is a skip list, not merged | `links/1.md` §Part A.5 | "This JSONL is a skip list for Part B, nothing merges it into the graph automatically." |
| LESSONS.md unbudgeted | `links/2.md` §6 | "There is no query, no ranking against the current question, and no token budget — the whole artifact enters context." |
| graphify memory ≠ general memory | `links/2.md` §11 Fit | "The unit of memory is 'how a graph query turned out'" |
| DeepWiki wrong on detect | `links/3.md` vs `graphify/detect.py:1915-1919` (0.9.73) | "explicitly ignored by `detect.py`" vs "# Always include graphify-out/memory/ - query results filed back into the graph" |
| claude-cli is plan-billed, defaults to Opus | `graphify/llm.py:212-224`, `:1767-1771` | "costs are billed to the plan" / "claude-cli defaults to Opus … GRAPHIFY_CLAUDE_CLI_MODEL=haiku (or sonnet …)" |
| claude-cli input tokens include cache reads | `llm.py:1814-1818` | `int(usage.get("input_tokens", 0) or 0) + int(usage.get("cache_read_input_tokens", 0) …` |
| measured cost and loss | `$S/semantic/extract.log` | "35/379 dispatched file(s) produced no nodes" / "448 nodes, 448 edges" / "tokens: 1,424,938 in / 166,709 out" / "real 877.67" |
| each spawn boots a full session | https://github.com/Graphify-Labs/graphify/pull/2783 (OPEN) | "Each claude -p spawn … boots a full Claude Code session with the user's global config, including SessionStart/SessionEnd hooks and plugins." |
| query default budget 2000 | `serve.py:1087` | `def _subgraph_to_text(G, nodes, edges, token_budget: int = 2000, …)` |
| session-start digest = LESSONS.md | `skills/claude/references/query.md:182` | "At the **start** of graph work, refresh and read the lessons: run `graphify reflect --if-stale` …" |
| #1064 open, code-graph summary | https://github.com/Graphify-Labs/graphify/pull/1064 | state=open merged=false updated 2026-07-12; "Key modules (top 15% by connectivity)" |
| attribute seeding gap acknowledged | https://github.com/Graphify-Labs/graphify/issues/3313 | "`_score_query` / `_pick_seeds` score nodes on their **label** and **source path** only." |
| body-tier fix open | https://github.com/Graphify-Labs/graphify/pull/3636 | "`body` is now the documented convention for this free text … (`_BODY_MATCH_BONUS = 0.35`, vs. rationale's `0.75`)" |
| not on default branch | `gh api repos/Graphify-Labs/graphify/contents/graphify/serve.py?ref=v8` | grep counts `_BODY_MATCH_BONUS` 0, `frontmatter` 0, `_node_attributes_text` 3 |
| #131 shipped (frontmatter-aware cache) | https://github.com/Graphify-Labs/graphify/issues/131 (closed 2026-04-09) | "The SHA256 cache hashes the entire file content, including YAML frontmatter." |

Control arms:

- PR lookups: `pulls/999999999` → 404, while the real PRs → 200.
- Raw fetch: a bogus path → 404, while page 1 → 200.
- Fresh known-absent terms → 0 in every search: issue search, code search, grep (rc=1), and graphify query (no match).
- Code-search health check: `repo:cli/cli filename:README.md` → 9.
- Label must-hit (C+): hit in both graphs.
- Memory dir: `graphify-out/` absent after every run.

## Conflicts resolved

1. **Is `graphify-out/memory/` scanned?** DeepWiki says no; the source says yes. Trusted the source
   (`detect.py:1915-1919`).
2. **Which branch is "upstream main"?** The `main` branch is stale; its last commit is from 2026-05-14. The live default
   branch is `v8`. Earlier lane-G and run-3 claims about "main" were re-checked on `v8` and still hold: 0 `frontmatter`
   in `serve.py`.
3. **Does semantic extraction make prose searchable?** Run 3 said it does. That holds only in a weak sense: it writes
   `rationale` text that the scorer reads, but measured recall was 2/9 on term questions and 0/2 on paraphrases.

## Gaps

- **Firecrawl.** All three scrapes failed with rc=1 "Insufficient credits". The pages were recovered with curl,
  defuddle, and the DeepWiki MCP API via mcp2cli, so the mirrors are not firecrawl output.
- **One run, one model.** The extract ran once, on sonnet rather than the default Opus, so there is no variance floor.
  The 35 dropped files were not retried.
- **Token breakdown not measured.** The 1.42M input tokens were not split into corpus, prompt schema, session-context
  cache reads, and retries. The 3.8× overhead is derived.
- **Not run:**
  - #2783 `--safe-mode` (not in 0.9.73).
  - 0.9.74/0.9.75 (run 3 checked them by diff only).
  - `graphify explain` and MCP `query_graph` recall.
  - #3636 (unmerged). Its effect on markdown is inferred from the PR text and `markdown.py:408-413`.
- **Grep is the ground truth for Q1–Q9,** so its 9/9 holds by construction. For paraphrases, grep recall depends on the
  agent picking a good keyword: `ownership` → 3/3, `owned by` → 0/3.

## Recommendation for Ray

1. **Keep Tier 0 and close the "more research" ask as answered.** Grep over the memory dir plus the `MEMORY.md` index
   is the only route that reliably hits `description:` and body facts. It is native and free.
2. **Do not adopt the LLM semantic mode for memory.** It reached 2/9 recall for about 1.4M plan tokens and 15 minutes
   per full build. It also silently drops about 9% of files, loses every heading, and goes stale as soon as Claude
   Code writes a memory.
3. **Do not build a keyless graphify memory task for recall.** It reached 0/9. Build one only if wikilink backlink
   structure becomes a real need.
4. **Optional, low cost:** post the drafted comment on #3313/#3636. That is a GitHub write, so it needs Ray's approval.
   Revisit Tier 1 only if #3636 lands *and* markdown frontmatter gets routed into `body`. At that point, re-run this
   harness (`$S/recall.py` Q6–Q9) against the new release.
5. **If semantic extraction is ever run again on this machine:**
   - Set `GRAPHIFY_CLAUDE_CLI_MODEL`; the default is Opus.
   - Switch to the `--safe-mode` route once #2783 ships, so user hooks and plugins stop running inside every chunk.

## Verification (refute pass)

| load-bearing claim | status | how |
|---|---|---|
| Semantic recall 2/9, and the expected files are in the graph | confirmed | harness re-run at budget 8000 gave the same hits; coverage checked per expected file |
| #3313/#3636/#2783/#1064 open and unmerged | confirmed | live `gh api pulls/N` returned merged=false; 404 control |
| No body or frontmatter tier on default branch `v8` | confirmed | raw `serve.py@v8` grep: 0 and 0, against control 3; code search: 0, against must-hit 1 |
| No upstream ask for page-frontmatter query search | confirmed (absence, two routes) | issue search in 4 armed query shapes, plus code search, plus reading the #295/#613/#131 bodies |
| DeepWiki's detect claim is wrong | confirmed | pinned source line |

## Files and scratch

- Mirrors: `docs/research/kb/raw/graphify-memory-2026-10-04/links/{1,2,3}.md` and `README.md` (this worktree).
- Scratch: `$S` = `/Users/rmanaloto/.claude/jobs/bcc4b879/tmp/graphify-mem`. It holds:
  - `memory-copy/`
  - `keyless/{update.log,graphify-out/}`
  - `semantic/{extract.log,graphify-out/}`
  - `recall.py`
  - `recall-*.json`
- Fan-out manifests: `.agent/kb/raw/research-fanout/{frontmatter-search,frontmatter-query,memory-index}/manifest.json`
  (this worktree).

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — issues #295 #613 #3313 #3026 #131 and PRs #1064 #3636 #3245 #2377 #2783 #191; issue and code search; `serve.py@v8`; releases. Pinned 0.9.73 source read on disk.
- [safishamsi/graphify](https://github.com/safishamsi/graphify) — the old slug. Issue #131 redirects to Graphify-Labs, and the DeepWiki page was generated from this slug.
- [mycelium-hq/ai-brain-starter](https://github.com/mycelium-hq/ai-brain-starter) — `skills/graphify/SKILL.md`, read and mirrored.
- [garrytan/gbrain](https://github.com/garrytan/gbrain) — named in ai-brain-starter as the source of the pattern; not read.
- [cli/cli](https://github.com/cli/cli) — used only as the code-search health control.

---

**Coordinator annotation (f5b237, 2026-10-04, after Ray's rulings):** (1) `links/1.md` is NOT in the tree. It was dropped
as a named gap (betterleaks `generic-password` at its line 754; Ray chose drop over allowlist). The citations to it above
resolve to the URL in `links/README.md` row 1. (2) The drafted comment was posted on PR #3636 with Ray's approval:
https://github.com/Graphify-Labs/graphify/pull/3636#issuecomment-5983019536
