# Session audit 2026-10-01c — Brief P: vague / misinterpretable docs and plans

Status: COMPLETE (written incrementally).

Audited session: `dotfiles-20261001.000` (7133045d). Method: Brief P (`session-2026-09-23d-agent-briefs.md:298`). Read-only lane; this file is the only write.

## Findings

### Batch 1 — handoff, takeover files, ship queue, task_plan (written incrementally)

Probes for this batch: `git ls-remote origin refs/heads/{main,docs/session-2026-10-01,docs/fanout-launch-fixes,docs/handoff-2026-10-02,docs/orchestration-research-fixes}` returned ONLY `main` (aeeb9164) — the main ref is the control arm, so the four absences are real. `gh api repos/ray-manaloto/knowledge-base/issues/{829,826}` → `pr=false open` for both (control: the same call returns title/state, so the endpoint answers). `git -C knowledge-base worktree list` → `lane-KB2-20261002 52babb73 [feat/kb-829-corpus-refresh]`.

#### V1 (HIGH) — running lanes are told to report to coordinator names that no longer exist

- **Claim:** every lane brief and two takeover files address a coordinator that is gone. The handoff itself says
  "old name `dotfiles-20261001.000` is gone" (`handoff-20261002/docs/handoffs/session-2026-10-02.md:55-56`), yet:
  - `dotfiles/.agent/plans/brief-lane-{A,B,C,E,G,KB2,KB3}-2026-10-02.md` — 3 hits each of `dotfiles-20261001.000`
    ("message dotfiles-20261001.000 first", "message dotfiles-20261001.000 with branch, head SHA…");
  - `takeover-native-cli-followups-2026-10-02.md:3,7,12,64,92` — "Coordinator: team-lead", "Report each item to
    team-lead via SendMessage", "report to team-lead **for ship**";
  - `takeover-kb-ship-2026-10-02.md:21,44,74` — "team-lead ruling", "send team-lead/Ray the PR#… team-lead does it";
  - `main-checkout-ship-queue.md:1` — "(owner: session dotfiles-20261001.000)", while `:35` says the owner changed.
  `team-lead` is the agent-team lead name of the dead `.000` session (the orchestration report calls its lane
  "teammate of `team-lead`", `orchestration-parallel-coordination-2026-10-02.md:9`); a `claude --bg` session has no
  team, so the name resolves to nothing.
- **Evidence:** transcript SendMessage scan (all `tool_use` with `name == SendMessage`, ordinal > 5000): after the
  HANDOFF broadcasts at 5351/5353/5355/5357 (to `kb-flake-fix`, `native-cli-followups`, `s29-takeover`,
  `cc-repoint`) the only message is 5522, to `dotfiles-20261002.coordinator`. No message re-points
  `dotfiles-20261002.lane-{A,B,C,E,G}` or the KB2/KB3 lanes to the new name. Whether the NEW coordinator re-pointed
  them is outside this transcript — UNVERIFIED (the ship queue `:38` "A: commit 3 gating" suggests some contact).
- **Control arm:** the same scan does find SendMessages to `dotfiles-20261002.lane-G`/`-A`/`-B` (5035, 5062, 5121),
  so the scan sees lane-addressed messages; it is not blind to them. `grep -c dotfiles-20261001.000` on the briefs
  returned 3 per file (non-zero), so the probe can count hits.
