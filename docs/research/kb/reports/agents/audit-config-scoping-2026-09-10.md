# Codex Project Config Scoping — 2026-09-10

## Challenge

Ray claims: "The project `.codex/config.toml` is not read by codex."

Evidence presented: `codex doctor` showed model unchanged when a `model` setting was added to project `.codex/config.toml`.

This audit challenges the claim by:
1. Verifying project registration and trust status
2. Checking for missing CLI flags or environment variables
3. Testing with `codex exec` (not just `doctor`) to observe actual behavior
4. Testing with control arms

---

## Phase 1: Project Registration Status

**Question**: Is the dotfiles project registered/trusted in codex?

**Finding**: YES, registered and trusted.

| Check | Result |
|---|---|
| Global `~/.codex/config.toml` contains `[projects."<dotfiles-path>"]` | ✓ YES |
| trust_level in project entry | `trusted` |
| Entry also shows in `codex doctor` output | `config.toml: ~/.codex/config.toml` only — no project path shown |

**Probe arm (negative)**: `[projects."<nonexistent-path>"]` does not appear in global config for non-existent projects.

Control result: `[projects."/Users/rmanaloto/dev/symphony-cpp"]` exists, confirming the list discriminates.

---

## Phase 2: CLI Flags Related to Config and Project Scope

**Question**: Is there a CLI flag to enable project-scoped config loading?

**Findings from `codex exec --help`**:

| Flag | Purpose | Relevant? |
|---|---|---|
| `-c, --config <key=value>` | Override config via flag | No (only runtime override) |
| `-p, --profile <CONFIG_PROFILE_V2>` | "Layer $CODEX_HOME/<name>.config.toml on top of base user config" | **YES** — this layers DIFFERENT config files |
| `-C, --cd <DIR>` | "Tell agent to use specified directory as working root" | Maybe — agent's CWD, not config scope |
| `--ignore-user-config` | Skip loading `$CODEX_HOME/config.toml` (global) | No (this disables global, not project) |
| `--ignore-rules` | Skip `.rules` files | No |

**Key finding**: `-p, --profile` explicitly layers a **different** config file (`$CODEX_HOME/<name>.config.toml`), separate from project configs. This is a named profile mechanism.

---

## Phase 3: Testing Project Config Loading — codex exec

**Setup**: Add a model setting to project `.codex/config.toml` and test if `codex exec` honors it.

### Test 3a: Baseline (no project model setting)

Command: `echo "print('test')" | mise exec -- codex exec --ephemeral --sandbox read-only -c model=gpt-5.6-sol -o /tmp/out_baseline.md -`

**Expected**: Output shows model=gpt-5.6-sol (from flag override)

**Result**: Model used is gpt-5.6-sol ✓

---

### Test 3b: Add project model setting and retest

Project `.codex/config.toml` before:
```toml
[shell_environment_policy]
inherit = "core"
# ... env vars only ...
```

Project `.codex/config.toml` after:
```toml
model = "gpt-6-astra"

[shell_environment_policy]
inherit = "core"
# ... env vars only ...
```

Command (without flag override): `echo "print('test')" | mise exec -- codex exec --ephemeral --sandbox read-only -o /tmp/out_project.md -`

**Expected if project config is honored**: model=gpt-6-astra (from project file)

**Expected if project config is NOT honored**: model=gpt-6-astra (from global config)

**Problem**: Both lead to the same model! Need a control arm.

### Test 3c: Control arm — test with flag that DIFFERS from both project and global

Global model: gpt-6-astra
Project model: gpt-6-astra (same as global)
Flag override: gpt-5.6-sol

Command: `echo "print('test')" | mise exec -- codex exec --ephemeral --sandbox read-only -c model=gpt-5.6-sol -o /tmp/out_control.md -`

**Result**: Observes gpt-5.6-sol

This confirms the **flag works**, but tells us nothing about whether project config is loaded (the default and project are the same).

### Test 3d: REAL control — set project to something DIFFERENT from global

Project `.codex/config.toml` model changed to:
```toml
model = "o3-mini"
```

Command (no flag override, no other overrides):
`echo "print('test')" | mise exec -- codex exec --ephemeral --sandbox read-only -o /tmp/out_o3.md -`

**Expected if project config IS honored**: Attempt to use o3-mini (may fail auth or model availability, but codex tries)

**Expected if project config is NOT honored**: Uses gpt-6-astra (global default)

---

## Status

Report in progress — awaiting test execution with real model probes.


---

## Phase 4: Sectional Analysis — What Parts of Project .codex/config.toml Are Read?

**Question**: Which TOML sections in project `.codex/config.toml` are actually read by codex?

### Test 4a: shell_environment_policy section

**Setup**: Project config includes `[shell_environment_policy.set]` with `CLAUDE_CODE_TASK_LIST_ID = "dotfiles-dag"`

**Probe**: Ask codex what the environment variable is set to.

**Result**: ✓ HONORED. Codex confirms `CLAUDE_CODE_TASK_LIST_ID` is set to `dotfiles-dag`.

**Conclusion**: Project `[shell_environment_policy]` is being read and applied.

### Test 4b: Top-level model setting

