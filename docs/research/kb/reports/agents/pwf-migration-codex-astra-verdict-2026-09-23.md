> Persisted verbatim by the coordinator from `.agent/kb/raw/codex-astra-adversarial-critic-verdict-36037-1790212866.md` (codex `gpt-6-astra`, xhigh, read-only; the real codex run behind Brief D, which its Claude wrapper wrongly reported as timed out/empty). Session `a6750a24`, 2026-09-23.

# Adversarial critique: pwf 3.20.7 migration, Brief C

**Verdict: amend before implementation.** The chosen layout is workable, but the proposed selection, attestation, and closing workflow does not yet support it safely.

Reviewed against:

- [Brief C](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-migration-fable-synthesis-2026-09-23.md), SHA-256 `e46eaa692c63d34015b24894ae4c05649107d6cbe1a9d6dee8515923f93e99db`.
- [Report A](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-skills-inventory-2026-09-23.md), [Report B](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-plan-doctor-hooks-2026-09-23.md), and the third input, [attestation history](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/plan-attest-history-2026-09-23.md).
- Repository HEAD `875dfe26a40d108b02b0c4d2d946f60650513400`, current local planning files, and installed Claude/Codex pwf 3.20.7 source.

The current plan records that **root roadmap and archive placement are already accepted**; Q1 is deferred and Q4–Q6 remain unanswered. This critique preserves those decisions. [task_plan.md:602](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/task_plan.md:602)

## 1. Summary

The principal blockers are:

1. **`.active_plan` does not disambiguate multiple live slugs.** Both upstream resolvers require `PLAN_ID` before consulting the shared pointer in that case.
2. **The proposed root-attestation command can attest a slug instead.** `mise run plan-attest` forwards to the upstream selector; it has no “attest the program roadmap” operation.
3. **`plan-close` is underspecified and not atomic.** Clearing the pointer does not guarantee root selection, an inherited `PLAN_ID` survives closure, and ticket completion does not necessarily complete its parent program phase.
4. **Change 1 closes the measured initializer route, not every self-attestation route.** Its explanation of the Write-tool residual also misreads the cited permission documentation.
5. **The migration omits required consumer and gate changes.** These include generated Codex skills, root-shaped tests, explicit handling of the program versus ticket pointer, and ownership of goal-history iteration 032.

The stale-plan defect remains present now: live read-only probes returned **zero ledger entries, 2/19 phases complete, and Phase 2b as current**.

## 2. Omissions and dropped findings

### A. Attestation routes are not fully enumerated

There are **six concrete executable attestation entry surfaces** in the inspected design:

| Surface | Existing D4 coverage |
|---|---|
| `attest-plan.sh` | Named deny rules |
| `attest-plan.ps1` | Named deny rules |
| `mise run plan-attest` | Named deny rules |
| `dotfiles-setup plan-attest` | Named deny rules |
| `init-session.sh` | Missing |
| `init-session.ps1` | Missing |

Selection adds **two separate surfaces**, `set-active-plan.sh` and `.ps1`; only the shell version appears in the existing deny bases. Direct digest writes and programmatic calls are additional mechanisms, so six is **not an exhaustive count of arbitrary ways to self-attest**. [settings.json:31](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:31) · [hook_selfcheck.py:756](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_selfcheck.py:756)

The wrapper itself performs no caller authorization:

```python
completed = subprocess.run(["sh", str(script), *args], check=False)
```

Its boundary depends on the invoking harness. Importing and invoking the Python function is not the same command string as invoking the denied CLI. [plan_attest.py:166](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plan_attest.py:166)

**Dropped requirement:** enumerate and test the actual mechanisms for both harnesses. Adding filenames to `_ATTEST_DENY_BASES` proves rule presence, not exhaustive enforcement. New `plan-init` and `plan-close` entry points also need coverage beneath their mise wrappers.

### B. Per-session binding was dropped from the workflow

Report A explicitly says multiple named plans require a session’s own `PLAN_ID`; it recommends pinned sessions or separate worktrees. Brief C instead recommends the shared `.active_plan` and diagnoses ambiguity only when that pointer is absent. [Report A:132](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-skills-inventory-2026-09-23.md:132)

