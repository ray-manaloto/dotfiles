# Secret Consumption Sweep — which of the 50 declared secrets are actually consumed

**Agent:** secret-consumers · **Date:** 2026-08-04 · **Status:** COMPLETE

Research question: which of this Mac's 50 declared secrets are actually consumed,
by what, and where — and which are orphans? Feeds a decision about what a new
"universal CRUD for API keys across dev projects" CLI must support.

## Safety posture for this sweep

No secret VALUE was printed, logged, or written at any point. Presence was probed
with `printenv VAR >/dev/null` and `[ -n "$VAR" ]`; the alias question was settled
with `[ "$A" = "$B" ]`, which emits one bit and never the value. No `fnox get`, no
`fnox list -V`. No value-emitting substitution (`${VAR:-x}` / `${VAR:=x}`) was used.
`fnox` was invoked only via its absolute path.

## Corpus

All 50 names are declared in ONE file — `/Users/rmanaloto/.config/fnox/config.toml`
(via `fnox list --sources`). 49 resolve through provider
`doppler_dotfiles_dev_personal`; **`DOPPLER_TOKEN` alone resolves via `keychain`**
— it is the bootstrap credential for the other 49.

Swept: `dotfiles`, `knowledge-base`, `macos-development-environment`, the other
25 `~/dev/github/ray-manaloto/*` repos (enumerated, not assumed — 28 total),
`~/.claude/` (162 `.mcp.json` files), `~/.claude.json`, and `~/.config/`.

## Finding 0 — raw hit counts are worthless here; four classes inflate them

| Class | Example | Consumer? |
|---|---|---|
| Baseline declaration | `dotfiles/doctor.toml` (all 50) | NO |
| Guard / protection list | `python/src/dotfiles_setup/hook_guard.py` — `secret_value_substitution` names credentials in order to **deny** printing them | NO |
| Test fixture | `tests/test_child_env.py`, `tests/test_hook_guard.py` | NO |
| Vendor doc cache | `docs/research/mintlify-cache/jdx/fnox/llms-full.txt` — 24 hits for `AWS_ACCESS_KEY_ID` | NO — third-party example text |

`AWS_ACCESS_KEY_ID` scores 46 non-markdown hits across the three repos and **not
one is a consumer**.

## Finding 1 — four names, ONE value (verified, not assumed)

The brief asked me to verify the alias belief rather than assume it. **It is wrong
as stated, and it undercounts.**

mise's docs (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:4004-4011`)
document a **precedence chain**, not aliases — three *distinct* variables mise
consults in order:

| Priority | Source |
|---|---|
| 1 | `MISE_GITHUB_TOKEN` |
| 2 | `GITHUB_API_TOKEN` |
| 3 | `GITHUB_TOKEN` |

They are separate variables that happen to carry the same value here. That they
are distinct is proven by `.devcontainer/Dockerfile:311`, which must explicitly
derive one from the other: `export MISE_GITHUB_TOKEN="$GITHUB_TOKEN"`.

Equality bits measured on this host (one bit each, no values):

```
GITHUB_TOKEN == GITHUB_API_TOKEN
GITHUB_TOKEN == MISE_GITHUB_TOKEN
GITHUB_TOKEN == GITHUB_MCP_PAT        <-- NOT previously suspected
AWS_REGION   == AWS_DEFAULT_REGION
NVIDIA_API_KEY != NVIDIA_20260705     <-- two DIFFERENT keys
OTEL_EXPORTER_OTLP_ENDPOINT != GEMINI_TELEMETRY_OTLP_ENDPOINT
```

So **one GitHub PAT is stored under four names**, and `AWS_REGION` /
`AWS_DEFAULT_REGION` are a fifth duplicate pair. A rotation of that PAT must
update four Doppler entries or the host silently runs split-brain.

**Implication for the new CLI: it needs a first-class alias/fan-out concept** —
one logical credential, N exported names — or rotation stays a four-place manual edit.

## Finding 2 — a predecessor secret store still exists

`~/.config/mise/secrets.sops.json` is a **SOPS-encrypted store holding 34 of the
50 names**, including every one of the orphans below. It is the historical
provenance of the observability block (Grafana/Loki/Mimir/Tempo/OpenLIT) and
predates the Doppler+fnox arrangement.

