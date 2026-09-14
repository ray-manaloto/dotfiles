# Retrieval-failure audit — 2026-09-14

Read-only audit lane. Objective (operator, verbatim): "information that we had
to research from other past sessions that should have been immediately found
and how to enforce not having to do that again."

**Corpus note:** this session's own transcript
(`6c26be81-8260-48af-b7c8-58eee272c87c.jsonl`) was still being written while
this audit ran — it is a snapshot, not a closed record. The primary evidence
base is `findings.md` (entries C1–C28, this session) and `progress.md`, cross-
read against the memory dir, `.claude/rules/`, `docs/receipts/`, and the
installed graphify graph.

## Part 1 — The retrieval-failure table

| # | Fact | Already recorded at | How re-derived this session | Cost | Class |
|---|---|---|---|---|---|
| 1 | `jdx/mise` has GitHub Issues **disabled** (`has_issues:false`) | `docs/receipts/440.md:247,254` (committed, tracked) | `res-mise-upstream` lane ran `gh api repos/jdx/mise` fresh to answer "can we file an issue" | One live GitHub API round-trip in a delegated lane, plus the coordinator/operator exchange where the operator's own stated belief ("i think it is ok to post to jdx github issues") had to be corrected in-session | (a) recorded but not loaded — `docs/receipts/` is not an eager-loaded tree, and nothing in the eager rule set or MEMORY.md names this fact |
| 2 | `claude-cli` is a graphify extract backend with `pricing: {"input": 0.0, "output": 0.0}` — billed to the Claude Code subscription, not pay-as-you-go API credit | The **flag/pricing detail** was not recorded anywhere; only the adjacent policy ("Claude-only, never auto-keys") was, in `feedback_kb_graphify_claude_only.md` | C27→C28: the coordinator raised a spend objection against `graphify extract` (no total-cost cap flag exists) that the operator overruled by naming `claude-cli`; a lane then read `graphify/llm.py:209-221` to confirm the 0.0/0.0 pricing | A full round of objection → operator correction → source read, instead of the objection never being raised | (c) recorded at the wrong granularity — the memory carries the *principle* (Claude-only) but not the *concrete fact* (the flag name, that it's free) needed to apply it without re-deriving |
| 3 | `timeout` is a broken shim on this host/toolchain | `project_session_2026-09-12b.md` (memory hook) | A probe this session wrapped a command in `timeout` and it broke again | One broken probe re-run | (b) loaded but not matched — the memory hook exists and is indexed in MEMORY.md, but nothing forces a check of "am I about to do the thing memory already warns against" at the point of tool construction; the rule set additionally tells agents to use `timeout`-adjacent patterns (background+poll) without cross-referencing this specific breakage |
| 4 | Background task "completed (exit code 0)" notifications can be flat wrong | `feedback_background_task_notification_can_lie.md` (memory, indexed in MEMORY.md), also machine-stated in `verify-before-advancing.md` (eager rule) | Recurred **≥3 times this session** per `findings.md` C24 and `progress.md`'s 2026-09-13 log ("task notification lied THREE times this session") | Each occurrence cost a full "wait, the log disagrees with the notification" detour, and once (C24) it hid 4 real test failures behind a false-green summary | (b) loaded but not matched at the moment of trust — the rule is eager and the memory is indexed, yet each individual background-task result was still taken at face value until manually re-checked |
| 5 | `#1049` / `#1050` are substantially fixed in code already; the tickets are stale | Nowhere — this is itself new information this session produced (`rev-agentsview` FINAL, `progress.md`) | A lane had to grep the source and diff it against the ticket text to discover the tickets were stale | One dedicated agent-lane's worth of source tracing | (e) genuinely not recorded before this session — but the *pattern* (open ticket ≠ undone work) WAS recorded in `feedback_open_ticket_is_not_evidence.md`, and that memory's own prescribed action ("grep the ticket's named symbols before planning it") is exactly the check that eventually resolved #1049/#1050. The mechanism worked; it just wasn't invoked pre-emptively — see class (b) below for why. |
| 6 | kb-setup pins graphify `0.9.42` (vs. this repo's `0.9.61`) | A comment in `python/pyproject.toml` (tracked, in-repo) | Found only by tracing dependency pins across repos while reasoning about the graphify version bump | One cross-repo trace | (a) recorded but not loaded — a `pyproject.toml` comment is source, not an eager-loaded instruction surface; nothing indexes "which pin says what" for retrieval by a coordinator that isn't already reading that file |
| 7 | `.agents/skills/graphify/SKILL.md` is a **deliberate stub** — `graphify-skill-install -- agents` must not overwrite it | `tests/test_skills_mirror.py:234-236` (`test_graphify_mirror_stays_the_deliberate_stub`) — a real, passing test, i.e. machine-enforced | Discovered only by **breaking it**: C24 ran the installer for the `agents` platform, the test failed, and only then was the invariant learned | A live regression (reverted before commit) plus the failure-triage cost recorded in C24 | (c)/(d) hybrid — the fact was recorded at the *correct* granularity (a test) but in a place with **no positive-discovery signal**: nothing surfaces "here is an invariant this operation will break" before you run the operation. A test that fails ex post is not retrieval, it is a trip-wire. |

Six other repeat-cost items surfaced in this session's own `findings.md`/
`progress.md` that fit the same shape but were not separately investigated in
depth for this table (flagged for a future pass, not fabricated as new rows):
the SubagentStop removal history re-litigated across three separate rule
audits in A-2 (`findings.md` "Rule 1: agent-report-persistence.md"); the
`lockfile` boolean's provenance (C23) required tracing one buried 2026-04-05
commit that no rule or memory names; and the `mise run gha-rerun --failed`
partial-rerun trap (`progress.md`, 2026-09-13, `#1046`) was filed as a fresh
issue specifically *because* nothing tracked pointed at it yet.

## Part 2 — Classification, with the counts that matter

| Class | Meaning | Instances above |
|---|---|---|
| (a) recorded but not LOADED | Fact lives in a file that is never in context by default (a receipt, a source comment, a `docs/` file outside the eager rule set) | #1, #6 |
| (b) loaded but not MATCHED | The exact memory/rule was already indexed in MEMORY.md or an eager rule, but nothing at the moment of decision connected it to the situation | #3, #4, #5 (partially) |
| (c) recorded at the wrong GRANULARITY | A principle existed where a concrete flag/path/fact was needed to act without re-deriving | #2, #7 |
| (d) recorded but STALE/contradicted | Not observed as the dominant failure this session — the closer relative is #7, where the record (a test) is correct but silent until triggered | — |
| (e) genuinely not recorded | New information this session actually produced | #5 (root cause), plus the `#1046` gha-rerun trap |

**The dominant class is (b), not (e).** Every memory referenced above for
items #3, #4, and #5 already existed, was already in `MEMORY.md`, and had
already been read into context via the SessionStart hook injection this
session (the transcript shows the standard memory-recall preamble). The
failure was never "we didn't write it down" — this matches the standing
finding in `project_session_2026-09-11-c.md`: *"same bug filed TWICE,
diagnosed THREE times — recording was never the gap, RETRIEVAL was."* This
session reproduces that exact pattern three more times.

## Part 3 — Could the graph have answered these? (control-armed)

`.claude/rules/graphify-first.md` mandates `mise run graphify-query` before
grepping raw files, on the premise that the graph is a faster, more complete
answer surface. Tested directly against two of the facts in the table:

```
$ mise run graphify-query -- "does jdx/mise have issues disabled"
[!] TRUNCATED: showing 42 of 135 nodes (~2000-token budget) — ERROR task failed

$ mise run graphify-query -- "claude-cli graphify backend pricing free"
[!] TRUNCATED: showing 44 of 55 nodes (~2000-token budget) — ERROR task failed
```

Raising the budget to 6000 tokens on the mise query still truncated (130/133
nodes) and still did not resolve — because **the graph does not contain the
fact at all**, not because the budget was too small. Confirmed structurally:

```
$ grep -c '"file": *"[^"]*\.md"' graphify-out/graph.json   → 0
$ grep -c 'docs/receipts' graphify-out/graph.json          → 476
```

Zero `.md` file nodes exist in the graph, but 476 raw string occurrences of
`docs/receipts` do — meaning the graph indexes **code structure** (functions,
classes, call edges, docstrings, and path *strings that appear inside code*),
not the **prose content of markdown files**. `docs/receipts/440.md` is where
fact #1 lives; the graph has no node for that file's content at all. This is
consistent with this session's own C27 finding that `graphify-update` (the
only sanctioned rebuild path) is explicitly **AST-only, no LLM, no prose
extraction** — `graphify extract` (which does deep/prose extraction) has never
been run in this repo, by policy (C27's blocker).

**Conclusion: the graph could not have answered fact #1 or fact #2 as tested,
and the mandate in `graphify-first.md` to query it "before grepping raw files"
is misleading for exactly this class of fact.** The rule's own health-check
distinguishes `fresh`/`stale`/`missing` graph states but has no state for
"this fact class isn't in the graph regardless of freshness." Nobody asked the
graph for facts #3–#7 either, but for those the more relevant surface was
memory/rules, not the graph, so the omission there is lower-value to fix.

Control arm on the "graph could work for code-shaped questions" side: earlier
in this session (see `findings.md` C21) `res-hook-map` successfully cross-
checked the Claude/Codex event count via the graph-adjacent source read, and
`blast-radius`-style graph queries are documented working elsewhere in this
repo's history — so the graph is not broadly broken, it is **scoped to code,
not prose**, and the eager rule does not say so.

## Part 4 — Enforcement proposals (one per class, each with a control arm)

### Class (a): recorded but not loaded — "promote or index cross-repo/source facts a coordinator will need without reading the file that holds them"

**Proposal:** Extend `doctor.toml`/the SessionStart doctor pass with a
narrowly-scoped **"known external facts" lookup file** — NOT a new rule
(rules are prose that must be recalled, which is the exact failure class this
audit is measuring), but a small, `grep`-able JSON/TOML table of
`external-fact -> file:line` pairs that a coordinator can search *before*
issuing a live `gh api`/`curl` call to answer a question a past session
already answered externally. Example row: `{"query": "jdx/mise issues
enabled", "answer": "disabled", "source": "docs/receipts/440.md:247"}`.

- **Why this and not another eager rule:** an eager rule adds bytes to every
  session's context (budget-constrained, see Part 5) and still requires the
  *reader* to connect prose to situation — the same match failure as class
  (b). A lookup table is only consulted on demand, at the moment a live
  external call is about to be made, and is cheap to grep.
- **Where it fires:** wire it as a **PreToolUse check on `Bash` calls matching
  `gh api`/`curl.*github.com` for read-only lookups** (same layer that already
  enforces `mise-tasks-only.md`), which prints "this may already be answered:
  see <file:line>" as advisory context, not a hard deny (a live check can
  still be legitimately re-run if state may have changed).
- **Control arm — what makes it FAIL:** if the table is added but no
  PreToolUse hook consults it, a repeat of fact #1 (another lane re-running
  `gh api repos/jdx/mise`) after the table exists would prove the mechanism
  didn't fire. That is a cheap, reproducible regression test: seed the table
  with a fake external fact, issue the matching `gh api` call, and assert the
  advisory string appears in the tool result.

