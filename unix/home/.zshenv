# Silent defaults for every zsh, including non-interactive agent commands.
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
if [[ -r "$HOME/.config/zsh/path.zsh" ]]; then
  source "$HOME/.config/zsh/path.zsh"
fi
