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

8. **Do NOT run bare `graphify install` — always pass `--project`.** One flag
   separates safe from destructive (verified in the installed 0.9.20
   `install.py`, 2026-07-20):
   - `graphify claude install` → **project only** (`./CLAUDE.md` +
     `./.claude/settings.json`).
   - `graphify install --project` → **project only** (adds
     `./.claude/skills/graphify/**` + a block in `./.claude/CLAUDE.md`).
   - ⚠️ `graphify install` **without** `--project` → **mutates `~/.claude`**:
     ~43 KB of skill files, **appends a `# graphify` H1 to
     `~/.claude/CLAUDE.md`** (creating it if absent), and sprays
     `.graphify_version` stamps into every other installed platform's user
     skill dir.

   Control arm on the safe claim: all **18** `Path.home()` call sites in
   `install.py` sit on `project=False` branches; the project-scoped call chain
   contains none. **`CLAUDE_CONFIG_DIR` is NOT containment** — it redirects the
   skill dir only, while the `~/.claude/CLAUDE.md` write is hardcoded. This is
   the machine-level expression of the PROJECT-ONLY invariant; also never run
   `graphify hook install` or `graphify --watch`.

9. **Do NOT commit onto the default branch — branch FIRST.** Create the branch
   *before* the commit, then `mise run ship`. On 2026-07-20 a session committed
   34 files straight onto `main` and had to move them afterwards
   (`git branch <new> && git reset --hard origin/main`). It was recoverable
   only because nothing had been pushed.

   The guidance already existed in the `git-branch-commit-push-workflow` skill
   — but that skill carries `disable-model-invocation: true`, which **agnix
   `--strict` requires** for state-mutating "dangerous" skills, so the model
   cannot reach it at decision time. Hence this line: an eager rule is the only
   layer that fires before the mistake. Do not "fix" the skill by removing the
   flag; the docs gate will reject it, and correctly.

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
