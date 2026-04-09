---
name: omc-hud-wrapper-diagnostic
description: When the OMC HUD statusline shows "Plugin dist/ exists but HUD not found" or similar discovery-wrapper errors, bypass the wrapper and invoke the target directly to surface the real import error. Generalizes to any Node.js wrapper script that walks fallback paths with try/catch and emits a terminal "not found" message.
triggers:
  - "HUD not found"
  - "Plugin dist/ exists but"
  - "OMC HUD"
  - "statusline not rendering"
  - "omc-hud.mjs"
---

# OMC HUD Wrapper Diagnostic (Bypass-the-Wrapper Principle)

## The Insight

Discovery wrappers that walk multiple fallback paths using `try { await import(...) } catch { /* continue */ }` **swallow the real import error**. When all fallbacks fail, they emit a single terminal message that conflates two distinct failure modes:

1. **The file is genuinely missing** (e.g., `dist/hud/index.js` doesn't exist)
2. **The file is present but `await import()` threw** (missing `node_modules/`, broken bundle, syntax error, missing sub-dependency)

The user-visible message — `[OMC HUD] Plugin dist/ exists but HUD not found. Run: cd "..." && npm run build` — reads like case (1), but is emitted for BOTH cases. If you run the suggested `npm run build` and the underlying import still throws, you'll keep seeing the same banner.

## Why This Matters

You can spend an hour on "fix the missing file" when the real problem is a missing runtime dep, a half-bundled dist, or a newly-shipped file the wrapper's path walker doesn't know to check. The banner's specificity misleads the debugger toward the wrong fix.

## Recognition Pattern

- OMC statusline shows an error banner like `[OMC HUD] <anything> not found. Run: <command>`
- The suggested fix (`npm run build`, restart, reinstall) doesn't change anything
- Looking at the plugin dir, the file the error names actually exists
- You're tempted to assume the error message is literal; resist that assumption

This pattern also applies to any wrapper script in `~/.claude/hud/`, `~/.claude/hooks/`, or a plugin-provided entrypoint that ends with `if (!found) { console.log("[X] not found"); }`.

## The Approach

**Bypass the wrapper. Invoke the target directly.**

For the OMC HUD specifically:

```bash
# Simulate a statusline invocation — pipe empty JSON to the shim:
echo '{}' | node ~/.claude/hud/omc-hud.mjs
```

Three possible outcomes:

1. **Renders a formatted statusline** → HUD is healthy. The banner you saw was stale. Restart Claude Code or wait one statusline tick.
2. **Prints the "not found" banner** → The wrapper genuinely couldn't walk to a valid target. Check the target dir contents + version selection logic in the shim.
3. **Throws with a stack trace** → That's the real root cause. Fix the underlying import (usually `cd <plugin-dir> && npm install && npm run build` for pre-4.11.4, or a bundler/dep issue for 4.11.4+).

For ANY wrapper-style discovery script: find the `await import()` / `require()` line, wrap it in a direct invocation with `node -e`, and see the raw error.

## Generalized principle

**When a wrapper script swallows errors and emits a single ambiguous fallback, the debugging technique is to peel off the wrapper and invoke the target contract directly.** This is a specific case of "don't trust error messages from layered infrastructure — reach the source."

## OMC-specific details

- The authoritative shim is at `$HOME/.claude/hud/omc-hud.mjs` — this is NOT a legacy file, despite the path. It's the canonical multi-version discovery wrapper. Do not rewrite `settings.json.statusLine.command` to point at the plugin cache directly; that breaks the 4.11.4+ import-failure fallback from [PR #2416](https://github.com/Yeachan-Heo/oh-my-claudecode/pull/2416).
- The shim walks `~/.claude/plugins/cache/omc/oh-my-claudecode/<version>/dist/hud/index.js`, filters to versions with the file present, picks the newest, and dynamically imports. If import throws, it catches silently and falls through.
- On OMC ≤ 4.11.3: missing `node_modules/` was the common hidden cause (plugin ships source-only; `dist/hud/index.js` was compiled TypeScript that still needed runtime deps).
- On OMC ≥ 4.11.4: 244 previously-gitignored `dist/` files were force-added and the bundle is self-contained. Post-upgrade HUD breakage should be rare.

## Related memory

- `feedback_omc_hud_shim_discovery.md` — the durable fact (shim is authoritative + error-conflating)
- `feedback_omc_plugin_dist_build.md` — the ≤4.11.3 rebuild workaround
- `user_omc_preferences.md` — statusLine configuration
