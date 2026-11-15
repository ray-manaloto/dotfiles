# Exactly one interactive activation, after prompt/completion setup.
if [[ -x "$HOME/.local/bin/mise" ]]; then
  # The env cache can replay a stale resolution of a `{ default }` or get_env template, ignoring a
  # caller's override (jdx/mise#15751); rerun with MISE_ENV_CACHE=0 or `mise x --fresh-env`.
  export MISE_ENV_CACHE="${MISE_ENV_CACHE:-1}"
  eval "$("$HOME/.local/bin/mise" activate zsh)"
fi
