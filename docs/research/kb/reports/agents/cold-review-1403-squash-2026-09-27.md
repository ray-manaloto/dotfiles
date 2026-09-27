# Cold review — #1403 squash `42a699c8` (Brief O)

- **Subject:** `42a699c850ba355eff8e0ba175c46ea1d26a5f5d` (parent `1c38e19b867a29d037d23dda3cb380ec19b4febb`)
- **Diff:** `git diff 42a699c8^ 42a699c8 -- . ':(exclude)docs/research/**' ':(exclude)*.lock' ':(exclude)docs/hk-builtins-audit.md'` — 27 files, +754/-72
- **Lens:** Opus cold-reviewer, cold (no intent supplied beyond the brief)
- **Round type:** OPEN HUNTING (round 1 on the squash) — cannot end the loop by any outcome.
- **Memory:** local cold-reviewer memory consulted.
- **Status:** COMPLETE: 9 findings (1 MEDIUM, 8 LOW), 0 HIGH. The prior F1 fix was verified effective with both arms (E4).

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| N1 | LOW | `ASSET_BACKENDS` omits `conda` although 21/21 conda entries in the committed lockfiles carry `platforms.<p>` checksum tables (and `core` 10/11 do), so an empty conda entry — the exact #1398 shape — passes the new absolute check. The comment's "npm/pipx/core/cargo/go … legitimately platform-less" list is also wrong twice: `core` is mostly platformed, and the one platformless non-listed backend present is `pypi` (`mise.lock` `pypi:azure-cli`). Whether `mise install --locked` fails on an empty conda entry is UNVERIFIED. | `python/src/dotfiles_setup/lock_integrity.py:114` | E1 |
| N2 | LOW | Two docstrings in this diff describe #1398's mechanism incompatibly: `lock_shared.lock_target` says mise 2026.9.8's bare `mise lock` is "a silent no-op: rc 0, NO entry written"; `lock_integrity` says the same command "wrote the version and nothing else". Only the second shape is visible to `platformless_asset_entries`; if the first is true, the delete-then-relock recipe leaves NO entry and the new absolute check cannot fire (it iterates existing entries only). Which is true is UNVERIFIED (needs mise 2026.9.8 in-container). | `python/src/dotfiles_setup/lock_shared.py:243` vs `python/src/dotfiles_setup/lock_integrity.py:112` | E2 |
| N3 | LOW | `event_has_hk_hook` trusts the NAME, not the command: a config hook named `hk-pre-commit` whose command is `true` counts as installed, and a hookdir script that merely mentions `hk run` in a comment and `exit 0`s counts too. The module docstring's claim "Which hk git hook events will actually RUN" is enforced only for enabled/present, not for "is hk". Also not checked: `HK=0` (the installed global command is `test "${HK:-1}" = "0" \|\| …`) and `HK_SKIP_HOOKS`, both of which make an installed hook a no-op while the doctor reports it present. No repo config sets either today (grep of `mise.toml`, `conf.d/*.toml`, `.devcontainer/*.toml`, `.claude/settings.json` = 0). | `python/src/dotfiles_setup/hk_hooks.py:76-78` | E3 (arms A5, A6) |
| N5 | MEDIUM | `test_hk_hooks.py` writes `git config --global hook.hk-*` with NO self-guard that `GIT_CONFIG_GLOBAL` points at a scratch file. Its promise "never the developer's `~/.gitconfig`" (module docstring) is enforced only by the autouse fixture in a different file. With the fixture absent (`--noconftest`, which the prior cold review used as its probe method at E2/E3), the run REWROTE the ambient global config: `[hook "hk-pre-commit"] command = hk run pre-commit --from-hook` (and commit-msg, pre-push). On this host the ambient global is `~/.gitconfig`, which now holds the operator's real `hook.hk-*` entries (`test "${HK:-1}" = "0" \|\| ~/.local/bin/mise x hk -- hk run … --staged`). `git config --global <key> <value>` REPLACES those, dropping `mise x`, the `HK` escape and `--staged` machine-wide. The doctor would still report them installed (N3). Fix direction (not applied): `_add_hook` writes via `--file <isolated_git_config path>`, or asserts `GIT_CONFIG_GLOBAL` is under `tmp_path.parent` first. | `tests/test_hk_hooks.py:28-44` | E4 |
| N6 | LOW | Q-CLAIM: the doctor's single remediation ("run `hk install --global --mise` from this checkout") cannot clear one of the three negative states `event_has_hk_hook` reports. A hook disabled at LOCAL scope (`hook.hk-pre-commit.enabled=false`) stays `disabled` after a global rewrite that even sets `enabled=true` globally, so the finding repeats every session with advice that cannot work. The test named `test_a_disabled_global_hook_is_reported_missing` in fact disables at LOCAL scope (no scope flag). | `python/src/dotfiles_setup/doctor.py:1387-1393` | E5 |
| N7 | LOW | `test_the_live_baseline_names_every_hook_hk_pkl_defines` binds only required ⊆ hk.pkl. Its docstring claims "doctor.toml's list tracks the hook events hk.pkl actually declares". Mutant: hk.pkl gains a `["post-checkout"]` git hook while doctor.toml stays unchanged, and the test still reports `1 passed`. The reverse direction (a new hk.pkl git hook nobody is told to install) is unguarded. | `tests/test_hk_hooks.py:168-178` | E6 |
| N8 | LOW | Stale claim NOT covered by the prior F4. `tests/test_workflow_hooks.py:33-34` still says autofix "installs the full toolchain, so hk IS present and the git hooks ARE written", which the postinstall change makes false. That is the same sentence this diff corrected in `workflow_hooks.py:333-335` and `:810-811`. The ADR (`docs/adr/0001-hk-hooks-do-not-run-in-ci.md:7,26`) is also still stale, but that is carried over from the prior F4 and is not NEW. | `tests/test_workflow_hooks.py:34` | `git grep -nE 'hooks ARE written\|hk install --mise' 42a699c8` |
| N9 | LOW | The fixture writes the repo path into git config UNQUOTED (`f"[safe]\n\tdirectory = {_REPO_ROOT}\n"`). A checkout path containing `#` or `;` is truncated at that character (measured: `/w/a#b` → `/w/a`, `/w/a;b` → `/w/a`), so the #1183 entry silently names a different directory. The failure is loud, not silent, because `test_the_fixture_keeps_this_checkout_a_safe_directory` compares the exact string. `git config --file <f> safe.directory <path>` would quote it. | `tests/conftest.py:43-46` | E7 |
| N4 | LOW | `hk_hooks._git` spawns `git` with no `timeout=` on the SessionStart doctor path (up to 6 spawns per session), while the sibling `claude_doctor` bounds its spawn (`timeout=_TIMEOUT_S`, `claude_doctor.py:251`) and doctor's own policy note says per-session spawns are "real latency" kept off SessionStart (`doctor.py:942-944`). Precedent exists (`codex_schema.py:27,215` also unbounded) and the SessionStart hook itself carries `"timeout": 600` (`.claude/settings.json:130`), so the worst case is bounded at 600 s. | `python/src/dotfiles_setup/hk_hooks.py:43` | `grep -nE 'subprocess.run\|timeout='` over the four modules |

