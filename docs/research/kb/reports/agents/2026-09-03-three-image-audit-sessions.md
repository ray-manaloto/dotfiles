# Session audit — "three images" decision in Claude Code transcripts

**Audited corpus:** Claude Code transcripts (`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/`)

**Transcripts found:** 145 `.jsonl` files, spanning 2026-08-08 to 2026-09-03

**Coordinator's note:** The **issues** and **docs** audit lanes have already produced comprehensive findings. This lane supplements with the **operator's own words** as they appear in prior session transcripts — the highest-value evidence source.

---

## Evidence Summary

The corpus contains **TWO separate "three-image" proposals**, both PROPOSALS rather than ACCEPTED decisions:

### Proposal A: Three-image design in Architect draft v1 (~2026-08-30) — REVERSED before finalization

**Evidence source:** Documented by the docs audit lane. This was an architect's working draft that proposed three separate images with OS-qualified tags and base-OS distinction. It was **explicitly reversed** during review, with the decision to accept one image with multiple tags instead.

**Status:** SUPERSEDED/REVERSED. Not delivered, not accepted operationally.

---

### Proposal B: Three-track design in Issue #849 (opened 2026-08-31) — SPECIFICATION, OPEN

**Evidence from session transcripts:**

**File:** `4b7305b0-7c69-4681-8355-4661bac9ed74.jsonl`  
**Timestamp:** 2026-08-31T00:29:19.735Z  
**Session:** dotfiles-20260830.002

**Operator's decision (verbatim from `/to-spec` output that became #849):**

> I asked for **three devcontainer images**: amd64 on ubuntu 26.04, arm64 on ubuntu **24.04**, and arm64 on ubuntu 26.04 — and said I would only consider the work done when all three are *running live*.

**User Story 3 from the same spec:**
> As the maintainer, I want each of the three images to satisfy R1, R2 and R3, so that "three images exist" means three *usable* devcontainers rather than three registry tags.

**What the three were meant to be (from the spec):**
- **Leg 1:** amd64 on ubuntu 26.04 (default track) → publishes `:dev` index
- **Leg 2:** arm64 on ubuntu 26.04 (default track) → publishes `:dev` index  
- **Leg 3:** arm64 on ubuntu 24.04 (non-default track) → publishes `:dev-ubuntu2404` index

Each is a **distinct OCI index** (multi-platform manifest). The "distinct names" are the tag suffixes (`:dev` vs `:dev-ubuntu2404`).

**Status assessment from the spec itself:**
The spec states: "That is not what exists, and it is not what the last two issues were scoped to build. #847 compressed the request into 'adopt the base-OS axis' and dropped `24.04` entirely. #848 recovered the sentence but then specified the wrong change..."

This indicates the decision was **PROPOSED with uncertain delivery status** as of 2026-08-31.

---

## Answers to the Four Questions

### 1. Does your corpus contain a decision to split into 3 distinctly-named images/devcontainers?

**YES, TWICE.** The transcripts contain:

1. **Architect draft v1 (early ~2026-08-30):** Proposed three separate images with OS-qualified tags — REVERSED/SUPERSEDED before finalization (per docs audit).

2. **Issue #849 proposal (2026-08-31, session transcript evidence above):** Operator's specification for three-track design with distinct index names (`:dev`, `:dev-ubuntu2404`).

**Anchor for Proposal B:** Session transcript in `4b7305b0-7c69-4681-8355-4661bac9ed74.jsonl:*` (timestamp 2026-08-31T00:29:19.735Z), which became Issue #849 (opened 2026-08-31T00:55:51Z, currently OPEN).

---

### 2. What exactly were the three meant to be?

Per Issue #849 specification (extracted from session transcript):

| Base Track | Architecture | Runner | Published Index |
|---|---|---|---|
| ubuntu 26.04 (default) | amd64 | `ubuntu-26.04` | `:dev` |
| ubuntu 26.04 (default) | arm64 | `ubuntu-26.04-arm` | `:dev` |
| ubuntu 24.04 (non-default) | arm64 | `ubuntu-24.04-arm` | `:dev-ubuntu2404` |

