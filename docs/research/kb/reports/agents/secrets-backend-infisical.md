# Infisical as a secrets backend — primary-source research

**Agent:** secrets-backend-infisical
**Date:** 2026-08-03
**Source rules:** `infisical.com/docs/**`, `infisical.com/pricing`, `Infisical/infisical` GitHub repo,
official API reference, official CLI `--help`. **`infisical.com/blog/**` is BANNED** (vendor
marketing); third-party comparison posts are BANNED. A fact only available from a banned source is
recorded as `UNVERIFIED (marketing-only)`.

Status: **COMPLETE** (written incrementally). One limitation is load-bearing and stated in Q7: the
CLI was **not** installed and no account exists on this host, so Q7 is **source-verified on two
independent routes, not live-probed**.

## Q1 — Free tier limits

Source: <https://infisical.com/pricing> (fetched 2026-08-03).

Free plan, verbatim numbers from the pricing table:

| Dimension | Free |
|---|---|
| Identities | **5** ("5 identities, unlimited projects") |
| Projects | **unlimited** |
| Environments | **3** |
| Secret Syncs | **10** |
| Custom Environments | **–** (not available) |

Pro tier is described as "Everything in Free, plus: Unlimited identities, Access Controls,
Secret Rotation, SAML SSO, 30-day Audit log retention, Secret Versioning, Point-in-time Recovery".
Dynamic Secrets is Advanced-tier only.

⚠️ **The pricing page does not state a numeric cap on secrets or on users/members** in what was
returned. `UNVERIFIED`: per-secret count limit and per-user/member seat limit on Free — not found on
the pricing page; tried <https://infisical.com/pricing>.

### What "identity" means

Source: <https://infisical.com/docs/documentation/platform/identities/machine-identities>

Verbatim: *"An Infisical machine identity is an entity that represents a workload or application
that require access to various resources in Infisical."* The docs compare it to "an IAM user in AWS
or service account in Google Cloud Platform (GCP)".

Consequence for the solo-dev question: an identity is a **created object with its own auth method
and role**, not a per-human count. The docs do NOT state that a CI token or a machine consumes
exactly one identity, but the model is one identity object per workload/application, each of which
you create individually. A solo developer using the CLI interactively logs in as a *user*, not as a
machine identity — machine identities are for workloads.

`UNVERIFIED`: whether the pricing page's "5 identities" counts **users + machine identities** or
machine identities only. The pricing page uses the bare word "identities"; the docs page defines
only "machine identity". Tried both URLs above; the two do not cross-reference. **This is a real
ambiguity and it matters** — if it counts both, a solo dev with 2 laptops + 2 CI runners is already
at 5.

## Q2 — License split

**Two repos, same dual-license structure.**

Server/platform: <https://github.com/Infisical/infisical> — root `LICENSE`
(<https://raw.githubusercontent.com/Infisical/infisical/main/LICENSE>), verbatim:

> Copyright (c) 2022 Infisical Inc. Portions of this software are licensed as follows...
> All content that resides under any "ee/" directory of this repository, if such directories exists,
> are licensed under the license defined in "ee/LICENSE".
> ... Content outside of the above mentioned directories or restrictions above is available under the
> "MIT Expat" license as defined below.

CLI: <https://github.com/Infisical/cli> — GitHub API reports `license.spdx_id = NOASSERTION`
(i.e. GitHub cannot classify it), and its `LICENSE` carries the **same** carve-out text, dated 2025:

> Copyright (c) 2025 Infisical Inc. ... All content that resides under any "ee/" directory of this
> repository, if such directories exists, are licensed under the license defined in "ee/LICENSE".
> ... Content outside ... is available under the "MIT Expat" license.

**The `ee/` tree is real and substantial.** GitHub code search on `repo:Infisical/infisical
filename:LICENSE` returns `backend/src/ee/LICENSE.md`, and the tree contains
`backend/src/ee/services/license/`, `backend/src/ee/services/license-v2/`,
`backend/src/ee/routes/v1/license-router.ts`, plus a Go mirror at
`backend-go/internal/ee/services/license/`. So a licence-gating subsystem is compiled into the
same binary and its own directory is under separate (non-MIT) terms.

**RESOLVED — the `ee/` licence is a proprietary Enterprise License, not an OSI licence.**
<https://raw.githubusercontent.com/Infisical/infisical/main/backend/src/ee/LICENSE.md> (HTTP **200**;
control arm: a bogus sibling path returned **404**, so the fetch discriminates). Verbatim opening:

