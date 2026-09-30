# S29-H round 2 (FINAL) — review fixes on `744c3b92`

Parent specs: `docs/specs/s29h-machine-checked-handoff.md`, `docs/specs/s29h-r1-review-fixes.md`.
Respec round **2 of max 2** — Ray approved this final round 2026-09-29 (AskUserQuestion "Final respec, then ship");
any residue goes to #1457. Source: `docs/research/kb/reports/agents/cold-review-744c3b92-2026-09-29.md` (F1-F6).

## 1. Objective

| id | finding | fix |
|---|---|---|
| F1 | MEDIUM — `merged since` starts at the previous handoff's mtime (= last save), not when its State was generated; merges in between vanish from both handoffs (live: #1455 merged 22:02:07Z, 29b mtime 22:26:03Z) | a generation stamp in the rendered State, read back by the next run |
| F2 | MEDIUM — a PR-only word on an ISSUE number is skipped invisibly; replay: `session-2026-09-02.md:42` `#905 … #887's … OPEN, auto-merge ARMED` passes rc=0 although #905 is MERGED (the 09-29b incident class) | count AND list skipped claims (not failing; spec-chosen) |
| F3 | LOW — unspaced `KB#N` / `owner/repo#N` do not end the previous dotfiles reference's window (`- #1454 MERGED; KB#814 OPEN` → false `#1454 OPEN`) | they end the window |
| F4 | LOW, introduced by r1 — the spaced `owner/repo #N` qualifier swallows `lint/pytest #1454 OPEN` (0 real spaced-slash uses) | drop that alternative |
| F5 | LOW — `--for` excludes by exact path; `29c` vs `29-c` or a bare filename silently fails to exclude | exclude by the handoff's (date, letter) key |
| F6 | LOW — no test for `#A/#B`; M10's named fixture passes for the wrong reason | tests |

## 2. Files

Modify only: `python/src/dotfiles_setup/handoff_check.py`, `python/src/dotfiles_setup/session_state.py`,
`tests/test_handoff_check.py`, `tests/test_session_state.py`; `python/src/dotfiles_setup/main.py` ONLY if an
interface below forces it. Append-only `progress.md`/`findings.md`; report
`docs/research/kb/reports/agents/implement-s29h-r2-2026-09-29.md`. Do NOT touch `task_plan.md`, `.claude/**`,
`.agents/**`, other `docs/**`, classifier files (a gate demanding them ⇒ STOP and report).

## 3. Behaviour

**F1.** `session_state.render` emits, right after the branch line, `- **generated**: <YYYY-MM-DDTHH:MM:SSZ>` —
the UTC time `gather` ran (`Snapshot.generated_at: str`, set in `gather` from an injectable `now`; tests pin it).
`default_since(repo_root, now, *, exclude=...)`: for the chosen previous handoff, read its text and take the LAST
line matching `^- \*\*generated\*\*: (\S+)\s*$` that `parse_since` accepts → `since`, source
`"<path> generated stamp"` (+ the existing ` (excluding …)` suffix when applicable). No parseable stamp → today's
mtime behaviour and source unchanged. An unreadable file → mtime fallback (never raise).

**F2.** `check_with_claims(...) -> tuple[list[Finding], ClaimTally]` where

```python
@dataclass(frozen=True)
class ClaimTally:
    checked: int
    skipped: tuple[Claim, ...]   # claim_holds(...) is None: a PR-only word on an ISSUE
```

`check()` still returns only the findings. `render(findings, *, source, tally: ClaimTally | None = None)`:
OK line = existing text + `; K skipped (PR-only word on an issue)` when K > 0; and in BOTH the OK and the findings
form, append one line per skipped claim:
`handoff-check: info — skipped #887 auto-merge armed (task_plan.md:1234): #887 is an issue, not a PR`.
rc unchanged (skips never fail). Keep `claims_checked` behaviour via `tally.checked`.