- **Disposition: FIX-NOW** (gitignored local files; the coordinator applies, then re-sends):
  - In each `brief-lane-*-2026-10-02.md`: old `message dotfiles-20261001.000` → new
    `message the coordinator named on line 1 of /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/main-checkout-ship-queue.md (today: dotfiles-20261002.coordinator)`;
    header old `coordinator session dotfiles-20261001.000` → `coordinator: see main-checkout-ship-queue.md line 1`.
  - `takeover-native-cli-followups-2026-10-02.md:3` old `Coordinator: team-lead.` → `Coordinator: dotfiles-20261002.coordinator (the name on line 1 of main-checkout-ship-queue.md; "team-lead" was the dead .000 session's agent-team name).`;
    every later `team-lead` → `the coordinator`.
  - `takeover-kb-ship-2026-10-02.md:21` `(team-lead ruling, Ray-approved)` → `(ruling by the old coordinator .000, Ray-approved)`;
    `:44` `send team-lead/Ray the PR# … team-lead does it` → `send dotfiles-20261002.coordinator the PR# + full head SHA; the coordinator performs Ray's pre-approved admin toggle-merge`.
  - `main-checkout-ship-queue.md:1` → `# Main-checkout ship queue (owner: session dotfiles-20261002.coordinator since 2026-10-02 ~13:30; was dotfiles-20261001.000)`.
  - Then one SendMessage to each live lane (`dotfiles-20261002.lane-{A,B,C,E,G}`, KB2/KB3 sessions): "coordinator is now `dotfiles-20261002.coordinator`; your brief is updated".
- **PLAN** (task_plan, Current Phase): `- [ ] Lane-brief template (parallel-work-split SKILL §5) names the coordinator INDIRECTLY ("the owner on line 1 of <ship-queue path>") so a coordinator rename is one edit, not N; add a handoff-check rule that flags a session name in .agent/plans/*.md that is not in \`claude agents --json --all\`.` Needs /to-spec (small; no grilling).

#### V2 (HIGH) — the plan still carries the superseded KB2 "SYMLINK, keep \$CC" ruling; three other docs say the opposite

- **Claim:** `task_plan.md:993` (POST-RESTART ORDER) says "KB#829 corpus refresh — Ray ruled: write the real mirror to
  `sources/claude-code-docs` and SYMLINK `sources/agent-harness-docs/docs/claude-code` to it (keeps the 98 `$CC`
  citations)", and `brief-lane-KB2-2026-10-02.md` repeats it. But the handoff (`session-2026-10-02.md:64`) says "KB2
  mirror at `sources/media/claude-code-docs/` (tracked); no `$CC` symlink", the cc-repoint takeover rewrites `$CC` to
  `$KB/media/claude-code-docs`, the ship queue `:32` names the repoint as a follow-up, and #1544 exists only because
  the anchors drift after a repoint. A fresh session reading Current Phase first would build the symlink.
- **Evidence:** `git -C knowledge-base diff --name-only origin/main...52babb73` → 234 of 243 files under
  `sources/media/claude-code-docs`; `git diff --summary` → 240 × `create mode 100644`, zero `120000` (symlink) entries.
- **Control arm:** the `--summary` probe prints modes (240 `100644` lines), so a `120000` symlink would appear; it
  does not. The path probe found `sources/media/...`, not `sources/claude-code-docs`.
- **Disposition: FIX-NOW** in `task_plan.md:993` (coordinator-only): old
  `KB#829 corpus refresh — Ray ruled: write the real mirror to \`sources/claude-code-docs\` and SYMLINK \`sources/agent-harness-docs/docs/claude-code\` to it (keeps the 98 \`$CC\` citations).`
  → new
  `KB#829 corpus refresh — SUPERSEDED 2026-10-02 (as built on feat/kb-829-corpus-refresh 52babb73): the mirror lives at \`sources/media/claude-code-docs/\`, NO symlink; dotfiles repoints \`$CC\` on \`docs/cc-repoint\` (414cc9f6) after the KB PR merges, and #1544 re-anchors the 78 drifted \`$CC/page.md:N\` citations. The 2026-10-01 symlink ruling is retired.`
  Ray ruling needed only to CONFIRM the supersession was his (the handoff lists it under "rulings already given");
  recommended option: confirm as-built.

#### V3 (HIGH) — the plan cites 15 reports/specs that exist on no pushed ref, and the handoff dropped the owed push

