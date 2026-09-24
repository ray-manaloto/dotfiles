# Session-integrity review S4: vague or misinterpretable docs and plans, DELTA run (2026-09-23, session `a6750a24`)

Status: COMPLETE. This was a read-only lane, and this file was its only write. Brief:
`session-2026-09-23d-agent-briefs.md` § "Briefs S1-S4" (S4). It follows Brief P's method on the delta scope.

**Scope.** I read the following surfaces the way a fresh session or a codex lane would:
- the delta commits `5e258baf..48a1ee12` (`86324c6a`, `b7c59920`, `48a1ee12`), which touched 17 files;
- the 12 `.claude/agents/codex-{sol,astra}-*.md` wrappers in the current tree;
- the `python/verification/suites.toml` contract `workflow.codex-lane-planning-isolation`;
- `docs/agents/plan-pointer.json`;
- `task_plan.md` Phase 11 (heading, addendum `:587-712`, Current Phase `:714-725`) and the Phase 10 lines the
  delta newly references;
- `docs/agents/goal-history.md` iteration 033;
- all 18 published issue bodies (dotfiles #1352-#1360, knowledge-base #802-#810), fetched live, and the #1351
  corrections comment;
- `.agent/plans/session-2026-09-23d.md`.

I also re-checked every Brief P finding (P1-P14) against the tree.

Verbatim reports under `docs/research/kb/reports/agents/` are records (`agent-artifact-conventions.md` rule 8).
That includes the new `codex-sol-advisor-zsh-echo-quoting.md` and the tickets draft body. I propose no rewrites
of them.

**State probes, each run with a control arm:**
- **Plan hash.** `shasum -a 256 task_plan.md` = `4a077b45…`, which equals `plan-pointer.json` `plan_sha256`. The
  file is unchanged since `48a1ee12`.
- **Codex resolution.**
  - `mise exec -- which -a codex` gives `~/.local/share/mise/shims/codex` and then `~/.local/bin/codex`.
    `mise exec -- codex --version` gives `codex-cli 0.156.1`.
  - Bare `which -a codex` in this lane's shell puts `…/installs/npm-openai-codex/0.154.0/bin/codex` first. Bare
    `codex --version` gives `codex-cli 0.154.0`.
  - Two routes to the same fact disagree. The cause is known: this session's PATH was captured before
    `disable_tools`.
- **Branch.** `git ls-remote --heads origin docs/session-2026-09-23d-handoff` is empty, and
  `gh pr list --head …` returns `[]`. Control: the same `gh pr list` shape returns #1350 for the 23c branch. So
  this branch is NOT pushed or shipped.
- **Issue bodies.** All 18 are OPEN with the expected labels. #1360 and KB#810 are `ready-for-human`; the rest are
  `ready-for-agent`.

## Brief P findings: fixed-in-tree check

| P | Status | Evidence |
|---|---|---|
| P1 printed literals | **FIXED** | `echo "lane files` appears once in each of the 12 wrappers, e.g. `codex-sol-advisor.md:101`. Control: `git show 5e258baf^`-era text had none in the 5 sol advisory files (Brief P probe). |
| P2 Current Phase stale NEXT | **FIXED** in Current Phase `:714-725`, but the addendum `:672-673` still carries the stale NEXT (see S4-3) | — |
| P3 goal-history iteration + authority wording | **FIXED**: iteration 033 exists (`goal-history.md:1579`). The round-5 contradiction is neutralised by the read-first block (`task_plan.md:589`), though `:642` still says "032 CHANGES the goal text" inline | 033 is itself now stale (S4-10) |
| P4 superseded rulings unmarked | **FIXED** via the read-first block `:589`. Inline markers at `:595`, `:608`, `:620-623` were not added, which is acceptable because the block names each one | — |
| P5 Phase 10 pwf ruling | **FIXED**: `:415` SUPERSEDED marker | residual ambiguity, see S4-13 |
| P6 `ai-cli-invocation.md` self-contradictions | **FIXED** (`:9-12`, `:30-41`, `:43` heading) | new gap, see S4-5 |
| P7 pr-loop `--watch` | **FIXED** (`pr-loop-ship-fix-land.md:65-66`) | — |
| P8 pr-loop re-entry and rounds | **FIXED** (`:70-73`) | — |
| P9 #1351 undefined terms and wrapper scope | **PARTIAL**: the #1351 corrections comment (2026-09-24T04:03Z) defines 4 terms and puts the 12 wrappers out of scope. "Initializer", "selector", "ledger appender", "completion check", "root mode file", "shared package" and "hidden archive" are glossed only via the draft's per-ticket anchors appendix (`pwf-migration-tickets-draft-2026-09-23.md:918-1057`), which each ticket footer cites | new overloaded term, see S4-7 |
| P10 handoff file stale | **FIXED then RECURRED**: regenerated at 23:27, but it predates `86324c6a`'s plan edit and `48a1ee12` | S4-9 |
| P11 "43% on this definition" | **NOT FIXED, NOT RECORDED** — still in 10 wrappers (e.g. `codex-sol-advisor.md:119-121`) | S4-12 |
| P12 120 s vs 600 s, and 2400 vs 1800 | **NOT FIXED, NOT RECORDED** — `codex-sol-advisor.md:114-115`, `codex-sol-implementer.md:161`, `:154-155`/`:206` (1800) | S4-12 |
| P13 three line counts | **NOT FIXED, NOT RECORDED** — `task_plan.md:592` "1,600-line", `:607` "1,640-line"; `wc -l` = 1755 | S4-12 |
| P14 pr-loop BRANCH_CLOSED, log_path | **FIXED** (`:52`, `:66-67`, `:79-80`, `:106`) | — |

"Not recorded" means `grep -nE '43%|P1[1-3]' task_plan.md` finds nothing, and the fix commit `5e258baf` body names
only P1 and O. Control: the same grep finds `1,6xx-line` at `:592` and `:607`. So the probe reads the file; the
three LOW items were dropped silently. S1 (dismissed errors) should count them.

## Findings

Severity ranks how likely a fresh session or codex lane is to act wrongly on the text.

### S4-1 — HIGH — three ticket-numbering schemes, and the plan, pointer, handoff and goal-history speak the one that no longer maps to issues

- **Claim.** The delta published tickets labelled **D1-D9 / K1-K9** in their titles. Their bodies and blocked-by
  lines use **draft ordinals "Ticket 1-18"**. Every authored plan surface still names the design's **T1-T10**.
  - The mapping is not 1:1:
    - T1 = D1 #1352;
    - T2 = K1-K5 (#802-#806) + D2 #1353;
    - T3 = D3 #1354 (+ K5's pointer half);
    - T4 = D4 #1355;
    - T5 = K6 #807 + D5 #1356;
    - T6 = D6 #1357;
    - T7 = K7 #808 + D7 #1358 + D8 #1359;
    - **T8 = D9 #1360, not D8 #1359**;
    - T9 = K8 #809 + K9 #810;
    - T10 = no ticket.
  - **"D4" now names two things**: the retired 2026-09-02 attestation deny ("dotfiles#1352 (D1 retire D4)",
    `task_plan.md:718`) and ticket **#1355 "pwf migration D4: the four remaining thin mise tasks"**.
- **Why it matters.** "#1351 T8" in the plan reads naturally as #1359 (D8, the instruction surface) when it means
  #1360 (D9, the plan migration). "Retire D4" reads as "close #1355". The plan-pointer's `active_phase` string
  embeds "until #1351 T3", so every `/session-resume` shows it.
- **Evidence.** T-references:
  - `task_plan.md`: `:506` (the heading, so `plan-pointer.json` `active_phase`), `:589`, `:653-654`, `:678`,
    `:699`, `:703`, `:724`;
  - `.agent/plans/session-2026-09-23d.md`: `:17`, `:52`, `:53`;
  - `goal-history.md` 033: the Changed-requirement line ("#1351 T8") and the mermaid "T1..T10".

  The ordinal-to-label map exists only in the draft appendix headings (`pwf-migration-tickets-draft-2026-09-23.md:924`
  "Ticket 1 (D1)" … `:1039` "Ticket 18 (K9)"), and the ordinal-to-T map only in each draft ticket's
  "**Design:**" line (e.g. `:213` "Ticket 17 — D9 … **Design:** T8").
- **Control.** The draft's own "Design:" lines are internally consistent: `grep '^\*\*Repo'` shows all 18, and each
  names its T. So the ambiguity is in the consumers, not in the draft.
- **Disposition: FIX-NOW** (coordinator; the plan is coordinator-only).

  (a) Insert after `task_plan.md:673`:

  > - **Ticket map for #1351 (published 2026-09-23; use ISSUE NUMBERS from here on — "T n" below and in older text
  >   is the design numbering, "Ticket n of 18" is the draft ordinal):** T1 → #1352 (D1) · T2 → KB#802-#806
  >   (K1-K5) + #1353 (D2) · T3 → #1354 (D3) (+ KB#806's pointer half) · T4 → #1355 (D4) · T5 → KB#807 (K6) +
  >   #1356 (D5) · T6 → #1357 (D6) · T7 → KB#808 (K7) + #1358 (D7) + #1359 (D8) · **T8 → #1360 (D9)** · T9 → KB#809
  >   (K8) + KB#810 (K9) · T10 → no ticket (upstream drafts for Ray). "The D4 deny" always means the retired
  >   2026-09-02 attestation deny, never ticket #1355.

  (b) Replace the T-references with issue numbers:
  - `:699` "fold into #1351 T3" → "in #1354 (D3)";
  - `:703` "handled by #1351 T8" → "handled by #1360 (D9)";
  - `:678` "deferred to #1351 T8" → "deferred to #1360 (D9)";
  - `:724` "#1351's tickets first (T1 first)" → "#1351's tickets first (frontier #1352 and KB#802)".

  (c) At the next plan edit, change the heading's "until #1351 T3" to "until #1354 (D3)". Then re-run
  `mise run plan-pointer`: the heading is the pointer's `active_phase`, and renaming it without the pointer fails
  `plan-pointer` at rc=1 (handoff trap `:53`).

  (d) Post the same table as a comment on #1351, so the 18 issues' "Ticket n of 18 from spec #1351" footers
  resolve (see S4-8).

### S4-2 — HIGH — #1352's (D1) acceptance grep misses the one file it most needs to catch, and as worded it requires rewriting verbatim records

- **Claim.** The AC reads: "No tracked file in the repo still says 'operator-only', 'OPERATOR ONLY' or 'HUMAN
  boundary' about attestation." It has two defects:
  1. **Blind spot.** `.claude/CLAUDE.md:20` says "**Attestation is OPERATOR-ONLY**". The hyphenated uppercase
     spelling matches none of the three literals, so the check passes while the most-loaded instruction file
     still says it.
  2. **Unsatisfiable scope.** 37 tracked files match. 33 are records under `docs/research/**` or
     `docs/agents/goal-history.md`, which rule 8 and the goal-history append-only gate forbid rewriting. An
     implementer either vandalises records or cannot pass.
- **Evidence and control.**
  - `git grep -lE 'operator-only|OPERATOR ONLY|HUMAN boundary' -- ':!docs/research' ':!docs/agents/goal-history.md'`
    returns `mise-tasks-only.md`, `mise.toml`, `main.py` and `suites.toml`. It does **not** return
    `.claude/CLAUDE.md`.
  - Adding `OPERATOR-ONLY` to the pattern returns `.claude/CLAUDE.md:20`. So the first grep discriminates, and
    its miss is the literal set, not the file.
  - `git grep -lE '…' | wc -l` = 37.
- **Disposition: FIX-NOW** (comment on #1352; an append leaves the Ray-approved body intact). Text:

  > **AC clarification (session-integrity review S4, 2026-09-23).** Read the "No tracked file … still says" item
  > as: `git grep -niE 'operator[- ]only|human boundary' -- .claude AGENTS.md mise.toml python/src
  > python/verification ':!.claude/agent-memory*'` returns no line about attestation. The match is
  > case-insensitive and covers the hyphen, so it catches `.claude/CLAUDE.md:20` "OPERATOR-ONLY". Verbatim records
  > (`docs/research/**`, `docs/agents/goal-history.md`, `docs/rules-evidence/**`) are excluded and must not be
  > edited (agent-artifact-conventions rule 8). Control arm: the same command before the change lists
  > `.claude/CLAUDE.md`, `mise.toml`, `python/src/dotfiles_setup/main.py` and `.claude/rules/mise-tasks-only.md`.

### S4-3 — MEDIUM — the Phase 11 heading (and so the pointer) and the addendum's NEXT line contradict the Current Phase order

- **Claim.** Three texts give different orders:
  - the heading `task_plan.md:506`, recorded verbatim in `plan-pointer.json` `active_phase`: "pwf … (#1351)
    FIRST, then codex class fix, pr-loop, …". It omits the **codex step-2a remainder**, which round 7 (`:681`)
    and Current Phase item 2 (`:721`) put before the class fix;
  - the addendum `:672-673`: "NEXT: Ray invokes `/mattpocock-skills:to-tickets` on #1351 …, then `/to-spec` +
    `/to-tickets` on pr-loop". `/to-tickets` is DONE (`:717`), and pr-loop is now third, not next;
  - `:661-662`: "Stopgap SHIPPED on the branch". The branch is not pushed and has no PR (probe above). In this
    repo "ship" means `mise run ship`.
- **Control.** Current Phase `:716-725` is internally consistent with round 7 `:680-681`.
- **Disposition: FIX-NOW** (coordinator).
  - `:672-673`: replace "NEXT: Ray invokes … on pr-loop (Fable)." with "`/to-tickets` DONE 2026-09-23 (18
    tickets, map above); the order from here is Current Phase."
  - `:661`: "Stopgap SHIPPED on the branch as `3f2caac6`" → "Stopgap COMMITTED on the unshipped branch
    `docs/session-2026-09-23d-handoff` as `3f2caac6` + `5e258baf` + `86324c6a` (`mise exec -- codex`)".
  - Heading `:506` at the next plan edit (with S4-1c): "… pwf current-workflow migration (#1351) FIRST, then codex
    step-2a remainder, codex class fix, pr-loop, fix-first `/session-resume`, verified `/session-handoff`, binding
    python standards". Then re-run `mise run plan-pointer`.

### S4-4 — MEDIUM — "Phase 10 step 2a" / "step 2b" are used in four files but defined nowhere, and "2b" collides with an archive heading

- **Claim.** Phase 10's Order has one step 2 (`task_plan.md:493`: "codex-native + gpt-6-sol PR, dotfiles (BASE
  REBUILD) → then KB mirror PR"). The delta's surfaces split it without defining the split:
  - "codex step-2a remainder": `:681`, `:684`, `:721`;
  - "Phase 10 step 2b": `:188`, `:677`, `mise.toml:168`, handoff `:18`.

  The archive has a heading "### Phase 2b: 2026-09-10 grilling outcomes" (`:753`), which a grep for "2b" lands on
  first-in-context.
