# Spec draft — pwf 3.20.7 current-workflow migration (Brief G, `/to-spec` deliverable)

> Written by a Fable lane (`general-purpose`, `model: fable`) on 2026-09-23 from the design of record
> `pwf-migration-fable-round3-2026-09-23.md` (T1–T10), its base `pwf-migration-fable-revision-2026-09-23.md`,
> `pwf-migration-codex-astra-verdict-2026-09-23.md`, `pwf-upstream-tracker-review-2026-09-23.md`, and the
> binding rulings in `task_plan.md` § "Addendum — pwf current-workflow migration" (rounds 1–6). The briefs
> file's "Shared context" statements about D4 / operator-only attestation are SUPERSEDED by the round-4 ruling
> and are not carried here. The coordinator publishes the spec (everything below `## Problem Statement`) as a
> GitHub issue after Ray reviews the `## Seams` section, which is removed before publishing.

## Seams

**Verdict on the coordinator's candidate: AGREE, with three refinements (one of them a DIFFER on altitude for
two behaviours).** I re-derived the seams from the design of record and from a live probe of the real installed
pwf 3.20.7 scripts in a throwaway git repo (no mocks; positive arm plus four negative arms — every arm
discriminated). Details, then the disagreements.

**(a) Primary seam — the new `kb-setup plan …` CLI (`status`, `init`, `close`, `log`, `attest`, `pointer`,
`doctor-probe`) run against a throwaway git repo using the REAL installed plugin scripts. AGREE.**

- The probe proved the seam is reachable with real scripts and that every state the CLI must classify is
  producible without a mock: `init-session.sh "<title>"` in a throwaway repo carrying a root `.mode` of
  `autonomous inject-smart` produced an attested slug whose `.mode` inherited the floor and whose `.attestation`
  equalled the plan's SHA-256; `check-complete` reported 0/5; the resolver returned the slug; `ledger-summary`
  named Phase 1. Negative arms: appending one line to the plan gave MISMATCH and the real dispatcher emitted
  `[PLAN TAMPERED — injection blocked]`; a second live slug made the resolver return empty with
  `PWF_PLAN_AMBIGUOUS_V1` while an explicit `PLAN_ID` still bound; moving a slug under `.planning/.archive/`
  left `.active_plan` reported as a "stale pointer", the resolver fell to the remaining live slug, and a
  `PLAN_ID` naming the archived id resolved EMPTY; `ledger-append` with `PLAN_ID` wrote into the bound slug.
  Those are exactly the C1/C2/C3/C4/C7 states the design keeps.
