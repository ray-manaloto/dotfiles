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
| `FAIL smoke-tiers-1-3` inside `mise run land`, while `mise run smoke` standalone is rc=0 | environmental | retry `land` once — see "The land-smoke transient" below |
| `fatal: detected dubious ownership in repository at '/workspaces/dotfiles'` | environmental | retry once — see "The dubious-ownership transient" below; do NOT reach for `dev-rebuild` |
| `<tool>@latest: no versions found for <tool> matching date filter` (every pass identical) | real defect | do NOT retry — the candidate set is empty (a registry/backend change against `minimum_release_age`); more passes cannot help |

## The dubious-ownership transient (in-container pytest, three sightings)

**2026-09-13 — `mise run land -- 1047`.** `verify-local` stopped on the first
test: `git ls-files` returned rc=128 with `fatal: detected dubious ownership
in repository at '/workspaces/dotfiles'`, then
`tests/test_env_blob_scan.py`, test
`test_tracked_files_reads_the_repo_and_not_an_empty_list`, failed. The scanner
logged the git error instead of treating an empty file list as clean. An
immediate `mise run verify-local` returned rc=0 with zero occurrences of the
signature and all smoke tiers green.

**2026-09-16 — `mise run land -- 1158`.** It reported
`FAIL smoke-tiers-1-3` on the first git call of the pytest run:
`tests/test_bash_budget.py`, test `test_cli_wires_end_to_end`, with
`git ls-files` rc=128 in `/workspaces/dotfiles`. Standalone `mise run smoke`
reproduced the failure once (rc=1). Minutes later, the in-container probe
showed uid 1000 = workspace owner 1000 and `git ls-files` rc=0; the smoke retry
passed with 3521 tests.

**2026-09-17 — `mise run ship` (Phase 7 branch, `fb35cb8`).** The in-container
smoke stopped at test ~3,095 of the run:
`test_requirements_cli_requires_an_explicit_source_root` saw the goal-history
validator print `fb35cb8… deletes the goal history` — its `git show
<rev>:docs/agents/goal-history.md` had returned non-zero, which the validator
reports as a deletion. Minutes later, in the same container, `git show` returned
61,880 bytes and the test passed alone.

Three sightings, three different git calls, one mid-suite — so this is NOT
"the first git call". The trigger remains unattributed. `safe.directory` is configured nowhere in
this repository, but that absence cannot explain an intermittent result; do
not add it on this evidence. Retry once and retain the direct rc. The expensive
wrong move is `mise run dev-rebuild`: it had already succeeded inside the
failing land, so rebuilding cannot be credited as the repair.

## The land-smoke transient (`land` only, twice in two sessions)

`mise run land -- <PR#>` has twice reported `FAIL smoke-tiers-1-3` on a container
that was perfectly healthy, and both times a plain retry passed:

| Session | Signature inside the failure | Standalone `mise run smoke` | `land` retry |
|---|---|---|---|
| 2026-09-03 (`land -- 955`) | a Rust panic in **mise's own** `src/git.rs:193` — not a path in this repo | rc=0, tiers 1-3 OK | rc=0 |
| 2026-09-03 (`land -- 958`) | `=== FAILURES ===` with the generic "stale base?" hint | rc=0, tiers 1-3 OK | rc=0 |

**The discriminating probe is `mise run smoke` on its own.** If it returns rc=0 with
tiers 1-3 OK, the container is a valid environment and `land`'s failure was transient —
retry `land` once. If it fails the same way standalone, that is a real defect: triage it,
do not retry.

⚠️ **The expensive wrong move is `mise run dev-rebuild`.** `land`'s hint text says
"stale base?", which points straight at a ~21.5GB pull that can take hours — and in both
recorded cases the base was already current. Run the standalone probe first; it costs
about a minute and settles it.

⚠️ **The task notification cannot be trusted here.** Both failures arrived with a
"completed (exit code 0)" summary while the log's real `rc=1` sat in the file. Read the
`rc=` you wrote to the log, per `verify-before-advancing.md`.

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
- `mise run land -- <PR#>` — its post-merge `sync` runs the same smoke tiers, and
  is where the land-smoke transient above has surfaced both times
- `mise run sync`
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