- **Control.** `grep -n '2a\b\|2b\b' task_plan.md` finds the uses above and `:753`. It finds no line that defines
  2a or 2b.
- **Disposition: FIX-NOW** (coordinator). Replace `:493` with:

  > 2. codex-native + gpt-6-sol, split 2026-09-23 (round 7): **2a (host)** — DONE in part: host runs native 0.156.x
  >    via root `mise.toml` `disable_tools`; the remainder is the addendum bullet "Codex step-2a remainder (host)".
  >    **2b (image + CI, BASE REBUILD)** — native `install.sh --release <recorded>` in the image, drop the
  >    `shared.toml` npm pin and `ci.yml` `MISE_DISABLE_TOOLS: ""`, then the KB mirror PR. (Not the archived
  >    "Phase 2b" at the bottom of this file.)

### S4-5 — MEDIUM — why the wrappers say `mise exec -- codex` is recorded only in a commit body, and the bare-`codex` instructions beside it hit a different binary

- **Claim.** `86324c6a` changed every launch line to `PLANNING_DISABLED=1 mise exec -- codex exec` because bare
  `codex` in a pre-change session resolves npm 0.154.0. None of the 12 wrappers, and not
  `ai-cli-invocation.md`, says:
  - why `mise exec` is there;
  - that on the host it now resolves the **native** install, by falling through the codex shim past the disabled
    npm pin (`mise.toml:165-170`);
  - that in the devcontainer, where root `mise.toml` is ignored, it still resolves npm 0.154.0.

  Meanwhile the same files tell the lane to use bare `codex`:
  - "Re-probe `codex exec --help`": `codex-sol-advisor.md:73`, `-adversarial-critic.md:75`,
    `-claude-code-expert.md:79`, `-staleness-auditor.md:51`, `-operator.md:133`, `-implementer.md:194`;
  - the implementer preflight "`command -v codex` must resolve" (`codex-sol-implementer.md:119`).

  In a pre-change shell those check 0.154.0 while the launch runs 0.156.1. And `ai-cli-invocation.md:7` "Use the
  pinned CLI through mise" is false for host codex: it is unpinned there.
