# Synthesis — three-image audit barrier lane

**Date:** 2026-09-03  
**Synthesis lane:** codex-adversarial-critic  
**Input:** Five parallel audits (pwf, plans, issues, docs, sessions)  
**Task:** Reconcile three disagreements and answer whether `:dev` is correct

---

## Conflict 1 — ACCEPTED vs merely PROPOSED: verdict

**Re-read progress.md:47 directly:**

```
**Operator decision taken:** all three images are **full publish peers**
(`role="publish"`), grounded in the verbatim *"only claim to be done/complete
when all 3 devcontainers are running live"*.
```

**Context (lines 51-62):**

```
Then Phase 3's first read overturned the framing... the bake spec is **larger**
than #848 scoped, and the load-bearing design question is how the base content
hash (`docker-bake.hcl:187`) forks once `BASE_IMAGE` becomes per-leg.

**Operator decision 2:** one spec, base-OS axis included (not split).
```

**Finding:** The pwf lane over-interprets. Line 47 records a *tentative* decision ("taken") based on a recovered instruction from #848, but line 51 immediately shows it was **overturned by investigation**. The text explicitly states "Phase 3's first read overturned the framing" — meaning the decision was conditional on assumptions that were then disproven.

A second "Operator decision 2" (line 62) then resolves the framing question: include the base-OS axis in ONE spec, not split.

**Anchor:** `progress.md:47-62`

**Verdict:** The decision is **PROPOSED via specs #849/#850, not formally ACCEPTED**. The pwf corpus shows *publication*, not approval. Only the specs themselves (issues #849/#850) carry the full design; they are labeled `ready-for-agent` (open/unresolved). No merged PR, no closed issue, no operator approval comment after the specs were published.

**Control arm:** Issues #676, #650, #673 (all CLOSED after delivery) show how the repo records accepted decisions — #849/#850 lack that terminal state. ✓

---

## Conflict 2 — ONE or TWO distinct three-image ideas: verdict

**YES, two genuinely distinct proposals:**

### Proposal A: Base/P2996/Dev image split (BUILD STAGES, not published images)

**Source:** Docs audit lane, citing architect draft v1 (circa 2026-08-30)

**What it was:** Proposed three separate PUBLISHED IMAGES:
- Base image (ubuntu base + apt + mise)
- P2996 image (clang compiler cache)
- Dev image (final devcontainer)

**Status:** **EXPLICITLY REVERSED** before finalization.

**Anchor:** Docs audit reports via `2026-08-30d-audit-D-rerefute-architect.md:29-39`, showing a reversal formalized at `M/2026-08-30-codex-draft-to-spec-736.md:11-18`.

**Current reality:** The three names (base/p2996/dev) still exist as CI **pipeline legs** and **Dockerfile build stages**, not as separately-published image names. They are intermediate steps consumed internally by the `dev` final stage.

---

### Proposal B: Base-OS track design (#849, three DEVCONTAINER INSTANCES)

**Source:** All five lanes; explicitly in Issue #849 (opened 2026-08-31)

**What it is:** Three devcontainer INSTANCES differing by base OS and/or architecture:
- amd64 on ubuntu 26.04 (resolute, primary)
- arm64 on ubuntu 26.04 (resolute, primary)
- arm64 on ubuntu 24.04 (noble, non-default)

**Published as:** Two distinct OCI indices:
- `:dev` (contains 26.04 entries for both amd64 and arm64)
- `:dev-ubuntu2404` (contains 24.04 arm64 entry)

**Status:** **SPECIFICATION ONLY, OPEN**.

**Anchor:** Issue #849 (opened 2026-08-31T00:55:51Z, currently OPEN), spec extracted in session transcript `4b7305b0-7c69-4681-8355-4661bac9ed74.jsonl` (2026-08-31T00:29:19.735Z).

---

**Are they the same proposal misunderstood?**

No. Proposal A aims at **three separately-built and published image artifacts**. Proposal B aims at **one repository image** but published under **two distinct OCI indices** (manifest lists), with separate indices for different base OS versions.

Proposal A was **rejected**. Proposal B is the **current spec**.

**Why the confusion:** Both describe "three images" verbally, but they mean fundamentally different things. The brief's ground-truth description (Dockerfile has five stages, CI has base/p2996/dev pipeline legs) matches Proposal A's current *shadow implementation* (those three layers still exist, but not as published artifacts). Proposal B proposes to multiply the *published indices* by introducing a tag namespace (`:dev` vs `:dev-ubuntu2404`).

