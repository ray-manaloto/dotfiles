# #601 — the seven codex adversarial review rounds, verbatim

**Persisted at clear-prep 2026-08-06** per `.claude/rules/agent-report-persistence.md`.
These reports existed ONLY in the session scratchpad, which is ephemeral — one
`/clear` from being lost. They are the corpus for the self-reflection pass.

Reviewer: `codex-cli 0.146.0`, `--sandbox read-only`,
`model_reasoning_effort=high`, file-captured output. Every round was told to
treat the implementer's gate results as CLAIMS, not evidence.

| Round | Verdict | Findings | Shape of what it found |
|---|---|---|---|
| v1 | DO NOT SHIP | 2 HIGH · 1 LOW | log wording overclaimed; contract engine |
| v2 | SHIP | 2 LOW | test control arm; doc accuracy |
| v3 | SHIP | 1 LOW | test control arm (again) |
| v4 | DO NOT SHIP | 1 HIGH | **real bug** — classify→execute race |
| v5 | DO NOT SHIP | 3 HIGH | **real bug** — queued-reply deadlock; residual race; execute_stop (→ #604) |
| v6 | DO NOT SHIP | 1 HIGH · 1 LOW | **real bug** — live-pid queued reply silent; TOCTOU traded |
| v7 | DO NOT SHIP | 2 MEDIUM | **bounded brief** — missing 5th axis (`tempo`); weak meta-tests |

⚠️ **v7 used a deliberately different brief shape** — three bounded questions
with an explicit stop condition, instead of open-ended "find what is broken".
It found an *axis* rather than another *cell*, in one pass. That contrast is
the single most important datum in this corpus.


---

## Round v1 — report, verbatim

### [HIGH] Required tracker projection is missing
- **Where:** [docs/receipts/575.md:3](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:3), [docs/receipts/575.md:17](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:17), [dag_tick.py:153](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:153), [dag_tick.py:159](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:159), [suites.toml:1255](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1255)
- **What:** The ground-truth receipt requires NEEDS_HUMAN to “log, project, label and never respawn,” with the scheduler writing an append-only tracker comment. This branch explicitly admits that no component or open ticket owns that projection and implements only a log line. Deferring label spelling and comment format at [docs/receipts/575.md:150](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:150) does not defer the projection itself. Worse, the emitted reason says `project + label dag:needs-human` even though neither action occurs at [dag_tick.py:491](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:491).
- **Why it matters:** The selector reads labels and terminal reasons belong in append-only comments at [docs/receipts/575.md:46](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:46). Consequently, GitHub remains unaware of the escalation, no human-facing projection is created, and the required evidence validation at projection time never runs.
- **Verified by:** reading the cited source and receipt lines.

### [HIGH] “Never auto-respawned” closes only one respawner
- **Where:** [dag_tick.py:430](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:430), [dag_tick.py:521](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:521), [dag_tick.py:949](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:949), [docs/receipts/565.md:18](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/565.md:18), [docs/receipts/565.md:53](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/565.md:53), [docs/receipts/575.md:136](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:136)
- **What:** This patch prevents only `dag_tick` from issuing `claude respawn`; its LOG action performs no live operation. Receipt #565 records that the native supervisor’s respawn predicate considers terminal state, tempo, and `queuedPrompt`—not `needs`—and that `blocked` is non-terminal. Thus the native supervisor path remains outside this fix while the log claims the node is “never auto-respawned.”
- **Why it matters:** If the native supervisor remains alive when a `blocked + needs` worker dies, it can respawn the worker before the 60-second launchd tick observes it, reproducing the idle-with-no-prompt loss this patch claims to eliminate.
- **Verified by:** reading the cited code and binary-derived receipt. **UNVERIFIED:** the exact live `blocked + needs` native-respawn arm was not probed; receipt #575 explicitly marks that route unverified.

### [LOW] The wiring contract still accepts commented-out wiring
- **Where:** [suites.toml:1266](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1266), [verify.py:483](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/verify.py:483), [token_audit.py:241](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/token_audit.py:241), [dag_tick.py:249](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:249)
- **What:** `per_path_tokens` performs unanchored substring membership, while `token_audit` only requires exactly one textual occurrence. Neither verifies syntax or strips comments. Commenting out `needs=normalize_needs(data.get("needs")),` while retaining those bytes would leave the contract and uniqueness audit green; `Node.needs` would then default to `None`.
- **Why it matters:** The contract specifically claims to bind actual wiring, but that mutation makes the feature inert while this contract remains green. The behavioral pytest suite should still catch it, so this is defense-in-depth rather than an independent production failure.
- **Verified by:** reading the handlers and reasoning through the comment-only mutation.

Severity count: **HIGH 2 · MEDIUM 0 · LOW 1**

Verdict: **DO NOT SHIP**

Receipts — verified by reading source:

- Opened all five changed files in full, including `tests/AGENTS.md` and `tests/TEST-INDEX.md`, which the brief’s list omitted.
- Opened `verify.py`, `token_audit.py`, and receipts 565/575/578 in full.
- Plain `blocked` without `needs` retains the old DEAD/WEDGED/ALIVE path at [dag_tick.py:430](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:430) and [dag_tick.py:807](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:807).
- The new negative assertions use real emitted strings: `stale beyond --max-age` at [dag_tick.py:478](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:478), `RESPAWN` at [dag_tick.py:903](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:903), and `ALSO stalled` at [dag_tick.py:834](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:834); those checks are not spelling-vacuous.
- Current tree receipts: focused pure tests **48 passed**; verification **115 passed, 0 failed, 4 policy skips**; token audit reported **0 violations**; `git diff --check` passed; worktree remained clean at `42e7c9c`.

Receipts — reasoning alone / UNVERIFIED:

- The native-supervisor race above follows from the documented predicate, but the exact NEEDS_HUMAN live arm remains **UNVERIFIED**.
- The comment-only contract mutation was reasoned from the handlers, not executed because the workspace is read-only.
- GitHub issue #601 was **UNVERIFIED** because `gh issue view` could not reach `api.github.com`.
- The commit’s mutation failure counts, lint result, and full pytest count were **UNVERIFIED**. Full pytest could not start because the sandbox exposes no writable temporary directory.


---

## Round v2 — report, verbatim

## v1 → v2 disposition

| v1 finding | Disposition | Settling line |
|---|---|---|
| Required tracker projection missing | PARTIALLY CLOSED | The log now truthfully says projection is absent at [dag_tick.py:516](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:516), but the implementation remains log-only at [dag_tick.py:544](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:544). |
| Global “never auto-respawned” claim | CLOSED | The reason is explicitly scoped to this tick and names the separate supervisor route at [dag_tick.py:514](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:514). |
| Commented-out wiring accepted | OPEN | `per_path_tokens` remains unanchored substring membership at [verify.py:483](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/verify.py:483). This is the accepted engine-wide LOW, not a round-2 regression. |

### [LOW] The new explanation misstates receipt #575’s deferral

- **Where:** [dag_tick.py:164](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:164), [suites.toml:1255](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1255), [575.md:5](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:5), [575.md:150](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:150)
- **What:** The new comment and contract say #575 deferred the projection “OWNER.” The receipt instead explicitly assigns projection to the scheduler. Its deferred list names the general `dag:*` label spellings, comment format, and evidence contract; the parenthetical separately says the later #573 receipt settles this specific `dag:needs-human` spelling.
- **Why it matters:** The correction embeds contradictory ownership history directly beside the single-writer rationale. Future work should read: scheduler ownership and projection are settled; implementation is pending; this particular label is settled by #573.
- **Verified by:** direct comparison with the cited receipt lines. The TOML entry parses successfully.

### [LOW] The projection wording regression test is not semantically control-armed

- **Where:** [test_dag_tick.py:558](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:558)
- **What:** The respawn half is adequately pinned by the preceding exact assertion at [test_dag_tick.py:536](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:536). The projection half is weaker: `"is NOT done here"` is not tied to tracker projection, while the negative assertion forbids only the exact old phrase. This misleading string satisfies every new wording assertion: `never respawned BY THIS TICK; tracker projection to dag:needs-human IS done here; cleanup is NOT done here`.
- **Why it matters:** A synonym of the projection overclaim can return while the test and the static contract remain green, contrary to the description’s claim that a tidy-up cannot restore it.
- **Verified by:** evaluating that counterexample against all six relevant assertions; all returned true.

Severity count: **HIGH 0 · MEDIUM 0 · LOW 3** — two round-2 LOW findings plus the accepted v1 engine-wide LOW.

Verdict: **SHIP** for #601. The runtime reason is now accurate, its action remains LOG-only, and no new behavioral defect was found. The two new findings are documentation/test-hardening issues; projection remains an explicit follow-up dependency.

Receipts — source-verified:

- Current branch is `fix/601-dag-tick-needs-human`, clean at `cf6e97dc89af23cc203574936ae84a13030d4164`.
- Read the v1 report first, then inspected `cf6e97d`, the complete current `dag_tick.py` and `test_dag_tick.py`, all changed supporting files, `verify.py`, `token_audit.py`, and receipts 565/575/578.
- `workflow.dag-tick-wiring` parsed and executed successfully; all 37 per-path tokens currently match exactly once.
- Focused pure tests: **13 passed**.
- Both `git diff --check` checks passed.
- Plain `blocked` without `needs` still reaches DEAD → RESPAWN at [dag_tick.py:434](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:434).
- The current negative spellings match emitted text, and `is_stalled(None)` remains opposite to `_is_stale_dead(None)`.

Receipts — reasoned-alone / UNVERIFIED:

- The claimed existence, sub-issue relationship, and ownership state of GitHub issue #602 are **UNVERIFIED**. No finding or SHIP decision depends on that tracker claim being confirmed.
- Whether the harness supervisor actually fires for the exact `blocked + needs` live shape remains **UNVERIFIED**; the corrected string accurately describes it only as a separate route this module cannot close.

Memory was used only to orient the scheduler boundary; all verdict claims were reverified against the current tree.


---

## Round v3 — report, verbatim

## v2 → v3 disposition

| v2 finding | Disposition | Settling line |
|---|---|---|
| Receipt-deferral correction | CLOSED | The three-part account at [dag_tick.py:164](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:164) now matches #575’s scheduler ownership and specific-label precedence, while preserving its genuinely deferred items. |
| Wording-test control arm | PARTIALLY CLOSED | The stored v2 counterexample is rejected, but `_reason_is_honest` still accepts a new contradictory string because it constrains required substrings, not surrounding meaning. |

### [LOW] The honesty predicate remains semantically bypassable

- **Where:** [test_dag_tick.py:539](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:539), [test_dag_tick.py:565](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:565), [suites.toml:1255](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1255)
- **What:** This new misleading reason satisfies every condition:

  > `never respawned BY THIS TICK; tracker projection to dag:needs-human is NOT done here; it is performed later in this same tick`

  It contains both contiguous required clauses, mentions `dag:needs-human` exactly once, and contains neither forbidden phrase. Executing the predicate extracted from the current AST returned `True`.
- **Why it matters:** The test still permits the tracker-projection overclaim it is meant to reject, provided the contradiction does not repeat the label literal. Therefore the suite description’s claim that the overclaim cannot return remains too strong.
- **Verified by:** source introspection of the exact predicate and execution against the quoted string. The real emitted reason returned `True`; the stored v2 counterexample returned `False`; this new counterexample returned `True`. An honest paraphrase also returned `False`, showing that the predicate is an exact-template guard, not a semantic classifier.

The control arms are real for those two fixed inputs, so the predicate is neither universally true nor universally false. They do not establish general discrimination. Extracting it did not weaken the old assertions: the new contiguous clauses imply both old positive fragments, and both old forbidden-phrase checks remain explicitly asserted at [test_dag_tick.py:608](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:608).

The three-part receipt correction is accurate:

- #575 assigns projection to the scheduler at [575.md:3](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:3).
- #575 explicitly says the later #573 receipt governs this specific spelling and defers the general spellings, comment format, and “evidence contract each stage’s brief renders” at [575.md:150](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:150).
- #573 uses `dag:needs-human` in its verdict at [573.md:19](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/573.md:19), while its general label/evidence taxonomy remains deferred at [573.md:117](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/573.md:117).

Severity count: **HIGH 0 · MEDIUM 0 · LOW 1**

Verdict: **SHIP**. The actual production reason is accurate; the remaining defect is test/contract hardening.

Receipts — source-verified:

- Read the v1 report and then the v2 report before reviewing.
- Branch is `fix/601-dag-tick-needs-human`, clean at `b9214adc9ee60defd43e831732605b04270f8e76`.
- Ran all three Git commands prescribed by the brief and inspected every `b9214ad` hunk.
- Python source introspection opened the actual `_needs_human_reason`; AST introspection executed the exact current `_reason_is_honest`.
- `suites.toml` parses successfully with stdlib `tomllib`.
- All **37** `workflow.dag-tick-wiring` per-path tokens match exactly once.
- `git diff --check origin/main...HEAD` passed.
- Cross-round coverage has no unread branch file: v1 records all five changed files read in full; v2 records the then-current source, tests, and supporting files; v3 covered all three files changed by `b9214ad`.

Receipts — reasoned-alone / **UNVERIFIED**:

- `mise run lint`, `mise run lint-docs`, the full pytest result, and the complete verification result remain **UNVERIFIED** here. Focused execution was attempted but `uv` could not initialize its cache in the read-only sandbox; this is not a finding.
- GitHub issue #602’s existence and sub-issue relationship remain **UNVERIFIED**.
- Whether the harness supervisor fires for the exact live `blocked + needs` shape remains **UNVERIFIED**.


---

## Round v4 — report, verbatim

| v3 finding | Disposition | Settling line |
|---|---|---|
| Honesty predicate remains semantically bypassable | **CLOSED as the guard** | Golden equality at [test_dag_tick.py:650](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:650) now detects every textual change. The predicate remains only a deliberately limited diagnostic at [test_dag_tick.py:664](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:664). |

### [HIGH] The golden’s “never respawned BY THIS TICK” clause is false across the classify→execute window

- **Where:** [dag_tick.py:439](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:439), [dag_tick.py:551](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:551), [dag_tick.py:919](/Users/rmanaloto/dev/github/ray-manaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:919), [dag_tick.py:1054](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:1054), [test_dag_tick.py:556](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:556), [suites.toml:1255](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1255)
- **What:** NEEDS_HUMAN is safely LOG-only only when that classification reaches `plan()`. The tick then executes the resulting actions without refreshing state. `execute_respawn()` re-reads only roster/PID liveness; it never reloads `state.json`, normalizes `needs`, or reclassifies the node. Therefore a node planned as DEAD→RESPAWN can acquire `state=blocked` plus `needs` before execution and still be respawned if its PID is dead at the fresh roster check.
- **Verified by:** source inspection plus a read-only behavioral introspection arm. It produced:

  `snapshot_class=dead → planned_action=respawn → latest_class_before_execution=needs_human → execute_result="dag-tick: RESPAWN race1"`.

  The ordinary static matrix is otherwise correct: a node already classified NEEDS_HUMAN plans LOG for unknown, fresh, and over-age states, under both PID-liveness values. `--dry-run` also does not spawn. The defect is specifically the stale action crossing into `execute_respawn()`.
- **Why it matters:** This is the exact loss #601 is meant to prevent: the tick can respawn an escalation into the idle/no-prompt state documented by #565. Golden equality now permanently enforces the stronger, false guarantee. Either execution needs a fresh state/needs reclassification before `Popen`, or the operator-facing claim must be narrowed to the planning snapshot.

### Clause-by-clause audit

| Literal clause | Result |
|---|---|
| `state=blocked with a needs payload` | Accurate for the production census path. Strings are stripped; empty strings and falsey JSON containers become absence; truthy non-string JSON payloads are conservatively converted to text at [dag_tick.py:338](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:338). The final condition is exactly `state == "blocked" and needs is not None` at [dag_tick.py:386](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:386). |
| `a human was asked a question a respawn cannot answer` | Supported, but partly inferential. Receipt #575 defines `blocked ∧ needs≠∅` as NeedsHuman, while #565 observed that manual respawn returns idle with no automatic continuation at [565.md:27](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/565.md:27). The exact live `blocked + needs` respawn arm remains **UNVERIFIED**. |
| `never respawned BY THIS TICK at any age` | **False**, due to the stale-classification execution route above. It is true only for actions planned from an already-NEEDS_HUMAN snapshot. |
| `the harness's own supervisor is a separate route this module cannot close` | Properly scoped. #565 demonstrates the separate supervisor route for plain `blocked`; #575 explicitly leaves the exact NeedsHuman route unverified and assigns its probe to #590 at [575.md:136](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:136). |
| `#590` | Locally supported as the supervisor/stall probe destination. Current tracker state is **UNVERIFIED** without network access. |
| `tracker projection … is NOT done here` | Accurate. Classification emits a note, planning emits LOG, and live LOG execution performs no operation at [dag_tick.py:971](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:971). |
| `#602` | Ownership/existence is **UNVERIFIED**. No authoritative local receipt for #602 exists, and network access is unavailable. |
| Operator-relevant omission | The reason omits that the no-respawn guarantee is snapshot-scoped and can become stale before execution. The printed note does include the actual `needs` text at [dag_tick.py:869](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:869). |

The golden is not computationally tautological: AST introspection confirmed that the test hardcodes the complete literal—including `dag:needs-human`—rather than importing or recomputing `_needs_human_reason()`. It will not silently follow a production wording or label change. Its problem is semantic provenance: the independent literal is not actually known-good.

The characterization test does not create an additional defect. `_reason_is_honest` is test-local, its implementation is unchanged, all previous positive/negative assertions remain, and the new test explicitly records that it is not a semantic classifier. Fixing that diagnostic would intentionally require updating its characterization test.

The rewritten contract parses successfully. All **39** declared `workflow.dag-tick-wiring` per-path tokens currently occur exactly once. Its “known-good literal” claim is nevertheless inaccurate for the same HIGH finding above.

Severity count: **HIGH 1 · MEDIUM 0 · LOW 0**

Verdict: **DO NOT SHIP**

Receipts — source-verified:

- Read v1, v2, and v3 in order before the v4 brief.
- Branch is `fix/601-dag-tick-needs-human`, clean at `397675b62135467ba4f1e8e828a79665822edd06`.
- Ran both prescribed Git inspections and reviewed every `397675b` hunk.
- Opened the complete current production module, the current changed test regions and supporting files, `python/AGENTS.md`, `tests/AGENTS.md`, and receipts 565/573/575/578. Prior-round receipts plus the current diff leave no unread changed branch file across the four rounds.
- Code introspection confirmed the golden equals the emitted runtime string, independently hardcodes its label, and does not track the implementation.
- Behavioral introspection confirmed both the normal all-age LOG matrix and the stale-action RESPawn counterexample.
- `suites.toml` parsed; all 39 per-path tokens matched exactly once.
- `git diff --check origin/main...HEAD` passed.
- The required `.agent/notepad.md` append was attempted immediately but rejected by the read-only sandbox.

Receipts — reasoned-alone / **UNVERIFIED**:

- A live occurrence of the classify→execute race was not probed; the code and synthetic behavioral arm establish that the route is permitted.
- The exact harness-supervisor behavior for `blocked + needs` remains unverified, as receipt #575 states.
- Current GitHub state for #590 and the existence/ownership claim for #602 are unverified.
- The implementer-reported lint, lint-docs, 1370-test pytest, full verification, and mutation results were not rerun under the sandbox limitations.


---

## Round v5 — report, verbatim

## v4 → v5 disposition

| v4 finding | Disposition | Settling line |
|---|---|---|
| Stale DEAD→RESPAWN action can cross into NEEDS_HUMAN | **PARTIALLY CLOSED — remains HIGH** | The new check catches escalation before [dag_tick.py:951](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:951), but it precedes the roster read and `Popen` at [dag_tick.py:963](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:963). State can still escalate afterward. |

### [HIGH] A queued human answer permanently disables recovery

- **Where:** [dag_tick.py:386](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:386), [dag_tick.py:439](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:439), [dag_tick.py:687](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:687), [565.md:18](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/565.md:18)
- **What:** `Node` reads `queuedPrompt`, but `is_needs_human()` ignores it. Current Claude 2.1.223 binary introspection established the lifecycle:
  - A successfully delivered human reply transitions the ledger active and clears `needs`.
  - If delivery fails, the reply handler persists `queuedPrompt` while leaving `state=blocked` and `needs` intact.
  - `claude respawn` is specifically able to consume that queued prompt and clear `needs`.
- **Why it matters:** `blocked + needs + queuedPrompt` means the human already answered and recovery must deliver that answer. This watchdog instead classifies NEEDS_HUMAN every tick, plans LOG forever, exits 0, and never invokes the respawn path that consumes the reply. Receipt #565 independently establishes that a queued prompt defeats terminal suppression and requires respawn.
- **Verified by:** current source; binary functions `HNr`/`b$n`/`$Nr`; and behavioral introspection: `queued_prompt_class=needs_human action=log`.

This settles the lifecycle question: **`needs` is cleared, but not until successful delivery, settlement, or prompt-consuming respawn.** The queued-but-undelivered state is the unhandled trap.

### [HIGH] The classify→execute race is narrowed, not closed

- **Where:** [dag_tick.py:951](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:951), [dag_tick.py:963](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:963), [dag_tick.py:966](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:966), [suites.toml:1255](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1255)
- **What:** The sequence is state re-check → roster read → `Popen`. A roster-absent but still-running node can write `blocked + needs` during the roster read, after the safety check.
- **Why it matters:** Read-only behavioral introspection produced:

  `dag-tick: RESPAWN race2`, with `Popen` observing `{'state':'blocked','tempo':'blocked','needs':'human answer needed'}`.

  Therefore “never respawned BY THIS TICK” remains false. Reversing the checks would put the escalation predicate closer to `Popen`, but a residual state-check→spawn window remains irreducible without a shared lock, CAS, or atomic “respawn only if state version/predicate still matches” primitive.
- **Verified by:** source ordering and an in-memory execution arm that mutated state during `read_roster()`.

When state is stable, checking escalation before PID changes only which SKIP message wins. Under concurrency, the ordering materially widens the escalation race.

### [HIGH] `execute_stop` has the analogous stale-state defect

- **Where:** [dag_tick.py:325](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:325), [dag_tick.py:572](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:572), [dag_tick.py:980](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:980), [565.md:18](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/565.md:18)
- **What:** A DONE→STOP action re-checks only PID liveness. Between classification and execution, a human reply can make the ledger `done + active`, or add `queuedPrompt`; both make it non-terminal under the source predicate. `execute_stop()` never reloads those fields and still calls `claude stop`.
- **Why it matters:** `claude stop` is live-proven to stop mid-activity. The watchdog can terminate newly resumed work and persist `stopped`.
- **Verified by:** source plus behavioral introspection: a planned STOP with a fresh simulated `done + active` state still issued `['claude', 'stop', 'done1']`.

This is a real defect, but **separate-ticket scope**: it belongs to #578’s general watchdog action lifecycle, not #601’s NEEDS_HUMAN respawn correction.

### [LOW] The execution tests leave one guard masked and use binary-invalid state fixtures

- **Where:** [test_dag_tick.py:1284](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:1284), [test_dag_tick.py:1305](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:1305), [test_dag_tick.py:1320](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:1320), [test_dag_tick.py:1370](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:1370)
- **What:** `test_execute_respawn_skips_when_pid_alive_now` creates no `state.json`. It now exits through the unreadable-state SKIP before reaching the PID check, so it passes even if the fresh PID guard is deleted. Additionally, the corrected and new fixtures omit fields required by Claude’s persisted-state schema—at minimum `detail`, `template`, `intent`, session/cwd, and timestamps. Mocking `Popen` proves an attempted invocation, not that the real binary would accept that ledger.
- **Why it matters:** The three new tests are armed against removing their immediate Python guards, but the change silently disarmed the existing PID-race test, and the claimed realistic control does not reach the actual recovery primitive.
- **Verified by:** control-flow inspection and current binary schema introspection.

The vanished-state test also does not exercise its claimed “next tick” behavior. A persistent unreadable file is classified conservative-ALIVE at [dag_tick.py:842](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:842), so the next tick does not retry `execute_respawn`; it becomes silent. Current Claude writes ordinary state updates via same-directory temporary file plus atomic rename, and `claude respawn` itself refuses missing saved state, so I did **not** establish a separate normally-recoverable partial-write/pruned-directory case caused specifically by the new unreadable-state SKIP. Persistent permission and fallback-write failures remain **UNVERIFIED** live.

`node_from_state` is otherwise an exact semantic extraction of the former census construction: identical type checks, `queuedPrompt` coercion, and `normalize_needs` call.

Severity count: **HIGH 3 · MEDIUM 0 · LOW 1**

Verdict: **DO NOT SHIP**

## Receipts — source-verified

- Read v1, v2, v3, and v4 in order before reviewing v5.
- Branch is clean at `fix/601-dag-tick-needs-human`, HEAD `8c87eecf4a03d1c7e5f6eb14a8213fa8586bbf51`; only `8c87eec` is new since v4.
- Inspected the complete production module, changed tests, contract, receipts 565/573/575/578, and current Claude 2.1.223 binary state/reply/respawn paths.
- Behavioral introspection reproduced the queued-prompt deadlock classification, residual escalation race, and stale STOP action.
- `workflow.dag-tick-wiring` parses: 119 suites; all **43** declared tokens match exactly once.
- `git diff --check origin/main...HEAD` passed.
- The required `.agent/notepad.md` append was attempted immediately and rejected by the read-only sandbox.

## Receipts — reasoned-alone / UNVERIFIED

- The frequency of the residual escalation and STOP races in live ticks is **UNVERIFIED**; source permits both interleavings.
- A live failed human-reply delivery producing the queuedPrompt/needs combination was not run; the current binary explicitly permits it.
- Implementer-reported lint, lint-docs, pytest, verification, and mutation results remain **UNVERIFIED** under the mandated sandbox limits.
- GitHub state for #590/#602 and any new ticket for `execute_stop` is **UNVERIFIED**.


---

## Round v6 — report, verbatim

| v5 finding | v6 disposition | Settling evidence |
|---|---|---|
| HIGH 1 — queued reply deadlock | **PARTIALLY CLOSED — remains HIGH** | Dead-PID delivery is restored, but the newly reachable live-PID shape becomes ALIVE with no action at [dag_tick.py:463](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:463). |
| HIGH 2 — residual classify→execute race | **NARROWED and accurately disclosed** | The escalation read is last before `Popen` at [dag_tick.py:998](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:998). The inverse PID race below is LOW because Claude independently refuses an already-running session. |
| HIGH 3 — stale `execute_stop` | **UNCHANGED; accepted out of scope** | No `execute_stop` behavior changed. Issue #604’s existence/relationship is **UNVERIFIED** under the mandated no-network review. |
| LOW — masked PID test / thin fixtures | **PID arm closed; schema objection correctly declined, narrowly** | The repaired test reaches and identifies the PID guard at [test_dag_tick.py:1409](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:1409). Unrelated omitted ledger fields exercise no code here. The missing live-PID queued-reply arm is behavioral, not a fuller-fixture issue. |

### [HIGH] A failed reply to a live-but-unreachable worker becomes permanently invisible

- **Where:** [dag_tick.py:419](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:419), [dag_tick.py:463](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:463), [dag_tick.py:895](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:895), [test_dag_tick.py:240](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:240), [test_dag_tick.py:359](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:359)
- **What:** `09d2cb9` assumes a queued reply always reaches respawn. It does only when `pid_alive=False`. For `blocked + needs + queuedPrompt + pid_alive=True`, `is_terminal` is false, `is_needs_human` is now false, DEAD is bypassed, and `tempo="blocked"` is not WEDGED. The result is ALIVE; `plan()` emits no action and the normal non-verbose tick emits no note.
- **Why it matters:** Claude 2.1.223’s actual reply handler can persist `queuedPrompt` after `ENOCONN`/`ETIMEOUT` while its roster worker PID is still alive. Its UI says that reply waits until the session restarts. A live-but-unreachable process can therefore retain the human answer indefinitely while every tick silently classifies it ALIVE. This is the same “watchdog stops recovering” failure the commit says is worse than over-recovery, now in a newly untested liveness arm.
- **Verified by:** current Python control flow; installed binary schema and functions `b$n`, `S$n`, `HNr`, and `$Nr`; and read-only behavioral introspection:

  `queued=True, pid_alive=True → class=alive, actions=[]`

  The new tests prove only dead-PID delivery: [test_dag_tick.py:375](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:375) explicitly supplies `pid_alive=False`, and the end-to-end fixture uses an empty roster at [test_dag_tick.py:400](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:400).

### [LOW] Moving the PID check earlier widens its TOCTOU window and can falsely report RESPAWN

- **Where:** [dag_tick.py:998](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:998), [dag_tick.py:1001](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:1001), [dag_tick.py:1014](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:1014)
- **What:** The PID decision now precedes the state-file stat/read/parse. Another actor can revive the node during that I/O, after which this function still launches `claude respawn` and unconditionally returns `RESPAWN`.
- **Why it matters:** The fresh-PID guard is no longer closest to the action it protects. The detached child’s stdout/stderr are discarded, so its refusal is reported as success.
- **Verified by:** AST ordering plus in-memory execution:

  `roster_read=False → state_read revives node → Popen sees pid_alive_now=True → "dag-tick: RESPAWN race3"`.

  **Counterevidence:** installed Claude `$Nr` rechecks liveness and returns “Session … is already running.” I therefore did not establish an actual double-start and rate this LOW, not HIGH. A live end-to-end occurrence remains **UNVERIFIED**.

### Mandatory code-introspection results

| Attack | Result |
|---|---|
| Queued prompt on dead PID | Correctly reaches DEAD → RESPAWN. |
| Queued prompt on live PID | **Broken:** reaches ALIVE → no action or normal note; HIGH above. |
| Stale/unrelated queued prompt | The binary schema provides only a bare string, with no question identity to correlate it to `needs`. A naturally occurring unrelated pair is **UNVERIFIED**; no separate finding manufactured. |
| PID-before-state ordering | Narrows escalation TOCTOU but widens PID TOCTOU; current CLI guard limits demonstrated impact to false reporting. |
| V2 counterexample | Still rejected **for its projection defect**: the rebased respawn clause matches, while `IS done here` fails the required contiguous `is NOT done here` clause. |
| V3 counterexample | Still returns `True` for its intended reason: it satisfies every template clause and contradicts itself afterward. |
| Contract tokens | TOML parsed; all **47** per-path tokens occur exactly once. No remaining 0× or 2× token. |

Golden-literal audit:

- `state=blocked … needs … no queued reply` — source-verified by the exact predicate at [dag_tick.py:419](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:419).
- `not respawned BY THIS TICK at any age` — source-verified for a state actually classified or freshly re-read as NEEDS_HUMAN.
- `re-checked immediately before spawn` — true when “spawn” means the outer `Popen` of the `claude respawn` CLI. The actual worker starts later inside that CLI; the literal’s disclosed read-to-spawn window covers that limitation.
- Residual read-to-spawn race — truthfully disclosed.
- Separate harness supervisor route — source/binary-supported; its exact live `blocked + needs` behavior remains **UNVERIFIED**.
- Tracker projection not done here — source-verified. Current #590/#602 tracker state is **UNVERIFIED**.
- AST introspection confirmed the production reason exactly equals the independent golden; V2 returned `False`, V3 returned `True`.

Severity count: **HIGH 1 · MEDIUM 0 · LOW 1**

Verdict: **DO NOT SHIP**

### Receipts — source-verified

- Read v1 through v5 in order before reviewing v6.
- Clean `fix/601-dag-tick-needs-human` at `09d2cb9406d2ff452496e322e326df8702d6ed39`; seven branch commits, only `09d2cb9` new since v5.
- Opened the complete production module, changed tests, contract, applicable `AGENTS.md` files, and supporting receipts.
- Inspected installed Claude 2.1.223’s persisted-state schema, failed-reply queue path, successful-reply clearing, respawn consumer, and already-running guard.
- Executed read-only AST and behavioral introspection for the golden, V2/V3, four queued/PID combinations, and reordered PID race.
- Parsed `suites.toml`; all 47 tokens matched once.
- The required notepad append was attempted twice and rejected by the read-only sandbox.

### Receipts — reasoned-alone / UNVERIFIED

- A live occurrence of the HIGH state was not induced against a real worker.
- A naturally stale or unrelated `queuedPrompt`/`needs` pair is **UNVERIFIED**.
- Actual double-start from the reordered PID window is **UNVERIFIED** and has strong binary counterevidence.
- Implementer-reported lint, lint-docs, pytest, verification, and mutation results remain **UNVERIFIED**, as required by the brief.
- GitHub state for #590, #602, and #604 remains **UNVERIFIED**.


---

## Round v7 — report, verbatim

1. **Q1 verdict — no disagreement.** All 32 expected values are semantically correct for the pinned `tempo="idle"` and `state_age_s=None`. This agrees with the terminal predicate, escalation/queued-reply rules, and precedence in [dag_tick.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:326) and [dag_tick.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:458), plus [565.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/565.md:18) and [575.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/575.md:14).

2. **Q2 verdict — four axes incomplete.** `tempo` is a fifth class-changing axis outside WEDGED. For the existing `done/no-needs/no-queued/dead` cell, `tempo="idle"` yields DONE, while `tempo="active"` yields DEAD; with a live PID and unknown age it yields ALIVE. The installed 2.1.223 binary confirms the same terminal predicate. The table pins tempo away at [test_dag_tick.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:648), despite `is_terminal()` using it at [dag_tick.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:326).

3. **Q3 verdict — meta-tests do not hold the mapping honest.** Coverage ignores the expected column, while reachability checks only its set of values ([test_dag_tick.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:660), [test_dag_tick.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:677)). A 32-row table assigning the five classes arbitrarily once and ALIVE to the remaining 27 cells passes both. The parametrized test catches disagreement with current code, but not identically wrong code and expectations.

4. **Counts:** HIGH 0 · MEDIUM 2 · LOW 0. **DO NOT SHIP.**

5. **Receipts:** Source-verified against the classifier, table, three receipts, and installed Claude Code 2.1.223; the tempo counterexample was executed directly. The meta-test counterexample was independently computed. Full repository gates were **UNVERIFIED** in this review.


---

## Brief v1 — what the reviewer was asked, verbatim

# Adversarial review brief — #601, `dag_tick` NEEDS_HUMAN

You are an **adversarial reviewer**. Your job is to find what is WRONG, not to
approve. A review that concludes "looks good" without having opened the source
is a failed review. Assume the implementer was plausible-sounding and wrong
somewhere; your job is to locate where.

Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch under review: `fix/601-dag-tick-needs-human`
Base: `origin/main` at `d070cb5`

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles diff origin/main...HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles log origin/main..HEAD
```

Two commits: `e9da8cb` (the fix) and `42e7c9c` (a review round).

## MANDATORY: code introspection is not optional

This section is load-bearing. A previous reviewer that skipped it rubber-stamped
a plan whose central artifact was silently inert.

1. **Open every file the diff changes**, in full — not just the hunks:
   - `python/src/dotfiles_setup/dag_tick.py`
   - `tests/test_dag_tick.py`
   - `python/verification/suites.toml` (the `workflow.dag-tick-wiring` suite)
2. **Open the code that CONSUMES what the diff adds.** If the diff adds a
   contract token, open the engine that reads it (`python/src/dotfiles_setup/
   verify.py`, and `token_audit.py`) and confirm the token is actually
   enforced — not merely present. This exact class of defect (a contract
   stanza silently ignored because no handler read it) is the reason this
   section exists.
3. **Cite `file:line` for every claim.** A finding with no line reference is
   not a finding.
4. **Mark anything you could not verify as `UNVERIFIED`** rather than
   asserting it. Do not guess.
5. **End with a receipts list** splitting what you verified *by reading source*
   from what you concluded *by reasoning alone*.

## What the change claims to do

`dag_tick.py` is a launchd watchdog: every 60s it censuses background Claude
Code agent nodes, classifies each, and recovers (`claude respawn` for a DEAD
node, `claude stop` for a lingering DONE node).

`TERMINAL_STATES = {done, failed, stopped}` deliberately excludes `blocked`.
The claimed defect: a node that escalated to a human — `state == "blocked"`
with a non-empty `needs` payload — classified DEAD once its process died, and
DEAD means respawn. A respawn allegedly returns the node IDLE with no prompt,
so the human's question is silently discarded.

The fix adds `NodeClass.NEEDS_HUMAN` for the conjunction `state == "blocked"
AND needs non-empty`, placed **above** the pid-liveness check and **below** the
terminal check. Its action is log-only, at any age and either liveness.

## Attack these specifically

Do not limit yourself to this list, but do not skip it either.

1. **Precedence.** The order is DONE → NEEDS_HUMAN → DEAD → WEDGED → ALIVE.
   Find a node shape where this order produces a WORSE outcome than before the
   change. In particular: NEEDS_HUMAN now pre-empts WEDGED, and it pre-empts
   DEAD. Is there a shape where suppressing the respawn is the wrong call?
2. **Behaviour regression.** The ticket requires that a plain `blocked` node
   with no `needs` behaves EXACTLY as before. Prove or disprove this by
   reading `classify`, `plan`, and `classify_background_rows` — not by reading
   the tests, which could share the implementer's blind spot.
3. **`normalize_needs`.** Find an input where it returns `None` for what is
   really an escalation (which would respawn the node — the exact harm), or
   returns non-`None` for what is really absence (which would strand a healthy
   node forever). Consider what `state.json` can actually contain.
4. **Tests that can only pass.** This repo's standard is that every probe
   needs a control arm. Find any new test that would still pass with the
   feature removed, or whose negative assertion (`not in`, `not any(...)`)
   checks a string the code never emits in any case — a spelling mismatch
   makes such an assertion vacuous. Verify the asserted strings against the
   real f-strings in `dag_tick.py`.
5. **The contract.** `workflow.dag-tick-wiring` uses `per_path_tokens`. Check
   whether each new token binds the actual WIRING or could be satisfied by a
   comment, a docstring, or a second occurrence elsewhere in the file. Open
   `token_audit.py` to see what uniqueness it does and does not enforce.
6. **The deferral.** The ticket said the action is "log, project, label
   `dag:needs-human`, never respawn". Only log + never-respawn shipped. The
   grounds given are `docs/receipts/575.md` R1 (projection is scheduler-owned
   and one-directional). Read `575.md` and rule on whether that is a
   legitimate boundary or a missing requirement dressed up as one.
7. **`is_stalled` vs `_is_stale_dead`.** These two helpers deliberately treat
   an unknown age (`None`) in OPPOSITE directions. Verify that both directions
   are actually correct at every call site, and that the extraction of
   `is_stalled` did not change `classify`'s behaviour for any input.
8. **Anything the implementer asserted that you can falsify.** The commit
   messages make specific factual claims (mutation-test failure counts, live
   node shapes, gate results). Check the ones that are checkable from source.

## Ground truth you may rely on

`docs/receipts/565.md`, `docs/receipts/575.md`, `docs/receipts/578.md`, and
GitHub issue #601 (`gh issue view 601 -R ray-manaloto/dotfiles`). Treat these
as the spec. Treat the commit messages as CLAIMS, not evidence.

## Output format

For each finding:

```
### [SEVERITY] Short title
- **Where:** file:line
- **What:** the defect
- **Why it matters:** the concrete failure it causes
- **Verified by:** reading <file:line> / reasoning alone
```

Severity is one of HIGH / MEDIUM / LOW. End with:

- a count per severity;
- an explicit `SHIP` or `DO NOT SHIP` verdict;
- the receipts list from item 5 of the introspection section.

Be specific and be harsh. If you find nothing HIGH, say so plainly — but only
after you have opened the files.


---

## Brief v2 — what the reviewer was asked, verbatim

# Adversarial review brief v2 — #601, `dag_tick` NEEDS_HUMAN

You reviewed this branch once and returned **DO NOT SHIP** (2 HIGH, 1 LOW).
Your v1 report is at:

`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/99d89987-5c97-45a2-9bf9-0d7f80a1ed54/scratchpad/codex-review.md`

**Read it first.** Do not restate its findings; adjudicate whether the fix
closed them, and hunt for what the fix broke.

Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch: `fix/601-dag-tick-needs-human`

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles log origin/main..HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles diff origin/main...HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles show cf6e97d
```

Three commits now: `e9da8cb` (fix) → `42e7c9c` (first review round) →
**`cf6e97d`** (your v1 findings). Only `cf6e97d` is new since you last looked.

## Your v1 findings and what was done

1. **HIGH — required tracker projection is missing.** Accepted in part. The
   projection is now owned by a filed ticket (**#602**, a sub-issue of map
   #556). The log line no longer claims it happens. The boundary argument is
   unchanged: `575.md` R1 makes projection scheduler-owned and
   one-directional, and no scheduler component exists in-tree, so this tick
   emitting a label would put a second writer on the tracker.
   **Your v1 sub-point was accepted in full and is the sharper one:** the
   reason string said `project + label dag:needs-human` while performing
   neither.
2. **HIGH — "never auto-respawned" closes only one respawner.** Accepted in
   full as a WORDING defect. The behaviour was not changed — #601's own body
   states the fix is safe either way, since suppressing our respawn cannot be
   worse than respawning into an idle zombie. The string now reads
   "never respawned BY THIS TICK" and names the harness's own supervisor as a
   route this module cannot close, pointing at #590.
3. **LOW — the contract accepts commented-out wiring.** Accepted, explicitly
   NOT fixed. It is a property of `verify.py`'s unanchored substring matching
   across all 115 contracts, not of this suite. Recorded in the commit body.

## MANDATORY: code introspection is not optional

Same rules as v1. Open the source; cite `file:line`; mark anything you cannot
verify as `UNVERIFIED`; end with a receipts list splitting source-verified
from reasoned-alone.

## Sandbox limits — do NOT report these as findings

Your v1 receipts correctly noted you could not reach the network, could not
read GitHub issue #601, and could not run the full pytest suite (no writable
temp dir). **That is still true and is not a defect in the change.** Do not
spend findings on it. Reason from source. The following are the implementer's
CLAIMS about the current tree — treat them as unverified claims, not evidence,
and do not re-report your inability to check them:

- `mise run lint` rc=0; `mise run lint-docs` rc=0
- `pytest tests/` → 1369 passed, 4 deselected, rc=0
- `dotfiles-setup verify run` → 115 passed, 0 failed, 4 skipped

## Attack these specifically

1. **Did the v1 fixes actually close v1's findings, or only relabel them?**
   Read the new `_needs_human_reason()` in full. Is the new string now
   *accurate* about every action the module does and does not take — or has a
   new overclaim been introduced while removing the old one?
2. **Did the fix introduce a new defect?** `cf6e97d` also changed the
   `NEEDS_HUMAN_LABEL` comment and the `workflow.dag-tick-wiring` description.
   Check the contract still parses and still binds what it claims, and that
   the description does not now assert something false.
3. **The new tests.** `test_plan_needs_human_reason_claims_no_action_this_module_skips`
   asserts two phrases PRESENT and two ABSENT. Is the absent-arm genuinely
   control-armed, or could it pass vacuously? Could either present-assertion
   pass against a string that is still misleading?
4. **Round-2 regression hunt.** Each fix round trades old bugs for new ones.
   Re-check the things you cleared in v1 — the plain-`blocked` path, the
   negative assertions' spellings, `is_stalled` vs `_is_stale_dead` — against
   the CURRENT tree, not your v1 notes. A file you read at `e9da8cb` has moved.
5. **Anything you deferred in v1 for time.** If you flagged something as
   UNVERIFIED that source could settle, settle it now.

## Output format

Same as v1. For each finding: severity, `file:line`, what, why it matters,
verified-by. End with a per-severity count, an explicit `SHIP` / `DO NOT SHIP`
verdict, and the receipts list.

Additionally, open with a short **v1 → v2 disposition table**: for each v1
finding, one of `CLOSED` / `PARTIALLY CLOSED` / `OPEN`, with the line that
settles it.

If the change is now shippable, say so plainly — but only after opening the
files. Do not manufacture findings to justify a second round.


---

## Brief v3 — what the reviewer was asked, verbatim

# Adversarial review brief v3 — #601, `dag_tick` NEEDS_HUMAN

You have reviewed this branch twice.

- v1 report: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/99d89987-5c97-45a2-9bf9-0d7f80a1ed54/scratchpad/codex-review.md`
  (DO NOT SHIP — 2 HIGH, 1 LOW)
- v2 report: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/99d89987-5c97-45a2-9bf9-0d7f80a1ed54/scratchpad/codex-review-v2.md`
  (SHIP — 0 HIGH, 0 MEDIUM, 2 new LOW)

**Read both first.** Do not restate their findings.

Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch: `fix/601-dag-tick-needs-human`

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles log origin/main..HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles show b9214ad
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles diff origin/main...HEAD
```

Four commits: `e9da8cb` → `42e7c9c` → `cf6e97d` → **`b9214ad`**.
**Only `b9214ad` is new since your v2 review, and it is the ONLY commit you
have never reviewed.** It exists solely to close your two v2 LOWs.

## Why you are being asked a third time

Your v2 round found a real hole in the very test written to close your v1
round — the loose fragment `is NOT done here`, which your counterexample
defeated. That is the fix-introduces-new-bugs pattern firing for real, not in
theory. `b9214ad` is another fix written to close a review finding, so it is
exactly the kind of commit that historically carries the next defect.

**Your job is to break `b9214ad` specifically.** If it holds, say so plainly.
Do not manufacture findings to justify a third round; a clean SHIP with no
findings is an acceptable and useful outcome here.

## What `b9214ad` changed

1. **`tests/test_dag_tick.py`** — the wording regression test was rewritten.
   The inline assertions became a named predicate `_reason_is_honest(reason)`,
   and your v2 counterexample is stored verbatim as `_DISHONEST_REASON`. The
   test now asserts `_reason_is_honest(real) is True` AND
   `_reason_is_honest(_DISHONEST_REASON) is False`.
2. **`python/src/dotfiles_setup/dag_tick.py`** — the `NEEDS_HUMAN_LABEL`
   comment was rewritten into three explicit parts (ownership SETTLED,
   spelling SETTLED, implementation PENDING), per your v2 LOW 1.
3. **`python/verification/suites.toml`** — the same three-part correction in
   the `workflow.dag-tick-wiring` description.

## Attack these specifically

1. **Break `_reason_is_honest` again.** Construct a NEW string that:
   - satisfies every condition in `_reason_is_honest`, AND
   - still misleads an operator about what the module does.
   If you find one, that is a finding; quote the string. If you convince
   yourself none exists within the predicate's terms, say what makes it tight
   this time and where its remaining blind spot is (e.g. what it does NOT
   constrain at all).
2. **Is the predicate's own control arm real?** The test asserts one passing
   input and one failing input. Does that actually demonstrate discrimination,
   or could `_reason_is_honest` be trivially satisfiable/unsatisfiable in a way
   those two inputs hide? Consider what happens if the real reason string were
   changed to something else valid.
3. **Did extracting the predicate move logic out of the assertion in a way
   that weakens it?** Compare `b9214ad`'s test against `cf6e97d`'s. Is anything
   the old version checked no longer checked?
4. **Is the three-part receipt correction now ACCURATE?** You faulted two
   previous versions in opposite directions. Read `575.md` and `573`'s receipt
   and rule on whether the third attempt is finally right — including the claim
   that 575 defers "each stage's evidence contract", and the claim that #573's
   receipt governs the spelling.
5. **Contract integrity.** `b9214ad` touched the suite description again.
   Confirm it still parses, tokens still match exactly once, and the
   description asserts nothing false.
6. **Anything in the full diff you have not yet examined.** This is your last
   pass; if something has gone unread across all three rounds, read it now and
   say so.

## MANDATORY: code introspection is not optional

Open the source; cite `file:line`; mark anything you cannot verify as
`UNVERIFIED`; end with a receipts list splitting source-verified from
reasoned-alone.

## Sandbox limits — do NOT report these as findings

Unchanged from v2: no network, no writable temp dir, so no GitHub access and
no full pytest run. Not a defect in the change; do not spend findings on it.
The implementer's CLAIMS about the current tree, to be treated as unverified
rather than re-reported:

- `mise run lint` rc=0; `mise run lint-docs` rc=0
- `pytest tests/` → 1369 passed, 4 deselected, rc=0
- `dotfiles-setup verify run` → 115 passed, 0 failed, 4 skipped
- GitHub issue #602 exists and is a sub-issue of #556 (verified by the
  implementer: sub-issue count moved 27 → 28, with a control arm)

## Output format

Open with a **v2 → v3 disposition table** (`CLOSED` / `PARTIALLY CLOSED` /
`OPEN` per v2 finding, with the settling line). Then findings in the usual
format: severity, `file:line`, what, why it matters, verified-by. End with a
per-severity count, an explicit `SHIP` / `DO NOT SHIP`, and the receipts list.


---

## Brief v4 — what the reviewer was asked, verbatim

# Adversarial review brief v4 — #601, `dag_tick` NEEDS_HUMAN

You have reviewed this branch three times. Reports (read all three first, in
order; do not restate their findings):

- v1 `…/scratchpad/codex-review.md` — DO NOT SHIP, 2 HIGH, 1 LOW
- v2 `…/scratchpad/codex-review-v2.md` — SHIP, 0 HIGH, 2 new LOW
- v3 `…/scratchpad/codex-review-v3.md` — SHIP, 0 HIGH, 1 LOW

(Full directory: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/99d89987-5c97-45a2-9bf9-0d7f80a1ed54/scratchpad/`)

Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch: `fix/601-dag-tick-needs-human`

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles log origin/main..HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles show 397675b
```

Five commits. **Only `397675b` is new since your v3 review.** It closes your
v3 LOW by replacing the substring guard with GOLDEN EQUALITY.

## Why a fourth round

Each of the last two "fix the review finding" commits carried the next
finding. That pattern has now held twice running, so `397675b` gets the same
treatment.

## What `397675b` changed

1. `_EXPECTED_NEEDS_HUMAN_REASON` — a golden literal in the test file; the
   test asserts the emitted reason EQUALS it.
2. `_reason_is_honest` demoted to a clause-level diagnostic, with its limits
   asserted in a new test
   (`test_reason_honesty_predicate_is_a_template_guard_not_a_classifier`):
   it accepts your v3 counterexample and rejects an honest paraphrase.
3. Your v3 counterexample stored verbatim as `_DISHONEST_REASON_V3`.
4. The `workflow.dag-tick-wiring` description walked back its "cannot return"
   claim.

## The primary attack — the one that matters most now

Every round so far has attacked whether the CHECK constrains the string.
Nobody has yet audited whether **the string itself is true**.

Golden equality pins the reason exactly — which means the guard is now only
as good as the literal it pins. If the expected literal itself misdescribes
the module, the test enforces a lie forever and every future round agrees
with it.

So: **read the current emitted reason clause by clause and verify each claim
against the code.** The string is at `_needs_human_reason()` in
`python/src/dotfiles_setup/dag_tick.py`. For each clause ask "is this
actually true of this module?", including:

- `state=blocked with a needs payload` — is that exactly the classification
  condition, or does `normalize_needs` widen/narrow it?
- `a human was asked a question a respawn cannot answer` — supported by
  `docs/receipts/565.md`, or stronger than what 565 measured?
- `never respawned BY THIS TICK at any age` — is "at any age" true on EVERY
  path, including `--max-age`, `--dry-run`, and `execute_respawn`'s fresh
  re-check? Is there any route by which this tick could still respawn a
  NEEDS_HUMAN node?
- `the harness's own supervisor is a separate route this module cannot close`
  — accurate, or does it assert more about the supervisor than 565/575
  establish?
