# Spec delta — native, self-updating claude / codex / agy in the devcontainer (2026-10-01)

This is a **delta** against `docs/specs/native-cli-installers-2026-09-30.md` rev 1. That spec lives on
branch `feat/native-cli-installers-workflow` (head `102ee0c5`) and is not on `main`. This delta covers only
the image and CI half (§2c, §2d, §2f, §3c, §3e, §5 D1–D6). Ray's rulings of 2026-10-01 are authoritative
and override that spec wherever the two differ.

## Rulings (Ray, 2026-10-01, AskUserQuestion)

1. The Mac **and** the devcontainer get the native installers for claude, codex **and** agy. No mise or npm
   install of any of the three exists anywhere.
2. Inside the image they **self-update, like the Mac**. This supersedes the rev-1 parts that pinned or
   switched off updates:
   - §3e "pinned + verified, `/usr/local/lib/<tool>/<pin>`";
   - Q10 (`DISABLE_AUTOUPDATER=1`, codex updater off);
   - C8 "Image: pinned artifacts";
   - the smoke assertion "`--version` contains the pin".

   Smoke asserts **provenance** instead. Agy in the image is new scope.
3. Supply chain: https-only, the vendor's official installer, and every verification recorded. Do not weaken
   an existing verification.
4. **Rev 1 rulings (Ray, 2026-10-01, AskUserQuestion, after premise review):**
   - **claude: run the vendor `install.sh` as-is.** The installer checks the binary's sha256 against a
     same-origin, unsigned manifest. Ray accepted this over the offered GPG manifest verify, which was
     probed working: key `31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE`, good signature rc 0, one-byte tamper
     BAD rc 1. This is an explicit, accepted exception to ruling 3 (see §4).
   - **Installed-version record: defer to the host ledger** (spec rev 1 R2, `docs/receipts/<tool>/<v>.md`,
     owned by session `dotfiles-20261001.000`). The container writes no receipt of its own.

## Revision 1 (2026-10-01) — premise-verifier findings applied

The report is at `docs/research/kb/reports/agents/2026-10-01-premise-verifier-native-cli-devcontainer.md`.

- **MISSING-1 (blocker).** The chezmoi-managed `home/dot_local/bin/executable_claude` wrapper
  (`exec mise exec claude-code -- claude`) sat at the native path. It is **deleted**. `install` now treats
  any non-vendor file at `~/.local/bin/<tool>` as stale: it **moves it aside** to `.<tool>.pre-native`
  (never deletes) and runs the vendor installer, which migrates every existing home volume. `.chezmoiremove`
  was rejected because it would delete the native symlink on every apply.
- **MISSING-2 (blocker).** `schema_vendor` gains `_VENDORED_PIN_TOOLS = {claude-code, codex}`, used by both
  `check_drift` and `refresh`; the header text in `sources.toml` is regenerated.
- **MISSING-3.** Installers inherit `MISE_*` (no credentials) so the container's mise-shim `curl` resolves.
  The in-container run through the real `on-create.sh` path is §5 D-oc.
- **MISSING-5.** agy is `flat`: it must be a regular file, not a symlink, at `~/.local/bin/agy`.
- **MISSING-6.** The stale docs are fixed: `mise.toml` comment, `.github/workflows/AGENTS.md`,
  `TOOL-PERSISTENCE.md`, `ai.py`.
- **D1-ctl.** rc 56 is what was measured (`curl: (56) The requested URL returned error: 404`, curl on
  macOS). It is recorded as observed, not as the documented `-f` rc of 22.

## 1. Objective

| CLI | Devcontainer (after) | CI runner (after) |
|---|---|---|
| claude | The vendor installer `https://claude.ai/install.sh`, run at container **create** as the container user. It produces `~/.local/bin/claude` → `~/.local/share/claude/versions/<v>` in the home volume and self-updates. | Unchanged: `setup-claude-code`. |
| codex | `https://chatgpt.com/codex/install.sh` with `CODEX_NON_INTERACTIVE=1`. It produces `~/.local/bin/codex` → `~/.codex/packages/standalone/current/bin/codex` and self-updates. | **None**, because pytest does not need it. That was measured, §5 P-CI. |
| agy | `https://antigravity.google/cli/install.sh`. It produces a flat binary `~/.local/bin/agy` and self-updates. | None. `eval_cases.py:44` already passes without agy. |

## 2. Files

