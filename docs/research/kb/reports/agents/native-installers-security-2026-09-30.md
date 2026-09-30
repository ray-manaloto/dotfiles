# Security lens: native installers for agy, codex and claude (2026-09-30)

Lane: security review (read-only on the host; writes only this file).
Status: COMPLETE. The measurements are listed first (M1–M20), followed by the findings (S1–S12).

Subject: `docs/specs/native-cli-installers-2026-09-30.md` (the **spec**), plus its input `native-installers-2026-09-30.md`
(**R-chan**).

Scope:
- the supply chain of each native installer (curl|sh, signature, checksum, update channel, auto-update without review),
  compared with the mise backends pinned in the locks;
- credential exposure;
- what a compromised update could reach on this host.

## Measurements log (appended as taken)

- M1. **`codesign -dv` does not detect tampering.** I copied `codex-code-mode-host` (0.159.2) into the scratchpad and
  flipped one byte at offset 21786624; `cmp -l` shows 1 differing byte.
  - The tampered copy: `codesign -dv` gives **rc=0 and `TeamIdentifier=2DC432GLL2`**. `codesign --verify --strict` gives
    rc=1 ("invalid signature (code or signature have been modified)").
  - Control, the untouched copy: `--verify` gives rc=0. With
    `-R='anchor apple generic and certificate leaf[subject.OU] = "2DC432GLL2"'` it gives rc=0; with the wrong team
    `EQHXZ8M8AV` it gives **rc=3** ("failed to satisfy specified code requirement").
- M2. **Team IDs re-derived on host binaries** (spec P22 is an inherited number, rule 6):
  - `~/.local/bin/agy` 1.1.12: Google LLC EQHXZ8M8AV.
  - codex 0.159.2: OpenAI OpCo, LLC 2DC432GLL2.
  - claude 2.1.286: Anthropic PBC Q6L2SF6YDW.
  - mise `antigravity-cli/1.2.13/antigravity` and `1.2.11/agy`: EQHXZ8M8AV.
  - `--verify --strict` gives rc=0 on all of them. **P22 CONFIRMED.**
- M3. **Cost of `--verify --strict`:** agy 0.52 s, codex 0.75 s, claude 0.51 s. That is about 1.8 s per session for three
  binaries.
- M4. **No quarantine xattr** on any of the three native binaries: `xattr -l` shows only `com.apple.provenance`. Gatekeeper
  therefore never assessed them at first launch, so the doctor check is the only signature check that ever runs.
- M5. **Self-updates landed today without review:**
  - claude `~/.local/bin/claude` now points to **2.1.286**, mtime `Sep 30 14:30`. R-chan measured 2.1.285 earlier today.
  - codex `current` now points to 0.159.2, mtime `Sep 30 10:14`.
  - codex keeps 9 retained releases (0.151.0 through 0.159.2) and claude keeps 4 (2.1.283 through 2.1.286).
- M6. **agy self-updates inside mise's install dirs.** 9 of 23 version dirs hold a replaced regular-file `agy` instead of
  the aqua `agy -> antigravity` symlink: 1.1.5, 1.1.8, 1.1.20, 1.1.21, 1.1.23, 1.1.25, 1.2.0, 1.2.10 and 1.2.11.
  **R-chan §4 CONFIRMED.**
- M7. **Installers fetched, not executed**, into the scratchpad. Their sha256 values match R-chan's:
  - agy: `ee1ea43c…c640`, 239 lines, no redirect.
  - claude: `3a68d340…a944`. `claude.ai/install.sh` redirects once (302) to
    `downloads.claude.ai/claude-code-releases/bootstrap.sh`.
  - codex: `150e3cf6…28bf6`. `chatgpt.com/codex/install.sh` redirects once to `releases.openai.com/codex/install.sh`.
- M8. **claude bootstrap runs the latest binary even for a pinned install.**
  - `:148-149`: `# Always download latest version`, then `version=$(download_file "$DOWNLOAD_BASE_URL/latest")`.
  - `:229`: `"$binary_path" install ${TARGET:+"$TARGET"}`.
  - The integrity check at `:158-217` is sha256 against the same-origin `manifest.json`. There is no `.sig` check.
