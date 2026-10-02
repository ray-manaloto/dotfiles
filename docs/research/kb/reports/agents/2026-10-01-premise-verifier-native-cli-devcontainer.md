# premise-verifier — native-cli-devcontainer-2026-10-01.md (rev 0 of the delta)

Persisted verbatim at receipt by the coordinator (the agent had no write tools).

PREMISE REPORT — native-cli-devcontainer-2026-10-01.md (worktree feat/native-cli-devcontainer)
(Note: I have no write tools, so this report is not persisted — please save it verbatim under docs/research/kb/reports/agents/.)

ROWS: 11 checked — 9 CONFIRMED / 0 REFUTED / 2 UNVERIFIABLE / 0 ASSUMED (1 CONFIRMED with a usage-context caveat)

| # | Verdict | Evidence |
|---|---|---|
| P1 | CONFIRMED | `.config/mise/conf.d/shared.toml:44` `"npm:@openai/codex" = { version = "0.154.0", allow_builds = [...] }`; `.devcontainer/Dockerfile:139` `COPY .config/mise/conf.d/shared.toml /usr/local/share/mise/conf.d/shared.toml` |
| P2 | CONFIRMED | `.devcontainer/mise-runtime.toml:63` `claude-code = "latest"`; stale comment `:59` (and `:60-62` codex comment) |
| P3 | CONFIRMED | `devcontainer.json:129` `source=${localEnv:DEVCONTAINER_HOME_VOLUME},target=/home/${localEnv:USER},type=volume` |
| P4 | CONFIRMED (config) | `devcontainer.json:236` onCreate → `bash …/on-create.sh`; `:237` postCreate ends `scripts/devcontainer-smoke.sh`; `remoteUser` `:119`. "Runs as the user" = devcontainer-CLI semantics, not repo-readable |
| P5 | CONFIRMED | `home/dot_bashrc.tmpl`, `home/dot_profile.tmpl` exist; `on-create.sh:41` `chezmoi init --apply --source=… --no-tty --force` |
| P6 | CONFIRMED w/ context caveat | `Dockerfile.host-user:77` `PATH="/home/$U/.local/bin:/home/$U/.local/share/mise/shims:${PATH}"`. Caveat: `check`/`install` run under `uv run` launched via a mise shim; if mise's shim exec prepends tool install dirs (not verified here), the PATH the module sees differs from the login PATH |
| P7 | CONFIRMED | `image.py:1043-1046` `for tool in claude codex gemini; do command -v "$tool" … FAIL: missing` |
| P8 | CONFIRMED | `schema_vendor.py:121` `"codex": lambda root: _read_shared_toml_pin("npm:@openai/codex", root)`; `schemas/sources.toml:47` pin_source = shared.toml |
| P9 | CONFIRMED | `ci.yml:72` `MISE_DISABLE_TOOLS: ""` (comment `:69-71`); "Install mise" comment naming codex `ci.yml:218` |
| P10 | CONFIRMED | `doctor.toml:265` `expected_install_method = "native"`, `:271` `enabled = true` |
| P11 | UNVERIFIABLE | cites external installer source + in-container `--help`; nothing in repo settles it |
| §1 `eval_cases.py:44` | CONFIRMED (off-by-one) | degradation docstring `:43-44`; `DECLARED_LANES = ("codex", "agy")` `:45` |
| §2 bash budget 74 | CONFIRMED | `bash_budget.py:67-68`; smoke 163 `:88-91` (script ~161 lines) |
| §2 mise-system.toml stale comment | CONFIRMED | `mise-system.toml:412-413` "run `claude install` in Dockerfile.host-user" |
| §2 mise.lock codex block | CONFIRMED | `.config/mise/mise.lock:531-536`; also `.devcontainer/mise-system.lock:4963-4968` |
| §2 pin-parity no codex row | CONFIRMED | `pin-parity.toml` `[tools.*]` = graphify, chezmoi, hk, claude-code, mise (`:46-123`) |
| §2 main.py "Add native-clis" | ALREADY DONE | `main.py:17,364-371,2275` already wired; `tests/test_native_clis_container.py:232` exercises it |
| §5 D1-ctl "curl rc 56 (HTTP 404)" | UNVERIFIABLE/suspect | with `-f`, curl returns 22 for HTTP ≥400; rc 56 = receive failure — re-check the receipt |
| §5 D1'', P-CI | UNVERIFIABLE | "see receipt"; no receipt yet |

MISSING (unstated premises):

