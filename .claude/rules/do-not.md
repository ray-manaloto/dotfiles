# Do Not — Project Invariants

This is the authoritative list of things agents (and humans) must not do
in this repo. Control arms and case history for each entry:
`docs/rules-evidence/do-not.md`.

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
   state files under `.agent/state/**` that should not be staged.

6. **Do NOT trust `gh run watch --exit-status`.** Verify with
   `gh pr checks <n> --json` or `gh run list --json`.

7. **Do NOT switch `docker context` away from `desktop-linux`.** The
   SSH path is Docker-Desktop-only; silent drift caused session
   2026-04-09c's debug goose-chase. See
   `feedback_docker_desktop_runtime.md`.

8. **Do NOT run bare `graphify install` — always pass `--project`.** Without it,
   graphify **mutates `~/.claude`**: ~43 KB of skill files and a `# graphify`
   H1 appended to `~/.claude/CLAUDE.md`. `CLAUDE_CONFIG_DIR` is NOT containment
   (it redirects the skill dir only; that write is hardcoded). Never run
   `graphify hook install` or `graphify --watch`.

   ⚠️ **This generalises to every platform, and `--project` is not always
   enough** — `graphify codex install` appends to the root `AGENTS.md` and
   fails our size gate either way. Run any `graphify <platform> install` in a
   **throwaway directory outside this repo**, never here.

9. **Do NOT commit onto the default branch — branch FIRST.** Create the branch
   *before* the commit, then `mise run ship`. It has happened twice, the second
   time straight after `mise run land` (which **leaves you on `main`**).
   Recovery is `git branch <new> && git reset --hard origin/main`.

   Machine-enforced (#400) in three layers: hk's `no_commit_to_branch` in the
   **pre-commit** hook, the PreToolUse guard denying `--no-verify` / `git commit
   -n` / a `HK_SKIP_HOOKS=` prefix (**no git hook can catch those** — git skips
   the hook before it exists as a process), and a repository **ruleset requiring
   a PR for `main`** — the only layer an agent cannot skip.

10. **Do NOT write an environment dump into a tracked file.** Not `env`, not
    `printenv`, not `export -p`, not a debug log carrying them. The interactive
    shell holds real credentials, and mise packs the whole delta into
    `__MISE_DIFF` (zlib + base64) — a form **no secret scanner can read**
    (measured: gitleaks 2 → 0, betterleaks 1 → 0). Write a dump to the
    scratchpad and delete it. Gated by `no_env_dump`; see
    `secrets-out-of-the-shell-env.md`.

11. **Do NOT reach for MCP to solve one of OUR OWN problems.** For anything this
    project builds, calls, or looks up: the tool's CLI or a plain HTTP **API**
    first, then `mcp2cli`, and native registration only as a documented last
    resort. A registered server taxes **every** conversation's system prompt
    with **every** tool's schema, forever — paying that for a call a `curl`
    already makes is pure loss.

    ✅ **NOT a "do not": a third-party plugin or skill that REQUIRES MCP.**
    Enabling one (bundled servers, `claude mcp add`, a project `.mcp.json`) is
    allowed and needs no justification — there the schema tax buys a capability
    we cannot build. The hard ban was relaxed 2026-07-19. **Unsure which case
    you are in? You are in the first one.** See `research-doc-sources.md`
    § "MCP: two lanes".

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
- `agent-artifact-conventions.md` — standard `.agent/` paths
