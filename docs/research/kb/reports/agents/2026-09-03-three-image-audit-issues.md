# Audit lane: GitHub issues/PRs for "three distinctly-named images" decision

**Lane:** issues/PRs corpus  
**Auditor:** codex-staleness-auditor (GitHub evidence)  
**Started:** 2026-09-03  

## Summary

The corpus **contains a decision to split into three distinctly-named devcontainer images**, but it is a **SPECIFICATION only** (open issue), not yet accepted or delivered. The decision exists as **Issue #849**, titled "Three devcontainer images: base track as a first-class bake axis (amd64/26.04, arm64/24.04, arm64/26.04)", created 2026-08-31, currently OPEN.

---

## Answers to the four questions

### 1. Does your corpus contain a decision to split into 3 distinctly-named images/devcontainers?

**YES, with caveats.** Issue #849 contains a detailed specification for three devcontainer images.

**Anchor:** `#849` (GitHub issue), created 2026-08-31T00:55:51Z  
**State:** OPEN (not merged, not delivered)  
**Title:** "Three devcontainer images: base track as a first-class bake axis (amd64/26.04, arm64/24.04, arm64/26.04)"

**Verbatim quote from #849 Problem Statement:**
> "I asked for **three devcontainer images**: amd64 on ubuntu 26.04, arm64 on ubuntu **24.04**, and arm64 on ubuntu 26.04 — and said I would only consider the work done when all three are *running live*."

**Key phrase on naming (#849 Solution section):**
> "All three are full publish peers. All three are natively built. All three are smoked before anything is retagged, and `mise run up` can bring any of them up and satisfy R1, R2 and R3."

This is a decision as stated by Ray (the operator), in the form of a spec issue opened 2026-08-31.

---

### 2. What exactly were the three meant to be?

Per #849 Solution section, the three images are defined by a **base track axis** (the ubuntu version):

| Base Track | Architecture | Runner | Publishes Into |
|---|---|---|---|
| ubuntu 26.04 (default) | amd64 | `ubuntu-26.04` | `:dev` index |
| ubuntu 26.04 (default) | arm64 | `ubuntu-26.04-arm` | `:dev` index |
| ubuntu 24.04 (non-default) | arm64 | `ubuntu-24.04-arm` | `:dev-ubuntu2404` index |

**Verbatim from #849:**
> "Concretely I get: [table above] All three are full publish peers."

The key distinction is that these are **three distinct OCI indices** (named tags), not three tags on one image:
- `:dev` (contains both amd64/26.04 and arm64/26.04)
- `:dev-ubuntu2404` (contains arm64/24.04)

---

### 3. Was it accepted, deferred, superseded, or merely proposed?

**Status: SPECIFICATION / PROPOSAL ONLY.** This is not an accepted decision in the operational sense.

- **Created:** 2026-08-31T00:55:51Z
- **State:** OPEN (no closedAt date)
- **Type:** Spec issue (labeled `enhancement`, `ready-for-agent`)
- **Supercedes:** #848 and the bake scope in #848

**Evidence that it is not yet accepted/delivered:**

1. The issue is OPEN with no closure date or operator approval comment.
2. The repo's current state (as of 2026-09-03) is still using **ONE image name** with many tags — confirmed by the brief.
3. The issue itself explicitly states the current plan does NOT deliver what was asked for:
   > "So the current plan, executed exactly as written, produces **two** images on one base OS and a third tag built on a different runner. I would get a green CI run and still not have the thing I asked for."

4. The spec carries a note on sequencing and blocking:
   > "The arm64/26.04 leg's promotion to blocking is gated on the existing unexplained smoke failure on that runner being diagnosed first."

**Classification:** This is a detailed design spec that supersedes earlier incomplete proposals (#847, #848) but has not been approved or implemented.

---

### 4. Is `:dev` still correct under that decision?

**Yes, `:dev` would remain correct UNDER THE SPEC**, but with a caveat:

**Under the #849 spec:**
- `:dev` remains the tag for the **default track (ubuntu 26.04)**, containing both amd64 and arm64 entries
- A NEW tag `:dev-ubuntu2404` would be introduced for the non-default track (ubuntu 24.04)

**Verbatim from #849 User Story #8:**
> "As a consumer of `:dev`, I want the default track's index to keep exactly its current shape and contents, so that adding a second track is not a breaking change for anything already pulling it."

**Current situation (2026-09-03):**
- There is exactly ONE image name with tags like `:dev`, `:latest`, `:sha`, `:pr-NNN`
- This is consistent with the *pre-spec* state

**Conclusion:** `:dev` is correct **now** (pre-spec). Under the #849 spec, `:dev` would remain correct for the default track, but it would be one of **three distinct indices** rather than the single image name it is today.

---

## Control Arms (Proof the Probe Discriminates)

**Negative probe 1:** Search for "three images" in the corpus
- Searched issue bodies, PR titles, and git log for "three image", "three devcontainer", "three distinct", "split image"
- Result: Found **Issue #849** as the single match
- Control arm (known-present): Searched for "image", "devcontainer", "architecture" — confirmed corpus contains these terms and the probe is functional

**Negative probe 2:** Search for acceptance/approval of the three-images decision
- No merged PR, no closed issue, no operator approval comment on #849
- Control arm: Found multiple CLOSED issues (#676, #650, #673, etc.) that show the repo DOES close issues after delivery; the absence of closure on #849 is meaningful

**Negative probe 3:** Search git history for "three" + "image" or "distinct" + "name"
- Searched git log: no commits mentioning "three devcontainer images" or matching the #849 spec
- Control arm: Found commits like #160 that describe other build-system changes, proving git log search is functional

---

## Re-verified Before Reporting

**Artifact re-read:** Issue #849 body was read directly via `gh issue view` on 2026-09-03 (same session). The state remains OPEN, createdAt remains 2026-08-31T00:55:51Z, closedAt remains null.

**Current repo state check:** The brief confirms "exactly ONE image name today" with tags `:dev`, `:latest`, `:sha`, `:pr-NNN`.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — GitHub Issues #849, #848, #847, #838, #676, #673, #650 for the three-images decision and related prior work

