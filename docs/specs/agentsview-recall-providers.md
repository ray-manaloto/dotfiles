# AgentsView Recall provider pilot

AgentsView 0.45.0 has two different model-backed features. **Generated insights**
can invoke the installed Claude or Codex CLI directly. **Automatic Recall
extraction** requires one OpenAI-compatible `/chat/completions` endpoint and a
strict `json_schema` response. Antigravity is not a native generated-insight
choice. Use an API bridge for it and for Claude/Codex extraction; do not treat
the presence of an agent CLI as proof that its account is available to Recall.

The active AgentsView service and archive belong to the global
`av-native:*` controller. This pilot is a configuration recipe, not a second
writer or a change to its credential-bearing config. Keep one extraction
provider active at a time. AgentsView fingerprints each configuration as a
separate generation; changing provider does not merge its output into the old
generation.

At the 2026-10-09 checkpoint, that service is ready on AgentsView 0.45.0,
automatic extraction is disabled, and generated insights have an endpoint
configured. The bundled finding-history skill is current for Claude and
`.agents/skills` readers. In disposable empty archives, both TOML examples
below passed `agentsview sync` and `recall extract status`. A local mock
endpoint passed `recall extract doctor`: AgentsView sent one strict
`json_schema` request to `/v1/chat/completions`. The reference-only fnox
profile below also passed a **live** OpenRouter probe without printing or
writing the key. In a disposable archive with a four-message synthetic Claude
session, `nvidia/nemotron-3-super-120b-a12b:free` passed `doctor` and
`extract run --session`: 1 session, 4 units, 4 entries, 0 failures, and an
active generation. `liquid/lfm-2.5-2.6b:free` passed both commands too, but
its entry count was not inspected. After three separate proxy OAuth logins,
the same isolated test also passed through CLIProxyAPI 8.0.23 with
`claude-haiku-5-5` (6 entries), `gpt-6-luna` (4 entries), and `gemini-3-flash`
(4 entries); each had 4 units, 0 failures, and an active generation. The
generic `openrouter/free` router passed `doctor` but its full extraction
violated AgentsView's response schema; `apodex/apodex-1.1-mini:free` failed
`doctor` with HTTP 400. Claude Haiku 4.5 and Sonnet 4.5 also failed the
strict-schema doctor, while Sonnet 4.6 passed `doctor` without a full run.
These are time-bound provider observations, not guarantees for future sessions
or production transcript quality.

## Generated insights: native Claude or Codex

With no `[insights] endpoint` or `model`, select an installed CLI in the
Generated insights picker, or set one default in the AgentsView config:

```toml
[insights]
default_agent = "codex" # or "claude"
```

`agentsview insight generate --agent claude|codex ...` explicitly selects one
for a single request. The server process must resolve that CLI on its `PATH`
and have that CLI's own login. No extraction setting changes this choice. The
current owner-managed service has an `[insights]` endpoint and model, so its
CLI picker cannot take effect until both values are removed from the existing
config and the service is restarted.

For generated insights using **any** of the four API routes, configure
`[insights] endpoint`, `model`, and `api_key_env` with the same endpoint and
exact model ID chosen below. This includes Antigravity through CLIProxyAPI and
OpenRouter directly. Endpoint mode overrides `default_agent`; it cannot be
combined with per-request native CLI selection in one running server.

## Automatic Recall extraction: select one server

All four candidates use AgentsView's native `[recall.extract]` configuration.
Start with `candidate_findings = "block"`; a full secret scan is still required
before a session can be sent. Keep the key in the service environment, never
in TOML. The examples enable the feature; place **only one** `[recall.extract]`
block in the service config. Replace the model in a proxy profile with an exact
ID returned by its authenticated `/v1/models` endpoint.

OpenRouter free model that passed the isolated one-session extraction:

```toml
[recall.extract]
enabled = true
model = "nvidia/nemotron-3-super-120b-a12b:free"
server = "openrouter"
candidate_findings = "block"

[recall.extract.servers.openrouter]
endpoint = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
timeout = "120s"
```

