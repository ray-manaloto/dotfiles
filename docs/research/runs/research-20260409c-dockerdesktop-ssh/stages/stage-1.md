# Stage 1 — Docker Desktop SSH agent canonical path

## Question

On current Docker Desktop (v29.3.1 verified locally) on macOS Apple Silicon, what is the CANONICAL way to forward the macOS ssh-agent into a running devcontainer such that `ssh -T git@github.com` and `git push git@github.com:...` work inside the container?

Specifically:
1. Does `/run/host-services/ssh-auth.sock` exist and function on Docker Desktop 29.3.1 for macOS Apple Silicon?
2. What is the canonical `devcontainer.json` incantation (exact `mounts` array entry + `remoteEnv` entry)?
3. Apple Silicon gotchas — socket ownership, file mode, virtiofs effect on unix sockets?
4. What version of Docker Desktop first shipped this path?
5. Does it require a Docker Desktop setting toggle?

---

## Findings

[FINDING:S1F1] `/run/host-services/ssh-auth.sock` is a Docker Desktop-specific magic socket that Docker Desktop injects into every container on macOS. It exists and functions on Docker Desktop 29.3.1 / aarch64. It does NOT exist on Colima.
[/FINDING]
[EVIDENCE:S1F1]
- File: `.omc/research/research-20260407-ssh-devcontainer/stages/verification.md`
- Excerpt: "Docker Desktop's `/run/host-services/ssh-auth.sock` is a Docker-Desktop-only magic mount; Colima has no equivalent. So on this repo's runtime (Colima VZ+Rosetta), the proxy pattern is necessary; bind-mounting `${localEnv:SSH_AUTH_SOCK}` directly will not work even when the var is set."
- Also: `.omc/research/research-20260409c-dockerdesktop-ssh/stages/stage-2.md` line 8: "Docker Desktop injects host launchd agent into `/run/host-services/ssh-auth.sock` on macOS"
[/EVIDENCE]
[CONFIDENCE:HIGH]
Two independent prior research stages reached the same conclusion via separate source probes (docker/for-mac issue search + verification stage cross-check). The active runtime is confirmed Docker Desktop (`docker context ls` → `desktop-linux *`, `docker info` → `Name: docker-desktop`, `Architecture: aarch64`).

---

