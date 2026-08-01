# Domain synthesis — mise `[dotfiles]` vs/with chezmoi for THIS repo

> ⚠️ **SUPERSEDED 2026-08-01 by [#448](https://github.com/ray-manaloto/dotfiles/issues/448)
> (`docs/receipts/448.md`). The recommendation below no longer holds; the analysis is kept as the
> 2026-07-10 baseline.** Re-measured on mise **2026.8.0**: the HARD BLOCKER (`promptBoolOnce`) is
> superseded by #439's decision to move `.ssh`/`.gnupg` onto the OS branch; `mode = "copy"`
> **preserves 0600**; the `is exists` test replaces `stat`; and the `.chezmoiignore` OS gate is
> replaced by **platform environments** (`mise.macos-arm64.toml` / `mise.linux.toml`) rather than by
> the config-level `{% if %}` this report left UNVERIFIED — so the `os_family()` correction below,
> while still factually right, is moot. Three of the four "standing uncertainties" are closed there
> (the `$remote` env signals: **0 of 5**, with `/.dockerenv` present in the container). **Current
> verdict: mise `bootstrap dotfiles` is the destination; chezmoi holds through the #431 takeover** —
> a deferral on blast radius and maturity, not on capability.

Run: `research-20260710-r3-mise-dotfiles` · Synthesis of 3 angle reports
(`mise-dotfiles-caps.md`, `chezmoi-parity.md`, `coexist-migrate.md`) plus the
adversarial-verification verdicts on 8 load-bearing claims. Date: 2026-07-10.
Baseline grounding: `docs/research/runs/research-20260709-r2-inventory/report.md`.

---

## Executive summary — RECOMMENDATION: NEITHER (keep chezmoi; do not adopt mise `[dotfiles]` yet)

**For THIS repo, mise `[dotfiles]` should NEITHER replace NOR complement chezmoi
today.** Keep chezmoi as the sole dotfile manager. Re-evaluate on a concrete
capability trigger (below), not on a calendar date.

Why, in one paragraph: mise `[dotfiles]` (shipped v2026.6.6 on 2026-06-13,
graduated from experimental to stable ~v2026.7.4 on 2026-07-09) is a real,
capable declarative dotfile manager with Tera templating, four apply modes, and
stateless marker-block edits — its *apply mechanics* map cleanly onto this
repo's devcontainer-only, run-once-per-create model. But a **replacement fails
on one hard, no-known-workaround blocker**: chezmoi's `promptBoolOnce`
interactive Mac-host setup (`is_dev_computer`/`is_personal`, persisted once to a
data file) has **no mise equivalent** — mise's only "prompt" is a `--yes`
apply-confirmation skip, a categorically different mechanism. A **complement /
hybrid has no driver**: the repo's `home/` tree (17 entries, zero `run_*`
scripts) has no "foreign-owned file that needs one marker-block poked into it"
gap for mise's edit mode to fill, so a hybrid would mean inventing new
apply-ordering machinery for zero benefit. Secondary friction reinforces
"neither": mise keeps **no state database** (removing an entry orphans its file
— a safety-net regression vs chezmoi's tracked apply), has **no
secrets/encryption** for managed files, **no `.chezmoiexternal` URL fetch**, no
`.chezmoi.osRelease` distro-ID granularity, and — a verification correction to
angle #2 — its `os_family()` **cannot** distinguish darwin from linux (it lumps
both into `"unix"`), and `os()` returns `"macos"` not `"darwin"`, so even the
"easy" machine-conditional gate needs a rewritten literal, not a drop-in.

The devcontainer-only constraint is **orthogonal** to the decision: mise's own
apply model is also manual-only, so it neither helps nor hurts the case. The
mechanically-easy part (swapping one `chezmoi init --apply` line in
`on-create.sh` for `mise dotfiles apply`) is not the bottleneck; the
feature-parity gaps are.

---

## Q1 — Can mise `[dotfiles]` REPLACE chezmoi here? No.

**One hard blocker + several bounded-cost gaps.** From angle #3 §4 (gaps
re-verified by reading `home/` directly), ranked:

| chezmoi mechanism used | Where (file:line) | Replacement cost in THIS repo |
|---|---|---|
| `promptBoolOnce` interactive setup | `home/.chezmoi.toml.tmpl:37-39` | **HARD BLOCKER** — mise has no data-gathering, persist-once prompt; only `mise dotfiles apply --yes` (confirmation skip). Confirmed by direct re-query of `mise.jdx.dev/dotfiles.html`. |
| `chezmoi managed` CI introspection gate | `.github/workflows/ci.yml:105-124` | **Medium** — real rewrite, but `mise dotfiles status --missing` (exit 1 if out of sync) is a designed-for replacement. Not capability-blocked. |
| `stat "/.dockerenv"` → `$remote` gate | `home/dot_zshrc.tmpl:1`, `dot_bashrc.tmpl:1` | **Medium** — 5 of 6 OR'd signals port to mise `env`/`get_env()`; the raw `/.dockerenv` `stat` has no mise template-function equivalent. Load-bearing only if the container sets none of the 5 env signals (unverified — see Open questions). |
| `.chezmoi.osRelease.id` distro branching | `dot_zshrc.tmpl:28`, `dot_tmux.conf.tmpl:9-19` | **Low today** — latent/future-proofing; only darwin-host + linux-devcontainer are real machines (`.chezmoi.toml.tmpl:1-6` says so). No operational loss. |
| `.chezmoitemplates/env` shared fragment | `home/.chezmoitemplates/env:1` (2 call sites) | **Low** — duplicate the one-line `exec("mise activate " + shell)` (mise `exec()` == chezmoi `output`). |
| `.chezmoiexternal.toml` remote URL fetch | `home/.chezmoiexternal.toml:7-10` | **Low** — same-file comment already documents `mise completion zsh > _mise` as the local replacement. |
| `executable_` filename chmod | `home/dot_local/bin/executable_claude` | **Low** — one `chmod +x` in create script. |
| Machine-conditional file gating (`.chezmoiignore`) | `home/.chezmoiignore:5,11,52` | **Open/Medium** — see Q-osfamily correction below; requires wrapping each `[dotfiles]` entry in a Tera `{% if %}`, UNVERIFIED that mise config-level templating can conditionally omit whole table entries. |
| Secrets / encrypted files | `home/.chezmoidata.yaml` (no secrets) | **Zero** — repo secrets flow through Doppler at devcontainer level (`devcontainer.json:198`), never chezmoi age/gpg. The general "mise dotfiles has no secrets" gap is real but **inapplicable here**. |
| `run_*` scripts | `Glob home/**/run_*` → zero | **Zero** — repo doesn't use chezmoi scripts at all. |
| `.chezmoiremove` | `home/.chezmoiremove` (empty) | **Zero** — unused. |

Net: most gaps are low/zero once measured against *actual* usage rather than
chezmoi's theoretical footprint — but `promptBoolOnce` alone is a categorical
blocker, and mise's **no-state-database** design (verified CONFIRMED) is a real
apply-safety regression: removing a `[dotfiles]` entry silently orphans its
file/block/line with no un-apply, unlike chezmoi's tracked-state model.

### Correction to angle #2 §1 (verification-driven): the "easy" OS gate is NOT a drop-in

Angle #2 marked the `chezmoi.os` machine gate "Covered" by mise's
`os()`/`os_family()`. **Verification REFUTED the equivalence** (claim #7, 0/3
upheld). Facts:
- chezmoi `.chezmoi.os` returns `"darwin"`/`"linux"`.
- mise `os()` returns `"macos"`/`"linux"`/`"windows"` — a **different literal**
  (`macos` ≠ `darwin`); any port needs `os() == 'macos'`, not a copy of the
  chezmoi check.
- mise `os_family()` returns only `"unix"`/`"windows"` — it **collapses macOS
  and Linux into one `"unix"` bucket** and therefore **cannot** express the
  darwin-vs-linux split at all.

So the single highest-stakes conditional in the repo — the `.chezmoiignore:52`
hard gate that stops the devcontainer-only mise overlay from rendering on the
Mac host — is replicable *only* via `os() == 'macos'`/`'linux'` string
branching, and *only if* mise config-level templating can conditionally omit
whole `[dotfiles]` entries (still UNVERIFIED). It is not the frictionless
"Covered" that angle #2 implied.

