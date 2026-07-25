# Stage 4 — R1 inbound sshd alternatives

## Current sshd feature schema (HEAD)

Source: `https://raw.githubusercontent.com/devcontainers/features/main/src/sshd/devcontainer-feature.json`
Version: **1.1.0** (fetched live 2026-04-09)

```json
{
  "id": "sshd",
  "version": "1.1.0",
  "options": {
    "version": { "type": "string", "default": "latest", "description": "Currently unused." },
    "gatewayPorts": { "type": "string", "enum": ["no","yes","clientspecified"], "default": "no" }
  },
  "entrypoint": "/usr/local/share/ssh-init.sh"
}
```

**Confirmed**: only `version` (unused) and `gatewayPorts` are valid options. The dotfiles
`devcontainer.json` currently passes `port`, `username`, and `startNow` — all three are silently
dropped. The feature's internal sshd is hardcoded to port 2222; the host-side mapping to 4444 is
done via `devcontainer.json` `appPort: ":4444"`. This is the correct wiring — the feature itself
has no port option to set.

## Findings

[FINDING:S4F1] The sshd feature is actively maintained (v1.1.0 at HEAD on main), Debian/Ubuntu only,
and its documented purpose exactly matches R1: *"use an external terminal… to interact with [the
container]"* — i.e., SSH INTO the container from the host. The feature's authentication model per
official docs requires `sudo passwd $(whoami)` on first start — i.e., **password auth**, not
key-based. No `authorized_keys` setup, no agent forwarding. Our requirement of "no password" is NOT
the feature's default behavior.
[/FINDING]
[EVIDENCE:S4F1] devcontainer-feature.json at HEAD (fetched live); mintlify cache llms-full.txt
lines 2028–2062 (the "Connecting" steps explicitly call for `sudo passwd`); prior research report
`.omc/research/research-20260407-ssh-devcontainer/report.md` line 74.
[/EVIDENCE]
[CONFIDENCE:HIGH — schema fetched live, docs confirmed via two independent sources]

[FINDING:S4F2] R1's "no password" requirement is NOT explained anywhere in AGENTS.md,
.devcontainer/AGENTS.md, or docs/research/ as a first-class rationale. The requirement appears as a
stated criterion in the devcontainer success table in AGENTS.md (line 163) without justification.
The closest implicit rationale from .devcontainer/AGENTS.md (line 172): the CLI lane (`mise run up`
+ `devcontainer exec`) needs R1 for non-IDE terminal access, because the VS Code Dev Containers
extension handles agent forwarding automatically but raw CLI/`docker exec` users do not get that.
[/FINDING]
[EVIDENCE:S4F2] AGENTS.md grep (r4); .devcontainer/AGENTS.md lines 54–57, 172–174; SSH research
report lines 16, 91.
[/EVIDENCE]
[CONFIDENCE:MEDIUM — rationale is implicit, not explicitly stated]

[FINDING:S4F3] `docker exec -it <container> bash` is insufficient for R1 because: (1) it requires
Docker CLI access and container name knowledge — not a stable external SSH endpoint; (2) it does
not satisfy `ssh $USER@localhost -p 4444` as a verification gate (`mise run verify-ssh-inbound`
runs that exact command); (3) the CLI lane research explicitly identifies the need for an SSH
endpoint for tools that speak SSH (SFTP, SSHFS, JetBrains Gateway).
[/FINDING]
[EVIDENCE:S4F3] AGENTS.md line 163 (gate is `mise run verify-ssh-inbound` which runs the ssh
command); SSH research report line 91.
[/EVIDENCE]
[CONFIDENCE:HIGH]

## R1 alternatives matrix

| Option | Works for R1? | Maintained? | Complexity | Recommended? |
|---|---|---|---|---|
| `ghcr.io/devcontainers/features/sshd:1` (current) | YES — with authorized_keys setup added | YES (v1.1.0, active) | Low — already wired, port mapping correct | YES — keep, fix auth |
| `docker exec -it <container> bash` | NO — not an ssh endpoint, wrong gate | n/a | Zero | NO |
| VS Code Remote Containers SSH forwarding | Partial — IDE users only, not CLI lane | YES | Zero config | NO — not CLI-lane |
| JetBrains Gateway SSH | Partial — IDE users only | YES | Low | NO — not CLI-lane |
| Custom Dockerfile sshd (no feature) | YES — full control over port/auth | Self-maintained | High — own init scripts, port config, sshd_config | Only if feature proves unusable |
| Docker Desktop container SSH | Does not exist as a product feature | n/a | n/a | NO |

## Verdict

**Keep the sshd feature.** It is the correct tool for R1, actively maintained, and already wired
with the right port mapping (internal 2222 → host 4444 via `appPort`). The three silently-dropped
options (`port`, `username`, `startNow`) in `devcontainer.json` should be removed as dead config.

The only gap is passwordless auth: the feature's default requires `sudo passwd` on first start.
To satisfy "no password" the container setup must either:
- Add the host user's `~/.ssh/id_*.pub` to `/home/$USER/.ssh/authorized_keys` during
  `initializeCommand` or `postCreateCommand`, OR
- Configure `sshd_config` to accept a known key via `postCreateCommand`.

This is a one-line `postCreateCommand` fix, not a feature replacement.

[STAGE_COMPLETE:4]

## GitHub repos touched

- [devcontainers/features](https://github.com/devcontainers/features) — fetched live sshd devcontainer-feature.json at HEAD; consulted mintlify cache docs for sshd feature schema and connection docs.
