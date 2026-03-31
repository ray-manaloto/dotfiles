#!/usr/bin/env bash
set -euo pipefail

# Enforce Mise strictness
export MISE_STRICT=1

# Dynamic environment discovery
GITHUB_USER="${GITHUB_USER:-}"
LOCAL_MODE=false

# 1. Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local) LOCAL_MODE=true; shift ;;
        *) GITHUB_USER="$1"; shift ;;
    esac
done

if [[ -z "$GITHUB_USER" && "$LOCAL_MODE" = false ]]; then
    echo "Error: GITHUB_USER is required for remote initialization." >&2
    exit 1
fi

# 2. Setup PATH
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/.local/bin"

# 3. Detect curl or wget
if command -v curl >/dev/null 2>&1; then
    GET="curl -fsSL"
elif command -v wget >/dev/null 2>&1; then
    GET="wget -qO-"
else
    echo "Error: curl or wget is required." >&2; exit 1
fi

# 4. Install Mise (Standalone) — pinned for reproducibility
MISE_VERSION="${MISE_VERSION:-v2026.3.17}"
$GET https://mise.run | MISE_VERSION="$MISE_VERSION" sh

# 5. Handoff to Chezmoi
# Use absolute path to ensure we use the mise we just installed
MISE="$HOME/.local/bin/mise"

CHEZMOI_SOURCE="$HOME/.local/share/chezmoi"

if [ "$LOCAL_MODE" = true ]; then
    echo "Local mode: Initializing from current directory..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Copy repo to chezmoi's standard source directory
    if [ "$SCRIPT_DIR" != "$CHEZMOI_SOURCE" ]; then
        echo "Copying dotfiles to $CHEZMOI_SOURCE..."
        mkdir -p "$(dirname "$CHEZMOI_SOURCE")"
        rm -rf "$CHEZMOI_SOURCE"
        cp -a "$SCRIPT_DIR" "$CHEZMOI_SOURCE"
    fi

    # Trust mise configs in both source and chezmoi dirs
    $MISE trust "$CHEZMOI_SOURCE" 2>/dev/null || true
    $MISE trust 2>/dev/null || true

    # Initialize (generates config from .chezmoi.toml.tmpl)
    echo "Generating chezmoi config..."
    $MISE x chezmoi@2.70.0 -- chezmoi init --force

    # Apply the dotfiles (triggers run_before + run_after scripts)
    echo "Applying dotfiles..."
    $MISE x chezmoi@2.70.0 -- chezmoi apply --force

else
    # Remote mode: chezmoi clones the repo to its source directory
    $MISE x chezmoi@2.70.0 -- chezmoi init --apply --force "$GITHUB_USER"
fi

# Install tools via mise in two phases:
# Phase 1: Install node first — npm-based tools (e.g., @google/gemini-cli) need
# Node.js available before mise can resolve their versions.
# Phase 2: Install everything else.
echo "Installing tools via mise (phase 1: node)..."
cd "$HOME"
$MISE install node -y

echo "Installing tools via mise (phase 2: all remaining)..."
$MISE install -y