## Evidence log

### E1 — backend tally over all four committed lockfiles (HEAD tree == 42a699c8 for these files)

`_TOOL_ENTRY_RE` matched **128/128** `[[tools.*]]` headers (mise.lock 35, shared 22, system 50, runtime 21) — no silent skips; 0 multi-version tools; `platformless_asset_entries` = `[]` on all four (so main is clean, as the comment says).

| backend | with platforms | platformless | in `ASSET_BACKENDS` |
|---|---|---|---|
| aqua | 48 | 0 | yes |
| conda | **21** | 0 | **no** |
| core | **10** | 1 | no |
| github | 12 | 0 | yes |
| npm | 0 | 17 | no |
| packslip | 4 | 0 | yes |
| pipx | 0 | 14 | no |
| pypi | 0 | 1 | no |

Conda entry shape: `.devcontainer/mise-system.lock:2307-2313` (`backend = "conda:bear"` → `[tools."conda:bear"."platforms.linux-arm64"]` `checksum = "sha256:…"`).

### E2 — docstring mechanisms

`lock_shared.py:243-247` ("runs `mise lock <bare>` … as a silent no-op: rc 0, NO entry written … `mise lock hk` -> 0 lines") vs `lock_integrity.py:111-113` ("mise 2026.9.8's `mise lock <bare-name>` wrote the version and nothing else"). `platformless_asset_entries` loops `_TOOL_ENTRY_RE.finditer` (existing entries only), `lock_integrity.py:131-141`.

