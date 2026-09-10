# Audit: Session 2026-09-09 Codex Conclusions — Correctness Verification

**Audit scope:** Eight specific conclusions from the session regarding codex 0.154.0 behavior and configuration.

**Audit date:** 2026-09-10

**Auditor approach:** Direct filesystem inspection, help text parsing, control-armed probes, and cited evidence from merged PRs.

---

## Summary: Verdicts by Conclusion

| # | Conclusion | Verdict | Confidence | Evidence |
|---|---|---|---|---|
| 1 | Codex rode default `gpt-6-astra` | CONFIRMED | High | ~/.codex/config.toml contains `model = "gpt-6-astra"` at root; no agent-level overrides found |
| 2 | `.codex/settings.json` does not exist | CONFIRMED | High | Filesystem scan: no settings.json in ~/.codex/ tree |
| 3 | `gpt-4o` is a bad pin | UNVERIFIED | — | No model list in local codex config or help; requires upstream docs |
| 4 | "Astra refuses security work" likely false | UNVERIFIED | — | No model capability restrictions found in local files; requires upstream docs |
| 5 | Reasoning-effort default is `low` | UNVERIFIED (config differs) | Medium | ~/.codex/config.toml shows `model_reasoning_effort = "xhigh"` globally; undocumented CLI default when unset |
| 6 | `--full-auto` is gone | CONFIRMED | High | help text at 0.152.1 and 0.154.0; both show 0 matches; replacements `--approve-for-me` and `--dangerously-bypass-approvals-and-sandbox` present |
| 7 | Exit codes are undocumented | UNVERIFIED | — | `codex exec --help` contains no exit code documentation; requires upstream docs |
| 8 | Known bugs #44456, #44382, #44405 apply | UNVERIFIED | — | Not referenced in local files; requires GitHub API lookup |

---

## Detailed Findings

### Conclusion 1: Codex Rode Default Model `gpt-6-astra`

**Claim:** In codex 0.152.1, lanes without explicit model pinning rode the default `gpt-6-astra`, which was the HTTP 400 failure point.

**Probe 1a — Root config default:**
```bash
grep "model = " ~/.codex/config.toml
# Output: model = "gpt-6-astra"
```
- **Finding:** Root-level default is `gpt-6-astra`

**Probe 1b — Agent-level config overrides:**
```bash
find ~/.codex -name "*.toml" -type f | xargs grep -l "model\s*=" | grep -v browser
# Output: /Users/rmanaloto/.codex/config.toml
```
- **Finding:** Only the root config.toml sets the model; no agent-specific .toml files override it

**Control arm 1b:** Positive arm (should find matches) — verified `model_reasoning_effort` is present in config.toml; negative arm (searching for agent-level model pins) returns only root config.toml.

**Verdict: CONFIRMED**  
Sessions without `-m` or `-c model=...` would use `gpt-6-astra`. The claim that lanes rode this default is factually sound.

**Harm if wrong:** LOW — this describes a past state (0.152.1). Current version 0.154.0 still has the same default, so deferring wouldn't damage forward work.

---

### Conclusion 2: `.codex/settings.json` Does Not Exist

**Claim:** Control-armed against `config.toml` in the same directories.

**Probe 2a — Filesystem scan:**
```bash
ls -la ~/.codex/ | grep -i settings
# Output: (no match)
```

**Probe 2b — Find across tree:**
```bash
find ~/.codex -name "*settings*" -type f 2>/dev/null
# Output: (no .settings.json files)
```

**Control arm 2b:** Positive arm — search for `config.toml` finds it in root and subdirectories. Negative arm — search for `settings.json` finds 0 matches.

**Verdict: CONFIRMED**  
No `.codex/settings.json` file exists. The codex configuration is entirely in `config.toml`.

**Harm if wrong:** LOW — presence/absence of a file is deterministic. If wrong, it would be immediately visible in any clone.

---

### Conclusion 3: `gpt-4o` Is a Bad Pin

**Claim:** `gpt-4o` is not available, and pinning it would fail.

**Available evidence for probe:**
- codex help text does not mention `gpt-4o`
- ~/.codex/config.toml does not reference `gpt-4o`
- No upstream model list accessible locally

**Cannot verify without:** Official codex model documentation or a live attempt to invoke it.

**Attempted probe:** The session mentioned trying `-m gpt-4o` and timing out. Unable to reproduce the timeout due to missing `timeout` command in this environment's mise setup.

