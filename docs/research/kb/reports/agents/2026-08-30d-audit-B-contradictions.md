# Audit B — Contradictions

**UNVERIFIED (process evidence, not a line-addressable source):** unless a finding says otherwise, Graphify/rule/skill/task paths are read from PR #846 ref `6278d6ca7e22f6ecd75b0898d65288a05ede94e8`; image/`conda:gxx` paths are read from `origin/main` ref `1e6a36821c94f276def99f262f108b9b03eedb74`. Report paths follow the two-root inventory below.

## Report ↔ report

Scope: contradictions among the 44 verbatim reports only. Code-dependent conclusions are explicitly marked for verification; architect confidence is treated as weak.

HIGH · The proposed Bake-to-GHA bridge depends on arbitrary custom target attributes even though the reference report says Bake has a fixed target schema with no runner field · `2026-08-30b-SYNTHESIS.md:167-186,207-217`; `2026-08-30b-gha-bake-action.md:214-227`; `2026-08-30b-bake-doc-reference.md:187-211`
  EVIDENCE: `gha-bake-action` generalizes a worked `platforms` example to “any target attribute” and “a custom var,” and SYNTHESIS therefore proposes `fields: runner, tag_suffix, role, blocking` plus `${{ matrix.include.runner }}`. The underlying Bake reference report instead says the documented target schema has no runner/builder/execution-host attribute, while SYNTHESIS later says `role`/`cache_eligible`/`blocking` have no Bake equivalent and must stay Python-owned. Control arm for the schema-negative: the same reference-report surface positively documents the real `target.platforms` attribute at lines 64-76, then explicitly reports no runner attribute at lines 187-196. Which side matches the action's current upstream contract is **UNVERIFIABLE (no network)**; a minimal `docker buildx bake --print` prototype with an unknown `runner` key, paired with the same file using known `platforms`, is still required before the #847 design may rely on this bridge.
  DISPOSITION: in-scope-for-#847 — Task 2 must either prove a legal carrier (for example target name/labels) or remove the custom-target-attribute design.

MEDIUM · The morning Bake report says no Bake-level change earns its cost, while the synthesis says a Bake matrix/subaction bridge materially satisfies the one-source requirement · `2026-08-30-codex-research-bake-features.md:135-174`; `2026-08-30b-SYNTHESIS.md:35-80`
  EVIDENCE: The first report calls Bake matrix/group/for a no-op wrapper and recommends only a third GHA matrix row; SYNTHESIS says that conclusion missed `subaction/matrix`, which converts `docker buildx bake --print` into the GHA matrix and therefore changes the “one place vs two” answer. This is an explicit supersession, not two compatible recommendations; the custom-field defect above prevents treating the later answer as already validated.
  DISPOSITION: in-scope-for-#847 — preserve the supersession in the corrected historical account and gate adoption on the requested Bake prototype.

MEDIUM · The initial `docker/github-builder` report calls #736 a documented first-class runner-map use case, but the later action report shows its platform-prefix key cannot distinguish the two same-platform arm64 legs · `2026-08-30-codex-research-github-builder.md:53-73`; `2026-08-30b-gha-build-push-action.md:293-321`
  EVIDENCE: The first report proposes `linux/arm64=ubuntu-26.04-arm` and says the mapping exactly fits the ask. The second report establishes that runner-map keys are only platform prefixes and explicitly says two legs sharing a platform but requiring different runner labels are not expressible; SYNTHESIS reaches the same corrected verdict at lines 81-88. The claims cannot both describe the shipped #840 shape, whose arm64 legs share `linux/arm64/v8`.
  DISPOSITION: in-scope-for-#847 — retain only the same-platform limitation in the corrected design record; do not revive full `github-builder` adoption on the earlier claim.

MEDIUM · The aiodocker report’s ecosystem-wide “no Python wrapper exists” claim is refuted by the Python-on-Whales report’s first-class Bake and imagetools surfaces · `2026-08-30b-pylib-aiodocker.md:78-92`; `2026-08-30b-pylib-python-on-whales.md:32-55,115-141,219-243`
  EVIDENCE: The aiodocker report correctly rejects aiodocker but then over-generalizes that no async or sync Python library wraps `buildx bake` and `imagetools`. The Python-on-Whales report supplies concrete `docker.buildx.bake`, `buildx.build`, and `imagetools.inspect/create` APIs and concludes it is a legitimate scoped replacement candidate, with maintenance and double-invocation caveats.
  DISPOSITION: in-scope-for-#847 — Task 2’s Python Docker API evaluation must start from Python-on-Whales as a candidate, not from the disproven ecosystem-negative.

