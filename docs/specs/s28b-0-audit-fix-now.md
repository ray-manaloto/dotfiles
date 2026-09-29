# S28b-0 — §1c audit FIX-NOW sweep

**EXECUTED 2026-09-29** in PR #1439 (squash `8454778c`); the OPEN rows below are the pre-implementation triage record. Do not re-dispatch.

Status: RATIFIED by the architect 2026-09-28c after Ray's rulings (AskUserQuestion). Drafted by `spec-scribe`;
revised by the architect. Revisions vs the draft: the plan pointer was DELETED by PR #1437 (Ray: "let's get rid of
plan pointer"), so T12/H9 (final gate) and T15 (pointer refresh) are DONE there and removed here; H10's control arm
uses the attestation; Q1 → the Q-S briefs file IS edited (H7b); Q4 → S7/S13/S14 are IN (H23-H25, literals verified
by the architect this session); the task_plan delta was applied by the coordinator (C6 DONE; D5 not applied).

Memory: `.claude/agent-memory-local/spec-scribe/` was consulted and is empty (first run).

## 0. Triage (every FIX-NOW item, checked at HEAD `cf5b914a` + working tree)

Probe tool: the Grep tool (ripgrep) over the working tree; this lane has no Bash, so
no `mise`/`git` command was run by the scribe. Every "absent" row names its control arm.

