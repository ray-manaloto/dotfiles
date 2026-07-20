# Follow-up: Multi-Provider / Multi-Subscription Backends for Cheap Bulk LLM Work

**Date:** 2026-07-19
**Question:** How do we route bulk LLM grunt work (graphify knowledge-graph
ingestion, sub-agent tasks) to free / cheap / local models on a Mac, and reserve
the Claude subscription for orchestration? Emphasis on **features/techniques to
adopt or build**, not just products. Free/self-hostable options only for
adoption; paid ones cited as feature references.

**Bottom line up front:** graphify's extractor already has the seam we need —
`--backend openai` honours `OPENAI_BASE_URL`, and `--backend ollama` needs no
key. That single fact means **doc ingestion can run at $0 against a local Ollama
model, or against NVIDIA's free OpenAI-compatible endpoint, without spending one
Claude token.** For Claude Code itself (and sub-agents), the `ANTHROPIC_BASE_URL`
/ `ANTHROPIC_AUTH_TOKEN` env pair lets a proxy swap the model under the harness.
Concrete recommendation and setup at the end.

---

## 1. NVIDIA NIM as a free Claude Code backend

There are **two distinct paths**, and they are frequently conflated. Both are
real; they differ in where inference runs and which wire protocol is spoken.

### Path A — self-hosted NIM, native Anthropic protocol (official NVIDIA doc)

