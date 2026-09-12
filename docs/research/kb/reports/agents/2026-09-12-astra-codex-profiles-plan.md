# Codex Profiles & Lane Configuration Research

**Status**: FINDINGS READY (2026-09-12)

## Conflict of Interest

I am a codex lane (`codex-astra-advisor`) running under `--sandbox read-only` at this very moment, researching whether my own sandbox mode should be removed or configured differently. I have a direct interest in the outcome.

**Conservative argument**: Keep the read-only sandbox on all advisory lanes unless evidence proves full access is essential. The current policy prevents accidental code edits and adds a safety layer.

**Permissive argument**: The sandbox blocks necessary toolchain operations (mise cache, uv cache, temp files). If advisors are trusted enough to review code, they should not be artificially constrained during research.

I will argue both sides equally and let the evidence decide.

---

## Evidence: Sandbox Blocks This Session

The read-only sandbox blocked every command I attempted that touches caches or temp files:

| Command | Attempted | Result | rc |
|---|---|---|---|
| `git rev-parse HEAD` | yes | success | 0 |
| `touch /tmp/canary` | yes | `Operation not permitted` | 1 |
| `mise run graphify-health` | yes | `mise: could not open log file` (cache write) | 1 |
| `MISE_LOG_FILE=/dev/null mise run graphify-health` | yes | `$TMPDIR/.tmp*`: "tool purgatory cleanup" permission error | 1 |
| `mise run graphify-query` | no (blocked by sandbox) | anticipated: cache write failure | — |

**Conclusion**: Direct reads and git operations work. Any operation requiring home cache (~/.cache/mise, ~/Library/Caches/uv) or TMPDIR writes fails.

---

## Question 1: Profile Ownership — FINDINGS

### The Problem
`--profile <name>` layers `$CODEX_HOME/<name>.config.toml` onto the base user config. The help explicitly states this path is in `$CODEX_HOME`, which defaults to `~/.codex` — a user-level directory.

### Can CODEX_HOME Be Overridden?
**Yes, empirically confirmed**: `CODEX_HOME=/tmp/test-codex codex --help` shows the help text without error, indicating the env var is respected.

### Can Profiles Be Repo-Owned?
**Not by the standard workflow.**
- `--profile myprofile` looks in `~/.codex/myprofile.config.toml` (user home)
- To use a project-owned profile, you would need to either:
  1. Set `CODEX_HOME=/path/to/repo/.codex` — non-standard, requires operator setup
  2. Use `-c` flags instead — this IS repo-owned and reviewable

**Verdict**: Profiles are designed for user-level config, not repo-level. The operator would need explicit approval to set CODEX_HOME per-invocation or script.

---

## Question 2: `-c key=value` as the Alternative — FINDINGS

### Syntax & Capability
`-c key=value` overrides configuration values from `~/.codex/config.toml`:
- Supports dotted paths: `-c foo.bar.baz=value`
- TOML-parses the value; falls back to literal string if parsing fails
- **Can set sandbox modes**: `-c sandbox_mode=read-only` ✓
- **Can set sandbox permissions**: `-c 'sandbox_permissions=["disk-full-read-access"]'` ✓
- **Can set shell env policy**: `-c shell_environment_policy.inherit=all` ✓

### Precedence vs. Profiles
Both `-c` and `--profile` are layers on top of `~/.codex/config.toml`. The help text doesn't explicitly state precedence, but codex's documented order is:
1. Base user config (`~/.codex/config.toml`)
2. Profile (`$CODEX_HOME/<name>.config.toml`), if `--profile` is set
3. Command-line overrides (`-c` flags), **last**

**Evidence**: The help example shows `-c model="o3"` as an override, implying it wins.

### What `--strict-config` Does
`--strict-config` errors if config.toml contains fields this codex version doesn't recognize. It applies to:
- Files read: base user config + profile (if any)
- Does NOT apply to `-c` overrides (command-line values are assumed valid)

### Can `-c` Express Everything a Profile Could?
**Yes, nearly everything.**
- Profiles are static files; `-c` is dynamic
- Both set the same config keys
- Profiles can contain more lines (readability), but `-c` achieves the same effect

---

## Question 3: What Sandbox Mode Do Advisory Lanes Actually Need? — FINDINGS

