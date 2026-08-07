# Agent + review-lane BRIEFS — session 2026-08-07 (#602, #625)

**Why this file exists.** `.claude/rules/agent-report-persistence.md` and the
`clear-prep` skill require both halves of a findings-bearing delegation on disk:
the **report** AND the **brief that produced it**. This session's three reports
were persisted at receipt; the briefs were not — two sat in an ephemeral
scratchpad and one existed only in the orchestrator's context. That is the exact
loss #601 took (seven review rounds, seven surviving reports, **zero** surviving
briefs), so they are captured here before `/clear`.

A report without its brief is an answer whose question is gone. You cannot tell
what the lane was *not* asked — which is the first thing you need when deciding
whether to re-run it or trust it.

| Lane | Report | Outcome |
|---|---|---|
| `xsession-probe` (Agent tool, `claude-code-expert`) | `602-crosssession-sendmessage-probe.md`, this dir | 2 rounds; settled #602's answer-path scope, then retracted its own round-1 mechanism |
| codex round 1 (`codex exec` 0.146.0, OpenAI family) | KB `.agent/kb/review/reports/review-3d86e007bc0f-cold.md` | 4 blocking, all real |
| codex round 2 | KB `.agent/kb/review/reports/review-e42ad0719610-cold.md` | 4 blocking, **two introduced by round 1's own fixes** |