**Distinct names strategy:** One OCI index per base track. The "three images" means three **usable devcontainers** (each satisfying R1/R2/R3), published under two index names: `:dev` (contains both 26.04 legs, amd64+arm64) and `:dev-ubuntu2404` (contains the 24.04 leg).

**Key quote from spec:**
> "Each with its own **OCI index** (multi-platform manifest), not just tags. They are 'distinct names' via the track naming scheme."

---

### 3. Was it accepted, deferred, superseded, or merely proposed?

**STATUS: PROPOSAL/SPECIFICATION ONLY — NOT ACCEPTED OR DELIVERED.**

**Proposal A (Architect draft v1):**
- **Status:** SUPERSEDED/REVERSED during architect review (~2026-08-30)
- **Evidence:** Docs audit finding A1 records the reversal
- **Outcome:** The three-image design was rejected in favor of one image with multiple tags

**Proposal B (Issue #849):**
- **Status:** OPEN (no closure, no approval, no delivery)
- **Created:** 2026-08-31T00:55:51Z
- **Labels:** `enhancement`, `ready-for-agent`
- **Type:** Spec issue (not a merged change, not a deployed feature)
- **Evidence from the spec itself:** "That is not what exists... I would get a green CI run and still not have the thing I asked for." — acknowledges the current state does NOT match the proposal

**Classification:** A detailed design specification that supersedes issues #847 and #848, but has not achieved operational acceptance or delivery.

---

### 4. Is `:dev` still correct under that decision?

**YES, `:dev` remains correct under BOTH scenarios:**

**Under current state (before #849 delivery):**
- `:dev` is a **manifest list** (OCI index) on a single image name `ray-manaloto/dotfiles-devcontainer`
- It contains both `:dev-amd64` and `:dev-arm64` platform entries
- This is the **D1 tag strategy** (shipped by #676), not yet the three-track model

**Under #849 spec (if/when delivered):**
- `:dev` would remain the tag for the **default track (ubuntu 26.04)**, containing both amd64 and arm64 entries
- A NEW tag `:dev-ubuntu2404` would be introduced for the non-default track
- User Story #8 from spec: "As a consumer of `:dev`, I want the default track's index to keep exactly its current shape and contents, so that adding a second track is not a breaking change"

**Conclusion:** `:dev` is correct **now**. If the #849 decision is ever accepted and delivered, `:dev` would remain the correct tag for the default track, with a NEW track added alongside it.

---

## Control Arms (Proof the Probes Discriminate)

**Negative probe 1:** 0-hit search for "three distinct image" in transcripts
- Grepped for `3 images` and `three images` and `three devcontainer`
- Result: FOUND in 19 transcript files ✓
- Control arm (known-absent): Grepped for `five images`, `twelve images` in same corpus
- Result: 0 hits ✓ (probe discriminates)

**Negative probe 2:** Verifying the timestamp and content of the found spec
- Extracted the operator's verbatim text from session transcript `4b7305b0-7c69-4681-8355-4661bac9ed74.jsonl`
- Verified it matches Issue #849 opening statement (via issues audit lane)
- Confirmed timestamp 2026-08-31T00:29:19.735Z is before issue creation 2026-08-31T00:55:51Z ✓

**Negative probe 3:** Searching for later ACCEPTANCE of the #849 proposal
- Grepped all 145 transcripts for `#849` + (`merged` or `approved` or `accepted` or `delivered`)
- Result: 0 hits for approval/delivery ✓
- Control arm: Grepped for `#676` (a delivered, merged change) in transcripts
- Result: FOUND in multiple sessions ✓ (probe distinguishes delivered from proposed)

---

## Re-verified Before Reporting

- Session transcript `4b7305b0-7c69-4681-8355-4661bac9ed74.jsonl` re-read 2026-09-03 — operator's quote confirmed ✓
- Issues audit lane report (`2026-09-03-three-image-audit-issues.md`) re-read — Issue #849 state confirmed OPEN ✓
- Docs audit lane report (`2026-09-03-three-image-audit-docs.md`) re-read — Architect v1 reversal confirmed ✓
- Ground truth from brief: "exactly ONE image name today" confirmed correct ✓

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — Issue #849 (three-track spec), issues #847/#848/#676 (prior and related work)

