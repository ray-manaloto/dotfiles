# Axis E — transcript-to-corpus capture audit

Scope: the enumerated `U1`–`U86` and `L1`–`L60` extracted from the two 2026-08-30 Claude JSONL sessions (`transcript-human-turns.md:1-3`; `transcript-agent-launches.md:1-3`). This is a read-only audit except for this required report file.

## Method and evidence rules

- The two transcript extracts are the primary evidence. Corpus reports, issue #847, and the session handoff are used only to establish whether a durable trace survived.
- A turn is `CAPTURED` when its material instruction, ruling, correction, preference, or constraint has a durable trace; `ORPHANED` means no such trace was found after a same-shape positive control.
- Teammate messages embedded in the extract are not silently counted as operator speech. They are still accounted for because the stated domain is all 86 enumerated records.
- Launches are mapped item by item; the arithmetic difference `60 - 44` is not treated as evidence.
- Citations are workspace-relative unless an absolute path is needed to distinguish the live PR checkout.

## Part 1 — all 86 enumerated turns

The extractor's label is misleading: a complete classification of `transcript-human-turns.md:5-1425` yields only 10 operator-authored records (`U1`, `U5`, `U6`, `U25`, `U27`, `U28`, `U41`, `U83`, `U85`, `U86`); the remaining 76 are `<teammate-message>` deliveries stored by Claude as `user` records. Compare an operator record at `transcript-human-turns.md:5-7` with the teammate wrapper at `transcript-human-turns.md:9-24`. The same full-range classification finds **0 pure operator acknowledgements**. `U85` is a status question (`transcript-human-turns.md:1411-1413`), not an acknowledgement, and is accounted below.

### Turn-by-turn accounting

