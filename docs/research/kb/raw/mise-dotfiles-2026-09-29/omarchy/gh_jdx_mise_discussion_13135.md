# mise bootstrap dotfiles templates do not support secrets

- URL: https://github.com/jdx/mise/discussions/13135
- author: iainsimmons created: 2026-09-13T03:09:18Z

## Body

```sh
$ mise doctor
```

doctor output:

```
version: 2026.9.1 linux-x64 (2026-09-02)
activated: yes
shims_on_path: yes
self_update_available: no

build_info:
  Target: x86_64-unknown-linux-gnu
  Features: openssl, rustls-native-roots, self_update
  Built: Wed, 2 Sep 2026 13:10:00 +0000
  Rust Version: rustc 1.94.0 (4a4ef493e 2026-03-02)
  Profile: release

shell:
  /usr/bin/fish
  fish, version 4.9.2

aqua:
  baked in registry: aquaproj/aqua-registry@e5290615d37d083d0ce31e5378a2ce52d855264b
  baked in registry tools: 2290

dirs:
  cache: ~/.cache/mise
  config: ~/.config/mise
  data: ~/.local/share/mise
  shims: ~/.local/share/mise/shims
  system_shims: /usr/local/share/mise/shims
  state: ~/.local/state/mise

config_files:
  ~/dotfiles/.config/mise/config.toml
  ~/dotfiles/.config/mise/config.linux.toml

env_files:
  (none)

ignored_config_files: (none)

backends:
  aqua
  asdf
  cargo
  conda
  core
  dotnet
  forgejo
  gem
  github
  gitlab
  go
  npm
  pipx
  pkgx
  spm
  http
  s3
  ubi
  vfox

plugins:

toolset:
  aqua:anomalyco/opencode@1.18.30
  aqua:cli/cli@2.100.0
  aqua:modem-dev/hunk@0.22.0
  aqua:openai/codex@0.153.4
  core:go@1.27.1
  core:node@24.21.0
  core:python@3.14.4
  github:joshmedeski/sesh@2.30.1
  npm:playwright@1.63.0

path:
  ~/.nub/bin
  ~/.local/share/mise/installs/codex/latest/bin
  ~/.local/share/mise/installs/gh/latest/gh_2.100.0_linux_amd64/bin
  ~/.local/share/mise/installs/go/1.27.1/bin
  ~/.local/share/mise/installs/github-joshmedeski-sesh/latest
  ~/.local/share/mise/installs/node/24/bin
  ~/.local/share/mise/installs/opencode/latest
  ~/.local/share/mise/installs/python/3.14.4/bin
  ~/.local/share/mise/installs/aqua-modem-dev-hunk/latest/hunkdiff-linux-x64
  ~/.local/share/mise/installs/npm-playwright/latest/node_modules/.bin
  ~/.local/share/mise/shims
  ~/.local/share/nvpm/bin
  ~/coding/yt-pl-dl
  ~/.cargo/bin
  ~/.local/share/mise
  ~/.local/share/omarchy/bin
  ~/bin
  /usr/local/bin
  ~/.local/share/../bin
  /usr/local/sbin
  /usr/bin
  ~/.local/bin
  /usr/lib/jvm/default/bin
  /usr/bin/site_perl
  /usr/bin/vendor_perl
  /usr/bin/core_perl
  ~/.config/nvpm/bin
  ~/.local/share/pnpm/bin
mise WARN  unknown bootstrap package manager 'aur' in [bootstrap.packages], ignoring — install a package plugin: mise plugin install package:aur <url>

system_packages:
  pacman: 12 requested, 0 missing

env_vars:
  MISE_SHELL=fish

settings:
  idiomatic_version_file_enable_tools  ["node"]     ~/dotfiles/.config/mise/config.toml
  dotfiles.default_mode                "symlink"    ~/dotfiles/.config/mise/config.toml
  dotfiles.root                        "~/dotfiles" ~/dotfiles/.config/mise/config.toml
mise WARN  mise version 2026.9.6 available
mise WARN  self-update is disabled for this install, update mise the same way you installed it

2 warnings found:

1. mise tool paths are not first in PATH. These paths take precedence:
     ~/.nub/bin
   This may cause system-installed tools to be used instead of mise-managed versions.
   Ensure `mise activate` runs after other PATH modifications in your shell rc file.

2. new mise version 2026.9.6 available, currently on 2026.9.1

No problems found
```

With this in the mise config:

```toml
[bootstrap.secrets]
gitlab_instance = "GITLAB_INSTANCE"

[dotfiles]
"~/.config/lazygit/config.yml" = { source = "../lazygit-config.yml.tmpl", mode = "template" }
```

And this in that template:

```tmpl
services:
  "{{secret(name="gitlab_instance")}}": "gitlab:{{secret(name="gitlab_instance")}}" # add custom GitLab instance
```

Running the bootstrap dotfiles apply:

```sh
$ mise bootstrap dotfiles apply -E desktop
```

Gives this error:

```
mise ERROR files: entries with errors:
  [dotfiles]."~/.config/lazygit/config.yml": failed to render template ~/dotfiles/.config/mise/../lazygit/config.yml.tmpl: error: Unknown function `secret`
  --> __tera_one_off:23:6
   |
23 |   "{{secret(name="gitlab_instance")}}": "gitlab:{{secret(name="gitlab_instance")}}" # add custom GitLab instance
   |      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

error: Unknown function `secret`
  --> __tera_one_off:23:51
   |
23 |   "{{secret(name="gitlab_instance")}}": "gitlab:{{secret(name="gitlab_instance")}}" # add custom GitLab instance
   |                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mise ERROR Version: 2026.9.1 linux-x64 (2026-09-02)
mise ERROR Run with --verbose or MISE_VERBOSE=1 for more information
```

As a workaround I had to use the `bootstrap.files` in my mise config, and move the template:

```toml
[bootstrap.files]
"~/.config/lazygit/config.yml" = { source = "templates/lazygit.config.yml", template = true, replace = true}
```

I don't know if `--prompt-secrets` works with `mise bootstrap dotfiles` either, so I need to first do it with `mise bootstrap files --prompt-secrets`.

## Comments
### jdx @ 2026-09-13T12:12:43Z

Thanks for the clear reproduction—this was a real gap between managed bootstrap file templates and dotfile templates. I opened https://github.com/jdx/mise/pull/13140 to add the same declared `secret()` inputs to `[dotfiles]` templates.

The PR also adds `--prompt-secrets` to dotfiles commands that may render templates, fails closed when a referenced value is unavailable, includes dotfile-only inputs in aggregate bootstrap status, and redacts resolved values from textual dotfile diffs. Until it lands, your `[bootstrap.files]` workaround remains the supported path.

*AI-assisted — Tool: Codex; model: openai/gpt-5; version: unavailable.*