### Class (b): loaded but not matched — the dominant failure, and the hardest to fix with prose

**Proposal:** This is exactly the shape `.claude/rules/probes-need-a-control-arm.md`
already targets for *probes*, but the memories here are not probes — they're
warnings that a *specific upcoming action* is a known trap (`timeout` is
broken; a background-task notification cannot be trusted; an open ticket is
not evidence). The fix that doesn't rely on the model "remembering to
remember" is a **PreToolUse pattern-match gate**, the same enforcement class
already used for `mise-tasks-only.md`'s `hook_guard.py`:

1. `timeout <cmd>` in a Bash call → deny/rewrite to the documented
   background-and-poll pattern from `long-running-command-hangs.md`. This is
   directly analogous to the existing `backgrounded mise run` guard rule —
   same file, same mechanism, new pattern.
2. A `run_in_background: true` Bash call whose result is consumed by the next
   assistant turn **without** a `grep`/`Read` of the redirected log path in
   between → the harness cannot see "did you check the log", but the prompt
   discipline in `verify-before-advancing.md` already demands this; the
   incremental win here is a **PostToolUse reminder on backgrounded Bash
   completions** that prints the log path and "read this before trusting exit
   code 0" — mirroring the existing `PostToolUse` scoped to the `Agent` tool
   for report persistence (`agent-report-persistence.md`'s "Native carriage").
3. Before planning work against an **open** GitHub issue number, a
   `pre-flight symbol grep` — this one already has a memory-prescribed action
   (`feedback_open_ticket_is_not_evidence.md`: "grep the ticket's named
   symbols before planning it"). Make it a **skill or mise task**
   (`mise run ticket-check -- <issue#>`) that greps the issue body's named
   symbols against the tree and reports hit-rate, so the check is a five-
   second command instead of a remembered discipline.

- **Control arm for all three:** each is testable by construction — run the
  banned pattern (`timeout sleep 5`, a background Bash whose log is never
  read, planning against a synthetically-stale issue) and confirm the gate
  fires; then remove the gate and confirm the same input passes silently
  (proving the check, not the world, discriminates — `probes-need-a-control-
  arm.md` rule 9).

### Class (c): recorded at the wrong granularity — principle without the concrete fact

**Proposal:** When curating memory (the existing `memory-index-curation`
skill), add a rule: **a `feedback`/`project` memory that states a policy
("Claude-only, never auto-keys") must also name the concrete mechanism that
satisfies it, if one exists in source** ("the `claude-cli` backend,
`pricing: 0.0/0.0`, in `graphify/llm.py:209"). This is a curation-time check,
not a runtime gate — it fires when a memory is written or edited, via the
skill's existing review pass.

- **Control arm:** a memory-quality lint (extend `memory-index-curation`'s
  existing verification step) that flags a `feedback`/`project` memory
  containing a policy statement with an imperative verb ("never", "always",
  "only") but zero `file:line` or flag-name citations — a coarse but
  cheap heuristic. Test it against `feedback_kb_graphify_claude_only.md`
  BEFORE this session's C28 update (should flag) and AFTER (should pass,
  once the `claude-cli`/pricing detail is folded in).

### Class (e): genuinely new information — the low-cost case

**Proposal:** Nothing new is needed beyond what already exists —
`agent-report-persistence.md` + `docs/research/kb/reports/agents/` already
route new findings (like #1049/#1050's staleness, and the `#1046` gha-rerun
trap) into a durable, tracked location, and this session did that correctly
for both. The only gap is that a *new* durable finding does not automatically
get folded into a *searchable* index the way `MEMORY.md` folds memory — a
report in `docs/research/kb/reports/agents/` is grep-able but not indexed by
relevance the way `MEMORY.md` is. This is a lower-priority fix than (a)/(b)/(c)
above because the cost of re-deriving a genuinely-new fact once is expected
and acceptable; the failure mode worth guarding against is re-deriving the
**same** fact repeatedly, which #1049/#1050 has not yet done (this was its
first derivation).

## Part 5 — Budget reality check

Measured this session, control-armed against the actual filesystem:

- **Eager rules** (`.claude/rules/*.md`, always in context per
  `md-size-budgets.md`): **26 files, 135,912 bytes total.** This is already a
  large fixed cost every session pays regardless of task relevance.
- **MEMORY.md index** (always loaded): **22,855 bytes**, but the underlying
  memory directory holds **327 individual files** — only the index/hook lines
  are eager; the full content of a given memory is retrieved on demand
  (relevance-based recall), not preloaded. This is why class (b) failures
  happen even for memories that ARE indexed: the *hook line* in MEMORY.md was
  in context, but the *decision to recall the full file* still depends on the
  model matching the situation to the hook's wording — recall is not
  retrieval-by-default.
- **Skill listing** carries its own separate character budget
  (`agent-artifact-conventions.md` rule 6) and is lossy under pressure
  (descriptions shortened, then whole skills dropped least-used-first).

**Consequence for the proposals above:** none of the class-(b) fixes should be
implemented as *more eager rule text* — the existing 136KB of eager rules is
already large, and each byte added competes with everything else for
attention at read time (this is the mechanism, not a metaphor: a long eager
corpus increases the chance any one clause is skimmed rather than matched).
The PreToolUse/PostToolUse gate proposals in Part 4 are deliberately mechanism
-based rather than prose-based for this reason: **a gate that pattern-matches
a dangerous action fires whether or not the relevant rule text was "read
carefully" in that turn — it does not compete for attention budget the way an
additional paragraph does.** This is the same principle
`probes-need-a-control-arm.md` states for probes, applied to *retrieval*
itself: a control that depends on the model remembering to check is not a
control, it is a hope.

## Summary

The dominant retrieval-failure class this session (as in the prior
`project_session_2026-09-11-c` incident it echoes) is **(b): the fact was
already recorded and already loaded, but nothing forced a match between the
stored warning and the live decision.** The graph (`graphify-first.md`'s
mandated first stop) is structurally unable to help with this class or with
class (a) failures sourced from prose docs — it indexes code, not markdown
content, confirmed by a direct node-count probe (0 `.md` file nodes vs. 476
raw path-string hits). The fixes that don't depend on "remember to recall
better" are mechanical: PreToolUse/PostToolUse pattern gates for the specific
recurring traps (`timeout`, unread background logs, unaudited open tickets),
a small external-fact lookup table for cross-repo/GitHub facts, and a
curation-time rule that policy memories must carry their concrete mechanism,
not just the principle.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — confirmed via `gh api` in-session
  (by other lanes) that Issues are disabled; this audit did not re-run that
  call, citing `docs/receipts/440.md` instead per this report's own thesis.

_No other external repos were queried directly by this audit lane; all other
evidence came from this repository's own tracked files, memory directory, and
installed graphify graph._
