# W1 — three live defects (A5 / A6 / A7)

All work is in this scratchpad; the repo was never written to.
Gates run: `ruff check` rc=0, `ruff format --check` rc=0, `pytest` 60 passed rc=0
(sandbox at `sandbox/`, a copy of `python/` + `tests/`).

---

## A6 — `hook_guard.py:30` stale matcher — CONFIRMED, and it is NOT one file

**Ground truth**, `.claude/settings.json:37`:

    "matcher": "Bash|AskUserQuestion|Edit|Write|NotebookEdit",

The team-lead's report is correct. Three LIVE occurrences of the stale claim:

| # | file:line | text | disposition |
|---|---|---|---|
| 1 | `python/src/dotfiles_setup/hook_guard.py:30` | ``matcher is ``Bash|AskUserQuestion``; dispatch is on ``tool_name``.`` | FIX (E3) |
| 2 | `.claude/rules/clarify-before-acting.md:70` | ``wires `PreToolUse` matcher **`Bash|AskUserQuestion`**`` | FIX (E4) |
| 3 | `python/verification/suites.toml:1112` | requires the token ``` `Bash|AskUserQuestion` ``` in file #2 | FIX (E5) — see below |

**#3 is the trap: fixing #2 alone breaks `mise run verify`.** The
`workflow.ask-quality-gate` suite pins the rule file's wording via
`require_tokens`, and the required token is backtick-DELIMITED. Control arm:

    token "`Bash|AskUserQuestion`" in OLD rule text : True
    token "`Bash|AskUserQuestion`" in NEW rule text : False   <-- contract fails
    token "`Bash|AskUserQuestion|Edit|Write|NotebookEdit`" in NEW : True

So E3+E4+E5 are one atomic change. (This is `feedback_forbid_tokens_substring_fragile`
biting in the require direction.)

### Deliberately NOT changed

- `tests/test_hook_selfcheck.py:61` — `"Bash|AskUserQuestion"` inside `_full_settings()`
  is a **synthetic fixture**, not a claim about reality. `hook_selfcheck._SETTINGS_WIRING:79`
  requires the substrings `("Bash", "AskUserQuestion")` and checks them with
  `matcher in m` (`hook_selfcheck.py:163`), so it passes against the real 5-tool
  matcher. Leaving it.
  ⚠️ **Adjacent gap, out of scope, worth a ticket:** `_SETTINGS_WIRING` does NOT
  require `Edit`/`Write`/`NotebookEdit`. If someone narrowed the live matcher back
  to `Bash|AskUserQuestion`, `hook selfcheck` would stay green and the #400 write
  guard would silently die. (`suites.toml:1808` pins the settings.json literal, so
  the repo is not defenceless — but the ship/land gate is.)
- `docs/research/kb/reports/**` (5 files) — persisted verbatim agent reports;
  `.claude/rules/agent-artifact-conventions.md` forbids normalising them. Two of
  them (`601-reflect-adversarial-critique.md:88`, `code-review-525-spec.md:41`)
  already record the CORRECT matcher.

---

## A7 — `project_transcripts` non-recursive glob — CONFIRMED, and worse than reported

`python/src/dotfiles_setup/command_audit.py:233` (old):

    files = [p for p in project_dir.glob("*.jsonl") if p.is_file()]

### The lead's control arm reproduced — and extended

    maxdepth 1 : 214      recursive : 2174   (2,176 on a later pass; the dir is live)

**The lead's diagnosis is incomplete in a way that matters.** Teammate transcripts do
NOT all live at `<session-id>/subagents/`. Depth histogram of `rglob("*.jsonl")`
(path-part count relative to the project dir), measured 2026-08-06:

| depth | count | shape |
|---|---|---|
| 1 | 214 | `<session-id>.jsonl` (session roots) |
| 3 | 166 | `<session-id>/subagents/agent-*.jsonl` |
| 5 | **1,796** | `<session-id>/subagents/workflows/wf_*/agent-*.jsonl` |

A fix of the shape `glob("*/subagents/*.jsonl")` — the obvious reading of the brief —
would still miss **92%** of the nested files. `rglob` is required.

### Q1: does the fix silently change what `limit` means? YES — and it is handled

