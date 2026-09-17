# codex SDLC team — review of the `/session-handoff` workflow (Phase 7, 2026-09-16), verbatim

Brief: `mise run sdlc-team` review mode, run `phase7-session-handoff-review-20260916`, spec `sdlc-review-session-handoff-spec.md` (copied below the report as an appendix); the generated prompt is `.agent/sdlc-runs/phase7-session-handoff-review-20260916/prompt.md`. Settlement: `completed`, 903 s (reconciliation line follows in the architect dispositions). Output copied verbatim; the architect's dispositions are appended at the tail.

---

# Phase 7 review verdict

**INCOMPLETE.** The workflow does not yet satisfy Ray’s six goals. The highest-risk defects are:

1. The handoff still duplicates task authority outside `task_plan.md`.
2. Two tests can overwrite the operator’s real session-review report.
3. Session-review artifacts are not generation-safe or transactionally published.
4. Current harness records create thousands of repetitive omissions without an actionable summary.
5. AgentsView and SDLC-team review are not named handoff steps.
6. Findings and automation candidates have no required disposition loop.

Three applicable specialists completed successfully. No files were modified, no gates were run, and no external state was changed. Graphify orientation was attempted first but returned `rc=1` because the read-only sandbox denied mise temporary-state creation.

## Typed findings

| Severity | Goal | Claim | File:line | Evidence |
|---|---|---|---|---|
| HIGH | G1 | Handoff and resume remain a second task authority. | [session-handoff skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-handoff/SKILL.md:3), [session-resume skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-resume/SKILL.md:3) | The workflow accepts or infers task text, stores it in memory and the handoff, prints it in the resume prompt, and verifies that it was recorded. Exact current `grep -c 'next task'` is 6; broader case/hyphen-aware probes found 11–12 references. |
| HIGH | G1 | `handoff-check` cannot enforce plan-only authority. | [handoff_check.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py:2), [task_plan.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/task_plan.md:970) | It validates citations and mise tasks, but neither forbids a task-bearing handoff nor requires an active `NEXT SESSION` plan phase. |
| HIGH | G5/G6 | At least two CLI tests can overwrite the canonical operator report and sidecars. | [test_session_review.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_session_review.py:1176), [second unsafe test](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_session_review.py:1269), [session_review.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:858) | Both subprocess tests run from `REPO_ROOT` without `--output`; the default is `.agent/session-review.md`. |
| HIGH | G5/G6 | Segmented artifacts are neither generation-scoped nor transactionally published. | [session_review.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:921) | Segments are overwritten before the index, and obsolete higher-numbered segments are never removed. A crash can leave an old index pointing at newly overwritten bytes. |
| HIGH | G5/G6 | Parser drift produces per-record omission floods instead of bounded diagnostics. | [session_ledger.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_ledger.py:2530) | `token_usage_record` is not known; current Claude attachment classes similarly append an omission for every occurrence. Unknown future records must remain blocking, but should summarize once per type with a count. |
| HIGH | G5/G6 | A failed report is not self-describing. | [session_ledger.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_ledger.py:4215), [session_review.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:894) | There is no first-line reasoned verdict, omission histogram, generation identity, or immediately visible index/newest-segment pointer. |
| HIGH | G3 | The implement-mode allowlist is advisory, not an enforced ownership boundary. | [sdlc_team.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sdlc_team.py:64), [request schema](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sdlc-team-request.json:31) | Allowlist entries are validated and rendered into the prompt, but settlement does not reconcile actual changed paths against them. |
| HIGH | G4 | Findings and automation candidates have no mandatory disposition loop. | [session-review skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-review/SKILL.md:192), [session_review.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:573) | Candidate output ends in prose; stable IDs, accepted/rejected status, carriers, and receipts are not required. |
| MEDIUM | G2 | Handoff lacks a named AgentsView session-integrity pass. | [session-handoff skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-handoff/SKILL.md:19) | Lost obligations, contradictions, and agent context are reconstructed manually even though the worked AgentsView report demonstrates bounded archive searches and dispositions. |
| MEDIUM | G2 | Semantic discovery and deterministic evidence are conflated. | [session-review skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-review/SKILL.md:34), [session_review.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:120) | Notepad/handoff regex discovery belongs in the archive lane; authority, lineage, hashes, tool pairing, and unknown-record failure remain ledger responsibilities. |
| MEDIUM | G3 | Requested specialist scope and cross-run ordering are not typed. | [sdlc_team.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sdlc_team.py:254), [request schema](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sdlc-team-request.json:4) | Settlement reconciles claimed versus observed children, but not requested versus observed specialists or review-before-implementation dependencies. |
| MEDIUM | G5/G6 | Lane 1 promotes shell syntax and wrapper fragments as workflow candidates. | [session_review.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_review.py:90) | Neighboring noise families such as `until [`, control operators, comments, timeout wrappers, and duration-bearing sleeps lack public-seam regression arms. |
| MEDIUM | G6 | The review skill carries excessive parser and state-machine detail. | [session-review skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-review/SKILL.md:52) | Implementation narrative obscures invocation, judgment, failure semantics, orchestration, and disposition responsibilities. |
| MEDIUM | G2/G6 | Handoff self-verification still refers to a retired “ref loop.” | [session-handoff skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-handoff/SKILL.md:248) | Step 2.5 rejects the old manual loop, while step 5 and the checklist still refer to it. `handoff-check` should be the single carrier. |