- `#590` and `#602` — are those the right tickets for the claims they are
  attached to?
- Anything the string OMITS that an operator acting on it would need.

## Also attack

1. **Is the golden tautological?** `tests/AGENTS.md` requires expected values
   to come from an independent source, not be recomputed the way the code
   computes them. Check how the literal is defined and whether it could
   silently track a module change.
2. **Does `test_reason_honesty_predicate_is_a_template_guard_not_a_classifier`
   pin a bug as a feature?** It asserts the diagnostic ACCEPTS a dishonest
   string. Is that a legitimate record of a measured limit, or does it
   entrench the weakness and make fixing it look like a regression?
3. **Did demoting `_reason_is_honest` lose any check** that the previous
   version performed?
4. **Contract accuracy.** The description was rewritten again. Does it now
   assert only what holds? Does it still parse, tokens matching exactly once?
5. **Anything unread across all four rounds.** Last pass; say what you read.

## MANDATORY: code introspection is not optional

Open the source; cite `file:line`; mark anything you cannot verify as
`UNVERIFIED`; end with a receipts list splitting source-verified from
reasoned-alone.

## Sandbox limits — do NOT report these as findings

No network, no writable temp dir (uv cannot initialise its cache), so no
GitHub access and no pytest run. Not a defect in the change. Implementer's
CLAIMS about the current tree, to be treated as unverified rather than
re-reported:

