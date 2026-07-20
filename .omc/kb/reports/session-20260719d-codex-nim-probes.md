# Codex CLI ↔ NVIDIA NIM — empirical probe results (session 2026-07-19-d)

Original findings from local probes, not from documentation. Every claim below
was produced by running a command on this machine on 2026-07-19. Where a probe
failed its own control arm, that is recorded rather than hidden.

## Verdict summary

| Question | Answer | Basis |
|---|---|---|
| Does codex-plugin-cc let Claude Code use arbitrary models? | **No** | plugin delegates CC → local `codex`; `openai_base_url` repoints Codex's own provider only |
| Can Codex be a wrapper over NIM (CC → codex → NIM)? | **NO — hosted NIM has no `/v1/responses`** | RESOLVED: agent probe (401/403 on chat vs 404 byte-identical to a fake route) + `codex exec` 404 + independent POC `SproutSeeds/codex-nim-poc` 4 months earlier. See `agents/codex-nim-wiring.md` |
| Why did GET `/v1/responses` return 405 then? | **Edge gateway knows the path; backend has no handler** | POST forwards to a nonexistent handler. Confirms 405 was never evidence of function — re-probe later, it may be a moving target |
| Is there a working NIM path? | **Yes — LiteLLM bridge** (`use_chat_completions_api: true`) | LiteLLM docs name Codex CLI as the motivating use case. UNVERIFIED locally (no key) |
| **Can Codex be a wrapper over a LOCAL free model (CC → codex → Ollama)?** | **YES — CONFIRMED, rc=0** | Probe 6; `ollama ps` keep-alive refreshed during run, no `auth.json` present |
| Does Ollama implement a real Responses API? | **Yes — full payload, HTTP 200** | Probe 6 |
| Does codex 0.144.6 support `wire_api = "chat"`? | **No — removed** | string compiled into the binary |
| Does NIM register a `/v1/responses` route? | **Yes** | GET → 405 vs 404 for fake paths |
| Does that prove NIM's Responses API *works*? | **No** | control arm: Ollama returns 405 too |
| Can Claude Code itself route to non-Claude models? | **No, unsupported** | Anthropic docs + process-global `ANTHROPIC_BASE_URL` |
| Does graphify 0.9.20 support custom OpenAI endpoints? | **Yes** | installed `llm.py:112` |

## Probe 1 — `wire_api = "chat"` is removed from Codex

`codex-cli 0.144.6` (installed at
`~/.local/share/mise/installs/codex/0.144.6/bin/codex`). Running `strings` over
the binary surfaces this literal, compiled-in message:

```
`wire_api = "chat"` is no longer supported.
remote thread config returned unknown wire_api:
```

Adjacent provider-config keys also present in the binary:
`base_url`, `env_key`, `env_key_instructions`, `experimental_bearer_token`,
`bearer_token`, `wire_api`, `query_params`, `request_max_retries`,
`stream_max_retries`, `stream_idle_timeout_ms`, `requires_openai_auth`,
`supports_websockets`, `startup_timeout_ms`.

**Reading:** the config docs are correct for this version — `responses` is the
only accepted `wire_api`. Chat/completions support existed historically and was
deliberately removed. Any third-party endpoint must therefore speak the
**Responses API**, not chat/completions, to work with Codex.

## Probe 2 — NIM endpoint existence (control-armed)

A POST-based probe was run first and **failed its control arm**: both
`/v1/chat/completions` (certainly real) and `/v1/bogus-endpoint-xyz` returned
`404`, so 404 carried no information. Recorded here because the failed probe is
the reason the second one was designed differently.

A GET-based probe discriminates, because real routes reject the method (405)
while unknown routes 404:

```
GET https://integrate.api.nvidia.com/v1/responses          -> 405
GET https://integrate.api.nvidia.com/v1/chat/completions   -> 405
GET https://integrate.api.nvidia.com/v1/completions        -> 405
GET https://integrate.api.nvidia.com/v1/embeddings         -> 405
GET https://integrate.api.nvidia.com/v1/models             -> 200
GET https://integrate.api.nvidia.com/v1/bogus-endpoint-xyz -> 404
GET https://integrate.api.nvidia.com/v1/another-fake-abc   -> 404
```

`/v1/responses` is a **registered route** on NIM.

## Probe 3 — the control arm that weakened Probe 2

The same GET probe against local Ollama 0.32.1:

```
GET http://localhost:11434/v1/responses        -> 405
GET http://localhost:11434/v1/chat/completions -> 405
GET http://localhost:11434/v1/models           -> 200
GET http://localhost:11434/v1/bogus-xyz        -> 404
```

Ollama registers `/v1/responses` too. Therefore **405 proves route
registration, not a working Responses implementation.** The honest conclusion
from Probes 2+3 is "NIM plausibly speaks Responses", not "NIM speaks
Responses". Settling it requires a real authenticated POST.

## Probe 4 — NIM catalog is publicly listable

`GET /v1/models` → 200 with **119 models**, no auth required. Confirms the
endpoint is live and NVIDIA-operated. Real model IDs (note: `qwen2.5-coder` and
`deepseek-v3` are **not** in the catalog — those were guesses):

- `moonshotai/kimi-k2.6`
- `z-ai/glm-5.2`
- `deepseek-ai/deepseek-v4-pro`, `deepseek-ai/deepseek-v4-flash`
- `openai/gpt-oss-120b`
- `nvidia/nemotron-3-super-120b-a12b`
- `qwen/qwen3.5-397b-a17b`

