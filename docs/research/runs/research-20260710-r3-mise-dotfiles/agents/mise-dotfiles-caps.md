# mise `[dotfiles]` capabilities — research report (Angle #1 of 3)

Run: `research-20260710-r3-mise-dotfiles` · Agent angle: mise dotfiles
capabilities only (chezmoi-side and synthesis are separate angles).
Researched 2026-07-10.

## Scope note on sourcing

The project's mintlify cache (`docs/research/mintlify-cache/jdx/mise/`)
does **not** contain the `dotfiles.html` page — greps for `dotfile`
(singular/plural) across both `llms.txt` and `llms-full.txt` returned no
hits for the feature page itself (the only hit was an unrelated line
about `mise` config file naming being "dotfile alternative", i.e.
`.mise.toml` vs `mise.toml`). The cache's `llms.txt` page index
(`docs/research/mintlify-cache/jdx/mise/llms.txt:5-42`) also does not
list a dotfiles page — the index predates the feature. This is
consistent with the feature being **very new**: it shipped in mise
`v2026.6.6` ("Declarative machine bootstrap", released **2026-06-13**,
per GitHub Releases), roughly a month before this cache was assembled
and one month before today (2026-07-10). Per the doc-fetch preference
chain, on a confirmed cache miss the next steps are `llms.txt` then
`<page>.md`; both `https://mise.jdx.dev/llms.txt` and
`https://mise.jdx.dev/dotfiles.md` 404'd (this mise doc site does not
serve a root `llms.txt` or clean-URL `.md` suffix the way the
mintlify.com mirror does), so I fell back to `WebFetch` directly against
the live rendered page `https://mise.jdx.dev/dotfiles.html`, which
succeeded and is the primary source below. This is a documented,
justified fallback per `research-doc-sources.md` step 4 (raw HTML fetch
as last resort), not a skipped step — the cheaper steps were tried first
and failed.

## Findings

### 1. What it is, and how new it is

