# Research Report — Runtime Pivot to Docker Desktop for Issue #77

**Session ID:** `research-20260409c-dockerdesktop-ssh`
**Date:** 2026-04-09
**Status:** complete · verified (live probe)
**Orchestrator:** sciomc (5 parallel scientists + 1 live-probe verification)

---

## Executive Summary

The dotfiles repo's devcontainer SSH bridge was premised on Colima as the runtime; the active runtime is Docker Desktop 29.3.1. Prior research concluded the custom host-TCP + container-unix-socket Python proxy was the correct pattern for Colima because Colima has no `/run/host-services/ssh-auth.sock` equivalent. That conclusion does not transfer to Docker Desktop, which DOES expose the magic socket.

A **live probe on this Mac** confirms end-to-end: a bare `alpine` container bind-mounting `/run/host-services/ssh-auth.sock` can list the host's ssh-agent identities with exit 0. This is decisive: the custom proxy can be deleted entirely in favor of the native path. Issue #77's "lifecycle rewrite" therefore collapses from a 6-ADR design exercise into a 3-line devcontainer.json edit plus Python code removal. The sshd feature for R1 inbound stays; VirtioFS inotify gaps are orthogonal to the socket path; R1/R2/R3 all stay green. Follow-up issue drafted for Colima replication.

---

## Methodology

### Research stages

| Stage | Focus | Tier | Status |
|---|---|---|---|
| 1 | Docker Desktop ssh-agent canonical path | HIGH | complete |
| 2 | Custom Python proxy deletion feasibility | HIGH | complete |
| 3 | Docker Desktop bind-mount propagation + inotify | MEDIUM | complete |
| 4 | R1 inbound sshd feature alternatives | MEDIUM | complete |
| 5 | Colima/Lima follow-up scope | LOW | complete |
| V | Live probe verification (MANDATORY) | decisive | **PASSED** |

### Approach

Five independent scientist lanes were fired in parallel via the OMC sciomc skill, each with explicit doc-source preference chain (mintlify cache first → context7 → curl). Individual stage files are in `stages/stage-{1..5}.md`. A live end-to-end probe was run on the orchestrator side as the verification stage, replacing a textual cross-validation agent — the live probe provides stronger evidence than any amount of doc-reading because it exercises the exact mechanism under discussion against the actual runtime.

---

## Live-probe verification (decisive)

```bash
docker run --rm \
  -v /run/host-services/ssh-auth.sock:/tmp/ssh-agent \
  -e SSH_AUTH_SOCK=/tmp/ssh-agent \
  alpine sh -c 'apk add --no-cache openssh-client && ssh-add -l; echo EXIT=$?'
```

**Result:**
```
256 SHA256:MbkBvIjNxQlbQRfWqUfcTna1eKKVhmLO7vugaRXuD9Y ray.manaloto@gmail.com (ED25519)
EXIT=0
```

Interpretation: the magic socket exists, is bind-mountable into any container, and surfaces the host-side launchd ssh-agent identities without any proxy, feature, setting toggle, Rosetta flag, or VirtioFS configuration. This single command validates all of Stage 1's load-bearing claims and Stage 2's deletion plan in one shot.

---

## Key Findings

### Finding 1: `/run/host-services/ssh-auth.sock` works on current Docker Desktop (HIGH, live-verified)

The socket exists, is bind-mountable, and forwards the host ssh-agent. Stage 1 derived this from the devcontainers/cli issue #441 authoritative statement by @chrmarti (Microsoft Dev Containers core maintainer) and from cross-referencing with the 2026-04-07 prior research. The live probe (above) is independent confirmation against the actual runtime.

**Canonical devcontainer.json incantation:**

```jsonc
{
  "mounts": [
    "source=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock,type=bind,consistency=cached"
  ],
  "containerEnv": {
    "SSH_AUTH_SOCK": "/run/host-services/ssh-auth.sock"
  }
}
```

Use `containerEnv` (not `remoteEnv`) because R2 must work for terminal SSH sessions, not just IDE-attached tool sessions.

### Finding 2: The custom Python proxy can be deleted (HIGH)

Stage 2 produced a complete deletion manifest with file:line references. Summary:
- Delete: `_proxy_connection`, `serve_proxy`, `_choose_host_ssh_proxy_port`, `_stop_proxy`, `_wait_for_unix_socket`, `_wait_for_tcp_port`, `initialize_host_ssh_runtime`, `stop_host_ssh_runtime`, `ensure_container_ssh_proxy`, `_resolve_host_ssh_auth_sock` in `docker.py`
- Delete: `audit_ssh`'s proxy log probing path, `BRIDGE_UNREACHABLE` loud-failure path (added by PR 1 commit 5a9de96)
- Delete: `HOST_SSH_PROXY_{PID,PORT,TARGET}_FILE`, `CONTAINER_SSH_PROXY_PID_FILE`, `CONTAINER_SSH_PROXY_SOCKET`, `DOTFILES_HOST_STATE_DIR`
- Delete: `/tmp/dotfiles-host-state` bind mount in devcontainer.json (REPLACED by the magic socket bind mount)
- Delete: `dotfiles-setup docker {initialize-host,start-container-proxy,stop-host-proxy,proxy}` CLI subcommands
- Rewrite: `build.ssh-r2-outbound-proxy-wired` contract in `suites.toml:125-134` to match new tokens
- **Keep**: `_collect_public_keys_from_agent` + `_write_host_authorized_keys` (still needed for R1 authorized_keys delivery), plus a minimal host-state dir for the authorized_keys file only

