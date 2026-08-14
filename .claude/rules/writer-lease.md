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
/Users/rmanaloto/.local/bin/mise -C <absolute-worktree> run writer-lease-status

/Users/rmanaloto/.local/bin/mise -C <absolute-worktree> run writer-lease-hold -- \
  --task-id <task-or-session-id> --owner codex:<task-or-session-id> \
  --handoff-sha256 <digest> \
  [--expected-prior-receipt-sha256 <receipt-digest>]
```

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

Codex and Claude `PreToolUse` register Bash/unified-exec and direct mutation
tool IDs only for the live owning session/worktree. `PostToolUse` removes that
exact ID, and Claude `PostToolUseFailure` drains failed tools through the same
finish transaction. Codex `write_stdin` publishes the original Bash ID when a
background process finishes, so a clean transfer cannot overtake a delayed
writer.

Only the current immutable generation is retained after its pointer is durable
and validated. It carries the complete canonical audit; superseded generations
are atomically renamed and safely reclaimed through an already-validated state
directory descriptor. Every validation, rename, unlink, and rmdir is relative
to that descriptor and no-follow, so swapping the state pathname to a symlink
cannot redirect cleanup. Cleanup after publication never reverses or denies the
committed transition: retained or malformed tombstones surface as typed
`cleanup_debt` in status and remain preserved for investigation.

Synchronous completion, failure completion, and holder release use bounded
state-lock retry. A transient overlapping hook cannot strand an already-started
tool merely because another state transaction briefly owns the lock.

Never remove or rewrite lease state to recover. Preserve `.omc/`, ignored,
untracked, generated, and dirty bytes. Design and diagrams:
`docs/specs/codex-writer-lease.md`.