mise gained a declarative dotfiles manager, `[dotfiles]` in `mise.toml`
plus a `mise dotfiles` subcommand family (`add`/`apply`/`edit`/`status`),
and a companion `mise bootstrap` command for whole-machine setup, in
release **v2026.6.6, "Declarative machine bootstrap," 2026-06-13**
(https://github.com/jdx/mise/releases/tag/v2026.6.6). The live docs page
does not mark the feature experimental/beta and states no minimum
version requirement in its own text (verified by direct query against
https://mise.jdx.dev/dotfiles.html, 2026-07-10) — but the feature is
objectively ~1 month old relative to today's date, undocumented in this
repo's cached doc snapshot, and (see §6) essentially absent from
third-party comparison content as of this research date. Source:
https://mise.jdx.dev/dotfiles.html (fetched 2026-07-10); release date
cross-checked at https://github.com/jdx/mise/releases/tag/v2026.6.6.

### 2. Core model: declarative entries in `mise.toml`, own-whole-file or own-a-fragment

"mise can manage dotfiles from the `[dotfiles]` section of `mise.toml`.
Entries can either own a whole file or directory, or manage one small
piece of a file something else owns." (https://mise.jdx.dev/dotfiles.html)

Two entry shapes:
- **Whole-file entries** — keyed by target path (absolute or `~/`-relative);
  optional `source` (if omitted, mise mirrors the home-relative target
  path under `dotfiles.root`); "Targets outside `$HOME` must specify
  `source`."
- **Edit entries** — keyed by target path *plus* an `id` naming an edit
  within the file (format like `"~/.zshrc/activate"`); distinguished from
  whole-file entries by pairing `source` with `template = "tera"`.

Source: https://mise.jdx.dev/dotfiles.html.

### 3. Storage model: a root directory, symlink-first

Settings: `dotfiles.root = "~/.dotfiles"` (default) and
`dotfiles.default_mode = "symlink"`, set under `[settings]`. Relative
explicit `source` paths resolve against the directory of the config file
that declares the entry. Source paths may contain glob wildcards (`*`,
`**`, `?`, `[ab]`); a wildcard source matching multiple paths requires
the target path to also carry matching wildcards so each source expands
to a unique target. Source: https://mise.jdx.dev/dotfiles.html.

### 4. Four apply modes — this is the storage/link mechanics core

| Mode | Behavior (verbatim from docs) |
|---|---|
| `symlink` (default) | "Symlink the target to the source. Works for files and directories — a directory source gets one link for the whole directory." |
| `symlink-each` | "Source must be a directory: recreate its directory structure under the target and symlink each file individually, so the target directory (say, `~/.config`) can also hold files mise doesn't manage." |
| `copy` | "Copy the source file (or directory, recursively). Use when the target must be a real file... Directory copies are additive: matching files are overwritten, files mise doesn't manage are left in place." |
| `template` | "Render the source through the mise template engine and write the result. Permissions are taken from the source file (and repaired if they drift)." |

Source: https://mise.jdx.dev/dotfiles.html.

### 5. Templating — YES, mise dotfiles has templating, via the same Tera engine used elsewhere in mise.toml

"Templates get the same context as other mise templates (`env`, `vars`,
`exec()`, etc.), which is the main reason to use them: one source file,
per-machine output." (https://mise.jdx.dev/dotfiles.html)

This is the same Tera template engine documented at
`configuration/templates.md`, cached locally at
`docs/research/mintlify-cache/jdx/mise/llms-full.txt:1519-1648`. Built-in
variables/functions confirmed in that cached page (not dotfiles-specific,
but the engine dotfiles templates draw on):
- `env` — access environment variables (`{{ env.HOME }}`)
  (llms-full.txt:1548-1556)
- `cwd` — current working directory (llms-full.txt:1558-1565)
- `get_env(name, default)` — read env var with fallback
  (llms-full.txt:1569-1576)
- `exec(command)` — run a shell command, use its output
  (llms-full.txt:1578-1585)
- `arch()` — system architecture, e.g. `x86_64`/`aarch64`
  (llms-full.txt:1587-1594)
- `os()` — OS name, `linux`/`macos`/`windows`
  (llms-full.txt:1596-1604), with a documented conditional-template
  pattern: `python = "{% if os() == 'macos' %}3.12{% else %}3.11{% endif %}"`
- `os_family()` — `unix` or `windows` (llms-full.txt:1606-1608)
- `num_cpus()` (llms-full.txt:1610-1617)
- Standard Tera string filters: `upper`, `lower`, `trim`, `replace`,
  `truncate`, `basename`, `dirname`, etc. (llms-full.txt:1619-1632)

**Machine-differences handling**: `os()`/`arch()`/`os_family()` are mise's
direct structural analog to chezmoi's `.chezmoi.os` builtin fact (see
`.claude/rules/use-tool-builtins.md` for why this repo prefers built-in
facts over homegrown env-var detection) — a template source file can
branch on `os()`/`arch()` the same way a chezmoi `.tmpl` branches on
`.chezmoi.os`. This is a real, native per-machine capability, not a gap.
Source: https://mise.jdx.dev/dotfiles.html (context claim) cross-referenced
with the cached Tera builtins list above.

Detection-of-drift detail specific to dotfiles templates: "Detecting
whether a template's output has drifted requires rendering it, so `mise
dotfiles status` and a real apply evaluate templates — including any
`exec()` calls — from your trusted config, just like `[env]` templates.
`--dry-run` is the exception: it promises to execute nothing, so it skips
template rendering and lists those entries as `(if changed)`."
(https://mise.jdx.dev/dotfiles.html)

### 6. Partial-file management: block and line edits, marker-delimited, stateless

For files mise doesn't fully own:
- **Block edits**: "A `block` is delimited by marker comments in the
  target file, named by the entry's id." Example:
  ```
  # >>> mise:activate >>> managed by mise - do not edit between markers
  eval "$(mise activate zsh)"
  # <<< mise:activate <<<
  ```
  "The markers are the ownership record, stored in the file itself, so
  the design stays stateless: applying replaces only what's between them
  or appends the block if absent, and everything else in the file is
  untouched." Marker comment prefix is inferred from file extension (`#`
  shell/config, `--` Lua, `//` C-like, `;` INI, `"` vim) or overridden
  with `comment = "..."`. Ids: letters, digits, `_`, `-`, `.`.