- `mise run lint` rc=0; `mise run lint-docs` rc=0
- `pytest tests/` → 1370 passed, 4 deselected, rc=0
- `dotfiles-setup verify run` → 115 passed, 0 failed, 4 skipped
- Mutation arm: appending the v3 counterexample clause to the real production
  string FAILS the test.

## Output format

Open with a **v3 → v4 disposition table**. Then findings: severity,
`file:line`, what, why it matters, verified-by. End with a per-severity count,
an explicit `SHIP` / `DO NOT SHIP`, and the receipts list.

A clean SHIP with zero findings is an acceptable and useful outcome. Do not
manufacture findings to justify a fourth round — but if the expected literal
misdescribes the module in any way, that IS a finding and it outranks
everything else here.


---

## Brief v5 — what the reviewer was asked, verbatim

# Adversarial review brief v5 — #601, `dag_tick` NEEDS_HUMAN

You have reviewed this branch four times. Reports (read all four first, in
order; do not restate their findings):

- v1 `…/codex-review.md` — DO NOT SHIP, 2 HIGH, 1 LOW
- v2 `…/codex-review-v2.md` — SHIP, 0 HIGH, 2 new LOW
- v3 `…/codex-review-v3.md` — SHIP, 0 HIGH, 1 LOW
- v4 `…/codex-review-v4.md` — **DO NOT SHIP, 1 HIGH** (the classify→execute race)

