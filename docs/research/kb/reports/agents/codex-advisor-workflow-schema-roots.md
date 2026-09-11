# codex-advisor: workflow schema root-type fix plan

Decision under advice: fix plan for object-root JSON Schema violations in
`.claude/workflows/gated-implementation.js` (GATES) and
`.claude/workflows/graphify-refresh.js` (TASK_RESULTS), on branch
`fix/workflow-schema-roots`.

Status: IN PROGRESS — gathering evidence, consulting codex.

## Evidence gathered (read directly from the live files, verified)

1. `.claude/workflows/gated-implementation.js:18-30` — `GATES` schema root
   is `type: 'array'`, passed as `schema: GATES` at line 97 inside the
   `agent()` call (label `gate-runner`, lines 93-98). Confirmed as the crash
   site. Consumption sites: line 99 (null check), line 104 (early return),
   lines 137-144 (final status ladder, returns `gates` verbatim).
   Object-rooted precedent in the SAME file: `REVIEW` (31-51), `CRITIC`
   (52-70) — both wrap their arrays in a named property (`findings`,
   `verdicts`).

2. `.claude/workflows/graphify-refresh.js:24-36` — `TASK_RESULTS` schema
   root is also `type: 'array'`, passed as `schema: TASK_RESULTS` at line 79
   (label `graphify-operator`, lines 75-80). This workflow has not been run
   yet (queued follow-up); same crash is latent. Consumption sites: line 81
   (null check + early return), line 101 (final return). Object-rooted
   precedent in this file: `RESEARCH` (16-23), `AUDIT` (37-56, same
   wrap-in-named-property pattern).

3. `.claude/workflows/modernization-audit.js` — read in full (236 lines).
   All six schemas (`GAP`, `FINDINGS`, `VERDICTS`, `SYNTH`, `CRITIQUE`) are
   object-rooted with every array wrapped in a named property. No root-array
   schema found — appears unaffected by this defect class.

