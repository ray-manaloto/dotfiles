# Source review — 9 web sources vs our graphify/Ollama bake-off setup

Date: 2026-07-21 · Agent: source-review · Status: **COMPLETE**

Raw captures live in `.omc/kb/raw/src-*.md`.

Primary-source anchor for adjudication: installed graphify **0.9.22** at
`/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.22/graphifyy/lib/python3.14/site-packages/graphify`
(referred to below as `<GP>`).

---

## Source 1 — Augment Code, "Graphify hits 58.3K stars: knowledge graphs for AI coding assistants"

URL: <https://www.augmentcode.com/learn/graphify-knowledge-graphs-ai-coding>
Fetched: HTTP 200, 212 KB HTML. Raw: `.omc/kb/raw/src-augmentcode-graphify-knowledge-graphs.md`
Published Jun 2 2026, "Last updated: Jun 18, 2026". Author: Paula Hingel, Augment Code (a **vendor blog** — Augment sells a competing context engine; treat "My Take" as marketing).

### What it actually says

- "Developer Safi Shamsi released Graphify **v0.8.28** as the latest in a rapid series of 123 releases."
- "33-language AST extraction … parsed **locally via tree-sitter with zero API calls**. LLM-powered extraction handles docs, PDFs, and images."
- "Multiple LLM backends — Supports Gemini, Claude, OpenAI, DeepSeek, **Ollama (fully local)**, AWS Bedrock, and Kimi for semantic extraction. **Auto-detects which API key is available**."
- "Every relationship gets tagged as `EXTRACTED`, `INFERRED`, or `AMBIGUOUS`."
- "`graphify install` registers the skill with your assistant."
- "`graphify hook install` adds post-commit hooks … with a merge driver that union-merges `graph.json`."
- "`graphify prs --triage` … `graphify prs --conflicts` flags PRs that share **graph communities**."
- "`graphify export callflow-html` to get a Mermaid diagram of the full call flow."

### So what for us? — **INFORMS**, with one loud contradiction

Nothing here changes a flag, model, or step. It is a feature-tour post, not an
operator's guide: **zero** extraction-config advice — no token budget, no
concurrency, no chunking, no model recommendation, no mention of
`--max-concurrency`, `--token-budget`, or `--api-timeout`. Control arm on that
claim: the same raw capture *does* contain `graphify query`, `graphify path`,
`graphify explain`, `graphify prs`, `graphify export callflow-html`,
`graphify hook install` — so the probe can find graphify CLI strings; it found
no tuning flags because there are none.

What it *does* inform:

1. **The `EXTRACTED` / `INFERRED` / `AMBIGUOUS` confidence tag is a first-class
   graph field.** Our bake-off scores precision/recall against a gold answer key
   but (as briefed) does not stratify by confidence tag. If graphify emits it per
   edge, a model that produces many `INFERRED` edges is materially different from
   one producing `EXTRACTED` edges at the same raw count. **Candidate bake-off
   metric: precision *conditioned on* confidence tag.** (Verify the field exists
   in our own artifacts before adopting — see Synthesis A.)
2. **"Auto-detects which API key is available"** is the failure mode our explicit
   `--backend ollama` already avoids. Keep passing it explicitly; never rely on
   auto-detect in a bake-off, or arm identity silently depends on ambient env.
3. `graphify prs --conflicts` "flags PRs that share **graph communities**" —
   confirms Louvain communities are a *consumed* product, not a debug artifact.
   Relevant to our known `[all]`→Louvain-on-3.14 note.

### ⚠️ CONTRADICTION — flag loudly

> "One-command setup — **`graphify install`** registers the skill with your assistant."

This is exactly the invocation our `.claude/rules/do-not.md` #8 forbids. Bare
`graphify install` (no `--project`) mutates `~/.claude`: ~43 KB of skill files,
appends a `# graphify` H1 to `~/.claude/CLAUDE.md`, and sprays `.graphify_version`
stamps into other platforms' user skill dirs. **Adjudication: our rule wins.** It
is derived from the installed `install.py`; the blog is a third-party feature
tour written against 0.8.28 that never mentions `--project` at all. Do not let
this post's "one-command setup" framing leak into any doc or skill here.

### Staleness

`v0.8.28` (post) vs **0.9.22** (ours) — 3 minor + many patch releases behind, at
the post's own stated cadence of ~1 release every other day that is ~2 months of
drift. Every capability claim in it is a *floor*, never a current inventory.

---
## Source 3 — Mateusz Sowiński, "Graphify: A Knowledge Graph for Your Codebase"

URL: <https://www.mateusz-dev.pl/blog/posts/graphify-for-ai-coding>
Fetched: HTTP 200, 161 KB HTML. Raw: `.omc/kb/raw/src-mateuszdev-graphify-for-ai-coding.md`
Dated 2026-07-11 (10 days old — the freshest of the graphify posts). Part 04 of a
"Token Efficiency in AI Coding" series. Independent blog, no vendor stake.

**This is the only source of the three with real operator content.**

### What it actually says

- "extracts code structure locally via tree-sitter, across roughly **40 languages**, with zero API calls" (source 1 said 33 — see Contradictions)
- "detects communities via **Leiden clustering** and highlights 'god nodes'"
- "**semantic extraction of docs, PDFs, and images goes through an API backend, unlike code extraction**"
- "every edge carries a confidence label such as `EXTRACTED`, `INFERRED`, or `AMBIGUOUS`"
- Real numbers from his Next.js repo: "**1412 nodes, 3092 edges, 109 communities across 325 files**", "token cost of the build: **0**, because code extraction is AST-only"
- ⭐ "One practical lesson from this repo: **scope matters. My early graphs also indexed the blog articles themselves, and long-form prose is poison for a code graph — its words either connect to nothing or to everything. A few lines in `.graphifyignore` restricting extraction to source directories made the graph noticeably tighter and the communities cleaner.**"
- "if you have clean structure of the project you might not need Graphify … It makes sense to use Graphify in a repo where you have many different components and you want to understand how they are connected."
- "Graphs above roughly **5000 nodes** skip HTML generation entirely, and there is a configurable size cap."
- "`graphify update .` refreshes changed content without a full rebuild"

