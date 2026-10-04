<!-- verbatim SubagentHandback of agent aed96876ae537f9a5 (premise-verifier, session c769e1a1), extracted from its subagent JSONL 2026-10-04 by coordinator 5a11da -->

PREMISE REPORT: spec-jobdir-part2-dispatch-gate.md
(/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04e/docs/research/kb/raw/specs-2026-10-04d/spec-jobdir-part2-dispatch-gate.md)

This lane is read-only (Read/Grep/Glob only, no shell, no Write), so nothing was written to findings.md. The coordinator needs to persist this report.

Baseline I read: main checkout working tree. `.git/refs/heads/main` and `.git/refs/remotes/origin/main` are both `ee3b29da24a4…`. `.git/logs/refs/remotes/origin/main:213` shows `ed8e1a96 → ee3b29da pull --ff-only`. You said "at or after d921a3f6". That sha appears nowhere in `.git/{FETCH_HEAD,logs/HEAD,packed-refs,refs/**}`; the control is `ee3b29da`, which does hit in those files. So I cannot place d921a3f6 relative to ee3b29da, and every verdict below is against ee3b29da. I assumed the main working tree is clean, because I could not run `git status`.

ROWS: 44 checked — 34 CONFIRMED (0 provenance corrected) / 5 REFUTED / 0 UNVERIFIABLE / 5 ASSUMED (1 checkable)

