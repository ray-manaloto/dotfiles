# mattpocock Standards review — S29-H (4e337900), 2026-09-29

Verbatim.

**Standards review of `4cb1fa81...HEAD` (S29-H).** I only read files and wrote nothing. Please persist this report yourself.

**(a) Where the diff breaks a documented standard**

1. **`session_state.py`: the PR lists are capped at 100 and nothing says so (hard).** `_PR_LIST_LIMIT = "100"` feeds `gh pr list --limit` for both the open list and the merged-since list. If more than 100 PRs match, the list is quietly cut short and still rendered as if complete. The handoff then carries incomplete state that looks authoritative. This breaks `probes-need-a-control-arm.md` rule 3: every bound must be removed or shown to contain the target. Either detect `len(rows) == limit` or print the cap in the output.
2. **`pr_facts.py`: `classify_check` hand-sorts checks into pass/fail/pending using `_PASS_VALUES`/`_FAIL_VALUES` (judgement, leaning hard).** The repo already relies on gh's own `bucket` field (`pr.py:386-392`, via `gh pr checks --json name,bucket`). `use-tool-builtins.md` requires a written reason when custom code is kept over a built-in. The spec gives none (`docs/specs/s29h-...md:52` only declares the enum). A likely valid reason exists: `gh pr list` does not return `bucket`. It needs to be written down in the code or the PR.
3. **Tests for `session_state`: the gh seam is patched, not passed in (judgement).** `tests/AGENTS.md` § Mocking says to prefer passing the dependency in. `handoff_check` does this correctly with its `facts=` parameter. `session_state.gather` has no such parameter, so its tests patch `pr_facts.run_gh` module-wide. Also, `test_default_facts_resolve_through_the_patched_run_gh` builds `pytest.MonkeyPatch()` by hand with `undo()` instead of using the fixture.

**(b) Code smells (all judgement calls)**

- **Primitive Obsession:** `PrFacts.state: str` and `PrSummary.state: str` are compared as the strings `"OPEN"`/`"MERGED"`. `claim_holds` uses `facts.state == word.value`, which ties an enum's display text to GitHub's wire value. Failures come back as `PrFacts | str`, a bare string used as an error signal. The same file's existing style uses `PrState.UNVERIFIABLE`.
- **Duplicated Code / Shotgun Surgery:** `session_state._check_word` (RED, green, PENDING) re-states the RED/GREEN rules in `handoff_check.claim_holds`. Changing what "green" means requires editing both. The round-trip test does soften this.
- **Data Clumps:** `PrFacts` and `PrSummary` both carry number, state, auto_merge and checks.
- **Middle Man:** `check()` now only forwards to `check_with_claims(...)[0]`.
- **Duplicated parsing:** `main.py` turns the args argparse already parsed back into an argv list. `session_state.main` then parses that list again with a hand-written `iter(args)` loop.
- **Long function:** `_claim_findings` handles the deadline, caching, lookup-failure reporting and judging all in one loop. It stores the deadline message in `answers` and then wraps it in a redundant `str(...)`.
- **Mutable global setting:** `CLAIMS_DEADLINE_S` is a public module constant, read at call time, and tests change it with monkeypatch.
- **Feature Envy (minor):** `session_state` imports `handoff_check` only to call `newest_handoff`.

**Clean:** there is no new `.sh`, so `bash_logic_budget` is unaffected. The mise task changes touch descriptions only. The gh mocking stays at the system boundary. The implement report records five live GitHub runs of the real commands, each with a failure check, which meets `real-integration-evidence.md`.

## GitHub repos touched

_None._ (Local diff review only.)
