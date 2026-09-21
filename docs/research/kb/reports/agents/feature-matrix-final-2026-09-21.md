# Final feature matrix — what `/codex-sdlc-team` takes from claudex-loop 2.1.0 and fable-orchestrator 1.21.0

Reconciled by the architect (Claude Fable 5.1) on 2026-09-21 from two independent reviews, for Ray's ruling
(`task_plan.md` 9.6b; artifact comments 20:24 / 20:27). Inputs, verbatim and tracked:

- `feature-review-fable-2026-09-21.md` — Claude Fable agent, 55 rows, 4 measured facts, 11 rule contradictions.
- `feature-review-astra-2026-09-21.md` — codex gpt-6-astra lane, 29 rows.

Row ids `F#` refer to the Fable report's numbering.

**STATUS: RATIFIED by Ray, 2026-09-21 (AskUserQuestion)** — sections A-D plus Addenda 1-3 as proposed (incl. U1 and A6), and all
three ⚖ calls per Addendum 2: one respec bound of 2 keyed to severity, fresh reviewer every round with no `codex exec resume`,
worktree provisioning by BOTH mechanisms. ⚖4 (retire the 12 codex wrappers via the entry point) was ruled earlier the same day.
Still owed before this feeds 9.7: a premise-verifier pass over this file; the #45482 probe (9.1c); the premise-loop bound and
the codex `--worktree` canary measurements.

## How the two reviews compare

**They agree on the core.** Both independently put the same things at the top: the PREMISES block and attestation,
evidence grading (captured / captured-fail / claim-only), stability anchors against a second writer, licensed
dissent, and the cross-family review rule. Both drop claudex-loop's phases and front-end.

**Where they disagree, I checked the code, and astra was wrong on three facts.** Same command, control arm included
(`grep -c` in `python/src/dotfiles_setup/sdlc_team.py`; control `PLANNING_DISABLED` in `codex_lane.py` -> 2):

| Claim (astra) | Measured | Verdict |
|---|---|---|
| "FAST MODE and EFFORT ... `sdlc_team.py:47,:69` pass these through. Already wired" | `fast` -> **0** hits | FALSE for fast mode (effort exists, as a bare string) |
| "Codex CLI model override ... `sdlc_team.py` passes through" | `"--model"` -> **0** hits | FALSE — the team runs whatever `~/.codex/config.toml` says |
| "`_reap_lane()` cleans up" | `_reap_lane` -> **0** hits | FALSE — no such function (supervision is `start_new_session` x2 + `killpg`) |
| (Fable) `PLANNING_DISABLED` missing from `sdlc_team.py` | **0** hits vs control 2 | TRUE |
| (Fable) implement mode = `workspace-write` | `sdlc_team.py:747` | TRUE |
| (Fable) `timeout_s` defaults to `None` = unbounded | `sdlc_team.py:70,147` | TRUE |

So on "do we already have it", this matrix follows the Fable review. Astra's value was the codex-side weighting:
what a codex lane needs from its wrapper (verbatim spec, grading it cannot do itself, stop-on-dissent, anchors).

**Genuine disagreements left for Ray** are marked ⚖ below.

## A. Fix first — defects in OUR code the review exposed (not migrations)

| # | What | Evidence | Proposed |
|---|---|---|---|
| A1 | `sdlc_team` does not set `PLANNING_DISABLED=1` on the spawn env | 0 hits vs `codex_lane.py` 2; a lane truncated the shared plan files 2026-09-09 | **FIX** — import `codex_lane.LANE_ENV_OVERRIDES`, do not restate it |
| A2 | No model pin: no `--model` in argv, no `model =` in any `codex-sdlc-*.toml` | measured above; `token-routing.md` records silent divergence when the global changed | **FIX** — `model` is a REQUIRED enum on the input model (no default), resolved model recorded in the settlement |
| A3 | `implement` mode uses `-s workspace-write`, which this repo measured as failing lint/pytest; `ai-cli-invocation.md:20` still prescribes it | `sdlc_team.py:747`; `codex-sol-implementer.md:60-95` both arms | **FIX after 9.4 re-measures on codex 0.155.1** — the repo currently contradicts itself |
| A4 | `timeout_s: None` = no timeout | `sdlc_team.py:70`; `long-running-command-hangs.md` "MUST be run with a hard time bound" | **FIX** — default by mode, `null` invalid |
| A5 | Request `effort` moves only the dispatcher; every specialist toml pins `high` | F42 (runtime precedence UNVERIFIED) | **MEASURE in 9.4**, then either drop the key from the tomls or make effort per-agent |