4. Corroboration from offline KB docs
   (`knowledge-base/sources/agent-harness-docs/docs/claude-code/`):
   - `workflows.md`'s own "what a saved script looks like" example shows
     `schema: { type: 'object', required: ['files'], properties: { files: {
     type: 'array', items: { type: 'string' } } } }` — object root, array
     wrapped in a named property. This is the documented pattern.
   - `agent-sdk__structured-outputs.md` — every example schema (~6) is
     object-rooted.
   - The literal runtime error text ("TelemetrySafeError", "unusable JSON
     Schema", "object-rooted tool input schema") does **not** appear anywhere
     in the offline corpus — we have no documented citation for the exact
     validation message, only the consistent object-root convention across
     every example (repo's own and upstream docs) and the runtime error text
     itself.

## Codex consult

Prompt: `.agent/kb/raw/codex-advisor-prompt.md`. Dispatched via
`PLANNING_DISABLED=1 codex exec --ephemeral --sandbox read-only --model
gpt-5.6-sol -c model_reasoning_effort="xhigh" -o
.agent/kb/raw/codex-advisor-verdict.md -`. Running in background (xhigh
effort); this file will be updated with the verdict when it returns.

## Verdict (codex gpt-5.6-sol, xhigh, read-only sandbox — completed, exit 0)

Full raw verdict: `.agent/kb/raw/codex-advisor-verdict.md`. Spot-checked
every file:line citation below against the live tree — all confirmed.

### 1. Diagnosis: CONFIRMED

Root-array schemas (`GATES` in `gated-implementation.js:18-30`,
`TASK_RESULTS` in `graphify-refresh.js:24-36`) are the direct cause. Wrapping
each array in a domain-named object property is correct and minimal — the
repo's own convention (`findings`, `verdicts`, `gaps`, `highlights`) already
does this; the doc's `files` example name is illustrative, not reserved.
Recommended names: `GATES` → `{ gates: [...] }`, `TASK_RESULTS` → `{ tasks:
[...] }`. Avoid generic names (`items`/`rows`) — they discard domain meaning.

Key architectural point: **the object wrapper is a transport constraint, not
part of the workflow's public result contract.** Unwrap immediately after the
`agent()` call so the rest of each script — and every external return value —
keeps the existing `gates: array | null` / `tasks: array | null` shape
unchanged. This makes the "lockstep" concern in the original ask much smaller
than it looked: only the `agent()` call site changes, not the null checks,
early returns, or final status ladder.

### 2. Concrete fix

**`gated-implementation.js`** — replace `GATES` (lines 18-30) with an
object-rooted schema `{ type: 'object', required: ['gates'], properties: {
gates: { type: 'array', items: {...same row shape...} } } }`. At line 93,
rename the raw result to `gateOutput`, update the prompt text to say "Return
one object whose `gates` property contains one gate-result row per command",
then `const gates = gateOutput === null ? null : gateOutput.gates` (NOT
`const { gates } = await agent(...)` — that throws on a null result). Lines
99, 104, 137-144 are then **unchanged**.

**`graphify-refresh.js`** — same shape for `TASK_RESULTS` → `{ tasks: [...] }`,
same unwrap pattern at line 75 (`taskOutput` → `tasks`). Lines 81-84 and 101
unchanged.

**Lockstep test/doc changes** (found by codex, not in my original ask —
confirmed present by direct read):
- `tests/test_workflows_js.py:151` (the `gate-runner` stub) and `:156` (the
  `graphify-operator` stub) currently fabricate the **obsolete bare-array**
  wire shape and must return `{ gates: [...] }` / `{ tasks: [...] }`.
- `tests/test_workflows_js.py:278` (`_GATES_OK_BODY`) — same fix.
- Add assertions that the workflow's final `result.gates`/`result.tasks`
  stay arrays, to pin the wire/public-shape distinction.
- `docs/specs/orchestration-pr-a-2026-09-09/spec-A1.md` §3c/3d (around line
  54) calls the gate/task result "schema-returned `[{cmd, rc, log,
  firstFailure}]`" — describes the pre-fix bare-array wire shape. Amend to
  distinguish the `{gates:[...]}` transport wrapper from the unwrapped public
  `gates` array; the public return contracts stated elsewhere in that spec
  are otherwise still correct.
- No consumer outside these two workflows was found reading `.gates`/`.tasks`
  (confirmed: `.claude/CLAUDE.md` only lists the workflow names).

### 3. Guard: YES — extend the existing test, no new module

Do **not** add a separate Python module, hk step, or `mise run verify`
contract. `tests/test_workflows_js.py` already globs every current and future
`.claude/workflows/*.js`, evaluates the real JS through repo-pinned Bun, and
receives the actual evaluated `options.schema` at the stubbed `agent()`
boundary — that IS the capability check per
`.claude/rules/probes-need-a-control-arm.md` rule 9, not a symptom sniff.
Add one guard in the shared stub:

```js
if (options.schema !== undefined && options.schema.type !== 'object') {
  throw new Error('agent schema root must declare type: object')
}
```

This beats regex/AST scanning because it inspects the actual object handed to
`agent()` — immune to reformatting, renamed constants, or indirection.
Control arms: **positive** — a miniature workflow with an object-rooted
schema wrapping an array completes; **negative** — the same workflow with
only the root changed to `type: 'array'` is rejected at the `agent()`
boundary (Bun still parses it fine; the check catches it). Do **not** assert
the literal `TelemetrySafeError` wording — that's a platform-owned symptom,
not the capability. Note: a generic JSON-Schema validator is insufficient
(root array is valid draft-07) — the failing rule is the platform's narrower
tool-input-schema policy, which only the `agent()` boundary itself can check;
no standalone CLI validation command was found for this path (medium-high
confidence — based on offline docs + installed CLI help, not runtime source).

### 4. Other same-class defects: NONE found

`modernization-audit.js`'s five schemas (GAP, FINDINGS, VERDICTS, SYNTH,
CRITIQUE) are all object-rooted; every `required` name has a matching
`properties` entry across all three files; no `Date.now()`/`Math.random()`/
bare `new Date()`; no call approaches the 4,096-item `parallel()`/`pipeline()`
cap. One separate (non-blocking) observation: schemas validate row *shape*
but not dynamic completeness/correlation with `A.verify`/`A.tasks` (e.g.
`{gates: []}` is schema-valid even when commands were requested) — flagged as
a distinct, optional hardening question, not part of this fix.

### Confidence

Diagnosis + wrapper fix: very high. Immediate-unwrap/public-compatibility
recommendation: high. Guard design: high. Absence of a standalone platform
schema validator: medium-high (docs + CLI help, not runtime source or a live
canary — codex could not run a live workflow to confirm the accept/reject
behavior end-to-end from inside the read-only sandbox).

### What neither codex nor I verified

- No live `/gated-implementation` or `/graphify-refresh` run was executed to
  confirm the fixed schema is actually accepted by the platform (that would
  require a real, mutating workflow run outside the advisory read-only scope
  of this consult — the caller should do this once the fix lands, per
  `.claude/rules/real-integration-evidence.md`).
- Graphify was unavailable inside codex's read-only sandbox (couldn't create
  temp/log state); it fell back to direct source reading, which is what both
  of us used throughout.

## GitHub repos touched

_None._ All evidence came from local repo files and the offline
knowledge-base doc cache (`agent-harness-docs`), no remote fetch was made.

---

## Real-integration evidence (added by the coordinator, 2026-09-11)

The advisory above flagged one thing neither the advisor nor the implementer could
settle by reading: **does the platform actually ACCEPT the wrapped schema?**
`.claude/rules/real-integration-evidence.md` forbids closing that on a passing unit
test. Both arms were therefore measured against the real Workflow runtime.

| arm | when | result |
|---|---|---|
| root-level `type: 'array'` | 2026-09-11 06:00Z, the `/gated-implementation` run that started this | `TelemetrySafeError: agent({schema}) received an unusable JSON Schema … The subagent was not started` |
| object root wrapping the array | 2026-09-11 07:4xZ, throwaway probe workflow | **ACCEPTED** — `agentCount: 1`, `agents_error: 0`, returned `{"gates":[{"cmd":"true","rc":0,"log":"/tmp/x.log","firstFailure":""}]}` |

The probe declared a schema shape-identical to the fixed `GATES` (object root, one
required property, that property an array of objects) and made one real `agent()` call
through the Workflow tool — the same code path that rejected the old shape. So the
positive direction is measured, not assumed.

### Guard mutation arms (coordinator-run, `23d6fab`)

| arm | result |
|---|---|
| baseline `pytest tests/test_workflows_js.py` | 6 passed |
| guard neutered (`if (false && …)`) | **1 failed** — the negative-arm test is bound to the guard, not passing incidentally |
| shipped `graphify-refresh.js` root flipped back to `type: 'array'` | **1 failed**: `agent() schema root must be type 'object', got 'array'` |

The third arm is the load-bearing one: it reproduces the real regression in a real
shipped workflow — and in the *other* file from the one the negative-arm test mutates —
so the guard is proven to cover both. Both mutations were reverted; `git diff` clean.