### Primary-source verification (all four load-bearing claims CONFIRMED in 0.9.22)

| Claim | Probe | Result |
|---|---|---|
| Leiden clustering | `<GP>/cluster.py:1` | ✅ *"Uses **Leiden (graspologic) if available, falls back to Louvain (networkx)**"*; `cluster.py:25-26`, `:48` `from graspologic.partition import leiden`, `:74-76` nx louvain fallback |
| `.graphifyignore` is real | `grep -rn graphifyignore <GP> --include="*.py"` | ✅ 20+ hits; `detect.py:834` gitignore-spec parser, `detect.py:939` `_load_graphifyignore`, `detect.py:915-918` — merged AFTER `.gitignore`, **"can only ever exclude MORE, never re-include"** |
| confidence tag vocabulary | `<GP>/validate.py:5` | ✅ `VALID_CONFIDENCES = {"EXTRACTED","INFERRED","AMBIGUOUS"}`; `export.py:159` `_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED":1.0,"INFERRED":0.5,"AMBIGUOUS":0.2}`; prompt at `llm.py:457,478,486` |
| ~5000-node HTML cap | `<GP>/exporters/html.py:13` | ✅ `MAX_NODES_FOR_VIZ = 5_000`, env-overridable (`html.py:18-28`); `__main__.py:543` documents `--no-viz` |

Control arm for the grep sweep: the same `--include="*.py"` sweep returned
**0 files** for `mlx`/`lmstudio` (per the brief) and **20+** for
`graphifyignore` — the probe discriminates.

### So what for us? — **ADOPT** (two concrete changes) + INFORMS

**ADOPT-1 — `.graphifyignore` in every bake-off arm's corpus dir, and treat scoping as a controlled variable.**
"Long-form prose is poison for a code graph — its words either connect to
nothing or to everything" is a *direct hazard to our bake-off design*: our gold
corpus is **7 fictional documents with lexical decoys**. Decoys are precisely the
"connect to everything" failure mode he describes. That is not a reason to drop
them — they are the discriminator — but it means **corpus scoping is a variable
we are currently not controlling**, and if any arm's fresh dir picks up an
ancestor `.gitignore` (which `_load_graphifyignore` walks up to the VCS root,
`detect.py:1107`) the arms are not identical. **Action:** the bake-off harness
should either (a) write an explicit `.graphifyignore` into each fresh run dir, or
(b) assert in the manifest which ignore files were in effect. Ancestor-`.gitignore`
inheritance is a silent arm-identity leak today.

**ADOPT-2 — score precision/recall *stratified by confidence tag*, and use `confidence_score` as a weight.**
`export.py:159` gives us the vendor's own weights (1.0 / 0.5 / 0.2). A model that
hits recall by emitting everything as `AMBIGUOUS` should not tie a model that
emits `EXTRACTED`. Cheap to add: our scorer already reads `graph.json`.
This also gives a **second, model-sensitive signal at n=1** — hedging rate — that
may separate arms where raw edge counts sit inside the noise floor.

**INFORMS-1 — his numbers are a sanity scale.** 325 files → 1412 nodes / 3092
edges ≈ **4.3 nodes and 9.5 edges per file**. Our 7-doc corpus should land in the
low tens-to-hundreds of nodes; anything wildly outside that ratio is a signal the
run degenerated, not that the model is good.

**INFORMS-2 — `MAX_NODES_FOR_VIZ` is irrelevant at our corpus size** (7 docs ≪
5000 nodes), so HTML is always generated; it is not a hidden per-arm cost
difference. Recorded so nobody re-derives it.

**INFORMS-3 — "code is AST-only, zero tokens; docs/PDFs/images go to the backend."**
This is the *reason* our fictional-document corpus is the right test bed: it
exercises the **only** path where the model matters. A code-heavy corpus would
have measured tree-sitter, not the model. Our design is already correct; this
source explains why.

---

## Source 4 — Sukanta Kumar Rout (LinkedIn Pulse), "How I Used Graphify + Ollama to Automatically Create Documentation for My C# Project (Fully Local Setup)"

URL: <https://www.linkedin.com/pulse/how-i-used-graphify-ollama-automatically-create-my-c-project-rout-lpg0c/>
Fetched: **HTTP 200, RETRIEVED IN FULL** despite an auth-wall banner in the markup —
LinkedIn Pulse serves article body to unauthenticated UAs. Raw:
`.omc/kb/raw/src-linkedin-graphify-ollama-csharp.md`. Published **May 16, 2026**
(~2 months old; graphify was ~0.8.x then). 8 reactions, 1 comment — low-signal, single-anecdote post.

### What it actually says