- **Evidence.** The probe pair in the preamble: `mise exec` → 0.156.1, bare → 0.154.0.
  `codex-sol-advisor-zsh-echo-quoting.md` "What could not be verified" lists exactly this as unprobed.
- **Why it matters.** A later tidy-up that "simplifies" `mise exec -- codex exec` back to `codex exec` looks
  harmless and reintroduces M-6. A lane that re-probes flags reads 0.154.0 help for a 0.156.1 run.
- **Disposition: FIX-NOW** (sol files, then `mise run codex-lane-mirror`; plus the rule).
  - In each of the 6 sol wrappers, change "Re-probe `codex exec --help`" to "Re-probe `mise exec -- codex exec
    --help`". In the implementer, change "`command -v codex` must resolve" to "`mise exec -- codex --version`
    must succeed (the same resolution the launch uses)".
  - Add one sentence after each launch block: "`mise exec --` is load-bearing: it resolves codex from the
    CURRENT config (host: native install, npm pin disabled in root `mise.toml`; devcontainer: npm pin). A bare
    `codex` resolves this shell's captured PATH, which in a session started before 2026-09-23 23:00 is npm
    0.154.0 (`86324c6a`)."
  - `ai-cli-invocation.md:7`: "Use the pinned CLI through mise …" → "Invoke AI CLIs through `mise exec --` and
    re-probe their help the same way before copying flags. Host codex is the native install (npm pin disabled
    in root `mise.toml`, 2026-09-23); `mise exec -- codex` reaches it through the shim, and a bare `codex` in an
    older shell may not."

  Optional arm: a `require_tokens` entry binding "mise exec -- codex exec --help" in the sol wrappers.

### S4-6 — MEDIUM — the re-bound isolation contract says "each" wrapper, but the one write-capable sol wrapper is bound by nothing

- **Claim.** The `workflow.codex-lane-planning-isolation` description says the `PLANNING_DISABLED=1` prefix is
  asserted "on the hand-dispatched invocation in each `.claude/agents/codex-*.md`". Its `paths`/`per_path_tokens`
  bind only the five non-implementer sol wrappers (`suites.toml` `paths` list). The astra six are covered
  indirectly by the mirror `--check` (`hk.pkl:729`). **`codex-sol-implementer.md`, the `danger-full-access`
  lane, is bound by no contract or test.** Deleting its `PLANNING_DISABLED=1` passes verify.
- **Control.** `grep -rln PLANNING_DISABLED tests python/src` finds `test_codex_lane.py` and `codex_lane.py`, so
  the probe sees bindings where they exist. `grep` for `codex-sol-implementer` plus planning/`mise exec` in
  `suites.toml` and `tests/` returns nothing.
- **Disposition: FIX-NOW.** Add `".claude/agents/codex-sol-implementer.md"` to `paths` with per-path token
  `"PLANNING_DISABLED=1 mise exec -- codex exec"`. In the description, replace "in each
  `.claude/agents/codex-*.md`" with "in each sol wrapper (six, bound here per path; the astra six are generated
  and held byte-true by `codex-lane-mirror --check`)". Mutation arm: delete the prefix from the implementer, and
  verify must fail.

  Note for S3: this is a coverage bug as much as a doc defect.

### S4-7 — MEDIUM — "pointer" means two different files across the 18 issue bodies

- **Claim.** Two artifacts share the word:
  - **upstream's active-plan pointer** (`.planning/.active_plan`, a hint close never writes);
  - **the tracked two-authority pointer** (dotfiles `docs/agents/plan-pointer.json`; KB declares none, K1 #802).

  Bodies mostly say bare "pointer". Counts of bare "a/the/retired/dangling/stale pointer": KB#803 5, KB#806 4,
  #1358 4, KB#810 3, #1354 2, #1360 2, KB#805 2, KB#809 1. Only KB#804 and KB#805 once say "active-plan pointer".
  KB#803's informational states ("a pointer naming an archived id, a pointer naming nothing") and KB#810's "status
  reports a retired pointer" must mean the active-plan pointer, because KB has no tracked pointer. In dotfiles
  either reading parses.
- **Evidence.** The per-body count table above. The #1351 body distinguishes the two ("shared active-plan
  pointer" `:53`, `:124`, `:261`, `:522` vs "Tracked pointer" `:329`) but defines neither term in its glossary
  comment.
- **Disposition: FIX-NOW.** Append to the #1351 corrections comment, or post a new comment:

  > **Glossary addendum (S4):** *active-plan pointer* = upstream's `.planning/.active_plan` (a hint; `plan close`
  > never writes it); the status states "retired pointer" / "dangling pointer" / "a pointer naming an archived id"
  > refer to THIS file. *Tracked pointer* = the two-authority pointer written by `plan pointer`
  > (dotfiles `docs/agents/plan-pointer.json`; the knowledge-base profile declares none). In #1354, #1358, #1360
  > and KB#806, bare "pointer" means the tracked pointer; in KB#803, KB#805 and KB#810 it means the active-plan
  > pointer.

### S4-8 — MEDIUM — bare "ticket n" ordinals in the bodies' prose collide with the title labels, and "Ray's Q n" collides with Phase 11's Q-numbers

- **Claim, ordinals.** Blocked-by lines pair ordinals with issue numbers, but the "What to build" prose does not:
  - #1353 `:8` "tickets 2–7";
  - #1355 `:10` "ticket 10";
  - #1356 `:8` "ticket 7";
  - #1359 `:7`, `:9` "ticket 8", "ticket 14";
  - KB#802 `:35`; KB#803 `:18`; KB#805 `:23`, `:37`; KB#806 `:11`; KB#807 `:11`, `:22`; KB#808 `:8`, `:21`;
    KB#809 `:13`, `:24`;
  - KB#804 `:34` "ticket 7/12".

  In #1359 (titled **D8**), "the shared skill and rule from ticket 8" means KB#808 (K7), and a reader resolves
  "8" to the issue they are reading.
- **Claim, Q-numbers.** "Ray's Q2/Q4/Q5/Q1/Q3 ruling" (#1354 `:9`, #1357 `:15`, #1353 `:10`, KB#806 `:11`,
  KB#808 `:10`) means #1351's design questions. Phase 11 Rulings use Q1-Q22 for other decisions: `task_plan.md:566`
  "Live probes live in `session-state` (Q5)", `:558-560` (Q2).
- **Evidence.** `grep -noE '[Tt]ickets? [0-9]+…'` over the 18 fetched bodies, excluding the "of 18" footers.
- **Disposition: FIX-NOW.** One #1351 comment carries the S4-1 table with a third column (draft ordinal → issue),
  plus: "In the ticket bodies, 'ticket n' is the draft ordinal and 'Ray's Qn' is #1351 design question n (see
  its Design questions section), not a Phase 11 Q-ruling." No body edits are needed. If bodies are edited later,
  assert `count(anchor)==1` first (memory `feedback_issue_body_edit_needs_anchor_assert`).

### S4-9 — MEDIUM — the handoff file is stale against the delta (P10 recurred)

- **Claim.** `.agent/plans/session-2026-09-23d.md` has mtime 23:27, which predates the plan edit in `86324c6a` or
  later and `48a1ee12`. Its stale lines:
  - `:5` and `:17`: plan sha `5ab1a140…`. The file and pointer are `4a077b45…`;
  - `:14`: HEAD `b7c59920`, while HEAD is `48a1ee12`. Its commit list is also out of order;
  - `:25`: "What shipped (on the branch)". Nothing is shipped;
  - `:30` and the whole file: no mention of the 18 published tickets;
  - `:34`: "(A-Q)". The briefs now run A-S4;
  - `:37` omits the tickets draft, `codex-sol-advisor-zsh-echo-quoting.md` and the four `session-audit-delta-*`
    reports;
  - `:17`, `:52`, `:53` use T-numbers (S4-1).
- **Control.** Its `:18` codex row and `:46` M-6 row do reflect `86324c6a`. So the file was partly updated, not
  untouched.
- **Disposition: FIX-NOW** (coordinator; `/session-handoff` regenerates it).
  - `:4-5` and `:17` → `4a077b45de2f08ac4628b488c30855feba67fc6c403c367487cd226c1ee5f534`.
  - `:14` → "`docs/session-2026-09-23d-handoff`, HEAD `48a1ee12`: `875dfe26`, `7feb4a29`, `b5af8ecf`, `3f2caac6`,
    `762396bc`, `5e258baf`, `86324c6a`, `b7c59920`, `48a1ee12`. NOT pushed, no PR; `mise run ship` when Ray asks."
  - `:23` heading → "## What landed on the branch (unshipped)".
  - Add a bullet: "`/to-tickets` #1351 DONE: dotfiles #1352-#1360 (D1-D9), knowledge-base #802-#810 (K1-K9);
    frontier #1352 + KB#802; map in `task_plan.md` Phase 11 addendum."
  - `:34` "(A-Q)" → "(A-R, S1-S4)". Add to `:35-37`: `pwf-migration-tickets-draft`,
    `session-audit-delta-{dismissed-errors,missing-requests,codex-cold-review,vagueness}`.
  - `:17` "retired by #1351 T1" → "retired by #1352 (D1)". `:52` "Retired by #1351 T1" → "Retired by #1352
    (D1)". `:53` "until #1351 T3" → "until #1354 (D3)".

### S4-10 — MEDIUM — goal-history 033's disposition is stale, and the delta's milestone has no iteration

- **Claim.** 033 (`goal-history.md:1579-1597`) says "stopgap `DELIVERED` (unverified live); `/to-tickets` on
  #1351 not started", and its mermaid starts at "/to-tickets #1351". The delta verified the stopgap live (M-6,
  `86324c6a`) and published 18 tickets (`48a1ee12`). That is a "major milestone", and this is a handoff, so
  `.claude/rules/goal-history.md` requires an appended iteration. None exists: `git log 5e258baf..48a1ee12 --
  docs/agents/goal-history.md` is empty. Control: the same `git log` over `219e83cc..` shows `5e258baf` and
  `7feb4a29`.
- **Disposition: FIX-NOW** (coordinator, append-only):

  ```markdown
  ## 2026-09-23 — #1351 ticketed (18 tickets); codex wrappers verified live on native 0.156.1

  - **Iteration ID:** `dotfiles-goal-20260923-034`
  - **Prior goal digest:** `sha256:711f7e97ef6be6f6f54b8386dd098840055b0ddf4b06259ed26635fc51a8518a`
  - **Current goal digest:** `sha256:711f7e97ef6be6f6f54b8386dd098840055b0ddf4b06259ed26635fc51a8518a`
  - **Changed requirement:** None to the goal text (still deferred to #1360, D9 = design T8). `/to-tickets` on
    #1351 DONE: dotfiles #1352-#1360 (D1-D9) and knowledge-base #802-#810 (K1-K9), native blocked_by edges; #1360
    and KB#810 `ready-for-human`. Topology: the 12 codex wrappers launch `PLANNING_DISABLED=1 mise exec -- codex
    exec` (was bare `codex exec`, which resolved a stale npm 0.154.0 from a pre-change PATH).
  - **Reason:** Ray approved the Fable breakdown and its four to-tickets rulings; `/verify` run 1 showed the
    wrapper ran `OpenAI Codex v0.154.0`.
  - **Evidence:** `86324c6a` (two live `codex-sol-advisor` runs, rc=0, 1 slice each; run 2 `OpenAI Codex
    v0.156.1`; gates pytest/lint/verify 165/lint-docs/token-audit rc=0), `48a1ee12`,
    `pwf-migration-tickets-draft-2026-09-23.md`, `session-audit-delta-*-2026-09-23.md`.
  - **Affected tickets:** #1351, #1352-#1360, KB #802-#810, #910 (closes with #1360).
  - **Disposition:** `DELIVERED` (tickets published; stopgap verified live); branch unshipped;
    implementation not started.
  - **Topology and ownership:** One writer, the Claude architect session. Delegates: Fable ticket drafter (R),
    two live `codex-sol-advisor` lanes (M-6), read-only delta integrity lanes S1-S4.

  ### Current goal

  > <033's Current goal paragraph, verbatim; digest unchanged>

  ### Current workflow

  ```mermaid
  flowchart LR
      A["codex step-2a remainder: /grilling -> /to-spec -> /to-tickets"] --> B["codex class fix: /to-spec -> /to-tickets"]
      B --> C["pr-loop: /to-spec -> /to-tickets"] --> D["/implement #1352 + KB#802 frontier ... #1360"]
      D --> E["#1327 + rest of Phase 11"] --> F["Phase 10 step 0 (#1310)"]
  ```
  ```

### S4-11 — MEDIUM (outside the listed scope; coordinator-owned) — the MEMORY.md "START HERE" pointer names a finished step, and its target file describes another session

- **Claim.** `MEMORY.md:18` says "START HERE: /to-tickets #1351 (Fable)", which is done. The linked
  `project_session_2026-09-23.md` frontmatter `description` reads "… next = /implement starting KB#793" (origin
  session `f643887b`), which is two orderings old. A fresh session reads MEMORY.md before `task_plan.md`.
- **Disposition: FIX-NOW** at this handoff (auto-memory is the handoff skill's surface, not a user file). Point
  `:18` at a new `project_session_2026-09-23d.md` whose description is "#1351 ticketed (#1352-#1360, KB#802-#810);
  next = codex step-2a remainder /grilling (task_plan Current Phase)". Mind the 25 KB byte budget (handoff trap
  `:59`).

### S4-12 — LOW — P11, P12 and P13 were silently dropped; two small implementer inconsistencies are added

- **Claim.**
  - P11: "43% of lanes on this definition's old haiku wrapper" is still in the 10 non-implementer wrappers.
  - P12: "the harness moves a foreground call to the background at 120 s" (10 wrappers) vs "caps a foreground
    Bash call at 600 s" (implementer `:161`); `TIMEOUT` 2400 vs 1800 (`:154-155`, `:206`), with no reason stated.
  - P13: "1,600-line" at `:592` and "1,640-line" at `:607`; the file is 1,755 lines.
  - New: the implementer prints three literals (`:149`, `$PROMPT $OUT $LOG`) but tells the lane to re-assign
    four, including `LANE_ID` (`:156`). It also says the budget runs from "`$PROMPT`'s mtime (written at
    launch)" (`:200`), but `$PROMPT` is written in setup.
