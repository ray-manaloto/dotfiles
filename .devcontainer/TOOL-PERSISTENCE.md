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