- M9. **agy installer:**
  - `:57-64`: when `agy` already exists it **exits 0** without installing.
  - `:188-193`: sha512 against a same-origin manifest.
  - `:225`: `xattr -d com.apple.quarantine`.
  - `:233/:236`: `"$BINARY_PATH" install … || true`, so the new binary runs straight away and its failure is swallowed.
  - It extracts only `antigravity` and writes it as `agy` (`:209`, `:215`). **The native install ships no `antigravity`
    name.**
- M10. **codex installer:**
  - It prefers `releases.openai.com`, with a GitHub fallback (`:178-207`). Either way the digest comes from the same
    origin (`:433-472`, `:555-563`).
  - It appends a `# >>> Codex installer >>>` PATH block to the profile (`:611-642`). That block is present on this host
    at `~/.zprofile:27-29`.
- M11. **The codex daemon updater is not running now.** The pid files name pids 66052 (updater) and 9064 (app-server);
  `ps -p` finds neither. `auto-update-version` = `0.159.2-aarch64-apple-darwin`, mtime `Sep 30 10:14`.
  `app-server-daemon/settings.json` is absent, so the updater defaults to ON whenever the daemon runs.
- M12. **Credential stores the user can read** (names, modes and sizes only; no contents read). All are 0600, which is
  no barrier to code running as the same user:
  - `~/.codex/auth.json` (4109 B);
  - `~/.gemini/{oauth_creds.json, jetski-standalone-oauth-token, mcp-oauth-tokens-v2.json}`;
  - `~/.config/gh/hosts.yml`;
  - `~/.ssh/id_ed25519`;
  - `~/.docker/.token_seed`.

  `SSH_AUTH_SOCK` is SET, so the agent socket can be used without reading any key.
- M13. **The ambient env carries 56 credential names by policy** (`doctor.toml [fnox].env_true`). They include
  `DOPPLER_TOKEN`, `AGE_PRIVATE_KEY`, `REPO_RECOVERY_AGE_IDENTITY_20260813`, `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`,
  `GITHUB_PAT_TOKEN`, `MISE_GITHUB_TOKEN` and `GEMINI_API_KEY`. Presence flags in this shell: `DOPPLER_TOKEN` SET,
  `GITHUB_TOKEN` SET, `GEMINI_API_KEY` SET.
- M14. **The ambient `GITHUB_TOKEN` is powerful.** I read only the `X-Oauth-Scopes` header of `gh api -i /user` (rc=0),
  never the value. Its scopes are **`repo, workflow, write:packages, admin:org`**, plus reads. `gh auth status` reports
  that the GITHUB_TOKEN account is active and the keyring token is inactive.
- M15. **There is no supply-chain cooldown today:**
  - mise `minimum_release_age = "0s"` at `mise.toml:148`, `shared.toml:24` and global `config.toml:10` (and per tool at
    `:85-100`).
  - Renovate uses `minimumReleaseAge: "1 hour"` (`renovate.json:9`), and minor/patch/digest updates **automerge**
    (`renovate.json:55-63`, `platformAutomerge`).
  - claude `~/.claude/settings.json`: `"autoUpdatesChannel": "latest"`.
  - `AGY_CLI_DISABLE_AUTO_UPDATE` is ABSENT from the env.
- M16. **The CI claude install is `curl | bash`** (`.github/actions/setup-claude-code/action.yml:45`). Callers are
  `ci.yml:111` and `autofix.yml:68`. Both jobs have `permissions: contents: read` and `persist-credentials: false`, and
  neither passes any secret in its env (`ci.yml:87-99`, `autofix.yml:14-15, :54`).
- M17. **The global mise config holds no secret values.**
  - `[env]` keys are build and MDE paths plus `_` (fnox references).
  - The regex `^[A-Z_]*(TOKEN|KEY|SECRET|PASSWORD)… = "…"` finds 0 matches. It is armed: the synthetic
    `FOO_TOKEN = "abc"` gives 1.
  - The live file is 0600. 8 of the 12 prior backups are 0644, which predates this work.