`~/.config/fnox/` additionally carries **8 timestamped backup copies** of the
config, with names like `config.toml.BROKEN-by-claude-20260801-1420` and
`config.toml.WIPED-evidence-20260730-055104`. Any migration must treat these as
part of the surface — a "universal CRUD" tool that only knows the live file will
leave 34 names' worth of stale declarations behind it.

## Finding 3 — MCP servers get credentials by INHERITANCE, not interpolation

Control-armed negative: across `~/.claude/settings.json`, `~/.claude/mcp_servers.json`,
`~/.claude.json`, and all 162 `.mcp.json` files under `~/.claude`, exactly **three**
files interpolate a secret name, and they are the same plugin at three paths:

```
~/.claude/plugins/marketplaces/context7-marketplace/plugins/claude/context7/.mcp.json:7
        "Authorization": "${CONTEXT7_API_KEY:-}"
```

Everything else relies on `env = true` putting the credential in the environment the
server inherits. That is the mechanism the whole posture rests on, and it means
**grep-for-`${VAR}` will systematically under-report consumption** — the new CLI
cannot infer usage from config files alone.

## Finding 4 — two declared secrets are ABSENT from the environment

`OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_PROTOCOL` are declared in
fnox but **not set in this process** (48/50 present). Under `env = true` the
project rule states that outcome is unreachable, so this is a real failure, not a
design choice — worth a follow-up (likely a stale `MISE_ENV_CACHE` entry or a
per-secret override). I did not diagnose it; it is out of this sweep's scope.

## Findings table

Category legend: **A** = agent/AI tooling · **O** = observability · **C** = cloud/infra
· **S** = social/scraping · **W** = web app.

