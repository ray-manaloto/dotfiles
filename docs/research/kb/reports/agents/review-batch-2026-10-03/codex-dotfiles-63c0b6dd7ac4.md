# dotfiles `63c0b6dd7ac4` — codex review lens

- Target: `63c0b6dd7ac4f07eebb590af683f31b574f1503f` (dotfiles)
- Command: `mise exec -- codex exec -s read-only --ignore-rules review --commit 63c0b6dd7ac4f07eebb590af683f31b574f1503f -c 'sandbox_mode="read-only"'` (codex-cli 0.160.0), run from the dotfiles checkout
- Log: `.agent/logs/review-batch/codex-dotfiles-63c0b6dd7ac4.log` (gitignored); rc=0

## Final codex message (verbatim)

```text
The new check can incorrectly pass non-native executables through symlinked native locations or empty PATH components. Review was source-based; Graphify health could not run because the read-only sandbox blocked temporary-file creation.

Full review comments:

- [P2] Keep native locations independent of the executable being checked — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/review-batch-20261003/python/src/dotfiles_setup/path_drift.py:538-540
  If `~/.local/bin/agy` is a symlink to a Homebrew or npm-installed executable, resolving the configured native location makes that foreign executable the trusted root. The PATH hit then resolves to the same file and passes without any finding, defeating the explicit rejection of non-native installations. Keep the declared location as the trust boundary rather than following its symlink to an arbitrary target.

- [P2] Include current-directory hits for empty PATH components — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/review-batch-20261003/python/src/dotfiles_setup/path_drift.py:518-521
  When the captured PATH starts with a colon or contains an empty component, shells search the current directory at that position. Skipping these components means a foreign `codex`, `claude`, or `agy` in the current directory can win actual command resolution while this check reports that a later native executable wins. Treat empty components as the current directory so the verdict reflects the shell's lookup order.
The new check can incorrectly pass non-native executables through symlinked native locations or empty PATH components. Review was source-based; Graphify health could not run because the read-only sandbox blocked temporary-file creation.

Full review comments:

- [P2] Keep native locations independent of the executable being checked — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/review-batch-20261003/python/src/dotfiles_setup/path_drift.py:538-540
  If `~/.local/bin/agy` is a symlink to a Homebrew or npm-installed executable, resolving the configured native location makes that foreign executable the trusted root. The PATH hit then resolves to the same file and passes without any finding, defeating the explicit rejection of non-native installations. Keep the declared location as the trust boundary rather than following its symlink to an arbitrary target.

- [P2] Include current-directory hits for empty PATH components — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/review-batch-20261003/python/src/dotfiles_setup/path_drift.py:518-521
  When the captured PATH starts with a colon or contains an empty component, shells search the current directory at that position. Skipping these components means a foreign `codex`, `claude`, or `agy` in the current directory can win actual command resolution while this check reports that a later native executable wins. Treat empty components as the current directory so the verdict reflects the shell's lookup order.
```

## Lane triage

2 findings, both [P2]. (1) Symlinked native root → DUPLICATE of #1599 finding 2. (2) Empty PATH components skipped. **Second read: CONFIRMED** at HEAD `path_drift.py:519-520` (`if not raw: continue`); a shell treats an empty component as cwd. The impact is narrow, since the doctor's cwd is the repo, but it is real. Added to #1599 as a comment.

## GitHub repos touched

_None._ (local git objects only)
