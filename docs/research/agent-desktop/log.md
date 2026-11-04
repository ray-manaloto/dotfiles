# Directory Update Log

## 2026-11-03
* **Creation**: source reading of vercel-labs/agent-desktop at main `6660fba` (v1.1.0 + 5 commits) and of the
  JetBrainsRuntime, intellij-community and OpenJDK accessibility and analysis code, with an adversarial critique. Read
  only; no settings, plugins or IDE state changed.
* **Addition**: `results.md`, from live runs on CLion 2026.3 RC and macOS 27.2 by a Claude and a Codex session working
  independently. Background error checks work with one open project, the file opened through MCP, and CLion's copy
  matching the disk. Headless `press --app` is blind; `press --window-id` fails closed; Swing tree actions are inert.
* **Rejected**: driving CLion by keystrokes (blind); `expand`/`scroll` on Swing (inert); the focus-steal workflow as the
  default (kept as a multi-project fallback); IDE settings changes (not needed).
* **Failed**: scraping YouTrack IJPL-231204 (every engine); Codex's provider searches (missing secrets profile).
