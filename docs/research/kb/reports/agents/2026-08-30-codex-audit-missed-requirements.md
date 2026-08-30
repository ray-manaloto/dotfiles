# Audit: session requirements log vs published issues #736, #839, #840, #838, #243

Read verbatim: #736 (OPEN, ready-for-agent), #839 (OPEN, ready-for-agent, blocked-by none), #840 (OPEN, ready-for-agent, blocked-by #839), #838 (OPEN, needs-triage), #243 (OPEN, 5 comments).

## Item-by-item verdicts

**1. Update docker images to latest tools/compilers (original ask)** — PARTIAL. GCC 16.2 and LLVM bump are addressed (see 3/4 below), but "merge pending Renovate PRs" and "audit anything not covered by Renovate" have no trace in any of the 5 issues — not confirmable or deniable from this corpus; if those PRs were merged it happened outside these issues.

**2. Add another parallel build for #736** — REFLECTED. #736's entire Solution section is exactly this: "Add `ubuntu-26.04-arm` as a **third, non-blocking** build leg alongside the two existing legs."

**3. Scope clarification: Renovate PRs + audit + GCC 16.2 + LLVM/clang→23.1.0** — PARTIAL. GCC 16.2 is referenced (#736 Out of Scope: "tracked separately by `docs/specs/devcontainer-gcc162-dual-arch.md`"). LLVM is explicitly addressed: #736 Out of Scope — "LLVM/clang bump to 23.1.0 — `llvm-toolchain-resolute-23` does not yet exist on apt.llvm.org... Deferred until upstream publishes it." Renovate-PR-merge and general audit: no trace.

**4. GCC 16.1 → 16.2 correction** — REFLECTED. #243 comment: "GCC 16.2.0 was released 2026-08-07. This issue asks for 16.1, which is now the previous stable release" and a later comment: "Superseded by `docs/specs/devcontainer-gcc162-dual-arch.md`... That spec targets GCC 16.2 via conda-forge."

**5. Canary vs 3-image framing ("just make it parallel... 3 total")** — REFLECTED. #736 Solution: "third, non-blocking build leg alongside the two existing legs" — literally 3 total, non-canary framing.

**6. Tags include Ubuntu version + CPU type** — PARTIAL/superseded-by-correction. #736's actual Naming decision goes the other way: "**No container-base-OS field**... this work must not create one [ubuntu-24.04 vs 26.04 container split]" and "Naming... rather than anything resembling an OS-version tag, since that would misleadingly suggest the container itself differs." This is not a silent drop — it's the corrected outcome after item 8's runner-OS/container-OS distinction was drawn out. Flag as intentionally revised, not missing.

**7. Research via last30days/firecrawl/exa/context7 (check last30days actually invoked)** — MISSING/UNVERIFIABLE from issue text. None of the 5 issues name which research tools were used. #838's "Research so far" section cites version/release-cycle/Discussions data consistent with a web-research pass but does not attribute it to `last30days` specifically, nor to any other named tool. **Cannot be resolved from GitHub issue content alone** — this needs a transcript/tool-call check outside this audit's scope, not an issue citation. Flag as genuinely open.

**8. Runner-OS vs container-OS distinction (BASE_IMAGE ubuntu:26.04 uniform)** — REFLECTED, strongly. #736 Problem Statement: "This is scoped entirely to the **GitHub Actions runner VM's OS**... not to the container's own base OS. `.devcontainer/Dockerfile` already pins `ubuntu:26.04` as `BASE_IMAGE` uniformly for both `amd64` and `arm64`... There is no 'ubuntu-24.04 container' vs 'ubuntu-26.04 container' split in this repo, and this work must not create one."

**9. Broader goal: support permutations cheaply, minimize repeated re-architecture** — REFLECTED. #736 Problem Statement: "the repo's build-matrix mechanism (`PublishTarget`/`platform_target.py`) needs to keep being cheap to extend: the maintainer wants to eventually support more CPU-architecture and runner-OS permutations... without repeated re-architecture work." Also User Stories: "As a future contributor adding the next runner or architecture permutation... I want to add one row to the `PublishTarget` table and get correct tagging/caching/manifest membership for free."

**10. "Keep codex lanes on original ask, fable-advisor for review/questions"** — REFLECTED (process evidence, not itself literal issue content). #736 Further Notes documents multiple fable-advisor-style commitment-boundary reviews ("A commitment-boundary review against this spec... caught the content-hash registry-tag collision"). Process instruction is corroborated by outcome, not directly quotable as a requirement.

**11. Three named production-usage examples (Pumpkin-MC/Pumpkin, google/binexport, rust-lang/libc) for `ubuntu-26.04-arm`** — MISSING. #736 Further Notes cites a *different* `gh search code` adopter list — for `docker/github-builder` evaluation (moby/moby, docker/compose, docker/cli, moby/buildkit, zizmorcore/zizmor, oxipng/oxipng, luanti-org/luanti, asterinas/asterinas). The three specific `ubuntu-26.04-arm`-usage repos named in the log do not appear anywhere in #736, #839, #840, #838, or #243.

**12. Two separate PRs (matrix first, GCC 16.2 second); #243 stays open, linked not closed** — REFLECTED. #736 Out of Scope: "tracked separately by `docs/specs/devcontainer-gcc162-dual-arch.md`, which supersedes issue #243. That work ships as its own follow-up PR, deliberately *after* this one." #243 state is OPEN (not closed), and its final comment: "Leaving this open until the GCC 16.2 PR merges, then closing as completed via the spec."

**13. docker/github-builder investigated and rejected, real-adopter research via `gh search code`** — REFLECTED. #736 Further Notes, first bullet, names the exact investigation and repo list, and the rejection rationale ("none route a pipeline with this repo's complexity... fully through it").

**14. fable-advisor found content-hash collision; "best of options 1 and 2"; separate codex lane for mise-OCI research** — REFLECTED. #736 Implementation Decisions "Content-hash registry-tag collision" section describes exactly this defect and fix. Further Notes: "The `role`/`cache_eligible` design was chosen after explicitly evaluating and rejecting two simpler alternatives (always-rebuild-forever; a leg-namespaced cache with no revalidation guarantee) in favor of one that reuses the existing nightly-rebuild tier... at the accepted cost of more upfront implementation" — matches "best of options 1 and 2, more upfront work." mise-OCI research is tracked as its own issue, #838.

**15. mise OCI ruled out for P2996/base pipeline replacement** — REFLECTED. #736 Further Notes, last bullet: "mise's OCI backend... was evaluated as a possible simplification for the P2996 compiler-cache or base/dev content-hash tiers, and rejected: it has no mechanism for a from-source cmake/ninja build like P2996's... would discard tuning... with no documented equivalent."

**16. User pushback "dont dismiss experimental" → required real maturity reassessment** — REFLECTED. #838 "Research so far" section is exactly this reassessment: "`mise oci build` is real, non-experimental in the sense of being actively maintained: introduced v2026.4.19 (~4.5 months old), touched in every one of the last ~15 release cycles... 5 real `oci`-tagged bug reports found were fixed within 2-10 days... a healthy maintenance signal" — a substantive rebuttal of a dismiss-on-label approach.

**17. Maturity reassessment tracked as its own issue, #838** — REFLECTED. #838 exists, title "Pilot mise oci build for per-tool Docker layer caching," explicitly separated: "Why this is separate from #736... Tracked separately so neither blocks the other."

**18. Standing instruction: all research/spec/opinions must cite mise documentation** — PARTIAL/REFLECTED. #838 cites concrete, checkable facts (version numbers, release cadence, "mise's own docs" quoted on layer caching, `os = [...]` syntax pointed at "`dev-tools/index.md` 'OS-Specific Tools'"). This is citation-grounded, consistent with the standing instruction being followed for this artifact. Cannot confirm it was followed for every research output in the session (out of scope for issue-only audit).

**19. `conda:gxx` `os=[...]` fix — fold into GCC follow-up or track separately? — question asked, no explicit answer given** — PARTIAL, confirmed genuinely unresolved. #838 "Related" section: "Also surfaced in the same research pass (unrelated to this pilot, tracked separately if pursued): `.devcontainer/mise-system.toml`'s `\"conda:gxx\"` entry currently installs on both `amd64` and `arm64` despite its own comment stating it's meant to backfill `arm64` only... mise's non-experimental `os = [...]` per-tool conditionality syntax... could fix this as declarative config, but that's a real behavior change (drops gxx from amd64) requiring an explicit decision, **not bundled here**." This confirms the log's own flag: it is noted only as an aside in #838, has **no ticket of its own**, and is **not folded into** the GCC 16.2 spec/#243 either (#243's comments never mention `conda:gxx`). Genuinely dropped between two homes — worth escalating.

**20. `/to-spec` invoked, codex lane drafted, architect reviewed before publishing** — PARTIAL (process claim, not independently verifiable from issue content). #736's spec is present and detailed in a way consistent with a drafted-then-reviewed document, but nothing in the issue text attributes authorship to a codex lane specifically. Not contradicted, just not confirmable from this corpus.

**21. Spec published to #736, `ready-for-agent` label applied** — REFLECTED. `labels: ready-for-agent` on #736; full spec content (Problem Statement through Further Notes) is present.

**22. fable-advisor commitment-boundary review of published spec found the content-hash collision (3 sites) + 3 smaller pin-in-tickets items; corrected and republished** — REFLECTED. #736 Further Notes: "A commitment-boundary review against this spec (post-publish, pre-tickets) caught the content-hash registry-tag collision above — the more serious of the two collision bugs — before it reached implementation." The "3 sites" show up concretely in #840's acceptance criteria (see item 26 below).

**23. `/to-tickets` invoked "codex implement, codex review" — same-family conflict flagged, not resolved** — Cannot be resolved from issue content; this is a session-routing/process question, and none of the 5 issues discuss reviewer lane assignment at all. Consistent with the log's own claim that this is **still open** — independently confirmed as unaddressed (not silently resolved elsewhere in the issue corpus), not merely "the log says so."

**24. Two tickets proposed (cache-scope fix; validation-leg addition), user approved granularity as-is** — REFLECTED. Exactly two child tickets exist: #839 ("Fix GHA cache-scope collision with a leg-keyed bake variable") and #840 ("Add non-blocking arm64/ubuntu-26.04-arm validation leg"), matching the described split precisely.

**25. Tickets #839 (unblocked) / #840 (blocked by #839), `ready-for-agent`, linked to parent #736** — REFLECTED. #839: "Blocked by: None — can start immediately"; "Part of #736." #840: "Blocked by: #839 (reuses the same leg-identity concept the cache-scope fix introduces)"; "Part of #736." Both carry `ready-for-agent`.

**26. fable-advisor reviewed both tickets: #839 ready as-is; #840 had 3 real gaps (smoke-test probe site; dev-tag marker-poisoning; manifest AC1/verify-arch-tags/matrix-shape-test consumers) — all fixed and republished** — REFLECTED, strongly, verbatim. #840 acceptance criteria include, bolded for emphasis exactly as flagged-gaps:
  - "**The `smoke-test` job's own `dev-cache-probe` step (a separate probe site from `dev-prep`, same composite action, also keyed on PLATFORM only) is likewise skipped/forced-miss...**"
  - "**`dev-tag` must not stamp the shared `:dev-<hash>` marker for a `cache_eligible=False` leg.**"
  - "The manifest-assembly job (`manifest`, `build-publish.yml`) and its correctness assertions (its `AC1` arch-count assertion, and the Python-side `image verify-arch-tags --matrix` consumer) filter to `role=\"publish\"` legs only."
  All three gaps the log names are present as acceptance criteria in #840. #839 has no such addenda — consistent with "ready as-is."

**27. "Where are the compiler-update tickets?" — GCC 16.2 unticketed (pre-existing spec doc only), LLVM has no ticket; architect asked whether to run `/to-tickets` on GCC spec now or open an LLVM placeholder, awaiting answer** — MISSING/confirmed-open. No GCC-16.2 ticket exists among the 5 issues audited (only the spec doc reference in #736/#243). No LLVM ticket exists anywhere. #243's last comment ("Leaving this open until the GCC 16.2 PR merges, then closing") confirms no ticket has been opened yet for that spec. Confirmed genuinely still open, matching the log.

**28. Codex-vs-cross-family reviewer routing conflict — awaiting resolution** — Confirmed still open; no issue addresses it (same finding as item 23 — this is the same underlying item).

**29. `conda:gxx` `os=[...]` fix disposition — awaiting resolution, possibly dropped** — Confirmed dropped between homes, same finding as item 19: noted as an aside in #838's Related section, explicitly "not bundled here," no ticket created, not referenced in #243/#736 either.

## Prioritized list — what the architect should fix or ask the user, ranked by how likely it bites later

1. **`conda:gxx` `os=[...]` disposition (items 19/29) — HIGH.** This is a real, already-identified correctness bug (`conda:gxx` installs on amd64 when the comment says it shouldn't) that currently has **no owner**: not a ticket, not folded into #243/GCC-16.2 spec, only a parenthetical in #838's Related section. Silent-drop risk is concrete, not hypothetical — ask the user now: new standalone issue, or fold into the GCC-16.2 PR (#243's successor)?

2. **Reviewer-lane routing conflict for `/to-tickets` output (items 23/28) — HIGH.** #839/#840 are `ready-for-agent` today with no recorded resolution of same-family (codex→codex) vs cross-family (codex→grok) review. If left unresolved, whichever lane runs first will make the call implicitly, contradicting the orchestration doctrine's own stated preference. Needs an explicit user answer before #839/#840 implementation starts.

3. **Missing GCC 16.2 / LLVM tickets (item 27) — MEDIUM.** Spec exists (`docs/specs/devcontainer-gcc162-dual-arch.md`) and #243 is explicitly waiting on it, but nothing has run `/to-tickets` against it yet. Not urgent (correctly sequenced *after* #736 per Out of Scope), but should not be forgotten — the architect already flagged this and just needs the user's go-ahead.

4. **`last30days` invocation unconfirmed (item 7) — LOW-MEDIUM.** Cannot be verified or refuted from issue content; the substitution (last30days + context7-cli + WebSearch/WebFetch) was pre-approved by the user regardless, so this is a provenance/traceability gap rather than a missing requirement. Worth a one-line confirmation in the session log, not worth blocking on.

5. **Three named `ubuntu-26.04-arm` production-usage examples not cited in #736 (item 11) — LOW.** The evidence that informed the blocking-status decision (kept non-blocking) doesn't appear in the published spec's Further Notes, which instead documents a different (docker/github-builder-adopter) research thread. Cosmetic/traceability gap — the decision itself (non-blocking) is correctly reflected either way; only the specific citation is missing.

6. **Renovate-PR-merge / "audit anything not covered" (item 1/3 residue) — LOW.** No trace in any of the 5 issues, but this was likely handled outside the `/to-spec`→`/to-tickets` pipeline (i.e., merged directly, not ticket-tracked) — not necessarily a drop, just outside this audit's visibility. Worth a quick confirmation, not a blocker.

Items 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 24, 25, 26 are all REFLECTED (fully or with acceptable process-only caveats) and need no follow-up action.