- **Line edits**: "A `line` ensures an exact line exists somewhere in the
  file, appending it at the end if absent. It never modifies or removes
  other lines... The value must be a single line; use a block for
  multi-line content."

Source: https://mise.jdx.dev/dotfiles.html.

### 7. Apply mechanics: manual-only, idempotent, no state database

- **Manual application only**: "Dotfiles are only applied when explicitly
  requested with `mise dotfiles apply` or as part of mise bootstrap. They
  are never applied implicitly by `mise install` or `mise bootstrap
  packages`."
- **Idempotent**: "entries already in their desired state are skipped;
  re-running is always safe."
- **Declarative and additive across config hierarchy**: entries merge
  global → project; whole-file entries merge by target path, edit entries
  merge by `(path, id)`.
- **No state database**: "Removing an entry from config leaves its file,
  block, or line in place because mise keeps no state database." This is
  a structural difference from chezmoi, which tracks managed-file state
  and can `chezmoi apply` a removal.
- **Unknown modes/operations ignored with a warning**, for forward
  config compatibility across mise versions.

Source: https://mise.jdx.dev/dotfiles.html.

### 8. Conflict/safety behavior

- "mise refuses to _replace_ existing files it doesn't manage: a real
  file or directory where a symlink should go, or a directory where a
  file should go, is an error listing the conflicting paths." Override:
  `mise dotfiles apply --force`.
- Symlink entries: "an existing regular file with identical content to
  the source is converged without `--force` by replacing it with the
  requested symlink. If the content differs, mise still treats it as a
  conflict."
- `copy`/`template` entries overwrite target content **without**
  `--force` by design ("that is the declared intent of those modes").
- Edit entries (block/line) never need `--force`; two cases are hard
  errors instead of silently guessed at: **corrupted markers** and
  **targets that are symlinks**.
- Root-owned files: "Dotfiles write as the current user — there is no
  sudo here. Managing `/etc/hosts` works when running as root (containers,
  CI); otherwise mise fails with an ordinary permission error." —
  directly relevant to this repo's devcontainer-only constraint, since
  the devcontainer user is UID 1000, not root (per `AGENTS.md`
  `DEVCONTAINER_USERNAME` table).
- Windows: file symlinks require elevation, so `symlink`/`symlink-each`
  fall back to copy for files; directory symlinks use junctions
  (irrelevant to this repo's Linux-only devcontainer target, noted for
  completeness).

Source: https://mise.jdx.dev/dotfiles.html.

### 9. Commands

| Command | Effect (verbatim/paraphrased from docs) |
|---|---|
| `mise dotfiles status` | shows applied/missing/differs (with a reason)/source missing per entry |
| `mise dotfiles status --missing` | exit 1 if anything is out of sync (CI-friendly gate) |
| `mise dotfiles apply` | apply files and edits |
| `mise dotfiles apply --dry-run` | print what would be done (skips template rendering, see §5) |
| `mise dotfiles apply --dry-run --verbose` | include diff-like details |
| `mise dotfiles apply --yes` | skip confirmation prompt |
| `mise dotfiles apply --force` | also replace conflicting files |
| `mise dotfiles add ~/.zshrc` | capture a live file into `dotfiles.root`; for an unmanaged target, creates a `[dotfiles]` entry and seeds the source; for an already-managed target, updates the existing source from the live target |
| `mise dotfiles edit ~/.zshrc` | edit the managed source or owning config |
| `mise dotfiles edit --apply ~/.zshrc` | edit-then-apply variant |

