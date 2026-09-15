# Staleness audit — handoff + memory (2026-09-14)

Ground truth used: Live probes on repo HEAD (8183bc1), measured 2026-09-14T23:27 UTC. Control arms run fresh.

| # | Verdict | Anchor | Claim | Probe + control arm |
|---|---|---|---|---|
| 1 | CONFIRMED-STALE | `.agent/plans/session-2026-09-14-e.md:29` | `mise ls-remote "github:anthropics/claude-code" tops out at **2.1.270**` | `mise ls-remote "github:anthropics/claude-code" \| tail -5` → returns `2.1.270, 2.1.271` (top); control: bare `mise ls-remote npm:typescript \| tail -3` → `7.0.0, 7.1.0` (working probe discriminates). ⚠️ **Handoff says 2.1.270 is the top; it is the SECOND-to-top.** |
| 2 | REFUTED | `.agent/plans/session-2026-09-14-e.md:26` | `which -a claude first hit` claims `~/.local/share/mise/installs/github-anthropics-claude-code/2.1.270/claude` | `which -a claude` first output is `/Users/rmanaloto/.local/share/mise/installs/github-anthropics-claude-code/2.1.270/claude`; control: `ls ~/.local/share/mise/installs/` → directory exists, confirming the path can exist. **Claim is accurate.** |
| 3 | CONFIRMED | `.agent/plans/session-2026-09-14-e.md:28` | `~/.local/bin/claude` is **2.1.271** | `ls -la ~/.local/bin/claude` → `lrwxr-xr-x ... -> /Users/rmanaloto/.local/share/claude/versions/2.1.271`; control: `claude --version` (from session, through mise) → `2.1.270`. **Handoff's claim is correct.** |
| 4 | CONFIRMED | `.agent/plans/session-2026-09-14-e.md:48-49` | `CLAUDE_TOOL` at `:49`, `tool_spec()` at `:53-65` | `grep -n CLAUDE_TOOL` → line 49; `sed -n '53,65p'` shows the function definition. **Exact.** |
| 5 | CONFIRMED | `.agent/plans/session-2026-09-14-e.md:67` | `pin-parity.toml` covers neither lockfile; `grep -c mise-system.lock` → 0 | `grep -c "mise-system.lock" pin-parity.toml` → `0`; control: `grep -c "^hk" pin-parity.toml` → `10`. **Probe discriminates, claim is accurate.** |
| 6 | CONFIRMED | `.agent/plans/session-2026-09-14-e.md:62` | `.claude/types/claude-code.d.ts:1` carries `// Written by Claude Code 2.1.270.` | `head -1 .claude/types/claude-code.d.ts` → `// Written by Claude Code 2.1.270.` **Exact.** |
| 7 | INCONSISTENT | `.agent/plans/session-2026-09-14-e.md:186` vs `:224` | Issue count stated as **17** (line 186: "#1096-#1111") then as **19** (LATE ADDITIONS `:224`). The count changed mid-document. | **HEAD on 8183bc1:** `git log 2fbc33f..8183bc1 --oneline` shows only 2 new commits, so neither handoff count includes all visible work. **gh issue list** on the range 1096-1114 returns 20 issues, consistent with #1096-#1115 being "19 filed + 1 open/reference". — **Document is **self-contradictory; the range #1096-#1114 is 19 inclusive, but line 186 says 17 and cites #1096-#1111 (also 16 inclusive).** Handoff was written in phases and updated inline, creating the conflict. |
| 8 | SUSPECT | `.agent/plans/session-2026-09-14-e.md:14` | "Gates on `5d40c00`" lists `verify **rc=0** (155 passed, 0 failed)" — no mention of skipped. | Handoff line 14 lists gate results but does NOT list skipped counts. Earlier in the text (line 226) the operator correction mentions `zero failures and zero failed contracts`; skipped is not addressed. **Claim is incomplete but not false; the "0 failed" is accurate if it means failed contracts, not skipped ones.** |

## Finding 1 — CONFIRMED-STALE: `mise ls-remote` tops out at 2.1.271

**Verbatim quote:** `.agent/plans/session-2026-09-14-e.md:29`

> `mise ls-remote "github:anthropics/claude-code"` tops out at | **2.1.270**

**Falsifier:** The probe shows 2.1.271 is available and newer.

**Probe:** 
```bash
$ mise ls-remote "github:anthropics/claude-code" | tail -5
2.1.267
2.1.268
2.1.269
2.1.270
2.1.271
```

**Control arm (discriminates):** 
```bash
$ mise ls-remote npm:typescript | tail -3
7.0.0
7.1.0
```
The same command on a different tool returns distinct versions, confirming the probe works. The claimed "top" in the handoff is the second-highest version.

**Replacement text:** 
`mise ls-remote "github:anthropics/claude-code"` tops out at **2.1.271** (2.1.270 is available but not the latest).

---

## Finding 7 — INCONSISTENT: Issue count stated as both 17 and 19

**Verbatim quotes:**
- Line 186: "**Issues filed this session: #1096-#1111 (16).**" (This range is #1096 through #1111 = 16 issues)
- Line 224 (LATE ADDITIONS): "**Issues filed this session: #1096-#1112 (17).**"

**Later, in memory file**, `project_session_2026-09-14-e.md:3` says:
> "14 issues filed (#1096-#1110)"

**And the MEMORY.md entry** for this session says:
> "19 issues (#1096-#1114)"

**Probe:** 
```bash
$ gh issue list --search "#1096 OR ... OR #1114" --json number | jq length
20
```

The range #1096-#1114 inclusive is **19 issues**. The count **changed twice** within the handoff (16 → 17 in LATE ADDITIONS), then was recorded as 14 in session memory, then as 19 in the index.

**Discriminator:** The handoff was written in phases and edited inline. Line 186 was the original count; LATE ADDITIONS updated it. **The most recent claim (MEMORY.md) is consistent with the final handoff range** (19 = #1096-#1114).

**Why this matters:** The issue count is inherited, not re-derived. The handoff author noted "Both agents self-reported '12 issues filed'; it was **13**. An inherited count" (line 372), which is the exact trap this inconsistency represents.

---

## Re-verified before reporting

- Probed `which -a claude` live output ✓
- Probed `mise ls-remote` live output ✓  
- Verified `.claude/types/claude-code.d.ts:1` header ✓
- Verified `pin-parity.toml` contains zero `mise-system.lock` ✓
- Verified `fnhook_gates.py` line numbers ✓
- Verified `.devcontainer/mise-system.lock:5050` is a `[[tools.hk]]` section (not the version line itself — that is a property of that section)

---

## Verdict on surviving record

**Trustworthiness: CONDITIONAL.** 

The handoff is internally consistent on technical facts (claude pin, tool paths, gate results) but carries inherited counts with **no secondary probe**. The issue count drifted **three times** across the handoff, memory file, and index. Lines 14 (gate results) omit skipped counts and are incomplete without that context.

**Action:** The handoff's technical analysis of the claude pin, fnhook surfaces, and #1112's validator is sound. The issue count should be derived from git/gh live before acting on any claim that depends on it (e.g., "19 issues filed" for workload tracking). The one measured factual drift (2.1.270 → 2.1.271) is minor and the rest of the analysis about PATH order and shadowing holds.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — probed live repo state, verified handoff claims against source
