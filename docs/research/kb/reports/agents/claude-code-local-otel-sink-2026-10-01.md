# Claude Code local-only OpenTelemetry sink (macOS, no cloud backend)

Synthesized 2026-10-01 by the `synthesize` node of the research-sweep fan-out
(`claude-code-local-otel-sink-2026-10-01`). Inputs: the planner's claims JSON, the
triage hit list, the code-search rows, seven fan-out manifests, and two offline
mirrors of the caller links. The synthesizer re-grepped both mirrors for every
load-bearing quote, cited by `file:line`, and ran four extra probes of its own:
the `mise registry` grep, `mise ls-remote` on four backends, `gh api` on release
assets, and a standard-vs-resource attribute read. Each probe is labeled
**[synth probe]** and lists its control arm.

## Answer

**Completeness.** No MANDATORY GAPS were supplied, no mirror failed, and the
FAILED READS list is empty. This is not a clean sweep, though. One dependency
source is `empty_unverified`: the anthropics/claude-code discussions query. Many
triage hits were never read. Several parts of the question are not covered by
any primary source in the inputs: supervising the collector, retention for the
raw-body directory, and actually running the collector to install it. See Gaps.
Treat the operational half of this answer as a design proposal, not a verified
recipe.

1. **Claude Code cannot write telemetry to files by itself, so you need a
   collector.** The documented exporter choices are `otlp | prometheus | console
   | none` for metrics and `otlp | console | none` for logs
   (`links/1.md:20-21`). The one exception is the raw API bodies.
   `OTEL_LOG_RAW_API_BODIES=file:<dir>` makes Claude Code write the untruncated
   `<uuid>.request.json` and `<uuid>.response.json` files itself. It also appends
   an `index.jsonl` line per response, carrying `session_id`, `message_uuid`,
   `request_file` and `response_file` (v2.1.274+, `links/1.md:746`, `:1287`).
   That index needs no backend and is the easiest artifact for an agent to read.
2. **Use otelcol-contrib with the `file` exporter as the sink.** The exporter
   writes OTLP JSON by default, or `proto` if configured. It supports
   size-based and age-based rotation (`max_megabytes`, `max_days`,
   `max_backups`, `localtime`) and optional `zstd` compression. It can also
   write to multiple files, choosing the path from a **resource** attribute
   (fileexporter README). otel-desktop-viewer is a viewer, not a file sink.
   Nothing in the inputs shows it writing JSONL, and #159 says it cannot import
   JSON. Use it only as an optional GUI next to the file sink.
3. **Partitioning per project and per session comes from attributes, not from
   settings scope.** Every metric and event carries `session.id` (on by default)
   and `vcs.repository.name`/`vcs.owner.name`. The `vcs.*` attributes need
   `OTEL_METRICS_INCLUDE_REPOSITORY=true` and v2.1.269+ (`links/1.md:456-471`).
   The docs call these attributes on **records**. The fileexporter's `group_by`
   reads a **resource** attribute. So moving `vcs.repository.name` or
   `session.id` into the resource takes a collector processor step. Which
   processor does this (`groupbyattrs`) and its config were not verified in
   this sweep.
4. **Scope: everything telemetry-related must go in shell, user, or managed
   settings.** `CLAUDE_CODE_ENABLE_TELEMETRY`, `OTEL_LOG_RAW_API_BODIES`, and
   `OTEL_LOG_USER_PROMPTS` are each "Ignored in project and local settings".
   For `OTEL_LOG_USER_PROMPTS`, the off values are an exception
   (`links/2.md:268`, `:462`, `:465`). The env-vars page also says project and
   local settings "can't set … the OpenTelemetry exporter variables"
   (`links/2.md:101`). OTel reads its variables once at startup, so a change
   needs a relaunch (`links/2.md:75`). Managed settings that set
   `OTEL_EXPORTER_OTLP_*` remove developer-set values (`links/1.md:61`).
5. **`otelHeadersHelper` is a settings key, not an environment variable.** It
   applies only to `http/protobuf` and `http/json`, not `grpc`
   (`links/1.md:291`). If the helper fails, export stops completely
   (`links/1.md:315`). A loopback collector with no auth does not need it.
6. **Install with mise using the `github:` backend.** Neither tool has a mise
   registry short name, and neither resolves through `aqua:`. The
   `github:open-telemetry/opentelemetry-collector-releases` backend lists
   versions up to 0.162.0 (published 2026-09-29). That release ships
   `otelcol-contrib_0.162.0_darwin_arm64.tar.gz` alongside the `otelcol-otlp`,
   `otelcol-prometheus` and other distributions, so the mise entry needs an
   asset selector that picks contrib. That selection was **not** tested. The
   `github:CtrlSpice/otel-desktop-viewer` backend lists v0.5.0 with a
   `darwin_arm64` tarball **[synth probe]**.
7. **Rotation, retention, and supervision.**
   - **Collector files:** the fileexporter handles rotation and retention
     itself (`max_days` / `max_backups`). Do not delete files it has open:
     #33987 says a deleted open file is never recreated and later writes are
     dropped silently.
   - **Raw-body directory:** Claude Code writes it, and no source in the inputs
     documents rotation for it. It needs its own pruning.
   - **Supervision:** no source in the inputs covers supervision. A launchd
     LaunchAgent is the native macOS mechanism, but that is the synthesizer's
     recommendation and is unsourced in this sweep.
