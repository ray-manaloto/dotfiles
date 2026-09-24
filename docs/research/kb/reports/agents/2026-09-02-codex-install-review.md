# Codex planning-with-files Installation Audit

**Start time:** 2026-09-02  
**Codex version cached:** 3.14.0 (actual in use unknown; desktop app)  
**Docs version audited:** 3.14.0 at `~/.codex/plugins/cache/planning-with-files/planning-with-files/3.14.0/docs/codex.md`

## Documented spec (Method 2: Personal Installation)

Per `codex.md:51-73`, a personal install requires:
1. `~/.agents/skills/planning-with-files/` containing the canonical skill (including SKILL.md)
2. `~/.codex/hooks/` containing hook shell scripts
3. `~/.codex/hooks.json` with 7 entries: SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, PreCompact, Stop
4. In `config.toml`: plugin entry for `planning-with-files` (enabled)
5. In `config.toml`: marketplace entry pointing to the GitHub repo

**Version skew note:** Docs warn that upgrading from ≤3.10.0 changes three command definitions (`SessionStart`, `UserPromptSubmit`, `PreCompact`) and requires re-trusting via `/hooks`.

---

## Actual installation state

### 1. ~/.codex/config.toml
✅ **Plugin declared:**
- Line 248-249: `[plugins."planning-with-files@planning-with-files"]` → `enabled = true`

✅ **Marketplace declared:**
- Lines 557-559: marketplace entry points to `https://github.com/OthmanAdi/planning-with-files.git`

### 2. Hooks in config.toml (hook state)
✅ **Hooks declared and trusted:**
- Lines 430-449: Seven hook entries for planning-with-files@planning-with-files in hooks.state
  - ✅ pre_tool_use:0:0
  - ✅ permission_request:0:0
  - ✅ post_tool_use:0:0
  - ✅ pre_compact:0:0
  - ✅ session_start:0:0
  - ✅ user_prompt_submit:0:0
  - ✅ stop:0:0
- Each has a trusted_hash, meaning they have been reviewed and approved

### 3. Directory inventory

Need to check:
- [ ] `~/.agents/skills/planning-with-files/` exists with SKILL.md
- [ ] `~/.codex/hooks/` exists with expected scripts
- [ ] Hooks are actually executable
- [ ] Plugin cache location for hook command paths


### 4. Disk inventory results