1 — REFUTED (stale) — `.git/refs/heads/main:1` = `ee3b29da24a4e64f30f0576353cee0331c7c75b5`, not `36ab6bba`.
2 — REFUTED (stale) — `.git/refs/remotes/origin/main:1` = `ee3b29da…`, the same as local main. The "origin ahead of local" premise no longer holds.
3 — CONFIRMED (historical only) — `.git/logs/refs/remotes/origin/main:211` reads `36ab6bba… eba2e4e4… fetch -q origin: fast-forward`. It is superseded by lines `:212-213`, ending at ee3b29da.
4 — CONFIRMED — `.git/logs/refs/heads/fix/codex-banner-ansi:2` reads `4fdbac59 → 2d81c36d commit: fix(sdlc-team): settle codex runs whose exec banner is ANSI-coloured`. The `.git/logs/HEAD:1057-1058` cite is not the place this is recorded; the branch log is.
5 — CONFIRMED, and now on main — `sdlc_team.py:819-822` on main is the comment plus `"--color", "never"`, and `dispatch` is still at `:723`.
6 — ASSUMED — I cannot read the PR number. The code is consistent with the claim: main now carries exactly the BA hunk, and the test `:412-416` asserts `--color never`.
7 — CONFIRMED — main `generate_dispatch_schema` `:1067`, `sdlc_team_main` `:1093`. The BA prediction now describes main.
8 — CONFIRMED — main `tests/test_sdlc_team.py`: `_request` `:171`, `_capture_dispatch` `:185`, sandbox test def `:270`, `--color` asserts `:412-416`, schema test def `:1706`.
9 — ASSUMED (moot) — I could not diff eba2e4e4..ee3b29da. Every cited file was re-read at ee3b29da instead (below), so this row no longer carries weight.
10 — CONFIRMED — `sdlc_team.py:56-62`.
11 — CONFIRMED — `sdlc_team.py:83-98`, the last field is `errors: tuple[str, ...] = ()` at `:98`.
12 — CONFIRMED — `_DispatchState` `:172-180`; `_resolved_dispatch` `:214-253` builds `SdlcTeamDispatch` by keyword (`:237-251`).
13 — CONFIRMED — `build_prompt` `:256-293`; `SPEC FILE:` `:274`; REVIEW clause `:261-267`. The signature is `build_prompt(request, repo_root)` at `:256`.
14 — CONFIRMED — 0 hits for `SPEC_UNCOMMITTED|spec_uncommitted|spec_commit` across python/tests/schemas/.claude/skills/.agents/skills. The control `SPEC_MISSING|spec_missing` gives 7 hits (6 plus the `.agents` mirror). The control anchor `tests/test_sdlc_team.py:1666` is now `:1671`.
15 — CONFIRMED — 0 hits for `\bgit\b|subprocess\.run` in `sdlc_team.py`. The same pattern gives 6 lines in `session_common.py` (`:184,186,187,194,197,202`).
16 — CONFIRMED — `sdlc_team.py:723-777` is exact: INVALID `:727-739`, SPEC_MISSING `:741-753`, CLI_MISSING `:755-767`, paths `:769-777`.
17 — REFUTED (anchor rot from #1662) — argv is now `:811-828` (spec says `:811-824`). The `try` (prompt write `:833`, unlink `:834`, `subprocess.Popen` `:852`) and `except OSError → INVALID_REQUEST carrying argv` are now `:830-878` (spec says `:826-874`). DISPATCHED result `:880+`. The behaviour is as described.
18 — CONFIRMED — `sdlc_team.py:16` `import subprocess`.
19 — CONFIRMED — `tests/test_sdlc_team.py:185-203` (fake records every call and returns `_DetachedProcess`; patches `sdlc_team.subprocess.Popen` and `sdlc_team.shutil.which`). `_DetachedProcess` `:28-31` has no `__enter__`.
20 — CONFIRMED — `:266-286`: the IMPLEMENT cell uses `_request` (an untracked `tmp_path/spec.md`, `:171-182`) and asserts only flag absence (`:285-286`).
21 — REFUTED (anchor rot, +5/+4) — the CLI test is now `tests/test_sdlc_team.py:1651-1673` (spec says `:1646-1668`); `sdlc_team_main` is now `:1093-1110` (spec says `:1089-1106`). Behaviour holds: `:1110` `return 0 if result.status is SdlcStatus.DISPATCHED else 1`.
22 — CONFIRMED — `schemas/sdlc-team-dispatch.json:1-97`, required `:73-76`, enum `:81-86` (4 values, sorted alphabetically).
23 — REFUTED (anchor rot) — the schema-equality test is now `tests/test_sdlc_team.py:1698-1714` (spec says `:1693-1709`); `generate_dispatch_schema` is now `sdlc_team.py:1067-1069` (spec says `:1063-1065`). Semantics hold: parsed-JSON equality at `:1711-1714`; `codec.schema(SdlcTeamDispatch)` at `:1069`.
24 — CONFIRMED — `sdlc_team.py:700-720` (`shutil.which("mise")` `:712`, `which("codex")` `:715`).
25 — CONFIRMED — `…/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py:512` `def run(`, `:554` `with Popen(*popenargs, **kwargs) as process:`. The venv home is that dir (`python/.venv/pyvenv.cfg:1`).
26 — CONFIRMED — `.claude/skills/codex-sdlc-team/SKILL.md:51`.
27 — CONFIRMED — `SKILL.md:72-77`; mirror `.agents/skills/codex-sdlc-team/SKILL.md:75`.
28 — CONFIRMED — `mise.toml:1389-1392`; `hk.pkl:733-734`.
29 — CONFIRMED — `skills_mirror.py:122-125`.
30 — CONFIRMED — `mise.toml:294-296`; `main.py:3056-3058`.
31 — CONFIRMED — `suites.toml:3046-3052` (`regex_forbid`, `PLANNING_DISABLED|LANE_ENV_OVERRIDES`, path `sdlc_team.py`).
32 — CONFIRMED — `tests/conftest.py:27-49`.
33 — CONFIRMED — `session_common.py:32`.
34 — CONFIRMED — `tests/test_worktree_guard.py:19-22` (`timeout=10`), `:30` (`init -b main`), `:35` (`-c commit.gpgsign=false commit`).
35 — CONFIRMED — the only sdlc hit is `tests/test_sdlc_team.py:268`. The other hits are `cv.Edge.REOPEN_IMPLEMENT`, which shows the probe matches.
36 — CONFIRMED — `:326-344`, `:364-367`.
37 — CONFIRMED — `agent-artifact-conventions.md:48`, `:75`.
38 — CONFIRMED — `.gitignore:125` `.agent/`; no `docs/specs` match.
39 — CONFIRMED — `HW/…/spec-jobdir-preservation.md:310-341`.
40 — CONFIRMED — same file `:466-479`, `:492-493`.
41 — CONFIRMED — same file `:600`.
42 — CONFIRMED — same file `:676-679`.
43 — ASSUMED — `--show-toplevel` symlink resolution. §3.2 resolves both sides, so nothing rests on it.
44 — ASSUMED (checkable) — this matches the existing pattern for every `str = ""` field (`schemas/sdlc-team-dispatch.json:33-36`, `:61-64`). The equality test settles it.

MISSING:
- **S5 can launch a real paid codex lane under mutation M8 (load-bearing).** The S5 precedent (`tests/test_sdlc_team.py:1651-1673`) fakes neither `shutil.which` nor `Popen`. It is safe today only because SPEC_MISSING returns before launch (`sdlc_team.py:741-753`). S5's spec exists, so with the gate deleted (M8), dispatch reaches the real `_codex_launcher` (`:712-720`, real `mise` and `codex` on the host) and the real `subprocess.Popen` at `:852`: a detached supervisor running real `codex exec`. The fix is for S5 to patch `sdlc_team.subprocess.Popen` with the F1 git-passthrough raising fake (and optionally `which`), so M8 fails S5 by assertion instead of by spending credits.
- **No git-context scrub on the gate's git calls (recommended correction).** The repo convention is that every production git probe passes `env=child_env.without_git_context()` (`child_env.py:71-74`; used at `pr.py:244,259`, `doctor.py:1524,1656`, `session_state.py:120`, `sync.py:414,436`, `pr_facts.py:53`). The reason is in `tests/test_pr.py:525-528`: "GIT_DIR overrides `git -C`". §3.2 omits it, so an inherited `GIT_DIR`/`GIT_WORK_TREE` from a hook or editor would retarget `rev-parse --show-toplevel` and `HEAD:<rel>` away from the spec's worktree. In tests the pre-push suite already strips these (`mise.toml:310-314`, `process git-isolated`), but plain `mise run test`/`uv run pytest` does not. Add it to §3.2's "every git call" sentence. F1's `_REAL_POPEN(command, **kwargs)` forwards `env=`. S2.9 still works because the scrubbed copy keeps the emptied PATH.
- **The order of setup in S2.9 matters and is not stated.** `_committed_spec` must run before `monkeypatch.setenv("PATH", empty)`, or the fixture's own git calls fail. Also, `git` resolves through a mise shim on this host (`conftest.py:61-64`), and this is irrelevant once PATH is emptied.
- **The skill example request will become a refused shape.** `SKILL.md:37-48` shows `"mode": "implement"` with `"spec_file": "/absolute/path/to/spec.md"`, which the gate now refuses. If U1 is accepted, change the example path to `…/docs/specs/<name>.md` (then the mirror regenerates).
- **Text vs bytes capture is unstated for checks 1, 3 and 5.** §3.2 says only check 4 is bytes. Checks 1 and 5 need `text=True` or an explicit decode before `Path(stdout.strip())` and the returned sha. State it, or the implementer may pass bytes into `Path` (TypeError, which escapes the `OSError`/`TimeoutExpired` catch). `session_common.py:186-192` is the `text=True` precedent.
- **Byte comparison assumes no eol/smudge filters.** There is no `.gitattributes` in the repo (Glob found nothing), so blob bytes equal working-tree bytes today. Non-blocking residual: a future `.gitattributes` eol rule would make check 4 fail closed (safe direction).
- **M9 does not make S2.1 fail.** With `ls-files --error-unmatch` as check 3, an untracked file still fails `ls-files` and returns the same message, so S2.1 stays green. S2.2 and S2.3 fail, because check 4's `cat-file HEAD:<rel>` returns the check-4 message instead of the expected check-3 message. The spec already says "or be explained". Record that S2.1 is expected to survive M9.
- **The other Popen-patching tests are all review mode,** so F1 does not need to touch them (`tests/test_sdlc_team.py:337,367,402,434,466,1614`; only `:268` uses IMPLEMENT). This is an implicit premise of "the only edits to existing tests" in §4, and it holds.

VERDICT: FIX SPEC FIRST. The four corrections below are blocking; the residuals after them are not.
1. **S5 safety (load-bearing):** require S5 to patch `sdlc_team.subprocess.Popen` with the F1 git-passthrough raising fake, so M8 cannot launch a real supervisor or codex.
2. **Rotted anchors (REFUTED rows):**
   - Rows 1-3 and the provenance caveat: local main = origin/main = `ee3b29da`. Drop the "unpulled main" narrative.
   - The #1662 paragraph and U3: #1662 has already merged, so the "+4/+5" caveat is now just fact. Cut from ee3b29da (or later), not "after #1662".
   - Row 17: argv `:811-828`, try/except `:830-878`.
   - Row 21: test `:1651-1673`, `sdlc_team_main` `:1093-1110`.
   - Row 23: test `:1698-1714`, `generate_dispatch_schema` `:1067-1069`.
   - Row 14 control anchor: `:1666` → `:1671`.
   - Rows 7-8: restate as main anchors.
   - Row 9: drop it (re-derived).
3. **Git env scrub:** add `env=child_env.without_git_context()` to the "every git call" sentence in §3.2, citing `pr.py:244` as the precedent.
4. **Capture types:** state that checks 1, 3 and 5 use `text=True` (or decode), and that check 4 alone captures bytes.

Non-blocking residuals:
- Row 6: an unverified PR number, with no effect on code.
- Rows 43-44: settled by the design and by the equality test.
- d921a3f6: its relation to ee3b29da is unverified. Before cutting, the coordinator should run `git merge-base --is-ancestor d921a3f6 ee3b29da` (or diff the §2 files between them).
- `.gitattributes`: none today; a future eol rule fails closed.
- Skill example path: only relevant if U1 is accepted.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local reads of sdlc_team.py, session_common.py, child_env.py, main.py, skills_mirror.py, tests, conftest, schemas, SKILL.md, suites.toml, mise.toml, hk.pkl, .gitignore, git refs/logs, and the parent spec in the handoff-2026-10-04d worktree.
