# Spec: migrate dotfiles hk 1.57.0 → 2.3.0 and editorconfig-checker 3.11.3 → 4.x

Status: LANDED 2026-09-27 as #1403 (squash `42a699c8`; land rc=0 incl. verify-local). Line anchors below are against the pre-change tree `8bffc0ef`. The landed diff also carries review fixes outside §2 (hk-hooks doctor check, lock_integrity platform-less check, lock_shared `tool@version`, curl/libsqlite3-dev apt pins). The operator step in §4 (global reinstall from this checkout) was done 2026-09-27 (#1397 status comment). Ratification: RATIFIED 2026-09-27 by Ray (AskUserQuestion: "upgrade to the latest hk and follow their v2 migration guide"; "Move to ec 4.x now"; rev 2: "Adopt upstream golden path" for hook installation, after `docs/research/kb/reports/agents/hk-v2-global-hooks-wrong-or-adapt-2026-09-27.md` showed the global install is upstream's recommended v2 setup). Evidence base: `docs/research/kb/reports/agents/hk-v2-migration-research-2026-09-27.md` (Q1–Q8). User-level `~/.gitconfig` global hooks are OUT OF SCOPE (tracked in #1397); this spec must not touch any file outside the repo.

## 1. Objective

Every hk site in dotfiles runs hk **2.3.0** with a v2-correct config, and editorconfig-checker runs at **4.x** under hk's v2 builtin default, with every gate green. Prevents: the permanently-red Renovate split (#1090 bumps the pkl package while `shared.toml` stays 1.57.0 → `pin_parity` drift + `editorconfig-checker` ENOENT), a stale 1.x binary silently evaluating the v2 package (`min_hk_version = "1.49.0"`), our stale `postinstall = "hk install --mise"` recipe (removed upstream in jdx/hk#1376 because it mutates `.git/config` during mise installs and races — discussion #1375), and pytest throwaway repos reading the user's GLOBAL git config/hooks.

## 2. Files

Modify only these (the allowlist):

