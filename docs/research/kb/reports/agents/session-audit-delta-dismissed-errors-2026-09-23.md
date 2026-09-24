# Session audit (DELTA) — dismissed errors and repeated mistakes, 2026-09-23 (Brief S1)

Status: COMPLETE (written incrementally). Session `a6750a24-770a-419d-996e-985bd27de611`.

Scope: commits `5e258baf..48a1ee12` (`86324c6a`, `b7c59920`, `48a1ee12`) and main-transcript JSONL ordinals
2157-3170 (Ray's "have agents review this session and ensure the following" is ordinal 2157). Subagents started
after 2157: M `a801a016`, N `a152a5ca`, O `afa9fe36`, P `af0a6178`, Q `a5ecbec5`, live wrapper tests `a868a9b5`
+ `a7cdee83`, Fable R `afbdb631`. S1-S4 excluded (running concurrently). Method: Brief M verbatim, plus a
check that every Brief M finding marked fixed is fixed in the tree now.

## Method

- Timeline extractor over the main JSONL from ordinal 2157 (scratchpad `s1/tl.py`), plus a full list of every
  tool_result in the delta (`s1/allres.txt`, 105 rows): each non-zero rc, `is_error`, WARN, DRIFT, BLOCK, deny.
- For each in-scope subagent: every `is_error` tool_result (6 rows), with the command that produced it.
- Attachment census for the delta: hook messages, silent-turn reminders and queued commands.
- Each candidate was checked against the tree at `48a1ee12`, `task_plan.md` (sha `4a077b45…`), the handoff
  `.agent/plans/session-2026-09-23d.md`, memory, and the 18 published ticket bodies.
- Control arm for the extractor: it surfaced the known delta errors (plan-pointer rc=1 at 2616, lint/verify rc=1
  at 2837, the AskUserQuestion deny at 2991), so it discriminates.

## Findings (only DISMISSED, unrecorded, or REGRESSED)

### S1-1 (MEDIUM, REGRESSION of M-7, third occurrence) — the handoff is stale against the branch tip it hands off
- Evidence: `.agent/plans/session-2026-09-23d.md` was last written at 23:27 local (04:27Z), before the #1351 ticket
  publication (main 3043-3067) and the second attest (3080). Against the tree now:
  - `:4-5` cites plan sha `5ab1a140…`, but `shasum -a 256 task_plan.md` = `docs/agents/plan-pointer.json` =
    `4a077b45de2f…` (probed now).
  - `:14` HEAD `b7c59920`, but HEAD is `48a1ee12`.
  - `:17` "STALE: plan `5ab1a140…` vs attestation `dc4b9265…`", but `.plan-attestation` = `4a077b45…` = the plan.
    The operator attested twice (main 2920 → `5ab1a140`, 3080 → `4a077b45`).
  - `:42` still owes `! mise run plan-attest`, which was done at 3080.
  - `:19` says graphify is "fresh (rc=0)", but it is stale now (S1-3).
  - `:20` dismisses a census bug (S1-4).
  - "What shipped" (`:23-30`) omits `86324c6a` (the wrappers now launch through `mise exec`) and the 18 tickets.
  - `:34` says briefs "A-Q", but R and S1-S4 exist.
  - Memory has the same staleness: `project_session_2026-09-23.md:65` says "Next step: Ray runs
    `/mattpocock-skills:to-tickets #1351`", and the `MEMORY.md` START HERE hook says "/to-tickets #1351 (Fable)".
    Both steps are done.
- This is the M-7 class again: M-7's FIX-NOW sha edit held until the next plan edit (3064). `handoff-check` still
  cannot see it, because the M-7 PLAN is ticket D3 = dotfiles#1354 (body line 22 carries the arm), which has not
  landed.
- Control arm: `handoff-check` passes on this handoff (main 2899). The staleness shows only when you compare
  against the files directly, and the probes above did exactly that.
- Disposition: **FIX-NOW** (in the final `/session-handoff` write, after every other edit to `task_plan.md`):
  - `:4-5`: use the sha in `docs/agents/plan-pointer.json` at write time (now
    `4a077b45de2f08ac4628b488c30855feba67fc6c403c367487cd226c1ee5f534`).
  - `:14`: "HEAD `48a1ee12` (+`b7c59920`, `86324c6a`, `5e258baf`, …)", or the final HEAD if the handoff commits.
  - `:17`: "`| plan attestation | owed only if `shasum -a 256 task_plan.md` ≠ `.plan-attestation` at /clear;
    D4 deny live until dotfiles#1352 |`".
  - `:42`: write the same condition, not an unconditional owe.
  - `:19` and `:20`: see S1-3 and S1-4.
  - "What shipped": add "`86324c6a`: all 12 codex wrappers launch `PLANNING_DISABLED=1 mise exec -- codex exec`;
    contract `workflow.codex-lane-planning-isolation` re-bound; two live runs coordinator-verified (0.154.0, then
    0.156.1)" and "#1351 → 18 tickets, dotfiles #1352-#1360 + knowledge-base #802-#810, **39** native blocked_by
    edges".
  - `:34`: "A-S".
  - Memory `:65` and the `MEMORY.md` START HERE hook: point at the Current Phase step 2 (codex step-2a remainder).

### S1-2 (MEDIUM, repeated 5x in the delta, once AFTER the fix) — M-4's PLAN half (the zsh `=`-expansion guard) never landed
- Evidence (every call `is_error=true`, and the rest of each compound command was lost):
  - N `a152a5ca` 107 (03:45:47Z, `echo ======`)
  - P `af0a6178` 57 (03:45:08Z)
  - Q `a5ecbec5` 119 (03:47:40Z, `echo =====`) and 168 (03:49:13Z)
  - Fable R `afbdb631` 53 (**04:30:01Z**): `…; echo ======; cd … && gh issue view 1351 … > …`. The `gh issue view`
    never ran, and R re-ran it at 65.
- M-4's FIX-NOW memory note landed at main 2281 (03:54:33Z): `feedback_zsh_equals_expansion.md`, `MEMORY.md:99`,
  and the handoff trap `:55`. **R's failure came 36 minutes after it**, so memory and the handoff do not reach a
  delegate.
- M-4's PLAN text was never added to the task plan: a `hook_guard` rule plus a SubagentStart contract line. Probes:
  - `grep -n -i -E "zsh|equals" task_plan.md` → 3 unrelated hits (:816, :1679, :1751); the Session follow-ups list
    (:695-714) has no M-4.
  - `hook_guard.py` has no `=`-expansion rule: 0 hits, with control `no-verify` = 8 hits.
  - The SubagentStart contract this lane received has no zsh line.
- Disposition: **PLAN** (no grilling). Add under "Session follow-ups" (task_plan ~:704): "- **M-4 / S1-2 (zsh
  `=`-expansion), 15 lane failures on 2026-09-23 (10 before Brief M, 5 after, one after the memory note):**
  `hook_guard` rule denying an unquoted argument word matching `^={2,}` to `echo`/`print` (test: `echo '===='`
  passes, `echo ====` denies), plus one line in the SubagentStart contract (`.claude/settings.json`, bound by
  `hook_selfcheck`). Memory does not reach delegates; the PreToolUse hook does, because it fired in every delegate
  this session."

