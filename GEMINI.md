# Project Rules: Reproducible Dotfiles

## Architecture
- **Chezmoi First**: Chezmoi is the master orchestrator. Mise, Pixi, and UV are tools managed by Chezmoi templates and hooks.
- **Zero-Bash Logic**: All non-trivial logic (environment detection, tool-specific configuration, validation) must reside in the `python/` library. Bash is restricted to the Stage 0 bootstrap (`install.sh`).
- **Mise-Managed Runtimes**: No runtimes (Python, Node, Go, etc.) should be installed via `apt-get`. Use `mise` exclusively.

## Docker & DevContainers
- **Strict Prohibition**: **NEVER use the raw `docker` CLI** (`run`, `exec`, `stop`, `rm`, `build`) for devcontainer-related tasks. This is a foundational mandate to ensure that `devcontainer.json` configurations and lifecycle hooks (`postCreateCommand`, etc.) are always respected.
- **Exclusive CLI Usage**: Use `@devcontainers/cli` (`devcontainer`) exclusively for the entire container lifecycle:
    - `devcontainer build` for image preparation.
    - `devcontainer up` for starting the environment and triggering lifecycle events.
    - `devcontainer exec` for running commands inside the container.
- **Context & Visibility**: If the CLI fails to find an image, resolve the Docker context (e.g., `DOCKER_CONTEXT=desktop-linux`) or rebuild using the CLI. Do not bypass the CLI with `docker run`.
- **Platform Enforcement**: Strictly target `linux/amd64`. Tooling must explicitly pass `--platform linux/amd64` during builds.
- **Dynamic Identity**: DevContainers must dynamically inherit the host user's identity via `${localEnv:USER}`, `${localEnv:UID}`, and `${localEnv:GID}`.
- **SSH Synchronization**: Leverage native `forwardAgent: true` and read-only bind mounts for SSH configuration.

## Engineering Standards
- **Python Version**: Standardize on **Python 3.13** for the core toolchain.
- **Audit-First Verification**: Every environment modification must be paired with an automated check in the `audit` module. Use native "doctor" commands (e.g., `mise doctor`, `pixi self-check`) and functional tests (e.g., SSH round-trips).
- **Quality Gates**: Ruff and Mypy must be configured with `select = ["ALL"]` and `strict = true`. **Zero skips/ignores allowed.**
- **Path Management**: Explicitly inject Mise shims (`~/.local/share/mise/shims`) and local bins into `os.environ["PATH"]` within Python hooks to ensure tool reachability in non-login shells.

