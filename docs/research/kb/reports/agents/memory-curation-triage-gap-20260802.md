# Triage of the 20 MEMORY.md entries the fan-out missed — 2026-08-02

Persisted verbatim per `.claude/rules/agent-report-persistence.md`. These 20 `feedback_*`
entries fell between two cohort filters in the `memory-index-curation` workflow and were
triaged by a follow-up agent. Every absence claim below carries its own control arm.

---

## Priority 1 — the five `feedback_omc_*` entries

**Confirmed, with a caveat on the framing.** The reviewer's citations all hold under my own reading:

- `.claude/settings.json:85-107` — 21 plugin entries, `grep -ci 'omc\|oh-my'` over that range → **0** (control: `codex@openai-codex` → 1). Also **0** in `~/.claude/settings.json`'s `enabledPlugins`, and 0 omc skills/agents in this session's listing.
- `.claude/rules/agent-artifact-conventions.md:68` — "the disabled `oh-my-claudecode` plugin and are absent from every session."
- `.claude/rules/notepad-enforcement.md:11-13` — "that plugin is disabled, so they are absent from every session (measured: **0 invocations across 941 transcripts**)."

**But "all five are cut candidates" is too coarse.** Three pieces of OMC infrastructure are still live and independent of the plugin: the `omc` CLI is on PATH (`~/.local/share/mise/installs/npm-oh-my-claude-sisyphus/4.15.7/bin/omc`), the HUD shim is the active statusline (`~/.claude/settings.json:48` → `node $HOME/.claude/hud/omc-hud.mjs`, file present), and `teammateMode` is written in **both** settings files (`.claude/settings.json:141` `"auto"`, `~/.claude/settings.json:184` `"tmux"`). So the five split three ways, and only two are true deletes.

| target | verdict | bytes_freed | reason |
|---|---|---|---|
| `feedback_omc_plugin_dist_build.md` | **delete** | 107 | Self-scoped to OMC **≤4.11.3**; installed is **4.15.7** (`~/.claude/plugins/installed_plugins.json`), and the memory itself says 4.11.4+ force-adds `dist/`. The unbuilt-`dist/` mechanism exists in no installed version. |
| `feedback_omc_autoresearch_tmux.md` | **delete** | 122 | Plugin disabled, `omc autoresearch` used nowhere in the repo, and its state paths (`.omc/state/autoresearch-state.json`) name the tree renamed to `.agent/` on 2026-07-25 per `agent-artifact-conventions.md`. |
| `feedback_omc_hud_shim_discovery.md` | **unindex** | 126 | Not dead — the shim **is** the live statusline. Unindex because the fact is duplicated into `.claude/skills/omc-hud-wrapper-diagnostic/SKILL.md` (line 16 the two-failure-mode conflation, line 44 the `echo '{}' \| node …` probe, line 61 "authoritative shim"), which loads on relevance. That skill's line 68 cites the memory file — so unindex, don't delete. |
| `feedback_omc_launch_required.md` | **unindex** | 104 | Plugin disabled and teammate panes here come from `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, not OMC; `user_omc_preferences.md` (`MEMORY.md:6`) already carries "`omc launch` panes". The CLI still works, so the file stays. |
| `feedback_omc_phantom_teammatemode.md` | **unindex** | 100 | Cut for a *different* reason than plugin-disabled: its central claim ("Claude Code's JSONSchema rejects `teammateMode` as Unrecognized field") is contradicted by the key sitting in both live settings files with agent teams running now. Contested, not dead — don't index it pending a re-probe. |

Five-entry subtotal: **559 bytes**.

## Priority 2 — `feedback_gh_run_watch.md`

**The verifier's grep holds, but the diagnosis inverts.** Arms on the file: `conclusion` → **0**, `cross.verif` → **0**; controls: `exit-status` → **3**, `gh run watch` → **7**. So the probe discriminates and the hook's "cross-verify the conclusion" is not in the file.

It is not *orphaned*, though — that fact is eagerly loaded three times over:

- `gh-cli-watch.md:18-19` — "⚠️ `gh run watch --exit-status` has reported **0 prematurely** — always cross-verify with `gh run view <id> --json conclusion`."
- `verify-before-advancing.md:89-91` — same caveat, with `--jq .conclusion`.
- `do-not.md:26-27` — "**Do NOT trust `gh run watch --exit-status`.** Verify with `gh pr checks <n> --json` or `gh run list --json`."

So migrate-then-unindex is the wrong move: nothing needs to move *into* the file. The real defect is worse and points the other way — **the file contradicts all three rules**, saying `gh run watch` "returns a non-zero exit code on failure so bash can branch on it," i.e. trust it. And both `gh-cli-watch.md:42` ("`# Cross-verify per feedback_gh_run_watch.md:`") and `gh-cli-watch.md:72` / `verify-before-advancing.md:91` cite this memory as the **authority** for a caveat it does not contain. Two eager rules have a dangling citation.

