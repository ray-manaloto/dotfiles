# Lane F — firecrawl offline mirror (2026-09-29)

## Log
- firecrawl v1.24.6, authenticated via FIRECRAWL_API_KEY (presence only). Credits before: 1,049 / 1,000 (per `firecrawl --status`), concurrency 0/2.
- Probes (curl, HTTP status): mise.jdx.dev llms.txt 200 (60825 B); llms-full.txt 404 (27150 B is the 404 page); dotfiles.md 404; sitemap.xml 200 (413 URLs); jdx.dev/sitemap.xml 200 (36 URLs). Control: dotfiles.html and bootstrap.html 200.
- Map step skipped in favour of the sitemaps (free, and complete: 413 mise + 36 jdx URLs); `firecrawl map` would have cost credits for the same list.
- Crawl step replaced by per-URL `firecrawl scrape -f markdown --only-main-content` (crawl returns a job with no per-URL control; scrape gave exact file names and per-URL rc).
- Run 1 with `xargs -P2` and no retry hit "Rate limit exceeded (34 req/min)" on ~44 URLs; I killed it, deleted its output, and reran with a 25 s retry-on-rate-limit wrapper, `-P2`. Final: 449/449 scrapes rc=0, 0 failures. Throughput was ~10 pages/min (about 45 min total). Throwaway driver lives in the scratchpad only.
- Second pass (48 URLs missed when I killed the first xargs) re-run: rc=0.
- Linked hop: 8 pages via firecrawl (fnox.jdx.dev, 2 omarchy manual pages, 3 chezmoi pages, gnu stow, yadm), 4 GitHub READMEs via `gh api repos/<r>/readme` (dotbot, mackup, dotstate, rcm), all rc=0. No GitHub PRs/issues are cited by the three target pages.
- Credits: before 1,049/1,000 (status text as printed), after 568/1,000 => about 481 used, including the wasted first run (~80) and retries.

## Page counts per target
- jdx-posts/: 36 files (posts index, home, every post in sitemap; 15 of them are stubs under 300 B because old posts/categories/tags/contact pages are redirects or empty).
- mise-docs/: 414 files (413 sitemap URLs + `_llms.txt`), includes dotfiles.md and bootstrap.md.
- linked/: 12 files.
- Total: 463 files including INDEX.md, 4.3 MB (well under the 40 MB stop line).
- Index: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/raw/mise-dotfiles-2026-09-29/INDEX.md (462 URL rows + failure notes).

## Digest of dotfiles.html, bootstrap.html and the blog post
1. Feature is `mise dot ...` (alias of dotfiles) driven by a `[dotfiles]` table in mise config; blog post is Sept 7 2026 "Dotfiles That Save Themselves".
2. Track a live file in place: `mise dot track ~/.zshrc` writes `[dotfiles]` / `"~/.zshrc" = { mode = "track" }` to `~/.config/mise/config.toml`; a checkpoint history lives in a bare repo at `~/.local/state/mise/history/repo.git`.
3. Autosave needs a service: `[bootstrap.services.mise-history]` / `builtin = "history-watch"`, then `mise bootstrap` (LaunchAgent on macOS, systemd user unit on Linux, Scheduled Task on Windows).
4. Modes: `symlink` (default), `symlink-each`, `copy`, `template` (Tera, `source = "dotfiles/gitconfig.tera"`), `absent`. Example: `"~/.config/nvim" = { source = "dotfiles/nvim", mode = "symlink" }`.
5. Per-OS/profile: `variants = [{ os = "macos", target = "~/Library/..." }, { os = "linux", target = "~/.config/..." }]`, also `{ profile = "work", ... }` and `{ default = true }`; unmatched machines skip the entry.
6. Commands: `mise dot status [--missing]`, `diff`, `apply [--dry-run|--yes|--force]`, `unapply`, `track/untrack`, `add [--changed]`, `edit [--apply]`, `save`, `history`, `paths`.
7. Secrets: `[history.encryption]` / `recipients = [...]` plus `{ mode = "track", encrypt = true }`; must be configured before first capture; also points to mise env secrets and fnox.
8. Bootstrap: `mise bootstrap` applies packages/files/services/repos/shell/tools and a final task; e.g. `[bootstrap.mise_shell_activate]` / `zprofile = "shims"` / `zshrc = "activate"`; `mise bootstrap --dry-run`, `status`, `--yes`.
9. Global config from a repo: `mise bootstrap --adopt example/mise-config` clones into `$MISE_CONFIG_DIR` (`~/.config/mise`); config.toml, config.work.toml (`-E work`), conf.d/, tasks/ stay live.
10. Self-managing pattern: `[settings]` / `dotfiles.root = "~/.dotfiles"` and `[dotfiles]` / `"~/.dotfiles" = "~/src/dotfiles"` / `"~/.config/mise/config.toml" = "~/src/dotfiles/mise/config.toml"` (repo must exist before first apply).

## GitHub repos touched
- [anishathalye/dotbot](https://github.com/anishathalye/dotbot) — README saved (post comparison table)
- [lra/mackup](https://github.com/lra/mackup) — README saved
- [serkanyersen/dotstate](https://github.com/serkanyersen/dotstate) — README saved
- [thoughtbot/rcm](https://github.com/thoughtbot/rcm) — README saved
- [jdx/mise](https://github.com/jdx/mise) — docs site mirrored (mise.jdx.dev)
