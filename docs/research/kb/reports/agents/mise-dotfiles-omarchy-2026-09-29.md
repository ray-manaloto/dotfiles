> **SUPERSEDED IN PART (2026-09-29b).** The headline "Omarchy does not use mise dotfiles or `mise bootstrap`"
> is RIGHT-BUT-MISLEADING: true of Omarchy's shipped code, but it omits that mise itself documents an Omarchy
> workflow (jdx post "On Omarchy", `history.md`, `bootstrap/setup.md`) and that Omarchy users run it. Adjudicated by
> the Opus cross-reference (`omarchy-mise-crossref-2026-09-29.md`) and the research sweep
> (`omarchy-mise-dotfiles-crossref-sweep-2026-09-29.md`), which agree. Kept verbatim below, unedited.

# Omarchy + mise dotfiles/bootstrap/history: lane O report, 2026-09-29b

Lane O (Omarchy) of `mise-dotfiles-research-briefs-2026-09-29.md`. Agent: general-purpose, claude-sonnet-5-5, session-default effort.
Mirror root: `docs/research/kb/raw/mise-dotfiles-2026-09-29/omarchy/` (55 files, 1.1 MB); rows appended to `../INDEX.md`
(section "Omarchy lane"). Paths below are relative to that raw root unless stated.

## Headline findings (read this first)

