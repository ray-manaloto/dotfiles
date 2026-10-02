# Cold review — 93d70c9 (native self-updating claude/codex/agy in the devcontainer)

- Subject: `93d70c96a152deaba9dc772b667fb7f03d6133c8`
- Base: `origin/main` = `846f20064de94e91a6251271be89ad41b3e31b2e` (also the merge-base)
- Diff: `git diff origin/main...93d70c96` — 30 files, +1172 / -345
- Reviewer: cold-reviewer (Opus), diff-only, no intent supplied
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start (first run)
- Status: COMPLETE (round 1, open hunting)

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| 1 | HIGH | The `MISE_*` passthrough hands the Doppler-injected `MISE_GITHUB_TOKEN` (a GitHub credential) to all three unpinned remote vendor install scripts and to the `--version` probes; the docstrings' "None of them is a credential" and "the Doppler-injected container credentials never reach a vendor script" are false | `python/src/dotfiles_setup/native_clis_container.py:52-55`, `:112-119`, `:24-26` | `doctor.toml:78` lists `MISE_GITHUB_TOKEN` in `[fnox].env_true`; `grep -c '^MISE_GITHUB_TOKEN='` on the `--env-file` Doppler files (`devcontainer.json:112-116`) = 1 in both `doppler-273897ea-amd64.env` and `doppler-0f760abc-amd64.env` (control: `OPENROUTER_API_KEY` = 1, fresh absent name = 0); it is the ONLY `MISE_` name in the file. `_minimal_env` keeps every `k.startswith("MISE_")`. |
| 1a | (evidence) | Real-call probe of the COMMIT's `_minimal_env` (module extracted with `git show 93d70c96:…` to `/tmp/cr93/ncc_commit.py`, because the worktree copy was being edited concurrently) with canary values | `native_clis_container.py:112-119` | input `{MISE_GITHUB_TOKEN, DOPPLER_TOKEN, GITHUB_TOKEN, HOME}` → kept `['HOME', 'MISE_GITHUB_TOKEN']`, rc=0. Control arm: `DOPPLER_TOKEN`/`GITHUB_TOKEN` dropped, so the allowlist discriminates and the prefix rule is what leaks. |
| 2 | MEDIUM | The credential test cannot see finding 1: its only canary is `DOPPLER_TOKEN`, which the allowlist drops anyway; no `MISE_`-prefixed secret is seeded, so the leak passes green | `tests/test_native_clis_container.py:181-207` | canary is `env["DOPPLER_TOKEN"]` (line 187); the only `MISE_` name seeded is the non-secret `MISE_SYSTEM_CONFIG_DIR` (line 188), asserted PRESENT (line 205). `grep -c MISE_GITHUB_TOKEN` on the commit's test file = 0 (control `_FakeInstall` = 6). |
| 3 | MEDIUM | The install now runs BEFORE `chezmoi init --apply` under `set -euo pipefail`, so any failure at any of three third-party origins (claude.ai, chatgpt.com, antigravity.google), or of the first `uv sync` of the project venv (incl. the `git+https` kb-setup dep) that `uv run` now performs at on-create, aborts onCreateCommand before chezmoi (which renders the #1183 `safe.directory` stanza and the user mise overlay config), the ownership repair and the overlay `mise install`. The spec's "the same as the overlay `mise install`" is not the same: that step runs after chezmoi, this one gates it | `.devcontainer/scripts/on-create.sh:33`, `:42`, `:45`; `native_clis_container.py:233-246` | `install()` returns the first non-zero rc (`:241-246`); on-create had no `uv run` before this diff (`git diff` adds the only one); `python/pyproject.toml:40` kb-setup is `git+https://github.com/...`; spec `docs/specs/native-cli-devcontainer-2026-10-01.md:114` ("Fail loud... the same as the overlay `mise install`"). Whether devcontainers CLI then skips postCreate is UNVERIFIED here (not probed). |
| 4 | MEDIUM | The wiring is unbound: no test or `suites.toml` contract reads the on-create call or the smoke call, and the `install` verb is never driven through the CLI. Deleting either call line leaves every gate green (`bash_budget` permits shrinking), which is the wiring-not-logic defect class `test_safe_directory.py` binds for the #1183 preflight | `.devcontainer/scripts/on-create.sh:42`; `scripts/devcontainer-smoke.sh:93-94`; `tests/test_native_clis_container.py:285-294` | `git grep native-clis 93d70c96 -- tests python/verification hk.pkl hk-common.pkl` → one hit, the `check` CLI test only. Precedent for binding a smoke line: `tests/test_safe_directory.py:12` reads `scripts/devcontainer-smoke.sh`. |
| 5 | MEDIUM | The CI no-mount smoke changed from REQUIRING claude/codex to FORBIDDING claude/codex/agy, and no test at this commit executes the new block (pass arm or fail arm) | `python/src/dotfiles_setup/image.py:1043-1053` | `git show 93d70c96:tests/test_image_smoke.py` has only `"AI CLI checks" not in script` assertions (lines 871, 1002) for OTHER scripts; `grep -c "baked into the image"` on the commit's test file = 0. Uncommitted tests for exactly this block appeared in the worktree mid-review (see notes) — they are not part of `93d70c96`. |
| 6 | MEDIUM | codex's schema `version` becomes a frozen, false provenance label: `check_drift`'s version arm can never fire for codex (`pin := entry.version`, then `pin != entry.version`), and `refresh` re-downloads the UNVERSIONED codex URL and re-records `version = 0.154.0` whenever the bytes change, while the native codex self-updates (spec measured 0.160.0). Previously Renovate moved the shared.toml pin and drift fired. The new header instruction "hand-edit `version` (+ the `source` tag), then run the refresh, which re-downloads at that tag" is false for codex — it has no tag and `_source_url` ignores `version` for it | `python/src/dotfiles_setup/schema_vendor.py:124`, `:197-198`, `:206`, `:420-421`, `:445-451`; `schemas/sources.toml:7-9`, `:43-47` | `_source_url` docstring at commit: codex is "a single unversioned URL that always serves the current schema... `version` records which codex release the bytes were fetched against" — after this diff nothing ever updates that record. Spec D1' measured codex 0.160.0 vs recorded 0.154.0. |
| 7 | LOW | The `mise.toml` comment says this `disable_tools` "REPLACES the global one" and, two lines later, that "the global list still covers codex/claude" — the second clause is false: effective `disable_tools` in this worktree is `["antigravity-cli"]` while the global list names codex/claude-code | `mise.toml:153-158` | `mise settings get disable_tools` in the worktree → `["antigravity-cli"]`, rc=0; `~/.config/mise/config.toml:12` lists `codex`, `claude-code`, `npm:@openai/codex`, … (control arm: the global entries exist, and are not effective here). No current tool declaration is re-enabled by this (none found in the merged project config), so the impact is the false claim. |
| 8 | LOW | "Move it aside (never delete)" is not enforced: `Path.replace` silently overwrites an existing `.<tool>.pre-native`, so a second migration of the same path destroys the first saved copy | `python/src/dotfiles_setup/native_clis_container.py:182-189` | `target.replace(aside)` with a fixed aside name; no existence check; the commit's test asserts only a single move (`tests/test_native_clis_container.py:210-228`). Same false clause in the commit message ("moved aside, never deleted"). |
| 9 | LOW | The probe-only updater switches are untested: no test references `_PROBE_ENV`, `DISABLE_AUTOUPDATER` or `AGY_CLI_DISABLE_AUTO_UPDATE`, so dropping them (and letting `--version` trigger a mid-smoke self-update) leaves the suite green. The agy variable name itself is UNVERIFIED (not probed in this review) | `python/src/dotfiles_setup/native_clis_container.py:60`, `:266` | `grep -c "_PROBE_ENV\|DISABLE_AUTOUPDATER\|AGY_CLI_DISABLE"` on the commit's test file = 0 (control `_FakeInstall` = 6). |
| 10 | LOW | Installer runs are opaque and leak on timeout: `capture_output=True` buffers up to 600 s per step and logs only after exit, so a slow on-create shows nothing; on `TimeoutExpired`, `subprocess.run` kills only the direct child, leaving installer grandchildren (curl, `claude install`) writing into `~/.local` after on-create has moved on/failed | `python/src/dotfiles_setup/native_clis_container.py:46`, `:122-138`, `:222-223` | CPython `subprocess.run` documents kill of the child on timeout only (no process-group kill); behaviour not probed live here. |
| 11 | LOW | Unrelated version bumps ride the base rebuild unannounced: the lock-image regeneration moved 8 tools and 3 conda packages that have nothing to do with the three CLIs, and the commit message calls it only "regenerate the image locks" | `.devcontainer/mise-runtime.lock`, `.devcontainer/mise-system.lock` | Tool/version diff main→commit: gh 2.101.0→2.102.0, task 3.53.1→3.54.0, turso 0.7.2→0.8.1, gemini-cli 0.61.0→0.62.0, conan 2.32.0→2.33.0, usage 6.11.1→6.12.0, conda:git 2.55.0→2.56.0, rust 1.98.1→1.99.0; conda libpng 1.6.58→1.6.59, perl/tbb build bumps. A regression in any of these would be attributed to this PR. Q-SCOPE: ticket or split, not a change request on the CLI logic. |
| 12 | LOW | The smoke banner and the CLI help claim "no mise/npm copy" / "no mise copy exists", but the check only covers (a) the PATH-winning binary and (b) keys in the ACTIVE mise config (`mise ls --current`); an installed-but-inactive mise or bun/npm global copy later on PATH is not looked at | `scripts/devcontainer-smoke.sh:93`; `python/src/dotfiles_setup/main.py:364-375`; `native_clis_container.py:275-293` | `mise ls --current --json` shape probed on the host: a dict keyed by active tool key (157 keys, control `hk` present). |
| 13 | LOW | The new tier-3 assertion is not merge-base-aware, unlike tier 1: against the current `:dev` (built from the merge-base, still carrying `npm:@openai/codex` and `claude-code` in its baked system config) `native-clis check` fails by construction, so `verify-container-latest` cannot pass on this branch until a `pr-NNN` image is synced. `ship` is unaffected because `mise-runtime.toml`/`shared.toml` are base inputs that skip `sync-full` | `scripts/devcontainer-smoke.sh:93-94`; `native_clis_container.py:282-293` | Tier-1 merge-base design: `scripts/devcontainer-smoke.sh:25-37`; base inputs: `python/src/dotfiles_setup/pr.py:132-142`; container reads the BAKED system config (`devcontainer.json:182`, `MISE_IGNORED_CONFIG_PATHS`). Not run live. |
| 14 | LOW | The install now runs before on-create's own "Scoped ownership repair", so it meets the very condition that repair exists for (paths under `$HOME` not owned by the user); `install_one` does not catch `OSError` from `target.replace(...)`, so a non-user-owned `~/.local/bin/<tool>` surfaces as a Python traceback rather than a logged finding | `.devcontainer/scripts/on-create.sh:42` vs `:47-55`; `python/src/dotfiles_setup/native_clis_container.py:182-189` | `_default_run` collapses OSError to rc 127 (`:136-137`) but `replace` is outside it; ordering read from the commit. Not probed live. |

## Notes / evidence log

- **Concurrent writer in this worktree.** At start `git status` was clean; mid-review
  `tests/test_image_smoke.py` became modified (+51 lines, adding AI-CLI-block tests) and a
  `2026-10-01-dockerfile-reviewer-native-cli-devcontainer.md` report appeared. Those bytes
  are NOT in `93d70c96` and are not reviewed here. Every claim below was checked against
  the commit (`git show 93d70c96:<path>`); `git diff 93d70c96 --stat` showed that test file
  as the only divergence when checked. Later still, `git diff 93d70c96 --stat` also showed
  `on-create.sh`, `bash_budget.py`, `native_clis_container.py` (+21) and `schema_vendor.py` (+6)
  modified, and `tests/test_native_clis_container.py` changed on disk. Some of those edits may
  already address findings below; they were deliberately not read, because they are not the subject.
- Dropped after checking: (a) the `--proto =https` redirect gap (curl's docs say `--proto-redir`
  cannot re-enable a protocol `--proto` denied); (b) `XDG_DATA_HOME`/`CODEX_HOME`/`CLAUDE_CONFIG_DIR`
  steering a self-update outside the vendor root (none is set in the commit's `.devcontainer/` or
  `home/`; control `TMPDIR` found in `Dockerfile.host-user`); (c) `rule-sync` breakage from the
  `.claude/CLAUDE.md` edit (the edited paragraph is not a synced line, `rule-sync.toml:39-41`).
- Hypothesis REFUTED: the new "baked into the image" absence loop would fire inside a real
  devcontainer (where ~/.local/bin holds the native installs). It does not: it lives only in
  `build_smoke_script` (CI no-mount, `image.py:1043-1053`); the devcontainer's tier 3 runs
  `build_tier3_script`, which is `_TIER3_COMPILER_BODY` only (`image.py:835-867`).
- `~/.local/bin` precedes both mise shim dirs on the overlay PATH
  (`Dockerfile.host-user:77`), so a leftover mise shim cannot shadow the native install.

## Q-FRESH (decision -> action re-validation)

- `install_one`: present-check -> skip (`:178-181`); stale-check -> move aside (`:182` re-reads
  `is_symlink()/exists()` immediately); the post-install `vendor_finding` (`:227`) re-validates
  against what the installer just wrote. Fresh.
- `check_one`: `which` -> `vendor_finding` -> `--version` on `expected` (`:258-266`); `real` (`:265`)
  only feeds a log line. Fresh.
- on-create: the install decides on `~/.local/bin/<tool>`, then `chezmoi --force` runs. chezmoi no
  longer manages anything under `~/.local/bin` (the commit's `home/` tree has no `dot_local/bin`
  entry; `home/.chezmoiremove` is comment-only), so the apply cannot undo the decision. Fresh.
- The installers' rc-file edits are undone only for chezmoi-managed files (`.bashrc`, `.profile`,
  `.zshenv`, `.zshrc` exist under `home/`); the measured edits (spec "rc-edit" row) hit `.bashrc`
  and `.profile`, both managed. No `chsh`/zsh login shell appears in the Dockerfiles read, so the
  measurement environment plausibly matches onCreate's `SHELL`; not re-probed.

