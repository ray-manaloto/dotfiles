[Skip to content](https://mise.jdx.dev/cli/mcp.html#VPContent)

On this page

# `mise mcp` [​](https://mise.jdx.dev/cli/mcp.html\#mise-mcp)

- **Usage:**`mise mcp`
- **Source code:** [`src/cli/mcp.rs`](https://github.com/jdx/mise/blob/main/src/cli/mcp.rs)

Run the Model Context Protocol server over stdin/stdout

Exposes project tools, tasks, environment, and configuration to an MCP client. Resources use `mise://tools`, `mise://tasks`, `mise://env`, and `mise://config`. `mise://tools?include_inactive=true` also includes inactive installations.

The `list_commands` tool describes commands and their declared effects. `run_task` executes project tasks with the user's permissions and can change files or invoke external services. `install_tool` is advertised but currently returns an error. Environment resources contain real values, including secrets.

Resources available:

- mise://tools - List all tools (use ?include\_inactive=true to include inactive tools)
- mise://tasks - List all tasks with their configurations
- mise://env - List all environment variables
- mise://config - Show configuration files and project root

Tools available:

- list\_commands - Every mise command, with its declared effect on the world
- install\_tool - Install a tool with an optional version (not yet implemented)
- run\_task - Execute a mise task with optional arguments

Note: This is primarily intended for integration with AI assistants like Claude, Cursor, or other tools that support the Model Context Protocol. See [https://mise.jdx.dev/mcp.html](https://mise.jdx.dev/mcp.html) for client configuration and access controls.

## Flags [​](https://mise.jdx.dev/cli/mcp.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/mcp.html\#examples)

Start from the project directory; an MCP client handles the protocol exchange

```
mise -C /path/to/project mcp
```

## Related documentation [​](https://mise.jdx.dev/cli/mcp.html\#related-documentation)

- [MCP integration](https://mise.jdx.dev/mcp.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)