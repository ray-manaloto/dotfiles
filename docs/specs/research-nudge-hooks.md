# Build plan — enforce research + adversarial review in the wayfinder loop

> **STATUS: NO-SHIP (2026-07-31). Superseded pending redesign. Nothing here is built,
> and the tiers below should NOT be built as written.**
>
> A Codex adversarial review returned `needs-attention` with four high findings and one
> medium — the full text is in [Appendix A](#appendix-a--codex-adversarial-review-verbatim),
> verbatim. Its core objection: every tier is the same *class* of mechanism as the eager
> rule that already failed twice, so changing delivery time does not establish completion.
> It proposes a different shape — **ticket-bound receipts plus a fail-closed resolution
> workflow** — with `SubagentStart` promoted from footnote to primary lever.
>
> **The findings are now VERIFIED (2026-07-31)** — see
> [Appendix C](#appendix-c--verification-results-2026-07-31-measured). Four survive intact; the
> fifth (`SubagentStart`) survives as a mechanism but its stated premise is measurably wrong —
> both documented misses launched **zero** subagents. Appendix B is the method; Appendix C is the
> result.
>
> The research below (29 hook events, the md5 cross-check, the statusline sensor, the two
> hard constraints) stands on its own measurements and survives the redesign. The *design*
> does not.

Written 2026-07-31 after two misses in one session: five decisions on #436 were designed before
anyone read chezmoi's docs (it ships native `[hooks]` that do the job), and the chezmoi-vs-mise
overlap was re-derived despite `deep-research-takeover-20260730.md` having already answered it. Both
were caught by Ray asking, not by the loop.

## The problem, stated precisely

**A rule is not enough, and we have direct evidence.** `.claude/rules/tool-currency-and-native-first.md`
rule 1 says, in as many words: *research the tool's release notes before writing custom tooling around
it.* It is unscoped, therefore eager, therefore loaded at launch. It was loaded in that session. It
did not fire — twice. Adding a rule file is the option measured to have already failed.

The three structural gaps:

1. **Wayfinder's ticket types are disjoint.** `research` is its own AFK type resolved by subagents at
   *charting* time. A `wayfinder:grilling` ticket has **no research step at all**, so a decision about
   a third-party tool can reach its answer without that tool's docs being opened.
2. **Adversarial review has no seat.** Map #431's `## Notes` name `/grilling`, `/domain-modeling`,
   `/prototype`, `/research` — no review lens, despite `feedback_refuters_and_cold_review_find_disjoint_defects`
   recording that refuters and cold review find *different* defect classes.
3. **Prior research is not consulted.** `docs/research/kb/reports/agents/` is the durable record and
   nothing in the flow reads it before starting new work.

## What the harness actually offers

Established from the KB mirror `sources/agent-harness-docs/docs/claude-code/hooks.md`, which is
**md5-identical** to the live `code.claude.com/docs/en/hooks.md` fetched the same day
(`0a8c3a6542d7c5085c1b451b994b9ce8`; a control file hashes differently, so the comparison
discriminates).

⚠️ **A first pass at this list was wrong, and the way it was wrong matters.** It grepped an
alternation of the event names already expected and found exactly those — 11. An unbounded
`^### [A-Z][A-Za-z]+$` returns **29**. Everything below rests on the unbounded enumeration.

| Event | Bearing on this plan |
|---|---|
| `UserPromptSubmit` | Once per turn, before the prompt is processed. Receives raw `prompt`. `additionalContext` is **injected as a system reminder with no visible transcript entry**. ⚠️ 30s default timeout, and a timed-out hook's context is **discarded** — the prompt proceeds without it. So the check must be a pure string match, no network. |
| `PreToolUse` | Every tool call. `permissionDecision` ∈ allow / **ask** / deny / defer; precedence deny > defer > ask > allow. For `ask`, `permissionDecisionReason` is shown **to the user, not to Claude**; `additionalContext` is the field that reaches Claude. |
| `SubagentStart` | Cannot block, but **injects `additionalContext` into the subagent's context**, matched on `agent_type`. The only route to enforcing research discipline on delegated work. |
| `PermissionRequest` | Distinct from `PreToolUse` — fires only when permission is about to be asked, or a call would be auto-denied. |
| `async` / `asyncRewake` | Command hooks only. Cannot block or return decisions; output arrives **next turn**. `asyncRewake` wakes Claude on exit code 2 with stderr shown as a system reminder. |
| Statusline (not a hook) | Hooks receive **no** context usage — control-armed: `transcript_path` → 35 mentions in hooks.md, `context_usage`/`token_count`/`percent` → **0**. The statusline receives `context_window.used_percentage`, `total_input_tokens`, and a broken-out `current_usage`. |

**Two hard constraints that no design removes:**

- `/clear` is a CLI command, and `clear-prep`, `handoff`, `resume` and `wayfinder` are all
  `disable-model-invocation: true`. **Claude cannot invoke any of them.** Automation can prepare
  everything and nudge; the keystroke stays human.
- Ray's statusline is configured at **user** level (`node $HOME/.claude/hud/omc-hud.mjs`). A
  project-level `statusLine` overrides it. **Decided 2026-07-31 (Ray): overriding is fine — we are
  migrating away from the OMC HUD regardless.** So tier 2 replaces rather than wraps. Note the
  override is scoped to this repo; every other project keeps the user-level HUD until the wider
  migration happens, which is not part of this plan.

## Proposed build

### Tier 1 — the nudges (no statusline, no user-level changes)

Ray selected all three triggers.

1. **`UserPromptSubmit`** — matches `/wayfinder`, `/grilling`, `/mattpocock-skills:*` in `prompt`.
   Emits `additionalContext`: read the tool's primary docs and release notes; grep
   `docs/research/kb/reports/agents/` for prior coverage first; run adversarial review before
   resolving. Pure string match, no IO beyond the match — the 30s timeout must never be approached.
2. **`PreToolUse`** on `gh issue edit <n> --add-assignee` — `allow` + `additionalContext`, same
   checklist. Covers a ticket claimed without `/wayfinder` being typed (resumed session, work picked
   up mid-flight).
3. **`PreToolUse`** on `gh issue close` / a resolution comment on a `wayfinder:*` ticket — **`ask`**,
   not `deny`. The guard cannot verify research happened, so a `deny` would make closing any
   wayfinder ticket impossible. `ask` puts the judgement with Ray.

This is a **new output shape for `hook_guard.py`**, which today emits only `deny`. `ask` and
`additionalContext` are new capabilities, requiring their own tests and a suites.toml contract, plus
`since` dates per `mise-tasks-only.md` § "since dates COVERAGE".

### Tier 2 — the context-budget trigger

Sensor → channel → actuator, because the sensor and the actuator are different subsystems:

- **Sensor:** a project `statusLine` script (`python/`, per zero-bash-logic) that writes
  `context_window.used_percentage` to `~/.local/state/dotfiles/context-usage`.
- **Actuator:** a `Stop` hook (once per turn) reading that file; above threshold, emits a reminder
  to run `/clear-prep`.

⚠️ **Replace-vs-wrap was reopened by measurement.** Overriding the HUD was sanctioned on the
assumption it was a dead shim. It is not. Fed representative statusline JSON on stdin it returns
rc=0 and renders:

```
[OMC#4.15.7L] | Model: Opus 5 | 5h:[#-------]12%(1h28m) wk:[##------]25%(4d14h)
extra:[####----]55%($109.73/$200.00) | session:0m | ctx:[####------]42%
```

So it already carries the **5-hour window**, the **weekly window**, **credit spend against a cap**,
session duration — and it **already reads `used_percentage` itself**. Those first three are exactly
what `builder-skills:stay-within-limits` needs and nothing else in the setup provides. It works
despite `oh-my-claudecode` being absent from `enabledPlugins`, because `~/.claude/hud/omc-hud.mjs` is
a **resolver shim** that imports from the plugin *cache* (6 built copies present), independent of
enablement.

⇒ **Recommended: wrap, not replace.** A project `statusLine` that tees stdin — hand it to the HUD,
print the HUD's output verbatim, and separately write `used_percentage` to the state file. Costs
nothing, loses nothing, and survives the eventual OMC migration by being one `exec` line to
re-point. Replacing is still available if Ray wants the HUD gone now, but it is a strict loss of the
usage and cost meters until something reimplements them.

**Residual risk that survives either choice:** `current_usage` is `null` before the first API call
and again immediately after `/compact` until the next call. The state file therefore has a genuine
unknown state, and the actuator must treat "no reading" as "no nudge", never as "0%".

### Tier 3 — the wayfinder map's `## Notes`

Notes are ours, not vendored, and wayfinder states that a session invokes the skills the Notes name.
Add the research + adversarial step there so it applies to every ticket on map #431 without touching
the plugin.

## What is deliberately NOT proposed

- **Auto-advance on "no issues or ambiguity found".** That judgement is exactly what failed twice.
  Both times the honest self-report would have been "no ambiguity". Keying auto-advance on *evidence*
  — a research artifact exists, an adversarial review returned findings — is a different and safer
  trigger, but it is not this plan.
- **Merging `handoff` into `clear-prep`.** They are already deliberately different and both
  frontmatters say so: `clear-prep` (247 lines) is same-machine `/clear` continuity; `handoff`
  (83 lines) is cross-surface, tracked and pushed, with `resume` as its other half.
- **A new rule file.** See the opening paragraph.

## Questions an adversarial review should attack

1. Does tier 1 actually prevent the failure, or only make it visible later? The `UserPromptSubmit`
   nudge is still instruction-following — better-timed instruction-following, but not a gate.
2. Is `ask` on close a speed bump that gets clicked through? What would make it carry information
   rather than become reflex?
3. Does the statusline wrapper introduce a worse failure than the one it detects?
4. Is `SubagentStart` the better primary lever, given delegated work is where research is most often
   skipped and it is the one place context can be injected unconditionally?
5. Three overlapping nudges — does redundancy here reduce misses, or train the reader to skim all of
   them?

## Appendix A — Codex adversarial review, verbatim

Run 2026-07-31, `--scope working-tree`, GPT-5.6 via `codex-companion.mjs`. Reproduced unedited.

> Target: working tree diff
> Verdict: needs-attention
>
> No-ship: the proposal multiplies reminders around a behavior that already ignored an eagerly loaded instruction twice. It provides no evidence-backed completion gate and adds silent fail-open, click-through, and fragile statusline paths. The loop needs a different mechanism, not more instruction-shaped nudges.
>
> Findings:
> - [high] No proposed tier makes research or adversarial review a prerequisite (docs/specs/research-nudge-hooks.md:61-78)
>   Tier 1 emits checklists, Tier 3 adds another instruction, and the plan explicitly declines the only evidence-oriented alternative. These are the same class of mechanism as the eager rule that lines 12-15 say failed twice; changing delivery time does not establish completion. The likely result is false confidence while unresearched decisions still resolve normally.
>   Recommendation: Do not build these tiers as enforcement. Define ticket-bound research and adversarial-review receipts, then make the supported resolution workflow fail closed when required evidence is missing or stale. Otherwise label the hooks as optional UX reminders and do not claim they fix the loop.
> - [high] The only unconditional delegated-work injection is omitted from the build (docs/specs/research-nudge-hooks.md:61-78)
>   The draft identifies delegated research as the structural gap and calls SubagentStart the only route that injects context directly into a subagent, yet none of the three Tier 1 triggers uses it. The proposed Notes path still depends on the agent noticing and following instructions. The workflow most responsible for research therefore remains untouched.
>   Recommendation: Make narrowly matched SubagentStart context the primary delivery mechanism for research workers, and require those workers to emit a ticket-bound artifact. Because SubagentStart cannot verify completion, pair it with the resolution evidence gate rather than treating injection alone as enforcement.
> - [high] The close-time ask cannot support an informed approval (docs/specs/research-nudge-hooks.md:72-78)
>   The plan admits the guard cannot verify that research happened, but still asks Ray to judge closure without presenting ticket-specific evidence. A repeated generic permission dialog provides no basis for distinguishing completed work from another miss and is likely to become reflex approval. It therefore adds friction without closing the failure path.
>   Recommendation: Have the guard report concrete receipt paths, source identities, review results, and missing requirements. Missing evidence should deny closure through a supported remediation workflow; reserve ask for genuine exceptions carrying enough evidence for a deliberate decision.
> - [high] The statusline side channel can lose the existing HUD and consume stale or cross-session state (docs/specs/research-nudge-hooks.md:82-113)
>   The single home-directory state file is not scoped by session and has no freshness or atomicity contract. Concurrent sessions can overwrite each other's percentages, and a null reading after compaction can leave a previous high or low value indistinguishable from current state. The wrapper also makes the working usage/cost HUD depend on new parsing, file I/O, and an unenabled plugin-cache shim; an uncaught child failure can remove the visibility the change is meant to preserve. The assertion that wrapping costs and loses nothing is unsupported.
>   Recommendation: Split Tier 2 from this proposal. Before adoption, key state by session, record timestamp and explicit unknown state, use atomic replacement and expiry, isolate and time-bound the HUD child, preserve a fallback display, and test concurrent sessions, null-after-compact, missing cache, malformed input, and child timeout.
> - [medium] UserPromptSubmit silently fails open when its context is most needed (docs/specs/research-nudge-hooks.md:41-68)
>   The draft states that timeout discards additionalContext and proceeds with no visible transcript entry. A fast regex does not bound process startup, interpreter, wrapper, scheduling, or hook-wiring failures, so 'must never be approached' is not a guarantee. Tests of matching logic would not reveal runtime delivery loss, leaving the nudge absent and unobservable.
>   Recommendation: Remove UserPromptSubmit from the correctness boundary. Add wired end-to-end self-checks and fail-open telemetry if retained as a reminder, while enforcing completion later through durable evidence that survives hook timeout or absence.
>
> Next steps:
> - Redesign the wayfinder loop around verifiable per-ticket artifacts and a fail-closed resolution workflow.
> - Prototype SubagentStart plus receipt generation against the two documented miss scenarios.
> - Review the statusline sensor as an independent reliability change only after concurrency and degraded-mode behavior are specified.

## Appendix B — verifying the findings before acting

A review is evidence, not a verdict, and this repo's own rule is that an inherited claim is not a
measurement ([[probes-need-a-control-arm]] rule 6). Each finding below is checkable; check it before
building against it.

| Finding | What would confirm it | What would refute it |
|---|---|---|
| No tier is a prerequisite | Trace the two real misses: would any tier have *stopped* the decision from resolving? Neither a `UserPromptSubmit` reminder nor a Notes line can — both are readable-and-ignorable. | A tier that gates rather than informs. None is proposed, so this looks **correct as stated**. |
| `SubagentStart` omitted | Confirm it is absent from all three Tier 1 triggers (it is) **and** that delegated work is where the misses happened. ⚠️ This half is doubtful: **both misses this session were made inline, not by a subagent.** | If neither miss involved delegation, `SubagentStart` is the right lever for a *different* failure than the one observed — an important scoping correction, not a refutation of the mechanism. |
| Close-time `ask` is uninformed | Confirm `permissionDecisionReason` is shown to the user but not to Claude (measured: it is) and that the guard has no receipt to cite. | A receipt format existing to cite. There isn't one yet, so **correct**, and it is the same gap as finding 1. |
| Statusline state is unscoped / non-atomic | Read back the tier-2 text: the state file is a single unscoped path with no timestamp or atomicity. **Correct as written.** Also verify the "wrapping loses nothing" claim — measured against the HUD's real output, which does render usage and cost. | Nothing refutes the concurrency point; multiple Claude Code sessions on this Mac are routine. |
| `UserPromptSubmit` fails open | Confirm from the hooks doc that a timed-out hook's context is discarded and the prompt proceeds (measured: it is, with a transcript notice only since v2.1.196). | The claim that a regex "must never approach" 30s ignores process startup — **correct**; the mitigation was asserted, never measured. |

**The one finding to push back on** is the second: it asserts delegated research is the structural
gap, but the two documented misses were both made inline by the main session. Adopting
`SubagentStart` as the *primary* lever would harden a path that did not fail, while leaving the path
that did. Worth resolving before the redesign commits to it.

## Appendix C — verification results (2026-07-31, measured)

Appendix B's checks were run. Every number below was **re-derived**, not inherited from the
handoff ([[probes-need-a-control-arm]] rule 6), and every negative carries its control arm.

**Verdict: 4 of 5 findings survive intact. F2 survives as a mechanism but its stated premise is
measurably wrong. F5's severity is lower than argued, but its conclusion survives on a stronger
argument than the one it was filed under.**

| # | Finding | Verdict | Decisive evidence |
|---|---|---|---|
| 1 | No tier is a prerequisite | **CONFIRMED** | Read-back: 1.1/1.2 emit `additionalContext` (informational), 1.3 emits `ask` (gates on judgement, not evidence), tier 3 is prose. No tier keys on an artifact existing. |
| 2 | `SubagentStart` omitted | **mechanism CONFIRMED · premise REFUTED** | Both miss sessions launched **0** subagents (`6b4602f4`: Agent=0, `subagent_type`=0, control Bash=132; `d4299a7a`: 0/0/48) against **239** Agent launches across all 181 project transcripts. `SubagentStart` would have fired **zero times** in the session it is proposed to fix. |
| 3 | Close-time `ask` is uninformed | **CONFIRMED (both halves)** | (a) hooks.md:1551 verbatim — *"For `allow` and `ask`, shown to the user but not Claude"* (control: `additionalContext`→40, bogus token→0). (b) No ticket-bound receipt convention exists: `reports/agents/` is 16 files, of which **1** (`concurrency-sweep-433.md`) carries a ticket; the other 15 are topic+date. ⚠️ The control arm originally cited here was wrong — see the correction below. |
| 4 | Statusline state unscoped / non-atomic | **CONFIRMED · premise now measured** | The path is global — keyed by neither session **nor project** — with no timestamp, atomic replace, or expiry. Concurrency, asserted in Appendix B, measured across all `~/.claude/projects` (251 transcript files, 7-day window, bucketed by the hour of each `"timestamp"` inside the file): **61 of 92 hours (66%) had ≥2 transcripts active.** Collision is the normal case. ⚠️ See the correction below on the peak. Note the F4 sub-claim about *wrapping* was **not** checked — see below. |
| 5 | `UserPromptSubmit` fails open | **direction CONFIRMED · magnitude CORRECTED** | See below. |

### Finding 5 in detail — the right conclusion for the wrong reason

The spec's mitigation ("pure string match ⇒ the 30s timeout must never be approached") was
asserted. Measured on `scripts/pretooluse-guard.sh` — the closest live analogue — 20 sequential
runs on a genuinely loaded host (load avg 15.23/19.34/31.66): **min 256 ms · median 1013 ms ·
max 1978 ms**, i.e. **6.6% of the 30s budget, ~15× headroom**. The regex is free; the *wrapper*
costs about a second. **Timeout is not the realistic failure mode**, so Codex overstates that half.

> A first 20-run batch read max = 3914 ms and was **discarded**: the measuring command had itself
> spawned 20 background processes. It measured its own load. Re-run clean.

Its *other* half is the real one, and it is stronger than the timeout argument: **absence is
unobservable**. Armed both directions — hiding the interpreter (`PATH=/usr/bin:/bin`) makes the
wrapper exit 0 *and* write `interpreter-absent` to the fail-open log; the same input on a normal
PATH writes nothing. The path works and discriminates, and
`~/.local/state/dotfiles/guard-fail-open.log` does not exist — a real negative, meaning the
PreToolUse guard has not failed open since #343's telemetry landed.

⚠️ **But that telemetry is wrapper-side.** A harness-side *timeout kill* never reaches
`fail_open()`, so it leaves no trace at all. A hook cannot record its own death. Whatever
establishes that research happened must therefore be **durable evidence outside the hook** — which
is finding 1's recommendation arriving by a second route.

### The scoping correction F2 forces

`SubagentStart` is not useless — 239 delegations across ~50 transcripts is real traffic, and
research delegated to a subagent is genuinely uninstrumented. But it addresses a path that **has
not been observed to fail**, while both observed misses were inline. A redesign that makes it the
*primary* lever hardens the wrong path. It belongs in the design as a **secondary** lever, and the
primary one must cover inline main-session work.

### What all five findings converge on

Findings 1, 3 and 5 arrive independently at the same missing thing: **a ticket-bound receipt**.
F1 wants a completion gate to key on; F3 wants something for the guard to cite; F5 wants evidence
that survives the hook not running. That artifact does not exist today — which makes it the first
thing the redesign must define, ahead of any hook.

Finding 4 is separable and should be split out, exactly as Codex recommends.

## Appendix D — corrections from the two-axis code review (2026-07-31)

Appendix C was then reviewed on a Standards axis and a Spec axis. **The Spec axis found a real
defect in Appendix C's own evidence**, which is recorded here rather than silently patched.

### D1 — "peaking at 4" was WRONG, and it was my own display bound

Appendix C's F4 row read *"60 of 91 hours (66%) had ≥2 sessions active, **peaking at 4**."* The
peak does not reproduce. The probe printed only `sorted(multi)[-8:]` — **the last eight hours
chronologically** — and the peak was read off that sample rather than off the full set.

Re-run over the same window, printing the true maximum:

```
files=251  hours>=1=92  hours>=2=61 (66%)
TRUE MAX = 154        top ten hour sizes: [154, 20, 17, 10, 9, 6, 6, 6, 5, 5]
hours exceeding 4: 12
```

**12 hours exceed 4**, and the top hour (`2026-07-28T02Z`) has **154** — 78 in the knowledge-base
project dir, 74 under the home dir, consistent with that day's parallel graphify queue.

This is exactly the failure [[probes-need-a-control-arm]] rule 3 names under **display bounds**
(`| head`, `| tail`, a bare listing) — committed in a document whose subject is evidence
discipline, and published to #449 before it was caught.

⚠️ **What the figure actually counts.** Distinct **transcript files** with a timestamp in the hour
— which conflates interactive sessions with subagent and queue-spawned transcripts. It is an upper
bound on concurrent human sessions, not a count of them. The hours-with-≥2 figure (61/92, 66%) is
robust to that; the peak is not. **The conclusion is unaffected and if anything strengthened:
collision is the normal case.**

### D2 — F3(b)'s control arm was the wrong corpus AND the wrong component

Appendix C cited *"control: 28 filenames match the date convention"*. Two defects:

- **Wrong corpus.** 28 spans `reports/agents/` **plus** `docs/research/runs/` (mostly directories).
  The claim under test is about `reports/agents/` alone, where only **3** filenames carry a date.
- **Wrong component** — the more serious one. The claim under test is that **no ticket-bound naming
  convention exists**. A *date* matcher firing proves the regex machinery works; it does not show
  that a **ticket** matcher discriminates. That is [[probes-need-a-control-arm]]'s "arm the
  component you actually depend on" — a control aimed at the link that was never in doubt.

The finding itself stands (1 of 16 carries a ticket, and that one is `concurrency-sweep-433.md`),
but it stands on the direct enumeration, not on the control that was cited for it.

### D3 — F4's second half was never checked

Appendix B asked for two things on F4. The second — *"Also verify the 'wrapping loses nothing'
claim"*, against Codex's *"The assertion that wrapping costs and loses nothing is unsupported"* —
**was not run**, and Appendix C reported F4 as though it had been. Recorded as open, not as done.

### D4 — F1 was answered by read-back, not by the trace that was asked for

Appendix B's F1 confirm column asked to *"Trace the two real misses: would any tier have stopped
the decision from resolving?"* Appendix C answers from the document's own text instead. The
conclusion is very likely right — no tier gates on evidence — but the asked-for check was not the
check performed. Judgement call, recorded for honesty.

### D5 — the md5 was inherited; now re-derived, and its harder half still is not

The `0a8c3a6542d7c5085c1b451b994b9ce8` hash arrived from the prior session. Re-derived:
`md5 -q` on the mirror returns exactly that, and a sibling doc (`accessibility.md`) returns
`055854e3…`, so the comparison discriminates. **But that only re-derives the mirror's own hash.**
The load-bearing claim — that it equals the *live* `code.claude.com` doc — remains inherited from
the day it was fetched, and a live doc drifts. Treat the mirror as current-as-of-2026-07-30.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the
  `sources/agent-harness-docs/docs/claude-code/hooks.md` mirror that every hook-behaviour claim in
  this document rests on (md5-verified against the live doc, see D5).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo;
  `scripts/pretooluse-guard.sh` was read and timed for the F5 latency measurement.

The upstream documentation itself (`code.claude.com/docs/en/hooks.md`) is Claude Code's own hooks
and statusline reference, not a GitHub repo.