## B. MIGRATE — we lack it and it earned its place today

| # | Feature | From | Why (evidence) | Form in our version |
|---|---|---|---|---|
| B1 | **premise-verifier** agent: Pass 1 verify rows, Pass 2 hunt unlisted premises, provenance rule | fable F7-F8 | #1202: 1 REFUTED row + 18 unlisted premises over 3 rounds; r3 showed a respec item was a harness artifact; the advisor lane missed all of it. No repo-owned definition exists | `.claude/agents/premise-verifier.md`, Claude-side, read-only |
| B2 | PREMISES block, typed rows L/I/P/E/A, "no citation, no row" | fable F7 | same | skill prose + the 7-heading check in B9; do NOT port the regex grammar |
| B3 | **Attestation bound to the spec's SHA256** | fable idea + **claudex `runner.py:247-254`** | fable admits a stale attestation passes its gate; claudex already solved it | `premises_report` + `spec_sha256` on the request; `dispatch()` recomputes, mismatch -> `INVALID_REQUEST`. Makes "a corrected spec is a new spec" automatic |
| B4 | Evidence grading captured / captured-fail / claim-only | fable F28, astra top-5 | ours fail-closes on WHO spawned, says nothing on WHETHER verification ran | `verification_grade` in the settlement, graded ONLY from `--json` events (B7), never prose; `claim-only` => `gate-runner` |
| B5 | Stability anchors: base SHA + branch at launch, re-verified at settlement | fable F32, astra top-5 | repo memory records the two-writer failure twice | fields on `SdlcTeamDispatch`; fail closed |
| B6 | HEAD-unchanged check under `COMMIT: caller` | claudex `runner.py:373-375` | cheapest real check in either predecessor | one `git rev-parse` before/after |
| B7 | `--json` event log | claudex, fable F38 | replaces banner-scraping for parent thread id; makes B4 honest | argv change; keep stderr separate |
| B8 | Dissent as a SETTLED status | fable F48 | a refusal exits 0 — `sdlc_team` would say `completed`. Two correct dissents today | `dissent` in `SdlcSettledStatus` |
| B9 | Seven-part spec as a VALIDATED input; referenced-artifact stat | fable F1, F4 | premise rounds only worked because parts were addressable | heading check on a template WE own |
| B10 | Review tiers as a typed enum `mechanical / behavior / security` + a repo-owned silent-failure reader | fable F11, F14 | today's stack was exactly this; the reader found fail-open branches no other lens listed | required enum (no value = invalid); second agent file |
| B11 | Refutation pass, written down | fable F21 | today: cold-review HIGH F1 was TRUE, HIGH F2 was FALSE — acting on both would have shipped a wrong fix | skill prose |
| B12 | Respec bound of two, then surface residuals | fable F23 | #1202 hit the bound today | `round` on the request; `dispatch()` refuses >2 without override |
| B13 | Allowlist enforced at settlement (changed paths ⊆ allowlist) | fable F22 | today it is prompt-only | same shape as the existing spawn reconciliation |
| B14 | Review snapshot fingerprint; diff-size guard; `coverage` + `limitations` in the review schema | claudex `runner.py:86-109`; fable F18-F19 | a review applies to one snapshot | reuse `codex_verdict` schema in review mode |
| B15 | One sentence: codex "read-only" is a SHELL property — MCP tools can still write | claudex `runtime.md:33` | a codex lane does call exa/context7 when registered | rule prose |

## C. KEEP-AS-IS — ours is already equal or better

