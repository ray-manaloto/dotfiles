# Spec — audit the full `codex exec` flag surface, settle the project-config question, and make the `openai-developers` plugin actually used

## Context you do NOT need to re-derive

The coordinator captured these first. Verify if you doubt them, but do not spend
budget rediscovering them.

**Current dispatch argv** (`python/src/dotfiles_setup/sdlc_team.py`, after commit
`38ed61f`) is exactly:

    codex exec -c model_reasoning_effort="<effort>" -C <workdir> -o <output> -

`-s` and `--ephemeral` were REMOVED on 2026-09-15 and are pinned absent by
`test_no_mode_passes_a_sandbox_or_ephemeral_flag` in `tests/test_sdlc_team.py`
(fail arms measured: re-adding either -> rc=1). **Do not propose re-adding
them** without treating that as a reversal and arguing it explicitly.

**Full `codex exec --help` for the installed codex-cli 0.154.0** is at
`/tmp/codex-exec-help.txt` (112 lines). Regenerate with
`mise exec -- codex exec --help` if you prefer.

## Deliverable 1 — audit EVERY flag, not just the named ones

For each option in `codex exec --help`, return a row: **ADOPT / REJECT /
CONDITIONAL**, the reason, and — for ADOPT — exactly where it goes in
`sdlc_team.py`'s argv and what test pins it.

The operator explicitly named these five. Each needs a real verdict:

| Flag | Help text says |
|---|---|
| `--strict-config` | "Error out when config.toml contains fields that are not recognized by this version of Codex" |
| `--dangerously-bypass-approvals-and-sandbox` | "Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY DANGEROUS. Intended solely for running in environments that are externally sandboxed" |
| `--dangerously-bypass-hook-trust` | "Run enabled hooks without requiring persisted hook trust for this invocation. DANGEROUS. Intended only for automation that already vets hook sources" |
| `--output-schema <FILE>` | "Path to a JSON Schema file describing the model's final response shape" |
| `--json` | "Print events to stdout as JSONL" |

Do NOT stop at those five. The surface also includes `-p/--profile`,
`--ignore-user-config`, `--ignore-rules`, `--worktree`, `--add-dir`,
`--thread-source`, `--enable`/`--disable`, `--skip-git-repo-check`,
`--approve-for-me`, `--oss`, `--local-provider`, `--color`, `-i/--image`, and
the `resume` / `fork` / `review` subcommands. Rule on all of them.

**Three that deserve special attention, with the reason they matter here:**

- **`--output-schema`** — this repo ALREADY has typed lifecycle schemas
  (`schemas/sdlc-team-{request,dispatch,settlement}.json`). A lane's final
  message is currently free prose that `lane_result` parses with a regex, and
  that regex being wrong is a live defect (`lane_result.py:92` rejects codex's
  real `` `name` as `/root/path` `` format). **Would `--output-schema` make the
  self-report parser unnecessary?** That is the highest-value question in this
  deliverable.
- **`--json`** — the DAG's `observed` collector is hard-coded unavailable
  (`sdlc_team.py:477`). JSONL events on stdout are a candidate real source.
  Does the event stream actually carry subagent spawn/stop?
- **`--dangerously-bypass-approvals-and-sandbox`** — ⚠️ we already inherit
  `danger-full-access` from `~/.codex/config.toml`. Is this flag a NO-OP for us,
  or does it additionally skip approvals that the sandbox mode alone does not?
  Answer with evidence, not inference. If it is a no-op, say so and REJECT it.

## Deliverable 2 — settle the project-config question

**The operator's words:** *"`--strict-config` to enforce that `.codex/config.toml`
is correct and used for codex agents — I don't think `.config/config.toml` is
valid."*

Coordinator-established facts:

- `codex exec --help` names **only** `~/.codex/config.toml`, `$CODEX_HOME/config.toml`
  and `$CODEX_HOME/<name>.config.toml` (profiles). **It never mentions a
  project-level `.codex/config.toml`.**
- This repo HAS `.codex/config.toml` (414 bytes) containing only
  `[shell_environment_policy] inherit`.
- This repo's own `.claude/rules/codex-sdlc-team.md` claims project
  `.codex/config.toml` `[shell_environment_policy]` **IS** honoured and
  `.codex/agents/` **IS** read, while project-level `model` /
  `model_reasoning_effort` are **NEVER** honoured (measured 2026-09-10).

**Settle it empirically, both arms:**

1. Does codex load project `.codex/config.toml` at all? Design a probe whose
   two outcomes are distinguishable — e.g. put a deliberately INVALID key in a
   COPY and run with `--strict-config`; if the project file is read, it must
   error. ⚠️ Do NOT corrupt the real file; work on a copy or a temp
   `CODEX_HOME`, and restore anything you touch.