- Refinement 1 (altitude within the seam): the CLI is the right height — the mise tasks are thin callers that a
  `require_tokens` contract binds, and testing the CLI covers the library. Tests inject the plugin root (the
  repo's existing resolver already takes a `home`), so a test never reads the developer's live cache by
  accident and never runs against a version it did not choose.
- Refinement 2 (where it can run): CI runs on a bare runner with no plugin cache, and this repo deliberately
  vendors no third-party scripts. The real-scripts tests therefore carry the existing `host_only` marker
  (auto-skipped only when `$CI` is set; they run on every developer host and inside `mise run ship`'s pytest
  gate). That is the repo's sanctioned precedent, not a new skip. The knowledge-base has no such marker or
  conftest convention today; T2 adds it there as a parity item, because the library and its tests live in the
  knowledge-base.
- Refinement 3 (what CI still proves): the pure-logic half — state classification from resolver/attestation
  outputs, the two-authority pointer schema, the active-phase rule, per-repo profile flags, the close
  post-conditions — also gets CI-runnable tests against fixture trees whose byte layouts are the ones the real
  scripts produce (`.attestation`, `.mode`, `.nonce`, `.stop_blocks`, `.active_plan`, `ledger-<agent>.jsonl`;
  recorded during the probe). Those are fixtures of real layouts, not mocks of behaviour, and one `host_only`
  arm asserts the recorded layout still matches what the installed version writes, so fixture drift after a
  pwf upgrade fails a test rather than hiding.

**(b) Secondary seam — existing `dotfiles-setup` entry points for dotfiles-only behaviour. AGREE on the
behaviours; DIFFER on altitude for two of them.**

- `handoff-check` stays at the CLI seam it has today (git-init fixture repo, verdict list). AGREE.
- Plan pointer: the design moves pointer writing into `kb-setup plan pointer`, so its behaviour is tested at
  seam (a); the `dotfiles-setup plan-pointer` alias survives only as a re-export bound by a contract, not by
  behaviour tests. Minor DIFFER from the candidate's framing.
- Doctor `pwf-hooks` check and the `sdlc-team` pre-dispatch refusal: DIFFER — test these at the repo's existing
  function seams, not at the CLI. Every doctor check here is a function that takes the assembled setup and
  returns a list of findings, and every dispatch test here fakes the process spawn and asserts either the
  recorded argv/env or that no spawn happened. Reaching those two through the CLI would need a real codex and
  a real session doctor run, buys nothing the function seam does not, and breaks with the prior art. The CLI
  registration for both remains covered by contracts.

**(c) Config contracts via `dotfiles-setup verify run` plus hook-selfcheck for the D4 retirement. AGREE, with
one addition.** The "attest deny must not return" contract is a `regex_forbid` over the settings deny list,
and its mutation arm (re-add one attest deny rule, run verify, expect FAIL) is the test of the contract — the
reversal's own control arm against the stale-memory risk the design names. hook-selfcheck loses its
`plan-attest-deny` arm entirely rather than converting it. Two further contracts belong here: the
skill → task → CLI → library wiring of the new workflow, and "no planning scrub in `sdlc_team`" (while the
`codex_lane` scrub contract is kept unchanged until Phase 10).

**(d) A seam the candidate did not name: the documentation surface.** Skills, rules and agent definitions
change in T7; they are tested by the existing gates — `lint-docs`, the skills mirror parity step, `rule-sync`
across both repos, and the `require_tokens` contract that pins the `mise run plan-pointer` fence in the
handoff skill. T8 (the plan migration) is a one-time operation, verified live through seam (a) (root MATCH,
Phase 11, ledger heading == pointer heading) and by session-review's append-only goal-history check; it adds no
tests.

**Count.** Two behavioural seams (the shared CLI in a throwaway repo; the dotfiles function/CLI seams for
dotfiles-only consumers) plus contracts. The ideal of one is not reachable because the dotfiles-only consumers
(handoff-check, doctor, sdlc_team) cannot be driven through the knowledge-base CLI, and pushing them there
would move dotfiles behaviour into the shared package for test convenience alone.

**One judgment surface is deliberately untested:** the skill-level requirement that `plan-close --force` on an
incomplete ticket is preceded by an `AskUserQuestion`. It is a `clarify-before-acting` judgment, not a
permission, so it is exercised by skill evals, not by pytest; the CLI's `--force` flag itself is tested.

---

## Problem Statement

Ray runs a multi-session, multi-agent program in two repositories (dotfiles and knowledge-base) with one Claude
orchestrator and codex worker lanes. The planning-with-files (pwf) plugin is supposed to carry the program's
working memory between sessions, but the way it is set up today makes it a cost centre:

- **Attestation is a chore that lands on Ray.** Because the plan is one 1,647-line root `task_plan.md` under
  `autonomous inject-smart`, every edit to it breaks its attestation and the plugin refuses to inject the plan
  until a human re-attests. Attestation was made operator-only in this repository (D4, 2026-09-02) on the belief
  that it is a human-approval boundary; upstream's maintainer says it is not ("not a keyed signature or proof of
  human approval"). The result is roughly twenty manual `! mise run plan-attest` runs in twenty-one days, an
  eleven-day outage of the read-only `--show` form that nobody noticed because the operator path was the only
  path, and sessions that routinely end with "attest is owed".
- **The plugin's own view of the plan is stale.** The machine-readable phase markers say Phase 2b is current
  while the tracked pointer says Phase 11; ledgers hold zero entries; `plan-doctor` warns about hash mismatches;
  codex lanes have received `[PLAN TAMPERED]` instead of the plan. Turn-start injection names the wrong phase.
- **Two repositories, two workflows.** The knowledge-base uses slug plans with an eleven-day-old live plan, its
  own archive recipe, a hard-coded plugin version in its resume skill, and no attestation posture; dotfiles uses
  a root plan, a deny list, a wrapper task, and a tracked pointer. Every improvement is made twice or in one
  place only.
- **Local hardening fights upstream.** The deny list, the wrapper's operator-only docstrings, the selfcheck arm
  and the verification contract all encode a trust model upstream does not share, so each pwf upgrade risks a
  local patch that upstream will never carry. Ray's standing instruction is "assume what we are doing is wrong
  and follow upstream so pwf updates land with minimal change".
- **Leftovers and gaps.** A `.planning/2026-09-21-graphify-…/` directory that holds only an archived plan; no
  `.planning/.archive/`; no way for a session to see in one line whether the plan it is about to trust is the
  resolved one, attested, unambiguous, and current.

From Ray's seat: he wants to stop being the attestation button, wants the plan to be small and true, wants
codex lanes to see the plan, wants one workflow for both repos, and wants the next pwf release to be a plugin
update rather than a migration.

## Solution

Adopt pwf 3.20.7's current workflow whole, under upstream's trust model, and put the human-review boundary where
a PR can actually see it.

- **Layout.** The root `task_plan.md` becomes a short program roadmap (≤150 lines, upstream's autonomous
  template shape, one `**Status:** in_progress` phase). Each `/implement` ticket gets its own scoped plan under
  `.planning/<date>-<slug>/`, created the upstream way (attested at creation, inheriting the tracked root `.mode`
  floor). Closed tickets move to `.planning/.archive/<id>/`, where the resolver cannot see them. The 1,647-line
  program plan is archived byte-for-byte, and its still-open obligations are mapped into a tracked decisions
  extract, the roadmap, or an existing issue.
- **Trust model.** Attestation is tamper detection by the orchestrator. The orchestrator creates a ticket plan,
  fills it, and attests it in the same turn; re-attests after each intentional edit and at phase boundaries;
  never attests a change it did not make (that is the tamper signal doing its job). Workers never attest. The
  D4 deny rules, the operator-only wrapper posture, their selfcheck arm and their contract are retired; a
  contract guarantees the deny does not return. Human review moves to the tracked artifacts a PR reviews: the
  digest pointer (root and ticket) and the append-only goal history.
- **Binding.** The main clone holds at most one live ticket plan and no `PLAN_ID`; parallel tickets run in
  worktrees with `PLAN_ID` exported (optionally pinned per worktree). Enforcement is detection, not denial: the
  status command and the doctor report a second live slug or a stale pin.
- **One merged workflow.** A shared planning library and a `kb-setup plan` command group (status, init, close,
  log, attest, pointer, doctor-probe) live in the knowledge-base's `kb_setup` package that dotfiles already
  consumes as a pinned dependency. Both repos expose the same thin mise tasks; per-repo differences (root
  roadmap or not, pointer path, program record, ticket reference shape, handoff skill) are declared flags, never
  a second workflow. Built strictly as reusable skill(s) → mise task(s) → library function(s), each layer calling
  the one below.
- **Consumers follow.** The pointer records both authorities; the active-phase rule becomes the one pwf's own
  scripts use; handoff-check gains a missing-root verdict; the session doctor gains a FAIL-only "dark hooks"
  probe of the real dispatcher plus live-slug and stale-pin findings; `/session-handoff` and `/session-resume`
  run status, classify a mismatch by who edited, and offer the attest command as the clickable next step; codex
  worker lanes (`sdlc_team`) see the plan and are refused dispatch when the resolved plan is unattested or
  tampered, naming the command that fixes it. The advisory `codex_lane` keeps its planning scrub until Phase 10
  retires that lane.
- **Knowledge-base parity.** Same tasks, same skill text via rule-sync, a tracked root `.mode` floor, no version
  literal, its eleven-day slug closed through the shared close command once its round is confirmed done.
- **Upstream first for what upstream lacks.** File (do not block on) two asks: an explicit root-target flag for
  the attester, and a Claude/Codex analogue of Pi's `/plan-execute`.

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
5. As the operator, I want the D4 deny rules retired and a contract that fails if they come back, so that a
   later session acting on stale memory cannot silently re-impose the old posture.
6. As the operator, I want one workflow across dotfiles and knowledge-base with differences declared as flags,
   so that I maintain one thing and every improvement lands in both repos.
7. As the operator, I want to be asked before an incomplete ticket is force-closed, before a listed obligation is
   dropped in the migration, and before the goal text changes, so that irreversible or judgment-laden steps still
   pass through me.
8. As the operator, I want the next pwf release to be a plugin update rather than a migration, so that upstream
   improvements arrive with minimal local change.
9. As the operator, I want the leftover `.planning/2026-09-21-graphify-…/` directory and the old program plan
   archived rather than deleted, so that nothing is lost and nothing stale is selectable.
10. As the operator, I want every open obligation in the old plan accounted for (roadmap line, existing issue,
    or dropped-with-reason) before the old plan is retired, so that live work does not vanish in the move.
11. As the operator, I want the plugin's own phase view, the pointer, and the ledger summary to name the same
    phase, so that turn-start injection and my own reading agree.
12. As the operator, I want a one-line status that says which plan resolves, whether it is attested, whether
    selection is ambiguous, and whether anything points at an archived plan, so that I never trust a plan the
    plugin is not actually injecting.
13. As the operator, I want the accepted cost stated plainly — an attested plan no longer means I approved it —
    so that no future session infers an approval that was never given.

The orchestrator agent (the Claude architect session)

14. As the orchestrator, I want to create a ticket plan with one command that prints the plan id and its status,
    so that I do not hand-type a version-pinned plugin path or guess whether creation attested.
15. As the orchestrator, I want to fill the ticket plan and attest it myself in the same turn, so that the tamper
    gate is armed on my own bytes without waiting for a human.
16. As the orchestrator, I want the attest command to print which plan it will target before writing, so that I
    never lock a slug when I meant the roadmap, or the reverse.
17. As the orchestrator, I want to be told when the roadmap is unattested while a ticket plan is live, so that I
    sequence roadmap edits to the boundary where the roadmap is the resolved plan.
18. As the orchestrator, I want to close a completed ticket with one model-runnable command that archives it,
    records the ledger event, drops my worktree pin, and reminds me which roadmap phase it belongs to, so that
    closing is routine and never leaves a stale selection behind.
19. As the orchestrator, I want closing to refuse an incomplete ticket unless I pass a force flag after asking
    Ray, so that "done" keeps meaning every phase complete.
20. As the orchestrator, I want closing to never touch the shared active-plan pointer, so that a stale pointer
    falls through to the roadmap by upstream's own rule and no second live slug can be silently promoted.
21. As the orchestrator, I want to log progress and notes to a ledger bound to the resolved plan, and to be
    refused when resolution is empty or ambiguous, so that ledger rows never land in the wrong plan.
22. As the orchestrator, I want status to distinguish MATCH, MISMATCH, UNATTESTED, AMBIGUOUS, ARCHIVED-REFERENCED
    and STALE-PIN, so that my next action is determined by the state and not by guesswork.
23. As the orchestrator, I want `/session-handoff` to classify a mismatch by whether this session edited the plan
    (attest if I did; report a finding if I did not), so that tamper detection still pays exactly where it should.
24. As the orchestrator, I want `/session-resume` to three-way compare file digest, attestation and committed
    pointer, so that "unattested edit after handoff" and "re-attested after the pointer was committed" are named
    as distinct disagreements with distinct first offers.
25. As the orchestrator, I want the handoff's owed list to never contain an attest, so that a handoff is
    complete when I write it rather than pending on Ray.
26. As the orchestrator, I want the pointer to record both the roadmap and the ticket plan, so that an
    unrecorded roadmap change is detectable even while a ticket is selected.
27. As the orchestrator, I want the active-phase rule to be the one pwf's own scripts use, so that my pointer,
    the ledger summary and the completion check can never disagree about the current phase.
28. As the orchestrator, I want to record a mid-ticket ruling in the ticket plan's decisions and batch roadmap
    edits to the boundary, so that the roadmap changes only at rulings and phase boundaries.
29. As the orchestrator, I want to append a goal-history iteration with the changed goal text when the plan
    migration lands, so that the program record states what task authority now is and who writes it.
30. As the orchestrator, I want the session doctor to fail loudly when a plan resolves but the real dispatcher
    injects nothing, so that dark hooks are caught at session start rather than noticed as silence.
31. As the orchestrator, I want the doctor and status to report a second live slug in the main clone or an
    environment pin naming an archived plan, so that I fix selection before I trust injection.
32. As the orchestrator, I want to run a ticket in a worktree with `PLAN_ID` pinned per worktree, so that two
    parallel tickets never share a pointer or an mtime guess.
33. As the orchestrator, I want `/pwf` to keep working as upstream ships it while the documented ticket route is
    the thin init task, so that I follow upstream by default and only add what upstream lacks (path resolution and
    the worktree pin).
34. As the orchestrator, I want the wrapper skills to call other skills, the tasks to call tasks, and the
    functions to call functions, so that no layer re-implements the one below it.
35. As the orchestrator, I want the skills and rules that mention "operator-only" or "task_plan.md is the sole
    task authority" rewritten in the same change, so that the instruction surface does not contradict the code.

A codex worker lane (`sdlc_team`)

36. As a codex worker lane, I want to see the resolved, attested plan the orchestrator is working from, so that my
    output is grounded in the current program state rather than in a spec alone.
37. As a codex worker lane, I want dispatch to be refused — naming the attest command — when the resolved plan is
    unattested or tampered, so that I am never blind-dispatched against a plan the hooks refuse to inject.
38. As a codex worker lane, I want to never attest and never edit the plan, with that prohibition carried in my
    spec, so that a hash break at the orchestrator's next status is a real tamper signal and not my doing.
39. As a codex worker lane, I want my ledger rows written under my own agent name in the bound plan, so that the
    orchestrator's status shows my progress without me touching the plan file.
40. As the advisory `codex_lane`, I want my planning scrub kept until Phase 10 retires me, so that the round-5
    ruling (worker lanes see the plan) is applied to workers and not silently widened.

A knowledge-base session

41. As a knowledge-base session, I want the same `plan status`/`init`/`close`/`log`/`attest` tasks as dotfiles,
    so that the muscle memory and the skill text are identical across repos.
42. As a knowledge-base session, I want the repo's differences (no root roadmap, no pointer, direction docs as
    the program record, next-ticket ids as ticket references, `/clear-prep` as the handoff) to be declared flags,
    so that the shared library behaves correctly here without a fork.
