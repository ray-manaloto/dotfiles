> Persisted verbatim by the coordinator from `/tmp/pwf-migration-spec-astra-review-49026-1790218005.md` (codex `gpt-6-astra`, xhigh, read-only, pid 49038, ~22 min; Brief H). Its haiku wrapper reported this run as "timed out / 0 bytes" at ~11-15 min — the THIRD such misreport this session.

**Verdict: revise before publishing as `ready-for-agent`.** The draft substantially preserves Ray’s final rulings and correctly retires D4. Its principal problems are contradictory lifecycle requirements, incomplete selection handling, and verification claims that exceed what the existing code proves.

References below use **S** for the [spec draft](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-migration-spec-draft-2026-09-23.md), **D** for the [final design](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-migration-fable-round3-2026-09-23.md), **P** for the installed Claude pwf `3.20.7` directory, and **KB** for the knowledge-base repository.

## 1. Executive summary

The draft gets the major decisions right:

- Attestation is tamper detection, not proof of human approval.
- Agents may create and attest plans using upstream behavior.
- Completed tickets may be closed by the model.
- Shared implementation belongs in `kb_setup`.
- `sdlc_team` retains planning; `codex_lane` retains its scrub until Phase 10.
- Round 6’s later goal-history iteration correctly supersedes round 5’s original iteration-032 wording.
- `plan init` warning instead of refusal is faithful to **D:17–19**. It is not a silent deviation from the final design.

The strongest blockers are:

1. Closing a ticket deliberately creates states that status and handoff do not clearly permit.
2. Root-only handoffs require logging through a command that expressly refuses root-only operation.
3. One live slug does not always avoid upstream ambiguity.
4. Fresh worktrees lack the required, gitignored root roadmap.
5. Task routing, alias retirement, and retained contracts prescribe incompatible outcomes.

**Evidence limits:** this was a read-only review. Graphify failed because its command needed a temporary write; source inspection followed. The `uv` probe also failed on cache access. No pytest, mutation suite, lifecycle mutation, or credential-read control is reported as executed. I performed no filesystem writes.

The reviewed draft remained at SHA-256:

```text
d4ff3fa728883eff74d93657e7377680a56894b0afffbd8cd43251ee77e4ffc5
```

Read-only upstream probes did execute:

| Probe | Result |
|---|---|
| `check-complete.sh`, planning enabled | rc=0; `Task in progress (2/19 phases complete)` |
| Same script with `PLANNING_DISABLED=1` | rc=0; empty output |
| `ledger-summary.sh .` with `PLANNING_DISABLED=1` | rc=0; names `### Phase 2b: 2026-09-10 grilling outcomes — cleanup PR + codex substrate` |
| Resolver with existing leftover slug whose plan was renamed | rc=0; returns its directory despite missing `task_plan.md` |
| Resolver with nonexistent explicit `PLAN_ID` | rc=0; empty output |

These results matter because **empty output, successful exit, selected directory, and valid plan are distinct states**.

## 2. Rulings checklist

| Round | Assessment | Evidence |
|---|---|---|
| 1 | **Carried.** Short root roadmap, ticket plans, ignored archive plus tracked extract. Hidden archive correctly follows the later ruling. | `task_plan.md:602–608`; S:321–337, 465–479 |
| 2 | **Substantially carried.** Upstream-first, per-worktree binding, shared implementation with profiles. Operator hardening correctly superseded. Shared-workflow enforcement remains incomplete. | `task_plan.md:609–620`; S:339–390; finding F8 |
| 3 | **Carried, with a lifecycle contradiction.** Shared package now, hidden archive, completion-based close, pointer untouched. Operator-only force correctly superseded. | `task_plan.md:621–625`; S:371–377; F1 |
| 4 | **Correct posture; incomplete retirement inventory.** D4 is explicitly superseded. Some active instructions and tests remain unnamed. | `task_plan.md:626–635`; S:297–319; F6 |
| 5 | **Carried.** Workers see plans, Phase 10 split, KB confirmation before closing the old round. Later goal-history scheduling correctly follows round 6. | `task_plan.md:636–640`; S:426–487 |
| 6 | **Carried.** Advisory scrub retained, thin initializer with pinning, layered implementation, check at dispatch, Phase 10 supersession, later goal-history iteration. Runtime binding still needs acceptance evidence. | `task_plan.md:642–651`; S:406–479; F15 |