NVIDIA's official Claude Code integration doc
([docs.nvidia.com/nim/.../claude-code.html](https://docs.nvidia.com/nim/large-language-models/latest/ai-assistant-integrations/claude-code.html))
assumes **you have deployed a NIM container yourself** and it serves an
**Anthropic-compatible `/v1/messages` endpoint**. Claude Code is pointed at it
purely through env vars — no code change:

```bash
export ANTHROPIC_BASE_URL="http://${NIM_ENDPOINT}:${NIM_SERVER_PORT}"   # default port 8000
export ANTHROPIC_API_KEY="not-used"          # "NIM does not validate ANTHROPIC_API_KEY. Set it to any non-empty string"
export ANTHROPIC_CUSTOM_MODEL_OPTION="${MODEL_NAME}"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="${MODEL_NAME}"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${MODEL_NAME}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="${MODEL_NAME}"
export CLAUDE_CODE_SUBAGENT_MODEL="${MODEL_NAME}"
```

Notes from the doc: Claude Code **requires tool calling**, so the served model
must support tool use. This is the mechanism that makes NIM look like Anthropic
to Claude Code: it re-implements the `/v1/messages` shape. **Cost is your own
GPU / DGX** — "free" only if you already own the hardware. On an arm64 Mac this
is **not** a practical local path (NIM containers target NVIDIA GPUs), so Path A
matters to us only if we ever run NIM on a rented/owned GPU box.

### Path B — free *hosted* NIM at build.nvidia.com, via a translating proxy (the blog)

The blog
([themenonlab.blog/.../free-claude-code-nvidia-nim-proxy-zero-api-fees](https://themenonlab.blog/blog/free-claude-code-nvidia-nim-proxy-zero-api-fees))
describes the genuinely-free path: NVIDIA hosts 100+ models on
**`https://integrate.api.nvidia.com/v1`**, an **OpenAI-compatible** endpoint
(vLLM-backed), free to NVIDIA Developer Program members. Because Claude Code
speaks Anthropic and NIM-hosted speaks OpenAI, the blog puts a **proxy** in
between (`free-claude-code` / `fcc-server`; LiteLLM is the general-purpose
equivalent) that translates Anthropic `/v1/messages` ⇄ OpenAI
`/v1/chat/completions`:

```bash
# 1. Get a free key at build.nvidia.com/settings/api-keys  (no credit card)   → nvapi-...
# 2. Run a translating proxy (fcc-server, or LiteLLM) and paste NVIDIA_NIM_API_KEY in its admin UI
# 3. Point Claude Code at the proxy's Anthropic endpoint:
export ANTHROPIC_BASE_URL="http://localhost:<proxy-port>"
export ANTHROPIC_AUTH_TOKEN="anything-nonempty"     # proxy holds the real nvapi- key
```

**Free-tier limits (corroborated across sources):** **~40 requests/minute**,
account-level, across NIM models; upgrade to ~200 RPM by request. Historical
"1,000 signup credits, up to 5,000 total" appears to have shifted toward pure
rate-limiting with no per-token billing on the free tier — treat the credit
numbers as stale and the **40 RPM** as the real constraint. Sources:
[decodethefuture](https://decodethefuture.org/en/nvidia-nim-api-pricing-limits-guide/),
[yangmao.ai free-tier](https://yangmao.ai/en/providers/nvidia-build/free-tier/),
[NVIDIA dev forums rate-limit thread](https://forums.developer.nvidia.com/t/api-rate-limit-increase-for-nvidia-nim/366043).

**Models (truly free):** 100+ open-weight models — Llama (incl. 405B), Qwen3 /
Qwen3-Coder, DeepSeek, Kimi K2, Mistral, Gemma, GLM, MiniMax, and NVIDIA
Nemotron. Sources:
[ai-sdk.dev NIM provider](https://ai-sdk.dev/providers/openai-compatible-providers/nim),
[NVIDIA LLM API reference](https://docs.api.nvidia.com/nim/reference/llm-apis).
*(Caveat / control-arm: a page-summarizer returned some exotic version strings —
"nemotron-3-super-120b", "kimi-k2.5", "glm5.1", "minimax-m2.5" — that I could not
independently confirm; treat the **build.nvidia.com catalog UI as the authority**
for exact model IDs before pinning one.)*

**Quality tier:** frontier-open-weight. Llama-405B / Qwen3-Coder-480B / Kimi-K2
are strong on structured extraction and summarization — below top Claude/Gemini
on hard reasoning, comfortably adequate for graphify node/edge extraction and
doc/code summarization.

**Is it OpenAI-compatible (so graphify `--backend openai` + a base URL works)?**
**Yes — directly, with no proxy.** `integrate.api.nvidia.com/v1` is a standard
OpenAI endpoint. For graphify we skip the Anthropic proxy entirely and point the
OpenAI backend at it (see §4a). The proxy is only needed to feed **Claude Code
itself**, which speaks Anthropic.

---

## 2. Local models on an Apple-Silicon Mac

All four runtimes below run natively on M-series and expose an
**OpenAI-compatible** HTTP endpoint, so graphify `--backend openai`
(`OPENAI_BASE_URL=...`) or `--backend ollama` can drive them, and a proxy can put
them behind Claude Code's `ANTHROPIC_BASE_URL`.

| Runtime | Endpoint | Notes |
|---|---|---|
| **Ollama** | `http://localhost:11434/v1` (OpenAI) + native `/api` | **0.19+ (Mar 2026) replaced its engine with Apple MLX on Apple Silicon** — big throughput win (M5 Max Qwen3.5-35B-A3B: decode +93%). Native `format` param takes a **JSON schema** for constrained structured output. graphify has a first-class `--backend ollama` (no key). Easiest path. |
| **LM Studio** | local server, OpenAI drop-in | GUI for browse/download/chat; serves **MLX-optimized** models; "drop-in replacement for OpenAI's API." Good for humans picking models. |
| **MLX / mlx-lm** | `mlx_lm.server` (OpenAI-compatible) | Apple's native framework; "**fastest way to run** [models]… beating llama.cpp by 30–40% on M5." Lowest-level, highest-throughput; more setup. |
| **llama.cpp** | `llama-server` (OpenAI-compatible) | Mature, portable, GGUF; MLX now edges it on Mac but llama.cpp remains the compatibility baseline and graphify lists it explicitly as an `OPENAI_BASE_URL` target. |

Sources: [Ollama MLX blog](https://ollama.com/blog/mlx),
[Ollama structured outputs](https://ollama.com/blog/structured-outputs),
[SitePoint local-LLMs Apple Silicon 2026](https://www.sitepoint.com/local-llms-apple-silicon-mac-2026/),
[gingter.org Ollama-goes-MLX](https://gingter.org/2026/04/23/ollama-goes-mlx/).

**Which models are strong enough?**
- **(a) graphify semantic extraction (structured JSON nodes/edges):** a **Qwen3
  ~7–32B** or **Llama-3.x-8B/70B** instruct model, run with **schema-constrained
  decoding** (Ollama `format: <json-schema>`, or llama.cpp/vLLM grammar). The
  constraint matters more than raw model size here — a 7–14B model with a JSON
  schema reliably emits valid node/edge objects. On a 32–64GB Mac a 32B (4-bit)
  fits; on 16GB stick to 7–8B.
- **(b) code/doc summarization:** **Qwen3-Coder** or **Llama-3.x** at 8–14B is
  ample for file/section summaries; larger (32–70B) only if summary quality
  visibly lags. Apple's own 3B on-device model is explicitly tuned for
  "summarization, classification, structured extraction" — fine for the cheapest
  tier.

**Realistic quality vs Claude:** local 7–14B is clearly weaker on multi-hop
reasoning and long-context synthesis, but for **mechanical extraction and
per-file summarization** (graphify's actual grunt work) the gap is small,
especially with schema constraints. Reserve Claude for the *orchestration* and
the final synthesis/GRAPH_REPORT reasoning, not the per-file passes.

---

## 3. Codex and Google Antigravity as scriptable backends

### OpenAI Codex CLI — scriptable today

`codex exec` is a **headless, non-interactive** mode: prompt in on argv/stdin,
final agent message out on stdout, progress on stderr, then exit — no TUI, no
approval prompt, sandbox-policed (default **read-only**). It's built for CI /
cron / git-hooks / batch loops over many files, and composes in pipes. This is
exactly the shape for "agent grunt work": fan a directory of files through
`codex exec` and collect stdout. Backed by the Codex model family (400K context
in-CLI). Sources: [OpenAI non-interactive-mode docs](https://developers.openai.com/codex/noninteractive),
[codex/docs/exec.md](https://github.com/openai/codex/blob/main/docs/exec.md),
[Developers Digest headless guide](https://www.developersdigest.tech/blog/codex-exec-ci-headless-guide).
This repo already sanctions Codex CLI usage (ai-cli-invocation rule / reference
memory: stdin + `-` flag, `--ephemeral` for research). **Realistically
scriptable: fully.** Cost = ChatGPT/Codex subscription or API; not free, so it's
a *feature reference* for headless agent orchestration, not a free-tier adopt.

### Google Antigravity — mostly GUI, but a headless CLI now exists

Antigravity is Google's agent-first platform: **Antigravity 2.0** is a standalone
desktop IDE for orchestrating parallel agents (GUI), and **Antigravity CLI** is a
terminal surface that shares the same agent harness and supports **headless
execution**. Critically, **Gemini CLI was folded into Antigravity CLI** — as of
**June 18, 2026** the old Gemini CLI / Code Assist paths stopped serving free and
Pro/Ultra requests. So "script Gemini agentically from a terminal" now means
**Antigravity CLI**. Sources:
[Google "transitioning Gemini CLI to Antigravity CLI"](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/),
[Choosing Antigravity or Gemini CLI](https://cloud.google.com/blog/topics/developers-practitioners/choosing-antigravity-or-gemini-cli),
[Build with Antigravity](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/).
**Realistically scriptable:** the CLI is headless-capable; the desktop app is
GUI-only orchestration. For *our* purpose the simpler lever is the **Gemini
Developer API free tier** (§4c) driven straight from graphify `--backend gemini`
— no IDE, no agent harness. Use Antigravity when you want a full agent loop with
Gemini 3's reasoning; use the raw API for cheap bulk extraction.

---

## 4. Pointing graphify's `--backend` at cheap/free extraction

graphify's extractor env-var seam (verified against the PyPI `graphifyy` README /
"LLM Dependencies"):

| Backend | Key env | Base-URL override | Default model | Cost |
|---|---|---|---|---|
| `gemini` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | — | `gemini-3.1-pro-preview` *(version-dependent; older builds defaulted to a flash preview — pin `--model`)* | free tier |
| `openai` | `OPENAI_API_KEY` | **`OPENAI_BASE_URL`** ("any OpenAI-compatible server: llama.cpp, vLLM, LM Studio") | `gpt-4.1-mini` | $0 if base-URL → local/NIM |
| `ollama` | none | `OLLAMA_BASE_URL` (`http://localhost:11434`), `OLLAMA_MODEL`, `GRAPHIFY_OLLAMA_NUM_CTX` | auto-detect | $0, local |
| `claude` | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` (Anthropic-compatible, e.g. LiteLLM proxy / self-hosted NIM) | `claude-sonnet-4-6` | subscription |
| `deepseek` | `DEEPSEEK_API_KEY` | — | — | cheap paid |
| `kimi` | `MOONSHOT_API_KEY` | — | — | cheap paid |

The `OPENAI_BASE_URL` and `ANTHROPIC_BASE_URL` overrides are the whole game: they
turn the `openai`/`claude` backends into pointers at **any** compatible server.

### (a) graphify against a free NIM endpoint — no proxy needed

```bash
export OPENAI_API_KEY="nvapi-YOUR_FREE_KEY"          # from build.nvidia.com
export OPENAI_BASE_URL="https://integrate.api.nvidia.com/v1"
graphify extract ./docs --backend openai --model meta/llama-3.3-70b-instruct
#   (pick an exact model ID from the build.nvidia.com catalog)
```

Cost: **$0** within the **~40 RPM** free limit. Because extraction is per-file
and rate-limited, add a small concurrency cap / retry-with-backoff so a large
corpus doesn't trip 40 RPM (graphify's incremental SHA256 cache already bounds
re-runs to changed files).

### (b) graphify against local Ollama — fully offline, no key, no limit

```bash
ollama pull qwen3:14b        # or a Qwen3-Coder / Llama-3.x tag
graphify extract ./docs --backend ollama --model qwen3:14b
#   OLLAMA_BASE_URL defaults to http://localhost:11434; GRAPHIFY_OLLAMA_NUM_CTX to widen context
```

Cost: **$0**, private, unlimited. Quality slightly below NIM's big models but the
JSON-schema constraint keeps node/edge output valid. **This is the recommended
default** (§ recommendation).

### (c) graphify against Gemini free tier

```bash
export GEMINI_API_KEY="..."      # AI Studio, no card
graphify extract ./docs --backend gemini --model gemini-2.5-flash
```

**Free-tier limits (2026, moving target):** Google **no longer publishes a fixed
universal table** — active quotas are project-specific in AI Studio, and **free
quotas were cut 50–80% on 2025-12-07**. Widely-reported current figures for the
flash tier: **~10 RPM, ~250K TPM, ~250–1,500 RPD** depending on model/account.
**Verify in the AI Studio rate-limit dashboard** before relying on a number.
Sources: [Gemini rate-limits doc](https://ai.google.dev/gemini-api/docs/rate-limits),
[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
[TokenMix free-tier writeup](https://tokenmix.ai/blog/gemini-api-free-tier-limits).
Flash is fast and cheap-to-free and handles structured extraction well; the RPD
cap makes it a **second** choice behind local Ollama for a large corpus.

---

## 5. Cost-control techniques worth *building* (not just buying)

Ordered by ROI for our setup. The recurring theme: put a **seam** between "work"
and "which model does it," then optimize behind the seam.

1. **Provider routing + fallback (BUILD — highest value).** A single
   OpenAI/Anthropic-compatible **gateway** in front of everything, with an
   ordered model list: *local Ollama → free NIM → Gemini free → Claude
   (last-resort)*. On rate-limit / low-confidence, fall through to the next tier.
   **LiteLLM** is the canonical open-source implementation (universal gateway,
   hard budget caps, spend tracking, fallback routing across 100+ providers) and
   speaks **both** OpenAI and Anthropic wire formats — so it simultaneously backs
   graphify `--backend openai` *and* Claude Code's `ANTHROPIC_BASE_URL`. Adopt
   LiteLLM as the seam rather than hand-rolling per-tool env-var juggling.
   ([LiteLLM router guide](https://www.gingerlabs.ai/blog/litellm-router-setup-guide),
   [LLM-router comparison 2026](https://www.developersdigest.tech/blog/llm-router-comparison-2026)).

2. **Cheap-draft-then-strong-verify / confidence-gated escalation (BUILD).**
   Run the cheap tier first; only escalate the *hard* items to Claude.
   **RouteLLM** demonstrates the pattern: route simple queries to cheap models,
   reportedly **~95% of frontier quality at a 75–85% cost cut**. For graphify:
   extract with local/NIM, and have Claude *review only* the low-confidence or
   god-node fragments — not every file. ([RouteLLM / routing evidence](https://wavect.io/blog/reduce-llm-token-costs-2026/)).

3. **Embedding-based dedup before LLM calls (BUILD — cheap, big win).** Before
   sending a doc/section to any model, embed it (local embedding model, ~free)
   and skip near-duplicates / unchanged content. graphify already does SHA256
   incremental caching (exact-match); an embedding pass catches *semantic*
   duplicates the hash misses. This is the single cheapest lever for a corpus
   full of near-identical rule/agent docs like ours.

4. **Semantic caching (ADOPT — GPTCache).** Cache by embedding-similarity so
   "similar" prompts reuse a prior answer; reported **~70% cost reduction on
   high-repetition workloads**. Useful for repeated sub-agent queries; less so
   for one-shot ingestion. ([GPTCache / caching](https://www.finout.io/blog/5-open-source-tools-to-control-your-ai-api-costs-at-the-code-level)).

5. **Prompt/context compression (ADOPT selectively — LLMLingua).** Compress
   verbose context up to ~20× "with minimal performance loss." Worth it when we
   *must* use a paid/frontier model on long context; wasteful on already-free
   local calls. ([LLMLingua](https://wavect.io/blog/reduce-llm-token-costs-2026/)).

6. **Batching (ADOPT where offered).** Provider batch endpoints run ~50% cheaper
   for non-latency-sensitive bulk work — exactly ingestion's profile. Free-tier
   NIM/Gemini batch availability is limited, but the pattern (queue → batch →
   collect) is the right shape for our offline periodic builds.

**Recommended build order** (mirrors the field's consensus "caching → batching →
routing → right-size model → semantic-cache → compress"): the two homegrown
pieces worth owning are the **routing/fallback seam** (LiteLLM, config not code)
and the **embedding dedup + confidence-gated escalation** in front of graphify.
Everything else is adopt-off-the-shelf. ([token-optimization order-of-operations](https://wavect.io/blog/reduce-llm-token-costs-2026/),
[awesome-llm-token-optimization](https://github.com/pleasedodisturb/awesome-llm-token-optimization)).

---

## Concrete recommendation

**For graphify ingestion — start here, in this order:**

1. **Local Ollama (MLX) + `--backend ollama`.** `$0`, private, no rate limit,
   MLX-accelerated on Apple Silicon, first-class graphify support, JSON-schema
   constrained output. This is the default. Model: `qwen3:14b` (or a Qwen3-Coder
   tag for code-heavy corpora); drop to 7–8B on ≤16GB RAM, go 32B (4-bit) on
   ≥32GB.
   ```bash
   ollama pull qwen3:14b
   graphify extract ./docs --backend ollama --model qwen3:14b
   ```
2. **Free NVIDIA NIM via `--backend openai` + `OPENAI_BASE_URL`** as the
   stronger-quality free fallback for hard docs where the local model's
   extraction is thin — `integrate.api.nvidia.com/v1`, free `nvapi-` key,
   ~40 RPM, big open-weight models (Llama-405B / Qwen3-Coder). No proxy needed
   for graphify.
3. **Gemini free tier (`--backend gemini`)** as a third option — verify the
   current AI Studio RPD before a big run (quotas were cut 50–80% in Dec 2025).

**Reserve Claude** for orchestration and final synthesis (the skill's
subagent-driven build, GRAPH_REPORT reasoning) — never for the per-file
extraction passes.

**For agent grunt work / Claude Code sub-agents:** put **LiteLLM** in front as
the routing seam. It backs graphify's OpenAI backend *and* fronts Claude Code via
`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`, with an ordered fallback chain
(local → free NIM → Gemini free → Claude). `codex exec` is the ready-made
headless loop if we want a second scriptable agent for read-only analysis
batches, though it's subscription-priced (feature reference, not a free adopt).

**One config, three consumers:** the `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL`
override is the common seam. Set it once (to LiteLLM, or straight to Ollama/NIM)
and graphify extraction, Claude Code, and any sub-agent all ride the same
cheap/free backend routing without per-tool changes.

**Verification caveats (control-arm discipline):** (1) exact NIM model IDs move —
confirm against the build.nvidia.com catalog before pinning; (2) Gemini free RPD
is project-specific and was recently cut — read the AI Studio dashboard, don't
trust a blog number; (3) graphify's default `gemini` model string differs by
version (task brief said a flash preview; current PyPI README says
`gemini-3.1-pro-preview`) — always pass `--model` explicitly rather than relying
on the default.

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — `codex exec` headless/non-interactive mode for scriptable agent grunt work (docs/exec.md).
- [pleasedodisturb/awesome-llm-token-optimization](https://github.com/pleasedodisturb/awesome-llm-token-optimization) — curated list of LLM cost-reduction tools/techniques (routing, caching, compression, dedup).

*(graphify/`graphifyy`, NVIDIA NIM, LiteLLM, RouteLLM, LLMLingua, GPTCache,
Ollama, LM Studio, MLX referenced via their docs/PyPI/vendor pages rather than
direct GitHub source reads — enumerated here for traceability but not "source
files read".)*
