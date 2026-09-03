# Investigation: #947 Mechanism — What Writes to Repo-Root mise.lock

**Status:** Evidence gathered; ready for codex advisory

**Decision under advice:** Find the exact mechanism by which `mise run lock-image -- --no-container` writes to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.lock` during CI job `image-lock-pr` in run `33763936742`.

**Constraint:** The architect has already ruled out several hypotheses (see below); do not re-derive them.

**Ruled out (measured with real mise 2026.9.1):**
- bare `mise lock` writes task-scoped tools to root lock (different mechanism, different job #821)
- `mise lock <explicit names>` does not write the root lock
- `mise install` does not touch the lock
- `mise run <task>` under `auto_install = true` does not touch the lock

---

## Evidence Gathered

### CI Run Log Analysis (run 33763936742)

**CI Job Flow:**
1. `setup-mise` installs python and uv via `jdx/mise-action`
2. `Check image-lock drift` — runs pytest, checks lock versions (PASSES with 1 test failure)
3. `Regenerate image locks` — runs `mise run lock-image -- --no-container` 
4. `Re-check image-lock drift after regeneration` — pytest checks (PASSES)
5. `Confirm the diff is confined to the two image locks` — **FAILS** with git status showing `M mise.lock`

**The Failure:**
```
regeneration touched files outside the image locks:
 M mise.lock
