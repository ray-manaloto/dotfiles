# R3 Domain Synthesis — Complete tool watch-list + automated release-note skill + missed mise releases

Run: `research-20260710-r3-watchlist-releasenotes` · Synthesis · 2026-07-10.
Domain: (1) did we identify ALL main tools for release-note mining
(esp. the Docker family)? (2) what do the missed mise releases contain
that affects the plan? (3) design the automated skill so ALL tools are
mined at once on the daily/Renovate cadence.

Grounding: `.omc/research/research-20260709-r2-inventory/report.md`;
angle reports `agents/complete-inventory.md`, `agents/missed-mise.md`,
`agents/skill-automation.md` (this run); adversarial-verification
verdicts on 8 load-bearing claims (7 CONFIRMED-or-usable, 2 REFUTED —
see the dedicated section).

---

## Executive summary — RECOMMENDATION up front

**No, the original enumeration was not complete — but the biggest gap is
NOT the Docker family.** The single most load-bearing finding, confirmed
3/3 by adversarial verification, is that the repo's own daily
tool-currency signal is **structurally blind to ~58 of its ~108 tracked
tools**: the two devcontainer image tiers
(`.devcontainer/mise-system.toml`, 36 tools; `.devcontainer/mise-runtime.toml`,
~22 tools) are invisible to both `mise outdated` (run from repo root; mise
discovery walks only *upward* from cwd, never into a child directory) and
to Renovate's native `mise` manager (its file-pattern glob requires
`mise.toml`/`mise.<env>.toml` — the hyphen in `mise-system.toml` never
matches). A 5th chezmoi-templated tier (`home/dot_config/mise/config.toml.tmpl`,
~30 tools) is invisible for a second independent reason: its extension is
`.tmpl`, not `.toml`.

**Recommended path (in priority order):**

1. **Bump the mise pin first.** `.devcontainer/Dockerfile:115` pins
   `MISE_VERSION=2026.7.2`, three patch releases behind v2026.7.5
   (2026-07-09). This is a stale pin, not missed research — and it
   *blocks* the `experimental = true` drop (bootstrap/dotfiles graduated
   to stable only in v2026.7.4). Let Renovate's `MISE_VERSION`
   customManager bump it, THEN drop the flag. Do not drop the flag first.
2. **Close the image-tier blind spot in the skill/`tool_currency.py`**,
   using the *corrected* mechanism (scratch-copy the two hyphenated files
   to `config.toml`/`config.runtime.toml` in a temp dir and point
   `MISE_CONFIG_DIR` at it — angle 1's "just `cd .devcontainer`" fix does
   NOT work; the files aren't named what mise's cwd-walk looks for).
3. **Add one 7th Renovate customManager** for `wagoodman/dive`'s
   hardcoded `DIVE_VERSION: 0.13.1` — a confirmed, ready-to-fix gap using
   the exact regex+`github-releases` shape already used for gcc-latest and
   `MISE_VERSION`.
4. **For the genuinely-unpinned Docker family** (Docker Engine, buildx,
   buildkit binary, containerd, `devcontainers/spec` `$schema`@main): add
   a read-only `gh release list` batch to the SAME daily job — there is no
   pinned string for Renovate to bump, so a chronological "what shipped"
   digest is the only viable automation.
5. **Do NOT retire the custom conda snapshot machinery** on the basis of
   the "conda backend now writes sha256+transitive deps to the lockfile"
   belief. That claim is **REFUTED** (0/3) and contradicts the
   `tool-currency-and-native-first.md` rule's own stated fact — flagged
   loudly below.

**On the Docker family specifically:** the user's instinct was right that
it was under-covered, but the precise "only 2 of 8 items watched" framing
is **wrong** — buildkit *is* partially watched today via the
`docker/dockerfile` syntax-directive digest (a moby/buildkit release
artifact) that Renovate's `dockerfile` manager tracks and PR #187 bumped.
Corrected accounting is below.

---

## Q1 — The COMPLETE watch-list, cross-checked against every source

