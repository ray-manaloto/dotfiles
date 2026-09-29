[Skip to content](https://mise.jdx.dev/lang/node.html#VPContent)

On this page

# Node.js [​](https://mise.jdx.dev/lang/node.html\#node-js)

Like `nvm` (or `volta`, `fnm`, or `asdf`), `mise` can manage multiple versions of Node.js on the same system.

## Usage [​](https://mise.jdx.dev/lang/node.html\#usage)

Select Node.js for the current project and verify it without depending on shell activation:

sh

```
mise use node@26
mise exec -- node --version
```

Use `mise use -g node@26` for a personal default. Project versions override that default when you enter the project with shell activation, run a task, or use `mise exec`. Use `mise upgrade node` to update within the configured request.

See the [Node.js Cookbook](https://mise.jdx.dev/mise-cookbook/nodejs.html) for common tasks and examples.

These instructions use mise's built-in node support. An installed external plugin with the same name can change the behavior; use `mise plugins ls` to check for overrides. See the [core implementation](https://github.com/jdx/mise/blob/main/src/plugins/core/node.rs) for backend details.

## Run projects with aube [​](https://mise.jdx.dev/lang/node.html\#run-projects-with-aube)

[aube](https://aube.jdx.dev/) is a fast Node.js package manager with strong supply-chain security defaults. It reads and writes existing `package-lock.json`, `pnpm-lock.yaml`, and `yarn.lock` files in place, so a project can try it without a lockfile migration. Its `aubr` command installs stale dependencies automatically before running a package script and skips the install when dependencies are already current.

Install it with mise, then run an existing package script:

sh

```
mise use aube
mise exec -- aubr test
```

See [aube's security overview](https://aube.jdx.dev/security) for its release-cooling, trust-policy, malicious-package, and lifecycle-script protections.

## Tool Options [​](https://mise.jdx.dev/lang/node.html\#tool-options)

The following [tool-options](https://mise.jdx.dev/dev-tools/#tool-options) are available for the `node` backend. These options go in the `[tools]` section in `mise.toml`.

### `install_env` [​](https://mise.jdx.dev/lang/node.html\#install-env)

Set environment variables for source builds, default package installation, Corepack setup, and install-time verification commands run by the core `node` backend:

toml

```
[tools]
node = { version = "latest", install_env = { CFLAGS = "-O2" } }
```

## Pinning npm version [​](https://mise.jdx.dev/lang/node.html\#pinning-npm-version)

By default, Node.js ships with a bundled version of npm. If you need a specific npm version (e.g. to keep your entire team on the same version and avoid `package-lock.json` conflicts), you can pin it alongside Node in your `mise.toml`:

mise.toml

toml

```
[tools]
node = "26"
npm = "11"
```

To pin both to exact versions:

sh

```
mise use --pin node@lts npm@latest
```

This writes the resolved concrete versions to `mise.toml`. The numbers depend on the current releases; inspect the result with `mise ls --current` or read the config file.

The separately configured npm takes precedence over Node's bundled npm inside the mise environment. Check it with `mise exec -- npm --version`. This selects the package-manager executable; the project's dependency lockfile still controls its npm packages.

## `.nvmrc`, `.node-version` and `package.json` support [​](https://mise.jdx.dev/lang/node.html\#nvmrc-node-version-and-package-json-support)

By default, mise uses a `mise.toml` file for auto-switching between software versions.

It also supports `.tool-versions` files for asdf compatibility. `.nvmrc`, `.node-version`, and the `devEngines` field in `package.json` are also supported but must be explicitly enabled (see the tip below).

See [idiomatic version files](https://mise.jdx.dev/configuration.html#idiomatic-version-files) for more information.

TIP

Idiomatic version files (`.nvmrc`, `.node-version`, `devEngines` field in `package.json`) are disabled by default and must be explicitly enabled:

sh

```
mise settings add idiomatic_version_file_enable_tools node
```

Or in `~/.config/mise/config.toml`:

toml

```
[settings]
idiomatic_version_file_enable_tools = ["node"]
```

To keep `.nvmrc` or `.node-version` enabled while preventing node from using `devEngines.runtime` in `package.json`:

sh

```
mise settings add idiomatic_version_file_disable_files node:package.json
```

### `package.json` [​](https://mise.jdx.dev/lang/node.html\#package-json)

With idiomatic version files enabled for `node`, mise reads `devEngines.runtime` when its `name` is `node`:

package.json

json

```
{
  "devEngines": {
    "runtime": { "name": "node", "version": "22.14.0" }
  }
}
```

This selects Node.js 22.14.0. `devEngines.runtime` accepts an object or an array; mise reads the first entry in an array. See the [Bun](https://mise.jdx.dev/lang/bun.html#version-files) and [Deno](https://mise.jdx.dev/lang/deno.html#version-files) guides for other runtimes.

mise does not read `engines.node`: it describes compatible Node.js versions, not the version to use for development. If a project only has an `engines` range, select a version explicitly:

sh

```
mise use node@22
```

### Package-manager versions in `package.json` [​](https://mise.jdx.dev/lang/node.html\#package-manager-versions-in-package-json)

Enable idiomatic version files separately for each package manager you use, for example:

sh

```
mise settings add idiomatic_version_file_enable_tools pnpm
```

For `npm`, `pnpm`, and `yarn`, mise reads a matching `devEngines.packageManager` declaration, then falls back to the top-level `packageManager` field:

package.json

json

```
{
  "packageManager": "pnpm@9.1.0"
}
```

This selects pnpm 9.1.0. The equivalent `devEngines` declaration is:

package.json

json

```
{
  "devEngines": {
    "packageManager": { "name": "pnpm", "version": "9.1.0" }
  }
}
```

`devEngines.packageManager` also accepts an array; mise reads its first entry. The declaration's name must match the enabled tool. For Bun's runtime and package-manager precedence, see [Bun version files](https://mise.jdx.dev/lang/bun.html#version-files).

## Default node packages [​](https://mise.jdx.dev/lang/node.html\#default-node-packages)

Planned deprecation

Default package files are deprecated. They are still supported for now, but mise will start warning in `2026.11.0` and support will be removed in `2027.11.0`.

For npm CLIs, install the tool directly with the [npm backend](https://mise.jdx.dev/dev-tools/backends/npm.html):

toml

```
[tools]
"npm:typescript" = "latest"
```

For packages that really should be installed into every Node.js version, use a tool-level `postinstall` hook:

toml

```
[tools]
node = { version = "22", postinstall = "npm install -g typescript" }
```

mise can automatically install a default set of npm packages right after installing a node version. To use this legacy feature, provide a `$HOME/.default-npm-packages` file that lists one package per line, for example:

text

```
typescript
eslint
```

You can specify a different location for this file with the `MISE_NODE_DEFAULT_PACKAGES_FILE` variable.

## "nodejs" -> "node" Alias [​](https://mise.jdx.dev/lang/node.html\#nodejs-node-alias)

You cannot install/use a plugin named "nodejs". If you try, mise renames it to "node". See the [FAQ](https://mise.jdx.dev/faq.html#what-is-the-difference-between-nodejs-and-node-or-golang-and-go) for an explanation.

## Building from source [​](https://mise.jdx.dev/lang/node.html\#building-from-source)

If compiling from source, see [BUILDING.md](https://github.com/nodejs/node/blob/main/BUILDING.md#building-nodejs-on-supported-platforms) in node's documentation for required system dependencies.

shell

```
mise settings node.compile=1
mise use node@latest
```

## Unofficial Builds [​](https://mise.jdx.dev/lang/node.html\#unofficial-builds)

Nodejs.org offers a set of [unofficial builds](https://unofficial-builds.nodejs.org/) for some platforms that the official binaries do not support. These are a nice alternative to compiling from source on those platforms.

To use them, first point the mirror URL at the unofficial builds:

sh

```
mise settings node.mirror_url=https://unofficial-builds.nodejs.org/download/release/
```

If you only need to support an alternative arch/OS like linux-loong64 or linux-armv6l, this is all that is required. Node also provides flavors such as musl or glibc-217 (an older glibc version than the official binaries are built with).

To use these, set `node.flavor`:

sh

```
mise settings node.flavor=musl
mise settings node.flavor=glibc-217
```

For the common musl case, `mise settings libc=musl` also selects Node's `musl` flavor when `node.flavor` is unset.

## Settings [​](https://mise.jdx.dev/lang/node.html\#settings)

### `node.apply_patches`

- Type: `string`(optional)
- Env: `MISE_NODE_APPLY_PATCHES`
- Default: `None`

Newline-separated list of patch files or URLs, applied to the extracted node source before
`./configure` runs.

They only reach a source build. `node.compile = true` forces one; failing that, they still apply
whenever no precompiled archive exists for the version and mise falls back to compiling on its own.
When a precompiled binary is what gets installed, mise warns rather than dropping the patches
silently.

### `node.cflags`

- Type: `string`(optional)
- Env: `MISE_NODE_CFLAGS`
- Default: `None`

Additional CFLAGS options (e.g., to override -O3).

### `node.compile`

- Type: `boolean`(optional)
- Env: `MISE_NODE_COMPILE`
- Default: `None`

Compile node from source.

### `node.concurrency`

- Type: `integer`
- Env: `MISE_NODE_CONCURRENCY`
- Default: `Number of physical CPUs (unless ninja is enabled)`

Number of parallel jobs for node compilation. Defaults to the number of physical CPU cores when using make. When ninja is enabled, this defaults to unset (ninja handles concurrency automatically).

### `node.configure_opts`

- Type: `string`(optional)
- Env: `MISE_NODE_CONFIGURE_OPTS`
- Default: `None`

Additional ./configure options.

### `node.corepack`

- Type: `boolean`
- Env: `MISE_NODE_COREPACK`
- Default: `false`

Installs the default corepack shims after installing any node version.

### `node.default_packages_file`deprecated

- Type: `string`
- Env: `MISE_NODE_DEFAULT_PACKAGES_FILE`
- Default: `~/.default-npm-packages`
- Deprecated: Default npm package files are deprecated. Use tool-level postinstall hooks for packages that should be installed into every node version, or use the npm: backend for CLI tools.

Path to a file containing packages to install with npm after installing a new Node.js version.
Defaults to `~/.default-npm-packages`. Also checks `~/.default-nodejs-packages` and `~/.default-node-packages` for backwards compatibility.

Format: one package per line, with optional version specifier:

```
lodash
typescript@latest
@types/node@^20
```

### `node.flavor`

- Type: `string`(optional)
- Env: `MISE_NODE_FLAVOR`
- Default: `None`

Install a specific node flavor like glibc-217 or musl. Use with unofficial node build repo.

### `node.gpg_verify`

- Type: `boolean`(optional)
- Env: `MISE_NODE_GPG_VERIFY`
- Default: `None`

Verify OpenPGP signatures for node (built-in, no external gpg required). Set to false to disable.

### `node.make`

- Type: `string`(optional)
- Env: `MISE_NODE_MAKE`
- Default: `None`

Make command to use.

### `node.make_install_opts`

- Type: `string`(optional)
- Env: `MISE_NODE_MAKE_INSTALL_OPTS`
- Default: `None`

Additional make install options.

### `node.make_opts`

- Type: `string`(optional)
- Env: `MISE_NODE_MAKE_OPTS`
- Default: `None`

Additional make options.

### `node.mirror_url`

- Type: `string`(optional)
- Env: `MISE_NODE_MIRROR_URL`
- Default: `None`

Mirror to download node tarballs from.

### `node.ninja`

- Type: `boolean`
- Env: `MISE_NODE_NINJA`
- Default: `Auto-detected: true if ninja is on PATH`

If true, use ninja build system instead of make for faster compilation.
Defaults to true if `ninja` is found on PATH, false otherwise.

Ninja is generally faster than make for incremental builds.

### `node.nodenv_root`

- Type: `string`
- Env: `NODENV_ROOT`
- Default: `~/.nodenv`

Directory for nodenv.

### `node.npm_shim`

- Type: `boolean`
- Env: `MISE_NODE_NPM_SHIM`
- Default: `true`

Install a bash wrapper at bin/npm that triggers `mise reshim` after `npm install -g`. Disable to let corepack or a global `npm install -g npm@...` manage `bin/npm` directly.

### `node.nvm_dir`

- Type: `string`
- Env: `NVM_DIR`
- Default: `~/.nvm`

Directory for nvm.

### `node.verify`

- Type: `boolean`
- Env: `MISE_NODE_VERIFY`
- Default: `true`

Verify the downloaded assets using GPG.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)