**F16 — LOW — The issue-level dependency ruling was dropped.**

- **Evidence:** `task_plan.md:593` says: **“It precedes #1327 and absorbs #910.”** Neither relationship appears in S’s dependencies at 570–584.
- **Probe:** Compared the addendum with the draft’s dependency section; searched the draft for both issue numbers.
- **Control arm:** Internal ordering such as T2 → dependency pin → T3 is already present and must remain.
- **Required correction:** Carry the two issue relationships explicitly; do not infer them from “Phase 11 first priority.”

## 3. Omissions — checklist 7–11

### 7. Attestation and self-attestation routes

The old security concern must not be resurrected. Direct attesters, initializer auto-attestation, wrapper calls, and writable digests are consistent with the newly adopted trust model.

Relevant routes include:

- `P/scripts/attest-plan.sh`
- `P/scripts/attest-plan.ps1`
- `P/scripts/init-session.sh:226–235`
- `P/scripts/init-session.ps1:456–477`
- `dotfiles-setup plan-attest`
- `mise run plan-attest`
- The proposed `kb-setup plan attest`

Upstream’s `commands/plan-attest.md` retains `disable-model-invocation: true`. Removing local denies does not change that slash command’s invocation metadata; model access through the wrapper remains a separate route.

**F6 — MEDIUM — T1 omits an active human-only instruction and the tests importing its deleted selfcheck.**

- **Evidence:** [.claude/rules/mise-tasks-only.md:31](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/mise-tasks-only.md:31) still says:

  > **nothing an agent may run** — attestation is a HUMAN boundary and `permissions.deny` blocks every model route.

  `tests/test_plan_attest.py:19–22` imports `_ATTEST_DENY_BASES` and `check_plan_attest_deny`. D:56 explicitly retires the deny tests; S does not carry that deletion with equal specificity.
- **Probe:** Read the active rule, imports, and tests against the retirement list.
- **Control arm:** Preserve resolver and passthrough coverage, including `test_the_separator_is_inserted_only_where_it_is_needed`.
- **Required correction:** Name the rule, imports, and four retiring tests:

```text
test_the_live_settings_deny_every_attestation_route
test_both_forms_are_denied_for_every_route
test_the_deny_check_notices_a_half_written_ban
test_an_unreadable_settings_file_fails_rather_than_passing
```

Deleting the selfcheck functions without those imports would break collection.

### 8. Codex hooks

The draft correctly counts all seven installed Codex events:

```text
SessionStart
UserPromptSubmit
PreToolUse
PermissionRequest
PostToolUse
PreCompact
Stop
```

Evidence: installed Codex `hooks/codex-hooks.json:4–89`. The existing repository doctor mirror is `.codex/hooks.json:35–45`. No omitted eighth event was found.

Trust records establish configuration, not a successful current hook fire. S:562 expressly defers a Codex adapter canary; therefore the claimed verification scope must remain **Claude dispatcher health plus Codex configuration**, not proven Codex injection.

**F3 — HIGH — One live slug does not guarantee unambiguous main-clone selection.**

- **Evidence:** S:341–342 says one live slug means the resolver “never reaches its ambiguity branch.” But `P/scripts/resolve-plan-dir.sh:343–354` includes:

```sh
if [ -d "${PLAN_ROOT}/sessions" ] && [ -f "${PWF_ROOT_PIN:-.}/task_plan.md" ]; then
    PLAN_COUNT=1
fi
```

  A root roadmap plus one live slug therefore exceeds one when session isolation is armed.
