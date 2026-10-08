# GitHubKit and native mise/fnox: complete Downloads review and fix handoff

Prepared 2026-10-08 for the Downloads project owner. **Revised Q5 is APPROVED for the bounded dotfiles migration. This document is the complete Downloads owner review/fix handoff; no Downloads application fixes have been performed.** It covers every finding from this migration/SDK/search review, not a new audit of unrelated PDF behavior. The required search outcome remains real GitHubKit repository, issue, pull-request and discussion search with saved, tunable, rerunnable definitions and trustworthy run history. [R2]

All local source references are relative to the named workspace root. “Downloads” means this project's workspace; “dotfiles” means the separate coordination repository. Paths identify reviewed sources, not instructions to overwrite another owner's work.

## What this review establishes

Downloads already has an installed GitHubKit 0.16.1 client, generated SDK schemas, a declarative JSON catalog, native task-secret declarations and a working selected-query rerun. Live SDK requests succeeded for repository search through the TOPIC branch, issues and PRs. The complete requested contract is not yet satisfied: the REPOSITORY branch returns false empty success; issue classification mishandles the SDK's UNSET sentinel; requested credentials failed to resolve through the observed route; pagination, completeness, immutable snapshots and safe diffs are missing. [D1, D2]

Dotfiles has a richer existing saved-search contract using tracked TOML, automatic query recording, controls, snapshots and comparable-result diffs. Its current transport is gh, so it does not satisfy the newly explicit GitHubKit requirement. Its kinds omit repositories; PR queries use the issues family with an is:pr qualifier. Preserve the existing saved-query contract while replacing or extending only the necessary transport and result-kind boundaries in a separately owned migration. [F1]

That migration must explicitly review the shared GitHub producer search and automatic-recording integration in `research_fanout.py` alongside saved reruns. Reuse a GitHubKit search adapter for the four required kinds wherever those paths share the same semantics, preserving the exact native fnox launcher and strict-five receipt/control contract. Existing gh-based receipts remain evidence of gh execution. Any retained gh operation outside those four kinds, such as release metadata, needs a named boundary; the producer search path is not silently exempted. Source overlap with held #1774 requires separate ownership and dependency admission. [F1]

The old graphify-prs-only proposal and default/GITHUB_TOKEN credential suggestion are superseded as adoption-ready recommendations. The user accepted ordinary native task grants plus retained exact research/bootstrap launches, and a separate KB compatibility prerequisite. The initial final-confirmation proposal was superseded; the user then approved revised Q5 and explicitly required every found Downloads issue in this handoff. The separate dotfiles migration may proceed within that approval. Downloads application changes remain with the current project owner; global credential changes, parked workflows and KB activation retain their stated boundaries. No further Q5 confirmation is requested. [R2]

## Observed implementation and live controls

Reviewed Downloads branch: `feature/webclaw-openrouter-intel`, HEAD `56aaf1af794fa50df175e1682c5404adb29615c2`, with concurrent owner edits. The receipt records source hashes; re-attest the actual branch and dirty files before any later implementation. This review preserved the owner's changes. [D2]

The final source check found 17 reviewed source hashes unchanged while root `AGENTS.md` changed concurrently. Both instruction-file hashes are retained in the receipt. Re-read the current instructions before applying this review. [D2]

| Required behavior | Observed implementation | Current evidence and gap |
|---|---|---|
| Repositories | `execute_topic_search` calls `client.rest.search.repos`; the enum also accepts REPOSITORY. | TOPIC query `repo:jdx/mise` returned 1/1 twice. The identical REPOSITORY query returned 0/0 with no request branch and no error. Repair dispatch before declaring repository support. [D3] |
| Issues | GitHubKit `issues_and_pull_requests` adds `is:issue`. | Returned 10 of 13. Ten issue URLs were wrongly marked `is_pr=true` because SDK UNSET is distinct from None. [D3, D4] |
| Pull requests | Same SDK method adds `is:pr`. | Returned 10 of 207. Persist the effective qualified query; the stored query currently omits the appended type qualifier. [D3] |
| Discussions | GitHubKit GraphQL `search(query:..., type:DISCUSSION, first:10)`. | This is actual query matching, not repository discussion listing. Live request returned HTTP 403/rate-limit; no successful authenticated witness. Repository identity is not selected/stored; pageInfo and cursors are absent. [D3] |
| Existing code searches | GitHubKit `client.rest.search.code`. | Both positive and absent-result controls returned HTTP 401. The absent control is not evidence of zero matches. Preserve code behavior and obtain valid controls after credential admission. [D2, D3] |
| Saved and tunable queries | JSON catalog with IDs, descriptions, query and optional filters/sort/order. | Seventeen definitions exist. PR and REPOSITORY examples are absent; filters are not validated per API kind. [D5] |
| Reruns | Existing CLI supports catalog, selected target, output directory and report path. | Selected TOPIC ID reran through the SDK into a second audit directory and returned 1/1. This proves replay, not automatic snapshots or diffs. [D2, D6] |
| Deep and paging controls | `--deep` is accepted but discarded. REST per_page and GraphQL first are fixed at ten. | No effective deep selection, page budget, complete collection or explicit completeness field. [D3, D6] |
| History and reports | Writes `<output-dir>/<id>.json`; report scans all JSON in that directory. | Same-ID output overwrites; stale files may enter reports. No run manifest or native diff. Report omits explicit error rows and labels application 0.2.0 as GitHubKit. [D6] |

The native task dry-run returned rc 0 and listed requested GITHUB_TOKEN without resolving it. The seven-query live run also returned rc 0, but its envelope was ERROR: four rows marked successful, three failed, 21 retrieved items. The four includes the no-op REPOSITORY defect; three actual SDK endpoint branches succeeded. The selected rerun returned rc 0/SUCCESS with one item. The test catalog and all outputs were isolated in the dotfiles audit; no Downloads catalog, generated model, tracked result or PDF was changed. [D2]

## Authentication and native task grants

The observed task requested GITHUB_TOKEN. Native resolution warned that the configured age identity file was missing. SDK source reads an explicit token argument or GITHUB_TOKEN; this CLI supplied no explicit token. Child key presence was not separately inspected, and GH_TOKEN is not read by this client. Public REST success plus HTTP 401/403 does not prove successful secret injection. The failure concerns this launch route; it does not establish that the user lacks a credential or identity elsewhere. [D2, D7]

Do not repair this by extracting a token with gh or copying secret values into configuration. Dotfiles' saved-search spec already forbids token extraction. Keep values out of catalogs, snapshots, logs and review artifacts. A future auth owner must prove the approved provider lineage and the SDK's actual GITHUB_TOKEN export without exposing values. [F1]

| Task or consumer | Current/required variable | Admission and acceptance |
|---|---|---|
| Downloads `github-search` and `github:deep-search` | Native task currently requests GITHUB_TOKEN. | Declaration observed; current value resolution failed. Require catalog problems inspection, selected-child key-presence proof and successful authenticated SDK controls before acceptance. |
| Dedicated dotfiles GitHubKit rerun | SDK-facing variable must be explicit; existing gh transport accepts GH_TOKEN/GITHUB_TOKEN or CLI store. | Existing CLI-store behavior is not an SDK grant. Reuse an approved fnox provider through a verified SDK export mapping; keep credential-free record/status operations credential-free. |
| Possible publication-profile mapping | codex_publish exposes GH_TOKEN in existing profile metadata. | Candidate only. Mapping GH_TOKEN to SDK GITHUB_TOKEN is not proved or selected; verify profile/provider/child behavior before editing task grants. Do not automatically rewrite global fnox configuration. |
| Local schema, report and catalog validation | No GitHub request required. | No GitHub grant merely because these commands share a package with online search. |
| Mandated five-provider research | Existing exact native fnox codex_research launcher. | Preserve explicit config, no-defaults, no-daemon and non-interactive controls. Research provider keys do not substitute for a working GitHub credential. |
| Publication and nested provider bootstrap | Existing workflow-specific codex_publish preparation. | Preserve its deliberate bootstrap contract. Do not impose universal DOPPLER_TOKEN removal or grant bootstrap secrets to every SDK task. |

Native `[secrets.fnox]` configures a source profile; it does not accept an arbitrary config-file path. Task-local source-control environment is too late for source resolution. An explicit ordinary profile can avoid ambient profile selection, but it cannot repair an unusable credential or clean every inherited variable. Keep the exact research launcher where its config/discovery contract is required. Native prerequisites are mise 2026.10.4 and fnox 1.39.0 or newer in each actual project environment, not only globally. [M1]

