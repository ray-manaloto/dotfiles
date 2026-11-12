# Exactly one interactive activation, after prompt/completion setup.
if [[ -x "$HOME/.local/bin/mise" ]]; then
  # Overridable values use get_env under mise run; see MISE_ENV_CACHE=0 or --fresh-env for raw mise x.
  export MISE_ENV_CACHE="${MISE_ENV_CACHE:-1}"
  eval "$("$HOME/.local/bin/mise" activate zsh)"
fi
