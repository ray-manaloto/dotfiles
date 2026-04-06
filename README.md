# Reproducible Dotfiles (AMD64)

A highly resilient, declarative dotfiles setup using **Chezmoi**, **Mise**, and **Python**, optimized for Linux-based devcontainers.

## Quick Start

### Local Development

```bash
mise install                                       # Install all tools
hk run pre-commit --all                            # Run lint checks (requires HK_PKL_BACKEND=pkl)
uv run --project python pytest tests/ -x -q      # Run all 65 tests
```

### Docker Build

```bash
docker buildx bake dev-load                        # Build devcontainer locally
```

### Bootstrap (Container)

```bash
curl -fsSL https://raw.githubusercontent.com/sortakool/dotfiles/main/install.sh | bash
```

## Architecture

1.  **Stage 0**: `install.sh` bootstraps `mise`.
2.  **Stage 1**: `mise` installs `git`, `chezmoi`, and `uv`.
3.  **Stage 2**: `chezmoi init` clones the repo and applies templated configs.
4.  **Stage 3**: Python lifecycle hooks (`uv run`) handle complex orchestration and tool installations.

## Features

-   **Strictly AMD64**: Forced x86_64 architecture for container consistency.
-   **Declarative Config**: Pydantic `DotfilesConfig` centralizes 16 env vars; `hk.pkl` for git hooks with shared `hk-common.pkl` checks.
-   **Zero-Bash**: Logic is encapsulated in a typed, linted Python library (`dotfiles_setup`).
-   **Zero Lint Suppressions**: No `noqa`, `type: ignore`, or `pylint: disable` — enforced by `no_lint_skip` hk step.
-   **Environment Auditor**: Built-in health checks for identity, toolchains, and SSH connectivity.
-   **CI/CD**: Lint, contract-preflight, build, and smoke-test on GitHub Actions.

## Tool Management

All tools are declared in `mise.toml` and installed via `mise install`.
Python dependencies are managed via `uv` with `python/pyproject.toml`.

## Local Testing

```bash
uv run --project python pytest tests/ -x -q      # All tests
uv run --project python dotfiles-setup verify run # Contract verification
mise run pin-actions                                # Verify GHA SHA-pinning
mise run lint-docs                                  # Validate agent documentation
```

