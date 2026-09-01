# Lane brief — devcontainer mount & volume uniqueness audit (2026-09-01)

**Lane:** `codex-advisor` (gpt-5.6-sol, xhigh) — runs on codex, spends no Claude tokens (#884).
**Origin:** operator, 2026-09-01-c: *"review the bind mounts and volumes as i dont
think they are unique per devcontainer which can cause data corruption."*
**Report:** `docs/research/kb/reports/agents/2026-09-01-mount-uniqueness-audit.md`

## Question

For every mount the devcontainer declares — `workspaceMount`, each entry in
`mounts`, and any volume the CLI or a feature creates implicitly — determine
whether it is **uniquely scoped** to one (workspace × architecture) pair, and
where it is not, whether two concurrently-running containers (or a container and
the macOS host) can write the same bytes and corrupt them.

## Scope

- `.devcontainer/devcontainer.json` (mounts at lines 112-120; `runArgs`, labels)
- `python/src/dotfiles_setup/devcontainer.py` — the name/hash resolver behind
  `mise run names`
- `mise.toml` `[tasks.up]` / `[tasks.names]` / `[tasks.ssh-port]`
- `.devcontainer/scripts/on-create.sh` and any lifecycle hook that writes to a mount
- `.devcontainer/AGENTS.md` for the declared invariants

## Ground truth measured before dispatch (verify, do not trust)

    DEVCONTAINER_WORKSPACE_HASH=273897ea
    DEVCONTAINER_NAME=dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233
    DEVCONTAINER_HOME_VOLUME=dotfiles-dotfiles-rmanaloto-273897ea-amd64-home

## Required

1. **Enumerate every mount as a table**: source · target · type · what scopes it
   (workspace hash? arch? nothing?) · what writes to it · collision verdict.
2. **Name the concurrency model for each shared mount.** A shared *read-only*
   path is not a corruption risk; a shared path with two writers is. Distinguish
   them — say which process writes, and whether writes are append, truncate, or
   rename.
3. **Control-arm every negative.** Before reporting "this is uniquely scoped",
   show the arm: resolve the name for a *second* workspace or arch and show the
   values differ. A claim of uniqueness with one sample is not evidence
   (`.claude/rules/probes-need-a-control-arm.md`).
4. **Include the host as a participant.** The macOS host writes to some of these
   paths too; a host↔container collision counts.
5. Severity per finding, and for each real collision, the concrete interleaving
   that corrupts data — not "could conflict".

## Constraints

- **Read-only audit. Do not edit any file** except your own report and raw notes.
- Do NOT run `mise run up`/`down`/`dev-rebuild`/`verify-local` — a `land` is
  running against the devcontainer right now and would be disrupted.
  `docker ps`/`docker volume ls`/`docker inspect` are read-only and fine.
- End the report with `## GitHub repos touched`
  (`.claude/rules/research-repo-enumeration.md`).

## Delivery — non-negotiable

- **Write the report file INCREMENTALLY, from your first finding onward.** Do not
  hold findings in memory and write at the end; agents that did have died and
  left nothing (`.claude/rules/agent-report-persistence.md`).
- **SendMessage LAST, after the file is on disk.** Final text that is not in the
  file goes nowhere.
