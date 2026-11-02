# Copied by mise. Installer writes create drift, never edits to the repository.
for _dotfiles_rc in "$HOME/.zshrc.d"/*.zsh(N); do
  source "$_dotfiles_rc"
done
unset _dotfiles_rc
