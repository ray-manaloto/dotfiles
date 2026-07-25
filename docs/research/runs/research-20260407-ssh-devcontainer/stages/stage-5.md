# Stage 5 — cpp-playground SSH-agent-proxy tech-debt audit

**Tier:** MEDIUM
**Question:** Why does cpp-playground use a custom Python TCP+unix-socket SSH-agent proxy? Is it legacy debt or current best practice?

## [FINDING:L5-proxy-architecture]

The proxy is a bidirectional TCP-to-Unix-socket relay implemented entirely in Python stdlib (`socket`, `select`, `threading`). Two halves:

**Host half** (lines 284-339): `start_host_ssh_proxy()` spawns a background subprocess running `serve_proxy(--listen-tcp 127.0.0.1:<ephemeral-port> --target-unix <SSH_AUTH_SOCK>)`. Picks a random free TCP port (line 266-268), writes the port to `~/.local/state/cpp-playground/ssh-agent-port`, waits up to 5 seconds for the TCP listener to accept connections (lines 329-336).

**Container half** (lines 802-814, 443): `resolve_ssh_auth_sock()` inside the container checks for the existing `/tmp/cpp-playground-ssh-agent.sock` (the stable `CONTAINER_SSH_PROXY_SOCKET`), then falls back to `ensure_container_ssh_agent_proxy()`. The container-side proxy runs `serve_proxy(--listen-unix /tmp/cpp-playground-ssh-agent.sock --target-tcp host.docker.internal:<port>)` where `<port>` is read from the host-state directory bind-mounted at `/tmp/cpp-playground-host-state/ssh-agent-port` (devcontainer.json line 50-51). `remoteEnv.SSH_AUTH_SOCK` is hardwired to `/tmp/cpp-playground-ssh-agent.sock` (devcontainer.json line 29, devcontainer.py line 443).

**Full chain:** macOS launchd agent socket → host TCP listener (127.0.0.1:N) → `host.docker.internal:N` → container Unix socket `/tmp/cpp-playground-ssh-agent.sock` → any process inside the container that uses `SSH_AUTH_SOCK`.

### [EVIDENCE:L5-proxy-architecture]

`devcontainer.py` lines 169-251 (`proxy_connection`, `serve_proxy`), lines 254-339 (`resolve_host_ssh_auth_sock`, `start_host_ssh_proxy`), lines 802-814 (`resolve_ssh_auth_sock`), line 443 (`remoteEnv["SSH_AUTH_SOCK"]`); `devcontainer.json` lines 29, 50-51.

### [CONFIDENCE:HIGH]

---

## [FINDING:L5-original-motivation]

Only one commit introduces the file: `d237aef — "refactor: consolidate cpp-playground control plane"`. The commit message is a refactor message with no prose explaining the SSH proxy motivation. No prior commit exists in the log for this file. The motivation must therefore be read from explicit documentation in `AGENTS.md` and `docs/archive/spec/2026-03-22-devcontainer-ssh-login-plan.md`.

`AGENTS.md` lines 12-16 (verbatim):

> "On macOS with Docker Desktop, do not assume a bind-mounted host UNIX socket is a usable SSH agent inside the Linux container. This repo's checked-in path is a host-local TCP proxy plus a container-local UNIX socket proxy."

The archived SSH spec (lines 32-34) confirms the assumption was Docker Desktop as canonical proof target. `resolve_host_ssh_auth_sock()` (lines 254-262) also falls back to `launchctl getenv SSH_AUTH_SOCK` because macOS launchd registers the agent socket and it is not always in the process environment — a macOS-specific quirk.

The explicit documented reason is **(b) Docker-on-macOS cannot reliably relay a Unix domain socket through the Linux VM boundary into the container**. A bind-mounted Unix socket appears in the container filesystem but the underlying transport goes through the hypervisor; the SSH agent protocol requires low-latency bidirectional framing that does not survive that path reliably. The TCP relay via `host.docker.internal` is the supported cross-VM transport on Docker Desktop and Colima.

### [EVIDENCE:L5-original-motivation]

Commit `d237aef` (sole commit, no motivating prose). `AGENTS.md` lines 12-16 (explicit doc rationale). `docs/archive/spec/2026-03-22-devcontainer-ssh-login-plan.md` lines 32-34 (original Docker Desktop assumption). `devcontainer.py` lines 254-262 (`launchctl` fallback = macOS-only path).

### [CONFIDENCE:HIGH]

(Doc rationale is explicit; commit message is silent on motivation but the AGENTS.md policy statement is unambiguous.)

---

## [FINDING:L5-tech-debt-verdict]

**Current, intentional workaround for a real and still-present platform constraint — not accidental tech debt.** The constraint it works around is well-established: Unix socket bind mounts through the Docker Desktop / Colima hypervisor layer (HVF or VZ+Rosetta) do not produce a functional SSH agent socket inside the AMD64 Linux container on macOS ARM. This is not a bug that has been fixed upstream; it is an architectural boundary between the macOS socket namespace and the Linux VM namespace.

The devcontainer spec offers `forwardAgent` via VS Code's remote-SSH extension, but that requires VS Code as the launch surface — this repo deliberately uses a terminal-only `uv run cpp-playground devcontainer up` path with no VS Code dependency. There is no `forwardAgent`, no `mountSSHSocket`, and no `sshd` feature in `devcontainer.json` because the control plane does all of this itself. The proxy is the correct solution for a CLI-first, editor-agnostic devcontainer workflow on macOS.

### [EVIDENCE:L5-tech-debt-verdict]

`AGENTS.md` lines 12-16 (explicit policy statement naming the constraint). `devcontainer.json` (no `forwardAgent`, no socket bind mount of `$SSH_AUTH_SOCK`, only the host-state directory bind mount at line 50-51). `devcontainer.py` lines 254-262 (`launchctl` fallback confirms macOS-launchd-specific design). Commit `d237aef` is the only commit — the proxy arrived fully formed in a consolidation refactor.

### [CONFIDENCE:HIGH]

[STAGE_COMPLETE:5]

## GitHub repos touched

- [ray-manaloto/cpp-playground](https://github.com/ray-manaloto/cpp-playground) — primary subject; `devcontainer.py`, `AGENTS.md`, `devcontainer.json`, and archive spec docs read directly from the local clone
