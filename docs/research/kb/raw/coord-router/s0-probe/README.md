# S0 probe artifacts (coord-router, 2026-10-04)

Verbatim copies of the throwaway probe mods and the PreToolUse settings arm.
Each mod's `.claude-plugin/plugin.json` is stored as `plugin.json.txt` ON
PURPOSE: `fnhook_gates.discover_plugin_dirs` treats any tree with
`.claude-plugin/plugin.json` + `hooks/hooks.json` as a live repo plugin and
type-checks it against the vendored types, which these evidence copies are
not. Rename it back under a scratch directory to re-run the probe.

Each mod's `hooks/register.ts` is likewise stored as `register.ts.txt`: the
root `tsconfig.json` includes `**/hooks/**/*.ts`, so `fnhook_gates` type-checks
any such file against the vendored (2.1.277) types, which lack `session.send`.
That broke `mise run ship` lint on 2026-10-05; rename back under a scratch dir
to re-run the probe.
