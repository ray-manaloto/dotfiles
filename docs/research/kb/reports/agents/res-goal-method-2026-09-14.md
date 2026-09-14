# Quantifying `/goal`: Method and a Rewritten Goal — 2026-09-14

Read-only research lane. Repo: `dotfiles` @ `feat/enable-research-plugins`. Objective:
make this project's `/goal` conditions and checks non-subjective and
quantifiable. This report determines what `/goal` mechanically is, what
"objectively verifiable" means for an agent goal, names the anti-patterns
this project has already lived, and delivers a rewritten three-phase goal
with per-phase machine-checkable conditions.

## 0. Sources and what each established

| Source | Type | What it established |
|---|---|---|
| `$CC/goal.md` (offline vendor doc, `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/goal.md`) | CITED, primary | `/goal` is a real harness feature: a session-scoped **prompt-based Stop hook**. After every turn, Claude Code sends the condition text plus the conversation-so-far to a small fast model (default Haiku) that returns `not yet met` / `met` / `impossible`. **The evaluator does not run commands or read files — it only judges what Claude's own output has already surfaced in the transcript.** Four failure classes clear the goal automatically (auth failure, exhausted credits, uncompactable context overflow, unavailable model); every other failure (including transient rate limits) leaves the goal active. Evaluation is capped: "if Claude keeps answering the evaluator without making progress (no tool use for several turns in a row), Claude Code stops the loop." |
| `github.com/anthropics/claude-code` issue #93744 (WebSearch, CITED) | Real-world defect report | "Stop condition evaluator cannot see the instruction passed via `/goal`, loops until it declares itself unachievable" — an independent confirmation, from actual users, of exactly the limitation goal.md documents structurally: the evaluator's view is bounded to what lands in the transcript. |
| `github.com/anthropics/claude-code` issue #66448 (WebSearch, CITED) | Real-world defect report | The evaluator call has a fixed ~30s timeout with no documented override, making it unreliable for goals whose proof is long (e.g. a long build/test run whose output must be summarized before the evaluator can see it). Reinforces: **the condition's proof must be cheap to state in-transcript**, not merely cheap to compute. |
| `docs/research/kb/reports/agents/goalrev-transcripts-2026-09-13.md` (this repo, tracked) | Local empirical evidence | In THIS repo, TWO `/goal` cycles already ran to completion this month with structured `goal_status: met:true` harness attachments (not self-reported prose). One goal was **REJECTED at a checkpoint** ("the feature is uncommitted... doctor integration is explicitly listed as 'not yet built'") — direct evidence the evaluator can catch a declared-done-but-not-actually-done state, provided the gap is visible in the transcript. |
| `docs/research/kb/reports/agents/goal-synthesis-2026-09-13.md` (this repo, tracked) | Local prior synthesis | Content-level advisory synthesis of the operator's 3-phase ask (update-all, dependency automation, graphify run) and open questions. This report reuses that CONTENT but changes its FORM per the operator's explicit ask this round: every check becomes a command + expected exit code / number, not an adjective. |
| Confident AI / Ampcome agent-eval guides (WebSearch, CITED, general industry) | Secondary, INFERRED-general | Independent (non-Anthropic) agent-eval literature converges on the same shape: turn "hazy" criteria into **numeric thresholds** ("<0.1% flagged in 10,000 trials"), and combine into **SLO-style AND-gates** ("completion rate > 85% AND p95 latency < 8s AND cost < $0.50") rather than a single vague adjective. |
| `.claude/rules/probes-need-a-control-arm.md` rule 9 (this repo) | House rule, CITED | "Assert the capability — never sniff for a symptom of its absence... feed the tool an input it must fail on and require the failure." This is the project's own falsifiability requirement, independently arrived at, and it agrees with the industry sources above: a check that cannot fail is not a check. |

## 1. What `/goal` mechanically is, and what it cannot do

**It is a real harness feature, not a project convention.** It is precisely: a
session-scoped prompt-based Stop hook wrapping a **small, fast, tool-less
model call**. Concretely this means three hard constraints on any condition
you write:

1. **The evaluator has no ground truth of its own.** It never runs `pytest`,
   never reads a file, never checks a git status. It reads the CONVERSATION.
   If Claude ran `pytest` and never printed the result, the evaluator cannot
   know pytest passed — confirmed independently by GitHub issue #93744
   ("cannot see the instruction... loops until unachievable") and named
   explicitly in goal.md: "write the condition as something Claude's own
   output can demonstrate."
