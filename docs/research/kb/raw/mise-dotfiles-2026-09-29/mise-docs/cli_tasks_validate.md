[Skip to content](https://mise.jdx.dev/cli/tasks/validate.html#VPContent)

On this page

# `mise tasks validate` [​](https://mise.jdx.dev/cli/tasks/validate.html\#mise-tasks-validate)

- **Usage:**`mise tasks validate [--errors-only] [--json] [TASKS]…`
- **Effect:** read-only
- **Source code:** [`src/cli/tasks/validate.rs`](https://github.com/jdx/mise/blob/main/src/cli/tasks/validate.rs)

Validate tasks for common errors and issues

## Arguments [​](https://mise.jdx.dev/cli/tasks/validate.html\#arguments)

- **`[TASKS]…`** — Tasks to validate If not specified, validates all tasks

## Flags [​](https://mise.jdx.dev/cli/tasks/validate.html\#flags)

- **`--errors-only`** — Only show errors (skip warnings)
- **`--json`** — Output validation results in JSON format
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tasks/validate.html\#examples)

Validate all tasks

```
mise tasks validate
```

Validate specific tasks

```
mise tasks validate build test
```

Output results as JSON

```
mise tasks validate --json
```

Only show errors (skip warnings)

```
mise tasks validate --errors-only
```

Validation Checks:

The validate command performs the following checks:

• Circular Dependencies: Detects dependency cycles • Missing References: Finds references to nonexistent tasks • Usage Spec Parsing: Validates #USAGE directives and specs • Timeout Format: Checks timeout values are valid durations • Alias Conflicts: Detects duplicate aliases across tasks • File Existence: Verifies file-based tasks exist • Directory Templates: Validates directory paths and templates • Shell Commands: Checks shell executables exist • Glob Patterns: Validates source and output patterns • Run Entries: Ensures tasks reference valid dependencies

## Related documentation [​](https://mise.jdx.dev/cli/tasks/validate.html\#related-documentation)

- [Task configuration](https://mise.jdx.dev/tasks/task-configuration.html).
- [`mise tasks [FLAGS] [TASK] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tasks.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)