- Setup: "Graphify for repository analysis / Ollama for local LLM inference / **Qwen2.5 model** for reasoning / ASP.NET Core for orchestration"
- `ollama pull qwen2.5:7b` then `ollama serve`
- "Models I Tested during this POC work — I experimented with several local models. **For my use case, Qwen2.5:7b gave the best overall results.**" (No list of what else was tried. No metric. No repeats.)
- ⭐ "The key lesson I learned: **DO NOT send the entire graph to the model.** Initially I tried that and quickly ran into: huge prompts, **timeout issues**, slow inference, memory problems. The better approach was: 1. Retrieve only relevant graph nodes 2. Build focused prompts 3. Ask the model to summarize architecture."
- Invocation printed as `graphify - repo C:/Projects/MyCSharpPlatform` (mangled by LinkedIn's typography; not a real flag — see Contradictions).
- Cites "Why I Chose Graphify: **https://graphify.net/**" — a domain that is not the project's (PyPI `graphifyy`, GitHub). Do not follow.

### So what for us? — **INFORMS** (weakly), one flag validated

1. **His "best model" finding is worth exactly nothing to us as a ranking**, and it
   is the same defect `.claude/rules/probes-need-a-control-arm.md` §6 was written
   for: n=1, no corpus stated, no noise floor, no list of the losing models, and a
   different task (documentation prose generation, not KG extraction). It does
   **not** override our own measured `qwen2.5-coder:14b` winner — if anything it is
   a weak concurrence that the qwen2.5 family suits this workload.
2. **His failure mode is downstream of extraction, not inside it.** "Do not send the
   entire graph to the model" is about *querying*, where he hand-rolled a RAG loop.
   graphify's own `extract` already chunks — which is what our `--token-budget 12000`
   controls. So his lesson is not an argument to change our flag; it is
   circumstantial support that **12000 is on the right side of the tradeoff** and
   that raising it toward "whole corpus in one prompt" would reproduce his
   "timeouts / memory problems" outcome. Our `--api-timeout 900` is the mitigation
   he lacked.
3. **7B on unknown consumer hardware.** He is on a "normal PC"; we have 96 GB
   unified memory. His model choice is hardware-driven and tells us nothing about
   our under-sized-roster hypothesis.

Nothing here changes a flag. Recorded mainly so a future session does not treat
"Qwen2.5:7b is best" as an independent second data point — it is an anecdote.

---
## Source 5 — Medium / Google Cloud, "Running an AI Agent Locally: ADK, Gemma 4 and Docker Model Runner"

URL: <https://medium.com/google-cloud/running-an-ai-agent-locally-adk-gemma-4-and-docker-model-runner-95ca9e6f506d>
Fetch: **curl → HTTP 403** (Medium bot-blocks plain curl, 6 KB challenge page).
**Retrieved via WebFetch** (extracted content, not byte-verbatim — no raw file saved
because I never held the verbatim bytes; do not treat the quotes below as
character-exact). Status: **RETRIEVED (extracted)**.

### What it actually says

- Docker Model Runner is "a built-in feature of Docker Desktop that lets you pull and run LLMs locally — just like pulling container images."
- Endpoint: **`http://localhost:12434/engines/v1`**, OpenAI-compatible.
- macOS/Windows requires explicit TCP activation: `docker desktop enable model-runner --tcp 12434`. On Docker Engine (Linux) port 12434 is on by default.
- `docker model pull ai/gemma4:E4B` / `docker model ls`
- Gemma 4 variants offered: **E2B, E4B, 26B, 31B**
- "No API key is needed; Docker Model Runner requires only a dummy placeholder."
- ADK wiring: `OPENAI_API_BASE=http://localhost:12434/engines/v1`, model prefixed `openai/`.

### So what for us? — **INERT as a backend; INFORMS on one number**

**Not a fourth option worth taking.** It is Ollama's shape (pull-a-model, serve
OpenAI-compat locally) with three strict disadvantages for *this* workload:

1. It runs under **Docker Desktop**, which on this machine is the pinned
   devcontainer runtime (`.claude/rules/do-not.md` #7 — never move
   `docker context` off `desktop-linux`). Loading a 20–60 GB model into Docker
   Desktop's VM competes for the exact resource pool our devcontainer needs, and
   `docker desktop enable model-runner --tcp 12434` mutates the shared Docker
   Desktop config. That is a real cost Ollama does not impose.
2. On Apple silicon it does **not** get us anything Ollama lacks — it is not the
   MLX/Metal path; it is another llama.cpp-family server.
3. `ai/gemma4:*` is a *different* distribution of the same weights we already
   pull from `ollama.com/library/gemma4`. New arm, no new capability.

**The one useful bit:** Docker's Gemma 4 catalog lists **26B and 31B** variants —
independent corroboration that Gemma 4 exists above the `12b` we run. Cross-checked
against the actual Ollama registry (below): `gemma4:26b` = 18 GB, `gemma4:31b` = 20 GB.
So the ceiling on our current gemma4 arm is a registry pull away, not a porting exercise.

---

## Source 6 — MLX (ml-explore/mlx) + mlx-lm server docs

URLs: <https://github.com/ml-explore/mlx> · raw README and
<https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md>
Fetch: HTTP 200 both (raw.githubusercontent.com). Raw: `.omc/kb/raw/src-mlx-README.md`,
`.omc/kb/raw/src-mlx-lm-SERVER.md`. **Verbatim.**

### What it actually says (MLX's own docs, not a blog)

From `mlx/README.md`:
> "MLX is an array framework for machine learning on Apple silicon, brought to you by Apple machine learning research."
> "**Unified memory**: A notable difference from MLX and other frameworks is the *unified memory model*. Arrays in MLX live in shared memory. Operations on MLX arrays can be performed on any of the supported device types without transferring data."

From `mlx_lm/SERVER.md` — **this answers the brief's question directly**:
> "# HTTP Model Server — You use `mlx-lm` to make an HTTP API for generating text with any supported model. The HTTP API is intended to be **similar to the OpenAI chat API**."
> "`mlx_lm.server --model <path_to_model_or_hf_repo>`"
> "This will start a text generation server on **port `8080`** of the `localhost`"
> "`curl localhost:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"messages":[…],"temperature":0.7}'`"
> "Use the **`v1/models`** endpoint to list available models"
> ⚠️ "**The MLX LM server is not recommended for production as it only implements basic security checks.**"

Supported request fields include `model`, `messages`, `temperature`, `top_p`, `max_tokens` (default **512**), `stream`, `logprobs`, `draft_model` (speculative decoding). Response carries a real `usage` object (`prompt_tokens`/`completion_tokens`/`total_tokens`).

### So what for us? — **ADOPT (as an experimental arm), and it CORRECTS an "ALREADY ESTABLISHED" fact**

**Yes, MLX is a realistic alternative — and `providers.json` is NOT required.**
The brief asked whether the custom-provider mechanism could target it. It could,
but there is a **simpler, vendor-documented path** the brief's framing missed:

> `<GP>/__main__.py:597-599` — graphify's own `--help` text:
> ```
> --backend B   gemini|kimi|claude|openai|deepseek|ollama (default: whichever API key is set)
>               openai also reaches self-hosted OpenAI-compatible servers (llama.cpp,
>               vLLM, LM Studio): set OPENAI_BASE_URL (e.g. http://localhost:8080/v1)
>               and OPENAI_MODEL to the model name your server serves
> ```
> `<GP>/llm.py:148-155` — the `openai` backend config:
> ```python
> # OPENAI_BASE_URL points the backend at any OpenAI-compatible server
> # (llama.cpp, vLLM, LM Studio, ...); OPENAI_MODEL overrides the default
> "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
> ```

Note the example port in graphify's own help is **`http://localhost:8080/v1`** —
byte-identical to `mlx_lm.server`'s default. So the concrete invocation is:

```bash
mlx_lm.server --model mlx-community/Qwen2.5-Coder-32B-Instruct-4bit     # port 8080
OPENAI_BASE_URL=http://localhost:8080/v1 \
OPENAI_API_KEY=dummy \
graphify extract <dir> --backend openai \
  --model mlx-community/Qwen2.5-Coder-32B-Instruct-4bit \
  --max-concurrency 1 --token-budget 12000 --api-timeout 900
```
(`OPENAI_API_KEY` must be **non-empty** — `<GP>/llm.py:1625-1629` raises
`No API key for backend 'openai'` on an empty key, and the ollama-style
placeholder fallback at `llm.py:1612-1623` is `backend == "ollama"` **only**.)

`~/.graphify/providers.json` (`<GP>/llm.py:221-224`, `_load_custom_providers` at
`:264`) is the *alternative* path — worth it only if we want a named arm
(`--backend mlx`) with its own pricing/temperature block. Note its guard:
project-local `./.graphify/providers.json` is **ignored** unless
`GRAPHIFY_ALLOW_LOCAL_PROVIDERS=1` (`llm.py:271-277`), and `provider_base_url_ok`
(`llm.py:227`) accepts loopback http silently. For a bake-off arm the env-var
route is strictly simpler and needs no new file.

### ⚠️ CORRECTION to an "ALREADY ESTABLISHED" fact — the original probe had a blind spot

The brief states: *"graphify supports NONE of MLX / LM Studio / Jan as a backend.
Control-armed grep … `lmstudio`, `lm_studio` … → 0 files each."*

**The literal claim is true; the operational conclusion drawn from it is wrong.**
The probe searched `lmstudio` and `lm_studio` — **not `LM Studio` with a space**:

```
$ grep -rli "lmstudio\|lm_studio" <GP>          →  0 files      (the original probe)
$ grep -rn  -i "lm studio"        <GP>          →  3 hits       (the missing arm)
      __main__.py:598 · llm.py:150 · llm.py:1906
$ grep -rn  -i "vllm\|llama\.cpp" <GP>          →  6 hits       (control arm: the probe
                                                    CAN find other OpenAI-compat servers)
$ grep -rn  -i "\bmlx\b"          <GP>          →  0 hits       (MLX genuinely absent by name)
$ grep -rn  "jan\.ai\|localhost:1234\|localhost:1337\|12434" <GP>  →  0 hits
```

Correct statement: **there is no *named* backend for MLX / LM Studio / Jan (true),
but all three are reachable today via the existing `openai` backend + `OPENAI_BASE_URL`,
and graphify's own `--help` and source comments say so explicitly for LM Studio.**
The 9-backend list is a list of *presets*, not a list of *reachable servers*. This is
the `probes-need-a-control-arm.md` §"bound-limited searches" failure mode: a token
spelling was the bound, and "not found" read as "not supported".

### ⚠️ SECOND FINDING — an MLX/LM-Studio arm is NOT flag-equivalent to an Ollama arm

`<GP>/llm.py:1194` gates the entire context/keep-alive block on the backend name:

```python
if backend == "ollama" and extra_body is None:
    ...
    num_ctx = auto_num_ctx            # min(est_input + out_cap + 2000, 131072), floor 8192
    keep_alive = os.environ.get("GRAPHIFY_OLLAMA_KEEP_ALIVE", "30m")
    kwargs["extra_body"] = {"options": {"num_ctx": num_ctx}, "keep_alive": keep_alive}
```

Under `--backend openai` (MLX / LM Studio / Jan / Docker Model Runner) graphify sends
**no `num_ctx` and no `keep_alive` at all** — the server's own defaults apply.
So a "MLX vs Ollama" arm comparison silently varies **two** things (engine *and*
context policy), not one. Any such arm must state that, or the result is another
anecdote. Also inherited: `mlx_lm.server`'s `max_tokens` default is **512**
(`SERVER.md`), whereas the ollama preset carries `max_tokens: 16384`
(`llm.py:130`) — a 32× gap that would truncate extraction JSON on MLX unless
`GRAPHIFY_MAX_OUTPUT_TOKENS` is set. **That alone would sink a naive MLX arm and
look like "MLX is worse at KG extraction".**

### One more thing the vendor comment gives us for free

`llm.py:1187-1189`, verbatim: *"Over-allocation (e.g. **128k slots for an 8k prompt on
a 31B model**) exhausts VRAM by chunk 4 and produces the same hollow-200 symptom."*
graphify's maintainers picked **31B** as the illustrative size where KV over-allocation
bites. Our `GRAPHIFY_OLLAMA_NUM_CTX` being **deliberately unset** is exactly the
recommended posture, and matters *more* as we scale the roster to 30B+, not less.
**Keep it unset.** Do not "helpfully" pin it when adding the big arms.

---

## Source 7 — LM Studio (lmstudio.ai)

URLs: <https://lmstudio.ai/> and <https://lmstudio.ai/docs/developer/openai-compat>
Fetch: HTTP 200 both. Raw: `.omc/kb/raw/src-lmstudio-home.md`, `.omc/kb/raw/src-lmstudio-openai-compat.md`

### What it actually says (vendor docs)

