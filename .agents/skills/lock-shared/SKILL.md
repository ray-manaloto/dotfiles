---
name: lock-shared
description: Regenerate the SHARED host<->image lockfile (`.config/mise/mise.lock`) via `mise run lock-shared -- "<tool>"`, resolving linux assets natively by routing into the devcontainer. Use whenever a tool in `.config/mise/conf.d/shared.toml` is bumped, when a linux runner reports a tool missing after a lockfile refresh that looked clean locally, or when `mise run lint`'s `mise_lock_integrity` step flags this file. Reach for it INSTEAD of `mise run lock` for anything in the shared fragment — `lock` resolves on the host, and macOS picks a different release asset than linux does for at least one tool, writing an entry that is wrong only on the platform no local gate exercises.
user-invocable: true
---

# lock-shared: regenerating the shared host↔image lockfile

`mise run lock-shared -- "<tool>"` is the whole mechanic. It validates the
name against `shared.toml`, routes into the devcontainer when this host
cannot resolve linux assets, and verifies platform coverage afterwards. The
recipe lives in `python/src/dotfiles_setup/lock_shared.py`; the task is a thin
caller (`.Codex/rules/zero-bash-logic.md`).

```bash
mise run lock-shared -- "uv"              # derive host capability, auto-route
mise run lock-shared -- "uv" "yq" "bun"   # several at once
mise run lock-shared -- --no-container "uv"   # fail instead of routing
```

This file carries only the judgement: which artifact you are touching, and the
ways a regen goes wrong while looking like success.

## Which artifact — three lockfiles, three owners

| You changed | Task | Artifact |
|---|---|---|
| a HOST-only tool in `mise.toml` | `mise run lock -- "<backend/name>"` | `mise.lock` |
| a tool in `.config/mise/conf.d/shared.toml` | **`mise run lock-shared -- "<tool>"`** | `.config/mise/mise.lock` |
| `.devcontainer/mise-system.toml` / `mise-runtime.toml` | `mise run lock-image` | the two image locks |

`shared.toml` is merged into BOTH the host config and the image config, so a
bump there needs **`lock-shared` AND `lock-image`** — they write different
files and neither covers the other. `lock-image` touches only the two
`.devcontainer/*.lock` files; it will never repair `.config/mise/mise.lock`.

Bare `mise lock` is never the answer for any of them: it re-locks the whole
file for the current platform. See `.Codex/rules/do-not.md` and
`feedback_mise_lock_whole_file_is_destructive`.

## Why routing exists: the asset is chosen by the RESOLVING host

mise resolves a **different release asset** per resolving host for at least
one shared tool. Measured 2026-08-27: `mise run lock -- uv` on macOS wrote

    uv-x86_64-unknown-linux-gnu.tar.gz

into the `linux-x64` entry, while mise on linux resolves the **musl** asset
for that same entry and derives the installed binary path from the asset
name. A linux runner then downloads the gnu tarball, extracts it to a
gnu-named directory, looks under the musl path, and reports `uv: not found` —
which cascades into ~18 red hk steps.

**Every local gate passes**, because macOS exercises the macOS entries. A
platform key holding wrong-host content is invisible to a coverage check: the
entry is present and well-formed, just wrong. That is why this task exists
rather than a rule saying "remember to lock on linux".

Control arm worth knowing: bun, hk, pixi and yq re-locked on linux produce
URLs **identical** to macOS, so this is specific to uv's aqua package, not a
blanket macOS problem. Do not generalise it into "macOS cannot lock".

## The trap routing creates: the container's settings are not yours

Inside the devcontainer mise reads `.devcontainer/mise-system.toml`, whose
settings are tuned for **building the image**, not for maintaining this
lockfile. Two of them are actively harmful here, and the task overrides both
via `--remote-env`:

| Setting | Image value | Effect on `.config/mise/mise.lock` |
|---|---|---|
| `lockfile_platforms` | `["linux-x64","linux-arm64"]` | truncates every re-locked tool **11 platforms → 2**, dropping the macOS/windows entries the host installs from |
| `github_attestations` | `false` | re-locks without provenance; mise then refuses to replace an attested entry, reporting a **possible supply chain attack** on a release that is properly attested |

Both were measured with isolating arms: the full platform set alone still
fails (rc=1); attestations alone still truncates. If you ever see either
symptom, check that these overrides are still in `_lock_command` before
suspecting upstream — a real supply-chain warning and this false one look
identical in the log.

The platform set is derived from the committed lockfile, never hard-coded, so
it cannot drift into being an eleventh place to update.

## Reading the result — rc=0 is not enough

- **`lock-integrity OK: every lockfile kept its platform coverage`** must
  appear. Without it, coverage was lost; repair with `git checkout --` on the
  lockfile and re-run scoped, never by hand-editing.
- **`No tools configured to lock`** with rc=0 means it locked *nothing* —
  the name was not recognised, or `MISE_IGNORED_CONFIG_PATHS` still hid the
  fragment. The task fails on this deliberately.
- **Use the FULL key** as written in `shared.toml`. A bare short name for a
  backend-qualified tool exits 0 having done nothing.
- A name from the ROOT `mise.toml` (`aws-cli`, `conda:ffmpeg`) is refused
  here on purpose — locking it would write the wrong file.

## See also

- `.Codex/skills/lock-image/SKILL.md` — the sibling task and its own traps.
- `.Codex/rules/do-not.md` — bare `mise lock` / `mise install` are destructive.
- `python/src/dotfiles_setup/lock_shared.py` — the recipe and its full history.
