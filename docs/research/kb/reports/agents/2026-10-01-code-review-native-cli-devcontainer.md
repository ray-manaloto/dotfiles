# /code-review medium origin/main — 93d70c96 (native-cli-devcontainer)

Persisted verbatim at receipt by the coordinator. (Harness note on receipt: the safety classifier
timed out reviewing this subagent's work; findings were verified by the coordinator before acting.)

Found 3 issues in `origin/main...HEAD` (ReportFindings tool isn't available in this session, so listing them here):

1. **`python/src/dotfiles_setup/schema_vendor.py:130` (medium)** — Adding codex to `_VENDORED_PIN_TOOLS` makes `schemas/sources.toml` `version = "0.154.0"` the self-referential pin, but unlike claude-code, codex's `source` is an unversioned URL (`https://learn.chatgpt.com/docs/config-schema.json`), so the version is never used to build the fetch URL and nothing bumps it anymore (Renovate used to bump the shared.toml npm pin). Failure: the host/container run native codex 0.156+, `schema-refresh` fetches the latest schema bytes and rewrites `sha256` but leaves the label at 0.154.0 — `check_drift` can never fire for codex again and the file claims provenance from a release it didn't come from. The new header tells you to hand-edit `version` for codex, which changes nothing fetched.

2. **`.devcontainer/scripts/on-create.sh:42` (medium)** — The new `native-clis install` call runs under `set -euo pipefail` before everything else, and fetches three external installers (claude.ai, chatgpt.com, antigravity.google) at create time; `install()` returns non-zero if any one fails. Failure: any of those endpoints down/rate-limited → the script exits immediately, so `chezmoi init --apply`, ownership repair, and the overlay `mise install` never run — container has no dotfiles/user-tier tools and `devcontainer up` fails. Previously claude/codex were baked into the image, so container creation had no such network dependency.

3. **`python/src/dotfiles_setup/native_clis_container.py:51` (low)** — `_minimal_env` passes only `HOME/PATH/USER/LOGNAME/LANG/SHELL/TMPDIR` + `MISE_*`, dropping `HTTPS_PROXY`/`HTTP_PROXY`/`NO_PROXY` and `SSL_CERT_FILE`/`CURL_CA_BUNDLE`. Failure: on a network that requires a proxy or a TLS-intercepting CA, the curl fetch and the vendor installers' own downloads fail even though the same curl works in the container's normal environment — which, combined with finding 2, blocks container creation. These are not credentials, so they can be added to `_ENV_PASSTHROUGH` without undermining the secret-exclusion goal.

Checked and found no defect: the new "must not be baked" check only lives in the CI no-mount image smoke (not the devcontainer tier-3 smoke), so it won't reject the native install; there's no `~/.codex` bind mount from the Mac, so the container codex installer can't clobber the host's; the retired-claude-wrapper move-aside for old home volumes works; the uv git dependency (knowledge-base) is public so it fetches before chezmoi configures git; `~/.local/bin` is first on PATH via `Dockerfile.host-user`; removing `MISE_DISABLE_TOOLS` leaves no CI step needing a codex binary; no active mise config still declares claude/codex.

## GitHub repos touched

_None._