**~/.agents/skills/planning-with-files/**
❌ **NOT FOUND**
- Directory exists: `~/.agents/skills/`
- Contents: 10 memory-index-curation skills only (verified with `ls -la`)
- No planning-with-files entry

**~/.codex/hooks/**
❌ **NOT FOUND**
- Directory does not exist on the user's filesystem

**~/.codex/hooks.json**
❌ **NOT FOUND**
- File does not exist at user level

**Project-level: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/**
✅ **EXISTS:**
- `.codex/hooks.json` present (60 lines, project-specific hooks only; no planning-with-files entries)
- `.codex/hooks/` directory: NOT FOUND
- No planning-with-files hooks in project `.codex/hooks.json`

**Plugin cache: ~/.codex/plugins/cache/planning-with-files/planning-with-files/3.14.0/**
✅ **FULLY PRESENT:**
- `.agents/skills/planning-with-files/SKILL.md` ✅ present
- `.agents/skills/planning-with-files/scripts/` ✅ 22 subdirs
- `.agents/skills/planning-with-files/templates/` ✅ present
- `.codex/hooks/` ✅ present with 17 files:
  - run_sh.py (executable Python)
  - pre_tool_use.py ✅ syntax valid
  - post_tool_use.py
  - permission_request.py
  - stop.py
  - session-start.sh ✅ executable
  - user-prompt-submit.sh ✅ executable
  - pre-compact.sh ✅ executable
  - resolve-plan-dir.sh ✅ executable
  - codex_hook_adapter.py (main adapter)
  - context_frame.py (helpers)
- `.codex-plugin/plugin.json` ✅ points to `./.agents/skills/` and `./hooks/codex-hooks.json`
- `hooks/codex-hooks.json` ✅ has all 7 hooks with ${PLUGIN_ROOT} paths

---

## Installation method: Plugin-based (NOT Method 1 or 2)

**Finding:** The desktop app installed planning-with-files as a **plugin from git marketplace**, not via either documented method.

**Mechanism:**
1. `config.toml:248-249` declares `[plugins."planning-with-files@planning-with-files"]` enabled
2. `config.toml:557-559` marketplace entry for plugin (git source, live at `https://github.com/OthmanAdi/planning-with-files.git`)
3. Plugin is cached at `~/.codex/plugins/cache/planning-with-files/planning-with-files/3.14.0/`
4. Plugin manifest (`.codex-plugin/plugin.json`) declares:
   - Skills at `./.agents/skills/` (resolved relative to cache root)
   - Hooks at `./hooks/codex-hooks.json` (resolved relative to cache root)
5. Codex loads hooks from plugin's manifest, resolving `${PLUGIN_ROOT}` to the cache path at runtime

**Contrast with documented methods:**
- **Method 1 (Workspace):** Would write to project `.agents/skills/planning-with-files/`, `.codex/hooks.json`, `.codex/hooks/` → files would be committed
- **Method 2 (Personal):** Would write to `~/.agents/skills/planning-with-files/`, `~/.codex/hooks.json`, `~/.codex/hooks/` → user-level files
- **Plugin method (actual):** Everything lives in plugin cache; nothing needs to be in user `~/.codex/` or `~/.agents/`; Codex resolves it automatically on startup

---

## Hook execution: Will it work?

**Verdict: YES, hooks should execute.** 

All seven hook commands reference `${PLUGIN_ROOT}` which Codex resolves to the cache directory at runtime. Trace of SessionStart hook:

```
config.toml: [plugins."planning-with-files@planning-with-files"] enabled = true
  ↓
Codex marketplace plugin loader reads plugin.json from cache
  ↓
Plugin manifest: "hooks": "./hooks/codex-hooks.json"
  ↓
Codex loads ~/.codex/plugins/cache/planning-with-files/planning-with-files/3.14.0/hooks/codex-hooks.json
  ↓
Hook command: python3 "${PLUGIN_ROOT}/.codex/hooks/run_sh.py" session-start.sh
  ↓
PLUGIN_ROOT=$HOME/.codex/plugins/cache/planning-with-files/planning-with-files/3.14.0
  ↓
Resolved: python3 ~/.codex/plugins/cache/planning-with-files/planning-with-files/3.14.0/.codex/hooks/run_sh.py
  ✅ File exists and is valid Python
```

**Control arm:** Verify a hook would FAIL if PLUGIN_ROOT were unset:
- Without PLUGIN_ROOT, command becomes `python3 "/.codex/hooks/run_sh.py"` → 404
- Codex has no documented way to run without PLUGIN_ROOT for plugins, so this is an unreachable failure

---

## Configuration status

### Hooks signed/trusted
✅ **All 7 hooks are in hooks.state as trusted** (config.toml:430-449):
- pre_tool_use:0:0 trusted_hash
- permission_request:0:0 trusted_hash
- post_tool_use:0:0 trusted_hash
- pre_compact:0:0 trusted_hash
- session_start:0:0 trusted_hash
- user_prompt_submit:0:0 trusted_hash
- stop:0:0 trusted_hash

This means the user has reviewed and approved them via `/hooks` already.

### Plugin version
✅ **Version 3.14.0 cached and declared**
- Plugin cache version: 3.14.0
- Docs reviewed: 3.14.0 (matching version)
- No version skew detected (docs warn about 3.10.0 → 3.14.0 changes; user is already on 3.14.0)

### Shared state with Claude Code
⚠️ **YES, shared state is active:**
The docs state (codex.md:114): "Local Codex session history is not part of the automatic hook path."
BUT the hooks WILL read and write:
- `task_plan.md` (per SessionStart/UserPromptSubmit hooks)
- `progress.md` (per PostToolUse/PreCompact hooks)
- `findings.md` (implicitly, via skill templates)

These files live in `${PWD}` during `codex exec`, so a shared working directory will cause LAST-WRITE-WINS collisions with Claude Code sessions in the same repo.

---

## Conflict check: Against project rules

### do-not.md #8: Installer writes outside repo
✅ **COMPLIANT** — The desktop app installed to `~/.codex/` only, not to the project repo. However:
- User-level install means secrets / tokens in `~/.codex/` are machine-local
- Planning files will accumulate in every shared project working directory

### feedback_no_user_level_file_updates
⚠️ **VIOLATION RISK** — The plugin **will write** `task_plan.md`, `progress.md`, and `findings.md` to the repo at runtime. If these files end up committed, they could drift from Claude Code's planning.

### Codex "plugin mode vs standalone" rule (codex.md:79)
✅ **COMPLIANT** — Plugin mode is being used. The project's `.codex/hooks.json` contains ONLY project-specific hooks (guard, currency-check, doctor). No planning-with-files entries in project hooks.

---

## Summary of findings

| Item | Status | Notes |
|------|--------|-------|
| Plugin declared in config | ✅ CORRECT | Line 248-249 |
| Marketplace registered | ✅ CORRECT | Lines 557-559, git source |
| All 7 hooks signed | ✅ CORRECT | Lines 430-449, each with trusted_hash |
| Plugin cache exists | ✅ CORRECT | 3.14.0 fully populated |
| Skills in cache | ✅ CORRECT | SKILL.md + templates present |
| Hook scripts in cache | ✅ CORRECT | All Python and shell scripts present |
| Python syntax valid | ✅ CORRECT | Sample pre_tool_use.py validated |
| ~/.agents/skills/planning-with-files | ❌ MISSING | Not Method 2 (personal install) |
| ~/.codex/hooks.json | ❌ MISSING | Not Method 1 or 2 (plugin install instead) |
| ~/.codex/hooks/ | ❌ MISSING | Not Method 1 or 2 (plugin install instead) |
| ${PLUGIN_ROOT} resolution | ✅ OK | Codex standard for plugin mode |
| Project repo conflicts | ⚠️ RISK | Planning files will write to repo at runtime |

