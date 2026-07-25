# Run D / Angle 4 — astral (uv, ruff, ty) release mining, 2026-01..2026-07

Analyst report, 2026-07-09. Remote-fetch only (astral repos are NOT in the
local mintlify cache — confirmed by the R2 inventory,
`docs/research/runs/research-20260709-r2-inventory/report.md:107-108`). All web
sources are ≤6 months old unless noted.

## Repo baseline (file:line evidence)

- uv pinned **0.11.27** in `.config/mise/conf.d/shared.toml:37`; python
  **3.14.6** at `:32`. Latest uv upstream is **0.11.28 (2026-07-07)** — one
  patch behind, Renovate territory.
- `python/uv.lock` resolves **ruff 0.15.20** (`uv.lock:182-183`) and
  **ty 0.0.56** (`uv.lock:207-208`); both are UNPINNED specifiers in
  `python/pyproject.toml:106-107` (deliberate: bump via
  `uv lock --upgrade-package`, per comment at `pyproject.toml:102-105`).
- hk wiring: ruff/ruff_format are hk **builtins with
  `prefix = "uv run --project python"`** (`hk.pkl:55-60`); `py_ty` is a
  custom whole-dir step
  `uv run --project python ty check --project python python/src tests plugins`
  (`hk.pkl:77`). Suppression guard `no_lint_skip` grep at `hk.pkl:98`.