Spec-file-only delivery, verbatim (F3) · exclusive allowlist (F6) · cold review by ref + intent stripped (F16-F17) ·
stop states never read as approval, fail-closed spawn reconciliation (F25) · host re-runs the proof via `gate-runner`
(F29) · `COMMIT: caller` (F30) · python detached supervisor, no LLM in the transport path (F35, F49) · reap by
unique output path, never `pgrep codex` (F37) · per-run artifact dir (F39) · advisor pair (F13; fix the dangling
`fable-orchestrator:*` fallback names) · loud `CLI_MISSING`, never silently substitute (F45).

## D. DROP — dead weight

grok lanes / `mix` mode / grok effort · the regex premise gate + E-row / `SECURITY TIER` grammar + its PreToolUse
hook (measured DARK for every lane this repo uses: `codex-sol-implementer` rc=0 vs control
`fable-orchestrator:codex-implementer` rc=2) · fast mode · intent-parsed CLAUDE.md config lines + the setup wizard ·
the sonnet-wrapper-as-supervisor machinery (90 s slices, heredoc assembly, transcript bounds, worktree provisioning)
· claudex's front half (recon / interview / ADR formats / claudex-route / 5-round plan review / session resume /
Windows shims) · auto-relaunch on early death · `codex exec review` for now (same family for a codex diff, no `--cd`).

## ⚖ Left for Ray — the reviewers, or the evidence, genuinely split

1. **Round budgets.** Astra: ENHANCE (add counters). Fable: take only the respec bound of two (B12), drop claudex's
   5-round plan-review counter. *My recommendation: B12 only — two is the number measured here today.*
2. **Same-session reviewer across rounds** (`exec resume`). Astra: "reuse is fine". Fable: DROP — a FRESH cold
   reviewer worked today and even corrected its own round-1 error. *Recommendation: DROP.*
3. **Worktree provisioning.** Astra: ENHANCE (document). Fable: DROP — native `.worktreeinclude` already does it.
   *Recommendation: DROP, keep the one-writer rule.*
4. **Scope of the retirement.** Fable found our own 12 `codex-{sol,astra}-*.md` wrappers each hand-keep an argv
   block — the same defect as the plugin's wrappers. One entry point implies retiring those too, not just the
   plugin. *Recommendation: yes, in the same parity-then-removal sequence; it is the literal meaning of your
   single-entry-point ruling, but it widens 9.7 considerably.*
5. **What the removal actually costs us.** Measured: today's #1202 run used ZERO plugin agents and its premise hook
   never fired for our lanes — the plugin contributed doctrine TEXT only. So "parity" is mostly writing that doctrine
   into our skill + B1. *This lowers the risk of your parity-first ruling; it does not change it.*

## Addendum 1 — upstream research (2026-09-21, after Ray's ruling-1 objection)

Source: `research-upstream-predecessors-2026-09-21.md` (raw bytes at pinned SHAs under `.agent/kb/raw/upstream-predecessors/`).

**What I got wrong, corrected.** Ray named `DannyMac180/fable-advisor`; the two reviews read `fable-orchestrator` 1.21.0.
They are related but NOT the same text: fable-orchestrator **began as a fork of fable-advisor at its 3.1.0 and was detached
from the fork network on 2026-07-10** (the fork's own `README.md:238`, `CHANGELOG.md:3`). fable-advisor is the UPSTREAM, now
at **5.0.0 @4d6cc62**; its `skills/orchestration/SKILL.md` is 11,258 B against the fork's 50,162 B, and its spec contract has
SIX parts — the PREMISES block is the fork's addition. None of the three prior reviews had read fable-advisor (0 hits for
`dannymac` / `5.0.0`; control `upstream` -> 12). `mar3co/fable-orchestrator` 404s on GitHub, so the fork point is the fork's
own claim — UNVERIFIABLE from history.

**claudex-loop: zero drift.** The local 2.1.0 cache is a git clone whose HEAD == `origin/main` == `8cf5e2c` after a fresh
fetch (control: `HEAD~1..HEAD` -> 5 files). So the four skills Ray listed (`claudex-loop`, `claudex-route`, `codex-build`,
`codex-review`) were reviewed at current upstream; the gap was that I never said which copy had been read.

