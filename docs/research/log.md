# Log

## 2026-11-03

**Creation** — Added `clion-mcp.md`. CLion 2026.3 RC (CL-263.7307.108) replaced 2026.2.4.1 as the IDE behind the user-scope `clion` MCP entry. It serves the same endpoint, `http://127.0.0.1:64362/stream`, so `~/.claude.json` needed no change, and no configuration this repo applies named a CLion version, path or port. The note also covers the `ECONNREFUSED` that sessions started before the switch show, and the `clion-debugger` skill. That skill ships inside CLion, and GitHub searches on that day found no JetBrains repo, plugin or marketplace entry for it. So it is installed by the IDE's export action and never committed here.