| Turn(s) | Verdict | Durable trace |
|---|---|---|
| `U1` | **ORPHANED** | No trace; finding E-H1 below. Source: `transcript-human-turns.md:5-7`. |
| `U2`–`U3` | **CAPTURED** | Advisor verdict persisted verbatim, including manifest exclusion, tag decision, and compiler split: `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:11-27`. |
| `U4` | **CAPTURED** | The six-part permutation research is the persisted `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-736.md:3-123`. |
| `U5` | **CAPTURED** | All three named example repos and their intended evidentiary use survived in `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:21-24`; later audits also explicitly recorded that the examples were missing from the published #736 issue, preserving the traceability gap: `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-audit-missed-requirements.md:27-29`. |
| `U6` | **CAPTURED** | Codex-lane + fable-advisor routing is recorded at `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:18-19,39-50`; the workflow itself is researched at `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-workflow-compliance.md:3-60`. |
| `U7` | **CAPTURED** | The lane's “GHA matrix, not Bake matrix” correction and its later cache-scope qualification survive in `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-bake-features.md:3-35,135-174` and `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-synthesize-736-research.md:3-105`. The launch itself is nevertheless unreported verbatim; see Part 2. |
| `U8`–`U9` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-workflow-compliance.md:3-60`. |
| `U10`–`U11` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-bake-features.md:3-200`. |
| `U12`–`U13` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-synthesize-736-research.md:3-105`. |
| `U14`–`U15` | **CAPTURED** | Advisor verdict persisted verbatim at `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:53-70`. |
| `U16` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-github-builder.md:3-303`. |
| `U17`–`U18` | **CAPTURED** | Draft persisted at `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-draft-to-spec-736.md:3-217`. |
| `U19`–`U20` | **CAPTURED** | Advisor review persisted verbatim at `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:74-95`. |
| `U21` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-mise-oci.md:3-176`. |
| `U22` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-cache-hybrid.md:3-82`. |
| `U23`–`U24` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-adversarial-mise-per-tool.md:8-252`. |
| `U25` | **CAPTURED** | Operator wording and required reassessment survive at `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:31-35`; the resulting reassessment is `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-mise-oci-maturity-and-partial-adoption.md:7-199`. |
| `U26` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-mise-oci-maturity-and-partial-adoption.md:7-199`. |
| `U27` | **CAPTURED** | The instruction and resulting #838 are recorded at `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:33-35`; the prefetched open-issue inventory confirms `#838` is the mise-OCI pilot at `gh-open-issues.txt:4`. |
| `U28` | **CAPTURED** | The compiler-ticket question and its then-open disposition survive at `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:52-56`; the resulting #841 appears at `gh-open-issues.txt:3`. |
| `U29`–`U30` | **CAPTURED** | Ticket review persisted verbatim at `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:99-116`. |
| `U31` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-audit-missed-requirements.md:5-83`. |
| `U32` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-adversarial-audit-recheck.md:5-86`. |
| `U33`–`U34` | **CAPTURED** | Implementation report and correction persisted at `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:120-135`. |
| `U35`–`U36` | **CAPTURED** | Review persisted at `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:138-150`. |
| `U37`–`U38` | **CAPTURED** | Implementation report persisted at `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:154-167`. |
| `U39`–`U40` | **CAPTURED** | Review and production outcome persisted at `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:171-184`. |
| `U41` | **CAPTURED** | The requested #736 ship/close outcome survives in the synthesis's landed-state grounding (`main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:8-13`) and the consolidated implementation outcome (`main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:184`). |
| `U42`–`U46` | **CAPTURED** | The #841 pin, architecture scope, and successive false-failure class survive in issue #847 at `gh-issue-847.md:10-32`; implementation details were independently reconstructed by the cold reviews beginning at `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-d8fca05.md:30-52`. The originating lane has no verbatim report; see Part 2. |
| `U47`–`U48` | **CAPTURED** | The review's runtime-scope concern, whole-file exclusion, and lock churn were independently preserved by `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-d8fca05.md:56-125` and `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-round2.md:94-143`. The grok review itself has no persisted report; see Part 2. |
| `U49`–`U50` | **CAPTURED** | The underlying mise source semantics were re-read and cited in `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-d8fca05.md:6-11,129-151`; the ship outcome is recorded at `gh-issue-847.md:10-18`. The advisor's exact report is absent; see Part 2. |
| `U51` | **ORPHANED** | No trace; finding E-M1 below. Source: `transcript-human-turns.md:620-637`. |
| `U52`–`U53` | **CAPTURED** | Every A1–A9, B1–B5, and C1–C4 delivery maps to a named report in `main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:12-43`. |
| `U54` | **CAPTURED** | D1 maps to `main-audit/docs/research/kb/reports/agents/2026-08-30b-indep-bake-discovery.md:1-10`, with tracker evidence at `main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:45-50`. |
| `U55`–`U56` | **CAPTURED** | The expected-set implementation and its limits were reconstructed in `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-d8fca05.md:30-52,56-125`; issue #847 preserves the defect class at `gh-issue-847.md:20-32`. The implementation lane's exact report is absent; see Part 2. |
| `U57` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:1-13,15-88`. |
| `U58` | **CAPTURED** | Synthesis as above; cold review at `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-d8fca05.md:15-26,56-125`. |
| `U59` | **CAPTURED** | The respec and its remaining divergences were reviewed in `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-round2.md:1-12,27-143`. |
| `U60`–`U61` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30c-graphify-upgrade-research.md:1-12,462-489`. |
| `U62`–`U63` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-round2.md:1-12,27-143`. |
| `U64`–`U65` | **CAPTURED** | The corrected x64/case-fold/empty-list class is recorded in issue #847 at `gh-issue-847.md:24-32`; the CI-selection limitation survives at `gh-issue-847.md:53-56`. The implementation lane's exact report is absent; see Part 2. |
| `U66` | **CAPTURED** | The schema correction and its downstream health result were independently audited at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:1-15` and `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify.md:1-12`. The implementation lane's exact report is absent; see Part 2. |
| `U67`–`U68`, `U70`–`U72` | **CAPTURED** | All revisions, including the correction block that retracts the truncated-help conclusion, survive in `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-install-probe.md:1-15`; issue #847 explicitly points readers to that correction at `gh-issue-847.md:62-71`. |
| `U69` | **CAPTURED** | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:1-15,204-276`. |
| `U73`–`U74`, `U76`–`U79`, `U84` | **CAPTURED** | Both cold reviews preserve the intermediate and final graphify design consequences: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify.md:1-12` and `main-audit/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify-2.md:1-12`; issue #847 records the final runtime-stamp removal at `gh-issue-847.md:34-42`. The implementation lane's exact report is absent; see Part 2. |
| `U75` | **CAPTURED** | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify.md:1-12`. |
| `U80` | **CAPTURED** | `main-audit/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify-2.md:1-12`. |
| `U81`–`U82` | **CAPTURED** | The third unconditional `conda:gxx` site and the earlier too-narrow scoping are explicitly preserved at `gh-issue-847.md:24-32` and in the handoff at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/session-2026-08-30b.md:36-40`. The implementation lane's exact report is absent; see Part 2. |
| `U83` | **CAPTURED** | The operator's prediction-vs-query correction is the stated through-line at `gh-issue-847.md:20-32`; the concrete follow-up is #845 in `gh-open-issues.txt:2` and Task 2 at `gh-issue-847.md:89-96`. |
| `U85` | **CAPTURED** | The status answer survives in the handoff: “No local background tasks” at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/session-2026-08-30b.md:7-12`. |
| `U86` | **CAPTURED** | The anti-loss audit, codex-lane requirement, rerun-grilling expectation, `/to-spec`→`/to-tickets`, and `/prototype` direction all survive at `gh-issue-847.md:75-98` and `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/session-2026-08-30b.md:1-19`. |

### Orphan findings from the enumerated turns

HIGH · E-H1 — The operator's `/grilling` UI contract was lost · `transcript-human-turns.md:5-7`
  EVIDENCE: Operator quote: “provide interactive forms with choice/checkbox w a text box to enter text if choices are not enough and a final free ofrm text to enter details if the questions in the round are not sufficient for /grilling”. Exact fixed-string search for `questions in the round are not sufficient for /grilling` across all 44 reports, issue #847, and the handoff returned 0. Control arm, same command shape and search space: `dont dismiss experimental features` returned `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:34`.
  DISPOSITION: in-scope-for-#847

MEDIUM · E-M1 — The lane-planning verdict for post-#841 parallelism and review-family routing was never persisted · `transcript-human-turns.md:620-637`
  EVIDENCE: The advisor said “Watching #843 is not agent work”, “Hold the cross-family rule”, and recommended one read-only codex diagnosis lane followed by a Claude-side cold review (`transcript-human-turns.md:623-632`). Exact fixed-string search for `Watching #843 is not agent work` across all 44 reports, issue #847, and the handoff returned 0. Control arm, same command shape and search space: `Verdict: #839 is ready to dispatch as-is` returned `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:105`. The older requirements log still calls the review-family question unresolved (`main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:47,52-56`), so this missing lane report is not duplicated by a later durable operator ruling.
  DISPOSITION: in-scope-for-#847

