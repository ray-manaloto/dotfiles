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
  `docs/research/kb/`, `.claude/skills/clear-prep/SKILL.md`.
