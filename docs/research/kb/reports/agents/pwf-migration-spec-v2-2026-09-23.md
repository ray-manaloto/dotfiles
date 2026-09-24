# Spec v2 — pwf 3.20.7 current-workflow migration (Brief L: the draft revised against the codex-astra verdict)

> Written by a Fable lane (`general-purpose`, `model: fable`) on 2026-09-23. Base:
> `pwf-migration-spec-draft-2026-09-23.md` (Brief G; left untouched as a verbatim record). Inputs:
> `pwf-migration-spec-codex-astra-verdict-2026-09-23.md` (F1–F17), the design of record
> `pwf-migration-fable-round3-2026-09-23.md` (T1–T10), and the binding rulings in `task_plan.md`
> § "Addendum — pwf current-workflow migration" rounds 1–6 (`task_plan.md:586-651`). The briefs file's
> "Shared context" statements about D4 / operator-only attestation are SUPERSEDED by round 4 and are not carried.
> The publishable issue body (template headings only, no paths/snippets/schemas — F17) is the sibling file
> `pwf-migration-spec-v2-issue-body-2026-09-23.md`.
>
> Evidence discipline: graphify reported `stale` (rc=3, built at `9a6ea68f`, HEAD `b5af8ecf`), so every claim
> below was verified by reading source. Every finding was checked against its cited lines before being
> accepted, narrowed, or rejected; the table says which. One live datum surfaced on the way: two read-only
> `sed -n` batches over the installed plugin scripts were DENIED by the harness because the command line
> contained the script names — the D4 collateral the design's retired-items table describes, observed again
> tonight. The scripts were read with the Read tool instead.

## Resolution table

Legend: **ACCEPTED** — the finding is correct and the spec now carries the correction; **NARROWED** — correct in
substance, the correction is smaller or differently shaped than the verdict asked; **→ RAY** — correct, and the
fix is a genuinely new decision, listed under "Questions for Ray" with a recommendation (the spec carries the
recommended answer provisionally and says so). No finding was rejected outright; where a premise of a finding was
wrong, the table says so.