## SDK types and cross-project compatibility

GitHubKit's REST `parsed_data` validates generated response models. Its GraphQL executor validates error envelopes but returns a dictionary payload; it does not provide a generated typed Discussion result for the application's selected query. Use the SDK's native REST models and missing-value semantics, then validate selected GraphQL nodes and local catalog/run/report envelopes through the project's existing schema-first pipeline. Do not hand-edit generated code or recreate the SDK's API models. [U1, U2, D4]

| Boundary | Preserve or change deliberately |
|---|---|
| Dependencies | Downloads pins GitHubKit 0.16.1; the observed installed schema package is `githubkit-schemas-2026-03-10` 26.9.29. Dotfiles currently lacks GitHubKit. Record the selected package/schema versions and actual runtime; add any dependency only in a separately authorized owner slice. [D1, F1] |
| Catalog formats | Keep dotfiles tracked TOML and Downloads JSON/Pydantic contracts. A common SDK does not require renaming or migrating both catalogs. Define an explicit semantic mapping for required kinds, effective query and options. [D5, F1] |
| Type names | Dotfiles code/issues/discussions/releases and Downloads CODE/TOPIC/REPOSITORY/ISSUE/PULL_REQUEST/DISCUSSION are not one enum. Add repository coverage without deleting existing project behavior; distinguish ISSUE from PULL_REQUEST in stored identity. [D3, F1] |
| Schema/code generation | Add local fields in source schemas, regenerate through supported tasks, and validate catalog/run compatibility. Codegen output is generated and ignored; no handwritten fixes there. [D5, D8] |
| Credential names | gh precedence and CLI-store discovery do not carry automatically into GitHubKit's GITHUB_TOKEN constructor. Validate the actual SDK child, not only a shell name or fnox catalog entry. [D7, F1] |
| Workspace ownership | Downloads review is document delivery only. Dotfiles #1774 keeps its sealed allowlist. KB native activation remains behind its separate runtime/source-provenance prerequisite. |

## Saved-query and rerun contract

Preserve the existing dotfiles contract: automatic recording of executed queries, stable watch identity, tracked TOML, protection of curated definitions, previous answered-run selection, staleness and NEW/GONE/count deltas. Do not present all of the following as already implemented; these are proposed additions or explicit acceptance requirements for the expanded SDK work. [F1]

1. Persist the declarative definition and the effective API request separately: search kind, complete query including issue/PR qualifiers, repository scope, filters, sort/order, API family, and actual page/time/item bounds. Validate options by endpoint; conflicting type qualifiers must be rejected or normalized explicitly.
2. Keep query identity separate from run identity. Every invocation gets a collision-resistant, immutable run directory/manifest. Query or tuning changes produce a versioned fingerprint; record schema/normalization and selected SDK/schema provenance. Current dotfiles second-resolution filenames and Downloads per-ID files do not establish immutable invocation history. [F1, D6]
3. Use SDK pagination primitives. GitHubKit REST pagination and GraphQL cursor/pageInfo support already exist; GraphQL pagination requires the cursor variable and does not support nested pagination. GitHub search returns at most 1,000 results, so a broad query can remain incomplete even after every accessible page is read. [U3]
4. Preserve stable typed item identity, repository provenance, returned count, API total/count semantics, incomplete_results/pageInfo, cap reason and structured auth/rate-limit/error state. A cap or failed page is not a zero-result search.
5. Compare only compatible, answered snapshots. Complete-set NEW/GONE claims require complete comparable coverage. Preserve existing top-window comparisons only when clearly labelled as changes in the observed ranked window; an item leaving that window is not proof it disappeared from the full result set. Suppress full-set GONE conclusions when a run fails, is capped, changes query semantics or has incomplete coverage. Retain the prior usable baseline. Updated-item detection is proposed additional behavior, not existing #1502 acceptance.
6. Generate the report from one run manifest. Include failures, incomplete coverage, actual SDK/schema versions and effective query. Unknown targets and unsupported types must return explicit errors instead of empty success.

Existing supported CLI shape, shown for owner review rather than authorization to execute:

```text
mise run github-search -- --catalog searches/searches.json --target <existing-id> --output-dir <new-relative-run-directory> --report-path <new-relative-report-path> --json
```

`--format json` is also supported. `github:deep-search` currently adds an ignored flag; it must not be documented as broader coverage until its semantics are implemented and verified. The audit used native mise read-only execution controls to prevent installs, sync, dependencies and code generation; exact recorded argv belongs to the audit receipt. [D2, D6]

## Proposed task and grant acceptance matrix

| Acceptance | Positive and negative/control evidence required | Current state |
|---|---|---|
| Real SDK transport | Trace the four required kinds to GitHubKit REST/GraphQL methods; unsupported kind fails explicitly. | Partial: repository enum branch missing. |
| Repository search | Known repository positive and impossible-query negative through REPOSITORY, not a mislabeled TOPIC workaround. | Positive TOPIC witness only; REPOSITORY false success demonstrated. |
| Issues and PRs | Distinct is:issue/is:pr results, SDK UNSET handled correctly, effective query and repository identity retained. | Public results returned; classification/query-provenance defects demonstrated. |
| Discussions | Authenticated query-matching positive on a known-enabled repository; distinguish disabled feature, no matches, capability failure and API failure. | Genuine GraphQL query exists; authenticated acceptance not obtained. |
| Credential lineage | Approved provider resolution and expected key presence without values; stale/unrelated inherited keys cannot satisfy the wrong consumer contract. | Requested key observed; age-resolution warning; child presence not independently proved. |
| Paging and bounds | More than one page, cap/incomplete response, rate limit and failed-page controls; declared completeness matches output. | Fixed first ten and discarded completeness. |
| Saved tuning and rerun | Save a definition, replay it, tune a copy, retain both effective requests and outputs. Unknown ID fails. | Selected replay succeeded; unknown target and deep semantics deficient. |
| Snapshots and deltas | Two immutable comparable runs, query-change control and partial-failure control; no overwrite or false GONE. | No Downloads native snapshot/diff; dotfiles contract offers existing safeguards to preserve. |
| Automation outcome | Process code, envelope and report agree with strict acceptance policy; partial public results cannot certify required authenticated success. | Observed rc0/ERROR and incomplete report. |
| Regression and hygiene | Existing code/topic behavior; schema-generated models; focused tests and project gates in the admitted owner context. | No repair, codegen or gates ran during this review. |

## Proposed implementation ownership and sequencing

Revised Q5 has approved the separate dotfiles GitHubKit/search migration and isolated-owner dispatch. Preserve #1774 and other STOPs; resolve approved credential lineage before declaring native grants ready. The KB prerequisite remains its own bounded plan/provenance milestone. Downloads receives this complete handoff for owner review and fixes, with ownership/preimage checks before application work. [R2]

Downloads application work requires its current owner's later ratification and a fresh source/dirty-state review. Candidate files are source schemas, `src/github_searcher/`, the existing catalog, native task grants, focused tests, supported skills and CLI documentation. Regenerate models through the existing pipeline. Do not copy active dirty source into another repository, invent a shared package without a concrete need, change global credentials automatically, or modify original PDFs.

## Complete actionable inventory

**Coverage: 50 stable finding dispositions: all 47 consumer/migration checklist IDs plus three primary-research/evidence items; 43 require owner review/fix or validation, and seven are preserve/no-change boundaries.** These are recommended priorities, not filed tickets. No acceptance test below was newly executed by this document pass. “Proven defect” identifies evidence-supported behavior, with Live versus Source stated per finding; a validation gap is not a claim that a previously unpromised feature was broken.

Priority: P1 blocks accepting the requested workflow; P2 is a required correctness, compatibility or validation item; P3 is a documentation/evidence correction. Owner labels name the responsible role for later admitted work, not permission to edit another owner's files.

Recommended order:

1. **O0 — ownership and preservation:** re-read current instructions, attest source/dirty state, assign the Downloads writer and isolate outputs; preserve the correct SDK/bootstrap/host boundaries.
2. **O1 — runtime and authentication:** establish actual project versions, select only an approved provider/profile/export route, and evaluate the whole task-grant matrix. Unit-level O2 work can proceed independently; real authenticated acceptance waits.
3. **O2 — request/response correctness:** dispatch, SDK absence semantics, effective queries, filters/sorting, selection, IDs, capability/error classification and focused regressions.
4. **O3 — coverage and durable reruns:** bounded native SDK pagination, explicit completeness, immutable runs/query revisions and comparable deltas.
5. **O4 — reporting, catalogs and documentation:** manifest-bound reports, truthful failures/version metadata, purposeful definitions, corrected native guide/skills and focused regression coverage.
6. **O5 — real acceptance and adoption:** authorized bounded authenticated controls, actual task grant evidence, selected reruns/tuned revisions/deltas, then applicable project gates and an owner adoption receipt for the final source.

Short source aliases used below: **D** = Downloads workspace; **C** = dotfiles `.agent/state/fnox-mise-session-audit-20261008/githubkit-consumer-review.md`; **F** = the sibling `migration-facts.md`; **M** = sibling `migration-guide-corrected-draft.md`; **E** = sibling `githubkit-consumer-review/execution-receipt.json`; **G** = Downloads `docs/FNOX_MISE_SECRETS_MIGRATION.md`. D2 means E plus its hash-bound outputs. All short Python filenames in those receipts refer to the named package; the inventory expands search-package paths where possible. [R3]

### Findings requiring review, correction or validation

#### DL-001 — Configured SDK credential route fails

**P1 · proven defect · O1 then O5; DL-002,029-034,040.**

**Evidence:** **Live** E.commands: native `GITHUB_TOKEN` resolution warned configured age identity missing. Code positive/absent controls returned HTTP401; discussion returned HTTP403 **rate limit exceeded**, not a proved permission-scope error. C:43-59; `src/github_searcher/client.py:16-19`. Child key presence was not inspected.

**Affected files/tasks:** `mise.toml:18,72-80`; `src/github_searcher/client.py`; auth-owner mapping.

**Required action:** Repair/choose the approved resolution route. Do not infer the user lacks credentials globally, treat public REST success as authenticated proof, or extract a token with `gh auth token`/`fnox get`.

**Acceptance/regression checks — proposed, not run by this pass:** Name-only grant/presence check plus bounded code and query-matching discussion positives; distinguish unauthorized, rate-limit and feature-disabled results. No token values in artifacts.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-002 — Whole-project profile and SDK export mapping remain unverified

**P1 · validation gap · O1; DL-001,029-034,040,042.**

**Evidence:** **Source + fact-lane metadata**, C:61-78: `codex_publish.GH_TOKEN` uses approved Doppler provider and `env=exec`; candidate task `env.GITHUB_TOKEN='{{ secrets.GH_TOKEN }}'` is supported natively but **not executed**. Source profile is project-wide; `mise.toml:108-134` contains other grants.

**Affected files/tasks:** Both GitHub tasks and `deps:intel`, `deps:research`, `deps:upgrade`, `deps:upgrade-all`; project `[secrets.fnox]`.

**Required action:** Review whole-project source/grant matrix before selecting profile. Candidate replaces the old `secrets=['GITHUB_TOKEN']` request; retaining it would still request the failed age source. Template itself grants GH_TOKEN and exports SDK name; no extra GH_TOKEN/DOPPLER_TOKEN SDK grant. Do not present this proposal as a validated fix.

**Acceptance/regression checks — proposed, not run by this pass:** Catalog shows every task's required keys; no unknown grants; clean SDK child has GITHUB_TOKEN, no unnecessary source-name export/bootstrap/unrelated values. Real SDK outcome after owner admission.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-003 — Zero process exit conceals failed searches

**P1 · proven defect · O2; DL-001,004,010.**

**Evidence:** **Live**, E first batch: process **rc0**, envelope `ERROR`, 7 rows/4 counted success/3 failed. One counted success is DL-004 no-op. `src/github_searcher/catalog.py:99-105`, `src/github_searcher/cli.py:77-79`.

**Affected files/tasks:** Catalog batch/CLI exit policy and consuming automation.

**Required action:** Specify and implement trustworthy partial-error/strict acceptance behavior. Public unauthenticated mode may be intentional; it must not silently satisfy authenticated acceptance.

**Acceptance/regression checks — proposed, not run by this pass:** All-success, all-fail, mixed, feature-disabled and no-op controls; assert both exit code and envelope/row status.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-004 — REPOSITORY falls through to false empty success

**P1 · proven defect · O2; DL-025,027.**

**Evidence:** **Live + source**: identical `repo:jdx/mise` REPOSITORY query reports empty success in 4 microseconds; TOPIC SDK query returns expected repo. `src/github_searcher/search.py:272-320,325-337`; `schemas/enums.json:75-85`; E `run1/repository-dispatch-negative.json` and positive.

**Affected files/tasks:** `src/github_searcher/search.py`, enums/schema, repository catalog examples.

**Required action:** Dispatch REPOSITORY to SDK repository search; fail unsupported types instead of success fallthrough. Preserve TOPIC semantics.

**Acceptance/regression checks — proposed, not run by this pass:** Assert SDK endpoint called, query preserved, known repo positive and impossible repo negative; unknown type fails before network.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-005 — SDK UNSET misclassifies issues as PRs

**P1 · proven defect · O2 before history/report acceptance.**

**Evidence:** **Live + source**: ten `/issues/` links become `is_pr=true`. `src/github_searcher/search.py:171`; installed SDK `githubkit_schemas/v2026_03_10/models/group_0540.py:71` defaults pull_request to UNSET, not None. `run1/issues-native-secrets.json`.

**Affected files/tasks:** Issue/PR normalization, report labels, future diffs.

**Required action:** Use SDK missing-value semantics; distinguish absent, nullable and present fields.

**Acceptance/regression checks — proposed, not run by this pass:** Representative actual SDK issue/PR models, UNSET/None/present checks; correct `is_pr` and report label.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-006 — Persisted query omits effective issue/PR qualifier

**P2 · proven defect · O2 before DL-017/018.**

**Evidence:** **Source + live serialized output**: `src/github_searcher/search.py:125` adds `is:issue`/`is:pr`; `query_executed` stores earlier `full_query` at :259,328.

**Affected files/tasks:** Search result schema/provenance, report, future snapshot keys.

**Required action:** Persist exact effective endpoint query, family and declared query separately; decide behavior for conflicting type qualifiers. GitHubKit documents a GitHub App user-token restriction for mixed issue/PR searches; use separate typed issue/PR requests where required while preserving explicitly supported existing mixed-query meaning. [U4]

**Acceptance/regression checks — proposed, not run by this pass:** Compare captured SDK q with persisted executed query for issue and PR; conflicting qualifiers rejected or normalized explicitly.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-007 — Per-kind query qualifiers and conflicts need validation

**P2 · validation gap · O2; informs DL-006,008,025.**

**Evidence:** **Source**, `src/github_searcher/search.py:29-46`, schema `github_search.json:32-80`: one qualifier builder appends language/filename/topic/stars to all kinds, repeated values and inline repo qualifiers without kind-specific validation. No API rejection/control was run for those combinations.

**Affected files/tasks:** SearchDefinition schema, query builder, catalog tuning.

**Required action:** Review per-endpoint valid qualifiers and intended AND/OR semantics; validate conflicts and prevent silent different query meaning. Do not claim every current multi-filter query is invalid.

**Acceptance/regression checks — proposed, not run by this pass:** Per-kind allowed/rejected qualifier fixtures, multiple languages/topics, inline versus target_repo conflict, empty query and malformed target. Official API-supported behavior or explicit rejection.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-008 — Unsupported sorting is silently dropped

**P2 · proven defect · O2 after API contract review DL-007.**

**Evidence:** **Source**, free-string sort/order schema :71-80; src/github_searcher/search.py:56-58,88-92,126-143 silently drops unrecognized values; issue type annotation lists more sorts than actual allowed tuple; discussion ignores sort/order entirely (:207-214).

**Affected files/tasks:** Query schemas, each executor and CLI/docs.

**Required action:** Validate per-kind sorts/orders or explicitly document supported translation; reject unsupported tuning instead of ignoring it.

**Acceptance/regression checks — proposed, not run by this pass:** Valid sort reaches SDK; misspelling/unsupported kind fails validation; discussion ordering either encoded using supported query syntax or explicitly unsupported.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-009 — Deep selector has no effect

**P2 · proven defect · O2; DL-025/027/028.**

**Evidence:** **Source**, `src/github_searcher/catalog.py:44` discards deep_only; `src/github_searcher/cli.py:45-48,64-69`, `mise.toml:77-80` advertise `--deep`. Ordinary run already executes every saved type.