8. **Secret-leak risk is high.** Raw bodies "contain the full conversation
   history, including the system prompt, every prior user and assistant turn,
   and tool results". Enabling them "implies consent to everything the other
   `OTEL_LOG_*` content flags would reveal". Only extended thinking is always
   redacted (`links/1.md:1285`). `user.email` is a standard attribute whenever
   it is available (`links/1.md:456-470`). In this repo every credential lives
   in the shell environment (`.claude/rules/secrets-out-of-the-shell-env.md`).
   Any tool result that ever printed one would therefore be stored unencrypted
   in the body files, outside every repo secret scanner. And because the flag
   is user-scoped, it would cover **every** project, not just this one.

## Evidence

### Claims (claim | URL or file:line | quote)

Two kinds of source appear here and should not be confused. **SHIPS/DOCS** rows
are the vendor's own documentation, which describes shipped behavior.
**THIRD-PARTY** rows are other people writing about the vendor. Issue rows are
field reports with their date. Their open or closed state was not part of the
inputs.

| # | Kind | Claim | URL / file:line | Quote |
|---|---|---|---|---|
| 1 | DOCS | Metrics exporters are otlp/prometheus/console/none, and there is no file exporter | https://code.claude.com/docs/en/monitoring-usage · `links/1.md:20` | "export OTEL_METRICS_EXPORTER=otlp       # Options: otlp, prometheus, console, none" |
| 2 | DOCS | Logs exporters are otlp/console/none | `links/1.md:21` | "export OTEL_LOGS_EXPORTER=otlp          # Options: otlp, console, none" |
| 3 | DOCS (absence) | The page names no file exporter. The synthesizer re-grepped `fileexporter` and `otelcol` and got 0 hits each. Control: `index.jsonl` returned 2 hits on the same file | `links/1.md` (whole file) | n/a (absence) |
| 4 | DOCS | Raw bodies can be inline (`=1`, 60 KB truncation) or written to files (`=file:<dir>`) | `links/1.md:105`, `:1286-1287` | "With `=file:<dir>`, Claude Code writes untruncated bodies to `.request.json` and `.response.json` files under that directory, and the events carry a `body_ref` path instead of the inline body. Ship the directory with a log collector or sidecar rather than through the telemetry stream." |
| 5 | DOCS | File mode appends `index.jsonl` per response, keyed by session_id (v2.1.274+) | `links/1.md:746` | "Claude Code also appends one JSON line to `<dir>/index.jsonl` for each successful response, with the fields `timestamp`, `session_id`, `query_source`, `model`, `request_id`, `message_id`, `message_uuid`, `request_file`, and `response_file`." |
| 6 | DOCS | Raw bodies hold the whole conversation, and only extended thinking is redacted | `links/1.md:1285` | "The bodies contain the full conversation history, including the system prompt, every prior user and assistant turn, and tool results, so enabling this implies consent to everything the other `OTEL_LOG_*` content flags would reveal. Claude Code always redacts Claude's extended-thinking content from these bodies, regardless of other settings." |
| 7 | DOCS | Tool arguments may hold secrets, and the docs leave redaction to the backend | `links/1.md:1278` | "Arguments may still contain sensitive values, so configure your telemetry backend to filter or redact these attributes as needed." |
| 8 | DOCS | Prompts are off by default and turned on with `OTEL_LOG_USER_PROMPTS=1` | `links/1.md:617` (and the Security section) | "User prompt content is not collected by default. Only prompt length is recorded. To include prompt content, set `OTEL_LOG_USER_PROMPTS=1`." |
| 9 | DOCS | Response text has its own flag and falls back to the prompts flag when unset | `links/1.md:631`, `:1277`; `links/2.md:460` | "When this variable is unset, `OTEL_LOG_USER_PROMPTS` is used as a fallback, so set `OTEL_LOG_ASSISTANT_RESPONSES=0` if you want prompt content without response content" |
| 10 | DOCS | `otelHeadersHelper` is a settings key that works over http only | `links/1.md:70`, `:291`, `:299` | "Dynamic headers apply only to the `http/protobuf` and `http/json` protocols. With the `grpc` protocol, Claude Code uses only the static headers variables" |
| 11 | DOCS | A failing helper stops all export | `links/1.md:315` | "If the helper fails or prints output that doesn't meet these requirements, exports fail and your telemetry backend receives nothing from the session until the helper works again." |
| 12 | DOCS | Managed settings override developer-set OTLP variables | `links/1.md:61` | "When you set an `OTEL_EXPORTER_OTLP_*` variable in managed settings, Claude Code removes conflicting developer-set variables at startup and logs a warning in the debug log." |
| 13 | DOCS | Traces are beta and need two flags | `links/1.md:140`, `:151` | "To enable it, set both `CLAUDE_CODE_ENABLE_TELEMETRY=1` and `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, then set `OTEL_TRACES_EXPORTER` to choose where spans are sent." |
| 14 | DOCS | The backend guidance names no local file sink | `links/1.md:1240` | "**Log aggregation systems**: Full-text search, log analysis" |
| 15 | DOCS | The standard attributes include `session.id`, `user.email`, and the opt-in `vcs.*` | `links/1.md:456-471` | "All metrics and events share these standard attributes: … `session.id` … `OTEL_METRICS_INCLUDE_SESSION_ID` (default: true) … `user.email` … Always included when available … `vcs.repository.name` … `OTEL_METRICS_INCLUDE_REPOSITORY` (default: false). Requires Claude Code v2.1.269 or later" |
| 16 | DOCS | Custom resource attributes go both in the resource block and on every record | `links/1.md:342` | "Claude Code attaches these values as attributes on every metric datapoint and event record, in addition to sending them in the OTLP resource block." |
| 17 | DOCS | `CLAUDE_CODE_ENABLE_TELEMETRY` works only in shell, user, or managed settings | https://code.claude.com/docs/en/env-vars · `links/2.md:268` | "Set it in your shell, user settings, or managed settings. Ignored in [project and local settings]" |
| 18 | DOCS | `OTEL_LOG_RAW_API_BODIES` has the same scope limit | `links/2.md:462` | "Set it in your shell, user settings, or managed settings. Ignored in [project and local settings]" |
| 19 | DOCS | `OTEL_LOG_USER_PROMPTS` has the same scope limit, except for off values | `links/2.md:465` | "Ignored in [project and local settings] … apart from the off values that section describes" |
| 20 | DOCS | Project and local settings cannot set the OTel exporter variables | `links/2.md:101` | "Project and local settings can't set some variables, such as `CLAUDE_CONFIG_DIR` and the OpenTelemetry exporter variables." |
| 21 | DOCS | OTel reads its variables only at startup | `links/2.md:75` | "a feature that reads its variables once at startup, such as [OpenTelemetry monitoring], keeps its startup values until you relaunch." |
| 22 | DOCS | The standard OTLP variables are supported | `links/2.md:495` | "Standard OpenTelemetry exporter variables (`OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER`, `OTEL_EXPORTER_OTLP_ENDPOINT`, … `OTEL_RESOURCE_ATTRIBUTES`, and signal-specific variants) are also supported." |
| 23 | DOCS (absence) | Neither page mentions installing the collector, running it as a service, or rotating its files. The synthesizer re-grepped 1.md for `launchd`, `mise` and `rotat` and got 0 hits each. Controls on the same file: `OTEL_LOG_TOOL_DETAILS` and `session.id` both hit | `links/1.md` | n/a (absence) |
| 24 | DOCS (absence) | `otelHeadersHelper` does not appear on the env-vars page (0 hits), while the control `CLAUDE_CODE_ENABLE_TELEMETRY` hit on lines 268 and 495. It is a settings key only | `links/2.md` | n/a (absence) |
| 25 | SHIPS (upstream README) | The fileexporter writes files, rotates them, and compresses them | https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/exporter/fileexporter/README.md | "Writes telemetry data to files on disk... Support for rotation of telemetry files. Support for compressing the telemetry data before exporting... rotation: max_megabytes: 10, max_days: 3, max_backups: 3, localtime: true... compression: zstd" |
| 26 | SHIPS | Rotation renames the file with a timestamp and creates a new file at the original path | same README | "When a file is rotated, it is renamed by putting the current time in a timestamp in the name immediately before the file's extension... A new telemetry file will be created at the original `path`." |
| 27 | SHIPS | The output path can be chosen from a resource attribute (`group_by`) | same README | "Support for writing into multiple files, where the file path is determined by a resource attribute." |
| 28 | SHIPS | The format is OTLP JSON by default, with optional proto and zstd | same README | "format: proto... compression: zstd... compression_params: level: 6" |
| 29 | SHIPS | `otlpjsonfilereceiver` reads the fileexporter's JSON back in | https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/otlpjsonfilereceiver/README.md | "Use the OTLP JSON File receiver to read the data back into the collector (as long as the data was exported using OTLP JSON format)" |
| 30 | ISSUE (field report) | A deleted open file is not recreated, and data is then dropped silently | https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/33987 | "If a currently open file from `fileexporter` is deleted, no new file with the same name will be created and all future entries will be silently discarded" |
| 31 | ISSUE 2026-09-23 | Rotation plus about 1000 directories caused a CPU blow-up | https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/49899 | "When we turned on file rotation, our Otel collector deployment scaled up to 50 replicas (the maximum) and each replica started using 1.5+ CPUs." |
| 32 | ISSUE | `otlpjsonfilereceiver` panics under sustained load | https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/50314 | "the collector panics intermittently (we observe ~2/day)" |
| 33 | ISSUE | A fileexporter line holds a full OTLP JSON envelope | https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/44086 | "{\"resourceMetrics\":[{\"resource\":{},\"scopeMetrics\"..." |
| 34 | ISSUE 2026-05-01 | Raw-body log records arrive without trace_id/span_id | https://github.com/anthropics/claude-code/issues/55269 | "the log records arrive at the collector with **empty `trace_id` and `span_id` fields**" |
| 35 | ISSUE 2026-08-19 | Custom `OTEL_RESOURCE_ATTRIBUTES` never appear on the exported records | https://github.com/anthropics/claude-code/issues/87991 | "Custom `OTEL_RESOURCE_ATTRIBUTES` never appear on Claude Code's own outgoing `claude_code.*` OTLP metrics/logs, regardless of whether they are set via `~/.claude/settings.json`'s `env` key or as a real OS-level environment variable" |
| 36 | ISSUE 2026-05-04 | A non-ASCII value in resource attributes drops **all** telemetry | https://github.com/anthropics/claude-code/issues/55949 | "**no telemetry records reach the OTLP collector** for that run" |
| 37 | ISSUE 2026-04-28 | gRPC ignores the headers produced by `otelHeadersHelper` | https://github.com/anthropics/claude-code/issues/54397 | "the actual gRPC unary requests to the configured endpoint go out **unauthenticated**" |
| 38 | ISSUE 2026-04-18 | OTLP metrics silently did nothing in 2.1.113 | https://github.com/anthropics/claude-code/issues/50567 | "the dynamic require() for them at runtime fails silently inside a try / catch." |
| 39 | ISSUE 2026-07-01 | Since 2.1.191 the logs exporter sends chunked transfer encoding | https://github.com/anthropics/claude-code/issues/72671 | "the OTLP/HTTP **logs** exporter changed from sending `Content-Length` to `Transfer-Encoding: chunked`" |
| 40 | ISSUE 2026-07-24 | A feature request asks for repo, worktree and branch attributes from Desktop | https://github.com/anthropics/claude-code/issues/80745 | "Claude Code exports metrics and events via OpenTelemetry (OTLP), which is great for tracking usage across a team." |
| 41 | ISSUE 2024-12-13 | otel-desktop-viewer cannot import a JSON file | https://github.com/CtrlSpice/otel-desktop-viewer/issues/159 | "I would instead like to upload a file or paste a JSON representation of spans." |
| 42 | THIRD-PARTY (Elastic) | Elastic suggests putting the config in user `~/.claude/settings.json` for local testing | https://www.elastic.co/security-labs/blog/claude-code-cowork-monitoring-otel-elastic | "For local testing, you can put the same configuration in `~/.claude/settings.json` on your own machine before rolling it out organization-wide." |
| 43 | THIRD-PARTY (Elastic) | Elastic's example config sets the tool-details and prompt flags | same | "\"OTEL_LOG_TOOL_DETAILS\": \"1\",\n    \"OTEL_LOG_USER_PROMPTS\": \"1\"" |
| 44 | THIRD-PARTY (B. Lyons) | Transcripts are already written as local JSONL | https://brandontlyons.substack.com/p/instrumenting-claude-code-otel-logging | "Claude Code automatically writes full conversation transcripts to local JSONL files at `~/.claude/projects/<project-hash>/<session-id>.jsonl`." |
| 45 | THIRD-PARTY (aibl.to) | OTel export can capture prompts, responses and file paths | https://aibl.to/blog/claude-code-opentelemetry-not-only-cost-tracking/ | "Claude Code's OTEL_EXPORTER_OTLP_ENDPOINT can capture prompts, responses, tool calls, and file paths — not just costs." |
| 46 | THIRD-PARTY (Dash0) | Dash0 recommends a local collector on port 4317 | https://www.dash0.com/guides/monitoring-claude-code-opentelemetry | "to a local OpenTelemetry Collector listening on port `4317`. the `otlp` exporter." |
| 47 | [synth probe] | No mise registry short name exists for otel tools | `mise registry` (mise 2026.9.18) | 0 lines match `otel\|opentelemetry` out of 1061. Control: `^hk ` → `hk packslip:github.com/jdx/hk aqua:jdx/hk` |
| 48 | [synth probe] | The `github:` backend resolves both tools and `aqua:` resolves neither | `mise ls-remote` | `github:open-telemetry/opentelemetry-collector-releases` rc=0, last 0.162.0. `github:CtrlSpice/otel-desktop-viewer` rc=0, last 0.5.0. Both `aqua:` forms rc=1. Controls: `aqua:jdx/hk` rc=0 (last 2.4.0), and a bogus `aqua:` name rc=1 |
| 49 | [synth probe] | A darwin_arm64 contrib asset exists, and the release bundles several distributions | `gh api repos/open-telemetry/opentelemetry-collector-releases/releases/tags/v0.162.0` | published 2026-09-29T12:34:07Z. `otelcol-contrib_0.162.0_darwin_arm64.tar.gz` (+ `.sha256`, `.sigstore.json`, SBOM) sits alongside `otelcol-otlp_…`, `otelcol-prometheus_…`. Control: bogus tag v0.0.999 → HTTP 404 |
| 50 | [synth probe] | otel-desktop-viewer v0.5.0 ships a darwin_arm64 tarball | `gh api repos/CtrlSpice/otel-desktop-viewer/releases/latest` | v0.5.0, 2026-08-24T20:19:07Z, `otel-desktop-viewer_darwin_arm64.tar.gz` |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `repo:open-telemetry/opentelemetry-collector-contrib path:exporter/fileexporter filename:README.md` | must-hit | planner | 1 | 0 |
| `repo:open-telemetry/opentelemetry-collector-contrib path:exporter/fileexporter rotation` | query | planner | 17 | 0 |
| `repo:open-telemetry/opentelemetry-collector-contrib filename:README.md fileexporter group_by` | query | planner | 1 | 0 |
| `repo:anthropics/claude-code OTEL_LOG_RAW_API_BODIES` | query | planner | 1 | 0 |
| `repo:CtrlSpice/otel-desktop-viewer filename:README.md` | must-hit | planner | 1 | 0 |
| `repo:open-telemetry/opentelemetry-collector-contrib filename:README.md qzvbnx7r4k` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:open-telemetry/opentelemetry-collector-contrib filename:README.md` | must-hit | workflow | 330 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |
| `repo:CtrlSpice/otel-desktop-viewer filename:README.md` | must-hit | workflow | 1 | 0 |

No row was rate-limited. The known-absent arm returned 0 while every must-hit
returned ≥1, so code search could tell present from absent in this run.

Notes:

- No CODE SEARCH NOTES were supplied with the inputs.
- `repo:anthropics/claude-code OTEL_LOG_RAW_API_BODIES` = 1. The anthropics/claude-code
  repo is the issue tracker and plugin repo, not the CLI's source, so this hit is not shipped
  code. Which file matched was not given in the inputs.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| open-telemetry/opentelemetry-collector-contrib | otel collector file exporter jsonl | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/claude-code-local-otel-sink-2026-10-01/deps/open-telemetry--opentelemetry-collector-contrib/1/manifest.json` (issues ok 9; discussions empty_verified; releases empty_verified) |