| # | Sev | Verdict | What I verified | How v2 handles it |
|---|---|---|---|---|
| F1 close has no clean terminal state | HIGH | **ACCEPTED** | `resolve-plan-dir.sh:367-368`: a stale pointer is skipped and resolution falls to newest live dir, then empty; `set-active-plan.sh:321` names it "stale pointer". Draft S:364 made `STALE_POINTER` non-clean while S:476 required "pointer absent or stale" then "doctor clean". | Status now separates **bindings** (env `PLAN_ID`: fails closed upstream, so a bad one is NON-CLEAN `STALE_PIN`) from **hints** (the shared pointer: upstream falls through it, so `RETIRED_POINTER` — names an archived id — and `DANGLING_POINTER` — names nothing — are INFORMATIONAL, exit 0). The clean terminal states after a successful close are enumerated (Implementation § Status). Handoff's "both MATCH" is defined as "every authority the profile declares and that resolves is MATCH". Close still never touches the pointer (round 3, unchanged). |
| F2 root-only handoff needs a ledger op the CLI forbids | HIGH | **ACCEPTED** (the draft's premise was wrong) | `ledger-append.sh:47-64`: the root fallback (`.`) is taken ONLY when the resolver is empty AND no selector is set — it is upstream's legacy single-file mode, not an unsafe fallback. The draft banned it. Also `.gitignore:143-151` does not ignore a root `ledger-*.jsonl`. | `log` resolves env `PLAN_ID` → live pointer → single live slug → **root roadmap** (when the profile declares one and no selector is set), i.e. exactly upstream's chain; it refuses only on AMBIGUOUS or a rejected selector. The handoff note therefore always has a target. T3 adds the root ledger pattern to the ignore list. |
| F3 one live slug ≠ unambiguous when session isolation is armed | HIGH | **ACCEPTED** | `resolve-plan-dir.sh:345-347` counts the root plan when `.planning/sessions/` exists; the dir is created only by opt-in codex session attachment (`README.md:640`, CHANGELOG #146 entry); `plan-doctor.sh:106` says delete it to turn isolation off. Not present in this checkout (control). | Session isolation is **not adopted**. Status reports `SESSION_ISOLATION_ARMED` (non-clean) whenever the directory exists under a root-roadmap profile, naming the two exits (delete the directory, or pin `PLAN_ID`). A fixture with the directory present is added to the throwaway-repo tests. The "never reaches its ambiguity branch" sentence is replaced by the bounded claim. |
| F4 fresh worktrees lack the required root roadmap | HIGH | **→ RAY (Q1)** | `.gitignore:143-151` ignores `/task_plan.md` and `/.plan-attestation`; `.mode` is tracked (`git ls-files .mode`). A linked worktree therefore starts with the mode floor and no root plan. | Provisional answer (recommended in Q1): the roadmap lives in the **main clone only**; a linked worktree is a ticket checkout; there `MISSING_ROOT_PLAN` is informational (`root: n/a (linked worktree)`), `plan pointer` updates only the ticket block and preserves the committed root block, and roadmap edits are a main-clone act at the boundary. |
| F5 task routing / alias retirement conflict with retained contracts | HIGH | **ACCEPTED** (compatibility surface **→ RAY (Q2)**) | `suites.toml:1707-1730` binds five per-path tokens (mise task line, two `main.py` registrations, `def main(` in the module, the public-CLI test name, the skill fence); `suites.toml:1868-1899` pins the `task_plan.md | coordinator ONLY` table row of the persistence rule. | The whole `plan-pointer-wiring` contract is migrated (not partially preserved) in the same ticket that moves the readers, to a `pwf-workflow-wiring` contract binding mise task → `kb-setup plan` verb → library function → skill fence. Recommended (Q2): the `dotfiles-setup plan-attest` / `plan-pointer` subcommands are DELETED in that ticket — no re-export period — because round 6's layering says tasks call tasks. The codex-lane contract keeps its behaviour tokens and gets its documentation token updated in T7 in the same change as the table reword. |
| F6 T1 omits an active human-only rule and the tests importing the deleted selfcheck | MEDIUM | **ACCEPTED** | `mise-tasks-only.md:31` row ("nothing an agent may run"); `test_plan_attest.py:19-22` imports `_ATTEST_DENY_BASES`/`check_plan_attest_deny`; the four deny tests at `:84/:90/:104/:121`; the registration at `hook_selfcheck.py:811`. | T1's retirement inventory now names the rule row, the imports, the four tests by name, the registration line, and keeps the resolver + passthrough tests (incl. the separator test) explicitly. |
| F7 consumer inventory misses root-writing rules and a public handoff bypass | MEDIUM | **ACCEPTED** | `notepad-enforcement.md:8` and `agent-artifact-conventions.md:76` route findings to root `findings.md`; `handoff_check.py:295-301` returns 0 before plan checks when no handoff exists, `:313-316` prints "skipped". `handoff-check` is not in the ship gate (`pr.py:327-330`; only `mise.toml:1006`). | Both rules join T7's inventory ("the resolved plan directory's findings/progress"). Handoff-check's public path is specified: no handoff → unchanged rc 0 info line (a fresh clone must stay green); a handoff present + root-roadmap profile + no root plan → `MISSING_ROOT_PLAN`, rc 1; no-root profile → never. Tested at the public `main()` seam. `verify` and `session-review` skills join the consumer list. |
| F8 "one workflow" lacks a content-sharing mechanism and a disposition for KB's lifecycle rules | MEDIUM | **NARROWED** (mechanism **→ RAY (Q3)**) | `rule_sync.py:133-163` checks plugin presence, selected lines and rule names — no content equality. KB resume: "Report it; do not archive it" (`:164-166`), next-ticket precedence (`:157-162`); clear-prep archives only on "/clear now" and only when complete (`:433-440`). | The rule-sync claim is narrowed to what it does (presence of the shared rule in both repos). Shared **implementation** (library, CLI, tasks, the shared skill text) vs repo-specific **invocation policy** (each repo's lifecycle skills decide WHEN to call status/close) is now an explicit split. KB's three behaviours are preserved by name: resume reports and never archives; user task > next-ticket > plan Next Step; archive only on "/clear now" and only when complete — which is exactly what `plan close` without `--force` enforces. Q3 recommends the content mechanism (package-shipped skill bytes + byte-parity copies). |
| F9 the anti-deny contract does not cover the wrapper routes or its JSON scope | MEDIUM | **ACCEPTED** | `settings.json:31-41`: six script entries + five wrapper entries (`plan-attest` ×5, all in the deny list — `grep -c` = 5, no allow-side mention); `verify.py:446-482` scans whole files line-by-line and strips after `#`, no JSON scoping. | Two layers: (a) hook-selfcheck's `plan-attest-deny` arm is **converted to its inverse**, JSON-scoped: parse settings, assert NO `permissions.deny` entry matches any of the four spellings (attest script, selector script, wrapper task/CLI, initializer) — so the mutation arm is meaningful; (b) a `regex_forbid` over `settings.json` for the same four spellings as belt. Mutation cases: one script rule AND one wrapper rule re-added → both layers fail. Controls: credential `Read(~/…)` denies stay accepted; the words in a description elsewhere are not a deny. |
| F10 overstates when upstream resolves or attests the root | MEDIUM | **ACCEPTED** | `attest-plan.sh:44-77`: resolver first; slug-cwd or `./task_plan.md` only when the resolver is empty and no selector is set. `init-session.sh:235`: root branch clears selectors then runs the attester, which still prefers a live slug. `init-session.sh:202-206` writes bare `autonomous` / `autonomous gate`; but `inject-plan.sh:957-967` (`mode_has`) also reads the ROOT mode file, so root `inject-smart` still governs slugs. | Conditions are explicit everywhere: "root is the attester's target only when no live slug resolves and no selector is set". `/pwf` is described as allowed upstream behaviour that attests whichever plan resolves. `.mode` inheritance is stated as a policy floor (mode token), with the note that root-level tokens such as `inject-smart` are read from the root file at injection time. |
| F11 universal agreement between phase readers is false | MEDIUM | **ACCEPTED** | `check-complete.sh:95-108` per-field maximum of primary and inline counts; `ledger-summary.sh:99-112` uses inline counts only when both primaries are zero; heading walk `:117-137` prefers the primary marker. | The claim is bounded to a **canonical format**: primary `**Status:**` markers only, exactly one `in_progress`, planning enabled. Status emits `NONCANONICAL_PHASE_MARKUP` (warning) when inline `[status]` tokens appear or more than one phase is in progress; the pointer's active-phase rule is defined as "first `### Phase` heading whose following primary status is in_progress". Test cases: canonical, mixed-format, multiple-active, no-phase, planning-disabled. |
| F12 worker guarantee and refusal matrix incomplete | MEDIUM | **ACCEPTED** (inherited-disable disposition **→ RAY (Q4)**) | `sdlc_team.py:805-818` and `:961-968` both `Popen` without `env=` → inherit `PLAN_ID` AND an ambient `PLANNING_DISABLED=1`; resolver returns empty at rc 0 for a rejected binding (`resolve-plan-dir.sh:363-366`). | Full pre-dispatch matrix: NONE → allow; RESOLVED+MATCH → allow; RESOLVED+MISMATCH/UNATTESTED (v3 mode) → refuse naming the attest task; AMBIGUOUS → refuse naming pin-or-close; REJECTED_BINDING (`PLAN_ID` set, resolver empty) → refuse naming the stale pin; resolved dir without a plan file → refuse. Inherited disable: recorded in the dispatch record as `PLANNING_DISABLED_INHERITED`; Q4 recommends warn-and-dispatch. The real supervisor→worker chain is tested with a stand-in argv that prints its environment. Check location stays the dispatch call (round 6). |
| F13 host/CI test plan lacks an execution and fixture contract | MEDIUM | **ACCEPTED** | `conftest.py:31` skips only when `CI == "true"`; `pr.py:327-330` runs `tests/` of this repo only; KB has `tests/conftest.py` but no `host_only` marker and no `doctor.toml`. | Testing Decisions now assigns every test to a repo and a gate, names fixture provenance (recorded under the KB test tree, stamped with plugin version + script digests, nonce/timestamp fields normalised), defines missing-plugin behaviour (`host_only` tests FAIL, never skip — the existing "missing binary fails the gate" sibling), and gives the doctor's dispatcher test a function-seam fixture twin. Prior-art wording narrowed as the verdict asked. |
| F14 CLI outputs depend on metadata the spec no longer supplies | MEDIUM | **ACCEPTED** | Revision `:43` (Goal carries `#NNNN`), `:60` (roadmap grep for the parent phase), `:90` (`[plan]` table, `--config`) were dropped by the draft. | Restored: ticket identity is the profile's `ticket_ref` pattern found in the ticket plan's Goal line; parent lookup = the roadmap phase block containing that reference; zero or multiple matches → the reminder says "no unique parent phase" and never manufactures one; open-ticket count = unchecked references in that block. Profile carrier = a `[plan]` table in each repo's tracked baseline (dotfiles: the existing doctor baseline; KB: a new tracked baseline file), `--config` overrides for tests. `--force` requires `--reason`. Partial-close recovery: close is idempotent by post-condition — an id already under the archive resumes the remaining steps. |
| F15 worktree pinning has no acceptance probe | MEDIUM | **ACCEPTED** | A child cannot update a running parent's environment; the design's own unverified list said so. | Bounded probe in T2/T4 verification: `plan init --pin` in a throwaway worktree, then a FRESH process launched through mise activation from that directory reports the binding (positive) while a shell started before the write reports the old value (control). Hook attachment is reported separately by the doctor. |
| F16 the issue-level dependency ruling was dropped | LOW | **ACCEPTED** | `task_plan.md:593` "It precedes #1327 and absorbs #910"; #910 OPEN "PLAN TAMPERED fires every prompt…"; #1327 OPEN "Land the native AgentsView service (#1141) and settle its parked worktree". | Further Notes carries both: #910 is absorbed (closed by T5 + T6 + T8's live arm, which is #910's own reproduction); #1327 is the first ticket run under the new workflow and must not start before T8 lands — its parked worktree is the first `PLAN_ID`-pinned worktree (why Q1 matters). |
| F17 removing Seams does not make the body template-compliant | LOW | **ACCEPTED** | Draft S:321-337 (paths) and S:394-396 (schema) sit in the spec body. | Separate issue-body file written in prose only; this file keeps paths for implementers. |

**C1–C7 after v2:** C1 complete (session-isolation state now dispositioned); C2 wording fixed (F10); C3 unchanged;
C4 unchanged; C5 superseded (unchanged); C6 bounded (F11); C7 has clean terminal states and recovery (F1, F14).

## Questions for Ray

Each carries a recommendation; the spec body provisionally assumes the recommended answer and marks it.

1. **Root authority in linked worktrees (F4).** *(Recommended)* **The roadmap lives in the main clone only.**
   A linked worktree is a ticket checkout: status prints `root: n/a (linked worktree)` instead of
   `MISSING_ROOT_PLAN`, `plan pointer` run there updates only the ticket block and carries the committed root
   block forward unchanged, and roadmap edits (with their re-attest) happen in the main clone at the boundary.
   PRO: no copied bytes to diverge; one place ever edits the roadmap; matches "PLAN_ID per worktree" (round 2).
   CON: a worktree session sees the roadmap only through the tracked pointer and extract, not the plan body —
   the same gap a fresh clone has (story 53). *Alternative:* `plan init --pin` copies the root plan and its
   attestation into the worktree. PRO: full context in the worktree. CON: two editable copies of the roadmap;
   any worktree-side edit is a MISMATCH the main clone cannot see. Evidence: `.gitignore:143-151`;
   `task_plan.md:613`.
2. **Compatibility surface for the dotfiles `plan-attest` / `plan-pointer` CLI subcommands (F5).**
   *(Recommended)* **Delete them outright in the consumer-cutover ticket** — mise tasks call `kb-setup plan …`
   directly, the wiring contract is migrated in the same change, and their tests move to the knowledge-base.
   PRO: one code path, no re-export to forget; this is what round 6's "tasks call tasks" means. CON: any
   transcript or memory naming `dotfiles-setup plan-attest` goes stale at once (the memory flip at the next
   handoff covers it). *Alternative:* permanent thin re-exports, contract-bound. PRO: old spellings keep
   working. CON: a second entry point to keep green forever. Evidence: `suites.toml:1707-1730`;
   `task_plan.md:644-646`.
3. **The content-sharing mechanism for the shared skill text (F8).** *(Recommended)* **Ship the shared
   `pwf-workflow` skill bytes inside the `kb_setup` package and keep a byte-identical copy in each repo's
   skills directory, checked by a parity gate** (the pattern the skills mirror already uses here); each repo's
   own lifecycle skills call it. PRO: a real equality check; one edit lands in both repos through the pin
   bump. CON: a second tracked copy per repo. *Alternative:* rely on rule-sync `lines` for a few key sentences.
   PRO: zero new machinery. CON: presence-only, so the two texts can still drift. Evidence:
   `rule_sync.py:133-163`.
4. **`PLANNING_DISABLED=1` inherited from the dispatcher's own environment (F12).** *(Recommended)*
   **Warn and dispatch** (`PLANNING_DISABLED_INHERITED` in the dispatch record). PRO: consistent — if the
   coordinator's own hooks are off, the lane's being off is not a defect; nothing is scrubbed or injected.
   CON: a blind lane is possible when the operator deliberately disabled planning. *Alternative:* refuse.
   PRO: never a blind worker. CON: breaks every planning-disabled session's dispatch. Evidence:
   `sdlc_team.py:805-818`, `:961-968`; `task_plan.md:636`.
5. **Should the dotfiles ship gate run the pinned library's own tests (F13)?** *(Recommended)* **No** — the
   knowledge-base's gates own the library tests; dotfiles adds one `host_only` smoke test that the pinned
   `kb-setup plan status` runs against this repo and one contract that the pin is at or above the version that
   ships the `plan` verbs. PRO: one owner per test suite. CON: a library regression reaches dotfiles only at
   the pin bump. Evidence: `pr.py:327-330`.

---

## Seams (revised; removed before publishing)

Unchanged in structure from the draft (one shared CLI seam driven with the real installed scripts in throwaway
repos; the dotfiles function/CLI seams for dotfiles-only consumers; contracts; the documentation gates), with
the verdict's §5 correction adopted: the table names **entry points**, not ownership groups —

| Entry point | Evidence shape | Repo / gate |
|---|---|---|
| `kb-setup plan …` CLI | real scripts in disposable git repos (`host_only`) + CI twins on recorded layouts | knowledge-base pytest (KB ship gate); one `host_only` smoke in dotfiles |
| `handoff-check` public `main()` | public-CLI tests + focused classification tests | dotfiles pytest |
| doctor check function | assembled setup + real-dispatcher canary (`host_only`) + fixture twin | dotfiles pytest |
| `sdlc_team` dispatch function | refusal matrix with captured spawn | dotfiles pytest |
| supervisor→worker process boundary | real child with a stand-in argv printing its environment, both arms | dotfiles pytest (`host_only`) |
| contracts, selfcheck, docs | verify, hook-selfcheck, lint-docs, mirror parity, rule-sync | both repos' ship gates |
| T8 migration | one-time recorded live verification | none (recorded in the ticket) |

The judgment surface that stays untested by pytest (ask before `--force`) is unchanged.

---

## Problem Statement

Ray runs a multi-session, multi-agent program in two repositories (dotfiles and knowledge-base) with one Claude
orchestrator and codex worker lanes. The planning-with-files (pwf) plugin is supposed to carry the program's
working memory between sessions, but the way it is set up today makes it a cost centre:

- **Attestation is a chore that lands on Ray.** The plan is one 1,647-line root `task_plan.md` under
  `autonomous inject-smart`; every edit breaks its attestation and the plugin refuses to inject until a human
  re-attests. Attestation was made operator-only here (D4, 2026-09-02) on the belief that it is a human-approval
  boundary; upstream's maintainer says it is not ("not a keyed signature or proof of human approval",
  `docs/attestation-locking.md:9-13`). Result: roughly twenty manual `! mise run plan-attest` runs in twenty-one
  days, an eleven-day outage of the read-only `--show` form nobody noticed, sessions that end with "attest is
  owed" — and a deny list that, observed again tonight, blocks a read-only `sed` of a plugin script because the
  script's name is on the command line.
