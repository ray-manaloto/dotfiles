# Tool Persistence Matrix

Reference companion to `.devcontainer/AGENTS.md`, which links it by path rather
than carrying it: agnix **AGM-003** caps an `AGENTS.md` at 12,000 characters for
Windsurf compatibility, and a lookup table is exactly the on-demand reference
that belongs in a sibling (same treatment as `tests/TEST-INDEX.md`). See
`.claude/rules/md-size-budgets.md`.

User-overlay paths live on the single **architecture-scoped** home volume
(`dotfiles-<basename>-<user>-<hash>-<arch>-home`, #677); `mise run stop &&
mise run up` preserves all state. Since v6 that includes `~/.cache/uv`,
`~/.local/tmp` (TMPDIR, 30-day atime sweep in `on-create.sh`) and
`~/.bash_history`.

| Tool family | System install (baked) | User overlay | How to add system |
|---|---|---|---|
| mise tools | `/usr/local/share/mise/installs/` | `~/.local/share/mise/installs/` | `mise-system.toml` (base) / `mise-runtime.toml` (runtime) + image PR; overlay tier: `home/dot_config/mise/config.toml.tmpl` |
| cargo crates | `/usr/local/share/cargo/{bin,registry}` | `~/.cargo/{bin,registry}` | base image PR; runtime `cargo install` |
| rust toolchains | `/usr/local/share/rustup/toolchains/` | `~/.rustup/toolchains/` | `mise-system.toml` `rust = "..."`; runtime `rustup install` |
| pipx tools | `/usr/local/share/mise/installs/pipx-*` | shadowed by mise overlay | `"pipx:<name>"` in `mise-system.toml` |
| apt packages | `/usr/{bin,lib,share}/...` | **none — not persistable** | `mise-system.toml [bootstrap.packages]` + base image PR |

**Apt packages have no runtime persistence.** Add system packages to
`mise-system.toml [bootstrap.packages]` and ship via a base-image PR.
`sudo apt install` at runtime works but is lost on container recreate.

**Why the overlay column matters for #677.** Every path in it holds *compiled
output*. Before the home volume carried the architecture, an amd64 and an arm64
container in the same working directory mounted the same volume and interleaved
these trees — docker reuses a named volume on mount and reports nothing, so the
first symptom was an `exec format error` far from its cause.

## Migrating a pre-#677 home volume

`mise run migrate-home-volume` copies `dotfiles-<basename>-<user>-<hash>-home`
into `…-<hash>-<arch>-home`. **Dry-run by default**; `-- --apply` executes. The
source is never deleted — `mise run prune` removes it once the new container is
known good.

It refuses, rather than guessing, in three situations. Each one is a way the
naive version produces a **torn home**: a copy that starts fine and misbehaves
later, which is worse than a copy that fails.

| Refusal | Why | What to do |
|---|---|---|
| `DOTFILES_PLATFORM` unset on a bare CLI call | The old volume name records **no architecture**, so the target would be named for whichever machine happened to ask. Measured: the same command resolves `amd64` under `mise run` (the repo pin) and `arm64` from a bare shell on an M-series Mac. | Run it through `mise run`, or pass `--platform` |
| A container still holds the source | `cp -a` over a home that is being written to captures half-written caches and sqlite files | `mise run stop` first |
| Target populated but **unmarked** | Either a copy that died partway, or a home you already created and worked in via `mise run up`. Nothing on disk tells them apart | Decide: `docker volume rm <target>` if it was a failed copy; skip the migration if it is real work |

**Completion is a marker file, not emptiness.** A successful copy writes
`.dotfiles-migrated-from-pre-677` as its **last** step, inside the same
`sh -c … set -e` as the copy, so it can only appear after `cp` returned 0.
Reading "non-empty" as "done" was the original bug: a copy that died at 90% of a
3.5 GB home leaves a very much non-empty target, which reported
`already-migrated` and would have sent the user into a truncated home.

## Container identity: the id labels, not the name

`@devcontainers/cli` looks an existing container up by `--id-label`, and **with
none supplied it infers one from the workspace folder alone** — read from the
pinned 0.88.0 bundle, `dist/spec-node/devContainersSpecCLI.js`, function `bg`:
it returns early on supplied id labels, otherwise builds
`[devcontainer.local_folder=<folder>]` (+ `config_file`). Both are per-folder.

So the arch-scoped container **name is not enough**: an arm64 `up` in a
directory that already has an amd64 container would find and reuse it and report
success. Every `up`, `dev-rebuild` and `devcontainer exec` therefore passes
`$DEVCONTAINER_ID_FLAGS`, which expands to:

```text
--id-label dotfiles.workspace=<hash> --id-label dotfiles.arch=<arch>
```

Both labels are required together. `--id-label` **replaces** the inferred set
rather than extending it, so the arch label alone would let two clones of this
repo collide; the workspace label is what folder inference used to provide.

`mise run stop` follows from the same fact: a bare
`devcontainer.local_folder=$PWD` filter matches the *other* architecture's
container too, so teardown resolves its targets through `dotfiles-setup
devcontainer teardown` — this architecture's container, plus any pre-#677
leftover this folder owns that carries none of our labels.
