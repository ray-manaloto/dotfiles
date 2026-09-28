# Codex read-only review lens — #1388 `1068c6b` (2026-09-28)

Command: `mise exec -- codex exec -s read-only --ignore-rules review --commit 1068c6b… -c 'sandbox_mode="read-only"'` rc=0. Final message verbatim (log lines 2960-2969 of `.agent/logs/codex-review-1388.log`). Both findings CONFIRMED by the coordinator (`zsh -c` + `match()`); finding 2 and the arithmetic half of finding 1 duplicate `code-review-1388-2026-09-28.md`; the escaped-space case `echo x\ ====` is NEW (zsh rc=0, denied).

---

The new rule blocks valid shell expressions while missing failing separators inside common compound statements. Shell behavior was verified with zsh; Python tests could not start because the read-only sandbox blocked uv cache access.

Full review comments:

- [P2] Restrict equality matching to actual shell argument boundaries — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:338-338
  Commands such as `echo $((1 == 1))` and `echo x\ ====` match this pattern even though both execute successfully in zsh without equals expansion. The quoted-blind view preserves arithmetic expressions and escaped whitespace, so whitespace before `==` does not establish an argument boundary. Consequently, the hook denies legitimate diagnostics and cancels their entire compound command. Distinguish these contexts and add allowed-case tests, consistent with the [narrow-pattern requirement](.claude/rules/mise-tasks-only.md#L90-L91).

- [P2] Recognize printing commands inside compound statements — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:338-338
  For `for f in a; do echo ====; done` or `if true; then echo ====; fi`, `_CMD` cannot reach the printing command because `do` and `then` intervene after the separator. Neither command is denied, although both fail with `=== not found` and rc=1 in zsh. This leaves ordinary loop and conditional forms of the [documented separator failure](.claude/rules/mise-tasks-only.md#L31) unguarded. Extend this rule's command-position recognition and add corresponding denial/control tests.

## GitHub repos touched

_None._
