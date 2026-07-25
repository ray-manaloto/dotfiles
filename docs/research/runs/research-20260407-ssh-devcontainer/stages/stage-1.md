# Stage 1 — containers.dev spec authority

**Tier:** MEDIUM
**Question:** Does the containers.dev spec define an official `devcontainer.json` property for forwarding the host SSH agent into a Dev Container?

## [FINDING:L1-spec-property]

**No dedicated SSH agent forwarding property exists in the devcontainer.json spec.** The spec does not define `forwardAgent`, `mountSSHSocket`, `sshAgent`, or any property specifically for SSH agent forwarding. The canonical workaround is the general-purpose `mounts` property combined with `${localEnv:SSH_AUTH_SOCK}` and `remoteEnv`.

### [EVIDENCE:L1-spec-property]

From `devcontainerjson-reference.md` (raw: `https://raw.githubusercontent.com/devcontainers/spec/main/docs/specs/devcontainerjson-reference.md`):

> `mounts` 🏷️ | string or object | Defaults to unset. Cross-orchestrator way to add additional mounts to a container. Each value is a string that accepts the same values as the Docker CLI `--mount` flag. Environment and pre-defined variables may be referenced in the value.

The JSON schema at `https://raw.githubusercontent.com/devcontainers/spec/main/schemas/devContainer.base.schema.json` (24,142 chars) contains **zero** matches for: `ssh`, `SSH`, `agent`, `forwardAgent`, `mountSSHSocket`, `socket`.

The `devContainer.schema.json` and `devContainerFeature.schema.json` also return zero matches for all SSH-related terms.

### [CONFIDENCE:HIGH]

Schema is the authoritative source; all three schema files were fetched and exhaustively searched.

### Canonical community workaround pattern (from devcontainers/cli#1190)

```json
"mounts": [
  "source=${localEnv:SSH_AUTH_SOCK},target=/run/ssh-agent.sock,type=bind"
],
"remoteEnv": {
  "SSH_AUTH_SOCK": "/run/ssh-agent.sock"
}
```

**Known caveat:** when `SSH_AUTH_SOCK` is unset (e.g., in CI without an agent), the CLI resolves `${localEnv:SSH_AUTH_SOCK}` to an empty string and passes `source=` to Docker, which fails. Issue #1190 is **open** as of CLI v0.85.0 with no spec-level fix.

### Implementation responsibility

The spec leaves SSH agent forwarding entirely to the orchestrator/user. VS Code's Dev Containers extension has its own out-of-band forwarding mechanism (mentioned in `devcontainers/cli` issue #441, open), but it is not spec-defined. The `@devcontainers/cli` has no built-in SSH agent forwarding — it passes `mounts` verbatim to Docker.

[STAGE_COMPLETE:1]

## GitHub repos touched

- [devcontainers/spec](https://github.com/devcontainers/spec) — primary spec source; schemas/ and docs/specs/ directories read directly
- [devcontainers/cli](https://github.com/devcontainers/cli) — issues #441 and #1190 read for SSH agent forwarding workaround patterns and known failure modes
