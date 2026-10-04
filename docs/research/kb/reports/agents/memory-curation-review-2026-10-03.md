# Memory-index curation review (lane G, 2026-10-03) — READ-ONLY

Status: COMPLETE.

## 1. The un-indexed set
Index 25,714 -> 16,633 B (current `wc -c` = 16633, confirmed). Cutoff moved to 2026-09-14.
Diff of `project_session_*.md` in the memory dir vs links in current MEMORY.md, intersected with the
entries present in the pre-curation index (session-start snapshot): **18 files, not 17**:
09-08b, 09-08c, 09-08d, 09-09, 09-09b, 09-09c (old hook "2026-09-10 — PR A done"), 09-10 (old hook "2026-09-10b"),
09-10c, 09-11, 09-11b, 09-11-c, 09-11-d, 09-12, 09-12b, 09-13, 09-13b, 09-13-c, 09-13-d.
(Lane log says "17 sessions un-indexed" — G.md last section. Likely an off-by-one: 09-11b sat at the TOP of the old
Project section, out of date order, and is easy to miss.) All non-session feedback_/reference_ entries are still indexed.

## 2. Method (probe + control arms)
- Corpus for "covered": the 116 `feedback_*`/`reference_*`/non-session `project_*` files linked from the CURRENT
  MEMORY.md + the 27 `.claude/rules/*.md` snapshotted from `origin/main` 186233e4 (`git show`; the checkout is on
  `fix/L0-handoff-findings-urgent`). Probe script: `coverage.py` beside this report; raw output `coverage.out`.
- Same regex shape, every run: control-present `control arm` -> 48 hits, `pipefail` -> 18 hits; a freshly assembled
  absent token -> 0. So a 0 below is "absent from this corpus", not a dead probe. Each lesson used 2-4 spellings.
- Load class: 25 rules eager; `ci-local-parity.md` and `md-size-budgets.md` are `paths:`-scoped (not eager).
- Recurrence: grep of the still-indexed later session files (09-14 .. 10-03) plus issue states via `gh issue view`.

## 3. Coverage — the seven named candidates