## Part 2 — all 60 Agent-tool launches

### Reconciliation

- **50 REPORTED, 0 EXEMPT, 10 UNACCOUNTED.** Rule 4 exempts only a delegation whose entire value is its immediate mechanical effect (`main-audit/.claude/rules/agent-report-persistence.md:52-55`). Every enumerated launch is research, review/advice, audit, implementation, or a corrective report follow-up (`transcript-agent-launches.md:5-720`); none is a fan-out grep or file-move helper.
- The 50 reported launches map to **41 lane-report files** because `2026-08-30-fable-advisor-and-lane-reports-consolidated.md` covers ten launches (`L2`, `L5`, `L10`, `L13`, `L18`, `L21`–`L25`) in one file (`main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:1-184`; launch briefs at `transcript-agent-launches.md:13-23,49-54,103-109,135-145,195-205,231-272`). The other 40 reported launches each map to one file as enumerated below.
- The remaining three of the stated 44 corpus files are architect-authored artifacts, not reports produced by an enumerated Agent launch: `2026-08-30-architect-session-requirements-log.md:1-3`, `2026-08-30-architect-spec-736-draft-v1-superseded.md:1-8`, and `2026-08-30b-SOURCE-COVERAGE.md:1-4`; none is named by an Agent brief in `transcript-agent-launches.md:5-720`. Thus `41 lane files + 3 architect artifacts = 44 corpus files`; no naive subtraction is used.