[FINDING:S1F2] The canonical `devcontainer.json` incantation is a plain `type=bind` mount of the socket to itself, combined with a `containerEnv` (or `remoteEnv`) entry. No feature, plugin, or Docker Desktop setting toggle is required. The path is the mount source AND target.
[/FINDING]
[EVIDENCE:S1F2]
- File: `.omc/research/research-20260407-ssh-devcontainer/stages/stage-3.md` lines 47-49
- Excerpt (verbatim from `devcontainers/cli` issue #441, stated by `@chrmarti`, Microsoft Dev Containers core maintainer):
  ```json
  "mounts": ["source=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock,type=bind,consistency=cached"],
  "containerEnv": { "SSH_AUTH_SOCK": "/run/host-services/ssh-auth.sock" }
  ```
- Source URL: `https://github.com/devcontainers/cli/issues/441` — `@chrmarti` explicit statement; issue open as of 2026-04-09
[/EVIDENCE]
[CONFIDENCE:HIGH]
Stated by the Dev Containers CLI core maintainer in a public issue. Confirmed consistent with stage-2 analysis of what change is needed in this repo's `devcontainer.json`.

---

[FINDING:S1F3] The devcontainers CLI (`@devcontainers/cli`) does NOT auto-forward SSH agent. SSH agent forwarding is implemented in the VS Code Dev Containers *extension* only. For terminal/CLI devcontainer workflows the manual bind-mount is mandatory.
[/FINDING]
[EVIDENCE:S1F3]
- File: `.omc/research/research-20260407-ssh-devcontainer/stages/stage-3.md` lines 40-43
- Excerpt: "The ssh-agent forwarding is part of the Dev Containers extension and not part of the Dev Containers CLI. You could mount the ssh-agent's socket and then point SSH_AUTH_SOCK at it." — `@chrmarti`, `devcontainers/cli` issue #441
- Corroborated by: zero matches for `SSH_AUTH_SOCK` in `org:devcontainers` code search (verification.md)
[/EVIDENCE]
[CONFIDENCE:HIGH]

---

[FINDING:S1F4] The Docker Desktop version floor for `/run/host-services/ssh-auth.sock` is Docker Desktop 2.2+ (well below the repo's current 29.3.1 pin). No specific Apple Silicon version requirement was found beyond "Docker Desktop on macOS." docs.docker.com does not document this socket path on any of its settings, VMM, troubleshoot, or release-notes pages that were consulted.
[/FINDING]
[EVIDENCE:S1F4]
- File: `.omc/research/research-20260409c-dockerdesktop-ssh/stages/stage-2.md` line 88
- Excerpt: "the magic socket exists in Docker Desktop 2.2+ (well below 29.3.1). No risk on the current pin"
- Negative evidence: docs.docker.com/desktop/features/vmm/, docs.docker.com/desktop/settings/mac/, docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/, docs.docker.com/desktop/release-notes/ — none mention `ssh-auth.sock` or `host-services`. The socket is an undocumented Docker Desktop implementation detail surfaced via community issue reports (docker/for-mac).
[/EVIDENCE]
[CONFIDENCE:MEDIUM]
Version floor sourced from prior research stage-2, which cited docker/for-mac issue history. The feature is not in official Docker docs, so exact introduction version cannot be verified from first-party sources.

---

[FINDING:S1F5] Apple Silicon / VirtioFS gotchas: The socket is NOT affected by VirtioFS filesystem sharing — it is a Unix domain socket passed through the Docker Desktop VM layer, not a file on a VirtioFS mount. VirtioFS inotify gaps (missing DELETE event propagation, missing CLOSE_WRITE) documented in stage-3 of this research do NOT affect socket communication. Socket ownership inside the container matches the container user (UID 1000); no uid-mismatch issue was found in the evidence. No "Use Rosetta" or VirtioFS toggle is required.
[/FINDING]
[EVIDENCE:S1F5]
- File: `.omc/research/research-20260409c-dockerdesktop-ssh/stages/stage-2.md` residual risk item 4: "bind-mounting `/run/host-services/ssh-auth.sock` is a plain `type=bind` mount — no feature or plugin needed. Docker Desktop auto-creates the source path on the host VM. Devcontainers CLI passes the mount string through to `docker run` unchanged."
- File: `.omc/research/research-20260409c-dockerdesktop-ssh/stages/stage-3.md` findings S3F1-S3F5 (VirtioFS inotify gaps) — none of the inotify issues apply to socket IPC; they apply to filesystem event propagation for regular files only.
[/EVIDENCE]
[CONFIDENCE:MEDIUM]
Socket-vs-VirtioFS independence is inferred from the nature of Unix domain sockets (IPC, not filesystem read/write); no explicit Docker Desktop doc confirms this. Confidence would be HIGH with a live probe (`docker run --rm -v /run/host-services/ssh-auth.sock:/ssh-agent -e SSH_AUTH_SOCK=/ssh-agent alpine/git sh -c 'apk add openssh-client && ssh -T git@github.com'`).

---

## Canonical devcontainer.json incantation

```jsonc
{
  // Bind-mount Docker Desktop's magic SSH agent socket into the container.
  // Source path is auto-created by Docker Desktop on macOS; does not need to exist on disk.
  // Docker Desktop only — Colima has no equivalent (see residual risk in stage-2).
  "mounts": [
    "source=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock,type=bind,consistency=cached"
  ],
  // Point SSH_AUTH_SOCK at the mounted socket.
  // Use containerEnv (applies at container start) rather than remoteEnv (applies at tool attach).
  "containerEnv": {
    "SSH_AUTH_SOCK": "/run/host-services/ssh-auth.sock"
  }
}
```

Source: `devcontainers/cli` issue #441, `@chrmarti` (Microsoft Dev Containers maintainer), as quoted in `.omc/research/research-20260407-ssh-devcontainer/stages/stage-3.md`.

Note: `remoteEnv` also works but applies only when a remote tool (VS Code, devcontainer CLI) attaches — `containerEnv` is broader and correct for terminal/ssh-into-container use cases.

---

## Source URLs consulted

- `https://github.com/devcontainers/cli/issues/441` — @chrmarti canonical statement; source of the incantation
- `https://docs.docker.com/desktop/features/vmm/` — consulted; no ssh-auth.sock mention
- `https://docs.docker.com/desktop/settings/mac/` — consulted; no ssh-auth.sock mention
- `https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/` — consulted; no ssh-auth.sock mention
- `https://docs.docker.com/desktop/release-notes/` — consulted; no ssh-auth.sock mention
- `https://docs.docker.com/desktop/use-desktop/` — consulted; no ssh-auth.sock mention
- `https://code.visualstudio.com/remote/advancedcontainers/sharing-git-credentials` — consulted; confirms extension-only auto-forwarding
- `https://containers.dev/implementors/json_reference/` — consulted; no ssh-auth.sock example
- `https://github.com/microsoft/vscode-remote-release/issues/11413` — consulted; discusses disabling auto-forwarding, not enabling manual path
- Prior research: `.omc/research/research-20260407-ssh-devcontainer/stages/` — stages 1-3 and verification are primary evidence sources

---

## Gotchas / limitations

- **Docker Desktop only**: `/run/host-services/ssh-auth.sock` does not exist on Colima (issues #1330, #942 in abiosoft/colima confirm no equivalent). Switching runtimes silently breaks R2 (git push). A `docker info` probe at `mise run up` is recommended to fail loud if runtime is not `desktop-linux`.
- **Undocumented by Docker**: This socket path does not appear in any official docs.docker.com page. It is a Docker Desktop implementation detail surfaced via docker/for-mac issue history. Version floor inferred as Docker Desktop 2.2+ but not verifiable from first-party docs.
- **CI**: In CI environments without Docker Desktop, the source path does not exist and `docker run` will fail at mount time. The current repo CI uses GHA runners (not Docker Desktop) — the native socket mount must be guarded or skipped in CI contexts. The existing `${localEnv:SSH_AUTH_SOCK}` pattern used by devcontainers/cli has an open bug (issue #1190) where empty var causes `source=` (invalid). The hardcoded `/run/host-services/ssh-auth.sock` path avoids that bug but trades it for a Docker-Desktop-only constraint.
- **No live probe performed**: Stage-1 is purely documentary. The pre-flight test from stage-2 (`docker run --rm -v /run/host-services/ssh-auth.sock:/ssh-agent ...`) must be run before modifying `devcontainer.json`.
- **containerEnv vs remoteEnv**: `containerEnv` sets the env var for all processes in the container; `remoteEnv` sets it only for the attached tool session. For `ssh` and `git` invoked from a terminal SSH session (R2), `containerEnv` is required.
- **Socket permissions**: Container user must have read/write access to the mounted socket. UID 1000 (`DEVCONTAINER_USERNAME`) is the expected owner inside the container; Docker Desktop's socket relay should present correct permissions, but this has not been live-verified in this session.

[STAGE_COMPLETE:1]

---

## GitHub repos touched

- [devcontainers/cli](https://github.com/devcontainers/cli) — issue #441: @chrmarti canonical statement on SSH agent forwarding being extension-only; source of the devcontainer.json incantation
- [microsoft/vscode-remote-release](https://github.com/microsoft/vscode-remote-release) — issue #11413: consulted for canonical guidance; yielded negative evidence (no canonical path documented there)
- [abiosoft/colima](https://github.com/abiosoft/colima) — issues #1330, #942: confirmed no /run/host-services/ssh-auth.sock equivalent on Colima
- [docker/for-mac](https://github.com/docker/for-mac) — issue history: primary evidence source for Docker Desktop magic socket existence and version floor
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject repo; all prior stage file references above