- **The plugin's own view of the plan is stale.** The phase markers say Phase 2b; the tracked pointer says
  Phase 11; ledgers hold zero entries; `plan-doctor` warns about hash mismatches; codex lanes have received
  `[PLAN TAMPERED]` instead of the plan (#910). Turn-start injection names the wrong phase.
- **Two repositories, two workflows.** The knowledge-base uses slug plans with an eleven-day-old live plan, its
  own archive recipe, a hard-coded plugin version in its resume skill, and no attestation posture; dotfiles uses
  a root plan, a deny list, a wrapper task, and a tracked pointer.
- **Local hardening fights upstream.** The deny list, the operator-only docstrings, the selfcheck arm and the
  verification contract encode a trust model upstream does not share. Ray's standing instruction: "assume what
  we are doing is wrong and follow upstream so pwf updates land with minimal change".
- **Leftovers and gaps.** A `.planning/2026-09-21-graphify-…/` directory holding only an archived plan; no
  `.planning/.archive/`; no one-line answer to "is the plan I am about to trust the resolved one, attested,
  unambiguous, and current?"

## Solution

Adopt pwf 3.20.7's current workflow whole, under upstream's trust model, and put the human-review boundary where
a PR can actually see it.

- **Layout.** Root `task_plan.md` becomes a short program roadmap (≤150 lines, upstream's autonomous template
  shape, exactly one `in_progress` phase). Each `/implement` ticket gets its own plan under
  `.planning/<date>-<slug>/`, created by upstream's initializer in slug mode (attested at creation, inheriting the
  tracked root `.mode` floor). Closed tickets move to `.planning/.archive/<id>/`, unscannable by construction.
  The old program plan is archived byte-for-byte; its open obligations are mapped into a tracked extract, the
  roadmap, or an existing issue.
- **Trust model.** Attestation is tamper detection run by the orchestrator: create, fill and attest a ticket
  plan in the same turn; re-attest after each intentional edit and at phase boundaries; never attest a change it
  did not make. Workers never attest. D4 and everything that existed only for it are retired; a JSON-scoped
  selfcheck arm plus a contract guarantee the deny never returns. Human review moves to the tracked
  two-authority pointer and the append-only goal history.
- **Binding.** The main clone holds at most one live ticket plan and no `PLAN_ID`; parallel tickets run in
  worktrees with `PLAN_ID` exported and optionally pinned per worktree. Enforcement is detection: status and the
  doctor report a second live slug, a stale pin, an armed session-isolation directory. Pointers are hints
  (upstream falls through them); only the environment binding fails closed.