Cross-checked against `mise.toml`, `.config/mise/conf.d/shared.toml`,
`renovate.json` (managers + customManagers), `.devcontainer/mise-system.toml`,
`.devcontainer/mise-runtime.toml`, `home/dot_config/mise/config.toml.tmpl`,
and the GHA workflows. ~108 tracked tools fall into six coverage classes:

| Class | Where | Tool count | Watched for release notes? | Mechanism |
|---|---|---|---|---|
| `mise-root` | `mise.toml:9-44` `[tools]` | 30 | **Yes** | `mise outdated` (repo-root cwd) + Renovate native `mise` manager |
| `mise-shared` | `.config/mise/conf.d/shared.toml:21-40` | 20 | **Yes** | same; Renovate native mise manager confirmed bumping this file (chezmoi 2.70.5→2.71.0 landed as a native-manager PR) |
| `mise-image-base` | `.devcontainer/mise-system.toml:21-76` | 36 (+15 apt) | **NO** (CONFIRMED gap) | invisible to `mise outdated` (upward-walk) AND Renovate (hyphen glob). Freshness only via daily lock-refresh auto-resolving `latest`; zero release-note review |
| `mise-image-runtime` | `.devcontainer/mise-runtime.toml:37-64` | ~22 | **NO** (CONFIRMED gap) | same as above; carries fnox, claude-code, gemini-cli, codex, sccache, turso, bats, the C++ lint toolchain |
| `mise-interactive-tmpl` | `home/dot_config/mise/config.toml.tmpl` | ~30 | **NO** (CONFIRMED gap) | `.tmpl` extension never matches Renovate's mise glob; all `latest`, no lockfile |
| `renovate-custom` | `renovate.json:33-96` (6 entries) | 6 | **Yes** | hk pkl pin, `.chezmoiversion`, clang-p2996 SHA, gcc-latest `.deb`, ubuntu digest, `MISE_VERSION` |

Plus GHA-pinned / hardcoded binaries outside the mise tree:

| Item | Location | Watched? |
|---|---|---|
| GHA action wrappers (`setup-buildx-action`, `trivy-action`, etc.) | workflows, SHA-pinned via pinact | **Yes** — Renovate `github-actions` manager |
| `wagoodman/dive` `DIVE_VERSION: 0.13.1` | `.github/workflows/image-analysis.yml:102` (env block → raw curl, not `uses:`) | **NO** (CONFIRMED gap — 9th self-discovered item) |

### The Docker family — CORRECTED tool-by-tool accounting

The "only @devcontainers/cli + sshd feature (2 of 8) are watched" claim
was **REFUTED** — buildkit is partially covered. Corrected table:

| Item | Repo state | Watched? |
|---|---|---|
| `@devcontainers/cli` | `mise.toml:10` npm pin `0.87.0` | **Yes** — Renovate npm manager |
| devcontainers **feature** `sshd` | `devcontainer.json:192` `sshd:1`, major-tag only (digest-pin disabled, PR #187/#196) | **Yes, coarse** — Renovate `devcontainer` manager, major-tag granularity only |
| **buildkit** (syntax frontend) | `.devcontainer/Dockerfile:1` `# syntax=docker/dockerfile:1.7@sha256:…`, digest-pinned | **Yes** — Renovate `dockerfile` manager; PR #187 (2026-07-08) bumped this exact `docker/dockerfile` digest, changelog → `moby/buildkit`. **This is the refutation of the "2 of 8" claim.** |
| **buildkit** (build *daemon*) | no `driver-opts.image` on any `setup-buildx-action` call site | **NO** — floats to latest each CI run |
| **buildx** (CLI plugin binary) | no `version:` input on any of 6 `setup-buildx-action` sites | **NO** — floats to latest each CI run (action wrapper IS watched; the binary it installs is not) |
| **Docker Engine / Desktop** | no pin; `docker-cli=29.6.1` (`mise.toml:41`) is the CLIENT only, not `dockerd`; engine prose `29.3.1+` in AGENTS.md | **NO** — no machine pin anywhere |
| **containerd** | zero repo references (substrate under DD/runner) | **N/A** — out of repo control |
| **docker compose** | `docker-compose` manager enabled but no compose file exists | **No-op** — nothing to scan (not a gap today) |
| **devcontainers/spec** `$schema` | `devcontainer.json:74` → `…/spec/main/…schema.json` (branch, not tag) | **NO** — floats on `main`; low risk (editor/validator hint only) |

Net corrected count of the 8 named items: **3 genuinely watched**
(@devcontainers/cli, sshd feature, buildkit-via-dockerfile-syntax), 4
unwatched/floating (Docker Engine, buildx binary, buildkit daemon, spec
`$schema`), 1 out-of-scope (containerd), plus compose as an enabled no-op.

---

## Q2 — What the missed mise releases contain that affects the plan

v2026.7.5 (2026-07-09) is confirmed still the latest as of 2026-07-10 —
no even-newer release was missed. The repo pins `2026.7.2`
(`.devcontainer/Dockerfile:115`), 3 behind. Content that touches the plan:

| Release | Date | What it ships | Impact on the plan |
|---|---|---|---|
| **v2026.7.4** | 2026-07-09 | **bootstrap + dotfiles graduate out of experimental** (`mise bootstrap` packages/repos/user-services/shell-activation + `mise dotfiles` work with `MISE_EXPERIMENTAL=0`, PR #10869) | **CONFIRMED**. The repo sets `experimental = true` at `mise-system.toml:119` (and `mise.toml:47` host). Dropping it today is **premature** — the pinned `2026.7.2` binary still gates `[bootstrap.packages]` behind the flag. **Sequence: bump pin ≥2026.7.4 first, then drop the flag, gated by CI + `mise doctor`.** |
| v2026.7.4 | 2026-07-09 | `MISE_INSTALL_SKIP_IF_EXISTS` (PR #10882); Rust component/target reconciliation (#10876); arm64 glibc fix (#10875) | Installer micro-opt relevant to `lock-refresh/action.yml:44` and the Dockerfile installer. Rust/arm64 items N/A (no rust in mise tiers; amd64-only). |
| v2026.7.3 | 2026-07-08 | brew cask lifecycle hooks; plugin-declared system deps | macOS/brew-only; image tier is apt-only — **no repo impact**. |
| **v2026.7.2** | 2026-07-07 | `get_env` Tera-v2 helper **restored** (PR #10830); **deprecated-settings warnings** (PR #10832) | `get_env` restoration means the repo's `env.VAR`-over-`get_env()` choice (`mise.toml:180-183`) should be **re-probed** — the comment's stated reason may no longer hold. Deprecated-settings warnings are a **new diagnostic with zero repo coverage** — a `mise doctor` / stderr-grep-for-`deprecated` step is a clean skill addition. |
| **v2026.7.1** | 2026-07-07 | **`start_calendar_interval` for macOS launchd agents** (PR #10797) | The r2 mac-automation report hand-designed a launchd plist from scratch — mise now has a native declarative `[bootstrap.macos.launchd.agents.*]` TOML equivalent for every field. Exactly the `tool-currency-and-native-first.md` "prefer native over hand-rolled" case. (Native layer replaces only plist-authoring + drift-detection, NOT the underlying maintenance logic.) Also: redaction wildcard→glob fix (#10729) and SOPS ordered-env (#10786), relevant to the fnox/Doppler secrets design (issue #83). |
| v2026.7.0 | 2026-07-02 | **shell expansion default-ON** in `[env]` (`env_shell_expand`, PR #10702) | Breaking-by-default, but **verified zero impact**: no `[env]` value in any of the four mise tiers contains a `$`-shell reference (all literals or Tera templates). `$VAR` usage lives in task `run` bodies, which are unaffected. No action; record that it was checked. |

**Net:** these are **under-actioned findings, not missed releases** — the
r2 release-mining pass on 2026-07-09 already enumerated them. The gap is
that the pin has not moved, which blocks the experimental-drop and leaves
the native-launchd overlap and get_env re-probe unactioned.

---

## Q3 — Skill design so ALL tools are mined at once on the daily cadence

The design **extends the existing daily mechanism, does not replace it**
(one signal, one judgment pass, one issue, one skill — satisfying "all
researched at once"):

**Existing shape (keep):** `tool_currency.py` (signal) → `mise run
tool-currency` (wiring) → `refresh.yml` daily cron → upserts one standing
"Tool currency report (daily)" issue → `tool-currency-check` skill
(judgment, run locally). This is the repo's canonical
python→task→cron→skill convention.

**Two new data sources into the SAME module/task/job:**

- **Gap class A — image-tier mise config.** Add a helper that scratch-copies
  `mise-system.toml`→`config.toml` and `mise-runtime.toml`→`config.runtime.toml`
  into a temp dir and runs `mise outdated --bump --json` with
  `MISE_CONFIG_DIR=<tmp>` and `MISE_ENV=runtime` — **reproducing the
  Dockerfile's own load mechanism** (`Dockerfile:75,127,388-389`). This is
  the *corrected* fix: angle 1's "run `mise outdated` with `cwd=.devcontainer`"
  would NOT work, because the files aren't named `mise.toml`/`config.toml`
  and mise's cwd-walk never finds them. mise has **no `MISE_CONFIG_FILE`
  arbitrary-path env var** (verified live) — the scratch-copy is required.
  Also fold in the `.tmpl` interactive tier (render it first, or point at
  `home/dot_config/mise/config.toml.tmpl` via the same scratch mechanism).

- **Gap class B — non-mise tools, split into two shapes:**
  - **B1 (pinned string, unwatched):** only `wagoodman/dive`'s
    `DIVE_VERSION` today. Native fix = a 7th Renovate `customManagers`
    regex entry with the `github-releases` datasource (documented,
    community-standard shape; same as the existing 6). **No new code** —
    Renovate's PR IS the release-note review.
  - **B2 (deliberately unpinned/floating):** Docker Engine, buildx binary,
    buildkit daemon, containerd, `devcontainers/spec` `$schema`@main.
    Renovate cannot help (no string to regex-extract). Add a **read-only
    `gh release list --repo <o>/<r> --limit N --json tagName,name,publishedAt`
    batch** over a static watch-list → rendered as a second chronological
    table in the SAME daily issue body. All four B2 repos publish standard
    GitHub Releases with real notes (moby/moby, moby/buildkit v0.31.1,
    docker/buildx v0.34.1). ~20 calls/day, trivially inside API budget.

**Watch-list becomes a tracked file** (proposed
`python/src/dotfiles_setup/watchlist.toml`, one row per tool tagged by
`class`), seeded from the Q1 table. This makes "did we identify ALL
tools" a `grep`/diff against a file forever — any new tool not added to
it is a reviewable diff gap, not a silent blind spot.

**Where results land:** daily raw signal stays in the standing issue
(wider content, same issue); judgment-pass artifacts land at
`docs/research/tool-currency/<date>.md` (matching the existing
`docs/research/trail/findings/` dated-snapshot precedent), each ending
with the mandatory `## GitHub repos touched` section. ADOPT→`mise run
ship`; multi-step→`.omc/plans/`; WATCH→tracked issue. No verdict lives
only in a transcript.

**No-MCP compliant by construction** — every mechanism is a mise-installed
CLI (`mise outdated`, `gh release list`) or plain HTTP fetch. Zero new MCP
servers, zero use of the Claude CLI mcp-add subcommand.

**New skill steps (additive to the existing 5):** Step-1 amendment
(`mise outdated` runs twice — root + image-tier scratch); new Step-3a
("Unpinned/floating watch" reads the B2 chronological table, decides
pin/keep-floating/no-action per repo); one guardrail bullet ("`github-releases`
customManager is the native fix for B1; `gh release list` batch is
reserved for B2 where no file has a value to extract"); plus a new
"grep `mise install` stderr for `deprecated`" step (from v2026.7.2's new
diagnostic).

---

## Refuted / unverified claims (do NOT assert as true)

Two of the eight adversarially-verified claims were REFUTED. They must not
be stated as fact anywhere downstream.

1. **REFUTED (0/3 upheld) — "mise's conda backend now writes per-platform
   sha256 + transitive deps to the lockfile natively (graduated
   ~v2026.5.0), retiring the custom snapshot machinery."**
   Verification found: mise's conda backend graduated only out of
   *experimental status* at v2026.5.0 (a stability flag, NOT a
   lockfile-schema change). mise's own docs
   (`mise.jdx.dev/dev-tools/backends/conda.html`,
   `.../mise-lock.html`) state the conda backend "only installs single
   packages, not full conda environments with dependencies" and conda
   appears in NONE of the lockfile support tiers. Open discussion
   `jdx/mise#7700` ("Add a Conda lockfile for reproducibility", opened
   2026-01-17, still open) confirms "the Conda backend does not lock the
   dependencies within the Mise lockfile." Likely conflation with
   *conda-the-package-manager*'s own May-2026 lockfile support.
   **Consequence: the custom `mise-system-resolved.json` /
   `mise_snapshot.py` snapshot machinery must NOT be retired on this
   basis.** This directly contradicts the standing
   `tool-currency-and-native-first.md` rule text (see Contradictions).

2. **REFUTED (1/3 upheld) — "Of the 8 Docker-family items, only 2
   (@devcontainers/cli, sshd feature) are genuinely watched; buildx,
   buildkit … have zero coverage anywhere in the repo."**
   Verification found the claim's OWN cited PR #187 (2026-07-08) is a
   counterexample: it digest-pinned `docker/dockerfile` (the buildkit
   syntax frontend, changelog → `moby/buildkit`) at `.devcontainer/Dockerfile:1`,
   tracked by Renovate's enabled `dockerfile` manager. So buildkit's
   syntax frontend IS under active Renovate coverage. Use the corrected
   "3 of 8 watched" accounting in the Q1 Docker table — the *buildkit
   build-daemon* and *buildx binary* installed by `setup-buildx-action`
   remain genuinely unwatched, but the blanket "buildkit has zero
   coverage" is false.

All other load-bearing claims were **CONFIRMED 3/3** (image tiers invisible
to tool-currency; Renovate hyphen-glob miss; `.tmpl` extension miss;
`DIVE_VERSION` gap; `MISE_VERSION=2026.7.2` is 3 behind; v2026.7.4
bootstrap graduation with the pin 2 short) and are asserted above.

---

## Open questions for Ray (with recommended answers)

1. **Bump `MISE_VERSION` to 2026.7.5 now, or wait for the 7d
   `minimum_release_age` gate?** *Recommended:* let Renovate's
   `MISE_VERSION` customManager bump it on its normal cadence (it carries
   the CHANGELOG for review); do not hand-bump. The experimental-drop is
   the only thing blocked, and it is not urgent.

2. **After the pin lands ≥2026.7.4, drop `experimental = true`?**
   *Recommended:* yes, in a separate PR gated by CI + `mise doctor`, once
   the pin is confirmed live in the built `:dev` image (not just the
   Dockerfile ARG). Keep host `mise.toml:47` separate — check the actual
   host mise version before touching it.

3. **Adopt mise's native `[bootstrap.macos.launchd.agents.*]` for the Mac
   maintenance automation the r2 mac-automation report hand-designed?**
   *Recommended:* yes for the plist-authoring + drift-detection layer
   (retire the hand-rolled plist per `tool-currency-and-native-first.md`);
   keep the `dotfiles_setup.maintain` python module for the actual
   maintenance logic. This is host-only and out of the devcontainer's
   R1/R2/R3 scope.

4. **Where does the watch-list file live?** *Recommended:*
   `python/src/dotfiles_setup/watchlist.toml`, for diffability, over
   embedding constants in `tool_currency.py`. Low-stakes; a build session
   can decide.

5. **Pin buildx/buildkit binaries, or keep floating?** *Recommended:*
   keep floating (matches the BASE/RUNTIME tiers' deliberate all-`latest`
   philosophy) but route them through the new B2 `gh release list` digest
   so drift is at least *visible*. Revisit only if CI build behavior
   becomes unreproducible.

6. **Re-probe `get_env()` vs `env.VAR` (v2026.7.2 restored the helper)?**
   *Recommended:* yes, cheap — one `mise config get` probe in a throwaway
   `mise.local.toml` before touching the `mise.toml:180-183` comment. Not
   blocking.

---

## Contradictions with the domain baseline / r2 conclusions

**LOUD:** The standing project rule `.claude/rules/tool-currency-and-native-first.md`
asserts as fact that "mise's rattler `conda:` backend now writes
per-platform `sha256` + transitive deps to `mise.lock` (graduated
v2026.5.0)… This **retires** the custom `mise-system-resolved.json`
snapshot + `mise_snapshot.py`." Adversarial verification (0/3 upheld,
three independent refutations against mise's live docs + open issue
`jdx/mise#7700`) shows this is **false**: the conda backend does not lock
transitive deps or write per-platform sha256; only its experimental *flag*
graduated. **The rule text is wrong on this point, and any plan step that
retires the custom snapshot machinery on this basis must be halted.** This
should be corrected in the rule file itself.

No other contradictions with the r2 inventory baseline — the image-tier
tier-split, the 6 customManagers, the Doppler secrets path, and the daily
refresh topology all held up. The only correction to an *angle* report is
the "2 of 8 Docker items watched" → "3 of 8" refutation (buildkit syntax
frontend is watched), and angle 1's proposed `cwd=.devcontainer` fix being
superseded by angle 3's scratch-copy `MISE_CONFIG_DIR` mechanism.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all in-repo file:line grounding across `mise.toml`, `.config/mise/conf.d/shared.toml`, `.devcontainer/{mise-system,mise-runtime}.toml`, `.devcontainer/{Dockerfile,devcontainer.json}`, `home/dot_config/mise/config.toml.tmpl`, `renovate.json`, `docker-bake.hcl`, `.github/workflows/{ci,build-publish,image-analysis,refresh}.yml`, `python/src/dotfiles_setup/tool_currency.py`, `.claude/skills/tool-currency-check/SKILL.md`, PRs #187/#196
- [jdx/mise](https://github.com/jdx/mise) — CHANGELOG + release pages v2026.7.0–v2026.7.5 (PRs #10702, #10729, #10786, #10797, #10830, #10832, #10869, #10875, #10876, #10882, #10890); `mise.jdx.dev/configuration.html` (no `MISE_CONFIG_FILE`); conda backend + lockfile docs; discussion #7700 (conda lockfile refutation)
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — mise-manager default `managerFilePatterns` (hyphen-glob miss); `github-releases` datasource (B1 fix); discussions #28157/#38002
- [docker/setup-buildx-action](https://github.com/docker/setup-buildx-action) — default buildx/buildkit version-floating when no `version`/`driver-opts.image` set
- [moby/moby](https://github.com/moby/moby) — Docker Engine standard GitHub Releases (B2 watch-list)
- [moby/buildkit](https://github.com/moby/buildkit) — v0.31.1 release shape; the `docker/dockerfile` syntax frontend PR #187 tracks (buildkit coverage refutation)
- [docker/buildx](https://github.com/docker/buildx) — v0.34.1/v0.35.0-rc2 cadence (B2 watch-list)
- [containerd/containerd](https://github.com/containerd/containerd) — substrate, out of repo control (B2 digest, not independently re-searched)
- [cli/cli](https://github.com/cli/cli) — `gh release list` batch flags for B2
- [wagoodman/dive](https://github.com/wagoodman/dive) — hardcoded `DIVE_VERSION` B1 gap + fix target
- [devcontainers/spec](https://github.com/devcontainers/spec) — `$schema` floating on `main`, unpinned (B2)
- [devcontainers/features](https://github.com/devcontainers/features) — `sshd` feature, major-tag-only Renovate coverage
