# Linked by mise into the checkout: an installer that writes here edits the repository, so `git status` shows it.
for _dotfiles_rc in "$HOME/.zshrc.d"/*.zsh(N); do
  source "$_dotfiles_rc"
done
unset _dotfiles_rc
