# Session audit — repeat offenders (Brief R), 2026-10-01

Session `03414a92-bb13-4324-83d2-fac74c0cd046`. Method: Brief R of
`docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md` (method only).
Status: COMPLETE (written incrementally).

## Findings

Extraction: main transcript (3,184 records) indexed by record number `[N]`; 18 subagent transcripts under
`…/03414a92-…/subagents/` scanned for hook denials, zsh aborts and gate loops. Anchors below are `main:[N]` or
`<agent-file-prefix>:[N]`. Control arm for the deny scan: the regex `hook error` returned the known `[802]` `====`
deny and the 3 AskUserQuestion denies, so the scan sees denies; the gate-loop regex returned the known `main:[176]`.

### F1 — MED — hand-batched `for g in …; do mise run gate -- run $g` (third session running)

- Occurrences: `main:[176]` (gates-n0), `main:[441]` (gates-r3), lane `agent-an0-round3-implementer:[480]`, lane
  `agent-ab650702436aba2ff` (cold-reviewer):[367]. Coordinator self-reported it to Ray at `main:[587]` ("My first two
  gate runs this session had the same shape"). After `[587]` the coordinator switched to an unrolled
  `gate run lint >> $L; echo "GATE lint rc=$?"; gate run pytest …` chain (`[576]`, `[1196]`, `[1290]`, `[1766]`,
  `[2041]`, `[2101]`, `[2230]`, `[2536]`) — 8 more hand-batches that obey the letter of the rule, not its intent.
- Prior warning that failed: eager `.claude/rules/verify-before-advancing.md:29` ("Never hand-batch `for g in …`");
  memory `project_session_2026-09-29.md` ("`gate run` not `grep rc`"); prior audit
  `session-audit-repeat-offenders-2026-09-30.md` F3 (11 occurrences); plan rows `task_plan.md:1125` (S29-2 R3+) and
  `:1378` (S28-3) — both still unbuilt.
- Root cause (not a discipline problem): `dotfiles_setup/gate_result.py:220-222` — `run_parser.add_argument("name")`
  takes exactly ONE gate, so there is no sanctioned batch form and every multi-gate check becomes a hand-rolled
  batch.
- Disposition — MACHINE (two parts, in order):
  1. `python/src/dotfiles_setup/gate_result.py`: `run` takes `names` with `nargs="+"`, runs them sequentially,
     writes each typed result, prints one `GATE <name> rc=<n>` line each, and exits with the first non-zero rc
     (or max). Test `tests/test_gate_result.py::test_run_many_returns_first_failure_rc` — arm: `gate run lint
     <bogus>` exits 2 even when lint passes. Rule text `verify-before-advancing.md:28` becomes
     "`mise run gate -- run lint pytest verify lint-docs`".
  2. `hook_guard.py` new dated `Rule("hand-batched gate loop", r"\bfor\s+\w+\s+in\b[^;]*;\s*do\b[^;]*mise\s+run\s+gate\s+--\s+run\s+\$")`
     whose message names the N-name form; test both the real loop (deny) and a quoted mention (allow). The
     unrolled chain is then legal-but-pointless and needs no rule.

### F2 — LOW — unquoted `echo ====` separator: 8 guard denies (1 main, 7 lanes)

- Occurrences: `main:[802]`; lanes `a2601a48`(cold-reviewer):[63], `a53806340`:[66], `ab5f2b018`(issue-filer):[18],
  `ab650702`(cold-reviewer):[25], `abdad20c`(cold-reviewer):[27], `mods-fable-synth`:[59],
  `raw-mirror-scan-implementer`:[429] (plus `a792ed12`:[33], which is a lane quoting the main deny, not a new one).
- Prior warning: memory `feedback_zsh_equals_expansion`; `mise-tasks-only.md` table row; `hook_guard` deny (#1388).
- The machine check WORKS (every instance was caught before running); the residue is one wasted round-trip per
  lane. Lanes never load the memory and rarely the eager rule's table row.
- Disposition — MACHINE (optional, cost-only): convert the #1388 rule from deny to rewrite — PreToolUse
  `hookSpecificOutput.updatedInput` replaces the command with the separator quoted
  (`$CC/hooks.md:1060`, `:1808`). Caveat to resolve first: `:1808` says `updatedInput` combines with `allow` (skips
  the permission prompt) or `ask`; confirm a no-decision `updatedInput` is honored before building, or this
  becomes an auto-approve. Otherwise: needs Ray ruling that a 1-round-trip deny is acceptable as-is.

### F3 — MED — zsh unmatched-glob abort (`no matches found`) recurs in lanes; S29-2a still unbuilt

- Occurrences: `a289b84a`(cold-reviewer):[155] (`.agent/logs/*s29*`), `ab650702`(cold-reviewer):[52]
  (`--include=*.yml`) and [97] (`--include=*.js`), `mods-fable-synth`:[146] (`/p…`); MAIN `main:[917]`
  (`agnix*`, rc swallowed: result `is_error:false`) and `main:[3128]` (`.agent/plans/session-2026-10-01*`). Total 6
  (2 main, 4 lanes). The main ones were found by a whole-record string search after the first (`is_error`-filtered)
  scan missed them — the filter was a bound (probes rule 3); lane counts came from the unfiltered scan.
- Prior warning: prior audit 09-30 F2 (21 aborts in 12 transcripts), 09-29 R1, plan `task_plan.md:1130` (S29-2a:
  probe `CLAUDE_CODE_SHELL=bash`) — unbuilt.
- Disposition — PLAN: execute S29-2a now (it is the cheaper, class-level fix: with bash, unmatched globs pass
  through literally); if refuted, ship the `hook_guard` unquoted-`--include=*` rule from S29-2 R1.

### F4 — HIGH — an unverified claim about a merged PR or an upstream cadence, put in an AskUserQuestion PRO/CON, steered Ray's ruling (2 in one session; corrected both times only after the ruling)

Anchor note: `main:[N]` is the 0-based JSONL record; sibling lanes cite `L<N+1>`.

- `main:[825]` (ask) → `main:[826]` (Ray ruled "Ticket it, decide later") → `main:[1005]`/`[1007]` correction: the
  recommended option's PRO said "#1475, just landed, already enforces native-first research inside sweeps". False —
  the merged diff keeps native-first prose-only. The citation was a bare `PR #1475`; nobody had read its diff for
  that claim. Ray had to re-rule at `[1015]`.
- `main:[1569]` (ask): the "Wait" option's CON said python-build-standalone ships "usually within days" and "the same
  failure recurs on every python patch release". `main:[2043]` correction: "The 'lag' was under a day, not a pattern."
  The ruling (split python into its own group) survived, but its stated motivation was an un-measured generalisation.
- Prior warnings that failed: `.claude/rules/probes-need-a-control-arm.md` rule 6 (an inherited claim is not a
  measurement) and rule 7 (cross-check before reporting); `verify-before-advancing.md` "carry a number with its
  CONDITION"; memory `feedback_open_ticket_is_not_evidence`; prior audit `session-audit-repeat-offenders-2026-09-30.md`
  F1 (an absence claim with no control arm relayed to Ray as fact — the same class, the previous session).
- Why the existing machine check did not fire: `ask_quality.py` requires a citation, and both asks had one — a
  `#NNN` satisfies it without anyone reading what `#NNN` contains. The gate certifies the citation's *presence*, not its
  *support* (the `feedback_forbid_tokens_substring_fragile` shape).
- Disposition — MACHINE (narrow, string-level; Ray ruling on whether to accept the heuristic):
  `python/src/dotfiles_setup/ask_quality.py`: when an option description makes a behavioural claim about a
  PR/issue/release (`\b(already|enforces?|guarantees?|blocks?|prevents?|usually|always|every)\b` within the same
  sentence as `#\d+` or a version), require a `path:line` or a URL anchor in that option — a bare `#NNN` no longer
  suffices. Deny text: "a claim about what #NNN *does* needs the line that does it". Test
  `tests/test_ask_quality.py::test_behaviour_claim_about_pr_needs_line_anchor` — arm: the verbatim `[825]` option
  text denies; the same text with `` `.claude/workflows/research-sweep-run.js:120` `` allows; a description citing
  `#1475` with no behavioural verb allows (control). Limit, stated: it forces an anchor, not a true one.

### F5 — HIGH — asked Ray (or designed) before searching the plan/issues for his prior asks: 4 instances, two of which Ray called out ("i've asked for this repeatedly before")

- `main:[2700]` q3 asked "'Enable all settings for Claude telemetry': which scope do you mean?" — already settled by
  **RULING (Q22)** at `task_plan.md:2112` (2026-09-15: "all features enabled = the FULL documented surface… operator
  specifically suspects OpenTelemetry settings we are not enabling").
- `main:[2920]` q1 "Where should telemetry go?" → Ray `main:[2928]`: "i've asked for this repeatedly before … can it
  just write jsonl … to a directory per project". q2 "How should the mod-exposure audit be built for every project?"
  → Ray: "i've asked about this already, it might be in the task plan backlog — dotfiles should host all scripts for
  ~/.config/mise/config.toml". The plan carries it at `task_plan.md:1074-1080` (S29b global-mise scripts, held port PR
  `feat/s29b-global-mise-scripts`) and `:1963-1975` (§5b = #1014; Q23 = #431). The first plan/issue search of the
  topic ran at `main:[2933]` — AFTER Ray's complaint (the commands `[2668]`–`[2920]` contain no `task_plan.md`
  grep or `gh api search/issues` for telemetry/global-mise).
- `main:[3008]` proposed a NEW `research/saved-searches.toml` registry; `main:[3026]` then found the N1 `github-watch`
  spec already designs that registry (`watches.toml`). Ray's self-improvement ask also pre-exists at
  `task_plan.md:1254` and `:2243`.
- Prior warnings that failed: memory index ⭐ lines for 2026-09-11c ("recording was never the gap, RETRIEVAL was;
  search issues BEFORE diagnosing"), 2026-09-12b ("five retrieval misses"), 2026-09-15 ("three retrieval failures");
  `.claude/rules/graphify-first.md` (and the graph cannot answer this: #1054, zero markdown nodes);
  `session-resume` skill (reconciles the plan at start, not at each ask). Three prior §1c retrieval-miss audits
  (`session-audit-retrieval-misses-2026-09-28/29/29b.md`) — the class is now ≥4 sessions old.
- Why prose keeps failing: the trigger is "about to ask Ray / about to design", and nothing observes that moment
  except the `AskUserQuestion` PreToolUse hook, which already runs `ask_quality`.
- Disposition — MACHINE: `python/src/dotfiles_setup/ask_quality.py` gains a prior-ask check. For each question,
  extract content words from `header` + `question` (drop a stoplist), grep `task_plan.md` lines carrying
  `RULING|Ray:|Ray ruled|Ray's|(Q\d+)` (pure python, local file, no network — keeps the hook fast and offline), and
  if ≥1 such line matches ≥2 content words and the question's citation corpus does not cite `task_plan.md` (or the
  `#NNN` on that line), DENY listing up to 3 hits: "Ray may have ruled this already: task_plan.md:2112 … — cite it, or
  re-ask NAMING the prior ruling". Test `tests/test_ask_quality.py::test_denies_ask_with_uncited_prior_ruling` with
  a tmp `task_plan.md` fixture: the verbatim `[2920]` q1 + a `RULING (Q22) … OpenTelemetry` line → deny; the same ask
  citing `task_plan.md:2112` → allow; an ask on an unrelated topic → allow (control); a fixture with zero RULING lines
  → allow (fixture arm, rule 8). Covers `[2700]`/`[2920]`; does NOT cover the design-before-search shape of
  `[3008]` (no ask was the trigger) — for that, PLAN row: `codex-sdlc-team` spec contract PREMISES gains a mandatory
  "prior designs searched: <grep cmd> → <hits>" row, which `premise-verifier` re-runs.

### F6 — HIGH — every implementation unit needed cold review to find spec/design defects; `premise-verifier` was never dispatched (4 units, 7 cold reviews)

| Unit | Implementer dispatch | Cold-review verdicts (rounds) | Defects only cold review found |
|---|---|---|---|
| N0 research-enforcement | `main:[383]` (+ rounds 4, 4b by SendMessage) | `[178]` SHIP-WITH-FIXES 6 MED → `[443]` SHIP-WITH-FIXES 2 MED → `[578]` SHIP | F1 regression (all planner runs fail ⇒ `complete`); F6/F7 untested lines; R1/R2 |
| raw-mirror-scan | `main:[974]` | `[1198]` SHIP-WITH-FIXES → `[1292]` SHIP | F1 allowlist suppresses more than the SHA FP; F3 reviewer's mutations m2–m5 GREEN although the implementer reported "every mutation RED" |
| S29-00 | coordinator inline | `[2134]` SHIP-WITH-FIXES | F1 `renovate.json:103` claims "auto-merges once a standalone build exists" — false |
| S29-00b | `main:[2462]` | `[2538]` SHIP-WITH-FIXES 2 MED (then rounds b, c) | F1 one `drift` bool gates both producers (contradicts its own comment); F2 new half discards the image-lock half (#887 deadlock); F6 no contract binds the new half; F8 "idempotent … cannot loop" wrong mechanism |

Two defect classes recur across units, each already named in memory:
(a) **tests/mutations that cannot fail, chosen by the implementer** — `feedback_coarse_mutation_certifies_nothing`,
`feedback_sharp_vs_coarse_mutation`, `feedback_test_right_answer_wrong_reason`;
(b) **prose (comments, rule descriptions) claiming more than the mechanism does** — the same shape as F4,
`feedback_forbid_tokens_substring_fragile`.

- Prior warning that failed: `.claude/skills/codex-sdlc-team/SKILL.md:173-175` — "A spec that … touches security,
  concurrency or migrations goes to `premise-verifier` before dispatch, and again for every corrected revision's
  changed rows." raw-mirror-scan edits `.gitleaks.toml` allowlists (security) and S29-00b changes a token-minting CI
  job (F7: App token minted before PR-controlled code); N0 rounds 3/4/4b are corrected revisions. A search of the main
  transcript for a `premise-verifier` dispatch returns 0 (`grep -c premise` over the tool index = 2, both prose;
  control: the same index returns all 7 `cold-reviewer` dispatches). Implementers re-checked their own PREMISES
  instead, and one premise count was wrong (raw-mirror P2: 39 vs 40, `main:[1074]`).
- Contributing cause: the repo's own `/gated-implementation` (`.claude/workflows/gated-implementation.js:6,91`)
  hard-codes `codex-sol-implementer`, and codex was usage-limited until 2026-10-03 (Ray's ruling `main:[304]`: Opus
  implementer). So every unit was hand-orchestrated, and the hand orchestration dropped the premise step; the
  workflow's `attestation` (`:87`) is optional anyway.
- Disposition — MACHINE (two parts):
  1. `.claude/workflows/gated-implementation.js`: add `args.implementerType` (default `codex-sol-implementer`, allow a
     Claude implementer when codex is down) and a `Premises` phase that dispatches `premise-verifier` and refuses to
     proceed on any REFUTED row, mandatory unless `args.premiseExempt` carries a reason. Test in
     `tests/test_workflows_js.py`: a scenario whose premise-verifier stub returns `REFUTED` must end with status
     `premise-refuted` and dispatch no implementer; control: all CONFIRMED proceeds.
  2. Same workflow, `args.mutations`: the ARCHITECT lists mutations (file + sed/patch) in the spec; the Gates phase
     applies each, requires the named test to go RED, restores with `cmp`. The implementer no longer chooses the
     mutations that certify its own tests — the class (a) failure. Test: a mutation that leaves the test green ⇒
     status `mutation-survived`.
  Class (b) (overclaiming prose) has no mechanical check; it stays a cold-review lens — needs Ray ruling that it
  stays review-only.

### F7 — MED — recommended AGAINST a ruling Ray gave ~150 records earlier in the same session (and against the repo's encoded stance)

- `main:[2046]` Ray: "we want to be on the latest python everywhere"; coordinator recorded it at `findings.md:2613`
  ("GOAL: latest python everywhere"). The repo already encodes the stance: `minimum_release_age = "0s"` at
  `mise.toml:148` and `.config/mise/conf.d/shared.toml:24` (the 7d gate removed 2026-09-10), and the coordinator
  printed those lines itself at `main:[1533]`.
- `main:[2200]` then recommended `minimumReleaseAge "2 days" (Recommended)` for python; the other option's PRO even
  said "matching your 'latest everywhere' goal". Ray `main:[2201]`: "i want the most recent version always".
- Prior warning: memory `feedback_clarify_before_acting` ("A user ruling conflicting with a protocol ⇒ re-ask NAMING
  the conflict" — here the conflict was with a fresh RULING, and the recommendation sided against it).
- Disposition — MACHINE: the same `ask_quality.py` prior-ruling check proposed in F5, with its corpus widened to
  `findings.md` lines matching `Ray( ruling|:| ruled)` (the file the coordinator writes rulings to at receipt). Deny
  when a `(Recommended)` option matches a recorded ruling's topic and the question does not cite that line. Test
  fixture: `findings.md` with the verbatim `:2613` line + the verbatim `[2200]` ask → deny; same ask citing
  `findings.md:2613` → allow. Caveat: `findings.md` is gitignored and machine-local, so the check must treat a
  missing file as "no corpus" (allow), never as an error — the hook fails open by design (#343).

### F8 — LOW — gate piped into `tail` (1, denied) — existing machine check held

- `main:[2089]`: `uv run --project python pytest tests/test_p2996_single_literal.py -q 2>&1 | tail -1` → denied
  (`main:[2090]`); the compound command's `renovate.json` rewrite was cancelled with it and re-run correctly at
  `main:[2095]`/`[2101]` (the post-deny side-effect re-check `mise-tasks-only.md` asks for did happen).
- Prior warnings: `long-running-command-hangs.md` rule 3; prior audit 09-29b F3 (15 in 5 sessions).
- Disposition: none new — the `hook_guard` rule `gate command piped to head/tail` is the machine check and fired. A
  scan of all 19 transcripts found no gate pipe that RAN (the other regex hits were `grep … pytest.log | tail` reads
  of a log file, not gate runs).

### F9 — LOW — AskUserQuestion quality denies: 3 of 25 asks — existing machine check held

- `main:[2722]` (q3 no `(Recommended)`), `main:[2756]` (option 3 no PRO/CON), `main:[2894]` (q1 no citation). Each a
  different missing element; each re-asked compliant in the next call (`[2732]`, `[2759]`, `[2898]`).
- Disposition: none new — `ask_quality.py` is the machine check and it held. Noted only because the `[2722]` miss was
  an "Anything else?" free-text catch-all question, which duplicates the harness's own "Other" slot
  (`clarify-before-acting.md` rule 2: "do not pad the choices"). PLAN-free; if it recurs, add an `ask_quality` deny
  for a question whose options are all free-text prompts.

### F10 — LOW — bash-only `${!v}` indirect expansion in zsh (1)

- `main:[2687]`: `[ -n "${!v}" ]` → `(eval):1: bad substitution`; re-run with `printenv $v >/dev/null` at `[2692]`.
  0 occurrences in the 11 preceding session transcripts (searched `bad substitution`; control: `no matches found`
  returns 2 in this transcript), so not a repeat. The fallback chosen is the one `secrets-out-of-the-shell-env.md`
  rule 7 prescribes. Disposition: none (first occurrence; the zsh-vs-bash class is F3's S29-2a probe —
  `CLAUDE_CODE_SHELL=bash` would also make `${!v}` valid).

### F11 — MED — live pins hard-coded in tests broke a bot PR again; the 09-30 class fix (meta-test) is still unbuilt

- This session: #1449 (Renovate, image-build inputs) failed pytest on the bot PR because `tests/test_image_smoke.py`
  carried literal `hk 2.3.0` / `python 3.14.7` (`tests/test_image_smoke.py:793-796` docstring, written this session);
  fixed by INSTANCE in `5d22d619` (#1490) — `_shared_pin()` now reads `.config/mise/conf.d/shared.toml`. The S29-00
  cold review (`cold-review-s29-00-2026-10-01.md` F1) still had to name `tests/test_image_smoke.py:802,813` as
  "must be bumped by hand" before that change.
- Prior warning: prior audit `session-audit-repeat-offenders-2026-09-30.md` F5 (two pytest failures the day before,
  same file) with disposition MACHINE: "a meta-test that fails when a `tests/**` literal equals a live pin"; memory
  `feedback_fix_the_class_not_the_instance`. `grep -rn` for such a meta-test in `tests/` returns 0 (control: the same
  grep shape finds `_shared_pin` at `tests/test_image_smoke.py:790`).
- Disposition — MACHINE (unchanged from 09-30, now overdue): `tests/test_no_live_pin_literals.py` — collect every
  exact pin from `.config/mise/conf.d/shared.toml`, `.devcontainer/mise-system.toml` and `mise.toml` `[tools]`, then
  scan `tests/**/*.py` string literals (via `ast`, not regex) for `"<tool>" … "<live version>"` pairs or a bare
  literal equal to a live version of a tool named within N lines; fail listing `file:line`. Arms: re-insert
  `"3.14.8"` next to `"python"` in a scratch test file → red; historical fixtures like `"3.14.6"` (not a live pin)
  → green (control). Add as a PLAN row under S29-2 so it stops being re-proposed.

### F12 — LOW — brief mode: turn ended without SendUserMessage, 10 harness nudges (fourth session running)

- `main:[234]`, `[604]`, `[1223]`, `[1316]`, `[2513]`, `[2560]`, `[2645]`, `[2980]`, `[3196]`, `[3240]` (the
  `[807]` hit is a quotation of the 09-30 audit, excluded). Prior counts: 09-28: 2, 09-29: 9, 09-30: 6.
- Prior warning: memory `project_session_2026-09-28.md:23`; 09-29 dismissed-errors F7; 09-30 audit F10 (disposition
  "RAY RULING: accept the harness nudge as the machine check" — still unruled).
- Disposition: needs Ray ruling (carried forward unchanged). The harness nudge IS a machine check and it fires every
  time; nothing project-side can observe a turn's end without a Stop hook, and Stop hooks force a turn
  (`feedback_stop_hooks_force_a_turn`), so no better check exists in-repo.

## Summary

| # | Sev | Mistake | Count (this session) | Warning that failed | Disposition |
|---|---|---|---|---|---|
| F1 | MED | hand-batched `for g in …` gate loops | 2 main + 2 lanes, then 8 unrolled batches | eager `verify-before-advancing.md:29`; 09-30 F3; plan `task_plan.md:1125`, `:1378` | MACHINE: `gate run` takes N names (`gate_result.py:221`) + dated `hook_guard` rule |
| F2 | LOW | unquoted `echo ====` | 1 main + 7 lanes, all denied | `hook_guard` (#1388) held | MACHINE (optional): rewrite via `updatedInput`, after confirming no-decision semantics; else Ray ruling |
| F3 | MED | zsh unmatched-glob abort | 2 main + 4 lanes | 09-30 F2; plan S29-2a `task_plan.md:1130` (unbuilt) | PLAN: run S29-2a (`CLAUDE_CODE_SHELL=bash` probe) now |
| F4 | HIGH | unverified claim in an AUQ option steered a ruling | 2 (`[825]` #1475; `[1569]` PBS cadence) | probes rules 6/7; 09-30 F1 | MACHINE: `ask_quality` behavioural-claim ⇒ `path:line` anchor (Ray ruling on the heuristic) |
| F5 | HIGH | asked/designed before searching plan + issues for Ray's prior asks | 4 (`[2700]`, `[2920]`×2, `[3008]`) — Ray: "asked repeatedly" | memory 09-11c/09-12b/09-15; 3 prior retrieval audits | MACHINE: `ask_quality` prior-ruling grep of `task_plan.md`; PLAN: PREMISES "prior designs searched" row |
| F6 | HIGH | design defects found only by cold review; `premise-verifier` never dispatched | 4 units, 7 cold reviews, 0 premise checks | `codex-sdlc-team/SKILL.md:173-175` | MACHINE: `gated-implementation.js` `implementerType` + mandatory Premises phase + architect-owned `args.mutations`; overclaiming prose = Ray ruling (review-only) |
| F7 | MED | recommended against a same-session ruling | 1 (`[2200]` vs `[2046]`) | `findings.md:2613`; `mise.toml:148` | MACHINE: F5's check also reads `findings.md` ruling lines |
| F8 | LOW | gate piped to `tail` | 1, denied | guard held | none new |
| F9 | LOW | AUQ quality denies | 3 of 25 | `ask_quality` held | none new |
| F10 | LOW | bash `${!v}` in zsh | 1 (first) | — | none (S29-2a covers) |
| F11 | MED | live pins hard-coded in tests broke #1449 | 1 bot-PR failure; instance fixed in #1490 | 09-30 F5 (meta-test unbuilt) | MACHINE: `tests/test_no_live_pin_literals.py` + PLAN row |
| F12 | LOW | brief-mode turn ended without SendUserMessage | 10 | 09-30 F10 | Ray ruling (carried) |

Three of the HIGH/MED items (F4, F5, F7) share ONE enforcement point — the `AskUserQuestion` PreToolUse hook that
already runs `ask_quality.py`. Building them together is one PR with three test arms.

## Method and extraction control arms

- Main transcript parsed to a tool/text index keyed by 0-based record number; human messages and all 25
  `AskUserQuestion` pairs extracted separately (the sibling missing-requests lane independently counted 25 pairs — a
  cross-check that agrees).
- Deny scan: `hook error` in tool results; control = it returned the known `[802]` deny. Gate-loop regex
  `for \w+ in [^;]*;\s*do[^;]*gate`; control = it returned the known `[176]`. Lane scan used the same regexes over all
  18 `subagents/*.jsonl`.
- The `is_error`-filtered first pass MISSED the 2 main-transcript zsh glob aborts (their results carry
  `is_error:false`); a whole-record search found them. Counts in F3 are from the unfiltered pass.
- Prior-warning lookups: `MEMORY.md` index, `.claude/rules/`, `.claude/skills/`, `task_plan.md`, and the 09-29b/09-30
  repeat-offender reports.

## What this corpus still cannot answer

- Whether the 8 hand-unrolled gate batches after `[587]` ever produced a wrong verdict — each wrote its own typed
  result, and I did not diff the `.agent/gate-results/` JSON against the logged rc lines.
- Whether `updatedInput` without a `permissionDecision` is honored by PreToolUse (F2's caveat) — not probed.
- The transcript was still growing during this audit (3,184 → 3,240+ records); findings after ~`[3240]` are not
  covered.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue lookups #1014, #431 (titles/state) and
  local source/transcript reads.
