# Codex cold adversarial review — receipt for #438 (flock replacement / dead inode)

**Lens:** codex CLI / `gpt-5.6-sol`, `codex exec --ephemeral --sandbox read-only`, `model_reasoning_effort=high`
**Input:** `docs/receipts/438.md` in full on stdin, with an explicit *"do NOT read the disk"* constraint.
**Date:** 2026-08-01

> Persisted **verbatim** at receipt, per `.claude/rules/agent-report-persistence.md`. Dispositions live in `docs/receipts/438.md`, not here.

---

1. **CRITICAL — The proposed upstream lock may begin too late to prevent lost updates.**  
   **Quoted text:** “wrap the four `config.rs` write functions in a `LedgerLockGuard`-shaped guard” and “`lock` → `load` → mutate → `save` sequences … the exact read-modify-write shape `config.rs` needs.”  
   **Why it fails:** Locking only a write/save function does not prevent two callers from loading the same old state before either acquires the lock. The document praises `lease.rs` specifically for locking before `load`, but does not establish that each proposed `config.rs` guard would encompass the caller’s complete load→mutate→save transaction. Consequently, “covers 10 of the 11 writers” does not follow.  
   **WHAT WOULD SETTLE IT:** For every caller, show the read and mutation boundaries and prove that the same guard is acquired before the read and held through the final rename; otherwise place the guard at the transaction-level call sites.

2. **CRITICAL — The claimed observed incident contradicts the document’s own evidence boundary.**  
   **Quoted text:** “Lane 2 is where the only observed incident lives,” “one of its items is live and measured,” and later: “Did not measure the race… The lost update is derived from source … not observed.”  
   **Why it fails:** The document moves from a source-derived possibility to an “observed incident” without presenting an observation. It also notes that a prior wipe was corrected to “codegen, not a race,” which further undermines attribution of an incident to this concurrency defect. A direct writer is observed in source; a lost-update incident is not.  
   **WHAT WOULD SETTLE IT:** An incident record or deterministic trace showing two overlapping operations, the stale read, and the resulting overwrite—or revise the claim to “the only identified high-risk writer.”

3. **MAJOR — The “11 writers” inventory repeats the enumeration error the document criticizes.**  
   **Quoted text:** “Measured writer inventory …” and “Covers 10 of the 11 writers.”  
   **Why it fails:** No exhaustive search method for writers is shown. The table enumerates selected command call sites and one Python writer, while the document itself names direct edits, regeneration, mise, chezmoi, and other agents as additional writers. It later admits “no gate would notice a new one.” Thus 11 is neither a complete writer count nor a stable denominator; it also conflates command-level callers with distinct writers.  
   **WHAT WOULD SETTLE IT:** Define “writer” precisely, show a complete write-sink/call-graph search across every in-scope repository and execution mechanism, and either include external writers or explicitly label the table “known application call sites.”

4. **MAJOR — A shared pathname alone is insufficient to make the Rust and Python locks interoperate.**  
   **Quoted text:** “Lanes 1 and 2 only compose if both take the same lock.”  
   **Why it fails:** Using the same file is necessary, but not sufficient. Different APIs can apply non-interacting lock classes or differing shared/exclusive, descriptor-inheritance, and open-file semantics. The local implementation is only described as taking “the same sidecar lock”; no Python primitive or compatibility contract is specified.  
   **WHAT WOULD SETTLE IT:** Specify the exact OS locking primitive and exclusive-lock semantics in both implementations, then provide a cross-process Rust↔Python contention test, including crash and descriptor-inheritance cases.

5. **MAJOR — The single-store bound used to reject CAS is inherited, not established here.**  
   **Quoted text:** “`docs/receipts/437.md` … supplies the ‘fnox cannot write Doppler’ premise that bounds this ticket to a single-store problem” and “CAS … was proposed for a distributed Doppler+fnox update that #437 established does not exist.”  
   **Why it fails:** This is a load-bearing premise imported from another document whose evidence is not reproduced. The current receipt’s rejection of CAS changes if that bound is false, and the receipt later expressly admits that a new Doppler write path would invalidate its reasoning.  
   **WHAT WOULD SETTLE IT:** Include the current-version provider/write call graph or behavioral evidence proving that neither fnox nor any covered workflow writes Doppler.

6. **MAJOR — “Nobody has raised” is not supported by the upstream search.**  
   **Quoted text:** “Nobody has raised concurrent config writes upstream.”  
   **Why it fails:** Four narrow queries do not establish absence. The search omits obvious vocabulary such as `race`, `concurrent`, `flock`, `locking`, `overwrite`, `data loss`, `clobber`, and `serialization`, and does not establish coverage of discussions or reports outside GitHub issues/PRs. The positive and negative controls test query operation, not semantic completeness.  
   **WHAT WOULD SETTLE IT:** Run and disclose a broader synonym set over all relevant upstream channels, or narrow the conclusion to “none found by these four queries.”

