[Skip to content](https://mise.jdx.dev/cli/oci.html#VPContent)

On this page

# `mise oci` [​](https://mise.jdx.dev/cli/oci.html\#mise-oci)

- **Usage:**`mise oci <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/oci/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/oci/mod.rs)

\[experimental\] Build OCI container images from a mise.toml

Each tool becomes its own OCI layer, so bumping any single tool version only invalidates one content-addressable blob — unlike a Dockerfile where changing an early `RUN` invalidates every layer above it.

This command is experimental and requires `mise settings experimental=true` (or `MISE_EXPERIMENTAL=1`). Behavior, flags, and output layout may change in future releases.

## Flags [​](https://mise.jdx.dev/cli/oci.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/oci.html\#subcommands)

- [`mise oci build [FLAGS]`](https://mise.jdx.dev/cli/oci/build.html)
- [`mise oci push [FLAGS] <REF>`](https://mise.jdx.dev/cli/oci/push.html)
- [`mise oci run [FLAGS] [-- CMD]…`](https://mise.jdx.dev/cli/oci/run.html)

## Related documentation [​](https://mise.jdx.dev/cli/oci.html\#related-documentation)

- [Building and running OCI images](https://mise.jdx.dev/dev-tools/mise-oci.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)