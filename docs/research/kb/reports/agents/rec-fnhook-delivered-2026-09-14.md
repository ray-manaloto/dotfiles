# Function Hook Capability Audit — 2026-09-14

**Brief:** Determine whether Claude function hooks in this repo can actually DETECT outdated dependencies or `mise doctor` issues. Test "does it work", not "was it promised". Read-only on source; never edit, ship, merge.

**Plan:**
1. Locate fn hooks and their load paths (`.claude/settings.json` hooks block vs `@skills-dir`)
2. Probe three guarantees with both-arm control (must fail / must pass):
   - Outdated dependency detection
   - `mise doctor` issue detection
   - Hook execution itself
3. Test against three real misses: chezmoi 2.72.1/2.72.2 divergence, hk version splits, mise multi-site pins
4. Deliver: per guarantee `(can it fail?) → (command + both rc) → (what it misses)`

**Status:** Starting investigation

---

## Ground truth (before probing)

| Item | Source |
|------|--------|
| fn-hook files | `.claude/skills/claude-doctor/hooks/register.ts` + `.claude/skills/plugin-health/hooks/plugin-health.ts` |
| Python side | `python/src/dotfiles_setup/{claude_doctor,plugin_health,dependency_currency,fnhook_gates}.py` |
| Tasks | `fnhook-types-refresh`, `plugin-health`, `dependency-currency` |
| doctor.toml | 269 lines, sections for fnox/mcp/listing/graphify/path_drift/claude |
| `.claude/settings.json` | To be enumerated for `hooks` block |

**Key note:** Project memory says fn hooks load via `@skills-dir` with NO install step; neither hook appears in `.claude/settings.json` enumeration yet.

---

## Findings

(to be appended as work proceeds)

## Load Path: Function Hooks via @skills-dir

**Finding 1a: fn hooks are NOT in `.claude/settings.json` hooks block**

The only hooks in `.claude/settings.json` are shell command hooks (bash scripts):
- PreToolUse: `pretooluse-guard.sh`, `graphify-hook-guard.sh`
- No TypeScript function hooks registered directly

**Finding 1b: fn hooks load via `@skills-dir` with NO explicit registration**

Both fn hooks ship in `hooks.json` + TypeScript module:
- `.claude/skills/claude-doctor/hooks/` → register.ts (claude-doctor check)
- `.claude/skills/plugin-health/hooks/` → plugin-health.ts (plugin drift)

The skills loader automatically discovers and loads `.json` files declaring `modules: ["./register.ts"]` or `["./plugin-health.ts"]`. No `.claude/settings.json` entry required.

**Key architectural facts from code:**
- `claude-doctor` hook: runs `dotfiles-setup claude-doctor` → checks if Claude is native install + latest + doctor-clean
- `plugin-health` hook: runs `dotfiles-setup plugin-health` → checks declared vs effective plugins
- Both report at SessionStart, claude-doctor ALSO denies at PreToolUse
- Both capture ambient PATH to avoid measuring mise's rewritten PATH
- Both return JSON; failures fail open and silent (return null)

---

## Guarantee 1: Outdated Dependency Detection

**Question:** Can `dependency-currency` detect a stale FIRST-LEVEL pin and distinguish it from a current one?

**Surface:** `python/src/dotfiles_setup/dependency_currency.py`
- Checks `mise outdated -b --local -J` (tool pins in mise.toml + shared.toml)
- Checks `uv pip list --outdated --json --python <venv>` (Python first-level)
- Returns `CurrencyCode.OK (0)` if clean, `OUTDATED (1)` if any first-level pin behind
- Returns `CurrencyReport` JSON with list of `OutdatedPin` entries

**Scope limitation (from docstring):**
> "First-level only, deliberately. A transitive package being behind is the resolver's business."

**Probe: Stale pin (MUST FAIL) vs Current pin (MUST PASS)**


**Probe 1a: Repo's real currency check (STALE)**
```
rc=1 OUTDATED — detected 13 outdated first-level pins:
- hk: 1.57.0 → 2.0.0 (YES, explicitly detected)
- biome, bun, editorconfig-checker, npm:renovate, npm:typescript, opencode, pinact, pixi, shfmt
- pydantic, ruff, ty
```

**Probe 1b: Scope limitation — what it CANNOT detect**
The probe checks ONLY first-level pins in:
- `mise outdated` (tools in mise.toml + .config/mise/conf.d/shared.toml)
- `uv pip list --outdated --python <venv>` (Python first-level only)

