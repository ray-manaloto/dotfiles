# Advisory: Mise Native Claude Code Binary vs npm Package

**Status:** Report in progress — evidence gathering phase

**Decision under advice:** Should mise manage Claude Code via the native Mach-O binary + launcher, or continue with the npm package?

**Proposed change shape:** Add a new entry to `~/.config/mise/config.toml` with `allow_builds`, by analogy to existing codex/gemini entries.

## Operator-stated facts (to verify)

1. mise 2026.9.5 on macOS ARM
2. `npm.package_manager = "bun"` set globally in both `~/.config/mise/config.toml` and project `mise.toml`
3. `allow_builds` is allegedly ineffective under bun per mise docs line 236
4. `npm:@anthropic-ai/claude-code` 2.1.269 is installed but orphaned (not in active config)
5. Native optional dep is present (203 MB)
6. Native installer tree is ahead (has 2.1.270)
7. `~/.local/bin/claude` was deleted during diagnosis
8. Other entries (`codex`, `gemini`) also have `allow_builds` under bun (no-ops)

## Evidence gathering

### Fetching mise npm backend docs...

### Fact 1: Verified — allow_builds is ineffective under bun

**Source:** https://raw.githubusercontent.com/jdx/mise/main/docs/dev-tools/backends/npm.md (fetched 2026-09-12)

**Evidence:** Line 236:
> `allow_builds` does not affect `bun` installs because mise's Bun path is a global install and does not write a per-transitive `trustedDependencies` allowlist.

**Condition:** This applies when `npm.package_manager = "bun"` (confirmed both in `~/.config/mise/config.toml` and project `mise.toml`).

**Impact:** The operator's proposed `allow_builds = ["@anthropic-ai/claude-code"]` line would be a **no-op**. It is identical in effect to the existing entries on `codex` and `gemini`.

---

### Fact 2: Verified — postinstall runs, creates bin/claude symlink, native optional dep is present

**Evidence:**
- `~/.local/share/mise/installs/npm-anthropic-ai-claude-code/2.1.269/bin/claude` exists as a symlink to the native binary
- `~/.local/share/mise/installs/npm-anthropic-ai-claude-code/2.1.269/node_modules/@anthropic-ai/claude-code-darwin-arm64/claude` exists (194 MB, executable)
- Install.cjs postinstall script (lines 99–138) hardlinks or copies the native binary from `node_modules/@anthropic-ai/claude-code-darwin-arm64/claude` to `bin/claude.exe`

**Operator's claim:** "postinstall did not run" — **REFUTED**. Postinstall ran; it created the symlink and the native optional dep is present. The 203 MB binary was downloaded.

---

### Fact 3: Verified — native installer tree is healthy and ahead

`~/.local/share/claude/versions/` contains: 2.1.267, 2.1.268, 2.1.269, **2.1.270** (latest)

`ClaudeCode.app` is present.

The native installer infrastructure is functional and up-to-date.

---

### Fact 4: Verified — ~/.local/bin/claude was deleted and is missing

Confirmed: no launcher in `~/.local/bin/`.

This is the CRITICAL MISSING PIECE. Without it, the npm install cannot be invoked as `claude` on the shell.

---

### Fact 5: Context — other npm tools also have useless allow_builds

`npm:@openai/codex` and `gemini` both declare `allow_builds` in config.toml, both under bun, both no-ops.

---

## Investigation: What creates ~/.local/bin/claude?

**Hypothesis 1:** mise's npm backend creates a shim/wrapper — **NOT CONFIRMED**. 

mise does create `~/.local/share/mise/installs/npm-<tool>/<version>/bin/<name>` for the tool's own binary, but does NOT automatically populate `~/.local/bin/`. That is typically done by:

**Hypothesis 2 (more likely):** mise shells out to the package manager (bun/npm/pnpm) which creates a bin wrapper, OR the postinstall script creates it.

**Hypothesis 3:** The native installer creates `~/.local/bin/claude` when `claude update` runs. This is the most plausible.

**Evidence supporting Hypothesis 3:**
- The native version tree (2.1.267–270) exists independently of the npm install path
- `ClaudeCode.app` exists (not downloaded by npm postinstall, created by native installer)
- The npm postinstall only manages `bin/claude.exe` inside the npm install directory, not `~/.local/bin`

---

## Decision: What actually creates the native binary's launcher?

The **native Claude Code installer** (`~/.local/share/claude/`) owns:
- Version binaries at `~/.local/share/claude/versions/<version>/`
- The `ClaudeCode.app` bundle
- The launcher at `~/.local/bin/claude` (when `claude update` or the native installer runs)

