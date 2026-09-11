# Advisor-consult routing

Relocated out of the Claude-specific project config (#994) to keep that file
inside agnix's recommended token budget (CC-MEM-009); its permanent posture was
ratified by the 2026-09-10 `/grilling` pass.

**Advisor consults permanently route to the `codex-advisor` subagent, not
`fable-orchestrator:fable-advisor`** — its reasoning runs on `gpt-5.6-sol` at
`xhigh` via the `codex` CLI. The same permanent routing applies to
`codex-adversarial-critic`, `codex-staleness-auditor`, and
`codex-claude-code-expert` in place of their Claude-backed originals (#884).
The originals remain intact for explicit selection; token availability does not
change the default route. Decision: 2026-09-10 `/grilling` ruling 10.
