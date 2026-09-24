## Problem Statement

Ray runs a multi-session, multi-agent program in two repositories (dotfiles and knowledge-base) with one Claude
orchestrator and codex worker lanes. The planning-with-files plugin is supposed to carry the program's working
memory between sessions, but the way it is set up today makes it a cost centre.

- Attestation is a chore that lands on Ray. The plan is one 1,647-line root plan in autonomous mode; every edit
  breaks its attestation and the plugin refuses to inject the plan until a human re-attests. Attestation was made
  operator-only here on 2026-09-02 on the belief that it is a human-approval boundary; upstream's maintainer says
  it is not a keyed signature or proof of human approval. The result is roughly twenty manual attest runs in
  twenty-one days, an eleven-day outage of the read-only form that nobody noticed because the operator path was
  the only path, sessions that end with "attest is owed", and a deny list that (observed again tonight) blocks a
  read-only look at a plugin script because the script's name appears on the command line.
- The plugin's own view of the plan is stale. The machine-readable phase markers say Phase 2b while the tracked
  pointer says Phase 11; ledgers hold zero entries; the plan doctor warns about hash mismatches; codex lanes have
  received a "plan tampered" notice instead of the plan (issue #910). Turn-start injection names the wrong phase.
- Two repositories, two workflows. The knowledge-base uses named per-round plans with an eleven-day-old live
  plan, its own archive recipe, a hard-coded plugin version in its resume skill, and no attestation posture;
  dotfiles uses a root plan, a deny list, a wrapper task and a tracked pointer. Every improvement is made twice or
  in one place only.
- Local hardening fights upstream. The deny list, the wrapper's operator-only wording, the selfcheck arm and the
  verification contract all encode a trust model upstream does not share, so each plugin upgrade risks a local
  patch upstream will never carry. Ray's standing instruction is to assume what we are doing is wrong and follow
  upstream so plugin updates land with minimal change.
- Leftovers and gaps. A leftover plan directory from 2026-09-21 that holds only an archived plan; no archive
  location; no way for a session to see in one line whether the plan it is about to trust is the resolved one,
  attested, unambiguous and current.

From Ray's seat: he wants to stop being the attestation button, wants the plan to be small and true, wants codex
lanes to see the plan, wants one workflow for both repos, and wants the next plugin release to be a plugin update
rather than a migration.

## Solution

Adopt the plugin's current (3.20.7) workflow whole, under upstream's trust model, and put the human-review
boundary where a pull request can actually see it.

- Layout. The root plan becomes a short program roadmap (at most 150 lines, upstream's autonomous template shape,
  exactly one phase in progress). Each implementation ticket gets its own scoped plan directory named by date and
  slug, created by upstream's initializer in slug mode, attested at creation, inheriting the tracked root mode
  setting as a policy floor. Closed tickets move to a hidden archive directory under the planning directory,
  which the plugin's resolver never scans. The old program plan is archived byte-for-byte and its still-open
  obligations are mapped into a tracked extract, the roadmap, or an existing issue.
- Trust model. Attestation is tamper detection run by the orchestrator: it creates a ticket plan, fills it and
  attests it in the same turn; re-attests after each intentional edit and at phase boundaries; never attests a
  change it did not make. Workers never attest. The operator-only deny rules and everything that existed only for
  them are retired; a JSON-scoped selfcheck arm plus a verification contract guarantee that no spelling of the
  deny returns. Human review moves to the tracked artifacts a pull request reviews: the two-authority digest
  pointer and the append-only goal history.
- Binding. The main clone holds at most one live ticket plan and no environment binding; parallel tickets run in
  git worktrees with the plan id exported and optionally pinned per worktree. Enforcement is detection, not
  denial: status and the doctor report a second live slug, a stale environment pin, or an armed session-isolation
  directory. The shared active-plan pointer is a hint that upstream falls through; only the environment binding
  fails closed.
- One merged workflow. A shared planning library and a plan command group (status, init, close, log, attest,
  pointer, doctor-probe) live in the knowledge-base's shared package that dotfiles already consumes as a pinned
  dependency. Both repos expose the same thin mise tasks; per-repo differences are declared profile flags, never
  a second workflow. Shared implementation is separated from repo-specific invocation policy: each repo's own
  lifecycle skills decide when to call status and close. Everything is built as reusable skill to mise task to
  library function, each layer calling the one below.
- Consumers follow. The pointer records both authorities; the active-phase rule is the canonical one upstream's
  own readers agree on, with a warning when a plan is not canonically formatted; handoff-check reports a missing
  root roadmap on its public path when a handoff exists; the session doctor gains a fail-only "dark hooks" probe
  of the real dispatcher plus the selection findings; the handoff and resume skills run status and classify a
  mismatch by who edited; codex worker lanes see the plan and are refused dispatch — naming the fix — on any plan
  the hooks would not inject. The advisory codex lane keeps its planning scrub until Phase 10 retires it.
- Knowledge-base parity. Same tasks, the shared skill text, a tracked root mode floor, no version literal, its
  existing lifecycle rules preserved by name, its eleven-day live slug closed through the shared close once its
  round is confirmed done.
- Upstream first for what upstream lacks. File, and do not block on, two asks: an explicit root-target flag for
  the attester, and a Claude Code / Codex analogue of the Pi adapter's plan-execute approval gate.

## User Stories

Ray, the operator

1. As the operator, I want attestation to stop being a manual step I perform after nearly every session, so that
   my involvement is reserved for decisions rather than for pressing a button on bytes an agent wrote.
2. As the operator, I want the program plan to be short and true, so that reading it tells me where the program
   is without scrolling through 1,600 lines of history.
3. As the operator, I want each ticket's working plan isolated from the roadmap, so that one ticket's churn never
   breaks the roadmap's attestation or another ticket's context.
4. As the operator, I want the tracked digest pointer and the goal history, not the gitignored plan, to be the
   things I review in a pull request, so that the human-approval boundary lives where a review actually happens.
5. As the operator, I want the deny rules retired and two independent checks that fail if any spelling of them
   comes back, so that a later session acting on stale memory cannot silently re-impose the old posture.
6. As the operator, I want one workflow across dotfiles and knowledge-base with differences declared as flags,
   so that I maintain one thing and every improvement lands in both repos.
7. As the operator, I want to be asked before an incomplete ticket is force-closed, before a listed obligation is
   dropped in the migration, and before the goal text changes, so that irreversible or judgment-laden steps still
   pass through me.
8. As the operator, I want the next plugin release to be a plugin update rather than a migration, so that upstream
   improvements arrive with minimal local change.
9. As the operator, I want the leftover 2026-09-21 directory and the old program plan archived rather than
   deleted, so that nothing is lost and nothing stale is selectable.
10. As the operator, I want every open obligation in the old plan accounted for before the old plan is retired,
    so that live work does not vanish in the move.
11. As the operator, I want the plugin's own phase view, the pointer and the ledger summary to name the same
    phase for a canonically formatted plan, and to be warned when a plan is not canonically formatted, so that
    turn-start injection and my own reading agree.
12. As the operator, I want a one-line status that says which plan resolves, whether it is attested, whether
    selection is ambiguous and whether anything binds to an archived plan, so that I never trust a plan the
    plugin is not actually injecting.
13. As the operator, I want the accepted cost stated plainly, that an attested plan no longer means I approved it,
    so that no future session infers an approval that was never given.
14. As the operator, I want a successful close to leave the repository in a state that status, the doctor and the
    handoff all call clean, so that closing never becomes a finding I must explain away.

The orchestrator agent (the Claude architect session)

15. As the orchestrator, I want to create a ticket plan with one command that prints the plan id and its status,
    so that I do not hand-type a version-pinned plugin path or guess whether creation attested.
16. As the orchestrator, I want to fill the ticket plan and attest it myself in the same turn, so that the tamper
    gate is armed on my own bytes without waiting for a human.
17. As the orchestrator, I want the attest command to print which plan it will target before writing, so that I
    never lock a ticket plan when I meant the roadmap, or the reverse.
18. As the orchestrator, I want to be told when the roadmap is unattested while a ticket plan is live, so that I
    sequence roadmap edits to the boundary where the roadmap is the resolved plan.
19. As the orchestrator, I want to close a completed ticket with one model-runnable command that archives it,
    records the ledger event, drops my worktree pin and names its parent roadmap phase when one is uniquely
    identifiable, so that closing is routine and never leaves a stale selection behind.
20. As the orchestrator, I want closing to refuse an incomplete ticket unless I pass a force flag with a reason
    after asking Ray, so that "done" keeps meaning every phase complete and the reason is on record.
21. As the orchestrator, I want closing to never touch the shared active-plan pointer, and a pointer that names
    an archived plan to be reported as informational rather than as a failure, so that upstream's own
    fall-through rule governs and a clean close is clean.
22. As the orchestrator, I want to re-run close after a partial failure and have it finish the remaining steps,
    so that a non-transactional close never strands a half-archived ticket.
23. As the orchestrator, I want to log progress and notes to a ledger bound to the resolved plan, the ticket when
    one is live and the roadmap when none is, and to be refused when resolution is ambiguous or a binding is
    rejected, so that ledger rows never land in the wrong plan and root-only sessions can still log.
24. As the orchestrator, I want status to distinguish the attestation state, the selection state, the binding
    findings and the informational pointer states, so that my next action is determined by the state and not by
    guesswork.
25. As the orchestrator, I want the handoff skill to classify a mismatch by whether this session edited the plan,
    attesting if I did and reporting a finding if I did not, so that tamper detection still pays exactly where it
    should.
26. As the orchestrator, I want the resume skill to three-way compare file digest, attestation and committed
    pointer, so that "unattested edit after handoff" and "re-attested after the pointer was committed" are named
    as distinct disagreements with distinct first offers.
27. As the orchestrator, I want the handoff's owed list to never contain an attest, so that a handoff is complete
    when I write it rather than pending on Ray.
28. As the orchestrator, I want the pointer to record both the roadmap and the ticket plan, so that an unrecorded
    roadmap change is detectable even while a ticket is selected.
29. As the orchestrator, I want the active-phase rule to be the canonical primary-marker rule, so that my pointer,
    the ledger summary and the completion check agree whenever the plan is well-formed and I am told when it is
    not.
30. As the orchestrator, I want to record a mid-ticket ruling in the ticket plan's decisions and batch roadmap
    edits to the boundary, so that the roadmap changes only at rulings and phase boundaries.
31. As the orchestrator, I want to append a goal-history iteration with the changed goal text when the plan
    migration lands, so that the program record states what task authority now is and who writes it.
32. As the orchestrator, I want the session doctor to fail loudly when a plan resolves but the real dispatcher
    injects nothing, so that dark hooks are caught at session start rather than noticed as silence.
33. As the orchestrator, I want the doctor and status to report a second live slug, a stale environment pin or an
    armed session-isolation directory, so that I fix selection before I trust injection.
34. As the orchestrator, I want to run a ticket in a worktree with the plan id pinned per worktree and to know
    how that worktree relates to the roadmap, so that two parallel tickets never share a pointer and a worktree
    never starts in a failing state.
35. As the orchestrator, I want upstream's own plan-start command to keep working as shipped while the documented
    ticket route is the thin init task, so that I follow upstream by default and only add what upstream lacks.
36. As the orchestrator, I want the wrapper skills to call other skills, the tasks to call tasks and the functions
    to call functions, so that no layer re-implements the one below it.
37. As the orchestrator, I want every rule, skill, task description and test docstring that still says
    "operator-only", "human boundary" or "root findings file" rewritten in the same change, so that the
    instruction surface does not contradict the code.

A codex worker lane

38. As a codex worker lane, I want to see the resolved, attested plan the orchestrator is working from, so that my
    output is grounded in the current program state rather than in a spec alone.
39. As a codex worker lane, I want dispatch to be refused, naming the fix, when the resolved plan is unattested,
    tampered, ambiguous, bound to a rejected pin or missing its plan file, so that I am never blind-dispatched
    against a plan the hooks refuse to inject.
40. As a codex worker lane, I want to never attest and never edit the plan, with that prohibition carried in my
    spec, so that a hash break at the orchestrator's next status is a real tamper signal and not my doing.
41. As a codex worker lane, I want my ledger rows written under my own agent name in the bound plan, so that the
    orchestrator's status shows my progress without me touching the plan file.
42. As the advisory codex lane, I want my planning scrub kept until Phase 10 retires me, so that the round-5
    ruling is applied to workers and not silently widened.

A knowledge-base session

43. As a knowledge-base session, I want the same status, init, close, log and attest tasks as dotfiles, so that
    the muscle memory and the shared skill text are identical across repos.
44. As a knowledge-base session, I want the repo's differences (no root roadmap, no pointer, direction docs as the
    program record, next-ticket ids as ticket references, the clear-prep skill as the handoff) to be declared
    flags, so that the shared library behaves correctly here without a fork.
