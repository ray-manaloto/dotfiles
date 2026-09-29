[Skip to content](https://fnox.jdx.dev/#VPContent)

# Secret management for development and CI

Load secrets from encrypted files, password managers, and cloud services into your application’s environment. Configure where each value comes from in `fnox.toml`.

[Get started ↗](https://fnox.jdx.dev/guide/quick-start) [Find your provider →](https://fnox.jdx.dev/providers/overview)

$`mise use -g fnox` Copy

Open source · MIT licensed · Built in Rust

![](https://fnox.jdx.dev/logo.svg) fnox.toml

COMMIT THE CONFIG

Vault references  Encrypted in git

```
# Connect the vault you already use
[providers.op]
type = "1password"
vault = "Engineering"

[secrets.DATABASE_URL]
provider = "op"
value = "Database/url"
```

```
# fnox set writes the ciphertext for you
[providers.age]
type = "age"
recipients = ["age1…"]

[secrets.DATABASE_URL]
provider = "age"
value = "YWdlLWVuY3J5cHRpb24…"
```

RUN WITH SECRETS

```
$ fnox exec -- npm start
```

↳ DATABASE\_URL is available to your app.

Commit the vault reference without putting the secret value in git.

SUPPORTED PROVIDERS

[age](https://fnox.jdx.dev/providers/age) [1Password](https://fnox.jdx.dev/providers/1password) [AWS](https://fnox.jdx.dev/providers/aws-sm) [Azure](https://fnox.jdx.dev/providers/azure-sm) [Google Cloud](https://fnox.jdx.dev/providers/gcp-sm) [Bitwarden](https://fnox.jdx.dev/providers/bitwarden) [Vault](https://fnox.jdx.dev/providers/vault) [All providers →](https://fnox.jdx.dev/providers/overview)

## Choose where secrets are stored

Each secret can use a different provider, so you can combine encrypted values with references to your team’s existing vaults.

[01 / ENCRYPT **Encrypted values in git**\\
Encrypt with age, a hardware key, or cloud KMS. Review configuration alongside your code and share access through public recipients or provider permissions. \\
Start with age ↗](https://fnox.jdx.dev/guide/quick-start) [02 / CONNECT **Existing vaults**\\
Reference the secrets your team already manages. Add a personal encrypted cache with fnox sync for local, offline access using age. \\
Connect a vault ↗](https://fnox.jdx.dev/guide/golden-path) [03 / RUN **Environment profiles**\\
Use profiles for development, staging, and production. Change the secret source without changing the way you launch your application. \\
Work with profiles ↗](https://fnox.jdx.dev/guide/profiles)

## Use secrets in your workflow

Load secrets when you enter a project, cache repeated reads, or issue temporary credentials when a service supports them.

[See how fnox works →](https://fnox.jdx.dev/guide/how-it-works)

[**Shell integration**\\
\\
Shell hooks load and unload values as you move between projects. \\
\\
↗](https://fnox.jdx.dev/guide/shell-integration) [**In-memory caching**\\
\\
An opt-in daemon keeps resolved values in memory during your session. \\
\\
↗](https://fnox.jdx.dev/guide/daemon) [**Temporary credentials**\\
\\
Create temporary credentials with AWS STS, GitHub Apps, Vault, and more. \\
\\
↗](https://fnox.jdx.dev/guide/leases) [**Credentials for agent requests**\\
\\
Pass placeholders to an agent and inject real values into matching HTTPS requests. \\
\\
↗](https://fnox.jdx.dev/guide/proxy)

![](https://fnox.jdx.dev/logo.svg)

## Set up your first provider

Install fnox, configure a provider, and run your first command.

[Follow the quick start →](https://fnox.jdx.dev/guide/quick-start)

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)