# `/to-tickets` draft — #1351 pwf current-workflow migration (Brief R)

> Written by a Fable lane (`general-purpose`, `model: fable`) on 2026-09-23/24 for the coordinator's step 4
> (quiz Ray) and step 5 (publish). Steps 1–3 of `mattpocock-skills/to-tickets` only. Inputs, all read in full:
> #1351's body and its authoritative corrections comment; the design of record
> `pwf-migration-fable-round3-2026-09-23.md` (T1–T10); `pwf-migration-spec-v2-2026-09-23.md` (resolution
> table F1–F17, Questions 1–5 — all ruled as recommended); `task_plan.md` § "Addendum — pwf current-workflow
> migration" rounds 1–7 and "Current Phase"; `docs/issue-tracker.md`, `docs/triage-labels.md`, `CONTEXT.md`.
> The briefs file's D4/operator-only statements are superseded by round 4 and are not carried.
>
> Evidence discipline: `mise run graphify-health` returned rc=3 `stale` (built at `762396bc`, HEAD `b7c59920`),
> so the graph was not used; every anchor below was read from source on this branch. Anchors into the installed
> pwf 3.20.7 scripts are carried from spec v2 and marked *inherited*. Nothing was edited except this file.

## How the breakdown was cut

- **Tracer bullets, not layers.** Every ticket is a vertical slice through library → CLI → mise task → tests
  (knowledge-base) or task → consumer → contract → tests (dotfiles), and is demoable alone.
- **Prefactoring first.** Ticket 1 (retire the operator-only posture) and ticket 2 (the shared-library
  foundation: profile, plugin-root resolver moved out of dotfiles, host-only harness, recorded layouts) are the
  two "make the change easy" slices; everything else builds on them.
- **The one wide refactor is cross-repo, and it is already expand–contract.** The dotfiles attest/pointer
  commands are consumed by tasks, two skills, a contract and three test modules across two repos. Expand in the
  knowledge-base (tickets 2–8, the new verbs exist beside the old commands), bump the pin (9), migrate the
  call sites and **contract in the same change** (10 — Ray's Q2 ruling: delete outright, no re-export period),
  then the remaining consumers (11–16). CI stays green batch to batch because dotfiles keeps its old commands
  until ticket 10.
- **Knowledge-base work is the knowledge-base's tickets** (K-prefixed below), with every cross-repo edge named.
  Ordering trap carried from `rule-sync`: the knowledge-base must carry the shared rule (ticket 14) BEFORE
  dotfiles widens the gate (ticket 16), or `main` goes red.
- **T1 first, T8 last on the dotfiles side; T10 is drafts for Ray, not tickets.**
- **Sizing.** Each ticket fits one fresh context window. The design's T2 (seven verbs) is split into six KB
  slices; T7 (docs) into the two lifecycle skills versus the rest of the instruction surface; T9 into adoption
  versus the Ray-gated slug close.
- **Issue template.** Each body below uses `## Parent`, `## What to build`, `## Acceptance criteria`,
  `## Blocked by`. No file paths or code in ticket bodies; the "Implementer anchors" appendix carries them.
- **Labels (proposal for step 5):** `enhancement` + `ready-for-agent` on every ticket except 17
  (`ready-for-agent`, but orchestrator-executed — not a codex lane; it carries three `AskUserQuestion` stops)
  and 18 (`ready-for-human` until Ray confirms the round is done). GitHub native issue dependencies for the
  edges (db-id, not number — see the tracker doc).

## Dependency graph

```
 1 D1 retire operator-only posture ──────────────────────────┐
                                                             ├──► 10 D3 readers + cutover + contract ─► 11 D4 four new tasks ─┐
 2 K1 foundation + status ─┬─► 3 K2 status findings/phase ─┬─► 9 D2 pin bump + smoke + pin contract ─┤                       ├─► 15 D7 handoff/resume skills ─┐
                           ├─► 4 K3 init/--pin/attest ─────┤                                          ├─► 12 D5 doctor pwf-hooks ─┤                              │
                           │      │                        │                                          └─► 13 D6 sdlc_team lanes ──┼─► 16 D8 instruction surface ─┼─► 17 D9 plan migration
                           │      └─► 5 K4 log + close ────┤                                                                      │        ▲                     │
                           ├─► 6 K5 pointer (needs 3) ─────┤                                                                      │        │                     │
                           └─► 7 K6 doctor-probe ──────────┘                                                                      │        │                     │
 3,4,5,6,7 ─► 8 K7 shared skill/rule bytes + parity verb ─► 14 K8 KB adoption (mode floor, lifecycle skills, rule) ──────────────┴────────┘                     │
 5,14 + Ray's confirmation ─► 18 K9 close the eleven-day slug                                                                                                   │
```

Frontier at start: **1** and **2** (both unblocked; different repos, no shared files).

---

## Ticket 1 — Retire the operator-only attestation posture; make attestation model-runnable tamper detection

**Repo:** ray-manaloto/dotfiles · **Design:** T1 · **Blocked by:** none — can start immediately

## Parent

#1351

## What to build

After this ticket, the orchestrator (any Claude session in this repo) can run the read-only attest form and the
write form of the plan attest task itself, and every place that told it not to has been rewritten to say the
opposite. Attestation becomes what upstream says it is: a local digest that detects a changed plan while the
digest is trusted, re-armed by whoever intentionally edited the plan. Two independent, mutation-tested checks
guarantee that no spelling of the retired deny rules can be reintroduced by a later session acting on stale
memory — that is the deciding risk of the whole migration, and this ticket ships its control arm.

Retired by name: the eleven deny entries (six naming the attest and selector scripts in shell and PowerShell
forms, five naming the wrapper task and the CLI beneath it); the selfcheck presence arm with its deny-bases table
and registration; the operator-only verification contract; the four tests asserting the deny is present and the
two imports that would break collection if the selfcheck functions were deleted alone; the operator-only wording
in the Claude-specific config, the task description, the CLI help, the wrapper's docstring, the test module's
docstring, and the mise-tasks rule row that calls attestation a human boundary.

Kept, for reasons unrelated to the old posture: resolving the installed plugin root (highest numeric version,
never modification time) and the passthrough-separator repair behind the read-only form, with their tests.

Added: (a) the selfcheck arm inverted and JSON-scoped — parse the settings, iterate the deny list, fail on any
entry matching the attest script, the selector script, the wrapper task/CLI or the initializer in any spelling;
(b) a forbid-pattern verification contract over the settings file for the same four spellings, plus a required
sentence in the Claude-specific config stating attestation is model-runnable tamper detection.

Stated cost, accepted by Ray: an attested plan no longer means Ray approved it. Write that sentence where the
old "operator-only" sentence was.

## Acceptance criteria

- [ ] Live arm: from a Claude session, the read-only attest form exits 0 and prints the attester's output;
      control: a covered credential-file read (the home netrc) is still denied by the same settings.
- [ ] Live arm: the bare attest form exits 0 after an intentional plan edit and the plan doctor reports MATCH;
      control: before the attest, the doctor reports a hash mismatch.
- [ ] Mutation arm: re-adding one script-spelling deny rule makes BOTH the inverted selfcheck arm and the forbid
      contract fail; re-adding one wrapper-spelling rule makes both fail; restoring the file makes both pass.
- [ ] The credential `Read` denies and every unrelated deny rule remain accepted (control for the inverted arm).
- [ ] The retired contract, selfcheck functions, deny tests and imports are gone; the resolver, separator and
      passthrough tests still pass unchanged.
- [ ] No tracked file in the repo still says "operator-only", "OPERATOR ONLY" or "HUMAN boundary" about
      attestation (grep with a known-present control term).
- [ ] Hook-selfcheck, `mise run lint`, pytest, `dotfiles-setup verify run` and `mise run lint-docs` are green
      with file-captured exit codes.

## Blocked by

- None — can start immediately.

**Seam / prior art:** the hook-selfcheck check function over an injected settings path (the existing
"half-written ban" test is the shape — inverted); `regex_forbid` + `require_tokens` contracts in the suites
file; the "unreadable settings file fails rather than passes" arm is kept as-is for the inverted check.

---

## Ticket 2 — K1: shared planning library foundation and `plan status` (attestation, selection, exit codes)

**Repo:** ray-manaloto/knowledge-base · **Design:** T2 (first slice) · **Blocked by:** none — can start immediately

## Parent

ray-manaloto/dotfiles#1351 (cross-repo; this is the first knowledge-base slice of the shared library)

## What to build

The prefactoring slice for everything shared. After this ticket, `kb-setup plan status` and the `plan-status`
mise task run in the knowledge-base itself and in any throwaway repo, and report: the resolved target (root
roadmap, ticket plan by id, or none); per-authority attestation state (match, mismatch, unattested); selection
state (resolved, ambiguous, none); whether the checkout is a linked worktree (detected from git's common
directory, in which case the root is reported as not applicable rather than missing); and an exit code that is
non-zero only on a mismatch or unattested state of a resolved authority or on ambiguity.

It ships the foundations the other verbs stand on: the per-repo profile (a plan section in a tracked baseline
file with a config override for tests; keys: root roadmap yes/no, pointer location, program record,
ticket-reference pattern, archive directory, handoff skill — no deny-set key), the knowledge-base's own profile
baseline (no root roadmap, no pointer, direction docs, next-ticket ids, clear-prep), the installed-plugin-root
resolver moved out of dotfiles (highest numeric version wins, never mtime; injectable for tests; legible error
when the plugin or a script is absent), the host-only test marker with the CI-skip convention (skipped only when
the CI variable is the literal string "true"; a missing plugin FAILS, never skips), and the recorded-layout
harness (layouts under the test tree stamped with plugin version and script digests, nonce/timestamp fields
normalised, one host-only arm that re-records and diffs against what the installed version writes).

Every verb wraps unmodified upstream scripts resolved from the plugin root; status resolves once and passes that
identity to every reader it calls.

## Acceptance criteria

- [ ] In a throwaway repo driven with the real installed scripts (host-only): status reports MATCH right after
      upstream's initializer creates a slug plan; MISMATCH after one byte of the plan changes; UNATTESTED when
      the attestation file is removed; AMBIGUOUS with two live slugs and no selector; NONE in an empty repo.
      Exit codes: 0, non-zero, non-zero, non-zero, 0 respectively.
- [ ] Linked-worktree arm: in a worktree of that repo, status prints the root as not applicable and exits 0;
      control: the main checkout of the same repo with no root plan under a root-roadmap profile reports a
      missing root plan (the non-clean finding lands fully in ticket 3, but the root/worktree distinction is
      here).
- [ ] Profile arm: the same tree under a no-root profile and a root-roadmap profile produces different root
      lines; the config override is what selected them.
- [ ] Resolver arm: two fake plugin versions in an injected home — the higher number wins even when the lower
      has the newer mtime; an absent plugin is a named error, not a silent miss.
- [ ] Harness arm: a host-only test re-records the layout and diffs clean; corrupting one recorded file makes
      it fail naming the file.
- [ ] Running status in the knowledge-base checkout itself (which currently holds one eleven-day live slug)
      resolves that slug and exits 0 or names exactly why not.
- [ ] CI twin: the classification runs on recorded layouts without the plugin installed.
- [ ] The knowledge-base ship gate is green; the host-only tests were run on a developer host with
      file-captured exit codes.

## Blocked by

- None — can start immediately.

**Seam / prior art:** the `kb-setup` CLI entry point (one `main`, subcommands); the knowledge-base's real-git
conftest fixtures (throwaway repos are already the house style); the dotfiles plugin-root resolver tests
(highest-version-wins, absent-plugin-is-legible) move here verbatim; the dotfiles `host_only` marker + CI-skip
conftest hook is the convention to copy.

---

## Ticket 3 — K2: `plan status` findings, informational states and the canonical active-phase rule

**Repo:** ray-manaloto/knowledge-base · **Design:** T2 (status, second slice) + F1/F3/F11 · **Blocked by:** 2

## Parent

ray-manaloto/dotfiles#1351

## What to build

Status becomes the one-line answer to "is the plan I am about to trust the resolved one, attested, unambiguous
and current?" It adds the **non-clean findings** — a second live slug; a stale environment pin (a binding naming
an archived or missing directory — upstream fails closed on it); an armed session-isolation directory (with the
two exits named: delete the directory, or pin the plan id); a missing root plan under a root-roadmap profile in
the main clone; a resolved directory without a plan file — and the **informational states** that exit 0: a
pointer naming an archived id, a pointer naming nothing, and non-canonical phase markup. It also prints the
completion check's report and the ledger summary block from upstream's own scripts.

