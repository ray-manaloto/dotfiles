[Skip to content](https://mise.jdx.dev/cli/env.html#VPContent)

On this page

# `mise env` [​](https://mise.jdx.dev/cli/env.html\#mise-env)

- **Usage:**`mise env [FLAGS] [TOOL@VERSION]…`
- **Aliases:**`e`
- **Effect:** read-only
- **Source code:** [`src/cli/env.rs`](https://github.com/jdx/mise/blob/main/src/cli/env.rs)

Print the environment for the current configuration

Evaluate the shell output to load tools and variables once, without installing prompt hooks. Changing directories afterward does not recompute this environment. Use `mise exec -- command` to apply it to one child process instead.

JSON, dotenv, and shell output contain actual variable values, including secrets. `--redacted` selects variables marked for redaction; it does not mask their values. Environment construction may install missing tools according to mise's settings.

## Arguments [​](https://mise.jdx.dev/cli/env.html\#arguments)

- **`[TOOL@VERSION]…`** — Tool(s) to include in addition to those in config, e.g. node@20

## Flags [​](https://mise.jdx.dev/cli/env.html\#flags)

- **`-D --dotenv`** — Output in dotenv format

- **`-J --json`** — Output in JSON format

- **`-s --shell <SHELL>`** — Shell type to generate environment variables for

**Choices:**`bash`, `elvish`, `fish`, `nu`, `xonsh`, `zsh`, `pwsh`, `powershell`

- **`--json-extended`** — Output in JSON format with additional information (source, tool)

- **`--redacted`** — Only include variables marked for redaction; their values are printed unmasked

- **`--values`** — Only show values of environment variables

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/env.html\#examples)

```
eval "$(mise env -s bash)"
eval "$(mise env -s zsh)"
mise env -s fish | source
execx($(mise env -s xonsh))
```

## Related documentation [​](https://mise.jdx.dev/cli/env.html\#related-documentation)

- [Environment variables](https://mise.jdx.dev/environments/).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)