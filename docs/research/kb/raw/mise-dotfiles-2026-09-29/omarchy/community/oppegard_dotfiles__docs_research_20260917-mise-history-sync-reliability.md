<!-- source: https://github.com/oppegard/dotfiles/blob/HEAD/docs/research/20260917-mise-history-sync-reliability.md ; fetched 2026-09-29 via gh api contents (lane X) -->
# Reliable mise dotfile-history synchronization

Researched 2026-09-17 against the locally installed mise `2026.9.10`
and current first-party mise and GitHub CLI sources. This note is read-only:
it proposes no configuration or service change.

## Conclusion

There are **two independent failures**:

1. The history watcher is running but is not watching this mise history store.
   This is the known post-upgrade state that mise `2026.9.10` diagnoses as
   `service-not-watching`; `mise bootstrap services apply` is now designed to
   restart that watcher.
2. Remote synchronization has failed 33 times because the checked-in Git
   credential helper calls a deleted, version-specific `gh` executable. A
   watcher restart cannot repair that Git configuration. The next watcher sync
   will use a repaired helper without needing a restart.

For a dependable setup, recover the stale watcher once, eliminate the
versioned HTTPS helper (prefer SSH for the history origin), and add an
independent read-only status monitor. Mise itself does not notify for
authentication or network-sync failures.

## Local evidence

`mise bootstrap dotfiles status` reported:

- 5 tracked files and 312 checkpoints;
- `automatic capture: running but not watching this store`;
- setup-history HTTPS fetch failure since 2026-09-16 17:01, with 33 attempts;
- the missing executable was
  `.../gh_2.100.0_macOS_arm64/bin/gh`.

`mise which gh` now resolves `gh` 2.101.0. The then-current global Git
configuration identifies the cause precisely: the `github.com` and
`gist.github.com` helpers used the obsolete 2.100.0 absolute path.
`launchctl print` shows the history LaunchAgent itself starts the durable
`/Users/glenn/.local/bin/mise dot watch` command; it does not name `gh`.

Thus local checkpoint capture can continue while **publishing and pulling are
blocked**. The stale HTTPS helper is the cause of the sync failure, not merely
a symptom of the stale watcher.

## 1. Does `track` notify when synchronization fails?

