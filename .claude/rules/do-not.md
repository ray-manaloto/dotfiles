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

7. **Do NOT switch `docker context` away from `desktop-linux`.** The
   SSH path is Docker-Desktop-only; silent drift caused session
   2026-04-09c's debug goose-chase. See
   `feedback_docker_desktop_runtime.md`.

> **Relaxed 2026-07-19 — MCP registration is no longer a "do not".** Native
> MCP registration (`claude mcp add`, a plugin's bundled servers, a project
> `.mcp.json`) is **allowed when a plugin or tool requires it**. `mcp2cli`
> (process-spawn, no schema-injection tax) stays the *preferred* path for
> one-off doc/tool calls — a preference, not a gate. See
> `research-doc-sources.md` and `feedback_no_mcp_registration.md`.

## See also

- `mise-tasks-only.md` — canonical mise tasks over one-off commands (hook-enforced)
- `zero-skip-policy.md` — no warning/error shall be dismissed
- `verify-before-advancing.md` — every applicable check green before the next task
- `probes-need-a-control-arm.md` — a check that can only pass is not a check
- `ci-local-parity.md` — keep local checks in sync with CI
- `clean-git-state.md` — stage all changes before validation
- `use-tool-builtins.md` — prefer tool builtins over homegrown logic
- `research-doc-sources.md` — preference chain for doc fetching
- `notepad-enforcement.md` — agents write findings to notepad as they go
- `omc-directory-conventions.md` — standard `.omc/` paths
