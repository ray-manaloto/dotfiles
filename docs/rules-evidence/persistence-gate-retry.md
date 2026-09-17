# Evidence — `persistence-gate-retry`

The incident behind `.claude/rules/persistence-gate-retry.md`. Extracted from the
rule so the eager copy carries the heuristic and the signature table, and this
file carries the case history.

## Why the gate is network-sensitive at all

The `persistence` gate inside `mise run verify-local` calls
`@devcontainers/cli up` **mid-cycle** to bring the container back up. That path
re-resolves `ghcr.io/devcontainers/features/sshd` for feature dependencies — so
the gate touches the network in a way that is not visible from
`mise.toml [tasks.persistence]` alone.

A transient DNS blip on the host, or inside Docker Desktop's DNS layer, surfaces
as `getaddrinfo ENOTFOUND ghcr.io` and aborts the gate. Meanwhile the image bytes
are healthy, the prior gates have already validated R1/R2/R3, and the
content-hashed `:dev` lineage is unaffected.

## The incident (2026-05-01)

A ~30s host DNS hiccup during the persistence gate's bring-back-up produced
`verify-local rc=1`.

**The first-pass log made it look like an R-invariant regression** in the
post-PR-#93 retagged `:dev` — i.e. a real defect in freshly-published image
bytes, which is about the most alarming thing this gate can report.

The retry ran clean in **18 minutes**, all gates green: R1 inbound, R2 outbound,
R3 amd64, persistence, secrets. **No code changes.**

Without the rule, a future session reading that log would reach for
`mise run dev-rebuild` — ~30 min on this Mac — to chase a transient that had
already cleared. That is the cost the retry-once heuristic buys back.

## Why the DNS pre-checks are the ones they are

Before retrying, the rule has you confirm the host can actually resolve and
reach the registry:

- `dscacheutil -q host -a name ghcr.io` → should return an `ip_address`.
- `curl -sI -o /dev/null -w "%{http_code}\n" https://ghcr.io/v2/ --max-time 10`
  → should return **405**, the registry's expected *unauthenticated* response.

The 405 matters: a `200` would mean something is intercepting, and a `000` means
the probe never got an answer at all — "never asked" is not "answered no"
(`probes-need-a-control-arm.md` rule 4).

## The dubious-ownership case history and attribution (#1183)

Three sightings originally looked intermittent because each retry happened
after Docker Desktop's ownership state had settled:

- **2026-09-13 — `mise run land -- 1047`:** `git ls-files` returned rc=128 in
  `/workspaces/dotfiles`; an immediate `mise run verify-local` returned rc=0.
- **2026-09-16 — `mise run land -- 1158`:** standalone `mise run smoke`
  reproduced the ownership failure once; minutes later the workspace root was
  uid 1000 and the smoke retry passed with 3,521 tests.
- **2026-09-17 — `mise run ship` on `fb35cb8`:** a mid-suite `git show` failed
  and the goal-history validator reported a deletion; minutes later the same
  command returned 61,880 bytes and the test passed alone.

The 2026-09-17 re-create attributed the trigger: Docker Desktop's virtiofs
reported the `/workspaces/dotfiles` mount root as `0:0` for roughly five
minutes while `.git` and the tracked files were `1000:1000`. In a fixture with
that exact shape, no global `safe.directory` produced `git rev-parse` rc=128
and hk/libgit2 rc=1 with `Owner (-36)`. Adding the fixture path to the global
gitconfig made both commands return rc=0 with no owner message. A mise task
returned rc=0 in both arms, so mise remained unarmed by that probe.

#1183 therefore renders one workspace-scoped `safe.directory` through the
chezmoi-managed global gitconfig and checks Git access before smoke tier 1.
Unlike DNS and image-store signatures, another dubious-ownership result is a
real defect: it means the stanza was not rendered or applied. A single retry is
useful only to retain the timing arm; it is not the repair.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `mise.toml [tasks.persistence]`, PR #93, and issue #1183.

_Named in the extracted text but **not** resolved during this extraction: the
`devcontainers/features` sshd feature image reference is carried over from the
rule, not re-fetched._