45. As a knowledge-base session, I want my existing lifecycle rules kept, resume reports and never archives, the
    user's task outranks the generated next ticket which outranks the plan's next step, and archive happens only on
    an explicit clear-now and only when complete, with the archive step now performed by the shared close, so that
    adopting the shared workflow changes the mechanism and not the policy.
46. As a knowledge-base session, I want a tracked root mode floor, so that a new plan's attestation requirement
    is a reviewed project setting rather than a flag the agent picks at creation.
47. As a knowledge-base session, I want the resume skill to stop hard-coding a plugin version, so that a plugin
    upgrade does not silently point the skill at a dead directory.
48. As a knowledge-base session, I want the eleven-day live slug closed through the shared close command once its
    round is confirmed done, so that the resolver stops offering a finished round as the live plan.

A future plugin upgrade

49. As a future plugin upgrade, I want every local command to be a thin wrapper over unmodified upstream scripts
    resolved from the installed plugin root, so that the upgrade changes plugin bytes and nothing else.
50. As a future plugin upgrade, I want a host-run test that asserts the recorded on-disk layouts still match what
    the installed version writes, so that a changed script surfaces as a failing test rather than as a silent
    misclassification.
51. As a future plugin upgrade, I want the repo to carry no deny rules, no flag enumeration and no version literal
    that upstream would have to be patched around, so that the upstream tracker is where behaviour changes are
    negotiated.
