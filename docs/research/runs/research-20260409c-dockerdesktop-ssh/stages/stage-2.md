# Stage 2 — Custom Python proxy deletion feasibility

## Requirements matrix

| Requirement | Current path (custom proxy) | Native path (`/run/host-services/ssh-auth.sock`) | Notes |
|---|---|---|---|
| R1 inbound (`ssh $USER@localhost -p 4444`) | Satisfied via sshd feature + authorized_keys copy | Satisfied — unchanged | Orthogonal to agent forwarding. `devcontainer.json:84-93` |
| R2 outbound (`ssh -T git@github.com`) | Satisfied via host-TCP→container-unix-socket bridge (`docker.py:267-425`) | Satisfied via Docker Desktop's magic socket bind-mounted + `SSH_AUTH_SOCK` pointing at it | Docker Desktop injects host launchd agent into `/run/host-services/ssh-auth.sock` on macOS |
| R3 amd64 | Orthogonal | Orthogonal | Controlled by `--platform=linux/amd64/v2` (`devcontainer.json:52`) |
| Audit (`audit_ssh`, `audit.py:473`) | Probes `/tmp/dotfiles-ssh-agent-proxy.log` (`audit.py:511`); 3s timeout on `ssh-add -l` | `ssh-add -l` works against native socket; log path disappears → audit check must be updated or removed | Loud-failure path `BRIDGE_UNREACHABLE` (`docker.py:131-138`) becomes dead code |
| IDE-attach (VS Code) | Works via extension auto-forward (orthogonal) | Works via extension auto-forward (orthogonal) | Neither path regresses the IDE lane |

## Findings

[FINDING:S2F1] The custom proxy exists solely to satisfy R2, and Docker Desktop's native `/run/host-services/ssh-auth.sock` is a drop-in replacement on this runtime. [/FINDING]

[EVIDENCE:S2F1]
- `docker.py:267-338` spawns a TCP proxy targeting `$SSH_AUTH_SOCK`
- `docker.py:364-425` spawns the container-side unix-socket listener at `CONTAINER_SSH_PROXY_SOCKET` (`/tmp/dotfiles-ssh-agent.sock`) forwarding to `host.docker.internal:<port>`
- Entire dataflow is "pipe bytes from container unix socket → launchd agent," identical semantics to bind-mounting the magic socket directly
- Prior research (`research-20260407`) rejected the native path because it assumed Colima; the active runtime is Docker Desktop (user-confirmed context)
[/EVIDENCE]

[CONFIDENCE:HIGH]

[FINDING:S2F2] Replacement requires only three devcontainer.json edits: add a bind mount of `/run/host-services/ssh-auth.sock:/run/host-services/ssh-auth.sock`, change `containerEnv.SSH_AUTH_SOCK` to `/run/host-services/ssh-auth.sock`, and drop the `initializeCommand`/`postStartCommand`/`postCreateCommand` proxy invocations. [/FINDING]

[EVIDENCE:S2F2]
- `devcontainer.json:70` (bind mount of state dir)
- `devcontainer.json:82` (SSH_AUTH_SOCK)
- `devcontainer.json:91,93,94` (lifecycle commands)
- No other consumer of `/tmp/dotfiles-ssh-agent.sock` exists in source
[/EVIDENCE]

[CONFIDENCE:HIGH]

[FINDING:S2F3] The `build.ssh-r2-outbound-proxy-wired` verification contract (`suites.toml:125-134`) hard-codes proxy-specific tokens and must be rewritten (not deleted) so R2 remains gated. [/FINDING]

[EVIDENCE:S2F3]
- Required tokens list: `"dotfiles-setup docker start-container-proxy"`, `"/tmp/dotfiles-ssh-agent.sock"`
- New contract should require `"/run/host-services/ssh-auth.sock"` in both the mounts array and `containerEnv`
[/EVIDENCE]

[CONFIDENCE:HIGH]

