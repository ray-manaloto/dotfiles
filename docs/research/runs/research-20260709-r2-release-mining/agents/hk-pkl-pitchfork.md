# Run D / Angle 2 — hk + pklr + pitchfork release mining (2026-01 → 2026-07)

Date: 2026-07-09. Analyst: release-mining subagent (remote container; Bash
blocked — all evidence via local cache Grep/Read + WebFetch).

Method per `.claude/rules/research-doc-sources.md`: local mintlify cache
first (`docs/research/mintlify-cache/jdx/{hk,pklr,pitchfork}/`, cached
**2026-04-07** per `docs/research/mintlify-catalog.md:4` — 3 months stale,
so every currency claim was re-verified against the GitHub CHANGELOGs and
the live docs site). Note: the cached `www.mintlify.com/jdx/hk/*.md` page
URLs now return **HTTP 410 Gone**; hk's live docs are at
`hk.jdx.dev/*.html` (mintlify preview surface retired — flag for the
cache-refresh workflow).

Repo baseline: hk pinned **1.50.0** (`.config/mise/conf.d/shared.toml:26`),
pkl CLI 0.31.1 (`shared.toml:31`, used only by the hk `pkl` builtin step),
three pkl configs all on `hk@1.50.0` package URLs (hk.pkl:1,8,11;
hk-common.pkl:17-18; hk-image.pkl:11,14). The repo is already on the
newest hk release — this angle is therefore mostly about *confirming
non-retirement* and flagging semantics/stability signals.

## Findings

### 1. hk — releases 1.46.0 (2026-05-27) → 1.50.0 (2026-07-06)

Source: <https://github.com/jdx/hk/blob/main/CHANGELOG.md> (fetched raw,
2026-07-09). Release train in the window:

| Version | Date | Notable |
|---|---|---|
| 1.50.0 | 2026-07-06 | textlint builtin; read string settings from live git config; **share resolved config cache by content** (perf); pre-commit hooks run staged by default on install |
| 1.49.0 | 2026-07-01 | text-only builtin hooks switched from globs to `types = List("text")`; rubocop_server; shellharden builtin; stash preservation fixes |
| 1.48.0 | 2026-06-11 | **inherit step settings from groups**; aqua update-checksum config; `check_diff` for ryl builtins; pklr bumped to 1.0.6 |
| 1.47.0 | 2026-06-09 | **default to pklr backend**; `hk test` config (step `tests{}`); ryl fix/check_list_files; merge-base fallback |
| 1.46.0 | 2026-05-27 | staged-only hook scope; oxfmt/vite-plus builtins; skip local install when hk configured globally |

#### 1a. NO native timeout — the lint.py wrapper survives (load-bearing)

Verified three independent ways on 2026-07-09:

- **Changelog**: zero mentions of "timeout" (any casing) in the entire
  `jdx/hk` CHANGELOG through 1.50.0; no Unreleased section.
- **Live docs**: `https://hk.jdx.dev/configuration.html` — no `timeout`
  property at step, group, hook, or global level; no `HK_TIMEOUT` env var
  documented ("No timeout property exists at any level").
- **Issue search** (`github.com/jdx/hk/issues?q=timeout`): no open/closed
  issue requesting step/run timeout support (matches were unrelated PRs).

