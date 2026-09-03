# Ship Decision — #918 Rule Registry

**Status:** PENDING CODEX VERDICT
**Branch:** `feat/rule-registry-918` (5 commits over `main` @ `433e1e3`)
**Decision:** Ship the root ticket before 10 sibling lanes #919-#928 read it, or block until #951 unifies parsers?

## The Three Tensions

### 1. The C2 Design — Agreement-Oracle vs. Unified Parser

**Problem:** Two independent parsers of rule frontmatter exist:
- `instructions_report.scoped_rules_on_disk` (lane-forbidden to edit)
- `rule_registry.build_registry` (this ticket)

They should agree on the real corpus, but cannot be unified due to lane boundaries.

**Solution Chosen:** Assert agreement via a test (`test_scoped_agreement_against_real_repo`), plus cover the divergence case where they disagree (`test_scoped_diverges_on_malformed`).

**The Risk:** The silent-failure sweep found this approach is structurally blind to bugs shared by both parsers. UTF-8 BOM case: a scoped rule with a BOM is silently reclassified as eager by BOTH parsers, the agreement test passes, and no signal fires. This is the exact failure the registry exists to prevent (see spec §1).

**Question for codex:** Is an agreement-oracle acceptable as a seam, or is this the kind of structural blindness that should block shipment until the parsers are unified (#951)?

### 2. The Deliberately Un-Armed Gate

**Problem:** The `C2b` tripwire asserts three classifiers agree on the real corpus:
- `registry.scoped_records`
- `scoped_rules_on_disk`
- `has_paths_frontmatter` (from kb_setup)

**Solution Chosen:** The test asserts they agree on the real corpus. The W1 spec lists the failure modes that would make them diverge (three shapes: `paths: string`, `paths: dict`, unparseable-with-`paths:`). But every fixture that would arm the failing arm pins a bug as a contract — the exact trap #917 hit.

**The Rule:** `.claude/rules/probes-need-a-control-arm.md` forbids a check that can only pass.

**Solution:** Documented non-arm with a citation to #951.

**Question for codex:** Did they resolve this correctly, or is documenting the non-arm a rationalization past a rule that should block shipment?

### 3. Speculative Generality — `body_bytes` and `inject`

**Problem:** Two fields exist in `RuleRecord`:
- `body_bytes: int` — no consumer exists yet (needed for #927, #928, #929-#932)
- `inject: bool` — only two pilot values, other rules TBD (needed for #928)

**Question for codex:** Is this correct groundwork for a root ticket, or premature generalization that introduces surface area (#918 doesn't need it, only future tickets do)?

---

## Evidence Summary

**Specification:** `docs/research/kb/reports/agents/2026-09-03-918-SPEC.md` (rev 4, 381 lines)

**Cold Review (Opus 5):** `docs/research/kb/reports/agents/2026-09-03-cold-review-918.md`
- 9 findings: 2 HIGH (strip_frontmatter uncovered, non-UTF-8 crashes), 5 MEDIUM, 2 LOW
- All findings reproduced with control arms
- Baseline: 27 tests pass, rc=0

**Silent-Failure Sweep (Opus 5):** `docs/research/kb/reports/agents/2026-09-03-silent-failure-918.md`
- 17 findings: 9 high/med silent failures (S1-S9), 1 inverse already pinned as expected, 1 loud crash (X1)
- Measured on real corpus (26 `.claude/rules/*.md` files)
- All probed with both arms

**Gates (Ray's verification):**
- `mise run lint` → rc=0
- `uv run --project python pytest tests/` → 2899 passed, 11 deselected, rc=0
- `mise run verify` → 146 passed, 0 failed, 4 skipped, rc=0
- 43 registry tests; every defect re-probed with control arms

**Process:**
- Premise verification (2 rounds, refuted central claim)
- Codex implementation at xhigh
- Opus cold review
- Opus silent-failure sweep
- Two respec rounds
- 17 findings confirmed and fixed

---

## What Codex Will Judge

1. **Is the agreement-oracle seam acceptable?** Or does structural blindness to shared bugs block shipment until #951?
2. **Is the deliberately un-armed gate the right resolution?** Or is documenting it a rationalization past `.claude/rules/probes-need-a-control-arm.md`?
3. **Is speculative generality appropriate here?** Or does introducing fields with no consumer violate YAGNI?

Answer: the single risk that decides whether to ship.
