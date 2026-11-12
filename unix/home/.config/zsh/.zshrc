# Linked by mise into the checkout and read through $ZDOTDIR (set in ~/.zshenv).
for _dotfiles_rc in "${ZDOTDIR:-$HOME/.config/zsh}/.zshrc.d"/*.zsh(N); do
  source "$_dotfiles_rc"
done
unset _dotfiles_rc
