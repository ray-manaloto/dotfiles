# Opus cold review — plugin re-enable commit 8d5265c (2026-08-29)

Substitute cross-family lens: diff authored by a codex-implementer lane; grok-reviewer unavailable (grok CLI not installed), so this Opus pass is the announced fallback.

## Brief (prompt sent to the agent)

Cold review, diff only, no intent framing beyond what's needed to locate the change: review commit `8d5265c` on branch `chore/reenable-research-plugins` in `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` (repo root; run `git show 8d5265c` to see the diff).

The change touches `.claude/settings.json`'s `enabledPlugins` map only: flips `context7@context7-marketplace` and `exa@exa` from `false` to `true`, and adds a new key `firecrawl@firecrawl: true`.

Checked with a skeptical eye: (1) JSON validity/no duplicate keys, (2) diff touches only the claimed 3 keys, (3) security/scope concern with enabling network-calling research plugins at project scope given this repo's secrets-handling rules, (4) `firecrawl@claude-plugins-official` correctly left untouched, (5) any other defect.

## Report (verbatim)

**Mechanical checks (all clean):**
- JSON parses; `object_pairs_hook` duplicate-key scan → no dupes anywhere in the file.
- Diff is exactly 3 key assignments in the `enabledPlugins` block (`.claude/settings.json:114,116,117`); no other hunk, no stray key, no whitespace/reorder. Working tree clean.
- `firecrawl@claude-plugins-official` is **absent** from `.claude/settings.json` entirely (verified by reading the file, not the message) — correct, no double-enablement. It is `false` in `~/.claude/settings.json`.
- `firecrawl` marketplace exists locally and publishes a plugin literally named `firecrawl`, so `firecrawl@firecrawl` resolves.

**Findings:**

1. **HIGH — knowingly ships a red doctor check with no ticket and no baseline update.** `doctor.toml:159 max_chars = 34000`; the commit message states the listing now measures 36,732 (+2,732) and explicitly defers it. `zero-skip-policy.md` forbids dismissing a diagnostic, and `.claude/CLAUDE.md` states "changing your setup means changing `doctor.toml` in a reviewed diff" — this diff changes the setup and does not touch `doctor.toml`. Either raise the ceiling here with justification or file the issue; "for review, not resolved here" is the shape the policy exists to reject.

2. **MEDIUM — the enabled firecrawl variant is the one that costs the most.** `~/.claude/plugins/marketplaces/firecrawl/.claude-plugin/plugin.json` declares **12 skills** (12 `SKILL.md` files on disk) — the single largest contributor to the overrun in finding 1 — and #812 (`c1a58bb`) measured firecrawl at **zero invocations across 310 transcripts**. Choosing the larger listing to obtain one skill (`firecrawl-developer-index`) while the budget is already breached is the trade-off no reviewer would grant silently.

3. **MEDIUM — the change's actual effect is unverified.** All three keys are `false` in `~/.claude/settings.json` (user-global). The diff relies on project-over-user precedence; the commit verifies only JSON validity and `lint rc=0`, neither of which can observe whether the plugins load. No probe recorded.

4. **LOW — re-registers two bundled MCP servers, one on the credential trap this repo already documents.** `context7`'s `.mcp.json` interpolates `Authorization: ${CONTEXT7_API_KEY:-}` — the empty-value/anonymous-tier fallback named in `secrets-out-of-the-shell-env.md` §5 (context7, 2026-07-29). Presence-probed only: the var is currently SET, and doctor's `${VAR}` check covers it. `exa`'s server is an **unauthenticated** public endpoint (`https://mcp.exa.ai/mcp?client=agent-plugin`, no key header), so `EXA_API_KEY` is unused there and queries leave the host unattributed. Lane-1 allowed under `research-doc-sources.md`; noted, not a blocker.

No syntax, scope, or double-enablement defect found.

## Refutation pass (architect)

- Finding 1: CONFIRMED. Resolved per user's choice: raised `doctor.toml` ceiling to 38,200 (commit `748d0ec`), paired `suites.toml` contract token updated, re-verified clean.
- Finding 2: accepted trade-off, no change — user chose to keep firecrawl and raise the ceiling rather than drop it.
- Finding 3: partially refuted. `mise run doctor -- --verbose`'s own live recomputation went straight to 110 entries/36,732 chars immediately after the edit — the harness's own merged-listing tool confirming project-scope precedence actually took effect, not just a docs-based inference. A true end-to-end skill-invocation test wasn't run.
- Finding 4: informational only, no action — already covered by existing doctor checks.

## GitHub repos touched

- None — self-contained `.claude/settings.json` config review.
