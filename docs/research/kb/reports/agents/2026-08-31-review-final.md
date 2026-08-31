# Cold review — c121741680e963e7388121a82f45b086ad21d9ce (parent 756f26c)

## Area 1 — containment invariant
Every mutating call in `install_skill()` (graphify_skill.py:244-264: `mkdir`,
`rmtree`+`copytree` for references/, `copy2` for `.bak`, `copy`+`.replace` for
the temp-file rename, `write_text` for `.graphify_version`) derives its target
from `placement.skill_dst.parent`. `resolve_placement()` now gates on
`skill_dst.parent.is_relative_to(project_root)` with no `!=` exemption
(graphify_skill.py:186). Enumerated: no write derives from anything else.
Verdict: COMPLETE for this file, for the checked class of inputs (absolute,
`..`-laden, and `""`/`"."`).

Reproduced the round-3 mutation myself: reverted to the old
`skill_dst != project_root and not skill_dst.is_relative_to(project_root)`
guard, ran `pytest tests/test_graphify_skill.py` — the new
`test_resolve_placement_refuses_a_skill_dst_that_resolves_to_project_dir_itself[]`
test failed with "DID NOT RAISE UnsafePlacementError", exactly as the commit
message claims. Restored the file, confirmed `git status` clean.

Residual, NOT introduced by this commit (pre-existing / inherent):
- TOCTOU between `resolve_placement()`'s `.resolve()` and the writes in
  `install_skill()` — a symlink swapped in between is not defended.
- `project_dir` itself being a symlink whose real target is outside the
  caller's intent — `.resolve()` would follow it and "project_root" becomes
  the symlink target, so containment holds relative to the wrong root.
- `refs_dst`'s `rmtree` deletes only the entry at that path (not a followed
  symlink target — Python 3.12+ raises rather than deleting through a
  top-level symlink), so a references/ symlink-swap doesn't escape further
  than the entry itself.
These are pre-existing conditions this round didn't touch and the brief
didn't attribute to this round, noting for completeness only.

## Area 2 — doctor/hk parity
hk step (hk.pkl:657, UNTOUCHED by this commit):
`test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB'
.agents/skills/graphify/SKILL.md && ! grep -q 'use the installed graphify
skill' AGENTS.md && test ! -e .codex/skills/graphify`
= 4 facts: (a) claude SKILL.md exists, (b) agents SKILL.md carries stub
marker (implicitly requires it exists too — missing file fails grep), (c)
AGENTS.md doesn't carry the vendor marker, (d) `.codex/skills/graphify`
absent.

doctor.py `check_graphify_skill_surface` (now 4 assertions): required_skill_files
(both SKILL.md paths exist), stub_marker present in stub_file, forbidden_paths
absent, and the NEW `forbidden_agents_md_marker` not in AGENTS.md
(doctor.py:1145-1157, doctor.toml:184-189). Semantically matches hk's 4 facts
1:1 (doctor's fact #1 covers hk's facts (a) AND the implicit existence half of
(b); doctor's stub-marker check covers the rest of (b)). Genuinely closes the
gap the commit message describes — before this commit doctor lacked the
AGENTS.md-marker fact entirely.

Mutation-tested myself: commented out the new `agents_md_marker` block in
doctor.py (`if False and isinstance(...)`), ran
`pytest tests/test_doctor.py -k graphify_skill_surface` — the new
`test_graphify_skill_surface_flags_a_landed_vendor_install_marker` failed
(`assert 0 == 1`), confirming the test actually exercises the new code.
Restored, `git status` clean.

Control arm for "both fail on broken state / pass on restored": the new
test pairs a healthy fixture (silent, asserted elsewhere in the file) against
the marker-present fixture (`len(findings) == 1`) — both arms present and
verified above.

Verdict: parity claim now holds for the 4 facts enumerated; not "identical
mechanics" (doctor groups differently) but equivalent discriminating power.

## Area 3 — tests
- New tests use genuinely new input shapes ("" and ".") not covered by the
  round-1/round-2 tests (absolute path, `..`-laden path) — confirmed by
  reading `_with_malicious_skill_dst` call sites (tests/test_graphify_skill.py:
  204-259).
- Mutation-tested both new test pairs myself (graphify_skill.py guard,
  doctor.py new block) — both fail under the reverted/disabled code, both
  pass restored. See Area 1/2 above.
- No test touches real network, $HOME, or wall clock — all use `tmp_path`/
  `monkeypatch`.

## Area 4 — prose
SKILL.md sweep (`.claude/skills/graphify-skill-install/SKILL.md`) is accurate
post-edit: describes `skill_dst.parent` as the validated/write target,
matches code.

**FOUND A FOURTH STALE CLAIM the sweep missed:**
`UnsafePlacementError`'s class docstring, graphify_skill.py:62-70 (UNCHANGED
by this commit — confirmed via `git show 756f26c:...` byte-identical):

    """A platform's declared ``skill_dst`` resolves outside ``project_dir``.
    ...
    is raised instead of silently writing (or silently skipping) whenever
    the joined-then-resolved destination is not `project_dir` itself or
    beneath it.
    """

This literally says the exception is NOT raised when the destination
resolves to `project_dir` itself ("is not project_dir itself or beneath
it" — i.e. project_dir itself is treated as a safe case). That is exactly
the ROUND-3 BUG this very commit fixes: `skill_dst` of `""`/`"."` resolves to
`project_dir` itself, and after this commit it DOES raise
`UnsafePlacementError` (correctly). The class docstring was never touched
by the "sweep for other stale containment claims" this commit's message
claims to have done, and it is now the fourth commit in a row to carry an
inaccurate claim about what's guaranteed — same pattern the review brief
was hunting for, just in a docstring instead of prose.

Severity: MEDIUM — not exploitable by itself (the code is correct; only the
comment lies), but it directly misdescribes the exact invariant this round
exists to fix, in the same file, one function up from the fix. A future
reader/auditor citing this docstring would conclude the "" / "." case is
safe, when it's the opposite.

## Commit message vs `--stat`
Matches: `.claude/skills/graphify-skill-install/SKILL.md`, `doctor.toml`,
`python/src/dotfiles_setup/doctor.py`, `python/src/dotfiles_setup/graphify_skill.py`,
`tests/test_doctor.py`, `tests/test_graphify_skill.py` — all six named/implied
in the message, no undisclosed files touched. `hk.pkl` correctly NOT touched
(commit says "H2's hk.pkl fix from the prior round is untouched" — verified,
hk.pkl not in the diff).

Test count claim ("26 tests in the file pass") verified: `pytest
tests/test_graphify_skill.py -q` → 26 passed.

## Full-suite / gate reruns
In progress (background) — pytest tests/ full run; will report actual counts
against the "2608 passed" claim.
