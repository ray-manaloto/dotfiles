# Cold review — 6563119b (graphify-fleet fork-feature probe)

- Subject: `6563119be618dc3324b7e9763787ec0110640f37` vs parent `8b3c3983a93b66f482d5b8494ffd3c4edc3c851c`
  (caller wrote `6563119b6`, which git does not resolve (`fatal: ambiguous argument`); `6563119b` resolves uniquely to the SHA above and is HEAD of `feat/graphify-fleet`).
- Author family: codex (SDLC run aa78bf7b). Reviewer: cold-reviewer (Claude Opus), diff-only, round 1 (open hunting + Q-FRESH/Q-SCOPE/Q-CLAIM).
- Stamp: 20261004T203552
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start (no prior review patterns).
- Files: `python/src/dotfiles_setup/graphify_fleet.py`, `tests/test_graphify_fleet.py`, `.claude/skills/graphify-fleet/SKILL.md`, `.agents/skills/graphify-fleet/SKILL.md` (153+/15-).

## Status

COMPLETE. Verdict: **SHIP** — no HIGH or MEDIUM. The core change (5 probe terms) is correct and verified against the real fork clone at three refs; the tests discriminate under two mutation arms. Findings are LOW/INFO wording and binding gaps.

## Findings

| # | Severity | Claim | file:line | Evidence / refutation check |
|---|---|---|---|---|
| F1 | LOW | The new "confirm against the fork commit list" command is printed as bare `git log <base>..<commit>`, with no `-C <fork>`. Pasted where the plan prints (the dotfiles checkout), it fails with rc=128. The sibling commands in the same function all use `git -C {roots.fork}`. | `python/src/dotfiles_setup/graphify_fleet.py:515-516`; `.claude/skills/graphify-fleet/SKILL.md:55` (+ `.agents` mirror) | Ran `git log --oneline v0.9.57..3c9b930f386f…` from the worktree and got rc=128 `unknown revision`. Control arm: the same range via `git -C ~/dev/github/ray-manaloto/graphify log` listed 8 commits. Sibling commands use `-C`: `:541` `git -C {roots.fork} switch`, `:543` `git -C {roots.fork} rebase`. Refutation check: `:515` has the f-string `` (`git log {ctx.fork_base_ref …}.. `` and no `-C`. Confirmed. |
| F2 | LOW | The commit fixes the "overclaims retirement" class in the SKILL and plan summary. The schema's `ForkProbe` description still says "Whether upstream now ships the fork's features natively", and that text is generated into the model docstring. This is a remaining instance of the same class (fix the class, not the instance). | `schemas/graphify-fleet.schema.json:60` → `python/src/dotfiles_setup/generated/graphify_fleet.py:61` (outside the diff) | Read both lines. The diff narrowed `SKILL.md:52-53` ("found every one of the 5 probed fork terms") and `graphify_fleet.py:512`, but not the schema. Fix: edit the schema, then `mise run codegen` (generated code is never hand-edited). Q-SCOPE: same ticket and class, but outside the diff's lines. |
| F3 | LOW | The clause "(manifest `clears_when`)" points at the wrong file. `clears_when` is a field of the KB's `currency.toml` `[tool.graphify.fork]`, the same table `_kb_leg` reads `base_ref` from. `sources/graphify.manifest` only mentions it in a comment. The wording predates this diff, but the diff rewrote both sentences and kept it. | `python/src/dotfiles_setup/graphify_fleet.py:513-514`; `SKILL.md:54` (both mirrors) | `git -C knowledge-base grep -n clears_when origin/main -- sources/graphify.manifest currency.toml` found the field at `origin/main:currency.toml:214` (`clears_when = "upstream merges an openai-cli backend. …"`). The manifest has it only at `:98`, inside a `#` comment. The module reads that table at `graphify_fleet.py:324-325`. |
| F4 | LOW (Q-SCOPE: sibling — KB ticket, not a change request here) | There are now two disagreeing retirement criteria. The KB's `clears_when` says the fork clears when "upstream merges an openai-cli backend". The fleet probe now requires all 5 change families. If upstream merges PR #3073 (named in that KB field), the KB criterion fires while the fleet probe (correctly) stays `native=False`. | KB `origin/main:currency.toml:214` (sibling repo); this repo `graphify_fleet.py:66-77` | Read the KB field verbatim (F3 probe). By the KB's own `reason` line (`:213`), #3073 is an independent implementation, so it would not carry `_run_semantic_extract`, `UNWIND $rows` or `_codex_resolvable_disable_args`. **Recommend a KB ticket** to widen `clears_when` to the 5 families. |
| F5 | LOW | The SKILL copies the term list and the count ("five", "5") by hand. The code derives the count from `len(probe.feature_hits)`. No test or contract ties the SKILL list to `FORK_FEATURE_TERMS`, so adding or renaming a term leaves both SKILL mirrors stale without any error. | `.claude/skills/graphify-fleet/SKILL.md:47-53`; `graphify_fleet.py:512` | `git grep -n "graphify-fleet\|graphify_fleet" -- python/verification/suites.toml hk.pkl hk-common.pkl mise.toml` returned only the `mise.toml` task. Control arm: `graphify-currency` hits `suites.toml:1540`, so the grep shape works. `tests/` asserts only the plan-summary string "all 5 probed fork terms" (`tests/test_graphify_fleet.py:509,517`), not the SKILL. |
| F6 | INFO | The commit subject "probe one term per fork change" overclaims: there are 8 payload commits and 5 terms. The body ("five change families") and the code comment (`:67`, which groups 8adbc178/45371550/5c755a83 under `openai-cli`) are accurate. 45371550 (the `cli.py` credential gate `elif backend == "openai-cli"`) has no term of its own. An upstream `openai-cli` backend without that gate would read that family as present. This is mitigated because `native` also needs the other four terms, and retirement is human-gated. | `python/src/dotfiles_setup/graphify_fleet.py:67-68` | `git log -S'openai-cli' v0.9.57..3c9b930f` attributes the term to 3c9b930f, 45371550 and 8adbc178. `git show 45371550 -- graphify/cli.py` shows only the gate, with no unique identifier. 5c755a83's `_codex_disable_mcp_args` survives at 3c9b930f (`llm.py:2031`) and calls `_codex_resolvable_disable_args` (`:2051`), so the term at `:76` covers it in practice. |
| F7 | INFO | No term has a runtime positive check at the fork commit. If a term disappears from the fork (for example, renamed during a replay), it reads 0 forever and `native` can never be True. That fails safe (the replay is kept), but nothing reports it. Grepping each term at `ctx.fork_commit` would give every term its own control arm (probes rule 9). The same mechanism means `native=True` happens only if upstream merges *our* identifiers verbatim (`_run_semantic_extract` and `_codex_resolvable_disable_args` are private names), not if upstream ships an equivalent of its own. The new SKILL wording states this accurately. | `python/src/dotfiles_setup/graphify_fleet.py:411,444` | `_fork_hits` greps only `tag` (`:411-412`). `ctx.fork_commit` is never grepped. |
| F8 | INFO | The text render joins `term=count` pairs with spaces, and `UNWIND $rows` itself contains a space, so the line cannot be split on whitespace (`… _run_semantic_extract=0 UNWIND $rows=0 …`). No consumer parses this line, and `--json` output is unaffected. | `python/src/dotfiles_setup/graphify_fleet.py:639` | Seen in the real `mise run graphify-fleet -- plan` output. A `git grep` for `fork-probe`/`feature_hits` outside the module and test found only the SKILL mirrors and the schema or generated model, so there is no text parser. |

## Verified correct (refutation attempts that failed)

- **Each of the five terms appears only in the fork, and the probe is positive at the fork commit.** Same command shape as `_grep_count` (`git -C <fork> grep -lF <term> <ref> -- graphify/`):

  | term | `3c9b930f` (fork) | `v0.9.57` (base) | `v0.9.76` (upstream) |
  |---|---|---|---|
  | `openai-cli` | 3 files | 0 (rc=1) | 0 (rc=1) |
  | `fallback-backend` | 3 files | 0 | 0 |
  | `_run_semantic_extract` | `watch.py` | 0 | 0 |
  | `UNWIND $rows` | `exporters/graphdb.py` | 0 | 0 |
  | `_codex_resolvable_disable_args` | `llm.py` | 0 | 0 |
  | control `claude-cli` | 18 | 18 | 18 |

  Checking the base too matters: a term already present at `v0.9.57` would not be fork-only. The commit message's claim reproduces.
- **The SHA comments map to the right terms.** `git log --oneline v0.9.57..3c9b930f` returns exactly the 8 cited commits. `git log -S` attributes `_run_semantic_extract` to c38f63d5, `UNWIND $rows` to c71245de, and `_codex_resolvable_disable_args` to 3c9b930f, matching the comments at `:71-76`.
- **The `$` in `UNWIND $rows` reaches git literally.** The argv is a list and no shell runs (`_call` `:216`, `_git` `:272`). The real positive-arm grep found `graphdb.py`. Ref-resolution control: `vZQ9.1.4^{commit}` gave rc=1, while `v0.9.57` and `v0.9.76` gave rc=0.
- **The tests discriminate.** pytest output: `29 passed`.
  - Mutation A: restoring the parent's 2-term `FORK_FEATURE_TERMS` in-process, run with `-n 0` so xdist workers inherit it, gives **6 failed**. These include `test_plan_only_original_terms_hit_keeps_fork_replay` (the regression test) and 3 of the 5 parametrized missing-term cases.
  - Mutation B: restoring the parent's "ships every fork feature natively" summary gives **1 failed** (`test_plan_native_upstream_proposes_retirement`).
  - Removing one term is also caught: `FakeRun.grep_hits` raises `KeyError` on an unknown term, and the parametrized case for the deleted term asserts `native is False`.
- **A real run through the public entrypoint agrees.** `mise run graphify-fleet -- plan` gave rc=1 (`behind`): `fork-probe v0.9.76: openai-cli=0 fallback-backend=0 _run_semantic_extract=0 UNWIND $rows=0 _codex_resolvable_disable_args=0 control claude-cli=18 -> native=False`, followed by the replay plan. This matches the manual grep table, so two independent routes agree.
- `ruff check` and `ruff format --check` on the 2 Python files: rc=0. The SKILL mirrors are byte-identical (`cmp` rc=0). No leftover "every fork feature"/"natively" wording remains in the module or the SKILLs (the schema is the exception, F2).

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH:** Not applicable to the diff. `native` drives a *printed* plan step with `commands=[]`, `human_gate=True` and `runnable=False` (`:518-520`). No automated action follows the decision. The probe reads an immutable tag from a local clone and never fetches; an absent tag fails closed as UNVERIFIABLE (`:403-410`).
- **Q-SCOPE:** F1, F3, F5 and F6 are in scope (this ticket's own strings and doc). F2 is the same class but sits in the schema, outside the diff's lines; fix it in this unit with codegen. F4 is a sibling: a **KB ticket**.
- **Q-CLAIM** (plan summary at `graphify_fleet.py:512-516` and SKILL `:52-56`):

  | Clause | Enforcing line | Outcome |
  |---|---|---|
  | "upstream {tag} contains all {N} probed fork terms" | `:444` `all(count > 0 …)`; N from `:411` (`hits` keyed by `FORK_FEATURE_TERMS`) | enforced |
  | "retiring the fork is a human decision" | `:518-520` `commands=[]`, `human_gate=True`, `runnable=False` | enforced (test asserts all three) |
  | "(manifest `clears_when`)" | none: the field lives in KB `currency.toml:214` | **F3** |
  | "confirm against the fork commit list (`git log …`)" | advisory, and the printed command lacks `-C <fork>` | **F1** |
  | SKILL "five fork terms: …" / "5 probed" | no binding to `FORK_FEATURE_TERMS` | **F5** |
  | SKILL "the plan says so instead of printing a rebase" | `:518` `commands=[]`; test `kb_first.commands == []` | enforced |
  | Code comment "Terms only our fork's payload introduces" | verified externally (table above), not at runtime | **F7** (INFO) |

## Probes run

1. `git rev-parse 6563119b6` gave rc=128. `6563119b` resolved to `6563119be618…`, with parent `8b3c3983a93b…`.
2. Fork ref resolution, with the control arm `vZQ9.1.4` (rc=1).
3. The 15-cell term grep table above, plus the control term at three refs.
4. `git log -S` attribution for each term; `git show` of 45371550 and 5c755a83.
5. KB `clears_when` location, with control grep `commit` in the manifest (15 hits).
6. `uv run --project python pytest tests/test_graphify_fleet.py -q -p no:cacheprovider`: 29 passed. A scratch log `/tmp/cr-6563119b-pytest.log` was written by mistake and deleted right after; later runs captured nothing to disk.
7. Two in-process mutation arms (A and B above). No source file was edited, and `git diff --quiet` gave rc=0 afterwards.
8. `mise run graphify-fleet -- plan` (real entrypoint): rc=1.
9. The printed `git log` run from the dotfiles cwd: rc=128 (F1).
10. `ruff check` and `ruff format --check` on the 2 files: rc=0.

## GitHub repos touched

- [ray-manaloto/graphify](https://github.com/ray-manaloto/graphify): local fork clone; term greps at `3c9b930f`, `v0.9.57`, `v0.9.76`; payload commit log.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): local clone at `origin/main`; `currency.toml` `clears_when` and `sources/graphify.manifest`.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the diff under review.
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify): its latest release tag (`v0.9.76`), queried through `gh release view` by the real `graphify-fleet plan` run.