| # | Lesson (source) | Coverage, cited | Recurrence | Verdict |
|---|---|---|---|---|
| C1 | Search issues BEFORE diagnosing; recording was never the gap, RETRIEVAL was (09-11-c:31-39) | PARTIAL. `feedback_check_upstream_issues_first.md:3` ("search a project's issues/PRs/discussions BEFORE diagnosing", framed as UPSTREAM); root `AGENTS.md:111` "Research before fixing: … issues". Neither names OUR OWN tracker/specs/task_plan RULING lines. 0 hits for `retrieval (was|is) the gap`, `filed twice|diagnosed (three|3) times`, `own (repo's )?issues|existing issues?` | **HIGHEST.** Recurred in 8 later sessions: 09-12b:15 (five misses), 09-13-c:134 ("again"), 09-14 (desc), 09-14-b:80, 09-14-d:70 (five), 09-15:19 (three), 09-23:39 ("4th session running"), 10-01:32 (four). Structural fix #1024/#1028/#1029 all OPEN | UNCOVERED in the specific (own-repo) form; recurring |
| C2 | `/plugin-types` rc 0 without its env flag; never gate on rc (09-12:18-28) | Principle COVERED by `probes-need-a-control-arm.md:127-136` (rule 9, "assert the capability"; validator "still exits 0"). Specific tool: OBSOLETE — `project_session_2026-10-01.md:22` (indexed): `/plugin-types` is gone since CC 2.1.287; fnhook types now come from CI (`fnhook_gates.py:522`) | none possible | Leave un-indexed |
| C3 | An off-switch wired to a DIFFERENT consumer is worse than none; bind the CALL SITE (09-13b:19-37) | PARTIAL. Call-site half: `feedback_forbid_tokens_substring_fragile.md:3` ("bind require to a call site", suites.toml tokens only). Different-consumer half: 0 hits (`different consumer`, `configurab`). Machine-carried for fn-hooks only: `fnhook_gates.py:338` `assert_escape_hatch_permitted`, called :601, bound by suites.toml:3015 | 09-18:64 — the same gate bricked again (different defect); the lever then worked. Plausible for any `doctor.toml` lever with >1 reader | Fold into the existing feedback (no new index line) |
| C4 | A live arm answered by an EARLIER LAYER (permission deny before argparse) proves nothing (09-13-c:65-69) | COVERED BY CLASS: `probes-need-a-control-arm.md:86-87` ("Arm the component you actually depend on … aimed at the wrong link"); `feedback_control_arm_wrong_subsystem.md:3,11`. The "earlier layer intercepts" wording: 0 hits for `earlier layer`, `answered by an earlier|before argparse`, `ARM ANSWERED` | No later recurrence found (0 hits in 09-14..10-03 files). #1049 OPEN | Optional sentence in the existing feedback |
| C5 | `gha-rerun --failed` on a manifest-only failure ⇒ a later `promote` STALE failure; recover with a FULL rerun (09-13:115-120) | **NOT COVERED.** `gha-rerun` appears only as the redirect `mise-tasks-only.md:28` and `project_automation_program.md:55`; 0 hits for `rerun --failed`, `#1046`, `index digest`, `full (re-?run|rerun)` | No recorded repeat, but **the canonical path steers INTO the trap**: `mise.toml:669-672` defines `gha-rerun` as `gh run rerun --failed`, and `mise-tasks-only.md:28` says to use it instead of `gh run rerun`. #1046 OPEN. (`hook_guard.py` has no `rerun` rule: 0 hits vs control `pr create` 12 hits, so a full rerun is doc-redirected, not denied) | UNCOVERED; live; a machine fix is better than a memory |
| C6 | `# :schema` with a SPACE is INERT (09-10c:42-45) | NOT in memory/rules (`# :schema` 0; `schema directive` 0). Machine-carried for 6 of 18 files: suites.toml:2949-2975 `config.schema-vendor-directives-bound` pins the exact `#:schema …` lines in mise.toml, ruff.toml, typos.toml, shared.toml, mise-system.toml, mise-runtime.toml. Tree today: spaced form 0 files vs correct form 18 (control) | None after 09-10c. The 12 unbound files include `.codex/agents/*.toml`, where `codex-sdlc-team.md:61` calls the directive "the pre-flight" | Leave un-indexed, or widen the contract |
| C7a | codex project config is SELECTIVE: project `model`/effort never honoured; global wins; don't delete `.codex/config.toml` (09-10:20-25) | NOT COVERED eagerly (`\.codex/config\.toml` 0, `shell_environment_policy` 0, `-m gpt|per-call` 0). `ai-cli-invocation.md:23-24` pins effort only in the implementation example. ⚠️ The 09-10 text is PARTLY REFUTED by 09-15:58-66 (project config IS read+validated; `--ignore-user-config` DOES suppress it). Note `.codex/config.toml` is gitignored and was never tracked (`.gitignore:59` `.codex/*`; `git log --all` empty) — a `git clean -xdf` removes it | Recurred: 09-15:62 (re-litigated), 10-01d:33 (unpinned lens ran at effort **low**, had to be re-run at high) | UNCOVERED; recurring; promote the CORRECTED form only |
| C7b | A codex prompt without the trailing `-` hangs forever (09-10:33) | **COVERED (eager):** `codex-sdlc-team.md:42-43`; canonical argv `ai-cli-invocation.md:20-24` ends in `-`; also `feedback_scope_process_hunts_to_this_project.md:72` | 09-14-sdlc-team:38 (same fact) | Nothing to do |

## 4. Coverage — every other ⭐/⚠️ lesson in the 18 files

