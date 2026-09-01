# SPEC — file the implementation issue for the R1/R2 process-enforcement design

## 1. Objective

A researched design exists for two standing operator requirements. It is
committed as a report but has no ticket, so it will be forgotten. File one
GitHub issue that a future session can pick up and implement without re-deriving
the research.

The failure this prevents: the design's most important content is what it rules
OUT. An implementer who reads only a summary will rebuild the thing the research
already proved impossible, or ship the row-existence gate the report explicitly
calls theatre.

## 2. Read first

    docs/research/kb/reports/agents/2026-09-01-process-enforcement-design.md

369 lines, on the current branch. Read it in full before writing. Do not
paraphrase from this spec — this spec is a pointer and a set of guardrails, the
report is the source.

## 3. What the issue must carry

**The two requirements**, in the operator's own framing:

  R1 — anything a codex lane works on is ALWAYS recorded in the
       planning-with-files task plan (`task_plan.md`), so it cannot be lost.
  R2 — anything needing the operator's answer is ALWAYS surfaced to them as a
       usable prompt, never buried in prose or silently guessed.

**The two harness facts that constrain any implementation.** Both were verified
against the vendor's offline docs; cite them as the report does, and re-check
them yourself before writing:

  - Parent-configured hooks DO fire for subagent tool calls, and the payload
    carries `agent_id` and `agent_type` (`hooks.md:265`). Lane work is therefore
    observable with lane identity attached.
  - `AskUserQuestion` is removed from EVERY subagent, even when named in the
    `tools` field (`sub-agents.md`, the first-filter list). A lane structurally
    cannot ask the operator anything, so the parent session must carry every
    surfacing.

**The verdicts, stated as verdicts, not aspirations:**

  - R1 is PARTIALLY enforceable.
  - R2 is NOT enforceable as literally stated.

The issue must say this plainly at the top. An issue that reads as "implement
full enforcement of R1 and R2" misrepresents the research and sets an
implementer up to fail.

**What is explicitly rejected**, so nobody rebuilds it: a gate that merely
verifies a task-plan row EXISTS and is described as guaranteeing the plan is
accurate and current. The report calls this theatre. Carry that judgement and
its reasoning.

**Acceptance criteria** an implementer can check, derived from the report — not
invented here. Include, for each proposed mechanism, its concrete bypass path, so
the implementer knows what it does not buy.

## 4. Constraints on the issue itself

- One issue, not two. R1 and R2 share a mechanism surface and the report treats
  them together.
- Label it consistently with #888/#889 (see `docs/triage-labels.md` for the
  repo's scheme; pick what actually fits rather than copying blindly).
- Reference the report by repo path AND note it is on branch
  `docs/advisor-graph-impact-gate` at the time of filing, since that branch may
  not have merged yet.
- Cross-reference #888 if there is a genuine relationship; do not manufacture
  one.
- Do not restate the whole report. Link it, carry the verdicts, the two harness
  facts, the rejected approach, and the acceptance criteria. A reader should
  know within thirty seconds what is and is not achievable.

## 5. Also record it in the task plan

Add the issue number to the existing Phase 13 in `task_plan.md` (repo root,
gitignored) alongside #888 and #889, one line on what it is. Do not create a new
phase and do not renumber anything.

## 6. Verification

    gh issue view <n> --json number,title,state,labels
    git status --porcelain     # must be EMPTY — task_plan.md is gitignored
    mise run lint              # rc=0

Paste the rendered issue body into your report.

## 7. Commit

COMMIT: caller — make NO commit and create NO branch.

⚠️ A `mise run ship` may be running in this checkout concurrently. Do not run any
git write operation: no commit, no branch, no checkout, no push, no stash. Your
only writes are `gh issue create` and an edit to the gitignored `task_plan.md`.

## 8. PREMISES

- L1 `docs/research/kb/reports/agents/2026-09-01-process-enforcement-design.md` exists at 369 lines and is committed as `8102e52` on branch `docs/advisor-graph-impact-gate` — verified by me this session.
- L2 `hooks.md:265` in the offline vendor docs states that hooks from settings, managed policy and plugins run inside subagents, that `PreToolUse`/`PostToolUse` fire the same configured hooks as in the main conversation, and that the input carries `agent_id` and `agent_type` — read by me this session at `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md`. Control arm: `PreToolUse` occurs 68 times in that file.
- L3 `sub-agents.md` in the same tree lists `AskUserQuestion` among the tools removed from every subagent "even when listed in the `tools` field", alongside `EndConversation`, `EnterPlanMode`, `ScheduleWakeup`, `TaskOutput` and `Workflow`; forks skip both filters — read by me this session.
- L4 Issues #888 (branch-protection bypass) and #889 (graphify community-id determinism) are OPEN and recorded in `task_plan.md` Phase 13 — filed this session.
- L5 `task_plan.md` is at the repo root, gitignored, and its phase headings follow `## Phase N — <name> — **STATUS**` — read this session.
- A1 ASSUMPTION: `docs/triage-labels.md` documents the repo's label scheme and the labels used on #888/#889 come from it. Held without reading that file; check it before choosing labels, and if the scheme differs from what #888/#889 used, follow the file and say so.