Source: https://mise.jdx.dev/dotfiles.html.

### 10. Self-managing bootstrap pattern

"You can manage the mise config and the dotfiles root as dotfiles too...
This is a bootstrap pattern: clone the real repo (for example
`~/src/dotfiles`) before the first `mise dotfiles apply` or `mise
bootstrap`. Use the real repo path for sources needed during the first
run; `~/.dotfiles` does not exist until mise creates that symlink."
Source: https://mise.jdx.dev/dotfiles.html.

### 11. `mise bootstrap` — the umbrella command dotfiles plugs into

`mise bootstrap` "sets up a machine for the current config in one
command: OS packages, git repos, dotfiles, mise shell activation, macOS
defaults, macOS LaunchAgents, Linux systemd user services, the user's
login shell, tools, and any final project-specific task." Convergent
semantics mirror the dotfiles feature: "if a package is already
installed, a repo is already at the requested ref, a dotfile already
matches, or a default is already set, mise skips it." Related flags:
`mise bootstrap --force-dotfiles` (replace conflicting whole-file
dotfile targets specifically during a bootstrap run), `mise bootstrap
status` / `mise bootstrap status --missing` (inspect/gate the full
declarative bootstrap surface, not just dotfiles).
Source: https://mise.jdx.dev/bootstrap.html (via search-result extraction,
2026-07-10) — this specific page was not independently re-fetched
verbatim; treat phrase-level wording here as lower-confidence than the
`dotfiles.html` citations above, which were fetched and quoted directly.

### 12. Secrets — explicit gap

