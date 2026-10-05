# Cold review: 37390929 (LLVM freeze gate, fix round 6), bounded round

- **Subject:** `37390929952e52c0cdcd2d6384b2250d3adc0cdc`, "fix(llvm): require apt head builds and recheck bump freshness". The author family is codex.
- **Worktree:** `dotfiles.worktrees/llvm23-20261002`, where HEAD == 37390929 (`git log --oneline -1`), so the working-tree line numbers below are the commit's.
- **Spec:** `docs/specs/llvm-major-detect-bump-fix6.md`. F1 was ruled by Ray: freeze requires apt to have built the current branch head.
- **Prior review:** `docs/research/kb/reports/agents/cold-reviewer-llvm-fix5-f2f163a9-2026-10-04.md`.
- **Mode:** BOUNDED. There are exactly six questions (Q1-Q6), and answering them ends the round. I used static reading, git and grep only. I ran no pytest, lint, verify, docker or network command.
- **Memory:** I consulted `.claude/agent-memory-local/cold-reviewer/`. Patterns 6, 12, 14 and 15 bear directly on this round.

## Verdict

**SHIP.** Q1-Q5 are YES and Q6 is NO. Q6 is phrased so that "NO" is the safe outcome: nothing outside the two files changed, and no invariant was weakened. No answer points in the defect direction, so the findings table is empty. The residual bounds are listed under Notes, as required for bounded rounds. They are not findings.

## Answers

### Q1. F1 condition (b), condition (a), and the three test cells: **YES**

- Condition (b) is exactly `apt_matches_head = build == head[:12]` (`python/src/dotfiles_setup/llvm_major.py:446`). `build` is the value stored as `Freeze.apt_build` and `head` is the value stored as `Freeze.branch_head` (positional args at `:448-458`; field order at `:62-70`).
- Condition (a) is still `ahead <= 1`: `frozen = ahead <= 1 and apt_matches_head and now - release_date >= _FREEZE_AGE` (`:447`).
- `tag_commit[:12]` no longer takes part in the decision. It is still validated (`:440`, through `_commit_sha`) and recorded.
- The tests are the rows of `test_freeze_independent_conditions` (`tests/test_llvm_major.py:360-385`). The fixture uses `head=TAG22 if ahead == 0 else TAG23` (`:382`), and `tag_commit` defaults to `TAG22` (`:199`).

  | Cell | Row | Expected |
  |---|---|---|
  | ahead 1, build == tag ≠ head | `:366` `(1, TAG22[:12], 14d, False)` | NOT frozen. This row fails at the parent f2f163a9, where it was `True` (`git diff f2f163a9 37390929` shows `-(1, TAG22[:12], …, True)`). |
  | ahead 1, build == head | `:365` `(1, TAG23[:12], 14d, True)` | frozen |
  | ahead 0, head == tag == build | `:363` `(0, TAG22[:12], 14d, True)` | frozen, with head=TAG22=tag_commit |

- Axis isolation is good. The ahead-2 row was changed to `build == head` (`:364`), so it now fails only on (a). The build-≠-head row (`:367`) and the age rows (`:368-371`) each isolate one axis.

### Q2. F2: does the bump path raise on a fresh build mismatch, and is there a test? **YES**

- `plan_bump` reads the version fresh through `_index_version` (`llvm_major.py:987`). The detected path then calls `_require_detected_build(version, detection.freeze_evidence[target])`. That call is guarded by `not explicit_control and target > pinned` (`:988-989`).
- `_require_detected_build` raises `RuntimeError("apt rebuilt -{major} since detection; re-run")` in two cases: when `_APT_BUILD.search(version)` is None, or when its group differs from `evidence.apt_build` (`:964-969`).
- The read is fresh, not cached. `detect` rebinds a local `fetch = cache(fetch)` (`:654`), while `_bump` passes the caller's raw `fetch` to `plan_bump` (`:1151`).
- `_index_version` requires one shared version across the complete amd64 and arm64 inventories (`:923-947`). The clang-T version is therefore that version, on both architectures.
- There are two tests:
  - **Unit test:** `test_plan_rechecks_detected_apt_build` (`tests/test_llvm_major.py:1603-1635`) has four arms:
    - the same build → passes;
    - the HEAD23 build → raises;
    - an unparsable `"1:23.1.0"` → raises (the `None` branch);
    - a version that carries the detected build only as a trailing substring → raises. This kills an `in version` mutation, because `search` reads the first `+<12hex>-1~exp1~`.
  - **CLI-path test:** `test_detected_bump_refuses_apt_rebuild` (`:1638-1662`) runs the real `bump_main`. The first read of the -23 amd64 `Packages.gz` (detection) is the original; every later read (plan, both architectures) is rewritten TAG22→HEAD23. The test asserts rc 1, the stderr message, and an unchanged tree.
