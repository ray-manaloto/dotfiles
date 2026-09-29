[Skip to content](https://jdx.dev/posts/2026-03-02-10-mise-features/#main)

On this page

## 1\. Task `sources` and `outputs` [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#1-task-sources-and-outputs)

Any task can declare input/output globs. If all outputs are newer than all sources, the task is skipped entirely:

```toml
[tasks.build]
run = "cargo build"
sources = ["Cargo.toml", "src/**/*.rs"]
outputs = ["target/debug/myapp"]
```

Don’t want to enumerate outputs? Set `outputs = { auto = true }` (which is actually the default when `sources` is defined) — mise tracks a hash internally and skips the task if sources haven’t changed.

## 2\. The `github`, `http`, and `s3` backends [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#2-the-github-http-and-s3-backends)

The `github` backend installs tools directly from GitHub releases. It infers the right asset for your platform automatically — just point it at a repo and it usually works:

```toml
[tools]
"github:BurntSushi/ripgrep" = "latest"
```

For more complex setups (non-standard naming, multiple binaries, etc.), the aqua registry is a better choice for open-source tools — it has hand-written manifests for hundreds of tools with full platform mapping. The `github` backend is best for quick one-offs and private/internal tools.

The `http` backend goes further — install any binary from any URL with templated platform variables:

```toml
[tools."http:my-internal-tool"]
version = "2.1.0"
url = 'https://artifacts.internal.co/tool-v{{version}}-{{os(macos="darwin")}}-{{arch(x64="amd64")}}.tar.gz'
```

The `s3` backend \[experimental\] does the same for S3 or S3-compatible storage (MinIO, etc.):

```toml
[tools."s3:my-tool"]
version = "1.0.0"
url = "s3://my-bucket/tools/my-tool-v{{ version }}.tar.gz"
endpoint = "http://minio.internal:9000"
```

Great for internal artifact servers, private buckets, or anything with a download link.

## 3\. Tool stubs [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#3-tool-stubs)

Inspired by Meta’s [dotslash](https://dotslash-cli.com/), tool stubs are self-contained scripts that auto-download and execute tools on first run. Check them into your repo and anyone can run them — they just need mise:

```bash
#!/usr/bin/env -S mise tool-stub
version = "20.0.0"
tool = "node"
bin = "node"
```

Generate them with `mise generate tool-stub`. Add `--lock` to embed platform-specific URLs and checksums for fully reproducible installs. Add `--bootstrap` to create a wrapper that installs mise itself if missing. You can also use the `http` backend style for custom binaries — no registry entry needed.

## 4\. Typed task arguments with `usage` [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#4-typed-task-arguments-with-usage)

Tasks can have real CLI arguments with validation, choices, defaults, and auto-generated help:

```toml
[tasks.deploy]
usage = '''
arg "<environment>" help="Target env" { choices "dev" "staging" "prod" }
flag "-v --verbose" help="Verbose output"
flag "--region <region>" default="us-east-1"
'''
run = 'deploy.sh ${usage_environment} --region ${usage_region}'
```

`mise run deploy --help` prints a proper help page. Tab completion works out of the box — including completing argument values from `choices` or dynamic `complete` handlers. Adding autocompletion for custom values is as simple as:

```fallback
complete "environment" run="mise plugins ls"
```

## 5\. Lockfiles — avoid `GITHUB_TOKEN` issues with `mise lock` [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#5-lockfiles--avoid-github_token-issues-with-mise-lock)

Pin exact versions, checksums, and download URLs for every tool:

```bash
mise lock
```

That’s it. Run it and it generates `mise.lock` with checksums and URLs for all common platforms. This is a big deal for teams — without a lockfile, every `mise install` hits the GitHub API to resolve versions and download URLs. GitHub’s API rate limits are aggressive for unauthenticated requests, and getting every developer on a team to configure a `GITHUB_TOKEN` is an unnecessary hassle. With a lockfile, installs are fully offline-capable: no API calls, no rate limits, no tokens needed.

Use `--locked` in CI to fail if the lockfile is missing or outdated.

## 6\. Supply chain security [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#6-supply-chain-security)

Most tools in the mise registry now install through the aqua backend, which natively verifies integrity — no external tools required:

- **Checksums** (SHA256, SHA512, Blake3) — always on
- **Cosign** signature verification
- **SLSA** provenance verification
- **GitHub Attestations** — workflow-level verification
- **Minisign** — public key signatures

Only 39 out of 919 tools in the registry default to a plugin-based backend (23 asdf, 16 vfox) — around 4%. The rest install through aqua, github, or other backends with built-in verification. Those remaining plugin-backed tools have all been forked to the [mise-plugins](https://github.com/mise-plugins) org under mise maintainer control. When you run `mise use ripgrep`, you’re getting a verified binary from the vendor’s GitHub release — not running arbitrary bash from a third-party plugin.

## 7\. Environment profiles with `MISE_ENV` [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#7-environment-profiles-with-mise_env)

Set `MISE_ENV=staging` and mise layers `mise.staging.toml` on top of `mise.toml`:

```fallback
mise.toml              # shared defaults
mise.dev.toml          # dev overrides
mise.staging.toml      # staging overrides
mise.local.toml        # personal overrides, never committed
```

The catch: `MISE_ENV` determines _which_ config files get loaded, so it can’t be set inside `mise.toml` itself. That’s what `.miserc.toml` is for — a lightweight config loaded before everything else:

```toml
# .miserc.toml
env = ["development"]
```

This way your project defaults to the `development` profile without requiring every developer to set an environment variable.

## 8\. Shell aliases [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#8-shell-aliases)

Project-scoped aliases that activate/deactivate as you `cd`:

```toml
[shell_alias]
ll = "ls -la"
dev = "npm run dev"
dc = "docker compose -f docker-compose.dev.yml"
src = "cd {{config_root}}/src"
```

Works in bash, zsh, and fish. Leave the directory and they’re gone.

## 9\. `mise prepare` \[experimental\] [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#9-mise-prepare-experimental)

Detects lockfiles and installs project dependencies only when they’re stale. If the content of `package-lock.json` has changed since the last run, it triggers `npm install`. Built-in providers for npm, yarn, pnpm, bun, go, pip, poetry, uv, bundler, and composer. Custom providers for anything else:

```toml
[prepare.codegen]
sources = ["schema/*.graphql"]
outputs = ["src/generated/"]
run = "npm run codegen"
depends = ["npm"]
```

Set `auto = true` and it runs automatically before `mise run` and `mise exec`. Pass `--dry-run` to see _why_ each provider is stale (e.g., “package.json changed”, “outputs missing”).

Watch this space — this is an area I plan to improve further to give users a cargo/uv-like experience across all languages.

## 10\. Monorepo tasks \[experimental\] [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#10-monorepo-tasks-experimental)

Run tasks across packages with wildcard patterns:

```bash
mise //services/api:build          # specific package
mise //...:test                    # all packages
mise '//services/...:build'        # all under services/
```

Configuration inherits from parent directories — define `node = "20"` and common env vars in the root `mise.toml`, and every package gets them automatically. Individual packages can override just what they need (e.g., a legacy app pinning `node = "14"`) while inheriting everything else. Enable with `experimental_monorepo_root = true` in your root `mise.toml`.

* * *

## Bonus: The mise ecosystem [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#bonus-the-mise-ecosystem)

### [fnox](https://github.com/jdx/fnox) [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#fnox)

Secret management for development and production. Encrypt secrets in git with age or cloud KMS, or fetch them from AWS Secrets Manager, 1Password, Vault, and more. Shell integration auto-loads secrets on `cd`:

```toml
# fnox.toml
[providers]
age = { type = "age", recipients = ["age1ql3z..."] }

[secrets]
DATABASE_URL = { provider = "age", value = "YWdlLWVuY3..." }  # encrypted, safe to commit
API_KEY = { default = "dev-key-12345" }                         # plain default for local dev

[profiles.production.providers]
aws = { type = "aws-sm", region = "us-east-1", prefix = "myapp/" }
```

### [hk](https://github.com/jdx/hk) [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#hk)

A git hook manager built for speed. The key innovation is read/write file locking: check commands (e.g., `eslint`, `prettier --check`) take read locks and run fully in parallel, while fix commands (e.g., `prettier --write`) take write locks to prevent race conditions. It runs checks first by default, only falling back to fixes when needed. No other git hook manager does this — tools like husky, lefthook, and pre-commit either run steps serially or do naive parallelism that can corrupt files when multiple fixers touch the same file:

```gdscript3
amends "package://github.com/jdx/hk/releases/download/v1.36.0/hk@1.36.0#/Config.pkl"
import "package://github.com/jdx/hk/releases/download/v1.36.0/hk@1.36.0#/Builtins.pkl"

hooks {
    ["fix"] {
        fix = true
        steps {
            ["prettier"] = (Builtins.prettier) {}
            ["eslint"] = (Builtins.eslint) {}
            ["tsc"] { check = "tsc --noEmit" }
        }
    }
    ["check"] {
        steps {
            ["prettier"] = (Builtins.prettier) {}
            ["eslint"] = (Builtins.eslint) {}
            ["tsc"] { check = "tsc --noEmit" }
        }
    }
}
```

### [pitchfork](https://github.com/jdx/pitchfork) [\#](https://jdx.dev/posts/2026-03-02-10-mise-features/\#pitchfork)

Daemon manager for dev services. Auto-starts processes when you `cd` into a project, auto-stops when you leave. Ready checks, restart on failure, dependency ordering, and cron jobs:

```toml
# pitchfork.toml
[daemons.postgres]
run = "docker run --rm -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:16"
auto = ["start", "stop"]
ready_delay = 5

[daemons.api]
run = "npm run dev:api"
auto = ["start", "stop"]
ready_output = "listening on"
depends = ["postgres"]
```