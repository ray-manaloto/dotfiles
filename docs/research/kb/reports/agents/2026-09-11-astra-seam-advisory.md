# Astra advisor — seam design for PR 2 (function-hooks issue retrieval)

**Lane:** `codex-astra-advisor` on `gpt-6-astra` at `xhigh` · **Date:** 2026-09-11
**Session:** `dotfiles-20260911.001` · Persisted VERBATIM at receipt per
`.claude/rules/agent-report-persistence.md` rule 1.

This was the first dispatch of the `codex-astra-*` family created in `1dfe854`.

> **Coordinator note.** Two citations were checked and one is wrong; the advisor
> accepted both corrections and neither changed its section 4 answer.
> (1) `python/src/dotfiles_setup/cli.py` **does not exist** — the real CLI entry
> is `main.py`. The *finding* stands, re-derived independently:
> `grep -cE "stdin|session_id|CLAUDE_SESSION" python/src/dotfiles_setup/doctor.py`
> → **0**, control arm `grep -c baseline` → **40**, so the probe discriminates
> and the doctor genuinely has no session identity.
> (2) `bun = "1.4.0"` at `.config/mise/conf.d/shared.toml:32` is confirmed, but
> `typescript` is pinned **nowhere** (`grep -rn typescript mise.toml
> .config/mise/conf.d/shared.toml` → 0), so the `tsc` gate costs ONE new pinned
> tool, not zero.

---

## Verdict

**The seam is right, the premise under it is wrong.** Push the logic behind the
cache — but "the TS becomes ~10 lines with no logic worth testing" is false in
the direction that decides the design, and the constraint "nothing in TS is
testable by us today" is also false.

## 1. The correction

Every measured failure mode of this hook is *shape*, not *logic*:

| Failure | Testable by moving selection to python? |
|---|---|
| `additionalContext: string` instead of `string[]` | no |
| forgotten `return next(e)` | no |
| 10 000 ms budget overrun / heartbeat wedge | no |
| `$.fs.read` throws (file absent on a fresh clone) | no — and this one is **new**, introduced by the cache |

The seam removes 100% of the class you can already test and 0% of the class that
actually kills you. It is still worth doing — smaller is better — but do not ship
it believing the residue is safe. The residue is *irreducible*, not *inert*, and
the cache read adds one more member to it.

**Two native gates exist and neither needs a TS test runner.** Both land inside
pytest as `rc == 0` assertions through the existing injected-runner pattern:

- `claude plugin validate <dir>` — measured this session
  (`docs/research/kb/reports/agents/2026-09-11-function-hooks-firing-probe.md`):
  it statically resolves registered events, their matchers, *and* what the module
  calls on `$` (`❯ ./register.ts calls: nothing on $`). That binds "did my
  registration bind the name I meant" and "does it touch only `$.fs.read`" with
  no session.
- `tsc --noEmit` against the vendored `claude-code-function-hooks-types.d.ts`
  (7,966 lines, already in the KB). This catches `additionalContext: string` —
  **the exact defect that was measured as the silent fail-open** — at build time.
  `bun = "1.4.0"` is already in `.config/mise/conf.d/shared.toml:32`;
  `npm:typescript` is one pinned tool, not new infrastructure.

That converts the #1 unobservable runtime failure into a red gate. It is a bigger
win than any refinement of the cache schema.

## 2. The deciding risk

**The liveness detector cannot distinguish "the handler body ran" from "the
context reached the model", and the fail-open modes are precisely what splits
those two.**

A marker written by the hook proves the body executed. But a wrong-shaped return
is caught *after* your code returns — so the sequence "write marker → return
`additionalContext: string`" leaves a fresh marker on disk while nothing reached
the model. The doctor then reports healthy, forever, on a hook that has been dead
since the day someone edited the return. That is
`probes-need-a-control-arm.md` rule 9 exactly: you are sniffing a symptom you own
instead of asserting the capability you depend on.

This is the one that changes the design. Mitigation is the `tsc` gate above
(kills the shape class at build time) plus accepting that the marker only covers
*load/dispatch* failures — and saying so in the check's own finding text, so
nobody later reads a green doctor as proof the feature works.

**Second, unnamed dependency:** the doctor has no session identity.
`.claude/settings.json` wires it as `mise -C … run doctor` with matcher
`startup|resume`, and a grep for `stdin|session_id|CLAUDE_SESSION` over the
doctor returns **zero hits** — it reads neither the hook's stdin payload nor a
session id. "Previous session's marker" therefore has nothing to key on except
mtime, and an mtime threshold makes a machine idle for a week indistinguishable
from a dead hook. Either the doctor starts consuming the stdin payload (the
classic hook payload carries `session_id`), or the check is a time-based
heuristic and must be labelled one.