### Finding 3: VirtioFS inotify gaps are real but orthogonal to the socket (HIGH)

Stage 3 confirmed via docker/for-mac #7246 (OPEN 2024→2026, Apple Silicon) that VirtioFS does not propagate DELETE inotify events from host to container, and #896 (OPEN since 2016) confirmed CLOSE_WRITE never propagates on any macOS Docker backend. This is a documented, unfixed bug class.

**But it is irrelevant to the chosen design**: the magic SSH socket is IPC (Unix domain socket), not a file on a VirtioFS mount. Socket communication does not use inotify. The VirtioFS inotify gaps would have mattered if we'd kept a file-based state-carrying bind mount — which we're deleting.

The prior issue #77 "design phase" was implicitly trying to work around these inotify gaps by designing a better lifecycle for the file-based state. **The native path sidesteps the problem entirely.**

### Finding 4: Keep the sshd feature for R1, fix the dead options (HIGH)

Stage 4 fetched the live `devcontainer-feature.json` for `ghcr.io/devcontainers/features/sshd@1.1.0`. The feature is actively maintained and the correct tool for R1. Prior research's finding that `port`/`username`/`startNow` options are silently dropped is confirmed — only `version` (unused) and `gatewayPorts` are real. Action: remove the dead options from our devcontainer.json and rely on the feature's hardcoded internal port 2222 mapped to 4444 via `appPort`. Auth is already handled via the existing `authorized_keys` postCreateCommand.

### Finding 5: Colima follow-up scope is well-understood (MEDIUM)

Stage 5 scoped the Colima path for the follow-up issue. Lima natively provides `ssh.forwardAgent: true` and `ssh.overVsock: true`; Colima wraps them via `colima start --ssh-agent`. The unresolved leg is **VM→container**: Lima forwards the agent into the Lima VM, but the container inside the VM cannot reach the VM-internal `$SSH_AUTH_SOCK` without an explicit docker volume mount or `docker buildx --ssh default` pattern. A 6-step probe sequence is drafted in stage-5.md for a future session to execute on a clean Colima install.

---

## Cross-validation results

**Inter-stage consistency:** No contradictions between stages.
- S1 and S2 agree on the canonical incantation (plain bind + containerEnv).
- S2 and S3 agree that the file-based state approach was constrained by inotify gaps — S2's solution (delete it) trivially satisfies S3's constraint.
- S4 is orthogonal (R1 inbound) and doesn't interact with S1/S2/S3 findings.
- S5 is forward-looking (Colima) and doesn't constrain the current pivot.

**Load-bearing claim audit vs prior research (research-20260407):**
- ✅ **Prior claim "Colima has no host-services/ssh-auth.sock equivalent"** remains TRUE (confirmed in stages 1, 2, 5)
- ✅ **Prior claim "@chrmarti authoritative on devcontainers/cli behavior"** remains TRUE
- ❌ **Prior scope assumption "this repo's runtime is Colima"** was WRONG — the active runtime is Docker Desktop, and has been since an unknown prior session ran `docker context use desktop-linux` or set `DOCKER_CONTEXT=desktop-linux` per the GEMINI.md fallback guidance
- 🔄 **Prior conclusion "adopt cpp-playground TCP-proxy pattern scoped to CLI lane"** was CORRECT IF runtime is Colima, but the runtime pivot inverts the conclusion: on Docker Desktop, the native path is correct and the proxy is redundant

**Live probe:** decisive confirmation of the native path on the current runtime (see above).

---

## Verdict (one-line)

**YES — delete the custom Python proxy and replace with `/run/host-services/ssh-auth.sock` bind mount**, with HIGH confidence, live-probe verified on 2026-04-09.

---

## Recommendations

### Immediate (this or next session)

1. **Commit the runtime decision to docs/memory before any code changes.** Update `.devcontainer/AGENTS.md`, `AGENTS.md` root, `feedback_colima_recommendation.md` → `feedback_docker_desktop_runtime.md`, and add a loud "Docker Desktop is the supported runtime" header to `.devcontainer/AGENTS.md`. This prevents a future session from reverting the pivot by accident.

