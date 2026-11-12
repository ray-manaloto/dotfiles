# /etc/zprofile has already run path_helper; restore our declared order.
if [[ -r "${ZDOTDIR:-$HOME/.config/zsh}/path.zsh" ]]; then
  source "${ZDOTDIR:-$HOME/.config/zsh}/path.zsh"
fi
