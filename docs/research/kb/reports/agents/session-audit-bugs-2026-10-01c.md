# Session audit 2026-10-01c — §1c bugs row (cold review by ref of every landed squash SHA)

Status: COMPLETE (2026-10-02). 3 codex lenses ran; 11 SHAs codex lens OWED (quota); Opus SAME-FAMILY reads for all. Audited session `7133045d` (`dotfiles-20261001.000`).

## Method

- Author family: from the main transcript's tool_use blocks (Agent launches and `git commit` Bash calls), a scan of
  all 36 subagent transcripts for `codex exec` / `sdlc-team` / `codex-lane` / `git commit`, and each squash
  commit's trailers. **No codex lane authored any commit**: the main transcript has zero `codex-*-implementer`
  launches and zero `sdlc-team`/`codex-lane` invocations; no subagent transcript invokes one either. Every squash
  body carries `Co-Authored-By: Claude Opus 5.5` and #1503's body says "Implemented on Opus (codex usage-limited
  until 2026-10-03)". Control arm: the same scan DID surface the Claude `git commit` calls (main ordinals 239, 494,
  692, 872, 964, 1596, 2407, 4058; subagent commits in native-only-doctor, secret-argv-hunt, parallel-planner,
  orchestration-research, kb-flake-fix, the agy fork), so it can see commits when they exist.
- Therefore every SHA is Anthropic-authored → lens = read-only codex review:
  `mise exec -- codex exec -s read-only --ignore-rules review --commit <full SHA> -c 'sandbox_mode="read-only"'`
  (codex-cli 0.160.0, native `~/.local/bin/codex`), sequential, each bounded at 1200 s by a SECONDS watchdog.
  Raw logs: `/Users/rmanaloto/.claude/jobs/7934b36e/tmp/bugs/<pr>.log`.
