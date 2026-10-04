# Premise report — `docs/specs/session-handoff-automation.md` rev 6 (22f4f588)

> Persisted verbatim at receipt by the handoff-automation lane (4daaf7e1), 2026-10-03. Producer: premise-verifier subagent (read-only).

PREMISE REPORT: rev 6 of `docs/specs/session-handoff-automation.md` at 22f4f588, scoped to the corrections for the rev-5 blocking items.

I had read-only tools (Read, Grep and Glob, no Bash), so nothing was persisted and you need to persist this report. I printed no secret values: I read only variable names from `mise.local.toml` and `mise.arm64.local.toml`, using a grep that matches the name and stops before `=`.

ROWS: 6 blocking items checked — 3 RESOLVED, 3 PARTIAL, 0 NOT RESOLVED

**P23 (classify by bind-mount source plus hash label): RESOLVED**
- **Hash and label line up.** `workspace_hash` is `sha256(str(Path(ws).resolve()))[:8]` (`devcontainer_names.py:174-175`). The label value is `dotfiles.workspace=<names.hash>` (`:245-247`). `names.hash` is `workspace_hash(resolved_workspace)` (`:304`).
- **Same directory on both routes.** The label is computed by `devcontainer env` from `Path.cwd()` (`:292, 1114`) in the `up` task (`mise.toml:385`). The mount source is that same cwd, via `devcontainer up --workspace-folder .` (`mise.toml:400`) and `workspaceMount source=${localWorkspaceFolder}` (`devcontainer.json:130`). Both are physical paths, so `workspace_hash(<route-1 path>)` reproduces the label, even for a path that has since been deleted (non-strict `resolve()`).
- **`.Mounts` carries the host source (precedent).** `container.py:97-104` already parses `docker inspect --format '{{json .Mounts}}'` and matches `Type=="bind"` and `Source==str(workspace)` against the host project root. It is load-bearing in the live `verify-container-latest` gate on Docker Desktop.
- **Residual (non-blocking).** A pre-#677 container has a mount source but no `dotfiles.workspace` label. The spec only says what happens when the two routes *disagree*, not when the label is *absent*. State that absent counts as skip.

**P24 (`teardown_container_ids(resolve_names(workspace=p), all_arches=True)`): PARTIAL**
- **Nonexistent path is accepted.** `resolve_names` calls `Path(source).resolve()` with no `strict` (`:292-293`). Python 3.14's non-strict `resolve` returns a path for a nonexistent target, and the hash matches what the container was created with (see P23).
- **Containers are covered.** With `all_arches=True` the filter is `label=dotfiles.workspace=<hash>` only (`:630-637`), which is arch-independent. The legacy folder filter uses the resolved `names.workspace` (`:642`).
- **Volumes and the doppler file are not fully covered.** `resolve_names` returns ONE architecture: `arch = platform_arch(resolve_platform(platform, env))` (`:295`), and `resolve_platform` takes `DOTFILES_PLATFORM`, else the host (`platform_target.py:474-480`). But `home_volume` (`:237`) and `doppler-<hash>-<arch>.env` (`:321`) are per architecture. So "home volume names and doppler file come from the same `resolve_names`" reaches only the resolving arch, and the other arch's `-home` volume and secrets file survive `--apply`.
- **Legacy volume not named.** The arch-less `legacy_home_volume` (`:242`) is not mentioned either.
- **Fix:** call `resolve_names(workspace=p, platform=<each arch>)` for both architectures, and name `legacy_home_volume`.
- **Port override is harmless here.** `resolve_names` also reads `DEVCONTAINER_SSH_PORT` (`:296-298`), but no container id or volume name depends on the port.

**P25 (`down` = `stop` = `docker rm -f`, removed before and after): RESOLVED**
- `stop` has alias `down` (`mise.toml:1285`), and its body is `devcontainer teardown` → `docker rm -f` (`:1300-1303`).
- `teardown_main` → `teardown_container_ids(resolve_names(), all_arches=False)` (`devcontainer_names.py:656-658`). Run with cwd = the clone, it filters on the clone's hash label AND the arch label, plus a legacy `devcontainer.local_folder=<clone path>`. The clone path differs from main's, so main's container can never match.
- Under `gate_env()`, `DOTFILES_PLATFORM` is pinned explicitly, so `up` and `down` resolve the same arch.
- **Residual:** `down` removes only the current arch's container. If a gate ever ran under the other arch, that clone container survives, and REAP never removes it because the clone path is never stale. Suggest `remove_container()` call `teardown_container_ids(resolve_names(workspace=clone), all_arches=True)` directly.

**MISSING-1 (`gate_env()`): RESOLVED**
- The main checkout's `mise.local.toml` names are `[env]`, `DOTFILES_PLATFORM` and `DEVCONTAINER_SSH_PORT`. `mise.arm64.local.toml` has the same two names. Nothing else is injected.
- Scrubbing `DEVCONTAINER_SSH_PORT`, `MISE_ENV` and those names is enough:
  - `mise.toml:368` (and `:434`, `:1115`) render `DEVCONTAINER_SSH_PORT` from `env.X | default('')`. A blank value falls through to derivation (`devcontainer_names.py:195`).
  - `mise.toml:214` renders `DOTFILES_PLATFORM = {{ env.DOTFILES_PLATFORM | default('linux/amd64/v2') }}`, so the explicitly passed value wins. With the scrub and no explicit value, the clone gets amd64/v2.
  - `mise.toml` has no `_.path`, `_.source` or `_.file` entries that could leak worktree paths. `GITLEAKS_CONFIG` is re-rendered from the clone's `config_root`.