Use an exact model ID here. `openrouter/free` routes each request to an
available free model; it passed `doctor` but failed a full synthetic-session
extraction on 2026-10-09 because the response violated AgentsView's strict
schema. OpenRouter currently lists only a subset of free models with
`response_format` or `structured_outputs` support, and advertised support
alone did not predict the `apodex` probe result. Filter the live model list,
then run both `doctor` and a one-session extraction for every selected ID.
Free status and model behavior can change independently of this recipe. This
route sends eligible transcript content to OpenRouter and the selected model
provider.

### Credential route for the OpenRouter pilot

`OPENROUTER_API_KEY` already exists in the user's top-level fnox config and
interactive dotfiles shell. The `codex_research` profile deliberately excludes
top-level secrets with `--no-defaults`, so checking that profile alone does
not test OpenRouter availability. In this noninteractive task, the top-level
secret's synced age cache could not decrypt because its identity file was
unavailable. A minimal fnox profile containing **references only** to the
existing Keychain-backed `DOPPLER_TOKEN` and Doppler-backed
`OPENROUTER_API_KEY`, with no `sync` cache field, resolved the key under
`fnox exec --no-defaults --non-interactive`. The service owner should use that
scoped profile at launch rather than storing the key in TOML or a LaunchAgent
plist. Keep the research profile unchanged; its source allowlist has a
different purpose.

The scoped profile has this **reference-only** shape. Fill the provider
selectors and Keychain lookup name from the existing fnox config; none of the
placeholders is a credential. Do not copy the existing `sync` fields into it.

```toml
[providers.recall_keychain]
type = "keychain"
service = "EXISTING_KEYCHAIN_SERVICE"

[providers.recall_doppler]
type = "doppler"
project = "EXISTING_DOPPLER_PROJECT"
config = "EXISTING_DOPPLER_CONFIG"

[profiles.agentsview_recall.secrets.DOPPLER_TOKEN]
provider = "recall_keychain"
value = "EXISTING_KEYCHAIN_LOOKUP_NAME"
env = false

[profiles.agentsview_recall.secrets.OPENROUTER_API_KEY]
provider = "recall_doppler"
value = "OPENROUTER_API_KEY"
env = true
```

Launch the owner-controlled AgentsView process under `fnox --profile
agentsview_recall --no-defaults --no-daemon --non-interactive exec -- ...`
using that profile. The Doppler token remains an internal provider dependency;
only `OPENROUTER_API_KEY` reaches AgentsView. The active global controller has
not yet been changed to use this launcher.

Claude, Codex, or Antigravity through a loopback CLIProxyAPI instance:

```toml
[recall.extract]
enabled = true
model = "REPLACE_WITH_PROXY_MODEL_ID"
server = "cliproxy"
candidate_findings = "block"

[recall.extract.servers.cliproxy]
endpoint = "http://127.0.0.1:8317/v1"
api_key_env = "AGENTSVIEW_RECALL_PROXY_KEY"
timeout = "120s"
```

CLIProxyAPI offers separate `--claude-login`, `--codex-login`, and
`--antigravity-login` flows and an OpenAI-compatible endpoint. It is a separate
service and credential broker; the already-installed `claude`, `codex`, and
`agy` binaries do not provide its OAuth credentials. The Mac binary is pinned
as `github:router-for-me/CLIProxyAPI@8.0.23` in `mise.toml` and `mise.lock`;
`mise install` makes it available as `cli-proxy-api`, and `cli-proxy-api -h`
checks the installed build without starting a service. All three browser OAuth
flows completed in this pilot; their files are in `~/.cli-proxy-api`, with the
directory at mode `700` and its files at mode `600`. The temporary test proxy
and its generated API key were removed after each probe; no persistent proxy
daemon or production AgentsView setting was added.

For a persistent proxy, bind to `127.0.0.1`, keep its config private, and give
it a separate API key. The key below is a placeholder, not a credential:

```yaml
host: "127.0.0.1"
port: 8317
auth-dir: "~/.cli-proxy-api"
api-keys:
  - "REPLACE_WITH_PRIVATE_PROXY_KEY"
remote-management:
  secret-key: ""
  disable-control-panel: true
```

