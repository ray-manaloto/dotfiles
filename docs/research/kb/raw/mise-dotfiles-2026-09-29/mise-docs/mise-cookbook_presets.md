[Skip to content](https://mise.jdx.dev/mise-cookbook/presets.html#VPContent)

On this page

# Presets [​](https://mise.jdx.dev/mise-cookbook/presets.html\#presets)

A preset is a task you write to create a project's starting configuration. Store it as a [global file task](https://mise.jdx.dev/tasks/file-tasks.html) so it is available in new repositories. For reuse within an existing project, [task templates](https://mise.jdx.dev/tasks/templates.html) may be a better fit: they share task definitions without generating files.

## Example python preset [​](https://mise.jdx.dev/mise-cookbook/presets.html\#example-python-preset)

This Bash task writes a Python and uv config into the directory where you invoke it. It refuses to replace an existing `mise.toml` and leaves project initialization and dependency installation as explicit next steps.

Create the task directory:

sh

```
mkdir -p ~/.config/mise/tasks/preset
```

Then save the following as `~/.config/mise/tasks/preset/python`:

~/.config/mise/tasks/preset/python

bash

```
#!/usr/bin/env bash
#MISE description="Create a Python and uv project config"
#MISE dir="{{cwd}}"
set -euo pipefail

if [[ -e mise.toml ]]; then
  echo "mise.toml already exists; merge the preset manually" >&2
  exit 1
fi

cat > mise.toml <<'TOML'
[tools]
python = "3.12"
uv = "latest"

[tasks.sync]
description = "Sync the project's locked dependencies"
run = "uv sync --locked"

[tasks.test]
description = "Run tests from the project environment"
run = "uv run --locked pytest"
TOML

echo "Created mise.toml"
```

Make the task executable on Unix:

sh

```
chmod +x ~/.config/mise/tasks/preset/python
```

Then run it from an empty project directory:

sh

```
mkdir my-project
cd my-project
mise run preset:python
mise exec -- uv init --bare
mise exec -- uv add --dev pytest
```

The preset creates `mise.toml`; uv creates the project manifest and lockfile. Add your application and tests, then run `mise run test`. Teammates can run `mise run sync` after cloning to install the locked dependencies. Commit `mise.toml`, `pyproject.toml`, and `uv.lock`, and ignore `.venv/`.

`#MISE dir=""` matters for a global task: it makes the task write into the invocation directory instead of the global task's config root. Adapt the script before using it in repositories with existing configuration or another package manager.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)