| # | New row | Source | Ruling proposed | Why |
|---|---|---|---|---|
| U1 | **`~/.codex/AGENTS.md` opt-out preamble**: `codex exec` loads that file every run; a machine-wide orchestration mandate makes codex DECLINE at exit 0 with an empty diff ("observed live 2026-08-04") | fable-advisor `agents/{codex,sol}-implementer.md:46-69`, post-fork (`ad2bdc3b`) — absent from fable-orchestrator AND from us (0 files; control 7) | **MIGRATE** | third independent source for the silent-success class behind B6/B8. Latent here today: `~/.codex/AGENTS.md` is 0 bytes and our trigger line lives in `.claude/CLAUDE.md`, which codex does not read |
| U2 | `--json`, `--output-schema`, `--model`, `turn.completed` parsing | OUR OWN `codex_lane.py` (4 / 1 / 2 / 1 hits) vs `sdlc_team.py` (0 each; control `exec` 4/9) | **A2 and B7 are sourced INTERNALLY**, not ported | `sdlc_team.py` is behind its sibling; reuse, do not re-derive |
| U3 | JUDGMENT CALLS line in the lane report | fable-advisor | ENHANCE B4 | ours 0 hits vs control 23/74/25 |
| U4 | Effort outside the enum is REFUSED, never rounded | fable-advisor | ENHANCE A5 | matches "unknown permutation fails closed" (9.12) |
| U5 | The two upstream implementer wrappers differ in 25 of 124 lines | fable-advisor | supports ⚖4 (Ray RULED: retire our 12 wrappers) | a third attestation that per-lane wrapper copies drift |

Provenance fix: `exec review`, `service_tier` and `features.fast_mode` come from fable-orchestrator, NOT claudex-loop (0 hits
in both upstreams; control `exec resume` -> `runner.py:149`). Bonus (fork `CHANGELOG:128`): `exec review --commit/--base` are
mutually exclusive with custom instructions on codex-cli 0.144.1 — re-measure in 9.4.

**Nothing in the upstream research overturns a proposed ruling in A-D.** ⚖ items 1-3 are withdrawn pending
`research-three-calls-2026-09-21.md` (Ray: "don't guess"). ⚖4 is RULED: retire the 12 wrappers via the entry point.

## Addendum 2 — cited research for the three ⚖ calls (Ray: "don't guess")

Source: `research-three-calls-2026-09-21.md` (13 raw sources under `.agent/kb/raw/three-calls/`). Tool honesty: step 00 (the
knowledge-base offline vendor docs) answered most of it and `exa` worked; **context7, firecrawl and last30days were NOT
invoked** — the agent recorded its reasons, but Ray asked for those plugins, so that part of the ask is still owed.

| ⚖ | Evidence-backed position | Key citations | Still open |
|---|---|---|---|
| 1 Round budgets | ONE respec bound (2) keyed to max unrefuted SEVERITY plus a verdict that can stop earlier; NOT per-phase counters. Name what CONSUMES a round (a dissent; a dangling spec path) | #1202: cold-review finding COUNTS went 12 -> 13 -> 7 while max severity went 2 HIGH -> 0 -> 0, and round 3's MEDIUMs include a regression from round 2's own fix (`cold-review-1202-r3`:24) — a counter would have read round 2 as "worse". Both predecessors treat the counter as a BACKSTOP (claudex README:63/137; fable SKILL:30). Anthropic ships only `maxTurns`, whose outcome is an error you resume past | whether the PREMISE loop needs its own bound (paid out all 3 rounds, n=1) |
| 2 Reviewer reuse | FRESH reviewer every round, `memory: local` for continuity, NO `codex exec resume` in the review path | measured on pinned 0.154.0: `exec -s read-only --help` rc=0 (control) vs `exec resume --last -s read-only` -> "unexpected argument '-s'"; resume also rejects `-C`, `--add-dir`, `-p`. openai/codex **#40149 (OPEN)**: a read-only session resumed without `-c sandbox_mode` WRITES — and our global config sets `danger-full-access` (third-party, not reproduced here). #19661 (OPEN): resume can silently become a NEW session. arXiv 2603.12123: fresh-session review F1 28.6% vs same-session 24.6% / 21.7% / 23.8% (p<=0.008) | `codex exec fork` and `codex exec review --base/--commit/--uncommitted/--output-schema` have 0 repo mentions and were never evaluated — the latter is the native review-by-ref primitive `use-tool-builtins.md` says to evaluate first. CORRECTION recorded: the claim "reviewing twice in-context is WORSE" does NOT survive (p=0.11) |
| 3 Worktree provisioning | BOTH, split by who creates the worktree: `.worktreeinclude` for non-secret inputs the harness must place; spec-named copy for secret-bearing / agent-controlling files (`.codex/config.toml`, `.claude/settings.local.json`) so exposure stays a per-dispatch decision | `.worktreeinclude` is a BOTH-vendor feature; Claude Code covers subagent worktrees explicitly (`$CC/worktrees.md:195`); codex scopes its own to "ChatGPT desktop app managed worktrees, NOT Git worktrees you create yourself" (`$CX/environments__git-worktrees.md:157`) | **my earlier "DROP — native already does it" was right for the Claude path and UNESTABLISHED for the codex path.** Canary measurement specified in the report |