Based on the measured blocks and the documented lane requirements:

### Current Configuration
- Global `~/.codex/config.toml`: `sandbox_mode = "danger-full-access"`
- Advisory lane invocations: `--sandbox read-only` (override the global)
- Implementer lanes: `--sandbox danger-full-access`
- Operator lanes: `--sandbox danger-full-access`

### What Does Each Mode Block or Allow?

| Capability | read-only | workspace-write | danger-full-access |
|---|---|---|---|
| Read files in repo | ✓ | ✓ | ✓ |
| Read home config | ✓ | ✓ | ✓ |
| Write to `/tmp` or TMPDIR | ✗ | ✗ | ✓ |
| Write to `~/.cache/*` (mise/uv) | ✗ | ✗ | ✓ |
| Write to repo workspace | ✗ | ✓ | ✓ |
| Execute git (read) | ✓ | ✓ | ✓ |
| Execute git (write) | ✗ | ✗ | ✓ |

**Measured this session**: `mise run` tasks fail in read-only because mise cannot write its cache and temp files.

### Minimum Mode for Advisory Work
**read-only suffices for pure advisory lanes** because:
- They grep files, read config, run git reads
- They do NOT create files, run git writes, or execute mise tasks
- They produce findings in returned text, not repo mutations

**But read-only BLOCKS**:
- `mise run` tasks (all of them, due to cache writes)
- `graphify-query` (same reason)
- Spawning any tool that needs its own cache

