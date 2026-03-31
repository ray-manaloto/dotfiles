---
name: chezmoi-check
description: Validate chezmoi templates render correctly and check for common template issues. Use when editing home/ templates or after changing .chezmoi.toml.tmpl.
---

# Chezmoi Template Validator

Validates all `.tmpl` files in `home/` render without errors and checks for consistency.

## Quick Validation

```bash
# Test all templates render with current data
chezmoi execute-template < home/.chezmoi.toml.tmpl

# Verify managed files match templates
chezmoi verify --verbose 2>&1 | head -20

# Diff what would change
chezmoi diff
```

## Template Variables

This project defines these data variables in `.chezmoi.toml.tmpl`:

| Variable | Type | Source | Default |
|----------|------|--------|---------|
| `is_dev_computer` | bool | Interactive prompt / `true` in containers | `false` |
| `is_personal` | bool | Interactive prompt | `false` |
| `is_ephemeral` | bool | Interactive prompt / `true` in containers+CI | `false` |
| `is_container` | bool | Auto-detected from `REMOTE_CONTAINERS`, `CODESPACES`, `DEVCONTAINER` env | `false` |
| `is_ci` | bool | Auto-detected from `CI` env | `false` |

## Environment Detection

Templates use this precedence for environment detection:
```
Container: REMOTE_CONTAINERS || CODESPACES || DEVCONTAINER
CI: CI env var
Interactive: not container AND not CI AND stdinIsATTY
```

When `isInteractive` is false, prompts are skipped and safe defaults are used.

## Full Validation Workflow

Run these checks in order:

```bash
# 1. Check template syntax (each .tmpl file)
for f in home/*.tmpl; do
  echo "--- $f ---"
  chezmoi execute-template < "$f" > /dev/null 2>&1 && echo "OK" || echo "FAIL: $f"
done

# 2. Check external sources are reachable
chezmoi managed --include=externals 2>&1

# 3. Check for undefined variables (grep for .chezmoi.data references)
grep -rn '\.chezmoi\.data\.' home/*.tmpl | grep -v 'is_dev_computer\|is_personal\|is_ephemeral\|is_container\|is_ci'

# 4. Verify platform-specific blocks reference valid chezmoi functions
grep -rn 'eq .chezmoi.os' home/*.tmpl
```

## Common Issues

- **Template changes require `chezmoi init --init`** on existing machines to re-run prompts
- **`.tmpl` files are NOT linted by ruff/shellcheck** — hk.pkl uses type-based matching, and `.sh.tmpl` files have type `text` not `shell`
- **Container environments skip prompts** — always test templates with both interactive and non-interactive paths
- **`scriptEnv.PATH`** in `.chezmoi.toml.tmpl` must include mise shims for run_once/run_after scripts

## Double-Escape Tera Syntax in mise Templates

`home/dot_config/mise/config.toml.tmpl` contains mise's Tera syntax inside a chezmoi template.
Double-escape with `{{ "{{ ... }}" }}` so chezmoi passes the literal string through unchanged.
Example: `{{ "{{ env.VAR | default(value=\"fallback\") }}" }}` — chezmoi outputs the literal
`{{ env.VAR | default(value="fallback") }}` which mise then expands at container runtime.
Verify with: `chezmoi execute-template < home/dot_config/mise/config.toml.tmpl | grep 'env\.'`
— output should show `{{` and `}}` literally, not interpolated values.

## `.chezmoitemplates/` Snippet Pattern

Reusable template fragments live in `home/.chezmoitemplates/`. Call them with:
`{{ template "env" (dict "SHELL" "zsh") }}` where `"env"` is the filename and
`(dict "SHELL" "zsh")` passes a map as `.` into the template. Inside the snippet,
`.SHELL` expands to `"zsh"`. This avoids copy-pasting shell-specific blocks across
multiple dotfiles (e.g., `.zshrc`, `.bashrc`). Validate with:
`chezmoi execute-template '{{ template "env" (dict "SHELL" "zsh") }}'`

## `run_onchange_after` with Hash Annotation

Scripts named `run_onchange_after_*.sh.tmpl` re-run when their content changes.
Add `# chezmoi:template:hash` as a comment and embed:
`# {{ include "dot_config/mise/config.toml.tmpl" | sha256sum }}`
This forces chezmoi to treat the included file's hash as part of the script body,
so any change to the mise config triggers a re-run. Without the annotation, chezmoi
only hashes the script itself, missing upstream config changes.

## `chezmoi source-path` for Dynamic Path Resolution

Never hardcode `~/.local/share/chezmoi` in scripts or templates. `install.sh` accepts
`--source <path>` so the source directory varies between installs. Use:
`chezmoi source-path` — prints the active source directory
`chezmoi source-path home/dot_config/mise/config.toml.tmpl` — resolves a specific file
This is critical in `run_once`/`run_onchange` scripts that reference source files directly.

## `scriptEnv.PATH` with `env "MISE_DATA_DIR"` Fallback

In `.chezmoi.toml.tmpl`, `scriptEnv.PATH` now uses:
`{{ env "MISE_DATA_DIR" | default (joinPath .chezmoi.homeDir ".local/share/mise") }}/shims`
This mirrors the pattern in `dot_zshenv.tmpl` — works in containers (MISE_DATA_DIR=/opt/mise)
and on bare-metal (falls back to `$HOME/.local/share/mise/shims`). Never hardcode
`/opt/mise` or `$HOME/.local/share/mise` directly in this path.
