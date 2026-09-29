# Research — CLANG_P2996_REF tracking (2026-09-29)

Research lane (read-only except this report). Issues #1434, #1435. Prior review:
`docs/research/kb/reports/agents/sdlc-team-p2996-ref-currency-2026-09-28.md`.
Branch at start: `fix/s28b-1-p2996-single-literal` (clean), HEAD `8454778c`.

_Status: COMPLETE (2026-09-29). Evidence per question below; raw sources in `.agent/kb/raw/p2996-ref-tracking-*`._

## Recommendations

| # | Question | Answer | Recommendation | Key evidence |
|---|---|---|---|---|
| 1 | mise-native git-ref tracking? | **No.** Only backend-scoped ref installs (cargo/spm/pypi/pipx) of tools mise installs; pipx follows the DEFAULT branch (`purpose`, not `p2996`) | Keep Renovate; mise cannot pin a bake build-arg | mise releases v2026.8.13/#12407, v2026.8.4/#11815; cache `llms-full.txt:1399` |
| 2 | RE2 matchString for bake HCL | `variable "CLANG_P2996_REF"\s*\{\s*default\s*=\s*"(?<currentDigest>[a-f0-9]{40})"` | Replace the current matchString; narrow `managerFilePatterns` to `docker-bake.hcl` | Renovate's own extractor: current regex → **0** deps on bake (reproduces #1434), new → **1** (`7220baff…`); validator rc=0, lookahead canary rc=1 |
| 3 | minimumReleaseAge on git-refs? | **Does not apply** — git-refs emits no `releaseTimestamp`; `timestamp-optional` proceeds immediately | New packageRule after the group rule: `matchDepNames [bloomberg/clang-p2996]`, `groupName: null`, `schedule ["before 6am"]` (preset tz America/Chicago), `automerge`/`pr`/`platformAutomerge` | `git-refs/index.js` `_getReleases`; `lookup/digest.js:21-49`; required check = `ci-gate` only, and bake is in the build path filter so build-publish+smoke cannot skip |
| 4 | Non-bake builds of the Dockerfile? | **None.** 3× `docker/bake-action`, `mise run build/validate`, benchmark script — all bake | Safe to drop the ARG default; update `suites.toml:429` token `ARG CLANG_P2996_REF=` (else `verify` fails) and 3 stale prose sites | `build-publish.yml:238,390,709`; `mise.toml:1294,1306` |
| 5 | `p2996_refresh.py` instead? | Same SHA source, louder on a missing pin, but re-adds a workflow + App token + PR machinery | **Renovate**, plus an extraction-asserting gate; retire or explicitly demote `p2996_refresh.py` (Ray's call) | `p2996_refresh.py:81-145`; `refresh.yml:20-24` |

Side findings: (a) the `github>jdx/renovate-config` preset (fetched live; `.agent/kb/raw/p2996-ref-tracking-jdx-renovate-config-default.json`)
groups every digest update into `non-major dependencies` and sets `timezone: America/Chicago`, `minimumReleaseAge: 7 days`,
`gitIgnoredAuthors: [github-actions[bot]]` — the repo's rules override the first three for this dep; `gitIgnoredAuthors`
is the native knob for the #1063 bot-commit freeze class (adding the refresh App's bot email would let Renovate keep
rebasing the image group) — **unverified, needs its own check**. (b) Post-implementation, run `mise run renovate-dryrun`
(~15 min) to confirm the effective config: one `bloomberg/clang-p2996` digest update, own branch, not in `image-build inputs`.

## Pin sites observed (start of lane)

- `docker-bake.hcl:100-102` — `variable "CLANG_P2996_REF" { default = "7220baffd57ea5b0f8cf59bee494dd5b7cc2b748" }`
- `.devcontainer/Dockerfile:426` — `ARG CLANG_P2996_REF=f349a2d801fbde1f2796dcc003db3d57b3f84515` (differs from bake)
- `renovate.json:124-137` — customManager, matchString `CLANG_P2996_REF["= ]+(?<currentDigest>[a-f0-9]{40})`, git-refs, currentValueTemplate `p2996`

## Q1 — Does mise natively track an arbitrary repo's branch-HEAD SHA? **No.**

Walked the chain: step 0 local cache, then `gh api repos/jdx/mise/releases` (all 641 releases,
through v2026.9.16 — newer than the 2026-08-13 cache). Raw: `.agent/kb/raw/p2996-ref-tracking-mise-native.md`,
`.agent/kb/raw/p2996-ref-tracking-mise-releases.json`. Installed mise: 2026.9.16.

