The native workflow is Hub’s project/workspace sidebar plus Conversation History for top-level sessions, and `/agents` plus `/tasks` inside an existing CLI session for live child agents and background commands. The offline docs do **not** establish a public host CLI or REST endpoint that lists every running IDE, Hub, and CLI agent together.

Evidence is an offline snapshot retrieved **2026-10-08T06:16:06.442954000Z**, recording Hub **2.21.1**. Current installation and runtime behavior remain unverified. [intel.json](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/intel.json:4)

| Surface | Supported status/history interface | Scope and freshness |
|---|---|---|
| **Hub / Antigravity 2.0** | Sidebar can group by project, status, or recency and show worktree names. Conversation History supports grouping, sorting, filtering, search, Only Unread, and archived conversations. Hub 2.21.1 adds **Cmd+K** content search; reply timestamps show relative time, with absolute time on hover. | Projects may include multiple folders; standalone sessions are separate. Archived rows retain status and last-updated time. No documented refresh interval or complete top-level status vocabulary in the inspected pages. |
| **Hub children** | Live subagent cards show **running, waiting, completed**, and open the child conversation in a side pane. The overview includes nested descendants. | Live UI indicators; no documented retention duration or polling interval. |
| **IDE** | Right-side Agent panel; toolbar above input tracks file changes, running terminal processes, and artifacts. | Conversation-local. These docs do not establish the newer Hub history controls as IDE controls. |
| **CLI children** | `/agents` opens Agent Manager. Subagents are grouped by triggering prompt; rows expose ID, role, live state, and current step. Enter opens child detail; Esc returns. | Existing active session. Live states are **running, done, error, killed**. |
| **CLI shell work** | `/tasks` lists background non-agent processes; selecting a task opens stdout logs. | Session-local background commands, distinct from agent lifecycle. |
| **CLI history** | `/resume` aliases `/switch`, `/conversation`; recency-sorted picker supports title/preview/ID search and older-history paging. | Directory/cache and project behavior have a documentation inconsistency, detailed below. |
| **Remote Control** | Existing connected instance in the browser displays active conversations, plans, and artifacts. `agy remote-control status` reports **daemon status and instance name**. | Daemon/machine connectivity status does not establish agent progress or completion. Interactive terminal instances synchronize in real time. |
| **SDK** | `LocalAgentConfig(save_dir=…, conversation_id=…, app_data_dir=…)` persists/restores SDK sessions. SDK configuration supports dynamic or static subagents. | SDK-owned sessions. Inspected SDK docs do not document enumeration or read-only attachment to all existing Hub/IDE sessions. |

Primary documentation and local anchors:

