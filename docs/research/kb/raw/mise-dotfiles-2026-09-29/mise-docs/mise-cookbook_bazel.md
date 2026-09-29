[Skip to content](https://mise.jdx.dev/mise-cookbook/bazel.html#VPContent)

On this page

# Bazel Cookbook [​](https://mise.jdx.dev/mise-cookbook/bazel.html\#bazel-cookbook)

Use mise to install the Bazel version declared in a project's `.bazelversion` file. This avoids repeating the version in `mise.toml`.

## Use a project's `.bazelversion` [​](https://mise.jdx.dev/mise-cookbook/bazel.html\#use-a-project-s-bazelversion)

Enable [idiomatic version files](https://mise.jdx.dev/configuration.html#idiomatic-version-files) for `bazel`:

sh

```
mise settings add idiomatic_version_file_enable_tools bazel
```

For example, a project can select Bazel 7.2.1 with this file:

.bazelversion

text

```
7.2.1
```

From that project, install the selected tools and check Bazel:

sh

```
mise install
mise exec -- bazel --version
```

Use `mise tool bazel --requested` to inspect the version request read by mise. If the project also configures Bazel in `mise.toml`, remove that duplicate entry to let `.bazelversion` select the version.

## Supported values [​](https://mise.jdx.dev/mise-cookbook/bazel.html\#supported-values)

mise reads only the first line of `.bazelversion`. It accepts concrete release versions, including release candidates and prereleases:

| Value | Read by mise? |
| --- | --- |
| `7.2.1` | Yes |
| `8.0.0rc1` | Yes |
| `5.0.0-pre.20210317.1` | Yes |
| `latest`, `latest-1`, `last_green`, `last_rc`, `rolling` | No |
| `8.x`, `8.*` | No |
| A commit hash or `<FORK>/<VERSION>` | No |

Unsupported values supply no version request, even if a later line contains a supported version. To select Bazel independently of such a file, configure it explicitly:

sh

```
mise use bazel@7.2.1
```

## Using Bazelisk instead [​](https://mise.jdx.dev/mise-cookbook/bazel.html\#using-bazelisk-instead)

Bazelisk is a launcher that reads `.bazelversion` itself and manages the corresponding Bazel installation. If your project relies on Bazelisk's version selectors, install Bazelisk with mise and let it interpret the file:

sh

```
mise use bazelisk
mise exec -- bazelisk --version
```

The version in `.bazelversion` applies to **Bazel**, not Bazelisk. Enabling idiomatic version files for `bazelisk` does not select a Bazelisk version from that file.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)