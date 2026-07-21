# Local embedding pass for graphify — design spec

**Status: SPEC ONLY. Do not build from this yet.** Ray chose spec-first
(2026-07-20). Two of the design decisions below are still open, and one of the
probes in §2 invalidates the upstream issue's headline parameter — building
before those settle would ship the wrong thing.

Modelled on **[Graphify-Labs/graphify#7](https://github.com/Graphify-Labs/graphify/issues/7)**
— *"v0.4.0: local embeddings via quantized Gemma 4 (no API cost)"* — which is
**OPEN and unimplemented** as of graphify 0.9.22.

Everything below is grounded in probes against the installed 0.9.22 source and
a live Ollama 0.32.1. Full archaeology:
`.omc/kb/reports/agents/graphify-embedding-archaeology.md` (943 lines, with
file:line citations).

---

## 0. Why we want this

Issue #7 promises to *"make cross-file concept linking exhaustive rather than
sampled"*. That is precisely the weakness we measured in the extraction
bake-off: the best model produced **1 cross-document edge out of 15**.

The two mechanisms are complementary, not competing — the LLM extractor finds
the *interesting* cross-cutting edges, an embedding pass finds the *exhaustive*
ones. Both land in the same graph.

> ⚠️ **But see §2.4 — our probe corpus cannot measure this.** The two documents
> in `.omc/kb/probe/` are topically disjoint, so the correct cross-document edge
> count for that corpus is near zero and `1/15` may already be the ceiling. The
> motivating number needs re-measuring on the full 137-document corpus before it
> justifies any build.

---

## 1. Model and transport

### 1.1 Issue #7's model choice is wrong — verified

#7 specifies *"Gemma 4 Q4 or Q8 via llama.cpp or ollama"* for the embeddings.
A chat model and an embedding model are **different artifacts**, and Ollama
enforces the distinction as a declared capability.

Two-armed probe against Ollama 0.32.1, run against **the exact model #7 names**:

```
POST /v1/embeddings  {"model":"gemma4:12b","input":"x"}
→ {"error":{"message":"This server does not support embeddings.
             Start it with `--embeddings`","type":"api_error"}}

POST /v1/embeddings  {"model":"qwen2.5-coder:14b","input":"parse_config()"}
→ same error

POST /v1/embeddings  {"model":"embeddinggemma","input":"parse_config()"}
→ 200, data[0].embedding = 768 floats, usage.prompt_tokens = 6
```

Control arm (proves the probe discriminates rather than failing uniformly):

```
POST /v1/embeddings  {"model":"definitely-not-a-model:99b","input":"x"}
→ {"error":{"message":"model \"definitely-not-a-model:99b\" not found,
             try pulling it first","type":"not_found_error"}}
```

`ollama show` confirms the mechanism — capability is declared per model:

| model | capabilities |
|---|---|
| **`gemma4:12b`** — *the model #7 specifies* | completion, vision, audio, tools, thinking — **no embedding** |
| `qwen2.5-coder:14b` | completion, tools, insert |
| `qwen3:0.6b` | completion, tools, thinking |
| `qwen3-coder` | completion, tools |
| **`embeddinggemma`** | **embedding** |

`gemma4:12b` is a multimodal chat model. It cannot produce embeddings through
Ollama at all, so issue #7 as written is not implementable on its own stated
transport.

**Decision: use `embeddinggemma`** — Google's purpose-built embedding model in
the Gemma family, 621 MB, 768 dimensions, ~0 GPU pressure. It is almost
certainly what #7 meant. Note it produces embeddings *only*; it cannot be
reused for extraction.

*(Worth reporting on #7 — the maintainers are currently debating ONNX Runtime
vs Ollama for a model that does not embed under either.)*

### 1.2 Transport

graphify already speaks to Ollama through the **`openai` Python SDK against the
OpenAI-compatibility layer** — `client.chat.completions.create` at `llm.py:1230`,
`:1513`, `:2560`. The same client exposes `client.embeddings.create`, and Ollama
serves `/v1/embeddings` on the same port.

So the reusable plumbing is: `_resolve_ollama_base_url` (`llm.py:60-97`), the
timeout/`keep_alive` handling, and the serialization guard. **The call itself is
new** — there is no embeddings code path anywhere in 0.9.22 (§4e of the
archaeology, control-armed: `grep 'embeddings'` → empty while
`grep 'chat.completions'` → 5 hits).

Per-request shape:

```python
resp = client.embeddings.create(model="embeddinggemma", input=[t1, t2, ...])
vecs = [d.embedding for d in resp.data]
```

Batch the `input` list — Ollama accepts arrays and it removes per-node HTTP
overhead. Keep `OLLAMA_NUM_PARALLEL=1` as with extraction (root cause of
graphify #798); leave `GRAPHIFY_OLLAMA_NUM_CTX` **unset** (auto-derived since
v0.7.13).

---

## 2. What gets embedded — the load-bearing decision

### 2.1 A graphify node has almost no text

#7 says to embed *"label + docstring"*. **There is no docstring field.** Nor
summary, description, signature, snippet, body, or source text — confirmed by
source grep *and* by an empirical key census of 3,157 real nodes in this repo's
own graph (archaeology §6d):

```
NODE keys: label, file_type, source_file, source_location, _origin, id,
           community, community_name, norm_label, metadata(40/3157)
```

The only text-bearing fields are **`label`** (a 1–4 word human-readable name)
and `norm_label` (its lowercased form). Everything else is a path, a line
number, or a cluster id.

### 2.2 Label-only embedding does not work — measured

The exact experiment #7 proposes, run over the 16 nodes of
`.omc/kb/graphs/bake-q25c/graphify-out/graph.json` with `embeddinggemma`
(120 pairs):

| rank | cos | x-doc | pair |
|---:|---:|:---:|---|
| 1 | 0.899 | – | `'Claude Code' ~ 'Free Claude Code'` |
| 8 | 0.649 | **YES** | `'OpenAI Codex' ~ 'Obsidian'` |
| 10 | 0.643 | **YES** | `'Obsidian' ~ 'Ollama'` |
| 12 | 0.622 | **YES** | `'Obsidian' ~ 'OpenAI API'` |
| 14 | 0.606 | – | `'Graphify 0.9.20' ~ 'Graphify llm.py'` |

Two failures at once:

1. **The top cross-document pairs are lexical collisions.** Obsidian, Ollama,
   OpenAI and Codex are unrelated tools that share an initial letter and a
   short-token shape. This is the same failure mode PR #1871's worked example
   cites (`page_not_found ~ patient_search`, *"lexical collision on 'not
   found'"*). The one genuinely related pair ranks **below** all three.
2. **#7's default threshold does nothing.** At `--embed-threshold 0.82` the pass
   emits **1 edge, 0 cross-document**:

   | threshold | edges | cross-doc |
   |---:|---:|---:|
   | 0.90 | 0 | 0 |
   | **0.82** | **1** | **0** |
   | 0.75 | 3 | 0 |
   | 0.70 | 5 | 0 |

   There is no threshold that admits the real edge without first admitting three
   false ones. The ordering is wrong, so no cut point fixes it.

### 2.3 Context enrichment fixes the ordering — measured

Second arm: embed `label` **plus the sentences in its source document that
mention the label** (1,200-char cap). Same nodes, same model, same corpus:

| rank | cos | pair |
|---:|---:|---|
| 1 | 0.939 | `'Codex CLI ↔ NVIDIA NIM — empirical probe results' ~ 'NVIDIA NIM'` |
| 2 | 0.854 | `'codex-plugin-cc' ~ 'Claude Code'` |
| 4 | 0.757 | `'OpenAI Codex' ~ 'OpenAI API'` |

**Every lexical collision drops out of the top 20**, and real relations take the
top slots. 5 of 16 nodes had no sentence match and fell back to label-only.

**So the spec's answer to "what gets embedded" is: not what #7 says.** Three
options, in order of cost:

| option | text embedded | cost | drawback |
|---|---|---|---|
| **A (recommended)** | `label` + mention-sentences from the source doc, re-read at embed time | one extra file read per source doc | needs the corpus present at embed time; heuristic sentence match |
| B | `label` + a slice via `file_slice.py` and `source_location` | cheap; the module already exists | line-anchored, so it works for code nodes and poorly for document concepts |
| C | a new `summary` node field written at extraction time | best signal | changes the extraction prompt and invalidates the whole semantic cache |

**A** is recommended: it needs no upstream change, no cache invalidation, and it
is the arm that was actually measured. **C** is the right long-term shape and is
worth proposing upstream on #7 independently.

### 2.4 ⚠️ The motivating metric is not measurable on the probe corpus

Every threshold in both arms yields **zero** cross-document edges — and that is
not a failure of the method. `.omc/kb/probe/` holds exactly two documents: a
YouTube transcript about Graphify + Obsidian, and a session log about Codex ↔
NVIDIA NIM. **They are topically disjoint.** The true cross-document edge count
for that corpus is at or near zero.

This has a consequence beyond this spec: the extraction bake-off has been
ranking models on an `x-doc` column that **this corpus cannot express**.
qwen2.5-coder's `1/15` is plausibly the ceiling, not a shortfall. Before either
this pass or a model choice is justified by cross-document yield, re-measure on
the full **137-document** corpus in `.omc/kb/raw/`.

*(This is the probes-need-a-control-arm rule applied to a metric: a number that
can only come out low is not evidence about the model.)*

---

## 3. Threshold and edge shape

### 3.1 Edge record

`validate.py:4-7` sets the closed vocabularies:

```python
VALID_CONFIDENCES = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
REQUIRED_EDGE_FIELDS = {"source", "target", "relation", "confidence", "source_file"}
```

An emitted edge:

```json
{
  "source": "<node_id_a>",
  "target": "<node_id_b>",
  "relation": "semantically_similar_to",
  "confidence": "INFERRED",
  "confidence_score": 0.87,
  "source_file": "<source_file of the SOURCE endpoint>",
  "source_location": null,
  "weight": 1.0,
  "_origin": "embed"
}
```

Two notes on that record:

- **`relation` is an open vocabulary.** There is no `VALID_RELATIONS` set
  anywhere; `validate.py` checks the *key* is present but never its *value*. The
  live graph already contains 12 relation values, 9 of which are absent from the
  prompt list at `llm.py:478`. So `semantically_similar_to` is safe to emit —
  and it earns a **1.5× surprise-score bonus** (`analyze.py:251-254`) plus a
  report tag (`report.py:179`).
- **`_origin: "embed"` is our own marker**, mirroring the `_origin: "ast"` that
  `extract.py:5153-5162` stamps on every AST node and edge. It is load-bearing
  for §5. Leading-underscore keys are stripped from GraphML export
  (`export.py:977-982`) but **persist in `graph.json`**.

### 3.2 Threshold

**Do not adopt #7's 0.82.** §2.2 shows it was chosen without measurement and
yields one edge. Derive it instead:

1. Run the pass with **no** threshold over the full corpus, dumping all pairs.
2. Hand-label the top ~100 by cosine as true/false.
3. Pick the cut that maximises precision at a recall the corpus can support.
4. Record the corpus, the model, and the date next to the number — a threshold
   without its conditions is not portable between corpora or embedding models.

Ship it as `--embed-threshold`, defaulting to whatever step 3 produces, and
**also** cap absolute edge count per node (`--embed-top-k`, default ~5). An
exhaustive pass over N nodes is O(N²) pairs — 3,157 nodes is ~5M comparisons,
which is fine to compute but catastrophic to *write* into a graph that currently
holds 4,642 edges.

---

## 4. Caching

Mirror graphify's existing structure rather than inventing one. `cache.py:454`:

```python
def cache_dir(root=Path("."), kind="ast", prompt_fp=None) -> Path:
    d = base / "cache" / kind
```

So the embedding cache is `kind="embeddings"` →
`graphify-out/cache/embeddings/`, sitting beside `ast/`, `semantic/`, and
`semantic-deep/`.

**Key** — deliberately *not* graphify's `file_hash` (which is
`SHA256(file_bytes || \0 || relpath)` and keyed to a *file*). An embedding is
keyed to a *node's embedded text*:

```
SHA256(model_name || "\0" || embedded_text)
```

Keying on the text rather than the node id means a renamed node with unchanged
text is a cache hit, and a node whose surrounding context changed is a miss —
both correct. Including the model name means switching embedding models
invalidates cleanly rather than silently mixing vector spaces.

**Value**: `{"model": "...", "dims": 768, "vector": [...]}`. At 768 float32 that
is ~3 KB per node uncompressed; 3,157 nodes ≈ 10 MB. Acceptable.

**Invalidation** is then automatic and needs no version namespace, unlike the
AST cache. Note that graphify has **no `--clear-cache` and no `--no-cache`**
(archaeology §8c — `cache.clear_cache` exists at `cache.py:647` with *zero
callers*); the only reset is `rm -rf graphify-out/cache/`. Match that rather
than adding a flag that graphify itself lacks.

---

## 5. ⭐ How the edges survive a rebuild — the hard part

This is the section that decides whether the feature is real or decorative. An
embedding edge is *by construction* the shape graphify destroys most reliably:
it spans two source files, and it is not regenerable by any extractor.

### 5.1 Both destruction mechanisms, cited

**Added edges are destroyed** — `build.py:1114-1131`:

```python
new_sources: set[str] = set()
for ch in new_chunks:
    for n in ch.get("nodes", []):          # <- built from NODES only
        ...
        new_sources.add(sf)
if new_sources:
    def _kept(item: dict) -> bool:
        sf = item.get("source_file")
        return sf not in new_sources and _norm_source_file(sf, _replace_root) not in new_sources
    existing_nodes = [n for n in existing_nodes if _kept(n)]
    existing_edges = [e for e in existing_edges if _kept(e)]   # <- edges too
```

An edge is filtered by **its own single `source_file` scalar**, never by its
endpoints. Whatever file we stamp on a cross-document edge, the moment that file
is re-extracted the edge is dropped — and nothing re-emits it.

**Deleted edges come back** — the semantic cache is keyed by file *content*
(`cache.py:312-318`), so a hand-edited `graph.json` changes no source bytes, the
cache still hits, and `build()` re-adds the fragment.

**The only shrink guard doesn't help** (`build.py:1237-1246`): it counts **nodes
only**, and it is skipped when `dedup` is true — which is the default. Edge loss
is never guarded. Upstream issue **#1711** describes this same class of silent
edge loss; **PR #1871** (`graphify curate`) proposes a fix but is a third-party
PR, open since 2026-07-13 with **no review**. Neither is available to build on.

### 5.2 The lever: `watch.py` is provenance-aware, `build_merge` is not

`watch.py:588-604`:

```python
preserved_edges = [
    edge for edge in existing.get("links", existing.get("edges", []))
    if edge.get("source") in all_ids and edge.get("target") in all_ids
    and not source_paths.is_evicted(edge, edge_evicted_source_identities)
    and not (edge.get("_origin") == "ast"
             and source_paths.is_evicted(edge, rebuilt_source_identities))
]
```

An edge is evicted **only if** `_origin == "ast"` *and* its source was rebuilt.
An edge carrying `_origin: "embed"` — or no `_origin` at all — **survives an AST
re-extraction of its source file on the watch path**, and is additionally
protected by an endpoint-existence check.

`build_merge`'s `_kept()` has no such clause. **The same edge survives
`graphify watch` and dies under `graphify extract`.** This asymmetry reads as an
upstream bug, not a designed contract, and it is the single most useful lever
available.

### 5.3 Three strategies

| # | strategy | durable? | cost | risk |
|---|---|:---:|---|---|
| **1** | **Idempotent re-injection** — run the pass after every build as a post-step | yes, by reconstruction | one pass per build (cached ⇒ cheap) | none upstream; a rebuild is briefly missing the edges |
| **2** | **`merge-chunks`** — emit a `.graphify_chunk_*.json` and let graphify fold it in | partially | lowest | still subject to `build_merge` replace on the next extract |
| **3** | **Patch `build_merge`'s `_kept()` to be `_origin`-aware** and upstream it | yes, properly | ~3 lines + a test | needs upstream review; #1871 shows that queue is slow |

**Recommended: 1 as the mechanism, 3 as the contribution.**

Strategy 1 sidesteps the entire durability problem by not needing durability —
if the pass is deterministic, cached, and re-run after every build, a destroyed
edge is simply recomputed for free. This is the honest reading of §5.1: the
graph is a *projection* of (cache ∪ extraction), so the way to make something
survive is to make it part of the projection, not to defend it inside the graph.

Strategy 3 is the right fix and is a genuinely small diff — worth opening
upstream regardless, with the `watch.py`/`build_merge` asymmetry as the
argument. It should not gate our implementation.

### 5.4 On `merge-chunks` — the sanctioned injection API

Worth recording because it is **undocumented in `--help`** but present in the
dispatch table (`cli.py:3497`):

```python
elif cmd == "merge-chunks":
    # graphify merge-chunks <chunk_glob_or_files...> --out <path>
    # Concatenates .graphify_chunk_*.json files written by semantic subagents.
```

`cli.py:3527-3533` treats these files as **untrusted external input** and
validates size caps and the node/edge id charset. So graphify already expects an
external process to hand it `{"nodes":[...],"edges":[...]}` — an embedding pass
emitting a chunk file is using the mechanism as intended, and is the correct
*format* for strategy 1's output even though it does not by itself solve
durability.

Note also that validation is **advisory**: `validate.assert_valid`
(`validate.py:90`) has zero callers, and `build_from_json` only prints a warning
(`build.py:540-543`). Do not rely on graphify to reject a malformed injection —
validate on our side.

---

## 6. Proposed surface

Nothing here is built. Written as it would land in this repo, per
`.claude/rules/mise-tasks-only.md` (a recurring workflow ships as a `python/`
module plus a mise task) and `.claude/rules/zero-bash-logic.md`.

```
python/src/dotfiles_setup/graph_embed.py     # the pass; no bash
mise run graph-embed                          # thin task wrapper
```

```bash
mise run graph-embed -- --graph .omc/kb/graphs/<name>/graphify-out/graph.json \
                        --corpus .omc/kb/raw \
                        --model embeddinggemma \
                        --threshold <derived, §3.2> --top-k 5
```

It reads `graph.json`, builds enriched text per §2.3, embeds with the §4 cache,
emits `semantically_similar_to` edges per §3.1, and writes them back
idempotently (strategy 1). Re-running on an unchanged graph must be a no-op —
that is the acceptance test.

**Acceptance criteria** (adapted from #7, with the unmeasurable ones removed):

- [ ] Re-run on an unchanged corpus adds zero new embeddings and zero new edges.
- [ ] Every emitted edge validates against `REQUIRED_EDGE_FIELDS` and
      `VALID_CONFIDENCES`.
- [ ] The pass survives a `graphify extract` + re-run cycle with an identical
      resulting edge set.
- [ ] Threshold is derived from labelled data on the 137-doc corpus (§3.2), and
      the corpus/model/date are recorded beside it.
- [ ] A control arm: a corpus with known-unrelated documents produces
      approximately zero cross-document edges.

---

## 7. Open decisions

1. **Enrichment strategy — A, B, or C (§2.3).** Recommended **A**. C is better
   but invalidates the semantic cache and needs an upstream prompt change.
2. **Whether to open the `build_merge` `_origin` patch upstream** (§5.3
   strategy 3) before or after building our own pass. Recommended: open it
   independently; do not let it gate us.
3. **Whether this is worth building at all** until §2.4 is resolved. The
   motivating number (`1/15` cross-document edges) came from a corpus that
   cannot express the metric. Re-measure on `.omc/kb/raw/` first.

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the
  subject: issue #7 (the feature being specced), PR #1871 (`graphify curate`,
  open, unreviewed), issues #1711 / #1800 / #834, and the installed 0.9.22
  source (`build.py`, `cache.py`, `validate.py`, `llm.py`, `watch.py`,
  `analyze.py`, `report.py`, `export.py`, `extract.py`, `cli.py`).
- [ollama/ollama](https://github.com/ollama/ollama) — the local inference
  server; probed live at 0.32.1 for `/v1/embeddings` capability semantics and
  the `embeddinggemma` model.
- [openai/openai-python](https://github.com/openai/openai-python) — the client
  SDK graphify uses for every backend including Ollama; named, source not read.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo;
  its `graphify-out/graph.json` supplied the 3,157-node key census and
  `.omc/kb/` supplied the probe corpus.

## See also

- `.omc/kb/reports/agents/graphify-embedding-archaeology.md` — the full
  archaeology with file:line citations and an explicit non-findings table.
- `.claude/rules/probes-need-a-control-arm.md` — the rule §1.1 and §2.4 apply.
- `.claude/rules/tool-currency-and-native-first.md` — why #7's asserted
  parameters were re-probed rather than adopted.