| open-telemetry/opentelemetry-collector-contrib | claude-code | 0 | `…/deps/open-telemetry--opentelemetry-collector-contrib/2/manifest.json` (issues ok 10; discussions empty_verified; releases empty_verified) |
| open-telemetry/opentelemetry-collector-contrib | otel-desktop-viewer | 0 | `…/deps/open-telemetry--opentelemetry-collector-contrib/3/manifest.json` (issues ok 2; discussions empty_verified; releases empty_verified) |
| anthropics/claude-code | opentelemetry-collector-contrib | 0 | `.agent/kb/raw/research-fanout/claude-code-local-otel-sink-2026-10-01/deps/anthropics--claude-code/1/manifest.json` (issues ok 10; **discussions empty_unverified, "canary returned 0 items"**; releases empty_verified) |
| CtrlSpice/otel-desktop-viewer | opentelemetry-collector-contrib | 0 | `…/deps/CtrlSpice--otel-desktop-viewer/1/manifest.json` (issues ok 3; discussions empty_verified; releases empty_verified) |

The topic fan-outs were `otelcol-file-exporter-jsonl-rotation` (github-issues 1,
firecrawl-developer 10, context7 5; all ok) and
`claude-code-opentelemetry-local-collector-file-exporter` (exa 10, last30days 10,
firecrawl-search 10; all ok).