2. If it is NOT read, then `.codex/config.toml` is dead weight and its
   `[shell_environment_policy]` is a **false belief in a shipped rule** — say so
   plainly and name every doc that repeats it.
3. Is `--strict-config` safe to adopt permanently? It errors on unrecognized
   fields, so a codex upgrade could break every lane. State that risk.
4. `-p/--profile` layers `$CODEX_HOME/<name>.config.toml`. **Is a profile the
   supported way to get per-project codex config?** If so, that may be the real
   answer to what the operator wants.

## Deliverable 3 — ⭐ THE PLUGIN REQUIREMENT. Do not dismiss this.

**The operator, verbatim:** *"codex agents should use this plugin to get help w
how to use codex: <https://chatgpt.com/plugins/openai-developers?open_in_app> —
enforce and verify and validate the codex agents actually use this — dont
dismiss this ever."*

Coordinator-established:

- The plugin **IS already installed and enabled**:
  `openai-developers@openai-curated-remote`, version **1.3.0**, id
  `plugin_connector_1p_32dba5a7095c8191adca04ee30276304` (from
  `codex plugin list`, line 822).
- **ZERO agent definitions reference it.** `grep -ril 'openai-developers'`
  across `.codex/`, `.claude/`, `python/`, `docs/` returns nothing. Control arm:
  `model_reasoning_effort` matches 26 files, so the grep works.
- An `.codex/agents/*.toml` declares `name`, `description`,
  `model_reasoning_effort`, `developer_instructions`.

**What to determine, with evidence:**

1. **What does the plugin actually expose to a codex agent?** Tools? Skills? A
   connector the model calls? Inspect the installed plugin under
   `~/.codex/plugins/` and report its real surface — do not infer from the name.
2. **How is a plugin made available to a specific agent?** Check
   `schemas/codex-agent.json` for the key that selects plugins/tools per agent.
   ⚠️ `.claude/rules/codex-sdlc-team.md` records that an `mcp_servers` array in
   an agent file made **all six agents silently invalid** — codex DEFINES servers
   with that key, it does not select them. **Validate any proposed key against
   `schemas/codex-agent.json` before recommending it**, using the `codex-schema`
   skill. A wrong key silently drops the agent.
3. **ENFORCE** — propose the concrete mechanism that makes the agents use it.
   Options to evaluate, not a menu to pick blindly: a line in every agent's
   `developer_instructions`; a per-agent plugin/tool declaration if the schema
   has one; a `hk` gate asserting the reference exists in all six files; a
   `suites.toml` contract.
4. **VERIFY** — propose how we prove an agent ACTUALLY consulted it at runtime,
   not merely that it was told to. ⚠️ This is the hard half and the operator
   asked for it specifically. Candidate evidence: the session rollout in
   `~/.codex/sessions` now persists (as of `38ed61f`), so a `turn_context` or
   tool-call record may show plugin invocation. **If no runtime verification is
   possible, say so explicitly rather than proposing a check that only asserts
   the instruction text exists** — that would be exactly the
   "symptom check instead of capability assertion" that
   `.claude/rules/probes-need-a-control-arm.md` rule 9 forbids.

## Constraints

- You have full access and network. `gh` works.
- **Do NOT write `task_plan.md`** (coordinator-only, no exception). Propose via
  `.agent/plans/task_plan-delta-codex-flags-2026-09-15.md`.
- `findings.md` / `progress.md`: **APPEND only**, never rewrite.
- Persist your report VERBATIM and INCREMENTALLY to
  `docs/research/kb/reports/agents/codex-flag-audit-2026-09-15.md`.
- Do NOT touch git — no commits, branches, pushes.
- Do NOT modify `sdlc_team.py`, its tests, or any `.codex/agents/*.toml`.
  **Propose diffs; the coordinator applies them.** You are the lane whose own
  dispatch path is under audit — editing it mid-run is a conflict.
- Cite `file:line` or command output. An uncited claim is labelled unverified.
- Every negative finding needs a control arm; invent known-absent tokens fresh.
- If the spec contradicts the repo or itself, STOP and report it.

## Deliverable 4 — one recommended argv

End with the single concrete `codex exec` argv you recommend
`sdlc_team.py` build, flag by flag, with the test that should pin each addition
and the fail arm that proves the test works.

## PREMISES (verify before relying on them)

| # | Premise | Where |
|---|---|---|
| P1 | argv today is `exec -c model_reasoning_effort=… -C … -o … -` | `python/src/dotfiles_setup/sdlc_team.py` |
| P2 | `openai-developers` 1.3.0 is installed and enabled | `codex plugin list` line 822 |
| P3 | No agent file references it | `grep -ril 'openai-developers'`; control `model_reasoning_effort` -> 26 |
| P4 | help names no project-level `.codex/config.toml` | `/tmp/codex-exec-help.txt` |
| P5 | codex-cli is 0.154.0 | `mise exec -- codex --version` |