MEDIUM · The first mise-OCI report says the feature is not worth any dedicated future exploration, while the maturity report explicitly revises that to a scoped pilot recommendation · `2026-08-30-codex-research-mise-oci.md:142-170`; `2026-08-30-codex-mise-oci-maturity-and-partial-adoption.md:142-199`
  EVIDENCE: The first verdict rejects both current adoption and future exploration, led partly by the experimental label. The maturity report calls itself a genuine revision, finds 28 candidate tools and active maintenance, and recommends a small composability pilot while retaining repo-specific architectural blockers.
  DISPOSITION: ticket recommendation — treat existing pilot tracker #838 as the authoritative continuation and annotate the first report as superseded.

HIGH · The Graphify upgrade procedure promises `fresh` after fixing schema and version literals even though the same report says a missing receipt independently prevents `FRESH` · `2026-08-30c-graphify-upgrade-research.md:428-431`; `2026-08-30c-graphify-upgrade-research.md:450-522`; `2026-08-30c-graphify-doc-audit.md:13-20,35-41`
  EVIDENCE: Q7 states that no `build-receipt.json` exists and `_receipt_problem()` therefore returns STALE after the schema gate. Q8 adds no receipt writer or relaxation, yet step 7 says steps 1+3 make health fresh. The independent doc audit supplies the required negative control: its same-shape grep finds only test/doc receipt references and zero dotfiles production writer, while the same grep shape for `GraphifyStatus` returns two source files; live health and query commands both return `build receipt missing`.
  DISPOSITION: in-scope-for-#847 — correct the upgrade lifecycle to name the receipt/stamp policy explicitly rather than promising freshness from schema and literal edits alone.

HIGH · One Graphify report marks bare `graphify update .` “verified CORRECT — do not fix,” while the later cold review says that exact bare command violates the newly authoritative no-global-binary rule · `2026-08-30c-graphify-doc-audit.md:311-333`; `2026-08-30c-opus-cold-review-graphify.md:36-57`
  EVIDENCE: The doc audit validates only that update is AST-only/no-LLM and therefore protects the bare command. The cold review points out that the adjacent eager prose forbids every bare PATH invocation and, at its reviewed ref, offers no compliant update task. The first report’s functionality proof does not answer the later version-routing prohibition, so its “do not fix” disposition does not survive.
  DISPOSITION: in-scope-for-#847 — Task 2 must make the lifecycle consistently use the project-pinned wrapper and expunge the earlier “do not fix” instruction.

MEDIUM · The install probe says 0.9.53 writes nowhere that 0.9.42 does not, then proves 0.9.53 alone creates `SKILL.md.bak` when reinstalling over divergence · `2026-08-30c-graphify-install-probe.md:446-452`; `2026-08-30c-graphify-install-probe.md:454-490`
  EVIDENCE: The “No” verdict is accurate only for a clean flagged install, but its absolute closing sentence says 0.9.53 never writes an extra path. The immediately following controlled diverged-file pass reports no backup at 0.9.42 and a new byte-preserving `.bak` at 0.9.53. Both use the same `install --project --platform claude` command shape; the changed precondition is the manual divergence, which is precisely the load-bearing upgrade case.
  DISPOSITION: in-scope-for-#847 — scope the identical-path claim to clean installs and preserve the divergent-file version split in the lifecycle spec.

HIGH · Three “unresolved/no owner” audits for `conda:gxx` contradict the consolidated report and later reviews showing the pin plus arm64 scope were folded into #841 and landed · `2026-08-30-architect-session-requirements-log.md:37,52-56`; `2026-08-30-codex-audit-missed-requirements.md:43,63-71`; `2026-08-30-codex-adversarial-audit-recheck.md:43,59-73`; `2026-08-30-fable-advisor-and-lane-reports-consolidated.md:31-49`; `2026-08-30b-opus-cold-review-d8fca05.md:30-49`; `2026-08-30b-SYNTHESIS.md:8-13`
  EVIDENCE: The requirement log calls disposition unanswered; both audit reports sharpen that to definitively dropped, no ticket, and not folded into the GCC follow-up. The consolidated report says the opposite—#841 folds the exact pin and arch scope—and the cold review reads the implemented `"conda:gxx" = { version = "16.2.0", os = ["linux/arm64"] }`; SYNTHESIS records #841 landed at `d8fca05`. This is not merely a later choice absent from the corpus: the same 44-report corpus contains the resolution and shipped review evidence the three status audits missed.
  DISPOSITION: in-scope-for-#847 — correct the anti-loss record; do not open a duplicate `conda:gxx` ownership ticket from the stale audits.

