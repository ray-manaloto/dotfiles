#!/bin/sh
set -eu
# Install mise — pinned version for Docker build reproducibility
MISE_VERSION="${MISE_VERSION:-v2026.3.18}" \
  curl -fsSL https://mise.run | sh