- M18. **claude 2.1.286 binary strings.** Hit counts:
  - `manifest.json.sig`: 0;
  - `claude-code.asc`: 0;
  - fingerprint fragments (upper and lower case): 0;
  - `BEGIN PGP`: 0;
  - `manifest.json`: 27;
  - `downloads.claude.ai`: 23;
  - positive control `DISABLE_AUTOUPDATER`: 11;
  - fresh nonce: 0.

  **This is LIKELY evidence that the self-update and `claude install` path checks no GPG signature**, which closes
  R-chan §7's gap as "likely no". It rests on string absence, not a code read.
- M19. **Shadow scan of the PATH entries ahead of `~/.local/bin`.** `~/.local/bin` sits at position 185 of 215 PATH
  entries, and entries 2–180 are mise install dirs.
  - The only `claude`/`codex`/`agy`/`antigravity` hits ahead of it are the ones this spec removes:
    `installs/antigravity-cli/1.2.13/{agy,antigravity}` and `shims/{codex,agy,antigravity}`.
  - Control arm: the same loop over the full PATH finds `~/.local/bin/claude`.
  - The lookalike packages ship only `omc`, `omc-cli`, `oh-my-claudecode` and `omx`.
- M20. **CPython 3.14 follows a redirect from https to http.** `urllib/request.py:676`, in `http_error_302`, accepts any
  redirect whose scheme is in `('http','https','ftp','')`, so the default opener follows an https→http downgrade.

## Findings

Severity reflects impact on THIS host, counting what the spec adds or relies on. Pre-existing exposure that the spec
leaves unchanged is marked as such, because the spec's §4 C9 asserts it.

### S1 — HIGH: the spec's Team ID check uses `codesign -dv`, which passes a tampered binary

- **Where:** spec §3a `find_stale_resolutions`, clause (3): a "codesign callable returns None for unsigned", i.e. it
  parses a TeamIdentifier. Also §4 C7 ("`codesign -dv` once per binary") and §5 L5
  (`codesign -dv --verbose=2 … Team ID`).
- **Evidence:** M1. A one-byte tamper still reports `TeamIdentifier=2DC432GLL2` with rc=0 under `-dv`.
  `--verify --strict` returns rc=1 on the tampered copy.
- **Why it matters:** M4 shows there is no quarantine xattr, so Gatekeeper never assessed these binaries. C9 names this
  check as the whole compensating control for dropping the lock digests, so as specified it certifies nothing about
  integrity.
- **Fix:** run
  `codesign --verify --strict -R='anchor apple generic and certificate leaf[subject.OU] = "<TEAM_ID>"' <realpath>` and
  treat rc as the verdict: 0 is valid and the right team, 1 is invalid or modified, 3 is the wrong team. Both non-zero
  arms were measured in M1.
  - Cost is 0.5–0.75 s per binary (M3), about 1.8 s per session. That fits C7 if the check runs only on the first hit.
  - Add a unit arm that runs the REAL `codesign` against a scratch copy with one flipped byte and requires a finding. A
    stubbed codesign callable certifies only the parser, not the call.

### S2 — HIGH (framing): the Team ID and currency checks are not a guard against a compromised update, but C9 and Q7 present them as one

- **Where:** §4 C9 says "stronger than any same-origin checksum, and stronger than the TOFU lock hashes it replaces".
  Q7 says "leave self-update ON, with the doctor's LIVE currency and Team ID checks as the guard".
- **What the Team ID check actually proves:** the bytes came from the vendor's signing identity. That is a different
  property from "the bytes we reviewed". Once S1 is fixed it detects non-vendor substitution, such as a PATH hijack or a
  file dropped by another tool. It does **not** detect:
  - a malicious build that is validly signed (a compromised vendor pipeline or signing key);
  - a **downgrade** to an older, vendor-signed release. Nine codex and four claude releases are retained on disk (M5),
    and a same-user attacker can re-point `current` or the `claude` symlink;
  - anything the unsigned installer or updater **scripts** do: rc edits (M10), and `agy install || true` (M9).
