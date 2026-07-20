# Free Claude Code — configuration recipe (claudefa.st)

Source: https://claudefa.st/blog/tools/customization/free-claude-code
Type: article (fetched 2026-07-19)

## Architecture

Uses a **local FastAPI proxy** (NOT LiteLLM, NOT a direct base-URL override).
The proxy listens on `localhost:8082` and translates Anthropic Messages API
calls to upstream providers. Implementation:
`https://github.com/Alishahryar1/free-claude-code`.

## Environment variables

Required for proxy redirection:

```
ANTHROPIC_AUTH_TOKEN="freecc"
ANTHROPIC_BASE_URL="http://localhost:8082"
```

Provider keys:

```
NVIDIA_NIM_API_KEY="nvapi-your-key"
OPENROUTER_API_KEY="sk-or-your-key"
```

Per-tier model routing — note this remaps EVERY Claude tier, so the strong
model is replaced too:

```
MODEL_OPUS="nvidia_nim/moonshotai/kimi-k2.5"
MODEL_SONNET="open_router/deepseek/deepseek-chat:free"
MODEL_HAIKU="lmstudio/unsloth/GLM-4.7-Flash-GGUF"
MODEL="nvidia_nim/z-ai/glm4.7"
```

## Providers named

| Provider | Setup | Model examples |
|---|---|---|
| NVIDIA NIM | free tier at build.nvidia.com | `z-ai/glm4.7`, `moonshotai/kimi-k2.5` |
| OpenRouter | direct API | DeepSeek V4, GLM, Llama variants |
| DeepSeek | Anthropic-compatible endpoint | DeepSeek V4 |
| LM Studio | desktop GUI + local | model-dependent tool-use support |
| llama.cpp | embedded, needs context tuning | any GGUF |
| Ollama | easiest local setup | Gemma, Llama 3.1 |

No Groq, Cerebras, or direct Gemini integration mentioned.

## Stated limitations (verbatim claims)

1. **Tool-call reliability degrades** — "Models with shaky tool-call formatting
   will return malformed deltas, omit tool names, or emit tool calls as plain
   text."
2. **Context window shrinks** — most alternatives cap at 32K-128K vs Opus 200K+.
3. **Quality drop is real** — "70 to 85 percent" of Opus quality at best;
   "Multi-step refactors, subtle bug hunts, and architectural decisions degrade
   noticeably."
4. **Streaming quirks** — malformed token counts occur.
5. **Local models are slow** — "Not a real option for a workflow that fires
   twenty tool calls per minute" without a discrete GPU.

## Setup steps

1. Install `uv`, Python 3.14, Claude Code.
2. Clone `github.com/Alishahryar1/free-claude-code`.
3. Set `.env` with provider key + `MODEL` + `ANTHROPIC_AUTH_TOKEN="freecc"`.
4. `uv run uvicorn server:app --host 0.0.0.0 --port 8082`.
5. `ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude`

## Author's own mitigation

Pair cheaper models with "a strong agent harness" — structured decomposition,
subagent roles, pre-planning, and progressive context disclosure recover
meaningful output quality.

## Relevance to this program (annotation, not from the article)

This recipe replaces **every** Claude tier including Opus, which directly
conflicts with the locked decision "architect-only strong model (Fable 5 @ high,
Opus 4.8 fallback)". Adopting it wholesale would remove the architect the design
depends on. The useful extract is the **provider/model list** (NIM free tier
serving `kimi-k2.5` and `glm4.7`) and the confirmation that the author's own
mitigation is precisely this program's thesis: cheap models + strong harness +
verification.