| Item | Report:line | Status | Evidence (probe → result; control) |
|---|---|---|---|
| T1 = S9 / MR-F5 bullet 3 (false "Renovate git-refs" prose) | retrieval-misses:78-80; missing-requests:167 | **OPEN** | `.github/workflows/AGENTS.md:18` still ends "`CLANG_P2996_REF`: Renovate git-refs."; `refresh.yml:20-23` still says p2996-refresh "was retired in favor of the Renovate git-refs manager, which bumps CLANG_P2996_REF in docker-bake.hcl + Dockerfile in lockstep". Control: same reads show the unrelated `refresh.yml:12-18` comment intact. DISSENT on S9's rewrite: ~250 chars into an AGENTS.md under agnix AGM-003's 12,000-char cap; this spec uses a shorter form (§3 H1). `Dockerfile:421`, `P2996-CACHE.md`, `p2996_refresh.py`, `mise.toml` prose are S28b-1 (task_plan.md:1011); a Dockerfile edit is an image build input, so it stays out of this PR. |
| T2 = S11 / R9-prose (eager rule endorses `timeout <n>`) | retrieval-misses:82-83; repeat-offenders:228-238 | **OPEN** (prose only) | `long-running-command-hangs.md:50` "wraps the loop with `timeout <n>` or `mise run bounded-wait`" with no host caveat. DISSENT on R9's "drop `timeout <n>` from the accepted-bound list": the guard still accepts it (`hook_guard.py:196-198` `_TIMEOUT_WRAPPER`, used at `:243`), so deleting the words would make the rule misdescribe the guard. Adopt S11's caveat form instead; the guard change (`bare_timeout_shim`) is S28b-4 (task_plan.md:1024-1025). |
| T3 = V15 ("no `timeout` binary" in agent prompts) | vagueness:190-199 | **OPEN** | Grep `no \`timeout\`\|\`timeout\` binary` (excluding `docs/research/**`) → 9 tracked `.claude/agents/*.md` hits: 3 Claude originals (`adversarial-critic.md:156`, `staleness-auditor.md:130`, `claude-code-expert.md:300`), 3 sol (`codex-sol-adversarial-critic.md:275`, `codex-sol-staleness-auditor.md:250`, `codex-sol-claude-code-expert.md:280`), 3 astra twins. Same grep over `.codex/` → 0 (the report's "12" counted 3 gitignored exports; control: the `.claude` arm of the same pattern hits 9, so the pattern works). Edit 6 authored files; astra regenerate. |
| T4 = V14(a) (advisor "the default advisor lane") | vagueness:176-188 | **OPEN** | `codex-sol-advisor.md:4` "The default advisor lane", `:15` "You are the default advisor lane:"; `.codex/agents/codex-sol-advisor.toml:12` "— the default advisor lane;"; astra twins identical. Contradicts `.claude/CLAUDE.md:70` "Neither is a default." and `.claude/token-routing.md:28`. `claude-advisor.md:3` ("the default advisor is a codex-*-advisor lane") is consistent (codex over Claude) and is NOT edited. |
| T5 = V20 (implementer "50 minutes has been observed") | vagueness:243-248 | **OPEN** | `codex-sol-implementer.md:30` and astra `:32` still carry it. |
| V14(b) (Standards 4 single-sourcing + md↔toml parity) | vagueness:183-188 | OUT-OF-SCOPE (S28b-4) | task_plan.md:1027 "R5 RULED: `codex-lane-mirror` generates the sol TOML body from the sol `.md`". |
| T6 = V1 (report filename collides same-day) | vagueness:13-25 | **OPEN** (doc half) | `.claude/skills/session-handoff/SKILL.md:117` and `.agents/…:117` still `session-audit-<kind>-<date>.md`. Machine half (no-overwrite guard) = R10 → S28b-4 (task_plan.md:1025). |
| T7 = V2 + V3 ("Briefs Q-S" letters; "reuse them") | vagueness:27-50 | **OPEN** | Same SKILL.md `:118-119` (both trees) still "Briefs M-P … and \"Briefs Q-S\" … ; reuse them." |
| T8 = V4 (bugs row scope) | vagueness:52-60 | **OPEN** | SKILL.md `:125` still "cold review of the branch diff by ref (base = merge-base with `main`)"; the 2026-09-28b bugs report reviewed only `3ba79a67` (bugs-28b:3,7). |
| T9 = V5 ("read-only" vs "add it there") | vagueness:62-70 | **OPEN** | SKILL.md `:116` "seven read-only reviews" vs `:129` "name the file that should carry it and add it there". |
| T10 = V22 (common finding contract) | vagueness:264-274 | **OPEN**, re-homed | The q-s briefs file (`session-handoff-briefs-q-s-2026-09-28.md:1-40`) has no common-contract paragraph. DISSENT on V2/V22's "edit the q-s file": it sits in the verbatim report tree and is the brief the 2026-09-28b lanes actually received (`agent-artifact-conventions.md` rule 8: fix authored pointers, not archived evidence). This spec puts the contract and the disambiguation in the SKILL §1c instead and leaves both brief files byte-identical — architect question Q1. |
| T11 = goal-history heading format | task_plan.md:998-999 | **OPEN** | `.claude/rules/goal-history.md` (read in full) never states the heading shape; the validator is `session_review.py:141` `^## (?P<title>\d{4}-\d{2}-\d{2} — [^\n]+)\n`. Iteration 042 itself is APPLIED (`goal-history.md:1858-1860`, heading `## 2026-09-28 — second session …`). |
| T12 = handoff→resume drift, FINAL GATE | task_plan.md:1000-1005 | **DONE in #1437** (ignore the rest of this row) | `session-handoff/SKILL.md:46-50` runs `plan-pointer` in step 1 only; `:281` runs `handoff-check` in step 5; step 6 (`:288-300`) runs `plan-attest` AFTER both and prints the resume line with no gate; checklist `:307` has no "after the last write". `plan_pointer.py:57` rewrites the file every run (`recorded_at` always changes), and `task_plan.md` is gitignored (`.gitignore:143`), so the only tracked artifact is `docs/agents/plan-pointer.json`. |
| T13 = FRESH ROUND-TRIP recipe | task_plan.md:1004-1005 | **OPEN** | `verify/SKILL.md:13-34` has no session-resume row. Grounding: `$CC/headless.md:312` "User-invoked skills and custom commands work in `-p` mode: include `/skill-name` in the prompt string"; `:37` `--bare` skips skills (must NOT be used); `:41` a non-bare `-p` run executes project hooks; `:309` `--allowedTools` prefix syntax `Bash(git diff *)`; `:33` exit code semantics. `session-resume/SKILL.md:84,94` makes `DISAGREEMENT:` mandatory when reality contradicts. |
| T14 = `.agents/skills/*` lockstep | brief item 8 | **CONSTRAINT** | `.agents/skills/**/SKILL.md` is GENERATED (`skills_mirror.py:2-18`, `write_mirror` `:354`), gated by hk `skills_mirror_parity` (`hk.pkl:722-723`). Edit only `.claude/skills/**`, then `mise run skills-mirror`. `RULES` rewrites `Claude`→`Codex` (`skills_mirror.py:124-125`), so new skill prose must not use the capitalised word for things that are Claude-only (write `claude -p`). `PER_FILE["session-handoff"]` (`:163-182`) must keep matching — do not edit the "two prior Claude sessions" or CLAUDE.md-stub sentences. |
| T15 = `docs/agents/plan-pointer.json` stale | brief item 8 | **VOID — file deleted in #1437** | File `recorded_at` `2026-09-29T01:44:21Z`, sha `7a80e015…` (read this run); task_plan.md was edited after. Refreshed by `mise run plan-pointer` as the implementer's LAST command. |
| T16 = V21 (devcontainer-workflow "holds ONE platform") | vagueness:250-262 | **OPEN** | `devcontainer-workflow/SKILL.md:57-60` unchanged; contradicts `mise.local.toml.example:45-47` and `sync.py:156-168`. |
| T17 = S2 (+ #1429 rule) sync `--check` outputs | retrieval-misses:44,62-63 | **OPEN** | `devcontainer-sync/SKILL.md:25,59-60` have rc 1/2 but no `check:` literals and no platform-absent rule. Literals verified `sync.py:879,884,886-887,890`; rc `:880,891`. |
| T18 = S3 sync record | retrieval-misses:45,64-65 | **OPEN** | Path `sync.py:278-280` (`re.sub(r"[^A-Za-z0-9._-]", "_", image_ref)`), `containers` keyed `f"{workspace_hash}:{arch}"` (`:275`), written by `write_sync_record` (`:323`). DISSENT on S3 wording "`/` and `:` → `_`": the rule is every char outside `[A-Za-z0-9._-]`. |
| T19 = S1 pr-workflow hook-selfcheck | retrieval-misses:43,60-61 | **OPEN** | `pr-workflow/SKILL.md:35` "→ `hook-selfcheck` (always-run:" still reads like a task. |
| T20 = S7 ship/land PR-number line | retrieval-misses:49,71-72 | **OPEN (Ray Q4)** — literals verified `pr.py:612`, `pr.py:910` | Scribe did not read `pr.py`'s success strings this run, so the proposed literals are unverified; recommend dropping from S28b-0 (Q4). |
| T21 = S5 tests may shell out only to shared.toml tools | retrieval-misses:47,67-68 | **OPEN** | `tests/AGENTS.md:110` is the "Subprocess usage" bullet; no shared.toml rule in the file (grep `shared\.toml\|jq` → only `:110`'s own line for `Subprocess`; control: same grep found `:110`). |
| T22 = S6 `gh issue view --comments` trap | retrieval-misses:48,69-70 | **OPEN** | `gh-cli-watch.md` § Canonical patterns (read via project instructions) has no `gh issue view` line. Rule is rule-synced by STEM only (`rule-sync.toml:51-56,64`), so no KB PR is needed. |
| T23 = S8 codex lens `-o` | retrieval-misses:50,73-77 | **OUT-OF-SCOPE (needs an arm)** | `-o` on `exec review` is unarmed (report's own caveat `:76-77`, #1296 precedent); the flag goes into the S28b-2 ship-gate spec. |
| T24 = S12 gitignored `.codex/agents` exports | retrieval-misses:54,84-85 | **OPEN** | `codex-sdlc-team/SKILL.md:18` "A `.codex/agents/*.toml` file is about to be written or edited." — no gitignored-export warning (grep `gitignored\|GITIGNORED` in the file → only `:18`'s neighbourhood unrelated; control `\.codex/agents` hit `:18`). |
| T25 = S13 / S14 (lock-image table syntax; research-sweep journal) | retrieval-misses:55-56,86-89 | **OPEN (Ray Q4)** — verified: `.devcontainer/mise-system.lock:2135-2145` `[tools.actionlint."platforms.linux-arm64"]`; a workflow `journal.jsonl` has 0 `"model"` keys while its `agent-*.jsonl` carries `"model":"claude-sonnet-5"` | Report grades both "low value"; not read this run. Q4. |
| T26 = V11 p2996 spec status | vagueness:132-143 | **OPEN** | `docs/specs/p2996-ref-currency-review.md:3` "Mode: **review**" with no executed marker; `:33` "~2.5 h cold in CI". The refuting evidence (`sdlc-team-p2996…md:141-144`) was NOT re-read by the scribe — row A3. |
| T27 = V13 R1/R3 wording | vagueness:159-174 | **OPEN** | `CONTEXT.md:36` "`-p 4444`"; `CONTEXT.md:38` "Never the host's by passthrough."; `AGENTS.md:166`; `verify/SKILL.md:33` "(`MISE_ENV=arm64` for arm64)". Profile facts: `mise.local.toml.example:35-43`. |
| T28 = V16 verify recipe wording | vagueness:201-211 | **OPEN** | `verify/SKILL.md:26` "sessions #1421/…"; `:31` `"<fresh>"`, "~314 bytes". |
| T29 = V17 prompt-audit-C §5 | vagueness:213-223 | **OPEN** | `prompt-audit-C-apply.md:80` `grep -rlF …` form; `:110` "planned separately." with no pointer. |
| V6 three "next session" claimants | vagueness:72-83 | APPLIED | task_plan.md:990 "NEXT-SESSION ORDER … supersedes the three separate \"next session\" claims". |
| V7 S27-14 "ask it FIRST" | vagueness:85-92 | **PLAN-ONLY** | task_plan.md:1157-1158 still "ask it FIRST next session" → delta D1. |
| V8 ship-gate "Also now" marks | vagueness:94-102 | **PLAN-ONLY** | task_plan.md:1053-1055 unmarked → delta D2. |
| V9 mise-native research owed | vagueness:104-114 | APPLIED | task_plan.md:1006-1007 "still owed: mise release notes for a native git-ref tracker". |
| V10 p2996 SCOPE | vagueness:116-130 | APPLIED (superseded) | task_plan.md:1008-1009 "bake default is the ONLY SHA literal"; the older `:1043-1045` text remains → delta D3 (mark superseded). |
| V12 Phase C / #1432 | vagueness:145-157 | APPLIED (partial) | task_plan.md:1033 "Phase C rulings/#1432 sit in the ARCHIVED section — treat them as live." `verify-ssh-outbound` not built is not named → delta D4. |
| V18 "NEXT SESSION" heading | vagueness:225-231 | **PLAN-ONLY, DISSENT** | The report's rewrite drops the token `NEXT SESSION`; `plan_pointer.py:19,22-25` and `handoff_check.py:221-228` select the active phase BY that token, so the rewrite would produce `missing_active_plan` and break both tasks. Delta D5 keeps the token. |
| V19 operator 0.158.0 | vagueness:233-241 | **PLAN-ONLY** | task_plan.md:1195 (Phase 11 item) → delta D6. |
| DE-F1 graph stale / S28-4 | dismissed-28b:57-70 | APPLIED | task_plan.md:1180 "✅ graph rebuilt fresh 2026-09-28b (`graphify-rebuild` rc=0, health fresh)". Not re-probed (no Bash) — A2. |
| DE-F2 glob half | dismissed-28b:72-94 | OUT-OF-SCOPE (S28b-3) | task_plan.md:1019-1023. |
| DE-F3 codex-schema regen | dismissed-28b:96-108 | UNVERIFIED → coordinator | Local gitignored output; scribe cannot run `mise run codex-schema-check`. PLAN half: item 26 (`task_plan.md:933-934`) still "0.157.0→0.157.1" → delta D7. |
| DE-F4, F5, F7, F9, F11 | dismissed-28b:110-212 | APPLIED (plan) | task_plan.md:1029-1033 (S28b-5). GitHub comments → Coordinator actions C1, C2. |
| DE-F6 S28-3 recurrence | dismissed-28b:137-147 | **PLAN-ONLY** | task_plan.md:1177 lacks the RECURRED note (grep `RECURRED` → only `:735`, `:1157`) → delta D8. |
| DE-F8 graphify 0.9.70 | dismissed-28b:164-172 | **PLAN-ONLY** | task_plan.md:1116 still "0.9.70" → delta D9. |
| DE-F10 #1434/#1435 plan line | dismissed-28b:188-198 | APPLIED | task_plan.md:1006. |
| MR-F1, F6, F7, F10 | missing-requests:128-225 | APPLIED | S28b-3 (:1019), S28b-1 (:1006-1014), S28-4 (:1180). |
| MR-F2 Renovate/Dependabot health | missing-requests:136-149 | APPLIED (plan) | task_plan.md:1006-1007. #1434 comment → C3. |
| MR-F5 SDLC finding 5 scope | missing-requests:161-178 | APPLIED (plan) | task_plan.md:1010-1014. #1434 comment → C3. |
| MR-F8 goal-history 042; ship 3ba79a67; MEMORY START HERE | missing-requests:206-215 | APPLIED | goal-history.md:1860; HEAD log `cf5b914a docs/p2996 ref currency review (#1436)`; MEMORY.md index "2026-09-28b — START HERE". |
| MR-F9 fable backup tgz | missing-requests:217-220 | APPLIED | Glob `.agent/state/fable-orchestrator-*` → none; control Glob `.agent/state/*` → 12 gitignored files, so the glob sees that directory. |
| PC-F2 `/code-review` of #1426 | process-compliance:55-70 | APPLIED | `code-review-1426-2026-09-28.md` exists (Glob). PLAN half = S28b-2 (:1015). |
| PC-F8 persist p2996-branch lens | process-compliance:119-127 | **OPEN → coordinator** | Glob `codex-review-lens-*2026-09-28*` → 6 files, none for p2996 (control: same glob finds the 6 PR lenses). The source is `.agent/logs/codex-review-handoff-branch.log` (gitignored); only the coordinator can persist it verbatim → C4. |
| PC-F1, F5, F6, F7 | process-compliance:45-117 | APPLIED (plan) | S28b-2 (task_plan.md:1015-1018). |
| RO R1-R10 machine checks | repeat-offenders:9-20 | OUT-OF-SCOPE (S28b-3/-4) | task_plan.md:1019-1028. Only R9's and R10's PROSE halves are in scope (T2, T6). |
| Bugs-28b | bugs-28b:7 | NOTHING TO FIX | "No actionable regressions"; its scope defect is T8. |

**Counts (rows above):** OPEN 25 (T1-T13, T15-T19, T21-T22, T24, T26-T29; implemented as H1-H22) + 1 OPEN →
coordinator (PC-F8) · CONSTRAINT 1 (T14) · APPLIED 14 · PLAN-ONLY 7 (V7, V8, V18, V19, DE-F6, DE-F8, + V10/V12/DE-F3
plan halves → delta D1-D9) · OUT-OF-SCOPE 6 (V14b, T23, DE-F2, RO R1-R10, and the S28b-1 p2996 prose; PC plan items) ·
DEFERRED-LOW 2 (T20, T25) · UNVERIFIED 1 (DE-F3 regen).

## Coordinator actions (the implementer never posts to GitHub)

- **C1** #1422 comment (dismissed-28b:118-121): "#1423 CI arm owed: the first main promote after a PR merges BEHIND an image-input commit must print status=already_current and exit 0."
- **C2** #1432 comment (dismissed-28b:185-186): "cost: 4/5 lands on 2026-09-28b rebuilt, incl. two with no new :dev (land-itemC, land-docs)."
- **C3** #1434 comment (missing-requests:146-149,174-178): Renovate/Dependabot health evidence + SDLC finding-5 scope bullets.
- **C4** Persist `.agent/logs/codex-review-handoff-branch.log`'s final message verbatim as `docs/research/kb/reports/agents/codex-review-lens-p2996-branch-2026-09-28.md` (new path; include it in this PR).
- **C5** Run `mise run codex-schema-check`; if DRIFT, `mise run codex-schema-generate` (dismissed-28b:106-107). Unverified by the scribe.
- **C6** DONE 2026-09-28c: delta D1-D4, D6-D9 applied and the plan re-attested; D5 not applied (the `NEXT SESSION` token stays).

## 1. Objective

Make every OPEN FIX-NOW item from the seven 2026-09-28b §1c audits true in the repo's prose, and close the
handoff→resume drift class, so that a fresh session (or a codex lane) reading these docs is not handed a false fact:
the fake "Renovate bumps p2996" claim, the eager rule endorsing a broken `timeout`, colliding audit-report paths,
ambiguous brief letters, a bugs review that skips merged work, skills that contradict #1429, an unstated
goal-history heading format, and a handoff that can edit the plan after its last pointer check. Doc/skill/agent-prose
edits only — no Python, no config, no image input.

## 2. Files

Edit (authored sources only):

1. `.github/workflows/AGENTS.md` (H1)
2. `.github/workflows/refresh.yml` — comment lines only (H2)
3. `.claude/rules/long-running-command-hangs.md` (H3)
4. `.claude/agents/adversarial-critic.md`, `.claude/agents/staleness-auditor.md`, `.claude/agents/claude-code-expert.md`,
   `.claude/agents/codex-sol-adversarial-critic.md`, `.claude/agents/codex-sol-staleness-auditor.md`,
   `.claude/agents/codex-sol-claude-code-expert.md` (H4)
5. `.claude/agents/codex-sol-advisor.md`, `.codex/agents/codex-sol-advisor.toml` (H5)
6. `.claude/agents/codex-sol-implementer.md` (H6)
7. `.claude/skills/session-handoff/SKILL.md` (H7) and `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md` (H7b — Ray Q1)
8. `.claude/rules/goal-history.md` (H8)
9. `.claude/skills/verify/SKILL.md` (H10, H11, H12)
10. `CONTEXT.md` (H13), `AGENTS.md` (H14)
11. `.claude/skills/devcontainer-workflow/SKILL.md` (H15)
12. `.claude/skills/devcontainer-sync/SKILL.md` (H16)
13. `.claude/skills/pr-workflow/SKILL.md` (H17)
14. `tests/AGENTS.md` (H18)
15. `.claude/rules/gh-cli-watch.md` (H19)
16. `.claude/skills/codex-sdlc-team/SKILL.md` (H20)
18. `.claude/skills/pr-workflow/SKILL.md` (H23, in addition to H17), `.claude/skills/lock-image/SKILL.md` (H24), `.claude/skills/research-sweep/SKILL.md` (H25)
17. `docs/specs/p2996-ref-currency-review.md` (H21), `docs/specs/prompt-audit-C-apply.md` (H22)

Regenerate, never hand-edit: `.claude/agents/codex-astra-*.md` + `.codex/agents/codex-astra-advisor.toml`
(`mise run codex-lane-mirror`); `.agents/skills/{session-handoff,verify,devcontainer-workflow,devcontainer-sync,
pr-workflow,codex-sdlc-team}/SKILL.md` (`mise run skills-mirror`, incl. `lock-image` and `research-sweep` if mirrored).

Do NOT touch: `task_plan.md` (coordinator-only), anything under `docs/research/kb/reports/agents/` EXCEPT the Q-S briefs
file named in H7b (the 23d briefs file stays byte-identical), `.devcontainer/**`, `docker-bake.hcl`, `renovate.json`, `python/**`.

## 3. Interfaces (exact hunks; old → new)

Line numbers are from reads made this run; match on the quoted text, not the number.

**H1** `.github/workflows/AGENTS.md:18` — old: `` `CLANG_P2996_REF`: Renovate git-refs. `` → new:
`` `CLANG_P2996_REF`: NOT auto-bumped — Renovate's regex reads only the Dockerfile `ARG`, never bake's default (#1434). ``

**H2** `.github/workflows/refresh.yml:21-23` — old:
```
# retired with the snapshot itself (#160 T1); p2996-refresh was retired
# in favor of the Renovate git-refs manager, which bumps CLANG_P2996_REF
# in docker-bake.hcl + Dockerfile in lockstep.
```
new:
```
# retired with the snapshot itself (#160 T1); p2996-refresh was retired
# (#169) on the belief that a Renovate git-refs manager bumps
# CLANG_P2996_REF in docker-bake.hcl + Dockerfile in lockstep. FALSE: its
# regex matches only the Dockerfile ARG, never bake's HCL default (#1434).
```

**H3** `.claude/rules/long-running-command-hangs.md:50-51` — old:
```
   `date +%s`, or when command position wraps the loop with `timeout <n>` or
   `mise run bounded-wait`. A comment, `--connect-timeout`, path containing
```
new:
```
   `date +%s`, or when command position wraps the loop with `timeout <n>` or
   `mise run bounded-wait`. ⚠️ On this Mac host `timeout` is an unversioned mise
   shim that exits 1 ("No version is set for shim: timeout"): bound host commands
   with `bounded-wait` or a `SECONDS` deadline; `timeout <n>` only in-container or
   in CI. A comment, `--connect-timeout`, path containing
```

**H4** the six authored agent files in §2 item 4 — old (wrapping varies; `staleness-auditor.md:130-131` breaks after
"with"): `- **There is no `timeout` binary here.** Bound a slow command with `python3` and` / `` `subprocess(timeout=N)`. ``
→ new (re-wrap to the file's width):
```
- **`timeout` is not usable here.** On this Mac it resolves to a version-less mise
  shim that exits 1 (`No version is set for shim`). Bound a slow command with
  `python3` and `subprocess(timeout=N)`.
```

**H5** `codex-sol-advisor.md:4` — old: `The default advisor lane (codex gpt-5.6-sol); claude-advisor is escalation-only.` →
new: `A standing advisor lane (codex gpt-5.6-sol; its astra twin is equivalent, neither is the default); claude-advisor is escalation-only.`
`codex-sol-advisor.md:15` — old: `You are the default advisor lane:` → new: `You are a standing advisor lane:`.
`.codex/agents/codex-sol-advisor.toml:12` — old: `— the default advisor lane; claude-advisor is escalation-only."` →
new: `— a standing advisor lane (its astra twin is equivalent; neither is the default); claude-advisor is escalation-only."`
Keep the `#` header lines 1-10 of the TOML byte-identical (`codex-agent-parity` signal, `:7-10`).

**H6** `codex-sol-implementer.md:29-30` — old: `tens of minutes; 50 minutes has been observed. Exactly three signals mean the` →
new: `tens of minutes. Exactly three signals mean the`.

**H7** `.claude/skills/session-handoff/SKILL.md:116-119` — replace the paragraph with:
```
Before writing the handoff, run seven read-only reviews of THIS session, in parallel; a lane writes nothing but
its own report. Each lane CREATES one new file at
`docs/research/kb/reports/agents/session-audit-<kind>-<date>[letter].md`, using this session's handoff letter
(`.agent/plans/session-<date>[-letter].md`); when the un-suffixed path is already tracked the letter is
mandatory. Never `Write` over an existing report — a second same-day session overwrote two tracked audits on
2026-09-28.

Method briefs: `### Brief M`..`### Brief P` in `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md`
(that file's Briefs Q, R and S1-S4 are UNRELATED — ignore them), and the process-compliance, repeat-offenders and
retrieval-misses briefs in `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md`. Name a brief
by its review (the table's first column), never by letter. Reuse their METHOD only: substitute this session's id
and transcript path, its commit range (see the bugs row), today's date plus letter in the report path, and this
session's plan sections; never reuse a brief's SHA, session id or report path. Common to all seven: every finding
carries severity, claim, evidence (transcript ordinal or file:line), a control arm and a disposition, and every
report ends with `## GitHub repos touched`.
```
`:125` bugs row, Question cell — old: `cold review of the branch diff by ref (base = merge-base with `main`)` → new:
`cold review, by ref, of every commit this session authored: each squash SHA that landed on `main` this session plus the handoff branch's diff against its merge-base with `main`; skip a squash SHA only when the process-compliance review shows it already had the cross-family lens on that exact SHA`
`:128` repeat-offenders row — old: `so the disposition is a MACHINE check (guard rule, test, gate),` → new:
`so the disposition is a proposed MACHINE check (guard rule, test, gate — file plus rule/test text; the lane does not build it),`
`:129` retrieval-misses row — old: `name the file that should carry it and add it there` → new:
`name the ONE file that should carry it and give the exact line to add; the coordinator applies it as a FIX-NOW`

**H8** `.claude/rules/goal-history.md`, second paragraph — after the sentence ending "followed by the current goal text
and a Mermaid workflow." insert:
```
Each iteration opens with the heading `## YYYY-MM-DD — <title>`: a bare date, a space, an em dash. Session review
splits entries on `^## \d{4}-\d{2}-\d{2} — ` (`_GOAL_HISTORY_ENTRY` in `python/src/dotfiles_setup/session_review.py`),
so `## 2026-09-28b — …` silently merges that iteration into the previous one; put a session letter in the title.
```

**H9** — DONE in #1437 (the §5 final gate, attestation-based). Nothing to do.

**H10** `.claude/skills/verify/SKILL.md` — append after `:34` (end of the 2026-09-28 table) a new section:
```
## Recipe addition (2026-09-28c, handoff → resume round-trip)

| surface | drive it | expect |
|---|---|---|
| fresh session-resume | after `/session-handoff`: `claude -p "/session-resume" --allowedTools "Read,Glob,Grep,Bash(mise run session-state),Bash(mise run handoff-check *),Bash(mise run handoff-check),Bash(git log *),Bash(gh issue list *)" > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"` — never `--bare` (it skips skills; `$CC/headless.md:37`); a `/skill` in a `-p` prompt expands (`:312`) · control arm: `cp .plan-attestation "$S/att.bak"`, append `junk` to `.plan-attestation`, re-run, then `cp "$S/att.bak" .plan-attestation` (never `git checkout --`; the file is gitignored) | clean: `rc=0` and no line starting `DISAGREEMENT`; control: a `DISAGREEMENT` line naming `unattested_plan`; after the restore `mise run handoff-check` is rc=0 and `cmp` shows the attestation byte-identical |
```
Use the lowercase `claude -p`; do not write the capitalised product name in this row (the `.agents` mirror
rewrites it to "Codex", `skills_mirror.py:124-125`).

**H11** `verify/SKILL.md:26` — old: `(2026-09-28, sessions #1421/#1423/#1427/#1429)` → new: `(2026-09-28, PRs #1421/#1423/#1427/#1429)`.
`:31` — old `"session_id":"<fresh>"` → new `"session_id":"<a new uuidgen UUID>"`; old `twice · then `… graphify-hook-guard.sh read`` →
new `twice · then, with the SAME `session_id`, `… graphify-hook-guard.sh read``; old `first call ~314 bytes, factual, no `MANDATORY`` →
new `first call prints the factual nudge (no `MANDATORY`)`.

**H12** `verify/SKILL.md:33` — old `(`MISE_ENV=arm64` for arm64)` → new
`(arm64: `MISE_ENV=arm64` plus the gitignored `mise.arm64.local.toml` from `mise.local.toml.example`)`.

**H13** `CONTEXT.md:36` — old `` `ssh ${USER}@localhost -p 4444` opens a shell, no password. `` → new
`` `ssh ${USER}@localhost -p $(mise run ssh-port)` opens a shell, no password (port derived per workspace+arch, #677). ``
`CONTEXT.md:38` — old `` `aarch64`/`arm64` under `MISE_ENV=arm64`. Never the host's by passthrough. `` → new
`` `aarch64`/`arm64` under `MISE_ENV=arm64` with the gitignored `mise.arm64.local.toml` profile. It must come from the request, never from host passthrough (on an arm64 Mac, arm64 matches the host only because it was requested). ``

**H14** `AGENTS.md:166` — old `` `aarch64`/`arm64` via `MISE_ENV=arm64`) `` → new `` `aarch64`/`arm64` via `MISE_ENV=arm64` + its local profile) ``
(+22 chars; AGM-003 12,000-char cap — if `lint-docs` fails, drop H14 and report, do not trim elsewhere).

**H15** `devcontainer-workflow/SKILL.md:57-60` — replace the "One wart survives…" paragraph with:
```
The local `:dev` tag keeps every platform `mise run sync` has refreshed onto it (a union, #1429). Run
`mise run sync` once in an arch's env before that arch's first `verify-local`: sync treats a tag that lacks this
arch's platform as stale and refreshes it without dropping the other arch's layers.
```

**H16** `devcontainer-sync/SKILL.md` — after `:37` (end of the "Staleness = …" paragraph) insert:
```
Since #1429 the local tag is also stale when THIS arch's platform is absent under it. `--check` prints
`check: current` (rc 0), `check: STALE — sync would rebuild` or
`check: OUTDATED — sync would rebuild this architecture's container` (rc 1), or
`check: UNKNOWN — registry unreachable` (rc 2).
```
and after `:47` (end of "Then the verification gate…") insert:
```
Sync record: `~/.local/state/dotfiles/sync-<image ref, every char outside [A-Za-z0-9._-] → _>.json`, keys
`registry_digest`, `local_image_id`, `containers` = `{"<workspace-hash>:<arch>": "<overlay image id>"}`; written by
`write_sync_record` after a converge (#1432: recorded ids can outlive their images).
```

**H17** `pr-workflow/SKILL.md:35` — old: ``pytest → `dotfiles-setup verify run` → `hook-selfcheck` (always-run:`` → new:
``pytest → `dotfiles-setup verify run` → hook selfcheck (`uv run --project python dotfiles-setup hook selfcheck`, NOT a mise task; always-run:``

**H18** `tests/AGENTS.md` — new bullet immediately after the `Subprocess usage` bullet (starts `:110`):
`- A test may shell out only to a tool pinned in `.config/mise/conf.d/shared.toml` (host, image and CI all install it, e.g. `jq`); any other binary gives a Mac-only pass.`

**H19** `.claude/rules/gh-cli-watch.md` § Canonical patterns — after the line
`gh pr checks 123 --json name,bucket  # one-shot read of PR checks` insert:
`gh issue view 123 --json title,body,comments  # never --comments: exclusive with --json, and non-TTY it prints ONLY comments`

**H20** `codex-sdlc-team/SKILL.md:18` — after the bullet `- A `.codex/agents/*.toml` file is about to be written or edited.` add:
```
  `.codex/agents/` also holds gitignored Codex-app exports of `.claude/agents` definitions (#1425): `git grep`
  cannot see them, so sweep a phrase with `grep -rF` over the directory.
```

**H21** `docs/specs/p2996-ref-currency-review.md` — insert after the title line:
`**Status: EXECUTED 2026-09-28** — report `docs/research/kb/reports/agents/sdlc-team-p2996-ref-currency-2026-09-28.md`; Ray's rulings and the fix PR live in `task_plan.md` (S28b-1). Do not re-dispatch.`
`:33` — old `- A p2996 bump triggers a base-image rebuild (~2.5 h cold in CI); weigh update cadence against that cost.` → new
`- ~~A p2996 bump triggers a base-image rebuild (~2.5 h cold in CI)~~ — refuted by the review: it invalidates the compiler and final-image tiers only; weigh cadence against that cost.`

**H7b** `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md` (Ray Q1: "Edit the Q-S file too") —
retitle `## Brief Q — process compliance` → `## Brief Q (process compliance)`, `## Brief R — repeat offenders` →
`## Brief R (repeat offenders)`, `## Brief S — retrieval misses` → `## Brief S (retrieval misses)`; after the title
line insert: `Not the Briefs Q, R or S1-S4 of \`session-2026-09-23d-agent-briefs.md\` — address these by review name.`;
in the intro paragraph change `session-audit-<kind>-<date>.md` → `session-audit-<kind>-<date>[letter].md (this
session's handoff letter; never Write over an existing report)`; and append to the intro one sentence carrying the
common finding contract from H7 ("every finding carries severity, claim, evidence (transcript ordinal or file:line), a
control arm and a disposition").

**H23** `.claude/skills/pr-workflow/SKILL.md` — after the sentence ending "ship prints the `mise run land`
follow-up for post-merge Mac validation." (`:61-62`) add: `Its success line is \`ship: OK — PR #<n> open, local gates
green, AUTO-MERGE enabled.\` (\`pr.py:612\`); land's is \`land: OK — PR #<n> merged, main green, Mac synced\`
(\`pr.py:910\`). Capture <n> with \`grep -oE 'PR #[0-9]+' <log> | tail -1\`.` Re-grep both literals in `pr.py` first;
if either moved or changed, quote the current text.

**H24** `.claude/skills/lock-image/SKILL.md` — add (place under its existing gotchas/notes section):
`Per-platform lock entries are TOML tables \`[tools.<tool>."platforms.linux-x64"]\` / \`[tools.<tool>."platforms.linux-arm64"]\`
(e.g. \`.devcontainer/mise-system.lock\`); count coverage with \`grep -c '^\\[tools\\..*"platforms\\.linux-arm64"\\]' <lock>\`.`
Run that grep once against `.devcontainer/mise-system.lock` and state the count you got in your report (non-zero).
Drop the report's conda clause unless you find a `[conda-packages.` table in a tracked lock.

**H25** `.claude/skills/research-sweep/SKILL.md` — add: `A workflow run's
\`subagents/workflows/<wf>/journal.jsonl\` has no model field; the model each node ran on is \`message.model\` in
that directory's \`agent-*.jsonl\`.`

**H22** `docs/specs/prompt-audit-C-apply.md` — in §5 (`:80` region) replace each `grep -rlF '<phrase>'` with
`git grep -lF '<phrase>' -- .claude/agents .codex/agents` and add one line: "TRACKED files only; the gitignored
Codex-app exports are #1425 and still hit a plain `grep -r`." `:110` — old `a single-source refactor, planned separately.` → new
`a single-source refactor, planned separately (task_plan.md S28b-4, R5 ruling).`

## 4. Constraints and invariants

- **Budgets** (`md-size-budgets.md`): eager rules (`long-running-command-hangs`, `goal-history`, `gh-cli-watch`) ≤ 200
  lines / 24,000 B; skills ≤ 500 lines / 32,000 B; every `AGENTS.md` (root, `.github/workflows/`, `tests/`) under
  agnix AGM-003's 12,000 chars — root is within ~500 chars (`.claude/CLAUDE.md` intro paragraph; premise A6). Net growth on AGENTS.md files
  must stay minimal; if `lint-docs` fails on one, drop that hunk and report it rather than trimming unrelated text.
- **Mirrors**: never hand-edit `codex-astra-*` (run `mise run codex-lane-mirror`) or `.agents/skills/**` (run
  `mise run skills-mirror`). Do not change the `session-handoff` sentences `PER_FILE` matches
  (`skills_mirror.py:163-182`).
- **Codex TOML**: before editing `.codex/agents/codex-sol-advisor.toml` follow the `codex-schema` skill pre-flight
  (codex drops an invalid agent file silently); keep header lines 1-10 byte-identical.
- `claude_md_import_stub`: root `CLAUDE.md` untouched. Zero-bash-logic: no scripts added. `task_plan.md` untouched.
- No file under `docs/research/kb/reports/agents/` is modified; C4's new file is the coordinator's.
- A `.github/**` comment edit still needs `mise run pin-actions` (verify-before-advancing table).
- Rule edits change content only; `rule-sync` binds rule STEMS (`rule-sync.toml:51-56`), so no KB PR.

## 5. Verification

Each command to a file with `; echo "rc=$?" >> <log>`; read the recorded rc.

1. `mise run codex-lane-mirror` then `mise run codex-lane-mirror -- --check` → rc=0.
2. `mise run skills-mirror` then `uv run --project python dotfiles-setup skills-mirror --check` → rc=0.
3. `mise run codex-agent-parity` → rc=0 (A5: task name taken from the TOML header comment, not `mise tasks ls`).
4. Presence/absence arms (each paired with a control on a string known present): `git grep -n "Renovate git-refs"
   -- .github` → 0 hits; `git grep -n "no \`timeout\` binary" -- .claude .codex` → 0; `git grep -n "default advisor lane"
   -- .claude/agents .codex/agents` → 0; `git grep -n "holds ONE platform" -- .claude .agents` → 0;
   `git grep -n "session-audit-<kind>-<date>.md" -- .claude .agents` → 0; `git grep -n "50 minutes has been observed"` → 0.
5. `mise run pin-actions` (refresh.yml touched).
6. `mise run lint` → rc=0 (hk: `md_size_budget`, `doc_refs`, typos, `skills_mirror_parity`, …).
7. `mise run lint-docs` → rc=0 (agnix, incl. AGM-003).
8. `uv run --project python pytest tests/ -x -q` → pass (doc-contract tests, e.g. skills-mirror and orchestration contracts).
9. `mise run verify` → 0 failed.
10. H10 live arm (coordinator, after merge or on the branch): run the new recipe row both arms once and record rc.
11. `git grep -n "Brief Q (process compliance)" -- docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md` → 1
    hit; `git diff --stat -- docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md` → empty.

`mise run rule-sync` is NOT required (no `.claude/CLAUDE.md`, `settings.json` or `rule-sync.toml` change).

## 6. Commit

Caller commits (the coordinator / `mise run ship`). The implementer does not commit, push,
or post to GitHub.

## 7. PREMISES

| # | Kind | Claim | Cited from (read this run) |
|---|---|---|---|
| L1 | L | Active phase = last `##` heading containing `NEXT SESSION` | `python/src/dotfiles_setup/handoff_check.py` `active_phase` (moved there by #1437) |
| L2 | L | handoff-check flags `unattested_plan` when the root plan no longer matches pwf's attestation | `handoff_check.py` `_plan_findings` (#1437) |
| L4 | L | `task_plan.md` is gitignored | `.gitignore:143` |
| L5 | L | goal-history entry regex `^## (?P<title>\d{4}-\d{2}-\d{2} — [^\n]+)\n` | `python/src/dotfiles_setup/session_review.py:141` |
| L6 | L | Guard accepts `timeout <n>` as a loop bound | `python/src/dotfiles_setup/hook_guard.py:196-198,243` |
| L7 | L | `sync --check` literals and rc 0/1/2 | `python/src/dotfiles_setup/sync.py:879-891` |
| L8 | L | Sync record path + `containers` key | `sync.py:275,278-280,323` |
| L9 | L | Missing platform ⇒ stale (#1429) | `sync.py:156-168` |
| L10 | L | Rule-sync binds stems, not content | `rule-sync.toml:51-56,64,66` |
| I1 | I | `.agents/skills/**` generated by `skills-mirror`, gated by `skills_mirror_parity` | `skills_mirror.py:2-18,354-383`; `hk.pkl:722-723` |
| I2 | I | Mirror rewrites `Claude`→`Codex`; `PER_FILE["session-handoff"]` must keep matching | `skills_mirror.py:122-136,163-182,386-421` |
| I3 | I | astra lanes (md + toml) generated from sol by `codex-lane-mirror` | `python/src/dotfiles_setup/codex_lane_mirror.py:2,29-33,77-91`; `mise.toml:1369-1372` |
| I4 | I | Skills expand in `claude -p`; `--bare` skips skills; non-bare runs project hooks; `--allowedTools` prefix syntax; rc semantics | `knowledge-base/sources/agent-harness-docs/docs/claude-code/headless.md:312,37,41,309,33` |
| I5 | I | session-resume must print `DISAGREEMENT:` when reality contradicts | `.claude/skills/session-resume/SKILL.md:84,94` |
| P1 | P | Current §1c/§6/checklist text that H7/H9 replace | `.claude/skills/session-handoff/SKILL.md:116-129,288-300,307,320,322`; mirror `.agents/…:116-135,288-322` |
| P2 | P | Iteration 042 exists with a bare-date heading | `docs/agents/goal-history.md:1858-1860` |
| P3 | P | Old texts for H1-H6, H11-H17, H21-H22 | `.github/workflows/AGENTS.md:18`; `refresh.yml:20-23`; `long-running-command-hangs.md:48-54`; agent grep lines (T3); `codex-sol-advisor.md:4,15`; `codex-sol-advisor.toml:1-12`; `codex-sol-implementer.md:29-30`; `verify/SKILL.md:26,31,33`; `CONTEXT.md:36,38`; `AGENTS.md:166`; `devcontainer-workflow/SKILL.md:57-60`; `devcontainer-sync/SKILL.md:25,34-47,59-60`; `pr-workflow/SKILL.md:35`; `codex-sdlc-team/SKILL.md:18`; `p2996-ref-currency-review.md:3,33`; `prompt-audit-C-apply.md:80,110` |
| P4 | P | Profile facts for H12-H14 | `mise.local.toml.example:35-47` |
| A1 | A | `--allowedTools "Bash(mise run handoff-check)"` (no-arg form) matches the bare command; and session-resume's step 4 question does not stall a `-p` run. Not verifiable from docs read; H10's first live arm settles it. | — |
| A2 | A | The S28-4 graph rebuild really happened (task_plan says so; scribe had no Bash to run `graphify-health`). | task_plan.md:1180 (a claim, not a probe) |
| A3 | A | The p2996 review refuted the "~2.5 h base rebuild" premise (compiler/final tiers only). Taken from vagueness:135-142; the scribe did not re-read `sdlc-team-p2996…md:141-144`. Implementer: read it before H21. | — |
| A4 | A | `gh issue view --comments` is exclusive with `--json` and non-TTY prints only comments (H19). From retrieval-misses:48; not re-probed. Implementer: run `gh issue view --help` and one arm before H19, or drop H19. | — |
| A5 | A | `mise run codex-agent-parity` is a real task (named only in `codex-sol-advisor.toml:7`). | — |
| A6 | A | Root `AGENTS.md` is ~500 chars under 12,000 (stated in `.claude/CLAUDE.md`, loaded as instructions; byte count not measured). | — |
| A7 | A | `claude` on PATH is the intended CLI for H10 (no mise pin was checked; `ai-cli-invocation.md` lists codex/agy/opencode only). | — |

## Rulings (Ray, 2026-09-28c)

- Q1: edit the Q-S briefs file too (H7b). Q2: moot — the pointer is deleted (#1437). Q3: the `timeout` caveat (H3)
  stands; the guard change is S28b-4. Q4: S7/S13/S14 IN (H23-H25), literals verified. Q5: moot — no pointer; the
  `NEXT SESSION` token stays because `handoff_check.active_phase` still reads it.
