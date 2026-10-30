# Codex and OpenCode read their MCP keys from the environment at launch.
codex() { command fnox --config "$HOME/.config/fnox/agent-tools.toml" --no-daemon --non-interactive exec -- codex "$@"; }
opencode() { command fnox --config "$HOME/.config/fnox/agent-tools.toml" --no-daemon --non-interactive exec -- opencode "$@"; }