Every `github-discussions.raw` across the five dependency runs has the same
sha256 (`e56779ec…`). That is consistent with an identical empty payload. The
`releases empty_verified` rows are scoped to the text query, not to "no
releases": the synth probe found real releases for both
opentelemetry-collector-releases and otel-desktop-viewer.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://code.claude.com/docs/en/monitoring-usage | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/raw/claude-code-local-otel-sink-2026-10-01/links/1.md` | 0 | 154419 | — |
| https://code.claude.com/docs/en/env-vars | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/raw/claude-code-local-otel-sink-2026-10-01/links/2.md` | 0 | 170222 | — |

Both caller links were read through these mirrors, which were captured on
2026-10-01. The live pages were not read.

## Conflicts resolved

1. **Do custom `OTEL_RESOURCE_ATTRIBUTES` show up on records?** The docs
   (`links/1.md:342`, fetched 2026-10-01) say they are attached to "every metric
   datapoint and event record" and also sent in the resource block. Issue #87991
   (2026-08-19) says they never appear, whether set in user settings or in the
   OS environment.
   - **Who to trust:** no shipped source code was in the inputs. The docs are
     newer than the issue, and the vendor's docs describe intended shipped
     behavior, so they are trusted for *intent*. The issue's open or closed
     state is unknown, so the conflict stays **open at the runtime level**.
   - **Effect on the design:** do not build partitioning on custom attributes.
     Partition on the standard `session.id` and the documented `vcs.*`
     attributes. Before relying on anything, run a live check with
     `OTEL_LOGS_EXPORTER=console`.
