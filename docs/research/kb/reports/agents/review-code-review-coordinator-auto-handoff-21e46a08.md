# /code-review — coordinator-auto-handoff 21e46a08

## Brief

Review target: `21e46a08`

`minimal prompt → single careful diff pass → ≤15 findings`

You are reviewing a pull request for real bugs. Run `git diff @{upstream}...HEAD` (or `git diff main...HEAD` / `git diff HEAD~1`
if there's no upstream) to get the unified diff under review. If there are
uncommitted changes, or the range diff is empty, also run `git diff HEAD` and
include the working-tree changes in scope — the review often runs before the
commit. If a PR number, branch name, or file path was passed as an argument,
review that target instead. Treat this diff as the review scope.

Review the diff as a careful senior engineer would: read every hunk, open the surrounding files for context as needed (Read, Grep, git log/blame/show), and hunt for correctness issues — wrong or inverted conditions, off-by-one, null/undefined dereference, missing `await`, dropped error handling, removed guards or validations, broken callers of changed functions, races. Prefer real failure modes over style; every finding needs a concrete scenario in which the code misbehaves.

When you are done, submit at most 15 findings via the ReportFindings tool, filling its fields as defined — for each: the file path and start line, a severity, and a comment that states the issue and the concrete scenario in which the code misbehaves. Quality over quantity: include everything you genuinely believe is a real issue, and nothing you don't.

After the tool call, also restate the findings in your final reply — one line each, `file:line — summary` — so they stay visible in sessions that do not render tool output.


## Report (verbatim)

I found four issues in `21e46a08`. One more thing: there is no ReportFindings tool in this session, so I couldn't submit them through it, and the findings below exist only in this reply.

1. **`.claude/skills/session-start/hooks/register.ts:137` (medium) — deferred session names always end in `.session`.**
   - The code treats the result of `$.model.complete(...)` as a string and passes it to `toSlug(reply)`.
   - In the running engine (2.1.288 types, line 2414) that call returns an object (`ModelCompleteResult`: `{ isAnswered, text, usage }`), not a string. The repo's vendored 2.1.277 types still say `Promise<string>`, which is why this type-checks.
   - At runtime `toSlug` calls `.toLowerCase()` on that object, throws a TypeError, and the `catch` falls back to `SLUG_FALLBACK`.
   - Result: every session that is renamed at its first prompt gets `<prefix>.session` instead of a slug made from the prompt.
   - The test harness mocks `complete` to return a plain string (`tests/fixtures/session_start_hook/harness.ts:85`), so the tests can't catch this.
   - Fix: check `reply.isAnswered` and use `reply.text`.

2. **`python/src/dotfiles_setup/coordinator_handoff.py:839` (medium) — `retire` can't find the launch record when the old coordinator ran outside the main checkout.**
   - The state directory is `project_root / .agent/state/coordinator-handoff`, and `.agent/` is a gitignored, per-checkout folder.
   - `launch` runs from the old coordinator's own checkout and writes the census and launch record there.
   - The successor is started from the main checkout, and its brief (line 524) tells it to run `mise run coordinator-handoff -- retire` with no `--state-dir`.
   - If the old coordinator was running in a worktree, `retire` looks in the main checkout's `.agent/state`, finds no launch record, and returns rc 2. The old coordinator is never retired through the gate.

3. **`python/src/dotfiles_setup/coordinator_handoff.py:258` together with `register.ts:166-189` (medium) — a fire is used up before the handoff is actually delivered.**
   - `decide` saves `last_fired` before returning `fire: true`.
   - The hook can still fail to deliver after that point:
     - `DOTFILES_COORDINATOR_HANDOFF_DRY_RUN=1` returns without submitting anything, and python never sees that variable.
     - The `skill not listed` path returns early.
     - `$.command.run` can reject. The 2.1.288 docs say it rejects when called "inside a hook the turn is waiting on". The spec marks P2 as ASSUMED and no live arm has tested it.
   - In each case the threshold is already spent, so the next try happens only one step later (35%, 40%, …).
   - If `command.run` always rejects from `session.measure`, the coordinator never hands off; the only symptom is an ERROR on the status line.
   - A dry-run test also silently pushes the real firing level up.

4. **`python/src/dotfiles_setup/coordinator_handoff.py:403` (low) — the census records the log path as the literal `$LOG`.**
   - `_log_path` reads the first redirect target from the process's command line.
   - For the repo's standard background pattern (`mise run ship > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`), the outermost `zsh -c` process holds the unexpanded text, so the saved path is `$LOG`.
   - The successor's brief then tells it to `bounded-wait` on that log's rc line, and `$LOG` doesn't exist in the successor's shell.
