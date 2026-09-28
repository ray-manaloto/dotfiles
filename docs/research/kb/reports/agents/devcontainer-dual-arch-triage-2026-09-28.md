# Devcontainer dual-arch triage (amd64 + arm64 local) — 2026-09-28

Read-only triage lane. Goal (Ray): "triage all tasks and GitHub issues to get both
devcontainers running" — a LOCAL devcontainer on BOTH amd64 (emulated) and arm64 (native)
on this arm64 Mac, each passing R1/R2/R3, smoke tiers 1-3, persistence.

Status: COMPLETE — sections (a)-(d) at the end; raw probe log first.

Note: checkout was found on branch `fix/graphify-hook-nudge` (brief said `main`); not switched.

## Raw log (incremental)

### Step 1 — plan + live state (probes run 2026-09-28)

- `task_plan.md:97-133` **Phase C — ONE universal devcontainer task (#669)** is the governing plan item: two
  arch-isolated containers from this clone simultaneously (default `linux/amd64/v2`, and `MISE_ENV=arm64`
  `linux/arm64/v8`); positive path = names x2 -> sync/up x2 -> verify-local x2 -> verify-container-latest /
  verify-arch / verify-ssh-inbound x2 -> a NEW public `verify-ssh-outbound` x2 -> exactly two running rows.
  Issues listed there: #11 #12 #72 #223 #669 #678 #679 #845 #851 #852 #854 #860 #861 #866 #870 #907 #909 #985 #1106.
  `task_plan.md:1135-1137`: the ACTIVE order is the 2026-09-24/25 remainder + S27/S28 owed items, then Phase 11.
  Phase C is in the ARCHIVED 2026-09-15 order (`task_plan.md:82` "do NOT execute from here") — so it is not
  currently scheduled.
- Arch selection mechanism = `MISE_ENV=arm64` loading gitignored `mise.arm64.local.toml`
  (`DOTFILES_PLATFORM = "linux/arm64/v8"`, `DEVCONTAINER_SSH_PORT = ""`). `mise.local.toml` pins amd64/v2 + port 26233.
  `mise.toml:203` default `linux/amd64/v2`.
- `mise run names` rc=0 -> amd64 `dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233`, vol `...-amd64-home`, port 26233.
  `MISE_ENV=arm64 mise run names` rc=0 -> `dotfiles-dotfiles-rmanaloto-273897ea-arm64-22975`, vol `...-arm64-home`,
  port 22975, env file `~/.local/state/dotfiles/doppler-273897ea-arm64.env`. Names/labels/ports DISTINCT (#677 works).
- Registry: `docker buildx imagetools inspect ghcr.io/ray-manaloto/dotfiles-devcontainer:dev --raw` rc=0 -> OCI index
  with `linux/amd64/v2` (a0e05dd9271a, created 2026-09-28T15:04Z) AND `linux/arm64` (19fab689d093, created
  2026-09-28T14:56Z, NO `v8` variant) + 2 attestation manifests. `:dev-arm64` rc=0 single manifest digest
  sha256:19fab689d093... == the arm64 entry of `:dev`. `:latest` identical index. Control arm: `:bogus-tag-qx7` rc=1.
  => an arm64 image IS published and pullable by platform.
- Docker (`desktop-linux`, containerd snapshotter): running rows with `dotfiles.workspace` label = 3, ALL amd64
  (this clone `bca476c60b78` Up 46m; plus two OTHER clones' amd64 containers `research-five-source-land`/`-gate`
  Up 19h). Zero arm64 containers. Local `:dev` tag is amd64/v2 only (`docker image inspect` Architecture=amd64
  Variant=v2); no local arm64 image. A stray arm64 home volume exists from a gone clone:
  `dotfiles-dotfiles-arm64-main-rmanaloto-019ae7b8-arm64-home` (created 2026-08-13) — evidence an arm64 container
  was brought up once (likely #678 era); its clone dir no longer exists.
- `timeout` on PATH is a broken mise shim here (rc from "No version is set for shim: timeout") — probes were run
  without it.

### Step 2 — issues + CI (probes run 2026-09-28)

- Open issue count: `gh issue list --limit 1000` = 428; control: search API `is:issue is:open` total_count = 428 (agree).
  NB a `--limit 300/400` list is truncated here.
- **arm64 local HAS WORKED BEFORE.** #678 comment 2026-08-28 (PR #801): `MISE_ENV=arm64 mise run verify-local` rc=0
  (R3 `linux/arm64/v8 aarch64` on all three signals, smoke tiers 1-3 OK incl. R2, R1 on port 22975, 98 tools
  persisted); both arches up at once in this clone; `verify-arch` request-derived. AC1 (native-by-default) NOT
  done BY DECISION — default stays amd64/v2, arm64 is opt-in via `mise.arm64.local.toml`. So the goal is a
  RE-VALIDATION on today's image/code, not a greenfield build-out.
- #800 (sync.py filtered on `devcontainer.local_folder`) is CLOSED.
- `uv run --project python dotfiles-setup platform-matrix` -> 3 legs: amd64/v2 ubuntu-latest publish blocking;
  arm64/v8 **ubuntu-24.04-arm publish blocking**; arm64/v8 ubuntu-26.04-arm validate non-blocking
  (`platform_target.py:188,196,198-209`). => arm64 IS a published, blocking CI leg (#676/#736 closed).
- CI: main scheduled run 36438084084 (e502c47b, 2026-09-28T14:43Z) success — all three smoke-test legs success
  incl. arm64 publish AND the 26.04-arm validate leg; manifest success. Run 36422517048 failed only at `promote`
  (fixed by #1423 "promote already current", merged). Latest main run 36455333327 success.
### Step 3 — code path for the arm64 leg (read-only)

- Selection: `MISE_ENV=arm64` -> `mise.arm64.local.toml` (DOTFILES_PLATFORM=linux/arm64/v8, port blank) ->
  tasks export `DOCKER_DEFAULT_PLATFORM` (`mise.toml:355,421,450`); `up` evals `dotfiles-setup devcontainer env` and passes
  `--id-label dotfiles.workspace=… --id-label dotfiles.arch=…` (`mise.toml:357-390`). Documented at
  `.devcontainer/AGENTS.md:97` and `mise.local.toml.example:36-46`.
- Local image store: `docker image inspect --platform linux/amd64/v2 …:dev` rc=0 (control), `--platform linux/arm64/v8`
  rc=1 => arm64 content ABSENT locally; `verify-local`'s first step `verify-image` runs `docker run --pull=never
  "$BASE_IMAGE"` (`mise.toml:450-466`) and would fail for arm64 until `MISE_ENV=arm64 mise run sync` fetches it.
  `sync.refresh_local_tag` (`sync.py:625-676`) requests the UNION of host platform + platforms already present, so
  once arm64 is fetched every later sync (either arch) re-resolves BOTH (~2x pull work; containerd store required —
  present: `driver-type io.containerd.snapshotter.v1`).
- `mise.local.toml.example:45-46` says "The local :dev tag holds one platform at a time" — looks STALE vs the #800 F2
  union logic in `sync.py:633-645` (doc drift, low severity).
- Sync record `~/.local/state/dotfiles/sync-…_dev.json`: registry_digest == live registry index digest
  `sha256:3d8ffba6…` (amd64 current); `containers` has only `273897ea:amd64` — arm64 never converged under the #894 key.
- Smoke is arch-aware in-container: tier-1 tool set + tier-3 `gcc_latest`/`conda_gxx` derive from `uname`
  (`image.py:2139-2180`, the 2026-08-28 `MISE_ENV=arm64 mise run sync` smoke FAIL fix). Local tier-3 always passes
  `emulated=True` (`image.py:2178`) so the TSan RUN is skipped even on native arm64 — a coverage gap, not a blocker.
- `verify-arch` (`mise.toml:1042-1086`) derives expected arch/uname from DOTFILES_PLATFORM via `platform_target`, and
  selects the container BY NAME (arch-scoped). `verify-ssh-inbound` resolves the port per arch.
- `persistence` writes host-side `/tmp/mise-persistence-{before,after}.json` + `/tmp/mise-persistence-{pre,post}.tsv`
  — NOT arch-scoped; two arches' `verify-local` run concurrently would clobber each other. Sequential is safe.
- Per-arch Doppler env files exist: `doppler-273897ea-amd64.env` (2026-09-28) and `doppler-273897ea-arm64.env`
  (2026-09-15, from the accidental-bring-up incident, findings.md:946) — regenerated by initializeCommand on `up`.
- Docker Desktop VM: 8 CPUs, ~15.6 GiB RAM, server 29.8.0; `docker system df` images 116GB (70.9GB reclaimable),
  build cache 74GB; host / 283Gi free. THREE amd64 containers already running (this clone + two other clones
  `research-five-source-land`/`-gate`, Up 19h) — resource headroom for a 4th (arm64) + its compile smoke is the
  practical constraint (#769 host resource broker is the unbuilt answer).
### Step 4 — extra probes

- Image locks are arch-symmetric: `[tools.*."platforms.linux-x64"]` vs `linux-arm64` tables = 46/46
  (`mise-system.lock`), 11/11 (`mise-runtime.lock`), 19/19 (`.config/mise/mise.lock`); `lockfile_platforms =
  ["linux-x64","linux-arm64"]` at `.devcontainer/mise-system.toml:319`.
- Since the last arm64 local pass (2026-08-28) there are 25 commits under `.devcontainer/` + `home/dot_config/mise/`
  (incl. #816 arm64 conda gcc, #844 gcc os-scoped smoke, #896 per-workspace state, #1186/#1183 safe.directory,
  #1403 hk v2.3, 6 lock refreshes). None was validated through a LOCAL arm64 container (no record found in
  progress.md / findings.md / reports after 2026-08-28 other than the 2026-09-15 accidental-bring-up incident,
  which was killed mid-pull).
- CI arm64 smoke history (main `ci.yml`, last 20 runs; runs that rebuilt): 2026-09-24T12:25, 09-25T12:25,
  09-26T11:57, 09-27T12:35, 09-28T14:43 — ALL three smoke-test legs `success` each time, including the
  non-blocking `ubuntu-26.04-arm` validate leg (5/5). The other 15 runs had no smoke-test job (warm path).
- No public `verify-ssh-outbound` task: `git grep -c verify-ssh-outbound -- mise.toml python scripts` rc=1;
  control `verify-ssh-inbound` in mise.toml -> 5 hits rc=0. R2 is only checked inside smoke tier 3.
- Separate arm64 registry name from the 2026-09-04 two-image plan does not exist:
  `imagetools inspect …/dotfiles-devcontainer-arm64:dev` rc=1 (control `…:dev-arm64` rc=0); that plan's chain
  (#849/#853/#867/#871/#873) is CLOSED NOT_PLANNED.
- R3 wording: `AGENTS.md:166` and `CONTEXT.md:38` still say "R3 amd64 … reports x86_64/amd64" (control: `git grep`
  found them). Spec `docs/specs/devcontainer-gcc162-dual-arch.md:147` (R2.1, Ray 2026-08-08: "both arches must be
  runnable LOCALLY and both must be built in CI/CD") and `:1720-1724` already say R3 becomes "the arch you asked for
  is the arch you got". `verify-arch` already implements that (#673). So the criterion TEXT is stale, not the gate.
- #72 still live: `mise doctor || true` at `mise.toml:570,598`. #11 still live: `git grep 'getent passwd 1000'`
  -> 0 sites in scripts/python (control: `mise doctor` grep in mise.toml hits). #12's premise ("openssh-server moved
  from base to overlay", Dockerfile.host-user) is partly stale — sshd now comes from the devcontainers `sshd`
  feature (`.devcontainer/devcontainer.json:27-29`).
- #891 is about PROCESS "R1/R2" (task_plan recording, operator prompts) — a name collision, NOT the devcontainer
  R1/R2. Out of scope for this goal.

---

## (a) Current state per architecture

| | amd64 (`linux/amd64/v2`, default) | arm64 (`linux/arm64/v8`, `MISE_ENV=arm64`) |
|---|---|---|
| Registry `:dev` | present, created 2026-09-28T15:04Z (`a0e05dd9…`) | present, created 2026-09-28T14:56Z (`19fab689…`, == `:dev-arm64`) |
| CI publish leg | blocking, `ubuntu-latest` | blocking, `ubuntu-24.04-arm`; + non-blocking `ubuntu-26.04-arm` validate leg |
| CI smoke (last 5 rebuilds) | 5/5 success | 5/5 success (both arm runners) |
| Local image content | present (`image inspect --platform linux/amd64/v2` rc=0) | ABSENT (`--platform linux/arm64/v8` rc=1) |
| Names (`mise run names`) | `…-273897ea-amd64-26233`, port 26233 (pinned in mise.local.toml) | `…-273897ea-arm64-22975`, port 22975 (derived) |
| Container | RUNNING `bca476c60b78`, Up 46m at probe time, overlay `vsc-dotfiles-273897ea-amd64` | NONE; no arm64 home volume for this clone |
| Sync record | `273897ea:amd64` converged on current registry digest `3d8ffba6…` | never converged |
| Last full gate pass | `mise run land -- 1363` 2026-09-24: verify-local rc=0 (ship-session-results-2026-09-24.md:45) | 2026-08-28 (#678 comment, PR #801): verify-local rc=0 — a month and 25 devcontainer commits ago |

## (b) Ranked blockers

| # | Sev | Claim | Evidence | Ray ruling? | Smallest next action |
|---|---|---|---|---|---|
| 1 | HIGH | arm64 has never been brought up on today's image; its content is not local, so `verify-local` step 1 (`verify-image`, `docker run --pull=never`) would fail and `up` would have to pull ~22GB inside the devcontainer CLI. | `image inspect --platform linux/arm64/v8 …:dev` rc=1 (amd64 control rc=0); `mise.toml:450-466`; sync record has only `273897ea:amd64` | Go-ahead only (mutating, ~22GB pull, 4th container) | `MISE_ENV=arm64 mise run sync` (buildkit, fetches arm64 as a union with amd64 — `sync.py:625-676`), then `MISE_ENV=arm64 mise run verify-local`. Run in the background with a file-captured rc; do NOT run concurrently with an amd64 verify-local (item 7). |
| 2 | HIGH (flaky, both arches) | The persistence gate fails whenever one of ~30 `latest`-pinned overlay tools releases between its pre and post snapshots. That is a false red that nobody can fix from the repo side on the day it happens. | #907 (fd, 2026-09-02), #1172 (dust, 2026-09-16; broot, 2026-09-26); `mise.toml:526-600`; `home/dot_config/mise/config.toml.tmpl:14-51` | YES — #1172 asks for a choice: (a) exact-pin the overlay tier (fits the repo's doctrine), or (b) compare names only for `latest` tools and report "floating pin advanced" as INFO | Ruling on #1172, then a narrow implementation (spec the fail arm as #1172 describes). Until then a retry passes, but the rule says the retry proves nothing (#907 "A retry passes, and the pass is worthless"). |
| 3 | MEDIUM | The local arm64 mount/SSH/persistence/tier-2 path has not been checked since 2026-08-28. 25 devcontainer-surface commits have landed since then. CI only runs the no-mount half. | Step 4 commit list; CI 5/5 green covers no-mount smoke only (`scripts/devcontainer-smoke.sh:72-90` notes which parts are bash-only) | No | Covered by the item 1 run. Triage any failure against `.claude/rules/persistence-gate-retry.md` signatures before touching code. |
| 4 | MEDIUM | Host headroom. The Docker Desktop VM has 8 CPU and 15.6 GiB, and three amd64 containers are already up: this clone plus two other clones (`research-five-source-land`/`-gate`, up 19h). A fourth container with tier-2 pytest, tier-3 compiles and a stop/up cycle may be starved. #769 (host resource broker, unbuilt) says "Do not enable dual-local mode before all isolation contracts pass". | `docker info` cpus=8 mem=16746086400; `docker ps` 3 rows; #769 body | YES — does #769's exclusion still bind, given Phase C (`task_plan.md:97-133`) and the 2026-08-28 precedent already ran dual-local? | Ray decides whether the two other-clone containers may be stopped (not this lane's to touch), or whether to raise VM memory, before item 1. |
| 5 | LOW-MED | The R3 success criterion is written as amd64-only, while the gate (`verify-arch`) is already request-derived. An arm64 pass therefore "violates" R3 as written. | `AGENTS.md:166`, `CONTEXT.md:38` vs `mise.toml:1042-1086`; spec R2.1 `docs/specs/devcontainer-gcc162-dual-arch.md:147,1720-1724` | Light: confirm the wording (spec R2.1 already decided the semantics, but AGENTS.md marks R1-R3 "durable, do NOT silently drop") | Proposed text: **R3 arch** — "container reports the REQUESTED platform on `uname -m`, `arch` and the image manifest: `x86_64`/`amd64` for `linux/amd64/v2` (default), `aarch64`/`arm64` for `linux/arm64/v8` (`MISE_ENV=arm64`)". Gate unchanged: `mise run verify-arch`. Keep amd64 as the default leg. Needs the AGENTS.md 12k-char budget check. |
| 6 | LOW | No public R2 gate. Phase C step 5 requires `verify-ssh-outbound`; today R2 is only an in-smoke tier-3 check. | `git grep verify-ssh-outbound` rc=1 (control inbound rc=0); `task_plan.md:116` | No | Add a thin task wrapping the existing tier-3 R2 probe. This is not required for "gates pass" today, because smoke covers R2. |
| 7 | LOW | Running both `verify-local`s at once is unsafe: `persistence` writes fixed host paths (`/tmp/mise-persistence-{before,after}.json`, `…-{pre,post}.tsv`) that are not arch-scoped. | `mise.toml:540-600` | No | Run the two sequentially. Optionally arch-scope the paths (the same class as #893/#894). |
| 8 | LOW | Ongoing cost once arm64 is local. `refresh_local_tag` re-resolves every platform already present, so every later `sync`/`ship`/`land` refreshes both arches, roughly doubling pull work on each `:dev` move. | `sync.py:633-645` docstring | Maybe (accept the cost) | Note it in the handoff. It is intended behaviour (#800 F2). |
| 9 | LOW | Doc drift: `mise.local.toml.example:45-46` says "The local :dev tag holds one platform at a time", but the #800 F2 union logic says otherwise. | `sync.py:625-645` | No | Fix the comment when next touching the file. |
| 10 | INFO | Local tier-3 always sets `emulated=True`, so the TSan RUN is skipped even on native arm64. #870 (two failing tier-3 exec tests, blocked by #861) runs only in `smoke-exec`, not `verify-local`. | `image.py:2176-2181`; #861/#870 | No | Coverage follow-up. Not a gate blocker. |

**Not blockers for the local goal** (CI hygiene; keep them in #669 or their own phase): #852 and #866 (26.04-arm validate
leg: 5/5 green on recent rebuilds, which is evidence toward #852's "shown not to reproduce across several runs"),
#1106, #851, #854, #745. #985 is the plain `linux/amd64` pull on a GHA runner; the Mac pins the variant triple,
`mise.toml:203`. #860 is the containerd `/v8` erasure; `sync.local_platforms` records a match on docker 29.7.2,
but this host now runs 29.8.0 and cannot re-arm until arm64 content is local. #845 is host-side `os=` prediction;
in-container smoke derives arch from `uname`. #841 (gcc 16.2 is shipped by #816/#844; LLVM 23 is blocked
upstream). #11, #12 and #223 are CI coverage.

## (c) Stale or closable for this goal

- **#678**: ACs 2, 3 and 4 were met on 2026-08-28 (PR #801). AC1 ("native by default") was deferred by decision. Close it after the item 1 run re-proves ACs 2-4 on today's image, and move AC1 into its own ruling or issue (see (d) Q1).
- **#800**: already CLOSED (sync.py now filters on `dotfiles.workspace`+`dotfiles.arch`).
- **#1106**: the issue itself says to close it once #852→#866 lands. Not closable yet, but it is no local blocker.
- **#12**: part of its premise is stale (sshd now comes from a feature, not `Dockerfile.host-user`). Rescope or close.
- **#891**: out of scope. Its R1/R2 are process requirements that merely share the names with devcontainer R1/R2. Consider renaming its title to avoid confusion.
- **#78** (Colima): out of scope. Docker Desktop is the supported runtime, and R2 depends on it.
- **The 2026-09-04 two-image/two-registry-name plan** (`docs/research/kb/reports/agents/2026-09-04-two-image-implementation-plan.md`): superseded. Its chain is CLOSED NOT_PLANNED, and the separate `-arm64` repo does not exist.
- **Still live, not stale**: #72 (`|| true` remains), #11 (no UID-1000 check), #907/#1172, #679 (measure during the dual run: "does the setting interfere with running both architectures at once?").

## (d) Open questions for Ray

1. **Default architecture.** Spec #669 says "native by default, AMD64 on demand". #678 AC1 kept amd64 as the default by decision (`mise.toml:203`, and this clone's `mise.local.toml` pins amd64). Keep amd64 as the default, with arm64 opt-in via `MISE_ENV=arm64` (recommended: no change, since "both running" does not need a flip)?
2. **Persistence gate on floating overlay tools** (#1172): (a) exact-pin, or (b) names-only compare for `latest`?
3. **Dual-local policy vs #769.** Does "do not enable dual-local mode before all isolation contracts pass" still bind, given Phase C and the 2026-08-28 run? And may the two other-clone amd64 containers be stopped to free VM headroom?
4. **R3 wording.** Approve rewriting AGENTS.md:166 / CONTEXT.md:38 to "R3 arch = the requested platform" (text proposed in blocker 5)?
5. **Scheduling.** Phase C sits in the ARCHIVED 2026-09-15 order (`task_plan.md:82`). The active order is the 2026-09-24/25 remainder + S27/S28 → Phase 11 (`task_plan.md:1135-1137`). Should "both devcontainers running" jump the queue?
6. **Accept the doubled pull cost** on every `:dev` move once arm64 content is local (blocker 8)?

Status: COMPLETE (read-only; nothing was pulled, brought up, or mutated).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — open issues (#669 #678 #679 #72 #11 #12 #223 #769 #78 #841 #845 #851 #852 #854 #860 #861 #866 #870 #891 #907 #909 #985 #1106 #1172 #745 #1185 #1121 #684 #800), CI runs of `ci.yml`, source and docs read locally
- ghcr.io/ray-manaloto/dotfiles-devcontainer (the registry package of the repo above): manifests `:dev`, `:dev-arm64`, `:dev-amd64`, `:latest` inspected read-only
