# S29-H round 1 — review fixes on `4e337900`

Parent spec: `docs/specs/s29h-machine-checked-handoff.md`. Respec round **1 of max 2** (codex-sdlc-team doctrine).
Findings refuted/confirmed by the architect against the cited code before this spec:

- cold review `docs/research/kb/reports/agents/cold-review-4e337900-2026-09-29.md` (F1-F10)
- `/code-review` `docs/research/kb/reports/agents/code-review-s29h-2026-09-29.md` (#1-#5)
- mattpocock `standards-review-s29h-2026-09-29.md`, `spec-review-s29h-2026-09-29.md`

## 1. Objective

Close the review findings that make the new check judge the WRONG object or lose data silently, so a green
`handoff-check` / a pasted `session-state` block means what it says:

| id | finding (source) | fix here |
|---|---|---|
| R1 | cross-repo refs written with a space (`KB #611`, `knowledge-base PR #611`, `owner/repo #N`) are judged against dotfiles #N — 39 of 77 real cross-repo refs (cold F1) | not a reference |
| R2 | `merged since` window collapses to "now" once the new handoff file exists (cold F2, spec-review #5) | `--for <handoff path>` excludes the handoff being written |
| R3 | branch-PR title + commit subjects printed raw → a pasted snapshot can fail its own check (code-review #1, spec-review #6) | code spans |
| R4 | `count_checks` keeps re-run duplicates, so a stale FAILURE keeps a green PR RED (code-review #2) | gh's `eliminateDuplicates` rule |
| R5 | `gh pr list --limit 100` truncates silently (standards #1, code-review #5) | say so |
| R6 | "was RED", "never MERGED", "auto-merge disarmed" read as present claims (code-review #4, cold F7 part) | mask negated/past forms |
| R7 | M1 (CLI `--since` forwarding), M9 (`check()` forwards `facts=`), M10 (the `/` in the reference lookbehind) deletable with tests green (cold F5) | tests that fail on each deletion |
| R8 | docstrings overstate: "one total 300 s deadline" (cold F6); `classify_check` has no written reason for not using gh's `bucket` (standards #2) | wording only |

Out of scope (tickets, not this diff): lowercase `merged/closed/open` and `#A/#B` lists (cold F3, spec-chosen);
PR-only words on an ISSUE (cold F4 / code-review #3 — REJECTED here: `task_plan.md` active section carries
`#1388 … RED` where #1388 is an issue, so a mismatch would be a false positive on real text); CodeRabbit
PENDING on merged PRs (F7); search-index lag (F8); `verify` skill row (F9, architect edits docs); bot-PR volatility
between step 5.2 and 5.3 (F10).

## 2. Files

Modify only: `python/src/dotfiles_setup/handoff_check.py`, `python/src/dotfiles_setup/session_state.py`,
`python/src/dotfiles_setup/pr_facts.py`, `python/src/dotfiles_setup/main.py` (session-state parser/dispatch: `--for`),
`tests/test_handoff_check.py`, `tests/test_session_state.py`, `tests/test_pr_facts.py`, `mise.toml` (the
`session-state` description string only). Append-only: `progress.md`, `findings.md`. Report file below.
Do NOT touch: `task_plan.md`, `.plan-attestation`, `.claude/**`, `.agents/**`, `docs/**` (except the report),
`classifier_tables.py` / `tests/test_classifier_tables.py` (if a gate demands an edit there, STOP and report).

## 3. Interfaces and exact behaviour

**R1 — `handoff_check.extract_claims`.** After a reference matches `_CLAIM_REFERENCE`, it is NOT a reference when
the text before it on the same line matches (end-anchored, case-sensitive where written):

```python
_FOREIGN_QUALIFIER = re.compile(
    r"(?:\b(?:KB|kb|knowledge-base)|\b[\w.-]+/[\w.-]+)[ \t]+(?:(?:PR|pr|issue|Issue)[ \t]+)?$"
)
```

A foreign reference still ENDS the previous reference's window (so its words are not attributed to the prior
dotfiles number) but produces no claim. Docstring names the limitation: only KB spellings and `owner/repo`
qualifiers are recognised; any other repo name followed by a space is still read as dotfiles.

**R2 — `session_state`.** `default_since(repo_root, now, *, exclude: Path | None = None)`: the newest handoff by
the same ordering as `handoff_check.newest_handoff`, skipping `exclude` (resolved-path equality). Implement by
adding an `exclude` keyword to `handoff_check.newest_handoff` (default None; existing callers unchanged).
`since_source` reads `"<path> mtime (excluding <for-path>)"` when excluded. CLI: `session-state [--no-pr]
[--since <ISO>] [--for <handoff path>]`; `--since` wins over `--for`; `--for` with a nonexistent path is fine
(the file being written may not exist yet). `gather(..., for_handoff: Path | None = None)`.

**R3 — `session_state.render`.** Branch-PR line: `- **open PR**: #N — `<title>` (checks: …)`; each commit line:
`` - `sha` `<subject>` ``. Use the SAME escaping helper as the open-row titles (backtick → `'`). Existing tests
that pin these strings are updated, not deleted.

**R4 — `pr_facts.count_checks`.** Before bucketing, drop duplicates exactly as gh does
(`cli/cli` `pkg/cmd/pr/checks/aggregate.go` `eliminateDuplicates`, lines 96-120 at `e9542451`): sort entries by
`startedAt` descending (missing/non-string sorts OLDEST), then keep the first entry per key, where key = `context`
when it is a non-empty string, else `(name, workflowName)`. (gh also keys on the workflow run's event; `gh pr
view/list --json statusCheckRollup` does not expose it — say so in the docstring.) Keep the fail-closed `None`
for a non-list / non-dict rollup.

**R5 — `session_state._summaries`.** When `len(rows) == int(_PR_LIST_LIMIT)`, the list is POSSIBLY TRUNCATED:
carry `truncated: bool` on the result (e.g. return `tuple[tuple[PrSummary, ...], bool] | None`, or a small
dataclass) and render the heading as `- **open PRs** (100, TRUNCATED at --limit 100 — list may be incomplete):`
(same for merged). Below the limit: unchanged.

**R6 — `handoff_check._window_words`.** Before the claim patterns run, blank (mask, no claim) these spans in the
window:

```python
_NEGATED_CLAIM = re.compile(
    r"(?i)\b(?:was|were|not|never|no longer)\s+(?:auto-merge(?:\s+armed)?|OPEN|MERGED|CLOSED|RED|green|landed)\b"
    r"|(?i:\bauto-merge\s+(?:disarmed|disabled|off|cancelled|canceled)\b)"
)
```

(Write it as valid Python — a global `(?i)` must lead the pattern; case-insensitive masking is intended: a masked
`was red` is simply not a claim.) Positive claims elsewhere in the same window still count.

**R7 — tests (each must FAIL when its production line is deleted; prove it with the mutation, then restore by
byte copy):**
- M1: a test that calls the real `main.py` dispatch (the argparse path, not a hand-built argv) with
  `--since 2026-09-29T20:00:00Z` and asserts the merged query carries `merged:>=2026-09-29T20:00:00Z`.
- M9: a `check()` test with a claim and an injected `facts=` stub asserting the stub was called and its answer
  produced a finding (deadline NOT zeroed).
- M10: a test that `owner/repo#12 MERGED` yields no claim (delete `/` from the lookbehind → red).
- Plus one test per R1-R6 behaviour above, including R4 with a stale FAILURE + newer SUCCESS for the same
  `(name, workflowName)` → 0 failing, and the reverse order → 1 failing.

**R8 — wording.** `check_with_claims` / `CLAIMS_DEADLINE_S` docstring: "no NEW lookup starts after 300 s; a lookup
in flight can add up to 2 × `GH_TIMEOUT` (worst case ~540 s)". `classify_check` docstring: why not gh's `bucket` —
`gh pr view/list --json` expose only `statusCheckRollup` (no `bucket`), and this mapping deliberately differs from
gh's: CANCELLED and STARTUP_FAILURE count as failing (gh buckets them `cancel`/`pending`) because a handoff's RED
means "will not merge as-is". `mise.toml` session-state description adds `[-- --for <handoff>]`.

## 4. Constraints

Same as the parent spec § 4 (py3.14, ruff/ty, zero suppressions, no network in unit tests — patch
`pr_facts.run_gh` only, call-time module-attribute seam, no bash). `handoff_check.newest_handoff` keeps its
existing behaviour when `exclude` is None. Do not change any verdict name or the OK-line prefix.

## 5. Verification

```bash
mise run gate -- run lint
mise run gate -- run pytest
mise run gate -- run verify
```

Live arms (quote rc + lines):

1. `mise run handoff-check -- .agent/plans/session-2026-09-29b.md` → rc=0, "N PR claim(s) match GitHub".
2. Scratch copy + line `- knowledge-base PR #611 MERGED and KB #509 OPEN` → no finding mentions #611 or #509
   (control: the same line without the qualifiers DOES produce claims for #611/#509).
3. Scratch copy + `- #1454 was RED; auto-merge disarmed on #1452` → no finding; control: `- #1454 RED` → mismatch.
4. `mise run session-state -- --for .agent/plans/session-2026-09-29c.md` → merged-since source names
   `session-2026-09-29b.md`; then `touch` a scratch-named file `.agent/plans/session-2026-09-29z.md`, re-run with
   `--for` that path → still `…29b.md`; without `--for` → `…29z.md`; delete the scratch file afterwards.
5. Paste arm: pipe the live `session-state` output into a scratch handoff and run handoff-check on it → rc=0.

## 6. Commit

`caller`.

## 7. PREMISES

| # | kind | claim | cite (read this session) |
|---|---|---|---|
| P1 | L | reference regex lookbehind `(?<![\w#/])` | `handoff_check.py:56` (via cold F1, F5/M10) |
| P2 | I | `default_since` = newest handoff mtime; `newest_handoff` ordering by date+suffix | `session_state.py:315-320`; `handoff_check.py:128-144` (pre-change numbering) |
| P3 | L | branch-PR line and commit lines render raw title/subject | `session_state.py:448`, `:461` |
| P4 | I | `count_checks` buckets every rollup entry, no de-dup | `pr_facts.py:99-111` |
| P5 | P | gh de-dups by `context`, else `name/workflow/event`, newest `startedAt` first | `cli/cli@e9542451:pkg/cmd/pr/checks/aggregate.go:96-120` (fetched this session) |
| P6 | L | rollup entry keys: CheckRun `{__typename, completedAt, conclusion, detailsUrl, name, startedAt, status, workflowName}`; StatusContext `{__typename, context, startedAt, state, targetUrl}` — no event | `gh pr view 1449 --json statusCheckRollup`, this session |
| P7 | L | `_PR_LIST_LIMIT = "100"` used for both lists | `session_state.py:37`, `:241` |
| P8 | L | gh buckets CANCELLED→cancel, default (incl. STARTUP_FAILURE, STALE)→pending | `aggregate.go:72-88` |
| P9 | L | `#1388` is an issue and the active plan section carries `#1388 … RED` | `gh api …/issues/1388` + prototype, this session |
| A1 | A | no observed rollup duplicates in 8 sampled PRs (no PR-head re-run found to arm R4 live) — R4 is armed by unit test only | this session's sample |