1. **Omarchy does NOT yet use mise dotfiles, `mise bootstrap` or `[dotfiles]` in shipped code.** Control-armed: a
   grep of a full clone at the default branch (`quattro`, `8b4eae66`) and at the latest release (`v4.0.4`, `c668141e`)
   for `mise (bootstrap|dotfiles)|\[dotfiles\]|history-watch|omarchy dots` finds hits only in `plans/dots.md` and two manual
   pages (quattro); v4.0.4 has no `plans/dots.md` at all. The integration is a **proposal** (jdx/mise discussions #12709,
   #13022; omacom/omarchy discussion #11029), plus a community PR (omacom/omarchy #12037) that implements a *different*,
   non-mise `omarchy dots` (bare git repo + Python). jdx states this himself: "what's still a proposal is the built-in Omarchy
   integration" (`omarchy/gh_omacom_omarchy_discussion_11029.md`, reply 2026-09-13T20:05).
2. **What Omarchy really uses mise for today is tools, not dotfiles**: `omarchy-mise-install` wrapper stubs in
   `~/.local/bin`, `mise use -g`, `mise up`, `mise settings set upgrade.auto_prune false`, and (open PR #9596) a
   system-level `/etc/mise/config.toml` of lazy tools that a user's `~/.config/mise/config.toml` overrides.
3. **The repo moved**: `basecamp/omarchy` now resolves to `omacom/omarchy` (default branch `quattro`, latest release
   `v4.0.4`, 2026-09-15). The Omarchy manual domain is `learn.omacom.io`; `manuals.omamix.org` answers 301 to it.
4. The mise-side design (the part that matters for our migration) is fully documented in jdx's proposals and PRs and is
   mirrored; the highest-value technique set is under "Techniques" below.

## Queries table (every query, rc, control arm)

| # | Query | rc | Result | Control arm |
|---|---|---|---|---|
| 1 | `gh api repos/basecamp/omarchy` | 0 | full_name `omacom/omarchy`, default `quattro` (redirect) | n/a |
| 2 | `gh api repos/omacom/omarchy/releases` | 0 | v4.0.4 latest (2026-09-15), v4.0.3, .2, .1, .0 | n/a |
| 3 | `gh api 'repos/omacom/omarchy/git/trees/{quattro,v4.0.4}?recursive=1'` (first attempt unquoted, zsh glob error rc!=0, re-run quoted) | 0 | 1953 / 1781 blobs; mise-related paths: `bin/omarchy-mise-install`, `bin/omarchy-update-mise`, `etc/mise/conf.d/omarchy.toml`, `install/user/mise{,-work}.sh`, `plans/dots.md` (quattro only), 4 `test/shell.d/*mise*` | tree grep `README.md` = 8 hits, `zzfoobarq` = 0 |
| 4 | `git clone --depth 1` default + `--branch v4.0.4`, recursive grep `mise` (excluding themes/tests) and `mise (bootstrap\|dotfiles)\|\[dotfiles\]\|history-watch\|omarchy dots\|omarchy-dots` | 0 | mise appears only as tools tooling (18 files use `omarchy-mise-install`); dotfiles-feature hits only in `plans/dots.md`, manual 03/05 (not mise-dotfiles related) | `omarchy-mise-install` = 18 files (present); `zzqfoo9` = 0 |
| 5 | `/search/issues?q=repo:jdx/mise+omarchy` | 0 | 17 hits (PRs 12882, 12904, 13232, 13233, 12594, 13266, 13454, 12718, ...) | `repo:jdx/mise+zzqfoo9x` = 0 |
| 6 | `repo:omacom/omarchy+mise+dotfiles` / `+mise+bootstrap` / `+dots+history` / `+mise+lazy` | 0 | 7 / 31 / 7 / 69 hits (PR 12037, 6965, 10358, 9596, issues 10300, 13177, 13708, ...) | same fresh-term arm = 0 |
| 7 | `repo:basecamp/omarchy+...` (old owner name) | 1 (HTTP 422) | search rejects the moved repo name: **a probe with the old name cannot see anything**; use `omacom/omarchy` | the same query with `omacom` returns hits |
| 8 | GraphQL `search(type:DISCUSSION)` `repo:omacom/omarchy mise bootstrap OR dotfiles OR history` | 0 | 52 hits; the relevant one is #11029 (rest are agent-roster requests) | `repo:jdx/mise zzqfoo9x` = 0 |
| 9 | GraphQL discussion(number) fetch: jdx/mise 13022, 12709, 12597, 13135, 12067; omacom/omarchy 11029, 12038, 6874 | 0 | saved with comments and replies | nonexistent number 99999999 returns NOT_FOUND |
| 10 | `gh api repos/{r}/issues/{n}` + comments + pulls reviews/files: jdx/mise 12882, 12904, 13232, 13233, 13454, 12594, 13266, 12718, 10373, 12918, 12083, 12692; omacom/omarchy 12037, 6965, 10358, 9596, 10300, 13177, 13708, 6964 | 0 | saved | `jdx/mise` #12709 via issues API FAILED (it is a discussion, not an issue); refetched via GraphQL (query 9) |
| 11 | `curl -I` learn.omacom.io, manuals.omamix.org, omarchy.org; bogus path | 200 / 301 to learn.omacom.io / 200; bogus = 404 | domains verified | bogus path 404 |
| 12 | `gh api gists/9e4e1e2a...` | 0 | CaffeinatedTech's Mason + mise sync gist | n/a |
| 13 | `repo:jdx/mise+chroot+bootstrap`, `+"enable-only"`, `+bootstrap+packages+absent+omarchy`, `+"setup+repository"+container` | 0 | oci PRs 10373/12083; `"enable-only"` returned 179 noisy hits (quoted phrase is tokenised, NOT a phrase match: **do not treat as evidence**) | fresh term = 0 |

## Sources mirrored (count, size, credits)

- GitHub threads, PRs and discussions (via `gh api`, 0 credits): 28 markdown files under `omarchy/gh_*.md`
  (PR files include body, comments, review comments, reviews, changed-file list; 12882 is 262 KB, 12594 155 KB).
- Omarchy source at both refs, `omarchy/src/{quattro,v4.0.4}/` (10 files quattro, 9 at v4.0.4; refs recorded in `omarchy/src/REFS.txt`).
- Firecrawl (7 scrapes, `learn.omacom.io` manual pages 62 development-tools, 107 ai, 115 omarchy-cli, 101 system-snapshots,
  96 manual-installation, 57 shell-tools, 97 mac-support): all rc=0 on attempt 1, 21 KB total.
  **Credits 568 to 561 (7 used; threshold 150 never approached; no 429 seen; run sequentially with a 4 s gap).**
- Reused, not re-fetched: `mise-docs/history.md` (60 KB), `mise-docs/bootstrap_setup.md`, `cli_dotfiles_*`, `dotfiles.md`,
  `linked/learn-omacom-io/*65_dotfiles.md`, `*68_updates.md`, `jdx-posts/posts_2026-09-07-dotfiles-that-save-themselves.md`.
- No other jdx.dev post about Omarchy exists in the mirror (grep of `jdx-posts/`: only the 2026-09-07 dotfiles post and sponsors).
- Gist: `linked/gist/CaffeinatedTech_9e4e1e2a_mason-lock-mise-sync.md`.
- Not mirrored on purpose: the Omarchy manual pages already contained verbatim in the repo `manual/` directory
  (the git clone is the authoritative, newer copy: the web manual predates quattro's `.lua` Hyprland files).

## Techniques (with verbatim quotes)

### T1. Omarchy's own model: defaults in system scope, user overrides in user scope
- "Wherever tooling supports system defaults and user overrides, Omarchy should put its defaults in the system configuration and leave personal configuration to the user ... it declares Omarchy's default tools in `/etc/mise/config.toml` instead of adding them to the user's global mise config." (`omarchy/gh_jdx_mise_discussion_13022.md`, Body).
- On quattro today only a `[tool_alias]` file exists at `etc/mise/conf.d/omarchy.toml` (`src/quattro/etc/mise/conf.d/omarchy.toml`); the lazy-tools list is PR #9596 (open) and needs mise 2026.9.4+.
- Overrides: `[settings] disable_tools = ["cursor-agent"]` in `~/.config/mise/config.toml`; system config sets `locked_scopes = ["project", "global"]` (`omarchy/gh_omacom_omarchy_9596.md`).
- jdx verified layering empirically: "the plan showed the union of both, the user's entries won on shared keys, and each line named the config that declared it." (discussion 12709).

### T2. Tool wrappers, first-run and update flow (real source)
- `src/quattro/bin/omarchy-mise-install` writes `~/.local/bin/<cmd>`: `export MISE_MINIMUM_RELEASE_AGE=0; mise use -g --quiet <pkg> || exit 1; exec mise x <pkg> -- <bin> "$@"`. Lots of bug history: recursion through PATH (omarchy issues #6349, #7234, #13177, #10300), stubs not restorable after `~/.local/bin` cleared (#13708). Lesson: hand-rolled wrapper stubs were the failure class that native lazy shims (PR #9596, mise PR #12594) replaced.
- `src/quattro/bin/omarchy-update-mise`: `MISE_MINIMUM_RELEASE_AGE=0 mise up`, comment: cooldown holds releases back for days, running `omarchy update` "is the user asking for current versions now".
- `src/quattro/install/user/mise.sh`: `mise settings set upgrade.auto_prune false` with the comment "Upgrades must not delete the version a running process is executing from".
- First-run in offline contexts: `src/quattro/install/user/mise-work.sh` switches on `OMARCHY_SETUP_CONTEXT` (`iso-chroot`, `provision-owner`, runtime), unpacks a bundled Node tarball into `~/.local/share/mise/installs/node/<ver>`, `mise use -g node@<ver>`, then loosens the pin: `mise config set tools.node latest --file ~/.config/mise/config.toml` because an exact pin "would exempt Node from mise up forever". Migration `migrations/1790457067.sh` repaired exact pins written earlier.
- Migrations are timestamped scripts (`migrations/<epoch>.sh`) run by `omarchy update`; mise-related ones (e.g. `1789095456.sh`) only remove byte-for-byte matches of stock templates (`sha256sum == $stock_sha`), back up customized files, and never touch user-owned ones.
- Update hook ordering documented in the manual: `post-update` runs "before mise tools are updated" (`src/quattro/manual/31-dotfiles.md`).
- Package management is not mise: mise itself is the `mise-bin` pacman package (`migrations/1786952219.sh`), self-update is disabled machine-wide via `/etc/mise/mise-self-update-instructions.toml` (mise PR #13454, closed unmerged in the snapshot we read, so treat as unshipped: re-verify).

### T3. Omarchy's dotfile posture and the two competing history designs
- Manual: `~/.config` files are "your files"; Omarchy's are in `/usr/share/omarchy`; backup advice is only "Stow is a great way to do that" (`src/quattro/manual/31-dotfiles.md`).
- `plans/dots.md` (Omarchy's in-house plan, rev 3) rejected chezmoi/yadm/Stow, chose a **bare repo at `~/.local/share/omarchy/dots.git`** over `$HOME` driven only by constrained commands, hermetic git (`GIT_CONFIG_GLOBAL=/dev/null`, synthetic identity, no hooks, `--no-verify`), an **audited manifest** ("Tracking is `git add -f --pathspec-from-file=<manifest>` only"), a `local` tier for machine-specific files ("the lightweight answer to chezmoi's hostname templates: exclude, no DSL"), "stand down" when Stow/chezmoi/yadm/symlinks are detected, labeled before/after snapshot pairs around each batch mutation, and sync as **squash-published current state**, not history.
- mise's design (jdx, discussion 11029/13022) differs on exactly these axes: it shares saved history including intermediate edits ("I'd keep one history for now"), has no per-file local-only tier (would need a second store), and uses variants instead. This divergence is the key design decision for us (see history design notes).
- Community PR #12037 (jordanhubbard, open) implements the Omarchy-native variant (manifest at `default/dots/manifest`, `dots.py` 540 lines, 13 real-git two-home tests, three-way merge, persistent conflicts, "conflicting changes require an explicit choice instead of a remote-wins fallback"). Not mise-based; useful as a test-design reference.

### T4. mise history/restore mechanics used in the Omarchy proposal (verbatim)
```sh
mise dot track ~/.bashrc                                  # baseline checkpoint + declaration in ~/.config/mise/config.toml
mise bootstrap services apply                             # starts [bootstrap.services.mise-history] builtin = "history-watch"
mise dot status
mise dot history --path ~/.bashrc
mise dot rollback ~/.bashrc --dry-run ; mise dot rollback ~/.bashrc ; mise dot undo
mise dot capture --label "omarchy update" -- omarchy-update
mise dot history diff --operation --patch
```
Source: `omarchy/gh_omacom_omarchy_discussion_11029.md`. Store: "History lives in a bare Git repository at `$MISE_STATE_DIR/history/repo.git`, separate from the files you edit" and "Checkpoints restore file contents. They do not restore installed packages or the running state of a service." (`mise-docs/history.md`, lines ~880-890). Capture: "A capture failure warns and lets the command run with its own exit status" (history.md:404; PR 12904). `mise dot watch --once` exists "for timers and cron" (`mise-docs/cli_dotfiles_watch.md`), the only non-systemd/launchd path documented.
- Version notes from the thread: features shipped in 2026.9.2; `mise dot` alias 2026.9.8; `track --encrypt` and identical-file adoption 2026.9.9; "Please upgrade both machines to 2026.9.9 or newer before continuing sync. That release fixes a race that could record untouched files as deleted and sync those deletions to the other machine." (reply 2026-09-15).

### T5. Bootstrap / first-run flow (fresh machine)
- `mise bootstrap --adopt git@github.com:me/dotfiles.git` (needs mise, git, repo auth): restores shared config first, then tracked files selected for this machine, remembers origin, then runs bootstrap (`mise-docs/history.md` ~335). Existing differing files: `mise dot status`, `mise dot conflicts PATH`, `mise dot pull --take-remote|--keep-local PATH`. `--replace-history --dry-run` previews discarding unrelated local history.
- Setup repositories are recognised by a `.mise-history/format.toml` marker and fetched into mise's bare store, "instead of cloning into `~/.config/mise`" (PR 12882 summary). This is the design point contradicting the older Omarchy proposal (`~/.config/mise` as a git checkout, `omarchy setup dotfiles <url>`, discussion 12709). The shipped mechanism is the history store, not a checkout.
- Proposed Omarchy order (discussion 12709): 1) `[bootstrap.services]`/`[bootstrap.files]` beside `[tools]` in system mise config, applied from `omarchy update`/`omarchy-migrate`; 2) `omarchy setup dotfiles`, run `mise bootstrap` from update; 3) package removal (`state = "absent"`), AUR, enable-only mode "so the same declarations can run at install time and on the installed system" (installer runs in a chroot with no live systemd).
- Remote: `mise bootstrap remote --host devbox --install-mise --from-git jdx/dotfiles --github-relay-read-only ...` borrows read-only GitHub access without copying a token (PR 12882).

### T6. Per-machine differences
- Variants: `"~/.zshrc" = { mode = "track", variants = [{ os = "macos" }, { os = "linux" }] }` or `mise dot track ~/.zshrc --os macos` (`mise-docs/dotfiles.md` ~686; history.md:333: stored as `home@macos/`). Selectors: `os` (optional `/arch`), `profile` (a mise environment), documented at `mise-docs/dotfiles.md:246-250`.
- jdx suggested "mise environments (`-E work`, `-E home`) handle the differences from one config" (discussion 12709) and "separate variants selected by OS or a mise environment" (11029).
- Omarchy's classification of what NOT to share: `monitors.lua` (per machine), `input.lua` (mixed; PR 12037 later flipped it to shared after a live cross-machine failure: the `local` tier silently filtered a file, so resolving conflicts could never transfer it), `autostart.lua`, `~/.XCompose` (seeded with name/email).

### T7. Secrets and safety
- "an accidentally saved credential can remain in history after being deleted from the live file"; `mise dot track <f> --encrypt` with `[history.encryption].recipients` (public age recipients incl. an independent recovery key; private identity via `settings.age.identity_files`/`key_file`); "mise blocks publishing that history by default" if older plaintext exists (11029; jdx post 2026-09-07, "Private files in a shared repository").
- Not covered: "a token accidentally saved in an ordinary, unencrypted `.zshrc` won't be caught by this check" (jdx post). Our repo's `no_env_dump`/gitleaks gates stay separate.
- Nested git repos inside a tracked directory are skipped (history.md "Nested repositories").
- Tracking a symlink records the link only; Stow/chezmoi users need stand-down (11029).

### T8. Containers (what Omarchy/jdx say, and gaps)
- Nothing about devcontainers in Omarchy. Closest: chroot-safe first-run via `OMARCHY_SETUP_CONTEXT` (T2), "enable-only mode for services and firewall" as a *planned* mise capability (12709; not confirmed shipped), airtonix's `mise bootstrap` + `mise oci` idea for atomic OCI images (12709 comments), and mise's own `mise oci build` baking project `[system.files]` and `apt:` packages into image layers (mise PR #10373; `mise-docs/cli_oci_build.md`, `dev-tools_mise-oci.md`, `cli_generate_devcontainer.md` are in the mirror).
- The history watcher is a user service (systemd/launchd/Scheduled Task); no doc describes it in a container without systemd, except `mise dot watch` foreground and `--once`.

## Migration lessons

### (a) macOS `~/.config/mise` (this Mac)
1. Track files individually, never `~/.config/mise` wholesale; enrol `config.toml` explicitly, since "Tracking `.zshrc` alone doesn't include those declarations" (jdx post). Scripts under `~/.config/mise` are tracked file by file or by an explicit directory only after inspecting for nested repos, caches, state.
2. Start local-only: `track` + `history-watch` (LaunchAgent on macOS, confirmed in `bootstrap_setup.md:61`), prove `rollback --dry-run` and `undo` before any `origin set`. Mirrors Omarchy's own staged rollout: "local autosave, labeled migration/refresh history, and restoring one file", remote later.
3. Keep credentials out: this repo's rule is secrets live in fnox; anything credential-like in `~/.config/mise` (tokens in env blocks) must be `--encrypt` with a recovery recipient before first capture or excluded. History is permanent once published.
4. Use `capture` around our risky mutating commands (e.g. `mise run lock`, tool bumps): `mise dot capture --label "<task>" -- mise run <task>` gives a labeled before/after pair (does NOT undo package effects).
5. Pin mise 2026.9.9+ on the Mac before any two-machine sync (the deletion-race fix); the Omarchy package lagged (2026.9.7 seen by a user on 2026-09-15).
6. Gotcha from the mirrored post: it shows Hyprland `.conf` names while quattro ships `.lua`. Docs age fast; verify paths against the real tree.

### (b) Docker devcontainer images
1. Build-time state belongs to declarative bootstrap/`mise oci`/`mise generate devcontainer` (no watcher, no history): in a Dockerfile use enable-only-style declarations or plain files; the history store and watcher are runtime-of-a-person features and should not be baked into an image (leaks history, machine identity, `$MISE_STATE_DIR`).
2. Copy Omarchy's context switch: one script branching on a context variable (`iso-chroot`, `provision-owner`, `runtime`) so the same first-run logic works offline and at runtime; for us a `DOTFILES_CONTEXT=image|container|host` analogue lives in `python/`, not bash (repo zero-bash-logic rule).
3. Loosen pins written at build time when they should float (`tools.node = latest` after installing the bundled tarball); conversely keep exact pins in image fragments. Never let a build-time exact pin leak into a user-overridable file (migration `1790457067.sh` cost them a repair).
4. System vs user layering maps cleanly to image vs container: image ships `/etc/mise/conf.d/*.toml` (our `mise-system.toml` analogue), user layer is `~/.config/mise/config.toml` from the tracked setup. Keep the image layer free of personal state.
5. Byte-for-byte, hash-guarded migrations (sha256 of the stock template before deleting) are the safe way to retire an old chezmoi-generated file.

### (c) Running devcontainers
1. Two options, decide with Ray: (i) run `mise bootstrap --adopt <setup repo>` in `postCreateCommand`, or (ii) bind-mount/generate configs and use `mise dot watch --once` from a timer. There is no documented supported path for the watcher in a systemd-less container; treat `--once` as the untested route and test it in the real container (both arms).
2. Use variants with `os = "linux"`/`arch` or `profile` = a mise environment (`-E devcontainer`) rather than templates for per-target differences; keep `monitors`-style host-specific files out of the shared set (Omarchy's `local` tier idea is a NON-goal in mise: separate store needed).
3. Git identity: history commits use `mise <mise@localhost>` unless configured; the container needs Git auth for the watcher (`history.md` ~327: credential helper written to `~/.gitconfig`).
4. Docker Desktop virtiofs ownership flicker (repo rule persistence-gate-retry) applies to tracked paths on bind mounts: keep the history store in a named volume, not a bind mount.

## History-tracking design notes (for the plan)

- **One shared history vs squash-publish.** mise: shared, full ancestry, fast-forward/merge, never force-push (`history.md` ~337). Omarchy's plan: squash-publish current state so old secrets never leave the machine. Choose deliberately: with mise we must encrypt or exclude BEFORE first save, because "Untracking stops future capture but doesn't erase old commits."
- **Whole-setup conflict pause**: any conflict pauses publish and apply for every file; local saves continue; desktop notifications by default; `status`/`doctor` report `failing_since`. Design a doctor check for our `doctor.toml` (`mise doctor` exposes the pause).
- **History is not a backup**: covers tracked file contents only; OS/package recovery stays with snapshots/image rebuild (jdx post). For us: history + image pinning + git remote are three separate layers.
- **Labeled operations** (`capture --label`, `history --label`, `history diff --operation`) map onto our tasks (`ship`, `land`, lock refresh) and give "what changed during the last update" as a query.
- **Omarchy `.bak` retained during rollout**: they keep the old safety net until restore is proven; mirror that by keeping chezmoi live until mise history restore is proven per file class.
- **Real-git two-home tests** (PR 12037: 13 tests, bare remote, conflicts, interrupted apply) are the model for our acceptance tests; they arm both the merge and the conflict path.

## Gaps and caveats

- No shipped Omarchy code uses mise dotfiles; everything Omarchy-specific is a proposal, so any "Omarchy does X with mise dotfiles" statement in our plan must say "proposed".
- The `enable-only` mode, package `state = "absent"`, and AUR status were not confirmed as shipped (search returned noise; mise PR #12718 AUR title only). Re-verify against the mise release notes at plan time.
- mise PR #13454 (`self-update` machine-wide) shows state closed with `merged_pr: n/a` in my snapshot; whether it merged another way is unverified.
- Discussion 12038 (conflict-resolution design in Omarchy) and omacom/omarchy-pkgs were not read beyond saving 12038.
- Credentials: none printed; firecrawl key presence only (status showed "Authenticated via FIRECRAWL_API_KEY").
- Firecrawl only touched 7 pages: the rest was GitHub/API data, which is more faithful than a scrape.
- The manual pages scraped from the web (`manual-web/`) predate quattro (they reference `.conf` Hyprland files elsewhere); prefer `src/quattro/manual/`.

## GitHub repos touched

- [omacom/omarchy](https://github.com/omacom/omarchy) — source at quattro and v4.0.4, issues/PRs/discussions (moved from basecamp/omarchy)
- [jdx/mise](https://github.com/jdx/mise) — discussions 12709/13022/12597/13135/12067; PRs 12882, 12904, 12918, 13232, 13233, 13454, 12594, 13266, 12718, 12692, 10373, 12083
- [jordanhubbard/omarchy](https://github.com/jordanhubbard/omarchy) — fork behind PR 12037 (referenced, not cloned)
- [jdx/omarchy](https://github.com/jdx/omarchy) — jdx's branch holding the Dots plan (referenced; identical plan read from omacom/omarchy quattro)
- [omacom-io/omarchy-pkgs](https://github.com/omacom-io/omarchy-pkgs) — mise-bin packaging (referenced only)
- [zapling/mason-lock.nvim](https://github.com/zapling/mason-lock.nvim) — referenced by the neovim/mise sync gist