Directory: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/99d89987-5c97-45a2-9bf9-0d7f80a1ed54/scratchpad/`

Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch: `fix/601-dag-tick-needs-human`

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles log origin/main..HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles show 8c87eec
```

Six commits. **Only `8c87eec` is new since your v4 review**, and unlike every
previous fix commit it changes **real execution behaviour**, not prose or
tests. It is the riskiest commit on the branch.

## What `8c87eec` changed

Your v4 HIGH was accepted in full. `execute_respawn` now performs a fresh
**escalation** re-check as well as the pid re-check it already did:

1. Re-read `state.json`; if unreadable → **SKIP** (new refusal path).
2. Build a `Node` via the new shared `node_from_state`; if
   `is_needs_human(...)` → **SKIP**.
3. Only then the pre-existing roster/pid check, then `Popen`.

Also: `node_from_state` extracted and shared with `classify_background_rows`;
three new tests (race SKIP, no-escalation control, vanished-state SKIP); two
existing fixtures corrected to write a `state.json` (they previously called
`execute_respawn` with none, which a DEAD-classified node cannot have).

## The primary attack — what this fix might have BROKEN

Your v4 finding was "it respawns when it must not". The symmetric risk now is
**"it fails to respawn when it must"** — a watchdog that silently stops
recovering is a worse outage than one that occasionally over-recovers, and it
would be invisible: the tick keeps exiting 0 and logging SKIP lines forever.

