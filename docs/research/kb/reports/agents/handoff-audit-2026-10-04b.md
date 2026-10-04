READ-ONLY LANE. Nothing was written to disk. Persist this report verbatim, for example as `docs/research/kb/reports/agents/handoff-audit-2026-10-04b.md`.

# Audit of handoff 10-04b (coordinator 03b81398) against its transcript

**Summary:** 1 HIGH, 6 MED, 5 LOW. Every SHA, issue and PR number checked is real and matches the handoff.

## What I checked

**Sources:**
- Transcript lines 900–1143. The handoff was Written at L972 (09:18:15), amended at L995, L1020 and L1058, and committed as b4e0228e (L1107).
- All 10 `Agent` dispatches and their agent IDs (L79–L886).
- All `SendMessage` calls.
- Both `AskUserQuestion` calls (L355, L360) and the answer at L379.
- The teammate messages at L970, L1008, L1032, L1041 and L1055.
- The subagent hand-back at L1134.

**Verified correct (positive probes):**
- **Ray ruling, exact wording.** Q: "...What scope should the N2/N1 fix have before credit-fallback ships?" A: **"Full workflow projection now"**. That is the non-recommended option; the recommended one was "Hook + N1 now, ticket workflow". Second answer: **"No, carry on (Recommended)"** (L379). The handoff (`:19-24`) is accurate.
- **dotfiles SHAs.** `git cat-file -t` returns `commit` for:
  - `87bc122c` (on branches 04a and 04b);
  - `f9b56da5` (feat/session-autostart-recipe; the worktree is detached at it);
  - `b79654d4` (L1);
  - `b0774dc1` (1502, detached).
- **Lane worktree heads** (`git log -1 --format=%H`):
  - rgs is `34b8651a…`;
  - handoff-pr1 is `17a97975…`;
  - credit-fallback is `636dd297…`.
