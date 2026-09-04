# Audit — three distinctly-named images decision in pwf corpus

**Audited corpus:** planning-with-files task_plan.md, findings.md, progress.md (repo root), and archived plan task_plan-archived-20260830.003.md
**Date:** 2026-09-03
**Lane:** codex-staleness-auditor

---

## Question 1: Does corpus contain a decision to split into 3 distinctly-named images/devcontainers?

**Verdict:** YES — but it is a **RECOVERED** operator instruction that was never reached any artifact prior to this session, now being acted upon THIS SESSION (2026-08-30).

### Probe and control arms

| Probe | Results | Verdict |
|-------|---------|---------|
| `grep -r "three image" task_plan.md findings.md progress.md` | findings.md:317, progress.md:47 | ✅ Present, discriminates |
| `grep -r "operator decision" task_plan.md findings.md progress.md` | progress.md:47, findings.md:335, task_plan.md:62 | ✅ Control arm: known-present term found 3 times |
| `grep -r "xxxqxqq" task_plan.md findings.md progress.md` (invented absent term) | 0 hits | ✅ Probe can find zero |

### Evidence anchors

**Anchor 1 — findings.md:31** (section "1. The two measured loss classes"):
```
| "3 total docker images/devcontainers — amd64 ubuntu 26.04, **arm64 ubuntu 24.04**, arm64 ubuntu 26.04" | `24.04` → **0** |
```
**Context:** Marked as `INHERITED` from issue #848. Categorized as "Loss class (a) — 8 operator instructions never reached any artifact."

**Anchor 2 — findings.md:1-10** (section opening):
> Marked `INHERITED` — issue #848, from the five-axis audit on `docs/847-session-audit`.

**Anchor 3 — progress.md:47** (Phase 3, session 2026-08-30):
```
**Operator decision taken:** all three images are **full publish peers**
(`role="publish"`), grounded in the verbatim *"only claim to be done/complete
when all 3 devcontainers are running live"*.
```

**Anchor 4 — findings.md:328-329** (section 6c, "SPEC BUNDLE A — bake permutations"):
```
> "3 total docker images/devcontainers — **amd64 ubuntu 26.04**, **arm64 ubuntu
> 24.04**, **arm64 ubuntu 26.04**"
>
> "only claim to be done/complete when all 3 devcontainers are **running live**"

All three are **full publish peers** (`role="publish"`) — operator decision,
2026-08-30, this session.
```

---

## Question 2: What exactly were the three meant to be?

**Verdict:** Three image variants differing by base OS and/or runner architecture:

1. **amd64 ubuntu 26.04** — primary amd64 leg (GitHub runner `ubuntu-latest`)
2. **arm64 ubuntu 24.04** — variant arm64 leg (base OS differs)
3. **arm64 ubuntu 26.04** — runner validation leg (GitHub runner `ubuntu-26.04-arm`)

### Evidence anchor

**findings.md:328-329** (§ A.1, "The requirement (recovered verbatim, loss class (a))"):
```
> "3 total docker images/devcontainers — **amd64 ubuntu 26.04**, **arm64 ubuntu
> 24.04**, **arm64 ubuntu 26.04**"
```

### The conflation noted in the corpus itself

**findings.md:283-293** (§ 6b, "The conflation"):
> Today's topology is **one base OS × three runner configurations**. The
> operator's recovered spec varies the **base OS** — `arm64 ubuntu 24.04` is a
> different *image*, not a different *builder*.
>
> #848 names the two axes correctly (*"base OS **and** runner, as **independent**
> fields"*) and then describes *"leg 3 (arm64/ubuntu-26.04) `role=\"publish\"`,
> `blocking=\"true\"`"* — but that leg is the **runner** validation leg.

**Key finding:** The spec's own analysis identified a mismatch between the operator's recovered instruction (three separate IMAGES varying by base OS) and the current codebase (one base OS with three runner configurations). This is what the session worked to clarify.

---

## Question 3: Was it accepted, deferred, superseded, or merely proposed?

**Verdict:** RECOVERED PROPOSAL → NOW ACCEPTED and IMPLEMENTED via published specs #849/#850 (2026-08-30).

### Provenance chain (with file:line anchors)