- **Probe:** Source replay of the count and `PWF_PLAN_AMBIGUOUS_V1` branch. The current checkout lacks `.planning/sessions/`; this is a supported-state counterexample, not a claim that the current checkout exhibits it.
- **Control arm:** Same root and slug with no sessions directory remains the ordinary single-slug case; explicit valid `PLAN_ID` bypasses this ambiguity count.
- **Required correction:** Define the supported disposition of session-isolation state and add this fixture. Preserve upstream behavior.

### 9. Tests and contracts pinning root assumptions

**F5 — HIGH — Task routing and alias retirement conflict with retained contract requirements.**

- **Evidence:** S:403–404 says aliases become re-exports “until deleted once the pin lands,” while their public registrations remain contract-bound. S:408 routes tasks directly to `kb-setup plan`. However, [workflow.plan-pointer-wiring](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1708) requires these exact tokens:

```text
dotfiles-setup plan-pointer'
"plan-pointer",
"plan-pointer": lambda: sys.exit(
def main(
def test_public_cli_registers_plan_pointer(
mise run plan-pointer\n```
```

  The contract protects considerably more than the handoff fence.
- **Probe:** Compared S’s routing and deletion instructions against `suites.toml:1708–1733`.
- **Control arm:** A retained alias with corresponding registration and updated task contract can be coherent; deleting that alias while retaining its required tokens cannot.
- **Required correction:** Specify the final compatibility surface and explicitly migrate the whole contract.

A second contract needs disposition: `workflow.codex-lane-planning-isolation` must preserve its scrub behavior, but `suites.toml:1892` also pins this root-only row:

```text
| Phases, checkboxes, current phase, distilled decisions | `task_plan.md` | **coordinator ONLY** |
```

S:456–458 changes that table to resolved-directory semantics while S:535 calls the contract “unchanged.” Preserve the isolation guarantee; reconcile its documentation token.

The implementation checklist should explicitly account for:

| Existing test or contract | Required disposition |
|---|---|
| `test_last_next_session_heading_is_the_only_recorded_phase` | Replace old heading and flat-payload expectation |
| `test_missing_active_heading_fails_without_writing_a_pointer` | Retain failure semantics under new phase grammar |
| `test_public_cli_registers_plan_pointer` | Retain or retire consistently with alias decision |
| `test_plan_without_next_session_heading_is_missing_active_plan` | Replace old convention |
| `test_pointer_stale_after_plan_bytes_change` | Preserve with two authorities |
| `test_plan_without_pointer_is_reported` | Define root-only and ticket states |
| `test_fresh_clone_without_plan_has_no_active_plan_finding` | Change for root-roadmap profile |
| `test_main_prints_explicit_no_handoff_state` | Reconcile default CLI behavior |
| `workflow.plan-attest-operator-only` | Delete |
| `workflow.plan-pointer-wiring` | Migrate beyond its fence token |
| `workflow.codex-lane-planning-isolation` | Preserve behavior; reconcile table token |
| `workflow.goal-history` | Preserve append-only and field requirements |

Evidence: `tests/test_plan_pointer.py:22–53`, `tests/test_handoff_check.py:116–166,332–341`, and the named suites.

### 10. Consumers beyond the implementation modules

Verified consumers include the mise tasks, public CLI registrations, handoff/resume skills, verification skill, session-review skill, session-review implementation, contracts, tests, and generated skill copies.

`session_state.py` does not currently consume plan pointers or goal history; it should not acquire speculative changes merely because it was an input to this review.

**F7 — MEDIUM — The consumer inventory misses active root-writing instructions and a public handoff bypass.**

- **Evidence:** `.claude/rules/notepad-enforcement.md:8` directs discoveries to root `findings.md`; `.claude/rules/agent-artifact-conventions.md:76` repeats that instruction. Neither is named in S’s T7 inventory. Separately, `handoff_check.py:295–301` returns success before checking plans when no handoff exists:

```python
if handoff is None:
    ...
    return 0
