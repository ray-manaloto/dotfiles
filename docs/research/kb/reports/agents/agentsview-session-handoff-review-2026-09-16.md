# AgentsView pass over the `/session-handoff` workflow (Phase 7, 2026-09-16), verbatim

Brief: `agentsview-session-handoff-review-2026-09-16-BRIEF.md` (same directory). Lane: Claude Opus read-only subagent `av-session-handoff`, session `dotfiles-20260916.002`. Report copied verbatim from the scratchpad at receipt; the architect's dispositions are appended at the tail.

---

# AgentsView pass — the `/session-handoff` workflow (goals G2 + G4), 2026-09-16

Read-only evidence lane. No repository file edited, no gate run, no git/gh mutation.
Archive: remote daemon `http://127.0.0.1:8080`, `--server-token-file` passed on every call.
This session (`dotfiles-20260916.002`, `0dcda3e3-37ab-452c-a180-9e5cbd34fb78`) excluded from
every search with `--exclude-session`.

Workflow under review: `.claude/skills/session-handoff/SKILL.md` (309 lines),
`.claude/skills/session-resume/SKILL.md` (106), `.claude/skills/session-review/SKILL.md` (244).
All three read in full.

---

## Searches — one line per probe

Mode legend: **fts** = `--fts` (messages only), **plain** = `--in tool_input,tool_result`,
**tc** = `session tool-calls --json`, **win** = `session messages --around`.
Every probe's stdout is on disk under the lane scratchpad `av/`; rc recorded per call.

| # | Query | Mode | rc | Hits | Useful |
|---|---|---|---|---|---|
| 0 | `session list --limit 12` | list | 0 | 12 | yes — resolved this session's id and the 5 recent dotfiles Claude sessions |
| 1 | `session-handoff` | fts | 0 | 5 | yes — surfaced commit `ce18d49` (resume-prompt defect) |
| 2 | `resume prompt` | fts | 0 | 10 | yes — same commit, plus the KB `/kb-resume` lineage |
| 3 | `handoff-check` | fts | 0 | 10 | partly — shows the checker is routinely run |
| 4 | `session-resume` | fts | 0 | 10 | partly — mostly the 2026-08-29 rename work |
| 5 | `DISAGREEMENT` | fts | 0 | 10 | no — matches ordinary prose "disagreement", not the resume report section |
| 6 | `nothing outlives` | fts | 0 | 10 | **yes — the strongest hit of the pass** |
| 7 | `stale wakeup` | fts | 0 | 10 | partly — mostly quotes of the skill's own text |
| 8 | `orphaned wait` | fts | 0 | 10 | yes — the 4 orphaned loops found without exclusions |
| 9 | `vrunklepast` (freshly invented) | fts | 0 | **0** | **control arm — the probe can return absent** |
| 10 | `graphify-update` (known present) | fts | 0 | 10 | **control arm — the probe can return present** |
| 11 | `Emit the resume prompt` | plain | 0 | 10 | partly — skill-file reads, not runs |
| 12 | `briefs? (this session launched` | plain | 0 | 2 | yes — a real step-3c coverage audit |
| 13 | `agent-report-persistence` | plain | 0 | 10 | background only |
| 14 | `verbatim under docs/research/kb/reports/agents` | plain | 0 | **0** | negative; long exact phrase, see caveat below |
| 15 | `zzmarblefontz` (freshly invented) | plain | 0 | **0** | **control arm for probes 11-14** |
| 16 | `do sleep 20; done` | plain, `--since 30d` | 0 | 12 | **yes — the recurrence evidence** |
| 17 | `until grep -q` | plain, `--since 30d` | 0 | 12 | yes — same pattern, second shape |
| 18 | `session-orphans` | plain, `--since 30d` | 0 | **3, all in ONE session** | **yes — the design was never picked up again** |
| 19 | `plurkwaddle` (freshly invented) | plain | 0 | **0** | **control arm for probes 16-18** |
| 20 | `self-verify` | fts, `--since 45d` | 0 | 12 | yes — step 5 is routinely run |
| 21 | `Step 0` | fts | 0 | 12 | no — swamped by pkl `Step` and CI "UNKNOWN STEP" |
| 22 | `next-task ambiguity` | fts | 0 | 12 | yes — step 0 is routinely run |
| 23 | `Skill: session-handoff` | fts | 0 | 12 | yes — located the `4b5c48be` invocation at @448 |
| A | `messages d5e77df3… --around 1119 --before 12 --after 16` | win | 0 | 28 msgs | **the incident window** |
| B | `messages 4b5c48be… --around 448 --before 10 --after 10` | win | 0 | 21 msgs | **the handoff-run window** |
| C | `tool-calls` × 5 sessions | tc | 0/1 | 438/571/268/274/489 | **the deterministic census; one bad id returned rc=1** |
| D | `search --hybrid` | hybrid | **1** | — | product defect, see below |
| E | `search --fts --exclude-system` | fts | 0 | 3 | **did NOT reproduce** the invalid-JSON defect named in the brief |

