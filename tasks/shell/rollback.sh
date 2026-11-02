#!/usr/bin/env bash
# Put back the newest tasks/shell/apply.sh backup byte for byte. A path it lacks did not exist then, so it goes.
# The XDG history stays: it holds commands newer than the backup.
set -euo pipefail
: "${SHELL_BACKUP_PATHS:?run this through: mise run shell:rollback}"
backups="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/shell-backup"

folders=("$backups"/*/)
newest="${folders[${#folders[@]}-1]}"
if [ ! -d "$newest" ]; then
  echo "shell:rollback: no backup under $backups" >&2
  exit 1
fi

for path in $SHELL_BACKUP_PATHS; do
  rm -rf "${HOME:?}/$path"
  if [ -e "$newest$path" ] || [ -L "$newest$path" ]; then cp -Rp "$newest$path" "$HOME/$path"; fi
done