MEDIUM · The early #736 report invents a per-leg Ubuntu 26.04 container base override, while the corrected spec reports one Ubuntu 26.04 base shared by every leg and only the runner OS varies · `2026-08-30-codex-research-bake-features.md:150-174`; `2026-08-30-codex-draft-to-spec-736.md:7-19,128-135`; `2026-08-30b-SYNTHESIS.md:90-123`
  EVIDENCE: The early report proposes overriding `BASE_IMAGE` to 26.04 “for that leg only,” treating the other runner-labelled legs as different container bases. The later spec explicitly prohibits that axis because the Dockerfile already pins the same 26.04 base for amd64 and arm64; SYNTHESIS calls the prior framing not the repo’s reality. This correction materially changes tag, matrix, and Bake design, so the early implementation sketch cannot remain an equally valid option.
  DISPOSITION: in-scope-for-#847 — keep runner OS and container base OS separate in Task 2 and mark the early per-leg base-image sketch superseded.

LOW · The superseded architect spec says CI Buildx 0.36.1 is confirmed by a repository pin, while the source report says CI has no version input and downloads latest · `2026-08-30-architect-spec-736-draft-v1-superseded.md:33-42`; `2026-08-30-codex-research-bake-features.md:38-70`
  EVIDENCE: The architect draft attributes v0.36.1 to `.config/mise/conf.d/shared.toml`. The source report checks all six `setup-buildx-action` call sites, finds no `version:` input, and traces the pinned action source to the literal `latest` fallback; v0.36.1 was only the release current on the probe date. Control-arm shape is present in that report: all six identical action-call searches lack `with: version`, while the pinned action source positively contains the `version || 'latest'` fallback.
  DISPOSITION: in-scope-for-#847 — any Bake feature floor in Task 2 must distinguish the local tool pin from the floating CI action download.

LOW · SYNTHESIS says Bake cross-products can never be pruned, while the stdlib report says HCL `for` conditionals may prune them but the page does not document the syntax · `2026-08-30b-SYNTHESIS.md:276-292`; `2026-08-30b-bake-doc-stdlib.md:88-98`
  EVIDENCE: SYNTHESIS upgrades “no documented filter function/keyword” to the absolute “No prune/exclude in bake’s matrix — ever.” The underlying stdlib report is narrower: no dedicated function exists, but `contains`/`regexall`/conditional expressions inside an HCL `for` may do the pruning; it withholds syntax because the selected page is not the HCL expression reference. The corpus therefore supports “not established by these Bake docs,” not “impossible”; current upstream legality is **UNVERIFIABLE (no network)**.
  DISPOSITION: in-scope-for-#847 — include a filtered-cross-product negative/positive Bake prototype before choosing enumerated tuples on impossibility grounds.

MEDIUM · The cache research says same-platform legs collide at base, P2996, and dev registry tags, but the shipped-design reports gate only the dev probe/stamp path and call base/P2996 deliberately untouched · `2026-08-30-codex-research-cache-hybrid.md:20-29,35-66`; `2026-08-30-fable-advisor-and-lane-reports-consolidated.md:100-116,154-165`
  EVIDENCE: The cache report says identical PLATFORM produces identical `base-hash`, `p2996-hash`, and `dev-hash`, recommends leg suffixes at all tier tag sites, and frames each hit as skipping runner-specific validation. The later ticket review says only the build job needs `LEG` because base/P2996 have no Bake `type=gha` cache, while the #840 implementation gates only dev-prep, smoke-test’s dev probe, and dev-tag. These discuss two cache mechanisms (registry skip tags versus Bake GHA layer scope), but the later “exact implementation” report never reconciles the earlier claim that base/P2996 registry hits also bypass the new runner. Whether that bypass is safe is a code/spec question, not settled report consensus.
  DISPOSITION: ticket recommendation — verify the base/P2996 registry-probe semantics against #840’s intended validation boundary and open a focused cache ticket only if those stages must execute per runner.

LOW · The architect log attributes all three collision sites to the spec review, while the adversarial recheck says the smoke-test site first appeared at ticket review · `2026-08-30-architect-session-requirements-log.md:39-43`; `2026-08-30-codex-adversarial-audit-recheck.md:47-57,65-69`
  EVIDENCE: The log says the commitment-boundary spec review found dev-prep, smoke-test’s separate probe, and dev-tag before tickets. The recheck’s full issue-text comparison finds only two sites in #736 and locates smoke-test first in #840, then explicitly downgrades the earlier “REFLECTED” assessment. Both agree the functional gap was fixed before implementation; they disagree on the provenance and timing.
  DISPOSITION: in-scope-for-#847 — correct the anti-loss chronology without reopening the already-landed fix.

### Claims that still require current code or executable verification

