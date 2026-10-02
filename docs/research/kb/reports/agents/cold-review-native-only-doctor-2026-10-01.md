# Cold review — `87c1fde6` (feat/native-only-doctor-check)

> **Lane:** Opus fallback cold pass for a Claude-authored diff (the codex review
> lens is out until 2026-10-03). Same model family as the author — treat as a
> degraded gate, not the full cross-family one.
>
> **Subject:** exactly one commit, `87c1fde688c8080306acbf5f3d7247991d10b49c`,
> base = `merge-base(87c1fde6, origin/main)` = `846f20064de94e91a6251271be89ad41b3e31b2e`.
> Reviewed by ref only; no intent brief. Memory consulted (`memory: local`).
>
> **Status:** COMPLETE (2026-10-01).

## Diff surface

```
 doctor.toml                             |  19 +++
 python/src/dotfiles_setup/doctor.py     |  22 ++++
 python/src/dotfiles_setup/path_drift.py | 219 ++++++++++++++++++++++++++++++++
 tests/test_doctor.py                    |  41 +++++-
 tests/test_path_drift.py                | 173 +++++++++++++++++++++++++
```

## Findings

| # | Severity | Claim | file:line | Evidence / control arm |
|---|---|---|---|---|
| F1 | **MEDIUM** | The check treats "native" as "not under a mise dir". A host whose only `agy`/`codex`/`claude` is a Homebrew cask, npm-global or bun-global copy gets **zero findings**. That contradicts the FAIL clause "no native `{binary}` on PATH" and the commit's claim to enforce "ONLY from their native installers". | `python/src/dotfiles_setup/path_drift.py:520`, `:526-534` | E2: a homebrew-shaped-only PATH gives 0 failures; the mise-shaped control gives 3. `brew info` lists casks `codex` and `claude-code`; a bogus name returns rc=1. For claude, `install-doctor` (`expected_install_method = native`) partly covers this. codex and agy have no positive native check. |
| F2 | LOW | The FAIL fix advice always names `specs[0]`, whichever install produced the hit. When codex or claude resolves to an npm-backed mise copy, the advice is `mise uninstall --all codex` / `claude`. Those specs map to slugs `codex`/`claude`, but the hit is under `npm-openai-codex`/`npm-anthropic-ai-claude-code`. | `python/src/dotfiles_setup/path_drift.py:518` | `probe_fix.py` used the doctor.toml table and a mise-shaped `installs/<slug>/…` hit first: codex `match=False`, claude `match=False`, agy control `match=True`. Whether `mise uninstall --all codex` would remove the npm install is UNVERIFIED (nothing is installed to dry-run against). |
| F3 | LOW | No test covers WARN output or data-dir discovery: 6 of 19 mutations survive. The worst survivor is M08, where the doctor adapter drops every WARN (later-on-PATH, re-created dir, `mise ls` error) and all 207 tests stay green. | `python/src/dotfiles_setup/doctor.py:1274`; `path_drift.py:451-456`, `:486` | E5 rows M08–M13. Control rows M00 (green) and M01 (red) show the harness is live. |
| F4 | LOW | Two clauses in the operator strings have no enforcing line. (a) "it was re-created" — the code only checks that the directory exists. (b) "the global `auto_install_disable_tools` already blocks auto-install, so a copy that came back was installed explicitly" — nothing reads that setting, and the literal setting does not contain 3 of the 11 doctor.toml specs. | `path_drift.py:546-550`; `path_drift.py:425-428` | E4: `claude`, `aqua:anthropics/claude-code` and `github:openai/codex` each match 0 times; control `aqua:google-antigravity/antigravity-cli` matches 1. Alias normalisation is UNVERIFIED. |
| F5 | LOW | The spec table says it covers "every mise tool spec that … through the registry, could put" a copy on PATH, but it omits `aqua:google-antigravity/antigravity-cli` and `http:claude`. The leftover-dir WARN therefore cannot see those install dirs. The first-hit FAIL is unaffected because it matches on path shape. | `doctor.toml:245-259`; `path_drift.py:400-414` | E3: `mise registry` output (control: `antigravity` is not found). The user's own global `auto_install_disable_tools` already lists the aqua agy spec. That `http:claude` installs to `http-claude` is inferred from `mise_slug`, not run live. |
| F6 | LOW | Nothing enforces "on the Mac host" (docstring and doctor.toml). There is no `host_system()` gate, although the same module gates `check_devcontainers_running` that way. Inside the image, `codex` and `claude` are mise copies, so a direct `dotfiles-setup doctor` there would FAIL both. | `doctor.py:1258-1274` vs `doctor.py:1758`; `.devcontainer/mise-runtime.toml:63`; `.config/mise/conf.d/shared.toml:44` | Static only. The SessionStart path cannot reach it in the container: `MISE_IGNORED_CONFIG_PATHS` drops `mise.toml` (`.devcontainer/devcontainer.json:182`), so no `doctor` task exists there. No live container arm was run (do-not #3). Sibling branch `feat/native-cli-devcontainer` drops those mise copies (Q-SCOPE). |
| F7 | INFO | Nothing in the doctor enforces the FAIL/WARN severity split. The adapter flattens both lists, both render as `DRIFT`, and `--strict` exits 1 on either. | `doctor.py:1274`, `:1869`, `:1894`; claim at `path_drift.py:502` | Code read. |
| F8 | INFO | No `suites.toml` contract binds the native-only chain, unlike its sibling `workflow.path-drift-ambient-capture`, which binds `("path-drift", check_path_drift),`. Registration is held only by the CHECKS count test. | `python/verification/suites.toml:2649` (sibling) | `git grep native_only/native-only` across contract files: 0 hits. M01 is killed by the count test. |

## Verdict

**SHIP.** No HIGH. The incident shape this check was built for is caught:
a mise copy first on PATH (shim, installs dir, a symlink into installs, or an
undeclared data dir). M02/M03/M04/M17 prove every branch of that logic is armed.
BLIND is reported, never passed, both in the live run (E1) and under mutation
(M07/M16). All gates run here are green: ruff, format, ty, `verify` 166/0, and
full pytest **4433 passed, 2 skipped, rc=0** on the scratch worktree at
`87c1fde6`.

Disposition owed before merge, all in this unit of work or as a ticket:

- **F1 (MEDIUM).** Either narrow the "native" clauses to what the code checks
  ("no mise copy resolves first / no non-mise copy"), or ticket a positive
  native-root check. The strings must not keep claiming "native" while a
  Homebrew-only host passes.
- **F2.** Derive the `mise uninstall` spec from the hit's `installs/<slug>` instead of `specs[0]`.
- **F3–F5.** Add an adapter test that asserts a WARN reaches the doctor
  (kills M08). Cover one data-dir source. Delete or narrow the two unenforced
  clauses (F4). Add `aqua:google-antigravity/antigravity-cli` and `http:claude`,
  or drop "every … could put" (F5).
- **F6–F8.** Optional: add a `host_system()` gate, or delete "on the Mac host".

Stop condition: this was one open-hunting round (round 1). By the
adversarial-review skill it cannot end the loop by itself. A follow-up round,
if run, should be BOUNDED to the 19-row mutation table plus the 15-row Q-CLAIM
table above.

## GitHub repos touched

_None._ All evidence came from the local repo, the `mise` CLI and `brew info`.

## Running evidence log (appended as found)

### E1 — live end-to-end arm through the real entry point (PASS + BLIND)

`DOTFILES_AMBIENT_PATH="$PATH" mise -C <worktree> run doctor -- --verbose` →
`PASS  doctor[native-only]`, `rc=0` (this host: `agy` = `~/.local/bin/agy` real
file; `codex` → `~/.codex/packages/standalone/current/bin/codex`; `claude` →
`~/.local/share/claude/versions/2.1.287`). Control arm, same command WITHOUT the
capture → `DRIFT doctor[native-only]: native-only check is BLIND …`, `rc=0`.
The check is the worktree's code (the base has no `native-only` row). The
BLIND branch discriminates.

### E2 — "native" means "not under a mise dir"; any other manager passes

Scratch executables named `agy`/`codex`/`claude` in three shapes, called via
the worktree's `path_drift.check_native_only(environ={}, ambient_path=…, listing={})`:

| Arm | PATH | failures |
|---|---|---|
| CONTROL native first | `~/.local/bin` | 0 |
| CONTROL mise-shaped first | `<S>/fakemise/mise/shims:~/.local/bin` | **3** (one per binary) |
| PROBE homebrew-shaped first | `<S>/fakebrew/bin:~/.local/bin` | **0** |
| PROBE bun-global-shaped first | `<S>/fakebun/.bun/bin:~/.local/bin` | **0** |
| PROBE homebrew-shaped ONLY (no native install at all) | `<S>/fakebrew/bin` | **0** |

The last row has NO vendor-native install anywhere on PATH and reports zero
findings, while the FAIL text at `path_drift.py:533` says the failing condition
is "no native `{binary}` on PATH".

### E3 — registry/backends the spec table omits (leftover-dir WARN coverage)

`mise registry` (control: `antigravity` → "tool not found", `codex` → found):
`agy` → `aqua:google-antigravity/antigravity-cli`; `claude`/`claude-code` →
`aqua:anthropics/claude-code http:claude`; `codex` → `aqua:openai/codex
npm:@openai/codex`. `--hide-aliased` shows `agy` and `claude-code` are aliases
(of `antigravity-cli`, `claude`). So the table omits the explicit specs
`aqua:google-antigravity/antigravity-cli` and `http:claude` (the backend the
image's `claude-code = "latest"` uses, `.devcontainer/mise-runtime.toml:59-63`).
The user's own global `auto_install_disable_tools` already lists
`aqua:google-antigravity/antigravity-cli`.

### E4 — the fix-text clause about `auto_install_disable_tools`

`mise settings get auto_install_disable_tools` (outside the repo) lists 8
specs. Exact-string membership of doctor.toml specs: `claude` 0,
`aqua:anthropics/claude-code` 0, `github:openai/codex` 0; control
`aqua:google-antigravity/antigravity-cli` 1. Nothing in the diff reads this
setting. Whether mise normalises the `claude`/`claude-code` alias for this
setting is UNVERIFIED.

### E5 — mutation table (scratch `git worktree add --detach <S>/wt-nod 87c1fde6`)

Each row: one exact-once replacement (count asserted == 1 before writing),
`pytest tests/test_path_drift.py tests/test_doctor.py`, then `git checkout --`.
Pristine control row is green with a non-zero count, so the harness is live;
M01 (unregister) going red proves the tests import the scratch copy.

| Row | Mutation | Result | Killed by |
|---|---|---|---|
| M00 | pristine control | 207 passed | — |
| M01 | delete `("native-only", check_native_only),` | 1 failed | `test_every_check_function_is_actually_registered` |
| M02 | `_from_mise` drops the `hit.resolve()` arm | 1 failed | symlink test |
| M03 | shape fallback → `False` | 1 failed | undeclared-data-dir test |
| M04 | first-hit FAIL off | 7 failed | 7 tests |
| M05 | leftover-dir loop off | 2 failed | 2 tests |
| M06 | adapter passes `None` (ignores baseline) | 1 failed | `test_native_only_reads_the_baseline_table` |
| M07 | adapter BLIND → `[]` | 1 failed | blindness test |
| **M08** | **adapter `return [*report.failures]` (drops every WARN)** | **207 passed** | **none** |
| **M09** | **`which_all` drops `os.access(X_OK)`** | **207 passed** | **none** |
| **M10** | **drop `/usr/local/share/mise`** | **207 passed** | **none** |
| **M11** | **drop `MISE_DATA_DIR`** | **207 passed** | **none** |
| **M12** | **drop the `mise ls` installs root** | **207 passed** | **none** |
| **M13** | **drop `XDG_DATA_HOME`** | **207 passed** | **none** |
| M14 | later-on-PATH WARN off | 1 failed | later-hit test |
| M15 | silent on `mise ls` error | 1 failed | failed-mise-ls test |
| M16 | BLIND falls through | 1 failed | blind-under-task test |
| M17 | shape matches `shims` only | 3 failed | 3 tests |
| M18 | "no native copy" FAIL off | 2 failed | 2 tests |
| M19 | suffix (not exact) slug match | 2 failed | incl. `npm-oh-my-codex` control |

13 killed / 6 survived. The core FAIL logic is well-armed. Every survivor
is on the WARN surface or the data-dir discovery. M12 matters most: the
`mise ls` installs root is the only reason `check_native_only` spawns a
subprocess (measured 0.11 s, so cost is not a finding), and no test can
tell whether it is used.

### E6 — the three required questions

**Q-FRESH.** The diff has no decision→action pair: the check is read-only and
returns strings. The only temporal seam is inherited from `path-drift`. The
verdict is computed from the PATH captured at SessionStart, while the repo
invokes these CLIs later through `mise exec --` (`ai-cli-invocation.md`).
Measured on this host, ambient and `mise exec` PATH put every mise install dir
(positions 2–182) ahead of `~/.local/bin` (186/185), so the orderings agree.
A mise copy activated mid-session is outside a SessionStart check by
construction. Not a finding.

**Q-SCOPE.** F1 is in scope as a claim: either narrow the "native" clauses in
this diff, or ticket a positive native-root check (claude
`~/.local/share/claude/versions/`, codex `~/.codex/packages/standalone/`, agy
`~/.local/bin/agy` regular file). F6 is a sibling of
`feat/native-cli-devcontainer`; that branch removes the image's mise copies and
shares no file with this diff (`comm -12` of both name lists is empty).
F2–F5 are in scope and cheap.

**Q-CLAIM.** Every operator-facing clause added:

| Clause | Enforcing line | Outcome |
|---|---|---|
| "`{binary}` resolves to mise's copy {hit} first" | `path_drift.py:521` | enforced (M04 kills 7 tests). For a SHIM, "copy" overclaims, because a shim with no active version falls through. UNVERIFIED, no live shim arm. |
| "it must come only from its native installer" | none beyond "not mise" | **F1** |
| "no native `{binary}` on PATH (…)" | `path_drift.py:520,526` = not-mise | **F1** |
| "Reinstall it with the vendor's native installer" | advice | fine |
| "resolves natively, but mise's copy is also on PATH … one PATH reorder from winning" | `path_drift.py:536-543` | enforced (M14). "natively" = **F1** |
| "mise install directory {leftover} exists" | `path_drift.py:547` | enforced (M05) |
| "— it was re-created" | none | **F4a** |
| "Fix: `mise uninstall --all {spec} && mise reshim`" | `path_drift.py:518` uses `specs[0]` | **F2** |
| "The usual trigger is a stale pin in an old worktree's mise config" | none (inherited narrative) | narrow or cite; folded into F4 |
| "the global `auto_install_disable_tools` already blocks auto-install …" | none | **F4b** |
| "could not ask mise for its installs root (…); only the default mise data directories were checked" | `path_drift.py:449-456` | enforced (M15). The data-dir sources themselves are untested (F3). |
| BLIND advice "This is NOT a pass. Capture it: …" | `resolve_ambient_path` + `doctor.py:1272-1273` | enforced (M07, M16; live E1) |
| docstring/toml "on the Mac host" | none | **F6** |
| "failures break the ruling, warnings foreshadow it" | none in doctor | **F7** |
| `path_drift.py:398-399` "`native_clis_container`, on a sibling branch" | — | TRUE: present on `refs/heads/feat/native-cli-devcontainer` (`tests/test_native_clis_container.py`) |

### E7 — gates run against the reviewed ref (scratch worktree)

- `ruff check` (4 changed .py files) → `All checks passed!` rc=0; `ruff format --check` → 4 already formatted, rc=0
- `ty check` (2 source files) → `All checks passed!` rc=0
- `dotfiles-setup verify run` from the scratch worktree (valid per a 2026-10-01 control arm) → `166 passed, 0 failed, 4 skipped` rc=0
- `pytest tests/test_path_drift.py tests/test_doctor.py` → 207 passed
- `mise run lint` / `lint-docs` NOT run by this reviewer.