- **One merged workflow.** A shared library and `kb-setup plan {status,init,close,log,attest,pointer,doctor-probe}`
  in the knowledge-base's `kb_setup` package (already a SHA-pinned dependency of dotfiles). Both repos expose the
  same thin mise tasks; per-repo differences are declared profile flags. Shared implementation is separated from
  repo-specific invocation policy (when each repo's lifecycle skills call status/close).
- **Consumers follow.** Two-authority pointer; the canonical active-phase rule; handoff-check gains
  `MISSING_ROOT_PLAN` on its public path; the session doctor gains a FAIL-only dark-hooks probe plus the
  selection findings; `/session-handoff` and `/session-resume` run status and classify mismatches by who edited;
  `sdlc_team` lanes see the plan and dispatch is refused on a plan the hooks would not inject, with a complete
  refusal matrix. `codex_lane` keeps its scrub until Phase 10.
- **Knowledge-base parity.** Same tasks; the shared skill text; a tracked root `.mode` floor; no version
  literal; its existing lifecycle rules preserved by name; its eleven-day slug closed through the shared close
  once its round is confirmed done.
- **Upstream first for what upstream lacks.** File, do not block on: an explicit root-target flag for the
  attester; a Claude/Codex analogue of Pi's `/plan-execute`.

## User Stories

Ray, the operator

1. As the operator, I want attestation to stop being a manual step I perform after nearly every session, so that
   my involvement is reserved for decisions rather than for pressing a button on bytes an agent wrote.
2. As the operator, I want the program plan to be short and true, so that reading it tells me where the program
   is without scrolling through 1,600 lines of history.
3. As the operator, I want each ticket's working plan isolated from the roadmap, so that one ticket's churn never
   breaks the roadmap's attestation or another ticket's context.
4. As the operator, I want the tracked digest pointer and the goal history — not the gitignored plan — to be the
   things I review in a PR, so that the human-approval boundary lives where a review actually happens.
5. As the operator, I want the D4 deny rules retired and two independent checks that fail if any spelling of them
   comes back, so that a later session acting on stale memory cannot silently re-impose the old posture.
6. As the operator, I want one workflow across dotfiles and knowledge-base with differences declared as flags,
   so that I maintain one thing and every improvement lands in both repos.
7. As the operator, I want to be asked before an incomplete ticket is force-closed, before a listed obligation is
   dropped in the migration, and before the goal text changes, so that irreversible or judgment-laden steps still
   pass through me.
8. As the operator, I want the next pwf release to be a plugin update rather than a migration, so that upstream
   improvements arrive with minimal local change.
9. As the operator, I want the leftover 2026-09-21 directory and the old program plan archived rather than
   deleted, so that nothing is lost and nothing stale is selectable.
10. As the operator, I want every open obligation in the old plan accounted for before the old plan is retired,
    so that live work does not vanish in the move.
11. As the operator, I want the plugin's own phase view, the pointer, and the ledger summary to name the same
    phase for a canonically formatted plan, so that turn-start injection and my own reading agree — and to be
    warned when a plan is not canonically formatted.
12. As the operator, I want a one-line status that says which plan resolves, whether it is attested, whether
    selection is ambiguous, and whether anything binds to an archived plan, so that I never trust a plan the
    plugin is not actually injecting.
13. As the operator, I want the accepted cost stated plainly — an attested plan no longer means I approved it —
    so that no future session infers an approval that was never given.
14. As the operator, I want a successful close to leave the repository in a state that status, the doctor and the
    handoff all call clean, so that "close" never becomes a finding I must explain away.

The orchestrator agent (the Claude architect session)

15. As the orchestrator, I want to create a ticket plan with one command that prints the plan id and its status,
    so that I do not hand-type a version-pinned plugin path or guess whether creation attested.
16. As the orchestrator, I want to fill the ticket plan and attest it myself in the same turn, so that the tamper
    gate is armed on my own bytes without waiting for a human.
17. As the orchestrator, I want the attest command to print which plan it will target before writing, so that I
    never lock a slug when I meant the roadmap, or the reverse.
18. As the orchestrator, I want to be told when the roadmap is unattested while a ticket plan is live, so that I
    sequence roadmap edits to the boundary where the roadmap is the resolved plan.
19. As the orchestrator, I want to close a completed ticket with one model-runnable command that archives it,
    records the ledger event, drops my worktree pin, and names its parent roadmap phase when one is uniquely
    identifiable, so that closing is routine and never leaves a stale selection behind.
20. As the orchestrator, I want closing to refuse an incomplete ticket unless I pass a force flag with a reason
    after asking Ray, so that "done" keeps meaning every phase complete and the reason is on record.
21. As the orchestrator, I want closing to never touch the shared active-plan pointer, and I want a pointer that
    names an archived plan to be reported as informational rather than as a failure, so that upstream's own
    fall-through rule is what governs and a clean close is clean.
22. As the orchestrator, I want to re-run close after a partial failure and have it finish the remaining steps,
    so that a non-transactional close never strands a half-archived ticket.
23. As the orchestrator, I want to log progress and notes to a ledger bound to the resolved plan — the ticket
    when one is live, the roadmap when none is — and to be refused when resolution is ambiguous or a binding is
    rejected, so that ledger rows never land in the wrong plan and root-only sessions can still log.
24. As the orchestrator, I want status to distinguish the plan's attestation state, the selection state, the
    binding findings and the informational pointer states, so that my next action is determined by the state.
25. As the orchestrator, I want `/session-handoff` to classify a mismatch by whether this session edited the plan
    (attest if I did; report a finding if I did not), so that tamper detection still pays exactly where it should.
26. As the orchestrator, I want `/session-resume` to three-way compare file digest, attestation and committed
    pointer, so that "unattested edit after handoff" and "re-attested after the pointer was committed" are named
    as distinct disagreements with distinct first offers.
27. As the orchestrator, I want the handoff's owed list to never contain an attest, so that a handoff is
    complete when I write it rather than pending on Ray.
28. As the orchestrator, I want the pointer to record both the roadmap and the ticket plan, so that an
    unrecorded roadmap change is detectable even while a ticket is selected.
29. As the orchestrator, I want the active-phase rule to be the canonical primary-marker rule with a warning when
    a plan mixes formats, so that my pointer, the ledger summary and the completion check agree whenever the plan
    is well-formed and I am told when it is not.
30. As the orchestrator, I want to record a mid-ticket ruling in the ticket plan's decisions and batch roadmap
    edits to the boundary, so that the roadmap changes only at rulings and phase boundaries.
31. As the orchestrator, I want to append a goal-history iteration with the changed goal text when the plan
    migration lands, so that the program record states what task authority now is and who writes it.
32. As the orchestrator, I want the session doctor to fail loudly when a plan resolves but the real dispatcher
    injects nothing, so that dark hooks are caught at session start rather than noticed as silence.
33. As the orchestrator, I want the doctor and status to report a second live slug, a stale environment pin, or
    an armed session-isolation directory, so that I fix selection before I trust injection.
34. As the orchestrator, I want to run a ticket in a worktree with `PLAN_ID` pinned per worktree and to know
    how that worktree relates to the roadmap, so that two parallel tickets never share a pointer and a worktree
    never starts in a failing state.
35. As the orchestrator, I want `/pwf` to keep working as upstream ships it while the documented ticket route is
    the thin init task, so that I follow upstream by default and only add what upstream lacks.
36. As the orchestrator, I want the wrapper skills to call other skills, the tasks to call tasks, and the
    functions to call functions, so that no layer re-implements the one below it.
37. As the orchestrator, I want every rule, skill, task description and test docstring that still says
    "operator-only", "HUMAN boundary" or "root findings.md" rewritten in the same change, so that the
    instruction surface does not contradict the code.

A codex worker lane (`sdlc_team`)

38. As a codex worker lane, I want to see the resolved, attested plan the orchestrator is working from, so that my
    output is grounded in the current program state rather than in a spec alone.
39. As a codex worker lane, I want dispatch to be refused — naming the fix — when the resolved plan is
    unattested, tampered, ambiguous, bound to a rejected pin, or missing its plan file, so that I am never
    blind-dispatched against a plan the hooks refuse to inject.
40. As a codex worker lane, I want to never attest and never edit the plan, with that prohibition carried in my
    spec, so that a hash break at the orchestrator's next status is a real tamper signal and not my doing.
41. As a codex worker lane, I want my ledger rows written under my own agent name in the bound plan, so that the
    orchestrator's status shows my progress without me touching the plan file.
42. As the advisory `codex_lane`, I want my planning scrub kept until Phase 10 retires me, so that the round-5
    ruling is applied to workers and not silently widened.

A knowledge-base session

43. As a knowledge-base session, I want the same `plan status`/`init`/`close`/`log`/`attest` tasks as dotfiles,
    so that the muscle memory and the shared skill text are identical across repos.
44. As a knowledge-base session, I want the repo's differences (no root roadmap, no pointer, direction docs as
    the program record, next-ticket ids as ticket references, `/clear-prep` as the handoff) to be declared flags,
    so that the shared library behaves correctly here without a fork.
