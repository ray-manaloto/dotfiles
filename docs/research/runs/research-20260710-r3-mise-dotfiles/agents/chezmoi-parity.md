# Research: chezmoi feature dependence in THIS repo (Run r3, angle #2/3)

Domain: mise dotfiles vs/with chezmoi. This angle enumerates every chezmoi
feature the repo's `home/` source tree actually exercises, then maps each to
whether `mise dotfiles` (mise.jdx.dev/dotfiles.html) can cover it.

Date: 2026-07-10. Baseline grounding:
`.omc/research/research-20260709-r2-inventory/report.md`.

## Findings

### 0. Inventory of `home/` (exhaustive — every file, via `Glob home/**/*`)

```
home/.chezmoi.toml.tmpl
home/.chezmoiexternal.toml
home/.chezmoidata.yaml
home/.chezmoiignore
home/.chezmoiremove
home/.chezmoitemplates/env
home/dot_bashrc.tmpl
home/dot_config/mise/config.toml.tmpl
home/dot_config/starship.toml
home/dot_gitconfig
home/dot_local/bin/executable_claude
home/dot_profile.tmpl
home/dot_tmux.conf.tmpl
home/dot_wezterm.lua
home/dot_zshenv.tmpl
home/dot_zshrc.tmpl
home/pixi.toml.tmpl
home/pyproject.toml.tmpl
```

**No `run_*`/`run_once_*`/`run_onchange_*` scripts exist anywhere under
`home/`** (confirmed via `Glob home/**/run_*` and `Glob
home/**/*run_once*`, both zero matches, 2026-07-10). This repo does NOT
depend on chezmoi's script-execution feature at all — a materially
narrower footprint than a typical chezmoi setup.

### 1. Feature: `chezmoi.os` builtin for host/container discrimination

- `home/.chezmoiignore:5,11,52` — three `{{ if (ne) .chezmoi.os ... }}`
  gates: macOS-only paths (`Library/**`, `.config/karabiner/**`) skipped
  off-darwin; Linux-only paths (`.config/systemd/**`) skipped off-linux;
  and the **hard gate** at line 52 — `.config/mise/config.toml` (the
  overlay tool tier) is skipped entirely unless `chezmoi.os == "linux"`.
  This is the single highest-stakes template conditional in the repo: the
  comment block (`.chezmoiignore:30-51`) explicitly documents that this
  gate previously used a custom `is_container` data variable (env-var
  sniffing) and was refactored onto the `chezmoi.os` builtin per
  `.claude/rules/use-tool-builtins.md`, because rendering the overlay on
  the Mac host would pollute `~/.config/mise/config.toml` with
  container-only tooling.
- `home/.chezmoi.toml.tmpl:15,40,44,49,58` — `$isInteractive` gates
  prompting to `eq .chezmoi.os "darwin"`; `$isDevComputer` defaults `true`
  on `linux` when non-interactive; `is_darwin` data var computed from
  `chezmoi.os`; `commitMessageTemplate` embeds
  `{{ .chezmoi.os }}/{{ .chezmoi.arch }}`.
- CI enforcement of this exact gate: `.github/workflows/ci.yml:105-124`
  runs `chezmoi init --source "$PWD/home" --apply=false` on the (always
  linux) CI runner and asserts `chezmoi managed` output contains
  `.config/mise/config.toml` — a machine check that the devcontainer-only
  render path still fires. This CI step is itself chezmoi-specific
  tooling (`chezmoi managed`) with no mise-dotfiles analogue.

**mise dotfiles coverage**: mise's Tera template engine ships `os()` and
`os_family()` functions (verified via `https://mise.jdx.dev/templates.html`
fetch, 2026-07-10 — returns e.g. `linux`/`macos`/`windows` and
`unix`/`windows` respectively), which is functionally equivalent to
`chezmoi.os` for a plain darwin/linux split. **Covered**, with one caveat
(see §4, `osRelease` finer-grained distro detection, which mise's `os()`
does NOT provide).

### 2. Feature: `.tmpl` templating with Go `text/template` + custom functions

10 of 17 `home/` entries are `.tmpl` files:
`dot_bashrc.tmpl`, `dot_profile.tmpl`, `dot_tmux.conf.tmpl`,
`dot_zshenv.tmpl`, `dot_zshrc.tmpl`, `dot_config/mise/config.toml.tmpl`,
`pixi.toml.tmpl`, `pyproject.toml.tmpl`, plus the two chezmoi-config
templates (`.chezmoi.toml.tmpl`, and the shared fragment
`.chezmoitemplates/env`).