`DEFAULT_SESSION_LIMIT = 50` (`command_audit.py:79`) is commented
"Most-recent **sessions** to scan", and `render_report:627` prints
`Scanned **N** recent session(s)`. Truncating a recursive glob by FILE would keep
the label and destroy the meaning: one team-heavy session contributes hundreds of
files, so a 50-file cap collapses the window from 50 sessions to two or three while
still printing "50".

**Chosen:** apply `limit` to the **session roots**, then pull in each selected
session's nested transcripts. `limit` keeps its documented meaning exactly.

Anchoring on roots loses nothing — measured: of the 82 directories under the project
dir, exactly **one** has no sibling root `.jsonl`, and it is `memory/` (the
auto-memory store, no transcripts). 133 roots have no directory (solo sessions).

### Q2: does anything downstream assume one file == one session? YES

`command_audit_main:739`: `sessions=len(transcripts)`. That is the only such
assumption (traced: `audit()` → `AuditResult.sessions` → `render_report:627`; no
other consumer, no top-N cap anywhere). Under a recursive glob it would inflate the
figure by the team size — reporting sessions that do not exist.

**Fixed** by counting transcripts whose parent IS the project dir (i.e. roots).
Empirical justification: a subagent transcript carries its **parent's** `sessionId`,
not its own — **0 mismatches across 12,006 lines** in 400 subagent files. So the
file count was never a session count once nesting is included.

### Q3: same JSONL schema? VERIFIED EMPIRICALLY, yes

Probed `a7eeccdb-…/subagents/agent-a15488cb85391935d.jsonl`, then 400 subagent files:

    types: {'user': 14, 'attachment': 2, 'assistant': 23}
    keys : parentUuid, isSidechain, agentId, type, uuid, timestamp, userType,
           entrypoint, cwd, sessionId, version, gitBranch
    tool_use names: {'Bash': 13}   tool_result blocks: 13

Across 400 files: **2,481** `type:"tool_use"` / `name:"Bash"` blocks, and
`toolUseResult` **dict-with-stdout = 2,431**, **bare-str = 67** — exactly the two
shapes `_executed_ids` (`command_audit.py:278`) documents. `_bash_blocks` and
`_executed_ids` need no change. New keys (`agentId`, `isSidechain`) are additive and
ignored by the defensive parser.

### Q4 (not asked): does this blow the SessionEnd hook's 120s timeout? NO

`.claude/settings.json:85` sets `timeout: 120`.

| scenario | files | bytes | `iter_bash_commands` |
|---|---|---|---|
| OLD, roots only (50) | 50 | — | 4,659 cmds / **0.6s** |
| NEW, limit=50 sessions | 281 | 169 MB | 7,309 cmds / **1.2s** |
| worst case, every file | 2,176 | 588 MB | 22,590 cmds / **4.5s** |

The real-world signal gain at the default limit is **+57% commands** (4,659 → 7,309).
The 2,176-file figure is not the steady-state cost: the 1,796 workflow transcripts
are concentrated in sessions older than the 50 most recent.

### Control arm for the test — recorded, both directions

Four new tests, run in `sandbox/` (repo `tests/` style: `sys.path.insert` of
`python/src`, `tmp_path`, no suppressions).

**Arm 1 — against the OLD non-recursive glob (must fail):**

    FAILED test_project_transcripts_includes_subagent_transcripts
    FAILED test_project_transcripts_includes_workflow_subagent_transcripts
    FAILED test_project_transcripts_limit_counts_sessions_not_files
    FAILED test_main_counts_sessions_not_transcript_files
    4 failed, 1 passed, 55 deselected in 2.36s      rc=1

**Arm 2 — against the REALISTIC wrong fix** (`rglob` + truncate-by-file +
`sessions=len(transcripts)`, i.e. what a hurried session would actually write):

    FAILED test_project_transcripts_limit_counts_sessions_not_files
    FAILED test_main_counts_sessions_not_transcript_files
    2 failed, 58 passed in 1.77s                    rc=1

**Arm 3 — against the fix:**

    60 passed in 0.25s                              rc=0
    ruff check          All checks passed!          rc=0
    ruff format --check 2 files already formatted   rc=0

Arm 2 is the one that matters: it proves the two limit/session-count tests are not
decoration. Arm 1 alone would have been satisfied by the wrong fix on 2 of 4 tests.

---

## A5 — brief coverage in the persistence rule