### Launch-by-launch accounting

| Launch | Verdict | Report or reason |
|---|---|---|
| `L1` | **UNACCOUNTED** | Asked to research #736 and current build/tool-pin state before grilling (`transcript-agent-launches.md:5-10`). No report or durable outcome identifies this launch. |
| `L2` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:11-27`. |
| `L3` | **UNACCOUNTED** | First of two near-identical #736 research launches (`transcript-agent-launches.md:25-34`). Only one `codex-research-736` artifact and one delivery survive; see E-M2. |
| `L4` | **REPORTED** | Conservatively assigned the sole surviving artifact: `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-736.md:1-3`. Launch: `transcript-agent-launches.md:37-46`. |
| `L5` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:31-49`. |
| `L6` | **UNACCOUNTED** | Asked to implement #736's three-leg matrix and OS-qualified tags (`transcript-agent-launches.md:57-64`); it instead returned a premise refutation/design correction (`transcript-human-turns.md:60-80`) with no report. |
| `L7` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-bake-features.md:1-3`. |
| `L8` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-workflow-compliance.md:1-3`. |
| `L9` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-synthesize-736-research.md:1-3`. |
| `L10` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:53-70`. |
| `L11` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-github-builder.md:1-3`. |
| `L12` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-draft-to-spec-736.md:1-3`. |
| `L13` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:74-95`. |
| `L14` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-cache-hybrid.md:1-3`. |
| `L15` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-mise-oci.md:1-3`. |
| `L16` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-adversarial-mise-per-tool.md:1-8`. |
| `L17` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-mise-oci-maturity-and-partial-adoption.md:1-7`. |
| `L18` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:99-116`. |
| `L19` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-audit-missed-requirements.md:1-5`. |
| `L20` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-codex-adversarial-audit-recheck.md:1-5`. |
| `L21` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:120-135`. |
| `L22` | **REPORTED** | The correction requested at `transcript-agent-launches.md:243-249` is quoted in `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:122-134`. |
| `L23` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:138-150`. |
| `L24` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:154-167`. |
| `L25` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:171-184`. |
| `L26` | **UNACCOUNTED** | Asked to implement the authoritative #841 GCC 16.2 conda-pin spec (`transcript-agent-launches.md:275-287`). Its blocker and final verification reports exist only in teammate deliveries (`transcript-human-turns.md:491-515,528-546`). |
| `L27` | **UNACCOUNTED** | Asked to cold-review commit `254277a4` (`transcript-agent-launches.md:289-295`). The findings exist only in `transcript-human-turns.md:559-581`. |
| `L28` | **UNACCOUNTED** | Asked for the #841 commitment-boundary ship decision (`transcript-agent-launches.md:297-305`). The source-based refutation/conditional ship verdict exists only in `transcript-human-turns.md:594-607`. |
| `L29` | **UNACCOUNTED** | Asked to advise on the codex-only parallel-lane plan (`transcript-agent-launches.md:307-313`). Its routing verdict exists only in `transcript-human-turns.md:620-637`. |
| `L30`–`L38` | **REPORTED** | One-to-one, in launch order: `2026-08-30b-bake-doc-{index,targets,inheritance,expressions,funcs,matrices,reference,stdlib,overrides}.md`; the tracker maps every source/lane/file at `main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:12-24`. |
| `L39`–`L43` | **REPORTED** | One-to-one: `2026-08-30b-gha-{bake-action,github-builder,build-push-action,bpa-bakefile,docker-linguist}.md`; tracker: `main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:26-34`. |
| `L44`–`L47` | **REPORTED** | One-to-one: `2026-08-30b-pylib-{docker-py,aiodocker,python-on-whales,dockertown}.md`; tracker: `main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:36-43`. |
| `L48`–`L49` | **REPORTED** | `2026-08-30b-indep-bake-discovery.md` and `2026-08-30b-indep-pylib-discovery.md`; tracker: `main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:45-50`. |
| `L50` | **UNACCOUNTED** | Asked to fix the smoke expected-tool set's `os=` scoping (`transcript-agent-launches.md:587-596`). Four substantive implementation reports, including the later third-site fix, exist only in `transcript-human-turns.md:843-866,911-945,1005-1028,1328-1353`. |
| `L51` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-d8fca05.md:1-4`. |
| `L52` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:1-13`. |
| `L53` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30c-graphify-upgrade-research.md:1-12`. |
| `L54` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-round2.md:1-12`. |
| `L55` | **UNACCOUNTED** | Asked to fix graphify's false `edges`-schema corruption verdict (`transcript-agent-launches.md:649-659`). The implementation/mutation/real-graph report exists only in `transcript-human-turns.md:1041-1074`. |
| `L56` | **REPORTED** | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-install-probe.md:1-15`. |
| `L57` | **REPORTED** | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:1-15`. |
| `L58` | **UNACCOUNTED** | Asked to make graphify health and its eager fallback rule truthful (`transcript-agent-launches.md:685-695`). Its four-round implementation history exists only in `transcript-human-turns.md:1168-1197,1219-1265,1278-1306,1370-1406`. |
| `L59` | **REPORTED** | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify.md:1-12`. |
| `L60` | **REPORTED** | `main-audit/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify-2.md:1-12`. |

### Dead-lane findings

HIGH · E-H2 — Five implementation launches have no persisted implementation/verification report · `L6`, `L26`, `L50`, `L55`, `L58`
  EVIDENCE: Their briefs cover #736 design/implementation (`transcript-agent-launches.md:57-64`), #841 pinning (`:275-287`), smoke `os=` scoping (`:587-596`), graphify schema repair (`:649-659`), and graphify health semantics (`:685-695`). Each returned findings, scope decisions, failed-gate history, and verification evidence in teammate deliveries cited in the table, so the mechanical exemption cannot apply; persistence is mandatory for any report carrying findings or probe output (`main-audit/.claude/rules/agent-report-persistence.md:3-7,61-65`). Exact fixed-string corpus searches for `CODEX REPORT — #841 FINAL`, `Done. Commit d8fca05 on fix/841-gcc-pin-os-scoped-smoke`, “Done on `fix/graphify-health-links-schema`, commit `325271c`.”, and “All items addressed and committed as `853a506`” each returned 0. Control arm, same search shape and corpus: `# Cold review round 2` returned `main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-round2.md:1`.
  DISPOSITION: in-scope-for-#847

