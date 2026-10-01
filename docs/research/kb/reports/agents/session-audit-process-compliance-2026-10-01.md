# Session audit — process compliance (Brief Q) — 2026-10-01

Session `03414a92-bb13-4324-83d2-fac74c0cd046`. Lane: session-handoff §1c, Brief Q method
(`docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md`). PRs in scope: #1475, #1486, #1490.
Evidence = transcript line numbers (`T:<line>`) from
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/03414a92-bb13-4324-83d2-fac74c0cd046.jsonl`.


## Method and probe arms

- Extraction: every `tool_use`/`tool_result` in the main transcript (360 tool calls) plus the 18 subagent transcripts
  under `…/03414a92-…/subagents/`, indexed by JSONL line (`T:<n>` = main transcript line).
- Skill/slash probe: `"skill":"…"` and `<command-name>` occurrences. **Control arm:** the same probe returns
  `research-sweep` ×2, `workflow-authoring` ×2, `session-handoff` ×2, and `/research-sweep`, `/session-resume`,
  `/reload-plugins` — so it sees skill calls when they exist. It returns **zero** `code-review`,
  `mattpocock-skills:code-review` or `verify` skill invocations.
- Codex probe: zero `codex exec review` / `codex exec -s read-only` *invocations* (all `codex exec` hits are quoted
  rule text in injected context).
- Gate probe: `for g in` inside a Bash `command` that also contains `gate` (python over the JSON, not a regex over raw
  lines). **Control arm:** the same scan finds `mise run gate -- run` in 4 subagent transcripts (4/20/36/38 hits), so it
  reads those transcripts.
- PR facts: `gh pr view <n> --json files,body,mergeCommit`; ship/land rc from the file-captured logs in the session
  scratchpad (`ship-n0.log`, `ship-scan.log`, `ship-s2900.log`, `land-1475.log`, `land-1486.log`, `land-1490.log`).

## Per-PR compliance table

| Step | #1475 research-enforcement | #1486 raw-mirror scan | #1490 S29-00 part 1 |
|---|---|---|---|
| Diff class | behavior-bearing; **spec'd** (`docs/specs/research-enforcement-2026-09-30.md` + scratchpad `spec-n0-round3.md`, `spec-n0-round4.md`); **session tooling** (`.claude/workflows/research-sweep-run.js`, skill, rule) | behavior-bearing; **spec'd** (scratchpad `spec-raw-mirror-scan.md`); **security path** (`.gitleaks.toml`); **session tooling** (`.claude/settings.json` `claudeMdExcludes`, `hk.pkl`, `scripts/check-claude-*.sh`) | behavior-bearing; no spec file (task_plan recipe + inline); touches `fnhook_gates.py` (fn-hook plugin gate) |
| Author family | Claude (Opus implementer `n0-round3-implementer`; round 1 Opus fallback from 09-30) | Claude (Opus `raw-mirror-scan-implementer`) | Claude (coordinator, inline) |
| lint / pytest / verify rc | T:176 → T:260 all rc=0 (166/0/4); T:441 → T:482 rc=0 (4379); T:576 → T:616 rc=0 (4401) | T:1196 → T:1235 rc=0 (4407); T:1290 → T:1335 rc=0 (4411) | T:2041 → T:2072 pytest **rc=1** (clang-last test) → fixed; T:2101 → T:2123 all rc=0 (4412); T:2230 → T:2278 lint **rc=1** (E501) → T:2295 lint rc=0 + touched tests; full pytest only via ship |
| ship rc | `ship-n0.log` rc=0 (6 gates PASS) | `ship-scan.log` rc=0 | `ship-s2900.log` rc=0 (lint/pytest/verify-contracts/hook-selfcheck/eval PASS) |
| bundled `/code-review` | **MISSING** | **MISSING** | **MISSING** |
| cross-family lens | Opus `cold-reviewer` ×3 rounds (T:178, T:443, T:578) — **same family**; codex lens OWED | Opus `cold-reviewer` ×2 (T:1198, T:1292) — **same family**; codex lens OWED | Opus `cold-reviewer` ×1 (T:2134) on `aef08679`+`0bbb6b2d` — **same family**; final commit `1b0f1338` **unreviewed**; codex lens OWED |
| `/mattpocock-skills:code-review` | **MISSING** (spec'd) | **MISSING** (spec'd) | N/A (no spec file) |
| repo `verify` skill | **NOT INVOKED**; substitute evidence: live Workflow `wf_be959049-495` `complete` (T:660/T:711) | **NOT INVOKED**; substitute evidence: `hook selfcheck` rc=0 in both gate runs (the skill's own row), `claudeMdExcludes` live arm 1→0 canary loads (T:1183) | **NOT INVOKED**; fnhook gate exercised only by pytest + hk `fnhook_gates` |
| land rc / main CI | `land-1475.log` rc=0; main run 36814240025 `conclusion=success` | `land-1486.log` rc=0; main run 36880762585 `success` | `land-1490.log` rc=0; main run 36898001290 `success` |

## Findings

### F1 — HIGH — bundled `/code-review` skipped on all three behavior-bearing PRs (third consecutive session)

- **Claim:** #1475, #1486 and #1490 shipped and landed with no bundled `/code-review`, which
  `.claude/skills/codex-sdlc-team/SKILL.md:193` requires for every behavior-bearing diff.
- **Evidence:** zero `code-review` skill/command invocations in the main transcript; PR rows above. Same miss on
  2026-09-28 (#1426) and 2026-09-30 (#1467, `findings.md` § "2026-09-30 — §1c process-compliance audit").
- **Control arm:** the skill probe finds `research-sweep`/`workflow-authoring`/`session-handoff` calls in the same
  transcript, so a `/code-review` call would have been seen.
- **Disposition: FIX-NOW** — run `/code-review` on the three squash commits `3a861923`, `3a3ca862`, `5d22d619`
  (post-merge; file confirmed findings as tickets). **PLAN** — the S28b-2 ship gate is the class fix and is unbuilt;
  add under Current Phase:
  `- (S28b-2, PROMOTED 2026-10-01) /code-review skipped on #1475/#1486/#1490 (3rd straight session after #1426, #1467): build the ship-gate check that refuses ship without a persisted /code-review report for HEAD, BEFORE the next behavior-bearing ship.`