52. As a future plugin upgrade, I want the two upstream asks filed with the maintainer, so that if they ship,
    local convenience code can be deleted rather than grown.

A pull-request reviewer and a fresh clone

53. As a reviewer, I want the pointer diff and the goal-history iteration to tell me what the roadmap's phase and
    digest are and why the goal changed, so that I can review program state without access to a gitignored file.
54. As a fresh clone, I want the tracked root mode, the tracked extract, the goal history and the pointer to be
    enough to understand where the program is, and handoff-check to stay green when no handoff exists, so that
    the missing gitignored plan is a working-memory gap, not a failing check.

## Implementation Decisions

Trust model and the retirement of the operator-only posture

- Attestation is upstream's: a local digest that detects a changed plan while the digest is trusted. The
  orchestrator attests immediately after each intentional edit (after filling a new ticket plan, after a boundary
  roadmap edit, and at handoff) and re-attests at phase boundaries in multi-agent runs, as upstream's migration
  guide prescribes. Workers never attest; that rule travels in every lane spec.
- Retired outright, by name: the eleven deny entries (six naming the attest and selector scripts in shell and
  PowerShell forms, five naming the wrapper task and the CLI beneath it); the selfcheck presence arm and its
  deny-bases table with its registration; the operator-only verification contract; the four tests that assert the
  deny is present, together with the two imports that would break test collection if the selfcheck functions were
  deleted alone; the operator-only wording in the Claude-specific config, the task description, the CLI help, the
  wrapper's docstring, the test module's docstring, and the row of the mise-tasks rule that calls attestation a
  human boundary; the earlier revision's plan-init deny route, force-flag operator-only and draft-import
  rejection, none of which was ever built.