2. **Do repo attributes exist?** #80745 (2026-07-24) asks for repo, worktree
   and branch attributes "from Desktop". The newer docs ship
   `vcs.repository.url.full`, `vcs.owner.name`, `vcs.repository.name` and
   `vcs.provider.name` behind `OTEL_METRICS_INCLUDE_REPOSITORY` (v2.1.269+).
   - The docs are trusted for the CLI.
   - Whether Desktop emits them, and whether branch or worktree attributes
     exist, is not established. Only `vcs.ref.head.*` on a `git commit` tool
     event is documented (`links/1.md:656`).
3. **Correlating raw bodies.** #55269 (2026-05-01) says raw-body log records
   have no trace_id or span_id. The file-mode `index.jsonl` (v2.1.274+,
   documented later) correlates by `session_id`, `message_uuid` and
   `request_id` without needing traces. This is not a contradiction: they are
   different mechanisms. For agent use, prefer `index.jsonl`.
4. **Old export regressions** (#50567 metrics no-op in 2.1.113; #72671 chunked
   logs since 2.1.191). These are older than the docs mirror. They do not show
   whether today's build is affected.
   - #72671 matters only for receivers that *require* `Content-Length`. That
     the otelcol OTLP/HTTP receiver accepts chunked bodies is the synthesizer's
     expectation, not a sourced fact.
   - Using `grpc` to a loopback collector avoids that path. Without a header
     helper, the gRPC header issue in #54397 does not matter.
