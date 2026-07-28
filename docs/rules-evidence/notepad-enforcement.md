# Evidence — `notepad-enforcement`

Archaeology behind `.claude/rules/notepad-enforcement.md`. Extracted so the
eager copy states the mechanism and the four operative rules, and this file
carries how the rule spent months naming a mechanism that did not exist.

## The rule named tools that are absent from every session

Until 2026-07-15 the rule named
`mcp__plugin_oh-my-claudecode_t__notepad_write_working` and
`..._write_priority` as *the* way to record findings.

Those tools ship with the `oh-my-claudecode` plugin, which is **disabled**. So
they are absent from every session — and a `/doctor` scan measured **zero
invocations across 941 transcripts**.

**The rule was unfollowable as written.** What kept the notepad current was
sessions writing `.agent/notepad.md` by hand, i.e. doing the right thing by a
mechanism the rule never mentioned. Naming the real mechanism — an ordinary file,
written with Write/Edit — is the whole fix.

If OMC is ever re-enabled, its notepad tools write this same file, so the rule
does not change.

The generalisable shape: **a rule that names a mechanism nobody can invoke is
indistinguishable from no rule at all**, and it will not announce itself — the
outcome looked fine because humans were compensating. The 941-transcript count is
what made it visible.

## Why the rule exists at all (2026-04-05)

The python-pro agent and the debugger team performed extensive analysis and did
**not** write to the notepad. When context was lost, every finding had to be
re-derived.

That is the same failure `agent-report-persistence.md` covers at full fidelity;
this rule covers the running condensed layer. Both, every time.

## Verifying compliance

After an agent completes work, check `.agent/notepad.md`. If it is empty or stale
relative to the work performed, the agent did not comply — and the finding is
gone unless it is still in context.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `.agent/notepad.md`.

_Named in the extracted text but **not** resolved during this extraction: the
`oh-my-claudecode` plugin. Its disabled state was verified in an earlier session
(2026-07-28-e), not re-probed here._
