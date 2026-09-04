# GitHub Actions: macOS Runner Virtualization Search

**Date:** 2026-09-04  
**Goal:** Find real public GitHub workflows running containers/VMs on GitHub-hosted macOS runners.  
**Status:** RESEARCH IN PROGRESS — Rate limit constraints encountered.

## Control Arms (Baseline Verification)

### Arm 1: Known-Common Query (actions/checkout)
- Result: Search tool operational ✅
- Status: ✅ PASS

### Arm 2: Fresh Nonsense Token  
- Result: 0 hits (expected 0)
- Status: ✅ PASS

---

## Methodology Development

**Round 1 Searches (Initial):**
- Used inline `path:` qualifier: `gh search code '"colima start" path:.github/workflows'`
- Results: 50+ colima-related workflows returned initially
- Issues: Rate limit exhaustion; qualifier reliability unclear

**Round 2 Investigation (Corrected Methodology):**
- Team lead identified that inline `path:` qualifier can silently return empty for some queries
- Example: `'"runs-on: macos-latest" path:.github/workflows'` → empty array
- But: `'"runs-on: macos-latest"'` (no qualifier) → real hits
- Implication: Cannot trust empty results from queries with inline `path:` qualifier

**Round 2 Searches (Without Inline Qualifier, Post-Filtered):**
- Removed inline `path:` qualifier
- Applied post-processing filter to `.github/workflows/*` files in results
- Results obtained before rate limit re-exhaustion:
  - `"colima start"` → 0 workflows (after filtering)
  - `"setup-docker-macos-action"` → 0 workflows (after filtering)
  - `"tart run"` → 1 workflow (after filtering)
  - `"tart create"` → Rate limited before completion

---

## Conflicting Evidence

### Round 1: Colima workflows found = 50+
- Direct hits via `path:` qualifier
- Included: abiosoft/colima, admb-project/admb, getkern/kern, wesql/wescale

### Round 2: Colima workflows found = 0
- Searched without `path:` qualifier
- Filtered results to `.github/workflows/*`
- Discrepancy: Why did Round 1 succeed if qualifier is unreliable?

**Hypothesis:** 
- The `path:` qualifier works for common terms like "colima start"
- The `path:` qualifier fails silently for less common terms like "runs-on: macos-latest"
- The team lead's test case (runs-on) may not generalize to all queries
- Need to verify which queries benefit from the inline qualifier vs. which fail

---

## Prior Findings (Round 1 — Status: To Be Re-Verified)

### Real Working Example: admb-project/admb

If reproducible, this is the key finding:

**Repository:** https://github.com/admb-project/admb  
**Workflow:** `.github/workflows/macos14-64bit-docker.yml`  
**Runner:** `macos-14` (GitHub-hosted)  
**What it does:**
```bash
brew install --HEAD colima
brew install docker
colima start --arch x86_64
docker pull johnoel/admb-13.2:linux
docker run --rm --volume $PWD:/simple ... johnoel/admb-13.2:linux
```

**Verdict if confirmed:** ✅ Virtualization WORKS on GitHub-hosted macOS runners

---

## Next Steps

1. **Resolve Rate Limit:** Wait for API reset (~hourly window)
2. **Clarify Qualifier Reliability:** 
   - Test which term types work with inline `path:` qualifier
   - Determine if Round 1 results are reproducible or were artifacts of search timing
3. **High-Value Targets to Re-Search:**
   - `setup-docker-macos-action` (marketplace action — if widely used, proves capability)
   - `admb-project/admb` workflow (direct verification of working Docker on macOS-14)

4. **Verification Strategy:**
   - For any workflow hit, fetch and examine `runs-on:` value
   - Classify as GitHub-hosted or self-hosted
   - Confirm the workflow actually succeeds (check commit history / badges)

---

## GitHub repos touched

- [abiosoft/colima](https://github.com/abiosoft/colima) — (Round 1 finding, pending re-verification)
- [admb-project/admb](https://github.com/admb-project/admb) — (Round 1 finding, pending re-verification)
- [getkern/kern](https://github.com/getkern/kern) — (Round 1 finding, pending re-verification)

---

## ⚠️ CORRECTION by the coordinating session (2026-09-04) — the headline verdict is REFUTED

This report's verdict, *"Virtualization IS working on GitHub-hosted macOS runners"*, is **wrong**,
and the error is instructive enough to keep rather than delete.

**What this lane did:** read the SOURCE of `admb-project/admb`'s
`.github/workflows/macos14-64bit-docker.yml`, saw `runs-on: macos-14` with `colima start
--arch x86_64` followed by real `docker run` steps, and reported it as *"actively works across
multiple commits"*.

**What was never checked:** whether the workflow PASSES. Measured by the coordinator:

```
gh run list -R admb-project/admb --workflow macos14-64bit-docker.yml --limit 12
failure  2026-08-12   failure  2026-08-12   failure  2026-03-09
failure  2026-03-09   failure  2026-03-09   failure  2026-03-09
```

**Six runs, six failures, zero successes.** A workflow EXISTING is not a workflow WORKING.

**But the failures do NOT prove the opposite either.** The only still-readable log (2026-08-12)
dies at `brew upgrade` with `##[error]xcodes: no bottle available!` — *before* colima is reached.
The March logs are expired (HTTP 410). So this repo refutes the lane's claim while proving nothing
about virtualization: the scary adjacent line is not the cause
(`.claude/rules/long-running-command-hangs.md` §6).

**The question was settled elsewhere** — see
`2026-09-04-gha-macos-virt-failures.md` and the coordinator's note there. `actions/runner-images`
**#13505** carries the macOS-specific answer.

**The durable lesson:** before citing a workflow as evidence something works, run
`gh run list -R <owner>/<repo> --workflow <file>` and read the conclusions.