Expose the same key to the AgentsView service as
`AGENTSVIEW_RECALL_PROXY_KEY`; never place it in AgentsView TOML. Inspect
`/v1/models` through the authenticated loopback endpoint before selecting an
exact model. The tested choices are `claude-haiku-5-5`, `gpt-6-luna`, and
`gemini-3-flash`. For Antigravity, retain a proxy version with its
`response_format=json_schema` fix. Re-run `agentsview recall extract doctor`
and one isolated session when enabling any model in the service environment.

## Activation and rollback

1. Use the global `av-native:status` owner to identify the service and archive.
   Make a protected copy of the existing AgentsView config, then edit its
   existing file without printing credentials. Do not start a second writer.
2. Confirm the chosen key exists **inside the service environment**, and the
   endpoint is reachable. A key visible in an interactive shell does not
   automatically reach the separate LaunchAgent; the scoped fnox launcher
   above needs an owner-managed integration. The project doctor now pins the
   interactive, `codex_research`, and `codex_publish` fnox scopes in
   `doctor.toml`; `mise run doctor-fnox` runs native, presence-only resolution
   for each active scope, including `agentsview_recall` with its OpenRouter and
   local proxy keys. The probe drops inherited secret variables and suppresses
   provider output. The doctor also checks that the LaunchAgent declaration
   selects the scoped fnox profile without embedding keys in its plist. This
   verifies launch wiring; the service owner must still verify the running
   AgentsView process after activation.
3. First run `agentsview recall extract doctor` in an **isolated**
   `AGENTSVIEW_DATA_DIR` using the candidate config. Require exit 0 and a
   structured-output probe for the selected model. In that archive, scan
   eligible sessions with `agentsview secrets scan --backfill`, check
   `agentsview recall extract status`, and run `agentsview recall extract run
   --limit 1`. Inspect the entry and its source evidence. The extraction CLI
   commands are local-only: they refuse `--server`, and manual mutation is
   refused while a daemon owns that archive.
4. Once a provider passes the isolated pilot, coordinate with the global
   service owner to install the config and key environment, run the full
   secret-scan backfill under its single-writer boundary, and restart its
   daemon. Its automatic extraction scheduler handles eligible sessions.
   Do not loosen `candidate_findings` for a remote provider. The current
   `av-native:client` allowlist has no Recall or secret-scan profile, so do
   not imply that it can run these local mutations.
5. Inspect production coverage and entries in the Corpus tab. The native
   `agentsview recall extract activate` command can serve an initial
   collection after one usable session when the daemon is not writing; ask
   the owner to coordinate that step. Review entries before depending on
   trusted-only briefing. Later provider changes create a new generation;
   inspect coverage before activating a replacement.
6. To stop new extraction, set `[recall.extract] enabled = false` and restart
   the owner-managed service. Keep the session archive and the experimental
   Recall corpus intact for comparison; use native generation controls if a
   generation must be retired.

## Pilot acceptance

For each of OpenRouter, Claude-proxy, Codex-proxy, and Antigravity-proxy, record
the endpoint/model identity, `doctor` exit code, one-session extraction exit
code, resulting evidence status, and the exact generation. A successful HTTP
chat response alone is insufficient: the model must honor AgentsView's strict
schema and produce evidence that the host accepts. Do not describe a provider
as working until both probes pass. When a credential or service is unavailable,
record that as `UNVERIFIED`, not as a failed model.

Sources: [AgentsView Recall](https://www.agentsview.io/docs/recall/),
[OpenRouter free router](https://openrouter.ai/openrouter/free),
[OpenRouter API schema](https://openrouter.ai/docs/api_reference/overview),
[OpenRouter model list](https://openrouter.ai/docs/api/api-reference/models/get-models),
[fnox profiles](https://fnox.jdx.dev/guide/profiles.html),
[fnox sync precedence](https://fnox.jdx.dev/guide/sync.html),
[CLIProxyAPI configuration](https://help.router-for.me/configuration/basic),
[Claude OAuth](https://help.router-for.me/configuration/provider/claude-code),
[Codex OAuth](https://help.router-for.me/configuration/provider/codex), and
[Antigravity OAuth](https://help.router-for.me/configuration/provider/antigravity).
