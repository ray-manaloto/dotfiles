[Skip to content](https://mise.jdx.dev/dev-tools/backends/ubi.html#VPContent)

On this page

# Ubi Backend deprecated [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#ubi-backend)

WARNING

The ubi backend is **deprecated**. Use the [GitHub backend](https://mise.jdx.dev/dev-tools/backends/github.html) instead.

The GitHub backend offers several advantages over ubi, including provenance verification, download progress reports, and fewer dependencies. To migrate, replace `ubi:owner/repo` with `github:owner/repo` in your configuration files. The [`matching`](https://mise.jdx.dev/dev-tools/backends/github.html#matching) and [`matching_regex`](https://mise.jdx.dev/dev-tools/backends/github.html#matching-regex) options carry over. One behavioral difference is worth noting: ubi applies the substring `matching` only as a tiebreaker among assets that already match your OS/arch, and skips it when a single asset matches the platform. The GitHub backend applies `matching` as a pre-filter before autodetection, so for multi-binary releases you get the binary your filter names, or a clear error naming the filter if it isn't published for your platform.

One migration gotcha: ubi folds `matching` into the install path, so you can install several binaries from one repo via separate `matching` values on the same `ubi:owner/repo` string. The GitHub backend keeps the install path keyed by tool name + version only, so two `github:owner/repo` entries with different `matching` values resolve to the **same** directory and the second overwrites the first. If you rely on that ubi pattern, give each binary its own [`tool_alias`](https://mise.jdx.dev/dev-tools/backends/github.html#multiple-assets-from-the-same-release) on GitHub so each gets its own install directory.

This page documents existing ubi configurations. For new installations, use the [GitHub](https://mise.jdx.dev/dev-tools/backends/github.html), [GitLab](https://mise.jdx.dev/dev-tools/backends/gitlab.html), or [HTTP](https://mise.jdx.dev/dev-tools/backends/http.html) backend as appropriate.

## Usage [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#usage)

Migrate one tool at a time. For a simple release install, change:

toml

```
[tools]
"ubi:BurntSushi/ripgrep" = "14.1.1"
```

To:

toml

```
[tools]
"github:BurntSushi/ripgrep" = "14.1.1"
```

Then run `mise install` and `mise exec -- rg --version`. Check custom options against the destination backend: for example, `exe` and `extract_all` are ubi options and should not be copied blindly. Regenerate and review any lockfile. Keep the old installation until the replacement works.

For multiple binaries, follow the alias migration described above. A direct `ubi:https://...` download belongs in an [HTTP tool entry](https://mise.jdx.dev/dev-tools/backends/http.html#usage).

## Tool Options [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#tool-options)

The following [tool-options](https://mise.jdx.dev/dev-tools/#tool-options) are available for the `ubi` backend—these go in `[tools]` in `mise.toml`.

### `exe` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#exe)

The `exe` option allows you to specify the executable name in the archive. This is useful when the archive contains multiple executables.

If you get an error like `could not find any files named cli in the downloaded zip file`, you can use the `exe` option to specify the executable name:

toml

```
[tools]
"ubi:cli/cli" = { version = "latest", exe = "gh" } # github's cli
```

### `rename_exe` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#rename-exe)

The `rename_exe` option allows you to specify the name of the executable once it has been extracted.

Use the `rename_exe` option to specify the target executable name:

toml

```
[tools]
"ubi:cli/cli" = { version = "latest", exe = "gh", rename_exe = "github" } # github's cli
```

### `matching` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#matching)

Set a string to match against the release filename when there are multiple files for your OS/arch, e.g. "gnu", "musl", or "msvc". This is only used when more than one release filename matches your OS/arch; if only one release asset matches, the option is ignored.

toml

```
[tools]
"ubi:BurntSushi/ripgrep" = { version = "latest", matching = "musl" }
```

### `matching_regex` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#matching-regex)

Set a regular expression to match against release filenames before matching against OS/arch. If the pattern yields a single match, that file is selected. If nothing matches, ubi reports an error.

toml

```
[tools]
"ubi:shader-slang/slang" = { version = "latest", matching_regex = "\\d+\\.tar" }
```

### `provider` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#provider)

Set the provider used to fetch assets and release information: either `github` or `gitlab` (default `github`). Set `provider` explicitly when you use `api_url`, since the type probably cannot be derived correctly from the URL.

toml

```
[tools]
"ubi:gitlab-org/cli" = { version = "latest", exe = "glab", provider = "gitlab" }
```

### `api_url` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#api-url)

Set the URL for the provider's API. This is useful when using a self-hosted instance.

toml

```
[tools]
"ubi:acme/my-tool" = {
  version = "latest",
  provider = "gitlab",
  api_url = "https://gitlab.acme.com/api/v4",
}
```

### `extract_all` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#extract-all)

Set to `true` to extract all files in the tarball instead of only the binary. Not compatible with `exe` or `rename_exe`.

toml

```
[tools]
"ubi:helix-editor/helix" = { version = "latest", extract_all = true }
```

### `bin_path` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#bin-path)

The directory in the tarball containing the binaries. This is useful when the binary is not at the root of the tarball, and it only makes sense when `extract_all` is set to `true`.

toml

```
[tools]
"ubi:owner/repo" = {
  version = "latest",
  extract_all = true,
  bin_path = "target/release", # match the archive's actual layout
}
```

**Binary path lookup order:**

1. If `bin_path` is specified, use that directory
2. If `extract_all` is set to `true`, use the install path root
3. If `bin_path` is not set, look for a `bin/` directory in the install path
4. If no `bin/` directory exists, use the root of the extracted directory

### `tag_regex` [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#tag-regex)

Set a regex to filter out tags that don't match it. This is useful when a vendor publishes releases for unrelated CLIs in the same repo. For example, `cargo-bins/cargo-binstall` has many releases for CLIs other than `cargo-binstall`; this option filters those releases out.

toml

```
[tools]
"ubi:cargo-bins/cargo-binstall" = { version = "latest", tag_regex = '^\d+\.' }
```

## Self-hosted GitHub/GitLab [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#self-hosted-github-gitlab)

If you are using a self-hosted GitHub/GitLab instance, you can set the `provider` and `api_url` tool options. Additionally, you can set the `MISE_GITHUB_ENTERPRISE_TOKEN` or `MISE_GITLAB_ENTERPRISE_TOKEN` environment variable to authenticate with the API.

## Supported Ubi Syntax [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#supported-ubi-syntax)

- **GitHub shorthand for latest release version:**`ubi:goreleaser/goreleaser`
- **GitHub shorthand for specific release version:**`ubi:goreleaser/goreleaser@1.25.1`
- **URL syntax:**`ubi:https://github.com/goreleaser/goreleaser/releases/download/v1.16.2/goreleaser_Darwin_arm64.tar.gz`

## Troubleshooting ubi [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#troubleshooting-ubi)

### `ubi` resolver can't find os/arch [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#ubi-resolver-can-t-find-os-arch)

Sometimes vendors name their releases in ways ubi can't figure out, possibly only for a specific OS/arch combination. For example, in [this ticket](https://github.com/houseabsolute/ubi/issues/79) a vendor used "mac" instead of the more common "macos" or "darwin" tags.

For an existing ubi install, compare with a separately installed ubi CLI if you need to isolate its resolver. Run this in an empty scratch directory:

sh

```
ubi -p jdx/mise
./bin/mise --version
```

### `ubi` picks the wrong tarball [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#ubi-picks-the-wrong-tarball)

A GitHub release may have many tarballs, some of which don't contain the CLI you want. Use the `matching` field to specify a string to match against the release filenames.

sh

```
mise use 'ubi:tamasfe/taplo[matching=full]'
# or with ubi directly
ubi -p tamasfe/taplo -m full
```

### `ubi` can't find the binary in the tarball [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#ubi-can-t-find-the-binary-in-the-tarball)

ubi assumes the repo name is the same as the binary name, but that is often not the case. For example, BurntSushi/ripgrep provides a binary named `rg`, not `ripgrep`. In this case, specify the binary name with the `exe` field:

sh

```
mise use 'ubi:BurntSushi/ripgrep[exe=rg]'
# or with ubi directly
ubi -p BurntSushi/ripgrep -e rg
```

### `ubi` uses weird versions [​](https://mise.jdx.dev/dev-tools/backends/ubi.html\#ubi-uses-weird-versions)

This issue is with mise, not ubi. mise needs to list the available versions of a tool so that "latest" points to the actual latest release of the CLI. Sometimes vendors publish GitHub releases for unrelated things. For example, `cargo-bins/cargo-binstall` is the repo for cargo-binstall, but it also has many releases for unrelated CLIs. Filter these out with the `tag_regex` tool option:

sh

```
mise use 'ubi:cargo-bins/cargo-binstall[tag_regex=^\d+\.]'
```

Now when running `mise ls-remote ubi:cargo-bins/cargo-binstall[tag_regex=^\d+\.]` you should only see versions starting with a number. This command's output is cached, so you will likely need to run `mise cache clear` first.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)