**Affected files/tasks:** CLI, catalog, `github:deep-search`, skill/docs.

**Required action:** Define and implement selector semantics or remove misleading distinction through agreed compatibility change.

**Acceptance/regression checks — proposed, not run by this pass:** With identical catalog, standard/deep selection matches documented behavior; explicit target selection interaction tested.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-010 — Unknown target reports empty success

**P2 · proven defect · O2; DL-003.**

**Evidence:** **Source**, `src/github_searcher/catalog.py:67-72,99-105`: unknown `--target` selects zero rows and succeeds. Not replayed live.

**Affected files/tasks:** Catalog/CLI target validation.

**Required action:** Reject missing target clearly before client/network/output work; distinguish intentionally empty catalog policy.

**Acceptance/regression checks — proposed, not run by this pass:** Unknown target nonzero/structured error, no SDK calls or result files; valid target executes exactly once.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-011 — Duplicate catalog IDs can overwrite results

**P2 · proven defect · O2 before O3.**

**Evidence:** **Source**, schema ID string :27-30, search list :93-99; no uniqueness validation before `src/github_searcher/catalog.py:78-92` writes by ID. Duplicate IDs overwrite each other. No duplicate catalog was executed.

**Affected files/tasks:** Catalog validation/schema, result naming.

**Required action:** Require unique stable IDs; retain revision identity separately.

**Acceptance/regression checks — proposed, not run by this pass:** Duplicate ID rejected before API/output writes; tuning copied query has distinct or explicitly versioned identity.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-012 — Catalog IDs lack path containment

**P1 · proven defect · O2 before any broader catalog ingestion.**

**Evidence:** **Source**, unrestricted ID string and `output_dir / f'{definition.id}.json'` at src/github_searcher/catalog.py:88-92 permit path separators/absolute IDs to escape intended result naming. No traversal was executed; no exploitation claim.

**Affected files/tasks:** Catalog/schema and output path boundary.

**Required action:** Validate path-safe IDs and enforce resolved output containment; never use query text as filesystem path.

**Acceptance/regression checks — proposed, not run by this pass:** Absolute, `../`, separator and platform-path cases rejected using tmp_path; accepted IDs remain inside isolated output root.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-013 — First-page collection does not satisfy bounded multi-page coverage

**P1 · validation gap · O3 after DL-004/005/006.**

**Evidence:** **Source + live counts**, fixed page size10 `src/github_searcher/search.py:26,65,99,150`; GraphQL first10 at :179-214 without cursor. Live issue10/13 and PR10/207.

**Affected files/tasks:** Schema pagination/budgets; REST/GraphQL executors.

**Required action:** Add bounded supported SDK pagination with explicit page/item/time budgets; define cap behavior. This is an accepted-Q5 capability gap, not evidence that first-page preview was previously prohibited. Prefer the SDK REST Link-header and GraphQL cursor/pageInfo paginators; GraphQL uses a cursor variable, first/last1–100, no nested pagination, and the1000-search-result ceiling. [U4]

**Acceptance/regression checks — proposed, not run by this pass:** >1-page fixtures/live bounded witness; final page, cap, timeout/rate-limit halfway, repeated cursor; no infinite loop or false full coverage.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-014 — Completeness and truncation metadata are absent

**P1 · validation gap · O3 with DL-013 before DL-018.**

**Evidence:** **Source**, executor normalizes only total_count/items; schema `SearchExecutionResult:191-251` has no completeness, pageInfo, REST incomplete_results or truncation reason.

**Affected files/tasks:** Result schema, normalizers, reports/diffs.

**Required action:** Persist enough coverage/status metadata to distinguish empty, partial, API-incomplete and fully exhausted results.

**Acceptance/regression checks — proposed, not run by this pass:** Deliberately incomplete REST and partial GraphQL responses stay incomplete; count alone is not completeness.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-015 — Error classes and bounded retry policy need explicit treatment

**P2 · validation gap · O2/O3; DL-001/003/014.**

**Evidence:** **Source + live errors**, `src/github_searcher/client.py:18-19` auto_retry=False; `src/github_searcher/search.py:340-355` collapses SDK exceptions to GITHUB_API_ERROR and string. No native query dry-run/preflight exists; only mise task dry-run was used.

**Affected files/tasks:** Client, error schema/CLI and execution budgets.

**Required action:** Preserve no unbounded retry. Review explicit bounded retry/backoff/rate metadata and auth/error classifications; add query-plan preview only if needed by ratified workflow. Do not call disabled auto-retry itself a bug. The SDK has native retry support, while the current client intentionally sets auto_retry=False. Reuse SDK controls if a bounded retry policy is adopted; do not replace them with an unbounded custom loop. [U4]

**Acceptance/regression checks — proposed, not run by this pass:** 401,403 rate-limit,429,network/transient and exhaustion fixtures; no secret headers, bounded waits; dry-run if introduced cannot call API or overwrite outputs.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-016 — Saved reruns lack immutable run identity

**P1 · validation gap · O3 after DL-011/012.**

**Evidence:** **Source**, `src/github_searcher/catalog.py:88-92` overwrites `<id>.json` on same-directory reruns. Actual run2 used a distinct directory, so no historical data was destroyed in this audit.

**Affected files/tasks:** Catalog persistence/run layout and defaults.

**Required action:** Implement immutable/non-overwriting run identity and intentional replacement policy meeting Q5; preserve historical user results.

**Acceptance/regression checks — proposed, not run by this pass:** Two reruns retain both artifacts and run manifests; repeat ID/collision handling explicit; test isolation outside tracked outputs.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-017 — Query/catalog revision and runtime provenance are missing

**P2 · validation gap · O3 after DL-006/008/016.**

**Evidence:** **Source**, schema/catalog have no saved-definition fingerprint, catalog hash, revision identity or transport/version run provenance.

**Affected files/tasks:** Schema, run manifest, catalog editing and snapshots.

**Required action:** Fingerprint actual normalized query/filters/endpoint/options/catalog and SDK/tool provenance; distinguish tuned query from same-query rerun.

**Acceptance/regression checks — proposed, not run by this pass:** Same input gives same query fingerprint; tuning type/query/filters changes it; secrets excluded; portable relative artifact references.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-018 — Safe native snapshot comparisons are missing

**P1 · validation gap · O3 after DL-013/014/016/017.**

**Evidence:** **Source**, Downloads CLI exposes search/report only; no snapshot diff. Dotfiles comparator `saved_searches.py:960-1011` suppresses false NEW/GONE for failed or incomparable/full-window transitions.

**Affected files/tasks:** Future diff schema/CLI/report and docs.

**Required action:** Add trustworthy deltas using stable item identity only between comparable runs; preserve dotfiles contract, not a shell-token extraction transport.

**Acceptance/regression checks — proposed, not run by this pass:** Complete→complete comparable runs may report full-set additions/removals. Failed, partial, capped, window→full or query-revision-changed observations cannot support full-set GONE/NEW claims; preserve prior per-query history selection. Supported comparable top-to-top observations may still report explicitly labelled ranked-window changes with ranking caveats; an item leaving the window is not proof it disappeared from the full result set. Universal complete-set-only comparison would be a stricter new policy. [F1, U4]

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-019 — Discussion results omit repository identity

**P2 · proven defect · O2/O3 before O5.**

**Evidence:** **Source**, GraphQL selection lacks repository; mapper stores `repo_name=''` at `src/github_searcher/search.py:179-203,237`. Successful live discussion result remains unproved.

**Affected files/tasks:** Discussion query/schema/mapping.

**Required action:** Select and preserve repository identity, alongside node identity/url and scope.

**Acceptance/regression checks — proposed, not run by this pass:** Cross-repository discussion results retain distinct correct repository; nullable author/category handled; page metadata retained.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-020 — Capability failure, disabled feature and not-probed states blur

**P2 · validation gap · O2, DL-001/019.**

**Evidence:** **Source**, `src/github_searcher/capabilities.py:33-34` swallows GitHubException to None; `src/github_searcher/search.py:261-264,282-320` only probes target_repo, not inline repo:.

**Affected files/tasks:** Capability result schema/error policy, search orchestration.

**Required action:** Distinguish unsupported feature, unavailable capability/auth/rate failure and not-probed. Decide whether inline repo scope must be normalized for probing; do not require repo probing for unscoped global searches.