- **The currency check** flags a native copy that *lags*. It is satisfied by a malicious *latest*.
- **Timing:** both checks run only at SessionStart, after new code has already executed with the full env (S3).
- **Fix:** reword C9 to say that Team ID covers vendor identity, not version or bytes, and that neither check is
  preventive. Reword Q7 so the accepted risk is explicit. Pair it with S4, the only preventive lever that exists.

### S3 — HIGH (pre-existing, unchanged by the spec, but the spec should state it): what a compromised update reaches

An update of any of the three CLIs runs as `rmanaloto`, with the environment of whatever launched it. For agy and claude
that is the CLI process itself; for codex it is the daemon that runs `install.sh`. Measured reach:

- **56 credential variables** by policy (M13), including:
  - `DOPPLER_TOKEN`, which can read every Doppler secret, not just the exported ones;
  - `AGE_PRIVATE_KEY` and `REPO_RECOVERY_AGE_IDENTITY_*`, which decrypt age-encrypted material;
  - AWS keys;
  - four GitHub token variables.
- **The ambient `GITHUB_TOKEN` has `repo, workflow, write:packages, admin:org`** (M14). That is enough to push workflow
  changes, to open PRs, and to **push to `ghcr.io/ray-manaloto/dotfiles-devcontainer`**, the image `mise run sync`
  pulls, and to change org settings. None of this was exercised. The rulesets still require a PR for `main`, but a
  poisoned `:dev` or `pr-*` image tag bypasses code review.
- **`SSH_AUTH_SOCK`** (git push over ssh without the key file) and every other vendor's OAuth store (M12).
- **A shared, user-writable `~/.local/bin`.** It holds all three launchers **and `mise` itself** (122 MB, updated
  2026-09-30 10:12), so one vendor's compromised updater can replace another's launcher or the tool that enforces
  every lock.
- **Shell rc files.** The installers already edit them (M10, `~/.zprofile:27-29`).

C9's "unchanged from mise" is correct as a delta. The exposure itself is large, it is pre-existing, and it is multiplied
by three auto-updaters.

- **Fix (follow-up issue, not this spec):** cut the ambient `GITHUB_TOKEN` down to read scopes, or a fine-grained token.
  Keep `write:packages`, `workflow` and `admin:org` keyring-only or `env = "exec"`, following the
  `CLAUDE_CODE_OAUTH_TOKEN` carve-out precedent in `.claude/rules/secrets-out-of-the-shell-env.md`. This is the one
  mitigation that bounds all three self-updaters at once, and changing it is Ray's decision.

### S4 — MEDIUM: no release cooldown anywhere, while a native one exists for claude

- **Evidence:** M15. mise `minimum_release_age = "0s"` in all three configs; Renovate soaks for 1 h and automerges
  minor, patch and digest updates; claude is on `autoUpdatesChannel: "latest"`.
- **Vendor cadence:** agy shipped 1.2.9→1.2.14 in 8 days (R-chan §4). codex has 9 retained releases from 2026-08-29 to
  2026-09-30 (M5). claude went 2.1.283→2.1.286 in 5 days, including one release today.
- **Assessment:** the spec loses no cooldown, because there was none. But a native lever exists and costs nothing:
  claude `autoUpdatesChannel: "stable"`, about one week old and skipping major-regression releases
  (`$CC/setup.md:227-261`, per R-chan §2).
- **Missing levers:** codex exposes only `updateIntervalMinutes` and `autoUpdateEnabled`, not a minimum age. agy has
  only the all-or-nothing `AGY_CLI_DISABLE_AUTO_UPDATE=true`.
- **Fix:** add "claude channel = stable" to Q7 as the recommended option. It is a user-level `~/.claude/settings.json`
  change, so it needs Ray's approval.

### S5 — MEDIUM: `install()` treats "logged the installer's sha256" and "installer rc 0" as verification

