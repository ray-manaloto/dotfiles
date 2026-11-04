# Directory Update Log

## 2026-11-03
* **Creation**: Research on LSP plugins after moving the official `*-lsp` plugins to the Anthropic Directory, run
  read-only against Claude Code 2.1.317 (installed binary), the local plugin caches, upstream
  anthropics/claude-plugins-official at `a2e251d9`, Piebald-AI/claude-code-lsps at `92afe665`, and 20 GitHub issue and
  PR searches. No plugin, marketplace or settings file was changed.
* **Addition**: the requirements for LSP in a dotfiles-built marketplace plugin, from the same evidence.
* **Update**: after review, the Directory move gate checks each of the 12 listings for `.lsp.json` at its own
  `reviewed_commit`, and "works today" is narrowed to the one tested route (pyright-lsp through
  claude-plugins-official).