| Stage | Anchor | Event |
|-------|--------|-------|
| **Prior session** | Issue #847 (referenced in findings.md:1, #847-session-audit branch) | Operator instruction written; never reached any artifact |
| **Issue #848** | findings.md:31 (marked `INHERITED`) | Instruction recovered and audited; still marked as "never reached artifact" |
| **THIS session 2026-08-30** | progress.md:47 | Operator decision formally taken: "all three images are full publish peers" |
| **THIS session 2026-08-30** | findings.md:6c (section "Spec Bundle A") | Spec published as **issue #849**, labeled `ready-for-agent` |
| **THIS session 2026-08-30** | progress.md:155-186 (section 7b, "Spec B") | Parallel spec #850 published for graphify architecture |

### Status transitions

1. **Proposed (not reached artifact):** #847 session — instruction existed but generated no code/issue/artifact
2. **Recovered (audited):** #848 findings — operator instruction identified as missing, audited, added to loss-class ledger
3. **Accepted (formalized):** 2026-08-30 progress.md — "Operator decision taken"
4. **Specified (published):** 2026-08-30 findings.md — `/to-spec` issued, spec #849/#850 published to GitHub with `ready-for-agent` label

**Confirmation anchor — task_plan.md:135-136** (ITEM 11, "Add schema references"):
```
**Status: SHIPPED 2026-09-02d.** Original text follows.
```
This shows specs have moved through multiple implementation phases since publication.

---

## Question 4: Is `:dev` still correct under that decision?

**Verdict:** CONDITIONAL.

### Current reality (per shared brief)

**ONE image name** with multiple tags:
- Name: `ghcr.io/ray-manaloto/dotfiles-devcontainer`
- Tags: `:dev`, `:latest`, `:sha`, `:pr-NNN`, `:dev-<hash16>`

Under this topology, **`:dev` is correct** — it is the primary development tag.

### Under the NEW decision (not yet delivered)

**findings.md:373-376** (§ A.3, "Fork 2" — the platform tuple collision):

| Option | Result |
|--------|--------|
| **Separate tag per base OS** | `:dev` (26.04 index, 2 arches) + `:dev-ubuntu2404` (1 arch) — base OS becomes a **tag namespace** |
| Extend platform tuple | OCI `platform.os.version` — untested, Windows-only convention |
| 24.04 publishes standalone | Standalone tag, no index membership |

**findings.md:6c, A.2, A.3:** The spec explicitly notes this fork was **never reached by #848** and must be **decided during the spec-building phase**.

### Verdict: Two branches

1. **If the new spec REJECTS separate-tag-per-base-os:** `:dev` stays single-index with variable base OS → needs clarification
2. **If the new spec ADOPTS separate-tag-per-base-os:** `:dev` remains correct for 26.04 track; `:dev-ubuntu2404` added for 24.04 track

The pwf corpus shows the decision PROPOSED and FORMALLY ACCEPTED (progress.md:47), but **not yet DELIVERED** to code. The implementation phase would answer this.

---

## Summary: pwf corpus describes the state of question 3 (acceptance), not question 4 (delivery)

| Question | Answered by corpus? | Finding |
|----------|-------------------|---------|
| Q1: Is a decision mentioned? | ✅ YES | `findings.md:31,328` and `progress.md:47` |
| Q2: What three images? | ✅ YES | `findings.md:328-329`: amd64/26.04, arm64/24.04, arm64/26.04 |
| Q3: Accepted? | ✅ YES | Recovered from #848, formally accepted 2026-08-30, specs published #849/#850 |
| Q4: `:dev` correct? | ⚠️ CONDITIONAL | Current `:dev` is correct; new spec fork unresolved; delivery not in this corpus |

---

## Re-verified before reporting

- `task_plan.md` (root, current session) — re-read; no mention of prior three-image split decision
- `findings.md` (root, session 2026-08-30.002) — re-read sections 1, 6b, 6c; anchors confirmed
- `progress.md` (root, sessions 2026-08-30.002 and 2026-09-01) — re-read phases 3 and 7; anchors confirmed
- archived plan `task_plan-archived-20260830.003.md` — head verified; confirms chain to #848

None of these files had moved; all anchors remain current.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #848, #849, #850; sessions 2026-08-30 and 2026-09-03
