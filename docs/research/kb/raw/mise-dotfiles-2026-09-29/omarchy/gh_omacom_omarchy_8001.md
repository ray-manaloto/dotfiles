# Fix GitHub credential helpers after mise gh upgrades

- URL: https://github.com/omacom/omarchy/pull/8001
- author: thecdrz state: open created: 2026-08-24T05:04:07Z merged: n/a
- fetched: 2026-09-29 via gh api (lane X)

## Body

## Summary
- After a mise-managed `gh` upgrade, Git HTTPS auth can keep a credential helper pointing at a deleted versioned binary (`gh auth setup-git` records `os.Executable()`).
- Pointing the helper at `~/.local/bin/gh` still fails when that stub prints mise status on stdout.
- Migration rewrites only matching `credential.https://github.com.helper` and `credential.https://gist.github.com.helper` values to `!mise exec --quiet gh -- gh auth git-credential`, leaving unrelated helpers alone.

## Test plan
- [x] `bash test/shell.d/gh-credential-helper-migration-test.sh` — rewrites versioned + wrapper helpers, preserves empty entries and `credential.helper=store`, idempotent on re-run

Fixes #7712

Made with [Cursor](https://cursor.com)

## Comments

### thecdrz @ 2026-09-27T15:28:27Z

Refreshed this onto current `quattro`. The underlying #7712 failure still has no upstream replacement. `bash test/shell.d/gh-credential-helper-migration-test.sh` passes for targeted replacement, preservation of unrelated helpers, and idempotency; `git diff --check` also passes. Ready for maintainer review.


### omarchybot @ 2026-09-28T16:05:45Z

Reviewed and verified on a disposable Omarchy worker. The fix works, and I pushed one commit to the test.

**Reproduction.** On the worker I installed gh 2.97.0 through mise, wrote the helper config `gh auth setup-git` produces (an empty reset, then the absolute path to that versioned binary), and uninstalled 2.97.0. On `quattro`, `git credential fill` fails with the same `No such file or directory` error as #7712. With this migration applied, the helper becomes `!mise exec --quiet gh -- gh auth git-credential`, and the same `git credential fill` returns the credential from gh. Without the migration it fails again.

**Pushed: e2df69ac.** The test put the versioned helper before the empty reset, which is the reverse of what gh writes. An empty value clears every helper listed before it, so the test would still pass if the migration left git with no working GitHub helper. The commit seeds the reset first and asserts the exact order (reset, then the new helper). The updated test passes on the head and fails against a migration that does nothing.

**Tests.** `test/shell.d/gh-credential-helper-migration-test.sh` passes. `./test/cli` has one failure, `vscode generated theme references current theme file`. It fails the same way on `quattro` without this PR and is unrelated to it.

**Second opinion.** Codex Medium reviewed it in two rounds. It found the test ordering problem fixed above. Its second round, on e2df69ac, found nothing open. It also raised three points that I left alone:

- A path gh would single-quote. gh only quotes a path containing spaces, `$` or backticks, and a stock `/home/<user>` cannot contain them.
- An early exit from `grep -q` under `pipefail`. This needs a single key with more values than fit in a pipe buffer.
- Recurrence, covered below.

**For the maintainer.** This migration repairs configs that exist today. It does not stop the problem coming back. The next time someone runs `gh auth setup-git`, or accepts git setup during `gh auth login`, gh records its versioned binary again, and the following mise upgrade breaks it. A durable fix is a decision about how Omarchy wires git credentials to gh, and it would be a separate change. Also, `~/.local/bin/gh` no longer prints to stdout on `quattro` (#8041). So rewriting helpers that point at the wrapper is now a tidy-up rather than a repair; it is harmless either way.

Waiting on the maintainer.


## Changed files
- added migrations/1787547773.sh (+21/-0)
- added test/shell.d/gh-credential-helper-migration-test.sh (+55/-0)
