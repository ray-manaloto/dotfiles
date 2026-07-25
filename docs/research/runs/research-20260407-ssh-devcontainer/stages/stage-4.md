# Stage 4 — devcontainers/features/sshd reality check

**Tier:** LOW
**Question:** What does `ghcr.io/devcontainers/features/sshd:1` actually do? Is it the right tool for forwarding the host SSH key into the container for git push?

## [FINDING:L4-sshd-options]

Valid options are exactly TWO: `gatewayPorts` and `version`. The options `port`, `username`, and `startNow` **do NOT exist** in the feature schema and are silently dropped when set in `devcontainer.json`.

### [EVIDENCE:L4-sshd-options]

From `devcontainer-feature.json` (raw: `https://raw.githubusercontent.com/devcontainers/features/main/src/sshd/devcontainer-feature.json`):

```json
"options": {
    "version": {
        "type": "string",
        "default": "latest",
        "description": "Currently unused."
    },
    "gatewayPorts": {
        "type": "string",
        "enum": ["no", "yes", "clientspecified"],
        "default": "no",
        "description": "Enable other hosts in the same network to connect to the forwarded ports"
    }
}
```

### [CONFIDENCE:HIGH]

---

## [FINDING:L4-sshd-purpose]

The feature's documented purpose is "to use an external terminal, sftp, or SSHFS to interact with [the container]." This means SSH **into** the container **from** the host — not to enable git operations inside the container.

### [EVIDENCE:L4-sshd-purpose]

From the feature `README.md`:

> "Adds a SSH server into a container so that you can use an external terminal, sftp, or SSHFS to interact with it."

Usage instructions: *"Forward port 2222 to your local machine and run: `ssh -p 2222 vscode@localhost`"*. Workflow is (1) start container in VS Code, (2) forward SSH port locally, (3) ssh in from local terminal using password.

### [CONFIDENCE:HIGH]

---

## [FINDING:L4-wrong-tool]

This feature does **NOT** solve the "git push from inside the container" problem at all. It installs `openssh-server` (a listening server inside the container) but does not forward the host's SSH agent (`SSH_AUTH_SOCK`) into the container, nor does it configure `authorized_keys` with the host SSH public key.

### [EVIDENCE:L4-wrong-tool]

`install.sh` analysis:
- Installs `openssh-server` (server-side, not client-side agent forwarding).
- Does NOT mention `SSH_AUTH_SOCK`.
- Does NOT configure `authorized_keys`.
- Does NOT forward host authentication socket.
- Requires manual password setup: `sudo passwd $(whoami)`.
- Output message: *"Forward port 2222 to your local machine"* — this is port forwarding FROM container, not agent forwarding INTO it.

### [CONFIDENCE:HIGH]

---

**Practical implication:** This feature is the wrong tool for the dotfiles problem. For git to work inside the container using your host SSH key, you need agent forwarding (mount + env var), **not** an in-container sshd. The current dotfiles `features.sshd` block should be deleted.

[STAGE_COMPLETE:4]

## GitHub repos touched

- [devcontainers/features](https://github.com/devcontainers/features) — read `devcontainer-feature.json`, `install.sh`, `README.md` for sshd feature schema, install logic, and documented use case
