# premise-verifier — doctor devcontainer arches spec (2026-09-30)

Verbatim.

PREMISE REPORT

Lane note: I was read-only (Read/Grep/Glob only) and wrote nothing. Please persist this report verbatim to `docs/research/kb/reports/agents/`.

ROWS: 8 checked — 4 CONFIRMED (0 provenance corrected) / 0 REFUTED / 3 UNVERIFIABLE / 1 ASSUMED (1 checkable)

- **P1 — CONFIRMED.**
  - `CHECKS` is a tuple of `(name, Callable[[Setup], list[str]])` at `python/src/dotfiles_setup/doctor.py:1397-1413`.
  - `check_hk_hooks` is at `:1363-1394` and reads `_str_keys(setup.baseline.get("hk_hooks"))` at `:1370`.
  - The two citations are listed in swapped order relative to the claim. That is cosmetic.
- **P2 — CONFIRMED.**
  - The signature is `resolve_names(*, workspace, user, platform, port_override, env: dict[str, str] | None)` at `devcontainer_names.py:278-306`.
  - `DevcontainerNames.workspace_label` and `.arch_label` are `@property` at `:244-252`, returning `dotfiles.workspace=<hash>` and `dotfiles.arch=<arch>`.
  - Both are exported via `__all__` (`:79`, `:91`).
- **P3 — CONFIRMED.**
  - `teardown_container_ids` with `all_arches=False` filters on both labels via `docker ps -aq` (`devcontainer_names.py:630-640`); `-a` includes exited containers. Data-level match holds.
  - A closer precedent exists and is unlisted; see MISSING 5.
- **P4 — UNVERIFIABLE (tooling).** This is a live `mise run names` / `docker ps` measurement, and this lane has no Bash.
- **P5 — UNVERIFIABLE (tooling).** This is a live `docker inspect` measurement; no Bash.
- **P6 — UNVERIFIABLE.**
  - What the cited lines do support: `.devcontainer/devcontainer.json:44-53` and `:238-244` show postStartCommand re-chowns the socket on every `up`, and that `up` reuses the container without re-running postCreate.
  - What nothing supports: the claim that restart policy `no` is deliberate. `runArgs` (`:109-118`) has no `--restart`, so `no` is just docker's default.
  - A repo-wide grep for `RestartPolicy|restart policy|unless-stopped` matches only this spec. The grep can find matches (it found the spec itself), so the absence is real.
  - Non-blocking: the check does not depend on why the policy is `no`.
- **P7 — CONFIRMED.**
  - The comment is at `doctor.py:89-92`.
  - The test is `tests/test_doctor.py:1155-1170`, which checks that every `check_*` in the module is in `CHECKS` or `LIVE_CHECKS`.
- **A1 — ASSUMED (checkable). The code confirms it.** The chain:
  - `.claude/settings.json:125-129` (matcher `startup|resume`) runs `DOTFILES_AMBIENT_PATH="$PATH" mise -C "${CLAUDE_PROJECT_DIR:-.}" run doctor` with no `--live`.
  - `mise.toml:695` runs `uv run --project python dotfiles-setup doctor`.
  - `main.py:828-834` defines `--live` as `store_true` (default False), and `main.py:3008-3014` passes it to `doctor_main`.
  - `doctor.py:1454` runs `CHECKS + (LIVE_CHECKS if live else ())`.
  - So anything in `CHECKS` runs at SessionStart. This should have been a cited row.
  - Caveats: the hook does not fire on `clear`/`compact`, and when `CLAUDE_CODE_REMOTE=true` it runs `web-setup.sh` instead of the doctor.

MISSING:

1. **BLOCKING — the `no_platform_literals` gate rejects the §3 `doctor.toml` block.**
   - `hk.pkl:281-283` runs `dotfiles-setup platform-literals` over every tracked `.toml`/`.py` file (`platform_target.py:148`, `:527-569`).
   - `_LITERAL_RE` matches `linux/(amd64|arm64|…)(/vN)?` (`:139-143`).
   - `doctor.toml` is not exempt: it is not in `DEFAULT_LITERAL_SITES` (`:126`), the excluded prefixes (`:153-158`) or the excluded paths (`:179-183`).
   - So `platforms = ["linux/amd64", "linux/arm64"]` turns `mise run lint` red. The same applies to any such literal in `doctor.py`. `tests/` is exempt.
   - Fact for the architect: bare arch words (`"amd64"`) do not match `_LITERAL_RE`, and `resolve_names(platform="arm64")` accepts them via `platform_arch` (`:459-471`).
   - The spec must restate the interface.
