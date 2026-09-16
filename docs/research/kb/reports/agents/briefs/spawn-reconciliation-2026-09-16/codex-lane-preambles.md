# Codex lane dispatch prompts (verbatim preambles), 2026-09-16

The spec text each prompt embedded follows `=== SPEC` in the originals and is the sibling `spec-*.md` file; only the preambles are reproduced here.

## codex-lane2-prompt.md

```text
You are the implementation lane for ONE ratified seven-part spec (below, verbatim, authoritative). Implement it on the CURRENT branch of this repository and report exactly what happened.

SITUATION — READ FIRST. The working tree already contains a PARTIAL, UNVERIFIED implementation of this spec (8 modified files, staged, nothing committed; HEAD is 36ac565). It was produced by a previous codex run that was killed mid-flight, AND — during the same window — by a second writer that edited the same files, weakened at least one test ("not check for exact error messages"), and dismissed a red lint. Treat every existing edit as SUSPECT: re-derive each change from the spec, keep what is correct, fix or rewrite what is not, and make every test arm in §5 a real, specific assertion (exact error prefixes/messages where the spec names them). Do not assume any existing test is adequate because it passes.

RULES FOR THIS RUN
- Stay inside the spec's §2 file list. If a change needs another file, stop and say so in your final message instead of editing it.
- Gates: run the §5 bundle EXACTLY as written, each with its exit code appended to the log file, and read the file back. Also run `mise run lint-docs > /tmp/sdlc-spawn-lintdocs.log 2>&1; echo "EXIT=$?" >> /tmp/sdlc-spawn-lintdocs.log`. Never pipe a gate into head/tail. If `mise run lint` fails with an hk INTERNAL error (a Rust source location such as `src/step/runner.rs`), re-run it once — that happened earlier under concurrent edits; a second identical internal failure is a finding, report it. A real lint violation is yours to fix.
- Commit ONLY when pytest, lint and lint-docs are all EXIT=0: `git add` exactly the files you changed (no `git add -A`, no `git add .`), then `git commit` with a conventional `fix(sdlc-team): …` subject and a body stating the rule, the negative arm, and the file-captured gate results; end the body with these two lines exactly:
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01R3V8ff1cnaWEp1QXtmvAYC
  The pre-commit hook (hk) runs for a minute or two — WAIT for it. NEVER use `--no-verify`, `-n`, `HK_SKIP_HOOKS`, or any inline lint suppression (`noqa`, `type: ignore`, `nosec`). If the hook rejects the commit (e.g. trailing whitespace), fix the files and commit again.
- Do not switch branches, rebase, push, or open a PR. Do not write task_plan.md; findings.md and progress.md are append-only if you touch them at all.
- LICENSED DISSENT: if your reading of the code contradicts the spec or one of its PREMISES rows, stop that part and report the conflict with file:line evidence rather than implementing around it.
- TEST CRAFT: isolated state only (tmp_path fixtures; never ~/.codex), no wall-clock timing; every assertion must fail when the change is reverted; when you exercise a failure arm, mutate realistically and assert the mutation landed.

FINAL MESSAGE (this is written to the -o file and is the ONLY report the coordinator receives; make it complete):
1. Every gate's EXIT= line verbatim (pytest bundle, lint, lint-docs).
2. The commit hash, or an explicit statement that you did not commit and why.
3. The list of files you changed, and for each existing suspect edit whether you kept, fixed, or rewrote it.
4. Each §5 arm (1-15) mapped to the test function that implements it.
5. Any premise you probed with both arms; any dissent, naming the spec section and the code location.

```

## codex-lane3-prompt.md

