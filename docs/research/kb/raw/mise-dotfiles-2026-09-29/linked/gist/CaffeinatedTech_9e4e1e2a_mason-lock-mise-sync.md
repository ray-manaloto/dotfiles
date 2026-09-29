# Sync Neovim Mason packages across machines

- https://gist.github.com/CaffeinatedTech/9e4e1e2a63781256483701b6e334b298

## nvim-mason-sync.md

```
# Syncing Neovim's Mason packages across machines

## The problem

[mason.nvim](https://github.com/williamboman/mason.nvim) installs LSP servers, linters, and formatters as prebuilt binaries under `~/.local/share/nvim/mason/`. These are:

- **platform-specific** — never sync that directory between machines
- **invisible to your config** — `~/.config/nvim` syncs fine, but a new machine starts with zero Mason packages
- **unlocked** — `lazy-lock.json` pins plugins, but Mason has no lockfile, and `ensure_installed` lists are hand-maintained and always drift from what you actually installed

## The solution

[`zapling/mason-lock.nvim`](https://github.com/zapling/mason-lock.nvim) plus a small startup hook:

- Every install/update/uninstall done through the normal `:Mason` UI automatically rewrites `mason-lock.json` (pinned versions) inside your config dir.
- At startup, a tiny autocmd compares the lockfile to what's installed locally and **installs only the missing packages** at their pinned versions. Otherwise it's a no-op.
- Since the lockfile lives in `~/.config/nvim`, any dotfile sync (git, mise sync, stow, …) covers it.

`lua/plugins/mason-lock.lua`:

```lua
return {
  -- mason lockfile: installing/updating via :Mason updates mason-lock.json,
  -- which is synced with your dotfiles; :MasonLockRestore reinstalls everything
  -- at pinned versions
  {
    "zapling/mason-lock.nvim",
    config = function()
      local mason_lock = require("mason-lock")
      mason_lock.setup({})

      -- auto-install packages listed in the lockfile but missing on this machine,
      -- so a synced config converges without running :MasonLockRestore
      vim.api.nvim_create_autocmd("VimEnter", {
        once = true,
        callback = function()
          local ok, registry = pcall(require, "mason-registry")
          if not ok then
            return
          end
          local ok_read, lock_data = pcall(mason_lock.read_file, mason_lock.lockfile_path)
          if not ok_read then
            return
          end
          local ok_json, packages = pcall(vim.json.decode, lock_data)
          if not ok_json or type(packages) ~= "table" then
            return
          end

          local missing = {}
          for name, version in pairs(packages) do
            local ok_pkg, pkg = pcall(registry.get_package, name)
            if ok_pkg and not pkg:is_installed() then
              table.insert(missing, { name = name, version = version, pkg = pkg })
            end
          end
          if #missing == 0 then
            return
          end

          vim.notify(("[mason-lock]: installing %d missing package(s) from lockfile..."):format(#missing))
          local done = 0
          for _, m in ipairs(missing) do
            local handle = m.pkg:install({ version = m.version })
            handle:once("closed", function()
              done = done + 1
              if done == #missing then
                vim.notify(("[mason-lock]: finished installing %d missing package(s)"):format(#missing))
              end
            end)
          end
        end,
      })
    end,
  },
}
```

## Workflow

1. Install/update/remove tools with `:Mason` as always — the lockfile updates itself.
2. Sync `~/.config/nvim` with your dotfile tool of choice.
3. On the other machine, just open Neovim: missing packages install automatically at the pinned versions (with a notification). In steady state, nothing happens.
4. Optional commands: `:MasonLock` re-snapshots everything, `:MasonLockRestore` force-reinstalls all packages at exact versions (e.g. to repair a broken install).

## Notes

- Requires [lazy.nvim](https://github.com/folke/lazy.nvim) and mason.nvim v2. LazyVim users: drop the file into `lua/plugins/`.
- The startup hook only fills gaps — it never upgrades or reinstalls packages already present.
- Packages that only publish rolling builds (e.g. `ols` ships only `nightly` in the Mason registry) can be pinned properly by a machine-level tool manager like [mise](https://mise.jdx.dev/) instead, and excluded from Mason.

```
