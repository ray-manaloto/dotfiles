---
status: accepted
---

# Dependency maps: SCIP computes blast radius, cbm is for browsing, each machine builds its own

A dependency map is built on each machine from the dependency's tagged source, at the version that
machine pins. A person runs `mise run //depmaps:sync` by hand, after `mise bootstrap` has installed the
tools; it keeps the maps outside the repo, in `~/.local/share/dep-maps` and cbm's own cache. Nothing syncs a
map between machines.

Bootstrap does not make the maps. A `[bootstrap.hooks.post-tools]` entry did, until it put about 20 s per
dependency, and a dependency on the live cbm daemon, on every bootstrap and every `//depmaps:test` run.
The package keeps its tasks. Its `test` task runs the real cbm with a cache and daemon of each test's own,
and is left out of `mise run test`.

We chose this because a map is too big to carry: mise's cbm artifact is 30.6 MB, and mise dotfiles'
private history leaves out any file over 16 MiB (`crates/mise-system/src/history/shadow.rs:25`,
enforced at `tracked.rs:1217`, mise v2026.11.2). A map also has to follow the machine's own pins, and
rebuilding one from the tag takes about 20 s for mise.

## Two engines, two jobs

- **cbm** maps every language it parses, so it is the map for browsing a dependency and for the
  function and file diff between two versions (`//depmaps:diff`).
- **SCIP** (rust-analyzer for Rust) computes the blast radius: its references are resolved by type,
  where cbm resolves a call such as `default()` by name and links callers to every function of that
  name.

## Considered options

- **Carry the maps in mise dotfiles' private history and sync them.** Refused: the artifact is over
  the per-file limit, and a synced map can be for a version the machine does not pin.
- **cbm alone for blast radius.** Refused: its name-resolved calls make unrelated functions reach each
  other, so the radius is mostly noise for common method names.