2. **BLOCKING — the "platform equal to the repo's default" comparison is wrong as written.**
   - Under `mise run doctor`, `resolve_platform(None)` returns the pinned triple `linux/amd64/v2` (`mise.toml:203`; this host's gitignored `mise.local.toml:2` also pins `linux/amd64/v2`). It never returns `linux/amd64`.
   - A string-equality test would mark no platform as default, so the amd64 finding would say `MISE_ENV=amd64 mise run up`.
   - Outside mise, `resolve_platform` falls back to `host_platform()`, which is `linux/arm64/v8` on this Mac (`platform_target.py:452-456`, `:428-437`). `devcontainer_names.py:1037-1041` records this measurement. In that case arm64 becomes "default" and its restore command would be `mise run up`, which brings up amd64.
   - The spec must pin the comparison to `platform_arch(...)` and name the env source.
3. **Test hermeticity and the env seam.**
   - `Setup.environ` is the injected environment (`doctor.py:246`, `:416`), and fixtures use `environ={}` (`tests/test_doctor.py:87`).
   - With `environ={}`, `resolve_platform` falls back to the host, so the default is arm64 on the Mac and amd64 on a CI runner. Tests must put `DOTFILES_PLATFORM` in `environ`.
   - `resolve_names(env=None)` reads `os.environ` (`devcontainer_names.py:291`), so the check must pass `env`.
   - `env` is typed `dict[str, str]` while `Setup.environ` is a `Mapping`. ty will reject a direct pass, so it needs `dict(...)`.
4. **Test count.** `tests/test_doctor.py:1202` asserts `len(doctor.CHECKS) == 15`. It must become 16, with a ledger comment added at `:1171-1201`.
   - Existing idioms: a module helper replaced with `monkeypatch.setattr(doctor, "probe_tools", …)` (`:658`), or keyword injection as in `teardown_container_ids` (`devcontainer_names.py:627-628`).
   - The doctor test module is `tests/test_doctor.py`; names tests are in `tests/test_devcontainer_names.py`.
   - Every existing `run_checks`/`doctor_main` test monkeypatches `CHECKS` (`:736`, `:751`, `:758`, `:788`, `:795`, `:802`), so none will reach real docker.
   - Helpers in `doctor.py` must not be named `check_*` (P7).
5. **Unlisted, closer precedent: `sync.container_state`** (`python/src/dotfiles_setup/sync.py:529-547`).
   - It runs the same query: `docker ps -a`, both label filters, `{{.State}}`.
   - It ignores the return code. `sync._run` maps a timeout or missing binary to rc 124/127 with empty stdout (`:395-417`), so a down daemon reads as `"absent"`. That is exactly the conflation the spec's first findings row forbids.
   - The spec should add a P row naming it, and say either why it is not reused or how the rc is handled.
6. **Container name in the finding.**
   - This host's `mise.local.toml:3` pins `DEVCONTAINER_SSH_PORT="26233"` as global `[env]`. Under `mise run doctor`, `resolve_names(platform=arm64).container` would therefore end `-arm64-26233`, while P4 says the real container ends `-22975` (P4 itself is unverified).
   - The finding must use docker's `{{.Names}}`, not `names.container`.
   - A malformed port pin makes `ssh_port` raise (`devcontainer_names.py:195-207`). That surfaces as a `check crashed` finding (`doctor.py:1455-1469`), not a `devcontainers:` line.
   - Non-blocking if the finding uses `.Names`.
7. **The restore command depends on a gitignored profile.**
   - `MISE_ENV=arm64 mise run up` needs `mise.arm64.local.toml` (`mise.local.toml.example:35-43`; `AGENTS.md:166`).
   - It is present on this host and pins `linux/arm64/v8`. On a clone without it, the named command brings up amd64.
   - Non-blocking here.
8. **`doctor.toml` schema: nothing breaks from a new `[devcontainers]` section.**
   - There is no `#:schema` directive (`doctor.toml:1-15`), no taplo or tombi config file, and taplo only lints syntax (`hk.pkl:167`).
   - `workflow.doctor-wiring` checks for required tokens only (`python/verification/suites.toml:1983-1997`).
   - `plugin_remove.py:265-273` reads only `[removed_plugins]`.
   - The only problem is item 1.
9. **Clone identity.**
   - The doctor's `repo_root` is `Path(main.py).parent×4` (`main.py:3129`). `up` hashes `Path.cwd().resolve()` (`devcontainer_names.py:292-293`).
   - Both give the same hash for the main checkout.
   - A session in `.claude/worktrees/...` hashes the worktree path, so it would report "no container for this clone" for every arch. The spec does not say whether that is intended.
   - Non-blocking.
10. **`docker` on the hook's PATH is unverified.** The spec's first findings row already covers a missing binary. Non-blocking.

VERDICT: correct the spec first. MISSING 1 blocks because the §3 `doctor.toml` literals fail `no_platform_literals`, so `mise run lint` goes red. MISSING 2 blocks because the default is the `linux/amd64/v2` triple, or the host's arm64 outside mise, so equality against `linux/amd64` names the wrong restore command.

Non-blocking residuals to accept on record:
- **P4/P5:** labels are derived at runtime; P4/P5 only set live-arm expectations.
- **P6:** the rationale does not change the check.
- **A1:** the code confirms it.
- **MISSING 3-10:** implementation details with known fixes. MISSING 4 must be done, or pytest goes red.