- `.config/mise/conf.d/shared.toml` — `hk = "1.57.0"` → `"2.3.0"` (line 37).
- `hk.pkl` — lines 1, 8, 11: `v1.57.0/hk@1.57.0` → `v2.3.0/hk@2.3.0`; line 19 `min_hk_version = "1.49.0"` → `"2.3.0"`; line 42 editorconfig step stays `Builtins.editorconfig_checker` (v2 default `version = "4"`); refresh any comment that names hk 1.57 behaviour only where it is now false (e.g. line 339 cites `hk 1.57 hook.rs`: re-verify against 2.3.0 or mark the version it was measured on).
- `hk-common.pkl` — lines 8 (comment), 17, 18: same URL bump.
- `hk-image.pkl` — lines 11, 14: same URL bump; line 19 `min_hk_version` → `"2.3.0"`.
- `mise.toml` — line 15: `editorconfig-checker = "3.11.3"` → the latest 4.x (4.0.2 at research time; confirm with `mise ls-remote editorconfig-checker`), and fix the trailing comment (the binary is no longer only `ec`). Line 180 postinstall: drop the hook install — `"mise reshim && hk install --mise"` → `"mise reshim"` — and replace the comment above it with one line citing jdx/hk#1376/#1375 and naming the setup `hk install --global --mise` (run once per machine from this checkout so the event set includes pre-push; an operator step, NOT done by this change).
- `mise.lock` — the `[[tools.editorconfig-checker]]` block (line 6470) regenerated for 4.x.
- `.config/mise/mise.lock` — `[[tools.hk]]` (line 412) regenerated for 2.3.0.
- `.devcontainer/mise-system.lock` — regenerated via `mise run lock-image` (hk is in the shared fragment the image merges; `mise-runtime.lock` has no hk entry, so it changes only if `lock-image` rewrites it).
- `docs/hk-builtins-audit.md` — GENERATED from `hk --version` + `hk builtins` (`hk_builtins_audit.py:109-125`); regenerate with `mise run hk-audit` after the bump. It is checked by the `hk_audit` step (`hk.pkl:372-374`), `tests/test_hk_builtins_audit.py:15` and suites `workflow.hk-builtins-audit` (`suites.toml:2183-2215`). New builtin names may trip typos — if so add a narrowly-scoped entry to `typos.toml` following the `sherif` precedent (`typos.toml:41-46`), and list it in the report.
- `tests/test_workflow_claude_code.py` — `_EXPECTED_FLAG_TABLES` (`:90-116`) must equal `HK_RUN_FLAGS`/`HK_GLOBAL_FLAGS` exactly (asserted at `:306-314`); update it in lockstep with every flag you add.
- Stale `hk install --mise` postinstall PROSE (none is asserted by a test/contract): `hk.pkl:404-408`, `python/src/dotfiles_setup/workflow_hooks.py:1-6`, `.github/workflows/refresh.yml:77,289`, `.github/workflows/gcc-sha-repair.yml:47`. Reword each to the new truth: the repo no longer installs hooks from `postinstall` (upstream jdx/hk#1376), so a runner gets hk hooks only if something else installs them; KEEP the `workflow_hk_skip_hooks` gate and `HK_SKIP_HOOKS` usage unchanged as defense-in-depth (ADR-0001 stands; do not edit `docs/adr/0001-*.md` beyond an optional one-line dated note).
- `tests/test_image_smoke.py` — line 814 `"1.57.0"` → `"2.3.0"`.
- `python/src/dotfiles_setup/workflow_claude_code.py` — `HK_RUN_FLAGS` (from line 108): add `Flag(("--junit-xml",), takes_value=True)`; add the hidden value-taking GLOBAL flag `--hkrc <PATH>` (2.3.0 usage spec `~/.local/share/mise/installs/hk/2.3.0/.mise-packslip/assets/hk.usage.kdl:109`) to `HK_GLOBAL_FLAGS`; update the "Transcribed from hk 1.57.0" comments (lines 86, 104) to 2.3.0 after re-transcribing from `hk --help` / `hk run --help` at 2.3.0 (add any other new value-taking flag you find; list them in your report).
- `tests/conftest.py` — add an autouse fixture (next to `isolated_mise_state`, same style) that points `GIT_CONFIG_GLOBAL` at a per-test file under the pytest tmp tree containing only `[user] name = T` / `email = t@example.com`, and sets `GIT_CONFIG_NOSYSTEM=1`, via `monkeypatch.setenv`. Git's documented mechanism (`git help git`: GIT_CONFIG_GLOBAL "… will not be read"); precedent `tests/test_safe_directory.py:58-66`. Tests that pass an explicit `env=` built from `os.environ` inherit it; tests that deliberately build their own global config (test_safe_directory) keep overriding it. Add one test proving isolation, and never touch the real `~/.gitconfig`: write a SECOND config file with a `hook.probe-pre-commit.command = exit 1` / `event = pre-commit` entry. Show that a throwaway-repo commit FAILS when `GIT_CONFIG_GLOBAL` points at that file (the control arm) and PASSES under the fixture's default.
- `tests/` for `workflow_claude_code` — add one test proving `hk run --junit-xml out.xml pre-commit` still resolves the hook as `pre-commit` (and the control: without the flag entry it would misparse — show it fails with the entry removed).
- `AGENTS.md` lines 151-154 — the fmt rule. Replace the "Always `git add` BEFORE `mise run fmt`" rationale: under hk 2 `hk fix` no longer stages (contextual staging, v2.0.0 #1256), so fixes are left UNSTAGED and must be `git add`-ed AFTER `mise run fmt`. Keep AGENTS.md under agnix's 12,000-char ceiling (it is 11,605 now — net growth ≤ 300 chars).
- `renovate.json` — add `hk.pkl`, `hk-common.pkl`, `hk-image.pkl` to the `"image-build inputs"` rule's `matchFileNames` (lines 20-27), and extend that rule's `description` with one sentence: the hk package URL in the pkl files and the hk pin in shared.toml must move in ONE PR (#1090 could never pass alone).
- `docs/research/kb/reports/agents/hk-v2-migration-research-2026-09-27.md` — already written; commit it unchanged.

## 3. Interfaces

- `pin_parity` must keep passing: `mise run pin-parity` reads the pkl URL tokens and `shared.toml`; after the change all hk sites must say 2.3.0.
- `Flag` in `workflow_claude_code.py` (`:78-83`) has fields `spellings: tuple[str, ...]`, `takes_value: bool`, `optional_value: bool`; construct new entries positionally exactly like the existing ones.
- The hk builtin `editorconfig_checker` at v2.3.0: default `version = "4"` → check argv `editorconfig-checker {{files}}`, fix argv `editorconfig-checker --fix {{files}}` (effect write). Our `fix` and `pre-commit` hooks have `fix = true`, so ec 4 WILL rewrite files there — accepted by Ray's "ec 4.x now" ruling.

## 4. Constraints and invariants

- **Environment:** this session inherited a stale `HK_PKL_BACKEND=pkl`; hk 2 refuses to start with it. Run EVERY command with it unset (`unset HK_PKL_BACKEND` first in each shell, or `env -u HK_PKL_BACKEND …`). Do NOT add it anywhere.
- Do not touch `~/.gitconfig`, `~/.config/mise/config.toml` or anything outside the repo. Do not run `hk install --global` or `hk uninstall --global`.
- Locks: use the repo tasks, never a bare whole-file `mise lock` (destructive — memory `feedback_mise_lock_whole_file_is_destructive`). Before a scoped re-lock, DELETE the tool's `[[tools.X]]` block first (`mise run lock` reuses the locked version otherwise). Host: `mise run lock -- "editorconfig-checker"` — the wrapper validates the mise.toml CONFIG KEY, not the lockfile backend string (rev 3: the lane's licensed dissent showed `"aqua:editorconfig-checker/editorconfig-checker"` fails rc=1 "not declared in the host config"). Shared: `mise run lock-shared -- "hk"` (routes into the devcontainer; needs it running — `mise run up` if not). Image: `mise run lock-image`. If a lock task cannot run (e.g. no container), STOP and report — do not hand-edit lock checksums.
- Never `mise run build` or build the base image locally (`do-not.md` #2).
- No inline suppressions (`noqa`, `type: ignore`, …). No new bash logic (`zero-bash-logic.md`).
- Gates: `mise run lint` (never raw `hk`), never pipe a gate into `tail`/`head`; capture `rc` to a file. Do NOT use `timeout` (broken mise shim here).
- If ec 4.x rewrites any tracked file under `mise run fmt`, keep the rewrite only if it is a pure whitespace/EOL fix and list every such file in the report; otherwise STOP and report.
- Dissent is licensed: if the code contradicts this spec (a line moved, a flag differs at 2.3.0, a lock task refuses), stop and report the contradiction instead of guessing.

## 5. Verification (run all, report each rc from a file)

1. `mise install` (host) then `hk --version` → `hk 2.3.0` and `mise which editorconfig-checker` resolves a 4.x binary named `editorconfig-checker`.
2. `mise run pin-parity` → rc 0.
3. `hk validate` → rc 0 (unset HK_PKL_BACKEND).
4. `mise run lint` → rc 0.
5. `mise run fmt` on a clean tree → rc 0, and `git status --short` shows no unexpected rewrites (report any).
5b. Staging behaviour (P15): in a scratch copy of the repo (NOT the working tree), introduce a trailing-whitespace defect in one tracked file, `git add` it, run `mise run fmt`, then report `git diff --cached --stat` and `git diff --stat`. Record which one holds the fix; the AGENTS.md rewrite must state the OBSERVED behaviour, not the assumed one.
6. `uv run --project python pytest tests/ -x -q` → rc 0, failure count 0.
7. `mise run verify` → `N passed, 0 failed`.
8. `mise run pin-actions` and `mise run lint-docs` → rc 0.
9. `hk test` (hk's own step tests, if any are declared) → rc 0 or report "no tests declared".
10. Control arm for the pin: temporarily revert `shared.toml` to 1.57.0 → `mise run pin-parity` FAILS; restore → passes.
11. `grep -n 'hk install' mise.toml` → no postinstall hook install remains (only prose/comment). Do NOT run `hk install`/`hk uninstall` in any scope — the global reinstall is an operator step after merge.
12. The conftest isolation test from §2 passes, and its control arm (failing hook config) fails as asserted.

## 6. Commit

`caller` — leave all changes uncommitted on branch `chore/hk-v2.3-migration`; the architect commits, cold-reviews and ships.

## 7. PREMISES

Rev 2 corrections from the premise check (`docs/research/kb/reports/agents/premise-verifier-hk-v2-migration-2026-09-27.md`): P13/P15 provenance is the research report (a secondary source) — P13 is settled by verification steps 1+4, P15 by new step 5b; P14 is now cited to the installed 2.3.0 usage spec.


| # | Kind | Claim | Source (read this session) |
|---|---|---|---|
| P1 | L | `hk = "1.57.0"` | `.config/mise/conf.d/shared.toml:37` |
| P2 | L | pkl URLs pin `v1.57.0/hk@1.57.0` | `hk.pkl:1,8,11`; `hk-common.pkl:8,17,18`; `hk-image.pkl:11,14` |
| P3 | L | `min_hk_version = "1.49.0"` | `hk.pkl:19`; `hk-image.pkl:19` |
| P4 | L | `["editorconfig-checker"] = Builtins.editorconfig_checker` | `hk.pkl:42` |
| P5 | L | `editorconfig-checker = "3.11.3" # provides \`ec\`` | `mise.toml:15` |
| P6 | L | `postinstall = "mise reshim && hk install --mise"` | `mise.toml:180` |
| P6b | E | upstream removed the postinstall recipe; global install is the golden path | https://github.com/jdx/hk/pull/1376, discussion #1375, `docs/cli/install.md@v2.3.0` |
| P6c | P | a test already isolates `GIT_CONFIG_GLOBAL` | `tests/test_safe_directory.py:58-66` |
| P6d | L | `tests/conftest.py:25-26` autouse `isolated_mise_state(tmp_path, monkeypatch)` | `tests/conftest.py:25` |
| P7 | L | `assert declared["hk"] == "1.57.0"` | `tests/test_image_smoke.py:814` |
| P8 | I | `HK_RUN_FLAGS = (Flag(("-e","--exclude"), takes_value=True), …)` transcribed from hk 1.57.0 | `python/src/dotfiles_setup/workflow_claude_code.py:104-112` |
| P9 | L | image-build inputs group `matchFileNames` lacks the pkl files | `renovate.json:20-27` |
| P10 | L | fmt rule "Always `git add` BEFORE `mise run fmt`" | `AGENTS.md:152-154` |
| P11 | L | lock anchors `[[tools.hk]]` | `.config/mise/mise.lock:412`, `.devcontainer/mise-system.lock:5050` |
| P12 | L | `[[tools.editorconfig-checker]]` backend `aqua:editorconfig-checker/editorconfig-checker` | `mise.lock:6470,6472` |
| P13 | E | v2 builtin `editorconfig_checker` default version 4 → argv `editorconfig-checker {{files}}`, plus a write-effect fix command since v2.1.0 | research report Q1 (jdx/hk `pkl/builtins/editorconfig_checker.pkl@v2.3.0`) |
| P14 | E | v2 per-repo `hk install` deletes local hk hooks when any global `hook.hk-*` exists unless `--force-local` — deliberate ("single source of truth") | `docs/cli/install.md@v2.3.0`; research report Q3 |
| P15 | E | `hk fix` no longer stages under v2 (contextual staging) | research report Q1 (v2.0.0 #1256) |
| P8b | L | `_EXPECTED_FLAG_TABLES` pins the flag tables exactly | `tests/test_workflow_claude_code.py:90-116,306-314` |
| P8c | L | `docs/hk-builtins-audit.md:9` records `hk 1.57.0`, generated by `mise run hk-audit` | `hk_builtins_audit.py:109-125`, `mise.toml:1340-1342` |
| P16 | E | ec 4.x ships a binary named `editorconfig-checker` via the aqua backend | verified: step 1 (hk-v2 implementer reports; `mise which editorconfig-checker` resolved 4.0.2) |
| P17 | L | `mise ls-remote editorconfig-checker` tail = 4.0.0, 4.0.1, 4.0.2 | measured 2026-09-27 |