This omission affects more than injection:

- `ledger-append.sh` falls back to `.` when resolution returns empty and no explicit selector exists.
- `ledger-summary.sh` similarly falls back to root.
- Thus two unpinned slugs can produce **refused injection but root ledger writes or root status output**. [ledger-append.sh:47](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/ledger-append.sh:47) · [ledger-summary.sh:61](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/ledger-summary.sh:61)

`--agent <lane>` selects a ledger filename; it does not bind that ledger to the intended plan.

### C. Codex hook parity is incomplete

The live configuration has two distinct paths:

- The repository’s [.codex/hooks.json:35](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/hooks.json:35) already runs the shared doctor at SessionStart.
- The globally enabled pwf plugin registers seven events: SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, PreCompact, and Stop. Trust records exist, but their presence alone does not verify a current hook fire. [config.toml:257](/Users/rmanaloto/.codex/config.toml:257) · [codex-hooks.json:4](/Users/rmanaloto/.codex/plugins/cache/planning-with-files/planning-with-files/3.20.7/hooks/codex-hooks.json:4)

`codex_lane` applies `PLANNING_DISABLED=1`; both `sdlc_team` spawn sites currently omit `env=`. Brief C correctly identifies that defect. [codex_lane.py:463](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/codex_lane.py:463) · [sdlc_team.py:805](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sdlc_team.py:805) · [sdlc_team.py:961](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sdlc_team.py:961)

However:

- Disabling planning hooks does not prohibit explicit attestation commands or file writes.
- A doctor using `listing_budget.plugin_root` examines the **Claude cache**, while Codex runs its own installation and adapters. Healthy Claude injection cannot certify Codex injection. [listing_budget.py:149](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/listing_budget.py:149)
- Current Codex Stop code can emit a block in gated mode. Report A’s historical “Codex lanes are safe from forced continuation” statement is too broad for this installation. [stop.py:18](/Users/rmanaloto/.codex/plugins/cache/planning-with-files/planning-with-files/3.20.7/.codex/hooks/stop.py:18)

### D. No knowledge-base migration workstream is specified

Brief C names KB only for the coreutils issue. It provides no parallel migration, owner, dependency, or explicit deferral.

KB already has different semantics: its resume skill treats pwf as intra-round state subordinate to `next-ticket`, and its archive procedure moves the **whole directory**, then clears `.active_plan` only if it still names that directory. [KB session-resume:151](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/skills/session-resume/SKILL.md:151) · [KB plan-archive:16](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/skills/clear-prep/references/plan-archive.md:16)

That is a parity decision to document, not a reason to copy dotfiles’ task-authority model into KB.

### E. Consumers and contracts are incompletely covered

| Consumer or gate | Migration consequence |
|---|---|
| `plan_pointer.write` | Reads root `task_plan.md`; records the last `NEXT SESSION` heading. |
| `handoff_check._plan_findings` | Checks that root file against the tracked pointer; currently returns no plan finding when root is absent. |
| Handoff and resume skills | Read root plan, pointer, and root-oriented recovery instructions. |
| Generated `.agents/skills` copies | Must be regenerated when the Claude skills change. |
| Session review | Validates goal-history structure, digest chain, and append-only history. |
| Root-oriented tests | Must change with the reader contract, alongside slug and missing-plan controls. |

Sources: [plan_pointer.py:17](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plan_pointer.py:17), [handoff_check.py:215](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py:215), [skills_mirror.py:310](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/skills_mirror.py:310), [session_review.py:481](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:481).

Adding `plan_id` to one pointer does not resolve **which authority it certifies**: the program roadmap, the selected ticket, or both. A slug pointer alone cannot detect an unrecorded root-roadmap change.

### F. Doctor limitations and side effects were compressed away

Report B explicitly records:

- The shell doctor can pass while the Python injection twin is defective.
- Diagnostic fires update regression markers; they are not entirely read-only.
- The dispatcher variant also affects turn-marker state.
- A bounded timeout is required. [Report B:28](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-plan-doctor-hooks-2026-09-23.md:28) · [Report B:139](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-plan-doctor-hooks-2026-09-23.md:139)

