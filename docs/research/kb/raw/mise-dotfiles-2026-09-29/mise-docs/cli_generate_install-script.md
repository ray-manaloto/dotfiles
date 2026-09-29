[Skip to content](https://mise.jdx.dev/cli/generate/install-script.html#VPContent)

On this page

# `mise generate install-script` [​](https://mise.jdx.dev/cli/generate/install-script.html\#mise-generate-install-script)

- **Usage:**`mise generate install-script [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/generate/install_script.rs`](https://github.com/jdx/mise/blob/main/src/cli/generate/install_script.rs)

Generate a script to download+execute mise

This is designed to be used in a project where contributors may not have mise installed.

Renamed from `mise generate bootstrap`, which read as a form of `mise bootstrap` (machine setup). The old name still works but is deprecated and will be removed in mise 2027.9.0.

## Flags [​](https://mise.jdx.dev/cli/generate/install-script.html\#flags)

- **`-l --localize`** — Keep mise data and cache in a project-local directory (`.mise` by default)

Use `--localized-dir` to choose its location. This isolates mise state; it is not an OS sandbox for commands the generated script runs.

- **`-V --version <VERSION>`** — Specify mise version to fetch

- **`-w --write [WRITE]`** — Write the script to a file and make it executable instead of printing it to stdout

- **`--localized-dir <LOCALIZED_DIR>`** — Directory to put localized data into

**Default:**`.mise`

- **`--windows`** — Also write a Windows launcher, `<WRITE>.cmd`

Windows cannot execute the `#!/usr/bin/env bash` script, so a contributor who clones the project on Windows has nothing to run without this.

Generated on every host, not only on Windows: the file is committed, and whoever runs it on Windows is not the person who generated it. Requires `--write`, since stdout cannot carry two files.

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/generate/install-script.html\#examples)

Download mise to .mise if it is not already installed.

```
mise generate install-script --write ./bin/mise
./bin/mise install
```

Write bin/mise.cmd as a launcher for contributors who clone the project on Windows.

```
mise generate install-script --write ./bin/mise --windows
.\bin\mise.cmd install
```

## Related documentation [​](https://mise.jdx.dev/cli/generate/install-script.html\#related-documentation)

- [Project installation scripts](https://mise.jdx.dev/dev-tools/).
- [`mise generate <SUBCOMMAND>`](https://mise.jdx.dev/cli/generate.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)