- Kept for reasons unrelated to the old posture: resolving the installed plugin root (highest numeric version,
  never modification time; the plugin root is unset in an agent's shell and the cache path is version-pinned) and
  the passthrough-separator repair behind the read-only form. The resolver and passthrough tests survive and
  move with the code.
- Regression prevention has two independent layers. First, the selfcheck arm becomes its inverse and is scoped to
  the settings' deny list: it parses the settings and fails on any deny entry that matches the attest script, the
  selector script, the wrapper task or CLI, or the initializer, in any spelling. Second, a forbid-pattern
  verification contract over the settings file for the same four spellings, plus a required sentence in the
  Claude-specific config stating that attestation is model-runnable tamper detection. Both layers are mutation
  tested with one script-rule re-addition and one wrapper-rule re-addition; the credential-file read denies remain
  accepted as the control.
- Stated cost, accepted by Ray: an attested plan no longer means Ray approved it.

Layout

- The root plan is the roadmap: at most 150 lines, upstream's autonomous template shape with primary status
  markers, exactly one phase in progress, no "next session" heading. Edited only at rulings and phase boundaries.
  Gitignored, as today.
- The root mode file is tracked and sets autonomous mode with smart injection. A new ticket plan inherits the mode
  token as a policy floor; root-level tokens such as smart injection continue to govern the ticket plan because
  the injector reads the root mode file as well. The root attestation is gitignored.
- One ticket plan directory per implementation ticket, created by upstream's initializer in slug mode; its goal
  line carries the profile's ticket reference (a dotfiles issue number, or the knowledge-base's next-ticket id).
- The hidden archive directory holds closed tickets and the archived program plan; hidden means never scanned,
  and a slug-invalid id never binds, so archived plans are unselectable by construction.
- The shared active-plan pointer is written by upstream's initializer and is a hint; close never writes it.
- Session isolation (the plugin's opt-in sessions directory) is not adopted. Its presence makes a root roadmap
  plus one live ticket plan ambiguous for every un-pinned session, so status reports it as a finding and names
  the two exits: delete the directory, or pin the plan id.
- When no ticket plan is live, upstream's ledger appender writes the ledger beside the root plan; that root
  ledger pattern joins the ignore list, which does not cover it today.
- Tracked: the obligation extract of the archived program plan, the goal history and the two-authority pointer.

Binding (one live slug; plan id per worktree)

- The main clone carries no environment binding and at most one live ticket plan. Parallel tickets run in
  worktrees with the plan id exported; the init command's pin option appends the binding to that worktree's
  gitignored per-clone mise override, and close removes it and warns that the running shell still carries the pin.
- Root authority in a linked worktree is provisional, pending Ray's answer to question 1: the roadmap lives in the
  main clone only; in a linked worktree status reports the root as not applicable rather than missing, the
  pointer command updates only the ticket block and carries the committed root block forward unchanged, and the
  linked-worktree condition is detected from git's common directory rather than a flag.
- Enforcement is detection: status and the doctor report a second live slug, a stale environment pin (a binding
  naming an archived or missing directory, which upstream fails closed on), an armed session-isolation
  directory, and the informational pointer states. Init warns, and does not refuse, when another live slug
  exists, because upstream's initializer runs as shipped.

The shared planning library and command group

Lives in the knowledge-base's shared package, which dotfiles already consumes as a pinned dependency; dotfiles
bumps the pin after the knowledge-base change lands. Every verb wraps an unmodified upstream script resolved from
the installed plugin root, with the root injectable for tests.

- Status resolves once and passes that identity to every reader. It reports the resolved target; per-authority
  attestation state (match, mismatch, unattested); selection state (resolved, ambiguous, none); the non-clean
  findings (second live slug, stale pin, session isolation armed, missing root plan under a root-roadmap profile
  in the main clone, a resolved directory without a plan file); the informational states (a pointer naming an
  archived plan, a pointer naming nothing, non-canonical phase markup); the completion check's report; and the
  ledger summary. It exits non-zero only on a mismatch or unattested state of a resolved authority, on
  ambiguity, or on a non-clean finding; informational states exit zero. The clean terminal states are therefore
  enumerable: root-only with no pointer; root-only with a retired or dangling pointer; root plus one live ticket
  plan whose pointer names it; and, in a linked worktree, ticket-only.
- Init execs the initializer in slug mode from the project root (never the autonomous flag, never root mode),
  captures the printed id (name collisions get a numeric suffix), verifies the post-state (directory exists, mode
  token inherited, attestation equals the plan digest, pointer names the id) because the initializer reports an
  attester failure at a zero exit, prints the plan id and a status, and with the pin option writes the worktree
  binding. Any post-state miss exits non-zero and names what to remove.
- Close, while the directory is live, requires the resolved id to equal the given id and the completion check to
  report every phase complete, or the force flag together with a mandatory reason that is recorded in the ledger
  note; it appends the phase-complete event, moves the directory to the archive and verifies, never touches the
  pointer, drops the worktree pin and warns about the live shell, and prints the parent-phase reminder. Close is
  idempotent by post-condition: an id already under the archive with no live directory resumes the remaining
  steps rather than failing the precondition. It is non-transactional by design; status names every partial
  state.
- The parent-phase reminder looks the ticket plan's ticket reference up in the roadmap. Exactly one phase block
  containing it yields "belongs to that phase, which lists so many other unchecked ticket references"; zero or
  several matches yield "no unique parent phase" and nothing is manufactured. Flipping a roadmap status is a
  coordinator edit at the boundary, never automatic.
- Log resolves exactly as upstream does: environment binding, then a live pointer, then the single live ticket
  plan, then the root roadmap when the profile declares one and no selector is set. It refuses on ambiguity or a
  rejected selector and passes the resolved id explicitly to the appender.
- Attest prints the target the resolver chose (the root only when no live ticket plan resolves and no selector
  is set), passes every flag straight through without enumerating upstream's, and warns when the roadmap is
  unattested while a ticket plan resolves. Model-runnable.
- Pointer writes the tracked two-authority pointer and prints both digests; from a linked worktree it updates the
  ticket block only.
- Doctor-probe is the fail-only dark-hooks probe both repos' doctors call.

The per-repo profile is a plan section in each repo's tracked baseline configuration (dotfiles reuses its
existing doctor baseline; the knowledge-base adds one, having none today), with a config override for tests. Its
keys: whether a root roadmap exists, the pointer location, the program record (goal history or direction docs),
the ticket-reference pattern, the archive directory and the handoff skill. No deny-set key exists.

