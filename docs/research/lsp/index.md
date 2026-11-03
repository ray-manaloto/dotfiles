---
okf_version: "0.2"
---

# LSP plugins and the Anthropic Directory (Claude Code 2.1.317, 2026-11-03)

Why the official `*-lsp` plugins load 0 language servers when installed through the Anthropic Directory, which other
plugins are exposed to the same gap, whether Piebald-AI/claude-code-lsps is needed, and what a dotfiles marketplace
plugin must do to get working LSP in every project.

* [Root cause: the Directory drops marketplace-entry components](root-cause.md) - the 5-step trace through Claude Code 2.1.317 and the upstream packaging gap.
* [Other strict:false and inline-component plugins](affected-plugins.md) - which other Directory listings depend on a marketplace entry; verified and unverified rows.
* [Piebald-AI/claude-code-lsps](piebald-claude-code-lsps.md) - how it ships LSP config, maintenance, overlap and risks; not needed.
* [GitHub issues, PRs and discussions](github-issues.md) - every relevant item across anthropics/claude-code, claude-plugins-official, claude-plugins-community and Piebald.
* [Recommendations](recommendations.md) - keep claude-plugins-official, file one issue, optional local marketplace; Piebald not needed.
* [LSP in a dotfiles marketplace plugin](dotfiles-marketplace-plugin.md) - the requirements a dotfiles-built plugin must meet for LSP to work in any project.

# Data

* `data/saved-searches.json` - the 20 GitHub issue and PR searches that were run, in the saved-search catalog row shape plus `endpoint`, `qualifiers`, `why` and hit counts.
* `data/search-hits/*.json` - one hit list per saved search (number, title, state, URL, dates, comment count), as returned on 2026-11-03.
