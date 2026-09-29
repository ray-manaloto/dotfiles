# Omarchy x mise dotfiles: cross-reference lane (Lane X), 2026-09-29b

Lane X of `mise-dotfiles-research-briefs-2026-09-29.md`. Agent: general-purpose (Claude Opus 5.5, 1M), session
`5545fa41`. Purpose: settle Ray's dispute of lane O's headline ("Omarchy does NOT yet use mise dotfiles, `mise bootstrap`
or `[dotfiles]` in shipped code", `mise-dotfiles-omarchy-2026-09-29.md` Headline 1) with a SECOND, independent probe route,
separating three claims:

1. Omarchy's **shipped code** invokes mise dotfiles / `mise bootstrap`.
2. Omarchy's **docs/manual or discussions** recommend/support it.
3. **mise documents** an Omarchy workflow.

Status: COMPLETE (written incrementally; final 2026-09-29).

## Evidence log (appended as probes run)

### E1. mise docs mirror (offline) -> Omarchy

Corpus: `docs/research/kb/raw/mise-dotfiles-2026-09-29/mise-docs/` (414 files).

- `grep -rli omarchy mise-docs` -> 386 files; `grep -rhi omarchy | sort | uniq -c`: 386 of those lines are the sponsor
  banner (`[![Omacom Foundation](...omacom-foundation.svg)](https://omarchy.org/patrons/)`), leaving **5 substantive
  locations**:
  - `mise-docs/bootstrap_setup.md:30` — "On Omarchy with Bash, use `~/.bashrc` instead." (setup guide, "Track a file").
  - `mise-docs/bootstrap_setup.md:333` — "On Omarchy, start with individual configuration files you edit. Inspect a
    directory before tracking it: themes, plugins, backgrounds, and application state may not belong in your dotfile history."
  - `mise-docs/history.md:386-392` — "To inspect what an update changed in your tracked dotfiles, wrap it with `capture`.
    For example, on Omarchy: `mise dot capture --label "omarchy update" -- omarchy-update`".
  - `mise-docs/directories.md:94` — "Distributions may collocate system and user storage ... For example, Omarchy can keep
    every tool artifact in the user's home directory" (`system_installs_dir`/`shims_dir`/`system_shims_dir`).
  - `mise-docs/bootstrap_packages_pacman.md:36` — `state = "absent"` removal "works the same for ... configured third-party
    repositories such as the Omarchy Package Repository".
- jdx post `jdx-posts/posts_2026-09-07-dotfiles-that-save-themselves.md:164-186` ("## On Omarchy"): `mise dot track
  ~/.bashrc`, `~/.config/hypr/bindings.conf`, `input.conf`; "Add the `history-watch` service from above and run `mise
  bootstrap`. It runs as a systemd user service."; `mise dot capture --label "omarchy update" -- omarchy-update`.
- Control arms: known-present `history-watch` in mise-docs -> 6 files (probe can hit); a freshly invented nonsense token
  -> 0 files (probe can miss).
- Side finding: `bootstrap_packages_pacman.md:36` documents `state = "absent"` as current behaviour, which contradicts lane O's
  caveat that package `state = "absent"` was "not confirmed as shipped".

### E2. GitHub API, mise -> Omarchy (live, 2026-09-29)

| # | Endpoint / query | rc | Count | Control arms (known-present / fresh-absent) |
|---|---|---|---|---|
| Q1 | `gh api '/search/issues?q=repo:jdx/mise+omarchy&per_page=100'` | 0 | 17 (all PRs; `+is:issue` = 0) | `repo:jdx/mise+bootstrap` = 594; fresh nonsense token = 0 |
| Q2 | GraphQL `search(type:DISCUSSION, query:"repo:jdx/mise omarchy")` | 0 | 15 | `repo:jdx/mise dotfiles` = 130; fresh nonsense token = 0 |
| Q3 | `gh api '/search/code?q=omarchy+repo:jdx/mise'` | 0 | 9 files | `history-watch+repo:jdx/mise` = 25; fresh nonsense token = 0 |
| Q4 | same + `path:src`, `Accept: text-match` | 0 | 4 src files, all incidental | n/a (fragments read) |

Q1 PRs (number, merged_at, title): 13454 (unmerged) self-update machine-wide; 13024 merged `registry: add basecamp`;
12718 merged AUR package manager; 12904 (closed, `merged_at` null) capture history around external commands; 12594 merged
lazy tool shims; 13233 merged resolve every sharing conflict; 13232 merged docs encryption key setup; 13266 merged
`shims.exclude`; 12882 (closed, `merged_at` null) automatic synchronization + fresh-machine bootstrap; the rest are
sponsor/registry/swift/config items. (12882/12904 show `merged_at` null, yet their features are in the live docs
(`history.md` "Capturing an external command"), so they landed another way — I did not chase which commit.)

Q2 discussions authored by jdx that name Omarchy: **#13022** "Proposal: give Omarchy dotfiles automatic history, easy
restore, and optional sync with mise" (2026-09-09); **#12709** "Proposal: give every Omarchy user a declarative 'my machine'
file with `mise bootstrap`" (2026-09-02); **#12597** "Using managed tool-stub bundles for Omarchy's lazy CLI layer". Also
**#12067** "mise use -g silently drops tools when two run concurrently", authored by **`omarchybot`** — Omarchy's own
automation account filing a mise bug about `mise use -g`, i.e. evidence Omarchy's tooling uses mise *for tools*.

Q3 file set on the default branch = `docs/bootstrap/packages/pacman.md`, `docs/bootstrap/setup.md`, `docs/directories.md`,
`docs/history.md`, `README.md`, and 4 `src/` files. **This independently reproduces E1**: the same four docs pages the
offline mirror grep found (route 1 = mirrored HTML, route 2 = GitHub code index of the Markdown source) — so the two probes
agree. The `src/` hits are incidental: sponsor text (`src/cli/sponsors.rs`), a pacman test removing packages named
`omarchy` (`src/system/packages/pacman.rs`), a swift os-release doc comment (`omarchy 4.0.1rc2`), and a history
description test fixture using `~/.config/hypr/bindings.lua` + `~/.config/omarchy/hooks/post-theme`
(`src/system/history/checkpoint.rs`). No Omarchy-specific code path in mise.

### E3. GitHub API, Omarchy -> mise (live, 2026-09-29)

`gh api repos/basecamp/omarchy` rc=0 -> `omacom/omarchy`, default `quattro`; latest release `v4.0.4` (2026-09-15);
`pushed_at` 2026-09-29T19:18Z. `repo:basecamp/omarchy+mise` in issue search -> **rc=1, HTTP 422** ("cannot be searched");
the search index does not follow the rename, so every probe below uses `omacom/omarchy`.

**Issues + PRs** (`gh api '/search/issues?q=repo:omacom/omarchy+<term>&per_page=100'`, all rc=0):

| Term | Total | What the hits are |
|---|---|---|
| `mise` | 391 | tool wrappers, PATH ordering, agent installs |
| `%22mise+dot%22` (quoted phrase) | **0** | — |
| `%22mise+bootstrap%22` (quoted) | 12 | all tokenised noise: PATH/uwsm shims (#13364, #8406, #9171), `mise __node-gyp-bootstrap` (#8327), wrapper recursion (#10300, #13177); none about `mise bootstrap` |
| `mise+bootstrap` (unquoted) | 31 | same classes as above, plus Hermes/OpenClaw runtime installs |
| `mise+dotfiles` | 7 | #6965 "Add git-based backup and restore" (open), #6964 serialize mise global config writes (closed), #7104 XCompose, security PRs — none adds mise dotfiles |
| `dotfiles` | 100 | general |
| `%22dot+track%22` | 1 | #8862 agents punchcard (noise) |
| `%22bootstrap.services%22` | **0** | — |
| `%22history-watch%22` | 9 | all clipboard-history/watcher PRs (noise) |
| `capture` | 1028 | noise (screenshots/clipboard) |
| `%22omarchy-mise-install%22` (known-present control) | 132 | the tools-wrapper bug class |
| fresh nonsense token (absent control) | 0 | — |

**Discussions** (GraphQL `search(type:DISCUSSION)`, all rc=0): `repo:omacom/omarchy "mise dot"` -> 1, `"mise bootstrap"` -> 1,
both **#11029** only (jdx, category Ideas). `mise dotfiles` -> 3 (#11029 + two VM manuals), `history-watch` -> 9 (only
#11029 relevant), `mise` -> 52, `dotfiles` -> 46; fresh nonsense token -> 0.

Live metadata of #11029 (re-fetched, not taken from lane O's mirror): upvotes 4, updated 2026-09-18, 2 top-level comments;
participants by `authorAssociation`: `jdx/NONE` x4, `CaffeinatedTech/NONE` x4, `shawnyeager/CONTRIBUTOR` x2. **No
MEMBER/OWNER/COLLABORATOR (e.g. dhh) has replied**; the thread is unanswered by maintainers and not closed. Its body says
verbatim: "**The mise functionality is available today; the built-in Omarchy experience is still a proposal.** Omarchy already
ships mise. I'd be happy to build the integration and maintain the history and synchronization machinery behind it."

Newly mirrored dotfiles discussions in omacom/omarchy (none mentions mise; `grep -ci mise` = 0 each):
#10682 "Version controlled dotfiles", #11261 "May be `vcsh` is a good framework for dots.", #5588 "First-class Omarchy
backup / restore / check workflow", #191 "Manage your OWN dotfiles with symlinks?".

**Code search** (`gh api '/search/code?q=<q>'`, text-match, rc=0, `incomplete_results=false` on all):

| Query | Total | Notes |
|---|---|---|
| `%22mise+dot%22+org:omacom` | **0** | |
| `%22mise+bootstrap%22+org:omacom` | **0** | |
| `%22mise+dot%22+repo:omacom/omarchy` / `%22mise+bootstrap%22+repo:omacom/omarchy` | **0 / 0** | |
| `%22%5Bdotfiles%5D%22+org:omacom` | 3 | punctuation is stripped by code search: matches are Markdown links `[Dotfiles](manual/31-dotfiles.md)` in README/manual — **this probe cannot see a literal `[dotfiles]` table**, so the clone grep (E4) is the authoritative route |
| `history-watch+org:omacom` | **0** | |
| `dot+capture+org:omacom` | 118 | `plans/dots.md`, screenshot capture code (noise) |
| `mise+org:omacom` (control) | 549 | `install/user/mise.sh`, `bin/omarchy-update-mise`, `bin/omarchy-mise-install`, `etc/mise/conf.d/omarchy.toml`, `omacom/try-omarchy:guest/scripts/register-pinned-mise.sh` ... |
| `omarchy-mise-install+org:omacom` (control) | 53 | |
| fresh nonsense token + `org:omacom` | 0 | |

Org roster (`gh api orgs/omacom/repos`): includes `omacom/omadots` ("Shared configs for Omacoms", last push 2026-07-04),
`omacom/omamac` ("Retired — see https://omarchy.org"), `omacom/try-omarchy` (runs Omarchy on macOS). None surfaced in any
mise-dotfiles code query.

### E4. Omarchy source trees and full history (clones in `$TMPDIR`, deleted after)

Refs: default branch `quattro` @ `8b4eae66da29` (2026-09-29T19:44+02:00, "Merge pull request #13771") — same SHA lane O read;
latest tag `v4.0.4` @ `c668141e9c42` (2026-09-14). Full clone: 185 remote branches, 69 tags, 27,697 commits; plus a fetch
of **all 6,678 `refs/pull/*/head`** (27,677 commits reachable from PR heads; fetch rc=0, 364 s) so unmerged PR code is
covered too.

| Probe | Result | Control arms |
|---|---|---|
| `git grep -n -I -E 'mise (dot\|dotfiles\|bootstrap)\|\[dotfiles\]\|history-watch\|dot capture\|bootstrap\.services\|bootstrap\.files'` on quattro (1,953 files) | rc=0, **2 hits, both Markdown links** `[dotfiles](31-dotfiles.md)` in `manual/03-coming-from-mac-or-windows.md:39` and `manual/05-the-top-bar.md:88` (the `\[dotfiles\]` alternative matching link text, not a TOML table) | `omarchy-mise-install` -> 18 files; fresh nonsense token -> 0 |
| same on v4.0.4 (1,781 files) | same 2 link hits (`05-the-top-bar.md:87`) | `omarchy-mise-install` -> 14 files; fresh token -> 0 |
| co-occurrence `mise.*(bootstrap\|\bdot\b\|history\|capture\|\btrack\b)` excluding `plans/` | only `test/shell.d/default-agent-test.sh` (`mise_history` = a stub call log) and `test/shell.d/dev-env-path-test.sh` ("env-bootstrap appends mise shims") — neither is mise dotfiles | n/a |
| `plans/dots.md`: `grep -ci mise` | **0** (13 × "omarchy dots", 3 × chezmoi) | — |
| `git log --all -S'mise dot'` / `-S'mise bootstrap'` / `-S'history-watch'` / `-S'dot capture'` / `-S'bootstrap.services'` | **0 commits each** — never added, never removed | `-S'omarchy-mise-install'` -> 32 commits; fresh token -> 0 |
| `git log --all -S'[dotfiles]'` | 2 commits (DHH, 2026-08-13, manual chapters) = the Markdown links above | — |
| `git log --all -G'mise[[:space:]]+(dot\|dots\|dotfiles\|bootstrap)([[:space:]]\|$)'` | **0** | `-G'mise[[:space:]]+use[[:space:]]+-g'` -> 38 |
| `git log --remotes=pr -G'<same>\|history-watch\|bootstrap\.services'` over all 6,678 PR heads | 1 commit, `3cf2bbc16` (PR #8956, C++ `bootstrap.services_` member) = **false positive**; no PR ever contained `mise dot`/`mise bootstrap`/`history-watch` | `-G'omarchy-mise-install'` on PR refs -> 162; fresh token -> 0 |
| `git log --all -- plans/dots.md` | exactly one commit: **`022f6993` by David Heinemeier Hansson, 2026-08-15, "Plan the dots feature for preserving and syncing user configs"** | — |

That last row matters for interpretation: jdx's #11029 links "the [Dots plan](https://github.com/jdx/omarchy/blob/022f6993.../plans/dots.md)"
— the same commit, i.e. **DHH's own plan**, carried in jdx's fork. Omarchy's in-house design (by its maintainer) is a
bare-repo `omarchy dots` feature that never mentions mise; jdx proposes backing those same `omarchy dots` commands with
mise history.

Omarchy authored-by probes: `repo:omacom/omarchy+author:jdx` -> 3 (#12828 OCR tests, open; **#9596 "feat(mise): install
default CLI tools through native lazy shims", open**; #8074 "Use mise registry shorthands", closed). jdx has opened **no
Omarchy PR for dotfiles/history**. Control `author:dhh+is:pr` -> 327.

### E5. Omarchy's own docs (manual) on mise

In the quattro tree, 52 manual chapters; `grep -ci mise` non-zero in only three:
- `manual/18-development-tools.md:17,19,33` — mise manages language environments ("`mise use -g ruby`"), `gh` is a
  "lazy-loading mise stub".
- `manual/17-ai.md:3,23,31` — agent CLIs are "tiny mise-managed stubs"; "`omarchy-mise-install <package> [command-name]`".
- `manual/31-dotfiles.md:40` — the `post-update` hook runs "before mise tools are updated". The same chapter's backup advice
  (`:21`) is still: "it's a good idea to backup all these dotfiles. [Stow is a great way to do that](https://www.youtube.com/watch?v=NoFiYOqnC4o)."

The live web manual page mirrored by lane F (`linked/learn-omacom-io/2_the-omarchy-manual_65_dotfiles.md:22`) says the same
Stow sentence and has no mise mention. So Omarchy's docs use mise for **tools** and recommend **Stow** for dotfiles backup.

### E6. Community: Omarchy users who DO run mise dotfiles (GitHub code/repo search, 2026-09-29)

All `gh api -H 'Accept: application/vnd.github.text-match+json' '/search/code?q=<q>&per_page=100'`, rc=0,
`incomplete_results=false`; `jdx/mise` and its mirror `zhcndoc/mise` excluded from the reading below.

| Query | Total | Relevant non-mise hits |
|---|---|---|
| `%22mise+dot%22+omarchy` | 25 | justEstif/dotfiles, iainsimmons/dotfiles, mikeastock/dotfiles, Abhishek-1804/dotfiles, nmc-costa/dotfiles, oppegard/dotfiles, iainsimmons/today-iain-learned (blog) |
| `%22mise+dot%22+hyprland` | 14 | AbaoFromCUG/dotfiles `mise.hyprland.toml`, mtrenker, TudorAndrei, AlinaNova21 (spec), BVisagie/omapicks |
| `%22mise+dot+track%22` / `+hypr` | 54 / 10 | almost all jdx/mise docs+src (known-present control) |
| `%22history-watch%22+omarchy` / `+hypr` | 7 / 13 | tokuhirom/64p.org note, oppegard research, bruhmux/dotfiles `config/config.toml`; mrodrigs hit is a clipboard script (noise) |
| `%22dotfiles%22+omarchy+path:.config/mise` | 4 | iainsimmons/dotfiles `.config/mise/config{,.linux,.macbook,.desktop}.toml` |
| `omarchy+path:.config/mise+filename:config.toml` | 2 | iainsimmons, CoreyCole (tools only) |
| `hypr+path:.config/mise+filename:config.toml+dotfiles` | 0 | (qualifier combo too narrow; the path-only query above is the one that answers) |
| `%22builtin+%3D+%5C%22history-watch%5C%22%22` | 54 | btkostner, nettlesh `mise/config.toml`, h-wb, skills repos |
| fresh nonsense token + `path:.config/mise` | 0 | absent control |

Repo search `search/repositories?q=oma-mise` -> 5, of which three Omarchy **plugins** built on mise:
**FilipHarald/oma-mise** (created 2026-09-08) — "A native Omarchy bar widget for sync activity, tracked-file counts for
[`mise dotfiles`]"; its `bootstrap.py:25` runs `[executable, 'bootstrap', 'dotfiles', 'status', '--json']` and reads
`payload['history']['sync']['declarations_changed']`, `review.py:32` runs `bootstrap dotfiles status|conflicts|history diff`.
chyld/omarchy-mise-radar and raavail-lasso/Omarchy-Mise-Manager are tool-update widgets; mdelgert/omarchy-mise browses mise tasks.
`omacom/omarchy-plugin-registry` tree (367 blobs) has **no** path matching `mise|filip` — oma-mise is not in the official registry
(it appears only in a third-party catalogue, `BVisagie/omapicks:data/unclassified-report.json`: `"id": "filipharald.oma-mise", "name": "Mise dotfiles"`).

Verbatim community evidence that Omarchy users run mise dotfiles today (user-land, not Omarchy-shipped):
- iainsimmons/dotfiles `.agents/skills/dotfiles-mise/SKILL.md`: "Machines today: **Desktop** (Arch+Omarchy, `MISE_ENV=desktop`),
  **Old MacBook** (Arch+Omarchy, `MISE_ENV=macbook`), **Work Mac** (macOS, no `MISE_ENV` — `auto_env` picks up `config.macos.toml`)";
  `.config/mise/config.linux.toml`: `"~/.config/hypr" = { mode = "symlink-each", exclude = ["monitors.lua"] }`. The same author
  filed jdx/mise discussion #13135 ("mise bootstrap dotfiles templates do not support secrets").
- mikeastock/dotfiles `mise.toml`: `min_version = "2026.9.2"` ... "Omarchy extras live in mise.omarchy.toml (`-E omarchy`)".
- Abhishek-1804/dotfiles README: `mise -E omarchy bootstrap plan   # declarative plan (packages + dotfiles)`.
- justEstif/dotfiles `home/.config/fish/conf.d/omarchy.fish`: "Tools that sed-rewrite configs (`omarchy font set`, `omarchy display
  text size`) atomically replace files, severing mise dotfiles symlinks" -> `home/.local/bin/heal-mise-dotfiles` runs
  `mise dotfiles add -g -- "$target"` then restores the link.
- Nishikoh/dotfiles `mise.toml`: link `~/.config/git/ignore` as a file, not the directory, because "~/.config/git には他のツール
  (omarchy など) が config を置く" (other tools such as omarchy put config there).
- nmc-costa/dotfiles `docs/AGENT_OS_UNIFICATION_EVIDENCE.md` (third-party corroboration of the status): "'Dots' proposal (discussion
  #11029): open, PARTIALLY implemented — `mise dot track` and related CLI functionality ... "; its plan keeps chezmoi and says
  "**Revisit trigger:** if Omarchy ships 'Dots' ...".
- oppegard/dotfiles `docs/research/20260917-mise-history-sync-reliability.md` cites omacom/omarchy **#7712** ("gh upgrades leave Git
  credential helper pointing to a deleted versioned binary", open) and PR **#8001** (open) as the cause of a stalled HTTPS history
  sync; remedy "change the mise-history origin from HTTPS to" SSH, then `mise bootstrap services apply` + `mise doctor` (`watcher = running`).

### E7. Web / social fan-out and new page mirrors

`mise run research-fanout -- "omarchy mise dotfiles" --sources exa,firecrawl-search,last30days` -> **rc=0**; manifest
`.agent/kb/raw/research-fanout/omarchy-mise-dotfiles/manifest.json` (exa 10 items 1.5 s, firecrawl-search 10 items 0.8 s,
last30days 10 items 41.3 s). The manifest records `control: null` for every source, so I ran the control myself:
`mise run research-fanout -- "omarchy qwindlestrup mise" --sources exa,firecrawl-search,last30days` -> rc=0, manifest
`.agent/kb/raw/research-fanout/omarchy-qwindlestrup-mise/manifest.json`, **also 10/10/10 items**. So for these semantic
engines the item COUNT cannot discriminate (the absent arm never returns 0); only content can. Content that appears in
the real run and not in the control: jdx/mise#13022, the jdx post, `mikeastock/dotfiles` PR #121 "feat(dotfiles): manage
machine files with mise" (2026-09-17), `timmo001/dotfiles` (uses its own `dot` tool; `"mise dot"` code search in it = 0),
Chris Krycho's "Using mise-en-place for dotfiles", and an r/omarchy thread "Managing dot files with updates". No result is
an Omarchy announcement, release note, or maintainer post adopting mise dotfiles; the last-30-days items about Omarchy
(Omarchy M launch 2026-09-11, Primeagen joining core 2026-09-26, "Why Omarchy Exists") do not mention mise dotfiles.

Firecrawl (CLI 1.24.6, key via env, presence only: `FIRECRAWL_KEY=SET`; sequential, 4 s gap, 3-try 429 retry; credits
545 -> 541, floor 150 never approached):

| URL | Saved | rc | Finding |
|---|---|---|---|
| https://omarchy.org/manual/dotfiles/ (live canonical manual) | `omarchy/web/omarchy-org_manual_dotfiles.md` (9,476 B) | 0 | `mise` = **0** mentions; line 77: "it's a good idea to backup all these dotfiles. [Stow is a great way to do that]" |
| https://omarchy.org/news/2026/09/introducing-omarchy-m/ | `omarchy/web/omarchy-org_news_2026-09_introducing-omarchy-m.md` | 0 | `mise` = 0 |
| https://v5.chriskrycho.com/notes/using-mise-en-place-for-dotfiles/ | `omarchy/web/chriskrycho_using-mise-en-place-for-dotfiles.md` | 0 | mise-based dotfiles note (not Omarchy) |
| https://akitaonrails.github.io/en/2025/09/07/omarchy-2-0-mise-for-organizing-dev-environments/ | `omarchy/web/akitaonrails_omarchy-2-0-mise.md` | 0 | `mise` = 35, `mise dot` = 0 — Omarchy 2.0 uses mise for dev environments (tools) |
| https://www.reddit.com/r/omarchy/comments/1p7n88v/managing_dot_files_with_updates/ | not saved | 1 | firecrawl: "we do not support this site"; `curl .json` -> 403 for both the real id AND a bogus id (probe cannot discriminate); exa `web_fetch` -> `SOURCE_NOT_AVAILABLE`. **UNVERIFIED** content. |

New GitHub threads saved (`gh api`, 0 credits): `omarchy/gh_omacom_omarchy_discussion_{10682,11261,5588,191}.md`,
`omarchy/gh_omacom_omarchy_7712.md`, `omarchy/gh_omacom_omarchy_8001.md`, `omarchy/gh_mikeastock_dotfiles_121.md`; community
files under `omarchy/community/` (10 files: mikeastock `mise.toml` + `mise.omarchy.toml`, iainsimmons `config.toml` +
`config.linux.toml` + blog post, oppegard history-sync research, bruhmux `config/config.toml`, FilipHarald/oma-mise `README.md` +
`bootstrap.py`, justEstif `heal-mise-dotfiles`).

## Verdicts

### Claim (1) — Omarchy's shipped code invokes mise dotfiles / `mise bootstrap`: **REFUTED**

Evidence, independent of lane O's recursive grep: `git grep` on quattro `8b4eae66` and v4.0.4 `c668141e` (only Markdown-link
false positives); `git log --all -S`/`-G` over 27,697 commits on 185 branches + 69 tags (0 commits ever added or removed
`mise dot`, `mise bootstrap`, `history-watch`, `dot capture`, `bootstrap.services`); the same regex over all **6,678 PR heads**
(one C++ false positive, #8956); GitHub code search `"mise dot"`/`"mise bootstrap"`/`history-watch` across `org:omacom` = 0/0/0.
Every control arm hit (`omarchy-mise-install` 18/14 files, 32 commits, 162 PR commits; `mise use -g` 38 commits) and every
fresh-token arm returned 0. What Omarchy does ship is mise **for tools**: `install/user/mise.sh` ("mise settings set
upgrade.auto_prune false"; `omarchy-mise-install codex|claude|gh|...`), `bin/omarchy-update-mise` ("MISE_MINIMUM_RELEASE_AGE=0 mise up"),
`etc/mise/conf.d/omarchy.toml` (a `[tool_alias]` for `cursor-agent`). Even Omarchy's own dotfiles plan, `plans/dots.md`
(sole commit `022f6993`, David Heinemeier Hansson, 2026-08-15), contains the word "mise" **zero** times.

### Claim (2) — Omarchy's docs/manual or discussions recommend/support it: **REFUTED** (for Omarchy's own voice); a third-party proposal exists

- Manual (repo `manual/31-dotfiles.md:21`, live https://omarchy.org/manual/dotfiles/ line 77, and the older
  https://learn.omacom.io/2/the-omarchy-manual/65/dotfiles line 22) recommends **Stow**, verbatim: "it's a good idea to backup
  all these dotfiles. [Stow is a great way to do that]". The manual names mise only for tools (`18-development-tools.md:17,19,33`,
  `17-ai.md:3,23,31`) and in the `post-update` hook timing (`31-dotfiles.md:40`).
- Discussions: the only thread about mise dotfiles is https://github.com/omacom/omarchy/discussions/11029, authored by **jdx**
  (`authorAssociation: NONE` in omacom/omarchy), category Ideas, 4 upvotes, and **no reply from any MEMBER/OWNER/COLLABORATOR**
  (participants: jdx x4, CaffeinatedTech x4, shawnyeager/CONTRIBUTOR x2). Its own body: "**The mise functionality is available
  today; the built-in Omarchy experience is still a proposal.**" Four other Omarchy dotfiles discussions (#10682, #11261 vcsh,
  #5588, #191) never mention mise. jdx has no dotfiles PR in Omarchy (`author:jdx` = 3 items, all tool-related, incl. open #9596
  lazy shims).
- So: "Omarchy recommends/supports mise dotfiles" is refuted; "mise dotfiles for Omarchy is **proposed inside Omarchy's
  discussion forum** by mise's author, unacknowledged by maintainers" is confirmed.

### Claim (3) — mise documents an Omarchy workflow: **CONFIRMED**

- https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/#on-omarchy (mirror line 164-186): "Add the `history-watch`
  service from above and run `mise bootstrap`. It runs as a systemd user service." and
  `mise dot capture --label "omarchy update" -- omarchy-update`.
- https://mise.jdx.dev/history.html#capturing-an-external-command (`mise-docs/history.md:386-392`): "For example, on Omarchy:
  `mise dot capture --label "omarchy update" -- omarchy-update`".
- https://mise.jdx.dev/bootstrap/setup.html (`bootstrap_setup.md:30`, `:333`): "On Omarchy with Bash, use `~/.bashrc` instead.";
  "On Omarchy, start with individual configuration files you edit."
- https://mise.jdx.dev/directories.html (`directories.md:94`): Omarchy example for `system_installs_dir`/`shims_dir`.
- Cross-checked by two routes that agree: offline mirror grep (5 substantive locations) and live GitHub code search in jdx/mise
  (the same 4 docs files + incidental src hits). This is a workflow **a user** runs on Omarchy (Omarchy ships mise), not
  something Omarchy runs.

### Lane O's headline: **RIGHT-BUT-MISLEADING**

- **Right**: its literal claim (claim 1, shipped code) survives an independent, stronger route (full history + every PR head).
  There is no probe disagreement on claim (1); lane O's grep and mine agree.
- **Misleading**, for four reasons:
  1. It collapsed claims (1)-(3) into one headline. Ray's cited evidence (the jdx post's "On Omarchy" section) is claim (3), which
     is TRUE — and lane O never states it as a finding. Its Techniques section does quote the #11029 commands, but attributes the
     `mise dot track` / `history-watch` / `capture` workflow to "the Omarchy proposal", not to mise's shipped docs (history.md,
     bootstrap/setup.md) and the jdx post, where it is documented as runnable today on Omarchy. Hence the dispute: Ray read
     "Omarchy does not use mise dotfiles" as "you can't do this on Omarchy", which is false.
  2. "hits only in `plans/dots.md`" places DHH's plan inside a sentence about mise-dotfiles hits; `plans/dots.md` has **0**
     occurrences of "mise" (its hits came from the `omarchy dots` alternative in lane O's regex). It also called it
     "Omarchy's in-house plan" without noting the author is Omarchy's maintainer, which is the strongest evidence that Omarchy's
     own direction (as of 2026-08-15) was a non-mise bare repo.
  3. Its caveat that package `state = "absent"` was "not confirmed as shipped" is contradicted by the live docs
     (`mise-docs/bootstrap_packages_pacman.md:36`, which even names the "Omarchy Package Repository").
  4. It did not surface the community reality: Omarchy users run mise dotfiles today (E6), including an Omarchy bar plugin
     (FilipHarald/oma-mise) that calls `mise bootstrap dotfiles status --json`.
- Why Ray and lane O disagreed: not a broken probe but two different claims. The post (claim 3) and the code (claim 1) are both
  accurate descriptions of different subjects.

## Techniques for our migration (Mac `~/.config/mise`, devcontainer image, running devcontainer)

Each item names its source; snippets are verbatim from the mirrored file unless marked "ours" (a proposal for this repo).

**X1. Track + one builtin watcher service (the jdx-documented Omarchy/macOS workflow).** bruhmux/dotfiles
(`omarchy/community/bruhmux_dotfiles__config_config.toml`):
```toml
[dotfiles]
"~/.config/hypr" = {}                                  # symlink from the repo (default mode)
"~/.dotfiles/.config/hypr" = { mode = "track" }        # history of the repo SOURCE copy
[bootstrap.services.mise-history]
builtin = "history-watch"
```
The pattern tracks the repo-side sources because "tracking a symlink records the link only" (lane O T7). The watcher is a
"systemd user service on Linux, a LaunchAgent on macOS" (`bootstrap_setup.md:61`); macOS path
`~/Library/LaunchAgents/dev.mise.<name>.plist` (`bootstrap_services.md:53`). Mac first step (ours): `mise dot track
~/.config/mise/config.toml` + the service block, then `mise dot rollback <f> --dry-run` / `mise dot undo` before any `origin set`.

**X2. Prefer `track`/`copy` over `symlink` for files a tool rewrites.** iainsimmons: `"~/.config/hyprmoncfg" = { mode = "copy" }
# hyprmoncfg rewrites profiles in place — keep real files`; justEstif had to write `heal-mise-dotfiles` because `omarchy font set`
"atomically replace[s] files, severing mise dotfiles symlinks" (fix: `mise dotfiles add -g -- "$target"` then relink). mise itself
writes `config.toml` atomically since jdx/mise#12040 (merged 2026-08-15, "write config files atomically"), so **inference to
test (ours)**: `mise use -g` on a symlinked `~/.config/mise/config.toml` likely replaces the link with a regular file. Track it
in place instead of symlinking it.

**X3. Per-machine layering with mise environments, not templates.** mikeastock `mise.toml`: `min_version = "2026.9.2"` ...
"Omarchy extras live in mise.omarchy.toml (`-E omarchy`)"; iainsimmons: `MISE_ENV=desktop` / `MISE_ENV=macbook` and
`config.linux.toml` "auto-loaded via auto_env on linux" with `"~/.config/hypr" = { mode = "symlink-each", exclude = ["monitors.lua"] }`.
Ours: `config.toml` (shared) + `config.macos.toml` (Mac host) + `mise.devcontainer.toml` (`-E devcontainer`), excluding
host-only files the way `monitors.lua` is excluded.

**X4. Managed blocks instead of owning a whole file** (fits image-owned rc files). mikeastock `mise.omarchy.toml`:
```toml
"~/.bashrc/personal" = { block = '''
export PATH="$HOME/.local/bin:$PATH"
''' }
```
"Applying replaces the content between the markers. If the block is missing, mise appends it. Everything else in the file
stays as it is." (`mise-docs/dotfiles.md:489`); "an edit's target is a symlink" is an error (`:510`).

**X5. Bootstrap hooks to clear a previous manager's files** (chezmoi retirement). mikeastock:
```toml
[bootstrap.hooks.pre-dotfiles]
run = '''
rm -f "$HOME/.config/tmux/tmux.conf" "$HOME/.config/tmux"/tmux.conf.bak.*
'''
```
Combine with Omarchy's hash-guarded migration pattern (lane O T2: delete only when `sha256sum == $stock_sha`) so a customised
chezmoi-rendered file is backed up, not removed. Per zero-bash-logic, ours lives in `python/`, invoked by the hook.

**X6. Labeled capture around every mutating step.** `mise dot capture --label "omarchy update" -- omarchy-update` (history.md:391)
-> ours: `mise dot capture --label "lock-image" -- mise run lock-image`, `--label "chezmoi-retire"`, `--label "dev-rebuild"`.
"A capture failure warns and lets the command run with its own exit status" (history.md:404), so it cannot mask a gate's rc.

**X7. Machine-readable health for `doctor.toml`.** FilipHarald/oma-mise `bootstrap.py:25`:
`[executable, 'bootstrap', 'dotfiles', 'status', '--json']` then `payload['history']['sync']['declarations_changed']`;
oppegard: confirm `watcher = running` via `mise doctor`. Ours: a doctor check reading `mise bootstrap dotfiles status --json`
(the conflict pause is global, so it must be surfaced; notifications are absent in a headless container).

**X8. Containers without systemd.** "To run one scan from a timer or cron job, use `mise dot watch --once`"; "`watch --once`
exits 1 if its save was deferred or failed. Only one watcher can run per history store" (history.md:978-982). Ours: in the
running devcontainer call `mise dot watch --once` from a lifecycle hook/timer and read its rc; keep `$MISE_STATE_DIR/history`
in the named home volume, never a bind mount (virtiofs ownership flicker, `.claude/rules/persistence-gate-retry.md`). Never bake
history into the image.

**X9. System-vs-user split = image-vs-person.** Omarchy ships defaults in `/etc/mise/conf.d/omarchy.toml` (`[tool_alias]`) and
jdx's proposal puts default tools in system config "instead of adding them to the user's global mise config"; mise documents an
Omarchy-style collocation (`directories.md:94`: `system_installs_dir = "~/.local/share/mise/installs"`). Ours: image keeps
`mise-system.toml` in the system layer; the tracked, history-bearing layer is only `~/.config/mise/`.

**X10. Sync auth: SSH origin, not HTTPS + credential helper.** omacom/omarchy#7712 "gh upgrades leave Git credential helper
pointing to a deleted versioned binary" stalled an HTTPS history sync (oppegard research). Ours: SSH origin, which matches R2
(Docker Desktop `ssh-auth.sock`) in the container.

**X11. Explicit-update semantics.** Omarchy: `MISE_MINIMUM_RELEASE_AGE=0 mise up` on explicit update, and
`mise settings set upgrade.auto_prune false` because "Upgrades must not delete the version a running process is executing from".
Relevant to a long-running watcher binary on the Mac and in containers.

**X12. Version floor.** mikeastock pins `min_version = "2026.9.2"` (feature release). Lane O reports 2026.9.9 fixes a deletion
race in sync — **inherited, not re-derived here**; re-verify in the mise changelog before pinning our floor.

## Gaps and caveats

- The r/omarchy thread (1p7n88v) could not be read by any route (firecrawl unsupported site; reddit JSON 403 for real and bogus
  ids alike, so that probe cannot discriminate; exa `SOURCE_NOT_AVAILABLE`): content UNVERIFIED.
- The fan-out engines return 10 items for a nonsense query, so their counts are not evidence; only their content was used.
- GitHub code search strips punctuation: `"[dotfiles]"` matched Markdown links. The literal-TOML question was answered by the
  clone grep and pickaxe, not by code search.
- jdx/mise #12882 / #12904 show `merged_at: null` although their features are documented live; which commit landed them was not
  traced.
- X2's symlink-replacement behaviour is an inference from #12040's title/body (atomic write); test it on the Mac before relying on it.
- Omarchy's packaged mise version (whether a stock Omarchy has `mise dot`) was not re-derived; lane O's "2026.9.7 seen by a user
  on 2026-09-15" is inherited.
- Per the brief ("write nothing else in the repo"), this lane did not append to root `findings.md`/`progress.md`; the coordinator
  should persist a condensed entry.
- Clones (`om-head`, `om-tag`, `om-full` incl. 6,678 PR refs, 1.7 GB) were in the session scratchpad and deleted.

## GitHub repos touched

- [omacom/omarchy](https://github.com/omacom/omarchy) — full history + all PR heads pickaxed; issues/PRs/discussions searched; discussions 11029/10682/11261/5588/191, issues 7712/8001 read
- [jdx/mise](https://github.com/jdx/mise) — issue/PR/discussion/code search for omarchy; PR 12040 read
- [omacom/omarchy-plugin-registry](https://github.com/omacom/omarchy-plugin-registry) — tree checked for mise plugins (none)
- [omacom/omadots](https://github.com/omacom/omadots), [omacom/omamac](https://github.com/omacom/omamac), [omacom/try-omarchy](https://github.com/omacom/try-omarchy) — org roster check
- [FilipHarald/oma-mise](https://github.com/FilipHarald/oma-mise) — Omarchy bar plugin over `mise bootstrap dotfiles status --json`
- [chyld/omarchy-mise-radar](https://github.com/chyld/omarchy-mise-radar), [mdelgert/omarchy-mise](https://github.com/mdelgert/omarchy-mise), [raavail-lasso/Omarchy-Mise-Manager](https://github.com/raavail-lasso/Omarchy-Mise-Manager) — Omarchy mise tool/task plugins
- [mikeastock/dotfiles](https://github.com/mikeastock/dotfiles) — `-E omarchy` mise dotfiles config; PR 121
- [iainsimmons/dotfiles](https://github.com/iainsimmons/dotfiles), [iainsimmons/today-iain-learned](https://github.com/iainsimmons/today-iain-learned) — MISE_ENV per Omarchy machine; blog post
- [bruhmux/dotfiles](https://github.com/bruhmux/dotfiles) — track + history-watch config
- [justEstif/dotfiles](https://github.com/justEstif/dotfiles) — symlink drift self-heal on Omarchy
- [oppegard/dotfiles](https://github.com/oppegard/dotfiles) — mise history sync reliability research
- [Abhishek-1804/dotfiles](https://github.com/Abhishek-1804/dotfiles), [Nishikoh/dotfiles](https://github.com/Nishikoh/dotfiles), [nmc-costa/dotfiles](https://github.com/nmc-costa/dotfiles), [AbaoFromCUG/dotfiles](https://github.com/AbaoFromCUG/dotfiles), [mtrenker/dotfiles](https://github.com/mtrenker/dotfiles), [CoreyCole/dotfiles](https://github.com/CoreyCole/dotfiles), [timmo001/dotfiles](https://github.com/timmo001/dotfiles) — code-search hits (read via text-match fragments)
- [BVisagie/omapicks](https://github.com/BVisagie/omapicks) — third-party plugin catalogue listing oma-mise
