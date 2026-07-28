# Evidence — `mise-tasks-only`

Case history behind `.claude/rules/mise-tasks-only.md`. The eager rule carries
the canonical task map and the operative constraints; this file carries the
measurements, the two defect stories, and the design rationale.

## Why we do NOT re-inject a per-turn reminder

*(2026-07-14, research-backed.)*

We deliberately do not re-inject a "use mise tasks" reminder every turn
(`UserPromptSubmit`) or nudge after every command (`PostToolUse`). Anthropic's
guidance routes static conventions to `CLAUDE.md` and enforcement to the
`PreToolUse` hook, and the LLM-behaviour evidence ranks a hard gate (zero decay)
far above per-turn reminders, which decay, cost instruction budget, and sit in
the lowest-trust tier.

Source: `docs/research/runs/research-20260714-hook-enforcement/report.md`.

The improvement path is layer 4 mining transcripts — not more per-turn hooks.

## Reading the command-audit report: why two axes are needed

A bare "matched a rule" verdict is almost pure noise. Measured over 3,615
commands (2026-07-14): **155** matched a rule — **147** predated it, **3** were
denials, **0** bypasses.

The transcript forces the second axis, recording the `tool_use` block whether or
not the command ran (a deny lands *after* the model emits it), so a denial and a
bypass are identical until you pair the attempt to its result.

## "Nothing has ever evaded the guard" was false in BOTH directions (#343)

That sentence stood in the rule until 2026-07-28.

Re-judged against the `hook_guard.py` live at each command's own timestamp
rather than trusting `since`: of 128 rows, **3 false**, **125 genuine**.

The 125 ran because **the guard never ran**. Hooks execute "in the current
directory", so the relative `bash scripts/pretooluse-guard.sh` was absent
whenever a session worked in the sibling repo (rc=127) — and a non-zero, non-2
`PreToolUse` exit is a **non-blocking error that lets the call proceed**.

Every path is now anchored to `$CLAUDE_PROJECT_DIR` (settings.json AND the
wrapper's equally-relative `uv --project`), and `hook_selfcheck` drives a
**foreign-cwd arm** — both old arms ran at the project root, which is precisely
why this survived so long.

**A fail-open that nothing counts is indistinguishable from enforcement.** Each
is now recorded (`~/.local/state/dotfiles/guard-fail-open.log`) and reported by
`command-audit`.

Evidence: `docs/research/runs/research-20260728-guard-fail-open/`.

## Fixed: prose content in compound commands (#265)

The guard used to match the RAW Bash string, so a separator inside quoted or
heredoc CONTENT read as a shell separator, and the denied literal after it looked
like it sat at a command position (`grep -iE "…|devcontainer up|…"` was denied).
A deny cancels the ENTIRE compound command, silently skipping its other parts —
so the cost was a command that *looked* like it ran.

**Fixed 2026-07-14** by `hook_guard._inert_masked`: separators (`;&|` + newline)
that are DATA get neutered before the rules run — inside quoted spans (content
preserved, only separators blanked, since a rule may need to read a quoted
argument) and inside heredoc bodies (`<<EOF`, `<<'EOF'`, `<<-EOF` — redacted
whole; a body is stdin data and can never be a command). Rule patterns are
untouched, so recall is preserved by construction. `blocked` went **3 → 1**,
keeping the one denial that was always correct.

Masking narrows the fail-open class deliberately: `eval "echo x; gh pr create"`
was denied before (the quoted `;` anchored `_CMD`) and is allowed now. That was
an accident, not coverage — bare `eval "gh pr create"` was always allowed, so
only the separator-bearing variant was ever caught. Giving it up IS the
precision-over-recall trade.

**Against the MATCHER, false positives were the defect, not evasion.** 2 of the
3 denials ever recorded were the quoted-regex shape, and the survivor (an `npx`
behind a real `||`) was correct — hence 3 → 1, not 3 → 0.

Twice a predicted risk was refuted by probing and the real one was its mirror
image (#264's cd-prefix; #265's quoting): **measure before believing**.

**Scope matters:** nothing has evaded the *matcher*, but #343 found 125 commands
bypassing the guard entirely by never reaching it. Those are different claims.

## `since` dates COVERAGE, not the Rule object — the #308 back-dating

`68f28c9` (#308) brought `hk run check` under the guard on 2026-07-18 by
**widening** the existing `hk run pre-commit` rule, leaving `since` at
2026-07-07. The audit therefore back-dated 11 days of coverage and cried bypass
on three calls the guard of that day had correctly allowed (#343). Now split
into `_V1` and `_V1B`.

**A proxy goes stale silently:** when a bypass count moves, check the rule's
history (`git log -S` on the pattern) before believing it.

## The repo-aware dispatch defect

The rules once matched `gh pr merge` unconditionally, so a knowledge-base PR was
denied and pointed at `mise run land` — a *dotfiles* task with no repo parameter,
watching dotfiles' main CI. KB PRs #1 and #2 were merged by hand.

**A guard whose redirect target cannot perform the redirected action is not
enforcement, it is an outage.** Hence dispatch by target repo, and hence
"any other repo → ALLOW".

## The provenance axis (#369)

It recurred along a second axis. Only `ship` arms auto-merge and a bot PR never
runs it; `land` refuses an OPEN PR; `gh pr merge` redirected to `land`. #138,
#236 and #386 sat green and unmergeable. `automerge` is the missing verb.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the guard,
  its rules, and issues #264/#265/#266/#308/#343/#369.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  the sibling repo whose PRs exposed the repo-aware dispatch defect.
