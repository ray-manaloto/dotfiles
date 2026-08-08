# graphify 0.9.22 — code archaeology for the embedding/semantic-edge design spec

**Package root (read-only):**
`/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.22/graphifyy/lib/python3.14/site-packages/graphify`

**Status: COMPLETE.** Written incrementally during the sweep.
Upstream: <https://github.com/Graphify-Labs/graphify> (from `graphifyy-0.9.22.dist-info/METADATA`).

---

## 1. Edge/link schema

### 1a. The authoritative schema line (the LLM prompt contract)

`llm.py:478` — the JSON shape graphify asks the model to emit:

```json
{"nodes":[{"id":"stem_entity","label":"Human Readable Name","file_type":"code|document|paper|image|rationale|concept","source_file":"relative/path","source_location":null,"source_url":null,"captured_at":null,"author":null,"contributor":null}],"edges":[{"source":"node_id","target":"node_id","relation":"calls|implements|references|cites|conceptually_related_to|shares_data_with|semantically_similar_to","confidence":"EXTRACTED|INFERRED|AMBIGUOUS","confidence_score":1.0,"source_file":"relative/path","source_location":null,"weight":1.0}],"hyperedges":[{"id":"snake_case_id","label":"Human Readable Label","nodes":["node_id1","node_id2","node_id3"],"relation":"participate_in|implement|form","confidence":"EXTRACTED|INFERRED","confidence_score":0.75,"source_file":"relative/path"}],"input_tokens":0,"output_tokens":0}
```

So an **edge** carries: `source`, `target`, `relation`, `confidence`,
`confidence_score`, `source_file`, `source_location`, `weight`.

### 1b. `confidence` — the values, and the validator

`validate.py:4-7`:

```python
VALID_FILE_TYPES = {"code", "document", "paper", "image", "rationale", "concept"}
VALID_CONFIDENCES = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
REQUIRED_NODE_FIELDS = {"id", "label", "file_type", "source_file"}
REQUIRED_EDGE_FIELDS = {"source", "target", "relation", "confidence", "source_file"}
```

`validate.py:65-72` — required-field + confidence enforcement:

```python
            for field in REQUIRED_EDGE_FIELDS:
                if field not in edge:
                    errors.append(f"Edge {i} missing required field '{field}'")
            if "confidence" in edge and edge["confidence"] not in VALID_CONFIDENCES:
                errors.append(
                    f"Edge {i} has invalid confidence '{edge['confidence']}' "
                    f"- must be one of {sorted(VALID_CONFIDENCES)}"
                )
```

**`relation` is REQUIRED but its VALUE is NOT validated** — there is no
`VALID_RELATIONS` set anywhere in `validate.py`. The relation vocabulary is
open. (See §5.)

### 1c. Provenance: is there a field distinguishing extractor-derived edges?

`confidence` IS the de-facto provenance field. Deterministic extractors stamp
`EXTRACTED` / `1.0`; heuristic resolution stamps `INFERRED` / `0.8`:

- `manifest_ingest.py:103-104` → `"confidence": "EXTRACTED"`, `"confidence_score": 1.0`
- `ruby_resolution.py:109-110` → `"confidence": "EXTRACTED"`, `"confidence_score": 1.0`
- `symbol_resolution.py:289-290`, `:498-499`, `:546-547` → `EXTRACTED` / `1.0`
- `symbol_resolution.py:369-370` → `"confidence": "INFERRED"`, `"confidence_score": 0.8`
- `cargo_introspect.py:103` → `"confidence": _CONFIDENCE_EXTRACTED`

Default when absent is `EXTRACTED` almost everywhere it is read
(`export.py:303`, `:400`, `:519`, `:578`, `:946`, `:1064`; `serve.py:1335`, `:1551`).

`callflow_html.py:210` normalizes from several aliases — this is the only place
the word "provenance" appears as a field name, and it is only an *input alias*:

```python
confidence = first_present(
    edge, "confidence", "evidence", "provenance", default="EXTRACTED"
)
score = first_present(
    edge, "confidence_score", "score", "weight", "probability", default=1.0
)
```

_(sections 2-8 to follow)_

---

## 2. `build_merge` — the per-`source_file` replace that destroys hand edits

`build.py:1044-1062` — signature + docstring (the contract is stated outright):

```python
def build_merge(
    new_chunks: list[dict],
    graph_path: str | Path | None = None,
    prune_sources: list[str] | None = None,
    *,
    directed: bool = False,
    dedup: bool = True,
    dedup_llm_backend: str | None = None,
    root: str | Path | None = None,
) -> nx.Graph:
    """Load existing graph.json, merge new chunks into it, and save back.

    Re-extracted files REPLACE their prior contribution: any source_file present
    in new_chunks is dropped from the loaded graph before merging, so a changed
    file's stale nodes/edges don't accumulate. Files absent from new_chunks are
    preserved unchanged; deleted files are removed via prune_sources.
    Safe to call repeatedly.
```

### 2a. The destroying lines — `build.py:1114-1131`

```python
new_sources: set[str] = set()
for ch in new_chunks:
    for n in ch.get("nodes", []):
        sf = n.get("source_file")
        if not sf:
            continue
        new_sources.add(sf)
        norm = _norm_source_file(sf, _replace_root)
        if norm:
            new_sources.add(norm)
if new_sources:

    def _kept(item: dict) -> bool:
        sf = item.get("source_file")
        return (
            sf not in new_sources
            and _norm_source_file(sf, _replace_root) not in new_sources
        )

    existing_nodes = [n for n in existing_nodes if _kept(n)]
    existing_edges = [e for e in existing_edges if _kept(e)]

base = [{"nodes": existing_nodes, "edges": existing_edges}] if had_graph else []
```

