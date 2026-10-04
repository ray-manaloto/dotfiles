# Cold review — feat/jobdir-part2 — ad4dbc62..ad86300d

- Base: `ad4dbc62bce8989928210007e4487f84109e1cfe`
- Head: `ad86300d5a2e156bc5548a9b593e3e72407f8f27` (branch `feat/jobdir-part2`, worktree HEAD == head)
- Commits: `b1240a4d` (spec), `ad86300d` (impl)
- Spec: `docs/specs/jobdir-dispatch-gate-2026-10-04.md` (in the reviewed range)
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start (no prior patterns).
- Status: COMPLETE — **SHIP** (0 HIGH, 0 MEDIUM; 8 LOW, 5 INFO)

## Findings

| Severity | Claim | file:line | Evidence |
|---|---|---|---|
| LOW | Check-5 nonzero is reported as `git unavailable: <stderr>` although git ran and failed; the spec never names a message for this branch (§3.2.5, §4 only say fail closed), so this label was the implementer's choice | `python/src/dotfiles_setup/sdlc_team.py:810-812` | branch read; reached by `tests/test_sdlc_team.py:610` probe `commit/nonzero` (rc=0 module run) |
| LOW | A spec `read_bytes()` OSError (`:773`) is caught by the outer handler and reported as `git unavailable: …`. The spec requires this (§3.2 "does the same"), so the fix belongs in the spec. The prefix wrongly names git as the cause | `python/src/dotfiles_setup/sdlc_team.py:773`, `:814-815` | `tests/test_sdlc_team.py:676` asserts the `git unavailable:` prefix for a FileNotFoundError |
| LOW | Q-CLAIM: every check-1 nonzero exit becomes `spec is not inside a git work tree` and git's stderr is dropped. That covers dubious ownership (#1183 class), a cwd inside `.git`, and a corrupt repo. The spec requires the exact string, so this is a ticket against the spec | `python/src/dotfiles_setup/sdlc_team.py:790-791` | code read; spec §3.2.1 `docs/specs/jobdir-dispatch-gate-2026-10-04.md:156-157` |
| LOW | Q-CLAIM: the skill says `spec_uncommitted` means "the spec is not a file committed under `docs/specs/`…". The status is also returned for git timeout, missing git, the read race and a check-5 failure, and in those cases the spec may well be committed. The clause has no enforcing line for those branches | `.claude/skills/codex-sdlc-team/SKILL.md:77` (mirror `.agents/skills/codex-sdlc-team/SKILL.md:77`) | `sdlc_team.py:812`, `:815` return under the same status at `:860` |
| LOW | The skill's "Read the dispatch result" list of `SdlcTeamDispatch` contents was not updated with the two new provenance fields `spec_commit` and `spec_path`, which are the point of this change | `.claude/skills/codex-sdlc-team/SKILL.md:68-71` | grep `spec_commit` over the skill → 0; the model has them at `sdlc_team.py:101-102` |
| LOW | Q-FRESH: HEAD is resolved twice. Checks 3 and 4 read `HEAD:<rel>`, then check 5 reads `HEAD` again. If HEAD moves in between (a `reset --soft`, a commit or a checkout in the same worktree), `spec_commit` names a commit other than the one whose blob was compared. Resolve the sha once and verify `<sha>:<rel>`. The ordering comes from the spec | `python/src/dotfiles_setup/sdlc_team.py:745-769`, `:802-809` | code read (a timing race, so no live repro) |
| LOW | Q-FRESH, a sibling of this ticket: the gate holds only at dispatch. The lane later reads the working-tree path from the `SPEC FILE:` line, and the prompt never tells it to read `<sha>:<rel>`. An edit made after dispatch therefore drifts from the recorded `spec_commit`. Ticket recommendation | `python/src/dotfiles_setup/sdlc_team.py:285-294` | prompt text read; spec §1 scopes the outcome to dispatch time (`docs/specs/jobdir-dispatch-gate-2026-10-04.md:85-94`) |
| LOW | Test gap: if `timeout=_GIT_TIMEOUT_S` is deleted from any git call, the whole module still passes. The timeout cells raise `TimeoutExpired` from the fake `Popen` constructor whether or not the call has the kwarg. Static mutation analysis, not executed | `tests/test_sdlc_team.py:634` | fake raises at construction regardless of kwargs (`:628-645`) |
| INFO | No test pins `_SPEC_PATH_MIN_PARTS = 3`. No cell commits a file named literally `docs/specs`, so mutating it to 2 survives | `python/src/dotfiles_setup/sdlc_team.py:194`, `:797` | S2 cell list `tests/test_sdlc_team.py:383-397` |
| INFO | The PLR0911 residual is met with no headroom: `dispatch` and `_spec_commit_error` have exactly 6 returns each, so the next added return fails ruff | `python/src/dotfiles_setup/sdlc_team.py:818`, `:779` | return lines enumerated below; armed control: 7 returns → `PLR0911 (7 > 6)`, 6 → clean |
| INFO | The committed spec's header still reads "NOT ratified, NOT dispatched" and names branch `fix/jobdir-dispatch-gate`. The appended sections (`:590-609`) record ratification and the real branch, so the top of a tracked doc contradicts its bottom | `docs/specs/jobdir-dispatch-gate-2026-10-04.md:6`, `:445-446` | file read |
| INFO | The commit body of `ad86300d` leaves out the citations §6 requires: the parent spec, the `sdlc-team-review-jobdir-artifacts-29a5dcc4.md` report (tracked, `git ls-files` rc=0) and the §R Q7 ruling. The squash PR body can carry them | `docs/specs/jobdir-dispatch-gate-2026-10-04.md:450-455` | `git log -1 --format=%B ad86300d` |
| INFO | `text=True` decoding can raise `UnicodeDecodeError` (a `ValueError`), which the `except` does not catch, so "no exception escapes" is not enforced for a toplevel path that is not UTF-8. APFS makes this unreachable on the Mac host. UNVERIFIED on Linux | `python/src/dotfiles_setup/sdlc_team.py:814` | code read; UNVERIFIED |

