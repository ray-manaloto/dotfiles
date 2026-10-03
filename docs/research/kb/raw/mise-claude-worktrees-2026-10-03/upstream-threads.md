# Upstream thread bodies (fetched 2026-10-03)
## jdx/mise PR #13440 feat(config): add .miserc.local.toml overrides
merged_at=2026-09-21T03:13:45Z state=closed
<!-- entire-trail-link-start -->
https://entire.io/gh/jdx/mise/trails/76
<!-- entire-trail-link-end -->

Developers can select a mise environment for one checkout without editing the project's shared `.miserc.toml` or repeating an environment flag:

```toml
# .miserc.local.toml
env = ["native"]
```

Ordinary `mise install` and `mise run dev` commands then load `mise.native.toml`. Add `.miserc.local.toml` to your global Git ignore file (`core.excludesFile`) to keep this preference untracked across repositories, and create it separately in each worktree that needs it.

Discovery checks `.miserc.local.toml` before `.miserc.toml` and `.config/miserc.toml` at each directory level. Closer directories retain precedence over parents. The local file uses the existing settings/template loader: explicit fields override shared values, omitted fields remain inherited, and `env = []` clears a shared selection. CLI flags and `MISE_ENV` still take precedence.

Validation covers shared/local precedence, inherited settings, nested directories, environment/CLI overrides, empty selections, templates, standalone local files, discovery ceilings and malformed TOML, alongside the existing miserc tests.

*AI-assisted — Tool: Codex; model: OpenAI/GPT-6; version: unavailable.*

<!-- CURSOR_SUMMARY -->
---

> [!NOTE]
> **Low Risk**
> Additive early-config discovery with existing merge semantics; behavior change is limited to optional local files and is covered by new e2e tests.
> 
> **Overview**
> Adds **`.miserc.local.toml`** so developers can pick a mise config environment per checkout (e.g. `env = ["native"]`) without changing committed `.miserc.toml` or passing `-E` every time.
> 
> Early miserc discovery now checks **`.miserc.local.toml` before `.miserc.toml`** at each directory on the walk t

## jdx/mise PR #13926 fix(config): skip miserc discovery with --no-config
merged_at=2026-10-03T15:37:37Z state=closed
## Problem

A malformed `.miserc.toml` anywhere in the discovery chain fails even config-free invocations: `run_inner` calls `miserc::init()?` unconditionally (`src/cli/mod.rs`) before no-config is honored anywhere, and TOML errors propagate via `?`. So `mise --no-config version` run from a directory with a broken repo-level (or global/system) miserc exits non-zero instead of ignoring config.

## Fix

Guard the four miserc entry points on the pre-existing `Settings::no_config()` (`MISE_NO_CONFIG` env or pre-`--` argv `--no-config`):

- `load_miserc_settings()` → `Ok(default)`
- `load_global_miserc_settings()` → default
- `get()` → default (folded into the existing `is_package_query()` early return, mirroring that precedent)
- `get_global_ignored_config_paths()` → `None`

No new API; `no_config()` already exists. No-config now means no early-config.

## Semantic edge (call-out for reviewers)

- `get_global_ignored_config_paths() → None` disables ignored-paths filtering (consumed via `env.rs`) under no-config. Consistent with "no config", but changes `prune`-family verdicts for no-config invocations.
- `no_config()` argv detection requires `ARGS` populated — true at the `run_inner` call site (`ARGS` is written just above the `miserc::init()?` call), so both `MISE_NO_CONFIG=1` and `--no-config` forms work.

## Test plan

- New `e2e/config/test_no_config_skips_miserc`: malformed project + global + system miserc; `MISE_NO_CONFIG=1` and `--no-config` both succeed on `version`/`exec` from root and nested cwd; control without the flag still fails with `Invalid TOML in config file`. Passes.
- Existing `e2e/config/test_miserc`, `test_miserc_local`, `test_no_config` all still pass.
- `cargo clippy --all-features` clean, `cargo fmt --all -- --check` clean, `shfmt`/`shellcheck` clea

## jdx/mise PR #6041 feat(config): Add a ceiling to how mise searchs for config & tasks
merged_at=2025-10-08T17:37:21Z state=closed
**Problem**: mise recurses upwards from cwd looking for and loading config and tasks files. When mise accesses a directory that is slow to load it has a noticable impact on performance of mise activate In my work environment this is due to use of autofs/automount on /home - meaning when I use mise under /home/username there is a slowdown as mise looks for config file such as /home/.mise.toml

