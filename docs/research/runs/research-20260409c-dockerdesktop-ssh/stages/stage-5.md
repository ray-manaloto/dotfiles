# Stage 5 — Colima/Lima follow-up scope

## Lima native primitives to evaluate

- **`ssh.forwardAgent: true`** (lima.yaml) — Forwards the macOS SSH agent into the Lima VM at a predictable socket path. Enabled by default; Lima injects `$SSH_AUTH_SOCK` pointing to the forwarded socket inside the VM.
  - Source: https://www.mintlify.com/lima-vm/lima/reference/lima-yaml.md

- **`ssh.overVsock: true`** (lima.yaml, requires VZ + systemd ≥256 in guest) — Uses vsock channel instead of TCP port forwarding for SSH communication between host and guest. Reduces host-side port footprint; may provide cleaner socket-layer integration.
  - Source: https://www.mintlify.com/lima-vm/lima/reference/lima-yaml.md

- **`mountInotify: true`** (lima.yaml, Lima ≥0.21.0, experimental) — Relays host inotify events into guest writable mounts. Not directly SSH-related but signals Lima's event-forwarding architecture; could hint at whether other socket events are forwarded.
  - Source: https://www.mintlify.com/lima-vm/lima/config/mounts.md

## Colima wrappers

- **`colima start --ssh-agent`** — CLI flag that sets `ssh.forwardAgent: true` in the Lima config.
  - Source: https://colima.run/docs/configuration/

- **`colima start --mount-type virtiofs`** (requires VZ) — Switches mount backend from 9p to virtiofs for better performance. Does not affect SSH-agent forwarding directly.
  - Source: https://colima.run/docs/configuration/

## Unresolved gap: VM→container leg

**The critical unresolved question:** Lima/Colima forwards the macOS SSH agent into the Lima VM. The container inside the VM sees `$SSH_AUTH_SOCK=/path/to/forwarded/socket` set by the VM's sshd. However, **the container process still cannot reach that socket path** unless:

1. The socket is mounted from the VM into the container (via docker volume mount), OR
2. The Docker daemon inside the VM is configured to forward SSH-agent connections transparently (e.g., via `docker buildx` `--ssh` flag, which re-exposes the socket).

Neither of these is automatic. Lima forwards the agent to the VM, but Docker (and by extension, containers) do not have built-in logic to relay the VM-internal `$SSH_AUTH_SOCK` into containers without explicit configuration. The Docker daemon would need to:
- Mount the socket as a volume when containers are created, OR
- Support a flag like `docker run --ssh=default` to inject it

The first approach (manual volume mount) is visible and testable. The second (docker daemon auto-relay) is not currently a standard feature.

## Proposed follow-up issue body (draft for gh issue create)

**Title:** Evaluate Colima/Lima SSH-agent forwarding as Docker Desktop alternative

**Body:**

We currently rely on Docker Desktop's built-in SSH-agent forwarding for devcontainer workflows (`ssh -T git@github.com` inside the container). Docker Desktop passes `SSH_AUTH_SOCK` into containers transparently.

Colima (Lima-based) offers `colima start --ssh-agent`, which forwards the macOS SSH agent into the VM. However, the VM→container leg is not automatic: containers inside the VM would need either:

1. Explicit docker volume mount of the VM-internal socket, or
2. Docker daemon support for `--ssh=default` flag (similar to `docker buildx`), which auto-injects the socket.

This issue tracks evaluating whether option 1 (manual volume mount) is viable and how it compares to Docker Desktop in ease-of-use and reliability.

Acceptance criteria:
- [ ] Confirm `forwardAgent: true` correctly sets `$SSH_AUTH_SOCK` inside Lima VM
- [ ] Test whether container volume-mounting `$SSH_AUTH_SOCK` from the VM works reliably
- [ ] Verify `ssh -T git@github.com` succeeds from inside a container when SSH socket is mounted
- [ ] Compare reliability with Docker Desktop baseline (session 2026-04-09c findings)
- [ ] Document Colima startup sequence and socket mounting steps in devcontainer.json or docker-compose override

## Minimum probe sequence

1. Start Colima with SSH-agent forwarding and VZ:
   ```bash
   colima start --ssh-agent --vm-type vz --mount-type virtiofs
   ```

2. Verify `$SSH_AUTH_SOCK` is set inside the VM:
   ```bash
   limactl shell default echo $SSH_AUTH_SOCK
   ```

3. Verify the socket is accessible:
   ```bash
   limactl shell default ssh -T git@github.com
   ```

4. Start a test container and attempt to mount the socket:
   ```bash
   docker run -v $SSH_AUTH_SOCK:$SSH_AUTH_SOCK --rm alpine ssh -T git@github.com
   ```

5. If step 4 fails, verify whether `docker buildx` supports `--ssh default` inside Colima:
   ```bash
   docker buildx build --ssh default -f - . <<< "FROM alpine
   RUN apk add --no-cache openssh-client && ssh -T git@github.com"
   ```

6. If step 5 succeeds, document the `docker buildx --ssh` pattern as the viable path.

[STAGE_COMPLETE:5]

## GitHub repos touched

- [lima-vm/lima](https://github.com/lima-vm/lima) — SSH agent forwarding native primitives, lima.yaml schema
- [abiosoft/colima](https://github.com/abiosoft/colima) — CLI wrapper (`--ssh-agent` flag) and configuration defaults
