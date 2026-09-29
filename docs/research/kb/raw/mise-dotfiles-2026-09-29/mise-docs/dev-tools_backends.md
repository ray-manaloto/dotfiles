[Skip to content](https://mise.jdx.dev/dev-tools/backends/#VPContent)

On this page

# Backends [​](https://mise.jdx.dev/dev-tools/backends/\#backends)

A backend tells mise where to find a tool's versions and how to install them. Use a registry shorthand such as `ripgrep` for the default selection, or specify a backend explicitly, such as `github:BurntSushi/ripgrep`.

## Choose an installation source [​](https://mise.jdx.dev/dev-tools/backends/\#choose-an-installation-source)

Start by checking the [registry](https://mise.jdx.dev/registry.html):

sh

```
mise registry ripgrep
mise ls-remote ripgrep
mise use ripgrep
mise exec -- rg --version
```

`mise use` installs the tool and records it in the project's `mise.toml`. Add `-g` for your global configuration. You can use an explicit backend even when a tool has no registry shorthand; a registry submission is not required.

| Source | Backends | What to check |
| --- | --- | --- |
| Signed publisher manifests | [Packslip](https://mise.jdx.dev/dev-tools/backends/packslip.html) | The publisher must provide Packslip releases and a verifiable signer. |
| Curated binary recipes | [Aqua](https://mise.jdx.dev/dev-tools/backends/aqua.html) | The aqua registry must have an entry for the tool and platform. No aqua CLI is required. |
| Release assets | [GitHub](https://mise.jdx.dev/dev-tools/backends/github.html), [GitLab](https://mise.jdx.dev/dev-tools/backends/gitlab.html), [Forgejo](https://mise.jdx.dev/dev-tools/backends/forgejo.html) | Releases must include an installable asset for your platform. |
| Direct downloads | [HTTP](https://mise.jdx.dev/dev-tools/backends/http.html), [S3](https://mise.jdx.dev/dev-tools/backends/s3.html) | Supply download URLs and, for version discovery, a version source. |
| Language packages | [Cargo](https://mise.jdx.dev/dev-tools/backends/cargo.html), [Go](https://mise.jdx.dev/dev-tools/backends/go.html), [npm](https://mise.jdx.dev/dev-tools/backends/npm.html), [pipx](https://mise.jdx.dev/dev-tools/backends/pipx.html), [gem](https://mise.jdx.dev/dev-tools/backends/gem.html), [.NET](https://mise.jdx.dev/dev-tools/backends/dotnet.html), [Swift Package Manager](https://mise.jdx.dev/dev-tools/backends/spm.html) | Read the backend's runtime and build prerequisites. |
| Binary package ecosystems | [Conda](https://mise.jdx.dev/dev-tools/backends/conda.html) | Packages and their runtime dependencies must support your platform. |
| Plugin-defined installation | [vfox](https://mise.jdx.dev/dev-tools/backends/vfox.html), [asdf](https://mise.jdx.dev/dev-tools/backends/asdf.html) (legacy) | Review the plugin and its dependencies before installation. |
| Legacy release installer | [ubi](https://mise.jdx.dev/dev-tools/backends/ubi.html) (deprecated) | Migrate existing configurations to the appropriate release backend. |

Built-in language support is documented in the [language guides](https://mise.jdx.dev/lang/node.html). Plugin authors can also create [custom backends](https://mise.jdx.dev/backend-plugin-development.html) that manage a family of tools.

## Verify the result [​](https://mise.jdx.dev/dev-tools/backends/\#verify-the-result)

A listed version does not guarantee that its publisher ships an artifact for your OS and architecture. Check installation and the actual executable with `mise exec -- <command> --version`. If selection fails, the backend's guide explains its asset names, authentication, and platform options.

For reproducible installations, record concrete versions and supported-platform checksums in [mise.lock](https://mise.jdx.dev/dev-tools/mise-lock.html). Verification coverage differs by backend; see [security](https://mise.jdx.dev/security.html) and the individual guide before relying on a particular signature or provenance check.

See [backend architecture](https://mise.jdx.dev/dev-tools/backend_architecture.html) for selection, installation dependencies, and the implementation lifecycle.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)