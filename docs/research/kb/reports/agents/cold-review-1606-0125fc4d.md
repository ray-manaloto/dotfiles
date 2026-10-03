# Cold review — 0125fc4d (base 911bcffd)

- Subject: `0125fc4df224916813a2b498baee8307a7b9c16d` "fix(hooks): apply cold-review F1-F7 to the #1606 EnterWorktree guard"
- Base: `911bcffdf70e8b64c746724bea4c4c98fe40b0d5` (the round-1 subject; parent of 0125fc4d)
- Worktree: `.claude/worktrees/fix-1606` (branch `fix/1606-enterworktree-guard`, HEAD == subject)
- Prior round: `docs/research/kb/reports/agents/cold-review-1606-911bcffd.md` (main checkout) — F1-F7 + I1
- Reviewer: cold-reviewer (Opus), diff-only, no ticket read
- Status: COMPLETE

## Verdict

**SHIP.** All three round-1 MEDIUMs (F1-F3) and F4-F6 are resolved and re-verified against Claude Code
2.1.288's own predicate; F7 is resolved except one residual enumeration. In the 20-cell real-wrapper
decision table (E4), every cell the guard ALLOWS is one Claude Code also allows, so no cell parks a
session (the #1606 failure). Gates re-run by this lane: targeted pytest 107 passed, `verify run`
172 passed / 0 failed, ruff + format + ty clean, strict token replay 0 fails with a discriminating control.
9 of 11 mutations are killed; the 2 survivors either fail closed or are pathological (I2). The four LOW findings below are cheap (each
under 5 lines) and recommended for this unit, but none blocks; I1-I3 are informational, and T1 is a
sibling ticket recommendation.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| R2-1 | LOW | The fail-closed flip took away the ship/land selfcheck's ability to detect a guard that cannot run git. Its only `path=` arm is a DENY, and an unverifiable path now also DENIES with both required tokens (`#1606`, `EnterWorktree name=`). There is no positive `path=` allow arm, so a guard that denies EVERY `path=` passes the gate. Cheap fix: also require the deny stdout to name the resolved main checkout (an unverifiable deny prints the literal `<main>`), or add a registered-worktree allow arm | `python/src/dotfiles_setup/hook_selfcheck.py:500` (unchanged); cause `python/src/dotfiles_setup/worktree_guard.py:52-53`, `:61-62` | E5: base 911bcffd + no git, selfcheck RED; subject + no git, selfcheck GREEN (`[]`) |
| R2-2 | LOW | Q-CLAIM: the deny for an UNVERIFIABLE path (git missing or failing, a mise-shim `git` choking on a bad `mise.toml`, an embedded NUL) reuses the location-violation text. It says the target "must be an existing worktree under <main>/.claude/worktrees/". It never says verification failed, keeps the literal `<main>` placeholder, and drops git's stderr. So a valid registered target is told it violates the policy | `python/src/dotfiles_setup/worktree_guard.py:20-31`, `:52-53`, `:61-62` | E4 N8 (`… under <main>/`); E5 no-git row; the host `git` is a mise shim (`which -a git` → `~/.local/share/mise/shims/git` first) |
| R2-3 | LOW | Stale prose around the new anchor and the fail-closed flip. (a) The `hook_dispatch` module docstring still says one stdin read feeds "both halves" (policy guard + graphify), with no mention of the third consumer this diff now routes through `handles()`. Its "Fails open like its predecessors" is true only for UNCAUGHT exceptions; the worktree guard turns its own errors into denies. (b) The selfcheck comment says EnterWorktree "needs the wrapper's project-root anchor", but the anchor is now the payload `cwd`, with project-root only as the fallback. (c) A test docstring still names "a non-repo fail-open path" that no longer exists | `python/src/dotfiles_setup/hook_dispatch.py:14-22`; `python/src/dotfiles_setup/hook_selfcheck.py:102`; `tests/test_worktree_guard.py:181` | Read at subject; `worktree_guard.py:37` ("deny paths we cannot verify") |
| R2-4 | LOW | F7 residual: TEST-INDEX now says "nine tools" but its parenthetical enumerates eight (`Bash…NotebookEdit` guarded, `Grep|Read|Glob` nudged); `EnterWorktree` is absent | `tests/TEST-INDEX.md:55` | `git grep` at subject (E6) |
| I1 | INFO | Case-variant path on APFS (`.claude/WORKTREES/a`): the guard DENIES, but Claude Code's bun `realpath` canonicalises case and ALLOWS. This over-denies only (no park), and the deny names the correct path | `python/src/dotfiles_setup/worktree_guard.py:60`, `:79` | E4 N11; bun 1.4.0 vs Python `os.path.realpath` |
| I2 | INFO | Two mutants survive, and both fail closed or are pathological. M7: running `git worktree list` from `project_dir` instead of `anchor` — no test ALLOWs a registered worktree of a cwd-repo different from the project repo. M11: dropping `target != allowed` — reachable only if a worktree is registered AT `.claude/worktrees` itself | `python/src/dotfiles_setup/worktree_guard.py:65`, `:68-69` | E7 |
| I3 | INFO | Process note, not a defect: THIS branch touches `python/verification/suites.toml` (`SURFACE_PATTERNS` `python/verification/*`), so `mise run ship` from this linked worktree will refuse with rc 2 (#1481). Run `git switch --detach` here, then ship from the main checkout | `python/src/dotfiles_setup/pr.py:112`, `:612-626`, `:572` | Read at subject |
| T1 | LOW (sibling → ticket) | The #1606 policy makes `<main>/.claude/worktrees/` the ONLY sanctioned location, but the tracked `.gitignore` ignores only `.worktrees/`. This clone hides `.claude/worktrees/` through the per-clone `.git/info/exclude:11` alone. In a fresh clone, the first `EnterWorktree name=` makes the main checkout dirty (`?? .claude/`), and `mise run ship` from main then refuses "working tree not clean". `$CC/worktrees.md:32` says to add `.claude/worktrees/` to `.gitignore`. Out of this diff's lines: recommend a ticket | `.gitignore:22-23` (subject); `python/src/dotfiles_setup/pr.py:559-562`, `:602-607` | Arms: fixture without ignore → `?? .claude/`; real main with exclude → 0 hits; `git check-ignore -v` → `.git/info/exclude:11` |

## Prior findings F1-F7 — resolved?

| Prior | Resolved? | Evidence |
|---|---|---|
| F1 (MEDIUM) nonexistent path under managed dir allowed | **RESOLVED** — allow now requires `target.is_dir()` AND an exact match in `git worktree list --porcelain -z`; old `foo` allow arms replaced by the registered `canonical`/`lane`; new deny arms for nonexistent, unregistered, moved-registered | `python/src/dotfiles_setup/worktree_guard.py:65-87`; `tests/test_worktree_guard.py:74-80`, `:94-123`; E4 cell P1 |
| F2 (MEDIUM) relative path / repo anchor used `CLAUDE_PROJECT_DIR`, not payload `cwd` | **RESOLVED** — dispatch threads payload `cwd` (str, non-empty) into `decide`; `decide` anchors BOTH `--git-common-dir` and the relative join to it; P2/P3 dispatch tests on a real repo | `python/src/dotfiles_setup/hook_dispatch.py:55-58`; `worktree_guard.py:43-59`; `tests/test_hook_dispatch.py:36-104`; E1, E4 cells P2/P3 |
| F3 (MEDIUM) handoff step not executable (ship "from main" after EnterWorktree) | **RESOLVED** — ship now from the handoff worktree itself (docs-only, no full-sync), ExitWorktree `keep` before any main-checkout ship; mirror identical modulo PER_FILE | `.claude/skills/coordinator-handoff/SKILL.md:49-56`; `pr.py:612` (`needs_full_sync` + linked-worktree refusal); E3 |
| F4 (LOW) parallel-work-split coordinator stays isolated before `git -C` | **RESOLVED** — ExitWorktree `keep` inserted before the lane-creation block | `.claude/skills/parallel-work-split/SKILL.md:87-90` |
| F5 (LOW) reason cited a prompt false under `bypassPermissions` | **RESOLVED** — reason and module docstring now state a uniform location policy; test pins absence of the prompt clause across 3 modes | `worktree_guard.py:5`, `:26`; `tests/test_worktree_guard.py:139-155` |
| F6 (LOW) `handles()` had no production caller | **RESOLVED** — dispatch calls `worktree_guard.handles(tool_name)`; contract token moved to the call site | `hook_dispatch.py:55`; `suites.toml:1341` |
| F7 (LOW) stale "eight-tool" prose; hook_guard docstring misattributed routing | **PARTIAL** — both "eight" sites now say "nine" and the docstring is fixed, but `tests/TEST-INDEX.md:55` enumerates only eight of the nine (EnterWorktree absent) — see R2-4 | `docs/rules-evidence/mise-tasks-only.md:126`; `hook_guard.py:33-36`; `tests/TEST-INDEX.md:55` |

## Evidence log

### E1 — Claude Code 2.1.288's own predicate re-derived (binary mmap scan; installed `~/.local/share/claude/versions/2.1.288`)

`EnterWorktree.checkPermissions` (offset ~194789279): no `path` → allow; `n = await vMr(path)`;
`n?.managed` → allow; else `behavior:"ask"` ("permission-root relocation … outside .claude/worktrees/").

`vMr` (offset ~188110314): `r = oe()` (current cwd); `s = Es(r)`; `if(!h) return null` (non-repo → ask);
`b = realpath(resolve(r, path))` (ENOENT → catch → null → ask); `w = realpath(Es(r))`;
managed iff `K = join(w,".claude","worktrees")` is not a link AND `J2(K, b, {strictly:true})`.
`Es` (offset ~181000875): `cr(e)` (nearest git root) → `canonicalRootByRoot` → the MAIN checkout for a
linked worktree. So CC's root is derived from the **current cwd**, which is exactly what the guard now
does (`git rev-parse --git-common-dir` run in the payload cwd → parent). Registration is NOT checked in
`checkPermissions`; `call` → `sqn` throws "is not a registered worktree" / "marked prunable" / "locked"
(offset ~188110314 region) — so the guard's registration requirement is STRICTER than CC (deny vs a tool
error, never a park).

Docs: `$CC/hooks.md:626-629` and `$CC/worktrees.md:46-49` — `${CLAUDE_PROJECT_DIR}` stays put; payload
`cwd` follows EnterWorktree and `cd`. `$CC/hooks.md:757` — `cwd` is a common input field.

### E2 — targeted pytest at the subject

`uv run --project python pytest tests/test_worktree_guard.py tests/test_hook_dispatch.py tests/test_hook_selfcheck.py -q`
in the subject worktree → `107 passed`, `rc=0` (`/tmp/cr1606r2/pytest.log`). Reproduces the commit
message's "107 targeted tests pass". The worktree venv imports the SUBJECT module
(`worktree_guard.__file__` = `.claude/worktrees/fix-1606/python/src/…`).

### E3 — strict `per_path_tokens` replay + mirror parity

SUBJECT suites.toml vs SUBJECT files: 1414 tokens, **0 fails**. Control: BASE (911bcffd) suites.toml vs
SUBJECT files: 1406 tokens, exactly 2 fails (`if tool_name == "EnterWorktree":` and
`reason = worktree_guard.decide(tool_input, project_root)` — the replaced dispatch lines), so the replay
discriminates. `.agents/skills/{coordinator-handoff,parallel-work-split}/SKILL.md` are real files;
`diff` against the `.claude` copies shows only the PER_FILE reversions (`.claude/`→`.agents/`
self-paths, "Ask Claude"→"Ask Codex"). Mirror current.


### E4 — decision table through the REAL wrapper (subject venv; isolated `/tmp/cr1606r2/fx` fixture)

Driver `/tmp/cr1606r2/probe.py`: `/bin/bash scripts/pretooluse-guard.sh` with `CLAUDE_PROJECT_DIR=<fixture main>`,
`UV_PROJECT_ENVIRONMENT=<subject venv>`, payload `cwd` as listed. Fixture built with global/system git config
isolated. No fail-open was recorded (`DOTFILES_GUARD_FAILOPEN_LOG` never created).

| Cell | guard | CC 2.1.288 (E1) | agree? |
|---|---|---|---|
| CTRL abs registered sibling `repo.worktrees/sib` | DENY | ask | yes (control) |
| CTRL abs registered managed `a` | ALLOW | allow | yes (control) |
| CTRL `name=x` | ALLOW | allow | yes (control) |
| P1 abs nonexistent managed `new-lane` | DENY | ENOENT → ask | yes (was fail-open in r1) |
| P2 `../a`, project=main, cwd=`b` | ALLOW | allow | yes (was over-deny in r1) |
| P3 `.claude/worktrees/a`, cwd=`main/python` | DENY | ENOENT → ask | yes (was fail-open in r1) |
| N1 existing UNREGISTERED dir under managed | DENY | allow → `call` throws "not a registered worktree" | stricter, no park |
| N2 registered but moved (prunable) | DENY | ENOENT → ask | yes |
| N3 registered + locked | ALLOW | allow → `call` throws only if a live CC session holds the lock | no park |
| N4 nested registered `a/nested` | ALLOW | allow | yes |
| N5 the managed dir itself | DENY | `strictly` → ask | yes |
| N6 subdir of registered (`b/python`) | DENY | allow → `call` throws (not registered) | stricter, no park |
| N7 cwd in ANOTHER repo, abs `a` | DENY | `Es(cwd)`=other root → ask | yes |
| N8 cwd non-repo, abs `a` | DENY (`<main>` placeholder) | `Es` null → ask | yes (see R2-2) |
| N9 `../../a` from `b/python` | ALLOW | allow | yes |
| N10 trailing slash `a/` | ALLOW | allow | yes |
| N11 case variant `.claude/WORKTREES/a` (APFS) | DENY | bun `realpath` canonicalises case → allow | over-deny only (INFO I2) |
| N12 `/private/tmp` spelling | ALLOW | allow | yes |
| N13 no `cwd` field, project=`b`, `../a` | ALLOW | allow | yes (fallback) |
| N14 cwd=`a`, path=`b` (switch) | ALLOW | allow | yes |

Every guard-ALLOW cell is a CC-allow cell, so no cell parks (the #1606 failure). N11 evidence: `bun -e
fs.promises.realpath(".../WORKTREES/a")` → `.../worktrees/a`, Python `os.path.realpath` keeps `WORKTREES`
(bun 1.4.0; CC is a bun binary).

Real repo (`/tmp/cr1606r2/realrepo.py`, project=real main, subject venv): registered `fix-1606` ALLOW;
`../dotfiles.worktrees/foo` DENY; `/tmp/x` DENY; `name=x` ALLOW; `../codegen-default-group` from cwd
`fix-1606` ALLOW; cwd=knowledge-base + abs dotfiles worktree DENY. Reproduces the commit message's
"real wrapper denies /tmp/x and ../dotfiles.worktrees/foo, allows the registered worktree and name=x".

### E5 — the selfcheck's worktree arm lost its "guard could not run git" teeth

`/tmp/cr1606r2/selfcheck_arm.py` calls `hook_selfcheck.check_worktree_guard_endtoend` (real wrapper) with
the guard module selected by `PYTHONPATH` (`-P` does not drop `PYTHONPATH`; the printed `__file__`
confirms which module ran):

| guard module | PATH | selfcheck failures |
|---|---|---|
| subject 0125fc4d | ambient (git present) | `[]` |
| subject 0125fc4d | `/nonexistent` (no git) | `[]` ← every `path=` is now denied, gate green |
| base 911bcffd | ambient | `[]` |
| base 911bcffd | `/nonexistent` | `["pretooluse wrapper did not DENY … the #1606 guard is not reachable"]` |

The base row proves the arm discriminates; the subject row proves the fail-closed flip made "deny" no
longer evidence that the guard computed anything, and the selfcheck has no positive `path=` allow arm.

### E6 — prose / doc sites

`git grep -nP 'NotebookEdit\|Grep\|Read\|Glob(?!\|EnterWorktree)'` at subject: only `.codex/hooks.json:5`
(codex has no EnterWorktree) and two verbatim reports (not to be normalised). "eight-tool" is gone from
`docs/rules-evidence/mise-tasks-only.md:126` and `tests/TEST-INDEX.md:55` (both now "nine"); the
TEST-INDEX parenthetical still lists eight tools (R2-4). `hook_guard.py:33-36` docstring now attributes
EnterWorktree routing to `hook_dispatch` correctly.

### E7 — mutation table (`/tmp/cr1606r2/mutate.py`; `git archive 0125fc4d python tests`; copy's tests import the copy)

The pristine control row fails 4 wrapper tests that need `scripts/` (not archived); those 4 fail
identically in EVERY row, so the table reads the DELTA against the control (59 tests run per row).

| Mutation | New failures vs control | Killed? |
|---|---|---|
| M0 pristine | — (55 passed) | control |
| M1 drop `target.is_dir()` | `test_denies_missing_registered_worktree` | yes |
| M2 registration → any record | `test_denies_existing_unregistered_directory` | yes |
| M3 dispatch ignores payload `cwd` | P2 + P3 dispatch tests | yes |
| M4 `decide` anchors to project_dir | P2 + P3 + `test_repo_anchor_follows_cwd_in_another_repo` | yes |
| M5 rev-parse failure → fail open | `test_nonrepo_denies_unverifiable_path` | yes |
| M6 exception → fail open | `test_missing_git_denies…`, `test_invalid_string_path_is_denied` | yes |
| M7 `worktree list` cwd=project_dir | none | **survives** (I2; fails closed) |
| M8 dispatch accepts `cwd=""` | `test_enterworktree_without_valid_cwd_falls_back_to_project_root` | yes |
| M9 final deny drops `main` | 3 tests (20 parametrised cases) | yes |
| M10 drop permission-mode sentence | `test_location_policy_is_uniform_across_permission_modes` | yes |
| M11 drop `target != allowed` | none | **survives** (I2; pathological) |

### E8 — other gates (subject worktree)

`uv run --project python dotfiles-setup verify run` → `172 passed, 0 failed, 4 skipped`, rc=0 (valid from a
worktree: its venv's editable install points at the worktree). `ruff check` + `ruff format --check` on the
4 changed python files → clean, rc=0; `ty check` on the 2 changed modules → clean, rc=0. `mise run lint`
NOT run (whole-tree, host-wide slot).

## Required questions

### Q-FRESH

1. Hook decision (PreToolUse) → Claude Code `checkPermissions`/`call`. The guard re-reads git
   (`--git-common-dir`, `worktree list`) and the filesystem (`resolve`, `is_dir`) on every call, with no cache.
   CC re-validates registration, prunable and lock state in `call` (`sqn`, E1). The guard's ALLOW is
   therefore re-checked by the actor immediately before the action.
2. Inside `decide`, rev-parse → containment → worktree list → `is_dir` run sequentially in one call against
   fresh reads. The only window is the hook→call gap, and CC's own re-check covers it.
3. Payload `cwd` → anchor: read from the same payload CC built for this tool call (`$CC/hooks.md:629`).
No freshness finding.

### Q-SCOPE

R2-1 through R2-4 and I1-I3 are in scope for #1606: they touch the guard, its gate, and this diff's
prose. T1 is a sibling, made load-bearing by #1606 but outside this diff's lines, so it goes to a ticket.

### Q-CLAIM — every clause of every operator-facing string this diff adds or changes

| String / clause | Enforcing line | Holds? |
|---|---|---|
| deny: "path={target} must be an existing worktree under {allowed}/" | `worktree_guard.py:76` (`is_dir`) + `:78-82` | yes when `main` is known; no for the unverifiable branch (R2-2) |
| deny: "strictly inside that directory" | `:65` | yes |
| deny: "and registered with this repo" | `:67-82` (`worktree list` from the anchor's repo) | yes |
| deny: "This location policy applies in every permission mode." | `decide` never reads `permission_mode`; test `:139-155` | yes |
| deny: "For NEW worktrees, from the main checkout ({checkout}), use `EnterWorktree name=<name>`" | `:39-40` (`name=` never denied) | yes; `{checkout}` is the literal `<main>` on the unverifiable branch (R2-2) |
| deny: "From inside a worktree session, use `EnterWorktree path={allowed}/<name>` for an existing registered worktree" | the allow branch `:65-84` | yes (E4 N14, P2) |
| deny: "or ExitWorktree (keep) before creating a NEW worktree with name=" | CC `validateInput` "Already in a worktree session … use ExitWorktree" (E1) | yes |
| module docstring: "Restrict EnterWorktree paths to existing managed worktrees" | `:65-87` | yes |
| `decide` docstring: "deny paths we cannot verify" | `:52-53`, `:61-62`, `:85-87` | yes |
| `hook_guard` docstring: "hook_dispatch routes EnterWorktree to its dedicated guard" | `hook_dispatch.py:55` | yes |
| suites.toml description: "resolve from payload cwd to existing registered managed worktrees" | tokens at `suites.toml:1341` | yes |
| TEST-INDEX: "nine tools (…)" | n/a | count right, enumeration short (R2-4) |
| skill: "Re-enter that existing registered worktree with `EnterWorktree path=…`" | guard allow branch; E4 | yes |
| skill: "`mise run ship` from the handoff worktree itself: `pr.py:598-626` permits linked-worktree ship when the change does not need a full sync" | `pr.py:612`; `SURFACE_PATTERNS` has no `docs/**` | yes. That CC's worktree isolation "command shape" check lets `mise run ship` run from inside an EnterWorktree session is **UNVERIFIED** (no live arm) |
| skill: "Before any main-checkout ship, use `ExitWorktree` with `keep`" | `$CC/worktrees.md:89-93`; `.claude/types/claude-code.d.ts:12444-12445` (`action: "keep"`) | yes |
| skill (parallel-work-split): "leave that isolated session with ExitWorktree using keep … Run the main-checkout `git -C <repo> worktree add` only after that exit" | `$CC/worktrees.md:91` | yes |

## What was done / not done

Read-only probes only. Ran: git show/grep/diff, an mmap scan of the installed CC 2.1.288 binary,
targeted pytest, `verify run`, ruff, ty, the strict token replay, and the real wrapper against an isolated
`/tmp` fixture and the real repo (decision only; nothing entered a worktree). Also ran an archived-copy
mutation harness and `bun`/Python realpath probes. No source, config, test or fixture in the repo was
edited. `mise run lint` was NOT run. CC behaviour is binary-derived, not exercised through a live
EnterWorktree call.

## GitHub repos touched

_None._ (Local sources only: this repo at 0125fc4d / 911bcffd, the knowledge-base offline Claude Code docs
corpus `$CC`, and the installed Claude Code 2.1.288 binary.)
