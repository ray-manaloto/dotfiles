Independent verification reconciles the lanes as follows: **at 2026-10-11 20:29:33 UTC, the exact lab workspace had 19 native conversation records: one root, 18 children, all recorded idle; not_fully_idle=0 and killed=0.** The authenticated AgentsView archive still had two lab sessions, Claude and Codex, and zero Antigravity sessions. These are two different corpora.

The fresh-status requirement matters: at **20:28:32 UTC**, the root briefly recorded RUNNING/not_fully_idle=1 while all 18 children remained idle. At **20:29:13 UTC** it recorded IDLE again, with step_count increasing from 22,226 to 22,228 and last_modified advancing from 20:14:06.309076 to **20:28:33.115029 UTC**. The final 20:29:33 snapshot corroborated all idle. The earlier lane's all-idle statement was valid at its timestamp but cannot be promoted into a durable status claim.

Root ID is `3705b3b1-615d-431b-aef7-df2402672cf4`; recorded project ID is `0ecf2ca5-234d-4587-9cd1-d106c382b445`. The whole-database control at 20:28:32 counted 247 records, one not_fully_idle and two statuses; the exact-workspace predicate selected 19. Queries and schema inspection used `sqlite3 -readonly`, rc=0. Matching accepted the exact filesystem path and exact file URI, guarding invalid JSON with an empty array.

A reproducible metadata-only snapshot is:

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

This SQLite schema is an internal implementation seam, not an attested stable public API. A recorded RUNNING state proves neither productive work nor delivery. The parent independently reported native quota errors, disabled Send message, and no observed Stop button just before 20:29:11; an artifact tab was focused, so absence of Stop there is inconclusive. I did not reproduce the parent UI observation. The state transition and two added steps can coexist with another quota failure.

The archive's positive control used the existing server at 127.0.0.1:8080 and its installed --server-token-file seam: lab query rc=0/total=2; adding --agent antigravity rc=0/total=0. No token contents were printed. This supports zero imported Antigravity coverage in that archive, not zero Antigravity source history.

Primary docs independently confirmed:

- CLI `/agents` monitors children in the active session and exposes running/done/error/killed; custom-agent selection is a separate section. Changing selection can fork. [Agents documentation](https://antigravity.google/docs/cli/commands/agents)
- CLI `/tasks` covers non-agent background commands; it is not a global agent roster. Hub's subagent panel supports viewing child conversations. [Subagent documentation](https://antigravity.google/docs/subagents)
- CLI `/resume` supports recency, search and paging. Its Antigravity tab can import desktop conversations, but confirmation clones history/context/tool trajectories. This is not passive live attachment. [Resume documentation](https://antigravity.google/docs/cli/commands/resume)
- Hub Conversation History supports grouping, sorting, filtering and archive filtering, and live subagent cards are documented. [Current changelog](https://antigravity.google/docs/changelog)
- Status-line scripting is explicitly CLI-only and receives state on TUI changes. Hooks explicitly apply to Hub 2.0, CLI and IDE. Hub uses workspace .agents/hooks.json or global ~/.gemini/config/hooks.json, inspectable under Settings > Customizations > Hooks. Stop's fullyIdle distinguishes remaining background work; events do not establish current state without recorded timestamps and missing-event handling. [Status line](https://antigravity.google/docs/cli/statusline), [Hooks](https://antigravity.google/docs/hooks)
- The directory-scoped history guide and project guide still describe different scopes: one says cwd-only histories, the other says default-cli-project and resumed conversations adopting their associated project. The workspace-keyed continue cache partly explains this, but actual picker filtering remains untested. [Conversations](https://antigravity.google/docs/cli/conversations), [Projects](https://antigravity.google/docs/projects)

The smallest supported recommendation is to inspect the **existing Hub lab project**, confirm its folder, use its conversation list/history filters for the root and historical sessions, and open its existing subagent panel/cards for child progress. For a fresh machine-readable count, repeat the metadata-only SQLite query and label its timestamp and internal-schema limitation. Use AgentsView for the two imported lab archives; it currently cannot supply this lab's Antigravity history. In an already-existing CLI session, /agents, /tasks and browsing /resume are supported. Starting agy -c or importing desktop conversations is unnecessary for read-only status.

For future automation, the documented cross-surface seam is hooks with conversationId/workspacePaths and Stop terminationReason/fullyIdle. CLI statusLine can supplement it for CLI state. Neither interface was configured or exercised here. A supported global all-surface list endpoint, existing hook effectiveness, event completeness, child-history retention, actual UI refresh interval, and exact picker project filtering remain UNVERIFIED. No custom exporter or service change is justified by this discovery alone.

Actual verifier routes: research-with-verification-gap-fill skill read; rg/cat/ls and sqlite3 metadata probes; authenticated AgentsView CLI; web tool primary-document opens/finds. No Exa/Firecrawl/Last30Days/Context7/GitHub fanout ran in this verifier; the parent's receipt owns those routes. No lab task, sync, import, serve, restart, service/config/code change or external agent message ran. Failed web routes: /docs/conversations and /docs/subagents?tab=antigravity returned tool errors; correct primary paths succeeded. One ad hoc glob read returned rc=1/no matches; targeted report reads succeeded.

Caveat: the first archive CLI response included a first_message field before metadata filtering; its text is neither repeated nor persisted in this report. No transcript files were read. Later status probes were metadata-only.

<oai-mem-citation>
<citation_entries>
MEMORY.md:64-69|note=[prior Antigravity activity claims required fresh verification]
MEMORY.md:227-227|note=[archive evidence kept distinct from runtime authority]
</citation_entries>
<rollout_ids>
</rollout_ids>
</oai-mem-citation>