1. **Can the new SKIP paths deadlock recovery permanently?** In particular the
   unreadable-`state.json` refusal. Find a realistic state in which a node
   genuinely needs respawning but this function now refuses it on **every**
   tick, forever. Consider: a `state.json` mid-write (partial JSON), a node
   whose job dir was pruned, a permissions error, a node whose `needs` is
   never cleared after the human answers.
2. **Is `needs` ever CLEARED?** If a node writes `needs`, a human answers, and
   the field is never cleared on disk, then that node is permanently
   un-respawnable by this tick. Is that correct behaviour or a new trap? Check
   whether anything in the repo or the receipts establishes the lifecycle of
   the `needs` field. If nothing does, say so — an unverified lifecycle
   assumption underneath a permanent refusal is itself a finding.
3. **Is the ordering right?** The escalation check runs BEFORE the pid check.
   Does that change any outcome versus the reverse order, or only the SKIP
   message? Is there a case where checking escalation first is wrong?
4. **Did the shared `node_from_state` change the census path's behaviour?**
   It replaced inline construction in `classify_background_rows`. Confirm
   byte-for-byte equivalent semantics, not just similar shape.
5. **Is the race actually closed, or only narrowed?** `load_state_json` and
   `Popen` are still two separate operations. Construct any remaining
   interleaving that still respawns an escalation. If the residual window is
   irreducible without locking, say that plainly and characterise it.