The dotfiles doc page contains **no mention of secrets, encryption,
age, gpg, or sops anywhere** — directly queried and confirmed absent
(WebFetch query against https://mise.jdx.dev/dotfiles.html, 2026-07-10:
"does this page mention... encryption, age, gpg, sops, or secrets" →
"No, the page does not mention these terms... there is no discussion of
secret management integration"). mise does have a **separate, unrelated**
secrets mechanism for environment variables — `environments/secrets.html`,
described in the cached index as "Manage sensitive environment variables
securely using SOPS, age encryption, or external secret managers"
(`docs/research/mintlify-cache/jdx/mise/llms.txt:26`) — but that page
covers `[env]`-block secret *values*, not dotfiles *files*. The dotfiles
feature and the secrets feature are orthogonal; `[dotfiles]` has no
first-class notion of "this managed file/block contains a secret,"
no encrypt-at-rest option for a dotfiles source, and no integration point
with the SOPS/age env-secrets system documented elsewhere. Any secret
material placed under `dotfiles.root` would sit there in plaintext exactly
as committed, with mise providing no special handling.

### 13. Stated/observed limits vs. a full dotfile manager (chezmoi-class)

Compiled from the sourced findings above, not from an explicit
"Limitations" section (the live page has none — confirmed by direct
query, §1):

- **No encryption/secrets integration** (§12) — chezmoi has native
  age/gpg encryption for individual files; mise dotfiles has nothing
  comparable at the file level.
- **No state database** (§7) — a removed `[dotfiles]` entry leaves its
  file/block/line in place; there is no "un-apply" or drift-cleanup on
  removal the way a stateful manager could offer.
- **No sudo / root-file management as non-root** (§8) — writes as the
  current user only; managing root-owned targets requires the whole
  process to run as root (fine for this repo's containers/CI, per the
  doc's own framing, but a real constraint for host-level `/etc` files).
- **Windows symlink limitation** — falls back to copy for file symlinks
  without elevation (§8); not relevant to this repo's Linux-only
  devcontainer target but a real cross-platform gap versus chezmoi,
  which has more mature Windows support.
- **Template rendering is not dry-run-safe** — `--dry-run` explicitly
  skips template evaluation (§5), so a dry-run cannot fully preview
  template-mode changes, only flag them as "(if changed)".
- **Feature is very new** (~1 month old as of this research date, §1) —
  not yet covered by third-party comparison writeups (§14), so
  real-world edge cases / maturity relative to chezmoi (which has years
  of production hardening, per chezmoi.io) are unproven at this point in
  time.
- **No documented run-script equivalent** (chezmoi's `run_once_`/
  `run_onchange_` scripts) was found anywhere in the fetched
  `dotfiles.html` content — the doc's four modes (symlink, symlink-each,
  copy, template) and block/line edits cover file placement and
  in-place edits, but nothing resembling an arbitrary onchange/one-time
  script hook. This is a functional gap versus chezmoi's `run_` script
  system if this repo relies on that mechanism (a question for the
  chezmoi-angle report to confirm current usage of).

### 14. Third-party / comparison coverage as of research date

A web search for "mise dotfiles vs chezmoi comparison 2026" (2026-07-10)
returned no direct comparison content; results were dominated by
chezmoi-only material (chezmoi.io's own comparison table, a "Stow or
Chezmoi" blog post, general dotfile-utility roundups) plus one repo
example (`dankaiser1808/dotfiles`) using chezmoi *and* mise together as
complementary tools (chezmoi for dotfiles, mise for tool/runtime
versions) — but that repo pattern predates mise's own native `[dotfiles]`
feature (v2026.6.6, 2026-06-13) and so doesn't speak to the new
capability. No evidence was found of anyone in the wild using mise's
native dotfiles feature as a chezmoi replacement yet. This corroborates
§1/§13's point that the feature is too new for independent validation.

## Uncertainties / gaps

- **`mise bootstrap` page (§11) not independently re-fetched verbatim** —
  I relied on WebSearch's extraction rather than a direct WebFetch of
  `https://mise.jdx.dev/bootstrap.html` (that direct fetch was not
  attempted in this run; the search-result summary is consistent with
  and complements the `dotfiles.html` content but should be treated as
  secondary-confidence).
  Fetching `system-files.html` (linked from `bootstrap.html` search
  results, plausibly the page behind "System Files" — a related
  root/etc-file feature) returned HTTP 404; the correct current URL for
  that page (if it still exists) was not resolved in this run.
- **No minimum-version / stability tag confirmed on the docs page
  itself** — absence of an "experimental" label is not the same as a
  changelog/GitHub-issue confirmation of stability; I did not walk the
  jdx/mise issue tracker or CHANGELOG for post-release bugfixes/caveats
  on `[dotfiles]` since v2026.6.6.
- **No direct confirmation of Tera's exact filter/function completeness**
  for dotfiles-specific templating beyond what's documented for
  `mise.toml` templates generally (§5) — the docs say dotfiles templates
  "get the same context as other mise templates," which I'm taking at
  face value rather than empirically testing a live `mise dotfiles apply
  --dry-run` against a template entry (no local mise
  environment was available in this Bash-broken research session to
  empirically verify).
- **This repo's actual applicability was explicitly out of scope for
  this angle** (assigned to a separate synthesis/chezmoi-angle report) —
  this report characterizes only what mise's native dotfiles feature
  *can do*, not whether it should replace/complement/neither the current
  chezmoi setup in `home/`.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — primary subject: fetched
  `dotfiles.html`/`bootstrap.html` docs (via mise.jdx.dev, mintlify-hosted)
  and the `v2026.6.6` GitHub release notes for the dotfiles/bootstrap
  feature's introduction and date.
- [dankaiser1808/dotfiles](https://github.com/dankaiser1808/dotfiles) —
  surfaced in a comparison web search as an example repo combining
  chezmoi (dotfiles) + mise (tool versions); not independently
  cloned/read, only its title/description seen in search results.