5. **Third-party versus docs on scope.** Elastic's "put it in
   `~/.claude/settings.json`" is *user* scope, which agrees with
   `links/2.md:268`. Third-party write-ups that mention "settings.json" without
   saying which one should not be read as allowing *project* settings. The docs
   say project and local scope are ignored for these variables.
6. **Is the output JSONL?** The planner's claim says the fileexporter writes
   "JSONL". The quoted README text says "files on disk" with OTLP JSON or proto
   format, and does not say "JSONL". #44086 shows each line is an OTLP envelope
   (`{"resourceMetrics":[…]}`). Treat the output as newline-delimited OTLP JSON
   envelopes, not one record per line. Agents need a
   `jq '.resourceLogs[].scopeLogs[].logRecords[]'` flatten step. Whether one
   line equals exactly one export batch is unverified.

## Verification

Five load-bearing claims were sent to independent refuters (`refute:1/5` to
`5/5`). A critic and an adjudicator then ran; both returned results. UPHELD
list (refuted or misleading verdicts the adjudicator sustained) is **empty**,
so no claim in the Answer or Recommendation was corrected, struck or qualified
as a result of this step. Failed stages: none.

| # | Claim | Refuter | Adjudicator | Final status |
|---|---|---|---|---|
| 1 | No built-in file exporter; metrics otlp/prometheus/console/none, logs otlp/console/none; raw API bodies are the one exception | misleading | overturned | **Confirmed** |
| 2 | Project/local settings ignore ENABLE_TELEMETRY, RAW_API_BODIES, USER_PROMPTS and the OTel exporter variables; startup-only | misleading | overturned | **Confirmed** |
| 3 | `OTEL_LOG_RAW_API_BODIES=file:<dir>` writes untruncated bodies plus `index.jsonl` (v2.1.274+); only extended thinking redacted | misleading | overturned | **Confirmed** |
| 4 | otelcol-contrib file exporter (JSON/proto, rotation, zstd, resource-attribute path); `vcs.repository.name` needs INCLUDE_REPOSITORY (v2.1.269+) plus an unverified move-to-resource step | misleading | overturned | **Confirmed**; the move-to-resource step stays **unverified** (no collector was run) |
| 5 | No mise registry short name and no `aqua:` for otelcol-contrib or otel-desktop-viewer; both resolve via `github:`; asset selection and install untested | not misleading | not disputed | **Confirmed**; asset selection and install stay **unverified** |

Why the adjudicator overturned the refuters' "misleading" calls:

1. **Exporters.** Traces (beta) also have only console/otlp/none
   (`links/1.md:147`), so the conclusion is unchanged, and traces are already
   in evidence row 13. Transcripts (row 44) and `--debug-file` are not OTel
   telemetry.
2. **Scope.** The refuter missed the primary lines: `links/2.md:101` and
   `links/1.md:57` say project and local settings ignore the OpenTelemetry
   exporter variables, and `links/2.md:495` says the same for the variables that
   enable export or pick its destination. Nuance, not a correction: a repository
   can still set an exporter selector to `none`; `OTEL_RESOURCE_ATTRIBUTES` and
   the interval, timeout and compression variables still apply from project or
   local settings. The advice to put enabling and destination variables in user
   or shell scope stands.
3. **Raw bodies.** The scope limit, the consent point and the full `index.jsonl`
   field list are already in the report (Answer 4 and 8, evidence rows 5 and 6).
4. **File exporter.** `groupbyattrs` (or `transform`) is the documented
   candidate for promoting a record attribute to the resource. Two caveats the
   adjudicator recorded: zstd is per-message by default, and `proto` output is
   length-prefixed, so neither is greppable. The Recommendation uses
   `format: json` with no compression, so neither caveat reaches the design.
   `group_by` is off by default, the path must contain `*`, and the README warns
   that field names are not guaranteed stable.
5. **mise.** Refuter probes had control arms (`hk` present; bogus `aqua:` name
   errors identically; aqua-registry has no `pkgs/open-telemetry` or
   `pkgs/CtrlSpice`; bogus tag 404). One residual risk, untested: the
   collector-releases tag list also carries tags such as `cmd/builder/v0.162.0`,
   so the `github:` backend's latest-version pick could land on the wrong tag.

**How the conclusion changes:** it does not. The design (otelcol-contrib file
exporter, user-scope env, loopback-only receiver, raw bodies off by default)
is unchanged. The operational half remains a design proposal; the critic's gaps
below are the work that would turn it into a verified recipe.

Claims not sent to a refuter, and therefore **unverified** beyond the cited
lines: supervision by launchd, raw-body retention, the secret-leak risk ratings,
the 127.0.0.1-only binding, and collector-down behavior.

## Gaps

- **Unverified empty result:** anthropics/claude-code `github-discussions`
  returned `empty_unverified` because its canary returned 0 items. Discussions
  about Claude Code OTel are **unknown**, not absent.