## G1 — make `task_plan.md` the only task carrier

Required disposition:

| Current surface | Change |
|---|---|
| Skill argument and task inference | Delete. The skill accepts no task text. |
| Step 0 | Keep, renamed to “resolve active-plan ambiguity.” Record rulings only in `task_plan.md`. |
| Prior-handoff read | Recover state, traps, and evidence—not task selection. |
| Memory “what’s next” | Delete. Memory may cite the plan but cannot restate task text. |
| Handoff body | Store plan path/digest, state, traps, evidence, and owed non-task obligations. |
| Resume prompt | Always emit only `Run /session-resume`. |
| Resume `NEXT:` line | Replace with `PLAN: task_plan.md → <active phase heading>`. |
| Resume offer | Ask whether to begin the active plan phase without copying it into another carrier. |
| `session_state.py` / `session_review.py` | No pointer producer found; no change required. |
| `handoff_check.py` | Add structural enforcement. |

Post-change:

```text
grep -c 'next task' .claude/skills/session-handoff/SKILL.md
0
```

That grep is a smoke check. The machine contract should reject a task-bearing handoff structurally and require a `NEXT SESSION`-shaped active plan phase.

Fail arms:

- Add `## Next task` or `NEXT:` to a fixture handoff → `handoff-check` returns nonzero with `forbidden_task_carrier`.
- Remove the active `NEXT SESSION` phase → nonzero with `missing_active_plan`.
- Restore a pointer-free handoff and active plan → zero findings.

Concrete cost avoided: a fourth session resuming stale task prose after the authoritative plan changed.

## G2 — add a named AgentsView pass

Add `2.0 AgentsView session-integrity pass` after deterministic state capture and before handoff drafting.

A Claude read-only lane should run bounded FTS searches such as:

- `owed work`
- `promised delivered`
- `missing issue`
- `contradiction plan`
- `failed ignored`

Use plain search with `--in tool_input,tool_result` for report paths, task-plan references, failed command names, and issue/PR identifiers. Inspect only the strongest 2–4 hits with `session messages --around`. Hybrid remains disabled until its index is healthy.

The lane must identify the subject root session and exclude its own review session. Subordinate-session findings require parent-session corroboration before being treated as decisions.

Required output:

- Subject session and archive cutoff.
- Exact searches and modes.
- Session/range/ordinal evidence.
- Typed finding and concrete avoided cost.
- `ACCEPTED`, `REJECTED`, `DUPLICATE`, or `BLOCKED`.
- Carrier and receipt.
- Explicit evidence gaps.

Migration boundary:

- Replace session-review lane 2’s semantic notepad/handoff discovery with archive search.
- Retain direct reads of current `task_plan.md`, handoff bytes, and disposition artifacts.
- Retain the deterministic lane 1 classifier unless AgentsView can prove exhaustive command enumeration; use archive search for contextual follow-up.
- Never replace the requirement ledger’s authority, lineage, hashes, cutoffs, tool pairing, stable claim IDs, or fail-closed unknown-record behavior.
- Use AgentsView lineage to discover agent activity, but filesystem receipts and SDLC settlement remain completion evidence.

Fail arm: remove the target session, ordinal evidence, or disposition from one archive row; typed validation must fail. An undispositioned owed-work hit must block handoff completion.

Concrete cost avoided: missed promises, contradictions, and red commands that never reached the notepad or current handoff.

## G3 — route handoff work through the SDLC team selectively

| Step | Owner |
|---|---|
| 0 | Inline architect; requires user authority. |
| 1 | Inline deterministic tools; live state is cheap and context-sensitive. |
| 2.0 AgentsView | Claude read-only lane. |
| 2.1–2.3 doc synchronization | One SDLC `implement` request when work crosses domains; exact allowlist. |
| 2.4 GitHub issue/epic | Inline architect; external mutation remains caller-owned. |
| 2.5 references | Normal machine gate/checker, not a manual loop. |
| 3a memory | Inline architect; user-global memory is outside team ownership. |
| 3b handoff drafting | Inline architect after specialist dispositions. |
| 3c coverage | AgentsView discovers lanes; disk receipts and settlement prove them. |
| 4 validation/commit | Caller; review lanes run no gates and `COMMIT: caller`. |
| 5 self-verification | `handoff-check`; optional SDLC review for consequential multi-domain work. |
| 6 prompt emission | Inline deterministic output. |

Recommended order:

1. Resolve plan ambiguity.
2. Snapshot deterministic state and run session-review with an explicit output.
3. Run the SDLC review and Claude AgentsView pass in parallel.
4. Wait for both and disposition every finding.
5. Use SDLC `implement` mode only for accepted cross-domain repository changes.
6. Caller runs gates, commits, and runs `handoff-check`.
7. Emit the fixed resume prompt.

Review request shape:

```json
{
  "spec_file": "/absolute/path/to/handoff-review-spec.md",
  "mode": "review",
  "effort": "xhigh",
  "timeout_s": 1800,
  "allowlist": [],
  "task": "Review the named handoff workflow; no edits and no gates"
}
```

Implementation request shape:

```json
{
  "spec_file": "/absolute/path/to/accepted-handoff-changes.md",
  "mode": "implement",
  "effort": "xhigh",
  "timeout_s": 1800,
  "allowlist": [
    "<exact skill or documentation paths>",
    "<exact Python and test paths>"
  ],
  "task": "Implement only accepted findings; COMMIT: caller"
}
```

Proposed request hardening:

- Add `expected_specialists`.
- Reconcile requested, claimed, and observed specialists.
- Reject absolute, empty, or repository-escaping allowlist entries.
- Reconcile implement-mode changed paths against the allowlist.
- Require a named completed review settlement before dependent implementation.

Fail arms:

- Omit one requested specialist while claimed and observed agree on the smaller set → settlement fails.
- Modify one allowed and one unlisted path → settlement fails.
- Supply `../outside.md` or an absolute allowlist entry → request is invalid.
- Start implementation before the review settlement completes → dispatch fails closed.

Cost avoided: missed cross-domain references and silent specialist omissions. Added cost: approximately 17 minutes plus specification and settlement review. Skip the team for a typo, a single-file edit, live questioning, state snapshots, memory curation, or exact prompt emission.

## G4 — close the self-improvement loop

