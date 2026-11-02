#!/usr/bin/env bash
# Put back the pre-apply backup of tasks/shell/apply.sh byte for byte. A path it lacks did not exist then, so it goes.
# What was live moves to replaced-<time> first, with its path relative to HOME.
# The XDG history stays: it holds commands newer than the backup.
set -euo pipefail
: "${SHELL_BACKUP_PATHS:?run this through: mise run shell:rollback}"
backups="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/shell-backup"

pre_apply="$backups/pre-apply"
if [ ! -d "$pre_apply" ]; then
  echo "shell:rollback: no backup at $pre_apply" >&2
  exit 1
fi

replaced="$backups/replaced-$(/bin/date +%Y%m%dT%H%M%S.%N%z)"
mkdir -m 700 "$replaced"
for path in $SHELL_BACKUP_PATHS; do
  if [ -e "$HOME/$path" ] || [ -L "$HOME/$path" ]; then
    mkdir -p "$replaced/$(dirname "$path")"
    mv "$HOME/$path" "$replaced/$path"
  fi
  if [ -e "$pre_apply/$path" ] || [ -L "$pre_apply/$path" ]; then
    mkdir -p "$HOME/$(dirname "$path")"
    cp -Rp "$pre_apply/$path" "$HOME/$path"
  fi
done
