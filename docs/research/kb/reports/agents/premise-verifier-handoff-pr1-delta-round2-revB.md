# Premise verifier: handoff PR 1 round-2 delta, revision B (verbatim)

Commissioned by coordinator `dotfiles-20261003T223944.628809000-05.coordinator` (session 6afe7222), 2026-10-03 ~23:00, re-verifying revision B of `.claude/worktrees/handoff-automation-research/.agent/plans/spec-delta-handoff-pr1-round2-2026-10-03.md` against 21011fb5. Read-only lane; persisted verbatim at receipt.

---

This lane was read-only, so nothing was written to findings.md or progress.md. Please persist this report verbatim.

**Verdict: FIX FIRST**, but only four one-line text edits remain. All 7 blocking items are closed in substance and no new premise is false. Four leftover sentences from revision A now contradict revision B's own fixes: two would make the spec'd tests demand the wrong behaviour, and one misstates who accepted the D1a narrowing. I re-verified against 21011fb5 in the handoff-pr1 worktree.

PREMISE REPORT (revision B)
ROWS: 8 checked — 7 CONFIRMED (2 provenance corrected) / 0 REFUTED / 0 UNVERIFIABLE / 1 ASSUMED (D5)
- **D1 — CONFIRMED.** `session_common.py:183-203` is now the anchor in §7. Fix 1's text still cites `:172-192` (delta line 63); fix that too.
- **D2 — CONFIRMED.** `claude-code.d.ts:2018-2028` ("as loaded"); the harness swaps `plugin.root` per arm (`cli_resolver/harness.ts:12`, `:43`, `:121-128`).
- **D3 — CONFIRMED (provenance corrected).** The anchor is still the cold review; the code is `session_start.py:413` and `main.py:3242-3246`.
- **D4 — CONFIRMED.** `coordinator_handoff.py:1247-1257` and `session_start.py:398-404`. Fix 1's text still says `1245-1255` (delta line 67); this is cosmetic.
- **D5 — ASSUMED.** Ray's F4 ruling.
- **D6 — CONFIRMED (provenance corrected).** I read both myself: `handoff-pr1/.git` is a `gitdir:` file, and the main checkout's `.git/HEAD` reads `ref: refs/heads/feat/session-autostart-no-prompts`.
- **D7 — CONFIRMED.** `FsStat.kind: 'file'|'dir'|'other'` (d.ts:4119-4124); `stat` is declared at d.ts:2830.
- **D8 — CONFIRMED.** `coordinator_handoff.py:303` sets `state["probe_pending"] = True`, and `:410` pops it. `LAUNCH_PENDING_TTL_S = 15 * 60` is at `:88`.

**The 7 blocking items**
1. **TTL, files, stored shape, legacy value — CLOSED in Fix 2.** One leftover: §5 item 2 still says "`probe_pending` older than **10 minutes** clears" (delta line 156). Change it to 15 minutes / `LAUNCH_PENDING_TTL_S`.
2. **File vs directory detection — CLOSED.** `$.fs.stat().kind`, `stat` added to `CliServices`, and harness mocks gain `kind`.
3. **Cache key and failure caching — CLOSED.** Keyed by `plugin.root`; only success is cached.
4. **Test arms — CLOSED, with one leftover.**
   - Done: the fail arm omits `--state-dir`; the bun `s.move()` check discriminates; there is a coordinator jobs fixture plus a `launch` key; every arm uses a temp `--jobs-dir`.
   - Leftover: Fix 4 line 101 still says "mocked `process.run` must return rc 2 for a non-git cwd, mirroring production". Line 104 withdraws that claim. Delete line 101's "mirroring production" requirement, or keep the rc-2 mock and drop the justification.
5. **Missing harness files — CLOSED.** Both harnesses are now in §2.
6. **Parity set — CLOSED.** It is now a per-function compare.
7. **Spec drift — CLOSED by the §0 table, but its attribution is false.** §0 row `:47` says "D1a narrowed (**accepted on the record by the premise-verifier**)". I never accepted it. My report said the narrowing "should be accepted on the record". I advise; the architect, or Ray for a Ray-ruled row, accepts. Reword it to "accepted on the record by the coordinator", or Ray, with a date. As written, it passes a verifier's advice off as acceptance.

**Still unimplementable as written**
- **§5 item 4 (blocking).** "Mutation: move `pinState` or `cliProject` above the fast path, and the test goes red" contradicts Fix 3's ordering. Fix 3 *requires* `pinState` before the fast path. `pinState` needs `<plugin tree>` (`cliProject/..`), so `cliProject` must run there too. With the cache, that move cannot turn the test red. Replace it with: "Mutation: remove the `cliProject` cache (or the `stateRoot` cache), and the 0-spawn assertion goes red."

**MISSING (non-blocking residuals; please accept each on the record)**
- **Coordinator fixture layout.** The record must sit at `<jobs>/<id[:SHORT_ID_LEN]>/state.json` with `sessionId` equal to the full id (`session_common.py:72-84`) and a `name` matching `^dotfiles-.+\.coordinator$` (`:41`, `:94-96`). The delta says only "named like a coordinator"; an implementer will find the rest from these anchors. Also, a pre-seeded `launch` key makes *both* `decide` calls return `already-launched` (`coordinator_handoff.py:286-287`). That is consistent with "one state file", but the text says only the second call returns it.
- **Fix 1 and D4 anchors** in the body (lines 63 and 67) are stale, as noted above. Cosmetic.

VERDICT: FIX FIRST. Make these four edits, then it is ready to dispatch with no re-verification needed:
1. §5 item 2: 10 minutes → 15 minutes.
2. §5 item 4: make the mutation "remove the cache", not "move above the fast path".
3. Fix 4 line 101: drop "mirroring production".
4. §0 `:47`: replace "accepted … by the premise-verifier" with the actual accepter.

Files read:
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.agent/plans/spec-delta-handoff-pr1-round2-2026-10-03.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/python/src/dotfiles_setup/session_common.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1/python/src/dotfiles_setup/coordinator_handoff.py

## GitHub repos touched

_None._
