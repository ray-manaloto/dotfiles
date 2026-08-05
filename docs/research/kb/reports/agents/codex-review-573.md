# Cold codex review — #573 close-out diff (2026-08-05)

**Lens:** codex exec, ephemeral, read-only sandbox, fed the staged diff (3,113 lines: receipt + five research reports) with no design context.
**Prompt scope:** contradictions within/across files, overclaimed measurements, broken references, implementer-misleading content.

## Findings (verbatim)

1. **High — `573-gh-issues-db.md`, `573.md`**  
   Claim: “**Dependency changes emit NO event … not in the Events API, not to any webhook**” / “topology changes emit **NO GitHub event**.”  
   Why: The report itself finds `BlockedByAddedEvent` and `BlockedByRemovedEvent` in timelines and explicitly says webhook runtime was not probed; only absence from the repository Events API was established.

2. **High — `573-symphony-cc-ports.md`**  
   Claim: “the harness already ships a **persistent, cross-session task list** … reimplementing a weaker claim table would violate `use-tool-builtins`.”  
   Why: The receipt reaches the opposite architecture: “`CLAUDE_CODE_TASK_LIST_ID` … fully demoted to session-local todo use” and GitHub Issues is the only database.

3. **High — `573-linear-tracker.md`**  
   Claim: GitHub has an “adequate” machine-state equivalent in “**a fenced block in the issue body**.”  
   Why: The same report describes that body approach as a lost-update race, while `573-gh-issues-db.md` and the receipt explicitly require that the body never be machine-written.

4. **High — `573-symphony-cc-ports.md`**  
   Claim: “Prefer **one edited state comment** … plus an append only at genuine phase boundaries.”  
   Why: This directly conflicts with the receipt’s append-only-comment contract and the GitHub report’s concurrency rationale that every state write must be a new comment.

5. **Medium — `573-linear-tracker.md`**  
   Claim: “Claiming is therefore **last-write-wins, identical to GitHub**.”  
   Why: `573-gh-issues-db.md` proves GitHub assignee addition is set-additive: two claimants can both succeed and leave two assignees, not a single last-write winner.

6. **Medium — `573-linear-tracker.md`**  
   Claim: Attachment metadata provides an upsert “with … **no lost-update race**.”  
   Why: The same file establishes that Linear supplies no CAS; two writers updating the same URL-keyed blob remain last-write-wins and can overwrite one another.

7. **Medium — `573-linear-tracker.md`**  
   Claim: “Linear’s one genuine technical advantage is a server-side `hasBlockedByRelations` filter.”  
   Why: The GitHub report establishes that every list row already contains the stronger, state-aware `issue_dependencies_summary.blocked_by` value; Linear still needs client-side blocker-state inspection.

8. **Medium — `573-gh-issues-db.md`**  
   Claim: The method used “**LIVE read-only probes** via `gh api`.”  
   Why: The report later documents creating and closing #589, changing bodies, labels, assignees, comments, dependency edges, and issue state.

9. **Medium — `573-gh-issues-db.md`**  
   Claim: “**one request per tick for the entire reconcile+select input**” returns “every blocker with its state.”  
   Why: The displayed proof queries only `issues(first:3)` and `blockedBy(first:5)`, while the same report says the repository has 132 open issues; neither connection is complete without pagination.

10. **Medium — `573-gh-issues-db.md`**  
    Claim: The Search API’s 30/minute bucket is “**~2000× tighter per unit time**” than 5,000/hour core.  
    Why: Normalized to an hour, the limits are 1,800 versus 5,000—about 2.8×, not 2,000×.

11. **Medium — `573-cc-scheduled-tasks.md`**  
    Claim: “Up to **30 s jitter on a 60 s period**” is marked `CONFIRMED`.  
    Why: The report explicitly says it did not establish whether the remotely gated configuration overrides the 50% local default on this host.

12. **Medium — `573-symphony-cc-ports.md`**  
    Claim: “**Still NOT verified … the dependency WRITE surface.**”  
    Why: `573-gh-issues-db.md` verifies add/remove writes directly, including accepted and rejected dependency mutations and restoration.

13. **Medium — `573-gh-issues-db.md`**  
    Claim: “**All live mutations were reverted** and verified against pre-probe baselines.”  
    Why: Its own table says #589 did not exist beforehand and remained as a newly created closed issue, so at least the creation was not reverted.

14. **Medium — `573.md`**  
    Claim: “map #556’s architecture-of-record line is **corrected accordingly**” and “Superseded map lines **corrected in the same close-out**.”  
    Why: The supplied staged diff contains no map-file modification or even the path of the allegedly corrected file.