**Solution**: Implement something similar to git's GIT_CEILING_DIRECTORIES, a list of directories at which mise will stop recursing up.

Users control this by setting `MISE_CEILING_PATHS` environment variable. In my case, I'd set this to include /home, meaning /home/username is the last directory searched.

This can be a set to a list of directories which are separated by the platform's conventions for PATH meaning `:` for Linux/macS and `;` for Windows. But basically I'm using `std::env::split_paths`, so that's the definition.

All the interesting work here seem to be in `src/config/mod.rs`, there are three places that call `file::all_dirs()` to get the list of ancestor folders of cwd

- `load_config_paths`
- `load_local_tasks`
- `config_file_from_dir`

Updated the signature of all_dirs to `all_dirs<P: AsRef<Path>>(start_dir: P, ceiling_dirs: &HashSet<PathBuf>) -> Result<Vec<PathBuf>>`

- Passing in `start_dir` helps with testability (unit tests added)
- The second argument is the set of "ceiling" directories that are used to stop the iteration
- Also rewrote to use `ancestors()`

Provided a wrapper `all_dirs` in `src/config/mod.rs` that passes in the current dir, and the value of `MISE_CEILING_PATHS` as a `HashSet`

Added e2e tests to check that search for config files and file tasks both stop at the ceiling. 