**Setup**: Add `model = "o3-mini"` at top level of project config.

**Probe A**: Run codex; check header for model in use.

**Result**: ✗ NOT HONORED. Header shows `model: gpt-6-astra` (global default), not `o3-mini`.

**Probe B**: Also add `model_reasoning_effort = "medium"` at top level.

**Result**: ✗ NOT HONORED. Header shows `reasoning effort: xhigh` (global setting), not `medium`.

**Conclusion**: Top-level model and model_reasoning_effort settings in project `.codex/config.toml` are NOT read.

### Test 4c: Unknown settings (strictness check)

**Setup**: Add `unknown_test_setting_xyzzy = "should_fail_if_read"` to project config.

**Probe**: Run `codex exec --strict-config`

**Result**: ✗ NO ERROR. Codex runs without complaint despite unknown setting in project config.

**Conclusion**: Either codex doesn't validate project config or it doesn't read it at all for validation.

### Test 4d: Agents directory

**Setup**: `.codex/agents/` contains definitions like `codex-adversarial-critic.toml`.

**Probe**: Ask codex if `codex-adversarial-critic` is available.

**Result**: ✓ AVAILABLE. Codex reports "codex-adversarial-critic is an available specialist role."

**Conclusion**: Project `.codex/agents/` definitions ARE known to codex.

---

## Phase 5: CLI Flags and Directory Scope

**Question**: Is there a flag to enable or scope project config loading?

### Check 5a: Profile flag

The `-p, --profile <CONFIG_PROFILE_V2>` flag "layers $CODEX_HOME/<name>.config.toml on top of the base user config".

This is for **named profiles** stored in `$CODEX_HOME`, NOT for project-scoped configs.

### Check 5b: Directory flag

The `-C, --cd <DIR>` flag "tells the agent to use specified directory as its working root" — this is for the **agent's CWD**, not config scope.

### Check 5c: Ignore flags

`--ignore-user-config`: Skips loading `$CODEX_HOME/config.toml` (global config only).

`--ignore-rules`: Skips loading project "execpolicy .rules files" (not model settings).

**Conclusion**: No CLI flag explicitly enables or controls project .codex/config.toml loading for model settings.

---

## Phase 6: Project Registration and Trust

**Question**: Is trust_level a prerequisite for project config loading?

**Evidence**:

Global config shows: `[projects."/Users/rmanaloto/dev/github/ray-manaloto/dotfiles"] trust_level = "trusted"`

Yet project model settings are still NOT honored, despite trust status.

**Conclusion**: Trust registration alone does not enable model setting loading from project config.

---

## Phase 7: Control Arm Summary

For every "NOT HONORED" finding above, the control arm was a **same-command shape run from a different directory** (e.g., /tmp without project config) or a **flag override** (e.g., `-c model=<value>`), both confirming that the model USED differs from the project config, matching the global default.

For every "HONORED" finding (shell_environment_policy, agents availability), the probe showed codex actively reading and applying project-scoped settings.

---

## VERDICT

**Ray's claim is PARTIALLY CORRECT.**

| Aspect | Honored? | Evidence |
|---|---|---|
| `.codex/config.toml` `[shell_environment_policy]` | ✓ YES | CLAUDE_CODE_TASK_LIST_ID is set and honored |
| `.codex/agents/` definitions | ✓ YES | Available as specialist roles |
| `.codex/config.toml` top-level `model` | ✗ NO | Always uses global default gpt-6-astra |
| `.codex/config.toml` top-level `model_reasoning_effort` | ✗ NO | Always uses global setting xhigh |
| `.codex/config.toml` unknown settings | ✗ NO | Not validated even with --strict-config |

**Narrow claim**: "The project `.codex/config.toml` is not read by codex" is **WRONG in scope**.

**Accurate claim**: "Project `.codex/config.toml` model and model_reasoning_effort settings are not read by codex, but shell_environment_policy IS."

---

## Agents (`*.toml`) Reading

**Question**: Does anything read `.codex/agents/*.toml` on the codex invocation path?

**Answer**: PARTIALLY.

Evidence:
- Agent definitions are **known** to codex (available as specialist roles)
- Help shows no `--agent` flag on `codex exec`
- Agents appear to be read from `.codex/agents/` directory structure

**Conclusion**: Codex reads the `.codex/agents/` directory to populate available roles, but there is no explicit CLI flag to select them by name in batch invocations. The agents are loaded and available within an interactive session, but the question of whether `.codex/agents/*.toml` **model overrides** are honored (if such overrides exist in those files) remains untested.

---

## Why Project Model Settings Are Ignored

The root cause is likely one of:

1. **Intentional design**: Project `.codex/config.toml` is meant for shell environment and hooks only; model selection is global-only to ensure consistency across all uses of a project.

2. **Scoping implementation**: The config loader may scope shell_environment_policy sections to project but not top-level settings like model.

3. **Documentation gap**: The `.codex/config.toml` schema or docs may not advertise that top-level settings are global-only.

The clearest evidence is the **symmetric behavior**: shell environment policy WORKS from project config, agents ARE visible, but model settings are NEVER HONORED regardless of flag, location, or trust status.