| Path | Action |
|---|---|
| `.config/mise/conf.d/shared.toml` | Delete the npm codex comment and pin. This is a **base-image input** (`Dockerfile:139`), so the PR runs a **cold base rebuild** (~2.5 h, inherited figure). |
| `.config/mise/mise.lock` | Drop the `npm:@openai/codex` block via `mise run lock-shared` (skill `lock-shared`). |
| `.devcontainer/mise-runtime.toml` | Delete `claude-code = "latest"` and its stale "http:claude backend" comment. Keep gemini. |
| `.devcontainer/mise-system.lock`, `.devcontainer/mise-runtime.lock` | Regenerate via `mise run lock-image` (skill `lock-image`). |
| `.devcontainer/mise-system.toml` | Rewrite the stale comment that tells you to "run `claude install` in Dockerfile.host-user" so it points at `on-create.sh` and the new module. |
| `python/src/dotfiles_setup/native_clis_container.py` | **NEW.** It provides `install` (missing tools only; https-only `curl --proto =https` to a file, never piped; minimal env) and `check` (provenance). |
| `python/src/dotfiles_setup/main.py` | Add `devcontainer native-clis {install,check}`. |
| `.devcontainer/scripts/on-create.sh` | Call `native-clis install` **before** `chezmoi init --apply`. The agy installer appends a PATH line to `~/.bashrc`/`~/.profile` unconditionally (measured), and so does codex when another codex is on PATH. Both files are chezmoi-managed, so the `--force` apply that follows restores them. Bash budget 74 → +N with justification. |
| `scripts/devcontainer-smoke.sh` | Tier 3: call `native-clis check`. Bash budget +N. |
| `python/src/dotfiles_setup/bash_budget.py` | The two budget bumps, each with a one-line justification. |
| `python/src/dotfiles_setup/image.py` | CI no-mount smoke: `claude`/`codex` leave the "must exist" list (the image no longer carries them) and **must be absent** from the image (`command -v` fails), alongside `agy`. `gemini` stays present. |
| `python/src/dotfiles_setup/schema_vendor.py` | Drop the `_PIN_RESOLVERS["codex"]` shared.toml resolver. codex joins claude-code as a **vendored** pin: `sources.toml` `version` IS the pin. |
| `schemas/sources.toml` | Codex `pin_source` becomes vendored. `version` is unchanged (0.154.0; the source URL is unversioned). |
| `tests/test_schema_vendor.py` | Change the fixture to the vendored form. |
| `.github/workflows/ci.yml` | Delete `MISE_DISABLE_TOOLS: ""` and its comment, and fix the "Install mise" comment that lists codex. **No `setup-codex`** (§5 P-CI). |
| `mise.toml` | Remove `"npm:@openai/codex"` from `disable_tools` and its comment. It becomes dead once shared.toml drops the pin. **Keep** `antigravity-cli`: PR #1505 and the host session own it. |
| `tests/test_native_clis_container.py` | **NEW** unit tests, both arms. |
| `home/dot_local/bin/executable_claude` | **DELETE** (rev 1, MISSING-1). |
| `tests/test_script_guard.py`, `script_guard.py` | The existing-file test no longer depends on the wrapper as its fixture. It builds its own fixture with a control arm. |
| `tests/test_shell_integration.py`, `tests/conftest.py` | `codex` login-shell params become `host_only`, the same as `claude` (§5 P-CI). |
| `.claude/CLAUDE.md`, `.devcontainer/AGENTS.md` | Docs. |

**Not changed, with reasons:**

- `doctor.toml [claude]` stays `enabled = true`, `expected_install_method = "native"`. In the D5 container,
  `claude doctor` reports `Running: native`, `Config install method: native`, "No installation issues
  found", so the method does not differ.
- `pin-parity.toml`: with no image pin, codex has exactly one pin site (`schemas/sources.toml`). A
  single-site parity row asserts nothing.
- No `setup-codex` composite (§5 P-CI).
- No host doctor check: session `dotfiles-20261001.000` owns the host side.

## 3. Interfaces

```
dotfiles-setup devcontainer native-clis install   # rc 0 all present; else the first installer/fetch rc
dotfiles-setup devcontainer native-clis check     # rc 0 native; 1 any finding (each logged "FAIL: …")
```

`check` reports a finding when any of these holds:

- `command -v <tool>` ≠ `~/.local/bin/<tool>`;
- the realpath is outside the vendor root (`~/.local/share/claude/versions`, `~/.codex/packages/standalone`,
  `~/.local/bin/agy`);
- `<tool> --version` rc ≠ 0. This probe runs with a minimal env plus `DISABLE_AUTOUPDATER=1` and
  `AGY_CLI_DISABLE_AUTO_UPDATE=true`, scoped to the probe;
- a `mise ls --current --json` key normalises to `claude`, `claude-code`, `codex`, `agy`, `antigravity` or
  `antigravity-cli`.

## 4. Constraints

