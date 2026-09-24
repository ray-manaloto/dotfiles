# Removal review — STANDARDS axis (2026-09-24)

Scope: dotfiles `3db81d8e...HEAD`, knowledge-base `origin/main...HEAD`. The graph was **stale** (`graphify-health` rc=3, built at 3db81d8e), so I read the source directly. The flags in the codex review command exist: `codex exec review --help` lists `--commit`, `--base` and `--ignore-rules`. `--sandbox` returned a hit in the same probe, which is the control arm.

## Hard violations (a documented standard is broken)

1. **dotfiles `python/src/dotfiles_setup/removed_plugins.py:33-37`.** `_load_json` turns `JSONDecodeError` into `{}`. A corrupt `installed_plugins.json` or `known_marketplaces.json` therefore reads as "not reinstalled". A TOML parse error at `:92` is reported instead, so the module treats the two formats differently. This breaks `probes-need-a-control-arm.md` rule 4: a parse error is not a "no". No test covers it.
2. **dotfiles `.claude/CLAUDE.md:60` and `.claude/skills/codex-sdlc-team/SKILL.md:187`.** Both make a hand-rolled `codex exec ... review` command the standard way to review a Claude-authored diff. That breaks two rules:
   - `mise-tasks-only.md`: a new recurring workflow ships with its mise task.
   - `ai-cli-invocation.md`: use raw CLI forms only when genuinely needed.

   The two copies are also spelled differently: the skill adds `-c 'sandbox_mode="read-only"'`. knowledge-base routes the same review through `mise run kb-codex -- --review`.

## Judgement calls

3. **Stale text, `suites.toml:2405`.** The `codex-only-lanes` description still points to `orchestration.mode-line-declared` "above", but that contract has been deleted. It also still refers to "the plugin skill's review-tier table", and that plugin has been removed.
4. **Duplicated Code.** Two near-copies of `BUILTIN_AGENT_TYPES` and `undeclared_agent_types` exist:
   - dotfiles `tests/test_workflows_js.py:21-50`
   - KB `tests/test_workflow_agent_roster.py:22-46`

   The copies have drifted. The dotfiles regex at `:21` matches single quotes only, so it cannot see `agentType: "x"`. The repos' own pattern is to put a shared check in `kb_setup`, not in test bodies: see "Runner is the SHARED kb_setup.evals" in `mise.toml [tasks.eval]`, and KB `zero-bash-logic.md` § "Why the checks themselves are python".
5. **Duplicated Code / Divergent scope.** The fable-orchestrator ban is implemented twice with different coverage:
   - dotfiles `suites.toml:2456-2463` leaves out `.claude/rules/*.md`.
   - KB `test_no_plugin_references.py:31` includes `.claude/rules/*.md`.
6. **Mysterious Name, `tests/test_verify.py:181`.** `_MODE_LINE` now holds a heading, not a mode line.
7. **Speculative Generality.** The shared engine still carries a live-case axis, but no case in either repo uses it:
   - KB `evals.py`: `LIVE_TIMEOUT` (`:56`) has no other reference, plus `Case.live` (`:142`) and `_cost_skip` (`:1186`).
   - KB `cli.py:105, 672, 741` still advertises and accepts `--live`, which now does nothing.
   - dotfiles `main.py:2649` hard-codes `live=False`.
8. **Shotgun Surgery.**
   - dotfiles `token-routing.md:14` calls itself the "single source" for the escalation triggers. KB `claude-advisor.md:17-19` restates them word for word.
   - The seven-part spec contract is restated in four places: dotfiles `codex-sdlc-team/SKILL.md:159`, KB `orchestrator-routing/SKILL.md:80`, and `premise-verifier.md` in both repos.
   - `rule_sync` checks only that shared agent files exist by name, so none of this wording drift can fail a gate.
9. **Silent skip, `doctor.py:1336`.** The check returns `[]` when `home` is `None` or `names` is missing. This is intended, but a deleted `[removed_plugins]` block gives the same silent green as a clean home.

## GitHub repos touched

_None._ Only the two local repos were read.
