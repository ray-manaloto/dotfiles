# Reapply after macOS /etc/zprofile runs path_helper. No external commands.
typeset -U path
# Remove retired managers and ambient Homebrew build-tool paths.
path=("${(@)path:#$HOME/.local/share/mde/bin}")
path=("${(@)path:#$HOME/.cache/oh-my-opencode/bin}")
path=("${(@)path:#$HOME/.opencode/bin}")
path=("${(@)path:#/usr/local/Homebrew/*}")
path=("${(@)path:#/usr/local/opt/*}")
_inherited=($path)
path=("$XDG_DATA_HOME/mise/shims" "$HOME/.local/bin" /usr/local/share/mise/shims
      /opt/homebrew/bin /opt/homebrew/sbin /usr/bin /bin /usr/sbin /sbin $path
      "$HOME/.docker/bin"
      "$HOME/Library/Application Support/JetBrains/Toolbox/scripts"
      /Applications/Obsidian.app/Contents/MacOS
      "$HOME/.antigravity-ide/antigravity-ide/bin")
# Only a login shell takes this order: elsewhere what `mise run` or a venv put first stays first.
[[ -o login ]] || path=($_inherited $path)
unset _inherited
export PATH