43. As a knowledge-base session, I want a tracked root `.mode` floor, so that a new slug's attestation
    requirement is a reviewed project setting rather than a flag the agent picks at creation.
44. As a knowledge-base session, I want the resume skill to stop hard-coding a plugin version, so that a plugin
    upgrade does not silently point the skill at a dead directory.
45. As a knowledge-base session, I want the eleven-day live slug closed through the shared close command once its
    round is confirmed done, so that the resolver stops offering a finished round as the live plan.
46. As a knowledge-base session, I want `/clear-prep` and `/session-resume` to call the shared status and close
    commands instead of their own shell recipes, so that archive semantics cannot drift between repos.
47. As a knowledge-base session, I want the shared workflow rule to ride the existing cross-repo rule-sync gate,
    so that the two repos cannot silently diverge on which concerns are governed.

A future pwf upgrade

48. As a future pwf upgrade, I want every local command to be a thin wrapper over unmodified upstream scripts
    resolved from the installed plugin root, so that the upgrade changes plugin bytes and nothing else.
49. As a future pwf upgrade, I want a host-run test that asserts the recorded on-disk layouts still match what
    the installed version writes, so that a changed script surfaces as a failing test rather than as a silent
    misclassification.
50. As a future pwf upgrade, I want the repo to carry no deny rules, no flag enumeration and no version literal
    that upstream would have to be patched around, so that the upstream tracker — not a local patch — is where
    behaviour changes are negotiated.