- ty config lives at `python/pyproject.toml:79-80`
  (`[tool.ty.environment] python-version = "3.14"`), discovery caveat
  documented at `:75-78` (#160 T12 probe).
- Root `ruff.toml` extends `python/pyproject.toml` (`ruff.toml:7`), with
  the re-anchoring fragility note at `ruff.toml:9-17`.
- Claude hook: `.claude/settings.json:15` runs
  `uv run --project python dotfiles-setup hook pretooluse` — this is the
  command that fails closed in the remote container ("no Python ≥3.14",
  inventory report lines 120-124).

## Findings

### 1. uv — python management: the "no Python 3.14" failure is solvable with stock uv, no custom code

- uv **auto-downloads missing interpreters during `uv run`/`uv sync`**;
  the `python-downloads` setting **defaults to `automatic`**
  (docs: <https://docs.astral.sh/uv/concepts/python-versions/>, fetched
  2026-07-09). So `uv run --project python …` (the exact hook command,
  `.claude/settings.json:15`) self-heals a missing CPython 3.14.6 wherever
  (a) the `uv` binary exists and (b) GitHub release downloads are reachable
  (through the agent proxy in the remote container). The failure mode in
  the R2 inventory is therefore an *environment bootstrap* gap (no uv on
  PATH / blocked download), not a gap uv has left for custom code.
- `uv python install 3.14 --default` installs `python3.14` (and `python`)
  shims onto PATH (`~/.local/bin`); the `--default` executable behavior is
  gated behind the `python-install-default` preview feature
  (<https://docs.astral.sh/uv/concepts/preview/>, fetched 2026-07-09).
- uv transparently upgrades managed Python **patch** versions
  (3.14.x→3.14.y) via symlinked installs; minor versions are never
  auto-upgraded (same python-versions doc). Complements — does not fight —
  the exact `python = "3.14.6"` mise pin in `shared.toml:32` (mise owns
  the interpreter in this repo; uv download is the fallback path).
- Adoption sketch: a SessionStart/bootstrap step for constrained
  environments = "install uv (single static binary), then
  `uv python install 3.14`" — retires nothing, but un-bricks the
  PreToolUse hook (and with it Bash) in remote/web sessions.

### 2. uv — `uv check` / `uv format` / `uv audit`: real, recent, still churning → WATCH

- **`uv check` (runs ty) added in uv 0.11.18** (~mid-June 2026):
  changelog entry "Add `uv check` to run `ty` from uv"
  (<https://github.com/astral-sh/uv/blob/main/CHANGELOG.md>, fetched
  2026-07-09). 0.11.19 added `--isolated` support; 0.11.22 (2026-06-18)
  added `--script` support and `TY`/`RUFF` env vars "for providing paths
  for binaries used by `uv format` and `uv check`"
  (<https://github.com/astral-sh/uv/releases/tag/0.11.22>).
- **`uv format` (runs ruff format)** has existed experimentally since uv
  0.8.13 (2025-08-21, outside window — pydevtools:
  <https://pydevtools.com/blog/uv-format-code-formatting-comes-to-uv-experimentally/>)
  and is STILL behind the named preview gate `format`
  (<https://docs.astral.sh/uv/concepts/preview/>).
- **`uv audit` shipped as preview** (built out across 0.11.15–0.11.22;
  Astral blog 2026-06-08 "Vulnerability and malware checks in uv",
  <https://astral.sh/blog/uv-audit>): 4-10x faster than pip-audit; opt-in
  OSV malware check via `UV_MALWARE_CHECK=1` (`malware-check` preview
  feature). Blog states both are "considered unstable and there may be
  breaking changes as we iterate on their design."
- There is an open upstream direction to make `uv check` an umbrella
  (`uv check = ty check + ruff check`):
  <https://github.com/astral-sh/uv/issues/19768> — i.e., the surface is
  actively being redesigned.
- **Mapping to repo custom code:** the hk ruff/ruff_format builtins
  (`hk.pkl:55-60`) are *per-staged-file* with fix ordering
  (`ruff check --fix` before `ruff format`, comment `hk.pkl:51-54`), and
  `py_ty` (`hk.pkl:70-77`) needs the explicit
  `--project python python/src tests plugins` path set that the #160 T12
  probe established. `uv check`/`uv format` are whole-project commands and
  currently thinner than what hk provides (no staged-file scoping, no
  fix-ordering dependency graph). They would NOT retire the hk steps
  today; they *could* eventually retire the `ruff`+`ty` entries in the dev
  dependency-group (`pyproject.toml:106-107`) once uv manages those
  binaries itself — but that path is preview and the `TY`/`RUFF` env-var
  escape hatches are days old. Verdict: **watch**, re-check when the
  `format` gate drops and #19768 resolves.
- `uv audit` verdict: **watch/pilot** — it complements (does not replace)
  the async Trivy image scan in `image-analysis.yml`; a
  `uv audit`-in-lint-lane pilot is cheap once it leaves preview.

### 3. uv — 0.11.0 breaking change (TLS): repo unaffected, worth knowing

uv 0.11.0 (2026-03-23) rewired TLS to `rustls-platform-verifier` and
deprecated `--native-tls` in favor of `--system-certs`
(<https://github.com/astral-sh/uv/blob/main/CHANGELOG.md>). Grep of the
repo finds no `native-tls`/`UV_NATIVE_TLS` usage (only `UV_LINK_MODE`,
`UV_CACHE_DIR`, `UV_PROJECT_ENVIRONMENT` — `suites.toml:150-155`,
`Dockerfile:175,398`, `devcontainer.json:120`,
`plugins/dotfiles-build-optimizer/scripts/local_preflight.sh:7`). No
action; note that platform-verifier TLS is what makes the agent-proxy CA
bundle honored system-wide.

Also in-window, lower stakes: relocatable project environments (preview,
0.11.23, 2026-06-23) and centralized environment storage
(`centralized-project-envs` preview, 0.11.25) — potentially interesting
for the devcontainer named-volume `.venvs` layout
(`devcontainer.json:120` already relocates the env via
`UV_PROJECT_ENVIRONMENT`), so the preview largely duplicates what the
repo already does with an env var. Watch only.

### 4. ruff — 0.15.0 "2026 style guide" (2026-02-03): one doc collision, one guard gap

Source: <https://astral.sh/blog/ruff-v0.15.0> (2026-02-03) and
<https://github.com/astral-sh/ruff/releases> (latest **0.15.21,
2026-07-09**; no 0.16/1.0 — ruff remains 0.x with a stable/preview rule
lifecycle; repo lock is one patch behind at 0.15.20).

- **PEP 758 formatter change collides with repo guidance.** On
  `target-version = py314` (exactly what `python/pyproject.toml:21` sets),
  ruff format now REMOVES parentheses around exception tuples:
  `except (A, B, C):` → `except A, B, C:`. The repo's documented trap
  rule says the opposite — "always use `except (A, B):`"
  (`python/AGENTS.md` § "Python 2 comma-except trap", backed by the
  `feedback_python2_comma_except` memory). On Python 3.14 the unparenthesized
  form is *valid multi-catch* (PEP 758), so the safety rationale is
  obsolete on py314 targets, and the formatter will actively rewrite code
  against the doc. Action: reconcile — either update `python/AGENTS.md` +
  memory to "py314 semantics changed; the formatter owns this", or pin the
  old style. Since ruff 0.15.20 is *already* in `uv.lock`, the formatter
  behavior is already live in the lint lane.
- **Block suppressions stabilized — and the `no_lint_skip` grep has a
  spacing gap.** 0.15.0 stabilized `ruff: disable`/`ruff: enable` block
  suppressions plus RUF102/103/104 (suppression-comment validation). Per
  the linter docs (<https://docs.astral.sh/ruff/linter/>, fetched
  2026-07-09), the comment syntax permits "optional whitespace after the
  `#` symbol and `:` symbol" — i.e. `# ruff: ignore[unused-import]`,
  `# ruff: disable[E501]`, `# ruff: file-ignore[…]` (spaced) are all
  valid. The guard at `hk.pkl:98` greps only the space-less forms
  `ruff:ignore\|ruff:file-ignore\|ruff:disable` (the #160 T12.5 additions,
  comment at `hk.pkl:93-97`). A spaced `# ruff: disable[...]` matches NO
  pattern in that grep (file-level `# ruff: noqa` is caught only
  coincidentally via the `noqa` token). **Concrete hardening:** extend the
  grep to `ruff: *ignore`-style patterns (or a single
  `ruff: *\(ignore\|file-ignore\|disable\)` alternation).
- **Human-readable rule names + `--add-ignore` (0.15.18–0.15.21).**
  Suppression comments and selectors can use names (`unused-import`)
  instead of codes (preview), and 0.15.21 (2026-07-09) added
  `ruff check --add-ignore` which bulk-inserts `ruff:ignore` comments
  (<https://github.com/astral-sh/ruff/releases>). Two repo touches:
  (a) `--add-ignore` is a one-command violation of the zero-skip policy —
  worth an explicit mention in `.claude/rules/zero-skip-policy.md`'s
  violation examples once adopted broadly; (b) named selectors could make
  the `pyproject.toml:24-44` ignore list self-documenting (cosmetic,
  preview — watch).
- 0.15.0 stabilized 16 rules (ASYNC212/240/250, RUF102-104, UP042, …);
  with `select = ["ALL"]` (`pyproject.toml:23`) these activated
  automatically at the 0.15.x bump — no config action needed, which is
  the intended behavior of the ALL+documented-ignores design.

### 5. ty — still beta/0.0.x; weekly releases; keep it locked, no retirement

- Version cadence: 0.0.49 (06-12) → 0.0.57 (07-07/08) — roughly weekly
  (<https://github.com/astral-sh/ty/releases>, fetched 2026-07-09). Repo
  lock is at 0.0.56 — current within a week.
- Status: Astral's beta announcement (blog 2025-12-16,
  <https://astral.sh/blog/ty>) says Astral uses ty exclusively internally
  and recommends it "to motivated users for production use", BUT "ty uses
  0.0.x versioning and does not yet have a stable API; breaking changes,
  including changes to diagnostics, may occur between any two versions",
  with Stable targeted for the year after beta (i.e., late 2026). The
  repo's posture — unpinned specifier + uv.lock freeze + deliberate
  `uv lock --upgrade-package` bumps (`pyproject.toml:102-107`) — is
  exactly right for this maturity: every ty bump can add/remove
  diagnostics, and in a zero-skip repo each bump is a mini-migration.
  Keep bump cadence deliberate, not automatic.
- In-window feature relevant to this codebase: **Pydantic support is
  landing now** — 0.0.57 (2026-07-07) "Added detection of model
  configurations and distinction between lax and strict modes"
  (<https://github.com/astral-sh/ty/releases/tag/0.0.57>). `dotfiles_setup`
  is Pydantic/pydantic-settings-based (`pyproject.toml:7-8`), so near-term
  ty bumps may surface NEW diagnostics in `config.py` — expect (and
  budget for) that at the next `uv lock --upgrade-package ty`.
- No evidence found of ty config-discovery changes that would relax the
  `--project python` requirement documented at `pyproject.toml:75-78` and
  `hk.pkl:70-77`; the custom `py_ty` step stays.

### 6. Governance signal: Astral → OpenAI (2026-03-19)

Astral announced an agreement to join OpenAI as part of the Codex team
(<https://astral.sh/blog>, post dated 2026-03-19; corroborated by
third-party coverage). Post-announcement release velocity has NOT dropped
(uv 0.11.x weekly, ruff 0.15.x biweekly, ty weekly through July), and an
"Open source security at Astral" post followed on 2026-04-08. Stability
signal: neutral-to-positive short-term; worth a watch item for license/
governance changes since three of the repo's core toolchain binaries (uv,
ruff, ty) now sit under one corporate owner.

## Retire / adopt / watch table

| Feature | Version (date) | What it touches in-repo | Verdict | Risk | Adoption sketch |
|---|---|---|---|---|---|
| uv auto Python download (`python-downloads=automatic`) + `uv python install --default` | long-stable; `--default` preview | `.claude/settings.json:15` hook bricked in envs without Python 3.14 | **ADOPT** (bootstrap) | low | Remote-session bootstrap: install uv binary → `uv python install 3.14`; hook self-heals. Retires nothing but un-bricks Bash in constrained sessions |
| ruff 2026 style: PEP 758 unparenthesized `except A, B:` on py314 | ruff 0.15.0 (2026-02-03), live in lock | `python/AGENTS.md` comma-except trap doc + `feedback_python2_comma_except` memory | **ADOPT** (doc fix) | low | Update the AGENTS.md trap section + memory: on py314, formatter owns this; trap rationale obsolete |
| ruff spaced suppressions `# ruff: ignore/disable/file-ignore` | stabilized 0.15.0 | `no_lint_skip` grep `hk.pkl:98` misses spaced forms | **ADOPT** (guard hardening) | low | Extend grep alternation to tolerate whitespace after `ruff:` |
| `uv check` (ty runner) | 0.11.18 (~2026-06) | `py_ty` custom step `hk.pkl:77` | **WATCH** | med (surface being redesigned, uv#19768) | Re-evaluate when `uv check` grows ruff + per-path scoping; today it can't express the T12 path set |
| `uv format` | preview gate `format` (since 0.8.13) | hk ruff builtins `hk.pkl:55-60`; dev-group ruff pin | **WATCH** | med (preview) | Revisit when gate drops; could eventually retire dev-group `ruff` entry, not the hk steps |
| `uv audit` (+ `UV_MALWARE_CHECK=1`) | preview, 0.11.15-22 (blog 2026-06-08) | nothing today; complements Trivy in `image-analysis.yml` | **WATCH/PILOT** | low | Add a non-gating `uv audit` lint-lane step once out of preview |
| ruff `--add-ignore` | 0.15.21 (2026-07-09) | zero-skip policy | **REJECT** (note in policy docs) | — | Bulk-suppression is the exact anti-pattern `zero-skip-policy.md` bans |
| ty 1.0 stabilization | targeted late 2026 | `py_ty` step, ty lock bump cadence | **WATCH** | med (diagnostics change between any 0.0.x) | Keep deliberate `uv lock --upgrade-package ty` bumps; expect new Pydantic diagnostics (0.0.57+) |
| uv relocatable/centralized envs | preview 0.11.23/0.11.25 | `UV_PROJECT_ENVIRONMENT` at `devcontainer.json:120` | **WATCH** | low | Repo already relocates via env var; preview may simplify later, no action |

## Uncertainties / gaps

- Could not load the raw ty CHANGELOG (GitHub blob render error; raw URL
  404 through the proxy), so per-version ty details between 0.0.45-0.0.55
  are summarized from the releases index only — a fuller pass should read
  individual release tags before a ty bump.
- The uv CLI reference lists `format`/`check`/`audit` without preview
  banners while the preview-features doc gates `format` and the audit blog
  calls audit unstable — docs internally inconsistent (the known
  docs-lag-code pattern). I trusted changelog + preview-features doc over
  the CLI index.
- `uv format` exact behavior vs the repo's ruff config chain
  (`ruff.toml` extend re-anchoring, `ruff.toml:9-17`) is unverified — if
  ever adopted, probe config resolution first (same class of bug as the
  dead `../tests/*.py` glob).
- Whether ruff's spaced-suppression forms are accepted in *stable* mode or
  only preview mode (`ruff: ignore` is documented as preview; `ruff:
  disable`/`enable` stabilized in 0.15.0) — the guard-gap fix is cheap
  either way, so this doesn't change the recommendation.
- Third-party sources (pydevtools, byteiota) date `uv format` to 0.8.13
  and characterize ty maturity; primary-source confirmation of the 0.8.13
  origin was not found in-window (it predates the window; immaterial to
  verdicts).

## GitHub repos touched

- [astral-sh/uv](https://github.com/astral-sh/uv) — CHANGELOG, releases 0.11.x, preview-features and python-versions docs, issue #19768
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — releases index (0.15.17-0.15.21), v0.15.0 blog, linter/suppression docs
- [astral-sh/ty](https://github.com/astral-sh/ty) — releases index, 0.0.57 release notes, beta announcement blog
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all repo baseline file:line evidence (hk.pkl, pyproject.toml, ruff.toml, shared.toml, uv.lock, settings.json)
