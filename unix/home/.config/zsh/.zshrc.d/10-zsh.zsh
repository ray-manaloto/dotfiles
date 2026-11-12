export ZSH_CACHE_DIR="${ZSH_CACHE_DIR:-$XDG_CACHE_HOME/zsh}"
export ZSH_COMPDUMP="$ZSH_CACHE_DIR/.zcompdump-$ZSH_VERSION"
HISTFILE="$XDG_STATE_HOME/zsh/history"
mkdir -p "${HISTFILE:h}" "$ZSH_CACHE_DIR"
HISTSIZE=50000
SAVEHIST=10000
setopt HIST_IGNORE_DUPS HIST_IGNORE_SPACE SHARE_HISTORY
fpath=(/opt/homebrew/share/zsh/site-functions $fpath)
fpath=("$XDG_CACHE_HOME/zsh/completions" "$HOME/.oh-my-zsh/custom/completions" "$HOME/.docker/completions" $fpath)
export LS_COLORS="${LS_COLORS:-di=1;36:ln=35:so=32:pi=33:ex=31:bd=34;46:cd=34;43:su=30;41:sg=30;46:tw=30;42:ow=30;43}"
export CLICOLOR=1
setopt AUTO_CD
autoload -Uz compinit up-line-or-beginning-search down-line-or-beginning-search
compinit -d "$ZSH_COMPDUMP"
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
bindkey -e
bindkey '^[[A' up-line-or-beginning-search '^[OA' up-line-or-beginning-search
bindkey '^[[B' down-line-or-beginning-search '^[OB' down-line-or-beginning-search
# A dumb terminal can't draw starship's prompt, and starship says so on stderr at every prompt (1.27.0).
if [[ $TERM != dumb ]] && command -v starship >/dev/null; then
  eval "$(starship init zsh)"
fi
