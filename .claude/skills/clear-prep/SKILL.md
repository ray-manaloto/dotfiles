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
`.omc/plans/session-*.md`.

Also inventory **session runtime state**: in-flight background tasks/agents
and any scheduled wakeups or crons created this session. Stop what should not
outlive the session; note anything intentionally left running in the handoff.
A stale wakeup firing after handoff re-triggers work that is already done
(observed 2026-07-05).

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
5. **Doc-ref integrity — repo-wide, NOT just this session's diff.** Stale
   refs predating the session escape the diff-scoped greps above (a deleted
   file's mentions can linger for months — the `home/AGENTS.md` case,
   deleted in PR #80, found 2026-07-05). Verify every backtick path ref in
   the agent docs resolves:
   ```bash
   git grep -hoE '`[A-Za-z0-9_./-]+\.(md|sh|py|toml|pkl|yml|yaml|json|hcl|lock)`' \
     -- 'AGENTS.md' 'CLAUDE.md' '*/AGENTS.md' '.claude/rules' '.claude/skills' \
     | tr -d '`' | sort -u | while read -r p; do [ -e "$p" ] || echo "MISSING: $p"; done
   ```
   Judge each MISSING hit: fix the ref, or confirm it is intentionally
   absent (container path, gitignored, planned file) and make the citing
   doc say so. Machine gate: `dotfiles-setup check-doc-refs` + hk step
   (validation-addition J, epic #160 T13) supersedes this loop once landed.

**Constraints (machine-enforced — respect or the gate fails):**
- `CLAUDE.md` / `AGENTS.md` files have a **200-line / 12,000-char hard
  limit** (`claude_md_size_limit` hk step; char half machine-enforced from
  #160 T13). Check BOTH (`wc -l` and `wc -c`); when a file sits at or near
  either limit, record in the handoff which future edit must trim. Any
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

Write `.omc/plans/session-<YYYY-MM-DD>[-letter].md`
(`.claude/rules/omc-directory-conventions.md` — handoffs are plans). The
handoff must be **self-sufficient** — the resume prompt (step 5) only points
here, so *everything the next session needs lives in this file*. Include:
**State at handoff** (branch/PR/merge state, gate results), **what shipped**,
**next task + preload pointers** (epic/issue/spec links), and **gotchas**. If
a prior handoff exists for today, append a letter suffix rather than
overwriting.

### c. Research artifacts — verbatim, receipt-time (audit coverage here)

Full subagent reports must already be on disk per
`.claude/rules/agent-report-persistence.md`: every findings-bearing agent's
final report persisted VERBATIM under `.omc/research/<topic>/agents/` at the
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

Stage specific paths (never `git add .` — phantom `.omc/state/**` files;
`.claude/rules/do-not.md`). Commit doc updates with the standard trailers.
The handoff (`.omc/plans/`) is gitignored and memory lives outside the repo —
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
Read and follow .omc/plans/session-<date>.md
```

At most, echo the task for the human's benefit on the same line:

```text
Resume <task>: read and follow .omc/plans/session-<date>.md
```

Then a one-line reminder: *"Run `/clear`, paste that line, and the session
resumes from the handoff."*

## Checklist (all true before you're done)

- [ ] Working state snapshotted; open PR/CI state known.
- [ ] Background tasks/agents + scheduled wakeups inventoried; stale ones cancelled or noted.
- [ ] Every doc affected by this session's changes updated; cross-refs grep-clean.
- [ ] Repo-wide doc-ref sweep run (step 2.5); every MISSING hit fixed or justified in place.
- [ ] `CLAUDE.md`/`AGENTS.md` files ≤ 200 lines AND ≤ 12,000 chars; at-limit files flagged in the handoff.
- [ ] Every findings-bearing agent report persisted verbatim under `.omc/research/`; coverage audited.
- [ ] Durable memory written + `MEMORY.md` pointer added.
- [ ] Local handoff written under `.omc/plans/` and self-verified (paths, file:line, task names, gate rcs).
- [ ] Relevant local gate green; doc commit made (if appropriate).
- [ ] Resume prompt printed for the user to paste after `/clear`.
