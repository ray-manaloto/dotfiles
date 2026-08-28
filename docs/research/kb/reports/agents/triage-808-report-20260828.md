# Triage — #808, which of the 23 CI-failing tests can actually run on a runner

Agent: `triage-808` (read-only `Explore`). Brief persisted separately at
`triage-808-brief-20260828.md`. Evidence base: real CI run `33208281690` on PR
#807, where a `pytest tests/` step was added to `contract-preflight` (a job that
installs only `python` + `uv`, with a default shallow checkout) and 23 tests
failed.

> ⚠️ **This report overturns #808's own framing.** The issue says the failures are
> mostly structural host-hostility. They are mostly a **subset install** plus a
> **shallow checkout**.

## Verdicts

| File | Bucket | Collected | Fail on runner | Pass on runner |
|---|---|---|---|---|
| `tests/test_bootstrap.py` | **TOOLCHAIN** | 9 | 2 | **7** |
| `tests/test_hk_builtins_audit.py` | **TOOLCHAIN** | 7 | 5 | **2** |
| `tests/test_lint_delta.py` | **GIT-DEPTH** | ~23 | 1 | rest |
| `tests/test_session_review.py` | **GIT-DEPTH** | ~52 | 5 | rest |
| `tests/test_shell_integration.py` | **MIXED** (TOOLCHAIN + HOST-ONLY) | 20 | 9 | **11** |
| `tests/test_skillopt_provenance.py` | **GIT-DEPTH** | ~17 | 1 | rest |

## 🚨 The load-bearing conclusion

> **No file may take a module-level marker.** Every one of the six has passing
> tests on a runner; the two worst are `test_shell_integration.py` (11 of 20
> pass) and `test_bootstrap.py` (7 of 9 pass).

`test_hk_builtins_audit.py` is the sharpest case: a module-level marker would
discard its **two control arms** (below).

## 1. `test_bootstrap.py` — TOOLCHAIN

`tests/test_bootstrap.py:10` — `@pytest.mark.parametrize("tool", ["mise",
"chezmoi", "uv", "pixi"])` → `shutil.which(tool)`.

- **Fails:** `[chezmoi]`, `[pixi]`. Both declared in
  `.config/mise/conf.d/shared.toml:27` and `:35` — a full `mise install` fixes both.
- **Passes:** `[mise]`, `[uv]`, plus all 5 unparametrized tests.
- ⭐ **Control arm found by the agent, not asked for:** `test_chezmoi_version`
  (`:33`) **passes despite chezmoi being absent**, because it shells out via
  `mise exec chezmoi -- …` and `mise.toml:92` sets `auto_install = true`, so mise
  installs it on demand. That proves the two failures are purely "not on PATH",
  not "unobtainable".

**Marker scope: parameter-level only** (`chezmoi`, `pixi`) — and arguably none at
all once the install is widened.

## 2. `test_hk_builtins_audit.py` — TOOLCHAIN

The 5 failures all route through `audit.available_builtins()` /
`hk_builtins_audit_main()`, which exec `hk`:

- `:13` `test_the_committed_doc_matches_the_generator`
- `:18` `test_not_adopted_names_are_real_builtins_and_none_are_wired`
- `:37` `test_wired_builtins_finds_the_scanners_and_names_their_config`
- `:45` `test_a_custom_step_is_not_reported_as_a_wired_builtin`
- `:60` `test_check_mode_fails_on_a_modified_doc`

`hk` is `.config/mise/conf.d/shared.toml:31` → `mise install` fixes it.

Not parametrized, but **2 tests pass**: `:25`
`test_stale_entries_fires_on_a_name_that_is_not_a_builtin` and `:32`
`test_stale_entries_fires_when_a_declined_builtin_is_wired` are pure-Python (they
pass literal name lists into `stale_entries`). **A module marker discards both —
and they are the file's two control arms.**

## 3. `test_lint_delta.py` — GIT-DEPTH (1 test)

`tests/test_lint_delta.py:161` → `lint_delta.previous_lock_revision(REPO_ROOT)`,
which is `git log -2 --format=%H -- <lockfile>`
(`python/src/dotfiles_setup/lint_delta.py:195-202`) returning
`revisions[1] if len(revisions) > 1 else None`. A depth-1 checkout yields at most
one commit → `None` → `assert revision` at `:162` fails. **`fetch-depth: 0` fixes
it.** Every other test in the file injects its subprocesses or reads files.
**Single-test marker** (or none, with the deeper checkout).

