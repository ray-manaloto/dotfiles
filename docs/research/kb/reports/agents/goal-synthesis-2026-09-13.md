# Goal Synthesis — Session 2026-09-13 — codex-astra-advisor

Advisor lane. Repo: dotfiles @ `5f96509` (branch `feat/enable-research-plugins`).

Read the three lane reports first — this report applies corrections and synthesizes them into a single proposed `/goal`.

## Executive Summary

**Proposed goal:** Fix `update-all` in `~/.config/mise/` so it runs clean (root cause: mise's lockfile forcing `--no-build`), then build fully-autonomous dependency-currency automation (skill → mise task → python library) that ships via `mise run ship` on green, then run full graphify commands (deep extraction, reflection, generated artifacts) once graphify 0.9.61 is installed. Run `/verify` after every phase. **Do NOT extend this to address the instrument decay thread — it is prerequisite-shaped but is not the operator's stated ask.**

**Three phases, concrete done-criteria:**
- **Phase 1:** `mise run update-all` succeeds without `MISE_LOCKFILE=0` workaround; root cause fixed in code, not papered over; `pytest` and `/verify` green.
- **Phase 2:** Dependency automation (mise.toml + pyproject.toml stale pins) fully autonomous from trigger to PR auto-merge, or drops-and-reports on red; skill→task→python structure; near-zero agent tokens per run; `pytest` and `/verify` green.
- **Phase 3:** Once graphify 0.9.61 installed, enumerate its CLI commands, run all relevant (deep extraction, reflection, generated artifacts), gitignored output; `pytest` and `/verify` green.

**Explicitly EXCLUDED (ranked by impact):**
1. **Instrument decay (session-review.md contamination + telemetry gap)** — Prerequisite-shaped but not the operator's stated ask. The operator asked for working automation, not working meters. Fixing the ledger is separate work; put it in an issue. (See §4 below: this is the deciding risk.)
2. **Secrets triage (44-distinct-value vs. 649-finding spread)** — Genuinely unresolved and high-stakes, but the operator did not name it in today's ask. The prior session already deferred rotation pending agentsview investigation; that decision stands. File `#1053` (operator to decide whether to re-activate the security thread) rather than embedding it in the dependency-automation goal.
3. **"While [" polling-loop task packaging** — Telemetry lane proposed this; team-lead's correction shows these are PRESCRIBED (not anti-pattern) for Mac-side container ops. Not a defect, just un-canonicalized. Leave as-is.
4. **Phase 2b cleanup (6-item stalled list)** — Real debt, zero momentum, operator did not mention it today. Carry it as-is in `task_plan.md`; do not adopt as `/goal`.
5. **#1046 (gha-rerun partial-failure caveat)** — Doc-only gap in `persistence-gate-retry.md`. Real but low-leverage (prevents human mistake, not mechanical). Defer to a post-goal doc-sync pass.
6. **fix/universal-subprocess-logging rebase** — Branch is stale (6 commits behind); merging would delete 9,600 lines of since-landed work. Real footgun, but agentsview pin may already be landed on main via a different mechanism. Defer to post-goal validation (30-second check for duplicate pin).

## The Deciding Risk

**The instrument decay thread is prerequisite-shaped but you cannot measure "fully automated, near-zero agent tokens" without working instruments.** Specifically:

- `.agent/session-review.md` is a **contaminated pytest artifact** (recorded_cwd = pytest tmpdir, 0 requirements/promises/events) dated 2026-09-13 TODAY. The real CAS is intact (2,514 run files), but the human-readable ledger is broken. **Any coordinator claim of "requirement coverage verified" made right now, without regenerating this file, is unsupported.**
- `.agent/telemetry/` stopped collecting **after 2026-08-29** — 15 days ago. All five telemetry-derived claims in this synthesis are bounded to a 3-day window (2026-08-26 through 2026-08-29). Future "did dependency automation actually reduce per-run agent cost?" questions cannot be answered without live data.
- **#1050 (graph rebuild) is partially closed** — staleness detection exists, but nothing triggers rebuilds. Once graphify 0.9.61 is running, you will not know whether the graph is stale between runs.

**The cost of ignoring this:** You ship dependency automation, mark it "done" via green `/verify`, and the next session still cannot answer "was this actually near-zero agent tokens?" because the ledger reading that would confirm it is broken, and the telemetry to measure token spend stopped 15 days ago.

**The cost of fixing it first:** Regenerating the ledger surfaces (and should fix) a test-isolation bug; restarting telemetry is configuration, not implementation. Both are <1 hour. But they delay the operator's explicit ask by at least a session.

**The recommend:** Proceed with the 3-phase goal AS STATED, document the instrument decay as the next `/goal` in a separate decision, and in Phase 3's done-criteria add one line: *"Know that graphify staleness between runs is not measured — #1050 rebuild automation and telemetry restoration are separate work."* This preserves the operator's priority while naming the debt.

## Open Questions for `/grilling` — the Genuine Ambiguities

These are decision-shaped questions with real alternatives, not open prompts. The operator already ran one grilling round; these are the remaining edge cases that decision raised.

### Q1. Phase 1 (fix update-all): Fix in mise itself, or work around it here?

**Context:** The root cause is upstream — mise's lockfile forces `--no-build` on pypi/pipx tools with a synthetic `requires-python = ">=3.8"` project, even though the real interpreter is 3.14. The two failing tools are `graphifyy[all]` (jieba) and `skypilot[aws]` (aiohttp), both shipping no wheels for 3.8/3.9/3.10.

**Verified workaround:** `MISE_LOCKFILE=0 mise run update-all` → rc=0. **Verified proof this is upstream:** `mise settings --all | grep -i python` has no native knob; the split is hardcoded in mise's resolution.

**Options:**
- **A (Recommended):** File mise issue + set `MISE_LOCKFILE=0` in `mise.toml` or `.claude/settings.json env` block as permanent fix-in-place. Removes the standing workaround tax. Cost: depends on mise's response, but this session can close it with rc=0 *today*.
- **B:** Skip phase 1 entirely; accept the `MISE_LOCKFILE=0` workaround as "sunk cost, live with it." Cost: every future `mise run` pays the workaround tax; leaves the defect unresolved for the next operator.
- **C:** Publish a detailed bug report + attempt to patch mise locally (add a `--no-build` knob or skip the synthetic project). Cost: high; may not land before next session.

**Your recommendation?** (This should be user-decided via AskUserQuestion; I'm an advisor, not decider.)

### Q2. Phase 2 (dependency automation): Image-build-input bumps — separate PR or bundled?

**Context:** The stale pins in `mise.toml` include two categories:
- **Tool versions** (mise, hk, uv, etc.) — safe to bump autonomously; no image input.
- **Image build inputs** (BASE_IMAGE, mise-system.toml pins, buildkit pins) — bumping one requires a full image rebuild (~2.5h CI).

**The handoff says:** "one PR per image-build-input bump, drops-and-reports on red" — implying separate PRs. But the brief also says "autonomous... near-zero agent tokens."

**Options:**
- **A (Recommended, per handoff):** Two distinct automation flows. Regular tool bumps ship in one slim PR per batch (near-zero gate cost). Image-input bumps get their own PRs, one per input, with a separate "image-build passed, but one pin caused a regression" reporting gate that names the pin and stops the automation for that one pending human triage.
- **B:** Bundle all bumps into one PR, accept the full rebuild cost. Simpler automation, higher token cost per run.
- **C:** Never automate image-input bumps; only automate tool versions, leave image inputs to manual review.

**Your recommendation?**

### Q3. Phase 3 (graphify run): Cost and coverage bounds?

**Context:** Operator said "no cost bound" on the graphify phase. But "enumerate all relevant commands" could mean:
- Just the three named ones (deep extraction, reflection, generated artifacts)
- All verbs graphify ships (you counted 27+ subcommands in `agentsview health --help` output)
- A subset based on "relevance to dotfiles" (needs judgment)

**Options:**
- **A (Recommended, per operator words):** All relevant commands. Use graphify's own `--help` to enumerate, apply human judgment ("deep extraction on a 567-session archive is relevant; `embeddings build` is probably not"), run them all, no cost bound, gitignored output. Done-criteria: every enumerated command ran and produced output (no silent failures).
- **B:** Just the three named ones (deep extraction, reflection, generated artifacts). Narrower, faster, matches the explicit ask most literally.
- **C:** The three named ones PLUS a cost budget (e.g., "stop after 2h of compute"). Balances thoroughness with practicality.

**Your recommendation?**

### Q4. Instrument decay — fix it before proceeding, or after?

**Context:** §3 above names the ledger contamination and telemetry gap. The transcripts lane showed that two prior `/goal` cycles in THIS SAME SESSION already ran to completion with structured goal-status attachments — meaning the harness's tracking WORKS even with broken instruments, it just means FUTURE sessions can't measure what happened in THIS one.

**Options:**
- **A (Recommended, per advisor note above):** Proceed with the 3-phase goal as-stated. Add to Phase 3 done-criteria: *"Acknowledge that graphify staleness between runs and near-zero-agent-token validation are not measurable until telemetry and session-review are restored; #1050 rebuild automation and telemetry restart are separate follow-up `/goal`s."* This preserves the operator's priority, documents the gap, and names what's owed.
- **B:** Stop now, fix the ledger (regenerate session-review.md + find which test wrote the contamination) + restart telemetry, THEN proceed with the 3-phase goal in the next session. Cost: delays the dependency work one more session; benefit: you can measure success honestly on the next run.
- **C:** Split into two `/goal`s: this session does "fix update-all" only (Phase 1), next session does "instrument restoration + phases 2-3." Cost: stretched timeline; benefit: forces the instruments to be current before measuring the expensive work.

**Your recommendation?**

## GitHub repos touched

_None._ This report synthesized local lane reports and the operator's own verbatim transcript excerpts; no external repo source, issue, or doc page was fetched.
