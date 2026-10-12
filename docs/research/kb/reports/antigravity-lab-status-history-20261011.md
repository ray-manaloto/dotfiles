# Antigravity lab status and session history — 2026-10-11

RESEARCH INCOMPLETE: Context7 returned `Monthly quota reached`; GitHub Discussions remained `empty_unverified` (`canary returned 0 items`); Firecrawl Search returned HTTP 402 and used provisional Serper fallback. The strict-five command exited 1. These gaps limit research coverage; local observations below were independently re-probed.

## Result and freshness

For `/Users/rmanaloto/Downloads/test.results.20260929`, use the existing Antigravity Hub project and conversation/subagent views for live status and history. A timestamped, read-only query of its local summaries database can corroborate recorded state. AgentsView currently lacks this project's Antigravity records.

The latest root refresh at **2026-10-11 20:32:45 UTC / 15:32:45 CDT** selected **19 native conversations: one root and 18 children, all recorded IDLE**, with `not_fully_idle=0` and `killed=0` (query rc=0). The independent verifier captured the same counts/state at 20:29:33 UTC. This is a captured state, not a lasting status or proof of successful delivery. [Independent verifier](agents/antigravity-lab-verifier-20261011.md)

| Capture UTC | Root recorded state | Child state | Root steps and timestamp |
|---|---|---|---|
| 20:25:42 | IDLE | All 18 IDLE | 22,226; modified 20:14:06.309076 |
| 20:28:32 | RUNNING; not_fully_idle=1 | All 18 IDLE | Modified timestamp still 20:14:06.309076 |
| 20:29:13 | IDLE; not_fully_idle=0 | All 18 IDLE | 22,228; modified 20:28:33.115029 |
| 20:29:33 | IDLE; not_fully_idle=0 | All 18 IDLE | Final corroborating snapshot |
| 20:32:45 | IDLE; not_fully_idle=0 | All 18 IDLE | Root refresh before final response; latest modified unchanged |

This transition demonstrates why last-modified time alone cannot establish current execution. The native app displayed quota errors just before 20:29:11 UTC; Send message was disabled and no Stop control appeared in the inspected artifact-focused view. That control observation alone is inconclusive. Recorded RUNNING state and additional steps do not establish productive work or validated changes.

- Root conversation: `3705b3b1-615d-431b-aef7-df2402672cf4`.
- Native project: `0ecf2ca5-234d-4587-9cd1-d106c382b445`.
- Children: research 7, dependency-optimizer 5, research-synthesizer 3, toolchain-architect 2, codebase-architect 1.
- Installed app 2.22.0, agy CLI 1.3.3, AgentsView 0.45.0. The app and language-server processes were alive; process liveness alone cannot attribute active work to this project. [Runtime report](agents/antigravity-lab-runtime-20261011.md)

## Native workflow