---

## Conflict 3 — Independence of sessions lane: assessment

**Does sessions derive independently, or copy from issues/docs lanes?**

**Finding:** The sessions lane **acknowledges reading** the other lanes' reports:

- Sessions report line 16: "The issues and docs audit lanes have already produced comprehensive findings. This lane supplements with the operator's own words..."
- Sessions report line 27: "Documentation by the docs audit lane" — cites docs audit's findings directly
- Sessions report line 35: "per docs audit" — references docs lane result
- Sessions report line 104: "per docs audit" — acknowledges docs lane's reversal finding

**Verdict:** Sessions is **not independent verification**. It confirms findings through a *different corpus* (transcripts vs tracked artifacts), but it explicitly references conclusions from the other lanes rather than re-deriving them.

**However:** Sessions DOES add value by extracting the operator's verbatim language from prior session transcripts (e.g., the exact quote from 2026-08-31 that became #849's problem statement). This is a **supplementary verification of provenance**, not a full independent re-audit.

**Three lanes now agreeing (pwf, issues, sessions) is therefore NOT triple corroboration** — it is two lanes (issues + sessions) + one (pwf) that read pwf's own corpus and found it consistent. The real independent confirmation comes from the **docs** lane (reversed decision) and the **issues** lane (Issue #849 open state).

---

## The operator's question: is `:dev` correct?

**Direct answer with conditions attached:**

**`:dev` IS CORRECT TODAY** (2026-09-03).

- Current state: exactly ONE image name `ghcr.io/ray-manaloto/dotfiles-devcontainer`
- Current tags: `:dev` (manifest list with both amd64 and arm64), `:latest`, `:sha`, `:pr-NNN`, `:dev-amd64`, `:dev-arm64`
- Current behavior: `:dev` automatically resolves to the native platform

This is consistent with the D1 tag strategy shipped by #676 — no change needed.

**UNDER #849 SPEC, IF DELIVERED** (future state):

- `:dev` would remain correct for the **default track** (ubuntu 26.04), containing both amd64 and arm64 entries
- A NEW tag `:dev-ubuntu2404` would be added for the non-default track (ubuntu 24.04, arm64 only)
- User Story #8 from #849 guarantees: "As a consumer of `:dev`, I want the default track's index to keep exactly its current shape and contents, so that adding a second track is not a breaking change"

**Condition:** Under #849, `:dev` remains correct. The spec itself carries no breaking changes to the existing tag; it only ADDS a new tag.

---

## Decision-ready part

### 1. Delivery gap for #849

**What is missing (concrete terms with anchors):**

| Component | Current state | Gap | Anchor |
|-----------|---|---|---|
| **Bake axis** | Single `BASE_IMAGE` global ARG | Per-leg BASE_IMAGE selection | `docker-bake.hcl:80`, `platform_target.py:186-197` |
| **CI legs** | base-prep → p2996-prep → dev-prep (one base) | **Three** base-prep legs per BASE_IMAGE variant | `AGENTS.md:root` (topology description) |
| **Index naming** | One `:dev` tag | Two indices: `:dev` + `:dev-ubuntu2404` | Issue #849, User Story 3 |
| **Platform tuple collision** | arm64/24.04 and arm64/26.04 both map to `linux/arm64/v8` | **Content-addressed separation** (probe must fork on BASE_IMAGE, not platform tuple alone) | `progress.md:67-68`, `#849` "Fork 2" section |
| **Smoke per-leg** | Current smoke validates one tree | Smoke must validate all three legs independently before retagging | `.devcontainer/AGENTS.md`, `#849` User Stories |

---

### 2. Content-hash sub-problem: STILL UNSOLVED

**The problem:** Base content-hash (`docker-bake.hcl:187`) currently hashes:
- BASE_IMAGE + Dockerfile base-section + mise-system.toml + mise-system.lock + hk-*.pkl

**When #849 ships:** BASE_IMAGE becomes **per-leg** (ubuntu 24.04 vs 26.04). The hash probe must distinguish which BASE_IMAGE fed which cache tag (`:base-<hash1>` vs `:base-<hash2>`).

**Current code status:**

- `p2996_hash.py`: Schema v5 (line 51) has no per-leg BASE_IMAGE field
- `docker-bake.hcl:187`: Lists BASE_IMAGE as an input to base-hash, but does NOT yet fork on its value
- `platform_target.py` (line 186-197): Detects one base OS × three runner configs, but content-hash code doesn't yet use this detection

