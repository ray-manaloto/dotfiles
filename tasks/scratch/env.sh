#!/usr/bin/env bash
# Run one command from this checkout with every home-derived path inside a scratch folder.
# Usage: bash tasks/scratch/env.sh <folder> <command> [args...]
# The climb stops above the checkout, and auto-install is off, so a config the climb reached installs nothing.
set -euo pipefail
root="$1"
shift
top="$(cd "$(dirname "$0")/../.." && pwd -P)"
cd "$top"
mkdir -p "$root/home" "$root/config" "$root/data" "$root/state" "$root/cache" "$root/tmp"
isolated=(env -i "HOME=$root/home" "USER=$USER" "PATH=$PATH" TERM=dumb "TMPDIR=$root/tmp"
  "XDG_CONFIG_HOME=$root/config" "XDG_DATA_HOME=$root/data" "XDG_STATE_HOME=$root/state" "XDG_CACHE_HOME=$root/cache"
  "MISE_TRUSTED_CONFIG_PATHS=$top" "MISE_CEILING_PATHS=${top%/*}" MISE_AUTO_INSTALL=0)
# The receipt that the climb stopped: the only config listed is this checkout's mise.toml.
"${isolated[@]}" mise config ls >&2
exec "${isolated[@]}" "$@"