### S1-3 (MEDIUM, REGRESSION of M-8; its PLAN half was dropped) — the graph is stale again, and the handoff says fresh
- Evidence: `mise run graphify-health` now (scratchpad `s1/gh.log`) → `stale (runtime=0.9.65) graph built at
  762396bc but .agents/skills/session-handoff/SKILL.md changed since (HEAD 48a1ee12, 40 corpus file(s))`, **rc=3**.
  Control arm: the same probe returned `fresh`, rc=0, at main 2328, so it can report fresh.
- M-8's FIX-NOW (`graphify-rebuild`, main 2283) ran before three more commits (`5e258baf`, `86324c6a`,
  `48a1ee12`). The handoff `:19` still says "fresh (rc=0)".
- M-8's PLAN (put graph health in the `session-state` live probes) is not in the task plan: the Q5 bullet at :566
  names no graph probe, and `graphify-health` appears only at :777 and :1748 (archive).
- The PreToolUse graphify hook fired 31 times in the delta. The main session ran 0 `graphify-query` and 1
  `graphify-rebuild`.
- Disposition: **FIX-NOW:** run `mise run graphify-rebuild` as the LAST repo-changing step before `/clear` (after the
  handoff commit, if any), then write the real `graphify-health` rc into the handoff's graphify row.
  **PLAN** (append to task_plan :566, the Q5 bullet): "…live probes include `graphify-health` (M-8/S1-3): resume
  prints `stale` with its corpus-file count, and the handoff records the rc taken after its own last commit."

