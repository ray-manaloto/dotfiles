# Review spec: credit-fallback Stop-hook prompt injection (N2), plus N1, at 636dd297

Requested by Ray, 2026-10-04 ~00:55 CDT ("/codex-sdlc-team skill to review"). REVIEW mode: research and propose. Do NOT edit tracked files, commit, push, or open PRs.

Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/credit-fallback`, branch at 636dd297.
Read with `git -C`, or with absolute paths.

## Context

Ray ruled "block once if unnamed" for the provisional Codex Stop hook. A Stop `decision: block`
`reason` becomes a new continuation prompt in the USER role (codex `hooks.md:914-925`, in
`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/`). The Opus
cold review (`docs/research/kb/reports/agents/cold-review-credit-fallback-636dd297.md` in the
worktree) found two problems:

- **N2.** `scripts/codex-research-gate.py:123-130` builds that `reason` from the provisional lines,
  which carry up to 300 chars of raw provider text each. A planted string in a Serper 400 body
  reached `reason` verbatim. **Ray: N2 MUST BE FIXED, not ticketed.** The suggested fix is to build
  the reason only from the structured source and route names.
- **N1.** `research_fanout.py:1428-1437`: the any-status fallback phrase rule fires on a 2xx body
  that failed only on shape. That launders a fallback failure into a passing provisional receipt.

## Questions

1. Confirm or refute N2 and N1 with file:line evidence and a probe (with its control arm, per
   `.claude/rules/probes-need-a-control-arm.md`).
2. Is building the reason from structured `{source, route}` fields alone sufficient? Consider:
   - can a source or route name itself be attacker-influenced (provider names are a fixed set?);
   - other provider-text paths into model-visible channels: `systemMessage`, `additionalContext`,
     the workflow synthesis prompt `provisionalRoutes`, the PROBE-JSON line that an agent copies,
     and the `last_assistant_message` matching.

   Enumerate every path from provider bytes to a model-visible channel. Cite file:line for each.
3. Propose the fix for N2 (required) and N1, each with PRO/CON and the tests that must pin it,
   including a mutation that proves each test discriminates.
4. Say whether any other cold-review LOW (N3–N5) interacts with this fix.

## Constraints

- HOST SLOT: another heavy run owns the host. Run only targeted pytest on
  `tests/test_codex_research_gate.py` and `tests/test_research_fanout.py`.
- No full suite, no `mise run lint`/`verify`, no container ops, and no live provider calls.
- Never print credential values.

## Output

Deliver:
- verdicts for N1 and N2;
- the injection-path table;
- the fix proposals, each with PRO/CON and its tests;
- ONE recommendation;
- `## GitHub repos touched`.

## COMMIT

caller (none in review mode).
