# Codex reads its MCP keys from the environment at launch.
codex() { command fnox --config "$HOME/.config/fnox/agent-tools.toml" --no-daemon --non-interactive exec -- codex "$@"; }
