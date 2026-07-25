# Stream 5 — Telemetry/observability tooling for Claude Code commands (cited)

Agent: general-purpose (web). Findings-bearing; persisted at receipt.
Question: existing tool/plugin/native feature to (A) observe/review every Bash
command in/out of Claude Code, and (B) feed a python scanner that flags one-off
commands. Bias to native + existing; build only the policy logic.

## BLUF
**Standardize the scanner's data source on the transcript JSONL
(`~/.claude/projects/**/*.jsonl`).** It already holds every Bash command
verbatim, is zero-config + retroactive, and the OFFICIAL `fewer-permission-
prompts` skill mines these exact files with the same frequency algorithm. Native
OTel + logging hooks are complementary, not replacements. Capture is solved by
native features; only the policy mapping is custom.

## 1. Transcripts — the prime data source
- Append-only JSONL at `~/.claude/projects/<encoded-path>/<session-id>.jsonl`;
  nothing rewritten/deleted. Lines carry `type`, `uuid`, `parentUuid`,
  `timestamp`, `sessionId`, `cwd`, `gitBranch`, `version`.
- Per Bash call: `type:"assistant"` line → `tool_use` block
  `{id, name:"Bash", input:{command:"…"}}` — **`input.command` = full command
  verbatim.** Paired `tool_result` in a later `type:"user"` line +
  `toolUseResult` (stdout/stderr/exit_code).
- **Stability caveat:** format is community-reverse-engineered, NOT an officially
  versioned schema (simonw: web APIs "unofficial and undocumented", have broken).
  On-disk local JSONL has been stable + is consumed by a first-party skill, but
  no Anthropic schema guarantee → **code defensively** (guarded field access).

## 2. Native OpenTelemetry (complementary, heavier)
`code.claude.com/docs/en/monitoring-usage`: emits PER-TOOL-CALL events, not just
tokens. `claude_code.tool_result` (attrs tool_name, success, duration_ms,
error_type, decision_source; + `tool_parameters` with `bash_command`/
`full_command` ONLY when `OTEL_LOG_TOOL_DETAILS=1` — redacted by default).
`claude_code.tool_decision` (accept/reject + source). Every event carries
`prompt.id` for correlation. Needs telemetry enabled + collector + Grafana →
best for team dashboards, weakest for a local scanner (infra + no history).

## 3. Existing viewers / dashboards (human review — don't build)
- **simonw/claude-code-transcripts** (1.6k★, maintained) — JSONL→clean HTML.
- **daaain/claude-code-log** — Python CLI JSONL→HTML/Markdown.
- **ccbashhistory** (pdenya) — interactive picker extracting EVERY bash command
  Claude ran in a session (closest "show me every command" tool).
- **nitsanavni/bash-history-mcp** — Claude bash history via MCP.
- Grafana dashboards (#25052; timurdigital claudestats) + ccdashboard — aggregate
  usage/tokens via OTel, NOT per-command audit.

## 4. Hook-logging vs transcripts
Anthropic uses "a PreToolUse hook that lets us log skill usage"
(claude.com/blog/lessons-from-building-claude-code). For pure CAPTURE a logging
hook is **redundant with transcripts** (same strings already on disk). A hook
wins only for (a) real-time enforcement/block, (b) a self-owned schema insulated
from transcript drift, (c) structured exit-code without parsing. → add LATER if
the loop graduates from review→enforce; not needed for a batch scanner.

## 5. Scanning prior art — the model to mirror
**Official `fewer-permission-prompts` skill** = direct prior art: finds
transcripts (cap 50 recent sessions), "extracts every Bash and MCP call, grouping
by command + first subcommand", filters to a policy set, writes allowlist to
settings.json. **Our scanner is the INVERSE filter**: same input, same grouping,
opposite verdict — flag mutating one-off shell commands that SHOULD be mise
tasks. Proven, maintained pattern.

## Ranked recommendation
1. **Transcripts** (scanner feed + retroactive history). Build: read `tool_use`
   where name==Bash → `input.command` → group by command+subcommand → flag
   one-off shapes with a mise-task equivalent. Human review: point
   simonw/claude-code-transcripts or ccbashhistory at the same files.
2. **PreToolUse/PostToolUse logging hook** — only if real-time/self-owned schema
   later needed (redundant now).
3. **Native OTel→Grafana** — team dashboards, not the scanner feed.

Build ONLY the policy mapping (one-off→mise-task detection); capture is native.

## Sources
code.claude.com/docs/en/monitoring-usage · /hooks · claude-dev.tools/docs/jsonl-format ·
/docs/transcripts · claude-world.com/tutorials/s16-session-storage ·
github.com/simonw/claude-code-transcripts · github.com/daaain/claude-code-log ·
github.com/NikiforovAll/ccdashboard · github.com/nitsanavni/bash-history-mcp ·
github.com/disler/claude-code-hooks-mastery · pdenya.com/blog/...extract-commands ·
claude.com/blog/lessons-from-building-claude-code-how-we-use-skills ·
claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more ·
wmedia.es/en/tips/claude-code-fewer-permission-prompts ·
github.com/anthropics/claude-code/issues/51057 · /issues/50226 ·
grafana.com/grafana/dashboards/25052-claude-code · quesma.com/blog/... · sealos.io/blog/claude-code-metrics ·
prokopov.me/posts/claude-code-observability-grafana-stack · dev.to/boucle2026/...audit-trail-hook-1g9j

## GitHub repos touched
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — hooks/monitoring docs, fewer-permission-prompts behavior + issues #51057/#50226
- [simonw/claude-code-transcripts](https://github.com/simonw/claude-code-transcripts) — JSONL→HTML viewer; stability caveat source
- [daaain/claude-code-log](https://github.com/daaain/claude-code-log) — JSONL→HTML/MD renderer
- [NikiforovAll/ccdashboard](https://github.com/NikiforovAll/ccdashboard) — OTel dashboard
- [nitsanavni/bash-history-mcp](https://github.com/nitsanavni/bash-history-mcp) — bash history via MCP
- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) — audit-logging hooks
