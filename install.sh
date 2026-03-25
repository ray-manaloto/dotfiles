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

# 4. Install Mise (Standalone)
$GET https://mise.run | sh

# 5. Handoff to Chezmoi
# Use absolute path to ensure we use the mise we just installed
MISE="$HOME/.local/bin/mise"

if [ "$LOCAL_MODE" = true ]; then
    echo "Local mode: Initializing from current directory..."
    # Use the current directory as the source
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Initialize (generates config from .chezmoi.toml.tmpl)
    echo "Generating chezmoi config..."
    $MISE x chezmoi@latest -- chezmoi init --source "$SCRIPT_DIR" --force
    
    # Debug: show what data chezmoi has
    echo "Chezmoi data:"
    $MISE x chezmoi@latest -- chezmoi data || echo "Failed to get chezmoi data"
    
    # Apply the dotfiles
    echo "Applying dotfiles..."
    $MISE x chezmoi@latest -- chezmoi apply --source "$SCRIPT_DIR" --force
else
    # For remote mode
    $MISE x chezmoi@latest -- chezmoi init --apply --force "$GITHUB_USER"
fi