Brief C needs to choose the actual probe and state what it certifies. “Dark hooks” is broader than “the selected injection producer returned output.”

### Findings that were **not** dropped

Brief C already preserves ledger behavior under `PLANNING_DISABLED`, rejects `/plan-loop` and `/plan-goal`, retains autonomous mode, and summarizes most gated-mode objections.

Two corrections remain:

- “Never mid-session” attestation in C §4 conflicts with Report A’s **phase-boundary** cadence when a session crosses several phases.
- C groups `start` with model-invocable commands, but Report A records `start.md` as `disable-model-invocation: true`. [Brief C:50](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-migration-fable-synthesis-2026-09-23.md:50) · [Report A:70](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/pwf-skills-inventory-2026-09-23.md:70)

## 3. Code contradictions and replays

### C1 — HIGH: A shared pointer cannot select among multiple live slugs

The shell resolver does this **before** consulting `.active_plan`:

```sh
[ "$PLAN_AMBIGUOUS" = "1" ] && exit 0
```

Only afterward does it call `resolve_from_active_file`. [resolve-plan-dir.sh:339](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/resolve-plan-dir.sh:339)

The Python twin agrees:

```python
if plan_is_ambiguous(fs_root, pin if pin else "."):
    return ("", "")
```

[ inject-plan.py:1381 ](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/inject-plan.py:1381)

**Replay:** two live slugs, `.active_plan=A`, no `PLAN_ID` → refusal, not A and not newest-mtime selection.

**Control:** explicit valid `PLAN_ID=A` takes the binding branch. One live slug without a pin remains eligible for fallback selection.

### C2 — HIGH: Root edits are not necessarily followed by root attestation

The attester accepts the resolved slug before considering `./task_plan.md`. The local wrapper forwards arguments without selecting root. [attest-plan.sh:44](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/attest-plan.sh:44) · [plan_attest.py:187](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plan_attest.py:187)

**Replay:** edit the program roadmap while ticket A is selected; run the proposed `! mise run plan-attest` → A is attested. The root edit remains unattested.

**Control:** with no eligible slug or explicit selector, the attester’s root fallback works.

This also breaks `plan-close`’s assumption that clearing `.active_plan` means its following attestation targets root.

### C3 — HIGH: Rename-only archival is not universally inert

Newest-directory selection requires `task_plan.md`. Explicit `PLAN_ID` and pointer selection require only a valid directory. [resolve-plan-dir.sh:254](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/resolve-plan-dir.sh:254)

**Live replay:** setting `PLAN_ID` to the existing archived Graphify directory returned that directory at rc=0, despite its containing only `task_plan.archived.md`.

Injection subsequently checks for `task_plan.md` and exits. [inject-plan.py:905](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/inject-plan.py:905)

Therefore:

- C’s “already inert” is true for the unpinned newest-directory scan only.
- Closing a plan must address retained session pins and stale pointers.
- A child command cannot unset the invoking session’s environment.

### C4 — MEDIUM: Initializer lifecycle is already implemented, and matters

Brief C leaves pointer creation and existing-slug behavior unverified. The code answers both:

- Existing names gain `-2`, `-3`, etc.
- Initialization writes `.active_plan`.
- It selects the new plan **before** mode setup and attestation.
- Attestation failure is reported, but `apply_v3_mode` returns success. [init-session.sh:454](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/init-session.sh:454) · [init-session.sh:244](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/init-session.sh:244)

**Replay:** repeat `plan-init foo` → a new suffixed plan, not necessarily the existing foo. Fail attestation → selection may already have changed.

The wrapper must capture the actual ID and verify final state. Script rc=0 alone is insufficient.

### C5 — MEDIUM: The claimed Write-tool residual misreads the cited docs

C §3.1 infers that ignored `Write(path)` rules leave Write unprotected.

The vendored permission documentation instead says:

> `Edit` rules apply to all built-in tools that edit files.

It explicitly directs users to substitute `Edit(path)` for `Write(path)`. [permissions.md:334](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/permissions.md:334)

**Replay:** an ignored rule named `Write(path)` does not establish that Write bypasses a correctly configured `Edit(path)` deny.