51. As a future pwf upgrade, I want the two upstream asks (root-target attest, a Claude/Codex approval gate)
    filed with the maintainer, so that if they ship, local convenience code can be deleted rather than grown.

A PR reviewer and a fresh clone

52. As a PR reviewer, I want the pointer diff and the goal-history iteration to tell me what the roadmap's phase
    and digest are and why the goal changed, so that I can review program state without access to a gitignored
    file.
53. As a fresh clone, I want the tracked root `.mode`, the tracked extract, the goal history and the pointer to
    be enough to understand where the program is, so that the missing gitignored plan is a working-memory gap,
    not a knowledge gap.

## Implementation Decisions

### Trust model and the retirement of D4

- Attestation is upstream's: a local SHA-256 that detects a changed plan while the digest is trusted. The
  orchestrator (the Claude architect session) attests immediately after each intentional edit — post-fill of a
  new ticket plan, post-boundary roadmap edit, and at handoff — and re-attests at phase boundaries in
  multi-agent runs, as upstream's migration guide prescribes. Workers never attest; that rule travels in every
  lane spec.
- Retired outright: the attest/selector deny rules (both bare and argument-carrying forms, shell and PowerShell
  twins, the mise task and the CLI beneath it); the hook-selfcheck presence arm and its deny-bases table; the
  operator-only verification contract; the operator-only docstrings, task description, CLI help and the
  Claude-specific config paragraph; the plan-init-as-deny-route, `--force`-operator-only and `--from`-rejection
  items of the earlier revision (never built). The selector deny goes too — it was collateral that denied a
  read-only `sed -n` of the script.
- Kept for non-D4 reasons: the attest wrapper's plugin-root resolution (the plugin root is unset in an agent's
  shell and the cache path is version-pinned) and its passthrough-separator repair (the `--show` outage fix).
  The wrapper migrates into the shared library; its docstring is rewritten to the new posture.
- New contract, "attest deny must not return": a forbid-pattern over the settings deny list for any attest or
  selector script rule, plus a required sentence in the Claude-specific config stating attestation is
  model-runnable tamper detection. It is the control arm against stale memory (index, transcripts and prose all
  still say "operator-only"). Its mutation arm — re-adding one deny rule makes verification fail — is part of the
  ticket's verification.