Added (brief) documentation to `configuration

## jdx/mise PR #10165 fix(config): honor ceiling paths during miserc discovery
merged_at=2026-05-31T15:42:29Z state=closed
## Summary
- stop early .miserc.toml discovery at raw MISE_CEILING_PATHS entries
- avoid using the lazy MISE_CEILING_PATHS fallback during .miserc discovery to prevent recursion
- add a regression case where a parent .miserc.toml above the ceiling would otherwise inject MISE_ENV

## Related
- Project item: https://github.com/users/risu729/projects/3/views/1?pane=issue&itemId=183814890
- Discussion: https://github.com/jdx/mise/discussions/5743

## Tests
- cargo test --all-features config::miserc::tests -- --nocapture
- cargo fmt --all -- --check
- git diff --check
- CARGO_TARGET_DIR=/home/risu/.cache/cargo-target/mise-409845c58888dcc6 mise run test:e2e e2e/config/test_miserc

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

* **New Features**
  * The `MISE_CEILING_PATHS` environment variable now properly limits how far configuration file discovery traverses up the directory hierarchy.

* **Tests**
  * Added end-to-end tests verifying ceiling path constraints on configuration file discovery behavior.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->

## jdx/mise PR #10890 feat(trust): share config trust across git worktrees
merged_at=2026-07-09T19:05:11Z state=closed
## What

A config file inside a linked git worktree is now trusted when the equivalent path in the repository's main checkout has been trusted. Trusting a repo once covers all of its worktrees — no more re-prompting in every `git worktree add` checkout.

## Why

Trust records are keyed by canonicalized absolute path, so every new worktree was a brand-new path that prompted again. This is especially painful for workflows that spin up many short-lived worktrees (e.g. AI-agent worktrees under `.claude/worktrees/`).

## How

- `src/git.rs`: new `main_checkout_equivalent()` maps a path inside a linked worktree to the same relative path in the main checkout. Detection is filesystem-only — a linked worktree root has a `.git` *file* containing `gitdir: <main>/.git/worktrees/<name>`, and `commondir` resolves the shared git dir — so no git subprocess; results are cached per worktree root. Returns `None` for main checkouts, non-repos, and bare-repo worktrees.
- `src/config/config_file/mod.rs`: `is_trusted()` consults the main-checkout equivalent after direct/monorepo checks fail.
- `src/cli/trust.rs`: `mise untrust` inside a worktree warns that the main checkout still trusts the config (mirrors the existing `trusted_config_paths` warning) and suggests untrusting there or using `--ignore`.

## Design notes for review

- **Read-side only**: `mise trust` inside a worktree trusts just that worktree; sharing flows only from main checkout → worktrees.
- **Paranoid mode is excluded**: its trust is tied to per-file content hashes, and a worktree can have a branch checked out with different config contents.
- An explicit `--ignore` on a worktree config still wins over the shared trust, since the ignore check runs first.

## Tests

- Unit: `git::tests::worktree_main_checkout_equivalent` (ne

## How to isolate nested mise project https://github.com/jdx/mise/discussions/6366 (2025-09-22T07:55:18Z)
Hi, I have a root project with a `mise.toml`. Inside I have a git submodule which also has a `mise.toml` that requires its own version of the dependencies and scripts.

When I run `mise install` the root mise scripts are also executed. Is there anyway I can isolate the sub project so when I run the commands only those in the submodule are executed?
ANSWER: none
COMMENTS:
- @my1e5: Does https://mise.jdx.dev/configuration/settings.html#ceiling_paths work?

## Options to ignore parent mise.toml and global settings for greater purity https://github.com/jdx/mise/discussions/6459 (2025-09-28T11:34:16Z)
I'd like to have a mise.toml which defines an environment in a fairly pure manner, to use a word from the functional and nix ecosystem - the tools and env and tasks are only those defined in the local mise folder, and everything else is ignored. This helps me to ensure that anyone who pulls down that project won't need anything implicit from outside of it.

I've been having trouble figuring out exactly how to do this. I saw this answer https://github.com/jdx/mise/discussions/4202#discussioncomment-11943815 about using a global config file to avoid dealing with a parent folder?

I want to use a parent folder mise.toml for various small projects which are personal to me without having to have a separate folder for which is not below that parent mise.toml for pure projects.
ANSWER: none
COMMENTS:
- @bheesham: Yeah, this affects `mise oci build`. It pulls stuff in from my user's config, which isn't really what I want (no reason to have stuff like `tokei` in my images).
- @risu729: I remember there was a bug report for this, so it might not work as intended, but [`MISE_CEILING_PATHS`](https://mise.jdx.dev/configuration/settings.html#ceiling_paths) should work for this purpose.


## Suggestion: Add a ceiling to mise config/task search (similar to GIT_CEILING_DIRECTORIES) https://github.com/jdx/mise/discussions/5743 (2025-07-22T10:40:13Z)
**Problem**: `mise` recurses upwards from cwd looking for and loading config and tasks files. When mise accesses a directory that is slow to load it has a noticable impact on performance of `mise activate` In my work environment this is due to use of autofs/automount on `/home` - meaning when I use mise under /home/username there is a slowdown as mise looks for config file such as `/home/.mise.toml`

**Idea**: Implement something similar to git's `GIT_CEILING_DIRECTORIES`, a list of directories at which mise will stop recursing up. In my case, I'd set this to include `/home`, meaning `/home/username` is the last directory searched.

After a checking in discord, I have a prototype for this, which works for me, and am happy to create a PR. So I'm looking for feedback on implementation, and naming.

**Implementation**
All the interesting work here seem to be in `src/config/mod.rs`, there are three places that call `file::all_dirs()` to get the list of ancestor folders of cwd
* `load_config_paths`
* `load_local_tasks` 
* `config_file_from_dir`

My prototype updates the signature of `all_dirs` to 
`all_dirs<P: AsRef<Path>>(cwd: P, ceiling_dirs: &HashSet<PathBuf>) -> Result<
ANSWER: none
COMMENTS:
- @jdx: this all sounds good, and yeah it probably has to be in an env var similar to `MISE_ENV` which is a prerequisite for loading the settings itself so it can't be specified in settings. As far as which one I think they all seem fine. I know we have `MISE_TRUSTED_CONFIG_PATHS` so there at least is some prior art around `_PATHS`
- @probberechts: I have the same setup as @richardthe3rd, and setting the `MISE_CEILING_PATHS` environment variable used to work well. However, this seems to have regressed after support for `.miserc.toml` was added.

`MISE_CEILING_PATHS` still correctly limits directory traversal for `mise.toml` and other project config files, but `.miserc.toml` discovery seems to be using a different traversal path that does not respect the ceiling.

In my case, this makes `mise hook-env` take up to ~30 seconds, which make
- @risu729: Opened draft PR https://github.com/jdx/mise/pull/10165 to restore `MISE_CEILING_PATHS` for early `.miserc.toml` discovery so parent miserc files above the ceiling cannot affect config loading.

*This comment was generated by an AI coding assistant.*
- @JamBalaya56562: Closing the loop on both halves of this thread.

