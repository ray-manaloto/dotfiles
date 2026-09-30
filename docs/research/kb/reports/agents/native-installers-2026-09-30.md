# Native install + update channels: agy, codex, claude (2026-09-30)

Lane: research (in-lane `research-sweep` steps). Writes only this file.
Status: COMPLETE (written incrementally; see §9 for verification).

Question: for each of agy (Google Antigravity CLI), codex (OpenAI Codex CLI), claude (Claude Code),
what is the OFFICIAL native install + update channel — install command, update command / self-update,
install location, macOS + linux (amd64/arm64) support, checksum/signature verification (vs mise
aqua/npm backends verified against mise.lock), pin/rollback, and env vars that disable self-update?

## 0. Measured host state (2026-09-30, mise 2026.9.18 macos-arm64)

| Tool | `which -a` first hit (main checkout cwd) | Native location | Native version | `mise latest` |
|---|---|---|---|---|
| agy | `~/.local/share/mise/installs/antigravity-cli/1.2.13/agy` (mise, repo pin 1.2.14 not yet installed) | `~/.local/bin/agy` — a 172 MB regular file, mtime 2026-08-12 | **1.1.12** (stale) | antigravity-cli -> 1.2.14 |
| codex | `~/.local/share/mise/shims/codex` (host `disable_tools = ["npm:@openai/codex"]`) | `~/.local/bin/codex` -> `~/.codex/packages/standalone/current/bin/codex` -> `releases/0.159.2-aarch64-apple-darwin` | 0.159.2 | codex / npm:@openai/codex -> 0.159.2 |
| claude | `~/.local/bin/claude` | symlink -> `~/.local/share/claude/versions/2.1.285` (2.1.283/284/285 retained) | 2.1.285 | claude / claude-code -> 2.1.285; npm:@anthropic-ai/claude-code -> **2.1.286** |

mise registry backends (`mise registry <t>`): `antigravity-cli` = `aqua:google-antigravity/antigravity-cli`;
`claude` / `claude-code` = `aqua:anthropics/claude-code http:claude`; `codex` = `aqua:openai/codex npm:@openai/codex`.

_Sections below are filled as each source is read._

## 1. Every mise hit, classified HOST / IMAGE / CI (worktree HEAD, tracked files + user-global)

Probe: `git grep` over every tracked mise config/lock (`mise.toml`, `mise.lock`, `.config/mise/conf.d/shared.toml`,
`.config/mise/mise.lock`, `.devcontainer/mise-{system,runtime}.{toml,lock}`) plus `~/.config/mise/config.toml`.
Control arm: the same grep shape finds `hk = "2.3.0"` at `shared.toml:37`, so the probe can hit. (A first attempt with a
`conf.d/*.toml` glob aborted under zsh `no matches found` BEFORE grep ran — a probe that could only report absence; re-run
glob-free.)