Tracked pointer and readers

- The pointer records a root block (digest and active phase, null only under a no-root profile) and a ticket
  block (id, digest, active phase, null when no ticket is live), plus a timestamp; it never carries task text.
- The active-phase rule is the canonical one: the first phase heading whose following primary status marker says
  in progress. That is the format upstream's completion check and ledger summary agree on; inline bracketed
  status tokens or more than one phase in progress produce the non-canonical-markup warning. The "next session"
  heading convention is retired.
- Handoff-check, when a handoff exists, verifies both authorities against disk and reports a missing root plan
  under a root-roadmap profile in the main clone; when no handoff exists, its public path keeps today's
  zero-exit informational line so a fresh clone stays green. The handoff skill's existing pointer fence stays
  verbatim because a contract pins it; new commands go in a second fence.
- Consumer cutover, provisional pending question 2: the dotfiles attest and pointer subcommands, their modules
  and their tests are deleted; the mise tasks call the shared verbs directly; the existing pointer-wiring
  contract is replaced, in the same change, by a workflow-wiring contract that binds mise task to shared verb
  registration to library function to skill fence. The reader tests that encode the old heading convention, the
  flat pointer and the fresh-clone behaviour are rewritten to the new grammar with explicit dispositions.

Mise tasks in both repos

Six thin tasks (status, init, close, log, attest, pointer), each calling the matching shared verb; task
descriptions state the new posture; the passthrough-separator repair extends to attest so the read-only form
reaches the script from either repo's task. The worktree pin gets a bounded acceptance probe: after pinning in a
throwaway worktree, a fresh process launched through mise activation from that directory reports the binding,
while a shell started before the write still reports the old value; hook attachment is reported separately by
the doctor.

Session doctor

- One new check in the existing session-start doctor, declared in the doctor baseline and enabled per repo. It
  skips, never fails, when the doctor's own environment has planning disabled; otherwise it runs the real Claude
  hook dispatcher for the user-prompt event with the resolved plugin root, a bounded timeout and the mise shims
  directory stripped from the child path, and fails only when the shared resolver says a plan exists and the
  dispatcher's output is empty. It also surfaces every non-clean status finding. Side effects (turn and progress
  markers refreshed by a diagnostic fire) are documented.
- Fail-only by decision: warning-class states are already injected each turn, and informational states are not
  doctor findings.
- It reaches interactive codex sessions through the existing codex session-start doctor mirror; no new Claude
  function hook and no new codex hook of any kind. The verification scope is stated honestly: Claude dispatcher
  health plus codex hook configuration, not proven codex injection.

Codex lanes