Already COVERED (cite):
| Lesson (source) | Carried by |
|---|---|
| Task notification "exit code 0" lies (09-08c, 09-10c, 09-11, 09-12b, 09-13, 09-13b, 09-13-c) | `feedback_background_task_notification_can_lie.md:3,11` (indexed) |
| A guard deny cancels the WHOLE compound (09-08c, 09-11-c, 09-13-c) | `mise-tasks-only.md:71` |
| Token-spelling / display bounds / fresh control tokens (09-08d, 09-09c, 09-12b, 09-13-c) | `probes-need-a-control-arm.md:69,75,94` |
| Coarse mutation certifies nothing (09-08c, 09-09c) | `feedback_coarse_mutation_certifies_nothing.md` (indexed) |
| Contract tokens bind strings, not behaviour (09-08b, 09-08c) | `feedback_forbid_tokens_substring_fragile.md:3` |
| Stop-hook `additionalContext` forces a turn (09-09c) | `feedback_stop_hooks_force_a_turn.md`; `agent-report-persistence.md` "Native carriage" |
| A lane truncated shared findings/progress (09-09c) | `agent-report-persistence.md:88` |
| Pin ONE ref in a review brief (09-09c) | `feedback_orchestration_process_lessons.md:41` (body; the index hook no longer says it) |
| zsh does not word-split (09-08d, 09-09) | `feedback_zsh_no_word_splitting.md` (indexed) |
| Host is not a control arm for CI (09-12) | `feedback_host_is_not_a_control_arm_for_ci.md` (indexed) |
| `timeout` is a broken shim (09-12b) | `long-running-command-hangs.md:51` |
| Dubious-ownership transient (09-13b) | `persistence-gate-retry.md:52` |
| Graph ancestry is the wrong staleness test (09-13-c) | `graphify-first.md:32` |
| Only `Read()`/`Edit()` path rules are checked (09-13-c) | `secrets-out-of-the-shell-env.md:116` |
| PEP 758 comma-except is correct (09-11-c) | `feedback_python2_comma_except.md` (indexed) |
| One host-wide gate slot; parallel ships need the one daemon (09-12b, 09-13b) | index line 19 (10-02b hook "one test slot host-wide") |
| GHA skip cascade / `always()` rescues only itself (09-08b, 09-11b) | MACHINE: `hk.pkl:476` `workflow_skip_cascade` (#1012); #981 still OPEN for the `!cancelled()` sweep |
| `mise run` eats one `--` (09-13-c) | MACHINE: fixed in code (`plan_attest.insert_passthrough_separator`, #1051) |

Not covered — classified (O = obsolete or fixed, L = low or one-off, P = plausible recurrence):
| Lesson (source) | Class | Note |
|---|---|---|
| graphify `TRUNCATED` names its own remedy (`--budget`); not an outage (09-08d, 09-12b) | **P, and the rule contradicts it** | `graphify-first.md:7` still lists truncation as "unavailable"; `graphify.py:606-611` already passes `--budget`. 09-12b asked for an amendment, which was never made. Recurred twice |
| agnix counts BYTES while saying "chars" (09-11-c) | **P** | `.claude/CLAUDE.md:4` says "~500 characters of the 12,000-character ceiling". AGENTS.md lives at the cap (09-12: 11,968/12,000). Inherited claim, not re-measured by me |
| A reported defect closes only when the REPORTER's command is run (09-13:15-25) | **P** | Proposed `verify-before-advancing.md` row never written (0 hits: `reporter`, `user said`) |
| Mutation battery: assert the SPECIFIC rc; pytest rc=4 = usage (09-09) | P | cause covered (zsh); the rc discipline isn't |
| macOS is case-insensitive: `ls -d .Codex` can't tell; use `git ls-files` (09-10c) | P | 0 hits `case-insensitive` |
| Non-blocking validation leg: read the JOB LOG, not `gh pr checks` (09-08d) | P | 0 hits `read the job` |
| `gh run list` result sets are unstable; re-run before citing (09-08b) | P | `gh-cli-watch.md:49` covers only the racy `--limit 1` |
| codex lane model: verify from the ROLLOUT (09-11-d) | P (folds into C7a) | `ai-cli-invocation.md:19,37` covers rollout persistence only |
| Memory can carry a BROKEN PROBE forward (09-13-c:70-75) | L/P | its subject (`plan-attest --show`) is fixed |
| Run the probe a lane NAMED but did not run (09-11-d, 09-10) | L | adjacent to `feedback_agent_team_delivery_discipline.md` |
| Fixture must differ only in the dimension under test (09-13b) | L | `probes-need-a-control-arm.md:119-125` (rule 8) is close |
| Cross-check a CAUSE before filing (09-13) | L | `probes-need-a-control-arm.md:115` (rule 7) covers surprises |
| ty: `tests/` is not importable (09-09); `tools:` without `Skill` (09-09b); md_size_budget blind to agents (09-09b); zizmor flags `workflow_run` (09-11b); `gh pr diff -- path` silently empty (09-11-c); shellcheck blind inside `-lc '…'` (09-08c); `uv tree --outdated --format json` (09-13-d); one module per plugin (09-13-d); `plugin list --json` not uniform (09-13-d, machine: plugin_health); `claude doctor`/`mcp list` rc 0 (09-13-d); zsh alias `g` (09-11); chain `checkout -b` with `&&` (09-08d); quoting a scanner shape trips it (09-09b) | L | tool facts, hit once each |
| fn-hook fail-open, `$.fs.read` throws, verdict cached in module scope (09-11-d, 09-13b); retry loop under `set -e` (09-11b); `/plugin-types` session-dependent (09-12); npm 12 `allowScripts` (09-13); packslip/`minimum_release_age` (09-10c); `MISE_LOCKFILE=0` (09-13-d) | O | fixed upstream or by us, or moot (claude is native-only) |

## 5. Options

### (a) Promote the uncovered RECURRING lessons to `feedback_*` + ~150 B index lines
PRO: this is exactly what `memory-index-curation/SKILL.md:51-59` prescribes for "fact is safe in the file, but the HOOK is
where you meet it". It costs about 463 B and keeps the index under 18 KB.
CON: C1 recurred in 8 sessions WHILE its 09-11c hook was eagerly indexed. Eager visibility alone did not stop it, so
this is necessary but not sufficient. #1024 is the real fix. Each new file is another file to curate.
Cite: SKILL.md:51-59; recurrence rows C1/C7a above.

Proposed new files (content sketch; frontmatter `type: feedback`):
1. `feedback_search_own_tracker_before_diagnosing.md` — "Before diagnosing, designing or asking Ray, search OUR record:
   `gh api '/search/issues?q=repo:ray-manaloto/dotfiles+<term>'` (open AND closed; never `gh search issues --repo`, see
   feedback_gh_search_issues_repo_flag_broken), `docs/specs/**` decision tables, `task_plan.md` RULING lines, prior
   handoffs/scratchpads. Why: #877 was filed with a working fix, re-filed as #998, and re-diagnosed by 3 lanes (09-11c).
   Later misses: 09-12b (5, incl. R16 codegen), 09-14-d (5), 09-15 (3), 09-23, 10-01 (4). Recording was never the gap.
   Structural fix pending: #1024/#1028/#1029. Session-handoff §0 'search the tracker even when the next task IS named'."
2. `feedback_gha_rerun_failed_manifest_only.md` — "`mise run gha-rerun` IS `gh run rerun --failed` (mise.toml:669-672).
   On a run where ONLY `manifest` failed, it re-assembles the index from identical children → a NEW index digest ≠ the one
   `dev-tag` recorded → the next `promote` fails STALE under the #1007 guard. Recover with a FULL `gh run rerun <id>`
   (no `--failed`). #1046 OPEN; `mise-tasks-only.md:28` redirects to the trap until it is fixed."
3. `feedback_codex_lane_inherits_global_config.md` — "A codex call that pins no `-m`/`model_reasoning_effort` inherits
   `~/.codex/config.toml` (10-01d: a review lens ran at effort LOW and had to be re-run at high). Pin both per call; read
   the `model:`/`reasoning effort:` banner or the rollout `~/.codex/sessions/**/rollout-*.jsonl` before citing a result.
   Project `.codex/config.toml` IS read and validated (09-15, refuting 09-10's 'inert/regardless' note);
   `--ignore-user-config` suppresses it. It is gitignored and never tracked, so `git clean -xdf` deletes it."

Proposed index lines (Feedback section), measured with `len(line.encode())+1`:
```
- [Search OUR tracker before diagnosing](feedback_search_own_tracker_before_diagnosing.md) — issues, specs, task_plan RULINGs; recorded ≠ retrieved (9+ misses)      [164 B]
- [`gha-rerun` is `--failed`: manifest-only ⇒ stale promote](feedback_gha_rerun_failed_manifest_only.md) — #1046; recover with a FULL `gh run rerun`   [153 B]
- [codex lanes inherit `~/.codex/config.toml`](feedback_codex_lane_inherits_global_config.md) — pin `-m` + effort per call; read the log banner   [146 B]
```
C3 and C4 need no new file. Append a paragraph to `feedback_forbid_tokens_substring_fragile.md` ("a config lever honoured by
the advisory reader and ignored by the enforcing one reads as configurable and is worse than none; #1047,
`assert_escape_hatch_permitted`") and one to `feedback_control_arm_wrong_subsystem.md` ("an arm a permission deny answers
before the code runs certified nothing; suites.toml:1544, #1049"). Optional hook tails: +49 B and +34 B.
**Projected: 16,633 + 463 = 17,096 B (+83 = 17,179 B with both hook tails); 162 lines of 200.** All ≤ 18 KB.

### (b) Fold into existing eager rules instead
- C1 → `research-doc-sources.md:11`, Always item 1 "Never guess": add "…and OUR OWN record first (issues open+closed,
  `docs/specs` decisions, task_plan RULINGs)". The file is 150 lines / 7,761 B against the eager `rule_unscoped` budget of
  200 lines / 24,000 B (`md-size-budgets.md:68-71`), so it fits. Avoid root `AGENTS.md:111`: it is ~500 chars from agnix
  AGM-003's 12,000 (`.claude/CLAUDE.md:4`).
- C5 → `mise-tasks-only.md:28`, the `gha-rerun` row: add "⚠️ `--failed` only; on a manifest-only failure run a FULL
  `gh run rerun <id>` (#1046)". 117 lines, fits.
- C7a → `ai-cli-invocation.md:47` § Codex facts: one bullet on global inheritance and per-call pins. 121 lines, fits. That
  section is already the "re-probe before relying" home.
- Also owed, independent of the memory question: amend `graphify-first.md:7` (truncation is not "unavailable"; re-query
  with a larger budget). That is the 09-12b finding, recurred twice and still unamended.
PRO: eager rules load in EVERY session, worktrees and subagents included (memory is per-repo and machine-local,
`$CC/memory.md:371,397`). Zero index bytes. A reviewed diff.
CON: grows always-loaded context. Needs a branch and PR, plus `lint-docs`, `md_size_budget` and rule-sync if those
files are synced. C5 belongs in code anyway.
Cite: `md-size-budgets.md:68-71`; `.claude/CLAUDE.md:4`.

### (c) Leave them un-indexed (status quo)
PRO: zero bytes, zero work. The facts are not lost (files remain; `memory-index` lists them, `MEMORY.md:8`). C2, C4, C6
and C7b are genuinely fine here.
CON: C1, C5 and C7a have no eager carrier. C5 is worse than invisible, because the eager rule actively points at the trap
(`mise-tasks-only.md:28` → `mise.toml:672`). The checker cannot flag any of this (§6.2). It also skips the skill's
"put it to the user" step (SKILL.md:57-59), which the lane log confirms was not done (G.md, last section).

### (d) Structural fix (#476 + progressive-disclosure spec)
#476 is OPEN and re-scoped as phase 4 of `docs/specs/progressive-disclosure-eager-context.md`. It proposes `--digest`
precompute and an extractor fix (its Options B/D; §5 "blind to 93% of the index"). Proposed additions that target THIS failure:
1. A `memory-index --dropped <old MEMORY.md>` mode: for every entry removed between two index versions, extract the ⭐/⚠️
   lines from the linked file and run the coverage probe above (indexed feedback/reference + eager rules, with control arms),
   failing rc=1 on any "uncovered" lesson until it is promoted, folded or explicitly waived. This turns SKILL.md:51-59 from
   a judgement step into a gate.
2. Promote standing lessons at HANDOFF time: `session-handoff` writes them to `feedback_*` and session files keep only
   status. Un-indexing a session then becomes lossless by construction, and no curation pass has to rediscover lessons.
3. Fix the worktree blind spot (§6) so the gate runs from wherever the curating lane sits.
PRO: fixes the class (feedback_fix_the_class_not_the_instance; feedback_machine_check_not_hand_fix). C5 additionally wants a
code fix (`gha-rerun` refuses `--failed` when only `manifest` failed, or drops `--failed`), per #1046.
CON: needs a PR, tests and review. Does not by itself restore the three lessons now. #476 is deliberately deferred behind the
InstructionsLoaded trace.

### Recommendation
**(a)+(b) hybrid now, (d) as a ticket, (c) for the rest:**
- C5 → (b) rule row now, plus a code fix under #1046. A memory alone is the weakest carrier for a trap the canonical task
  creates.
- C1 → (a) feedback file + index line, and a one-clause (b) in `research-doc-sources.md:11`. #1024 stays the real fix.
- C7a → (b) one bullet in `ai-cli-invocation.md` § Codex facts (CORRECTED form). Promote to (a) only if Ray prefers memory.
- C3, C4 → append to the existing indexed feedback files (0-83 B).
- C2, C6, C7b and the L/O rows → (c).
- Put the per-lesson choice to Ray, as SKILL.md:57-59 requires; the lane skipped this. Projected index ≈ 17.1-17.2 KB.
- Separately: amend `graphify-first.md:7` (truncation) and check the agnix bytes-vs-chars claim against `.claude/CLAUDE.md:4`.

## 6. Checker blind spots — confirmed

### 6.1 Worktree arm: "no memory directory", rc=0
Both arms run 2026-10-03, rc captured to files (`mi_main.log`, `mi_wt.log` beside this report):
| cwd | output | rc |
|---|---|---|
| main checkout `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` (control) | full report: 159 lines / 16,633 B, **149 entries**, no index-only facts | **0** |
| linked worktree `.claude/worktrees/handoff-2026-10-03k` | `memory-index: no memory directory at ~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles--claude-worktrees-handoff-2026-10-03k/memory` | **0** |

The probe discriminates: same task, same index. The control arm finds 149 entries, and the worktree arm audits nothing
yet still exits 0.

Code path (origin/main 186233e4):
- `python/src/dotfiles_setup/main.py:3242`: `project_root = Path(__file__).parent.parent.parent.parent`. That is the
  checkout whose package is running, so in a worktree it is the worktree.
- `memory_index.py:215-227` `memory_dir()`: `transcripts_base(env, home) / encode_cwd(project_root) / "memory"`
  (`command_audit.py:215,226`). It encodes the WORKTREE path.
- `memory_index.py:634-640`: `if not directory.is_dir(): write("no memory directory …"); return 0`. The same pattern
  applies at :650-651 (no MEMORY.md, also return 0).
- Native semantics disagree with the encoding. `$CC/memory.md:371` says "The `<project>` path is derived from the git
  repository, so all worktrees and subdirectories within the same repo share one auto memory directory" (also :397). The
  checker resolves a directory Claude Code never uses.

Proposed fix (two parts, both needed):
1. Resolve like the harness: `memory_dir(main_checkout(project_root))`, reusing `session_common.main_checkout`
   (`session_common.py:172`, the first `git worktree list --porcelain` entry, which `coordinator_handoff.py:839,1267`
   already uses). Also honour `autoMemoryDirectory` (`$CC/memory.md:375`; `settings-reference.md:2661`) if set.
2. A missing directory or index is not a pass. Return a distinct non-zero rc (e.g. 2 = "nothing audited"); `--refs` too.
   Tests need both arms: a real `git worktree add` fixture whose result equals the main-checkout result, and a
   missing-dir case asserting rc≠0. Mutation: revert to `encode_cwd(project_root)` and the worktree test must FAIL.

### 6.2 The un-indexing blind spot (structural, SKILL.md:51-59)
Removing an entry is never a finding. The checker reports un-indexed files under "Unindexed memories (informational)"
(seen in the main-arm report), because their facts are still in the file. "Lost eager visibility" is invisible to it by
design, so the lane's "audit rc=0, 0 index-only, 0 broken" (G.md) could not have caught the issue raised here. This is
§5(d) item 1.

### 6.3 Count discrepancy
The lane log says 17 sessions were un-indexed. The diff gives **18**: the old index's 09-11b entry sat at the top of the
Project section, out of date order. Every removed entry was a session entry; all 116 non-session targets remain linked
and no links are broken. Minor hook-shortening losses seen while reading: the "Pin ONE ref" fact left the
orchestration hook (still in its file, :41); `feedback_gh_run_watch.md:56-62` still RECOMMENDS `gh run watch`, which is
now guard-denied (`do-not.md` #6), a stale memory body unrelated to this curation.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #476, #1024, #1028, #1029, #1046, #1049, #1050, #864, #981 (state/body); origin/main source and rules
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs (`sources/agent-harness-docs/docs/claude-code/memory.md`, `settings-reference.md`) for the memory-dir semantics