### E3 — `hk_hooks.event_has_hk_hook` arms (git 2.54.0 Apple Git-157; isolated `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM=1`)

| Arm | `git hook list` | `event_has_hk_hook` |
|---|---|---|
| A0 control: hk shim in `.git/hooks` | rc0 `hook from hookdir` | True |
| A1 relative `core.hooksPath=.githooks` + shim | rc0 `hook from hookdir` | True |
| A2 GLOBAL absolute `core.hooksPath` + shim | rc0 `hook from hookdir` | True |
| A3 linked worktree, shim in common hooks | rc0 `hook from hookdir` | True |
| A4 `hook.hk-pre-commit.event` with NO command | rc128 `fatal: 'hook.hk-pre-commit.command' must be configured…` | raises `HookConfigUnreadableError` (loud — good) |
| **A5** `hk-pre-commit` with `command = true` | rc0 `hk-pre-commit` | **True** |
| **A6** hookdir script `# TODO: hk run pre-commit` / `exit 0` | rc0 `hook from hookdir` | **True** |
| A7 hook named `hk-pre-commit` on `commit-msg`, ask `commit-msg` | rc0 `hk-pre-commit` | False (name convention is load-bearing; fails loud) |

A1-A3 close the `core.hooksPath` / worktree questions: `rev-parse --git-path hooks/<e>` honours `core.hooksPath` and `repo_root / <abs>` stays absolute. No finding there.

Host state (read, not assumed): the operator has since run the global install — `git config --global --get-regexp '^hook\.'` → `hook.hk-{pre-commit,commit-msg,pre-push}` with command `test "${HK:-1}" = "0" || ~/.local/bin/mise x hk -- hk run <e> --from-hook [--staged]`; local `hook.*` rc=1 (the old postinstall entries are gone); `git hook list <e>` → `hk-<e>` for all three.

### E4 — the prior F1 fix, and the global-write escape (pytest, both arms each)

Prior F1 (`safe.directory` stripped by the fixture) is FIXED. The arm: `GIT_TEST_ASSUME_DIFFERENT_OWNER=1 GIT_CONFIG_GLOBAL=<scratch cfg without [safe]>` over `tests/test_bash_budget.py::test_cli_wires_end_to_end`:

| Arm | Result |
|---|---|
| HEAD conftest | `1 passed`, rc=0 |
| `--noconftest` | `1 failed`, rc=1 |

Escape. The ambient global is a scratch copy (`[user]` only). NEVER run against the real `~/.gitconfig`.

| Arm | Result | ambient global afterwards |
|---|---|---|
| `GIT_CONFIG_GLOBAL=$S/ambient.gitconfig pytest tests/test_hk_hooks.py --noconftest` | `1 failed, 9 passed`. The failure is `test_a_foreign_or_non_executable_hookdir_script_does_not_count`: `event_has_hk_hook(...) is False` got True, because an EARLIER test's global write leaked into it. | **gained** `[hook "hk-pre-commit"] event = pre-commit / command = hk run pre-commit --from-hook`, plus the same for `hk-commit-msg` and `hk-pre-push` |
| control, same env, fixture on | `10 passed` | unchanged (`[user]` only) |

