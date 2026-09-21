# Feature review: claudex-loop 2.1.0 + fable-orchestrator 1.21.0 vs repo-owned `sdlc-team` (Fable lane)

Status: COMPLETE. Reviewer: Claude Fable 5.1, read-only lane, independent of the codex astra lane (its report was not opened).
Date: 2026-09-21. Branch `fix/claude-doctor-1202-cached-verdict`, HEAD `54798c57`. Nothing edited except this file.

Graphify: `mise run graphify-health` -> rc=3, `stale ... built at ff2fbaf7, HEAD is 54798c57 (32 commit(s) behind)`.
Per `graphify-first.md` the graph is unavailable; everything below is from source reads.

Abbreviations: **A** = `~/.codex/plugins/cache/claudex-loop/claudex-loop/2.1.0`, **B** =
`~/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0`. `B/SKILL` = `B/skills/orchestration/SKILL.md`.
`B/impl` = `B/agents/codex-implementer.md`. `run-lane`/`premise-gate` = `B/scripts/*.sh` (line numbers are the scripts' own).
`ours` paths are repo-relative.

## Reading log (what "end to end" actually covered)

- **A, read in full**: `skills/claudex-loop/SKILL.md` (90), `references/build.md` (37), `references/runtime.md` (51),
  `skills/claudex-route/SKILL.md` (62), `codex-build` (17), `codex-review` (16), `scripts/runner.py` (420), `README.md`,
  `VALIDATION.md`, `ACKNOWLEDGMENTS.md`, `scripts/validate.py`, both `plugin.json`, ADR/CONTEXT formats, CI workflow,
  `legacy/grill-me-codex/SKILL.md`. `tests/test_runner.py`: the 23 test names only. `legacy/grill-with-docs-codex/*`: NOT read (superseded) — UNVERIFIED.
- **B, read in full**: `skills/orchestration/SKILL.md` (178), `agents/codex-implementer.md` (204), `codex-reviewer.md` (116),
  `premise-verifier.md` (75), `fable-advisor.md` (29), `hooks/hooks.json`, `scripts/run-lane.sh` (224),
  `scripts/premise-gate.sh` (223), `commands/doctor.md`. `CHANGELOG.md`: all 279 lines, each truncated at 330 chars.
  NOT read: `agents/grok-*.md`, `scripts/doctor.sh`, `commands/setup.md`, `scripts/test-*.sh`, `README.md` — grok is not
  installed here (`.claude/CLAUDE.md` "There is no `grok` here"); rows that lean on them are marked UNVERIFIED.
- **C, read in full**: `sdlc_team.py` (1080), `codex_lane.py` (637), `codex-sdlc-team/SKILL.md`, `codex-sdlc-team.md` rule,
  `ai-cli-invocation.md`, `docs/specs/codex-sdlc-subagent-team.md`, `codex-sol-implementer.md`, `codex-sol-advisor.md`,
  `cold-reviewer.md`, `token-routing.md`; `gated-implementation.js` by grep outline. `codex-sol-{adversarial-critic,
  operator,staleness-auditor,claude-code-expert}.md`: NOT read (same skeleton as the two read) — UNVERIFIED.
- **D, read**: both history reports in full; `premises-1202` r1/r2/r3, `advisor-1202`, `impl-1202`, `impl-1202-respec1` in full;
  `cold-review-1202` first 120 lines, `-r2` first 60, `silent-failure-1202` first 45.

## Four measured facts that change the rulings

These are mine, run this session, both arms stated.

1. **The plugin's premise hook is DARK for every lane this repo actually uses.** `premise-gate.sh:131-135` matches only the
   basenames `codex-implementer`/`grok-implementer`. Probe (a PREMISES-less prompt piped to the real script):
   `codex-sol-implementer` -> rc=0, `codex-astra-implementer` -> rc=0, control `fable-orchestrator:codex-implementer` -> **rc=2**.
   So removing the plugin removes zero mechanical premise enforcement from today's flow — there was none. The only
   live check is the LLM-judged sentence at `.claude/agents/codex-sol-implementer.md:118-120` (block presence; no attestation check).
2. **Today's #1202 run used ZERO plugin agents.** Session roster (`subagents/*.meta.json`, `customAgentType`):
   `impl-1202`/`impl-1202-r1` = `codex-sol-implementer`, `advisor-1202` = `codex-sol-advisor`, both cold reviews = `cold-reviewer`
   (opus); `premises-1202` and `silent-failure-1202` = `null` (generic opus teammates with the two-pass method re-typed in the
   brief — the plugin's `premise-verifier` definition was apparently not loaded; UNVERIFIED whether a plugin agent would record
   non-null). What the plugin contributed today was **doctrine text only** (`B/SKILL`), not code, agents, or hooks.
3. **`sdlc_team` is missing three things its own sibling lanes call load-bearing.** `grep -c PLANNING_DISABLED sdlc_team.py` -> 0
   (control `codex_lane.py` -> 2); no codex `--model`/`-m` in its argv (`sdlc_team.py:769-781`; the one `-m` hit at `:808` is
   `python -m`; control `codex_lane.py:392` has `--model`); and `implement` selects `workspace-write` (`sdlc_team.py:747`) — the
   sandbox `codex-sol-implementer.md:62-85` measured as failing `mise run lint`, pytest and `mise uninstall` on permissions.
4. **Zero-hit features (control: `model_reasoning_effort` -> 45 files, `output-schema` -> 10, same command, `docs/research` excluded):**
   `SECURITY TIER` 0, `claim-only`/`captured-fail` 0 (one unrelated test hit case-insensitively), `evidence grade` 0,
   `exec resume` 0, `UNCOVERED` 0, `1500 lines` 0, `refutation pass` 0 outside receipts, `skip-git-repo-check` 0 outside one doc,
   `fast_mode|service_tier` 0 outside vendored schemas. `PREMISES-VERIFIED` -> 2 files (`gated-implementation.js:87` passes it
   through if supplied; nothing requires or checks it).

## Feature matrix

Ruling key: **KEEP-AS-IS** = ours already covers it, keep ours · **MIGRATE** = we lack it, take it · **ENHANCE** = we have a
partial/weaker form, extend ours with the predecessor's idea · **DROP** = do not carry.

### 1. Spec contract

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 1 | Seven-part spec (objective, files, interfaces, constraints+invariants, verification, commit, premises) | `B/SKILL:113-121` | Fixed shape every delegation carries; "outcome and invariants over mechanism" | PARTIAL — `spec-scribe` agent drafts it, `gated-implementation.js:4,6`; `SdlcTeamRequest` has only `spec_file`+`task`+`allowlist` (`sdlc_team.py:64-78`), no parts | **ENHANCE** | D: all three #1202 specs were seven-part and the premise rounds could only work because parts were addressable (`premises-1202-r2` "§2 mirror bullet / §3 / §4"). Make the parts a *validated* input: refuse a spec file lacking the 7 headings | Low. A heading check in python; risk = false-block on heading decoration (B burned six rounds on this, `premise-gate.sh:40-79`) — so check headings in a FILE we own the template for, never free prompt text |
| 2 | Outcome+failure-scenario objective, mechanism only with cited ruling | `B/SKILL:113,115,118` | Stops "faithful implementation of the architect's bug" | NO (doctrine only in plugin; control: `licensed dissent` -> 4 files) | **MIGRATE** (as skill prose) | B CHANGELOG 1.15.0 root cause: "dominant failure loop was architect-caused". Pure prose, no code | Trivial; belongs in `codex-sdlc-team/SKILL.md` |
| 3 | `SPEC FILE:` pointer delivery, verbatim `cat`, never re-typed | `B/SKILL:123`, `B/impl:52` | Long specs travel as a file; wrapper copies bytes | YES, stronger — `spec_file` is the ONLY delivery (`sdlc_team.py:67,272`), absolute+exists enforced `:650-652,710-722` | **KEEP-AS-IS** | B needed 1.19.0 because a wrapper spent "5–6 minutes and ~25 tool calls" re-typing a 22 KB spec; ours has no LLM in the transport path | — |
| 4 | Referenced-artifact stat at preflight (exists, readable, non-empty; never read) | `B/impl:38`, `B/SKILL:118`, `run-lane:61` | Missing input = dissent-shaped stop, not an outage | PARTIAL — spec file only (`sdlc_team.py:711`, `is_file()`, no non-empty test); no list of referenced artifacts | **ENHANCE** | Add `artifacts: tuple[str,...]` to the request; stat each; add the `-s` (non-empty) test to the spec. D: none here. Cheap insurance | Low |
| 5 | `TIMEOUT:` honest estimate, 1800 impl / 600 review default | `B/SKILL:129`, `run-lane:58-60` | Bounds every lane | PARTIAL and WEAKER — `timeout_s: float\|None = None` and `None` = **no timeout** (`sdlc_team.py:70`, SKILL `:51`) | **ENHANCE** | An unbounded default contradicts `long-running-command-hangs.md` ("MUST be run with a hard time bound"). Default by mode (3600 impl per `gated-implementation.js:85`, 900 review); make `null` invalid. D: `codex-sol-implementer.md:44-46` "50 minutes has been observed" -> 1800 is too small for xhigh here | Low; risk = killing a legitimate slow run, so default generously |
| 6 | File allowlist as exclusive ownership | ours only | — | YES `sdlc_team.py:71,256-258,281-282` | **KEEP-AS-IS** | Stronger than B's prose "one writer per module" (`B/SKILL:135`) | But it is prompt-only: nothing diffs `git status` against it at settlement — see row 22 |

### 2. PREMISES, attestation, verifier

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 7 | PREMISES block, typed rows L/I/P/E/A, "no citation, no row", read-fresh provenance | `B/SKILL:121`, `B/agents/premise-verifier.md:18-42` | Turns premise-checking from intention into artifact | PARTIAL — used by convention (all #1202 specs; `spec-scribe` description), enforced nowhere mechanically (fact 1) | **MIGRATE** | **Strongest D evidence in the whole review.** r1: 1 row REFUTED (L11, a "generated mirror" that no generator writes) + 8 MISSING, 3 blocking (`premises-1202:33-75`). r3: the provenance rule caught a respec item that "rests on a harness artifact" (`-r3:170-189`) and a wrong line citation about to be baked into a production comment (L5) | Low as doctrine. Row grammar stays human-format; do NOT port the regex |
| 8 | premise-verifier agent: Pass 1 verify rows, Pass 2 hunt unlisted premises; verdict vocabulary CONFIRMED / (provenance corrected) / REFUTED / UNVERIFIABLE / ASSUMED(checkable); `ready to dispatch` rule | `B/agents/premise-verifier.md:28-73` | Cold, read-only, opus | NO repo-owned definition (control: `cold-reviewer.md` exists). Today it ran as an ad-hoc opus teammate with the method re-typed (fact 2) | **MIGRATE** — highest priority | Pass 2 is where the value was: M1–M8 in r1, M1–M5 in r2, M1–M5 in r3 were ALL unlisted premises. The advisor lane on the same spec missed them (`advisor-1202` Q3 "string equality is sufficient ... no filesystem access is needed" — contradicted by r1 M2 `$.fs.stat`/`realPath`). Removing the plugin deletes the only written definition | Low: one `.claude/agents/premise-verifier.md` (Read/Grep/Glob, opus). Keep it CLAUDE-side: it must be a different family from the codex implementer, same logic as cold review |
| 9 | Respec re-entry: "a corrected spec is a new spec" — changed rows re-verify | `B/SKILL:121`, CHANGELOG 1.20.0 | Closes the door both B field failures came through | NO | **MIGRATE** | D reproduces B's field finding exactly: r2 and r3 each found NEW blocking items in rows added by the respec | Prose + row 10's hash makes it mechanical |
| 10 | `PREMISES-VERIFIED: <abs path>` attestation, stat-only | `B/SKILL:121`, `premise-gate:199-210`, `B/impl:42` | Presence of a verifier report file gates dispatch | NO check anywhere (fact 4); passthrough only `gated-implementation.js:87` | **ENHANCE, do not copy** | B admits the hole: "a stale attestation passes both layers mechanically" (`B/SKILL:121`). **A already has the fix**: bind approval to path + SHA256 of the reviewed document and refuse on mismatch (`A/runner.py:247-254,369-370`). Ours: `SdlcTeamRequest.premises_report` + verifier writes `spec_sha256`; `dispatch()` recomputes and returns `INVALID_REQUEST` on mismatch. That makes row 9 automatic | Medium: verifier must emit a small typed receipt. Risk: fabrication still possible — B's own accepted limit ("converts silent skipping into active fabrication") |
| 11 | Trigger rule (emits telemetry/errors/events, or security/concurrency/migration) via E-row / `SECURITY TIER` regex over prompt text | `premise-gate:156-197`, `B/SKILL:121` | Decides WHEN verification is mandatory | NO | **DROP the mechanism, MIGRATE the intent** as a typed field `tier: mechanical\|behavior\|security` | The regex cost B six review rounds and still documents residuals (`premise-gate:47-79`); it exists only because a hook can see nothing but prompt text. We own a typed request — a required enum is a control arm for free (no value = invalid) | Low |
| 12 | PreToolUse hook on `Agent` enforcing 7/10 | `B/hooks/hooks.json`, `premise-gate.sh` | Refuses implementer dispatch | NO, and it never covered us (fact 1) | **DROP** | Dark for our lanes; FAIL-OPEN by design (`premise-gate:10-16`), which `mise-tasks-only.md` says is the wrong home for a hard ban. With one python entry point the gate is `dispatch()` itself — fail-closed, typed, testable, and it also covers follow-up rounds (B's hook cannot see SendMessage rounds, `premise-gate:24-26`) | Removes a bash hook; zero behaviour lost |

### 3. Advisor

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 13 | fable-advisor: verdict-not-survey, <300 words, declines without decisive evidence, three trigger moments | `B/agents/fable-advisor.md`, `B/SKILL:151-159` | Commitment-boundary second opinion | YES — `codex-{sol,astra}-advisor.md` (`:20-32` same triggers; `:149-157` same output shape), routing ratified `token-routing.md:7-13` | **KEEP-AS-IS**, fix one dangling ref | D: KB ruling "Build ours, disable theirs" (`agentsview-history:254-265`). BUT `codex-sol-advisor.md:171-181` names `fable-orchestrator:codex-reviewer` and `fable-orchestrator:fable-advisor` as the reviewer of record / sanctioned fallback — both vanish with the plugin. 4 hits each in sol+astra `.md` and 2 each in `.codex/agents/*.toml` | Low; mirror regenerates astra. D caution: today's advisor was the weakest lens (haiku wrapper, generic table, missed what Pass 2 found) — do not let it substitute for row 8 |

### 4. Review

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 14 | Review tiers: mechanical / declared spike -> verify only; behavior-bearing -> one cold cross-family pass; security/auth/concurrency/migration -> + silent-failure completeness read | `B/SKILL:161-170` | Scales review to blast radius | PARTIAL — cold pass in `gated-implementation.js:115-119`; no tier selector; silent-failure read has no definition (ran ad hoc today) | **MIGRATE** (tiers as the row-11 enum; silent-failure reader as a second repo agent) | D: today ran exactly this stack. `silent-failure-1202` enumerated fail-open branches no other lens listed (`readVerdict` empty catch, A1/A2) | Low–medium: one agent file + enum |
| 15 | Cross-family rule: reviewer never from the implementer's family; degraded same-family read must be ANNOUNCED | `B/SKILL:167`; same idea `A/runner.py:50-57,279-282` (hard refusal) | Prevents shared blind spots | YES in prose (`.claude/CLAUDE.md` "No `codex-*` lane is the cold-review lens for a codex diff") ; NOT enforced in code | **ENHANCE** | A enforces it as a `RunError`; ours is a sentence. In `sdlc_team`, `mode=review` of a codex-authored diff is same-family by construction — the settlement should carry `reviewer_family`/`author_family` and a `degraded` flag rather than rely on the caller remembering. D: claudex's only lesson judged worth keeping was exactly this ("whoever built it never grades it", `agentsview-history:171-173`) | Low |
| 16 | Review by REF, never a diff file; resolve+report concrete SHAs; read blobs via `git show <sha>:<path>` | `B/SKILL:167`, `B/agents/codex-reviewer.md:32-44,95` | Immutable review identity | YES `cold-reviewer.md:16-18`; D both cold reviews report full SHAs | **KEEP-AS-IS** | — | — |
| 17 | Cold discipline: strip intent framing | `B/agents/codex-reviewer.md:32` | No happy-path priming | YES `cold-reviewer.md:16-18`, `gated-implementation.js:116` | **KEEP-AS-IS** | ⚠️ but `sdlc_team` review mode hands the dispatcher the SPEC (`sdlc_team.py:272`) — that is a spec-conformance review, not a cold one. Say so in the skill; do not call it the cold gate | doc only |
| 18 | Diff-size guard (~1,500 lines -> per-file batches, `UNCOVERED`, `STATUS: partial`) | `B/agents/codex-reviewer.md:42,105` | No silent quality collapse | NO (fact 4) | **MIGRATE** (into cold-reviewer + review-mode prompt) | D: today's diff was 921+/97- (`cold-review-1202:13-21`) — under the line, so untested here; A independently requires `coverage`+`limitations` (row 19) | Low |
| 19 | Structured review result, schema-enforced + validated: verdict APPROVED/REVISE/BLOCKED, findings{id,severity,path,evidence,fix}, coverage, limitations; APPROVED+material finding rejected; REVISE needs findings; BLOCKED needs limitation | `A/runner.py:20-35,112-142`, `--output-schema` `:155` | Transport failures and contradictory verdicts can't read as approval | PARTIAL — `codex_lane.py:380-394` does it for the DAG review lane (`codex_verdict.VERDICT_SCHEMA`); `sdlc_team` review output is free-form markdown (`sdlc_team.py:261-265`) | **ENHANCE** | Reuse `codex_verdict`'s schema in `sdlc_team` review mode. `coverage`+`limitations` are the two fields ours lacks and both matter (row 18). D: `cold-reviewer.md:41-43` already forces `{findings, reportPath}` on the Claude side | Medium: `--output-schema` and the dispatcher's closing "Specialists spawned:" list must coexist — put the roster in the schema |
| 20 | `codex exec review` subcommand | `run-lane:112-114` | CLI derives the diff from a ref named in the instructions | NO; D: prior KB ruling "evaluate once on a real diff before adopting" (`agentsview-history:225-227`); `docs/receipts/575.md:142` it has no `--cd` | **DROP** (for now) | Same-family for a codex diff anyway; no `--cd` is a worktree hazard | — |
| 21 | Refutation pass: findings are claims; refute cited-first in severity order; UNCITED last; refute the *clean* report on security tier | `B/SKILL:172-174` | Stops acting on false positives | NO written form (fact 4) | **MIGRATE** (skill prose) | D, decisive: cold-review r1 **F2 HIGH was FALSE** (HookBudget) — refuted from the types by `premises-1202-r3 (a)` and retracted in `cold-review-1202-r2:20-27`; **F1 HIGH was TRUE** -> respec. Acting on both would have added a wrong fix | Trivial |
| 22 | Settlement scope check: changed files == task files; foreign commits flagged | `B/impl:174-176` | Catches scope creep and foreign writers | PARTIAL — `codex-sol-implementer.md:260-262` (LLM cross-check); `sdlc_team` settlement records nothing about the tree | **ENHANCE** | Row 6's allowlist is unenforced. At settlement record `git status --porcelain` + `git diff --name-only <base>` and fail closed on any path outside `allowlist` — same shape as the existing claimed-vs-observed spawn reconciliation (`sdlc_team.py:577-643`) | Medium; very on-pattern for this module |

### 5. Loop control and stop conditions

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 23 | Respec bound: max two respec->re-implement->re-review rounds, then surface residuals to the user; "routinely hitting it = unverified premises" | `B/SKILL:34,174` | Terminates the loop | PARTIAL — `max_rework` exists for the DAG lane (15 files; `codex_lane.py:255-292` atomic increment); nothing for `sdlc_team`/gated-implementation | **MIGRATE** | D: #1202 is at respec round 1 -> cold r2 (13 findings, 0 HIGH) -> premises r3. Round 3 is where B says stop-and-surface | Low: `round: int` in the request, `dispatch()` refuses `>2` without an explicit override |
| 24 | claudex budgets `MAX_ROUNDS=5` (plan review), `MAX_FIX_ROUNDS=2`, `MAX_INSPECTION_ROUNDS=2`; "present unresolved findings ... instead of manufacturing convergence" | `A/SKILL:33-39,78` | Same idea, three counters | see 23 | **DROP** the 5-round plan-review counter; row 23's two is the measured number | A's 5 is a default, not a measurement ("illustrative run, not a controlled benchmark", `A/README:153`) | — |
| 25 | Stop states are never approval: BLOCKED / failed process / malformed / rc=0-but-REVISE; "exit 0 means a valid completed turn, not APPROVED"; never reuse last good result after a failed newer round | `A/runtime.md:22`, `A/SKILL:76`, `A/runner.py:206-211,364-366` | Separates transport success from verdict | YES, and stronger — `SdlcSettledStatus` + fail-closed reconciliation even at rc=0 (`sdlc_team.py:989-990`); `settlement_file.unlink` before launch `:787`; `codex_lane._STALE_ARTIFACTS` `:146-151` | **KEEP-AS-IS** | Repo history #1142 is the same lesson learned the hard way (`codex-sdlc-subagent-team.md:170-198`) | — |
| 26 | Same-session reviewer across plan rounds (`exec resume <uuid>`, returned-UUID check, resume refuses provider/model/effort mismatch) | `A/runner.py:149-152,238-239,257-269` | Reviewer remembers its prior findings | NO (`exec resume` 0 hits) | **DROP** | Conflicts with fresh-lens discipline that D shows working: cold r2 was a FRESH agent and still self-corrected r1 via `memory: local` (`cold-review-1202-r2:17,23-27`). B also measured wrapper degradation from ~144k tokens (`B/SKILL:149`). One useful crumb: `resume` rejects `-s`, needs `-c sandbox_mode=` (`A/runner.py:150-152`) — record in `ai-cli-invocation.md` if resume is ever used | — |
| 27 | No silent model/provider fallback; record requested vs observed model separately | `A/SKILL:21`, `A/runner.py:215,231,313-316` | Honest identity | PARTIAL — `codex_agent_parity` pins name<->model for the sol/astra wrappers (`token-routing.md:17-21`); `sdlc_team` records neither | **ENHANCE** | Fact 3: no `--model` in `sdlc_team` argv, no `model =` in any `codex-sdlc-*.toml` -> the team runs whatever `~/.codex/config.toml` says, the exact drift `token-routing.md:27-30` records ("silently diverged ... when global changed"). Add `model` to the request (required, no default — "neither is a default") and record the banner's resolved model in the settlement | Low |

### 6. Verification evidence and commits

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 28 | Evidence grading `captured` / `captured-fail` / `claim-only`, graded from the machine log, wrapper NEVER re-runs; narration-of-intent = claim-only BY RULE | `B/impl:174`, `B/SKILL:178` | A report is a claim; a log is evidence | NO (fact 4). Ours: `codex-sol-implementer.md:232-248` relays codex's self-written `EXIT=` lines — still the model's text; `sdlc_team` SKILL `:123-124` just says "verify independently" | **MIGRATE**, adapted | This is the second-biggest loss. But under `read-only`/`workspace-write` the gates can't run (fact 3), so at `sdlc_team` level the honest grade today is always `claim-only`. Adapted form: settlement carries `verification_grade` computed from `codex.log`, and the skill states that `claim-only` => `gate-runner` runs the matrix. Needs `--json` (row 38) so the log has machine-labeled command exits instead of prose | Medium. Risk: grading prose logs by regex is the `require_tokens` trap — only do it on `--json` events |
| 29 | Proof command carried as data; host re-runs proof itself; "do not trust a builder's success report" | `A/runner.py:305-306,335`, `A/build.md:22,26` | Builder report is advisory | YES — `gate-runner` agent + `verify-before-advancing.md`; `gated-implementation.js` has a gates phase | **KEEP-AS-IS** | A's VALIDATION admits both delegated builders had their proof blocked by sandbox (`A/VALIDATION.md:34`) — same finding as fact 3, same answer: host runs gates | — |
| 30 | Commit ownership `COMMIT: lane\|caller`; lane default; wrapper backstop commit scoped to task files; never-empty `COMMIT:` field with explicit non-hash states | `B/SKILL:120`, `B/impl:176,186` | Every diff has a ref for cold review | DIVERGED — `sdlc_team.py:283` hard-codes `COMMIT: caller`; `codex-sol-implementer.md:250-252` commits only when every named gate is green | **KEEP-AS-IS** (caller) + **MIGRATE** the never-empty field | B's backstop commits on a `claim-only` grade — against `verify-before-advancing.md`. Keep ours. But take the enumerated `COMMIT:` states into the settlement (`gated-implementation.js:94-111` already parses `COMMIT:` and has an `implementer-no-commit` status) | Low |
| 31 | No-commit contract verified: HEAD unchanged after a build, else fail | `A/runner.py:373-375` | Catches a builder that commits anyway | NO | **MIGRATE** | One `git rev-parse HEAD` before/after in `_supervise`; fail closed under `COMMIT: caller`. Cheapest real check in this table | Trivial |
| 32 | Stability anchors: BASELINE sha + BRANCH captured pre-launch; re-verified (branch same, baseline is ancestor, reflog for foreign reset) before grading and before settling; never reset/revert/checkout over foreign commits | `B/impl:107-118,176`, CHANGELOG 1.14.0 | Detects a second writer / moved checkout | NO in `sdlc_team` (`merge-base --is-ancestor` only in 2 docs) | **MIGRATE** | Repo memory records this exact failure twice ("a file revert 4x", "Verification during a collision window is VOID"); `codex-sdlc-team.md` "The lane owns the checkout while it runs" is prose. Record `base_sha`+`branch` in `SdlcTeamDispatch`, re-check at settlement | Low–medium |
| 33 | Inspected-state fingerprint: sha256 over base + per-file hashes (tracked, staged, deleted, untracked) + diff; refuse result if it changed during the review | `A/runner.py:86-109,371-372` | A review applies to one snapshot only | NO | **MIGRATE** (review mode) | Same failure class as 32 from the reviewer's side; A's `snapshot()` is ~25 lines of stdlib and the only piece of A worth lifting near-verbatim (MIT) | Low |
| 34 | Clean-checkout gate before a delegated build; artifacts must live outside the checkout | `A/runner.py:295-296,307-309` | Attributable diff | PARTIAL — artifacts under gitignored `.agent/` (fine); no clean-tree check | **ENHANCE** (warn, don't refuse) | This repo routinely has untracked agent reports (see today's `git status`); a hard refuse would block real work. Record pre-existing dirt in the dispatch like `B/impl:120` | Low |

### 7. Process supervision

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 35 | Detached launch + out-of-agent watchdog + process-GROUP kill + `EXIT:` marker + reap evidence in the report | `run-lane:38-45,91-94,171-189,206-219` | Wall clock holds even if the wrapper dies | YES, better — python supervisor `start_new_session=True` twice (`sdlc_team.py:805-818,961-968`), `killpg` TERM->KILL `:847-858`, typed settlement, `read_status` derives `abandoned` `:861-882`; `mise run reap` | **KEEP-AS-IS** | B needs an LLM (sonnet) looping 90 s `wait` slices (`B/impl:145-151`) because a hook/agent can't outlive its turn; ours returns immediately and needs no babysitter. Also `zero-bash-logic.md` forbids importing `run-lane.sh` | One gap: `read_status` uses `os.kill(pid,0)`, which memory `project_session_2026-09-16d` records as "true on a zombie" — UNVERIFIED whether it bites here |
| 36 | Early-death single relaunch (dies <1 min, no diff) dropping fast/effort knobs | `B/impl:161` | Rides out transient launch failures | PARTIAL — `codex-sol-implementer.md:216-221` (one relaunch); none in `sdlc_team` | **DROP** for `sdlc_team` | A says the opposite and is right for a typed API: "Stop and report a failed handoff rather than automatically retrying" (`A/claudex-route:60`). Repo history: a retry-and-continue clause hid an all-spawns-failed run (`codex-sdlc-subagent-team.md:193-198`). Caller retries, visibly | — |
| 37 | "A completion without a report is not a success" + orphan hunt `pgrep -f 'codex exec'` + group kill | `B/SKILL:145-147` | Treat the tree as unsettled | PRINCIPLE yes (`read_status`; `codex-sol-implementer.md:290-292`); the HUNT contradicts us | **KEEP-AS-IS** (ours) | See contradictions §C3 — reap by unique output path, never the bare name | — |
| 38 | `--json` event log (machine-labeled exec + exit codes) | `A/runner.py:153`, `run-lane:113` | Parseable evidence | NO in `sdlc_team` argv `:769-781` (plain log; parent thread id scraped from the banner `:904`) | **MIGRATE** | Enables row 28 honestly, gives `thread.started`/`turn.completed`/`turn.failed` (`A/runner.py:206-211`) — a far better completion + parent-id source than banner scraping, and `usage` for cost. Memory `2026-09-14f` notes log-scraping is "PRESCRIBED by the repo" — this is the exit | Medium: `lane_result.parse_parent_thread_id` changes source; keep both until armed |
| 39 | Per-run artifact dir with `prompt.txt`, `command.json`, `stdout`, `stderr`, `result.json` written as `running` first | `A/runner.py:311-319,360`, `A/runtime.md:20` | Diagnosable failures; crash leaves a `running` record | YES — `.agent/sdlc-runs/<id>/{prompt.md,output.md,codex.log,settlement.json}`, argv in the dispatch JSON; atomic writes `:666-671` | **KEEP-AS-IS** | Only delta: A separates stderr; ours merges (`stderr=STDOUT :966`). Fine unless row 38 lands — then keep stderr apart so JSONL stays parseable | trivial w/ 38 |
| 40 | CLI version probe recorded per run | `A/runner.py:353-357` | Flags drift | PARTIAL — pinned in `shared.toml:44`, doctor schema-currency; not recorded per run | **ENHANCE** (one field) | `ai-cli-invocation.md` "flags drift between releases"; A's VALIDATION shows 0.144.5 exposing the flags but failing the model (`:23`) | Trivial |
| 41 | `PLANNING_DISABLED=1` on the spawn env | ours `codex_lane.py:121-136,469`; all 12 wrappers | Stops a lane inheriting/writing the coordinator's plan | **MISSING in `sdlc_team`** (fact 3) | **ENHANCE** (bug) | Measured cause of a real loss: "a lane has already truncated those shared files once (2026-09-09)" (`codex-sol-implementer.md:180-183`). Import `codex_lane.LANE_ENV_OVERRIDES` — do not restate it | Trivial, do first |

### 8. Knobs, fallback, parallelism

| # | feature | source | what it does | have it? | ruling | why / evidence (D) | cost / risk |
|---|---|---|---|---|---|---|---|
| 42 | Effort knob, validated enum `none\|low\|medium\|high\|xhigh\|max`, refuse invalid before launch | `run-lane:62-71`, `B/SKILL:91-99` | One knob | PARTIAL — `effort: str = "xhigh"`, validated only as an identifier (`sdlc_team.py:69,653-656`) | **ENHANCE** | Make it a `StrEnum`. ⚠️ and it does not reach the specialists: every `codex-sdlc-*.toml` pins `model_reasoning_effort = "high"` (`:4`/`:9`) and the agent file wins (`codex-sdlc-subagent-team.md:31-37`), so `"effort":"xhigh"` moves only the dispatcher. UNVERIFIED at runtime; derived from the spec's cited precedence | Low; decide whether the tomls should omit the key |
| 43 | Fast mode (`-c service_tier=fast -c features.fast_mode=true`), loud downgrade | `run-lane:89-90`, `B/SKILL:81-89` | ~1.5x speed for ~2–2.5x credits | NO | **DROP** | Tokens are the constraint here (`codex-sol-advisor.md:15-17`); suites.toml `:2259` even carries a contract about where the fast-mode line lives — delete with the plugin | removes a contract |
| 44 | Lane modes grok/codex/mix + CLAUDE.md config lines "honor the intent, not the exact string" | `B/SKILL:65-79` | Routing config | we pin `codex` + `xhigh` (`.claude/CLAUDE.md`), contract-bound `suites.toml:2210-2253`, `rule-sync.toml:29,40-41` | **DROP** | No grok. Intent-parsed prose config is the opposite of a typed request. ⚠️ removal cost is real: >=7 suites.toml contract blocks + rule-sync + the KB sibling (`history-herdr-claudex:106-120`) | Medium, cross-repo |
| 45 | Fallback chain (other CLI -> Opus), every step announced, review never relaxes | `B/SKILL:63,22` | Availability | PARTIAL — `SdlcStatus.CLI_MISSING` is loud (`sdlc_team.py:724-736`); `codex-sol-advisor.md:174-181` explicit-only fallback | **KEEP-AS-IS** + keep one sentence | Ours = "never silently substitute" (`codex-sol-implementer.md:244-248`), same as A (`A/SKILL:21`). Carry the sentence "verification and review do not relax under fallback" into the skill | — |
| 46 | Parallelism: one live writer per checkout; parallel writers get worktrees; spec names the gitignored per-machine files to copy (wrapper copies only those, `git check-ignore`, never staged) | `B/SKILL:133-137`, `B/impl:122` | Safe fan-out | PARTIAL — `goal-history.md` one-writer rule; `agent-artifact-conventions.md` `.worktreeinclude`; `sdlc_team` has `-C workdir` but only ever `repo_root` | **DROP** provisioning, **KEEP** the one-writer rule | Native `.worktreeinclude` already solves the config-copy problem B hand-rolled (`use-tool-builtins.md`). `codex-sol-operator` measured worktrees BLOCKED under the write sandboxes (`codex-sol-implementer.md:87-90`). No D evidence of parallel implement lanes here | — |
| 47 | Wrapper transcript bound (~144k degrade, ~200k ceiling; fresh wrapper per task) | `B/SKILL:149` | Avoids end-of-task discipline decay | N/A once the supervisor is python | **DROP** | D: today used a fresh implementer per round anyway (`impl-1202`, `impl-1202-r1`) | — |
| 48 | Licensed dissent + test-craft standing clauses injected by the wrapper | `B/SKILL:125`, `B/impl:80-88` | Implementer may refuse a wrong spec | YES `sdlc_team.py:275-280` (and "stop on spawn failure" `:284-285`, no-pager `:286-287` — ours adds two) | **KEEP-AS-IS** | D: #1026 "refused four dispatches and every refusal was correct" (`codex-sol-implementer.md:110-116`). Missing from ours: the dissent SETTLEMENT shape (a refusal exits 0 — `codex-sol-implementer.md:287-290` reads `$OUT` for it; `sdlc_team` would settle `completed`) -> add `dissent` detection to the settlement | Low–medium |
| 49 | "Supervisor, not editor" — transport never paraphrases, never reads referenced inputs, never implements | `B/impl:38` | Keeps the weakest model out of the content path | YES by construction (no LLM in `sdlc_team`'s path) | **KEEP-AS-IS** | D: the haiku wrapper that "decided ... I'll code the implementation myself" (`codex-sol-implementer.md:30-42`). This is the single best argument for the unification | — |

### 9. claudex-only and packaging

| # | feature | source | what it does | have it? | ruling | why | cost |
|---|---|---|---|---|---|---|---|
| 50 | Plan review BEFORE build by the other provider; approval bound to plan path+SHA | `A/SKILL:68-78`, `A/runner.py:247-254` | Harden the plan first | PARTIAL — row 8 verifies FACTS; `codex-*-adversarial-critic` attacks PROPOSALS | **DROP** the phase, keep the hash (row 10) | Premise-verifier + critic cover it with repo-specific evidence discipline; A's reviewer "cannot ... run tests" and gets only Read/Glob/Grep | — |
| 51 | Reviewer tool boundary for a Claude reviewer: `--safe-mode --strict-mcp-config --mcp-config '{"mcpServers":{}}' --tools Read,Glob,Grep --permission-mode dontAsk` | `A/runner.py:161-166` | Hard read-only Claude CLI lane | N/A (our Claude reviewers are in-process agents with `tools:`) | **DROP**; note for reference | Useful only if a Claude CLI lane is ever spawned from codex | — |
| 52 | MCP caveat: codex's shell sandbox does not restrict MCP side effects; audit write-capable servers before a read-only review | `A/runtime.md:33`, `A/VALIDATION.md:42` | Honest boundary | NOT STATED in ours (the SDLC spec notes `mcp_servers` can't narrow per agent, `codex-sdlc-subagent-team.md:230-233`) | **MIGRATE** (one sentence in the rule) | D: a codex lane does call `mcp__exa__*`/`context7` when registered (`agentsview-history:104-109`). "read-only" in `sdlc_team` review mode is a shell property, not a tool property | Trivial |
| 53 | Recon/interview phases, assumptions ledger, ADR + CONTEXT formats, claudex-route model picker, Windows `cli_prefix`, legacy grill skills | `A/SKILL:43-66`, `A/claudex-route`, `A/runner.py:60-76`, `A/legacy/` | Requirements front-end | YES elsewhere — `mattpocock-skills:grilling`/`domain-modeling`, `docs/adr/`, `CONTEXT.md`, `.claude/CLAUDE.md` lane table | **DROP** | Duplicates enabled skills; A's legacy grill IS Matt Pocock's (`A/README:155`) | — |
| 54 | Lane doctor (presence, auth, model access via tiny live calls; version floor) | `B/commands/doctor.md`, `B/scripts/doctor.sh` (UNVERIFIED, not read) | Setup-time loudness | PARTIAL — `doctor.toml [codex]` schema currency; `CLI_MISSING` | **ENHANCE** later | A live "model X answers on CLI Y" probe is the only thing that catches A's 0.144.5 case. Low priority | paid calls |
| 55 | Setup wizard writing CLAUDE.md lines | `B/commands/setup.md` (UNVERIFIED) | Install UX | N/A | **DROP** | Already a documented trap (`.claude/CLAUDE.md`: "decline"; writes to the stub-gated root file) | — |

## codex CLI flags, verbatim, with file:line

| user | argv | where |
|---|---|---|
| A review, fresh | `exec -s read-only -c approval_policy="never" --json -o <run>/reply.txt --skip-git-repo-check --output-schema <run>/schema.json [-m <model>] [-c model_reasoning_effort="<e>"] -` | `A/runner.py:149-160` |
| A review, resumed | `exec resume <uuid> -c sandbox_mode="read-only" -c approval_policy="never" --json -o ... --skip-git-repo-check --output-schema ... -` | same; `resume` takes no `-s` |
| A build | `exec -s workspace-write -c approval_policy="never" --json -o ... [-m] [-c model_reasoning_effort=] -` (resumed: `-c sandbox_mode="workspace-write"`) | `A/runner.py:151-153` |
| A legacy | `codex exec -s read-only --json -o /tmp/codex-verdict.txt "$(cat REVIEW_PROMPT)" < /dev/null 2>/dev/null` | `A/legacy/grill-me-codex/SKILL.md` (superseded) |
| B implement | `codex exec --model "${MODEL:-gpt-5.6-sol}" -c model_reasoning_effort="$EFFORT" [-c service_tier=fast -c features.fast_mode=true] --sandbox workspace-write --skip-git-repo-check --cd "$(pwd)" --output-last-message "$FINAL" - < "$SPEC" > "$LOG" 2>&1` | `run-lane:91-93` |
| B review | `codex exec review --model ... -c model_reasoning_effort="$EFFORT" [fast] -c 'sandbox_mode="read-only"' --json --output-last-message "$FINAL" - < "$SPEC"` | `run-lane:112-114` |
| ours, team | `<abs codex> exec -s read-only\|workspace-write -c model_reasoning_effort="<effort>" -C <workdir> -o <output> -` — deliberately NO `--ephemeral` | `sdlc_team.py:769-781`, why `:748-768` |
| ours, DAG review lane | `codex exec --ephemeral --sandbox read-only --output-schema <schema> -o <verdict.json> [--model M] -` + env `PLANNING_DISABLED=1` | `codex_lane.py:380-394,469` |
| ours, implementer wrapper | `cat "$PROMPT" \| PLANNING_DISABLED=1 codex exec --ephemeral --sandbox danger-full-access --model gpt-5.6-sol -c model_reasoning_effort="xhigh" -o "$OUT" - > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"` | `codex-sol-implementer.md:167-171` |
| ours, advisor wrapper | same with `--sandbox read-only` | `codex-sol-advisor.md:101-105` |

Flags a predecessor uses that ours never does: `--json`, `--skip-git-repo-check`, `-c approval_policy="never"`,
`exec resume`, `exec review`, `-c service_tier`/`features.fast_mode`. Flags ours uses that neither predecessor does:
`--ephemeral`, `danger-full-access`, `-C` (B spells it `--cd`). Every form here should be re-probed against
`mise exec -- codex exec --help` at 0.154.0 before adoption (`ai-cli-invocation.md` re-probe rule) — I did NOT run the CLI; UNVERIFIED.

## (1) The five whose loss would hurt most

1. **premise-verifier, esp. Pass 2 + the provenance rule (rows 7–9).** Today: 1 refuted row + 18 unlisted premises across three
   rounds, including the one that showed a respec item was a test-harness artifact. It exists only as plugin text; nothing in
   the repo defines it; the advisor lane demonstrably does not replace it.
2. **Cold cross-family review by ref + the refutation pass (rows 15, 16, 21).** One HIGH confirmed and one HIGH refuted in the
   same report, today. The cold half we own (`cold-reviewer`); the refutation half is unwritten here.
3. **Evidence grading / "a report is a claim" (row 28) with the never-empty COMMIT/PROCESS fields (row 30).** Ours fail-closes on
   *who spawned* but says nothing on *whether verification ran*.
4. **Respec bound of two + "a corrected spec is a new spec" (rows 9, 23).** #1202 is at the bound right now, and both respec
   rounds introduced new blocking premises — B's field result, reproduced.
5. **Licensed dissent as a first-class SETTLED outcome (row 48).** The clause is already in our prompt; the settlement shape
   is not — a refusal exits 0 and `sdlc_team` would call it `completed`.

Honourable mention, from A not B: **hash-binding the verified document (row 10)** — it closes the freshness hole B documents
and leaves open.

## (2) The five that are dead weight

1. grok lanes, `mix` mode, grok effort, grok permission/scheduler containment (rows 44; `run-lane:117-168`) — no grok here.
2. The regex premise gate + E-row/`SECURITY TIER` grammar + the hook (rows 11–12) — dark for our lanes, fail-open, replaced by a typed enum.
3. Fast mode and the intent-parsed CLAUDE.md config lines + setup wizard (rows 43, 44, 55).
4. The sonnet-wrapper-as-supervisor machinery: 90 s wait slices, guard-shaped heredoc assembly, `$RL` resolution, transcript
   bounds, worktree config provisioning (rows 35, 46, 47; `B/impl:48-116`) — all artefacts of having an LLM in the transport path.
5. claudex's front half: recon/interview, ADR/CONTEXT formats, claudex-route, 5-round plan review, session resume, Windows shims (rows 24, 26, 50, 53).

## (3) Where a predecessor contradicts a repo rule

| # | predecessor says | repo rule says |
|---|---|---|
| C1 | `premise-gate.sh:10-16` "FAIL-OPEN BY DESIGN ... a broken gate must never brick all dispatches" | `mise-tasks-only.md` § Enforcement layers: "Hard bans that must never fail open belong in settings.json permission deny rules, not the hook" (#343, 125 commands bypassed by never reaching the guard) |
| C2 | `B/impl:167` "`--sandbox workspace-write` ... Never `danger-full-access`"; `A/build.md:18` same | `codex-sol-implementer.md:60-95` measured both arms: workspace-write -> file NOT created, danger-full-access -> created. ⚠️ **and the repo contradicts itself**: `ai-cli-invocation.md:18-20` still prescribes `-s workspace-write` as the implementation form, and `sdlc_team.py:747` uses it |
| C3 | `B/SKILL:147` orphan hunt `pgrep -f 'codex exec'` then group-kill | `codex-sol-implementer.md:222-229`: reap "by its unique output path — never by the bare name `codex`, which the desktop Codex app's processes share", via `mise run reap` (`mise-tasks-only.md`); memory `feedback_scope_process_hunts_to_this_project` — KB runs codex too |
| C4 | `B/SKILL:32` "filter at the tool call (`--jq`, `grep`, `tail`)" | `long-running-command-hangs.md` rule 3 (machine-enforced: "gate command piped to head/tail"); ours even injects the ban into the lane prompt (`sdlc_team.py:286-287`) |
| C5 | `B/SKILL:120`, `B/impl:176` lane-owned commit by default, wrapper backstop commits on a `claim-only` grade | `verify-before-advancing.md` "The gate": commit only after every applicable check is green with evidence; `sdlc_team.py:283` `COMMIT: caller` |
| C6 | `run-lane.sh` (224 lines of launch/watchdog/reap bash), `premise-gate.sh` (223) | `zero-bash-logic.md`: non-trivial logic lives in `python/`; new `.sh` fails `bash_logic_budget`. (Plugin cache is out of scope for the gate — but it means neither script can be "migrated", only re-expressed; `sdlc_team.py` already did) |
| C7 | `B/SKILL:49-55` grok lanes; fallback "re-route the same spec to the other CLI lane" | `.claude/CLAUDE.md` "There is no `grok` here — codex lanes only, stop asking" |
| C8 | B setup (`CHANGELOG 1.8.0`) writes config to the scoped CLAUDE.md and gates the trigger on "When the session model is Fable" | `.claude/CLAUDE.md`: root `CLAUDE.md` is byte-locked by `claude_md_import_stub`; trigger "deliberately UN-gated ... decline" |
| C9 | `A/runner.py:307` default artifacts under `tempfile.gettempdir()`; `A/legacy` fixed `/tmp/codex-verdict.txt` + `2>/dev/null` | `agent-artifact-conventions.md` ("No ad-hoc directories", `.agent/` paths); `do-not.md` #4 spirit (stderr loud); B itself bans fixed paths |
| C10 | `B/impl:161` auto-relaunch on early death; every wrapper hand-rolls `codex exec` | `codex-sdlc-team.md` "never a hand-rolled `codex exec`" (guard-denied for the team); `ai-cli-invocation.md` "This is the only hand-kept argv block". ⚠️ our own 12 `codex-{sol,astra}-*.md` wrappers each hand-keep an argv block too — the unification should retire those, not just the plugin |
| C11 | `B/agents/codex-reviewer.md` cold lens = codex | `.claude/CLAUDE.md`: "No `codex-*` lane is the cold-review lens for a codex diff" — correct under B's own rule, but it means B's reviewer is unusable here by construction |

## Could not verify

- Whether a plugin-defined teammate records a non-null `customAgentType` (fact 2's inference about `premises-1202`).
- Row 42's claim that per-agent `model_reasoning_effort = "high"` overrides the request's `xhigh` at runtime (derived from the
  spec's cited precedence text, not measured).
- Any codex flag's validity at 0.154.0 — I ran no `codex` command.
- `doctor.sh`, `setup.md`, `grok-*.md`, `test-*.sh`, B `README.md`, A `legacy/grill-with-docs-codex`, four of the six
  `codex-sol-*.md` wrappers: not read.
- The full bodies of `cold-review-1202*` and `silent-failure-1202` past the line counts in the reading log.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject; all "ours" rows.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — predecessor B, read from the local plugin cache at 1.21.0.
- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — predecessor A, read from the local codex plugin cache at 2.1.0.
- [mattpocock/skills](https://github.com/mattpocock/skills) — named by A as the origin of its legacy grill skills; not fetched.
- [openai/codex](https://github.com/openai/codex) — CLI whose flags are tabulated; not fetched, no command run.
