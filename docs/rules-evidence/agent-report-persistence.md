# Evidence — `agent-report-persistence`

Case history behind `.claude/rules/agent-report-persistence.md`. Extracted so
the eager copy carries the directive and the five operative rules, and this file
carries the three incidents that produced them.

## Why persist at all (2026-07-05)

An 11-agent release-notes sweep produced **13 detailed reports** — syntax
sketches, file:line misconfiguration tables, probe transcripts, a backend status
matrix. The notepad got condensed summaries as the work progressed, but the full
reports existed **only in the session's context window**: one `/clear` away from
being lost. A manual round-2 pass recovered them.

**Condensation is lossy in exactly the way that hurts later.** The summary keeps
the conclusion and drops the evidence, the exact command lines, and the file:line
anchors the *implementing* session needs.

## Why INCREMENTALLY, not at the end (2026-07-20)

Two agents held everything in memory, **died silently after ~40 minutes, and
left nothing.** Re-dispatched with an explicit incremental instruction, they
produced output within minutes.

The arithmetic is the whole argument: an agent that dies having written 13 of 20
sources leaves **13**. An agent that dies planning to write all 20 at the end
leaves **0**. Same principle as `PostCompact` / `SubagentStop` capture — durable
capture must be incremental, never end-of-run.

## The path change, and what two conventions cost (2026-07-20)

The old path was `docs/research/runs/<topic>/agents/`; the current one is
`docs/research/kb/reports/agents/<agent-name>.md`.

`docs/research/kb/` is the corpus root and is **tracked in git** (added with
`git add -f`, since `.git/info/exclude` carried `.agent/*`), so artifacts survive
a fresh clone. `docs/research/runs/**` is not tracked and does not.

**The two conventions co-existed for exactly one session and immediately cost
something:** an agent correctly followed the *old* rule, the caller looked in the
*new* path, and wrongly reported the agent as non-compliant. One path.

Existing `docs/research/runs/**` artifacts stay where they are; new ones go to
`docs/research/kb/`. See memory `feedback_store_research_in_graphify`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `docs/research/kb/`, `.claude/skills/session-handoff/SKILL.md`.

## 2026-09-09 — audit refactor

**Findings applied:** `rule-agent-report-persistence-1` through `-5`.

**Native anchors re-read:** `hooks.md:314` (SubagentStart matchers filter agent
types); `hooks.md:870` and `:888` (start-hook failure is non-blocking and stderr
is visible only in the subagent transcript); `hooks.md:2304-2317`
(`SubagentStart` `hookSpecificOutput.additionalContext`); `hooks.md:2319-2346`
(SubagentStop context returns to the delegate; parent context requires
PostToolUse on `Agent`); `sub-agents.md:1051-1057` (the native
`agent_transcript_path`).

**Wiring probes:** `.claude/settings.json` now has one unscoped command entry
for each event, both running
`python -m dotfiles_setup.hook_selfcheck subagent-contract`. The real-entry arm
passes. Deleting `SubagentStart` or `SubagentStop` independently fails
`check_settings_wiring`; the runtime arm observes start context, a first-stop
reminder, and a silent recursive stop. A missing registration therefore cannot
remain invisible to ship/land selfcheck.

## The stop channel: `additionalContext`, not `decision: "block"` (2026-09-10)

The first implementation returned `{"decision": "block", "reason": ...}`. It was
live from the working tree while the A-2 codex lane ran, and the lane could not
idle: it re-delivered its report **three times**, each opening by re-explaining
that "this hook fires mechanically on every Stop attempt … N/A-by-design". The
hook was working exactly as coded; the problem is that `block` renders as a hook
*error*, so a lane that had already complied read the reminder as an objection
and argued with it.

`hooks.md:2346` documents that SubagentStop accepts
`hookSpecificOutput.additionalContext` with `hookEventName: "SubagentStop"` for
**non-error feedback that keeps the subagent running**, and `hooks.md:2549` says
to use it "when the hook is working as designed and giving Claude guidance" —
same `stop_hook_active` guard, same 8-continuation cap, but labelled `Stop hook
feedback` with no error notification. That is precisely this hook's job, so the
stop arm now uses it.

**Both arms run (2026-09-10).** Restoring the original
`{"decision": "block", ...}` body — the realistic regression, since it is the
code that was actually written — turns `check_subagent_contract_endtoend` red
with two failures (lost required output; forbidden `"decision"` channel);
restoring `additionalContext` returns it to `[]`. The explicit forbid is
load-bearing: `block` and `additionalContext` **both** keep the delegate
running, so no liveness- or presence-shaped assertion can tell them apart.

**Loop-guard scope, corrected.** `stop_hook_active` is true only while Claude
Code is already continuing the delegate as a result of a stop hook
(`hooks.md:2470`) — it guards recursion within ONE continuation chain. A new
parent message starts a new chain, so a long-lived named agent pays the reminder
once per message received, not once per session. The three re-deliveries above
are consistent with that: the lane received three separate parent messages.

**Motivating defect still caught:** the injected start contract requires
incremental writes and the stop contract requires delivery before idle, so the
2026-07-05 context-only reports and the two 2026-08-03 agents that died with
nothing written are the exact failures the native carriage prevents.
