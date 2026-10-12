# Telemetry versus AgentsView — 2026-10-11

The current lab OpenTelemetry file is not a superset of AgentsView. Use native
transcripts/Git for approvals and edit attribution, the existing archive for
discoverable indexed history where ingestion is verified, and traces for
measured instrumented behavior. Raw native agent transcript JSONL is distinct
from project OpenTelemetry trace JSONL. Neither record set alone establishes
full history, applied runtime settings, live activity or successful delivery.

## Evidence and verification

At 22:01 UTC, fresh authenticated explicit-server metadata queries returned
two project archive sessions: Claude three messages ending October 3, Codex
four ending September 30; zero Antigravity sessions; no next page; all rc0.
Queries included children, automated and one-shot sessions. No archive body
review/sync/import occurred. Installed agentsview --version returned v0.45.0,
commit b9d0a207f51ff27b84adbaae2a91b344247079b3. Session/search/usage help
corroborated the read/query capabilities and no-sync usage option.

The [version-pinned Session API][session-api] was read through its local mirror
and live primary documentation. It exposes messages, tool calls, indexed search
and conditional usage/cost estimates. Substring/regex can search tool I/O;
FTS/semantic/hybrid search message content. The [OpenTelemetry trace docs][otel]
describe instrumented operations and span relationships. This does not imply
automatically complete transcript capture. Generic OTLP ingestion support in
AgentsView was not adjudicated; product-wide absence is unnecessary for this
recommendation.

[session-api]: https://github.com/kenn-io/agentsview/blob/v0.45.0/docs/session-api.md
[otel]: https://opentelemetry.io/docs/concepts/signals/traces/

Fresh jq aggregates of the full lab file returned rc0: 612 records/338 traces;
177 GenAI, 101 doctor.probe, 38 MCP, 296 council spans; MCP methods 15 initialize,
15 tools-list, eight tools-call; three input and three output usage fields;
zero events; 215 CLIENT, 397 INTERNAL; 177 openrouter labels. Durations minimum
0.011/maximum 166486.532 ms and overlapping sum 1587491.419 ms. Prior complete
review supplies seven degraded seats, 138 empty completions, 34 fixture council
targets and 32 simulated replies. Original trace size/mtime remained 643230
bytes/October 11 16:53:52 UTC. Prompts/payloads were not printed or semantically
certified safe.

Source control: telemetry.py:315–373 serializes span structure without
resource/session/workspace data; doctor.py:889–919 emits its own probe and
passes on initialization/line-count health. Scoped src/tests compaction search
found telemetry.py:487 definition and test_opentelemetry.py:183 caller. The
zero-event aggregate independently confirms no retained compaction events,
without proving no native agent compaction happened. Operation counts cannot
establish a comprehensive agent command census; missing token data is unknown,
not zero cost.

Refutation checks: ordered message roles/tool archive queries remain absent
from the observed trace schema; archive positive control returns two source
sessions while Antigravity-specific query returns zero. Raw/full-file counts
and schema/attribute-key inspection agree; source definitions/test call provide
positive controls for the compaction search. The recommendation depends on
this bounded corpus and supported surfaces, not an unverified universal
inability to ingest OpenTelemetry.

The OKF handoff report 06 now includes the source-comparison table,
operation/token/duration/compaction/doctor details and missingness rules.
W1/checklist require complementary inputs, attributable joins, deduplication
and preservation of unknowns. No new observability service or source-code
implementation was introduced.

## Research routes and gaps

Applied research-sweep in-lane; no agents spawned. Native fnox profile
codex_research ran mise research-fanout with strict-five, request
telemetry-agentsview-20261011-followup and explicit Last30Days plan. Manifest
generated 21:59:48.446020 UTC, command rc1. Evidence resides in standard
.agent/kb/raw/telemetry-agentsview-20261011/.

| Route | Actual result |
| --- | --- |
| GitHub issues/releases | empty_verified with positive controls5/1 |
| GitHub Discussions | empty_unverified, canary0; subsequent repo API confirms has_discussions=false |
| Exa native API | ok,5results |
| Context7 CLI | rc1,Monthly quota reached |
| Firecrawl Developer | ok,5results |
| Firecrawl Search | HTTP402credits-exhausted; SerperHTTP200,5results,provisional |
| Last30Days plugin CLI | ok,4results,explicit GitHub/grounding plan |
| GitHub code search | HTTP200/rc0,query3/must-hit84/known-absent0; primary result paths read as metadata |
| Firecrawl mirror probe | webclaw fallback rc0,provisional; probe reports HTTPstatus0, not a verified200 receipt |
| Web primary reads | pinned AgentsView API/README, current API, OpenTelemetry traces |
| Local CLIs | agentsview,jq,rg,stat,mise/git/uv/document validators; no app control |

RESEARCH INCOMPLETE: Context7 quota and provisional Firecrawl Search/mirror
routes remain; strict-five exited 1 and is not a successful audit. Disabled
Discussions explain that arm's absence rather than an unsupported no-discussion
conclusion. The initial jq status-key assumption and aggregate bracket typo
failed; corrected structural and aggregate projections exited 0. No credentials
were printed or persisted, no billing changes and no source/service/test/event
mutations occurred.

## GitHub repos touched

- kenn-io/agentsview: exact-version documentation, repo capability API,
  issues/releases/discussions and controlled code searches.

Primary sources govern capabilities; installed help and actual local corpus
govern this recommendation. Indexed archive support does not establish that
this project's records were ingested. Neither historical PASS prose nor trace
status establishes final implementation acceptance.
