# Silent defaults for every zsh, including non-interactive agent commands.
# zsh reads this file from $HOME; the other startup files come from $ZDOTDIR, so an installer that appends to
# ~/.zprofile or ~/.zshrc edits a file zsh never reads (and none that the repository tracks). ZDOTDIR is exported,
# so a zsh started inside another one reads $ZDOTDIR/.zshenv instead: mise links that to this file too.
export ZDOTDIR="$HOME/.config/zsh"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
if [[ -r "$HOME/.config/zsh/path.zsh" ]]; then
  source "$HOME/.config/zsh/path.zsh"
fi
