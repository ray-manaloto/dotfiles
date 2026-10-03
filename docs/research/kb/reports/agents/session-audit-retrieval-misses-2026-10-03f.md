# Session-integrity review: retrieval misses (2026-10-03f)

Status: COMPLETE (see end of file)

Method: `## Brief S (retrieval misses)` of `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md`,
under `/Users/rmanaloto/.claude/jobs/998ab91b/tmp/audit-brief-common.md`.
Session: `998ab91b-50a0-4bd2-917b-aa8e5825b915` ("dotfiles-20261002.watch"). Transcript ordinals `[N]` are 1-based
line numbers of
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles-worktrees-lane-completion-20261002/998ab91b-50a0-4bd2-917b-aa8e5825b915.jsonl`
(5148 lines). Lane: read-only except this file. `$CC` =
`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`. Claude Code on this host:
`2.1.288` (`claude --version`, run now).

Each row: the fact the session re-derived, its cost, and the ONE file that should carry it. The exact lines are in
**§ Lines to add (verbatim)**, kept out of the table so their `|` characters survive. The coordinator applies them.

## Findings

| # | Sev | Fact the session re-derived (or never retrieved) | Cost (transcript ordinals) | Carrier (ONE file) | Control arm |
|---|---|---|---|---|---|
| R1 | HIGH | This repo's own `dev.mise.dotfiles-dag-tick` LaunchAgent runs `claude stop` on every DONE background node whose process lingers (`python/src/dotfiles_setup/dag_tick.py:9`, still so on `origin/main`). A coordinator idle at turn end reads `done`, so the watchdog kills it. The session instead blamed the harness: "A background session that ends its turn with nothing running gets stopped" [1134], and later logged "its process was stopped" for fnox-provider [3107], audit-s29 [3408] and devcontainer-cap [3669] without asking what stopped them | The attribution was never corrected by this session; the ~12 h coordinator outage (≈22:30 to 10:23, [2778] to [4124]) ran until the coordinator traced STOP lines in `~/Library/Logs/dotfiles-dag-tick.log` [4171]/[4183]. Every stop the watcher reported was evidence it did not follow | `.claude/skills/parallel-work-split/SKILL.md` § 6 "Monitor and collect" (after :139) — the section a fan-out watcher reads for lane state | `git show origin/main:python/src/dotfiles_setup/dag_tick.py` :9 → "`claude stop` for a DONE node whose process is still lingering"; `mise.toml:695` declares the LaunchAgent. Negative arm: `grep -n -i 'dag.tick' .claude/skills/parallel-work-split/SKILL.md` → no hit (the section the session read [333] never names it) |
| R2 | MEDIUM | `claude agents --json --all` field semantics for finished lanes: `state` is NOT a completion signal on its own. Measured in one census [429]: lane G finished yet `state: working, status: idle`; KB2 finished yet `state: blocked` with no `waitingFor` [195]/[203]; lanes B/E `status: waiting, waitingFor: "input needed", state: blocked` on live AskUserQuestion dialogs; lane A `state: blocked, status: idle`, no `waitingFor` = a PROSE question at turn end [902]/[911]; a stopped process drops `pid`/`status` and keeps only `state` | A full research sweep [370]/[481] (Opus synthesis, 495-line report) plus 4 `claude logs` scrapes [198], [434]-[463]. The sweep itself concluded "No single Claude Code field reliably says finished" (`fanout-lane-completion-detection-2026-10-02.md:27`). The `pid`/`status` vs `state` split was already measured in `docs/research/kb/reports/agents/602-crosssession-sendmessage-probe.md:43` | `.claude/skills/parallel-work-split/SKILL.md:134` (§ 6, the line that tells the reader to use `state`, `waitingFor`) | Rows quoted verbatim at [429]. Doc arm: `$CC/agent-view.md` says a finished turn reads `done` (cited by the session at [487] as `agent-view.md:783`), so docs and measurement disagree — the line records the measurement, not the doc |
| R3 | MEDIUM | The native worktree-isolation guard (EnterWorktree, [396]) refuses a compound Bash command as "names git in a form too complex to verify" when it carries an UNQUOTED `$?` (`echo rc=$?`) together with any path containing the substring `git` — e.g. `~/dev/github/...`. It is not about git at all. A quoted `"rc=$?"`, a plain `cp a b`, or a `/tmp` path passes. Separately, a `Write` to a main-checkout path is refused ("Edit the worktree copy") while a Bash `cat file >> <main-checkout path>` passes [2757] vs [2774] | 7 refused calls: [403], [435], [439], [948], [2751], [4442] (Bash) and [2757] (Write); each forced a rewrite. The session's rule of thumb after [442] ("Literal paths, then") was wrong — [4441] used literal paths and was still refused | `.claude/rules/agent-artifact-conventions.md` § "Worktrees and agent isolation" (eager; it is the repo's only worktree-isolation text) | Re-derived NOW in this (also isolated) lane, same session class: `ls -d /Users/rmanaloto/dev/github; echo rc=$?` → REFUSED; `ls -d /Users/rmanaloto/dev; echo rc=$?` → `rc=0`; `ls <worktree>/AGENTS.md; echo rc=$?` → REFUSED; same with `echo "rc=$?"` → `rc=0`; same with `echo done` → passes; `X=<github path>; ls $X/AGENTS.md` → passes. The `git` substring + unquoted `$?` pair discriminates. Docs: `$CC/errors.md:3321` documents only path-resolution refusals; `$CC/changelog.md:741` (2.1.257) and `:671` (2.1.259) claim the loop/`$VAR` false positives fixed, yet this reproduces on 2.1.288 |
| R4 | MEDIUM | After `EnterWorktree` the session transcript moves to the worktree's project dir (`$CC/worktrees.md:79`; the JSONL carries `relocated`/`worktree-state` records, [393], [5080], [5085]) while task outputs stay under the ORIGINAL project's `/private/tmp/claude-501/<old-project>/…/tasks/`. `mise run session-agentsview-pass` then lists by project name and returns UNVERIFIABLE; its `--session <id>` flag (in `main.py:1674-1679`, "skips session list") runs the pass anyway | [5091] UNVERIFIABLE accepted as the §1b result; [5100] glob over `~/.claude/projects/*/` to find the transcript; [5146] reported the pass as UNVERIFIABLE instead of retrying with `--session` | `.claude/skills/session-handoff/SKILL.md` § 1b (after the `mise run session-agentsview-pass` block, :112-113 on origin/main) | Run NOW, both arms: bare `mise run session-agentsview-pass` → `UNVERIFIABLE — session list found no Claude session for this project`, rc=2; `mise run session-agentsview-pass -- --session 998ab91b-50a0-4bd2-917b-aa8e5825b915` → `537 tool calls … unbounded waits: 0 … AskUserQuestion: 12 … handoff Skill: ord 1218`, rc=0 |
| R5 | MEDIUM | `mise run coordinator-handoff -- launch --handoff <file> --old-session <id>` is usable from OUTSIDE the old coordinator (any session, from the main checkout), with `--dry-run` first. The skill frames it only as "the old coordinator's half" | The first plan was a hand-rolled `claude --bg -n dotfiles-20261003.coordinator` [4378]; then Read of the skill [4387], `launch --help` [4400], a dry-run [4419] before the real launch [4425] (rc=0, session `30d222ef`). The generated brief still said the old coordinator "handed off automatically at its context limit" [4426] — false for an external launch, so the successor was told something untrue | `.claude/skills/coordinator-handoff/SKILL.md` § 2 "Launch the successor" (after the code block, :57-59 on origin/main) | `--help` [4401] lists only `--handoff`, `--old-session`, `--dry-run`, `--jobs-dir`, `--state-dir` — no "must run inside the old session" guard; the dry-run [4420] and real launch [4426] succeeded from the watcher session. Negative arm: `git show origin/main:.claude/skills/coordinator-handoff/SKILL.md \| grep -n -i 'outside\|external\|another session'` → 0 hits |
| R6 | MEDIUM | The coordinator-handoff function hook is loaded only at session start or after `/reload-plugins`: a coordinator started before the plugin reached the main checkout never fires, and fails silent (no state file under `.agent/state/coordinator-handoff/`) | A side agent [4190] re-derived it from file mtimes (`register.ts` 10:24:37 vs coordinator restart 10:23:53) and state-dir contents; the stuck coordinator sat at 98% context. The fact was already CONFIRMED as premise P7 in `docs/specs/coordinator-auto-handoff-2026-10-02.md:335`, which neither the skill nor the land step surfaces | `.claude/skills/coordinator-handoff/SKILL.md`, header paragraph (after :24, "The judgement is `mise run coordinator-handoff -- decide`…") | `git grep -n reload-plugins origin/main -- .claude/skills/coordinator-handoff` → 0 hits; same grep over `docs/specs/coordinator-auto-handoff-2026-10-02.md` → :335, :346, :356 |
| R7 | MEDIUM | A bare `git push` whose pre-push hook runs the full suite (~16 min) dies `rc=141` after the suite passes because GitHub drops the idle SSH connection; `ship` avoids it with `ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=20` (`pr.py:568`). Known in `pr-workflow/SKILL.md:128`, but the session pushed outside `ship` and never loaded that skill | Push 1 rc=141 after 4540 tests passed [767]; push 2 started blind [771] and was stopped [814] once the coordinator diagnosed it [807]; push 3 with `GIT_SSH_COMMAND` rc=0 [818]/[845]. ≈32 min of suite time lost | `.claude/rules/long-running-command-hangs.md` rule 2, the "Mac-side container ops" paragraph (eager — the rule in force at every push) | `grep -c ServerAlive ~/.ssh/config` → 0, control `grep -c '^Host' ~/.ssh/config` → 1 (readable, no keepalive); `git ls-tree -r --name-only origin/main home \| grep -i ssh` → none (chezmoi carries no ssh config). Positive arm is the session's own [845] rc=0 with the flag |
| R8 | LOW | `session-state --for` accepts only `session-YYYY-MM-DD` plus at most ONE letter (`handoff_check.py:35`, `-?[A-Za-z]`); a word suffix such as `-watch` exits 2 | 1 failed call [5069]/[5070] rc=2, retried as `session-2026-10-03-f.md` [5074] | `.claude/skills/session-handoff/SKILL.md:36` (§ 1 snapshot command, already read at [5050]) | Regex `^session-(?P<date>\d{4}-\d{2}-\d{2})(?:-?(?P<suffix>[A-Za-z]))?\.md$`; `-watch` → rc=2 [5070], `-f` → rc=0 [5075] |
| R9 | LOW | Text in a lane's input box shown by `claude logs` is not necessarily a human draft: Claude Code renders grayed-out prompt suggestions there (`$CC/settings-reference.md:3175`). The tick strips ANSI before reading, which erases the only visual difference | One false alert to the coordinator and Ray about lane G's "run memory-index-curation" [2006]/[2018], corrected by the coordinator [2023]; the model-registry draft [3965] was real ([4140]), so the same reading was right once and wrong once | `.claude/skills/parallel-work-split/SKILL.md` § 6 (same section as R1/R2; it already warns against scraping logs) | Doc arm: `$CC/settings-reference.md:3175` "the grayed-out predictions that appear in your prompt input"; `$CC/env-vars.md:276` `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION`. UNVERIFIED: no saved log under `/Users/rmanaloto/.claude/jobs/998ab91b/tmp/` still holds a suggestion sample (checked 4 logs' last `❯` lines), so the exact SGR that marks a suggestion is not measured here |
| R10 | LOW | `Workflow({name: "research-sweep-run"})` runs the copy in the session's CWD `.claude/workflows/`; a worktree branched before #1581 runs the pre-fix workflow, so the sweep reported Retrospect "missing" when it was on main | The stale claim was committed (`49c6f7fc`) and sent to the coordinator; a side agent caught it [4720]; one correction addendum + commit `0ac9bacd` [4778]-[4870] | `.claude/skills/research-sweep/SKILL.md`, next to `:30` ("`.claude/workflows/research-sweep-run.js` — that file is the single source of …") | `git merge-base --is-ancestor origin/main HEAD` in this worktree → rc=1 (base predates main) |
| R11 | LOW | `autoCompactEnabled: false` is set deliberately in the USER settings (Ray's "/clear, never /compact"). The session told the coordinator "nothing in the repo turns it off. Something else did" [4757] | The coordinator retracted its question once it found the user-level key [4789]; one wrong claim relayed | Memory `feedback_no_compact.md` (`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/`) — the file whose MEMORY.md hook ("No compact, use /clear") is loaded every session | `grep -c autoCompactEnabled ~/.claude/settings.json` → 1; control `grep -c '"model"\|"env"' ~/.claude/settings.json` → 2. Negative arm: `grep -c autoCompactEnabled` over the memory file → 0 |

Count: HIGH 1, MEDIUM 6, LOW 4.

**Disposition:** every row is FIX-NOW with the matching `L-R<n>` below, EXCEPT:

- R3 also needs an upstream report: PLAN, below.
- R1's real fix is the dag-tick code change already in a lane ("DONE never stops", per [4199]). L-R1 is the stopgap
  until that lands, so its wording must be removed in the same PR that lands the fix.

R1-R10 are tracked repo edits (the handoff branch can carry them; `mise run lint-docs` and the `md_size_budget`
step must hold for the rule and skill edits). R11 is an auto-memory edit outside the repo.

## Lines to add (verbatim)

**L-R1**: `.claude/skills/parallel-work-split/SKILL.md`, § 6, new paragraph after the existing one (:134-139):

```text
A lane or coordinator that reads `state: done` gets `claude stop`ped within a minute by this repo's
`dev.mise.dotfiles-dag-tick` LaunchAgent (`dag_tick.py:9`: "`claude stop` for a DONE node whose process is
still lingering"), and a coordinator idle at turn end reads `done`. When a session's process vanishes, check
`~/Library/Logs/dotfiles-dag-tick.log` for a STOP line before blaming the harness (2026-10-02: a 12 h outage).
```

**L-R2**: `.claude/skills/parallel-work-split/SKILL.md:134`, replace the parenthesis with:

```text
Read lane state with `claude agents --json --all` — a top-level array; a live row has `pid` and `status`
(`busy`/`idle`/`waiting`), a stopped one keeps only `state`. `state` is NOT a finish signal on its own
(measured 2026-10-02, 2.1.287): a finished lane read `working`+`idle`, another `blocked` with no `waitingFor`.
Only `status: waiting` + `waitingFor` means a live dialog; `blocked`+`idle` with no `waitingFor` is a prose
question at turn end. Corroborate "finished" with the lane's report file and branch commit.
```

**L-R3**: `.claude/rules/agent-artifact-conventions.md`, § "Worktrees and agent isolation", append:

```text
In an isolated session the native guard refuses a compound Bash command that has an UNQUOTED `$?`
(`echo rc=$?`) and any path containing `git` (e.g. `~/dev/github/…`) as "names git in a form too complex to
verify" — measured on 2.1.288. Write `echo "rc=$?"`. A `Write`/`Edit` to a main-checkout path is refused; write
the file under the scratchpad and copy it with a plain `cp`.
```

**L-R4**: `.claude/skills/session-handoff/SKILL.md` § 1b, after the `mise run session-agentsview-pass` block:

```text
After `EnterWorktree` the transcript moves to the worktree's project directory (`$CC/worktrees.md:79`), so the
project listing finds nothing and reports UNVERIFIABLE. Re-run with the session id before accepting that:
`mise run session-agentsview-pass -- --session <session id>`.
```

**L-R5**: `.claude/skills/coordinator-handoff/SKILL.md` § 2, after the code block:

```text
`launch` does not have to run inside the old coordinator. When that session is dead, stopped, at its context
limit, or never loaded the hook, any session may run it from the main checkout with the old session's id —
`--dry-run` first. The brief it generates still says the old coordinator handed off "automatically"; correct
that in the handoff file it points at.
```

**L-R6**: `.claude/skills/coordinator-handoff/SKILL.md`, header, after "The judgement is … the spec is
`docs/specs/coordinator-auto-handoff-2026-10-02.md`.":

```text
The hook exists only in sessions that started, or ran `/reload-plugins`, AFTER the plugin reached the main
checkout (spec premise P7). An older coordinator never fires and leaves no state file under
`.agent/state/coordinator-handoff/`; launch its successor from outside (§ 2).
```

**L-R7**: `.claude/rules/long-running-command-hangs.md` rule 2, end of the "Mac-side container ops" paragraph:

```text
A bare `git push` outside `ship` runs the same ~16 min pre-push suite, and GitHub drops the idle SSH
connection: rc=141 after the tests pass. Push with the keepalive `ship` uses (`pr.py:568`):
`GIT_SSH_COMMAND='ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=20' git push …`.
```

**L-R8**: `.claude/skills/session-handoff/SKILL.md:36-38`, after the command:

```text
`[-letter]` is ONE letter, with or without the dash (`session-2026-10-03f.md`); any other suffix
(`-watch`) exits 2.
```

**L-R9**: `.claude/skills/parallel-work-split/SKILL.md` § 6, append:

```text
Text in a lane's input box in `claude logs` may be a grayed-out prompt suggestion, not a human draft
(`$CC/settings-reference.md:3175`); stripping ANSI erases the difference. Ask the lane's owner before
alerting "unsent reply".
```

**L-R10**: `.claude/skills/research-sweep/SKILL.md`, after :30-31:

```text
The workflow runs from the session's CWD checkout. From a worktree, confirm
`git merge-base --is-ancestor origin/main HEAD` first, or the sweep runs (and audits) a stale copy.
```

**L-R11**: memory `feedback_no_compact.md`, append to **How to apply**:

```text
`autoCompactEnabled: false` in `~/.claude/settings.json` is this preference, set deliberately at user level.
A session showing "auto-compact is off" is expected; do not report it as an unexplained setting.
```

## PLAN (task_plan.md text)

- R3: `- [ ] File upstream (anthropics/claude-code): worktree-isolation guard refuses `cmd <path containing
  "git">; echo rc=$?` as "names git in a form too complex to verify" on 2.1.288 although no git runs; quoted
  "rc=$?" passes. Repro + both arms: docs/research/kb/reports/agents/session-audit-retrieval-misses-2026-10-03f.md
  R3. Search existing issues first (gh api '/search/issues?q=repo:anthropics/claude-code+"too complex to verify"').`

## Not findings (checked, ruled out)

- `git rev-parse --short a b` → rc 128 [2155]: a git usage slip, not a retrieval gap.
- `index.lock` commit failure [4779]/[4785]: caused by the concurrent push's hook; the session diagnosed it in one
  call.
- `tick.py` auto-backgrounded at the 120 s default [4798]: already carried by memory
  `feedback_bash_slice_needs_explicit_timeout.md` — a repeat-offender item, not a retrieval miss.
- `claude agents --json` top-level array and missing keys: handed by the `/loop` prompt itself [19] ("use .get").

Status: COMPLETE. 11 findings (HIGH 1, MEDIUM 6, LOW 4); 11 FIX-NOW lines, 1 PLAN item.

## GitHub repos touched

_None._ (Only local files, the local transcript, and the on-disk KB harness-docs corpus were read; no GitHub
repository source, issues or docs were queried.)