```text
You are the implementation lane for a RESPEC ROUND on a committed change. Implement spec v7 (below, verbatim, authoritative) on the CURRENT branch and report exactly what happened.

CONTEXT. Commit 22bee5a on this branch implemented spec v5 (spawn reconciliation for the codex SDLC team settlement). A cold review found nine confirmed defects; v7 below fixes them. Read `git show 22bee5a` for the baseline diff, and read the parent spec at /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/68a8b3b8-90eb-4d81-ab35-ceabe415ec3b/scratchpad/spec-sdlc-spawn-reconciliation.md (v5) for everything v7 does not change. The tree is clean at HEAD; you are the only writer.

RULES FOR THIS RUN
- Stay inside v7 §2's file list. If a change needs another file, stop and say so in your final message instead of editing it.
- Gates: run the v7 §5 bundle EXACTLY as written (pytest bundle, lint, lint-docs), each with its exit code appended to the log file, and read the files back. Never pipe a gate into head/tail. If `mise run lint` fails ONLY on a Taplo schema-fetch timeout for the Starship schema (a network transient), re-run it once. A real lint violation is yours to fix.
- Commit ONLY when all three gates are EXIT=0: `git add` exactly the files you changed (never `git add -A`/`.`), then `git commit` with a conventional `fix(sdlc-team): …` subject and the body v7 §4 requires (including the one-paragraph correction of 22bee5a's type-guard claim); end the body with these two lines exactly:
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01R3V8ff1cnaWEp1QXtmvAYC
  The pre-commit hook takes a minute or two — WAIT for it. NEVER `--no-verify`, `-n`, `HK_SKIP_HOOKS`, or any inline lint suppression. If the hook rejects the commit, fix and commit again.
- Do not switch branches, rebase, push, or open a PR. Do not write task_plan.md; findings.md/progress.md are append-only if touched.
- LICENSED DISSENT: if your reading of the code contradicts the spec or a PREMISES row, stop that part and report the conflict with file:line evidence.
- TEST CRAFT: isolated state (tmp_path; never ~/.codex), no sleeps or wall-clock timing (set mtimes with os.utime), every assertion exact and fails when the change is reverted; mutate realistically when you exercise a fail arm.

FINAL MESSAGE (written to the -o file; the ONLY report the coordinator receives):
1. Every gate's EXIT= line verbatim.
2. The commit hash, or why you did not commit.
3. Files changed.
4. v7 arms 16-28 mapped to test functions; confirm arms 1-15 still pass by name.
5. Any premise probed with both arms; any dissent.

```

## codex-lane4-prompt.md

```text
You are the implementation lane for a RESPEC ROUND on a committed change. Implement spec v7 (below, verbatim, authoritative) on the CURRENT branch and report exactly what happened.

CONTEXT. Commit 22bee5a on this branch implemented spec v5 (spawn reconciliation for the codex SDLC team settlement). A cold review found nine confirmed defects; v7 below fixes them. Read `git show 22bee5a` for the baseline diff, and the parent spec at /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/68a8b3b8-90eb-4d81-ab35-ceabe415ec3b/scratchpad/spec-sdlc-spawn-reconciliation.md (v5) for everything v7 does not change.

TREE STATE. The working tree already holds a PARTIAL implementation of v7 from a previous codex run that the host killed for memory pressure mid-edit (5 files modified, unstaged, nothing committed, HEAD unchanged). It was a single writer, so the edits are not adversarial, but they are unverified and incomplete: re-derive each change from v7, keep what is correct, finish what is missing, and make every §5 arm 16-28 a real, exact test. You are the only writer now.

RULES FOR THIS RUN
- Stay inside v7 §2's file list. If a change needs another file, stop and say so in your final message instead of editing it.
- Gates: run the v7 §5 bundle EXACTLY as written (pytest bundle, lint, lint-docs), each with its exit code appended to the log file, and read the files back. Never pipe a gate into head/tail. If `mise run lint` fails ONLY on a Taplo schema-fetch timeout for the Starship schema (a network transient), re-run it once. A real lint violation is yours to fix.
- Commit ONLY when all three gates are EXIT=0: `git add` exactly the files you changed (never `git add -A`/`.`), then `git commit` with a conventional `fix(sdlc-team): …` subject and the body v7 §4 requires (including the one-paragraph correction of 22bee5a's type-guard claim); end the body with these two lines exactly:
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01R3V8ff1cnaWEp1QXtmvAYC
  The pre-commit hook takes a minute or two — WAIT for it. NEVER `--no-verify`, `-n`, `HK_SKIP_HOOKS`, or any inline lint suppression. If the hook rejects the commit, fix and commit again.
- Do not switch branches, rebase, push, or open a PR. Do not write task_plan.md; findings.md/progress.md are append-only if touched.
- LICENSED DISSENT: if your reading of the code contradicts the spec or a PREMISES row, stop that part and report the conflict with file:line evidence.
- TEST CRAFT: isolated state (tmp_path; never ~/.codex), no sleeps or wall-clock timing (set mtimes with os.utime), every assertion exact and fails when the change is reverted; mutate realistically when you exercise a fail arm.

FINAL MESSAGE (written to the -o file; the ONLY report the coordinator receives):
1. Every gate's EXIT= line verbatim.
2. The commit hash, or why you did not commit.
3. Files changed, and for each inherited partial edit whether you kept, fixed, or rewrote it.
4. v7 arms 16-28 mapped to test functions; confirm arms 1-15 still pass by name.
5. Any premise probed with both arms; any dissent.

```

