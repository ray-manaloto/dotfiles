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

⚠️ **Enumerate by ANCESTOR CHAIN, and exclude NOTHING.** This step was prose
until 2026-09-15 and it failed: a sweep reported "nothing outlives this session"
while a 32-minute orphaned wait loop was running. The sweep had excluded
`/bin/zsh -c source …snapshot-zsh…` — which is exactly how the harness runs a
background task, so it filtered out the category the target belongs to. The
operator's status line ("1 shell") was ground truth; the probe was not.

The method that works: walk `ppid` from each process up to init, keep everything
whose chain reaches THIS session's `claude` pid, and only then classify. That
same chain is what proves a foreign `codex exec` (the ChatGPT desktop app runs
one under `ChatGPT.app` -> `Codex Computer Use.app`) is **not yours and must not
be killed**.

Three probe shapes that each returned a confident wrong answer in one session —
none of them can produce the other outcome, so none is evidence:

- `until [ -f X ]` where `X` already exists from an earlier run — exits instantly
  against a stale file. **Delete `X` first, or the wait is a no-op.**
- `until ! pgrep -f "<literal>"` — the waiting shell's own argv CONTAINS the
  literal, so it matches itself and can never finish.
- any sweep with an exclusion — see above.

⚠️ **An `until [ -f X ]` wait is UNSATISFIABLE if the producer of `X` was killed.**
The 2026-09-15 orphan waited on a receipt whose gate run had been terminated
mid-flight; it would have spun forever. Prefer the harness's background run plus
its completion notification over any hand-rolled wait; when a wait is genuinely
needed, use `mise run bounded-wait` with its required deadline.

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
processes — do NOT block `/clear` on the latter (Ray, 2026-07-08).** GitHub-side
processes — running GHA runs, and autonomous bots like **Renovate** that
continuously open/merge PRs on their own schedule — execute on GitHub
regardless of whether you `/clear`, start a new session, or none. They are NOT
"background tasks of this session." Trying to wait for `main` to "settle"
before `/clear` is futile when Renovate is active: merging one PR immediately
triggers its promote run + the next queued PR (observed 2026-07-08 — #188
merged → promote in-flight + #189 building + #192 failing, all at once).
Correct handling: **INVENTORY** in-flight autonomous PRs / CI runs in the
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

## 2. Documentation sync — make docs match reality

For everything changed this session (uncommitted **and** recent commits not yet
reflected in docs), find and update every affected doc. Walk these in order:

1. **Directory docs.** For each touched directory, update its `AGENTS.md`
   (the `CLAUDE.md` is a thin `@AGENTS.md` stub — edit `AGENTS.md`). Root
   `AGENTS.md` for cross-cutting changes (pipeline shape, build types, tasks).
2. **Cross-references.** Grep for anything renamed, moved, deleted, or
   re-timed and fix every hit:
   ```bash
   git grep -nE "<old-filename>|<old-command>|<old-cron>|<renamed-symbol>" \
     -- ':!.omc*' ':!*.lock'
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

   **This step used to print an ad-hoc `git grep | while read` loop, and it
   was retired 2026-07-24 because it was actively misleading**: it matched
   bare basenames and reported **~120 false MISSING hits** in one run (a
   `.claude/rules/*.md` "see also" cites `do-not.md`, which resolves at
   `.claude/rules/do-not.md`). Filtering by "does this basename exist anywhere
   in `git ls-files`" still left 58, nearly all legitimately external —
   container paths, gitignored artifacts, memory files living outside the
   repo, illustrative examples. Exactly one was real. The checker encodes all
   of that as `_ALLOWED_ABSENT`, each entry justified; the loop encoded none
   of it. A sweep whose output is ~99% noise does not get read.

   So: if `mise run lint` is green, doc refs are clean. When the gate DOES
   fire, judge the hit — fix the ref, or add a justified `_ALLOWED_ABSENT`
   entry (prefer fixing). Widening the checker's scope is a `DOC_PATHSPECS`
   change plus a coverage assertion in `tests/test_doc_refs.py`; do not
   re-add a manual loop.

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
- Project docs/rules/cross-refs point to `CLAUDE.md` (which imports
  `AGENTS.md`), never reference `AGENTS.md` directly
  (`feedback_refer_to_claude_md_not_agents_md`).
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
moment it was received — condensed notepad summaries do NOT count (near-loss
observed 2026-07-05: 13 reports existed only in context until a manual
round-2 pass). At session-handoff, audit coverage: enumerate every agent launched
this session; each findings-bearing one must map **both its brief (the prompt
handed TO it) and its report** to an artifact file (or an explicit N/A in the
handoff). Anything missing: write it now, verbatim from context, before
`/clear` destroys the only copy. Briefs are in scope because #601's seven
review rounds left all seven briefs in an ephemeral scratchpad — the reports
survived, the questions that produced them did not.

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

Print exactly this single line and nothing else:

```text
Run /session-resume
```

## Checklist (all true before you're done)

- [ ] **Active-plan ambiguity driven to zero; every ruling recorded in `task_plan.md` only.**
- [ ] **No-context-lost self-check passed: plan + MEMORY.md + handoff + research artifacts reconstruct the full working context.**
- [ ] Working state snapshotted; open PR/CI state known.
- [ ] `mise run plan-pointer` refreshed the tracked plan digest.
- [ ] `mise run session-orphans` reports no unallowed `OTHER` descendants and no live wait loops.
- [ ] `mise run session-agentsview-pass` completed; findings dispositioned or daemon marked `UNVERIFIABLE`.
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

- `.claude/skills/session-resume/SKILL.md` — invoked by the resume prompt to read the newest handoff and reconcile it against live repo/PR state after `/clear`.