- Worker lanes see the plan. Both spawn sites already pass no environment, so lanes inherit the session
  environment today; a contract forbids a planning scrub from being "fixed" back in. A pre-dispatch check at the
  dispatch call resolves the plan as the shell resolver would and applies a complete matrix: no plan anywhere
  dispatches; a resolved, matching plan dispatches; a resolved plan whose digest differs from its attestation
  (mismatch or unattested, in a v3 mode) is refused naming the attest task; ambiguous selection is refused naming
  pin-or-close; a rejected binding (plan id set, resolver empty) is refused naming the stale pin; a resolved
  directory without a plan file is refused. Planning disabled in the dispatcher's own environment is recorded in
  the dispatch record and, provisionally pending question 4, dispatch proceeds with a warning. Never auto-attest
  at dispatch.
- The advisory codex lane keeps its planning scrub and its isolation contract's behaviour tokens until Phase 10
  retires the lane; that contract's documentation token is updated together with the rule row it pins.
- Interactive codex uses the globally enabled codex plugin with its seven trusted hooks against the same planning
  directory, pointer and binding; this design adds no hook and requires no new hooks trust.
- Phase 10 step 5's plugin items are superseded and the supersession is recorded in Phase 10's rulings block: no
  absolute plan root in tracked settings, no worker scrub, no lint forbidding ticket plans or the pointer, and no
  hold on design decisions pending deep extraction.

Skills, rules, agents

- The consumer inventory covers the handoff, resume, verify and session-review skills; the scribe agent; the
  report-persistence rule's file-role table (now "the resolved plan directory's findings and progress;
  coordinator-attested plan"); the notepad-enforcement and artifact-conventions rules that still route findings
  to the root findings file; the mise-tasks rule's attestation row; the subagent-start contract tokens; the
  generated skills mirror; and the memory-index note, flipped at the next handoff.
- The handoff skill keeps the pointer fence, adds status, attests then re-checks on a mismatch this session
  caused, reports a finding without attesting on a mismatch it did not cause, then writes a ledger note bound to
  the resolved plan (ticket if live, else root), the pointer with both digests, and the doctor. Its checklist:
  every declared, resolving authority matches; at most one live slug; the completed ticket closed. The owed list
  never contains an attest.
- The resume skill runs status, then the three-way compare of file digest, attestation and committed pointer:
  all equal is clean; file differs from attestation is "unattested edit after handoff" with the attest command as
  the first offer; attestation differs from pointer is "re-attested after the pointer was committed", a
  disagreement to fix first. A stale pin's first offer is a new terminal.
- Shared versus repo-specific: the shared workflow skill and rule carry the posture, the layout, who attests
  when, the state vocabulary and the operator's stops; invocation policy stays in each repo's lifecycle skills.
  The knowledge-base's resume skill keeps "report, never archive" and its task precedence; its clear-prep skill
  keeps "archive only on an explicit clear-now and only when complete" and performs the archive through the
  shared close. The cross-repo rule-sync gate guarantees the shared rule is declared in both repos; the shared
  skill text is kept identical by the mechanism Ray selects in question 3.
- The close skill requires a clarifying question before the force flag on an incomplete ticket, as a judgment
  under the clarify-before-acting rule rather than a permission. The ticket-creation skill documents the thin
  init task as the route; upstream's own plan-start command stays allowed and is described accurately: it
  creates root files first and then attests whichever plan resolves.

Plan migration (one-time, coordinator-executed, no operator step)

Seven verifiable outcomes, in order: archive the old program plan and its attestation byte-for-byte and move the
leftover 2026-09-21 directory to the archive; enumerate every unchecked item and still-open reference from the
old plan into the tracked extract, each mapped to a roadmap line, an existing issue or dropped-with-reason (drops
are asked); install the roadmap with Phases 10 and 11 and the migration addendum condensed to decision rows,
canonical markers only; append the goal-history iteration (writer: the coordinator, on the branch, before the
first ticket init) whose goal text names the root roadmap plus the attested ticket plan as task authority and
attestation as orchestrator-run tamper detection; reconcile selection (no live slug, no sessions directory,
pointer absent or retired, environment binding unset); write the pointer, attest the roadmap with the target
printed as root, and show; verify that status reports the root matching at Phase 11 with a zero exit and no
non-clean finding, the ledger-summary heading equals the pointer heading, the doctor is clean, and the next prompt
injects a plan body. That last outcome is issue #910's reproduction turned green.

Knowledge-base parity

A tracked root mode floor; the version literal dropped from the resume skill; a plan baseline with the
knowledge-base profile; resume and clear-prep calling the shared status and close under their existing
policies; the archive reference replaced by a pointer to the shared close; the eleven-day live slug closed
through the shared close after confirming with Ray that its round is done; the host-only test marker and the
CI-skip convention its test configuration lacks; the shared rule via rule-sync. No deny set.

Upstream asks (file, do not block)

An explicit root-target flag for the attester, and a Claude Code / Codex analogue of the Pi adapter's
plan-execute approval gate.

Operator's remaining stops

A clarifying question on genuine ambiguity or irreversibility (force-close with reason; an obligation dropped in
the migration; the goal-text wording; the open questions below); user-invoked protocol verbs; codex hooks trust
after a plugin upgrade; plugin upgrades and clearing the session; pull-request review of the pointer and goal
history. Not a stop: attestation, plan creation, closing a complete ticket, logging, status.

