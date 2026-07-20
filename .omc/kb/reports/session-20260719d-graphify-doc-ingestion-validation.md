# graphify doc-ingestion: validation on OUR corpus — NEGATIVE result

Date: 2026-07-19. Backend: local Ollama `qwen3:14b` via `--backend openai`
+ `OPENAI_BASE_URL=http://localhost:11434/v1` (maintainer-preferred path).
Corpus: 2 documents, 17 KB — one YouTube transcript
(`22iy2mDFiF8.md`, "Graphify + Obsidian") and one dense technical report
(`session-20260719d-codex-nim-probes.md`).

This is the test the community-mining report said to run before betting on
semantic enrichment: *"validate the semantic-enrichment claim on your own corpus
before committing."* **It failed.**

## Run result

```
found 0 code, 2 docs, 0 papers, 0 images
semantic extraction on 2 files via openai... chunk 1/1 done
wrote graph.json: 9 nodes, 6 edges, 3 communities
tokens: 5,315 in / 2,013 out
rc=0, elapsed 165s
```

The pipeline **works** — rc=0, no hangs, no crashes, 165 s for 2 docs
(≈35 min extrapolated for all 26). Mechanically sound. The problem is the
output.

## Finding 1 (STRUCTURAL, will NOT improve with a better model)

**Node IDs are namespaced by source file, so there is zero cross-document
fusion.**

```
22iy2mDFiF8_graphify                          :: "Graphify"
session-20260719d-codex-nim-probes_graphify_0_9_20 :: "Graphify 0.9.20"
```

Both documents discuss graphify. They produce **separate, unlinked nodes**.

Measured:
- **cross-document edges: 0 / 6**
- duplicate labels across docs: **none** (because each is namespaced apart)
- **all 3 communities span exactly 1 document each**

Clustering cannot fix this: community detection runs over the edge set, and the
edge set has no cross-document edges to find.

**Consequence:** what is produced is not *a* knowledge graph. It is *N
disconnected per-document mini-graphs* sharing a file. A query like "what do we
know about graphify across every source we've ingested" cannot be answered by
traversal, because no path exists between documents.

