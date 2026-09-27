# hk 1.57.0 -> v2.3.0 migration research (2026-09-27)

Read-only research lane. No hk 2.x binary was installed into the repo toolchain,
no pin was changed. Builds on (does not replace) the prior report
`docs/research/kb/reports/agents/hk-2-0-impact-2026-09-23.md` (#1306), which
covered 1.57.0 -> 2.0.1. This report re-verifies its load-bearing claims and
extends to v2.1.0, v2.2.0, v2.3.0, the global-hooks question, and the current
state of Renovate PR #1090.

Status: COMPLETE (2026-09-27).

## Q1. Breaking / behaviour changes 1.57.0 -> 2.3.0, and which bite us

Releases in range (`gh release list -R jdx/hk`, rc=0): v1.58.0 (backfilled, no
assets), v1.58.1 (docs-only), v2.0.0 (2026-09-13), v2.0.1 (2026-09-15), v2.1.0
(2026-09-23), v2.2.0 (2026-09-25), v2.3.0 (2026-09-26, Latest). Raw notes saved
to `.agent/kb/raw/hk-v2-releases/<tag>.md`.

### Hard breaks (v2.0.0, https://github.com/jdx/hk/releases/tag/v2.0.0)

| Change | Do we use it? | Evidence |
|---|---|---|
| `HK_PKL_BACKEND=pkl` rejected (#1257); `pklr` accepted as no-op | Repo: NO (prose only, see Q2). User-global `~/.config/mise/config.toml`: see Q2 | v2.0.0 notes "Deprecated v1 interfaces removed" table |
| `hk.toml/yaml/json`, `.hkrc.pkl`, `~/.hkrc.pkl`, `--hkrc`, `UserConfig.pkl`, `Types.Regex`/`Config.Regex`, `hk generate` removed | NO | prior report §B greps (control-armed); unchanged since |
| Variant builtins removed: `gitleaks_staged`, `knip_strict`, `pinact_v3`, `pinact_update_v3`, `check_byte_order_marker`, `fix_byte_order_marker` | NO in dotfiles. `hk-common.pkl:118` already uses `Builtins.byte_order_marker` | file-list diff v1.57.0 vs v2.3.0 of `pkl/builtins/` (153 -> 161 files; exactly those 6 removed). KB `hk.pkl` uses `gitleaks_staged` (prior report R2) |
| Staging contextual (#1256): only `pre-commit` stages by default; `hk fix` leaves index alone | YES: `hk.pkl` `["fix"] { fix = true ... }` (hk.pkl:837-841) is what `mise run fmt` runs; under 2.x it stops staging. `AGENTS.md` "Always `git add` BEFORE `mise run fmt`" rationale goes stale | v2.0.0 notes "Staging is contextual" |
| Top-level `steps` materialises check/fix/pre-commit | NOT triggered (we declare explicit `hooks` only). Optional per v2.0.1 #1370 | v2.0.1 notes "Top-level `steps` is optional" |
| Builtins become flat configurable steps; evaluator pklr 2.0.1 (2.0.0) -> 2.0.4 (2.0.1) -> **pklr 3.0 (2.1.0)** | Indirect: our configs rely on spreads (`...allSteps`, `...common.hygiene`) and an aliased relative import (`import "hk-common.pkl" as common`, hk-image.pkl:16). Evaluation parity under pklr 3 is UNMEASURED | v2.1.0 notes "Support comes from upgrading hk's bundled Pkl evaluator to pklr 3.0" |

### Builtin-level changes that reach our steps (v1.57.0 vs v2.3.0 source diff)

All 29 builtins we reference were fetched at both tags (`.agent/kb/raw/hk-v2-builtins/`).
Control: bogus `zq_bogus_77.pkl` -> 404 (rc=1), so the fetcher discriminates.

- **SAME (20):** actionlint, betterleaks, byte_order_marker, check_conventional_commit,
  check_merge_conflict, detect_private_key, fix_smart_quotes, ghalint_action,
  ghalint_workflow, hadolint, mise, mixed_line_ending, newlines, pkl,
  python_check_ast, python_debug_statements, ruff, taplo, trailing_whitespace, yamllint.
- **Test-fixture-only diffs (no runtime effect):** check_added_large_files,
  check_case_conflict, check_executables_have_shebangs, check_symlinks,
  no_commit_to_branch (`write {` -> `write = new Mapping<String,String> {`),
  zizmor (hash-pinned checkout in fixtures), shellcheck (only
  `project_indicators` gains `recursive = true` — `hk init` metadata, not the step).
- **typos:** now preserves typos' exit status when output is empty (v2.1.0 #1398)
  plus invalid-config tests. Stricter, correct; could surface a previously-masked
  failure. Used at `hk-common.pkl:141`.
- **gitleaks:** gains `scan` option; default `dir` argv unchanged (prior report §B).
  Used at `hk.pkl:328`.
- **editorconfig_checker — BITES US.** v2 default `version = "4"` -> argv
  `editorconfig-checker {{files}}` (v1.57.0 argv `ec`). Our pin
  `mise.toml:15 editorconfig-checker = "3.11.3" # provides ec` has no
  `editorconfig-checker` binary name -> ENOENT (seen live in #1090, Q4).
  ALSO NEW since v2.1.0 (#1397): with version 4 the builtin has a **fix** command
  `editorconfig-checker --fix {{files}}` (effect write), so our `fix` and
  `pre-commit` hooks (`fix = true`) would start rewriting files. Used at `hk.pkl:42`.
  Options: bump editorconfig-checker to 4.x in the same change (then accept/decline
  the new fixer), or `(Builtins.editorconfig_checker) { version = "3" }`.

### Schema (`pkl/Config.pkl` v1.57.0 vs v2.3.0)

Property-name diff: added `batch_min_files`, `enabled` (hooks); `check_first`
default flipped `true` -> `false` (v1.57.0 Config.pkl:539 vs v2.3.0:568, v2.2.0
#1461); `CommandSpec.command/effect` became `abstract` (declaration only).
Every key we set still exists with the same type: `min_hk_version`, `fail_fast`,
`exclude` (top-level `List<String>` via `hk-common.pkl:42`), hook `fix`/`stash`/
`steps`, step `fix`/`check`/`batch`/`exclusive`/`glob` (grep of the three files:
hk.pkl:19,22,26,64,87,88,92,96,168,175,334,795,796,838,859,863; hk-image.pkl:19,21,26,30,44;
hk-common.pkl:135,142). We set no `check_first`, `profiles`, `stage`,
`check_diff`, `check_list_files`.

### Behaviour changes (not schema) worth knowing

- v2.2.0 #1461 `check_first` default false: fix steps run `fix` directly. Affects
  our custom ruff steps (hk.pkl:64 `ruff check --fix`, hk.pkl:87 `ruff format`)
  under `fix`/`pre-commit`: fixers now run without a prior check. Output-neutral
  for idempotent formatters; only faster.
- v2.2.0 #1458 batching: `min(jobs, files/4)` batches. Affects our `batch = true`
  steps; no config change.
- v2.2.0 #1460: top-level `exclude` from `~/.config/hk/config.pkl` and `hk.pkl` now
  COMBINE (was replace). Only matters if a user-global hk config exists.
- v2.2.0 #1450: config cache keyed on env vars read by Pkl. Neutral.
- v2.3.0 #1466: staging now always via `git add` (also with libgit2); #1469 stash
  skip on no-HEAD repos; #1476 `GIT_OPTIONAL_LOCKS=0`. Neutral-to-positive.
- v2.3.0 #1468 jq builtin now sorts keys on check. We use NO jq/yq/black/prettier
  builtin (grep `\["(jq|yq|black|prettier)` -> 0; control `Builtins\.` in hk.pkl -> 22).
- v1.58.0 #1318: `HK_FIX`/`HK_CHECK`/`git config hk.check|fix` now select run
  type as documented. Our `autofix.yml` uses `HK_FIX=1` with a `fix = true` hook
  (prior report §B) — unaffected.
- `min_hk_version = "1.49.0"` (hk.pkl:19, hk-image.pkl:19) is weaker than the v2
  package default `"{{version|truncate(length=1)}}.0.0"` (v2.3.0 Config.pkl:13);
  recommend raising to "2.3.0" (or at least "2.0.0") so a stale 1.x binary refuses
  the v2 config instead of silently applying v1 staging semantics.

## Q2. `HK_PKL_BACKEND`

**Tracked repo: prose only, no live setting, no CI env.** `git grep -n HK_PKL_BACKEND`
(excluding `docs/research`, `docs/receipts`) returns only:

- `mise.toml:207` — comment "HK_PKL_BACKEND dropped (#160 T12)"
- `.devcontainer/mise-system.toml:377` — comment "(HK_PKL_BACKEND dropped #160 T12 — pklr parity verified)"
- `.claude/agents/dockerfile-reviewer.md:50` — prose (override retired at hk 1.49)
- `docs/specs/deep-interview-devcontainer-build-mise-chezmoi-resync.md:78`,
  `docs/specs/deep-interview-devcontainer-lifecycle.md:86,198,370` — historical
  spec command lines `HK_PKL_BACKEND=pkl hk run pre-commit ...` (stale if anyone
  copies them; spec history, not config).

No `.github/workflows/*` hit (covered by the same grep; control: the same grep shape
finds the `mise.toml:207` comment).

**User-global mise config: already clean.** `grep -c HK_PKL_BACKEND
~/.config/mise/config.toml` -> 0 (control `grep -c HK_MISE` same file -> 1; line 48
is now `HK_MISE = "1"`, which is where the prior report found `HK_PKL_BACKEND = "pkl"`).
So prior report R1 has been applied by the operator. `mise env -s bash | grep -c
HK_PKL_BACKEND` -> 0 (control `HK_MISE` -> 1). Also 0 in `~/.zshrc`, `~/.zprofile`,
`~/.profile`, `~/.claude/settings.json`, repo `.claude/settings{,.local}.json`,
`mise.local.toml`.

**BUT a stale value is still live in long-running processes.** This agent's own
process env has `HK_PKL_BACKEND=pkl` (`printenv` rc=0, value `pkl`) — inherited from a
shell/Claude session started before the config line was deleted. Measured
consequence (real invocation): in a throwaway repo with NO hk.pkl, `git commit`
fired the GLOBAL hk hook (hk 2.3.0) and **failed rc=1**:
`Error: Failed to load configuration ... HK_PKL_BACKEND no longer selects an
evaluator in hk v2 ... Location: src/config.rs:30:13`. The same commit with
`env -u HK_PKL_BACKEND` -> rc=0. So the bail fires BEFORE the `--from-hook`
no-config no-op check, i.e. a stale `HK_PKL_BACKEND=pkl` breaks **every commit in
every repo** once hk 2 global hooks are installed. Fix: restart any shell / Claude
Code session / terminal multiplexer pane older than the config edit (or
`unset HK_PKL_BACKEND`). No repo change needed.

## Q3. Global git hooks (`~/.gitconfig`) under hk v2

### What hk v2 writes (source: jdx/hk `src/cli/install.rs@v2.3.0`, docs `docs/cli/install.md@v2.3.0`)

- `hk install --global` (requires Git >= 2.54, bails otherwise, install.rs:63-67):
  removes every `hook.hk-*` in `--global`, then writes `hook.hk-<event>.command` +
  `hook.hk-<event>.event` into `~/.gitconfig` (install.rs:323-336, 370-385).
  Command = `<mise> x hk -- hk run <event> --from-hook` when `--mise`/`HK_MISE=1`
  (install.rs:157-166,191-195), else the absolute path of the running hk binary;
  `pre-commit` additionally gets `--staged` (install.rs:511-519).
  **Event set** = the hooks of the project config in the cwd where you ran it (minus
  `check`/`fix`, and `enabled=false` ones), else the fixed set
  `commit-msg, pre-commit, pre-push, prepare-commit-msg` (install.rs:8-10,168-185).
- `hk install` (per-repo): on Git >= 2.54 writes config-based hooks
  (`hook.hk-<event>.command/.event`) into `.git/config` (`--local`), leaving
  `.git/hooks/` untouched; on older Git (or `--legacy`) writes `.git/hooks/*` shims
  (install.rs:91-118; docs `cli/install.md:18`). Local command is
  `mise x -- hk run <event> --from-hook` (install.rs:149-155) — no `--staged`.
- **If ANY `hook.hk-*` exists in `~/.gitconfig`, per-repo `hk install` does NOT
  install, and DELETES existing local hk hooks** (shims + `hook.hk-*` local entries),
  unless `--force-local` (install.rs:74-88, 404-450; docs `cli/install.md:20`).

### What hk does in a repo without hk.pkl

`src/hook_options.rs@v2.3.0:217-232`: `if self.from_hook &&
!Config::project_config_exists()` -> debug log "no hk config found for {name},
skipping (--from-hook)" and return Ok (rc 0). `project_config_exists`
(`src/config.rs@v2.3.0:399-420`) looks for `hk.local.pkl`, `.config/hk.local.pkl`,
`hk.pkl`, `.config/hk.pkl` in cwd **and every ancestor up to (not including) `/`** —
not bounded by the git root. Legacy `hk.toml/yaml/json` count as present (so they
error instead of no-op).

### Current machine state (measured 2026-09-27)

- `git --version` -> 2.54.0 (Apple Git-157): config-based hooks supported.
- `git config --global --get-regexp '^hook\.'` -> ALREADY INSTALLED:
  `hook.hk-pre-commit.command test "${HK:-1}" = "0" || ~/.local/bin/mise x hk -- hk run pre-commit --from-hook --staged`
  and `hook.hk-commit-msg.*` (events pre-commit, commit-msg only — so it was run
  inside a repo whose hk.pkl declares just those two hooks, not dotfiles, which also
  has pre-push).
- In `~/.gitconfig`'s `mise x hk`, `hk` resolves to **2.3.0** outside this repo
  (`~/.local/bin/mise x hk -- hk --version` in scratch -> `hk 2.3.0`; user-global
  `~/.config/mise/config.toml` pins `packslip:github.com/jdx/hk = 2.3.0` per `mise ls hk`).
  Inside dotfiles it resolves to the project pin 1.57.0 (`shared.toml:37`).
- This repo's `.git/config` also has local `hook.hk-pre-commit`, `hook.hk-commit-msg`,
  `hook.hk-pre-push` (from 1.57's `hk install --mise`, `mise.toml:180` postinstall).
- `git hook list pre-commit` in dotfiles -> ONE entry `hk-pre-commit`.

### Does global+local double-fire? No, for same-named hooks

git docs `Documentation/config/hook.adoc@v2.54.0:1-7`: "If more than one value is
specified for the same `<friendly-name>`, only the last value parsed is used."
Probe (isolated `GIT_CONFIG_GLOBAL`): global-only -> `FROM_GLOBAL, OTHER_GLOBAL`;
global+local same name -> `OTHER_GLOBAL, FROM_LOCAL` (local replaced global, once).
So hk's own comment at `install.rs:293-295` ("Git aggregates ... fires hk twice")
is WRONG for hk's same-named entries; in dotfiles today the LOCAL 1.57 command runs.

### Real-invocation probes of the global hook (scratchpad throwaway repos)

| Arm | Result |
|---|---|
| no hk.pkl, `HK_PKL_BACKEND=pkl` inherited | commit **rc=1** (v2 bail, see Q2) |
| no hk.pkl, `HK_PKL_BACKEND` unset, `HK_LOG=debug` | rc=0; log shows `no hk config found for pre-commit, skipping (--from-hook)` and same for commit-msg (proves the hook RAN and no-oped) |
| hk.pkl with an always-failing pre-commit step (control) | commit **rc=1**, `✗ always_fail – ERROR ... PROBE_FAIL_ARM` (proves the global hook enforces when config exists) |
| cost | 3x `git commit` with hook: 1.87/1.85/1.86 s real; with `HK=0`: 0.38/0.38/0.39 s -> **~1.5 s per commit** for two no-op hooks (mise x + hk startup) |

### Interaction with this repo's pytest throwaway repos

14 test files run `git commit` (`git grep -l -E '"commit"|git commit' -- tests`),
25 `"init"` call sites; only `tests/test_safe_directory.py:61-62` isolates
`GIT_CONFIG_GLOBAL`/`GIT_CONFIG_NOSYSTEM` (and `tests/test_graphify.py:1288` sets a
local `core.hooksPath`). So with the global install, every test commit spawns
`mise x hk` twice (~1.5 s each commit) and — worse — **inherits the test runner's
env**: a stale `HK_PKL_BACKEND` makes those commits fail, and any throwaway repo
created under a directory that has an `hk.pkl` ancestor (e.g. inside the dotfiles
checkout rather than pytest `tmp_path` under `/private/var/folders`) would run that
ancestor's full hk config. `tmp_path` has no hk.pkl ancestor (checked `~`, `~/dev`,
`~/dev/github`, `~/dev/github/ray-manaloto`, `/Users`: none; `~/.config/hk` absent).

### Verdict on the global install

Sensible-with-caveats for a single-user Mac, but **not** a fit for this repo's
posture as currently wired:

1. It silently **disables dotfiles' per-repo install**: under hk 2, `mise install`
   runs `mise.toml:180` `hk install --mise`, which sees the global `hook.hk-*`
   entries and DELETES the local `hook.hk-pre-push` — and the global set has no
   pre-push, so `hk.pkl`'s pre-push suite (`ghcr_publish_prereqs`, `test`) would
   stop running with no error. (Same for KB/any repo.) Either re-run
   `hk install --global --mise` from inside dotfiles (event set then includes
   pre-push — but a global pre-push then runs in EVERY hk repo), or use
   `hk install --mise --force-local` in the postinstall.
2. Global command pins whatever `mise x hk` resolves to per cwd — fine, but its
   `--staged` pre-commit flag differs from the local form; mixed 1.57/2.x across
   repos is expected during migration.
3. ~1.5 s tax on every commit in every non-hk repo and in every pytest throwaway
   commit, plus env-leak risk. Mitigate for tests with `GIT_CONFIG_GLOBAL=/dev/null`
   (or `HK=0`) in a conftest autouse fixture.
Recommendation: keep hooks **repo-scoped** here (`hk install --mise --force-local`,
or remove the global `hook.hk-*` with `hk uninstall --global`/`git config --global
--remove-section`), OR if the global install is kept, re-install it from dotfiles
so pre-push is covered and change the postinstall to be explicit about scope. This
is an operator decision (user-level file).

## Q4. Renovate PR #1090 (`renovate/jdx-hk-2.x`) — current failing `lint`

State (2026-09-27, `gh pr view 1090`): OPEN, updated 2026-09-26T21:59Z, now bumps
to **v2.3.0**. Diff touches ONLY `hk.pkl`, `hk-common.pkl`, `hk-image.pkl` (8 URL
tokens + the hk-common.pkl:8 comment); `.config/mise/conf.d/shared.toml` untouched,
so CI ran the **1.57.0 binary against the v2.3.0 pkl package**.
Failing checks: `lint` (run 36274581677, job 108494721519) and `ci-gate` (derived).
Excerpt from `gh run view --job 108494721519 --log-failed` (1705 lines; 68 `✔`,
4 `✗` lines = 2 distinct failing steps, each printed twice):

```
✗ editorconfig-checker – ERROR
hk ERROR check: hook finished with error: editorconfig-checker .agents/plugins/marketplace.json ... (669 files)
    No such file or directory (os error 2)

pin_parity – DRIFT hk
pin_parity –        hk.pkl: 2.3.0, 2.3.0, 2.3.0
pin_parity –        hk-common.pkl: 2.3.0, 2.3.0, 2.3.0
pin_parity –        hk-image.pkl: 2.3.0, 2.3.0
pin_parity –        .config/mise/conf.d/shared.toml: 1.57.0
pin_parity –     -> pin drift across sites: 1.57.0, 2.3.0
pin_parity – pin-parity FAILED for 1 of 5 tool(s): hk
pin_parity – Bump every site for a tool in ONE change. Renovate sees each site as a separate dependency, so group them in renovate.json packageRules as well, or the next bump splits again.
##[error]Process completed with exit code 1.
```

Diagnosis: (1) v2 `editorconfig_checker` default `version="4"` calls
`editorconfig-checker`, absent with our 3.11.3 pin (`mise.toml:15`). (2) Renovate
split: the pkl customManager (`renovate.json:96-108`, depName `jdx/hk`,
github-releases) is not in the `image-build inputs` group whose `matchFileNames`
(`renovate.json:20-27`) list `shared.toml` but not the pkl files — so the binary
bump rides in #1063/#1093 ("update image-build inputs") while the pkl bump is #1090.
Also still open: #1325 (hk v1.58.1, `renovate/non-major`).
Side evidence: the 1.57 binary evaluated the v2.3.0 package with 66 other steps
green — because our explicit `min_hk_version = "1.49.0"` (hk.pkl:19,
hk-image.pkl:19) overrides the v2 package default "2.0.0" (v2.3.0 Config.pkl:13).
That is exactly the silent binary/package skew `min_hk_version` should refuse.

## Q5. hk pin sites (dotfiles)

`mise run pin-parity` (read-only, rc=0): "OK hk — hk.pkl: 1.57.0 x3, hk-common.pkl:
1.57.0 x3, hk-image.pkl: 1.57.0 x2, .config/mise/conf.d/shared.toml: 1.57.0".
Sites pin-parity does NOT cover, found by `git grep -n '1\.57\.0'`:

| Site | Line(s) | How to move it |
|---|---|---|
| `.config/mise/conf.d/shared.toml` | 37 `hk = "1.57.0"` | edit |
| `hk.pkl` | 1, 8, 11 | edit |
| `hk-common.pkl` | 8 (comment), 17, 18 | edit |
| `hk-image.pkl` | 11, 14 | edit |
| `.config/mise/mise.lock` | 412-458 (`[[tools.hk]]` backend `aqua:jdx/hk`, 9 URLs) | `mise run lock-shared -- "hk"` |
| `.devcontainer/mise-system.lock` | 5050-5081 | `mise run lock-image` |
| `tests/test_image_smoke.py` | 814 `assert declared["hk"] == "1.57.0"` | edit |
| `python/src/dotfiles_setup/workflow_claude_code.py` | 86, 104 (tables "Transcribed from hk 1.57.0 `hk --help`/`hk run --help`") | re-transcribe: see below |
| `renovate.json` | 96-108 customManager; 20-27 group | add the 3 pkl files to `matchFileNames` |
| `min_hk_version` | hk.pkl:19, hk-image.pkl:19 (`"1.49.0"`) | raise to `"2.3.0"` |
| KB | `knowledge-base/mise.toml:46`, `hk.pkl:1,6` (see Q6) | separate PR in KB |

`workflow_claude_code.py` flag tables vs real `--help` (both binaries run via
`mise x hk@<v> -- hk ... --help`, rc=0 each): `hk --help` global flags identical;
`hk run --help` gains **`--junit-xml <PATH>`** (value-taking, v2.2.0 #1432) which is
absent from `HK_RUN_FLAGS` (workflow_claude_code.py:108-135; `--sarif` is at :116).
Per the file's own comment (:86-89) an unknown value-taking flag "can consume what
this parser sees as the command" — so add `Flag(("--junit-xml",), takes_value=True)`.
(`--from-ref`/`--to-ref` are present in both; an earlier regex diff flagged them only
because of help-text wrapping — cross-checked by direct grep.)

No `.github/**` pins an hk version (only a prose mention at `autofix.yml:54`).

## Q6. knowledge-base (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base`, branch main)

Pin sites: `mise.toml:46 hk = "1.57.0"`; `hk.pkl:1` and `hk.pkl:6` (two tokens each:
`download/v1.57.0/hk@1.57.0`); prose `currency.toml:1521`. Hooks: `check`, `fix`,
`pre-commit`, `commit-msg` (`hk.pkl:588-606`) — note this is exactly the event set
of the global `~/.gitconfig` install minus check/fix, consistent with the global
install having been run from a repo shaped like this one.

Builtins used: check_added_large_files, check_conventional_commit,
check_merge_conflict, detect_private_key, gitleaks, **gitleaks_staged**, lychee,
mixed_line_ending, newlines, pkl, ruff, rumdl, rumdl_format, taplo, taplo_format,
trailing_whitespace, typos. KB-only ones diffed v1.57.0 vs v2.3.0: lychee, rumdl,
rumdl_format, taplo_format all byte-identical; `gitleaks_staged.pkl` 404 at v2.3.0.

The two workarounds the coordinator named:

- **`hk.pkl:308-346` (`local gitleaksStaged: Step = Builtins.gitleaks_staged`, :346)
  — BREAKS on v2.** The builtin was removed in v2.0.0 (#1253). Replacement
  `(Builtins.gitleaks) { scan = "staged" }` (migration-v2.md:31-33). Argv is
  byte-identical: v1.57.0 `gitleaks_staged.pkl` = `gitleaks git --pre-commit --redact
  --staged --verbose --no-banner`; v2.3.0 `gitleaks.pkl:12-21` with `scan=="staged"`
  = same list. The comment block's history (it was OUR discussion jdx/hk#1246 ->
  jdx/hk#1248) stays accurate; the "46 -> 51" `hk test` count must be re-measured.
- **`hk.pkl:337-340` "FOURTH VERSION TOKEN"** (Module version conflict when only the
  `amends` URI is bumped) — still applies under v2: move all four tokens on lines 1
  and 6 together (the sed probe below did).

### Real evaluation probes (hk binaries run directly, `HK_PKL_BACKEND`/`HK_MISE` unset, `HK_CACHE=0`, scratch copies)

| Config | hk | `hk validate` |
|---|---|---|
| KB hk.pkl as-is (1.57 URLs) | 1.57.0 | rc=0 "is valid" |
| KB hk.pkl, URLs -> v2.3.0 only | 2.3.0 | **rc=1** `Eval error: undefined variable: gitleaksStaged` (misleading message; the missing name is `Builtins.gitleaks_staged`) |
| KB hk.pkl, URLs -> v2.3.0 + `(Builtins.gitleaks) { scan = "staged" }` | 2.3.0 | rc=0 "is valid" |
| dotfiles hk.pkl (+hk-common/hk-image imported), URLs -> v2.3.0 | 2.3.0 | rc=0 "is valid" |
| dotfiles as-is | 1.57.0 | rc=0 |

Plan parity (`hk run <hook> --all --plan --json < /dev/null`, full `git archive HEAD`
tree, index-staged): compared step name, status, fileCount, reasons, metadata,
orderIndex, groups.

- **dotfiles** 1.57.0 vs 2.3.0: check 65/65, fix 65/65, pre-commit 66/66 steps,
  identical order and file counts. **Only diff:** `editorconfig-checker`
  `metadata.effect` `read` -> `write` in `fix` and `pre-commit` (the v2.1.0 fixer).
  So pklr 3.0 evaluates our spread/import architecture identically — the prior
  report's open item E is now CLOSED for dotfiles.
- **KB** 1.57.0 (as-is) vs 2.3.0 (migrated): check/fix/pre-commit 24/24 steps each,
  zero diffs.
- Control arm: the comparison is not blind — v1.57 `check` vs `pre-commit` step sets
  differ by exactly `{no_commit_to_branch}`.
- `pre-push`/`commit-msg` plans need hook args (rc=1/rc=2 with none) — not compared.

### Side finding from the probe (it bit me): config-based hooks ignore `core.hooksPath`

Creating the dotfiles scratch copy with `git -c core.hooksPath=/dev/null commit`
STILL ran the global `hook.hk-pre-commit` — the full 66-step dotfiles pre-commit
ran in the scratch copy (incl. a `uv sync` creating `.venv`), and the commit failed
on `no_commit_to_branch` ("Cannot commit directly to protected branch 'main'").
So `core.hooksPath` (what `tests/test_graphify.py:1288` uses) does not isolate a
test repo from global config-based hooks. See Q8 for the armed probe.

## Q8. Double-fire probe: `.git/hooks/pre-commit` (hk shim) + global `hook.hk-pre-commit`

Setup (all under the scratchpad, hk 2.3.0 binary on PATH, `HK_PKL_BACKEND`/`HK_MISE`
unset): each repo's `hk.pkl` has one pre-commit step `echo run >> <counter>`, so the
counter's line count = number of hk runs per commit. The global entries were written
by hk itself (`GIT_CONFIG_GLOBAL=<tmp> hk install --global`, rc=0; run in a dir with
no hk.pkl it wrote the CORE set `commit-msg, pre-commit, pre-push,
prepare-commit-msg`, confirming `install.rs:8-10,168-176`). The shim was written by
`hk install --legacy` (content: `test "${HK:-1}" = "0" || exec hk run pre-commit
--from-hook "$@"`). Every arm uses `GIT_CONFIG_NOSYSTEM=1` + a temp `GIT_CONFIG_GLOBAL`,
so the real `~/.gitconfig` is not involved.

| Arm | Hooks present | hk runs per commit |
|---|---|---|
| A | `.git/hooks/pre-commit` shim + global `hook.hk-pre-commit` | **2 (double-fire CONFIRMED)**; `git hook list pre-commit` -> `hk-pre-commit`, `hook from hookdir` |
| B (control) | shim only, empty global | 1 |
| C | global only | 1 |
| D | shim + global, `git -c core.hooksPath=/dev/null` | 1 (hookdir suppressed; the GLOBAL config hook still ran -> `core.hooksPath` does not disable config-based hooks) |
| E | local config-based `hook.hk-pre-commit` (from `hk install` on Git 2.54) + global same name | 1 (local replaces global, git `hook.adoc:5-7`) |
| F | fresh repo, `hk install` while global exists | writes nothing: "hk hooks already configured globally (~/.gitconfig); skipping local install" |
| G | shim repo, `hk install` while global exists | **deletes the shim**: "removed hook: .../.git/hooks/pre-commit ... removed 1 stale local hook(s) and did not install new ones" |

Conclusion: yes — a repo with a legacy `.git/hooks/pre-commit` (hk 1.x default on
older Git, or `--legacy`) PLUS the global config hook runs hk twice per commit (both
concurrently-stashing, both staging under v2 pre-commit). Same-named config-based
local+global does NOT double-fire. This dotfiles clone uses config-based local hooks
(`.git/hooks` has no non-sample files), so it is in arm E today — not double-firing.
hk's own warning text (`install.rs:293-295`, "Git aggregates ... fires hk twice")
is correct only for the hookdir+config case (arm A), not same-name config (arm E).

## Q7. Our architecture vs hk v2 documented practice

Upstream sources: `docs/configuration.md@v2.3.0:12-60` ("For a shared set of linters,
prefer top-level `steps`"; "You can omit top-level `steps` ... This is fully supported
in v2"; "Existing typed mappings such as `local linters = new Mapping<String, Step>`
and `steps = linters` remain supported"), `docs/migration-v2.md@v2.3.0:56-74`,
`docs/pkl_introduction.md@v2.3.0:130-200` (sharing, `import*`),
`docs/mise_integration.md@v2.3.0:36-77`, `docs/cli/install.md@v2.3.0:16-20`.

| Aspect | Ours | Upstream v2 recommendation | Verdict | Evidence |
|---|---|---|---|---|
| Sharing steps across check/fix/pre-commit | `local allSteps` (hk.pkl:34) spread into explicit `pre-commit`/`check`/`fix` hooks (hk.pkl:~795-840); KB `lintSteps` assigned to 3 hooks (KB hk.pkl:588-601) | Top-level `steps { }` materialises the three hooks; hook-only + typed local mappings "fully supported" | **Equal (supported), slightly more verbose.** Top-level `steps` would delete ~3 hook blocks but changes `suites.toml` contract shapes; `pre-commit`'s extra `no_commit_to_branch` would become a hook-level addition. Optional, not a defect | configuration.md:14-24,35-60; migration-v2.md:58 |
| Cross-file split (`hk-common.pkl` groups imported by `hk.pkl` and `hk-image.pkl`) | `import "hk-common.pkl" as common`, `...common.hygiene` etc. (hk.pkl, hk-image.pkl:16,34-37) | Docs show sharing via `amends "./hk.pkl"` (hk.local.pkl) and, new in v2.1, `import*("generated/*.pkl")` for many files | **Equal / better for our case.** Two *independent* configs (host vs `/etc/hk/hk.pkl` in the image) sharing groups is not what `hk.local.pkl` models; `import*` buys nothing for one shared file. Proven to evaluate identically under pklr 3 (Q6 plan parity) | pkl_introduction.md:130-200; v2.1.0 notes #1423 |
| `stage` | never set; relies on default | `pre-commit` stages by default; `fix`/`check`/custom leave index alone | **Equal for pre-commit; behaviour changes for `fix`** (see next row) | v2.0.0 #1256 |
| "Always `git add` BEFORE `mise run fmt`" (AGENTS.md:152-155) | rationale: "`fix=true` can strand unstaged edits" | `hk fix` never stages in v2; `--stage` opts in | **Stale under v2.** Rationale becomes false; `mise run fmt` (`mise.toml:1297-1299` `run = "hk fix"`) leaves fixes unstaged. Keep "`git add` your edits first" only as diff hygiene; add "review then `git add` fixer output" | migration-v2.md:72-74; prior report R5 |
| `check`/`fix` hook wiring | explicit `["check"]` and `["fix"] { fix = true }` (hk.pkl:832-841) | Materialised automatically when top-level `steps` is used; explicit is fine | Equal | configuration.md:28-40 |
| `exclusive` (ruff format hk.pkl:88; pre-push steps :859,:863) | used | still supported, unchanged schema (Config.pkl v2.3.0:828) | Equal | Config.pkl diff |
| `batch = true` (hk.pkl:92,96,168,175,334; hk-common:135,142; hk-image:44) | used, no `batch_min_files` | v2.2 batches `min(jobs, files/4)`; v2.3 `batch_min_files` (default 4) helps slow-startup tools on whole-tree runs | **Equal; tuning opportunity.** For `mise run lint` (`hk check --all`, ~670 files) a higher `batch_min_files` on slow-startup batched steps could cut process count; measure before adopting (upstream: small pre-commits got slightly slower) | v2.3.0 notes #1475 |
| `check_first` | not set (was implicitly `true`) | default now `false` (fix directly) | Equal/better for free (faster fix/pre-commit) | Config.pkl v1.57.0:539 vs v2.3.0:568 |
| `min_hk_version = "1.49.0"` | hk.pkl:19, hk-image.pkl:19, KB hk.pkl:9 | package default = `<major>.0.0` of the package | **Worse** — overrides the guard; #1090 proved a 1.57 binary happily evaluates the v2.3.0 package. Set `"2.3.0"` | v2.3.0 Config.pkl:13; Q4 |
| Mise integration | `HK_MISE = "1"` in `[env]` (mise.toml:211, mise-system.toml:378) + postinstall `hk install --mise` (mise.toml:180) | Recommended: `hk install --global --mise` on Git 2.54+ once per machine; `hk install --mise` still documented for repo-scoped; the postinstall recipe "is removed from the main setup flow" (v2.0.1 #1376). `HK_MISE=1` makes `--mise` the default | **Mostly equal; one real hazard:** on a machine with any global `hook.hk-*`, the v2 postinstall `hk install --mise` DELETES local hooks and installs none (Q8 arms F/G). With today's global set (pre-commit, commit-msg) dotfiles would lose `pre-push`. Use `hk install --mise --force-local` if repo scope is kept | mise_integration.md:36-77; install.rs:74-88 |
| External hard timeout (`python/src/dotfiles_setup/lint.py`, `[tasks.lint]` mise.toml:262) | out-of-process kill of hk's process group | hk has no timeout setting | **Still required.** 0 `timeout` hits in v2.3.0 `settings.toml`, `docs/environment_variables.md`, `docs/configuration.md`, `pkl/Config.pkl` (control `fail_fast`: 3/2/1 hits) | this report's probe |
| Hook installation scope | per-repo config-based hooks in `.git/config` (`hook.hk-pre-commit/commit-msg/pre-push`, via 1.57 `hk install --mise`); separately, a global `~/.gitconfig` `hook.hk-pre-commit/commit-msg` written by another project's `hk install --global --mise` | Upstream recommends global | **Ours is the safer choice for this repo**, but the two now coexist: same-name local overrides global (arm E, no double-fire); a legacy `.git/hooks` shim + global double-fires (arm A); global hooks ignore `core.hooksPath` (arm D) and add ~1.5 s/commit in non-hk repos and pytest throwaway repos; a stale `HK_PKL_BACKEND=pkl` in env makes the global hook fail every commit (Q2) | Q3, Q8 |
| Builtin variants | none used (dotfiles); KB `gitleaks_staged` | typed options | dotfiles equal; KB must migrate | Q6 |
| `editorconfig_checker` | pinned ec 3.11.3, builtin default | builtin defaults to v4 binary + fixer | **Breaks** until pinned `version = "3"` or ec bumped to 4.x | Q1, Q4 |

### Is our setup "wrong or suboptimal" vs v2 best practice? (verdict)

- **Not wrong architecturally.** The hook-scoped + spread/import design is explicitly
  supported in v2 and evaluates to the identical plan under hk 2.3.0/pklr 3 (Q6).
- **Wrong/stale in four concrete places:** `min_hk_version = "1.49.0"`
  (defeats the guard), the fmt/`git add` doctrine (AGENTS.md:152-155), the
  editorconfig-checker coupling, and the Renovate grouping that can never deliver the
  bump green (Q4).
- **Suboptimal/optional:** top-level `steps` could shorten hk.pkl; `batch_min_files`
  tuning for whole-tree lint; the global-hook question is a machine policy, and for
  a machine with many non-hk repos plus pytest throwaway repos, repo-scoped hooks are
  the lower-risk choice.

## Recommended migration order (dotfiles, then KB)

1. **Operator, now:** restart any shell / Claude session / tmux pane that still has
   `HK_PKL_BACKEND=pkl` (the global v2 hook fails every commit in every repo with it).
   Decide the global-hook policy: either `hk uninstall --global` (keep repo-scoped),
   or keep global and re-run it from dotfiles so `pre-push` is included.
2. **renovate.json:** add `hk.pkl`, `hk-common.pkl`, `hk-image.pkl` to the
   `image-build inputs` group `matchFileNames` (renovate.json:20-27) so the binary and
   package move together; close/supersede #1090, #1325.
3. **One PR (dotfiles):** `shared.toml:37` -> 2.3.0; 8 pkl URL tokens (+ hk-common.pkl:8
   comment); `min_hk_version = "2.3.0"` (hk.pkl:19, hk-image.pkl:19);
   `["editorconfig-checker"] = (Builtins.editorconfig_checker) { version = "3" }`
   (hk.pkl:42) — or bump editorconfig-checker to 4.x and consciously accept the new
   fixer; `mise run lock-shared -- "hk"` then `mise run lock-image`;
   `tests/test_image_smoke.py:814`; add `--junit-xml` to `HK_RUN_FLAGS`
   (workflow_claude_code.py:108) and update the "Transcribed from hk 1.57.0" notes
   (:86,:104); rewrite AGENTS.md:152-155 fmt doctrine; decide postinstall
   `hk install --mise` vs `--force-local` (mise.toml:180). Gates: `mise run lint`,
   pytest, `mise run verify`, `mise run pin-parity`, and a `hk run pre-commit` +
   `hk fix` smoke on a scratch commit.
4. **KB PR:** `mise.toml:46`; `hk.pkl:1,6` (four tokens); `hk.pkl:346` ->
   `(Builtins.gitleaks) { scan = "staged" }` (validated rc=0 on 2.3.0, plan parity 24/24);
   re-measure the `hk test` count quoted at hk.pkl:331-335; `min_hk_version` (KB hk.pkl:9).
5. Optional follow-ups: top-level `steps`; `batch_min_files` measurement; retire
   `no_hk_depends` question (prior report D1, still Ray's standing decision).

## Unverified / residual

- Real `hk run pre-commit`/`hk fix` EXECUTION under 2.3.0 for the full dotfiles
  config was not run (only `validate` + `--plan`); execution-time differences
  (check_first=false, new batching, v2.3 staging) are covered only by release notes.
- `pre-push` and `commit-msg` plans were not compared (need hook args).
- The per-commit ~1.5 s cost is n=3 on one machine, coarse `/usr/bin/time`.
- Who installed the global `hook.hk-*` entries: coordinator states another project
  (not ours); consistent with the 2-event set, not independently verified.

## GitHub repos touched

- [jdx/hk](https://github.com/jdx/hk) — release notes v1.58.0-v2.3.0; `docs/migration-v2.md`, `configuration.md`, `pkl_introduction.md`, `mise_integration.md`, `cli/install.md`, `cli/uninstall.md`, `environment_variables.md`, `settings.toml`; `pkl/Config.pkl` and `pkl/builtins/*.pkl` at v1.57.0 and v2.3.0; `src/cli/install.rs`, `src/hook_options.rs`, `src/config.rs` at v2.3.0
- [git/git](https://github.com/git/git) — `Documentation/config/hook.adoc` at v2.54.0 (config-based hook scope semantics)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — hk configs, pin sites, renovate.json, lint.py, workflow_claude_code.py, tests; PR #1090 CI log (run 36274581677 job 108494721519); PRs #1325, #1063, #1093 listed
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — hk.pkl, mise.toml (local clone, read-only; scratch copies only)
