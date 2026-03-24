# Design Document: AI/LLM Agent Orchestration

**Date**: 2026-03-22
**Status**: Approved
**Complexity**: Complex
**Design Depth**: Deep

## 1. Objective
Add and configure a suite of AI agents (Claude, Codex, Gemini) into the dotfiles setup using strictly declarative Mise/Chezmoi patterns, custom Python logic for non-standard installers, and a single source of truth for agent grounding via the AGENTS.md standard.

## 2. Architectural Approach: "The Documentation-First AI Terminal"
This approach respects official installation methods while maintaining a centralized logic layer.

### 2.1 Tool Management (Mise)
- **Runtimes**: Ensure `node` and `bun` are present as foundation layers.
- **Declarative Agents**:
    - **Gemini**: `@google/gemini-cli` (via npm backend).
    - **Codex**: `@openai/codex` (via npm backend).
- **Core Shims**: Use Mise to manage the shims for these tools to ensure path consistency.

### 2.2 Orchestration Logic (Python)
- **Claude Code**: Implement a Python method in `dotfiles-setup` to execute the official `curl -fsSL https://claude.ai/install.sh | bash` command.
- **Extension Logic**: Handle any GitHub CLI extensions or sidecar binaries required for the agents.

### 2.3 Agent Logic & Grounding (AGENTS.md Standard)
- **Master Manifest**: Deploy a single `AGENTS.md` file containing all shared project standards (Zero-Bash, Mise-managed, AMD64 target).
- **Agent Entry Points**: `CLAUDE.md`, `GEMINI.md`, and `CODEX.md` will link to the master `AGENTS.md` to ensure consistent behavior across all providers with zero duplication.
- **Shared Skills**: Scaffold `~/.agents/skills/` for cross-tool capability reuse.

## 3. Core Stack
- **Languages**: Node.js, Python 3.13.
- **Agents**: Claude Code, Codex CLI, Gemini CLI.
- **Managers**: Mise (Tools), Chezmoi (Config), Python (Logic).

## 4. Repository Structure (Updates)
- `python/src/dotfiles_setup/ai.py`: New AI setup logic.
- `home/AGENTS.md.tmpl`: Master project standards.
- `home/CLAUDE.md.tmpl`: Agent entry point.
- `home/GEMINI.md.tmpl`: Agent entry point.
- `home/CODEX.md.tmpl`: Agent entry point.

## 5. Decision Matrix
| Feature | Choice | Rationale |
|---------|--------|-----------|
| Claude Install | Official Script | Respects the complex shim/update logic required by Anthropic. |
| Gemini/Codex | Mise npm | Standard declarative pattern for well-behaved npm CLIs. |
| Grounding | AGENTS.md | Follows emerging standards for multi-agent project context. |

## 6. Constraints & Success Criteria
- **Zero Bash**: Manual shell scripts are forbidden; logic must live in Python.
- **Declarative**: All foundation tools must be in `config.toml`.
- **Validation**: All agents must report version and valid login status.
