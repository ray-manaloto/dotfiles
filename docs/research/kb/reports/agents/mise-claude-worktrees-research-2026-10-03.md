# mise config inheritance in nested Claude Code worktrees — research (2026-10-03)

Versions: mise **2026.10.1** (host, `mise --version`), Claude Code **2.1.288** (`claude --version`).
Offline mise corpus: KB mirror `sources/mise` @ `794948606e02` (2026-09-09, CHANGELOG head 2026.9.4);
releases 2026.9.5 → 2026.10.1 fetched live (`raw/.../mise-releases-since-2026.9.4.md`).

## Answer (TL;DR)

`MISE_CEILING_PATHS` / the `ceiling_paths` setting **is** the sanctioned upstream mechanism — it is the
feature built for exactly this (#6041, `GIT_CEILING_DIRECTORIES` semantics), and mise maintainers point
nested-project users at it (discussions #6366, #6459). There is **no** "root = true"/stop-marker, no
`worktree.*` location setting in Claude Code, and the monorepo machinery only scopes *tasks*.

But the env var is the wrong *delivery* vehicle for us. `ceiling_paths` is an early-init setting that
can be set **in a committed `.miserc.toml`** (settings.toml:430-456 `rc = true`), which supports Tera
templates with `config_root` (docs/templates.md:532-560). This repo already tracks a `.miserc.toml`
(`auto_env = false`, from #1464). Recommended fix — one line, the exact pattern
oss-review-toolkit/ort ships:

```toml
# .miserc.toml
auto_env = false
# Stop upward config discovery at this checkout's parent. In the main checkout that is a no-op
# (measured: identical `mise config ls`); in <main>/.claude/worktrees/<name> it is
# <main>/.claude/worktrees, so the main checkout's mise.toml / mise.local.toml / conf.d stop leaking in.
ceiling_paths = ["{{ config_root | dirname }}"]
```

Because it is a FILE read by every mise process from its own cwd, it reaches every consumer with no env
plumbing — Claude sessions/subagents, codex lanes, hk git hooks, and the devcontainer
(`/workspaces/<clone>/.claude/worktrees/<n>` → ceiling `/workspaces/<clone>/.claude/worktrees`) —
and it needs no literal host path, so it sidesteps `settings.json` `env` taking literal values.

## Evidence — live probes (mise 2026.10.1, scratch fixture, both arms)

Full table: `docs/research/kb/raw/mise-claude-worktrees-2026-10-03/live-probes.md`. Fixture:
`main/{mise.toml,mise.local.toml,.config/mise/conf.d/shared.toml}` set `FROM_MAIN*`; the worktree
`main/.claude/worktrees/wt/{mise.toml,.config/mise/conf.d/shared.toml}` sets `FROM_WT*`.

| Arm | Setup | cwd | Result |
|---|---|---|---|
| A control | nothing | wt | main's 3 files listed — leak reproduced (`mise config ls`) |
| B fix | conditional `config_root` template in both `.miserc.toml` | wt | only wt files (`config ls`); cross-checked by `mise env`: only `FROM_WT*` |
| S fix (ORT form) | `ceiling_paths = ["{{ config_root \| dirname }}"]` in both | wt | only `FROM_WT*` |
| T/C no-regression | same | main | all `FROM_MAIN*` present; a `mise.toml` ABOVE main is dropped (T) vs present without miserc (U) |
| Real repo | `MISE_CEILING_PATHS=~/dev/github/ray-manaloto` (≡ ORT form in main) | main checkout | `mise config ls` **IDENTICAL** to without — no-op on this host |
| F | fix | wt/sub/deep | only `FROM_WT*` (works from subdirs) |
| G | fix, no `MISE_TRUSTED_CONFIG_PATHS` | wt | works — `.miserc.toml` needs no trust |
| E env route | `MISE_CEILING_PATHS=<main>/.claude/worktrees` | wt | only `FROM_WT*` (reproduces the coordinator's measurement) |
| R env route | same env | main | `FROM_MAIN*` intact — the static env value is harmless in main |
| **D hazard** | template only in MAIN, wt's copy old (no ceiling) | wt | **LEAK** — main's file renders with `config_root=<main>` |
| **O/P hazard** | fix in both, but `mise -C <wt>` invoked from main or `/` | main, `/` | **LEAK** — miserc is discovered from the *invocation* cwd (src/cli/mod.rs:868 `miserc::init()` runs before `cd` at :913; miserc.rs:60-65 `invocation_cwd`) |
| Q | env route + `mise -C` from main | main | only `FROM_WT*` — the env var covers `-C` |

Template pitfalls measured (miserc uses **Tera 2** regardless of `tera_v1`, src/tera.rs:1274-1281):
`cwd is containing(..)`, `cwd is starting_with("/")`, `cwd | as_str` + `is containing` all **fail to
render**; mise then falls back to the raw text (miserc.rs:146-151), which is invalid TOML → **hard
`mise::config::parse_error` for every mise command in the tree**. `"/.claude/worktrees/" in cwd` and
`cwd | split(...)` rendered but did not match. Only `config_root | dirname [| basename]` forms worked.
So: keep the template to the ORT one-liner, and gate it. `mise settings get ceiling_paths` printed `[]`
even with the working template — it is NOT a valid probe of miserc values (control arm failed).

## Source facts (file:line, KB mirror unless noted)

- Discovery walk stops at `MISE_CEILING_PATHS`: docs/configuration.md:76-77, :673-677.
- `ceiling_paths` setting: rc-capable, ceiling dir itself excluded, early-init only (setting it in
  `mise.toml` has no effect): settings.toml:430-456.
- miserc discovery: `.miserc.toml` + `.config/miserc.toml` in cwd and ancestors, then global, system
  (miserc.rs:228-271; docs/configuration/environments.md:84-86). Merge is per-key, **closest file wins
  and replaces the whole value** (miserc.rs:164-182, :204-216) — so the worktree's own tracked copy
  overrides the main checkout's.
- miserc discovery itself honors ONLY the raw `MISE_CEILING_PATHS` env (miserc.rs:273-284; PR #10165,
  released v2026.5.18) — a miserc-set ceiling does not hide parent miserc files (harmless here).
- Template context: `config_root` = dir of the miserc file, `cwd`, `env`, `xdg_*` (miserc.rs:110-151;
  docs/templates.md:532-560).
- `.miserc.local.toml` (gitignored per-checkout override, checked before `.miserc.toml`): PR #13440,
  merged 2026-09-21.
- `--no-config` / `MISE_NO_CONFIG` now skips miserc discovery: PR #13926, merged 2026-10-03 (not yet in
  a release as of 2026.10.1 — check the next one).
- Trust is shared across git worktrees: PR #10890 (v2026.7.x) — so trusting the main checkout already
  covers worktree configs; not a lever for inheritance.
- monorepo: `experimental_monorepo_root` deprecated (#11052); "don't load tasks from an enclosing
  monorepo root" (#11283) fixes **tasks only** — discussion #11276 (exactly the `<repo>/.worktrees/<n>`
  case) confirms tools/env still inherit. Not a fix for our leak.
- CHANGELOG/releases 2026.9.5–2026.10.1: no ceiling/worktree/discovery change (grep of all 8 release
  bodies; only #13882 `:task` completion mentions config roots).
- Claude Code: worktrees default to `<repo>/.claude/worktrees/<name>` (worktrees.md:21); relocating them
  needs a `WorktreeCreate` hook (worktrees.md:220, :271-292) — the only `worktree.*` settings are
  `baseRef`, `bgIsolation`, `sparsePaths`, `symlinkDirectories` (settings-reference.md:817-820,
  :4884-4983). `${CLAUDE_PROJECT_DIR}` stays at the main checkout after entering a worktree; hook input
  `cwd` follows (worktrees.md:44-51). `CLAUDE_ENV_FILE` from SessionStart/Setup/CwdChanged/FileChanged
  hooks can export env into later Bash calls (hooks.md:1222-1258, :2782).

## Delivery to each consumer

| Consumer | Mechanism with the recommended fix | Notes |
|---|---|---|
| (a) Claude sessions + subagents (incl. `isolation: worktree`) | the worktree's tracked `.miserc.toml` — every Bash tool call runs mise with cwd inside the worktree | nothing in settings.json; no literal path |
| (b) codex lanes | same file; lanes launch with cwd = worktree | `hook_guard` can't see codex commands, but this needs no guard |
| (c) hk git hooks | git runs hooks with cwd = worktree top; `HK_MISE=1` mise resolves from there | |
| (d) devcontainer `/workspaces/...` | template is relative (`config_root | dirname`) → `/workspaces/<clone>/.claude/worktrees` | image config lives in `MISE_SYSTEM_CONFIG_DIR=/usr/local/share/mise` (devcontainer.json:202, Dockerfile:75-77), not on the walk, so unaffected |
| `mise -C <wt>` from outside | NOT covered (arms O/P) | grep of tracked python/scripts/mise.toml/.claude/.codex/hk/.github for `mise -C`/`--cd` returned nothing (control: `git grep -c 'mise run' -- mise.toml` = 106). If one appears, cd first or set `MISE_CEILING_PATHS` for that call |

Belt-and-braces (optional) for the D/O gaps: a `SessionStart` + `CwdChanged` hook that appends
`export MISE_CEILING_PATHS="<git-common-dir parent>/.claude/worktrees"` to `$CLAUDE_ENV_FILE` (computed,
not literal). Not recommended as the primary: it reaches only Claude Bash calls, not codex lanes, hk run
from a terminal, or the devcontainer, and it is a new hook to maintain.

## Alternatives rejected

1. **`MISE_CEILING_PATHS` in `.claude/settings.json` `env`** — literal values only; the path differs per
   clone and host vs container (`/Users/...` vs `/workspaces/...`); never reaches codex lanes started
   outside Claude, hk from a terminal, or the devcontainer. (The repo's earlier gate runs used it ad hoc:
   docs/specs/s29b-global-mise-scripts-port.md:59; implement-s29b-machine-checks-2026-09-29.md:90,105.)
2. **Conditional `config_root | dirname | basename == "worktrees"` template** — works (arm B) but is more
   template surface for zero gain over the ORT one-liner, which is a measured no-op in the main checkout.
   Any `cwd`-based template — fails to render → hard parse error (measured).
3. **Relocate worktrees out of the repo via `WorktreeCreate` hook** (sibling `dotfiles.worktrees/`, the
   repo's own manual convention) — fixes inheritance structurally, but the hook replaces git logic
   entirely: `.worktreeinclude` stops being processed (worktrees.md:271), transcripts stay at the launch
   dir (:79), and there is a pile of open bugs: #89076 (hook path outside the repo always refused),
   #36205 (EnterWorktree ignores the hooks), #29716 (Desktop never calls them), #84989 (subagent +
   hook "cannot be confirmed as a separate isolation worktree"), #73363, #94265 (each switch outside
   `.claude/worktrees/` costs an approval), #99270/#99278. Feature request for a native location
   setting: #27282 (open).
4. **`MISE_CONFIG_DIR` / `MISE_GLOBAL_CONFIG_FILE`** — these move the *global* config; they do not stop
   the project walk.
5. **`ignored_config_paths`** (miserc, relative globs) — could list `../../../mise.toml` etc. from the
   worktree, but it is a deny-list that must enumerate every parent file name (mise.toml,
   mise.local.toml, conf.d/*, env-suffixed variants) and silently rots when a new one appears; the
   ceiling is an allow-boundary.
6. **`.miserc.local.toml`** (#13440) — per-checkout and gitignored, so it would have to be created in
   each worktree (e.g. via `.worktreeinclude`); strictly weaker than the tracked file.
7. **monorepo `config_roots` / `monorepo_root`** — tasks only (#11283, discussion #11276); deprecated key.
8. **direnv-style `source_up`** — the inverse problem (opt-in inheritance; liveblocks/.envrc). Not
   applicable to mise's walk.

## How other projects do it (GitHub code search)

- **oss-review-toolkit/ort** `.miserc.toml`: `ceiling_paths = ["{{ config_root | dirname }}"]` (and
  sunakan/isuren-mondai identical) — the recommended form.
- **Conchylicultor/singularity** `plugins/.../mise/core/internal/mise.ts:9-25`: sets
  `MISE_CEILING_PATHS: dirname(root)` on every spawned mise because a worktree lives at
  `<main>/.claude/worktrees/<wt>` — and records that a child `mise lock` **rewrote the parent's lock**
  (measured on mise 2026.4.28). That is a second, worse symptom of the same leak worth knowing.
- **asjer/rails-worktrees** `post_create_runner.rb:180-185`: `MISE_CEILING_PATHS = dirname(git root)`
  plus `MISE_TRUSTED_CONFIG_PATHS`.
- **laurigates/dotfiles** `tests/test-mise-tasks.sh:252-265`: ceiling at the parent of the checkout
  "(a worktree sits inside the main checkout)".
- Others set `ceiling_paths = ["{{ env.HOME }}"]` (hydeik/dotfiles, srinitude/hermes-mastra) — perf, not
  worktrees. Nobody found using a Claude Code setting for this; `"MISE_CEILING_PATHS" filename:settings.json` = 0.

## Control arms stated

- Issues/PRs (`gh api -X GET search/issues`): must-hit `repo:jdx/mise ceiling` = 38,
  `repo:anthropics/claude-code hooks` = 8915, `repo:direnv/direnv worktree` = 7; fresh per-run nonce = 0
  in all three repos.
- Discussions (GraphQL `search(type: DISCUSSION)`): must-hit `repo:jdx/mise ceiling` = 20, nonce = 0.
  anthropics/claude-code: must-hit `hooks` ALSO 0 → discussions there are "never asked", not absent.
- Code search: must-hit `"[tools]" filename:mise.toml` = 26368, fresh nonce = 0.
- Live mise probes: leak arm A before fix arm B; no-regression arms C/T/U; cross-route check
  (`config ls` vs `env`); hazards D/O/P/Q armed.
- Saved-search TOML validated against the #1502 JSON schema (OK) and a fail-arm (`bogus_key` →
  rejected "Additional properties are not allowed").

## Saved, re-runnable search

`docs/research/kb/searches/mise-claude-worktrees.toml` (copy:
`docs/research/kb/raw/mise-claude-worktrees-2026-10-03/saved-search.toml`) — #1502 SavedSearchFile
schema: 29 `[[watch]]` (16 issues, 5 discussions, 8 code) with `control_hit`/`control_absent "{nonce}"`
and 29 `[[result]]` baselines. Re-run: `mise run research-saved-search -- rerun <file>` once #1502
lands; the header carries the exact `gh api` commands to run it by hand today. Note: the #1502 branch
stores these under `docs/research/saved-searches/`; this file is at the coordinator-specified
`docs/research/kb/searches/` (same as the lock-format lane's) — reconcile when #1502 lands.

## Open questions

1. Old-base worktrees (arm D): a worktree whose branch predates the `.miserc.toml` change still leaks
   until rebased. Acceptable, since Claude Code cuts worktrees from origin/default (worktrees.md:117),
   but existing worktrees (`fix-1606`, `agent-*`, `codegen-default-group`) need a rebase or the env var.
2. Does `/workspaces` (container) hold any `mise.toml` that something relies on? Not probed (no raw
   `docker exec`); the ORT form would drop it. Probe in-container with `mise config ls` before/after.
3. `mise -C` callers — none in tracked code today; should a lint/verify contract pin the
   `.miserc.toml` line (and a test asserting `mise config ls` from a fixture worktree excludes the
   parent) so a "tidy-up" cannot remove it silently? Recommended, per probes-need-a-control-arm rule 9.
4. Should the singularity finding (child `mise lock` rewriting the parent lockfile) be re-measured here?
   `mise run lock` from a worktree today could touch the main checkout's `mise.lock`.
5. Claude Code: no native setting to place worktrees elsewhere (#27282 open); revisit if it ships.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — source (miserc.rs, tera.rs, cli/mod.rs, settings.toml), docs, CHANGELOG, releases 2026.9.5–2026.10.1, PRs #6041 #8283 #10165 #10890 #11283 #13440 #13926, discussions #5743 #6366 #6459 #8281 #11276
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues #27282 #36205 #29716 #46222 #73363 #83953 #84989 #89076 #94265 #99270 #99278 #16600 #12962; discussions probe (disabled)
- [direnv/direnv](https://github.com/direnv/direnv) — issue search for worktree handling
- [oss-review-toolkit/ort](https://github.com/oss-review-toolkit/ort) — `.miserc.toml` ceiling pattern
- [sunakan/isuren-mondai](https://github.com/sunakan/isuren-mondai) — same pattern
- [hydeik/dotfiles](https://github.com/hydeik/dotfiles) — `ceiling_paths = [env.HOME]` miserc
- [srinitude/hermes-mastra](https://github.com/srinitude/hermes-mastra) — same, `$HOME`
- [Conchylicultor/singularity](https://github.com/Conchylicultor/singularity) — env ceiling for `.claude/worktrees`; parent-lock rewrite finding
- [asjer/rails-worktrees](https://github.com/asjer/rails-worktrees) — env ceiling in worktree bootstrap
- [laurigates/dotfiles](https://github.com/laurigates/dotfiles) — env ceiling in test harness
- [liveblocks/liveblocks](https://github.com/liveblocks/liveblocks) — direnv `source_up_if_exists` worktree pattern
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.miserc.toml`, devcontainer config, prior ad-hoc `MISE_CEILING_PATHS` uses, #1502 saved-search schema