---

# Astra seam advisory — sections 3-5 (remainder)

Corrections accepted, neither changes section 4:
- Cite `python/src/dotfiles_setup/main.py` (the real CLI entry). `cli.py` does not exist; my grep named a non-existent file, which is a bound that turns "absent" into "unreachable". Your re-derivation (0 hits vs control 40) is the arm that settles it — the finding stands, the citation was wrong.
- `typescript` is pinned nowhere. The `tsc --noEmit` gate needs ONE new pinned tool (`npm:typescript`, bun backend already in use). Justified, not free.

## 3. The 5-cap and the format in the cache — three problems

**(a) The cap belongs to the consumer, not the producer.** The hook holds the only
information that could vary the policy (the SessionStart payload: `source`,
startup vs resume). Baking 5 into the cache means the one place that knows the
context has no say — a later "5 interactively, 0 under `-p`" needs a cache format
change. Store **N** rendered lines (20, say) and let the TS `.slice(0, 5)`. Three
characters of TS, no logic, every option preserved, ~15 unused lines in a tracked
file. Strictly better split than rendering exactly 5.

**(b) A pre-rendered blob has no freshness signal — and that is this feature's own
failure mode.** A line rendered 2026-09-11 asserting "#877 open" is stated as fact
at session start on 2026-10-20, with identical authority, if #877 closed an hour
after the refresh. You would be building a machine for confidently restating stale
facts: the same class as the defect it exists to fix. The build timestamp must be
IN the rendered text ("as of 2026-09-11 — 4 open"), not in metadata the hook never
shows.

**(c) The regeneration loop.** A format tweak becomes PR -> merge -> GHA -> second
PR. Make the cache-build task runnable locally on demand so the loop is one
command. Small ask, but it is the difference between "we'll fix the wording" and
"we won't bother".

## 4. One new seam is not the minimum — zero is

Make the hook's input a **newline-delimited text file**:
`$.fs.read(path).split("\n").filter(Boolean).slice(0, 5)`. No schema, no version,
no parse — and therefore no JSON-parse-error fail-open mode, which would otherwise
be a fifth member of the untestable table in section 1.

Any metadata the doctor needs (build timestamp, source SHA, issue count, the no-op
guard's input) goes in a **sibling JSON that only python reads**. The schema
contract then exists only between python and python — fully testable — and the TS
side crosses nothing but read/split/slice.

So the cache schema is not a new seam you must accept. It is a seam you delete by
choosing the file format, and the deletion removes a failure class rather than
relocating it.

Neither correction touches this. The `typescript` pin is a build-time gate on the
handler's return type; it is orthogonal to whether the hook's INPUT has a schema.
Zero-seam still stands, and it stands more strongly with `tsc` in play: with the
return shape gated at build time and the input unparsed, the TS residue has no
remaining branch that can fail for a reason a python test could have caught.

## 5. What I could not verify, and the probe that settles each

| Claim | Probe |
|---|---|
| `tsc --noEmit` against the vendored `.d.ts` actually rejects `additionalContext: string` | write the bad handler, run it, then the good one — **both arms**. If the bad arm passes, the declarations are not being applied to the handler signature and the gate is decoration. This is also the probe that justifies the new pin: do not add `npm:typescript` until the bad arm has gone red. |
| `claude plugin validate` exits **non-zero** on a broken registration | the firing-probe report only shows it PASSING ("Validation passed with warnings"). Register `on("classic.SessionStartt", ...)` and read `echo $?`. A validator that only ever exits 0 is not a gate. |
| `$.fs.read` on a missing file throws vs returns empty | a `--plugin-dir` run with the cache deleted, under `--debug-file`; grep for `hook failed`. This decides whether a fresh clone silently loses the hook — the one new untestable failure the cache introduces. |
| The hook coexists with this repo's 9 classic registrations | never established; the firing probe ran in an empty scratch dir with no project hooks loaded, and says so explicitly. |
| Whether a clone-ready deployment path exists at all | `@skills-dir` is documented with zero users worldwide and unprobed, and #1020 Part 2 already found that an external-source plugin enabled only by project settings does NOT load on a clone. **Probe this before specifying anything else** — it is the only open question that can make the rest moot. If it survives, the feature is a per-invocation `--plugin-dir` flag, not a thing that runs for anyone. |

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under advice; #1020 carries the function-hooks evaluation this design serves.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — source of the vendored function-hook type declarations the proposed `tsc` gate would check against.
