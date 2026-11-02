export ZSH_CACHE_DIR="${ZSH_CACHE_DIR:-$XDG_CACHE_HOME/zsh}"
export ZSH_COMPDUMP="$ZSH_CACHE_DIR/.zcompdump-$ZSH_VERSION"
HISTFILE="$XDG_STATE_HOME/zsh/history"
mkdir -p "${HISTFILE:h}" "$ZSH_CACHE_DIR"
HISTSIZE=50000
SAVEHIST=10000
setopt HIST_IGNORE_DUPS HIST_IGNORE_SPACE SHARE_HISTORY
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git gh)
fpath=(/opt/homebrew/share/zsh/site-functions $fpath)
fpath=("$XDG_CACHE_HOME/zsh/completions" "$ZSH/custom/completions" "$HOME/.docker/completions" $fpath)
zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 13
export LS_COLORS="${LS_COLORS:-di=1;36:ln=35:so=32:pi=33:ex=31:bd=34;46:cd=34;43:su=30;41:sg=30;46:tw=30;42:ow=30;43}"
if [[ -r "$ZSH/oh-my-zsh.sh" ]]; then
  source "$ZSH/oh-my-zsh.sh"
else
  autoload -Uz compinit
  compinit -d "$ZSH_COMPDUMP"
fi