### S1-4 (MEDIUM, DISMISSED in the handoff) — `session-orphans` blocks on its own pipeline's `grep` and `cut`
- Evidence:
  - Main 2691: after the reap, `mise run session-orphans 2>&1 | grep -E …` → `BLOCK OTHER 68635 (1s, S) ugrep …
    -E WAIT-LOOP:|OTHER:|…` and `session-orphans: BLOCK — allow every OTHER pid explicitly with --allow`.
  - Main 3121: the same shape, `OTHER: 2`, own `ugrep`.
  - Main 3126/3129: re-run redirected to a file → `OTHER: 0`.
  - The handoff `:20` records it as "the only OTHER is the census's own grep". The bug is noted in prose there,
    but it is not a PLAN line and not fixed.
- Cause: `build_plan` protects only the caller's ancestors (`own_chain`) and descendants (`own_subtree`), at
  `python/src/dotfiles_setup/session_orphans.py:146-148`. The processes of a `| grep | cut` pipeline are children
  of an ancestor shell, not of the caller, so they classify as OTHER.
- Reproduced now, both arms: three piped runs each list this lane's own `ugrep` and `/usr/bin/cut -c1-140`, 2s old,
  as `BLOCK OTHER`. The file-redirected run lists no ugrep of this lane. (Both arms also list the concurrent
  S2-S4 lanes' processes, which is expected mid-handoff.)
- `/session-handoff` checklist `SKILL.md:337` requires "no unallowed OTHER". A piped census therefore fails the
  handoff falsely and trains the operator to wave BLOCK through, which is what the handoff line does.
- Recorded nowhere: `grep -n -i -E "own grep|sibling|pipeline" task_plan.md` → only unrelated hits; memory → 0.
- Disposition: **PLAN** (no grilling): "- **S1-4 `session-orphans` self-detection:** also protect processes in the
  caller's own process group (or the other children of the nearest ancestor shell). Test: `census | grep | cut` →
  OTHER 0. Control: an unrelated background child of the session still BLOCKs. Until fixed, the handoff runs it
  redirected to a file (`> $S/orph.log`), never piped." **FIX-NOW:** handoff `:20` → "session-orphans
  (file-redirected): <real counts>; a piped run lists its own grep (S1-4, planned)".

### S1-5 (LOW, unrecorded) — `plan-pointer` rewrites a tracked file on every run, even when nothing changed
- Evidence:
  - Main 3118-3121: the `/session-handoff` snapshot ran `mise run plan-pointer`, and `git status` showed
    ` M docs/agents/plan-pointer.json`.
  - 3129: the diff lines carry the identical `plan_sha256` prefix `4a077b45de2f08ac4628b488c30855feba67fc6c403`.
  - 3134: the coordinator discarded the change with `git checkout --`.
  - Cause: `plan_pointer.py:51` always builds the payload with `recorded_at=now()`, and `:57` writes
    unconditionally.
  - The skill mandates the run (`SKILL.md:49`, checklist `:336`), so every handoff dirties the tree on a no-op.
    (Not re-run here, because running it writes a tracked file; the evidence is code plus the transcript diff.)
- Ticket K5 = knowledge-base#806 (draft `:354-379`) carries the "plus a timestamp" design forward and has no
  unchanged-digest arm. Recorded nowhere: `grep -i "recorded_at|idempot"` in task_plan and memory → 0. Control: the
  draft grep does find "idempotent" for K4.
- Disposition: **PLAN**. Add one acceptance line to knowledge-base#806 (coordinator comment, for Ray to approve):
  "- [ ] Unchanged-plan arm: re-running `plan pointer` with no change to either digest or the active phase leaves
  the pointer byte-identical; control: a one-byte plan edit rewrites it." Add a task_plan follow-up line
  "- S1-5: `plan-pointer` timestamp churn (`plan_pointer.py:51-57`) → KB#806 acceptance".

### S1-6 (LOW) — the ticket publication reported 42 blocked_by edges; there are 39
- Evidence:
  - The count 42 appears in the message to Ray (main 3071), the turn text (3075) and the `48a1ee12` commit body
    (line 4: "42 native blocked_by edges written").
  - The intended count is 39: the dry-run list at 3038 sums to 39.
  - The written count is 39: `  edge … rc=0` lines at 3046.
  - The live count is 39: the sum of `gh api repos/<r>/issues/<n>/dependencies/blocked_by --jq length` over all 18
    issues (probed now: 0+6+2+1+1+1+2+4+6 for dotfiles, 0+1+1+2+1+2+5+2+2 for KB).
  - So nothing is missing. The reported number was never measured (`probes-need-a-control-arm.md` rule 6).
- Disposition: **FIX-NOW:** use 39 in the handoff and memory (S1-1), and correct the count for Ray in the handoff
  summary. The commit body stays: the branch is unshipped, but rewriting a non-tip commit is not worth a rebase.
  Put the correction in the PR body at `ship`. No PLAN.

### S1-7 (LOW, instance fixed, class unrecorded) — `grep PAT $(…)` with an empty substitution hung for 60 minutes
- Evidence:
  - Lane I `a76afa51` 325 (03:12:15Z) ran
    `grep -l '"fable-orchestrator:codex-implementer"' $(grep -rl "2026-08-29T19:08" $P --include='*.meta.json' 2>/dev/null) 2>/dev/null | head -2; …`.
  - At 328 the call was moved to the background at 120s. The lane finished at 04:12Z and left it running.
  - The main session found pid 50871 at 59m40s (2666), dry-ran `mise run reap` (2671) and SIGTERMed 2 pids (2685).
  - Mechanism: the inner search matched nothing, so the outer grep got no file operands and read stdin. The
    backgrounded tool call never closes stdin.
- Reproduced now, both arms:
  - `sleep 4 | { grep -l foo $(true); … }` → grep finished after **4s** (it waited for stdin EOF).
  - Control `grep -l foo /dev/null $(true)` → **0s**.
- Brief M's scope included lane I but did not flag this. The handoff `:20` records only the instance ("A 60-min
  hung grep left by a lane was reaped"). Class recorded nowhere: grep of memory, `.claude/rules`,
  `docs/rules-evidence`, task_plan and the handoff for "reads stdin" / "empty $(" → 0. Control: "word-split" → 2
  memory files.
- Disposition:
  - **FIX-NOW:** add a handoff Trap. `MEMORY.md` is at 24,965/25,000 bytes, so it goes in the handoff rather than
    a new index row: "- **`grep PAT $(cmd)` with an empty `$(cmd)` reads stdin.** In a Bash call that auto-backgrounds
    at 120s, stdin never closes, so it hangs forever (60 min, lane I, 2026-09-23). Always pass `/dev/null` as a
    file operand (`grep -l PAT /dev/null $(…)`) or use `find … -exec grep -l PAT {} +`."
  - **PLAN:** fold into S1-2's `hook_guard` ticket as a second rule, "a `grep`/`rg` whose only file operand is a
    `$(…)` substitution" (test both arms as above).

### S1-8 (LOW) — M-5's brief half was not applied
- Evidence:
  - M-5's FIX-NOW had two halves: amend the handoff trap, which is done (`:50-52`, and it also names
    `mise run plan-attest`), and add the D4-deny sentence to the common section of every brief until T1 lands.
  - The second half did not happen. The S1-S4 section (`session-2026-09-23d-agent-briefs.md:332-345`) and the
    M-Q common part (:266-279) lack it.
  - R's prompt (main 2954) said the briefs' "D4/operator-only statements are SUPERSEDED by round 4". A lane can
    read that as "the deny is gone", while `.claude/settings.json:31-37` still denies (read now).
  - No in-delta lane hit the deny apart from M itself (M 266, already counted as M-5's fourth instance). The trap
    is live for every brief until dotfiles#1352 lands.
- Disposition: **FIX-NOW:** append to the briefs file's S1-S4 section: "D4 deny is live until dotfiles#1352 lands:
  any Bash command whose TEXT names the attest/selector scripts or `mise run plan-attest` is denied, reads and
  heredoc writes included. Use Read/Edit/Write." No PLAN beyond #1352.

### S1-9 (LOW) — M-2's jq trap was never written down
- Evidence: M-2 called it "memory-worthy" (`([…]|join(",")), (.body|length)`: parenthesise each side of `,` after a
  pipe). No memory file carries it (`ls memory | grep -i jq` → 0; `MEMORY.md` jq grep → 0), and neither does the
  handoff. No recurrence in the delta: the delta's jq uses (2521, 3052) are parenthesised or single-valued.
- Disposition: **FIX-NOW:** one handoff Trap line, because memory is at budget: "- **jq: `,` binds tighter than `|`** —
  write `([.labels[].name]|join(",")), (.body|length)`; the unparenthesised form applies `.body` to the array
  (#1351's length check silently failed that way)."

## Brief M findings: fixed or recorded? (verified in the tree at `48a1ee12`)

| M | Claimed disposition | Verified now | Status |
|---|---|---|---|
| M-1 | PLAN | task_plan:704 ("takes `--cmd`/`--file` … never hide its rc"); handoff Trap :56 | recorded (the rule-doc and guard halves of M-1's text are absent; wording is S4's lane) |
| M-2 | FIX-NOW re-probe; memory-worthy | re-probe done; no memory/trap | partial → S1-9 |
| M-3 | PLAN | task_plan:706-709 | recorded |
| M-4 | FIX-NOW memory + PLAN guard | memory `feedback_zsh_equals_expansion.md` + `MEMORY.md:99` + handoff :55 ✓; guard/contract ✗ | **PLAN dropped; recurred 5x** → S1-2 |
| M-5 | FIX-NOW handoff + briefs | handoff :50-52 ✓; briefs ✗ | partial → S1-8 |
| M-6 | PLAN | task_plan:696 "✅ VERIFIED" — backed by main 2786 (rc 0, 441 B, v0.154.0) and 2837 (rc 0, 138 B, v0.156.1), both coordinator-read files | FIXED |
| M-7 | FIX-NOW sha + PLAN | sha fixed at 2896, then stale again; PLAN = task_plan:698 → dotfiles#1354 body line 22 ✓ | **REGRESSED** → S1-1 |
| M-8 | FIX-NOW rebuild + PLAN probe | rebuild rc=0 at 2328, stale again now (rc=3); probe PLAN ✗ | **REGRESSED** → S1-3 |
| M-9 | none (ship runs the matrix) | branch still unshipped; `86324c6a` ran the full matrix (2873/2891) | holds |
| M-10 | PLAN | task_plan:700 | recorded |
| M-11 / M-12 | PLAN (#1351 T8) | task_plan:702 → dotfiles#1360 body lines 8, 10 (leftover dir moved; stale in-progress markers resolved) | recorded |
| M-13 | PLAN + grilling | task_plan:710 | recorded |
| M-14 | none | repeated in the delta: 7 `silent_turn_reminder` (2411-3047) + 1 no-SendUserMessage reminder (2332) | unchanged by design |

## Accounted for in the delta (fixed or recorded) — NOT findings

| Item | Evidence | Where it landed |
|---|---|---|
| `plan-pointer` rc=1 after the Phase 11 heading lost `NEXT SESSION` | 2616 (`pp rc=1`, output hidden by `> /dev/null 2>&1` but rc read) → diagnosed at 2622 | FIXED at 2628; handoff Trap :53; memory `project_session_2026-09-23.md`; retired by #1354 |
| lint rc=1 (`contract_token_uniqueness`) + verify rc=1 after the wrappers moved to `mise exec` | 2837, 2844 | FIXED at 2870: 6 tokens in `suites.toml` re-bound (6 hits now for the new token, 0 for the old); 2873 token-audit/lint/verify rc=0; pytest rc=0 at 2891; `86324c6a` |
| First live wrapper run on codex 0.154.0 (session PATH predates `disable_tools`) | 2786 | FIXED `86324c6a` (12 wrappers `mise exec -- codex exec`); run 2 at 2837 = 0.156.1 |
| Plugin codex lanes still resolve bare `codex` (`fable-orchestrator` `run-lane.sh:88-91`); S3 ran `codex-cli 0.154.0` | S3 `aa6718fb` (the `codex --version` line) | covered by handoff :18 ("a shell started before `5e258baf` still resolves 0.154.0"); heals at `/clear`. `mise exec` resolves the shim → 0.156.1 (2743), so the `mise run sdlc-team`/`codex-lane` paths are fine |
| AskUserQuestion denied for missing citations | 2991 | FIXED at 2995 (the gate working; 1 deny in 19 asks all session) |
| `git show … for f …` rc=1 | 2472 (the loop's last `[ -e ]` was false) | benign; the 13 stranded 09-02 reports were recovered (2479) |
| PLAN TAMPERED on 11 prompts | 2160 … 2826 | resolved by operator attests at 2920 and 3080; D4 retired by #1352 |
| Stop hook "2 phase(s) still in progress" x14 | 2213 … 3077 | M-11 → #1360 |
| zsh `=` in N/P/Q (before the memory note) | see S1-2 | S1-2 |
| antigravity "BULK work" prompt hint x4 | 2220, 2235, 2410, 2979 | informational plugin hint; not an error |
| O report located in `/var/folders/…/codex-review-final.XXXXXX.…` (the plugin's `mktemp` template kept literal `X`s on BSD) | 2423-2429 | persisted verbatim by the coordinator; third-party cosmetic |

## Summary

9 findings: 0 HIGH, 4 MEDIUM (S1-1 to S1-4), 5 LOW.

- **Two regressions of Brief M fixes, both caused by edits after the fix:**
  - M-7: the handoff is stale again (S1-1).
  - M-8: the graph is stale again (S1-3).
  - Common cause: a FIX-NOW taken mid-session is overtaken by later commits. The handoff's state rows and the
    graph rebuild must be the LAST steps.
- **Two M PLAN halves were dropped:**
  - M-4's guard: the zsh failure recurred 5x, once after the memory note (S1-2).
  - M-8's resume probe (S1-3).
- **One bug dismissed in prose:** session-orphans self-detection (S1-4).
- **Three unrecorded classes:** plan-pointer timestamp churn (S1-5), the empty-`$(…)` grep hang (S1-7), and one
  unmeasured published number (S1-6).
- **FIX-NOW before `/clear`:**
  - handoff rewrites (S1-1, S1-3 row, S1-4 row, S1-6 count, S1-7 and S1-9 traps);
  - `mise run graphify-rebuild` last (S1-3);
  - the briefs sentence (S1-8);
  - memory pointer update (S1-1).
- **PLAN lines:** S1-2 (with S1-7's second guard rule), S1-3 probe, S1-4, S1-5 (KB#806 acceptance). None needs
  `/grilling`. All are mechanical guard/test additions or fold into existing tickets.

Evidence note: `ordinal` = 1-based JSONL line in the named transcript (main unless a lane is named). Lane ids:
M `a801a016…`, N `a152a5ca…`, O `afa9fe36…`, P `af0a6178…`, Q `a5ecbec5…`, R `afbdb631…`, I `a76afa51…`,
S3 `aa6718fb…`. Scratchpad: `…/a6750a24-…/scratchpad/s1/` (`tl.py`, `show.py`, `main.tl`, `allres.txt`,
`suberr.txt`, `gh.log`, `orph-file.log`, `i1360.md`).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1352-#1360 blocked_by counts,
  #1354 and #1360 bodies (M-7/M-11/M-12 fold-ins), via `gh api`/`gh issue view`; repo files and session
  transcripts.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issues #802-#810 blocked_by
  counts, #805/#806 titles, via `gh api`/`gh issue view`.
- [ray-manaloto/fable-orchestrator](https://github.com/ray-manaloto/fable-orchestrator) — installed plugin 1.21.0
  `scripts/run-lane.sh` read locally (bare `codex` resolution); no network call. (The owner is inferred from the
  plugin cache path `fable-orchestrator/fable-orchestrator`; unverified.)

Status: COMPLETE.