- Hub identity: [official overview](https://antigravity.google/docs/overview), [local overview:13](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/overview.md:13). Hub is standalone and succeeds the original Agent Manager.
- Sidebar grouping: [official feature deep dive](https://antigravity.google/blog/google-io-2026-feature-deep-dive), [local:28](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/blog/google-io-2026-feature-deep-dive.md:28).
- Hub content search, timestamps, archived status: [official changelog](https://antigravity.google/docs/changelog), [local:21](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/changelog.md:21); History archive filter at **93**, workspace grouping at **105**, Only Unread at **660**, History view/search options at **684**.
- Live cards: [local changelog:172](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/changelog.md:172); nested descendants at [789](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/changelog.md:789).
- IDE toolbar: [official side panel](https://antigravity.google/docs/ide/agent-side-panel), [local:11](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/ide/agent-side-panel.md:11).
- CLI agents: [official `/agents`](https://antigravity.google/docs/cli/commands/agents), [local:74](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/commands/agents.md:74); real-time ID/role/state/step independently corroborated by [local subagents:164](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/subagents.md:164).
- Background commands: [official subagents](https://antigravity.google/docs/subagents), [local:193](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/subagents.md:193).
- History: [official `/resume`](https://antigravity.google/docs/cli/commands/resume), [local:19](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/commands/resume.md:19).
- Remote Control: [official docs](https://antigravity.google/docs/remote-control), [local:124](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/remote-control.md:124).
- SDK persistence: [official lifecycle](https://antigravity.google/docs/sdk/lifecycle), [local:65](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/sdk/lifecycle.md:65). SDK subagents: [official docs](https://antigravity.google/docs/sdk/subagents), [local:17](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/sdk/subagents.md:17).

**Status meanings and completion limits**

- CLI `/agents`: `running` actively executes tools/reasoning; `done` completed its assigned background task; `error` terminal failure; `killed` manually or parent-terminated. A custom agent’s green selection circle means active/prepared, not necessarily executing. [agents:43,83](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/commands/agents.md:83)
- General subagent lifecycle also documents **Idle**: task returned to parent, paused, retains context, and can wake upon a message. **Killed** cannot wake. Do not silently equate the general lifecycle vocabulary with CLI rows. [subagents:99](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/subagents.md:99)
- Hooks provide the strongest explicit completion distinction: `Stop` has `terminationReason` such as `model_stop`, `max_steps_exceeded`, or `error`, and **`fullyIdle=true` means agent plus background commands/asynchronous tasks finished; false means background work remains**. This is an event payload, not an existing global status query. [official hooks](https://antigravity.google/docs/hooks), [local:390](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/hooks.md:390)
- Status-line commands receive state JSON **whenever state changes**: `conversation_id`, launch `cwd`, workspace paths, `agent_state` (`idle`, `thinking`, `working`, `tool_use`, `initializing`), `task_count`, `pending_input_count`, and `tool_confirmation_pending`. This requires configured instrumentation; it is not a standalone list command. [official statusline](https://antigravity.google/docs/cli/statusline), [local:34](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/statusline.md:34)
- Native agent tool `manage_subagents` supports `Action="list"`; `manage_task` supports `list` and `status`. The hooks tool catalog documents these agent tools, without a host CLI/HTTP transport contract. [hooks:158](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/hooks.md:158)
- Headless `agy -p … --output-format stream-json` monitors **the run it starts**, producing `init`, `step_update`, `result`; steps have `ACTIVE`/`DONE`, and child metadata includes ID, role, log URI, workspace URIs. It is not a documented read-only subscription to an already-running session. [official headless](https://antigravity.google/docs/cli/headless), [local:125](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/headless.md:125), child fields at **184**. Final statuses `SUCCESS`, `ERROR`, `CANCELED`, `INTERRUPTED`, `INVALID`, `WAITING`, `RUNNING` are defined at [445](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/headless.md:445); `SUCCESS` means response produced, not independently verified deliverable.

**Project scoping and history caveat**

`agy -c` / `agy --continue` resolves the most-recent ID using a workspace-keyed cache, verifies it with the backend, and may start a fresh session if absent/deleted. `agy --conversation <id>` resumes a specific session. `/resume` can switch to an Antigravity tab, but importing desktop history explicitly **clones** history/context/tool trajectories after confirmation. That import is not passive observation of the existing live desktop agent. [resume:56](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/commands/resume.md:56), [resume:91](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/commands/resume.md:91)

The conversations guide says history is directory-scoped. The projects guide says no flags means `default-cli-project`, `agy --project=<id>` attaches an existing project, and resume adopts the conversation’s associated project. Both can partly coexist through the cache, but the picker’s actual filtering needs runtime verification. [conversations:16](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/cli/conversations.md:16), [projects:68](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/docs/projects.md:68)

**Minimal recommendation**

Inspect the existing Hub instance, group its sidebar by workspace/project, confirm the target folder, then inspect live subagent cards and nested overview. Use Conversation History with archived filtering and timestamp hover for historical freshness. For an already-open CLI session, use `/agents`, `/tasks`, and `/resume` browsing without imports, switching, messages, approvals, or termination.

Remaining runtime questions: installed surface/version; exact project ID and included folders; current sidebar/history filters; whether active sessions are Hub, IDE, CLI, or SDK; whether Remote Control is already enabled; whether completion telemetry already exists; whether picker/import preserves or clones child visibility; and actual refresh behavior.

Only file reads/searches ran (`rg`, `cat`, `nl`, `sed`, `head` through execution tools). No Antigravity runtime, research provider, app, plugin, source sync, gate, credential config, transcript, or patient file was accessed. Release mirror pages show “Loading releases…” ([local:7](/Users/rmanaloto/Downloads/test.results.20260929/offline/antigravity/site/releases_tab_hub_version_2.21.1.md:7)); use the independently mirrored changelog for released feature evidence.

<oai-mem-citation>
<citation_entries>
MEMORY.md:67-69|note=[kept observed activity distinct from verified completion]
</citation_entries>
<rollout_ids>
</rollout_ids>
</oai-mem-citation>