Add a named `Disposition every learning` step backed by a typed manifest.

Each row needs:

- Stable finding ID.
- Source artifact and SHA-256.
- Disposition.
- Rationale.
- Concrete avoided cost.
- Carrier and owner.
- Receipt.

Suggested dispositions:

- `implemented_local`
- `issue`
- `plan`
- `rule_or_skill`
- `memory_fact`
- `external_handoff`
- `rejected`
- `blocked`

Routing:

| Producer | Destination |
|---|---|
| AgentsView finding about dotfiles | Issue, rule, test, implementation, or active plan. |
| AgentsView product defect | `docs/handoffs/agentsview-<date>.md`; never fixed here. |
| SDLC finding | Persisted report plus architect disposition; accepted work gets a plan/issue/spec. |
| Requirement claim | Existing semantic disposition and receipts. |
| Automation candidate | New typed candidate manifest with carrier or rejection rationale. |
| `command-audit` signal | Candidate manifest, duplicate, or explicit rejection. |
| Stable historical lesson | Memory; never task selection. |

Fail arm: add two source findings but disposition only one, alter a source after hashing, or accept a finding without a carrier/receipt. Finalization must return nonzero.

Concrete cost avoided: red commands and workflow defects surviving only in transient prose after `/clear`.

## G5/G6 — required session-review improvements

1. **Test isolation and output safety**

   Add explicit `--output tmp_path/...` to both unsafe subprocess tests. Require explicit output whenever the reviewed source root and execution/output repository differ.

   Fail arm: seed the canonical report and sidecars with sentinel hashes; the mismatched-root CLI case must leave every sentinel unchanged.

   Cost avoided: destruction of the operator’s only readable review evidence.

2. **Generation-safe publication**

   Stage report, sidecars, and segments under a generation ID, validate hashes, then atomically replace one current-generation pointer. Prune the prior referenced generation only after successful publication.

   Fail arms:

   - Publish three segments followed by one → only the new generation is reachable.
   - Inject failure before pointer replacement → prior generation remains fully readable.
   - Corrupt a staged segment → publication fails without moving the pointer.

   Cost avoided: mixed-generation and half-published evidence.

3. **Current record classification**

   Fixture-derive the exact safe fields, then classify:

   - `token_usage_record`: known bounded telemetry or explicitly known-and-skipped.
   - Reminders such as `total_tokens_reminder`, `batching_reminder_sent`, and `bash_output_audience_note`: known-and-skipped counters.
   - Context-bearing records such as `hook_system_message`, `prompt_snapshot`, `instructions`, `session_context`, and `output_style_instructions`: bounded diagnostics/digests, never user authority.
   - Fresh unknown types: still blocking, summarized once per provider/family/type/disposition with count and sample references.

   Fail arm: 100 known telemetry rows produce no parser-blocking omission; renaming the type to `future_shape_zzq` produces one blocking row with `count=100` and a nonzero review result.

   Cost avoided: a 19,000-row failure that cannot explain its actionable cause.

4. **Operator-oriented first block**

   Start the report with:

   ```text
   VERDICT: COMPLETE|INCOMPLETE — <one primary reason>
   ```

   Follow with selected session, source root, invocation/output root, pytest-temp detection, source/requirement/promise counts, omission total and histogram, generation ID, omission index, newest referenced segment, and iteration action.

   Fail arm: delete the reason, session identity, histogram, or index pointer independently; focused report-contract tests must fail.

   Cost avoided: log archaeology merely to explain `rc=1`.

5. **Disposition automation candidates**

   Give each candidate a stable ID and terminal status with carrier/receipt or rejection rationale.

   Fail arm: an output candidate without a terminal disposition blocks handoff finalization.

   Cost avoided: recurring candidates being rediscovered every session.

