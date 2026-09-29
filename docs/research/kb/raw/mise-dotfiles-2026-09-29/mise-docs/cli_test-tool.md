[Skip to content](https://mise.jdx.dev/cli/test-tool.html#VPContent)

On this page

# `mise test-tool` [​](https://mise.jdx.dev/cli/test-tool.html\#mise-test-tool)

- **Usage:**`mise test-tool [FLAGS] [TOOLS]…`
- **Source code:** [`src/cli/test_tool.rs`](https://github.com/jdx/mise/blob/main/src/cli/test_tool.rs)

Test that a tool installs and runs

Includes newly published releases by disabling the global minimum release age for this command.

## Arguments [​](https://mise.jdx.dev/cli/test-tool.html\#arguments)

- **`[TOOLS]…`** — Tool(s) to test

## Flags [​](https://mise.jdx.dev/cli/test-tool.html\#flags)

- **`-a --all`** — Test every tool specified in registry/

- **`-j --jobs <JOBS>`** — Number of tool tests to run in parallel Values below 1 are treated as 1 \[default: 4\]

**Environment Variable:**`MISE_TEST_TOOL_JOBS`

- **`--all-config`** — Test all tools specified in config files

- **`--include-non-defined`** — Also test tools not defined in registry/, guessing how to test them

- **`--raw`** — Connect backend install command stdin/stdout/stderr directly to the terminal. Implies `--jobs=1`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/test-tool.html\#examples)

```
mise test-tool ripgrep
```

## Related documentation [​](https://mise.jdx.dev/cli/test-tool.html\#related-documentation)

- [Contributing and registry tests](https://mise.jdx.dev/contributing.html#tool-testing).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)