- **Claim:** `task_plan.md:993` cites "Session audits … docs/research/kb/reports/agents/session-audit-*-2026-10-01.md"
  and says "Docs branch `docs/session-2026-10-01` commit `2dfb8030` (11 reports + 4 briefs) is LOCAL ONLY … push
  after #1496"; `:1004` cites `claude-mods-refactor-plan-2026-10-01.md`, `claude-code-mods-2-1-287-sweep-2026-10-01.md`,
  `claude-code-local-otel-sink-2026-10-01.md`, `leak-prevention-betterleaks-hk-2026-10-01.md`. #1496 closed via #1503
  (landed), so the gating condition passed, but the push never happened and the 2026-10-02 handoff, ship queue and all
  four takeover files never mention `2dfb8030` or `docs/session-2026-10-01` (grep count 0 in each). A fresh session
  following those citations finds nothing; #1532 fixed V15-V17 FROM `session-audit-vagueness-2026-10-01.md`, a file
  that is not on main.
- **Evidence:** `git ls-remote origin refs/heads/docs/session-2026-10-01` → empty; `git branch -v` → local
  `docs/session-2026-10-01 2dfb8030`; `git cat-file -e origin/main:<f>` for all 29 files of `2dfb8030` → 29 MISSING;
  the files are also absent from the main checkout's working tree (`ls` → No such file).
- **Control arm:** `git cat-file -e origin/main:AGENTS.md` → present (the probe can say ON); `grep -c
  docs/fanout-launch-fixes` on the handoff → 4 (the grep can count a branch name that is there); the `ls` of the
  same directory lists other reports.
- **Disposition: FIX-NOW** in the unshipped handoff (`handoff-20261002/docs/handoffs/session-2026-10-02.md`), §
  "Main-checkout ship queue", add item 0:
  `0. \`docs/session-2026-10-01\` (\`2dfb8030\`, LOCAL ONLY, 29 files: the 2026-10-01 MODS/OTel/leak reports, six session-audit reports, four implementer briefs). Its "push after #1496" gate passed when #1503 landed. Rebase onto origin/main and ship it FIRST — task_plan.md:993/:1004 and #1532 cite these files and they exist on no remote ref.`
  and in `task_plan.md:993` replace `is LOCAL ONLY: pre-push pytest fails on the 2.1.287 claude- prefix break; push after #1496.`
  with `is LOCAL ONLY (still, 2026-10-02): its gate (#1496) closed via #1503; owed: rebase + ship as ship-queue item 0.`

#### V4 (MED) — "after KB #829 merges" / "after KB #826 lands": those numbers are ISSUES, not PRs

- **Claim:** handoff `:39` "`docs/cc-repoint` — only after KB #829 merges", `:41` "after KB #826 lands";
  `takeover-cc-repoint` heading "do not ship before KB #829 merges"; `task_plan.md:2478` "(after KB #829 + docs/cc-repoint)";
  ship queue `:32` "(KB2 #829)… (KB3 #826)". Both are open issues; an issue never "merges". A lane polling
  `gh pr view 829 -R ray-manaloto/knowledge-base` gets an error/issue, and one checking `gh issue view 829 --json state`
  waits for a CLOSED that may come from a different PR or never (the PR may not say `Closes #829`). The cc-repoint
  takeover's own probe (`gh pr list --head feat/kb-829-corpus-refresh`) is the right one; the prose around it is not.
- **Evidence:** `gh api repos/ray-manaloto/knowledge-base/issues/829` → `pr=false open`; same for 826.
- **Control arm:** the same call distinguishes PRs (`pull_request != null` → `pr=true` for any PR number); 836 also
  returned `pr=false`, consistent with all three being issues.
- **Disposition: FIX-NOW.** Handoff `:39` → `6. \`docs/cc-repoint\` — only after the KB PR from branch \`feat/kb-829-corpus-refresh\` (for KB issue #829) is MERGED: \`gh pr list -R ray-manaloto/knowledge-base --head feat/kb-829-corpus-refresh --state merged --json number\` non-empty.`
  `:41` `(after KB #826 lands)` → `(after the KB PR from \`feat/kb-826-currency-engine\`, for KB issue #826, is MERGED)`.
  Same substitution in `takeover-cc-repoint-2026-10-02.md:29`, ship queue `:32`, and `task_plan.md:2478`.

#### V5 (MED) — cc-repoint takeover misplaces the KB2 branch and tells the lane to ship from its worktree