`.claude/rules/agent-report-persistence.md:56-59` — rule 5 audits **reports** only.
One-clause amendment, as briefed (no new step):

    ...requires each findings-bearing one to map
    **both its brief and its report** to an on-disk artifact (or an explicit
    N/A note in the handoff) before the resume prompt is printed.

**The enforcing step DID need the matching line.** `.claude/skills/clear-prep/SKILL.md`
§3c is where the audit actually happens ("enumerate every agent launched this session;
each findings-bearing one must map to an artifact file"), plus its checklist line. Both
say *report*. Without them the rule is a claim with no enforcing call site — the exact
failure class the post-mortem convicts three times. Two hunks, E2a/E2b.

No `suites.toml` contract pins either file (checked: zero hits for
`agent-report-persistence` / `clear-prep` in `python/verification/suites.toml`), so
A5 is self-contained.

### Two pre-existing inconsistencies found in passing — NOT fixed, flagged

1. `SKILL.md` §3c says persist under `docs/research/runs/<topic>/agents/`; its own
   checklist and `agent-report-persistence.md` rule 1 say `docs/research/kb/reports/agents/`.
   The rule marks `runs/` as the OLD path ("ONE path... the old
   `docs/research/runs/<topic>/agents/` does not [survive a fresh clone]"). §3c is stale.
2. `.claude/rules/agent-artifact-conventions.md` lists BOTH `docs/research/runs/` and
   `docs/research/kb/reports/` as tracked.

Out of scope for a one-clause amendment; worth a follow-up ticket.

---

## Deliverables

- `APPLY.md` — 7 edits across 6 files, every anchor verified `count == 1`
  (10/10 unique, 0 non-unique).
- `artifacts/` — complete final content: `command_audit.py`, `test_command_audit.py`,
  `hook_guard.py`, `clarify-before-acting.md`, `suites.toml`,
  `agent-report-persistence.md`, `clear-prep-SKILL.md`.
- `sandbox/`, `sandbox-naive/` — the three control arms, re-runnable.

## GitHub repos touched

_None._ (All evidence is this working copy and the local `~/.claude` transcript tree.)

---

## Addendum — harness cleanup (2026-08-06, after mid-flight correction)

Three points came in; two rest on things that did not happen, so recording the
measurement rather than the assumption:

1. **`report.md` already existed** — 9,925 B, mtime 15:02, written before the
   correction arrived. No work was ever held only in memory.
2. **mypy was never run.** `.mypy_cache` and `.DS_Store` DO exist under
   `sandbox/`, but their provenance is `cp -R`, not an invocation:
   `python/.mypy_cache` is present **in the repo**, dated **Mar 23 2026**; the
   sandbox copies are dated Aug 6 14:56, which is the `cp -R` timestamp. The
   repo's own tree is where they came from. (`ty`, not mypy, is this repo's
   type checker — agreed, and it was never in play either; `ruff check` was the
   lint signal used throughout.)
3. **The underlying complaint is nonetheless right**: copying `python/` wholesale
   dragged in `.venv` and made the sandbox 87 MB. Fixed.

**Rebuilt minimal, per the instruction**: `python/src/dotfiles_setup/` (needed —
`command_audit` imports `hook_guard` for the rule table) plus the one test file,
run against the repo's own env via `uv run --project <repo>/python`.

| | before | after |
|---|---|---|
| sandbox size | 87 MB | **892 KB** |
| `.venv` / `.mypy_cache` / `.DS_Store` / `__pycache__` | 10 + venv trees | **0** |

`artifacts/` was clean the whole time — it only ever held the 9 deliverable files.

### All three arms re-run on the rebuilt harness — same results

    ARM 1  old non-recursive glob   4 failed, 56 passed   rc=1
    ARM 2  naive rglob fix          2 failed, 58 passed   rc=1
    ARM 3  the fix                 60 passed              rc=0

### Re-running them yourself

    R=/Users/rmanaloto/dev/github/ray-manaloto/dotfiles
    cd sandbox       && uv run --project "$R/python" pytest tests/ -q   # ARM 3, rc=0
    cd sandbox-naive && uv run --project "$R/python" pytest tests/ -q   # ARM 2, rc=1

`sandbox-naive/` currently holds the **naive mutation**. For ARM 1 (the original
defect), restore the pristine module:

    cp "$R/python/src/dotfiles_setup/command_audit.py" \
       sandbox-naive/python/src/dotfiles_setup/command_audit.py
