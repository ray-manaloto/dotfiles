## v2026.10.1
This release is mostly bug fixes. `mise run` now stops tasks properly when `--timeout` expires or you press Ctrl-C. Task daemons and native shims work better on Windows. `core:rust` now follows `mise.lock` and picks up new stable and beta toolchains. Lockfile, GitHub asset selection, Homebrew cask and plugin update problems are also fixed.

## Fixed

### Tasks

- **`mise run --timeout` now stops the tasks it was running.** Before, mise printed the timeout error and exited, but the task processes could keep running in the background. Now the whole-run timeout (`--timeout` or the `task.timeout` setting) stops tasks the same way a per-task `timeout` does. On Unix, mise sends SIGTERM and then SIGKILL after 5 seconds. On Windows, it runs `taskkill /F /T`. Tasks with `raw = true` are not stopped by the whole-run timeout. [#13876](https://github.com/jdx/mise/pull/13876) by @Marukome0743
- **A single Ctrl-C lets tasks shut down cleanly.** Before, one Ctrl-C could make mise exit right away while tasks were still cleaning up. This happened in three cases: a task that runs `mise run` itself got SIGINT twice; a tool like `docker compose up` treated the duplicate SIGINT as a force-quit; and a task that exits non-zero on SIGINT caused mise to send SIGTERM to its sibling tasks. Now mise waits for tasks to finish and then exits with status 130. A second Ctrl-C still force-quits. [#13904](https://github.com/jdx/mise/pull/13904)
- **Tab completion for the `:task` shorthand.** In a monorepo, `mise run :<TAB>` now suggests tasks from the current config root, and task flags complete after the shorthand. [#13882](https://github.com/jdx/mise/pull/13882) by @pikeas

### Daemons

- **Task daemons start on Windows.** A daemon declared with `task =` failed under `cmd /C` with `'exec' is not recognized`. mise now registers it as an argv command that pitchfork starts without a shell, so `args` reach the task exactly as written on every platform. **This needs pitchfork 2.28.0 or later.** With an older pitchfork, mise shows an error that tells you to upgrade, for example with `mise use pitchfork@latest`. Task daemons that use `init` still run through a shell, so they still don't work under `cmd /C`. [#13714](https://github.com/jdx/mise/pull/13714) by @JamBalaya56562
- **Daemon `run` commands can use `[env]` and `[vars]`.** Before, a template such as `{{ vars.test_var }}` failed with `Variable 'vars' is not defined`. `mise x` now renders the command when the daemon starts, using the project's `[env]`, `[vars]` and mise template filters. Pitchfork's own variables, such as `{{ name }}`, still work. This applies only to `run` and requires a pitchfork release newer than 2.29.0. [#13894](https://github.com/jdx/mise/pull/13894)

  ```toml
  [vars]
  greeting = "it's"

  [daemons.hello]
  run = "exec echo {{ vars.greeting | quote }} from {{ name }}"
  ```

### Windows shims

- **No more endless process chains from duplicate shim copies.** If two copies of `mise-shim.exe` were on PATH (for example, one from winget's `Links` directory), they could keep calling each other through `mise x`. Running `mise-shim` by its own name now exits with an error. If `mise x` resolves a tool to another shim copy, mise stops after one step and names the PATH directory to remove. [#13681](https://github.com/jdx/mise/pull/13681) by @JamBalaya56562
- **Node IPC works through the `node.exe` shim.** A Node parent that spawned the shim with an `'ipc'` stdio entry used to wait forever. JSON IPC messages and disconnects now pass through the shim. Passing socket or server handles over the channel is still not supported. [#13903](https://github.com/jdx/mise/pull/13903)

### Rust

- **`mise upgrade rust` updates `stable` and `beta`.** mise didn't recognize rustup 1.29's new `update available:` text. Even when it detected an update, the upgrade skipped the toolchain as already installed. mise now reads both spellings, counts only updates for the toolchain it manages, and updates the toolchain in place. If the update fails, the old toolchain stays usable. [#13898](https://github.com/jdx/mise/pull/13898)
- **`core:rust` follows `mise.lock`.** mise mistook rustup's symlinks for `mise link`ed versions, so it ignored the lockfile and installed the newest version even with `locked = true`. [#13915](https://github.com/jdx/mise/pull/13915)

### Backends, lockfiles and bootstrap

- **GitHub auto-detection no longer installs metadata files.** SBOMs, signatures, checksums and other sidecar files with platform names, such as `*.tar.gz.sbom.json`, could be chosen as the tool and saved to `mise.lock`. Automatic selection now skips them. Explicit `url` and `asset_pattern` options are unchanged. [#13908](https://github.com/jdx/mise/pull/13908)
- **`mise lock` removes outdated duplicate entries.** After you changed a tool option, for example by adding `uvx = false` to a `pipx:` tool, `mise lock --upgrade` could leave the old unbound entry next to the new bound one. Unfiltered `mise lock` runs now remove the old entry, unless it has platform data (checksum or URL) that the new entry doesn't have. [#13909](https://github.com/jdx/mise/pull/13909)
- **Aqua registry cache errors after upgrading.** Compiled registry caches from earlier versions could load but then fail when a package was resolved. mise now ignores those caches and rebuilds them. [#13884](https://github.com/jdx/mise/pull/13884)
- **Packslip installs retry missing skills.** If the binary installed but a declared skill couldn't be fetched, mise still marked the install as complete. Now the install fails with an error. The next `mise install` fetches only the missing skills and doesn't reinstall the tool. [#13885](https://github.com/jdx/mise/pull/13885)
- **Pkg-based `brew-cask` packages are no longer reinstalled on every run.** Casks such as `google-drive` list package IDs for several architectures, and mise expected every one of them to be installed. Receipts now store only the patterns that match on your machine. Casks recorded by earlier versions are reinstalled once to write a corrected receipt. [#13893](https://github.com/jdx/mise/pull/13893)
- **`mise plugins update` works when the remote isn't named `origin`.** This happens, for example, when git's `clone.defaultRemoteName` is set to something else. mise uses `origin` if it exists and otherwise uses the first remote. [#13914](https://github.com/jdx/mise/pull/13914)

## Changed

- `mise skills sync`, the table output of `mise skills ls`, and other human-facing messages now show paths under your home directory with `~`. This includes output from `mise deps install`, task source lines, `mise completion --install` and daemon messages. `--json` output and script-oriented commands still print full paths. [#13910](https://github.com/jdx/mise/pull/13910)

**Full Changelog**: https://github.com/jdx/mise/compare/vfox-v2026.10.0...v2026.10.1

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
## v2026.10.0
This release tightens supply-chain verification. Keyless cosign bundles must now match a pinned signer identity, and GitHub attestation workflow checks no longer accept partial matches. It also closes a `.tool-versions` trust gap that could leak `GITHUB_TOKEN`, adds a per-cask `appdir` option for Homebrew casks, and fixes problems with locked SLSA installs, musl hosts and `mise backends switch`.

## Security

- **Inline tool options in `.tool-versions` now require trust.** This is the `.tool-versions` version of the `mise.toml` fix in 2026.9.18. An untrusted project could ship a `github:` entry with inline options, such as `[api_url=...]`, pointing at another host. Commands such as `mise ls`, `env`, `current`, `outdated` and `latest` would then send your `GITHUB_TOKEN` to that host without asking for trust. Any entry whose tool name contains `[` now requires trust, the same as Tera templates. Plain lines like `node 20.0.0` still load without trust, and a `[` inside a comment is ignored. Run `mise trust` for projects you rely on. `MISE_SAFE=1` still skips trust checks. (GHSA-wcqh-j26q-g44x) [#13869](https://github.com/jdx/mise/pull/13869)
- **Keyless cosign verification now checks who signed.** Before, the aqua backend only checked that a bundle chained to Sigstore's Fulcio CA. Any GitHub Actions workflow in any repository can get such a certificate, so a bundle signed by the wrong workflow would still pass. mise now applies the registry's `--certificate-identity[-regexp]`, `--certificate-oidc-issuer[-regexp]` and `--certificate-github-workflow-{repository,ref,name,trigger,sha}` options to the signing certificate. It does this for both current and legacy bundles. Keyless verification now requires a pinned identity, and an unknown or empty `--certificate-*` option is an error. Key-based verification (`--key`) is unchanged. Registry patterns that use RE2 `\Q…\E` quoted literals, such as the one for `vfox`, are supported. [#13875](https://github.com/jdx/mise/pull/13875), [#13879](https://github.com/jdx/mise/pull/13879)
- **GitHub attestation signer workflow matching is anchored.** The expected `signer_workflow` must now match the end of the certificate's workflow path as whole path segments. Before, it was a substring match against the whole identity, so a longer workflow file name such as `release.yml.evil.yml`, or a ref that contained the expected path, would pass. An empty `signer_workflow` now fails verification. Both the bare form (`.github/workflows/release.yml`) and the repository-qualified form (`owner/repo/.github/workflows/release.yml`) still work. [#13877](https://github.com/jdx/mise/pull/13877)

## Added

- **Per-cask app directories.** A `brew-cask:` bootstrap package can set its own `appdir`. This overrides the global `MISE_BREW_CASK_OPT_APPDIR` setting, expands `~/`, and also applies to the cask's dependencies. [#13865](https://github.com/jdx/mise/pull/13865)

  ```toml
  [bootstrap.packages]
  "brew-cask:1password" = { appdir = "/Applications" }
  ```

  The setting only applies to installs and upgrades: apps that are already installed are not moved. A first install into a new `appdir` won't replace an existing app it doesn't own unless you set `adopt = true`. Other package managers ignore `appdir` and print a warning.
- **`slsa_signer_identity` and `slsa_signer_issuer` options for aqua tools.** These work the same as in the github backend. They let `mise lock` verify and record SLSA provenance for packages whose registry entry has no signer, such as `aqua:google/osv-scanner`. You must set both options to non-empty strings, and together they override any signer in the registry, including version overrides. [#13856](https://github.com/jdx/mise/pull/13856)
- **Registry:** `cloudflare-cf`, Cloudflare's `cf` CLI, which is in beta and installs from `npm:cf`. It provides the `cf` and `cloudflare` binaries. Pin a beta version for now, such as `mise use cloudflare-cf@1.0.0-beta.10`. An unpinned install currently resolves to an unrelated old `0.x` release. [#13871](https://github.com/jdx/mise/pull/13871)
- **Docs:** a new Releases page (under About in the docs) shows a timeline of release sizes, the issues each release resolved, and expandable release notes. [#13855](https://github.com/jdx/mise/pull/13855)

## Fixed

- **Locked SLSA installs work again without a registry signer.** Since 2026.9.17, a lockfile that recorded a checksum and SLSA provenance failed with "Aqua registry metadata has no signer_identity and signer_issuer" for tools such as `aqua:google/osv-scanner` and `aqua:fluxcd/flux2`. A lock entry with a checksum and recorded provenance is now trusted for SLSA too: the install only checks the artifact digest, as it already did for other provenance types. `locked_verify_provenance` or paranoid mode still re-verify and still require a signer. [#13856](https://github.com/jdx/mise/pull/13856)
- **aqua on musl hosts.** On Alpine and other musl hosts, an aqua tool whose registry entry only names a glibc build (such as `zizmor`) failed with "no asset found: ...-unknown-linux-musl...". mise now installs the asset the registry names. The binary still needs glibc or `gcompat` to run. `mise lock` for `linux-x64-musl` records the same asset. [#13857](https://github.com/jdx/mise/pull/13857)
- **`mise backends switch` handles stale lock entries.** Sometimes `mise install` warned that a tool was locked to a replaced backend, for example `asdf:clojure` instead of `vfox:jdx/vfox-clojure`, but `mise backends switch` then reported there was nothing to switch. This happened when the config's version no longer matched the lock entry. The command now switches those entries too. Entries at a version the config no longer resolves to are relocked at the config's version and reported as `replacing stale <tool>@<version>`. [#13859](https://github.com/jdx/mise/pull/13859)
- **Ctrl-C exits with status 130.** Interrupting `mise install`, `upgrade`, `exec` and similar commands used to exit with 1, the same as an ordinary failure. They now exit with 130 (128 + SIGINT), matching `mise run`, so shells and scripts can tell when a user interrupted. A repeated Ctrl-C during `mise run` also exits with 130. This applies on Unix and Windows. [#13862](https://github.com/jdx/mise/pull/13862)
- **Declining a trust prompt skips the config for that run.** Before, declining still failed the current command with "not trusted". [#13868](https://github.com/jdx/mise/pull/13868)
- The one-time startup migration for stale `latest` runtime directories has been removed. It was due to expire in this release and would have blocked normal installs. `mise install` still repairs a stale `latest` directory, but passive commands such as `mise ls` no longer touch it. [#13868](https://github.com/jdx/mise/pull/13868)
- **Stale dotfile history watchers are diagnosed.** A history watcher started on an older mise can fail every capture with an unknown-field error for newer settings such as `exclude`. `mise doctor` and `mise dot status` now report that the watcher is outdated and tell you to run `mise bootstrap services apply`, which restarts it. [#13864](https://github.com/jdx/mise/pull/13864)
- **Java:** the missing-metadata error now names the target platform, for example `no metadata found for version zulu-8 on windows-arm64`. [#13873](https://github.com/jdx/mise/pull/13873) (@jsiu93)

## Breaking Changes

- **`--from-git` removed from `mise bootstrap`.** `mise bootstrap --from-git` and `mise bootstrap remote --from-git` now fail with an unexpected-argument error. Use `--adopt`, which has been the documented flag since 2026.9.3: [#13872](https://github.com/jdx/mise/pull/13872)

  ```sh
  mise bootstrap --adopt git@github.com:me/dotfiles.git
  ```
- **vfox tool plugins that use keyless cosign must pin an identity.** If a `PreInstall` attestation sets `cosign_sig_or_bundle_path` without `cosign_public_key_path`, it must also set `cosign_certificate_identity` or `cosign_certificate_identity_regexp`. You can also set `cosign_certificate_oidc_issuer`. Without an identity, the attestation is rejected. Registry entries that already work with the aqua CLI are not affected. [#13875](https://github.com/jdx/mise/pull/13875)
- **Alpine/musl:** if a registry entry names a gnu asset but the release also ships a musl build, mise now installs the gnu build. Before, it switched to musl. Set `libc = "musl"` on that tool to keep the musl build. [#13857](https://github.com/jdx/mise/pull/13857)
- **Exit code on Ctrl-C:** scripts that checked for exit status 1 after an interrupt should now check for 130. [#13862](https://github.com/jdx/mise/pull/13862)

## New Contributors

* @jsiu93 made their first contribution in [#13873](https://github.com/jdx/mise/pull/13873)

**Full Changelog**: https://github.com/jdx/mise/compare/vfox-v2026.9.20...v2026.10.0

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
## v2026.9.5
This release deepens macOS bootstrap support with current-host and nested defaults, lets dotfiles and tasks adapt to the platform and to parsed arguments, and adds an opt-in trial of complete lockfile generation. It also carries a batch of install progress, self-update, brew-cask, and sandbox fixes.

## Added
- **bootstrap:** New `[[bootstrap.macos.defaults_entries]]` blocks let you set macOS preferences explicitly with `domain`, `key`, `value`, and an optional `host` (`any` by default, or `current`), covering preferences normally written via `defaults -currentHost` while keeping the existing `[bootstrap.macos.defaults]` shorthand. Entries also accept an optional `path` to patch a nested dictionary value without replacing its siblings, preserving property-list types and creating missing parents. ([#12983](https://github.com/jdx/mise/pull/12983) by @azohra, [#12984](https://github.com/jdx/mise/pull/12984) by @azohra)

  ```toml
  [[bootstrap.macos.defaults_entries]]
  domain = "com.apple.dock"
  key = "autohide"
  value = true
  host = "current"
  ```
- **bootstrap:** More friendly macOS preferences: Finder folder sorting and default cloud save location, Dock autohide delay and timing (integers or floats), and keyboard automatic capitalization and spelling correction, all using snake_case names consistent with the existing sections. ([#13032](https://github.com/jdx/mise/pull/13032) by @jdx)
- **bootstrap:** `[bootstrap.files]` and `[bootstrap.directories]` entries gain `phase = "pre-packages"` so repository definitions, apt sources, and signing keys can be applied before package installation instead of only afterward. Existing declarations default to `"post-packages"`. ([#13052](https://github.com/jdx/mise/pull/13052) by @jdx)

  ```toml
  [bootstrap.files."/etc/apt/sources.list.d/vendor.sources"]
  source = "./files/vendor.sources"
  phase = "pre-packages"
  ```
- **bootstrap:** Ordinary `[bootstrap.files]` templates can now reference resolved `[vars]` values, alongside the existing `config_root`, `target`, and `secret()` helpers. ([#13033](https://github.com/jdx/mise/pull/13033) by @nettlesh)
- **dotfiles:** A single dotfiles source can deploy to different destinations per operating system, architecture, or mise profile using `variants` with an optional `target`. This works for `copy`, `symlink`, `symlink-each`, and `template` modes. ([#13050](https://github.com/jdx/mise/pull/13050) by @jdx)

  ```toml
  [dotfiles.settings]
  source = "dotfiles/vscode/settings.json"
  mode = "copy"
  variants = [
    { os = "macos", target = "~/Library/Application Support/Code/User/settings.json" },
    { os = "linux", target = "~/.config/Code/User/settings.json" },
  ]
  ```
- **task:** Task `sources` and `outputs` can now use `{{usage.*}}` templates, resolved per invocation from parsed arguments and flags before freshness and artifact-cache checks run, so different argument values track freshness independently. ([#13051](https://github.com/jdx/mise/pull/13051) by @jdx)
- **brew-cask:** Casks with structured `set_permissions` preflight/postflight steps now install correctly (for example `brew-cask:blender`), running an unprivileged `chmod` over resolved staged or appdir paths instead of failing with an unsupported step-type error. ([#13043](https://github.com/jdx/mise/pull/13043) by @azohra)
- **lock:** Opt-in trial of complete lockfile generation via `lockfile_mode = "generate"` (or `MISE_LOCKFILE_MODE=generate`). The default remains incremental `merge`. Generate mode rebuilds lockfiles from current requests while treating the previous file as an immutable baseline, reusing unchanged artifacts and publishing through staged atomic writes so failures or concurrent edits do not clobber a good lockfile. This mode records only cryptographically verified provenance per target platform; `provenance_verified` is no longer treated as a trust signal. ([#13031](https://github.com/jdx/mise/pull/13031) by @jdx)
- **self-update:** New `disable_update_warning` setting (`MISE_DISABLE_UPDATE_WARNING`) suppresses "newer mise available" notices in `mise version`, `mise --version`, and `mise doctor`. Explicit self-update and automatic updates are unaffected. ([#13028](https://github.com/jdx/mise/pull/13028) by @jdx)

## Fixed
- **install:** Interactive installs no longer leave a permanent line for every resolved, skipped, or already-installed tool; live progress shows what is happening while the final summary lists what changed (for example `installed 1 tool in 1.1s: dummy@1.0.0`). `mise upgrade` no longer duplicates its old to new version list. ([#13030](https://github.com/jdx/mise/pull/13030) by @jdx)
- **install:** Long non-TTY installs no longer flood CI logs with a snapshot every three seconds. The heartbeat now scales to roughly 10% of elapsed time, clamped between 3 seconds and 1 minute. ([#13036](https://github.com/jdx/mise/pull/13036) by @jdx)
- **self-update:** On 32-bit ARM, `mise self-update` now selects the correct `linux-armv7` archive instead of requesting a missing `linux-arm` one and falling back to an ARM64 binary that failed signature verification. A missing archive now fails asset selection rather than picking the wrong architecture. ([#13023](https://github.com/jdx/mise/pull/13023) by @jdx)
- **self-update:** npm installs now ship the instructions file that redirects update guidance to the package manager, so they no longer advertise `mise self-update`. ([#13028](https://github.com/jdx/mise/pull/13028) by @jdx)
- **brew-cask:** `mise bootstrap packages upgrade` no longer replaces the bundle of a running self-updating app (for example Chrome), which could strand helper processes and blank out tabs. Such apps are skipped while running and left to update themselves. ([#13041](https://github.com/jdx/mise/pull/13041) by @azohra)
- **brew-cask:** The cask metadata fetch error no longer includes stale advice about installing with `brew` and a broken documentation anchor; it now gives a short, accurate message. ([#12800](https://github.com/jdx/mise/pull/12800) by @Marukome0743)
- **bootstrap:** `mise bootstrap dotfiles origin set <url>` now uses the repository's own default branch when `--branch` is omitted, so repositories on `master` connect correctly instead of publishing a second root branch. A missing requested branch is now reported clearly rather than mistaken for an empty repository. ([#13037](https://github.com/jdx/mise/pull/13037) by @Dhaulagiri)
- **dotfiles:** History watcher locks now live alongside the history store in the state directory instead of being hashed into the cache directory, so a launchd watcher and an interactive shell using different cache directories coordinate correctly and `dotfiles status` no longer misreports `declared-not-running`. Existing watchers must be stopped and restarted with the updated binary. ([#13038](https://github.com/jdx/mise/pull/13038) by @ascarter)
- **sandbox:** The macOS Seatbelt profile now allows `file-read-metadata` on the ancestors of readable paths, fixing `Operation not permitted` failures when a portable Ruby resolves its own executable during third-party tap evaluation. Symlinked data directories and allow-listed paths are also handled. ([#13039](https://github.com/jdx/mise/pull/13039) by @Marukome0743)

## Registry
- Added `clipboard` ([github:Slackadays/Clipboard](https://github.com/Slackadays/Clipboard)) by @i-api in [#13044](https://github.com/jdx/mise/pull/13044)

## New Contributors
- @Dhaulagiri made their first contribution in [#13037](https://github.com/jdx/mise/pull/13037)

**Full Changelog**: https://github.com/jdx/mise/compare/v2026.9.4...v2026.9.5

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
## v2026.9.6
This release adds experimental project daemons backed by pitchfork, a `mise doctor project` command for project-declared diagnostic checks, and tool discovery from vfox backend plugins in `mise search`. It also changes the HTTP backend's default install layout so uninstall and prune reclaim disk space, speeds up warm `lockfile_mode = "generate"` installs and repeated OCI builds, and fixes a batch of nushell, monorepo, lockfile, brew, and Windows bootstrap issues.

## Highlights
- **Services next to tools:** `[daemons]` declares background processes and PostgreSQL/Redis presets in `mise.toml`, managed through `mise daemons` and optionally started when you enter the project. `[doctor.checks.<name>]` lets projects declare their own environment probes for `mise doctor project`.
- **Discovery and output:** `mise search`, shell completion, and interactive `mise use` now include tools published by installed vfox backend plugins, and `settings.truncate` / `--no-truncate` disable terminal-width truncation (automatically when a coding agent is detected).
- **Storage and speed:** HTTP tools now extract into their own install directory by default (opt back into deduplication with `shared_extraction = true`), warm generate-mode installs skip needless lockfile rewrites, and OCI builds share a local tool-layer cache.

## Added
- **daemons:** New experimental `[daemons]` section and `mise daemons` command family (`start`, `stop`, `restart`, `ls`, `status`, `logs`, `tui`) manage project background processes with pitchfork. PostgreSQL and Redis presets install the database as a tool (participating in lockfiles), supply connection environment variables and readiness checks, and keep project data across stop/start. Daemons with `auto = ["start", "stop"]` start when entering the project from an activated Bash, Zsh, or Fish shell and are released when the last shell session leaves. Requires `experimental = true` and pitchfork 2.25.0 or later; database presets are Unix-only and PostgreSQL uses loopback trust authentication intended for local development. ([#13085](https://github.com/jdx/mise/pull/13085) by @jdx)

  ```toml
  [settings]
  experimental = true

  [daemons]
  postgres = "18"
  redis = "8"

  [daemons.web]
  run = "npm run dev"
  port = 3000
  auto = ["start", "stop"]
  ```
- **doctor:** `mise doctor project` runs checks declared in `[doctor.checks.<name>]` with the project's environment and installed tools, reporting PASS/FAIL/error/skipped per check in text or `--json`. Checks support `description`, `hint`, `timeout` (default `10s`), `dir`, `shell`, and `os` selectors, run concurrently under the `jobs` limit, and exit nonzero when any check fails. Ordinary `mise doctor` does not run them, and hints are never executed. A follow-up aligned `dir` resolution with task conventions (config root for project configs including `~/mise.toml`, `~/` expansion), fixed head-of-line blocking when one probe hangs, and kept `nohup mise doctor project` alive on SIGHUP. ([#13062](https://github.com/jdx/mise/pull/13062), [#13089](https://github.com/jdx/mise/pull/13089) by @jdx)

  ```toml
  [doctor.checks.openssl]
  description = "OpenSSL development files are discoverable"
  run = "pkg-config --exists openssl"
  hint = "Run `mise bootstrap packages apply` to install the declared build dependencies."
  timeout = "5s"
  os = ["linux", "macos"]
  ```
- **vfox:** Tools provided by installed vfox backend plugins now appear in `mise search`, shell completion, and interactive `mise use`, namespaced as `<plugin>:<tool>`. Plugins can implement `BackendListTools` for a finite catalog and/or `BackendSearchTools` for query-driven discovery in large ecosystems; a prefixed query like `npm:eslint` is routed only to that plugin. Results are cached, slow plugins fall back to stale cache, and existing plugins need no changes. `mise registry` remains registry-only. ([#13111](https://github.com/jdx/mise/pull/13111) by @jdx)
- **cli:** New `settings.truncate` (and `MISE_TRUNCATE`, default `true`) controls terminal-width shortening of table cells and task metadata. `mise ls`, `mise config ls`, and `mise bootstrap dotfiles status` gain `--truncate` / `--no-truncate`, and output is kept complete automatically when a known coding agent is detected. ([#13112](https://github.com/jdx/mise/pull/13112) by @jdx)

  ```sh
  mise bootstrap dotfiles status --no-truncate
  ```
- **bootstrap:** `[bootstrap.macos.dock]` gains `apps`, an ordered list of pinned application paths. Status compares identity and order (ignoring Dock-added metadata), apply adds, removes, and reorders application tiles while preserving other tiles and `persistent-others`, and an empty list removes all application tiles. Paths must be absolute or home-relative `.app` bundles. ([#13075](https://github.com/jdx/mise/pull/13075) by @azohra)

  ```toml
  [bootstrap.macos.dock]
  apps = [
    "/System/Applications/Utilities/Terminal.app",
    "/Applications/Firefox.app",
  ]
  ```
- **bootstrap:** `mise bootstrap packages where brew:<formula>` prints an installed formula's stable `opt` root (for example `/opt/homebrew/opt/unzip`), so scripts can put keg-only executables on PATH without hardcoding the Homebrew prefix or Cellar version. Missing installs exit nonzero with empty stdout. ([#13083](https://github.com/jdx/mise/pull/13083) by @himkt)
- **dotfiles:** Destination `variants` can omit `source` when every variant sets a `target`; the entry key is then resolved as a relative path under `settings.dotfiles.root` instead of next to `mise.toml`. Parent traversal is rejected. ([#13087](https://github.com/jdx/mise/pull/13087) by @jdx)

  ```toml
  [dotfiles."vscode/settings.json"]
  mode = "copy"
  variants = [
    { os = "macos", target = "~/Library/Application Support/Code/User/settings.json" },
    { os = "linux", target = "~/.config/Code/User/settings.json" },
  ]
  ```
- **fmt:** `mise fmt` now sorts lists whose order has no meaning: `redactions` lexically, and task `sources`/`outputs`, `task_templates` sources/outputs, `task_config.global_inputs`, and `input_groups` by reach (`@group:` references, then globs, then literal paths). Lists containing `!` exclusions, entries starting with template syntax, or comments are left untouched, and precedence-sensitive lists such as `env_file`, `tools.*`, `includes`, and `depends` are never sorted. ([#13058](https://github.com/jdx/mise/pull/13058) by @jrandolf)
- **oci:** `mise oci build` gains `--no-cache` to bypass the new local tool-layer cache; entries live under each tool's cache directory and are removed by `mise cache clear TOOL`. ([#13056](https://github.com/jdx/mise/pull/13056) by @jdx)

## Changed
- **http:** New `http:` installations extract directly into their own install directory, so `mise uninstall` and `mise prune` now remove their files instead of leaving payloads in `$MISE_DATA_DIR/http-tarballs/`. Set `shared_extraction = true` on a tool to keep the previous deduplicated symlink layout. Existing symlinked installs keep working; `mise install --force <tool>` migrates one to independent files without disturbing other installs that share the content. Legacy `http-tarballs` entries are not reclaimed automatically. Shared raw and compressed binary caches now also include the executable filename in their key, so differently named tools no longer reuse the wrong filename. ([#13059](https://github.com/jdx/mise/pull/13059) by @jdx)
- **oci:** `mise oci push --no-cache` now bypasses both the remote registry cache and the local tool-layer cache. ([#13056](https://github.com/jdx/mise/pull/13056) by @jdx)
- **registry:** `postgres`, `redis`, and `mongodb` now prefer `conda:` backends, installing prebuilt conda-forge binaries in seconds instead of compiling through vfox; vfox and asdf remain as fallbacks. `conda:redis-server` covers Linux and macOS only. ([#13061](https://github.com/jdx/mise/pull/13061) by @jdx)

## Performance
- **lockfile:** Warm `mise install` runs in `lockfile_mode = "generate"` skip scheduling work for tools whose artifact metadata is already reusable, and skip rebuilding, serializing, and staging the lockfile entirely when nothing was installed and the on-disk lock already matches (preserving comments in the file). Explicit `mise lock`, forced provenance verification, upgrades, and new platforms still regenerate. ([#13101](https://github.com/jdx/mise/pull/13101), [#13103](https://github.com/jdx/mise/pull/13103) by @jdx)
- **oci:** `mise oci push --from BASE` no longer downloads base layers when the base and target live in the same repository, and `oci build`, `oci run`, and `oci push` share a local cache of packaged tool layers keyed on file contents, so repeated builds with overlapping tools skip tar and gzip work. ([#13055](https://github.com/jdx/mise/pull/13055), [#13056](https://github.com/jdx/mise/pull/13056) by @jdx)

## Fixed
- **nushell:** `mise activate nu` no longer throws `env_variable_not_found` on every prompt or `cd` when a variable to hide is absent from the current scope; `hide-env` is now wrapped in `try`, matching the no-op behavior of other shells. ([#13071](https://github.com/jdx/mise/pull/13071) by @i-api)
- **task:** Task-level tools are now auto-installed for tasks referenced from `run` entries, including names rendered at runtime, right before they execute; `--skip-tools` is honored and install failures are reported as task failures without blocking siblings. ([#13086](https://github.com/jdx/mise/pull/13086) by @jdx)
- **config:** `[monorepo]` settings are now merged across same-directory config layers (base plus `mise.<env>.toml` overlays): omitted fields are inherited, an overlay's `config_roots` replaces the base list, and `monorepo_root = false` in an overlay disables the root and its descendant trust. ([#13084](https://github.com/jdx/mise/pull/13084) by @jdx)
- **lockfile:** Runtime tool requests such as `mise which hk --tool hk@latest` now use the lockfile belonging to the config that effectively defines the tool, instead of merging project and global pins and reporting a false "multiple resolutions" ambiguity or selecting an overridden pin. `mise which --tool` warns when a lower-precedence config has a matching pin the effective config lacks. ([#13042](https://github.com/jdx/mise/pull/13042) by @nettlesh)
- **lockfile:** Complete lockfile generation for Packslip tools skips platforms with no published artifact while still writing supported targets, and a verified Packslip signer may now replace legacy `github-attestations` metadata on upgrade instead of being rejected as a provenance downgrade. ([#13102](https://github.com/jdx/mise/pull/13102), [#13105](https://github.com/jdx/mise/pull/13105) by @jdx)
- **upgrade:** `mise upgrade` now detects updates between letter-suffixed versions such as tmux `3.7b` to `3.7c`; `sub-N` aliases keep resolving numeric components as before. ([#13119](https://github.com/jdx/mise/pull/13119) by @jdx)
- **brew:** Formulae that are keg-only solely because macOS ships them (such as `brew:zip` and `brew:unzip`) are now linked into `<prefix>/bin` on Linux, matching Homebrew. Kegs installed by earlier mise versions stay unlinked until the next `mise bootstrap packages upgrade` or a reinstall. ([#13108](https://github.com/jdx/mise/pull/13108) by @lil-lon)
- **brew-cask:** Tap casks with `preflight_steps` or `postflight_steps` no longer fail during metadata extraction; declarative `run` steps are captured as structured steps and executed by mise, with support for `must_succeed = false`. ([#13060](https://github.com/jdx/mise/pull/13060) by @jdx)
- **bootstrap:** `mise bootstrap remote` on Windows now finds `ssh.exe` and `tar.exe` on PATH instead of failing with `required command 'ssh' not found`. ([#13117](https://github.com/jdx/mise/pull/13117) by @JamBalaya56562)
- **bootstrap:** macOS defaults status explains type mismatches, showing for example `2 (real; expected integer)` instead of two identical-looking values marked `differs`. ([#13096](https://github.com/jdx/mise/pull/13096) by @jdx)
- **dotfiles:** `mise bootstrap dotfiles track` honors the global `yes` setting for confirmations, and warns when tracking a symlink whose resolved source is not itself tracked, suggesting the command to enroll it. ([#13072](https://github.com/jdx/mise/pull/13072) by @nettlesh, [#13095](https://github.com/jdx/mise/pull/13095) by @jdx)
- **schema:** The JSON schema now models Git directory `manifest` dotfile entries, restricting explicit modes to `copy` or `symlink-each` and rejecting combinations with inline content or file-edit fields. ([#12741](https://github.com/jdx/mise/pull/12741) by @risu729)
- **asdf:** `mise asdf install` and `mise asdf reshim` no longer re-enter the full CLI dispatch, avoiding stack overflows on small-stack Linux environments; `asdf install` now follows the same implicit config trust as `mise install`. Bash completions are regenerated for the updated usage-rs word-break handling. ([#13114](https://github.com/jdx/mise/pull/13114) by @jdx)

## Registry
- Added `mpv` (`conda:mpv`, Linux and macOS) ([#13049](https://github.com/jdx/mise/pull/13049) by @i-api), `agent-browser` (`aqua:vercel-labs/agent-browser`) ([#13088](https://github.com/jdx/mise/pull/13088) by @3w36zj6), and `himalaya` (`github:pimalaya/himalaya`) ([#13091](https://github.com/jdx/mise/pull/13091) by @i-api).
- `editorconfig-checker` installs again after 4.0.1 renamed its assets and executable; the shorthand now uses the GitHub backend. ([#13098](https://github.com/jdx/mise/pull/13098) by @jdx)
- `mc` installs from MinIO's GitHub releases instead of the retired Aqua download URL that returned HTTP 410. ([#13113](https://github.com/jdx/mise/pull/13113) by @jdx)

## Documentation
- The docs landing page gains interactive diagrams for project environment switching, bootstrap machine resources, tool configuration precedence, artifact cache execution, and tracked dotfile synchronization. ([#13065](https://github.com/jdx/mise/pull/13065), [#13066](https://github.com/jdx/mise/pull/13066), [#13067](https://github.com/jdx/mise/pull/13067), [#13068](https://github.com/jdx/mise/pull/13068), [#13069](https://github.com/jdx/mise/pull/13069) by @jdx)
- The task-running guide is reorganized around finding and running tasks, passing arguments, then controlling execution. ([#13077](https://github.com/jdx/mise/pull/13077) by @azohra)

## New Contributors
- @lil-lon made their first contribution in [#13108](https://github.com/jdx/mise/pull/13108)

**Full Changelog**: https://github.com/jdx/mise/compare/v2026.9.5...v2026.9.6

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
## v2026.9.7
This release introduces `mise.lock` revision 2, which records complete transitive dependency graphs for npm tools (via embedded aube) and Python tools (via uv) in native sidecar files, and adds `mise bootstrap dotfiles conflicts` for inspecting dotfile sync conflicts before resolving them. It also lets dotfile templates consume bootstrap secrets, stops `minimum_release_age` from rejecting versions already committed to a lockfile, and closes a security gap in `history.describe_command`.

## Added
- **lock:** Lockfile revision 2 records the full dependency graph of npm tools installed by embedded aube and of `pypi:` tools installed by uv, then replays it with a strict frozen install so two projects on the same top-level version can still receive their own reviewed transitive graph. Graphs live in native sidecar files (`uv.lock` / `aube-lock.yaml` plus a manifest) under `.mise/locks/<backend-tool>/<version>/`, referenced from `mise.lock` by relative path and SHA-256 digest, so the lockfile itself stays small. Commit the sidecar directory with `mise.lock`. New lockfiles use revision 2; existing revision 0 and 1 files keep their format until you run `mise lock --upgrade`. `mise lock --bump <tool>` refreshes a tool's transitive graph even when its top-level version is unchanged, ordinary `mise install` validates and accepts hand-edited sidecars, and `mise install --locked` rejects digest mismatches until you run `mise lock`. Python graph locking requires uv 0.12.10 or newer and published wheels for the target platform; Git sources, standalone pipx installs, and free-form `uvx_args`/`pipx_args` stay version-only. ([#13131](https://github.com/jdx/mise/pull/13131), [#13146](https://github.com/jdx/mise/pull/13146) by @jdx)

  ```sh
  mise lock --upgrade        # move an existing lockfile to revision 2 and resolve graphs
  mise install --locked      # replay the recorded graphs
  mise lock --bump pypi:black  # refresh Black's dependencies without changing its version
  ```
- **pypi:** `pypi:` is now the preferred name for the Python CLI backend; `pipx:` remains fully supported as an alias with no warnings, and settings accept both `pypi.*` and `pipx.*` names. The two spellings are distinct tool identities (`pypi-black` vs `pipx-black` install directories and lock entries), so switching spelling creates a new installation. ([#13146](https://github.com/jdx/mise/pull/13146) by @jdx)
- **bootstrap:** `mise bootstrap dotfiles conflicts [PATH...]` shows a read-only comparison of the saved local and fetched remote versions of a conflicted dotfile so you can decide between `--take-remote` and `--keep-local` with full context. The default output is a unified diff including file-mode changes; `--difftool` opens the configured Git `diff.tool` (falling back to `merge.tool`) and `--tool <name>` picks one explicitly. Encrypted contents are decrypted only into private temporary files, and inspection never modifies either side or marks the conflict resolved. Bootstrap secrets are also now resolved from the same composed config maps as dotfile discovery, so root-scoped dotfile templates can use secrets declared by their bootstrap root. ([#13144](https://github.com/jdx/mise/pull/13144) by @jdx)

  ```sh
  mise bootstrap dotfiles conflicts ~/.config/mise/config.toml
  mise bootstrap dotfiles conflicts --difftool ~/.config/mise/config.toml
  ```
- **dotfiles:** Dotfile templates (`mode = "template"`) can reference `[bootstrap.secrets]` values with `{{ secret(name="...") }}`, matching managed bootstrap file templates. Dotfiles commands that render templates (`add`, `apply`, `diff`, `edit`, `status`, `unapply`) accept `--prompt-secrets`; without an available value, rendering fails closed. A full `mise bootstrap` run preflights dotfile templates before making changes, `mise bootstrap status` reports secrets used only by dotfiles, and textual diffs redact resolved secret values. ([#13140](https://github.com/jdx/mise/pull/13140) by @jdx)

  ```toml
  [bootstrap.secrets]
  api_token = "EXAMPLE_API_TOKEN"

  [dotfiles."~/.config/example/credentials"]
  source = "dotfiles/credentials.tmpl"
  mode = "template"
  ```

## Fixed
- **lock:** Installing from a committed `mise.lock` no longer fails when the locked release is younger than `minimum_release_age`. The cutoff still applies when resolving unlocked fuzzy requests and when generating or bumping a lockfile, and `npm:`/`pypi:` still forward it to unpinned transitive dependencies, but a reviewed lock entry now reproduces immediately in CI instead of waiting for the release to cool. ([#13128](https://github.com/jdx/mise/pull/13128) by @jdx)
- **config:** A `.python-version` (or other idiomatic version file) containing `system` selects the system interpreter without printing the mise-specific `@system` deprecation warning, matching the existing `.tool-versions` exception. Explicit `python@system` requests from mise configuration or command arguments still warn. ([#13132](https://github.com/jdx/mise/pull/13132) by @jdx)
- **npm:** Embedded aube is updated to 2.2.16, fixing the Bun checksum install regression and ensuring local npm tarballs keep their manifest package name. ([#13145](https://github.com/jdx/mise/pull/13145) by @jdx)
- **registry:** The `mc` shorthand uses `aqua:minio/mc` again now that the upstream Aqua registry entry is restored, with `asdf:mise-plugins/mise-mc` kept as the fallback. ([#13124](https://github.com/jdx/mise/pull/13124) by @jdx)

## Security
- **history:** `history.describe_command` is now global-only. Previously an implicitly trusted project could set it and have a later dotfiles history checkpoint execute the project-controlled command with unencrypted tracked-file diffs. The setting is honored only from system/global configuration or `MISE_HISTORY_DESCRIBE_COMMAND`; project values are ignored with a warning. ([#13134](https://github.com/jdx/mise/pull/13134) by @jdx)
- **oci:** `mise oci build` now renders dotfile templates with a restricted engine: `secret()` is rejected and the `env` context, `get_env()`, `exec()`, and `read_file()` are unavailable, so ambient credentials cannot be baked into a publishable image layer. ([#13140](https://github.com/jdx/mise/pull/13140) by @jdx)

## Breaking Changes
- **Lockfile revision 2 is not readable by older mise versions.** Newly created lockfiles use revision 2, and existing files switch only when you run `mise lock --upgrade`. Upgrade collaborators and CI to this release before committing a revision 2 `mise.lock`, and commit the `.mise/locks/` (or `.config/mise/locks/`) sidecar directory alongside it. Revision 2 `--locked` installs fail if a recorded graph is missing or its digest does not match. If you gitignore `mise.local.lock`, also ignore its matching sidecar subdirectory (for example `.mise/locks/mise.local/`).
- **`history.describe_command` in project configuration is ignored.** Move it to `~/.config/mise/config.toml` or set `MISE_HISTORY_DESCRIBE_COMMAND`.
- **`mise oci build` dotfile templates** can no longer call `secret()`, `get_env()`, `exec()`, or `read_file()` or read the `env` context.

**Full Changelog**: https://github.com/jdx/mise/compare/v2026.9.6...v2026.9.7

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
## v2026.9.8
Dotfile management moves to the top level as `mise dot`, Homebrew bootstrap installs run their download, extraction, and linking stages concurrently, and several install paths are corrected: embedded aube reputation gates now report the real reason and honor `--yes`, PyPI tools fall back to version-only installs when a dependency graph cannot be built, lazy tools no longer trigger `missing:` warnings, and lockfiles no longer resurrect disabled backends.

## Added
- **dotfiles:** The full dotfiles command tree is now available as `mise dotfiles`, with `mise dot` as a short alias. `mise bootstrap dotfiles` remains supported and all three spellings share the same behavior, including bootstrap hooks around `apply`. Generated history-watch services now invoke `mise dot watch`. ([#13158](https://github.com/jdx/mise/pull/13158) by @jdx)

  ```sh
  mise dot track ~/.zshrc
  mise dot status
  mise dot history
  ```
- **dotfiles:** Enabling encryption on a file that was previously saved in plaintext left older commits that blocked sync. `mise dot sync --allow-plaintext-history` lets that history reach the origin for one run, and the global-only setting `settings.history.allow_plaintext_history = true` (default `false`, env `MISE_HISTORY_ALLOW_PLAINTEXT_HISTORY`) does the same for sync, publish, the history watcher, and incoming history on pull. New saves still follow the file's encryption policy; the history guide also documents how to remove the old commits instead. ([#13175](https://github.com/jdx/mise/pull/13175) by @jdx)
- **registry:** Added `poppler` (`conda:poppler`), providing `pdftotext`, `pdfinfo`, `pdftoppm`, `pdftocairo`, `pdfunite`, and the other Poppler PDF utilities. ([#13133](https://github.com/jdx/mise/pull/13133) by @i-api)

## Fixed
- **npm:** Embedded aube reputation gates (low weekly downloads, similar-name, new package name) no longer surface as a misleading `user aborted mise add` error when stdin is closed or no terminal is attached. Non-interactive installs now report the measured signal (for example 569 weekly downloads against the 1000 threshold) and suggest the mise-native fix, `allow_low_downloads = true` on the tool; an explicit "no" reports `user declined to add <package>`. An explicit CLI `--yes` now reaches the aube prompt and approves it, including auto-installs through `use`, `exec`, `run`, `shell`, and `upgrade`; CI mode and a configured `yes = true` setting alone do not approve reputation gates. ([#13123](https://github.com/jdx/mise/pull/13123) by @jdx)
- **pypi:** Ordinary `mise install` of `pypi:`/`pipx:` tools no longer fails when a uv dependency graph cannot represent the package or its configuration, such as a source-only dependency or free-form `uvx_args`/`pipx_args`. mise warns and falls back to the version-only install path, reusing an existing version-only installation on later runs. `mise lock` and `mise install --locked` remain strict and still reject unsupported arguments or dependencies without usable wheels. ([#13170](https://github.com/jdx/mise/pull/13170) by @jdx)
- Tools declared with `lazy = true` are no longer reported as `missing: <tool>` when entering a project or running a bare `mise install`, regardless of `status.missing_tools`; ordinary missing tools are still reported as before. ([#13169](https://github.com/jdx/mise/pull/13169) by @jdx)
- **backend:** Backend discovery from lockfiles now skips backends listed in `disable_backends`. When a parent `mise.lock` pins a shorthand such as `yarn` to `asdf:yarn` and a child project disables asdf, `mise tool yarn --backend` and a fresh child `mise lock` now select the first enabled recorded backend or fall back to the enabled registry backend (`aqua:yarnpkg/berry`) instead of the disabled pin. The parent lockfile is left unchanged and explicitly installing a disabled backend still fails. ([#13178](https://github.com/jdx/mise/pull/13178) by @jdx)

## Changed
- **bootstrap:** `mise bootstrap packages apply` installs Homebrew packages substantially faster. Formula metadata for each dependency frontier is fetched concurrently, bottles are extracted, relocated, signed, and receipted concurrently, and each job now downloads and prepares its own bottle so prepared bottles are committed as soon as dependency order allows. All stages respect the existing `jobs` limit with no new settings; Cellar commits and prefix linking stay dependency-ordered, `opt/<name>` is linked last so an interrupted install cannot look complete, and a failure cancels queued work while cleaning up in-flight staging. On Apple silicon, a fresh install of `brew:jq brew:tree brew:wget brew:just brew:shellcheck` dropped from roughly 6.6s to 4.0s, and dependency resolution for `brew:ffmpeg` from 288ms to 112ms. ([#13151](https://github.com/jdx/mise/pull/13151), [#13152](https://github.com/jdx/mise/pull/13152), [#13155](https://github.com/jdx/mise/pull/13155) by @jdx)

## Documentation
- The npm backend, PyPI backend, and `mise.lock` guides now open with quick-start and everyday workflows (`mise use node@24 npm:prettier`, `mise use python@3.14 uv pypi:black`, `mise lock`, `mise install --locked`) and group dependency-graph locking, sidecar management, and strict-mode details afterward. The lockfile guide clarifies that URL-lock exemptions do not exempt dependency graphs from validation. ([#13149](https://github.com/jdx/mise/pull/13149) by @jdx)

**Full Changelog**: https://github.com/jdx/mise/compare/v2026.9.7...v2026.9.8

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
## v2026.9.9
The dotfiles history watcher no longer records files as deleted when a checkpoint and a sync compose snapshots at the same time, `mise dot track --encrypt` enrolls a file with encrypted history from its first checkpoint, `mise bootstrap --adopt --replace-history` discards unrelated local history in one shot, and `pypi:` tools gain lock-aware `with`, `expose`, and `dependency_prereleases` options. Also fixed: `packslip:` installs from private GitHub repositories, stale history watchers after upgrading, global npm tools being reinstalled under `lockfile = true`, and the `--` separator in activated PowerShell sessions.

## Added
- **dotfiles:** `mise dot track --encrypt` writes `encrypt = true` into the tracked declaration and encrypts the initial baseline checkpoint, for files that must never have plaintext history. `[history.encryption].recipients` must be configured first; if the encrypted baseline cannot be saved, enrollment fails closed and rolls back the declaration without committing history metadata. Run it as a standalone command rather than inside `mise dot capture`. Enabling encryption on a file that already has plaintext history does not rewrite that history. ([#13180](https://github.com/jdx/mise/pull/13180) by @jdx)

  ```sh
  mise dot track ~/.config/app/credentials --encrypt
  ```
- **bootstrap:** Fresh `mise bootstrap --adopt` now compares existing live files against the incoming setup before creating any local history, so identical files adopt the origin's history instead of being rejected as an unrelated root (for example right after the history store was removed). Differences still pause for an explicit decision. For machines that genuinely hold unrelated local history, `--replace-history` discards it and adopts the setup repository's branch in one shot; `--dry-run` previews the local and origin commits, and a failed replacement restores the previous branch and sync state. Ordinary sync never replaces divergent history and there is no persistent force setting. ([#13182](https://github.com/jdx/mise/pull/13182) by @jdx)

  ```sh
  mise bootstrap --adopt <url> --replace-history --yes
  ```
- **pypi:** Three new tool options express common uv install behavior without opaque `uvx_args`, and unlike free-form arguments they participate in dependency graph locking: `with` installs extra requirements, `expose` installs extra requirements and links their executables (requires uv 0.8.5 or newer), and `dependency_prereleases` sets uv's prerelease policy (`disallow`, `allow`, `if-necessary`, `explicit`). Setting any of them selects uv as the installer. `uvx_args` and `pipx_args` remain available as version-only escape hatches. The Ansible and Azure CLI registry entries now use these options by default; if you force pipx for one of them, clear the default with an empty list, e.g. `"pypi:ansible" = { version = "latest", uvx = false, expose = [], pipx_args = "--include-deps" }`. ([#13181](https://github.com/jdx/mise/pull/13181) by @jdx)

  ```toml
  [tools]
  "pypi:azure-cli" = { version = "latest", with = ["pip"], dependency_prereleases = "allow" }
  "pypi:ansible" = { version = "latest", expose = ["ansible-core"] }
  ```
- **registry:** Added `nubr` (`npm:@nubjs/runner`), the Nub project's TypeScript runner for a file, `package.json` script, or installed bin on plain Node. ([#13191](https://github.com/jdx/mise/pull/13191) by @colinhacks)

## Fixed
- **dotfiles:** With `history.sync = "sync"` and a running watcher, a checkpoint could record a sorted prefix of tracked files as deleted even though they were untouched on disk; those deletions then synced to other machines and removed their copies. Two compositions in one process (the watcher's checkpoint and the sync it started) shared a single scratch git index, and one resetting it mid-flight truncated the other's tree. Each composition now uses its own scratch index, and indexes left by killed processes are swept. Files recorded as falsely deleted are still in history and can be restored from an earlier checkpoint. ([#13195](https://github.com/jdx/mise/pull/13195) by @jdx)
- **dotfiles:** A history watcher started before mise 2026.9.5 (which moved history locks into `$MISE_STATE_DIR/history/`), or started with a different `MISE_STATE_DIR` than the shell, kept running the old process without watching the current store, while `mise bootstrap services apply` considered the unchanged service converged and skipped it. `services apply` now restarts a `history-watch` service whose process is not watching this store, and `mise doctor` and `mise dot status` report "running but not watching this store" instead of "not running" (`service-not-watching` in `mise dot status --json`). Users already in this state are recovered by running `mise bootstrap services apply`. ([#13190](https://github.com/jdx/mise/pull/13190) by @jdx)
- **npm:** With `lockfile = true` in effect, an npm tool pinned in the global config was resolved with a graph-specific install identity that no automatic flow could persist, so every `mise exec` treated the installed tool as unsatisfied, re-ran an install pass, and warned that it was missing. Global requests now stay version-only unless resolved from an explicitly generated revision 2 global lockfile; opt in with `mise lock --global`. ([#13186](https://github.com/jdx/mise/pull/13186) by @jdx)
- **packslip:** Installing from a private GitHub repository failed with `404 Not Found` on the manifest because GitHub only serves private release assets through its API, not the `releases/download/` URLs a packslip records. mise now falls back to the API asset endpoint using the same credentials as the `github:` backend (`MISE_GITHUB_TOKEN`, `GITHUB_API_TOKEN`, or `GITHUB_TOKEN`) with no configuration changes; signature, identity, digest, and size verification are unchanged. Tags containing `/` (such as `@biomejs/biome@2.5.2` or monorepo `tool/v1.0.0` tags) and `#` are also resolved correctly now. Non-GitHub hosts and GitHub Enterprise are not covered. ([#13188](https://github.com/jdx/mise/pull/13188) by @jdx)
- **activate:** In a shell activated with `mise activate pwsh`, `mise exec -- pnpm --version` failed with `unexpected argument '--version'` because PowerShell's parameter binder removes the first bare `--` before the `mise` wrapper function sees its arguments. The wrapper now recovers the separator from the raw invocation line, fixing `mise exec`/`mise x`, `mise tasks add`, `mise dotfiles capture`, `mise oci run`, `mise generate git-pre-commit`, and `mise bootstrap`; `mise run` was not affected. Open sessions pick up the fix the next time `mise activate pwsh` runs (normally at shell start). The doubled `mise exec -- -- cmd` workaround now fails in an activated shell, as it always did without activation, so drop back to a single `--`. ([#13202](https://github.com/jdx/mise/pull/13202) by @jdx)
- **registry:** The `dbt-fusion` install test now expects `dbt <version>`, matching what `dbt --version` actually prints. ([873c400](https://github.com/jdx/mise/commit/873c4009ebb92a34cbaffd88e1304bcac203784b) by @jdx)

## Documentation
- The GitHub star count on mise.jdx.dev now also appears in the nav overflow menu at medium viewport widths. ([#13193](https://github.com/jdx/mise/pull/13193) by @jdx)

**Full Changelog**: https://github.com/jdx/mise/compare/v2026.9.8...v2026.9.9

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
## v2026.9.10
New settings let mise manage a tool without claiming its command names (`shims.exclude`) and approve non-registry npm dependencies (`allow_exotic_deps`), `mise dot pull` can decide every sharing conflict at once, and vfox plugin hooks gain `cmd.stream` plus a working `cmd.exec` timeout. On the fix side, `mise run` now survives Ctrl-C on Windows instead of orphaning `cmd.exe`, fish shells launched through shims start much faster with correct PATH order, and several task-resolution, lockfile, and Homebrew cask bugs are corrected.

## Highlights
- **Control over what mise puts on PATH and what it installs:** `settings.shims.exclude` keeps names like `python` resolving to the OS while mise still manages the tool; `allow_exotic_deps` approves specific npm packages fetched from git or tarball URLs; exact `packslip:` pins install during a `minimum_release_age` cooling window; and `mise upgrade --bump` keeps SemVer build metadata such as `+k3s1`.
- **Dotfiles sharing on a second machine:** `mise dot pull --take-remote-all` / `--keep-local-all` resolve all conflicts in one command, paths that cannot be decided are held rather than aborting the pass, and a directory sitting where a tracked file belongs is now reported as exactly that.
- **Task and shell reliability:** Windows Ctrl-C shuts tasks down cleanly, a task's own name always beats another task's alias, glob expansions no longer drop file tasks, Bash completion of `ns:task` names no longer duplicates the prefix, and fish startup through `mise exec`/shims is no longer quadratic in the number of tools.

## Added
- **shims:** `settings.shims.exclude` (env `MISE_SHIMS_EXCLUDE`) lists command names mise never creates shims for. The tool stays installed and version-qualified names like `python3.12` still resolve through mise, but the excluded name resolves to whatever else is on `PATH`; existing shims for those names are removed on the next `mise reshim`. Note that under `mise activate` without `--shims` the tool's `bin` directory still joins `PATH`, and excluding `python3` means `python3 -m venv` silently uses the system interpreter. ([#13266](https://github.com/jdx/mise/pull/13266))

  ```toml
  [settings.shims]
  exclude = ["python", "python3", "pip", "pip3"]
  ```
- **npm:** `allow_exotic_deps` approves dependencies that aube's `blockExoticSubdeps` gate would otherwise block because they come from a git, `file:`, or direct tarball URL. List package names to exempt only those (the gate stays on for the rest of the graph), or set `true` to exempt the whole graph. Applies to the `aube` and `aube_cli` installers. Embedded-aube installs now also warn when `install_env` is set, since it never reached the in-process installer. ([#13231](https://github.com/jdx/mise/pull/13231))

  ```toml
  [tools]
  "npm:@gmickel/gno" = { version = "2.3.0", allow_exotic_deps = ["xlsx"] }
  ```
- **dotfiles:** `mise dot pull --take-remote-all` and `--keep-local-all` decide every pending conflict at once, with per-path `--take-remote`/`--keep-local` naming exceptions. The two blanket flags are mutually exclusive, and paused-sync and adoption messages now point at them. ([#13233](https://github.com/jdx/mise/pull/13233))

  ```sh
  mise dot pull --take-remote-all --keep-local ~/.bashrc
  ```
- **bootstrap:** Every string value in `[bootstrap.linux.systemd.units]` and `[bootstrap.macos.launchd.agents]` is rendered as a template before the unit file or plist is written, so `{{ config_root }}/.env` in `environment_file` resolves to the declaring config's directory. Values without template syntax (including `%h` and `$HOME`) pass through untouched, `exec()` is rejected, and a unit whose template fails is skipped by name without blocking the others. `[bootstrap.services]` is not yet templated. ([#13227](https://github.com/jdx/mise/pull/13227))
- **hooks:** Each `MISE_INSTALLED_TOOLS` entry passed to `postinstall` hooks now carries `requested_version` (for example `latest`, `22`, or an alias) alongside the resolved `version`, so a hook can tell a floating request from a pin. The field is always present; existing hooks reading `name`/`version` are unaffected. ([#13274](https://github.com/jdx/mise/pull/13274))
- **vfox plugins:** `cmd.stream` runs a command with stdin connected and stdout/stderr streamed to the terminal, for hooks that genuinely need input such as a login or license prompt; it pauses the progress renderer and holds the terminal exclusively while it runs. `cmd.exec` and `os.execute` now detach stdin unless `--raw` is set, matching every other subprocess mise spawns, so a plugin that read stdin through `os.execute` should switch to `cmd.stream`. ([#13261](https://github.com/jdx/mise/pull/13261))
- **vfox plugins:** The `timeout` option on `cmd.exec` (and `cmd.stream`) now works instead of being silently ignored. It takes seconds (fractions allowed); on expiry the spawned shell is killed and the call raises a catchable error. Only the shell mise spawned is killed, so background processes it started may keep running. ([#13263](https://github.com/jdx/mise/pull/13263))

  ```lua
  local ok, err = pcall(cmd.exec, "some-tool sync", { timeout = 30 })
  ```

## Fixed
- **task:** On Windows, pressing Ctrl-C during `mise run` no longer kills mise immediately and leaves a `cmd.exe` behind stuck on `Terminate batch job (Y/N)?`. The first Ctrl-C lets running commands exit and stops scheduling new tasks; a second one takes the remaining process tree down. Tasks ended by the console are reported as interrupted instead of failing with exit code -1073741510. ([#13226](https://github.com/jdx/mise/pull/13226))
- **task:** A task's own name now always wins over another task's alias. Previously a parent config's `tests` task with `alias = "test"` could shadow a `test` task in the current directory, depending on alphabetical order. Aliases still resolve wherever no task claims that name. ([#13230](https://github.com/jdx/mise/pull/13230))
- **task:** Glob expansions such as `mise run '//...:lint'` or `'*:lint'` no longer silently drop file tasks (`mise-tasks/lint.sh`) when a sibling package has an exact match. The same-package dedup that stops `hello` and `hello.sh` running twice is preserved. ([#13277](https://github.com/jdx/mise/pull/13277))
- **completions:** Bash completion of namespaced tasks like `update:deps:no<TAB>` no longer produces `update:deps:update:deps:no-cooldown`. Reinstall the script with `mise completion bash --install` if yours predates the prefix-aware wrapper. ([#13276](https://github.com/jdx/mise/pull/13276))
- **exec:** Launching fish through `mise exec` or a shim emitted one `fish_add_path` per directory, which made startup quadratic (over 1s with ~80 tools) and reversed mise's PATH order relative to bash. A single batched call restores both. ([#13235](https://github.com/jdx/mise/pull/13235))
- **dotfiles:** A blanket `--take-remote-all`/`--keep-local-all` no longer aborts the whole pass when one path cannot be decided (a directory on the live side, or unsaved local changes under `--keep-local-all`). Decisions for the other conflicts are recorded, and the error names the held paths so fixing just those finishes the setup. ([#13239](https://github.com/jdx/mise/pull/13239), [#13242](https://github.com/jdx/mise/pull/13242))
- **dotfiles:** A directory or unreadable path where the repository has a file is now reported by `mise dot conflicts`, `mise dot status`, and `mise doctor` as exactly that, with advice to move it aside, instead of as a "changed type" conflict that `--take-remote`/`--keep-local` cannot resolve. Git or process failures while reading a live file now stop the sync with their own error instead of posing as a conflict. ([#13249](https://github.com/jdx/mise/pull/13249))
- **upgrade:** `mise upgrade --bump` preserves SemVer build metadata when rewriting a pin, so k3s bumps to `1.37.0+k3s1` rather than a nonexistent `1.37.0`, and Temurin keeps its `+7` build number. Coarser pins like `1.36` still bump to `1.37`. ([#13258](https://github.com/jdx/mise/pull/13258))
- **packslip:** An exactly pinned version (for example `"packslip:github.com/jdx/hk" = "2.0.1"`) now installs and locks while still inside its `minimum_release_age` window, as the setting documents. Fuzzy requests such as `"2"` or `latest` still wait out the cutoff. ([#13251](https://github.com/jdx/mise/pull/13251))
- **install:** `MISE_LOCKED=1 mise install <tool>` no longer warns about unrelated (often global) tools missing from the lockfile; installing the requested tool or a bare `mise install` still fails if that tool is not locked. ([#13259](https://github.com/jdx/mise/pull/13259) by @jamescassell)
- **pypi:** `mise lock` no longer fails when a `with`/`expose` requirement is pinned to a release needing a newer Python than the tool itself (e.g. `mkdocs` 1.6.1 with `mkdocstrings==1.0.6`). The sidecar's `requires-python` is now intersected across every pinned requirement; unpinned requirements and pins behind an interpreter marker leave the range alone. Existing lockfiles remain valid. ([#13252](https://github.com/jdx/mise/pull/13252))
- **aqua:** With `minimum_release_age` set, the latest release no longer falls back to an older version when the hosted version list lags GitHub. The release date from the `/releases/latest` response mise already fetched is used directly, with no extra requests. ([#13228](https://github.com/jdx/mise/pull/13228))
- **backend:** Tools whose registry entry splits across backends at a version boundary (like `hk`) now list versions from the backend that actually resolves, so `mise ls-remote hk@1.57` and `mise latest hk@1.57` return `1.57.0` instead of nothing. Also covers backends promoted by `MISE_DISABLE_BACKENDS`, platform-scoped entries, and lockfile pins. ([#13238](https://github.com/jdx/mise/pull/13238))
- **http:** GitHub answers an exhausted rate limit with 403 rather than 429, so mise never retried it. A 403 carrying `x-ratelimit-remaining: 0` or `retry-after` is now retried like a 429 under `http_retries`; a 403 with quota remaining is still treated as a refusal. Default backoff (~5s total) will not outlast a long reset, but brief contention no longer fails an install outright. ([#13256](https://github.com/jdx/mise/pull/13256))
- **skills:** `mise skills ls` and `mise skills sync` now warn when a packslip declares a skill the install does not hold, with the reason (`skills.fetch` off, `packslip.exec` off, or a failed download), instead of looking identical to "no skills declared". After an install with `skills.auto_sync` off, a one-time hint points at `mise skills sync`. `--json` output is unchanged. ([#13275](https://github.com/jdx/mise/pull/13275))
- **brew:** `adopt` is now honored for casks named on the command line (`mise bootstrap packages apply brew-cask:menuwhere`) and for tap-qualified names and aliases like `brew-cask:homebrew/cask/firefox`, so existing app bundles are adopted rather than replaced and macOS keeps their Privacy & Security grants. ([#13262](https://github.com/jdx/mise/pull/13262))
- **brew:** Tap formulae declaring requirement symbols such as `depends_on :macos` no longer make `bootstrap packages` try to fetch a formula named `macos` and abort the whole run with a 404. ([#13240](https://github.com/jdx/mise/pull/13240) by @waynehoover)
- **brew:** Tap cask metadata evaluation now understands `appdir` and `HOMEBREW_PREFIX` interpolation, and casks whose app bundle sits in a nested archive directory (`app "nested/Example.app"`) install as `Example.app` instead of being rejected as a relative target; duplicate app targets are rejected before anything is downloaded. ([#13138](https://github.com/jdx/mise/pull/13138) by @Guria, [#13199](https://github.com/jdx/mise/pull/13199) and [#13200](https://github.com/jdx/mise/pull/13200) by @soodoh)
- **bootstrap:** Selecting a Ruby to evaluate third-party Homebrew taps skips mise shims, which the metadata sandbox could not load, so package bootstrap no longer fails when Ruby is installed through mise. ([#13198](https://github.com/jdx/mise/pull/13198) by @jacobbednarz)

## Documentation
- The dotfiles history guide now explains encryption recipients (SSH keys, `age-keygen`, recovery keys) and warns that passphrase-protected SSH keys and plugin-only recipients cannot decrypt in the background; the setup guide covers adopting onto a machine that already has the files and using non-GitHub Git hosts. ([#13232](https://github.com/jdx/mise/pull/13232))
- The PyPI backend's locking limitations now point at the lockable `with`, `expose`, and `dependency_prereleases` options. ([#13222](https://github.com/jdx/mise/pull/13222))

## New Contributors
* @waynehoover made their first contribution in [#13240](https://github.com/jdx/mise/pull/13240)

**Full Changelog**: https://github.com/jdx/mise/compare/v2026.9.9...v2026.9.10

## 💚 Sponsor mise

mise is built and maintained by [@jdx](https://github.com/jdx), an open source developer at [**entire.io**](https://entire.io/), the title sponsor of his open source work.

If mise saves you or your team time, please consider becoming an [individual or company sponsor](https://jdx.dev/sponsors.html). Your support funds ongoing development and helps keep mise fast, free, and independent.
