# PRD: Minimal Global Mise Refactor (Standard Baseline)

## Objective
Implement global `mise` tool installation during the Docker build stage using the system-wide `/etc/mise/config.toml` path, while maintaining the stable host-user identity and SSH forwarding logic from the current mainline baseline.

## Requirements
- **Global Installation**: `mise` and core tools must be pre-baked into `/opt/mise` in the base image.
- **System Config**: `/etc/mise/config.toml` must be the source for tools, managed via `chezmoi` from `home/dot_config/mise/config.toml.tmpl` (mapping to the system path).
- **Identity Restoration**: Use the existing dynamic host-user logic in `devcontainer.json` and `Dockerfile.host-user`.
- **SSH Forwarding**: Ensure `forwardAgent: true` works correctly with the dynamic host user.
- **Architecture**: Stick to the `home/` directory structure as the primary source for `chezmoi`.

## Acceptance Criteria
1. `devcontainer build` succeeds for `linux/amd64`.
2. `devcontainer up` adopts the host username and UID/GID.
3. `ssh-add -l` works inside the container.
4. Tools (python, uv, etc.) are pre-installed in `/opt/mise` and reachable via PATH.