**Acceptance/regression checks — proposed, not run by this pass:** Known disabled discussions, known enabled positive, failed probe and intentionally unprobed case yield distinguishable states; PR search not blocked by disabled issues flag.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-021 — Reports can include stale or unrelated results

**P2 · proven defect · O4 after DL-016/017.**

**Evidence:** **Source**, `src/github_searcher/report.py:26-35` aggregates every JSON file in output directory. Old or unrelated results can enter a new report; not reproduced by mixing files.

**Affected files/tasks:** Report reader, run manifest, report CLI.

**Required action:** Bind report to one declared run or explicit selected history, not an uncontrolled directory glob.

**Acceptance/regression checks — proposed, not run by this pass:** Stale/foreign JSON excluded or rejected explicitly; missing expected result fails visibly; reporting a historical run remains supported.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-022 — CLI version is mislabeled as SDK version

**P3 · proven defect · O4.**

**Evidence:** **Live generated report + source**, `src/github_searcher/report.py:47` labels CLI_VERSION as GitHubKit version; `lab_results_core/system.py:13` is0.2.0, installed SDK0.16.1.

**Affected files/tasks:** Report metadata/version display.

**Required action:** Report actual SDK distribution version and separate CLI version; avoid hardcoded duplicated dependency numbers.

**Acceptance/regression checks — proposed, not run by this pass:** Fixture distinguishes CLI0.2.0 and SDK0.16.1; generated report agrees with runtime metadata.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-023 — Reports hide failed searches as zero matches

**P1 · proven defect · O4 after DL-003/014/015.**

**Evidence:** **Live report + source**, src/github_searcher/report.py:59-97 omits error_code/error_message/partial-state summary; failed searches appear as matches0.

**Affected files/tasks:** Markdown report/error summary.

**Required action:** Show failed, unavailable, disabled and incomplete results clearly, with safe diagnostic classification and coverage.

**Acceptance/regression checks — proposed, not run by this pass:** Mixed ERROR batch report highlights failures; zero verified result distinguishable; no access token/request secret dumped.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-024 — Report-generation failure policy is unclear

**P2 · validation gap · O4 after DL-003/021.**

**Evidence:** **Source**, `src/github_searcher/cli.py:71-79` report failure only warns; response exit stays original and text later says report generated (:109-115). Contract may permit search-only success, so policy needs review.

**Affected files/tasks:** CLI report generation status/envelope.

**Required action:** Specify whether report is required; represent its outcome/path honestly and align exit behavior without losing successful search artifacts.

**Acceptance/regression checks — proposed, not run by this pass:** Report OSError/invalid/missing input: truthful structured outcome and text; policy-specific exit; raw results retained. Do not emit text claiming a report was generated when its write failed; retain successful raw search artifacts for recovery.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-025 — Required repository and PR catalog examples are missing

**P2 · validation gap · O4 after DL-004/007-014.**

**Evidence:** **Source**, `searches/searches.json` has17 code/topic/issue/discussion entries but no PULL_REQUEST or REPOSITORY entry. Existing saved/tunable queries are already supported.

**Affected files/tasks:** Saved catalog and examples/skills.

**Required action:** Add purposeful bounded repository/PR examples and full required-kind acceptance queries; preserve existing queries, descriptions and tuning history.

**Acceptance/regression checks — proposed, not run by this pass:** Validate every catalog entry; known positive/absent and disabled-feature controls; examples actually dispatch requested kinds.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-026 — Authenticated positive and absent controls remain incomplete

**P1 · validation gap · O5 after O1-O4.**

**Evidence:** **Source + live failed controls**, E run1 code-positive and nonce-negative both401, discussion403. No complete authenticated code/discussion success or verified absent control was obtained. Repository TOPIC rerun and public issue/PR success are real but limited.

**Affected files/tasks:** Acceptance receipt and final completion claims.

**Required action:** Finish meaningful controls only after authorized route resolution; do not call an auth/rate failure empty. Preserve exact failed receipt.

**Acceptance/regression checks — proposed, not run by this pass:** Repository positive/negative; code positive/fresh-absent; distinct correct issue/PR; known-enabled query-matching discussion positive and separate disabled control; saved rerun/tuned revision/delta.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-027 — Tests do not cover the actual standalone contract and found defects

**P2 · validation gap · O2-O4; all defects.**

**Evidence:** **Source**, `tests/test_github_search.py:57-92,133-189,238-288` primarily tests builders and mocked code; CLI test imports legacy lab updater app, not standalone github_searcher app.

**Affected files/tasks:** Focused tests for actual standalone task entrypoint plus compatible legacy alias.

**Required action:** Cover every confirmed defect and accepted capability; use meaningful fake SDK boundaries and exact generated optional types; test actual entrypoint. No test/gate ran in this audit.

**Acceptance/regression checks — proposed, not run by this pass:** Per-finding regressions above, standalone CLI JSON/exit/errors, legacy alias compatibility if retained, tmp_path outputs and no provider calls in unit tests.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-028 — Scoped instructions, skills and canonical command prose drifted

**P3 · doc correction · O4 after agreed source behavior.**

**Evidence:** **Source**, `src/github_searcher/AGENTS.md:10-16` names check_repo_capabilities/execute_issue_search, repository-list discussion query and1s delay; actual symbols detect_repo_capabilities/execute_issue_pr_search, GraphQL search, 2.5s code/0.5s other (`src/github_searcher/catalog.py:93-94`). G:66 shows legacy lab updater command; current task uses standalone github-search, though legacy alias still exists (`lab_results_updater/cli.py:501`).

**Affected files/tasks:** Scoped AGENTS, root/catalog capability prose, skills/plugin copies, CLI and migration docs.

**Required action:** Align names/signatures/behavior and current canonical command; do not wrongly claim legacy alias absent. Expand docs to accepted repository/issues/PRs/discussions, saved/tuned/rerun/delta semantics.

**Acceptance/regression checks — proposed, not run by this pass:** Documentation references match source/CLI contract and schema; no docs imply `--deep`, pagination or auth acceptance before implemented.

**Owner:** Downloads documentation/skill owner; global configuration owner verifies host-specific claims.

#### DL-029 — Profile/default selection can break other grants

**P1 · validation gap · O1; DL-002/033/042.**

**Evidence:** **Live metadata + source**, F:9,12,30,50; M:93-108. Research profile alone59 keys; no-defaults6 declarations/5 injectable. Project research-only selection produces five unknown GitHub-task grants even with catalog rc0.

**Affected files/tasks:** Project source/profile, all grants, migration docs.

**Required action:** Review profile/defaults together; keys catalogued are not actual child env. Avoid globally selecting research-only profile as a universal fix.

**Acceptance/regression checks — proposed, not run by this pass:** Exact source metadata and problems[] inspected; all consuming tasks resolve named keys; no unexpected defaults leak to clean child.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-030 — Native discovery is not an exact global-file pin

**P2 · doc correction · O1; DL-040.**

**Evidence:** **Live discovery + source**, G:56 implies fixed global file; F:10,16,18,49 and M:87-91,120-125: native discovery can combine project/parents; `[secrets.fnox]` only accepts profile, no exact config-file pin. FNOX_CONFIG_DIR is not equivalence.

**Affected files/tasks:** Migration guide, launcher/source design.

**Required action:** Correct fixed-file claim; retain exact `fnox --config ...` wrapper where pinned provenance is required. No custom loader needed.

**Acceptance/regression checks — proposed, not run by this pass:** Evidence distinguishes current discovered files from invariant; future discovery tests with controlled project/parent configs; pinned wrapper retained for required workflows.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-031 — Task-local environment cannot configure the native source

**P2 · doc correction · O1 with DL-029/030.**

**Evidence:** **Source**, F:9,67; M:103-109: source constructed from process/project/tool environment, excluding task env. Supported FNOX_NO_DEFAULTS, NON_INTERACTIVE and DAEMON controls do not supply exact-config pin.

**Affected files/tasks:** Source-control examples, project env/launcher tasks.

**Required action:** Place source controls at an effective reviewed scope; do not propose task-local FNOX_PROFILE/no-defaults as source isolation. Distinguish key-export templates from source-control env.

**Acceptance/regression checks — proposed, not run by this pass:** Native source metadata reflects intended process/project settings; task-local setting cannot be treated as proof; real daemon/noninteractive resolution still validated later.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-032 — Named grants do not guarantee universally clean environments

**P2 · doc correction · O1/O5; DL-002/040.**

