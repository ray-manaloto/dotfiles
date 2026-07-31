# Spec-axis code review — `docs/specs/research-nudge-hooks.md` (2026-07-31)

Persisted verbatim per `.claude/rules/agent-report-persistence.md`. Produced by the Spec axis of
`/mattpocock-skills:code-review`, fixed point `origin/main` (bc4876a), two-dot.

> **Sibling axis note:** the Standards axis of the same review **failed to deliver** — it signalled
> idle twice without a report and did not answer a direct request for one. That axis was performed
> inline by the main session instead; its findings are in Appendix D of the spec (D5) and in
> `.agent/notepad.md` under the 2026-07-31-c heading. Recorded so the coverage gap is visible rather
> than implied.

---

## Spec axis — `docs/specs/research-nudge-hooks.md` (+62/−2 vs base `78aafc4`)

### (b) Scope creep — CLEAN
Session diff is `+62/−2`; the only deletions are the two "findings are not yet verified" banner lines. Tier sections untouched → *"Keep as-is under the NO-SHIP banner"* honoured. Appendix C characterises the redesign, it does not design it → *"Ticket it, stop there"* honoured. #449 faithfully mirrors Appendix C; no overstatement I found.

### (a) Missing / partial — 2

**A1. Appendix B's F4 confirm column has no result in Appendix C.** Spec line: *"Also verify the 'wrapping loses nothing' claim — measured against the HUD's real output, which does render usage and cost."* Appendix C's F4 row reports only path-scoping + concurrency. Codex's F4 explicitly says *"The assertion that wrapping costs and loses nothing is unsupported"* — that half is never answered.

**A2. F1's confirm column asked for a trace, C substitutes a read-back.** Spec line: *"Trace the two real misses: would any tier have stopped the decision from resolving?"* C's evidence is *"Read-back: 1.1/1.2 emit additionalContext…"* — the document, not the misses. Conclusion is likely right; the asked-for check wasn't run.

F2's pushback (*"the one finding to push back on"*) **was** properly resolved with measurement. F3, F5 covered both halves.

### (c) Implementation wrong — 1 hard, 1 soft

**C1. "peaking at 4" does NOT reproduce.** Doc/issue: *"60 of 91 hours (66%) had ≥2 sessions live, peaking at 4."* Re-derived over `~/.claude/projects/*/*.jsonl`, hour-buckets containing a real message timestamp, 7-day window:
```
transcripts in window: 249 | hours ≥1: 88 | hours ≥2: 61 (69%) | peak: 154
distribution: {1:27, 2:31, 3:13, 4:5, 5:4, 6:3, 9:1, 10:1, 17:1, 20:1, 154:1}
```
Hours/percentage reproduce (61/88 = 69% vs 60/91 = 66%; drift = sliding window). **Peak does not** — 11 hours exceed 4, top hour is `2026-07-28T02:00Z` at 154 files. Likely cause: teammate transcripts are also `<uuid>.jsonl`, so parallel subagents inflate a session count. Either way the doc states no method, so the figure isn't reproducible as written — the exact defect [[probes-need-a-control-arm]] rule 6 names. Conclusion ("collision is the normal case") is unaffected and if anything strengthened.

**C2. F3(b)'s control arm doesn't arm the component depended on.** Doc: *"control: 28 filenames match the date convention, so the probe sees naming patterns."* The claim under test is a **ticket-number** matcher; a date matcher firing proves regex works, not that ticket detection discriminates. I also could not reproduce 28 from any single corpus (`reports/` → 5 dated files; `docs/research/**` → 6; `runs/` dirs → 25; 25+3 = 28 mixes dirs and files across two trees).

### Reproduced clean (both arms)
- **hooks.md:1551** — verbatim `| \`permissionDecisionReason\` | For "allow" and "ask", shown to the user but not Claude.` Control: `additionalContext`→40, bogus token→0. ✅
- **16 files / 1 with a ticket** — `ls docs/research/kb/reports/agents/ | wc -l` → 16; only `concurrency-sweep-433.md` carries a ticket. ✅
- **0 subagents in both miss sessions** — `6b4602f4`: Agent=0, subagent_type=0, control Bash=132; `d4299a7a`: 0/0/48. ✅
- **239 vs 241 project-wide** — I get 241 across 181 transcripts; +2 is this review's own two axes. Reproduces. ✅
- **`guard-fail-open.log` absent** — `ls` rc=1 with control `ls -d ~/.local/state/dotfiles` rc=0 (8 sibling files listed), so the probe can see. ✅
- F5 arithmetic self-consistent: 1978/30000 = 6.6%, 30000/1978 = 15.2×.

**Recommendation:** fix or method-annotate the "peaking at 4" figure in both the spec and #449; add the F4 wrapping-claim result or say explicitly it was not run.

---

## Disposition by the main session

| Finding | Action |
|---|---|
| C1 "peaking at 4" | **CONFIRMED and fixed.** Independently re-derived: true max 154, 12 hours exceed 4. Root cause was a display bound in the original probe (`sorted(multi)[-8:]`), not the agent's subagent-inflation hypothesis — though that hypothesis is *also* partly right about what the count conflates. Corrected in the spec (Appendix D1) and in issue #449. |
| C2 control arm | **CONFIRMED and fixed.** Independently reproduced: `reports/agents/` alone has 3 dated filenames, not 28; the 28 spanned two trees. The "wrong component" half is the sharper point. Corrected in Appendix D2. |
| A1 F4 wrapping half | **ACCEPTED.** Recorded as not-run in Appendix D3 rather than back-filled. |
| A2 F1 read-back | **ACCEPTED as a judgement call.** Recorded in Appendix D4. |
| Scope creep = clean | Agreed. |

One correction to the agent's own report: its C1 hypothesis attributes the peak to subagent
transcripts. The dotfiles project dir held **181** transcript files before and after this review's
two sub-agents ran, so sub-agent turns are **not** written as separate transcripts there. The
`2026-07-28T02Z` peak is 78 knowledge-base + 74 home-dir files, consistent with that day's parallel
graphify queue. The agent's conclusion (the figure conflates things and is not reproducible as
written) is right; its stated mechanism is not the whole story.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; the
  spec, `.claude/rules/`, and `docs/research/kb/reports/agents/` were read.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the
  `sources/agent-harness-docs/docs/claude-code/hooks.md` mirror used to verify the hooks claims.