⚠️ The two codex reports live in the **knowledge-base** repo under `.agent/`,
gitignored **by design** (`kb-review`: *"a receipt is machine-local proof that
THIS machine reviewed THIS commit"*). They survive `/clear` but not a fresh
clone. The briefs below are the tracked record.

---

## 1. `xsession-probe` — the Agent-tool delegation

Spawned with `subagent_type: claude-code-expert`, model `opus`, named so it stayed
addressable. ⚠️ **Reconstructed from the orchestrator's context, not copied from a
file** — it was never written to disk, so this entry is a transcription. The two
follow-up `SendMessage` prompts are included because the second is what triggered
the round-2 retraction.

### 1a. Initial brief

> You are settling ONE question with evidence, for a spec being written right now
> (ticket #602). This is a terminating verification question over a finite domain,
> not a search. Answer it and stop.
>
> **The question.** Claude Code CLI **2.1.224** added cross-session messaging. A
> previous session measured only STRING COUNTS in the two on-disk bundles
> (`crossSessionInbound` 0→18, `dialogExpiry` 0→4, `ListAgents` 5→10). **That
> proves the feature exists; it does NOT prove it can reach the node we care
> about.** Do not carry that measurement forward as capability.
>
> **Can a human's answer be delivered, via 2.1.224's cross-session `SendMessage`
> (or `ListAgents`+`SendMessage`), to a background `--bg` node in
> `state="blocked"` with a non-empty `needs` and NO `queuedPrompt`?**
>
> Split it into two sub-cases and answer BOTH separately — they have different
> answers and the difference is the whole point:
> **(a) LIVE blocked node** — process alive. Can `ListAgents` enumerate it, and can
> `SendMessage` address and deliver to it?
> **(b) DEAD blocked node** — process exited, `state.json` still `blocked` with a
> `needs`. The REAL case: `~/.claude/jobs/{ad8baf35,fdfdaf90}`.
>
> **Hard constraints.** (1) DO NOT MUTATE `~/.claude/jobs/**` — those two files are
> the only real escalation payloads in existence and are cited in
> `tests/test_dag_tick.py`. If a probe would write to a job dir, describe what it
> would have shown instead. (2) Do not leave long-lived background agents running.
> (3) Control-arm every negative; invent any known-absent term FRESH. (4)
> Three-corpus rule, in order: the 2.1.224 BINARY > `--help` > docs. BSD grep is
> blind on that binary — use a python byte-search; the 2.1.223 bundle is a built-in
> control arm. (5) Distinguish "answered no" from "never asked".
>
> **What the answer is FOR.** The spec must decide whether the ANSWER path is in
> scope. The default is OUT — `575.md` R1 makes projection one-directional, and
> #601/#616/#604 all stopped at that boundary deliberately; a fourth crossing would
> make it decorative. So the useful answer is not "is cross-session messaging
> cool". It is: **does 2.1.224 create a delivery route that did not exist when R1
> was written, and does it actually reach case (b)?**
>
> Also if cheap: is there any 2.1.224 mechanism by which an inbound cross-session
> message would set `queuedPrompt` on a `--bg` node's `state.json`? (`dag_tick`'s
> `is_reply_queued` already treats that field as the "answer is on its way" signal.)
>
> **Deliverable and delivery discipline — read twice.** Write to
> `docs/research/kb/reports/agents/602-crosssession-sendmessage-probe.md`
> **INCREMENTALLY** — create it with headings BEFORE the first probe and append each
> finding as you get it. Agents that held findings in memory here have died at ~40
> minutes and left nothing. End with `## GitHub repos touched`. **You MUST call
> `SendMessage` to the parent before going idle** — final text goes nowhere in this
> harness (failed 3/3 here). Do not edit anything outside that report. Do not touch
> git branches.
>
> Be blunt about what you could not establish. A labelled null result is worth more
> than a confident inference.

### 1b. Follow-up — the datapoint that produced the retraction

Sent mid-run, after the orchestrator's own `ListAgents` call returned rows whose
names matched the two dead nodes. **Handed over as a claim to VERIFY, not a fact
to use** — which is the only reason the error was caught.

> Datapoint from the parent's own `ListAgents` at 2.1.224, for you to VERIFY and
> control-arm — do not take it from me as settled. Both dead-blocked nodes DO
> appear, under their `state.json` `name`: `zstd-compression-level-tuning`
> (= `ad8baf35`) and `Resume KB concurrency queuing design…` (= `fdfdaf90`). 34 peer
> rows, all `Remote Control`, all `idle`. Note what the row does NOT say: neither is
> labelled `background`/`bg`, and both show `idle` while `state.json` says `blocked`.
>
> Two things to settle: **(1) Enumerable ≠ addressable.** The `ListAgents` tool
> description says remote bridge sessions are *"reply-only — you can message one
> only in reply, after it messages you first"*. Verify against the BINARY: is that
> enforced in code, or only prose in a tool description? **(2) `idle` vs `blocked`
> is a two-probe disagreement** — per `probes-need-a-control-arm.md` rule 7 one of
> them is wrong or they measure different things. Which? And does delivery route on
> the bridge view (idle ⇒ "deliverable") or on `state.json`? If it routes on the
> bridge view it may ACCEPT a send to a node long dead and report success.
>
> Do NOT send to either node to find out — they hold the only two real escalation
> payloads and a delivery attempt could set `queuedPrompt` and destroy the evidence.
> Settle it from the binary, plus a throwaway node you spawn and stop yourself if
> you need a live arm.

**What that brief got right, worth copying:** it named the prior measurement and
explicitly forbade carrying it forward as capability; it split the question into
the two sub-cases *before* the agent could conflate them; it stated what the answer
was FOR so the agent could tell a useful answer from a complete one; and it handed
the mid-run datapoint over as *suspect*. That last one is why the round-2
retraction happened at all.

---

## 2. codex cold review, round 1 — verbatim from `cold-prompt.md`

Lane chosen by the `kb-review` skill's family table: Claude authored the diff ⇒
the cold lane must be a different family ⇒ `codex exec` (OpenAI).
Invocation: `codex exec --ephemeral --sandbox read-only -o <file> -` with the
prompt on stdin (`.claude/rules/ai-cli-invocation.md`).

```text
You are a cold code reviewer. You are being handed a commit by reference and
NOTHING about what it was supposed to do. Do not ask what the intent was; judge
what is there.

Repository: /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base
Commit under review: 3d86e007bc0f  (full: 3d86e007bc0f... — resolve it yourself)
Fixed point: 3a45f256170b7b07a9fa81e0bf3f6503ea426a84

Inspect it yourself, scoped exactly like this (the exclusion is deliberate):

    git -C /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base diff \
      3a45f256170b7b07a9fa81e0bf3f6503ea426a84...3d86e00 -- . ':(exclude)docs/research/**'

The changed artifact is a JSON "extraction chunk" that is merged into a knowledge
graph. Schema rules the repo enforces live in
`python/src/kb_setup/chunks.py` — read them rather than assuming. In particular
look at `_NODE_REQUIRED`, `_EDGE_REQUIRED`, `_CONFIDENCE`, `_SEMANTIC_ORIGIN`,
`_SUPERSEDES`, and `replay_order`.

The chunk's data was derived from
`sources/agent-harness-docs/docs/claude-code/commands.md`. Check the DERIVATION,
not just the schema: does every claim in the chunk actually follow from that file?

Report findings. Requirements:
- EVERY finding must cite `file:line` or quote the exact hunk. A finding you
  cannot cite, label `unverified` — do not drop it and do not promote it.
- Rate each finding blocking / non-blocking, and say which.
- Where you can, TEST your claim (run a command, parse the JSON, count something)
  rather than asserting it. Say what you ran.
- Begin your report with the literal line: `Reviewed 3d86e007bc0f`
- If you find nothing, say `NO FINDINGS — reviewed 3d86e007bc0f` and say what you
  checked so a reader can tell thoroughness from silence.

Be specific and adversarial. Do not compliment the change.
```

**The clause that paid:** *"Check the DERIVATION, not just the schema."* Every
local gate validated the schema and passed; all four blocking findings were
derivation defects — provenance laundering, inferred edges marked `EXTRACTED`, an
overstated version range, and an over-claiming memory file.

---

## 3. codex cold review, round 2 — verbatim from `cold-prompt2.md`

Round 2 is the LAST lane round the `kb-review` skill allows. Note the brief is
**verification-shaped over a finite list**, not a fresh search — and that it
explicitly directs the lane at the fixes themselves.

```text
You are a cold reviewer running ROUND 2 — the LAST round. Round 1 reported five
findings against an earlier SHA; the author says they fixed them. Your job is to
VERIFY the fixes, and to look for defects the FIXES introduced. Do not re-litigate
round 1's framing; check the current bytes.

Repository: /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base
Commit under review: e42ad0719610ba05dbb5b16f60cbcbe0a5823817
Fixed point: 3a45f256170b7b07a9fa81e0bf3f6503ea426a84

    git -C /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base diff \
      3a45f256170b7b07a9fa81e0bf3f6503ea426a84...e42ad07 -- . ':(exclude)docs/research/**'

Round 1's findings, to verify as FIXED / NOT FIXED / REGRESSED:

1. BLOCKING — binary-probe evidence was tagged as derived from commands.md
   (source_file + source_location L38) when the doc does not contain it. Also
   affected insight_autonomy_delegation's Agent-tool / Workflow-resumability /
   human-paste claims.
2. BLOCKING — `conceptually_related_to` edges the doc never connects on any line
   (cmd_goal<->cmd_loop, cmd_batch<->cmd_workflows) were marked
   confidence=EXTRACTED, score 1.0.
3. BLOCKING — "(v2.1.212+; pre-2.1.212 /subtask==/fork==forked-subagent)"
   overstated the doc, which scopes the old behaviour to v2.1.161 through
   v2.1.211.
4. BLOCKING — the committed query-memory file said the whole ten-command
   orchestration surface was missing; the superseded chunk already held
   cmd_background, cmd_fork and cmd_subtask (7 of 10, not 10).
5. NON-BLOCKING — the query memory's causal-history claim had no citable support
   inside this repository.

Then hunt for NEW defects the fixes introduced. Specifically worth attacking:
- Did re-tiering edges to INFERRED get applied to any relationship the doc DOES
  state (an over-correction)? Check each `conceptually_related_to` pair against
  the doc yourself.
- Do the two "PROVENANCE" labels now claim anything ELSE the doc does not
  support, or contradict each other?
- Did the memory-file rewrite introduce a new unsupported claim?
- Anything in `python/src/kb_setup/chunks.py` this chunk now violates.

Requirements, unchanged:
- EVERY finding cites `file:line` or quotes the hunk; uncitable ones are labelled
  `unverified`, neither dropped nor promoted.
- Rate each blocking / non-blocking.
- TEST claims where you can; say what you ran.
- Begin with the literal line: `Reviewed e42ad0719610`
- If nothing: `NO FINDINGS — reviewed e42ad0719610`, plus what you checked.

Be adversarial. A fix written under review pressure is the least-reviewed code in
the diff.
```

**The clause that paid:** *"look for defects the FIXES introduced"* plus the named
over-correction suspicion. Two of round 2's four blocking findings were exactly
that — a blanket re-tiering that demoted three relationships the doc states
explicitly, and confidence scores off the contract's required ladder that **no
local gate can check** (`chunks.py` validates the tier, not the score).

---

## What this session would tell the next one about briefs

- **A verification question over a finite list terminates; a search question over
  an open domain does not.** Round 2 named its five items and asked FIXED /
  NOT FIXED / REGRESSED. It came back in one pass.
- **Point the lane at the fixes.** "A fix written under review pressure is the
  least-reviewed code in the diff" is a single sentence that produced two of four
  blocking findings.
- **Ask for the derivation, not just the schema.** Every gate here checks shape;
  no gate can check whether a tagged source actually supports the claim.
- **Hand a mid-run datapoint over as SUSPECT.** The one place the orchestrator
  gave the agent a fact instead of a claim to verify, the agent would have
  inherited the orchestrator's error.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #602 and the
  spec these lanes fed.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  the diff both codex rounds reviewed (PR #229).