| # | Site | Entry | Class | Lock verification today |
|---|---|---|---|---|
| H1 | `mise.toml:126` | `antigravity-cli = "1.2.14"` | HOST (root mise.toml is in the image's `MISE_IGNORED_CONFIG_PATHS`, per `mise.toml:114`) | `mise.lock:4491-4548` — aqua, per-platform `checksum = "sha256:…"` + GitHub release URL (11 platforms incl. linux-x64/arm64, macos-arm64/x64) |
| H2 | `~/.config/mise/config.toml:142` (user-global, outside repo review) | `antigravity-cli = { version = "1.2.14", minimum_release_age = "0s" }` | HOST | user-global `~/.config/mise/mise.lock` |
| H3 | `mise.toml:169` | `disable_tools = ["npm:@openai/codex"]` | HOST (host already runs native codex; comment: "CI re-enables it with MISE_DISABLE_TOOLS=\"\"") | n/a |
| S1 | `.config/mise/conf.d/shared.toml:44` | `"npm:@openai/codex" = { version = "0.154.0", allow_builds = [...] }` | **SHARED → IMAGE + CI** (host disables it via H3) | `.config/mise/mise.lock:531-536` and `.devcontainer/mise-system.lock:4963-4968` — **version + options only, NO checksum field** |
| I1 | `.devcontainer/mise-runtime.toml:63` | `claude-code = "latest"` (comment at :59 says "http:claude backend" but the lock says aqua) | IMAGE | `.devcontainer/mise-runtime.lock:583-615` — `backend = "aqua:anthropics/claude-code"`, version 2.1.283, per-platform sha256 |
| C1 | `.github/actions/setup-claude-code/action.yml:44-45` | NOT mise: `curl -fsSL https://claude.ai/install.sh \| bash -s "$version"`, version read from `schemas/sources.toml` | CI (already native) | installer's own manifest checksum (see §3) |
| — | `mise.toml:27-39` | comment only: "deliberately NO claude-code entry here" | HOST (already native since `6d1ae23`) | — |
| — | `mise.toml:55` | `"npm:claude-code-lint"` — a different tool (linter), not Claude Code | out of scope | — |

Consequence for the approved edit set (user: remove antigravity-cli, codex, claude mise pins): only **H1, H2, H3** are
HOST-only. **S1** feeds the image (`mise-system.lock`) and CI (`ci.yml` sets `MISE_DISABLE_TOOLS=""`), and **I1** feeds the
image runtime tier — per the task rule these need a native install path PROVEN inside the image / on a runner before removal.
Note H3 (`disable_tools`) becomes dead once S1 is gone and should be removed in the same change, not left dangling.

## 2. claude (Claude Code) — native installer

Sources: `$CC/setup.md` (KB offline corpus, snapshot 2026-09-15; `$CC` = `knowledge-base/sources/agent-harness-docs/docs/claude-code`),
`$CC/env-vars.md`, and the LIVE installer fetched (not executed) 2026-09-30: `https://claude.ai/install.sh` → 302 →
`https://downloads.claude.ai/claude-code-releases/bootstrap.sh`, 260 lines, sha256 `3a68d340…a944`.

| Aspect | Finding | Evidence |
|---|---|---|
| Install | `curl -fsSL https://claude.ai/install.sh \| bash` (optional arg `stable` \| `latest` \| `X.Y.Z`) | `$CC/setup.md:45,302,324,346`; bootstrap.sh:6-11 validates the arg against `^(stable\|latest\|[0-9]+\.[0-9]+\.[0-9]+(-…)?)$` |
| How the script works | downloads the **latest** binary to `~/.claude/downloads/`, checks its sha256, then runs `"$binary_path" install ${TARGET}` — i.e. the binary itself installs the requested version/channel, then the bootstrap copy is deleted | bootstrap.sh:148-149 "Always download latest version (which has the most up-to-date installer)"; :226, :229 |
| Location | launcher `~/.local/bin/claude` = symlink into `~/.local/share/claude/versions/<ver>`; old versions retained (host has 2.1.283/284/285) | `$CC/setup.md:205`; host `ls -la ~/.local/bin/claude` |
| Update | **self-updates in the background** (native); manual `claude update` (alias `upgrade`); `claude install [target] [--force]` | `$CC/setup.md:67,197,284`; live `claude update --help`, `claude install --help` |
| Channel | `autoUpdatesChannel`: `"latest"` (default) or `"stable"` (~1 week old, skips major-regression releases); `minimumVersion` floor; managed `requiredMinimumVersion`/`requiredMaximumVersion` | `$CC/setup.md:227-261`. Live channel pointers 2026-09-30: `…/claude-code-releases/latest` = **2.1.286**, `…/stable` = **2.1.285** |
| Disable self-update | `DISABLE_AUTOUPDATER=1` (background only; `claude update`/`install` still work); `DISABLE_UPDATES=1` (blocks ALL incl. manual); `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` also disables auto-updates (and much else — any value incl. `0`) | `$CC/env-vars.md:408,428,256`; `$CC/setup.md:265-277` |
| Pin / rollback | `bash -s 2.1.89` at install, or `claude install <ver>`; retained `versions/` dir means a rollback is a re-point; a custom launcher at `~/.local/bin/claude` is respected (since v2.1.207 the updater no longer overwrites it) | `$CC/setup.md:205-209,346` |
| macOS | darwin-arm64, darwin-x64 (Rosetta shell → arm64 binary); binaries **codesigned "Anthropic PBC" + notarized** | bootstrap.sh:128-133; `$CC/setup.md` "Platform code signatures" |
| Linux | linux-x64, linux-arm64, and `-musl` variants (musl auto-detected); binaries NOT individually signed; signed apt/dnf/apk repos at `downloads.claude.ai/claude-code/{apt,rpm,apk}/{stable,latest}` (no auto-update — upgrade via the package manager) | manifest platform keys (below); bootstrap.sh:136-144; `$CC/setup.md:365-454` |
| Root/sudo | refuses `sudo` from a user shell unless `CLAUDE_INSTALL_ALLOW_SUDO=1`; plain root (containers/CI) is fine | bootstrap.sh:14-36 |

### Verification (claude) — measured, both arms

- **Installer**: fetches `…/<version>/manifest.json` and compares the binary's sha256 against
  `platforms.<platform>.checksum`, aborting on mismatch (bootstrap.sh:158-217). It does **NOT** verify the manifest's GPG
  signature — manifest and binary come from the same origin over TLS, so this detects corruption, not an origin compromise.
  The version actually installed is fetched by the binary's own `install` subcommand (closed source) — whether THAT path
  checks the manifest signature is **unverified** (gap).
- **Out-of-band signed manifest** (manual, documented at `$CC/setup.md:481-560`): key
  `https://downloads.claude.ai/keys/claude-code.asc`, fingerprint `31DD DE24 DDFA B679 F42D 7BD2 BAA9 29FF 1A7E CACE`.
  Measured in an isolated `GNUPGHOME`: 2.1.285 `gpg --verify manifest.json.sig manifest.json` → `Good signature … rc=0`;
  **control arm** — the same sig over a manifest with one appended byte → `BAD signature`. The installed host binary
  `~/.local/share/claude/versions/2.1.285` sha256 `51f09bd1…6db4` **MATCHES** `platforms["darwin-arm64"].checksum`.
  `manifest.json.sig` for 2.1.285 → HTTP 200; for bogus `9.9.999` → 404 (the probe discriminates). Signatures exist from 2.1.89 on.
- Manifest platform keys (2.1.285): `darwin-arm64 darwin-x64 linux-arm64 linux-arm64-musl linux-x64 linux-x64-musl win32-arm64 win32-x64`.
- **vs mise**: IMAGE pin I1 uses `aqua:anthropics/claude-code` whose `mise-runtime.lock` entry carries a per-platform sha256 of
  the **GitHub release tarball** (`claude-linux-x64.tar.gz`) — a TOFU checksum recorded at lock time, stronger than the
  installer for reproducibility (pinned bytes) but not tied to Anthropic's GPG key. The native path's strongest form is
  "pin version + verify signed manifest + sha256 the binary" — the installer does only the last two-thirds implicitly
  (checksum, not signature). A CI/image recipe wanting parity with mise.lock should verify the `.sig` explicitly.

Latest: `mise latest claude` = 2.1.285 (aqua/GitHub releases), `mise latest npm:@anthropic-ai/claude-code` = 2.1.286,
Anthropic `latest` pointer = 2.1.286 — the aqua/GitHub route lagged the vendor pointer by one release at probe time.

## 3. codex (OpenAI Codex CLI) — standalone installer

Sources: `$KB/codex/config-file__environment-variables.md:17-38`, `$KB/codex/cli__reference.md:296-298`,
`$KB/codex/config-file__config-reference.md:186-189` (`$KB` = `knowledge-base/sources/agent-harness-docs/docs`);
LIVE installer fetched (not executed) 2026-09-30: `https://chatgpt.com/codex/install.sh` → redirected to
`https://releases.openai.com/codex/install.sh`, 1305 lines, sha256 `150e3cf6…28bf6`; source at tag **rust-v0.159.2**
(latest stable, 2026-09-29T23:57Z; newer tags are prereleases `rust-v0.160.0-alpha.6.1`, `rust-v0.161.0-alpha.3/.4`):
`codex-rs/app-server-daemon/src/{update_loop.rs,settings.rs,lib.rs}`, `codex-rs/tui/src/updates.rs`,
`codex-rs/cli/src/doctor/updates.rs`. Prior local report: `codex-native-installer-status-2026-09-23.md`.

| Aspect | Finding | Evidence |
|---|---|---|
| Install | `curl -fsSL https://chatgpt.com/codex/install.sh \| CODEX_NON_INTERACTIVE=1 sh` (optional `--release X.Y.Z` or `CODEX_RELEASE`) | env-vars doc :38; install.sh:5-6, :86-101 |
| Download source | prefers `releases.openai.com/codex` (`CODEX_INSTALLER_USE_RELEASES_OPENAI_COM=0` → GitHub Releases), falls back to GitHub on failure | install.sh:8-10, :178-205, :425 |
| Location | package `${CODEX_HOME:-~/.codex}/packages/standalone/releases/<ver>-<target>/`, `current` symlink, `auto-update-version` marker; launcher `${CODEX_INSTALL_DIR:-~/.local/bin}/codex` (+ `codex-code-mode-host` on macOS) | install.sh:16-35; host `ls ~/.codex/packages/standalone` (9 releases retained, 0.151.0 → 0.159.2) |
| Shell rc edit | appends a marked PATH block to `~/.zprofile`/`.bash_profile` (macOS) or `~/.zshrc`/`.bashrc` (linux) / `~/.profile` | install.sh:575-628 — relevant to chezmoi-managed rc files in the image |
| Update (manual) | `codex update` ("when the installed release supports self-update"); `codex app-server daemon update` for the daemon package | `$KB/codex/cli__reference.md:296-298`; live `codex --help`, `codex app-server daemon --help` |
| Self-update | **YES, via the managed app-server daemon's updater loop** (a `pid-update-loop` process): every `updateIntervalMinutes` (default **60**, first check after 5 min) it downloads `https://chatgpt.com/codex/install.sh` and runs it with `CODEX_RELEASE=latest CODEX_NON_INTERACTIVE=1`. The TUI's `check_for_update_on_startup` only NOTIFIES (popup), it does not install. | update_loop.rs:63-66, :532-579; settings.rs:14, :87-92; tui/updates.rs:27-28, :152-153 |
| Disable self-update | **no env var.** `$CODEX_HOME/app-server-daemon/settings.json` → `{"updater":{"autoUpdateEnabled":false}}` (camelCase; default true; also `updateIntervalMinutes`); a restart stops the update-loop backend when disabled. `check_for_update_on_startup = false` in `config.toml` silences only the TUI notice. No CLI flag (`daemon bootstrap --help` has none). Host: that settings file is ABSENT → defaults → updater ON | settings.rs:69-92; lib.rs:55, :341, :470-474; `ls ~/.codex/app-server-daemon/` |
| Pin / rollback | `install.sh --release 0.158.0` (or `CODEX_RELEASE=`); old releases retained under `releases/`, `current` is a symlink. The updater will move it forward again unless `autoUpdateEnabled=false` | install.sh:5,:86; host releases dir |
| macOS | aarch64-apple-darwin, x86_64-apple-darwin (Rosetta shell → aarch64). Binary **Developer ID signed "OpenAI OpCo, LLC (2DC432GLL2)"**, Gatekeeper-accepted (`codesign -dv`, `spctl -a`) | install.sh:1111-1125; host probe |
| Linux | x86_64-unknown-linux-musl, aarch64-unknown-linux-musl (static musl — glibc-independent) | install.sh:1128-1136 |

### Verification (codex) — measured

- **Installer**: reads the release metadata (releases.openai.com, or the GitHub API) and requires a `sha256:` digest for the
  asset (`release_asset_digest`, install.sh:432-472); for the `package` layout it also downloads `codex-package_SHA256SUMS`
  and checks the archive against it (install.sh:476-530, :555-561). Both come from the same origin as the archive — TLS +
  checksum, **no signature check** (grep of install.sh for `cosign|sigstore|minisign|gpg|signature` finds none).
- **Signatures that exist but nothing checks**: Linux assets ship `*.sigstore` bundles (keyless Fulcio cert); the cert on
  `codex-package-x86_64-unknown-linux-musl.tar.gz.sigstore` names SAN
  `https://github.com/openai/codex/.github/workflows/rust-release.yml@refs/tags/rust-v0.159.2`, issuer
  `https://token.actions.githubusercontent.com`, commit `ff6aec96…`. Cryptographic `cosign verify-blob` NOT run: `cosign` on
  this host is an orphan mise shim (`mise use -g cosign@3.1.3` error) and installing it was out of scope → **unverified**.
  No macOS sigstore bundles (macOS relies on codesign/notarization).
- **GitHub artifact attestations: none.** `gh attestation verify … --repo openai/codex` → HTTP 404 for digest
  `sha256:9e2d29a7…`; control arm: `gh api repos/cli/cli/attestations/<digest of gh_…_macOS_arm64.zip>` → 1 attestation, so the
  probe can find one.
- Measured bytes agree across three routes: downloaded `codex-package-x86_64-unknown-linux-musl.tar.gz` sha256 `9e2d29a7…a6b` ==
  `codex-package_SHA256SUMS` line == GitHub API asset `digest`.
- **vs mise**: S1 is `npm:@openai/codex`; with this repo's `npm.package_manager = "bun"` (`mise.toml` [settings]) mise.lock
  records **version + options only** (`.config/mise/mise.lock:531-536`) — mise's docs: aube records dependency graphs,
  "Other language package installers: Top-level versions only" (jdx/mise `docs/dev-tools/mise-lock.md` Backend Support table).
  Integrity then rests on bun's registry `sha512` integrity (TOFU vs the registry, not vs the lock). Notably the npm tarball
  DOES carry SLSA provenance (`registry.npmjs.org/@openai/codex/0.159.2` → `dist.attestations.provenance.predicateType =
  https://slsa.dev/provenance/v1`, 2 registry signatures) that neither mise nor bun is asked to verify. So the native installer
  (sha256 against release metadata + SHA256SUMS) is **not weaker** than today's S1 pin; it is weaker than an aqua/github
  backend lock only in that the digest is fetched at install time rather than committed.
- aqua registry `pkgs/openai/codex/registry.yaml` (current block): asset `codex-package-{{.Arch}}-{{.OS}}.tar.gz`, file
  `bin/codex`, **no `checksum:`/cosign/slsa block** — an `aqua:openai/codex` mise.lock sha256 would be mise-computed TOFU. It
  also installs only `bin/codex` into mise's dir, not `$CODEX_HOME/packages/standalone`, so it cannot own the managed daemon
  (the 2026-09-16 finding cited in `codex-native-installer-status-2026-09-23.md:124-125`). The `mise.toml:119-123` comment
  ("aqua's release only ships the Rust CLI binary") is now half-stale: aqua moved to `codex-package-*`.

## 4. agy (Google Antigravity CLI) — native installer

Sources: `google-antigravity/antigravity-cli` README (§Installation, lines 35-49) and CHANGELOG.md (853 lines, top = 1.2.14);
LIVE installer fetched (not executed) 2026-09-30: `https://antigravity.google/cli/install.sh` (HTTP 200, 239 lines, sha256
`ee1ea43c…c640`); auto-updater manifests at `https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/<platform>.json`;
issues #1046, #1080, #834, #568 (fan-out hits, deep-read via `gh api`). Latest release **1.2.14** (2026-09-30T04:03Z; daily cadence:
1.2.9…1.2.14 in 8 days).