## Notes (incremental)

### Probes run (each with its rc read from a file)

- `uv run --project python pytest tests/test_sdlc_team.py -x -q` → `80 passed`, rc=0 (`/tmp/cold-review-ad86300d-pytest.log`).
- `ruff check` on `sdlc_team.py` + `tests/test_sdlc_team.py` → rc=0; `--select PLR0911,PLR0912,PLR0915,C901` → rc=0.
  - Control arm for PLR0911 under `--config python/pyproject.toml` (`select = ["ALL"]`, `pyproject.toml:76`, no `max-returns` override):
    a scratch 7-return function → `PLR0911 Too many return statements (7 > 6)` rc=1; the 6-return copy → clean. So the
    ceiling is 6 and the probe discriminates.
- `ty check` on the two Python files → rc=0.
- `dotfiles-setup skills-mirror --check` → `skills-mirror OK`, rc=0.
- `PLANNING_DISABLED|LANE_ENV_OVERRIDES` in `sdlc_team.py` → 0 (control `SPEC_MISSING|spec_missing` → 2 in same file).
- Inline suppressions added by the diff (`noqa|type: ignore|pylint: disable|nosec`) → 0 (control: `cast(` in the same diff → 6).

### §3.2 — every git call (4 of 4 checked)

| Call | file:line | literal `"git"` | `capture_output` / `check=False` | `timeout=_GIT_TIMEOUT_S` | `env=child_env.without_git_context()` | capture type (spec) |
|---|---|---|---|---|---|---|
| 1 `rev-parse --show-toplevel` | `sdlc_team.py:782-789` | yes | yes | yes | yes | `text=True` (spec: text) — OK |
| 3 `rev-parse --verify --quiet HEAD:<rel>` | `sdlc_team.py:745-760` | yes | yes | yes | yes | `text=True` (spec: text) — OK |
| 4 `cat-file blob HEAD:<rel>` | `sdlc_team.py:763-769` | yes | yes | yes | yes | bytes, no `text=` (spec: bytes) — OK |
| 5 `rev-parse HEAD` | `sdlc_team.py:802-809` | yes | yes | yes | yes | `text=True` (spec: text) — OK |

