# graphify "gemma" issue/PR sweep — assessment of our setup

Date: 2026-07-20 · Agent: graphify-gemma-issues
Query: <https://github.com/search?q=repo%3AGraphify-Labs%2Fgraphify+gemma&type=issues>

## Probe methodology (and its control arms)

`gh search issues --state all` is **invalid** — `gh` accepts only `open|closed`, so the
command in the brief errors out. The authoritative probe was the plain REST search, which
returns issues **and** PRs in one result set:

```
gh api -X GET search/issues -f q="repo:Graphify-Labs/graphify gemma" -f per_page=100
→ total_count = 7
```
Split: **3 ISSUE + 4 PR**. `gh search issues` / `gh search prs` divide the same 7 across two
commands (issues-only excludes PRs unless `--include-prs`) — that is the `gh`-vs-web-UI
disagreement the brief warned about. The REST call is the union and is what this report uses.

Source-verification target (all `file:line` below are from this tree, referred to as `$G`):
`/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.22/graphifyy/lib/python3.14/site-packages/graphify`

**Control arms used throughout** (a probe that can only say "not found" is not evidence):

| negative claim | probe | control arm (same command shape) |
|---|---|---|
| no `embed.py` | `ls $G/embed.py` → absent | `ls $G/file_slice.py` → **present, 6318 bytes** |
| no gemma code | `grep -rni gemma $G --include='*.py'` → **0** | `grep -rn 'qwen2.5-coder'` → **2** (`llm.py:128`, `llm.py:1264`) |
| no `--embeddings` flag | `grep -c -- '--embeddings' cli.py` → **0** | `grep -c -- '--token-budget' cli.py` → **5** |
| no `stitch.py` | `grep -rn stitch $G --include='*.py'` → **0** | `grep -rn hollow` → **12** |
| graphify never sets `OLLAMA_NUM_PARALLEL` | `grep -rn NUM_PARALLEL` → **0** | `grep -rn NUM_CTX` → **5** |
| no user-settable sampling knobs | `grep -rn top_p` → **0** | `grep -rn temperature` → many |

---

## 1. Every gemma-matching issue/PR