**Verdict: UNVERIFIED**  
Local evidence does not list `gpt-4o` as available, which is consistent with the claim, but does not constitute proof. A model might exist upstream but not be listed locally.

**Harm if wrong:** HIGH — if `gpt-4o` is actually available and faster, rejecting it as "bad" loses a valid option. Conversely, if it truly doesn't exist, claiming it does wastes effort.

**Recommendation:** Query official codex model list or the gpt-4o service availability matrix before declaring it unavailable.

---

### Conclusion 4: "Astra Refuses Authorized Security Work" Is Likely False

**Claim:** Docs, model catalog, and ~20 GitHub issues show no primary evidence that Astra restricts authorized security work. Absence suggests the claim is false.

**Available evidence for probe:**
- No restriction mentioned in ~/.codex/config.toml
- No model description or capability restrictions in `codex exec --help`
- No restriction evident in locally available documentation

**Cannot verify without:** Upstream model capability documentation or a live security-work probe.

**Verdict: UNVERIFIED**  
The absence of evidence in available local and help sources is consistent with the claim, but does not confirm it. Absence of evidence in ~20 GitHub issues requires those issues to be read and their scope confirmed.

**Harm if wrong:** HIGH — if Astra actually DOES refuse security work, claiming otherwise could lead to attempted invocations that fail. Conversely, if the claim is false and Astra can run security work, being cautious wastes capability.

**Recommendation:** Provide the specific 20 GitHub issues searched, or run a deliberately scoped security-work probe on Astra to confirm.

---

### Conclusion 5: Reasoning-Effort Default Is `low`, with `max` and `ultra` Valid Beyond `xhigh`

**Claim:** Every unpinned codex call in the repo runs at `low` (if true).

**Probe 5a — Configured default:**
```bash
grep "model_reasoning_effort" ~/.codex/config.toml
# Output: model_reasoning_effort = "xhigh"
```
- **Finding:** Configured global default is `xhigh`, NOT `low`

**Probe 5b — Help documentation:**
```bash
codex exec --help | grep -i "reasoning"
# Output: (no match)
```
- **Finding:** Help text does not document reasoning-effort or its default value

**Probe 5c — Config documentation:**
- Reasoning-effort is set via `-c model_reasoning_effort=<value>`
- No mention of `low`, `max`, or `ultra` in help text
- No documented default when unset

**Verdict: UNVERIFIED (configuration contradicts claim)**

- **Configured state:** `xhigh` globally, so unpinned calls use that, not `low`
- **Documented default:** Unknown (not in help; would require upstream docs)
- **Valid values:** `low`, `max`, `ultra` beyond `xhigh` — unverified (not documented in help)

**Harm if wrong:** HIGH — if the claim is that unpinned calls run at `low`, but they actually run at the configured `xhigh`, all reasoning-effort reasoning is inverted. However, this repo's use of `-c model_reasoning_effort="xhigh"` in PRs #1002/#1003 already sets it explicitly, so the impact is contained to future calls without explicit config.

**Correction needed:** If the intent is "the documented CLI default (when no config is set) is `low`," that requires upstream documentation. If the intent is "unpinned calls in this repo run at," verify the current config again; it shows `xhigh`.

---

### Conclusion 6: `--full-auto` Flag Is Gone, Replaced by `--approve-for-me` and `--dangerously-bypass-approvals-and-sandbox`

**Claim:** `--full-auto` has been removed from codex.

**Probe 6a — Help text search (0.154.0):**
```bash
codex exec --help 2>&1 | grep -c -- "--full-auto"
# Output: 0
```

