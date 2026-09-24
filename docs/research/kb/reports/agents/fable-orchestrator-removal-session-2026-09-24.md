# fable-orchestrator removal — delegated session results (2026-09-24)

Session: a separate headless Claude Code session (Opus 5.5), started by coordinator `a6750a24` because its
context was full. Ray's instruction (verbatim in the brief): remove fable-orchestrator globally and from every
project if it is no longer needed. Then run code review, fix, `/verify`, fix, and `/session-handoff`. Only
this report goes back to the coordinator. It is written incrementally.

Branches: dotfiles `chore/remove-fable-orchestrator` (from `3db81d8e`); knowledge-base
`chore/remove-fable-orchestrator` (from `e8fe42ae` = origin/main). **Nothing is pushed or shipped** (per the brief).

## Step 0 — is fable-orchestrator still needed? Dependency inventory

Probes:
- `git grep` over the live paths of both repos. Excluded: historical records (research reports, specs,
  receipts, goal history, direction, artifacts). Control arm: the same grep hits
  `.claude/settings.json:194`, which is known to be present.
- `jq` over `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json` and
  `~/.claude/plugins/known_marketplaces.json`.
- A `find` of every `.claude/settings*.json` under `~/dev`, to maxdepth 6. It examined 47 files. Control arm:
  `antigravity` hits the same two repos.
- `grep -n` over `~/.codex/config.toml`, keeping only the plugin, marketplace and hook-state lines. No values
  were read.

### Where it is installed or enabled

| Scope | State |
|---|---|
| User-global `~/.claude/settings.json` `enabledPlugins` | **not enabled** (`{}` for fable/claudex) |
| `installed_plugins.json` | 1.21.0 (sha `78f9cb5`), **project scope only**: dotfiles and knowledge-base |
| `known_marketplaces.json` | `fable-orchestrator` → `mar3co/fable-orchestrator` (upstream is 404) |
| Other projects under `~/dev` | none. The only other hits are git worktrees of dotfiles (2) and knowledge-base (5). Those are branches of the same repos and inherit the change when they rebase onto main. |
| `~/.claude.json` | only `skillUsage`/`pluginUsage` telemetry keys, no config |
| `~/.codex/config.toml` | `[plugins."fable-orchestrator@fable-orchestrator"] enabled=true` (:80), hook trust (:436), `[marketplaces.fable-orchestrator]` (:601); `[plugins."claudex-loop@claudex-loop"] enabled=true` (:254), `[marketplaces.claudex-loop]` (:653) |

### Capabilities and their replacements