| Aspect | Finding | Evidence |
|---|---|---|
| Install | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` (only flags: `-d/--dir <path>`, `-h`) | README:39; install.sh:16-49 |
| Version selection | **none** — the script always installs whatever the platform manifest names (latest). **Refuses to run if `<dir>/agy` already exists** ("automatically self-updates in the background… delete the binary first") | install.sh:57-64, :132-141 |
| Location | `$HOME/.local/bin/agy` (or `--dir`), a single flat binary; then runs `agy install [--dir]` for shell setup (`\|\| true` — failures swallowed); strips macOS quarantine xattr | install.sh:12, :54, :215-236 |
| Update | **self-updates IN PLACE in the background during normal runs** (updater spawns a background process; state in `~/.gemini/antigravity-cli/updater/update_status.json`); manual `agy update` exists (#568: "`agy update` reports already on latest") | install.sh:59; #1046 body ("auto_updater.go:305] Spawned background update process"; "updated agy in place from 1.2.5 to 1.2.6"); CHANGELOG:541 (updater double-spawn fix) |
| Disable self-update | `AGY_CLI_DISABLE_AUTO_UPDATE=true` — maintainer-stated (#834 COLLABORATOR haofan 2026-08-23; #568 COLLABORATOR yaoshengzhe 2026-07-08). ⚠️ **only the literal `true` works; `=1` still updates** (#1046, OPEN, reported on 1.2.6, log line `auto_updater.go:218] Auto-update disabled via environment variable`). Undocumented in README/CHANGELOG. Also maintainer-stated: a **read-only (`chmod 555`) install dir** makes the updater skip (#1080 COLLABORATOR 2026-09-23) | issue threads |
| Pin / rollback | not via the installer. Download a specific GitHub release asset (`agy_cli_<os>_<arch>[_musl].tar.gz`, every version retained on GitHub Releases) + disable auto-update. ⚠️ Server-side floor: #568 — a version can be declared "no longer supported" and refuse to run (1.1.0, 2026-07-08; the maintainer's workaround was *roll back to 1.0.16 + `AGY_CLI_DISABLE_AUTO_UPDATE=true`*) — a pin can be bricked remotely | #568 |
| macOS | darwin arm64 + amd64 (installer), GitHub `mac_arm64`/`mac_x64`; binary **Developer ID signed "Google LLC (EQHXZ8M8AV)"**, Gatekeeper-accepted | install.sh:70-78; `codesign -dv`/`spctl -a` on host binaries and on the extracted 1.2.14 tarball |
| Linux | `linux_amd64`, `linux_arm64`, `_musl` variants (musl auto-detected) — all four manifests return 1.2.14 | manifest GETs; control: `bogus_zz9` → 404. (My first probe used `linux_x64` → 404: the installer's key is `amd64`, install.sh:76 — a probe error, not a missing platform.) |

### Verification (agy) — measured

- **Installer**: fetches the per-platform manifest `{version,url,sha512}` and compares `sha512` of the download, halting on
  mismatch ("Security Halt…", install.sh:187-197). Manifest and payload are same-party (Cloud Run + GCS
  `storage.googleapis.com/antigravity-public/antigravity-cli/<ver>-<build>/…`) over TLS — **no signature**, and there are no
  `.sig`/sigstore assets on GitHub Releases and **no GitHub attestations** (`…/attestations/sha256:468edcc4…` → 404; the same
  API returned 1 for a cli/cli asset — §3 control arm).
- **Byte identity, measured**: 1.2.14 darwin_arm64 — GCS tarball sha512 == manifest (YES); GCS tarball sha256 ==
  GitHub asset sha256 == `mise.lock` `macos-arm64` checksum `468edcc4…c19`; extracted `antigravity` binaries identical
  (`a33fdf08…14c4`). So native and mise install **the same bytes** at install time.
- **vs mise, the real difference**: the self-updater replaces the binary **inside mise's install dir** too, so after the first
  update the `mise.lock` checksum no longer describes what runs. Host evidence: `installs/antigravity-cli/{1.1.20,1.1.21,1.1.23,1.1.25,1.2.0,1.2.10,1.2.11}/agy`
  are regular 165-187 MB files, while untouched dirs hold the aqua `agy -> antigravity` symlink (the aqua `files: name: agy
  src: antigravity` mapping); memory `project_session_2026-09-25b.md:19` recorded `installs/antigravity-cli/1.2.2/agy --version`
  printing 1.2.11. aqua registry `pkgs/google-antigravity/antigravity-cli/registry.yaml` has **no `checksum:` block**, so the
  `mise.lock` sha256 is mise-computed TOFU (it matches the GitHub API digest). **A mise pin of agy is therefore a pin in name
  only unless `AGY_CLI_DISABLE_AUTO_UPDATE=true` is also set** — and the same env var is what makes a native install pinnable.
- Host: `~/.local/bin/agy` = 1.1.12 (2026-08-12 mtime), never self-updated because PATH resolves the mise copy first
  (`which -a agy`); the installer would refuse to replace it (install.sh:57) — the stale copy must be `rm`-ed before a native
  re-install. My `~/.local/bin/agy --version` probe did not rewrite it (mtime unchanged after).

## 5. Side-by-side answer

| | **claude** | **codex** | **agy** |
|---|---|---|---|
| Install | `curl -fsSL https://claude.ai/install.sh \| bash [-s stable\|latest\|X.Y.Z]` | `curl -fsSL https://chatgpt.com/codex/install.sh \| CODEX_NON_INTERACTIVE=1 sh [-s -- --release X.Y.Z]` | `curl -fsSL https://antigravity.google/cli/install.sh \| bash [-s -- --dir D]` |
| Pin at install | yes (arg) | yes (`--release` / `CODEX_RELEASE`) | **no** (latest only; manual GitHub-asset download to pin) |
| Update cmd | `claude update`, `claude install <v>` | `codex update`; `codex app-server daemon update` | `agy update` |
| Self-updates | yes, background, on use | yes, via managed-daemon updater loop (5 min, then hourly), runs install.sh with `CODEX_RELEASE=latest` | yes, background, on use, **in place** (even inside mise's install dir) |
| Disable | `DISABLE_AUTOUPDATER=1` (bg only) / `DISABLE_UPDATES=1` (all); settings.json `env` works | `$CODEX_HOME/app-server-daemon/settings.json` `{"updater":{"autoUpdateEnabled":false}}` + `daemon restart` (since #43542, 2026-09-07); no env var; `check_for_update_on_startup=false` only mutes the TUI notice | `AGY_CLI_DISABLE_AUTO_UPDATE=true` (literal `true`; `1` fails, #1046 open) or a read-only install dir |
| Rollback | `versions/` retained; `claude install <old>` | `releases/` retained; `--release <old>` | re-download old GitHub asset; server may refuse old versions (#568) |
| Location | `~/.local/bin/claude` → `~/.local/share/claude/versions/<v>` | `~/.local/bin/codex` → `$CODEX_HOME/packages/standalone/current/bin/codex` | `~/.local/bin/agy` (flat binary) |
| Edits shell rc | installer's `claude install` sets up shell integration (not inspected, closed source) | yes, marked PATH block in `.zprofile`/`.bash_profile`/`.zshrc`/`.bashrc`/`.profile` | `agy install` "Configuring shell environment" (not inspected) |
| macOS arm64/x64 | ✓/✓, codesigned+notarized (Anthropic PBC Q6L2SF6YDW) | ✓/✓, Developer ID (OpenAI OpCo 2DC432GLL2) | ✓/✓, Developer ID (Google LLC EQHXZ8M8AV) |
| linux amd64/arm64 | ✓/✓ + musl; signed apt/dnf/apk repos also offered | ✓/✓ (musl static only) | ✓/✓ + musl |
| Installer integrity | sha256 vs same-origin `manifest.json` (no sig check) | sha256 vs release-metadata digest + `SHA256SUMS` (no sig check) | sha512 vs same-origin manifest (no sig check) |
| Stronger check available | **GPG-signed manifest** (key `31DD…CACE`) — verified live, both arms | **sigstore bundles** (linux only; keyless, `rust-release.yml@refs/tags/…`) — cert decoded, crypto verify NOT run; no GH attestations | **none** (no sig, no attestation) |
| mise today | IMAGE `aqua:anthropics/claude-code` (sha256 in lock; aqua registry also uses upstream `SHASUMS256.txt`) | SHARED `npm:@openai/codex` via bun → lock has **version only**, no checksum | HOST `aqua:…/antigravity-cli` (sha256 in lock, mise-computed; aqua has no checksum source) — **invalidated by in-place self-update** |

## 6. Conflicts resolved

- **codex "auto-update cannot be disabled"** (openai/codex#40969, OPEN, filed 2026-08-26 on 0.149→0.150) vs source: PR #43542
  "Make app-server daemon automatic updates configurable" merged 2026-09-07T18:28Z; `settings.rs` at `rust-v0.159.2` has
  `updater.autoUpdateEnabled` (default true) and the daemon README documents it. **Trusted: source + merged PR** — the issue is
  stale (an open issue is not current state). The 60 s kill budget it complains about is also configurable
  (`shutdownGraceSeconds`, #43572).
- **claude `autoUpdates: false` ignored** (anthropics/claude-code#91646 OPEN, #88030 closed): not a conflict — on native installs
  `autoUpdates` in `~/.claude.json` is installer bookkeeping; the supported switch is `DISABLE_AUTOUPDATER` (bot answer on #88030
  + `$CC/env-vars.md:408`). Confirmed the env names are compiled into 2.1.285 (`DISABLE_AUTOUPDATER` ×8, `DISABLE_UPDATES` ×7;
  fresh nonce ×0).
- **agy `AGY_CLI_DISABLE_AUTO_UPDATE` value**: maintainers said "set it" (#834) / "=true" (#568); a user measured `=1` does not
  work (#1046, open). **Use `=true`**. The name is present in the 1.2.14 binary (×1; fresh nonce ×0; positive control
  `AGY_CLI_HIDE_LOGO` ×2).
- **`mise.toml:119-123` comment** says aqua codex ships only the Rust CLI binary; the current aqua registry block installs
  `codex-package-*` (`bin/codex`). The operative reason to avoid aqua/npm for the host remains the managed-daemon location
  (`$CODEX_HOME/packages/standalone`), not the asset shape.

## 7. Gaps (carried, not "nothing found")

- **IMAGE and CI native paths are NOT proven here** (read-only lane; no container run). S1 (`npm:@openai/codex`, feeds
  `mise-system.lock` and CI where `ci.yml:69-72` says "pytest shells out to `codex`") and I1 (`claude-code` in
  `mise-runtime.toml`) must not be removed until a native install is proven in the image (home-volume masking + PATH order —
  `native-installer-placement-2026-09-15.md`, `codex-native-installer-status-2026-09-23.md` F4) and on a runner. Claude on CI
  is already native (C1).
- `claude install <target>` (the binary's own download of the requested version) — closed source; whether it verifies the GPG
  manifest signature is unverified.
- codex sigstore: `cosign verify-blob` not run (cosign here is an orphan shim; installing it was out of scope). Identity decoded
  only.
- `agy update --help` / `agy install` semantics not probed: running the native agy can spawn its self-updater, which would mutate
  the host (read-only mandate). The shell-rc edits `agy install` makes are therefore unknown.
- `context7` fan-out source: `status=error` ("exited 1") on the claude run — a gap, not an empty result.
- `github-discussions` for antigravity-cli: `empty_unverified`.
- Corpora dates: `$CC/*` snapshot 2026-09-15 (claude 2.1.285/286 is newer; the load-bearing env vars were re-confirmed in the
  2.1.285 binary). Codex docs corpus undated in this lane; load-bearing codex claims were taken from source at the latest tag.

## 8. Recommendation

1. **HOST (approved now):** remove `antigravity-cli = "1.2.14"` (`mise.toml:126`) and the user-global
   `~/.config/mise/config.toml:142` entry; remove `disable_tools = ["npm:@openai/codex"]` (`mise.toml:169`) **only together with**
   S1, otherwise leave it (it is what keeps the host on native codex while S1 exists). There is no host claude mise pin to remove
   (already native since `6d1ae23`). Also update the now-stale comments at `mise.toml:108-125` and `mise.toml:164-168`.
2. **agy native on host:** `rm ~/.local/bin/agy` (stale 1.1.12 — the installer refuses to overwrite it), run the official
   installer, and decide the update policy explicitly: either let it self-update (today's de-facto behaviour even under mise) or
   set `AGY_CLI_DISABLE_AUTO_UPDATE=true` (literal) where a pin matters (KB's `kb-review-receipt` compares running agy to a pin).
3. **codex / claude on host:** already native and self-updating; nothing to install. If a version floor/ceiling or freeze is
   wanted: claude `DISABLE_AUTOUPDATER=1` / `minimumVersion` / managed `requiredMaximumVersion`; codex
   `app-server-daemon/settings.json` `updater.autoUpdateEnabled=false`.
4. **IMAGE/CI (NOT approved for removal yet):** keep S1 and I1 until a native path is proven in-container and on a runner. For
   parity with mise.lock's committed digests, a native recipe should pin the version and verify: claude — `gpg --verify` the
   signed `manifest.json` then sha256 the binary (strictly stronger than today's aqua TOFU checksum); codex — `--release <v>` +
   SHA256SUMS (+ `cosign verify-blob` on the linux `.sigstore` bundle for a real signature, strictly stronger than today's npm
   version-only lock); agy — host-only, no image/CI consumer found in this grep.

## 9. Verification (refute pass)

| Claim | Arm | Result |
|---|---|---|
| Claude manifest is GPG-signed and the installed binary matches | good sig on real manifest; BAD sig on 1-byte-tampered manifest; sha256 of installed 2.1.285 vs manifest | CONFIRMED |
| Claude env switches exist | strings count in 2.1.285 vs fresh nonce (8/7 vs 0) | CONFIRMED |
| codex auto-update is configurable off (settings.json) | source at tag + README + merged PR #43542; `autoUpdateEnabled` ×3 in installed 0.159.2 binary vs nonce 0 | CONFIRMED (behavioural toggle NOT exercised — would mutate host) |
| codex has no GitHub attestations | 404 for codex digest; cli/cli digest → 1 attestation | CONFIRMED |
| agy native == mise bytes (1.2.14 darwin-arm64) | GCS vs GitHub tarball sha256 + extracted binary sha256 + mise.lock checksum | CONFIRMED |
| agy disable var name / value | binary strings (×1 vs nonce 0; positive control ×2); #1046 `=1` fails | CONFIRMED name; value `true` per maintainers + #1046 (behaviour NOT exercised here) |
| npm backend lock has no checksum here | `.config/mise/mise.lock:531-536` + `mise-system.lock:4963-4968` show no `checksum`; same file shape shows `checksum` for aqua tools (`mise.lock:4496`) | CONFIRMED |

## Evidence: fan-out runs

| Query | Repo | Sources → status | Manifest | rc |
|---|---|---|---|---|
| `auto update disable` | google-antigravity/antigravity-cli | issues ok, discussions **empty_unverified**, releases ok, firecrawl-developer ok, exa ok (off-topic hits) | `.agent/kb/raw/research-fanout/auto-update-disable/manifest.json` | 0 |
| `disable auto update standalone installer` | openai/codex | issues ok, discussions ok, releases empty_verified, firecrawl-developer ok | `.agent/kb/raw/research-fanout/disable-auto-update-standalone-installer/manifest.json` | 0 |
| `DISABLE_AUTOUPDATER native installer version pin` | anthropics/claude-code | issues ok, releases empty_verified, firecrawl-developer ok, context7 **error** | `.agent/kb/raw/research-fanout/disable-autoupdater-native-installer-version-pin/manifest.json` | 0 |

(Manifest paths are relative to the worktree root. Installer scripts, source files and downloaded artifacts were kept in the
session scratchpad, not the repo.)

## GitHub repos touched

- [google-antigravity/antigravity-cli](https://github.com/google-antigravity/antigravity-cli) — README install section, CHANGELOG, releases 1.2.9–1.2.14 + asset digests, issues #1046 #1080 #834 #568, attestations API (404)
- [openai/codex](https://github.com/openai/codex) — `scripts/install/install.sh` (served copy), `codex-rs/app-server-daemon/{update_loop,settings,lib}.rs` + README, `codex-rs/tui/src/updates.rs`, `codex-rs/cli/src/doctor/updates.rs` at rust-v0.159.2; releases + `.sigstore` + `SHA256SUMS`; PR #43542; issues #40969 #34692; settings.rs commit history
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — latest release assets (`SHASUMS256.txt(.sig)`), issues #91646 #88030
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry) — `pkgs/{google-antigravity/antigravity-cli,anthropics/claude-code,openai/codex}/registry.yaml` (checksum/signature blocks)
- [jdx/mise](https://github.com/jdx/mise) — `docs/dev-tools/mise-lock.md` (backend support: what a lock entry verifies per backend)
- [cli/cli](https://github.com/cli/cli) — control arm only (a release asset known to carry a GitHub attestation)

Status: COMPLETE.
