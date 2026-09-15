# SDLC review: mise lifecycle and native Claude installation

## Verdict

Mise has **no lifecycle event that runs once per machine, project setup, or configuration change**. Its closest native mechanism is task freshness through `sources` and `outputs`, but timestamp freshness cannot prove that the `claude` currently resolving on `PATH` is native or at the pinned version.

The required installation should use an **explicit, uncached mise task backed by a Python version/ownership guard**. Each environment setup path should invoke that task once after its mise installation completes. The guard runs cheaply every time; the native installer runs only when Claude is missing, shadowed, or at the wrong version.

Do not make the required installation a top-level `postinstall` hook. Mise catches failures from inline and task-backed hooks, warns, and continues, so a failed Claude installation would not fail `mise install`. See [hook failure handling](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/src/hooks.rs:499), especially lines 520–585.

## Licensed dissent and current blockers

The specification’s current-state premise is false for the devcontainer:

- [`.devcontainer/mise-runtime.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:58) still declares `claude-code = "latest"`.
- [`.devcontainer/mise-runtime.lock`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.lock:583) resolves it through `aqua:anthropics/claude-code` at **2.1.270**.
- [`schemas/sources.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:48) declares the authoritative version as **2.1.272** and explicitly says there is no mise tool pin.

Therefore, Claude is still mise-managed inside the published image and differs from the stated authoritative version. That declaration and its lock entry must be removed before the repository can truthfully claim native-only ownership.

