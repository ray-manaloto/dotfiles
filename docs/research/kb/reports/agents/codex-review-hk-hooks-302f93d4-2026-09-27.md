# Cold codex review — 302f93d4 (review fixes F1-F4), 2026-09-27

Lens: `mise exec -- codex exec -s read-only --ignore-rules review --commit 302f93d4` (gpt-6-astra; session 01a0e1d5-3758-7602-a386-ebd8d67a16e2). rc=0.

## Final message (verbatim)

codex
The new doctor check can accept disabled hooks and reject working legacy installations. The new safe-directory assertion also fails for checkout paths containing spaces. Full tests were not run in the read-only sandbox.

Full review comments:
- [P2] Check effective hooks rather than raw event declarations — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hk_hooks.py:63-67
  When a checkout disables a global hook with `hook.hk-pre-commit.enabled=false` or clears its events with an empty `.event`, this query still returns the earlier `pre-commit` declaration, so the doctor incorrectly passes. Read-only probes confirmed that `git hook list` reports the hook as disabled or absent while this parser counts it. Inspect effective hook state instead, consistent with the [native-tool policy](.claude/rules/use-tool-builtins.md#L25-L29), so the check actually detects loss of the [required enforcement layer](.claude/rules/do-not.md#L63-L65).
- [P2] Recognize working legacy hk hook installations — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hk_hooks.py:49-51
  For a checkout installed with `hk install --legacy --mise`, the required hooks exist as executable scripts rather than `hook.hk-*.event` entries. This query therefore reports every hook missing even though they run. hk 2.3 also selects this installation mode automatically on Git older than 2.54, where the doctor's suggested `--global` repair is unsupported. Recognize hk scripts in Git's effective hooks directory before concluding that an event is missing.
- [P2] Preserve spaces in safe.directory paths — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_git_config_isolation.py:92-93
  If the checkout path contains a space, Git returns the correctly configured directory as one line, but `.split()` breaks it into separate words. The following assertion then fails despite the fixture correctly trusting the checkout, making the test suite fail in such clones or worktrees. Use `.splitlines()` to preserve each complete path.

## GitHub repos touched

_None._
