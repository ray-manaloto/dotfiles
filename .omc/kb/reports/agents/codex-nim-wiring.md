# Agent report (verbatim): codex-nim-wiring

Persisted from agent transcript `9d872796-45c8-4f91-9add-8e8cab52b8dc.jsonl` on 2026-07-19.
Captured per `.claude/rules/agent-report-persistence.md` (verbatim, at receipt).

---

Both of your findings are **corroborated, not contradicted**. Full report follows verbatim, with a reconciliation section added at the front.

---

# Can OpenAI Codex CLI be pointed at NVIDIA NIM (or any third-party OpenAI-compatible endpoint)?

## VERDICT

**Any third-party OpenAI-compatible endpoint: YES — provided it implements `/v1/responses`.** The protocol requirement is real but satisfiable by non-OpenAI servers; Ollama is the existence proof.

**NVIDIA NIM specifically:**
- **Hosted (`https://integrate.api.nvidia.com/v1`): NO.** It does not implement `/v1/responses`. Verified first-hand today with control arms, and reproduced end-to-end through `codex exec`.
- **Self-hosted NIM container ≥ 1.14.0: MAYBE** — NVIDIA documents an *experimental* `/v1/responses`, gpt-oss models only, with a documented memory leak. **UNVERIFIED** whether Codex actually drives it.
- **Via a translating proxy (LiteLLM): YES-WITH-CAVEATS.** This is the only path with vendor-acknowledged support.

---

## 0. Reconciliation against your local findings

**No disagreement on either point.** Both are independently confirmed by my research, and your #2 is the more important of the two — it converts my structural argument into a demonstrated one.

### Your finding 1 — `wire_api = "chat"` string compiled into 0.144.6 → Responses-only

