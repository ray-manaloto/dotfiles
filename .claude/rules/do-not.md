# Do Not — Project Invariants

This is the authoritative list of things agents (and humans) must not do
in this repo. Moved out of `AGENTS.md` in session 2026-04-09c as part of
a doc-size split (the root `AGENTS.md` was exceeding the
`claude_md_size_limit` hk step and this list was the largest
self-contained block). Each item's context is preserved verbatim.

1. **Do NOT launch CLion or VS Code from the dock for devcontainer work.**
   macOS GUI processes don't inherit terminal env, so `mise`, `uv`, and
   `$SSH_AUTH_SOCK` are not available to `initializeCommand`, which then
   fails to spawn the host-side SSH agent proxy. Terminal only. See
   `.devcontainer/AGENTS.md`.

2. **Do NOT `mise run build` or `docker buildx bake dev-load` locally.**
   CI-only. Base image is published by `main` workflow.

3. **Do NOT use raw `docker` CLI for devcontainer lifecycle**
   (`run/exec/stop/rm/build`). Use `@devcontainers/cli` so lifecycle
   hooks run. Raw `docker ps/logs/info` for inspection are fine.

4. **Do NOT add `2>/dev/null` to the Dockerfile.** The
   `build.no-stderr-suppression` contract rejects it. Let errors be loud.

5. **Do NOT bulk `git add .`** — previous sessions have left phantom
   state files under `.omc/state/**` that should not be staged.

6. **Do NOT trust `gh run watch --exit-status`.** Verify with
   `gh pr checks <n> --json` or `gh run list --json`.

7. **Do NOT register MCP servers via the native Claude Code CLI
   subcommand** (the one that adds servers via `mcp`). Registering a
   server injects every tool's JSON schema into every conversation's
   system prompt forever. Use `mcp2cli` (process-spawn, no schema
   injection) instead; machine-enforced by the `no_mcp_registration`
   hk step. See `feedback_no_mcp_registration.md`.

8. **Do NOT switch `docker context` away from `desktop-linux`.** The
   SSH path is Docker-Desktop-only; silent drift caused session
   2026-04-09c's debug goose-chase. See
   `feedback_docker_desktop_runtime.md`.

## See also

- `zero-skip-policy.md` — no warning/error shall be dismissed
- `ci-local-parity.md` — keep local checks in sync with CI
- `clean-git-state.md` — stage all changes before validation
- `use-tool-builtins.md` — prefer tool builtins over homegrown logic
- `research-doc-sources.md` — preference chain for doc fetching
- `notepad-enforcement.md` — agents write findings to notepad as they go
- `omc-directory-conventions.md` — standard `.omc/` paths
