# Standards review — 07221b46 (s28b-0 FIX-NOW sweep)

Scope: `git diff 07221b46~1...07221b46`, generated mirrors excluded. Literal claims probed and all CONFIRMED:
`pr.py:612`/`:910` success lines; `sync.py:879-890` `--check` strings, `_state_file` sanitiser (`:279`),
`write_sync_record` (`:323`); `_GOAL_HISTORY_ENTRY` (`session_review.py:141`); lock grep → 46 arm64 / 46 x64 /
0 for a bogus platform; `jq = "1.8.2"` in `shared.toml:38`; workflow `agent-*.jsonl` 1616 hits beside `journal.jsonl`.

## Hard violations

1. **Tracked docs cite a gitignored file.** `docs/specs/p2996-ref-currency-review.md:3` — "Ray's rulings and the fix PR
   live in `task_plan.md`"; `docs/specs/prompt-audit-C-apply.md:111` — "(task_plan.md S28b-4, R5 ruling)".
   `git check-ignore task_plan.md` rc=0 (control: `AGENTS.md` tracked rc=0). Breaks
   `agent-artifact-conventions.md` § Tracked: "A citation that only one machine can open is not durable evidence."
   Cite an issue/PR number instead.

## Judgement calls

2. **Verbatim tree edited** — `session-handoff-briefs-q-s-2026-09-28.md` (headings `— ` → `( )`, path, contract).
   Ray-sanctioned (spec Q1/H7b), so not a violation, but it collides with `agent-report-persistence.md` rule 4 and
   `agent-artifact-conventions.md` rule 8, and the file carries no "amended 2026-09-28c" marker: a reader cannot
   tell it is no longer what the 2026-09-28b lanes received.
3. **Duplicated Code / Shotgun Surgery** — the `timeout` caveat now lives in 9 `.claude/agents` files plus
   `long-running-command-hangs.md`; the finding contract ("severity, claim, evidence … control arm and a
   disposition") is in both SKILL §1c and the Q-S briefs file. Known (S28b-4) but grew here.
4. **Divergent guidance** — agents say bound with `python3 subprocess(timeout=N)`; the rule says `bounded-wait` or a
   `SECONDS` deadline. `mise-tasks-only.md` makes `bounded-wait` canonical; the agent line should point at it.
5. **Mysterious Name** — root cause of the brief muddle is two files both lettering Q/R/S; the fix adds "never by
   letter" prose while keeping the letters. `verify/SKILL.md` recipe uses undefined `$S` (and `$LOG`).
6. **Misfiled facts (Feature Envy)** — the `.codex/agents` gitignored-exports note is nested under a "when it applies"
   trigger bullet in `codex-sdlc-team/SKILL.md`; the workflow-journal model-field fact sits in `research-sweep`,
   which doesn't run workflows.
7. **Rot-prone anchors** — `pr.py:612`/`:910` in `pr-workflow/SKILL.md`; the quoted strings suffice.
8. `AGENTS.md` R3 "+ its local profile" is vague next to CONTEXT.md's named `mise.arm64.local.toml` (size-driven).

## GitHub repos touched

_None._
