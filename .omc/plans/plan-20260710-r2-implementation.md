# Plan — R2 Implementation (successor to plan-20260709-unified-image.md)

Date: 2026-07-10. Supersedes `.omc/plans/plan-20260709-unified-image.md` (the
r1 unified-image plan). Grounded in the seven r2 domain reports and the
unified synthesis (`.omc/research/research-20260709-r2-synthesis/report.md`).
This is an execution plan, not new research — every item traces to a verified
finding cited there.

## Framing

The synthesis through-line: **formalize the mise config as the ONE shared
source of truth; let thin per-environment consumers fan out from it.** No
universal image, no self-hosted control plane. The work is ~a dozen small,
mutually-reinforcing changes, ordered below into phases by dependency.

**Convention mandate (applies to every new capability built below).** Per the
repo's own rules, any repeated action becomes: skill → `mise` task → python
library (`python/src/dotfiles_setup/`, zero-bash-logic), always with (a) docs
synced in the same change (AGENTS.md / rule / skill, respecting
`claude_md_size_limit`), (b) an hk step and/or agent double-check wiring, and
(c) a mandatory-checks checklist. The per-workstream "convention compliance"
box below instantiates this.

**Global mandatory-checks checklist** (every PR in every phase; from
`verify-before-advancing.md`): `mise run lint` rc=0 · `uv run --project python
pytest tests/ -x -q` green · `dotfiles-setup verify run` 0 failed · conditional
rows (`mise run pin-actions` if `.github/**`; `mise run lint-docs` + ≤200-line
/ ≤12000-char limit if `*.md` docs; `mise run verify-local` if `.devcontainer/**`
or image inputs) · PR checks watched to terminal green · post-merge `main` CI
`conclusion == success`.

---

## Phase 0 — Quick wins (independent, low-risk, ship first)

Small edits with no cross-dependencies; land them in any order to bank value
and de-risk later phases. Each is one-file-ish.