- **Residual:** the spec does not say where the explicit `DOTFILES_PLATFORM` value comes from. Name it, e.g. the ship process's resolved value.

**MISSING-2 (fetch the unpushed branch from the main checkout path): RESOLVED**
- This rests on git semantics, not repo code. `refs/heads/*` and objects live in the common dir, which is the main checkout's `.git`, so upload-pack from the main checkout path sees a branch that is checked out in a linked worktree.
- "Checked out elsewhere" only blocks writes (push or checkout), not reads.
- No `allowAnySHA1InWant` is needed for a named ref. A `refs/verify/*` destination accepts non-fast-forward updates without `+`: git-fetch(1) says updates outside `refs/{tags,heads}/*` are accepted unforced.
- `origin/main` is refreshed from GitHub every gate, which covers `image.py:2010-2023`.
- I did not run this; arm (iii)/L7 should exercise it live.

**MISSING-3 (Gate gains env; `run_gates` passes cwd and env): PARTIAL**
- **Wrong citation.** `Gate` is at `pr.py:221-226`, not `:222-243`; that range is `_run`. It has only `name` and `cmd`.
- **`Gate` also needs `cwd`.** The spec says Gate "gains `env`" but then uses `gate.cwd` and `Gate(…, cwd=<clone>)`.
- **`_stream` must change, and the spec does not say so.** `_stream(cmd, *, cwd)` hard-codes `env=child_env.without_git_context()` (`:256-260`) and has no `env` parameter.
  - If `run_gates` forwards `env=gate.env` and that is `None` for every ordinary gate, `subprocess.run(env=None)` inherits the full `os.environ`, including `GIT_DIR` and `GIT_WORK_TREE`. That would silently drop the git-context scrub from every other gate.
  - The spec must say: `_stream` gains `env`, and `None` falls back to `without_git_context()`.
- **`gate_matrix` cannot detect a linked worktree.** Its signature is `gate_matrix(paths, *, suite_at_push=False)` (`:377`), with no workspace.
- **The always-remove step has no home.** `run_gates` returns on the first failure (`:451-452`). §3j steps 2-7 (lock, `ensure_clone`, fetch, `down` before, `down` after on pass and on fail) cannot be one Gate `cmd`. The spec needs to place them: either the Gate cmd is a single wrapper (e.g. `mise run verify-clone -- gate`) that owns the lock and a `try/finally`, or `_gate_and_push` wraps `run_gates` in that `finally`.

**MISSING (new in rev 6):**
- **Squash merges hide stale worktrees (load-bearing).** §3k criterion (b) uses `git branch --merged origin/main`, but this repo squash-merges: `pr.py:27, 510, 529` arm `--squash --delete-branch`. A squash-merged branch is never an ancestor of `origin/main`, so `--merged` never lists it. The local branch in the worktree also survives, because `--delete-branch` deletes only the remote. Lane worktrees would never classify as stale, and L8 ("every stale lane or PR stem is listed") fails. Define "gone" as upstream gone (tracking `[gone]` after `git fetch --prune`), or as the PR's state being MERGED.
- **Per-arch volumes and doppler files under REAP:** see P24. Load-bearing, because secrets files survive `--apply`.
- **`Gate.cwd`, `_stream` env fallback, `gate_matrix` signature, and where the `finally` lives:** see MISSING-3. Load-bearing for the shape of the implementation.
- **Lock order (checked, no defect).** The verify-clone lock is taken while ship holds `HEAVY_GATE` (`pr.py:682`). `sync.py` takes neither lock, and the interactive route takes only verify-clone, so there is no inverse order and no deadlock.
- **Unlabelled pre-#677 containers:** route 2 is absent, so state "skip" explicitly (see P23).

VERDICT: correct the spec first. Three small edits are needed:
1. In §3k, iterate both architectures (and name `legacy_home_volume`) for volumes and doppler files.
2. In §3k, replace `--merged` with an upstream-gone or PR-merged test that works with squash merges.
3. In the `pr.py` gate-slot row, add `Gate.cwd`, the `_stream` env parameter with a `without_git_context()` default, a workspace parameter on `gate_matrix`, and an explicit `finally` for clone removal.

Non-blocking residuals:
- the arch-scoped `down` in the clone (use `all_arches`);
- the source of `DOTFILES_PLATFORM`;
- the absent-label skip.

Key files (absolute):
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/python/src/dotfiles_setup/{devcontainer_names.py,pr.py,container.py,platform_target.py,child_env.py,host_lock.py}`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/mise.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.devcontainer/devcontainer.json`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.local.toml` and `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.arm64.local.toml` (names only)

## GitHub repos touched

_None._ (local sources only)
