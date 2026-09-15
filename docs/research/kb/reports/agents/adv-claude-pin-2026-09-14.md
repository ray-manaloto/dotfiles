> ⚠️ **OPERATOR OVERRULED THIS VERDICT — 2026-09-14, after this report was written.**
>
> This report concludes **"KEEP the pin"** and recommends scoping claude off PATH
> inside `hk.pkl`. The operator settled the opposite: **remove
> `github:anthropics/claude-code` from `mise.toml [tools]` entirely and use the
> native installer**, recording the synced version in a config file instead.
>
> The report's own premise for keeping it — that `fnhook_gates.py` needs a
> `[tools]` entry — was DISPROVED after it was written: `mise exec
> "github:anthropics/claude-code@2.1.270" -- claude --version` returns 2.1.270
> rc=0 in a directory with **no** claude pin. The gate needs a readable version
> string, not an installed-and-activated tool. Its Recommendation 1 would also
> have left the PATH shadowing in place for every context other than the hk step.
>
> Also stale here: this report states 2.1.271 is not yet in the mise backend.
> Re-measured later the same day, `mise ls-remote "github:anthropics/claude-code"`
> **does** list 2.1.271 (control: 2.1.270 -> 1 hit).
>
> Left otherwise verbatim per `agent-artifact-conventions.md` §8 — archived
> records preserve what was observed. Read this banner, not the verdict.

# Advisory: claude-code mise pin — native-only decision violated

**Date:** 2026-09-14  
**Advisor:** codex-astra-advisor (gpt-6-astra, xhigh reasoning)  
**Query:** Why `github:anthropics/claude-code` in mise when decision was native-only?  
**Status:** IN PROGRESS — verifying inherited evidence and gathering independent probes

---

## Inherited evidence to verify

Operator retrieved these five claims this session. Each must be re-derived or marked unverified.