- Stated cost, accepted by Ray: an attested plan no longer means Ray approved it. Human review moves to the
  tracked digest pointer and the append-only goal history, which a PR reviews.

### Layout

- Root `task_plan.md`: the program roadmap, ≤150 lines, upstream's autonomous template shape (Goal / Next Step /
  Current Phase / `### Phase N` blocks with `**Status:**` markers / Decisions ≤10 rows / Errors), exactly one
  phase `in_progress`, no `NEXT SESSION` heading. Edited only at rulings and phase boundaries. Gitignored, as
  today.
- Root `.mode`: tracked, `autonomous inject-smart`, the floor every slug inherits at creation (upstream #238
  behaviour). Root attestation file: gitignored, as today.
- One `.planning/<date>-<slug>/` per `/implement` ticket: plan (3–7 phases, one `in_progress`), findings,
  progress, attestation, mode, nonce, stop-block counter, per-agent ledgers. Created by upstream's initializer in
  slug mode.
- `.planning/.archive/<id>/`: closed tickets and the archived program plan. A hidden directory is never scanned
  by the resolver, and a slug-invalid id never binds through `PLAN_ID` or the pointer, so archived plans are
  unselectable by construction (probed).
- `.planning/.active_plan`: written by upstream's initializer; informational here. Never written by close.
- Tracked: the decisions/traps/obligation extract of the archived program plan, the goal history, the two-authority
  digest pointer.

### Binding (one live slug; `PLAN_ID` per worktree)

- The main clone carries no `PLAN_ID` and at most one live slug, so the pointer and newest-mtime agree by
  construction and the resolver never reaches its ambiguity branch. Parallel tickets run in worktrees with
  `PLAN_ID` exported — what the initializer prints and what upstream #50 prescribes. `plan init --pin` appends
  the binding to that worktree's gitignored per-clone mise override file; `plan close` removes it and warns that
  the running shell still carries the pin.
- Enforcement is detection, not denial: `plan status` and the doctor report more than one live slug, an
  environment `PLAN_ID` or pointer naming an archived or missing directory, and a stale pin. `plan init` warns
  (does not refuse) when another live slug already exists, naming close-or-worktree, because upstream's
  initializer is run as shipped.

### The shared planning library and CLI (`kb-setup plan …`)

Lives in the knowledge-base's `kb_setup` package, which dotfiles already consumes as a SHA-pinned git
dependency; dotfiles bumps the pin after the knowledge-base PR lands. Every verb wraps an unmodified upstream
script resolved from the installed plugin root (highest numeric version, never mtime), with the root injectable
for tests. Verbs:

- `status` — resolve once, pass the same identity to every reader; report resolved target; root and ticket
  digest versus attestation; active-plan pointer state (live / stale / absent); environment `PLAN_ID` state;
  live-slug count; the completion check's report; the ledger summary block; archived-directory references from
  pin or pointer. Per-plan attestation state is one of:
  `MATCH | MISMATCH | UNATTESTED`; selection state is one of `RESOLVED | AMBIGUOUS | NONE`; the extra findings
  are `SECOND_LIVE_SLUG`, `STALE_POINTER`, `STALE_PIN`, `ARCHIVED_REFERENCED`, `MISSING_ROOT_PLAN` (the last
  only when the repo profile declares a root roadmap). Exit code is non-zero on any non-clean state so the
  doctor and the skills can branch on it.
- `init "<title>"` — exec the upstream initializer in slug mode from the project root (never `--autonomous`,
  never root mode); capture the printed plan id (names collide to `-2`, `-3`); verify post-state — directory
  exists, `.mode` inherited from the root floor, attestation equals the plan's digest, pointer names the id —
  because the initializer reports an attester failure at exit 0; print `PLAN_ID=` and a status; `--pin` writes
  the worktree binding. Any post-state miss exits non-zero and names what to remove.
- `close <id> [--force]` — resolved id must equal `<id>`; the completion check must report all phases complete or
  `--force` was given (the ledger note records the reason); append a `phase_complete` ledger event bound to the
  id; move the directory to the archive and verify the post-condition; never touch the active-plan pointer (a
  stale pointer falls through to the roadmap by upstream's own rule); drop the worktree pin and warn about the
  live shell; print the parent-phase reminder (which roadmap phase names this ticket and how many other open
  tickets that phase lists) — flipping a roadmap status is a coordinator edit at the boundary, never automatic.
  Non-transactional by design; every step verifies its post-condition and `status` names each partial state.
- `log <event> "<summary>" [--agent NAME]` — resolve once (environment `PLAN_ID` → pointer → the single live
  slug), pass that id explicitly to the ledger appender, refuse when resolution is empty or ambiguous, never the
  root-directory fallback.
- `attest [--show|--clear]` — print the target the resolver chose, then pass every flag straight through to the
  upstream attester (flags are not enumerated locally); warn when the root roadmap is unattested while a ticket
  plan resolves (the C2 diagnostic). Model-runnable.
- `pointer` — write the tracked two-authority pointer (schema below) and print both digests.
- `doctor-probe` — the Lane B option B probe used by the doctor (below), exposed so both repos' doctors share it.

Per-repo profile, read by the library from each repo's declared baseline: `root_roadmap` (dotfiles true,
knowledge-base false), `pointer_path` (dotfiles set, knowledge-base none), `program_record` (goal history versus
direction docs), `ticket_ref` shape (`#NNNN` versus next-ticket id), `archive_dir` (both `.planning/.archive`),
`handoff_skill` (`/session-handoff` versus `/clear-prep`). No deny-set row exists in either profile.

