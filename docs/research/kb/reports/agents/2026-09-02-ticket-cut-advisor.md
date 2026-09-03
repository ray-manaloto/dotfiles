# Ticket-cut advisor — #916 under parallel-lane + 40K-token constraints (2026-09-02)

**Status: COMPLETE.** Advises only. Reasoning is in-model (Claude, Fable 5.1);
every `file:line` below was read in this lane unless marked UNVERIFIED.
Token figures use **bytes ÷ 4** (prose/code blend) and are estimates, not
measurements — re-derive before citing as a number.

## Brief (condensed)

Critique the team-lead's 14-ticket cut of #916 against three operator
constraints: (1) concurrent tickets must be file-disjoint so parallel codex
lanes cannot collide; (2) each codex lane ≤ ~40K tokens (ticket + reads +
diff) against gpt-5.6-sol's ~200K; (3) orchestrator and Claude subagents each
stay ~20% of their own limits.

## 1. Verdict on the proposed cut

**The suspected defect is CONFIRMED, and it is wider than named.** Under #916's
own wording — *"one lint step backed by a single module with a single test
module"* — tickets 3, 4 and 5 all edit the same two files, so "parallel by
blocker" is "colliding by file." Tickets 9 and 10 collide too, and 10 is worse
than a sibling collision: converting a rule to a skill renames a file whose
basename is cited from **6 to 147 files each** (measured below), so it collides
with *every* lane, not just 9.

Beyond that, four premises of the cut do not hold:

| Premise in the cut | Finding |
|---|---|
| "~78 modules" for ticket 14 | **UNVERIFIED / inherited.** Measured: **30 modules, 174 sites (172 `sys.std*` + 2 `print(`), ~900 KB.** Neither #687 nor #688's body carries a module count. `T201` is already on (`python/pyproject.toml:64 select = ["ALL"]`), so the migration is `sys.stdout/err.write` → events, not `print`. |
| Ticket 14 must be ONE lane because the operator wants ONE commit | **False.** `ship` arms `gh pr merge --auto --squash` (`pr.py:428-447`), so **any number of lane commits on one branch squash to one commit on `main`.** "One commit" binds the PR, not the lane. The review-difficulty concern the architect recorded is unchanged. |
| Ticket 3 (eager-corpus byte ceiling) is a new dotfiles gate check | **It duplicates the shared engine.** `md-size-budgets.md:183-186`: *"`kb_setup.md_budget` … the enforcer … this repo no longer carries a budget test module of its own."* `md_budget.py:188 EAGER_CLASSES`, `:367 has_paths_frontmatter` already classify eager vs scoped. The aggregate ceiling is a KB-repo change + a SHA bump at `python/pyproject.toml:40`. |
| Ticket 5 is blocked by 2 only | The co-match check needs **rule → globs → body bytes for the INJECTED set** — the dispatcher's registry. Blocked by whatever owns the registry (a root ticket below), not by 2 alone. |

And one dependency in the cut is not real: **2 blocked by 1** — the gate module
has no read of `hook_selfcheck.py`. The real edge is **6 blocked by 1**, because
1 pins the command string `dotfiles-setup mise-config-context` in
`_SETTINGS_WIRING` (`hook_selfcheck.py:85-103`) and 6 renames it.

## 2. Shared-file collision map (the thing that makes lanes unsafe)

