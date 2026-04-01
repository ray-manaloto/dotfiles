#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-standard}"
TOOL_TO_TEST="${2:-}"
IMAGE_REF="${IMAGE_REF:-}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/dotfiles-uv-cache}"

run_base_checks() {
  hk validate
  hk run pre-commit --all
  uv run --directory python dotfiles-setup verify run \
    --category build --category ci --category identity --category architecture --json
  mise doctor
}

case "${MODE}" in
  standard)
    run_base_checks
    ;;
  tool)
    run_base_checks
    test -n "${TOOL_TO_TEST}" || { echo "tool name required"; exit 1; }
    mise test-tool "${TOOL_TO_TEST}"
    ;;
  image)
    run_base_checks
    test -n "${IMAGE_REF}" || { echo "IMAGE_REF env var required"; exit 1; }
    uv run --directory python dotfiles-setup image smoke --image-ref "${IMAGE_REF}"
    uv run --directory python dotfiles-setup image benchmark --image-ref "${IMAGE_REF}"
    ;;
  *)
    echo "usage: $0 [standard|tool|image] [tool-name]" >&2
    exit 1
    ;;
esac