- **Disposition: FIX-NOW** (sol files, then mirror; plan lines by the coordinator). Use Brief P's exact P11, P12
  and P13 rewrites, which are still valid. Also:
  - implementer `:149` → `echo "lane files: LANE_ID=$LANE_ID PROMPT=$PROMPT OUT=$OUT LOG=$LOG"`;
  - `:200` "(written at launch)" → "(written in setup, just before launch)".

  If any is deliberately deferred, add it to the Phase 11 follow-ups list at `:695`. Otherwise S1 should count it
  as dismissed.

### S4-13 — LOW — Phase 10's superseded pwf bullet leaves three clauses' status unstated, and Order step 5 is unmarked

- **Claim.** The `:415` marker names four "do NOT"s. The original bullet (`:416-422`) also carries three more
  items:
  - "interim = plugin 3.17.2 → 3.20.5 (operator)" (the plugin is already 3.20.7, `:592`);
  - "archive `.planning/2026-09-21-*` to `.planning/.archive/`" (now #1360's outcome 1);
  - "refuse dispatch on an unattested plan; codex PreToolUse deny + operator `/hooks` trust" (now #1357's matrix,
    and the "operator … trust" is Phase 11 N F11).

  A Phase-10 resumer cannot tell which of these are live. Order step 5 "pwf interim (above)" (`:496`) has no
  marker.
- **Disposition: FIX-NOW.** Append to the `:415` marker: "The rest of this bullet is also absorbed: plugin
  already 3.20.7; the 2026-09-21 archive is #1360 outcome 1; refuse-on-unattested is #1357; `/hooks` trust is
  Phase 11 N F11." Change `:496` to "5. ~~pwf interim (above)~~ SUPERSEDED by #1351's tickets (Phase 11)."

### S4-14 — LOW — two follow-ups have no landing place, although their list header promises one

- **Claim.** `:695` says "each is a ticket or a line in an existing spec". But:
  - M-1 (`:704-705`, bounded-wait usage) names neither a ticket nor a spec;
  - N F10 (`:711`, "file the KB ticket for the `conda:coreutils` shim tax") has no owner and no number. A search
    found no such KB issue (`gh api search … coreutils` → 3 unrelated hits; control: `plan doctor-probe` → 1 hit,
    KB#807).
- **Disposition: FIX-NOW.**
  - M-1: "M-1 → trap line in the codex class-fix `/to-spec` (guard rule: deny `bounded-wait --file-contains` and
    a `2>/dev/null` on it); until then the handoff trap `:56` carries it."
  - N F10: "coordinator files it at the next session start (`issue-filer`, `FILE ISSUES: yes`, `-R
    ray-manaloto/knowledge-base`)", or file it now. Whether it was a missing request is S2's call.

## Checked and clean (no finding)

- **`plan-pointer.json`.** Its hash equals `task_plan.md`. `active_phase` equals the `:506` heading text (the order
  problem is S4-3's).
- **The `suites.toml` token re-bind itself.** The 5 per-path tokens and the global token equal the 5 sol launch
  lines: `grep -c 'PLANNING_DISABLED=1 mise exec -- codex exec'` = 1 in each. Control: `git show 5e258baf:` of
  `codex-sol-advisor.md` has 1 of the old `PLANNING_DISABLED=1 codex exec` form and 0 of the new.
- **The 12 wrappers carry no bare launch.** The regex `(^|| *|PLANNING_DISABLED=1 )codex exec` returns 0 in all
  12. That regex returns 1 on the pre-delta advisor, so it discriminates.
- **Current Phase `:714-725`** is internally consistent with round 7, and its frontier is right: #1352 and KB#802
  both say "Blocked by: None".
- **#1351 corrections comment** covers ruled questions 1 and 3, the upstream-asks status, the 12 wrappers being
  out of scope, and the order.
- **Issue bodies vs the approved draft.** Each footer cites "Ticket n of 18" and the draft appendix entry, and the
  appendix headings map all 18. The bodies carry no file paths, per the issue-template rule.

## Questions for Ray

1. **Fix the issue texts by comment or by body edit (S4-2, S4-7, S4-8)?**
   - *(Recommended)* **Comments on #1351 and #1352.** PRO: append-only, and the Ray-approved bodies stay byte-exact
     against `pwf-migration-tickets-draft-2026-09-23.md`. CON: an implementer must read the comments; the #1351
     corrections comment already sets that precedent ("this comment is authoritative").
   - **Edit the 18 bodies.** PRO: one place to read. CON: 18 body edits, each needing an anchor assert (memory
     `feedback_issue_body_edit_needs_anchor_assert`), and drift from the tracked draft.
2. **Retitle #1355 "D4" to avoid the deny collision (S4-1)?**
   - *(Recommended)* **No; add the "D4 deny always means the retired deny" line to the plan map.** PRO: no
     relabel churn across 18 cross-referencing titles. CON: the collision stays visible in titles
     [no prior evidence of a naming ruling].
   - **Retitle to "D4 (tasks)" or renumber.** PRO: removes the ambiguity at the source. CON: breaks the D1-D9
     sequence Ray approved.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #1351 (comments) and #1352-#1360
  (bodies, titles, labels) via `gh issue view -R`; PR/branch state via `gh pr list` and `git ls-remote`; local
  source, rules, agents, contracts and plans.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): issues #802-#810 (bodies, titles,
  labels); issue search for the N F10 ticket; local `.planning/` listing.