- **Triage hits never read** (their content is unknown):
  - sudopower.com "Capturing Claude Code Session Telemetry with a Local OTel Collector"
  - gist sit/ab1dc2b2…
  - jessitron/claude-collector
  - Arize-ai/claude-code-otlp-collector
  - huanghuiquan/claude-otel, on the mirror host github.laiyagushi.com, which is suspect and should not be trusted without the canonical URL
  - code.claude.com/docs/en/agent-sdk/observability
  - minware.com "How Claude Code Telemetry Works"
  - opentelemetry-collector-contrib #44280 (auto-create the output directory) and #36515 (non-OTLP-JSON log format)
  - otel-desktop-viewer #179 (`go install` broken) and PR #268 (collector 1.63.0)

  Any of these may contain a ready-made local-collector config that this
  report did not see.
- **otel-desktop-viewer storage and export:** whether it persists or exports to
  disk was not read. Only #159 (no JSON import) is in evidence.
- **fileexporter details not verified from a quoted line:**
  - the exact `group_by` keys (`enabled`, `resource_attribute`, `max_open_files`)
  - the `*` placeholder rule in `path`
  - whether `rotation` and `group_by` can be combined in the current version
  - the default `flush_interval`

  #49899 suggests they combine, at a CPU cost.
- **Moving record attributes to the resource:** which processor does it
  (`groupbyattrs` or `transform`) and its config were not researched.
- **Retention for the raw-body directory:** no source documents rotation or
  cleanup for `OTEL_LOG_RAW_API_BODIES=file:<dir>` or its growing `index.jsonl`.
- **Supervision:** launchd, `brew services`, or anything else. No source in the
  inputs covers it.
- **mise install was not run:** the `github:` backend's asset selection when one
  release holds several `otelcol-*` distributions is untested. Pinning
  (`mise.lock` checksum or sigstore) is also untested.
- **Collector-down behavior:** whether Claude Code drops, buffers, or blocks
  when the local collector is not running is undocumented in the sections read.
- **Live end-to-end run:** none. No Claude Code session was pointed at a
  collector during this sweep, so every config below has no control arm.
- **Settings scope for `otelHeadersHelper`:** the settings-reference page was
  not read.
- **No MANDATORY GAPS, MIRROR GAPS, or FAILED READS** were supplied, so none are
  listed.

### Critic gaps (appended by reconcile)

Note: critic gap 1 below is partly answered by the Verification section
(`links/2.md:101`, `links/1.md:57`, `links/2.md:495` state the scope rule), but
the live test and the settings-reference read remain undone.

1. **Settings-scope claim** is stated as fact in the Recommendation, and the
   settings-reference page was never read, so `otelHeadersHelper` scope is
   unverified. Next probe: read the settings and monitoring-usage pages, quote
   the env-var scope rules and the `otelHeadersHelper` entry, then run a live
   test setting `CLAUDE_CODE_ENABLE_TELEMETRY` in project `.claude/settings.json`
   versus `~/.claude/settings.json` against a listening collector.
2. **No end-to-end run.** The fileexporter keys (`group_by`, the `*` path
   placeholder, rotation combined with `group_by`, `flush_interval`) and the
   `groupbyattrs`/`transform` step that moves `vcs.repository.name` and
   `session.id` into the resource are unverified, and per-project partitioning
   rests on this sketch. Next probe: read the v0.162.0 fileexporter README and
   `config.go` at the pinned tag, run otelcol-contrib locally with a minimal
   otlp -> groupbyattrs -> file config, send a synthetic OTLP record and confirm
   per-project files appear; check #49899 for the rotation plus `group_by` CPU
   cost.
3. **Unread triage hits** that may be ready-made recipes: jessitron/claude-collector,
   Arize-ai/claude-code-otlp-collector, the sudopower post, the sit gist,
   agent-sdk/observability docs, collector-contrib #44280 and #36515. The
   anthropics/claude-code discussions query was `empty_unverified`. Next probe:
   fetch each by canonical URL (not the laiyagushi mirror), extract collector
   YAML and env sets, diff against the proposal, and re-run the discussions
   query with a working canary.
4. **mise install path untested.** No `mise install` ran for
   `github:open-telemetry/opentelemetry-collector-releases`, so the asset
   matcher, lock and checksum handling are unverified. Next probe: trial
   install with an `asset_pattern` in a scratch config, then
   `otelcol-contrib --version`.
5. **Supervision and raw-body retention are unsourced design guesses.** No
   LaunchAgent documentation was read; no source covers pruning of
   `OTEL_LOG_RAW_API_BODIES=file:<dir>` or `index.jsonl` growth; the `file:<dir>`
   semantics rest on `links/1.md:746` and `:1287`, v2.1.274+, with no version
   check against the installed `claude`. Next probe: check `claude --version`
   against v2.1.274, run one session with `file:<dir>` to inspect layout,
   growth and permissions (umask), write a launchd plist and verify it with
   `launchctl bootstrap` and `print`, and test a `find -mtime` pruner that skips
   `index.jsonl`.
6. **Collector-down behavior unknown.** The negative gate only shows the file
   does not grow, not that Claude Code stays responsive or that no retry queue
   flushes later. Next probe: start a session with the collector stopped,
   measure startup and turn latency, read stderr and debug logs, restart the
   collector and see whether buffered records arrive.
7. **Secret-leak analysis is asserted, not evidenced.** The "moderate" and
   "high" ratings and the claim that hk scanners see only tracked files have no
   test; no collector redaction or attributes processor was evaluated; the
   127.0.0.1-only binding is unverified. Next probe: run a session with raw
   bodies on, grep the output for a planted canary secret and the
   `Authorization` header, evaluate the redaction/attributes processors, and
   check `lsof -i :4317` for the bind address and the file modes.