```

  Its later output at 313–316 still says `"active-plan checks skipped"` when the root is missing.
- **Probe:** Followed the public `main()` path, rather than only `_plan_findings()`, and searched active instructions for root findings ownership.
- **Control arm:** A profile without a root roadmap must not produce `MISSING_ROOT_PLAN`; unrelated handoff prose failures must retain their existing behavior.
- **Required correction:** Specify the no-handoff/root-required result and test the public CLI. Update both active findings rules.

Also include `.claude/skills/verify/SKILL.md:18` and `.claude/skills/session-review/SKILL.md:71–88` in the consumer review. Their handoff and goal-history checks are external callers, not implementation internals.

### 11. Knowledge-base parity

The draft includes the root `.mode` floor, removal of the `3.12.0` literal, archive-reference replacement, shared close, old-round confirmation, and no new deny set.

**F8 — MEDIUM — “One workflow” lacks both a content-sharing mechanism and a disposition for KB’s existing lifecycle rules.**

- **Evidence:** S:154 promises “Same tasks, same skill text via rule-sync.” But `rule_sync.py:133–163` checks plugin presence, selected lines, and rule names—not equality or generation of skill text. KB’s resume skill currently says:

  > **Report it; do not archive it.**

  It also gives the user’s task and `next-ticket` precedence over the previous plan (`KB/.claude/skills/session-resume/SKILL.md:157–167`). KB clear-prep archives only after `"/clear now"` and only when done (`:433–440`). S:483–485 says resume and clear-prep call status and close without assigning these existing behaviors a disposition.
- **Probe:** Read the gate implementation and both lifecycle skills.
- **Control arm:** An incomplete plan must remain available across clear/resume; a previous round’s next step must not override a newly selected ticket.
- **Required correction:** Define shared implementation versus repository-specific invocation policy. Preserve or explicitly replace the existing archive triggers and task precedence. Narrow the `rule-sync` claim unless an actual content-sharing mechanism is supplied.

## 4. Contradictions — checklist 12–15

### 12. T1–T10 outcomes against code

| Change | Assessment |
|---|---|
| T1 retirement | Correct direction; omitted active rule/test imports and underspecified regression contract: F6, F9 |
| T2 shared CLI | Correct location; lifecycle, selection, and metadata gaps: F1–F3, F14 |
| T3 readers | Required migration identified; public CLI bypass and existing contract need coverage: F5, F7 |
| T4 tasks | Direct shared routing conflicts with alias/contract wording: F5 |
| T5 doctor | Dispatcher/function seam is reasonable; does not prove Codex adapter injection |
| T6 workers | Existing code already inherits environment; new guarantee and refusal matrix remain future work: F12 |
| T7 documentation | Named surfaces are incomplete; `rule-sync` cannot ensure shared skill text: F6–F8 |
| T8 migration | Most outcomes concrete; “pointer absent or stale” conflicts with clean-state expectations: F1 |
| T9 KB parity | Correct workstream, incomplete lifecycle integration: F8 |
| T10 upstream asks | Both asks carried; correctly non-blocking |

**F1 — HIGH — Successful close has no defined clean terminal state.**

- **Evidence:** S:371–377 requires preserving the active pointer after moving its target into the archive. S:358–365 reports `STALE_POINTER` and `ARCHIVED_REFERENCED`, with nonzero exit for any non-clean state. S:476 expressly permits an absent **or stale** pointer immediately before requiring clean verification.
- **Probe:** Replayed the specified transition: live A → archive A, leave pointer A → stale/archive reference. Compared that result with status, doctor, and handoff acceptance.
- **Control arm:** Root-only state with no pointer or pin can be clean; a stale explicit `PLAN_ID` must remain distinguishable from an intentionally retained pointer.
- **Required correction:** Define whether an expected retired pointer is informational or non-clean, including exit codes and handoff behavior. Do not resolve this by silently violating the ruling that close leaves the pointer untouched.

**F2 — HIGH — Root-only handoff requires a ledger operation that the CLI forbids.**

- **Evidence:** S:446–448 unconditionally requires a handoff ledger note. S:378–380 requires `log` to refuse empty resolution and “never the root-directory fallback.” S:476 deliberately establishes a root-only state with no live slug.
- **Probe:** Followed that supported state through the specified handoff sequence; read upstream ledger fallback at `P/scripts/ledger-append.sh:47–64`.
- **Control arm:** A bound live ticket must receive its own ledger event; ambiguous selection must never log into an arbitrary ticket.
- **Required correction:** Specify an explicit root logging operation or conditionally omit ticket logging when `ticket=null`. Define “both MATCH” for that same state.

**F10 — MEDIUM — The draft overstates when upstream resolves or attests the root.**

- **Evidence:** S:373–374 says a stale pointer falls through to the roadmap, while its own probe at S:27–29 says the resolver selected the remaining live slug. Upstream tries the active pointer and then newest live directory at `resolve-plan-dir.sh:367–368`. S:460–462 also says root-mode `/pwf` re-attests the roadmap. `init-session.sh:235` clears selectors but then invokes the ordinary attester, which still prefers a live slug.
- **Probe:** Traced initializer → attester → resolver. The draft’s recorded archive probe independently contradicts its unconditional root-fallback wording.
- **Control arm:** No live slug and no explicit binding permits root fallback. A remaining live slug does not.
- **Required correction:** Make the conditions explicit. Describe `/pwf` as allowed upstream behavior without promising it always refreshes the roadmap attestation.

Also, root `.mode` inheritance is a **policy floor**, not byte-for-byte copying: `init-session.sh:170–205` writes `autonomous` or `autonomous gate`, not the entire `autonomous inject-smart` line.

### 13. Deny retirement and regression prevention

The live D4 block contains exactly these eleven entries:

```text
Bash(*attest-plan.sh)
Bash(*attest-plan.sh *)
Bash(*attest-plan.ps1)
Bash(*attest-plan.ps1 *)
Bash(*set-active-plan.sh)
Bash(*set-active-plan.sh *)
Bash(mise run plan-attest)
Bash(mise run plan-attest *)
Bash(*mise run plan-attest *)
Bash(*dotfiles-setup plan-attest)
Bash(*dotfiles-setup plan-attest *)
```

Evidence: `.claude/settings.json:31–41`. Their presence today is expected before implementation; it is not itself a spec defect.

**F9 — MEDIUM — The proposed anti-deny contract does not specify coverage of the wrapper routes or its JSON scope.**

- **Evidence:** S:313–317 describes attest/selector **script** rules, and S:64 proposes `regex_forbid` “over the settings deny list.” Five current entries instead contain `plan-attest`. Existing `verify.py:446–482` scans whole files line by line; it does not select `permissions.deny`.
- **Probe:** Compared all eleven entries with the proposed script-oriented scope and inspected the handler. An illustrative `attest-plan|set-active-plan` matcher covers the six script entries but misses the five wrapper entries.
- **Control arm:** An allowed command or explanatory text containing the same names must not be mistaken for a deny; unrelated credential protections must remain accepted.
- **Required correction:** Specify route coverage, actual scope, and mutation cases for both script and wrapper spellings. One script-rule mutation does not prove the motivating D4 reversal is protected.

### 14. Mise descriptions

The current descriptions are old, as expected:

```text
OPERATOR ONLY: attest ...
```

Evidence: `mise.toml:997`, with the old caller at `:999`. S:297–319 and 408–410 explicitly require updating this posture. **No additional omission found here.**

### 15. Worker scrub prohibition

**F12 — MEDIUM — Environment inheritance is present, but the proposed worker guarantee and selection refusal matrix are incomplete.**

- **Evidence:** Both `sdlc_team.py:805–818` and `:961–968` call `subprocess.Popen` without `env=`. Thus they currently inherit both `PLAN_ID` **and an ambient `PLANNING_DISABLED=1`**. S:430 expects the child to lack the disable flag. S:431–434 defines attested, mismatched, and no-plan cases but not rejected bindings or ambiguity.
- **Probe:** Read both process boundaries; executed the resolver’s existing-directory and nonexistent-binding arms. The latter returns empty output at rc=0, which cannot alone establish “no plan.”
- **Control arm:** A truly plan-free repository may dispatch; a valid attested v3 plan may dispatch; neither should conceal an invalid explicit binding.
- **Required correction:** Define behavior for ambiguous selection, rejected pins, missing plan files, and inherited disable state. Test the real supervisor-to-worker chain. Retain round 6’s check location at dispatch; do not silently move it.

The **absence of a scrub exists today**. Its durable contract and refusal check are proposed future work.

## 5. Seams and testing — checklist 16–18

The proposed testing altitudes are mostly sensible, but “two behavioral seams” describes two ownership groups, not two entry points.

| Actual boundary | Appropriate evidence |
|---|---|
| Shared `kb-setup plan` CLI | Real scripts in disposable repositories |
| Handoff CLI | Public `main()` tests plus focused classification tests |
| Doctor check function | Assembled setup and real dispatcher canary |
| Dispatch function | Refusal tests with captured spawn |
| Supervisor/worker process boundary | Real child environment probe |
| Contracts and documentation | Verify, selfcheck, lint-docs, mirror and rule-sync gates |
| T8 migration | One-time recorded live verification |

**F11 — MEDIUM — The promised universal agreement between phase readers is false for supported inputs.**

- **Evidence:** S:220–223 and 397–399 describe a common phase rule. But `check-complete.sh:95–108` counts primary and inline statuses independently, taking their per-field maximum. `ledger-summary.sh:99–111` considers inline counts only when both primary complete and in-progress counts are zero. Only ledger-summary selects an active heading.
- **Probe:** Read both implementations. Executed `check-complete` with planning enabled and disabled, then ledger-summary with planning disabled: completion became empty while the ledger still reported phases and a heading.
- **Control arm:** A canonical primary-status plan, planning enabled, with exactly one active phase should produce matching counts and heading.
- **Required correction:** Bound the agreement claim to a defined canonical format and environment. Add mixed-format, multiple-active, no-phase, and disabled-planning cases. Do not claim the upstream scripts already implement one parser.

**F13 — MEDIUM — The host/CI test plan lacks a complete execution and fixture contract.**

- **Evidence:** S:37 says host tests skip when `$CI` is set. Actual `tests/conftest.py:31` skips only when:

```python
os.environ.get("CI") == "true"
```

  S:43–47 says real layouts were recorded, but provides no fixture location or receipt. S:509 says shared KB tests run through the ship gate; dotfiles’ `pr.py:327–330` runs its own `tests/`, not dependency tests. The doctor’s real-dispatcher test also needs an explicit host/CI disposition.
- **Probe:** Read conftest, the ship gate matrix, KB pytest configuration, and the draft’s fixture descriptions.
- **Control arm:** `CI=false` must not skip host tests. CI must still fail for deliberately malformed recorded state without an installed plugin.
- **Required correction:** Assign each test to a repository and gate; name fixture provenance and normalization of random nonce/timestamp fields; define missing-plugin behavior and the doctor test’s fixture twin.

Prior-art claims also need narrower wording:

- `test_the_documented_read_only_form_reaches_the_script` checks source wiring and parser output (`tests/test_plan_attest.py:168–187`); it does **not** execute mise or the script.
- Most handoff tests invoke `check()`. Public CLI coverage exists, but is not the altitude of the entire suite.
- The `codex_lane` real-child positive/control precedent is genuine.

The proposed live `mise run plan-attest -- --show` arm remains necessary after changing routing.

## 6. Implementability — checklist 19–20

**F4 — HIGH — Parallel worktrees have no specified bootstrap for their required root authority.**

- **Evidence:** S:339–345 prescribes ticket worktrees. S:387–400 makes the root roadmap mandatory for dotfiles. But `.gitignore:143–151` excludes the roadmap and root attestation. S:366 initializes only a slug; T8 installs the root only as a one-time migration.
- **Probe:** Inspected ignore rules and tracked-file membership. `.mode` is tracked; the root plan and attestation are not. No worktree-copy mechanism is supplied by the draft.
- **Control arm:** The migrated main checkout already has a root roadmap. The KB profile deliberately has no root authority and must remain supported.
- **Required correction:** Specify how a fresh worktree acquires and verifies its root roadmap, or explicitly define a different root-authority policy there. Otherwise the advertised worktree path begins in `MISSING_ROOT_PLAN`.

**F14 — MEDIUM — Several required CLI outputs depend on metadata and recovery rules the spec no longer supplies.**

- **Evidence:** S:375 requires a parent-phase reminder and count of other open tickets. The earlier revision required a ticket plan’s Goal to contain `#NNNN` (`revision:43`) and described its roadmap lookup (`:60`); S retains only a `ticket_ref` shape. S:387 says profiles come from a “declared baseline” without naming the carrier or override mechanism; the revision specified `[plan]` and `--config` (`:90`). S:372 requires a force-close reason but exposes no reason input.
- **Probe:** Compared the previous interface details with S’s CLI and profile definitions; inspected KB’s existing CLI.
- **Control arm:** A unique ticket reference mapped to one roadmap phase can yield a deterministic reminder. Missing or duplicate references must not silently manufacture a parent.
- **Required correction:** Define ticket identity storage, parent/open-ticket grammar, profile discovery and override, and force-reason input.

