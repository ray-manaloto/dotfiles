#!/bin/sh
set -eu
# Install mise — pinned version for Docker build reproducibility
MISE_VERSION="${MISE_VERSION:-v2026.3.17}" \
  curl -fsSL https://mise.run | sh