- Whether arbitrary custom Bake target keys survive parsing and appear in `subaction/matrix fields`; test the same HCL with unknown `runner` and known `platforms` arms.
- Whether core-HCL `for` conditionals can legally prune a Bake-generated cross-product; the report corpus contains opposite claims but no executable syntax.
- Whether #840 intentionally permits base/P2996 registry-tag hits across the two arm64 runners, and whether those hits still satisfy its runner-validation boundary.
- Whether the current Graphify lifecycle writes or intentionally omits a receipt/stamp after update. The reports capture receipt-required, receipt-relaxed, and runtime-stamp revisions at different SHAs; only current code can select the live contract.
- Whether current CI still leaves `setup-buildx-action`’s version unset; the report proves it for its reviewed workflow, but `latest` is drift-prone and must not be carried forward as a current fact without a fresh read.

### Corpus cardinality and exact-list assurance

**UNVERIFIED (process evidence, not a line-addressable source):** read line-complete: **44/44 reports** — **41** from the detached `origin/main` corpus at `1e6a368`, plus **3** `2026-08-30c-*` reports from PR branch `6278d6c`. The enumeration commands were `rg --files ... | rg '/2026-08-30.*\\.md$' | sort` on each supplied root; their exact filenames were:

```text
origin/main (41)
2026-08-30-architect-session-requirements-log.md
2026-08-30-architect-spec-736-draft-v1-superseded.md
2026-08-30-codex-adversarial-audit-recheck.md
2026-08-30-codex-adversarial-mise-per-tool.md
2026-08-30-codex-audit-missed-requirements.md
2026-08-30-codex-draft-to-spec-736.md
2026-08-30-codex-mise-oci-maturity-and-partial-adoption.md
2026-08-30-codex-research-736.md
2026-08-30-codex-research-bake-features.md
2026-08-30-codex-research-cache-hybrid.md
2026-08-30-codex-research-github-builder.md
2026-08-30-codex-research-mise-oci.md
2026-08-30-codex-research-workflow-compliance.md
2026-08-30-codex-synthesize-736-research.md
2026-08-30-fable-advisor-and-lane-reports-consolidated.md
2026-08-30b-SOURCE-COVERAGE.md
2026-08-30b-SYNTHESIS.md
2026-08-30b-bake-doc-expressions.md
2026-08-30b-bake-doc-funcs.md
2026-08-30b-bake-doc-index.md
2026-08-30b-bake-doc-inheritance.md
2026-08-30b-bake-doc-matrices.md
2026-08-30b-bake-doc-overrides.md
2026-08-30b-bake-doc-reference.md
2026-08-30b-bake-doc-stdlib.md
2026-08-30b-bake-doc-targets.md
2026-08-30b-gha-bake-action.md
2026-08-30b-gha-bpa-bakefile.md
2026-08-30b-gha-build-push-action.md
2026-08-30b-gha-docker-linguist.md
2026-08-30b-gha-github-builder.md
2026-08-30b-indep-bake-discovery.md
2026-08-30b-indep-pylib-discovery.md
2026-08-30b-opus-cold-review-d8fca05.md
2026-08-30b-opus-cold-review-round2.md
2026-08-30b-pylib-aiodocker.md
2026-08-30b-pylib-docker-py.md
2026-08-30b-pylib-dockertown.md
2026-08-30b-pylib-python-on-whales.md
2026-08-30c-graphify-upgrade-research.md
2026-08-30c-opus-cold-review-graphify-2.md

PR branch (3)
2026-08-30c-graphify-doc-audit.md
2026-08-30c-graphify-install-probe.md
2026-08-30c-opus-cold-review-graphify.md
```

## Report ↔ shipped code

MEDIUM · The upgrade report's live-health contract says a missing receipt makes the graph stale, while shipped PR code deliberately treats an absent receipt as healthy · `2026-08-30c-graphify-upgrade-research.md:428-431,507-522`; `python/src/dotfiles_setup/graphify.py:145-189,224-243`
  EVIDENCE: The report says `_receipt_problem()` independently prevents `FRESH` and nevertheless predicts freshness after schema/version edits. At PR #846 ref `6278d6c`, `_receipt_problem()` documents and implements the opposite policy: `if not receipt_path.is_file(): return None`, after which health can return `FRESH`. This is a temporal code-policy change, but the report remains in #847's answer corpus and its upgrade procedure is unsafe to reuse without the supersession.
  DISPOSITION: in-scope-for-#847 — Task 2's upgrade/lifecycle spec must choose and state the current optional-receipt contract, and mark the report's receipt-required procedure superseded.