No, not for this failure class. Mise documents desktop notifications only for
sharing conflicts, once per paused conflict. Authentication and network errors
retry with exponential delays from one minute to one hour, while `mise dot
status` and `mise doctor` retain the last error. There is no documented native
desktop notification for persistent authentication, transport, or checkpoint
failure. [Mise history: sync, conflict notifications, and health](https://mise.jdx.dev/history.html)

The distinction is intentional in the source: the notification component is
for conflicts requiring a decision, while sync errors are persisted as
`last_error`, `failing_since`, and `consecutive_failures`.
[Notification source](https://github.com/jdx/mise/blob/main/src/system/history/notify.rs)
and [sync error persistence](https://github.com/jdx/mise/blob/main/src/system/history/sync/run.rs#L432-L448).

`mise dot status --missing` is not a substitute: it exits nonzero for managed
dotfile drift, not a failed history origin. The JSON status is the supported
read-only monitoring seam: `.history.watcher`,
`.history.health.watcher.last_error`, `.history.sync.last_error`,
`.history.sync.failing_since`, and `.history.sync.consecutive_failures`.
[Status source](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/history_status.rs).

## 2. What lifecycle recovery exists?

### Stale watcher process

This host is on the release that fixed the stale-watcher recovery path. Mise
2026.9.5 moved history locks to `$MISE_STATE_DIR/history`; an already-running
watcher keeps the old lock until restarted. The upstream fix makes `mise
bootstrap services apply` restart a converged `history-watch` process when it
is not watching the current store, and makes `doctor`/`dot status` report the
actionable `service-not-watching` state.
[Mise PR #13190](https://github.com/jdx/mise/pull/13190) and the
[2026.9.10 release notes](https://github.com/jdx/mise/releases/tag/v2026.9.10).

The local dry run confirms it would boot out, bootstrap, enable, and kickstart
only `dev.mise.mise-history`. It should be applied once after approval; it is
the correct fix for the first failure.

There is no general hook that automatically restarts this service after every
tool update. Bootstrap `post-tools` hooks run only on an explicit bootstrap.
The upstream discussion notes that an external package replacement cannot
notify mise at replacement time; its recovery point is the next `doctor`,
`bootstrap`, or `bootstrap services apply`.
[Discussion #13189](https://github.com/jdx/mise/discussions/13189).

### `gh` upgrade lifecycle

Use a **tool-level** `gh.postinstall` hook for a repair that must run after
each `mise upgrade gh`, not a global `[hooks].postinstall` or bootstrap
`post-tools` hook. Mise documents tool-level `postinstall` as running after
that tool installs; the upgrade implementation installs the new tool version
through that path. [Mise hooks](https://mise.jdx.dev/hooks.html),
[upgrade source](https://github.com/jdx/mise/blob/main/src/cli/upgrade.rs),
and [backend postinstall source](https://github.com/jdx/mise/blob/main/src/backend/mod.rs#L3695-L3700).

That hook must repair the helper to a *stable resolver*, not invoke `gh auth
setup-git`. GitHub CLI intentionally writes its own resolved executable path
as the helper, which is disposable when that executable was installed by mise.
[GitHub CLI source](https://github.com/cli/cli/blob/trunk/pkg/cmd/auth/shared/gitcredentials/helper_config.go#L20-L64).

The exact mise-managed failure has an independent public reproduction. Its
working helper is `!mise exec --quiet gh -- gh auth git-credential`; a bare
mise shim emitted non-protocol output in that environment. For this macOS
LaunchAgent, the stronger untested proposal is a durable absolute mise path
plus `MISE_EXEC_AUTO_INSTALL=0`, for example:

```ini
!MISE_EXEC_AUTO_INSTALL=0 /Users/glenn/.local/bin/mise exec --quiet gh -- gh auth git-credential
```

The absolute mise path and no-auto-install guard are an inference for a
non-interactive service, not an upstream-prescribed string. Validate that the
helper writes only Git credential-protocol data before adopting it.
[Mise `exec_auto_install` setting](https://mise.jdx.dev/configuration/settings.html).
[Omarchy issue #7712](https://github.com/omacom/omarchy/issues/7712) and its
[open migration PR #8001](https://github.com/omacom/omarchy/pull/8001) are
third-party corroboration, not mise or GitHub CLI authority.

## Recommended durable design

1. **Recover now:** review and run `mise bootstrap services apply`, then use
   `mise dot status` and `mise doctor` to confirm `watcher = running`.
2. **Remove this dependency:** change the mise-history origin from HTTPS to
   `git@github.com:oppegard/setup.git`, after verifying the LaunchAgent can
   use the intended SSH agent/key. Mise explicitly prefers an SSH-agent key for
   SSH remotes. This makes `gh` credential-helper paths irrelevant to history
   publish and pull. [Mise repository authentication guidance](https://mise.jdx.dev/history.html).
3. **Protect normal HTTPS Git too:** replace only the two GitHub/Gist
   versioned helpers with the stable, quiet resolver above. Make that repair a
   tested, idempotent `gh.postinstall` action so a later `mise upgrade gh` does
   not reintroduce a deleted installation path. Do not run `gh auth setup-git`
   as the repair because it recreates the fragile path.
4. **Add an independent monitor:** a macOS scheduled LaunchAgent should run
   `mise dot status --json` through the durable mise executable at login and a
   modest interval, alert once per new error fingerprint when watcher is not
   `running` or `.history.sync.last_error` is non-null, and clear its local
   alert state on recovery. It must not call `sync`, `pull`, or `save`; status
   and doctor read the health report without starting synchronization or
   changing files. A normal idle period is not an error, so do not alert solely
   on age of `last_publish`.

This is defense in depth, not a claim of literal impossibility of failure: a
sleeping Mac, unavailable network, expired credential, or broken SSH agent can
still block sync. It does ensure the known watcher-version and `gh`-path
failures self-heal or signal promptly without silently accumulating retries.

## Relevant public discussions and social search

- **Relevant mise discussions:** [#13189](https://github.com/jdx/mise/discussions/13189)
  is the direct stale-watcher-after-upgrade report and led to PR #13190. Also
  relevant for continuous sync safety, [#13194](https://github.com/jdx/mise/discussions/13194)
  reported a concurrent scratch-index race that could publish false deletions;
  it was fixed in [PR #13195](https://github.com/jdx/mise/pull/13195), included
  in the installed 2026.9.10 release.
- **No direct mise `gh` report found:** GitHub issue and discussion searches of
  `jdx/mise` found no report specifically about a versioned `gh` credential
  helper after a mise upgrade. GitHub CLI maintainers do document/configure
  `gh auth setup-git`, and their public issue shows its expected absolute-path
  helper shape. [GitHub CLI manual](https://cli.github.com/manual/gh_auth_setup-git)
  and [CLI issue #8678](https://github.com/cli/cli/issues/8678).
- **X/Twitter:** current public X searches for the exact mise watcher and stale
  helper phrases produced no attributable relevant post. This is only a search
  result, not proof that no post exists or that X has indexed all public posts.

## Approval-gated follow-up

Implementing the durable repair would change the history origin, managed Git
configuration, and user LaunchAgent configuration. It needs a dated plan and
review before any mutation. The implementation should include a dry-run,
credential-protocol test that never prints secrets, service/status verification,
and a failure-notification test.