### Tracked pointer and readers

- Pointer schema (tracked, task-text-free):
  `{ root: { plan_sha256, active_phase } | null, ticket: { plan_id, plan_sha256, active_phase } | null,
  recorded_at }`. `root` is null only when the profile declares no root roadmap.
- Active-phase rule: the first `### Phase` heading followed by `**Status:** in_progress` — the rule the ledger
  summary and completion check already use. The `NEXT SESSION` convention is retired; a plan with more than one
  `in_progress` phase is a status warning.
- Handoff-check verifies both authorities against disk and reports `MISSING_ROOT_PLAN` when the profile declares
  a root roadmap and none exists (today it reports nothing). The handoff skill's `mise run plan-pointer` fence
  stays verbatim because a contract pins it; new commands go in a second fence.
- The dotfiles pointer and attest entry points become thin re-exports of the shared verbs until deleted once the
  pin lands; their public CLI registration stays contract-bound.

### Mise tasks in both repos

`plan-status`, `plan-init`, `plan-close`, `plan-log`, `plan-attest`, `plan-pointer`, each a thin caller of the
matching `kb-setup plan` verb; task descriptions state the new posture. The passthrough-separator repair extends to
`plan attest` so `-- --show` reaches the script from either repo's task.

### Session doctor: `pwf-hooks`

- One new check in the existing SessionStart doctor (declared in the doctor baseline, enabled per repo): skip —
  never FAIL — when the doctor's own environment has planning disabled; otherwise run the real Claude hook
  dispatcher for the user-prompt-submit event with the resolved plugin root, a bounded timeout and the mise shims
  directory stripped from the child PATH; FAIL only when the shared resolver says a plan exists and the
  dispatcher's output is empty. Also surfaces `SECOND_LIVE_SLUG`, `STALE_PIN` and `ARCHIVED_REFERENCED` from
  `status`. Side effects (turn marker, progress marker refreshed by a diagnostic fire) are documented.
- FAIL-only by decision: every WARN-class state is already injected each turn, and repeating the tamper warning
  at every session start would be a permanent finding.
- It reaches interactive codex sessions through the existing codex SessionStart doctor mirror; no new Claude
  function hook and no new codex hook of any kind (both fail open and silent; a codex hook would false-FAIL in
  every planning-disabled lane).

### Codex lanes

- `sdlc_team` (worker lanes): no planning scrub — lanes inherit the session environment and see the plan (they
  already do; a contract forbids a scrub from being "fixed" back in, and a test spawns a real child to assert it
  inherits `PLAN_ID` when set and lacks the disable flag). Pre-dispatch attestation check at the dispatch call:
  resolve the plan as the shell resolver would; if the resolved plan is in a v3 mode and its digest differs from
  its attestation (missing or mismatched), refuse to dispatch and name the attest task — which the orchestrator
  can now run in the same turn. No plan at all → allow (the spec file carries the task). Never auto-attest at
  dispatch: that would make tamper detection a no-op.
- `codex_lane` (advisory): keeps its planning scrub and its existing isolation contract until Phase 10 retires the
  lane. The `PLANNING_DISABLED=1` prose in the codex agent definitions stays with it.
- Interactive codex uses the globally enabled pwf codex plugin with its seven trusted hooks against the same
  `.planning/`, pointer and `PLAN_ID`; this design adds no hook and requires no new `/hooks` trust.
- Phase 10 step 5's pwf items are SUPERSEDED by this design and the supersession is recorded in Phase 10's
  rulings block: no absolute plan root in tracked settings env (it breaks worktrees), no `sdlc_team` scrub, no
  lint forbidding slug plans or the active-plan pointer, and no "design decisions wait for pwf deep extraction"
  hold.

### Skills, rules, agents (documentation surface)

- `/session-handoff`: keep the pointer fence; add status; on MISMATCH and this session edited the plan → attest
  then re-status; on MISMATCH and it did not → a finding, reported, not attested; then a ledger note naming the
  handoff, the pointer (both digests), the doctor. Checklist: both MATCH, at most one live slug, completed ticket
  closed. OWED never contains an attest. The memory-index note flips "operator-only" to "model-runnable".
- `/session-resume`: after the handoff, status, then the three-way compare (file digest vs attestation vs
  committed pointer): all equal → clean; file ≠ attestation → "unattested edit after handoff", first offer the
  attest command; attestation ≠ pointer → "re-attested after the pointer was committed" → a disagreement,
  fix-first. The plan line reads `root → <phase> [MATCH] | ticket <id> → <phase> [MATCH|TAMPERED]`. Stale pin →
  first offer "new terminal".