LOW · A SHA-pinned cold review describes the runtime stamp as implemented, but the shipped PR removes every stamp code path · `2026-08-30c-opus-cold-review-graphify-2.md:1-7,17-50,96-106,248-252`; `python/src/dotfiles_setup/graphify.py:373-385`
  EVIDENCE: The review is explicit that it audits `c90bcf2`, where `update()` wrote `runtime-stamp.json`; current `6278d6c` makes `update()` only invoke `graphify update`. Negative-control evidence for current absence: `rg -n '_runtime_stamp|runtime-stamp' python/src/dotfiles_setup/graphify.py tests/test_graphify.py` returned 0, while the identical files searched for `_BUILD_RECEIPT|build-receipt` returned production and test hits (`graphify.py:34,158,187`; `tests/test_graphify.py:335,355,398,426,459,488`). This mismatch is honest, ref-qualified history rather than an unsupported review, but it is the surviving prose that still describes the removed mechanism as present at its reviewed SHA.
  DISPOSITION: in-scope-for-#847 — retain it as superseded historical evidence; current operator-facing prose must use the no-stamp contract. The live `mise.toml` contradiction is separately HIGHER-risk under rule/code below.

No other unresolved report↔current-code contradiction was found after qualifying historical reports by the SHA they state. For example, the first `conda:gxx` cold review explicitly audits `d8fca05` and identifies defects (`2026-08-30b-opus-cold-review-d8fca05.md:1-23`); round 2 is explicitly the post-fix review (`2026-08-30b-opus-cold-review-round2.md:1-12`), and the shipped `1e6a368` code contains those repairs (`python/src/dotfiles_setup/image.py:129-224`; `python/src/dotfiles_setup/platform_target.py:100-143`; `tests/test_image_smoke_exec.py:103-209`). Treating the first review alone as a current-code claim would manufacture a contradiction by dropping its ref.

## Rule ↔ rule and rule ↔ shipped code

MEDIUM · The surviving `graphify-update` task still promises a builder-version stamp that the final rule and implementation say was removed · `.claude/rules/graphify-first.md:27-32`; `mise.toml:736-746`; `python/src/dotfiles_setup/graphify.py:373-385`
  EVIDENCE: On PR #846 ref `6278d6c`, the rule says the stamp "was removed" (`.claude/rules/graphify-first.md:27-32`) and `update()` only returns `_run(["graphify", "update", target], ...)` (`python/src/dotfiles_setup/graphify.py:373-385`). The task description nevertheless says it will "stamp the graphify version" and "records the builder version so graphify_health can catch a graph built by the wrong binary" (`mise.toml:736-746`). Negative-control evidence for removal: `rg -n '_runtime_stamp|runtime-stamp' python/src/dotfiles_setup/graphify.py tests/test_graphify.py` returned 0; the same command shape for `_BUILD_RECEIPT|build-receipt` returned production and fixture hits, including `graphify.py:34,158,187` and `tests/test_graphify.py:335,355,398,426,459,488`.
  DISPOSITION: in-scope-for-#847 — PR #846 should not merge with task metadata claiming a protection its final commit deliberately removed.

LOW · `graphify-first.md` assigns checker-runtime drift to both `version drift` and `stale`, but shipped control flow assigns it only to `VERSION_DRIFT` · `.claude/rules/graphify-first.md:34-38`; `python/src/dotfiles_setup/graphify.py:194-200,224-243`
  EVIDENCE: The rule says its "`version drift`/`stale` states only ever catch the checking process itself drifting" (`graphify-first.md:34-38`). At `6278d6c`, a checker-runtime mismatch returns `VERSION_DRIFT` before receipt validation (`graphify.py:224-238`); `STALE` is returned only for a present-but-mismatching receipt (`graphify.py:194-200`). Thus the procedural limitation is honest, but the status attribution is not.
  DISPOSITION: in-scope-for-#847 — make the final PR #846 rule name only `version drift` for checker-runtime drift and reserve `stale` for receipt mismatch.

HIGH · Claude's eager instruction routes `/graphify` into a generated skill that mandates the bare/global paths the eager Graphify rule forbids · `.claude/CLAUDE.md:35-41`; `.claude/rules/graphify-first.md:10-12,34-41`; `.claude/skills/graphify/SKILL.md:53,65-100,684-692`
  EVIDENCE: `.claude/CLAUDE.md` says to use `.claude/skills/graphify/SKILL.md` on `/graphify` while also saying never to use bare `graphify` (`.claude/CLAUDE.md:35-41`). The rule makes mise tasks authoritative and calls generated skill material reference-only (`graphify-first.md:10-12,34-41`). But the routed skill says to run bare `graphify query` immediately (`SKILL.md:53,684-692`) and, when its import check fails, to run an unpinned `uv tool install --upgrade graphifyy` or `pip install graphifyy` (`SKILL.md:65-100`). The sibling `.agents` skill demonstrates the intended repository-safe form: reviewed tasks only, with generated Claude references subordinate (`.agents/skills/graphify/SKILL.md:8-24`).
  DISPOSITION: in-scope-for-#847 — Task 2 already includes three-platform skills and the full lifecycle; the spec must resolve which instruction owns execution rather than merely adding another platform copy.