The actual documented residual is **indirect arbitrary subprocess I/O**. Live harness enforcement remains unprobed here; that should be tested separately rather than assuming a fail-open hook is necessary.

### C6 — HIGH: Changing the pointer parser does not fix pwf’s phase selection

C change 4 attributes F2 to competing heading conventions and replaces `NEXT SESSION` with `Current Phase`.

But the ledger walks `### Phase` headings and selects the first associated `**Status:** in_progress`. It never consults `## Current Phase`. [ledger-summary.sh:114](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/ledger-summary.sh:114)

**Replay:** change only the pointer parser → pointer says Phase 11, ledger still says Phase 2b.

Change 7 can repair the data, but change 4 does not close F2. Agreement between `Current Phase` and the status-bearing phases also remains an unenforced invariant.

### C7 — HIGH: “Close must be atomic” has no supporting mechanism

The upstream selector atomically replaces **one pointer file**. It does not transact archival, pointer removal, root status changes, root attestation, and tracked-pointer refresh. [set-active-plan.sh:351](/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7/scripts/set-active-plan.sh:351)

**Replay:** archive A, clear its pointer, leave live B → B becomes eligible; a following ordinary attestation can bless B rather than root.

There is also no defined mapping from “ticket complete” to “root phase complete.” Phase 11 contains multiple tickets. Closing one cannot blindly flip Phase 11 to complete.

## 4. Defect closure by ordered change

| Change | Closure verdict | Required correction or missing assumption |
|---|---|---|
| **1. Deny initializer and state writes** | **Closes A-F1’s measured initializer route if enforced; partial overall.** | Cover selection `.ps1`, new wrapper/CLI surfaces, and Codex enforcement. Correct the Write explanation. Include `hook_guard.py` in scope if a hook is actually added. Presence checks alone cannot certify enforcement. |
| **2. SDLC scrub + precheck** | **Closes hook inheritance; precheck underspecified.** | Both spawn sites are correctly identified. Bind the check to the intended project, plan ID, and bytes; reject missing/ambiguous state. Specify freshness at the actual child launch. Scrubbing is not write protection. |
| **3. `plan-status`** | **Useful diagnostic; closes neither F1 nor F2 by itself.** | Resolve once and pass the same identity to all readers. Distinguish missing, ambiguous, archived, unattested, and mismatched states. `check-complete.sh` returns empty under `PLANNING_DISABLED=1`, whereas ledger-summary still reports—observed live. |
| **4. Pointer/handoff migration** | **Necessary compatibility change; does not close A-F2.** | Define root versus ticket authority and pointer schema. Update root-shaped tests and the missing-root behavior. Do not equate a valid digest with an injectable plan. |
| **5. Init/close/log wrappers** | **Not ready for implementation.** | Resolve naming collisions, failed-init recovery, actual plan ID, root attestation, session pin removal, conditional pointer clearing, parent-phase completion, and ledger binding. New CLI wiring also belongs in `main.py`; existing passthrough repair is explicitly limited to `plan-attest`. |
| **6. Doctor check** | **Closes a bounded subset of B’s dark-output defect.** | Choose shell, Claude dispatcher, or Codex adapter explicitly. Separate intentional-disable, healthy, and genuine-dark test arms. A disabled outer wrapper must skip; a disabled producer can be an inner-probe fixture. FAIL-only parsing does not detect every unusable installation. |
| **7. Migrate plan** | **Can close A-F2, subject to preservation and verification.** | Preserve all live obligations; establish consistent phase statuses; publish durable decisions and iteration 032; refresh pointer; attest the intended root; verify actual injection. |
| **8. Move old directory** | **Safe cleanup only with selector checks.** | It is currently excluded from automatic selection, but still resolves through explicit `PLAN_ID`. Check references and pins before moving it. |
| **9. Skill edits** | **Required, incomplete file scope.** | Regenerate `.agents/skills` counterparts. Reconcile root/slug findings and progress paths. Replace “never mid-session” with the agreed phase-boundary cadence. |

### Gates and tests the proposal must account for

