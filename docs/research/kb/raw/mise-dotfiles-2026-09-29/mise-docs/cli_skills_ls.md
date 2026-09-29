[Skip to content](https://mise.jdx.dev/cli/skills/ls.html#VPContent)

On this page

# `mise skills ls` [​](https://mise.jdx.dev/cli/skills/ls.html\#mise-skills-ls)

- **Usage:**`mise skills ls [-J --json]`
- **Aliases:**`list`
- **Effect:** read-only
- **Source code:** [`src/cli/skills/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/skills/ls.rs)

List the skills the active tools declare

Each line is a skill of a tool that is installed and active in the current directory, with the version it belongs to and the directory holding its `SKILL.md`.

## Flags [​](https://mise.jdx.dev/cli/skills/ls.html\#flags)

- **`-J --json`** — Output in JSON format
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/skills/ls.html\#examples)

```
mise skills ls
Skill  Tool                        Version  Path
mise   packslip:github.com/jdx/mise  2026.9.1  ~/.local/share/mise/installs/.../skills/mise
```

## Related documentation [​](https://mise.jdx.dev/cli/skills/ls.html\#related-documentation)

- [Skills and other Packslip resources](https://mise.jdx.dev/dev-tools/packslip-resources.html).
- [`mise skills [SUBCOMMAND]`](https://mise.jdx.dev/cli/skills.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)