### F2 — MED — `/mattpocock-skills:code-review` skipped on both spec'd PRs

- **Claim:** #1475 (spec `docs/specs/research-enforcement-2026-09-30.md` + round-3/4 specs) and #1486
  (`spec-raw-mirror-scan.md`) never got the Standards+Spec review (`codex-sdlc-team/SKILL.md:193-194`).
- **Evidence:** zero `mattpocock-skills:code-review` invocations (same probe and control arm as F1). Repeat of 09-30
  (#1464).
- **Secondary:** the #1486 spec and all round specs live only in the session scratchpad
  (`…/scratchpad/spec-*.md`), so a post-hoc Spec review can only run while that scratchpad survives.
- **Disposition: FIX-NOW** — run `/mattpocock-skills:code-review` since `a8233f81` for #1475 (spec
  `docs/specs/research-enforcement-2026-09-30.md`) and since `3a861923` for #1486 (copy
  `spec-raw-mirror-scan.md` to `docs/specs/raw-mirror-scan-2026-10-01.md` first so the review cites a tracked spec).

### F3 — MED — codex cross-family lens owed on every PR, but not recorded in `task_plan.md`

- **Claim:** all three PRs are Anthropic-authored and were cold-reviewed only by Opus (same family). The deferral is
  legitimate (codex usage limit until 2026-10-03 12:01, `task_plan.md:1202-1203`), but `task_plan.md:993-994` record
  the three PRs as DONE with no owed-lens line; only gitignored `progress.md` (T:783) mentions "codex lens after
  10-03", and only for #1475.
- **Evidence:** `grep -n -E '1475|1486|1490|3a861923|3a3ca862|5d22d619' task_plan.md` → only :993/:994, neither
  says "lens". Control: the same grep pattern style finds `CODEX LENS OWED` at `task_plan.md:1019` for 09-30 work.
- **Disposition: PLAN** — append under the 2026-10-01 ORDER block:
  `- CODEX LENS OWED (>= 2026-10-03 12:01): Claude-authored, Opus-reviewed only — #1475 3a861923, #1486 3a3ca862, #1490 5d22d619 (incl. unreviewed review-fix 1b0f1338); run mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> per squash commit; S29-00b commits 9421b5de/f8f4adf9 join the list when shipped.`

### F4 — MED — #1490's review-response commit `1b0f1338` shipped unreviewed

- **Claim:** the cold review (T:2134) covered `aef08679`+`0bbb6b2d`; the fix commit `1b0f1338` (new matcher test,
  rule-description rewrite, `test_image_smoke.py` helper refactor) was committed (T:2300) and shipped (T:2305) with no
  re-review and no Ray ruling waiving one. #1475 and #1486 did get narrow re-reviews (T:578, T:1292), so the session
  knew the pattern. Repeat of the 09-30 finding "final respec commits unreviewed with no Ray ruling" and of
  `task_plan.md:1215` ("every review-response commit this session shipped unreviewed").
- **Disposition: FIX-NOW** — covered by F1's `/code-review` of `5d22d619` and F3's owed codex lens; add the
  `1b0f1338` hunk explicitly to that review's scope.

### F5 — MED — premise-verifier never run on the four specs, including a security-path spec

- **Claim:** four seven-part specs were written and dispatched (`spec-n0-round3.md` T:368, `spec-n0-round4.md` T:491,
  `spec-raw-mirror-scan.md` T:970, `spec-s2900b.md` T:2458) with no `premise-verifier` pass. The agent definition calls
  for it on "every corrected or follow-up spec" and on security changes; #1486 is a secret-scanning change. The first
  #1486 cold review's main finding was **the spec's own mistake** (T:1275), the defect class premise verification
  exists to catch pre-dispatch. Repeat of 09-30 ("respec PREMISES not premise-verified").
- **Evidence:** Agent `subagent_type` values used this session: `cold-reviewer`, `general-purpose`, `issue-filer` —
  no `premise-verifier`.
