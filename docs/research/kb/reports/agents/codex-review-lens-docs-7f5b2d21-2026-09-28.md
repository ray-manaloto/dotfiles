# Codex read-only review lens — doc/agent branch `7f5b2d21` (2026-09-28)

Command: `mise exec -- codex exec -s read-only --ignore-rules review --commit 7f5b2d21 -c 'sandbox_mode="read-only"'` rc=0. Final message verbatim. Both findings CONFIRMED and fixed in the verify skill: OUTDATED stays a failure unless the #1432 signature is shown; the stale-file probe runs the hook in `read` mode. Disjoint from `/code-review` of the same commit (which found the TOML figure + probe version) — the two lenses again found different defect classes.

---

The verification instructions introduce a misrouted probe and can dismiss genuine container drift. Findings were checked against source and existing tests; runtime validation was blocked by read-only cache permissions.

Full review comments:

- [P2] Preserve OUTDATED as a failed check until its cause is verified — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agents/skills/verify/SKILL.md:42-43
  `sync_main()` returns 1 for `OUTDATED`, including genuine overlay mismatches covered by `test_sync_check_mode_reports_an_outdated_container`. The output does not distinguish those failures from #1432, so this blanket exemption can bless an outdated container after landing. Require evidence that the result is specifically the known bookkeeping issue; otherwise retain the failed verification status. This also preserves the confirmation requirement in [AGENTS.md:144](AGENTS.md#L144). Update both skill copies.

## GitHub repos touched

_None._
