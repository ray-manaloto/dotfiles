# feat(mise): install default CLI tools through native lazy shims

- URL: https://github.com/omacom/omarchy/pull/9596
- state: open | author: jdx | created: 2026-09-01T11:48:31Z | closed: null | merged_pr: n/a
- labels: enhancement

## Body

Omarchy's default CLI tools now use mise's native lazy installation. Running `codex`, `claude`, `gh`, or another default still installs it on first use, but the 20 defaults are declared together in `/etc/mise/config.toml` and appear in mise's normal tool listings. Later launches reuse the installed version; updates come from `omarchy update`, or `mup` for mise-managed tools only.

```bash
mise ls --current              # Inspect the configured tools
mise install gh               # Install one tool before first use
mise install --include-lazy   # Install all configured tools, including lazy tools
```

Registry shorthands replace explicit backends where appropriate, allowing mise to use cached version and release metadata and reducing GitHub API requests. Python setup now installs `uv` through mise, and removing the Python environment leaves `uv` available.

## Adoption and overrides

Requires **mise 2026.9.4 or newer**, supplied by the merged omacom/omarchy-pkgs#372.

Existing installations migrate automatically. The migration removes only complete, byte-for-byte matches for known Omarchy wrapper templates. Customized scripts and user-owned symlinks remain untouched.

Users can disable a default in `~/.config/mise/config.toml` to use their own installation on `PATH`:

```toml
[settings]
disable_tools = ["cursor-agent"]
```

The default-agent launcher also prefers user-installed Cursor and Muse commands in `~/.local/bin`. The system configuration sets `locked_scopes = ["project", "global"]`, so invocation-wide locked mode still applies to users' project and global tools while allowing Omarchy's system defaults to install.

Hermes retains its separate launcher for the Python 3.13 requirement and Hermes Desktop ownership checks. `omarchy install hermes cli --now` installs it ahead of time; an unfinished Desktop setup does not block user finalization or restoring other preinstalls. Cloudflare's `cf` uses `npm:cf` with an explicit lazy shim name because the registry shorthand `cf` refers to Cloud Foundry.

## Remove and Restore Preinstalls

Removal deletes the system tool configuration and reconciles the current user's shims. Restoration reinstates the configuration, rebuilds the shims, and restores Hermes's launcher. A failed configuration or shim step stops restoration and leaves the preinstalls opt-out marker in place.

**Multi-user behavior changes:** the configuration is machine-wide, while the opt-out marker is per-user. Removing or restoring preinstalls changes the system tool defaults for every user. Users who want only a personal override should use `disable_tools`.

## Validation

- Seven focused shell suites pass as an unprivileged user in a local Ubuntu ARM64 container: **124 assertions**, covering default-agent selection, Hermes, migration, Python setup, preinstalls, and wrapper installation/rewriting.
- The customized-wrapper regression fails before the fix and passes afterward. Coverage includes added environment settings, comments, commands, changed binary names, and trailing blank lines, plus all five historical wrapper templates.
- With checksum-verified **mise 2026.9.4**, a cold offline migration creates all 20 primary shims without installing tools or writing global tool pins. A second migration succeeds; first-use `uv` installation works under `MISE_LOCKED=1`; removing/restoring the system configuration retires/rebuilds lazy shims and preserves installed `uv`.
- Bash syntax and whitespace checks pass. Earlier PR validation also covered an Arch x86_64 package build and first-use Basecamp, Cursor, and Muse installation.

Desktop actions and package transactions in the shell suites are mocked. **Fresh-ISO installation and the interactive Remove/Restore flow still need validation on Omarchy.**

*AI-assisted — Tool: Claude Code; model: anthropic/claude-opus-5; version: 2.1.270.*

*AI-assisted — Tool: Codex; model: openai/unavailable; version: unavailable.*


## Comments

## Review comments

## Reviews

## Files
- AGENTS.md +1/-0
- agents/skills/mise-tools.md +35/-0
- bin/omarchy-agent +8/-0
- bin/omarchy-default-agent +4/-8
- bin/omarchy-install-dev-env +1/-1
- bin/omarchy-install-hermes-cli +19/-14
- bin/omarchy-install-preinstalls +15/-3
- bin/omarchy-refresh-applications +1/-5
- bin/omarchy-remove-dev-env +0/-1
- bin/omarchy-remove-preinstalls +10/-3
- default/mise/config.toml +29/-0
- install/config/all.sh +1/-0
- install/config/mise.sh +3/-0
- install/user/mise.sh +4/-27
- manual/17-ai.md +12/-4
- manual/18-development-tools.md +33/-4
- migrations/1785617047.sh +1/-1
- migrations/1785846769.sh +2/-2
- migrations/1787215824.sh +1/-1
- migrations/1787342993.sh +1/-1
- migrations/1787590397.sh +29/-0
- migrations/1788262200.sh +74/-0
- migrations/1788577553.sh +3/-6
- migrations/1788724825.sh +3/-3
- migrations/1788941927.sh +2/-2
- migrations/1789310715.sh +2/-2
- test/shell.d/default-agent-test.sh +119/-43
- test/shell.d/hermes-cli-test.sh +12/-2
- test/shell.d/mise-lazy-tools-migration-test.sh +137/-0
- test/shell.d/mise-python-dev-env-test.sh +38/-0
- test/shell.d/preinstalls-test.sh +55/-0