| Plugin capability | Live dependents | Replacement | Exists? |
|---|---|---|---|
| Orchestration skill as "authoritative routing" (eager trigger) | dotfiles `.claude/CLAUDE.md:45`; KB `.claude/CLAUDE.md:31`; `rule-sync.toml` lines; `orchestration.trigger-armed` contract | A routing-doctrine section in `codex-sdlc-team/SKILL.md` (dotfiles) and `orchestrator-routing` (KB), plus a new trigger line naming it | built in this session (D3/K6) |
| Mode/effort lines (`implementation lane = codex`, `effort = xhigh`) | both CLAUDE.md files; `mode-line-declared`, `config-placement` contracts; `rule-sync.toml` | none needed. They configure only the plugin's own lanes. Our wrappers pin effort in argv. | n/a, deleted |
| `codex-implementer` | KB CLAUDE.md:34; KB `orchestrator-routing:21` | dotfiles `codex-{sol,astra}-implementer`; KB stopgap `kb-codex-implementer` (K4) | dotfiles yes; KB built |
| `codex-reviewer` (cold review of a Claude-authored diff) | KB `kb-tool-review.js:188` (**the only runtime dispatch**); KB `kb-review` skill; dotfiles lane table (no row) | KB `kb-codex-astra-reviewer`; dotfiles `mise exec -- codex exec -s read-only --ignore-rules review …` (the §1c form) | yes |
| `fable-advisor` | dotfiles `token-routing.md:8`, `codex-{sol,astra}-advisor` fallbacks; KB CLAUDE.md:34 | `claude-advisor` in both repos (dotfiles#1294 design; KB renames `kb-advisor`) | built |
| `premise-verifier` | dotfiles CLAUDE.md:69; KB review.py docstrings | repo-owned `premise-verifier` port (MIT, sha `78f9cb5`), both repos | built |
| `grok-*` lanes | none (grok is not installed) | n/a | n/a |
| PreToolUse `premise-gate.sh` hook | matches only the plugin's own implementer names (`premise-gate.sh:132-133`), so it is dark for ours | none needed | n/a |
| `doctor.sh` (eval `--live`) | dotfiles `eval_cases.py:54-57`, `main.py:1010`, `mise.toml:1331`; KB `evals.py:489-520`, `mise.toml:455` | none. It points at a 1.14.0 path that is gone and can only skip. | n/a, removed |
| codex-side plugin + `claudex-loop` | codex sessions load the plugin's skills and hook | the codex-side SDLC team (`.codex/agents/`) and `mise run sdlc-team` | yes |

**Decision: no longer needed.** Every capability has an in-repo replacement or is dead. Proceeding with removal
in both repos, at user-global/project install scope and on the codex side.

## Changes

Ruling recorded: `task_plan.md` § Current Phase, "SUPERSEDED 2026-09-24" paragraph (the file is gitignored, so
coordinator-local).

| Repo | Commit | Tickets | What |
|---|---|---|---|
| dotfiles | `9ed414a0` | #1311-#1315 | Additive parity. Eval `--live` doctor retired. rule-sync `agents` axis. Workflow agentType roster test. `claude-advisor` + `premise-verifier` (MIT port, 78f9cb5). token-routing.md is the escalation source. Advisor/implementer pointers rewritten, mirror regenerated. `owned-agents` contract. Glossary rows. Doctrine section in codex-sdlc-team. New trigger line beside the old one. |

| knowledge-base | `76f95cfa` | KB#793-#796 | Additive parity. kb-tool-review Review phase → `kb-codex-astra-reviewer`, plus a roster test (FAILED on the pre-change workflow, passes after). kb-review default cold lane `cold:codex-astra`. `kb-advisor`→`claude-advisor` (md + codex twin). `premise-verifier` port + codex twin. Stopgap `kb-codex-implementer` + twin. New trigger line, byte-identical to dotfiles'. orchestrator-routing de-plugined. |
| dotfiles | `2c8cc745` | #1316 | Removal. rule-sync set swapped (plugin dropped, new trigger, `agents` axis declared). settings keys removed. CLAUDE.md block rewritten, with a new "Cold review of a Claude-authored diff" row. Contracts rewritten/deleted. New `orchestration.no-plugin-references` + verify `path_globs`. Pointer rewrites. |
| knowledge-base | `d94b0e82` | KB#797 | Removal. Eval doctor shell-out + case + tests removed. settings keys removed. Old trigger/mode lines removed. Docstrings corrected. New `tests/test_no_plugin_references.py`. |
| dotfiles | `d4b0b5c4` | #1317 | Doctor check `removed-plugins`: `doctor.toml [removed_plugins]` plus `removed_plugins.py`. |

FAIL arms run for `9ed414a0`, each with its control:
- `owned-agents`: FAILS on `model: fable`→`opus` and on deleting `premise-verifier.md`; passes restored.
- The agents-axis tests: 2 FAIL with the gap filter disabled (`and False`); 26/26 pass restored.
- The roster test FAILS with `fable-orchestrator:gate-runner` planted in `gated-implementation.js`; passes restored.

FAIL arms for the later commits:
- `2c8cc745`:
  - `no-plugin-references` FAILS with `fable-orchestrator:fable-advisor` planted in `.claude/agents/claude-advisor.md`, and FAILS with the plugin key re-added to `settings.json`.
  - rule-sync FAILS ("knowledge-base: missing agent `premise-verifier`") when that KB file is moved away.
  - The live-path grep for `fable-orchestrator:` hits only the contract's own 2 lines. Control: `codex-sol-implementer` = 15 hits.
- `d94b0e82`: `test_no_plugin_references` FAILS with a reference planted in the real KB `claude-advisor.md`. Control: `antigravity@` hits the same globs.
- `d4b0b5c4`: doctor `removed-plugins` reported **7 findings BEFORE** the uninstall (positive control) and **0 AFTER**.

### User-global and codex scope (done this session; Ray authorized "globally")

| Step | Command (native) | Result |
|---|---|---|
| Backup | `tar` of `~/.claude/plugins/{cache,marketplaces}/fable-orchestrator` → dotfiles `.agent/state/fable-orchestrator-1.21.0-cache-backup-2026-09-24.tgz` (gitignored, 417 KB). The upstream is 404, so this and KB's `sources/fable-orchestrator/` clone are the only recovery path. | ok |
| Claude project scope ×2 | `claude plugin uninstall fable-orchestrator@fable-orchestrator --scope project` in dotfiles and knowledge-base | `outcome: ok` ×2 |
| Claude marketplace | `claude plugin marketplace remove fable-orchestrator` | removed. `installed_plugins.json` and `known_marketplaces.json` now have 0 fable keys. The cache dir `~/.claude/plugins/cache/fable-orchestrator` still exists (orphaned; harness GC will remove it) |
| Codex check | `ps` showed no `codex exec`/`review` lane running, only app-server daemons | ok |
| Codex backup | `~/.codex/config.toml.pre-fable-removal-2026-09-24` (mode 600, beside the original) | ok |
| Codex plugin + marketplace | `codex plugin remove fable-orchestrator@fable-orchestrator`, then `codex plugin marketplace remove fable-orchestrator` | removed |
| Codex hook trust | no native command. Removed the 2-line `[hooks.state."fable-orchestrator@…:pre_tool_use:0:0"]` table by text edit; the file re-parses as TOML | removed |
| claudex-loop | no native disable (only `remove`). Set `enabled = false`, per the ruling "DISABLE". `codex plugin list` → `installed, disabled` | disabled |
| Other projects | none enable it. 7 git worktrees of dotfiles/KB on older branches still carry the key in their `settings.json`; each inherits the removal when it rebases on main | noted |

## GitHub issues filed

- **dotfiles#1362**: sdlc_team resolves codex through the mise shim to argv[0]=`mise`, so codex never runs.
  Re-probed live this session: `which` → shim → `resolve()` → `~/.local/bin/mise`. Control:
  `~/.local/bin/codex` resolves to the native 0.156.1 binary.

## Code review (step 1) and fixes (step 2)

**Choice: I ran both reviewers plus a cross-family lens.** The repo's own doctrine (the #1310 story 13 review
doctrine, now in `codex-sdlc-team` § Review tiers) assigns each tool a different question:
- the bundled `/code-review` answers "correctness bugs in any behaviour-bearing diff";
- `/mattpocock-skills:code-review` answers "Standards and Spec for a spec'd diff". This change is both, with spec
  #1310 and 14 tickets.

