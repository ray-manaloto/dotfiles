# Sourced by the p2996:* tasks.
PIN=f17c8d6c7bfef5e02ccadcf33517fd2a53b51b6e
TREE=9899759f9004a7df8442ec57000a17e53e6ad5f6
REMOTE=https://github.com/bloomberg/clang-p2996.git
# Install location (DL-755): change this one line (or set P2996_ROOT) to move it.
ROOT="${P2996_ROOT:-$HOME/.local/share/p2996}"
PREFIX="$ROOT/$PIN"
BIN="$ROOT/bin"  # the one folder on PATH: <name>-p2996 links into $PREFIX/bin
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE="${P2996_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/p2996}"
SRC="$CACHE/source"
BUILD="$CACHE/build"
# The heavy-build gate the legacy host_lock.py takes (fcntl.flock), so one heavy build runs at a time.
LOCK="$HOME/.local/state/dotfiles/heavy-gate.lock"