| # | type | state | last activity | title | one-line verdict |
|---|---|---|---|---|---|
| [#7](https://github.com/Graphify-Labs/graphify/issues/7) | ISSUE | **OPEN** | 2026-06-02 | v0.4.0: local embeddings via quantized Gemma 4 (no API cost) | **Confirmed unimplemented in 0.9.22** by source, not by ticket state. Our fact holds. |
| [#798](https://github.com/Graphify-Labs/graphify/issues/798) | ISSUE | closed | 2026-05-09 | [Critical] Context Window Saturation / Missing Session Reset between Chunks (Ollama Backend) | **Most relevant to us.** Fixed 0.7.13; fix live in 0.9.22 at `llm.py:1193-1233`. Our unset-`NUM_CTX` choice is exactly right. Its *headline diagnosis is wrong* — see §4. |
| [#792](https://github.com/Graphify-Labs/graphify/issues/792) | ISSUE | closed | 2026-05-09 | [Feature Request] Enhancing Local LLM Performance (Ollama) & High-Core CPU Scaling via graphify.yaml | Origin of `--max-workers` / `--token-budget` / `--max-concurrency` / `--api-timeout` — i.e. **three of the four flags we pass**. `graphify.yaml` + temperature/top_p/top_k/seed knobs were **declined**. |
| [#1126](https://github.com/Graphify-Labs/graphify/pull/1126) | PR | closed, **NOT merged** | 2026-06-05 | feat: local embedding pass for exhaustive `semantically_similar_to` edges (#7) | The one serious attempt at #7. Rejected → embeddings still absent. Used **ONNX `embeddinggemma-300m`**, *not* Ollama. |
| [#1326](https://github.com/Graphify-Labs/graphify/pull/1326) | PR | closed, **NOT merged** | 2026-06-17 | feat: intra-file slicing, incremental safety, and cross-file stitch | Slicing half **shipped anyway** (`file_slice.py`, wired `llm.py:2139`); the `stitch.py` half did **not**. |
| [#1398](https://github.com/Graphify-Labs/graphify/pull/1398) | PR | closed, **NOT merged** | 2026-06-22 | fix: Fix for the slicer (0.8.42 #1369), regression from 0.8.43 (#1386) | `Path(FileSlice)` crash under a **lowered `--token-budget`**. Matches "gemma" only via a passing mention that local Gemma env vars broke the author's backend-detection tests. |
| [#252](https://github.com/Graphify-Labs/graphify/pull/252) | PR | closed, **NOT merged** | 2026-04-15 | feat: Windows-native skill support and edge-model workflow optimizations for OpenClaw | Inert for us (PowerShell, Windows `python`, OpenClaw skill files). A `claw` platform does exist in 0.9.22 (`install.py:359`, `skill-claw.md`) but is unrelated to this PR's content. |

**All four PRs are closed with `mergedAt: null`.** Where a feature they describe nevertheless
exists in 0.9.22 (file slicing), the maintainer reimplemented it. So **PR merge status is not
a reliable proxy for "shipped" in this repo, in either direction** — every verdict below is
adjudicated against installed source.

---

## 2. Does this affect our setup?

Our setup under assessment:
`graphify extract <dir> --backend ollama --model <M> --max-concurrency 1 --token-budget 12000 --api-timeout 900`,
`OLLAMA_NUM_PARALLEL=1`, `GRAPHIFY_OLLAMA_NUM_CTX` **unset**, graphify `0.9.22` pinned
host-only at `mise.toml:53` as `"pipx:graphifyy" = { version = "0.9.22", extras = ["all"] }`.

### #7 — local embeddings via Gemma 4 → **INERT, and our reading of it is correct**
Verified unimplemented in 0.9.22:
- `$G/embed.py` **does not exist** (control-armed against `file_slice.py`, which does).
- `grep -c -- "--embeddings" $G/cli.py` → **0** (control arm `--token-budget` → 5).
- `grep -rn "embed_threshold\|embeddings" $G --include='*.py'` → **0 hits**.
- The shipped package METADATA markets the opposite:
  `graphifyy-0.9.22.dist-info/METADATA:169` — *"**Not a vector index.** No embeddings, no
  vector store: a real graph you traverse."*

**Consequence:** `embeddinggemma` is currently **dead weight for graphify** — nothing in
0.9.22 can call it. No flag, env var, model, or version change follows from #7. Note further
that #1126 chose **ONNX Runtime + `onnx-community/embeddinggemma-300m-ONNX`**, i.e. *not* the
Ollama `embeddinggemma` we pulled, and the #7 thread (2026-06-02, TPAteeq +
FolatheDuckofDuckingburg) explicitly settles on "pull Gemma 4 from Hugging Face". If #7 ever
lands it will most likely arrive as ONNX/HF, not as an Ollama pull.

### #798 — Ollama context saturation → **DIRECTLY RELEVANT; our config is on the correct side**
The fix is present in 0.9.22 at `llm.py:1193-1233`:
```python
if backend == "ollama" and extra_body is None:
    num_ctx_raw = os.environ.get("GRAPHIFY_OLLAMA_NUM_CTX", "").strip()      # llm.py:1195
    estimated_input = len(user_message) // _CHARS_PER_TOKEN + 400            # llm.py:1198
    auto_num_ctx = min(estimated_input + max_completion_tokens + 2000, 131072)
    auto_num_ctx = max(auto_num_ctx, 8192)                                   # llm.py:1199-1200
    ...
    kwargs["extra_body"] = {"options": {"num_ctx": num_ctx}, "keep_alive": keep_alive}  # llm.py:1229
```
With `_CHARS_PER_TOKEN = 4` (`llm.py:36`) and `max_completion_tokens = 8192` (`llm.py:1127`),
our `--token-budget 12000` derives **num_ctx ≈ 12000 + 400 + 8192 + 2000 ≈ 22.6k** —
comfortably inside the 131072 cap and above the 8192 floor. That is the intended regime.

**Leaving `GRAPHIFY_OLLAMA_NUM_CTX` unset is correct and load-bearing.** The env var
*overrides* the derivation entirely (`llm.py:1201-1203`); pinning it re-introduces #798's
failure from one side or the other — too big → KV-slot VRAM blowout; too small → silent prompt
truncation, which the code explicitly warns about at `llm.py:1216-1222`. **Do not set it.**

`OLLAMA_NUM_PARALLEL=1` is also correct and is *only* achievable from our side: the
maintainer's root-cause comment on #798 (2026-05-09 22:44) names Ollama's default
`OLLAMA_NUM_PARALLEL=4` as the multiplier that turned an over-large `num_ctx` into chunk-4
VRAM exhaustion, and **graphify never sets that variable itself** (`grep -rn NUM_PARALLEL` →
0 hits; control arm `NUM_CTX` → 5). Keep it.

`--max-concurrency 1` is the second half of the same protection: `llm.py:2223`
`workers = max(1, min(max_concurrency, total))` forces strictly sequential LLM calls.

### #792 — CLI flags for local LLMs → **ORIGIN OF OUR FLAGS; all present**
- `--api-timeout` → `cli.py:2507` / `cli.py:2557` (sets `GRAPHIFY_API_TIMEOUT`), consumed by
  `_resolve_api_timeout(default=600.0)` (`llm.py:403`), applied at `llm.py:1156`. Our `900`
  overrides the 600s default upward — appropriate for a 12–14B model on Apple silicon.
- `--max-concurrency` (`llm.py:2085`, `2173`), `--token-budget` (`cli.py`, ×5),
  `--max-workers` — all present.
- **Declined upstream, therefore unavailable to us:** `graphify.yaml`, and any
  `temperature` / `top_p` / `top_k` / `seed` knob. `grep -rn 'top_p'` → **0 hits**; the
  `temperature` hits are per-backend *defaults* in the `BACKENDS` table (e.g. `llm.py:131`
  `"temperature": 0` for ollama), not user-settable per run. Maintainer's stated position:
  *"set these server-side via Ollama Modelfile."*
  **Real gap for us**: if extraction quality wobbles on gemma4/qwen, our only lever for
  temperature/top_p/top_k is an Ollama `Modelfile` — there is no graphify flag.

### #1126 — the embeddings PR → **INERT** (not merged; see #7).
Useful intel if we ever revisit: at threshold 0.82 it added +169 similarity edges to a
177-node / 246-edge graph. Its own "Deferred" note records that on a **pure-code corpus, 87%
of edges at 0.82 were identical-label collisions** (different classes' `.__init__()` embedding
identically). A known trap for any embedding pass we build over code.

### #1326 / #1398 — the slicer → **RELEVANT; resolved in our favour**
`file_slice.py` exists and `expand_oversized_files(files, _FILE_CHAR_CAP)` is wired into the
real extraction path at `llm.py:2139` (imported `llm.py:22`). Oversized markdown docs *are*
split at heading/paragraph boundaries before packing in 0.9.22. **This matters to us
specifically**: #1398 notes its crash "only surfaces … with a **lowered `--token-budget`**",
and 12000 is a heavily lowered budget on a markdown corpus — but the crashing code was
reimplemented rather than merged, so the failure cannot be reproduced by construction.

`stitch.py` did **not** ship (0 hits; control arm `hollow` → 12). **Actionable — see §3(e).**

### #252 — OpenClaw / Windows → **INERT.** Not merged, and Windows/PowerShell-specific.

---

## 3. Known bugs / gotchas with gemma-under-Ollama we should guard against

**(a) There is NO gemma-specific code path in graphify 0.9.22.**
`grep -rni gemma $G --include='*.py'` → **0 hits**, control-armed by `grep -rn 'qwen2.5-coder'`
→ 2 hits in the identical sweep. Every gemma-related behaviour is generic-Ollama behaviour.
Corollary: graphify's own default Ollama model is **`qwen2.5-coder:7b`** (`llm.py:128`,
`OLLAMA_MODEL` fallback), and its low-token warning recommends `qwen2.5-coder:14b`
(`llm.py:1264`). The maintainer's implicit recommendation is the qwen-coder family, not gemma
— independently corroborating our bake-off result (qwen2.5-coder:14b winning).

**(b) Hollow-response handling — mitigated, but know the signature.**
`_response_is_hollow()` (`llm.py:1047-1071`) treats HTTP-200 with empty content **or** zero
nodes/edges as truncation and relabels `finish_reason = "length"` (`llm.py:1247-1256`) so
adaptive bisection fires. **Measurement gotcha:** a chunk that *legitimately* yields zero nodes
is indistinguishable from a choke and gets bisected and retried. If a gemma4:12b run looks
slow, this is a likely reason — and it inflates the output-token count we measure.

**(c) The "very few tokens" warning is now VRAM-first** (`llm.py:1258-1266`). If we see it on
gemma4:12b, the prescribed order is: reduce `--token-budget`, then switch model — **not** raise
`NUM_CTX`.

**(d) `GRAPHIFY_OLLAMA_KEEP_ALIVE` defaults to `"30m"` and we are not setting it — for a
bake-off we probably should.** `llm.py:1228`:
`keep_alive = os.environ.get("GRAPHIFY_OLLAMA_KEEP_ALIVE", "30m")`, passed to Ollama at
`llm.py:1229`. **After a gemma4:12b run finishes, that model stays resident for 30 minutes.**
Back-to-back arms (gemma4:12b → qwen2.5-coder:14b → qwen3:14b) therefore stack resident models
in unified memory and can make the *second* arm look slower than it is.
**Recommendation: `GRAPHIFY_OLLAMA_KEEP_ALIVE=0` (or `ollama stop <model>`) between bake-off
arms.** Measurement hygiene, not a correctness bug. (`RANGERVIII` in #798 reports this var was
"completely ineffective" — true for *saturation*, which is not what it controls; it is
effective for residency, which is our use.)

**(e) `stitch.py` never shipped → incremental extracts can produce isolated subgraphs.**
PR #1326's Problem 3 is unfixed in 0.9.22. If we run `graphify extract` **incrementally**
(adding docs one at a time) rather than over the whole corpus, new nodes may not connect to the
existing graph, and BFS/`query` will not reach them. **Guard: prefer full-corpus extracts, or
verify connectivity after an incremental run.** Our `mise run graphify-query` path is a
deterministic BFS over `graph.json` and inherits exactly this limitation.

**(f) Ollama gets `max_retries = 0` by default (#1686).** `llm.py:1152-1155` sets the OpenAI
SDK to zero transient retries for ollama specifically, so **`--api-timeout 900` is a hard
per-call wall-clock bound**, not a 7×900s one. Good, and worth knowing when budgeting a run.

---

## 4. Contradictions with our established facts

**No hard contradiction found.** Three near-misses, each adjudicated against source rather than
issue text:

1. **"#7 is open ⇒ embeddings unimplemented"** — the shape that most often lies (an open issue
   outliving its fix). Here it is **corroborated by source**: no `embed.py`, `--embeddings`
   count 0, and shipped METADATA advertising "No embeddings, no vector store". Our fact stands
   on evidence, not on the ticket.

2. **PRs #1326/#1398 closed-unmerged, yet `file_slice.py` exists** — the mirror-image trap:
   *unmerged does not mean unshipped here*. Adjudicated by reading `llm.py:22` and
   `llm.py:2139`. Anyone reasoning about this repo from PR status alone will be wrong in both
   directions.

3. **⚠️ #798's headline diagnosis is WRONG, and it is the more visible artifact.** The issue
   title and body assert "Missing Session Reset between Chunks" / KV-cache leakage. The
   maintainer refutes it in-thread and the source agrees: every call builds a fresh
   `messages=[system, user]` array (`llm.py:1160-1166`), there is no conversation history, and
   graphify uses `/v1/chat/completions` — not the native `/api/generate` endpoint where the
   `context` array exists at all. Real cause: `num_ctx` over-allocation × Ollama's default
   `OLLAMA_NUM_PARALLEL=4`. **Do not adopt the `ollama stop`-between-chunks workaround from
   that thread** — it targets a mechanism that does not exist, and it would serialise our runs
   for nothing. (Setting `KEEP_ALIVE=0` between *bake-off arms*, §3(d), is a different and
   legitimate use of a superficially similar idea.)

Nothing found contradicts: our 0.9.22 pin, the `--max-concurrency 1` / `--token-budget 12000` /
`--api-timeout 900` flag set, `OLLAMA_NUM_PARALLEL=1`, leaving `GRAPHIFY_OLLAMA_NUM_CTX` unset,
or the gemma4:12b-has-no-embedding-capability finding (graphify contains no gemma code at all,
so it cannot and does not speak to it).

---

## Verdict on our setup

**Correct as configured.** Every deliberate choice is either the directly-prescribed remedy for
a closed gemma/Ollama issue (`NUM_CTX` unset → #798; `--max-concurrency 1` +
`OLLAMA_NUM_PARALLEL=1` → #798 root cause; `--api-timeout 900` → #792 addendum) or is inert
with respect to every finding. Two optional changes, neither a correctness fix:

1. **Set `GRAPHIFY_OLLAMA_KEEP_ALIVE=0`** (or `ollama stop <model>`) between bake-off arms —
   the 30m default (`llm.py:1228`) leaves prior models resident and biases comparisons.
2. **Prefer full-corpus extracts over incremental ones** until `stitch.py` ships — incremental
   runs can leave unreachable subgraphs (#1326 Problem 3, verified unimplemented).

One expectation to drop: **`embeddinggemma` does nothing for graphify 0.9.22**, and if #7 ever
lands it will most likely arrive as ONNX/HuggingFace, not as an Ollama pull.

One gap with no workaround inside graphify: **no `temperature` / `top_p` / `top_k` / `seed`
flags** (declined in #792). If gemma4:12b output quality needs tightening, that must be done in
an Ollama `Modelfile`.

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the sole subject: issues #7, #792, #798 and PRs #252, #1126, #1326, #1398 read via `gh`; the installed 0.9.22 package source read from disk to adjudicate every load-bearing claim.
