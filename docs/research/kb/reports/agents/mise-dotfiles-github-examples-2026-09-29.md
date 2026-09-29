# mise native dotfiles — GitHub examples (Lane G), 2026-09-29

Status: COMPLETE. Lane G, sonnet-class agent, 2026-09-29. Queries logged with real rc.

## Query log
| # | query | endpoint | count | rc | notes |
|---|---|---|---|---|---|
| 1 | `"[tools]" filename:mise.toml` (POSITIVE control) | `gh api -X GET search/code -f q=… -f per_page=5` | 26816 | 0 | probe can return hits |
| 2 | `zzqvbx7913nonexistent filename:mise.toml` (NEGATIVE control, invented fresh) | same | 0 | 0 | probe can return 0 |
| 3 | `"[dotfiles]" filename:mise.toml` | same, then `--paginate per_page=100` | 281 reported / 257 returned | 0 | pagination caps below reported total |
| 4 | `"[dotfiles]" path:.config/mise` | same | 71 / 71 | 0 | matches `.config/mise/config*.toml` + conf.d |
| 5 | `"[dotfiles]" filename:config.toml path:.config/mise` | same | 43 | 0 | subset of 4 |
| 6 | `"[dotfiles]" (path:**/mise.toml OR path:**/config.toml)` (the web-UI query verbatim) | same | - | 1 (HTTP 422) | `ERROR_TYPE_QUERY_PARSING_FATAL unable to parse query!` — REST legacy syntax has no OR/parens/`**` |
| 7 | `gh search code '"[dotfiles]"' --filename mise.toml --limit 100 --json repository,path` | `gh search code` (same /search/code) | - | 1 | `HTTP 403: API rate limit exceeded` — code-search bucket is 10 req/min; hit right after --paginate. A 403 is NOT "no results" |
| 8 | pre-flight `gh api rate_limit` | core | code_search limit 10/min, search 30/min | 0 | check `.resources.code_search.remaining` before a burst |

Union of queries 3+4 = 326 unique (repo,path). VERIFIED each by fetching the raw file
(`gh api -H 'Accept: application/vnd.github.raw' repos/<o>/<r>/contents/<path>`, core quota, 2 fetch failures for paths containing `##`)
and grepping `^\[+dotfiles`: **306 files really contain a `[dotfiles]` table; 19 do not** (false positives: the legacy
tokenizer drops punctuation so `"[dotfiles]"` ≈ the word `dotfiles`, which also matches the repo name/path — control arm:
the 19 misses, e.g. `cnwangjie/dotfiles .config/mise/conf.d/tools.toml`). So the raw hit count overstates by ~6%; always verify content.
Trap hit while scripting: in zsh `read -r repo path` CLOBBERS `$PATH` (tied variable) -> `tr: command not found`; use `fp`.

Usage census over the 306 verified files (`grep -ho 'mode *= *"…"'`): symlink 1248, symlink-each 355, copy 126,
template 101, track 33, shims 2, activate 2, generate 1. Inline keys seen: source, variants, mode, min_version, exclude, block, content, cache, fpath.
Sibling sections co-occurring: [bootstrap] 311 files, bootstrap.macos.defaults 177, bootstrap.hooks 120, bootstrap.services 26,
bootstrap.macos.launchd.agents 24, bootstrap.brew 20, bootstrap.directories 12, bootstrap.repos 12, bootstrap.files 9.

Extra queries (independent searches, all `gh api`, rc=0):

| # | query | endpoint | count | rc | notes |
|---|---|---|---|---|---|
| 9 | `repo:jdx/mise dotfiles` | `GET search/issues` per_page=40 | 288 | 0 | PRs + issues; nearly all the recent ones are `feat(dotfiles)` PRs Sept 2026 |
| 10 | `repo:jdx/mise dotfiles is:issue` | `GET search/issues` | 38 | 0 | mostly pre-2025 noise (tokenizer matches unrelated); real ones #13746 #13636 #13653 #13655 |
| 11 | `repo:jdx/mise dotfiles` type DISCUSSION first:15 | `gh api graphql` `search(type:DISCUSSION)` | 130 | 0 | the richest source: 13410, 13135, 13394, 13045, 13578/9, 13787 |
| 12 | discussion bodies 13410 / 13135 / 13394 | graphql `repository.discussion(number:)` | 3 | 0 | maintainer replies read |

