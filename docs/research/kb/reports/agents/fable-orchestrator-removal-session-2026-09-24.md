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

## /verify

_(pending)_

## Gate rcs

_(pending)_

## Open questions for Ray

_(pending)_

## Owed operator actions

_(pending)_

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — spec #1310 and tickets #1311-#1319; live references; the change itself
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — tickets #793-#797; live references; the change itself
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — read only from the installed 1.21.0 cache (upstream 404)