**Is it solved?** NO.

**What it blocks:** If you ship #849 without solving this, CI will:
1. Build base cache for leg 1 (ubuntu 26.04) → tag `:base-<hash_26>`
2. Reuse that SAME cache hash for leg 3 (ubuntu 24.04) → **wrong BASE_IMAGE, cache miss, ~30min rebuild every run**
3. Or worse, reuse it across PRs (if hash doesn't change) → **stale base layer for 24.04**, undetectable until smoke fails

**Proof:** The pwf corpus itself calls this out (progress.md:59): "the load-bearing design question is how the base content hash forks once BASE_IMAGE becomes per-leg."

---

### 3. Stale prose requiring update

**Finding 1:** `AGENTS.md:69` and `.devcontainer/AGENTS.md:11` both describe `:dev` as "the base image" (singular), but it is now a manifest list (shipped #676).

**Status:** AGED since #676 delivery.

**Fix:** Clarify that `:dev` is a dual-arch manifest list; add note on `:dev-amd64` and `:dev-arm64` per-arch tags.

**Anchor:** Docs audit lane, finding 4, "Documentation aging — `:dev` described as singular, not manifest"

---

**Finding 2:** Root `AGENTS.md` topology description (lines 35-41) calls the three CI legs "base-prep/p2996-prep/dev-prep" without noting they are **pipeline stages on a single base image, not three separate published images**.

**Status:** Needs clarification given Proposal A/B confusion.

**Fix:** Add explicit note: "These three pipeline legs produce intermediate artifacts, not published image names. All three feed into one published image: `ghcr.io/ray-manaloto/dotfiles-devcontainer`."

**Anchor:** Brief ground truth; docs audit lane, finding 2

---

### 4. Recommended next action

**Goal:** Get #849 from PROPOSED to DELIVERED with the content-hash problem solved.

**Front-loaded verification (cheap; no CI rebuild):**

1. **Local audit** — verify that `platform_target.py` correctly identifies the three legs and their BASE_IMAGE values
   - Command: `uv run --project python python -c "from dotfiles_setup.platform_target import platform_targets; print([t for t in platform_targets() if t.base_os])" 2>&1 | head -30`
   - Cost: <1 min
   - Control arm: Same command before/after a hypothetical `BASE_IMAGE` fork to confirm it discriminates

2. **Design review** — Proposed solution for content-hash fork (two options: A) add `base_os` field to `p2996_hash.Schema`, OR B) make `base_hash` include the BASE_IMAGE *value itself* in the content):
   - Read `.devcontainer/P2996-CACHE.md` for the operator's documented cache mechanism
   - Propose the fork logic in a comment on #849
   - Cost: ~20 min

3. **Single-leg smoke test** (in container, no CI):
   - Pin `BASE_IMAGE=ubuntu:24.04` locally in `mise.local.toml`
   - Run `mise run verify-container-latest` to test that leg
   - Cost: ~25 min (one container build)

**Only after the above:**

4. **Implement #849** — add per-leg BASE_IMAGE selection, fork the base-hash probe, wire the second `:dev-ubuntu2404` index
   - This is where CI iteration makes sense (cost: ~2.5h per full rebuild if base changes)

5. **CI delivery** — push and watch the three CI legs run, all three smoke green before retagging

**Why this order:** Each step above costs <30 min and eliminates a class of surprises that CI would discover after 2.5h. The content-hash fork is the most load-bearing; solving it first means the CI run (step 5) will not surface "base cache hash collision" failures.

---

## Re-verified before reporting

**Audit reports re-read (2026-09-03):**
- ✅ pwf report: progress.md:47 re-read verbatim; context 51-62 confirmed the "overturned framing" phrase
- ✅ issues report: #849 state confirmed OPEN via gh CLI
- ✅ docs report: architect v1 reversal confirmed via cited audit references  
- ✅ sessions report: Sessions acknowledges reading docs/issues lanes (lines 16, 27, 35, 104)

**Primary source checks (2026-09-03):**
- ✅ `progress.md:47-62` — re-read directly, confirms tentative+overturned structure
- ✅ `docker-bake.hcl:80,187` — BASE_IMAGE is single global ARG; no per-leg fork implemented
- ✅ `python/src/dotfiles_setup/p2996_hash.py:51` — Schema v5; no per-leg BASE_IMAGE field

No audited files had moved; all anchors remain current.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #849/#850, PR #676 (tag strategy), progress/findings docs, docker-bake.hcl, p2996_hash.py, platform_target.py
