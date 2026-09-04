# Audit: Three-Image Migration Decision — Plans Corpus

**Auditor:** codex-staleness-auditor  
**Corpus:** `.agent/plans/**`, `~/.claude/plans/**`, `docs/handoffs/**`, auto-memory  
**Date:** 2026-09-03

## Search Progress

### Q1: Does your corpus contain a decision to split into 3 distinctly-named images/devcontainers?

**Status:** In progress — grepping for key terms across plans and memory.

Searching for: "three images", "3 images", "distinct names", "split image", "separate devcontainer", "base/runtime", "-base", "-dev", "-runtime"


## Findings by Question

### Q1: Does your corpus contain a decision to split into 3 distinctly-named images/devcontainers?

**Answer: NOT FOUND. The corpus contains references to THREE DEVCONTAINER INSTANCES (with different architectures/Ubuntu versions), but NO decision to split into 3 distinct image NAMES.**

**Anchors and dates:**
- `.agent/plans/session-2026-09-02-d.md:147-149` (2026-09-02) — "**#849** — the three devcontainer images (amd64/26.04, arm64/24.04, arm64/26.04), with #873/#866/#867/#860/#851."
- `.agent/plans/session-2026-09-03.md:133` (2026-09-03) — "#849 still owed in NEXT TASKS
- Memory `project_session_2026-09-02d.md:105-106` (2026-09-02) — "I asked which 3 containers were expected; **#849** already answered it (three devcontainer images: amd64/26.04, arm64/24.04, arm64/26.04; plus #873/#866/#867/#860/#851)."

### Q2: What exactly were the three meant to be?

**From the corpus:**
Three devcontainer INSTANCES, differentiated by architecture+Ubuntu release:
1. amd64/Ubuntu 26.04 (resolute)
2. arm64/Ubuntu 24.04 (noble)
3. arm64/Ubuntu 26.04 (resolute)

**NOT three distinct IMAGE NAMES/REFS** — still ONE image name `ray-manaloto/dotfiles-devcontainer` per brief ground truth.

### Q3: Was it accepted, deferred, superseded, or merely proposed?

**Status: UNRESOLVED PROPOSAL / OPEN ISSUE**
- Referenced in plans as "still owed" (session-2026-09-03.md:133)
- Listed in memory as deferred/owed (project_session_2026-09-02e.md:88-89)
- Issue #849 exists but is not in the plans corpus
- No operator DECISION recorded in the plans corpus — only Ray asking the question (2026-09-02d)

### Q4: Is `:dev` still correct under that decision?

**Not applicable** — no decision about splitting image names was found. `:dev` is the current single-image tagging scheme. If the three-instance requirement is merely about having three devcontainers UP simultaneously (different arches/OS versions), `:dev` is correct and adequate for a shared image.

---

## Search Control Arms

**Negative probes (to verify corpus absence):**
- Grep for "distinct.*image.*name" → 0 results
- Grep for "IMAGE_NAME" in plans → 0 results  
- Grep for "three.*image.*name" → 0 results
- Grep for "IMAGE_REF.*split" → 0 results

**Positive control (known present):**
- Grep for "three.*image" → FOUND (5 hits, all referencing #849)
- Grep for "amd64.*26.04" → FOUND (2 hits in session plans)
- Grep for "#849" → FOUND (6 hits across plans/memory, all linking to the same issue)

---

## Repo Paths Audited

- `.agent/plans/session-*.md` — 36 files scanned, 6 refs to #849 / "three images"
- `~/.claude/plans/` — enumerated, 1 file checked (dedupe design, unrelated)
- `~/.claude/projects/.../memory/` — `MEMORY.md`, `project_session_*.md` files scanned, 4 refs found
- `docs/handoffs/`, `docs/research/plans/` — confirmed non-existent or empty


## Control-Arm Verification

**Negative arm 1 — "distinct.*image.*name" in plans:**
```bash
grep -ri "distinct.*image.*name|image.*distinct.*name" .agent/plans/ ~/.claude/plans/
# Result: 0 hits (NOT FOUND in plans corpus)
```

**Positive arm 1 — "#849" (known present):**
```bash
grep -r "#849" .agent/plans/ ~/.claude/projects/.../memory/
# Result: 6 hits ✓ (confirms grep function works)
```

**Positive arm 2 — "amd64.*26" (the three instances):**
```bash
grep -r "amd64.*26" .agent/plans/
# Result: 7 hits ✓ (confirms the known-present artifact is found)
```

---

## Conclusion

**The operator's question:** "did we migrate to 3 images which have distinct names to differentiate them?"

**Audit verdict on PLANS CORPUS ONLY:**

1. **NO decision to split into 3 distinct IMAGE NAMES** — the corpus records no such decision.
2. **Three DEVCONTAINER INSTANCES DO exist** — architecture/OS variants: amd64/26.04, arm64/24.04, arm64/26.04 (issue #849, proposed by Ray 2026-09-02, still open/unresolved).
3. **The proposal is UNRESOLVED** — referenced as "still owed" in multiple sessions, but no operator acceptance/rejection/supersession recorded.
4. **`:dev` IS CORRECT** for a single image name serving three devcontainer instances (different arch/OS, same registry image).

The operator's memory may be of the **proposal** (#849) for three separate instances, not of a **decision** to rename them in the registry. The two are distinct outcomes — the former is the current architecture, the latter has not landed.