MEDIUM · `do-not.md` bans nonexistent `graphify --watch` while leaving the actual `graphify watch <path>` spelling unnamed · `.claude/rules/do-not.md:34-43`; `python/.venv/lib/python3.14/site-packages/graphify/__main__.py:537`; `python/.venv/lib/python3.14/site-packages/graphify/cli.py:1696-1704`
  EVIDENCE: The active rule says "Never run `graphify hook install` or `graphify --watch`" (`do-not.md:34-38`). The installed, project-pinned 0.9.42 package advertises `watch <path>` (`graphify/__main__.py:537`) and dispatches only `cmd == "watch"` (`graphify/cli.py:1696-1704`). Negative-control evidence: the same `rg -n 'watch|--watch'` over installed `cli.py`/`__main__.py` returned many `watch` hits and zero `--watch` hits; the identical files searched for `query|--budget` returned the documented query command and budget flag (`__main__.py:556-559`, `cli.py:943-971`). This independently confirms the corpus audit at `2026-08-30c-graphify-doc-audit.md:125-135`.
  DISPOSITION: in-scope-for-#847 — correct item 8 while its graphify subject matter is already under audit; do not weaken its separate installer protections.

LOW · The install probe and issue calculate an AGENTS byte cap, while the governing size rule specifies a character cap · `2026-08-30c-graphify-install-probe.md:31-37`; `gh-issue-847.md:48-49`; `.claude/rules/md-size-budgets.md:98-105`
  EVIDENCE: The architect correction calls 12,000 a byte cap and derives `12,961`, "961 bytes over" (`graphify-install-probe.md:31-37`); issue #847 repeats the measured-byte conclusion (`gh-issue-847.md:48-49`). The eager budget rule instead calls AGM-003 a hard 12,000-character ceiling (`md-size-budgets.md:98-105`). Which unit agnix itself actually counts is **UNVERIFIABLE (no network)** because its current own documentation/source was not available in the supplied corpus; therefore the safe conclusion is that the two session-produced unit claims disagree and the exact overage must not be presented as adjudicated here.
  DISPOSITION: in-scope-for-#847 — preserve the substantive "codex install breaches the cap" decision only after the Task 2 spec obtains the actual AGM-003 counting contract; correct the unit and arithmetic in the summary.

LOW · `.claude/CLAUDE.md` says `AGENTS.md` is at its 200-line ceiling, but the shipped file ends at line 192 · `.claude/CLAUDE.md:3-6`; `AGENTS.md:184-192`
  EVIDENCE: The eager Claude file uses "200/200 lines" to justify placing Claude-only material outside root (`.claude/CLAUDE.md:3-6`). On PR #846 ref `6278d6c`, the complete root file ends at `hk.pkl` on line 192 (`AGENTS.md:184-192`). This does not rescue `graphify codex install` from the separate 12,000-character gate, but it is a stale rule-to-file claim.
  DISPOSITION: ticket recommendation — fold this low-risk eager-doc correction into the graphify instruction cleanup, or a sibling docs-hygiene ticket if PR #846 remains narrowly scoped.

## Required high-yield seam checks that did not produce another contradiction

### Two installed Graphify versions

The surviving eager rule does not collapse the two installations: it distinguishes bare-PATH 0.9.53 from the project-pinned 0.9.42 (`.claude/rules/graphify-first.md:14-26`), and the project dependency is still 0.9.42 on PR #846 (`python/pyproject.toml:7-9`). The rule also correctly admits that health cannot identify which one built unreceipted graph bytes (`graphify-first.md:23-41`; `python/src/dotfiles_setup/graphify.py:163-177,224-243`). The contradiction is the stale `mise.toml` promise already reported above, not an assumption that there is only one version.

### `conda:gxx` / `os=` scope at `origin/main` `1e6a368`

All five numbered defects in issue #847 are present in corrected form in the shipped code:

1. The declaration is arm64-only (`.devcontainer/mise-system.toml:64-68`), and exact-tool-set parsing filters a present `os` list by exact OS/arch semantics (`python/src/dotfiles_setup/image.py:129-224,227-249`).
2. Real-image exec tests derive architecture from `docker image inspect`, independently controlled by in-container `uname`, and pass that result to the merge-base tool-set resolver (`tests/test_image_smoke_exec.py:103-174,177-209`).
3. The tier-3 `conda:gxx` compile probe has both a present arm and an absent-but-must-not-resolve arm (`image.py:627-644`); both CI and in-container call sites derive `conda_gxx` from the same filtered declared-tool set (`image.py:1085-1092,2166-2182`).
4. `x64` is in `_ARCH_ALIASES`, and `_LITERAL_RE` is generated from that same key set (`python/src/dotfiles_setup/platform_target.py:100-143`).
5. Tool-OS and tool-arch normalization intentionally do not fold or trim, and a present empty list falls through to `False` (`image.py:129-224`).