Not run (out of budget, no need): `mise bootstrap` as a bare code query, `symlink` + `[dotfiles]` (tokenizer would collapse to
`symlink dotfiles`), README migration searches. The `[dotfiles]` corpus (306 files) already contains the migration stories in comments.

## Working method (what actually works against the code-search API)
- REST `/search/code` = LEGACY syntax: implicit AND, `filename:`, `path:`, `extension:`, `repo:`, `user:`, `language:`, quoted phrases.
  NO `OR`, NO parentheses, NO `**`, NO regex (422 `ERROR_TYPE_QUERY_PARSING_FATAL`). Run one query per alternative and union with `sort -u`.
- Punctuation is dropped by the tokenizer: `"[dotfiles]"` searches the word `dotfiles`, so path/repo-name hits are false positives
  (6% here). Always fetch the file and grep the literal `^\[+dotfiles`.
- `--paginate` with `per_page=100` returned 257 of a reported 281 (index churn/cap); treat `total_count` as an estimate.
- Rate limit: code_search bucket 10/min (check `gh api rate_limit --jq .resources.code_search`), search 30/min. A burst of
  paginate + `gh search code` returned HTTP 403 (query 7). Space bursts >=60s apart or read `reset`. 403 is NOT zero results.
- Verification fetch uses the core bucket (5000/h): `gh api -H 'Accept: application/vnd.github.raw' repos/<o>/<r>/contents/<path>`.
  Paths containing `#` (`##class.home`) fail URL encoding -> record as fetch failures, not misses.
- zsh trap: never name a loop variable `path`.
- Recency: no sort option gives recency for code; the feature is <1 month old so any real `[dotfiles]` hit is recent.