- **Definite mirror failure:** editing only the two Claude skills leaves generated counterparts stale. `skills_mirror_parity` runs in hk. [hk.pkl:712](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl:712)
- **Definite reader incompatibility without change 4:** the proposed root shape lacks the `NEXT SESSION` heading required by current readers. Tests explicitly pin that behavior and the exact three-field pointer payload. [test_plan_pointer.py:22](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_plan_pointer.py:22) · [test_handoff_check.py:116](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_handoff_check.py:116)
- **Potential formatting-induced contract failure:** `workflow.plan-pointer-wiring` requires the literal `mise run plan-pointer` immediately before a closing code fence. Appending commands inside that fence changes the required token. [suites.toml:1708](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1708)
- **False confidence from existing D4 tests:** they enumerate `_ATTEST_DENY_BASES`; they do not independently discover omitted routes. [test_plan_attest.py:84](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_plan_attest.py:84)
- **Root-mode floor:** the inspected contracts mention the historical floor defect, but do not execute an upstream root/slug floor matrix. The lane-isolation contract binds environment wiring, not resolver behavior. [suites.toml:1869](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1869)

### Change 7 is several operations, not one move

The file is now **1,647 lines**, so “archive the 1,640-line file” must mean the exact current bytes, not a stale snapshot.

The transition needs distinct, verifiable outcomes:

1. Preserve the old plan bytes.
2. Install the short roadmap with every remaining obligation accounted for.
3. Promote durable rulings and traps.
4. Append a valid goal-history iteration.
5. Reconcile selection and session pins.
6. Refresh the tracked pointer and attest the intended root.
7. Verify phase and injection agreement.

The existing archive explicitly says several older issues remain open; retaining only Phases 10 and 11 without mapping those obligations risks dropping live work. [task_plan.md:619](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/task_plan.md:619)

**If `.active_plan` was unset:** the file move does not create one. With no eligible slug and no explicit pin, callers can use root fallback. With one eligible slug, that slug shadows root; with multiple, ambiguity applies.

**Who writes 032?** No inspected initializer, attester, or pointer task writes it. Assign the coordinating writer explicitly. It is an **iteration**, not a phase, and needs the required fields, prior/current goal digests, current goal text, evidence, disposition, topology/ownership, and Mermaid workflow. Existing entries must remain byte-preserved. [goal-history rule:3](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/goal-history.md:3) · [session_review.py:538](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:538)

## 5. Control arms and verification limits

| Claim checked | Subject and control | Result |
|---|---|---|
| Current phase view is stale | Actual installed `ledger-summary.sh` against current root | rc=0; zero entries; `2/19 complete`; Phase 2b |
| Completion output respects disable | Same `check-complete.sh task_plan.md`, disabled versus unset | Both rc=0; disabled empty, unset reports 2 complete / 2 in progress / 3 pending |
| Ledger remains readable when disabled | Explicit `PLANNING_DISABLED=1` | rc=0; same stale ledger block |
| Archived directory can still resolve | Explicit existing archived ID versus nonexistent ID | Both rc=0; existing directory emitted, nonexistent ID empty |
| Resolver output is not root-plan existence | No pin, no active pointer, archived-only slug tree | rc=0, empty output despite root plan existing |
| Multiple-slug pointer claim | Shell ambiguity branch compared with Python twin and explicit-ID branch | Both sources reject ambiguity before reading shared pointer |
| Write-rule claim | Proposal compared with its cited repository rule and vendored permission docs | Documentation contradicts the claimed Write residual |
| Mirror omission | Proposed two-file edits compared with generator and hk call site | Generated counterparts are mandatory |
| Current identities | Direct SHA-256 reads | Plan `4dd740b2…`; tracked pointer `421e1562…`; attestation `dc4b9265…`: three different states |

The multiple-plan, initializer-failure, and close scenarios above are **source replays**, not newly executed filesystem mutations. Report A’s self-attestation experiment was not repeated.

Both required Graphify queries failed under the read-only sandbox. A read-only Python probe through `uv` also failed because it required a temporary file. Consequently, no pytest/verify success or live permission-engine enforcement is claimed. No files were changed; this report is returned here because persistence was unavailable.


## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed 3.20.7 Claude + Codex plugin source
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — settings, python modules, tests, suites.toml, skills
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — session-resume + clear-prep skills, vendored permissions.md

_(section appended by the coordinator from the citations above)_