[FINDING:S2F4] `audit_ssh` in `audit.py:473` hard-references the proxy log file at `/tmp/dotfiles-ssh-agent-proxy.log` (`audit.py:511`); its loud-failure path (3s `TimeoutExpired` → `AuditError`) was added to catch proxy hangs and becomes moot under the native path. The audit must be simplified to just `ssh-add -l` with a reachability check on the new socket. [/FINDING]

[EVIDENCE:S2F4]
- `audit.py:473,511`
- `docker.py:107,120-138` (`UPSTREAM_CONNECT_TIMEOUT_SECONDS`, `BRIDGE_UNREACHABLE`, PR #77 context in commit 5a9de96)
[/EVIDENCE]

[CONFIDENCE:HIGH]

## Deletion manifest

Becomes dead code once the native path ships:

- `python/src/dotfiles_setup/docker.py:28` — `DEFAULT_HOST_STATE_DIR`
- `docker.py:29` — `HOST_PROXY_HOST`
- `docker.py:31-33` — `HOST_SSH_PROXY_{PID,PORT,TARGET}_FILE`
- `docker.py:36-52` — `host_state_dir()` (still used by authorized_keys; keep a trimmed version for R1)
- `docker.py:61-104` — `_collect_public_keys_from_agent`, `_write_host_authorized_keys`, `_resolve_host_ssh_auth_sock` — **KEEP** first two for R1 authorized_keys flow; delete `_resolve_host_ssh_auth_sock`
- `docker.py:107-175` — `_proxy_connection` (including `BRIDGE_UNREACHABLE` path)
- `docker.py:178-228` — `serve_proxy`
- `docker.py:231-234` — `_choose_host_ssh_proxy_port`
- `docker.py:237-264` — `_stop_proxy`, `_wait_for_unix_socket`, `_wait_for_tcp_port`
- `docker.py:267-338` — `initialize_host_ssh_runtime` (replace with authorized_keys-only variant for R1)
- `docker.py:341-349` — `stop_host_ssh_runtime`
- `docker.py:364-425` — `ensure_container_ssh_proxy`
- `python/src/dotfiles_setup/audit.py:473-511` — proxy log probing in `audit_ssh`; simplify to plain `ssh-add -l`
- `python/src/dotfiles_setup/config.py` — `CONTAINER_HOST_STATE_DIR`, `CONTAINER_SSH_PROXY_PID_FILE`, `CONTAINER_SSH_PROXY_SOCKET`, `container.host_state_dir` field
- `.devcontainer/devcontainer.json:70` — `/tmp/dotfiles-host-state` bind mount (replace with `/run/host-services/ssh-auth.sock` bind mount)
- `devcontainer.json:82` — `SSH_AUTH_SOCK` value change
- `devcontainer.json:91` — strip `dotfiles-setup docker initialize-host` (keep mkdir for authorized_keys staging)
- `devcontainer.json:93` — strip `dotfiles-setup docker start-container-proxy` (keep authorized_keys install + known_hosts)
- `devcontainer.json:94` — delete entire `postStartCommand`
- `mise.toml [tasks.down]:368` — `dotfiles-setup docker stop-host-proxy || true`
- `python/verification/suites.toml:125-134` — rewrite contract tokens
- CLI subcommands: `docker initialize-host`, `docker start-container-proxy`, `docker stop-host-proxy`, `docker proxy` — delete wiring
- Env var `DOTFILES_HOST_STATE_DIR` — remove from Pydantic settings and docs

Retained: `_collect_public_keys_from_agent` + `_write_host_authorized_keys` still drive the R1 sshd `authorized_keys` flow (`devcontainer.json:93` `postCreateCommand` reads `/tmp/dotfiles-host-state/authorized_keys`). The R1 path needs *some* host-state bind mount for the keys file unless we migrate keys delivery into the overlay Dockerfile.

## Residual risk

1. **Host-state bind mount is still needed for R1 authorized_keys delivery** unless key staging moves elsewhere. Cheapest option: keep a tiny state dir with *only* `authorized_keys`, drop the PID/port/target files. Alternative: bake a post-create hook that runs `ssh-add -L` from *inside* the container via the now-working native agent — but this requires the container to already have a usable agent, chicken-and-egg unless we keep the host-side write.
2. **Docker Desktop version floor**: the magic socket exists in Docker Desktop 2.2+ (well below 29.3.1). No risk on the current pin, but `.devcontainer/AGENTS.md` should note the runtime dependency.
3. **Colima regression**: if a future contributor switches back to Colima, R2 silently breaks (Colima has no magic socket — `abiosoft/colima#1330`). Add a `docker info` probe at `mise run up` that refuses to proceed if the server is not Docker Desktop, OR document the runtime dependency loudly in `.devcontainer/AGENTS.md`.
4. **`devcontainer.json` schema**: bind-mounting `/run/host-services/ssh-auth.sock` is a plain `type=bind` mount — no feature or plugin needed. Docker Desktop auto-creates the source path on the host VM. Devcontainers CLI passes the mount string through to `docker run` unchanged.
5. **Audit loud-failure path loss**: the PR #77 `BRIDGE_UNREACHABLE` detection was added after a 50-minute silent hang. The replacement audit must still probe `ssh-add -l` with a timeout so a dead/unshared agent surfaces fast.

## Verdict

**YES — the custom Python proxy can be deleted in favor of `/run/host-services/ssh-auth.sock`, with HIGH confidence**, contingent on (a) committing to Docker Desktop as the supported runtime, (b) preserving a minimal host-state path for R1 authorized_keys, and (c) rewriting the `ssh-r2-outbound-proxy-wired` contract.

## Test plan for the deletion

1. **Pre-flight probe (before editing anything)**: on a running container under the *current* proxy setup, run `docker run --rm -v /run/host-services/ssh-auth.sock:/ssh-agent -e SSH_AUTH_SOCK=/ssh-agent --platform=linux/amd64/v2 alpine/git sh -c 'apk add openssh-client && ssh -o StrictHostKeyChecking=accept-new -T git@github.com'`. If this returns `successfully authenticated` on the bare alpine container, the native path is proven on this Mac before touching any project code.
2. **Branch + minimal diff**: create branch, apply devcontainer.json edits (mount + env + lifecycle strip) WITHOUT deleting Python code yet. `mise run down && mise run up`. Run `mise run verify-local` (R1+R3 gates) and `scripts/devcontainer-smoke.sh` tier 3 (R2 gate: `ssh -T git@github.com` from inside container).
3. **Inside-container validation**: `devcontainer exec -- ssh-add -l` (must list host keys), `devcontainer exec -- ssh -T git@github.com` (must return `Hi <user>! You've successfully authenticated`), `devcontainer exec -- git ls-remote git@github.com:ray-manaloto/dotfiles.git` (must succeed).
4. **Rebuild/restart cycle**: `mise run down && mise run up` twice in a row to confirm no stale-state dependency (the prior proxy had PID-file liveness issues — native path should survive trivially).
5. **Only after steps 1-4 pass**: delete the Python proxy code, update `audit.py`, rewrite `suites.toml` contract, run `hk run pre-commit --all --stash none` + `uv run --project python pytest tests/ -x -q` + `dotfiles-setup verify run`.
6. **Regression guard**: add a new verification contract `build.ssh-r2-outbound-native-docker-desktop-wired` requiring the magic socket tokens in `devcontainer.json` so a future revert to the custom proxy cannot silently land.
7. **Runtime guard** (optional but recommended): in `mise run up`, probe `docker info --format '{{.Name}}'` — if not `desktop-linux`, fail loud with a message pointing at Colima-incompatibility.

[STAGE_COMPLETE:2]

## GitHub repos touched

- [devcontainers/cli](https://github.com/devcontainers/cli) — verified no native SSH_AUTH_SOCK forwarding; spec passes mounts verbatim
- [abiosoft/colima](https://github.com/abiosoft/colima) — issues #1330, #942 (no host-services socket equivalent); relevant to residual risk #3
- [docker/docs](https://github.com/docker/docs) — authoritative Docker Desktop SSH-agent forwarding doc (`/run/host-services/ssh-auth.sock`)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject repo; all file:line refs above
