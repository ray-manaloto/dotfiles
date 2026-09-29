# mise stubs cannot be restored after ~/.local/bin is cleared, silently breaking the documented gh auto-install

- URL: https://github.com/omacom/omarchy/issues/13708
- state: open | author: amaurisd97 | created: 2026-09-29T04:18:21Z | closed: null | merged_pr: n/a
- labels: 

## Body

## Problem

`install/user/mise.sh` creates 15 lazy-install stubs in `~/.local/bin/` via `omarchy-mise-install`. Each wrapper runs `mise use -g <pkg>` on first execution, so the tool installs itself.

`manual/18-development-tools.md` documents this for `gh`:

> It's wired up as one of the lazy-loading mise stubs, so the first time you run `gh`, it installs itself.

Migration `1784909971.sh` ("Regenerate mise wrappers to stop them recursing through PATH") is the only recovery path. It derives the list of packages **by iterating the wrappers that already exist**:

```bash
for wrapper in "$HOME/.local/bin"/*; do
  [[ -f $wrapper && -x $wrapper ]] || continue
  package=$(sed -n 's/^mise use -g "\(.*\)"$/\1/p' "$wrapper")
  ...
  omarchy-mise-install "$package" "$(basename "$wrapper")" "$bin"
done
```

There is no canonical list of expected stubs stored anywhere in the repo. Once `~/.local/bin` is empty the glob does not expand, the loop finds nothing, and no migration recreates anything.

## Impact

Clearing `~/.local/bin` — a routine cleanup — permanently destroys all 15 stubs. The documented `gh` auto-install silently stops working with `gh: command not found`, with no error, warning, or log line. Users cannot recover without re-running `omarchy-mise-install` by hand.

Note that `migrations/1786183928.sh` ("Refresh mise stubs so tools take new releases immediately") does not help either: it only calls `omarchy-refresh-applications`.

## Reproduction

```bash
rm -rf ~/.local/bin/*
omarchy update          # runs all migrations
gh --version            # gh: command not found
```

Verified on Omarchy 4.0.4, kernel 7.2.5-3-omarchy.

## Suggested fix

Store the canonical stub list (a data file, or by re-running the `omarchy-mise-install` lines from `install/user/mise.sh`) and have `1784909971.sh` iterate that list rather than the existing filesystem state, so stubs are restored idempotently on every update.

## Related

Same migration, different failure modes already reported: #13040, #11973, #11971, #13677, #13177, #10300.


## Comments
