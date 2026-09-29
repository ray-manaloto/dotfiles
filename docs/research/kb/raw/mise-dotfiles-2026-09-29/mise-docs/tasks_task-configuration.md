[Skip to content](https://mise.jdx.dev/tasks/task-configuration.html#VPContent)

On this page

# Task Configuration [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-configuration)

Use this reference to configure task commands, dependencies, inputs, and execution settings. For a starting example, see [TOML tasks](https://mise.jdx.dev/tasks/toml-tasks.html) or [file tasks](https://mise.jdx.dev/tasks/file-tasks.html). To share settings across tasks, use [task templates](https://mise.jdx.dev/tasks/templates.html).

## Task properties [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-properties)

The examples use `[tasks.<name>]` in `mise.toml`. Unless noted otherwise, the same properties are available in file-task `#MISE` headers.

### `run` [​](https://mise.jdx.dev/tasks/task-configuration.html\#run)

- **Type**: `string | (string | { task: string, args?: string[], env?: { [key]: string } } | { tasks: string[] })[]`

The commands or execution steps to run. A task may instead use [`file`](https://mise.jdx.dev/tasks/task-configuration.html#file), inherit its command through `extends`, or contain only dependencies to group other tasks. Each `run` entry finishes before the next starts; a `{ tasks = [...] }` entry runs its listed tasks in parallel.

You can mix scripts with task references, and pass optional `args` and `env` to referenced tasks:

mise-toml

```
[tasks.grouped]
run = [\
  { task = "t1" },          # run t1 (with its dependencies)\
  { task = "build", args = ["--release"], env = { RUSTFLAGS = "-C opt-level=3" } },\
  { tasks = ["t2", "t3"] }, # run t2 and t3 in parallel (with their dependencies)\
  "echo end",               # then run a script\
]
```

`{ task }` and `{ tasks }` are execution steps for this task, not [`depends`](https://mise.jdx.dev/tasks/task-configuration.html#depends). They still run with their own dependencies. `mise tasks deps` does not include them as graph edges. See [`mise tasks deps`](https://mise.jdx.dev/cli/tasks/deps.html).

Simple forms still work and are equivalent:

mise-toml

```
tasks.a = "echo hello"
tasks.b = ["echo hello"]
tasks.c.run = "echo hello"
[tasks.d]
run = "echo hello"
[tasks.e]
run = ["echo hello"]
```

### `run_windows` [​](https://mise.jdx.dev/tasks/task-configuration.html\#run-windows)

- **Type**: `string | (string | { task: string, args?: string[], env?: { [key]: string } } | { tasks: string[] })[]`

A Windows-specific variant of `run` that supports the same structured syntax:

mise-toml

```
[tasks.build]
run = "cargo build"
run_windows = "cargo build --features windows"
```

### `file` [​](https://mise.jdx.dev/tasks/task-configuration.html\#file)

- **Type**: `string`

Execute an external script instead of an inline `run` command. Relative paths are resolved from the directory containing the task's config file. The path supports Tera templates.

mise-toml

```
[tasks.release]
description = "Cut a new release"
file = "scripts/release.sh"
```

`file` also accepts HTTP(S) URLs and `git::` sources. See [Using a file or remote script](https://mise.jdx.dev/tasks/toml-tasks.html#using-a-file-or-remote-script) for the supported formats and security considerations.

### `description` [​](https://mise.jdx.dev/tasks/task-configuration.html\#description)

- **Type**: `string`

A description of the task. This is used in (among other places) the help output, completions, `mise run` (without arguments), and `mise tasks`.

mise-toml

```
[tasks.build]
description = "Build the CLI"
run = "cargo build"
```

### `alias` [​](https://mise.jdx.dev/tasks/task-configuration.html\#alias)

- **Type**: `string | string[]`

An alias for the task so you can run it with `mise run <alias>` instead of the full task name.

mise-toml

```
[tasks.build]
alias = "b" # run with `mise run b`
run = "cargo build"
```

If another task is actually named `b`, that task wins—a task's own name always takes precedence over an alias, including over an alias defined in a parent directory's config.

### `depends` [​](https://mise.jdx.dev/tasks/task-configuration.html\#depends)

- **Type**: `string | (string | string[] | { task: string, args?: string[], env?: { [key]: string }, optional?: bool })[]`

Tasks that must run before this task, given as a list of task names or aliases. Arguments can be passed to a dependency, e.g.: `depends = ["build --release"]`. If multiple tasks share a dependency, that dependency runs only once. mise runs whatever it can in parallel (up to [`--jobs`](https://mise.jdx.dev/cli/run.html)) based on `depends` and related properties.

[`mise tasks deps`](https://mise.jdx.dev/cli/tasks/deps.html) visualizes this declared graph (`depends`, `wait_for`, `depends_post`), not task references inside `run`.

mise-toml

```
[tasks.build]
run = "cargo build"
[tasks.test]
depends = ["build"]
run = "cargo test"
```

#### Passing environment variables to dependencies [​](https://mise.jdx.dev/tasks/task-configuration.html\#passing-environment-variables-to-dependencies)

You can pass environment variables to specific dependencies using two syntaxes:

**Shell-style inline:**

mise-toml

```
[tasks.test]
depends = ["NODE_ENV=test setup"]
run = "npm test"

[tasks.setup]
run = 'echo "Setting up for $NODE_ENV"'
```

**Structured object format:**

mise-toml

```
[tasks.test]
depends = [\
  { task = "setup", env = { NODE_ENV = "test", DEBUG = "true" } }\
]
run = "npm test"
```

The structured format also supports combining env vars with arguments:

mise-toml

```
[tasks.deploy]
depends = [\
  { task = "build", args = ["--release"], env = { RUSTFLAGS = "-C opt-level=3" } }\
]
run = "./deploy.sh"
```

String and structured dependencies can be mixed in the same array:

mise-toml

```
[tasks.check]
depends = [\
  "lint",\
  { task = "test", env = { CI = "true" } },\
]
run = "echo checks complete"
```

These environment variables are passed only to the specified dependency, not to the current task or other dependencies.

#### Optional dependencies [​](https://mise.jdx.dev/tasks/task-configuration.html\#optional-dependencies)

Set `optional = true` on a structured dependency to run matching tasks when they exist, without failing when the task name or pattern matches nothing. Invalid task patterns still produce an error.

mise-toml

```
[tasks.test]
depends = [\
  { task = "//...:test", optional = true },\
  { task = "//...:test:*", optional = true },\
]
```

#### Passing parent task arguments to dependencies [​](https://mise.jdx.dev/tasks/task-configuration.html\#passing-parent-task-arguments-to-dependencies)

You can forward a parent task's arguments to its dependencies using `{{usage.*}}` templates. Both the parent and child tasks must define a `usage` spec for the arguments they accept:

mise-toml

```
[tasks.build]
usage = 'arg "<app>"'
run = 'echo "building {{usage.app}}"'

[tasks.deploy]
usage = 'arg "<app>"'
depends = [{ task = "build", args = ["{{usage.app}}"] }]
run = 'echo "deploying {{usage.app}}"'
```

Running `mise run deploy myapp` passes `"myapp"` to both `deploy` and its `build` dependency.

This also works with the string syntax:

mise-toml

```
[tasks.deploy]
usage = 'arg "<app>"'
depends = ["build {{usage.app}}"]
run = 'echo "deploying {{usage.app}}"'
```

And with flags:

mise-toml

```
[tasks.compile]
usage = 'flag "--target <target>"'
run = 'echo "compiling for $usage_target"'

[tasks.package]
usage = 'flag "--target <target>"'
depends = [{ task = "compile", args = ["--target", "{{usage.target}}"] }]
run = 'echo "packaging for $usage_target"'
```

Arguments flow through dependency chains — if A depends on B which depends on C, each task can forward its resolved arguments to its own dependencies.

### `depends_post` [​](https://mise.jdx.dev/tasks/task-configuration.html\#depends-post)

- **Type**: `string | (string | string[] | { task: string, args?: string[], env?: { [key]: string }, optional?: bool })[]`

Like `depends`, but these tasks run _after_ this task and its dependencies complete. For example, you may want a `postlint` task that you can run individually without also running `lint`:

mise-toml

```
[tasks.lint]
run = "eslint ."
depends_post = ["postlint"]
[tasks.postlint]
run = "echo 'linting complete'"
```

Supports the same argument, environment variable, and optional dependency syntax as `depends`. Dependencies of a `depends_post` task also wait until the parent task finishes, so an entire cleanup chain runs after the main work. mise runs the full subtree if the parent started, even when the parent fails, but skips it when a regular dependency fails before the parent can start. The same task may be referenced by both `depends` and `depends_post`; in that case it runs once before the parent and once afterward.

### `wait_for` [​](https://mise.jdx.dev/tasks/task-configuration.html\#wait-for)

- **Type**: `string | (string | string[] | { task: string, args?: string[], env?: { [key]: string }, optional?: bool })[]`

Like `depends`, this waits for the listed tasks to complete before running. Unlike `depends`, `wait_for` does not add matching tasks to the run; it only waits for them when they are already scheduled. To allow a task name or pattern to have no configured matches, use `optional = true`.

mise-toml

```
[tasks.lint]
wait_for = ["render"] # creates some js files, so if it's running, wait for it to finish
run = "eslint ."
```

Supports the same argument, environment variable, and optional dependency syntax as `depends`.

`wait_for` matches tasks differently depending on whether args or env vars are specified:

- `wait_for = ["setup"]` — matches by name, regardless of args or env overrides. If another task runs `depends = ["DEBUG=1 setup"]`, this will still match and wait for it.
- `wait_for = ["setup arg1"]` or `wait_for = ["DEBUG=1 setup"]` — matches only tasks running with that exact args/env configuration.

### `daemons`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#daemons)

- **Type**: `bool | string | string[]`

[Project daemons](https://mise.jdx.dev/daemons.html) that must be running and ready before task execution. Requires `experimental = true` and pitchfork 2.25.0 or later.

| Value | Requirement |
| --- | --- |
| `"postgres"` | One named daemon. |
| `["postgres", "redis"]` | Each named daemon. |
| `true` | All daemons in the task's project configuration. |
| `false` or omitted | No daemon requirement. |

mise-toml

```
[daemons]
postgres = "18"

[tasks.test]
daemons = "postgres"
run = "npm test"
```

mise starts the requested daemons through pitchfork and waits for readiness before any task body runs. Already-running daemons are reused and remain running after the task exits; use `mise daemons stop` to stop them.

Names must match `[daemons]` entries in the task's own project configuration hierarchy, including inherited declarations. In a monorepo, a dependency task in another subproject resolves its names there, not in the calling project's config. An unknown name fails the run.

`--skip-deps` and the `task.skip_depends` setting skip daemon requirements. `--dry-run` still validates names and the experimental setting, but starts nothing. Safe mode blocks task daemon startup.

A subtask reached through a `run = [{ task = "..." }]` entry is resolved after the run has started, so its own `daemons` are not started. Declare the requirement on the task you invoke.

For setup, readiness checks, and daemon lifecycle details, see the [daemon guide](https://mise.jdx.dev/daemons.html#tasks-that-require-daemons).

### `env` [​](https://mise.jdx.dev/tasks/task-configuration.html\#env)

- **Type**: `{ [key]: string | int | bool }`

Environment variables specific to this task. These are not passed to `depends` tasks.

mise-toml

```
[tasks.test]
env.TEST_ENV_VAR = "ABC"
run = [\
    "echo $TEST_ENV_VAR",\
    "mise run some-other-task", # running tasks like this _will_ have TEST_ENV_VAR set of course\
]
```

### `vars` [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-vars)

- **Type**: `{ [key]: string | int | bool | directive }`

Values available through `{{ vars.NAME }}` when mise renders this task. Task-local values override config vars and vars inherited from a task template. They are not exported as environment variables; use [`env`](https://mise.jdx.dev/tasks/task-configuration.html#env) for values the task process should inherit.

mise-toml

```
[vars]
mode = "headless"

[tasks.test]
vars = { mode = "headed" }
run = "echo --mode={{ vars.mode }}"
```

`mise run test` prints `--mode=headed`. Other tasks still use the config value, `headless`, unless they define their own override.

Overrides apply to references in the task's templated fields, including inherited fields. They do not recalculate top-level vars that were already resolved during config loading. See [variable resolution](https://mise.jdx.dev/configuration/vars.html#what-a-task-local-var-can-change) for an example, and [task template vars](https://mise.jdx.dev/tasks/templates.html#parameterizing-a-template-with-vars) for sharing a command with different values in each task.

See [configuration variables](https://mise.jdx.dev/configuration/vars.html#value-directives) for value directives and redaction.

### `tools` [​](https://mise.jdx.dev/tasks/task-configuration.html\#tools)

- **Type**: `{ [key]: string }`

Tools to install and activate before running the task. This is useful for tasks that require a specific tool or a different version of a tool. These tools apply only to that task, not to its dependencies.

mise-toml

```
[tasks.build]
tools.rust = "1.50.0"
run = "cargo build"
```

Run [`mise lock`](https://mise.jdx.dev/dev-tools/mise-lock.html) to resolve task-specific tools into the owning config's lockfile before running the task. This reads the task definition without executing the task or installing its tools.

Run `mise install --include-task-tools` to install tools for every task in the current scope without executing task commands or dependencies. This is useful for preparing CI caches or container images; combine it with `--monorepo` to include every configured monorepo root.

### `dir` [​](https://mise.jdx.dev/tasks/task-configuration.html\#dir)

- **Type**: `string`
- **Default**: `"{{ config_root }}"` \- the directory containing `mise.toml`, or for a path like `~/src/myproj/.config/mise.toml`, `~/src/myproj`.

The directory to run the task from. Most commonly, this is used to run the task in the user's current directory:

mise-toml

```
[tasks.test]
dir = "{{cwd}}"
run = "cargo test"
```

### `hide` [​](https://mise.jdx.dev/tasks/task-configuration.html\#hide)

- **Type**: `bool`
- **Default**: `false`

Hide the task from help, completion, and other output like `mise tasks`. Useful for deprecated or internal tasks you don't want others to easily see.

mise-toml

```
[tasks.internal]
hide = true
run = "echo my internal task"
```

### `confirm` [​](https://mise.jdx.dev/tasks/task-configuration.html\#confirm)

- **Type**: `string` \| `{ message: string, default: string }`

A message to show before running the task. This is useful for tasks that are destructive or take a long time to run. The user is prompted to confirm before the task's own `run` command executes.

WARNING

`confirm` only guards the task's own `run` command. Dependencies (`depends`) execute **before** the confirmation prompt appears. If you need confirmation before dependencies run, add `confirm` to the dependency tasks themselves, or use `run = [{ task = "..." }]` instead of `depends`.

mise-toml

```
[tasks.release]
confirm = { message = "Are you sure you want to cut a release?", default = "no" }
description = 'Cut a new release'
file = 'scripts/release.sh'
```

The confirm message supports Tera templates and can reference usage arguments:

mise-toml

```
[tasks.deploy]
usage = '''
arg "<environment>" help="Environment to deploy to"
flag "--force" help="Force deployment"
'''
confirm = "Deploy to {{ usage.environment }}?{% if usage.force %} (forced){% endif %}"
run = "deploy.sh ${usage_environment}"
```

### `raw` [​](https://mise.jdx.dev/tasks/task-configuration.html\#raw)

- **Type**: `bool`
- **Default**: `false`

Connects the task directly to the shell's stdin/stdout/stderr. This is useful for tasks that need to accept input or output in a way that mise's normal task handling doesn't support.

A raw command holds an exclusive lock for as long as it runs, so mise will not run another command alongside it and you do not have to keep other tasks out of the way yourself. The lock is taken per command rather than per task, so two raw tasks can still take turns between their individual commands. If you need a whole task to run without interruption, search for or file a ticket requesting a property like `single = true`.

### `raw_args` [​](https://mise.jdx.dev/tasks/task-configuration.html\#raw-args)

- **Type**: `bool`
- **Default**: `false`

When `true`, mise does not parse arguments to the task at all — every argument is passed through verbatim to the underlying command, including `--help`/`-h`. Use this for tasks that act as a thin proxy for a tool that already has its own argument parser (e.g. `next build`, Django `manage.py`, Python scripts using `argparse`):

toml

```
[tasks.manage]
raw_args = true
run = 'python manage.py'
```

sh

```
mise run manage --help          # forwarded to manage.py, not intercepted by mise
mise run manage migrate --fake  # all flags reach manage.py unchanged
```

Without `raw_args`, mise intercepts `--help` and prints its own task help. As an ad-hoc alternative for individual invocations, you can also use `mise run task -- --help` — the `--` separator bypasses mise's usage parser for `--help`/`-h`. Arguments after that separator belong to the task, so `mise run task -- -- --help` forwards `-- --help` to the task.

### `interactive` [​](https://mise.jdx.dev/tasks/task-configuration.html\#interactive)

- **Type**: `bool`
- **Default**: `false`

Connects the task directly to the shell's stdin/stdout/stderr. Interactive tasks acquire an exclusive lock, ensuring sole access to standard I/O — while an interactive task is running, all other tasks (both interactive and non-interactive) are blocked. Non-interactive tasks can still run in parallel with each other. This is more targeted than [`raw`](https://mise.jdx.dev/tasks/task-configuration.html#raw), which takes its exclusive lock per command, and than `mise run --raw`, which goes further and forces single-threaded execution globally (by setting `jobs = 1`).

### `sources` [​](https://mise.jdx.dev/tasks/task-configuration.html\#sources)

- **Type**: `string | string[]`

Files or directories that this task uses as input. If both this and `outputs` are defined, mise skips the task when the modification time of the oldest output file is newer than the modification time of the newest source file. This is useful for tasks that are expensive to run and only need to run when their inputs change.

The task definition itself is automatically added as a source, so editing the definition also causes the task to run.

`mise watch` also uses `sources` to know which files and directories to watch.

Entries can be relative paths and/or glob patterns, e.g.: `src/**/*.rs`. Brace alternatives such as `src/**/*.{js,ts}` are supported by freshness checks, `mise watch`, and `task_source_files()`. Don't go overboard with globs that match a huge number of files, though—mise has to scan each and every one to check its timestamp.

mise-toml

```
[tasks.build]
run = "cargo build"
sources = ["Cargo.toml", "src/**/*.rs"]
outputs = ["target/debug/mycli"]
```

Running the above executes `cargo build` only if `mise.toml`, `Cargo.toml`, or any ".rs" file in the `src` directory has changed since the last build.

Both `sources` and `outputs` can use parsed [usage](https://mise.jdx.dev/tasks/task-configuration.html#usage) arguments and flags. mise resolves these templates separately for each task invocation before checking freshness or the task cache:

mise-toml

```
[tasks.compile]
usage = 'arg "<target>"'
run = "compile {{usage.target}} --output dist/{{usage.target}}"
sources = ["src/{{usage.target}}/**"]
outputs = ["dist/{{usage.target}}"]
```

Relative entries are resolved from the task directory (the task's `dir`, or the project root when it has none) and may use `..` to reach files above it, such as a `node_modules` directory shared at the root of a monorepo:

mise-toml

```
[tasks.build]
dir = "packages/web"
run = "npm run build"
sources = ["src/**/*.ts", "../../node_modules/**"]
outputs = ["dist"]
```

Use the [`task_source_files`](https://mise.jdx.dev/templates.html#task-source-files) function to iterate over a task's `sources` within its template context.

#### Excluding sources [​](https://mise.jdx.dev/tasks/task-configuration.html\#excluding-sources)

Entries in `sources` prefixed with `!` are excluded, matching the convention used by gitignore, watchexec, and rsync. Exclusions affect the freshness check, the `task_source_files` template function, and which files `mise watch` watches for changes.

mise-toml

```
[tasks.build]
sources = ["src/**/*.ts", "!src/**/*.test.ts", "!src/**/*.spec.ts", "tsconfig.json"]
run = "npm run build"
```

Entries are evaluated in order, and the latest matching entry wins. A later non-negated entry can re-include a file an earlier `!` excluded — for example, `["src/**/*.ts", "!src/**/*.test.ts", "src/keep.test.ts"]` excludes all `*.test.ts` files except `src/keep.test.ts`.

To include a literal path that begins with `!`, escape the prefix as `\!` (e.g. `"\\!important.txt"` in TOML).

#### Reusable and global inputs experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#reusable-and-global-inputs)

Use `[task_config.input_groups]` to define source patterns once and reuse them across tasks. Reference a group from `sources` with `@group:<name>`. Groups can reference other groups; undefined references and cycles are configuration errors.

Group entries are resolved relative to the config file that defines them, even when a task uses a different `dir`. Ordinary entries written directly in `sources` remain relative to the task directory.

mise-toml

```
[settings]
experimental = true

[task_config.input_groups]
toolchain = ["rust-toolchain.toml", "Cargo.lock"]
rust = ["Cargo.toml", "src/**/*.rs", "@group:toolchain"]

[tasks.build]
run = "cargo build"
sources = ["@group:rust"]
outputs = ["target/debug/mycli"]

[tasks.test]
run = "cargo test"
sources = ["@group:rust"]
outputs = []
```

`task_config.global_inputs` adds source patterns to every task in the config scope. This is useful for repository-wide configuration and lockfiles that should invalidate all cacheable tasks without being repeated in each task's `sources`. Global inputs may also reference named groups.

mise-toml

```
[task_config]
global_inputs = ["mise.toml", ".github/tool-versions", "@group:lockfiles"]

[task_config.input_groups]
lockfiles = ["Cargo.lock", "pnpm-lock.yaml"]
```

#### Dependency invalidation [​](https://mise.jdx.dev/tasks/task-configuration.html\#dependency-invalidation)

When a task depends on another task that also has `sources` defined, and the dependency runs because its sources changed, the dependent task also re-runs — even if the dependent's own sources haven't changed. This is useful for monorepo workflows where downstream tasks should be invalidated by upstream changes:

mise-toml

```
[tasks."core:build"]
run = "tsc -p packages/core"
sources = ["packages/core/src/**/*.ts"]
outputs = ["packages/core/dist/**/*.js"]

[tasks."frontend:build"]
run = "tsc -p packages/frontend"
sources = ["packages/frontend/src/**/*.ts"]
outputs = ["packages/frontend/dist/**/*.js"]
depends = ["core:build"]
```

If a file in `packages/core/src/` changes, both `core:build` and `frontend:build` run. If nothing changes, both are skipped.

Dependencies **without**`sources` (which always run) do not trigger this invalidation — otherwise `sources` on the dependent task would be effectively useless.

### `watch` [​](https://mise.jdx.dev/tasks/task-configuration.html\#watch)

- **Type**: `{ no_vcs_ignore = bool }`
- **Default**: `{ no_vcs_ignore = false }`

Options used when the task runs through [`mise watch`](https://mise.jdx.dev/cli/watch.html). By default, `mise watch` respects VCS ignore files such as `.gitignore`, even when an ignored path is listed in `sources`. Set `watch.no_vcs_ignore` for tasks that need to watch generated or intermediary files that are intentionally excluded from version control:

mise-toml

```
[tasks.generate]
run = "process generated/output.json"
sources = ["generated/output.json"]
watch = { no_vcs_ignore = true }
```

This is equivalent to passing `--no-vcs-ignore` to watchexec. Because watchexec applies ignore options to the entire watch process, watching multiple tasks together disables VCS ignores for all of them if any selected task enables this option. Keep `sources` narrowly scoped: disabling VCS ignores for broad build, distribution, or dependency directories may substantially increase filesystem scanning.

### `outputs` [​](https://mise.jdx.dev/tasks/task-configuration.html\#outputs)

- **Type**: `string | string[] | { auto = true }`
- **Default**: `{ auto = true }`

The counterpart to `sources`: the files or directories that the task creates or modifies when it runs.

Entries prefixed with `!` exclude matching outputs. As with `sources`, entries are evaluated in order, a later entry can re-include a path, and `\!` escapes a literal leading bang. Output globs also support brace alternatives such as `dist/{client,server}/**`.

mise-toml

```
[tasks.build]
run = "npm run build"
sources = ["src/**"]
outputs = ["dist", "!dist/**/*.map", "!dist/.vite/**"]
```

Excluded files do not participate in output freshness checks and are not stored in task-cache artifacts. If excluded files already exist beneath an output directory when a cached artifact is restored, mise preserves them.

`auto = true` is an alternative to specifying output files manually. In that case, mise touches an internally tracked file based on the hash of the task definition (stored in `~/.local/state/mise/task-outputs/<hash>` if you're curious). This is useful if you want `mise run` to execute when sources change but don't want to `touch` a file manually for `sources` to work.

mise-toml

```
[tasks.build]
run = "cargo build"
sources = ["Cargo.toml", "src/**/*.rs"]
outputs = { auto = true } # this is the default when sources is defined
```

### `cache`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#cache)

- **Type**: `{ enabled = bool, audit = bool, env = string[], command_inputs = string[] }`
- **Default**: `{ enabled = false, audit = false, env = [], command_inputs = [] }`

Cache a successful task result by its declared inputs. A cache hit restores explicit outputs and replays captured logs. Requires experimental features, matching sources, and explicit output paths or `outputs = []`.

See [Task caching](https://mise.jdx.dev/tasks/caching.html) for setup, input declarations, debugging, remote service configuration, and cache retention. `outputs = { auto = true }` supports freshness checks but cannot store artifacts.

#### External dependencies and lockfiles [​](https://mise.jdx.dev/tasks/task-configuration.html\#external-dependencies-and-lockfiles)

See [external dependencies and lockfiles](https://mise.jdx.dev/tasks/caching.html#external-dependencies-and-lockfiles).

#### Per-run cache access [​](https://mise.jdx.dev/tasks/task-configuration.html\#per-run-cache-access)

See [per-run cache access](https://mise.jdx.dev/tasks/caching.html#per-run-cache-access).

#### Remote cache and sensitive data [​](https://mise.jdx.dev/tasks/task-configuration.html\#remote-cache-and-sensitive-data)

See [remote cache and sensitive data](https://mise.jdx.dev/tasks/caching.html#remote-cache-and-sensitive-data).

#### Cache correctness and deterministic tasks [​](https://mise.jdx.dev/tasks/task-configuration.html\#cache-correctness-and-deterministic-tasks)

See [cache correctness and deterministic tasks](https://mise.jdx.dev/tasks/caching.html#cache-correctness-and-deterministic-tasks).

### `rust_cache`deprecated [​](https://mise.jdx.dev/tasks/task-configuration.html\#rust-cache)

- **Type**: `boolean | table`
- **Default**: `false`

This setting no longer enables Rust compiler action caching. mise accepts it temporarily as a deprecated no-op so existing task configurations continue to run. Enabled values print a migration warning; disabled values are silent.

Use [mbx](https://mr-boxington.jdx.dev/getting-started) for Rust action caching instead. Install it globally with `mise use -g mr-boxington`, or add it to the project tools. To keep existing task commands unchanged, configure mise's [`cargo` command wrapper](https://mise.jdx.dev/dev-tools/shims.html#command-wrappers):

mise-toml

```
[tools]
mr-boxington = "latest"

[wrappers.cargo]
command = "mbx"
env = { MBX_CARGO_SHIM_MODE = "1" }

[tasks.build]
run = "cargo build"
```

Run `mise reshim` after adding the wrapper, then remove `rust_cache`. The compatibility field is scheduled for removal in mise 2027.8.14.

### `shell` [​](https://mise.jdx.dev/tasks/task-configuration.html\#shell)

- **Type**: `string`
- **Default**: [`task_config.shell`](https://mise.jdx.dev/tasks/task-configuration.html#task_config.shell) when set (config-scoped); otherwise [`unix_default_inline_shell_args`](https://mise.jdx.dev/configuration/settings.html#unix_default_inline_shell_args)/ [`windows_default_inline_shell_args`](https://mise.jdx.dev/configuration/settings.html#windows_default_inline_shell_args) (global-only).
- **Note**: Only applies to toml-tasks.

The shell used to run the task. This is useful if you want a task to use a shell other than the default, such as `fish`, `zsh`, or `pwsh`. Generally, though, a [shebang](https://mise.jdx.dev/tasks/toml-tasks.html#shell-shebang) is recommended instead because it lets IDEs with mise support show syntax highlighting and linting for the script.

When the shell is PowerShell (`pwsh` or `powershell`), mise passes `-NoProfile` so your PowerShell profile is not loaded, matching the non-interactive behavior of `sh -c`/`zsh -c`. This prevents profiles that mutate `PATH` (for example, a mise activation snippet) from shadowing a task's own installed tools. Set [`windows_powershell_no_profile`](https://mise.jdx.dev/configuration/settings.html#windows_powershell_no_profile) to `false` if your tasks depend on side effects from your profile.

mise-toml

```
[tasks.hello]
run = '''
#!/usr/bin/env node
console.log('hello world')
'''
```

### `timeout` [​](https://mise.jdx.dev/tasks/task-configuration.html\#timeout)

- **Type**: `string`
- **Default**: unset

Maximum execution time for this task. The value accepts durations such as `30s`, `5m`, or `1h` and supports Tera templates. The task fails if it does not complete within the configured duration.

mise-toml

```
[tasks.integration-test]
run = "./scripts/integration-test.sh"
timeout = "10m"
```

This limits the individual task. Use [`mise run --timeout`](https://mise.jdx.dev/cli/run.html) or the [`task.timeout`](https://mise.jdx.dev/configuration/settings.html#task.timeout) setting to limit the entire task run. When both a global timeout and a per-task timeout are set, the shorter of the two wins: a per-task timeout cannot extend beyond the global timeout. The `--timeout` CLI flag overrides the global setting.

### `deny_all` [​](https://mise.jdx.dev/tasks/task-configuration.html\#deny-all)

- **Type**: `bool`
- **Default**: `false`

Block filesystem reads, filesystem writes, network access, and environment inheritance for this task. Specific `allow_*` properties can add exceptions.

mise-toml

```
[tasks.lint]
run = "eslint ."
deny_all = true
allow_read = ["."]
allow_write = ["./node_modules/.cache"]
allow_env = ["NODE_*"]
```

Sandbox support and implicit system access vary by platform. See [Sandboxing](https://mise.jdx.dev/sandboxing.html) for the complete behavior and limitations.

### `deny_read` [​](https://mise.jdx.dev/tasks/task-configuration.html\#deny-read)

- **Type**: `bool`
- **Default**: `false`

Block filesystem reads except for the system and mise paths required to execute the task. Use `allow_read` to add task-specific exceptions.

### `deny_write` [​](https://mise.jdx.dev/tasks/task-configuration.html\#deny-write)

- **Type**: `bool`
- **Default**: `false`

Block filesystem writes except for implicitly writable system paths such as the temporary directory. Use `allow_write` to add task-specific exceptions.

### `deny_net` [​](https://mise.jdx.dev/tasks/task-configuration.html\#deny-net)

- **Type**: `bool`
- **Default**: `false`

Block network access for this task. Use `allow_net` for host-specific exceptions on platforms that support them.

### `deny_env` [​](https://mise.jdx.dev/tasks/task-configuration.html\#deny-env)

- **Type**: `bool`
- **Default**: `false`

Block inherited environment variables except for essential variables such as `PATH`, `HOME`, `USER`, `SHELL`, `TERM`, and `LANG`. Use `allow_env` or `pass_through_env` to preserve additional variables.

### `allow_read` [​](https://mise.jdx.dev/tasks/task-configuration.html\#allow-read)

- **Type**: `string[]`
- **Default**: `[]`

Allow reads from the listed paths and block other filesystem reads. Relative paths are resolved from the task's effective working directory.

### `allow_write` [​](https://mise.jdx.dev/tasks/task-configuration.html\#allow-write)

- **Type**: `string[]`
- **Default**: `[]`

Allow writes to the listed paths and block other filesystem writes. Allowed write paths are also readable. Relative paths are resolved from the task's effective working directory.

### `allow_net` [​](https://mise.jdx.dev/tasks/task-configuration.html\#allow-net)

- **Type**: `string[]`
- **Default**: `[]`

Allow network access to the listed hosts and block other network access. Per-host network filtering is platform-dependent; see [Platform Support](https://mise.jdx.dev/sandboxing.html#platform-support).

### `allow_env` [​](https://mise.jdx.dev/tasks/task-configuration.html\#allow-env)

- **Type**: `string[]`
- **Default**: `[]`

Allow the listed environment variable names and block other inherited environment variables. Entries support `*` wildcards, such as `MYAPP_*`.

### `pass_through_env`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#pass-through-env)

- **Type**: `string[]`
- **Default**: `[]`

Preserve the listed ambient environment variables when environment inheritance is denied without including their values in the task cache key. Entries support `*` wildcards. This property does not enable environment sandboxing by itself and has no effect unless environment sandboxing is active, including through `allow_env`, `deny_env`, `deny_all`, or an equivalent CLI or global sandbox option.

Use `pass_through_env` for values such as short-lived credentials that must not affect the cache key. Do not use it for values that affect generated outputs or logs. Use `cache.env` instead when changes to a variable should invalidate the task cache.

### `quiet` [​](https://mise.jdx.dev/tasks/task-configuration.html\#quiet)

- **Type**: `bool`
- **Default**: `false`

Suppress mise's own output for the task, such as the command being run, e.g.: `[build] $ cargo build`. When this is set, mise shows nothing other than what the script itself outputs. To hide the task's own output as well, use [`silent`](https://mise.jdx.dev/tasks/task-configuration.html#silent).

`quiet` is a _verbosity_ setting and is independent of the [`output`](https://mise.jdx.dev/tasks/task-configuration.html#output) _style_: it does not force un-prefixed output, so `output = "prefix"` together with `quiet = true` keeps the task-name prefixes while hiding mise's own messages.

### `silent` [​](https://mise.jdx.dev/tasks/task-configuration.html\#silent)

- **Type**: `bool | "stdout" | "stderr"`
- **Default**: `false`

Suppress all output from the task. If set to `"stdout"` or `"stderr"`, only that stream is suppressed.

### `output` [​](https://mise.jdx.dev/tasks/task-configuration.html\#output)

- **Type**: `string`
- **Default**: unset (inherits the global [`task.output`](https://mise.jdx.dev/configuration/settings.html#task.output) setting)

Output _style_ for this task: `prefix`, `interleave`, `keep-order`, `replacing`, `timed`, `quiet`, or `silent`. This is the per-task equivalent of the global `task.output` setting and is orthogonal to the [`quiet`](https://mise.jdx.dev/tasks/task-configuration.html#quiet)/ [`silent`](https://mise.jdx.dev/tasks/task-configuration.html#silent) verbosity fields, so styles and quietness combine freely (e.g. `output = "prefix"` \+ `quiet = true`). The `quiet`/`silent` _values_ are kept for backwards compatibility and bundle a style with that verbosity.

Deprecated

The `quiet` output value is deprecated. Warnings begin in mise `2026.9.3`, and support will be removed in `2027.9.3`. Use `output = "interleave"` with `quiet = true` instead. For a global task default, use `task.output = "interleave"` with `task.quiet = true` under `[settings]`.

### `usage` [​](https://mise.jdx.dev/tasks/task-configuration.html\#usage)

- **Type**: `string`

TIP

For comprehensive information about task arguments and the usage field, see the dedicated [Task Arguments](https://mise.jdx.dev/tasks/task-arguments.html) page.

More advanced usage specs can be added to the task's `usage` field. This only applies to toml-tasks.

mise-toml

```
[tasks.test]
usage = '''
arg "<file>" help="The file to test" default="src/main.rs"
'''
run = 'cargo test ${usage_file?}'
```

#### Environment Variable Support for Args and Flags [​](https://mise.jdx.dev/tasks/task-configuration.html\#environment-variable-support-for-args-and-flags)

Both args and flags in usage specs can specify an environment variable as an alternative source for their value. This lets task arguments be provided through environment variables when they are not specified on the command line.

The precedence order is:

1. CLI arguments/flags (highest priority)
2. Environment variables (middle priority)
3. Default values (lowest priority)

**For positional arguments:**

mise-toml

```
[tasks.deploy]
usage = '''
arg "<environment>" env="DEPLOY_ENV" help="Target environment" default="staging"
arg "<region>" env="AWS_REGION" help="AWS region" default="us-east-1"
'''

run = '''
echo "Deploying to ${usage_environment?} in ${usage_region?}"
'''
```

Usage examples:

bash

```
# Using CLI args (highest priority)
mise run deploy production us-west-2

# Using environment variables
export DEPLOY_ENV=production
export AWS_REGION=us-west-2
mise run deploy

# Using defaults (lowest priority)
mise run deploy  # deploys to staging in us-east-1

# CLI overrides environment variable
export DEPLOY_ENV=staging
mise run deploy production  # deploys to production
```

**For flags:**

mise-toml

```
[tasks.build]
usage = '''
flag "-p --profile <profile>" env="BUILD_PROFILE" help="Build profile" default="dev"
flag "-v --verbose" env="VERBOSE" help="Verbose output"
'''

run = '''
echo "Building with profile: ${usage_profile?}"
echo "Verbose: ${usage_verbose:-false}"
'''
```

Usage examples:

bash

```
# Using CLI flags
mise run build --profile release --verbose

# Using environment variables
export BUILD_PROFILE=release
export VERBOSE=true
mise run build

# Mixed usage - env var provides one, CLI provides another
export BUILD_PROFILE=release
mise run build --verbose
```

**File tasks** (tasks defined as executable files in `mise-tasks/` or `.mise/tasks/`) also support the `env` attribute:

bash

```
#!/usr/bin/env bash
#USAGE arg "<input>" env="INPUT_FILE" help="Input file to process"
#USAGE flag "-o --output <file>" env="OUTPUT_FILE" help="Output file" default="out.txt"

echo "Processing ${usage_input?} -> ${usage_output?}"
```

**Required arguments:**

Environment variables can satisfy required argument checks. If an argument is marked as required (using angle brackets `<arg>`), providing its value through the environment variable specified in the `env` attribute fulfills that requirement:

mise-toml

```
[tasks.deploy]
usage = '''
arg "<api-key>" env="API_KEY" help="API key for deployment"
'''
run = 'deploy --api-key ${usage_api_key?}'
```

bash

```
# This will fail - no API_KEY provided
mise run deploy

# This succeeds - API_KEY provided via environment
export API_KEY=secret123
mise run deploy

# This also succeeds - provided via CLI
mise run deploy secret123
```

## Vars [​](https://mise.jdx.dev/tasks/task-configuration.html\#vars)

Top-level [configuration vars](https://mise.jdx.dev/configuration/vars.html) are available when rendering TOML tasks. Tasks can also define task-local vars that override config vars for that task:

mise-toml

```
[tasks.test]
vars = { e2e_args = "--headed" }
run = './scripts/test-e2e.sh {{vars.e2e_args}}'
```

## `[task_config]` options [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-options)

Options available in the top-level `mise.toml``[task_config]` section. These apply to all tasks that are included by that config file or share the same root directory, e.g.: `~/src/myproject/mise.toml`'s `[task_config]` applies to file tasks like `~/src/myproject/mise-tasks/mytask`. Set `cascade = true` to also apply the section to tasks owned by descendant config roots.

### `task_config.cascade` [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-cascade)

Cascade this config's `[task_config]` values to descendant config roots. Descendant values override individual inherited fields. A descendant can set `cascade = false` to stop inheriting the section.

toml

```
[task_config]
cascade = true
shell = "bash -c"
```

This applies to `dir`, `shell`, `cache`, `rust_cache`, `global_inputs`, `input_groups`, and `includes`. Inherited include paths and task inputs remain relative to the config root where they were defined.

A descendant's non-empty `global_inputs` replaces the inherited value. Descendant `input_groups` merge with inherited groups by name; the nearest definition wins when the same name appears more than once. This also applies to group references in inherited `global_inputs`. Each group remains relative to the config root where it was defined.

### `task_config.dir` [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-dir)

Change the default directory tasks are run from.

toml

```
[task_config]
dir = "{{cwd}}"
```

### `task_config.shell` [​](https://mise.jdx.dev/tasks/task-configuration.html\#task_config.shell)

Set the default shell for tasks in this config scope. A task's explicit `shell` setting takes precedence, including a `shell` inherited from a task template. With `task_config.cascade = true`, descendant config roots inherit this default and may override it with their own `task_config.shell`.

toml

```
[task_config]
shell = "bash -c"
```

Unlike the global-only [`unix_default_inline_shell_args`](https://mise.jdx.dev/configuration/settings.html#unix_default_inline_shell_args) and [`windows_default_inline_shell_args`](https://mise.jdx.dev/configuration/settings.html#windows_default_inline_shell_args) settings, this default is scoped to project tasks and cannot change the interpreter used by hooks, tool installation, or tasks from another config root.

### `task_config.cache`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-cache)

Sets the default artifact-cache configuration for tasks in this config scope. The default is only inherited by cache-eligible tasks with sources and either explicit output paths or `outputs = []`. Task-local and task-template cache configuration takes precedence, including `cache = { enabled = false }`.

toml

```
[task_config.cache]
enabled = true
env = ["NODE_ENV", "CI"]
command_inputs = ["node --version"]
```

### `task_config.rust_cache`deprecated [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-rust-cache)

This deprecated compatibility setting no longer enables Rust action caching. An effective enabled value warns once while tasks continue normally. Remove it and run Rust build commands through [mbx](https://mr-boxington.jdx.dev/getting-started) instead. The [`wrappers.cargo` configuration](https://mise.jdx.dev/lang/rust.html#share-cargo-builds-with-mr-boxington) lets existing tasks keep invoking `cargo` without modification.

toml

```
[task_config]
rust_cache = true
```

### `task_config.global_env`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-global-env)

Adds ambient environment variable names to the cache key of every cache-enabled task in the config scope. These values compose with task-local `cache.env` rather than acting as defaults.

toml

```
[task_config]
global_env = ["CI", "NODE_ENV"]
```

### `task_config.global_pass_through_env`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-global-pass-through-env)

Preserves ambient environment variables when environment inheritance is denied, without adding their values to task cache keys.

toml

```
[task_config]
global_pass_through_env = ["CI_JOB_TOKEN"]
```

### `task_config.global_inputs`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-global-inputs)

Adds config-root-relative source paths and glob patterns to every task in this config scope. Entries may reference a named input group with `@group:<name>`.

toml

```
[task_config]
global_inputs = ["mise.toml", "@group:lockfiles"]
```

### `task_config.input_groups`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-config-input-groups)

Defines reusable, config-root-relative source groups. Tasks reference them from `sources` with `@group:<name>`. Groups may reference other groups.

toml

```
[task_config.input_groups]
lockfiles = ["Cargo.lock", "pnpm-lock.yaml"]
rust = ["Cargo.toml", "src/**/*.rs", "@group:lockfiles"]
```

### `task_config.includes` [​](https://mise.jdx.dev/tasks/task-configuration.html\#task_config.includes)

Set the toml files and file-task directories mise should search when looking for tasks.

toml

```
[task_config]
includes = [\
    "tasks.toml", # a task toml file\
    "mytasks"     # a directory containing file tasks\
]
```

When `task_config.includes` is set, it replaces the default file-task directories for that config scope instead of adding to them. Include entries are rendered as Tera templates, so they can reference values such as `config_root`, `env`, and resolved `vars`.

The default file-task directories are:

- `mise-tasks`
- `.mise-tasks`
- `.mise/tasks`
- `.config/mise/tasks`
- `mise/tasks`

If you want to keep the defaults and add another directory, include the defaults explicitly:

toml

```
[task_config]
includes = [\
    "mise-tasks",\
    ".mise-tasks",\
    ".mise/tasks",\
    ".config/mise/tasks",\
    "mise/tasks",\
    "mytasks",\
    "tasks.toml",\
]
```

For local and monorepo task discovery, mise uses the nearest config file that defines `task_config.includes`. When the parent has `task_config.cascade = true`, its includes are inherited until a child defines its own. A child config's `includes` replaces both the defaults and any inherited `includes` for that directory. User-global config files form one config scope, as do system config files. Within each scope, the highest-precedence config that defines `task_config.includes` replaces lower-precedence includes and the default directories. A [conf.d folder](https://mise.jdx.dev/configuration.html#conf-d-folders) is its own root in either case: its `includes` resolve inside the folder and replace only the folder's own defaults. User-global and system scopes remain independent. User-global tasks replace same-named system tasks without inheriting system task metadata, while system tasks with other names remain available.

Entries are evaluated in order, and when more than one include defines a task with the same name the **last** entry in the list wins. This applies uniformly to directory, toml-file, and `git::` includes, so to override a task coming from a `git::` include with a local one, list the local directory after the `git::` entry (see the example below).

toml

```
[task_config]
includes = [\
    "git::https://github.com/myorg/shared-tasks.git//tasks", # remote task…\
    ".mise/tasks",                                           # …is overridden by the local one with the same name\
]
```

#### Included TOML files [​](https://mise.jdx.dev/tasks/task-configuration.html\#included-toml-files)

Included task toml files have a different format than `mise.toml`: they are simply a list of tasks. The file uses the same format as the `[tasks]` section of `mise.toml` but without the `[tasks]` prefix:

tasks.toml

mise-toml

```
task1 = "echo task1"
task2 = "echo task2"
task3 = "echo task3"

[task4]
run = "echo task4"
vars = { target = "linux" }
```

For auto-completion and validation in included toml task files, use the following JSON schema: [https://mise.jdx.dev/schema/mise-task.json](https://mise.jdx.dev/schema/mise-task.json)

#### Configuring file tasks from TOML [​](https://mise.jdx.dev/tasks/task-configuration.html\#configuring-file-tasks-from-toml)

Use a `[tasks.<name>]` block to configure an executable file task. A block without `run`, `run_windows`, or `file` adds metadata and keeps the script as its command. Adding one of those fields replaces the script's command, subject to [config precedence](https://mise.jdx.dev/tasks/task-configuration.html#file-task-config-precedence).

##### Add metadata and dependencies [​](https://mise.jdx.dev/tasks/task-configuration.html\#add-metadata-and-dependencies)

For `mise-tasks/hello.sh`, use either `[tasks.hello]` or `[tasks."hello.sh"]`:

mise.toml

toml

```
[tasks.hello]
description = "Say hello after linting"
env = { GREETING = "hi" }
depends = ["lint"]
```

`mise run hello` runs `lint` and then the script with `GREETING=hi`. `mise tasks ls` shows the description. The script's full task name is `hello.sh`; `mise run` also accepts `hello` without the extension.

The full name selects one script. The name without the extension selects all scripts with that name, unless a task already has that exact name. For example, if both `hello.sh` and `hello.js` exist, `[tasks.hello]` configures both, while `[tasks."hello.sh"]` configures only `hello.sh`.

##### Replace a script's command [​](https://mise.jdx.dev/tasks/task-configuration.html\#replace-a-script-s-command)

Set `run`, `run_windows`, or `file` to replace a matching file task:

mise.toml

toml

```
[tasks.hello]
run = "echo hi"
```

`mise run hello` now runs `echo hi`. The discovered `hello.sh` no longer exists as a separate task, so `mise run hello.sh` is no longer available. If `hello.js` also exists, this block replaces both scripts with one task named `hello`.

To replace only `hello.sh`, use its full name:

mise.toml

toml

```
[tasks."hello.sh"]
run = "echo hi"
```

Here, `mise run hello.sh` runs `echo hi`, and `hello.js` remains a separate task. To keep both the original script and a new command available, give the command a different task name.

##### File task config precedence [​](https://mise.jdx.dev/tasks/task-configuration.html\#file-task-config-precedence)

A command replaces a script only when its block comes from the config whose [`task_config.includes`](https://mise.jdx.dev/tasks/task-configuration.html#task_config.includes) selected the script's directory, or from a higher-precedence config. A lower-precedence block can add metadata, but its command is ignored and the script still runs. This applies to both full names and names without extensions.

When no config sets `task_config.includes`, mise discovers scripts in the default directories. In that case, a command from any config in the chain can replace a matching script.

While a script remains the task's command, only the highest-precedence TOML block that matches it supplies metadata. Lower-precedence blocks add nothing, including `env` and `alias`. For example, `[tasks.hello]` in `mise.local.toml` takes precedence over `[tasks."hello.sh"]` in `mise.toml`; their metadata is not combined.

Once a TOML command replaces the script, [layered task definitions](https://mise.jdx.dev/tasks/task-configuration.html#layered-task-definitions) apply. Higher-precedence metadata blocks can configure the replacement using either name. For example, `[tasks."hello.sh"]` in `mise.local.toml` can add a description to `[tasks.hello] run = "echo hi"` in `mise.toml`. Blocks below the selected command contribute nothing. If both names declare commands, the higher-precedence command wins.

##### Windows script pairs [​](https://mise.jdx.dev/tasks/task-configuration.html\#windows-script-pairs)

On Windows, mise selects the [Windows-native sibling](https://mise.jdx.dev/tasks/file-tasks.html#windows) from a pair such as `build.sh` and `build.ps1`, and names the task `build`. Use `[tasks.build]` to configure or replace that task. A block named `[tasks."build.ps1"]` defines a separate task.

#### Layered task definitions [​](https://mise.jdx.dev/tasks/task-configuration.html\#layered-task-definitions)

An inline `[tasks.<name>]` block without `run`, `run_windows`, or `file` adds metadata to a task of the same name from a lower-precedence config. It can add a description, environment variables, or dependencies without repeating the command.

mise.tomlmise.local.toml

toml

```
[tasks.check]
depends = ["lint", "test"]
```

toml

```
[tasks.check]
description = "Run the project checks"
```

Here, `mise run check` still runs `lint` and `test`. A dependency group can receive metadata even when it has no command of its own.

When a definition with `run`, `run_windows`, or `file` exists, it provides the command. Blocks above the highest-precedence command definition add metadata in precedence order, including any `depends` they declare. Definitions below that command do not contribute. When no definition has a command, the highest-precedence dependency group provides the base instead.

For a task from an [included TOML file](https://mise.jdx.dev/tasks/task-configuration.html#included-toml-files), an inline command replaces the included task, while an inline block without a command adds metadata. The inline block must come from the config that selected the include or a higher-precedence config. This is also required when [replacing a file task's command](https://mise.jdx.dev/tasks/task-configuration.html#file-task-config-precedence).

#### Remote Git Includes experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#remote-git-includes)

You can include directories or individual task toml files from git repositories using the `git::` URL syntax:

sshhttps

mise-toml

```
[task_config]
includes = [\
    "git::ssh://git@github.com/myorg/shared-tasks.git//tasks?ref=v1.0.0",\
    "git::ssh://git@github.com/myorg/shared-tasks.git//tasks/release.toml?ref=v1.0.0",\
]
```

mise-toml

```
[task_config]
includes = [\
    "git::https://github.com/myorg/shared-tasks.git//tasks?ref=main",\
    "git::https://github.com/myorg/shared-tasks.git//tasks/release.toml?ref=main",\
]
```

URL format: `git::<protocol>://<url>//<path>?ref=<ref>`

Required fields:

- `protocol`: The git protocol (ssh or https).
- `url`: The git repository URL.
- `path`: The path to a directory or a `.toml` task file in the repository.

Optional fields:

- `ref`: The git reference (branch, tag, commit). Defaults to the repository's default branch.

When `path` points at a directory, mise loads both executable file tasks and any `.toml` task files inside that directory. When `path` points at a single `.toml` file, only that file is loaded.

Included `.toml` files use the [task toml file format](https://mise.jdx.dev/tasks/task-configuration.html#task_config.includes) (the keys are task names — there is no `[tasks.…]` prefix). The repository is cloned and cached in `MISE_CACHE_DIR/remote-git-tasks-cache`. Tasks from the include are loaded as if they were local. You can disable caching with `MISE_TASK_REMOTE_NO_CACHE=true` or the `--no-cache` flag.

### `task_config.excludes` [​](https://mise.jdx.dev/tasks/task-configuration.html\#task_config.excludes)

Set paths or glob patterns to exclude from file-task discovery. Relative entries resolve from the config root and may exclude a file, an entire directory, or files matched by a glob:

toml

```
[task_config]
excludes = [\
    ".mise/tasks/python/pyproject.toml",\
    ".mise/tasks/generated",\
    ".mise/tasks/**/fixtures/*.toml",\
]
```

The closest config that defines `task_config.excludes` replaces inherited exclusions. Set it to an empty array to clear exclusions inherited through `task_config.cascade = true`. Exclusions apply to both the default task directories and paths selected by `task_config.includes`.

Task directories are searched recursively. Executable files are loaded as file tasks, and every `.toml` file that is not a mise configuration file is loaded using the [included task TOML format](https://mise.jdx.dev/tasks/task-configuration.html#task_config.includes). Use `task_config.excludes` when other TOML files, such as `pyproject.toml` or `Cargo.toml`, must live inside a task directory.

## Monorepo Support [​](https://mise.jdx.dev/tasks/task-configuration.html\#monorepo-support)

mise supports monorepo-style task organization with target path syntax. Enable it by setting `monorepo_root = true` in your root `mise.toml`.

For complete documentation on monorepo tasks including:

- Task path syntax and wildcards
- Tool layering from parent configs
- Performance tuning
- Best practices and troubleshooting

See the dedicated [Monorepo Tasks](https://mise.jdx.dev/tasks/monorepo.html) documentation.

## `redactions`experimental [​](https://mise.jdx.dev/tasks/task-configuration.html\#redactions)

- **Type**: `string[]`

Redactions hide sensitive information from task output. This is useful for API keys, passwords, and other secrets that you don't want to leak accidentally in logs or other output.

A list of environment variables to redact from the output.

toml

```
redactions = ["API_KEY", "PASSWORD"]

[env]
API_KEY = "s3cr3t"

[tasks.show-key]
run = 'echo "key: $API_KEY"'
```

Running `mise run show-key` will output `key: [redacted]` instead of the value of `API_KEY`.

You can also specify these as a glob pattern, e.g.: `redactions = ["SECRETS_*"]`.

## `[vars]` options [​](https://mise.jdx.dev/tasks/task-configuration.html\#vars-options)

See [Variables](https://mise.jdx.dev/configuration/vars.html).

## Task Configuration Settings [​](https://mise.jdx.dev/tasks/task-configuration.html\#task-configuration-settings)

The following settings control task behavior. Set them under `[settings]` in `~/.config/mise/config.toml`. Settings that are not marked global-only can also be set per project in `mise.toml`:

## `task`

#### `task.auto_infer`

- Type: `string[]`
- Env: `MISE_TASK_AUTO_INFER`
- Default: `[]`

List the workspace provider languages whose ecosystem tasks mise should import. For example,
`["node"]` imports scripts from Node workspace `package.json` files. Inferred tasks use stable
provider-scoped names and monorepo path aliases. Task inference is opt-in because ecosystem commands
may overlap with explicit mise tasks.

#### `task.cache.audit_report`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_AUDIT_REPORT`
- Default: `None`

Write the complete report produced by [`cache.audit`](https://mise.jdx.dev/tasks/task-configuration.html#cache) to this
file as JSON Lines, one `{"task", "kind", "path"}` object per undeclared path. Console warnings
remain limited to the first 20 paths per task.

Truncation happens once per `mise` invocation: the first audited task in each invocation truncates
the file and later audited tasks in that invocation append to it, so one file holds that run's
report for every audited task and a later run replaces it rather than adding to it. Cached tasks do
not execute and write nothing, leaving an earlier report in place. Relative paths resolve against
mise's working directory.

#### `task.cache.remote_mode`

- Type: `string`
- Env: `MISE_TASK_CACHE_REMOTE_MODE`
- Default: `read-write`
- Choices:
  - `read-write`
  - `read-only`
  - `write-only`

Control access to the remote cache used by task result and action caching:

- `read-write` reads remote misses and uploads successful local results.
- `read-only` reads remote misses without uploading results.
- `write-only` uploads results without reading remote entries.

The per-run `--task-cache=local-only` mode disables remote task-result access. Action-cache adapters
may further restrict this mode. Remote writes are allowed only from protected-branch push pipelines
in GitHub Actions and GitLab CI; pull requests, unprotected branches, other CI systems, and local
developer runs are read-only. The server must independently enforce the same policy from verified
OIDC claims.

#### `task.cache.remote_namespace`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_REMOTE_NAMESPACE`
- Default: `None`

Opaque repository or organization namespace used to isolate remote build-cache entries. This
setting is required when [`task.cache.remote_url`](https://mise.jdx.dev/configuration/settings.html#task.cache.remote_url) is configured.

#### `task.cache.remote_oidc_audience`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_REMOTE_OIDC_AUDIENCE`
- Default: `None`

Acquire a short-lived OIDC token for this audience when running in a supported workload identity
environment. GitHub Actions is supported through its OIDC request environment variables. This
setting is global-only so shared project configuration cannot choose a token audience.

#### `task.cache.remote_token`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_REMOTE_TOKEN`
- Default: `None`

Authenticate remote build-cache requests with an HTTP `Authorization: Bearer` header. Prefer the
`MISE_TASK_CACHE_REMOTE_TOKEN` environment variable or a protected global configuration file; this
setting is global-only so shared project configuration cannot supply credentials.

#### `task.cache.remote_token_file`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_REMOTE_TOKEN_FILE`
- Default: `None`

Read the remote build-cache bearer token from this file before each request. This supports rotating
credentials such as Kubernetes projected service account tokens. This setting is global-only so
shared project configuration cannot select a credential file.

#### `task.cache.remote_url`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_REMOTE_URL`
- Default: `None`

Enable the versioned HTTP remote build-cache protocol at this base URL. Remote access also requires
[`task.cache.remote_namespace`](https://mise.jdx.dev/configuration/settings.html#task.cache.remote_namespace). Leave unset to use only local caches.

#### `task.cache.stats_report`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_STATS_REPORT`
- Default: `None`

Write a versioned JSON report describing Rust action-cache activity, transfer volume, restored
outputs, and phase timings. Timing values use nanoseconds. Concurrent phase timings are cumulative
work time and can exceed the end-to-end `session_duration_ns`; `prefetch_duration_ns` is the sum of
wall-clock durations for each task prefetch run.

This is intended for CI qualification and benchmarking. Relative paths resolve against mise's
working directory. The report is replaced atomically after each `mise run` invocation that creates
an action-cache session.

#### `task.cache_dir`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_DIR`
- Default: `None`

Store task output cache artifacts in this directory instead of
`MISE_CACHE_DIR/task-artifacts`. mise stores the current artifact format in a
versioned subdirectory and includes custom locations in `mise cache clear` and
manual and automatic cache pruning.

#### `task.cache_max_age`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_MAX_AGE`
- Default: `None`

Remove task output cache entries that have not been accessed within this duration after a new entry
is stored. This limit applies only to the task output cache and is independent of
[`cache_prune_age`](https://mise.jdx.dev/configuration/settings.html#cache_prune_age). Set to `0s` or leave unset to disable the age limit.

#### `task.cache_max_size`

- Type: `string`(optional)
- Env: `MISE_TASK_CACHE_MAX_SIZE`
- Default: `None`

Keep the task output cache at or below this size by removing least-recently-accessed entries after a
new entry is stored. Values accept SI or IEC units such as `500MB` or `2GiB`. Set to `0` or leave
unset to disable the size limit.

#### `task.disable_paths`

- Type: `string[]`
- Env: `MISE_TASK_DISABLE_PATHS`
- Default: `[]`

Paths that mise will not look for tasks in.

Relative paths set in a config file are resolved from that file's config root. Relative paths from
the environment are resolved from the invocation's working directory.

Paths are separated by the OS path separator when using the environment variable,
`mise settings set`, or `mise settings add` (`:` on Unix, `;` on Windows).

#### `task.disable_spec_from_run_scripts`

- Type: `boolean`
- Env: `MISE_TASK_DISABLE_SPEC_FROM_RUN_SCRIPTS`
- Default: `false`

When enabled, `arg()`, `option()`, and `flag()` Tera functions in run scripts will not contribute
to the task's usage spec—only the explicit `usage` field is used.

This is useful for:

- Skipping the extra template pass over run scripts (performance)
- Avoiding two-pass parsing quirks where template functions return empty strings during spec collection
- Early opt-out before Tera template arguments are removed in 2026.11.0

#### `task.monorepo_depth`

- Type: `integer`
- Env: `MISE_TASK_MONOREPO_DEPTH`
- Default: `5`

When using monorepo mode (monorepo\_root = true), this controls how deep
mise will search for task files in subdirectories.

**Depth levels:**

- 1 = immediate children only (monorepo\_root/projects/)
- 2 = grandchildren (monorepo\_root/projects/frontend/)
- 5 = default (5 levels deep)

**Performance tip:** Reduce this value if you have a very large monorepo and notice
slow task discovery. For example, if your projects are all at `projects/*`, set to 2.

**Example:**

```toml
[settings]
task.monorepo_depth = 3  # Only search 3 levels deep
```

Or via environment variable:

```bash
export MISE_TASK_MONOREPO_DEPTH=3
```

#### `task.monorepo_exclude_dirs`

- Type: `string[]`
- Env: `MISE_TASK_MONOREPO_EXCLUDE_DIRS`(comma separated)
- Default: `[]`

If empty (default), uses default exclusions: node\_modules, target, dist, build.
If you specify any patterns, ONLY those patterns will be excluded (defaults are NOT included).
For example, setting to \[".temp", "vendor"\] will exclude only those two directories.

#### `task.monorepo_respect_gitignore`

- Type: `boolean`
- Env: `MISE_TASK_MONOREPO_RESPECT_GITIGNORE`
- Default: `true`

When enabled, mise will skip directories that are ignored by .gitignore files
when discovering tasks in a monorepo.

#### `task.output`

- Type: `string`(optional)
- Env: `MISE_TASK_OUTPUT`
- Default: `None`
- Choices:
  - `prefix` – (default if jobs > 1) print by line with the prefix of the task name
  - `interleave` – (default if jobs == 1 or all tasks run sequentially) print output as it comes in
  - `keep-order` – stream one task's output live while buffering others, printing in definition order as tasks complete
  - `replacing` – replace stdout each time a line is printed-this uses similar logic as `mise install`
  - `timed` – only show stdout lines that take longer than 1s to complete
  - `quiet` – deprecated: interleave task output and suppress mise's own messages. Use `interleave` with the appropriate quiet setting or flag.
  - `silent` – print nothing from tasks or mise (nulls stdout and stderr)

Change output style when executing tasks. This controls the output of `mise run`.

This is the output _style_ axis. Verbosity is a separate axis controlled by
`task.quiet`/`silent` (as settings, `--quiet`/`--silent` flags, or per-task
fields), so a style can be combined with quietness — e.g. `output = "prefix"`
together with `task.quiet = true` keeps the task-name prefixes while suppressing
mise's own task messages. The `quiet` and `silent` _values_ below are kept for
backwards compatibility and bundle a style with that verbosity.

::: warning Deprecated
The `quiet` output value is deprecated. Warnings begin in mise `2026.9.3`, and
support will be removed in `2027.9.3`. For a global task default, use
`task.output = "interleave"` with `task.quiet = true`. For an individual task,
use `output = "interleave"` with `quiet = true`. On the command line, use
`--output interleave --quiet`.
:::

#### `task.quiet`

- Type: `boolean`
- Env: `MISE_TASK_QUIET`
- Default: `false`

Suppress mise's own output while executing tasks without affecting other mise
commands. Task stdout and stderr remain visible. This setting is independent of
the `task.output` style, so it can be combined with `prefix`, `interleave`, or
another output style.

#### `task.remote_no_cache`

- Type: `boolean`(optional)
- Env: `MISE_TASK_REMOTE_NO_CACHE`
- Default: `None`

Mise will always fetch the latest tasks from the remote, by default the cache is used.

#### `task.run_auto_install`

- Type: `boolean`
- Env: `MISE_TASK_RUN_AUTO_INSTALL`
- Default: `true`

Automatically install missing tools when executing tasks.

#### `task.show_full_cmd`

- Type: `boolean`
- Env: `MISE_TASK_SHOW_FULL_CMD`
- Default: `false`

Disable truncation of command lines in task execution output. When true, the full command line will be shown.

#### `task.skip`

- Type: `string[]`
- Env: `MISE_TASK_SKIP`
- Default: `[]`

Tasks to skip when running `mise run`.

#### `task.skip_depends`

- Type: `boolean`
- Env: `MISE_TASK_SKIP_DEPENDS`
- Default: `false`

Run only specified tasks skipping all dependencies.

#### `task.source_freshness_equal_mtime_is_fresh`

- Type: `boolean`
- Env: `MISE_TASK_SOURCE_FRESHNESS_EQUAL_MTIME_IS_FRESH`
- Default: `false`

When source mtime equals output mtime, consider sources fresh (use <=). Default false uses strict < comparison.

#### `task.source_freshness_hash_contents`

- Type: `boolean`
- Env: `MISE_TASK_SOURCE_FRESHNESS_HASH_CONTENTS`
- Default: `false`

Use content hashing (blake3) instead of metadata for source freshness. More accurate but slower.

#### `task.timeout`

- Type: `string`(optional)
- Env: `MISE_TASK_TIMEOUT`
- Default: `None`

Sets a global default timeout for all tasks. Individual tasks can also specify their own `timeout`.

When both a global timeout and a per-task timeout are set, the **shorter** of the two always wins—a
per-task timeout cannot extend beyond the global timeout. The `--timeout` CLI flag overrides this
global setting.

#### `task.timings`

- Type: `boolean`(optional)
- Env: `MISE_TASK_TIMINGS`
- Default: `None`

Show completion message with elapsed time for each task on `mise run`. Default shows when output type is `prefix`.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)