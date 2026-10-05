# gfy-T3 spec review (mattpocock Spec axis) — `origin/main...1e7a2911`

Spec: `graphify-plan` worktree `docs/specs/graphify-0976-plan-2026-10-04.md` §3 T3, §4, §7 + coordinator lane brief. Read-only review; no source edited.

## (a) Missing / partial

1. **The real `status` run doesn't match HEAD.** The spec asks for this lane to be "tested with fixtures AND one real read-only `status` run". `gfy-T3-report.md` admits that "The real-run sections below were captured at 6b4719f7 and predate the fixes". The output there shows only the 2-term probe (`openai-cli=0 fallback-backend=0`). The shipped 5-term probe (`_run_semantic_extract`, `UNWIND $rows`, `_codex_resolvable_disable_args`) and the host-first plan order have never been run for real. Fix: re-run `status`/`plan` on HEAD and replace those sections.
2. **The fork replay isn't printed as an exact command.** The spec says the tool "prints the exact `git rebase --onto` and stops". The preview line contains a placeholder `mise -C <fork-maintenance checkout>` (`graphify_fleet.py:535`), and the rebase falls back to `'<old base tag>'` when `base_ref` is missing (`:545`). The rebase is exact on the real KB, where `base_ref = v0.9.57`. The preview line is not.

## (b) Not asked for (scope creep)

1. **The host leg goes beyond D1.** The spec says "`--leg host` → prints the D1 command". D1 is `uv tool uninstall graphifyy`. `_host_commands` (`:564-572`) also prints `mise use -g pipx:graphifyy@<latest>` and `exec $SHELL`. It also marks the host leg `behind` whenever the user-global pin is older than upstream. This is reasonable, but it wasn't requested.
2. **Extra CLI flags.** `--kb-root/--kb-ref/--fork-root/--mise-global-config` (`:691-694`) weren't asked for. They do enable the control arms. INFO.
3. **Three review receipts outside the allowlist.** `gfy-T3-codex-review-{6b4719f7,eb6fb8bd}.md` and `gfy-T3-cold-review-6563119b.md` are covered by `agent-report-persistence.md`. INFO only.

## (c) Implemented, but looks wrong

1. **`apply --leg dotfiles` doesn't enforce the order `plan` relies on.** `plan` puts host first because `graphify-upgrade`'s closing check "fails the dotfiles step after it has already moved the lock" (`:96-98`). `apply_leg` (`:678-685`) runs `graphify-upgrade` without checking the host leg. Run directly, it can leave a moved lock behind a red rc. Fix: gate on the host state, or document the precondition in the SKILL.
2. **The two orderings disagree.** The per-leg comment says "Drift outranks behind" (`:188`). The fleet verdict severity (`_SEVERITY`, `:90-95`; SKILL "unverifiable > behind > drift") ranks behind above drift. Both exit rc=1, so the impact is wording only. Pick one.
3. **`_git` treats any stderr as failure even when rc=0** (`:275`). A benign git warning would turn the KB leg or fork probe UNVERIFIABLE. This fails closed, so it's low severity.

Met: status/plan/apply verbs; kb refuses until T8 (rc=2); host never runs; dotfiles delegates to `graphify-upgrade`; reuses `check`/`_path_binary_probe`; the probe has a `claude-cli` control arm; schema → codegen job → generated models; mirror is byte-identical; docstring has the native-first reasoning; main.py/mise.toml/pyproject edits stay inside their allowed blocks; 23 tests.

## GitHub repos touched

_None._ (local diff and spec only)
