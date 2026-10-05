# Cold review — `ff20b590` (coordinator-handoff queued-questions heading)

- **Subject:** `ff20b590a9b3c7f427d399a114671df6034720b5`, by ref only (`git show ff20b590`)
- **Base:** parent `bd50763d2fc020b4322d3923371ec0f9181ce0d2` (= `origin/main`)
- **Author family:** codex (sdlc-team python specialist) → Claude Opus cold lens
- **Reviewer:** cold-reviewer (Opus), 2026-10-04
- **Round:** 1 (open hunting). It cannot end the loop by any outcome and promotes to one bounded round.
- **Memory:** I read the main checkout's `.claude/agent-memory-local/cold-reviewer/` (`review_method.md`,
  `handoff_claim_checker_review.md`). The worktree memory directory was empty.
- **Scope of the diff:** `python/src/dotfiles_setup/coordinator_handoff.py` (+31/−5) and
  `tests/test_coordinator_handoff.py` (+131). The worktree was clean apart from this report, so the working
  tree equals the ref. All line numbers below are from `git show ff20b590:<path>`.
- **Status:** COMPLETE

## Verdict: **SHIP**

The fix does what the commit says. Before it, real handoffs lost their queued questions. After it they are
carried. The new tests catch the regressions that matter. The findings below are all LOW or INFO: shapes
that are possible but do not occur in the corpus. Recommendation 1 below closes F1 and F3 with one change,
in a follow-up or a ticket.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | LOW | The broader H2 regex combined with first-match `.search` lets an earlier H2 that only *starts with* "Queued questions" (`## Queued questions-old (answered)`, `## Queued questions answered last session`) take the section ahead of a later bare live one. Base chose the live one. Nothing warns, because a valid H2 exists. | `python/src/dotfiles_setup/coordinator_handoff.py:135`, `:445`, `:456` | Probe P5/P5b: new returns `'1. Old Q?'` / `'- A1 done'`; base returns `'1. Live Q?'`. Real corpus: 0 of 205 unique handoffs have more than one valid H2, so this has not happened yet. |
| F2 | LOW | `_ANY_QUEUED_HEADING_RE` is `^#+…`, so it also matches lines that are not headings: an issue ref at line start (`#1696 fixed the queued questions parser`) and a `#` shell comment inside a fenced block. The brief then says "queued-questions heading exists but could not be parsed". That is untrue, though it fails loud rather than silent. | `coordinator_handoff.py:138`, `:680` | Probe P1 → WARN quoting `#1696 fixed the queued questions parser`. P1b → WARN quoting `# print queued questions for the successor`. Base gave NONE-FOUND for both. Real corpus: the warning fired 0 times in 205 unique handoffs; P9/P16 show the regex can fire, so 0 is a real negative. |
| F3 | LOW (sibling → ticket) | The warning only fires when no valid H2 exists anywhere (`:456`), not when nothing was extracted. Three shapes stay silent: (a) an empty valid H2 plus a populated wrong-level queued heading → "none found"; (b) a populated stale H2 plus a later `### Queued questions (replaces the section above)` → the stale questions, with no warning; (c) two valid H2s where the first holds `_None._` → `_None._`. | `coordinator_handoff.py:456`; pinned as "valid wins" by `tests/test_coordinator_handoff.py:629` | Probes P13/P14/P15. Shape (b) occurs for real in `docs/handoffs/session-2026-10-03n.md:120`, where it was appended after launch. Base behaves the same for (a)–(c), so this is the existing first-match class and not a regression. |
| F4 | INFO | A valid H2 whose qualifier holds the content (`## Queued questions: restart H3?`, `## Queued questions (see task_plan.md QUEUE)`) with an empty body gives "none found", and the qualifier is dropped. | `coordinator_handoff.py:445-451`, `:683-686` | Probes P7/P7b. Base also gave NONE-FOUND (the heading did not match), so behaviour is unchanged. |
| F5 | INFO | Backticks in a quoted unparsed heading break the inline code span the brief wraps it in (`` `### Queued questions for `kb-land`` ``). Cosmetic only. | `coordinator_handoff.py:681` | Probe P8. |
| F6 | INFO | A ``## Queued questions`` template inside a fenced code block, placed before the real section, takes the section (body `'_template_\n```'`). Base did the same. | `coordinator_handoff.py:445` | Probe P2: new and base are identical. |
| F7 | INFO | Some heading shapes are still silently invisible (NONE-FOUND, no warning): a CommonMark-valid indented heading (`   ## Queued questions`), a setext heading, a `**Queued questions**` pseudo-heading, `Queued-questions`, and a NBSP between the words. All are outside what the commit claims ("wrong level"). | `coordinator_handoff.py:135`, `:138` | Probes P3, P4, P6, P11, P17: new = base = NONE-FOUND. |

### Recommendation (one predicate, closes F1 and F3)

Count the queued headings with `_ANY_QUEUED_HEADING_RE.finditer`. If there is more than one, or the one
present is not the extracted valid H2, quote every one of them in the brief. Today the warning only fires
when no valid H2 exists. With this change, a stale or superseded section can no longer be passed along
silently. Severity is LOW and it does not block shipping. Route it as a ticket, or as a follow-up commit
if the author is still in this unit of work.

## Positive evidence

### Real-corpus replay

I ran every distinct handoff copy through base and new: `docs/handoffs/**` and `.agent/plans/*.md` across
the main checkout and all `.claude/worktrees/*`. That was 2,665 files, 205 unique by sha256.