**Evidence:** **Source/live help**, F:33,53; M:26-31: named task grants exclude dependencies/subtasks; ordinary children and mise x inherit; nested mise run scrubs marked grants; arbitrary inherited env is separate. G:5,87 overstate universal least privilege.

**Affected files/tasks:** Migration guide, nested task/SDK launch and acceptance environment.

**Required action:** Correct blanket clean-environment claim; map exact nested consumers and grant boundaries. Don't infer all inherited values scrubbed.

**Acceptance/regression checks — proposed, not run by this pass:** Parent task, ordinary subprocess, dependency, nested run and x cases with names-only sentinels/approved grant presence; unrelated ambient keys remain an explicit control.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-033 — The documented all-secret CLI syntax is invalid

**P3 · doc correction · O4; prerequisite for examples DL-002.**

**Evidence:** **Live deliberate invalid replay**, G:109-110 bare `--secrets --`; F:12,33,51; M:143-147: rc2, no child.

**Affected files/tasks:** Migration examples/skills.

**Required action:** Named `--secrets KEY[,KEY...]`; broad syntax is --secrets-all, but do not substitute broad exposure for a narrow consumer. Default has59 injectable keys, including bootstrap. mise x lacks same task-output redaction.

**Acceptance/regression checks — proposed, not run by this pass:** CLI syntax example valid; no broad grant introduced; outputs remain secret-safe. Existing invalid replay is sufficient proof; no need to repeat credentials.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-034 — Project runtime compatibility needs a reproducible admission contract

**P1 · prerequisite · O1 before native implementation/adoption.**

**Evidence:** **Version probes/source**, F:21,44; M:15-24. Native baseline mise2026.10.4, fnox>=1.39.0; experimental already enabled globally. D mise.toml tools omit fnox/minimum mise, relying on host. Installed GithubKit0.16.1 already confirmed.

**Affected files/tasks:** Project tool ownership/min_version/lock policy and guide.

**Required action:** Establish reproducible selected runtime/floor per project without forced exact latest or unrelated tool upgrades. Re-attest selected executable before implementation. Don't duplicate already-enabled experimental gratuitously.

**Acceptance/regression checks — proposed, not run by this pass:** Correct project resolution/version metadata, declared compatible floor/pin or explicitly approved host ownership; schema/catalog supports actual version. KB1.34.1 is a separate cross-project prerequisite, not a Downloads bug.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-035 — Ignored auto_update cleanup is not global update-policy authority

**P3 · doc correction · O4/no forced config change.**

**Evidence:** **Source and current observation**, G:57-58, F:52, M:151-154: project auto_update ignored/global-only, canonical self_update.auto; project removal observed but pre-change project backup unavailable.

**Affected files/tasks:** Guide/settings narrative only unless stale config remains.

**Required action:** Describe cleanup accurately; do not attribute historical removal without evidence or change global update preference automatically.

**Acceptance/regression checks — proposed, not run by this pass:** Current project has no ignored setting; docs use canonical global-only semantics and attribution uncertainty. No user policy change required.

**Owner:** Downloads documentation/skill owner; global configuration owner verifies host-specific claims.

#### DL-036 — Backup identity does not prove a fnox content migration

**P2 · doc correction · O0/O4.**

**Evidence:** **Byte/structure probe**, F:32,46 and M:39-48: global fnox backup and active identical; named backup size36934. G:13-18 treats backups as authoritative pre-migration timing.

**Affected files/tasks:** Backup/change narrative and rollback planning.

**Required action:** Record actual equality and timestamp-label evidence; no invented fnox content migration or assured chronology. Preserve backup; don't restore identical secret file pointlessly.

**Acceptance/regression checks — proposed, not run by this pass:** Value-free identity/structural evidence retained; backup provenance clear; no secret contents printed.

**Owner:** Downloads documentation/skill owner; global configuration owner verifies host-specific claims.

#### DL-037 — Whole-file rollback would risk unrelated global tool changes

**P1 · validation gap · O0 before any rollback decision.**

**Evidence:** **Structural probe**, F:32,47; M:45-48: global mise differs by plugin declaration and node/inspector/pandoc/pitchfork versions. Attribution/timing unknown.

**Affected files/tasks:** Global-change audit and rollback instructions; not blanket permission to edit global config.

**Required action:** Any rollback must be field-scoped to owned approved changes and compare current state, preserving other owners' unrelated tool edits; no whole-file restore from old backup. Establish attribution before claiming sole migration change.

**Acceptance/regression checks — proposed, not run by this pass:** Review exact metadata diff and ownership; rollback simulation/plan preserves unrelated values; explicit owner authority before execution. No rollback was attempted.

**Owner:** Global configuration owner for any separate policy/rollback decision; Downloads documentation owner records the boundary.

#### DL-038 — Declaration removal is not plugin uninstall or consumer migration

**P2 · doc correction · O0/O4; preserve other sessions.**

**Evidence:** **Live plugin inventory + backup source**, F:13,17,45; M:50-53: global env._.fnox-env absent both before/after, legacy plugin still installed. G:5,42-45 overstate demonstrated removal of global loading.

**Affected files/tasks:** Migration guide and any proposed legacy plugin cleanup.

**Required action:** Distinguish declaration removal, plugin uninstall, and actual secret-consumer transition. Inventory ambient activation/other consumers before cleanup; do not uninstall automatically.

**Acceptance/regression checks — proposed, not run by this pass:** Concrete consumer evidence, no legacy active directive missed; scoped plugin removal only after separate owner authorization if needed.

**Owner:** Downloads documentation/skill owner; global configuration owner verifies host-specific claims.

#### DL-041 — Research failure/fallback evidence must remain explicit

**P2 · validation gap · O4/O5 reporting; no new provider calls needed here.**

**Evidence:** **Existing research receipts**, F:28,34,83-84; M:181-185: Firecrawl search402 credits exhausted with accepted Serper fallback; native five-provider coverage provisional. Consumer code/discussion failures separate. GithubKit research lane also records disabled discussions on upstream SDK repo. Current required SDK-research receipt R1 is actual rc1/INCOMPLETE: discussion canary0/empty_unverified, and yanyongyu/githubkit has discussions disabled; this is distinct from the earlier fnox audit's rc0/provisional receipt.

**Affected files/tasks:** Research evidence ledger, completion language and handoff.

**Required action:** Preserve provider identities/failed routes/primary verification; no claim all native providers or all SDK types passed. Do not reopen exhausted-credit billing or turn disabled feature into positive search coverage.

**Acceptance/regression checks — proposed, not run by this pass:** Final report lists Exa, Firecrawl/fallback, Last30Days, Context7, GitHub routes actually run, source receipt status and failed routes; authentic SDK acceptance tracked separately DL-026. Preserve the original failed receipt/hash, expose the402→Serper provider substitution as PROVISIONAL, and use known-enabled jdx/mise for a future authorized positive discussion control rather than treating disabled upstream discussions as a positive.

**Owner:** Research receipt owner and Downloads documentation owner.

#### DL-042 — Catalog/doctor status is not real consumer acceptance

**P1 · validation gap · O1/O5; DL-003/029.**

**Evidence:** **Live metadata**, F:9; M:103-108,156-162: secret catalog rc0 can contain five problems; guide G:113-131 suggests catalog/doctor checks but neither proves consumer success.

**Affected files/tasks:** Validation scripts/docs, catalog/doctor result evaluation.

**Required action:** Inspect structured problems/warnings plus rc and actual consumers; don't equate catalog count or doctor success with auth/SSH/Git/research/SDK success.

**Acceptance/regression checks — proposed, not run by this pass:** Deliberate unknown grant reported as non-accepted even when command rc0; separate successful bounded consumer outcomes; name-only presence not a substitute.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-047 — The portable guide must not embed host-specific paths

**P3 · doc correction · O4; DL-028/036/037.**

**Evidence:** **Source**, G:17-18,50,58 includes host-absolute backup paths and file-URI project links; D AGENTS relative-path invariant requires portable project metadata. Exact backup locations are useful audit evidence but should not be presented as portable commands.

**Affected files/tasks:** Downstream migration/review docs and any future run manifests.

**Required action:** Use project-relative source/artifact links in the portable handoff; identify host-specific backup evidence separately, with no executable assumption that another host has those paths. Fix noncanonical file-URI links using the publication surface's supported links. Do not erase exact historical audit provenance.

**Acceptance/regression checks — proposed, not run by this pass:** Portable document contains relative project/artifact references, no machine-specific executable placeholders; backup evidence remains verifiable in the local audit; copied instructions match target host.

