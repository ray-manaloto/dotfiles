# /code-review medium — Phase C dual-arch `f93bb776` (2026-09-28)

Verbatim fork report. Coordinator disposition:
- Finding 1 CONFIRMED on real data: the running amd64 container's `mise ls --json --installed` already holds an
  inactive leftover (`npm:typescript 7.0.2`, `active=false`, `requested_version: null`). Fixed by keying only
  `select(.active)` installs. Arms on the real JSON: bump + inactive leftover → diff rc=0 with the new key, rc=1 with the
  previous key (the reviewer's scenario).
- Finding 2 CONFIRMED by reading `local_platforms` (published triples only). Fixed with `sync.platform_present`, which
  compares by `platform_arch`; an unparsable platform is "absent" (refresh reports it). Mutation back to literal
  membership: 1 fail.

---

I found 2 issues in `f93bb776~1..f93bb776`. There is no ReportFindings tool in this session, so the findings are below only.

1. **`mise.toml:610` (medium): an old version left on disk still fails the `#1172` gate.** The new key only works on entries that carry `requested_version == "latest"`. `mise ls --json --installed` also lists older installed versions of the same tool, and those have `requested_version: null`. I checked this on the host: `aqua:FiloSottile/age` lists `1.3.1` with `null` and `1.3.2` with `"1.3.2"`. So when an upstream release lands during the stop/up cycle and the old version stays installed, the snapshots look like this:
   - before the cycle: `tool\tlatest`
   - after the cycle: `tool\tlatest` plus `tool\t<old-version>`

   The `diff` then reports "installed-tool set drifted" for exactly the version bump `#1172` meant to allow. One fix is to skip inactive entries (`select(.active)`) or entries with a `null` `requested_version` before building the key. I haven't confirmed the old version actually stays installed inside the container after an upgrade; the arms in the commit message never produced a second, inactive entry.

2. **`python/src/dotfiles_setup/sync.py:727` (low): a short platform spelling makes sync permanently stale.** `platform_present` is `resolve_platform() in local_platforms(...)`. `local_platforms` only ever returns the full triples from `published_targets()` (`linux/amd64/v2`, `linux/arm64/v8`). If someone overrides `DOTFILES_PLATFORM` in `mise.local.toml` as `linux/amd64` (no `/v2`), docker accepts it, but the check can never match. The result:
   - `SyncStatus.stale` is always True, so `sync --check` always returns 1.
   - Every `mise run sync` picks `rebuild` and tears down a running container, even right after a successful refresh.

   Before this commit, the same override just refreshed through the union and settled. Normalising the resolved platform to its published triple before the membership check (or matching on `platform_arch`) would fix it.

I ran no gates; this was a read-only review of the diff.

## GitHub repos touched

_None._