The same interface section should specify recovery after a partial close. Once the directory moves, an unchanged explicit pin no longer resolves; blindly rerunning a command whose first condition is `resolved id == id` cannot complete later cleanup.

**F15 — MEDIUM — Worktree pinning has no acceptance probe proving it reaches the relevant processes.**

- **Evidence:** S:343–345 writes the mise override and acknowledges the running shell retains its old binding. S:596–607 still lists environment propagation as unverified. The planned child test begins with `PLAN_ID` already supplied; it does not prove mise activation or a newly launched Claude/Codex session receives the pin.
- **Probe:** Compared the pin-write operation, process inheritance, and test preconditions. A child cannot update its already-running parent’s environment.
- **Control arm:** A fresh correctly activated process should receive the new binding; an already-running process must remain detectably stale until refreshed.
- **Required correction:** Add a bounded acceptance probe covering override write → activation/launch → observed binding, with a stale-process control. Environment inspection and actual hook attachment should be reported separately.

**F17 — LOW — Removing Seams will not make the issue body comply with its template.**

- **Evidence:** Brief G explicitly forbids file paths and code snippets in the spec body (`session-2026-09-23d-agent-briefs.md:168–169`); Brief H requires checking this (`:182–183`). S:321–337 contains concrete paths and S:394–396 contains the pointer schema.
- **Probe:** Compared the publication instruction at S:1–9 with the body remaining after Seams removal.
- **Control arm:** The implementation evidence may retain paths and schemas in a linked design artifact; the publication body must follow the selected template.
- **Required correction:** Perform a separate issue-body transformation rather than publishing the remainder verbatim.

**C1–C7 disposition:** C1 remains incomplete because session-isolation state is omitted; C2 is recognized but contradicted by the `/pwf` root-attestation claim; C3 correctly uses directory moves; C4 preserves collisions and post-state validation; C5’s D4-specific hardening is correctly superseded; C6 needs bounded parser agreement; C7 correctly abandons atomicity but still lacks clean terminal and recovery semantics.

## 7. GitHub repos touched

| Repository | Intended changes |
|---|---|
| `ray-manaloto/dotfiles` | D4 retirement, dependency pin, consumers, tasks, doctor, worker checks, skills/rules, contracts, tests, roadmap and tracked records |
| `ray-manaloto/knowledge-base` | Shared planning library/CLI, profile configuration, tests, tasks, mode floor, lifecycle skills and archive integration |
| `OthmanAdi/planning-with-files` | Two non-blocking issue requests: explicit root attestation target; Claude/Codex approval-gate analogue |

No GitHub mutation was performed. The draft should be revised around the lifecycle and interface contradictions before implementation tickets are marked ready.