**Owner:** Downloads documentation/skill owner; global configuration owner verifies host-specific claims.

#### SYN-001 — GraphQL payload typing needs its own local-schema boundary

**P2 · validation gap · O2/O3 before O5; DL-005,013,014,019,027,044**

**Evidence:** U1/U2/U4 verify REST parsed_data uses generated validated models, whereas the GraphQL executor returns dict[str, Any] after error-envelope validation. Downloads selected Discussion nodes are mapped in src/github_searcher/search.py:179–250; SDK typing alone is not proof that those selected nodes were validated.

**Affected files/tasks:** schemas/github_search.json; src/github_searcher/search.py; focused GraphQL mapper tests; generated models via codegen only

**Required action:** Reuse SDK REST response types and validate the application's selected GraphQL node shape through the existing schema-first pipeline. Check current normalization rather than assuming every dictionary is unsafe; do not duplicate all SDK API models or treat a TypedDict annotation as runtime validation.

**Acceptance/regression checks — proposed, not run by this pass:** Malformed/null/missing node fields, nullable authors/categories and incorrect repository shape produce a typed, classified outcome. Valid query results preserve id, number, URL, repository and pagination metadata. No manual codegen edits.

**Owner:** Downloads GitHub search/schema maintainer.

#### SYN-002 — Do not repeat stale claims about GitHub saved queries or API absence

**P3 · doc correction · O4; DL-017,018,028,044**

**Evidence:** U4 official GitHub saved-query docs support creating/naming/editing/deleting queries in the search UI. No saved-query persistence endpoint was identified only in the inspected SDK/REST search surface; this is a scoped negative finding.

**Affected files/tasks:** Architecture/migration rationale, search skills and catalog/rerun documentation

**Required action:** Correct any carried-forward issue-only or universal no-saved-search/API claim. Explain the actual project need: automatic executed-query recording, typed provenance, controls, immutable history and comparisons. Preserve existing catalogs for those requirements instead of inventing a new SDK/library or assuming UI saving replaces the workflow.

**Acceptance/regression checks — proposed, not run by this pass:** Docs distinguish GitHub UI capability, the inspected API surface and project-specific persistence/verification needs. Source citations support each claim and no universal absence statement exceeds the evidence.

**Owner:** Downloads documentation/architecture owner, with dotfiles migration compatibility review.

### Preserve/no-change boundaries

These seven items are not open application defects. Preserve them while fixing adjacent behavior, or obtain the explicitly separate policy/source admission described by the item. Do not invent work to turn a preservation receipt green.

#### DL-039 — Global trust policy is a separate review

**P2 · preserve-no-change · O0/O1; no mandatory change.**

**Evidence:** **Metadata/source**, F:14,69: trusted_config_paths contains '/', paranoid unset; task run can trust configs implicitly outside CI/paranoid.

**Affected files/tasks:** Trust-policy narrative, global settings.

**Required action:** Record that native grants are not an independent user-approval boundary here. Trust tightening is review-only and separate user policy; no automatic global change in this migration.

**Acceptance/regression checks — proposed, not run by this pass:** Docs accurate; if separately authorized, map blast radius/session implications and test that policy independently.

**Owner:** Global configuration owner for any separate policy/rollback decision; Downloads documentation owner records the boundary.

#### DL-040 — Distinct research and publication bootstrap contracts must survive

**P1 · preserve-no-change · O0/O1/O5; DL-001/002/029-032.**

**Evidence:** **Live research wrapper + source**, F:19,54,66; M:111-133. Research exact wrapper works; default/research/publish have different bootstrap contracts. SDK candidate must not receive publish DOPPLER_TOKEN merely because publish consumer legitimately does.

**Affected files/tasks:** Research/bootstrap launchers and SDK grants, Doppler/SSH environment preparation.

**Required action:** Preserve exact research wrapper/config/no-defaults/no-daemon/noninteractive where required; preserve approved publish nested bootstrap. Do not impose universal bootstrap exclusion across all workflows or broad exports to SDK.

**Acceptance/regression checks — proposed, not run by this pass:** Per-profile key contract and each actual consumer independently checked; bootstrap remains internal to research, necessary publish export retained, SDK child minimal. Preserve SSH_AUTH_SOCK where needed, not as a fnox grant.

**Owner:** Existing research/publication launcher owners; Downloads configuration owner preserves the SDK boundary.

#### DL-043 — Existing project source placement is already correct

**P2 · preserve-no-change · O0/O1, no relocation needed.**

**Evidence:** **Current source**, D mise.toml:18 and F:18,48,62; M:21-24: project source scope already correct; global native sources ignored.

**Affected files/tasks:** `[secrets.fnox]`, global config, guide instructions.

**Required action:** Keep source project-scoped and grants task-specific; don't add native source/global task grants to user config. No defect in existing placement; profile/export route is separately DL-001/002.

**Acceptance/regression checks — proposed, not run by this pass:** Source placement and eligible config verified; no unrelated global settings diff.

**Owner:** Downloads configuration/auth owner; coordinate cross-project provider changes with the approved dotfiles migration owner.

#### DL-044 — Reuse the real SDK and schema-first project pipeline

**P2 · preserve-no-change · O0/O2/O4.**

**Evidence:** **Live SDK and source**, pyproject.toml:27,42-44,138-152; mise.toml:29-39; schemas/codegen exist. Actual SDK REST/GraphQL calls already run; SDK GraphQL is query-matching search.

**Affected files/tasks:** SDK dependency, schema-first models, CLI pipeline.

**Required action:** Reuse installed pinned GitHubKit and project schema generation, not custom HTTP/token loader or a new competing script. Preserve query-matching discussions; correct misleading listing prose DL-028. Never hand-edit codegen. Q5 approved a separate dotfiles migration owner to evaluate/reuse a common GitHubKit adapter across saved reruns and research_fanout's producer/automatic-recording seam, preserving exact fnox/strict-five/curated-recording contracts. That is external dependency work, not permission to copy dirty Downloads source, create a competing persistence engine or claim existing gh calls are SDK calls. [F1, R2]

**Acceptance/regression checks — proposed, not run by this pass:** Meaningful model/SDK compatibility checks through native project tasks after admitted edits; deterministic codegen; actual SDK requests not only mocks.

**Owner:** Downloads GitHub search maintainer/current project owner.

#### DL-045 — Preserve bounded native execution and output isolation

**P2 · preserve-no-change · O0 for every future probe.**

**Evidence:** **Live safe execution**, E.commands and C:37-45: explicit external output/report dir; no-deps/skip-deps/skip-tools/task-cache-off, UV_NO_SYNC, no Python downloads, no bytecode; task dry-run no secret resolution. Source auto deps would otherwise prepare uv/codegen.

**Affected files/tasks:** Future probe commands, tests and output paths.

**Required action:** Keep bounded isolated native task execution; no Downloads one-off scripts or tracked `searches/results`, PDFs, offline/templates/generated writes during audit. Persist tests under tmp_path. Caller-selected run2 isolation is real; native snapshot feature remains DL-016.

**Acceptance/regression checks — proposed, not run by this pass:** Command plan lists all output/dependency effects; timeout and final rc; originals/other-owner changes preserved. After code edits use normal admitted required gates, not audit flags to evade them.

**Owner:** Downloads test/probe owner.

#### DL-046 — Concurrent source ownership and historical evidence must survive

**P1 · preserve-no-change · O0 and O5.**

**Evidence:** **Hash recheck + source**, C:7-15, E.source_sha256; root AGENTS changed concurrently, remaining17 hashes match. M:176-179.

**Affected files/tasks:** Owner workflow/branch/task plan, mutable instructions and historical receipts.

**Required action:** Re-read instructions and assign writer/checkout before edits; retain other-owner dirty state and historical probe hashes. User accepting Q5 is not a GO for parked1774/KB or other workflows. No broad restart/rollback/goal change. Revised Q5 is approved for the bounded dotfiles migration; Downloads remains this owner review/fix handoff. No further Q5 confirmation is required, but this document does not perform or authorize Downloads application adoption. [R2]

**Acceptance/regression checks — proposed, not run by this pass:** Fresh owner scope/HEAD/hash attestation and all applicable gates when implementation is actually admitted; exact final-source report status.

**Owner:** Downloads project coordinator/current source owner.

#### SYN-003 — Preserve the triaged public upstream scanner fixture finding

**P3 · preserve-no-change · O0/O4 evidence preservation; no application repair**