6. **Repair lane 1 at its public seam**

   Normalize or reject structural prefixes, control operators, continuation markers, comments, timeout wrappers, and duration-bearing sleep commands. Test through `shape_candidates` with realistic `BashCommand` inputs and positive controls.

   Fail arm: reverting normalization must restore all observed noise families while real `gh issue` and `uv run` controls remain ranked.

   Cost avoided: reviewer time spent on shell fragments instead of reusable workflows.

7. **Split judgment from implementation detail**

   Keep invocation, lane purposes, verdict semantics, unknown-record failure, AgentsView/SDLC orchestration, concrete-cost judgment, and disposition rules in the skill. Move cache mechanics, provider field catalogues, attachment limits, and finalize internals to a technical reference.

   Target approximately 120–150 lines.

   Fail arm: documentation validation requires the reference link plus the public invocation, `INCOMPLETE` semantics, cost gate, review roles, and receipt fields.

   Cost avoided: repeated prompt/context cost and hidden operator decisions.

## Required fail arms

1. Forbidden handoff task section.
2. Missing active PWF phase.
3. AgentsView row missing target session, ordinal evidence, or disposition.
4. Requested/spawned/observed SDLC roster mismatch.
5. Implement-mode path outside allowlist.
6. Implementation launched before review settlement.
7. Undispositioned or hash-mismatched learning.
8. Operator report sentinel modified by a test.
9. Cross-root implicit output accepted.
10. Interrupted generation publication damages the prior generation.
11. Shorter generation leaves old segments reachable.
12. Known current record becomes blocking.
13. Repeated unknown future type is not grouped or does not remain blocking.
14. Incomplete report lacks primary reason, histogram, or artifact pointer.
15. Lane 1 noise reappears while real-command controls remain.
16. Skill loses its technical-reference link or required judgment anchors.

## Gaps for the next session

- AgentsView was not probed; the spec declares it unreachable from this sandbox.
- Graphify’s required wrapper returned `rc=1` because mise could not create temporary state.
- GitHub issue #1157 was not live-verified.
- Exact safe fields for new Claude attachment types require fixture-derived schemas.
- Specialists observed the canonical report at different moments: two lanes saw the pytest-clobbered one-omission generation, while the documentation lane saw a regenerated 19,403-omission, 73-segment generation. This confirms the path was mutable during review; neither count should become a durable plan invariant.
- Exact names for new request and learning-disposition schema fields require architect ratification.

## Licensed dissent

- Keep handoff step 0: its valid job is resolving ambiguity in the active plan, not carrying a second task pointer.
- Do not replace the fail-closed ledger with AgentsView; semantic archive recovery cannot certify authority, pairing, prefix integrity, or parser completeness.
- `grep -c 'next task'` is a smoke test, not the structural contract.
- The default report resolves through the CLI’s repository root; “relative to cwd” is only indirectly true when cwd selects that root.
- Volatile omission totals belong in generated artifacts, not `task_plan.md`.
- The four primary workflow files are insufficient for G5/G6; parser behavior lives in `session_ledger.py`, and the public CLI seam also includes `main.py`.
- Removing task text from memory and handoffs means fresh-clone task recovery is no longer supplied by those artifacts. Because the sole PWF plan is gitignored, that continuity limitation must be accepted or solved without covertly restoring a second task carrier.
- The current SDLC allowlist must not be described as enforced ownership until changed-path reconciliation exists.

## Specialists spawned:

- `sdlc-python-specialist` — `/root/phase7_python_review`
- `sdlc-config-specialist` — `/root/phase7_config_review`
- `sdlc-documentation-specialist` — `/root/phase7_docs_review`

No others were spawned.


---

## Appendix — the spec handed to the team (verbatim)

# Spec — codex SDLC team REVIEW of the `/session-handoff` workflow (Phase 7, 2026-09-16)

Repo: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Session: `dotfiles-20260916.002` (Claude architect). Branch at dispatch: a docs
branch identical to `origin/main` for every file in scope.
Mode: **REVIEW — do not edit any file, do not run gates, do not commit or push.**