The git semantics that make it destructive on a real host: `git config --global <key> <value>` replaces a single-valued key. The live host values were read in E3.

### E5 — local disable vs a global reinstall (git 2.54, isolated config)

Global `hook.hk-pre-commit.{event,command}` plus local `hook.hk-pre-commit.enabled=false` gives `git hook list pre-commit` → `disabled	hk-pre-commit`. After a simulated global reinstall (rewrite `command`, plus `--global enabled true`) → still `disabled	hk-pre-commit`. Local scope is read after global, so no global install can clear it.

### E6 — mutation of the hk.pkl ↔ doctor.toml binding

`git archive 42a699c8 hk.pkl doctor.toml tests python/src` goes into a scratch dir. The mutation inserts `["post-checkout"] { steps { ["x"] { check = "false" } } }` before `["commit-msg"]` (anchor count asserted ==1; the mutant grep shows 1). Then `PYTHONPATH=<scratch>/python/src pytest <scratch>/tests/test_hk_hooks.py::test_the_live_baseline_names_every_hook_hk_pkl_defines` → `1 passed`, rc=0. This harness is valid for pytest because the test reads `Path(__file__).resolve().parent.parent`.

### E7 — unquoted git-config value

`printf '[safe]\n\tdirectory = %s\n' <p>` then `git config --file … --get safe.directory` → `/w/plain dir` → `/w/plain dir` (spaces fine), `/w/a#b` → `/w/a`, `/w/a;b` → `/w/a`. The backslash row is not claimed, because zsh `echo` mangled the display.

### E0 — non-findings checked (so the next round need not re-derive)

- **Global hook in the sibling KB repo.** KB pins `hk = "1.57.0"` (`knowledge-base/mise.toml:46`), and the machine-global command passes `--from-hook --staged`. hk 1.57.0 accepts both: `--staged` is in help, and `--from-hook` is hidden but parses. In an empty dir `hk run pre-commit --from-hook --staged` → rc=0, while a bogus-flag control → rc=2 `unexpected argument`. No finding.
- **Container git.** `.devcontainer/mise-system.lock:3157-3158` has `conda:git` 2.55.0, so `git hook list` exists wherever the doctor runs (host 2.54.0 Apple Git-157, CI 2.55 per the prior review). No finding.
- **Renovate grouping.** Exactly one customManager matches the pkl files (`/(^|/)hk(-common|-image)?\.pkl$/`, depName `jdx/hk`), so adding `hk.pkl`/`hk-common.pkl`/`hk-image.pkl` to rule 0 pulls in only the hk dep. No other rule mentions hk. No finding.
- **The isolation test's claim** "deleting the fixture fails the first one". It holds with no ambient `GIT_CONFIG_GLOBAL` (`--noconftest` → 3 failed). With an ambient one set, test 1 passes without the fixture. No repo path sets one (`grep GIT_CONFIG_GLOBAL mise.toml .github python/src scripts` → 0; `test-hook-isolated` runs `process git-isolated`). Note only.
- **Doctor strictness.** Nothing in `.github/`, `pr.py` or `sync.py` runs `doctor --strict`, so a runner with no hooks is not failed by the new check.
- **Contract binding.** The 2 `hk-hooks` hits in suites.toml are the ADR filename (`suites.toml:2258,2260`). No suite binds `hk_hooks.py`, `check_hk_hooks` or `[hk_hooks]`. Registration is held by `test_every_check_function_is_actually_registered` (`len(CHECKS) == 15`). Note only.

