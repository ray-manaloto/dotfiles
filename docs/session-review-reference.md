# Session Review Technical Reference

This is the implementation reference for `.claude/skills/session-review/SKILL.md`.
The skill owns invocation and judgment; this document preserves the cache,
provider, attachment, bounded-search, and finalization contracts needed when
changing the tool.

## Cache mechanics

The requirement lane caches only typed, normalized pre-finalization facts under
`.agent/state/session-review/`. Every run reapplies lineage, form/tool pairing,
authority, omissions, and semantic dispositions globally. Use
`--rebuild-cache` to force the cold parser; raw transcript records are never
stored in the cache.

## Requirement inputs and provider fields

The default review runs requirement coverage and both automation lanes. For a
focused requirements-only packet, run `mise run session-requirements` (equivalent to
`session-review --requirements-only --sessions 5 --source-repo-root
/absolute/source/checkout`). The root is mandatory and must be the exact
checkout path stored as `cwd` in the source sessions. This keeps an isolated
worktree review from silently auditing only that new worktree. A missing,
non-Git, or unmatched root is an `INCOMPLETE` review. It reads both Claude and
Codex native transcripts and retains user messages, interactive questions and
answers including free text, attachment metadata backed by hashed bytes,
compactions, subagent lineage and authenticated inherited prefixes, tool
call/result pairs, terminal state, and turn authority context.

This lane emits **UNREVIEWED bounded evidence**, not an inferred verdict. Assistant
prose cannot grant authority and a promise is not marked fulfilled merely
because a later answer says it was. Unknown or malformed transcript records
make the run `INCOMPLETE` and non-zero. Each source carries a prefix hash and
byte cutoff so an appended transcript remains verifiable while a rewritten
prefix invalidates the old review. An external attachment that cannot be read
also makes coverage `INCOMPLETE`; hashing its path string is not evidence of
its content.

Pass the native current Codex task identifier with `--codex-session-id`. A
nonempty `CODEX_THREAD_ID` is the fallback; an empty value is never forwarded
as an explicit selector. Claude roots are selected independently and are never
filtered by a Codex ID. The provider census records expected, available,
discovered, selected, rejected, archived, imported, malformed, and unreadable
sources. The most-recent relevant
user/turn activity is only a bounded fallback and **cannot certify that the
selected root is this active task**; requirements-only exits non-zero without
an explicit identity. A nonexistent or stale explicit Codex identity records
Codex `selected=0` and remains `INCOMPLETE`; Claude evidence cannot satisfy the
missing requested provider selection. Its certification is
`EXPLICIT_SESSION_ID_UNRESOLVED`, and the final iteration packet remains
`NEEDS_AGENT_ACTION` rather than converging on the other provider alone.

## Structural parsing and attachment limits

Transcript JSONL is parsed structurally. Never inspect rollout files with raw
`rg`/grep: a matching compaction row can contain megabytes of inline base64
or opaque tool output. The ledger whitelists bounded fields and represents data
URLs, encrypted agent bodies, full tool outputs, and compaction bodies only by
digest, byte count, and safe structural metadata.
Attachments are accepted only from approved transcript/source roots, with
symlinks refused and an 8 MiB cap. This is deliberately not described as
lossless: any unknown native record, missing pair, or unsupported current shape
makes coverage `INCOMPLETE` until a fixture and control arm establish it.

Known harness reminder types are counted as known-and-skipped. Context-bearing
attachments are bounded diagnostics containing a digest and byte count, never
user authority. A fresh unknown provider record or attachment remains
parser-blocking, but repeated instances are grouped once by provider/type with
a count and first source location.

## Prevention dispositions

Known credential-launcher/environment-scope and Git-hook/worktree-contamination
failures are high severity even when seen once; the recurring-command threshold
does not apply. A reviewer may confirm one only with a disposition JSON record
that records all four prevention facts: an in-repository nonsymlink
hook/rule/lint/static/test/task carrier plus SHA-256; typed mutation and
normal-gate audit receipts; and an issue readback. Persisted receipts are audit
evidence only: they **never authorize `COMPLETE`**, even when hashes and runner
context match. Their honest status is `ATTESTED`, not proof that arbitrary JSON
executed. Offline synthetic fixtures are test-signed controls and the
production loader refuses them. A declaration is not evidence.
The disposition schema names these `carrier`, `mutation_receipt`,
`gate_receipt`, and `issue_receipt`.
Missing or forged bytes keep coverage `INCOMPLETE`. Pass the file through `mise run session-review --
--requirements-only --source-repo-root ROOT --dispositions FILE`.
Pass reviewed requirement/promise decisions separately with
`--semantic-dispositions FILE`; each row names a stable `claim_id`, terminal
`status`, nonempty `rationale`, and typed `receipt_refs` including verification
such as `test:...`, `commit:...`, `artifact:...`, or `user:...`.

## Finalize state machine

