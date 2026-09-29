[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/brew/untap.html#VPContent)

On this page

# `mise bootstrap packages brew untap` [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/untap.html\#mise-bootstrap-packages-brew-untap)

- **Usage:**`mise bootstrap packages brew untap [FLAGS] <TAPS>…`
- **Aliases:**`remove`, `rm`
- **Effect:** modifies state
- **Source code:** [`src/cli/system/brew/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/brew/mod.rs)

Remove Homebrew tap URLs from \[bootstrap.brew.taps\]

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/untap.html\#arguments)

- **`<TAPS>…`** — Tap name(s), e.g. `owner/repo`

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/untap.html\#flags)

- **`-l --local`** — Write to the local config instead of the global config

- **`-n --dry-run`** — Print the config change without writing it

- **`-p --path <PATH>`** — Write to this config file or directory

**Aliases:**`--file`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/untap.html\#examples)

```
mise bootstrap packages brew untap railwaycat/emacsmacport
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/untap.html\#related-documentation)

- [Homebrew packages and taps](https://mise.jdx.dev/bootstrap/packages/brew.html).
- [`mise bootstrap packages brew <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages/brew.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).