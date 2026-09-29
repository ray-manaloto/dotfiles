[Skip to content](https://mise.jdx.dev/lang/dotnet.html#VPContent)

On this page

# .NET [​](https://mise.jdx.dev/lang/dotnet.html\#net)

The core .NET plugin installs .NET SDKs using Microsoft's official install script. All SDK versions are installed side-by-side under a shared `DOTNET_ROOT` directory, matching .NET's native multi-version model. This means `dotnet --list-sdks` shows every version you've installed through mise.

Unlike most tools, the SDKs don't live inside `~/.local/share/mise/installs` because they share a common root. mise symlinks its tracking path to `DOTNET_ROOT` and puts that shared installation on `PATH`. The .NET SDK resolver then chooses an SDK, using `global.json` when present. Without it, .NET normally uses the highest installed SDK; a mise version declaration alone does not isolate SDK selection in shared mode.

INFO

This plugin manages the **.NET SDK** itself. To install .NET global tools (e.g., `dotnet-ef`), use the [`dotnet` backend](https://mise.jdx.dev/dev-tools/backends/dotnet.html) with `dotnet:ToolName` syntax.

## Usage [​](https://mise.jdx.dev/lang/dotnet.html\#usage)

Install the latest SDK for the current project and inspect the shared installation:

sh

```
mise use dotnet@latest
mise exec -- dotnet --list-sdks
mise exec -- dotnet --version
```

Use `mise use -g dotnet@latest` for a personal default. To install another SDK without replacing the project's version request, use `mise install`:

sh

```
mise install dotnet@8.0.400
mise exec -- dotnet --list-sdks
```

For a project that must build with a particular SDK, configure `global.json` below, or enable [isolated mode](https://mise.jdx.dev/lang/dotnet.html#isolated-mode) before installation.

## `global.json` support [​](https://mise.jdx.dev/lang/dotnet.html\#global-json-support)

Enable discovery so mise installs the SDK declared by the project, preserving any other tools already enabled for idiomatic files:

sh

```
mise settings add idiomatic_version_file_enable_tools dotnet
```

For example, this file requests an exact SDK and disables .NET's roll-forward behavior:

json

```
{
  "sdk": {
    "version": "8.0.400",
    "rollForward": "disable"
  }
}
```

Run `mise install`, then `mise exec -- dotnet --version` from the project. mise reads `sdk.version` to install the requested SDK. .NET itself interprets `rollForward` and other SDK selection policy; see Microsoft's [`global.json` reference](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json). Do not keep a conflicting `dotnet` version in `mise.toml` if `global.json` is the project's version source.

## Isolated Mode [​](https://mise.jdx.dev/lang/dotnet.html\#isolated-mode)

By default, all SDK versions share a single `DOTNET_ROOT` directory. This matches .NET's native side-by-side model and means `dotnet --list-sdks` shows every installed version.

If you prefer the traditional mise approach where each version gets its own directory, enable isolated mode:

sh

```
mise settings set dotnet.isolated=true
```

Choose this mode before installing the versions you need. Changing the setting alone does not move existing shared installations into isolated directories.

In isolated mode each SDK version is installed under `~/.local/share/mise/installs/dotnet/<version>/`, just like most other mise-managed tools. `dotnet --list-sdks` will only report the currently active version.

|  | Shared (default) | Isolated |
| --- | --- | --- |
| `dotnet --list-sdks` | All installed versions | Active version only |
| Install location | `DOTNET_ROOT` | `installs/dotnet/<version>/` |
| Multi-targeting | Works out of the box | Requires switching versions |

## Runtime-only Installs [​](https://mise.jdx.dev/lang/dotnet.html\#runtime-only-installs)

By default, mise installs the full .NET SDK. If you only need to _run_ .NET applications, without building them or the overhead of the SDK, install just the runtime with the `runtime` inline option:

sh

```
mise use "dotnet[runtime=dotnet]@8.0.14"
mise exec -- dotnet --list-runtimes
```

### Valid runtime values [​](https://mise.jdx.dev/lang/dotnet.html\#valid-runtime-values)

| Value | Framework | Use case |
| --- | --- | --- |
| dotnet | Microsoft.NETCore.App | Console apps, libraries |
| aspnetcore | Microsoft.AspNetCore.App | ASP.NET Core web apps |
| windowsdesktop | Microsoft.WindowsDesktop.App | WPF / WinForms (Windows) |

### Example: mix SDK and runtime [​](https://mise.jdx.dev/lang/dotnet.html\#example-mix-sdk-and-runtime)

You can install a full SDK for development alongside a runtime for a production-like environment:

toml

```
[tools]
dotnet = ["9", { version = "8.0.14", runtime = "dotnet" }]
```

WARNING

- **Version numbers are runtime versions**, not SDK versions. For example, `8.0.14` refers to .NET Runtime 8.0.14, not SDK 8.0.14. Check the [.NET release notes](https://github.com/dotnet/core/tree/main/release-notes) for available runtime versions.
- Runtime-only installs do **not** include the SDK build tools. Commands like `dotnet build` and `dotnet publish` will not be available, and `dotnet --version` will not report an SDK version.

TIP

Only exact runtime versions are supported (e.g., `dotnet[runtime=dotnet]@8.0.14`). Channel syntax like `@8` is not currently supported for runtime installs, as it resolves against SDK versions rather than runtime versions.

## Tool Options [​](https://mise.jdx.dev/lang/dotnet.html\#tool-options)

The following [tool-options](https://mise.jdx.dev/dev-tools/#tool-options) are available for the `dotnet` backend. These options go in the `[tools]` section in `mise.toml`.

### `install_env` [​](https://mise.jdx.dev/lang/dotnet.html\#install-env)

Set environment variables for the .NET install script and install-time verification commands:

toml

```
[tools]
dotnet = { version = "latest", install_env = { DOTNET_CLI_TELEMETRY_OPTOUT = "1" } }
```

## Environment Variables [​](https://mise.jdx.dev/lang/dotnet.html\#environment-variables)

The plugin sets the following environment variables:

| Variable | Value |
| --- | --- |
| `DOTNET_ROOT` | Shared SDK install directory (or install path if isolated) |
| `DOTNET_MULTILEVEL_LOOKUP` | `0` |
| `DOTNET_CLI_TELEMETRY_OPTOUT` | Only set when `dotnet.cli_telemetry_optout` is configured |

## Settings [​](https://mise.jdx.dev/lang/dotnet.html\#settings)

### `dotnet.cli_telemetry_optout`

- Type: `boolean`(optional)
- Env: `MISE_DOTNET_CLI_TELEMETRY_OPTOUT`
- Default: `None`

When set to true, the `DOTNET_CLI_TELEMETRY_OPTOUT` environment variable is set to `1`,
disabling .NET CLI telemetry. When set to false, it is set to `0`.

When unset (default), mise does not set the variable and .NET uses its own default behavior.

### `dotnet.dotnet_root`

- Type: `string`(optional)
- Env: `MISE_DOTNET_ROOT`
- Default: `None`

All .NET SDK versions are installed side-by-side under this directory, matching .NET's native multi-version model.

By default, mise uses `~/.local/share/mise/dotnet-root`. Set this to override the location.

### `dotnet.isolated`

- Type: `boolean`
- Env: `MISE_DOTNET_ISOLATED`
- Default: `false`

When true, each SDK version is installed in its own directory under mise's installs path,
like most other tools. `dotnet --list-sdks` will only show the active version.

When false (default), all SDK versions share a single `DOTNET_ROOT` directory and
`dotnet --list-sdks` shows all installed versions, matching .NET's native side-by-side model.

### `dotnet.package_flags`deprecated

- Type: `string[]`
- Env: `MISE_DOTNET_PACKAGE_FLAGS`(comma separated)
- Default: `[]`
- Deprecated: Use the \`prerelease = true\` tool option or the global \`prereleases\` setting instead.

Deprecated. Use the `prerelease = true` tool option on a `dotnet:` tool, or the global
`prereleases` setting, to include pre-release versions.

This legacy setting is a list of flags to extend the search and install abilities of dotnet tools.
Because it is global, remove it before relying on `prerelease = false` per-tool opt-outs.
The only supported flag is:

- 'prerelease' : include pre-release versions in search and install

### `dotnet.registry_url`

- Type: `string`
- Env: `MISE_DOTNET_REGISTRY_URL`
- Default: `https://api.nuget.org/v3/index.json`

URL of the NuGet service index used to discover tool versions. The default is
the public [NuGet service index](https://api.nuget.org/v3/index.json).

Installation runs `dotnet tool install`, which reads its own `NuGet.Config` and
credentials. Configure a private feed there as well; this setting does not add
an installation source to the dotnet CLI.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)