`session-requirements` accepts configurable session and iteration bounds. The
Python CLI is a deterministic analyzer and resumable state machine; it never
claims to perform semantic agent work or edit prevention carriers. Each pass
emits exactly one typed action: `CONVERGED`, `PREVENTION_RECORDED`, or
`NEEDS_AGENT_ACTION`. A missing disposition is always `NEEDS_AGENT_ACTION`,
`INCOMPLETE`, and non-zero.
The iteration packet is self-sufficient: it records the repository root,
explicit session id and certification state, maximum and remaining iteration
budget, required roles, receipt state per finding, and content-addressed paths
for the report, evidence, and source-cutoff artifacts.

For every `NEEDS_AGENT_ACTION` packet, the invoking agent MUST orchestrate the
actual loop, bounded by the requested maximum N:

Before assigning prevention work, review every `unreviewed_requirement_id` in
the bounded evidence. Any unreviewed requirement keeps the action at
`NEEDS_AGENT_ACTION`; the current analyzer cannot semantically mark a request
fulfilled. Stop with the resumable packet at N until a reviewed disposition
path exists rather than claiming convergence. The iteration packet separately lists
`issue_candidate_requirement_ids` for requests that explicitly say to create
or update an issue, track or persist work, avoid forgetting it, or recover a
missed request. Resolve every candidate through live GitHub readback as one of:
an existing issue, a newly created issue, a completed carrier, a user-rejected
request, or a duplicate. This candidate list is a prioritization hint, never
completion authority; a zero-hit recurring-command report cannot override the
full pending-requirement list.

1. Spawn or assign a specialized fixer to implement a hook, rule, lint/static
   check, test, or mise task that prevents the motivating defect.
2. Assign independent QA to run a hostile mutation that reproduces the defect
   and prove the normal gate rejects it, then restore the control and prove the
   gate passes.
3. Assign an adversarial reviewer to verify the carrier would have caught its
   own motivating defect and that an issue/receipt records the disposition.
4. Choose a registered `prevention_id` and an exact GitHub issue API URL in a
   `session-review.finalize.v1` spec. The registry—not caller JSON—fixes the
   carrier contract, distinct mutation task, normal gate task, expected return
   codes, and named mutant. The registered mutation copies all carrier targets
   to an isolated directory, changes the target bytes, records before/after
   SHA-256 values, and invokes the **same** registered normal gate against that
   candidate. It emits `ARMED` only after the gate rejects the changed target;
   no edit or an accepted mutant fails closed. Unknown IDs, extra argv/expected-status
   fields, `--help`, same-task registrations, and repository-level endpoints
   fail closed. Run `mise run session-review-gate --
   --repo-root ROOT finalize --spec SPEC`. It generates an ephemeral nonce,
   executes both bounded checks and `fnox exec -- gh api` itself, validates all
   facts in memory, and emits only a temporary result. The nonce and completion
   authority are never persisted.
5. Resume only from that same-process temporary result. Every later review is
   `INCOMPLETE` until `finalize` is rerun. Stop after current finalize success
   or N passes with the resumable non-zero packet.

The agent-team protocol is the semantic self-improvement loop. The Python state
machine is its fail-closed evidence and resumption boundary. A report without
the verified disposition cannot become `COMPLETE` merely because the same
cutoff was parsed twice.

Use only the durable invocation chain shown above: skill -> mise task ->
`uv run --project python` -> the Python library. Do not replace it with
`python3` or bare `mise exec -- python`. The broader #715 research-runner
requirement follows the same boundary: an external last30days engine needs a
project CLI/library seam that verifies the selected interpreter's CA bundle and
launches the pinned engine. That runner is outside this ledger lane and must not
be half-implemented here.

## Lane bounds and filters

Both lanes are windowed, and the report says so on its first line — a
bound-limited search that does not declare its bound reads as complete.

- **Lane 1** scans the most recent sessions' transcripts. The count printed is
  **transcript files**, which includes every nested subagent transcript, so it
  is much larger than the session count you asked for.
- **Lane 2** reads the **tail** of `.agent/notepad.md` and only the **newest**
  handoff. The notepad accumulates across every session this repo has had; an
  unbounded scan answers "what has this repo ever done by hand" and buries the
  session you are reviewing under its own history.

Widen either with `--sessions` or by pointing the library at different files.

A regex cannot tell an expensive slog from a sentence describing one, so read
the passage before believing the row. Two filters already run, both derived
from real output rather than guessed:

- Shell constructs and harness mechanics are dropped from lane 1 — `while [`,
  `for i`, scratchpad `mkdir -p`, the in-turn poll loop. The poll loop is
  mandated by `.claude/rules/long-running-command-hangs.md` rule 2, so ranking
  it would put required behavior at the top of a list of things to stop doing.
- Instructions **not** to do something by hand are dropped from lane 2. A
  handoff saying "do NOT re-derive this" is the previous session having already
  paid, which is the opposite of a finding.

If a filter is hiding something real, widen it in a reviewed diff and say what
it missed. That is cheaper than reading a report nobody trusts.