- **Disposition: PLAN** — add: `- (S29-2) dispatch premise-verifier on every spec before the implementer lane (missed 4/4 on 2026-10-01; #1486's spec error surfaced only at cold review T:1275); make gated-implementation refuse a spec without a PREMISES verdict file.`

### F6 — MED — cold-review briefs never state the author family; PR bodies omit the fallback

- **Claim:** 0/7 cold-review briefs (T:178, 443, 578, 1198, 1292, 2134, 2538) state the author's family, which
  `codex-sdlc-team/SKILL.md:183-184` requires; 3 of 7 open with intent framing (`Focus:` / "Focus on whether …"),
  against "no intent framing" (:183). PR bodies #1475/#1486/#1490 contain 0 matches for `fallback|codex|usage limit`,
  though `task_plan.md:1202-1203` says "state the fallback in every report/PR". Repeat of 09-30 ("PR bodies omit
  fallback").
- **Control arm:** the same per-brief check reports `focus=True` on 3 briefs, so it reads brief text; the body grep
  returns 5/2/1 hits for `review` in the same three bodies.
- **Disposition: PLAN** — add: `- (S29-2) review briefs: state author family + "same-family fallback, codex lens owed" while codex is limited; ship's PR-body template carries a Review-lanes line (lens, family, fallback) — 0/3 PRs and 0/7 briefs had it on 2026-10-01.`

### F7 — LOW-MED — hand-batched `for g in` gate loops (eager rule `verify-before-advancing.md`)

- **Claim:** three real loops: main T:176 and T:441 (both #1475 gates) and `n0-round3-implementer` transcript line 480
  (`for g in lint pytest verify lint-docs; do mise run gate …`). Implementer line 200 also runs a no-op
  `for g in verify lint-docs; do :; done` before single gate calls. The main session self-corrected from T:576 onward
  (8 later runs, one command per gate). Repeat offender (09-30 R-J ×11); guard `task_plan.md:1125` (S29-2 R3+) and
  `mise run gates` (`task_plan.md:1378`, S28-3) are both still unbuilt.
- **Disposition: PLAN** — prefix `task_plan.md:1125` with: `RECURRED ×3 on 2026-10-01 (main T:176/T:441, n0 implementer L480) — build before S29-0.`

### F8 — LOW — repo `verify` skill not invoked on three session-tooling diffs

- **Claim:** #1475 (`.claude/workflows/research-sweep-run.js`), #1486 (`.claude/settings.json`, `hk.pkl`, stub/pairs
  scripts) and #1490 (`fnhook_gates.py`) touched session tooling; `.claude/skills/verify/SKILL.md` was never invoked.
- **Mitigation:** real-surface evidence ran anyway: live `research-sweep-run` `wf_be959049-495` `complete`; the
  `claudeMdExcludes` canary arm (InstructionsLoaded 1 → 0 records, T:1183); `hook selfcheck` rc=0 (a verify-skill row)
  in T:1196/T:1290; land smoke tiers 1-3. So the gap is procedural, not evidential.
- **Disposition: PLAN** — add: `- verify skill: add recipe rows for (a) a claudeMdExcludes canary arm (InstructionsLoaded with/without) and (b) a one-question research-sweep-run live arm, so the 2026-10-01 ad-hoc arms become the skill's procedure.`

### F9 — LOW — #1490 implemented inline by the coordinator, with an unrelated fix bundled

- **Claim:** S29-00 part 1 had no seven-part spec and no implementer lane; the coordinator edited `renovate.json`,
  `renovate_dryrun.py`, `fnhook_gates.py` and tests directly (T:1675-T:2211), and folded in the `fnhook_gates`
  `--no-deps` fix for a failure that predated the branch (stash control arm, T:1803). The doctrine is "only execution is
  delegated" (`.claude/CLAUDE.md` § Cross-vendor orchestration). The bundling was disclosed to Ray (T:1823), but no
  question asked whether to split it.
- **Disposition: PLAN** — note under S29-2: `- 2026-10-01 #1490 was coordinator-implemented without a spec (the Opus fallback lane was available); route follow-ups through the implementer lane + spec, and split pre-existing-failure fixes into their own PR unless Ray rules otherwise.`

### Compliant (no finding)

- Every PR has recorded gate rcs from one file-captured `mise run gate -- run <g>` per gate (after T:441), both red
  runs (T:2072 pytest rc=1, T:2278 lint rc=1) were fixed before shipping, and the ship log re-ran the full suite.
- `ship` rc=0 ×3, `land` rc=0 ×3, and main CI `conclusion=success` ×3 are read from the logged rc and API conclusion,
  not task notifications.
- Narrow cold re-reviews closed the review loops for #1475 (round 4/4b, T:578 SHIP) and #1486 (round c, T:1292 SHIP).

## Totals

9 findings by primary disposition: **FIX-NOW 3** (F1, F2, F4; F1 also carries a PLAN line); **PLAN 6** (F3, F5, F6, F7, F8, F9). Severity: 1 HIGH, 5 MED (F2-F6), 1 LOW-MED (F7), 2 LOW.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR #1475/#1486/#1490 files, bodies, merge commits; task_plan/findings/skill text