What mise has is **backend-scoped ref installs**, all of which install a *tool* mise manages:

- `ref:<vcs-ref>` version scope — "Compile from a VCS ref" (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:1399`), core plugins only.
- `cargo:<git-url>@branch:/@rev:` (`llms-full.txt:1953-1963`); `spm:` `rev:<commit>` (v2026.8.4, jdx/mise#11815);
  `pypi:` git sources (v2026.9.15, #13607).
- v2026.8.13 (#12407): pipx non-GitHub git `latest` resolves to **the remote default branch HEAD** as a rolling channel.
- v2026.2.22: `mise plugins ls --outdated` compares plugin git refs (plugins only).
- v2026.9.13 (#13544): `mise lock --bump` checks remote versions — for tools in the manifest only.

Why none replaces Renovate here: `CLANG_P2996_REF` is a **BuildKit build-arg consumed by bake**, not a
tool mise installs; no mise backend writes a resolved SHA into `docker-bake.hcl`. And even the pipx
rolling channel follows the *default* branch — clang-p2996's default is `purpose`, not `p2996`
(`gh api repos/bloomberg/clang-p2996 --jq .default_branch` → `purpose`), so it would track the wrong ref.
A `[vars]`/`exec(git ls-remote …)` template could compute HEAD at run time but that is an unpinned,
non-reproducible value (it would also bypass the content-hash that keys the p2996 cache) — not a pin.

Control arm: the same jq filter over 2026 release bodies found the known-present spm `rev:` entry,
and a `lockfile` grep of the same corpus returned 200 lines, so the probe discriminates.

Upstream cadence (informs schedule): p2996 HEAD `f17c8d6c7bfe` @ 2026-09-24; prior commits 09-23, 09-12,
09-08 ×2, 09-03, 09-02, then 08-08 … 06-30 (`7220baff`, the current bake pin). ~1–2 commits/week lately.

## Q2 — Renovate matchString for bake's multi-line block

**Recommended `matchStrings` entry** (JSON-escaped, as it goes in `renovate.json`):

```json
"variable \"CLANG_P2996_REF\"\\s*\\{\\s*default\\s*=\\s*\"(?<currentDigest>[a-f0-9]{40})\""
```

Keep `depNameTemplate`/`packageNameTemplate`/`currentValueTemplate: "p2996"`/`datasourceTemplate: "git-refs"`
unchanged, and narrow `managerFilePatterns` to `/(^|/)docker-bake\\.hcl$/` once the Dockerfile ARG loses its default
(the Dockerfile then holds no SHA to match; leaving it listed is harmless but misleading — it is what let the
current entry look like it covered both files).

**Engine facts (primary source = installed renovate 44.117.1, `mise where npm:renovate`):**

- The regex manager compiles every matchString with flags **`"g"` only** — no `m`, no `s`
  (`dist/modules/manager/custom/regex/strategies.js:9,16,32`). So `.` does NOT cross a newline unless inline `(?s)` is used.
- `dist/util/regex.js:12-14,33` constructs `RE2` (falls back to `RegExp` only if RE2 is unusable — the #644 degradation `renovate_validate.py` canaries).
- Live arms through Renovate's own `regEx()` (ctor reported `RE2`): `a\sb` on `"a\nb"` → **match**; `(?s)a.b` → **match**;
  `a.b` → **no match** (control); `(?=x)` → **THROW** "Invalid regular expression (re2)" (lookahead rejected, as expected);
  `(?<n>x)` named group → match. So `\s` crosses newlines natively and `(?s)` is supported; `\s*` is the simpler choice
  and also tolerates tabs/blank lines.

**Validation method: Renovate's OWN `extractPackageFile` (custom regex manager) imported from the installed dist and run
on the real files** — stronger than python `re` (same engine, same code path), weaker than a full `renovate-dryrun`
(no lookup/update). Script: scratchpad `p2996-regex-probe.mjs`; output copied to `.agent/kb/raw/p2996-ref-tracking-regex-probe-output.md`.

| matchString × file | deps | extracted digest / replaceString |
|---|---:|---|
| CURRENT × `docker-bake.hcl` | **0** | — (reproduces #1434: bake never extracted) |
| CURRENT × `Dockerfile` | 1 | `f349a2d8…`, replace `CLANG_P2996_REF=f349…` |
| CURRENT × Dockerfile with default removed | 0 | — (after Ray's ruling the current entry tracks NOTHING) |
| NEW × `docker-bake.hcl` | **1** | `7220baff…`, value `p2996`, ds `git-refs`, replace spans `variable "CLANG_P2996_REF" {\n  default = "7220…"` |
| NEW × bake with extra spaces/tab/blank line | 1 | same digest |
| NEW × `Dockerfile` (either form) | 0 | — (does not false-match the `CLANG_P2996_REF = CLANG_P2996_REF` arg-forwarding lines either; bake has them at :139/:239 and extraction still yields exactly 1) |
| `(?s)…\{.*?default = "…"` variant × bake | 1 | same — works, but `.*?` could span into a later block if the literal were ever removed; prefer `\s*` |

Arms: the CURRENT regex returning 0 on bake is the negative control (the known defect); NEW returning exactly 1 with
the correct SHA is the positive arm. Config-schema validation (`renovate-config-validator --strict --no-global` on a
patched copy) — see the Q3 section.

## Q3 — git-refs + minimumReleaseAge, and the packageRule

**minimumReleaseAge does NOT apply to git-refs digests — there is no timestamp.**
`dist/modules/datasource/git-refs/index.js` `_getReleases` returns `{version, gitRef, newDigest}` per ref — no
`releaseTimestamp`, no `postprocessRelease` (0 matches in `git-refs/index.js` and `git-refs/base.js`; control arm:
`github-tags/index.js` → 6 matches). Lookup's `getTimestamp` (`process/lookup/index.js:32-37`) therefore returns
nothing, and `applyMinimumReleaseAgeToDigestUpdate` (`process/lookup/digest.js:21-49`) + branch stability
(`update/branch/index.js:288-307`) take the no-timestamp path:

- `timestamp-required` (Renovate's default, `config/options/index.js:2131`) → pending **forever** (stabilityStatus yellow).
- `timestamp-optional` (this repo's global, `renovate.json:9`) → **proceeds immediately** with a warning.

So the global `"minimumReleaseAge": "1 hour"` is a no-op for this dep. The only lever for soak/cost is `schedule`.
Commit dates exist upstream (`gh api repos/bloomberg/clang-p2996/commits/p2996` → `2026-09-24T09:38:11Z`) but
Renovate's git-refs never fetches them. Note `github-tags` is NOT a substitute: its digest path without a value
follows the **default** branch, and clang-p2996's default is `purpose`.

**Why a separate PR matters here:** packageRules[0] (`renovate.json:18-31`) groups by `matchFileNames` including
`.devcontainer/Dockerfile` and `docker-bake.hcl` → `groupName: "image-build inputs"`; that is what put the compiler in
#1063, which froze when `gcc-sha-repair.yml` committed to the branch (prior review §3). The digest auto-merge rule
(`renovate.json:45-54`, `matchUpdateTypes: [minor, patch, digest]` → `automerge/pr/platformAutomerge`) already applies
to this dep. Later packageRules override earlier ones, so a rule appended AFTER both suffices:

```json
{
  "description": "clang-p2996 (#1434/#1435): its OWN daily PR, out of `image-build inputs`. Each bump is a cold ~2h+ p2996 compile (build-publish.yml:292), so a once-a-day window bounds cost; git-refs carries no releaseTimestamp, so minimumReleaseAge cannot soak it (timestamp-optional proceeds, timestamp-required would hold forever) and `schedule` is the only lever. Auto-merge is GitHub-native and waits on the required `ci-gate`, which fails unless build-publish (incl. smoke-test) succeeds — docker-bake.hcl is in ci.yml's build path filter, so build-publish cannot skip for this PR.",
  "matchDatasources": ["git-refs"],
  "matchDepNames": ["bloomberg/clang-p2996"],
  "groupName": null,
  "schedule": ["before 6am"],
  "automerge": true,
  "automergeType": "pr",
  "platformAutomerge": true
}
```

- `groupName: null` is the precedent already in this file (graphify rule, `renovate.json:57-64`) and passes the
  current validator. Alternatively `"groupName": "clang-p2996"` gives a stable branch name `renovate/clang-p2996`.
- The dep name is `bloomberg/clang-p2996` (`depNameTemplate`, `renovate.json:134`) — matched exactly; packageRules[7]'s
  warning about guessed depNames does not bite because this one is templated here.
- "Daily": `schedule` gates branch creation AND updates, so a PR is opened/rebased at most once per day window
  (Mend-hosted runs roughly hourly; confirm the window in the Dependency Dashboard after landing).

**"Auto-merge only after required image/smoke checks" — what enforces it today (verified live):**

- Classic branch protection on `main` requires exactly one context: **`ci-gate`**
  (`gh api repos/ray-manaloto/dotfiles/branches/main/protection` → `contexts: ["ci-gate"]`, strict=false). The ruleset
  `main: require a pull request` (id 19868073) has no status-check rule.
- `ci-gate` (`.github/workflows/ci.yml:360-384`) needs `[lint, contract-preflight, changes, build-publish]` and passes on
  `success|skipped`. ⚠️ A SKIPPED build-publish would satisfy it — but `docker-bake.hcl` is in the `changes` build filter
  (`ci.yml:297`), so build-publish runs (`ci.yml:339`) and its result reflects `smoke-test` (`build-publish.yml:807`).
- ⚠️ Every build-publish leg has `continue-on-error: ${{ !matrix.target.blocking }}` (`build-publish.yml:148,286,442,554,837,1095`):
  only the **blocking** (amd64) leg gates; the arm64 runner-validation leg does not. That is the existing policy (#840), not new.
- With `platformAutomerge: true` GitHub merges when required checks pass, so the gate is exactly `ci-gate`. If Ray wants
  smoke NAMED rather than transitively via ci-gate, that is a branch-protection change, not a Renovate one.

### Config validation of the proposed patch (renovate-config-validator 44.117.1, `--strict --no-global`)

Patched a scratch COPY of `renovate.json` (customManagers[2] matchString + `managerFilePatterns: ["/(^|/)docker-bake\\.hcl$/"]`,
plus the packageRule above appended). Results:

| Config | rc | Output |
|---|---:|---|
| repo `renovate.json` (unchanged, baseline) | 0 | "Config validated successfully" |
| proposed patch | **0** | "Config validated successfully" |
| canary: same patch with `(?=x)` injected into the clang matchString | **1** | `Invalid regExp for customManagers: …(?=x)…` |

The canary failing proves the validator is running on RE2 (the #644 degradation would have passed it), so the rc=0
on the patch is meaningful.

## Q4 — Does anything build `.devcontainer/Dockerfile` WITHOUT bake? **No.**

Grep over `.github/workflows/*.yml`, `.github/actions/*/action.yml`, `mise.toml`, `python/src`, `scripts/`,
`.devcontainer/scripts/`, `.devcontainer/devcontainer.json` for `docker build`, `buildx build`, `bake`,
`build-push-action`, `Dockerfile`. Every entry point:

| Entry point | Builds | Via bake? |
|---|---|---|
| `build-publish.yml:238` (base), `:390` (p2996-cache), `:709` (dev) | `.devcontainer/Dockerfile` targets | **yes** — `docker/bake-action@018cb641 # v7.4.0` |
| `mise.toml:1292-1294` `[tasks.build]` | `docker buildx bake dev-load` | yes (and CI-only per do-not #2) |
| `mise.toml:1304-1306` `[tasks.validate]` | `docker buildx bake validate` → `docker-bake.hcl:265-268` (`inherits dev`, `call = "check"`) | yes — bake supplies the arg |
| `scripts/benchmark-docker.sh:63,68` | `docker buildx bake dev-load` | yes |
| `.devcontainer/devcontainer.json:92` + `python/src/dotfiles_setup/docker.py:344-355` (`devcontainer build`) | `Dockerfile.host-user` (thin overlay, `FROM ${BASE_IMAGE}`) | n/a — different file, no `CLANG_P2996_REF` |
| `python/src/dotfiles_setup/sync.py:696-712` | `docker buildx build --pull … -` with stdin `FROM <image_ref>` | n/a — a pull-by-build of the published image, not this Dockerfile |
| `sync.py:456`, `image.py:1285`, `image_manifest.py:128`, `image_promote.py`, `ci.yml:479-580`, `build-publish.yml:263…1301` | `docker buildx imagetools inspect/create` | n/a — registry metadata only |

No `docker/build-push-action`, no raw `docker build` of `.devcontainer/Dockerfile` anywhere. Control arm: the same
grep found all three `docker/bake-action` sites and the `buildx build` in `sync.py`, so it sees build calls.

**Consequences of dropping the ARG default** (things that DO read the Dockerfile literal):

- `python/verification/suites.toml:420-431` `build.clang-p2996-reflection` requires the token **`ARG CLANG_P2996_REF=`** in
  the Dockerfile. `ARG CLANG_P2996_REF` (no default) does NOT contain it → `mise run verify` fails. That token must
  change (e.g. to `ARG CLANG_P2996_REF\n` as a contiguous multi-line token, or `ARG CLANG_P2996_REF` + a forbid of
  `ARG CLANG_P2996_REF=`), which is also the natural single-literal guard.
- Failure mode without bake is loud, not silent: `Dockerfile:465` `git fetch --depth 1 origin "${CLANG_P2996_REF}"`
  with an empty value fails the RUN. Optionally add `test -n "${CLANG_P2996_REF}"` for a clear message (build-time
  self-check pattern).
- `p2996_hash.py:439`, `image.py:96-100,2081-2085`, `p2996_refresh.py:126-128` already read the **bake** value (or the
  Phase-D env override) — unaffected.
- Tests that fabricate bake text (`tests/test_p2996_hash.py:95,529`, `tests/test_image_promote.py:89`) use the one-line
  form `variable "CLANG_P2996_REF" { default = "abc123" }`; the proposed matchString handles that form too (`\s*` around braces).
- **Stale prose to fix in the same change** (tool-currency rule 5): `Dockerfile:421-425` ("the git-refs Renovate manager
  rewrites BOTH files in lockstep"), `mise.toml:1467` (`p2996-refresh` "the scheduled refresh.yml workflow's p2996-refresh
  job does this in CI" — retired in #169, `352063a5`), `.devcontainer/P2996-CACHE.md:91,112,140` (auto-bump via refresh.yml).
  `refresh.yml:20-24` already records the #1434 correction.

## Q5 — `p2996_refresh.py` vs Renovate for the daily PR (recommendation only)

| Axis | Renovate git-refs (fixed regex) | `p2996_refresh.py` (+ a re-added scheduled job) |
|---|---|---|
| SHA source | `git ls-remote` via git-refs datasource (`getDigest` → ref `p2996` hash) | `git ls-remote … refs/heads/p2996` (`p2996_refresh.py:81-94`) — identical source |
| SHA validation | 40-hex enforced by the matchString capture | `_validate_sha` 40-char lowercase hex (`:67-78`) |
| Missing-pin behaviour | **silent** — zero extraction logs at debug only (the #1434 failure) | **loud** — `replace_pinned_ref` raises unless exactly one match (`:131-145`) |
| PR lifecycle | native: branch, rebase, dashboard, schedule, `platformAutomerge` | must re-add a refresh.yml job + App-token mint + `peter-evans/create-pull-request` + auto-merge arming (what #169 deleted) |
| Bot-commit freeze risk (#1063) | low once separate: the PR touches only `docker-bake.hcl`; `gcc-sha-repair.yml:20-24` triggers only on Dockerfile paths and commits only on drift (`:84`); `image-lock-pr` exits 0 with no lock drift | n/a (own branch) |
| Maintenance | ~15 lines of JSON; Renovate version churn is already paid | 169 lines of python + tests + a workflow job + secrets wiring |
| Rule fit | `use-tool-builtins` / `tool-currency-and-native-first` favour the native path | custom machinery for what the tool does natively |

**Recommendation: Renovate.** Its one real weakness is the silent zero-extraction — exactly what hid #1434 — so close
that with a gate that asserts **extraction**, not a symptom: e.g. a test that runs Renovate's own
`extractPackageFile` (as this lane's probe did, <1 s) on `docker-bake.hcl` and requires exactly one
`bloomberg/clang-p2996` dep with the pinned digest, or registering the bake site in `pin-parity.toml` (prior review §2).
`p2996_refresh.py` is then superseded: per tool-currency rule 3, either retire it (and its task, CLI subcommand and
tests) or keep it explicitly as a manual/emergency bump with its stale `mise.toml:1467` description corrected — Ray's
call; it should not be re-wired to a schedule alongside Renovate (two writers of one pin).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — all 641 release notes via `gh api` + cached docs; native git-ref tracking check (Q1)
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — default branch (`purpose`), `p2996` HEAD and commit dates (Q1/Q3)
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — installed dist 44.117.1 source (regex manager, RE2, git-refs, minimumReleaseAge) (Q2/Q3)
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — `default.json` preset this repo extends (Q3 side finding)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — branch protection / rulesets on `main` (Q3)
