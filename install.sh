#!/usr/bin/env bash
set -euo pipefail

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

# 2. Dynamic platform detection
if [[ -z "${FORCE_PLATFORM:-}" ]]; then
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    case "$OS" in
        Darwin)
            case "$ARCH" in
                arm64) export FORCE_PLATFORM="osx-arm64" ;;
                x86_64) export FORCE_PLATFORM="osx-64" ;;
                *) echo "Error: Unsupported Mac architecture: $ARCH" >&2; exit 1 ;;
            esac
            ;;
        Linux)
            case "$ARCH" in
                x86_64) export FORCE_PLATFORM="linux-64" ;;
                aarch64|arm64) export FORCE_PLATFORM="linux-aarch64" ;;
                *) echo "Error: Unsupported Linux architecture: $ARCH" >&2; exit 1 ;;
            esac
            ;;
        *) echo "Error: Unsupported OS: $OS" >&2; exit 1 ;;
    esac
fi

# 3. Setup PATH
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/.local/bin"

# 4. Detect curl or wget
if command -v curl >/dev/null 2>&1; then
    GET="curl -fsSL"
elif command -v wget >/dev/null 2>&1; then
    GET="wget -qO-"
else
    echo "Error: curl or wget is required." >&2; exit 1
fi

# 5. Install Mise (Standalone)
$GET https://mise.run | sh

# 6. Minimal Bootstrap Tools
# Use absolute path to ensure we use the mise we just installed
MISE="$HOME/.local/bin/mise"
# git is typically provided by the system (apt) as it's a prerequisite for mise plugins
# We ensure chezmoi is at the latest version via mise.
$MISE use -g chezmoi@latest

# 7. Handoff to Chezmoi
if [ "$LOCAL_MODE" = true ]; then
    echo "Local mode: Initializing from current directory..."
    # Ensure we are in the source directory chezmoi expects
    cd "$HOME/.local/share/chezmoi"
    
    # Initialize (generates config from .chezmoi.toml.tmpl)
    echo "Generating chezmoi config..."
    $MISE exec chezmoi -- chezmoi init --source . --force
    
    # Debug: show what data chezmoi has
    echo "Chezmoi data:"
    $MISE exec chezmoi -- chezmoi data || echo "Failed to get chezmoi data"
    
    # Apply the dotfiles
    echo "Applying dotfiles..."
    $MISE exec chezmoi -- chezmoi apply --force
    
    # Finalize tool installation
    echo "Finalizing Mise tool installation..."
    $MISE install --yes
else
    # For remote mode
    $MISE exec chezmoi -- chezmoi init --apply --force "$GITHUB_USER"
    $MISE install --yes
fi