→ `python/src/dotfiles_setup/lint.py` (process-group timeout wrapper,
DEFAULT 600s, `DOTFILES_LINT_TIMEOUT`, exit 124, HK_LOG_FILE tail) is
**NOT retired** by any hk release through 1.50.0. Its docstring's claim
("verified against hk 1.46 / v1.48 docs", lint.py:3-5) can be refreshed to
"through 1.50.0". Additional context: `mise.toml:121-127` already layers
mise's **native task `timeout = "700s"`** above the wrapper — decision 15
(#160 T12.5) explicitly evaluated retiring the wrapper in favor of the
native mise timeout and kept it because mise's kill lacks the hk-log-tail
diagnostics. Tool-currency verdict: **keep custom code, justification
already recorded in-repo** (mise.toml:122-126).

#### 1b. hk_version_parity: the "check idea" is ALREADY implemented

`hk.pkl:279-283` (`hk_version_parity`, check-H #160 T12) asserts the three
pkl `hk@X.Y.Z` URLs are identical AND equal the `shared.toml` binary pin;
`min_hk_version = "1.49.0"` (hk.pkl:19) guards binary-too-old. Currently
in parity at 1.50.0 (grep: 8 `hk@1.50.0` occurrences across the 3 pkl
files). Nothing to adopt — the brief's "version-parity check idea" is
shipped. Minor follow-up: bump `min_hk_version` to 1.50.0 opportunistically
if a 1.50-only feature is relied upon.

#### 1c. hk 1.48 group inheritance — WATCH, do not adopt

Live docs (`hk.jdx.dev/configuration.html`): groups can now provide
defaults that child steps inherit — exactly `dir`, `prefix`,
`workspace_indicator`, `shell`, `stage`, `exclude`, with simple override
(not merge) semantics. But groups are also execution barriers: "A group is
a collection of steps that are executed in parallel, waiting for previous
steps/groups to finish and blocking other steps/groups from starting until
it finishes."

Repo mapping: the only inheritable duplication in `hk.pkl` is
`prefix = "uv run --project python"` on 2 steps (ruff, ruff_format;
hk.pkl:55-61 — py_ty/no_lint_skip embed uv in `check` strings instead).
The heavier duplication (`glob` lists on 5 python steps, `batch = true` on
several) is NOT in the inheritable set. Converting the flat `allSteps`
spread (hk.pkl:34-368) into groups to save ~2 lines would **serialize the
currently fully-parallel step set** — a real perf regression on the lint
gate. Verdict: watch (revisit if hk later makes `glob`/`batch` inheritable
without the barrier semantics).

#### 1d. hk 1.47 `hk test` / step `tests{}` — stays DEFERRED, no upstream fix

The repo already probed this: `hk.pkl:361-367` records that `hk test`
"executes test cases IN THE REAL PROJECT DIRECTORY (no sandbox … tests
observed each other's files)", so a violation-case test for `no_lint_skip`
would write a real `noqa` file into `python/src/`. No 1.48-1.50 changelog
entry and no issue found (2026-07-09 search) about sandboxing/tempdir for
`hk test`. Verdict: keep deferred; the retire condition (upstream sandbox)
has not shipped. (Candidate upstream contribution if Ray wants it.)

#### 1e. hk 1.49 `types = List("text")` — inherited for free, behavioral note

1.49 switched the text-only *builtins* (trailing_whitespace, newlines,
mixed_line_ending, etc. — all used via `common.hygiene`,
hk-common.pkl:41-46) from glob patterns to `types = List("text")` with
extension/shebang/content detection. Being on 1.50.0 the repo already
runs this. Behavioral note: coverage can widen to extensionless text files
(content-detected) that the old globs missed — if a future lint run
suddenly flags files it never touched before, this is why, not a repo
regression. `shellcheck` already uses the `types` key (hk.pkl:164).

#### 1f. hk 1.50 perf: content-shared resolved-config cache

"share resolved config cache by content" (1.50.0) extends the
content-hashed pkl-eval cache story (hk 1.47) that already retired the
manual cache-clearing guidance (`ci-local-parity.md` rule 5, retired).
No repo change; confirms the retirement stays valid.

### 2. pklr — 1.0.0 (2026-06-09) → 1.1.3 (2026-07-06): hot semantics-fix cadence

Source: <https://github.com/jdx/pklr/blob/main/CHANGELOG.md> (fetched raw,
2026-07-09). **12 releases in 4 weeks**, essentially all evaluator
semantics fixes: 1.0.0 (skip unused imports), 1.0.2 (explicit union
mapping types), 1.0.3 (string→boolean), 1.0.4 (rewritten package amends),
1.0.5 (import glob matching), 1.0.6 (Mapping annotation value types),
1.1.0 (pkl-pantry package resolution), 1.1.1 (**`&&`/`||`
short-circuiting**, Map/Mapping `filter()`, relative imports against
remote URLs, class identity, lambda declaration order), 1.1.2 (object
methods as complete imports), 1.1.3 (partial imports include sibling
functions).

Repo relevance:

- hk depends on pklr as a **semver range** — `pklr = "1"` in
  `jdx/hk@v1.50.0` Cargo.toml; the hk 1.50.0 **Cargo.lock pins pklr
  1.1.2**. So the embedded evaluator advances with each hk release, and
  pklr 1.1.3's import-completeness fix is NOT yet in any hk release.
- Several 1.1.x fixes are squarely in the repo's usage pattern:
  import/spread of `Mapping<String, Config.Step>` across three files,
  package-URL amends, `(Builtins.x) { … }` overrides. The #160 T12 parity
  probe (pklr backend ≡ pkl CLI, byte-identical `--plan -J`) was run at hk
  1.49 — i.e., against a *different embedded pklr* than 1.50.0 carries.
- Stability signal: boolean-operator short-circuiting being fixed in
  late June (1.1.1) says the evaluator's semantics were still maturing
  weeks ago. Cheap insurance, high value:

**Recommendation (adopt, process-level): re-run the pklr↔pkl parity probe
(`hk config --plan -J` byte-diff vs pkl CLI eval, minus timestamps) as a
standard step of every hk pin bump** — mechanizable as a Renovate
postUpgradeTask note or a checklist line in the hk-bump flow. The pkl CLI
0.31.1 pin (`shared.toml:31`) must therefore stay (it is the parity
oracle + the `pkl` builtin step binary) — do not retire it.

### 3. pitchfork — v1.0.0 (2026-01-19) → v2.16.0 (2026-07-07): cross-reference for Run F

Source: <https://github.com/jdx/pitchfork/blob/main/CHANGELOG.md> (fetched
raw, 2026-07-09). Local cache (2026-04-07) predates everything ≥ v2.5.0.
Pitchfork is **not installed or referenced anywhere in the repo config**
(grep: only mintlify-cache/catalog entries) — everything here is watch/
cross-ref material for Run F's mac automation, not a retirement.

