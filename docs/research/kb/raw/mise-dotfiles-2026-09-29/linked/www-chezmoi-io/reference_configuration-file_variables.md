[Skip to content](https://www.chezmoi.io/reference/configuration-file/variables/#variables)

# Variables

## Top level

### cacheDir

| Type | Default |
| --- | --- |
| `string` | `$XDG_CACHE_HOME/chezmoi` / `$HOME/.cache/chezmoi` / `%USERPROFILE%/.cache/chezmoi` |

Cache directory.

### color

| Type | Default |
| --- | --- |
| `string` | `auto` |

Colorize output.

### data

| Type | Default |
| --- | --- |
| `object` | _none_ |

Template data.

### destDir

| Type | Default |
| --- | --- |
| `string` | `$HOME` / `%USERPROFILE%` |

Destination directory.

### encryption

| Type | Default |
| --- | --- |
| `string` | _none_ |

Encryption type, either `age`, `gpg`, or `transparent`.

### env

| Type | Default |
| --- | --- |
| `object` | _none_ |

Extra environment variables for scripts and commands.

### format

| Type | Default |
| --- | --- |
| `string` | `json` |

Format for data output, either `json` or `yaml`.

### interactive

| Type | Default |
| --- | --- |
| `string` | `false` |

Prompt for all changes.

### mode

| Type | Default |
| --- | --- |
| `string` | `file` |

Mode in target dir, either `file` or `symlink`.

### pager

| Type | Default |
| --- | --- |
| `string` | `$PAGER` |

Default pager CLI command.

### pagerArgs

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to the pager command.

### persistentState

| Type | Default |
| --- | --- |
| `string` | `$XDG_CONFIG_HOME/chezmoi/chezmoi.boltdb` / `$HOME/.config/chezmoi/chezmoi.boltdb` / `%USERPROFILE%/.config/chezmoi/chezmoi.boltdb` |

Location of the persistent state file.

### progress

| Type | Default |
| --- | --- |
| `bool` | `false` |

Display progress bars.

### scriptEnv

| Type | Default |
| --- | --- |
| `object` | _none_ |

Extra environment variables for scripts, hooks, and commands.

### scriptTempDir

| Type | Default |
| --- | --- |
| `string` | _none_ |

Temporary directory for scripts.

### sourceDir

| Type | Default |
| --- | --- |
| `string` | `$XDG_DATA_HOME/chezmoi` / `$HOME/.local/share/chezmoi` / `%USERPROFILE%/.local/share/chezmoi` |

Source directory.

### tempDir

| Type | Default |
| --- | --- |
| `string` | _from system_ |

Temporary directory.

### umask

| Type | Default |
| --- | --- |
| `int` | _from system_ |

Umask.

### useBuiltinAge

| Type | Default |
| --- | --- |
| `string` | `auto` |

Use builtin age if `age` command is not found in `$PATH`.

### useBuiltinGit

| Type | Default |
| --- | --- |
| `string` | `auto` |

Use builtin git if `git` command is not found in `$PATH`.

### verbose

| Type | Default |
| --- | --- |
| `bool` | `false` |

Make output more verbose.

### workingTree

| Type | Default |
| --- | --- |
| `string` | _source directory_ |

git working tree directory.

## `add`

### `add.encrypt`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Encrypt by default.

### `add.secrets`

| Type | Default |
| --- | --- |
| `string` | `warning` |

Action when secrets are found when adding files.

### `add.templateSymlinks`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Template symlinks to source and home dirs.

## `age`

### `age.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to age CLI command.

### `age.command`

| Type | Default |
| --- | --- |
| `string` | `age` |

age CLI command.

### `age.identities`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

age identity files.

### `age.identity`

| Type | Default |
| --- | --- |
| `string` | _none_ |

age identity file.

### `age.passphrase`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Use age passphrase instead of identity.

### `age.recipient`

| Type | Default |
| --- | --- |
| `string` | _none_ |

age recipient.

### `age.recipients`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

age recipients.

### `age.recipientsFile`

| Type | Default |
| --- | --- |
| `string` | _none_ |

age recipients file.

### `age.recipientsFiles`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

age recipients files.

### `age.suffix`

| Type | Default |
| --- | --- |
| `string` | `.age` |

Suffix appended to age-encrypted files.

### `age.symmetric`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Use age symmetric encryption.

## `awsSecretsManager`

### `awsSecretsManager.profile`

| Type | Default |
| --- | --- |
| `string` | _none_ |

AWS shared profile name.

### `awsSecretsManager.region`

| Type | Default |
| --- | --- |
| `string` | _none_ |

AWS region.

## `azureKeyVault`

### `azureKeyVault.defaultVault`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Default Azure Key Vault name.

## `bitwarden`

### `bitwarden.command`

| Type | Default |
| --- | --- |
| `string` | `bw` |

Bitwarden CLI command.

### `bitwarden.unlock`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Whether to unlock the Bitwarden CLI.

## `bitwardenSecrets`

### `bitwardenSecrets.command`

| Type | Default |
| --- | --- |
| `string` | `bws` |

Bitwarden Secrets CLI command.

## `cd`

### `cd.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to shell in `cd` command.

### `cd.command`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Shell to run in `cd` command.

## `completion`

### `completion.custom`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Enable custom shell completions.

## `dashlane`

### `dashlane.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to Dashlane CLI command.

### `dashlane.command`

| Type | Default |
| --- | --- |
| `string` | `dcli` |

Dashlane CLI command.

## `diff`

### `diff.args`

| Type | Default |
| --- | --- |
| `[]string` | _see [`diff`](https://www.chezmoi.io/user-guide/tools/diff/)_ |

Extra args to external diff command.

### `diff.command`

| Type | Default |
| --- | --- |
| `string` | _none_ |

External diff command.

### `diff.exclude`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Entry types to exclude from diffs.

### `diff.pager`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Diff-specific pager.

### `diff.pagerArgs`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to the diff-specific pager command.

### `diff.reverse`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Reverse order of arguments to diff.

### `diff.scriptContents`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Show script contents.

## `docker`

### `docker.command`

| Type | Default |
| --- | --- |
| `string` | `docker` |

Docker CLI command.

## `doppler`

### `doppler.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to Doppler CLI command.

### `doppler.command`

| Type | Default |
| --- | --- |
| `string` | `doppler` |

Doppler CLI command.

### `doppler.config`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Default config (aka environment) if none is specified.

### `doppler.project`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Default project name if none is specified.

## `edit`

### `edit.apply`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Apply changes on exit.

### `edit.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to edit command.

### `edit.command`

| Type | Default |
| --- | --- |
| `string` | `$EDITOR` / `$VISUAL` |

Edit command.

### `edit.hardlink`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Invoke editor with a hardlink to the source file.

### `edit.minDuration`

| Type | Default |
| --- | --- |
| `duration` | `1s` |

Minimum duration for edit command.

### `edit.watch`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Automatically apply changes when files are saved.

## `ejson`

### `ejson.key`

| Type | Default |
| --- | --- |
| `string` | _none_ |

The private key to use for decryption, will supersede using the `keyDir` if set.

### `ejson.keyDir`

| Type | Default |
| --- | --- |
| `string` | `/opt/ejson/keys` |

Path to directory containing private keys. Setting the `$EJSON_KEYDIR` environment variable will also set this value, with lower precedence.

## `git`

### `git.autoAdd`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Add changes to the source state after any change.

### `git.autoCommit`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Commit changes to the source state after any change.

### `git.autoPush`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Push changes to the source state after any change.

### `git.command`

| Type | Default |
| --- | --- |
| `string` | `git` |

git CLI command.

### `git.commitMessageTemplate`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Commit message template.

### `git.commitMessageTemplateFile`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Commit message template file (relative to source directory).

### `git.lfs`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Run `git lfs pull` after cloning.

## `gitHub`

### `gitHub.refreshPeriod`

| Type | Default |
| --- | --- |
| `duration` | `1m` |

Minimum duration between identical GitHub API requests.

## `gopass`

### `gopass.command`

| Type | Default |
| --- | --- |
| `string` | `gopass` |

gopass CLI command.

### `gopass.mode`

| Type | Default |
| --- | --- |
| `string` | _none_ |

See [gopass functions](https://www.chezmoi.io/reference/templates/gopass-functions/).

## `gpg`

### `gpg.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to GPG CLI command.

### `gpg.command`

| Type | Default |
| --- | --- |
| `string` | `gpg` |

GPG CLI command.

### `gpg.recipient`

| Type | Default |
| --- | --- |
| `string` | _none_ |

GPG recipient.

### `gpg.recipients`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

GPG recipients.

### `gpg.suffix`

| Type | Default |
| --- | --- |
| `string` | `.asc` |

Suffix appended to GPG-encrypted files.

### `gpg.symmetric`

| Type | Default |
| --- | --- |
| `bool` | `false` |

Use symmetric GPG encryption.

## `hooks`

### `hooks.` _command_`.post.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra arguments to command to run after _command_.

### `hooks.` _command_`.post.command`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Command to run after _command_.

### `hooks.` _command_`.pre.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra arguments to command to run before _command_.

### `hooks.` _command_`.pre.command`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Command to run before _command_.

## `interpreters`

### `interpreters.` _extension_.`args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

See [Interpreters](https://www.chezmoi.io/reference/configuration-file/interpreters/).

### `interpreters.` _extension_.`command`

| Type | Default |
| --- | --- |
| `string` | _special_ |

See [Interpreters](https://www.chezmoi.io/reference/configuration-file/interpreters/).

## `keepassxc`

### `keepassxc.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to KeePassXC CLI command.

### `keepassxc.command`

| Type | Default |
| --- | --- |
| `string` | `keepassxc-cli` |

KeePassXC CLI command.

### `keepassxc.database`

| Type | Default |
| --- | --- |
| `string` | _none_ |

KeePassXC database.

### `keepassxc.mode`

| Type | Default |
| --- | --- |
| `string` | `cache-password` |

See [KeePassXC functions](https://www.chezmoi.io/reference/templates/keepassxc-functions/).

### `keepassxc.prompt`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Prompt for password.

## `keeper`

### `keeper.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to Keeper CLI command.

### `keeper.command`

| Type | Default |
| --- | --- |
| `string` | `keeper` |

Keeper CLI command.

## `lastpass`

### `lastpass.command`

| Type | Default |
| --- | --- |
| `string` | `lpass` |

LastPass CLI command.

## `merge`

### `merge.args`

| Type | Default |
| --- | --- |
| `[]string` | See [`merge`](https://www.chezmoi.io/user-guide/tools/merge/) |

Extra args to three-way merge CLI command.

### `merge.command`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Three-way merge CLI command.

## `onepassword`

### `onepassword.cache`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Enable optional caching provided by `op`.

### `onepassword.command`

| Type | Default |
| --- | --- |
| `string` | `op` |

1Password CLI command.

### `onepassword.mode`

| Type | Default |
| --- | --- |
| `string` | `account` |

See [1Password Secrets Automation](https://www.chezmoi.io/user-guide/password-managers/1password/#secrets-automation).

### `onepassword.prompt`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Prompt for sign-in when no valid session is available.

## `pass`

### `pass.command`

| Type | Default |
| --- | --- |
| `string` | `pass` |

Pass CLI command.

## `passhole`

### `passhole.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to Passhole CLI command.

### `passhole.command`

| Type | Default |
| --- | --- |
| `string` | `ph` |

Passhole CLI command.

### `passhole.prompt`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Prompt for password.

## `pinentry`

### `pinentry.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to pinentry CLI command.

### `pinentry.command`

| Type | Default |
| --- | --- |
| `string` | _none_ |

pinentry CLI command.

### `pinentry.options`

| Type | Default |
| --- | --- |
| `[]string` | See [`pinentry`](https://www.chezmoi.io/reference/configuration-file/pinentry/) |

Extra options for pinentry.

## `protonPass`

### `protonPass.command`

| Type | Default |
| --- | --- |
| `string` | `pass-cli` |

Proton Pass CLI command.

## `rbw`

### `rbw.command`

| Type | Default |
| --- | --- |
| `string` | `rbw` |

Unofficial Bitwarden CLI command.

## `secret`

### `secret.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to secret CLI command.

### `secret.command`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Generic secret CLI command.

## `status`

### `status.exclude`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Entry types to exclude from status.

### `status.pathStyle`

| Type | Default |
| --- | --- |
| `string` | `relative` |

How to present the path to files in status output.

## `template`

### `template.options`

| Type | Default |
| --- | --- |
| `[]string` | `["missingkey=error"]` |

Template options.

## `textconv`

### `textconv.`

| Type | Default |
| --- | --- |
| `[]object` | _none_ |

See [textconv](https://www.chezmoi.io/reference/configuration-file/textconv/).

## `update`

### `update.apply`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Apply after pulling.

### `update.args`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Extra args to update command.

### `update.command`

| Type | Default |
| --- | --- |
| `string` | _none_ |

Update command.

### `update.recurseSubmodules`

| Type | Default |
| --- | --- |
| `bool` | `true` |

Update submodules recursively.

## `vault`

### `vault.command`

| Type | Default |
| --- | --- |
| `string` | `vault` |

Vault CLI command.

## `verify`

### `verify.exclude`

| Type | Default |
| --- | --- |
| `[]string` | _none_ |

Entry types to exclude from verify.

## `warnings`

### `warnings.`

| Type | Default |
| --- | --- |
| `object` | _none_ |

See [Warnings](https://www.chezmoi.io/reference/configuration-file/warnings/).

Back to top