## 4. `test_session_review.py` — GIT-DEPTH (5 tests) — ⭐ this solves the 6 unattributed `assert 2 == 1`

Root cause is one line: `python/src/dotfiles_setup/session_review.py:528` returns
`"cannot resolve the fixed origin/main goal-history baseline"` when
`_authorized_goal_history_base()` (`:479-481`, `git merge-base HEAD origin/main`)
cannot resolve. `_review_preflight_error` (`:686`/`:690`) wraps it as
`invalid goal history: …` and the CLI exits **2**.

All five spawn the real CLI with `cwd=REPO_ROOT`, so preflight runs against the
shallow checkout:

| Test | Line | Symptom |
|---|---|---|
| `test_real_cli_runs_requirements_only` | `:1070`, assert `:1105` | `assert 2 == 1` |
| `test_default_cli_includes_automation_and_dual_provider_requirements` | `:1112`, assert `:1158` | `assert 2 == 1` + stderr msg |
| `test_requirements_cli_cannot_certify_active_session_from_recency` | `:1171`, assert `:1203` | `assert 2 == 1` |
| `test_requirements_cli_requires_an_explicit_source_root` | `:1243`, assert `:1259` | rc 2 matches, then `assert 'requires --source-repo-root' in '…invalid goal history…'` |
| `test_requirements_cli_fails_closed_when_recorded_cwd_does_not_match` | `:1264` | _(tail truncated — see below)_ |

**So the 6 bare `assert 2 == 1` failures are all this file, all one cause.**
`fetch-depth: 0` fixes them.

## 5–6. `test_shell_integration.py` (MIXED) and `test_skillopt_provenance.py`

⚠️ **TRUNCATED.** The agent's delivery was cut off mid-table; a follow-up was
sent requesting the tail and the session cleared before it arrived. What is
known from the verdict table above:

- `test_shell_integration.py` — **MIXED**, 20 collected, 9 fail, **11 pass**.
  Failures are `test_tool_execution_in_login_shell[claude|codex|gemini|pixi]`,
  `test_tool_reachable_in_login_shell[claude|codex|gemini|pixi]`, and
  `test_zshenv_path_injection`; causes are missing `zsh` (not in any mise config)
  and the host-only `claude` / `gemini` CLIs. `codex` and `pixi` ARE mise-managed,
  so **those parameters may move to TOOLCHAIN once the install is widened** —
  which would shrink the host-only set to the `claude` / `gemini` parameters plus
  whatever genuinely needs a login shell. **Re-derive this before marking.**
- `test_skillopt_provenance.py` — **GIT-DEPTH**, 1 test
  (`test_manifest_is_stable_and_all_live_objects_bind`). Mechanism unconfirmed.

**Next session: re-run the brief for sections 5–6 rather than guessing.** The
specific open question is whether `test_zshenv_path_injection` is separable from
the login-shell parametrized cases, and which exact parameter ids need marking
after the install is widened.

## Consequences for #808's design

1. **Per-test / per-parameter marks only.** No module-level markers anywhere.
2. **`fetch-depth: 0` fixes 7 tests across three files** (5 + 1 + 1), not the 2
   originally estimated.
3. **Widening `install_args` fixes 7 more** (2 bootstrap + 5 hk-audit), and may
   additionally reclaim the `codex` / `pixi` login-shell parameters.
4. That leaves a genuinely host-only residue of roughly **4–5 tests**
   (`claude` / `gemini` login-shell parameters, `test_zshenv_path_injection`) —
   an order of magnitude smaller than the "23 tests" the issue implies.

> **Citation note (architect, verified line-by-line):** the agent's `file:line`
> anchors were consistently **off by one** — it appears to have counted the
> decorator or docstring line rather than the `def`. Every one was re-read and
> corrected above. The SUBSTANCE was correct in every case, including the
> `auto_install` control arm: `auto_install = true` really is set
> (`mise.toml:92`), and `test_chezmoi_version` really is absent from the CI
> failure list. Spot-check citations before acting on any agent report — an
> off-by-one sends the next reader spelunking.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo triaged.
