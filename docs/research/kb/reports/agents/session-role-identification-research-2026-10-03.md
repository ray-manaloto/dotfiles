# How others identify session roles and trigger handoffs: GitHub research behind Option A (2026-10-03)

- **Why:** Ray ruled Option A for the lane discriminator (role by name first, placement from `$.session.root()`, a visible `lane-unplaced`, a feature segment that must contain a letter) on one condition. GitHub issues, PRs, discussions and the saved searches had to be researched first for how others identify session roles and handoff triggers. Ruling relayed by coordinator `28f1a8f7`; the options are in `proposals-session-handoff-automation-defects-2026-10-03.md` (coordinator worktree `coord-28f1a8f7`).
- **Method:**
  - `research-sweep` skill shape: `gh api search/issues` (issues and PRs), `search/code`, discussions over GraphQL, and releases/CHANGELOG through the offline `$CC` corpus.
  - Every row has a control arm.
  - Raw JSON for every query: `.agent/kb/raw/session-role-identification-2026-10-03/` (machine-local). The tracked copies are `docs/research/kb/raw/session-role-identification-research-2026-10-03/probe-summary.json` and the third-party mirrors; the machine-local tree also holds `summary.json` and `issues/*.json` holding verbatim bodies.
- **Saved searches (#1502):** the `research-saved-search` task exists only on the unmerged `feat/1502-saved-searches` branch (`mise.toml:890` there), so it cannot run from main. Instead, the relevant watches from the tracked `docs/research/saved-searches/orchestration-2026-10-02.toml` were re-run directly under the same controls:
  - `orch-issues-claude-code-claude-bg`
  - `orch-issues-claude-code-crosssessioninbound`
  - `orch-issues-claude-code-background-session`
  - `orch-code-claude-agents-json`
  - `orch-code-crosssessioninbound`

## Answer

**Option A survives the research, with one refinement: the name has a native, in-hook source.**

1. **Nobody upstream offers a role primitive.** Claude Code gives hooks no session name in general:
   - #97220 is open (2026-09-25), "Hooks cannot obtain the session display name that ListAgents reports".
   - #36058, "Include session_name in hook input JSON", was closed NOT_PLANNED by the inactivity bot.

   The one documented exception is **`SessionStart`**, whose input carries `session_title`, "the current session title if one is already set, for example via `--name` or `/rename`" (`$CC/hooks.md:1148,1155`; typed at `.claude/types/claude-code.d.ts:9153-9158`, beside `agent_type`). Since every dotfiles session is launched with `-n <name>` (`coordinator_handoff.py:733` `launch_argv`), the hook can capture the name **at start, natively**. That removes the job-record read from the hot path, and the job record becomes the fallback.
2. **Others declare roles at launch rather than inferring them.**
   - The closest third-party orchestrator found, `firstintent/ccteam`, launches each worker as `claude --bg --agent <role>` and refuses an empty role (`crates/ccteam-harness/src/execution/claude_bg.rs:5,200-202,222-223`, mirrored at `docs/research/kb/raw/session-role-identification-research-2026-10-03/ccteam-claude_bg.rs`).
   - That role then appears natively as `agent_type` on the main thread of hook input (`d.ts:597-599`; `$CC/hooks.md` common fields).
   - **We do not adopt it:** `--agent` *replaces the session's agent definition*, meaning its system prompt and tools (`$CC/cli-reference.md:62`). That is a much larger behavioural change than labelling, and 0 of 47 live respawn records carry it (proposals report). It is recorded as the native alternative if the name grammar ever proves insufficient.
3. **Placement must not come from `CLAUDE_PROJECT_DIR` or a shell env.** Upstream confirms what the proposals probe measured:
   - #87890 is open, and staff reproduced it on 2.1.233: after `EnterWorktree`, hooks still see `CLAUDE_PROJECT_DIR` pointing at the original directory.
   - #80692 is open: `EnterWorktree` does not fire `CwdChanged`.
   - #98872 is open: `claude --bg` sessions inherit the **daemon's** env, not the calling shell's, so a launch-time env var cannot carry a role.
   - #99145 is open and was filed today: in a worktree session, settings hooks run with `CLAUDE_PROJECT_DIR` set to the main checkout, while hook input `cwd` is the worktree.
   - Together these back Option A's choice of `$.session.root()`, which follows a worktree move and not a shell `cd` (`d.ts:2362-2368`).
4. **The stale-hook class is a known, unfixed upstream gap.**
   - #97349 is open: "Long-lived worktree sessions silently run stale hook scripts — add a drift signal and an explicit hook script source".
   - #84723 is open: a request for `CLAUDE_AGENT_ROOT_DIR`, because absolute and relative hook paths are each wrong in a worktree.
   - Nothing native is coming, which supports D1 (resolve the CLI from the module's own tree) and the generation-marker reload (ruling 3).
5. **Handoff triggers in the wild are threshold hooks or mods, the same shape as ours.**
   - `samosunaz/agent-skills#70` (open): "A mod tells the agent to run the handoff skill when context use passes a threshold".
   - `yuliang615/claude-cache-guard` has a usage-threshold handoff hook (`src/usage-handoff-hook.js:29-51`, mirrored at `docs/research/kb/raw/session-role-identification-research-2026-10-03/claude-cache-guard-usage-handoff-hook.js`).
   - `samosunaz/agent-skills#66` (open) independently moved worker supervision to "brief as the initial `claude` argument … supervised with `SendMessage` + `notify_when_idle`", the same pattern as our START-by-SendMessage workaround for #1592.
   - Upstream, the native trigger is still only requested: #90089 is open, and #18027 (native context visibility) is open.

## Evidence: probe table (controls first)

| Kind | Role | Query | Count | rc |
|---|---|---|---|---|
| issues | must-hit | `repo:anthropics/claude-code PreCompact` | 444 | 0 |
| issues | known-absent (fresh nonce) | `repo:anthropics/claude-code zq<12 hex>` | 0 | 0 |
| issues | query | `repo:anthropics/claude-code "session name" hook` | 1193 | 0 |
| issues | query | `repo:anthropics/claude-code session_name hook` | 29 | 0 |
| issues | query | `repo:anthropics/claude-code agent_type hook --agent` | 114 | 0 |
| issues | query | `repo:anthropics/claude-code EnterWorktree hook cwd` | 114 | 0 |
| issues | query | `repo:anthropics/claude-code CLAUDE_PROJECT_DIR worktree` | 67 | 0 |
| issues | query | `repo:anthropics/claude-code multiple sessions role orchestrator` | 63 | 0 |
| issues | query | `repo:anthropics/claude-code handoff context threshold` | 152 | 0 |
| issues | query | `repo:anthropics/claude-code session.measure` | 0 (armed by the must-hit; the event is named only in the shipped types, `d.ts:3604`) | 0 |
| issues | saved:`orch-issues-claude-code-claude-bg` | `repo:anthropics/claude-code "claude --bg"` | 509 | 0 |
| issues | saved:`orch-issues-claude-code-crosssessioninbound` | `repo:anthropics/claude-code crossSessionInbound` | 62 | 0 |
| issues | saved:`orch-issues-claude-code-background-session` | `repo:anthropics/claude-code background session` | 6113 | 0 |
| PRs | query | `is:pr "claude code" session handoff hook` | 42113 | 0 |
| PRs | query | `is:pr "claude code" orchestrator worker role session` | 7995 | 0 |
| issues | query | `"claude code" handoff "context" percent hook -repo:anthropics/claude-code` | 1545 | 0 |
| issues | query | `"claude code" coordinator lane worker session naming` | 1613 | 0 |
| code | health | `repo:cli/cli filename:README.md` | 9 | 0 |
| code | known-absent | `"zq<12 hex>" filename:mise.toml` | 0 | 0 |
| code | query | `"agent_type" PreCompact` | 11296 | 0 |
| code | query | `"session_name" handoff` | 11840 | 0 |
| code | query | `"claude --bg" "--agent"` | 1140 | 0 |
| code | saved:`orch-code-claude-agents-json` | `"claude agents --json"` | 5360 | 0 |
| code | saved:`orch-code-crosssessioninbound` | `crossSessionInbound` | 2656 | 0 |
| code | query | `"used_percentage" handoff` | 1552 | 0 |
| discussions | must-hit | `repo:cli/cli extension` | 94 | 0 |
| discussions | known-absent | `zq<12 hex>` | 0 | 0 |
| discussions | query | `"claude code" session handoff` | 345 | 0 |
| discussions | query | `"claude code" orchestrator session role` | 153 | 0 |
| discussions | query | `"claude code" context threshold new session` | 328 | 0 |

**How to read the counts:**
- GitHub search tokenises loosely, so a count is not a relevance count. The top 10 of every row were read (`summary.json`), and only the hits cited above bear on the question.
- No row was rate-limited.
- `anthropics/claude-code` has discussions disabled (sweep report), so discussions were searched across all repos.
- The discussions hits (`siteboon/claudecodeui#1454`, self-healing for hung sessions; `pingdotgg/t3code#7001`, agents messaging sibling threads; `openai/codex#39282`, continuity across tools) were title-level only and add no role primitive.

**Releases:** the offline `$CC/changelog.md` and `hooks.md` are the release record used. `session_title` and `agent_type` on `SessionStart` are documented there (`hooks.md:1148-1155`). No release adds a session name to other hook events (consistent with #97220 being open).

## Effect on the spec (folded into `docs/specs/session-handoff-automation.md` rev 3)

- **Option A stands:** name first, then placement via `$.session.root()`, with `lane-unplaced` and a letter in the feature segment.
- **Refinement:** the hook records `session_title` from `SessionStart` (classic input, `d.ts:9156-9158`) and passes it to `decide` as `--session-name`. Python uses it ahead of the job-record name.
  - **Caveat:** a session renamed after start (`/rename`, or the session-start mod's own pending rename) shows the old title until restart. For that reason the job record (`state.json` `name`) remains the fallback, and a disagreement between the two is logged.
- **Rejected:** `--agent <role>`, because it replaces the agent definition, and launch-time env roles, because of #98872.
- **Corroborated:**
  - D1 and the generation-marker reload (#97349, #84723);
  - the research report's `CLAUDE_PROJECT_DIR` correction (#87890, #99145);
  - the #1592 START workaround pattern (`samosunaz/agent-skills#66`).

## Gaps

- The `research-saved-search` tool (#1502) is unmerged, so the watches were re-run by hand. No `watches.toml` freshness record was written.
- `session_title` on `SessionStart` in a **function** hook (`classic.SessionStart`, as `plugin-health.ts:55` uses) is typed but not live-armed. Arm L1 must log it once.
- Third-party code was read at the cited commits only, not run.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): #97220, #36058, #87890, #80692, #97349, #84723, #99145, #98872, #90089, #18027 read; issue and code searches
- [firstintent/ccteam](https://github.com/firstintent/ccteam): `claude --bg --agent <role>` role launch (`claude_bg.rs`, mirrored)
- [yuliang615/claude-cache-guard](https://github.com/yuliang615/claude-cache-guard): usage-threshold handoff hook (mirrored)
- [samosunaz/agent-skills](https://github.com/samosunaz/agent-skills): #66 (brief-as-argument plus SendMessage supervision), #70 (context-threshold handoff mod)
- [cli/cli](https://github.com/cli/cli): code-search health and discussions must-hit controls only
- [siteboon/claudecodeui](https://github.com/siteboon/claudecodeui), [pingdotgg/t3code](https://github.com/pingdotgg/t3code), [openai/codex](https://github.com/openai/codex): discussion titles only
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): saved searches `orchestration-2026-10-02.toml`, #1502, #1592
