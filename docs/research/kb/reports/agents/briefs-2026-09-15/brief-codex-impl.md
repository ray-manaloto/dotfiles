# Spec — implement all six steps of the codex-flags delta

Operator ruled **"all six steps now"** (2026-09-15). The audit is done; this is
the build. Source of truth for WHAT to build:
`.agent/plans/task_plan-delta-codex-flags-2026-09-15.md` and its report
`docs/research/kb/reports/agents/codex-flag-audit-2026-09-15.md`.

This spec records the **operator rulings and coordinator measurements that
CHANGE that delta**. Where they conflict, these win.

## Coordinator measurements — use these, do not re-derive

Four arms, run on codex-cli **0.154.0**. Config validation fails at
`thread/start`, BEFORE any model call, so these cost nothing:

| Invocation (bogus key in a temp project `.codex/config.toml`) | rc | Meaning |
|---|---|---|
| `codex exec --strict-config -C <tmp> -` | **1** | errors naming the PROJECT file -> project config IS read + validated |
| `+ --ignore-user-config` | **0** | **DOES suppress** project config validation |
| `+ --ephemeral` | **1** | still errors -> does **NOT** suppress config LOADING |
| clean config (control) | **0** | probe discriminates |

⚠️ **Correct the delta and the report on one point.** They say `--ephemeral`
*and* `--ignore-user-config` suppress project config. Measured: only
`--ignore-user-config` suppresses **loading**. The report's claim is about
shell-policy **APPLICATION**, which these arms do not test — so state the two
separately and do not collapse them. If you test application, say which you
tested.

⚠️ The 2026-09-10 note at `task_plan.md:271`, `.agent/plans/session-2026-09-10.md:38`
and `memory/project_session_2026-09-10.md` says project config is honoured
"regardless of `--ignore-user-config`". **That is now REFUTED on 0.154.0.**
Annotate those as version-bound (they were measured on 0.152.1); do not silently
delete them.

## ⭐ OPERATOR RULING that REPLACES delta step 2's framing

The delta proposes requiring `openai-developers` for OpenAI-API-shaped tasks.
**Keep that.** But the operator ruled the *underlying* need differently:

> *"Find the right codex-help surface instead."*

**It exists and is already on this disk:**

    ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/
      125 markdown files — official vendor docs, offline, greppable

Including `cli__reference.md`, `config-file__config-reference.md`,
`config-file__environment-variables.md`, `agent-configuration__subagents.md`,
`agent-configuration__rules.md`, `hooks.md`, `plugins.md`,
`skills-and-plugins.md`, `build-skills.md`, `sandboxing.md`,
`enterprise__managed-configuration.md`.

This is the **codex half of the corpus `research-doc-sources.md` step 00 already
mandates** — that rule names only the `claude-code` tree today.

⚠️ **Control-armed caveat that MUST be in the instruction you write:** the
corpus LAGS the installed CLI. `--strict-config` appears in **0** corpus files,
while `ephemeral` appears in 10 and `dangerously-bypass` in 4 (invented token ->
0, so the probe discriminates). **Order the sources explicitly:**

1. the offline codex corpus above (cheapest, official, but may lag);
2. `codex exec --help` / `codex <sub> --help` on the INSTALLED binary;
3. the generated `schemas/codex-config.json` / `schemas/codex-agent.json`
   — version-exact, regenerate with `mise run codex-schema-generate`.

For **OpenAI API / Agents SDK / ChatGPT Apps / API-key** tasks, use the
`openai-developers` plugin. It has **no Codex CLI skill** — do not point Codex
CLI questions at it.

## What to build — all six delta steps

Follow the delta. These are the deltas TO the delta:

1. **`--strict-config`** — adopt permanently, exactly as the delta says.
   Operator ruled "yes, permanently". Argv becomes:

       codex exec --strict-config -c 'model_reasoning_effort="<effort>"' -C <workdir> -o <output> -

   ⚠️ Preserve the existing `-s` / `--ephemeral` absence assertions. Add arms:
   a fresh unknown key in a COPIED project config -> rc=1 naming that file; a
   clean copy -> rc=0.

2. **Plugin enablement on all six agents** — the delta's TOML block is
   **coordinator-verified**, both arms, against a temp repo root:

       ARM A  block on all six              -> rc=0
       ARM B  `plugin_names = [...]` at TOP LEVEL -> rc=1 "unexpected key 'plugin_names'"

   ⚠️ TOML is order-sensitive: ARM B only discriminates when the invented key is
   at top level, BEFORE any table. Appended after a table it becomes a child key
   and passes. Write the mutation test that way or it proves nothing.

   The developer instruction must carry BOTH halves: the codex-corpus ordering
   above for Codex questions, and `openai-developers` for OpenAI-API questions.

3. **Runtime consultation verification** — build it as the delta specifies, on
   the plugin's own eval rule (`skills/agents/references/evals.md:3`, *"Record
   which skill files were actually read"*). Walk only descendants of the
   captured parent thread id; require a completed tool/command record reading a
   `SKILL.md` beneath the installed plugin root. **Reject** prompt text, catalog
   presence, plugin-list status, final-message claims, wrong-parent reads.
   Fixtures: valid read, absent read, prose-only claim, wrong-parent, failed
   command, missing agent.

4. **`--output-schema`** — typed final report, per the delta. Adopt only when
   the supervisor decodes the type and fails closed on malformed output. Keep it
   classified SELF_REPORT.

5. **`--json`** — split child stdout from stderr FIRST (current `stderr=STDOUT`
   would corrupt the stream), then parse `thread.started` for the real parent
   thread id.

6. **Doc repair** — per the delta, plus: add the codex corpus to
   `.claude/rules/research-doc-sources.md` step 00, which currently names only
   the claude-code tree.

## Constraints

- Full access, network available.
- **Do NOT write `task_plan.md`.** Propose via
  `.agent/plans/task_plan-delta-codex-impl-2026-09-15.md`.
- `findings.md` / `progress.md`: **APPEND only**.
- Do NOT touch git — no commits, branches, pushes. The coordinator commits.
- Report incrementally to
  `docs/research/kb/reports/agents/codex-impl-2026-09-15.md`.
- **Run the gates** and report REAL exit codes, file-captured, never a piped
  tail: `mise run lint`, `uv run --project python pytest tests/ -x -q`,
  `mise run verify`, `mise run codex-agent-validate`, `mise run codex-schema-check`.
- Every new assertion needs a **realistic** fail arm — delete the wiring, not
  rename a symbol. Prove each fail arm by running it.
- If the spec contradicts the repo or itself, STOP and report it.

## PREMISES

| # | Premise | Where |
|---|---|---|
| P1 | The delta and report exist and are as summarised | `.agent/plans/task_plan-delta-codex-flags-2026-09-15.md` |
| P2 | The four config arms reproduce | re-run them; they are free |
| P3 | 125 codex docs exist offline | `agent-harness-docs/docs/codex/` |
| P4 | The TOML block validates, invented top-level key does not | `codex_agent_validate` on a temp root |
| P5 | codex-cli is 0.154.0 | `mise exec -- codex --version` |