**F3.** Any `#<digits>` immediately preceded by a word character (`KB#814`, `repo#12`, `owner/repo#12`) ENDS the
previous reference's window and yields no claim. `/#N` (the second number of `#A/#B`) keeps today's behaviour:
it is NOT a reference and does NOT end the window (so `#1454/#1453 MERGED` claims MERGED for #1454 only).

**F4.** `_FOREIGN_QUALIFIER` keeps only the KB spellings (`KB`, `kb`, `knowledge-base`, optional `PR`/`issue`);
remove the `[\w.-]+/[\w.-]+` alternative. Update its docstring's limitation sentence.

**F5.** `handoff_check.newest_handoff(repo_root, *, exclude=None)`: compare by the `_HANDOFF_RE` key
(date, suffix-order), not the path. `exclude` may be a bare filename or any path; its basename must match
`_HANDOFF_RE`. In `session_state`, a `--for` whose basename does not match → stderr
`session-state: --for must name a session-YYYY-MM-DD[-x].md handoff` and rc=2.

**F6 tests** (each shown red under its mutation, restored by byte copy):
- `#1454/#1453 MERGED` → exactly one claim (1454, MERGED).
- `- #1454 MERGED; KB#814 OPEN` → only `#1454 MERGED` (mutation: drop the F3 terminator → red).
- `- lint/pytest #1454 OPEN` → a `#1454 OPEN` claim (F4; mutation: restore the slash alternative → red).
- F1: a previous handoff carrying `- **generated**: 2026-09-29T22:00:00Z` with a later mtime → since 22:00:00Z,
  source names `generated stamp`; without the line → mtime.
- F2: an issue fact + `#887 auto-merge armed` → no finding, `tally.skipped` has it, render shows the info line.
- F5: `--for session-2026-09-29-c.md` excludes an on-disk `session-2026-09-29c.md`; `--for notes.md` → rc=2.

## 4. Constraints

As the parent specs (py3.14, ruff/ty, zero suppressions, no network in unit tests — patch `pr_facts.run_gh` only,
module-attribute seam, no verdict renames, OK-line prefix unchanged).

## 5. Verification

`mise run gate -- run lint|pytest|verify` (report each rc), then live arms with rc + lines:

1. `mise run handoff-check -- .agent/plans/session-2026-09-29b.md` → rc=0; quote the OK line (skipped count, if any,
   and its info lines).
2. Replay `.agent/plans/session-2026-09-02.md` → an info line names `#887` as skipped.
3. `mise run session-state -- --for .agent/plans/session-2026-09-29c.md` → `generated` line present; since source
   still `…29b.md mtime` (29b has no stamp). Then write a scratch `.agent/plans/session-2026-09-29y.md` containing
   only `- **generated**: 2026-09-29T21:00:00Z`, run `session-state -- --for session-2026-09-29-z.md` → since
   `2026-09-29T21:00:00Z` from `…29y.md generated stamp` and the merged list includes #1455; delete the scratch file.
4. `mise run session-state -- --for notes.md` → rc=2.

## 6. Commit

`caller`.

## 7. PREMISES

| # | kind | claim | cite |
|---|---|---|---|
| P1 | L | window/qualifier/lookbehind code sites | cold-review-744c3b92 F3/F4: `handoff_check.py:56`, `:59-62`, `:422-430` |
| P2 | I | skip path: `claim_holds` → None, loop `continue`s before counting | `handoff_check.py:447-450`, `:583-585`, `:647-648` |
| P3 | I | `default_since` uses the previous handoff's mtime; `render` has no generation stamp | `session_state.py:340`, `:483-521` |
| P4 | L | handoff name regex allows an optional hyphen before the letter | `handoff_check.py:34-36` (`_HANDOFF_RE`) |
| P5 | L | live: #1455 merged 22:02:07Z; 29b mtime 22:26:03Z | cold-review-744c3b92 F1 |
| P6 | L | corpus: 0 spaced `a/b #N` uses; 58 unspaced `\w#N` | cold-review-744c3b92 Q1 replay |