No eager rule sentence separately restates `conda:gxx` or mise `os=` semantics. Negative-control evidence: `rg -n -i 'conda:gxx|os[[:space:]]*=' .claude/rules AGENTS.md .claude/CLAUDE.md` returned 0; the identical corpus/command shape for `graphify` returned hits in `AGENTS.md:110`, `.claude/CLAUDE.md:33-48`, `do-not.md:34-43`, and `graphify-first.md:1-53`. The code-wide production sweep for `conda:gxx|CONDA_GXX` found only the declaration, lock data, Dockerfile prose, and the filtered/gated `image.py` paths cited above; its same-shape `gcc-latest|GCC_LATEST` control returned numerous independent production hits, including `image.py:617-623,698-701` and `platform_target.py:204-215,386-392`.

The issue's wording is nevertheless imprecise: it calls all five items "places [that] assumed that tool exists on every architecture" (`gh-issue-847.md:22-30`), but items 4-5 are alias/regex and normalization/list-semantics defects, not additional unconditional `conda:gxx` consumers. The shipped result is corrected; the stated cardinality is five heterogeneous defects, not five assumption sites.

### Issue #847 claim sweep

- **What shipped:** the three rows say #841/PR #844 merged at `1e6a368`, PR #846 remained open, and #845 remained open (`gh-issue-847.md:10-18`). The main code has the five #841 repairs cited above; the prefetched state lists #845 open and PR #846 open (`gh-open-issues.txt:1-4`; `gh-open-prs.txt:1-4`). Auto-merge and whether either local `land` operation remains owed are **UNVERIFIABLE (no network / no line-addressable local receipt)**; no contradiction is asserted for those subclaims.
- **Operator decisions:** the issue actually contains **seven** decision bullets (`gh-issue-847.md:34-42`). Bake adoption is contradicted/under-proved by the custom-field and cross-product findings above; the descriptive tag decision is consistent with SYNTHESIS's proposed scheme (`2026-08-30b-SYNTHESIS.md:234-258`); amd64 remains the local default (`mise.toml:145-153`); three Graphify platforms and the full lifecycle are future Task 2 scope rather than shipped claims (`gh-issue-847.md:39-42,89-96`); stamp removal matches code but contradicts live task prose (`python/src/dotfiles_setup/graphify.py:163-177,373-385`; `mise.toml:736-746`); and the 0.9.53 upgrade still supersedes the open 0.9.48 Dependabot PR in the recorded plan (`gh-open-prs.txt:1-4`).
- **Six overturned findings:** Bake's “single source” conclusion remains contingent on the missing prototype; `github-builder`'s platform-prefix limit is consistent across its two reports; the AGENTS cap's unit is contradictory and **UNVERIFIABLE (no network)**; the two installed Graphify versions are stated separately and consistently; current macOS-runner contents are **UNVERIFIABLE (no network)**; and Python-on-Whales being a candidate directly contradicts aiodocker's ecosystem-negative (`gh-issue-847.md:44-51`; the paired report citations are in the findings above).
- **Six known-imperfect bullets:** CI's default pytest command deselects `image_exec` through root `addopts` (`gh-issue-847.md:53-60`; `pytest.ini:1-15`; `.github/workflows/ci.yml:227-237`); the two named exec tests omit architecture-derived `gcc_latest` arguments while that builder defaults to present (`tests/test_image_smoke_exec.py:221-255`; `python/src/dotfiles_setup/image.py:790-819,833-863`); the stale `kb-currency` nudge has report evidence and a same-surface positive task control (`2026-08-30c-graphify-doc-audit.md:188-202`; `mise.toml:585-601`); and strict Graphify hook mode is documented but unset (`scripts/graphify-hook-guard.sh:11-19`; `.claude/settings.json:1-10`). The exact hook timing and broad-query truncation remain **UNVERIFIABLE (no live timing/query run in this audit)**. No additional contradiction was found in this six-bullet group.

## Enumeration adequacy

HIGH · The three enumerated pairwise surfaces are not the complete contradiction space: they omit the summary issue itself, report↔rule, and generated/runtime contract surfaces · `gh-issue-847.md:1-98`; `.claude/CLAUDE.md:35-41`; `.claude/skills/graphify/SKILL.md:53,65-100,684-692`; `mise.toml:736-746`; `.claude/settings.json:51-69`
  EVIDENCE: This audit found contradictions that cannot be represented cleanly by the three pairs alone: issue #847 says the AGENTS limit is byte-based while its governing rule says characters (`gh-issue-847.md:48-49`; `.claude/rules/md-size-budgets.md:98-105`); the generated Graphify skill contradicts the eager rule, despite a skill being neither a rule nor shipped application code; and task metadata promises a removed stamp. Hook configuration also injects an execution surface independently of the rule files (`.claude/settings.json:51-69`). These are concrete counterexamples to completeness, not hypothetical categories.
  DISPOSITION: in-scope-for-#847 — expand the anti-loss comparison model to include issue↔report/code/rule and instruction/runtime artifacts; do not call the original three-pair enumeration exhaustive.