---

## Q2 — Can mise `[dotfiles]` COMPLEMENT chezmoi here (hybrid)? No driver.

From angle #3 §1–§2:
- mise's model is per-target-path; chezmoi already claims all 17 `home/`
  targets. A safe hybrid requires **zero target overlap** — neither tool knows
  about the other.
- The only natural interop seam is mise's **block/line edit mode** ("manage one
  small piece of a file something else owns", verified CONFIRMED). **This repo
  has no such target**: every `home/` file is either a whole chezmoi-owned
  `.tmpl` or a static file. There is no foreign-owned file needing a
  marker-block.
- A hybrid would require *new* machinery: a new `on-create.sh` step ordered
  chezmoi-first/mise-second (chezmoi's `--force` re-render would otherwise
  clobber mise's writes), and a `[dotfiles]` table in the **root `mise.toml`**
  (not the chezmoi-rendered overlay — that would be circular).
- No prior art: two independent web searches (angles #1 §14, #3 §3) found the
  native `[dotfiles]` feature has **never** been combined with chezmoi for the
  same files in the wild. The only "chezmoi + mise" repos use them for
  *non-overlapping concerns* (chezmoi=files, mise=tool versions), which predates
  the `[dotfiles]` feature entirely.

Cost with no offsetting benefit ⇒ do not build a hybrid speculatively.

---

## Q3 — The devcontainer-only constraint: orthogonal, mechanically compatible

`chezmoi apply`/`update` are DENY-listed on the Mac host (verified CONFIRMED —
`.claude/settings.json:4-5` + `python/src/dotfiles_setup/hook_guard.py:62-68`;
read-only chezmoi allowed). chezmoi applies once per container create via
`.devcontainer/scripts/on-create.sh:41`.

mise `[dotfiles]` is **also manual-only** ("never applied implicitly", verified
CONFIRMED). So swapping the single apply line is a trivial one-line
substitution that preserves the exact "runs once, non-interactive,
in-container-only" shape (angle #3 §5). The constraint therefore **does not tilt
the decision either way** — it neither blocks nor motivates a switch. The entire
cost lives in Q1's parity gaps, not the wiring.

Additional container-specific note (angle #1 §8, verified CONFIRMED, though one
verifier dissented on the whole feature's existence — see Refuted section):
mise dotfiles writes as the current user with no sudo. This repo's devcontainer
runs as non-root UID 1000 (`AGENTS.md` DEVCONTAINER_USERNAME), so any future
root-owned target (`/etc/*`) would fail — but the repo manages no such targets
today, so this is a latent, not active, constraint.

---

## Q4 — mise `user.html` / `shell.html` relevance: none (pages don't exist)

Both `mise.jdx.dev/user.html` and `mise.jdx.dev/shell.html` return HTTP 404
(angles #2, #3 §6). The real shell-adjacent pages — `cli/shell.html` (session
tool pinning), `cli/activate.md`, `dev-tools/shims.md` — are about
tool-activation, not dotfile-file management, and surface no additional
coexistence/migration capability. The brief's referenced URLs are stale paths.

---

## What mise `[dotfiles]` genuinely does well (for a future re-eval)

All CONFIRMED by verification (claims #1, #3, #5, #6):
- **Native Tera templating** — same engine/context as `mise.toml` (`env`,
  `vars`, `exec()`), with `os()`/`arch()`/`os_family()` built-ins for
  per-machine output. Structural analog to chezmoi's builtin facts (modulo the
  literal-value mismatch in Q1's correction).
- **Four apply modes** — symlink (default), symlink-each, copy, template.
- **Stateless marker-block/line edits** — for files mise doesn't own; ownership
  recorded in the file's own marker comments, no state DB.
- **Strict conflict handling** — errors on unmanaged-file collisions, `--force`
  to override; edit entries never need `--force` but hard-error on corrupted
  markers or symlink targets.
- **CI-friendly gate** — `mise dotfiles status --missing` exits 1 on drift.
- **`mise bootstrap` umbrella** — one-command machine setup (packages, repos,
  dotfiles, shell activation, services).

These make it a legitimate chezmoi alternative *for simpler setups* (the
third-party blog.verybadfrags.com post frames it exactly that way). This repo
is not a simpler setup on the one axis that matters (`promptBoolOnce`).

---

## Refuted / unverified claims (do NOT assert these as true)

- **REFUTED (claim #4, 1/3 upheld): "The feature is absent from third-party
  mise-vs-chezmoi comparison content as of 2026-07-10."** This sub-claim is
  false. `https://blog.verybadfrags.com/posts/manage-dotfiles-with-mise/`
  (published 2026-06-13, same day as v2026.6.6, still live) explicitly compares
  the feature to chezmoi ("more advanced dotfiles tool like chezmoi"), and
  further searches surface feature-by-feature "chezmoi wins X / mise wins Y"
  content. The angle reports (#1 §14, #3 §3) that leaned on "no comparison
  content exists" overstated it. **What DID survive:** the release fact
  (v2026.6.6, 2026-06-13) and the local-cache staleness (jdx/mise cache predates
  the feature; last probed 2026-04-06) are both CONFIRMED. Also note (from r2
  release-mining, `docs/research/runs/research-20260709-r2-release-mining/report.md`)
  that bootstrap+dotfiles **graduated from experimental to stable in v2026.7.4
  (2026-07-09)** — i.e. it was stabilized the day before this research, not
  still-experimental. Treat "very new" as accurate; treat "unvalidated by any
  third party" as **overstated**.

- **REFUTED (claim #7, 0/3 upheld): "mise's `os()`/`os_family()` cover the same
  darwin/linux split as `chezmoi.os`."** See Q1 correction above. The chezmoi
  half (the `.chezmoiignore:52` hard gate on `chezmoi.os`) is CONFIRMED, but
  mise `os_family()` returns only `unix`/`windows` (cannot distinguish
  darwin/linux), and `os()` returns `macos` (a different literal than
  chezmoi's `darwin`). Any assertion that the gate ports "as-is" or is fully
  "covered" is refuted — it needs a rewritten `os() == 'macos'` literal, and
  the whole-entry conditional-omission question remains UNVERIFIED.

- **Partially-dissented (claim #6, 2/3 upheld, verdict CONFIRMED): "mise dotfiles
  writes only as the current user / no sudo."** Upheld 2/3; one verifier claimed
  the mise dotfiles feature doesn't exist at all (relying on the stale local
  cache and 404s on `.md`/`llms.txt` suffixes). That dissent is **outweighed**:
  the feature's existence is independently CONFIRMED by the v2026.6.6 GitHub
  release, the live `dotfiles.html` page, and the third-party blog. Treat the
  no-sudo/root-file behavior as accurate but note it is a live-fetch-sourced
  fact, not byte-verified against raw HTML.

CONFIRMED and safe to assert: claims #1 (templating), #2 (no secrets/encryption),
#3 (manual-only/idempotent/no-state-DB), #5 (four modes + strict conflicts), #8
(chezmoi devcontainer-only deny-list).

### Standing uncertainties (unverified either way — inherited from the angles)

- Whether mise config-level templating can wrap `[dotfiles]` entries in
  `{% if %}` to conditionally declare/omit whole entries (needed to replicate
  `.chezmoiignore` machine-conditional gating). UNVERIFIED — blocks the
  cleanest replacement path.
- Whether the devcontainer sets any of the 5 non-`stat` `$remote` env signals
  (`CODESPACES`/`SSH_CONNECTION`/`KUBERNETES_SERVICE_HOST`/`container`/
  `REMOTE_CONTAINERS`). If none, the `/.dockerenv` `stat` is load-bearing and
  the `$remote` gap hardens from Medium toward blocker.
- Whether mise has a `mode`/permission key replacing `executable_`. Low-stakes
  (a `chmod +x` works regardless).
- No empirical `mise dotfiles apply --dry-run` was ever run — all three angles
  are docs/source-reading only (Bash broken this session).

---

## Open questions for Ray (with recommended answers)

1. **Decision: adopt mise `[dotfiles]` now, later, or never?**
   *Recommended:* **Not yet, not never.** Keep chezmoi. The single blocker is
   `promptBoolOnce`; everything else is bounded-cost or inapplicable. Revisit on
   a concrete trigger, not a date.

2. **What triggers a re-evaluation?** *Recommended (all three must hold):*
   (a) mise ships an interactive-prompt-and-persist mechanism closing the
   `promptBoolOnce` gap, OR the repo's `is_dev_computer`/`is_personal` need goes
   away; AND (b) the feature accrues independent production track record or a
   changelog entry signalling post-`v2026.7.4` hardening; AND (c) a genuine
   "small edit into a foreign-owned file" need actually arises in `home/` — at
   which point a **scoped complement** (mise for that one file, chezmoi for
   everything else) is the right shape, not a wholesale hybrid.

3. **Should we validate the "low cost" gap assessments empirically before ever
   acting?** *Recommended:* Yes — a future in-devcontainer session should run
   `mise dotfiles status`/`apply --dry-run` against a scratch `[dotfiles]` table
   mirroring ~3 `home/` entries, and probe `env` inside the container for the 5
   `$remote` signals. Both are blocked in this Bash-broken research session.
   Low priority (only matters if the decision ever flips toward adoption).

4. **Is the sibling-repo precedent decision-relevant?** *Recommended:* Treat as
   circumstantial only. `ray-manaloto/macos-development-environment` (via
   DeepWiki, third-party mirror) shows the same chezmoi-primary/mise-secondary
   convention, reinforcing that the choice isn't driven by the devcontainer
   constraint — but it's not primary-source evidence.

---

## Contradictions with the domain brief baseline / r2 conclusions

- **"Absent from third-party comparison content" (angles #1 §14, #3 §3) — REFUTED.**
  Comparison content exists (blog.verybadfrags.com, 2026-06-13). Flagged loudly
  above. Does not change the recommendation (the blocker is `promptBoolOnce`,
  not lack of prior art), but the supporting rationale must be corrected.
- **"os()/os_family() cover the same darwin/linux split" (angle #2 §1) — REFUTED.**
  os_family() cannot distinguish darwin/linux; os() uses `macos` not `darwin`.
  This makes the "easy" OS gate a rewrite, not a drop-in — strengthens "neither."
- **Experimental-vs-stable status:** angle #1 §1 said the docs don't mark the
  feature experimental. r2 release-mining
  (`docs/research/runs/research-20260709-r2-release-mining/report.md:62`) dates the
  experimental→stable graduation to **v2026.7.4 (2026-07-09)** — one day before
  this research. Consistent, not contradictory, but worth stating: the feature
  was stable for exactly one day at research time, which *supports* the "very
  new, unproven maturity" caution.

No contradictions found with the r2 inventory baseline itself (secrets flow via
Doppler, chezmoi devcontainer-only deny-list, tool-tier topology) — all
corroborated by this run's file:line reads.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo;
  all `home/**` chezmoi sources, `.chezmoiignore`, `.chezmoi.toml.tmpl`,
  `.chezmoiexternal.toml`, `.chezmoidata.yaml`, `.chezmoiremove`,
  `.chezmoitemplates/env`, `.devcontainer/scripts/on-create.sh`,
  `.devcontainer/AGENTS.md`, `.github/workflows/ci.yml`, `.claude/settings.json`,
  `python/src/dotfiles_setup/hook_guard.py` read for file:line evidence.
- [jdx/mise](https://github.com/jdx/mise) — primary subject; `dotfiles.html`,
  `templates.html`, `bootstrap.html` (mise.jdx.dev, live — not in local cache),
  and the `v2026.6.6`/`v2026.6.14` GitHub release notes.
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — incumbent system;
  `chezmoi.io/user-guide/manage-machine-to-machine-differences/` and
  `/encryption/` for the canonical `chezmoi.os`/`.chezmoiignore` and
  age/gpg-encryption patterns this repo cites.
- [dankaiser1808/dotfiles](https://github.com/dankaiser1808/dotfiles),
  [shunk031/dotfiles](https://github.com/shunk031/dotfiles) — surfaced in web
  search as the pre-`[dotfiles]` chezmoi+mise (non-overlapping-concern) pattern;
  titles/descriptions only.
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment)
  — same-author sibling repo; consulted via DeepWiki mirror as circumstantial
  cross-repo precedent for the chezmoi-primary convention.