> "Set the base url to point to LM Studio — You can reuse existing OpenAI clients (in Python, JS, C#, etc) by switching up the 'base URL' property to point to your LM Studio instead of OpenAI's servers."
> "**Note: The following examples assume the server port is 1234**"
> `base_url="http://localhost:1234/v1"` · `curl http://localhost:1234/v1/chat/completions`
> Supported: `/v1/chat/completions`, `/v1/completions` (legacy), `/v1/embeddings`, `/v1/models`, `/v1/responses`, Structured Output, Tool Use, plus an **Anthropic Compatibility** surface.
> "Codex is supported because LM Studio implements the OpenAI-compatible `POST /v1/responses` endpoint."

### So what for us? — **INFORMS** (viable, but no reason to prefer it)

- **OpenAI-compatible: YES. Default port: 1234. Path: `/v1`.** Confirmed from LM Studio's own docs, as the brief asked.
- Reachable via `OPENAI_BASE_URL=http://localhost:1234/v1 --backend openai` — and it is the server graphify's own comment names.
- **Models Ollama does not have: not materially.** LM Studio's catalog is Hugging Face GGUF + MLX-community repos. That *is* broader than `ollama.com/library` in the tail, but for the 30B-class instruct/coder models we care about, Ollama already carries them (verified below). LM Studio's real differentiators are a GUI and an **MLX backend** — and if we want MLX we should drive `mlx_lm.server` directly rather than add a desktop GUI to a scripted, reproducible bake-off harness.
- **Against it for our use:** it is a GUI-first desktop app whose server is started from the UI. Our harness needs headless, scriptable, manifest-recordable arm setup. `lms` CLI exists but adds a dependency for zero capability gain over `mlx_lm.server`.
- Its `/v1/embeddings` endpoint is noted for completeness — we currently use `embeddinggemma` via Ollama.

---

## Source 8 — Jan (jan.ai)

URLs: <https://jan.ai/> (JS-rendered, no usable text) → docs at <https://www.jan.ai/docs/desktop/api-server>
Fetch: home HTTP 200 but client-rendered (grep for `1337`/`openai` over 2.4 MB of markup → **0 hits**; that is a rendering artifact, not absence). Docs page HTTP 200, 80 KB, **content confirmed**. Raw: `.omc/kb/raw/src-jan-home.md`, `.omc/kb/raw/src-jan-api-server.md`
Note: `https://jan.ai/docs/api-server` → **404**; the live path is `https://www.jan.ai/docs/desktop/api-server`.

### What it actually says (vendor docs)

> "Jan provides a built-in, **OpenAI-compatible API server** that runs entirely on your computer, **powered by llama.cpp**. Use it as a drop-in replacement for cloud APIs…"
> "The server is ready when the logs show `JAN API listening at http://127.0.0.1:1337`."
> "`curl http://127.0.0.1:1337/v1/chat/completions …`"
> "**1337 (Default)**: A common alternative port." · "**`/v1` (Default)**: Follows OpenAI's convention."
> API Key: "If a key is configured, requests must include it in the `Authorization: Bearer YOUR_API_KEY` header."
> Also lists "Local AI Engine: **Llama.cpp / MLX**" and an Anthropic-compatible messages endpoint.

### So what for us? — **INERT**

- **OpenAI-compatible: YES. Default port: 1337. Path: `/v1`.** Question answered.
- **Models Ollama does not have: no.** It is a llama.cpp/MLX front-end over GGUF + Hugging Face — the same weights, plus Jan's own small `Jan-v1` / `Jan-Code-4B` fine-tunes, which are 4B-class and therefore *below* the size range our under-sized-roster hypothesis is about.
- Same GUI-first objection as LM Studio, with a smaller catalog and no advantage. If we want the MLX engine, drive `mlx_lm.server`; if we want llama.cpp, we already have Ollama. **No arm.**

---

## Source 9 — Codersera, "Local AI Model Picker"

URL: <https://codersera.com/tools/local-ai-model-picker>
Fetch: HTTP 200, 61 KB. Raw: `.omc/kb/raw/src-codersera-local-ai-model-picker.md`
"Last updated 2026-06-16". **Low trust: this is an SEO/lead-gen page** for a
dev-staffing agency ("Hire Developers", "Hire a Developer"), and it openly admits
forward-projecting model names: *"When a forward-projected name doesn't have a real
HuggingFace page yet, we point to the closest currently-shipping model and label it honestly."*

### What it actually says

- Runtime one-liners: "Ollama is the easiest entry point… OpenAI-compatible REST API on localhost:11434." / "**MLX** — Apple's native ML framework. Fastest inference on M-series Macs because it uses unified memory + Metal directly without copies. Use mlx-lm … **expect 2-3× the throughput of llama.cpp on the same hardware**." / "vLLM … not for desktop chat."
- Sizing rule: "**working-set memory ≈ 0.6 GB per billion parameters**, plus 2-4 GB for KV cache + overhead" at Q4_K_M. "Add 4-8 GB for OS / apps."
- RAM table row for us: "**96 GB+ — Command R+ (104B) · DeepSeek V4 MoE 670B** — Server / workstation. You can run almost any open model."
- Also: "48-64 GB — Llama 4 70B · Kimi K2.6 70B · Hermes 4 70B … Approaches GPT-4-class quality."

### So what for us? — **INFORMS on sizing arithmetic only; the model names are NOT usable**

**Do not lift model names from this page.** Control arm on that judgement — I checked
its names against the actual Ollama registry (`ollama.com/library/<name>/tags`,
bogus name → 404 so the probe discriminates):

| Codersera name | Ollama library probe | verdict |
|---|---|---|
| `DeepSeek V4` / `DeepSeek Coder V4 6.7B` | `library/deepseek-v4` → **HTTP 404** | **does not exist there** |
| `Llama 4 8B` (16 GB row) | `library/llama4/tags` → smallest is `scout` / `16x17b` = **67 GB** | **no 8B variant exists** |
| `Qwen 3.6 27B / 35B-A3B` | not in the library tag list | forward-projected |
| `Gemma 4 27B` | real tags are **`gemma4:26b` (18 GB)** and **`gemma4:31b` (20 GB)** | approximately right, name wrong |