2. **The proof must be transcript-cheap.** Issue #66448's ~30s evaluator
   timeout means a condition whose proof requires digesting a huge log
   (a full CI run, a 10,000-line pytest verbose dump) is unreliable — the
   proof Claude prints must already be the SUMMARY (an exit code, a count),
   not the raw artifact.
3. **A goal that never shows progress self-aborts.** "no tool use for
   several turns in a row" halts the loop and returns control with the goal
   still set — so a condition phrased as pure research/discussion with no
   tool-verifiable milestone risks silently stalling rather than completing.

**What it CAN do, demonstrated in this repo:** it correctly rejected a
premature "done" claim when the transcript itself contained the
contradiction (uncommitted code, an explicit "not yet built" note) —
`goalrev-transcripts-2026-09-13.md` §1. That is the evaluator working as
designed: it is a **transcript-consistency checker**, not an
oracle. Every condition below is written to hand it an unambiguous,
already-printed number or exit code to check consistency against — never a
computation it would have to perform itself.

## 2. The method: writing a condition the evaluator (and a human) can settle

Reconciling the vendor doc, the independent eval literature, and this
repo's own `probes-need-a-control-arm.md` rule 9 yields one method,
stated as a checklist. A condition clause passes when ALL of these hold:

1. **It names a command with an expected exit code or a number**, not an
   adjective. `"lint is clean"` fails this; `"mise run lint exits 0"` passes.
2. **Claude prints the exact evidence line in the transcript before
   claiming met.** Per constraint 1 above — if the evaluator can't see it,
   it can't verify it, regardless of whether it's true.
