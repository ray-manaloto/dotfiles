# Extraction model bake-off — graphify 0.9.22 on the 2-doc probe corpus

Corpus: `.omc/kb/probe/` — 2 documents.
Flags held constant across every run:

```bash
OLLAMA_NUM_PARALLEL=1 \
graphify extract .omc/kb/probe --backend ollama --model <M> \
  --out .omc/kb/graphs/<name> --max-concurrency 1 \
  --token-budget 12000 --api-timeout 900
```

## Leaderboard

Cross-document edges measured by **real `source_file`**, never by splitting node
ids on `_` (that heuristic gave a false 15/15 for qwen2.5-coder):

```python
src = {n['id']: n.get('source_file') for n in d['nodes']}
cross = sum(1 for e in d['links']
            if src.get(e['source']) and src.get(e['target'])
            and src[e['source']] != src[e['target']])
```

| model | nodes | edges | x-doc | out tok |
|---|---:|---:|---:|---:|
| qwen2.5-coder:14b | **16** | **15** | 1 | 3,142 |
| gemini-3.1-flash-lite | 13 | 10 | 0 | 3,167 |
| qwen3:14b (reasoning) | 9 | 6 | 0 | 2,013 |
| **gemma4:12b** (2026-07-20) | 8 | 6 | **2** | 7,479 |
| qwen3-coder (30B) | 5 | 4 | 0 | 999 |
| **claude-cli** (Claude Code sub) | — | — | — | **FAILED, rc=1** |

`gemma4:12b` capabilities: completion, vision, audio, tools, **thinking**
(no embedding — see `docs/graphify-local-embedding-pass.md` §1.1).

## The counts are the wrong metric — read the nodes

Both headline columns mislead on this corpus, and inspecting the actual output
reverses the ranking.

**gemma4's 8 nodes are all real concepts:**

```
'Graphify', 'Obsidian', 'Tree Sitter', 'Faster Whisper'   [doc 1]
'Graphify v0.9.20', 'Claude Code', 'NVIDIA NIM', 'Codex CLI'   [doc 2]
```

**qwen2.5-coder's 16 include the raw document titles as nodes** (`'Graphify +
Obsidian is INSANE: Build an AI Second Brain That Never Forgets'`) **and env-var
noise** (`OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`). So its node lead is partly
padding, not recall.

**The cross-document edges, qualitatively:**

| model | edge | verdict |
|---|---|---|
| gemma4 | `'Graphify v0.9.20' --semantically_similar_to--> 'Graphify'` | ✅ **the correct entity-resolution link** — the same tool named in both docs; this is exactly what cross-doc linking exists to find |
| gemma4 | `'Claude Code' --conceptually_related_to--> 'Obsidian'` | ⚠️ weak — both are "tools in an AI workflow", no substantive relation |
| qwen2.5-coder | `'<youtube title>' --references--> 'Graphify 0.9.20'` | ◐ plausible, but it links a *document node*, not two concepts |

gemma4 found the one genuinely valuable cross-document link that every other
model missed. It costs **2.4× the output tokens** to do it.

## ⚠️ This corpus cannot measure cross-document linking

The two documents are a YouTube transcript about Graphify + Obsidian and a
session log about Codex ↔ NVIDIA NIM. **They are topically disjoint** — they
share one entity (Graphify) and nothing else. The true cross-document edge count
is ~1–2, so the `x-doc` column has been ranking models on a metric with almost
no dynamic range.

Independently confirmed by embedding: `embeddinggemma` over the same 16 nodes
yields **zero** cross-document pairs at every threshold from 0.90 down to 0.70,
both label-only and context-enriched. See
`docs/graphify-local-embedding-pass.md` §2.4.

**Do not choose a model on this corpus's `x-doc` column.** Re-run on the full
137-document corpus in `.omc/kb/raw/` before treating cross-doc yield as signal.

## The `claude-cli` backend is BROKEN on Claude Code 2.1.216

graphify has a `claude-cli` backend (`llm.py:205-216`) that routes through the locally
installed `claude` CLI and bills to a Pro/Max subscription rather than an
`ANTHROPIC_API_KEY` — pricing declared as `{"input": 0.0, "output": 0.0}`.
It **does not work**, and the extraction is lost *after* the model has done it:

```
[graphify] LLM returned invalid JSON, skipping chunk (first 200 chars:
  'Knowledge graph extracted and delivered — 21 nodes, 20 edges, 3 hyperedges
   from the Codex↔NIM probe document.')
[graphify] claude-cli returned a hollow response; treating as truncation…
[graphify extract] graph is empty — extraction produced no nodes.
rc=1
```

Claude Code **did the work** — 21 nodes / 20 edges / 3 hyperedges would have beaten every
model in the table — then replied with an agentic *summary* instead of the raw JSON
payload. graphify's `_response_is_hollow` reads that as truncation, bisects, and converges
on nothing. The two semantic cache entries written are `partial: True`, `nodes: 0`.

### Diagnosis — four arms, cause isolated

| # | hypothesis | probe | result |
|---|---|---|---|
| 1 | our repo's ~107 KB eager `CLAUDE.md`/`AGENTS.md` context makes it behave agentically | re-ran in a clean room outside the repo | **REFUTED** — fails identically (`'Graph fragment extracted and delivered.'`) |
| 2 | user-level `~/.claude/CLAUDE.md` leaks in everywhere | `ls ~/.claude/CLAUDE.md` | **REFUTED** — does not exist, so the clean room really was clean |
| 3 | `claude -p --output-format json` can't return raw JSON | direct minimal prompt | **REFUTED** — returns `result: '{"nodes":[{"id":"a","label":"A"}],"edges":[]}'` exactly |
| 4 | graphify's own prompt construction triggers agentic behavior | ← by elimination, and see below | **CONFIRMED** |

`llm.py:1376-1391` documents this exact failure class and claims a fix — deliver the schema
in the **user turn** and drop `--system-prompt` — explicitly *"verified against Claude Code
**2.1.197**"*. We run **2.1.216**. The workaround has regressed in the intervening releases.

**Worth reporting upstream.** Until then, `claude-cli` is not a usable ingestion backend, and
the $0-cost path it advertises is unavailable.

## Caveats

- **n=1 run per model.** No variance estimate; graphify extraction is not
  deterministic across runs.
- 2 documents is too small to distinguish recall from verbosity.
- The `orchestra-ast` graph in the same directory (446 nodes / 810 edges / 27
  docs / **0** cross-doc) is AST-only and is not comparable to these semantic
  runs.

## Standing recommendation

`qwen2.5-coder:14b` remains the default for bulk ingestion on token cost and
throughput. `gemma4:12b` is the better *quality* extractor on this evidence and
is worth re-testing on the full corpus, where its 2.4× token cost is the real
question.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the
  extraction tool under test (0.9.22).
- [ollama/ollama](https://github.com/ollama/ollama) — local inference server
  (0.32.1) hosting every model in the table.