45. As a knowledge-base session, I want my existing lifecycle rules kept — resume reports and never archives;
    the user's task outranks next-ticket which outranks the plan's Next Step; archive only on "/clear now" and
    only when complete — with the archive step now performed by the shared close, so that adopting the shared
    workflow changes the mechanism and not the policy.
46. As a knowledge-base session, I want a tracked root `.mode` floor, so that a new slug's attestation
    requirement is a reviewed project setting rather than a flag the agent picks at creation.
47. As a knowledge-base session, I want the resume skill to stop hard-coding a plugin version, so that a plugin
    upgrade does not silently point the skill at a dead directory.
48. As a knowledge-base session, I want the eleven-day live slug closed through the shared close command once its
    round is confirmed done, so that the resolver stops offering a finished round as the live plan.

A future pwf upgrade

49. As a future pwf upgrade, I want every local command to be a thin wrapper over unmodified upstream scripts
    resolved from the installed plugin root, so that the upgrade changes plugin bytes and nothing else.
50. As a future pwf upgrade, I want a host-run test that asserts the recorded on-disk layouts still match what
    the installed version writes, so that a changed script surfaces as a failing test rather than as a silent
    misclassification.
51. As a future pwf upgrade, I want the repo to carry no deny rules, no flag enumeration and no version literal
    that upstream would have to be patched around, so that the upstream tracker is where behaviour changes are
    negotiated.
52. As a future pwf upgrade, I want the two upstream asks filed with the maintainer, so that if they ship, local
    convenience code can be deleted rather than grown.

A PR reviewer and a fresh clone

53. As a PR reviewer, I want the pointer diff and the goal-history iteration to tell me what the roadmap's phase
    and digest are and why the goal changed, so that I can review program state without access to a gitignored
    file.
54. As a fresh clone, I want the tracked root `.mode`, the tracked extract, the goal history and the pointer to
    be enough to understand where the program is, and I want handoff-check to stay green when no handoff exists,
    so that the missing gitignored plan is a working-memory gap, not a failing check.

## Implementation Decisions

### Trust model and the retirement of D4 (T1)

- Attestation is upstream's: a local SHA-256 that detects a changed plan while the digest is trusted. The
  orchestrator attests immediately after each intentional edit — post-fill of a new ticket plan, post-boundary
  roadmap edit, and at handoff — and re-attests at phase boundaries in multi-agent runs (`MIGRATION.md:188-190`).
  Workers never attest; that rule travels in every lane spec.
- Retired outright, by name: the eleven deny entries (`.claude/settings.json:31-41`: six script spellings, five
  wrapper spellings); `_ATTEST_DENY_BASES` and `check_plan_attest_deny` (`hook_selfcheck.py:750-794`) and the
  registration at `:811`; the `workflow.plan-attest-operator-only` contract (`suites.toml:1831-1866`); the four
  deny tests `test_the_live_settings_deny_every_attestation_route`, `test_both_forms_are_denied_for_every_route`,
  `test_the_deny_check_notices_a_half_written_ban`, `test_an_unreadable_settings_file_fails_rather_than_passing`
  and the two imports at `test_plan_attest.py:19-22` (the module docstring `:2-10` is rewritten); the
  operator-only text in `.claude/CLAUDE.md:20-22`, `mise.toml:997`, `main.py:1547`, the `plan_attest.py`
  docstring, and the `mise-tasks-only.md:31` table row (rewritten to "model-runnable; print the target first");
  the earlier revision's plan-init deny route, `--force`-operator-only and `--from` rejection (never built).
- Kept for non-D4 reasons: plugin-root resolution (highest numeric version, never mtime; the plugin root is
  unset in an agent's shell) and the passthrough-separator repair (the `--show` outage fix). The resolver,
  separator and passthrough tests (`test_plan_attest.py:44-79`, `:161-210`, including
  `test_the_separator_is_inserted_only_where_it_is_needed`) survive and move with the code.
- Regression prevention, two layers (F9): (a) hook-selfcheck's `plan-attest-deny` arm becomes its **inverse**,
  JSON-scoped — parse settings, iterate `permissions.deny`, fail on any entry matching the attest script, the
  selector script, the wrapper task/CLI, or the initializer, in any spelling; (b) a `regex_forbid` contract over
  `settings.json` for the same four spellings, plus `require_tokens` on the new Claude-config sentence stating
  that attestation is model-runnable tamper detection. Mutation arms: re-add one script rule → both fail; re-add
  one wrapper rule → both fail. Controls: the credential `Read(~/…)` denies stay; a description elsewhere that
  mentions the words is not a deny.
- Stated cost, accepted by Ray: an attested plan no longer means Ray approved it.

### Layout

- Root `task_plan.md`: the roadmap, ≤150 lines, upstream's autonomous template shape (Goal / Next Step /
  Current Phase / `### Phase N` blocks with primary `**Status:**` markers / Decisions ≤10 rows / Errors), exactly
  one `in_progress`, no `NEXT SESSION` heading. Edited only at rulings and phase boundaries. Gitignored, as today.
- Root `.mode`: tracked, `autonomous inject-smart`. A slug inherits the mode **token** as a policy floor
  (`init-session.sh:170-182,202-206` write `autonomous` or `autonomous gate`); root-level tokens such as
  `inject-smart` continue to govern the slug because the injector reads the root mode file too
  (`inject-plan.sh:957-967`). Root attestation: gitignored.
- One `.planning/<date>-<slug>/` per `/implement` ticket, created by upstream's initializer in slug mode.
  Its Goal line carries the profile's ticket reference (dotfiles `#NNNN`; knowledge-base the next-ticket id).
- `.planning/.archive/<id>/`: closed tickets and the archived program plan; hidden ⇒ never scanned; a
  slug-invalid id never binds.
- `.planning/.active_plan`: written by upstream's initializer; a **hint**, never written by close.
- `.planning/sessions/`: **not adopted**. Its presence arms upstream's session isolation, under which a root
  roadmap plus one live slug is ambiguous for every un-pinned session (`resolve-plan-dir.sh:345-347`). Status
  reports it and names the exits (delete the directory, or pin `PLAN_ID`).
- Root ledgers: when no ticket is live, upstream's ledger appender writes beside the root plan
  (`ledger-append.sh:62-64`); the root ledger pattern joins the ignore list (today `.gitignore:143-151` does not
  cover it).
- Tracked: the obligation extract, the goal history, the two-authority pointer.

### Binding (one live slug; `PLAN_ID` per worktree)

- The main clone carries no `PLAN_ID` and at most one live slug. Parallel tickets run in worktrees with
  `PLAN_ID` exported; `plan init --pin` appends the binding to that worktree's gitignored per-clone mise
  override file; `plan close` removes it and warns that the running shell still carries the pin.
- Root authority in a linked worktree — **provisional, pending Q1**: the roadmap lives in the main clone only;
  in a linked worktree status prints `root: n/a (linked worktree)`, `plan pointer` updates only the ticket block
  and preserves the committed root block, and the linked-worktree condition is detected from git's common
  directory, not from a flag.
- Enforcement is detection: status and the doctor report `SECOND_LIVE_SLUG`, `STALE_PIN` (env `PLAN_ID` naming
  an archived or missing directory — a binding, upstream fails closed), `SESSION_ISOLATION_ARMED`, and the
  informational pointer states. `plan init` warns (does not refuse) when another live slug exists, naming
  close-or-worktree (`D:17-19`).

### The shared planning library and CLI (`kb-setup plan …`, T2)

Lives in `kb_setup` (knowledge-base), consumed by dotfiles as a SHA-pinned dependency (`pyproject.toml:40`);
dotfiles bumps the pin after the KB PR lands. Every verb wraps an unmodified upstream script resolved from the
installed plugin root, injectable for tests. Verbs:

- `status` — resolve once and pass that identity to every reader. Reports: resolved target; per-authority
  attestation `MATCH | MISMATCH | UNATTESTED`; selection `RESOLVED | AMBIGUOUS | NONE`; **non-clean findings**
  `SECOND_LIVE_SLUG`, `STALE_PIN`, `SESSION_ISOLATION_ARMED`, `MISSING_ROOT_PLAN` (root-roadmap profile, main
  clone only), `MISSING_PLAN_FILE` (a resolved directory without a plan file); **informational states**
  `RETIRED_POINTER` (pointer names an archived id), `DANGLING_POINTER` (pointer names nothing),
  `NONCANONICAL_PHASE_MARKUP` (inline `[status]` tokens present, or more than one `in_progress`); the completion
  check's report; the ledger summary block. Exit code: non-zero only on MISMATCH/UNATTESTED of a resolved
  authority, AMBIGUOUS, or any non-clean finding; informational states exit 0. **Clean terminal states** are
  therefore: root-only with no pointer; root-only with a retired or dangling pointer; root plus one live slug
  whose pointer names it; and, in a linked worktree, ticket-only (Q1).
- `init "<title>"` — exec the initializer in slug mode from the project root (never `--autonomous`, never root
  mode); capture the printed id (collisions to `-2`, `-3`); verify post-state (directory, mode token inherited,
  attestation equals the plan digest, pointer names the id) because the initializer reports attester failure at
  exit 0 (`init-session.sh:244-254`); print `PLAN_ID=` and status; `--pin` writes the worktree binding.
- `close <id> [--force --reason "<text>"]` — precondition while the directory is live: resolved id equals
  `<id>`; the completion check reports all phases complete, or `--force` with a mandatory reason (recorded in
  the ledger note); append `phase_complete`; move to the archive and verify; **never touch the pointer** (a
  stale pointer is a hint upstream falls through, `resolve-plan-dir.sh:367-368`); drop the worktree pin and
  warn about the live shell; print the parent-phase reminder. **Idempotent by post-condition** (F14): when the
  id is already under the archive and no live directory remains, close resumes the remaining steps (ledger
  event present or appended, pin dropped, reminder) instead of failing the precondition. Non-transactional;
  every partial state is named by status.
- Parent-phase reminder grammar (F14): the ticket reference from the ticket plan's Goal line is looked up in the
  roadmap; exactly one phase block containing it → "belongs to `### Phase N`; N lists K other unchecked
  ticket references"; zero or several → "no unique parent phase" and nothing is manufactured. Flipping a roadmap
  status is a coordinator edit at the boundary, never automatic.
- `log <event> "<summary>" [--agent NAME]` — resolve exactly as upstream does: env `PLAN_ID` → live pointer →
  the single live slug → the **root roadmap** when the profile declares one and no selector is set (upstream's
  legacy path, `ledger-append.sh:47-64`). Refuse on AMBIGUOUS or a rejected selector; pass the resolved id to
  the appender explicitly.
- `attest [--show|--clear]` — print the target the resolver chose (root only when no live slug resolves and no
  selector is set, `attest-plan.sh:44-77`), then pass every flag through; warn when the root is unattested
  while a ticket plan resolves (C2). Model-runnable.
- `pointer` — write the tracked two-authority pointer and print both digests; in a linked worktree, ticket block
  only (Q1).
- `doctor-probe` — the FAIL-only dark-hooks probe both repos' doctors call.

Per-repo profile: a `[plan]` table in each repo's tracked baseline (dotfiles reuses its existing doctor
baseline; the knowledge-base adds one — it has none today), `--config` for tests. Keys: `root_roadmap`
(dotfiles true / KB false), `pointer_path` (set / none), `program_record` (goal history / direction docs),
`ticket_ref` pattern (`#NNNN` / next-ticket id), `archive_dir` (both `.planning/.archive`), `handoff_skill`
(`/session-handoff` / `/clear-prep`). No deny-set key exists.

### Tracked pointer and readers (T3)

- Pointer schema (tracked, task-text-free): `root: {plan_sha256, active_phase} | null`,
  `ticket: {plan_id, plan_sha256, active_phase} | null`, `recorded_at`. `root` is null only under a no-root
  profile; from a linked worktree the committed root block is carried forward unchanged (Q1).
- Active-phase rule (F11): the first `### Phase` heading whose following **primary** `**Status:** in_progress`
  marker is found — the canonical format upstream's two readers agree on (`check-complete.sh:95-97`,
  `ledger-summary.sh:99-100,117-130`). Inline `[status]` tokens or multiple `in_progress` phases produce the
  `NONCANONICAL_PHASE_MARKUP` warning; the `NEXT SESSION` convention (`plan_pointer.py:19`,
  `handoff_check.py:227,256`) is retired.
- Handoff-check (F7): with a handoff present it verifies both authorities against disk and reports
  `MISSING_ROOT_PLAN` under a root-roadmap profile in the main clone when no root plan exists; with no handoff
  its public path keeps today's rc 0 info line (`handoff_check.py:295-301`) so a fresh clone stays green. The
  skill's `mise run plan-pointer` fence stays verbatim; new commands go in a second fence.
- Consumer cutover (F5; provisional per Q2): the dotfiles `plan-attest` and `plan-pointer` subcommands, modules
  and their tests are deleted; mise tasks call `kb-setup plan …`; `workflow.plan-pointer-wiring` is replaced by
  `workflow.pwf-workflow-wiring` binding mise task → `kb-setup` verb registration → library function → skill
  fence, in the same change. The existing tests `test_last_next_session_heading_is_the_only_recorded_phase`,
  `test_missing_active_heading_fails_without_writing_a_pointer`, `test_public_cli_registers_plan_pointer` move
  or retire with the code; `test_plan_without_next_session_heading_is_missing_active_plan`,
  `test_pointer_stale_after_plan_bytes_change`, `test_plan_without_pointer_is_reported`,
  `test_fresh_clone_without_plan_has_no_active_plan_finding`, `test_main_prints_explicit_no_handoff_state` are
  rewritten to the new grammar and the two-authority pointer with the dispositions the verdict's §3.9 table
  lists.

### Mise tasks in both repos (T4)

`plan-status`, `plan-init`, `plan-close`, `plan-log`, `plan-attest`, `plan-pointer`, each a thin caller of the
matching verb; descriptions state the new posture. The passthrough-separator repair extends to `plan attest` so
`-- --show` reaches the script from either repo's task. Acceptance probe for the pin (F15): in a throwaway
worktree, `plan init --pin`, then a fresh process launched through mise activation from that directory reports
`PLAN_ID`; a shell started before the write still reports the old value (control). Hook attachment is the
doctor's report, not this probe's.

### Session doctor: `pwf-hooks` (T5)

- One new check in the existing SessionStart doctor (declared in the doctor baseline, enabled per repo): skip —
  never FAIL — when the doctor's own environment has planning disabled; otherwise run the real Claude hook
  dispatcher for the user-prompt-submit event with the resolved plugin root, a bounded timeout and the mise
  shims directory stripped from the child PATH; FAIL only when the shared resolver says a plan exists and the
  dispatcher's output is empty. Also surfaces every non-clean status finding (`SECOND_LIVE_SLUG`, `STALE_PIN`,
  `SESSION_ISOLATION_ARMED`, `MISSING_PLAN_FILE`). Side effects (turn and progress markers refreshed) documented.
- FAIL-only by decision; informational states are not doctor findings.
- Reaches interactive codex through the existing codex SessionStart doctor mirror (`.codex/hooks.json:35-45`);
  no new Claude function hook and no new codex hook. Verification scope is stated honestly: Claude dispatcher
  health plus codex hook configuration — not proven codex injection (a codex adapter canary is a follow-up).

### Codex lanes (T6)

