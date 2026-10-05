**Review complete: recommend HOLDs for specs 02, 04 and 19.** The team produced 88 decision blocks, including distinct amendments added after the original drafts. No direct contradiction with Ray’s settled §8 rulings was found.

Licensed dissent requires corrections before the affected implementation proceeds:

- **01:** coverage ownership points to 02, while 02 assigns it to item 29.
- **03:** “unknown gates create no directories” contradicts current code and tests; its bounded, nonraising identity promise also conflicts with discovery and index-copy error paths.
- **04:** the unconditional live-child lease guarantee conflicts with an acknowledged unlock race.
- **17:** `root.resolve()` is prescribed before the runner creates `root`; discovery can hang before the protected deadline starts.
- **19:** the environment-only fallback lacks matching CLI/documentation instructions; eager-text and permission-defense deferrals conflict with current rules.

All three specialists completed. **Gate exit codes: N/A**—pytest, lint and lint-docs were not run, as requested. No report file, checkout edit, commit or test execution occurred.

Citation notation:

| Key | Source |
|---|---|
| S01 | [01-capacity-bound-review-dispatch.md at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening/01-capacity-bound-review-dispatch.md) |
| S02 | [02-settlement-publication-integrity.md at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening/02-settlement-publication-integrity.md) |
| S03 | [03-immutable-gate-provenance.md at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening/03-immutable-gate-provenance.md) |
| S04 | [04-descriptor-owned-resource-leases.md at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening/04-descriptor-owned-resource-leases.md) |
| S17 | [17-hermetic-mise-experiments.md at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening/17-hermetic-mise-experiments.md) |
| S19 | [19-secret-output-boundary.md at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening/19-secret-output-boundary.md) |
| S20 | [20-citation-precheck.md at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening/20-citation-precheck.md) |
| Ledger | [Process-hardening ledger at 9ef93b55](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/specs/process-hardening-2026-10-04.md) |
| V2 | [01/02/03/20 rev-2 verifier](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/research/kb/reports/agents/premise-verifier-process-hardening-01-02-03-20-rev2.md) |
| V04 | [04 verifier](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/research/kb/reports/agents/premise-verifier-process-hardening-04.md) |
| V043 | [02/04 rev-3 verifier](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/research/kb/reports/agents/premise-verifier-process-hardening-02-04-rev3.md) |
| V17 | [17 verifier](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/research/kb/reports/agents/premise-verifier-process-hardening-17.md) |
| V0417 | [04/17 rev-2 verifier](https://github.com/ray-manaloto/dotfiles/blob/9ef93b55/docs/research/kb/reports/agents/premise-verifier-process-hardening-04-17-rev2.md) |

`S01:24` means line 24 of that fixed blob. `P/` means `python/src/dotfiles_setup/`; `T/` means `tests/`. Code, tests and rule citations refer to the inspected checkout at **cd66147e64eb0f2fc6c1f875bc3adda083e820fe**. All nine specified premise-verifier reports were read.

Spec 04’s former OPEN labels are absent at the pinned revision; its resolved numbered rulings are covered below without inventing aliases. Spec 17’s U1–U5 correspond to R1–R5.

### 01-U1: Preserve the existing request model direction

- **Chosen:** Extend handwritten `SdlcTeamRequest`; generate new capacity types. S01:24–32.
- **Alternatives:** A—preserve direction. **PRO:** retains schema parity. **CON:** maintains a generated-model-policy exception. `T/test_sdlc_team.py:1706`; `python/AGENTS.md:111`. B—migrate everything. **PRO:** one pipeline. **CON:** broadens decoding and compatibility changes. S01:27.
- **Recommendation:** A, with the existing-model exception explicitly documented.
- **Reversibility after implementation:** **MODERATE**—schema and decoder consumers require coordinated migration.
- **Contradicts a Ray ruling?** No.

### 01-U2: Use separate runs for excess domains

- **Chosen:** No waves or thread reuse; carry bound reports into another run. S01:33–38.
- **Alternatives:** A—separate runs. **PRO:** avoids relying on unproven slot release. **CON:** adds orchestration and report custody. S01:35. B—close-then-spawn waves. **PRO:** potentially one synthesis run. **CON:** release remains unverified. V2:37; S01:322.
- **Recommendation:** A until supported release evidence exists.
- **Reversibility after implementation:** **MODERATE**—callers adopt the split-run workflow.
- **Contradicts a Ray ruling?** No.

### 01-U3: Bind reused reviews to source state

- **Chosen:** Bind report digest, spec digest and repository HEAD. S01:39–40.
- **Alternatives:** A—those three bindings. **PRO:** detects changed reports and commits. **CON:** HEAD misses uncommitted source changes. S01:240. B—add tree identity. **PRO:** distinguishes dirty source. **CON:** adds fingerprint dependencies and fields. S03:194–207.
- **Recommendation:** B through an explicitly scoped revision; require clean source until then.
- **Reversibility after implementation:** **MODERATE**—older review records need compatibility handling.
- **Contradicts a Ray ruling?** No.

### 01-U4: Count the dispatcher in the budget

- **Chosen:** Total-thread units include the dispatcher; default four. S01:41–42.
- **Alternatives:** A—total threads. **PRO:** measures the limiting resource. **CON:** callers subtract one specialist. S01:172. B—specialist-only units. **PRO:** direct roster count. **CON:** hides parent consumption and needs another total. S01:314.
- **Recommendation:** A; keep the subtraction explicit.
- **Reversibility after implementation:** **MODERATE**—changing units changes existing request meaning.
- **Contradicts a Ray ruling?** No.

### 01-U5: Defer coverage recording to its corrected owner

- **Chosen:** Record no coverage here; the header assigns settlement coverage to 02. S01:43–46.
- **Alternatives:** A—defer to item 29. **PRO:** matches corrected ownership. **CON:** coverage remains absent meanwhile. S02:241; Ledger:228. B—add coverage here. **PRO:** closes the gap sooner. **CON:** exceeds this file allowance and ownership. S01:45.
- **Recommendation:** A after correcting the stale 02 handoff.
- **Reversibility after implementation:** **MODERATE**—coverage ownership crosses lanes.
- **Contradicts a Ray ruling?** No.

### 01-EAGER: Put capacity guidance in the skill

- **Chosen:** Leave the eager rule untouched; use the skill subsection. S01:47–51.
- **Alternatives:** A—skill plus generated prompt. **PRO:** avoids eager growth. **CON:** skill guidance depends on invocation. S01:293. B—neutral-size eager replacement. **PRO:** reaches every launch. **CON:** changes standing text and needs budget validation. `.claude/rules/codex-sdlc-team.md:13`.
- **Recommendation:** A; generated prompts carry the operational requirement.
- **Reversibility after implementation:** **EASY**—prose placement has no receipt migration.
- **Contradicts a Ray ruling?** No.

### 01-ASSERTIONS: Assert the complete capacity refusal

- **Chosen:** Assert the full literal message. S01:52.
- **Alternatives:** A—complete assertion. **PRO:** catches the diagnosed parent-count regression. **CON:** couples wording to the test. S01:226. B—structured counts plus essential text. **PRO:** tolerates harmless wording changes. **CON:** needs a stable structured surface. [no prior evidence]
- **Recommendation:** A for the existing single-error-string interface.
- **Reversibility after implementation:** **EASY**—test strength changes locally.
- **Contradicts a Ray ruling?** No.

### 01-ISOLATION: Prevent mutation tests launching real Codex

- **Chosen:** Patch executable lookup; isolate Git routing and commit identity. S01:53–56.
- **Alternatives:** A—isolated boundaries. **PRO:** regressions remain credit-free and repository-local. **CON:** requires explicit fixtures. `T/test_sdlc_team.py:201`; S01:205. B—real executable negative arm. **PRO:** exercises launch wiring. **CON:** broken refusal starts real work. S01:54.
- **Recommendation:** A; retain separately authorized real integration.
- **Reversibility after implementation:** **EASY**—fixture-only choices.
- **Contradicts a Ray ruling?** No.

### 01-SEAM: Inject HEAD acquisition through dispatch

- **Chosen:** Add `head_revision` and extend `_capture_dispatch`. S01:54; :190.
- **Alternatives:** A—explicit callable. **PRO:** isolates the new boundary while retaining composition. **CON:** adds an API parameter. `tests/AGENTS.md:97`. B—patch subprocess internals. **PRO:** preserves the signature. **CON:** shared `Popen` patches affect `subprocess.run`. `T/test_sdlc_team.py:202`.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—optional injection preserves callers.
- **Contradicts a Ray ruling?** No.

### 02-D1: Generate enums without migrating settlement

- **Chosen:** Generate two enums; retain code-first settlement. S02:10–12; :238.
- **Alternatives:** A—additive enums. **PRO:** preserves legacy decoding. **CON:** retains two schema directions. `T/test_sdlc_team.py:566`. B—generated settlement. **PRO:** follows general model policy. **CON:** changes unknown-field handling and parity direction. S02:238; `python/AGENTS.md:111`.
- **Recommendation:** A with an explicit grandfathered-model rationale.
- **Reversibility after implementation:** **MODERATE**—later migration needs compatibility tests.
- **Contradicts a Ray ruling?** No.

### 02-D2: Require both receipt formats

- **Chosen:** Require JSON and Markdown publication. S02:13; :239.
- **Alternatives:** A—both required. **PRO:** machine and human records agree. **CON:** Markdown failure blocks completion. `P/sdlc_team.py:982`. B—JSON authoritative, Markdown derived. **PRO:** one critical artifact. **CON:** weakens the human-receipt obligation. S02:239.
- **Recommendation:** A unless Ray changes the publication contract.
- **Reversibility after implementation:** **MODERATE**—completion semantics affect consumers.
- **Contradicts a Ray ruling?** No.

### 02-D3: Repair publication without repeating child work

- **Chosen:** No republish command; repair means make paths writable and re-dispatch. S02:14–15; :152.
- **Alternatives:** A—re-dispatch. **PRO:** reuses an entrypoint. **CON:** repeats successful work merely to repair evidence. S02:152. B—separately specified recovery-only publication. **PRO:** preserves performed work. **CON:** needs custody and immutable-source validation. S02:240.
- **Recommendation:** B; keep settlement failed pending that contract.
- **Reversibility after implementation:** **HARD**—repeated child effects may be irreversible.
- **Contradicts a Ray ruling?** No; recovery remains subject to approved-remedy policy, Ledger:219.

### 02-D4: Separate evidence from content completeness

- **Chosen:** Content disposition and coverage belong to item 29. S02:16–20; :241.
- **Alternatives:** A—separate axis. **PRO:** preserves evidence’s precise meaning. **CON:** incomplete reviews can still say completed/verified meanwhile. S02:93–95. B—add content here. **PRO:** closes the gap sooner. **CON:** expands the typed contract and scope. Ledger:228.
- **Recommendation:** A with explicit warnings and owned item-29 custody.
- **Reversibility after implementation:** **MODERATE**—consumers must distinguish axes.
- **Contradicts a Ray ruling?** No.

### 02-PATH: Preserve exact unpublished destination strings

- **Chosen:** Record payload path strings verbatim, JSON then Markdown. S02:21–22; :172.
- **Alternatives:** A—verbatim. **PRO:** identifies the attempted destination. **CON:** preserves noncanonical spelling. `P/sdlc_team.py:983`. B—resolve again. **PRO:** canonical presentation. **CON:** filesystem changes can alter meaning. S02:176.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—a separate canonical field can be added.
- **Contradicts a Ray ruling?** No.

### 02-ENUM: Pin generated enum member names

- **Chosen:** Require `x-enum-varnames` and inspect generated names. S02:23–24; :186.
- **Alternatives:** A—explicit names. **PRO:** matches uppercase API references. **CON:** generator-specific metadata. S02:188. B—accept generated lowercase names. **PRO:** fewer extensions. **CON:** changes references and expectations. V2:35.
- **Recommendation:** A; confirm generated output without hand edits.
- **Reversibility after implementation:** **MODERATE**—Python callers depend on names.
- **Contradicts a Ray ruling?** No.

### 02-CHILD-RC: Make nonzero child outcomes testable

- **Chosen:** Optional return-code override in the supervisor fixture. S02:25–26.
- **Alternatives:** A—fixture override. **PRO:** separates evidence validity from child success. **CON:** adds fixture state. `T/test_sdlc_team.py:42`; S02:337. B—one-off failure fixture. **PRO:** narrower setup. **CON:** duplicates boundary composition. `T/test_sdlc_team.py:101`.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—production behavior is unchanged.
- **Contradicts a Ray ruling?** No.

### 02-GUARD: Preserve timeout while downgrading completion

- **Chosen:** Downgrade only COMPLETED; mutation removes that guard. S02:27; :207.
- **Alternatives:** A—guarded downgrade. **PRO:** preserves timeout outcome. **CON:** needs separate evidence classification. `P/sdlc_team.py:1027`. B—all publication failures become FAILED. **PRO:** simpler branch. **CON:** destroys timeout information. S02:363.
- **Recommendation:** A.
- **Reversibility after implementation:** **MODERATE**—terminal statuses guide recovery.
- **Contradicts a Ray ruling?** No.

### 02-ORDER: Serialize overlapping implementation lanes

- **Chosen:** Dispatch 01 first, then rebase and recheck 02. S02:29–30.
- **Alternatives:** A—serialized edits. **PRO:** preserves fresh shared-file premises. **CON:** increases elapsed time. V2:99. B—parallel isolated branches with final re-anchoring. **PRO:** throughput. **CON:** merge and generated-output reconciliation. V2:101.
- **Recommendation:** A for 01/02.
- **Reversibility after implementation:** **EASY**—procedural ordering.
- **Contradicts a Ray ruling?** No.

### 02-PROVENANCE: Treat spawn-failure evidence as confirmed

- **Chosen:** Replace the blind absence claim with direct log evidence. S02:28; :463.
- **Alternatives:** A—direct evidence. **PRO:** supports the incident. **CON:** gitignored evidence requires direct access. Ledger:242. B—retain unverified classification. **PRO:** honest when inaccessible. **CON:** understates an observed finding. V2:45.
- **Recommendation:** A where accessible; otherwise cite the pinned verifier.
- **Reversibility after implementation:** **EASY**—evidence classification.
- **Contradicts a Ray ruling?** No.

### 03-U-1: Generate receipts while preserving GateResult

- **Chosen:** Generate new receipt types; keep existing result/status models. S03:11–13.
- **Alternatives:** A—additive receipts. **PRO:** preserves JSON and exit mappings. **CON:** another model family. `P/gate_result.py:43`; :72. B—migrate both. **PRO:** uniform pipeline. **CON:** expands compatibility and classifier changes. `T/test_gate_result.py:304`.
- **Recommendation:** A with an explicit existing-model exception.
- **Reversibility after implementation:** **MODERATE**—persisted consumers must migrate together.
- **Contradicts a Ray ruling?** No.

### 03-U-2: Fingerprint through a temporary Git index

- **Chosen:** Copy index, stage into the copy, write a tree; leave objects for GC. S03:14–18; :194.
- **Alternatives:** A—Git tree identity. **PRO:** captures nonignored source without altering the real index. **CON:** runs clean filters and writes unreachable objects. S03:198; :380. B—custom raw-file digest. **PRO:** avoids object writes. **CON:** invents selection semantics. [no prior evidence]
- **Recommendation:** A with filter and ignored-input limitations recorded.
- **Reversibility after implementation:** **HARD**—fingerprint semantics become receipt identity.
- **Contradicts a Ray ruling?** No.

### 03-U-3: Distinguish unverified evidence with rc 3

- **Chosen:** 0 pass; 1/124/127 verified failure; 3 unverified; 2 unknown. S03:19–20.
- **Alternatives:** A—distinct rc 3. **PRO:** separates missing evidence from failure. **CON:** another caller branch. S03:268. B—rc 1 for both. **PRO:** familiar shell behavior. **CON:** collapses remediation choices. `P/gate_result.py:72`.
- **Recommendation:** A, after correcting the contradictory unknown-gate filesystem contract at S03:216/:361 and `P/gate_result.py:130/:159`.
- **Reversibility after implementation:** **MODERATE**—shell consumers depend on mapping.
- **Contradicts a Ray ruling?** No.

### 03-U-4: Update standing authorization without eager growth

- **Chosen:** Reject eager-rule edits; document verify in help and evidence. S03:21–25.
- **Alternatives:** A—chosen placement. **PRO:** avoids eager growth. **CON:** eager instructions still authorize gate-run rc. `.claude/rules/verify-before-advancing.md:27`. B—neutral-size replacement. **PRO:** aligns standing authorization with verify. **CON:** needs instruction and budget review. S03:67.
- **Recommendation:** B or equivalent verified authorization integration.
- **Reversibility after implementation:** **MODERATE**—agents must adopt a new authorization path.
- **Contradicts a Ray ruling?** No.

### 03-U-5: Capture source identity before and after

- **Chosen:** Start/end mismatch yields unidentified. S03:26–27.
- **Alternatives:** A—double capture. **PRO:** refuses evidence across moving source. **CON:** intentional nonignored output invalidates it. S03:254. B—start-only binding. **PRO:** fewer probes. **CON:** cannot establish which final tree passed. S03:55.
- **Recommendation:** A; classify mutating gates explicitly.
- **Reversibility after implementation:** **MODERATE**—receipt interpretation changes.
- **Contradicts a Ray ruling?** No.

### 03-EXCLUSION: Exclude gate artifacts by pathspec

- **Chosen:** Exclude `RESULTS_DIR`; fixture ignore rules are secondary. S03:29–31; :207.
- **Alternatives:** A—explicit exclusion. **PRO:** works without ignore entries. **CON:** intentionally omits that subtree. `P/gate_result.py:55`; S03:431. B—rely on `.gitignore`. **PRO:** less probe logic. **CON:** new repositories invalidate their own receipts. S03:211.
- **Recommendation:** A using the canonical constant.
- **Reversibility after implementation:** **MODERATE**—exclusion changes identity.
- **Contradicts a Ray ruling?** No.

### 03-ENV: Bound identity probes and fail closed

- **Chosen:** Reuse Git isolation, reset temporary index, return None on specified failures. S03:33–34; :186.
- **Alternatives:** A—bounded, nonraising probe. **PRO:** satisfies the promised contract. **CON:** requires correcting discovery/index-copy scope. `P/process_env.py:76`; V2:85. B—accept hang/raise residuals. **PRO:** smaller patch. **CON:** contradicts “never raises.” S03:184; :358.
- **Recommendation:** A; CORRECT FIRST.
- **Reversibility after implementation:** **MODERATE**—probe behavior controls evidence availability.
- **Contradicts a Ray ruling?** No.

### 03-TIMEOUT-RECEIPT: Publish terminal queue-timeout evidence

- **Chosen:** Lock-wait timeout publishes result and receipt without a log. S03:35; :228.
- **Alternatives:** A—terminal receipt. **PRO:** distinguishes admission failure from abandonment. **CON:** nullable log pairing needs validation. `P/gate_result.py:172`. B—start evidence only. **PRO:** simpler path. **CON:** settled timeout looks incomplete. S03:232.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—localized receipt metadata.
- **Contradicts a Ray ruling?** No.

### 03-TEST-PATH: Preserve Git while faking gate executables

- **Chosen:** Prepend fake-executable directory to PATH. S03:32.
- **Alternatives:** A—prepend. **PRO:** native Git remains available. **CON:** other executables remain reachable. `T/test_gate_result.py:114`; S03:134. B—replace PATH and explicitly supply Git. **PRO:** tighter isolation. **CON:** more setup and platform sensitivity. [no prior evidence]
- **Recommendation:** A with controlled commands and disposable repositories.
- **Reversibility after implementation:** **EASY**—fixture-only change.
- **Contradicts a Ray ruling?** No.

### 03-MUTATING-GATES: Reject evidence after source writes

- **Chosen:** Nonignored writes yield unidentified; acknowledge clean filters. S03:36–37; :380.
- **Alternatives:** A—read-only authorization gates. **PRO:** binds unchanged input. **CON:** formatting/artifact gates need separate treatment. S03:432. B—authorize resulting tree. **PRO:** accommodates mutation. **CON:** may bless code never fully tested. S03:55.
- **Recommendation:** A; separate mutation from validation.
- **Reversibility after implementation:** **MODERATE**—gate classifications affect callers.
- **Contradicts a Ray ruling?** No.

### 03-WAIT-BOUND: Bound concurrent-publication tests

- **Chosen:** Timeout V11’s synchronization wait. S03:38.
- **Alternatives:** A—bounded wait. **PRO:** regressions fail instead of deadlocking. **CON:** deadline selection. S03:441. B—unbounded wait. **PRO:** avoids timing sensitivity. **CON:** broken publication hangs the suite. V2:78.
- **Recommendation:** A with generous deadline and explicit failure.
- **Reversibility after implementation:** **EASY**—fixture-only change.
- **Contradicts a Ray ruling?** No.

### 04-SCOPE: Expose CPU-only CLI and three library resources

- **Chosen:** Library supports CPU/checkout/worktree; CLI defers the latter two to 05. S04:24–30.
- **Alternatives:** A—staged exposure. **PRO:** tests separation now. **CON:** CLI mutation custody remains absent. S04:29. B—expose all now. **PRO:** fuller interface sooner. **CON:** needs item-05 integration. V04:91.
- **Recommendation:** A as explicit partial delivery.
- **Reversibility after implementation:** **HARD**—canonical keys become lock identity.
- **Contradicts a Ray ruling?** No; preserve release-after-push, Ledger:217.

### 04-CLI: Use comma-separated resources and typed receipts

- **Chosen:** `--resources K[,K...]`; no request file or stderr markers. S04:31–34.
- **Alternatives:** A—CLI plus receipt. **PRO:** simple shell use with typed evidence. **CON:** parsing edge cases. S04:32. B—request file. **PRO:** supports richer requests. **CON:** another public interface. V04:50.
- **Recommendation:** A for CPU-only exposure.
- **Reversibility after implementation:** **MODERATE**—wrappers depend on argv.
- **Contradicts a Ray ruling?** No.

### 04-LABEL: Truncate all labels

- **Chosen:** Explicit/default labels truncate to 120 characters. S04:35.
- **Alternatives:** A—truncate. **PRO:** valid lease decoding. **CON:** long labels lose distinctions. V04:33. B—reject oversized labels. **PRO:** exact attribution. **CON:** diagnostic text becomes admission failure. `P/host_lock.py:257`.
- **Recommendation:** A; lease identifiers supply identity.
- **Reversibility after implementation:** **EASY**—separate detail fields remain possible.
- **Contradicts a Ray ruling?** No.

### 04-WAIT: Reject invalid waits

- **Chosen:** Reject nan, infinity and negative waits with rc 2. S04:36.
- **Alternatives:** A—refuse. **PRO:** deterministic admission limits. **CON:** differs from legacy fallback. `P/host_lock.py:164`. B—normalize defaults. **PRO:** preserves tolerance. **CON:** hides malformed intent. `P/host_lock.py:165`.
- **Recommendation:** A for the new CLI.
- **Reversibility after implementation:** **EASY**—localized validation.
- **Contradicts a Ray ruling?** No.

### 04-KEYS: Normalize whitespace and duplicates

- **Chosen:** Strip whitespace, reject empty elements, collapse duplicates. S04:37–38.
- **Alternatives:** A—normalize. **PRO:** one lock per logical key. **CON:** repeated input can be concealed. S04:774. B—reject whitespace/duplicates. **PRO:** catches mistakes. **CON:** less forgiving construction. [no prior evidence]
- **Recommendation:** A with canonical resources recorded.
- **Reversibility after implementation:** **EASY**—mechanical caller updates.
- **Contradicts a Ray ruling?** No.

### 04-VALIDATION: Validate before acquiring

- **Chosen:** Validate every key before opening locks. S04:39.
- **Alternatives:** A—prevalidation. **PRO:** invalid mixed requests leave no lock artifacts. **CON:** initial pass required. S04:774. B—validate during acquisition. **PRO:** one traversal. **CON:** partially admits impossible requests. V04:85.
- **Recommendation:** A.
- **Reversibility after implementation:** **MODERATE**—partial admission affects concurrency.
- **Contradicts a Ray ruling?** No.

### 04-MODEL: Generate required-nullable receipt fields

- **Chosen:** Reachable `$def`; nullable fields remain required. S04:40–44.
- **Alternatives:** A—required-nullable. **PRO:** distinguishes known-null from missing. **CON:** complete payloads required. V04:35. B—optional-nullable. **PRO:** looser compatibility. **CON:** generates UNSET and weakens meaning. V04:38.
- **Recommendation:** A through codegen.
- **Reversibility after implementation:** **MODERATE**—persisted decoder contract.
- **Contradicts a Ray ruling?** No.

### 04-PUBLICATION: Publish before starting the child

- **Chosen:** Atomic admission receipt, terminal rewrite; first failure blocks launch. S04:45–48.
- **Alternatives:** A—prelaunch publication. **PRO:** preserves custody and rc attribution. **CON:** disk failure blocks work. S04:47. B—terminal-only publication. **PRO:** fewer writes. **CON:** killed supervisors leave no admission record. S04:775.
- **Recommendation:** A.
- **Reversibility after implementation:** **MODERATE**—consumers rely on visibility.
- **Contradicts a Ray ruling?** No.

### 04-ARGPARSE: Allow parser errors without receipts

- **Chosen:** Argparse errors return 2 without receipts. S04:49.
- **Alternatives:** A—no parser receipt. **PRO:** follows existing behavior. **CON:** some rc-2 cases lack typed reasons. `P/host_lock.py:256`. B—preparse receipt routing. **PRO:** uniform evidence. **CON:** ambiguous destination discovery and another parser path. [no prior evidence]
- **Recommendation:** A with the distinction documented.
- **Reversibility after implementation:** **EASY**—parser receipts can be added later.
- **Contradicts a Ray ruling?** No.

### 04-LAUNCH: Use Popen plus wait

- **Chosen:** Launch with `Popen`, expose PID, then wait. S04:50–51.
- **Alternatives:** A—Popen/wait. **PRO:** live attribution and explicit exception handling. **CON:** cleanup sequencing. V04:98. B—`subprocess.run`. **PRO:** simpler composition. **CON:** no live PID and different exception cleanup. `P/host_lock.py:261`; V04:67.
- **Recommendation:** A, preserving child rc.
- **Reversibility after implementation:** **MODERATE**—supervision behavior changes.
- **Contradicts a Ray ruling?** No.

### 04-LIFETIME: Resolve the live-child unlock race

- **Chosen:** Child survives supervisor death; exceptions wait it out, with accepted launch-window races. S04:52–54; :101; :492.
- **Alternatives:** A—narrow guarantee. **PRO:** fixes common death cases. **CON:** shared `LOCK_UN` can release under a live child. `P/host_lock.py:195`. B—hold until closed or explicitly ratified. **PRO:** aligns admission with live ownership. **CON:** delays rollout. S04:118.
- **Recommendation:** B; stop the contradictory unconditional guarantee.
- **Reversibility after implementation:** **HARD**—already admitted overlap cannot be undone.
- **Contradicts a Ray ruling?** No.

### 04-HOLDER: Store stripped holder records

- **Chosen:** Store `read_holder`’s representation. S04:55–56.
- **Alternatives:** A—stripped equality. **PRO:** matches actual reads. **CON:** loses trailing formatting. `P/host_lock.py:112`. B—raw written record. **PRO:** exact write representation. **CON:** differs from stripped reads. `P/host_lock.py:184`; V04:73.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—old sidecars can be unattributed.
- **Contradicts a Ray ruling?** No.

### 04-SIDECARS: Ignore temporary remnants

- **Chosen:** Read only `<lock>.json`. S04:57–58.
- **Alternatives:** A—exact path. **PRO:** debris cannot corrupt status. **CON:** cleanup remains separate. S04:773. B—directory glob. **PRO:** broad discovery. **CON:** incomplete writes become apparent evidence. V04:101.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—reader policy.
- **Contradicts a Ray ruling?** No.

### 04-CONTRACTS: Register lease verification

- **Chosen:** Add `workflow.slot-lease`. S04:59.
- **Alternatives:** A—structured tokens plus tests. **PRO:** checks critical integration sites. **CON:** tokens prove structure only. V04:102. B—pytest alone. **PRO:** behavior remains central. **CON:** loses verification parity. `python/AGENTS.md:52`.
- **Recommendation:** A, retaining realistic fail arms.
- **Reversibility after implementation:** **EASY**—localized registration.
- **Contradicts a Ray ruling?** No.

### 04-PROVENANCE: Qualify the smoke dependency

- **Chosen:** Cite land-smoke-timeout worktree rather than nonexistent main integration. S04:60–61.
- **Alternatives:** A—branch-qualified evidence. **PRO:** separates shipped/planned behavior. **CON:** worktree citations can disappear. V04:29. B—claim main integration. **PRO:** simpler prose. **CON:** false on the inspected base. S04:91.
- **Recommendation:** A; use a main commit citation after landing.
- **Reversibility after implementation:** **EASY**—provenance correction.
- **Contradicts a Ray ruling?** No.

### 04-TEST-SURFACES: Test interfaces where they exist

- **Chosen:** Receipt discrimination, library multi-resource tests, mixed refusal; remove stderr assertions. S04:62–66.
- **Alternatives:** A—interface-aligned tests. **PRO:** exercises the actual split. **CON:** library tests do not establish future CLI integration. S04:768. B—CLI-only tests. **PRO:** uniform workflow. **CON:** checkout/worktree CLI is unsupported. S04:26.
- **Recommendation:** A; item 05 owns consumer integration.
- **Reversibility after implementation:** **EASY**—test organization.
- **Contradicts a Ray ruling?** No.

### 04-BUSY: Derive busy status from flock

- **Chosen:** No process scan; metadata supplies attribution only. S04:68–69; :84–87.
- **Alternatives:** A—flock state. **PRO:** measures lease ownership. **CON:** unleased smoke is invisible. `P/host_lock.py:267`; S04:509. B—identity scan. **PRO:** could cover unleased work. **CON:** substring false positives and host argv differ. S04:470; [#1690](https://github.com/ray-manaloto/dotfiles/issues/1690).
- **Recommendation:** A as lease observation, bounded by consumer coverage.
- **Reversibility after implementation:** **MODERATE**—“free” can acquire wider interpretation.
- **Contradicts a Ray ruling?** No.

### 04-FREE: Give the predicate explicit rc polarity

- **Chosen:** `--free`: 0 free, 1 held, 2 error; task alias. S04:70–71.
- **Alternatives:** A—explicit predicate. **PRO:** direct bounded-wait use. **CON:** differs from legacy status polarity. `P/host_lock.py:253`; S04:435. B—legacy status. **PRO:** no new mode. **CON:** requires inversion and weaker machine output. S04:426.
- **Recommendation:** A while preserving legacy behavior.
- **Reversibility after implementation:** **MODERATE**—shell conditions depend on polarity.
- **Contradicts a Ray ruling?** No.

### 04-ARGV: Share exact matching inside containers

- **Chosen:** Container preflight uses `is_smoke_argv`; omit host smoke-process field. S04:72–76; :88–89.
- **Alternatives:** A—container matcher. **PRO:** available argv boundaries. **CON:** different host/container mechanisms. S04:473. B—host matcher too. **PRO:** apparent API uniformity. **CON:** host argv begins with docker. S04:470.
- **Recommendation:** A; require a viable positive control for every negative.
- **Reversibility after implementation:** **MODERATE**—consumer coordination.
- **Contradicts a Ray ruling?** No.

### 04-SPLIT: Gate replacement-task delivery on smoke ownership

- **Chosen:** Ship primitives/task now; defer probe replacement until smoke integration lands. S04:90–99.
- **Alternatives:** A—split delivery. **PRO:** primitives available early. **CON:** `host-slot-free` reports free during known smoke. S04:497. B—integrate ownership before replacement task. **PRO:** avoids premature readiness interpretation. **CON:** couples lanes. S04:95.
- **Recommendation:** B for the replacement task; library can land separately.
- **Reversibility after implementation:** **MODERATE**—task adoption spreads.
- **Contradicts a Ray ruling?** No.

### 04-FAIL-ARMS: Arm concurrency fixtures

- **Chosen:** Strip holder exports, retain partial holds, test receipts/SIGINT, require live wrapper. S04:103–113; :775; :778.
- **Alternatives:** A—armed fixtures. **PRO:** regressions fail observably. **CON:** synchronization/setup cost. `P/host_lock.py:176`; S04:768. B—simpler inherited-state fixtures. **PRO:** shorter tests. **CON:** re-entry/dead wrappers can pass falsely. V043:32.
- **Recommendation:** A; pinned V14 includes the later liveness fix.
- **Reversibility after implementation:** **EASY**—fixture strength.
- **Contradicts a Ray ruling?** No.

### 17-U1/R1: Remove inherited mise state

- **Chosen:** Drop `MISE_*`/`__MISE_*`, redirect directories, disable auto-install routes. S17:15–18; :126–143.
- **Alternatives:** A—expanded set. **PRO:** covers system/runtime contamination. **CON:** removes intentional profiles. S17:385–389. B—seven variables only. **PRO:** smaller boundary. **CON:** misses the system leakage arm. S17:386.
- **Recommendation:** A, consistent with mise’s separate configuration/data/state directories. [Primary directory docs](https://mise.jdx.dev/directories.html).
- **Reversibility after implementation:** **MODERATE**—callers rely on profile removal.
- **Contradicts a Ray ruling?** No.

### 17-U2/R2: Trust the resolved experiment directory

- **Chosen:** Set trusted paths to resolved cwd. S17:19; :143.
- **Alternatives:** A—directory trust. **PRO:** noninteractive experiments run. **CON:** descendant scope is broader. [Mise settings](https://mise.jdx.dev/configuration/settings.html#trusted_config_paths). B—explicit trust per experiment. **PRO:** narrower approval. **CON:** additional setup/refusals. S17:143; :452.
- **Recommendation:** A for deliberately selected disposable experiments; document scope.
- **Reversibility after implementation:** **EASY**—trust state is disposable.
- **Contradicts a Ray ruling?** No.

### 17-U3/R3: Publish optional results atomically

- **Chosen:** Optional typed `--result PATH`, codec encoding and atomic replacement. S17:20; :185–217; :236.
- **Alternatives:** A—typed file. **PRO:** avoids partial JSON and distinguishes timeout. **CON:** durable interface. S17:195–196; :237. B—rc only. **PRO:** fewer artifacts. **CON:** child rc 124 and boundary timeout are indistinguishable. S17:366.
- **Recommendation:** A using existing codec policy, `P/codec.py:2–15`.
- **Reversibility after implementation:** **MODERATE**—schema consumers.
- **Contradicts a Ray ruling?** No.

### 17-U4/R4: Assign deferred adoption

- **Chosen:** Skill/rule recipes deferred; follow-up names direct uv entrypoint. S17:21–22; :80–81.
- **Alternatives:** A—unassigned follow-up. **PRO:** small implementation scope. **CON:** adoption lacks custody. S17:21. B—owned companion adoption. **PRO:** callers receive protected recipes. **CON:** another scoped change. `.claude/rules/agent-artifact-conventions.md:90–93`.
- **Recommendation:** B while keeping implementation separate.
- **Reversibility after implementation:** **EASY**—recipe edits.
- **Contradicts a Ray ruling?** No.

### 17-U5/R5: Preserve inherited PATH

- **Chosen:** Leave PATH unchanged; disclose residual. S17:23; :297–298.
- **Alternatives:** A—preserve. **PRO:** existing tools remain executable. **CON:** real mise installs remain reachable. S17:297. B—minimal PATH/explicit executables. **PRO:** constrains binary identity. **CON:** every tool must be located. `T/test_process_env.py:160–172`; :226.
- **Recommendation:** A; describe configuration/state isolation precisely.
- **Reversibility after implementation:** **MODERATE**—restrictions can break callers.
- **Contradicts a Ray ruling?** No.

### 17-R6/R7.11: Correct authored evidence

- **Chosen:** Correct anchors and promote confirmed task facts. S17:24–25; :37; :433; :458–459.
- **Alternatives:** A—correct authored pointers. **PRO:** checkable premises. **CON:** maintenance. S17:5. B—rewrite archived reports. **PRO:** apparent historical consistency. **CON:** violates verbatim preservation. `.claude/rules/agent-artifact-conventions.md:94–95`.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—provenance text.
- **Contradicts a Ray ruling?** No.

### 17-R7.1: Correct the HOME rationale

- **Chosen:** Explain explicit global-file selection and default TOML behavior. S17:27; :145–154; :446.
- **Alternatives:** A—correct rationale. **PRO:** matches verified conditions. **CON:** upstream default dependency. V17:33. B—explicitly pin `MISE_USE_TOML`. **PRO:** visible dependency. **CON:** expands agreed variable contract. S17:359.
- **Recommendation:** A with behavioral leakage tests.
- **Reversibility after implementation:** **EASY**—explanation correction.
- **Contradicts a Ray ruling?** No.

### 17-R7.2: Correct creation and resolution order

- **Chosen:** Resolve cwd/root first; symlink arm. S17:28; :108–114; :373.
- **Alternatives:** A—create root before resolving it. **PRO:** implementable and prevents ceiling leakage. **CON:** requires spec correction. S17:98–108; :167. B—lexical paths. **PRO:** preserves spelling. **CON:** misses exact ancestor matching. V17:71.
- **Recommendation:** A; CORRECT FIRST.
- **Reversibility after implementation:** **EASY**—internal ordering.
- **Contradicts a Ray ruling?** No; the contradiction is internal.

### 17-R7.3: Bypass outer mise for protected execution

- **Chosen:** Task is convenience; direct uv is protected entrypoint. S17:29; :267–268; :299–304.
- **Alternatives:** A—direct uv. **PRO:** bypasses motivating outer-mise load. **CON:** longer invocation. S17:267. B—task alone. **PRO:** familiar entrypoint. **CON:** outer mise can install first. `T/test_process_env.py:220–228`.
- **Recommendation:** A for contamination-sensitive work.
- **Reversibility after implementation:** **EASY**—both forms coexist.
- **Contradicts a Ray ruling?** No.

### 17-R7.4: Parse configuration listings as JSON

- **Chosen:** Use `mise config ls --json`. S17:30; :325–328.
- **Alternatives:** A—JSON path sets. **PRO:** avoids truncated/abbreviated display. **CON:** output-shape dependency. V17:45. B—human table. **PRO:** simple inspection. **CON:** display bounds hide target configuration. V17:74; `.claude/rules/probes-need-a-control-arm.md:66–76`.
- **Recommendation:** A with own-config controls.
- **Reversibility after implementation:** **EASY**—test implementation.
- **Contradicts a Ray ruling?** No.

### 17-R7.5: Bound discovery and clean up process groups

- **Chosen:** TERM, grace, group KILL, reap, bounded grandchild poll. S17:31; :173–182; :365.
- **Alternatives:** A—group cleanup plus bounded discovery. **PRO:** covers descendants and pre-spawn hangs. **CON:** deadline accounting correction. `P/process_env.py:76–83`; `.claude/rules/long-running-command-hangs.md:3–5`. B—conditional cleanup copy. **PRO:** familiar code. **CON:** resistant descendants can survive leader exit. `P/lint.py:213–223`.
- **Recommendation:** A; CORRECT FIRST.
- **Reversibility after implementation:** **MODERATE**—deadline/rc semantics.
- **Contradicts a Ray ruling?** No.

### 17-R7.6: Add runtime and XDG leakage controls

- **Chosen:** Runtime-env mutation and fake-XDG global fixture. S17:32; :339; :351–355; :389.
- **Alternatives:** A—both behavioral fixtures. **PRO:** checks actual discovery routes. **CON:** more real-mise cases. S17:360–363. B—literal environment test only. **PRO:** fast. **CON:** does not establish discovery behavior. `.claude/rules/real-integration-evidence.md:3–10`.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—supplemental tests.
- **Contradicts a Ray ruling?** No.

### 17-R7.7: Define dropped names as removal history

- **Chosen:** Include inherited names later reset; lists may overlap. S17:33; :202–208.
- **Alternatives:** A—removal history. **PRO:** records rejected inherited values. **CON:** overlap needs explanation. S17:206. B—final absent names. **PRO:** simple child comparison. **CON:** hides replacement of inherited paths. S17:371.
- **Recommendation:** A, names only; precedent `P/child_env.py:95–98`.
- **Reversibility after implementation:** **MODERATE**—result meaning.
- **Contradicts a Ray ruling?** No.

### 17-R7.8a: Preserve child_command parser destination

- **Chosen:** Shared argparse destination. S17:34; :228–231.
- **Alternatives:** A—shared destination. **PRO:** fits normalization. **CON:** parser coupling. `P/main.py:1721`; :2441. B—individual destinations. **PRO:** independent evolution. **CON:** requires normalization relocation. `P/main.py:2438–2448`.
- **Recommendation:** A for additive implementation.
- **Reversibility after implementation:** **EASY**—internal attribute.
- **Contradicts a Ray ruling?** No.

### 17-R7.8b: Return typed refusals

- **Chosen:** rc 2 with closed discovery/separator reasons; preserve Git behavior. S17:34; :238–248; :270.
- **Alternatives:** A—specific refusal. **PRO:** distinguishes invalid input/discovery failure. **CON:** shared-path branching. `P/main.py:2441–2444`. B—generic failure. **PRO:** minimal change. **CON:** violates refusal grammar. V0417:105–106.
- **Recommendation:** A including rev-2.1 correction.
- **Reversibility after implementation:** **MODERATE**—automation depends on reasons.
- **Contradicts a Ray ruling?** No.

### 17-R7.9: Prevent sensitive assertion diagnostics

- **Chosen:** Drain capture; assert controlled fields/names. S17:35; :279–282; :364.
- **Alternatives:** A—parsed assertions. **PRO:** limits failure disclosure. **CON:** assertion discipline. S17:364. B—raw environment dictionaries. **PRO:** convenient diagnostics. **CON:** exposes values on failure. S17:279–282.
- **Recommendation:** A; inherited production stdio is separate, S17:170–171.
- **Reversibility after implementation:** **EASY**—test hygiene.
- **Contradicts a Ray ruling?** No; consistent with Ledger:224.

### 17-R7.10: Verify settings precedence with the real binary

- **Chosen:** Precedence remains assumed until V11. S17:36; :309–311; :374.
- **Alternatives:** A—require V11. **PRO:** tests installed behavior. **CON:** completion remains unverified meanwhile. S17:374. B—documentation alone. **PRO:** fewer probes. **CON:** does not establish this fixture’s precedence. [Mise auto-install settings](https://mise.jdx.dev/configuration/settings.html#auto_install).
- **Recommendation:** A; escalate contrary behavior.
- **Reversibility after implementation:** **EASY**—verification condition.
- **Contradicts a Ray ruling?** No.

### 19-D1: Implement native regex rules

- **Chosen:** Native `hook_guard`; reject direct KB reuse for compatibility/administration gaps. S19:516–527.
- **Alternatives:** A—reuse directly. **PRO:** shared maintenance. **CON:** permits administration and rejects sanctioned redirected probes. `python/.venv/lib/python3.14/site-packages/kb_setup/secret_guard.py:189/:266`. B—repair KB first. **PRO:** one implementation. **CON:** delays protection and affects pinned dependency. `python/pyproject.toml:40`.
- **Recommendation:** Native rules; observed gaps justify separate implementation.
- **Reversibility after implementation:** **MODERATE**—consolidation must preserve safe forms and audit identities.
- **Contradicts a Ray ruling?** No.

### 19-D2: Restrict enforcement to verified Doppler administration

- **Chosen:** Deny verified set/delete/upload/token creation and aliases. S19:528–529.
- **Alternatives:** A—broaden all credential CLIs. **PRO:** wider ownership enforcement. **CON:** more verified inventories needed. Ledger:224. B—allow quiet administration. **PRO:** automation convenience. **CON:** violates Ray-only administration regardless of output. Ledger:224.
- **Recommendation:** Retain narrow enforcement; uncovered administration remains prohibited.
- **Reversibility after implementation:** **EASY**—rules can be added with audits, `.claude/rules/mise-tasks-only.md:97`.
- **Contradicts a Ray ruling?** No; alternative B would.

### 19-D3: Defer broader environment-dump enforcement

- **Chosen:** Defer dumps outside Doppler; include probe-confirmed Doppler dump forms. S19:530–531.
- **Alternatives:** A—deny bare dumps now. **PRO:** covers known disclosure routes. **CON:** must distinguish legitimate env consumers. `python/.venv/lib/python3.14/site-packages/kb_setup/secret_guard.py:185`. B—ban all printenv. **PRO:** simple matching. **CON:** breaks sanctioned redirected presence probes. `T/test_hook_guard.py:1086`.
- **Recommendation:** Retain temporary scope with explicit residual and owner.
- **Reversibility after implementation:** **EASY**—additive narrow rules.
- **Contradicts a Ray ruling?** No.

### 19-D4: Make conditional sources consistent

- **Chosen:** Environment plus probe-confirmed Doppler names; otherwise environment only. S19:532–534.
- **Alternatives:** A—environment only. **PRO:** no provider subprocess. **CON:** observes received environment rather than backend records. `.claude/rules/secrets-out-of-the-shell-env.md:67`. B—require Doppler before landing. **PRO:** consistent interface. **CON:** blocks useful environment probing on unconfirmed shape. S19:772–783.
- **Recommendation:** Retain conditional sources after correcting fallback CLI, guide and tests.
- **Reversibility after implementation:** **MODERATE**—callers depend on source semantics.
- **Contradicts a Ray ruling?** No.

### 19-D5: Place presence probing under process

- **Chosen:** Process subcommand plus thin mise task. S19:535–536.
- **Alternatives:** A—top-level command. **PRO:** shorter invocation. **CON:** duplicates process grouping. `P/main.py:1706`. B—secrets module/group. **PRO:** future tooling separation. **CON:** another ownership seam without demonstrated need. `P/process_env.py:2`.
- **Recommendation:** Retain process placement; dispatch before separator parsing.
- **Reversibility after implementation:** **EASY**—stable task can hide CLI aliases.
- **Contradicts a Ray ruling?** No.

### 19-D6: Correct eager instructions without growth

- **Chosen:** Omit inventory row; neutral-size replacement; leave other wording stale. S19:537–542.
- **Alternatives:** A—replace existing inventory/stale sentences within budget. **PRO:** current, consistent instructions. **CON:** careful compression. `.claude/rules/mise-tasks-only.md:89`. B—evidence-only correction with explicit exception. **PRO:** preserves budget. **CON:** eager readers still receive false claims. `.claude/rules/secrets-out-of-the-shell-env.md:90`.
- **Recommendation:** A; do not retain knowingly false instructions.
- **Reversibility after implementation:** **MODERATE**—instructions propagate into behavior.
- **Contradicts a Ray ruling?** No.

### 19-D7: Require explicit project and configuration

- **Chosen:** Both Doppler scope flags required. S19:543–544.
- **Alternatives:** A—ambient scope. **PRO:** convenient. **CON:** ambiguous presence result. `docs/secrets-doppler-fnox-keychain.md:358`. B—dotfiles/dev_personal default. **PRO:** concise. **CON:** embeds local configuration in reusable interface. `docs/secrets-doppler-fnox-keychain.md:107`.
- **Recommendation:** Retain explicit flags.
- **Reversibility after implementation:** **EASY**—defaults can be added compatibly.
- **Contradicts a Ray ruling?** No.

### 19-D8: Correct the guide alongside enforcement

- **Chosen:** Target enforcement, names-only verification and Ray-only rollback wording. S19:545–546.
- **Alternatives:** A—remove unsafe recipe. **PRO:** removes misleading advice. **CON:** incomplete procedure. `docs/secrets-doppler-fnox-keychain.md:373`. B—rewrite whole guide. **PRO:** broader consistency. **CON:** expands security-change scope. `docs/secrets-doppler-fnox-keychain.md:307`.
- **Recommendation:** Retain targeted corrections, conditional on D4’s shipped interface.
- **Reversibility after implementation:** **EASY**—documentation only.
- **Contradicts a Ray ruling?** No.

### 19-D9: Resolve permission defense before hard-boundary claims

- **Chosen:** Defer permission denies. S19:547.
- **Alternatives:** A—companion denies for verified unsafe forms. **PRO:** covers hook-error bypass. **CON:** native denies lack custom redirects. `P/hook_guard.py:878`. B—explicitly accept redirect-only enforcement. **PRO:** existing architecture. **CON:** retains fail-open exposure. `P/hook_dispatch.py:24–25`.
- **Recommendation:** A, preserving safe consumers/probes and verifying permission behavior.
- **Reversibility after implementation:** **HARD**—later configuration cannot retract leaked transcripts; prior rotation precedent at `.claude/rules/secrets-out-of-the-shell-env.md:74`.
- **Contradicts a Ray ruling?** No.

### 19-D10: Track KB parity separately

- **Chosen:** Caller-owned KB follow-up; no KB edits here. S19:548–552.
- **Alternatives:** A—synchronize both before landing. **PRO:** immediate parity. **CON:** couples repositories/dependency updates. `python/pyproject.toml:40`. B—local evidence only. **PRO:** minimal coordination. **CON:** upstream gaps lack ownership. `knowledge-base/python/src/kb_setup/secret_guard.py:266`.
- **Recommendation:** Retain a separately owned issue; recheck state before citing it.
- **Reversibility after implementation:** **EASY**—issue scope is editable.
- **Contradicts a Ray ruling?** No.

### 20-D1: Require repository-relative paths

- **Chosen:** Exact repository paths; nonexistent root-basename shorthand fails. S20:28; :252.
- **Alternatives:** A—exact paths. **PRO:** unambiguous blob lookup. **CON:** legacy shorthand needs rewriting. `P/handoff_check.py:211`; S20:378. B—unique-basename resolution. **PRO:** accepts shorthand. **CON:** guesses intent and changes with files. S20:382.
- **Recommendation:** A for machine PREMISES format.
- **Reversibility after implementation:** **MODERATE**—authored grammar changes.
- **Contradicts a Ray ruling?** No.

### 20-D2: Require both range-boundary anchors

- **Chosen:** Two anchors for multiline citations. S20:29–30.
- **Alternatives:** A—boundary anchors. **PRO:** detects shifted/widened ranges. **CON:** author work. S20:385. B—one containment anchor. **PRO:** simpler rows. **CON:** can fit correct and incorrect ranges. `P/handoff_check.py:225`; S20:388.
- **Recommendation:** A.
- **Reversibility after implementation:** **MODERATE**—stored rows adopt grammar.
- **Contradicts a Ray ruling?** No.

### 20-D3: Use one citation per machine row

- **Chosen:** Split multisite premises into rows. S20:31; :392.
- **Alternatives:** A—one citation. **PRO:** unambiguous pairing. **CON:** longer tables. S20:393. B—positional lists. **PRO:** compact. **CON:** parsing/pairing failure modes. S20:395.
- **Recommendation:** A; linked rows may support one semantic claim.
- **Reversibility after implementation:** **MODERATE**—parser and format evolve together.
- **Contradicts a Ray ruling?** No.

### 20-D4: Require explicit spec and revision

- **Chosen:** `spec-premises SPEC --revision REV [--json]`. S20:32–33; :396.
- **Alternatives:** A—explicit inputs. **PRO:** reproducible identity. **CON:** longer invocation. S20:315. B—inference. **PRO:** convenience. **CON:** wrong artifact/source risk. `P/handoff_check.py:716`; S20:398.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—wrappers can supply explicit values.
- **Contradicts a Ray ruling?** No.

### 20-D5: Permit targeted implementer tests

- **Chosen:** One handoff-check test file. S20:34–35; :400.
- **Alternatives:** A—targeted tests. **PRO:** finds local defects before caller gates. **CON:** not whole-repository assurance. `tests/AGENTS.md:39`. B—zero lane tests. **PRO:** lower load. **CON:** caller discovers avoidable defects. Ledger:241.
- **Recommendation:** A with full caller gates retained.
- **Reversibility after implementation:** **EASY**—check allocation.
- **Contradicts a Ray ruling?** No.

### 20-R6: Defer legacy line-count correction

- **Chosen:** Separate ticket for existing `splitlines()` behavior. S20:36–37.
- **Alternatives:** A—defer. **PRO:** preserves compatibility. **CON:** two numbering semantics. `P/handoff_check.py:225`; S20:331. B—correct both. **PRO:** consistency. **CON:** changes old callers and exceeds scope. S20:289.
- **Recommendation:** A with an owner.
- **Reversibility after implementation:** **MODERATE**—legacy verdict dependencies.
- **Contradicts a Ray ruling?** No.

### 20-R7: Read revision blobs as bytes

- **Chosen:** Explicit UTF-8 decode and newline handling. S20:41–44; :314.
- **Alternatives:** A—bytes. **PRO:** preserves line numbering/anchors. **CON:** explicit decoding. S20:264. B—text mode. **PRO:** fewer steps. **CON:** universal newlines alters carriage returns. S20:321.
- **Recommendation:** A.
- **Reversibility after implementation:** **MODERATE**—line semantics affect verdicts.
- **Contradicts a Ray ruling?** No.

### 20-R8: Replace filler in the form-feed mutation

- **Chosen:** Replace a line rather than insert one. S20:45–46.
- **Alternatives:** A—replacement. **PRO:** isolates splitting without shifting ranges. **CON:** controlled fixture. S20:46. B—insertion and updated ranges. **PRO:** tests movement too. **CON:** mixes causes. `premise-verifier-process-hardening-01-03-20.md:181`.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—fixture only.
- **Contradicts a Ray ruling?** No.

### 20-R9: Report unclosed fences

- **Chosen:** Structural finding, rc 1. S20:47–48.
- **Alternatives:** A—explicit finding. **PRO:** malformed fences cannot silently hide premises. **CON:** may accompany missing-premises. `P/handoff_check.py:308`; S20:240. B—blank remaining content. **PRO:** simpler parsing. **CON:** conceals cause. `P/handoff_check.py:307`.
- **Recommendation:** A.
- **Reversibility after implementation:** **EASY**—additive finding.
- **Contradicts a Ray ruling?** No.

### 20-R10: Verify inputs at the dispatch revision

- **Chosen:** Check tracked cited inputs before self-run. S20:49–51.
- **Alternatives:** A—explicit precondition. **PRO:** separates custody from checker defects. **CON:** caller preparation. S20:50. B—let self-run discover missing blobs. **PRO:** fewer steps. **CON:** confounds uncommitted evidence with citation defects. S20:316.
- **Recommendation:** A using revision-qualified existence checks; current-index tracking alone is insufficient.
- **Reversibility after implementation:** **EASY**—caller procedure.
- **Contradicts a Ray ruling?** No.

The dispatch column below follows the review spec’s supplied status; it is not a claim of delivery.

| Decision id | Recommendation | Reversibility | Spec already dispatched? |
|---|---|---|---|
| 01-U1 | Preserve request direction; document exception | MODERATE | yes |
| 01-U2 | Separate bound runs | MODERATE | yes |
| 01-U3 | Add source-tree binding | MODERATE | yes |
| 01-U4 | Total threads, including dispatcher | MODERATE | yes |
| 01-U5 | Correct ownership to item 29 | MODERATE | yes |
| 01-EAGER | Skill plus generated prompt | EASY | yes |
| 01-ASSERTIONS | Complete refusal assertion | EASY | yes |
| 01-ISOLATION | Isolate mutation launch paths | EASY | yes |
| 01-SEAM | Explicit HEAD callable | EASY | yes |
| 02-D1 | Generate enums; preserve settlement | MODERATE | no |
| 02-D2 | Require both receipts | MODERATE | no |
| 02-D3 | Recovery-only publication proposal | HARD | no |
| 02-D4 | Separate content/coverage axis | MODERATE | no |
| 02-PATH | Exact payload strings | EASY | no |
| 02-ENUM | Explicit generated member names | MODERATE | no |
| 02-CHILD-RC | Fixture rc override | EASY | no |
| 02-GUARD | Preserve timeout during downgrade | MODERATE | no |
| 02-ORDER | Serialize shared-file edits | EASY | no |
| 02-PROVENANCE | Confirmed direct evidence | EASY | no |
| 03-U-1 | Add generated receipts | MODERATE | yes |
| 03-U-2 | Temporary-index tree identity | HARD | yes |
| 03-U-3 | Distinct rc 3; correct unknown contract | MODERATE | yes |
| 03-U-4 | Neutral-size authorization update | MODERATE | yes |
| 03-U-5 | Start/end capture | MODERATE | yes |
| 03-EXCLUSION | Explicit artifact exclusion | MODERATE | yes |
| 03-ENV | Bound and contain probe failures | MODERATE | yes |
| 03-TIMEOUT-RECEIPT | Terminal admission-timeout receipt | EASY | yes |
| 03-TEST-PATH | Prepend controlled executables | EASY | yes |
| 03-MUTATING-GATES | Read-only authorization checks | MODERATE | yes |
| 03-WAIT-BOUND | Bounded fixture synchronization | EASY | yes |
| 04-SCOPE | Three library resources; CPU CLI | HARD | yes |
| 04-CLI | Resource CLI plus receipts | MODERATE | yes |
| 04-LABEL | Truncate all labels | EASY | yes |
| 04-WAIT | Refuse invalid waits | EASY | yes |
| 04-KEYS | Normalize keys | EASY | yes |
| 04-VALIDATION | Validate before acquisition | MODERATE | yes |
| 04-MODEL | Required-nullable generated model | MODERATE | yes |
| 04-PUBLICATION | Publish before launch | MODERATE | yes |
| 04-ARGPARSE | Parser refusal without receipt | EASY | yes |
| 04-LAUNCH | Popen plus wait | MODERATE | yes |
| 04-LIFETIME | Close or ratify race before delivery | HARD | yes |
| 04-HOLDER | Stripped-record equality | EASY | yes |
| 04-SIDECARS | Exact final sidecar only | EASY | yes |
| 04-CONTRACTS | Suite plus behavioral fail arms | EASY | yes |
| 04-PROVENANCE | Branch-qualified evidence | EASY | yes |
| 04-TEST-SURFACES | Interface-aligned tests | EASY | yes |
| 04-BUSY | Lease-only flock observation | MODERATE | yes |
| 04-FREE | Explicit free/held/error mapping | MODERATE | yes |
| 04-ARGV | Container argv matcher | MODERATE | yes |
| 04-SPLIT | Gate replacement task on smoke custody | MODERATE | yes |
| 04-FAIL-ARMS | Armed isolated fixtures | EASY | yes |
| 17-U1/R1 | Expanded isolation inputs | MODERATE | yes |
| 17-U2/R2 | Disposable-directory trust | EASY | yes |
| 17-U3/R3 | Optional atomic typed result | MODERATE | yes |
| 17-U4/R4 | Owned companion adoption | EASY | yes |
| 17-U5/R5 | Preserve PATH; narrow guarantee | MODERATE | yes |
| 17-R6/R7.11 | Correct authored evidence | EASY | yes |
| 17-R7.1 | Correct HOME rationale | EASY | yes |
| 17-R7.2 | Correct creation/resolution order | EASY | yes |
| 17-R7.3 | Direct protected entrypoint | EASY | yes |
| 17-R7.4 | JSON configuration path sets | EASY | yes |
| 17-R7.5 | Bound discovery; group cleanup | MODERATE | yes |
| 17-R7.6 | Runtime and XDG controls | EASY | yes |
| 17-R7.7 | Removal-history names | MODERATE | yes |
| 17-R7.8a | Shared parser destination | EASY | yes |
| 17-R7.8b | Typed refusals | MODERATE | yes |
| 17-R7.9 | Controlled diagnostics | EASY | yes |
| 17-R7.10 | Real-binary precedence probe | EASY | yes |
| 19-D1 | Native regex rules | MODERATE | no |
| 19-D2 | Verified administration forms | EASY | no |
| 19-D3 | Explicit temporary dump residual | EASY | no |
| 19-D4 | Correct conditional-source contract | MODERATE | no |
| 19-D5 | Process CLI and thin task | EASY | no |
| 19-D6 | Current wording through replacements | MODERATE | no |
| 19-D7 | Explicit project/configuration | EASY | no |
| 19-D8 | Targeted, fallback-aware guide | EASY | no |
| 19-D9 | Companion permission defenses | HARD | no |
| 19-D10 | Separate owned KB issue | EASY | no |
| 20-D1 | Exact repository paths | MODERATE | no |
| 20-D2 | Two boundary anchors | MODERATE | no |
| 20-D3 | One citation per machine row | MODERATE | no |
| 20-D4 | Explicit spec and revision | EASY | no |
| 20-D5 | Targeted lane tests | EASY | no |
| 20-R6 | Owned legacy correction | MODERATE | no |
| 20-R7 | Byte-preserving blob reads | MODERATE | no |
| 20-R8 | Isolated replacement mutation | EASY | no |
| 20-R9 | Explicit fence finding | EASY | no |
| 20-R10 | Revision-qualified input check | EASY | no |

**HOLD candidates**

- **02 — D3:** repair publication without automatically repeating successful child effects.
- **04 — LIFETIME:** close or explicitly ratify the release-under-live-child window before claiming the lease guarantee.
- **19 — D9:** resolve companion permission defenses before claiming a hard secret-output boundary.

These are proposed HOLDs, not actions taken against dispatched lanes. The licensed-dissent corrections listed above apply independently of the HARD/differing-recommendation criterion.

**Research execution receipt**

The dispatcher ran research through native `fnox` with `codex_research`, `--no-defaults --no-daemon --non-interactive`, followed by mise-managed tools. Secrets were neither printed nor persisted.

| Route | Observed result |
|---|---|
| Exa HTTPS API | HTTP 200; five results, including primary mise docs/source |
| Firecrawl CLI search | rc 1; HTTP 402 |
| Context7 `ctx7 docs /jdx/mise` | rc 0; documentation/source references returned |
| Last30Days plugin script 3.26.0 | rc 1; planned sources unavailable under effective configuration; no retrieval started |
| GitHub code search | rc 0; query 18 hits, must-hit 21, fresh known-absent 0 |
| GitHub issues/PRs and discussion metadata | Successful reads for mise, Codex, Doppler CLI, fnox, AWS CLI and CPython; disabled discussions recorded as metadata |
| GitHub latest-release endpoints | AWS CLI and CPython returned rc 1/HTTP 404; other queried endpoints answered |
| Primary source rereads | Raw mise directory documentation HTTP 200; config specialist’s official documentation reads succeeded |

This is **partial provider coverage**, not a successful five-provider audit. Last30Days’ failure does not establish missing user credentials; Exa answered successfully in the same injected research environment. Search results were used for discovery; recommendations rely on inspected specs, current code, dependency source and primary documentation.

No connector apps ran. The dispatcher used the `codex-sdlc-team` skill and consulted research-sweep/Context7 guidance. Firecrawl and Context7 ran as CLIs; Last30Days ran its installed plugin script. Specialists used read-only shell/Git searches; the config specialist additionally used official-documentation browsing and bounded `fnox`/`curl`. Exploratory missing-path reads were recorded as rc 1/2 or Git rc 128 and were not treated as evidence of absence.

No others were spawned.

**Specialists spawned:**

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/documentation_review`