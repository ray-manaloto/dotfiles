# Issue triage and universal devcontainer task — 2026-09-15

Status: complete

## Authority and scope

- Spec: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/4b5c48be-fade-4708-aff8-2edec71aac2d/scratchpad/spec-issue-triage.md`
- Repository: `ray-manaloto/dotfiles`
- File ownership: dispatcher-only for this report, the plan delta, `findings.md`, and `progress.md`; specialists return structured results without file edits.
- `task_plan.md` is read-only. Its planning-with-files attestation currently reports `PLAN TAMPERED`; this run does not alter or re-attest it.

## Premise verification

| Premise | Observation | Direct rc | Verdict |
|---|---|---:|---|
| P1 open-issue count | `gh issue list --state open --limit 500 --json number --jq 'length'` → 335 | 0 | pass |
| P1 independent count | GitHub search API `.total_count` → 335 | 0 | pass |
| P1 frozen corpus | `wc -l docs/research/kb/raw/open-issues-2026-09-15.tsv` → 335 | 0 | pass |
| P2 blockers | #676 CLOSED; #677 CLOSED | 0 each | pass |
| P3 parent | #849 CLOSED | 0 | pass |
| P4 network | `gh issue view 678` returned the live OPEN issue | 0 | pass |

## Investigation ledger

- Broad Graphify searches returned `rc=3` because their complete traversals exceeded the initial budgets. A narrowed `verify-arch` traversal completed with `rc=0`, locating the architecture/name/verification surface in `python/src/dotfiles_setup/platform_target.py`, `devcontainer_names.py`, `container.py`, and `sync.py`.
- Checkout guard: `git branch --show-current` → `docs/session-2026-09-15-preclear` (`rc=0`), so the tracked report is not being written on `main`.
- Live type-label vocabulary: `bug`, `documentation`, `enhancement`, `question`, `dependencies`. State labels such as `needs-triage` are not treated as types.
- Specialist dispatch is complete; the canonical reconciliation below assigns exactly one disposition to all 335 frozen issues.

## Live Mac devcontainer baseline

| Probe | Observation | Direct rc |
|---|---|---:|
| `mise run names` | amd64 name `dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233`, volume suffix `amd64-home`, port 26233 | 0 |
| `MISE_ENV=arm64 mise run names` | arm64 name `dotfiles-dotfiles-rmanaloto-273897ea-arm64-22975`, volume suffix `arm64-home`, port 22975 | 0 |
| `docker context show` | `desktop-linux` | 0 |
| `docker ps --filter label=dotfiles.workspace=273897ea --filter label=dotfiles.arch=amd64` | one running amd64 container | 0 |
| same query with `dotfiles.arch=arm64` | no running arm64 container | 0 |

The negative arm is discriminating because the identical workspace+architecture query finds the amd64 control. An earlier `devcontainer.local_folder` filter was rejected as evidence: this repo passes explicit `--id-label` values, which replace the CLI's inferred labels. The universal task therefore starts from one verified-running candidate namespace and one missing runtime instance.

## Frozen-corpus partition

Direct TSV parsing (`rc=0`) yields modulo-4 shard sizes 86, 78, 85, and 86 (sum 335). It also independently reproduces 11 `needs-triage` rows and 107 unlabelled rows. These counts are the pre-mutation reconciliation baseline; live GitHub counts may decrease while specialists close or label issues.

## Specialist checkpoint — image specialist (verbatim)

> Checkpoint: live controls both report 335 open (gh issue list --limit 500 rc=0; search API total_count rc=0); #676/#677/#849 confirmed CLOSED and #678 OPEN. Graphify narrow query rc=0. I have inspected the 19 mandatory seed issues plus 50+ older image/lifecycle/smoke/toolchain candidates, and confirmed verify-arch is request-derived at mise.toml:1021-1064 via platform_target.py:484-486 (not fixed x86_64). I am finalizing an exhaustive image-surface ledger (~70 rows), then will mutate only this shard: type-label unlabeled rows, remove needs-triage on #838, cross-link/close only evidence-backed superseded issues. No files/gates/git/container bring-up touched.

## Specialist checkpoint — Python specialist (verbatim)

> Checkpoint: live count verified 335 (gh rc=0); modulo-0 shard count verified 86 (gh rc=0). I have enumerated all 86 titles/labels and inspected bodies/comments for ~60, including the sole shard needs-triage issue #536 and the likely stale/completed candidates. Mutations so far: 0; mutation failures: 0. I am defaulting ambiguous closes to KEEP-SEPARATE, and will perform only evidence-backed label/removal/close commands after classification is complete. Final output will contain exactly 86 ISSUE rows.

## Specialist checkpoint — config specialist (verbatim)

> Checkpoint: live pre-mutation shard was 79 residue-1 issues (not 78); after I closed #881 the live open shard is now 78, so my final ledger will include all original 79 exactly once, including #881 CLOSE. All 79 have been dispositioned. Mutations: 17 `gh issue edit` commands rc=0 (15 initially-unlabelled issues typed; #537 typed + needs-triage removed; #953 needs-triage removed) and 1 `gh issue close` rc=0 (#881, evidence in its own WONTFIX record). Failures=0. Tentative counts: KEEP-SEPARATE 53, CLOSE 1, BLOCKED-BY 4, DEFER-IMAGE 21.

Dispatcher note: the frozen TSV has 78 residue-1 rows. The specialist's final result must identify the exact live-only/frozen-only set difference; the mismatch is unresolved at this checkpoint.

### Config checkpoint correction (verbatim)

> Correction after machine-counting the captured number list: original shard is 78, not 79 (manual recount error in my checkpoint). Current open residue-1 count is 77 because #881 was closed. Final counts therefore: KEEP-SEPARATE 52, CLOSE 1, BLOCKED-BY 4, DEFER-IMAGE 21 = 78.

Dispatcher note: resolved. The frozen and live pre-mutation residue-1 corpora agree; the one-row live decrease is the specialist's evidenced close of #881.

## Final specialist report — config specialist (verbatim)

Processed the complete pre-mutation residue-1 shard: 78/78 issues. The live repository started at 335 open issues; closing #881 reduced it to 334.

Counts:

- Assigned: 78
- KEEP-SEPARATE: 52
- CLOSE: 1
- BLOCKED-BY: 4
- DEFER-IMAGE: 21
- `needs-triage` resolved: 2
- Initially unlabelled, non-image issues typed: 15
- Initially unlabelled deferred-image issues left for image specialist: 7 — #5, #33, #73, #769, #909, #1105, #1121
- Mutation commands: 18
- Mutation failures: 0
- Closed: #881 only, based on its existing `wontfix` label and five documented DO NOT SHIP reviews
- No repository files, git operations, gates, or issue-body edits performed

Graphify orientation:

- Broad query: rc=3 because its 50/690-node result exceeded the budget.
- Narrow repository-rules query: rc=0 and identified `.claude/rules/agent-report-persistence.md` and `.claude/rules/notepad-enforcement.md`.

Mutation log, with direct return codes:

```text
gh issue edit 69 --add-label enhancement\trc=0
gh issue edit 165 --add-label enhancement\trc=0
gh issue edit 537 --add-label bug --remove-label needs-triage\trc=0
gh issue edit 717 --add-label bug\trc=0
gh issue edit 721 --add-label enhancement\trc=0
gh issue edit 725 --add-label bug\trc=0
gh issue edit 729 --add-label dependencies\trc=0
gh issue edit 765 --add-label question\trc=0
gh issue edit 829 --add-label bug\trc=0
gh issue edit 953 --remove-label needs-triage\trc=0
gh issue edit 965 --add-label bug\trc=0
gh issue edit 1017 --add-label enhancement\trc=0
gh issue edit 1049 --add-label bug\trc=0
gh issue edit 1097 --add-label bug\trc=0
gh issue edit 1101 --add-label bug\trc=0
gh issue edit 1117 --add-label bug\trc=0
gh issue edit 1125 --add-label question\trc=0
gh issue close 881 --comment "Closing as WONTFIX: #881 documents five independent DO NOT SHIP reviews and the decision that session skills must not carry planning-with-files state."\trc=0
```

Ledger:

```text
ISSUE\t5\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tMulti-arch image support is image-specialist scope; #5 also names an external P2996 blocker.
ISSUE\t13\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tThe policy expands checks around Dockerfile/devcontainer identity surfaces.
ISSUE\t17\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tImage size, image tool count, and image build-time metrics belong to the universal image task.
ISSUE\t33\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tDocker-build bun warning; the body says it is documented/no-action pending upstream suppression.
ISSUE\t69\tKEEP-SEPARATE\tB=HK-V2-1090\tenhancement\tADD_LABEL enhancement rc=0\tMarkdown-linter adoption is hk configuration work and should follow the v2 engine change.
ISSUE\t73\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tCorrects the devcontainer SSH conclusion and cites shipped commit e87b65f.
ISSUE\t101\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tHost-OS lint coverage is distinct from container-image execution.
ISSUE\t165\tKEEP-SEPARATE\tB=HK-V2-1090\tenhancement\tADD_LABEL enhancement rc=0\tFocused mdschema builtin adoption remains distinct from broader #69.
ISSUE\t193\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tdependencies\tNONE\tRenovate Dependency Dashboard is the persistent dependency coordination issue.
ISSUE\t225\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tenhancement\tNONE\tAutomation-library speed work is a measured tooling optimization, not image work.
ISSUE\t253\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tenhancement\tNONE\tRelease-note ingestion covers all tools; Docker is emphasis, not the owning runtime.
ISSUE\t257\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tdependencies\tNONE\tRenovate rebase churn is dependency-automation work.
ISSUE\t281\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tenhancement\tNONE\tCanonical doctor task/module work is tooling automation.
ISSUE\t293\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tdocumentation\tNONE\tTracks a Claude-Code-version-bound skill-description limit and audit.
ISSUE\t313\tBLOCKED-BY\tE=TOOLING-CURRENCY\tenhancement\tNONE\tIssue body explicitly blocks Graphify T2 on open #312.
ISSUE\t317\tBLOCKED-BY\tE=TOOLING-CURRENCY\tenhancement\tNONE\tIssue body explicitly blocks Graphify wiring on open #315 and #316.
ISSUE\t337\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tControl-arm enforcement remains an independent reliability guardrail.
ISSUE\t489\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\t-\tNONE\tSecurity-relevant unmanaged host-file inventory remains an evidence-gathering task.
ISSUE\t493\tKEEP-SEPARATE\tG=DEFERRED-NEEDS-HUMAN\t-\tNONE\tThe HITL prototype must settle proxy enforcement and credential-exposure behavior.
ISSUE\t497\tKEEP-SEPARATE\tG=DEFERRED-NEEDS-HUMAN\t-\tNONE\tExplicit grilling decision on the secrets CLI repository boundary.
ISSUE\t537\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tADD_LABEL bug REMOVE_LABEL needs-triage rc=0\tMeasured UserPromptSubmit timeouts are a live hook-reliability defect; companion #536 is distinct.
ISSUE\t569\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\t-\tNONE\tResearches upstream Codex SDK support before custom rate-limit code.
ISSUE\t577\tKEEP-SEPARATE\tG=DEFERRED-NEEDS-HUMAN\t-\tNONE\tExplicit grilling decision on context threshold and restart contract.
ISSUE\t581\tKEEP-SEPARATE\tG=DEFERRED-NEEDS-HUMAN\t-\tNONE\tExplicit grilling decision on DAG telemetry and observability.
ISSUE\t597\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\t-\tNONE\tMerge-commit convention policy needs an orchestration/documentation ruling.
ISSUE\t605\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\t-\tNONE\tReflect DAG-node design is orchestration work, not an image concern.
ISSUE\t669\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tParent dual-architecture devcontainer substrate is the universal image-task core.
ISSUE\t681\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tStructured nonblocking event sinks are part of #669 build/lifecycle behavior.
ISSUE\t685\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tLifecycle stop/remove/restart/status verbs are part of the devcontainer substrate.
ISSUE\t689\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tBuild and lifecycle warning gates are explicit #669 outcomes.
ISSUE\t709\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\t-\tNONE\tTwo-repository Graphify provenance remains separate tooling research.
ISSUE\t713\tKEEP-SEPARATE\tG=DEFERRED-NEEDS-HUMAN\t-\tNONE\tHITL promotion decision for the canonical currency risk model.
ISSUE\t717\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tbug\tADD_LABEL bug rc=0\tUnsupported mise bootstrap placement produces warnings on every project command.
ISSUE\t721\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tADD_LABEL enhancement rc=0\tTyped GitHub Markdown transport addresses a demonstrated shell-interpolation incident.
ISSUE\t725\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tADD_LABEL bug rc=0\tPR #726 merged to the already-used #703 branch after #703 reached main, so no verified main landing supports closure.
ISSUE\t729\tBLOCKED-BY\tB=HK-V2-1090\tdependencies\tADD_LABEL dependencies rc=0\tThe v1.55-specific review must be reconciled with open hk-v2 PR #1090 first.
ISSUE\t745\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tbug\tNONE\tARM64 CI disk cleanup belongs to the architecture/image lane.
ISSUE\t765\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tquestion\tADD_LABEL question rc=0\tBounded evaluation of a research adapter is tooling admission work.
ISSUE\t769\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tDual-local AMD64/ARM64 containers, ports, volumes, and caches are image-task scope.
ISSUE\t829\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tADD_LABEL bug rc=0\tConfirmed handoff/session-state defects remain independent reliability fixes.
ISSUE\t833\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\t-\tNONE\tHandoff citation validation is an unblocked orchestration-tool task.
ISSUE\t841\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tARM64-scoped GCC pinning is container-image content work.
ISSUE\t845\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tRequires probing mise behavior inside the image.
ISSUE\t853\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tBake-owned permutation source of truth is image-specialist scope.
ISSUE\t857\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\tenhancement\tNONE\tRoot agent-instruction budget headroom is documentation/orchestration work.
ISSUE\t861\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tquestion\tNONE\tCadence for image_exec tests materially concerns image verification.
ISSUE\t865\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tquestion\tNONE\tProbes whether macOS runners can build Linux container images.
ISSUE\t869\tBLOCKED-BY\tE=TOOLING-CURRENCY\tenhancement\tNONE\tGraphify installer cost reporting is explicitly blocked by #856; platform means agent surface, not CPU architecture.
ISSUE\t873\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tLive ARM64 devcontainer work is universal-task scope; body names #867/#871 blockers and architecture-aware smoke.
ISSUE\t881\tCLOSE\t-\tdocumentation\tCLOSE_WITH_COMMENT rc=0\tWONTFIX record documents five independent DO NOT SHIP reviews and the no-PWF-state decision.
ISSUE\t889\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tquestion\tNONE\tGraphify determinism experiment is tooling verification.
ISSUE\t909\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tDev image liveness and sync convergence are bring-up/image verification.
ISSUE\t917\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\tenhancement\tNONE\tMeasures rule-loading behavior in the agent instruction system.
ISSUE\t921\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tLogging migration CLI/sink wiring is a reliability lane.
ISSUE\t925\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tDAG-project logging migration is separate reliability work.
ISSUE\t929\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tControl-arm corpus classification is reliability-policy work.
ISSUE\t933\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tNo-suppression gate is an independent enforcement task.
ISSUE\t937\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\tenhancement\tNONE\tConverts niche eager rules into on-demand skills.
ISSUE\t941\tKEEP-SEPARATE\tG=DEFERRED-NEEDS-HUMAN\t-\tNONE\tIssue remains needs-info until the required live off-root Codex hook probe settles the premise.
ISSUE\t949\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tObserver-corpus retention/error handling is a reliability issue.
ISSUE\t953\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tdependencies\tREMOVE_LABEL needs-triage rc=0\tCurrent daily currency report remains the active dependency review surface.
ISSUE\t965\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tADD_LABEL bug rc=0\tHand-rolled CI polling has a documented run-selection race and rule conflict.
ISSUE\t981\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tNONE\tCancellation-insensitive CI conditions are a workflow reliability defect.
ISSUE\t985\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\tbug\tNONE\tAMD64 manifest selection failure is image publication/architecture scope.
ISSUE\t993\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tenhancement\tNONE\tWhole-repo native-feature modernization is tooling work.
ISSUE\t997\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tenhancement\tNONE\tGraphify refresh and feature inventory are tooling currency.
ISSUE\t1017\tKEEP-SEPARATE\tG=DEFERRED-NEEDS-HUMAN\tenhancement\tADD_LABEL enhancement rc=0\t2026-09-15 operator ruling moves agentsview out of this repo; kept open because no commit/issue evidence supports closure.
ISSUE\t1029\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\tenhancement\tNONE\tSession-start skills-directory plugin remains orchestration work.
ISSUE\t1041\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tenhancement\tNONE\tBuild-time tool.call restrictions are enforcement hardening.
ISSUE\t1049\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tADD_LABEL bug rc=0\tThe command fix does not close the three reliability channels documented by the issue.
ISSUE\t1057\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tNONE\tUnconsumed guard fail-open records remain a reliability defect.
ISSUE\t1097\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tADD_LABEL bug rc=0\tGraphify guard failures are swallowed without cause or count.
ISSUE\t1101\tKEEP-SEPARATE\tD=RELIABILITY-SECURITY\tbug\tADD_LABEL bug rc=0\tTypeScript function-hook logic bypasses the bash-logic gate.
ISSUE\t1105\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tTriages retired base-OS-track children into the universal image outcome.
ISSUE\t1117\tKEEP-SEPARATE\tE=TOOLING-CURRENCY\tbug\tADD_LABEL bug rc=0\tPin-parity coverage gaps are tooling/dependency consistency defects.
ISSUE\t1121\tDEFER-IMAGE\tC=UNIVERSAL-DEVCONTAINER\t-\tNONE\tlock-shared lacks bounded devcontainer exec and bring-up behavior.
ISSUE\t1125\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\tquestion\tADD_LABEL question rc=0\tOpen decision on parallel agent dispatch and gate-runner/workflow shape.
ISSUE\t1137\tKEEP-SEPARATE\tF=DOCS-ORCHESTRATION\tenhancement\tNONE\tSkill-gated SDLC dispatch is agent-orchestration enforcement.
```

## Image-specialist incident report at discovery (verbatim)

> Important incident: while posting #678 via `gh issue comment --body "..."`, I failed to neutralize Markdown backticks. zsh executed the two documented commands inside command substitution: `mise run up` and `MISE_ENV=arm64 mise run up`. This violated the no-bring-up constraint; the comment command timed out/returned no direct rc while an arm64 image pull began. I am immediately inspecting process state and will stop only the spawned host processes (not use raw docker or tear down pre-existing containers), then correct/report the malformed comment. Other gh mutations succeeded.

Dispatcher containment: stop only exact spawned host-process ancestry; no broad `pkill`, no raw Docker lifecycle, and no pre-existing amd64 teardown. Verify #678 comments through structured `gh` JSON. If correction is necessary, append a corrective comment via a safely quoted body file rather than edit/delete authored text. Final evidence must include direct return codes and post-containment container state.

### Image-specialist containment report (verbatim)

> Incident contained. Exact accidental ancestry: zsh 60687 -> mise 61305 -> fnox 61345 -> devcontainer node 61418 -> docker buildx 61991. `kill -TERM 60687` rc=0 left reparented children; `kill -TERM 61991 61418 61345 61305` rc=0 stopped all. Control ps afterward rc=0 showed only the probe itself. Read-only `docker ps --filter label=dotfiles.workspace=273897ea` rc=0 now shows exactly the pre-existing amd64 container b954aff8b809 (`dotfiles.arch=amd64`), no arm64 container. #678 had no malformed/new comment; I posted the intended correction safely with `--body-file`: https://github.com/ray-manaloto/dotfiles/issues/678#issuecomment-5690057899 rc=0. #838 did get a malformed comment because `needs-triage` backticks executed as a failed shell command; per instruction I did not edit/delete it and added corrective https://github.com/ray-manaloto/dotfiles/issues/838#issuecomment-5690058868 rc=0. Temp body files deleted; absence check rc=0.

### Dispatcher containment verification

| Check | Observation | Direct rc |
|---|---|---:|
| `ps -p 60687,61305,61345,61418,61991` | no incident process remains | 1 (expected no-match) |
| same `ps` mechanism on the live probe shell | current process returned | 0 |
| workspace+amd64 Docker-label probe | pre-existing `b954aff8b809` running | 0 |
| identical workspace+arm64 probe | no arm64 container | 0 |
| structured fetch of #678 comment 5690057899 | intended literal commands present | 0 |
| structured fetch of #838 final two comments | malformed comment preserved; corrective comment states the missing `needs-triage` text | 0 |

Containment accepted. The accidental build did not leave an arm64 container running and did not disturb the pre-existing amd64 container.

## Final specialist report — Python specialist (verbatim)

Live inventory: 335 open issues before mutation (`gh issue list --state open --limit 500`, rc=0). Assigned modulo-0 shard: 86 issues.

Counts: assigned=86, keep=58, close=1, blocked=10, defer-image=17, needs-triage-resolved=1, unlabelled-typed-by-this-lane=25, remaining-unlabelled-in-open-shard=0, mutation-failures=0.

Graphify’s narrow queries returned rc=3 because results were truncated, so repository rules authorized source fallback. No files, repository gates, or git state were touched. #312 was the sole closure, supported by merged PR #319. Image-owned issues were not mutated by this lane.

```text
ISSUE\t1124\tKEEP-SEPARATE\tD\tenhancement\tgh issue edit 1124 --add-label enhancement (rc=0)\tPreventive SessionStart guard-runner health probe is distinct from reactive fail-open diagnostics.
ISSUE\t1120\tBLOCKED-BY\tD\tenhancement\tgh issue edit 1120 --add-label enhancement (rc=0)\tExplicitly blocked by #1099 and #1100 before the one-process-per-event gate can be sound.
ISSUE\t1116\tDEFER-IMAGE\tC\tdependencies\tNONE\tRenovate grouping is explicitly coupled to image-build inputs and belongs to the image specialist.
ISSUE\t1112\tKEEP-SEPARATE\tD\tbug\tgh issue edit 1112 --add-label bug (rc=0)\tConcurrent Codex lanes can exchange fixed prompt/verdict paths; live reliability defect.
ISSUE\t1108\tKEEP-SEPARATE\tD\tbug\tgh issue edit 1108 --add-label bug (rc=0)\thandoff-check has a distinct basename-resolution false-positive class from #831.
ISSUE\t1104\tKEEP-SEPARATE\tE\tbug\tgh issue edit 1104 --add-label bug (rc=0)\tfnox activation bakes prunable versioned paths; tooling lifecycle defect remains reproducible by mechanism.
ISSUE\t1100\tKEEP-SEPARATE\tD\tbug\tgh issue edit 1100 --add-label bug (rc=0)\tGraphify guard registrations have mutation-proven zero wiring coverage.
ISSUE\t1096\tKEEP-SEPARATE\tD\tbug\tgh issue edit 1096 --add-label bug (rc=0)\tFail-open audit rows omit stderr and therefore cannot diagnose cause.
ISSUE\t1060\tKEEP-SEPARATE\tE\tdocumentation\tgh issue edit 1060 --add-label documentation (rc=0)\tDurable Phase-2 dependency-currency goal carrier remains authoritative until that workflow lands.
ISSUE\t1056\tKEEP-SEPARATE\tD\tbug\tNONE\tThree probe-integrity failure classes remain mechanically unprevented.
ISSUE\t1032\tBLOCKED-BY\tF\tenhancement\tNONE\tBody explicitly blocks on #1025 through #1031.
ISSUE\t1028\tBLOCKED-BY\tF\tenhancement\tNONE\tBody explicitly blocks on #1025 because the query requires the label first.
ISSUE\t1024\tKEEP-SEPARATE\tF\tenhancement\tNONE\tParent feature for session-start retrieval has open child work and is not subsumed by image work.
ISSUE\t1020\tKEEP-SEPARATE\tF\tquestion\tgh issue edit 1020 --add-label question (rc=0)\tFunction-hook compatibility evaluation remains broader than the narrower result in merged PR #1023.
ISSUE\t1016\tKEEP-SEPARATE\tG\tenhancement\tgh issue edit 1016 --add-label enhancement (rc=0)\tOperator ruling moves agentsview out of this repo's next work; no destination issue was available to justify closure.
ISSUE\t1008\tKEEP-SEPARATE\tF\tbug\tgh issue edit 1008 --add-label bug (rc=0)\tThree cold-review inconsistencies remain independently actionable.
ISSUE\t1000\tKEEP-SEPARATE\tF\tbug\tNONE\tAgent-skill twin drift and dead pointers are an active orchestration/configuration defect.
ISSUE\t996\tKEEP-SEPARATE\tE\tbug\tNONE\tRenovate no longer proposes Graphify bumps after the backend move; currency automation defect.
ISSUE\t972\tKEEP-SEPARATE\tF\tenhancement\tNONE\tResume correctness must distinguish real agreement from under-checking.
ISSUE\t964\tKEEP-SEPARATE\tD\tenhancement\tNONE\tset -e makes the documented CI retry loop a reliability no-op.
ISSUE\t948\tKEEP-SEPARATE\tD\tbug\tNONE\tHook anchoring default reopens the #343 failure class.
ISSUE\t940\tBLOCKED-BY\tF\tenhancement\tNONE\tBody explicitly blocks on #927, #929-#935, and #920 before enabling the gate.
ISSUE\t936\tBLOCKED-BY\tF\tenhancement\tNONE\tBody explicitly blocks on #928.
ISSUE\t932\tBLOCKED-BY\tF\tenhancement\tNONE\tBody explicitly blocks on #918.
ISSUE\t928\tBLOCKED-BY\tF\tenhancement\tNONE\tBody explicitly blocks on #918.
ISSUE\t924\tKEEP-SEPARATE\tD\tenhancement\tNONE\tHook-guard logging migration is an unblocked reliability lane.
ISSUE\t920\tKEEP-SEPARATE\tF\tenhancement\tNONE\tShared eager-corpus budget work is explicitly unblocked.
ISSUE\t916\tKEEP-SEPARATE\tF\tenhancement\tNONE\tRule scoping epic remains the parent for its staged ticket map.
ISSUE\t912\tKEEP-SEPARATE\tD\tbug\tgh issue edit 912 --add-label bug (rc=0)\thk typos step ignores nonzero rc for ambiguous corrections; mutation-worthy fail-open.
ISSUE\t908\tKEEP-SEPARATE\tE\tbug\tgh issue edit 908 --add-label bug (rc=0)\tRoot lock regeneration adds undeclared node and blocks lock refresh; cause is not yet proven.
ISSUE\t888\tKEEP-SEPARATE\tG\tbug\tNONE\tLive branch-protection gap requires an explicit human choice among break-glass tradeoffs.
ISSUE\t884\tKEEP-SEPARATE\tF\tdocumentation\tgh issue edit 884 --add-label documentation (rc=0)\tProcedure and four runtime defects remain useful despite the temporary token-pressure framing.
ISSUE\t872\tBLOCKED-BY\tE\tenhancement\tNONE\tBody explicitly blocks on #856, #868, and #869.
ISSUE\t868\tBLOCKED-BY\tE\tenhancement\tNONE\tBody explicitly blocks on #856.
ISSUE\t864\tKEEP-SEPARATE\tG\tquestion\tNONE\tGraphify-memory meaning is an unresolved design decision.
ISSUE\t860\tDEFER-IMAGE\tC\tbug\tNONE\tarm64 platform tuple/variant semantics are part of the universal image architecture task.
ISSUE\t856\tKEEP-SEPARATE\tE\tenhancement\tNONE\tParameterized Graphify installer library is explicitly unblocked and non-image tooling.
ISSUE\t852\tDEFER-IMAGE\tC\tbug\tNONE\tubuntu-26.04-arm smoke failure directly gates the image matrix.
ISSUE\t848\tDEFER-IMAGE\tC\t-\tNONE\tMixed audit record materially defines bake axes and the multi-image topology; image owner must disposition it.
ISSUE\t772\tKEEP-SEPARATE\tF\tenhancement\tgh issue edit 772 --add-label enhancement (rc=0)\tOrchestration status contracts remain follow-up work from PR #770.
ISSUE\t764\tKEEP-SEPARATE\tF\tquestion\tgh issue edit 764 --add-label question (rc=0)\tBounded project-scoped research-adapter evaluation is independent of image bring-up.
ISSUE\t724\tKEEP-SEPARATE\tD\tbug\tNONE\tDirty-tree attribution is a ship/session-end integrity requirement.
ISSUE\t716\tKEEP-SEPARATE\tD\tbug\tNONE\tKnown workaround does not eliminate shared-hook rewriting by isolated worktrees.
ISSUE\t712\tKEEP-SEPARATE\tE\t-\tNONE\tGraphify dependency/execution boundary prototype remains distinct tooling work.
ISSUE\t708\tKEEP-SEPARATE\tF\t-\tNONE\tInstalled Codex project-contract catalog is orchestration research.
ISSUE\t692\tDEFER-IMAGE\tC\tdependencies\tNONE\tGCC prebuilt availability changes container image contents; delegated to image owner.
ISSUE\t688\tBLOCKED-BY\tD\t-\tNONE\tBody explicitly blocks on #687.
ISSUE\t684\tDEFER-IMAGE\tC\tenhancement\tNONE\tDriving a container through the typed library is devcontainer lifecycle work.
ISSUE\t680\tDEFER-IMAGE\tC\t-\tNONE\tGenerated container configuration models belong to the devcontainer task.
ISSUE\t640\tKEEP-SEPARATE\tE\tdependencies\tNONE\tPinned kb-setup predates its own description-budget fix; dependency currency work.
ISSUE\t608\tKEEP-SEPARATE\tD\t-\tNONE\tTwo proposed control-arm rule clauses remain a reliability-policy task.
ISSUE\t576\tKEEP-SEPARATE\tG\t-\tNONE\tBudget guardrails and fan-out caps require the recorded grilling decision.
ISSUE\t572\tKEEP-SEPARATE\tF\t-\tNONE\tVerb spawn helper is a discrete Wayfinder orchestration task.
ISSUE\t556\tKEEP-SEPARATE\tF\t-\tNONE\tWayfinder map remains the parent for the autonomous DAG framework.
ISSUE\t536\tKEEP-SEPARATE\tD\tbug\tgh issue edit 536 --add-label bug --remove-label needs-triage (rc=0)\tMeasured PreToolUse latency/timeouts are a live performance and fail-open defect.
ISSUE\t528\tKEEP-SEPARATE\tG\t-\tNONE\tIssue is intentionally deferred pending Python 3.15/PEP 810 and carries needs-info.
ISSUE\t524\tKEEP-SEPARATE\tD\t-\tNONE\tGuard latency and fail-closed timeout behavior remain active reliability work.
ISSUE\t496\tKEEP-SEPARATE\tG\t-\tNONE\tSecrets resolution ownership requires a design ruling.
ISSUE\t492\tKEEP-SEPARATE\tD\t-\tNONE\tStructural confinement research addresses a security/reliability boundary.
ISSUE\t488\tKEEP-SEPARATE\tG\t-\tNONE\tWhether 49 sync blocks enter the baseline is an unresolved policy choice.
ISSUE\t476\tKEEP-SEPARATE\tF\tenhancement\tgh issue edit 476 --add-label enhancement (rc=0)\tMemory-curation redesign contains measured defects and remains orchestration work.
ISSUE\t376\tKEEP-SEPARATE\tF\tquestion\tgh issue edit 376 --add-label question (rc=0)\tCross-session communication substrate spike is explicitly separate from the Graphify queue.
ISSUE\t356\tKEEP-SEPARATE\tF\tbug\tgh issue edit 356 --add-label bug (rc=0)\tTranscript audit remains blind in the dotfiles cwd where delegation occurs.
ISSUE\t340\tKEEP-SEPARATE\tD\tenhancement\tNONE\tADR-0001 skip matching is an unresolved gate-correctness question.
ISSUE\t336\tKEEP-SEPARATE\tD\tenhancement\tNONE\tAuthor-time suppression detection is distinct from commit-time enforcement.
ISSUE\t316\tKEEP-SEPARATE\tF\tenhancement\tNONE\tGraphify adoption documentation ticket remains open; no merged PR explicitly closes #316.
ISSUE\t312\tCLOSE\t-\tenhancement\tgh issue close 312 --comment <completed-by-PR-319> (rc=0)\tMerged PR #319 explicitly implements #312 at commit 7d2a1ddc396e5358e4db5701dc9606acf8c24016.
ISSUE\t304\tKEEP-SEPARATE\tG\t-\tNONE\tUpstream hk discussion draft is explicitly ready-for-human and not yet filed.
ISSUE\t284\tKEEP-SEPARATE\tE\tdependencies\tgh issue edit 284 --add-label dependencies (rc=0)\tFloating ty LSP diverges from the project pin.
ISSUE\t280\tKEEP-SEPARATE\tF\tdocumentation\tNONE\tPlugin disable semantics and cross-scope conflicts need canonical documentation.
ISSUE\t268\tKEEP-SEPARATE\tB\tbug\tgh issue edit 268 --add-label bug (rc=0)\thk write-lock deadlock is direct hk-engine work and the root cause for #304.
ISSUE\t252\tDEFER-IMAGE\tC\tenhancement\tNONE\tGraphviz installation method changes the container image.
ISSUE\t224\tDEFER-IMAGE\tC\tenhancement\tNONE\tDevcontainer image-matrix epic is universal-task material; image owner controls closure.
ISSUE\t220\tKEEP-SEPARATE\tG\tbug\tgh issue edit 220 --add-label bug (rc=0)\tRoot cause is in the external MDE repo and waits for a deliberate migration.
ISSUE\t168\tDEFER-IMAGE\tC\tquestion\tNONE\tapt bootstrap arguments are scoped to Docker-image package installation.
ISSUE\t164\tKEEP-SEPARATE\tB\tenhancement\tgh issue edit 164 --add-label enhancement (rc=0)\tAdopting hk's rumdl builtin belongs with hk-engine work.
ISSUE\t160\tDEFER-IMAGE\tC\tenhancement\tNONE\tDevcontainer build-input observability and p2996 re-tiering are image architecture.
ISSUE\t116\tDEFER-IMAGE\tC\tenhancement\tNONE\tCompleted-looking build/publish epic is image-owned; this lane made no closure mutation.
ISSUE\t104\tKEEP-SEPARATE\tE\tenhancement\tNONE\tCI mise tool-scope optimization is tooling work, not devcontainer bring-up.
ISSUE\t92\tDEFER-IMAGE\tC\tenhancement\tNONE\tTrivy gating depends on the devcontainer image CVE baseline.
ISSUE\t76\tDEFER-IMAGE\tC\tenhancement\tNONE\tDockerfile.host-user package hardening is direct image work.
ISSUE\t72\tDEFER-IMAGE\tC\tbug\tNONE\tContainer persistence and verify-local behavior belong to universal devcontainer verification.
ISSUE\t64\tKEEP-SEPARATE\tB\tbug\tgh issue edit 64 --add-label bug (rc=0)\thk stash/restore can resurrect deleted files; direct hk defect.
ISSUE\t20\tDEFER-IMAGE\tC\tenhancement\tNONE\tRestoring cppclean changes the devcontainer image toolchain.
ISSUE\t12\tDEFER-IMAGE\tC\tenhancement\tNONE\tOverlay smoke-test CI is part of devcontainer image verification.
ISSUE\t4\tKEEP-SEPARATE\tF\tenhancement\tgh issue edit 4 --add-label enhancement (rc=0)\tChezmoi management of Claude skills/hooks/rules is agent-configuration orchestration.
```

## Final specialist report — image specialist (verbatim)

Triaged 79 image/devcontainer-surface issues: 17 SUBSUME, 43 KEEP-SEPARATE, 16 CLOSE, 3 BLOCKED-BY.

```tsv
ISSUE\t5\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tlabeled:enhancement;closed:not_planned\tSuperseded by #669/#678 after #676 and #677 delivered multi-arch publication and isolated runtime resources.
ISSUE\t6\tKEEP-SEPARATE\tD=TOOLCHAIN-CURRENCY\tquestion\tlabeled:question\tPixi isolation is an independent toolchain-design question, not required for two running containers.
ISSUE\t11\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tThe universal smoke must prove the published image has one coherent UID-1000 identity.
ISSUE\t12\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tThe host-user overlay is part of each real local container and therefore belongs in the live verification outcome.
ISSUE\t13\tKEEP-SEPARATE\tH=DOCS-POLICY-HARDENING\tenhancement\tNONE\tThis is static no-vscode scan coverage, independent of concurrent runtime success.
ISSUE\t14\tKEEP-SEPARATE\tH=DOCS-POLICY-HARDENING\tenhancement\tNONE\tThis deduplicates CI policy enforcement and does not affect the two-container outcome.
ISSUE\t15\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tclosed:completed\tImplemented at python/src/dotfiles_setup/image.py:1007-1017 for user, group, home, and environment.
ISSUE\t17\tCLOSE\tG=IMAGE-OPTIMIZATION\tenhancement\tclosed:completed\t#240/#241 and image-analysis.yml:134-152 now report compressed size, tool count, smoke result, and CI build time.
ISSUE\t19\tKEEP-SEPARATE\tH=DOCS-POLICY-HARDENING\tdocumentation\tNONE\tThis documents cross-host UID behavior and does not gate the Mac-local two-architecture outcome.
ISSUE\t20\tKEEP-SEPARATE\tD=TOOLCHAIN-CURRENCY\tenhancement\tlabeled:enhancement\tCppclean restoration is an independent image-tool compatibility task.
ISSUE\t22\tKEEP-SEPARATE\tD=TOOLCHAIN-CURRENCY\tenhancement\tlabeled:enhancement\tGraphviz restoration is independent image content work.
ISSUE\t33\tCLOSE\tE=IMAGE-HYGIENE\tdocumentation\tlabeled:documentation;closed:not_planned\tThe issue itself records the bun message as unsuppressible and already documented; actionable warning work remains under #689.
ISSUE\t72\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tlabeled:bug\tThe universal outcome includes persistence, and this stale advisory weakens that public gate.
ISSUE\t73\tKEEP-SEPARATE\tH=DOCS-POLICY-HARDENING\tdocumentation\tlabeled:documentation\tThis corrects historical research prose, not runtime behavior.
ISSUE\t74\tKEEP-SEPARATE\tH=DOCS-POLICY-HARDENING\tdocumentation\tlabeled:documentation\tThis protects documentation presence independently of live verification.
ISSUE\t76\tKEEP-SEPARATE\tE=IMAGE-HYGIENE\tenhancement\tlabeled:enhancement\tExplicit openssh-client installation is defense-in-depth, not required to resolve current concurrency.
ISSUE\t78\tKEEP-SEPARATE\tE=RUNTIME-ALTERNATIVES\tenhancement\tNONE\tDocker Desktop remains the supported runtime; Colima evaluation is a deferred alternative.
ISSUE\t82\tKEEP-SEPARATE\tG=IMAGE-OPTIMIZATION\tenhancement\tlabeled:enhancement\tCompiler-cache optimization is not necessary to prove correct concurrent operation.
ISSUE\t92\tKEEP-SEPARATE\tE=IMAGE-SECURITY\tenhancement\tlabeled:enhancement\tPromoting Trivy to a gate is security-policy work independent of local bring-up.
ISSUE\t102\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tclosed:not_planned\tThe research spike is superseded by #669 and completed substrate issues #676/#677.
ISSUE\t116\tKEEP-SEPARATE\tE=CI-IMAGE-PIPELINE\tenhancement\tNONE\tThe reusable workflow epic is a broader CI-delivery carrier.
ISSUE\t160\tKEEP-SEPARATE\tE=CI-IMAGE-PIPELINE\tenhancement\tNONE\tBuild-input observability and re-tiering remain a broader image-maintenance epic.
ISSUE\t166\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tlabeled:enhancement;closed:not_planned\tThe multi-Ubuntu matrix was retired when #849 closed NOT_PLANNED.
ISSUE\t167\tKEEP-SEPARATE\tG=IMAGE-OPTIMIZATION\tquestion\tlabeled:question\tMise OCI layering remains upstream-dependent research.
ISSUE\t168\tKEEP-SEPARATE\tD=TOOLCHAIN-CURRENCY\tquestion\tlabeled:question\tThis is an upstream mise bootstrap-package request, not local runtime work.
ISSUE\t222\tKEEP-SEPARATE\tG=IMAGE-OPTIMIZATION\tenhancement\tNONE\tImage size and pull-speed optimization follows capability correctness.
ISSUE\t223\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tIts shared smoke and Linux validation requirements directly strengthen the universal verification surface.
ISSUE\t224\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tclosed:not_planned\tThe dual-arch portion is superseded and its Ubuntu cross-product axis was retired by #849.
ISSUE\t243\tCLOSE\tD=TOOLCHAIN-CURRENCY\tenhancement\tlabeled:enhancement;closed:not_planned\t#841 explicitly supersedes this GCC 16.1 request with the current GCC 16.2 design.
ISSUE\t252\tKEEP-SEPARATE\tD=TOOLCHAIN-CURRENCY\tenhancement\tNONE\tThis evaluates Graphviz packaging mechanics independently.
ISSUE\t254\tKEEP-SEPARATE\tD=TOOLCHAIN-CURRENCY\tenhancement\tlabeled:enhancement\tThis remains a broad post-PR-C follow-up tracker.
ISSUE\t339\tKEEP-SEPARATE\tE=IMAGE-HYGIENE\tenhancement\tNONE\tThe hk warning has its own non-devcontainer cause and carrier.
ISSUE\t370\tKEEP-SEPARATE\tE=LOCK-MANAGEMENT\tbug\tNONE\tRoot mise.lock corruption is a broader lock-management defect.
ISSUE\t410\tKEEP-SEPARATE\tH=DOCS-POLICY-HARDENING\tdocumentation\tNONE\tThis corrects overlay documentation rather than runtime behavior.
ISSUE\t411\tKEEP-SEPARATE\tE=DELIVERY-CORRECTNESS\tbug\tlabeled:bug\tThe ship surface-path omission is delivery correctness outside the live two-container proof.
ISSUE\t669\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tcommented\tUse this as the single universal carrier, narrowed to two concurrent verified containers.
ISSUE\t678\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tlabeled:enhancement;commented\t#676/#677 are closed; native arm64 is unblocked and becomes one leg of the universal outcome.
ISSUE\t679\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tquestion\tlabeled:question\tShutdown behavior can invalidate simultaneous operation and must be measured in the universal task.
ISSUE\t684\tKEEP-SEPARATE\tF=REUSABLE-LIFECYCLE-SDK\tenhancement\tlabeled:enhancement\tThe typed reusable library is a broader architecture effort; existing public mise tasks can prove the local outcome.
ISSUE\t685\tKEEP-SEPARATE\tF=REUSABLE-LIFECYCLE-SDK\tenhancement\tlabeled:enhancement\tNew lifecycle library verbs are not prerequisites for the existing public up/down/verify workflow.
ISSUE\t686\tKEEP-SEPARATE\tF=REUSABLE-LIFECYCLE-SDK\tenhancement\tlabeled:enhancement\tRaw-command refusal is a policy/library phase independent of proving the current public workflow.
ISSUE\t689\tKEEP-SEPARATE\tE=IMAGE-HYGIENE\tenhancement\tlabeled:enhancement\tWarning classification is a cross-cutting quality gate, not part of the two-container completion bar.
ISSUE\t690\tKEEP-SEPARATE\tF=REUSABLE-LIFECYCLE-SDK\tenhancement\tlabeled:enhancement\tA second consuming repository proves reusability, not this Mac's two-container outcome.
ISSUE\t691\tCLOSE\tD=TOOLCHAIN-CURRENCY\tenhancement\tlabeled:enhancement;closed:not_planned\t#841 replaced the both-architecture GCC design with an arm64-scoped conda pin and asymmetric counts.
ISSUE\t692\tCLOSE\tD=TOOLCHAIN-CURRENCY\tdependencies\tlabeled:dependencies;closed:not_planned\t#841 carries the current stable-GCC and remaining LLVM-upstream work.
ISSUE\t699\tKEEP-SEPARATE\tG=IMAGE-OPTIMIZATION\tenhancement\tlabeled:enhancement\tGHA cache-budget accounting is CI optimization.
ISSUE\t722\tKEEP-SEPARATE\tE=IMAGE-SECURITY\tenhancement\tNONE\tLifecycle-scoped secret delivery is a separate security architecture.
ISSUE\t723\tKEEP-SEPARATE\tE=LOCK-MANAGEMENT\tbug\tNONE\tThe generated feature lock is configuration-integrity work.
ISSUE\t739\tKEEP-SEPARATE\tE=IMAGE-HYGIENE\tbug\tlabeled:bug\tThe BuildKit secrets warning retains its own security-focused carrier.
ISSUE\t745\tKEEP-SEPARATE\tE=CI-IMAGE-PIPELINE\tbug\tNONE\tARM runner disk-cleanup warnings affect CI hygiene, not local dual-container verification.
ISSUE\t769\tBLOCKED-BY\tF=HOST-RESOURCE-BROKER\tenhancement\tlabeled:enhancement\tBlocked by #766; its multi-repository resource broker is broader than this task.
ISSUE\t838\tKEEP-SEPARATE\tG=IMAGE-OPTIMIZATION\tenhancement\tlabeled:enhancement;removed:needs-triage;commented\tA mise OCI layering pilot is optional optimization and must not expand the universal outcome.
ISSUE\t841\tKEEP-SEPARATE\tD=TOOLCHAIN-CURRENCY\tdependencies\tlabeled:dependencies;commented\tGCC 16.2 and LLVM 23 currency remain separate; their asymmetry informs universal smoke.
ISSUE\t845\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tlabeled:bug\tThe universal smoke must ask mise inside each architecture rather than predict filtering on macOS.
ISSUE\t851\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tThe current two-target model requires an explicitly pinned amd64 Ubuntu 26.04 runner.
ISSUE\t852\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tcommented\tThe recurrent Ubuntu 26.04 arm smoke failure must be diagnosed before the arm leg can become authoritative.
ISSUE\t853\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tclosed:not_planned\tIts #849 base-track permutation was retired; two explicit Ubuntu 26.04 legs need no track axis.
ISSUE\t854\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tNONE\tThe amd64 microarchitecture value affects publication, pulling, and architecture verification.
ISSUE\t860\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tNONE\tArm64 variant erasure must be normalized consistently or architecture checks can disagree.
ISSUE\t861\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tquestion\tNONE\tThe image_exec cadence must be known so the universal verification cannot silently remain deselected.
ISSUE\t865\tKEEP-SEPARATE\tE=CI-IMAGE-PIPELINE\tquestion\tNONE\tWhether hosted macOS can build Linux images is independent runner research.
ISSUE\t866\tBLOCKED-BY\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tcommented\tBlocked by #852; promotion is required only after the current arm smoke failure is explained.
ISSUE\t867\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tclosed:not_planned\tThe independent base-track axis was retired by #849.
ISSUE\t870\tBLOCKED-BY\tC=UNIVERSAL-DEVCONTAINER\tbug\tcommented\tBlocked by #861; establish the real exec-test cadence before reproducing its failures.
ISSUE\t871\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tclosed:not_planned\tMultiple per-track OCI indexes are unnecessary after the base-track axis was retired.
ISSUE\t873\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tenhancement\tclosed:not_planned\tThe operator selected two Ubuntu 26.04 containers, not a third arm64/24.04 container.
ISSUE\t887\tKEEP-SEPARATE\tE=LOCK-MANAGEMENT\tdependencies\tlabeled:dependencies\tRenovate image-lock regeneration is dependency automation.
ISSUE\t907\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tlabeled:bug\tA false persistence failure makes the required real verification unreliable.
ISSUE\t909\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tlabeled:bug\tSync must reject or repair an image that matches by digest but cannot run.
ISSUE\t963\tKEEP-SEPARATE\tE=LOCK-MANAGEMENT\tbug\tNONE\tThe CI-only --no-container lock perturbation is separate lock tooling.
ISSUE\t974\tKEEP-SEPARATE\tE=RUNTIME-ALTERNATIVES\tdocumentation\tNONE\tThe already-shelved third macOS environment remains outside the two-Linux-container outcome.
ISSUE\t985\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tNONE\tThe amd64 half of the moving tag must be pullable by the universal amd64 leg.
ISSUE\t1046\tKEEP-SEPARATE\tE=CI-IMAGE-PIPELINE\tbug\tNONE\tManifest-only rerun recovery is an independent CI operational defect.
ISSUE\t1105\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tbug\tlabeled:bug;closed:completed\tIts retired children were closed while current #852/#866 were retained.
ISSUE\t1106\tSUBSUME\tC=UNIVERSAL-DEVCONTAINER\tbug\tlabeled:bug;commented\tIt records that production arm64 still uses ubuntu-24.04-arm while #852→#866 moves authority to 26.04.
ISSUE\t1107\tCLOSE\tC=UNIVERSAL-DEVCONTAINER\tbug\tlabeled:bug;closed:completed\tLive state confirms #676/#677 closed and #678 unblocked.
ISSUE\t1116\tKEEP-SEPARATE\tE=DEPENDENCY-AUTOMATION\tdependencies\tlabeled:dependencies\tRenovate grouping for hk image inputs belongs before image work but is not part of the runtime outcome.
ISSUE\t1121\tKEEP-SEPARATE\tE=LOCK-MANAGEMENT\tbug\tlabeled:bug\tlock-shared bring-up/timeout behavior is a distinct tool boundary, not the universal devcontainer lifecycle.
```

Universal task text:

> Phase C — UNIVERSAL-DEVCONTAINER: two architecture-isolated devcontainers concurrently running and verified on this Mac
>
> After PR #1128 and hk v2 land, bring up exactly two containers from this clone: `linux/amd64/v2` through the default profile and `linux/arm64/v8` through `MISE_ENV=arm64`. The containers must remain up simultaneously and have distinct container names, `dotfiles.arch` labels, home volumes, SSH ports, and overlay tags.
>
> Public positive path, with every direct return code captured:
>
> 1. `mise run names` → rc 0; `MISE_ENV=arm64 mise run names` → rc 0. Parsed name, volume, port, and architecture values must differ.
> 2. `mise run sync` → rc 0; `mise run up` → rc 0.
> 3. `MISE_ENV=arm64 mise run sync` → rc 0; `MISE_ENV=arm64 mise run up` → rc 0.
> 4. `mise run verify-local` → rc 0 and `MISE_ENV=arm64 mise run verify-local` → rc 0. This public chain already sequences image verification, bring-up, process visibility, `verify-arch`, smoke, persistence, R1 inbound SSH, and secrets at `mise.toml:1118-1139`.
> 5. `mise run verify-container-latest` and its arm64-profile equivalent → rc 0.
> 6. `mise run verify-arch` → rc 0 and `MISE_ENV=arm64 mise run verify-arch` → rc 0.
> 7. `mise run verify-ssh-inbound` → rc 0 and its arm64-profile equivalent → rc 0.
> 8. Add/use a public `mise run verify-ssh-outbound` wrapper that converts GitHub’s successful `ssh -T` message into task rc 0; both profiles must return rc 0.
> 9. Read-only `docker ps --filter label=dotfiles.workspace=<resolved-hash>` → rc 0 and exactly two rows: one `dotfiles.arch=amd64`, one `dotfiles.arch=arm64`; rerun both `verify-arch` tasks afterward to prove bringing up the second did not orphan the first.
>
> Architecture-aware smoke:
>
> - Common tools and lifecycle invariants must pass on both images.
> - Declared image tools must be derived using mise inside the target image (#845), not a macOS reimplementation.
> - Do not require content symmetry: the reflection/trunk compiler exists only where upstream publishes it; arm64 must not fail for its deliberate absence.
> - Keep GCC/LLVM currency in #841, but use its declared architecture scope when calculating expected tools.
> - The moving `:dev` index must be pullable for amd64 and arm64 (#985); arm64 variant normalization must account for containerd erasing `/v8` (#860).
>
> Required discriminating controls:
>
> - In an isolated public-CLI fixture, return amd64 image/uname/arch signals for an arm64 request: `verify-arch` must return nonzero. Reverting request-derived expectation to fixed x86_64 must make this test fail.
> - Mutate architecture out of the name/volume/port derivation: the isolation test must fail on a collision.
> - Feed smoke an arm64 image lacking the amd64-only compiler: architecture-aware smoke returns 0; mutate expected-tool selection back to symmetric and it returns nonzero.
> - Give sync a digest-matching but non-runnable image fixture: it must rebuild or return nonzero; a healthy same-digest image remains the positive control.
> - Remove the image_exec CI/task cadence established by #861: the coverage contract must fail.
> - Keep the real two-container run as the integration proof; fixture controls supplement it and cannot replace it.
>
> `verify-arch` already satisfies #678’s sharp criterion: it derives expected architecture and machine from the active `DOTFILES_PLATFORM` at `mise.toml:1021-1064`; `expected_uname_machine()` maps the requested platform through `platform_arch()` at `python/src/dotfiles_setup/platform_target.py:484-486`.

Mutation and evidence summary:

- Initial inventory: `gh issue list --state open --limit 500 ...` → 335, rc 0; search API `total_count` → 335, rc 0.
- Premises: #676 CLOSED rc 0; #677 CLOSED rc 0; #849 CLOSED rc 0; #678 OPEN rc 0.
- Added type labels to 40 previously untyped image-surface issues; every `gh issue edit --add-label` returned rc 0.
- Removed `needs-triage` from #838; rc 0.
- Closed 16 issues above with cited one-line comments; every `gh issue close` returned rc 0.
- Posted successful disposition comments on #669, #841, #852, #866, #870, and #1106; rc 0.
- #678 corrective comment: https://github.com/ray-manaloto/dotfiles/issues/678#issuecomment-5690057899, rc 0.
- #838 corrective comment: https://github.com/ray-manaloto/dotfiles/issues/838#issuecomment-5690058868, rc 0. The preceding malformed comment was preserved as instructed.
- Post-mutation live controls both reported 317 open issues, rc 0; this is repository-wide concurrent state, not solely this shard’s delta.
- No repository file, gate, git command, or raw Docker lifecycle mutation was used.

Containment record:

- An unsafe quoted `gh issue comment 678` command expanded Markdown backticks and accidentally invoked the two bring-up commands. Exact ancestry was `zsh 60687 → mise 61305 → fnox 61345 → devcontainer 61418 → docker buildx 61991`.
- `kill -TERM 60687` → rc 0; descendants were reparented.
- `kill -TERM 61991 61418 61345 61305` → rc 0.
- Process-control probe afterward → rc 0 with no matching child remaining.
- Read-only labeled-container inspection → rc 0 and exactly the pre-existing amd64 container `b954aff8b809`; no arm64 container was created and the amd64 container was not torn down.
- #678 JSON inspection showed the unsafe command posted no comment. The intended comment was posted using `--body-file`; temporary body files were deleted and absence verification returned rc 0.

## Dispatcher fallback and machine reconciliation

The collaboration runtime refused the workflows-specialist spawn twice with `agent thread limit reached`, including after the config specialist reported completion. These were not `no thread with id` failures, so the spec's historyless retry rule did not apply. No documentation-specialist spawn was attempted after the runtime demonstrated that the slot could not be reclaimed; the dispatcher completed modulo-2 and modulo-3 directly.

The image specialist's prose summary says 79 rows / 43 KEEP-SEPARATE, but its persisted ledger contains **78 unique rows / 42 KEEP-SEPARATE**. Machine parsing gives 17 SUBSUME + 42 KEEP-SEPARATE + 16 CLOSE + 3 BLOCKED-BY = 78. The canonical synthesis uses the ledger, not the header. Three shard rows deferred to image but absent from the image ledger are resolved here:

- #680 — KEEP-SEPARATE, phase F: generated container models are reusable-lifecycle architecture, not required for the two-container outcome.
- #681 — KEEP-SEPARATE, phase D: nonblocking event sinks are observability/reliability work.
- #848 — KEEP-SEPARATE, phase F: the audit record remains useful provenance but is not an executable universal-task child.

Dispatcher mutations:

- Resolved non-image `needs-triage` on #298, #538, #539, #882, #883, #1042, and #1043; each direct `gh issue edit` returned rc=0.
- Added an existing type label to the 40 remaining unlabelled survivors: #31, #75, #163, #266, #283, #354, #355, #358, #474, #718, #730, #747, #766, #771, #787, #823, #835, #910, #911, #967, #1014, #1015, #1018, #1050, #1058, #1059, #1098, #1099, #1102, #1103, #1110, #1111, #1114, #1115, #1118, #1119, #1122, #1123, #1126, #1127. Every direct edit returned rc=0.
- Post-mutation controls: issue-list count 317 rc=0; search API count 317 rc=0; open unlabelled count 0 rc=0; open `needs-triage` count 0 rc=0.

Two read-only reconciliation attempts were rejected as evidence: one confused real TSV tabs with literal `\t` strings and failed rc=1; another over-escaped the digit regex and returned zero image rows. Direct literal-delimiter parsing then found 78 unique image rows and the full canonical union.

## Canonical 335-issue disposition

Precedence is exclusive and exhaustive:

1. The 78-row image ledger above owns those issue numbers.
2. The Python ledger owns modulo-0 numbers not present in the image ledger.
3. The config ledger owns modulo-1 numbers not present in the image ledger.
4. The dispatcher owns modulo-2/modulo-3 numbers not present in the image ledger, plus the three explicit resolutions above.

Machine reconciliation against the frozen TSV reports 335 canonical numbers, no missing numbers, and no extras. Final dispositions:

| Disposition | Count |
|---|---:|
| KEEP-SEPARATE | 281 |
| BLOCKED-BY | 19 |
| SUBSUME | 17 |
| CLOSE | 18 |
| **Total** | **335** |

The 317 surviving issues map to these phases:

- **B — hk v2 follow-through (8):** #31, #64, #69, #163, #164, #165, #268, #729.
- **C — one universal devcontainer outcome (19):** #11, #12, #72, #223, #669, #678, #679, #845, #851, #852, #854, #860, #861, #866, #870, #907, #909, #985, #1106.
- **D — reliability and security (74):** #101, #314, #336, #337, #340, #354, #358, #431, #474, #489, #492, #524, #536, #537, #542, #608, #610, #681, #687, #688, #715, #716, #721, #724, #725, #771, #787, #829, #831, #835, #858, #910, #911, #912, #919, #921, #924, #925, #929, #933, #935, #939, #948, #949, #954, #964, #965, #981, #1030, #1031, #1041, #1042, #1043, #1049, #1055, #1056, #1057, #1096, #1097, #1098, #1099, #1100, #1101, #1102, #1108, #1110, #1111, #1112, #1114, #1115, #1119, #1120, #1123, #1124.
- **E — tooling, currency, image hygiene, and CI operations (92):** #6, #7, #20, #22, #75, #76, #78, #82, #92, #103, #104, #116, #160, #167, #168, #193, #222, #225, #252, #253, #254, #255, #257, #258, #281, #284, #293, #310, #313, #315, #317, #318, #339, #370, #375, #411, #538, #569, #571, #598, #640, #689, #699, #707, #709, #712, #717, #718, #722, #723, #730, #739, #745, #765, #838, #841, #850, #855, #856, #859, #865, #868, #869, #872, #874, #882, #883, #887, #889, #908, #923, #930, #943, #953, #963, #974, #993, #996, #997, #1046, #1050, #1054, #1058, #1059, #1060, #1103, #1104, #1116, #1117, #1118, #1121, #1122.
- **F — documentation and orchestration (84):** #4, #13, #14, #19, #73, #74, #266, #280, #282, #283, #316, #355, #356, #376, #410, #476, #479, #499, #539, #550, #556, #570, #572, #579, #597, #605, #606, #607, #680, #682, #683, #684, #685, #686, #690, #708, #747, #764, #766, #769, #772, #823, #833, #847, #848, #857, #862, #863, #884, #916, #917, #918, #920, #922, #926, #927, #928, #931, #932, #934, #936, #937, #938, #940, #942, #951, #967, #971, #972, #986, #994, #999, #1000, #1008, #1020, #1024, #1027, #1028, #1029, #1032, #1125, #1126, #1127, #1137.
- **G — deferred / needs-human (40):** #220, #279, #298, #302, #304, #470, #471, #488, #490, #491, #493, #494, #495, #496, #497, #498, #503, #528, #534, #566, #576, #577, #581, #582, #583, #590, #623, #710, #711, #713, #714, #864, #888, #891, #941, #1014, #1015, #1016, #1017, #1018.

Closed issues and reasons:

- #5 — superseded by #669/#678 after #676/#677 delivered publication and isolation.
- #15 — implemented at `python/src/dotfiles_setup/image.py:1007-1017`.
- #17 — metrics now reported by #240/#241 and `image-analysis.yml:134-152`.
- #33 — warning is unsuppressible/documented; actionable warning work remains #689.
- #102 — research spike superseded by #669 and completed #676/#677.
- #166 — multi-Ubuntu axis retired with #849.
- #224 — dual-arch portion superseded; cross-product retired by #849.
- #243 — superseded by #841's GCC 16.2 design.
- #312 — implemented by merged PR #319 at `7d2a1ddc396e5358e4db5701dc9606acf8c24016`.
- #691 — replaced by #841's architecture-scoped compiler design.
- #692 — remaining compiler work carried by #841.
- #853 — base-track permutation retired by #849.
- #867 — independent base-track axis retired by #849.
- #871 — per-track indexes unnecessary after #849.
- #873 — operator selected two Ubuntu 26.04 containers, not a third arm64/24.04 container.
- #881 — existing WONTFIX record documents five independent DO NOT SHIP reviews.
- #1105 — retired children closed; current #852/#866 retained.
- #1107 — premise resolved: #676/#677 are closed and #678 is unblocked.

## Final verification

- Live controls: `gh issue list` = 317, search API `.total_count` = 317, unlabelled = 0, `needs-triage` = 0, and carrier #669 remains OPEN; every command returned rc=0.
- A public-interface audit re-read the frozen corpus, fetched the live open set through `gh issue list`, and parsed both coordinator artifacts. It returned rc=0 with phase counts B=8, C=19, D=74, E=92, F=84, G=40; the plan and report sets match; the phase union equals all 317 live issues; and the 18 documented closures plus the live set equal all 335 frozen issues with no overlap, omissions, or extras.
- The first audit arm returned rc=1 after a deliberately strict parser omitted the TSV's leading `#` and therefore found zero frozen rows. Hex inspection established the actual public format (`#<number><TAB>...`); the corrected parser is the successful arm above. No repository gates were run, per the specification.

Status: complete.