**Why a hand-added edge dies.** An edge is filtered by **its own single
`source_file` scalar field** (`build.py:1126-1127`), not by its endpoints. An
edge is a flat record with ONE `source_file`. So a hand-added edge spanning
`a.py` → `b.py` must be stamped with *some* `source_file`; whichever file that
is, the moment that file (or any file the author guessed) is re-extracted and
appears in `new_sources`, `_kept()` returns `False` and the edge is dropped from
`existing_edges` before the merge (line 1129). The re-extraction of the *other*
endpoint's file has no protective effect at all — there is no endpoint-aware
retention anywhere in this function.

Worse, the `new_sources` set is built from the new chunks' **nodes** only
(line 1116, `ch.get("nodes", [])`), so a re-extraction that emits a node for file
X marks X for replacement, and every hand edge stamped `source_file: X` is
deleted regardless of what the new chunk's edges contain.

**Why a hand-DELETED edge comes back.** Deletion from `graph.json` only removes it
from `existing_edges` — but `existing_edges` is discarded for that source
anyway, and the authoritative content for that `source_file` is rebuilt from
`new_chunks`, which come from the extractor or **from the content-keyed cache**
(§3). Since the file's bytes are unchanged, the cache serves the *same* stored
`{"nodes": [...], "edges": [...]}` fragment it stored before, and `build()`
re-adds the deleted edge. The graph is a projection of (cache ∪ fresh
extraction); hand-editing the projection is not durable.