Check 2 is a pure path-component check (`sdlc_team.py:793-798`), no git call, `len(parts) >= 3` and `parts[:2] == ("docs","specs")`.

### Error / timeout branches of `_spec_commit_error` (all enumerated)

| Branch | file:line | Result | Spec | Test that reaches it |
|---|---|---|---|---|
| check 1 rc≠0 | `:790-791` | `spec is not inside a git work tree` | §3.2.1 | S2 `not-a-repo`; probe `worktree/nonzero` |
| `relative_to` ValueError → `Path()` | `:793-796` | falls to path-mismatch message | §3.2.2 | symlink `inside=False` |
| path component mismatch | `:797-798` | `ratified specs live in docs/specs/` | §3.2.2 | S2 `research`/`ignored`/`prefix` |
| check 3 rc≠0 | `:761-762` | `spec is not committed at HEAD` | §3.2.3 | S2 `untracked`/`staged`/`unborn`; probe `membership/nonzero` |
| check 4 rc≠0 | `:771` | `working tree differs from the committed spec` | §3.2.4 (fail closed, same message) | probe `blob/nonzero` |
| check 4 digest mismatch | `:772-775` | same message | §3.2.4 | S2 `edited` |
| spec `read_bytes` OSError | `:773` → `:814-815` | `git unavailable: <exc>` | §3.2 ("does the same") | `test_spec_disappearing_during_git_read…` |
| check 5 rc≠0 | `:810-812` | `git unavailable: <stderr or 'could not resolve HEAD'>` | **not specified** (spec only says fail closed, §4) | probe `commit/nonzero` |
| any OSError / TimeoutExpired | `:814-815` | `git unavailable: <exc>` | §3.2 | S2 `git-unavailable`; probe `*/timeout` (4 cells) |

No branch returns `(None, …)` except `:813`, after all five checks. Fail-open: none found.

### Return counts (PLR0911 residual)

- `dispatch`: returns at `:834, :848, :865, :881, :1000, :1015` = **6** (ceiling).
- `_spec_commit_error`: `:791, :798, :801, :812, :813, :815` = **6** (ceiling).
- `_committed_spec_bytes_error`: `:762, :775, :776` = 3.
No function exceeds 6. Both are AT the ceiling.

### §5.2 mutation arms — static kill analysis (not executed; reviewer may not edit source)

| Arm | Killed by | Reasoning |
|---|---|---|
| M8 delete gate | every S2 cell, S5, probe cells, symlink-outside | dispatch reaches the hostile fake → `AssertionError` (not `OSError`, `:986`) propagates |
| M9 `ls-files` for check 3 | S2 `staged`, `unborn`; probe `membership` (its argv match `:failures==1` breaks) | as spec R18; S2 `untracked` survives by design |
| M10 string prefix | S2 `prefix` | `docs/specsX` passes → launch fake raises |
| M11 drop digest | S2 `edited` | — |
| M12 gate review too | S3 (`git_calls == []`, status) | — |
| M13 drop prompt line | S1 (`lines[index+1]`) | — |
| M14 OSError → None | S2 `git-unavailable`, probe timeouts | reaches launch fake |
| M15 revert T0 | T0 `DISPATCHED` assertion | `_request` spec at `tmp_path/spec.md`, not a repo → refused |
| M16 old schema | schema-equality test | enum lacks `spec_uncommitted` |

Extra mutations outside the spec's enumeration (enumeration audit):

- drop `env=` scrub from any ONE call → killed by `test_implement_git_probes_use_the_specs_worktree_and_scrub_hook_context`
  (poisoned `GIT_OBJECT_DIRECTORY`/`GIT_COMMON_DIR` break calls 1/3/4; call 5 would return `other_sha` or fail).
- drop `text=True` from call 1 → `TypeError` crash, killed; from call 5 → `spec_commit` is `bytes`, S1 equality killed;
  add `text=True` to call 4 → `sha256(str)` `TypeError`, killed; drop `text=True` from call 3 → survives (harmless).