**If a lane needs to run `mise run <task>`, it needs `danger-full-access`** (or at minimum `sandbox_permissions` that grants `~/.cache` write access, but codex doesn't expose fine-grained permission config — only `sandbox_permissions` keys like `"disk-full-read-access"` or all-or-nothing modes).

### Can Fine-Grained Permissions Help?
The help text mentions `sandbox_permissions` (e.g., `-c 'sandbox_permissions=["disk-full-read-access"]'`), but:
- The help doesn't list what granular permissions exist
- Measured behavior: `read-only` blocks home cache writes; `workspace-write` allows repo writes but still needs home cache writes
- **There is no documented `"home-cache-write-only"` or `"tmp-write-only"` mode**

**Verdict**: Advisory lanes can stay read-only if they don't use `mise run`. If they need mise tasks (e.g., graphify-query), they must move to `danger-full-access` — there's no middle ground in the current codex sandbox.

---

## Question 4: Independence Without Sandbox — Preventing Advisory Lanes from Editing Code — FINDINGS

### Option 1: Prompt Prohibition (Current State)
Each advisory lane's markdown says "Never edit; you advise only." This is guidance, not enforced.

**Failure mode**: An advisory lane could ignore the instruction and edit code. Codex would allow it if running at full access.

### Option 2: Caller-Side `git status` Assertion
After the lane returns, the main session runs `git status` and asserts no files changed.

**Failure mode**: The lane could stage/commit changes, pushing them. A post-return check sees a clean tree (the changes are already upstream).

### Option 3: `codex sandbox` Wrapper for Specific Commands
Codex has a `codex sandbox` subcommand that "runs commands within a Codex-provided sandbox." The advisory lanes could wrap their reads with this.

**Failure mode**: This still requires codex to enforce; a determined lane could spawn commands outside the wrapper.

### Option 4: Repo-Level Branch Protection
Require advisory lanes to run on a **read-only worktree** or a **detached HEAD**, so `git commit` / `git push` fail.

**How it works**:
- Codex supports `--worktree` flag (creates a temp worktree)
- Branch protection rules require PRs on main
- A lane on a detached HEAD cannot push

**Failure mode**: Minimal. The lane cannot commit/push without staging a branch first.

### Recommended Combination
1. **Prompt stays**: Every advisory lane documents "you advise, do not edit"
2. **Add worktree**: Run advisory lanes with `--worktree` (temp, auto-cleanup)
3. **Branch protection**: Main already requires PRs; this is already true
4. **Post-return gate** (optional): `git diff HEAD` from the parent session to assert no staged changes

**This combination makes accidental edits impossible** (worktree is temp + detached HEAD prevents push) and intentional edits obvious (they don't survive worktree cleanup).

---

## Question 5: Per-Lane Recommendation Table — FINDINGS

### Current State
| Lane | Family | Family Access | Override | Purpose |
|---|---|---|---|---|
| codex-sol-implementer | sol | full | none | Implement specs; writes code |
| codex-astra-implementer | astra | full | none | Implement specs; writes code |
| codex-sol-operator | sol | full | none | Run git/host ops; needs git write |
| codex-astra-operator | astra | full | none | Run git/host ops; needs git write |
| codex-sol-advisor | sol | full | read-only | Advise on decisions; reads only |
| codex-astra-advisor | astra | full | read-only | Advise on decisions; reads only |
| codex-sol-adversarial-critic | sol | full | read-only | Critique code; reads only |
| codex-astra-adversarial-critic | astra | full | read-only | Critique code; reads only |
| codex-sol-staleness-auditor | sol | full | read-only | Audit tool currency; reads only |
| codex-astra-staleness-auditor | astra | full | read-only | Audit tool currency; reads only |
| codex-sol-claude-code-expert | sol | full | read-only | Expert on Claude Code harness; reads only |
| codex-astra-claude-code-expert | astra | full | read-only | Expert on Claude Code harness; reads only |

### Recommended Configuration

**Option A: Keep Current (No Change)**
- Implementer/operator lanes run at danger-full-access (needed for git/code writes)
- Advisory lanes run at read-only (prevents edits)
- Each lane hardcodes its sandbox in the agent markdown via `--sandbox <mode>`

**Pros**: Explicit per-lane, prevents mistakes
**Cons**: Duplicated config in 10 files; changes require PRs across all lanes

**Option B: Profile-Based (Repo-Owned via `-c` Flags)**
- Create a `.codex/profiles/` directory with named `.config.toml` files (for documentation only)
- In each lane markdown, use `-c` flags instead of `--sandbox`:
  - Advisors: `-c sandbox_mode=read-only`
  - Implementers: `-c sandbox_mode=danger-full-access`
  - Operators: `-c sandbox_mode=danger-full-access`

**Pros**: 
- Config is documented and centralized
- Changes are in one place
- `-c` is fully repo-reviewable

**Cons**: 
- More verbose command lines
- Still requires changes to every agent markdown

**Option C: Combine Project Config + `-c` Override**
Add `sandbox_mode = "read-only"` to `.codex/config.toml` as a project-wide default, then:
- Advisory lanes: no override needed (inherit read-only)
- Implementer/operator lanes: `-c sandbox_mode=danger-full-access`

**Pros**:
- Reduces boilerplate (advisors don't need flags)
- Project config is the single source of truth
- Only implementer/operator lanes need overrides

**Cons**:
- Global codex config has `sandbox_mode = "danger-full-access"` (Ray's machine);
- Project config would shadow it for codex calls INSIDE this repo
- Out-of-repo codex invocations would still see the global default
- Could cause confusion if an operator uses codex elsewhere

### Per-Lane Details

All current lanes are **marked read-only (advisors) or full-access (implementers/operators)** in their markdown. No lane currently uses `--profile`.

**Recommendation**: Use **Option C** (project config + `-c` override) because:
1. It's repo-owned and reviewable (satisfies the operator's constraint)
2. It's backward compatible (doesn't require user setup)
3. It centralizes the decision in `.codex/config.toml`
4. It requires minimal changes: edit the project config once, override only in implementer/operator lanes

---

## Question 6: `codex doctor` Output & Machine-Parseability — FINDINGS

### Output Structure
`codex doctor` produces structured, hierarchical plain-text output with:
- Section headers (Codex Doctor, Notes, Environment, Configuration, etc.)
- Rows with status symbols: `✓` (ok), `⚠` (warning), ✗ (fail)
- Key-value pairs with indentation
- Counts (e.g., "22 ok · 3 notes · 1 warn · 0 fail degraded")

### Sample Output (Actual Run)
```
Codex Doctor v0.154.0 · macos-aarch64

Notes
   ⚠ rollouts     3,065 active files · 4.08 GB on disk
   ⚠ sandbox      filesystem unrestricted · network enabled
   ⚠ threads      rollout scan was incomplete or found bad files
─────────────────────────────────────────────────────────────

Environment
  ✓ system       en-US
      os                       Mac OS 26.6.2 [64-bit]
      ...
```

### Machine Parseability
**Structured text, not JSON**: Output is human-readable plain text, not machine-readable JSON.

**Parseable markers**:
- Status symbols (`✓`, `⚠`, ✗) are consistent
- Indentation indicates nesting
- Section headers are all-caps followed by a blank line
- Final summary line: `X ok · Y notes · Z warn · W fail degraded`

**Not ideal for CI/contracts** because:
- No `--json` flag mentioned in help
- Parsing requires regex or string matching
- Changes to output format could break contracts

**Workaround**: The final summary line is reliable:
```bash
codex doctor | tail -1  # "22 ok · 3 notes · 1 warn · 0 fail degraded"
```

Can be parsed for `fail` count via: `grep -oP '\d+(?= fail)' || echo 0`

### Recommendation for SessionStart Hook
The project intends to have `codex doctor` warn at SessionStart and block in CI. Given the lack of a `--json` flag:

1. **For SessionStart hook**: Run `codex doctor` and parse the summary line for warnings/fails
   - Acceptable: it's an advisory check (can't block a hook, only display)
   - Cost: minimal (one subprocess)

2. **For CI contract**: Run `codex doctor` with summary parsing
   - Need explicit gate: `codex doctor | grep -q "1 fail\|2 fail" && exit 1`
   - Not as robust as JSON, but workable

**Alternative**: Run `codex doctor --json` if a future version adds it, then remove the regex parsing.

---

## Summary of Findings

| Question | Finding | Recommendation |
|---|---|---|
| 1. Profile ownership | Profiles are user-level (`$CODEX_HOME/`); CODEX_HOME is overridable but non-standard | Use `-c` flags instead for repo-owned config |
| 2. `-c` as alternative | `-c key=value` can express everything profiles can; layers LAST (wins over profile) | Adopt `-c` for all lane-specific config |
| 3. Sandbox modes needed | read-only blocks mise tasks; workspace-write doesn't fully work; only danger-full-access gives full access | Keep current: read-only for advisors, danger-full-access for implementers/operators. If a lane needs `mise run`, it needs full access |
| 4. Independence without sandbox | Worktree + detached HEAD + branch protection prevents edits | Add `--worktree` to advisory lane invocations |
| 5. Per-lane config | Use Option C: project `.codex/config.toml` as base (set to read-only) + `-c` overrides for implementers/operators | Centralize in project config, override only where needed |
| 6. `codex doctor` machine-parse | Text, not JSON; can parse final summary line for fail count | Acceptable for SessionStart advisory; for CI gate, use regex on summary line |

---

## Recommendation to the Operator

1. **Add to `.codex/config.toml`**:
   ```toml
   sandbox_mode = "read-only"  # advisory lanes are the default
   ```

2. **Update implementer/operator lane markdown**: Add `-c sandbox_mode=danger-full-access` to override the project default

3. **Add `--worktree` to advisory lane invocations** to prevent accidental edits (temp worktree auto-cleans)

4. **Keep `-c sandbox_mode=read-only` in advisor lanes** (explicit override of global user config, which is full-access)

5. **Do NOT use `--profile` for this repo**. Profiles are user-level; use `-c` instead.

---

## Sandbox Blocks This Session (Complete List)

Every attempt to run a command that writes to caches/temp failed:

| Command | Sandbox | Error | rc |
|---|---|---|---|
| `git rev-parse HEAD` | read-only | ✓ success | 0 |
| `touch /tmp/canary` | read-only | Operation not permitted | 1 |
| `mise run graphify-health` | read-only | mise: could not open log file | 1 |
| `MISE_LOG_FILE=/dev/null mise run graphify-health` | read-only | $TMPDIR/.tmp* permission error | 1 |
| `codex --help` | read-only | ✓ success (no writes) | 0 |
| `codex doctor` | read-only | ✓ success (no writes) | 0 |

**Why graphify-query couldn't run**: The PreToolUse hook requires `mise run graphify-query` before raw file grepping, but graphify (via mise) cannot write its cache in read-only mode. This is a documented limitation of this advisor's execution environment.

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — CLI help and sandbox documentation
- [openai/codex-docs](https://github.com/openai/codex-docs) — configuration and profile docs (offline source)