- Quota: the coordinator flagged a possible codex quota block until 2026-10-03 12:01. Probed with ONE lens first
  (#1532): it returned a real verdict at rc=0 (13:29 CDT 2026-10-02), so quota was available and the queue ran.

## Author-family table

| PR | squash SHA | author family | evidence |
|---|---|---|---|
| #1503 | 64fd545ec32e | Anthropic (main session) | main ord 494 (commit), 692, 964; body "Implemented on Opus" |
| #1505 | 461ee74b18c6 | Anthropic (main + fork `athis-needs-to`) | main ord 1596; fork transcript l.50 |
| #1510 | 4ba69bb77526 | Anthropic (other Claude session 01CdDRur) | trailers; this session landed it (ord 3191, 3404) |
| #1520 | b1bec698afb9 | Anthropic (main session) | main ord 872, 2407 |
| #1523 | 4facf6433133 | Anthropic (subagent `secret-argv-hunt`) | subagent l.189 commit; main ord 2978 launch |
| #1526 | 40268e738eac | Anthropic (other Claude session 01N9VuNX + subagent `native-cli-followups`) | trailers; main ord 3341 launch, 4154-4193 land |
| #1531 | 63c0b6dd7ac4 | Anthropic (subagent `native-only-doctor`) | subagent l.167, l.278; main ord 2231 |
| #1532 | e6bc086af3dc | Anthropic (main session) | main ord 239 |
| #1533 | 317d91e22bdb | Anthropic (subagent `parallel-planner`) | subagent l.166, l.195; main ord 2729 |
| #1534 | 9fdcaf4c59e6 | Anthropic (subagent `orchestration-research`) | subagent l.272, l.347; main ord 3139 |
| #1535 | aeeb9164de56 | Anthropic (other Claude session 01CdDRur) | trailers; landed ord 4625/4931/4962 |
| KB #831 | e91fb84b0b49 | Anthropic (fork + `kb-flake-fix`) | fork l.107; kb-flake-fix l.1131 |
| KB #832 | 55923b5f1640 | Anthropic (`kb-flake-fix`, kb-hk) | kb-flake-fix l.819 |
| KB #833 | 91a56a82907e | Anthropic (`kb-flake-fix`) | kb-flake-fix l.195 |

## Course correction (coordinator, mid-run)

After 3 lenses had completed (#1532, #1523, #1535 — all rc=0, real verdicts) the coordinator stopped the queue
(codex quota to be preserved until 2026-10-03 ~12:01 local; host load avg 192). The runner was interrupted mid-KB#833
(`KB833.log` has no verdict = not a result); `ps` afterwards shows no `run.sh` and no `codex exec … review` process
alive, so nothing of mine was left running. Every remaining SHA is **codex lens OWED (quota)**, and I did an Opus
cold diff read of each instead, labelled **SAME-FAMILY** (the author is Anthropic, so this is NOT a substitute for the
cross-family lens). All git reads via `/usr/bin/git`, one command at a time.

## Lens results

| PR | rc | verdict |
|---|---|---|
| #1532 | 0 | no actionable regressions ("only clarifies documentation and policy enforcement scope") |
| #1535 | 0 | no actionable regression ("retains the existing dev defaults while adding the defined codegen group… runtime validation was not performed") |
| #1523 | 0 | no actionable regression ("disables environment probing while preserving Docker-inherited container variables… runtime validation was not performed") |

## Cross-check of persisted reviews against the merged SHAs (step 4)

Each prior finding was re-checked at origin/main `aeeb9164` (the audit worktree) — the merged state.

| PR | prior review | residue status at main |
|---|---|---|
| #1503 | `cold-review-1496-2026-10-01.md` (SHIP; F8 LOW gate gap) | F8 ticketed as **#1511** (open). Tracked, not a new finding. |
| #1510 | `cold-review-1329-round2` R2-F1..F7, `/code-review`, spec + standards | R2-F1 closed (`main.py:637-643` `except Exception:`); R2-F2 closed (suites binds `run_codegen_check` call site + `assert main.run_codegen_check(tmp_path) == DriftVerdict.ERROR`); R2-F3 closed by a real-generator formatter test (`tests/test_codegen_check.py:287-301`) + `PYTHONWARNINGS=always::UserWarning` (`codegen_check.py:121`); R2-F4 closed (`test_a_generated_struct_passes_the_repo_ruff_gate`); R2-F5 path-scoped (`doc_refs.py:88`); R2-F6 closed (`test_the_vendored_agent_skill_is_upstream_verbatim`); `refresh.yml` docstring claim removed (0 hits). Eager-import residue ticketed **#1508**. No unfixed residue. |
| #1520 | `cold-review-plugin-health-builtin-2026-10-01.md` F1-F7 | F2-F6 fixed per commit body; **F1 and F7 NOT fixed and NOT ticketed** — see B1 below. |
| #1526 | `2026-10-01-cold-review-native-cli-devcontainer.md` round 2 (#12, N1-N3, F6 text) | All five LOW leftovers resolved at main: `main.py` "no mise copy" 0 hits; on-create no longer fails onCreate on a vendor outage and warns with the rc (`.devcontainer/scripts/on-create.sh:40-45`); "not credential" 0 hits; `schemas/sources.toml:10-12` now calls codex's version a label. |
| #1531 | `cold-review-native-only-doctor-2026-10-01.md` F1-F8 | F1 (MEDIUM) fixed with POSITIVE native roots + contract `workflow.native-only-host-clis` (`suites.toml:2667-2682`) binding `is_relative_to(root)` and the Homebrew-only test; F2 bound (`uninstall_spec(hits[0], …)`); F3 bound (`test_native_only_warnings_reach_the_doctor`); F6 `host_system()` gate (`doctor.py:1274`); F8 contract exists. No residue. |

Control arm for the residue probes: each `grep` that returned 0 on main was paired with a hit for a term known to
be present in the same file (e.g. `builtin_unobservable` → 5 hits in `plugin_health.py`; `test_declared_not_installed_drift`
present in the plugin-health contract tokens while `builtin` is absent from them).

## Findings

### B1 — LOW — #1520 merged with two cold-review findings unfixed and untracked (F1, F7)

- **Claim.** (a) F7: no contract binds the new `@builtin` behaviour — `workflow.plugin-health-gates`
  (`python/verification/suites.toml` ~:2995-3005) pins five pre-existing test names and neither
  `test_declared_builtin_is_unobservable_not_missing` (`tests/test_plugin_health.py:52`) nor
  `test_builtin_exemption_does_not_hide_a_missing_marketplace_plugin` (`:60`), nor the `_is_builtin_id` call site
  (`plugin_health.py:269-271`). Deleting both tests and the exemption keeps `verify` green. (b) F1: a declared
  `@builtin` id naming no real built-in (typo / dropped by a CC upgrade) is moved to `builtin_unobservable`, which no
  consumer renders (`git grep builtin_unobservable` → only `plugin_health.py` and SKILL.md prose), so the doctor shows
  it as OK and the id disappears from every human-facing surface.
- **Evidence.** `cold-review-plugin-health-builtin-2026-10-01.md` rows F1, F7; re-probed at main: the contract
  token list contains no `builtin` string; `builtin_unobservable` has no reader in `doctor.py` or the hook `.ts`.
  Issue search `repo:ray-manaloto/dotfiles builtin created:>=2026-10-01` returns #1509/#1520/#1500/#1508/#1510 —
  none covers F1/F7 (control: the same search shape finds #1511 for the #1503 residue).
- **Disposition: PLAN** (code + contract, not doc-only). task_plan text:
  `- [ ] #1520 residue (audit 2026-10-01c B1): bind the @builtin exemption in workflow.plugin-health-gates
  (tokens: the two new test names + the `_is_builtin_id(plugin_id)` call site in evaluate()), and render
  `builtin_unobservable` in the doctor plugin-health adapter as an INFO line so a typo'd @builtin id stays visible.
  Arm: delete the exemption -> verify rc=1. No grilling needed.`

### B2 — LOW — #1505's "every mise name for agy is in `disable_tools`" is false; the full backend spec escapes

- **Claim.** `.claude/rules/ai-cli-invocation.md:66-67` (added by #1505) says "every mise name for it is in
  `disable_tools`". The project list is `disable_tools = ["antigravity-cli"]` (`mise.toml:158`), and the comment above it
  (`:153-155`) itself records that this list REPLACES the global one in this repo — so the global entries for
  `aqua:google-antigravity/antigravity-cli` (it is in global `auto_install_disable_tools`, not `disable_tools`) and for
  codex/claude (`npm:@openai/codex`, `aqua:openai/codex`, `codex`, `claude-code`, `npm:@anthropic-ai/claude-code`,
  `github:anthropics/claude-code`) are all dropped here. `mise settings get disable_tools` in the repo → `["antigravity-cli"]`.
- **Evidence (live, 4 arms, throwaway dirs, `mise ls --current`):** (a) full spec pinned + `disable_tools=["antigravity-cli"]`
  → tool LISTED (not disabled); (b) full spec, no disable → listed (baseline); (c) short name pinned + short disable → 0
  rows (disable works); (d) full spec pinned + full-spec disable → 0 rows. So the short name does NOT cover the full backend
  spec. Exposure today is latent: the global `config.toml` pins none of the 8 names (count 0; control: 35 other tool pins
  counted by the same grep), and the doctor `native-only` check still catches a PATH hit.
- **Disposition: FIX-NOW (config one-liner + doc claim).** `mise.toml:158`
  old: `disable_tools = ["antigravity-cli"]`
  new: `disable_tools = ["antigravity-cli", "aqua:google-antigravity/antigravity-cli", "codex", "aqua:openai/codex", "npm:@openai/codex", "claude-code", "github:anthropics/claude-code", "npm:@anthropic-ai/claude-code"]`
  (mirrors the global list it replaces). Arm after the edit: `mise settings get disable_tools` in the repo shows all 8.
  If Ray prefers the list stay minimal, the alternative is the doc fix only — `.claude/rules/ai-cli-invocation.md:66-67`
  old: `every mise name for it is in \`disable_tools\`` new: `its short name \`antigravity-cli\` is in this repo's \`disable_tools\` (the full aqua spec is not)`.
  Recommended: the config fix (it makes the rule's claim true). Ray ruling needed only if he wants the list minimal.

### #1523 — Opus SAME-FAMILY read: no defect (plus the codex lens above: no defect)

Reviewed `.devcontainer/devcontainer.json` (+`"userEnvProbe": "none"`) and the `require_lines` contract. Checked the
consumers that could have depended on the login-shell probe: the smoke task runs `scripts/devcontainer-smoke.sh`
which itself wraps tiers in `bash -lc` (`scripts/devcontainer-smoke.sh:41`, `:91`); persistence/doctor execs use
`bash -lc` (`mise.toml:564-620`); `image_lock`/`lock_shared` exec `mise` which is on the image `ENV PATH`
(`.devcontainer/Dockerfile:76-81`: `/usr/local/bin` + `/usr/local/share/mise/shims`). `--remote-env` values in
`lock_shared.py:283-292` are non-secret config paths. `remoteEnv`/`containerEnv` interpolate no credential `localEnv`.
Not verified: a live `ps` arm during a lifecycle hook (host held; the commit body reports one on alpine:3).

### B3 — LOW — #1535 left the pyproject comment calling `codegen` an "isolated group" (codex lens: no defect; Opus SAME-FAMILY read: this doc drift only)

- **Claim.** #1535 made `codegen` a DEFAULT group (`python/pyproject.toml` `[tool.uv] default-groups = ["dev", "codegen"]`,
  ~:65), but the group's own comment still reads "Exact pin, isolated group:" (`python/pyproject.toml:205`). The group is now
  installed into every synced venv (host `.venv`, the devcontainer's `UV_PROJECT_ENVIRONMENT`, `scripts/web-setup.sh:61`).
- **Checked, not a defect:** no caller uses `--no-default-groups`/`--only-group`/`--no-dev` (`git grep` over `.devcontainer`,
  `.github`, `mise.toml`, `hk.pkl`, `python/src`, `scripts` → 0; control: the same grep finds `uv sync --locked` at `mise.toml:8`),
  so nothing silently drops or double-installs the group; `uv.lock` already resolved all groups together, so no new conflict.
- **Disposition: FIX-NOW (comment).** `python/pyproject.toml:205`
  old: `# Exact pin, isolated group: the \`codegen\`/\`codegen-check\` mise tasks run it`
  new: `# Exact pin, DEFAULT group since #1535 (so plain syncs keep it); the \`codegen\`/\`codegen-check\` mise tasks run it`

### B4 — LOW — #1503's reserved-name arm skips on any host that lags the moving vendored pin, not the rule's fixed version

- **Claim.** `tests/test_fnhook_gates.py` `test_reserved_name_fixture_is_rejected_by_the_pinned_claude` skips when
  `running < pin`, where `pin = fnhook_gates.claude_code_pin(REPO_ROOT)` — the `schemas/sources.toml` `claude-code` version that
  `refresh.yml`'s schema refresh bumps. The rule it tests arrived in a FIXED version, 2.1.287 (its own docstring). After the next
  pin bump (say 2.1.290), a host on 2.1.288 — which does enforce the rule — silently skips, so the arm stops running exactly when
  the host is merely one refresh behind. A skip is a pass-shaped outcome; the arm can lose its control without anyone noticing.
- **Evidence.** diff of 64fd545e, `tests/test_fnhook_gates.py` new lines ~:385-405 (`pin = tuple(... claude_code_pin(...))`;
  `if running is None or running < pin: pytest.skip(...)`). Control: the production gate (hk `fnhook_gates` + M5 in
  `cold-review-1496-2026-10-01.md` F4) does not depend on this comparison, so the defect is confined to this arm.
- **Disposition: PLAN.** task_plan text:
  `- [ ] #1503 residue (audit 2026-10-01c B4): in tests/test_fnhook_gates.py bind the reserved-name arm's skip to a constant
  RESERVED_PREFIX_SINCE = (2, 1, 287) instead of claude_code_pin(); arm: set the host-version stub to 2.1.288 with pin 2.1.290 ->
  the test must RUN (not skip). No grilling.`

### #1520 — Opus SAME-FAMILY read of the squash: no new defect

`_is_builtin_id` (`plugin_health.py` ~:100-108) now matches CC's own predicate (one `@`, non-empty name, marketplace
exactly `builtin`), and the control test pins `@builtin`, `a@b@builtin`, `x@notbuiltin`, `builtin@market`. The two residues
the prior cold review raised and the merge did not close are B1 above. codex lens OWED (quota).

### B5 — LOW — #1531: agy's native root is a FILE path that `native_roots()` resolves, so anything AT `~/.local/bin/agy` is "native"

- **Claim.** `DEFAULT_NATIVE_ONLY["agy"].native = ("~/.local/bin/agy",)` (`python/src/dotfiles_setup/path_drift.py:416-418`)
  names the binary itself, and `native_roots()` (`:536-541`) calls `.resolve()` on it. If `~/.local/bin/agy` is ever a
  symlink, the root BECOMES its target, and `is_native()` (`:544-547`) compares `hit.resolve()` to that same target — always
  equal. So a non-mise copy that lands at that path as a symlink (an npm/bun global with prefix `~/.local`, a hand `ln -s` to a
  Homebrew cask) is classified native and produces zero findings. mise copies are still caught because `_from_mise` runs
  first (`:618`); codex/claude are unaffected because their roots are vendor-owned DIRECTORIES
  (`~/.codex/packages/standalone`, `~/.local/share/claude/versions`).
- **Evidence.** Code read at main; the docstring (`:407`) records that today `~/.local/bin/agy` is a regular Mach-O file, so
  the hole is latent, not live. Control: for codex, a symlink `~/.local/bin/codex -> /opt/homebrew/Caskroom/...` resolves
  outside `~/.codex/packages/standalone` → `is_native` false → FAIL (the positive design works where the root is a dir).
  Not run live (host load hold); this is a static read.
- **Disposition: PLAN.** task_plan text:
  `- [ ] #1531 residue (audit 2026-10-01c B5): native_roots() must not resolve a FILE root through a symlink — for a root
  that names a file, require hit == root (unresolved) AND hit.resolve() not under a mise dir or a _FOREIGN_SOURCES marker;
  or point agy's root at the directory agy's own installer owns (probe `agy update` layout first). Arm: tmp home with
  ~/.local/bin/agy -> tmp/.bun/.../agy must FAIL; regular file must pass. No grilling.`

### B6 — LOW — #1533's merged skill lacks the blocked-lane check its own author wrote the next morning; the fix is unpushed

- **Claim.** The merged `parallel-work-split` skill (`.claude/skills/parallel-work-split/SKILL.md` §5-§6, and the `.agents`
  mirror) has no step to detect a lane parked on a permission prompt (`state == "blocked"`), no `CWD:` line forbidding
  `EnterWorktree` in the brief, and no warning that `claude agents --json --all` rows can lack `id`. Commit `faad62f8`
  ("launch bg lanes inside their worktree; watch for blocked lanes") adds all three, with the measured incident (seven lanes
  parked ~11h on EnterWorktree's relocation prompt) — but it sits only on local branch `docs/fanout-launch-fixes`, whose push
  died rc=141 (audit-common: "push rc=141, chain broke"). So the shipped skill still teaches the monitoring that missed an
  11-hour stall.
- **Evidence.** `/usr/bin/git log docs/fanout-launch-fixes` in the main checkout → `faad62f8` atop `aeeb9164`;
  `git diff --stat origin/main...docs/fanout-launch-fixes` → only the two SKILL.md copies, +58/-12. Control: `origin/main`'s
  SKILL.md contains `claude agents --json --all` (present) and no `blocked` token.
- **Disposition: PLAN** (doc-only, but it is an existing unpushed commit, so the fix is to ship it, not to re-author it):
  `- [ ] Ship docs/fanout-launch-fixes (faad62f8, parallel-work-split blocked-lane watch + CWD brief line) — audit 2026-10-01c B6;
  its push died rc=141. Re-push, then mise run ship from the main checkout; lint-docs applies.`

### #1531 — Opus SAME-FAMILY read: B5 only

Read `path_drift.py:391-700` and the doctor adapter at main. The prior cold review's F1-F8 are closed (see cross-check). The
double FAIL for a mise-first/no-native host is deliberate (`test_a_homebrew_only_host_fails_twice`). codex lens OWED (quota).

### #1533 — Opus SAME-FAMILY read: B6 only

`git merge-tree --write-tree --name-only --no-messages` rc semantics (1 = conflict) and the `git rebase --onto` advice are
correct. codex lens OWED (quota).

### B2 (KB side) — the same overclaim in knowledge-base #831

KB `mise.toml` (at `e91fb84b`, `[settings] disable_tools`, ~:259-272) says it "carries every mise name for the three
native-installer-only CLIs", and the comment at ~:239-245 says "every mise name for them is in `[settings] disable_tools`".
The list has 7 entries and omits `aqua:google-antigravity/antigravity-cli` and `github:openai/codex` — the B2 arms above show a
full backend spec is NOT covered by its short name. Latent (no KB config pins either). **Disposition: FIX-NOW** (KB, config):
append `"aqua:google-antigravity/antigravity-cli",` and `"github:openai/codex",` to that list (both already appear in KB's own
`live_receipt_scope.EXTRACTION_LOCK_TOOLS` / dotfiles' `path_drift` spec tables as real spellings). Lands via `kb-ship`.

### B7 — LOW — KB #832 removed the only per-repo hk hook install, and KB has no check that hooks exist

- **Claim.** KB `mise.toml` `[hooks] postinstall` went from `mise reshim && hk install --mise` to `mise reshim` (#832, citing
  jdx/hk#1376), delegating hooks to a once-per-machine `hk install --global --mise`. dotfiles pairs that same move with a doctor
  `hk-hooks` check that reports when the global install has not run (`do-not.md` #9). KB has no equivalent: `git grep` at
  `91a56a82` for `hk install|hk-hooks|hook\.hk` outside sources/research finds only the new comment and the retired-test text.
  On a machine (or a fresh clone) without the global install, KB commits run with NO pre-commit gate and nothing says so.
- **Evidence.** KB #832 diff (`mise.toml` `[hooks]`, `tool_sync.py` hook-line tolerance removed). Issue search
  `repo:ray-manaloto/knowledge-base hk install global` → no open issue for a presence check (control: `hk-2-latest` → 26 hits,
  so the search answers).
- **Disposition: PLAN.** task_plan text (KB):
  `- [ ] KB: port dotfiles' hk-hooks presence check (doctor / kb-handoff-check) so a missing global \`hk install --global --mise\`
  is reported — audit 2026-10-01c B7 (KB #832 removed the postinstall hook install). Arm: unset global hook.hk-* -> check reports;
  set -> silent. No grilling.`

### KB #833 — Opus SAME-FAMILY read: no defect

`[tool.uv] default-groups = ["dev", "codegen"]` parses as one `[tool.uv]` table (`tomllib` → `['dev','codegen']`; the
`[tool.uv.sources]` sub-table follows it, no duplicate header). CLAUDE.md row updated in the same diff. codex lens OWED (quota).

### KB #832 — Opus SAME-FAMILY read: B7 only

`(Builtins.gitleaks) { scan = "staged" }` matches hk 2.x's documented replacement for the removed `gitleaks_staged`;
`min_hk_version` raised to 2.4.0 so a 1.x binary refuses; `sources/rumdl.manifest`'s stale "pinned here: v0.2.58" header
(pre-existing drift vs ref v0.2.62) is corrected to v0.2.78. codex lens OWED (quota).

### KB #831 — Opus SAME-FAMILY read: B2 (KB side) only

`live_receipt_scope._only_exempt_lock_tools_changed` fails closed (non-`tools` change, unparsable/oversized lock → evidence
required) and keeps every extraction-relevant spelling; `review._native_only` / `disabled_tools` fail toward comparing the pin
(the refusing side); `mod_runtime` now judges by files written, not child rc, and still returns NOT_RUN without the binary.
Not exercised live (host hold). codex lens OWED (quota).

### #1526, #1510, #1534 — scope of the Opus read

- **#1526** (41 files): not re-read line by line; it had six persisted reviews incl. a two-round cold review. I re-checked every
  round-2 residue at main (table above): all closed. codex lens OWED (quota).
- **#1510**: EXCLUDED the generated/vendored bulk — `docs/research/mintlify-cache/datamodel-code-generator/llms-full.txt`
  (+43,508), `llms.txt`, the vendored `datamodel-code-generator` skill `references/*.md` in both `.claude` and `.agents` copies
  (3×2 files, ~887 lines each set), `docs/research/kb/raw/.../links/*`, `python/uv.lock`, the persisted review reports, and
  `python/src/dotfiles_setup/generated/*`. Hand-written files (`codegen_check.py`, `main.py` dispatcher, `pyproject.toml`
  `[tool.datamodel-codegen]`, `schemas/drift-verdict.schema.json`, `schemas/templates/msgspec.jinja2`, `hk.pkl`, `mise.toml`,
  `suites.toml`, `doc_refs.py`, `tests/test_codegen_check.py`) were read for the prior reviews' residues: all closed or ticketed
  (#1508). No new defect found. codex lens OWED (quota).
- **#1534**: EXCLUDED the vendored mirror `docs/research/kb/raw/herdr-docs-2026-10-02/**` (29 files, ~12.4k lines). Hand-written:
  `orchestration-parallel-coordination-2026-10-02.md` (research report, prose) and
  `docs/research/saved-searches/orchestration-2026-10-02.toml` (parses: `schema_version`, 26 `watch`, 29 `result`). No code; no
  defect found. codex lens OWED (quota).

### B8 — MED (process) — 11 of 14 landed SHAs never got their cross-family lens

- **Claim.** `.claude/skills/codex-sdlc-team/SKILL.md:182-187` requires one cold review BY REF from a DIFFERENT family for every
  behavior-bearing diff; every SHA here is Anthropic-authored, so that lens is codex. The session landed all 14 with codex usage
  exhausted (#1503's body: "codex usage-limited until 2026-10-03"); the Opus cold reviews it did run are SAME-FAMILY fallbacks
  (`cold-review-1496-2026-10-01.md:5` says so itself). This audit ran 3 lenses (#1532, #1523, #1535 — all clean) before the
  coordinator stopped the queue for quota.
- **Disposition: PLAN.** task_plan text:
  `- [ ] OWED codex lens (>= 2026-10-03 12:01 local), read-only, sequential, one per SHA (audit 2026-10-01c B8):
  dotfiles 64fd545ec32e (#1503) 461ee74b18c6 (#1505) 4ba69bb77526 (#1510) b1bec698afb9 (#1520) 40268e738eac (#1526)
  63c0b6dd7ac4 (#1531) 317d91e22bdb (#1533) 9fdcaf4c59e6 (#1534); KB e91fb84b0b49 (#831) 55923b5f1640 (#832)
  91a56a82907e (#833). Command: mise exec -- codex exec -s read-only --ignore-rules review --commit <full SHA>
  -c 'sandbox_mode="read-only"'. Runner + logs: /Users/rmanaloto/.claude/jobs/7934b36e/tmp/bugs/run.sh (skips SHAs whose log
  already ends in rc=). Done: #1532, #1523, #1535 (clean).`

## Summary

| sev | id | PR | disposition |
|---|---|---|---|
| MED | B8 | 11 SHAs | PLAN (owed codex lens) |
| LOW | B1 | #1520 | PLAN |
| LOW | B2 | #1505 + KB #831 | FIX-NOW (config one-liner each) |
| LOW | B3 | #1535 | FIX-NOW (comment) |
| LOW | B4 | #1503 | PLAN |
| LOW | B5 | #1531 | PLAN |
| LOW | B6 | #1533 | PLAN (ship unpushed faad62f8) |
| LOW | B7 | KB #832 | PLAN |

No HIGH. No defect found in #1523 (both lenses), #1532 (codex), #1535 code (codex; B3 is its comment), KB #833.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the 11 squash SHAs, prior review reports, issue search (#1508, #1509, #1511)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — KB #831/#832/#833 squash SHAs, issue search
