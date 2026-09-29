<!-- source: https://github.com/iainsimmons/today-iain-learned/blob/HEAD/src/content/posts/managing-dotfiles-with-mise.md ; fetched 2026-09-29 via gh api contents (lane X) -->
---
title: Managing dotfiles with mise
date: 2026-09-25
description: "today iain learned: How to manage dotfiles, installed tools and packages with mise"
tags:
  - dotfiles
  - linux
  - macos
  - productivity
  - tools
  - CLI
hideTOC: false
draft: false
atUri: "at://did:plc:aoqs4f5ru6ztomatyvept7bf/site.standard.document/3mwdgmmrd7y2p"
---

I recently replaced my old [GNU Stow](https://www.gnu.org/software/stow/) dotfiles setup and its multiple Git branches (per OS/machine) with a consolidated [mise bootstrap and dotfiles](https://mise.jdx.dev/bootstrap.html) setup.

I now manage my dotfiles, installed tools (like Node.js, Go, Python, etc), packages (CLIs/TUIs, etc) and other configuration across both operating systems (macOS and Omarchy/Arch Linux) and multiple machines that I use.

Configs are now in `~/.config/mise/`, including a shared `config.toml`, `config.linux.toml` for Omarchy/Arch Linux and `config.macos.toml` for macOS, automatically loaded via [mise's `auto_env`](https://mise.jdx.dev/configuration/environments.html#platform-environments). My old `custom-omarchy-install.sh` shell script became the mise bootstrap packages and tasks sections. See my [dotfiles Setup section](https://github.com/iainsimmons/dotfiles#setup).

## Tools

mise can manage tools (mostly for development work) in one section of the configuration:

```toml title="~/.config/mise/config.toml"
[tools]
gh = { version = "latest", os = ["linux"] }
go = "latest"
"github:joshmedeski/sesh" = "latest"
node = "24"
nub = "latest"
opencode = { version = "latest", os = ["linux"] }
python = "3.14.4"
"aqua:modem-dev/hunk" = "latest"
"npm:playwright" = "latest"
codex = "latest"
```

Here you can see there are a few sources of supported tools that can be managed this way, including GitHub, npm and Aqua. See [Backends](https://mise.jdx.dev/dev-tools/backends/) for more info and other available sources.

`mise upgrade` for upgrading tools respects the configured version range, so pinned tools (e.g. `node = "24"` and `python = "3.14.4"`) stay as they are (or only upgrade minor/patch versions in the case of Node.js). `mise upgrade --bump` updates the pinned version.

## Packages

The OS-specific configs use the corresponding package managers (Pacman/AUR on Arch Linux, [Homebrew](https://brew.sh/) on macOS) and the installed packages can differ without me having to manage different setups in different git branches. I used to use [Homebrew Bundle](https://docs.brew.sh/Brew-Bundle-and-Brewfile) to manage bulk-installing packages on macOS, and a custom bash script to install packages on Arch via [yay](https://github.com/jguer/yay).

Here are some examples, first for Linux:

```toml title="~/.config/mise/config.linux.toml"
[bootstrap.packages]
"pacman:fish" = "latest"
"pacman:kitty" = "latest"
"pacman:tmux" = "latest"
"pacman:tree-sitter-cli" = "latest"
"pacman:yazi" = "latest"
"pacman:eza" = "latest"
"pacman:fx" = "latest"
"pacman:gum" = "latest"
"pacman:7zip" = "latest"
"pacman:diff-so-fancy" = "latest"
"pacman:fastfetch" = "latest"
"pacman:uwsm" = "latest"
"pacman:walker" = "latest"
"aur:ov" = "latest"
"aur:hyprmoncfg" = "latest"
"aur:helium-browser-bin" = { os = "linux" }
"aur:vesktop-bin" = { os = "linux" }
"aur:bibata-cursor-theme-bin" = { os = "linux" }
"aur:pnpm-bin" = "latest"
```

And then macOS:

```toml title="~/.config/mise/config.macos.toml"
[bootstrap.brew.taps]
"asmvik/formulae" = "https://github.com/asmvik/homebrew-formulae.git"
"brevity1swos/tap" = "https://github.com/brevity1swos/homebrew-tap.git"
"jesseduffield/lazydocker" = "https://github.com/jesseduffield/homebrew-lazydocker.git"
"jesseduffield/lazygit" = "https://github.com/jesseduffield/homebrew-lazygit.git"
"noahgorstein/tap" = "https://github.com/noahgorstein/homebrew-tap.git"
"noborus/tap" = "https://github.com/noborus/homebrew-tap.git"

[bootstrap.packages]
"brew:bat" = "latest"
"brew:eza" = "latest"
"brew:fastfetch" = "latest"
"brew:fd" = "latest"
"brew:fish" = "latest"
"brew:fx" = "latest"
"brew:fzf" = "latest"
"brew:gum" = "latest"
"brew:jq" = "latest"
"brew:lazygit" = "latest"
"brew:miller" = "latest"
"brew:neovim" = "latest"
"brew:ov" = "latest"
"brew:ripgrep" = "latest"
"brew:starship" = "latest"
"brew:tmux" = "latest"
"brew:tree-sitter-cli" = "latest"
"brew:yazi" = "latest"
"brew:zoxide" = "latest"
# From taps.
"brew:asmvik/formulae/skhd" = "latest"
"brew:brevity1swos/tap/rgx" = "latest"
"brew:jesseduffield/lazydocker/lazydocker" = "latest"
# Homebrew casks (macOS-only GUI apps and fonts).
"brew-cask:1password-cli" = { os = "macos" }
"brew-cask:espanso" = { os = "macos" }
"brew-cask:font-symbols-only-nerd-font" = { os = "macos" }
"brew-cask:notunes" = { os = "macos" }
```

## Dotfiles / Configuration

mise puts your dotfiles (configuration files) in the appropriate destination using [one of five modes](https://mise.jdx.dev/dotfiles.html#modes), with the default being to symlink entire directories (can be changed). It sources the directories and files to move/create via the root, configured in the settings:

```toml title="~/.config/mise/config.toml"
[settings]
dotfiles.root = "~/dotfiles"
dotfiles.default_mode = "symlink"
```

Then keys in the `[dotfiles]` section become the target directory or file, and it looks up the equivalent from the root configured above. This behaviour is similar to GNU Stow if you use it from the root directory of your dotfiles directory in your home directory. It's possible to list a different path to the source, as shown below.

```toml title="~/.config/mise/config.toml"
[dotfiles]
"~/.bashrc" = {}
"~/bin" = {}
"~/CommitMono_iainsimmonsV143" = {}
"~/epomaker_split65.layout.json" = {}
"~/.config/mise" = {}
"~/.agents/skills/dotfiles-mise" = { source = "../../.agents/skills/dotfiles-mise", mode = "symlink" }
"~/.config/bat" = {}
"~/.config/commit-mono-font" = {}
"~/.config/fish" = {}
"~/.config/ov" = {}
"~/.config/sesh" = {}
"~/.config/starship.toml" = {}
"~/.config/tmux" = {}
"~/.config/yazi" = {}
```

For some configurations, you may not want to symlink the entire directory, in which case you can use either `symlink-each` to symlink individual files within the directory (and optionally exclude some) or `copy` to just copy the files directly from the source to the target when the dotfiles are applied (`mise dot apply`).

```toml title="~/.config/mise/config.toml"
[dotfiles]
"~/.config/fastfetch/.prettierrc" = { mode = "copy" }
"~/.config/opencode" = { mode = "symlink-each", exclude = ["node_modules", "package.json", "package-lock.json", "bun.lock"] }
"~/.config/hunk" = { mode = "symlink-each" }
"~/.config/kitty/tokyonight_night.conf" = { mode = "copy" }
"~/.config/lazygit/.gitignore" = { mode = "copy" }
"~/.config/nvpm" = { mode = "copy", exclude = ["bin", "artifacts", "packages", "plugins"] }
```

The last mode that I use is `template`, which allows you to use [tera](https://keats.github.io/tera/) templating features. See the [mise Templates docs](https://mise.jdx.dev/templates.html).

This, combined with [mise Bootstrap secret inputs](https://mise.jdx.dev/bootstrap/secrets.html) and local environment variables to avoid putting secrets into my public dotfiles repo, allows me to have slightly different versions of some configuration files between each OS, such as my git config.

```toml title="~/.config/mise/config.toml"
[dotfiles]
# Rendered from `.gitconfig.tmpl`; macOS-only bits (osxkeychain, pbcopy/open
# aliases, ~/dev/Squiz includeIf) are OS-gated in the template.
"~/.gitconfig" = { source = "../../.gitconfig.tmpl", mode = "template" }
# sources a custom GitLab server mapping for my work machine running macOS, as configured in .env
"~/.config/lazygit/config.yml" = { source = "templates/lazygit.config.yml", mode = "template"}
# minor differences in these
"~/.config/fastfetch/config.jsonc" = { source = "../fastfetch/config.jsonc.tmpl", mode = "template" }
"~/.config/kitty/kitty.conf" = { source = "../kitty/kitty.conf.tmpl", mode = "template" }
```

## Bootstrap Tasks

This section is essentially just running a bash script for further configuration, some of it OS-specific, but generally just for tasks that would be run after installing various tools or packages. In the example below, I copy the customised version of the [CommitMono](https://commitmono.com/) font with my personal preferences into the appropriate directory for the current OS, and in the case of Omarchy, set it as the primary font across the system.

```toml title="~/.config/mise/config.toml"
[tasks.bootstrap]
run = """
set -euo pipefail

# Fonts dir (Linux: ~/.local/share/fonts, macOS: ~/Library/Fonts).
if [ "$(uname -s)" = "Darwin" ]; then
  FONT_DEST="$HOME/Library/Fonts/CommitMono"
else
  FONT_DEST="$HOME/.local/share/fonts/CommitMono"
fi
if [ ! -d "$FONT_DEST" ]; then
  echo "Installing CommitMono fonts..."
  mkdir -p "$FONT_DEST"
  cp "$HOME/dotfiles/CommitMono_iainsimmonsV143/"*.otf "$FONT_DEST/"
fi
if [ "$(uname -s)" != "Darwin" ]; then
  command -v fc-cache >/dev/null 2>&1 && fc-cache -f >/dev/null 2>&1 || true
  command -v omarchy-font-set >/dev/null 2>&1 && omarchy-font-set CommitMono_iainsimmons || true
fi
"""
```

## macOS Defaults

mise can also set [default options on macOS](https://mise.jdx.dev/bootstrap/macos-defaults.html). Here I set a long delay for the dock auto-hide, so it is essentially always hidden (I open all apps via keyboard shortcuts or a launcher, currently [Tinycast](https://tinycast.dev/), previously Vicinae or Raycast, or otherwise just Spotlight); and disable the default behaviour of pressing and holding a key for accented characters.

```toml title="~/.config/mise/config.macos.toml"
[bootstrap.macos.dock]
autohide_delay = 1000

[bootstrap.macos.keyboard]
press_and_hold = false

[bootstrap.hooks.post-defaults]
run = "killall Dock || true"
```

## Updating / Syncing

To keep things up-to-date across each machine, I have a `dotfiles-update` bash script that does the following:

1. sources the necessary (and secret) environment variables via the `.env` file (git ignored)
2. pulls the latest commit from my [dotfiles repo](https://github.com/iainsimmons/dotfiles): `git pull --ff-only`
3. applies the dotfiles (for the relevant OS/machine): `mise dot apply --prompt-secrets`
4. updates mise itself: `mise self-update`
5. upgrade tools (like Node.js) within specified version ranges: `mise outdated`/`mise upgrade`
6. upgrades configured packages via the relevant package manager(s): `mise bootstrap packages upgrade`
7. runs the bootstrap tasks to ensure things are configured correctly: `mise run bootstrap`

This is much nicer than my previous method of cherry-picking commits between different branches of my dotfiles repo or copying specific configurations between branches via git worktrees (so as to not break the config on the machine I was using).

## Conclusion

I'm enjoying having my dotfiles more consolidated and easy to get things up and running, and having things like Node.js versions managed by the same tool is a really nice bonus.

I'd recommend having a poke around the [mise Bootstrap docs](https://mise.jdx.dev/bootstrap.html) to see if it would work for you!
