---
name: codex-sdlc-team
description: Dispatch this repo's typed codex SDLC subagent team through `mise run sdlc-team`. Use when a change spans several domains and needs routed review or implementation, when an independently configured Codex lane should review a diff, or before editing `.codex/agents/*.toml`. The task owns prompt construction, detachment, timeout supervision, Codex argv, and artifact paths; callers provide one typed request and receive one typed dispatch result.
user-invocable: true
---

# Dispatching the codex SDLC team

Six agents in `.codex/agents/codex-sdlc-*.toml` cover dispatch, Python, config,
workflows, images, and documentation. Codex spawns and routes them; callers use
the typed task seam rather than invoking `codex exec` themselves. The eager
summary is `.claude/rules/codex-sdlc-team.md`.

## When this team earns its cost

- A change spans several domains and needs each one checked by its specialist.
- An independently configured Codex lane should review a diff.
- A `.codex/agents/*.toml` file is about to be written or edited.

**When it does not:** a single-file change, work that depends on conversation
context the lane cannot see, or work whose correctness criteria are not yet
settled. Finish the spec before dispatching it.

## Dispatch one typed request

Write an `SdlcTeamRequest` JSON document, then make one task call:

```bash
mise run sdlc-team -- REQUEST.json
```

Pass `-` instead of a filename to decode the request from stdin. A typical
request is:

```json
{
  "spec_file": "/absolute/path/to/spec.md",
  "mode": "implement",
  "effort": "xhigh",
  "timeout_s": 1800,
  "allowlist": [
    "python/src/dotfiles_setup/example.py",
    "tests/test_example.py"
  ],
  "task": "Implement the accepted example contract"
}
```

`spec_file` must be absolute and exist at dispatch. `mode` defaults to `review`;
the mode shapes the prompt only: no `-s` is passed, so every lane runs under the
machine's `danger-full-access` and `review` is asked (not prevented) not to write.
`effort` defaults to `xhigh`, `timeout_s: null` means no timeout, and an empty
`run_id` is generated. Prompt, output, log, and receipt path fields are optional;
omit them to use deterministic defaults.

The task code generates the dispatcher address, spec pointer, licensed-dissent
and test-craft clauses, file allowlist, `COMMIT: caller`, the stop-on-spawn-failure
clause (never "do the work yourself"), the pinned closing-list format, and
the prohibition on piping results into a pager. It also constructs the Codex argv, includes the load-bearing trailing `-`, and launches
the detached supervisor. Do not assemble any of those pieces manually.

## Read the dispatch result

The task returns immediately with `SdlcTeamDispatch` JSON. Keep the whole result:
it contains the run id, dispatch status, supervisor `pid`, resolved Codex `argv`,
mode, start time, errors, workdir, and every resolved prompt, output, log, and
lane-receipt path.

The dispatch statuses are:

- `dispatched` — the detached supervisor owns the run.
- `spec_missing` — no process launched; `pid` is null and `argv` is empty.
- `cli_missing` — Codex was unavailable and no lane launched.
- `invalid_request` — request decoding or validation failed.

`pid` is the supervisor, not the Codex process. The supervisor starts Codex in a
process group, enforces `timeout_s`, and writes the terminal result after Codex
completes, fails, or times out. A successful dispatch is not completion evidence;
the settlement and lane receipt are.

## Keep the two artifact families distinct

Run artifacts belong to this task. By default they are:

- `.agent/sdlc-runs/<run-id>/prompt.md`
- `.agent/sdlc-runs/<run-id>/output.md`
- `.agent/sdlc-runs/<run-id>/codex.log`
- `.agent/sdlc-runs/<run-id>/settlement.json`

The first three may be overridden in the request. the run's `settlement` file is the
typed `SdlcTeamSettlement`: `completed`, `failed`, or `timed_out`, with return
code, Codex child `codex_pid`, finish time, duration, and errors. It is absent
while the run is live. `read_status` returns the recorded terminal status when
the file exists, returns no settled status while the supervisor is alive, and
derives `abandoned` when the file is absent after the supervisor dies.

Settlement records the dispatcher's claimed specialists separately from child
sessions observed in Codex rollout files. A missing parent id, unavailable scan,
zero observed children, or claimed/observed mismatch fails closed even when the
Codex process exits zero; inspect both rosters and the reconciliation errors.

Lane receipts belong to `lane_result`, not to the run-artifact directory. Their
defaults are `.agent/lane-results/<run-id>.json` and
`.agent/lane-results/<run-id>.md`; both resolved paths are returned in the
dispatch JSON and may be overridden with `receipt_json` and `receipt_md`. The
supervisor writes both through the public lane-result composition at settlement.

## Caller responsibilities and measured boundaries

- Treat the allowlist as exclusive ownership while the lane runs. Do not edit
  those paths concurrently.
- Read licensed dissent as a finding about the spec. Do not pressure a lane to
  guess through a contradiction.
- Review mode is intentionally told not to run gates or write its own report;
  nothing but the prompt enforces that. The supervisor still captures output,
  settlement, and lane receipts.
- `hook_guard` denies a visible `codex exec` command that references an SDLC
  artifact path and redirects it to `mise run sdlc-team`. The general piped
  prompt case is not detectable from the command string, so put every required
  prohibition in the spec.
- Codex can silently drop an invalid agent definition. Validate changed agent
  files against `schemas/codex-agent.json` with the `codex-schema` skill.
- Verify a completed lane's claims independently. The output and receipt report
  what the lane said; they do not replace real gate exit codes.

## Schemas

The three lifecycle documents have committed, currency-tested schemas:

- `schemas/sdlc-team-request.json`
- `schemas/sdlc-team-dispatch.json`
- `schemas/sdlc-team-settlement.json`

Use these schemas when another tool produces requests or consumes results. Never
reconstruct the prompt, Codex command, detached process, or artifact layout in a
wrapper.

## See also

- `.claude/rules/codex-sdlc-team.md` — the eager summary.
- `.agents/skills/codex-schema/SKILL.md` — agent schema pre-flight.
- `.claude/rules/ai-cli-invocation.md` — the underlying CLI flag contract.
- `docs/specs/codex-sdlc-subagent-team.md` — design and decision trail.
