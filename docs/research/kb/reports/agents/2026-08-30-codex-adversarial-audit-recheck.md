# Adversarial re-check: session requirements log vs #736/#839/#840/#838/#243

Independently re-fetched all 5 issues verbatim (`gh issue view 736/839/840/838 --repo ray-manaloto/dotfiles`, `gh issue view 243 ... --comments`) — did not trust the prior pass's citations. Full text read in full, not skimmed.

## Item-by-item: my own verdict + agree/disagree with prior pass

**1. Update docker images to latest tools/compilers (original ask)** — MY VERDICT: PARTIAL (Renovate-merge/audit untraceable; GCC/LLVM addressed). **AGREE.**

**2. Add another parallel build for #736** — REFLECTED. #736 Solution: literal "third, non-blocking build leg alongside the two existing legs." **AGREE.**

**3. Scope: Renovate PRs + audit + GCC 16.2 + LLVM→23.1.0** — PARTIAL. GCC 16.2 referenced (Out of Scope, points at the spec doc); LLVM explicitly deferred with a cited reason (`llvm-toolchain-resolute-23` doesn't exist yet on apt.llvm.org). Renovate-merge/audit: no trace. **AGREE.**

**4. GCC 16.1 → 16.2 correction** — REFLECTED. #243 comment 4: "GCC 16.2.0 was released 2026-08-07. This issue asks for 16.1, which is now the previous stable release," comment 5: spec "targets GCC 16.2 via conda-forge." **AGREE.**

**5. Canary vs 3-image framing** — REFLECTED. #736: "third, non-blocking build leg alongside the two existing legs" — literally 3, non-canary. **AGREE.**

**6. Tags include Ubuntu version + CPU type** — PARTIAL, but I sharpen the prior's framing. Re-reading #736's Naming section: "**No container-base-OS field**... this work must not create one" and "rather than anything resembling an OS-version tag, since that would misleadingly suggest the container itself differs." The **OS-version half of item 6 was explicitly rejected**, not just "superseded" — it's a deliberate reversal after item 8's runner/container-OS distinction was drawn. The **CPU-type half is separately, already true**: #736 says the new leg's suffix should "follow the existing `tag_suffix` convention used by the other rows (which today denotes architecture)" — architecture/CPU-type was already baked into tag naming before this session, so nothing new needed to happen for it. Net: neither half of item 6 required new work; one half was explicitly reasoned away, the other was already satisfied. **AGREE with the "not a silent drop" conclusion, but the prior pass didn't split the two halves — worth being explicit that "CPU type" was never actually gap-having.**

**7. Research via last30days/firecrawl/exa/context7 (verify last30days invoked)** — UNVERIFIABLE from issue content — none of the 5 issues name a research tool. #838's "Research so far" section reads like a synthesized research pass with zero tool attribution. **AGREE — genuinely unresolvable from this corpus; needs a transcript/tool-call check, not an issue citation.**

**8. Runner-OS vs container-OS distinction** — REFLECTED, strongly, near-verbatim: "This is scoped entirely to the **GitHub Actions runner VM's OS**... not to the container's own base OS... There is no 'ubuntu-24.04 container' vs 'ubuntu-26.04 container' split in this repo, and this work must not create one." **AGREE.**

**9. Broader goal: cheap-to-extend permutations, minimize repeated re-architecture** — REFLECTED. #736 Problem Statement + User Stories ("add one row to the `PublishTarget` table and get correct tagging/caching/manifest membership for free"). **AGREE.**

**10. "Codex lanes on original ask, fable-advisor for review"** — process evidence only, not literal issue content, but corroborated by the review artifacts actually present in #736/#840 Further Notes/ACs. **AGREE this is process-only, can't be pinned to issue text directly.**

**11. Three named adopter repos (Pumpkin-MC/Pumpkin, google/binexport, rust-lang/libc)** — MISSING. Confirmed by full read: #736 Further Notes cites a DIFFERENT `gh search code` adopter list — moby/moby, docker/compose, docker/cli, moby/buildkit, zizmorcore/zizmor, oxipng/oxipng, luanti-org/luanti, asterinas/asterinas — for the `docker/github-builder` evaluation. None of the three named repos appear anywhere across all 5 issues. **AGREE, confirmed by independent full-text read, not just grep.**

**12. Two separate PRs, #243 stays open/linked not closed** — REFLECTED. #736 Out of Scope names `docs/specs/devcontainer-gcc162-dual-arch.md` as tracked separately, "ships as its own follow-up PR, deliberately after this one." #243 state = OPEN, last comment: "Leaving this open until the GCC 16.2 PR merges, then closing as completed via the spec." **AGREE.**

**13. docker/github-builder investigated/rejected via `gh search code`** — REFLECTED, verbatim, first Further Notes bullet with the full repo list and rejection rationale ("none route a pipeline with this repo's complexity... fully through it"). **AGREE.**

**14. Content-hash collision found; "best of options 1 and 2"; separate mise-OCI codex lane** — REFLECTED with one nuance the prior pass didn't surface. #736's actual language: "rejecting two simpler alternatives (always-rebuild-forever; a leg-namespaced cache with no revalidation guarantee) **in favor of** one that reuses the existing nightly-rebuild tier... at the accepted cost of more upfront implementation." That is REJECTING both alternatives in favor of a *third* design (`role`/`cache_eligible`), not literally *combining* "the best of options 1 and 2" as the log's paraphrase implies. The outcome-quality (more upfront work, future flexibility) matches; the "combine 1+2" framing is looser than what's in the issue. Minor — doesn't change the REFLECTED verdict, but it's the log's own imprecision, not a gap in #736. mise-OCI tracked as #838, confirmed. **AGREE with REFLECTED, flagging the "best of 1+2" phrase as loose paraphrase rather than literal issue content.**

**15. mise OCI ruled out for P2996/base pipeline** — REFLECTED. #736 last Further Notes bullet: "it has no mechanism for a from-source cmake/ninja build like P2996's, and replacing the existing Dockerfile+Bake pipeline with it would discard tuning... with no documented equivalent." **AGREE.**

**16. "Don't dismiss experimental" pushback → real maturity reassessment** — REFLECTED. #838 Research so far: "actively maintained: introduced v2026.4.19 (~4.5 months old), touched in every one of the last ~15 release cycles... 5 real oci-tagged bug reports found were fixed within 2-10 days... a healthy maintenance signal" — a genuine rebuttal of a dismiss-on-label approach, with concrete version/cadence numbers. **AGREE.**

**17. Maturity reassessment tracked as its own issue #838** — REFLECTED. #838 title/body explicitly: "Why this is separate from #736... Tracked separately so neither blocks the other." **AGREE.**

**18. Standing instruction: all research must cite mise documentation** — PARTIAL. #838 is citation-grounded (version numbers, "mise's own docs" quoted, `dev-tools/index.md` "OS-Specific Tools" named for the `os=[...]` syntax). #736, by contrast, cites zero mise documentation directly — its mise-OCI rejection bullet ("no documented equivalent") is an assertion, not a citation. **AGREE this is genuinely uneven across the two issues** — the prior pass hedged correctly ("cannot confirm... for every research output") but I'll state it more sharply: #736's own mise-OCI-rejection claim is NOT itself cited to mise docs, only #838's is. Worth noting if the standing instruction is meant to bind every artifact equally.

**19. `conda:gxx` `os=[...]` fix disposition — question asked, no explicit answer** — CONFIRMED genuinely unresolved, independently verified. #838 Related section, quoted in full: "...currently installs on both amd64 and arm64 despite its own comment stating it's meant to backfill arm64 only... could fix this as declarative config, but that's a real behavior change... requiring an explicit decision, **not bundled here**." Checked #243 (all 6 comments) for any mention of `gxx`/`conda:gxx` — none. Checked #736 Out of Scope/Further Notes — no mention. **No ticket exists anywhere in the 5-issue corpus for this fix. AGREE — confirmed, not "possibly dropped" but definitively dropped between homes as of current issue state.**

**20. `/to-spec` invoked, codex-drafted, architect-reviewed** — process claim, not verifiable/contradicted from issue text. **AGREE.**

**21. Spec published to #736, `ready-for-agent` applied** — REFLECTED. Confirmed `labels: ready-for-agent` on #736, full 7-part spec structure present (Problem Statement → Further Notes). **AGREE.**

**22. fable-advisor commitment-boundary review found collision on THREE sites + 3 smaller pin-in-tickets items; corrected and republished** — **DISAGREE with the prior pass's outright "REFLECTED" verdict; this needs a sharper split.** On independent full-text read of #736's "Content-hash registry-tag collision" section, only **two** collision points are explicitly named: the `dev-prep`/`dev-tag` job pair's probe-and-skip, and the `base`/`p2996` registry tags feeding it. The THIRD site — "the `smoke-test` job's own `dev-cache-probe` step (a separate probe site from `dev-prep`, same composite action, also keyed on PLATFORM only)" — does **not appear anywhere in #736**. It first appears, verbatim, as a bolded acceptance criterion in **#840** (the ticket-level fable-advisor review, item 26 of this log), not in the spec-level review item 22 claims to describe. The prior pass's own prose noticed this ("show up concretely in #840's acceptance criteria — see item 26 below") but then still scored item 22 as flatly "REFLECTED" in its verdict line, which overstates what #736 itself contains. Read literally, item 22 (the *spec*-level review finding 3 sites) is **only 2/3 reflected in the artifact it claims to describe** — the third site was actually caught one stage later, at the ticket review. The fix DID land (in #840), so nothing is functionally missing, but the log's claim about *which review round* caught the third site does not hold up against #736's text. Also unverifiable: the "3 smaller pin-in-tickets items" — no issue text enumerates exactly 3 smaller items separately from the 3 named #840 gaps, so this sub-claim is unconfirmable either way, not confirmed as the prior pass's phrasing implies.

**23. `/to-tickets` "codex implement, codex review" — same-family conflict flagged, unresolved** — CONFIRMED still open; none of the 5 issues discuss reviewer-lane routing at all. **AGREE.**

**24. Two tickets proposed, granularity approved as-is** — REFLECTED. Exactly two child tickets exist (#839, #840) matching the described split precisely. **AGREE.**

**25. #839 unblocked / #840 blocked-by #839, `ready-for-agent`, linked to #736** — REFLECTED. #839: "Blocked by: None — can start immediately," "Part of #736." #840: "Blocked by: #839," "Part of #736." Both `ready-for-agent`. **AGREE.**

**26. fable-advisor ticket review: #839 ready as-is; #840 had 3 real gaps (smoke-test probe site, dev-tag marker-poisoning, manifest AC1/verify-arch-tags/matrix-shape-test filtering) — fixed and republished** — REFLECTED, verbatim, all three gaps present as bolded acceptance criteria in #840, exactly as the log describes. #839 carries no equivalent addenda. **AGREE — and this is where the "third collision site" from item 22's over-claim actually landed; see item 22 above.**

**27. GCC/LLVM tickets — status check, awaiting user answer on next step** — CONFIRMED open. No GCC-16.2 ticket anywhere in the 5-issue corpus (only the spec-doc reference in #736 Out of Scope and #243's last comment). No LLVM ticket anywhere. **AGREE.**

**28. Codex-vs-cross-family reviewer routing conflict — awaiting resolution** — same underlying fact as item 23; confirmed still open, independently. **AGREE.**

**29. `conda:gxx` disposition — awaiting resolution, possibly dropped** — same underlying fact as item 19; confirmed dropped (not "possibly" — definitively, per full-corpus read). **AGREE, with the same sharpening as item 19: this is not hedged/possible, it's confirmed.**

## Where I disagree with the prior pass

Only one real disagreement, but it's substantive: **item 22's verdict line ("REFLECTED")** overstates what #736 actually contains. The spec-level fable-advisor review (item 22, pre-tickets) is only correctly described as finding **two** of the three collision sites in #736's own text; the third ("smoke-test's own separate probe") only surfaces at the ticket-level review captured by item 26, in #840. The prior pass's prose flagged this in passing but didn't let it change the verdict category — I'd score item 22 as PARTIAL, not REFLECTED, on a strict reading of "does #736 itself contain what item 22 claims the spec review found." Practically inconsequential (the gap was caught before implementation either way), but it's exactly the kind of "reads as reflected on a skim, actually short of the substance" case this recheck was commissioned to find.

Every other item — including all 20 the prior pass called REFLECTED, both "genuinely unresolved" items (19/29, 23/28), the one unverifiable item (7), and the one cosmetic gap (11) — held up on independent re-derivation. No item was found to be MORE broken than the prior pass stated, and no additional missed/dropped item was found beyond what the prior pass already surfaced.

## Reconciled priority list (severity order)

1. **`conda:gxx` `os=[...]` fix has no owner (items 19/29) — HIGH, confirmed, unchanged from prior pass.** Real, already-identified correctness bug (installs on amd64 despite the comment saying arm64-only), living only as a parenthetical in #838's Related section. No ticket, not folded into #243/GCC-16.2 spec. Ask the user: standalone issue, or fold into the GCC-16.2 follow-up?

2. **Reviewer-lane routing conflict unresolved for #839/#840 (items 23/28) — HIGH, confirmed, unchanged from prior pass.** Both tickets are `ready-for-agent` today with no recorded resolution of same-family (codex→codex) vs cross-family review. Needs an explicit user answer before implementation starts on either.

3. **GCC 16.2 / LLVM tickets not yet created (item 27) — MEDIUM, confirmed, unchanged from prior pass.** Correctly sequenced after #736 per its own Out of Scope section; not urgent, but the architect already flagged it and is waiting on a go-ahead (run `/to-tickets` on the GCC spec now, or open an LLVM placeholder).

4. **`last30days` invocation unconfirmed (item 7) — LOW-MEDIUM, unchanged from prior pass.** Cannot be verified or refuted from issue content since no research artifact names its tooling; the substitution was pre-approved regardless, so this is a traceability gap, not a missing requirement.

5. **NEW: item 22's "three sites" claim is only 2/3 supported by #736's own text (this recheck's finding) — LOW.** Not actionable — the fix landed correctly in #840 regardless of which review round is credited with catching the third site — but worth a one-line correction in future session logs so "found at spec review" claims aren't inflated relative to what actually shipped at that stage. Purely a provenance-accuracy note, not a functional gap.

6. **Three named `ubuntu-26.04-arm` adopter repos not cited in #736 (item 11) — LOW, unchanged from prior pass.** The decision itself (non-blocking) is correctly reflected regardless; only the specific supporting citation is absent from the published spec.

7. **Renovate-PR-merge / general audit trace (items 1/3 residue) — LOW, unchanged from prior pass.** No trace in any of the 5 issues; plausibly handled outside the ticket pipeline. Worth a one-line confirmation, not a blocker.

Items 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 20, 21, 24, 25, 26 are REFLECTED (fully, or with correctly-hedged process-only caveats where issue text can't attest to session-internal process claims) and need no follow-up action. Item 6 specifically: neither half needed new work (CPU-type already present via the pre-existing `tag_suffix` convention; OS-version explicitly and correctly rejected after the runner/container-OS distinction was drawn out) — not a gap, but also not a case of "the ask was fulfilled," so it's excluded from the pure-REFLECTED list above and called out on its own in the item-by-item section.
