# Verification Stage — cross-validation of L1-L5

**Verifier model:** opus
**Result:** [VERIFIED] (with one clarifying gap-fill)

## [VERIFICATION_RESULT] VERIFIED

All five findings are internally consistent. Two load-bearing claims were independently re-probed and confirmed; one material gap (CLI lane vs IDE-attach lane) was filled.

---

## [L5_CLAIM_AUDIT]

L5's premise — *"bind-mounted host UNIX socket is not a usable SSH agent inside Linux container on macOS"* — is corroborated for **Colima specifically**. Colima issue #1330 ("Not mapping declared SSH_AUTH socket", open) and #942 ("VZ/Virtiofs SSH agent forward fails after stop/start", open) confirm Colima does NOT transparently pass `$SSH_AUTH_SOCK` through the VM boundary.

Colima FAQ has **zero** ssh-agent passthrough story — only `colima ssh` (VM shell), unrelated.

Docker Desktop's `/run/host-services/ssh-auth.sock` is a Docker-Desktop-only magic mount; **Colima has no equivalent**. So on this repo's runtime (Colima VZ+Rosetta), the proxy pattern is necessary; bind-mounting `${localEnv:SSH_AUTH_SOCK}` directly will not work even when the var is set.

### [EVIDENCE]

- github.com/abiosoft/colima#1330 (open)
- github.com/abiosoft/colima#942 (open)
- Colima FAQ — no ssh-auth-sock passthrough documentation
- `/run/host-services/ssh-auth.sock` confirmed as Docker Desktop-specific via docker/for-mac issue search

### [CONFIDENCE:HIGH]

---

## [L2_L3_CHRMARTI_AUDIT]

**Verified.** `chrmarti` = Christof Marti, company `@Microsoft` per `api.github.com/users/chrmarti`. Not in the public devcontainers org member list, but Microsoft employment plus authorship of issue #441 in `devcontainers/cli` is consistent with maintainer status (devcontainers org membership is largely private). Combined with the substantive content of #441 and **zero** `ssh-auth.sock` references anywhere in `org:devcontainers` code search (0 hits), L2's claim that the CLI does no auto-forwarding stands.

### [EVIDENCE]

- `api.github.com/users/chrmarti` → company `"@Microsoft"`
- `org:devcontainers ssh-auth.sock` code search = 0 hits
- `devcontainers/features` only has `sshd` (no agent-forward feature)
- `devcontainers-contrib` search for ssh-agent = 0 hits

### [CONFIDENCE:HIGH]

---

## [GAP_FOUND_OR_NOT]

**One material gap.** The 5 findings did not separate the **CLI lane** (`mise run up` via `@devcontainers/cli`) from the **IDE-attach lane** (VS Code Dev Containers extension, JetBrains Gateway/CLion "Connect to Dev Container").

`microsoft/vscode-remote-release` issues #11413, #8810, #6600 confirm the VS Code extension actively performs ssh-agent forwarding. Issue #11413 literally requests a setting to *disable* the automatic forward — proving it is on by default.

So: when the user attaches with VS Code, agent forwarding is added by the extension on top of whatever the CLI built — git push works "for free" in that lane. The CLion/JetBrains lane is unverified here, but JetBrains Gateway uses its own SSH-tunnel agent, separate from the CLI build.

**Net:** only the **CLI lane** (and any pure-`docker exec` shell) is broken; the IDE lanes likely work today. **This sizes the fix down considerably.**

### [EVIDENCE]

- microsoft/vscode-remote-release#11413 (open: "Add setting to disable automatic SSH agent forwarding in Dev Containers")
- #8810, #6600 (confirm scope)

### [CONFIDENCE:HIGH]

(HIGH for VS Code extension auto-forward; MEDIUM for the assertion that CLion behaves the same — not directly probed.)

---

## [RECONCILED_RECOMMENDATION]

**Adopt the cpp-playground host-TCP + container-unix-socket proxy pattern, but scope it to the CLI lane only** (`mise run up` / `devcontainer up`) and to terminal/`docker exec` workflows — that is the lane this repo's devloop actually uses and the lane Colima cannot fix on its own.

Do NOT key the design on "all lanes are broken": the VS Code Dev Containers extension already auto-forwards (vscode-remote-release#11413 confirms this is on by default), so users attaching via VS Code get git push "for free" and the proxy is purely additive for them.

**There is no simpler escape hatch on Colima specifically:**
- No `host-services/ssh-auth.sock` equivalent exists.
- No official devcontainers feature solves it (devcontainers/features ships only `sshd`, devcontainers-contrib ships nothing for ssh-agent).
- The spec has no native property (L1).

**The proxy is the smallest correct fix for the CLI lane.** The `sshd`-on-4444 path (L4) should be deleted as it solves a different problem (ssh-into-container, not agent-forwarding-out).

[STAGE_COMPLETE:verification]

## GitHub repos touched

- [abiosoft/colima](https://github.com/abiosoft/colima) — confirmed no SSH_AUTH_SOCK passthrough (issues #1330, #942, FAQ)
- [devcontainers/cli](https://github.com/devcontainers/cli) — re-verified zero ssh-auth refs via code search; chrmarti=Microsoft
- [devcontainers/features](https://github.com/devcontainers/features) — only `sshd` feature exists; no ssh-agent feature
- [devcontainers-contrib/features](https://github.com/devcontainers-contrib/features) — zero ssh-agent features
- [microsoft/vscode-remote-release](https://github.com/microsoft/vscode-remote-release) — issue #11413 proves VS Code extension auto-forwards agent (gap finding)
- [docker/for-mac](https://github.com/docker/for-mac) — `/run/host-services/ssh-auth.sock` is Docker-Desktop-specific, no Colima equivalent