LOW · Additional durable surfaces could preserve a contradictory contract even when reports, rules, and code agree · `python/verification/suites.toml:7-41,50-75`; `docs/agents/goal-history.md:8-27`; `docs/receipts/602.md:1-28,32-44`; `python/src/dotfiles_setup/memory_index.py:2-20,31-45`
  EVIDENCE: `suites.toml` is an executable token-contract registry; goal history explicitly records decisions without certifying landing; committed receipts assert what shipped; and the auto-memory index is a separate capped fact store with documented stale/index-only failure modes. Other omitted surfaces in this session are generated skills, agent definitions, hook payloads, task descriptions, commit/PR/issue state, live `graphify-out/` artifacts, and installed dependency source. This axis did not exhaustively audit those added domains; it names them because each can disagree with the three supplied surfaces. The prefetched GitHub snapshot itself demonstrates external-state surfaces (`gh-open-issues.txt:1-8`; `gh-open-prs.txt:1-4`).
  DISPOSITION: ticket recommendation — a sibling anti-loss framework ticket should define a typed artifact inventory and authority/ref rules; #847 should at minimum consume the concrete Graphify and issue-summary contradictions already found here.

LOW · Issue #847's “five places assumed the tool exists everywhere” summary overstates the kind of cardinality the shipped fix establishes · `gh-issue-847.md:22-30`; `.devcontainer/mise-system.toml:64-68`; `python/src/dotfiles_setup/image.py:129-224`; `python/src/dotfiles_setup/platform_target.py:100-143`
  EVIDENCE: Three fixes govern declaration/expected-set/compile-probe consumers, while the fourth adds alias/regex grammar and the fifth mirrors mise's exact normalization/list semantics. All five defects are fixed, but only three are tool-existence consumer sites. The production negative sweep and its positive control are recorded in the `conda:gxx` seam section above.
  DISPOSITION: in-scope-for-#847 — change “five places assumed” to “five defects in the architecture-scoping implementation,” then enumerate their distinct classes.

## Coverage and cardinality

**UNVERIFIED (process evidence, not a line-addressable source):** reports read line-complete: **44/44** — **41** under the detached `origin/main` worktree at `1e6a368`, **3** under the PR #846 checkout at `6278d6c`. The exact 44-file inventory is recorded under `Report ↔ report` above. The two ref checks were `git rev-parse HEAD`, yielding `1e6a36821c94f276def99f262f108b9b03eedb74` and `6278d6ca7e22f6ecd75b0898d65288a05ede94e8` respectively.

**UNVERIFIED (filesystem enumeration, not a line-addressable source):** rule files enumerated: **26** `.claude/rules/*.md` files on each ref, plus `AGENTS.md` and `.claude/CLAUDE.md`. The 26 were:

```text
agent-artifact-conventions.md
agent-report-persistence.md
ai-cli-invocation.md
ci-local-parity.md
clarify-before-acting.md
clean-git-state.md
do-not.md
gh-cli-watch.md
goal-history.md
graphify-first.md
local-devcontainer-first.md
long-running-command-hangs.md
md-size-budgets.md
mise-tasks-only.md
notepad-enforcement.md
persistence-gate-retry.md
probes-need-a-control-arm.md
real-integration-evidence.md
research-doc-sources.md
research-repo-enumeration.md
secrets-out-of-the-shell-env.md
tool-currency-and-native-first.md
use-tool-builtins.md
verify-before-advancing.md
zero-bash-logic.md
zero-skip-policy.md
```

The complete rule corpus was searched for `graphify`, `conda:gxx`, and mise `os=` sentences; every matching rule was then read at its relevant lines. Only `.claude/rules/graphify-first.md` differs between the two refs; `AGENTS.md` and `.claude/CLAUDE.md` also differ outside the 26-file rule directory. **UNVERIFIED (process evidence):** this ref-difference statement comes from `git diff --no-index`/hash comparison rather than a line-addressable source file.

## GitHub repos touched

- `ray-manaloto/dotfiles` — the supplied report corpus, issue snapshot, rules, generated skills, workflows, tests, and shipped code at both refs.
- `Graphify-Labs/graphify` — the installed project-pinned 0.9.42 package source used to verify the actual `watch <path>` CLI spelling (`python/.venv/lib/python3.14/site-packages/graphify/__main__.py:537`; `graphify/cli.py:1696-1704`).
