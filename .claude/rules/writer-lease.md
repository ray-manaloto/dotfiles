# Repository writer lease

Before the first repository mutation in a Codex or Claude task, establish one
live lease for this Git common directory:

1. Run the pinned status bootstrap printed below, substituting the absolute
   worktree path. A bare `mise`, `env`, PATH override, compound command, or
   different argv is denied before ownership.
2. After the handoff is acknowledged, the predecessor is idle, and the
   coordinator sends START, retain the pinned `writer-lease-hold` command in a
   foreground execution session. Supply the exact prior receipt digest after
   any earlier owner; do not label the transition yourself.
3. Keep the holder alive until commit or safe transfer. It drains every active
   mutating tool before recording release and dropping the OS lock.

```text
# Darwin host
<absolute-home>/.local/bin/mise -C <absolute-worktree> run writer-lease-status

<absolute-home>/.local/bin/mise -C <absolute-worktree> run writer-lease-hold -- \
  --task-id <task-or-session-id> --owner codex:<task-or-session-id> \
  --handoff-sha256 <digest> \
  [--expected-prior-receipt-sha256 <receipt-digest>]

# Supported Linux devcontainer
/usr/local/bin/mise -C <absolute-worktree> run writer-lease-status

/usr/local/bin/mise -C <absolute-worktree> run writer-lease-hold -- \
  --task-id <task-or-session-id> --owner codex:<task-or-session-id> \
  --handoff-sha256 <digest> \
  [--expected-prior-receipt-sha256 <receipt-digest>]
```

On Darwin, resolve the current account's `$HOME` once and substitute its
literal absolute value for `<absolute-home>` before invocation. Do not leave
`$HOME`, `~`, `env`, or a `PATH` lookup in the executed bootstrap command.
No other mise location is accepted on either platform.

For a manual cooperative control, `mise run writer-lease-check -- --task-id
<same-id> --handoff-sha256 <same-digest>` verifies the holder challenge,
receipt, worktree, task, and handoff. Native hooks remain the enforcement seam.

The state directory is private to the current user. Lock, current-pointer,
receipt, audit, and in-flight paths must be owned regular files opened without
following symlinks. Receipt, canonical audit, and active-tool state publish as
one content-addressed generation through an atomic pointer. `status` never
creates or changes state.

The retained `fcntl.flock` excludes registered worktrees. A loopback
challenge token binds the receipt to the process holding that lock, so a stale
receipt plus an unrelated flock cannot impersonate its owner. Audit facts—not
a caller flag—derive `initial`, clean `handoff`, or stale-owner `recovery`.
Recovery refuses while an in-flight mutation remains recorded.

Repository identity uses one platform-exclusive executable: Darwin accepts
only `/usr/bin/git`; Linux accepts only the conda-Git path derived from the
tracked `.devcontainer/mise-system.lock`. There is no cross-platform fallback
and no ambient `PATH` lookup.

Codex runs hook commands from the session working directory, which may be any
repository subdirectory or a checkout nested beneath an unrelated Git
repository. The pinned system-Python hook command therefore walks ancestors
and requires exactly one Git marker whose marker and every path component to
the regular tracked runner and hook entrypoint can be opened descriptor-relative
with `O_NOFOLLOW`. Missing or ambiguous complete candidates exit `2` before
mutation. The locator binds the selected root inode and executes the runner
bytes read from the admitted descriptor; the runner independently binds the
payload root and passes the already-open hook entrypoint to project Python.
Neither stage invokes Git, mise, `env`, or ambient `PATH` during location.

Codex and Claude `PreToolUse` register Bash/unified-exec and direct mutation
tool IDs only for the live owning session/worktree. `PostToolUse` removes that
exact ID, and Claude `PostToolUseFailure` drains failed tools through the same
finish transaction. Codex `write_stdin` publishes the original Bash ID when a
background process finishes, so a clean transfer cannot overtake a delayed
writer.

Only the current immutable generation is retained after its pointer is durable
and validated. Its audit head contains at most 64 open events and links private,
immutable, content-addressed 64-event chunks; reconstruction validates the
complete sequence. Each transition therefore rewrites a bounded tail while
sealed history is written once. Superseded generations are atomically renamed
and safely reclaimed through an already-validated state directory descriptor.
Every state/chunk validation, rename, unlink, and rmdir is relative to a private
no-follow descriptor, so swapping the state pathname to a symlink cannot
redirect cleanup. Cleanup after publication never reverses or denies the
committed transition: retained or malformed tombstones surface as typed
`cleanup_debt` in status and remain preserved for investigation.

Each hook invocation may validate at most 8 MiB of sealed audit-chunk bytes.
Every chunk is admitted by descriptor metadata against the remaining budget
before a size-exact bounded read; growth or replacement fails closed. Crossing
that ceiling denies before state mutation. The 256-pair real replay
measured 35,822,208 cumulative sealed-chunk bytes across 512 hooks, 161,662
final state bytes, and 77.10 seconds on the Darwin host; the ceiling bounds one
hook's read even though complete-history validation intentionally rereads the
content-addressed chain.

Synchronous completion, failure completion, and holder release use bounded
state-lock retry. A transient overlapping hook cannot strand an already-started
tool merely because another state transaction briefly owns the lock.

Never remove or rewrite lease state to recover. Preserve `.omc/`, ignored,
untracked, generated, and dirty bytes. Design and diagrams:
`docs/specs/codex-writer-lease.md`.