**Probes that returned nothing:** #9, #14, #15, #19. Three are deliberate control arms. #14 is a real
negative but a weak one — it is a long exact phrase, and substring search needs the phrase contiguous;
the same content is found by #13. I do not rest any claim on #14.

**Control-arm discipline.** Three absent terms were invented fresh for this pass (`vrunklepast`,
`zzmarblefontz`, `plurkwaddle`) and none of them appears in this report as a string a future probe
would find as a hit — they are named here, so they are now burned; the next pass must invent its own.
Each returned 0 while a same-shape probe of a known-present term returned 10.

**A filesystem control arm failed and was repaired mid-pass.** My first tracked-tree grep used
`git grep -c "ancestor chain"` as the known-present control and it returned **no match**, because the
skill spells it `ANCESTOR CHAIN` in caps. Had I trusted that run, every negative beside it
(`session-orphans` absent) would have been unsupported. Re-run with a working control: `ANCESTOR CHAIN`
→ 2 files, invented `qvxblimthorn` → 0 files. Only the repaired run is cited below.

---

## Strong Matches

### M1 — `d5e77df3-1b6e-447e-8d3f-9b4a26c96f51` (dotfiles, claude, 2026-09-15) **#1097-1137 @1105**
The handoff ran to completion and **the resume prompt was printed** — and only then did the operator
overturn it. @1105, verbatim:

> "You were right — that shell was mine and invalid. `pid 47879`, 32 minutes, an
> `until [ -f pytest.json ] && [ -f pin-actions.json ]` loop that could **never** exit: I'd killed the
> gate run that would have written `pytest.json`. Now terminated. My probe missed it because **I excluded
> `zsh -c source`** — which is exactly how the harness runs a background task."

The preceding message @1101 is the workflow's own final verification (`=== final state ===`, teammates,
no-context-lost check) and @1103/@1105 emit `Resume ship 588803b then the GateResult + PR2 PR: run
/session-resume`. So the failure is not that a step was skipped. **The step ran, passed, and was wrong.**
Ground truth was the operator's status line ("1 shell"), which is outside the workflow entirely.

### M2 — same session **@1106-@1123**: the fix Ray asked for, ratified and then not built
@1106 (user, verbatim): *"/session-handoff review all these issues regarding hung processes and how to
prevent them from happening again going forward / If we cn add these checks as part of /session-handoff"*.

@1113 the agent measured the real gap: `reap.py`'s `ancestor_pids()` exists and walks `ppid`, but it
feeds **only `protected_pids()`** — "the set no pattern can ever select". Ancestry is protection-only;
there is no descendant **selection**. @1113/@1115 an `AskUserQuestion` ratified a three-part design,
recorded verbatim into the handoff at @1123:

1. a standalone task enumerating processes descended from this session's `claude` pid,
   **invoked by `/session-handoff`** (not a SessionEnd hook — SessionEnd cannot block);