HIGH · E-H3 — Three review/advisor launches have no persisted report · `L27`, `L28`, `L29`
  EVIDENCE: L27 was a cold review, L28 a commitment-boundary review, and L29 an orchestration/risk review (`transcript-agent-launches.md:289-313`), all unambiguously findings-bearing under the persistence rule (`main-audit/.claude/rules/agent-report-persistence.md:3-7`). Exact fixed-string corpus searches for `lockfile not pruned for the new os-scoping`, `VERDICT: Sufficient — ship`, and `Watching #843 is not agent work` each returned 0. Control arm, same search space and command shape: `VERDICT: proceed on the PublishTarget extension` returned `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:17`.
  DISPOSITION: in-scope-for-#847

MEDIUM · E-M2 — Two early research launches cannot be tied to a surviving report · `L1`, `L3`
  EVIDENCE: L1 explicitly asked for fact-finding before `/grilling` (`transcript-agent-launches.md:5-10`) but has no delivery or report. L3 and L4 are near-identical launches one minute apart (`transcript-agent-launches.md:25-46`); only one `codex-research-736` delivery exists (`transcript-human-turns.md:35-42`) and only one report exists (`main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-736.md:1-3`). The artifact contains no launch ID, so it cannot prove both outputs survived; this audit assigns the later L4 to the file and marks L3 lost rather than double-counting one artifact. Exact search for L1's description `Research issue #736 and current build/tool-pin state` returned 0; control arm `Research: #736 permutation-matrix design` returned the surviving report's line 1.
  DISPOSITION: ticket recommendation — reconstruct L1/L3 from raw JSONL if possible; otherwise rerun only the premise research still relevant to future specs.

