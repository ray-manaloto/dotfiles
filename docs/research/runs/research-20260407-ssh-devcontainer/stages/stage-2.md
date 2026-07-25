# Stage 2 — @devcontainers/cli implementation

**Tier:** MEDIUM
**Question:** Does the `@devcontainers/cli` (npm package) auto-forward the host's `$SSH_AUTH_SOCK` during `devcontainer up` or `devcontainer exec`?

## [FINDING:L2-cli-ssh-auto]

**No.** The `@devcontainers/cli` does **nothing** automatic with `$SSH_AUTH_SOCK` — SSH agent forwarding is implemented in the VS Code Dev Containers *extension*, not in the CLI.

### [EVIDENCE:L2-cli-ssh-auto]

- **devcontainers/cli#441** (comment by `@chrmarti`, Microsoft, Dev Containers core maintainer):

  > "The ssh-agent forwarding is part of the Dev Containers extension and not part of the Dev Containers CLI. You could mount the ssh-agent's socket and then point SSH_AUTH_SOCK at it."

- Direct source probes against `devContainersSpecCLI.ts` and the cli `README.md`: **zero matches** for `SSH_AUTH_SOCK`, `ssh-agent`, `forwardAgent`, `mountSSHSocket`.

### [CONFIDENCE:HIGH]

---

## [FINDING:L2-cli-exec-env]

**No evidence of automatic SSH_AUTH_SOCK passthrough in `devcontainer exec`.** Nothing in the CLI source or issues indicates `devcontainer exec` automatically injects the host's `SSH_AUTH_SOCK` into the exec session. The socket path would differ inside the container anyway (Linux socket path vs macOS `/private/tmp/...`), so passthrough without a mount would be meaningless.

### [EVIDENCE:L2-cli-exec-env]

- No code match in `devContainersSpecCLI.ts` for `SSH_AUTH_SOCK`.
- Issue #441 user reports: even after manually mounting the socket, `ssh-add` fails to connect — suggesting the CLI does not wire the env var either.

### [CONFIDENCE:MEDIUM]

---

## [FINDING:L2-canonical-pattern]

The CLI community pattern is `mounts` + `remoteEnv` in `devcontainer.json`, with `${localEnv:SSH_AUTH_SOCK}` as the mount source — but this pattern is **fragile**: when `SSH_AUTH_SOCK` is unset (CI, Windows hosts), the CLI passes `source=` (empty) to Docker and Docker rejects the run. Issue #1190 (open, CLI v0.85.0) requests that the CLI skip mounts whose `${localEnv:VAR}` resolves to empty.

### [EVIDENCE:L2-canonical-pattern]

- Issue #441 comment 4 (community-documented pattern):

  ```json
  "runArgs": [
    "-e", "SSH_AUTH_SOCK=/tmp/ssh-agent.socket",
    "-v", "${env:SSH_AUTH_SOCK}:/tmp/ssh-agent.socket"
  ]
  ```

- Issue #1190 body (canonical `devcontainer.json` form + failure mode):

  ```json
  "mounts": [
    "source=${localEnv:SSH_AUTH_SOCK},target=/run/ssh-agent.sock,type=bind"
  ]
  ```

  > "When `${localEnv:SSH_AUTH_SOCK}` resolves to empty… Docker rejects this: `invalid value for 'source': value is empty`"

- Issue #1190 is **open** as of CLI v0.85.0 — no fix shipped yet.

### [CONFIDENCE:HIGH]

---

**Practical implication for this repo:** The `mounts` + `remoteEnv` pattern works on a Mac with a live `$SSH_AUTH_SOCK`, but will blow up in CI (where `SSH_AUTH_SOCK` is unset) unless guarded. The correct guard is the `${localEnv:SSH_AUTH_SOCK}` empty-skip fix from issue #1190 — which is not yet in the CLI. Until it lands, the only safe approach is a conditional mount or accepting that CI skips the mount entirely via a feature flag.

[STAGE_COMPLETE:2]

## GitHub repos touched

- [devcontainers/cli](https://github.com/devcontainers/cli) — probed source, README, issues #441 and #1190 for SSH agent forwarding behavior
