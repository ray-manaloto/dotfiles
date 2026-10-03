# apt.llvm.org exact-pin churn after a 22→23 swap — research 2026-10-03

Status: COMPLETE (2026-10-03).

Brief: measure -23/-22/-21 rebuild cadence, confirm/refute one-build-per-suite, measure Renovate apt-pin PR latency,
compare mitigation options, survey other projects. Prior reports read first:
`llvm-23-grilling-research-2026-10-02.md`, `llvm-major-detection-sweep-2026-10-02.md`.

## Quoted repo rationale against "latest" (mise-system.toml)

`.devcontainer/mise-system.toml` lines 118-122 (general) and 192-196 (LLVM block):

> WHY PINNED (#288, was "latest" until 2026-07-16): mise.lock does NOT cover bootstrap packages and the base
> content-hash keys on THIS FILE'S BYTES, so a "latest" entry drifts silently while the hash still reports "same" —
> an unrelated edit rebuilds against a different curl/openssl and nothing says so. A pin converts that silent drift
> into a LOUD build failure.

> WHY PINNED: apt.llvm.org retains one build per package. A latest declaration could rebuild a changed compiler under
> the same input content hash. Uniform exact pins make index rotation a loud failure; Renovate's apt-mise-system
> customManager handles within-major updates (mise's native manager does not parse bootstrap.packages).

Current -22 pin: `1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17` (build 2026-07-14).

## Q1 evidence (live probes 2026-10-03)

### Release `Date:` per suite (control: `-bogus77` → 404, all real suites → 200)

| Suite | HTTP | Release Date | Packages (amd64) | Single version? |
|---|---|---|---|---|
| resolute-21 | 200 | 2026-05-29 03:38 | 54 | yes: `1:21.1.8~++20260528104042+2078da43e25a-1~exp1~20260528224128.9` |
| resolute-22 | 200 | 2026-07-14 18:49 | 58 | yes: `1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17` (== our pin) |
| resolute-23 | 200 | 2026-09-22 11:37 | 58 | yes: `1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77` |
| resolute (trunk) | 200 | 2026-09-22 11:37 | 69 | two: 58 × `1:24~++20260911…+58c46bae2118…254`, 11 × `1:23.0-71~exp1~20260701…` |
| resolute-bogus77 | 404 | — | — | control |

Every numbered suite's Packages index carries exactly ONE version (`sort | uniq -c`). Even trunk had not
republished for 11 days at probe time.

### The pool keeps leftover signed `.dsc.asc` files — an accidental build history

The pool directories list only the current build's `.deb`s (one version per package × amd64/arm64/s390x), but
leftover `llvm-toolchain-N_*.dsc.asc` files from earlier builds survive. The trailing `.<n>` is a monotone build counter.

- **-22 (resolute)**: builds .6 (04-28, 22.1.5), .7 (04-29), .8 (05-06, 22.1.6), .9 (05-07), .10 (05-09), .11 (05-14),
  .12 (05-22, 22.1.7), .15 (06-13, 22.1.8), .17 (07-14, 22.1.8 ca7933e, current). Counter 6→17 = 11 builds in 77 days
  ≈ **1.0/week** while the branch was releasing patches every ~2 weeks; then nothing after 07-14 (branch frozen).
- **-21 (resolute)**: .6 (04-25), .9 (05-28, current). Frozen major: ~0.4/week, then stopped.
- **-23 (resolute)**: .31 (07-30, 23.1.0~), .35 (08-02, 23.1.0~), .77 (09-22, 23.1.3~, current). Counter 31→77 = 46
  in 54 days ≈ **6/week** of counter increments (counter likely includes failed/unpublished runs; see Wayback below).
- Older `.deb`s are absent from the pool listing: only the current build's binaries are listed (147 hrefs in -23 pool,
  all for build .77 except the two stray `.dsc.asc`).

### Wayback Machine (sparse but discriminating)

CDX control: `apt.llvm.org/llvm.sh` → 11 captures in 2026; `apt.llvm.org/resolute/*` → 11 rows. The suite directories
were captured on 2026-08-22/08-31 only; **no `.deb` was ever captured** (CDX for `…/llvm-toolchain-22/clang-22_*` → 0
while the same CDX shape over the parent dir → hits). Directory-listing mtimes from the 2026-08-31 capture:

| Suite dir (captured 2026-08-31) | `main/` mtime (≈ suite birth) | Release mtime then | Release Date now |
|---|---|---|---|
| resolute-23 | 2026-07-23 16:18 | 2026-08-18 15:40 | 2026-09-22 → **republished in between** |
| resolute-22 | 2026-04-25 22:31 | 2026-07-14 18:49 | 2026-07-14 (unchanged) |
| resolute-21 | 2026-04-25 23:17 | 2026-05-29 03:38 | 2026-05-29 (unchanged) |
| resolute (trunk) | 2026-04-28 12:29 | 2026-08-20 00:34 | 2026-09-22 |

This closes the prior sweep's gap G3/G10 for resolute: **`dists/llvm-toolchain-resolute-23/main/` existed from
2026-07-23** (after rc1 07-18, before rc2 07-28, ~33 days before 23.1.0 GA 08-25).

### "Old debs deleted": CONFIRMED with both arms

Wayback's 2026-07-23 capture of `noble/pool/main/l/llvm-toolchain-22/` listed
`clang-22_22.1.8~++20260613092238+e80beda6e255-1~exp1~20260613092253.78_amd64.deb` (and, transiently, s390x debs of
22.1.7 build .75 next to amd64 22.1.8 — the pool can briefly hold two versions when one arch lags).
- that old URL live today → **404**
- the current Packages `Filename:` for clang-22 (`…20260714135019.80_amd64.deb`) → **200** (control)
- Wayback has no copy of any pool `.deb` (CDX 0 vs the parent dir's hits), so **Wayback is not a fallback mirror**.

### Jenkins build history (llvm-jenkins.debian.net JSON API) — the best cadence source

`/job/<job>/api/json?tree=builds[number,timestamp,result]`; control `llvm-toolchain-resolute-bogus77-binaries` → 404,
real jobs → 200. Jenkins retains only ~3-5 builds per job, so the full history is NOT available; build NUMBERS still
count every run since the job existed. The package version's trailing `.<n>` equals the **source** job build number
(`.77` ↔ `resolute-23-source #77`).

| Job | Retained builds (number:date:result) |
|---|---|
| resolute-23-source | 77:09-22:S 76:09-20:S 75:09-19:S 74:09-19:S 73:09-16:F |
| resolute-23-binaries | 42:09-22:S 41:09-20:S 40:09-19:S |
| resolute-22-source | 17:07-14:S 16:06-16:S 15:06-13:S 14:06-01:F 13:05-26:F |
| resolute-22-binaries | 15:07-14:S 14:06-16:F 13:06-13:S |
| noble-23-binaries | 40 S (09-19), 42 F (09-22) |
| noble-22-binaries | first retained 70, last success 73 (07-14), 71 F (06-13) |

### What triggers a rebuild — tag events and packaging changes, NOT every branch commit

- 67f4a076a097 (the live -23 build) = "Bump version to 23.1.3", committed 2026-09-22 06:48, **exactly 1 commit after
  `llvmorg-23.1.2`** (GitHub compare: ahead 1 / behind 0); release/23.x head 21ef2ddb is now 26 commits ahead of it.
  The branch had commits on 09-23, 09-25, 09-29, 09-30 with **no** apt rebuild since 09-22 → builds are not per-commit.
- -22: source #16 ran 06-16 (the 22.1.8 tag day); **#17 rebuilt on 07-14 at the same branch-head commit ca7933e
  (= `llvmorg-22.1.8^{}`)**. A frozen branch still produced a NEW version string (new `~++<date>` and `.17`), i.e.
  a packaging-side rebuild **would have broken a 22 pin taken before 07-14**. Frozen ≠ immune; it is merely rare.
- LLVM release dates (GitHub releases): 23.1.0 08-25, 23.1.1 09-08, 23.1.2 09-22 — a fortnightly patch train that by
  LLVM's usual schedule runs through ~x.1.8 (22.x ran 02-24 → 06-16, 9 releases).

### Q1 answer — cadence estimate

- **-23 (moving)**: observed publishes 07-30, 08-02, 08-18, 09-19, 09-20, 09-22 (incomplete; Jenkins retention and
  Wayback sparsity hide others). Binaries job #1→#42 over the suite's ~61 days ≈ 4.8 runs/week incl. failures and
  pre-GA runs; observed *published* builds suggest **≈1-2 publishes/week on average, bursty (3 in 4 days around a patch
  tag), with gaps up to ~4 weeks**. Expect this until the 23.x patch train ends (~mid-December 2026 if it mirrors 22.x).
- **-22 (frozen at 22.1.8)**: 10 known publishes 04-28 → 07-14 (≈0.9/week during the patch train), then **0 in the
  81 days since 07-14**.
- **-21 (frozen)**: last publish 05-28 (`.9`); 0 in 128 days.
- **"Exactly one build per suite / old debs deleted"**: CONFIRMED (Packages carries one version in every numbered suite;
  pool lists only the current build's debs; an old pool URL 404s while the current one 200s). Caveat: brief per-arch lag
  windows where the pool holds two versions; stray `.dsc.asc` files survive but no old binaries.
- **Pin-break probability**: with an exact -23 pin, every publish is a hard image-build break until the bump merges —
  ~1-2 breaks/week through ~Dec 2026.

## Q2 — Renovate `apt-mise-system`: does it automerge, how fast?

Config (renovate.json, read 2026-10-03):
- Global: `extends: github>jdx/renovate-config` (that preset sets `"automerge": true` and automerges
  minor/patch/digest), `schedule: at any time`, `minimumReleaseAge: 1 hour` + `timestamp-optional`, `prHourlyLimit 0`.
- `packageRules[3]`: minor/patch/digest → `automerge: true, automergeType: pr, platformAutomerge: true`.
- **`packageRules[0]`: `matchFileNames` includes `.devcontainer/mise-system.toml` → `groupName: "image-build inputs"`.**
  So every apt pin bump (LLVM and Ubuntu) rides in ONE grouped PR with bun/chezmoi/hk/mise/pixi/uv/ubuntu-digest/
  gcc-latest bumps. Automerge is armed, but GitHub merges only when `ci-gate` is green for the WHOLE group.
- `packageRules[5]` hard-codes `suite=llvm-toolchain-resolute-22` in the deb registryUrl — a 22→23 swap must rewrite it.

Measured outcome (control-armed):
- `git log --author=renovate` → **201** commits repo-wide (control), **4** touching `shared.toml`, **0** touching
  `.devcontainer/mise-system.toml`. **No Renovate apt bump has ever merged.**
- The Renovate group PRs that carried apt bumps never went green:
  | PR | Created | Ended | Outcome |
  |---|---|---|---|
  | #442 "update all dependencies" (carried libssl-dev) | 07-30 | 08-01 closed | closed; the line was extracted into human #454 |
  | #947 "update all dependencies" (carried gnupg) | 09-03 | 09-29 | abandoned/autoclosed after 26 days |
  | #1063 "update image-build inputs" | 09-14 | 09-29 closed unmerged (lint/autofix/image-lock-pr/ci-gate red) | 15 days |
  | #1449 "Update image-build inputs" | 09-29 | still OPEN, auto-merge armed, lint + ci-gate red | 4+ days |
- Every apt pin repair was a **human standalone PR** after a red base build or red `verify-apt-pins`:
  | Break surfaced | Fix | Latency (surfaced → merged) |
  |---|---|---|
  | #332 (07-21 16:52, build-essential + libsqlite3-dev) | #333 | **54 min** — but the pins had been stale silently for an unknown period; `main` was green on cache hits |
  | #454 (libssl-dev; surfaced by #427 on ~07-30) | #454 merged 08-01 02:29 | **~1.5 days** |
  | #962 (09-03 21:43, gnupg) | #969 merged 09-03 23:38 | **~2 h** (issue closed 09-04) |
- Today every Ubuntu pin equals the newest version across resolute/-updates/-security (14/14 checked against live
  Packages.gz), and the -22 LLVM pin equals the live -22 build, so nothing is owed right now.

**Answer**: automerge is nominally ON but **effectively never fires for apt pins**, because grouping puts them behind
whatever else in "image-build inputs" is red, plus a ~2.5 h cold base build. Observed Renovate open→merge latency for
apt pins = **∞ (0 of 4 merged)**; human repair latency = 1 h–1.5 d after someone notices. With -23 publishing ~1-2×/week,
the current machinery would leave the base build red most of the time.

### Upstream's own statement of the trigger

apt.llvm.org homepage source (`opencollab/llvm-jenkins.debian.net` `index.php`, "Workflow"): *"Twice a day, each
jenkins job will checkout the debian/ directory necessary to build the packages"*; the `-source` job makes
`llvm-toolchain-X_X.Y.Z~++DATE+UPSTREAM_COMMIT_HASH.orig.tar.xz`, then triggers `-binary`, which builds, runs lintian and
"Publish[es] the result on the LLVM repository". So rebuilds come from **packaging (salsa `debian/`) changes polled twice
daily, plus upstream activity**, which explains both the -22 same-commit rebuild on 07-14 and the burst around 23.1.2.
Independent corroboration: skyRolly/Anamorph ADR-0033 measured `-23` = `1:23.1.0~++20260818083557+55feb0a3b6b7`, built
2026-08-18, identical commit across noble/resolute/bookworm/trixie. That matches the Wayback Release mtime 08-18 above.

## Q3 — options

### (a) Looser pin: version glob/prefix, or `latest`, for the LLVM set only

- **apt supports a trailing-`*` prefix in `pkg=ver`.** `apt-pkg/cacheset.cc:492` builds `pkgVersionMatch(ver, Version)`.
  `apt-pkg/versionmatch.cc:45-53` sets `VerPrefixMatch` when the string ends in `*`. So `apt-get install
  clang-23='1:23.1.*'` resolves (inferred from the source; not executed, because the brief said no containers).
- **mise passes the string through verbatim** (`src/system/packages/apt.rs:270-271`: `format!("{}={v}", p.name)`), so
  install would work. **But status compares exact strings** (`apt.rs:169-171`: `!versions.contains(&requested)` →
  `VersionMismatch`), and `src/cli/system/status.rs:113-115` treats `VersionMismatch` as `any_missing = true`. Our
  Dockerfile's anti-drift gate `mise bootstrap packages status --json --missing` would therefore **exit 1 on every glob
  pin**. A glob is incompatible with the existing gate unless that gate is rewritten.
- The Renovate regex (`[0-9][^"]*`) would also extract `1:23.1.*` as a currentValue that deb versioning cannot parse.
- `latest`: mise docs say "`latest` entries are satisfied by any installed version". The repo's documented objection
  (quoted at the top) applies in full: the base content-hash keys on file bytes, so a rebuilt compiler lands under an
  unchanged hash, silently.
- An apt-preferences file (`Pin: version 1:23.1.*`) plus `latest` in mise is the native apt way to bound drift to a
  minor, and it passes the mise status gate. It still loses the "loud on drift" property, so it would need a
  post-install record (e.g. write `dpkg-query` versions into an image label) to stay detectable.
- PRO: zero breakage from rebuilds; native mechanisms only. CON: gives up reproducibility and loud detection, which
  #288 deliberately bought; the glob form breaks our status gate.

### (b) Archive/snapshot service

- **None for apt.llvm.org.** Old pool `.deb`s 404 (proved above). Wayback never captured a pool `.deb` (CDX 0, while
  the parent dir has hits). No official retention or archive is documented in the homepage source.
- **snapshot.debian.org does archive *Debian's* llvm-toolchain-23** (`/mr/package/llvm-toolchain-23/` → 200 with
  1:23.1.2-1, 1:23.1.1-1/-2, 1:23.1.0-1/-2, rc1-3; control `llvm-toolchain-bogus77` → 404), and Debian sid currently
  ships `clang-23 1:23.1.2-1`. These are **tag-exact, permanently archived** versions, but they are built for sid, not
  resolute, so pulling them onto Ubuntu 26.04 mixes distributions (libc6/libstdc++ dependency floors; unverified).
- **Ubuntu archive (Launchpad)**: llvm-toolchain-23 exists only for `stonking` (26.10), and only in -proposed, where
  it is Deleted/Superseded. There is **nothing for resolute** (control: llvm-toolchain-22 has stonking Release
  Published; bogus → 0).
- PRO: Debian snapshot is immutable and tag-exact. CON: wrong distro; a new trust path; unverified installability.

### (c) Mirror the exact debs ourselves (GHCR OCI artifact or release assets)

- Size measured from the -23 Packages `Size:` fields: the 52 active packages are **391 MB amd64 + 383 MB arm64 ≈ 0.77 GB
  per mirrored build**. That fits easily in a GHCR OCI artifact (oras) or in GitHub release assets (2 GB per file).
- Prior art: oven-sh/WebKit already mirrors toolchain debs as release assets (`gcc-13-focal-debs` →
  `gcc-13-focal-{amd64,arm64}.tar.gz`). Its PR #473 names "mirror the llvm-21 debs to a sha256 pinned release asset" as
  the follow-up that would remove the apt.llvm.org dependency.
- Mechanism: on a pin bump, a CI job downloads the exact debs and pushes them (sha256-addressed). The Dockerfile adds a
  local flat repo (`deb [trusted=yes] file:/…` or a signed one) before `mise bootstrap packages apply`. mise is
  unchanged, because apt resolves `name=version` from any configured source.
- PRO: true reproducibility, so a rebuild never breaks; pins become currency, not survival; it also removes the
  build-time dependency on a third-party host (oven-sh's outage class). CON: new custom code and a new trust path, which
  under `use-tool-builtins.md` needs a written justification; ~0.8 GB storage per kept build; the mirror job has to win
  the race against the next publish when it captures (bursts land 1-2 days apart); it adds a pinned-digest input to the
  content hash.

### (d) Fast Renovate automerge plus a `verify-apt-pins` canary, with schedule tuning

- Today this path does not work for apt pins (Q2: 0 of 4 merged), because `packageRules[0]` groups them into
  "image-build inputs" behind unrelated red tools.
- Fix shape, which is all native Renovate: a packageRule matching `matchDatasources: ["deb"]` and
  `matchPackageNames: ["/-23$/", "/^lib.*23/", …]` (or a `matchFileNames` + depName pattern) with `groupName: "llvm-apt"`,
  `automerge: true`, `platformAutomerge: true`. This mirrors the existing clang-p2996 rule (`packageRules[9]`), which
  already split a churny compiler out of the group for the same reason. `registryUrls` must also move from
  `llvm-toolchain-resolute-22` to `-23`.
- Canary: nothing scheduled runs `verify-apt-pins` today (grep of `.github/workflows/` → 0; the `mise.toml` task exists;
  `ship` runs it only when the diff touches mise-system.toml/Dockerfile, per #962). A daily index probe (pin == live
  Packages version, no container needed, the same comparison this report ran) would turn silent rot into an issue
  within 24 h. Without it, main stays "green on a cache hit" while broken (#333's own words).
- Cost: each LLVM bump is a cold base build (~2.5 h). At ~1-2 publishes/week that is 1-2 cold builds/week through ~Dec.
  The race risk is a publish landing during the ~2.5 h bump build. That is low on average, but real in bursts (09-19,
  09-20 and 09-22 were 1-2 days apart).
- PRO: all native, small diff, keeps exact pins and loud failure. CON: breakage windows still happen (publish → Renovate
  run → 2.5 h build); CI spend.

### (e) Stay on a frozen major until its branch stops moving

- Evidence: -22 had 0 publishes in the 81 days since 07-14, and -21 had 0 in 128 days. A frozen suite is quiet, but
  **not immune**: the 07-14 packaging rebuild at the same commit would have broken a 22 pin taken in June.
- 22.x ran 9 releases over ~16 weeks (22.1.0 02-24 → 22.1.8 06-16). If 23.x repeats that, the patch train ends around
  **23.1.8 ≈ mid-December 2026**. Measurable freeze signal: `release/23.x` head == latest `llvmorg-23.*^{}` (today it is
  26 commits ahead of the build, so not frozen), plus no `-source` Jenkins build for N weeks.
- Relation to the IWYU hold: `llvm-bump` already refuses a major until conda-forge IWYU targets it on both arches
  (mise-system.toml:53-56, 180-181). Waiting for the freeze is the same kind of gate, a readiness condition on the major,
  and could live in the same detector. Not researched here: when IWYU for clang 23 lands.
- Prior art: skyRolly/Anamorph ADR-0033 (2026-08-30) evaluated 23 and **stayed on 22** because apt.llvm.org's -23 was a
  pre-tag branch build. It then added a release-identity assertion (clang `--version` commit == `llvmorg-<v>^{}`).
  Note: our -23 build is tag+1 ("Bump version to 23.1.3"), so a strict tag-commit assertion would also refuse it.
- PRO: zero new machinery, and rebuild churn ≈ 0; consistent with exact pins. CON: forgoes 23 for ~2.5 months; the
  freeze date is an estimate; rare packaging rebuilds still need the canary from (d).

### (f) Other findings

- **Pin by `~++` snapshot-date prefix**: useless. One build exists per suite, so any prefix narrower than the major
  either matches the single live build (equivalent to a glob) or nothing.
- **Debian sid tag-exact packages via snapshot.debian.org**: see (b).
- **Treat the published `:dev` base image as the archive.** The base is content-hash cached, so the installed debs
  already persist in the registry image. Pin rot only bites a *cold* rebuild. That is why the failure is latent (#333,
  #454, #962 were all discovered by an unrelated input change), and why the canary matters more than the pin form.

## Q4 — what other projects do (GitHub code + issue search)

Controls: code search `apt.llvm.org/llvm.sh` → **10,096** (must-hit), fresh invented `qxvlmbrtz-llvm-pin-ghost` → **0**.
Issue search fresh invented `zqvrtyplonk "apt.llvm.org"` → **0**. Note: an unquoted `404` term matched issue numbers
(205k junk hits), so quoted-phrase queries were used.

| Query | Hits | Relevant |
|---|---|---|
| `apt.llvm.org llvm-toolchain renovate` | 35 | colopl/pskel (major-only ARG via github-releases), JetBrains/qodana-docker (major-only ARG), otel (exact pin, frozen suite), ours |
| `datasource=deb apt.llvm.org` | 1 | open-telemetry/opentelemetry-dotnet-instrumentation only |
| `"~exp1~" clang apt.llvm.org` | 165 | mostly docs and logs; skyRolly/Anamorph ADR-0028 |

Patterns observed:
1. **Major-only, unpinned within the suite** (most common): JetBrains/qodana-docker `ARG CLANG="16"` →
   `llvm-toolchain-bookworm-$CLANG`; colopl/pskel `# renovate: datasource=github-releases depName=llvm/llvm-project` /
   `ARG LLVM_VERSION=23`; skyRolly/Anamorph ADR-0028, which explicitly **rejects a full version pin**: *"apt.llvm.org is a
   snapshot archive whose pool retains only the current .deb per architecture, so an exact version pin stops resolving …
   as soon as the suite is rebuilt. On an open branch that is a matter of days."*
2. **Exact pin + Renovate deb datasource only on a dead suite**: open-telemetry `clang-5.0=1:5.0.2~svn328729-1~exp1~
   20180509124008.99` from `llvm-toolchain-xenial-5.0` (frozen since 2018). Exact pinning works there only because the
   suite never rebuilds.
3. **Leave apt.llvm.org for an immutable archive**: ferrum-edge/ferrum-edge #5989 replaced apt.llvm.org `xenial-6.0`
   with an exact pin from Ubuntu's frozen `xenial-updates`, citing the build-time third-party dependency and an
   empty-key outage (#4978).
4. **Mirror debs as release assets**: oven-sh/WebKit (gcc-13-focal-debs exists; PR #473 proposes the same for llvm-21).
5. **Release-identity assertion instead of a version pin**: skyRolly/Anamorph ADR-0033.
6. **Resilience only**: sanohiro/align #755 (own repo definition, pinned key fingerprint, minimum package set; unpinned);
   oven-sh/WebKit #473 (retries/mirror failover).

**No project was found exact-pinning a *moving* apt.llvm.org numbered suite with Renovate.** We would be the outlier.
Code search covers public default branches only.

## Recommendation

**(e) + (d), in that order.** Keep the image on LLVM 22 (frozen, 0 publishes in 81 days) until release/23.x stops
moving. Encode that as a readiness gate in the `llvm-bump` detector, next to the IWYU gate: `release/23.x` head ==
latest `llvmorg-23.*^{}`, and the live `-23` build commit == that tag or tag+1, with no new `-source` build for ≥2 weeks.
Expected around mid-December 2026. Ship the cheap native guards **now**, whatever the major:
- split the LLVM deb deps out of "image-build inputs" into their own automerging Renovate group (the clang-p2996
  precedent), and make the suite in `registryUrls` follow the major;
- add a daily, container-free pin-vs-live-index canary (or schedule `verify-apt-pins`) that opens an issue on rot, because
  frozen suites still rebuild occasionally (22 on 07-14) and base caching hides rot until an unrelated change.

Hold (c), the deb mirror, as the escalation if Ray needs 23 before the freeze. It is the only option that makes a
moving-suite pin truly reproducible, and it has prior art (oven-sh/WebKit). It is custom code, though, and needs the
`use-tool-builtins` justification. Do not adopt (a): a glob breaks mise's `status --missing` gate (exact-string compare),
and `latest` reintroduces the silent drift #288 removed.

**Main risk:** the freeze date is an estimate from one prior cycle (22.x); LLVM can add patch releases, so 23 could
stay "moving" longer. Also, while waiting, the image runs a compiler one major behind the newest GA. The canary
mitigates breakage but does not touch the currency cost.

## Gaps

- Jenkins keeps only 3-5 builds per job, and Wayback captured the suite dirs twice. The **complete -23 publish list
  is not recoverable**, so the cadence is an estimate from counters plus partial dates.
- Whether every `-binaries` SUCCESS publishes (vs. some upload step being separate) is inferred from the homepage
  workflow text, not observed.
- apt `pkg=ver*` prefix behaviour was read from apt source, not executed (no containers per the brief).
- Debian-sid-on-resolute installability (option b) was not tested.
- IWYU-for-clang-23 readiness was not researched (a probe was started and aborted as out of scope).
- Renovate's update-type classification for a `~++date`-only change (patch vs other) was not verified. It matters for
  whether `packageRules[3]` automerge applies.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — renovate.json, mise-system.toml, PR/issue history (#333, #442, #454, #947, #962, #969, #1063, #1449)
- [llvm/llvm-project](https://github.com/llvm/llvm-project) — release dates, tag commits, release/23.x commits, compare 23.1.2...67f4a076
- [opencollab/llvm-jenkins.debian.net](https://github.com/opencollab/llvm-jenkins.debian.net) — apt.llvm.org homepage source: rebuild workflow ("twice a day")
- [jdx/mise](https://github.com/jdx/mise) — `src/system/packages/apt.rs`, `src/cli/system/status.rs`, `docs/bootstrap/packages/apt.md`: pin passthrough and exact status compare
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — preset `automerge: true` for non-major updates
- [Debian/apt](https://github.com/Debian/apt) — `apt-pkg/cacheset.cc`, `apt-pkg/versionmatch.cc`: trailing-`*` version prefix match
- [skyRolly/Anamorph](https://github.com/skyRolly/Anamorph) — ADR-0028/0033: major-only pin, rejects exact pin, release-identity assertion
- [open-telemetry/opentelemetry-dotnet-instrumentation](https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation) — exact apt.llvm.org pin + Renovate deb on frozen xenial-5.0
- [colopl/pskel](https://github.com/colopl/pskel) — major-only ARG via Renovate github-releases
- [JetBrains/qodana-docker](https://github.com/JetBrains/qodana-docker) — major-only ARG, unpinned suite
- [ferrum-edge/ferrum-edge](https://github.com/ferrum-edge/ferrum-edge) — #5989 moved off apt.llvm.org to a frozen Ubuntu pocket
- [oven-sh/WebKit](https://github.com/oven-sh/WebKit) — #473 retries/mirror; gcc-13-focal-debs release-asset mirror precedent
- [sanohiro/align](https://github.com/sanohiro/align) — #755 apt.llvm.org install hardening (unpinned)
