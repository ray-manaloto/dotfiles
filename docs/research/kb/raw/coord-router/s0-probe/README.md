# S0 probe artifacts (coord-router, 2026-10-04)

Verbatim copies of the throwaway probe mods and the PreToolUse settings arm.
Each mod's `.claude-plugin/plugin.json` is stored as `plugin.json.txt` ON
PURPOSE: `fnhook_gates.discover_plugin_dirs` treats any tree with
`.claude-plugin/plugin.json` + `hooks/hooks.json` as a live repo plugin and
type-checks it against the vendored types, which these evidence copies are
not. Rename it back under a scratch directory to re-run the probe.
