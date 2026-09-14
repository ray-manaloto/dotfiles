# res-release-notes — 2026-09-14 (READ-ONLY)

Answering the operator's question: **did we review all the relevant uv/mise
release notes before concluding on the `update:all` lockfile blocker?** Answer:
**no** — and the miss is not a minor one. The single most load-bearing fact in
this whole incident (the failing mechanism is *hours old, in the exact pinned
release*) was never checked, because both prior lanes (`res-mise-upstream`,
C15-C18) went straight to source-code tracing and the *new* docs page it
shipped with, without ever asking "when did this code land, relative to when
we hit it?"

Pins: mise **2026.9.7** (macOS arm64, released 2026-09-13T23:42:17Z), uv
**0.12.13** (released 2026-09-10T19:27:24Z). All release bodies fetched via
`gh api repos/<owner>/<repo>/releases --paginate` (read-only); no `mise`
mutating commands run, no git/GitHub mutation.

## mise release notes, 2026-07-26 → 2026-09-13 (v2026.7.14 → v2026.9.7)

31 releases in the window. Table covers every one with content bearing on
locking, pypi/pipx, the registry, or tool options — the rest (task graphs,
packslip, bootstrap, Windows/brew fixes) are out of scope and omitted.

| Version | Date | Relevant note | Why it matters here |
|---|---|---|---|
| **v2026.9.7** | 2026-09-13 | **Introduces `mise.lock` revision 2**: "records the full dependency graph of npm tools installed by embedded aube and of `pypi:` tools installed by uv, then replays it with a strict frozen install... Python graph locking requires uv 0.12.10 or newer and published wheels for the target platform; Git sources, standalone pipx installs, and free-form `uvx_args`/`pipx_args` stay version-only." Also: "`pypi:` is now the preferred name for the Python CLI backend; `pipx:` remains fully supported as an alias." (#13131, #13146) | ⭐ **This is our pin.** See "What we missed" below — the whole failing code path (`src/backend/pipx/lock.rs`, the `>=3.8` floor, `--no-build`) was created in the SAME PR, same day, hours before the failure. |
| v2026.9.7 | 2026-09-13 | Fixed: "Installing from a committed `mise.lock` no longer fails when the locked release is younger than `minimum_release_age`... `npm:`/`pypi:` still forward it to unpinned transitive dependencies." (#13128) | A genuine, adoptable fix for a *different* class of `minimum_release_age` friction (reproducing a reviewed lock in CI). Unrelated to the `packslip` 7d-gate removal the operator recalls (that was the general `minimum_release_age` gate for fuzzy/`latest` resolution across all backends, removed 2026-09-10 in THIS repo, not upstream — no upstream note references a "packslip registry flip"; see Contradictions). |
| v2026.8.11 | 2026-08-23 | "Complete lockfile generation for Packslip tools skips platforms with no published artifact..." (#13102, #13105) | Packslip-specific, not pypi/pipx. Confirms "packslip" in mise's changelog is about the `packslip:` backend (a separate, unrelated GA feature from 2026.8.x), not a pipx/pypi registry event. |
| v2026.8.11 (registry, azure-cli) | 2026-08-23 (dated in the 2026.8.11 body, PR merged earlier) | "On Windows x64, `azure-cli` now installs from the official bundled-Python ZIP release instead of PyPI... Linux and macOS continue to use the existing pipx install." (#12161) | The only azure-cli-specific registry note in the window; Windows-only, doesn't touch macOS/Linux pipx path. Not the cause of our azure-cli failure. |
| v2026.8.6 | 2026-08-14 | "**pipx:** discover wheel-only package versions from PEP 503 Simple API indexes, so packages published only as wheels now appear in `mise ls-remote`." (#11959) | Pre-existing wheel-discovery improvement; unrelated to graph *locking* (that didn't exist yet). |
| v2026.8.1 | 2026-08-03 | "adds a per-tool pipx registry option" — `registry_url` (#11754) | Confirms `registry_url` (used in C17's isolated-repro discussion) is a stable, documented per-tool key, not new. |

**Control arm for "no release note before 9.7 mentions pypi/pipx dependency-graph
locking":** grepped the full 1,742-line concatenated body text (v2026.7.14
through v2026.9.6) for `dependency graph`, `uv lock`, `uv_lock`, `wheel`,
`requires-python`, `3.8`. Zero hits tie any of those terms to the pypi/pipx
backend before 2026.9.7 (`3.8` matched once, `armv7 ... libclang 3.8`, an
unrelated toolchain version — confirming the grep discriminates rather than
silently missing a real hit).

## uv release notes, 2026-07-28 → 2026-09-10 (0.11.33 → 0.12.13)

15 releases. None in this window touch `--no-build` semantics, `requires-python`
resolution-floor behavior, or build-isolation defaults for tool installs —
the closest hits are generic lockfile/performance items (`exclude-newer`
handling, indexed lockfile traversal, PEP 751 `pylock.toml` validation), none
of which bear on mise's synthetic `>=3.8` floor or its hardcoded `--no-build`
flag on `uv lock`. **uv 0.12.10** (2026-09-04, the version mise's docs name as
the minimum for graph locking) itself carries no `--no-build`/`requires-python`
content either — its notes are `exclude-newer` bug fixes and a publish-token
enhancement. mise's choice of "0.12.10 or newer" as the floor is not explained
by anything in uv's own changelog; it is presumably an internal mise
compatibility test result, not a uv-side feature gate we can find documented.

**Control arm:** grepped the full 1,455-line uv release corpus for
`no-build`, `no_build`, `requires-python`, `requires_python`, `build isolation`
— matched only unrelated hits (`uv build` + `no-build` interaction for
workspace packages, #21294; PEP 751 hash validation). A freshly-invented
absent term (`zzqvbnotarealterm8271`) returns 0 hits as expected, confirming
the grep is not silently failing.

## ⭐ What did we MISS? (ranked by impact)

1. **The entire failing mechanism was introduced in the exact release we're
   pinned to, hours before we hit it — and nobody checked.** `gh api
   "repos/jdx/mise/commits?path=src/backend/pipx/lock.rs"` returns exactly
   **one commit ever**: `a2db6d3c`, 2026-09-13T20:22:32Z, "feat(lock): store
   Python and npm dependency graphs in native sidecars (#13146)" — the file
   that contains the `>=3.8` floor and the hardcoded `--no-build` flag
   (`lock.rs:186-213`, cited in `res-mise-upstream`'s C15) **did not exist
   before this commit**. The release (v2026.9.7) published at 23:42:17Z the
   same day. `res-mise-upstream` read the brand-new
   `docs/dev-tools/backends/pypi.md` (also created by PR #13146) and treated
   its content as long-standing documented design — technically true (the
   *docs* describe the *intended* design) but it obscured that this is a
   same-day-old feature nobody outside mise's own test suite has exercised at
   scale yet. **This should have changed the recommendation**: filing upstream
   isn't "a reasonable feature request to consider at leisure" (C15's actual
   wording) — it's timely first-adopter feedback on code that shipped hours
   ago, exactly the situation where upstream authors most want a report.

2. **A rollback to mise 2026.9.6 was never considered as an option**, because
   nobody checked when the feature landed. v2026.9.6 (published
   2026-09-12T23:58:09Z, one release/one day earlier) predates PR #13146
   entirely — pinning to it would have avoided the `>=3.8`/`--no-build` failure
   mode altogether, with zero per-tool `uvx = false` workarounds needed, at the
   cost of losing the new lockfile-revision-2 features (which this repo wasn't
   using pypi dependency-graph locking on purpose anyway — it was surfaced as
   a side effect of `lockfile = true`). This is a legitimate lower-risk
   alternative to the three-tool `uvx = false` patch adopted in C18, and it
   was never on the table because "check whether a newer/older mise version
   changes this" (this task's own item 4, and the standing
   `tool-currency-and-native-first.md` rule) was answered only in the "is
   there a newer fix" direction, never the "was there an older, unaffected
   version" direction.

3. **The release-note PROSE overstates graceful degradation; the full docs
   page says something narrower, and that gap is worth naming explicitly.**
   The v2026.9.7 release body says "free-form `uvx_args`/`pipx_args` **stay
   version-only**" — read naturally, that sounds like an automatic, silent
   fallback. The docs page it shipped alongside
   (`docs/dev-tools/backends/pypi.md:104-106`, fetched live) says the accurate
   thing: **"No free-form installer arguments: `uvx_args` and `pipx_args` are
   unsupported with dependency graphs."** — i.e. it's a **hard error**
   ("azure-cli dependency locking does not support uvx_args or pipx_args"),
   not a silent downgrade to version-only. `res-mise-upstream`/C16-C17 hit the
   error and correctly diagnosed the *mechanism* (`uv_lock_allowed` /
   `uvx_disabled()`), but never flagged that the terse release-note summary
   and the full docs disagree on *how gracefully* this degrades. Anyone
   reading only the release note (the cheaper, more likely thing to check)
   would reasonably expect no error at all for a `uvx_args`-carrying tool —
   and would be wrong. Worth a one-line correction if this repo ever cites the
   release note instead of the docs page for this behavior.

4. **`mise lock --bump <tool>`** (new in 2026.9.7, "refreshes a tool's
   transitive graph even when its top-level version is unchanged") is a
   narrower tool than the manual "delete `[[tools.azure-cli]]` from
   `mise.lock`, then `mise run lock -- azure-cli`" surgery C17 performed.
   Untested by this read-only lane, but worth trying next time a lock entry
   needs refreshing without a version bump — it's plausibly the *intended*
   replacement for hand-editing the lockfile, and this session never checked
   whether it existed before reaching for manual TOML surgery. (It would not
   have fixed the azure-cli case specifically, since that tool is rejected
   outright — not stale — but it's the documented tool for the *general*
   class of problem C17's workaround solved by hand.)

5. **No mise release in the window revisits `locked_scopes` or adds a
   documented per-tool `lockfile = false`.** This confirms (rather than
   contradicts) `res-mise-upstream`'s finding that the operator's originally
   proposed config key does not exist — it also never appeared as a *planned*
   feature in any changelog entry, so there's no "coming soon" to wait for.

## Is a newer mise/uv available, and would it change anything?

- **mise 2026.9.7 is the latest release** (verified via `gh api
  repos/jdx/mise/releases` — first row of the paginated, date-sorted list).
  No newer version exists to move to. Nothing in the 2026.9.7 body itself
  suggests a further fix is queued for the `>=3.8` floor — it's presented as
  the intended design, not a known limitation being tracked.
- **uv 0.12.13 is the latest release** (same check against
  `repos/astral-sh/uv/releases`). No newer uv version exists either, and
  nothing in 0.12.10–0.12.13's own notes bears on the floor/`--no-build`
  behavior (that's entirely mise's own synthesis, not something uv's
  changelog would ever mention — uv is just doing what `uv lock --no-build`
  with a `>=3.8` `requires-python` constraint always does).
- **The only version-based lever available is backward**, per item 2 above:
  mise 2026.9.6 lacks the feature. Not recommended over `uvx = false` without
  operator sign-off (it forfeits other 2026.9.7 changes — the
  `minimum_release_age`/lockfile fix, the `history.describe_command` security
  fix, the OCI template-injection closure — for a repo that runs plenty of
  `mise oci build`/history-adjacent tooling), but it should have been
  *presented* as an option, which it wasn't.

## Contradictions with `findings.md` C15–C18 / `res-mise-upstream-2026-09-13.md`

- **No hard contradiction found** — the prior work's technical tracing
  (`uv_lock_allowed`, `resolve_uv_lock`, the `uvx = false` escape hatch, the
  azure-cli registry-carried `uvx_args`) all check out against the live docs
  and match the source-of-truth (`docs/dev-tools/backends/pypi.md`,
  fetched fresh in this lane). The gap is *framing*, not fact: C15 calls the
  `>=3.8`/`--no-build` design "hardcoded, documented behavior" as though it
  were a stable, aged feature reasonable to treat as immovable; it is neither
  aged (one commit, same day) nor necessarily final (it shipped hours before
  anyone outside mise exercised it against a real multi-tool `mise.toml`).
  That framing difference is exactly why the rollback option (item 2 above)
  was never surfaced.
- The operator's recalled "`minimum_release_age` 7d gate removed 2026-09-10
  over a packslip registry flip" does not correspond to any upstream mise
  release note in this window — the only `packslip` + lockfile note
  (v2026.8.11, #13102/#13105) is about the `packslip:` backend's own platform
  coverage, unrelated to pypi/pipx or a registry backend reassignment. If
  that gate removal was a repo-local change (this repo's own
  `minimum_release_age` config), it isn't contradicted by anything upstream;
  it just isn't an upstream event, which is worth confirming with whoever
  made that change since the "registry flip" attribution doesn't have an
  upstream source to point to.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — release bodies v2026.7.14–v2026.9.7
  (`gh api repos/jdx/mise/releases`), commit history for
  `src/backend/pipx/lock.rs` and `src/backend/pipx.rs`, PR #13146 file list,
  and the live `docs/dev-tools/backends/pipx.md` / `pypi.md` pages
  (`raw.githubusercontent.com`) and `e2e/backend/test_pipx_missing_dependency`
  fixture, to verify the release-note prose against the full docs and tests.
- [astral-sh/uv](https://github.com/astral-sh/uv) — release bodies
  0.11.33–0.12.13 (`gh api repos/astral-sh/uv/releases`), searched for
  `--no-build`/`requires-python`/lock-related content in the same window.
