# Stage 3 — VS Code Dev Containers extension SSH credential forwarding

**Tier:** MEDIUM
**Question:** What does VS Code's official "Sharing Git credentials with your container" page say about SSH? Does the extension's auto-forwarding apply to the `@devcontainers/cli` terminal path?

## [FINDING:L3-vscode-text]

The VS Code sharing-git-credentials page states that SSH agent forwarding is handled by the Dev Containers **extension**, not universally. The exact text:

> "There are some cases when you may be cloning your repository using SSH keys instead of a credential helper. To enable this scenario, **the extension will automatically forward your local SSH agent if one is running**."

### [EVIDENCE:L3-vscode-text]

`https://code.visualstudio.com/remote/advancedcontainers/sharing-git-credentials` — "Using SSH keys" section, verbatim quoted above.

### [CONFIDENCE:HIGH]

---

## [FINDING:L3-macos-path]

The doc treats macOS as the easy case — it says the agent is already running and no setup is needed:

> "On Windows and Linux, you may get an error because the agent is not running (**macOS typically has it running by default**)."

The doc does not describe any macOS-specific socket path, launchd integration, or auto-spawn behavior. It relies on the host ssh-agent already being present and the extension forwarding `$SSH_AUTH_SOCK` into the container. The macOS launchd Keychain agent (`/private/tmp/com.apple.launchd.*/Listeners`) satisfies "already running" in practice, but the doc does not name it explicitly.

### [EVIDENCE:L3-macos-path]

Same URL, "On Windows and Linux…" paragraph — macOS is mentioned only as the platform that does not need the Windows/Linux startup steps.

### [CONFIDENCE:HIGH]

(HIGH on the doc claim; MEDIUM on the launchd detail, which is inferred not stated.)

---

## [FINDING:L3-cli-parity]

The `@devcontainers/cli` does **not** get the same auto-forwarding. This is confirmed by a Microsoft engineer (`@chrmarti`, a Dev Containers core maintainer) in `devcontainers/cli` issue #441:

> "**The ssh-agent forwarding is part of the Dev Containers extension and not part of the Dev Containers CLI.** You could mount the ssh-agent's socket and then point SSH_AUTH_SOCK at it."

The issue remains open (no fix shipped). The workaround for terminal `devcontainer up` is a manual bind-mount + env var in `devcontainer.json`:

```json
"mounts": ["source=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock,type=bind,consistency=cached"],
"containerEnv": { "SSH_AUTH_SOCK": "/run/host-services/ssh-auth.sock" }
```

The macOS-specific socket path `/run/host-services/ssh-auth.sock` is what **Docker Desktop** exposes; **Colima does not expose the same path** — it does not pass through `$SSH_AUTH_SOCK` from the host environment. (See verification stage for Colima-specific evidence.)

### [EVIDENCE:L3-cli-parity]

`https://github.com/devcontainers/cli/issues/441#issuecomment` — `@chrmarti` explicit statement; issue open as of 2026-04-07.

### [CONFIDENCE:HIGH]

[STAGE_COMPLETE:3]

## GitHub repos touched

- [microsoft/vscode-remote-release](https://github.com/microsoft/vscode-remote-release) — issue #4024 (macOS SSH agent forwarding workaround) and search results for ssh-agent behavior
- [devcontainers/cli](https://github.com/devcontainers/cli) — issue #441 (explicit confirmation that SSH forwarding is extension-only, not CLI)