3. **The check can fail, and failing looks different from passing.**
   Per rule 9 ("assert the capability, never sniff for a symptom of its
   absence") — a check phrased so every possible transcript output reads as
   "met" is not a check. Concretely: prefer `rc == 0` (can be non-zero) over
   "the agent tried" (always true).
4. **The threshold is a number chosen in advance, not read off the result.**
   "Zero failures" chosen before the run is falsifiable; "an acceptable
   number of failures" chosen after seeing the count is not.
5. **Constraints that must NOT change are stated explicitly** (goal.md's own
   third bullet: "anything that must not change on the way there"). E.g.
   "no other test file is modified" — otherwise a literal-minded pass can
   satisfy the letter of a condition by breaking something adjacent.
6. **A condition that intrinsically resists exit-code proof (e.g. "code
   quality is good," "the design is elegant") is not usable as a `/goal`
   clause at all** — route it to human review (a PR description, a
   `/code-review` invocation) instead of forcing a numeric proxy that would
   misrepresent the judgment as mechanical.

## 3. Anti-pattern catalogue — this project's own unfalsifiable goals

| Anti-pattern | Live example in this repo | Why it's unfalsifiable | The fix (per the method above) |
|---|---|---|---|
| **Adjective with no instrument** | "fully automated w minimal to zero agent tokens" (operator's own 2026-09-13 handoff, quoted verbatim in `goalrev-transcripts-2026-09-13.md` §0) | No number is named ("minimal" relative to what?), and the one instrument that could measure it — `.agent/telemetry/` — **stopped writing on 2026-08-29** (15 days before this ask), per `goal-synthesis-2026-09-13.md` §3. Token spend now lands in agentsview's SQLite DB, which nothing in this repo's automation reads. The claim cannot be checked even in principle right now. | Split into two clauses: (a) a **process-shape** check that IS falsifiable today (does the automation run end-to-end with a bounded number of agent turns — see Phase 2 below); (b) an explicit, separately-tracked follow-up goal to restore the token-spend instrument before any numeric token-budget claim is attempted. Never let (a)'s green mask (b)'s absence. |
| **Adverb standing in for a threshold** | "does not have any errors" (update-all) | "Any errors" sounds falsifiable but was never pinned to a specific invocation shape — it silently tolerated `MISE_LOCKFILE=0 mise run -n update:all` (a **dry run**, `-n`) passing while a real mutating run remains unproven (#1043 open). | Name the exact command AND flag whether `-n` (dry-run) satisfies it or only a real run does. See Phase 1 below — both are now separate, explicit clauses. |
| **A goal proven only by a probe that cannot fail** | An early version of the doctor's plugin-health check reportedly returned `rc=0` regardless of actual health (see `project_session_2026-09-13-d.md`: "`claude mcp list`/`claude doctor` exit 0 regardless of health") | If the passing case and the failing case produce the same exit code, the check has no discriminating power — this is exactly rule 9's "a check that can only pass is not a check." | Any check embedded in a `/goal` clause must be control-arm-verified BEFORE being cited: prove it can return non-zero on a known-bad input (see Phase 2's canary requirement below). |
| **Scope creep disguised as ambition** | "run all relevant [graphify] commands... no cost bound" | "All relevant" and "no cost bound" together admit no failure mode — any subset of commands run, for any duration, satisfies the letter of the condition. | Bind it to an enumerable, checkable set: the installed CLI's own `--help` output IS the enumeration; the condition becomes "every subcommand listed under X ran and exited 0, OR is explicitly logged as skipped with a reason" — see Phase 3 below. |
| **A number inherited without re-derivation** | The handoff's "3 breakages" figure for update-all, later corrected to 2 in the SAME session because a config had changed underneath it (`goalrev-transcripts-2026-09-13.md` §3) | An inherited number carries no control arm of its own — this repo's `probes-need-a-control-arm.md` rule 6 names this exact failure. | Every phase below states its numbers as OF-THIS-SESSION, re-derived at goal-set time, never carried forward from a prior report without re-running the check. |

## 4. The rewritten goal — three phases, each check is a command + expected result

Per-phase form: **Outcome** (one sentence) → **Measurable check(s)** (command,
expected exit code/number, printed BEFORE claiming met) → **Today vs.
needs-an-instrument-first** (what can be checked with zero new tooling vs.
what requires building something first).

### Phase 1 — `update-all` runs clean

**Outcome:** `mise run update:all` (the real, mutating invocation — NOT
`-n`/dry-run) completes without error, without relying on the
`MISE_LOCKFILE=0` workaround baked in as a standing tax.

**Measurable checks (state ALL, print each exit code in the transcript):**
1. `mise run update:all` (no `-n`, no `MISE_LOCKFILE=0` override) → **exit 0**.
2. `uv run --project python pytest tests/ -x -q` immediately after → **exit
   0**, and the printed summary line's failure count is **0**.
3. `mise run verify` → printed "N passed / 0 failed" with **0 failed**
   (verify's own convention, matching `verify-before-advancing.md`'s
   evidence discipline).
4. If (1) requires an upstream fix rather than a config toggle (per
   `goal-synthesis-2026-09-13.md` Q1), the fix's mechanism is named
   explicitly in the transcript (e.g. "set `MISE_LOCKFILE=0` permanently in
   `mise.toml`" vs. "filed mise issue #NNNN, workaround remains") — either
   is acceptable, but the condition is NOT met on a silent workaround that
   isn't declared as such.

**Today vs. needs-an-instrument:** Fully checkable TODAY with existing
tooling — no new instrument needed. The only unresolved fact is which of
Q1's three options (A/B/C in `goal-synthesis-2026-09-13.md`) the operator
picks; that is a human decision, not a measurement gap.

### Phase 2 — autonomous dependency-currency automation

**Outcome:** Stale pins in `mise.toml` and `pyproject.toml` are detected,
bumped, gated, and shipped (or reported-and-dropped on red) without a human
in the loop for the common case, via skill → mise task → python module,
using `mise run ship` with auto-merge on green.

**Measurable checks:**
1. **Structure check (static, exit-code-checkable):**
   `git log --oneline -- python/src/dotfiles_setup/*.py .claude/skills/**/SKILL.md` for the
   new automation shows the skill → mise-task → python-module chain exists
   as three distinct, separately-committed artifacts (not one script) —
   verified by `grep -l` finding a `mise run <name>` invocation inside the
   skill file AND a `python/src/dotfiles_setup/<module>.py` referenced from
   `mise.toml`'s task body. Exit code of the grep chain: **0** (found), not
   "looks skill-shaped."
2. **End-to-end dry run, numeric:** Triggering the automation against a
   FIXTURE containing at least one genuinely-stale pin and one genuinely
   red/incompatible pin must produce: stale pin bumped (diff exists, `git
   diff --stat` shows a changed line count **> 0** for the stale pin) AND
   the incompatible pin left untouched with a report artifact naming it
   (a file exists at the reported path, checked via `test -f`, exit **0**).
3. **Canary requirement (rule 9 control arm, MANDATORY before this phase is
   claimed met):** Feed the automation a pin it MUST reject (e.g. a version
   string that does not exist upstream) and require it to exit non-zero /
   produce the "dropped and reported" path, not silently succeed. Print
   both the injected-bad-pin's exit code (expected **non-zero**) and a
   known-good pin's exit code in the SAME transcript block, so the
   evaluator (and a human reviewer) sees the discriminating pair, not one
   arm alone.
4. **Live gate, per bump:** the actual PR (opened via `mise run ship`) shows
   `gh pr checks <n> --json` with every check `pass` or `skipping` and
   **0 fail**, then auto-merges (verified via `gh pr view <n> --json
   state,mergedAt` showing `state: MERGED` with a non-null `mergedAt`) —
   OR, for an image-build-input bump, a SEPARATE PR per the handoff's
   documented split (Q2 option A in `goal-synthesis-2026-09-13.md`).
5. **Token-cost clause (the "near-zero agent tokens" ask, made falsifiable
   for TODAY only in its process-shape sense):** the automation's mise task
   completes the trigger→PR step **without invoking Claude Code at all**
   (i.e. it is a deterministic `python/` module run by mise/cron, not a
   Claude session) — checkable by `ps`/log evidence that no `claude` process
   ran during the automation window, exit-code style: **0 Claude Code
   invocations logged for this automation run.**

**Today vs. needs-an-instrument:** Checks 1–5 above are ALL checkable
today with no new instrument — note that check 5 is a **process-shape**
proxy (no Claude Code invocation during automation), not a genuine token-COUNT
budget. **A numeric token-spend threshold ("used fewer than N tokens")
cannot be asserted honestly until `.agent/telemetry/` is restored or the
agentsview SQLite DB is read by something in this repo** — that is a
named, separate prerequisite, not silently folded into "done." State it
in the transcript as: *"Process-shape automation verified (0 Claude
invocations); numeric token-spend threshold NOT measured — telemetry gap
open, tracked separately."*

### Phase 3 — full graphify run

**Outcome:** Once graphify (target 0.9.61+) is installed with its skills
properly wired, this project runs every graphify command relevant to deep
extraction, reflection, and generated artifacts.

**Measurable checks:**
1. **Enumeration is a command, not a memory.** `mise run graphify-query --
   --help` (or the installed CLI's own `--help`) is run and its output
   captured; the transcript states the exact subcommand count printed
   (e.g. "27 subcommands listed") — this is the falsifiable enumeration
   basis per anti-pattern §3's fix.
2. **Per-command exit code table.** For every subcommand judged relevant
   (deep extraction, reflection, generated-artifacts categories — judged by
   a human/Claude reading the `--help` text, not invented from memory), the
   transcript prints a table: `command | exit code | artifact path or
   skip-reason`. The condition is met when every row is either **exit 0
   with an artifact that exists** (`test -f`/`test -d` exit 0) or
   **explicitly logged as skipped with a named reason** (e.g. "requires a
   paid API key, not configured") — an unexplained blank row fails the
   condition.
3. **Staleness caveat, stated not silently dropped:** per
   `goal-synthesis-2026-09-13.md`'s Deciding Risk, the transcript states
   explicitly: *"Graph staleness between future runs is not automatically
   detected — #1050 rebuild-trigger automation is separate, tracked
   work."* This is a Phase-3-done-criterion line item, not an afterthought.

**Today vs. needs-an-instrument:** Blocked until graphify 0.9.61+ is
actually installed (a version-string check: `graphify --version` printing
`>= 0.9.61`, exit 0) — that installation is itself Phase 3's precondition,
not yet satisfied as of this report. Everything else (the enumeration
method, the per-command table) is checkable the moment installation lands.

## 5. Applying `/verify` and the blanket constraint

Per the operator's standing instruction, append to EVERY phase above the
same closing clause, made concrete: **`mise run verify` prints a summary
with 0 failed, run AFTER the phase's own checks, in the same transcript
block** — not a separate unlogged pass. This is what makes "all changes
must run `/verify` to confirm they work and are not fragile" itself
falsifiable: the printed 0-failed line is the proof, not the intention to
have run it.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issue #93744 (evaluator cannot see the goal instruction, loops to "impossible") and issue #66448 (evaluator ~30s timeout, no override) cited as independent confirmation of the transcript-only evaluation constraint documented in the vendor's own `/goal` doc.
