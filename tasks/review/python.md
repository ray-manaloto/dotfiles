You lead a read-only review of this repository. Change nothing; only report. Your sandbox is
read-only, and so is every subagent's.

Scope: the `Path:` and `Commit:` lines at the end of this prompt. With `Commit: none`, review the
uncommitted changes (staged, unstaged and untracked) under that path: `git status --short -- <path>`,
`git diff HEAD -- <path>`, and each untracked file read in full. With a commit, review what it
changed under that path: `git show <commit> -- <path>`.

Review against `CODING_STANDARDS.md` at the repository root (rules R1-R8), applying every rule to
every changed file. Skip what ruff, ty, coverage and `codegen --check` already enforce, and skip
correctness nits unless they break a rule. Find every finding in this one pass: a checklist row
is done only when it has been checked, never because an earlier row found something.

## 1. Size the change

Count the changed lines in scope (`git diff --numstat HEAD -- <path>` plus untracked files' lengths,
or `git show --numstat <commit> -- <path>`). Leave generated models, JSON Schemas and lock files out
of the count, and out of line-by-line review: check code against them instead.

- Under 1,000 changed lines: review it yourself. Build the checklist of (file, R1-R8) and work
  every row. A row is done only when every changed line in that file was checked against that rule.
  Report each site that breaks it, one line per site, never one example for a rule that repeats.
- 1,000 lines or more: split it into slices of about 1,000 changed lines each, grouping files that
  test or call each other (a module with its tests). Split one large file by line range. Do not read
  the code yourself beyond what you need to slice it.

Size and slice from the numstat counts above before you read any code.
When a tool lists projects, files or tools, keep only what this review needs: never print a whole
project inventory or tool catalogue.

## 2. Fan out (large changes only)

Spawn one subagent per slice with `spawn_agent`, `fork_turns: "none"` and `reasoning_effort:
"medium"`. At most 6 run at once (review:python sets the thread limit to the lead plus 6): start
up to 6, and each time one finishes, start the next until every slice is done. If a spawn fails
with the thread limit, wait for one to finish and spawn it again.

Each subagent's message carries its paths or line ranges, the scope command for them (the same
`git status` / `git diff` / `git show` as above, limited to its paths), and the review rules and
output format below; not your own instructions. The subagent does not spawn agents. It messages you
only for a blocker it cannot get past, and otherwise reports once, in its final answer. It reads
`CODING_STANDARDS.md`, the changed lines of only its files, and any other file just enough to
confirm a finding. It builds a checklist of (file, R1-R8) and works every row: no stopping at the
first finding. A row is done only when every changed line in that file was checked against that
rule. It reports each site that breaks it, one line per site, never one example for a rule that
repeats. Skip what ruff, ty, coverage and codegen enforce. It returns, and nothing else:

- one line per finding: `R<rule> path:line - what is wrong - the change that fixes it`;
- one line per file: `checked <file>: R1 clean, R2 1, ...` with every rule from R1 to R8.

## 3. Verify and merge

When every slice has returned (or after your own review of a small change):

- Check each finding at its path:line: read the smallest enclosing function or block, plus a
  caller or definition only when the finding depends on it. Read several excerpts in one batch.
  Do not read whole files. Drop any finding that does not hold up, with the reason.
- Merge duplicates. Findings that share one fix may be grouped, but every path:line stays, one
  line each.
- Order by rule, then path.

## Report

Final answer, in this order and nothing else:

1. One line per confirmed finding: `R<rule> path:line - what is wrong - the change that fixes it`.
2. One line per dropped finding: `dropped: <finding> - <reason>`.
3. One line per changed file: `checked <file>: R1 clean, R2 1, ...` with every rule from R1 to R8.
4. One line, `slices: <n>` (0 when you reviewed it yourself).
5. Rules checked with no finding in any file, as one line: `clean: R1, R3, ...`.
6. The last line, exactly one of:
   - `VERDICT: PASS` when there are no confirmed findings,
   - `VERDICT: CHANGES` otherwise.
