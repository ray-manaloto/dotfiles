#!/usr/bin/env bash
# Link the zsh startup files into $HOME through mise's [dotfiles], after a private backup of what they replace.
# The first run that links keeps it as pre-apply for tasks/shell/rollback.sh; a later one as replaced-<time>.
# A repeat with nothing to change makes neither.
set -euo pipefail
: "${SHELL_BACKUP_PATHS:?run this through: mise run shell:apply}"
# Named, because a whole-config apply would also repoint ~/.zshrc.d/60-agent-tools.zsh at this checkout.
targets=('~/.zshenv' '~/.zprofile' '~/.zshrc' '~/.zshrc.d/10-zsh.zsh' '~/.zshrc.d/90-mise.zsh' '~/.config/zsh/path.zsh')
state="${XDG_STATE_HOME:-$HOME/.local/state}"
cache="${XDG_CACHE_HOME:-$HOME/.cache}"

# --force: a symlink entry never replaces a real file without it, even an identical one.
link() { mise dot apply --force --yes "$@" "${targets[@]}"; }

copy_live() {
  for path in $SHELL_BACKUP_PATHS; do
    if [ -e "$HOME/$path" ] || [ -L "$HOME/$path" ]; then
      mkdir -p "$1/$(dirname "$path")"
      cp -Rp "$HOME/$path" "$1/$path"
    fi
  done
}

refuse() {
  echo "shell:apply: $1; nothing changed" >&2
  exit 1
}

# The links would point into this checkout, and a linked worktree goes away with its branch.
if [ -f .git ]; then
  echo "shell:apply: this is a linked git worktree; run it from the main checkout" >&2
  exit 1
fi

# Its own statement: only a plain assignment passes the dry run's failure to set -e.
pending="$(link --dry-run)"
if [ -n "$pending" ]; then
  backups="$state/dotfiles/shell-backup"
  mkdir -p "$backups"
  chmod 700 "$backups"
  fresh="$backups/.incoming.$$"
  scratch="$(mktemp -d)"
  trap 'rm -rf "$fresh" "$scratch"' EXIT
  mkdir -m 700 "$fresh"
  copy_live "$fresh"

  # A clean start prints the one word. env -i keeps the shell's XDG paths inside the scratch folder.
  mkdir "$scratch/home" "$scratch/now"
  cp -R unix/home/. "$scratch/home"
  started="$(env -i HOME="$scratch/home" PATH="$PATH" TERM=dumb zsh -il -c 'print started' </dev/null 2>&1 || true)"
  [ "$started" = started ] || refuse "a shell started from unix/home printed: $started"

  # Compared as two folders: Apple diff fails on a dangling link or an absent path named on its command line.
  copy_live "$scratch/now"
  diff -r --no-dereference "$fresh" "$scratch/now" >/dev/null || refuse "a live file changed during the run"

  # Renamed after every check, so pre-apply is only ever a whole backup. Only a rollback frees the name.
  if [ -e "$backups/pre-apply" ]; then
    mv "$fresh" "$backups/replaced-$(/bin/date +%Y%m%dT%H%M%S.%N%z)"
  else
    mv "$fresh" "$backups/pre-apply"
  fi
  link
fi

history="$state/zsh/history"
if [ -f "$HOME/.zsh_history" ] && [ ! -e "$history" ]; then
  mkdir -p "${history%/*}"
  install -m 600 "$HOME/.zsh_history" "$history"
fi

mkdir -p "$cache/zsh/completions"
mise completion zsh >"$cache/zsh/completions/_mise"