## Probe 5 — graphify 0.9.20 custom-endpoint support (issue #959 is stale)

Installed source, `graphify/llm.py:112`:

```python
"base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
```

with the comment at line 108: *"OPENAI_BASE_URL points the backend at any
OpenAI-compatible server"*. Sibling providers each take their own override:
`ANTHROPIC_BASE_URL`, `KIMI_BASE_URL`, `OLLAMA_BASE_URL`
(default `http://localhost:11434/v1`), `GEMINI_BASE_URL`, `DEEPSEEK_BASE_URL`.

graphify also ships `provider_base_url_ok()`, whose docstring states a custom
`base_url` "is an exfiltration channel" — the maintainers explicitly treat
pointing a corpus at a third party as a security decision.

**GitHub issue #959 ("OpenAI base_url hardcoded") is stale-open.** The feature
shipped in 0.8.40. An earlier research pass read the open issue and concluded
custom endpoints were blocked; reading the installed source refuted it. *Source
beats issue tracker.*

## Blocking constraint — NVIDIA API Trial ToS

Independent of any technical result:

- **§1.2 / §1.4** — trial access is for *"internal testing and evaluation
  purposes, not in production"* without a paid Subscription.
- **§3.3(iv)** — NVIDIA collects *"User Content and Generated Content to
  improve NVIDIA products and services, including AI models."* This contradicts
  §2.3's no-storage language; the training-use clause is the operative one.
- Practical ceiling: **40 RPM, ~1,000 credits**.

**Consequence:** do not send private repo/corpus content to NIM. The technical
path being open does not make the data path acceptable.

## Why Claude Code cannot mix a Claude architect with non-Claude workers

Three independent confirmations:

1. Subagent `model:` accepts only `sonnet|opus|haiku|fable|<claude model id>|
   inherit` — "the same values as the `--model` flag".
2. `ANTHROPIC_BASE_URL` is **process-global** — all-or-nothing. This is why the
   claudefa.st recipe must remap `MODEL_OPUS` as well.
3. Anthropic states Claude Code "doesn't support routing Claude Code to
   non-Claude models through any gateway"
   (<https://code.claude.com/docs/en/llm-gateway>).

This **confirms** the program's already-locked launcher-wrapped shell-out
substrate: a separate process with separate auth is the only working shape.

## GitHub repos touched

- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — README
  read directly; established the plugin's direction and its `openai_base_url`
  semantics.
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) —
  issue #959 status vs installed 0.9.20 source; `llm.py` provider table.
- [DeL-TaiseiOzaki/claude-code-orchestra](https://github.com/DeL-TaiseiOzaki/claude-code-orchestra)
  — cloned; prior art already built on codex-plugin-cc (3-tier routing,
  `agent-router.py`, Sol Guardrails), running `gpt-5.6-sol` with no custom
  base_url.
- [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code)
  — the FastAPI Anthropic→NIM proxy behind the claudefa.st recipe.

---

## CONFIRMED (Probe 6): Codex CLI drives a local model end-to-end — no OpenAI, no NIM, no cost

**This supersedes the "plausible/unverified" framing above for the LOCAL case.**

### Ollama implements a real Responses API

`POST http://localhost:11434/v1/responses` → **HTTP 200** with a correct
OpenAI Responses payload: `object:"response"`, `output[]` containing a
`reasoning` item and a `message` item, plus `previous_response_id`, `store`,
`tool_choice`, `parallel_tool_calls`, and `usage.output_tokens_details.
reasoning_tokens`. Not a stub — the full shape.

This explains why Codex ships built-in `ollama` / `lmstudio` providers despite
`wire_api = "chat"` being removed: those servers speak **Responses**.

### End-to-end run

```toml
# $CODEX_HOME/config.toml   (scratch dir — user's ~/.codex untouched)
model = "qwen3:0.6b"
model_provider = "ollama"
approval_policy = "never"
sandbox_mode = "read-only"
```

```
CODEX_HOME=<scratch> codex exec --skip-git-repo-check "say OK"   ->  RC=0
```

Completed successfully, 10,022 tokens.

### Control arms (this is what makes it evidence)

| arm | result | what it rules out |
|---|---|---|
| no `auth.json` in scratch `CODEX_HOME` | absent | ChatGPT/OpenAI credentials — fallback impossible |
| `ollama ps` UNTIL timer **before** run | "About a minute from now" (decaying) | — |
| `ollama ps` UNTIL timer **during** run | **"4 minutes from now" (refreshed)** | proves the request reached Ollama; keep-alive only resets on a request |
| dead-port provider | **INVALID** — hung on stdin, never tested the socket | recorded as failed, not counted as evidence |

### Consequence

The chain **`Claude Code → /codex:* (codex-plugin-cc) → codex → local Ollama`
works today**: free, fully local, no third-party ToS, no rate limit, no data
egress. This is strictly better than the NIM variant for any work touching
private repo content.

It also raises confidence that **NIM would work if its `/v1/responses` is
functional** — the protocol requirement is satisfiable by non-OpenAI servers,
which was the open question. Confirming NIM specifically still needs one
authenticated call.

### Caveat

`qwen3:0.6b` followed instructions poorly (it summarized `AGENTS.md` instead of
replying "OK"). The chain is proven; **worker quality is a separate axis** and
argues for `qwen3:14b` or a stronger free endpoint. `qwen3:14b` exceeded a
2-minute foreground budget on cold load — size the timeout accordingly.