Notable template constructs actually used:

- **Shared template + `template` call**: `home/.chezmoitemplates/env:1`
  defines `{{ output "mise" "activate" .SHELL }}` — chezmoi's `output`
  function shells out to `mise activate <shell>` at apply-time and bakes
  the result into the rendered file. `dot_profile.tmpl:1` and
  `dot_zshenv.tmpl:1` both invoke it via `{{ template "env" (dict "SHELL"
  "bash"|"zsh") }}` — this is chezmoi's `.chezmoitemplates/` shared-
  fragment + parameterized `dict` pattern, used to avoid duplicating the
  `mise activate` line across two files.
- **Data-driven values**: `pixi.toml.tmpl:5` — `platforms =
  {{ .platforms | toJson }}` — sources from `home/.chezmoidata.yaml`
  (`platforms: [linux-64, osx-arm64, linux-aarch64]`), a static
  chezmoi-managed data file merged into the template context.
- **`.chezmoi.osRelease` distro-ID branching** (see §4 below) in
  `dot_zshrc.tmpl:28` and `dot_tmux.conf.tmpl:9,13,17`.
- **`env "VAR"` lookups + boolean coercion**: the `$remote` computation
  repeated verbatim in `.chezmoi.toml.tmpl:44`, `dot_zshrc.tmpl:1`, and
  `dot_bashrc.tmpl:1` — `or (env "CODESPACES"|not|not) (env
  "SSH_CONNECTION"|not|not) ... (stat "/.dockerenv"|not|not)` — chezmoi's
  `stat` template function (probing `/.dockerenv`) has no mise
  equivalent; mise templates don't expose a filesystem-stat function per
  the fetched `templates.html` variable/function list (only `env`, `cwd`,
  `config_root`, `mise_bin`, `mise_pid`, XDG dirs, plus `os()`/`arch()`/
  `os_family()`/`exec()`).
- **`.local/bin/executable_` prefix**: `dot_local/bin/executable_claude`
  — chezmoi's filename-attribute encoding (`executable_` prefix → chmod
  +x on apply) sets the exec bit on a 3-line wrapper script
  (`exec mise exec claude-code -- claude "$@"`).

