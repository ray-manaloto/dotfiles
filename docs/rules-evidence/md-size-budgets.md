# Markdown Size Budgets — Evidence

Evidence extracted from `.claude/rules/md-size-budgets.md`; the scoped rule
keeps the machine-bound budget table and the Windsurf-misattribution lesson.

## 2026-09-09 — audit refactor

**Findings applied:** `rule-md-size-budgets-1` through `-5`.

**Native anchors re-read:** `memory.md:401-405` and `:456` state that
`CLAUDE.md` loads through 4 MiB and a larger file is skipped, while the 200-line
and 25 KiB truncation belongs to `MEMORY.md`; `memory.md:69`, `:145`, `:421`,
and `:437` document `/context` and its Memory files row; `memory.md:242-244`
documents the 1,000-expanded-pattern/4 MiB shared `paths:` budget and literal,
non-matching fallback; `memory.md:462` documents post-compact root re-injection
and file-triggered reload for nested instructions and scoped rules.

`settings-reference.md:2723-2753` documents
`skillListingBudgetFraction` (default 0.01) and
`skillListingMaxDescChars` (default 1,536); `settings-reference.md:3885` and
`skills.md:1050-1058` document `skillOverrides`, least-used-first description
drops, `/doctor`, and the post-budget Skills row. `skills.md:337-338` assigns
the 1,536 default to combined `description` + `when_to_use`, not description
alone. `/skill-doctor` is anchored to the saved verbatim 2.1.261 changelog at
`.agent/kb/raw/claude-code-changelog-2.1.258-2.1.266.md:67-71` because the KB
corpus predates that release. ⚠️ **That path is gitignored and machine-local**,
so a fresh clone cannot open it; treat the `/skill-doctor` claim as unverifiable
off this machine until the excerpt is promoted to a tracked path.

**Probe outputs:** `grep -R "regardless of length"` over the Claude Code doc
tree returned **0**; the same command shape for `reduce adherence` returned
**2** files. The three skill-listing project keys are absent from
`.claude/settings.json`, while the control key `fallbackModel` is present.
This rule measures 5 brace-free `paths:` globs, far below the expansion budget.

**Gate ownership probe:** `hk.pkl:617` invokes `kb-setup md-budget`.
Knowledge-base `kb_setup/md_budget.py:95` defines
`EAGER_BYTE_BACKSTOP = 24_000`; its table construction at `:182` owns the
remaining class constants. No number moved in this repository.

**Motivating defect still caught:** the 12,000-character fact once travelled
without its Windsurf provenance and was enforced against the wrong files. The
refactored rule retains the original source URL, vendor boundary, and unchanged
machine-consistent table while replacing stale Claude Code claims.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule
  and evidence note.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base)
  — budget implementation and pinned documentation corpus.