| File | Size | Who wants it under the 14-ticket cut | Rule |
|---|---|---|---|
| `python/src/dotfiles_setup/main.py` | **96,791 B, 105 `add_parser` calls** | 2 (new verb), 6 (verb rename), 14 (it is the LARGEST direct-write module) | **One writer per stage. A whole-file read is ~24K tokens = 60% of a lane** — every brief must pin the insertion anchor (neighbouring `_add_*_subcommand`) and forbid whole-file reads. |
| `python/verification/suites.toml` | 2,443 lines, 149 `[[suite]]` | every contract (1?, 2, 6, 14) | Two lanes appending at EOF conflict every time. Contracts land in the serial tail; feature lanes deliver the tokens (`mise run token-check`). |
| `hk.pkl` | 784 lines | 2 (step) — and turn-on ordering (§7.3) | Tail only. |
| `.claude/settings.json` | 5,631 B | 6 (PostToolUse command), story 42's `InstructionsLoaded` observer (missing from the cut) | One owner; sequence. |
| `python/src/dotfiles_setup/hook_selfcheck.py` + test | 22,272 B / 10,003 B | 1, 6, **and 14** (it is one of the 30 direct-write modules) | 1 first; 6 later; exclude it from the migration lanes until 6 lands. |
| `python/src/dotfiles_setup/mise_config_context.py` + test | 9,219 B / 13,665 B | 6 (retire), **14** (it is one of the 30) | **Do not migrate a file 6 deletes.** Exclude from 14; `rule_context.py` is born on the events API. |
| `python/src/dotfiles_setup/hook_guard.py` | 42,124 B | 14 only | No #916 ticket touches it — safe in a migration lane. |
| `python/pyproject.toml` + `uv.lock` | — | 3 (SHA bump), 14 (TID251 `banned-api` table at `:106`), Dependabot (#901 open) | Sequence; tiny edits. |
| `ruff.toml` | — | 4 (`:18`, `:33`) | 4 only. |
| root `AGENTS.md` | 11,875 B, **200/200 lines** | 12 — and any ticket tempted to add a Quick Start line | 12 owns it exclusively; no other lane may touch it (any addition also fails the line budget). |
| `.claude/rules/*.md` (26 files, 122,531 B) | — | 2 (pilot pair), 8, 9, 10, 11, 12 (cites them) | Partition **by file** across lanes; **no renames/deletions in the parallel phase.** |
| `docs/rules-evidence/<rule>.md` (17 exist, 9 missing) | — | 11 | Same partition as the rule it mirrors (1:1). |
| `tests/test_<module>.py` | 15 use `capsys`/`capfd` | 14 | A migration lane owns its modules' tests too, or capsys assertions break in someone else's territory. |

Not a collision: `tests/TEST-INDEX.md` exists but no gate in `hk.pkl` or
`suites.toml` names it (control: the `ls` hit, the grep did not).

## 3. Sizing — bytes → tokens per ticket

| Lead's ticket | Must read | ≈ tokens (read + write + brief) | Fits 40K? |
|---|---|---|---|
| 1 selfcheck PostToolUse | `hook_selfcheck.py` 22 KB, its test 10 KB, `settings.json` 5.6 KB | ~12K | yes |
| 2 gate checks 1+2 + verb + step | prior art `bash_budget.py` (215 lines) + `test_bash_budget.py` 4.3 KB, `memory.md:205-245` (2 KB), 2 rule files, `main.py` **by anchor** | ~18K (**~42K if `main.py` is read whole**) | yes, only with the anchor rule |
| 3 byte ceiling | `md_budget.py` 22.5 KB + its KB tests (UNVERIFIED size) | ~12K | yes — in the **KB repo** |
| 4 suppression check + ruff fixes | gate module, `ruff.toml`, `pyproject.toml` | ~11K | yes, **but blocked on an operator ruling** (§7.5) |
| 5 co-match cap | registry module, gate module; rule BYTES via `stat`, not reads | ~10K | yes |
| 6 dispatcher | `mise_config_context.py` 9.2 KB, its test 13.7 KB, `hooks.md` excerpts ~5 KB, `settings.json`, `mise.toml:1246-1259`, `main.py` anchor, `hook_selfcheck.py` region; writes ~30 KB | ~25-30K | borderline — split core / wiring (§5 H + L) |
| 7 codex adapter | `codex/hooks.md:700-760`, adapter seam, `.codex/hooks.json` 1.6 KB | ~9K | yes |
| **8 classify 26 rules** | **122,531 B = ~31K tokens of pure reading** | ~34K+ | **no margin.** 6 rules already self-classify (`grep -l 'Why this rule is eager\|EAGER on purpose\|cannot be .paths.'` → 6; control token → 0) and 2 are already scoped; the remaining 18 ≈ 90.7 KB ≈ 23K. Split by file — and **fold into the migration lanes**, because the classification's only durable output IS the frontmatter (§7.4). |
| 9/10/11 migrate/convert/move | same corpus | see §5 I and N | by file, 4 lanes ≈ 15-18K each |
| **12 AGENTS.md** | root 11.9 KB + `.devcontainer/` 11.9 + `.github/workflows/` 12.0 + `python/` 5.7 + `tests/` 6.7 = **48.3 KB ≈ 12K** | ~20K | yes; splits cleanly root / subdirs |
| 13 logging expand | `events.py` 10.7 KB + `sinks.py` 17.7 KB (KB repo) | ~9K | yes — but `configure()` wiring lands in `main.py` (§5 E1) |
| **14 migrate ~78 → 30 modules** | **~900 KB ≈ 225K tokens whole-file; 174 sites × ~300 tokens by anchor ≈ 52K** | **> 40K either way** | **no — not as one lane** (§4) |

## 4. Ticket 14 under a 40K lane — plain answer

**Not executable by a single lane.** The 30 direct-write modules total
~900 KB (`main.py` alone is 96.8 KB ≈ 24K tokens). Even the cheapest
discipline — grep the 174 sites, read ±30 lines each, edit by anchor — is
~52K tokens before verification, and a lane that reads any of the top eleven
files whole is over budget on that file alone.

**But the operator's constraint does not conflict with the budget.** The
constraint is *one migration commit*; the repo squash-merges every PR
(`pr.py:447 "--squash"`, `allow_squash_merge=true`), so N file-disjoint lanes
on one branch produce exactly one commit on `main`. What survives is the
architect's recorded concern — a ~900 KB squash is hard to review — and that
was accepted knowingly. Recommend: **six lanes, by module set, each ≤ ~170 KB
of source, edit-by-anchor mandated, whole-file reads forbidden above 40 KB,
each lane owning its modules' tests** (15 test files use `capsys`/`capfd`):

| Lane | Modules (bytes) | ≈ KB |
|---|---|---|
| E1 | `main.py` + the `kb_setup.events.configure()`/sink wiring (lead's 13) | 97 |
| E2 | `image.py`, `dag_tick.py` | 169 |
| E3 | `doctor.py`, `devcontainer_names.py`, `workflow_hooks.py` | 147 |
| E4 | `hook_guard.py`, `pr.py`, `sync.py`, `platform_target.py` | 151 |
| E5 | `dag_project.py`, `command_audit.py`, `codex_lane.py`, `audit.py`, `memory_index.py` | 149 |
| E6 | `verify.py`, `graphify.py`, `schema_vendor.py`, `renovate_dryrun.py`, `graphify_skill.py`, `apt_pins.py`, `session_state.py`, `gcc_sha.py`, `apt_repo.py`, `container.py`, `renovate.py`, `handoff_check.py`, `autofix.py` | 152 |
| **excluded** | `mise_config_context.py` (deleted by the dispatcher ticket), `hook_selfcheck.py` (migrate after B and L land, in the tail) | — |

E1 is the one lane that may not run concurrently with any verb-adding ticket
(§2). Then one serial tail ticket adds `sys.stdout`/`sys.stderr` to the
existing `[tool.ruff.lint.flake8-tidy-imports.banned-api]` table
(`python/pyproject.toml:106`) plus the suites contract — and must **arm it with
a canary** that TID251 actually flags attribute access, not just imports
(UNVERIFIED here; `probes-need-a-control-arm.md` rule 9).

## 5. The re-cut

Territory = the ONLY files a lane may write. Anything else it needs, it reads.

**Stage 0 — not a ticket, a gate.** Decision 10 / story 41: work lands on a
branch off `main` after the in-flight work ships. `docs/spec-916-corrections`
is **9 commits ahead of `origin/main`** (incl. ITEM 11 schemas). Nothing below
starts until that merges.

**Stage 1 — up to 9 lanes, all file-disjoint**

| ID | Ticket | Territory (exclusive) | Blocked by | ≈ tokens |
|---|---|---|---|---|
| **A** | **Rule registry + frontmatter schema** (the root). Parses `.claude/rules/*.md` frontmatter — `paths:` (vendor), `eager: <reason>` and `inject: true` (ours) — into records `(rule_id, path, globs, eager_reason, inject, body_bytes)`. Schema lives in the module docstring. Applies the pilot pair to the two already-scoped rules. **No gate, no verb, no hk.** | `python/src/dotfiles_setup/rule_registry.py`, `tests/test_rule_registry.py`, `.claude/rules/md-size-budgets.md`, `.claude/rules/ci-local-parity.md` | — | ~10K |
| **B** | PostToolUse in ship/land selfcheck (lead's 1) | `hook_selfcheck.py`, `tests/test_hook_selfcheck.py` | — | ~12K |
| **C** | Aggregate eager-corpus byte ceiling **in `kb_setup.md_budget`** (lead's 3, relocated; `kb-ship`). Orchestrator does the SHA bump in `python/pyproject.toml:40` + `uv.lock` afterwards. | knowledge-base: `python/src/kb_setup/md_budget.py` + its tests | — | ~12K |
| **E1–E6** | Logging migration lanes (§4); E1 carries lead's 13 | listed in §4 + each module's tests | — (E1 must not overlap L or P) | ≤ ~40K each by anchor |

**Pre-dispatch probe (orchestrator, live, not a lane):** does Claude Code still
load a rule whose frontmatter carries keys other than `paths`? The vendor
documents only `paths` (`memory.md:205-209`). Arm both ways with
`InstructionsLoaded` (`hooks.md:56`, load reasons `:323`): a scoped rule with
an extra key must still fire `path_glob_match` on read; an eager rule with an
extra key must still fire `session_start`. **If this fails, the whole schema
changes — run it before A ships, not after I×4.**

**Stage 2 — after A: 6 lanes**

| ID | Ticket | Territory (exclusive) | Blocked by | ≈ tokens |
|---|---|---|---|---|
| **G** | Gate checks 1 + 2 (globs match real files incl. the two silent shapes — budget 1,000 expanded patterns / 4 MiB, `memory.md:242-244`; eager declares a reason). **Package with one entry point `find_violations(root)`, one test module per check.** No hk step, no verb — fixtures only. | `python/src/dotfiles_setup/rule_corpus/{__init__,globs,reasons}.py`, `tests/test_rule_corpus_globs.py`, `tests/test_rule_corpus_reasons.py` | A | ~18K |
| **H** | Dispatcher core (lead's 6, first half): Claude adapter reading `file_path` AND `notebook_path`, match via A, compose, budget-trim under 10,000, dedup key `(harness, session, agent, rule)`, render→write→flush→mark order, fail-open. **Touches no wiring file; does not delete the old handler.** | `python/src/dotfiles_setup/rule_context.py`, `tests/test_rule_context.py` | A | ~25K |
| **I1–I4** | Corpus lanes, **cut by file** (lead's 8 + 9 + 11 merged). Per file: classify on the four-category test (`md-size-budgets.md:132-147`), write the frontmatter (`paths:` or `eager:` reason; six rules already carry their reason in a "why eager" section), move archaeology to the 1:1 evidence file. **No renames, no deletions, no edits outside the set.** | I1: `probes-need-a-control-arm`, `secrets-out-of-the-shell-env`, `agent-report-persistence`, `persistence-gate-retry`, `real-integration-evidence` (27.4 KB) · I2: `mise-tasks-only`, `verify-before-advancing`, `graphify-first`, `research-repo-enumeration`, `goal-history`, `clean-git-state` (25.2 KB) · I3: `research-doc-sources`, `clarify-before-acting`, `long-running-command-hangs`, `use-tool-builtins`, `ai-cli-invocation`, `notepad-enforcement` (28.0 KB) · I4: `agent-artifact-conventions`, `tool-currency-and-native-first`, `do-not`, `local-devcontainer-first`, `zero-skip-policy`, `gh-cli-watch`, `zero-bash-logic` (29.1 KB) — each plus its `docs/rules-evidence/<same>.md` | A | ~15-18K each |

**Stage 3 — 3-4 concurrent**

| ID | Ticket | Territory (exclusive) | Blocked by | ≈ tokens |
|---|---|---|---|---|
| **J** | Check 4 (no suppression above file scope) + fix `ruff.toml:18`, `:33`. **Needs the operator's S101 ruling first (§7.5).** | `rule_corpus/suppression.py`, `tests/test_rule_corpus_suppression.py`, `ruff.toml`, one line in `rule_corpus/__init__.py` | G, ruling | ~11K |
| **K** | Check 5 (every co-matching `inject:` set fits the cap) | `rule_corpus/comatch.py`, `tests/test_rule_corpus_comatch.py`, one line in `rule_corpus/__init__.py` | G (J and K serialize on `__init__.py` — or G pre-registers both names) | ~10K |
| **L** | Wiring swap (lead's 6, second half): `settings.json` PostToolUse → `rule-context`; `mise.toml:1246` task; `main.py` verb by anchor; `_SETTINGS_WIRING` tuple; **delete** `mise_config_context.py` + its test; mise reminder becomes a registry row; commit body records the native-filter justification and the `PostToolBatch` rejection (stories 51, 55). | `.claude/settings.json`, `mise.toml`, `main.py`, `hook_selfcheck.py` (+test), `mise_config_context.py` (+test), `rule_context.py` (registry row only) | B, H, E1 | ~15K |
| **M** | Codex adapter (lead's 7): parse `apply_patch` paths (a SET), `.codex/hooks.json` PostToolUse entry. Inherits the `${CLAUDE_PROJECT_DIR:-.}` defect knowingly (out of scope per #916). | `python/src/dotfiles_setup/rule_context_codex.py`, `tests/test_rule_context_codex.py`, `.codex/hooks.json` | H | ~9K |
| **N** | Skill conversions (lead's 10) — **serial, after I×4**, because each rename must fix every citing file. Pick candidates from the fan-in tail (`real-integration-evidence` 6 files, `clean-git-state` 11, `persistence-gate-retry` 11, `goal-history` 13); anything ≥ 30 files is not a one-lane job. | the converted rules, their new `.claude/skills/<name>/SKILL.md`, every citing file (enumerated by grep in the brief) | I1-I4 | ~5K per rule |
| **O** | AGENTS.md extraction + subdir split (lead's 12). Subdir files are **already** on-demand (`memory.md:159`), so "split by load class" for them means *promote behaviour-triggered content to eager*, not *make them lazy* — say so in the ticket. Split O1 root / O2 subdirs if desired. | root `AGENTS.md`, the four subdir `AGENTS.md`, NEW rule files it creates (unique names) | I1-I4, **after N** (both edit citations) | ~20K |

**Stage 4 — serial tail**

| ID | Ticket | Territory | Blocked by |
|---|---|---|---|
| **F** | TID251 `sys.stdout`/`sys.stderr` in `pyproject.toml:106` table + suites contract + canary; migrate `hook_selfcheck.py` (excluded from E) | `python/pyproject.toml`, `suites.toml`, `hook_selfcheck.py` | E1-E6, L |
| **P** | Gate turn-on: `hk.pkl` step (thin, `bash_logic_budget` shape at `hk.pkl:247-250`), `main.py` verb `rule-corpus` by anchor, suites contracts for gate + dispatcher wiring (tokens via `mise run token-check`), `md-size-budgets.md` pointer, C's SHA bump. **Lands only after I×4** — the reason-check is red until all 24 eager rules carry a reason. | `hk.pkl`, `main.py`, `suites.toml`, `python/pyproject.toml`, `uv.lock`, `md-size-budgets.md` | G, J, K, L, I1-I4, C |
| **Q** | `InstructionsLoaded` observer (story 42 — **missing from the cut**): settings hook → `.agent/state/rules-fired/<session>.jsonl` via a thin verb. | `.claude/settings.json`, a small module + test, `main.py` by anchor | L, P |

Not lane tickets: closing #283/#681/#687/#688 with verbatim content (stories
31-33; #916's "Supersession" already carries the reversal) — orchestrator; the
codegen audit (stories 37-38, "three denies" #2) is **absent from the 14
tickets** — a read-only audit lane producing an issue, or an explicit deferral.

## 6. Frontier shape

| Stage | Concurrent lanes | Of which rule-scoping work |
|---|---|---|
| 0 | 1 (ship the in-flight branch) | 0 |
| 1 | up to 9 (A, B, C, E1-E6) | 3 |
| 2 | 6 (G, H, I1-I4) | 6 |
| 3 | 3-4 (J→K, L, M, N→O) | 3-4 |
| 4 | 1-2 (F, P, Q) | 1 |

**Parallelism is real but front-loaded, and most of stage 1's width is the
logging migration, not the rule work.** The rule work's intrinsic width is 6
(stage 2) narrowing to ~3 then 1. It is available only if all four of these
hold: `main.py` has one writer per stage; the gate is a package, not one
module (§7.2); corpus lanes are cut by rule file with no renames; and every
contract/step/settings edit is consolidated into the tail. Drop any one and
the frontier collapses to "mostly one."

## 7. Failure modes not named in the brief

1. **Gate turn-on ordering.** Check 2 ("every eager rule declares a reason")
   is red on `main` from the moment the hk step lands until all 24 carry
   reasons. The step wiring must be the LAST thing, not the first (P after
   I×4). The lead's cut wires the gate in ticket 2 and classifies in ticket 8 —
   backwards.
2. **`doc_refs` gives a false green on skill conversion.** `doc_refs.py`
   resolves a citation by *basename match against any tracked file* (docstring
   rule 2, `doc_refs.py:14`). `docs/rules-evidence/<name>.md` keeps the
   basename alive, so a stale `.claude/rules/<name>.md` citation still resolves
   after the rule is deleted. N needs a grep sweep, not the gate.
3. **`main.py` is the universal collision point AND the budget-breaker.**
   105 `add_parser` calls, 96.8 KB; every verb ticket and the largest migration
   lane want it; read whole it costs 60% of a lane.
4. **Ticket 8 as a standalone deliverable double-pays the corpus.** A
   classification table read back by a later lane costs the 31K twice; the
   frontmatter IS the classification, so classify-and-write in one pass.
5. **Three decisions a codex lane cannot make** (`AskUserQuestion` is stripped
   from every subagent — memory `project_session_2026-09-01`): (a) the
   `tests/**/*.py` S101/D103/PLR2004 ignore at `ruff.toml:18` has no legal home
   under the ladder "code block > file > (never) project" except 82 per-file
   entries or a nested `tests/ruff.toml` (directory scope — the ladder does not
   name it); (b) whether "single module" in #916 bends to "single package with
   one entry point"; (c) where the mise-reminder registry row's body lives when
   it has no rule file. Rule on all three before dispatch.
6. **Vendor tolerance of extra frontmatter keys is UNVERIFIED** — see the
   stage-1 probe. `memory.md:205-209` documents only `paths`.
7. **Worktrees change the collision class, not the requirement.** pwf adopted
   worktrees (memory 2026-09-02b), so lanes in worktrees merge-conflict instead
   of live-reverting — but only if EVERY lane really runs in its own worktree.
   The brief must pin the worktree per lane; a lane run in the main checkout
   reintroduces the 4×-revert incident (`feedback_lane_done_does_not_release_the_checkout`).
8. **Cross-lane section anchors.** Rule A cites "rule B § heading"; lane I2
   moving B's section to evidence breaks the anchor in lane I1's file. Not
   gate-checked (`doc_refs` strips `:line`, ignores anchors). Cheap post-pass.
9. **`configure()` wiring for `kb_setup.events` lives in `main.py`** (the CLI
   entry), so lead's 13 "blocked by none" is really "shares `main.py` with E1"
   — fold them (done in §4).
10. **Stage 0 may be the long pole.** Memory 2026-09-02b/c: Docker Desktop
    dropped image layers and four `ship`s died on it; the 9-commit branch has
    to get through `ship`'s container gate before any lane can branch off
    `main`.

## 8. Premises of the brief — corrected or unverified

- "~78 modules" — **UNVERIFIED, inherited**; measured 30 / 174 sites / ~900 KB.
- "Ticket 14 in one lane" — **not required**; squash-merge makes one commit
  from N lanes (`pr.py:447`).
- "3/4/5 collide" — **CONFIRMED** under #916's single-module wording; a
  package resolves it.
- "9/10 collide" — **CONFIRMED and understated**; 10 collides with every citing
  file (6-147 per rule).
- "8 and 12 worry me most" — 8 yes (31K of reading, no margin); 12 no (48 KB ≈
  12K, fits; and the subdir files are already lazy — `memory.md:159`).
- "2 blocked by 1" — **not a real edge**; "6 blocked by 1" is.
- "5 blocked by 2" — incomplete; 5 needs the registry.
- Ticket 3 as a dotfiles check — contradicts the recorded seam
  (`md-size-budgets.md:183-186`); it is a KB-repo ticket.
- graphify: `mise run graphify-query` returned **TRUNCATED (52 of 144 nodes)
  → task failed**, so per `graphify-first.md` the graph was unavailable and
  every claim here is from source.

## Probe controls run

- Rules self-classified as eager: pattern → **6 files**; invented token
  `qxzv-plork-8817` → **0** in the same corpus. Discriminates.
- Citation fan-in per rule (`grep -rl -F <name>.md`, excl. `docs/research`,
  `.agent`, `graphify-out`): 6 → 147; control basename `zzplork-nonesuch.md`
  → **0**. Discriminates.
- Vendor frontmatter/`InstructionsLoaded`/brace-budget greps in
  `$CC/memory.md` and `$CC/hooks.md`: hits at `memory.md:205,209,242-244,159`,
  `hooks.md:56,323`; control `qxzv-plork-8817` → **0** in `memory.md`.
- Direct-write count: `\bprint\(|sys\.(stdout|stderr)` over `python/src` → 30
  files; widened with `click.echo|Console\(` → still 30; over src+tests+scripts
  → 32. `print(` alone → 2 sites, `sys.std*` → 172.
- `#687`/`#688` bodies grepped for `N (modules|files|sites)` → **no hit** —
  the ~78 has no provenance in the tracker.
- `gh api repos/… allow_squash_merge` → `true`; `pr.py:447` → `"--squash"`.
- `TEST-INDEX.md` gate: `ls` → present; `grep` in `hk.pkl`/`suites.toml` → 0.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #916, #687, #688 bodies; repo merge settings via `gh api`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — sibling clone read offline: `kb_setup/{md_budget,events,sinks}.py` and the vendor doc corpus under `sources/agent-harness-docs/docs/claude-code/`.
