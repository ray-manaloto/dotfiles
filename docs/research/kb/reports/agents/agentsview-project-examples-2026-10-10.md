# AgentsView project examples (2026-10-10)

## Answer

Public projects use AgentsView as a session index and API for live dashboards, agent-history recall, issue/PR traceability, operational reports, and transcript analysis. These repositories contain implementation files or executable scripts; their READMEs do not establish production adoption or compatibility with this host's v0.45.0 archive. The research receipt is incomplete because GitHub Discussions returned an unverified empty result and Context7 reported monthly quota exhaustion. Firecrawl Search was replaced by a provisional Serper result after HTTP 402.

## Implemented examples

| Project | How it uses AgentsView | Evidence and practical limit |
| --- | --- | --- |
| [riclib/omarchy-agentsview](https://github.com/riclib/omarchy-agentsview) | Omarchy bar widget shows active sessions, daily activity, session search, and resume via luvus. | [README](https://github.com/riclib/omarchy-agentsview#readme) documents HTTP snapshots and SSE. Tested by its author against v0.41.1; it checks resume commands against an allowlist. |
| [cpcloud/herdr-agentsview](https://github.com/cpcloud/herdr-agentsview) | Herdr terminal dashboard filters AgentsView activity by project, model, and agent. | [README](https://github.com/cpcloud/herdr-agentsview#readme) and Rust source; accepts authenticated remote base URL, with token supplied outside config. |
| [josix/agent-flow](https://github.com/josix/agent-flow/blob/main/docs/guides/using-agentsview.md) | Claude plugin registers AgentsView MCP; research/planning/review personas search earlier sessions, while write/verify personas are excluded. | [Guide](https://github.com/josix/agent-flow/blob/main/docs/guides/using-agentsview.md) and [MCP startup wrapper](https://github.com/josix/agent-flow/blob/main/scripts/start-agentsview-mcp.sh). It has an opt-out and gracefully degrades when the archive is unavailable. |
| [christoph-jerolimov/agentsview-rhdh-extension](https://github.com/christoph-jerolimov/agentsview-rhdh-extension) | Go CLI wraps a pinned AgentsView binary and finds session references to Jira issues or GitHub PRs. | [README](https://github.com/christoph-jerolimov/agentsview-rhdh-extension#readme) and tests. It post-processes CLI JSON, since AgentsView's Go internals are not an import surface. |
| [Lazymindz/agentsview-hermes-ops](https://github.com/Lazymindz/agentsview-hermes-ops) | Deterministic daily report on usage, failures, retries, health, context strain, and secret-scan counts; optional Hermes script-only cron delivery. | [README](https://github.com/Lazymindz/agentsview-hermes-ops#readme) and [script](https://github.com/Lazymindz/agentsview-hermes-ops/blob/main/scripts/agentsview_daily_summary.py). It calls sync by default, so a shared single-writer deployment should use its `--no-sync` option. |
| [mrojas54/tool-benchmarks](https://github.com/mrojas54/tool-benchmarks) | Uses AgentsView to enumerate multi-agent sessions, then analyzes transcript tool costs, retries, and failure patterns. | [README](https://github.com/mrojas54/tool-benchmarks#readme) documents explicit archive mode, raw-source fallback, timeouts, and corpus fingerprints. It records known Hermes export/listing limitations rather than treating missing data as zero. |
| [ochen1/agentsview-prompts](https://github.com/ochen1/agentsview-prompts) | Exports prompt/final-response pairs and associated commits from the SQLite archive. | [README](https://github.com/ochen1/agentsview-prompts#readme) and Python implementation. Direct read-only database access is more version-sensitive than CLI/HTTP. |
| [sefk/llm-use-charts](https://github.com/sefk/llm-use-charts) | Local charts of daily tokens and costs by model and project, with agent and date filters. | [README](https://github.com/sefk/llm-use-charts#readme) and server/frontend implementation; the server shells out to AgentsView. |

One first-hand usage note, [Simon Willison's custom model pricing example](https://github.com/simonw/til/blob/main/llms/agentsview-custom-model-price.md), shows subscription users adding pricing estimates for a model missing from AgentsView's built-in table. The estimate is a token-price comparison, not a subscription invoice.

## What transfers to dotfiles and knowledge-base

1. Adopt Agent Flow's **persona-limited history lookup** pattern where prior decisions matter, using the already installed AgentsView skill/MCP path. Make search/read evidence available to research, planning, and review roles without injecting it into every worker. This is a recommendation inferred from its design, not a tested change here.
2. Use the RHDH extension's **issue/PR-to-session mapping** as a pattern for handoffs and review provenance. Prefer the installed v0.45.0 CLI JSON or authenticated API over parsing private archive tables; verify exact fields against this version first.
3. Adapt the Hermes report and tool-benchmarks' **read-only quality signals** for an exception-only daily or weekly report. In this environment the active service should own sync; consumers should use no-sync reads. The roborev [cost reconciler issue](https://github.com/kenn-io/roborev/issues/1356) shows why per-job CLI spawning against a large archive needs batching/backoff.

These are candidate workflow changes, not deployed integrations. AgentsView's index should be checked for skipped files and correct child/automated/one-shot inclusion before treating a zero-result search or aggregate as corpus-wide evidence.

## Evidence and gaps

- Strict-five receipt: `/Users/rmanaloto/.codex/research-coverage/01a121d6-bf89-7400-8d7c-80bc02845138/01a12431-44f6-7fa1-9562-393208fd8072/manifest.json`; fanout exited 1. Exa, Firecrawl Developer, and Last30Days answered; Firecrawl Search hit HTTP 402 and used Serper provisionally. Context7 exited 1 with `Monthly quota reached`. The GitHub Discussions arm returned `empty_unverified` because its canary returned zero; a direct GitHub GraphQL control independently reported that kenn-io/agentsview has discussions disabled and zero discussions. GitHub issues and releases arms were `empty_verified` for this specific query; that is not proof the repository has no issues or releases.
- GitHub code search returned 292 hits for `agentsview session filename:README.md`; a fresh nonexistent term returned zero. The broad query includes irrelevant uses of the word, so every cited project was checked at its own source. Topic searches for AgentsView plus `agent-observability`, `llm-observability`, or `claude-code-plugin` returned zero; a `claude-code-plugin` topic-only control returned 9199, so these topic filters were unproductive rather than broken.
- Public source establishes that code/docs exist, not that an integration has been run here or is popular. No third-party example was installed or executed for this report. No changes were made to the active AgentsView service or archive.

## GitHub repos touched

`kenn-io/agentsview`, `riclib/omarchy-agentsview`, `cpcloud/herdr-agentsview`, `josix/agent-flow`, `christoph-jerolimov/agentsview-rhdh-extension`, `Lazymindz/agentsview-hermes-ops`, `mrojas54/tool-benchmarks`, `ochen1/agentsview-prompts`, `sefk/llm-use-charts`, `kenn-io/roborev`, `simonw/til`.