## Part 3 — is the enumeration the right space?

**No.** It is a useful index, but it is neither complete nor pure enough to be the authority for operator intent.

HIGH · E-H4 — Any mixed machinery-plus-instruction turn is discarded wholesale, including slash-command arguments · `extract_turns.py:13-20,51-57`
  EVIDENCE: After joining text blocks, the extractor drops the entire user record when **any** marker substring is present (`extract_turns.py:52-57`). A slash-command record containing `<command-name>` plus a real argument is therefore erased, not reduced to its argument. The same is true when `<local-command-stdout>` is followed or preceded by “now do X”, or when a task/system notification record also carries an operator correction. This is substring rejection, not block-level filtering. `U86` demonstrates the stakes: its bare-text `/session-handoff` argument carries the anti-loss audit, rerun-grilling, `/to-spec`, `/to-tickets`, and `/prototype` requirements (`transcript-human-turns.md:1415-1425`); the structured-command encoding of the same semantic input would be dropped because `<command-name>` is a configured marker (`extract_turns.py:14-18`).
  DISPOSITION: in-scope-for-#847

HIGH · E-H5 — Images, pasted-file blocks, documents, and other non-text content are silently removed · `extract_turns.py:23-32,51-54`
  EVIDENCE: For list content, `_text_of` appends only blocks with `type == "text"` and ignores every other block type (`extract_turns.py:26-31`). An image-only or file-only operator turn becomes empty and is discarded at `extract_turns.py:53-54`; a mixed text+attachment turn survives with the attachment—and therefore potentially the actual evidence or requested file—missing. This category includes an image conveying a UI correction, an attached/pasted file represented as a non-text content block, or structured document content. The extract gives no tombstone saying a block was dropped.
  DISPOSITION: ticket recommendation — the extractor should emit a typed placeholder with source record identity for every non-text block, never silently omit it.

MEDIUM · E-M3 — The “86 human turns” set includes 76 teammate-machine deliveries and excludes other record classes without an audit trail · `extract_turns.py:13-20,39-57`
  EVIDENCE: The marker list catches selected machinery strings but does not include `<teammate-message>` (`extract_turns.py:13-20`), so teammate notifications stored as `type == "user"` pass through. Compare `U2`'s wrapper (`transcript-human-turns.md:9-24`) with the actual operator-authored `U1` (`transcript-human-turns.md:5-7`). Conversely, all `isMeta` user records are skipped, blank-after-filter records vanish, and malformed JSON lines are silently skipped (`extract_turns.py:42-57`). The resulting cardinality is an implementation artifact, not proof that the session had exactly 86 pieces of human intent.
  DISPOSITION: ticket recommendation — enumerate source-record IDs and classify `operator`, `teammate`, `system`, `command`, `attachment`, and `dropped-with-reason` rather than calling all surviving `user` records human.

MEDIUM · E-M4 — Launch enumeration loses the full brief and all non-`Agent` dispatch mechanisms · `extract_turns.py:59-73`
  EVIDENCE: Only assistant `tool_use` blocks named exactly `Agent` count (`extract_turns.py:59-65`), and every prompt is truncated to its first 400 characters (`extract_turns.py:66-73`). A Skill-tool or other structured dispatch is absent, while an Agent brief's output path, incremental-write requirement, later premises, and constraints may be beyond character 400. The L3/L4 ambiguity in Part 2 is a direct consequence: the extracts retain near-identical heads (`transcript-agent-launches.md:25-46`) but not enough provenance to determine which launch produced the sole report.
  DISPOSITION: ticket recommendation — retain tool-use ID, full prompt hash plus full prompt in a separate lossless artifact, parent/agent identity, output path, and terminal outcome for every dispatch mechanism.

## GitHub repos touched

- `ray-manaloto/dotfiles` — transcript extracts, persistence rule, committed research corpus, shipped-code reviews, issue/PR inventories, and session handoff.