It defines the **canonical active-phase rule** the pointer, the ledger summary and the completion check all
agree on: the first phase heading whose following primary status marker says in progress. Inline bracketed
status tokens, or more than one phase in progress, produce the non-canonical-markup warning instead of a
silent disagreement. The rule is exposed as a library function so ticket 6 (pointer) and the dotfiles readers
use the same one.

Clean terminal states are enumerable after this ticket: root-only with no pointer; root-only with a retired or
dangling pointer; root plus one live slug whose pointer names it; and ticket-only in a linked worktree.

## Acceptance criteria

- [ ] Each non-clean finding has a positive arm and a control in a throwaway repo: second live slug (two live
      dirs) vs one; stale pin (env binding names the archived id) vs a binding naming the live id;
      session-isolation armed (the sessions directory beside a root plan) vs the same tree without it; missing
      root plan (root profile, main clone, no root file) vs a linked worktree of the same repo; missing plan
      file (plan renamed inside its directory) vs intact. Each positive exits non-zero.
- [ ] Each informational state exits 0 and is printed: retired pointer after an archive move; dangling pointer
      naming a never-existing id; non-canonical markup for a plan with inline tokens and for a plan with two
      phases in progress.
- [ ] Phase-rule arm: for a canonical plan, the phase named by the library rule equals the heading the upstream
      ledger summary prints and the one the upstream completion check counts; for a mixed-format plan the
      warning fires and the rule still returns the primary-marker phase.
- [ ] The planning-disabled environment case (the plugin's own disable variable set) is reported, not crashed.
- [ ] CI twins on recorded layouts for every classification above.

## Blocked by

- Ticket 2 (foundation, resolver, profile, harness).

**Seam / prior art:** same CLI seam and harness as ticket 2; the phase rule is a pure function with fixture
plans (canonical, mixed, multiple-active, no-phase, planning-disabled).

---

## Ticket 4 — K3: `plan init` (slug mode, post-state verification, `--pin`) and `plan attest` (target printed, passthrough)

**Repo:** ray-manaloto/knowledge-base · **Design:** T2 (init + attest) + F10/F15 · **Blocked by:** 2

## Parent

ray-manaloto/dotfiles#1351

## What to build

The orchestrator creates a ticket plan with one command that prints the plan id and a status line, and attests
with one command that prints which plan it will target before writing.

`plan init "<title>"` execs upstream's initializer in slug mode from the project root (never the autonomous
flag, never root mode), captures the printed id (name collisions get the numeric suffix upstream assigns),
verifies the post-state — directory exists, mode token inherited from the tracked root mode file, attestation
equals the plan digest, the active-plan pointer names the id — because the initializer reports an attester
failure at a zero exit, then prints the id and a status. Any post-state miss exits non-zero and names what to
remove. It **warns, and does not refuse**, when another live slug exists (naming close-or-worktree), because
upstream's initializer runs as shipped. `--pin` appends the plan-id binding to that worktree's gitignored
per-clone mise override.

