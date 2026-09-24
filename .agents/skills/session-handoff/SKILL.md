---
name: session-handoff
description: "Prepare for a /clear: reconcile the active plan, bring documentation up to date, persist recovery evidence, and emit the canonical /session-resume prompt. Invoke explicitly as /session-handoff, or on your own judgment when context is getting full and a clean handoff would protect against losing work."
disable-model-invocation: false
---

# Session-Handoff — Before `/clear`

Run this **before** `/clear` to (1) make every doc reflect the latest changes,
(2) persist recovery context that survives the clear, and (3) print a resume
prompt to paste after `/clear`. `task_plan.md` is the sole task authority;
memory and the handoff carry evidence, traps, and state, never task prose.

Work top-to-bottom. Do not skip the validation gate. Keep the final resume
prompt short — durable detail lives in memory + the handoff, not the prompt.

## 0. Resolve active-plan ambiguity FIRST — mandatory (Ray, 2026-07-08)

Before writing the handoff, inspect the active phase in `task_plan.md`. When
its scope, order, owner, end state, or a material choice is ambiguous, ask the
user clarifying questions (`AskUserQuestion`) across as many rounds as needed.
Record every ruling in `task_plan.md` only. Do not copy or paraphrase the
active phase into memory or the handoff.

**Then double-check nothing will be lost by `/clear`** (see step 3c + the
final checklist): every findings-bearing agent/research report is on disk,
every non-task decision and open question is in the handoff, and the plan +
memory + handoff + research artifacts reconstruct the full working context.
If that set has a gap, fix it before emitting the resume prompt.

## 1. Snapshot the working state

Gather, don't guess:

```bash
git status --short
git branch --show-current
git log --oneline -8
gh pr list --head "$(git branch --show-current)" --json number,title,state 2>/dev/null
```

Note: current branch, staged/unstaged/untracked files, open PR + its CI state
(`gh pr checks <n> --json name,state`), and any in-flight process or owed
evidence from the prior `.agent/plans/session-*.md`.

Refresh the tracked identity of the authoritative plan after step 0:

```bash
mise run plan-pointer
```

This writes only the plan SHA-256, active phase heading, and timestamp to
`docs/agents/plan-pointer.json`; it never copies the phase body.

Also inventory **session runtime state**: in-flight background tasks/agents
and any scheduled wakeups or crons created this session. Stop what should not
outlive the session; note anything intentionally left running in the handoff.
A stale wakeup firing after handoff re-triggers work that is already done
(observed 2026-07-05).

A process belongs to this session only if its `ppid` chain reaches THIS
session's `claude` pid — enumerate by that chain and exclude nothing. The
harness runs its own background tasks as `/bin/zsh -c source …snapshot-zsh…`,
so any exclusion filter hides exactly the category you are looking for; the
same chain proves a foreign `codex exec` (e.g. one under `ChatGPT.app`) is not
yours and must not be killed. Prefer the harness's background run and its
completion notification over any hand-rolled wait; when a wait is genuinely
needed, use `mise run bounded-wait` with its required deadline — a
file-existence wait whose producer was killed never finishes.

Run the descendant census instead of reimplementing the ancestry walk:

```bash
mise run session-orphans
```

At handoff, every session-local wait loop is an orphan whether its predicate is
bounded or unbounded; `session-orphans` intentionally classifies both. The dry
run labels each `WAIT-LOOP` as `bounded` or `unbounded` and groups a typed,
directly owned sleep as its `WAIT-LOOP child`; `--kill` reaps both. A typed
harness shape is `HARNESS` only when its parent requirement also matches; those
rows neither block nor receive signals. Every remaining `OTHER` row blocks
handoff until stopped or explicitly named with `--allow` — never `--allow` a
healthy harness row merely to make the census pass.

