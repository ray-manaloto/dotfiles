# Agent report (verbatim): graphify-mining

Persisted from agent transcript `5a7e97bf-884c-4514-9041-cb4b9877cca7.jsonl` on 2026-07-19.
Captured per `.claude/rules/agent-report-persistence.md` (verbatim, at receipt).

---

Report complete. Findings persisted to `.omc/notepad.md`.

---

# Graphify community mining — practical tips, techniques & best practices

**Target:** [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — 91,533 ★, created 2026-04-03, default branch `v8`, homepage [graphify.com](https://www.graphify.com). PyPI package is **`graphifyy`** (double-y); CLI is `graphify`.

**What I actually read:** the README (861 lines, fetched via API), `docs/how-it-works.md`, ~40 issues/PRs read in full, ~2,000 issue/PR titles swept via the GitHub search API, 83 discussions enumerated with 12 read in full including maintainer replies, `graphify.com` + `/docs` + `/llms-full.txt`, and the Discord invite API. **X/Twitter content I could NOT read** — see §3.

---

## 1. GitHub issues, PRs & discussions

### 1a. Local inference with Ollama

| # | URL | Takeaway | Status |
|---|---|---|---|
| **820** | [issues/820](https://github.com/Graphify-Labs/graphify/issues/820) | Ollama's default context is **2048 tokens**; graphify wasn't wiring `GRAPHIFY_OLLAMA_NUM_CTX` into `_call_openai_compat`, so every chunk >2048 tok returned `content=""` → **0 nodes, 0 edges, silently**. Surfaced as `Expecting value: line 1 column 1`. | **Fixed** (env var now reaches the API layer) — but *always set `GRAPHIFY_OLLAMA_NUM_CTX` explicitly* |
| **798** | [issues/798](https://github.com/Graphify-Labs/graphify/issues/798) | KV-cache saturation across chunks: chunks 1–2 perfect, chunks 3–4 degrade to "few tokens"/closing-bracket-only. Ollama session wasn't reset statelessly per chunk. Restarting fixed it temporarily. | **Closed/fixed**; if you see this pattern on any local backend, suspect context leak |
| **1686** | [issues/1686](https://github.com/Graphify-Labs/graphify/issues/1686) | A **wedged Ollama server hangs the entire extract indefinitely** despite `--api-timeout 180`. Signature: graphify at 0% CPU, Ollama idle, an independent `curl /api/generate` *also* hangs. Reproduced 3× in one session. Reporter ran `--max-concurrency 1`, `qwen3-coder-next` (extract) + `qwen3.5:122b` (label). | **Closed/fixed**; the 0%-CPU + idle-server + independently-hung-curl triage signature is worth keeping |
| **792** | [issues/792](https://github.com/Graphify-Labs/graphify/issues/792) | Best single tuning writeup. On RTX 5090 + Ryzen 9950X3D: `max_workers` was capped at 8 (400% underuse on 32 threads); default `token_budget` 60k and `max_concurrency` 4 are **cloud defaults that cause timeouts/VRAM OOM on local**. Manual patching → **95% GPU saturation**. Requested values: `max_workers: 32`, `token_budget: 16384`, `max_concurrency: 1`, `temperature: 0.3`, `seed: 42`, `num_ctx: 65536`. | **Closed** — `--max-workers`/`--token-budget`/`--max-concurrency` now exist as flags; the proposed `graphify.yaml` did not ship |
| **1940** | [issues/1940](https://github.com/Graphify-Labs/graphify/issues/1940) | graphify reads `OLLAMA_BASE_URL`, but Ollama itself only defines **`OLLAMA_HOST`** — no `OLLAMA_BASE_URL` concept exists upstream. | **Open bug**; two competing fix PRs [#1966](https://github.com/Graphify-Labs/graphify/pull/1966), [#2019](https://github.com/Graphify-Labs/graphify/pull/2019). **Set `OLLAMA_BASE_URL` explicitly today.** |
| **1272** | [pull/1272](https://github.com/Graphify-Labs/graphify/pull/1272) | `OLLAMA_BASE_URL` should include the **`/v1`** path. | Open docs PR — worth doing anyway |
| **1168** | [issues/1168](https://github.com/Graphify-Labs/graphify/issues/1168) | mDNS `.local` hostnames were **hard-blocked** as link-local (a Bonjour name always resolves an `fe80::` companion alongside its routable v4), with no override. Same host by literal IPv4 was accepted. Reporter was running **LM Studio on a second Mac**. | **Closed/fixed** — workaround was pinning the IPv4 |
| **1549** | [pull/1549](https://github.com/Graphify-Labs/graphify/pull/1549) | Proposes laptop-safe local defaults: **`qwen2.5-coder:3b` first, then `gemma3:4b`**; routes through Ollama's native **`/api/chat`** so `num_ctx` actually applies; retry-next-local-model on failure. | **Open PR**, not merged — treat the model list as a community suggestion, not shipped behavior |

### 1b. OpenAI-compatible base URLs / vLLM / NIM / LM Studio

| # | URL | Takeaway | Status |
|---|---|---|---|
| **959** | [issues/959](https://github.com/Graphify-Labs/graphify/issues/959) | The original ask: local models were Ollama-only, OpenAI base-url hardcoded, blocking vLLM. | **Open**, but functionally superseded — `OPENAI_BASE_URL`/`OPENAI_MODEL` now exist and README explicitly lists llama.cpp/vLLM/LM Studio |
| **981 / 1084** | [981](https://github.com/Graphify-Labs/graphify/issues/981), [1084](https://github.com/Graphify-Labs/graphify/issues/1084) | Configurable base URL for OpenAI **and** Anthropic backends. | Delivered via [#1273](https://github.com/Graphify-Labs/graphify/pull/1273), [#1113](https://github.com/Graphify-Labs/graphify/pull/1113), [#1458](https://github.com/Graphify-Labs/graphify/pull/1458) (`*_BASE_URL` for kimi/gemini/deepseek too) |
| **1223** | [issues/1223](https://github.com/Graphify-Labs/graphify/issues/1223) | Gateways that stream when `stream` is omitted break the SDK — needed a way to force `stream:false`. | **Closed** — relevant if you front a local model with a proxy |
| **1621** | [issues/1621](https://github.com/Graphify-Labs/graphify/issues/1621) | `deepseek-v4-flash` runs with **thinking enabled by default** with no `extra_body` override → JSON-parse failure on a semantic chunk. Same class as the kimi fix ([#623](https://github.com/Graphify-Labs/graphify/pull/623), [#610](https://github.com/Graphify-Labs/graphify/issues/610): kimi rejects `temperature=0`). | **Closed** — **reasoning models need thinking disabled or they return empty `content`** |
| **1107 / 1041** | [1107](https://github.com/Graphify-Labs/graphify/pull/1107), [1041](https://github.com/Graphify-Labs/graphify/pull/1041) | Azure OpenAI backend (merged); OpenRouter backend (open). | Azure shipped as `--backend azure` |

**No NVIDIA NIM–specific issue exists** — I searched and found none. NIM would ride the generic `--backend openai` + `OPENAI_BASE_URL` path.

### 1c. Truncation / output-token limits — the biggest practical trap

| # | URL | Takeaway | Status |
|---|---|---|---|
| **1365** | [discussions/1365](https://github.com/Graphify-Labs/graphify/discussions/1365) | User pointed the **Ollama shim at OpenRouter**; got constant `Unterminated string` + `chunk of 4 truncated at depth 0, splitting into halves of 2 and 2`. Maintainer root-caused a **real bug**: `ollama`/`openai`/`deepseek`/`kimi` configs declare `max_tokens: 16384`, but dispatch only read `max_completion_tokens` (gemini-only key) → those four silently fell back to an **8192** cap. Fixed in `5b0c154`. Maintainer's explicit advice: **prefer `--backend openai` + `OPENAI_BASE_URL` over the Ollama shim for OpenAI-compatible gateways.** | **Fixed** — confirmed-working guidance |
| **1758** | [issues/1758](https://github.com/Graphify-Labs/graphify/issues/1758) | On the **skill/subagent path** (no API key → Claude Code Agent-tool subagents act as the LLM), each subagent must emit a whole chunk's JSON in one turn. `SKILL.md` chunks by **file count (20–25), not output size**, so `--mode deep` on dense corpora blows the **~64k output-token turn limit** → the chunk file is *never written*, no partial, no error. Presents as either an infinite hang or 12–28 min unexplained latency. Step B3's diagnostic ("you probably used a read-only Explore subagent") is a **plausible-but-wrong** explanation. This path never goes through `graphify/llm.py`, so it gets none of the bisection recovery the headless backends have. | **OPEN known-bug** — highly relevant to anyone driving graphify from an agent harness |

### 1d. Video / image / document ingestion

- **Video pipeline is `[video]` extra = faster-whisper + yt-dlp**, and per [`docs/how-it-works.md`](https://github.com/Graphify-Labs/graphify/blob/v8/docs/how-it-works.md) "Pass 2 — Video and audio (**local, no API calls**)". Ingest via `graphify add <youtube-url>`.
- [#592](https://github.com/Graphify-Labs/graphify/issues/592) — **yt-dlp SSRF bypass** in `transcribe.download_audio`. Closed/fixed. [#1436](https://github.com/Graphify-Labs/graphify/pull/1436) (cap `max_filesize` to limit resource/SSRF abuse) and [#2021](https://github.com/Graphify-Labs/graphify/pull/2021) (normalize `www.`-prefixed URLs before validation) are still **open**. If you ingest untrusted URLs, this is your risk surface.
- **[#1109](https://github.com/Graphify-Labs/graphify/issues/1109) — images are broken on headless `extract`.** `_read_files` does `path.read_text(errors="replace")` on *every* semantic file, so a PNG becomes replacement-character garbage. `--backend claude-cli` exits 1 outright; API backends emit hollow nodes guessed from the filename. **No backend ever puts the image in front of a vision model.** **OPEN.** Fix proposed in #1110. Related: #450, #181 (images inside PDFs).
- [#259](https://github.com/Graphify-Labs/graphify/issues/259) — local PDF parsing without an LLM API: still **open**.

### 1e. Query patterns (BFS/DFS, budget, affected, path, explain) — and their known defects

Confirmed CLI surface (README `Full command reference`):
```
graphify query "what connects attention to the optimizer?"
graphify query "..." --dfs --budget 1500
graphify path "DigestAuth" "Response"
graphify explain "SwinTransformer"
graphify affected <symbol>
```
Note: **there is no `--context` flag** in the documented surface. I searched the README and command reference and found `--budget`, `--dfs`, `--graph`, and (open PRs only) `--recency`.

| # | URL | Takeaway | Status |
|---|---|---|---|
| **445** | [issues/445](https://github.com/Graphify-Labs/graphify/issues/445) | BFS seeds are picked by naive substring match `sum(1 for t in terms if t in label)`. On a mixed corpus, a query about `seg_result.planes` seeded on **three PNG golden-test renders** whose captions contained the terms; all 15 real mutation sites were missed. Proposed weighting: `code 1.0 / document 0.7 / image 0.4` × degree. | **OPEN known-bug** — hits exactly the cross-cutting queries graphify markets |
| **449** | [issues/449](https://github.com/Graphify-Labs/graphify/issues/449) | Root cause of the above: **semantic subagent labels are free-form 200-char summaries**, which accidentally match dozens of terms and crowd out precise AST symbol labels. Measured on an 8,333-node graph: top-3 seeds for *every* semantic query came from the same 20 files. Proposed schema split: short `label` + verbose `summary`. | **OPEN known-bug** |
| **2004** | [issues/2004](https://github.com/Graphify-Labs/graphify/issues/2004) | **`affected` silently returns false negatives.** `from pkg.sub.mod import X` creates an `imports_from` edge whose target ID is derived from the *import string* (`pkg_sub_mod`), not the real scanned node (`sub_mod`). So `affected "mod.py"` and `affected "sub_mod"` both return "No affected nodes found" while `affected "pkg_sub_mod"` works. `diagnose multigraph` showed **thousands of `dangling_endpoint_edges`** on a 21k-node graph. Also: `god_nodes` is not a CLI subcommand; `--output` is ignored on `extract`. | **OPEN known-bug** — an agent reads this as "nothing depends on this" |
| **1969** | [issues/1969](https://github.com/Graphify-Labs/graphify/issues/1969) | `explain` resolves ambiguous terms **silently** (unlike `path`, which warns); resolution degrades as the graph grows. | OPEN |
| **1654 / 1664** | [1654](https://github.com/Graphify-Labs/graphify/issues/1654), [1664](https://github.com/Graphify-Labs/graphify/pull/1664) | Per-project `config.json` defaults for query budget/depth. | Open PR |
| **1296** | [issues/1296](https://github.com/Graphify-Labs/graphify/issues/1296) | "query is a traversal, agents need a **name harvester**" — a label-match node enumeration subcommand. | Open, and a genuinely good idea for agent tooling |
| **1184** | [issues/1184](https://github.com/Graphify-Labs/graphify/issues/1184) | Argues the graph *quality* is fine; the gap is the **retrieval/API surface for agents** — asks for composable structured primitives ("what files are involved in changing X", "blast radius of Y") over `graph.json`. | Open — directly on-point for building on top |
| **977** | [issues/977](https://github.com/Graphify-Labs/graphify/issues/977) | `--exclude` / `--no-tests` to filter by `source_file` **before** BFS. | Open |

### 1f. Accuracy / hallucination of semantic extraction

- **[#198](https://github.com/Graphify-Labs/graphify/issues/198) — the semantic layer is mostly disconnected from the AST graph.** The two passes run in parallel, so the semantic pass can't intentionally attach to AST nodes; fusion relies on **exact node-id collision**, which almost never happens (`SentenceTransformer` vs `"sentence transformer"`). Verified on HKUDS/OpenHarness: effectively **zero `code↔document` or `code↔concept` bridges** — one code component, one separate semantic subgraph. **OPEN.** This is the single most important caveat for anyone treating graphify as a unified KB.
- **[#437](https://github.com/Graphify-Labs/graphify/issues/437)** — cross-file inference creates **false edges via common .NET method names**; fix PR [#440](https://github.com/Graphify-Labs/graphify/pull/440) adds a BCL blocklist. Sibling: [#1221](https://github.com/Graphify-Labs/graphify/pull/1221) blocklists Python stdlib + JS globals from noise nodes and INFERRED edges. Both **open**.
- **[#1318](https://github.com/Graphify-Labs/graphify/issues/1318)** — inconsistent node IDs at *definition* vs *reference* sites → edges connect to orphan "shadow nodes". **[#952](https://github.com/Graphify-Labs/graphify/issues/952)** — ID collisions on identical filenames across folders **merge distinct functions into one node**. Both open.
- **Confidence tiers are the mitigation, and they work.** Per `how-it-works.md`: `EXTRACTED` (always confidence 1.0), `INFERRED` (discrete rubric, 0.0–1.0), `AMBIGUOUS` (flagged for manual review). [#1676](https://github.com/Graphify-Labs/graphify/issues/1676) is a strong independent validation — see §1i.
- **[#2051](https://github.com/Graphify-Labs/graphify/issues/2051)** (open, actively discussed) argues staleness must be **enforced at query time**, not merely stored: *"The original harm is not that stale nodes exist. It is that they are returned in polished, canonical-sounding form with no warning."* Acceptance criteria proposed: default queries exclude or materially down-rank stale nodes. Related: [#1665](https://github.com/Graphify-Labs/graphify/pull/1665) opt-in `--recency` flag.

### 1g. Memory / save-result / reflect feedback loop — **confirmed working, shipped 0.8.47**

From [#1441](https://github.com/Graphify-Labs/graphify/issues/1441) (design, closed) → [#1443](https://github.com/Graphify-Labs/graphify/pull/1443) + [#1542](https://github.com/Graphify-Labs/graphify/pull/1542) (merged), and the [announcement discussion #1449](https://github.com/Graphify-Labs/graphify/discussions/1449):

```bash
graphify save-result --question "how does auth work?" \
  --answer "JWT via verify_token()" \
  --nodes "verify_token()" "jwt_auth.py" --outcome useful
# --outcome ∈ useful | dead_end | corrected   (+ --correction "..." for corrected)

graphify reflect                    # → graphify-out/reflections/LESSONS.md
graphify reflect --if-stale         # no-op if LESSONS.md newer than all inputs — cheap per session
graphify reflect --graph graphify-out/graph.json   # group by community + write .graphify_learning.json overlay
```
Ranking mechanics (maintainer, verbatim-sourced): **deterministic, uses no LLM**. Citations decay by recency (`--half-life-days`, default **30**). A node only becomes a *preferred* source after appearing in **≥2 separate useful results** (`--min-corroboration`, default 2) — a single save is "tentative", not trusted. Conflicts (useful once, dead-end later) surface **once with a "most recent wins" note**, not silently in both lists. Citations pointing at nodes that no longer exist are **dropped**, so deleting code clears its lessons. The overlay tags nodes preferred/tentative/contested and makes `explain`/`query` print a `Lesson:` hint, flagged **"code changed — re-verify"** when the source moved on. Git post-commit/post-checkout hooks run `reflect` automatically once you have outcomes saved.

Related open work: **[#1871](https://github.com/Graphify-Labs/graphify/pull/1871) `graphify curate`** — durable *human* corrections that survive a rebuild.

### 1h. Global / multi-repo graphs

Confirmed CLI (README):
```bash
graphify extract ./docs --global --as myrepo          # extract + register into cross-project graph
graphify global add graphify-out/graph.json --as myrepo   # → ~/.graphify/global-graph.json
graphify global remove myrepo
graphify global list                                   # repos + node/edge counts
graphify global path
graphify merge-graphs a.json b.json --out merged.json
```
Caveats: [#1691](https://github.com/Graphify-Labs/graphify/pull/1691) "preserve repository-local identities" on merge (open); [#569](https://github.com/Graphify-Labs/graphify/issues/569) scoped resolution for monorepos/name collisions (open); [#1177](https://github.com/Graphify-Labs/graphify/issues/1177) "how to integrate with multi repo project" (open); [#1687](https://github.com/Graphify-Labs/graphify/issues/1687) recursive `update` for monorepo/workspace layouts (open).

**[Discussion #645](https://github.com/Graphify-Labs/graphify/discussions/645)** is the best practical large-project pattern I found — a user split output into type-scoped folders plus an `AllFolders/` master graph, with a `CLAUDE.md` telling the assistant to prefer the scoped `GRAPH_REPORT.md` for narrow questions. Community answer: generate the **wiki for `AllFolders` only** (per-folder wikis cause "massive token redundancy and split the navigation index"); regenerate the wiki only at major milestones, not per update; devs update only `AllFolders` locally and **offload type-scoped graph updates to nightly CI**.

**[Discussion #1408](https://github.com/Graphify-Labs/graphify/discussions/1408)** (multi-machine): there is no hosting story and none is needed — **commit `graphify-out/` to git**; gitignore `graphify-out/cache/` (mtime-based, invalid after a fresh clone) and `graphify-out/cost.json`.

### 1i. `merge-driver` / git-hook workflow

- `graphify hook install` writes **post-commit + post-checkout** hooks (AST-only rebuild, **no API cost**) *and* registers a **git merge driver** that union-merges `graph.json`, so two devs committing in parallel never get conflict markers.
- **[#1902](https://github.com/Graphify-Labs/graphify/issues/1902)** — `hook install` **never actually registered the merge driver** that both README and CHANGELOG 0.7.0 documented. **Closed/fixed** — but verify on your version.
- **[#1385](https://github.com/Graphify-Labs/graphify/issues/1385)** — `hook install` wrote a junk directory and **reported false success** when `core.hooksPath` resolved to a non-POSIX (Windows) path. Closed.
- **[#791](https://github.com/Graphify-Labs/graphify/issues/791)** — the post-commit hook **spawned unbounded detached Python rebuilds**; concurrent multi-repo commits exhausted memory. Closed. Follow-up **[#1037](https://github.com/Graphify-Labs/graphify/issues/1037)** — still raced on `graph.json` with rapid same-repo commits. Closed; `graph.json`/`manifest.json` are now written **atomically** ([#1952](https://github.com/Graphify-Labs/graphify/pull/1952)).
- README (v0.9.x): re-run `graphify hook install` after any upgrade — the hook **embeds the interpreter path** at install time.

### 1j. Performance & scale

| # | URL | Takeaway |
|---|---|---|
| [#1958](https://github.com/Graphify-Labs/graphify/issues/1958) | open | `detect()` is CPU-bound **35+ min on a large monorepo** despite dir pruning, while `git ls-files` discovery takes ~1s |
| [#1964](https://github.com/Graphify-Labs/graphify/issues/1964) | open | `manifest.json` uses **absolute paths as keys** → `--update` always triggers a **full rebuild on CI or a different clone path**. (README now claims keys are relative + re-anchored — verify on your version; the issue is still open.) |
| [#2033](https://github.com/Graphify-Labs/graphify/issues/2033) | open | The update runbook **omits `kind="ast"`**, so incremental update **re-extracts the entire corpus semantically** — i.e. pays full LLM cost when it shouldn't |
| [#2015](https://github.com/Graphify-Labs/graphify/issues/2015) | open | `watch._rebuild_code` stamps the whole corpus into the manifest on code-only rebuilds → `--update` **silently skips new docs** |
| [#1711](https://github.com/Graphify-Labs/graphify/issues/1711) | open | `build_merge` **severs edges from unchanged files into re-extracted files** — measured **−12% doc↔code edges in one update cycle**; endpoints get replaced, survivors dangle, dangling-edge cleanup eats them |
| [#728](https://github.com/Graphify-Labs/graphify/issues/728) | open | Large graphs carry **24% isolated dead-weight nodes** from bundled/synthetic source files |
| [#446](https://github.com/Graphify-Labs/graphify/issues/446) | open | Leiden on code-heavy graphs → **274 communities at cohesion 0.01** (fragmentation). Mitigations that shipped: `--resolution`, `--exclude-hubs` |
| [#1431](https://github.com/Graphify-Labs/graphify/pull/1431) | merged | Trigram candidate prefilter cuts O(N) `serve` query latency, byte-identical results |
| [#370](https://github.com/Graphify-Labs/graphify/pull/370) | open | igraph C backend for betweenness centrality, **~100× speedup** |
| [#1019](https://github.com/Graphify-Labs/graphify/discussions/1019) | — | `graphify export` **hard-caps at 512 MB `graph.json`**; [#1708](https://github.com/Graphify-Labs/graphify/issues/1708) proposes transparent sharded-graph loading |
| README | — | HTML viz becomes unopenable **>5000 nodes** — use `--no-viz` and query the JSON |

**Determinism ([#1090](https://github.com/Graphify-Labs/graphify/discussions/1090) / [#1105](https://github.com/Graphify-Labs/graphify/discussions/1105))** — the most useful maintainer thread in the repo. A user measured 4 runs of `graphify update` on an unchanged repo: node counts and MD5 all differed. Maintainer root-caused it to **`os.walk()` returning files in filesystem b-tree order**, with several first-writer-wins downstream passes (cross-file import resolution, label dedup, symbol resolution) — *not* Leiden, which is properly seeded (`random_seed=42, trials=1`). Fixed in `8db19d6` by lexicographically sorting `all_files`. A second residual — 77–88% of nodes "changing community" between runs — was a **labeling artifact**: community integer IDs came from size-sorting, and equal-sized small communities permuted. Fixed via a total order `(-size, sorted nodes)`. Key operational line: **"the default install uses Louvain, which is fully deterministic (verified 20/20 identical runs) — so if you need byte-stable `graph.json`, a default install (no `[leiden]` extra) gives it."** The `[leiden]`/graspologic path retains a ~0.1% residual wobble when re-splitting small low-cohesion subgraphs.

### 1k. Third-party work built on graphify (best real-world validation)

**[#1676](https://github.com/Graphify-Labs/graphify/issues/1676)** — [`jest-graph-tia`](https://github.com/Elbltagy2/jest-graph-tia), a Test Impact Analysis orchestrator using `graph.json` as its semantic layer. The technique is directly reusable: git diff → **reverse-BFS with per-confidence-tier hop budgets (EXTRACTED 6 / INFERRED 2 / AMBIGUOUS off)** → feed the expanded set to `jest --findRelatedTests`. Because the graph only ever *widens* Jest's input, selection can never be less safe than Jest's own. Measured on a production Next.js repo (23,403 nodes / 47,913 edges): on **5 of 10 recent commits** it selected 5–8 genuinely affected tests Jest's scanner missed (root cause: **`import type` dependencies**, which Jest drops but tree-sitter keeps as EXTRACTED edges), at ~2% of the suite. Verified schema facts: edges live under `links`, **direction = source-depends-on-target**; **INFERRED edges survive `graphify update` re-extraction**; incremental update on 23k nodes ≈ **41s**.

### 1l. Benchmarks (maintainer-published, with caveats stated)

[Discussion #1328](https://github.com/Graphify-Labs/graphify/discussions/1328) + [#1677](https://github.com/Graphify-Labs/graphify/discussions/1677) → [BENCHMARKS.md](https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md). Agent-capability run on **ERPNext** (~1M LOC), fixed agent (Claude Opus 4.8, ≤14 turns), real measured token usage, one added tool per treatment:

| config | accuracy | tokens vs floor | $/task |
|---|--:|--:|--:|
| **+ graphify** | **82.0%** | **1.3×** | **$0.320** |
| + codebase_memory | 80.5% | 2.7× | $0.599 |
| + repomix | 80.5% | **30.0×** | $3.936 |
| + codegraphcontext | 79.2% | 2.2× | $0.391 |
| + claude_context | 79.1% | 1.4× | $0.340 |
| grep/read floor | 70.8% | 1.0× | $0.322 |

Memory benchmarks: LOCOMO n=300 recall@10 **0.497** (~10× mem0), QA 45.3%; LongMemEval-S n=50 **76%**. Judge blind-validated against a second judge (90.6% agreement, κ=0.81). **The maintainer flags honestly** that the LOCOMO/LongMemEval "graphify" configuration is *"an experimental engine implementing graphify's retrieval architecture over conversation turns — a benchmark prototype of the architecture, not the shipped package as-is"* (turn-level nodes in SurrealDB/HNSW with hybrid dense+lexical seeds). Independent community benchmark framework: [FolatheDuckofDuckingburg/graphify/tree/v8/benchmarks](https://github.com/FolatheDuckofDuckingburg/graphify/tree/v8/benchmarks) (16 tasks, paired trials, McNemar's test).

---

## 2. Discord — **invite found, history NOT read**

Both invites resolve (via the public `discord.com/api/v10/invites/<code>` endpoint) to the **same guild**, id `1496114518160441345`, name **"Graphify Labs (YC S26)"**, inviter `graphifylabs` / "Safi (Graphify Labs)":

- **https://discord.gg/XPPYrdw3Yp** — from [graphify.com/llms-full.txt](https://graphify.com/llms-full.txt). `expires_at: null` → **permanent, use this one**.
- **https://discord.gg/598Ad9zQZ** — the badge in the [README](https://github.com/Graphify-Labs/graphify#readme). `expires_at: 2026-07-28` → **expires in 9 days**. Worth reporting upstream.

Server description (verbatim from the invite payload): *"Join developers, builders, and contributors turning codebases into queryable knowledge. Graphify gives AI assistants a second brain that cuts token usage and keeps answers grounded instead of guessed."* Guild features include `NEWS` and `COMMUNITY`.

**I did not join and I could not read any channel history, announcements, or pinned messages.** Everything I know about the Discord is the invite metadata above plus two GitHub discussions that merely *reference* it ([#1526 "Join the graphify community on Discord"](https://github.com/Graphify-Labs/graphify/discussions/1526), [#773 "Follow us on X + Discord community coming soon"](https://github.com/Graphify-Labs/graphify/discussions/773)). **No Discord content is quoted anywhere in this report.**

---

## 3. Twitter / X — **handle found, content NOT readable**

- **Handle: [@graphify](https://x.com/graphify)** — sourced from the README footer badge (line 858 of the fetched README), which links `https://x.com/graphify`.
- Maintainer GitHub is [safishamsi](https://github.com/safishamsi) ("Safi"); the Discord inviter's global name is "Safi (Graphify Labs)". **I did not find a verified personal X handle for him** and will not guess one.
- **I could not read any tweets.** `WebFetch` on `https://x.com/graphify` returned **HTTP 402 Payment Required** — X blocks unauthenticated fetches. A web search surfaced the account's existence and third-party coverage but **no readable post content**. **No tweets are quoted or summarized in this report.**
- Announcement [#773](https://github.com/Graphify-Labs/graphify/discussions/773) ("Follow us on X + Discord community coming soon") confirms X is an official channel. LinkedIn is also official ([#1598](https://github.com/Graphify-Labs/graphify/discussions/1598) "Graphify Labs is live on LinkedIn").
- ⚠️ A web search returned **`graphify.net`** ("Graphify — Knowledge Graph Skill for AI Coding Assistants"). This is **not** linked from the repo or from `graphify.com`, and the README explicitly warns that *"Other `graphify*` packages on PyPI are not affiliated."* I did not use it as a source and **you should treat `graphify.net` as unverified/possibly unaffiliated.**

---

## 4. Docs / website

- **[graphify.com](https://www.graphify.com)** — landing page. Positions **graphify Enterprise** as an always-on layer over meetings/files/docs/code ("free trial launching soon"). [Announcement #1798](https://github.com/Graphify-Labs/graphify/discussions/1798): "Graphify is now at graphify.com — Enterprise early access is open." The project [joined Y Combinator S26](https://github.com/Graphify-Labs/graphify/discussions/983).
- **[graphify.com/llms-full.txt](https://graphify.com/llms-full.txt)** — the highest-signal machine-readable doc; it's what I'd point an agent at. Notable framing found only here: relation tags are **`EXTRACTED` / `INFERRED` / `AMBIGUOUS`** *"so agents distinguish grounded facts from guesses"*, and answers carry *"explicit graph paths with real file:line citations."*
- Sub-pages: [/docs](https://graphify.com/docs), [/concepts](https://graphify.com/concepts), [/docs/mcp-tools](https://graphify.com/docs/mcp-tools), [/vs/rag](https://graphify.com/vs/rag), [/integrations](https://graphify.com/integrations).
- In-repo docs: [`docs/how-it-works.md`](https://github.com/Graphify-Labs/graphify/blob/v8/docs/how-it-works.md) (pipeline, confidence rubric, `ProcessPoolExecutor` AST parallelism ≈1.66× over sequential on 84 files), [`ARCHITECTURE.md`](https://github.com/Graphify-Labs/graphify/blob/v8/ARCHITECTURE.md), [`BENCHMARKS.md`](https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md), [`docs/docker-mcp-sqlite.md`](https://github.com/Graphify-Labs/graphify/blob/v8/docs/docker-mcp-sqlite.md).
- **No official blog found.** There's a paid book, ["The Memory Layer"](https://safishamsi.gumroad.com/l/qetvlo), linked from the README — I did not purchase or read it.
- **Doc inconsistency worth knowing:** README line 536 says query logging is on by default with `GRAPHIFY_QUERY_LOG_DISABLE=1` to opt out, while lines 520–521 say it's **off** by default and needs `GRAPHIFY_QUERY_LOG_ENABLE=1` (per [#1797](https://github.com/Graphify-Labs/graphify/issues/1797)). The opt-in text is the newer one. Log path: `~/.cache/graphify-queries.log`.

---

## Actionable best-practices distilled

**Build the graph outside your agent's context.** From [discussion #1931](https://github.com/Graphify-Labs/graphify/discussions/1931): run `graphify extract . --code-only` in a **terminal**, not `/graphify .` in chat — the latter spends your session's tokens on graph construction. Code parsing is tree-sitter-only: no API key, no LLM, zero cost.

**Local Ollama — the settings that actually matter:**
```bash
GRAPHIFY_OLLAMA_NUM_CTX=32768 \
GRAPHIFY_OLLAMA_KEEP_ALIVE=0 \
OLLAMA_BASE_URL=http://localhost:11434/v1 \
graphify extract ./docs --backend ollama \
  --max-concurrency 1 --token-budget 4000 --api-timeout 900 --max-workers 16
```
- `--max-concurrency 1` — the default of 4 is a *cloud* default and causes local queue congestion / VRAM OOM ([#792](https://github.com/Graphify-Labs/graphify/issues/792)).
- **Always set `GRAPHIFY_OLLAMA_NUM_CTX` explicitly.** Ollama's own default is 2048; anything larger silently returned empty ([#820](https://github.com/Graphify-Labs/graphify/issues/820)). Drop to 8192 if VRAM-constrained and pair with `--token-budget 4000`.
- `GRAPHIFY_OLLAMA_KEEP_ALIVE=0` unloads the model between chunks — saves VRAM on small GPUs.
- `--max-workers` is **AST** parallelism (independent of LLM concurrency) — raise it to your core count; the old hardcoded cap was 8.
- Set `OLLAMA_BASE_URL` explicitly and include `/v1`; graphify does **not** yet read Ollama's real `OLLAMA_HOST` ([#1940](https://github.com/Graphify-Labs/graphify/issues/1940), unfixed).

**Model choices (what's actually attested, not marketing):** community-reported working setups are `qwen3-coder-next` for extraction + `qwen3.5:122b` for labeling ([#1686](https://github.com/Graphify-Labs/graphify/issues/1686)), `gemma4:31b` on 24GB+ VRAM ([#792](https://github.com/Graphify-Labs/graphify/issues/792)), and — from an unmerged PR, so treat as a suggestion — `qwen2.5-coder:3b` then `gemma3:4b` for laptops ([#1549](https://github.com/Graphify-Labs/graphify/pull/1549)). **Disable "thinking" on any reasoning model** or `content` comes back empty (kimi #623, deepseek #1621).

**For any OpenAI-compatible server (vLLM, llama.cpp, LM Studio, OpenRouter, NIM), use `--backend openai`, not the Ollama shim.** This is the maintainer's explicit recommendation in [discussion #1365](https://github.com/Graphify-Labs/graphify/discussions/1365) — it's the cleaner code path and avoids the Ollama-specific quirks entirely:
```bash
OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_MODEL=<name-from-/v1/models> \
  graphify extract ./docs --backend openai
```

**When you see `LLM returned invalid JSON` / `Unterminated string`: don't panic, then fix the cap.** graphify auto-recovers by bisecting the chunk, so it's noise, not data loss. The reliable levers, in order: `GRAPHIFY_MAX_OUTPUT_TOKENS=16384` (or 32768) to lift the cap, then `--token-budget 4000` to shrink the input so the output shrinks with it. If your model has a hard output ceiling, only `--token-budget` helps.

**If you drive extraction through an agent harness (no API key), cap chunk size yourself.** [#1758](https://github.com/Graphify-Labs/graphify/issues/1758) is unfixed: the skill chunks by file count (20–25), not output size, and `--mode deep` on dense corpora blows the ~64k output-token turn limit — the chunk file is never written and the failure looks like a hang. Prefer a headless backend (which has bisection recovery) over the subagent path for deep mode, and treat "chunk file never appeared" as *too big*, not *wrong subagent type*.

**Query patterns that work, and the traps.** `graphify query "<q>" --dfs --budget 1500` for scoped traversal; `graphify path A B` for connection tracing; `graphify explain X` for one concept. There is **no `--context` flag**. Traps to design around: seed selection is naive substring matching on `label`, so image/doc nodes with caption-y labels hijack code queries ([#445](https://github.com/Graphify-Labs/graphify/issues/445), [#449](https://github.com/Graphify-Labs/graphify/issues/449)) — if you're building on top, do your own seed weighting by `file_type` and degree. And **`affected` silently returns empty on the natural ID guess** ([#2004](https://github.com/Graphify-Labs/graphify/issues/2004)) — resolve the real node ID first (or check `diagnose multigraph` for `dangling_endpoint_edges`) rather than trusting "No affected nodes found."

**Traverse with confidence-tier hop budgets, not uniform depth.** The single best technique I found, from a production user ([#1676](https://github.com/Graphify-Labs/graphify/issues/1676)): reverse-BFS with **EXTRACTED 6 hops / INFERRED 2 hops / AMBIGUOUS off**. It exploits the fact that `EXTRACTED` edges are deterministic tree-sitter facts (confidence 1.0) while `INFERRED` edges are the ones that hallucinate ([#437](https://github.com/Graphify-Labs/graphify/issues/437), [#1221](https://github.com/Graphify-Labs/graphify/pull/1221)). Edges live under `links`; direction is **source-depends-on-target**.

**Use the feedback loop — it's deterministic and free.** `save-result --outcome useful|dead_end|corrected` → `reflect --if-stale` at session start. The defaults are well-chosen: 30-day half-life, ≥2 corroborations before a node is "preferred", conflicts surfaced once with most-recent-wins, and citations to deleted nodes auto-dropped. `graphify hook install` runs `reflect` for you post-commit. Add `graphify curate` ([#1871](https://github.com/Graphify-Labs/graphify/pull/1871)) to your watch list if you need human corrections to survive rebuilds.

**Want byte-stable graphs? Skip the `[leiden]` extra.** The default install uses **Louvain, verified deterministic 20/20**; graspologic-Leiden retains a ~0.1% community-count wobble ([#1090](https://github.com/Graphify-Labs/graphify/discussions/1090)). If you compare graphs across runs, compare **co-membership signatures**, not community integer IDs.

**Large-project layout:** one master graph + type-scoped sub-graphs, wiki generated for the master only, scoped updates offloaded to nightly CI ([#645](https://github.com/Graphify-Labs/graphify/discussions/645)). Use `--no-viz` above ~5000 nodes. Use `--resolution` / `--exclude-hubs 99` to fight community fragmentation ([#446](https://github.com/Graphify-Labs/graphify/issues/446)). For cross-repo, `graphify extract --global --as <name>` + `graphify global list`.

**Team/multi-machine: commit `graphify-out/` to git.** Gitignore `graphify-out/cost.json` and `graphify-out/cache/` (mtime-based, invalid after a fresh clone). `graphify hook install` gives you free AST rebuilds *and* the `graph.json` union merge driver — verify it actually registered, since it silently didn't for a while ([#1902](https://github.com/Graphify-Labs/graphify/issues/1902)).

**Add `graph.json` + `graphify-out/` to `.claudeignore`.** Every extract writes into the workspace and invalidates Claude Code's prompt cache, forcing a full re-upload at cache-write rates on the next turn (README troubleshooting).

**A rules file alone will not make an agent use the graph.** From [discussion #921](https://github.com/Graphify-Labs/graphify/discussions/921) — a user's global `CLAUDE.md` rule was ignored; the fix was `graphify claude install`, which writes a **PreToolUse hook** that fires *at the moment the agent reaches for grep*. Maintainer's framing: *"it is not a soft instruction Claude can rationalize past; it is a hook that runs at the tool layer"* — and project-level `CLAUDE.md` beats user memory. `--strict` escalates the nudge to blocking the first raw source read of a session. Even so, expect to say "use graphify to find the affected modules first" for tasks the agent frames as *implementing* rather than *asking* ([#1931](https://github.com/Graphify-Labs/graphify/discussions/1931)).

**Two caveats to design around before you build a KB on this:** (1) **the semantic layer is largely disconnected from the AST graph** — fusion relies on exact node-id collision, and a real-world check found effectively zero code↔concept bridges ([#198](https://github.com/Graphify-Labs/graphify/issues/198), open). Don't assume doc→code linkage exists; measure it on your corpus. (2) **Images are read as text garbage on headless `extract`** — no backend sends them to a vision model ([#1109](https://github.com/Graphify-Labs/graphify/issues/1109), open), so image nodes are guessed from filenames. Video/audio is fine (local faster-whisper), but if you ingest untrusted URLs, note that the yt-dlp size-cap and URL-normalization hardening PRs ([#1436](https://github.com/Graphify-Labs/graphify/pull/1436), [#2021](https://github.com/Graphify-Labs/graphify/pull/2021)) are still open.

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the subject: issues, PRs, discussions, README, `docs/how-it-works.md`, BENCHMARKS/ARCHITECTURE references
- [Graphify-Labs](https://github.com/Graphify-Labs) — the org (created per discussion #1647)
- [safishamsi](https://github.com/safishamsi) — maintainer profile, to identify the author of the technical replies quoted above
- [Elbltagy2/jest-graph-tia](https://github.com/Elbltagy2/jest-graph-tia) — third-party Test Impact Analysis tool built on `graph.json`; source of the confidence-tier hop-budget technique and the verified schema facts (issue #1676). *Referenced from the issue; I did not read its source.*
- [FolatheDuckofDuckingburg/graphify](https://github.com/FolatheDuckofDuckingburg/graphify/tree/v8/benchmarks) — community fork hosting an independent benchmark framework (discussion #1328). *Referenced only.*
- [HKUDS/OpenHarness](https://github.com/HKUDS/OpenHarness) — the corpus used in issue #198 to demonstrate the AST/semantic disconnect. *Referenced only.*
- [anthropics/skills](https://github.com/anthropics/skills) — the cross-framework Agent-Skills spec targeted by `--platform agents`. *Referenced only.*