## Q-SCOPE

Subject: "native self-updating claude/codex/agy; drop mise/npm copies". Findings 1-10 and 12-14
are in scope (code, tests, comments or docs this commit adds). Finding 11 (8 unrelated tool bumps
plus conda rebuilds in the image locks) is a sibling: recommend a split or a ticket, not a change
to the CLI logic.

## Q-CLAIM (operator-facing strings this diff adds/changes)

| Clause | Enforcing line | Verdict |
|---|---|---|
| "the Doppler-injected container credentials never reach a vendor script" (module docstring) | none: the `MISE_*` prefix passes `MISE_GITHUB_TOKEN` | FALSE, finding 1 |
| "None of them is a credential" (`_ENV_PASSTHROUGH_PREFIX` comment) | none | FALSE, finding 1 |
| commit msg "minimal env (no Doppler secrets…)"; spec §4 "Installers never see the container's Doppler credentials"; spec rev 1 MISSING-3 "(no credentials)" | none | FALSE, finding 1 |
| "a present vendor install is left to its updater" | `native_clis_container.py:178-181` | holds |
| "moved aside, never deleted" (commit msg, `:183-186` comment) | `:187-188` uses an overwriting `replace` | partly false, finding 8 |
| "https-only fetch to a file" | `:197-209` (`--proto =https`, `-o`) | holds (`--proto` also bounds redirects per curl's docs; not probed) |
| `check`: "its realpath sits under the vendor's own install root" | `vendor_finding` `:146-157` | holds |
| "`--version` never triggers an update mid-smoke" | `_PROBE_ENV` `:60`, `:266` | enforced in code, unbound by tests (finding 9); agy variable UNVERIFIED |
| smoke banner "(home volume, no mise/npm copy)"; CLI help "no mise copy exists" | only the PATH-first binary + `mise ls --current` | overstated, finding 12 |
| CI smoke "FAIL: $tool baked into the image at …" | `image.py:1049-1053` | holds; untested at the commit (finding 5) |
| `mise.toml` "the global list still covers codex/claude" | none: the list is replaced | FALSE, finding 7 |
| `sources.toml` header "hand-edit `version` (+ the `source` tag)… re-downloads at that tag", for codex | none: codex's URL is unversioned | FALSE for codex, finding 6 |
| `_VENDORED_PIN_TOOLS` comment "the vendored `version` … IS the pin" | true for claude-code (CI `setup-claude-code` reads it); nothing consumes codex's as a pin | misleading, finding 6 |
| `bash_budget` "74 -> 78" / "163 -> 166" justifications | the diff adds exactly 4 / 3 lines | holds |

## Gates

Not run by this reviewer: the worktree was being edited concurrently (python/src, on-create.sh,
tests), so `mise run lint`/pytest/`verify` here would have measured a tree that is not `93d70c96`.
Real-call probes run: `_minimal_env` of the commit's module (row 1a); `mise ls --current --json`
shape; `mise settings get disable_tools`; Doppler env-file key COUNTS (no values printed). No PR or
CI run exists yet for `93d70c96` (`gh pr list --head feat/native-cli-devcontainer` and
`gh run list --commit 93d70c96…` both returned `[]`).

## Verdict

DO NOT SHIP as-is on finding 1 (a credential reaches three unpinned remote scripts, contradicting
the diff's own stated invariant). Cheap fix: allowlist the specific `MISE_*` config names the shim
needs (or drop every `*TOKEN*`), and seed a `MISE_`-prefixed canary in the test. Findings 3-6 should
be dispositioned in this unit of work or ticketed. This round was OPEN HUNTING; it cannot end the
loop and should promote to one bounded round over the 14 rows above.

## GitHub repos touched

_None._ Only this repository's files at `93d70c96` / `origin/main`, the user-global mise config,
and host-side Doppler env-file key counts were read; no external repository source or docs.

---

# Round 2 — bounded re-review of `ccfc7b85` (fix for round 1)

- Subject: `ccfc7b8538eb45f49508d6a960e1e9abb49639c6`; delta reviewed `git diff 93d70c96 ccfc7b85`
  (14 files, +408 / -37). Every read via `git show ccfc7b85:<path>`.
- Domain (cardinality 14 + 1): the 14 round-1 findings, each judged FIXED / ACCEPTED-RESIDUAL
  (documented in spec §4) / NOT FIXED; plus new defects introduced by `ccfc7b85` itself only.
- Status: COMPLETE (bounded round: all 14 rows judged + the new-defect question answered)

## Round-2 disposition of the 14 round-1 findings

| # | R1 sev | Verdict | Where (at `ccfc7b85`) | Evidence |
|---|---|---|---|---|
| 1 | HIGH | **FIXED** | `python/src/dotfiles_setup/native_clis_container.py:78-82`, `:139-147` | `_CREDENTIAL_NAME` drops credential-shaped `MISE_*`; mutation removing it fails 2 tests (E1); the only real `MISE_*` secret (`MISE_GITHUB_TOKEN`) is the only container `MISE_*` name the regex drops (E2) |
| 2 | MEDIUM | **FIXED** | `tests/test_native_clis_container.py:189-192`, `:212-214`, `:305-325` | `MISE_GITHUB_TOKEN` canary seeded for both install and `--version` paths; armed by E1 |
| 3 | MEDIUM | **FIXED as scoped**; residual undocumented | `.devcontainer/scripts/on-create.sh:43-44`, `:81` | rc held via `\|\| native_rc=$?`, returned last, so chezmoi / ownership repair / overlay install now run. Residual (round 1 left it UNVERIFIED, now verified from spec text, E3): `onCreateCommand` still exits non-zero, so `postCreateCommand` (`devcontainer.json:237`: authorized_keys = R1, known_hosts, smoke) and `postStartCommand` (`:244`, R2 chown) are skipped on a vendor outage at first create. Spec §4 `:114-116` accepts "fails `onCreateCommand`" but does not name the R1/R2 consequence |
| 4 | MEDIUM | **FIXED** | `python/verification/suites.toml:2985-3014` | suite passes on the commit, fails with the on-create call deleted (E6); all 8 tokens unique. Ordering not bound (new defect N1) |
| 5 | MEDIUM | **FIXED** | `tests/test_image_smoke.py:2016-2065` | pass arm + 3 baked arms + missing-gemini arm; all 5 fail against main's pre-change block (E5) |
| 6 | MEDIUM | **ACCEPTED-RESIDUAL** | spec `docs/specs/native-cli-devcontainer-2026-10-01.md:119-121`; `schemas/sources.toml:10-12` | codex `version` reframed as a label, `sha256` verifies; rendered header == file and `check_drift` = [] on the commit tree. Leftover contradiction: `sources.toml:7-9` still says codex's `version` "IS the pin… re-downloads at that tag", and `schema_vendor.py:120-123` still says "the vendored `version` … IS the pin" for codex |
| 7 | LOW | **FIXED** | `mise.toml:157` | false clause replaced by "No repo config pins codex/claude at all"; control-armed `git grep` (control `hk = "2.3.0"` hit) finds codex only in a vendored research raw file |
| 8 | LOW | **FIXED** | `native_clis_container.py:194-210`; test `tests/test_native_clis_container.py:329-340` | aside name is UTC-second-stamped; test fails against the old fixed name. A same-second collision would still overwrite (`rename` is POSIX-replacing) — theoretical, not raised |
| 9 | LOW | **FIXED** | test `tests/test_native_clis_container.py:305-325` | asserts both switches reach the probe. Names now probed: `AGY_CLI_DISABLE_AUTO_UPDATE` in the host native agy binary = 1 line, `DISABLE_AUTOUPDATER` in claude 2.1.287 = 8 (fresh absent names = 0). Value semantics (`"true"`) UNVERIFIED; host binaries are darwin builds |
| 10 | LOW | **ACCEPTED-RESIDUAL** | spec `:133-134`; code unchanged `native_clis_container.py:150-166` | documented |
| 11 | LOW | **ACCEPTED-RESIDUAL** | spec `:137-138`; `ccfc7b85` commit body | 8 tools named in the commit body; "and the PR" is pending (`gh pr list --head feat/native-cli-devcontainer --state all` = `[]`, control query returned #1507). Conda libpng/perl/tbb build bumps not named |
| 12 | LOW | **NOT FIXED** (partly) | `python/src/dotfiles_setup/main.py:374` | smoke banner fixed (`scripts/devcontainer-smoke.sh:93`, now "no active mise copy", enforced by `mise ls --current` at `native_clis_container.py:333`); CLI help still claims "no mise copy exists" (E4); not listed in §4 |
| 13 | LOW | **ACCEPTED-RESIDUAL** | spec `:135-136` | documented |
| 14 | LOW | **FIXED** | `native_clis_container.py:204-208`, `:271-274` | `OSError` from the move is caught, logged, tool returns 1, the other tools continue; ownership repair still runs after (held rc). No test drives the OSError arm (read only) |

Tally: FIXED 9 (1, 2, 3, 4, 5, 7, 8, 9, 14) · ACCEPTED-RESIDUAL 4 (6, 10, 11, 13) · NOT FIXED 1 (12).

## New defects introduced by `ccfc7b85` itself

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| N1 | LOW | The new suite's description claims on-create "calls `devcontainer native-clis install` BEFORE chezmoi", but nothing enforces the ordering: `require_tokens` checks presence only | `python/verification/suites.toml:2987`, `:3000-3003` | E7: call moved after `chezmoi init --apply` → suite still 1 passed, rc=0 |
| N2 | LOW | `on-create.sh` prints "[on-create] Done" and then exits with the held non-zero rc, with no line naming the held native-install failure; the cause sits in python log lines above the chezmoi/mise output | `.devcontainer/scripts/on-create.sh:80-81` | read from the commit; no echo references `native_rc` except the exit |
| N3 | LOW | The proxy passthrough is labelled "not credentials" unconditionally, but proxy URLs can carry `user:password@` userinfo, which would then reach the three unpinned vendor scripts. No current source injects these names (E2: count 0 in every Doppler env file), so impact today is the overstated clause | `native_clis_container.py:60-70`; spec `:117-118` | E2; Docker Desktop proxy injection into containers not probed (UNVERIFIED) |

Checked and NOT raised: the credential regex drops no container `MISE_*` config name (E2); every
contract token counts exactly 1; `bash_budget` 81 equals the file's 81 lines; the
`_render_sources_toml` header renders byte-equal to `schemas/sources.toml`; the `install_one`
split keeps the old control flow (present-skip, move-aside, fetch, post-install `vendor_finding`).
Whether a mise-shimmed `curl` inside an installer needs `MISE_GITHUB_TOKEN` (now stripped) to resolve is
UNVERIFIED; the image tools are locked, so no remote resolution is expected.

## Round-2 verdict

**SHIP**, from this lens. The HIGH (finding 1) is fixed, and the fix is armed (E1); every MEDIUM is
either fixed with an armed gate or a documented residual. Before or at ship, disposition the
LOW leftovers: finding 12 (`main.py:374`), N1 (bind the ordering or drop "BEFORE chezmoi" from the
description), N2, N3, the finding-6 contradictory text, and naming the finding-3 R1/R2 lifecycle
consequence in spec §4. Each is a text or one-line change, so dispositioning them does not change the
enumeration. Per the bounded-round stop condition, this round ends the loop.

Gates: lint/pytest/`verify` were not run in the shared worktree. The probes above ran against
`git archive ccfc7b85` in `/tmp/cr2`, using the worktree venv's interpreter with `PYTHONPATH` pinned to
the archive (control: `__file__` resolved under `/tmp/cr2`). `git diff ccfc7b85 --stat` at the end
showed only this report changed, and HEAD was still `ccfc7b85`.

## Round-2 evidence log (written as found)

- E1 Mutation probe on the COMMIT's tree (`git archive ccfc7b85` → `/tmp/cr2`, imported via
  `PYTHONPATH=/tmp/cr2/python/src`; control: `ncc.__file__` printed `/tmp/cr2/...`). Unmutated:
  33 passed, rc=0. Filter removed (`:144` reverted to the bare `k.startswith(...)` rule): **2 failed**
  (`test_install_fetches_https_only_and_strips_credentials`,
  `test_version_probe_switches_updaters_off_and_drops_credentials`), rc=1 — the spec's
  "Removing the filter fails 2 tests" reproduces.
- E2 Doppler env files (6 on host, names only): the ONLY `MISE_*` name in each amd64 file is
  `MISE_GITHUB_TOKEN`; proxy/cert names = 0 (control `OPENROUTER_API_KEY` = 1). Of the 21 `MISE_*`
  names the container config uses (`git grep` over `.devcontainer/` + `docker-bake.hcl`, control
  `MISE_SYSTEM_CONFIG_DIR` = 1), the credential regex matches only `MISE_GITHUB_TOKEN`, so no shim
  config name is dropped (first probe returned 0 names with a `\b` ERE; control caught it, re-run).
- E3 devcontainers spec (`docs/research/mintlify-cache/devcontainers/spec/llms-full.txt:4431`): "If any
  lifecycle script fails, subsequent scripts will not execute." `onCreateCommand` still exits non-zero
  on a vendor failure (`on-create.sh:81`), so `postCreateCommand` (`devcontainer.json:237`: ssh-auth.sock
  chown, authorized_keys = R1, known_hosts, smoke) and `postStartCommand` (`:244`, R2 chown) are skipped.
  This was UNVERIFIED in round 1; now verified from the spec text (not run live).
- E4 `main.py:374` (CLI help) at `ccfc7b85` still reads "no mise copy exists"; `main.py` is not in the
  fix diff.
- E5 CI AI-CLI block mutation (same `/tmp/cr2` tree): with `image.py`'s block replaced by main's
  pre-change loop (`for tool in claude codex gemini … FAIL: missing $tool`), `-k ai_cli` → **5 failed**,
  rc=1; unmutated they pass (E1 run). The commit message's "the pre-change loop fails all 5" reproduces.
- E6 `workflow.native-clis-container-wiring` run via the commit's own CLI on `/tmp/cr2`
  (`verify run --suite …`): unmutated 1 passed rc=0; on-create call line deleted → FAILED
  "missing 'dotfiles-setup devcontainer native-clis install) || native_rc=$?'", rc=1. All 8 tokens
  count exactly 1 in their files (`grep -F -c`; fresh invented absent token = 0).
- E7 Same suite with the install call MOVED after `chezmoi init --apply` (not deleted) → 1 passed, rc=0.
  The suite description's "calls … BEFORE chezmoi" has no enforcing token (require_tokens is presence-only).
- E8 Host native binaries (byte grep, counts only): agy `AGY_CLI_DISABLE_AUTO_UPDATE` = 1 (control
  `output-format` = 12, fresh absent = 0); claude 2.1.287 `DISABLE_AUTOUPDATER` = 8 (fresh absent = 0).
- E9 `git diff ccfc7b85 --stat` at the end: only this report modified; two other lanes' untracked reports
  appeared (`…-spec-review-…`, `…-standards-review-…`), and were not read.

## Round-2 GitHub repos touched

_None._ This repository at `ccfc7b85` / `93d70c96` / `846f2006` (main's pre-change AI-CLI block), the
local devcontainers mintlify cache (`docs/research/mintlify-cache/devcontainers/spec/llms-full.txt`),
host Doppler env-file NAME counts, and host native binary string counts. No external fetches.
