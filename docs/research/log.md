# Log

## 2026-11-03

**Creation** — Added `clion-mcp.md`. CLion 2026.3 RC (CL-263.7307.108) replaced 2026.2.4.1 as the IDE behind the user-scope `clion` MCP entry. It serves the same endpoint, `http://127.0.0.1:64362/stream`, so `~/.claude.json` needed no change, and no configuration this repo applies named a CLion version, path or port. The note also covers the `ECONNREFUSED` that sessions started before the switch show, and the `clion-debugger` skill. That skill ships inside CLion, and GitHub searches on that day found no JetBrains repo, plugin or marketplace entry for it. So it is installed by the IDE's export action and never committed here.

**Update** — `clion-mcp.md` now installs the `clion-debugger` skill with the `clion:skills` mise task, which bootstrap runs. The task copies the skill from the installed CLion's jar, so nothing from JetBrains is committed. CLion's own export copies the skill once and never updates it. The task owns only a folder it marked, and leaves edits and foreign folders alone. The deferred-task entry is replaced by the reason CLion's own sync to agent homes is not used.

**Update** — `clion:skills` now takes the skill from the CLion serving the `clion` MCP entry: the module jar the process listening on its port has open. Before, it took the highest installed version, which gave 2026.3's skill, with its different tool names, to a session that 2026.2 served. With no listener it changes nothing and reports `no-server`, so bootstrap still passes. This design merges this session's version with a parallel Codex session's.
