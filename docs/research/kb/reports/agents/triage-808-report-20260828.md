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

## 5. `test_shell_integration.py` — MIXED, and fully separable

20 collected, 9 fail, **11 pass**. The split is **by PARAMETER** for the two
login-shell tests and **by TEST FUNCTION** for `test_zshenv_path_injection`.

Parametrize lists: `:19` `_SHELL_RC_TEMPLATES`; `:139-141` reachable (7 params);
`:159` execution (6 params).

| Group | Def | Params | Verdict |
|---|---|---|---|
| `test_gpg_guard_no_clobber_when_gpgconf_absent` | `:95` | ×2 templates | **PASS** — hermetic `PATH` at `:82`, needs only `bash`+`grep` |
| `test_gpg_guard_no_clobber_when_ssh_support_disabled` | `:108` | ×2 | **PASS** |
| `test_gpg_guard_overrides_when_ssh_support_enabled` | `:125` | ×2 | **PASS** |
| `test_tool_reachable_in_login_shell` | `:142` | `mise`, `chezmoi`, `uv` | **PASS** |
| " | " | `pixi` | FAIL — **TOOLCHAIN** (`shared.toml:35`) |
| " | " | `codex` | FAIL — **TOOLCHAIN** (`mise.toml:87`, no `os =` gate; `aqua:openai/codex` ships linux assets) |
| " | " | `claude` | FAIL — **HOST-ONLY**, absent from every mise config |
| " | " | `gemini` | FAIL — **HOST-ONLY on a runner** (see correction below) |
| `test_tool_execution_in_login_shell` | `:160` | `chezmoi`, `uv` | **PASS** |
| " | " | `pixi`, `codex`, `claude`, `gemini` | FAIL, same buckets |
| `test_zshenv_path_injection` | `:173` | — | FAIL — **HOST-ONLY**. Needs the `zsh` binary *and* a chezmoi-applied `~/.zshenv` (asserts `.local/bin` + `mise/shims` in a non-interactive zsh `$PATH`, `:180-181`). **Installing zsh does NOT make it pass.** |

> ⭐ **Correction to the architect's own brief, verified independently.** The brief
> asserted `gemini` is "NOT in any mise config". It **is** — at
> `.devcontainer/mise-runtime.toml:63` (`npm:@google/gemini-cli`). But that is an
> **image-only** config: a repo-root `mise install` merges only
> `.config/mise/conf.d/*.toml`, which contains just `shared.toml`. Confirmed by
> listing that directory. Same practical outcome, different reason — and the
> reason matters, because someone could otherwise "fix" it by expecting the
> widened install to supply it. The brief's grep checked `mise.toml` and
> `shared.toml` only; it never looked at the image configs.

**Parameter ids to mark HOST-ONLY:** `claude`, `gemini` on both login-shell
tests, plus the standalone `test_zshenv_path_injection`. `pixi` and `codex`
should need no marker once the install is widened. A module marker here discards
11 passing tests, **including all 6 issue-#87 gpg-guard regressions**.

## 6. `test_skillopt_provenance.py` — GIT-DEPTH, one test

`test_manifest_is_stable_and_all_live_objects_bind` (`:60`) →
`subject.verify_live(_fetch())` at `:64`. The injected `_fetch` runs
`git show f"{fix.commit}:{fix.path}"` with `check=True` (`:38-42`) against the
commits pinned in `FIXES` (`python/src/dotfiles_setup/skillopt_provenance.py:66+`).
A shallow checkout lacks those objects → `CalledProcessError`.

Control arm confirming the bucket: `export()` (`skillopt_provenance.py:157`) and
`verify_local()` (`:358`) are git-free — the only other git call is `git archive`
in `replay()` (`:278`), which no test invokes. That is why the file's other ~16
tests pass. **Single-test marker**, or none once the checkout is deepened.

## 4b. The bare `assert 2 == 1` count — BOTH earlier figures were wrong

The architect reported **6**; the agent's tail said **3**. Control-armed count by
the architect: **4**.

`grep -c 'assert 2 == 1'` on the CI log returns **8**. The control arm:
`grep -c 'chezmoi is not installed or not in PATH'` returns **2** for what is
indisputably ONE test — so **pytest prints every failure twice** (traceback plus
short summary). 8 ÷ 2 = **4 distinct tests**, all `test_session_review`, all the
shallow-checkout cause. The authoritative line is `FAILED tests/`, which appears
exactly **23** times, matching the reported total.

Lesson worth more than the number: a raw `grep -c` over a pytest log is a
**display-bounded** probe. Neither original figure was measured against a
known-single-failure control.

<details>
<summary>Superseded truncation notice (kept for provenance)</summary>

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

</details>

## Consequences for #808's design

1. **Per-test / per-parameter marks only.** No module-level markers anywhere.
2. **`fetch-depth: 0` fixes 7 tests across three files** (5 + 1 + 1), not the 2
   originally estimated.
3. **Widening `install_args` fixes 7 more** (2 bootstrap + 5 hk-audit), and may
   additionally reclaim the `codex` / `pixi` login-shell parameters.
4. **The genuinely host-only residue is exactly 5 test instances**: `[claude]`
   and `[gemini]` on each of the two login-shell tests, plus
   `test_zshenv_path_injection`. Against the "23 tests" #808 implies, that is a
   4.6x overstatement — and `test_zshenv_path_injection` is the only one that
   installing a tool could never fix.

> **Citation note (architect, verified line-by-line):** the agent's `file:line`
> anchors were consistently **off by one** — it appears to have counted the
> decorator or docstring line rather than the `def`. Every one was re-read and
> corrected above. The SUBSTANCE was correct in every case, including the
> `auto_install` control arm: `auto_install = true` really is set
> (`mise.toml:92`), and `test_chezmoi_version` really is absent from the CI
> failure list. Spot-check citations before acting on any agent report — an
> off-by-one sends the next reader spelunking.
>
> **The TAIL delivery was different**: asked explicitly for `file:line`, the
> agent returned `:95`, `:108`, `:125`, `:142`, `:160`, `:173`, `:19`,
> `:139-141`, `:159` and `:38-42` — every one exact on re-read. Only the
> skillopt def drifted (`:59` → `:60`). Asking for the anchor explicitly
> appears to be what produced accurate ones.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo triaged.