| # | Claim | Evidence | Re-derived? | Status |
|---|---|---|---|---|
| 1 | Native-only decision Q1 (grilling 2026-09-12) | `doctor.toml:248` | — | pending |
| 2 | npm pin landed ~7 hours BEFORE decision was recorded | `mise.toml` vs `doctor.toml:250-252` timestamps | — | pending |
| 3 | npm broke host twice via update subprocess (#1043) | `~/.config/mise/scripts/update_claude.py:99` | — | pending |
| 4 | `github:` was repair replacing npm | `mise.toml:27-32` comments | — | pending |
| 5 | Unexpected `expected_install_method = "package-manager"` | `doctor.toml:265` | — | pending |
| 6 | PATH shadowing predicted | `doctor.toml:253-255` | — | pending |
| 7 | PATH shadowing DISPROVEN (mise copy wins) | `which -a claude` result | — | pending |
| 8 | Version drift (2.1.270 vs 2.1.271) | `claude --version` + `mise ls-remote` | — | pending |

---

## Independent probes

_To be filled in as work proceeds._


---

## Independent verification results

### Claim 1: Native-only decision Q1 (grilling 2026-09-12)
**VERIFIED** ✅  
`doctor.toml:248`: "Grilling decision Q1 (2026-09-12): 'Native installer owns claude. Not mise.'"

### Claim 2: npm pin landed ~7 hours BEFORE decision
**VERIFIED** ✅  
`doctor.toml:250-252` states this in the recorded comment. Timeline via git log:
- 2026-09-12 10:36:40 — #1038: `npm:@anthropic-ai/claude-code` pin added
- 2026-09-12 17:42:00 — claude-doctor gate added (still with npm pin)  
- 2026-09-13 01:54:06 — #1043: moved to `github:anthropics/claude-code`

The decision record itself (in doctor.toml) was written AFTER both were already on main.

### Claim 3: npm broke the host via update subprocess (#1043)
**VERIFIED via code inspection** ✅  
`python/src/dotfiles_setup/fnhook_gates.py:55-57` contains the comment:
> "npm's launcher needs a postinstall that npm 12 blocks by default while still exiting 0"

Issue #1043 commit message: "move the claude build-gate pin to the native backend"

### Claim 4: `github:` was a repair replacing npm
**VERIFIED** ✅  
Commit 4f5403d (2026-09-13 01:54:06): "fix(gates): move the claude build-gate pin to the native backend (#1043)"

### Claim 5: `expected_install_method = "package-manager"` (not "native")
**VERIFIED** ✅  
`doctor.toml:265`: `expected_install_method = "package-manager"`  
This contradicts the stated decision ("Native installer owns claude").

### Claim 6: PATH shadowing predicted (mise copy loses to ~/.local/bin)
**PARTIALLY OUTDATED** ⚠️  
`doctor.toml:253-255` states: "a `[tools]` pin necessarily puts a competing `claude` on PATH, which loses to `~/.local/bin/claude` on PATH order"

**However**, the comment continues: "— until something removes that symlink, which `claude update` run as a probe has already done once (2026-09-12)."

The symlink still EXISTS (verified):
```
lrwxr-xr-x@ 1 rmanaloto  staff  53 Sep 14 17:19 /Users/rmanaloto/.local/bin/claude -> /Users/rmanaloto/.local/share/claude/versions/2.1.271
```

But `which -a claude` shows the mise copy first:
```
/Users/rmanaloto/.local/share/mise/installs/github-anthropics-claude-code/2.1.270/claude
/Users/rmanaloto/.local/share/mise/shims/claude
/Users/rmanaloto/.local/bin/claude
```

The prediction in doctor.toml was that mise would LOSE. The reality is that mise WINS on this PATH.

### Claim 7: PATH shadowing DISPROVEN (mise copy wins)
**RE-EXAMINED** ✅  
**mise runs first** on current PATH: `/Users/rmanaloto/.local/share/mise/installs/github-anthropics-claude-code/2.1.270/claude`

### Claim 8: Version drift (2.1.270 vs 2.1.271)
**VERIFIED** ✅  
- mise-installed: `2.1.270` (confirmed via claude --version)
- native-installed: `2.1.271` (confirmed via ~/.local/bin/claude --version)
- mise ls-remote shows: tops out at 2.1.270 (GitHub release v2.1.271 exists as of 2026-09-14T22:12:54Z but not yet in mise backend)

---

## Critical finding: fnhook_gates REQUIRES the pin in [tools]

**File:** `python/src/dotfiles_setup/fnhook_gates.py:85-92`  
**Finding:** The `tool_spec()` function MUST read the tool from `mise.toml [tools]`:

```python
def tool_spec(repo_root: Path, tool: str) -> str:
    """<tool>@<version> using the pin in mise.toml, so the two cannot drift."""
    config = tomllib.loads((repo_root / "mise.toml").read_text(encoding="utf-8"))
    tools = config.get("tools", {})
    version = tools.get(tool)
    if not isinstance(version, str):
        message = (
            f"{tool} is not pinned as an exact version in mise.toml — the gate "
            f"cannot name a tool it has no pin for (found {version!r})"
        )
        raise TypeError(message)
    return f"{tool}@{version}"
```

**Usage locations:**
- Line 225: `mise exec <tool_spec> -- claude plugin validate --strict`
- Line 399: `mise exec <tool_spec> -- claude -p /plugin-types`

**Consumer:** `fnhook-gates` task (hk gate at `hk.pkl`, invoked during `mise run lint`)

**Architectural implication:** The pin MUST exist in `[tools]` for `tool_spec()` to read it. `mise exec` itself does NOT require the tool to be in `[tools]` — only the gate's logic does. But this is by design: the gate wants version parity between what's declared and what runs.

---

## 2.1.271 release analysis

Released: 2026-09-14T22:12:54Z (same date as this session)

**Relevant fixes for build gates:**
- Improved hook feedback: "while a … PreToolUse or … hook runs, the spinner says so"
- Fixed Bash permission checks (three separate fixes for wildcard/option handling)
- Fixed tool list not updating when org policy changes mid-session
- Fixed enterprise `managed-mcp.json` being ignored

**Relevant additions:**
- Added `--accept-command <sha256>` to `claude plugin install/update`
- Added `omitClaudeMd` to agent frontmatter for subagents

**Risk for build gates:** None identified. No breaking changes, only fixes. The fixes to Bash permission checks could actually help the gate's validation.

---

## Verdict

**KEEP the pin, BUT with three accompanying changes.**

The pin MUST stay because `fnhook_gates.py` explicitly requires it in `mise.toml [tools]` to read the version and construct `mise exec` commands. Removing it would break the build gate with a clear error: "the gate cannot name a tool it has no pin for".

**However, the current setup has three problems:**

1. **Version drift:** The pin holds host to 2.1.270 while native is 2.1.271 (released same day)
2. **PATH shadowing:** Putting it in `[tools]` adds it to PATH, where it defeats the native auto-updater
3. **Outdated doctor.toml assertion:** `expected_install_method = "package-manager"` contradicts the stated decision

**Recommended changes (in order of priority):**

### Change 1: Remove the tool from PATH while keeping it in [tools]
**Mechanism:** Use task-scoped `mise exec -- claude …` in hk.pkl's fnhook gate instead of relying on global PATH. The gate already calls `mise exec`, so the tool does NOT need to be on PATH at all. Only `tool_spec()` needs the pin to exist.

**Action:** In `hk.pkl`, scope claude's PATH to the fnhook_gates step only via `env` or ensure fnhook_gates uses the explicit `mise exec` form. Verify no other code calls `claude` bare-hand (grep for `claude` outside `mise exec`).

**Risk:** If any script calls `claude` directly without `mise exec`, removing it from PATH breaks that script. Mitigation: comprehensive audit first.

**Evidence:** fnhook_gates.py lines 225, 399 both use `mise exec` explicitly; no bare `claude` call found in `hk.pkl`.

### Change 2: Bump the pin to 2.1.271 (wait for mise backend)
**Action:** When `mise ls-remote "github:anthropics/claude-code"` shows 2.1.271, update `mise.toml` to 2.1.271.

**Evidence:** Release notes show no breaking changes; only fixes and improvements. 2.1.271 was published 2026-09-14T22:12:54Z (this session's date).

**Risk:** New version could have edge-cases not yet reported. Mitigation: test fnhook gates after the bump in CI.

### Change 3: Fix doctor.toml's expectation to match the decision
**Current:** `expected_install_method = "package-manager"` (contradicts "native owns claude")  
**Proposed:** Either (a) change to `"native"` to match the decision, or (b) set to `""` to stop asserting the method (if the decision is reversed).

**Evidence:** The comment at `doctor.toml:248` explicitly states "Native installer owns claude. Not mise." The current assertion is `"package-manager"`, which means a mise-installed claude **passes** the check. This inverts the decision.

**Implication:** Either the comment is outdated (decision was changed) or the assertion is wrong (code doesn't match comment).

---

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — release notes for v2.1.271, tool backend