- Deleting the call at `:988-989` lets the plan succeed. That fails both tests: `pytest.raises` fails in the first, and `== 1` plus `tree_bytes` fail in the second. This is a static derivation (UNVERIFIED at runtime).

### Q3. F3: does `_freeze_summary` read the recorded result, with tests that would fail if (b) changed alone? **YES**

- `relation = "matches" if evidence.apt_matches_head else "≠"` (`llvm_major.py:463`). There is no second copy of the predicate; the f2f163a9 set-membership line is gone (diff hunk at `:461-468`).
- **Both text variants are tested** from real `freeze_state` output in `test_freeze_summary_build_relation` (`tests/test_llvm_major.py:388-410`): `≠` at `:391` and `matches` at `:392-394`. The test asserts both `state.frozen` and the summary text.
- **Mutation 1:** revert (b) to the set test, either in `apt_matches_head` (`:446`) or only in the `frozen` expression (`:447`). In both cases row `:391` (ahead 1, build == tag) gets `frozen True`, and its `state.frozen is False` assertion fails.
- **Mutation 2:** re-introduce a recomputing summary. `test_freeze_summary_uses_recorded_build_match` (`:413-419`) uses `dataclasses.replace(state, apt_matches_head=False)` on a state whose build == head. A summary that recomputes would print "matches", and the `≠` assertion fails.

### Q4. F4: held-reason prefix, gate order, both explanations, and `for {codename}`: **YES**

- **Prefix:** `f"{held} GA+served, held: {', '.join(gates)}; "` (`llvm_major.py:625`).
- **Order:** IWYU is appended before freeze (`:619-623`).
- **Explanations:**
  - The IWYU explanation is `"IWYU: conda-forge include-what-you-use has no version whose newest builds on both Linux architectures target libllvm{held}; "` (`:626-632`). It has the same wording as the b1224700 text (`git show b1224700:…llvm_major.py:420-422`); only the framing changed from parentheses to `IWYU: …;`.
  - `"freeze: {_freeze_summary(...)}"` follows (`:633`).
  - Both-held output is `<M> GA+served, held: IWYU, freeze; IWYU: …; freeze: …`, which matches the spec format.
- **`for {codename}`:** restored at `:602` (`no suite served in [{pinned}, {newest}] for {codename}`) and `:638-640` (`M={newest} not served for {codename}; highest served in [P, M-1] = {target}`). Both are byte-identical to b1224700 `:408` and `:428-429`.
- **Tests:**
  - `test_detect_requires_both_gates` (`tests/test_llvm_major.py:616-653`): the prefix with `IWYU, freeze` / `IWYU` / `freeze`, the IWYU explanation when IWYU holds (`:647-651`), and its absence otherwise (`:653`).
  - `test_detect_no_suite_names_codename` (`:300-305`) and `test_detect_fallback_names_codename` (`:308-315`).

### Q5. F5/F6/F8: guard tests fail on deletion, realistic gh fake, wording and docstring: **YES**

These are static derivations. The runtime kill is UNVERIFIED here; the implementer reports 44 mutations killed, which is inherited evidence.

| Guard (source) | Test | What deleting the guard does |
|---|---|---|
| `_commit_sha` (`llvm_major.py:356-361`) | `test_freeze_rejects_invalid_commit_sha` (`tests:422-434`), 5 shas × {branches, commits} | Branch site: a 12-char head equals the build, so the state is frozen with no raise; `g*40` becomes not-frozen with no raise; `None[:12]` raises TypeError. Commit site: `tag_commit` is unused by the decision, so nothing raises. Every arm fails `pytest.raises(ValueError, match=…)`. This is the "never-asked becomes no" guard from memory pattern 15, now armed. |
| naive `now` (`:431-433`) | `test_freeze_rejects_naive_clock` (`tests:437-442`) | The fixture has ahead 0 and build == head, so the `and` chain reaches `now - release_date`. That raises TypeError, which is not ValueError, so the test fails. |
| no GA tag for M (`:428-430`) | `test_freeze_rejects_missing_major_ga` (`tests:445-450`) | `max({})` raises a ValueError whose message does not match `no GA llvmorg-22 tag found`, so the test fails. |
| `ahead_by` type/sign (`:442-444`) | `test_freeze_rejects_invalid_ahead_by` (`tests:453-462`): -1, "1", 1.0, True, None | -1, 1.0 and True become frozen with no raise; "1" and None raise TypeError. All arms fail. |
| clang-M count (`:391-396`) | `test_freeze_rejects_clang_count` (`tests:465-485`): 0 and 2 | 0 gives IndexError (wrong type); 2 silently picks the first version. Both fail. With the guard present, `apt_repo.parse_packages` neither dedups nor raises on empty input (`apt_repo.py:147-167`), so the arm reaches the guard. |