**mise dotfiles coverage**: mise dotfiles supports "render the source
through the mise template engine" per `dotfiles.html` (fetched
2026-07-10), so basic Tera conditionals/variables ARE coverable, INCLUDING
`exec()` (mise's shell-out function, functionally equivalent to
chezmoi's `output`) for the `mise activate` baking pattern. **Partially
covered**: the `dict`/named-template `include`-style composition
(`.chezmoitemplates/env` reused across 2 files) has no confirmed mise
dotfiles equivalent — Tera itself supports `{% include %}` and macros,
but this is unverified against mise's specific dotfiles template
context/sandboxing (not documented on the fetched `dotfiles.html` page).
The `stat`-based `/.dockerenv` probe and filename-attribute chmod
(`executable_` prefix) are NOT covered — see §4.

### 3. Feature: `.chezmoiignore` machine-conditional file gating

Already covered as the hard gate in §1. Additionally:
`.chezmoiignore:1-4` unconditionally excludes `README.md`, `LICENSE`,
`.github/` from being chezmoi-managed at all (repo-hygiene exclusion, not
machine-conditional); `.chezmoiignore:16-22` unconditionally excludes
`.cargo/**`, `.rustup/**`, `.config/gcloud/**` (tool-owned directories,
same on both host and container per the v6-refactor comment at
`.chezmoiignore:16-19`); `.chezmoiignore:24-28` gates `.ssh/config` and
`.gnupg/**` on the `is_personal` data var (from the interactive prompt in
`.chezmoi.toml.tmpl:39`).

**mise dotfiles coverage**: NOT covered as a unit. mise dotfiles has no
declarative ignore-list; per the fetched `dotfiles.html`, entries are
declared individually in `mise.toml [dotfiles]` (target/source/mode
triples) — the *absence* of a declaration is mise's version of "ignore,"
so the unconditional exclusions (§ README/LICENSE/.github,
.cargo/.rustup/.config-gcloud) trivially port (just never declare them).
But the machine-*conditional* exclusions (linux-only mise overlay,
darwin-only Library/karabiner, personal-only ssh/gnupg) would require
wrapping each `[dotfiles]` entry declaration itself in a Tera `{% if %}`
inside `mise.toml` — unverified whether mise's config-level templating
(as opposed to dotfiles *content* templating) extends to conditionally
declaring/omitting whole `[dotfiles]` table entries hence this is an
open gap, not a confirmed pass.

### 4. Features chezmoi has that this repo uses and mise does NOT have

- **`.chezmoi.osRelease.id` distro-ID detection** — `dot_zshrc.tmpl:28`
  branches on `bazzite`; `dot_tmux.conf.tmpl:9,13` branch on
  `ubuntu`/`debian`/`fedora` (falling to `darwin` at line 17). mise's
  `os()`/`os_family()` (confirmed via `templates.html` fetch) return only
  the 3-way OS class (linux/macos/windows) and 2-way family
  (unix/windows) — no distro/ID granularity. **Not covered** by mise
  templates as documented.
- **`stat` template function** (`/.dockerenv` existence probe, used 3×
  for the `$remote` computation) — not in mise's documented template
  function list. **Not covered.**
- **`executable_` filename-attribute chmod** on
  `dot_local/bin/executable_claude`. mise dotfiles docs (fetched
  2026-07-10) describe symlink/symlink-each/copy/template modes keyed off
  explicit `[dotfiles]` table config, not filename-attribute encoding —
  unverified whether an explicit `mode`/permission key exists to replace
  it, but the *mechanism* (infer chmod from filename prefix) is
  chezmoi-specific and not restated on the fetched page. **Not
  confirmed covered.**
- **`promptBoolOnce` interactive prompting** — `.chezmoi.toml.tmpl:38-39`
  (`is_dev_computer`, `is_personal`) prompts once on first `chezmoi init`
  on an interactive darwin+non-CI TTY, then persists the answer in
  `~/.config/chezmoi/chezmoi.toml`. Per the fetched
  `dotfiles.html` summary, mise's template engine has **no interactive
  input mechanism** ("the documentation contains no interactive input
  mechanism equivalent to chezmoi's prompting"). **Not covered** — this
  is a first-class chezmoi feature this repo actively depends on for its
  Mac-host personal/dev-computer split.
- **`chezmoi managed` introspection command** — `ci.yml:118-119` uses
  `chezmoi --source "$SRC" managed | grep -qE '^\.config/mise/config\.toml$'`
  as the machine check that the render gate fires correctly. This is a
  chezmoi CLI capability (list what would be managed, without applying)
  with no stated mise dotfiles equivalent in the fetched docs.
- **`.chezmoiexternal.toml` URL-sourced external files** —
  `home/.chezmoiexternal.toml:7-10` declares a `type = "file"` external
  fetching `_mise` zsh completions from
  `raw.githubusercontent.com/jdx/mise/main/completions/_mise` with a
  168h `refreshPeriod`. No equivalent surfaced in the fetched mise
  `dotfiles.html` page (mise dotfiles entries are `source`/`target`
  pairs against local paths, not remote URL fetches). **Not covered.**
- **`.chezmoiremove` removal allowlist** — currently empty
  (`home/.chezmoiremove`, 15 lines, all comments) but is a real
  chezmoi mechanism (explicit removal list, applied only when chezmoi
  itself owns the apply). Per the fetched `dotfiles.html`, mise dotfiles
  "keeps no state database," so "removing an entry from config leaves its
  file... in place" — structurally the opposite of what
  `.chezmoiremove` is for. **Not covered** (though currently unused, so
  zero present dependence).
- **`chezmoi diff` pager (`delta`) / `git.autoCommit=false`** —
  `.chezmoi.toml.tmpl:56-61` — chezmoi-specific apply-time UX/git
  integration config, no mise dotfiles equivalent surfaced.

### 5. Apply mechanics — where/how chezmoi actually runs in this repo

- `.devcontainer/scripts/on-create.sh:40-41` — `chezmoi init --apply
  --source="${WORKSPACE_FOLDER}" --no-tty --force` runs on EVERY
  container create (comment at line 15-17: "managed files refresh every
  container create — persistent home volume does NOT protect local edits
  to managed files").
  This is devcontainer-only; `chezmoi apply`/`update` is DENY-listed on
  the Mac host per `.claude/settings.json:4-5` (`"Bash(chezmoi
  apply:*)"`, `"Bash(chezmoi update:*)"` both denied) and
  `python/src/dotfiles_setup/hook_guard.py:64` ("chezmoi apply/update is
  blocked on the Mac host — it may only run [in the devcontainer]").
- mise dotfiles is explicitly pull/manual: fetched `dotfiles.html` states
  "Nothing is written implicitly. Only `mise dotfiles apply` or mise
  bootstrap applies dotfiles" — structurally compatible with the
  existing on-create.sh invocation pattern (swap the `chezmoi init
  --apply ...` line for a `mise dotfiles apply` call), IF everything else
  in this report were covered — which it is not (§4).

## Uncertainties / gaps

- I could not fetch a live `mise.jdx.dev/dotfiles.html` page directly
  with source HTML (WebFetch summarizes through a small model); the
  quoted capability strings ("Nothing is written implicitly...", "keeps
  no state database", etc.) are the tool's verbatim quotes back from that
  fetch, not independently re-verified against raw HTML. Recommend a
  second-pass verifier re-fetch with `curl
  https://mise.jdx.dev/dotfiles.html` (or `.md` if mintlify-hosted) to
  confirm these quotes are accurate and not paraphrased.
  `docs/research/mintlify-catalog.md` does NOT list a dedicated
  `dotfiles.html` cache entry for jdx/mise (only the general
  `llms-full.txt`, which has exactly one incidental "dotfiles" mention at
  line 1109 about `mise.toml`/`.mise.toml` filename equivalence — this
  page is NOT mintlify-cached and required a live fetch).
  `mise.jdx.dev/shell.html` returned HTTP 404 on fetch (2026-07-10) — the
  domain brief referenced this path but current mise docs may have moved
  or renamed it; unresolved, did not chase further within this angle's
  scope (shell/user.html is arguably angle #1's or #3's territory).
- Whether mise's Tera dotfiles-template context exposes `{% include %}`
  or macros equivalent to chezmoi's named-template (`.chezmoitemplates/`
  + `template` call + `dict` args) pattern is UNVERIFIED — the fetched
  `templates.html` page covers mise.toml-level templating functions, not
  the dotfiles-specific template context, which may differ or be more
  restricted (dotfiles docs did not enumerate its available functions
  exhaustively in the WebFetch summary).
  Whether mise dotfiles config (`[dotfiles]` table in `mise.toml`) itself
  supports being wrapped in `{% if %}` to conditionally declare/omit
  entries (needed to replicate `.chezmoiignore`'s machine-conditional
  gating as a unit, §3) is UNVERIFIED.
- Whether mise dotfiles has any filename-attribute-style permission
  encoding (to replace chezmoi's `executable_` prefix on
  `dot_local/bin/executable_claude`) is UNVERIFIED — not stated on the
  fetched page.
- This angle only enumerates chezmoi FEATURES the repo's `home/` source
  depends on; it does not weigh mise dotfiles' own unique benefits (e.g.
  tighter mise-native integration, single-tool consolidation) — that
  synthesis is the domain-level recommendation, out of scope for this
  angle report per the task framing (angle #2 of 3).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read `home/**` (every chezmoi-managed source file), `.chezmoiignore`, `.chezmoi.toml.tmpl`, `.chezmoiexternal.toml`, `.chezmoidata.yaml`, `.chezmoiremove`, `.chezmoitemplates/env`, `.devcontainer/devcontainer.json`, `.devcontainer/scripts/on-create.sh`, `.devcontainer/Dockerfile`, `.github/workflows/ci.yml`, `.claude/settings.json`, `python/src/dotfiles_setup/hook_guard.py` for file:line evidence of every chezmoi feature this repo actually exercises.
- [jdx/mise](https://github.com/jdx/mise) — fetched `mise.jdx.dev/dotfiles.html` and `mise.jdx.dev/templates.html` (live docs, not in the local mintlify cache) to establish mise dotfiles' templating/apply-mechanics capability surface for the feature-by-feature mapping.
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — fetched `chezmoi.io/user-guide/manage-machine-to-machine-differences/` to cross-check the canonical `chezmoi.os` / `.chezmoiignore` pattern this repo's `.chezmoi.toml.tmpl` and `.chezmoiignore` comments cite directly.
