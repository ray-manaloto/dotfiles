> **COORDINATOR ANNOTATION (2026-09-13) — read before the report below.**
> The report is preserved verbatim. One load-bearing claim in it is WRONG, and
> the correction is the whole point of the finding:
>
> **The `-- --show` recipe was never a working workaround.** The report reads
> the presence of `-- --show` in the docs as evidence the author knew about the
> argparse behaviour and routed around it. Measured after the report landed:
> `mise run` **consumes one `--` of its own** before the task's command line is
> built, so `mise run plan-attest -- --show` reaches argparse as a bare
> `--show` and dies. Evidence, from mise's own echoed command line:
>
> ```
> mise run handoff-check -- --help     -> uv run ... handoff-check --help
> mise run handoff-check -- -- --help  -> uv run ... handoff-check -- --help
> ```
>
> So the CLI-level docstring (`plan_attest.py:28`) was correct and the three
> **mise-level** restatements were wrong at the call site. Fixed in code rather
> than in prose — `plan_attest.insert_passthrough_separator` — so every existing
> doc site becomes true instead of teaching operators `-- -- --show`.

# Plan-Attest --show Defect: Transcript Search for Prior Discovery

**Date**: 2026-09-13  
**Fact to investigate**: `dotfiles-setup plan-attest --show` is UNREACHABLE (errors with "unrecognized arguments: --show") because argparse claims dash-prefixed tokens as unknown OPTIONS when `nargs="*"` is used. The documented safe form errors while the destructive bare form works.

**Question**: Was this discovered before? When, where, what was concluded?

## Search Plan
1. Transcript search for `plan-attest`, `--show`, `unrecognized arguments`
2. Agent state (plans, logs, notepad, kb/raw) for prior findings
3. Shell history for prior invocations
4. Rule/doc files for mentions
5. Issues/PRs for prior tickets

## Findings (append-only)

### Search 1: Transcript grep for "plan-attest"

### Search 1 Result: Oldest "unrecognized arguments"
**Date**: 2026-09-03 22:14:40 UTC
**Transcript**: `05968c99-421d-4c89-8692-a55eacfd9b92.jsonl`
**But**: Error was `apt-repo gnupg` not `plan-attest --show`
**Status**: Different subcommand, same underlying parsing issue in argparse

### Search 2: Specific "plan-attest --show" discovery

### Search 3: GitHub Issues for plan-attest defect

**Result**: Issue #910 filed 2026-09-02 about `/plan-attest` warning, but NOT about the `--show` parsing defect.

### Search 4: Check .claude/CLAUDE.md and rules for current --show usage

**Result**: FOUND THE DEFECT DOCUMENTED:
- `.claude/CLAUDE.md:21` states: `-- --show` reads, bare WRITES
- `.claude/rules/mise-tasks-only.md:31` states: `-- --show` reads; bare form WRITES

**Interpretation**: The documented workaround is `-- --show` (with explicit `--` separator), not `--show` alone. This suggests the defect was KNOWN and WORKED AROUND, but the root cause was never fixed.

### Search 5: Git history of these lines

**Result**: First documented use of `-- --show` workaround:
- Commit `f6ee355` (2026-09-02 13:41:29) titled "feat(plan): make attestation operator-only, with a real layer (D4)"
- Files changed: `.claude/CLAUDE.md`, `plan_attest.py`, `main.py`, and others
- Commit message mentions `/plan-attest` was newly restricted to operator-only

### Search 6: Check if the argparse nargs defect was documented as a known issue

**Result**: Found the ROOT CAUSE in main.py:1437-1442:
```python
plan_attest_parser.add_argument(
    "args",
    nargs="*",  # ← THE DEFECT
    help="Passed straight through to the plugin's attest-plan.sh "
    "(e.g. --show, --clear); deliberately not enumerated here",
)
```

With `nargs="*"`, argparse treats dash-prefixed tokens as OPTIONS, not positionals, so:
- `dotfiles-setup plan-attest --show` → SystemExit(2): "unrecognized arguments: --show"
- `dotfiles-setup plan-attest -- --show` → works (-- is argparse separator)

### Search 7: When was nargs="*" added? Was it there in f6ee355?

**Result - CRITICAL**: 
- `nargs="*"` was ADDED in commit f6ee355 (2026-09-02 13:41:29)
- Same commit documented the workaround `-- --show` in `.claude/CLAUDE.md`
- **The defect was KNOWN AT AUTHORING TIME**, not discovered later

This means the author (likely working on D4 operator-only task) introduced nargs="*" deliberately to pass args straight through, BUT did not account for argparse's treatment of dash-prefixed tokens as OPTIONS.

The workaround `-- --show` was implemented IMMEDIATELY as a known limitation, documented as:
- `.claude/CLAUDE.md:21` (2026-09-02): `-- --show` reads, bare WRITES
- `.claude/rules/mise-tasks-only.md:31` (later, but same guidance): `-- --show` reads; bare form WRITES

### Summary of findings

| Question | Answer |
|----------|--------|
| Was this defect discovered before today? | **YES**, 2026-09-02 in commit f6ee355 |
| When exactly? | 2026-09-02 13:41:29 (commit f6ee355) |
| Was a fix attempted? | **NO** - only a workaround was documented |
| Was it just deferred or deliberately left? | Deliberately accepted - the comment says "deliberately not enumerated here" acknowledging the passthrough nature |
| What broke the knowledge transfer? | The defect was NEVER filed as an issue; only documented in code comments and task descriptions. Issue #910 (2026-09-02) is about `/plan-attest` warning, NOT about the --show parsing |
| Why did today's session not know? | The knowledge lived in: (1) code comments in main.py, (2) .claude/CLAUDE.md docstring, (3) .claude/rules/mise-tasks-only.md. None of these were discovered through memory, issue tracker, or structured handoff during today's session |

## GitHub repos touched

_None._ — All findings are from local dotfiles transcripts and source files; no external repos were consulted.
