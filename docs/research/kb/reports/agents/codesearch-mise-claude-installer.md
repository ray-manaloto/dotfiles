
### bellini666/dotfiles — mise.toml
```toml
agent_install_dir=$(mktemp -d)
trap 'rm -rf "$agent_install_dir"' EXIT

if command -v claude >/dev/null 2>&1; then
  claude update
else
  curl -fsSL https://claude.ai/install.sh -o "$agent_install_dir/claude.sh"
  bash "$agent_install_dir/claude.sh"
fi

curl -fsSL https://chatgpt.com/codex/install.sh -o "$agent_install_dir/codex.sh"
```

### naa0yama/devtool-wsl2 — mise.toml
```toml
#!/usr/bin/env bash
set -euo pipefail
case "$(uname -s)" in
	Linux|Darwin) ;;
	*) echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
esac
curl -fsSL https://claude.ai/install.sh | bash
"""
```

### hiramekun/dotfiles — mise.toml
```toml
description = "Install runtimes and developer tools managed by mise"
run = "mise install"

[tasks.agents]
description = "Install Claude Code and Codex with their official installers"
run = [
  "curl -fsSL https://claude.ai/install.sh | bash",
  "curl -fsSL https://chatgpt.com/codex/install.sh | sh",
]

[tasks.link]
```

### kjgarza/snowyowl — .mise.toml
```toml
  gh extension install github/gh-copilot
fi

# Install Claude Code CLI
if ! command -v claude &> /dev/null; then
  echo "Installing Claude Code CLI..."
  curl -fsSL https://claude.ai/install.sh | bash
fi

echo "✅ All dependencies installed!"
"""
```
```toml

[tasks."install:claude"]
description = "Install Claude Code CLI only"
run = """
if ! command -v claude &> /dev/null; then
  echo "Installing Claude Code CLI..."
  curl -fsSL https://claude.ai/install.sh | bash
else
  echo "Claude Code CLI already installed"
fi
"""
```

### carljohan/dotfiles — mise.toml
```toml
description = "Install vendor-managed tools needed on every host"
run = '''
set -eu

claude="$HOME/.local/bin/claude"
if [ ! -x "$claude" ]; then
  curl -fsSL https://claude.ai/install.sh | bash -s latest
fi
"$claude" --version

codex="$(npm prefix -g)/bin/codex"
```

### advaypakhale/dotfiles — mise.toml
```toml
"""

[tasks.tmux-plugins]
run = '[ -d ~/.config/tmux/plugins/tpm ] || git clone --depth 1 https://github.com/tmux-plugins/tpm ~/.config/tmux/plugins/tpm'

[tasks.claude]
run = '[ -x "$HOME/.local/bin/claude" ] || curl -fsSL https://claude.ai/install.sh | bash'

[tasks.agent-skills]
description = "clone agent-skills and link it as ~/.claude/skills"
run = "./scripts/install_agent_skills.sh"
```

### ericboehs/dotfiles — mise.toml
```toml
# Version check rather than a bare -x test, so a half-installed or broken
# binary reinstalls instead of being taken for a working one.
if "$HOME/.local/bin/claude" --version >/dev/null 2>&1; then
  echo "bootstrap:claude: $("$HOME/.local/bin/claude" --version) already installed"
  exit 0
fi
curl -fsSL https://claude.ai/install.sh | bash
'''
```

### RickDavis404/ai-infra-platform — mise.toml
```toml

# --- Coding agent CLIs (npm backend) ---
# codex CLI, mise-managed via the npm backend (the aqua registry backend for codex lags
# upstream releases; converge to a bare aqua codex pin later).
"npm:@openai/codex" = "0.144.6"
# Claude Code CLI, mise-managed via the npm backend; supersedes the native-installer binary
# (curl https://claude.ai/install.sh) for in-repo use, so the whole agent toolchain is pinned
# and reproducible. The native installer stays optional for out-of-repo use.
# npm_args opts this ONE package back into its postinstall (mise defaults to --ignore-scripts):
# the wrapper package's postinstall downloads the platform-native `claude` binary, without which
# `claude` aborts with "native binary not installed". Scoped to the trusted @anthropic-ai package.
```

### pagerguild/guilde-lite — mise.toml
```toml

# =============================================================================
# AI CODING TOOLS
# =============================================================================
# Installation priority: curl > mise > bun > npm > homebrew
# Claude Code - Install via curl (npm is deprecated):
#   curl -fsSL https://claude.ai/install.sh | bash
#
# The following are managed by mise:

# OpenCode - AI coding assistant (mise native plugin)
```

### abnoumaru/dotfiles — mise.toml
```toml
description = "install Claude CLI if not installed"
run = """
#!/usr/bin/env bash
echo "checking Claude CLI installation..."
if ! command -v claude &> /dev/null; then
  echo "Claude CLI not found, installing..."
  curl -fsSL https://claude.ai/install.sh | bash
else
  echo "Claude CLI is already installed"
fi
"""
```

### jalevin/dotfiles — mise.toml
```toml
#!/usr/bin/env bash
set -euo pipefail

# Claude Code
if ! command -v claude &>/dev/null; then
  echo "Installing Claude Code..."
  curl -fsSL https://claude.ai/install.sh | bash
else
  echo "Claude Code already installed, skipping."
fi
"""
```

### jtsoi/dotfiles — skvk-mbp/mise.toml
```toml
[bootstrap.packages]
"brew:zoxide"                  = {}
"brew:zsh-autosuggestions"     = {}
"brew:zsh-syntax-highlighting" = {}
"brew:starship"                = {}
# Carried over from the retired mbp_modules/01-claude. That module also ran
# `curl https://claude.ai/install.sh | bash` for the CLI, which has no
# declarative equivalent here — install the CLI by hand if a fresh machine
# needs it.
"brew-cask:claude"             = {}
"brew-cask:karabiner-elements" = {}
```
