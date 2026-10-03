# Premise report — `docs/specs/session-handoff-automation.md` rev 3 (7bddeda7)

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: premise-verifier subagent (read-only).

PREMISE REPORT: `docs/specs/session-handoff-automation.md` rev 3 (worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research`)

**Limitations.** This lane is read-only (no Write or Bash), so nothing went to findings.md and the coordinator needs to persist this report. I couldn't run `git` or `gh`, so the git behaviour in MISSING-B comes from git's documented semantics and was not run here. I didn't re-check the HEAD commit (7bddeda7). I read the spec file as it stands in that worktree.

**ROWS:** 8 checked: 6 CONFIRMED (0 provenance corrected) / 0 REFUTED / 2 UNVERIFIABLE / 0 ASSUMED (0 checkable)

- **P16: UNVERIFIABLE.** The documented and typed half holds; the `--bg` runtime half is a context mismatch.
  - **The field is documented.** `hooks.md:1148,1155` say `session_title` is "the current session title if one is already set, for example via `--name` or `/rename`".
  - **It is typed.** `SessionStartHookInput` carries it at `d.ts:9153-9158`, with `agent_type` at `:9156`.
  - **A function hook's `classic.SessionStart` receives it.** `d.ts:951-952` maps `classic.<E>` to `ClassicHookInputs[E]`, which is the SDK's `<Event>HookInput` (`:960-964`).
  - **`classic.SessionStart` already fires for function hooks in production.** `install-doctor/hooks/register.ts:343-345` caches its verdict there, and `:156-163` records measured denials that depend on that cache.
  - **It is the `-n` name for lanes.** In `~/.claude/jobs/6fae0fec/state.json:18-19,26-27`, `respawnFlags` `-n` equals `name`, and `nameSource` is "user".
  - **Unsettled:** delivery in an unattached `--bg` session on 2.1.288. The vendored types are from 2.1.277. L1 arms this. Non-blocking, because the job-record fallback is today's source.
- **P17: CONFIRMED (the literal claim).**
  - `pr.py:1049-1052` runs `git -C <workspace> checkout main`, then `pull --ff-only`.
  - `workspace` is `project_root` (`main.py:2433`), which is the tree the CLI runs from (`main.py:3242`; `mise.toml:1009`).
  - Whether that is the *main checkout* depends on where `land` runs. See MISSING-B.
- **P18: UNVERIFIABLE (the `turns()` semantics).**
  - `$.fs.read` exists and needs no subprocess (`d.ts:2738-2757`). It **rejects when the file is missing** (`:2743`), so the reader must treat "absent" as "no generation", not as an error.
  - `turns()` exists (`d.ts:2374-2378`), but it counts "prompts the user has sent this session".
  - Nothing says whether a SendMessage peer delivery (`UserPromptSubmit` `source:"system"`, `d.ts:11288`) counts. If it doesn't, a successor whose launch prompt was swallowed (#1592) and that was started only by SendMessage START stays at `turns()==0` and never reloads.
  - The bun harness in §5 item 9 fakes `turns()`, so it can't settle this.
- **P3 (re-read): CONFIRMED.** Call sites:
  - `coordinator-handoff/hooks/register.ts:115-116,182-183,203-204`
  - `session-start/hooks/register.ts:106-108`
  - `install-doctor/hooks/register.ts:124-125`
  - `plugin-health.ts:36-44`
  - `install-doctor:229-236` is the permit fallback: `root()` first, then `CLAUDE_PROJECT_DIR` when `root()` throws (`:230-234`).
- **P14 (new `CLAUDE_PROJECT_DIR` clause): CONFIRMED.** `hooks.md:626-628`: "`${CLAUDE_PROJECT_DIR}` stays put" after a worktree entry.
- **D1a anchors: CONFIRMED.**
  - `sessionProject` = `root()`, falling back to `CLAUDE_PROJECT_DIR`, matches `install-doctor:229-234`. Note that `session-start:106` and `coordinator-handoff:115/182/203` use the *reverse* order today, so D1a changes their behaviour. The spec does this intentionally.
  - The plugin-health skew is swallowed today: `process.run` resolves on any exit code (`d.ts:2964`), the hook never reads `exitCode` or `stderr`, and `JSON.parse` throws into `catch → null` (`plugin-health.ts:38-52`). So `isSkew` needs new `exitCode`/`stderr` capture there.
  - The permit stays consistent after the `DOTFILES_PROJECT_ROOT` change: `baseline_path` comes from `project_root` (`install_doctor.py:578,619`; `main.py:3005-3008`), and the cached path then equals `sessionProject`.
- **D2a anchors: CONFIRMED.**
  - `CONFORMING_NAME_RE` is at `session_start.py:69-71`.
  - The not-below-limit re-check is at `register.ts:228-231,248`.
  - The lane regex on real names:
    - `dotfiles-20261002T204357.298786000-05.llvm-23-bump` gives feature `llvm-23-bump`;
    - `dotfiles-20261003T143441.L0-urgent-code` gives `L0-urgent-code`;
    - the stamp-only `…298786000-05` gives `298786000-05`, which has no letter, so it is rejected.
- **D4a anchors: CONFIRMED.** `queue()` is at session-start `:80`, the reload pair at `:232-233`, and `prompt.submit` at `:288`. Today the module has no `session.measure` handler, so this is a new handler.

**MISSING:**
- **A. The captured `session_title` does not survive a module reload. Non-blocking, but it defeats the purpose.**
  - The repo's own code says "a reload discards this module's memory" (`session-start/hooks/register.ts:21-23`; `session_start.py:18-20`).
  - A reload re-loads changed modules (`d.ts:3545`). `SessionStart` does not re-fire on a reload. D4a deliberately causes reloads after every land, and every new session also queues `reload-plugins --force` (`session_start.py:296`; `register.ts:231-234`).
  - So the module-memory Map is empty whenever the coordinator-handoff module was reloaded, and decide silently falls back to the job record.
  - **Fix:** use `$.store`, which is "kept between sessions and hot reloads" (`d.ts:2853-2860`), keyed by session id. Alternatively, `classic.UserPromptSubmit` also carries `session_title` (`d.ts:11291`), the current title after a rename.
  - L1 should log the title at **measure time**, after the start reload, not at `SessionStart`.
- **B. The `land_main` marker covers the main checkout only when `land` runs there. Load-bearing for the §3g claim "one write covers the coordinator, watcher and every EnterWorktree lane".**
  - `workspace` is the tree `mise run land` was invoked from (`main.py:2433,3242`).
  - Coordinators run in linked worktrees: the spec's own controls `a8d7baf5`/`f6687621`, and this coordinator lives in `.claude/worktrees/coord-28f1a8f7`.
  - From a linked worktree, `git checkout main` at `:1050` normally fails when `main` is checked out in the main checkout. That is git semantics, not run here. In that case `land` returns 1 before the marker write.
  - **Fix:** state that `land` runs in the main checkout, or write to `main_checkout(workspace)` (`session_common.py:172-192`).
- **C. The spec contradicts itself on `dotfiles-20261002.fnox-provider`. Blocking for §5 item 5's fixture; cheap to fix.**
  - §3b rule 5 makes any lane-shaped name that fails placement, including a different repo, `Unplaced`.
  - §5 item 5 (and proposals `:131`) expects `None`.
  - Pick one. Either add "different repo → `None`" before rule 5, or change the fixture to `lane-unplaced`.
- **D. The at-limit re-check is not really "once".**
  - The TS pre-filter uses a single `limit` read from `DOTFILES_COORDINATOR_HANDOFF_PCT` (`register.ts:227`), before the role is known.
  - A miss at or above that limit caches `"not"` with a 10-minute TTL (`:28,248-249`). So a lane still unplaced at 30% is suppressed for up to 10 minutes, including at 40%.
  - Specify which limit the pre-filter uses under per-role thresholds, the TTL, and how `lane-unplaced` maps into the `roles` cache and the `REASONS` list (`:32-36`; `coordinator_handoff.py:90-104`).
- **E. "At registration it records the generation" can't be implemented as written.** `Register` is `(on, options)` with no `$` (`d.ts:7420`). Record it in `session.start`, which fires once per fresh load (`d.ts:3541-3546`), or at the first measure.
- **F. Edge case in the lane regex.** `CONFORMING_NAME_RE` allows a `Z` zone (`session_start.py:70`). A stamp-only `dotfiles-…T204357.298786000Z` would yield feature `298786000Z`, which contains a letter and so passes as a lane. Exclude `^\d+Z$`, or apply the letter test after stripping the stamp.

**Disposition of earlier MISSING-1 to 10:**
- **1: Resolved in design**, but C and D are new defects in it.
- **2: Resolved.** It needs the new `exitCode`/`stderr` capture (D1a row).
- **3: Resolved**, modulo E.
- **4: Resolved.** Verified that the permit `baseline_path` follows `project_root`.
- **5: Mostly resolved.** `main()` has the path (`handoff_check.py:722-736`). But §3c lane-handoff steps 0-6 never invoke `handoff-check` on the lane path, so say who runs it.
- **6: Partly resolved.**
  - On a step-0 rc of 3 or 2, steps 1 and 3 (`handoff-apply`, new in PR 2) and the `handoff-inbox` fallback still run from an unsynced, possibly pre-L0 tree.
  - §3c doesn't say whether steps 3 and 5 are skipped. The same gap makes **9** conditional: a successor launched into an unsynced worktree loads old hooks (P14). With D1 that shows as `n/a (CLI skew)`, so the successor has no trigger.
- **7: Partly fixed, as the spec says.** Read fresh: `1d335db0/state.json` has no `crossSessionInbound`, while `6fae0fec/state.json:21` has it (same probe shape, so the probe discriminates).
- **8: Resolved on paper.** `_land_post_merge` returns `bool | None` today (`pr.py:990,1028`), and `land_main` needs the `surface` flag (`:1043,1057-1059`). The new return must carry both.
- **9: Conditional.** See 6.
- **10: Worked around.** It rests on P18's unsettled `turns()` semantics.

**VERDICT:** correct the spec first.
- **Blocking:**
  - C: the fixture contradicts §3b rule 5.
  - B: the "one land write covers every main-loaded session" claim depends on an unstated run location, and from a coordinator worktree `land` probably fails before the write.
- **Non-blocking residuals:**
  - P16 (`--bg` runtime): L1 arms it, and a job-record fallback exists.
  - P18 / MISSING-10: this one needs a live arm with a SendMessage-only-started session in L2 or L5, because the harness can't settle it.
  - A: graceful fallback, but switch to `$.store`.
  - D, E, F: implementation-level, but name them in the spec.
  - 5, 6 and 9: specify the sync-failure branch of §3c.

**GitHub repos touched**

_None._ Sources were local only: the `handoff-automation-research` worktree, the knowledge-base offline `$CC` corpus, and `~/.claude/jobs/{6fae0fec,1d335db0}/state.json`.
