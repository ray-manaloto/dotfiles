# /etc/zprofile has already run path_helper; restore our declared order.
if [[ -r "$HOME/.config/zsh/path.zsh" ]]; then
  source "$HOME/.config/zsh/path.zsh"
fi