## Also settle this (flagged UNVERIFIED by the implementer)

`execute_stop` re-reads only the roster, exactly as `execute_respawn` did
before this fix. **Does it have the same staleness defect?** Rule on it with
source, and say whether it is in #601's scope or a separate ticket. Do not
assume it is affected — the claim is explicitly unverified and was raised as a
hunch, not a finding.

## Also attack

- Contract description accuracy; does it parse, tokens matching exactly once?
- The three new tests: are they armed, or could any pass with the fix removed?
- The two corrected fixtures: is writing `{"state": "blocked", "tempo": "idle"}`
  the right realistic shape, or does it smuggle in an assumption?
- Anything unread across all five rounds.

## MANDATORY: code introspection is not optional

Open the source; cite `file:line`; mark anything you cannot verify as
`UNVERIFIED`; end with a receipts list splitting source-verified from
reasoned-alone.

## Sandbox limits — do NOT report these as findings

No network, no writable temp dir, so no GitHub access and no pytest run.
Implementer's CLAIMS about the current tree, treat as unverified rather than
re-reporting:

- `mise run lint` rc=0; `mise run lint-docs` rc=0
- `pytest tests/` → 1373 passed, 4 deselected, rc=0
- `dotfiles-setup verify run` → 115 passed, 0 failed, 4 skipped
- Mutation arm: deleting the escalation re-check fails the race test and only
  the race test.

