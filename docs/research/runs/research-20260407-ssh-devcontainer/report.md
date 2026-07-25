# Research Report — Canonical SSH Agent Forwarding into a Dev Container on macOS-ARM/Colima

**Session ID:** `research-20260407-ssh-devcontainer`
**Date:** 2026-04-07
**Status:** complete · verified
**Orchestrator:** sciomc (5 parallel scientists + 1 verification pass)

---

## Executive Summary

The dotfiles repo's devcontainer SSH model is broken in three independent ways stacked together: (1) `ghcr.io/devcontainers/features/sshd:1` is configured with options that don't exist in its schema (`port`, `username`, `startNow`) and silently uses its hardcoded port 2222 — making `ssh -p 4444` from the host fail; (2) the readonly bind-mount of `~/.ssh` carries the host's encrypted private key + macOS-only `UseKeychain` directive into a Linux container that has no Keychain to unlock the key; (3) there is no SSH_AUTH_SOCK forwarding at all, so no agent path exists for git push from inside the container.

The five-lane research established that **`@devcontainers/cli` does not auto-forward the host SSH agent** (Microsoft maintainer @chrmarti, devcontainers/cli#441), the **devcontainer.json spec defines no native SSH-agent property** (zero matches across all three schema files), and the **`sshd` feature is the wrong tool** (its purpose per README is letting external clients ssh INTO the container, not agent forwarding OUT). Verification independently confirmed that **Colima specifically has no `host-services/ssh-auth.sock` equivalent** and does not pass `$SSH_AUTH_SOCK` through the VM boundary (Colima issues #1330, #942) — meaning the manual `mounts` + `${localEnv:SSH_AUTH_SOCK}` workaround documented for Docker Desktop **will not work on this repo's runtime**.

The cpp-playground host-TCP + container-unix-socket proxy pattern is therefore **not legacy debt — it's the correct, intentional, and currently-only solution for the CLI lane on macOS-ARM + Colima**. However, verification surfaced one critical gap-fill: the **VS Code Dev Containers extension auto-forwards the agent** (vscode-remote-release#11413, currently in active use), so users attaching via VS Code already get git push for free. Only the CLI lane (`mise run up` + `devcontainer exec` + raw `docker exec`) actually needs the proxy. This sizes the fix down considerably.

---

## Methodology

### Research stages

| Stage | Focus | Tier | Status |
|-------|-------|------|--------|
| 1 | containers.dev spec authority | MEDIUM | complete |
| 2 | @devcontainers/cli implementation | MEDIUM | complete |
| 3 | VS Code Dev Containers SSH credentials docs | MEDIUM | complete |
| 4 | devcontainers/features/sshd reality check | LOW | complete |
| 5 | cpp-playground proxy tech-debt audit | MEDIUM | complete |
| V | Cross-validation + load-bearing-claim audit | (opus) | passed |

### Approach

Five independent lanes were fired in parallel via the OMC scientist subagent. Each lane had a single research question, an exact list of probes (raw GitHub URLs, GitHub API search, local file reads), and a hard word cap to keep outputs evidence-only. After all five returned, an opus verification pass was run to (a) check for inter-lane contradictions, (b) independently re-probe two load-bearing claims, and (c) surface gaps the original lanes did not address.

---

## Key Findings

### Finding 1: containers.dev spec defines no SSH agent property

**Confidence:** HIGH
**Source:** stages/stage-1.md

The devcontainer spec at `github.com/devcontainers/spec` has zero references to `ssh`, `agent`, `forwardAgent`, `mountSSHSocket`, or `socket` across all three JSON schema files (`devContainer.base.schema.json`, `devContainer.schema.json`, `devContainerFeature.schema.json`). The canonical workaround is the general-purpose `mounts` property combined with `${localEnv:SSH_AUTH_SOCK}` and `remoteEnv` — but this is community pattern, not spec-defined. Implementation responsibility is left entirely to the orchestrator (VS Code extension or CLI).

### Finding 2: @devcontainers/cli does nothing automatic

**Confidence:** HIGH
**Source:** stages/stage-2.md

Microsoft maintainer @chrmarti in devcontainers/cli#441 (open):
> "The ssh-agent forwarding is part of the Dev Containers extension and not part of the Dev Containers CLI. You could mount the ssh-agent's socket and then point SSH_AUTH_SOCK at it."

CLI source has zero `SSH_AUTH_SOCK` references. The manual `mounts` + `remoteEnv` pattern works only when `${localEnv:SSH_AUTH_SOCK}` resolves non-empty (devcontainers/cli#1190 — open in v0.85.0 — Docker rejects empty source).

### Finding 3: VS Code extension auto-forwards; CLI does not

**Confidence:** HIGH
**Source:** stages/stage-3.md + verification

VS Code's official sharing-git-credentials page:
> "The extension will automatically forward your local SSH agent if one is running."
> "macOS typically has it running by default."

Confirmed for the GUI extension. Confirmed NOT inherited by the npm CLI. Critical gap-fill from verification: vscode-remote-release#11413 ("Add setting to disable automatic SSH agent forwarding in Dev Containers") proves the extension auto-forward is on by default and active in current versions. Users attaching via VS Code "Attach to Running Container" get git push for free.

### Finding 4: sshd feature is the wrong tool, options are silently ignored

**Confidence:** HIGH
**Source:** stages/stage-4.md

Valid options on `ghcr.io/devcontainers/features/sshd` are exactly `version` and `gatewayPorts`. The `port`, `username`, and `startNow` options used in the dotfiles `devcontainer.json` do not exist in the schema and are silently dropped. The feature's documented purpose is *"to use an external terminal, sftp, or SSHFS to interact with [the container]"* — i.e., SSH INTO the container, not agent forwarding OUT. `install.sh` installs `openssh-server` on the hardcoded port 2222 with no mention of `SSH_AUTH_SOCK`, no `authorized_keys` setup, and no agent forwarding.

### Finding 5: cpp-playground proxy is intentional, not legacy debt

**Confidence:** HIGH
**Source:** stages/stage-5.md

cpp-playground/AGENTS.md states verbatim:
> "On macOS with Docker Desktop, do not assume a bind-mounted host UNIX socket is a usable SSH agent inside the Linux container. This repo's checked-in path is a host-local TCP proxy plus a container-local UNIX socket proxy."

The Python TCP+unix-socket proxy works around the macOS launchd-Keychain → Linux-VM socket boundary. It is the intentional, current solution for a CLI-first devcontainer workflow on macOS. The constraint applies identically to dotfiles (Colima VZ+Rosetta has the same VM boundary; verification confirmed Colima has no `host-services/ssh-auth.sock` equivalent).

### Verification finding (gap-fill): only the CLI lane is broken

**Confidence:** HIGH
**Source:** stages/verification.md

VS Code Dev Containers extension auto-forwards (vscode-remote-release#11413 active). JetBrains Gateway / CLion uses its own SSH-tunnel agent (MEDIUM confidence — not directly probed). **Only the `mise run up` + `devcontainer exec` + raw `docker exec` lane needs the proxy fix.** The fix is purely additive for IDE-attach users, not a blocker for them.

---

## Cross-validation results

**Result:** [VERIFIED]

- **Inter-lane consistency:** No contradictions found.
- **Load-bearing claim 1 (L5: Colima cannot bridge the SSH agent socket):** independently confirmed via Colima issues #1330 and #942, plus zero `host-services/ssh-auth.sock` equivalent in Colima docs.
- **Load-bearing claim 2 (L2/L3: chrmarti is authoritative):** confirmed — chrmarti = Christof Marti, Microsoft, consistent with Dev Containers maintainer status; zero `ssh-auth.sock` references in `org:devcontainers` code search corroborates.
- **Gap filled:** CLI lane vs IDE-attach lane separation. Only the CLI lane is broken. VS Code IDE-attach already works.

---

## Recommendation

**Adopt cpp-playground's host-TCP-proxy + container-unix-socket-proxy pattern, scoped to the CLI lane only.** Specifically:

1. **Delete** the broken sshd plumbing:
   - `features.ghcr.io/devcontainers/features/sshd` block in `devcontainer.json`
   - `appPort` and `forwardPorts`
   - The `~/.ssh` readonly bind mount (the encrypted host key + macOS-only ssh config can never work in Linux)
   - `DEVCONTAINER_SSH_PORT` task-scoped env in `mise.toml [tasks.up].env`
   - `mise.local.toml.example` `DEVCONTAINER_SSH_PORT` line
   - `_${PORT}` suffix from container name + named volume names (the port-collision-recovery design rationale evaporates with no port to map)
   - Constraint C12 ("internal sshd port stays literal 4444") references in `.devcontainer/AGENTS.md` and project memory

2. **Adopt** the proxy pattern (port from cpp-playground or write minimal in-tree):
   - Host helper: spawns a `serve_proxy(--listen-tcp 127.0.0.1:N --target-unix $SSH_AUTH_SOCK)` subprocess; writes the chosen port to `~/.local/state/dotfiles/ssh-agent-port`
   - Container helper: reads the port file from the bind-mounted host-state dir, runs `serve_proxy(--listen-unix /tmp/dotfiles-ssh-agent.sock --target-tcp host.docker.internal:N)`
   - Both halves are stdlib-only Python (no extra deps)

3. **Wire** lifecycle hooks in `devcontainer.json`:
   - `initializeCommand` (host): spawn host proxy, fail loud if `$SSH_AUTH_SOCK` is unreachable on macOS (with `launchctl getenv SSH_AUTH_SOCK` fallback per cpp-playground line 254-262)
   - `postStartCommand` (container): spawn container proxy
   - `remoteEnv.SSH_AUTH_SOCK = /tmp/dotfiles-ssh-agent.sock`

4. **Rewrite** `scripts/devcontainer-smoke.sh` tier 3 to assert real success:
   - `SSH_AUTH_SOCK` is set to `/tmp/dotfiles-ssh-agent.sock` and the path exists
   - `ssh-add -L` returns ≥1 identity (proves the proxy reaches the host's keychain agent)
   - `ssh -T git@github.com` returns *"successfully authenticated"* (real auth completion now possible)

5. **Keep** the existing `~/.local/state/dotfiles` ↔ `/tmp/dotfiles-host-state` bind mount in `devcontainer.json:52` — that's already the channel for the proxy port file.

6. **Update** `.devcontainer/AGENTS.md`, project memory, and the deep-interview spec to document the new pattern and remove vestigial C12 references.

### Open follow-up question

Should the proxy helper be:
- (a) a hard-fork of cpp-playground's `serve_proxy` (port + adapt — faster, better-tested), or
- (b) a minimal new implementation in `python/dotfiles_setup/devcontainer.py` (~150 LOC, stdlib only — avoids drift)?

My recommendation: hard-fork to start, file an issue for "extract shared helper into a small standalone package both repos depend on."

---

## Limitations

- **CLion/JetBrains Gateway behavior is unverified.** The verification stage marked this MEDIUM-confidence. If CLion does NOT auto-forward like VS Code, the proxy needs to also kick in for that lane. Worth probing before final commit if CLion is in scope.
- **Issue #1190 (empty `${localEnv:SSH_AUTH_SOCK}` mount source) is open in CLI v0.85.0.** Even with the proxy, if dotfiles ever wants to fall back to direct mount on a non-Colima runtime, the empty-source guard issue still applies.
- **The cpp-playground `serve_proxy` implementation excerpt cited at lines 169-251 was not read end-to-end** (only summarized). A direct read should happen before porting.

---

## GitHub repos touched

- [devcontainers/spec](https://github.com/devcontainers/spec) — schemas + docs
- [devcontainers/cli](https://github.com/devcontainers/cli) — source, README, issues #441 + #1190
- [devcontainers/features](https://github.com/devcontainers/features) — sshd feature schema, install.sh, README
- [devcontainers-contrib/features](https://github.com/devcontainers-contrib/features) — zero ssh-agent features
- [microsoft/vscode-remote-release](https://github.com/microsoft/vscode-remote-release) — issues #11413, #4024, #8810, #6600
- [abiosoft/colima](https://github.com/abiosoft/colima) — issues #1330, #942 + FAQ
- [docker/for-mac](https://github.com/docker/for-mac) — `/run/host-services/ssh-auth.sock` is Docker-Desktop-specific
- [ray-manaloto/cpp-playground](https://github.com/ray-manaloto/cpp-playground) — `devcontainer.py`, `AGENTS.md`, `devcontainer.json`

## Appendix

### Stage findings (raw)

- [stages/stage-1.md](stages/stage-1.md) — containers.dev spec
- [stages/stage-2.md](stages/stage-2.md) — @devcontainers/cli source
- [stages/stage-3.md](stages/stage-3.md) — VS Code docs
- [stages/stage-4.md](stages/stage-4.md) — sshd feature reality check
- [stages/stage-5.md](stages/stage-5.md) — cpp-playground audit
- [stages/verification.md](stages/verification.md) — cross-validation

### Session state

- [state.json](state.json)
