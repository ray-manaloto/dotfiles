<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->

# home/ — Chezmoi-Managed Dotfiles

## Purpose

Chezmoi source directory. All files here are **templates** processed by
`chezmoi apply` — the rendered output lands in `$HOME` on the target
machine (Mac host or devcontainer).

## Key Files

| File | Purpose |
|------|---------|
| `dot_zshrc.tmpl`, `dot_bashrc.tmpl`, `dot_profile.tmpl`, `dot_zshenv.tmpl` | Shell init (chezmoi `dot_` prefix → `.zshrc`, `.bashrc`, etc.) |
| `dot_config/`, `dot_local/` | XDG-compliant tool configs |
| `CLAUDE.md.tmpl`, `AGENTS.md.tmpl` | **User-level** home agent instructions — render to `~/CLAUDE.md`, `~/AGENTS.md`. Distinct from this repo's root `AGENTS.md`. |
| `pyproject.toml.tmpl`, `pixi.toml.tmpl` | User-level Python/pixi project templates |
| `executable_run_before_00-install-runtimes.sh.tmpl` | Pre-apply chezmoi script |
| `executable_run_once_after_00-install-tools.py.tmpl` | One-time post-apply tool install script |
| `executable_run_after_10-hk-install.sh.tmpl` | Post-apply hk install script |

## Multi-machine differentiation

Uses the **built-in `chezmoi.os` fact**, NOT custom env-var detection:

- `{{ eq .chezmoi.os "darwin" }}` — Mac host
- `{{ eq .chezmoi.os "linux" }}` — devcontainer

See `.claude/rules/use-tool-builtins.md` for the rationale. Session
2026-04-06g removed ~20 lines of custom `$isContainer` env-var detection
(`REMOTE_CONTAINERS` / `CODESPACES` / `DEVCONTAINER`) in favor of the
canonical chezmoi pattern.

## Rules for working here

1. **`chezmoi apply` on the Mac host is BLOCKED** by
   `.claude/settings.json` until Mac integration ships. Read-only
   `chezmoi` commands (`chezmoi diff`, `chezmoi status`,
   `chezmoi managed`) remain allowed.
2. **Chezmoi scripts must NEVER install tools.** Tool install belongs
   in `.devcontainer/Dockerfile` or `.devcontainer/mise-system.toml`
   (devcontainer), or on the Mac host via Homebrew. See
   `feedback_chezmoi_scripts_no_tool_install`.
3. **The mise overlay `dot_config/mise/config.toml.tmpl` is
   devcontainer-only.** It must NEVER render on the Mac host. The gate
   lives in `.chezmoiignore` using `{{ ne .chezmoi.os "linux" }}`. See
   `feedback_devcontainer_only_mise_overlay`.
4. **No custom `is_container` data variables.** Previously this repo
   had custom `$isContainer` env-var parsing. Deleted 2026-04-06g; use
   `.chezmoi.os` instead.

## Verification

Use the `chezmoi-check` skill (under `.claude/skills/`) to validate
template rendering before committing. Example:

```bash
# From repo root
chezmoi execute-template < home/dot_zshrc.tmpl
```

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