- **Hook env leak into pytest:** measured on git 2.54 — a pre-commit hook receives `GIT_INDEX_FILE=.git/index` + `GIT_PREFIX`, a pre-push hook receives neither and no `GIT_DIR`. hk.pkl runs pytest only in `pre-push` (`hk.pkl:858-874`, `test-hook-isolated`), so the new tests' unscoped `git -C <tmp> config …` cannot land in the real repo. No finding.
- **`lock_target` key matching:** `lock_shared_main` rejects any name not a literal `shared.toml` key (`lock_shared.py` main, `unknown = [tool for tool in tools if tool not in declared]`), so a backend-qualified spelling never reaches `lock_target`. All 21 string pins map to `<key>@<pin>`; the one table pin (`npm:@openai/codex`) stays bare. No finding.

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH.** Every decision→action pair here re-reads its input right before acting. `lock_target` parses `shared.toml` when the argv is built, immediately before `mise lock`. `check_lockfiles` reads the working-tree file before scanning. `event_has_hk_hook` runs `git hook list`, then `rev-parse --git-path`, then reads the script, with no cached state. The doctor verdict is a SessionStart snapshot by design. No findings.
- **Q-SCOPE.** Everything is in scope for #1403 except two items. N8's ADR half is carried from the prior F4. The machine-wide blast radius of the recommended `hk install --global` (every repo on the host now runs `hk run --from-hook`) is a SIBLING concern; it was checked for the KB repo (E0) and is safe there. Ticket recommendation: none needed today. N5 is the only finding with a destructive failure mode.
- **Q-CLAIM.** This diff adds or changes operator-facing strings, each checked against its enforcing line:

| String / clause | Enforcing line | Verdict |
|---|---|---|
| doctor `hk-hooks: no hk git hook for <events>` | `hk_hooks.py:72-78` | holds for "missing". It also fires for "disabled" and for non-executable hookdir states, where the wording "no hk git hook" is loose but true in effect |
| ``run `hk install --global --mise` from this checkout`` | none for the LOCAL-disabled state | **N6** |
| `until then these hooks do not run on commit/push` | `git hook list` semantics | holds |
| `could not read git hook config: <stderr>` | `hk_hooks.py:69-71` | holds (arm A4) |
| `` `doctor.toml` has no [hk_hooks].required `` | `doctor.py` `if not isinstance(required, list) or not required` | holds (test `test_an_empty_baseline_is_loud`) |
| `tool <n>@<v> (<backend>): no platform entries — a locked install has no URL to fetch` | `lock_integrity.py` `platformless_asset_entries` | holds for the listed backends; **N1** for `conda` |
| hk_hooks module docstring "will actually RUN" | none for name-vs-command, `HK=0`, `HK_SKIP_HOOKS` | **N3** |
| test module docstring "never the developer's `~/.gitconfig`" | none in `test_hk_hooks.py` itself | **N5** |
| baseline test docstring "tracks the hook events hk.pkl actually declares" | subset loop only | **N7** |
| do-not.md #9 "present only once `hk install --global --mise` has run" | none. A local install or legacy hookdir script also satisfies the doctor (`hk_hooks.py:76-78`) | narrower than the code; cosmetic, folded here |

## Round classification

OPEN HUNTING round 1 on the squash. It states no domain with a cardinality, so per `.claude/skills/adversarial-review/SKILL.md` it cannot end the loop by any outcome and promotes to one bounded round. A natural enumeration for that round is: the 3 negative states of `event_has_hk_hook` (missing / disabled / non-hk) × the 3 scopes (local / global / hookdir) × the doctor remediation, plus the 8 backends present in the four lockfiles × {platformed, platformless}.

## GitHub repos touched

_None._ No upstream source was fetched. The hk behaviour was measured on the locally installed hk 1.57.0 and 2.3.0 binaries, and git behaviour on git 2.54.0. The sibling `ray-manaloto/knowledge-base` checkout was read locally (`mise.toml:46`, `hk.pkl:1,9`) for Q-SCOPE.