- **Where:** spec §3a `install`: "log its sha256, and run it … then verify the codesign Team ID and `--version`".
- **Logging is not verification.** A hash compared against nothing is a record only. The vendor scripts change without
  notice (R-chan and M7 measured them on the same day), so pinning the script hash is not viable either.
- **claude runs the latest binary regardless of the requested version** (M8, `bootstrap.sh:149, :229`). A pinned
  `install` therefore still executes an unpinned binary first, with whatever env the subprocess has.
- **agy runs the new binary (`agy install || true`) before any post-check** (M9, `:233-236`). It **exits 0 while
  installing nothing** when `agy` already exists (`:57-64`), so "rc 0" is a false success unless the post-check compares
  bytes and version.
- **Fix:**
  - (a) For claude, do real verification in `native_clis`. Fetch `<ver>/manifest.json` and `.sig`, then
    `gpg --verify` against the pinned fingerprint `31DD DE24 DDFA B679 F42D 7BD2 BAA9 29FF 1A7E CACE`. R-chan §2
    verified both arms. Then sha256 the `<ver>/<platform>/claude` binary, run `codesign --verify -R` (S1), and exec
    `<verified-binary> install <ver>`. Only verified, pinned bytes execute.
  - (b) For agy and codex, the post-condition is "the realpath's sha256 changed, `--version` equals the manifest's
    version, and `codesign --verify -R` passes", not the installer's rc.
  - (c) Run every installer and update subprocess with an explicit minimal `env=`: `HOME`, `PATH`, `TMPDIR`, `LANG`,
    `USER`, `SHELL`, plus `CODEX_NON_INTERACTIVE=1` for codex. The installer, and the binary it launches, then do not
    inherit the 56 credentials. A Python `env=` bypasses mise's re-injection (memory
    `feedback_mise_reinjects_user_global_env`).
  - (d) The `Fetcher` must be https-only and allowlist redirect hosts, because `urllib` follows https→http by default
    (M20). The redirects in use are `claude.ai`→`downloads.claude.ai` and `chatgpt.com`→`releases.openai.com`, plus
    GitHub and `storage.googleapis.com` for payloads.
  - (e) Say plainly in the skill that executing the vendor installer is trust-on-first-use.

### S6 — MEDIUM (alarm fatigue): `binaries = ["agy", "antigravity"]` makes the resolution check permanently red

- **Where:** spec §3c `[native_clis.tools.agy]` and §3a clause (4), "the tool is absent from PATH entirely".
- **Evidence:** the native installer writes only `agy` (M9, `:209`, `:215`). Today `antigravity` resolves only through
  mise (M19), so once the pin is removed it resolves nowhere, and the check fails forever.
- **Why it matters:** a doctor check that is always red trains the reader to ignore it. That is exactly the check that
  catches a PATH hijack (S1/S2).
- **Fix:** `binaries = ["agy"]`, plus a separate `must_not_resolve_under = ["~/.local/share/mise/installs/"]` clause for
  `antigravity`, where absence is fine and a mise hit is a finding.

### S7 — LOW: the probe and currency paths execute the vendor binary with the full env and self-update on

- **Where:** §3a `check_currency` and `status`, and §5 L5, all run `<native> --version`.
- **Evidence:** it is unverified whether `agy --version` spawns the background updater. R-chan §4 saw no mtime change
  from one probe, which is weak evidence, and §7 lists `agy` semantics as not probed.
