---
name: lock-image
description: Regenerate the devcontainer IMAGE lockfiles (`.devcontainer/mise-system.lock` + `mise-runtime.lock`) via `mise run lock-image`. Use whenever a change to `.devcontainer/mise-system.toml`, `.devcontainer/mise-runtime.toml` or `.config/mise/conf.d/shared.toml` needs its locks refreshed, when `mise run lint`'s `mise_lock_integrity` step or CI reports the image locks stale or short, or when you are about to transcribe the recipe out of `.github/actions/lock-refresh/action.yml` by hand. Reach for it BEFORE hand-rolling `mise lock` against a staged config — regenerating these two files on macOS truncates them silently, and the tool count does not move, so the damage reads as success.
user-invocable: true
---

# lock-image: regenerating the devcontainer image locks

`mise run lock-image` is the whole mechanic. It stages the image's merged
config, installs the image's **pinned** mise, converges under GitHub rate
limits, and collects only after verifying platform coverage against `HEAD`.
The recipe lives in `python/src/dotfiles_setup/image_lock.py`; the task is a
thin caller (`.Codex/rules/zero-bash-logic.md`).

```bash
mise run lock-image                            # derive platforms, auto-route
mise run lock-image -- --platform linux-x64    # narrow it deliberately
mise run lock-image -- --no-container          # refuse rather than route
mise run lock-image -- --stage /path/to/stage  # resume a rate-limited run
```

This file carries only the judgement: which artifact you are touching, and the
three ways a regen goes wrong while looking fine.

## Which artifact — `lock` and `lock-image` are different files

| You changed | Task | Artifact |
|---|---|---|
| a HOST-only tool in `mise.toml` | `mise run lock -- "<backend/name>"` | `mise.lock` |
| a tool in `shared.toml` | `mise run lock-shared -- "<tool>"` | `.config/mise/mise.lock` |
| `.devcontainer/mise-system.toml` or `mise-runtime.toml` | `mise run lock-image` | the two image locks |
| `shared.toml` (merged into BOTH) | `lock-shared` **and** `lock-image` | both |

`shared.toml` is the one that catches people: it is merged into the image
config *and* read on the host, so a bump there leaves the image locks stale
even after a clean `mise run lock-shared`.

**A shared tool is `lock-shared`'s, not `lock`'s.** `mise run lock` resolves
on THIS host, and macOS picks a different release asset than linux for at
least one shared tool — an entry that is wrong only on the platform no local
gate exercises. See `.Codex/skills/lock-shared/SKILL.md`.

Bare `mise lock` is never the answer for either — it re-locks the whole file
for the current platform. `.Codex/rules/do-not.md` and
`feedback_mise_lock_whole_file_is_destructive` carry that.

## Three ways a regen looks fine and is not

Each of these cost a cycle to learn, and each produces a lockfile that parses,
commits, and passes a naive check.

**macOS cannot write linux conda checksums** (jdx/mise#7700). A regen on
darwin drops the linux entries — measured 2026-08-08, `mise-system.lock`'s
`linux-x64` occurrences went 131 → 64 and `mise-runtime.lock`'s 35 → 12 —
while the **tool count stayed at 49 and 22**. That is why the old collect step
returned `rc=0` on it (#648). The task routes into the amd64 devcontainer by
default rather than refusing, so the normal answer on this Mac is to run it and
let it route; `--no-container` turns the routing into a loud refusal when you
want to know rather than to fix.

**A `linux-x64`-only pass loses the macOS entries of any BUMPED tool.** The
committed lock carries six platforms, 29 of them `macos-x64` tool entries, and
they survive only because the committed lock is seeded in as a starting point.
Bump a tool and its entries are replaced, so `lock-check` then fails with
`tool uv: lost platform(s) ['macos-x64']`. The task derives the platform set
from the committed lock for exactly this reason — pass `--platform` only when
you have decided to narrow it, never to reproduce what CI's workflow file does.

**A short lock is the expected mid-run state, not a failure.** `mise lock`
resolves through GitHub and anonymous quota runs out partway, which is what the
convergence loop is for. Only the last pass has to succeed. If every pass
fails, a tool is genuinely unresolvable — `mise lock` has hard-errored on that
since 2026.6.13, so read the error rather than raising `--passes`.

## Reading the result

Success prints the mise version and the platform count, and means the coverage
check passed against `HEAD` — not merely that the file was written. Two exits
worth distinguishing:

- **`LOST platform coverage`** — the regen truncated. The file on disk is
  untouched; nothing landed. Almost always the wrong host, so re-run without
  `--no-container`.
- **`missing tools`** — the stage lock does not cover the merged config. A
  config edit that never reached the stage, or an interrupted run.

Then confirm with the gate the rest of the repo uses:

```bash
uv run --project python dotfiles-setup lock-check
```

## Adding a platform on purpose

Widening coverage is a real change, not drift: the first regen that adds a
platform makes it part of the committed lock, and every later run derives it
automatically. Nothing needs editing to make that stick — which also means an
*accidental* widening becomes permanent silently, so say in the commit body
that you meant it.