Every diff was Claude-authored, so the doctrine also requires a codex lens:
`mise exec -- codex exec -s read-only --ignore-rules review --base <ref> -c 'sandbox_mode="read-only"'`, with no
prompt. A first try with a `-` prompt failed rc=2, because `--base` cannot be combined with `[PROMPT]`.

Verbatim reports (this directory):
- `removal-review-bundled-2026-09-24.md` — 10 findings.
- `removal-review-standards-2026-09-24.md` — 2 hard + 7 judgement.
- `removal-review-spec-2026-09-24.md` — 4 missing, 4 creep, 3 wrong.
- `removal-review-codex-2026-09-24.md`: dotfiles 2×P2, knowledge-base 1×P1. The knowledge-base run used npm codex
  0.154.0, because that repo still pins it; dotfiles resolved native 0.156.1.

Dispositions (duplicates merged; B = bundled, S = standards, P = spec, C = codex):

| # | Finding | Disposition |
|---|---|---|
| B1, C-kb-P1 | kb-tool-review → `kb-codex-astra-reviewer` cannot review a report dir (diff-only, needs `KB_LANE`) | **FIXED.** The agent (md + codex twin) gained an "Artifact review" section: `kb-codex` exec mode, read-only, no receipt. The workflow prompt now names artifact mode, the author family and a per-tool `KB_LANE` (`laneRoot` arg). |
| B2 | astra reviewer still says `cold:codex` is the default and cites the deleted mode line (md, toml, lanes.md) | **FIXED** in all three. A small diff stays with Astra unless Sol is requested by name. |
| B3 | `kb-codex-implementer` runs a 3000s lane as one foreground call (600s cap) | **FIXED.** Background launch, `lane.log` + `lane.rc`, poll in <600s slices (md + twin). |
| B4, S2 | CLAUDE.md lane row: raw command without `sandbox_mode`, a second copy of the skill's command | **FIXED.** The row now points to the single copy in `codex-sdlc-team` § Review tiers. The mechanism stays out of scope (#1310; #1297 canary). |
| B5 | KB `.codex/agents/claude-advisor.toml` would run a "Fable" advisor on GPT | **FIXED.** Twin deleted. |
| B6 | disabled codex plugin's hook trust still reported | **FIXED.** Now exempt. Arm: the test FAILS with the exemption removed. |
| B7, S1, C-df-1 | corrupt/unreadable registry reads as clean | **FIXED.** Missing = empty; unreadable/unparsable = "went unchecked" finding (JSON and TOML alike). Arm: the test FAILS with the old swallow restored. |
| B8, C-df-2 | cache dir and settings `extraKnownMarketplaces` not checked | **FIXED.** Both added. The live host arm fired on the surviving `~/.claude/plugins/cache/fable-orchestrator`, which I then removed (backup verified). Doctor → 0 findings. |
| B9, P-c3 | dotfiles roster regex single-quote only | **FIXED.** It accepts `'`, `"` and backticks. The new double-quote/backtick test FAILS with the old regex. |
| B10, S3, P-a4 | `codex-only-lanes` description cites a deleted contract and the plugin | **FIXED.** Rewritten. |
| P-a1 | KB#794 "a review invoked with no lane uses `cold:codex-astra`, asserted at the CLI seam" | **PARTIAL, ruling needed.** No code default exists: `review-receipt` REQUIRES `--lanes` (a receipt must name what ran). I updated the CLI example. The default lives in the skill. See Q2. |
| P-a1b | legacy-spelling test | **FIXED.** `test_report_path_strips_the_lane_variant` now also pins `cold:codex-astra` → `-cold.md`. |
| P-a2 | #1315 Opus cold review + premise-verifier pass over the doctrine | **DONE** this step: an Opus lane carrying the `premise-verifier.md` instructions (the new type cannot be spawned in a session that predates it). Report: `removal-premise-verifier-doctrine-2026-09-24.md`. The Opus cold reviews are the standards/spec lanes above. |
| P-a3 | per-ticket live arms (#1314, KB#795/#796 spawns) | **OWED** (next session). New agent types load only at session start. #1319 is also blocked by #1362 for its sdlc-team arm. |
| P-b1 | concrete `codex exec review` command is scope creep | **KEPT, justified.** One copy, in the skill. It already existed in `/session-handoff` §1c (prior session), labelled pending #1297. |
| P-b2 | KB codex twins for new agents | **KEPT, justified.** KB convention: every `.claude/agents` file has a `.codex/agents` twin (the root CLAUDE.md roster). The claude-advisor twin was removed (B5). |
| P-b3 | premise-verifier `effort: xhigh`; header said "unedited" | **FIXED.** `effort` removed (spec: "Opus, Read/Grep/Glob"). The header now states both edits: a shortened description and one formatter-removed blank line. |
| P-b4 | doctor flags installs in ANY project | **REFUTED.** Ray ruled a global removal ("globally and in all projects"), so a machine-level reinstall anywhere is the regression. |
| P-c1 | KB states the escalation triggers 3× | **FIXED.** The single source is the KB `.claude/CLAUDE.md` advisor line; the agent description and body link to it. |
| P-c2 | `owned-agents` substring model pin passes `model: opus-4` | **FIXED.** Now `require_lines`/`per_path_lines`. Arm: `model: fable-x` → verify rc=1. |
| S4 | roster helper duplicated across repos | **KEPT.** Spec #1310 asks for "a test in each repo". A shared `kb_setup` helper would add a cross-repo SHA-pin hop to a test. Recorded as a later consolidation candidate. |
| S5 | forbid scopes diverge (dotfiles lacked `.claude/rules/*.md`) | **FIXED.** Added. |
| S6 | `_MODE_LINE` misnamed | **FIXED.** Renamed to `_REAL_LINE`. |
| S7 | live-case axis now unused (`LIVE_TIMEOUT`, `Case.live`, `--live`) | **PARTIAL.** Removed `LIVE_TIMEOUT`, which had no other reference. Kept `Case.live`/`--live`: a shared-runner capability with its own tests (`test_evals.py:135,158`), consumed by both repos. Removing it is a cross-repo API change outside #1310. |
| S8 | doctrine restated in 4 places | **KEPT.** Spec risk "two doctrine copies drift"; rule-sync gates presence only. The content-hash axis is a named later ticket (#1310 Out of Scope). |
| S9 | deleted `[removed_plugins]` block reads green | **FIXED.** Now a finding. Tested. |

Fix commits: dotfiles `1bd184b8`, knowledge-base `0fd45960`.

## /verify (step 3) and fixes (step 4)

Surfaces driven after `1bd184b8` / `0fd45960`. Each rc is file-captured under dotfiles
`.agent/logs/verify-removal/`.

| Surface | Drive | Result |
|---|---|---|
| PreToolUse guard | `scripts/pretooluse-guard.sh` with `gh pr create --fill` / `git status` | deny JSON / empty allow, rc=0 both: the guard is intact |
| SessionStart doctor | the hook's own form `DOTFILES_AMBIENT_PATH=… mise -C … run doctor` | rc=0 with **0** `removed-plugins` findings. Positive arm: `extraKnownMarketplaces.fable-orchestrator` planted in `settings.local.json` → `DRIFT doctor[removed-plugins] … declares marketplace` (restored, `cmp` identical). The SessionStart aggregate listing-budget drift (48,589 > 48,110 chars) is **gone** after the removal |
| `mise run eval` | dotfiles | rc=0 (5 cases, none live) |
| `mise run rule-sync` | vs knowledge-base branch | rc=0: 1 plugin + 1 line + 22 rules + **2 agents**; agents axis in the report `dotfiles=25, knowledge-base=11, shared=2` |
| `mise run verify` | dotfiles | rc=0, 165 passed / 0 failed |
| `mise run plugin-health` (live) | dotfiles | **rc=1**: `declared_disabled_here: ["ponytail@ponytail"]`. It is **not** from this change: `settings.json` enables ponytail (same at `3db81d8e`), and the gitignored operator `settings.local.json` sets it `false`. No fable key in any list. See Q3 |
| `claude plugin list --json` | both repo dirs | 0 `fable` entries (control: 2 `antigravity` entries) |
| `mise exec -- codex plugin list` | — | no fable-orchestrator. `claudex-loop@claudex-loop  installed, disabled`. (`get-fable@openai-curated-remote` is an unrelated OpenAI catalog plugin, not installed) |
| knowledge-base `mise run eval` | — | rc=0, 6 passed, 1 skip = `tier2.kb-retrieval` (`--slow` only, by design) |

**Step 4:** /verify found nothing caused by this change, so there are no code fixes. The four remaining doctor
DRIFT lines were all present at this session's SessionStart and are owed elsewhere:
- antigravity description length;
- graphify path-binary 0.9.67 vs 0.9.65;
- claude-code pin 2.1.278 → 2.1.281 (Phase 10 order item 1);
- codex-schema generated by 0.154.0 (`mise run codex-schema-generate`, Phase 10 step 2).

## Gate rcs

Every rc is file-captured (never a pipe) and was read before advancing.

| Commit | Gates |
|---|---|
| dotfiles `9ed414a0` | lint 0 · pytest 0 (3768) · verify 0 (166/0) · lint-docs 0 · rule-sync 0 · mirrors 0 |
| dotfiles `2c8cc745` | lint 0 · pytest 0 (3770) · verify 0 (165/0) · lint-docs 0 · rule-sync 0 · eval 0 · mirrors 0 |
| dotfiles `d4b0b5c4` | lint 0 before the TEST-INDEX row was added (that row carried an agnix warning, which the pre-commit did not catch; fixed in `1bd184b8`) · pytest 0 (3778) · verify 0 |
| dotfiles `1bd184b8` | lint 0 · pytest 0 (3783) · verify 0 (165/0) · lint-docs 0 · rule-sync 0 · eval 0 · mirrors 0 |
| knowledge-base `76f95cfa` | kb-gates: lint/brain-audit/eval/graph-size/hk-test/funnel/manifest/catalog/lock-drift/mod-runtime PASS; `mise run test` 0 serially (the first run hit a 120 s MCP-handshake timeout while dotfiles pytest ran concurrently; it passes alone) · lint-docs 0 |
| knowledge-base `d94b0e82` | kb-gates 11/11 PASS · lint-docs 0 |
| knowledge-base `0fd45960` | kb-gates 11/11 PASS on the code fixes; after the doc-only follow-ups, lint 0 · lint-docs 0 · md-budget/forbid/roster tests 0 |

## Open questions for Ray (this was a headless run, so none were asked)

1. **Ship order.** Nothing is pushed. rule-sync in CI reads knowledge-base `main`, so KB must land first.
   - Recommended: `kb-ship` KB (both commits as one PR, or parity then removal), `kb-land`, then `mise run ship`
     dotfiles. The dotfiles branch also carries the prior session's 11 unshipped commits
     (`docs/session-2026-09-23d-handoff`, which Ray ruled must ship before any #1351 dispatch).
   - PRO: one dotfiles PR, and the gate holds.
   - CON: a large diff. The alternative is to ship `docs/session-2026-09-23d-handoff` first and rebase this
     branch onto main.
2. **KB#794 "default at the CLI seam".** `review-receipt` requires `--lanes` by design, because a receipt must
   name what ran.
   - Recommended: accept the skill-level default and close #794 on that basis.
   - The alternative is a code default lane, which would let a receipt claim a lane nobody named.
3. **`plugin-health` rc=1 on `ponytail@ponytail`.** Your local `settings.local.json` disables a plugin the project
   enables. This predates this session.
   - Recommended: either drop ponytail from project `settings.json` in a reviewed diff, or re-enable it locally.
4. **`kb-tool-review` artifact mode** is a new documented mode on `kb-codex-astra-reviewer`. The ticket named that
   agent, but the agent was diff-only.
   - Recommended: keep it, and run one real `kb-tool-review` to its Review phase (#1319 / KB#793 live arm).
5. **claudex-loop.** It is disabled per the ruling. `codex` has no native disable, so I did it by config edit.
   Should it be fully removed like fable-orchestrator (`codex plugin remove claudex-loop@claudex-loop`)? The
   doctor already tolerates the disabled state.

## Owed actions

- **Operator, LAST:** `! mise run plan-attest`. `task_plan.md` changed this session (the ruling recorded in §
  Current Phase), so the attestation is owed.
- **Next session (new agents load only at session start), the #1319 live arms:**
  - one `Agent` spawn each of `premise-verifier` and `claude-advisor`, in each repo;
  - one real `mise run sdlc-team` review dispatch settling `completed`, **blocked by dotfiles#1362** (argv[0]
    resolves to `mise`);
  - one end-to-end `kb-tool-review` run reaching its Review phase;
  - one `kb-codex-implementer` trivial dispatch (KB#795).
- **Close tickets at land time:** #1311-#1317 and KB#793-#797 once merged. #1318 is done in this session (record
  the doctor before/after arms on it). #1319 stays open until the live arms run.
- **Harness worktrees:** 7 git worktrees of dotfiles/KB on older branches still enable the plugin in their
  `settings.json`. Sessions there will warn about a missing plugin until those branches rebase on main.
- **Backups kept:**
  - dotfiles `.agent/state/fable-orchestrator-1.21.0-cache-backup-2026-09-24.tgz`;
  - `~/.codex/config.toml.pre-fable-removal-2026-09-24` (mode 600; delete when satisfied).
- The temporary review-base branch `tmp/review-base-fable` was deleted after the codex review.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — spec #1310 and tickets #1311-#1319; live references; the change itself
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — tickets #793-#797; live references; the change itself
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — read only from the installed 1.21.0 cache (upstream 404)