Two fixes the research supports TODAY, independent of any ruling: `worktree.baseRef` is unset, so every isolated lane
branches off `main` rather than the PR branch (`$CC/worktrees.md:144-147`); and `.claude/worktrees/` is ignored only via
`.git/info/exclude:11`, so a fresh clone does not get it.

Shared failure signature across all three — a mechanism that stops working without saying so (exhausted budget read as
approval; resume escalating its sandbox or reopening as new; a `.worktreeinclude` pattern matching nothing,
`$CC/changelog.md:1128`). Each needs a control arm on EVERY run, not a one-time check.

## Addendum 3 — plugin pass (context7, ctx7, firecrawl, last30days, exa all invoked)

Source: `research-plugin-pass-2026-09-21.md` (12 raw files under `.agent/kb/raw/plugin-pass/`). Tool log: context7 MCP +
`ctx7` YES (index pinned at `rust-v0.155.1`); firecrawl developer-index YES, scrape FAILED rc=1 ("we do not support this
site", reddit); last30days PARTIAL (rc=0, 64 items, web lane HTTP 422); exa YES.

| # | Finding | Effect on the matrix |
|---|---|---|
| P1 | **openai/codex #45482 (OPEN, 0.153.4)**: an agent file's `sandbox_mode="read-only"` is ignored when spawned from `codex exec` — it inherits the parent sandbox; a write succeeded (rollout JSONL evidence). Our SDLC review lane is exactly this shape and our global config is `danger-full-access`. NOT reproduced here | NEW row **A6 — PROBE FIRST** (`task_plan.md` 9.1c). Until probed, "review mode is read-only" is a claim, not a property. Strengthens B15 |
| P2 | `codex exec review --base/--commit/--uncommitted` each declare `conflicts_with_all=[… "prompt"]` — `review --base main "<brief>"` is a PARSE ERROR | confirms D's "drop `codex exec review` for now": it cannot carry our cold-review contract text |
| P3 | #40149 still OPEN, no fix merged (armed: `40149 type:pr` -> 0 vs control 338) | Addendum 2 ⚖2 stands: no `exec resume` in the review path |
| P4 | Daemon auto-update PRs #43521 #44314 #43542 #43562 are MERGED and all post-0.154.0; #40969 = auto-update SIGKILLed live turns; **#41188 (OPEN): externally-managed installs unsupported** | Ray's "auto-update = yes" may not be implementable for a mise-installed codex; verify on 0.155.1 (`task_plan.md` 9.1b) |
| P5 | `codex exec --worktree` is behind an experimental gate (`--enable worktrees`), else it bails | the Addendum-2 worktree canary must pass that flag or it fails for the wrong reason |
| P6 | Round budgets: nothing from vendors or practitioners in 30 days (partial null — last30days web lane errored) | Addendum 2 ⚖1 stands on our own #1202 data |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject; the grep arms above.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — via the two reviews, local cache 1.21.0.
- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — via the two reviews, local codex cache 2.1.0.