- `sdlc_team` (worker lanes): no planning scrub. Both spawns (`sdlc_team.py:805-818`, `:961-968`) already pass
  no environment, so lanes inherit the session environment today; a contract forbids a scrub from being "fixed"
  back in. Pre-dispatch check at the dispatch call (`:805`, round 6), full matrix (F12):
  `NONE` (no live slug, no root plan) → dispatch; `RESOLVED + MATCH` → dispatch; `RESOLVED + MISMATCH` or
  `UNATTESTED` in a v3 mode → refuse, naming `mise run plan-attest`; `AMBIGUOUS` → refuse, naming pin-or-close;
  `REJECTED_BINDING` (`PLAN_ID` set, resolver empty at rc 0) → refuse, naming the stale pin;
  `MISSING_PLAN_FILE` → refuse. `PLANNING_DISABLED=1` in the dispatcher's own environment is recorded as
  `PLANNING_DISABLED_INHERITED` in the dispatch record — provisionally warn-and-dispatch (Q4). Never auto-attest
  at dispatch.
- `codex_lane` (advisory): keeps its scrub and the `workflow.codex-lane-planning-isolation` contract's
  behaviour tokens until Phase 10; its documentation token (the persistence rule's table row,
  `suites.toml:1892`) is updated in T7 together with the row it pins.
- Interactive codex uses the globally enabled pwf codex plugin with its seven trusted hooks; this design adds
  no hook and requires no new `/hooks` trust.
- Phase 10 step 5's pwf items (`task_plan.md:411-418`) are superseded and the supersession is recorded in Phase
  10's rulings block: no absolute plan root in tracked settings env, no `sdlc_team` scrub, no lint forbidding
  slug plans or the pointer, no "design decisions wait for pwf deep extraction" hold.

### Skills, rules, agents (T7)

- Consumer inventory (F6, F7): `/session-handoff`, `/session-resume`, `verify` (`SKILL.md:18` handoff-check
  row), `session-review` (`SKILL.md:71-88`), `pwf-scribe`, the persistence rule's file-role table (now "the
  resolved plan directory's findings/progress; coordinator-attested plan"), `notepad-enforcement.md:8` and
  `agent-artifact-conventions.md:76` ("root `findings.md`" → "the resolved plan's `findings.md`"),
  `mise-tasks-only.md:31`, the SubagentStart contract tokens in `hook_selfcheck._SETTINGS_WIRING`, the
  generated skills mirror, the memory-index note flipped at the next handoff.
- `/session-handoff`: keep the pointer fence; add status; on MISMATCH and this session edited the plan → attest
  then re-status; on MISMATCH and it did not → a finding, reported, not attested; then a ledger note bound to
  the resolved plan (ticket if live, else root), the pointer (both digests), the doctor. Checklist: every
  declared, resolving authority MATCH; at most one live slug; completed ticket closed. OWED never contains an
  attest.
- `/session-resume`: status, then the three-way compare (file digest vs attestation vs committed pointer):
  all equal → clean; file ≠ attestation → "unattested edit after handoff", first offer the attest command;
  attestation ≠ pointer → "re-attested after the pointer was committed" → fix-first. Plan line:
  `root → <phase> [MATCH] | ticket <id> → <phase> [MATCH|TAMPERED]`. Stale pin → first offer "new terminal".
- Shared vs repo-specific (F8): the shared `pwf-workflow` skill and rule carry the posture, layout, who attests
  when, the state vocabulary, and the operator's stops; **invocation policy** stays in each repo's lifecycle
  skills — dotfiles' handoff/resume as above; the knowledge-base's `/session-resume` keeps "report, never
  archive" and its task precedence, `/clear-prep` keeps "archive only on '/clear now' and only when complete"
  and performs the archive through `plan close`. rule-sync guarantees the shared rule is declared in both repos;
  the shared skill text is kept identical by the mechanism Q3 selects.
- The close skill requires an `AskUserQuestion` before `--force`; the ticket-creation skill documents
  `mise run plan-init` as the route (`/pwf` stays allowed: it creates root files first and then attests
  whichever plan resolves, `pwf.md:7-12`, `init-session.sh:481-485,235`).

### Plan migration (T8; one-time, coordinator-executed, no operator step)

Seven verifiable outcomes, in order: (1) archive the old program plan and its attestation byte-for-byte under
`.planning/.archive/`, and move the leftover 2026-09-21 directory there; (2) enumerate every unchecked item and
"still open" reference from the old plan into the tracked extract, each mapped to a roadmap line, an existing
issue, or dropped-with-reason (drops are asked); (3) install the ≤150-line roadmap with Phases 10 and 11 and the
pwf addendum condensed to decision rows, canonical markers only; (4) append the goal-history iteration — writer:
the coordinator, on the branch, before the first ticket init — whose goal text names the root roadmap plus the
attested ticket plan as task authority and attestation as orchestrator-run tamper detection (032 recorded the
re-ordering and trust-model change at handoff; this is the later iteration round 6 assigns to T8); (5) reconcile
selection — no live slug, no `.planning/sessions/`, pointer absent or retired, environment `PLAN_ID` unset;
(6) write the pointer, attest the roadmap (target printed: root), show; (7) verify — status: root MATCH, Phase
11, exit 0 with no non-clean finding; ledger-summary heading equals pointer heading; doctor clean; the next prompt
injects a plan body. Outcome (7) is #910's reproduction turned green.

### Knowledge-base parity (T9)

Tracked root `.mode` floor (its ignore file covers `/.planning/` only, `.gitignore:256-260`); drop the version
literal from the resume skill; a `[plan]` baseline with the KB profile; resume and clear-prep call the shared
status and close under their existing policies; the archive reference becomes a pointer to the shared close;
close the eleven-day live slug (`.planning/2026-09-12-session-review-round-dag`) through the shared close after
confirming with Ray that its round is done; add the `host_only` marker and the `CI == "true"` skip convention
its conftest lacks; the shared rule via rule-sync. No deny set.

### Upstream asks (T10; file, do not block)

An explicit root-target flag for the attester; a Claude Code / Codex analogue of Pi's `/plan-execute`.

### Operator's remaining stops

`AskUserQuestion` on genuine ambiguity or irreversibility (force-close with reason; an obligation dropped in the
migration; the goal-text wording; the five questions above); user-invoked protocol verbs; codex `/hooks` trust
after a plugin upgrade; plugin upgrades and `/clear`; PR review of the pointer and goal history. Not a stop:
attestation, plan creation, closing a complete ticket, logging, status.

## Testing Decisions

What makes a good test here: it drives a public entry point against a real or recorded-real filesystem state,
and it carries both arms — the state that must be reported and a control that must not be — because every defect
this migration closes was a probe or a gate that could only pass.

**Execution contract (F13).** Tests are assigned to a repo and a gate; `host_only` tests run on every developer
host and inside that repo's ship gate, and are skipped only when `CI` equals the string `true`
(`conftest.py:31`; the knowledge-base adopts the same convention in T2). A `host_only` test whose plugin is not
installed **fails** (never skips), matching the "missing binary fails the gate" sibling. Recorded layouts live
under the knowledge-base test tree with a provenance stamp (plugin version, script digests) and normalised
nonce/timestamp fields; one `host_only` arm re-records and diffs.

- **Shared library and CLI (knowledge-base; KB pytest + KB ship gate).** Throwaway git repos driven through
  `kb-setup plan …` with the REAL installed scripts (`host_only`). Arms: init prints the id and passes
  post-state verification, and fails legibly on a forged exit-0 initializer whose attester did not write; status
  names MATCH after init, MISMATCH after an edit, AMBIGUOUS with two live slugs, `SESSION_ISOLATION_ARMED` with a
  sessions directory beside a root plan (control: same tree without it), `RETIRED_POINTER` (exit 0) after an
  archive move, `STALE_PIN` (non-zero) when `PLAN_ID` names the archived id, `MISSING_PLAN_FILE` for a
  directory whose plan was renamed, `NONCANONICAL_PHASE_MARKUP` for mixed and multiple-active plans, and the
  planning-disabled environment case; the phase heading agrees across pointer, ledger summary and completion
  check for a canonical plan (control) and is warned for mixed format; close refuses an incomplete plan, requires
  a reason with `--force`, succeeds on a complete one, moves the directory, leaves the pointer untouched, drops
  the pin, resumes after a simulated partial failure; log refuses AMBIGUOUS and a rejected selector, writes under
  the bound id, and writes beside the root plan when only the roadmap exists; attest prints its target and
  forwards `--show`; the parent-phase reminder for one, zero and two matching phases. CI twins for
  classification, pointer schema, phase rule, close post-conditions and both profiles run on the recorded
  layouts. The pin probe (F15) runs `host_only`.