**Correct action: correct-then-unindex** (index line = **100 bytes**). The sentence to fix is in the file's opening paragraph — "and returns a non-zero exit code on failure so bash can branch on it" — which must gain the caveat verbatim from `gh-cli-watch.md:18-19`:

> ⚠️ `gh run watch --exit-status` has reported **0 prematurely** — always cross-verify with `gh run view <id> --json conclusion`.

Alternatively delete the file outright (everything in it is in `gh-cli-watch.md`) and fix the three citations. Either way the citations must not be left pointing at contradicting text. I made no edits.

## The remaining 13

| target | verdict | bytes_freed | reason |
|---|---|---|---|
| `feedback_refer_to_claude_md_not_agents_md.md` | keep | 0 | The AGENTS.md→AGENTS.md layer rule is in **no** rule file (arm `only refer to AGENTS\|AGENTS.md files (any directory)` → 0; control `AGENTS.md` → 9 rule files hit); `hk.pkl:584 claude_agents_md_pairs` checks pairing, not cross-reference targets. |
| `feedback_long_running_command_hangs.md` | unindex | 134 | All facts in eager `long-running-command-hangs.md` rules 1/3/4 — and now wrong: it says the wrapper wraps `hk run pre-commit --all --stash none`; `lint.py:44-45` reads "Read-only gate (no --stash…) Matches CI's `hk run check --all`". |
| `feedback_long_running_tail_logs.md` | unindex | 121 | Actively misleading — tells you to tail `~/.local/state/hk/hk.log`, which the rule (lines 55-57) calls "a *different*, usually stale file… reading it made a live hang look idle"; correct path `~/.local/state/dotfiles/hk-lint.log` at `lint.py:47`. |
| `feedback_long_mac_ops_keep_turn_engaged.md` | unindex | 143 | Verbatim in rule 2's "EXCEPTION — Mac-side container ops: background-and-idle gets them REAPED… in-turn polling", same `deadline=$((SECONDS+540))` loop. |
| `feedback_guard_cd_prefix_already_denied.md` | unindex | 119 | Its own named durable record verified live: `hook_guard.py:478` "# NO `cd`-prefix unwrap, deliberately" + `tests/test_hook_guard.py:196`. |
| `feedback_find_missing_startdir_trips_set_e.md` | keep | 0 | Absent from the eager corpus (arm `missing start dir\|maybe-missing` over `.claude docs scripts` → 0; control `pipefail` → 2 rule files). Cost a container round-trip (#294/PR #295). |
| `feedback_fd_skips_hidden_dirs.md` | keep | 0 | Absent from rules (arm `git ls-files`, `fd skips` → 0 each; control `hk.pkl` → 5 rule files). This repo's dirs are mostly hidden. |
| `feedback_cd_resets_shell_cwd.md` | keep | 0 | Absent from rules (arm `shell cwd\|cwd was reset\|cwd-dependent` → 0; control `mise run` → 3+ rule files). Live now: three working dirs, and `mise run <task>` is cwd-dependent. |
| `feedback_graphify_attached_graph_flag.md` | keep | 0 | Not in the graphify skill (arm `graph=\|attached` in `.claude/skills` → 0; control `graphify` → 156 in `graphify/SKILL.md`). The only guard, `ATTACHED_GRAPH`, is KB-side (`kb_setup/graphify_ops.py:218`) and covers `kb-query` only. |
| `feedback_kb_graphify_claude_only.md` | keep (correction owed) | 0 | Directives live (`knowledge-base/mise.toml:263 kb-query`, `:326 kb-label`), but its rule-2 enforcement claim is false: `graphify` → **0** occurrences in `hook_guard.py` (control `_V4` at line 121), and `scripts/graphify-hook-guard.sh:14` is "advisory (soft mode, no --strict)". |
| `feedback_no_mcp_registration.md` | unindex | 104 | Policy is in `research-doc-sources.md` § "MCP: two lanes", and its cost claim is the sentence that rule retracts (lines 73-78: "Measured 2026-07-30 and false in this harness… 33× difference… **Do not cite the old sentence**"). Also asserts `.mcp.json` "remains", contradicted by `MEMORY.md:13`. |
| `feedback_bundled_workflows_invoke_by_name.md` | keep | 0 | Absent from the eager corpus (arms `bundled workflow` → 0, `Workflow({` → 0, `category` in the probes rule → 0; control `control arm` in that rule → 7). |
| `feedback_mintlify_cache_stale.md` | keep | 0 | **Contradicts** the eager rule and still true. Rule step 0: "the cache is the authoritative source"; arms `stale`/`raw.githubusercontent`/`410` in that rule → 0/0/0 (controls `llms.txt` → 6, `mintlify` → 13). Live probe today: `www.mintlify.com/jdx/mise/llms.txt` → **410**, `raw.githubusercontent.com/…/docs/index.md` → **200**, bogus path → **404**. |
| `feedback_github_app_token_setup_gotchas.md` | keep | 0 | Mechanism live at `refresh.yml:86` and `gcc-sha-repair.yml:60`; the failure chain is only testable in CI, so re-deriving costs workflow runs. |
| `feedback_plan_files_persist.md` | keep | 0 | `~/.claude/plans` exists with 12 files. |

## Totals

Original 20: **1,180 bytes** (10 unindex = 951, 2 delete = 229). Adding `feedback_gh_run_watch.md` at 100 → **1,280 bytes**, but that one is blocked behind correcting the file and the three citations first.

## Open items

`teammateMode` — I proved the key is present in both settings files; I did **not** probe the schema or the current runtime, so "the memory is wrong" is not established, only "not settled enough to index."

`feedback_kb_graphify_claude_only` — I verified the directives and KB tasks but not claim 3 (claude-cli labeling / graphify #2076) or the `clean_env()` backend-stripping detail; those are KB-side and I only confirmed `kb-label` exists.

`feedback_mintlify_cache_stale` — the refresh URL still 410s, but the cache files were refreshed 2026-07-02, so someone found a working path the memory doesn't describe. "Stale-by-default" may now overstate it; the raw.githubusercontent guidance is still right. Worth a one-line update, not a re-verdict.

`feedback_omc_launch_required` — I unindexed on native-agent-teams grounds, but the `omc` CLI is live and the HUD is this user's statusline. If Ray still starts sessions via `omc launch`, that one is a keep and I'd defer.


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.claude/settings.json`, `.claude/rules/**`, `.claude/skills/**`, `python/src/dotfiles_setup/{hook_guard,lint}.py`, `hk.pkl`, `.github/workflows/{refresh,gcc-sha-repair}.yml`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `mise.toml` (`kb-query`, `kb-label`), `kb_setup/graphify_ops.py`.
- [jdx/mise](https://github.com/jdx/mise) — live probe of `www.mintlify.com/jdx/mise/llms.txt` (HTTP 410) against `raw.githubusercontent.com` (200).