## Output format

Open with a **v4 → v5 disposition table**. Then findings: severity,
`file:line`, what, why it matters, verified-by. End with a per-severity count,
an explicit `SHIP` / `DO NOT SHIP`, and the receipts list.

A clean SHIP with zero findings is acceptable and useful. Do not manufacture
findings — but a way for this watchdog to stop recovering silently outranks
everything else here, so look for that first.


---

## Brief v6 — what the reviewer was asked, verbatim

# Adversarial review brief v6 — #601, `dag_tick` NEEDS_HUMAN

You have reviewed this branch five times. Reports (read all five first, in
order; do not restate their findings):

- v1 `…/codex-review.md` — DO NOT SHIP, 2 HIGH, 1 LOW
- v2 `…/codex-review-v2.md` — SHIP, 0 HIGH, 2 new LOW
- v3 `…/codex-review-v3.md` — SHIP, 0 HIGH, 1 LOW
- v4 `…/codex-review-v4.md` — DO NOT SHIP, 1 HIGH (classify→execute race)
- v5 `…/codex-review-v5.md` — DO NOT SHIP, 3 HIGH (queued reply, residual race, execute_stop)

Directory: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/99d89987-5c97-45a2-9bf9-0d7f80a1ed54/scratchpad/`

Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch: `fix/601-dag-tick-needs-human`

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles log origin/main..HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles show 09d2cb9
```