So its catalog is a mix of real and invented. What survives is the **arithmetic**,
which is standard and independently checkable: ~0.6 GB/B at Q4 + KV. Applied to a
96 GB M2 Max (minus ~8 GB OS): **a 70B dense model at Q4 ≈ 42 GB + KV — comfortably
resident.** That is the number that matters for the "roster is badly under-sized"
hypothesis, and it holds regardless of this page's naming.

The MLX "2-3× throughput vs llama.cpp" figure is **uncited** here and should be
treated as marketing until measured on our own corpus. It is a hypothesis for an
arm, not a finding.

---
# Synthesis

## A. Does anything change the BAKE-OFF?

**Yes — three things, in descending order of value.**

### A1. The roster IS badly under-sized, and the fix is a registry pull, not a port

Our largest arm ever is **18 GB** (`qwen3-coder:latest` = `30b-a3b-q4`) on **96 GB**
unified memory. Applying the standard Q4 arithmetic (~0.6 GB/B + KV, corroborated by
source 9 and by the measured tag sizes below), the machine's practical headroom after
~8 GB for macOS is **~85 GB** — i.e. we are using **~21 %** of it.

Measured against the real Ollama registry (`ollama.com/library/<f>/tags`; control arm:
`library/deepseek-v4` → **404**, so a bogus family is distinguishable from a real one):

| candidate | size | why it belongs in the bake-off |
|---|---|---|
| **`qwen2.5-coder:32b`** | **20 GB** | ⭐ **highest-value single arm.** Same family/tuning as our measured winner `qwen2.5-coder:14b`, ~2.3× params. It isolates **scale alone** with family held constant — the one comparison our current data cannot make. |
| **`gemma4:31b`** (or `:26b`, 18 GB) | 20 GB | Same for the gemma4 line vs our `gemma4:12b`. Corroborated independently by Docker's catalog (source 5: "E2B, E4B, 26B, 31B"). |
| **`qwen3:32b`** | 20 GB | Scale-up of `qwen3:14b`; completes the third family. |
| **`qwen3-coder:30b-a3b-q8_0`** | 32 GB | Same weights we already run, at **q8 instead of q4**. Isolates **quantization** — a variable currently confounded with model choice across every arm. |
| `qwen3-coder:30b-a3b-fp16` | 61 GB | Unquantized ceiling of a model we already have. Fits. The definitive "is q4 costing us extraction quality?" answer. |
| **`llama3.3:70b`** (q4) | **43 GB** | The first true **70B dense** arm. Different lineage entirely — the strongest test of "is 14B the bottleneck?" |
| **`gpt-oss:120b`** | 65 GB | Fits in 96 GB. Largest credible arm available. |
| `deepseek-r1:32b` | 20 GB | A *reasoning*-tuned 32B — plausibly good at relation inference, plausibly terrible at strict JSON. Cheap to find out. |
| `mistral-small3.2:24b` / `devstral:24b` | 15 / 14 GB | Apache-2.0 mid-size controls. Low priority. |
| ~~`llama4:scout`~~ | 67 GB | Fits, but 109B MoE at 67 GB with `keep_alive=0` is a punishing reload cost. Only after A2. |

**Recommended next matrix:** hold everything else fixed and run
`qwen2.5-coder:14b` (incumbent) → `qwen2.5-coder:32b` → `qwen3-coder:30b-a3b-q4` →
`qwen3-coder:30b-a3b-q8_0` → `llama3.3:70b`, plus the existing NULL arm. That is
**one family-scale axis, one quantization axis, one lineage axis** — three answerable
questions instead of five incomparable points.

### A2. ⚠️ `GRAPHIFY_OLLAMA_KEEP_ALIVE=0` becomes a serious cost at 30B+ — reconsider it per-arm

`<GP>/llm.py:1228` — graphify's default is `"30m"`; we override to **`0`**, which
unloads the model **after every chunk**. At 9 GB that is a tolerable few seconds. At
**43 GB (`llama3.3:70b`) or 61–65 GB** it is a full re-read of tens of GB from disk
into unified memory *per chunk*, and with `--api-timeout 900` a slow reload can be
mistaken for a slow model.

This is a genuine tension: `keep_alive=0` is what makes our arms **memory-clean and
independent**, which is exactly the isolation the harness was built for. So do not
just flip it — **decide it explicitly and record it in the manifest**:
- keep `0` for isolation, and **measure the load cost separately** (a warm-up call
  outside the timed window), or
- set a short non-zero keep-alive **uniformly across all arms including the NULL arm**,
  so the confound is constant.

Either is defensible; silently keeping `0` while scaling to 43 GB is not. **The one
thing that must not happen is `keep_alive` differing between arms.**

### A3. Add confidence-tag stratification to the scorer (cheap, high signal)

Both source 1 and source 3 highlight the per-edge tag, and it is real in 0.9.22:
`<GP>/validate.py:5` `VALID_CONFIDENCES = {"EXTRACTED","INFERRED","AMBIGUOUS"}`,
weights at `<GP>/export.py:159` `{"EXTRACTED":1.0,"INFERRED":0.5,"AMBIGUOUS":0.2}`,
and the extraction prompt instructs the model to *"Mark uncertain ones AMBIGUOUS
instead of omitting"* (`<GP>/llm.py:486`).

That last line is the point: **the prompt actively rewards hedging**, so raw
edge-count recall silently favours whichever model hedges most. Report
(a) precision/recall **per tag**, and (b) a `confidence_score`-weighted score using
the vendor's own weights. It costs one pass over `graph.json` and gives a
**second, orthogonal discriminator** — useful precisely where n=3 raw counts sit
inside the NULL-arm noise floor.

### A4. MLX — realistic, but run it as a deliberate experiment, not a bake-off arm

**Verdict: worth ONE scoped probe, and it must not be scored against the Ollama arms.**

