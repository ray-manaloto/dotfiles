# Agent report (verbatim): codex-nim-research

Persisted from agent transcript `ccb182b4-5d6d-4836-adc9-18361e29fe6d.jsonl` on 2026-07-19.
Captured per `.claude/rules/agent-report-persistence.md` (verbatim, at receipt).

> **NOTE — a FINAL, RICHER version of this report was delivered directly by the
> agent after this transcript capture.** The delivered version adds, beyond what
> is below:
>
> 1. **Source-verified Rust** in `openai/codex`
>    (`codex-rs/model-provider-info/src/lib.rs`): `pub enum WireApi` has
>    **exactly one variant**, `Responses`, plus a
>    `CHAT_WIRE_API_REMOVED_ERROR` const pointing at
>    [discussion 7782](https://github.com/openai/codex/discussions/7782). The
>    same commit removed `LEGACY_OLLAMA_CHAT_PROVIDER_ID` — **which is why our
>    local Ollama success runs over Responses.**
> 2. **A third independent NIM probe** agreeing with ours and with
>    `codex-nim-wiring`: `POST /v1/responses` → 404 byte-identical to a bogus
>    path, while `POST /v1/chat/completions` → 401 and `/v1/embeddings` → 401.
>    NIM serves **chat/completions + embeddings only**.
> 3. **A trap worth flagging:** LiteLLM's `nvidia_nim` docs list `/responses`
>    among supported endpoints. That is **LiteLLM's translation surface, not
>    NIM's native route.** Reading that page as evidence NIM serves Responses
>    would be a false positive.
> 4. **The sharp architectural point:** reaching NIM requires a Responses→chat
>    shim (LiteLLM) in front of it — *"at which point Codex is a pure cost with
>    no benefit over calling NIM's chat endpoint directly."*
> 5. **ToS §4.12 (no competing use):** *"You will not use … the API Service
>    including Generated Content to develop or improve products or services that
>    compete with the API Service."* An autonomous coding-agent orchestrator is
>    arguably adjacent — **UNVERIFIED** whether NVIDIA would read it that way.
> 6. **Interpretive principle for the §2.3 ↔ §3.3(iv) contradiction:** *"When a
>    ToS contradicts itself, assume the clause granting the vendor more rights is
>    operative."*
> 7. **Rate limit is ACCOUNT-level** — `--max-workers 16` will hit 40 RPM;
>    graphify's OpenAI path does 6 SDK retries on 429, so it degrades rather than
>    fails. Credits 1,000 → extendable to 5,000; forum staff cannot grant
>    increases directly.
> 8. **graphify escape hatch** for the `max_completion_tokens` vs `max_tokens`
>    risk: `.graphify/providers.json` supports `extra_body` behind
>    `GRAPHIFY_ALLOW_LOCAL_PROVIDERS=1`.
>
> Its corrected framing, which supersedes the "irrelevant" wording below:
> **"Codex is a viable wrapper only for Responses-capable endpoints
> (Ollama ✅, NIM ❌), and `codex-plugin-cc` is separately irrelevant because it
> cannot change Claude's model."**

---

Findings recorded. Full report below.

# NVIDIA NIM as a Free Worker Backend — Research Report

**Date:** 2026-07-19 · **Bottom line up front:** `codex-plugin-cc` is **the wrong direction entirely** and does not help. NVIDIA NIM *is* a genuine free OpenAI-compatible endpoint and *does* work with graphify today (issue #959 is stale — support shipped in 0.8.40). But NVIDIA's **Trial ToS forbids production use and claims the right to train on your inputs**, which disqualifies it for ingesting this repo's corpus. The research also produced a hard architectural finding that **confirms the launcher-wrapped shell-out substrate decision**.

---

## 1. `openai/codex-plugin-cc` — routes the OPPOSITE way

**Verdict: irrelevant to this problem. Do not adopt it for worker models.**

| Fact | Value | Source |
|---|---|---|
| Description | "Use Codex from Claude Code to review code or delegate tasks." | [GitHub API](https://github.com/openai/codex-plugin-cc) |
| Stars / forks | 29,331 / 1,861 | GitHub API, 2026-07-19 |
| Open issues | 356 | GitHub API |
| Last push | 2026-07-08 | GitHub API |
| License / owner | Apache-2.0, **official `openai` org** | GitHub API |

**Direction (this is the crux):** it is a **Claude Code plugin that delegates work FROM Claude Code TO OpenAI's Codex**. It is *not* a mechanism for Claude Code to call arbitrary OpenAI-compatible models.

**Architecture** — plugin manifest, not MCP, not a proxy. The tree at [`plugins/codex/`](https://github.com/openai/codex-plugin-cc/tree/main/plugins/codex) is a standard CC plugin: `.claude-plugin/plugin.json`, `commands/*.md` (`/codex:review`, `/codex:rescue`, `/codex:transfer`…), `hooks/hooks.json`, and `scripts/lib/app-server.mjs`. The README is explicit:

> "**Does the plugin use a separate Codex runtime?** No. This plugin delegates through your local Codex CLI and Codex app server on the same machine… it uses the same local authentication state."

**Can it be pointed at build.nvidia.com?** Technically the README says:

> "If you need to point the built-in OpenAI provider at a different endpoint, set `openai_base_url` in your Codex config."

But per [Codex's own config docs](https://learn.chatgpt.com/docs/config-file/config-advanced), `openai_base_url` **"only adjusts the built-in provider"**, and non-OpenAI services are supposed to use a separate `[model_providers.<id>]` block with `base_url` / `env_key` / `wire_api`. So the *supported* route to NIM would be a Codex custom provider — which means **you'd be using Codex, not Claude Code, as the worker**, and paying an extra process hop for nothing. `codex-plugin-cc` adds no value on that path.

**Conclusion:** codex-plugin-cc changes nothing about the substrate decision. Its requirement is literally *"ChatGPT subscription or OpenAI API key"* — it is a Codex-delegation UX, not a model-routing layer.

---

## 2. NVIDIA build.nvidia.com / NIM as a free OpenAI-compatible endpoint

### 2.1 Endpoint and compatibility — CONFIRMED by direct probe

- **Base URL:** `https://integrate.api.nvidia.com/v1`, endpoint `POST /v1/chat/completions` — [docs.api.nvidia.com](https://docs.api.nvidia.com/nim/reference/llm-apis). Confirmed OpenAI chat-completions compatible.
- **Auth:** `Authorization: Bearer nvapi-…` key from [build.nvidia.com](https://build.nvidia.com/). I probed unauthenticated and got the exact error `Header of type 'authorization' was missing`, `http=401`.
- **`/v1/models` is publicly listable with NO auth.** My probe returned `http=200` and **119 models**. *Control arm:* a bogus path (`/v1/definitely-not-a-real-endpoint`) returned `404`, so the probe discriminates — the 200 is real, not a catch-all.
- LiteLLM ships a first-class provider: default base `https://integrate.api.nvidia.com/v1/`, env `NVIDIA_NIM_API_KEY` / `NVIDIA_NIM_API_BASE`, model prefix `nvidia_nim/<model>` — [LiteLLM docs](https://docs.litellm.ai/docs/providers/nvidia_nim).

### 2.2 Free-tier limits

| Limit | Value | Confidence |
|---|---|---|
| Default rate limit | **40 requests/minute** | NVIDIA staff confirm on the [developer forum](https://forums.developer.nvidia.com/t/api-rate-limit-increase-for-nvidia-nim/366043); **no formal docs page exists** |
| Default credits | **1,000**, extendable to **5,000** on request | Inferred from the *volume* of NVIDIA-hosted forum threads titled literally ["1,000 → 5,000 credits, 40 → 200 RPM"](https://forums.developer.nvidia.com/t/api-access-confirmation-credit-rate-limit-increase-request-1-000-5-000-credits-40-200-rpm/375201) |
| Increase process | Cannot be approved via forum; escalated internally | Staff quote: *"I can elevate this internally… but we cannot approve rate-limit increases directly from the forum."* |
| Credits per request | Varies by model size | ToS §1.4 confirms a credit-deduction model exists but names no rates |

**UNVERIFIED:** I could find **no official NVIDIA documentation page** stating 40 RPM or the credit allocation. `docs.api.nvidia.com/nim/docs/product` does **not** mention credits, rate limits, or key format. Treat these numbers as staff/community-corroborated, not an SLA. Also note the secondary claim that "credit limits have been removed" ([pasqualepillitteri.it](https://pasqualepillitteri.it/en/news/1621/nvidia-build-free-api-100-ai-models-2026)) **conflicts** with the active forum threads still requesting credit increases — I could not resolve which is current.

### 2.3 Available models — VERIFIED against the live catalog

⚠️ **Your brief's guesses were wrong.** `qwen2.5-coder`, `deepseek-v3`, and `qwen3-coder` are **NOT in the catalog**. Real IDs, pulled from the live `/v1/models` response:

**Best for coding / agentic work:**
| Model ID | Note |
|---|---|
| `qwen/qwen3.5-397b-a17b` | Large MoE, strongest open coder present |
| `deepseek-ai/deepseek-v4-pro` | DeepSeek's current flagship |
| `deepseek-ai/deepseek-v4-flash` | Faster/cheaper; graphify has a `#1621` thinking-disable note for exactly this model |
| `moonshotai/kimi-k2.6` | Reasoning model |
| `z-ai/glm-5.2` | GLM family (the claudefa.st article uses GLM) |
| `openai/gpt-oss-120b` / `gpt-oss-20b` | Open-weight GPT |

**Best for cheap structured extraction (graphify's actual need):**
| Model ID | Note |
|---|---|
| `nvidia/nemotron-3-super-120b-a12b` | MoE, ~12B active — good quality/throughput |
| `nvidia/nemotron-3-nano-30b-a3b` | ~3B active — very fast, ideal for bulk chunk extraction |
| `qwen/qwen3-next-80b-a3b-instruct` | 3B active, 80B total |
| `meta/llama-3.3-70b-instruct` | Safe baseline |

Legacy/weak, avoid: `deepseek-ai/deepseek-coder-6.7b-instruct`, `meta/codellama-70b`, `bigcode/starcoder2-15b`, `mistralai/codestral-22b-instruct-v0.1`.

### 2.4 Reliability caveats for sustained batch use

- 40 RPM is an **account-level** cap. For graphify ingest this is *usually fine* — chunk extraction is slow per-call — but a `--max-workers 16` fan-out will hit it. Graphify's OpenAI SDK path defaults to 6 retries on 429 (`_resolve_max_retries`), so it degrades rather than fails.
- The **credit cap is the real wall**: a large-corpus ingest can exhaust 1,000–5,000 credits in a single run, and there is no graceful behavior documented for exhaustion.
- ToS §1.3 warns endpoints may be **pre-release** with *"reduced or different security, privacy, availability, and reliability standards"* and may be terminated *"at any time without liability."*

---

## 3. The claudefa.st article

[claudefa.st/blog/tools/customization/free-claude-code](https://claudefa.st/blog/tools/customization/free-claude-code) describes a **local Anthropic-protocol shim**, not a plugin. Its thesis: *"Claude Code speaks the Anthropic Messages API protocol. So does any proxy that pretends to be Anthropic."*

**Recipe:**
1. Install `uv` + Python 3.14; clone the project; copy `.env.example` → `.env`.
2. Set provider creds — for NVIDIA: `NVIDIA_NIM_API_KEY="nvapi-…"`, `MODEL="nvidia_nim/z-ai/glm4.7"` (LiteLLM prefix form).
3. Run a FastAPI translation server: `uv run uvicorn server:app --host 0.0.0.0 --port 8082`.
4. Launch CC redirected at it:
   ```bash
   ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude
   ```
5. Optional per-tier routing: `MODEL_OPUS`, `MODEL_SONNET`, `MODEL_HAIKU`.

**Gotchas it names:** tool-use reliability degrades on weaker models; context shrinks to 32K–128K vs 200K+; quality is *"70 to 85 percent of the result"* at 2–5% of cost.

**Gotcha it does NOT name (and this is the important one):** `ANTHROPIC_BASE_URL` is **process-global**. Redirecting it sends *every* request in that session — architect, subagents, compaction, title generation — to the proxy. It is all-or-nothing.

---

## 4. Synthesis

### 4.1 Can NIM be a Claude Code *worker* model? — Only via a whole-process swap

**The decisive finding: CC's subagent `model:` field cannot name a non-Claude model.** Per [the official subagents doc](https://code.claude.com/docs/en/sub-agents), `model` accepts:

> `sonnet`, `opus`, `haiku`, `fable`, a full model ID (for example, `claude-opus-4-8`), or `inherit`… **Accepts the same values as the `--model` flag**

There is no base-URL or provider field on a subagent. **Integration surface (A) is closed.** Combined with `ANTHROPIC_BASE_URL` being process-global, it is **architecturally impossible to run a Fable/Opus architect and NIM workers inside one Claude Code process.**

And Anthropic states plainly ([llm-gateway docs](https://code.claude.com/docs/en/llm-gateway)):

> "Anthropic doesn't endorse, maintain, or audit third-party gateway products, and **doesn't support routing Claude Code to non-Claude models through any gateway**."

**Ranked mechanisms:**

| Rank | Mechanism | Verdict |
|---|---|---|
| **1** | **Bash shell-out** to a NIM-backed CLI from the architect session | ✅ Only option preserving a Claude architect + NIM workers concurrently. Per-call model choice; no global state. **Confirms your existing lean.** |
| 2 | Separate CC process with `ANTHROPIC_BASE_URL` → LiteLLM/free-claude-code | ⚠️ Works, but that whole process is non-Claude. Viable as a *detached worker pool*, never for the architect. |
| 3 | `claude-code-router` | ⚠️ Same class as #2, more setup, unsupported by Anthropic. |
| 4 | `codex-plugin-cc` | ❌ Wrong direction. Delegates CC→Codex. Adds nothing. |
| 5 | Subagent `model:` field | ❌ **Impossible.** Claude model IDs only. |

**Minimal concrete setup (option 1):** no proxy at all — call NIM's OpenAI endpoint directly from a worker script, since NIM *is* OpenAI-compatible:
```bash
export NVIDIA_API_KEY="nvapi-…"
# worker invocation, per-call model choice
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1 \
OPENAI_API_KEY="$NVIDIA_API_KEY" \
  <your-worker-cli> --model qwen/qwen3.5-397b-a17b
```
The LiteLLM/FastAPI shim is only needed if you want an *Anthropic-protocol* surface, which shell-out does not.

### 4.2 graphify — issue #959 is STALE; support already shipped

**Your brief's premise needs correcting.** [Issue #959](https://github.com/Graphify-Labs/graphify/issues/959) is **still open with 0 comments** since 2026-05-21, and its body claims the OpenAI base URL is *"hardcoded"*. **That is no longer true.** I verified against source:

- `CHANGELOG.md` **0.8.40 (2026-06-16)**: *"Feat: custom OpenAI- and Anthropic-compatible endpoints via `OPENAI_BASE_URL`/`OPENAI_MODEL`… Point either backend at a self-hosted or proxy server (vLLM, llama.cpp, LM Studio, LiteLLM, gateways) (#1273)."*
- `graphify/llm.py:112-115`: `"base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")`, `"default_model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")`.
- Tests exist: `tests/test_openai_custom_endpoint.py`.
- **We run graphify 0.9.20** (verified locally), well past 0.8.40. **It works today.**

**Exact invocation:**
```bash
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1 \
OPENAI_API_KEY="nvapi-…" \
OPENAI_MODEL=nvidia/nemotron-3-super-120b-a12b \
  graphify extract ./docs --backend openai --token-budget 30000
```
Model pick: `nvidia/nemotron-3-super-120b-a12b` (MoE, ~12B active — quality at throughput) or `nvidia/nemotron-3-nano-30b-a3b` for max speed. `--token-budget 30000` because graphify's README explicitly recommends smaller chunks for non-frontier models.

**⚠️ CONCRETE COMPATIBILITY RISK — must probe before adopting.** `graphify/llm.py:1123` sends **`max_completion_tokens`** in every request. NVIDIA's [endpoint reference](https://docs.api.nvidia.com/nim/reference/meta-llama-3_3-70b-instruct-infer) documents **`max_tokens`**, `temperature`, and `tools` — **`max_completion_tokens` is not listed**. If NIM rejects the unknown key you get an HTTP 400 on every call. I could **not verify this** — the unauthenticated probe 401s before parameter validation, so this is **UNVERIFIED** and needs a single live call with a real key as the first adoption step.

Two supporting notes: graphify does **not** use `response_format`/JSON-schema on this path (it parses JSON from text), so structured-output support is not a blocker. And graphify has a `.graphify/providers.json` custom-provider mechanism with an `extra_body` escape hatch, gated behind `GRAPHIFY_ALLOW_LOCAL_PROVIDERS=1` — useful if NIM needs request-shape tweaks.

### 4.3 Risks — the ToS is the actual blocker

I extracted the [NVIDIA API Trial Terms of Service](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf) PDF and read it verbatim. Three clauses matter:

**§1.2 / §1.4 — trial and evaluation only, NOT production:**
> "NVIDIA will provide you access to the API Service for **limited trial purposes only and without use of the API Service or Generated Content in production**."
> "Unless you purchase a Subscription… you may only use the API Service for **internal testing and evaluation purposes, not in production**."

An autonomous orchestrator doing bulk work on your real repo is, at minimum, an aggressive reading of "internal testing and evaluation." Programmatic use per se is not banned (the only automation clause, §4.6, targets spam), but **sustained production workloads are.**

**§3.3(iv) — NVIDIA trains on your inputs and outputs:**
> "NVIDIA will collect the following data… (iv) **User Content and Generated Content to improve NVIDIA products and services, including AI models.**"

Note this **directly contradicts §2.3** (*"NVIDIA will not store or use User Content or Generated Content at the end of each API Service session"*) and contradicts the NVIDIA staff reassurance on the [privacy forum thread](https://forums.developer.nvidia.com/t/clarification-on-trial-api-use/334275) that content is used *"solely to provide users with the API Service."* **When a ToS contradicts itself, assume the clause that grants the vendor more rights is the operative one.** For a graphify ingest — which by design ships your **entire source corpus** to the endpoint — this is disqualifying.

**§4.12 — no competing use:**
> "You will not use (or allow others to use) the API Service including Generated Content to develop or improve products or services that compete with the API Service."

Reliability: pre-release quality bar, terminable "at any time without liability" (§1.3).

### 4.4 Bottom line — ranked

**(a) Claude Code worker models:**
1. **Local Ollama via shell-out** — no ToS risk, no rate limit, no corpus egress, works offline. Default.
2. **NIM via shell-out** — reach for *specific* large models (`qwen3.5-397b`, `deepseek-v4-pro`) that don't fit on this Mac, on non-sensitive tasks only, within evaluation framing.
3. **NIM via `ANTHROPIC_BASE_URL` proxy** — only for a detached, disposable worker process. Never the architect.
4. **codex-plugin-cc** — not applicable.

**(b) graphify ingestion backend:**
1. **Local Ollama** (`--backend ollama`) — **clear winner.** graphify's most-tuned path (`num_ctx` auto-derive, `keep_alive`, retry tuning, `#798`/`#1686` fixes all target Ollama). Your corpus never leaves the machine. No credits, no 40 RPM, no §3.3(iv).
2. **NIM** — viable *technically*, but §3.3(iv) means ingesting this repo hands NVIDIA training rights over your entire source tree. **Do not use it on the dotfiles corpus.** Acceptable only for throwaway/public-code capability probes.

**Is NIM worth adopting over local Ollama? No — not as a default.** The technology is sound and free; the *licence* is the problem. Adopt it as an **on-demand capability probe** (a mise task that requires an explicit opt-in flag), never as the standing ingestion or worker backend.

**Highest-value corrections to your priors:**
1. `codex-plugin-cc` routes CC→Codex — it can never be the worker-model substrate.
2. Subagent `model:` is Claude-only ⇒ **mixed architect/worker models in one process is impossible** ⇒ **shell-out is not merely preferable, it is the only design that works.**
3. graphify #959 is stale — `OPENAI_BASE_URL` shipped in 0.8.40; no upstream work is blocking you.
4. `qwen2.5-coder` / `deepseek-v3` aren't on NIM; use the verified IDs above.

---

## GitHub repos touched

- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — primary subject; read README, file tree, and repo metadata to establish delegation direction and maturity.
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — read issue #959, `graphify/llm.py`, `CHANGELOG.md`, `README.md` to verify `OPENAI_BASE_URL` support and find the `max_completion_tokens` compatibility risk.
- [BerriAI/litellm](https://github.com/BerriAI/litellm) — consulted its `nvidia_nim` provider docs for base URL, env vars, and model-prefix format.