- A shared `pwf-workflow` rule (the posture, the layout, who attests when, the operator's remaining stops)
  carried by the cross-repo rule-sync gate; the report-persistence rule's file-role table and the scribe agent
  are reworded from "root findings/progress, operator-attested plan" to "the resolved plan directory,
  coordinator-attested plan"; the SubagentStart contract tokens follow; the generated skills mirror is
  regenerated in the same change.
- The wrapper skill for ticket creation documents `mise run plan-init` as the route (upstream's `/pwf` remains
  allowed but creates root files first and then takes the root-mode branch, which re-attests the roadmap —
  harmless, not what a ticket wants). The close skill requires an `AskUserQuestion` before `--force` on an
  incomplete ticket, as a judgment under clarify-before-acting, not a permission.

### Plan migration (one-time, coordinator-executed, no operator step)

Seven verifiable outcomes, in order: (1) preserve the old program plan and its attestation byte-for-byte under
the archive, and move the leftover 2026-09-21 directory there; (2) enumerate every unchecked item and every
"still open" reference from the old plan into the tracked extract, each mapped to a roadmap line, an existing
issue number, or dropped-with-reason (drops are asked); (3) install the ≤150-line roadmap with Phases 10 and 11
and the pwf addendum condensed to decision rows; (4) append a new goal-history iteration — writer: the
coordinator, on the branch, before the first ticket init — whose goal text names the root roadmap plus the
attested ticket plan as task authority and attestation as orchestrator-run tamper detection, with the required
fields, changed digest and Mermaid workflow, append-only against the merge-base (iteration 032 recorded the
re-ordering and trust-model change at handoff; this is the later iteration the round-6 ruling assigns to the
migration ticket); (5) reconcile selection — no live slug, pointer absent or stale, environment `PLAN_ID`
unset; (6) write the pointer, attest the roadmap (target printed: root), show; (7) verify agreement — status
root MATCH and Phase 11, ledger-summary heading equals pointer heading, doctor clean, and the next prompt injects
a plan body.

### Knowledge-base parity

Tracked root `.mode` floor (its gitignore does not cover it, so it will track); drop the version literal from the
resume skill; resume and clear-prep call the shared status and close; the archive reference becomes a pointer to
the shared close; close the eleven-day live slug through the shared close after confirming with Ray that its
round is done; add the `host_only` marker and CI-skip convention the shared tests need; the shared rule via
rule-sync in both repos. No deny set is added to the knowledge-base.

### Upstream asks (file, do not block)

An explicit root-target flag for the attester (so root can be attested while a slug resolves), and a Claude
Code / Codex analogue of Pi's `/plan-execute` — the only way an approval boundary returns upstream-first.

### Operator's remaining stops

`AskUserQuestion` on genuine ambiguity or irreversibility (force-close of an incomplete ticket; an obligation
dropped in the migration; the goal-text wording); user-invoked protocol verbs; codex `/hooks` trust after a
plugin upgrade; plugin upgrades and `/clear`; PR review of the pointer and goal history. Not a stop:
attestation, plan creation, closing a complete ticket, logging, status.

## Testing Decisions

What makes a good test here: it drives a public entry point (the shared CLI, a doctor check, a dispatch call, a
verification contract) against a real or recorded-real filesystem state, and it carries both arms — the state
that must be reported and a control that must not be — because every defect this migration closes was a probe
or a gate that could only pass.

- **Shared library and CLI (knowledge-base).** Throwaway git repo fixtures driven through `kb-setup plan …` with
  the REAL installed plugin scripts, marked `host_only` (run on every developer host and by the ship gate;
  auto-skipped only on the bare CI runner). Arms: init prints the id and passes post-state verification, and
  fails legibly on a forged exit-0 initializer whose attester did not write; status names MATCH after init,
  MISMATCH after an edit, AMBIGUOUS with two live slugs, STALE_POINTER after an archive move,
  ARCHIVED_REFERENCED when `PLAN_ID` names the archived id, STALE_PIN when the pin outlives the directory;
  close refuses an incomplete plan and succeeds on a complete one, moves the directory, leaves the pointer
  untouched, drops the pin; log refuses empty or ambiguous resolution and writes under the bound id; attest
  prints its target and forwards `--show`. CI-runnable twins for the classification, pointer schema, phase rule,
  close post-conditions and per-repo profiles run against fixture trees whose byte layouts were recorded from the
  real scripts; one `host_only` arm asserts the recorded layouts still match what the installed version writes.
  Both repo profiles are exercised (root roadmap true/false).
- **Readers (dotfiles).** Pointer and handoff-check tests at their existing seams: the old `NEXT SESSION` fixture
  fails; the `### Phase` + `**Status:** in_progress` fixture passes; a two-authority pointer is written and
  verified; a missing root with the roadmap profile yields `MISSING_ROOT_PLAN`; a stale pointer after a byte
  change is still caught. The ledger summary and the pointer must name the same heading on the same file.
- **Doctor `pwf-hooks` (dotfiles).** At the check-function seam: a live-plan fixture with planning disabled in the
  CHILD environment → FAIL (the canary that proves the probe can fire); the same fixture unset → clean; the
  doctor's own environment disabled → skipped, not FAIL; findings for a second live slug, stale pin and archived
  reference each with a control.
- **`sdlc_team` (dotfiles).** At the dispatch seam with a fake spawn: a tampered or unattested v3 fixture →
  no spawn, message names the attest task; an attested fixture → dispatch proceeds; no plan → dispatch proceeds.
  A real spawned child asserts it inherits `PLAN_ID` when set and lacks the disable flag (positive), and the same
  probe reports the unset state (control) — the same shape the `codex_lane` isolation test already uses.
- **Contracts (dotfiles, via `dotfiles-setup verify run`).** The retired operator-only contract is deleted; the
  new "attest deny must not return" contract passes on the retired settings and its mutation arm (re-add one
  attest deny rule) fails; a wiring contract binds skill → task → CLI → library for the new workflow; a contract
  forbids a planning scrub in `sdlc_team`; the `codex_lane` isolation contract is unchanged and still green.
  hook-selfcheck passes with its attest arm removed.
- **Documentation surface.** `lint-docs`, the skills mirror parity step, `rule-sync` in both repos, and the
  existing handoff-fence contract; skill evals in dry-run for the close skill's ask-before-force behaviour.
- **Live arms recorded in the tickets.** After T1, the model runs the read-only attest form and receives exit 0
  while a covered credential-file read is still denied (control). After T8, status reports root MATCH and
  Phase 11, the ledger heading equals the pointer heading, the doctor is clean, and the next prompt injects a
  body.

Prior art in this codebase: the attest wrapper tests (plugin resolution through an injected home, the
half-written-ban mutation arm, the end-to-end passthrough test that binds the call site rather than the helper);
the handoff-check tests (git-init fixture repos, verdict lists, unclosed-fence control); the `sdlc_team` tests
(fake spawn recording argv, "no process launched" arms); the doctor tests (check functions over an assembled
setup, "unreadable config fails rather than passes"); the `codex_lane` isolation test (real child, positive plus
control); the `host_only` marker with its CI auto-skip and the "missing binary fails the gate rather than
skipping it" sibling; the knowledge-base's conftest git fixtures and its usage-render test ("the arm is the
render, not the source").

## Out of Scope

- The `pr-loop` ship → fix → land loop (its own spec).
- Phase 10 work: retiring `codex_lane` and its scrub, the one-codex-entry-point consolidation, RESEARCH mode,
  role-typed models, codex-native install and the daemon gate.
- Adopting `/plan-loop`, `/plan-goal`, gated mode, `phase-status`, or any Claude-side approval gate for
  attestation; auto-attest in any hook or at dispatch; a Claude function hook or a codex hook for plan-doctor;
  `PLAN_ID` in tracked settings env or in the main clone; rename-based archival; automatic roadmap status flips
  on close; a shared active-plan pointer as the binding.
- A codex-side doctor arm through the codex plugin's own adapter (optional follow-up), and the knowledge-base's
  coreutils shim tax (its own ticket).
- Changing upstream behaviour locally; the two upstream asks are filed, not blocked on.
- Any change to how the plan's contents are trusted as instructions (delimiter framing, nonce, prompt-injection
  posture) — unchanged upstream behaviour.