- ✅ It works: `mlx_lm.server` serves **OpenAI-compatible `/v1/chat/completions` on
  port 8080** (`mlx_lm/SERVER.md`, quoted above), and graphify reaches any such server
  via `--backend openai` + `OPENAI_BASE_URL` — its own `--help` gives
  `http://localhost:8080/v1` as the example (`<GP>/__main__.py:598`). **No
  `providers.json` required.**
- ✅ The Apple-silicon rationale is real and from Apple's own README: unified memory,
  no host↔device copies.
- ❌ But **it is not flag-equivalent** (see Source 6, second finding): under
  `--backend openai`, graphify sends **no `num_ctx` and no `keep_alive`**
  (`llm.py:1194` gates on `backend == "ollama"`), and `mlx_lm.server`'s `max_tokens`
  default is **512** vs the ollama preset's **16384** (`llm.py:130`). A naive MLX arm
  would truncate its own JSON output and look like a bad model.
- ⚠️ MLX's own docs: *"not recommended for production as it only implements basic
  security checks."* Fine for a local probe; note it.

**If run:** set `GRAPHIFY_MAX_OUTPUT_TOKENS=16384`, use an
`mlx-community/*-4bit` build of a model we already have on Ollama, and frame the
result strictly as **"same weights, different engine — throughput and JSON-validity
delta"**, never as a quality ranking against Ollama arms.

### A5. LM Studio / Jan / Docker Model Runner — answered, and all three are declined

| | OpenAI-compatible? | default port | path | models Ollama lacks? | verdict |
|---|---|---|---|---|---|
| **LM Studio** | ✅ (vendor docs) | **1234** | `/v1` | Not materially (HF GGUF + MLX repos; tail only) | **INFORMS** — viable, GUI-first, no gain over `mlx_lm.server` |
| **Jan** | ✅ (vendor docs) | **1337** | `/v1` | No (llama.cpp/MLX over GGUF; own models are 4B-class) | **INERT** |
| **Docker Model Runner** | ✅ (source 5) | **12434** | `/engines/v1` | No (`ai/gemma4:*` = same weights) | **INERT** — and it contends with Docker Desktop, our pinned devcontainer runtime |

All three are reachable the same way as MLX (`--backend openai` + `OPENAI_BASE_URL`)
should that ever change. **None of them is a fourth option worth taking today** —
every one is a different front-end over weights Ollama already serves, and each adds a
GUI/daemon dependency to a harness whose value is that it is scriptable and
manifest-recordable.

---

## B. Does anything change how we USE graphify?

**Two concrete changes and one confirmation.**

### B1. ADOPT — control corpus scoping explicitly (`.graphifyignore`) — source 3

> *"long-form prose is poison for a code graph — its words either connect to nothing
> or to everything. A few lines in `.graphifyignore` restricting extraction to source
> directories made the graph noticeably tighter and the communities cleaner."*

Two consequences:

1. **Arm-identity leak (act on this).** `_load_graphifyignore` (`<GP>/detect.py:939`)
   walks the **ancestor chain up to the VCS root** (`detect.py:1107`) and **merges
   `.gitignore` too** (`detect.py:929`, `:915-918`). Our harness makes a *fresh
   directory per run* — if any of those dirs sit under a git tree, arms can inherit
   *different* ignore sets depending on where they land. Fix: write an explicit
   `.graphifyignore` into each run dir **and record its content hash in the manifest**.
   Today the manifest cannot prove two arms saw the same corpus.
2. **Interpretation of our gold corpus.** Our 7 fictional docs *are* long-form prose
   with lexical decoys — precisely the "connects to everything" shape. That is the
   right test (it is the only path where the model matters — see B3) but it means our
   absolute precision numbers will look poor by his standards. **Judge arms against
   each other and the NULL arm, never against an absolute bar.**

### B2. ADOPT — do not raise `--token-budget` toward "whole corpus in one prompt" — source 4

> *"DO NOT send the entire graph to the model. Initially I tried that and quickly ran
> into: huge prompts, timeout issues, slow inference, memory problems."*

