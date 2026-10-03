# Slot-order deviation advice, 2026-10-03

Codex call: succeeded (rc=0, gpt-6.1-sol xhigh, read-only). Raw verdict: .agent/kb/raw/codex-sol-advisor-verdict-slotadv.md (gitignored).

## Verdict
Recommended (a): let kb837 finish, verify its real rc, release the slot, then restore the approved order strictly.

1. Reorder violated Ray's ruling. Autonomy covers routine slot grants/ship-land order (memory feedback_coordinator_autonomy.md:11), but Ray's later specific ruling "queue order unchanged" (main-checkout-ship-queue.md:284, "Ray rulings 11:55 (3)"; handoff session-2026-10-03b.md:26) wins. Free slot / short runtime / MR-B failure justify PROPOSING an exception, not taking one. MR-B only changed KB ship priority. The watch-push overlapping kb837 is a separate capacity breach (queue file :288); load 174 as cause of flake #1597 is not established.
2a. Finish kb837, then handoff ship -> land 1589 -> autostart -> brief-review-field -> capfix -> G-container -> 1502 -> kb837 remainder -> llvm23. PRO: keeps a progressing run (~3.5 min elapsed at 12:09, load fell 174->30). CON: handoff waits. Green kb837 test does not itself authorize KB ship.
2b. Kill kb837. PRO: handoff sooner. CON: discards run, retry cost; only for hang/deadline/emergency (long-running-command-hangs.md rule 4).
2c. Finish then keep interleaving. PRO: throughput. CON: continues contradicting ruling; needs a superseding ruling.
3. Durability: low immediate risk (branch ref 1c4ee3ae lives in shared repo; protects from gc); exposure = deletion/disk loss. Cheap step: make and verify an incremental git bundle of unpushed commits, record base SHA, copy off the checkout (ideally off-host). Do NOT push with --no-verify (mise-tasks-only.md:31).
4. Process fix: mark Ray-approved queue segments FIXED with ruling timestamp in the ship-queue file; check next approved item before every slot grant ("fits while editing" cannot override); routine grants stay autonomous inside uncommitted portions; a real conflict goes to clarify-before-acting. Put pushes and every KB gate route under the same host lock (python/src/dotfiles_setup/host_lock.py:10); add an order check at grant time. CON: may leave slot idle.

## Not verified
Past full-KB-test duration (no ship/test log found to estimate remaining time). host_lock.py behavior not read by me. Codex's claim that the branch ref exists was its own live check, not mine.

## GitHub repos touched

_None._