7. **MAJOR — The daemon alternative is rejected from an enum that does not prove routing behavior.**  
   **Quoted text:** “`Request` … admits only `ResolveBatch`/…/`Shutdown` … `fnox set` does not route through it.”  
   **Why it fails:** The request variants show the visible protocol surface, but do not by themselves prove every `fnox set` path or exclude use of an existing generic operation. More importantly, “not available today” does not establish that the daemon is an unsuitable replacement design; it only establishes that implementation work would be required.  
   **WHAT WOULD SETTLE IT:** Show the `fnox set` call graph or runtime trace, and evaluate the effort and failure properties of adding a daemon mutation operation rather than dismissing it solely because it is absent.

8. **MAJOR — “Local is mandatory” and “no upstream change can ever reach it” overstate the design constraint.**  
   **Quoted text:** “the local one is not optional,” “no fnox-side lock can ever reach,” and “no upstream change can serialise it.”  
   **Why it fails:** This follows only if the direct Python writer must remain. Other designs could remove that writer, route it through fnox, expose a supported transaction API, or change ownership of the config. The document establishes that the proposed fnox-internal patch alone cannot govern the current raw `Path.write_text()` call—not that a local lock implementation is universally mandatory.  
   **WHAT WOULD SETTLE IT:** State the constraint that the Python direct-write architecture is fixed, or compare elimination/rerouting alternatives and show why they are infeasible.

9. **MAJOR — The “correct pattern” is asserted beyond the properties actually demonstrated.**  
   **Quoted text:** “fnox already ships the correct pattern,” “temp+rename for torn reads: … solved,” and “at `0o600`.”  
   **Why it fails:** The excerpt proves only the intended lock-path rationale. It does not show `FSLock`’s actual platform semantics, whether rename is same-filesystem and atomic under every supported filesystem, crash durability, directory syncing, or error cleanup. `OpenOptions::mode(0o600)` ordinarily controls creation permissions, not necessarily an already-existing stale temp file, so the final file’s mode is not established from the description.  
   **WHAT WOULD SETTLE IT:** Show the complete open/write/flush/rename/error path and `FSLock` implementation or authoritative contract, plus tests for contention, process death, stale temp files, permissions, and crash recovery.

10. **MAJOR — The document claims full elimination despite admitting uncoordinated writers.**  
    **Quoted text:** “mutual exclusion plus atomic replace genuinely eliminates both lost updates and torn reads” versus “Any future writer that does not take the lock is invisible to both lanes.”  
    **Why it fails:** The first claim is true only under an all-writers-cooperate bound. The document has not proved that bound and explicitly says it is unenforced. Atomic replacement can protect readers from partial replacement, but advisory locking cannot eliminate lost updates from bypassing writers.  
    **WHAT WOULD SETTLE IT:** Qualify the claim to cooperating writers and add a mechanism that discovers or blocks bypass writers if system-wide elimination is intended.

11. **MAJOR — The local “minimum fix” does not explicitly cover the stale read it identifies.**  
    **Quoted text:** “read at `:265`, `doppler_list_secrets()` at `:304`, write at `:322`” and “Minimum fix: take the same sidecar lock and write via temp+rename.”  
    **Why it fails:** If “take the lock” occurs only around the final write, the network-spanning stale read remains and the lost update persists. The document never states the acquisition point or lock lifetime, despite that being the central correctness requirement.  
    **WHAT WOULD SETTLE IT:** Require acquisition before `_read_existing_config` and retention through the successful rename, with a test that blocks a competing fnox mutation during that entire interval.

12. **MAJOR — The rejection of CAS does not follow from the reasons supplied.**  
    **Quoted text:** “It would also need a version field the TOML schema has not got.”  
    **Why it fails:** CAS need not use an embedded schema field; it can compare content hashes, file identity, metadata, or a sidecar generation. The absence of a TOML version field therefore does not rule it out. Single-host locking may still be the simpler choice, but that comparative conclusion is asserted rather than demonstrated.  
    **WHAT WOULD SETTLE IT:** Compare concrete CAS implementations and failure modes against the proposed lock, then reject them on measured complexity or unmet requirements.

13. **MINOR — Appending `.lock` does not resolve the collision or identity problem claimed.**  
    **Quoted text:** “`with_extension("lock")` … risks colliding with a real user file; the upstream patch should append.”  
    **Why it fails:** `config.toml.lock` can also collide with a real file. Moreover, deriving locks from path strings can yield different sentinels for symlinked, relative, case-varied, or otherwise aliased paths to the same target.  
    **WHAT WOULD SETTLE IT:** Define the sidecar namespace as reserved, specify canonical path resolution and symlink policy, and test that all supported path spellings converge on one lock.

14. **MINOR — The devcontainer exclusion is asserted rather than demonstrated.**  
    **Quoted text:** “The devcontainer is not a cross-boundary concern for this file.”  
    **Why it fails:** Separate home volumes do not prove that the host file is never bind-mounted, forwarded, regenerated, or accessed through another configured path. The conclusion depends on runtime configuration not shown in the document.  
    **WHAT WOULD SETTLE IT:** Provide the relevant mount/config inventory or qualify the statement to the currently inspected configuration.

**Overall verdict: needs-attention.** The sidecar-lock direction is plausible, but the receipt does not yet prove that either proposed guard encloses complete transactions, that the two languages’ locks interoperate, or that its writer inventory and incident claims are sound.