| # | Change | File(s) | Source | Notes |
|---|---|---|---|---|
| 0.1 | Override the inherited Friday-only Renovate schedule | `renovate.json` (+`"schedule": ["at any time"]`) | Synthesis §2d (C#1=D#24) | The entire daily-or-better gap on the Renovate surface. Verify effect on the next Renovate run. |
| 0.2 | Commit `.devcontainer/mise-runtime.lock` in the daily refresh | `refresh.yml` `open-refresh-pr` `paths:` (`:107-111`) | C#2 | Live bug: runtime lock regenerated then discarded; runtime tools never refreshed. |
| 0.3 | `mise lock --minimum-release-age 7d` on the composite | `.github/actions/lock-refresh/action.yml:31,58` | D#2 | Closes PR #169 fail-close class. Decide `minimum_release_age_excludes` fate same PR. Flag shipped v2026.5.6 (not 5.7). |
| 0.4 | Move both crons off `:00` (drift hygiene) | `refresh.yml` (00:00→e.g. `17 0`), `ci.yml` (02:00→`23 2`) | C#7 | `:00` is the documented worst GHA scheduled-queue window. |
| 0.5 | Fix the two devcontainer-Doppler bugs | `devcontainer.json:198` (download→temp→`mv`); smoke tier-2 (`devcontainer-smoke.sh:91-104`) and/or `verify-secrets` S1 (`mise.toml:518-541`) require ≥1 non-metadata canary | E deltas #1-2 | Closes the "zero-real-secret download passes both gates" false-green. |
| 0.6 | Correct `.devcontainer/AGENTS.md:54-55` issue-#83 note | `.devcontainer/AGENTS.md` | D#7, E§2.1 | #83 is OAuth-token injection, NOT static-secret migration; the mise-env-fnox future-note is wrong. Also correct the Colima "hard-lock" and "two rotation points" framing (E deltas #7-8). |
| 0.7 | ruff/py3.14 comma-except doc correction | `python/AGENTS.md` + `feedback_python2_comma_except` memory | D#15 | ruff 0.15.20 (live in `uv.lock`) already contradicts the documented trap today. |
| 0.8 | Harden `no_lint_skip` grep for spaced ruff suppressions | `hk.pkl:98` | D#16 | ruff 0.15.0 stabilized `# ruff: disable[...]`; current grep misses spaced forms. |
| 0.9 | Bring `doppler` CLI under mise management | host `mise.toml [tools]` or `shared.toml` (`doppler`→`github:DopplerHQ/cli`) | E delta #5 | Most security-critical currently-unmanaged tool. |
| 0.10 | `chezmoi --error-on-conflict` + `.chezmoiversion`→2.71.0 | `.devcontainer/scripts/on-create.sh:41`, `.chezmoiversion` | D#22 | Probe `--no-tty` interplay first. |
| 0.11 | Doc-only: chezmoi unknown-field detection note | `.claude/skills/chezmoi-check/SKILL.md` | D#23 | Already live at installed 2.70.5. |

**Convention compliance (Phase 0):** these are edits to existing
config/docs, not new capabilities — the docs-sync + mandatory-checks columns
cover them. 0.5/0.9 touch enforcement, so update the relevant contract/smoke
text in the same PR.

---

## Phase 1 — The fork-ready base-tier split (keystone; unblocks Phases 2 & 4)

The keystone four domains touch (Synthesis §2a). Do this as one structural PR
before the web lane and the updater topology depend on the new layout.

**Change (Run B Phase-0):**
- Split `.devcontainer/mise-system.toml` → `mise-core.toml` (COPY as
  `config.toml`: the 20 shared pinned tools + python/uv) + `config.cpp.toml`
  (`MISE_ENV=cpp`: 8 runtimes + ~25 conda C++ packages), with a per-env
  `mise.cpp.lock`.
- Insert an internal, **unpublished** `devcontainer-core` stage before
  `devcontainer-base`; re-root `devcontainer-base` on it. Optionally pre-wire
  the `CORE_HASH_BEGIN/END` sentinel + `core-hash` tier so a future `:core`
  probe is one flip away.
- Drop the graduated `experimental=true` at `mise-system.toml:119` **in the
  same PR** once `MISE_VERSION`≥2026.7.4 (D#4). Handle the host-side
  `mise.toml:47` flag **separately** — it is not ARG-gated (D#4 correction).

**Cost/preservation (CONFIRMED, Run B):** one ~25-min cold base build, zero
compiler rebuild (p2996-hash independent), one `:dev-<hash>` marker miss.
Preserve the warm path + `verify-container-latest` by handling the six gates
in the same change (smoke tier-1 identity → point at core/cpp configs; the
`changes` path-filter → add the new toml/lock names; ghcr-cleanup families;
promote; provenance). Do **not** publish a `:ci` leaf (Phase 1-deferred in the
report; gated on a real consumer).

**Convention compliance:** image change → `mise run verify-local` (or a direct
`docker run` check) is mandatory; base-currency is a hard gate. Update
`.devcontainer/AGENTS.md` tier table + `P2996-CACHE.md` in the same PR.

---

## Phase 2 — The three self-learning automation workflows (the core ask)

Each is a NEW recurring capability → full skill → mise task → python library
treatment. Build after Phase 0 (schedule/lock fixes) so they sit on a correct
updater baseline.

### 2A. Release-notes feature-mining workflow (automated tool-currency)
- **What:** automate what Run D did by hand — periodically mine the fast-moving
  tools' release notes for features that retire custom code, emitting a
  retire/adopt/watch report.
- **Build:** extend `python/src/dotfiles_setup/` (a `tool_currency` module) +
  a `mise run tool-currency-report` task; the existing `tool-currency-check`
  skill becomes its front door. Cache-first per `research-doc-sources.md`;
  changelog-over-docs per `tool-currency-and-native-first.md`.
- **Double-check:** output is advisory (a report/issue), so the "hook" is an
  agent review pass before any retirement PR — never auto-edit source.
- **Mandatory checks:** the report cites version+date+file:line for every claim
  (the Run D format); no retirement lands without its own Phase-0-style PR +
  the global checklist.

### 2B. Daily-or-better version/commit discovery → build triggering
- **What:** the trigger topology from Run C — keep hosted Renovate (~4-hourly
  after 0.1) + `refresh.yml` daily lock-refresh (sole writer of the 5-artifact
  lock set, now 6 with core/cpp) as the discovery engine; add the gap-closers.
- **Build (Run C change-list #5):** a ~40-line regen-push micro-workflow on
  `renovate/**` PRs touching `devcontainer.json` (run `devcontainer upgrade`,
  push with the refresh App token, add it to `gitIgnoredAuthors`, make it a
  required check) — closes the devcontainer-feature and MISE_VERSION two-PR
  hard-red windows. Keep the git-refs customManager as the sole p2996 writer
  (C#3). Optionally add the trusted gcc-deb sha256 recompute job (C Q2, policy
  decision — see open questions).
- **Do NOT** buy sub-daily discovery for freshness; defer the external
  minute-accurate dispatcher until measured drift shows the stagger inverting
  (C#7). No `container:` keys enter `ci.yml`, ever (Run B).
- **Convention compliance:** `.github/**` change → `mise run pin-actions`;
  workflow logic that isn't trivial glue lives in python; document in
  `.github/workflows/AGENTS.md`.

### 2C. Automated macOS pull + verification
- **What:** Run F — after the nightly publish, the Mac auto-runs digest-aware
  `mise run sync` + `mise run verify-local`, alerting on failure.
- **Build:** a `mise run maintain` task → new `dotfiles_setup.maintain` module
  (modeled on `lint.py`'s bounded-subprocess + rc-to-file house style): digest
  staleness check → assert `desktop-linux` context (never switch) → ensure
  Docker Desktop (prefer first-party `docker desktop start`, now fixed —
  F-refuted #15) → bounded sync → bounded verify-local → 3-channel alert (ntfy
  urgent + healthchecks.io dead-man switch + `gh issue` upsert with explicit
  `GH_TOKEN`). Scheduler: a `gui/<uid>` **launchd LaunchAgent**
  (`StartCalendarInterval` ~06:30 CT + `RunAtLoad` gated by the staleness
  check), wrapper prepends mise shims to PATH. NOT the self-hosted GHA runner
  (public repo). NOT pitchfork yet (young cron path).
- **Alert secrets** in `mise.local.toml [env]`, not Doppler (avoids
  keychain-under-launchd risk).
- **Convention compliance:** new skill (`devcontainer-maintain`) → the
  `mise run maintain` task → the python module; `.devcontainer/AGENTS.md`
  documents the launchd job; mandatory-checks incl. `mise run verify-local`.

---

## Phase 3 — Web-session lane + secrets adapter (parallel to Phase 2)

### 3A. Web-session setup (fixes THIS session's brick)
- **Build (Run A + D#14, one fix three hats):** a per-environment **setup
  script** (root, Ubuntu 24.04, ≤5-min budget, snapshot-cached ~7d) installing
  mise from a GitHub-release binary → `mise trust && mise install` the
  `shared.toml`/core toolset (NOT the full root `mise.toml`) → `uv sync
  --project python` (with `uv python install 3.14`); plus a repo SessionStart
  hook gated on `CLAUDE_CODE_REMOTE=true` persisting PATH via `$CLAUDE_ENV_FILE`.
  Set a read-only `GITHUB_TOKEN` env var. Trusted network policy suffices.
  Consider making the PreToolUse guard no-op when its interpreter is absent
  (A Q6). Reuse the local `session-start-hook` skill.
- **Verify:** the A-Q8 first-live-session probe (one ~15-min session).

### 3B. fnox — one narrow job, or retire (reconciled D+E, Synthesis §2b)
- Do **not** adopt the mise-env-fnox plugin. Keep host-side Doppler as the sole
  devcontainer path. Either build the narrow plugin-free `fnox exec` +
  committed-age-ciphertext adapter for the low-blast-radius web/CI research
  keys (E§2.3), **or** retire the unused `fnox="latest"` pin
  (`mise-runtime.toml:41`) if no consumer lands within ~a month. The
  `fnox mcp env="exec"` blast-radius reduction (D#6) is a later opt-in via
  `mcp2cli` only.

---

## Phase 4 — Knowledge base for the research corpus (Run G)

- **Layer 1 (build now):** python-native `docs/research/INDEX.md` generator +
  YAML front-matter on new artifacts + an hk validator (reusing the whole-tree-
  grep idiom of `claude_md_size_limit`/`no_mcp_registration`), wired as
  `mise run research-index` / `dotfiles-setup research validate`. Closes the
  enforcement gap `research-repo-enumeration.md` + `agent-report-persistence.md`
  already promise.
- **Corpus boundary (G Q1):** promote durable run outputs to
  `docs/research/runs/<slug>/` so this round's outputs (and future ones) are
  clone-visible — otherwise they share the r1 Mac-only fate.
- **Layer 2 (gated pilot, Mac-only):** periodic graphify synthesis over
  `docs/research/` + `.omc/research/` (excluding `mintlify-cache/`), outputs
  committed to `docs/research/graph/`, wrapped in `mise run research-graph`;
  monthly/on-demand, never the hot query path (LazyGraphRAG economics). Keep
  markdown+grep primary.
- **This very round is the pilot's seed content.**

---

## Sequencing summary

```
Phase 0 (quick wins, any order)  -┐
                                  ├─► Phase 1 (core/cpp split, keystone)
                                  │        ├─► Phase 2B (updater gap-closers, on new lock layout)
                                  │        └─► Phase 3A (web lane reads core/shared)
Phase 2A (tool-currency)  ────────┘   (independent; informs future Phase-0-style PRs)
Phase 2C (mac automation) ─── after a nightly publish exists on the new topology
Phase 3B (fnox decision)  ─── after 0.6 (AGENTS.md correction)
Phase 4 (KB)              ─── independent; do Layer 1 early to index this round
```

## Open questions carried to Ray (from the synthesis §5 — decide before/at each phase)

- **P0:** land the core/cpp split (1); the Friday-schedule override (0.1);
  the runtime-lock paths fix (0.2); `--minimum-release-age` (0.3); the two
  Doppler bugs (0.5); the web lane (3A); plain-launchd mac automation (2C);
  the KB index (4 L1). All recommended **yes**.
- **P1:** measured image-size number; regen-push micro-workflow; gcc-deb
  sha256 automation (**policy/posture decision** — TOFU friction vs
  verification, document against #160 T13); keep git-refs for p2996; fnox-age
  adapter vs retire the pin; doppler-under-mise; corpus-boundary promotion;
  web first-live-session probe. Recommendations in synthesis §5.
- **P2:** `:ci` leaf trigger (consumer-gated); external cron-drift dispatcher
  (defer); git-over-HTTPS R2 lane into durable criteria (**needs your explicit
  sign-off** per the durable-criteria rule; run the #78 Colima probe first);
  repo→private (reopens self-hosted-runner); graphify cadence.

## Verification

Every phase gates on the global mandatory-checks checklist above. No phase
advances until its checks are green with evidence read from the real artifact
(file `rc` / API `conclusion`), never a piped tail. Image-touching phases (1,
2C) additionally gate on `mise run verify-local` / `verify-container-latest`
with a current base. Docs-touching PRs gate on `mise run lint-docs` + the size
limit.
