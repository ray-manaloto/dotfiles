[Skip to content](https://mise.jdx.dev/cli/generate/github-action.html#VPContent)

On this page

# `mise generate github-action` [​](https://mise.jdx.dev/cli/generate/github-action.html\#mise-generate-github-action)

- **Usage:**`mise generate github-action [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/generate/github_action.rs`](https://github.com/jdx/mise/blob/main/src/cli/generate/github_action.rs)

Generate a GitHub Action workflow file

This command generates a GitHub Action workflow file that runs a mise task like `mise run ci` on pull requests, tags, manual dispatch, and pushes to the current Git branch. Prints YAML by default; `--write` saves it under .github/workflows. Define the selected task and review the generated triggers before committing.

## Flags [​](https://mise.jdx.dev/cli/generate/github-action.html\#flags)

- **`-t --task <TASK>`** — The task to run when the workflow is triggered

**Default:**`ci`

- **`-w --write`** — Write to .github/workflows/$name.yml

- **`--name <NAME>`** — The name of the workflow to generate

**Default:**`ci`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/generate/github-action.html\#examples)

Preview before writing the workflow

```
mise generate github-action --task=ci
mise generate github-action --write --task=ci
git add .github/workflows/ci.yml
```

## Related documentation [​](https://mise.jdx.dev/cli/generate/github-action.html\#related-documentation)

- [Continuous integration](https://mise.jdx.dev/continuous-integration.html).
- [`mise generate <SUBCOMMAND>`](https://mise.jdx.dev/cli/generate.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)