## Recommendation

This is a design proposal and has not been run. Ship it as a reviewed change:
a `python/` module plus a mise task, following
`.claude/rules/zero-bash-logic.md` and `.claude/rules/mise-tasks-only.md`.

1. **Install.** Pin
   `"github:open-telemetry/opentelemetry-collector-releases" = "0.162.0"` with an
   asset matcher for `otelcol-contrib_*_darwin_arm64.tar.gz`. Verify the
   matcher with a real `mise install` and lock the result with
   `mise run lock -- "<backend/name>"`. Optionally add
   `github:CtrlSpice/otel-desktop-viewer@0.5.0` as a GUI.
2. **Collector config** (a sketch whose key names need verifying):
   - **Receiver:** `otlp` bound to **127.0.0.1**, gRPC on `:4317` and HTTP on
     `:4318`. Never bind `0.0.0.0`, because prompts travel over this socket.
   - **Processors:** move `vcs.repository.name` and `session.id` into the
     resource (see Gaps), then `batch`.
   - **Exporters:** one `file` exporter per signal under
     `~/.local/state/claude-otel/<signal>/`, with `group_by` on
     `vcs.repository.name` and `format: json`.
   - **Rotation:** `rotation: {max_megabytes: 50, max_days: 14, max_backups: 20, localtime: true}`.
   - **Do not** clean up by deleting the open files (#33987).
3. **Claude Code environment.** Set this in **user** settings `env`, or in the
   shell. Project, local, and `.claude/settings.json` scope are ignored, and
   per the memory rule an agent must not edit user-level files unasked, so the
   operator applies it:
   - `CLAUDE_CODE_ENABLE_TELEMETRY=1`
   - `OTEL_METRICS_EXPORTER=otlp`
   - `OTEL_LOGS_EXPORTER=otlp`
   - `OTEL_EXPORTER_OTLP_PROTOCOL=grpc`
   - `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317`
   - `OTEL_METRICS_INCLUDE_REPOSITORY=true`

   Leave `OTEL_RESOURCE_ATTRIBUTES` unset or ASCII-only (#55949, #87991).
   Relaunch after any change. A per-project mise `[env]` would count as "shell"
   scope. However, `.claude/CLAUDE.md` warns that background launches strip
   shell-exported `CLAUDE_*` variables, so user settings are the robust place.
4. **Content flags: decide one at a time, and leave them off by default.**
   - `OTEL_LOG_USER_PROMPTS=1` is moderate risk.
   - `OTEL_LOG_RAW_API_BODIES=file:~/.local/state/claude-otel/bodies` is
     **high risk**. It is user-scoped, so it covers every project.
   - If you enable raw bodies, keep that directory `chmod 700`, keep it outside
     every repo, and give it its own age-based pruning task (Claude Code does
     not prune it).
   - Never put the directory under a path that git tracks: hk's secret
     scanners only see staged or tracked files.
   - Use `index.jsonl` as the agent-facing index into the body files.
5. **Supervise** with a launchd LaunchAgent (`KeepAlive`, logs to
   `~/.local/state/claude-otel/collector.log`). Have it call
   `mise exec <pinned tool> -- otelcol-contrib --config …`, so a version bump
   does not break the plist path. This part is unsourced and needs its own
   research step.
6. **Gate with both arms.**
   - **Positive:** start a session, then assert that a `claude_code.*` record
     with this repo's `vcs.repository.name` lands in the matching partition
     file within one export interval.
   - **Negative:** with the collector stopped, assert the file does **not**
     grow. This also answers the collector-down gap.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:open-telemetry/opentelemetry-collector-contrib | general-purpose | sonnet | low |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| deps:CtrlSpice/otel-desktop-viewer | general-purpose | sonnet | low |
| mirror:1/2 | general-purpose | haiku | (default) |
| mirror:2/2 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): issues #50567, #54397, #55269, #55949, #72671, #80745 and #87991 (OTel export bugs and scope); its discussions were `empty_unverified`.
- [open-telemetry/opentelemetry-collector-contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib): the fileexporter and otlpjsonfilereceiver READMEs, plus issues #33987, #44086, #49899 and #50314.
- [open-telemetry/opentelemetry-collector-releases](https://github.com/open-telemetry/opentelemetry-collector-releases): synth probe of the v0.162.0 darwin_arm64 assets and the `mise ls-remote` version list.
- [CtrlSpice/otel-desktop-viewer](https://github.com/CtrlSpice/otel-desktop-viewer): issue #159 (no JSON import), the latest release v0.5.0 assets, and the dependency fan-out.
- [cli/cli](https://github.com/cli/cli): the code-search health-check query only.
- [jdx/hk](https://github.com/jdx/hk): control arm for the mise registry and `aqua:` probes only.
- [jessitron/claude-collector](https://github.com/jessitron/claude-collector): surfaced by triage, **not read**.
- [Arize-ai/claude-code-otlp-collector](https://github.com/Arize-ai/claude-code-otlp-collector): surfaced by triage, **not read**.
- [huanghuiquan/claude-otel](https://github.com/huanghuiquan/claude-otel): surfaced through a suspect mirror host, **not read**.
