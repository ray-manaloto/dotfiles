# Premise report — `docs/specs/session-handoff-automation.md` rev 5 (ec916579)

> Persisted verbatim at receipt by the handoff-automation lane (4daaf7e1), 2026-10-03. Producer: premise-verifier subagent (read-only).

PREMISE REPORT: rev 5 of `docs/specs/session-handoff-automation.md` at ec916579 (worktree handoff-automation-research). This was a read-only lane, so nothing was persisted; the caller persists this report.

ROWS: 4 premise rows and 22 anchors checked. Tally: 20 CONFIRMED (2 of them provenance-corrected), 4 REFUTED, 2 UNVERIFIABLE, 0 ASSUMED.

**Premise rows**

- **P20 (retired): CONFIRMED (provenance corrected).** The evidence cited is "CONFIRMED by the proposals review", which is a report rather than code. Re-read:
  - `pr.py:133-143` is `BASE_INPUT_PATTERNS`.
  - The Dockerfile COPY sources at `:127,133,139,392,393,669,672` are all in that set.
  - `build-publish.yml:419-424` is a comment block describing HIT → retag `:pr-NNN`.
  - `p2996_hash.py:480-526` (the cited 475-523 is slightly off) shows the dev hash = base + p2996 + Dockerfile + dev target + runtime toml/lock.
- **P22: CONFIRMED (provenance corrected), with one caveat.** The name, volume and port come from the resolved path: `devcontainer_names.py:174-175` (hash), `:209-211` (port), `:226-237` (names); `mise.toml:385` evaluates the resolver; `:400` runs `devcontainer up --workspace-folder .`. The "#1481 probe" is not a code citation.
  - **Caveat:** `ssh_port` lets an override win (`devcontainer_names.py:195-208`). The `up` task reads it from the ambient env: `mise.toml:368` `DEVCONTAINER_SSH_PORT = "{{ env.DEVCONTAINER_SSH_PORT | default(value='') }}"`. See MISSING-1.
- **P23: REFUTED.** CLI 0.89.0 `devContainersSpecCLI.js:488`: `let B=r||(await dg(...)).idLabels`. Supplied `--id-label`s replace the inferred `devcontainer.local_folder=` set. `devcontainer.json:109-118` adds no label of its own.
  - In-repo statement: `sync.py:10-12`: "`--id-label` REPLACES the CLI's inferred `devcontainer.local_folder` label, so that one no longer identifies anything post-#677" (also `devcontainer_names.py:150-152`).
  - Our labels hold the hash only (`dotfiles.workspace=<hash>`, `:245-247`), and a hash cannot be turned back into a path.
  - So the "classify by local-folder label" route does not exist. The "name-hash re-derivation alone" fallback needs candidate paths from somewhere. A real second route is the bind-mount source in `docker inspect .Mounts`, since `workspaceMount source=${localWorkspaceFolder}` is set at `devcontainer.json:130`.
  - The `mise.toml:1289-1290` comment ("label that the devcontainer CLI applies to every container") is stale and pre-dates #677.
- **P24: REFUTED.**
  - (a) Not exactly one stem: prune ends with a host-wide `docker builder prune -f` (`mise.toml:1279`), which evicts every clone's build cache, including main's. Calling it once per stem repeats that each time.
  - (b) It cannot be called per stem: it is hard-wired to cwd. `_stem` comes from `devcontainer name legacy-volume` (`:1190`), which resolves through `resolve_names()` → `Path.cwd()` (`devcontainer_names.py:292`). The legacy-volume grep uses `basename "$PWD"` (`:1256`). It takes no stem or path argument, and `uv run --project python` needs a checkout at cwd. A vanished-folder stem therefore cannot be pruned through this path.
  - Confirmed part: all architectures are covered (`teardown --all-arches`, `:1209`).

**Anchors**

