# Premise verifier: handoff PR 1 round-2 spec delta (verbatim)

Commissioned by coordinator `dotfiles-20261003T223944.628809000-05.coordinator` (session 6afe7222), 2026-10-03 ~22:55, over `.claude/worktrees/handoff-automation-research/.agent/plans/spec-delta-handoff-pr1-round2-2026-10-03.md` against `feat/handoff-automation-pr1` @ 21011fb5. Read-only lane; persisted verbatim at receipt.

---

This lane was read-only, so nothing was written to findings.md or progress.md. Please persist this report verbatim.

I read every PREMISES row and each factual claim in the delta myself, against the handoff-pr1 worktree at 21011fb5. One premise is false: the delta says the probe TTL can reuse an existing 10-minute window, but that window is 15 minutes. Several fixes are also not yet implementable as written. **Verdict: FIX FIRST.**

PREMISE REPORT
ROWS: 6 checked — 5 CONFIRMED (2 provenance corrected) / 0 REFUTED / 0 UNVERIFIABLE / 1 ASSUMED (D5). The REFUTED claim is outside the table; it is listed below.

- **D1 — CONFIRMED, but the anchor is wrong.** `main_checkout` is at `python/src/dotfiles_setup/session_common.py:183-203`, not `:172-192` (those lines are `chicago_stamp`/`stamped_name`). It returns the first `worktree ` line of `git -C <cwd> worktree list --porcelain` (`:199-201`).
- **D2 — CONFIRMED for production only.** `.claude/types/claude-code.d.ts:2018-2028` says "This plugin, as loaded". The harness context is different: `tests/fixtures/cli_resolver/harness.ts` imports the module once (`:12`) and then runs arms with different `plugin.root` values (`:43`; the `pluginRoot: outside` arm at `:121-128`). A cache that lasts for the whole module load would return `main/python` in the `outside-git-visible-na` arm, so that arm goes red. See MISSING.
- **D3 — CONFIRMED (provenance corrected).** The row cites the cold review, not code. The code agrees: `session_start.py:413` is `state_dir = args.state_dir or project_root / STATE_SUBDIR`, and `main.py:3242-3246` defaults to `Path(__file__).parent.parent.parent.parent` (the CLI's own tree).
- **D4 — CONFIRMED.** coordinator-handoff adds `--state-dir` to decide, release, launch and retire at `coordinator_handoff.py:1247-1257` (the cited `1245` falls in the inbox block). session-start adds it to decide, renamed and pending at `session_start.py:398-404`.
- **D5 — ASSUMED.** This is a ruling, not code: Ray's F4 ruling that PIN stays advisory until PR 2, which you confirmed.
- **D6 — CONFIRMED (provenance corrected).** The row cites the cold review's probe. My own reads: `.claude/worktrees/handoff-pr1/.git` is a file (`gitdir: …/.git/worktrees/handoff-pr1`); the main checkout's `.git/HEAD` is readable and holds `ref: refs/heads/feat/session-autostart-no-prompts`. So the advisory will fire right away for any session whose hooks load from main.

**Claims outside the table**
- **REFUTED — Fix 2's TTL.** The delta says "a 10-minute TTL … the same as the existing launch-pending window". The code says otherwise: `coordinator_handoff.py:88` is `LAUNCH_PENDING_TTL_S = 15 * 60`, and `:229` reads "An unconfirmed start blocks for 15 minutes". The 10 minutes is the TypeScript `NEGATIVE_ROLE_TTL_MS` (`coordinator-handoff/hooks/register.ts:28`). Also, `probe_pending` is stored as a bare `True` (`:303`) with no timestamp, so any TTL requires changing what is stored.
- **CONFIRMED.**
  - The `:216` invariant is real (`coordinator-handoff register.ts:216-217`), and the early returns at `:196`, `:200` and `:207` break it.
  - `:262` and the fast path at `:248-264` are as described.
  - The positional argv patch is at `:119-134`.
  - The `DOTFILES_PROJECT_ROOT` read is at `main.py:3242-3246`.
  - session-start has no `.agents` mirror; only install-doctor is mirrored.
- **CONFIRMED (interpretive) — D1a was only meant for inspection.** The defects report supports this: `proposals-…-defects-2026-10-03.md:149-150` gives the doctor.toml / `baseline_path` consistency as the reason, and `:223` left state placement as an open question. But the ruled spec row says "*Session project* … in all four copies" (`docs/specs/session-handoff-automation.md:47`), so narrowing it should be accepted on the record.

**F1-F12 coverage.** Every finding is mapped to a fix, and the Q-SCOPE reverse-skew item is deferred to a ticket. Fix 3 is consistent with the F4 ruling: advisory only, no early return, a status suffix plus `toastOnce`. As written, though, F3 (via Fix 2), F4 (via Fix 3) and F5 (via Fix 4) are not cleanly closed; see MISSING.

MISSING:
- **Fix 3's detection does not work as worded (blocking).** "pinState reads `<plugin tree>/.git` … A failure to read `.git` gives `not-applicable`" cannot tell a file from a directory with `$.fs.read`. Reading a directory fails, so taken literally the primary checkout always comes out `not-applicable` and PIN never fires. The spec must name `$.fs.stat(path).kind` (`'file'|'dir'|'other'`, d.ts:2830 and :4124). It must also add `stat` to `CliServices` (`session-start register.ts:321` declares only `read`) and add `kind` to the harness mock (`cli_resolver/harness.ts:52-55` returns only `isLink` and `realPath`). Say that only a stat failure gives `not-applicable`.
- **Fix 2 needs files and an old-data rule (blocking).**
  - `python/src/dotfiles_setup/coordinator_handoff.py` and `tests/test_coordinator_handoff.py` are not in §2 Files.
  - `probe_pending` must change from `True` to something like `{"at": iso}`; `release` pops it, which still works with the new shape (`:410`).
  - The spec must say how a legacy `True` with no timestamp is treated. The precedent is `_launch_in_progress`, which treats an unknown age as stale and adds a warning (`:242-244`).
  - Pick 10 or 15 minutes explicitly.
- **A test file that will break is missing from Files (blocking).** `tests/fixtures/coordinator_handoff_hook/harness.ts:231` asserts `DOTFILES_PROJECT_ROOT: "/session-root"` for coordinator-handoff, and Fix 1 removes that env. Add the file. Its mocked `process.run` (plugin root `/hook-tree/…`, `:61`) will also need answers for `git worktree list --porcelain` and for `fs.stat` of `/hook-tree/.git`. The session_start_hook harness (`:57`, `:206`) needs the same.
- **The cache must be keyed by `plugin.root`, and must cache only success (blocking for the harness).** Fix 5's "cached per module load" breaks the cli_resolver harness (D2). It must also not cache a failed result, or one transient git failure disables the hook for the rest of the module's life.
- **Fix 4's fail arm cannot fail as worded (blocking).** If the arm passes `--state-dir`, which is what the hook does after Fix 1, then `DOTFILES_PROJECT_ROOT=w` is ignored (`session_start.py:413`), rc is 0, and the expected rc 2 never happens. The fail arm must reproduce the rev-1 call: no `--state-dir`, plus `DOTFILES_PROJECT_ROOT=w`. Two related points:
  - Any real-CLI arm that omits both `--state-dir` and `DOTFILES_PROJECT_ROOT` writes into the real repo's `.agent/state` (`main.py:3245`).
  - Every arm should pass a temp `--jobs-dir`, as the cold review did.
- **Fix 4's pass arm cannot fail.** With an explicit `--state-dir`, the python arm can only pass: `renamed` takes no root, so the "move" changes nothing the CLI sees. The check that actually discriminates is a bun-harness assertion that the hook passes the same `--state-dir` and cwd before and after `s.move()`. Add that.
- **The coordinator-handoff real-CLI arm needs a fixture.** `decide` returns `not-coordinator` before touching state unless the job record names a coordinator (`coordinator_handoff.py:339-349`), so "one state file" would find zero files. The arm needs a temp `--jobs-dir` with a coordinator-named record. To exercise `already-launched`, the state also needs a `launch` key (`:286-287`).
- **Fix 4's mock rule describes old behaviour.** "Mocked rc 2 for a non-git cwd, mirroring production" is true only for coordinator-handoff without `--state-dir` (`coordinator_handoff.py:1266-1272`). After Fix 1, neither state hook's CLI reads its cwd for state. Assert cwd equals the plugin toplevel instead, or drop the claim that the mock mirrors production.
- **Fix 8 contradicts Fix 1.** After Fix 1, `sessionProject` is unused in session-start and coordinator-handoff, which recreates F12. The parity set should be:
  - `cliProject` and `isSkew` in all four hooks;
  - `sessionProject` only in install-doctor and plugin-health;
  - `stateRoot` and `pinState` only in session-start and coordinator-handoff.

  Today the parity test compares everything after `PARITY_MARKER` byte for byte (`test_cli_resolver_parity.py:21`, `:31-38`), and `PIN_ARMS` / `EXTRA_ARMS` (`:18-20`) will change.
- **Spec drift (load-bearing for later PRs).** The delta changes behaviour the spec still states, but never amends it. These spec rows contradict it:
  - `:47` (D1a, "all four copies");
  - `:49` (PIN hook status `n/a (main checkout on <branch>)`);
  - `:105` and `:120` (session-start uses `sessionProject`);
  - `:528` (commit title "skew and pin are n/a");
  - `:555` (P19: missing HEAD → `n/a`).

  Bump the spec to rev 11, or state in the delta that it supersedes these rows.
- **Non-blocking: Fix 3 and Fix 5 pull against each other.** Fix 5 runs `pinState` after the fast path, so the fast-path heartbeat `handoff X%/Y%` will not carry the advisory suffix that Fix 3 promises. `pinState` is filesystem-only, so running it first would not break `:262`. State which behaviour is intended.
- **Non-blocking: Fix 2 with no CLI.** When `cliProject` is undefined, `release` cannot be attempted. The spec should say the heartbeat stays `fail($, "<reason>; release unavailable")`.
- **Non-blocking: Fix 7 is not testable as stated.** Verification 5 asserts "`pendingAttempts` at 0", but that map is private to the module (`session-start register.ts:54`). Assert the behaviour instead: a fourth healthy prompt recovers.
- **Non-blocking: the reverse-skew ticket has no owner** or filing step.

VERDICT: FIX FIRST. To dispatch, the delta needs:
1. Correct the TTL premise (15 minutes, not 10), add `coordinator_handoff.py` and its test to Files, and specify the `probe_pending` timestamp and how a legacy `True` is treated.
2. Specify `$.fs.stat().kind` for Fix 3, plus the `CliServices` and harness-mock changes.
3. Key the caches by `plugin.root` and cache only success.
4. Make the Fix 4 fail arm omit `--state-dir`, and give the coordinator arm a jobs fixture.
5. Add `tests/fixtures/coordinator_handoff_hook/harness.ts` to Files.
6. Fix Fix 8's function set to match Fix 1.
7. Amend the spec rows listed above, and record your acceptance of the D1a narrowing.

Files read (all absolute):
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.agent/plans/spec-delta-handoff-pr1-round2-2026-10-03.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/docs/specs/session-handoff-automation.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/docs/research/kb/reports/agents/cold-review-handoff-pr1-21011fb5.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/docs/research/kb/reports/agents/proposals-session-handoff-automation-defects-2026-10-03.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/.claude/skills/{session-start,coordinator-handoff}/hooks/register.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/python/src/dotfiles_setup/{coordinator_handoff,session_start,session_common,main}.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/tests/test_cli_resolver_parity.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/tests/fixtures/cli_resolver/harness.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/.claude/types/claude-code.d.ts

## GitHub repos touched

_None._