1. **[LOAD-BEARING, BLOCKS DISPATCH] chezmoi-managed `~/.local/bin/claude` wrapper.** `home/dot_local/bin/executable_claude:3` = `exec mise exec claude-code -- claude "$@"`, and `home/.chezmoiignore` does not exclude `.local/bin` on linux. On a FRESH volume: native install runs first, then `chezmoi … --force` (`on-create.sh:41`) OVERWRITES the native symlink with this wrapper → `check` fails "outside the vendor root", and the wrapper calls a `claude-code` mise tool that no longer exists. On EXISTING volumes (all of them have the wrapper): `install_one` sees `target.exists()` and skips claude ("its self-updater owns it") → never installed. Spec must delete `executable_claude` AND migrate existing volumes (`.chezmoiremove` or install replacing a non-vendor file) — deleting the source alone does not remove the target on existing volumes. Also touches `tests/test_script_guard.py:203-215` (uses that file as fixture; skips if absent) and `script_guard.py:178` comment.
2. **[LOAD-BEARING] Schema-vendor: dropping the resolver is not enough.** `check_drift` (`schema_vendor.py:195`) and `refresh` (`:417`) special-case ONLY `entry.tool == "claude-code"` as vendored; with the codex resolver gone, codex hits "could not resolve the current pin…" → `config.schema-vendor-drift` (verify) FAILS, and refresh logs error + skips codex. Both branches need codex added; the generated header text (`:274-282`, `sources.toml:5-9`) and `tests/test_schema_vendor.py:437,462` (fixture + `refresh(...) == ["codex"]`) need updating.
3. **[UNVERIFIABLE, load-bearing for `install`] Installer env/PATH context.** D1' ran the vendor installers by hand; the module runs them with `PATH` but no `MISE_*` vars (`_ENV_PASSTHROUGH`, `native_clis_container.py:48`) and resolves `curl` via `shutil.which` (`:152`). The runtime tier declares `"conda:curl" = "latest"` (`mise-runtime.toml:38`), whose shim at `/usr/local/share/mise/shims` precedes `/usr/bin/curl` (apt, `mise-system.toml:158`). Under the uv/mise-shim launch, `which curl` may yield a conda curl (CA bundle unknown) or a shim that — with `MISE_ENV=runtime` stripped — cannot see the runtime tier; the installers' own internal `curl` calls inherit the same env. Only an in-container run of `native-clis install` through on-create's real invocation settles this; D3' only covers `check`.
4. **`uv run` at onCreate before chezmoi (question c)** — plausible, unproven: on-create.sh runs no uv today. For: `chezmoi` (a shared.toml tool) already resolves via the system shim at the same moment (`on-create.sh:41`), so `uv` (`shared.toml:54`) should too; venv goes to `UV_PROJECT_ENVIRONMENT=/home/$U/.venvs/dotfiles-python` (`devcontainer.json:152`); the one git dep is knowledge-base over https (`pyproject.toml:40`, public per `ci.yml:206`) so no credentials/chezmoi gitconfig needed; build backend is plain setuptools (`pyproject.toml:48-49`) so no uv git call in the workspace (#1183 safe.directory not needed). Gaps: the spec must give a cwd (smoke uses `cd "${WORKSPACE_FOLDER}" && uv run --project python …`, `devcontainer-smoke.sh:40`); first uv sync now moves into onCreate (network + latency).
5. **agy provenance check is vacuous for symlinks** (`native_clis_container.py:217-219`): with `install_root=".local/bin/agy"`, the root resolves through the same symlink as the binary, so `real == root` always — a symlink `~/.local/bin/agy` → a mise/npm tree passes. No test covers it (tests `:96-110` only missing/rc≠0). Spec §3 says "realpath inside vendor root"; needs a "regular file, not a symlink" assertion.
6. **Unlisted stale refs (non-blocking docs):** `mise.toml:118-125` (codex comment, separate from the disable_tools comment `:163-171`); `.github/workflows/AGENTS.md:125` ("pytest shells out to … codex"); `.devcontainer/TOOL-PERSISTENCE.md:96`; `ai.py:23-29` ("installed declaratively through mise"; only manually invoked, `main.py:2791`); `audit.py:562-593` (report-only, not a gate).
7. **Checked and CLEAR (question a):** tier-1 exact tool-set is derived from the three configs (`image.py:253-280`, `:2035-2061`) so it follows the edits automatically; `hk-image.pkl`, `renovate.json`, `docker-bake.hcl`, the Dockerfiles, `currency.toml` (comments only, `:31-37`) have no codex/claude refs; suites.toml has no contract tokenizing `claude-code`/`npm:@openai/codex` in the edited files; `tests/test_image_smoke.py` asserts nothing about the claude/codex/gemini loop (`:871`/`:1002` only assert the heading is absent from tier scripts); in-container codex callers (`codex_schema.py:28`, `sdlc_team.py:707-712`, plugin_* via `mise exec -- codex`) are mocked in tests and `mise exec -- codex` falls through to the PATH codex at runtime; the bootstrap gap report covers apt packages only (`build-publish.yml:1006-1022`); nothing reads `disable_tools` in python/tests (only a comment `sdlc_team.py:700`).
8. **Question b (other container reliance):** only item 1; `home/` has no other claude/codex/agy reference; no `dot_codex`.

Module vs spec (beyond item 5): CLI already in main.py (spec §2 says "Add"); `install` continues past a failure and returns the first rc — also can return 127 (no curl) / 1 (rc0 but no binary), broader than spec §3 wording but compatible; `mise_findings` runs with full environ, probe with minimal env (as specced).

VERDICT: CORRECT SPEC FIRST — blocked by MISSING-1 (chezmoi `executable_claude` wrapper overwrites/blocks native claude on both fresh and existing volumes) and MISSING-2 (schema_vendor's claude-code-only vendored branches would make the verify drift check fail for codex). MISSING-3 requires an in-container run of `native-clis install` through the real on-create path before relying on D1'. Non-blocking residuals: P11 (external installer behaviour — measured in-container per spec), D1''/P-CI (receipts pending), D1-ctl rc 56 inconsistency (re-check receipt), items 4–6.

## GitHub repos touched

_None._ (all reads were local to the worktree)