The feature is yours — **#6041**, merged 2025-10-08, first released in **v2025.10.7**. `MISE_CEILING_PATHS`, an environment variable, exactly as @jdx suggested here.

@probberechts — the `.miserc.toml` regression you hit is fixed. **#10165** (@risu729), merged 2026-05-31, first released in **v2026.5.18**: miserc discovery honours the ceiling now, so a parent `.miserc.toml` above it can no longer pull config loading back up the tree. If `mise hook-

## monorepo_root in git worktree https://github.com/jdx/mise/discussions/11276 (2026-07-24T20:07:55Z)
When working with git worktrees, I often use `<repo>/.worktrees/<worktree name>` for pathing. However, I'm running into a scenario where mise uses the <repo>/mise.toml instead of <repo>/.worktrees/<worktree>/mise.toml for tasks and {{config_root}}. 

Expected behvaior: if a mise.toml declares itself `monorepo_root = true` that it is considered the mono repo root, even if there is a monorepo root above it. As the config_roots are explicitly defined, I would not expect this to conflict unless a config_root is set to a path that also declares itself monorepo_root.

If this is generally unexpected, I am happy to spin up a PR to contribute a fix.  However, if there is a good reason for this behavior, I'll work around it.
ANSWER: none
COMMENTS:
- @yhay81: Your expectation is reasonable, and the current behavior comes from how mise selects the active monorepo root—not from Git worktree metadata.

