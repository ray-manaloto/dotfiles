[Skip to content](https://mise.jdx.dev/dev-tools/backends/pipx.html#VPContent)

On this page

# PyPI Backend [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#pypi-backend)

The `pypi` backend installs Python command-line applications in isolated virtual environments. Each tool gets its own dependencies. Use a project environment and pip or uv for application libraries such as NumPy and requests.

## Quick start [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#dependencies)

Install uv, Python, and a CLI from PyPI:

sh

```
mise use python@3.14 uv pypi:black
mise exec -- black --version
```

### Project configuration [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#usage)

This adds the following to `mise.toml`:

toml

```
[tools]
python = "3.14"
uv = "latest"
"pypi:black" = "latest"
```

Add `-g` to `mise use` to install tools globally.

mise uses uv to install tools. With [dependency locking](https://mise.jdx.dev/dev-tools/backends/pipx.html#dependency-locking), it runs `uv sync --frozen`; version-only installs use `uv tool install`. If uv is unavailable, version-only installs fall back to `pipx install`. See [Using pipx](https://mise.jdx.dev/dev-tools/backends/pipx.html#using-pipx) to select that installer explicitly.

## Package sources [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#supported-pipx-syntax)

Use `pypi:black` for the PyPI distribution or `pypi:psf/black` for its GitHub source. Their releases and installation requirements can differ.

| Source | Example |
| --- | --- |
| PyPI, latest version | `pypi:black` |
| PyPI, specific version | `pypi:black@24.3.0` |
| GitHub, latest release | `pypi:psf/black` |
| GitHub, specific release | `pypi:psf/black@24.3.0` |
| Git repository | `pypi:git+https://github.com/psf/black.git` |
| Git branch | `pypi:git+https://github.com/psf/black.git@main` |
| Git subdirectory | `pypi:git+https://github.com/o/repo#subdirectory=cli` |

For GitHub sources, `latest` selects the newest GitHub release and installs from the default branch only when the repository has no releases. For other Git URLs, `latest` resolves default-branch HEAD to a concrete commit. Any branch, tag, or commit can be requested explicitly, and remote tags are also available for explicit version requests.

### Monorepo subdirectories [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#git-subdirectory)

For a package that lives in a subdirectory of a Git repository, add the same `#subdirectory=` fragment that pip and uv accept. The `.git` suffix is optional, and the fragment also works with GitHub shorthand:

sh

```
mise use 'pypi:git+https://github.com/runpantheon/ltui#subdirectory=ltui@main'
mise use 'pypi:runpantheon/ltui#subdirectory=jtui@main'
```

Quote the argument so the shell does not treat `#` specially. The fragment is part of the tool name, so each subdirectory is a separate tool, and the version still goes after `@`. mise places the ref before the fragment in the request it sends to the installer. Other fragment keys pass through unchanged, except that mise reads `[...]` in a tool name as [tool options](https://mise.jdx.dev/dev-tools/#tool-options); use the [`extras`](https://mise.jdx.dev/dev-tools/backends/pipx.html#extras) option instead of `#egg=pkg[extra]`.

Versions come from the repository as a whole, so `latest` selects the newest release even if the subdirectory did not exist at that tag. Pin a branch or commit when a repository's releases predate the subdirectory. When you use [`extras`](https://mise.jdx.dev/dev-tools/backends/pipx.html#extras), mise guesses the distribution name from the subdirectory; set `package_name` if the name differs.

Direct HTTPS archive URLs are unsupported. Other source syntax may work but is unsupported and untested.

## Dependency locking [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#dependency-locking)

With **uv 0.12.10 or newer**, new `mise.lock` files record the full Python dependency graph, including wheel hashes and Python/platform markers. Locked installs reuse that graph without resolving dependencies again.

Create a lockfile, or upgrade an existing version-only lockfile, then install:

sh

```
mise lock --upgrade
mise install --locked
```

Commit both `mise.lock` and its [dependency sidecar directory](https://mise.jdx.dev/dev-tools/mise-lock.html#native-dependency-sidecars), which contains the native `pyproject.toml` and `uv.lock` files. Existing lockfiles keep version-only behavior until explicitly upgraded.

### Updating dependencies [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#updating-dependencies)

Ordinary `mise lock` reuses the recorded graph. To refresh a tool's transitive dependencies even when its own version has not changed:

sh

```
mise lock --bump pypi:black
```

You can also inspect or edit a sidecar with uv. For a tool locked to Black 24.10.0 in the default sidecar layout:

sh

```
uv tree --project .mise/locks/pypi-black/24.10.0
uv lock --project .mise/locks/pypi-black/24.10.0 --upgrade-package click
mise lock
```

Run `mise lock` after editing a sidecar to accept its updated digest before using `mise install --locked`.

### Requirements and limitations [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#requirements-and-limitations)

- **Wheels only for dependency graphs:** every dependency needs a published wheel for the target Python version and platform. Explicit `mise lock` and locked installs do not build source distributions. An ordinary `mise install` falls back to a version-only uv installation when it cannot produce a wheel-only graph.
- **PyPI packages with uv:** Git sources and standalone pipx installs use version-only locking. pipx cannot replay a uv dependency graph.
- **No free-form installer arguments in dependency graphs:**`uvx_args` and `pipx_args` use version-only installation during ordinary installs. Explicit dependency locking rejects them because mise cannot safely translate arbitrary installer arguments into a reproducible graph. Use the semantic options instead when dependency locking is required: [`with`](https://mise.jdx.dev/dev-tools/backends/pipx.html#with) injects additional requirements into the tool environment, [`expose`](https://mise.jdx.dev/dev-tools/backends/pipx.html#expose) also exposes their executables, and [`dependency_prereleases`](https://mise.jdx.dev/dev-tools/backends/pipx.html#dependency_prereleases) sets uv's prerelease policy. These are locked together with the tool, so the graph covers the injected packages. Configure [Python](https://mise.jdx.dev/dev-tools/backends/pipx.html#choosing-python) and the [registry URL](https://mise.jdx.dev/dev-tools/backends/pipx.html#registry-url) directly as well.
- **Installed Python required:** lock generation needs an interpreter discoverable by uv, though it need not match the tool's configured Python version. Graph installs use the selected mise Python and do not download a replacement.
- **Complete lockfiles required:** revision-2 locked uv installs fail if their dependency graph is missing. Run `mise lock` to generate it.

The graph covers the Python range that every locked requirement supports, starting at Python 3.8, and retains all published wheel targets for portability. Requirements injected with [`with`](https://mise.jdx.dev/dev-tools/backends/pipx.html#with) or [`expose`](https://mise.jdx.dev/dev-tools/backends/pipx.html#expose) are part of that calculation: one pinned to an exact version raises the range's floor to the release's own `requires-python`, because a single release cannot span the wider range the way uv resolves an unpinned requirement. A pin carrying an environment marker that tests the interpreter, such as `python_version < "3.12"`, is left out, since it is simply absent from the versions it excludes. This can make sidecars large. Frozen installs reuse uv's artifact cache.

Different dependency graphs and configured Python interpreters get separate installations; `mise ls` still shows the package version. For system Python, mise records the interpreter's implementation, major/minor version, ABI, and platform during installation so later commands can find the environment even if that interpreter is no longer on PATH.

### Private indexes and release age [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#private-indexes-and-release-age)

Simple-only indexes must provide consistent `data-requires-python` metadata on the selected release's wheel links. Registry credentials belong in the installer environment or credential provider. URLs containing credentials or query strings cannot be recorded in the lockfile.

[`minimum_release_age`](https://mise.jdx.dev/configuration/settings.html#minimum_release_age) filters transitive dependencies when resolving a graph, not when replaying it. For version-only installs, mise passes uv's `--exclude-newer` flag (requires uv 0.2.22 or newer) or pip's `--uploaded-prior-to` flag through pipx.

## Choosing Python [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#choosing-python)

For graph-locked tools, configure the interpreter through mise:

toml

```
[tools]
python = "3.14"
uv = "0.12.10"
"pypi:black" = "latest"
```

For legacy version-only installs, the selected installer chooses the interpreter; `uvx_args` and `pipx_args` can pass installer-specific Python options.

## Python upgrades [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#python-upgrades)

If a CLI stops working after changing Python, reinstall it under the intended Python version. This recreates the tool environment and its dependencies:

sh

```
mise install --force pypi:black
mise exec -- black --version
```

Check which Python version is active before reinstalling. Existing virtualenvs and native extensions do not necessarily remain usable after their interpreter is removed or changed.

## Using pipx [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#using-pipx)

To use the pipx installer, install Python and pipx, then disable uv for the tool:

sh

```
mise use python@3.14 pipx
```

toml

```
[tools]
"pypi:ansible" = { version = "latest", uvx = false, expose = [], pipx_args = "--include-deps" }
```

This uses version-only locking. An existing uv dependency graph cannot be replayed with pipx.

### Compatibility with `pipx:` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#compatibility-with-pipx)

The `pipx:` backend name remains supported. Existing configurations do not need to change. However, `pypi:black` and `pipx:black` are distinct tool identities: switching prefixes creates a separate installation and lock entry. mise preserves explicit `pipx:` names in output and lockfiles.

The legacy option names `uvx` and `uvx_args` control uv installation; they do not mean mise runs the `uvx` command.

## Settings [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#settings)

Set these with `mise settings set [VARIABLE]=[VALUE]` or by setting the environment variable listed.

### `pypi.registry_url`

- Type: `string`(optional)
- Env: `MISE_PYPI_REGISTRY_URL`
- Default: `None`

Package registry URL for Python tools (pipx.registry\_url is a compatibility alias).

### `pypi.uvx`

- Type: `boolean`(optional)
- Env: `MISE_PYPI_UVX`
- Default: `None`

Use uv for Python tools when available (pipx.uvx is a compatibility alias).

## Tool Options [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#tool-options)

The following [tool-options](https://mise.jdx.dev/dev-tools/#tool-options) are available for the `pypi` backend—these go in `[tools]` in `mise.toml`.

### `registry_url` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#registry-url)

Set the registry URL used to resolve versions for this tool. Include a `{}` placeholder for the package name. This overrides the `pypi.registry_url` setting for this tool.

toml

```
[tools]
"pypi:my-tool" = { version = "latest", registry_url = "https://packages.example.com/pypi/{}/json" }
```

Dependency locking also derives the install index from this URL. For version-only installs, configure the install index separately through `uvx_args` or `pipx_args`. For example, with the pipx installer:

toml

```
[tools]
"pypi:my-tool" = { version = "latest", uvx = false, registry_url = "https://packages.example.com/pypi/{}/json", pipx_args = "--pip-args='--index-url https://packages.example.com/pypi/simple'" }
```

### `install_env` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#install-env)

Set environment variables for the installer. mise still sets the tool directory, bin directory, and configured Python package index variables after applying `install_env`. For the uv installer, for example:

toml

```
[tools]
"pypi:black" = { version = "latest", install_env = { UV_COMPILE_BYTECODE = "1" } }
```

### `extras` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#extras)

Install optional dependencies (Python package extras).

toml

```
[tools]
"pypi:harlequin" = { version = "latest", extras = "postgres,s3" }
# equivalent array form:
# "pypi:harlequin" = { version = "latest", extras = ["postgres", "s3"] }
# extras also work with Git sources:
# "pypi:psf/black" = { version = "latest", extras = ["jupyter"] }
```

When passing extras inline, use mise's `key=value` tool-option syntax:

bash

```
mise use 'pypi:psf/black[extras=jupyter]@latest'
```

For Git repositories whose name differs from the Python distribution name, set `package_name` so mise can build the requirement used to select extras:

toml

```
[tools]
"pypi:owner/repository" = { version = "latest", package_name = "distribution", extras = ["feature"] }
```

### `pipx_args` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#pipx-args)

Additional arguments for `pipx install`. These apply only to version-only installs using pipx and are unsupported with dependency graphs.

toml

```
[tools]
"pypi:ansible" = { version = "latest", uvx = false, expose = [], pipx_args = "--include-deps" }
```

### `with` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#with)

Install additional Python requirements in the tool environment. This option requires uv and participates in dependency locking.

toml

```
[tools]
"pypi:azure-cli" = { version = "latest", with = ["pip"] }
```

A requirement pinned to an exact version narrows the locked Python range to the versions that release supports, so the tool may end up needing a newer interpreter than it declares on its own. Guard the pin with an interpreter marker, such as `"legacy==1.0.0; python_version < '3.12'"`, to keep the wider range when the requirement is only needed on some versions.

### `expose` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#expose)

Install additional Python requirements and expose their executable entry points. This option requires uv 0.8.5 or newer and participates in dependency locking.

toml

```
[tools]
"pypi:ansible" = { version = "latest", expose = ["ansible-core"] }
```

### `dependency_prereleases` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#dependency-prereleases)

Set uv's prerelease policy for dependency resolution. Supported values are `disallow`, `allow`, `if-necessary`, and `explicit`. This option requires uv and is applied both when generating dependency graphs and during version-only installs.

toml

```
[tools]
"pypi:azure-cli" = { version = "latest", dependency_prereleases = "allow" }
```

### `uvx` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#uvx)

Set to `false` to use pipx instead of uv for this tool. This also disables dependency graph locking and requires pipx to be installed.

toml

```
[tools]
"pypi:ansible" = { version = "latest", uvx = false, expose = [] }
```

The empty `expose` list clears Ansible's uv-backed registry default. Clear any other semantic defaults the same way when overriding a registry tool to use pipx.

### `uvx_args` [​](https://mise.jdx.dev/dev-tools/backends/pipx.html\#uvx-args)

Additional arguments for version-only installs using `uv tool install`. These are unsupported with dependency graphs; `pipx_args` applies only to pipx.

toml

```
[tools]
"pypi:ansible-core" = { version = "latest", uvx_args = "--resolution lowest" }
```

Prefer the semantic [`with`](https://mise.jdx.dev/dev-tools/backends/pipx.html#with), [`expose`](https://mise.jdx.dev/dev-tools/backends/pipx.html#expose), and [`dependency_prereleases`](https://mise.jdx.dev/dev-tools/backends/pipx.html#dependency_prereleases) options when they cover the desired behavior. Unlike arbitrary arguments, those options support dependency graphs.

Implementation: [`src/backend/pipx.rs`](https://github.com/jdx/mise/blob/main/src/backend/pipx.rs).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)