## Further Notes

**Ticket order and dependencies (T1–T10 of the design of record).**

- **T1 (retire D4) first and independently.** Everything after it is model-runnable in this repo only once the
  deny rules are gone; an agent implementing later tickets here would otherwise hit the deny on its own live
  arms. Also ships the "must not return" contract.
- **T2 (shared library + CLI) is a knowledge-base PR, followed by the dependency pin bump in dotfiles.** T3–T6
  and T9 depend on it. T2 also adds the knowledge-base's `host_only` convention.
- **T3 (readers), T4 (mise tasks both repos), T5 (doctor), T6 (`sdlc_team`) are independent of each other after
  the pin bump.** T4 must precede T7, because skill text naming a task that does not exist fails the docs gate.
  T3 must precede T8, because the new roadmap shape fails today's handoff-check.
- **T7 (skills, rules, agents, mirror, rule-sync)** after T3–T6; **T8 (plan migration)** last on the dotfiles
  side, after T7, since the handoff/resume skills must already describe the state T8 creates.
- **T9 (knowledge-base parity)** after T2, in parallel with T3–T6; closing the eleven-day slug waits for Ray's
  confirmation that its round is done.
- **T10 (upstream asks)** any time; not a dependency of anything.

**Rulings encoded, for the reviewer's checklist.** Upstream trust model supersedes D4 and the round-2
"upstream + its hardening"; root roadmap plus per-ticket slugs; `PLAN_ID` per worktree; `.planning/.archive/`;
one merged workflow in `kb_setup` with per-repo flags; layering skill → mise task → library function; close
model-runnable when complete with `--force` behind an `AskUserQuestion`; `sdlc_team` lanes see the plan and the
pre-dispatch attestation check runs at the dispatch call; `codex_lane` scrub kept until Phase 10; Phase 10 step
5's pwf items superseded; goal-history iteration written by the coordinator with the changed goal text; the
knowledge-base's eleven-day slug archived via the shared close; the "attest deny must not return" contract.

**Deciding risk.** Stale memory: the memory index, several transcripts, the config paragraph, task
descriptions and test docstrings all still say "operator-only", and a later session acting on that will re-add
the deny from habit. The contract is the control arm; T7's rewrite of the prose and the memory-index flip at the
next handoff are the rest of the mitigation.

**Unverified items carried from the design, to be settled by the implementing tickets.** That a per-worktree
mise override's environment reaches a `claude` process launched from that shell (standard mise activation,
unmeasured); the exact codex hook trust currency after a plugin upgrade; whether the knowledge-base already has
a plugin-root resolver (none was found under its package; the dotfiles one moves or is mirrored).

**Why `/pwf` stays allowed but is not the documented route.** Upstream's command creates root files first and
only then chooses a mode, which with root files present takes the root-mode branch and re-attests the roadmap.
Under the adopted trust model that is harmless; it is simply not the slug a ticket wants, so the thin init task
is the documented route and the only local addition is path resolution plus the worktree pin.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed 3.20.7 source
  read and probed (`init-session.sh`, `attest-plan.sh`, `resolve-plan-dir.sh`, `check-complete.sh`,
  `ledger-append.sh`, `ledger-summary.sh`, `set-active-plan.sh`, the Claude hook dispatcher, `commands/pwf.md`,
  `MIGRATION.md`, `docs/attestation-locking.md`, `SKILL.md`); tracker #50/#150/#190/#193/#202/#237/#238 via the
  upstream review report.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — task plan addendum, settings deny list,
  verification contracts, the attest/pointer/handoff-check/sdlc_team/codex_lane/hook_selfcheck/doctor modules
  and their tests, the handoff/resume skills, the scribe agent, the persistence rule, goal history, pointer,
  gitignore, pytest markers, CI workflow, and the six input reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `.planning/` state, settings,
  gitignore, `kb_setup` package layout and CLI dispatch, tests and conftest, the session-resume and clear-prep
  skills and the plan-archive reference.