> The Infisical Enterprise license (the "Enterprise License")
> Copyright (c) 2022 Infisical Inc
> ... This software ... may only be used in production, if you (and any entity that you represent)
> have agreed to, and are in compliance with, the Infisical Subscription Terms of Service ... and
> otherwise have a valid Infisical Enterprise License for the correct number of user seats.
> ... Notwithstanding the foregoing, you may copy and modify the Software for development and testing
> purposes, without requiring a subscription. ... it is forbidden to copy, merge, publish, distribute,
> sublicense, and/or sell the Software.

So the answer to "is any part of the repo non-open-source" is **yes, explicitly**: `ee/` is
**production-use-forbidden without a paid seat-counted subscription**, dev/test use excepted. It is
not BUSL — it is Infisical's own Enterprise License, closer to the Sentry/GitLab "ee/" model.

**Paywalled features** (source: <https://infisical.com/pricing>, Pro tier described as "Everything
in Free, plus: …"):

| Feature | Free? |
|---|---|
| Secret versioning | ❌ Pro |
| Point-in-time recovery | ❌ Pro |
| RBAC / "Access Controls" | ❌ Pro |
| Secret rotation | ❌ Pro |
| Audit logs | ❌ Pro (30-day retention) |
| SAML SSO | ❌ Pro |
| Dynamic secrets | ❌ Advanced |

This is the decisive shape for a solo user: **secret versioning and point-in-time recovery — the
two things that make a secrets store recoverable — are both paid.**

## Q3 — `infisical run` injection semantics

Sources: <https://infisical.com/docs/cli/commands/run> and CLI source
`packages/cmd/run.go` (<https://github.com/Infisical/cli>).

Command forms (from the cobra `Example`/`Use` fields in `packages/cmd/run.go:29-35`, verbatim):

```
infisical run --env=dev -- npm run dev
infisical run --command "first-command && second-command; more-commands..."
```

`Use: "run [any infisical run command flags] -- [your application start command]"`,
`Short: "Used to inject environments variables into your application process"`.

**Yes, it execs a child with secrets in that child's environment.** `formatSecretsForShell`
(`packages/cmd/run.go`) copies `os.Environ()` into a map, overlays the Infisical secrets on top, and
hands the resulting `[]string` to `executeSingleCommandWithEnvs` / `executeMultipleCommandWithEnvs`.
The parent's own environment is never mutated, so **teardown is structural** — the variables exist
only in the child process and die with it. This is exactly the `fnox exec --` shape.

Notable behaviour found in source, not in the docs summary: `filterReservedEnvVars` **silently drops**
secrets named `HOME PATH PS1 PS2 PWD EDITOR XAUTHORITY USER TERM TERMINFO SHELL MAIL` and anything
prefixed `XDG_` / `LC_`, printing a warning.

Documented flags: `--command`, `--env` (default `dev`), `--projectId` (required with machine-identity
auth), `--path` (repeatable), `--token`, `--watch` (restarts the child on secret change),
`--project-config-dir`, `--expand` (default true), `--include-imports` (default true),
`--secret-overriding` (default true), `--tags`.

**Interactive shell / the `fnox activate` equivalent: NOT documented.** The docs page does not
document injecting into an interactive shell. The closest supported thing is
`infisical run -- $SHELL` (a child shell — same teardown semantics), which is an inference from the
exec model, **not a documented feature**: `UNVERIFIED (not documented)`. There is no
`infisical activate` / shell-hook / `eval "$(infisical …)"` form on the `run` docs page.

## Q4 — Offline / unreachable behaviour

**There IS an offline cache, and it is real code, not a doc claim.**
Source: `packages/util/secrets.go` in <https://github.com/Infisical/cli>, function
`GetAllEnvironmentVariables`:

```go
// only attempt to serve cached secrets if no internet connection and if at least one secret cached
if !isConnected {
    backupEncryptionKey, _ := GetBackupEncryptionKey()
    if backupEncryptionKey != nil {
        backedUpSecrets, err := ReadBackupSecrets(params.WorkspaceId, params.Environment, params.SecretsPath, backupEncryptionKey)
        if len(backedUpSecrets) > 0 {
            PrintWarning("Unable to fetch the latest secret(s) due to connection error, serving secrets from last successful fetch. For more info, run with --debug")
            secretsToReturn = backedUpSecrets
            errorToReturn = err
        }
    }
}
```

Mechanics, read off the same file:

- Every **successful** fetch writes a backup: `WriteBackupSecrets(workspaceId, environment,
  secretsPath, key, secrets)` → `<config-dir>/secrets-backup/project_secrets_<workspace>_<env>_<path>.json`.
- The backup is **encrypted**, with the key stored in the **OS keyring**
  (`GetBackupEncryptionKey` → `GetValueInKeyring(INFISICAL_BACKUP_SECRET_ENCRYPTION_KEY)`, generating
  a random 16-byte key on first use). If the platform has no keyring it returns an error telling you
  to use a service token.
- The gate is `isConnected := ValidateInfisicalAPIConnection()`. So the cache serves **only** when the
  API is unreachable — it is not a general fallback for API errors.
- Cache is **keyed by (workspace, environment, secretsPath)** and only used when
  `len(backedUpSecrets) > 0`.

So: **offline → serves the last successful fetch, with a stderr warning, rc unchanged.** This is a
cache-on-unreachable, not a fail-open on a bad request (see Q7).

⚠️ **The cache path applies only to the logged-in-user branch.** The `else` branch of
`GetAllEnvironmentVariables` — used when `InfisicalToken` (service token) or
`UniversalAuthAccessToken` (machine identity) is set — has **no cache fallback at all**. CI/machine
auth therefore hard-fails when the API is unreachable.

`UNVERIFIED`: whether the offline cache is documented on `infisical.com/docs/**`. A grep of
`https://infisical.com/docs/llms.txt` for `offline` and `cache` returned **0** — but that index is
API-reference-only (control arm: `docs` → 957 lines of 963, all `api-reference/endpoints/*`), so the
0 proves the index is narrow, not that the docs are silent. Treat the offline behaviour as
**source-verified, doc-status unknown**.

## Q5 — Self-host requirements

Source: <https://infisical.com/docs/self-hosting/deployment-options/docker-compose>
(<https://infisical.com/docs/self-hosting/overview> lists the deployment options — Docker,
Kubernetes, Docker Compose, AWS, GCP, Linux package — but carries **no** resource numbers).

Three services, all required:

1. Backend — "The main Infisical application (exposed on host port 80, internal port 8080)"
2. **PostgreSQL** — "PostgreSQL database for storing encrypted secrets"
3. **Redis** — "Redis for caching and job queues"

Stated minimum resources: **2 CPU cores, 4 GB RAM, 20 GB disk.**

Required configuration: `ENCRYPTION_KEY`, `AUTH_SECRET`, `DB_CONNECTION_URI`
(`postgresql://<user>:<password>@<host>:5432/<dbname>`), `REDIS_URL`
(`redis://:<password>@<host>:6379`), `SITE_URL`, and `SMTP_*` for email.

`UNVERIFIED`: the exact minimum **Postgres version**. Not stated in what the page returned.

**Read this against the alternative.** fnox is a single static binary with no server. Infisical
self-hosted is a Postgres + Redis + Node service with a 4 GB RAM floor, which on this Mac means
another always-on container stack. The SaaS free tier avoids that but reintroduces a hard network
dependency (see Q4).

## Q6 — Agent / plugin surface

**Found, and it is the strongest part of the whole offering.** Three separate primitives:

### 6a. Official MCP servers — TWO of them

- <https://github.com/Infisical/infisical-mcp-server> — "Infisical's official MCP server."
  JavaScript, **Apache-2.0**, last pushed 2026-04-14 (GitHub API `repos/Infisical/infisical-mcp-server`).
- A hosted **docs** MCP at `https://infisical.com/docs/mcp`, which
  <https://github.com/Infisical/ai-skills> README documents installing as:
  `claude mcp add --transport http infisical-docs https://infisical.com/docs/mcp`

### 6b. A Claude Code plugin marketplace

<https://github.com/Infisical/ai-skills> — "AI skills and MCP connection for Infisical". Its tree
contains **`.claude-plugin/marketplace.json`**, an `AGENTS.md`, a `.github/workflows/validate-plugins.yml`,
and a full `evals/infisical-agent/` tree with `with_skill` vs `without_skill` A/B runs. README:
*"They follow the [Agent Skills](https://agentskills.io) open standard and work across 45+ AI tools"*,
installable via `npx skills add Infisical/ai-skills` or the Claude Code plugin marketplace.

### 6c. An agent-scoped credential-brokering primitive in the CLI itself

This is the notable one. `packages/cmd/agent_proxy.go` / `agent_proxy_run.go` in
<https://github.com/Infisical/cli> define:

| Command | `Short` (verbatim) |
|---|---|
| `infisical secrets agent-proxy` | "Secrets brokering: run an agent proxy and connect agents to it" |
| `… agent-proxy start` | "Start the agent proxy (MITM proxy that brokers credentials on the wire)" |
| `… agent-proxy connect [flags] -- [agent start command]` | "Set up the environment and launch an agent behind the agent proxy" |
| `… agent-proxy run [flags] -- [agent start command]` | "Launch an agent on this machine, sandboxed, with credentials brokered on the wire" |

The `Example` for `run` is, verbatim: **`infisical secrets agent-proxy run --env=dev --path=/myapp -- claude`**
— i.e. Claude Code is the named example agent. Design details read off the source:

- The child gets **no credentials at all**. Comment: *"The single identity for the run: fetches config
  and secret values in the parent. The child gets none of it."* Secrets are injected on the wire by a
  MITM proxy instead of into the environment.
- `secretShapedEnvSubstrings = {"TOKEN","SECRET","PASSWORD","PASSWD","CREDENTIAL","API_KEY","APIKEY","PRIVATE_KEY","ACCESS_KEY"}`
  — env vars whose *name* contains any of these are **scrubbed from the child**; `--pass-env <NAME>`
  re-admits one explicitly. Its test file asserts this on `ANTHROPIC_API_KEY` and `AWS_SECRET_ACCESS_KEY`.
- OS-level sandboxing (`resolveSandboxEnabled`, `--allow-read` / `--allow-write` / `--allow-host`,
  `--unmatched-host allow|block`), a per-run `0700` tempdir, and a darwin-specific CA in
  `~/.infisical/agent-proxy`.
- It knows the agent harnesses by name: the test fixture creates `~/.claude`, `~/.claude.json` and
  checks for `~/.codex` in `defaultAgentStateWritePaths`.

**This is exactly the posture `.claude/rules/secrets-out-of-the-shell-env.md` says this repo gave up**
(50 credentials in every agent child). Infisical ships a scrub-plus-broker primitive for it, with
Claude Code as the worked example.

### Control arm for the absence claims

A grep of the CLI repo for `mcp` / "model context protocol" (excluding `kmip`) returned **0** — but the
control arm (`gateway`, known present) returned **57 files**, so the probe discriminates and the CLI
binary genuinely does not embed an MCP server. The MCP surface lives in the two separate repos above,
which is why the org-level `gh api orgs/Infisical/repos` sweep was needed to find it. **A repo-scoped
grep would have produced a false "no MCP".**

## Q7 — Fail-open vs refusal (DECISIVE)

### Verdict: **REFUSES** — nonzero exit, no secrets emitted, no child process started.

⚠️ **Method disclosure up front.** I could **not** run a live probe: `infisical` is not installed on
this host (`which infisical` → not found) and I have no Infisical account or token, so there is no
credential with which to issue a real bad-project request. The verdict below is **source-verified on
two independent routes** (the Go CLI's error path and the TypeScript backend's throw sites), which
cross-check each other, but it is **not empirical** the way the fnox `-P <nonexistent>` → 49 secrets
at rc=0 result is. Treat it as `SOURCE-VERIFIED, NOT LIVE-PROBED`.

### Route 1 — the CLI never swallows an API error

`packages/api/api.go:603` `CallGetSecretsV4` (<https://github.com/Infisical/cli>):

```go
if response.IsError() {
    return GetSecretsV4Response{}, NewAPIErrorWithResponse(operationCallGetRawSecretsV3, response, nil)
}
```

Any non-2xx becomes an error. That error propagates unchanged:

`GetPlainTextSecretsV4` → `util.GetAllEnvironmentVariables` (`errorToReturn = err`) →
`fetchSecrets` (`return nil, fmt.Errorf("failed to fetch secrets for path %q: %w", path, err)`) →
`fetchAndFormatSecretsForShell` (`return models.InjectableEnvironmentResult{}, err`) →
`runCmd.Run`:

```go
injectableEnvironment, err := fetchAndFormatSecretsForShell(...)
if err != nil {
    util.HandleError(err, "Could not fetch secrets", "If you are using a service token to fetch secrets, please ensure it is valid")
}
```

`util.HandleError` (`packages/util/log.go:67`) is `PrintErrorAndExit(1, err, ...)`, whose last
statement is `os.Exit(exitCode)` — **rc=1, and the `-- <command>` child is never exec'd**, because
`executeSingleCommandWithEnvs` is called only after that block. There is **no** `if err != nil {
log and continue }` anywhere on this path.

Two more refusal points before any network call, both `util.HandleError` (rc=1):

- no project resolvable → *"Please either run infisical init to connect to a project or pass in
  project id with --projectId flag"* (`packages/util/secrets.go`)
- machine-identity auth without a project → *"Project ID is required when using machine identity"*

And in the agent-proxy lane (`packages/cmd/agent_proxy_run.go`), a missing environment is a hard
refusal: *"the environment is required; pass --env, set INFISICAL_ENVIRONMENT, or set
defaultEnvironment in .infisical.json"*.

### Route 2 — the backend actually returns an error for each bogus input

`backend/src/services/secret-v2-bridge/secret-v2-bridge-service.ts`, function `getSecrets`
(<https://github.com/Infisical/infisical>):

- **Nonexistent project** → `permissionService.getProjectPermission(...)` is called *before* any
  secret lookup; `backend/src/ee/services/permission/permission-service.ts:465` throws
  `NotFoundError({ message: \`Project with ${projectId} not found\` })`.
- **Nonexistent environment slug or path** → both branches throw, unconditionally:

```ts
if (recursive) {
  const deepPaths = await recursivelyGetSecretPaths({ ... environment, currentPath: path });
  if (!deepPaths?.length) {
    throw new NotFoundError({
      message: `Folder with path '${path}' in environment '${environment}' was not found. Please ensure the environment slug and secret path is correct.`,
      name: "SecretPathNotFound"
    });
  }
} else {
  const folder = await folderDAL.findBySecretPath(projectId, environment, path);
  if (!folder) {
    throw new NotFoundError({ message: `Folder with path '${path}' ... not found ...`, name: "SecretPathNotFound" });
  }
}
```

I specifically checked whether the throw is gated behind a flag (which would open a fail-open lane) —
it is not; it is unconditional in both the `recursive` and non-recursive branches. The same
`Folder with path ... not found` throw appears at ~10 other call sites in the file for the
write/update/delete paths.

- **Nonexistent identity** → the token is rejected at auth, before `getSecrets` is reached.

### Two residual soft-fail-open axes worth naming honestly

1. **The offline cache serves STALE secrets at rc=0** with only a stderr `Warning:` line
   (`PrintWarning("Unable to fetch the latest secret(s) due to connection error, serving secrets from
   last successful fetch...")`, Q4). That is not the fnox failure mode (wrong scope → wrong secrets),
   but it *is* "rc=0 with secrets you did not just authorise". It is bounded: the backup is keyed by
   `(workspaceId, environment, secretsPath)`, so a **bogus** project/env has no backup file,
   `len(backedUpSecrets) == 0`, the fallback is skipped, and the original error still propagates to
   `os.Exit(1)`. So offline + bogus scope still **REFUSES**.
2. **A real-but-empty folder** injects zero secrets and runs the child at rc=0. There is no
   `--require-secrets` / minimum-count flag in `run.go`'s flag set. So "valid scope, nothing in it" is
   silent — but a *typo'd* scope is a 404, which is the case that matters.

### Against the incumbent

| | fnox 1.32.0 | Infisical CLI |
|---|---|---|
| Bogus profile/project | **FAILS OPEN** — 49 secrets, rc=0, zero stderr | **REFUSES** — rc=1, no child exec'd (source-verified) |
| Bogus environment | n/a | **REFUSES** — backend 404 `SecretPathNotFound` |
| Offline | n/a | serves encrypted local cache + warning, rc=0 (user-auth lane only) |

**Recommended follow-up before deciding:** install the CLI (`brew install infisical/get-cli/infisical`
per <https://github.com/Infisical/homebrew-get-cli>), create a free-tier project, and run the live
arm — `infisical run --projectId <bogus> --env dev -- echo REACHED` — asserting that `REACHED` is
**not** printed and `rc != 0`. Also run the *positive* control (a real project, expecting `REACHED`),
or the probe can only fail. That converts this from `SOURCE-VERIFIED` to measured.

## Method notes / control arms run

- **Absence of MCP in the CLI repo**: grep for `mcp` (ex-`kmip`) → 0 files; control `gateway` → 57
  files. Probe discriminates ⇒ the 0 is real for that repo. The org-wide sweep
  (`gh api orgs/Infisical/repos`) then found the MCP surface in two *other* repos — a repo-scoped
  grep alone would have been a false negative.
- **`docs/llms.txt` grep for `offline`/`cache`/`self-hosting` → 0**: control `docs` → 957 of 963
  lines. The index is **API-reference-only**, so the 0 means "the index is narrow", not "the docs are
  silent". I did **not** report doc-silence on the strength of it.
- **`raw.githubusercontent.com/.../backend/src/ee/LICENSE` → HTTP 404**: a 404 is "never asked", not
  "no ee licence". GitHub code search gave the real path, `backend/src/ee/LICENSE.md`.
- **No live CLI probe was possible** (not installed, no account) — stated in Q7 rather than papered
  over.

## GitHub repos touched

- [Infisical/infisical](https://github.com/Infisical/infisical) — root `LICENSE` (MIT Expat + `ee/`
  carve-out), `backend/src/services/secret-v2-bridge/secret-v2-bridge-service.ts` (`getSecrets`
  NotFoundError throws), `backend/src/ee/services/permission/permission-service.ts` (project-not-found),
  `backend/e2e-test/routes/v4/secrets.spec.ts`, full tree listing for the `ee/` inventory.
- [Infisical/cli](https://github.com/Infisical/cli) — the Go CLI: `packages/cmd/run.go`,
  `packages/cmd/agent_proxy*.go`, `packages/util/secrets.go` (offline cache), `packages/util/log.go`
  (`HandleError` → `os.Exit(1)`), `packages/api/api.go` (`CallGetSecretsV4`), `LICENSE`,
  `agent-config.yaml`.
- [Infisical/infisical-mcp-server](https://github.com/Infisical/infisical-mcp-server) — official MCP
  server; metadata only (Apache-2.0, JS, pushed 2026-04-14).
- [Infisical/ai-skills](https://github.com/Infisical/ai-skills) — Claude Code plugin marketplace
  (`.claude-plugin/marketplace.json`), agent skills, docs-MCP install instructions, evals tree.
- [Infisical/homebrew-get-cli](https://github.com/Infisical/homebrew-get-cli) — named only as the
  install route for the recommended live follow-up probe; not inspected.

Non-GitHub primary sources: <https://infisical.com/pricing>,
<https://infisical.com/docs/documentation/platform/identities/machine-identities>,
<https://infisical.com/docs/cli/commands/run>, <https://infisical.com/docs/self-hosting/overview>,
<https://infisical.com/docs/self-hosting/deployment-options/docker-compose>,
<https://infisical.com/docs/llms.txt>. **`infisical.com/blog/**` was not fetched.**
