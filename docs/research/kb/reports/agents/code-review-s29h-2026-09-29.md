# /code-review medium on feat/s29h-machine-checked-handoff (4e337900) — 2026-09-29

Verbatim.

I found 5 issues in `feat/s29h-machine-checked-handoff`. The ReportFindings tool isn't available in this session (ToolSearch found nothing by that name), so the findings are only in this reply. The review was read-only; I didn't run any gates.

1. **`python/src/dotfiles_setup/session_state.py:461` (and `:448`) — medium.** The generated snapshot can fail its own check.
   - The branch-PR line (`- **open PR**: #N — {title}`) and the recent-commit lines (`` `sha` {subject} ``) print the title and subject raw.
   - The new open-PR rows put titles in a code span precisely so their words aren't read as claims. These two older lines don't, but `handoff-check` now parses them.
   - Scenario: the branch PR is titled "ci: keep main green" and its checks are pending. The pasted State section yields a `#N green` claim, and `handoff-check` reports `pr_claim_mismatch` at once.
   - Same for a commit subject like "fix #1443 auto-merge race" when #1443 has already merged.
   - This breaks the docstring's promise that "a State section pasted from this output checks itself".

2. **`python/src/dotfiles_setup/pr_facts.py:99` — medium.** `count_checks` counts every `statusCheckRollup` entry and never removes duplicates.
   - When a workflow is re-run (`mise run gha-rerun`), the rollup can hold both the old FAILURE run and the new SUCCESS run for the same check name. `gh pr checks` removes these duplicates itself; this code doesn't.
   - Result: `failing >= 1` sticks after a green re-run. `#N green` and `#N auto-merge` claims then report `pr_claim_mismatch`, `#N RED` wrongly passes, and `session_state._check_word` prints RED for a PR that is actually green.
   - I didn't run this against a live re-run PR; it comes from how gh handles the rollup.

3. **`python/src/dotfiles_setup/handoff_check.py:418` — low/medium.** For an issue number, `claim_holds` returns None (skipped and not counted) for MERGED, landed, auto-merge armed, auto-merge, RED and green.
   - A handoff that says "#1450 MERGED" when #1450 is an issue, or a typo'd PR number that lands on an issue, passes silently. Only the "N PR claim(s) match" count drops.
   - These words are impossible for an issue, so they should report a mismatch, not be skipped.

4. **`python/src/dotfiles_setup/handoff_check.py:343-352` — low.** A reference's window picks up every state word to the end of the line, with no handling of transitions or negation.
   - "#1447 OPEN → MERGED", "#1449 MERGED (was RED)" and "#1454 auto-merge disarmed" each produce a claim that is false by construction. The last one hits the bare `\bauto-merge\b` pattern, since the next character is a space.
   - This is exactly how handoffs describe history, so these lines give permanent `pr_claim_mismatch` noise that trains resume sessions to ignore the check.

5. **`python/src/dotfiles_setup/session_state.py:37` / `:241` — low.** `gh pr list --limit 100` truncates silently, and nothing records that it did.
   - With more than 100 open PRs, or more than 100 merged since a stale `--since`, the output looks complete and never says it is partial.
   - That undercuts the module's own rule that an unanswered lookup is never shown as a clean answer.

`file:line` summary:
- `python/src/dotfiles_setup/session_state.py:461` — branch-PR title and commit subjects printed raw, so the pasted snapshot fails its own `handoff-check`
- `python/src/dotfiles_setup/pr_facts.py:99` — `count_checks` doesn't remove re-run duplicates, so a stale FAILURE keeps a green PR RED
- `python/src/dotfiles_setup/handoff_check.py:418` — PR-only words on an issue number are skipped instead of reported
- `python/src/dotfiles_setup/handoff_check.py:343` — "OPEN → MERGED", "was RED" and "auto-merge disarmed" produce false mismatches
- `python/src/dotfiles_setup/session_state.py:37` — the 100-row limit truncates open/merged lists without saying so
