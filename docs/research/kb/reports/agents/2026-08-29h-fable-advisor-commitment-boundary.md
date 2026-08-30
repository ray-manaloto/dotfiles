# Agent report: fable-advisor — commitment-boundary check before /to-spec

Session: 2026-08-29h.

## Brief

Decision: is this session ready to move from the `/grilling` re-scope thread
into the `/to-spec` → `/to-tickets` → `/implement` pipeline, and what should
happen to 5 confirmed cold-review findings on already-merged code first: fix
now, file as GitHub issues, or defer silently?

Context pasted: item 3 (re-review) closed via clean session-state; item 4
(code review coverage) answered via a real codex-reviewer pass over
`7eb6ba5^..a7b561f`, 10 findings, 5 confirmed by the architect (P1
session-handoff ordering; env-scrub gap; extensionless-regex gap; OSError
gap; test-mock argument-drop). Item 2 (ponytail-debt) already settled
separately: don't adopt.

Questions: (1) should the P1 be fixed inline now? (2) should the 4 P2s be
bundled into one issue or does any rise to fix-now? (3) is this a legitimate
commitment boundary to move to /to-spec?

Verdict in under 300 words.

## Report (verbatim)

Verdict: fix the P1 now, file one issue for the P2s (include the 5 unverified findings, labeled), then the boundary is legitimate.

1. **P1 — yes, fix inline now.** I read both sites; the conflict is real but mild: step 2 item 4 (`SKILL.md:98-99`) instructs the GitHub mutation unconditionally, and the self-triggered review gate (`SKILL.md:200-214`) constrains those same verbs — a reader executing top-to-bottom on a self-triggered run mutates before the gate. Fix is one sentence at item 4 ("on self-triggered runs, the review gate below applies before these"), no lane, no spec. Branch first, three local gates, `mise run ship`.

2. **P2s — one issue, not four, and not fix-now — with one candidate exception.** None of the four is a live production hazard: `GIT_DIR` scrubbing (real but theoretical on this host), extensionless-citation regex, `OSError` traceback, and the argument-discarding mocks. Zero-skip rule 4's precedent fits exactly: one issue, full context, file:line anchors as given. The exception worth considering: finding 5 guards precisely the regression #827 just fixed — asserting the mock's argument is a few-line test change, and if you're already opening the P1 PR, folding it in is cheaper than the issue round-trip. Either disposition is defensible; do not fix the other three now.

3. **One piece of unfinished business before `/to-spec`:** the 5 *unverified* cold-review findings. Silently dropping them violates the same rule 4 you just applied — list them in the issue explicitly marked "unverified, not re-derived" (per `probes-need-a-control-arm.md` rule 6, inherited claims get labeled, not repeated as findings). Once the P1 PR lands and the issue exists, this is a clean commitment boundary; proceed to `/to-spec`.

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-handoff/SKILL.md`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_pr.py`.

## GitHub repos touched

- _None._ — advisory verdict on pasted evidence and named local files only.