**CONFIRMED, and I can name the source line and the commit.** From [`codex-rs/model-provider-info/src/lib.rs`](https://github.com/openai/codex/blob/main/codex-rs/model-provider-info/src/lib.rs):

```rust
const CHAT_WIRE_API_REMOVED_ERROR: &str = "`wire_api = \"chat\"` is no longer supported.\n\
How to fix: set `wire_api = \"responses\"` in your provider config.\n\
More info: https://github.com/openai/codex/discussions/7782";
```

That is the exact literal you found in the binary. I also reproduced it at runtime on the same 0.144.6 build (sandboxed via `CODEX_HOME`, your `~/.codex` untouched):

```
rc=1
Error loading config.toml: `wire_api = "chat"` is no longer supported.
How to fix: set `wire_api = "responses"` in your provider config.
More info: https://github.com/openai/codex/discussions/7782
in `model_providers.nvidia_nim.wire_api`
```

The enum has exactly one variant — this is not a soft deprecation:

```rust
pub enum WireApi {
    /// The Responses API exposed by OpenAI at `/v1/responses`.
    Responses,          // <-- the ONLY variant
}
// Deserialize:
"responses" => Ok(Self::Responses),
"chat"      => Err(serde::de::Error::custom(CHAT_WIRE_API_REMOVED_ERROR)),
_           => Err(serde::de::Error::unknown_variant(&value, &["responses"])),
```

A second legacy ID was killed in the same sweep: `ollama-chat` → `OLLAMA_CHAT_PROVIDER_REMOVED_ERROR`.

### Your finding 2 — `codex exec` with `model_provider = "ollama"` drives local Ollama, rc=0

**CONFIRMED, and I can supply the upstream provenance you'd want for the writeup.** Your `ollama ps` keep-alive-refresh + absent-`auth.json` verification is a well-armed probe — it discriminates "Codex actually drove the local server" from "Codex silently fell back to OpenAI," which is the failure mode that would have made a naive rc=0 meaningless.

Upstream facts that back it:
- **Ollama added `/v1/responses` in v0.13.3**, via [ollama/ollama#13351](https://github.com/ollama/ollama/pull/13351). The feature was requested in [#10309, "Support for OpenAI Responses API (for Codex CLI compatibility)"](https://github.com/ollama/ollama/issues/10309) — Codex compatibility was the *stated motivation*. Docs/changelog gap logged at [#13595](https://github.com/ollama/ollama/issues/13595): v0.13.3/0.13.4/0.13.5 release notes never mention it.
- Codex's built-in table was migrated to match, in [#8798 `ollama: default to Responses API for built-ins`](https://github.com/openai/codex/pull/8798) (2026-01-13) — *before* chat was dropped (2026-02-03). The ordering matters: OpenAI staged the ecosystem migration first, then cut.

```rust
(OLLAMA_OSS_PROVIDER_ID,   create_oss_provider(DEFAULT_OLLAMA_PORT,   WireApi::Responses)),
(LMSTUDIO_OSS_PROVIDER_ID, create_oss_provider(DEFAULT_LMSTUDIO_PORT, WireApi::Responses)),
```

**One caveat on your rc=0 result worth carrying forward:** Ollama's implementation is **non-stateful** — no `previous_response_id`, no conversation support. A short `codex exec` run won't exercise that; longer multi-turn sessions may. Flagging so the success isn't over-generalized.

**Your narrowing is correct.** "Codex is locked to OpenAI" is false — it's locked to a *protocol*, and that protocol is implementable by anyone. The question really is just: does NIM implement it? Answered in §2.

---

## 1. The `wire_api` contradiction in the docs, resolved

The answer is **(b) + (d) simultaneously** — chat *was* supported and *was* removed, **and** Ollama/LM Studio *have since* implemented `/v1/responses`. The docs are correct and current; they simply don't tell you the history. Possibility (c) — special-casing for built-ins — is **false**; there is no such code path.

### Timeline (from openai/codex git history — primary source)

| Date | Commit / PR | What happened |
|---|---|---|
| 2025-05-08 | `e924070c` — [#862](https://github.com/openai/codex/pull/862) | `feat: support the chat completions API in the Rust CLI` — chat support **added** |
| 2025-12-09 | [Discussion #7782](https://github.com/openai/codex/discussions/7782) | Deprecation **announced** by maintainer `@etraut-openai`: *"Maintaining compatibility with this legacy protocol has added complexity, introduced regressions, and increased support overhead."* |
| 2025-12-11 | `43e6e753` — [#7897](https://github.com/openai/codex/pull/7897) | Deprecation **warning** added for `wire_api = "chat"` |
| 2026-01-13 | `fe033207` — [#8798](https://github.com/openai/codex/pull/8798) | `ollama: default to Responses API for built-ins` |
| **2026-02-03** | **`88598b94` — [#10498](https://github.com/openai/codex/pull/10498)** | **`feat: drop wire_api from clients` — chat support REMOVED** |

Full removal landed in the **0.84.0+** era per the discussion thread; commit `88598b94` (merged 2026-02-03) is the code-level cut.

### Reserved provider IDs — a trap worth documenting

Built-in IDs `openai`, `ollama`, `lmstudio`, and `amazon-bedrock` (added 2026-04-21, [#18744](https://github.com/openai/codex/pull/18744)) are **reserved**. `merge_configured_model_providers` uses `.or_insert()`, so a user-defined provider reusing a built-in ID is **silently ignored** — no error, no warning. You cannot reach a third party by overriding the `openai` provider's `base_url`; you must define a new ID.

The design intent is stated in the source comment:

> *"We do not want to be in the business of adjudicating which third-party providers are bundled with Codex CLI, so we only include the OpenAI and open source ("oss") providers by default. Users are encouraged to add to `model_providers` in config.toml to add their own providers."*

---

## 2. **Does NVIDIA NIM implement a working `/v1/responses`?** — the highest-value section

### Hosted API: **NO.** Probed live 2026-07-19, with both control arms

A bare 404 proves nothing, so I armed the probe in both directions:

| Request | Result | Reads as |
|---|---|---|
| `GET /v1/models` | **200** + full model list | host reachable, API live ✅ |
| `POST /v1/chat/completions` (no auth) | **401** | route **exists**, auth enforced ✅ |
| `POST /v1/chat/completions` (bogus key) | **403** `{"title":"Forbidden","detail":"Authorization failed"}` | route exists ✅ |
| **`POST /v1/responses`** (no auth) | **404** `page not found` | **route does not exist** ❌ |
| **`POST /v1/responses`** (bogus key) | **404** `page not found` | not an auth failure ❌ |
| `POST /v1/definitely_not_an_endpoint` (negative control) | **404** `page not found` | **byte-identical to `/v1/responses`** |

The negative control is the load-bearing part: `/v1/responses` is indistinguishable from a route NVIDIA never defined, while `/chat/completions` clearly discriminates (401/403, not 404). The bogus-key arm rules out "404 as an auth-masking response."

> **One anomaly, reported honestly:** `GET /v1/responses` returns **405**, as does `GET /v1/chat/completions`, while `GET /v1/definitely_not_an_endpoint` returns 404. So the *edge gateway* appears to know the path string, but a POST forwards to a backend with no handler. Net effect is unchanged and confirmed end-to-end below — but I flag **UNVERIFIED** why the edge behaves this way. It may indicate NVIDIA has provisioned the route at the edge ahead of backend rollout, which would make this a moving target worth re-probing later.

### End-to-end confirmation through the real binary

Same 0.144.6, `CODEX_HOME`-sandboxed, custom provider pointed straight at hosted NIM with `wire_api = "responses"`:

```
OpenAI Codex v0.144.6
model: meta/llama-3.1-8b-instruct
provider: nvidia_nim
warning: Model metadata for `meta/llama-3.1-8b-instruct` not found.
         Defaulting to fallback metadata; this can degrade performance and cause issues.
ERROR: Reconnecting... 1/5 … 5/5
ERROR: unexpected status 404 Not Found: 404 page not found,
       url: https://integrate.api.nvidia.com/v1/responses
```

Note what this proves **positively**, and why it complements your Ollama result: the custom-provider plumbing works flawlessly — config parsed, provider selected, correct URL constructed, auth header attached, retries performed. Your finding 2 shows the same machinery succeeding against a compliant server. **Only NVIDIA's missing endpoint fails.** Two probes, opposite outcomes, same code path — that pair isolates the defect to NVIDIA, not Codex.

### Independent corroboration — someone else's POC, four months earlier

[`SproutSeeds/codex-nim-poc`](https://github.com/SproutSeeds/codex-nim-poc) ran the identical experiment on **2026-03-25**. From [`docs/first-live-run-2026-03-25.md`](https://github.com/SproutSeeds/codex-nim-poc/blob/main/docs/first-live-run-2026-03-25.md), verbatim:

```
- direct `GET https://integrate.api.nvidia.com/v1/models`: `200`
- direct `POST https://integrate.api.nvidia.com/v1/responses`: `404 page not found`
- second direct POST check with `nvidia/llama-3.3-nemotron-super-49b-v1`: `404 page not found`
- `codex exec` through a custom provider configured for
  `https://integrate.api.nvidia.com/v1` and `wire_api = "responses"`:
  repeated `404 Not Found` against `/v1/responses`
- manual fallback `POST /v1/chat/completions` with `nvidia/nemotron-3-super-120b-a12b`: `200`
```

Their stated read:

> *"NVIDIA hosted NIM on `integrate.api.nvidia.com/v1` is usable through `chat/completions`; this endpoint currently does not expose a working `/v1/responses` path for the tested model/provider path; Codex therefore fails at the Responses boundary before any provider-specific `extra_body` primitive can help direct integration."*

Two probes, four months apart, different operators, different models tested, same answer.

### A second-order gap even if NVIDIA ships the endpoint

The same POC found that NVIDIA Nemotron models require `extra_body.chat_template_kwargs.force_nonempty_content = true` — without it, `message.content` comes back **null** with only reasoning fields populated; with it, content is non-null. **Codex exposes no provider-level request-body injection** (tracked at [openai/codex#5458](https://github.com/openai/codex/issues/5458)). So even if `/v1/responses` appeared tomorrow, Nemotron-via-Codex would likely still need a Codex-side primitive.

### Self-hosted NIM container: experimental, and caveat-heavy

[NIM for LLMs 1.14.0 release notes](https://docs.nvidia.com/nim/large-language-models/1.14.0/release-notes.html):

- *"The Responses API is experimental. The `/v1/responses` (POST) endpoint immediately returns the complete response."*
- Scoped to **GPT-OSS-20B / GPT-OSS-120B only** in the notes
- GET-retrieval and cancel require `VLLM_ENABLE_RESPONSES_API_STORE=1`, which *"causes a memory leak because responses are not automatically cleaned up"*
- *"Stored responses are not persisted to disk, so all stored data is lost on server restart"*
- Cancel only works for `"background": true`; immediate responses can't be cancelled
- *"When passing the payload using the Responses API, background fill is disabled"*

This is a self-hosted-container capability, **not** available on `integrate.api.nvidia.com`. **UNVERIFIED** whether Codex successfully drives it — I found no report of anyone running Codex against a self-hosted NIM 1.14+ container. This is the single most valuable open experiment if you have GPU access.

### Community attempts and OpenAI's position

- **[openai/codex#19145 "Integrate NVIDIA NIM as an Inference Provider"](https://github.com/openai/codex/issues/19145)** (opened 2026-04-23) — **CLOSED AS NOT PLANNED.** No maintainer discussion of `/v1/responses` in-thread. Consistent with the "not adjudicating third-party providers" comment in the source — policy, not oversight.
- **[Discussion #23156 "Community Codex v1 with NVIDIA NIM Integration"](https://github.com/openai/codex/discussions/23156)** (2026-05-17) — a **fork**, [`HackWidMaddy/OpenCodex`](https://github.com/HackWidMaddy/OpenCodex), by the same author whose feature request was rejected. Author's words: *"Version 1 is already integrated with NVIDIA NIM, which honestly I'm not sure why OpenAI wasn't doing 😭"*. **10 stars.** Working status **UNVERIFIED** — and a 10★ fork of a repo moving at openai/codex's pace is a maintenance liability regardless.
- **[Prince Arora, "Run Codex CLI Free with NVIDIA NIM" (Medium, 2026-05-11)](https://prince-arora-aws.medium.com/run-codex-cli-free-with-nvidia-nim-c8392f24243c)** — uses LiteLLM on `localhost:4000`, explicitly warns *"`base_url` must point to LiteLLM on `localhost:4000`"* / direct NVIDIA connections fail. **Caveat: no execution logs or screenshots** — a guide, not a demonstrated run.
- Third-party breakage reports consistent with the above: [RightNow-AI/openfang#471](https://github.com/RightNow-AI/openfang/issues/471) (NVIDIA custom provider 401s), [Hmbown/CodeWhale#1081](https://github.com/Hmbown/CodeWhale/issues/1081) ("nvidia-nim provider can not works").

**Direct answer to your narrowed question: NVIDIA's hosted API does not implement `/v1/responses`. Self-hosted ≥1.14.0 does, experimentally and partially. Nobody has published a working direct Codex↔NIM config, and the one serious POC concluded it is impossible today.**

---

## 3. The path that works: LiteLLM bridge

**LiteLLM explicitly names Codex CLI as the motivating use case** ([docs.litellm.ai/docs/response_api](https://docs.litellm.ai/docs/response_api)):

> *"This is particularly useful when connecting clients that hardcode the `/responses` endpoint (e.g. **OpenAI Codex CLI**) to local or third-party OpenAI-compatible providers that only expose `/chat/completions`."*

Bridge history: [#11632](https://github.com/BerriAI/litellm/pull/11632) added it, [#11685](https://github.com/BerriAI/litellm/pull/11685) improved it, [#23716](https://github.com/BerriAI/litellm/issues/23716) and [#13130](https://github.com/BerriAI/litellm/issues/13130) track opt-in for custom `api_base` providers.

**`litellm_config.yaml`:**
```yaml
model_list:
  - model_name: nim-nemotron
    litellm_params:
      model: openai/nvidia/llama-3.3-nemotron-super-49b-v1
      api_base: https://integrate.api.nvidia.com/v1
      api_key: os.environ/NVIDIA_API_KEY
      use_chat_completions_api: true      # <-- the /responses -> /chat/completions bridge
```
```bash
export NVIDIA_API_KEY=nvapi-...
litellm --config litellm_config.yaml --port 4000
```

**`~/.codex/config.toml`:**
```toml
#:schema https://developers.openai.com/codex/config-schema.json

model = "nim-nemotron"            # must match model_name in litellm_config.yaml
model_provider = "nvidia_nim"

[model_providers.nvidia_nim]
name = "NVIDIA NIM via LiteLLM"
base_url = "http://localhost:4000/v1"   # LiteLLM, NOT integrate.api.nvidia.com
env_key = "LITELLM_MASTER_KEY"          # or any dummy key var; env_key must be set
wire_api = "responses"                  # the only legal value
supports_websockets = false
request_max_retries = 2
stream_max_retries = 4
stream_idle_timeout_ms = 600000
```

Invoke: `codex`, or `codex --profile <name>`, or per-invocation `codex -c model_provider="nvidia_nim"`.

**Direct-to-NIM version — DOES NOT WORK, shown for contrast.** This is [`codex-nim-poc/configs/codex.nvidia-nim.example.toml`](https://github.com/SproutSeeds/codex-nim-poc/blob/main/configs/codex.nvidia-nim.example.toml), and it 404s:
```toml
base_url = "https://integrate.api.nvidia.com/v1"   # <-- 404 at /v1/responses
```

**Evidence class for the LiteLLM chain: "read in docs + a blog", NOT "I ran it."** No `NVIDIA_API_KEY` in this environment. What *is* verified: the bridge key is in LiteLLM's official docs with Codex named; and the Codex half of the chain provably works (both my 404-at-the-right-URL result and your Ollama rc=0 confirm the plumbing).

---

## 4. Real projects pointing Codex at other backends

| Backend | Status | Source |
|---|---|---|
| **Ollama** | ✅ **Built-in provider, works** — your rc=0 + upstream v0.13.3 | [Ollama Codex docs](https://docs.ollama.com/integrations/codex) — recommends ≥64k context window for Codex |
| **LM Studio** | ✅ Built-in provider (port 1234), `WireApi::Responses` | codex source `built_in_model_providers()` |
| **OpenRouter** | ✅ Documented by the vendor | [OpenRouter Codex CLI cookbook](https://openrouter.ai/docs/cookbook/coding-agents/codex-cli), [OpenRouter blog tutorial](https://openrouter.ai/blog/tutorials/codex-cli-openrouter/) — must define a new `openrouter` provider ID; cannot override built-in `openai` |
| **vLLM** | ⚠️ Mixed — "production path" per guides, but vLLM 15.1 reported non-functional on responses at the Feb cutover | [knightli.com local-LLM guide](https://knightli.com/en/2026/07/11/use-local-llm-api-with-codex-ollama-lm-studio-vllm/); [Discussion #7782](https://github.com/openai/codex/discussions/7782) |
| **llama.cpp** | ⚠️ Partial — newer versions convert responses back to chat completions internally | [Discussion #7782](https://github.com/openai/codex/discussions/7782) |
| **Groq / Together / Cerebras** | **UNVERIFIED** — no first-party Codex config found; would require the LiteLLM bridge unless they ship `/v1/responses` | — |
| **Azure OpenAI** | ✅ Supported via `query_params`, [#1435](https://github.com/openai/codex/pull/1435); `is_azure_responses_provider` special-casing in source | codex source |
| **Amazon Bedrock** | ✅ Built-in since 2026-04-21 | [#18744](https://github.com/openai/codex/pull/18744) |

Multi-backend guides: [morphllm](https://www.morphllm.com/codex-provider-configuration), [ofox.ai](https://ofox.ai/blog/codex-cli-custom-model-providers-byo-setup/), [danielvaughan Codex KB](https://codex.danielvaughan.com/2026/04/23/codex-cli-custom-model-providers-configuration-guide/), [LangWatch](https://langwatch.ai/docs/ai-gateway/cli/codex), [Unsloth](https://unsloth.ai/docs/basics/codex). **Caution: guides written pre-2026-02 show `wire_api = "chat"` and are now actively wrong** — they will hard-fail config load.

Also: [`lidge-jun/opencodex`](https://github.com/lidge-jun/opencodex) — "Universal provider proxy for OpenAI Codex **&** Claude Code," covering both ends.

---

## 5. Known incompatibilities: Responses-oriented client → OpenAI-compatible gateway

Open issues in openai/codex — what you'll actually hit behind any bridge:

| Issue | Problem |
|---|---|
| [#31181](https://github.com/openai/codex/issues/31181) (2026-07-05) | **`max_output_tokens` sent unconditionally** → `400 Unsupported parameter: max_output_tokens`. Note: reporter says native `wire_api = "responses"` is *fine* — it's the `@ai-sdk/openai` npm wrapper path that breaks. This is the `max_tokens` / `max_completion_tokens` / `max_output_tokens` divergence in practice. |
| [#24973](https://github.com/openai/codex/issues/24973) (2026-05-28) | Codex fails against a custom Responses-API provider with `upstream_error` **while identical curl requests succeed** |
| [#33263](https://github.com/openai/codex/issues/33263) (2026-07-15) | **MCP tools wrapped as "namespace" tool type are ignored by non-OpenAI endpoints** — tool-calling fidelity loss |
| [#31750](https://github.com/openai/codex/issues/31750) (2026-07-09) | Browser & Computer Use plugins **silently unusable** with a custom `model_provider` (no `tool_search` / dynamic tool discovery) |
| [#32349](https://github.com/openai/codex/issues/32349) (2026-07-11) | Custom model metadata unresolvable despite `model_catalog_json` loading — this is the `warning: Model metadata ... not found` I hit |
| [#29592](https://github.com/openai/codex/issues/29592) (2026-06-23) | Model-ID normalization breaks OpenAI-compatible models with **provider prefixes** — `nvidia/...` is exactly this shape |
| [#20652](https://github.com/openai/codex/issues/20652) (2026-05-01) | MCP tool-name flattening breaks through OpenAI-compatible proxies |
| [#8240](https://github.com/openai/codex/issues/8240) | Ollama support assumes localhost, ignoring config.toml — **relevant to your finding 2** if you ever move Ollama off-box |
| [#5458](https://github.com/openai/codex/issues/5458) | No provider-level `extra_body` — blocks Nemotron's `force_nonempty_content` |
| [#34138](https://github.com/openai/codex/issues/34138) (2026-07-19) | API-key length/charset validation too strict for custom `responses-api-endpoint` |
| [#11698](https://github.com/openai/codex/issues/11698) | Allow overriding base URL for the built-in `openai` provider (the reserved-ID trap, filed as a feature request) |

**Ecosystem readiness at the Feb 2026 cutover**, from [Discussion #7782](https://github.com/openai/codex/discussions/7782) — anecdotal, versions have moved:
- **LM Studio 0.3.39** — streaming failed on `responses` despite curl working
- **LiteLLM** — tool use broken in *both* modes at that time (bridge has since been improved)
- **llama.cpp** — partial
- **vLLM 15.1** — non-functional on responses
- **Ollama** — maintainers said "near future"; **delivered in 0.13.3** ← the one that landed

**State/`store`/`previous_response_id`:** Ollama is explicitly non-stateful. NIM self-hosted `store` needs an env flag and leaks memory. **Assume every bridged/local setup is stateless.**

---

## 6. Claude-Code-model-routing tools and NIM support

For completeness — the chain the user's premise was designed to *avoid*.

| Tool | NIM support | Maintained | Notes |
|---|---|---|---|
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | ✅ **Explicit** — [NIM provider docs](https://docs.litellm.ai/docs/providers/nvidia_nim) + [Claude Code with non-Anthropic models](https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models) | ✅ 54.0k★, pushed 2026-07-19 | Translates Anthropic Messages API ↔ OpenAI-compatible. CC calls `GET /v1/models` against `ANTHROPIC_BASE_URL` and populates the `/model` picker labeled *"From gateway"*. **Most credible.** |
| [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code) | ✅ **Explicit** — routes CC → NVIDIA NIM / OpenRouter / DeepSeek / local | ✅ **40.9k★**, pushed 2026-07-19 | Purpose-built for exactly this |
| [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) | ⚠️ Generic OpenAI-compatible; NIM works by config but is **not called out** | ✅ 35.9k★, pushed 2026-07-19 | "One local control plane for every AI agent" |
| `y-router` | **UNVERIFIED** | **UNVERIFIED** | Did not verify directly — flagging rather than guessing |
| `claude-code-proxy` | **UNVERIFIED** | **UNVERIFIED** | Same |

All are **unsupported-but-working-in-practice**, via `ANTHROPIC_BASE_URL`. Third-party writeups specifically covering CC→NIM: [themenonlab](https://themenonlab.blog/blog/free-claude-code-nvidia-nim-proxy-zero-api-fees), [uright.ca](https://uright.ca/posts/running-claude-code-for-free-with-nvidia-nim/), [MindStudio](https://www.mindstudio.ai/blog/free-claude-code-alternatives-openrouter-nvidia-nim-ollama-2).

**UNVERIFIED:** I could not locate the primary Anthropic doc page stating CC *"doesn't support routing Claude Code to non-Claude models through any gateway."* The claim appears in the brief and in secondary write-ups; I will not cite a source I could not read. Separately, one low-trust secondary source claims Anthropic shipped third-party inference support for **Claude Desktop** in April 2026 — **UNVERIFIED, single source, and Desktop ≠ Code.**

---

## 7. Bottom line for the original hypothesis

The chain `Claude Code → /codex:* → codex → NIM` is **architecturally sound and blocked by exactly one missing endpoint**. It becomes:

```
Claude Code → /codex:* → codex → LiteLLM (localhost:4000) → integrate.api.nvidia.com
```

That inserts a required local daemon, but **preserves the property that motivated the design: Claude Code itself only ever talks to Claude.** All non-Claude traffic is downstream of the `codex` binary. That is a materially different trust posture from the §6 routers, which redirect Claude Code's own API calls.

Two things to watch:
- Codex's custom-provider path against non-OpenAI gateways is visibly buggy (§5 — nine-plus open issues, several filed in the last two weeks). Expect degraded tool-calling and MCP behavior, not parity.
- The `nvidia/...` model-ID prefix is precisely the shape that trips [#29592](https://github.com/openai/codex/issues/29592). Aliasing to a flat `model_name` in LiteLLM (as in §3) sidesteps it.

**On the over-confident answer the user received:** the likely path is reading the config reference, seeing `wire_api = "responses"` next to a `base_url` field, and stopping. The config is accepted and the request is well-formed — it fails one HTTP layer past where a config review can see. Your Ollama rc=0 and my NIM 404 together are the cheap disambiguator that a doc read cannot produce.

**Highest-value open experiment, if you have GPU access:** run Codex against a self-hosted NIM ≥1.14.0 container with a gpt-oss model. That is the only unresolved branch, and nobody appears to have published it.

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — primary source: `WireApi` enum, `built_in_model_providers`, `merge_configured_model_providers`, commit history for the chat removal, and the issue/discussion tracker
- [ollama/ollama](https://github.com/ollama/ollama) — `/v1/responses` support (v0.13.3, PR #13351); issues #9659, #10309, #13595 establishing Codex compatibility as the motivation
- [BerriAI/litellm](https://github.com/BerriAI/litellm) — the `/responses` → `/chat/completions` bridge (PRs #11632, #11685; issues #13130, #17246, #23716) and NVIDIA NIM provider support
- [SproutSeeds/codex-nim-poc](https://github.com/SproutSeeds/codex-nim-poc) — independent 2026-03-25 POC reproducing the hosted-NIM 404; source of the `force_nonempty_content` finding and the example TOML
- [HackWidMaddy/OpenCodex](https://github.com/HackWidMaddy/OpenCodex) — community Codex fork claiming built-in NIM integration (10★, working status UNVERIFIED)
- [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code) — CC→NIM proxy, explicitly supports NIM, actively maintained (40.9k★)
- [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) — generic CC model router (35.9k★); NIM by config, not called out
- [lidge-jun/opencodex](https://github.com/lidge-jun/opencodex) — universal provider proxy covering both Codex and Claude Code
- [RightNow-AI/openfang](https://github.com/RightNow-AI/openfang) — issue #471, third-party report of NVIDIA custom-provider auth failures (corroborating context)
- [Hmbown/CodeWhale](https://github.com/Hmbown/CodeWhale) — issue #1081, "nvidia-nim provider can not works" (corroborating context)
- [api-evangelist/nvidia-nim](https://github.com/api-evangelist/nvidia-nim) — NIM API surface catalog (context only)

**Non-repo sources:** [Codex chat/completions deprecation Discussion #7782](https://github.com/openai/codex/discussions/7782) · [Community NIM Discussion #23156](https://github.com/openai/codex/discussions/23156) · [NIM LLM 1.14.0 release notes](https://docs.nvidia.com/nim/large-language-models/1.14.0/release-notes.html) · [NIM LLM API reference](https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html) · [NIM configuration guide](https://docs.nvidia.com/nim/large-language-models/latest/configuration.html) · [LiteLLM /responses docs](https://docs.litellm.ai/docs/response_api) · [LiteLLM NVIDIA NIM provider](https://docs.litellm.ai/docs/providers/nvidia_nim) · [LiteLLM Claude Code non-Anthropic tutorial](https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models) · [LiteLLM OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible) · [Ollama Codex integration](https://docs.ollama.com/integrations/codex) · [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) · [Codex config reference](https://learn.chatgpt.com/docs/config-file/config-reference) · [Codex advanced config](https://developers.openai.com/codex/config-advanced) · [OpenRouter Codex CLI cookbook](https://openrouter.ai/docs/cookbook/coding-agents/codex-cli) · [OpenRouter Codex tutorial](https://openrouter.ai/blog/tutorials/codex-cli-openrouter/) · [Prince Arora, "Run Codex CLI Free with NVIDIA NIM" (Medium, 2026-05-11)](https://prince-arora-aws.medium.com/run-codex-cli-free-with-nvidia-nim-c8392f24243c) · [knightli local-LLM-with-Codex guide](https://knightli.com/en/2026/07/11/use-local-llm-api-with-codex-ollama-lm-studio-vllm/) · [morphllm Codex provider config](https://www.morphllm.com/codex-provider-configuration)

---

**Reconciliation summary: zero contradictions.** Your finding 1 is confirmed at source-line and runtime level. Your finding 2 is confirmed with upstream provenance (Ollama PR #13351, v0.13.3) — and it is the stronger of the two results, because it demonstrates the protocol requirement is satisfiable by a non-OpenAI server, which is exactly what isolates the NIM failure to NVIDIA rather than to Codex. The one caveat to carry forward: Ollama's `/v1/responses` is **non-stateful**, so a short `codex exec` won't exercise `previous_response_id` behavior.
