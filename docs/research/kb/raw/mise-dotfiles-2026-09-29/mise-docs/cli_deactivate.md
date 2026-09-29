[Skip to content](https://mise.jdx.dev/cli/deactivate.html#VPContent)

On this page

# `mise deactivate` [​](https://mise.jdx.dev/cli/deactivate.html\#mise-deactivate)

- **Usage:**`mise deactivate`
- **Effect:** read-only
- **Source code:** [`src/cli/deactivate.rs`](https://github.com/jdx/mise/blob/main/src/cli/deactivate.rs)

Print the script to disable mise in the current shell session

The shell function installed by activation evaluates this output in supported shells. When calling the executable directly, evaluate or source its output with the appropriate shell syntax. This does not remove the startup-file line; new shells will activate mise again.

## Flags [​](https://mise.jdx.dev/cli/deactivate.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/deactivate.html\#examples)

Bash or Zsh, calling the executable rather than the activation function

```
eval "$(command mise deactivate)"
```

Fish

```
command mise deactivate | source
```

## Related documentation [​](https://mise.jdx.dev/cli/deactivate.html\#related-documentation)

- [Shell activation](https://mise.jdx.dev/getting-started.html#activate-mise).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)