At present, [`find_monorepo_config`](https://github.com/jdx/mise/blob/main/src/config/mod.rs#L1112-L1116) effectively does:

```rust
config_files.values().find(|cf| cf.monorepo_root() == Some(true))
```

So when both of these are ancestors of the working directory:

```
<repo>/mise.toml                         # monorepo_root = true
<repo>/.wo
- @jdx: I couldn't reproduce this on 2026.7.0 or on `main` — **mise already selects the nearest `monorepo_root = true` config**, so the behavior you're asking for should be what you get.

I built the layout you described:

```
<repo>/mise.toml                                  # monorepo_root = true, config_roots = ["projects/*"]
<repo>/projects/alpha/mise.toml
<repo>/.worktrees/wt/mise.toml                     # monorepo_root = true, config_roots = ["projects/*"]
<repo>/.worktrees/wt/projects/alpha/mise
- @jdx: Update: #11283 now fixes the leak I described above, rather than documenting it.

Tasks from an **enclosing** monorepo root are no longer loaded. They're a different monorepo's task set, not a parent namespace of the selected root, so from inside `<repo>/.worktrees/<name>` you no longer see the main checkout's `build` sitting next to the worktree's `//:build`, and a task that only exists on the main checkout's branch no longer runs with `config_root = <repo>`.

Scope is limited to that case: any

## `mise.toml` in the directory of MISE_CEILING_PATHS is ignored https://github.com/jdx/mise/discussions/8281 (2026-02-21T16:30:14Z)
The documentation does not say
`mise.toml` at the directory of `MISE_CEILING_PATHS` is ignored.

For example, if `MISE_CEILING_PATHS` is "/foo",
then `/foo/mise.toml` is ignored, but `/foo/bar/mise.toml` is recognized.

I thought that `MISE_CEILING_PATHS` includes the mise.toml in its dir

I read debug log and unittests of `all_dir()` in <https://github.com/jdx/mise/blob/main/src/file.rs>,
and then understand the meaning of `MISE_CEILING_PATHS` 
that `mise.toml` inside  `MISE_CEILING_PATHS`  is ignored.

The current doc for `MISE_CEILING_PATHS` is a bit confusing,
OR the current behavior is not the expected bahavior.

It seems weird to set `MISE_CEILING_PATHS` to the graphparent of `mise.toml`, instead of parent of `mise.toml`, in order to use `mise.toml`.

But changing this will affect the compability. I suggest to update the documentation.

ANSWER: none
COMMENTS:
- @Marukome0743: The observed behavior is intentional, and the documentation was clarified by [PR #8283](https://github.com/jdx/mise/pull/8283), included with mise [v2026.2.18](https://github.com/jdx/mise/releases/tag/v2026.2.18).

`MISE_CEILING_PATHS` identifies directories at which upward configuration discovery must stop. The ceiling directory itself is excluded, along with its parents. This follows the semantics of Git’s `GIT_CEILING_DIRECTORIES`.

For example:

```sh
export MISE_CEILING_PATHS=/foo
`

## anthropics/claude-code #46222 [closed] Duplicate .claude/rules loading in worktrees nested inside .claude/
https://github.com/anthropics/claude-code/issues/46222 created=2026-04-10T13:00:56Z
## Summary

When using worktrees created inside `.claude/worktrees/`, rules from `.claude/rules/` are loaded twice — once from the worktree's own copy and once from the parent repo's `.claude/rules/` (discovered via ancestor directory traversal).

## Steps to reproduce

1. Have a project with `.claude/rules/` containing rule files
2. Enter a worktree (created at `.claude/worktrees/<name>/`)
3. Observe that rules are loaded twice:

```
Loaded ../../rules/pagination.md
Loaded ../../rules/security.md
Loaded ../../rules/viewsets.md
Loaded .claude/rules/pagination.md
Loaded .claude/rules/security.md
Loaded .claude/rules/viewsets.md
```

## Expected behavior

Each rule file should be loaded only once. When operating inside a worktree, the rule discovery should deduplicate rules that resolve to the same file content/origin, or skip ancestor `.claude/rules/` directories that belong to the parent repo.

## Actual behavior

Rules are loaded twice because:
- The worktree is physically located at `<repo>/.claude/worktrees/<name>/`
- The worktree has its own `.claude/rules/` (checked into git)
- Walking up the filesystem from the worktree also finds `<repo>/.claude/rules/`
- Both are loaded, re

## anthropics/claude-code #27282 [open] [Feature Request] Configurable worktree directory location with sibling directory support
https://github.com/anthropics/claude-code/issues/27282 created=2026-02-21T00:21:32Z
**Bug Description**
Please provide a way to configure where worktrees go, specifically a sibling directory. I asked Claude what is the recommended location for worktrees, and it said: "The widely recommended convention is to put worktrees in a sibling directory to the main repository, not inside it." Using a subdirectory like you do now causes problems.

**Environment Info**
- Platform: darwin
- Terminal: iTerm.app
- Version: 2.1.50
- Feedback ID: f0086445-61db-4342-b4ea-df9fff886599

**Errors**
```json
[]
```


## anthropics/claude-code #83953 [open] Project-scope hooks do not reach git worktrees: branch-local when tracked, absent entirely when `.claude/` is gitignored
https://github.com/anthropics/claude-code/issues/83953 created=2026-08-04T22:03:12Z
## Summary

Project-scope hooks (`.claude/settings.json`) are the one piece of project configuration that does not reach a git worktree. The docs section "What worktrees share with the main checkout" lists three things that do carry over from the main checkout: the `.git` directory, project-scope plugins, and saved permission approvals, and it states that all three apply whether the worktree was made with `--worktree`, with `git worktree add`, or by the desktop app. Hooks and project settings are not on that list, and in practice they arrive by only one route: git checking out a tracked file.

That route fails in two independent ways:

1. **Branch-local when tracked.** A hook committed on one branch does not exist in a worktree checked out on a different branch until that branch merges the commit. A worktree created from `origin/main` before the hook landed simply does not have it.
2. **Never delivered when `.claude/` is gitignored.** Many repos gitignore `.claude/`, and the worktree docs themselves recommend gitignoring `.claude/worktrees/`. Git cannot deliver a file it does not track, so a gitignored project `settings.json` reaches no worktree at all. `.worktreeinclude` is

## anthropics/claude-code #16600 [open] [FEATURE] Claude Code memory traversal should respect git worktree boundaries
https://github.com/anthropics/claude-code/issues/16600 created=2026-01-07T11:24:41Z
### Preflight Checklist

- [x] I have searched [existing requests](https://github.com/anthropics/claude-code/issues?q=is%3Aissue%20label%3Aenhancement) and this feature hasn't been requested yet
- [x] This is a single feature request (not multiple features)

### Problem Statement

When using git worktrees, Claude Code's CLAUDE.md traversal loads memory files from both the current worktree AND the parent repository directory, causing a security warning:

> This project's CLAUDE.md imports files outside the current working directory. Never allow this for third-party repositories.

**The problem:**
- Git worktrees are a common development pattern for working on multiple branches simultaneously
- Each worktree represents a different branch state with potentially different CLAUDE.md instructions
- Claude Code traverses up from CWD to filesystem root `/`, loading ALL CLAUDE.md files it encounters
- This causes the parent repo's CLAUDE.md to be loaded alongside the worktree's CLAUDE.md
- When the parent CLAUDE.md imports files (e.g., `@./AGENTS.md`), those paths resolve outside the worktree CWD
- This triggers a misleading security warning for the developer's own repository

**Why this ma

## anthropics/claude-code #94265 [open] Worktrees outside .claude/worktrees/ cost one approval prompt per switch
https://github.com/anthropics/claude-code/issues/94265 created=2026-09-14T12:01:13Z
# Worktrees outside `.claude/worktrees/` cost one approval prompt per switch

## Summary

Two behaviours compound into an approval prompt on **every** worktree switch, for repos that keep
their worktrees somewhere other than `.claude/worktrees/`:

1. **Worktree→worktree switching is rejected** unless the target is under `.claude/worktrees/`, so
   moving between trees requires `ExitWorktree` back to the launch directory and re-entering.
2. **An approved path is not remembered.** Re-entering a path already approved in the same session
   prompts again.

Either alone is liveable. Together they mean an agent alternating between two tickets pays an
approval on every hop, forever.

I understand the first-entry prompt is deliberate, and that neither an `EnterWorktree` permission
rule nor "don't ask again" suppresses it. This report is about the repeat.

## Version

- Claude Code **2.1.251**
- macOS 15.6 (Apple silicon)
- Worktrees at `<repo>/.worktrees/<ticket-id>`, created by a repo-owned wrapper around
  `git worktree add` (not `claude --worktree`), and registered in `git worktree list`.

## Repro 1 — direct switching is rejected outside `.claude/worktrees/`

With the session already i

## anthropics/claude-code #89076 [open] [BUG] WorktreeCreate hook returning a path outside the repository is always refused: "git could not be run to resolve it"
https://github.com/anthropics/claude-code/issues/89076 created=2026-08-23T21:46:23Z
### What's Wrong?

A `WorktreeCreate` hook that creates a valid git worktree **outside the repository** and prints its path is always refused by Claude Code's git-identity verification:

```
Refusing to use /Users/me/workspace/worktrees/my-repo/<name> as an isolation worktree: git could not be run to resolve it, so its git identity could not be verified. Isolation is refused rather than assumed — recreate the worktree (or remove the corrupt .git entry) and retry.
```

The worktree itself is healthy: it is registered in `git worktree list`, `git -C <path> status` works, the path contains no symlinks and no `.`/`..` segments. The hook's stdout is clean (only the path on the last line; git output redirected to stderr).

**Control test:** the *identical* hook returning a path inside the repository (`$repo_root/.claude/worktrees/$name`) is accepted, and the session runs in it. So the hook mechanics and output parsing are fine — the external location is the trigger.

The refusal reproduces identically for all three creation paths: `claude --worktree`, the `EnterWorktree` tool, and `Agent(isolation: "worktree")` subagents, and in completely fresh sessions.

### What Should Happen?

Per ht

## anthropics/claude-code #12962 [open] [FEATURE] Settings.json parent directory traversal for monorepos
https://github.com/anthropics/claude-code/issues/12962 created=2025-12-03T10:06:22Z
## Problem

When working in a monorepo subdirectory (e.g., `/repo/packages/app/`), Claude Code only looks for `.claude/settings.json` in the current working directory. It does not traverse parent directories to find shared settings at the repo root.

This means you either need to:
- Duplicate settings in every subdirectory
- Always launch Claude Code from the repo root
- Use global user settings (`~/.claude/settings.json`) which apply to all projects

## Proposed Solution

Claude Code should traverse parent directories (up to the git root or filesystem root) looking for `.claude/settings.json` files, similar to how many tools handle config files (e.g., `.gitignore`, `tsconfig.json`, `.eslintrc`).

Settings could be merged with deeper directories taking precedence, or the first found settings file could be used.

## Use Case

In a monorepo with multiple packages/services, you want shared settings (allowed tools, MCP servers, permissions) defined once at the repo root, while still being able to work from within subdirectories.

## Related Issues

- #2365 - Better Monorepo Support (MCP and commands)
- #374 - MCP repo scope
- #705 - Nested CLAUDE.md context
- #3146 - Configure addition

