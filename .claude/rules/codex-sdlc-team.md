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

## Invocation — prompt-triggered, NOT a mise task

This team has no mise task at all. You pipe a prompt to `codex exec`; codex
spawns, routes and closes the threads itself. Address the dispatcher and let it
choose:

```bash
cat prompt.md | mise exec -- codex exec --ephemeral -s read-only -o out.md -
```

Use `-s workspace-write` for implementation. Follow
`.claude/rules/ai-cli-invocation.md` for the flag contract, and re-probe
`codex exec --help` before changing any flag.

⚠️ **The trailing `-` is load-bearing** — without it the prompt is never read and
the call hangs forever.

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