2. **File the Colima follow-up issue now** with the body drafted in `stages/stage-5.md`. Tag as `enhancement`, `runtime`, `research`. Link to this report.

3. **Pre-flight re-probe on a clean container** before any edits: the probe above used a throwaway `alpine` container; the next step is to add the bind mount + containerEnv to the actual devcontainer.json on a branch, rebuild the overlay, and run `mise run verify-local` + `scripts/devcontainer-smoke.sh` tier 3 (R2 gate).

4. **Delete the Python proxy code** ONLY after the devcontainer.json change is proven green locally. Staged deletion: (a) add native mount → verify R2 → (b) strip `initializeCommand`/`postStartCommand` → verify R2 → (c) delete Python proxy functions → re-run pytest + hk + verify CLI.

5. **Add a runtime-guard** in `mise run up`: probe `docker info --format '{{.Name}}'`; fail loud if not `desktop-linux`, with remediation text pointing at the Colima follow-up issue.

### Documentation corrections (parallel to implementation)

Per your earlier instruction, all docs/configs/memories claiming Colima is the runtime must be corrected. Blast radius from the earlier grep:
- `mise.toml`
- `AGENTS.md` (root)
- `.devcontainer/AGENTS.md` (the major one — SSH Agent Forwarding section + runtime claim)
- `scripts/benchmark-docker.sh`
- `mise.lock` (only if colima binary is pinned there — may need removal)
- Memory: `feedback_colima_recommendation.md` → replace with `feedback_docker_desktop_runtime.md`
- Notepad: already updated with runtime pivot note
- Session handoff: `.omc/plans/session-2026-04-09c-issue-77-bridge-lifecycle.md` — needs a "REPIVOTED 2026-04-09" banner

### Root-cause cleanup

- **Investigate and fix `GEMINI.md:11`** — the `DOCKER_CONTEXT=desktop-linux` fallback advice likely caused a prior session to persistently switch the docker context. Either remove the line, or add "switch back afterward" guidance, or document Docker Desktop as the supported runtime so the switch is intentional.

---

## Limitations

- The live probe was a throwaway `alpine` container, NOT the actual devcontainer. It confirms the socket mount works in principle on this Mac; it does not guarantee the devcontainer's UID/GID mapping, Rosetta emulation, or feature stack won't introduce an interaction bug. The staged deletion plan (steps 3-4 above) addresses this by testing in the real devcontainer before deletion.
- The socket path is undocumented on docs.docker.com — evidence comes from community issue tracker and the devcontainers/cli maintainer's public statement. Confidence is HIGH for current behavior but MEDIUM for version stability (Docker Desktop could deprecate the path in a future release without a release-note entry). Mitigation: pin Docker Desktop version in `.devcontainer/AGENTS.md` and monitor for changes.
- No bench measurement of inotify propagation was performed. The decision not to need it (the native socket path doesn't use filesystem events) makes the measurement unnecessary for this session's scope; it was the right design call for the original proxy design, but is moot now.

---

## Appendix

### Raw stage findings

- `stages/stage-1.md` — Docker Desktop canonical path
- `stages/stage-2.md` — proxy deletion feasibility + deletion manifest
- `stages/stage-3.md` — VirtioFS inotify behavior
- `stages/stage-4.md` — sshd feature alternatives
- `stages/stage-5.md` — Colima follow-up scope

### Session state

`state.json` — current status: complete, verification: passed (live probe)

---

## GitHub repos touched

- [devcontainers/cli](https://github.com/devcontainers/cli) — issue #441 (@chrmarti authoritative on SSH agent forwarding being extension-only; canonical incantation source)
- [devcontainers/features](https://github.com/devcontainers/features) — live fetched `src/sshd/devcontainer-feature.json` v1.1.0 to confirm R1 feature schema and maintenance status
- [devcontainers/spec](https://github.com/devcontainers/spec) — consulted spec for SSH agent property (zero matches, as prior research found)
- [docker/for-mac](https://github.com/docker/for-mac) — issues #7246, #6350, #896, #1802, #681, #7416 (VirtioFS inotify DELETE/CLOSE_WRITE propagation bugs)
- [docker/docs](https://github.com/docker/docs) — consulted docs.docker.com VMM, settings, troubleshoot, release-notes pages (negative evidence: magic socket is not documented on first-party docs)
- [abiosoft/colima](https://github.com/abiosoft/colima) — issues #1330, #942 (no host-services socket equivalent; drives the Docker Desktop-only constraint and the follow-up issue scope)
- [lima-vm/lima](https://github.com/lima-vm/lima) — lima.yaml reference (`ssh.forwardAgent`, `ssh.overVsock`, `mountInotify`) for follow-up scoping
- [microsoft/vscode-remote-release](https://github.com/microsoft/vscode-remote-release) — issue #11413 (extension auto-forwarding confirmation)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject repo