`plan attest [flags]` prints the target the resolver chose (the root only when no live ticket plan resolves and
no selector is set), passes every flag straight through without enumerating upstream's, warns when the roadmap
is unattested while a ticket plan resolves, and carries the passthrough-separator repair so the read-only form
reaches the script from a mise task in either repo. The `plan-init` and `plan-attest` mise tasks are added.

## Acceptance criteria

- [ ] Init arm (host-only, real scripts): the printed id names a directory whose plan is attested at creation,
      whose mode token equals the tracked root floor, and whose pointer names it; status right after is MATCH.
- [ ] Forged-initializer arm: with an injected initializer that exits 0 without writing an attestation, init
      exits non-zero and names the attestation as the miss.
- [ ] Second-slug arm: init with one live slug present succeeds AND prints the close-or-worktree warning;
      control: no warning with none present.
- [ ] Pin acceptance probe (host-only): after `--pin` in a throwaway worktree, a fresh process launched through
      mise activation from that directory reports the binding; a shell started before the write still reports
      the old value (control). Hook attachment is NOT asserted here (that is the doctor's, ticket 7/12).
- [ ] Attest arm: with one live slug, the printed target is the slug; with none, the target is the root; the
      read-only flag is forwarded and the script's output appears; the roadmap-unattested-while-slug-live
      warning fires and is absent when the roadmap is attested (control).
- [ ] Both mise tasks call the verbs and the read-only form reaches the script through the task.

## Blocked by

- Ticket 2.

**Seam / prior art:** the dotfiles attest wrapper's separator test ("inserted only where it is needed") and its
"documented read-only form reaches the script" wiring test move here and gain a real execution arm; the
forged-initializer arm is new (a control the design's C4 finding demands).

---

## Ticket 5 — K4: `plan log` and `plan close` (archive, ledger event, pin drop, parent-phase reminder, idempotent resume)

**Repo:** ray-manaloto/knowledge-base · **Design:** T2 (log + close) + C3/C7/F1/F2/F14 · **Blocked by:** 3, 4

## Parent

ray-manaloto/dotfiles#1351

## What to build

Closing a completed ticket is one model-runnable command, and logging is bound to the plan the plugin would
actually inject.

`plan log <event> "<summary>" [--agent NAME]` resolves exactly as upstream does — environment binding, then a
live pointer, then the single live slug, then the **root roadmap** when the profile declares one and no selector
is set (upstream's legacy single-file path, so root-only sessions can still log) — refuses on ambiguity or a
rejected selector, and passes the resolved id explicitly to upstream's appender.

`plan close <id> [--force --reason "<text>"]`: while the directory is live, requires the resolved id to equal the
given id and upstream's completion check to report every phase complete, or `--force` with a mandatory reason
recorded in the ledger note; appends the phase-complete event; moves the directory under the hidden archive and
verifies; **never touches the active-plan pointer** (a stale pointer is a hint upstream falls through); drops the
worktree pin and warns that the running shell still carries it; prints the parent-phase reminder — the ticket
reference from the plan's goal line looked up in the roadmap: exactly one phase block yields "belongs to that
phase, which lists N other unchecked references", zero or several yields "no unique parent phase" and nothing is
manufactured. Close is idempotent by post-condition: an id already under the archive with no live directory
resumes the remaining steps instead of failing the precondition. Non-transactional by design; status (ticket 3)
names every partial state. Flipping a roadmap status is a coordinator edit at the boundary, never automatic. The
`plan-log` and `plan-close` mise tasks are added.

## Acceptance criteria

- [ ] Log arms: writes under the bound id when a binding is set; under the single live slug when none is;
      beside the root plan when only the roadmap exists (root profile); refuses AMBIGUOUS (two live slugs, no
      selector) and a rejected selector (binding names a missing dir) naming the fix.
- [ ] Close refuses an incomplete plan with a message naming the phases still open; with `--force` and no
      reason it refuses; with `--force --reason` it succeeds and the reason is in the ledger note.
- [ ] Close on a complete plan: directory is under the archive; the ledger has the phase-complete event; the
      pointer bytes are byte-identical before and after; the pin line is gone from the override file and the
      live-shell warning printed; status afterwards reports a retired pointer at exit 0 (the clean terminal
      state from ticket 3).
- [ ] Idempotence arm: simulate a partial failure (directory moved, ledger event missing) and re-run close —
      it completes the remaining steps and exits 0; control: a fresh live id is not treated as already closed.
- [ ] Parent-phase reminder for one, zero and two matching roadmap phase blocks; the zero/two cases print
      "no unique parent phase".
- [ ] Both mise tasks wired; CI twins for close post-conditions on recorded layouts.

## Blocked by

- Ticket 3 (completion check + status states it relies on), ticket 4 (the pin format it removes).

**Seam / prior art:** CLI seam with the real scripts (host-only); the knowledge-base's existing clear-prep
archive recipe (mkdir the archive, check-complete first, mv) is the behaviour being promoted into code.

---

## Ticket 6 — K5: `plan pointer` — the tracked two-authority pointer

**Repo:** ray-manaloto/knowledge-base · **Design:** T2/T3 (pointer half) + C6 + Q1 · **Blocked by:** 3

## Parent

ray-manaloto/dotfiles#1351

## What to build

The pointer a pull request reviews records both authorities: a root block (digest and active phase; null only
under a no-root profile) and a ticket block (id, digest, active phase; null when no ticket is live), plus a
timestamp; never task text. `plan pointer` writes it to the profile's pointer location and prints both digests.
From a linked worktree it updates only the ticket block and carries the committed root block forward unchanged
(Ray's Q1 ruling: the roadmap lives in the main clone only). The active phase comes from ticket 3's canonical
rule. Under a no-pointer profile (the knowledge-base's own) the verb says so and exits 0. The `plan-pointer`
mise task is added.

## Acceptance criteria

- [ ] Root-only tree: root block filled, ticket null; root + live slug: both filled with the slug's id; the
      digests printed equal the file digests recomputed by the test.
- [ ] Linked-worktree arm: with a committed pointer holding a root block, running pointer in a worktree
      rewrites only the ticket block and leaves the root block byte-identical; control: in the main clone both
      blocks update.
- [ ] Non-canonical plan: the pointer still writes (primary-marker phase) and the warning is printed;
      no-phase plan: exits non-zero and writes nothing.
- [ ] No-pointer profile: exit 0 with an explicit "profile declares no pointer" line, nothing written.
- [ ] The pointer never contains a task line (a fixture with a "Next task" line in the plan is written and the
      pointer is grepped for its text: zero hits, with a known-present control term).

## Blocked by

- Ticket 3 (phase rule, linked-worktree detection).

**Seam / prior art:** the dotfiles pointer tests ("missing active heading fails without writing a pointer",
"last heading is the only recorded phase") are the shapes, rewritten to the two-authority schema and the
primary-marker rule.

---

## Ticket 7 — K6: `plan doctor-probe` — the fail-only dark-hooks probe

**Repo:** ray-manaloto/knowledge-base · **Design:** T5 (shared half) + Lane B option B · **Blocked by:** 2

## Parent

ray-manaloto/dotfiles#1351

## What to build

The library function both repos' session doctors call. It skips — never fails — when the calling environment has
planning disabled; otherwise it runs the real Claude hook dispatcher for the user-prompt event with the resolved
plugin root, a bounded timeout and the mise shims directory stripped from the child path, and returns FAIL only
when the shared resolver says a plan exists and the dispatcher's output is empty. It also returns every non-clean
status finding from ticket 3 as doctor findings (informational states are not). Side effects of a diagnostic
fire (turn and progress markers refreshed) are documented in its docstring and the skill text. Exposed as
`kb-setup plan doctor-probe` for the host-only test and for a codex mirror later.

## Acceptance criteria

- [ ] Canary (host-only): a live-plan fixture with planning disabled in the CHILD environment only → FAIL
      naming the dispatcher; the same fixture with it unset → clean. This is the probe's own control arm.
- [ ] The probe's own environment disabled → skipped with a reason, never FAIL.
- [ ] Timeout arm: an injected dispatcher that sleeps past the bound → FAIL naming the timeout, and the probe
      returns within the bound.
- [ ] Each non-clean finding from ticket 3 surfaces as a doctor finding with its control; informational states
      do not.
- [ ] CI twin: a fixture dispatcher (function seam) exercises the same decision table without the plugin.

## Blocked by

- Ticket 2 (resolver, profile) — and ticket 3 for the findings pass-through (may land with a stub that the
  ticket-3 merge fills; if so say so in the PR).

**Seam / prior art:** the doctor check functions over an assembled setup in dotfiles are the shape; the "canary
that must fail" pattern from the renovate RE2 gate (assert the capability, never sniff a symptom).

---

## Ticket 8 — K7: the shared `pwf-workflow` skill and rule shipped as bytes in the package, with a parity verb

**Repo:** ray-manaloto/knowledge-base · **Design:** T7 (shared half) + Q3 · **Blocked by:** 3, 4, 5, 6, 7

## Parent

ray-manaloto/dotfiles#1351

## What to build

One skill text and one rule text carry the posture, the layout, who attests when, the state vocabulary from
tickets 3–7, and the operator's remaining stops. They ship as bytes inside the shared package, and
`kb-setup plan skill-sync [--check]` writes (or verifies) a byte-identical copy into a repo's skills and rules
directories — the mirror-parity mechanism Ray selected in Q3, on the pattern the dotfiles skills mirror already
uses. Invocation policy (WHEN each repo calls status/close) is deliberately NOT in the shared text; it stays in
each repo's lifecycle skills. The knowledge-base installs its own copy in this ticket and adds the `--check` arm
to its lint gate. The shared skill documents the thin init task as the ticket route and describes upstream's own
plan-start command accurately (it creates root files first and then attests whichever plan resolves). The close
skill section requires a clarifying question before `--force`.

## Acceptance criteria

- [ ] `--check` passes on a fresh copy; editing one byte of the repo copy fails naming the file; editing the
      package copy and re-running sync restores parity.
- [ ] The skill text names only tasks that exist in the knowledge-base after tickets 2–7 (the agent-docs
      linter and a grep of every `mise run` mention against the task list, with a known-absent control).
- [ ] The rule file has the eager-rule shape the rule-sync gate expects (stem, headings) and the knowledge-base
      declares it in its rules directory.
- [ ] The knowledge-base lint gate runs the parity check; skill eval in dry-run for the ask-before-force
      behaviour passes.

## Blocked by

- Tickets 3–7 (the vocabulary and verbs the text documents).

**Seam / prior art:** the dotfiles skills-mirror generator's `--check` arm and its "stale pattern names the
skill" test.

---

## Ticket 9 — D2: bump the shared-package pin; one host-only smoke; a minimum-version contract

**Repo:** ray-manaloto/dotfiles · **Design:** T2 pin bump + Q5 · **Blocked by:** 2, 3, 4, 5, 6, 7

## Parent

#1351

## What to build

Dotfiles consumes the plan verbs. The SHA-pinned dependency on the shared package moves to the commit that ships
tickets 2–7; one host-only smoke test runs the pinned `plan status` against this repo and asserts it resolves
and exits 0 or names a finding; a verification contract asserts the pin is at or above the version that ships
the plan verbs (Ray's Q5 ruling: dotfiles does not run the knowledge-base's test suite). The dotfiles profile
section is added to the existing doctor baseline (root roadmap yes, the tracked pointer path, goal history,
issue-number ticket references, the hidden archive, the handoff skill). Nothing else changes in this ticket —
the old dotfiles attest and pointer commands still exist and still work (expand before contract).

## Acceptance criteria

- [ ] Lockfile and pin updated; the smoke test passes on a developer host and is skipped in CI by the
      host-only convention (control: with the plugin directory renamed, it FAILS, never skips).
- [ ] The pin contract passes; editing the pin back to the previous SHA makes it fail naming the version.
- [ ] `mise run plan-pointer` and `mise run plan-attest -- --show` (the OLD commands) still work — this
      ticket must not break them.
- [ ] Lint, pytest, verify green.

## Blocked by

- Tickets 2–7 (all in the pinned SHA).

**Seam / prior art:** the existing "kb-setup git dep" pin comment block in the project file; the `md-budget`
shell-out is the precedent for a pinned `kb-setup` verb used by a dotfiles gate.

---

## Ticket 10 — D3: reader migration and consumer cutover — two-authority pointer, canonical phase rule, handoff-check, contract migration

**Repo:** ray-manaloto/dotfiles · **Design:** T3 + Q2 + F5/F7 + M-7 · **Blocked by:** 1, 9

## Parent

#1351

## What to build

The contract half of the expand–contract. After this ticket `mise run plan-pointer` and `mise run plan-attest`
call the shared verbs directly; the dotfiles attest and pointer subcommands, their modules and their tests are
deleted (Ray's Q2 ruling — no re-export period); the old pointer-wiring contract is replaced, in the same change,
by a workflow-wiring contract binding mise task → shared verb registration → library function → skill fence; and
handoff-check reads the new world: with a handoff present it verifies both authorities against disk, reports a
missing root plan under a root-roadmap profile in the main clone, and compares the plan digest written in the
handoff text with the tracked pointer (integrity-review item M-7); with no handoff its public path keeps today's
zero-exit informational line so a fresh clone stays green. The "next session" heading convention is retired from
every reader. The handoff skill's existing pointer fence stays verbatim (a contract pins it); the root ledger
pattern joins the ignore list.

## Acceptance criteria

- [ ] Public-CLI arms: no handoff → rc 0 and the informational line; handoff + root profile + no root plan →
      the missing-root finding, rc 1; no-root profile → never; a handoff whose stated plan digest differs from
      the pointer → a named finding; equal → none.
- [ ] Reader arms: a fixture using the old "next session" heading now fails; a canonical primary-marker fixture
      passes; the two-authority pointer is written and verified; a stale pointer after a byte change is still
      caught.
- [ ] Deletion arm: the two subcommands are absent from the CLI's help; their modules and tests are gone; the
      task-existence check in verify passes.
- [ ] Contract arm: the old pointer-wiring contract is gone; the new workflow-wiring contract passes; deleting
      the mise task line for `plan-pointer` makes it fail (call-site token, not a definition).
- [ ] The handoff skill's pointer fence is byte-identical to before (the handoff-fence contract passes).
- [ ] Lint, pytest, verify, hook-selfcheck, lint-docs green.

## Blocked by

- Ticket 1 (rewrites the same attest test module and task description), ticket 9 (the verbs exist here).

**Seam / prior art:** handoff-check's public `main` tests and its classification tests (both shapes exist);
the "fresh clone has no active-plan finding" test is rewritten, not deleted.

---

## Ticket 11 — D4: the four remaining thin mise tasks (status, init, close, log) and the wiring contract extended to six

**Repo:** ray-manaloto/dotfiles · **Design:** T4 (dotfiles half) · **Blocked by:** 10

## Parent

#1351

## What to build

Dotfiles exposes the same six thin tasks as the knowledge-base. `plan-status`, `plan-init`, `plan-close` and
`plan-log` are added, each a one-line caller of the matching shared verb with a description stating the new
posture (model-runnable; print the target first; close refuses incomplete unless forced with a reason after
asking). The workflow-wiring contract from ticket 10 is extended to bind all six tasks. The tasks-only rule's
canonical task map gains the six rows.

## Acceptance criteria

- [ ] Each task runs here and exits as the verb does (status on this repo; init/close round-trip on a throwaway
      slug in this checkout, closed and archived within the test — leaving no live slug behind, asserted).
- [ ] Contract arm: removing any one of the six task lines fails the wiring contract naming it.
- [ ] The passthrough separator reaches the script from `plan-attest -- --show` and `plan-close -- <id> --force
      --reason x` alike.
- [ ] Lint, verify, lint-docs green.

## Blocked by

- Ticket 10 (the contract it extends; the task pattern it copies).

**Seam / prior art:** the wiring contract's per-path call-site tokens (the apt-pins contract description explains
why a definition-only token stays green through a deleted wiring line — bind the invocation).

---

## Ticket 12 — D5: session doctor `pwf-hooks` check (FAIL-only), reaching interactive codex through the existing mirror

**Repo:** ray-manaloto/dotfiles · **Design:** T5 (dotfiles half) · **Blocked by:** 9

## Parent

#1351

## What to build

The session-start doctor gains one check, declared in the doctor baseline and enabled here, that calls the shared
doctor-probe (ticket 7): dark hooks FAIL loudly at session start instead of being noticed as silence, and every
non-clean status finding (second live slug, stale pin, session isolation armed, missing plan file) is a doctor
finding. Informational states are not. It reaches interactive codex sessions through the codex session-start
doctor mirror that already exists; no new Claude function hook and no new codex hook of any kind. The
verification scope is stated honestly in the check's text: Claude dispatcher health plus codex hook
configuration, not proven codex injection.

## Acceptance criteria

- [ ] Assembled-setup tests: live plan + planning disabled in the child → FAIL; unset → clean; the doctor's own
      environment disabled → skipped; one arm per non-clean finding with its control.
- [ ] Real-dispatcher arm (host-only) via the probe; fixture-dispatcher twin in CI.
- [ ] SessionStart doctor run on this repo is silent when healthy (rc 0, no output) and prints the finding when
      the canary is injected via the environment.
- [ ] The codex mirror still invokes the same doctor command (a test asserts the codex hooks file's
      session-start command contains the doctor task — the wiring, not the behaviour).

## Blocked by

- Ticket 9.

**Seam / prior art:** doctor check functions over an assembled setup, including "unreadable config fails rather
than passes"; the doctor baseline's per-check enable flags.

---

## Ticket 13 — D6: worker lanes see the plan; pre-dispatch refusal matrix; scrub forbidden by contract

**Repo:** ray-manaloto/dotfiles · **Design:** T6 + Q4 + F12 · **Blocked by:** 9

## Parent

#1351

## What to build

Codex worker lanes (the sdlc-team dispatcher) are grounded in the same attested plan the orchestrator works
from, and are never blind-dispatched against a plan the hooks would refuse to inject. Both spawn sites already
pass no environment, so lanes inherit the session environment today; a verification contract forbids a planning
scrub from being "fixed" back in. A pre-dispatch check at the dispatch call resolves the plan as the shell
resolver would and applies the full matrix: no plan anywhere → dispatch; resolved and matching → dispatch;
resolved with a digest differing from its attestation (mismatch or unattested, in a v3 mode) → refuse naming the
attest task; ambiguous → refuse naming pin-or-close; rejected binding (plan id set, resolver empty) → refuse
naming the stale pin; resolved directory without a plan file → refuse. Planning disabled in the dispatcher's own
environment is recorded in the dispatch record and dispatch proceeds with a warning (Ray's Q4 ruling). Never
auto-attest at dispatch. The lane spec the task constructs carries the worker prohibition: never attest, never
edit the plan; write ledger rows under your own agent name. The advisory codex lane is untouched (its scrub and
its isolation contract's behaviour tokens stay until Phase 10); the twelve Claude wrapper agents are out of scope
(corrections comment, item 3).

## Acceptance criteria

- [ ] Dispatch seam with a fake spawn: every matrix row — attested dispatches; tampered and unattested do not
      spawn and the message names the attest task; ambiguous; rejected binding; missing plan file; none
      dispatches. Each refusal row asserts "no process launched".
- [ ] Inherited-disable arm: with the plugin's disable variable set in the dispatcher's environment, dispatch
      proceeds, the record carries the inherited marker, and a warning is printed; control: unset → no marker.
- [ ] Supervisor-to-worker boundary (host-only): the real supervisor path with a stand-in command that prints
      its environment shows the worker inherits the plan id when set and lacks the disable variable; the same
      probe reports the unset state as the control.
- [ ] Contract arm: adding a planning-scrub line to the dispatcher fails the new forbid contract; the advisory
      lane's isolation contract still passes with its behaviour tokens.
- [ ] The constructed lane prompt contains the never-attest/never-edit prohibition (string arm) and the typed
      dispatch record has the new field.

## Blocked by

- Ticket 9.

**Seam / prior art:** the dispatcher's existing "missing spec launches no process" and "missing codex launches
no process" arms; the advisory lane's real-child positive-plus-control environment test is the exact shape for
the supervisor→worker probe.

---

## Ticket 14 — K8: knowledge-base adoption — tracked mode floor, lifecycle skills call the shared verbs, no version literal, shared rule declared

**Repo:** ray-manaloto/knowledge-base · **Design:** T9 (adoption half) · **Blocked by:** 5, 8

## Parent

ray-manaloto/dotfiles#1351

## What to build

The knowledge-base runs the merged workflow with its policies preserved by name. A tracked root mode file sets
the autonomous floor (a new plan's attestation requirement becomes a reviewed project setting). The resume skill
stops hard-coding a plugin version and calls `plan status`; it keeps "report it; do not archive it" and its task
precedence (the user's task outranks the generated next ticket, which outranks the plan's next step). The
clear-prep skill keeps "archive only on an explicit clear-now and only when complete" and performs the archive
through `plan close` (which enforces exactly that); its archive reference becomes a pointer to the shared close.
The shared skill and rule copies from ticket 8 are installed and declared so the cross-repo rule-sync gate can
later see the rule here. Nothing about the eleven-day slug changes in this ticket.

## Acceptance criteria

- [ ] The mode file is tracked and holds the autonomous floor; a throwaway slug created here inherits the token
      (status shows the mode line).
- [ ] The resume skill contains no plugin version literal (grep with a known-present control term elsewhere)
      and its status step runs `plan status` and exits with the checkout's real state.
- [ ] The clear-prep skill's archive step is the shared close; a dry-run eval shows it refuses an incomplete
      plan and does not archive; a complete throwaway plan is archived.
- [ ] The knowledge-base's skill-parity check (ticket 8) and its lint gate are green; the rule file is present
      under the shared stem.
- [ ] `kb-setup plan status` in this checkout still resolves the eleven-day slug (unchanged, by design).

## Blocked by

- Ticket 5 (close verb), ticket 8 (shared bytes and parity verb).

**Seam / prior art:** the clear-prep archive reference's own "check-complete first, mkdir the archive" recipe;
skill evals in dry-run.

---

## Ticket 15 — D7: `/session-handoff` and `/session-resume` run status, classify mismatches by who edited, three-way compare

**Repo:** ray-manaloto/dotfiles · **Design:** T7 (lifecycle half) · **Blocked by:** 11, 12

## Parent

#1351

## What to build

Handoff: keep the pointer fence; add status; on a mismatch this session caused → attest, then re-check; on a
mismatch it did not cause → report a finding, do not attest (the one place tamper detection still pays); then a
ledger note bound to the resolved plan (ticket if live, else root), the pointer with both digests, and the
doctor. Checklist: every declared, resolving authority matches; at most one live slug; the completed ticket
closed. The owed list never contains an attest; the "attest is owed" paragraph and checkbox are removed.

Resume: status, then the three-way compare of file digest, attestation and committed pointer — all equal is
clean; file differs from attestation is "unattested edit after handoff" with the attest task as the first
(clickable) offer; attestation differs from pointer is "re-attested after the pointer was committed", a
disagreement to fix first. The plan line reads `root → <phase> [MATCH] | ticket <id> → <phase> [MATCH|TAMPERED]`.
A stale pin's first offer is "new terminal". Invocation policy stays here (not in the shared skill).

## Acceptance criteria

- [ ] Handoff-check on a handoff written by the new skill returns zero findings; a handoff carrying an
      "attest is owed" line is rejected by a new handoff-check rule (positive) while the pointer fence is
      untouched (control).
- [ ] The three-way compare has fixture arms: equal/equal → clean; file≠attest → the unattested-edit wording;
      attest≠pointer → the re-attested wording; each names its first offer.
- [ ] Skill evals in dry-run: the mismatch-this-session-caused branch attests; the not-caused branch does not
      and writes the finding.
- [ ] The skills mirror regenerates and its parity step is green; lint-docs green.

## Blocked by

- Ticket 11 (the tasks the text names), ticket 12 (the doctor the handoff runs).

**Seam / prior art:** the handoff-fence contract; the verify skill's handoff-check row (fixtures with a task
carrier and a fenced one); the resume skill's existing reconciliation table.

---

## Ticket 16 — D8: the rest of the instruction surface — rules, agents, persistence tokens, shared skill mirror, rule-sync widened

**Repo:** ray-manaloto/dotfiles · **Design:** T7 (instruction-surface half) + F6/F7 · **Blocked by:** 8, 11, 13, 14

## Parent

#1351

## What to build

No rule, agent or contract token contradicts the code. The shared skill and rule from ticket 8 are installed as
byte-identical copies and the parity check joins the lint gate; the cross-repo rule-sync declared set gains the
shared rule (after ticket 14 made the knowledge-base true — order is load-bearing). Rewritten in the same
change: the report-persistence rule's file-role table ("the resolved plan directory's findings and progress;
coordinator-attested plan"), the notepad-enforcement and artifact-conventions rules that still route findings to
the root findings file, the subagent-start contract tokens in hook-selfcheck that pin that table row, the
advisory-lane isolation contract's documentation token (updated together with the row it pins), the scribe
agent's "operator-attested" sentence, the verify and session-review skills' handoff-check rows. The generated
skills mirror is regenerated. The memory-index flip ("operator-only" → "model-runnable") is a coordinator step at
the next handoff, not part of this diff.

## Acceptance criteria

- [ ] Grep arms: no tracked rule, skill or agent under the Claude config says "operator-attested",
      "operator-only" or "root findings" about the plan (known-present control term in the same corpus).
- [ ] Hook-selfcheck passes with the new tokens; reverting the persistence-rule table row alone fails it.
- [ ] Rule-sync passes in BOTH repos (the knowledge-base checkout must be present; a SKIP is not a pass here).
- [ ] The shared-skill parity check passes; one byte changed in the local copy fails it naming the file.
- [ ] The codex-lane isolation contract passes with its behaviour tokens and the updated documentation token;
      removing the behaviour token still fails it (control that the contract still bites).
- [ ] Lint, lint-docs, hook-selfcheck, verify green; skills mirror parity green.

## Blocked by

- Ticket 8 (the bytes), ticket 11 (task names the text uses), ticket 13 (the sdlc-team lane-spec wording it
  documents), ticket 14 (rule-sync order).

**Seam / prior art:** hook-selfcheck's settings-wiring required-token table; the rule-sync gate's stem/lines
checks; the skills-mirror `--check`.

---

## Ticket 17 — D9: the plan migration — archive the program plan, install the roadmap, goal-history iteration, reconcile, attest, verify (closes #910)

**Repo:** ray-manaloto/dotfiles · **Design:** T8 + M-11/M-12 · **Blocked by:** 10, 11, 12, 13, 15, 16
**Executor:** the Claude orchestrator on a branch — NOT a codex lane. Three `AskUserQuestion` stops inside.

## Parent

#1351

## What to build

Seven verifiable outcomes, in order: (1) archive the old program plan and its attestation byte-for-byte under
the hidden archive, and move the leftover 2026-09-21 directory there; (2) enumerate every unchecked item and
still-open reference from the old plan into the tracked extract, each mapped to a roadmap line, an existing
issue, or dropped-with-reason — every drop is asked (stop 1); the two stale in-progress markers found by the
integrity review are resolved in the extract; (3) install the roadmap: at most 150 lines, upstream's autonomous
template shape with primary status markers, Phases 10 and 11 and the migration addendum condensed to decision
rows, exactly one phase in progress, no "next session" heading; (4) append the goal-history iteration — writer:
the coordinator, on the branch, before the first ticket init — whose goal text names the root roadmap plus the
attested ticket plan as task authority and attestation as orchestrator-run tamper detection; the wording is
asked (stop 2); (5) reconcile selection: no live slug, no sessions directory, pointer absent or retired,
environment binding unset; (6) write the pointer, attest the roadmap with the target printed as root, show;
(7) verify: status reports root MATCH at Phase 11 with exit 0 and no non-clean finding; the ledger-summary
heading equals the pointer heading; the doctor is clean; the next prompt injects a plan body. Outcome 7 is
#910's reproduction turned green; #910 closes with this ticket. Stop 3: if any outcome cannot be reached, ask
before forcing anything.

## Acceptance criteria

- [ ] Archive arm: the archived plan's digest equals the pre-migration digest recorded in the tracked pointer's
      last commit; the leftover directory is gone from the live planning tree and present under the archive.
- [ ] Extract arm: every unchecked item of the old plan appears in the extract with a mapping; a control count
      (unchecked items in the archived plan) equals the extract's row count; zero silent drops.
- [ ] Roadmap arm: line count ≤ 150; exactly one in-progress primary marker; the non-canonical warning does not
      fire; handoff-check (new grammar) passes on the next handoff.
- [ ] Goal-history arm: the append-only check against the branch baseline passes; the new iteration's changed
      requirement names the authority change.
- [ ] Outcome 7 recorded verbatim in the PR (status output, doctor output, the injected body's first line);
      #910 closed with the reference.
- [ ] Lint, pytest, verify, lint-docs, hook-selfcheck green; the branch ships via the normal PR path.

## Blocked by

- Tickets 10, 11, 12, 13, 15, 16 (readers must accept the new shape; the tasks, doctor and lane check must
  exist; the skills and rules must describe the world the migration creates).

**Seam / prior art:** the one-time live verification is recorded in the ticket, not automated (design of
record); the goal-history append-only session-review check is the existing gate for outcome 4.

---

## Ticket 18 — K9: close the eleven-day live slug through the shared close, after Ray confirms its round is done

**Repo:** ray-manaloto/knowledge-base · **Design:** T9 (slug half) · **Blocked by:** 5, 14, and Ray's confirmation
**Label:** `ready-for-human` until Ray answers; then `ready-for-agent`.

## Parent

ray-manaloto/dotfiles#1351

## What to build

The resolver stops offering a finished round as the live plan. The session asks Ray whether the 2026-09-12
session-review-round-dag round is done (recommended answer: yes if its completion check reports all phases
complete; if not, the question is whether to force with a reason or leave it live). On "yes", `plan close`
archives it under the hidden archive, records the ledger event, leaves the pointer untouched, and status
reports a retired pointer at exit 0 with no live slug. On "force", the reason is recorded. On "leave it", the
ticket closes as won't-do with the reason.

## Acceptance criteria

- [ ] The clarifying question was asked with a recommendation and both sides; the answer is quoted in the PR.
- [ ] After close: the directory is under the archive; status in the knowledge-base checkout shows no live slug,
      retired pointer, exit 0; the resume skill's status step reports the same (control: before close it named
      the slug).
- [ ] Nothing was force-closed without a recorded reason.

## Blocked by

- Ticket 5, ticket 14, and Ray's confirmation.

**Seam / prior art:** ticket 5's close arms; this is the first real-world run of the verb.

---

## Not tickets: upstream asks (T10) — drafts for Ray's review, NOT filed

Per the round-7 ruling these are drafted, not posted. Both go to the planning-with-files tracker only after Ray
approves the text. Neither blocks anything above.

**Draft A — "attest-plan: an explicit `--target root` flag".** Today the attester's target is whatever the
resolver returns, falling to the root plan only when no live plan resolves and no selector is set. A program
that keeps a short root roadmap plus one live ticket plan therefore cannot re-attest the roadmap while a ticket
is live without clearing selection first. Ask: a `--target root|<plan-id>` flag (default: current behaviour),
printing the chosen target before writing. Offer: a PR with the flag, a test, and a doc line in the attestation
page. Context to cite: the maintainer's statement that attestation is tamper detection, not approval (#150),
and the multi-agent guidance to re-attest at phase boundaries in the migration guide.

**Draft B — "A Claude Code / Codex analogue of the Pi adapter's `/plan-execute` approval gate".** The Pi adapter
has an explicit human-approval step before execution; Claude Code and Codex have none, so any project wanting a
human boundary re-implements it locally against the trust model (which is how this repo ended up with a deny
list upstream never carried). Ask: whether an approval gate for those adapters is on the roadmap, and what
shape the maintainer would accept (a Stop-gate mode? a command that requires an interactive confirmation?).
Offer: a design sketch and a willingness to implement behind a flag. Context to cite: #190/#193 (Pi
plan-execute), and this repo's experience that a local deny list blocks read-only looks at scripts.

---

## Step-4 questions the coordinator should put to Ray

1. **Granularity of the knowledge-base slices (tickets 2–8, seven KB tickets).** Recommended: keep seven — each
   is one verb group with its own host-only arms and lands green alone. Alternative: fold 6 (pointer) and 7
   (doctor-probe) into 3 and 2 respectively, giving five; PRO fewer PRs, CON two bigger reviews and ticket 9
   waits the same.
2. **One pin bump or two (ticket 9 vs 16).** Recommended: one bump in 9 covering tickets 2–7, and if ticket 8
   lands later, a second small bump inside 16. Alternative: hold 9 until 8 lands (fewer bumps, later start of
   all dotfiles work).
3. **Ticket 10 folds M-7 (handoff digest vs pointer).** Recommended: yes, it is the same reader. Alternative:
   its own ticket after 10.
4. **Ticket 17's executor.** The design says coordinator-executed with no operator step; the ticket therefore
   carries `ready-for-agent` but is NOT dispatchable to a codex lane. Confirm the label, or use
   `ready-for-human` to mark that Ray must be present for its three stops.
5. **Ticket 18's gating question** can be asked now (before the verb exists) to unblock it early. Recommended:
   ask at step 4.

---

## Implementer anchors (appendix — paths and lines for the implementing agent; NOT for the issue bodies)

All dotfiles anchors are on branch `docs/session-2026-09-23d-handoff` at `b7c59920`; knowledge-base anchors at
its current `main` checkout on this machine. pwf script anchors are *inherited* from spec v2 (installed
3.20.7 at `~/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7`).

### Ticket 1 (D1)
- Deny rules: `.claude/settings.json:31-41` (11 entries).
- Selfcheck: `python/src/dotfiles_setup/hook_selfcheck.py:756` `_ATTEST_DENY_BASES`, `:765` `check_plan_attest_deny`,
  `:811` registration `("plan-attest-deny", …)`; the SubagentStart contract token `:676` "`task_plan.md` is coordinator-only"
  (leave for ticket 16).
- Contract: `python/verification/suites.toml:1832` `workflow.plan-attest-operator-only` (block ≈1831-1866).
- Tests: `tests/test_plan_attest.py:19-22` imports; deny tests `:84`, `:90`, `:104`, `:121`; keep `:44-79` (resolver)
  and `:161-210` (separator/passthrough); module docstring `:1-10`.
- Wording: `.claude/CLAUDE.md:20-22`; `mise.toml:1002-1005` (`[tasks.plan-attest]` description);
  `python/src/dotfiles_setup/main.py:1544-1550` help text; `python/src/dotfiles_setup/plan_attest.py:1-10` docstring;
  `.claude/rules/mise-tasks-only.md` table row "sh $CLAUDE_PLUGIN_ROOT/scripts/attest-plan.sh (or /plan-attest) | nothing an agent may run".
- Control arm for the live test: `Read(~/.netrc)`/`Bash(*~/.netrc*)` denies in the same settings file (rule 8 of the secrets rule).
- Prior-art test shape: `tests/test_plan_attest.py:104` (`test_the_deny_check_notices_a_half_written_ban`) — invert it.

### Ticket 2 (K1)
- KB package: `python/src/kb_setup/` (flat modules; `cli.py:34` `def main(argv)`); console script `python/pyproject.toml:39-40`.
- Resolver to move: dotfiles `python/src/dotfiles_setup/plan_attest.py:140` `resolve_attest_script(home)` (+ tests `:44-79`).
- Host-only convention to copy: dotfiles `tests/conftest.py:26-37` (`CI == "true"` only).
- KB conftest today: `tests/conftest.py` real-git fixtures (`:86`, `:136`, `:151`, `:174`); no `host_only` marker.
- KB has no doctor/rule-sync baseline (`doctor.toml`, `rule-sync.toml` absent; `currency.toml` present) — the KB `[plan]`
  baseline is a NEW tracked file.
- KB live state: `.planning/.active_plan` = `2026-09-12-session-review-round-dag`; that dir holds `findings.md progress.md task_plan.md`.
- pwf scripts (installed): `resolve-plan-dir.sh` (linked-worktree/root counting `:345-347`, stale pointer `:367-368`, rejected binding `:363-366` — *inherited*),
  `attest-plan.sh:44-77` (*inherited*), `check-complete.sh:95-108`, `ledger-summary.sh:99-137` (*inherited*).

### Ticket 3 (K2)
- Phase rule sources (*inherited*): `check-complete.sh:95-97`, `ledger-summary.sh:117-137`; session isolation `resolve-plan-dir.sh:345-347`,
  `plan-doctor.sh:106`.
- Dotfiles readers this rule replaces: `python/src/dotfiles_setup/plan_pointer.py:19` (`NEXT SESSION` regex), `handoff_check.py:225-227,256`.

### Ticket 4 (K3)
- `init-session.sh` (*inherited*): slug mode `:226-230`, root branch `:481-485`, `:235`; attester failure at exit 0 `:244-254`; mode token `:170-182,202-206`;
  prints `PLAN_ID=` `:476-477`. `commands/pwf.md:7-12` (root files first).
- Separator repair to move: `plan_attest.py:86` `insert_passthrough_separator`; call site `main.py:3086-3089`; tests `tests/test_plan_attest.py:161-210`.
- Pin target: the worktree's `mise.local.toml` `[env] PLAN_ID` (gitignored per clone — `mise.local.toml.example`).

### Ticket 5 (K4)
- `ledger-append.sh:47-64` (root fallback), `set-active-plan.sh:303-321` (no `--clear`; "stale pointer" `:321`), `check-complete.sh` — *inherited*.
- KB clear-prep recipe being promoted: `.claude/skills/clear-prep/references/plan-archive.md:16-35`.
- Root ledger ignore gap: dotfiles `.gitignore:137-151` covers `/task_plan.md`, `/.planning/`, `/.plan-attestation`, not a root `ledger-*.jsonl` (ticket 10 adds it).

### Ticket 6 (K5)
- Current flat pointer: `docs/agents/plan-pointer.json` (`plan_sha256`, `active_phase`, `recorded_at`).
- Dotfiles pointer tests to port: `tests/test_plan_pointer.py:22,41,53`.

### Ticket 7 (K6)
- Lane B option B: `docs/research/kb/reports/agents/pwf-plan-doctor-hooks-2026-09-23.md:275-296,314-319` (*inherited* cite).
- Dispatcher: pwf `hooks/claude-hook.sh`; `inject-plan.sh:957-967` (`mode_has` reads root mode — *inherited*).
- Prior art for "canary must fail": `.claude/rules/probes-need-a-control-arm.md` rule 9 (#644).

### Ticket 8 (K7)
- Dotfiles mirror pattern: `hk.pkl:716-731` (`skills_mirror_parity`, `codex_lane_mirror`); `python/src/dotfiles_setup/skills_mirror.py`;
  suites `workflow.skills-mirror-wiring` (description at `suites.toml:1786`).
- KB skills dir: `.claude/skills/` (15 skills incl. `session-resume`, `clear-prep`); KB rules dir has 23 rules incl.
  `agent-report-persistence.md`, `notepad-enforcement.md`, `agent-artifact-conventions.md`.

### Ticket 9 (D2)
- Pin: `python/pyproject.toml:40` (`kb-setup @ git+…knowledge-base@e8fe42ae…`), comment block `:24-51`.
- Doctor baseline (dotfiles): `doctor.toml`; `python/src/dotfiles_setup/doctor.py` check functions `:485-1208`.
- Precedent for a pinned `kb-setup` verb behind a gate: `md_size_budget` → `kb-setup md-budget` (pyproject comment `:24`).

### Ticket 10 (D3)
- Tasks: `mise.toml:1002-1015` (`plan-attest`, `plan-pointer`, `handoff-check`).
- CLI: `main.py:99,134-138` imports; `:1544-1570` parsers; `:2817-2823` dispatch; `:3086-3089` parse_known_args note.
- Readers: `plan_pointer.py` (whole module deleted), `handoff_check.py:46-52` verdicts, `:217-260` plan checks, `:262` `check`, `:284-316` `main`
  (no-handoff rc 0 `:295-301`, "skipped" `:313-316`).
- Contracts: `suites.toml:1708` `workflow.plan-pointer-wiring` (≈1707-1730, five per-path tokens incl. the skill fence).
- Handoff fence to keep verbatim: `.claude/skills/session-handoff/SKILL.md:49` (`mise run plan-pointer`), `:53`.
- Tests: `tests/test_handoff_check.py:116,129,143,154,332,341`; `tests/test_plan_pointer.py` (retire with the module); `tests/test_plan_attest.py` (whatever ticket 1 left, moves to KB).
- M-7 source: `task_plan.md:698-699`.

### Ticket 11 (D4)
- Task pattern: `mise.toml:1002-1015`; canonical task map: `.claude/rules/mise-tasks-only.md` table.
- Call-site-token rationale: `suites.toml:2333` (apt-pins description).

### Ticket 12 (D5)
- Codex mirror: `.codex/hooks.json:35-45` (SessionStart `startup|resume`; the doctor command line is `:41` → `mise run tool-currency-check; … mise run doctor`).
- Doctor tests: `tests/test_doctor.py:278` (unreadable config fails rather than passes) — shape.

### Ticket 13 (D6)
- Spawn sites at HEAD: `python/src/dotfiles_setup/sdlc_team.py:814` (dispatch `subprocess.Popen`) and `:970` (supervisor) — spec v2 cited `:805/:961`
  from an earlier revision; line numbers moved, sites unchanged. Neither passes `env=`.
- Advisory lane (untouched): `codex_lane.py:136` `LANE_ENV_OVERRIDES = {"PLANNING_DISABLED": "1"}`, `:469`; contract `suites.toml:1869`
  `workflow.codex-lane-planning-isolation` (documentation token at `:1892` pins the persistence-rule table row — ticket 16).
- Prior art: `tests/test_sdlc_team.py:325,346` (no-process arms); `tests/test_codex_lane.py:592`
  (`test_the_spawned_lane_really_has_the_planning_hooks_disabled` — real child, positive+control).
- Lane prompt construction: `sdlc_team.py` (search `spec`/prompt assembly near the dispatch site); the "blind spot" paragraph in
  `.claude/rules/codex-sdlc-team.md`.
- Phase 10 supersession already recorded: `task_plan.md:415` ("SUPERSEDED 2026-09-23 by #1351").

### Ticket 14 (K8)
- Version literal: KB `.claude/skills/session-resume/SKILL.md:139` (`…/3.12.0`); policy lines `:157-165`.
- clear-prep: `.claude/skills/clear-prep/references/plan-archive.md:5,16-35`.
- KB `.gitignore:256-260` (`/.planning/` only — a root `.mode` will track); KB settings plugin block `.claude/settings.json:194,218-221`.
- KB mise.toml has 103 tasks; `kb-ship` at `:1496` (task style to copy).

### Ticket 15 (D7)
- Handoff skill: `.claude/skills/session-handoff/SKILL.md:49-53` (pointer fence), `:311` (handoff-check), `:326` ("attestation is owed"),
  `:336,340` (checklist rows to rewrite). Resume skill: `.claude/skills/session-resume/SKILL.md:60-64,107`.
- Verify skill row: `.claude/skills/verify/SKILL.md:18`; session-review: `.claude/skills/session-review/SKILL.md:88`.

### Ticket 16 (D8)
- Rules: `.claude/rules/notepad-enforcement.md:8`, `.claude/rules/agent-artifact-conventions.md:76`, `.claude/rules/agent-report-persistence.md` file-role table (§3).
- Agent: `.claude/agents/pwf-scribe.md:13,17` ("operator-attested").
- Selfcheck tokens: `hook_selfcheck.py:96` `_SETTINGS_WIRING`, `:541`, `:676`.
- Contract doc token: `suites.toml:1892` (inside `workflow.codex-lane-planning-isolation`).
- rule-sync: `rule-sync.toml` `[shared] rules = [...]` (order trap documented at its head, lines 19-22); KB must carry the stem first.

### Ticket 17 (D9)
- Old plan: `task_plan.md` (1,752 lines at HEAD; addendum `:587-712`; Current Phase `:714-722`; Phase 10 `:349-…`).
- Leftover dir: `.planning/2026-09-21-graphify-0-9-65-skill-refresh/` (only `task_plan.archived.md` — inherited claim from the briefs).
- Goal history: `docs/agents/goal-history.md` last iteration `dotfiles-goal-20260923-033` at `:1581`; rule `.claude/rules/goal-history.md`.
- Tracked pointer: `docs/agents/plan-pointer.json`; extract target: `docs/agents/plan-archive-2026-09-23.md` (new).
- M-11/M-12 source: `task_plan.md:702-703`; #910 body: "PLAN TAMPERED fires every prompt…".

### Ticket 18 (K9)
- Slug: KB `.planning/2026-09-12-session-review-round-dag/`; pointer `.planning/.active_plan`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #1351 body + corrections comment; `task_plan.md`
  addendum/Current Phase/Phase 10; `.claude/settings.json`, `mise.toml`, `main.py`, `hook_selfcheck.py`, `suites.toml`,
  `plan_attest.py`, `plan_pointer.py`, `handoff_check.py`, `sdlc_team.py`, `codex_lane.py`, `doctor.py`, `hk.pkl`,
  `rule-sync.toml`, `.gitignore`, `.codex/hooks.json`, the four test modules, the handoff/resume/verify/session-review
  skills, `pwf-scribe.md`, three rules, `docs/agents/*`, `docs/issue-tracker.md`, `docs/triage-labels.md`, `CONTEXT.md`,
  and the three input reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `python/src/kb_setup/` layout,
  `python/pyproject.toml`, `tests/conftest.py`, `.planning/`, `.gitignore`, `.claude/settings.json`, `mise.toml`,
  `.claude/skills/session-resume/SKILL.md`, `.claude/skills/clear-prep/references/plan-archive.md`, `.claude/rules/`.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed 3.20.7 `scripts/`
  listing read directly; script line anchors inherited from spec v2 (`init-session.sh`, `attest-plan.sh`,
  `resolve-plan-dir.sh`, `ledger-append.sh`, `set-active-plan.sh`, `check-complete.sh`, `ledger-summary.sh`,
  `inject-plan.sh`, `plan-doctor.sh`, `commands/pwf.md`); tracker #150/#190/#193 via the upstream review report.
- [mattpocock/mattpocock-skills](https://github.com/mattpocock/mattpocock-skills) — `to-tickets/SKILL.md` 1.2.3 (process + issue template).
