# codex-sol-advisor: zsh separator printf vs echo (verification run 2, lane a6750a24)

Decision under advice: In a zsh probe, should a separator line be printed with
`printf '%s\n' '===='` or `echo '===='`?

Scope note: this is a mechanical fact lookup, well below the advisor's bar
("hard to reverse", "resisted two attempts", "routing/fallback choice",
"pre-done multi-step review"). It was run anyway as a **live verification of
the codex-sol-advisor lane mechanics** (launch line changed to `mise exec --
codex exec`), not because the underlying question warranted advisor-tier
consult. Future callers with a similarly trivial question should use a
cheaper lane.

## Verdict (relayed verbatim from codex's `-o` output)

> Prefer `printf '%s\n' '===='`. It is more predictable across shells because
> `echo` may interpret options or backslash escapes differently.

## Lane mechanics — verification evidence

- Lane files line: `lane files: LANE_ID=a6750a24-verify2 PROMPT=.agent/kb/raw/codex-sol-advisor-prompt-a6750a24-verify2.md OUT=.agent/kb/raw/codex-sol-advisor-verdict-a6750a24-verify2.md LOG=.agent/kb/raw/codex-sol-advisor-verdict-a6750a24-verify2.log`
- Launch form used: `cat "$PROMPT" | PLANNING_DISABLED=1 mise exec -- codex exec --sandbox read-only --model gpt-5.6-sol -c model_reasoning_effort="xhigh" -o "$OUT" -`
- `$LOG.rc` contents: `0`
- `$OUT` byte size: `138`
- Codex version line from top of `$LOG`: `OpenAI Codex v0.156.1`
- Wait slices run: **1** (single bounded slice of up to 540s; the run settled
  well within it — completed before the first poll interval finished, per the
  background-task notification)

## What could not be verified

- Whether `mise exec -- codex exec` resolves the same pinned Codex version as
  a bare `codex exec` in this environment — not probed separately in this run
  (out of scope for a mechanics-only verification of launch-line change).
- No repo files were read or cited by codex for this trivial factual
  question; nothing to cross-check against source.

## GitHub repos touched

_None._