## Testing Decisions

What makes a good test here: it drives a public entry point (the shared command group, the handoff-check CLI, a
doctor check function, the dispatch call, a verification contract) against a real or recorded-real filesystem
state, and it carries both arms, the state that must be reported and a control that must not be, because every
defect this migration closes was a probe or a gate that could only pass.

Execution contract. Every test is assigned to a repo and a gate. Host-only tests run on every developer host and
inside that repo's ship gate, and are skipped only when the CI variable equals the literal string "true"; a
host-only test whose plugin is not installed fails, never skips, matching the existing "missing binary fails the
gate" precedent. Recorded layouts live under the knowledge-base test tree with a provenance stamp (plugin
version and script digests) and normalised nonce and timestamp fields; one host-only arm re-records and diffs
them against what the installed version writes.

- Shared library and command group (knowledge-base tests, knowledge-base ship gate). Throwaway git repos driven
  through the shared verbs with the real installed scripts. Arms: init prints the id and passes post-state
  verification, and fails legibly on a forged zero-exit initializer whose attester did not write; status names
  match after init, mismatch after an edit, ambiguous with two live slugs, session-isolation-armed with the
  sessions directory beside a root plan (control: the same tree without it), a retired pointer with a zero exit
  after an archive move, a stale pin with a non-zero exit when the binding names the archived id, a missing plan
  file for a directory whose plan was renamed, non-canonical markup for mixed and multiple-active plans, and the
  planning-disabled environment case; the phase heading agrees across pointer, ledger summary and completion
  check for a canonical plan and is warned for a mixed one; close refuses an incomplete plan, requires a reason
  with the force flag, succeeds on a complete one, moves the directory, leaves the pointer untouched, drops the
  pin, and resumes after a simulated partial failure; log refuses ambiguity and a rejected selector, writes under
  the bound id, and writes beside the root plan when only the roadmap exists; attest prints its target and
  forwards the read-only flag; the parent-phase reminder for one, zero and two matching phases. CI-runnable
  twins for classification, pointer shape, phase rule, close post-conditions and both profiles run on the
  recorded layouts. The worktree-pin acceptance probe runs host-only.
- Readers (dotfiles tests). Handoff-check at its public entry point and its classification seam: no handoff
  gives a zero exit with the informational line; a handoff with a root-roadmap profile and no root plan gives
  the missing-root finding; a no-root profile never does; the old heading convention fails; the canonical
  fixture passes; a two-authority pointer is written and verified; a stale pointer after a byte change is still
  caught.
- Doctor check (dotfiles tests; the real-dispatcher arm host-only with a fixture twin in CI). A live-plan
  fixture with planning disabled in the child environment fails (the canary that proves the probe can fire); the
  same fixture unset is clean; the doctor's own environment disabled is skipped, not failed; each non-clean
  finding with a control.
- Worker dispatch (dotfiles tests). At the dispatch seam with a fake spawn: every matrix row (attested
  dispatches; tampered or unattested does not spawn and names the attest task; ambiguous; rejected binding;
  missing plan file; no plan). At the supervisor-to-worker process boundary (host-only): the real supervisor
  path with a stand-in command that prints its environment asserts the worker inherits the plan id when set and
  lacks the disable flag, and the same probe reports the unset state as the control, the shape the advisory
  lane's real-child test already uses.
- Contracts (dotfiles, verification run plus hook-selfcheck). The operator-only contract is deleted; the inverse
  selfcheck arm and the forbid contract pass on the retired settings and both fail on a re-added script rule
  and on a re-added wrapper rule; the wiring contract binds skill to task to command to library; a contract
  forbids a planning scrub in the worker dispatcher; the advisory-lane isolation contract keeps its behaviour
  tokens with its documentation token updated.
- Documentation surface. The agent-docs linter, the skills mirror parity step, rule-sync in both repos, the
  handoff-fence contract, the shared-skill parity check; skill evals in dry-run for the ask-before-force
  behaviour.
- Live arms recorded in the tickets. After the retirement ticket, the model runs the read-only attest form and
  receives a zero exit while a covered credential-file read is still denied (control). After the migration
  ticket, the seventh migration outcome above.

Prior art in this codebase, worded to what it proves: the attest wrapper tests prove plugin resolution through an
injected home and that the passthrough call site is wired (they inspect source and parser output; they do not
execute the script); the handoff-check suite is mostly at the classification function with public-CLI coverage in
its main-path tests; the worker dispatcher's fake-spawn "no process launched" arms; the doctor's check functions
over an assembled setup, including "unreadable config fails rather than passes"; the advisory lane's real-child
positive-plus-control test; the host-only marker with its CI auto-skip and the "missing binary fails the gate"
sibling; the knowledge-base's git-fixture conftest and its render-is-the-arm usage test.

## Out of Scope

- The pr-loop ship, fix, land loop (its own spec).
- Phase 10 work: retiring the advisory codex lane and its scrub, the one-codex-entry-point consolidation,
  research mode, role-typed models, codex-native install and the daemon gate.