- **Claim:** `takeover-cc-repoint-2026-10-02.md:31` says the KB2 branch is "checked out in the main KB clone at
  52babb73"; it is checked out in `knowledge-base.worktrees/lane-KB2-20261002`, and `takeover-kb-ship:13-14` says the
  KB main checkout is on `main`. `:39` says "`mise run ship` from the worktree", contradicting the one-shipper rule
  ("`mise run ship` runs from the main checkout… a linked-worktree ship fails `sync-full`", parallel-work-split
  SKILL.md:11-13, #1481; handoff `:27` "one shipper per repo").
- **Evidence:** `git -C knowledge-base worktree list` → `lane-KB2-20261002 52babb73 [feat/kb-829-corpus-refresh]`.
- **Control arm:** the same `worktree list` would show the main clone's path on that branch if the claim were true.
- **Disposition: FIX-NOW.** `:31` → `The branch is local-only (no origin ref), checked out in the KB2 lane worktree knowledge-base.worktrees/lane-KB2-20261002 at 52babb73; the KB main checkout stays on main.`
  `:39` → `3. Report branch + head SHA + gate rcs to dotfiles-20261002.coordinator; the coordinator ships it from the dotfiles MAIN checkout (/Users/rmanaloto/dev/github/ray-manaloto/dotfiles) per main-checkout-ship-queue.md, then lands it. This lane never runs ship.`

#### V6 (MED) — the ship queue is a broken table whose status column is 8 merges stale

- **Claim:** `main-checkout-ship-queue.md` interleaves bullets between table rows (`:19-24`, `:28`, `:30`, `:32`), so
  rows 6-11 no longer render as a table; and rows 0-8 still read "READY"/"queued"/"NEXT after plugin-health" although
  #1510, #1526, #1520, #1531, #1532, #1533, #1534, #1523 are all merged (handoff `:11-16`). Row 1 still says
  "ships after the secret fix". A reader taking "status" literally re-ships merged branches; the file's own rule
  (`:5` "Update the status column when a step changes") was not followed.
- **Control arm:** the MERGED rows are confirmed by `git log origin/main` (the 14-SHA table in the audit brief);
  row 0 shows the column CAN carry "MERGED #1510", so the stale cells are omission, not format.
- **Disposition: FIX-NOW.** Set Status: 1 `MERGED #1526 (40268e73)`, 2 `MERGED #1520`, 3 `MERGED #1531`, 4 `MERGED #1532`,
  6 `MERGED #1533`, 7 `MERGED #1534`, 8 `MERGED #1523`; 9/10 `NOT ON GITHUB — ship2 chain died at git push rc=141 (see OWNER CHANGE)`;
  move every bullet under a `## Notes (dated)` heading after the table.

#### V7 (MED) — "ship from MAIN" is ambiguous (the `main` branch vs the main checkout)

- **Claim:** handoff `:32` "ship from MAIN", ship queue `:33` "(Lane G; ship from MAIN…)", s29 takeover `:4,:87`
  "ships it from the MAIN checkout". Read literally by a codex lane, "from MAIN" is "from the main branch", which
  `do-not.md` #9 forbids and `ship` refuses. Only some sites say "checkout".
- **Control arm:** n/a (prose ambiguity; the other two sites spell out "main checkout", proving the intended reading).
- **Disposition: FIX-NOW.** Every "ship from MAIN" → `ship from the dotfiles main checkout (/Users/rmanaloto/dev/github/ray-manaloto/dotfiles) with the branch checked out there — never from a lane worktree (#1481)`.

#### V8 (MED) — stash instructions conflict with the shared-stash rule

- **Claim:** handoff `:72` "Host mise rewrites `mise.lock` during land/gates; stash by message before land";
  kb takeover `:58` "pop the two stashes BY MESSAGE (find the index with `git stash list | grep -n`)"; ship queue
  `:30` "3 stashes hold examples" (unowned, unnamed). The stash stack is shared across every worktree and session
  (several sessions run concurrently by design of this fan-out), so an index found by `grep -n` can shift before
  `pop`, and `pop` on the wrong index applies another session's work. The harness contract for this repo's sessions
  is: capture the stash SHA immediately, `git stash apply <sha>`, then drop by re-found tag.
- **Control arm:** n/a (instruction-vs-rule conflict; the kb takeover's own `stash push -m … -- <paths>` is the
  safe half).
- **Disposition: FIX-NOW.** kb takeover `:58` → `# restore EXACTLY: switch main; for each tag: sha=$(git -C $K stash list --format='%H %gs' | grep -F '<tag>' | cut -d' ' -f1); git -C $K stash apply "$sha"; then re-find its stash@{n} by the same tag and drop it.`
  Handoff `:72` → `Host mise rewrites mise.lock during land/gates (musl entries, jdx/mise#13857) — fix it at the source (ship-queue item 7: commit the entries via scoped \`mise run lock -- "<backend/name>"\`); until then stash with a unique -m tag, capture the SHA, and restore with \`git stash apply <sha>\`, never \`pop\`.`
  Ship queue `:30` → name the three stash tags or say `none outstanding`.

#### V9 (MED) — task_plan Goal contradicts Current Phase; the 2026-10-02 fan-out is invisible from Current Phase

- **Claim:** `task_plan.md:11-18` (§ Goal, the first section a fresh session reads) says "Phase 1 — `update-all` runs
  clean [check 1 OPEN…]" and "A real mutating run is unproven"; `:1001` (Current Phase, 2026-10-02 STATE) says
  "Phase 1 check 1: real `mise run update:all` rc=0 (2026-10-01…) — MET". Separately, Current Phase's "2026-10-02 STATE"
  block (`:995-1003`) still lists the pre-fan-out SHIP QUEUE (`#1329 -> feat/native-cli-devcontainer -> … -> S29-00b`, all
  but S29-00b merged) and never names the fan-out, the new coordinator, or the handoff; the only 2026-10-02 coordinator
  section (`:2477`) sits under `## Phase 8 — QUEUED behind Phase 9` (`:2369`), after `## ARCHIVE` (`:1447`).
- **Control arm:** `rg -n 'Phase 1' task_plan.md` finds both sites (the contradiction is between two hits of one
  probe, not a missed third site).
- **Disposition: FIX-NOW** (coordinator-only file). `:11` `[check 1 OPEN, checks 2-4 MET]` → `[ALL MET — check 1 met 2026-10-01, see Current Phase 2026-10-02 STATE]`;
  `:16-18` replace the OPEN sentence with `**MET** 2026-10-01: real run rc=0 (64.3s, 52.7s guarded).`
  Add as the first bullet of Current Phase `:995`: `- **2026-10-02 FAN-OUT (read first):** coordinator is now \`dotfiles-20261002.coordinator\`; index = \`docs/handoffs/session-2026-10-02.md\` (branch docs/handoff-2026-10-02, 9d2f202b, NOT yet on GitHub); ship order = \`.agent/plans/main-checkout-ship-queue.md\` § OWNER CHANGE; the SHIP QUEUE line below is HISTORICAL (all merged except S29-00b).`
  Move the `### 2026-10-02 coordinator follow-ups` block (`:2477-2479`) up under Current Phase.

#### V10 (MED) — undefined shorthand in the TRACKED handoff; definitions live only in a gitignored file

- **Claim:** the tracked handoff uses "Lane G" (`:32`), "Lanes A … B … C … E" (`:34-35`), "lanes A/B/C/E/G, KB2/KB3
  lane sessions" (`:54`), "watcher `dotfiles-20261002.watch` (`998ab91b`)" (`:55`), "round i" (`:37`), and the ship
  queue / native-cli takeover use "HEL" (`ship-queue:23`, `takeover-native-cli:15,17`) and "F1–F5", "item 2/5/6",
  "U1–U6", "S1–S4". The letters are defined only in `dotfiles/.agent/plans/parallel-lane-plan-2026-10-02.md`
  (gitignored, main-checkout-local) and `brief-lane-*.md`; neither is cited by the handoff. The tracked orchestration
  report also cites that local file (`orchestration-parallel-coordination-2026-10-02.md:136` "lanes A–J"), contrary to
  `agent-artifact-conventions.md` ("Promote anything a… later session will cite"). Lane D/F/H/I/J were planned but
  never launched, so "lanes A–J" ≠ "lanes A/B/C/E/G" — a reader cannot tell which exist. `998ab91b` is an
  unlabeled id (a `/Users/rmanaloto/.claude/jobs/998ab91b/` job dir per ship-queue `:39`, not a git SHA).
- **Control arm:** `rg -c 'dotfiles-20261001.000'` on briefs = 3 each shows the briefs ARE where lanes are defined;
  the handoff `rg -n 'parallel-lane-plan'` → 0 hits (no pointer).
- **Disposition: FIX-NOW**, add to the handoff after "## Fan-out sessions":
  ```
  ## Glossary
  - Lane letters come from `.agent/plans/parallel-lane-plan-2026-10-02.md` (local, main checkout). LAUNCHED: A = feat/ask-quality-v2 (ask_quality v2), B = feat/handoff-check-stale-prose (#1457 + stale-prose check), C = fix/research-sweep-1471-1514, E = feat/gate-run-multi-name, G = fix/ops-sync-1478-1481 (#1478/#1481). D, F, G2, H, I, J were planned, NOT launched.
  - KB2 = KB issue #829 corpus refresh, branch feat/kb-829-corpus-refresh; KB3 = KB issue #826 currency library mode, branch feat/kb-826-currency-engine.
  - HEL = the ray-manaloto/harness-evolution-ledger repo.
  - S29-00b = the bot-PR regenerate fix (branch fix/s29-00b-bot-pr-regenerate); "round i" = its ninth review round (spec docs/specs/s29-00b-round-i-2026-10-02.md).
  - watcher = session dotfiles-20261002.watch, job dir ~/.claude/jobs/998ab91b/.
  ```
  PLAN: the orchestration-research-fixes branch (`aac2c0b8`, unshipped) should also promote the lane-plan table, or
  replace `:136` with the launched-lane list above.

#### V11 (LOW) — "codex usage-limited until 2026-10-03 12:01" has no timezone (and lost its AM/PM)

- **Claim:** the source line (transcript ordinal 6, the resumed handoff) reads "until 2026-10-03 12:01 PM"; every
  derivative drops "PM" and the zone: handoff `:7`, all 7 lane briefs, kb takeover `:29,:83`, s29 takeover `:85`,
  task_plan `:1002,:1006`. "12:01" alone reads as 00:01 to a UTC-minded codex lane — 12 h early — and the owed
  codex-sol lenses are scheduled on it.
- **Evidence/control:** transcript scan for `12:01` + `usage|limit` → ordinal 6/246 carry "12:01 PM"; later copies do not.
- **Disposition: FIX-NOW** everywhere: `2026-10-03 12:01` → `2026-10-03 12:01 PM local (America/Los_Angeles = 19:01Z), per the codex usage-limit message`.
  (Zone assumed from the Mac host; if Ray's codex banner showed another zone, use it — UNVERIFIED.)

#### V12 (LOW) — garbled ship-queue instruction for lane E

- **Claim:** ship queue `:37` "E feat/gate-run-multi-name (90c9c96d; re-stamp _V12 since if after 2026-10-02 UTC)" is
  not parseable. Lane E's `hook_guard.py:173` has `_V12 = "2026-10-02"`; per `mise-tasks-only.md` § Extending, a rule's
  `since` must be "the day it lands on main", so it needs a re-stamp iff the merge date ≠ 2026-10-02 UTC.
- **Evidence:** `git grep -n _V12 90c9c96d -- python/src/dotfiles_setup/hook_guard.py` → `:173 _V12 = "2026-10-02"`.
- **Disposition: FIX-NOW** → `E feat/gate-run-multi-name (90c9c96d) — before ship, set hook_guard.py \`_V12\` (now "2026-10-02") to the UTC date the PR will merge, if that is later than 2026-10-02 (mise-tasks-only.md § Extending: \`since\` = the day it lands on main).`

(Correction to V10's control arm: the probe actually run was `rg -c 'parallel-lane-plan|Lane G'` on the handoff → 2,
both `Lane G` hits; so the handoff contains no pointer to the lane plan, and the probe was shown able to count.)

### Batch 2 — shipped docs (#1505, #1526, #1520, #1531, #1532, #1533, #1534, #1510)

Read: diffs of `.claude/CLAUDE.md`, `.claude/rules/ai-cli-invocation.md`, `.devcontainer/{AGENTS,TOOL-PERSISTENCE}.md`,
`.github/workflows/AGENTS.md`, lock-image + plugin-health SKILL.md, `python/AGENTS.md`, `doctor.toml` native_only
block, `docs/specs/research-enforcement-2026-09-30.md` header, `parallel-work-split/SKILL.md` (whole),
`orchestration-parallel-coordination-2026-10-02.md` (whole). Cold/code/spec reviews and vendored mirrors were not
re-read (verbatim records, `agent-artifact-conventions.md` rule 8). Clean on read: lock-image `--no-bump` paragraph,
plugin-health `builtin_unobservable` line, python/AGENTS.md codegen section, research-enforcement Status header,
devcontainer AGENTS/TOOL-PERSISTENCE hunks.

#### V13 (MED) — ai-cli-invocation.md now contradicts its own first sentence, and its version line is stale

- **Claim:** #1505 changed the agy example to `"$HOME/.local/bin/agy"` and says "never rely on … `mise exec -- agy`"
  (`:68`), but the rule still opens with "Invoke every AI CLI through `mise exec --`" (`:7`) and its re-probe block
  says "run the **pinned** CLI's own help" (`:99`) although #1505/#1526 made claude/codex/agy unpinned
  ("no mise/npm pin anywhere", `.claude/CLAUDE.md` after #1526). `:46` "the host now runs native 0.156.x" — the host
  runs 0.160.0. A codex lane reading `:7` first follows the wrong form for agy.
- **Evidence:** `rg -n 'mise exec --|pinned CLI|0\.15[0-9]' ai-cli-invocation.md` → `:7`, `:46`, `:68`, `:99`;
  `~/.local/bin/codex --version` → `codex-cli 0.160.0`.
- **Control arm:** the same rg hits `:68` (the new agy sentence), so it sees the post-#1505 text.
- **Disposition: FIX-NOW** (eager rule; run `mise run lint-docs` + rule-sync after): `:7` →
  `Invoke codex and opencode through \`mise exec --\` (for codex, mise's \`disable_tools\` makes that resolve the NATIVE install) and agy by its absolute native path (below); re-probe each CLI's help before copying flags.`
  `:46` → `## Codex facts (probed at 0.152.1; host runs native 0.160.0 as of 2026-10-02 — re-probe before relying)`;
  `:99` `run the pinned CLI's own help:` → `run the installed CLI's own help:`.

#### V14 (MED) — s29 takeover asks for `/code-review` with a "base", right after saying the argument is the target

- **Claim:** `takeover-s29-00b-2026-10-02.md:75-78`: "re-run `/code-review high` … with the TARGET
  `fix/s29-00b-bot-pr-regenerate` (the argument is the target, not a base…), against base `c7a46169`". `/code-review`
  takes ONE target; there is no base argument, so "against base c7a46169" is either ignored or, if passed, makes it
  review commit c7a46169 — the exact mistake the handoff gotcha (`:69`) records for #1534. `:87` also cites "queue
  item 5 in `docs/handoffs/session-2026-10-02.md`", a file that exists only on the unpushed `9d2f202b` in another
  worktree (V3/handoff), not in this lane's worktree.
- **Control arm:** the skill description (`code-review: Review the current diff, or a PR number/branch/path target`)
  lists no base parameter; MEMORY `feedback_code_review_arg_is_target_not_base`.
- **Disposition: FIX-NOW.** `:75-78` → `If not, run \`/code-review high fix/s29-00b-bot-pr-regenerate\` from inside the worktree (one TARGET argument; it reviews the branch against its merge-base — there is no base argument). For a review of only round i, use the cold-reviewer agent with fixed point c7a46169 instead.`
  `:87` → `(ship-queue item 5 in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/main-checkout-ship-queue.md)`.

#### V15 (LOW) — kb takeover names two different actors for the KB2 admin merge

- **Claim:** `takeover-kb-ship-2026-10-02.md:44` "Ray already approved the admin toggle-merge, and team-lead does it",
  `:45` "After Ray merges: sync main…". Handoff `:61-62` gives the procedure but no actor. The lane cannot tell whether
  to wait for Ray or the coordinator.
- **Disposition: FIX-NOW** `:45` → `After the coordinator (dotfiles-20261002.coordinator) completes the pre-approved toggle-merge and confirms enforce_admins is back ON: sync main with …` (and V1's `:44` rewrite).

#### V16 (LOW) — native-cli-followups takeover states the main checkout's branch, which is stale

- **Claim:** `takeover-native-cli-followups-2026-10-02.md:96` "the main checkout is on feat/native-only-doctor-check
  4923773b". `/usr/bin/git -C dotfiles branch --show-current` → `docs/fanout-launch-fixes`. A point-in-time fact with no
  timestamp reads as current.
- **Control arm:** the same command returns a branch name (not empty), so it can report one.
- **Disposition: FIX-NOW** → `- Never touch the main dotfiles checkout; its branch changes with the ship queue (main-checkout-ship-queue.md), so do not rely on any branch named here.`

#### V17 (LOW) — parallel-work-split SKILL launch snippet mixes two cwd bases; template has no coordinator name

- **Claim:** `SKILL.md:99-100`: `git -C <repo> worktree add ../<repo>.worktrees/…` resolves `../` against `<repo>`, while
  the next line's `cd ../<repo>.worktrees/…` resolves against the caller's cwd — the two only agree when cwd is
  `<repo>`. The brief template (`:129`) says "report to the coordinator" without a session name or channel, which is
  how V1's dead-name problem arose (the skill itself warns at `:137` that messages are held or dropped).
- **Disposition: FIX-NOW** `:99-100` →
  ```bash
  wt=$(dirname <abs-repo>)/<repo>.worktrees/<lane>-<YYYYMMDD>
  git -C <abs-repo> worktree add "$wt" -b <type>/<lane> origin/main
  cd "$wt" && claude --bg -n <lane> "<brief>"
  ```
  `:129` STOP AT → `STOP AT: commit on the branch. Do NOT push, ship or open a PR. Final status goes in the PERSIST report file; also SendMessage the coordinator named on line 1 of <ship-queue path> — the file, not the message, is authoritative.`

#### V18 (LOW, no edit) — orchestration report's "crossSessionInbound is unset" is now false

- **Claim:** `orchestration-parallel-coordination-2026-10-02.md:43,100` say `crossSessionInbound` is unset; the user
  setting was set the same day (handoff `:65`; SKILL.md `:113-114`). The skill is current, the report is a dated
  verbatim record. **Disposition: PLAN** (no record edit): `- [ ] When docs/orchestration-research-fixes (aac2c0b8) ships, add a dated "Superseded 2026-10-02: crossSessionInbound=accept now set in user settings" note ABOVE the report body, not inside it.`

## Summary

18 findings: HIGH 3 (V1 dead coordinator names in lane briefs/takeovers; V2 plan carries the superseded KB2 symlink
ruling; V3 15+ cited reports exist on no pushed ref and the owed push was dropped from the handoff). Counts: HIGH V1 V2 V3; MED V4 V5 V6 V7 V8 V9 V10 V13 V14;
LOW V11 V12 V15 V16 V17 V18 → 3 / 9 / 6.
Every FIX-NOW in a gitignored file (`.agent/plans/*`, `task_plan.md`) is the coordinator's to apply; tracked-file
fixes (handoff, ai-cli rule, SKILL.md) go on a branch. Per the 2026-09-29b-late protocol, V1/V3/V9 also deserve a
machine check (session names vs `claude agents --json --all`; cited paths vs `git cat-file -e origin/main:`) before
the hand edit — PLAN rows, need /to-spec.

Status: COMPLETE.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `git ls-remote` branch existence; local history/diffs of the 11 dotfiles SHAs
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issues #826/#829/#836 type+state via `gh api`; KB2 branch diff (local clone)
