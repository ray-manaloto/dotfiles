[Skip to content](https://mise.jdx.dev/environments/secrets/age.html#VPContent)

On this page

# Direct age Encryption experimental [​](https://mise.jdx.dev/environments/secrets/age.html\#direct-age-encryption)

Encrypt individual environment variable values directly in `mise.toml` using [age](https://github.com/FiloSottile/age) encryption. Encryption and decryption are built into mise. The optional `age-keygen` command below comes from the separate age CLI.

This is a simple way to store encrypted environment variables directly in `mise.toml`. Run `mise set --age-encrypt <key>=<value>` to use it. By default, mise uses your SSH key (`~/.ssh/id_ed25519` or `~/.ssh/id_rsa`) if one exists.

- **Inline storage**: values live alongside other env vars in `mise.toml`
- **Multiple recipients**: x25519 age keys and SSH recipients
- **Automatic decryption**: at runtime when identities are available

## Quick start [​](https://mise.jdx.dev/environments/secrets/age.html\#quick-start)

1. Enable experimental features:

bash

```
mise settings set experimental=true
```

2. Use an existing SSH identity, or install age and generate a dedicated identity. Skip key generation if `age.txt` already contains an identity you want to keep:

bash

```
mise use -g age
mkdir -p ~/.config/mise
mise exec -- age-keygen -o ~/.config/mise/age.txt
# Public key: age1...
```

The public key is a **recipient**: share it with people who need to encrypt for you. `age.txt` contains the private **identity** needed to decrypt; keep it outside the repository.

3. Encrypt a value:

bash

```
mise set --age-encrypt --prompt DB_PASSWORD
# Enter value for DB_PASSWORD: [hidden input]
```

WARNING

Use `--prompt` so the plaintext does not become part of the command or shell history.

4. Values are stored encrypted in `mise.toml` as an age directive:

toml

```
[env]
DB_PASSWORD = { age = { value = "<base64>" } }
```

5. Run a command or task that needs the value. mise decrypts it before starting the process:

bash

```
# Bash example: checks availability without printing the password
mise exec -- bash -c 'test -n "$DB_PASSWORD" && echo "DB_PASSWORD is available"'
```

`mise env` and `mise set DB_PASSWORD` print the decrypted value. Use them only when that plaintext output is intended; see [redaction](https://mise.jdx.dev/environments/#redactions).

## CLI flags [​](https://mise.jdx.dev/environments/secrets/age.html\#cli-flags)

- `--age-encrypt` — enable age encryption for the value
- `--age-recipient <KEY>` — x25519 recipient (can be set multiple times)
- `--age-ssh-recipient <PATH|KEY>` — SSH public key or path to `.pub`/private key (can be set multiple times)
- `--age-key-file <PATH>` — use recipients derived from an age identity file
- `--prompt` — prompt for the value to avoid accidentally exposing it to your shell history

If no recipients are provided explicitly, mise tries the defaults (see below).

## Storage format [​](https://mise.jdx.dev/environments/secrets/age.html\#storage-format)

The stored payload is base64-encoded ciphertext, not an encoded plaintext secret. The `format` field identifies the payload representation:

- `format = "raw"` — uncompressed ciphertext (typically for small values)
- `format = "zstd"` — zstd-compressed ciphertext (used when ciphertext > 1KB)

## Decryption identities [​](https://mise.jdx.dev/environments/secrets/age.html\#decryption-identities)

mise looks for identities in this order:

1. `MISE_AGE_KEY`environment variable
   - Can contain one or more raw `AGE-SECRET-KEY-...` lines, or an age identity file payload
2. `settings.age.identity_files` (list of paths)
3. `settings.age.key_file` (single path)
4. Default `~/.config/mise/age.txt` if it exists
5. SSH identities from `settings.age.ssh_identity_files` and common defaults (`~/.ssh/id_ed25519`, `~/.ssh/id_rsa`)

Paths configured in `settings.age.key_file`, `settings.age.identity_files`, and `settings.age.ssh_identity_files` are resolved relative to the config root of the file that declares them. They also support Tera templates, including `{{ config_root }}` and values from `env`. Absolute paths and paths beginning with `~` keep their existing meaning.

Decrypted values are always marked as redacted.

Age decryption is strict by default. If no identities are found, no available identity can decrypt the value, or the age payload is invalid, mise fails instead of continuing with a partially resolved environment.

To allow commands and tasks to continue when an age value cannot be decrypted, disable strict mode:

bash

```
mise settings set age.strict=false
```

In non-strict mode, mise skips values that cannot be decrypted and continues resolving the rest of the environment.

## Defaults for recipients (encryption) [​](https://mise.jdx.dev/environments/secrets/age.html\#defaults-for-recipients-encryption)

When `--age-encrypt` is used without explicit recipients, mise attempts to derive recipients from:

- The public keys corresponding to identities in the default key file `~/.config/mise/age.txt`
- Public keys inferred from SSH private keys if a corresponding `.pub` file exists

If none are found, the command fails with an error asking you to provide recipients or configure `settings.age.key_file`.

## Settings [​](https://mise.jdx.dev/environments/secrets/age.html\#settings)

## `age.identity_files`

- Type: `string[]`(optional)
- Env: `MISE_AGE_IDENTITY_FILES`
- Default: `None`

List of age identity files to use for decryption (encrypted shared dotfiles and the experimental `[env]` age directives).

## `age.key_file`

- Type: `string`
- Env: `MISE_AGE_KEY_FILE`
- Default: `~/.config/mise/age.txt`

Path to the age private key file to use for encryption/decryption: the default recipient and identity for encrypted shared dotfiles and the key for the experimental `[env]` age directives.

## `age.ssh_identity_files`

- Type: `string[]`(optional)
- Env: `MISE_AGE_SSH_IDENTITY_FILES`
- Default: `None`

List of SSH identity files to use for age decryption (encrypted shared dotfiles and the experimental `[env]` age directives).

## `age.strict`

- Type: `boolean`
- Env: `MISE_AGE_STRICT`
- Default: `true`

If true, fail when age decryption fails (including when age is not available, the key is missing, or the key is invalid). If false, skip decryption and continue in these cases.

## Notes [​](https://mise.jdx.dev/environments/secrets/age.html\#notes)

- This feature is experimental; flags and behavior may change.
- `mise set KEY` prints the decrypted value.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)