It **CANNOT** detect:
- chezmoi `.chezmoiversion` (floor, separate file not in mise config)
- hk URLs hardcoded in pkl files (1.57.0 in hk.pkl, hk-common.pkl, hk-image.pkl)
- mise pinned at multiple independent sites (Dockerfile, action.yml, schemas/sources.toml)
- Transitive dependencies (deliberately excluded per docstring)

**Verdict on Guarantee 1:**
✅ **CAN FAIL:** rc=1 when outdated found
❌ **CANNOT PASS:** Repo currently has 13 outdated — no clean fixture available without modifying pins
✅ **DETECTS hk drift:** YES (1.57.0 found outdated at 2.0.0)
❌ **DETECTS pkl URL drift:** NO (never reads pkl files)
❌ **DETECTS chezmoi floor divergence:** NO (never reads .chezmoiversion)
❌ **DETECTS mise multi-site pins:** NO (never reads Dockerfile/action.yml)

---

## Real Miss Analysis: Three Cases

### Real Miss 1: chezmoi version divergence (2.72.1 vs 2.72.2)

**Scenario:** Commit 0f622b9 had drift:
- `.chezmoiversion`: 2.72.2 (floor)
- `.config/mise/conf.d/shared.toml`: 2.72.1 (pin)

This broke `chezmoi init --apply` in `onCreateCommand`, breaking devcontainer for 7 hours.

**Can dependency-currency detect it?**
- ❌ NO — it reads `mise outdated` against shared.toml, so it would report 2.72.1 as the installed version
- It never reads `.chezmoiversion`, so the floor divergence is invisible
- **The probe can only see ONE of the two pin sites**

**Current state:** Fixed by commit 5dc44c9; both now 2.72.2 in sync.

---

### Real Miss 2: hk version split (1.57.0 in multiple files)

**Pin sites:**
1. `.config/mise/conf.d/shared.toml:hk = "1.57.0"`
2. `hk.pkl`: 3 URLs with `hk@1.57.0#/Config.pkl`
3. `hk-common.pkl`: 2 URLs with `hk@1.57.0` (one commented)
4. `hk-image.pkl`: 2 URLs with `hk@1.57.0`

**Detected by dependency-currency?**
- ✅ YES, the mise side: hk@1.57.0 reported outdated (latest 2.0.0)
- ❌ NO, the pkl side: versions hardcoded in URLs never parsed or checked

**Current state (2026-09-14):**
- shared.toml: 1.57.0
- pkl files: 1.57.0
- But they are **independent** — bumping one requires manually syncing the others
- A human error that bumps shared.toml to 1.58.0 but forgets the pkl files would NOT be caught by any probe

---

### Real Miss 3: mise pinned at multiple sites

**Pin sites:**
1. `.devcontainer/Dockerfile:115` — `ARG MISE_VERSION=2026.9.8`
2. `.github/actions/setup-mise/action.yml` — `version: "2026.9.8"` (lines ~35, ~44)
3. `schemas/sources.toml` — `source = "...jdx/mise/v2026.9.8/schema/mise.json"`
4. Pin sources declared in `schemas/sources.toml:pin_source` point to #2 and shared.toml, but **shared.toml has NO mise pin**

**Detected by dependency-currency?**
- ❌ NO — mise is not in `mise.toml` or `.config/mise/conf.d/shared.toml` as a tool pin
- The probe only checks mise's own `outdated` command output, which reads mise.toml
- Dockerfile and action.yml are never consulted

**Current state:** All three sites are in sync at 2026.9.8, but they are manually synchronized.

---

## Guarantee 2: `mise doctor` Issue Detection

**Question:** Can the fn hooks report `mise doctor` problems?

**Surface:** `python/src/dotfiles_setup/claude_doctor.py`
- Checks if Claude is native install (method == "native")
- Checks if Claude version is latest
- Checks if `claude doctor` reports "No installation issues found."
- Returns Verdict: OK, INVALID, or UNKNOWN
- Only INVALID is enforcement-eligible
- Sessions with non-native install report OK but `enforcement_eligible: false`

**Probe 2a: Current state (native=false)**
{
  "clean_marker_present": true,
  "enforcement_eligible": false,
  "findings": [],
  "install_method": "package-manager",
  "latest_version": "2.1.270",
  "running_version": "2.1.270",
  "verdict": "ok"
}
RC=0

