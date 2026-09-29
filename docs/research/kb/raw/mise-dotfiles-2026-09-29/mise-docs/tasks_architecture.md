[Skip to content](https://mise.jdx.dev/tasks/architecture.html#VPContent)

On this page

# Task System Architecture [​](https://mise.jdx.dev/tasks/architecture.html\#task-system-architecture)

Understanding how mise's task system works helps you write more efficient tasks and troubleshoot dependency issues.

## Task Dependency System [​](https://mise.jdx.dev/tasks/architecture.html\#task-dependency-system)

mise uses a dependency graph to manage task execution order and parallelism. This ensures tasks run in the correct order while maximizing parallel execution.

### Dependency Graph Resolution [​](https://mise.jdx.dev/tasks/architecture.html\#dependency-graph-resolution)

When you run a task, mise builds a directed graph of the selected tasks and their declared dependencies, then rejects cycles. In this example, selecting `deploy` includes all of the prerequisites shown; arrows point from prerequisite to dependent:

Syntax error in textmermaid version 11.17.2

This graph ensures that:

- Dependencies run before dependents
- Independent tasks run in parallel
- No circular dependencies exist
- Failed dependencies prevent dependents from running

### Dependency Types [​](https://mise.jdx.dev/tasks/architecture.html\#dependency-types)

mise supports three types of task dependencies:

#### `depends` \- Prerequisites [​](https://mise.jdx.dev/tasks/architecture.html\#depends-prerequisites)

Tasks that must complete successfully before this task runs:

toml

```
[tasks.test]
depends = ["lint", "build"]
run = "npm test"
```

#### `depends_post` \- Cleanup Tasks [​](https://mise.jdx.dev/tasks/architecture.html\#depends-post-cleanup-tasks)

Tasks that run after this task completes (whether it succeeded or failed):

toml

```
[tasks.deploy]
depends = ["build", "test"]
depends_post = ["cleanup", "notify"]
run = "kubectl apply -f deployment.yaml"
```

Regular dependencies of cleanup tasks belong to the same post-phase subtree and do not start until the parent task has completed. mise runs that subtree if the parent started, even when the parent fails, but skips the entire subtree when a regular dependency fails before the parent can start. A task used as both a regular dependency and a post-dependency is executed separately in each phase.

#### `wait_for` \- Soft Dependencies [​](https://mise.jdx.dev/tasks/architecture.html\#wait-for-soft-dependencies)

Tasks that must finish first if they are already scheduled. `wait_for` does not schedule them. A missing task definition still causes an error unless the reference sets `optional = true`; see [`wait_for`](https://mise.jdx.dev/tasks/task-configuration.html#wait-for).

toml

```
[tasks.integration-test]
wait_for = ["start-services"]  # Only waits if start-services is also being run
run = "npm run test:integration"
```

## Parallel Execution Engine [​](https://mise.jdx.dev/tasks/architecture.html\#parallel-execution-engine)

### Job Control [​](https://mise.jdx.dev/tasks/architecture.html\#job-control)

mise executes tasks in parallel up to the configured job limit:

bash

```
mise run --jobs 16 test       # Use 16 parallel jobs
mise run -j 1 test            # Force sequential execution
```

The default is 8 parallel jobs, but you can configure this globally:

toml

```
# ~/.config/mise/config.toml
[settings]
jobs = 4
```

### Example Execution Flow [​](https://mise.jdx.dev/tasks/architecture.html\#example-execution-flow)

Given these tasks:

toml

```
[tasks.lint]
run = "eslint src/"

[tasks.test-unit]
depends = ["lint"]
run = "npm run test:unit"

[tasks.test-integration]
depends = ["lint"]
run = "npm run test:integration"

[tasks.build]
depends = ["test-unit", "test-integration"]
run = "npm run build"
```

Execution with `--jobs 2`:

```
Time →
0s:   [lint]
5s:   [test-unit] [test-integration]  # Run in parallel after lint
15s:  [build]                        # Waits for both tests
```

## Task Discovery and Resolution [​](https://mise.jdx.dev/tasks/architecture.html\#task-discovery-and-resolution)

### Task Sources [​](https://mise.jdx.dev/tasks/architecture.html\#task-sources)

mise loads inline TOML tasks, included task files, and executable file tasks from the active configuration hierarchy. A child configuration can override a parent configuration. An inline metadata-only definition can also add properties to an existing command or file task.

There is no single source-type ordering that describes every combination. See [`task_config.includes`](https://mise.jdx.dev/tasks/task-configuration.html#task_config.includes) for include ordering, command replacement, and metadata overlays. Use `mise tasks info <task>` to inspect the selected definition.

### Task Resolution Process [​](https://mise.jdx.dev/tasks/architecture.html\#task-resolution-process)

When you run `mise run build`, mise:

1. **Discovers all tasks** from all configuration sources
2. **Resolves the task name** (handles aliases and partial matches)
3. **Builds the dependency graph** including all dependencies
4. **Validates the graph** (checks for circular dependencies)
5. **Executes in dependency order** with parallelism

### Task Resolution Across Directories [​](https://mise.jdx.dev/tasks/architecture.html\#task-resolution-across-directories)

Tasks from parent directories are available in subdirectories and can be overridden:

```
project/
├── mise.toml              # defines: lint, test, build
└── frontend/
    └── mise.toml          # overrides: test, adds: bundle
```

In `frontend/`, you have access to `lint` (from parent), `test` (overridden), `build` (from parent), and `bundle` (local).

## Advanced Dependency Features [​](https://mise.jdx.dev/tasks/architecture.html\#advanced-dependency-features)

### Conditional Dependencies [​](https://mise.jdx.dev/tasks/architecture.html\#conditional-dependencies)

Use task arguments for conditional behavior:

toml

```
[tasks.test]
depends = ["build"]
run = '''
#!/usr/bin/env bash
if [ "$1" = "--with-lint" ]; then
  mise run lint
fi
npm test
'''
```

The shebang selects Bash, which must be installed on the host. Without it, mise uses the platform default inline shell (`sh -c` on Unix, `cmd /c` on Windows), so the bash `[ ... ]` test would fail to parse on a Windows host. For richer argument handling, prefer the [`usage` field](https://mise.jdx.dev/tasks/task-arguments.html#usage-field) instead of positional parameters.

### Dynamic Dependencies [​](https://mise.jdx.dev/tasks/architecture.html\#dynamic-dependencies)

A script can invoke another task conditionally. These nested invocations are separate runs; they are not added to the original dependency graph and do not appear in `mise tasks deps`:

bash

```
#!/usr/bin/env bash
#MISE depends=["setup"]

# Additional conditional dependency
if [ ! -f ".env" ]; then
  mise run generate-env
fi

npm start
```

### Cross-Project Dependencies [​](https://mise.jdx.dev/tasks/architecture.html\#cross-project-dependencies)

Enable [monorepo mode](https://mise.jdx.dev/tasks/monorepo.html#configuration) and declare the project roots before referencing their tasks. For projects named `api` and `frontend`:

toml

```
[tasks.deploy-all]
depends = [\
  "//api:build",\
  "//frontend:build",\
  "deploy-infrastructure"\
]
run = "echo 'All services deployed'"
```

## Performance Optimizations [​](https://mise.jdx.dev/tasks/architecture.html\#performance-optimizations)

### Source and Output Tracking [​](https://mise.jdx.dev/tasks/architecture.html\#source-and-output-tracking)

Tasks can skip execution if sources haven't changed:

toml

```
[tasks.build]
sources = ["src/**/*.ts", "package.json"]
outputs = ["dist/**/*"]
run = "npm run build"
```

mise only runs the task if:

- Source files are newer than output files
- The task has never been run
- Dependencies have changed

### Incremental Execution [​](https://mise.jdx.dev/tasks/architecture.html\#incremental-execution)

Use `mise run --force` to ignore source/output checking:

bash

```
mise run --force build     # Always run, ignore source changes
```

### Parallel File Watching [​](https://mise.jdx.dev/tasks/architecture.html\#parallel-file-watching)

Use `mise watch` for continuous development:

bash

```
mise watch              # Watch the default task
mise watch build test   # Watch specific tasks
```

This automatically reruns tasks when their source files change.

## Debugging Task Dependencies [​](https://mise.jdx.dev/tasks/architecture.html\#debugging-task-dependencies)

### Visualize Dependencies [​](https://mise.jdx.dev/tasks/architecture.html\#visualize-dependencies)

bash

```
mise tasks deps build           # Show build's declared dependencies
mise tasks deps --dot > deps.dot # Generate graphviz diagram
```

### Execution Tracing [​](https://mise.jdx.dev/tasks/architecture.html\#execution-tracing)

bash

```
mise run --verbose build       # Show task execution details
mise run --dry-run build       # Show what would run without executing
```

### Common Issues [​](https://mise.jdx.dev/tasks/architecture.html\#common-issues)

**Circular Dependencies**:

```
Error: Circular dependency detected: test → build → test
```

Solution: Remove the cycle or split the shared work into a separate prerequisite. `wait_for` also creates ordering constraints when both tasks are scheduled, so it is not a general way to break a cycle.

**Missing Dependencies**:

```
Error: Task 'build' depends on 'lint' but 'lint' was not found
```

Solution: Define the missing task or remove the dependency.

**Slow Parallel Execution**:

- Check if tasks have unnecessary dependencies
- Use `mise tasks deps` to verify the declared dependency graph (`depends`, `wait_for`, `depends_post`)
- Consider increasing `--jobs` if you have spare CPU cores

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)