1. In the existing Hub window, select the lab project and confirm the exact folder. Open its parent conversation and existing child cards/subagent overview to inspect current lifecycle state.
2. Use Conversation History for earlier sessions, including its archived filter. Cmd+K searches conversation contents; hover reply timestamps for absolute times. Native child cards provide running/waiting/completed state and child navigation. These features are documented in the [current official changelog](https://antigravity.google/docs/changelog/).
3. In an already-existing CLI session, `/agents` monitors that session's children, `/tasks` inspects its non-agent background commands, and `/resume` browses/searches/pages history. These are session interfaces; `agy agents` lists available agent definitions. [Agents](https://antigravity.google/docs/cli/commands/agents/), [background tasks](https://antigravity.google/docs/subagents/), [resume](https://antigravity.google/docs/cli/commands/resume/).

The resume picker can import desktop conversations, but that operation clones context and history. It is unnecessary for passive inspection. `agy -c` can start a fresh session if its workspace cache lacks a valid conversation. Its workspace-keyed cache does not settle the docs' separate directory/project history-filter descriptions; exact picker filtering remains untested.

The offline documentation was captured October 8 and identifies Hub 2.21.1. Live official release notes identify 2.22.0, released October 8; the installed app matches 2.22.0. The offline release-mirror shells are less useful than the complete mirrored changelog. [Offline evidence](agents/antigravity-lab-offline-20261011.md), [official release notes](https://antigravity.google/docs/changelog/).

## Fresh metadata snapshot

This exact-workspace query was independently executed with rc=0. It selects state and attribution metadata only. The database schema is internal and may change; it is not a stable public monitoring API.

```sh
sqlite3 -readonly -header ~/.gemini/antigravity/conversation_summaries.db "
WITH lab AS (
 SELECT conversation_id,parent_conversation_id,status,
        not_fully_idle,killed,last_modified_time,step_count
 FROM conversation_summaries c
 WHERE EXISTS (
  SELECT 1 FROM json_each(
   CASE WHEN json_valid(c.workspace_uris)
        THEN c.workspace_uris ELSE '[]' END
  ) w
  WHERE w.value IN (
   'file:///Users/rmanaloto/Downloads/test.results.20260929',
   '/Users/rmanaloto/Downloads/test.results.20260929'
  )
 )
)
SELECT datetime('now') observed_utc,count(*) records,
       sum(parent_conversation_id='') roots,
       sum(parent_conversation_id!='') children,status,
       sum(not_fully_idle) not_fully_idle,sum(killed) killed,
       max(last_modified_time) latest_modified
FROM lab GROUP BY status;"
```

The control query covered all 247 database records, while the exact-workspace predicate selected 19. An FTS index covered only one lab conversation; it cannot substitute for this full source census.

## AgentsView and existing telemetry

The authenticated custom archive at `127.0.0.1:8080` contained **two** lab sessions: Claude ending October 3 and Codex ending September 30. Adding `--agent antigravity` returned **zero**, rc=0. Children, automated and one-shot records were included. `--active` returned zero but means activity within 15 minutes, not a guaranteed executing-agent census. The source/archive mismatch is 19 native records versus zero imported Antigravity records; the archive's total lab count is two.

```sh
agentsview \
  --server http://127.0.0.1:8080 \
  --server-token-file '/Users/rmanaloto/Library/Application Support/AgentsView-M1-working-b0ae79c5365e-20260915/archive/native-server-token' \
  session list --project test.results.20260929 \
  --include-children --include-automated --include-one-shot \
  --limit 500 --json
```

The command returns session content fields; filter before displaying or saving if only metadata is needed. The installed token-file seam was used without printing credential contents. Default `serve status` reported no server because it addressed another archive namespace. An unauthenticated explicit-server query returned HTTP 401/rc=1 before the credential seam resolved it. No sync or archive repair ran. Missing-ingestion cause remains unverified.

Lab collector and proxy status tasks exited 0, with listeners at 4319 and 8088. The traces command exited 0; its last displayed trace ended 16:53:52 UTC. Those services and traces do not provide a live Antigravity roster. Safe lab probes disabled automatic package/model-generation dependencies:

```sh
mise -C /Users/rmanaloto/Downloads/test.results.20260929 \
  run --no-deps --skip-tools collector:status
mise -C /Users/rmanaloto/Downloads/test.results.20260929 \
  run --no-deps --skip-tools proxy:status
mise -C /Users/rmanaloto/Downloads/test.results.20260929 \
  run --no-deps --skip-tools uv -- \
  run --no-sync doc-sync traces --json --limit 5
```

## Future monitoring seam

Native hooks are documented for Hub, CLI and IDE. Payloads include conversation/workspace attribution; Stop includes termination reason, error and `fullyIdle`, distinguishing remaining asynchronous work. CLI status-line commands additionally receive state JSON whenever the TUI state changes, including conversation ID, workspace, agent state and task count. [Hooks](https://antigravity.google/docs/hooks/), [CLI status line](https://antigravity.google/docs/cli/statusline/).

A metadata-only lifecycle capture could build on those native events, retaining capture time and explicit unknown/stale states. It would still need startup reconciliation, missed-event handling and child coverage verification. This is a proposed seam, not an implemented monitor. No supported global read-only all-surface listing endpoint was established. Headless stream-json observes the run it starts; SDK persistence covers SDK-owned sessions; remote-control daemon status describes connectivity.

## Research routes and limits

The user-mandated credential route ran native `fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec --` around `mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout`, with strict-five, request ID, explicit Last30Days plan and hook output directory. No credentials were printed or persisted.

| Route actually attempted | Observed outcome |
|---|---|
| Exa native API | 10 search results; official status/history documentation discovered |
| Firecrawl Developer | 10 results including AgentsView integration issues |
| Firecrawl Search | Primary HTTP 402; accepted Serper fallback HTTP 200, provisional |
| Last30Days 3.27.3 engine | Explicit GitHub + grounding plan; 8 recent results; other social engines were not claimed |
| Context7 CLI | rc=1; `Monthly quota reached` |
| GitHub issues/releases/discussions | Main receipt Discussions `empty_unverified`, canary zero; separate CLI and SDK repository arms also ran |
| GitHub SDK code search | rc=0/HTTP 200: session query 69, Agent control 124, known-absent control zero; no incomplete-results flag |
| Web tool | Live Google primary docs and official SDK GitHub repository verified |
| Unified computer use | Existing native Antigravity UI observed; no prompt sent |
| Local CLIs | fnox, mise, research-fanout, ctx7, gh, agy help/version, agentsview, sqlite3 and file/process tools |

Applied skills: research-sweep, research-with-verification-gap-fill, Context7 CLI/find-docs, Exa Search guidance, Last30Days, and the installed AgentsView credential guidance in the runtime lane. Exa connector tools were unavailable; the native API route ran. No Exa Agent job or Firecrawl scrape was claimed. The verifier ran fresh local probes and primary-doc checks independently after both lanes returned.

The hook-owned receipt is [manifest.json](/Users/rmanaloto/.codex/research-coverage/01a12c9d-6fe6-7651-a120-7c692351efa1/01a12c9f-c8d5-7370-ada8-e1f6eebe5087/manifest.json); its request ID is `01a12c9f-c8d5-7370-ada8-e1f6eebe5087`. Raw responses and supplemental CLI/SDK GitHub receipts are colocated. Nonzero or empty-unverified arms are blockers, not completed five-provider coverage.

Stop-hook retry at **20:33:57 UTC** reran the same native fnox/mise strict-five command, request ID, Last30Days plan and hook output directory. It again exited **1**. All five groups were inspected: Exa 10 results; Last30Days 8; Firecrawl Developer 10 plus provisional Search fallback 10; Context7 rc=1 with raw `Monthly quota reached`; GitHub issues/releases empty_verified but Discussions empty_unverified with `canary returned 0 items`. Research coverage remains incomplete. The current receipt reflects this retry.

## Evidence and scope

- [Verbatim offline lane](agents/antigravity-lab-offline-20261011.md) and [brief](agents/antigravity-lab-offline-20261011-brief.md).
- [Verbatim runtime lane](agents/antigravity-lab-runtime-20261011.md) and [brief](agents/antigravity-lab-runtime-20261011-brief.md).
- [Verbatim independent verifier](agents/antigravity-lab-verifier-20261011.md) and [brief](agents/antigravity-lab-verifier-20261011-brief.md).

Research reports and an append-only findings record were written in the dotfiles checkout. No lab source/configuration changes, service restart, sync, import, installation, Antigravity agent message or automation creation ran. One verifier archive response initially displayed a first-message field; it was not repeated or persisted in the report, and later probes filtered metadata. Earlier all-idle evidence is retained verbatim and superseded by the timestamped verification above.