| Secret | Consumed by (file:line) | Cat | Verdict |
|---|---|---|---|
| AGE_PRIVATE_KEY | `mde/src/mde/secrets/manage.py:45,486-507` (bootstrap parity check vs Doppler) | C | CONSUMED |
| AUTH_TOKEN | `~/.config/last30days/.env:5`; last30days skill `README.md:148` (X/Twitter cookie, Bird CLI) | S | CONSUMED |
| AWS_ACCESS_KEY_ID | no in-repo consumer; read by AWS SDK/CLI by convention | C | AMBIENT |
| AWS_DEFAULT_REGION | AWS CLI convention; **value-identical to `AWS_REGION`** | C | ALIAS + config |
| AWS_REGION | `mde/.agents/skills/aws-agentic-ai/services/gateway/deploy-template.sh`; AWS SDK convention | C | AMBIENT (config, not secret) |
| AWS_SECRET_ACCESS_KEY | no in-repo consumer; AWS SDK/CLI convention | C | AMBIENT |
| BRAVE_API_KEY | `~/.config/last30days/.env`; `mde/scripts/mcp/mde-mcp-brave-search:1`; `dotfiles/scripts/devcontainer-smoke.sh` | S | CONSUMED |
| BSKY_APP_PASSWORD | `~/.config/last30days/.env`; skill `README.md:155` | S | CONSUMED |
| BSKY_HANDLE | `~/.config/last30days/.env:5`; skill `README.md:155` | S | CONSUMED (config, not secret) |
| CONTEXT7_API_KEY | `~/.claude/plugins/.../context7/.mcp.json:7`; `~/.config/opencode/opencode.json:13`; `dotfiles/python/src/dotfiles_setup/doctor.py` | A | CONSUMED |
| CT0 | `~/.config/last30days/.env`; skill `README.md:148,165` (X cookie, pairs with AUTH_TOKEN) | S | CONSUMED |
| DB_PASSWORD | no consumer in Ray's code — only vendored `claude-flow-src` examples and vendor docs | W | ORPHAN |
| DOPPLER_TOKEN | keychain-backed bootstrap for the other 49; `mde/src/mde/secrets/manage.py` (14 refs), `mde/.mise.toml` | C | CONSUMED (critical) |
| EXA_API_KEY | last30days `README.md:157,364`; exa plugin; `dotfiles/scripts/devcontainer-smoke.sh` | A | CONSUMED |
| GEMINI_API_KEY | `knowledge-base/mise.toml:2` + `kb_setup/graphify_env.py`; `~/.config/fabric/.env.all:9`; `mde/scripts/install-agent-stack.sh` | A | CONSUMED |
| GEMINI_TELEMETRY_ENABLED | `mde/src/mde/telemetry_verify.py` (4); `mde/scripts/status-dashboard.sh` | O | CONSUMED (boolean, not secret) |
| GEMINI_TELEMETRY_LOG_PROMPTS | declaration only | O | ORPHAN (boolean, not secret) |
| GEMINI_TELEMETRY_OTLP_ENDPOINT | `mde/src/mde/telemetry_verify.py` (2); `status-dashboard.sh` | O | CONSUMED (endpoint, not secret) |
| GEMINI_TELEMETRY_OTLP_PROTOCOL | `mde/src/mde/telemetry_verify.py`; `status-dashboard.sh` | O | CONSUMED (config, not secret) |
| GEMINI_TELEMETRY_TARGET | `mde/scripts/status-dashboard.sh` | O | CONSUMED (config, not secret) |
| GITHUB_API_TOKEN | `renovate_dryrun.py:98`; mise precedence #2 | C | ALIAS of GITHUB_TOKEN |
| GITHUB_MCP_PAT | `mde/scripts/mcp/mde-mcp-github:2`, `gemini-wrapper.sh`; **value-identical to GITHUB_TOKEN** | A | ALIAS of GITHUB_TOKEN |
| GITHUB_TOKEN | 8 GHA workflows/actions; `.devcontainer/Dockerfile:309-311,562-564`; `docker-bake.hcl`; `renovate_dryrun.py:97`; `hk.pkl` | C | CONSUMED (heaviest) |
| GOOGLE_CLIENT_ID | `guilde-lite-tdd-sprint/backend/app/core/oauth.py`, `config.py:112`, `kubernetes/secret.yaml` | W | CONSUMED (not a secret — public ID) |
| GOOGLE_CLIENT_SECRET | `guilde-lite-tdd-sprint/backend/app/core/oauth.py`, `config.py:113` | W | CONSUMED |
| GRAFANA_PASSWORD | `mde/docker/observability/compose.yaml:28` (→ `GF_SECURITY_ADMIN_PASSWORD`); `mde/src/mde/domain/observability_stack.py` | O | CONSUMED |
| LANGSMITH_API_KEY | `mde/scripts/mcp/mde-mcp-langsmith:1`; `verify-langchain-tools.sh`; `health-check.sh` | A | CONSUMED |
| LANGSMITH_WORKSPACE_ID | `knowledge-base/python/src/kb_setup/evals.py:1`; `knowledge-base/mise.toml`; `mde/scripts/mcp/mde-mcp-langsmith:2` | A | CONSUMED (ID, not secret) |
| LINEAR_API_KEY | `~/.claude/plugins/marketplaces/claude-tag-plugins/linear/skills/linear-api/scripts/linear_issues.sh` | A | CONSUMED (if that plugin is enabled) |
| LOKI_S3_ACCESS_KEY | declaration only | O | ORPHAN |
| LOKI_S3_BUCKET | declaration only | O | ORPHAN (config, not secret) |
| LOKI_S3_SECRET_KEY | declaration only | O | ORPHAN |
| MIMIR_S3_ACCESS_KEY | declaration only | O | ORPHAN |
| MIMIR_S3_BUCKET | declaration only | O | ORPHAN (config, not secret) |
| MIMIR_S3_SECRET_KEY | declaration only | O | ORPHAN |
| MISE_GITHUB_TOKEN | `.github/actions/lock-refresh/action.yml` (3); `.devcontainer/Dockerfile:311,564`; mise precedence #1 | C | ALIAS of GITHUB_TOKEN |
| NEXTAUTH_SECRET | no consumer in Ray's code (only vendored `claude-flow-src` skill docs) | W | ORPHAN |
| NEXTAUTH_URL | declaration only — **zero** refs outside declarations | W | ORPHAN (URL, not secret) |
| NVIDIA_20260705 | `hook_guard.py` (protection list only) — **value differs from NVIDIA_API_KEY** | A | ORPHAN (dated/stale) |
| NVIDIA_API_KEY | `dotfiles/python/src/dotfiles_setup/graph_bakeoff.py:1` | A | CONSUMED |
| OPENLIT_ENDPOINT | `mde/scripts/verify-openlit.sh` (2); `mde/configs/otel/collector-gateway.yaml`, `collector-env.sample` | O | CONSUMED (endpoint, not secret) |
| OPENLIT_UI_PASSWORD | declaration only | O | ORPHAN |
| OPENLIT_UI_USER | declaration only | O | ORPHAN (username, not secret) |
| OTEL_EXPORTER_OTLP_ENDPOINT | `mde/src/mde/observability.py`, `telemetry_verify.py` (11), `mde/.claude/settings.json`, `mde/.codex/config.toml`; OTel SDK convention | O | AMBIENT + CONSUMED (endpoint, not secret) ⚠ absent from env |
| OTEL_EXPORTER_OTLP_PROTOCOL | `mde/src/mde/telemetry_verify.py`; `mde/.claude/settings.json`; OTel SDK convention | O | AMBIENT (config, not secret) ⚠ absent from env |
| SCRAPECREATORS_API_KEY | `~/.config/last30days/.env`; skill `README.md:134-153` (TikTok/IG/Threads/LinkedIn/Reddit/YouTube) | S | CONSUMED |
| SKILLSMP_API_KEY | `mde/src/mde/research/clients/skillsmp_client.py` (6); `mde/src/mde/research/skill_discover.py` | A | CONSUMED (mde is deprecated) |
| TEMPO_S3_ACCESS_KEY | declaration only | O | ORPHAN |
| TEMPO_S3_BUCKET | declaration only | O | ORPHAN (config, not secret) |
| TEMPO_S3_SECRET_KEY | declaration only | O | ORPHAN |