- **Fix:** give probe subprocesses a minimal env plus `AGY_CLI_DISABLE_AUTO_UPDATE=true` (the literal; `1` fails,
  agy #1046) and `DISABLE_AUTOUPDATER=1`. These are scoped to the probe process only, so C8 is not violated: the user's
  switches are unchanged. A doctor probe must not be able to mutate the binary it measures.

### S8 — LOW: C4 says there is no `curl | sh` anywhere in repo code, but CI already has one, and its pin does not pin what executes

- **Evidence:** M16, `setup-claude-code/action.yml:45` pipes the claude installer to `bash -s "$version"`. By M8 it
  executes the `latest` binary before installing `$version`. The action's control arm 2 proves the pinned version ended
  up installed, not that nothing else ran.
- **Reach is small:** `contents: read`, `persist-credentials: false`, no secrets in the job env (M16). Cache poisoning
  from these jobs was **not investigated**.
- **Fix:** scope C4 to *new* code, and add "setup-claude-code: GPG-verified fetch (S5a)" to the F1 follow-up list in
  spec §6, next to the Dockerfile item that is already there.

### S9 — LOW: codex's update channel is an unsigned script run hourly, not just "sha256 against metadata"

- **Evidence:** the daemon's update loop downloads `install.sh` and runs it with `CODEX_RELEASE=latest` (R-chan §3,
  `update_loop.rs:532-579`). The script is unsigned, edits rc files (M10), and runs before any codesign check could
  observe it. Exposure is intermittent: the daemon is not running now (M11), and `settings.json` is absent, so the
  updater is ON whenever the daemon runs.
- **Fix:** the posture table (C9) should list the update channel's trust separately from the binary's. The same applies
  to claude (a closed-source in-binary updater, likely without a signature check: M18) and agy (an in-place update with
  no signature).

### S10 — INFO: on the host, C9's "what we lose" is overstated; the security value is entirely in the new checks

- agy's committed digest was already void, because agy self-updated inside mise's dirs (M6: 9 of 23 dirs).
- The host codex pin is disabled, and the npm lock has no checksum anyway (R-chan §3).
- The host claude had no pin (spec P5).
- "Reviewed version change" means an automerged Renovate PR gated by CI (M15), not human review.

The net host supply-chain delta of the pin removal is about zero. That is why S1 (a check that actually checks) and S6
(a check that is not permanently red) decide whether the spec improves the posture at all.

### S11 — INFO: global config handling carries low risk

- No secret values are in `~/.config/mise/config.toml` (M17, regex armed). The `copy2` backup that keeps 0600 is
  therefore sufficient.
- Keep `global-stanza --check` output to the managed marker region, so a 553-line file is never echoed into a
  transcript.
- 8 of the 12 pre-existing backups are 0644, which predates this work and is noted only.

### S12 — INFO: premises this lens re-derived

- **P22 (Team IDs) CONFIRMED** on the live binaries (M2).
- **R-chan §4, agy self-updating inside mise dirs, CONFIRMED** (M6).
- **The installer bytes are unchanged since R-chan** (M7).
- **R-chan §7's gap on whether the claude updater checks the signature** is closed as **likely no** (M18: string
  evidence).
- **P25 is partly stale:** the ambient agy first hit is still `installs/antigravity-cli/1.2.13/agy`, but the
  `1.2.14` install dir now exists (mtime Sep 30 10:13).

## Not measured (gaps, not "clean")

- Whether the `~/.ssh/id_ed25519` passphrase is set. Not probed, because it would need reading a key file.
- Whether a same-user non-GUI process can read the Claude or gh keychain items without a dialog. Not probed: the probe
  would print a value, or hang (`secrets-out-of-the-shell-env.md`).
- Pushing to ghcr with the ambient token. Scopes were inferred from the header only.
- Whether `agy --version` or `agy update` spawn the updater (S7).
- Cache poisoning from the CI jobs that run the installer (S8).
- The codex `.sigstore` cryptographic verify, which R-chan also did not run.

## GitHub repos touched

- [google-antigravity/antigravity-cli](https://github.com/google-antigravity/antigravity-cli): the served `install.sh`
  (read, not run), and the issue #1046 value semantics via R-chan.
- [openai/codex](https://github.com/openai/codex): the served `install.sh` (read, not run), and the daemon update loop
  via R-chan.
- [anthropics/claude-code](https://github.com/anthropics/claude-code): the served `bootstrap.sh` (read, not run), and
  binary strings for signature references.
- [python/cpython](https://github.com/python/cpython): `Lib/urllib/request.py` redirect scheme check (the local 3.14.0
  copy).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the spec, R-chan, `doctor.toml`, `renovate.json`,
  `setup-claude-code`, `ci.yml` and `autofix.yml`.