**Evidence:** F actual execution inventory and migration-facts/gitleaks-report.json plus gitleaks-triage.json: the primary-source scan returned rc1 on an upstream synthetic mise marker fixture; value-free triage identified the public test fixture. Later review-artifact scans are separate results.

**Affected files/tasks:** Audit evidence, source corpus and final validation claims; no Downloads application source

**Required action:** Keep the verbatim source and original scanner result/triage. Do not delete source evidence, add suppressions, rotate a real credential based only on this public fixture, or claim every historical scan was clean.

**Acceptance/regression checks — proposed, not run by this pass:** Final evidence distinguishes this retained upstream fixture from live-secret exposure and from independently scanned final documents. Exact findings are retained without reproducing fixture/credential bytes in the handoff.

**Owner:** Audit evidence owner/documentation reviewer.

## Completeness reconciliation

All DL-001 through DL-047 from the independent completeness checklist appear exactly once as findings above. SYN-001 adds the primary-source GraphQL validation distinction; SYN-002 adds the corrected native saved-query/API claim; SYN-003 preserves the triaged upstream scanner fixture. SDK dispatch/auth, every catalog/CLI/report finding, native-source/profile/runtime semantics, migration narrative corrections, live-validation gaps and preservation boundaries are included. The machine-readable reconciliation is dotfiles `.agent/state/fnox-mise-session-audit-20261008/document-reconciliation.json`. [R3]

The accepted dotfiles producer/rerun SDK integration remains explicit in this handoff, but is owned by its separate migration task. Current gh receipts remain gh evidence. KB pin/source-provenance work remains a separate prerequisite, and this handoff does not expand Downloads into a KB or unrelated PDF repair project.

## Source register and reviewer provenance

The required strict-five research attempt returned **rc 1 / RESEARCH INCOMPLETE**: the GitHub discussion canary returned zero items (`empty_unverified`), and the official GitHubKit repository has discussions disabled. Firecrawl search returned HTTP 402/credits-exhausted and used the accepted Serper fallback, marked **PROVISIONAL**. Exa, Context7, Firecrawl developer and Last30Days returned results; GitHub issues and releases had verified empty results for the submitted research query. The original receipt remains unchanged. This failure does not invalidate the cited source reads or live SDK defect controls, and those controls do not establish complete five-provider coverage. [R1]

| ID | Verified source or receipt |
|---|---|
| D1 | Downloads `pyproject.toml:27`; installed package metadata in dotfiles `.agent/state/fnox-mise-session-audit-20261008/githubkit-consumer-review/execution-receipt.json`; `src/github_searcher/client.py:12–21`. |
| D2 | Dotfiles `.agent/state/fnox-mise-session-audit-20261008/githubkit-consumer-review/execution-receipt.json`, `catalog.json`, `run1/`, `run2/` and reports. Receipt includes exact commands, rc/envelopes, eight output hashes and source hashes. |
| D3 | Downloads `src/github_searcher/search.py:24–42,45–78,81–116,119–176,179–250,259–337`; `schemas/enums.json:75–85`. |
| D4 | Downloads installed SDK schema `githubkit_schemas/v2026_03_10/models/group_0540.py:71`; `src/github_searcher/search.py:171`; live issue-result receipt. |
| D5 | Downloads `schemas/github_search.json`; `schemas/enums.json`; `searches/searches.json`; `pyproject.toml:138–152`. |
| D6 | Downloads `src/github_searcher/cli.py:25–79`; `catalog.py:44,67–72,88–105`; `report.py:25–47`; `mise.toml:77–80`. |
| D7 | Downloads `mise.toml:18,72–80`; `src/github_searcher/client.py:12–21`; receipt authentication_evidence. |
| D8 | Downloads `AGENTS.md`, sections 2–5,10–15,19; `src/github_searcher/AGENTS.md`. |
| F1 | Dotfiles `docs/specs/research-saved-searches-1502.md:314–319`; `mise.toml:926–929`; `python/src/dotfiles_setup/generated/saved_search_file.py:15–21`; `saved_searches.py:66–68,122–133,575–631,696–824,886–941,960–1011,1051–1083`; `research_fanout.py:766–767,2498–2505`. Current packets: `.agent/state/fnox-mise-session-audit-20261008/githubkit-research.md` and `githubkit-consumer-review.md`. |
| M1 | [Native mise fnox integration, v2026.10.4](https://github.com/jdx/mise/blob/v2026.10.4/docs/environments/secrets/fnox.md); dotfiles `.agent/state/fnox-mise-session-audit-20261008/migration-facts/primary/manifest.json`. |
| R1 | Dotfiles `.agent/state/fnox-mise-session-audit-20261008/githubkit-research.md` and `githubkit-research/receipt-verification.json`; required request ID `01a11aad-2655-7a00-af5c-2cd1e111dd6c`, policy `strict-five-v2`. |
| R2 | Dotfiles `.planning/2026-10-08-fnox-mise-session-audit/decision-q5-revised.json`: direct human Q5 yes, complete Downloads finding handoff requirement, approved separate dotfiles owner and surviving boundaries. |
| R3 | Dotfiles `.agent/state/fnox-mise-session-audit-20261008/downloads-all-findings-checklist.md`: 47 unique finding IDs, source/live distinction, six initial preserve items, source recheck17/18 and current AGENTS drift. The independent synthesis adds SYN-001–003. |
| F / M | Dotfiles `.agent/state/fnox-mise-session-audit-20261008/migration-facts.md` and `migration-guide-corrected-draft.md`; primary metadata/structural probes and `migration-facts/primary/manifest.json`; historical scanner result/triage in `migration-facts/gitleaks-report.json` and `gitleaks-triage.json`. |
| U4 | Dotfiles `.agent/state/fnox-mise-session-audit-20261008/githubkit-research.md` and `githubkit-research/primary-sources.json`:16 pinned primary artifacts, SDK method/types/paginator/retry semantics, GitHub App issue/PR constraints, live GraphQL schema and official saved-query/UI documentation. |
| U1 | [GitHubKit v0.16.1 REST usage](https://github.com/yanyongyu/githubkit/blob/v0.16.1/docs/usage/rest-api.md), parsed_data and JSON type distinctions. |
| U2 | [GitHubKit v0.16.1 GraphQL usage](https://github.com/yanyongyu/githubkit/blob/v0.16.1/docs/usage/graphql.md) and `githubkit/graphql/__init__.py:51–71`, `models.py:23`. |
| U3 | GitHubKit v0.16.1 REST/GraphQL pagination documentation and source; live GitHub GraphQL introspection in dotfiles `.agent/state/fnox-mise-session-audit-20261008/githubkit-research/primary/github-graphql-search-schema.json`. |

Consumer reviewer: `/root/takeover_session_census`, gpt-6-astra/high, runtime-attested. Tools actually used: existing github-deep-search skill, native fnox/mise/uv project pipeline, actual GitHubKit REST/GraphQL requests, read-only source/Git inspection and audit-owned artifact writes. SDK/history/primary-source reviewer: `/root/fnox_migration_facts`, gpt-6-astra/xhigh; its separate strict-five receipt remains independently reported and cannot be inferred from these SDK calls. Independent synthesis: `/root/fnox_scope_synthesis`, gpt-6-astra/xhigh by dispatch; planning-with-files, bounded source/report reads and assigned-artifact writes.

Research routes actually run through native fnox were Exa HTTP, Firecrawl developer/search with Serper fallback, Context7 CLI, GitHub CLI and the Last30Days script. The legacy research runner's GitHub arms used gh; the separate Downloads controls used GitHubKit. No connector app is claimed as used by these CLI/HTTP routes. The research lane reused the mise skill; the parent coordination also used grilling, task orchestration and planning-with-files.

The SDK audit did not run application tests/gates, regenerate models, install/sync dependencies, extract tokens, edit Downloads source/config/catalogs, or validate a finished migration. Its successful public requests and failed authenticated routes remain separate evidence.

This final completeness pass reused the established planning-with-files ownership and prior review skills. It read only local reports, the accepted decision, selected documentation/task headers and the independent checklist; it wrote only the published handoff, its identical audit copy and reconciliation JSON. No fresh provider/credential call, SDK request, application test/gate, code generation, package install/sync, configuration change or Downloads source/PDF write was performed. A guessed audit-root decision path was absent; the authoritative decision was read from the selected `.planning/` directory. Final document/reconciliation checks are recorded separately and do not certify application fixes.
