---
name: clear-prep
description: "Prepare for a /clear: bring all documentation up to date with this session's changes, persist recovery context (memory + handoff), and emit a copy-paste resume prompt so the next session begins the next task with zero context loss. Invoke explicitly as /clear-prep [next-task]."
disable-model-invocation: true
argument-hint: "[one-line description of the next task, optional]"
---

# Clear-Prep — Session Handoff Before `/clear`

Run this **before** `/clear` to (1) make every doc reflect the latest changes,
(2) persist recovery context that survives the clear, and (3) print a resume
prompt to paste after `/clear`. `$ARGUMENTS` (optional) is the next task; if it
is empty, infer the next task from open issues / the prior handoff and state
your guess.

Work top-to-bottom. Do not skip the validation gate. Keep the final resume
prompt short — durable detail lives in memory + the handoff, not the prompt.

## 0. Resolve next-task ambiguity FIRST — mandatory (Ray, 2026-07-08)

**Before writing the handoff, drive the next-task scope to zero ambiguity by
asking the user clarifying questions** (`AskUserQuestion`), and keep asking
across rounds until nothing material is unresolved. The handoff's "Next task"
section is only as good as this step — a vague next-task line makes the whole
`/clear` lossy. This is a hard requirement, not a courtesy: if the next task
admits multiple interpretations, scope forks, an undecided B-vs-C, or an
unstated end-goal, you MUST surface each and get the user's answer, then encode
the answers verbatim in the handoff. Skipping this because the task "seems
clear" is the failure mode this step exists to prevent.

**Then double-check nothing will be lost by `/clear`** (see step 3c + the
final checklist): every findings-bearing agent/research report is on disk,
every decision + open question is in the handoff, and the resume prompt +
memory + handoff together reconstruct the full working context. Verify by
asking: "if I `/clear` right now and only have MEMORY.md + the handoff + the
research artifacts, can the next session continue with no gaps?" If the answer
is no, fix it before emitting the resume prompt.

## 1. Snapshot the working state

Gather, don't guess:

```bash
git status --short
git branch --show-current
git log --oneline -8
gh pr list --head "$(git branch --show-current)" --json number,title,state 2>/dev/null
```

Note: current branch, staged/unstaged/untracked files, open PR + its CI state
(`gh pr checks <n> --json name,state`), and any in-flight task from the prior
`.agent/plans/session-*.md`.

Also inventory **session runtime state**: in-flight background tasks/agents
and any scheduled wakeups or crons created this session. Stop what should not
outlive the session; note anything intentionally left running in the handoff.
A stale wakeup firing after handoff re-triggers work that is already done
(observed 2026-07-05).

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
session's task — e.g. a merge you must confirm landed.)

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
   cross-link (`gh issue edit`, `gh issue comment`).
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
shipped, what's next (with issue/PR numbers), locked decisions, and any
non-obvious gotcha. Convert relative dates to absolute. Add a one-line
pointer to `MEMORY.md` (`- [Title](file.md) — hook`). Update an existing
file rather than duplicating; delete memories proven wrong.

### b. Local handoff (survives `/clear`; gitignored, this-clone-only)

Write `.agent/plans/session-<YYYY-MM-DD>[-letter].md`
(`.claude/rules/agent-artifact-conventions.md` — handoffs are plans). The
handoff must be **self-sufficient** — the resume prompt (step 5) only points
here, so *everything the next session needs lives in this file*. Include:
**State at handoff** (branch/PR/merge state, gate results), **what shipped**,
**next task + preload pointers** (epic/issue/spec links), and **gotchas**. If
a prior handoff exists for today, append a letter suffix rather than
overwriting.

### c. Research artifacts — verbatim, receipt-time (audit coverage here)

Full subagent reports must already be on disk per
`.claude/rules/agent-report-persistence.md`: every findings-bearing agent's
final report persisted VERBATIM under `docs/research/runs/<topic>/agents/` at the
moment it was received — condensed notepad summaries do NOT count (near-loss
observed 2026-07-05: 13 reports existed only in context until a manual
round-2 pass). At clear-prep, audit coverage: enumerate every agent launched
this session; each findings-bearing one must map to an artifact file (or an
explicit N/A in the handoff). Anything missing: write it now, verbatim from
context, before `/clear` destroys the only copy.

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

## 5. Self-verify the handoff — claims must match reality

The handoff is written by paraphrase; wrong details cost the next session
more than missing ones. Before printing the resume prompt, verify:

- every repo path the handoff cites exists (run the step-2.5 ref loop
  against the handoff file itself — it is gitignored, so the hk gate never
  sees it);
- spot-check every `file:line` claim (Read the cited line; a stale line
  number sends the next session spelunking);
- every `mise run <task>` / CLI command it names exists (`mise tasks ls`);
- gate results it reports match the recorded `rc` files, not memory.

## 6. Emit the resume prompt — keep it MINIMAL

All context lives in memory (auto-loaded) + the handoff (step 3b). The resume
prompt is therefore a **one-line pointer**, nothing more. Do NOT inline the
task plan, issue summaries, gotchas, preload lists, or gate commands — those
are all in the handoff; duplicating them in the prompt is the failure mode
this skill exists to prevent.

Print exactly this (single line, no extra sections):

```text
Read and follow .agent/plans/session-<date>.md
```

At most, echo the task for the human's benefit on the same line:

```text
Resume <task>: read and follow .agent/plans/session-<date>.md
```

Then a one-line reminder: *"Run `/clear`, paste that line, and the session
resumes from the handoff."*

## Checklist (all true before you're done)

- [ ] **Next-task ambiguity driven to zero via clarifying questions (step 0, mandatory); answers encoded in the handoff.**
- [ ] **No-context-lost self-check passed: MEMORY.md + handoff + research artifacts alone reconstruct the full working context.**
- [ ] Working state snapshotted; open PR/CI state known.
- [ ] Session-LOCAL background tasks/agents + scheduled wakeups inventoried; stale ones cancelled or noted.
- [ ] Session-INDEPENDENT autonomous processes (running GHA runs, Renovate PRs) inventoried in the handoff — NOT waited/blocked on; `main` noted as bot-advanced.
- [ ] Every doc affected by this session's changes updated; cross-refs grep-clean.
- [ ] Repo-wide doc-ref sweep run (step 2.5); every MISSING hit fixed or justified in place.
- [ ] `mise run lint` + `mise run lint-docs` green (class-aware `md_size_budget` + agnix AGM-003); at-limit files flagged in the handoff.
- [ ] Every findings-bearing agent report persisted verbatim under `docs/research/kb/reports/agents/`; coverage audited.
- [ ] Durable memory written + `MEMORY.md` pointer added.
- [ ] Local handoff written under `.agent/plans/` and self-verified (paths, file:line, task names, gate rcs).
- [ ] Relevant local gate green; doc commit made (if appropriate).
- [ ] Resume prompt printed for the user to paste after `/clear`.