| Outcome (base → new) | Files |
|---|---|
| None → None (no section) | 164 |
| QUEUED → same QUEUED | 35 |
| **None → QUEUED (recovered)** | **6** (`session-2026-10-03i/j/k/l/m/n`, all `## Queued questions (put to Ray in QUESTIONS format)`) |
| QUEUED → different body | 0 |
| new WARN fired | 0 |

The motivating 04t handoff had already been renamed to the bare heading by hand
(`handoff-2026-10-04t/docs/handoffs/session-2026-10-04t.md:118`). Its verbatim original heading is pinned
by the test at `tests/test_coordinator_handoff.py:323`.

### Mutation harness (tests are teeth, not decoration)

The harness loads a mutated module into `sys.modules`, then runs pytest serially with
`-k "queued or brief"`. **Control:** pristine = 27 passed. M1 (revert the regex) = 8 failed, so the
harness discriminates.

| Mutation | Result |
|---|---|
| M1 revert H2 regex to base | **killed** (8 failed) |
| M2 drop the valid-H2 guard in `_unparsed_queued_heading` | **killed** (2) |
| M3 delete `unparsed_queued_heading=` wiring in `_launch_locked` (`:931`) | **killed** (6), via the public `ch.launch` dry run |
| M4 `[ \t]+` → `\s+` | **killed** (1) |
| M5 drop trailing `\b` from the H2 regex | **killed** (2) |
| M6 make `_ANY` CommonMark-only (`#{1,6}[ \t]+`) | **killed** (1). This is a pinned design choice: `##Queued questions` warns |
| M8 remove the WARNING branch in `successor_brief` | **killed** (6) |
| M10 gate the guard on extracted body instead of heading | **killed** (2) |
| M7 drop the leading `\b` in `_ANY` | survived. Harmless: it only widens the warning to `Unqueued questions` |
| M9 drop `.rstrip()` | survived. Cosmetic: a trailing `\r` on CRLF input |
| M11 drop the trailing `\b` in `_ANY` | survived. Harmless: it only widens the warning |

All three survivors widen the warning or are cosmetic. None of them can silence a real section.

### Targeted suite

`uv run --project python pytest tests/test_coordinator_handoff.py -q` → **220 passed**, rc=0. This was
the only suite run. Full pytest, lint and verify were not run, at the caller's request.

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH:** `_gather` reads the handoff once (`coordinator_handoff.py:801`). Both `queued_questions`
  and `_unparsed_queued_heading` are computed from that same snapshot (`:930-931`), and the brief is built
  from those values. The diff adds no decision that reads different inputs from its action. No temporal
  defect.
- **Q-SCOPE:** F1 and F2 are in scope, caused by this diff's broader regex and its new regex. F3 is
  sibling scope, the existing first-match / multi-section class; recommend a ticket. F4–F7 are existing
  behaviour or cosmetic.
- **Q-CLAIM:** each clause of the strings this diff adds, with the line that enforces it:

  | Clause | Enforcing line | Outcome |
  |---|---|---|
  | "queued-questions heading exists" | `_ANY_QUEUED_HEADING_RE` `:138` | **Over-claims**: it fires on `#`-prefixed lines that are not headings (F2) |
  | "but could not be parsed" | guard `:456` (`_QUEUED_HEADING_RE.search is None`) | holds |
  | quoted heading `` `{…}` `` | `:459` `heading.group().rstrip()` | holds (backtick escaping, F5) |
  | "inspect the handoff in step 1" | brief step 1 (`:722`) tells the successor to review the handoff | holds (an instruction, not a fact) |
  | docstring "non-empty H2 section body, allowing qualifiers after its title" | `:135` `\b[^\n]*$`, `:451` | holds |
  | commit: "Accept a qualifier after a word boundary" | `:135` `\b` | holds (also accepts `questions-old`, F1) |
  | commit: "when only an unparseable … heading exists (wrong level), … warn and quote it instead of claiming none" | `:456-459`, `:678-682` | holds for the "only" case; also fires on lines that are not headings (F2) |

Gates: no `suites.toml`, `hk.pkl` or `hook_selfcheck` token binds any changed string (`git grep` over those
paths at the ref: 0 coordinator_handoff hits). The module is the only parser of the heading in the
codebase (`git grep` over `python/ tests/ scripts/`). The skill docs (`.claude/skills/coordinator-handoff/SKILL.md:41,102`,
`.claude/skills/session-handoff/SKILL.md:39`) say "`## Queued questions` section" and never "bare only",
so they are still accurate.

## Probes run

- `git show ff20b590` and `git show ff20b590:<path>` for every citation.
- Corpus replay (inline `uv run --project python python -`): base regex vs new module over 205 unique handoffs.
- `/tmp/cr-qq/probe.py`: 21 synthetic heading shapes, new vs base. The controls P0/P0b behave as expected.
- `/tmp/cr-qq/mut.py`: 12 mutations. ⚠️ The first run had every mutation green because `pytest.ini`'s
  `addopts` has `-n auto`. xdist workers re-import the unmutated module, so the in-process `sys.modules`
  patch was void. I re-ran with `-n 0`, and then the control arm discriminated.
- All `/tmp/cr-qq/` scratch files and `/tmp/cr-qq-pytest.log` were deleted after the review.

## GitHub repos touched

_None._ Local checkouts only.