- **Readers (dotfiles pytest).** Handoff-check at its public `main()` seam and its classification seam: no
  handoff → rc 0 info line; handoff + root profile + no root plan → `MISSING_ROOT_PLAN`; no-root profile → none;
  `NEXT SESSION` fixture fails; canonical fixture passes; two-authority pointer written and verified; stale
  pointer after a byte change still caught.
- **Doctor `pwf-hooks` (dotfiles pytest; dispatcher arm `host_only`, fixture twin in CI).** Live-plan fixture
  with planning disabled in the CHILD → FAIL (the canary); unset → clean; the doctor's own environment disabled
  → skipped; each non-clean finding with a control.
- **`sdlc_team` (dotfiles pytest).** Dispatch seam with a fake spawn: every matrix row (attested → dispatch;
  tampered/unattested → no spawn, message names the attest task; ambiguous; rejected binding; missing plan file;
  none). Supervisor→worker boundary (`host_only`): the real supervisor path with a stand-in argv that prints its
  environment asserts the worker inherits `PLAN_ID` when set and lacks the disable flag (positive) and reports
  the unset state (control) — the `codex_lane` real-child shape, which is genuine prior art.
- **Contracts (dotfiles, `dotfiles-setup verify run` + hook-selfcheck).** The operator-only contract is
  deleted; the inverse selfcheck arm and the forbid contract pass on the retired settings and both fail on a
  re-added script rule and on a re-added wrapper rule; the wiring contract binds skill → task → CLI → library;
  a contract forbids a planning scrub in `sdlc_team`; the `codex_lane` isolation contract keeps its behaviour
  tokens with the documentation token updated.
- **Documentation surface.** `lint-docs`, mirror parity, `rule-sync` in both repos, the handoff-fence contract,
  the shared-skill parity check (Q3); skill evals in dry-run for ask-before-force.
- **Live arms recorded in the tickets.** After T1: the model runs the read-only attest form and gets exit 0
  while a covered credential-file read is still denied (control) — this arm is the one the routing change makes
  necessary. After T8: outcome (7) above.

Prior art, worded to what it proves: the attest wrapper tests prove plugin resolution through an injected home
and that the passthrough call site is wired (`test_the_documented_read_only_form_reaches_the_script` checks
source wiring and parser output, `test_plan_attest.py:168-187`; it does not execute mise or the script); the
handoff-check suite is mostly at `check()` with public-CLI coverage in `test_main_*`; the `sdlc_team` fake-spawn
"no process launched" arms; the doctor's assembled-setup check functions; the `codex_lane` real-child
positive+control test (genuine); the `host_only` marker; the knowledge-base conftest git fixtures.

## Out of Scope

- The `pr-loop` ship → fix → land loop (its own spec).
- Phase 10 work: retiring `codex_lane` and its scrub, the one-codex-entry-point consolidation, RESEARCH mode,
  role-typed models, codex-native install and the daemon gate.
- Adopting `/plan-loop`, `/plan-goal`, gated mode, session isolation (`.planning/sessions/`), `phase-status`,
  or any Claude-side approval gate for attestation; auto-attest in any hook or at dispatch; a function hook or a
  codex hook for plan-doctor; `PLAN_ID` in tracked settings env or in the main clone; rename-based archival;
  automatic roadmap status flips on close; a shared pointer as the binding.
- A codex-side doctor arm through the codex plugin's own adapter (follow-up); the knowledge-base's coreutils
  shim tax (its own ticket).
- Changing upstream behaviour locally; the two upstream asks are filed, not blocked on.
- Any change to how the plan's contents are trusted as instructions (delimiter framing, nonce, prompt-injection
  posture).

## Further Notes

**Issue relationships (F16).** This migration **absorbs #910** ("PLAN TAMPERED fires every prompt and has no real
tracking issue"): T5's dark-hooks probe, T6's pre-dispatch refusal, and T8's outcome (7) — the next prompt injects
a body — are #910's reproduction turned green; #910 closes with T8. This migration **precedes #1327** ("Land the
native AgentsView service (#1141) and settle its parked worktree"): #1327 is the first ticket to run under the new
workflow — its parked worktree becomes the first `PLAN_ID`-pinned worktree — so it must not start before T8 lands
and Q1 is answered.

**Ticket order and dependencies.** T1 first and independently (everything after it is model-runnable in this
repo only once the deny is gone; ships both regression layers). T2 is a knowledge-base PR (library, CLI, KB
`host_only` convention, recorded layouts), then the pin bump in dotfiles. T3 (readers + consumer cutover + the
contract migration, one dotfiles change), T4 (mise tasks both repos), T5 (doctor), T6 (`sdlc_team`) are
independent after the pin bump; T4 precedes T7 (skill text naming a task that does not exist fails the docs gate);
T3 precedes T8 (the new roadmap shape fails today's handoff-check). T7 after T3–T6; T8 last on the dotfiles side.
T9 after T2, in parallel with T3–T6; closing the eleven-day slug waits for Ray's confirmation. T10 any time.

**Rulings encoded.** Upstream trust model supersedes D4 and the round-2 hardening; root roadmap plus per-ticket
slugs; `PLAN_ID` per worktree; `.planning/.archive/`; one merged workflow in `kb_setup` with per-repo flags;
skill → mise task → library layering; close model-runnable when complete, `--force` behind an `AskUserQuestion`,
pointer untouched; `sdlc_team` lanes see the plan, check at the dispatch call; `codex_lane` scrub kept until
Phase 10; Phase 10 step 5's pwf items superseded; goal-history iteration written by the coordinator with the
changed goal text; the knowledge-base's eleven-day slug archived via the shared close.

**Deciding risk.** Stale memory: the memory index, transcripts, the config paragraph, task descriptions and test
docstrings all still say "operator-only"; a later session acting on that will re-add the deny from habit. The
inverse selfcheck arm and the forbid contract are the control arms (both fail on any of the eleven spellings);
T7's rewrite and the memory-index flip are the rest.

**Unverified, to be settled by the tickets.** That the per-worktree mise override reaches a `claude` process
launched from that shell (the F15 probe settles it); the codex hook trust currency after a plugin upgrade; whether
the knowledge-base already has a plugin-root resolver (none found under `kb_setup/` beyond one hard-coded path in
`eval_cases.py:53`; the dotfiles resolver moves).

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed 3.20.7 source
  read for every finding: `resolve-plan-dir.sh`, `ledger-append.sh`, `set-active-plan.sh`, `init-session.sh`,
  `check-complete.sh`, `ledger-summary.sh`, `attest-plan.sh`, `inject-plan.sh`, `plan-doctor.sh`,
  `hooks/claude-hook.sh`, `commands/plan-attest.md`, `commands/pwf.md`, `docs/attestation-locking.md`,
  `MIGRATION.md`, `README.md`, `CHANGELOG.md`.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `task_plan.md` addendum and Phase 10,
  `.claude/settings.json`, `.gitignore`, `.mode`, `docs/agents/plan-pointer.json`, `docs/agents/goal-history.md`,
  `python/verification/suites.toml`, `hook_selfcheck.py`, `handoff_check.py`, `plan_pointer.py`, `sdlc_team.py`,
  `rule_sync.py`, `verify.py`, `pr.py`, `main.py`, `mise.toml`, `tests/conftest.py`, `tests/test_plan_attest.py`,
  `tests/test_plan_pointer.py`, `tests/test_handoff_check.py`, `.codex/hooks.json`, the rules and skills named
  above, issues #910 and #1327, and the input reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `.planning/` state,
  `.gitignore`, `pyproject.toml`, `tests/conftest.py`, `python/src/kb_setup/` layout, the session-resume and
  clear-prep skills.