This is the documented issue [#198](https://github.com/Graphify-Labs/graphify/issues/198)
("semantic layer is mostly disconnected") in a sharper form — not merely
AST↔semantic disconnect but **doc↔doc** disconnect, caused by ID namespacing
rather than by extraction quality. `merge-graphs` / `global add` union files;
they do not create semantic bridges.

## Finding 2 (QUALITY, may partly improve with a stronger model)

**Extraction is shallow.** 17 KB of dense prose yielded **9 concept nodes**.
The probe report alone contains dozens of discrete, load-bearing facts
(the compiled-in `wire_api = "chat"` removal string, the 405-vs-404
discrimination method, ToS §1.2/§3.3(iv), six real NIM model IDs, issue
numbers). Essentially none were captured.

Compare maintainer-acknowledged
[#1890](https://github.com/Graphify-Labs/graphify/issues/1890): 53% of docs lost
**even with gpt-5** — so this is not purely a small-model artifact.

## Finding 3 (ACCURACY — the dangerous one)

The extractor emitted:

```
NVIDIA NIM --supports--> Responses API   (confidence: EXTRACTED)
```

The source document **explicitly refuses that claim.** It states: *"405 proves
route registration, not a working Responses implementation"* and *"NIM plausibly
speaks Responses — unconfirmed."*

The extractor **flattened a carefully hedged, control-armed finding into a
confident assertion.** A future agent querying this graph would be told, with
apparent authority, something the underlying evidence explicitly does not
support — and the hedge is not recoverable from the graph.

This is the **false-authority** failure mode that
[#2051](https://github.com/Graphify-Labs/graphify/issues/2051) raises for stale
nodes, arriving here through a different door: not staleness, but
**hedge-flattening at extraction time.** For a knowledge base whose whole
purpose is feeding autonomous agents, this is the most serious defect of the
three.

## Finding 4 — confidence is not a number

Every edge carries `confidence: "EXTRACTED"` — a constant string. There is no
numeric confidence to threshold on, so any design that planned to filter edges
by confidence has nothing to filter on. (Note this differs from
[#540](https://github.com/Graphify-Labs/graphify/issues/540)'s bimodal-0.5/0.85
report, which described INFERRED edges; the doc path here emits a literal.)

## What still holds

- **The AST/code path remains excellent** and is unaffected: deterministic,
  0 tokens, 3,157 nodes for this repo, 446 for claude-code-orchestra, with
  working control-armed BFS query. That was always the solid part.
- The ingestion **mechanism** is reliable — bounded, resumable, cheap locally.
  If the fusion and hedging problems were solved, the plumbing is ready.

## Recommendation

**Do not build the autonomous program's knowledge layer on graphify's semantic
doc ingestion as it currently behaves.** Specifically:

1. **Keep** graphify for what it is good at: the deterministic code graph.
2. **Do not** treat the doc graph as a cross-source knowledge base — it cannot
   join sources, which is the single property the knowledge layer needs.
3. If doc retrieval is needed now, prefer a method that preserves the source
   text and its hedges (the documents are already clean Markdown in
   `.omc/kb/`; plain retrieval over them loses nothing that the graph adds).
4. Re-test if upstream lands identifier normalization / fuzzy bridging (the
   contributor work referenced in #198). This validation is cheap to repeat —
   165 s.

## Reproduction

```
INGEST_TIMEOUT=900 INGEST_LOG=/tmp/kb-probe.log \
  ingest_kb.sh .omc/kb/probe .omc/kb/graphs/probe qwen3:14b
```

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the tool
  under validation; issues #198, #540, #1890, #2051 referenced against observed
  behavior.

---

## ADDENDUM — a confound was raised, tested, and REFUTED (same session)

After the original run, `graphify-mining`'s best-practices section surfaced:
*"**Disable 'thinking' on any reasoning model** or `content` comes back empty"*
(kimi #623, deepseek #1621). The probe above used **qwen3:14b — a reasoning
model** — so the shallow-extraction finding was potentially measuring a starved
model rather than graphify.

### The confound is real at the API level

```
qwen3:14b via /v1/chat/completions, max_tokens=600:
  reasoning chars: 2459
  content   chars: 0          <-- ZERO
  finish_reason  : length
```

At `max_tokens=4000`: reasoning 2618 **+ content 563**, `finish=stop`. Ollama's
native API with `think:false`: thinking 0, clean content. So the mechanism is
genuine — a reasoning model can consume its entire output budget before emitting
anything. `/no_think` does **not** pass through the OpenAI-compat layer.

### But it did NOT affect graphify — tested directly

`GRAPHIFY_MAX_OUTPUT_TOKENS` **is** honored by 0.9.20 (`llm.py:264-265`). Re-ran
the identical corpus with it raised to `16384`, into a **separate output
directory**:

| | probe 1 | probe 2 (`MAX_OUTPUT_TOKENS=16384`) |
|---|---|---|
| nodes / edges / communities | 9 / 6 / 3 | **9 / 6 / 3** |
| tokens | 5,315 in / 2,013 out | **5,315 in / 2,013 out** |
| cross-document edges | 0 / 6 | **0 / 6** |
| `graph.json` md5 | `87061d46…7bc6b` | **`87061d46…7bc6b`** |

**Freshness control (this is what makes the comparison valid):** probe2 wrote its
own semantic cache at **18:10:51** vs probe1's **17:45:17**, in its own
directory. A real re-extraction, not a replayed cache — which matters, since
graphify's semantic cache has a history of stale replays (#1939, #1894).

### Conclusion

**Confound REFUTED.** The output cap was never the binding constraint — the
model produced 2,013 output tokens and stopped naturally, with room for both
reasoning and content. **Findings 1, 2 and 3 stand as originally reported.**

Two bonus results:
- **Byte-identical `graph.json` across two independent runs** corroborates the
  maintainer's determinism claim for the default (Louvain) install — 2/2 here
  against their reported 20/20. Our `[all]` pin lands on the deterministic side.
- Still **UNVERIFIED**: whether a *non-reasoning* model yields richer extraction.
  The "starved by cap" mechanism is dead, but reasoning tokens still occupy part
  of each response. Testing that needs a non-reasoning model pulled locally.

### Method note

The original write-up asserted three findings as if equally supported. Only
Finding 1 (structural ID namespacing) was ever immune to model choice; 2 and 3
required this second arm before they deserved the same confidence. Raising a
confound and testing it cost ~5 minutes and converted an assumption into a
result.