- **CONFIRMED:**
  - `pr.py:283-290` (`needs_full_sync` = surface and not base).
  - `pr.py:596-628` (`_ship_preflight`).
  - `pr.py:603-607` ("the gates validate exactly what ships").
  - `pr.py:612-627` (the `_RC_LINKED_WORKTREE` refusal).
  - `pr.py:1059` (`sync_main(workspace, SyncOptions(full=surface))`).
  - `devcontainer.json:245-246` (onCreate and postCreate run scripts from the bind-mounted `/workspaces/<basename>`).
  - `ci.yml:309-317` (the `decide` step drops `.md` with jq).
  - `doctor.py:1810` (`CHECKS` tuple; `check_devcontainers_running` at `:1771` is the existing precedent and is silent in linked worktrees, `:1794`).
  - `do-not.md` #3.
  - `pr-workflow/SKILL.md:125` (the row exists and says "ship from the main checkout").
  - Side-fix safety: none of `.devcontainer/scripts/*` or `scripts/devcontainer-smoke.sh` reads a `.md` file. The control arm is that the same grep hits comments in `on-create.sh`.
- **REFUTED: §3j step 6, §3k and L8, "stop the clone's container via `mise run down` (devcontainer CLI)", "the clone's stopped container survives".** `down` is an alias of `stop` (`mise.toml:1285`), whose body is `docker rm -f ${container_ids}` (`:1303`). It removes the container rather than stopping it, and it is raw docker, not the devcontainer CLI.
  - This is load-bearing for arm (ii). The `sync` matrix reuses a stopped container: "stopped → up (reuse — CLI starts, never recreates)" (`sync.py:38`), and a running one is verify-only (`:37`). If the container were really kept stopped, a broken `on-create.sh` would pass every gate after the first.
  - The gate must guarantee the container is absent at gate start, and the spec must say "removed" (only the home volume stays warm).
- **REFUTED: §3j step 2 / arm (v), "stale lock (dead pid) detected and broken".** For flock this is not a real case: the kernel drops the lock when the holder dies (`host_lock.py:10-15`). `host_lock.held()` already gives the bounded wait, the holder label and descendant re-entry, at the same directory (`lock_path("verify-clone")` = `~/.local/state/dotfiles/verify-clone.lock`).
  - Ship already serializes the whole gate and the push under `HEAVY_GATE` (`pr.py:682`), so the "two concurrent ships" part of arm (v) already holds today. The new lock only matters for the #1555 `sync --full` routing.
- **UNVERIFIABLE: §3k criterion "the folder is an old lane or PR checkout".** It has no code-checkable definition.
- **UNVERIFIABLE: §2 `verify_clone.run_gate()` = "a `sync_main(full=True)` call with cwd = the clone" versus §3j step 5 "`mise run sync -- --full` with cwd = the clone".** These are two different execution contexts: an in-process call inherits the ship process's env, while a subprocess re-resolves it through mise in the clone. The code is the same either way (clone HEAD == worktree HEAD), but the env is not (MISSING-1). The spec must pick one.

**MISSING**

1. **The inherited port pin (load-bearing).** The main checkout's `mise.local.toml` has a live `DEVCONTAINER_SSH_PORT =` line (`grep -c` = 1) and a live `DOTFILES_PLATFORM =` line.
   - Under #1614, a `.claude/worktrees/*` worktree loads the main checkout's mise config, so `mise run ship` there carries main's port pin in `os.environ`.
   - Any child (`mise run sync` in the clone, or an in-process `sync_main`) re-reads it through `{{ env.DEVCONTAINER_SSH_PORT }}` (`mise.toml:368`). The clone container then binds main's port, and `ssh-keygen -R` (`:392`) wipes main's known_hosts entry.
   - "Never copy `mise.local.toml`" does not cover this. The gate must remove `DEVCONTAINER_SSH_PORT` (and `MISE_ENV`) from the child env.
   - Arm (iv) as written runs `mise run names` in the clone from a clean shell. That control sits in the wrong context, so it will pass while ship collides. It must run with the ship process's env.