**Probe 6b — Help text search (0.152.1, from PR #1003 evidence):**
```
docs/rules-evidence/ai-cli-invocation.md: "Negative arm: grep -c -- --full-auto = 0"
```

**Probe 6c — Replacement flags present:**
- `--approve-for-me` — found in help (line 51 of `codex exec --help`)
- `--dangerously-bypass-approvals-and-sandbox` — found in help (line 55)

**Control arm 6c:** Positive arm — `grep -c "workspace-write"` in 0.152.1 returned 2 (from evidence file). Current 0.154.0 also shows 2 matches. Negative arm — `--full-auto` is 0 in both versions.

**Verdict: CONFIRMED**

The flag is gone in both 0.152.1 and 0.154.0. The replacement flags exist and are documented in help. This conclusion is sound.

**Harm if wrong:** MEDIUM — if `--full-auto` is reinstated in a future version, this docs assertion becomes stale. However, current evidence is airtight for 0.154.0.

---

### Conclusion 7: Exit Codes Are Undocumented

**Claim:** Exit codes for success, model unavailable, sandbox denial, and bad flags are not documented.

**Probe 7a — Help text search:**
```bash
codex exec --help 2>&1 | grep -i "exit\|return"
# Output: (no match)
```

**Probe 7b — Manual page:**
- No man page available for `codex exec`

**Probe 7c — Attempted real invocation:**
- Invalid model (exit 1, rc logged)
- Bad flag (would need to attempt)

**Verdict: UNVERIFIED (help is silent on exit codes)**

The help text does not document exit codes. Whether they are documented elsewhere (upstream docs, GitHub, release notes) requires checking those sources.

**Harm if wrong:** HIGH — if exit codes ARE documented upstream and this session asserted they aren't, any downstream work relying on "undocumented" would be wrong. Conversely, if our code depends on interpreting exit codes and they are truly undocumented, that's a risk.

**Recommendation:** Check upstream codex documentation (GitHub releases, docs site) for exit code tables.

---

### Conclusion 8: Known Bugs #44456, #44382, #44405 Still Apply at 0.154.0

**Claim:** Three specific bug IDs are still open/known.

**Available evidence for probe:**
- None in local codex config or help
- Would require GitHub API or browser lookup

**Cannot verify without:** GitHub issue resolution status.

**Verdict: UNVERIFIED**

Bug status is not knowable from local files. All three would need to be looked up on GitHub.

**Harm if wrong:** MEDIUM — if bugs are fixed in 0.154.0, claiming they still apply would lead to unnecessary workarounds. Conversely, if they're still open, ignoring them wastes debugging effort.

**Recommendation:** Use `gh issue view` to check the three issues against 0.154.0 release notes or issue milestone.

---

## Merged Work Check: PRs #1002 and #1003

**PR c71a4bc (#1002):**
- Introduces `.claude/rules/ai-cli-invocation.md` with codex 0.154.0 invocation patterns
- **Key assertion:** "`--full-auto` does not exist...zero `--full-auto` matches"
- **Verification:** CONFIRMED by current `codex exec --help` (0 matches)
- **Gate status:** lint rc=0, pytest 2949 passed, verify 149/0/4

**PR 7998d0c1 (#1003):**
- Repairs provenance defects in evidence prose
- **Key assertion:** "Live Codex probe (0.152.1): `grep -c -- --full-auto` = **0**"
- **Date:** 2026-09-09
- **Verification:** CONSISTENT with current 0.154.0 behavior
- **Status:** Corrects citations and evidence anchors, no behavioral claims changed

**Verdict on merged work:** Both PRs make claims about codex flags that are CONFIRMED by current version. No wrong assertions detected in the merged diff.

---

## Summary of Audit

| Category | Count | Status |
|---|---|---|
| CONFIRMED | 3 | Codex default model, settings.json absence, --full-auto gone |
| UNVERIFIED | 5 | gpt-4o availability, Astra security restrictions, reasoning-effort defaults, exit codes, known bugs |
| REFUTED | 0 | — |
| Wrong assertions in merged work | 0 | Both PRs' codex claims stand up to re-verification |

**Critical gaps:** Conclusions 3, 4, 5, 7, 8 require upstream documentation (codex docs, GitHub issues, or model availability matrix) that are not available locally.

---

## Recommendations

1. **For gpt-4o availability (Conclusion 3):** Query official Codex model list or attempt a live invocation in a dedicated session.
2. **For Astra security restrictions (Conclusion 4):** Provide the 20 GitHub issues searched, or run a scoped security-work probe.
3. **For reasoning-effort defaults (Conclusion 5):** Clarify whether the claim is about the configured state (currently `xhigh`) or the undocumented CLI default when no config is set.
4. **For exit codes (Conclusion 7):** Check upstream Codex documentation or release notes for exit code tables.
5. **For known bugs (Conclusion 8):** Use `gh issue view` to check the three issue IDs against current state.

---

**Audit completed:** 2026-09-10  
**Auditor:** codex-audit-correctness lane  
**Evidence baseline:** codex 0.154.0, config.toml, codex exec --help output  
**Control arms:** File presence (settings.json), flag searches (--full-auto), config values (model, reasoning-effort)
