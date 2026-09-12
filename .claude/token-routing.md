# Advisor-consult routing

Relocated out of the Claude-specific project config (#994) to keep that file
inside agnix's recommended token budget (CC-MEM-009); its permanent posture was
ratified by the 2026-09-10 `/grilling` pass.

**Advisor consults permanently route to a `codex-*-advisor` subagent, not
`fable-orchestrator:fable-advisor`** — its reasoning runs at `xhigh` via the
`codex` CLI. The same permanent routing applies to the `adversarial-critic`,
`staleness-auditor` and `claude-code-expert` roles in place of their
Claude-backed originals (#884). The originals remain intact for explicit
selection; token availability does not change the default route.
Decision: 2026-09-10 `/grilling` ruling 10.

## Two model families, and the name carries the choice (2026-09-11)

Every codex role exists twice: **`codex-sol-<role>`** pinned to `gpt-5.6-sol`
and **`codex-astra-<role>`** pinned to `gpt-6-astra`. **Neither is a default** —
the lane you name is the model you get, which is the whole point of the split.
`codex_agent_parity` fails any lane that pins a model its name does not
advertise, so a dispatch site cannot be silently served the other one.

The sol lanes are AUTHORED; the astra lanes are GENERATED from them by
`mise run codex-lane-mirror` (`-- --check` gates the drift). Edit the sol lane
and regenerate; an edit to an astra lane is overwritten and fails the check.

Ray, 2026-09-11: "we want the ability to use both models". Before this, all five
lanes hard-pinned sol while the user-global codex config had moved to astra —
the pin was written to MATCH global inheritance and silently diverged from it
when global changed.
