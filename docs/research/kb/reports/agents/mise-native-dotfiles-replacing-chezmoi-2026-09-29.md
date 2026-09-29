# mise native dotfiles vs chezmoi — synthesis (2026-09-29)

**Question.** How does mise's native dotfiles support (`[dotfiles]` config
section, `mise dotfiles` / `mise dot` commands, `mise bootstrap`) work as of
the latest mise release; what does it cover and not cover compared with
chezmoi (templating, per-OS/per-host differences, secrets, run-once scripts,
file modes, symlink vs copy, drift detection); and how would a user-global
`~/.config/mise` config plus scripts be managed from a git dotfiles repo with
it?

**Version pinned for this report.** Latest published release is
**v2026.9.17** (`gh release list -R jdx/mise` → `isLatest: true`,
published 2026-09-29T10:06Z; release commit `5a5b9286`). The v2026.9.18
release PR (#13815) is still **OPEN**, so anything merged after
v2026.9.17 (notably #13822 `?ref=` for `bootstrap --from`, merged
2026-09-29T17:05Z) is on `main` but **unreleased**. Source/doc claims below
were re-read from a sparse clone of the v2026.9.17 tag (`docs/`,
`src/system/`, `src/cli/dotfiles/`, `settings.toml`).

## Answer

**How it works.** `[dotfiles]` is a declarative table in any mise config
file, keyed by target path. Each entry names a source (relative sources
resolve from the directory of the declaring config file, or implicitly from
`dotfiles.root`, default `~/.dotfiles`) and a `mode`. Entries merge across
the config hierarchy (whole-file entries by target path, edit entries by
`(path, id)`). Nothing is applied implicitly: `mise dot apply` (also spelled
`mise dotfiles apply` / `mise bootstrap dotfiles apply`) applies them, and
`mise bootstrap` applies them as step 9 of a fixed machine-setup sequence
(after packages, files, services, repos; before shell activation, macOS
defaults, launchd/systemd, user, `mise install`, the `bootstrap` task and the
`final` hook). `mise install` never touches dotfiles.

**Modes.** `symlink` (default, configurable via `dotfiles.default_mode`;
`dotfiles.relative_symlinks` gives Stow-style relative links),
`symlink-each` (per-file links in a real directory, unmanaged neighbours
kept, own links pruned), `copy`, `template` (Tera engine), `absent` (remove a
file or symlink — never a directory), plus `track` (added 2026.9.2: file
stays in place, a background watcher saves Git checkpoints to a separate
history store at `$MISE_STATE_DIR/history/repo.git`, optionally synced
two-way to a private remote). Also `block`/`line` edit entries that manage a
marker-delimited piece of a file, and permission-only entries.

**Coverage vs chezmoi.**

| Concern | mise v2026.9.17 | vs chezmoi |
|---|---|---|
| Templating | `mode = "template"`, Tera; `env`, `vars`, `exec()`, `os()`, `arch()`; `remove_empty = true` deletes the target when the render is empty (conditional file) | Covered, different engine; no `.chezmoi.toml.tmpl` data/prompt machinery, no `.tmpl` suffix/filename-attribute encoding; templates cannot be reverse-captured (`dot add --changed` skips them) |
| Per-OS / per-profile | `variants = [{ os = ... }, { profile = "work" }, { default = true }]`; most specific wins, ties invalid, no match + no default skips | Covered for OS(+arch) and mise environment (`-E`/`MISE_ENV`). **No hostname selector** — the `Variant` struct has only `os`, `profile`, `default`. Host differences must go through a per-host mise environment or template `exec()` |
| Secrets | `[bootstrap.secrets]` maps names to env vars (fnox as the intended provider); `{{ secret(name=...) }}` in templates; redacted from diffs/output; all resolved before any mutation | Covered at the env-var boundary only; no built-in keychain/1Password/vault functions. `secret()` does not quote/escape |
| Encrypted-at-rest sources | Only for `track` entries: `[history.encryption] recipients` + `encrypt = true`; push refuses branches with plaintext versions | **Not covered** for copy/symlink/template sources (chezmoi's age-encrypted source files have no equivalent) |
| Run-once / run-onchange scripts | **None.** `[bootstrap.hooks]` phases and `[tasks.bootstrap]` run on **every** selected apply; docs tell you to make them idempotent. `[history.reload]` runs after writes to matching files (incl. bootstrap writes since #13509) | **Gap.** No `run_once_`/`run_onchange_` state tracking; you guard it yourself |
| File modes | `permissions = "0600"` on copy/template/inline content; permission-only entries (e.g. `"~/.ssh" = { permissions = "0700" }`); status reports mode drift, apply resets it; inline `content` defaults to 0600; template output inherits source mode; `track` history records non-default modes of files and intermediate directories (#13412) | Covered, but not with symlink/symlink-each/track modes; ignored on Windows |
| Symlink vs copy | Per-entry choice + global default; Windows symlink falls back to copy | Richer than chezmoi (which only copies, or symlinks via `symlink_` sources) |
| Drift detection | `mise dot status` (applied/missing/differs/source missing), `status --missing` exits 1, `mise dot diff`, `--json` | Covered (≈ `chezmoi status`/`diff`/`verify`) |
| Reverse capture | `mise dot add <target>`; `mise dot add --changed` for copy-mode files | Covered (≈ `chezmoi add`/`re-add`), not for templates |
| Deletion | `mode = "absent"` removes files (OS-scopable via variants); unapply removes only what still matches what mise wrote | Covered for files; **no directory removal**; deleted sources in a directory copy leave stale copies behind |
| Externals/archives | `[bootstrap.repos]` for git repos | No archive/URL `externals` equivalent found |
| Privilege | Writes as the current user; no sudo | Same as chezmoi (neither elevates) |

**Managing `~/.config/mise` + scripts from a git repo.** Two documented
patterns:

1. **Adopt pattern (whole config dir is the repo).** `mise bootstrap --adopt
   <repo>` clones the repo into `$MISE_CONFIG_DIR` (normally
   `~/.config/mise`): `config.toml`, `config.<env>.toml`, `conf.d/`, `tasks/`
   ride along and stay live for future mise commands; `-E work` selects a
   profile; `--update` fast-forwards an existing checkout whose origin
   matches. File tasks in `tasks/` are the natural home for scripts. Pinning a
   branch/tag via `?ref=` (#13822) is **unreleased** as of v2026.9.17.
2. **Self-managing pattern (repo elsewhere).** Clone to e.g.
   `~/src/dotfiles`, set `dotfiles.root`, and declare
   `"~/.config/mise/config.toml" = "~/src/dotfiles/mise/config.toml"`
   (symlink default). Use the real repo path for first-run sources, and the
   source must already be a valid config because replacing the active global
   config affects every later mise invocation. Scripts/bins go through
   `"~/.local/bin" = { source = "bin", mode = "symlink-each" }` so the
   target keeps unmanaged files; symlinked scripts keep the exec bit that git
   tracks (`permissions` is not allowed on symlink modes).

Setup that chezmoi would put in `run_once_` scripts goes into
`[tasks.bootstrap]`, written to be idempotent.

## Evidence

| Claim | URL or file:line | Quote |
|---|---|---|
| Latest release is v2026.9.17; v2026.9.18 not yet released | `gh release list -R jdx/mise`; `gh pr view 13815` | `{"isLatest":true,"publishedAt":"2026-09-29T10:06:19Z","tagName":"v2026.9.17"}`; `{"mergedAt":null,"state":"OPEN","title":"chore: release 2026.9.18"}` |
| `[dotfiles]` is applied only by explicit commands | src/system/files.rs:1-21 (v2026.9.17) | "`[dotfiles]` — declarative config files (dotfiles) applied by `mise dot apply` or `mise bootstrap`, and removed by `mise dot unapply`." |
| Three spellings of the command set | docs/dotfiles.md:1097-1101 | "The documentation uses the short `mise dot` alias. The descriptive `mise dotfiles` spelling and `mise bootstrap dotfiles` namespace provide the same commands." |
| Mode table incl. `absent` | docs/dotfiles.md:209-219 | "`absent` … Remove a file or symlink at the target; takes no source." |
| `absent` never removes a directory | docs/dotfiles.md:275 | "An `absent` entry never removes a directory, or anything else that is" |
| Default mode / relative symlinks settings | settings.toml:578-599 | "`[dotfiles.default_mode]` default = \"symlink\"" ; "`[dotfiles.relative_symlinks]` default = false" |
| Relative source resolution | docs/dotfiles.md:487-489 | "`source = \"ssh/config\"` in `~/.config/mise/config.toml` refers to `~/.config/mise/ssh/config`." |
| Templates (Tera context) | docs/dotfiles.md:379-393 | "Templates can use `env`, `vars`, `exec()`, and the rest of the template context." |
| Secret redaction | docs/dotfiles.md:397 | "Secret values are redacted from diffs and other command output." |
| Secrets provider boundary is env | docs/bootstrap/secrets.md:7-11 | "Values come from the environment, making secret managers such as fnox the provider boundary rather than adding provider-specific credentials to mise." |
| Variant selectors are os/profile/default only (no hostname) | src/system/history/select.rs:10-20 | "`pub os: Vec<String>` … `pub profile: Option<String>` … `pub default: bool`" |
| No run-once concept | grep `run_once\|run_onchange\|run-once` over docs+src → 0 (control: `symlink-each` → 60) | — |
| Hooks/task run every apply | docs/bootstrap.md:220 | "Hooks and the `bootstrap` task run on every selected apply, so make them safe to repeat." |
| Bootstrap ordering | docs/bootstrap.md:141-184 | "9. `mise dot apply` applies `[dotfiles]`." |
| Permissions key | docs/dotfiles.md:499-554 | "Set `permissions` to an octal string … It works with `copy` and `template` entries that have a file source, and with inline `content`" |
| Permission-only entry | docs/dotfiles.md:533 | "`\"~/.ssh\" = { permissions = \"0700\" }`" |
| Track history records intermediate-directory modes | docs/history.md:1159-1165; PR #13412 (merged 2026-09-20) | "Tracking `~/.claude/settings.json` inside a `0700` `~/.claude` records that mode, so a fresh machine recreates the directory private rather than world-readable." |
| Drift detection exits non-zero | docs/dotfiles.md:715-741 | "Use `status --missing` in scripts to exit with status 1 when any selected entry is out of sync." |
| Reverse capture excludes templates | docs/dotfiles.md:837-854 | "The command skips directory copies, symlinks, templates, and inline content." |
| Directory copies do not prune | docs/dotfiles.md:228-235 | "Directory copies keep existing target files when you delete or exclude their sources. Review and remove those leftover copies yourself." |
| Encryption only for tracked files | docs/history.md:855-870 | "`\"~/.config/app/credentials\" = { mode = \"track\", encrypt = true }`" |
| Track mode is in-place, auto-saved | https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/ | "mise leaves the file where it is, as a regular file… mise saves your changes automatically." |
| Track added in 2026.9.2 | same post | "That's what I added to mise bootstrap in mise 2026.9.2." |
| Tracking only in system/global config | docs/dotfiles.md:1054-1057 | "Tracking entries belong in system or global configuration. mise warns and ignores `mode = \"track\"` in project configuration." |
| `track --dry-run` exists | src/cli/dotfiles/track.rs:61-63; docs/dotfiles.md:860-873 | "Show what each path expands to (files, size, what is left out) without tracking it" ; "Tracking shows the count and size before confirmation and warns above 5,000 files or 256 MiB." |
| Per-entry include/exclusions for track | docs/history.md:575-590 | "`\"~/.codex\" = { mode = \"track\", include = [\"config.toml\", \"rules/**\"] }`" |
| Nested repos skipped and reported, not gitlinked | docs/history.md:1183-1188 | "mise skips its contents and reports its path during tracking, saving, status, and path listing. It does not create a commit pointer for the repository." |
| Credential omissions now reported by save/track/status | docs/dotfiles.md:924-926 | "`mise dot save`, `mise dot track`, and `mise dot status` report these omissions" |
| Reload runs after bootstrap writes | PR #13509 (merged 2026-09-23) | "`[history.reload]` commands already run after `mise dot apply` writes a matching dotfile (#13414), but the dotfiles phase of `mise bootstrap` … ran none of them." |
| Reload is not setup; first adopt does not run new reloads | https://github.com/jdx/mise/blob/main/docs/history.md | "commands that arrive in the same update, including the first `mise bootstrap --adopt`, do not run for it. Put setup steps … in `[tasks.bootstrap]`." |
| Adopt clones into `$MISE_CONFIG_DIR` | docs/bootstrap.md:81-97 | "mise clones it into `$MISE_CONFIG_DIR`, normally `~/.config/mise`… `config.toml`, `config.work.toml`, `conf.d/`, and `tasks/` stay available to future mise commands." |
| Self-managing global config | docs/dotfiles.md:1069 | "`\"~/.config/mise/config.toml\" = \"~/src/dotfiles/mise/config.toml\"`" |
| Scripts via symlink-each | src/system/files.rs:8-17 | "`\"~/.local/bin\" = { source = \"bin\", mode = \"symlink-each\" }`" |
| No sudo | docs/dotfiles.md:1080-1095 | "Dotfiles write as the current user — there is no sudo here." |
| Partial pulls unsupported | https://github.com/jdx/mise/blob/main/docs/history.md | "Pull applies the complete incoming file set… partial pulls are not supported." |
| `?ref=` for `bootstrap --from` is merged but unreleased | https://github.com/jdx/mise/pull/13822 (merged 2026-09-29T17:05Z, after v2026.9.17 at 10:06Z) | "To check out a branch, tag or commit instead of the default branch, append `?ref=` to the URL" |
| Real-world migration gap report | https://github.com/jdx/mise/discussions/13410 (2026-09-20) | "[dotfiles] Six gaps found migrating a real setup off chezmoi" |

## Conflicts resolved

1. **Discussion #13410 (2026-09-20) vs v2026.9.17 source/docs.** The
   discussion reported six gaps. Four are **superseded** by merged PRs and are
   present in the v2026.9.17 tree; I trusted the tag's source/docs (newer,
   primary) over the discussion (older, secondary):
   - "`mise dot track` has no `--dry-run`" → `track.rs:61-63` has `dry_run`
     with a file-count/size preview, and tracking warns above 5,000 files /
     256 MiB.
   - "per-entry `exclude` not available for track" → per-entry `include` and
     exclusions now documented for track entries (history.md:575-596).
   - "parent directories recreated 0755" → fixed by #13412; history.md:1159-1165
     documents recording intermediate-directory modes.
   - "nested repos become silent gitlinks" → history.md:1183-1188: skipped and
     reported, no commit pointer (older history's pointers are skipped on pull).
   - "credential guard silent in `dot save`/`status`" → dotfiles.md:924-926
     says save, track and status report omissions; #13483 delivers warnings
     from background captures.
   - "no after-apply/after-pull hook" → **partly** addressed: `[history.reload]`
     now fires on `dot apply` (#13414) and bootstrap writes (#13509), but it is
     still explicitly not a setup hook and does not fire for commands arriving
     in the same first adopt; #13435 ("finish a new machine with a task the
     setup names") was **closed unmerged**. So this gap stands: setup lives in
     `[tasks.bootstrap]`, run every time.
2. **"Five modes" (mise.jdx.dev page claim) vs "six incl. track".** Both
   true at different granularity: the deployment table lists five
   (symlink/symlink-each/copy/template/absent) and `track` is the separate
   history mode (`files.rs:44-68` parses all six). Trusted source.
3. **"mise does not sync permissions" vs "mise records modes in manifest".**
   Not a contradiction: declarative `permissions` govern copy/template/
   permission-only entries; the history store records modes for `track`
   entries. Different subsystems.
4. **Latest release: v2026.9.17 vs a "release 2026.9.18" item in the
   manifest.** The manifest item is the release **PR** #13815, which is OPEN;
   `gh release list` shows v2026.9.17 as latest. Trusted the release API.
5. **"`absent` cannot remove directories" vs #13518 "remove directories mise
   created once they are empty".** #13518 is about cleanup of parent
   directories mise itself created (unapply/absent side effect), not an
   `absent` entry targeting a directory; dotfiles.md:275 is authoritative.

## Gaps

- **unverifiedEmpty:** the triage list was empty — no source returned an
  unverified empty result.
- **FAILED READS:** none reported.
- **jonpulsifer/infra ADR 0011 ("Migrate dotfiles from chezmoi to mise").**
  exa returned the URL but the reader reported the file not found in a repo
  search. Its content is **unknown** (possibly a wiki path, renamed, or
  private); this is a gap, not evidence the ADR does not exist.
- **Discussion #13410 follow-up replies** were not read; whether the author
  confirmed the fixes is unknown.
- **Hostname-based selection** was established only by absence in the
  `Variant` struct and docs; whether a template helper exposes the hostname
  (e.g. `exec(command="hostname")` works; a dedicated function) was not
  checked in `src/system/templating.rs`.
- **Windows behaviour** (symlink fallback to copy, permissions ignored) is
  documentation-only here; not exercised.
- **No real invocation** was run: nothing here is a live `mise dot apply`
  against this repo's layout. Per `real-integration-evidence.md`, the
  migration's feasibility for this repo is **unverified** until a scratch
  `HOME` run exercises apply/status/unapply with both arms.
- **Unreleased behaviour on `main`** (12 commits after v2026.9.17; only
  `docs/bootstrap.md` and `src/cli/bootstrap.rs` changed in dotfiles paths
  per the lane's diff) — `?ref=` lands in 2026.9.18, not yet released.
- Community migration write-ups (tommeurs.nl, the listed dotfiles repos)
  were surfaced by triage but not read in this synthesis.
- **Critic gap: no live run.** apply/status/unapply were never exercised against a real mise binary, so behaviour (symlink into `~/.config/mise`, symlink-each, `status --missing` exit codes, permissions) is docs/source-only. Next probe: in a scratch HOME with mise 2026.9.17, run `mise dot apply/status --missing/diff/unapply` for `~/.config/mise/config.toml` and `~/.local/bin` symlink-each; record exit codes.
- **Critic gap: hostname selection** is inferred only from absence in the `Variant` struct; `src/system/templating.rs` and the template-context docs were never read for a hostname/os/arch helper or chezmoi-style data/prompts. Next probe: read them at v2026.9.17 and render `{{ hostname }}` or an equivalent.
- **Critic gap: jonpulsifer/infra ADR 0011** and community migration write-ups (tommeurs.nl, public dotfiles repos) are unread. Next probe: search the repo tree via `gh api`; fetch the post; grep public repos for `[dotfiles]` with variants.
- **Critic gap: Discussion #13410 replies** are unread, so the maintainer response and the status of the run-once gap are unknown. Next probe: `gh api` the comments and search for run-once/after-apply hook issues or PRs.
- **Critic gap: release currency.** Unreleased main was checked only for dotfiles paths, and v2026.9.18 may have shipped since. Next probe: re-run `gh release list -R jdx/mise` and diff v2026.9.17..latest for `docs/dotfiles.md`, `docs/bootstrap.md`, `src/system/`.
- **Critic gap: chezmoi-side claims** (no encrypted source for non-track entries, externals, run_onchange semantics) rest on memory, not a fresh read of chezmoi docs or version. Next probe: fetch chezmoi.io reference pages for scripts, encryption and externals, and confirm the current release.
- **Critic gap: secrets.** fnox integration and `[bootstrap.secrets]` resolution were not tested; the claim that `secret()` does not escape is unverified beyond docs. Next probe: render a template with `secret(name=...)` containing quotes/newlines in a scratch HOME with an env var set.
- **Critic gap: adopt conflicts.** Behaviour is unexamined when `~/.config/mise` already exists, when the repo also holds non-mise dotfiles, and when adopt is combined with `[dotfiles]` in the same config. Next probe: run `mise bootstrap --adopt` on a scratch repo with a pre-existing `~/.config/mise`.

## Verification

Refuter and critic both ran. Refuter checked five load-bearing claims against the v2026.9.17 source and docs and `gh`. Result: 5 confirmed, 0 refuted, 0 unverified.

| Claim | Verdict | Evidence |
|---|---|---|
| Latest release is v2026.9.17; release PR #13815 open; #13822 merged but unreleased | confirmed | `gh release list`: v2026.9.17 Latest (2026-09-29T10:06Z), no 9.18. #13815 "chore: release 2026.9.18" is OPEN. #13822 MERGED 2026-09-29T17:05Z, after the release. |
| `[dotfiles]` applied only by explicit command; modes symlink/symlink-each/copy/template/absent/track plus block/line and permission-only entries | confirmed | `files.rs` header: "only ever applied by an explicit command". `FileMode` enum has Symlink, SymlinkEach, Copy, Template, Content, Track, Absent, Permissions. `docs/dotfiles.md:209-219` (modes table) and `:663-669` (`block=`/`line=`). |
| No run_once/run_onchange; hooks and bootstrap task run every apply; #13435 closed unmerged | confirmed | `grep -rli 'run_once\|run_onchange'` over docs and src returned nothing. The control term `symlink-each` matched 2 files, so the grep discriminates. `docs/bootstrap.md:220`. #13435 CLOSED with mergedAt null. |
| Variants select only on os(+arch), profile, default; no hostname selector; secrets from env only; encryption only for track entries | confirmed | `select.rs` `Variant` has only os, profile, default, with `deny_unknown_fields`. Hostname appears only as a `{hostname}` placeholder in the history `git_email`. `secrets.md` says env only. `history.md` ~855-870 shows `encrypt = true` on a `mode=track` entry. |
| Global `~/.config/mise` from git via `bootstrap --adopt`, or a symlink entry plus symlink-each | confirmed | `docs/bootstrap.md:81-97`. `docs/dotfiles.md:1059-1078`. `files.rs` header shows symlink-each for `~/.local/bin`. |

**Effect on the conclusion.** Nothing was refuted, so no Answer or Recommendation text is struck or corrected. The recommendation stays: do not replace chezmoi wholesale yet, and use the scratch-HOME spike for `~/.config/mise` and `~/.local/bin`. The confirmations cover docs and source only. The critic gaps below (no live run, hostname templating, chezmoi-side claims) keep feasibility for this repo unverified.

## Recommendation

For **this repo**, do not replace chezmoi wholesale yet; the fit is
asymmetric:

- mise dotfiles covers the Mac-host side well and is attractive for
  `~/.config/mise` itself: `mise bootstrap --adopt` (or a symlink entry into a
  repo checkout) plus `symlink-each` for scripts and `[tasks.bootstrap]` for
  idempotent setup is a smaller surface than chezmoi templates for the
  user-global mise config. Note the repo's standing rule that `chezmoi apply`
  is blocked on the host — mise dotfiles would be the first sanctioned host
  apply path, which is itself a policy decision for Ray.
- The devcontainer side relies on chezmoi features mise lacks: `run_once_`/
  `run_onchange_` scripts (the repo's `run_*.sh.tmpl`), `.chezmoi.os`-style
  data plus hostname-level differences, and per-machine data prompts. Porting
  requires rewriting every run-once script as an idempotent
  `[tasks.bootstrap]` step.
- The `track` (auto-save/two-way sync) model is orthogonal to chezmoi and
  conflicts with a reviewed-diff git workflow (history lives in a separate
  bare repo with its own remote); keep it out of scope unless Ray wants
  auto-synced machine state.

Next step, if pursued: a spike that manages only `~/.config/mise/config.toml`
and `~/.local/bin` via `[dotfiles]` in a scratch `HOME`, with `mise dot
status --missing` as the control arm (rc=1 before apply, rc=0 after), on a
pinned release (≥ 2026.9.18 if `?ref=` pinning is wanted).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — v2026.9.17 source/docs (dotfiles, history, bootstrap, settings), releases, PRs #13412/#13414/#13435/#13483/#13509/#13513/#13518/#13815/#13822, discussion #13410
- [jonpulsifer/infra](https://github.com/jonpulsifer/infra) — searched for ADR 0011 chezmoi→mise; file not found (gap)