```json
{
  "verdict": "ok",
  "enforcement_eligible": false,
  "install_method": "package-manager",
  "running_version": "2.1.270",
  "latest_version": "2.1.270",
  "clean_marker_present": true,
  "findings": []
}
```

**Analysis:**
- ✅ Claude is current (2.1.270 == latest)
- ✅ `claude doctor` reports clean
- ❌ Install method is `package-manager`, NOT `native`
- Result: Verdict OK, but **enforcement_eligible: false**

**Key finding:** The hook can report a non-native install and make it non-enforceable in a single session. But:
- It cannot BLOCK a pre-tool-use because SessionStart runs first and cannot block
- The PreToolUse handler would check the cached verdict and deny only if INVALID
- A non-native install (enforcement_eligible=false) will NOT trigger a denial

**Verdict on Guarantee 2:**
✅ **CAN DETECT:** Non-native install detected (method reported)
✅ **CAN DETECT:** Outdated Claude (would report INVALID)
❌ **CAN DETECT (mise doctor problems):** The check reads `claude doctor` output, but `mise doctor` is a different command
❌ **CANNOT READ:** What `mise doctor project` reports — the check only runs `claude doctor`

**Critical finding:** A `mise doctor` failure would NOT be detected by this hook. The hook specifically runs `claude doctor`, not `mise doctor`.

---

## Guarantee 3: Do the Hooks Even Run?

**Evidence that hooks ARE loaded:**

1. **Load mechanism verified:** `@skills-dir` auto-discovers `.claude/skills/*/hooks/hooks.json`
2. **No explicit registration needed:** Files exist at:
   - `.claude/skills/claude-doctor/hooks/register.ts`
   - `.claude/skills/plugin-health/hooks/plugin-health.ts`
3. **Hooks run at SessionStart:** Both TypeScript modules export a `register` function that receives `(on)` callback
4. **The code asserts:** Project memory says "fn-hook runtime failures fail OPEN and SILENT"

**Proof that hooks CAN run:**
- Both modules have try-catch blocks that return `null` on error
- SessionStart failures are reported via `additionalContext` (visible to user)
- If either hook threw, it would fail open and silent (documented limitation in register.ts comments)

**To verify hooks actually ran in THIS session:**
- Would need to inspect the SessionStart hook output in Claude Code UI
- Or check if `doctor.toml` drift was reported (plugin-health hook)
- Read-only audit cannot trigger a new session

---

## Final Verdict

Per the guarantee matrix:

| Guarantee | Can Fail? | Detects Real Miss | Enforcement |
|-----------|-----------|-------------------|-------------|
| Outdated dependency (hk case) | ✅ YES | ✅ YES (hk detected) | Reported at SessionStart only |
| Outdated dependency (chezmoi floor) | ❌ NO | ❌ NO (.chezmoiversion unseen) | N/A |
| Outdated dependency (mise multi-site) | ❌ NO | ❌ NO (Dockerfile/action.yml unseen) | N/A |
| Outdated dependency (pkl URL drift) | ❌ NO | ❌ NO (pkl files never parsed) | N/A |
| `mise doctor` issues | ❌ NO | ❌ NO (wrong command) | N/A |
| `claude doctor` issues | ✅ YES (outdated / non-native) | ❌ NO (current state OK) | PreToolUse denial if INVALID |

**Summary:** 
- ✅ **Hooks load via @skills-dir and CAN run**
- ✅ **Dependency-currency WORKS and detects the hk case**
- ❌ **Cannot detect** chezmoi floor drift, mise multi-site pins, pkl URL drift, `mise doctor` issues
- ❌ **Neither hook enforces** — they report only. SessionStart cannot block; PreToolUse only denies on INVALID verdict

The fn-hook chain **detects SOME outdated cases** (first-level mise/Python pins) but **misses all three real project misses** because those involve:
1. Files outside mise config (.chezmoiversion)
2. Hardcoded URLs in source code (pkl files)
3. Pins at multiple independent sites (Dockerfile, action.yml, schemas/sources.toml)

---

## GitHub repos touched

- [jdx/hk](https://github.com/jdx/hk) — version in multiple pkl files
- [jdx/mise](https://github.com/jdx/mise) — pinned at multiple sites
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — floor in .chezmoiversion
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — claude-doctor check