- **Self-update stays ON in the image.** The probe-only switches never reach the tools' normal runs.
- **An existing tool is never reinstalled.** On an existing volume the self-updater owns it, which is ruling 2.
- **Fail loud.** A failed install fails `onCreateCommand`, the same as the overlay `mise install`.
- **No new `.sh` files and no `curl | sh`.** Logic lives in python; bash grows only by thin call lines.
- **Installers never see the container's Doppler credentials.** Their env is `HOME PATH USER LOGNAME LANG
  SHELL TMPDIR` plus every `MISE_*` (rev 1), plus `CODEX_NON_INTERACTIVE=1` for codex.
- **What each installer verifies**, read from the installer sources fetched 2026-10-01:

  | Installer | Verification it performs | Replaced mechanism |
  |---|---|---|
  | claude | sha256 of the binary against `downloads.claude.ai/.../<v>/manifest.json`, same origin, unsigned in the script | image `aqua:anthropics/claude-code`, a lock-time TOFU sha256 |
  | codex | sha256 against `codex-package_SHA256SUMS` / release metadata | `npm:@openai/codex` under bun; the lock recorded the **version only** |
  | agy | sha512 against a same-origin platform manifest | none (agy was never in the image) |

  Net effect:
  - claude moves from a lock-time sha256 (pinned in git) to an install-time same-origin sha256. **This
    weakens** the image's recorded checksum. Ray accepted it explicitly as ruling 4, over the offered
    GPG-verified manifest.
  - codex **gains** a checksum.
  - The updaters' own verification is the vendors'. Spec rev 1 §C9 records what is known.

## 5. Verification

**Gates:** lint, pytest, verify, pin-actions, lint-docs; rule-sync (`.claude/CLAUDE.md`); `mise run
verify-container-latest` after CI publishes `pr-NNN` (`mise run sync -- --tag pr-NNN`).

**Local-devcontainer-first proofs.** Throwaway `docker run --rm` on the local overlay images built from the
published `:dev` (`vsc-dotfiles-273897ea-{amd64,arm64}`), as UID 1000, with a **fresh** named home volume.

| # | Proof | Result |
|---|---|---|
| D1' | The three vendor installers, amd64 | Each exits rc 0. claude 2.1.287 → `~/.local/share/claude/versions/2.1.287`; codex 0.160.0 → `~/.codex/packages/standalone/releases/0.160.0-x86_64-unknown-linux-musl`; agy 1.2.14 flat. Each `--version` exits rc 0. |
| D1'' | The same, arm64 | Each exits rc 0. claude 2.1.287; codex 0.160.0 → `…/0.160.0-aarch64-unknown-linux-musl`; agy 1.2.14. Each `--version` exits rc 0. |
| D-oc | `mise run up` for this worktree: the real `on-create.sh` → `native-clis install` path | see the PR body |
| D1-ctl | A bogus installer URL (`antigravity.google/cli/install-bogus-xq7.sh`) | curl rc 56 (HTTP 404): fetch failure is loud |
| D3' | `native-clis check` against a stale shadow (a non-native `~/.local/bin/codex`) and against a mise copy | must FAIL; native must PASS (unit tests plus an in-container run) |
| D5 | `claude doctor` in the D1' container | `Running: native (2.1.287)`, `Config install method: native`, "No installation issues found" |
| rc-edit | rc files before and after the installs | agy appended a PATH export to `.bashrc` and `.profile`; codex appended to `.profile` (because the image's npm codex was on PATH) |
| P-CI | the full pytest suite on the Mac host with codex, claude and agy **absent** from PATH | 4,404 passed, 1 failed (`test_zshenv_path_injection`, `host_only`, tripped by the stripped PATH itself). **Weak arm:** `bash -l` re-adds `~/.local/bin`. Code reading names the only CI codex consumers: the two `codex` params in `test_shell_integration.py`, now `host_only`. So there is no `setup-codex`. |

## 6. Commit

One PR, `feat(devcontainer): native self-updating claude/codex/agy; drop mise/npm copies`. The body states
the cold base rebuild and the verification table.

## 7. PREMISES

| # | Premise | Provenance |
|---|---|---|
| P1 | shared.toml pins npm codex, and it is a base-image input | `.config/mise/conf.d/shared.toml:44`; `.devcontainer/Dockerfile:139` |
| P2 | mise-runtime pins `claude-code = "latest"` | `.devcontainer/mise-runtime.toml:63` |
| P3 | The home is a named volume mounted over `/home/<user>` | `.devcontainer/devcontainer.json` `mounts` |
| P4 | `onCreateCommand` runs `on-create.sh` as the user, after the mount and before postCreate smoke | `devcontainer.json` `onCreateCommand`/`postCreateCommand` |
| P5 | `.bashrc` and `.profile` are chezmoi-managed, and on-create applies with `--force` | `home/dot_bashrc.tmpl`, `home/dot_profile.tmpl`; `on-create.sh` `chezmoi init --apply … --force` |
| P6 | `~/.local/bin` precedes the mise shims on the container PATH | `.devcontainer/Dockerfile.host-user` `ENV PATH` |
| P7 | The CI no-mount smoke requires claude/codex today | `python/src/dotfiles_setup/image.py` "AI CLI checks" |
| P8 | The codex schema pin resolves from shared.toml | `schema_vendor.py` `_PIN_RESOLVERS["codex"]` |
| P9 | CI re-enables npm codex | `.github/workflows/ci.yml` `MISE_DISABLE_TOOLS: ""` |
| P10 | `doctor.toml [claude]` expects `native` | `doctor.toml:265` |
| P11 | The agy installer runs `agy install` with no flags; that edits rc files; `--skip-path` exists but is unreachable through install.sh | installer source (fetched 2026-10-01); `agy install --help` in the D1' container |