### Tally

- **CONSUMED**: 25
- **AMBIENT** (third-party reads by convention, no in-repo ref): 4 — `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `OTEL_EXPORTER_OTLP_PROTOCOL`
- **ALIAS**: 4 — `GITHUB_API_TOKEN`, `GITHUB_MCP_PAT`, `MISE_GITHUB_TOKEN` (all = `GITHUB_TOKEN`), `AWS_DEFAULT_REGION` (= `AWS_REGION`)
- **ORPHAN**: 17

### The orphan block is one dead project

14 of the 17 orphans are a single coherent group: an **S3-backed
Grafana/Loki/Mimir/Tempo/OpenLIT observability stack** (9 names) plus a
**NextAuth web app** (2) plus stragglers (`DB_PASSWORD`,
`GEMINI_TELEMETRY_LOG_PROMPTS`, `NVIDIA_20260705`). The observability compose that
survives (`mde/docker/observability/compose.yaml`) uses **local storage and reads
only `GRAFANA_PASSWORD`** — the S3 tier was declared and never wired.

## Names that look like CONFIGURATION, not secrets

Project rule `.claude/rules/secrets-out-of-the-shell-env.md` rule 3 — "do not mark
a non-secret as a secret" — because fnox redaction is value-based, so a short or
empty "secret" corrupts every log the tool writes. **19 of the 50 qualify:**

Endpoints/URLs: `OTEL_EXPORTER_OTLP_ENDPOINT`, `GEMINI_TELEMETRY_OTLP_ENDPOINT`,
`OPENLIT_ENDPOINT`, `NEXTAUTH_URL`
Protocols/targets: `OTEL_EXPORTER_OTLP_PROTOCOL`, `GEMINI_TELEMETRY_OTLP_PROTOCOL`,
`GEMINI_TELEMETRY_TARGET`
Booleans: `GEMINI_TELEMETRY_ENABLED`, `GEMINI_TELEMETRY_LOG_PROMPTS`
Regions: `AWS_REGION`, `AWS_DEFAULT_REGION`
Buckets: `LOKI_S3_BUCKET`, `MIMIR_S3_BUCKET`, `TEMPO_S3_BUCKET`
Usernames/handles/IDs: `OPENLIT_UI_USER`, `BSKY_HANDLE`, `LANGSMITH_WORKSPACE_ID`,
`GOOGLE_CLIENT_ID` (public by OAuth design)

`GEMINI_TELEMETRY_ENABLED` is the sharpest case: a boolean whose value is almost
certainly `true` or `1`. A 1-4 character "secret" means fnox will redact every
occurrence of that string in any log it touches.

## Stale / dated

- **`NVIDIA_20260705`** — a date-stamped name (2026-07-05), value **differs** from
  `NVIDIA_API_KEY`, and its only reference is `hook_guard.py`'s protection list.
  Almost certainly a superseded key kept "just in case". Prime deletion candidate.
- **`AUTH_TOKEN`** — dangerously generic name for what is specifically an
  **X/Twitter session cookie**. Any tool that reads a variable called `AUTH_TOKEN`
  by convention will silently get an X cookie.
- **`SKILLSMP_API_KEY`** — sole consumer is `macos-development-environment`, which
  is deprecated.
- The 8 `~/.config/fnox/config.toml.*` backups, two of them named `BROKEN-by-claude`
  and `WIPED-evidence`.

## Implications for the "universal CRUD for API keys" CLI

1. **Aliases are a first-class requirement, not a nicety.** One PAT lives under
   four names; rotation today means four coordinated edits.
2. **Usage cannot be inferred from config files.** Only 1 of 50 is interpolated
   into an MCP config; the rest are consumed by environment inheritance. Any
   "find unused secrets" feature that greps for `${VAR}` will report ~49 false orphans.
3. **Secret vs config must be a declared field.** 19 of 50 are not secrets, and
   marking them so actively corrupts logs via value-based redaction.
4. **Migration must handle predecessor stores.** A SOPS store with 34 of the names
   and 8 config backups are still on disk.
5. **`DOPPLER_TOKEN` is the bootstrap root** — the only keychain-backed entry, and
   the one every other read depends on. It needs a distinct lifecycle.

## Control arms

Every negative below was armed before being reported.

| Probe | Positive arm | Negative arm | Verdict |
|---|---|---|---|
| Secret names in Claude MCP/settings configs → 0 | `mcpServers`/`enableAllProjectMcpServers`, same `rg -F -w -f` shape → **31 hits in `~/.claude.json`** | — | probe discriminates; the 0 is real |
| ORPHAN claim across all corpora | `GITHUB_TOKEN` → **272 files** | freshly-invented `QWFJVZ_NOPE_7731` (never written to disk before this run) → **0 files** | probe discriminates in both directions |
| `LOKI_S3_ACCESS_KEY` "orphan" | — | 13 files, all enumerated and inspected: fnox config + 8 backups, SOPS store, `doctor.toml`, a test-values doc, and this report | all declarations, zero consumers |

The known-absent term was **invented fresh for this run** rather than reused from a
prior receipt — a published control string is in the corpus and stops discriminating.
It is deliberately not repeated as a reusable token.

### Two bounds I hit and corrected mid-sweep

1. **`| head -200` on a `tee` pipeline killed the loop via SIGPIPE**, truncating
   the per-name breakdown at name 28 of 50. Re-run unbounded.
2. **`sort -u -t: -k3` collapsed each file to a single name** (the `-o` output has
   only 2 colon fields, so `-k3` sorted on nothing). This under-reported
   `~/.config/last30days/.env` as holding one variable when it holds six — and
   those six are the reclassification that moved five names out of the orphan list.
   My own parser was the bound.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — primary sweep corpus; `doctor.toml`, `hook_guard.py`, `renovate_dryrun.py`, workflows, Dockerfile
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `kb_setup/graphify_env.py`, `evals.py`, `mise.toml`
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — deprecated historical owner; `mde/secrets/manage.py`, `telemetry_verify.py`, observability compose, MCP wrappers
- [ray-manaloto/guilde-lite-tdd-sprint](https://github.com/ray-manaloto/guilde-lite-tdd-sprint) — sole consumer of the Google OAuth pair
- [jdx/mise](https://github.com/jdx/mise) — cached docs establishing the GitHub token precedence chain (refuting the alias framing)
- [jdx/fnox](https://github.com/jdx/fnox) — cached docs; the declaring tool
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — cached docs (source of many false-positive hits)