- Adopting the plugin's plan-loop or plan-goal commands, gated mode, session isolation, the phase-status script,
  or any Claude-side approval gate for attestation; auto-attest in any hook or at dispatch; a Claude function
  hook or a codex hook for the plan doctor; the plan id in tracked settings or in the main clone; rename-based
  archival; automatic roadmap status flips on close; a shared active-plan pointer as the binding.
- A codex-side doctor arm through the codex plugin's own adapter (optional follow-up), and the knowledge-base's
  coreutils shim tax (its own ticket).
- Changing upstream behaviour locally; the two upstream asks are filed, not blocked on.
- Any change to how the plan's contents are trusted as instructions (delimiter framing, nonce, prompt-injection
  posture): unchanged upstream behaviour.

## Further Notes

Issue relationships. This migration absorbs #910 ("plan tampered fires every prompt and has no real tracking
issue"): the doctor's dark-hooks probe, the worker pre-dispatch refusal and the migration's final verification
(the next prompt injects a plan body) are #910's reproduction turned green, and #910 closes with the migration
ticket. This migration precedes #1327 ("land the native AgentsView service and settle its parked worktree"):
#1327 is the first ticket to run under the new workflow, its parked worktree becomes the first pinned worktree, so
it must not start before the migration ticket lands and question 1 is answered.

Ticket order and dependencies. Retire the operator-only posture first and independently: everything after it is
model-runnable in this repo only once the deny is gone, and it ships both regression layers. The shared library
and command group are a knowledge-base change (with the host-only convention and the recorded layouts), followed
by the dependency pin bump in dotfiles. The reader migration with the consumer cutover and contract migration, the
mise tasks in both repos, the doctor check and the worker dispatcher change are independent after the pin bump;
the tasks must precede the documentation ticket (skill text naming a task that does not exist fails the docs
gate); the readers must precede the plan migration (the new roadmap shape fails today's handoff-check). The
documentation ticket follows those four; the plan migration is last on the dotfiles side. Knowledge-base parity
follows the shared library, in parallel with the dotfiles tickets; closing the eleven-day slug waits for Ray's
confirmation that its round is done. The upstream asks can be filed at any time.

Open questions for Ray, each with a recommendation; the spec above carries the recommended answer provisionally.

1. Root authority in linked worktrees. Recommended: the roadmap lives in the main clone only; a linked worktree
   is a ticket checkout whose status reports the root as not applicable, whose pointer command updates only the
   ticket block, and whose roadmap edits happen in the main clone at the boundary. Alternative: the init pin
   copies the root plan and its attestation into the worktree, at the cost of two editable copies whose
   divergence the main clone cannot see.
2. Compatibility surface for the dotfiles attest and pointer subcommands. Recommended: delete them outright in
   the cutover ticket, migrating the wiring contract in the same change; the memory flip at the next handoff
   covers stale spellings. Alternative: permanent thin re-exports, a second entry point to keep green forever.
3. The content-sharing mechanism for the shared skill text. Recommended: ship the shared skill bytes inside the
   shared package and keep a byte-identical copy in each repo's skills directory, checked by a parity gate on the
   pattern the skills mirror already uses. Alternative: rely on rule-sync's shared lines, which is presence-only.
4. Planning disabled in the dispatcher's own environment. Recommended: warn and dispatch, recording it in the
   dispatch record, since a coordinator whose own hooks are off is not a defect in the lane. Alternative: refuse,
   which breaks every planning-disabled session's dispatch.
5. Whether the dotfiles ship gate runs the pinned library's own tests. Recommended: no; the knowledge-base's
   gates own them, and dotfiles adds one host-only smoke test that the pinned status verb runs here plus a
   contract that the pin is at or above the version shipping the plan verbs.

Rulings encoded, for the reviewer's checklist: upstream's trust model supersedes the operator-only posture and
the round-2 hardening; root roadmap plus per-ticket plans; plan id per worktree; the hidden archive directory; one
merged workflow in the shared package with per-repo flags; skill to mise task to library layering; close
model-runnable when complete with the force flag behind a clarifying question and the pointer untouched; worker
lanes see the plan with the check at the dispatch call; the advisory lane's scrub kept until Phase 10; Phase 10
step 5's plugin items superseded; the goal-history iteration written by the coordinator with the changed goal
text; the knowledge-base's eleven-day slug archived via the shared close.

Deciding risk: stale memory. The memory index, several transcripts, the config paragraph, task descriptions and
test docstrings all still say "operator-only", and a later session acting on that will re-add the deny from
habit. The inverse selfcheck arm and the forbid contract are the control arms; the documentation rewrite and the
memory-index flip at the next handoff are the rest of the mitigation.

Unverified items carried from the design, to be settled by the implementing tickets: that a per-worktree mise
override's environment reaches a Claude process launched from that shell (the acceptance probe settles it); the
exact codex hook trust currency after a plugin upgrade; whether the knowledge-base already has a plugin-root
resolver (none was found beyond one hard-coded path in its eval cases; the dotfiles resolver moves).
