# 640 — STANDARDS axis review

Diff: `git diff main...HEAD`, branch `fix/640-md-budget-defects`, commit c5ed9e9.
Files: `python/pyproject.toml`, `python/uv.lock`,
`python/src/dotfiles_setup/listing_budget.py`, `python/verification/suites.toml`.

**No hard violations of a documented standard.** Four judgement calls below.

## What the diff gets right (checked, not assumed)

- `tool-currency-and-native-first.md` rule 3 ("when a native feature supersedes
  custom code, RETIRE the custom code in the same change") — satisfied
  exemplarily: the pin moves and `listed_description()` is deleted in one
  commit, exactly as its own docstring instructed.
- `python/AGENTS.md` § "Verification contracts" — `per_path_tokens` used (not
  bare `tokens`) for the new bindings; all three new/kept tokens match **exactly
  1×** in `listing_budget.py` (`def collect_listing(`, the import line,
  `desc = skill_description(raw)`), so the "how many places match?" question is
  answered. `dotfiles-setup token-audit` → rc=0.
- `probes-need-a-control-arm.md` — verifying against the **installed** package
  rather than the KB source is the correct control. Re-armed independently:
  installed `kb_setup.md_budget.skill_description` returns `'AAA BBB'` with
  `when_to_use` and `'AAA'` without. Both arms discriminate.
- No inline suppressions; no new bash; no `listed_description` references left
  in code or tests (`tests/test_listing_budget.py:59`
  `test_when_to_use_counts_toward_the_cost` now exercises the upstream path).

## Judgement calls

### 1. `skill_description` re-exported in `__all__` — Middle Man

`listing_budget.py:49-56`. The module now publishes an upstream name it does
not own; with `SKILL_DESCRIPTION_MAX` that makes it a partial facade over
`kb_setup.md_budget`. Callers should import from the owner. Minor, and
consistent with the file's existing habit.

### 2. Contract description is becoming a changelog — Divergent Change

`suites.toml:1879`. The appended "Updated 2026-08-07 (#640): …" grows an already
~1,900-char description that now serves two purposes: stating the contract and
logging its revision history. A second such append makes it unreadable. Consider
capping it at the *current* rationale and letting `git log` / a receipt hold the
history.

### 3. Redundant bare `tokens` alongside `per_path_tokens` — Duplicated Code

`suites.toml:1890-1892` still carries `tokens = ["def collect_listing("]`,
already bound path-specifically. Per `python/AGENTS.md`, the bare form is a
weaker UNION check; here it is pure duplication. **Pre-existing, not introduced
by this diff** — flagged because the diff edits the adjacent line.

### 4. Stale SHA left in a spec — `tool-currency-and-native-first.md` rule 5

`docs/specs/eval-harness-design.md:810` reads "Pin is now
`737ff6e3…` (knowledge-base `main`)" — the SHA this diff replaces. Rule 5 says
sync the describing docs in the same change. Weak: that line sits inside a
dated "2026-07-27-d revision" note, so it reads as a historical record rather
than a live claim. A one-line "superseded by 46a3e7d (#640)" would settle it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the `kb-setup` pin whose bump this diff is; the installed `md_budget.skill_description` was probed, not the source.
