# Agent report: fable-advisor — should this repo adopt /ponytail-debt?

Session: 2026-08-29h.

## Brief

Decision to advise on: should this project (dotfiles) adopt
`/ponytail:ponytail-debt` as a real, used part of its workflow, or leave it
unused for now?

Context: ponytail mode is active in this project (full/ultra intensity) and
its convention is to mark deliberate simplifications with a
`# ponytail: <ceiling>, <upgrade path>` comment. `ponytail-debt` is a skill
that harvests every such comment into a debt ledger.

Constraint/fact already verified this session: a live grep across the whole
tracked tree for `# ponytail:` returns **zero hits** — no such comment
currently exists anywhere in this repo.

Files to read: the ponytail-debt SKILL.md; this project's `.claude/rules/*.md`
(existing debt/deferral discipline via zero-skip-policy.md rule 4 / GitHub
issues).

Options considered: (1) adopt now as a recurring habit, (2) leave unused
until the first comment appears, (3) actively discourage the convention
since GitHub issues already serve that role.

Give your verdict in under 300 words.

## Report (verbatim)

Verdict: **Option 3** — don't adopt the skill, and route ponytail-style deferrals through GitHub issues instead of `# ponytail:` comments in this repo.

The decisive fact is that this project already has a stronger, mandatory version of what `ponytail-debt` provides. `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/zero-skip-policy.md` rule 4 requires every user-approved deferral to become a GitHub issue with full context and repro steps — and the repo's whole operational loop (triage labels, `NEXT:` pointers in memory, session handoffs) reads the issue tracker, not source comments. A comment-scraping ledger (read the skill at `/Users/rmanaloto/.claude/plugins/cache/ponytail/ponytail/4.9.0/skills/ponytail-debt/SKILL.md` — it's a one-shot grep report, optionally persisted to `PONYTAIL-DEBT.md`) is strictly weaker: no owner, no labels, invisible to triage, and a persisted `PONYTAIL-DEBT.md` would be a second ledger that drifts from the issues — exactly the dual-source-of-truth this repo's rules keep killing.

The zero-hit grep confirms the convention has never taken root here despite ponytail mode being active for a while, so option 1 would be running a scanner over an empty corpus before every ship — a check that can only pass (`probes-need-a-control-arm.md`). Option 2 just defers the same duplication question.

Practical form of option 3: when ponytail mode wants a ceiling marked, file the issue per zero-skip rule 4 and, if an in-code breadcrumb helps, write `# ponytail: <ceiling>, see #NNN` — the issue is the ledger, the comment is a pointer. No new habit, no new file, no periodic scan.

One adjacent flag: this is a per-repo convention override of an active plugin mode; a one-line note in `.claude/CLAUDE.md` (the designated home for Claude-specific config) would make it durable.

## GitHub repos touched

- _None._ — advisory verdict, read local plugin/skill files and project rules only.