- delete `timeout=` from any call → **survives every test** (the timeout cells raise `TimeoutExpired` from the fake
  `Popen` constructor, `tests/test_sdlc_team.py` probe test, independent of the kwarg).
- `_SPEC_PATH_MIN_PARTS` 3 → 2 → survives (no cell commits a FILE named `docs/specs`).
- delete check-5 rc branch (`:810-812`) → killed by probe `commit/nonzero` (dispatch reaches launch fake).

### §5.1 test arms vs spec (enumerated)

| Spec arm | Test | Conforms |
|---|---|---|
| F1 `_REAL_POPEN` at import | `tests/test_sdlc_team.py:27` | yes |
| F1 passthrough in `_capture_dispatch` (unrecorded git) | `:246-275` | yes. git goes to a separate optional list, so `len(calls)` keeps its meaning |
| F2 `_committed_spec` (`init -b main`, `-c commit.gpgsign=false`) | `:198-210` | yes. It adds `add -f`, which the S2.6 `.agent/` case needs |
| T0 IMPLEMENT on committed spec + `DISPATCHED` for both cells | `:339-358` | yes |
| S1 sha, literal `spec_path`, line immediately after `SPEC FILE:`, `len(calls)==1` | `:362-382` | yes |
| S2.1-S2.9 with message, `pid`, `argv`, no prompt, no non-git Popen | `:384-448` | yes. All 9 cells are present, and S2.9 runs the fixture before emptying PATH (R17) |
| S3 review draft: zero git calls measured, byte-identical prompt | `:451-476` | yes. It also pins `build_prompt(review, spec_commit=…)` as unchanged |
| S4 skill tokens | `:479-485` | yes |
| S5 CLI with both boundary fakes before `run_command` | `:488-517` | yes |
| Boundary rule R1 (every dispatch-calling arm fakes `which` and `Popen`) | all new tests | yes. Checked for every new test, extras included (`:520`, `:559`, `:610`, `:676`, `:712`) |
| Schema equality | `:2158` | passes (module rc=0) |

Extras beyond the spec: env-poison scrub (`:520`), post-gate provenance (`:559`), 4×2 probe-failure matrix (`:610`),
read race (`:676`), symlink alias in and out (`:712`).

### Q-SCOPE

Every finding is in scope for part (2) except two. The gate→lane freshness row is a sibling and should be ticketed. The
check-1 message and the read-OSError message are spec-mandated, so they need a spec amendment rather than a change to
this diff.

### Refuted hypothesis (control-armed)

Could a `GIT_CONFIG_PARAMETERS` `core.worktree`, which `child_env` does not scrub, retarget `--show-toplevel`? The
override was confirmed live (`user.name` override → `Qv7`, and `git config core.worktree` → `/nonexist`), but
`rev-parse --show-toplevel` returned the real repo in both the control and the poisoned arm. Refuted, so it is not a
finding.

### Consumers

No code consumer parses dispatch status except `sdlc_team_main`, which exits rc 0 only for `DISPATCHED`.
`git grep` over `*.py|*.js|*.ts|*.toml|*.json|*.pkl` returns `main.py`, `hook_guard.py`, `suites.toml`, `mise.toml`,
`rule-sync.toml` and the tests. `.claude/workflows/gated-implementation.js` uses `codex-sol-implementer`, not
sdlc-team (control: `codex` hits 7 in that file), so it is ungated as §R Q5 says.

## Verdict

**SHIP.** All four git calls carry the literal `"git"`, `capture_output`, `check=False`, `timeout=_GIT_TIMEOUT_S`
and `env=child_env.without_git_context()`, and each has its stated capture type (calls 1/3/5 `text=True`, call 4
bytes). Every error and timeout branch of `_spec_commit_error` fails closed and has a reaching test. No function
exceeds 6 returns. Every §5.1 arm is present and follows the boundary rule. The LOW rows are message, doc and
test-pin precision; none can launch a lane on an uncommitted spec.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local reads only of the reviewed range, its spec,
  conftest, `hk.pkl`, `mise.toml`, `child_env.py`, the workflows and skills.