2. **Clone remote and fetch source.** The spec does not say what is cloned or what is fetched.
   - The sha is unpushed at gate time, so it must come from the local repo (fetch `refs/heads/<branch>` from the main checkout's common dir; a bare sha fetch needs `allowAnySHA1InWant`).
   - Tier-1 identity runs `git merge-base HEAD origin/main` in the clone (`image.py:2010-2023`). If the clone's `origin/main` is the main checkout's local `main` (which only `land` moves), the merge-base can be stale. Specify `origin/main` = GitHub, fetched each gate.
3. **Where the clone gate slots in.** `gate_matrix` adds `Gate("sync-full", ("mise","run","sync","--","--full"))` (`pr.py:439-440`), and `run_gates` always runs with `cwd=workspace` (`:448`) inside `_gate_and_push` under `HEAVY_GATE` (`:682`).
   - The clone gate needs either a `cwd` on `Gate` or a linked-worktree branch in `gate_matrix`. Preflight (`:612`) must stop refusing.
   - The `pr`, `doctor` and `coordinator_handoff` tests reference the refusal (`tests/test_pr.py`, `tests/test_doctor.py`, `tests/test_coordinator_handoff.py`).
4. **Reaper invocation.** Prune needs a workspace or stem parameter: `devcontainer name|teardown|teardown-images` all resolve from cwd (`devcontainer_names.py:658, 1005, 1124`). Otherwise reaping must be its own sanctioned path. Prune also runs host-wide `docker builder prune` (P24a).
5. **Doppler secrets files for reaped stems.** `~/.local/state/dotfiles/doppler-<hash>-<arch>.env` (`devcontainer_names.py:321`, `:1116`) holds real secrets, and prune never deletes it (`mise.toml:1181-1281`). A clone gate creates another one. The reaper should remove these.
6. **Orphan volumes.** After `down`, the clone's warm volume has no container. Volumes carry no labels, so the only volume-to-workspace route is the name stem plus re-deriving the hash from known paths (main checkout, clone path, `git worktree list`).
7. **#1555 routing versus land.** `land` validates main through `sync_main(workspace)` at `pr.py:1059`. Under PIN/E, land must sync `main_checkout(workspace)`, not route through `verify_clone`. "`sync --full` from a linked worktree routes through `verify_clone`" would make land validate the clone's checkout of main instead of main's container.
8. **`mise trust`.** It is harmless and redundant on this host: the user-global `~/.config/mise/config.toml:9` has `trusted_config_paths = ["/"]`. Keep it for portability, but note that it writes user-level mise state.
9. **`sync` side effects.** `sync` in the clone can trigger `refresh_local_tag` and `dev-rebuild` when local `:dev` is stale (`sync.py:803-818`), which is a multi-GB pull inside ship. Main's container image id is unaffected, because its container is already created (arm vi holds).
10. **Side-fix asymmetry (non-blocking).** It changes `needs_full_sync` only. `land` still uses `touches_surface(merge_paths)` (`pr.py:1028`), so an `.md`-only merge still gets the full tier. The exclusion must filter paths one by one before `touches_surface`.

VERDICT: correct the spec first. Blocking items:
- P23 is false by CLI source, so REAP classification needs the mount-source route.
- P24 and the per-stem prune are infeasible as specified.
- "stopped, via devcontainer CLI" contradicts `stop` = `docker rm -f`, and arm (ii) depends on removal.
- MISSING-1 (main's inherited port pin) defeats §3j's invariants and arm (iv).
- MISSING-2 (fetch source and `origin/main`) and MISSING-3 (gate slot) are needed for the gate to work at all.

Non-blocking residuals: the stale-pid lock wording (use `host_lock`), the `run_gate` wording, "old lane/PR checkout", and MISSING 5, 6, 8, 9, 10.

Key files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/{python/src/dotfiles_setup/pr.py, sync.py, devcontainer_names.py, host_lock.py, doctor.py, image.py; mise.toml; .devcontainer/devcontainer.json; .github/workflows/ci.yml}` and `/Users/rmanaloto/.local/share/mise/installs/npm-devcontainers-cli/0.89.0/node_modules/@devcontainers/cli/dist/spec-node/devContainersSpecCLI.js:488`.

## GitHub repos touched

_None._ (local sources: worktree at ec916579, installed devcontainers CLI 0.89.0, mise.toml, KB offline docs)