- **KB SHAs.** `e79f3846`, `1eb5fdfc`, `50e54f2f` and `c7336ca1` all exist. KB origin/main is e79f3846 (#873).
- **gh probes:**
  - #1648: OPEN, "research-gate-sync: doctor blind to a gate moved…".
  - #1649: OPEN, "handoff hooks: PIN toast names PR ordinals…".
  - KB#872: OPEN, agnix.
  - KB#873: MERGED, mergeCommit `e79f3846131c…`.
  - KB#862 and KB#865: both MERGED.
- **Agent IDs.**
  - ac4747f8 (L856) is the rgs implementer.
  - a6597e7c (L886) is the PR1 round-4 implementer.
  - a6055388 (L811) is the premise-verifier.
  - Their dispatch prompts (L855, L885) name exactly the report paths the handoff gives, and say "ONE new commit".
- **PR1 F1 citation.** `harness.ts:345-363` matches row F1 of `cold-review-handoff-pr1-round3-17a97975.md`.
- **04b not pushed.** `ls-remote --heads origin docs/handoff-2026-10-04b` returned empty. Control arm: `ls-remote origin main` returned `2cdcda4562e8`.

## Findings

| Sev | Claim in handoff (file:line) | What the transcript or probe shows | Proposed correction |
|---|---|---|---|
| HIGH | `:44-48`: "SLOT GO was given for the re-push + kb-land; **the KB shipper HOLDS the host slot.** When it reports DONE, forward the merge SHA…" | This is stale text left over from the first Write (L972). L970 (09:17:53): the shipper reported "DONE, and the HOST SLOT IS RELEASED. KB #873 … MERGED as e79f3846". L988 then forwarded the SHA, and L1057 granted the slot to KB ship #3. So the file contradicts itself: `:60` says KB#873 is DONE, `:64` says the slot is granted to ship #3, and `:47` still says it is held for #873. A successor reading top-down could wait for a #873 DONE that already came. | Rewrite `:45-48` as: "KB#873 MERGED e79f3846 (kb-land rc 0). SHA forwarded to model-registry. Slot now with KB ship #3; see HOST SLOT." |
| MED | `:59` and `:68`: the premise-verifier a6055388 is "IN FLIGHT". The plan is "persist…, apply corrections, then dispatch codex-sol-implementer" | The hand-back arrived at L1134 (09:21:06), after the handoff commit (L1107) and after the old session went idle (L1126). Its verdict is **FIX FIRST**. Rows: 40 total, 34 CONFIRMED, 1 REFUTED (P31), 5 ASSUMED. Blockers: **A** (T7 / M-N1c reason text contradicts the shared decode helper, so the mutation survives); **B** (T4's route mutation cannot go RED; `fanout:2057-2059`); **C** (a JS mirror row with `code:''` that is not mirrored has no rule). P2 ("the worktree is clean") is ASSUMED, so the coordinator must confirm it. Probe: `premise-verifier-credit-fallback-projection-r1.md` now exists in the credit-fallback worktree (13379 B, mtime 04:22), so the successor has persisted it. | Mark the item settled with verdict FIX FIRST. Name A, B and C plus the P31 correction as required spec edits before dispatch, and say that P2 needs a `git status` check. |
| MED | `:59`: dispatch with spec `docs/research/kb/raw/specs-2026-10-04b/spec-credit-fallback-projection-r1.md` (a relative path) | That path exists only in the handoff-2026-10-04b worktree. In the main checkout, `ls …/dotfiles/docs/research/kb/raw/specs-2026-10-04b` returns "No such file". The original is in `~/.claude/jobs/03b81398/tmp/specs/`. The 04b worktree now shows ` M …/spec-credit-fallback-projection-r1.md`, meaning the corrections are being edited into the copy that is about to ship. | Give the absolute path, and say which copy is authoritative for the corrected r1.1. Either re-commit 04b after the edits or keep the edits in jobs/tmp, so the shipped 04b and the dispatched spec do not diverge. |
| MED | `:57`: the rgs lane "Settles when [report] exists AND … a new commit" | Probe at 04:22: the report exists (3186 B, mtime 04:22) but rgs HEAD is still `34b8651a`, with ` M tests/test_doctor.py` and ` M tests/test_research_gate_sync.py`. The codex lane writes its report incrementally; pid 11736 still runs under session 03b81398. So "the report exists" is not a settle signal on its own. | Settle on the commit plus a `SubagentHandback` in `subagents/agent-ac4747f87f7d82af0.jsonl`, not on the report file existing. The same applies to PR1: no round-4 report exists yet, pid 94562 is running and the worktree is dirty. |
| MED | `:97`: "The owner is unresolved, so the shipper's move-aside ruling stands." `:92`: the shipper "restores them" | L1055 (09:19:17), model-registry correction: KB `.agents/skills/model-registry/` "is most likely mine… **I've told the shipper to drop it rather than restore it** after ship #3." Two seconds later the coordinator's SLOT GO (L1057) said "Moving … aside **and restoring it after is approved**." The shipper received **conflicting instructions**, and the handoff records neither the correction nor the conflict. | Add: "model-registry now claims ownership (L1055) and told the shipper to drop it. That conflicts with the coordinator's restore approval (L1057). The successor must send the shipper one ruling: drop it, because the owner consents." |
| MED | Not in the handoff | L1057 asked the KB shipper: "Please file the .agents mirror tracking/gitignore question **as a comment on KB#872**." The real fix (track or gitignore the `.agents` mirror; #868 added the skill without its mirror) is not recorded as owed. | Add to the owed actions: verify the KB#872 comment exists, then decide track or gitignore for the `.agents/skills` mirror. |
| MED | task_plan `:2610-2627`: the only 633cd8 block | It says PR1 round 3 "Next: Opus cold review, then ship" and rgs "Next: respec round 1". It lacks: the round-3 DO NOT SHIP (F1) and round 4 in flight, rgs respec r1.2 RATIFIED and in flight, #1648 and #1649, KB#873 merged, and the 04b handoff itself. `grep -n 04b\|1648\|1649 task_plan.md` matched nothing; the control `grep 'Full workflow'` matched `:2613`. | Append a 03b81398 handoff block through plan-apply with the current state of PR1, rgs and credit-fallback. |
| LOW | `:64` HOST SLOT: "It reports DONE to the successor" | The SLOT GO at L1057 also told the shipper "Its first dotfiles ship is docs/handoff-2026-10-04b". The shipper first asked the OLD coordinator (L1041) because no successor appeared in ListAgents. It may report back to 03b81398 again. | Add: "If no DONE arrives, check 03b81398's inbox and the fallback `.agent/plans/handoff-inbox/`." |
| LOW | `:85` and `:73`: promises to lanes | These are recorded: L1 (L205), 1502 PR# (L206), autostart PR# (L597), capfix PR#. Not recorded: L597 told autostart that the main-checkout agent-memory-local is "noted… **I'll handle it**". `:93` only says "watch". | Change `:93` to say it is a promise owed to the autostart lane. |
| LOW | `:34`: "216 passed and 15/15 mutations red" | That is the implementer's figure. The cold review measured **1 failed, 288 passed, rc=1** on the targeted set, and notes F1 already failed at 18e35f9c (round 2), not only in round 3. | Note the cold review's count and that the failure dates from round 2. |
| LOW | `:70-79`: queue items 2–11 | The SHAs are omitted, though the 633cd8 queue block has them (serp 1ba74fab, bgisolation c3569d61, cap e078c542, rev10 703e5612, G b07ebd7b/15c1061d/14a02f76, codex-research ccf6234c). Queue item 14 (the remainder: ship-pytest fix, #1639/#1636/#1637, the 10-03m list, MR-B-D, ledger last) is dropped. | Point to the queue block for SHAs and mention item 14. |
| LOW | Ship queue `:472-473` | There is a duplicate, empty heading `## 2026-10-04T04:19:51-05:00 — …coordinator` before the real 04:20 block. That is a queue-append artifact. | Cosmetic; leave it or remove it in the next queue-append. |

## Negative probes and their control arms

- **PR1 round-4 report is absent.** `ls …/handoff-pr1/…/codex-sol-implementer-handoff-pr1-round4.md` returned "No such file". Control: `cold-review-handoff-pr1-round3-17a97975.md` in the same directory was listed (18944 B).
- **No new rgs or PR1 commit.** `log -1` gives the base SHAs. Control: the 04b worktree's `log -1` shows the new b4e0228e.
- **task_plan lacks 04b, #1648 and #1649.** Control: the `Full workflow` grep hit `:2613`.
- **The specs directory is not in the main checkout.** Control: `git show --stat HEAD` in the 04b worktree lists the three spec files.
- **The 04b branch is not on the remote.** Control: origin main resolved.

## Live state at 04:22 CDT

- Codex lanes still running under session 03b81398: pids 11736 (8m38s) and 94562 (10m55s).
- A third codex lane (pid 7795) runs under session 1debf341, the successor.