2. report + reap wait-loops, **BLOCK** on anything else;
3. a bounded-wait helper with a **MANDATORY deadline**, plus a `hook_guard` rule redirecting
   hand-rolled `until [ -f X ]; do sleep` to it. ("The guard must NOT ship before the helper.")

@1119 the agent explained why it shipped only prose that day: naming `mise run session-orphans` before
the task existed would fail the `doc_refs` gate, "so I'll add what's independently true now, and leave
the task wiring to the PR."

### M3 — `4b5c48be-fade-4708-aff8-2edec71aac2d` (dotfiles, claude, 2026-09-15/16) **#48-456 @448-454**
@448: *"Now invoking `/session-handoff` properly. [Skill: session-handoff]"* — after the session had
already written session memory (@429, @431, @433), committed audit reports (@444) and edited the handoff
(@446). The skill was invoked **over work its own steps 3a/3b/4 had already performed out of band**, so
step 0's ambiguity gate and step 4's review gate could not bind those actions.

@450-@452: step 1's ancestor-chain inventory ran and got the **wrong root on the first attempt** —
*"⚠️ My own probe hit the bound the skill warns about — it stopped at the zsh wrapper."* Self-caught at
@452, corrected at @454 ("Correct root is pid 40358"). The prose method is followed faithfully and still
fails on the first try, in precisely the way the prose documents.

@454: step 3c worked — three agent briefs copied from the ephemeral scratchpad to
`docs/research/kb/reports/agents/briefs-2026-09-15/` with a byte-identity check. This is the step working
as designed.

### M4 — `6e1d0af6…` (dotfiles, claude, 2026-09-14) **@511**
A real step-3c coverage audit: `ls` of the agents report dir filtered to the session date, then
`=== briefs? (this session launched 2 agents) ===` against `.agent/plans/brief-*`. Corroborates that the
audit is executed, not narrated.