- **F6, the gh fake:**
  - `gh_output` now emits `HTTP/2.0 200 OK` plus two header lines with CRLF terminators (`tests:219-227`). The `offline_gh` fixture and the HTTP-failure test use it (`:230-240`, `:527`).
  - `test_freeze_gh_requires_http_200` builds a status line, `Content-Type` and `X-Github-Request-Id` with both `\n` and `\r\n` (`:553-583`).
  - `default_gh` splits on `b"\n\n"` after normalising `\r\n` → `\n` (`llvm_major.py:188`), so both fake variants hit the real separator.
  - Suppose a regression splits on the first newline. Then the 200 arm's body starts at `Content-Type:`, and `json.loads` raises, which fails the `== {"sha": TAG22}` assertion (`tests:577-580`).
- **F8, the clang-count message:** it now reads `{suite}/main/binary-amd64/Packages.gz: expected exactly one clang-{major} version` (`llvm_major.py:391-396`). That is accurate: `RepoQuery.for_llvm` defaults to `arch="amd64"`, component `main` (`apt_repo.py:86-106`). It is asserted at `tests:478-485`.
- **F8, the summary date:** it now reads `suite published {date} (Release Date)` (`llvm_major.py:467`), asserted at `tests:410` and `:646`.
- **F8, the `bump_main` docstring:** it now reads "IWYU/freeze holds change no files" (`:1168`). The `freeze_state` docstring was also corrected to "an apt build of head" (`:417`).

### Q6. Changes outside the two files, or a weakened invariant? **NO** (the safe answer)

- **Files:** `git show --numstat 37390929` lists only two files: `python/src/dotfiles_setup/llvm_major.py` (+51/-21) and `tests/test_llvm_major.py` (+212/-9).
- **Never-asked != no:** this is preserved. `_body` (`:300-306`) and `suite_served` (`:471-480`) are untouched. The new `_require_detected_build` raises when the build is unparsable (`:967`), so it never passes silently. The newly armed `_commit_sha` closes the one guard whose deletion degraded to "no".
- **P never re-gated:** eligibility is unchanged, `major == pinned or (ready[major] and evidence[major].frozen)` (`:604-608`). The new bump re-check fires only for `target > pinned` (`:988`), and the explicit-control Detection with empty evidence is excluded by `not explicit_control`. `test_detect_never_regates_pin` is intact (`tests:656-672`).
- **Parity literal scan:** `_LITERAL` (`:52-55`), `_python_violations` (`:706-747`) and the scanned-file list (`:904-907`) are all outside the diff's hunks.
- **No test was removed:** the test-function count went from 68 at f2f163a9 to 79 at 37390929, which is 11 additions. The only `-` lines in the test diff are the old fake, the two re-specified rows, a docstring, a signature, the old status line and two strengthened asserts.

## Findings

| Severity | Claim | file:line | Cited |
|---|---|---|---|
| — | None. No question has a defect-direction answer. | — | — |

## Notes (residual bounds, not findings; ticket only if the owner wants them)

1. **F2 checks only the build commit.** A same-commit rebuild has a new `~++<timestamp>` and republishes the suite with a new Release `Date`. It passes `_require_detected_build`, so the bump would pin a version whose suite publication is under 14 days old. GitHub head and `ahead_by` are not re-read at bump time either. Spec F2 asked only for the build check (`docs/specs/llvm-major-detect-bump-fix6.md`, F2 bullet), so this is outside the enumerated domain. It is a Q-FRESH residual for the spec owner.
2. **IWYU-only hold still appends `freeze: <summary>`** even though freeze is not a held gate (`llvm_major.py:633`). The `held:` list is the authoritative clause. The spec defines the format only for the both-held case, so this is not a Q4 failure.
3. **`--json` output gains `freeze_evidence.<M>.apt_matches_head`** through `asdict` (`:1078`, `:1108`). The change is additive. The only tracked consumer reads `--markdown` (`.github/workflows/refresh.yml:184`), and the markdown table did not gain a column for it (`:1095-1103`).
4. **The real `gh api --include` line terminator is UNVERIFIED offline.** Correctness does not depend on it, because `default_gh` normalises CRLF and both terminators are tested.
5. **All mutation-kill claims in this report are static derivations.** The implementer's "228 passed, 44 mutations killed" (`docs/research/kb/reports/agents/codex-sol-implementer-llvm23-fix6-2026-10-04.md`, header section; untracked) is inherited evidence and was not re-derived here.

## GitHub repos touched

_None._ This was a local static review only.