The only two escape hatches in the whole function are:
- `prune_sources` (whole-file deletion, `build.py:1204-1235`), and
- `prune_set -= new_sources` (`build.py:1161`) — "replace" deliberately WINS over
  a contradictory "delete" of the same source (#1796), so you cannot even use
  `prune_sources` to suppress a re-extracted file.

### 2b. The only shrink guard — and why it doesn't help

`build.py:1237-1246`:

```python
    # Safety check: refuse to shrink the graph silently (#479)
    # Skip when dedup or prune_sources is active — shrinkage is intentional there.
    if graph_path.exists() and not dedup and not prune_sources:
        existing_n = len(existing_nodes)
        new_n = G.number_of_nodes()
        if new_n < existing_n:
            raise ValueError(
                f"graphify: build_merge would shrink graph from {existing_n} → {new_n} nodes. "
                f"Pass prune_sources explicitly if you intend to remove nodes."
            )
```

It counts **nodes only**, and `dedup` defaults to `True` (line 1050), which
disables the guard entirely on the default path. Edge loss is never guarded.

---

## 3. The cache — the mechanism that re-injects deleted edges

### 3a. Location on disk

`cache.py:454-482`:

```python
def cache_dir(
    root: Path = Path("."), kind: str = "ast", prompt_fp: str | None = None
) -> Path:
    ...
    _out = Path(_GRAPHIFY_OUT)
    base = _out if _out.is_absolute() else Path(root).resolve() / _out
    d = base / "cache" / kind
    if kind == "ast":
        d = d / f"v{_EXTRACTOR_VERSION}"
        _cleanup_stale_ast_entries(d.parent, d)
    elif prompt_fp:
        d = d / f"p{prompt_fp}"
    d.mkdir(parents=True, exist_ok=True)
    return d
```

Layout:

| kind | path | versioned? |
|---|---|---|
| AST | `graphify-out/cache/ast/v{graphify version}/{sha256}.json` | **yes**, by package version |
| semantic | `graphify-out/cache/semantic/[p{prompt_fp}/]{sha256}.json` | **no** |
| semantic-deep | `graphify-out/cache/semantic-deep/[p{prompt_fp}/]{sha256}.json` | **no** |

`_GRAPHIFY_OUT` comes from `graphify.paths.GRAPHIFY_OUT`, overridable via the
`GRAPHIFY_OUT` env var (`cache.py:13-18`), relative or absolute.
`_EXTRACTOR_VERSION` is `importlib.metadata.version("graphifyy")` (`cache.py:28-33`).
`_PROMPT_FP_LEN = 12` (`cache.py:76`).

### 3b. What the key is derived from

`cache.py:256-257, 312-318` — `file_hash()`:

```python
def file_hash(path: Path, root: Path = Path("."), cache_root: "Path | None" = None) -> str:
    """SHA256 of file contents + path relative to root.
    ...
    raw = p.read_bytes()
    content = _body_content(raw) if p.suffix.lower() == ".md" else raw
    h = hashlib.sha256()
    h.update(content)
    h.update(b"\x00")
    h.update(salt.encode())
    digest = h.hexdigest()
```

So the key is `SHA256(file_bytes || b"\x00" || salt)` where `salt` is the
lowercased posix path **relative to root** (`cache.py:290-293`), falling back to
the absolute path when outside root. **Nothing about the graph, the edges, or
prior output enters the key.** For `.md` files only the body below YAML
frontmatter is hashed (`cache.py:166 _body_content`, `:313`), so frontmatter
edits do NOT invalidate.

There is also a stat fastpath: `(size, st_mtime_ns)` memo in
`graphify-out/cache/stat-index.json` (`cache.py:193-199, 295-334`) that skips the
re-read but produces the same digest.

For the semantic kinds the key is additionally namespaced by the **prompt
fingerprint** (`cache.py:89-109`):

```python
def prompt_fingerprint(prompt: "str | Path") -> str:
    ...
    return hashlib.sha256(normalized.encode()).hexdigest()[:_PROMPT_FP_LEN]
```

### 3c. What gets stored

**Parsed nodes/edges — NOT the raw LLM response.** `cache.py:560-566`:

```python
def save_cached(path: Path, result: dict, root: Path = Path("."), kind: str = "ast",
                cache_root: Path | None = None, prompt: "str | Path | None" = None,
                prompt_file: "str | Path | None" = None) -> None:
    """Save extraction result for this file.

    Stores as graphify-out/cache/{kind}/{hash}.json where hash = SHA256 of current file contents.
    result should be a dict with 'nodes' and 'edges' lists.
```

The buckets that are path-normalized on write confirm the shape
(`cache.py:407`): `("nodes", "edges", "hyperedges", "raw_calls")`.
`source_file` fields are relativized on write (`cache.py:586-600`) and
re-absolutized on read (`cache.py:554-555`) for portability.

### 3d. Invalidation rules

1. **Content change** — different bytes ⇒ different SHA256 ⇒ miss. This is the
   ONLY natural invalidation. **A hand-edited `graph.json` does not change any
   source file's bytes, so the cache still hits and re-serves the fragment
   containing the edge you deleted.**
2. **AST kind: graphify version bump** — `cache_dir` appends `v{version}` and
   `_cleanup_stale_ast_entries` (`cache.py:39`, called at `:478`) deletes other
   versions' entries. **Semantic entries are deliberately NOT version-namespaced**
   (`cache.py:463-466`) "re-extraction costs LLM calls, #1252".
3. **Semantic kind: prompt fingerprint change** — a different extraction prompt
   selects a different `p{fp}/` namespace (`cache.py:508-517`). With
   `allow_legacy=True` (default) a flat pre-fingerprint entry is still served.
4. **`partial` entries are treated as a MISS** on read unless `allow_partial`
   (`cache.py:547-548`):
   ```python
        if not allow_partial and isinstance(result, dict) and result.get("partial"):
            return None
   ```
5. **Manual**: `clear_cache(root)` (`cache.py:647`) deletes `ast/`, `semantic/`,
   `semantic-deep/` and legacy flat entries; `prune_semantic_cache(root, live_hashes)`
   (`cache.py:665`) garbage-collects entries whose files no longer exist.

---

## 4. Ollama backend transport

### 4a. Client library and endpoint

**The `openai` Python SDK against Ollama's OpenAI-compatibility layer.** There is
no `ollama` python package dependency. `llm.py:1135-1139`:

```python
    try:
        from openai import OpenAI
    except ImportError as exc:
        extra = backend if backend in ("kimi", "gemini", "openai", "ollama") else "openai"
        raise ImportError(_backend_pkg_hint("openai", extra)) from exc
```

`llm.py:1156-1157, 1230` — client construction and the single call site:

```python
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=_resolve_api_timeout(),
    max_retries=_retries,
)
...
resp = client.chat.completions.create(**kwargs)
```

Endpoint path: **`{base_url}/chat/completions`** where `base_url` ends in `/v1`
(i.e. `http://localhost:11434/v1/chat/completions`). Ollama's native
`/api/generate` and `/api/chat` are NOT used. Other `chat.completions.create`
sites: `llm.py:1513`, `llm.py:2560`, `llm.py:2523` (Azure), `prs.py:643`.

### 4b. Backend config block — `llm.py:126-133`

```python
    "ollama": {
        "base_url": _resolve_ollama_base_url("http://localhost:11434/v1"),
        "default_model": os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        "env_key": "OLLAMA_API_KEY",
        "pricing": {"input": 0.0, "output": 0.0},
        "temperature": 0,
        "max_tokens": 16384,
    },
```

### 4c. Base-URL resolution — `llm.py:60-97`

```python
def _resolve_ollama_base_url(default: str) -> str:
    """Resolve the Ollama base URL. Honors an explicit OLLAMA_BASE_URL first
    (verbatim), else falls back to Ollama's own OLLAMA_HOST (#1940), else the
    default. OLLAMA_HOST may be a bare host, host:port, ``:port`` or bare port —
    normalized the way the ollama client does: add ``http://`` when the scheme is
    missing, default the port to 11434 when absent, and append the OpenAI-compat
    ``/v1`` suffix."""
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL")
    if ollama_base_url is not None:
        return ollama_base_url
    ollama_host = os.environ.get("OLLAMA_HOST")
```

Precedence: `OLLAMA_BASE_URL` (verbatim) → `OLLAMA_HOST` (normalized, `/v1`
appended, port defaulted to 11434) → `http://localhost:11434/v1`.

Note: `BACKENDS` is a **module-level dict evaluated at import time**, so these
env vars must be set before `graphify.llm` is imported.

### 4d. Ollama-specific env vars

| Env var | Where | Effect |
|---|---|---|
| `OLLAMA_BASE_URL` | `llm.py:67` | base URL, verbatim (highest precedence) |
| `OLLAMA_HOST` | `llm.py:70` | fallback, normalized to `…:11434/v1` |
| `OLLAMA_MODEL` | `llm.py:128` | default model (ships `qwen2.5-coder:7b`) |
| `OLLAMA_API_KEY` | `llm.py:129` | auth; ignored by Ollama but the SDK needs non-empty — defaults to literal `"ollama"` with a warning (`llm.py:1612-1624`, `:2416-2419`) |
| `GRAPHIFY_OLLAMA_NUM_CTX` | `llm.py:1195` | pins `options.num_ctx`; else auto-derived |
| `GRAPHIFY_OLLAMA_KEEP_ALIVE` | `llm.py:1228` | `keep_alive`, default `"30m"` |
| `GRAPHIFY_OLLAMA_PARALLEL` | `llm.py:2172` | `=1` allows concurrency; else serialized (one request at a time per loaded model) |
| `GRAPHIFY_OLLAMA_VISION` | `llm.py:851` | `=1` opts into vision |
| `GRAPHIFY_API_TIMEOUT` | `llm.py:1143`, `_resolve_api_timeout()` | seconds; **default 600** |
| `GRAPHIFY_MAX_RETRIES` | `llm.py:1153-1155` | SDK retries; **forced to 0 for ollama** unless set explicitly (#1686) |

`llm.py:1194-1229` — the num_ctx auto-derive (the thing to be careful of if a
new embedding path reuses this code):

```python
    if backend == "ollama" and extra_body is None:
        num_ctx_raw = os.environ.get("GRAPHIFY_OLLAMA_NUM_CTX", "").strip()
        estimated_input = len(user_message) // _CHARS_PER_TOKEN + 400
        auto_num_ctx = min(estimated_input + max_completion_tokens + 2000, 131072)
        auto_num_ctx = max(auto_num_ctx, 8192)
        ...
        keep_alive = os.environ.get("GRAPHIFY_OLLAMA_KEEP_ALIVE", "30m")
        kwargs["extra_body"] = {"options": {"num_ctx": num_ctx}, "keep_alive": keep_alive}
```

There is also SSRF hardening on the base URL: `_validate_ollama_base_url`
(`llm.py:2604`) hard-blocks link-local/metadata hosts, warns on others
(`_ollama_host_is_link_local_or_metadata`, `llm.py:2577`).

### 4e. Embeddings: **NONE. Confirmed with a control arm.**

Target grep (ran from the package root):

```
$ grep -rni 'embedding|embeddings|embed\(' . --include='*.py'
ingest.py:14:    """Escape a string for embedding in a YAML double-quoted scalar.
security.py:397:    Safe for embedding in JSON data (inside <script> tags) and plain text.
export.py:117:    """Escape a value for safe embedding in a YAML double-quoted scalar (F-009).
export.py:340:    """Escape a string for safe embedding in a Cypher single-quoted literal.
extractors/go.py:239:                # Type body: struct fields (with embeds) or interface embedding.
```

All five are the **English word** in docstrings about string escaping and Go
struct embeds. Zero API usage.

```
$ grep -rn 'embeddings' . --include='*.py'
(no output)
```

**Control arm** — a term I know is present, proving the grep discriminates:

```
$ grep -rn 'chat.completions|chat/completions' . --include='*.py'
llm.py:1230:    resp = client.chat.completions.create(**kwargs)
llm.py:1513:    resp = client.chat.completions.create(**kwargs)
llm.py:2523:        resp = azure_client.chat.completions.create(**azure_kwargs)
llm.py:2560:    resp = client.chat.completions.create(**kwargs)
prs.py:643:            with client.chat.completions.create(
```

Second control arm — `cosine|faiss|sentence_transformers|vector` returned only
`std::vector` C++ parsing, "exfiltration vector" prose, and `_minhash.py`'s
numpy import. **There is no `/v1/embeddings` call, no vector store, no cosine
similarity, and no embedding model config anywhere in the package.**
`numpy>=1.21` IS a hard dependency but is used by `_minhash.py` (MinHash/LSH
lexical dedup), not by any semantic-vector path.

---

## 5. `semantically_similar_to`

**Confirmed: three sites total, none of them a validator.** Full grep output
(the same command that found `conceptually_related_to` as a control arm):

```
$ grep -rn 'semantically_similar_to' . --include='*.py'
llm.py:478           # the LLM prompt's emittable relation list
analyze.py:221       # comment
analyze.py:253       # scoring: 1.5x bonus
report.py:179        # report tag
```

**Site 1 — LLM-emittable label** (`llm.py:478`, inside the extraction prompt's
JSON schema line):

```
"relation":"calls|implements|references|cites|conceptually_related_to|shares_data_with|semantically_similar_to"
```

**Site 2 — report tag** (`report.py:179`):

```python
            sem_tag = " [semantically similar]" if relation == "semantically_similar_to" else ""
```

**Site 3 — scoring bonus** (`analyze.py:251-254`) — a bonus, effectively a
first-class citizen in surprise-ranking:

```python
    # 4b. Semantic similarity bonus - non-obvious conceptual links score higher
    if data.get("relation") == "semantically_similar_to":
        score = int(score * 1.5)
        reasons.append("semantically similar concepts with no structural link")
```

And `analyze.py:221-222` explicitly **exempts** it from the resolver-pollution
suppression:

```python
    # Excludes `semantically_similar_to` (genuine cross-boundary insight) and all
    # AMBIGUOUS/EXTRACTED edges (not from the resolver path).
```

### Is the relation-label set closed?

**No.** `validate.py` requires the `relation` KEY (`REQUIRED_EDGE_FIELDS`,
`validate.py:7`) but never checks its VALUE — there is no `VALID_RELATIONS`
constant, and the only value-level checks are `VALID_FILE_TYPES` (nodes) and
`VALID_CONFIDENCES` (edges). **An injected edge with
`relation: "semantically_similar_to"` would survive validation**, would be
tagged in reports, and would get the 1.5× surprise bonus. The prompt's
pipe-separated list at `llm.py:478` is prose to the model, not an enforced enum.

---

## 5b. ⚠️ CORRECTION/ADDITION to §1c — there IS a second provenance field: `_origin`

Found empirically by dumping the real `graph.json` in this repo (3157 nodes /
4642 edges), which showed a key the source-only sweep had not surfaced.

`extract.py:5153-5162` — the AST pass stamps **every** node and edge:

```python
    # Tag AST provenance so the incremental watch rebuild can distinguish
    # AST-extracted nodes from semantic/LLM nodes. On a full re-extraction
    # the watcher drops any AST-marked node missing from the fresh output
    # even when its source file still exists (#1116). Edges carry the same
    # marker so edge eviction can be tier-scoped: re-extracting a source
    # replaces its AST edges without evicting the semantic edges the AST
    # pass cannot regenerate (#1865).
    for n in all_nodes:
        n["_origin"] = "ast"
    for e in all_edges:
        e["_origin"] = "ast"
```

So `_origin == "ast"` ⇔ deterministic tree-sitter extractor;
**absence of `_origin`** ⇔ semantic/LLM (or anything else). Leading-underscore
keys are treated as internal markers and are stripped from GraphML export
(`export.py:977-982`) but **are persisted in `graph.json`** (confirmed
empirically — every node and edge in the live graph carries `"_origin": "ast"`).

### The load-bearing asymmetry for the design spec

**`watch.py` is provenance-AWARE. `build.py:build_merge` is provenance-BLIND.**

`watch.py:588-604`:

```python
        # Edges are owned by source_file, but ownership is tier-scoped: the AST
        # pass replaces a re-extracted source's AST edges, while that source's
        # semantic/LLM edges — which the AST pass cannot regenerate — survive
        # until a semantic re-extraction supersedes them. Same provenance rule
        # the node reconciliation above applies via _origin (#1865). Deletion
        # eviction stays provenance-blind.
        preserved_edges = [
            edge
            for edge in existing.get("links", existing.get("edges", []))
            if edge.get("source") in all_ids
            and edge.get("target") in all_ids
            and not source_paths.is_evicted(edge, edge_evicted_source_identities)
            and not (
                edge.get("_origin") == "ast"
                and source_paths.is_evicted(edge, rebuilt_source_identities)
            )
        ]
```

Read the last clause: an edge is evicted **only if** `_origin == "ast"` AND its
source was rebuilt. An edge **without** `_origin: "ast"` — exactly what an
externally injected semantic edge would be — **survives an AST re-extraction of
its source file** on the watch path. It is additionally protected by an
endpoint-existence check (`source in all_ids and target in all_ids`).

Contrast `build.py:1125-1129` (§2a), whose `_kept()` looks at `source_file`
**only** and drops the edge regardless of `_origin`.

**Implication:** the durability of an injected edge depends on *which code path*
rebuilds the graph. `watch`/`update` via `watch.py` would preserve a
non-`_origin` edge; `build_merge` would not. Any design that injects edges must
either (a) route through the watch-style reconciliation, (b) patch
`build_merge`'s `_kept()` to be `_origin`-aware, or (c) re-inject after every
build (idempotent post-pass). This asymmetry looks like a latent bug in
graphify, not a designed contract.

### Empirical edge/node key census (this repo's `graphify-out/graph.json`)

```
top-level keys: ['directed', 'multigraph', 'graph', 'nodes', 'links', 'hyperedges', 'built_at_commit']

NODE keys (n=3157): label 3157, file_type 3157, source_file 3157,
  source_location 3157, _origin 3157, id 3157, community 3157,
  community_name 3157, norm_label 3157, metadata 40, type 1, ecosystem 1, version 1

EDGE keys (n=4642): relation 4642, confidence 4642, source_file 4642,
  source_location 4642, weight 4642, _origin 4642, source 4642, target 4642,
  confidence_score 4642, context 1744

relation counts: contains 1949, calls 1083, rationale_for 785, references 570,
  method 103, imports_from 60, uses 41, indirect_call 25, extends 13,
  inherits 7, defines 5, requires_env 1
confidence counts: EXTRACTED 4219, INFERRED 423

sample node: {"label": "@modelcontextprotocol/server-memory", "file_type": "code",
  "source_file": ".mcp.json", "source_location": "L1",
  "metadata": {"mcp_kind": "mcp_package"}, "_origin": "ast",
  "id": "mcp_package_modelcontextprotocol_server_memory", "community": 104,
  "community_name": ".mcp.json", "norm_label": "@modelcontextprotocol/server-memory"}

sample edge: {"relation": "references", "confidence": "EXTRACTED",
  "confidence_score": 1.0, "source_file": ".mcp.json", "source_location": "L1",
  "weight": 1.0, "context": "command", "_origin": "ast",
  "source": "mcp_mcp_server_memory", "target": "mcp_command_npx"}
```

Note: **zero `semantically_similar_to` edges exist in the live graph** — the
relation is emittable in principle but this corpus (AST-only, `--code-only`-ish)
has none. It also confirms `relation` is an open vocabulary in practice:
`contains`, `rationale_for`, `method`, `imports_from`, `indirect_call`,
`extends`, `inherits`, `defines`, `requires_env` all appear and **none of them
are in the `llm.py:478` prompt list**.

---

## 6. Node schema

### 6a. Declared required fields — `validate.py:6`

```python
REQUIRED_NODE_FIELDS = {"id", "label", "file_type", "source_file"}
```

`file_type` is the one node field with a closed value set (`validate.py:4`):
`{"code", "document", "paper", "image", "rationale", "concept"}`, coerced rather
than rejected at build (`build.py:526-529`):

```python
        ft = node.get("file_type", "")
        if ft and ft not in {"code", "document", "paper", "image", "rationale", "concept"}:
            node["file_type"] = _FILE_TYPE_SYNONYMS.get(ft, "concept")
```

### 6b. Full field list (prompt schema, `llm.py:478`)

`id`, `label`, `file_type`, `source_file`, `source_location`, `source_url`,
`captured_at`, `author`, `contributor`.

Plus, added downstream:
- `_origin` — `"ast"` or absent (§5b)
- `metadata` — a free-form dict (seen on 40/3157 nodes, e.g. `{"mcp_kind": ...}`)
- `community`, `community_name`, `norm_label` — stamped by
  `export.py:295-300` at write time:
  ```python
      for node in data["nodes"]:
          cid = node_community.get(node["id"])
          node["community"] = cid
          if cid is not None and _labels:
              node["community_name"] = _labels.get(cid, f"Community {cid}")
          node["norm_label"] = _strip_diacritics(node.get("label", "")).lower()
  ```

### 6c. The schema is OPEN at build time

`build.py:618` — every non-`id` key is passed straight through to NetworkX:

```python
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
```

and `build.py:893` for edges (minus `source`/`target`/`target_file`):

```python
        G.add_edge(src, tgt, **attrs)
```

`json_graph.node_link_data` then serializes whatever attributes are present
(`export.py:292`). **So a new field — e.g. `embedding`, `summary`, or
`_origin: "embed"` — round-trips through build → graph.json with no schema
change required.** (Caveat: GraphML export coerces non-scalars to JSON strings,
`export.py:986-990`, and strips `_`-prefixed keys.)

### 6d. ⚠️ What is available to embed: **NOT MUCH.**

**There is NO docstring, summary, description, signature, body, snippet, or
source-text field on a node.** Grep:

```
$ grep -rnE '"(docstring|summary|description|signature|snippet|body|text|content|code)"' --include='*.py' . | grep -v extractors/
build.py:62:    "text": "document",            # a _FILE_TYPE_SYNONYMS key, not a node field
build.py:63:    "tool": "code",
build.py:64:    "library": "code",
diagnostics.py:333:    "summary": {                 # a diagnostics report key
manifest_ingest.py:74:    "file_type": "code",
serve.py:*                                   # MCP tool JSON-Schema "description" keys
```

None is a node field. Confirmed by the empirical census in §5b: the only
text-bearing node fields are **`label`** (a human-readable name, e.g.
`"parse_config()"` / `"README.md"`) and **`norm_label`** (its lowercased,
diacritic-stripped form), plus `source_file` (a path) and `source_location`
(e.g. `"L1"`).

**Embeddable today, without re-reading source: `label` + `source_file`
(+ `community_name`, `file_type`, `metadata`).** That is a very thin signal — a
symbol name and a path. Any embedding design that wants real semantics must
either re-read the source slice (`file_slice.py` exists and takes a
`source_location`) or add a new node field at extraction time.

---

## 7. Extension seams — is the write path closed?

### 7a. The function that writes `graph.json`

**`graphify.export.to_json`** — `export.py:232`:

```python
def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str, *, force: bool = False, built_at_commit: str | None = None, community_labels: dict[int, str] | None = None) -> bool:
```

Actual disk write at `export.py:318-320`:

```python
from graphify.paths import write_json_atomic

# Atomic write: a crash/ENOSPC mid-write must not truncate a good graph.json.
write_json_atomic(output_path, data, indent=2)
return True
```

Only three call sites:

```
cli.py:1672:    to_json(G, communities, str(out / "graph.json"), community_labels=labels)
cli.py:3343:    _wrote = _to_json(G, communities, str(graph_json_path), force=_force_write)
watch.py:1263:  json_written = to_json(G, communities, str(graph_tmp), force=True, built_at_commit=commit, community_labels=labels)
```

### 7b. Is there a plugin / hook / post-processing seam? **No.**

Grep for the usual seam shapes:

```
$ grep -rniE 'entry_points|plugin|register_|post_process|importlib.import_module|__subclasses__' . --include='*.py'
```

Every hit is one of:
- **IDE integrations**, not graph passes — `install.py:1058-1178` writes a
  `.kilo/plugins/graphify.js` / OpenCode `tool.execute.before` plugin; these are
  *editor* plugins that shell out to graphify.
- **git hooks** — `hooks.py` installs post-commit/post-checkout hooks and a git
  **merge driver** (`_register_merge_driver`, `hooks.py:525`) for union-merging
  two `graph.json` files. Not a graph-mutation seam.
- `__init__.py:28` — a lazy `importlib.import_module` for graphify's own
  submodules.

**There are no `entry_points`, no exporter registry, no post-build callback, no
`GRAPHIFY_PLUGINS` env var.** `exporters/__init__.py` is a one-line docstring;
`exporters/base.py` is a color palette. `resolver_registry.py` is an *internal*
per-language symbol-resolver table, not an external plugin API.

### 7c. So what ARE the seams?

The write path is closed to in-process extension, but three practical seams exist:

1. **Post-write file mutation.** `graph.json` is plain JSON on disk; nothing
   checksums or signs it. An external pass can read it, add edges, and rewrite
   it. This is the *only* real injection point — and it is exactly what §2/§3
   show gets clobbered on the next `build_merge`. Idempotent re-injection after
   every build is the workable pattern.
2. **`graphify merge-graphs <g1> <g2>`** (CLI, §8) and the **git merge driver**
   (`graphify merge-driver <base> <current> <other>`, `hooks.py`) — both
   union-merge whole `graph.json` files. A synthetic graph file containing only
   the inferred edges could be union-merged in. This is the closest thing to a
   sanctioned injection API.
3. **Seed the semantic cache.** Since the cache stores parsed `{"nodes","edges"}`
   fragments keyed by `SHA256(content||\0||relpath)` (§3), a pass could write
   cache entries directly. Fragile (key derivation + prompt fingerprint) and
   definitely off-contract, but it is the only route that survives `build_merge`,
   because `build_merge` rebuilds *from* the cache.

**Dead code worth noting:** `validate.assert_valid` (`validate.py:90`) has
**zero callers** — `grep -rn 'assert_valid'` returns only its definition.
`build_from_json` calls `validate_extraction` and merely **prints a warning**
(`build.py:540-543`):

```python
real_errors = [e for e in errors if "does not match any node id" not in e]
if real_errors:
    print(
        f"[graphify] Extraction warning ({len(real_errors)} issues): {real_errors[0]}",
        file=sys.stderr,
    )
```

So validation is **non-fatal on the build path**. An injected edge with an
unknown `relation`, or even an invalid `confidence`, would produce a stderr line
and still land in the graph. Likewise `cache.clear_cache` (`cache.py:647`) has
**zero callers** — there is no `--clear-cache` flag; you must `rm -rf
graphify-out/cache/`.

### 7d. ⭐ The best seam found: `graphify merge-chunks` (undocumented in `--help`)

`cli.py:3497-3501`:

```python
    elif cmd == "merge-chunks":
        # graphify merge-chunks <chunk_glob_or_files...> --out <path>
        # Concatenates .graphify_chunk_*.json files written by semantic subagents.
        # Deduplicates nodes by id (first writer wins). Sums token counts.
```

`cli.py:3527-3533` — it explicitly treats these files as **untrusted external
input** and validates them:

```python
        # These chunk files are untrusted subagent output. load_validated_...
        # stats the file size BEFORE reading it (so a multi-GB chunk can't blow up
        # memory), parses the JSON, and validates the security caps + the node/
        # edge id charset that blocks path traversal (#825) — the same enforcement
        # the skill merge path applies. A bad chunk is skipped with a warning
        # while valid siblings still merge; if every chunk is invalid, fail
```

**This is the designed injection API.** graphify already expects an *external
process* ("semantic subagents") to write `{"nodes":[...],"edges":[...]}` chunk
files that are then folded into the graph. An embedding pass that emits
`semantically_similar_to` edges as a chunk file is using the mechanism as
intended. Sibling: `merge-semantic --cached <p> --new <p> --out <p>`
(`cli.py:3578`), which concatenates two such fragments (cached wins on node id).

---

## 8. CLI surface

Taken from `graphify --help` (v0.9.22) **and** the dispatch table in
`cli.py` / `__main__.py`.

### 8a. Top-level subcommands

**Documented in `--help`:** `install`, `uninstall`, `path`, `explain`,
`diagnose multigraph`, `clone`, `merge-driver`, `merge-graphs`, `add`, `watch`,
`update`, `cluster-only`, `label`, `query`, `affected`, `god-nodes`,
`save-result`, `reflect`, `check-update`, `tree`, `extract`,
`global {add,remove,list,path}`, `benchmark`, `export callflow-html`,
`hook {install,uninstall,status}`, plus ~20 per-IDE
`<platform> {install,uninstall}` pairs (claude, gemini, cursor, codex, opencode,
kilo, aider, copilot, vscode, claw, droid, trae, trae-cn, antigravity, hermes,
kiro, pi, devin, codebuddy).

**Present in the dispatch table but NOT in `--help`** (`cli.py:627, 1763, 1768,
3437, 3497, 3578`):

| cmd | line | what |
|---|---|---|
| `provider` | `cli.py:627` | provider/backend config |
| `hook-check` | `cli.py:1763` | hook self-check |
| `hook-guard` | `cli.py:1768` | the PreToolUse guard body |
| `cache-check` | `cli.py:3437` | semantic-cache hit/miss probe; writes `.graphify_cached.json` + `.graphify_uncached.txt` |
| `merge-chunks` | `cli.py:3497` | **fold external chunk files into a graph** (§7d) |
| `merge-semantic` | `cli.py:3578` | merge cached + new semantic fragments |

A bare path (`graphify .`) falls through to the full-extraction default
(`cli.py:3620`: `elif Path(cmd).exists() or cmd in (".", "..") or cmd.startswith(...)`).

### 8b. Output / merge / cache flags

**`extract <path>`** — the main build command:

| flag | meaning |
|---|---|
| `--out DIR`, `--output DIR` | output dir (default `<path>`); writes `<DIR>/graphify-out/` |
| `--force` | **full re-scan and re-dispatch: skips the incremental manifest gate AND the semantic cache READS** (env `GRAPHIFY_FORCE=1`) |
| `--backend B` | `gemini\|kimi\|claude\|openai\|deepseek\|ollama` (default: whichever API key is set) |
| `--model M` | override backend default model |
| `--mode deep` | aggressive INFERRED-edge semantic extraction (uses the `semantic-deep/` cache namespace) |
| `--api-timeout S` | per-request LLM timeout, **default 600** |
| `--max-concurrency N` | parallel semantic chunks (default 4; **set 1 for local LLMs**) |
| `--token-budget N` | per-chunk token cap (default 60000) |
| `--max-workers N` | AST subprocess count |
| `--no-cluster` | skip clustering, write raw extraction only |
| `--code-only` | AST only, no API key, skip doc/paper/image |
| `--no-gitignore` | ignore `.gitignore` / `.git/info/exclude` |
| `--global`, `--as <tag>` | also merge into `~/.graphify/global-graph.json` |
| `--postgres DSN`, `--cargo`, `--google-workspace` | alternate ingest sources |

**`update <path>`** (AST-only re-extract, no LLM):
- `--force` — overwrite `graph.json` even if the rebuild has **fewer nodes**
  (env `GRAPHIFY_FORCE=1`). This is the override for the `to_json` shrink guard
  (`export.py:235`) — see `cli.py:1708-1713`.
- `--no-cluster`

**`merge-graphs <g1> <g2> …`** — `--out <path>` (default
`graphify-out/merged-graph.json`).
**`merge-chunks <files…>`** — `--out <path>` (required).
**`merge-semantic`** — `--cached <p> --new <p> --out <p>`.
**`cache-check <files_from>`** — `--root <dir>`, `--mode <m>` / `--deep`,
`--prompt-file <path>`.

Query-side commands (`path`, `explain`, `query`, `affected`, `god-nodes`,
`tree`, `diagnose`) all take `--graph <path>` (default
`graphify-out/graph.json`).

### 8c. ⚠️ There is NO `--no-cache` and NO `--clear-cache`

```
$ grep -rn '\-\-no-cache\|no_cache\|--clear-cache' cli.py __main__.py
(no output)
```

`--force` is the only cache-bypass, and it bypasses the **read** only — the
**write** still happens (`cli.py:2901-2910`):

```python
            if force:
                # --force: skip the cache READ so every semantic file is
                # re-dispatched; the save below still runs so the fresh
                # results replace the stale entries.
                cached_nodes, cached_edges, cached_hyperedges = [], [], []
                uncached_paths = list(sem_paths_str)
```

`cache.clear_cache` (`cache.py:647`) has **zero callers** — no CLI wiring. The
only way to fully invalidate is `rm -rf graphify-out/cache/`.

---

## Design-spec implications (summary of the load-bearing findings)

1. **No embedding infrastructure exists at all** — no `/v1/embeddings` call, no
   vector store, no cosine similarity, no embedding model config. Confirmed with
   a control arm (§4e). This is greenfield.
2. **The Ollama transport is the OpenAI SDK against `/v1/chat/completions`.** An
   embeddings pass would need a *new* code path; `client.embeddings.create` is
   available on the same `OpenAI` client and Ollama serves `/v1/embeddings`, so
   the transport plumbing (`_resolve_ollama_base_url`, timeout, keep_alive,
   serialization guard) is reusable but not the call itself.
3. **`semantically_similar_to` is a first-class label with NO validation gate**
   (§5) — inferred edges bearing it survive validation, get a report tag, and
   earn a 1.5× surprise-score bonus.
4. **Node text available to embed is thin**: `label` + `source_file` only. No
   docstring/summary field exists (§6d). A useful embedding pass probably has to
   re-read source slices or add a node field.
5. **Hand-edited `graph.json` is not durable** (§2, §3): `build_merge` replaces
   per-`source_file` and is `_origin`-blind, and the content-keyed cache
   re-injects the same fragments because source bytes never changed.
6. **BUT `watch.py` IS `_origin`-aware** (§5b) — a non-AST edge survives an AST
   rebuild there. This asymmetry between `watch.py` and `build_merge` looks like
   an upstream bug and is the single most useful lever: making `build_merge`'s
   `_kept()` `_origin`-aware would make injected edges durable with a ~3-line
   change.
7. **`merge-chunks` is the sanctioned injection API** (§7d) — graphify already
   expects untrusted external processes to hand it `{"nodes","edges"}` files.
8. **Validation is advisory, not enforcing** — `assert_valid` is dead code and
   `build_from_json` only prints a warning (§7c).

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the subject of this archaeology; read the installed 0.9.22 `site-packages/graphify` source (`llm.py`, `build.py`, `cache.py`, `export.py`, `validate.py`, `analyze.py`, `report.py`, `watch.py`, `extract.py`, `cli.py`, `__main__.py`, `extractors/models.py`, `exporters/*`). Issue numbers cited inline (#479, #563, #582, #760, #777, #798, #825, #932, #1007, #1116, #1252, #1504, #1571, #1574, #1686, #1774, #1796, #1865, #1894, #1939, #1960, #1989, #2012) come from that repo's tracker as referenced in the source comments — **not independently verified against the live tracker.**
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the local repo whose `graphify-out/graph.json` provided the empirical node/edge key census in §5b.
- [openai/openai-python](https://github.com/openai/openai-python) — the client library graphify uses for every backend including Ollama (`from openai import OpenAI`, `client.chat.completions.create`); named only, source not read.
- [ollama/ollama](https://github.com/ollama/ollama) — the local inference server graphify targets via its OpenAI-compat `/v1` layer; referenced via graphify's own comments (`num_ctx` defaults, `keep_alive`, `OLLAMA_HOST` normalization), **its docs/source were not read in this pass.**
- [networkx/networkx](https://github.com/networkx/networkx) — the graph library backing `build`/`to_json` (`json_graph.node_link_data`, the `edges="links"` compat shim); named only.

## Explicit non-findings (things looked for and NOT found)

| Looked for | Result | Probe (with control arm) |
|---|---|---|
| any embeddings API call | **absent** | `grep -rn 'embeddings'` → empty; control `grep -rn 'chat.completions'` → 5 hits |
| vector store / cosine similarity | **absent** | `grep -rniE 'cosine\|faiss\|sentence_transformers'` → 0 relevant; `numpy` present but only in `_minhash.py` |
| a closed `VALID_RELATIONS` set | **absent** | `validate.py` has `VALID_FILE_TYPES` + `VALID_CONFIDENCES` only; live graph contains 12 relation values, 9 of them absent from the `llm.py:478` prompt list |
| node docstring/summary/description field | **absent** | source grep + empirical key census of 3157 real nodes |
| plugin/entry_points seam for graph passes | **absent** | `grep -rniE 'entry_points\|plugin\|register_'` → only IDE integrations + git hooks |
| `--no-cache` / `--clear-cache` CLI flag | **absent** | `grep -rn '\-\-no-cache\|--clear-cache' cli.py __main__.py` → empty; `clear_cache()` has 0 callers |
| `assert_valid` enforcement | **dead code** | `grep -rn 'assert_valid'` → definition only |
