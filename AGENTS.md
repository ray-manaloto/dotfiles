# dotfiles2

A mise monorepo for TypeScript (Claude Code mods), Python and C++.

- Root `mise.toml` declares the monorepo roots and one locked toolset; `mise.lock` covers
  macos-arm64, linux-x64 and linux-arm64.
- `mise run test` runs every root's `test` task; the root task lists them in `depends`
  (`//...:test` would include the root task itself and recurse).
- Roots: `typescript/` (bun), `python/` (uv project), `cpp/` (CMake presets, C++26).
- `.gitignore` is an allowlist. A new top-level path must be added there on purpose; never
  add keys, `age.txt` or any secret file.
