# Persistence Gate: Retry Once on Transient DNS

The `persistence` gate inside `mise run verify-local` calls
`@devcontainers/cli up` mid-cycle, which re-resolves the sshd feature —
so the gate is **network-sensitive** in a way `mise.toml
[tasks.persistence]` does not show. A transient host (or Docker
Desktop) DNS blip aborts it while the image bytes are perfectly
healthy.

## Retry-once heuristic

Before triaging a `persistence` failure as a real defect:

1. **Confirm the failure mode is environmental.** Look for
   `getaddrinfo ENOTFOUND` / `dial tcp: lookup ... no such host` /
   `An error occurred setting up the container` in the verify-local
   log. That is the network signature. A real defect surfaces as
   `FAIL: installed-tool set drifted across stop/up` or a missing
   canary.
2. **Check host DNS** before retry: `dscacheutil -q host -a name
   ghcr.io` should return an `ip_address`. `curl -sI -o /dev/null -w
   "%{http_code}\n" https://ghcr.io/v2/ --max-time 10` should return
   `405` (the registry's expected unauthenticated response).
3. **Re-run `mise run verify-local`** — do NOT re-run `mise run
   dev-rebuild`. The image bytes are the same; rebuild costs ~30 min
   on this Mac for a transient that's already cleared.
4. If the retry passes, log the transient and move on. If two
   consecutive runs fail with the same network signature, triage host
   DNS / VPN / Docker Desktop networking before changing project code.

## Why this rule exists

Session 2026-05-01: a ~30s host DNS hiccup during the gate's
bring-back-up produced `verify-local rc=1`, and the first-pass log made
it look like an **R-invariant regression** in the freshly-retagged
`:dev`. The retry ran clean in 18 minutes, all gates green, no code
changes. Without the rule, the next session reaches for `dev-rebuild`
(~30 min) to chase a transient that already cleared.
Detail: `docs/rules-evidence/persistence-gate-retry.md`.

## Failure-mode signatures

| Signature | Class | Action |
|---|---|---|
| `getaddrinfo ENOTFOUND ghcr.io` | environmental | retry once per heuristic above |
| `dial tcp: lookup ... no such host` | environmental | retry once per heuristic above |
| `docker: ... parent snapshot sha256:... does not exist` | environmental (image store) | retry once — `sync` repairs it as a side effect; do NOT reach for a base pull |
| `FAIL: installed-tool set drifted across stop/up` | real defect | triage `mise-system.toml` ↔ runtime drift |
| `FAIL: in-volume canary missing` | real defect | home-volume mount regression — investigate volume name / mount opts |
| `R[123] ... not works` | real defect | the corresponding R-invariant regressed; do NOT retry without diagnosing |

## The image-store signature repairs itself, and that is not luck

Measured 2026-08-08 during a `mise run ship`: `verify-local` died with
`docker: ... parent snapshot sha256:c8a425d7... does not exist` — a local
overlay image referencing a layer the store no longer had, with the local
`:dev` (`3c957a17`) also behind the registry's (`104cdcdc`). Neither DNS
signature above was present, so the rule's table said nothing.

**Retrying `mise run verify-local` alone returned rc=0 in ~20 minutes.** The
repair is a side effect of the same failed run: `sync` detects `CONTAINER
OUTDATED`, runs `dev-rebuild` (rc=0), and the rebuilt overlay no longer
references the missing snapshot. So the retry-once heuristic covers this class
too — and the expensive wrong move is inferring a stale base and starting a
~21.5GB pull, which the earlier `dev-rebuild` had already made unnecessary.

Distinguish it from a REAL base-currency failure: that one surfaces as smoke
tier-1 identity failing on a config-hash mismatch, not as a missing snapshot.

## Applies to

- `mise run verify-local`
- `mise run persistence`
- Any future task that calls `@devcontainers/cli up` mid-test (the
  feature-dependency-resolution path is what touches the network)

## See also

- `.devcontainer/CLAUDE.md` — gate definition + R1/R2/R3 success
  criteria; the in-place persistence-gate caveat lives in the same
  file.
- `mise.toml [tasks.persistence]` — the gate body; `mise run up` mid-
  task is the network-touching call.
- `feedback_docker_desktop_runtime.md` (auto-memory) — the runtime
  whose DNS layer this rule depends on.
- `feedback_research_before_fixing.md` (auto-memory) — sibling
  principle: don't guess at failures; verify the signature first.