Feature timeline relevant to host-side supervision:

- **v1.0.0-1.3.0 (Jan-Feb)**: daemon dependency resolution, IPC socket
  0600, `ready_cmd` startup validation, `pitchfork.local.toml`,
  `--since <humantime>` logs.
- **v1.5.0 (2026-02-16)**: process-group atomic shutdown, SIGKILL after
  SIGTERM timeout (same kill discipline lint.py implements by hand).
- **v2.0.0 (2026-03-04) BREAKING**: namespaced daemon IDs; port-conflict
  auto-bump.
- **v2.2.0-2.3.0 (Mar)**: `on_stop`/`on_exit` lifecycle hooks; memory/CPU
  limit enforcement.
- **v2.4.0 (2026-04-09)**: **container mode support**; MCP tools (NB: the
  repo's no-MCP-registration rule — any use would go through mcp2cli).
- **v2.8.0-2.10.0 (Apr-May)**: system-level boot-start; macOS boot-start
  fixed to use **LaunchDaemon** (supervisor-level launchd integration;
  per-user `pitchfork boot enable` creates a LaunchAgent plist — cached
  docs, cli/boot page).
- **v2.9.0 (2026-05-03)**: `on_output` hook; customizable stop signals.
- **v2.11.0 (2026-05-17)**: HTTP-status ready checks; daemon grouping.
- **v2.13.0 (2026-06-07)**: log rotation; cron scheduling `immediate`
  startup-behavior config; `pf daemons`/`pf settings` CLI restructure.
- **v2.15.0-2.16.0 (Jul)**: archive hook before log-retention pruning;
  "fire config-only cron daemons without boot_start"; `--grep`/`--regex`
  log filtering.

Run F cross-reference: the devcontainer `initializeCommand` host-side
prerequisites (Doppler download, SSH agent socket plumbing — devcontainer.
json:198, R2 socket chown re-run needed after Docker Desktop restarts) are
the natural candidates for a supervised/scheduled host daemon; pitchfork
now covers launchd registration, cron with immediate-fire control, ready
checks, and lifecycle hooks natively — i.e., anything Run F would
otherwise hand-roll as launchd plists + bash. Stability caveat: one major
breaking release (v2.0.0) inside the window and a ~weekly minor cadence;
pin exact and expect config churn.

### Retire / Adopt / Watch table

| Feature | Version (date) | What it touches in-repo | Verdict | Risk | Adoption sketch |
|---|---|---|---|---|---|
| hk native timeout | **does not exist** through 1.50.0 (2026-07-06) | `python/src/dotfiles_setup/lint.py`, `mise.toml [tasks.lint]` | **KEEP custom** | n/a | Refresh lint.py docstring "verified through 1.50.0"; re-check each hk release |
| hk cross-file version parity | already shipped in-repo | `hk.pkl:279-283` + `min_hk_version` hk.pkl:19 | **DONE** (no action) | — | Bump `min_hk_version` with next feature reliance |
| hk 1.48 group-inherited step settings | 1.48.0 (2026-06-11) | `prefix` dup on 2 ruff steps (hk.pkl:55-61) | **WATCH** | groups = execution barriers → serializes parallel lint | Revisit if glob/batch become inheritable without barriers |
| hk step `tests{}` / `hk test` | 1.47.0 (2026-06-09) | deferred probe note hk.pkl:361-367 | **WATCH** (stay deferred) | writes test files into real tree (no sandbox) | Adopt when upstream sandboxes; candidate upstream PR |
| hk 1.49 `types=text` builtins | 1.49.0 (2026-07-01) | `common.hygiene` steps (hk-common.pkl:41-46) | **inherited free** | coverage may widen to extensionless text files | none — behavioral awareness only |
| hk 1.50 content-shared config cache | 1.50.0 (2026-07-06) | perf of `mise run lint` | **inherited free** | — | none; confirms retired cache-clear guidance stays retired |
| pklr 1.1.x semantics fixes | 1.0.0→1.1.3 (06-09→07-06); hk 1.50 embeds 1.1.2 | 3 pkl configs' import/spread/amends | **ADOPT (process)**: parity probe on every hk bump | evaluator semantics still maturing (12 releases/4 wks) | Add "re-run pklr↔pkl `--plan -J` byte-diff" to hk-bump checklist; keep pkl 0.31.1 pin as oracle |
| pitchfork supervision suite | v1.0.0→v2.16.0 (01-19→07-07) | nothing yet (not installed) | **WATCH → Run F** | v2.0.0 breaking in-window; weekly minors | Supervise host-side initializeCommand prereqs (Doppler env refresh, SSH-sock chown) as launchd-registered pitchfork daemons/cron |

## Uncertainties / gaps

- The hk issues search was rendered through a summarizing fetch; a
  timeout feature request could exist under different wording (e.g.
  "hang", "kill step"). Confidence in "no native timeout" is high anyway
  (docs + changelog are independent confirmations); confidence in "nobody
  has asked upstream" is medium.
- I did not determine which pklr version hk **1.49.0** locked (the version
  the #160 T12 parity probe actually exercised); only 1.48→pklr 1.0.6
  (changelog) and 1.50.0→pklr 1.1.2 (Cargo.lock) are pinned down. The
  recommendation (re-probe per hk bump) is robust to this gap.
- Pitchfork changelog summaries came through a fetch-summarizer; exact
  config-key names (e.g. cron `immediate`) should be re-read from
  `pitchfork.jdx.dev` docs before Run F implements anything.
- Cache staleness: `docs/research/mintlify-cache/jdx/*` is from 2026-04-07
  and the `www.mintlify.com/jdx/hk/*.md` URL surface now returns 410 Gone —
  the cache-refresh workflow needs new source URLs (hk: `hk.jdx.dev`;
  pitchfork llms.txt URL status unverified this session).

## GitHub repos touched

- [jdx/hk](https://github.com/jdx/hk) — CHANGELOG.md, Cargo.toml/Cargo.lock @v1.50.0, issues search, live docs hk.jdx.dev.
- [jdx/pklr](https://github.com/jdx/pklr) — CHANGELOG.md release mining 1.0.0-1.1.3.
- [jdx/pitchfork](https://github.com/jdx/pitchfork) — CHANGELOG.md release mining v1.0.0-v2.16.0; cached mintlify docs (cli/boot).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local working tree reads: hk.pkl, hk-common.pkl, mise.toml, shared.toml, lint.py, mintlify cache/catalog.