There is also an unresolved policy contradiction. [`currency.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/currency.toml:29) says the native installer owns Claude and self-updates, while the specification requires one exact version across host, CI, and container. The eventual implementation must choose one contract:

1. Disable native auto-update where exact cross-environment parity is required.
2. Treat 2.1.272 as a bootstrap/check target while permitting native updates afterward.

A third blocker is verification topology. The image smoke currently requires `claude` to be baked into the published image at [image.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:1042). Moving native installation to container creation requires moving or splitting that assertion.

## Complete top-level hook inventory

The `[hooks]` event set is exactly `cd`, `enter`, `leave`, `preinstall`, and `postinstall`; the source enum contains no others. See [hooks.rs](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/src/hooks.rs:32), lines 32–52.

| Event | When it fires | Frequency and scope |
|---|---|---|
| `cd` | Every detected directory change | Config-level, per activated shell transition; not per tool. |
| `enter` | Crossing into a project directory tree | Once per entry. Moving inside the same tree does not retrigger it. |
| `leave` | Crossing out of a project directory tree | Once per exit. Moving inside the tree does not trigger it. |
| `preinstall` | Before a nonempty selected-tool installation batch | Once per installation batch, not once per tool. It is absent on the no-work path. |
| `postinstall` | After the selected installation batch | Once per actual `mise install` invocation, including no-op installs; receives `MISE_INSTALLED_TOOLS=[]` when nothing was installed. |

Documentation and source evidence: [hooks.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/hooks.md:7), [toolset_install.rs](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/src/toolset/toolset_install.rs:333), and [install.rs](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/src/cli/install.rs:614).

`enter`, `leave`, and `cd` require `mise activate`; install hooks do not. All matching hooks from loaded configurations run, ordered from higher-precedence configurations to lower-precedence ones. Multiple array entries each start a subprocess. See [hooks.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/hooks.md:22).

`watch_files` is adjacent but structurally separate: it uses top-level `[[watch_files]]`, requires shell activation, and is checked during activation rather than by a background watcher. It is not a `[hooks]` event. See [hooks.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/hooks.md:153).

## Per-tool command options

The generic per-tool command-running option is `postinstall`. It runs after that particular tool/version installs successfully, with `MISE_TOOL_NAME`, `MISE_TOOL_VERSION`, `MISE_TOOL_INSTALL_PATH`, and related context. Independent tool installations may run these commands in parallel. See [hooks.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/hooks.md:98).

The GDB entry at [mise-system.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-system.toml:86) is this per-tool form. It differs from project `[hooks].postinstall` in three ways:

- It belongs to one declared tool and runs only when that tool installs.
- Its failure propagates as an installation failure.
- It does not run on unrelated or no-op installs.

There is no generic per-tool `preinstall`. The controlled search for `preinstall` in the per-tool documentation returned `rc=1`; the identical search for known-present `postinstall` returned `rc=0` with multiple matches.

Using this mechanism for Claude would require a synthetic Claude tool entry, directly violating the native-only constraint.

## Task lifecycle and once-like behavior

- `depends` schedules prerequisites before a task. A shared dependency is deduplicated within one resolved task graph, but that state does not survive another `mise run`. See [task-configuration.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:107).
- `depends_post` schedules tasks after the parent; the same task referenced before and after can execute twice. See [task-configuration.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:231).
- `wait_for` only waits for a matching task that is already scheduled. It does not schedule or persist anything. See [task-configuration.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:253).
- `sources` plus `outputs` skips execution when every output exists and the oldest output is newer than the newest source. The task definition is also an implicit source. See [task-configuration.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:440).
- `outputs = { auto = true }` uses an internal marker under `~/.local/state/mise/task-outputs/`. See [task-configuration.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:595).
- Missing explicit outputs cause the task to run again. Freshness remains timestamp-based. See [running-tasks.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/running-tasks.md:171).

There is no `run_once` field or persistent equivalent. The controlled search for `run_once` across task documentation, schemas, and source returned `rc=1`; the same search shape for `wait_for` returned `rc=0`, including the schema and implementation.

Task freshness is unsuitable as the authority for Claude because a fresh marker can survive deletion, PATH shadowing, or replacement by a wrong-version executable. Artifact caching is also inappropriate because the native installer changes external user state that cannot be faithfully represented as a task-cache artifact.

`mise bootstrap` provides a deliberately invoked machine-setup lifecycle, but it is not once-only. Its hooks and final `bootstrap` task run on every selected bootstrap application and must themselves be idempotent. See [bootstrap.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/bootstrap.md:199), especially lines 207–209 and 320–333.

## `mise exec`, `mise run`, and external tools

`mise exec` loads mise’s environment and executes an arbitrary command. It has no task freshness behavior. `mise run` executes configured tasks and owns dependency and freshness processing. Both can auto-install missing **mise-managed** tools. See [exec.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/exec.md:6) and [run.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/run.md:6).

Mise has no declaration meaning “require binary X on PATH and run arbitrary installer Y when absent”:

- `path:<PATH>` selects an existing runtime but does not install it.
- `mise link` registers an externally built installation but does not create or repair it.
- `mise sync` supports specific Node and Python managers.
- `@system` does not install or enforce a version.
- A custom backend could install Claude, but would make mise its tool manager.

The negative search for an `externally_managed` configuration surface returned `rc=1`; the same corpus and command shape found known-present `postinstall` with `rc=0`.

## GitHub Actions behavior

The lint job calls the local composite once at [ci.yml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:96). That composite invokes `jdx/mise-action` twice at [action.yml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/actions/setup-mise/action.yml:24):

1. `mise install --locked bun pipx`
2. `mise install --locked` for the full configured toolset

The action’s `install` input defaults to true, and every action invocation calls `miseInstall()` after cache restoration. See the pinned action’s [action definition](https://github.com/jdx/mise-action/blob/v4.3.0/action.yml#L30-L40) and [execution path](https://github.com/jdx/mise-action/blob/v4.3.0/src/index.ts#L57-L107).

Therefore, the root project’s `postinstall` fires **exactly twice during the successful lint setup path**. It fires once per actual install command, not once per installed tool. A warm action cache does not change this because the action still runs `mise install`, and mise explicitly fires `postinstall` on a no-op install.

For process-count diagnostics, the action also runs two `mise install --help` capability probes. Thus the job starts four processes whose command begins with `mise install`, but only two are actual installer invocations and only those two fire the lifecycle hook.

The comment at [ci.yml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:137), lines 140–141, is stale: it says cache restoration prevents mise from rerunning install and therefore suppresses `postinstall`. Current action and mise source contradict that statement.

`MISE_LOCKED=1` remains effective for mise-managed tools, but it does not manage or lock a native installer launched by a task.

## Recommended design

Create one normal, uncached mise task backed by a Python command that:

1. Reads the authoritative Claude version from `schemas/sources.toml`.
2. Resolves the effective `claude` command and verifies native ownership.
3. Runs `claude --version`.
4. Exits immediately when ownership and version are correct.
5. Otherwise runs `curl -fsSL https://claude.ai/install.sh | bash -s <version>`.
6. Rechecks resolution, ownership, and exact version.
7. Returns nonzero on installer failure or any remaining mismatch.

Invoke that task once from each setup entry point:

- **macOS:** from the canonical host setup command after `mise install`.
- **CI:** as a fail-closed step in the setup-mise composite after the second `jdx/mise-action`.
- **Devcontainer:** invoke the same Python helper from [on-create.sh](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/scripts/on-create.sh:53), before smoke validation.

The devcontainer must use `onCreateCommand` because it is once per container creation and runs with the correct user, home directory, mounted persistent home, and `~/.local/bin` first on PATH. The container deliberately ignores the workspace’s root `mise.toml` at [devcontainer.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json:164), so the root hook cannot cover this path.

If an existing container must converge automatically when the pin changes, invoke the same cheap helper from `postStartCommand` as well. The installer will still run only on mismatch.

Do not configure `sources`, `outputs`, artifact caching, or a sentinel as the authoritative guard. They can reduce checks but weaken recovery from deletion, self-update drift, or PATH shadowing.

## Verification design for implementation

Use an isolated temporary `HOME` and controlled `PATH`, exercising the public task/CLI:

- Matching native version: task returns zero; installer stub must fail the test if called.
- Missing Claude: installer runs exactly once, installs the expected executable, and the task returns zero.
- Second invocation: installer call count remains one.
- Wrong version: installer runs; reverting the version comparison must make this test fail.
- Mise-shim shadowing: task rejects the shadowed resolution even if the version text matches.
- Installer failure: task returns nonzero; reverting failure propagation must make this test fail.
- Pin change: the new version causes exactly one new installation.
- CI wiring: current composite produces one ensure-task invocation after both actions; deleting that step must fail the topology test.
- Container wiring: deleting the on-create invocation must fail the lifecycle fixture.
- Ownership cleanup: any remaining `claude-code`, `http:claude`, or `aqua:anthropics/claude-code` tool declaration or lock entry must fail a controlled configuration assertion.

No runtime mutation arms were executed because review mode prohibited modifications and installation state changes.

## Evidence and execution notes

- Installed version probe: `mise --version`, direct `rc=0`, returned `2026.9.9 macos-arm64 (2026-09-15)`.
- Installed `mise run --help` and `mise exec --help` both returned `rc=0` and confirmed task freshness exists only on `run`.
- The on-disk mise source identifies itself as 2026.9.4 at [Cargo.toml](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/Cargo.toml:12); these capabilities therefore predate both CI’s 2026.9.8 and the host’s 2026.9.9.
- The required Graphify query was attempted first and returned direct `rc=1` because the read-only sandbox prevented mise from creating a temporary directory. Source and documentation were used as the fallback authority.
- No repository gates were run.
- No report file, checkout file, or commit was created.
- Final `git status --short` showed only the pre-existing modification to `docs/research/kb/reports/agents/mise-topology-advisor.md`.

Each initial full-history specialist spawn failed with `no thread with id: 01a0a68f-d34d-7db0-9f50-04500c7029fd`. Each was retried exactly once without conversation history and succeeded.

### Specialists spawned:

- `sdlc-config-specialist` as `/root/mise_config_review`
- `sdlc-workflows-specialist` as `/root/mise_workflow_review`
- `sdlc-image-specialist` as `/root/mise_image_review`
- No other specialists were spawned.

