#!/usr/bin/env bash
# Link the zsh startup files into $HOME through mise's [dotfiles], after a private backup of what they replace.
# A repeat with nothing to change makes no backup, so tasks/shell/rollback.sh still reaches the pre-apply files.
set -euo pipefail
: "${SHELL_BACKUP_PATHS:?run this through: mise run shell:apply}"
# Named, because a whole-config apply would also repoint ~/.zshrc.d/60-agent-tools.zsh at this checkout.
targets=('~/.zshenv' '~/.zprofile' '~/.zshrc' '~/.zshrc.d/10-zsh.zsh' '~/.zshrc.d/90-mise.zsh' '~/.config/zsh/path.zsh')
retired=("$HOME/.zprofile.d/macos-dev-env.zsh" "$HOME/.zshrc.d/50-mde-secrets.zsh")
state="${XDG_STATE_HOME:-$HOME/.local/state}"
cache="${XDG_CACHE_HOME:-$HOME/.cache}"

# --force: a symlink entry never replaces a real file without it, even an identical one.
link() { mise dot apply --force --yes "$@" "${targets[@]}"; }

copy_live() {
  for path in $SHELL_BACKUP_PATHS; do
    if [ -e "$HOME/$path" ] || [ -L "$HOME/$path" ]; then cp -Rp "$HOME/$path" "$1/"; fi
  done
}

refuse() {
  rm -rf "$backup"
  echo "shell:apply: $1; nothing changed" >&2
  exit 1
}

# The links would point into this checkout, and a linked worktree goes away with its branch.
if [ -f .git ]; then
  echo "shell:apply: this is a linked git worktree; run it from the main checkout" >&2
  exit 1
fi

pending="$(link --dry-run; ls "${retired[@]}" 2>/dev/null || true)"
if [ -n "$pending" ]; then
  scratch="$(mktemp -d)"
  trap 'rm -rf "$scratch"' EXIT
  backups="$state/dotfiles/shell-backup"
  backup="$backups/$(date +%Y%m%dT%H%M%S)"
  mkdir -p "$backups"
  chmod 700 "$backups"
  mkdir -m 700 "$backup"
  copy_live "$backup"

  # A clean start prints the one word. env -i keeps the shell's XDG paths inside the scratch folder.
  mkdir "$scratch/home" "$scratch/now"
  cp -R unix/home/. "$scratch/home"
  started="$(env -i HOME="$scratch/home" PATH="$PATH" TERM=dumb zsh -il -c 'print started' </dev/null 2>&1 || true)"
  [ "$started" = started ] || refuse "a shell started from unix/home printed: $started"

  # Compared as two folders: Apple diff fails on a dangling link or an absent path named on its command line.
  copy_live "$scratch/now"
  diff -r --no-dereference "$backup" "$scratch/now" >/dev/null || refuse "a live file changed during the run"

  link
  rm -f "${retired[@]}"
fi

history="$state/zsh/history"
if [ -f "$HOME/.zsh_history" ] && [ ! -e "$history" ]; then
  mkdir -p "${history%/*}"
  install -m 600 "$HOME/.zsh_history" "$history"
fi

mkdir -p "$cache/zsh/completions"
mise completion zsh >"$cache/zsh/completions/_mise"
