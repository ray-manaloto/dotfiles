# The codex SDLC Team: Six Specialists codex Itself Orchestrates

This repo has a codex-side subagent team. A fresh Claude session had **no way to
learn that** before this file existed: a grep for `sdlc` across the whole eager
instruction surface returned ONE hit, in a comment explaining why a gate skips
these files. The team was built, verified working, and invisible.

## The roster

Declared in `.codex/agents/codex-sdlc-*.toml`. ⚠️ The **filenames** carry a
`codex-` prefix the `name` fields do not — codex spawns by `name`.

| `name` | owns | its gate |
|---|---|---|
| `sdlc-dispatcher` | routes, waits, synthesises — never edits | — |
| `sdlc-python-specialist` | `python/src/`, `tests/` | pytest |
| `sdlc-config-specialist` | `.pkl`, `.toml`, `.hcl` | `mise run lint` |
| `sdlc-workflows-specialist` | `.github/workflows/` | `mise run pin-actions` |
| `sdlc-image-specialist` | `.devcontainer/`, Dockerfile | `mise run verify-container-latest` |
| `sdlc-documentation-specialist` | `docs/`, `.claude/rules/`, `AGENTS.md` | `mise run lint-docs` |

## Invocation — `mise run sdlc-team`, never a hand-rolled `codex exec`

```bash
mise run sdlc-team -- request.json    # typed request in, typed dispatch out
```

The request names a spec file and a mode (`review` -> read-only,
`implement` -> workspace-write); everything else has a deterministic default.
The task owns prompt construction, sandbox selection, the Codex argv, detached
launch, timeout supervision and every artifact path — so none of it is retyped
or remembered. It returns immediately with an `SdlcTeamDispatch` (supervisor
pid, resolved argv, prompt/output/log/receipt paths); a detached supervisor
writes `SdlcTeamSettlement` when the run ends. Details: the
`codex-sdlc-team` skill; settlement records claimed versus rollout-observed
specialists and fails closed when that evidence is unavailable or inconsistent.

⚠️ **A hand-rolled `codex exec` for this team is guard-denied** (`hook_guard`
rule `hand-rolled Codex SDLC dispatcher`). That guard sees only the COMMAND
LINE, so it catches an invocation naming an sdlc artifact path and cannot catch
one whose dispatcher address lives only inside a prompt file — use the task
regardless.

⚠️ **The trailing `-` is why the task exists.** Omit it from a hand-rolled call
and codex never reads the prompt; it hangs forever. The task always supplies it.

⚠️ **Under `-s read-only` every repo gate fails for sandbox reasons** (uv cache,
mise state, DNS). That is sandbox noise, not a finding. Tell a read-only lane
NOT to run gates and run them yourself.

⚠️ **The lane owns the checkout while it runs.** Do not edit files it may touch,
and name its allowlist in the spec — `.claude/rules/agent-report-persistence.md`
and the orchestration skill both bind here.

## codex drops an invalid agent file SILENTLY

No error, no exit code, no log line — the agent simply does not exist. This has
already cost six agents once: an `mcp_servers` array, which in `config.toml`
DEFINES servers rather than selecting them by name, made every file invalid.

So a file that "looks fine" is not evidence it loaded. Before hand-writing or
editing any `.codex/agents/*.toml`, use the `codex-schema` skill — the
`#:schema` directive on each file is the pre-flight, and `schemas/codex-agent.json`
is derived from the schema OpenAI publishes (`schemas/sources.toml`).

## Its blind spot, which is yours too

`hook_guard` is a Claude `PreToolUse` hook, so **a codex lane's shell commands
are invisible to all of its rules**. A command the guard would refuse from you
runs unchallenged from a lane. Until that gap is closed, the spec you hand a
lane is the only thing standing in for the guard — state the prohibitions
explicitly rather than assuming they are enforced.

## See also

- `docs/specs/codex-sdlc-subagent-team.md` — design, decisions, verification.
- `.claude/skills/codex-sdlc-team/SKILL.md` — the working detail.
- `.claude/rules/ai-cli-invocation.md` — the CLI flag contract.