**Distinguish session-LOCAL state from session-INDEPENDENT autonomous
processes, and do not block `/clear` on the latter.** Running GHA runs and bots
like **Renovate** execute on GitHub whether or not this session exists, and an
active bot means `main` never goes quiet: each merge triggers its promote run
and the next queued PR. Correct handling: **INVENTORY** in-flight autonomous PRs / CI runs in the
handoff (number, what each is, expected outcome, any that are legitimately
failing and why), pin the handoff to the current HEAD, note that `main` is
bot-advanced and the next session just `git pull`s the latest — then `/clear`.
Do not idle waiting for a quiescent `main` that an active bot will never
produce. (Only wait on a GHA run if YOU need its result to finish THIS
session's active work — e.g. a merge you must confirm landed.)

### 1b. AgentsView session-integrity pass

Run the named deterministic census:

```bash
mise run session-agentsview-pass
```

It reads the remote-daemon flags from the installed AgentsView skill, inspects
this project's current and two prior Claude sessions, and reports unbounded
wait ordinals, `AskUserQuestion` count, handoff-skill position relative to the
first commit, and report writes under `docs/research/kb/reports/agents/`.
A daemon failure is `UNVERIFIABLE`, never zero findings. Any unbounded wait or
out-of-order evidence is a finding that must be dispositioned before drafting
the handoff.

### 1c. Session-integrity review — nothing dismissed, missing, broken or vague (Ray, 2026-09-23)

Before writing the handoff, run four read-only reviews of THIS session, in parallel, each persisting its
report under `docs/research/kb/reports/agents/session-audit-<kind>-<date>.md`. Their briefs from the first run
are "Briefs M-P" in `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md`; reuse them.

| Review | Question | Lane |
|---|---|---|
| dismissed errors | every non-zero rc, error, WARN, denied call, DRIFT line and repeated mistake: fixed, recorded in `task_plan.md`, or dismissed? | Opus `general-purpose` |
| missing requests | every user message and AskUserQuestion answer: does it land in `task_plan.md`, an issue, a commit or memory? | Opus `general-purpose` |
| bugs | cold review of the branch diff by ref (base = merge-base with `main`) | a model family different from the diff's AUTHOR (not the orchestrator): an Anthropic-authored diff gets the read-only codex review lens, a codex-authored diff gets an Opus `cold-reviewer`; the exact command lives in `.agents/skills/codex-sdlc-team/SKILL.md` § Review tiers. |
| vagueness | every doc, plan, spec, rule or agent file the session changed, read as a fresh session or a codex lane would: stale, ambiguous, contradictory, unowned | Opus `general-purpose` |

Every finding gets a disposition: **FIX-NOW** (make the change before §2) or **PLAN** (exact `task_plan.md`
text; mark it "needs `/grilling` → `/to-spec` → `/to-tickets`" when a design decision is open, and ask Ray
through AskUserQuestion when a ruling is needed). The handoff may not be written while any finding is neither
fixed nor planned. A codex lane's "timed out"/"empty" report is not a result: check its process and output file
first (memory `feedback_haiku_lane_wrapper_abandons_codex_and_self_implements`).

## 2. Documentation sync — make docs match reality

For everything changed this session (uncommitted **and** recent commits not yet
reflected in docs), find and update every affected doc. Walk these in order:

1. **Directory docs.** For each touched directory, update its `AGENTS.md`
   Root
   `AGENTS.md` for cross-cutting changes (pipeline shape, build types, tasks).
2. **Cross-references.** Grep for anything renamed, moved, deleted, or
   re-timed and fix every hit:
   ```bash
   git grep -nE "<old-filename>|<old-command>|<old-cron>|<renamed-symbol>" \
     -- ':!*.lock'
   ```
   Common sources: workflow/file renames, mise task names/descriptions,
   CLI command names, cron timings, env-var names, moved docs.
3. **Spec / design docs** under `docs/` — update status banners and phased
   checklists; keep point-in-time analysis legible (mark the old state as
   baseline rather than rewriting the reasoning). Add any newly-consulted
   repos to a `## GitHub repos touched` section
   (`.claude/rules/research-repo-enumeration.md`).
4. **Issue / epic checklists** on GitHub — tick boxes, file follow-ups,
   cross-link (`gh issue edit`, `gh issue comment`). **On a self-triggered
   run**, step 4's review gate applies to these two verbs before you run
   them here — do not mutate GitHub while still walking this list; queue the
   edits and post them after that gate clears.
5. **Doc-ref integrity — machine-gated; do NOT hand-roll a grep sweep.**
   Stale refs predating the session escape the diff-scoped greps above (a
   deleted file's mentions can linger for months — the `home/AGENTS.md` case,
   deleted in PR #80, found 2026-07-05). That sweep is now the **`doc_refs`
   hk step** (`dotfiles-setup check-doc-refs`, logic in
   `python/src/dotfiles_setup/doc_refs.py`, pinned by `tests/test_doc_refs.py`),
   so `mise run lint` already covers it — nothing extra to run here.

   The checker's `_ALLOWED_ABSENT` list justifies each legitimately external
   reference (container paths, gitignored artifacts, out-of-repo memory
   files, illustrative examples); a basename-level grep loop reports mostly
   noise, so do not hand-roll one. If `mise run lint` is green, doc refs are
   clean. When the gate fires, judge the hit — fix the ref (preferred) or add
   a justified `_ALLOWED_ABSENT` entry. Widening the checker's scope is a
   `DOC_PATHSPECS` change plus a coverage assertion in `tests/test_doc_refs.py`.

**Constraints (machine-enforced — respect or the gate fails):**
- Markdown size is **class-aware** — see `.claude/rules/md-size-budgets.md`
  for the table (hk step **`md_size_budget`**, which replaced the retired
  `claude_md_size_limit`). An `AGENTS.md` additionally carries agnix
  AGM-003's 12,000-char cap — **Windsurf's rule, not Anthropic's** — which
  binds first. Do NOT restate a flat "200-line / 12,000-char" limit: that
  misattribution is exactly what `md-size-budgets.md` exists to kill.
  Verify with `mise run lint` + `mise run lint-docs`; when a file sits near
  a limit, record in the handoff which future edit must trim. Any
  addition needs an offsetting trim — prefer collapsing duplication to a
  pointer (rule files / `action.yml` / other docs are the authority) over
  deleting load-bearing facts. Long single-line table rows are more
  line-efficient than wrapped prose.
- Project docs/rules/cross-refs point to `AGENTS.md` directly — there is no `CLAUDE.md` layer
  to route through on this side (`feedback_refer_to_claude_md_not_agents_md`
  describes the `.claude`-side convention this inverts).
- Follow `.claude/rules/` (zero-skip, ci-local-parity, use-tool-builtins).

## 3. Persist recovery context — two layers

Both, every time. They cover different recovery surfaces.

### a. Durable memory (survives `/clear` AND fresh clones; auto-loaded each session)

Write or update a `project_*` (or `feedback_*`) file under
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/`
with frontmatter (`name`, `description`, `metadata.type`). Record: what
shipped, locked decisions, evidence pointers, and any non-obvious gotcha.
Memory may cite the plan path and digest but must not restate its task text.
Convert relative dates to absolute. Add a one-line
pointer to `MEMORY.md` (`- [Title](file.md) — hook`). Update an existing
file rather than duplicating; delete memories proven wrong.

### b. Local handoff (survives `/clear`; gitignored, this-clone-only)

Write `.agent/plans/session-<YYYY-MM-DD>[-letter].md`
(`.claude/rules/agent-artifact-conventions.md` — handoffs are plans). The
handoff must be self-sufficient for recovery evidence while leaving task
authority in `task_plan.md`. Include **State at handoff** (branch/PR/merge
state, gate results), **what shipped**, the plan path and SHA-256 from
`docs/agents/plan-pointer.json`, evidence/preload pointers, owed non-task
obligations, open decisions, and **gotchas**. Do not copy a plan phase,
directive, or task description. If a prior handoff exists for today, append a
letter suffix rather than overwriting.

### c. Research artifacts — verbatim, receipt-time (audit coverage here)

Full subagent reports must already be on disk per
`.claude/rules/agent-report-persistence.md`: every findings-bearing agent's
final report persisted VERBATIM under `docs/research/kb/reports/agents/` at the
moment it was received — condensed notepad summaries do NOT count. At
session-handoff, audit coverage: enumerate every agent launched
this session; each findings-bearing one must map **both its brief (the prompt
handed TO it) and its report** to an artifact file (or an explicit N/A in the
handoff). Anything missing: write it now, verbatim from context, before
`/clear` destroys the only copy. Briefs are in scope because a report without
its brief has lost the question that produced it.

Every report written this session also needs an inbound pointer from the
handoff **and** from the rule or skill whose behavior it governs. If no such
consumer exists, record the report as deliberately orphaned in the handoff.

## 4. Validate, then commit doc changes

Run only the gates relevant to what changed; all must exit 0 before committing:

```bash
mise run pin-actions                            # only if .github/ touched
mise run lint                                   # always (timeout-wrapped hk)
uv run --project python pytest tests/ -x -q     # if python/ or tests/ touched
dotfiles-setup verify run                       # if .devcontainer/ or contracts touched
```

Stage specific paths (never `git add .` — phantom `.agent/state/**` files;
`.claude/rules/do-not.md`). Commit doc updates with the standard trailers.
The handoff (`.agent/plans/`) is gitignored and memory lives outside the repo —
neither is committed. If on `main`, branch first; open a PR only if the user
asks.

**When this run started on your own judgment rather than an explicit
`/session-handoff` from the user** (per the description's "or on your own
judgment when context is getting full"): before running `git commit` or any
`gh issue edit`/`gh issue comment`, dispatch a read-only cold-review pass
(a subagent, `model: "opus"`) over the exact staged diff and the exact issue
comment text you're about to post. If it flags anything material — content
that looks wrong, unrelated, or bigger than a doc-sync should be — stop and
surface it to the user instead of committing/posting unattended. This
review-gate is scoped to self-triggered runs only; when the user typed
`/session-handoff` themselves, that invocation IS the consent and no extra
gate applies. (Ray, 2026-08-29 — the auto-invocation carve-out for this
skill's own memory writes at step 3a, and this review gate for its
commit/issue-edit steps, are the two conditions that make automatic
invocation safe: memory writes are the whole point of the feature and are
covered by the same approval that enabled auto-invocation; commits and
issue edits are outward-facing and get a review pass instead.)

## 5. Self-verify the handoff — claims must match reality

The handoff is written by paraphrase; wrong details cost the next session
more than missing ones. Run the single checker against the exact handoff:

```bash
mise run handoff-check -- .agent/plans/session-<YYYY-MM-DD>[-letter].md
```

Resolve every finding. The checker validates cited paths/lines and mise tasks,
forbids a second task carrier, requires an active plan, and verifies the tracked
plan pointer. Also confirm gate results against recorded exit codes, not memory.

## 6. Emit the resume prompt — exact output

Print exactly this single line and nothing else (an owed attest prompt, below, is the one thing that may precede it):

```text
Run /session-resume
```

If an attestation is owed (the plan changed and the model may not attest), put the `! mise run plan-attest` prompt
**before** that line, and only after `mise run session-orphans` shows no live wait loops or lanes and no background
agent, codex lane or harness task is still running, so the attestation covers the final plan bytes. Any later plan
edit makes it stale again.

## Checklist (all true before you're done)

- [ ] **Active-plan ambiguity driven to zero; every ruling recorded in `task_plan.md` only.**
- [ ] **No-context-lost self-check passed: plan + MEMORY.md + handoff + research artifacts reconstruct the full working context.**
- [ ] Working state snapshotted; open PR/CI state known.
- [ ] `mise run plan-pointer` refreshed the tracked plan digest.
- [ ] `mise run session-orphans` reports no unallowed `OTHER` descendants and no live wait loops.
- [ ] `mise run session-agentsview-pass` completed; findings dispositioned or daemon marked `UNVERIFIABLE`.
- [ ] §1c session-integrity review ran (four reports persisted); every finding is FIX-NOW done or a PLAN line in `task_plan.md`.
- [ ] Any owed `! mise run plan-attest` is printed only after every background task, agent and codex lane finished.
- [ ] Session-LOCAL background tasks/agents + scheduled wakeups inventoried; stale ones cancelled or noted.
- [ ] Session-INDEPENDENT autonomous processes (running GHA runs, Renovate PRs) inventoried in the handoff — NOT waited/blocked on; `main` noted as bot-advanced.
- [ ] Every doc affected by this session's changes updated; cross-refs grep-clean.
- [ ] `mise run lint` covered repository doc refs; every finding fixed or justified in place.
- [ ] `mise run lint` + `mise run lint-docs` green (class-aware `md_size_budget` + agnix AGM-003); at-limit files flagged in the handoff.
- [ ] Every findings-bearing agent's brief AND report persisted verbatim under `docs/research/kb/reports/agents/`; coverage audited.
- [ ] Every report has handoff + governing rule/skill pointers, or is explicitly recorded as deliberately orphaned.
- [ ] Durable memory written + `MEMORY.md` pointer added.
- [ ] Local handoff written under `.agent/plans/` and `mise run handoff-check` returned zero findings.
- [ ] Relevant local gate green; doc commit made (if appropriate).
- [ ] Resume prompt printed for the user to paste after `/clear`.

## See also

- `.agents/skills/session-resume/SKILL.md` — invoked by the resume prompt to read the newest handoff and reconcile it against live repo/PR state after `/clear`.
