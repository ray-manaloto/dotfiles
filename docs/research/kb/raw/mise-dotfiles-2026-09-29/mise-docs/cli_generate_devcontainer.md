[Skip to content](https://mise.jdx.dev/cli/generate/devcontainer.html#VPContent)

On this page

# `mise generate devcontainer` [​](https://mise.jdx.dev/cli/generate/devcontainer.html\#mise-generate-devcontainer)

- **Usage:**`mise generate devcontainer [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/generate/devcontainer.rs`](https://github.com/jdx/mise/blob/main/src/cli/generate/devcontainer.rs)

Generate devcontainer configuration for mise

Prints JSON by default. `--write` saves .devcontainer/devcontainer.json; review the image, mounts, and generated setup commands before opening it.

## Flags [​](https://mise.jdx.dev/cli/generate/devcontainer.html\#flags)

- **`-i --image <IMAGE>`** — The image to use for the devcontainer
- **`-m --mount-mise-data`** — Bind the mise-data-volume to the devcontainer
- **`-n --name <NAME>`** — The name of the devcontainer
- **`-w --write`** — Write to .devcontainer/devcontainer.json
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/generate/devcontainer.html\#examples)

```
mise generate devcontainer
```

## Related documentation [​](https://mise.jdx.dev/cli/generate/devcontainer.html\#related-documentation)

- [IDE integration](https://mise.jdx.dev/ide-integration.html).
- [`mise generate <SUBCOMMAND>`](https://mise.jdx.dev/cli/generate.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)