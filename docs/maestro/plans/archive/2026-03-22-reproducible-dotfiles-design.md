# Design Document: Reproducible Dotfiles Setup

**Date**: 2026-03-22
**Status**: Approved
**Complexity**: Complex
**Design Depth**: Deep

## 1. Objective
Setup a reproducible, declarative dotfiles environment using `chezmoi` and `mise`, targeted for Linux-based devcontainers (and local environments). The setup must enforce "Zero-Bash" logic, total declarative tool management, and strict engineering standards (ruff/mypy).

## 2. Architectural Approach: "The Bare Minimum Bootstrap"
This approach minimizes the entry point to the absolute essentials required to reach a declarative state.

### 2.1 The Sequence
1. **Stage 0 (Shell)**: A tiny `install.sh` detects `curl`/`wget` and installs `mise` using its standalone binary installer.
2. **Stage 1 (Mise Bootstrap)**: Immediately uses `mise` to install `git` and `chezmoi` (latest versions).
3. **Stage 2 (Chezmoi Handoff)**: `chezmoi init --apply <repo>` is executed.
4. **Stage 3 (Declarative Chain)**: Chezmoi renders templates for `mise/config.toml`, `pixi.toml`, and `pyproject.toml`.
5. **Stage 4 (Python Orchestration)**: A `run_once_` Python script (executed via `uv run`) handles dynamic version querying and triggers the final `mise install`.

## 3. Core Stack
- **OS**: Ubuntu 24.04 (Primary Target).
- **Orchestrator**: `chezmoi`.
- **Tool Manager**: `mise` (Global) + `pixi` (Env-specific).
- **Logic Runtime**: Python 3.13+ (via `uv`).
- **Formatting/Linting**: `ruff` + `mypy` (Zero skips).

## 4. Repository Structure (Chezmoi Native)
- `home/`: The `.chezmoiroot`.
- `home/dot_config/mise/config.toml.tmpl`: Templated Mise config.
- `home/dot_pixi.toml.tmpl`: Templated Pixi config.
- `home/executable_run_once_after_00-install-tools.py.tmpl`: Python orchestrator hook.
- `python/`: Source code for the setup library.
- `tests/`: Validation suites.

## 5. Decision Matrix
| Feature | Choice | Rationale |
|---------|--------|-----------|
| Entry Point | Chezmoi via Mise | Ensures `git` and `chezmoi` are version-controlled by `mise`. |
| Scripting | Python (via `uv`) | Replaces fragile Bash with testable, typed logic. |
| Tooling | Mise + Pixi | Best-in-class for global and project-specific reproducibility. |
| Versions | Dynamic Querying | Keeps the setup fresh without manual intervention. |

## 6. Constraints & Success Criteria
- **Zero Bash**: No shell scripts beyond the 20-line Stage 0 bootstrap.
- **Total Declarative**: All tools must be in a config file with pinned versions.
- **Validation**: Must pass `ruff` and `mypy` with zero skips.
- **Reproducibility**: Must build successfully on a bare `ubuntu:latest` image.
