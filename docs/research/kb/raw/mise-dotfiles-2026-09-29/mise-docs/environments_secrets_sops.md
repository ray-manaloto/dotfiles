[Skip to content](https://mise.jdx.dev/environments/secrets/sops.html#VPContent)

On this page

# sops experimental [​](https://mise.jdx.dev/environments/secrets/sops.html\#sops)

mise reads encrypted secret files and makes values available as environment variables via `env._.file`.

- **Formats**: `.env.json`, `.env.yaml`, `.env.toml`
- **Encryption**: [sops](https://getsops.io/), using the built-in age support or the external `sops` CLI

## Choose a decryption method [​](https://mise.jdx.dev/environments/secrets/sops.html\#choose-a-decryption-method)

The default built-in implementation handles age-encrypted files. To use AWS KMS, GCP KMS, Azure Key Vault, Vault, or PGP, install the SOPS CLI, authenticate to the provider, and set `sops.rops = false` as described below.

## Encrypt with sops [​](https://mise.jdx.dev/environments/secrets/sops.html\#encrypt-with-sops)

INFO

The default `sops.rops = true` implementation supports age-encrypted files. Set `sops.rops = false` to use the external `sops` CLI for other key services and methods supported by SOPS, such as AWS KMS, GCP KMS, Azure Key Vault, Vault, and PGP.

WARNING

The external `sops` CLI does not currently support TOML input/output. mise can decrypt SOPS-encrypted `.env.toml` files only with the default `sops.rops = true` setting. If you set `sops.rops = false`, mise shells out to the `sops` CLI and encrypted TOML env files fail with a configuration error. Use `.env.json` or `.env.yaml` when you need the external CLI path.

1. Install tools and enable experimental features:

sh

```
mise use -g sops age
mise settings set experimental=true
```

2. Reuse an existing age identity, or create one if the file does not exist:

sh

```
mkdir -p ~/.config/mise
mise exec -- age-keygen -o ~/.config/mise/age.txt
# Public key: <public key>
```

3. Create `.env.json` with your values. This example uses a placeholder:

.env.json

json

```
{
  "API_TOKEN": "replace-with-your-token"
}
```

Encrypt it with the public key printed by `age-keygen`:

sh

```
mise exec -- sops encrypt -i --age "<public key>" .env.json
```

TIP

The `-i` flag replaces the plaintext file with ciphertext. Commit the encrypted file, and keep `age.txt` outside the repository. The external SOPS CLI reads `SOPS_AGE_KEY_FILE`; `MISE_SOPS_AGE_KEY_FILE` configures mise only. To edit the file:

sh

```
SOPS_AGE_KEY_FILE="$HOME/.config/mise/age.txt" mise exec -- sops .env.json
```

Age key files use the standard SOPS/age format: put one identity on each line. Blank lines and lines beginning with `#` are ignored, and all identities are tried when decrypting.

4. Reference it in config:

toml

```
[env]
_.file = { path = ".env.json", redact = true }
```

mise now decrypts the file for `mise exec`, tasks, and shell activation. `mise env` prints the plaintext values; `redact = true` does not hide that export.

## Environment Variables [​](https://mise.jdx.dev/environments/secrets/sops.html\#environment-variables)

mise supports both mise-specific environment variables and standard SOPS ones:

**mise-specific variables (highest priority):**

- `MISE_SOPS_AGE_KEY` \- Age private key content directly
- `MISE_SOPS_AGE_KEY_FILE` \- Path to age private key file

**Standard SOPS variables (fallback):**

- `SOPS_AGE_KEY_FILE` \- Path to age private key file
- `SOPS_AGE_KEY` \- Age private key content directly

**Precedence order:**

1. `MISE_SOPS_AGE_KEY` (mise setting or env var, checked first)
2. `MISE_SOPS_AGE_KEY_FILE` or `sops.age_key_file` (mise setting or env var)
3. `SOPS_AGE_KEY_FILE` (standard)
4. `SOPS_AGE_KEY` (standard, direct key content)
5. Default: `~/.config/mise/age.txt`

This allows you to override SOPS settings specifically for mise while keeping your standard SOPS configuration intact for other tools.

## Redaction [​](https://mise.jdx.dev/environments/secrets/sops.html\#redaction)

Mark secrets from files as sensitive:

toml

```
[env]
_.file = { path = ".env.json", redact = true }
```

Redaction applies to captured task output. `mise env --redacted` deliberately exports the matching secrets; it does not mask them. See [redactions](https://mise.jdx.dev/environments/#redactions) for output-mode limitations.

### CI masking (GitHub Actions) [​](https://mise.jdx.dev/environments/secrets/sops.html\#ci-masking-github-actions)

See [CI masking](https://mise.jdx.dev/environments/#ci-masking) for mise-action integration and a manual masking example that preserves whitespace and multiline values.

## Settings [​](https://mise.jdx.dev/environments/secrets/sops.html\#settings)

## `sops.age_key`

- Type: `string`(optional)
- Env: `MISE_SOPS_AGE_KEY`
- Default: `None`

The age private key to use for sops secret decryption. Takes precedence over standard SOPS\_AGE\_KEY environment variable.

## `sops.age_key_file`

- Type: `string`
- Env: `MISE_SOPS_AGE_KEY_FILE`
- Default: `~/.config/mise/age.txt`

Path to the age private key file for sops secret decryption. Takes precedence over standard SOPS\_AGE\_KEY\_FILE environment variable.

## `sops.age_recipients`

- Type: `string`(optional)
- Env: `MISE_SOPS_AGE_RECIPIENTS`
- Default: `None`

The age public keys to use for sops secret encryption.

## `sops.rops`

- Type: `boolean`
- Env: `MISE_SOPS_ROPS`
- Default: `true`

Use rops to decrypt sops files. Disable to shell out to `sops` which will slow down mise but sops may offer features not available in rops. Required for TOML SOPS files because the sops CLI does not support TOML.

## `sops.strict`

- Type: `boolean`
- Env: `MISE_SOPS_STRICT`
- Default: `true`

If true, fail when sops decryption fails (including when sops is not available, the key is missing, or the key is invalid). If false, skip decryption and continue in these cases.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)