The **npm postinstall** owns:
- Downloading and placing the native binary inside the npm install tree
- Creating `bin/claude` symlink or copy inside `~/.local/share/mise/installs/npm-anthropic-ai-claude-code/`

**These are two separate installation paths.**

---

## Ranked Approaches with Risks

### (a) Add `bun_args = "--trust"` on a new claude entry, keeping bun

```toml
[tools]
"npm:@anthropic-ai/claude-code" = { version = "2.1.270", bun_args = "--trust" }
```

**Outcome:** mise would install the npm package with bun. The postinstall would download and place the native binary in the npm install tree. But `~/.local/bin/claude` would STILL NOT BE CREATED by this step.

**Blocker:** The npm postinstall creates `bin/claude` *inside* the npm tool's directory, not in `~/.local/bin/`. mise does not automatically expose npm `bin` entries as shell-accessible commands.

**Risk:** **MEDIUM-HIGH** — The npm package installs but the native binary cannot be invoked as `claude` on the shell without a shim/wrapper. The operator would have to either:
- Add `~/.local/bin/claude` as a symlink to the npm install's `bin/claude` (manual workaround)
- Or rely on the native installer to create it (out-of-mise control)

**Blast radius on ~60 npm tools:** NONE — `bun_args` only affects this one entry.

---

### (b) Switch npm.package_manager to aube/pnpm, use allow_builds

```toml
[settings.npm]
package_manager = "aube"  # or "pnpm"

[tools]
"npm:@anthropic-ai/claude-code" = { version = "2.1.270", allow_builds = ["@anthropic-ai/claude-code"] }
```

**Outcome:** Same launcher problem as (a). `allow_builds` would at least be *recognized* by aube/pnpm (not a no-op), but postinstall still creates the binary in the npm install tree, not `~/.local/bin`.

**Risk:** **HIGH** — Global change affecting ~60 npm-backed tools. If aube/pnpm differ from bun in behavior (dependency resolution, caching, speed), all tools could be affected. The codex entry explicitly uses aube, but that is one tool, not validation for all 60.

**Blast radius:** **VERY LARGE** — `npm.package_manager` is a GLOBAL setting. Every npm tool would use aube/pnpm instead of bun.

---

### (c) Non-npm backend (github:/release artifacts)

```toml
"github:anthropic-ai/claude-code" = { version = "2.1.270" }
```

**Research:** Anthropic does NOT publish Claude Code releases on GitHub (no `https://github.com/anthropic-ai/claude-code` repo, no release artifacts).

**Risk:** **BLOCKING** — Not feasible.

---

### (d) Do not manage claude via mise; let the native installer own it

Remove the orphaned npm install. Let `claude` stay managed by Anthropic's native installer only.

**Outcome:** 
- `~/.local/bin/claude` would be created and maintained by `claude update` (the native update mechanism)
- No mise dependency or version pinning
- PATH resolves the native launcher directly
- mise has zero responsibility or troubleshooting surface

**Risk:** **LOW** — This decouples mise from a tool it cannot fully manage via npm anyway (the npm postinstall and native installer are in conflict).

**Blast radius:** NONE — removes a tool from mise's scope.

---

## The Unresolved Problem: How Does ~/.local/bin/claude Get Created?

All four approaches assume that **something creates the launcher at ~/.local/bin/claude**. The evidence suggests:
- NOT the npm postinstall (postinstall only creates `bin/claude` inside the npm install directory)
- NOT mise itself (mise does not expose npm bin entries as shell commands by default)
- LIKELY the native installer (`claude update` or the automatic update mechanism)

**Until this is verified, no approach guarantees that `claude` will be invokable as a shell command.**

---

## Recommendation

**Start with approach (d): Remove the orphaned npm install from mise management.**

**Reasoning:**
1. The npm package manages the native binary (postinstall downloads it), but mise does not own the launcher creation.
2. The native installer already manages the full installation (versions, launcher, ClaudeCode.app).
3. Combining both creates maintenance confusion (two installation paths, divergent versions, conflicting update mechanisms).
4. The orphaned `npm:@anthropic-ai/claude-code` entry in config (now commented out) was never completed.

**Next step:** Verify whether `claude update` recreates `~/.local/bin/claude` and measure the native update cycle (frequency, control points).

**Conflict of interest:** No bias toward any particular approach. Approach (c) (github) would not increase codex usage. Approach (b) would affect 60 tools, making it the riskiest.

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — npm backend docs and configuration
- [anthropic-ai/claude-code](N/A) — no public repo (npm package only)