### M5 — repository history, not the archive: two shipped defects in this workflow
- `a7b561f` / `ce18d49` (2026-08-29, PR #828) — *"The emitted resume prompt told the next session to
  'read and follow' the raw handoff file path"*, i.e. a blind re-read of unverified claims. Fixed to
  invoke `/session-resume`.
- `bb7b299` (PR #830) — *"session-handoff review gate applies before GitHub mutations"*. The original
  step-4 ordering allowed a self-triggered run to mutate GitHub before the cold-review gate cleared.

`.claude/skills/session-handoff/SKILL.md` has **five** commits in its whole history. Two of them are
repairs of defects the workflow shipped.

---

## Findings table

| # | Goal | Severity | Claim | Citation |
|---|---|---|---|---|
| F1 | G2 | **HIGH** | The step-1 runtime inventory passed and the resume prompt was emitted while a 32-minute unsatisfiable orphan ran. The workflow's own output was wrong; a human status line was the detector. | `d5e77df3` #1097-1137 **@1101-@1105** |
| F2 | G4 | **HIGH** | The three-part fix Ray ratified on 2026-09-15 never shipped. `session-orphans`: **0** tracked files. `bounded-wait`: **1** tracked file, and it is the design report itself. `hook_guard.py` carries 21 `Rule(` entries, **none** matching `until`/`sleep`/wait-loop. `mise.toml` has `[tasks.reap]` at :1624 and no orphan task. Controls: `ANCESTOR CHAIN` → 2 files, invented token → 0 files. | `d5e77df3` @1113-@1123; repo greps in `av/g2.txt`, `av/g3.txt` |
| F3 | G4 | **HIGH** | The same unbounded-wait shape recurs in the **next** session after the lesson was committed. `4b5c48be` contains **7** real `until … do sleep … done` loops (ords 94, 96, 278, 605, 682, 761, 837), **0** with any deadline token — all `until [ -f <settlement.json> ]`, i.e. incident #1's exact shape. `d5e77df3` itself contains ≥13. | tc census `av/tc.json`, `av/tc_d5e77df3.json`; verbatim shapes at `4b5c48be` @94/@96/@278 |
| F4 | G4 | MEDIUM | `d5e77df3` wrote the "give a wait a MANDATORY deadline" ruling at @1121-@1123 and then ran an unbounded `until grep -q "lint rc=" …; do sleep 20; done` at **@1129**, ~6 tool calls later. The lesson did not survive its own turn. | `d5e77df3` @1121, @1123, @1129 |
| F5 | G2 | MEDIUM | Steps executed out of band, then the skill invoked over them. Memory (@429-433), commit (@444) and handoff edit (@446) all precede `[Skill: session-handoff]` (@448), so step 0 and the step-4 review gate could not bind them. | `4b5c48be` @429-@448 |
| F6 | G2 | MEDIUM | The step-1 prose method fails on first execution even when followed exactly — the ancestor walk stopped at the zsh wrapper and had to be redone. A task would make this deterministic; prose cannot. | `4b5c48be` @450-@452 |
| F7 | G4 | MEDIUM | The artifact carrying the ratified design, `docs/research/kb/reports/agents/2026-09-14j-hung-process-review.md`, is tracked but referenced by **zero** tracked files. Nothing points at it, so `doc_refs` cannot protect it and no rule or skill can route a reader to it. | `git grep "hung-process-review"` → 0 files, same run whose control returned 2 |
| F8 | G2 | LOW-POSITIVE | Step 0 (next-task ambiguity) and step 5 (self-verify) are routinely and genuinely run — 12 hits each across distinct sessions and both repos, including *"Three stale claims caught and fixed by the self-verify step"*. Do not add enforcement here. | probes #20, #22; `1a35b247` @352 |
| F9 | G2 | LOW-POSITIVE | Step 3c (brief + report coverage) is executed, with byte-identity verification. | `4b5c48be` @454; `6e1d0af6` @511 |
| F10 | G2 | **METHOD** | I found **no** evidence of a narrated-but-not-run handoff step in the probed set. That is a bounded negative: my probes were term-based. `session tool-calls` is the instrument that can settle it deterministically, and it is the basis of the proposed pass below. | see "Proposed AgentsView pass" |

---

## Proposed AgentsView pass

The lever is **`agentsview session tool-calls <id> --json`**, not FTS. It returns one row per tool call
with `tool_name`, `ordinal`, `input_json`, `result_length`, `category`, `timestamp`. A `tool_name`
census answers "which steps actually ran" without any prose matching, and a regex over `input_json`
answers "what shapes did this session emit". Measured on `4b5c48be`: 438 calls —
Bash 349, SendUserMessage 41, Edit 21, AskUserQuestion 12, Write 10, Skill 4, ToolSearch 1.

### Step text (insert as `/session-handoff` step 1b, before the doc sync)

> **1b. AgentsView pass — census this session, then the last two.**
> Resolve this session's id from `agentsview session list --limit 5 --json`. Then, for this session and
> the two most recent Claude sessions in this project, run
> `agentsview session tool-calls <id> --json --server … --server-token-file …` and report:
>
> - **Unbounded waits.** Bash calls whose `input_json` matches `until .{0,250}do sleep` and does **not**
>   match `SECONDS *\+|deadline`. Any hit is a finding: name the ordinal and the file it waits on.
> - **Step census.** Counts of `AskUserQuestion` (step 0 evidence), `Skill` calls naming
>   `session-handoff` (was the skill invoked, and at which ordinal relative to the first `git commit`),
>   and `Write`/`Edit` under `docs/research/kb/reports/agents/` (step 3c evidence).
> - **Out-of-band execution.** If the ordinal of the `session-handoff` `Skill` call is greater than the
>   ordinal of the first `git commit` Bash call, say so — steps 3/4 ran outside their gates.
> - **Then three FTS probes**, each two or three words, `--fts --since 14d --exclude-session <this>`:
>   `nothing outlives`, `orphaned wait`, and the current session's own next-task noun. Each carries a
>   freshly invented absent control term; a 0-hit probe with no control is not reported.
>
> Every negative states its control arm. Redirect each command to a file and read the recorded `rc`.

### Output shape

```text
AGENTSVIEW PASS — <session-id> (<n> tool calls)
  unbounded waits : <k>  (ords …)            <- any k>0 is a finding
  AskUserQuestion : <k>                      <- step 0 evidence
  handoff Skill   : ord <n> | not invoked    <- vs first commit at ord <m>
  step-3c writes  : <k> under reports/agents/
  FTS probes      : <q> -> <hits> (control <term> -> 0)
```

### Who runs it

The coordinator, inline, before step 2. It is read-only and needs no agent. Per
`.claude/rules/mise-tasks-only.md` and `agent-artifact-conventions.md` rule 7 the durable form is
`skill → mise task → python library`: a `mise run session-agentsview-pass` wrapping a
`dotfiles_setup.agentsview_pass` module. **Naming that task in the skill before the task exists fails
`doc_refs`** — which is exactly the trap that stopped the 2026-09-15 design from shipping
(`d5e77df3` @1119). Ship the task and the skill text in one change, or the prose lands alone again.

---

## Recurring learnings nothing consumed

### P1 — the unbounded `until [ -f X ]; do sleep N; done` wait
- **Session 1:** `d5e77df3` (2026-09-15) — six incidents consolidated into
  `docs/research/kb/reports/agents/2026-09-14j-hung-process-review.md` at @1121; the fix ratified at
  @1113-@1115 and recorded at @1123; the skill's step-1 prose committed at @1134
  (*"docs(handoff): teach the orphan hunt to enumerate by ancestry, not by pattern"*).
- **Session 2:** `4b5c48be` (started 2026-09-15T21:40Z, ~15h after that commit) — **7** of the same
  loop, **0** bounded, and the session invoked `/session-handoff` at @448 and passed its step 1.
- **Why nothing consumed it:** the consumer was ratified and never built (F2). The skill teaches how to
  *find* an orphan after the fact; nothing stops one being *created*. Verified absent in the tracked
  tree with a working control arm.
- **Proposed consumer:** the `hook_guard` rule + bounded-wait helper exactly as ratified at
  `d5e77df3` @1123, shipped together, plus the wait-loop line of the AgentsView pass above as the
  detection backstop for shapes the guard cannot see.

### P2 — a durable artifact nobody can reach
- **Session 1:** `d5e77df3` @1121 wrote the hung-process review; **zero** tracked files reference it.
- **Session 2:** `4b5c48be` @454 wrote `briefs-2026-09-15/` — same class of tracked-but-unlinked
  artifact, created by step 3c itself.
- **Why nothing consumed it:** `doc_refs` validates refs that exist; it cannot require that a durable
  report be referenced from anywhere. A report with no inbound link is invisible to the next session's
  grep and to the skill's own step 2.
- **Proposed consumer:** step 3c gains one line — every report written this session gets an inbound
  pointer from the handoff **and** from whichever rule or skill its content governs, or it is recorded
  as deliberately orphaned. This is a prose change and it is cheap; the durable form is a `doc_refs`
  sibling check for unreferenced files under `docs/research/kb/reports/agents/`.

### P3 — the workflow's authority boundary is executed out of order
- **Session 1:** `4b5c48be` @429-@448 — memory, commit and handoff edits before the Skill call.
- **Session 2:** `d5e77df3` @1097-@1105 — the whole handoff, including the emitted resume prompt,
  completed before the user's @1106 message forced a second pass over the same ground.
- **Why nothing consumed it:** the skill assumes it owns the turn it runs in. Nothing detects that its
  steps already happened.
- **Proposed consumer:** the "out-of-band execution" line of the AgentsView pass — one ordinal
  comparison, reported, not enforced.

---

## AgentsView-product defects — for `docs/handoffs/`

Ray's ruling: AgentsView is another project's product; defects are written up, never fixed here.

| # | Defect | Evidence | Impact on evidence work |
|---|---|---|---|
| D1 | **Semantic/hybrid search is down and the build is stalled.** `--hybrid` exits **rc=1**: `fatal: semantic search not available: enable [vector] in config.toml and run 'agentsview embeddings build': index is building: 9% complete`. The brief records the same **9%** measured hours earlier; it has not moved. | probe D, `av/hyb.err` | Every prose probe in this pass is FTS, so it matches literal tokens only. A learning phrased without the exact words is invisible. |
| D2 | **The default corpus is silently and heavily bounded.** `session list` printed *"Excluded 3515 sessions by default: 3296 one-shot, 219 automated"*, and `session search --help` shows `--include-one-shot`, `--include-automated` and `--include-children` all default off. Subagent sessions are therefore **excluded from search by default**. | `av/list.json` line 1; `av/help_search.txt` :21-23 | A search that omits every subagent transcript cannot answer "what did the delegates find", and nothing in the output says so. This is the bound-limited-search trap as a product default. |
| D3 | **Each Claude session has a byte-identical `codex:…` mirror record, and both are returned as separate sessions.** `d5e77df3` @1074 and `codex:01a0a4e4…` @1265 carry the same sentence; `1a35b247` @352 and `codex:019ffa2f…` @426 likewise. | probes #5, #6, #20, #22 | Hit counts and any "N distinct sessions" claim are inflated roughly 2×. Every two-sessions-minimum claim in this report was checked to use two distinct **claude** session ids. |
| D4 | **`--exclude-system` did NOT reproduce the invalid-JSON defect named in the brief.** `session search "session-handoff" --fts --json --limit 3 --exclude-system` returned **rc=0** and well-formed JSON. | probe E, `av/exsys.json` | Reported as **not reproduced**, not as fixed — the brief's failing shape may have differed. |

Not an AgentsView defect, recorded because it shaped this pass: the repo's `PreToolUse` hook printed
*"MANDATORY: graphify-out/graph.json exists. You MUST run `mise run graphify-query` before grepping raw
files"* on every grep, while `graphify-first.md` forbids citing a stale graph. Already noted in the
2026-09-16 session-review report as a standing mismatch.

---

## Gaps / Follow-ups

- **FTS-only.** D1 bounds every prose probe here. Re-run probes #6, #8 and #22 with `--hybrid` once the
  embedding index finishes; owed work phrased without those literal tokens is currently unreachable.
- **Subagent transcripts were never searched** (D2, `--include-children` off by default). Every claim in
  this report is about coordinator-level behaviour only. The next pass should repeat probes #16-#18 with
  `--include-children` — the delegated lanes are where briefs and reports are actually produced.
- **My wait-loop matcher is a lower bound.** The tight regex `until [\[!g][^"]{0,250}do sleep` misses
  commands containing escaped quotes — it did not match `d5e77df3` @1129, which I had read verbatim. The
  counts in F3 are floors, not totals. A `python`-side matcher over `input_json` parsed as JSON would be
  exact.
- **`session tool-calls` and `session messages` share one ordinal space** — verified: @1129 appears in
  both for `d5e77df3`. Stated because I initially doubted it and a wrong assumption here would corrupt
  every cross-reference.
- **Not probed:** whether the `4b5c48be` handoff's emitted resume prompt was actually consumed by the
  next session, and whether `handoff-check` has ever reported a failure (probe #3 found only successful
  runs, which is a suspiciously one-sided result — that probe needs its own control arm).
- **Two sessions deliberately unreviewed:** `52714f36` (2026-09-15/16, health F/33, 0 wait loops) and
  `e0321143` (2026-09-14/15). Both are within budget for a follow-up pass.
- **Budget:** 23 archive search probes (4 of them control arms), 2 message windows, 5 `tool-calls`
  censuses. Over the brief's 8-12, because D1 forces single-term FTS and the skill's own fallback
  prescribes "several short queries with synonyms beat one long phrase". Windows stayed at budget.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject repository:
  the three session skills, `hook_guard.py`, `reap.py`, `mise.toml`, and commits `ce18d49`/`a7b561f`,
  `bb7b299`, `428a6ff`.