15. **Medium — `573.md`**  
    Claim: Findings and disposition are recorded in `docs/research/kb/reports/agents/codex-review-573.md`.  
    Why: That file is absent from the supplied staged corpus, so the receipt’s close-out review and disposition cannot be audited from this change.

16. **Low — `573.md`**  
    Claim: The declared prior-art corpus is `docs/research/kb/reports/`, `docs/specs/`, and `docs/adr/`, but the hit table includes `docs/agent-team.md`.  
    Why: That path lies outside the stated grep corpus and therefore could not have been a hit from the quoted search.

17. **Low — `573-cc-scheduled-tasks.md`**  
    Claim: “**Zero durable tasks exist anywhere on this machine**.”  
    Why: A `find /Users/rmanaloto -maxdepth 6` probe cannot establish an anywhere-on-machine negative; its control only proves visibility of one in-range lockfile.

18. **Medium — `573-cc-scheduled-tasks.md`**  
    Claim: A cloud routine “**can reach GitHub Issues through connectors**” and “open an issue or PR.”  
    Why: The report establishes cloud execution, clone behavior, interval floor, and `/fire`, but never probes or cites configured GitHub connector credentials or issue/PR mutation capability.
## Disposition (by the close-out session, evidence-checked per finding)

| # | Disposition | Reasoning |
|---|---|---|
| 1 | **ACCEPTED-IN-PART** — receipt narrowed | The Events-API absence IS measured (control: 11 adjacent events seen); webhook delivery was not runtime-probed. Receipt now states exactly that. The conclusion (reconcile mandatory) is unchanged — timeline reads are per-issue re-query either way. |
| 2 | **NOT-A-DEFECT (temporal)** | The ports report §4 predates rounds 4–5; reports are verbatim snapshots (`agent-report-persistence.md`). The receipt + map row are authoritative. Cross-referenced in the receipt's reading note. |
| 3 | **COVERED by precedence clause** | The Linear report itself declares its GitHub-side comparisons INHERITED and defers to `573-gh-issues-db.md` on any disagreement. |
| 4 | **NOT-A-DEFECT (temporal)** | Same as 2 — the design's append-only contract postdates the ports report's suggestion; the receipt's contract governs. |
| 5 | **COVERED by precedence clause** | gh probes override: assignee writes are set-additive, not last-write-wins. Recorded in the receipt note. |
| 6 | **CONFIRMED report overclaim** | Upsert-by-url is idempotent creation, not race-free mutation. Report stays verbatim; noted. |
| 7 | **COVERED by precedence clause** | GitHub's inline summary is the stronger primitive; the receipt's decisions table already reflects it. |
| 8 | **CONFIRMED report mislabel** | The method line says read-only; the brief sanctioned bounded mutations and the report documents them + restoration. Receipt note carries the correction. |
| 9 | **ACCEPTED** — receipt corrected | Pagination is real at 132 open issues; receipt now says "one paginated conditional query (2 pages)". |
| 10 | **CONFIRMED report arithmetic error** | 30/min = 1800/hr vs 5000/hr ≈ 2.8×, not ~2000×. Directional conclusion (avoid Search API for the tick) stands. Receipt note records it. |
| 11 | **CONFIRMED overreach in draft ledger row** | The 30s-jitter figure is conditional on the unconfirmed local default; the row must carry that caveat if ever appended to the ledger. |
| 12 | **NOT-A-DEFECT (temporal)** | The gh agent probed the write surface after the ports agent declined to; closure recorded in receipt + notepad. |
| 13 | **CONFIRMED wording nit** | Creation of scratch #589 is not revertible (issues cannot be deleted); it was closed and stripped. "All mutations reverted" should read "all mutations to pre-existing issues reverted; scratch issue closed". |
| 14 | **NOT-A-DEFECT** | Map #556 is a GitHub issue body, not a repo file — its correction happens API-side in this same close-out and cannot appear in a staged diff. |
| 15 | **RESOLVED BY ACTION** | This file. |
| 16 | **ACCEPTED** — receipt annotated | The `docs/agent-team.md` row is now marked as added outside the quoted grep corpus. |
| 17 | **CONFIRMED report overclaim** | A maxdepth-6 find cannot prove an anywhere-negative (probes rule 3). The gate-off conclusion rests on the schema ternaries, not the find. |
| 18 | **ACCEPTED as open item** | Routine→GitHub write capability is docs-asserted, unprobed. Recorded in the receipt as a verification prerequisite for the escalation lane. |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed diff and every file it cites
