[Skip to content](https://mise.jdx.dev/cli/skills.html#VPContent)

On this page

# `mise skills` [​](https://mise.jdx.dev/cli/skills.html\#mise-skills)

- **Usage:**`mise skills [SUBCOMMAND]`
- **Aliases:**`skill`
- **Effect:** read-only
- **Source code:** [`src/cli/skills/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/skills/mod.rs)

Agent skills the active tools ship, from their packslips

A tool installed with the `packslip:` backend may declare an agent skill: a directory holding `SKILL.md` and whatever it references, in the Agent Skills format. mise knows which version of each tool is active here, so it can hand an agent the skill for exactly that version.

## Flags [​](https://mise.jdx.dev/cli/skills.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/skills.html\#subcommands)

- [`mise skills ls [-J --json]`](https://mise.jdx.dev/cli/skills/ls.html)
- [`mise skills sync [FLAGS]`](https://mise.jdx.dev/cli/skills/sync.html)

## Related documentation [​](https://mise.jdx.dev/cli/skills.html\#related-documentation)

- [Skills and other Packslip resources](https://mise.jdx.dev/dev-tools/packslip-resources.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)