Seven commits. **Only `09d2cb9` is new since your v5 review.**

## Disposition of your v5 findings

- **HIGH 1 (queued reply deadlock) — fixed.** `is_needs_human` now takes
  `queued_prompt` and requires it false. Your binary-derived lifecycle is
  recorded in the docstring and the contract.
- **HIGH 2 (residual race) — narrowed and DISCLOSED, not closed.** The
  escalation re-check moved to run LAST, immediately before `Popen` (pid
  check first). The operator-facing reason now states the residual
  read-to-spawn window explicitly rather than claiming "never".
- **HIGH 3 (`execute_stop`) — accepted, out of scope, FILED as #604** (a
  sub-issue of map #556, verified: 28 → 29). Not fixed on this branch, by
  your own scoping.
- **LOW (masked pid test + schema-thin fixtures)** — the masked test is fixed
  and mutation-verified re-armed. The fixture-schema point is recorded as a
  known limitation and deliberately not chased: this module reads only
  `state`/`tempo`/`queuedPrompt`/`needs`, so a fuller ledger would exercise
  none of our code. **Say if you think that reasoning is wrong.**

## The primary attack

Your last two rounds each found a HIGH, and v5's HIGH 1 was **introduced by
the fix for v4's HIGH**. So the specific thing to hunt is: **what did
`09d2cb9` break?**

1. **Does the `queued_prompt` term create a NEW hole?** A node with
   `blocked + needs + queuedPrompt` now classifies DEAD and gets respawned.
   Is that right in every case? Construct one where respawning it is wrong —
   e.g. a stale `queuedPrompt` that will never be consumed, a queued prompt
   on a node whose process is alive, a `queuedPrompt` that coexists with a
   genuinely unanswered `needs`.
2. **Is the reordering safe?** The pid check now runs BEFORE the state read.
   Find any case where that ordering is worse than the reverse, beyond which
   SKIP message wins.
3. **Is the new golden literal true?** Same audit as v4, on the NEW string —
   every clause against the code. It now claims "no queued reply",
   "re-checked immediately before spawn", and a disclosed residual window.
   Verify each. If any clause is false, that outranks everything else: golden
   equality now enforces whatever it says.
4. **Did the re-based counterexamples stop probing what they were built for?**
   `_DISHONEST_REASON_V2/V3` had their scoped-respawn clause changed from
   "never" to "not" so they still exercise their own defect rather than being
   rejected on a wording mismatch. Confirm V2 is still rejected FOR ITS
   DEFECT and V3 still passes the predicate for the reason it was built to.
5. **Anything else `09d2cb9` touched.** The contract description grew again;
   two contract tokens were rebound after `contract_token_uniqueness` flagged
   a stale 0x match and an ambiguous 2x match.

## MANDATORY: code introspection is not optional

Open the source; cite `file:line`; mark anything you cannot verify as
`UNVERIFIED`; end with a receipts list splitting source-verified from
reasoned-alone.

## Sandbox limits — do NOT report these as findings

No network, no writable temp dir. Implementer's CLAIMS, treat as unverified
rather than re-reporting:

- `mise run lint` rc=0; `mise run lint-docs` rc=0
- `pytest tests/` → 1378 passed, 4 deselected, rc=0
- `dotfiles-setup verify run` → 115 passed, 0 failed, 4 skipped
- Mutation arms: dropping the `queued_prompt` term fails 5 tests including the
  end-to-end delivery arm; deleting the fresh pid guard fails
  `test_execute_respawn_skips_when_pid_alive_now` (i.e. it is re-armed).
- #604 exists and is a sub-issue of #556.

## Output format

Open with a **v5 → v6 disposition table**. Then findings: severity,
`file:line`, what, why it matters, verified-by. End with a per-severity count,
an explicit `SHIP` / `DO NOT SHIP`, and the receipts list.

A clean SHIP with zero findings is acceptable and useful — six rounds in, an
honest "I cannot break this further" is a real result. Do not manufacture
findings. But a way for this watchdog to either respawn an escalation or stop
recovering silently outranks everything else, so look for those first.


---

## Brief v7 — what the reviewer was asked, verbatim

# Review brief v7 — #601 close-out. BOUNDED TASK, not open hunting.

**Read this section before anything else. This brief is deliberately shaped
differently from v1–v6, and following the old shape would be wrong.**

Your previous six rounds found real defects — three HIGH, all genuine. But the
loop did not converge, and the reason is now understood:

- Each round reviewed a **different program**, because the implementer changed
  production behaviour in response to each round.
- Every HIGH was **the same shape**: a reachable combination of
  `state × needs × queuedPrompt × pid_alive` that nobody had enumerated. Round
  5 found `blocked+needs+queued+dead`. Round 6 found the same with `alive`.
  Each fix made a new cell reachable, and the next round walked into it.
- The briefs asked "what is broken", which has no completion criterion.

So this round has a **bounded task with a definite end**, and a **stop
condition**. Do not treat it as another hunt.

## The artifact under review

`tests/test_dag_tick.py` now contains `_CLASSIFY_TABLE`: the four
class-deciding axes crossed exhaustively — state-class × needs × queuedPrompt
× pid_alive, **32 rows** — with `tempo="idle"` and `state_age_s=None` pinning
WEDGED and the `--max-age` arm out of scope (both have their own tests).

Every expected value was derived by hand from intended semantics, then checked
against the code. All 32 agreed on the first run.

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles log origin/main..HEAD
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles show HEAD
```

## YOUR TASK — exactly three questions, nothing else

**1. Is any of the 32 expected values WRONG?**
Not "does the code produce it" — it does, they pass. The question is whether
the *decision* in each cell is the right one for this watchdog, judged against
`docs/receipts/565.md`, `575.md`, `578.md`, and the installed binary. Answer
per-cell only where you disagree; say "no disagreement" for the rest.

**2. Are the four axes the RIGHT axes — is there a fifth that changes a class?**
This is the question that would have prevented rounds 5 and 6. The table claims
`tempo` and age only matter for WEDGED/`--max-age`. If some other `state.json`
field, or some other value of an existing axis, can change a classification,
name it — that is a genuine gap in the enumeration. **If the four axes are
complete, say so explicitly; that is the answer that ends this.**

**3. Do the two meta-tests actually hold the table honest?**
`test_classify_truth_table_is_exhaustive` computes coverage from the axis
lists; `test_classify_truth_table_reaches_every_class_it_can` requires the
expected column to reach every reachable class. Can a degenerate or wrong
table still pass both?

## Explicit stop condition

**If your answer to (1) is "no cell is wrong", to (2) is "the four axes are
complete", and to (3) is "the meta-tests hold", then the correct verdict is
SHIP and the correct finding count is ZERO.** Say that plainly.

Do NOT:
- re-report findings from v1–v6 (all are fixed, or filed as #602 / #604);
- report anything about `execute_stop` (filed as #604, out of scope by your
  own v5 scoping);
- report sandbox limits (no network, no writable temp) as findings;
- report style, wording, or documentation issues — this round is about the
  table's correctness and completeness only;
- manufacture a finding to justify the round. Six rounds in, "this is correct
  and complete" is the most useful thing you can say if it is true.

If you find something genuinely outside these three questions that is HIGH
severity and would cause data loss or a silent recovery failure, report it —
but say explicitly that it is out of the brief's scope, and it will become a
ticket rather than another commit on this branch.

## MANDATORY: code introspection

Open the source; cite `file:line`. Mark anything you cannot verify as
`UNVERIFIED`.

## Output format

1. **Q1 verdict** — "no disagreement", or the specific cells and why.
2. **Q2 verdict** — "four axes complete", or the missing axis with evidence.
3. **Q3 verdict** — "meta-tests hold", or how a wrong table passes.
4. Per-severity count and an explicit `SHIP` / `DO NOT SHIP`.
5. Receipts: source-verified vs reasoned-alone.


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; #601, #602, #604 and map #556 read via `gh`.
