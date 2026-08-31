# SPEC — restore agnix's dropped `provenance_verified` on linux-x64

## 1. Objective

`mise.lock`'s agnix `platforms.linux-x64` entry must carry
`provenance_verified = true` again, as it did before commit `b75fa3b`.

The failure this prevents: `agnix . --strict` runs in CI on **GitHub's linux
runners** (`ci.yml:151-154`), so linux-x64 is the platform actually executed.
Its lock entry currently records `provenance = "github-attestations"` with no
verification flag — the supply-chain attestation record for the executed
platform was silently lost.

## 2. Files

- `mise.lock` — the agnix `platforms.linux-x64` entry, via a lock task only

Expect NO other file to change. If your fix requires touching another file,
stop and report why before doing it.

## 3. Interfaces — the exact end state

```toml
[tools."github:agent-sh/agnix"."platforms.linux-x64"]
checksum = "sha256:46486fef7baa22d8ecbce3620dd5fee44055c237329a86c17c5d55333d3b3ecd"
url = "https://github.com/agent-sh/agnix/releases/download/v0.52.1/agnix-x86_64-unknown-linux-gnu.tar.gz"
url_api = "https://api.github.com/repos/agent-sh/agnix/releases/assets/532200867"
provenance = "github-attestations"
provenance_verified = true
```

The checksum, url and url_api above are what the entry ALREADY has and what it
had before `b75fa3b` — byte-identical. **Only the missing
`provenance_verified = true` line is at issue.** If your fix changes the
checksum or URL, something is wrong — stop and report.

The `macos-arm64` entry already has `provenance_verified = true` and had it
before; do not disturb it.

## 4. Constraints and invariants

**C1 — do NOT hand-edit `mise.lock`.** `.claude/rules` and the repo's own
convention forbid hand-editing lockfiles. The flag must be produced by mise
resolving the entry, not typed in.

**C2 — the flag is PLATFORM-LOCAL to the resolving host.** mise can only set
`provenance_verified` for a platform whose attestation it can verify from the
executing machine. That is exactly why `b75fa3b` lost it: the block was deleted
and re-resolved from this **macOS** host. So a fix that re-locks from macOS
again will reproduce the bug. Verified in this repo's own doctrine: `mise run
lock-shared` exists precisely because "mise resolves a different release asset
on macOS than on linux", and it routes into the amd64 devcontainer.

**C3 — investigate the right mechanism before acting; do not guess.**
Candidates, in the order worth trying:
  (a) a linux-native re-lock of this one tool — note `mise run lock-shared`
      targets `.config/mise/mise.lock` (the SHARED fragment), and agnix is a
      **host-only** tool in `mise.toml` (`:493` documents agnix as host-only),
      so `lock-shared` may not apply as-is. Read
      `python/src/dotfiles_setup/lock_shared.py` and the `lock`/`lock-shared`
      tasks (`mise.toml:1198`, `:1212`) before choosing.
  (b) running the scoped `mise run lock -- "github:agent-sh/agnix"` from INSIDE
      the amd64 devcontainer (the container bind-mounts this workspace, so it
      writes the same `mise.lock`).
  (c) `git checkout b75fa3b~1 -- mise.lock` to recover the pre-loss bytes, then
      re-apply ONLY the intended version-field change from `b75fa3b`. Note this
      would also revert the aws-cli 2.36.35 bump and the rumdl/agnix bare
      `version` fields that `b75fa3b` legitimately produced, so it needs care —
      it is a last resort, not a first move.

**If none of these can restore the flag, that is a legitimate outcome** —
report it with the evidence and the mechanism that prevents it, and leave the
lock as it is. Do not fabricate the flag by hand to make the diff look right.

**C4 — never a bare `mise lock` or `mise install`** — whole-file re-lock,
destructive on this macOS host. Named tools only.

**C5 — the definition of done must not regress.** After your change:

```
mise outdated -b --local     # must stay "All tools are up to date", rc=0
```

**C6 — this host's shell PATH is STALE.** Bare `hk` resolves 1.56.1 while the
repo pins 1.57.0, which false-fails `tests/test_hk_builtins_audit.py`. Run every
gate through `mise exec -- sh -c '...'`.

**C7 — no inline lint suppressions** (`noqa`, `type: ignore`, `nosec`).

**C8 — commit on the current branch `chore/deps-currency-20260831`**, HEAD
`b03de55`, tree clean. Do not create a branch, do not push, do not open a PR.
**Stage by name — never `git add -A`**: untracked `.agents/skills/**` and
`.omc/` directories exist in this working tree and must NOT be committed
(`do-not.md` #5; a bulk add already swept 35 unintended files once today).

## 5. Verification

```
mise outdated -b --local
```

must stay clean, plus all four gates under `mise exec`, each rc=0:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly; never pipe a gate into `tail`/`head`.

**And show the restored entry**: print the agnix `platforms.linux-x64` block
and confirm `provenance_verified = true` is present, with the checksum
unchanged from §3.

## 6. Commit

`COMMIT: lane`. The commit message must state plainly that this restores an
attestation record dropped by `b75fa3b`, and why it was dropped
(host-side re-lock cannot verify another platform's attestation).

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | Before `b75fa3b`, agnix `platforms.linux-x64` carried `provenance = "github-attestations"` AND `provenance_verified = true`; after, only `provenance` remains — `git show b75fa3b~1:mise.lock` vs current `mise.lock`, both read this session |
| 2 | L | The entry's `checksum`, `url` and `url_api` are byte-identical before and after — read this session |
| 3 | L | agnix `platforms.macos-arm64` has `provenance_verified = true` and had it BEFORE `b75fa3b` too — it did not "gain" the flag; read this session |
| 4 | L | `rumdl`, re-locked identically in the same commit, has NO `provenance_verified` before or after — control arm proving this is not a blanket relock side effect; read this session |
| 5 | L | `ci.yml:151-154` runs `agnix . --strict` on GitHub linux runners; `mise.toml:1195-1196` is the local parity task — read this session |
| 6 | L | `mise.toml:493` documents agnix as a host-only tool — read this session |
| 7 | I | `mise run lock-shared` routes into the amd64 devcontainer because mise resolves a different release asset on macOS than on linux; it targets `.config/mise/mise.lock` — `mise.toml:1212-1216` |
| 8 | I | `mise run lock` re-locks NAMED tools only; a bare `mise lock` is destructive on this host — `mise.toml:1198-1201` |
| 9 | A | That `provenance_verified` can only be set for a platform verifiable from the executing host is INFERRED from the observed before/after asymmetry (macOS kept its flag, linux lost its) — it is not read from mise's source. Verify it before relying on it to choose a fix. |
| 10 | A | Whether mise re-verifies attestation at install time when the flag is absent, or silently skips verification, is UNKNOWN. It determines how severe this is, but not whether to fix it. |
