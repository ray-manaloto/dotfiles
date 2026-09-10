# Temporary advisor-consult routing

Relocated out of the Claude-specific project config (#994) to keep that file
inside agnix's recommended token budget (CC-MEM-009) — content unchanged, verbatim.

⚠️ **Until Claude tokens reset (from 2026-08-31), advisor consults route to the
`codex-advisor` subagent, not `fable-orchestrator:fable-advisor`** — its reasoning
runs on `gpt-5.6-sol` at `xhigh` via the `codex` CLI, so a consult costs no Claude
tokens. Same for `codex-adversarial-critic`, `codex-staleness-auditor` and
`codex-claude-code-expert` in place of their Claude-backed originals (#884). The
originals are intact and are the ones to use once tokens reset.
