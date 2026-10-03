# Real-world code examples (fetched 2026-10-03)
## Conchylicultor/singularity plugins/infra/plugins/deps/plugins/mise/core/internal/mise.ts @6a617a083e213468ea7de8cb9aa9333df76ab5dd
6- * Runs `mise <args>` for the checkout at `root`, seeing ONLY that checkout's
7- * config.
8- *
9: * `MISE_CEILING_PATHS` is load-bearing. A worktree lives inside the main
10- * checkout (`<main>/.claude/worktrees/<wt>`), so mise also loads main's
11- * `mise.toml` as a parent config — and `mise lock` run in a worktree rewrites
12- * the PARENT's lock too, moving main's toolchain to whatever this worktree just
13- * installed. Verified on mise 2026.4.28: a child `mise lock` changed the
14: * parent's go from 1.24.13 to 1.27.1. The ceiling stops the walk at the
15- * worktree's own directory.
16- */
17-export async function mise(
18-  root: string,
19-  args: string[],
20-  timeoutMs: number,
--
22-  const argv = [miseBin(), ...args];
23-  const result = await spawnCaptured(argv, {
24-    cwd: root,
25:    env: { ...process.env, MISE_CEILING_PATHS: dirname(root) },
26-    timeoutMs,
27-  });
28-  if (result.exitCode !== 0) {
29-    throw new Error(
30-      `\`mise ${args.join(" ")}\` failed (exit ${result.exitCode}${result.timedOut ? ", timed out" : ""}):
31-` +

## asjer/rails-worktrees lib/rails/worktrees/post_create_runner.rb @985fc4c91a512da5320661a7f2768e62cd57b48c
180-        trust_root = target_git_root || canonical_target_dir
181-
182-        {
183:          'MISE_CEILING_PATHS' => File.dirname(trust_root),
184-          'MISE_TRUSTED_CONFIG_PATHS' => trust_root
185-        }
186-      end
187-
188-      def target_git_root
189-        stdout_str, status = capture_target_git_root

## laurigates/dotfiles tests/test-mise-tasks.sh @911ef2270ed500fb0ebc319acc98d5a818683789
43-#
44-# mise runs with `env -i`, HOME set to an empty directory, isolated config,
45-# state and cache dirs, the global config replaced by the tasks extracted from
46:# the rendered template, and MISE_CEILING_PATHS so no parent config leaks in.
47-# A task that silently ran in $HOME would find nothing there.
48-#
49-# A linter that is missing or cannot run SKIPs its fixture and repo checks
50-# loudly. `--require shellcheck,python3` turns those SKIPs into failures (the
51-# smoke Linters job does this). luacheck 1.2.0 cannot run on Lua 5.5
52-# (lunarmodules/luacheck#147); lint:lua prints the fix.
--
249-
250-# --- mise harness -------------------------------------------------------------
251-# run_mise <cwd> <state-dir> <data-dir> <path> <mise args...>: output + rc.
252:# Two ceilings. The parent of the git checkout holding <cwd>: mise reads that
253-# checkout's .mise.toml and nothing above it (a worktree sits inside the main
254-# checkout). $WORK: a task that runs in the empty $HOME does not pick up
255-# configs above it, such as the real ~/.config/mise/config.toml when $TMPDIR
256-# is under the real home.
257-run_mise() {
258-    local cwd="$1" state="$2" data="$3" path="$4" top
--
262-        ${LANG:+LANG="$LANG"} ${LC_ALL:+LC_ALL="$LC_ALL"} ${LC_CTYPE:+LC_CTYPE="$LC_CTYPE"} \
263-        MISE_GLOBAL_CONFIG_FILE="$WORK/global-tasks.toml" MISE_CONFIG_DIR="$WORK/mise/cfg" \
264-        MISE_STATE_DIR="$state" MISE_CACHE_DIR="$WORK/mise/cache" MISE_DATA_DIR="$data" \
265:        MISE_CEILING_PATHS="$(dirname "$top"):$WORK" MISE_TASK_RUN_AUTO_INSTALL=0 \
266-        "$MISE_BIN" "$@" </dev/null 2>&1)
267-}
268-# run_task <root> <task> [extra args]: run with the real tool installs.
269-run_task() {
270-    local root="$1" task="$2"
271-    shift 2

## liveblocks/liveblocks .envrc @ee1b0080157e7f244fe83ae499114e4ced8b6db9
1:# Inherit from a parent .envrc when this repo is checked out as a worktree
2:# group (see https://github.com/nvie/worktrees). No-op in a normal checkout.
3:source_up_if_exists
4-
5-layout node
6-
7-# Automatically put scripts/ in your $PATH, as long as you
8-# are inside this repo
9-PATH_add ./scripts/

## oss-review-toolkit/ort .miserc.toml f68175d78f629b64798fe2fec86d8f6eee833ec6 ceiling @
1:

## hydeik/dotfiles .miserc.toml 64a5bb91dfdc93f04e0accfc1e977408273ade38 ceiling @
1:

## srinitude/hermes-mastra .miserc.toml b82d68b982b789d1d42ec4ca3d8dcb18886a626b ceiling @
1:

## sunakan/isuren-mondai .miserc.toml be324f617f95d44a0af4000515ab57e60731c737 ceiling @
1:

## oss-review-toolkit/ort .miserc.toml @f68175d78f629b64798fe2fec86d8f6eee833ec6 (full)
```toml
# Stop search upward for further `mise.toml` files, see
# https://mise.jdx.dev/configuration.html#configuration-resolution-process
ceiling_paths = ["{{ config_root | dirname }}"]
```
## hydeik/dotfiles .miserc.toml @64a5bb91dfdc93f04e0accfc1e977408273ade38 (full)
```toml
# ~/.config/mise/miserc.toml

# Automatically activate the config environment baensed on the current platform.
auto_env = true

# Make files in .mise/conf.d and .config/mise/conf.d use environment suffixes
env_conf_d = true

# Stop config search at $HOME
ceiling_paths = ["{{ env.HOME }}"]
```
## srinitude/hermes-mastra .miserc.toml @b82d68b982b789d1d42ec4ca3d8dcb18886a626b (full)
```toml
ceiling_paths = ['{{env.HOME}}']
```
## sunakan/isuren-mondai .miserc.toml @be324f617f95d44a0af4000515ab57e60731c737 (full)
```toml
ceiling_paths = ["{{ config_root | dirname }}"]
```
