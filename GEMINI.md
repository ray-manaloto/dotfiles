# Project Rules: Reproducible Dotfiles

## Architecture
- **Chezmoi First**: Chezmoi is the master orchestrator. Mise, Pixi, and UV are tools managed by Chezmoi templates and hooks.
- **Zero-Bash Logic**: All non-trivial logic (environment detection, tool-specific configuration, validation) must reside in the `python/` library. Bash is restricted to the Stage 0 bootstrap (`install.sh`).
- **Mise-Managed Runtimes**: No runtimes (Python, Node, Go, etc.) should be installed via `apt-get`. Use `mise` exclusively.

## Docker & DevContainers
- **Platform Enforcement**: Strictly target `linux/amd64`. Pass `--platform linux/amd64` on every build.
- **Use devcontainer CLI**: Use `@devcontainers/cli` (`devcontainer`) exclusively for the container lifecycle (`build`, `up`, `exec`). Avoid the raw `docker` CLI (`run`, `exec`, `stop`, `rm`, `build`) for devcontainer tasks — this ensures `devcontainer.json` configs and lifecycle hooks are respected.
- **Context & Visibility**: If the CLI fails to find an image, resolve the Docker context (e.g., `DOCKER_CONTEXT=desktop-linux`) or rebuild using the CLI.
- **Dynamic Identity**: DevContainers dynamically inherit the host user's identity via `${localEnv:USER}`, `${localEnv:UID}`, and `${localEnv:GID}`.
- **SSH Synchronization**: Leverage native `forwardAgent: true` and read-only bind mounts for SSH configuration.

## Engineering Standards
- **Python Version**: Standardize on **Python 3.14** for the core toolchain.
- **Audit-First Verification**: Pair every environment modification with an automated check in the `audit` module. Use native "doctor" commands (e.g., `mise doctor`) and functional tests (e.g., SSH round-trips).
- **Quality Gates**: Configure ruff with `select = ["ALL"]` and ty for type checking. Zero skips/ignores allowed.
- **Path Management**: Mise shims and local bins are injected into `os.environ["PATH"]` within Python hooks to ensure tool reachability in non-login shells.

