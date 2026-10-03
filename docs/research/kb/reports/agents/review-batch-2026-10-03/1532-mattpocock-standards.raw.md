# PR #1532 — STANDARDS axis (63c0b6dd..e6bc086a, 3 files +7/-3)

## Measurements (re-derived at e6bc086a, not inherited)
- `AGENTS.md`: **11,978 bytes / 11,892 chars** (`wc -m`, UTF-8), up from 11,937 bytes. That leaves **108 chars** under the 12,000 AGM-003 ceiling. Line count stays 194.
- The `docs/research/kb/raw/**` exemption is **TRUE**. Both `scripts/check-claude-md-stub.sh:55` and `scripts/check-claude-agents-md-pairs.sh:39,43` filter with `grep -v -E '^(\.claude|docs/research/kb/raw)/'`. Control arms:
  - a synthetic `docs/research/kb/raw/x/links/CLAUDE.md` is dropped;
  - `docs/research/kb/rawfoo/CLAUDE.md` and `.devcontainer/CLAUDE.md` are kept;
  - the real tree has 13 CLAUDE/AGENTS files, 0 under kb/raw, and the 2 `.devcontainer/` files survive the filter.
  - The exemption came from PR #1486 (`3a3ca862`, found by `git log -S`).
- Spec status line: `3a861923` = #1475 and is an ancestor of e6bc086a. #1471 is CLOSED; #1473 and #1474 are OPEN. `SKILL.md:56-69` contains the health control, the planner-or-README must-hit and the per-repo existence check. Everything checks out.

## (a) Hard violations
None found. Every new claim is true at e6bc086a, AGENTS.md stays under 12,000, and no verbatim tree was edited (rule 8 holds).

## (b) Judgement calls / smells
1. **Ceiling headroom (`.claude/CLAUDE.md:4`).** "within ~500 characters of the 12,000" is still literally true, but the headroom is now 108 chars. Another +2-line edit like this one would breach AGM-003. Under verify-before-advancing ("carry a number with its CONDITION"), the line should state the measured figure and when it was measured.
2. **Inconsistent citation, a Duplicated Code / Divergent Change smell.** `AGENTS.md:61` cites **#1486** (the PR). For the same fact, `.claude/CLAUDE.md:8` and the `hk.pkl:779-781` comment cite **#1472**, an issue that is still OPEN (about betterleaks F5). One exemption is now documented in 4+ places (AGENTS.md, .claude/CLAUDE.md, hk.pkl ×2, both scripts) under two different references. That is Shotgun Surgery waiting to happen. Pick one reference, ideally the PR, since it is what shipped.
3. **Imprecise scope, `AGENTS.md:61`.** The sentence says kb/raw is exempt "from the stub check", but the scripts exempt it from the **pairs** check too. This is inherited from the `.claude/` phrasing, so it adds no new error, just the same under-statement.
4. **Mysterious Name, `research-doc-sources.md:9`.** "in-lane" is not defined anywhere in the rule. The likely intent is "a research lane outside the workflow". The fix this PR makes for a vagueness finding (V15-V17) brings in a new vague term.
5. **Speculative status prose, spec:3-5.** Repeating as-built details in the spec ("health control, planner-or-README must-hit…") duplicates SKILL.md and will drift. The pointer alone is enough.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR/issue state for #1472, #1486, #1471, #1473, #1474