## 1. Objective

Ray ruled (task_plan.md "Phase 7", 2026-09-16): the codex SDLC team reviews the
`/session-handoff` workflow against SIX goals, returns typed findings, and the
ACCEPTED findings are implemented this session. You are the review half. The
failure this prevents: the workflow keeps a hand-maintained "next task" pointer
that has drifted from the plan three sessions running, its session-review tool
is red (#1157) and its own report cannot say why, and every step is done inline
by the most expensive model when a specialist team and an archive query would do
it cheaper and more completely.

Deliverable: for EACH goal, (a) findings with `file:line`, (b) a concrete
proposed change — the carrier (file + mechanism), the fail arm that proves it,
and the concrete cost it avoids (#607's test: "what concrete cost would this
have avoided?" — a preference is not a candidate).

## 2. Files in scope (read all four in full; they ARE the workflow)

- `.claude/skills/session-handoff/SKILL.md` (309 lines — the sending half)
- `.claude/skills/session-resume/SKILL.md` (106 lines — the receiving half)
- `.claude/skills/session-review/SKILL.md` (245 lines — the review tool's skill)
- `python/src/dotfiles_setup/session_review.py` (965 lines — the CLI)
- Supporting, read as needed: `python/src/dotfiles_setup/session_ledger.py`
  (4336 lines; the parser — `_parse_codex` at ~2530, the `known` record set at
  ~2536), `session_state.py`, `handoff_check.py`, `session_store.py`,
  `session_gate.py`, `tests/test_session_review.py`, `mise.toml` tasks
  `session-review`, `session-state`, `handoff-check`, `sdlc-team`.
- The planning-with-files plan: `task_plan.md` (section "Phase 7 — NEXT
  SESSION" at line ~970 carries the ruling verbatim).
- Worked examples of the two review lanes this workflow should adopt:
  `docs/research/kb/reports/agents/codex-sdlc-session-review-2026-09-16.md`
  (your own team's review of the last session, with the architect's
  dispositions) and
  `docs/research/kb/reports/agents/agentsview-session-review-2026-09-16.md`
  (the Claude AgentsView pass). The prior handoff is
  `.agent/plans/session-2026-09-16c.md`.
- The AgentsView query skill (read it; you cannot RUN it, see §5):
  `/Users/rmanaloto/.claude/skills/agentsview-finding-history/SKILL.md`.

## 3. The six goals — verbatim from Ray — and the required findings

### G1 — "we have fully removed the next task pointer and only rely on pwf task plan"

The ruling (2026-09-16, goal-history iteration 017): `task_plan.md` (the
planning-with-files plan) is the ONLY next-task carrier. The handoff carries
state, traps and evidence pointers — no task text.

Required: enumerate EVERY place in the four scoped files (and in
`session_state.py` / `handoff_check.py` if they emit one) that still produces,
requires, verifies, or consumes a next-task pointer. Known candidates:
session-handoff step 0 ("Resolve next-task ambiguity FIRST"), step 3b ("next
task + preload pointers"), step 6 ("Resume <task>:" prefix), the checklist's
first box; session-resume step 3's `NEXT:` line and step 4 "Offer the next
step". For each: keep (why — e.g. step 0's ambiguity-resolution is about the
PLAN's next phase, not a pointer) / rewrite to read the plan / delete. Propose
the minimal diff and the machine check that makes regression fail
(`handoff-check` already verifies citations — can it assert the handoff
carries no `NEXT TASK`/`Next task` section, and that `task_plan.md` has a
"NEXT SESSION"-shaped phase?). Say what the `grep -c 'next task'` count on
`session-handoff/SKILL.md` should be after the change and why.

### G2 — "migrate wherever possible to agentsview for reviewing the session for finding bugs/issues/missing items/vagueness in the session"

Required: map every step of `/session-handoff` and `/session-review` that
currently reads transcripts, notepads, handoffs, or "memory" by hand or by
regex, and say which of them an AgentsView query (per the skill's command
shapes: `session search --fts|--hybrid`, `--in tool_input,tool_result`,
`session messages --around`) answers better. Design the "AgentsView pass" as a
NAMED step of `/session-handoff` with: the queries it runs (2-3 word FTS
probes; hybrid is DOWN, see §5), the output shape (the 2026-09-16 report is the
worked example), who runs it (a Claude read-only lane — the codex sandbox
cannot reach the daemon), and how its findings are dispositioned into the
handoff. Also: which of `session-review`'s lane 1 (recurring command shapes)
and lane 2 (notepad passages) SHOULD be replaced by an archive query and which
must stay (the ledger's fail-closed evidence chain is a different product —
say which parts are irreplaceable and why).

### G3 — "utilize the /codex-sdlc-team skill and team for any of the steps in /session-handoff"

Required: for each numbered step of `/session-handoff` (0, 1, 2.1-2.5, 3a-3c,
4, 5, 6) say: inline (architect must do it — e.g. asking the user), delegate
to the SDLC team (which mode, which specialists, what the spec must name), or
delegate to a Claude lane. Design the request shape (`SdlcTeamRequest` — the
skill at `.claude/skills/codex-sdlc-team/SKILL.md`) for each delegated step,
and the ORDER (the team owns the checkout while it runs; a review lane must
not run gates; the doc-sync step edits files so it is `implement` mode with an
allowlist). Name the concrete cost each delegation avoids and the one it
adds (a ~17-minute review run is not free: say when it is NOT worth it).

### G4 — "use agentsview and any other tools to self-improve/self-help/self-optimize the project based on learnings from the session"

Required: propose the self-improvement LOOP as a step: which tool produces
the learnings (AgentsView pass, SDLC review, `session-review` lanes,
`command-audit`), where each learning lands (issue / rule / memory / plan /
`docs/handoffs/` for AgentsView-owned defects — Ray's ruling: AgentsView is
another project's product; its defects are WRITTEN as a document for that
project, never fixed here), and the fail arm that proves a learning was
recorded rather than narrated. Flag any existing step that produces learnings
nothing consumes.

### G5 — "find any missing steps that should be added to /session-review"

### G6 — "overall improvement of /session-review"

Required for G5+G6 together — start from these KNOWN inputs (do not re-derive;
verify and extend):

1. Issue #1157: `mise run session-review` exits 1 on codex 0.154 rollouts —
   `unknown Codex record 'token_usage_record'` (`session_ledger.py` `known`
   set at ~2536) plus unknown Claude attachment records. Architect re-ran it
   at 2026-09-16 ~20:55 (rc=1): **19,403 omissions across 73 segments** —
   10,982 `Claude attachment 'total_tokens_reminder'`, 3,246 parser-authority
   "unknown" dispositions, 1,306 `Codex record 'token_usage_record'`, 442
   `batching_reminder_sent`, 433 `hook_system_message`, 324 `prompt_snapshot`,
   261 `bash_output_audience_note`, then ~160 each of `environment`, `date`,
   `model`, `instructions`, `session_context`, `remote_session_change`,
   `output_style_instructions`. Read the current `.agent/session-review.md`
   and its `.omissions.json` index + segments (each segment is a dict with an
   `omissions` list). Note: nearly all of these are HARNESS-injected
   attachment types with no user content — say which must become known
   records (parsed) vs. known-and-skipped, and how a new unknown type should
   degrade (one omission line per TYPE with a count, not one per record).
   The report is not self-describing about its failure (it labels every
   promise UNREVIEWED but never names the unknown record types or the
   omission count).
2. **NEW, architect-verified this session (fresh read):**
   `tests/test_session_review.py:1269`
   `test_requirements_cli_fails_closed_when_recorded_cwd_does_not_match` runs
   the CLI with `cwd=REPO_ROOT` (line 1290) and no `--output`;
   `session_review.py:864` defaults the destination to
   `Path(".agent/session-review.md")` relative to cwd. So **the test suite
   overwrites the operator's real report and its sidecars** — the 15:43
   `.agent/session-review.md` on disk records
   `cwd: …/pytest-of-rmanaloto/pytest-6456/test_requirements_cli_fails_cl0/unmatched`,
   `Sources: 0`, 1 omission, while the real 15:17 run's segments
   (`.0002…0076.json`) are the "118 stale sidecars" the last review counted.
   Find the CLASS: every test that invokes the CLI or `write_report` with a
   repo-relative default path; propose the isolation fix (tmp cwd, explicit
   `--output`, or a default that refuses to write into a repo it did not
   select) and the test that pins it.
3. Segmented artifact writes (`session_review.py` `_write_segmented_artifact`
   ~915) never remove a previous generation's segments, so a glob-based reader
   mixes generations.
4. The skill text itself (245 lines): which of its sections are the
   judgement worth having and which are implementation narrative that belongs
   in a docs file; propose the cut that keeps the skill under the 500-line
   budget with room.
5. Missing steps: what does a reviewer need that the report does not give —
   e.g. a first-line verdict (COMPLETE/INCOMPLETE + the one reason), the
   session id it reviewed, whether it ran on a pytest tmp cwd, the omission
   histogram by record type, a pointer to the newest omissions segment.
   Compare against what the AgentsView and SDLC reports provided that the
   ledger report did not.

## 4. Output shape — typed, so the architect can disposition each row

1. A findings table: `| Severity | Goal | Claim | File:line | Evidence |`
   (HIGH/MEDIUM/LOW/BLOCKED), severity-ordered.
2. Per goal, a "Proposed change" list: carrier file(s), the mechanism in one
   paragraph, the FAIL ARM (the mutation that must make the check go red),
   the concrete cost avoided, and a cost/benefit line for delegations.
3. "Required fail arms" — one per proposal, as in your 2026-09-16 report.
4. "Gaps for the next session" — what you could not settle from the sandbox.
5. "Licensed dissent" — any premise above that the code contradicts.
6. The pinned closing list of specialists spawned.

## 5. Constraints — absolute

- **Do not edit, create, or delete any repository file.** Findings go in your
  final message only.
- **Do not run gates** (`mise run lint`, `pytest`, `mise run verify`, `hk`).
  Under the read-only sandbox every gate fails for sandbox reasons; that is
  noise, not a finding.
- **Do not run `git commit`, `git push`, `gh pr create`, `gh pr merge`,
  `gh issue edit`.** Read-only `gh` and `git` are fine but GitHub was
  unreachable from this sandbox last run — if `gh` fails, record
  UNVERIFIABLE, never "none".
- **AgentsView is unreachable from this sandbox** (last run: every request
  `dial tcp 127.0.0.1:8080: connect: operation not permitted`). Do not spend
  probes on it; design against the skill text and the worked-example report.
  Architect-measured this session: `--hybrid` returns
  `semantic search not available … index is building: 9% complete` (same as
  yesterday — the index is stuck, that is an AgentsView-project defect);
  `--fts` works (rc=0).
- **Graphify** may be denied by the sandbox; read source directly if so.
- **Never pipe a command into `head`/`tail`/a pager** — redirect to a file
  and read the recorded rc.

## 6. Evidence standard

Every claim carries a `file:line` or a command with its real output. Every
NEGATIVE claim carries a control arm proving the probe can find things; invent
the known-absent control token fresh. Do not report a conclusion supported
only by your own summary of what you did: if you spawn specialists, the
discriminating evidence is on disk (a real spawn writes a second session file
whose log carries `"parent_thread_id"`), and the settlement reconciles your
claimed roster against it and fails closed on mismatch.

## 7. Licensed dissent

If any premise here is wrong — including the ruling's framing — say so with
evidence and stop that line of work.

## 8. Commit

COMMIT: caller. Do not commit anything.