## Examples table (all files fetched and read; URLs are `https://github.com/<repo>/blob/HEAD/<path>`)
| repo | file | pattern | snippet (verbatim) |
|---|---|---|---|
| david-driscoll/dotfiles | `.config/mise/config.toml` (https://github.com/david-driscoll/dotfiles/blob/HEAD/.config/mise/config.toml) | Closest match to our goal: repo owns `~/.config/mise/config.toml` and `scripts/`; per-OS layer files linked with `variants`; `dotfiles.root`; postinstall hook task | `dotfiles.root = "~/dotfiles"` / `"~/.config/mise/config.toml" = { source = "~/dotfiles/.config/mise/config.toml" }` / `"~/.config/mise/scripts" = { source = "~/dotfiles/.config/mise/scripts", mode = "symlink-each" }` / `"~/.config/mise/config.macos.toml" = { source = "~/dotfiles/.config/mise/config.macos.toml", variants = [{ os = "macos" }] }` and comment "The macOS platform layers have to be linked from HERE, not from their own [dotfiles]: mise only reads config.macos.toml once it is already in ~/.config/mise" |
| Pandoks/.dotfiles | `.config/mise/config.toml` | Shorthand string form, relative to the config file; whole `~/.config/mise` dir self-linked; agent files | `"~/.config/mise" = "." # mise directory` / `"~/.claude/CLAUDE.md" = "../../AGENTS.md"` / `"~/.codex/AGENTS.md" = "../../AGENTS.md"` / `[bootstrap.user]` `login_shell = "/bin/zsh"` |
| iainsimmons/dotfiles | `.config/mise/config.toml` (+ `config.{macos,linux,desktop,macbook}.toml`) | Templates + `symlink-each` + per-host layers | `"~/.gitconfig" = { source = "../../.gitconfig.tmpl", mode = "template" }` / `"~/.config/opencode" = { mode = "symlink-each", exclude = ["node_modules","package.json","package-lock.json","bun.lock"] }` / `"~/.agents/skills" = { mode = "symlink-each", exclude = ["dotfiles-mise"] }` |
| h-wb/dotfiles | `mise.toml` ("chezmoi removed") | Template + secrets-from-env vars, permissions, permission-only entries, `variants` with per-OS `target` | `"~/.ssh/config" = { source = "home/ssh/config.tmpl", mode = "template", permissions = "0600" }` / `"~/.ssh" = { permissions = "0700" }` / `"zshrc" = { source = "home/zshrc", mode = "symlink", variants = [{ os = "macos", target = "~/.zshrc" }] }` / `[vars]` `git_email = "{{ get_env(name='GIT_EMAIL', default='') }}"`; template body `email = {{ vars.git_email }}`; header: `mise run apply -> fnox exec -c fnox.toml -- mise bootstrap` |
| cnwangjie/dotfiles | `.config/mise/config.toml` + `conf.d/{tools,packages,tasks}.toml` | Full chezmoi replacement, split across conf.d | "Replaces the former chezmoi setup. `mise bootstrap` runs, in order: packages -> dotfiles -> macos-defaults -> launchd -> user -> tools -> task"; `experimental = true # bootstrap/dotfiles are experimental (mise >= 2026.6.6)`; `dotfiles.root = "~/.dotfiles"` |
| guitsaru/dotfiles | `mise.toml` | chezmoi `private_` replacement via post-dotfiles hook; worktree guard | `post-dotfiles = ['mkdir -p ~/.ssh && chmod 700 ~/.ssh', 'chmod 600 ~/.ssh/config ...']`; `pre-dotfiles = ''' test "$(git rev-parse --git-dir)" = "$(git rev-parse --git-common-dir)" || { echo "run mise bootstrap from the main checkout: from a worktree, [dotfiles] would link into it" >&2; exit 1; } '''` |
| jefftriplett/dotfiles | `mise.toml` | Default mode + empty entries | `dotfiles.default_mode = "symlink"` then `"~/.bashrc" = {}` `"~/.claude" = {}` |
| nrminor/.dotfiles | `.config/mise/config.toml` | Third-party repos as sources via `[bootstrap.repos]` + `symlink-each` with `exclude` | `"~/.config/opencode/command" = { source = "~/.local/share/agent-sources/autoresearch/.opencode/commands", mode = "symlink-each", exclude = [ "complete-next-task.md", ... ] }` |
| xqm32/dotfiles | `.config/mise/conf.d/dotfiles.toml` | `block` = managed fragment inside a file (chezmoi-modify-like) | `"~/.zshrc/zsh" = { block = """ source <(~/.local/bin/mise activate zsh) ... """ }` |
| mattniedelman/dotfiles | `.config/mise/conf.d/dotfiles-tracking.toml` | Pure tracking, no repo tree | `"~/.config/herdr/config.toml" = { mode = "track" }` |
| erzz/dotfiles | `mise.toml` | fnox/1Password-rendered templates via `bootstrap files apply`; forced dotfile apply of one path | `run = """fnox exec --replace -- mise -C "$HOME/dotfiles" bootstrap files apply --yes"""`; `mise ... bootstrap --force-dotfiles dotfiles apply --yes ~/.config/fnox` |
| tdkn/dotfiles | `.config/mise/conf.d/40-dotfiles.toml` | Repo self-link, `conf.d` and `tasks` dirs linked | `"~/.dotfiles" = "~/ghq/github.com/tdkn/dotfiles"` / `"~/.config/mise/conf.d" = "~/.dotfiles/.config/mise/conf.d"` / `"~/.config/mise/tasks" = "~/.dotfiles/.config/mise/tasks"` |
| Guria/mise-config-roots-repro | `case*/bundles/{a,b}/mise.toml` | Maintainer-facing bug repro (config_root/source resolution across bundles) | `"~/.config/demo" = { source = "srcA", mode = "copy" }` |

Repo-level patterns from the 306-file census: `mode` symlink (default; 1248 uses) > symlink-each (355) > copy (126) > template (101) > track (33);
`variants = [{ os = "macos" }]` (26 macos, 21 linux, 3 windows) and `{ profile = "work"|"personal"|"wsl" }`; per-entry `permissions = "0600"` (8) / `"0700"` (2);
`hooks`: 120 files use `[bootstrap.hooks]` (`pre-packages`, `post-packages`, `pre-dotfiles`, `post-dotfiles`); 311 pair `[dotfiles]` with `[bootstrap]`.

## Tips and tricks (each grounded in the examples above)
1. `dotfiles.root = "~/dotfiles"` in `[settings]` makes `"~/.zshrc" = {}` infer its source (`<root>/.zshrc`); `dotfiles.default_mode = "symlink"` removes `mode =` noise (jefftriplett). Both need `experimental = true` (cnwangjie).
2. Shorthand: `"<target>" = "<source>"` is a symlink; relative sources resolve against the CONFIG FILE's directory (Pandoks `"../../.zshrc"`), `~/...` sources against home.
3. Self-hosting `~/.config/mise`: link the whole dir (Pandoks, iainsimmons) or `config.toml` + `conf.d` + `tasks`/`scripts` individually (tdkn, david-driscoll). Whole-dir link breaks per-machine untracked files; `symlink-each` + `exclude` is the fix.
4. Per-OS/host: put layer files `config.macos.toml` etc. in the repo and link them from the BASE config with `variants = [{ os = "macos" }]` (mise only reads a layer once it is present in ~/.config/mise). `variants` may also override `target`/`source` per os.
5. chezmoi `private_` has no equivalent in git modes: use `permissions = "0600"` per entry, or permission-only entries `"~/.ssh" = { permissions = "0700" }` (never creates a missing target).
6. Templates: `mode = "template"` renders tera with `{{ vars.x }}`; keep secrets out of files via `[vars]` reading env (`get_env`) and run under `fnox exec` (h-wb, erzz). Native `secret()` inputs for dotfile templates landed via jdx/mise#13140.
7. `block = """..."""` targets `"~/.zshrc/<name>"` to manage a fragment of a file (xqm32).
8. Guard hooks: `pre-dotfiles` can refuse to run from a git worktree so links do not point into a throwaway checkout (guitsaru).
9. Before tracking a directory: `mise dot track --dry-run <dir>` / `mise dot paths --preview <dir>`; scope junk with `mise dot exclude '~/.codex/sessions/**'` (absolute globs), not `**/sessions/**` (discussion 13410).
10. `mise bootstrap` order per cnwangjie: packages -> dotfiles -> macos defaults -> launchd -> user -> tools -> task; `[history.reload]` runs commands after `dot pull/apply`.
11. Bootstrapping order trap: a config that itself arrives via `[dotfiles]` is not yet in the global config on a first adopt, so reload/hook tables are empty; use a bootstrap task (jdx reply, 13410 item 6).

## Gotchas / upstream issues found
- #13410 discussion "Six gaps found migrating a real setup off chezmoi" (https://github.com/jdx/mise/discussions/13410): track swallowed 33,014 files; exclude on track entries (#13418), permission capture (#13412), nested repos (#13416/#13422), credential-store omission (#13415/#13427 `[history] protect`), reload after apply (#13414). All closed within days.
- #13135 -> PR #13140: dotfile templates initially had no `secret()` inputs; workaround `[bootstrap.files]`.
- #13394: `mode = "track"` inside `config.unix.toml` still deploys on Windows because enrollment lives in shared `.mise-history/manifest.json`, not per-config (jdx: documented, not a loader bug).
- #12763: `[bootstrap.files].source` does not expand `~` while `[dotfiles].source` does.
- Feature PRs to know: #13050 variants, #13087 infer variant sources from root, #13513 `mode = "absent"`, #13514 `permissions` key, #13515 empty template removes target, #13585 `dot_prefix`, #13583 relative symlinks, #13432 include lists, #13749 explicit plaintext tracking of credential-like files.
- This host: mise cache `docs/research/mintlify-cache/jdx/mise` predates the feature, so upstream PR titles above are the best changelog until re-fetched.

## Skill enhancement proposal (NOT applied; no repo files edited)
Carrier: `.claude/skills/research-sweep/SKILL.md` step 3 (Deep-read) already covers "how other projects solved a problem"; add a sub-step there, and mirror the recipe as a new source in `python/src/dotfiles_setup/research_fanout.py`.

Recommended: YES, add a `github-code` fan-out source. Rationale: it needs no key beyond `gh`, is mechanical, and `_SOURCE_NAMES` already models gh-api sources with a control arm (`_github_repo_control`). Spec:
- name `github-code`, details `("gh api REST search/code", "gh on PATH")`, OPT-IN like `last30days` (10 req/min bucket; keep out of `_DEFAULT_CANDIDATES`).
- one query per alternative (no OR); input is a list of legacy-syntax queries, a `--code-path`/`--filename` pair, not `--repo`.
- must: pre-read `rate_limit.resources.code_search.remaining`; map HTTP 403 -> `Status.error` (never empty); map 422 to a usage error naming the unsupported operator.
- control arm: a positive query (`"[tools]" filename:mise.toml`, must be > 0) plus a fresh invented token (must be 0); record both counts.
- verify-by-fetch step: fetch each hit via contents API and re-grep the literal token; report `hits`, `verified`, `false_positive` (here 326 / 306 / 19 + 2 fetch failures).

Text for SKILL.md (add after step 3's clone paragraph):

> **Config-pattern examples from GitHub code.** To see how real projects configure a tool, use REST code search (legacy
> syntax, NOT the web UI's): `gh api -X GET search/code -f q='"[dotfiles]" filename:mise.toml' -f per_page=100 --paginate --jq '.items[]|"\(.repository.full_name) \(.path)"'`.
> One query per alternative (no `OR`, parentheses or `**`; a 422 `ERROR_TYPE_QUERY_PARSING_FATAL` means unsupported syntax).
> Punctuation is stripped by the tokenizer, so verify every hit by fetching the file
> (`gh api -H 'Accept: application/vnd.github.raw' repos/<o>/<r>/contents/<path>`) and grepping the literal token.
> Control arms: a query that must hit (`"[tools]" filename:mise.toml`) and a freshly invented token that must return 0.
> The code-search bucket is 10 req/min: check `gh api rate_limit --jq .resources.code_search`; HTTP 403 is a rate limit, never "no results".
> In zsh never name a loop variable `path`. Record every query, endpoint, count and real rc in the report's query table.

Also worth adding to `research-doc-sources.md`? No; keep it in research-sweep only.

## GitHub repos touched
- [jdx/mise](https://github.com/jdx/mise) — issues/PRs/discussions on dotfiles (#13410, #13135, #13394, #13140 etc.)
- [david-driscoll/dotfiles](https://github.com/david-driscoll/dotfiles) — closest analogue (~/.config/mise + scripts)
- [Pandoks/.dotfiles](https://github.com/Pandoks/.dotfiles) — shorthand form, self-linked mise dir
- [iainsimmons/dotfiles](https://github.com/iainsimmons/dotfiles) — templates, symlink-each, host layers
- [h-wb/dotfiles](https://github.com/h-wb/dotfiles) — chezmoi removed; template/permissions/secrets
- [cnwangjie/dotfiles](https://github.com/cnwangjie/dotfiles) — chezmoi replacement, conf.d split
- [guitsaru/dotfiles](https://github.com/guitsaru/dotfiles) — hooks for private modes, worktree guard
- [jefftriplett/dotfiles](https://github.com/jefftriplett/dotfiles) — default_mode + empty entries
- [nrminor/.dotfiles](https://github.com/nrminor/.dotfiles) — repos as sources, exclude lists
- [xqm32/dotfiles](https://github.com/xqm32/dotfiles) — block entries
- [mattniedelman/dotfiles](https://github.com/mattniedelman/dotfiles) — track mode
- [erzz/dotfiles](https://github.com/erzz/dotfiles) — fnox/1Password templates
- [tdkn/dotfiles](https://github.com/tdkn/dotfiles) — self-link, conf.d/tasks link
- [Guria/mise-config-roots-repro](https://github.com/Guria/mise-config-roots-repro) — upstream bug repro
- [h-wb/dotfiles etc. remaining 290+](https://github.com/search?q=%22%5Bdotfiles%5D%22+filename%3Amise.toml&type=code) — census only (306 verified files)