His failure is downstream (querying), but the mechanism is identical and it is
independently confirmed by graphify's own code: over-large contexts cause **hollow
200 OK responses** (`<GP>/llm.py:1184-1189`, issue #798) from *both* directions —
truncation when `num_ctx` is too small, KV exhaustion when it is too large.
**`--token-budget 12000` + auto-derived `num_ctx` + `--api-timeout 900` is the
correct posture; keep it, and keep `GRAPHIFY_OLLAMA_NUM_CTX` unset** (graphify's own
comment names *"128k slots for an 8k prompt on a 31B model"* as the OOM shape —
directly relevant as we add 31B+ arms).

### B3. CONFIRMED — a document corpus is the right test bed

Sources 1, 3 and the code all agree: **code extraction is tree-sitter AST, zero LLM
calls; docs/PDFs/images are the only model-driven path.** A code-heavy bake-off
corpus would have measured tree-sitter, not the model. Our fictional-document corpus
is correct by construction. Recorded so nobody "improves" it into a code corpus.

### B4. Rejected as guidance

- **`graphify install`** (source 1) — forbidden here; see the Contradictions section.
- **`graphify -repo <path>`** (source 4) — not a real flag; LinkedIn typography mangled it.
- **`graphify update .` for incremental refresh** (source 3) — real and useful for
  day-to-day use, but **must never be used in a bake-off run**: it reads the
  incremental manifest and semantic cache, which is exactly what our fresh-dir
  isolation exists to defeat. `--force` (`<GP>/__main__.py`, `GRAPHIFY_FORCE=1`) is
  the bake-off-safe direction.

---

## C. Contradictions — adjudicated against primary sources

### C1. ⚠️⚠️ **"graphify supports NONE of MLX / LM Studio / Jan as a backend" — literally true, operationally misleading. CORRECT IT.**

The established fact's grep used the tokens `lmstudio` / `lm_studio`. graphify spells
it **"LM Studio"**, with a space, in three places — including its own `--help`:

> `<GP>/__main__.py:597-598`
> ```
> openai also reaches self-hosted OpenAI-compatible servers (llama.cpp,
> vLLM, LM Studio): set OPENAI_BASE_URL (e.g. http://localhost:8080/v1)
> ```

**Adjudication (installed code beats the prior probe):** there is no *named preset*
for MLX / LM Studio / Jan — that part stands, and MLX/Jan are genuinely absent by
name (0 hits for `\bmlx\b`, `jan.ai`, `localhost:1234`, `localhost:1337`, `12434`).
But **all four are reachable today** through the `openai` backend + `OPENAI_BASE_URL`,
and the vendor documents that path for LM Studio explicitly. The 9-backend list is a
list of presets, not of reachable servers. Restate the fact that way in memory.

Control arm proving the corrected probe discriminates: `vllm|llama\.cpp` → 6 hits,
`\bmlx\b` → 0 hits, in the same sweep. It can find OpenAI-compat server names; MLX
really is absent, LM Studio really is present.

### C2. ⚠️ **"`graphify install` registers the skill with your assistant" (source 1) — contradicts `do-not.md` #8.**

**Adjudication: our rule wins**, and by the widest possible margin — the rule is
derived from the installed `install.py`; the blog is a vendor feature tour against
**0.8.28** that never mentions `--project`. Bare `graphify install` mutates
`~/.claude`. **Ignore the blog's "one-command setup" framing entirely.**

### C3. Leiden vs Louvain — *not* a contradiction; our note was under-specified

Source 3 says "Leiden clustering"; our memory says "`[all]` → Louvain on 3.14".
`<GP>/cluster.py:1` reconciles both: *"Uses **Leiden (graspologic) if available, falls
back to Louvain (networkx)**."* So Leiden is the intended algorithm and **we are
running the fallback** because `graspologic` is unavailable on Python 3.14.

**This is a live bake-off concern, not a footnote.** Community structure is a scored
output, Leiden and Louvain do not produce identical partitions, and if `graspologic`
availability ever differs between arms the community counts are incomparable.
**Action: assert the resolved clustering backend in the run manifest.** Also worth
noting our arms are being scored on the *fallback* algorithm, which is not what the
tool's authors consider "best quality" (`cluster.py:25`).

### C4. Node/language counts differ between sources — both are stale, neither matters

Source 1 says **33 languages**; source 3 says **~40**. Both are third-party counts of
different releases (0.8.28 vs ~0.9.x). Irrelevant to us — our corpus is documents, and
the AST path is not under test. Recorded only so the discrepancy is not re-litigated.

### C5. Source 9's model catalog is partly invented — do not seed the roster from it

`DeepSeek V4` → `ollama.com/library/deepseek-v4` **HTTP 404**; `Llama 4 8B` does not
exist (smallest `llama4` tag is 67 GB); `Qwen 3.6` is forward-projected. The page says
so itself. Its **arithmetic** (~0.6 GB/B at Q4) is standard and survives; its
**names** do not. Every model in the A1 table was verified against the live registry
instead.

### C6. No source contradicted the "Our setup" facts

Ollama 0.32.1, graphify 0.9.22 host-only via mise pipx, the flag set, and the local
model list were all consistent with or unaddressed by every source. Source 4's
`qwen2.5:7b` "best model" is **not** a contradiction of our `qwen2.5-coder:14b`
result — different task, different hardware, n=1, no noise floor, and no list of the
models it beat. It is an anecdote (`probes-need-a-control-arm.md` §6) and must not be
recorded as a second data point.

---

## Retrieval ledger

| # | Source | Status |
|---|---|---|
| 1 | augmentcode.com — Graphify 58.3K stars | ✅ RETRIEVED (curl 200, verbatim) |
| 3 | mateusz-dev.pl — Graphify knowledge graph | ✅ RETRIEVED (curl 200, verbatim) |
| 4 | linkedin.com/pulse — Graphify + Ollama C# | ✅ RETRIEVED **in full** (curl 200; auth-wall banner present in markup but article body served to an unauthenticated desktop UA) |
| 5 | medium.com/google-cloud — ADK + Gemma 4 + Docker Model Runner | ⚠️ **curl 403** (Medium bot-block). Retrieved via WebFetch as **extracted content, not byte-verbatim**. |
| 6 | github.com/ml-explore/mlx (+ mlx-lm SERVER.md) | ✅ RETRIEVED (raw.githubusercontent 200, verbatim) |
| 7 | lmstudio.ai (+ /docs/developer/openai-compat) | ✅ RETRIEVED (curl 200, verbatim) |
| 8 | jan.ai | ⚠️ home page is client-rendered (200 but no text). **Docs retrieved** at `www.jan.ai/docs/desktop/api-server` (200). `jan.ai/docs/api-server` → 404. |
| 9 | codersera.com — Local AI Model Picker | ✅ RETRIEVED (curl 200, verbatim) — low trust, see C5 |

Nothing was invented. Where a fetch failed or was partial, it is marked above.

---

## GitHub repos touched

- [ml-explore/mlx](https://github.com/ml-explore/mlx) — README read for the unified-memory / Apple-silicon claim (source 6).
- [ml-explore/mlx-lm](https://github.com/ml-explore/mlx-lm) — `mlx_lm/SERVER.md` read for the OpenAI-compatible endpoint, port 8080, and the `max_tokens` default of 512.
- [ml-explore/mlx-examples](https://github.com/ml-explore/mlx-examples) — referenced from the MLX README; not read.
- [ml-explore/mlx-swift](https://github.com/ml-explore/mlx-swift), [ml-explore/mlx-c](https://github.com/ml-explore/mlx-c) — listed in the MLX README as sibling APIs; not read.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; rules and bake-off harness referenced.

Not a GitHub repo but the primary adjudication source throughout: the **installed
graphify 0.9.22 package** at
`~/.local/share/mise/installs/pipx-graphifyy/0.9.22/graphifyy/lib/python3.14/site-packages/graphify`
(PyPI `graphifyy`). Files cited: `llm.py`, `cluster.py`, `detect.py`, `validate.py`,
`export.py`, `exporters/html.py`, `__main__.py`, `serve.py`.