```

Log timestamp: 2026-09-03T13:58:40 (during confine-check step)

### Code Path Analysis

**Task Definition:** `mise.toml [tasks.lock-image]`
```
run = 'uv run --project python dotfiles-setup image-lock'
```
- No explicit `depends` clause
- `auto_install = true` (global setting)

**`image_lock.py` Subprocess Chain:**
1. Line 383-388: `image_lock_main()` checks `host_can_lock()`
   - CI runner is Linux x86_64, so returns `True`
   - Does NOT route into container (no `container_command()` call)
2. Line 425-427: Calls `stage_system_lock_dir(stage_dir)` — stages the image config
3. Line 427: Calls `run_lock_passes(mise_bin, stage_dir, platforms)` — subprocess
4. Line 285-295: Subprocess invocation with:
   - `argv = ["/tmp/mise-pinned/mise", "lock", "--platform", ..., "-C", "/tmp/dotfiles-image-lock-XXXX/"]`
   - `MISE_TRUSTED_CONFIG_PATHS` = `/tmp/dotfiles-image-lock-XXXX/` (stage dir, not repo root)
5. Line 428: Calls `collect_system_lock(repo_root, stage_dir)` — copies stage locks to `.devcontainer/mise-*.lock`

**Key Observation:** The only `mise lock` subprocess uses `-C <stage_dir>` with `MISE_TRUSTED_CONFIG_PATHS` set to stage dir. Per architect's test, this should not write to repo root.

### Tool Installation Trace

When `mise run lock-image` starts, auto_install invokes multiple tool installations:
- agnix, doppler, editorconfig-checker, devcontainers-cli, agents-lint, colima, betterleaks, mcp2cli, renovate, biome, claude-code-lint, contextlint, markdownlint-cli2, and others
- npm/bun installs print `Saved lockfile` (for npm packages, not mise.lock)
- uv `tool install` for pipx packages prints `Saved lockfile` (for uv tool cache, not mise.lock)

**No direct `mise lock` invocation found in logs except:**
- `Detected a mise lock file, running mise install --locked` (during setup-mise, not regenerate)
- `mise lock --upgrade` (WARN message, not actual invocation)
- `mise lock converged on pass 1/5` (subprocess with stage dir, at 13:58:39)

### Containment Mechanism — What Should Work

1. **`-C <stage_dir>` flag:** mise lock should read/write config only in `stage_dir`
2. **`MISE_TRUSTED_CONFIG_PATHS` env override:** Subprocess receives only stage dir, not repo root
3. **`python/src/dotfiles_setup/lock_refresh.py`:** Explicitly documents that `lock_shared.py` "never touches the root `mise.lock`"

### Unresolved Questions

1. **Parent process modification:** Does the Python code or `uv run` invocation itself modify `mise.lock` before/after the subprocess?
2. **`uv run` interaction:** When `uv run --project python` runs, does it invoke mise in a way that triggers a lock update?
3. **Tool dependency resolution:** When `mise run lock-image` resolves task dependencies, does a tool's installation as part of auto_install write to the lock?
4. **Subprocess env replacement:** Confirmed subprocess env uses `**os.environ` + explicit overrides, so `MISE_TRUSTED_CONFIG_PATHS` is properly replaced, not appended

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — investigation of the image-lock task and subprocess mechanism

---

## Codex Advisory Findings

**Codex conducted static analysis in a read-only sandbox** (cannot reproduce the failure with real subprocess state) but applied the following diagnostic approach:

### Hypotheses Tested

1. **Inherited environ variable (`MISE_PROJECT_ROOT`, `MISE_LOCK`, etc.)** — Codex looked for any escape from `-C <stage_dir>` via an inherited mise environment variable that subprocess.run might inherit despite the env dict override.

2. **Second uncontained subprocess** — Searched for multiple `subprocess.run` invocations or direct file writes to root `mise.lock` in image_lock.py and lock_refresh.py.

3. **Environment merge order** — Examined whether `{**os.environ, ..., "MISE_TRUSTED_CONFIG_PATHS": stage_dir}` properly replaces vs. appends.

4. **Pre-subprocess modification** — Checked whether the parent process (before calling run_lock_passes) writes to the lock via `uv run` side effects or Python import-time behavior.

### Codex's Constraint

The read-only sandbox prevents:
- Real subprocess execution to observe actual environment isolation
- Measuring what `subprocess.run(..., env=child_env)` actually inherits
- Reproducing the exact CI runner environment

### What Codex DID Find

- **No second uncontained `mise lock` call** in the reachable code graph
- **Lock command is properly scoped** with `-C stage_dir`  
- **Environment override structure is correct** in Python: `{**os.environ, "MISE_TRUSTED_CONFIG_PATHS": stage_dir}` DOES replace the parent value (dict unpacking followed by explicit key assignment)
- **No direct `mise.lock` writes** visible in image_lock.py or lock_refresh.py source
- **collect_system_lock copies ONLY to `.devcontainer/mise-*.lock`**, not to root

---

## Verdict: Unable to Identify Mechanism — Requires Real Reproduction

The modification to root `mise.lock` is **confirmed to occur** (CI logs show `M mise.lock` in git status), but the **exact mechanism escapes static analysis**. 

**Probable root causes (ordered by likelihood):**

1. **A third `mise lock` call invoked by uv or Python internals**, not directly visible in the image_lock.py code path — e.g., when `uv run --project python` resolves its environment, mise might auto-refresh the root lock as a side effect.

2. **Environment isolation leakage**: The subprocess env dict correctly contains the override, but `MISE_TRUSTED_CONFIG_PATHS` on a CI runner might not work as intended (e.g., mise 2026.9.1 on ubuntu-latest might resolve configs differently than expected).

3. **Timing/state issue**: The root `mise.lock` modification happens outside the `run_lock_passes` subprocess — perhaps during `mise run` task resolution or tool auto-install BEFORE the subprocess is spawned.

---

## Required Next Steps

To identify the mechanism definitively, one of the following is needed:

1. **Strace/ltrace the subprocess** to see which processes write to which files during `mise run lock-image -- --no-container`
2. **Add logging to subprocess.run()** in image_lock.py to output the exact argv and env dict before invocation
3. **Run a CI simulation locally** on a Linux x86_64 machine with mise 2026.9.1 and capture file system calls during the task
4. **Inspect the actual git diff** from run 33763936742 to see what lines in mise.lock changed (to infer WHEN and from WHERE the change came)

