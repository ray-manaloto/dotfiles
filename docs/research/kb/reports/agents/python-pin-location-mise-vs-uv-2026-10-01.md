# Where should the Python version pin live: mise core:python vs uv (requires-python / .python-version)?

Synthesis node of the `python-pin-location-mise-vs-uv-2026-10-01` research sweep. Date: 2026-10-01.
Branch at time of writing: `fix/s29-00-image-input-pins`, which already carries an uncommitted
`renovate.json` package rule isolating the python bump (S29-00, #1449).

## Answer

**Keep the exact pin in mise `core:python` (`.config/mise/conf.d/shared.toml:49`, `python = "3.14.7"`). Keep
`requires-python` in `python/pyproject.toml` as a floor range (`>=3.14`). Do not add a `.python-version`.** One
more step is needed, because a live probe found a gap the question did not anticipate: **on the host today, uv
does NOT use mise's interpreter.** `uv python find --project python` returns uv's own managed CPython **3.14.0**,
and `python/.venv` runs on it, while `mise where python` is 3.14.7. The mise pin governs the shell and the image,
but not the uv project venv. That happens because of uv's default `python-preference = "managed"`. Closing it
means pointing uv at mise's interpreter, for example with `python-preference = "only-system"` (detail under
Recommendation).

The sub-questions:

- **Files each tool reads.**
  - **mise** reads `mise.toml` and conf.d fragments.
  - It reads `.python-version` / `.python-versions` **only after opt-in**: `idiomatic_version_file_enable_tools`
    must include `python`. If both declare a version, `mise.toml` wins.
  - **uv** reads `.python-version` in the cwd, then in each parent, then in the user config directory. It also
    reads `requires-python` from `pyproject.toml`, but only as a *range*: "the first compatible" interpreter
    wins unless `.python-version` or `--python` overrides it.
  - **Renovate's mise manager** matches `**/.config/mise/conf.d/*.toml` and extracts `[tools]` and
    `tasks.*.tools`. It reads `mise.lock` for `lockedVersion`.
  - **Renovate's pep621 manager**, per its docs as surfaced by the exa search (that page was *not* mirrored),
    matches `pyproject.toml` and has a `requires-python` depType. **It does not run in this repo:** `pep621` is
    absent from `renovate.json` `enabledManagers` (`renovate.json:243-252`).
- **Can mise delegate Python installs to uv?** Nothing read shows that it does. mise uses uv for **venv creation**
  (`_.python.venv`) and for **sourcing a uv venv** (`python.uv_venv_auto`). It also uses uv for **PyPI-tool
  dependency sidecars** (PR #13146). Interpreter installs come from python-build-standalone (PBS). When
  `python.compile` is set or no build exists for the platform, they come from python-build instead. The absence
  of uv-backed interpreter installs is **not confirmed** by a source read; see Gaps.
- **PBS release lag.** Both options share the same upstream: uv documents that it uses PBS and names mise as
  another PBS consumer. **CPython `v3.14.8` exists upstream (tagged 2026-09-30), and none of PBS's four most
  recent releases (20260825 through 20260929) has a 3.14.8 asset.** This was measured today, with control arms.
  **Qualification (adjudicated): this is NOT evidence of lag.** Every one of those releases was published on or
  before 2026-09-29, before the `v3.14.8` tag existed, so none could have contained it. PBS PR #1308
  ("CPython 3.14.7 -> 3.14.8") merged 2026-10-01T13:50Z, so a release with 3.14.8 is probably imminent. The
  absence is point-in-time and may be stale within hours; actual lag is under about one day.
  - Under **mise**, `mise lock` refuses an unbuilt version. That is why Renovate's artifact step failed in #1449.
  - Under **uv**, a second layer of lag is added: "available Python versions are frozen for each uv release".
  - Under either option, a *range* pin (`>=3.14`) never blocks on lag, while an *exact* pin does. A bump that
    lands before PBS publishes the build can fail (as #1449 did), so isolating the exact-pin bump, which the
    branch already does, is sensible. It does not argue for moving the pin. (The 3.14.8 gap measured here is
    a under-one-day tag-to-asset window, not a demonstrated multi-release lag; see Verification.)
- **Lockfiles.**
  - `mise.lock` pins the **interpreter artifact**: per-platform PBS URL, sha256 and provenance
    (`.config/mise/mise.lock:742-779`, release `20260924`).
  - `uv.lock` pins **packages only** and records `requires-python = ">=3.14"` (`python/uv.lock:3`). It does not
    pin an interpreter.
  - mise's newer `.mise/locks/<tool>/<ver>/{pyproject.toml,uv.lock}` sidecars apply to **`pypi:` tools**, not to
    the `core:python` interpreter.

No MANDATORY GAPS were supplied to this node, so the sweep is not flagged INCOMPLETE. Several individual sources
did fail or come back unverified; they are listed under Gaps.

## Evidence

Each row says whether it records what a project **SHIPS** (code, lockfile or shipped docs), what it
**PROPOSES** (an issue or discussion), or what a **THIRD PARTY** documents.

| claim | URL or file:line | quote |
|---|---|---|
| SHIPS (docs): mise installs PBS precompiled binaries by default | https://mise.jdx.dev/lang/python.html (mirror `links/1.md:257`) | "By default, mise downloads [precompiled binaries](https://github.com/astral-sh/python-build-standalone) for python instead of compiling them with python-build." |
| SHIPS (docs): `python.compile` unset means precompiled when available "for the current platform", otherwise compile | `links/1.md:325-327` | "[undefined] - use precompiled binary if one is available for the current platform, compile otherwise." |
| SHIPS (docs): `.python-version` is opt-in for mise | `links/1.md:74,79` | "`.python-version`/`.python-versions` files are supported after you enable discovery:" … `mise settings add idiomatic_version_file_enable_tools python` |
| SHIPS (docs): use one authoritative source; `mise.toml` wins on conflict | `links/1.md:82` | "Keep one authoritative project version source. A conflicting Python declaration in `mise.toml` takes precedence over an idiomatic file." |
| SHIPS (docs): mise uses uv to create venvs, not to install interpreters | `links/1.md:196` | "If you have installed `uv` … `mise` will use it to create virtual environments via `_.python.venv`." |
| SHIPS (docs): `uv_venv_auto` keys off `uv.lock` | `links/1.md:93` | "mise locates the uv project by walking up for a `uv.lock` file, so a `uv.lock` must be present — without one the setting does nothing." |
| SHIPS (docs): legacy `uv_venv_auto = true` exports a bare-version `UV_PYTHON`, which does not bind the interpreter | `links/1.md:204` | "does not guarantee that `uv` uses the specific interpreter managed by `mise` — `uv` may fall back to a system or self-managed Python of the same version." |
| REPO: the image uses the string form, so no `UV_PYTHON` is exported there | `.devcontainer/mise-system.toml:352` | `python.uv_venv_auto = "source"` |
| SHIPS (docs): uv reads `.python-version` upward, then from the user config dir | https://docs.astral.sh/uv/concepts/python-versions (`links/2.md:58-61`) | "uv searches for a `.python-version` file in the working directory and each of its parents. If none is found, uv will check the user-level configuration directory." |
| SHIPS (docs): `requires-python` is a range, and the first compatible interpreter wins | `links/2.md:216-219` | "The first Python version that is compatible with the requirement will be used, unless a version is otherwise requested, e.g., via a `.python-version` file or the `--python` flag." |
| SHIPS (docs): uv's default preference is managed over system | `links/2.md:409-411` | "By default, the `python-preference` is set to `managed` which prefers managed Python installations over system Python installations." |
| SHIPS (docs): uv's Python list is frozen per uv release | `links/2.md:123-124` | "The available Python versions are frozen for each uv release. To install new Python versions, you may need upgrade uv." |
| SHIPS (docs): uv uses PBS and names mise as a co-consumer | `links/2.md:449-453` | "uv instead uses pre-built distributions from the Astral [`python-build-standalone`] project … also is used in many other Python projects, like [Mise]" |
| SHIPS (docs): uv auto-downloads by default | `links/2.md:52` | "By default, uv will automatically download Python versions if they cannot be found on the system." |
| **MEASURED (this node)**: the host uv project resolves to uv-managed 3.14.0, not mise 3.14.7 | `uv python find --project python` rc=0 (uv 0.12.13) | `/Users/rmanaloto/.local/share/uv/python/cpython-3.14-macos-aarch64-none/bin/python3.14`. Second route: `python/.venv/pyvenv.cfg` `home = …/uv/python/cpython-3.14-…`; the venv python reports `3.14.0`. Control arm: `uv python list --only-installed` lists mise's `…/mise/installs/python/3.14.7/bin/python3.14`, so uv *can see* mise's build and passes it over. `mise where python` returns `…/installs/python/3.14.7`. `UV_PYTHON` and `UV_PYTHON_PREFERENCE` are both ABSENT. |
| **MEASURED (this node)**: CPython 3.14.8 is tagged upstream | `git ls-remote --tags https://github.com/python/cpython` rc=0 | `refs/tags/v3.14.8` present, `v3.14.7` present (control), `v3.14.99` absent (negative control) |
| **MEASURED (this node)**: PBS has no 3.14.8 asset in its four latest releases | `gh api repos/astral-sh/python-build-standalone/releases?per_page=4` rc=0 | `20260929 n314_8=0 n314_7=195`; `20260924 n314_8=0 n314_7=195`; `20260901 n314_8=0 n314_7=189`; `20260825 n314_8=0 n314_7=189`. The bogus `3.14.99` pattern returns 0 everywhere. **Qualified:** all four releases predate the `v3.14.8` tag (2026-09-30T17:55Z), so the zeros are expected, not lag; PBS PR #1308 bumping to 3.14.8 merged 2026-10-01. |
| REPO: the exact pin lives in the shared fragment | `.config/mise/conf.d/shared.toml:49` | `python = "3.14.7"` |
| REPO: `mise.lock` pins the PBS artifact per platform | `.config/mise/mise.lock:742-748` | `version = "3.14.7"`, `backend = "core:python"`, `url = ".../releases/download/20260924/cpython-3.14.7+20260924-aarch64-unknown-linux-gnu-install_only_stripped.tar.gz"`, `provenance = "github-attestations"` |
| REPO: `requires-python` is a floor, and `uv.lock` mirrors it | `python/pyproject.toml:5`; `python/uv.lock:3` | `requires-python = ">=3.14"` (both) |
| REPO: no `.python-version` exists | `ls .python-version python/.python-version` | "No such file or directory" for both. Control: the same `ls` found the mirror files. |
| REPO: Renovate's pep621 manager is not enabled | `renovate.json:243-252` | `"enabledManagers": ["npm","cargo","mise","dockerfile","docker-compose","devcontainer","github-actions","custom.regex"]` |
| REPO (working tree, uncommitted): #1449's failure mode, and the isolation rule | `renovate.json:117` | "#1449 bumped python 3.14.7 -> 3.14.8 before any standalone 3.14.8 existed, Renovate's artifact step then failed (`failed to resolve python@3.14.8 ... refusing to replace locked version(s) 3.14.7`)" |
| SHIPS (docs): Renovate's mise manager matches conf.d fragments | https://docs.renovatebot.com/modules/manager/mise (`links/3.md:20`) | `**/.config/mise/conf.d/*.toml` |
| SHIPS (docs): Renovate extracts `[tools]` and `tasks.*.tools` | `links/3.md:82` | "Renovate supports top level [`tools`] and [`tasks.*.tools`] keys." |
| SHIPS (docs): concrete pins follow normal source-file updates; fuzzy selectors resolve against the lock | `links/3.md:148-154` | "Concrete versions such as `25.0.3` retain Renovate's normal source-file update behavior" |
| SHIPS (docs): mise lock refresh is an unsafe execution and needs an existing `mise.lock` | `links/3.md:183,199` | "Renovate treats mise lockfile refreshes as an unsafe execution." … "an existing `mise.lock` is required" |
| SHIPS (docs): only the first version of a multi-version tool is updated | `links/3.md:204` | "designed to automatically update the _first_ (primary) version listed for each tool" |
| SHIPS (docs): the Renovate registry table lists core python | `links/3.md:1104` | "\| [`python`](https://mise.jdx.dev/lang/python.html) \| mise \| ✅ \|" |
| SHIPS (docs, not mirrored, exa hit only): the pep621 manager has a `requires-python` depType and matches `pyproject.toml` | https://docs.renovatebot.com/modules/manager/pep621/ | "`requires-python` \| The `requires-python` constraint from `[project]`" |
| SHIPS (merged PR): mise lock now preserves the recorded PBS release instead of re-resolving to the newest one | https://github.com/jdx/mise/pull/11747 | "preserve the python-build-standalone release already recorded for each locked platform" |
| PROPOSES (discussion, motivating #11747): PBS re-dates the same CPython, which churns `mise.lock` | https://github.com/jdx/mise/discussions/11743 | "PBS periodically republishes the same CPython version under a new date tag, this rewrites every [tools.python.\"platforms.*\"] URL and checksum in mise.lock" |
| SHIPS (merged PR): PyPI-tool dependency sidecars use `uv.lock` | https://github.com/jdx/mise/pull/13146 | "`.mise/locks/pypi-black/24.10.0/{pyproject.toml,uv.lock}`" |
| SHIPS (fix): `.python-version` containing `system` | https://github.com/jdx/mise/issues/13132 | "A `.python-version` containing `system` now continues to select the system Python without printing the deprecation warning." |
| SHIPS (fix): `uv_venv_auto` honours `UV_PROJECT_ENVIRONMENT` | https://github.com/jdx/mise/pull/11475 | "respect UV_PROJECT_ENVIRONMENT when python.uv_venv_auto selects, creates, and activates a uv virtual environment" |
| THIRD PARTY (user in a uv issue): mise users force uv onto system Python | https://github.com/astral-sh/uv/issues/17253 | "`python-downloads = 'never'`, `python-preference = 'only-system'`" |
| PROPOSES (open uv issue): uv should read `.tool-versions` | https://github.com/astral-sh/uv/issues/6574 | "It'd be nice if uv supported that." |
| PROPOSES (mise discussion): mise should read `[tool.uv] required-version` | https://github.com/jdx/mise/discussions/12991 | "I'd like mise to read required-version from [tool.uv] in pyproject.toml" |
| SHIPS (uv docs, exa hit, not mirrored): Renovate can maintain `uv.lock` | https://docs.astral.sh/uv/guides/integration/renovate/ | "lockFileMaintenance: { enabled: true }" |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `idiomatic_version_file_enable_tools filename:mise.toml` | query | planner | 880 | 0 |
| `repo:jdx/mise path:src/plugins/core filename:python.rs` | query | planner | 1 | 0 |
| `repo:jdx/mise filename:README.md` | must-hit | planner | 19 | 0 |
| `qzvxkplwmrt9fnord` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:jdx/mise filename:README.md` | must-hit | workflow | 19 | 0 |
| `repo:astral-sh/uv filename:README.md` | must-hit | workflow | 79 | 0 |
| `repo:astral-sh/python-build-standalone filename:README.md` | must-hit | workflow | 1 | 0 |
| `repo:renovatebot/renovate filename:README.md` | must-hit | workflow | 248 | 0 |

No row was rate-limited. The must-hit rows were non-zero and the known-absent row was 0, so the search
discriminates. No CODE SEARCH NOTES were supplied. Note: the one `python.rs` hit was **located but not read**,
so the core-plugin source behind the "mise does not install via uv" and lag-fallback questions is still unread
(see Gaps).

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| jdx/mise | python uv pin | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/python-pin-location-mise-vs-uv-2026-10-01/deps/jdx--mise/1/manifest.json` |
| jdx/mise | uv | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/python-pin-location-mise-vs-uv-2026-10-01/deps/jdx--mise/2/manifest.json` |
| jdx/mise | python-build-standalone | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/python-pin-location-mise-vs-uv-2026-10-01/deps/jdx--mise/3/manifest.json` |
| jdx/mise | renovate | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/python-pin-location-mise-vs-uv-2026-10-01/deps/jdx--mise/4/manifest.json` |
| astral-sh/uv | mise | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/python-pin-location-mise-vs-uv-2026-10-01/deps/astral-sh--uv/1/manifest.json` |
| astral-sh/python-build-standalone | mise | 0 | `.agent/kb/raw/research-fanout/python-pin-location-mise-vs-uv-2026-10-01/deps/astral-sh--python-build-standalone/1/manifest.json` |
| renovatebot/renovate | mise | 0 | `.agent/kb/raw/research-fanout/python-pin-location-mise-vs-uv-2026-10-01/deps/renovatebot--renovate/1/manifest.json` |

Each run returned rc 0, but some *sources* inside these runs did not answer; those are listed under Gaps. The
topic-level manifests read alongside these were `research-fanout/mise-python-uv-python-version-idiomatic-version-file-python/manifest.json`
and `research-fanout/renovate-mise-manager-python-pep621-requires-python-python-b/manifest.json`.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://mise.jdx.dev/lang/python.html | `docs/research/kb/raw/python-pin-location-mise-vs-uv-2026-10-01/links/1.md` | 0 | 18199 | — |
| https://docs.astral.sh/uv/concepts/python-versions | `docs/research/kb/raw/python-pin-location-mise-vs-uv-2026-10-01/links/2.md` | 0 | 21631 | — |
| https://docs.renovatebot.com/modules/manager/mise | `docs/research/kb/raw/python-pin-location-mise-vs-uv-2026-10-01/links/3.md` | 0 | 97528 | — |

All three caller links are cited above.

## Conflicts resolved

1. **The input claim "No evidence PBS has released 3.14.8 *or any 3.14.x*" is wrong in its second half.** It was
   sourced from the mise releases page, which is the wrong subsystem for PBS release contents. This repo's lock
   pins `cpython-3.14.7+20260924` from PBS (`mise.lock:748`), and PBS issue #1293 cites
   `cpython-3.14.7%2B20260825`. My `gh api` probe over the four latest PBS releases settles it: 3.14.7 is
   present (189–195 assets per release) and 3.14.8 is absent (0). I trusted the primary artifact (release
   assets) over a secondary page.
2. **"mise reads `.python-version`"** (issue #4178, phrased as unconditional) **vs "after you enable discovery"**
   (current docs). I trusted the current shipped docs (`links/1.md:74`). The issue text is older, and the docs
   were updated by #12864 (2026-09-06) to document the opt-in. Treat `.python-version` as opt-in for mise.
3. **Sidecar path: `.mise/locks/pipx-black/…` (#13141) vs `.mise/locks/pypi-black/…` (#13146).** I trusted
   #13146, which is the later PR (16:21Z vs 13:12Z the same day). The input claims also blur scope: these
   sidecars cover **PyPI tool dependency graphs**. They do not lock the `core:python` interpreter, which stays
   in `mise.lock`'s `[tools.python."platforms.*"]` URL and checksum entries.
4. **"Renovate's mise manager supports the pypi datasource, and python has a registry mapping."** These are two
   separate facts. The pypi datasource is in the manager's datasource list (`links/3.md:28`), but that list is
   for `pypi:` tools. The registry table row (`links/3.md:1104`) shows that core python is *supported*, but not
   *which datasource* it queries. Which one Renovate uses for `core:python` is therefore a gap. The #1449
   evidence (`renovate.json:117`) shows that whatever it queries offered 3.14.8, which PBS did not have.
5. **PBS lock churn, discussion #11743 vs PR #11747.** The discussion describes the churn; the merged PR fixes
   it. I trusted the merged PR, since the shipped behaviour is that the recorded PBS release is preserved.
   Rollout to the mise version this repo pins is **unverified** (see Gaps).
6. **"uv honours `requires-python`" vs the measured host behaviour.** These are consistent: the docs say the
   "first compatible" interpreter is used, ordered by `python-preference = managed`, and the managed 3.14.0
   satisfies `>=3.14`. The surprise is not a documentation conflict. The mise pin was never an input to uv's
   selection.

## Gaps

These are unknowns, not "nothing found".

- **The context7 source failed** (`mise-python-uv context7`: `exited 1`). Its content is unknown.
- **The PBS github-releases source failed** in the fan-out (`exited 1: gh: We couldn't respond to your request in
  time`). The resulting lag gap was **partially closed by this node's own probe** (four latest releases, armed).
  Lag *duration* (how many days PBS typically trails a CPython tag) was not measured.
- **`astral-sh/uv` github-discussions returned `empty_unverified`.** The canary returned 0 items, so the probe
  could not discriminate. What uv discussions say about mise interop is unknown.
- **`mise-python-uv` github-issues and github-discussions were `empty_verified` with 0 items** for the exact
  query. The probe works (control `mise` returned 10), but the exact phrasing found nothing. That is not
  evidence of absence.
- **No source read confirms that mise never installs interpreters via uv.** The docs mention uv only for venvs
  and sidecars. `src/plugins/core/python.rs` was located by code search but not read.
- **mise's behaviour when an exact pin has no PBS build and `python.compile` is unset is unconfirmed.** The doc
  says "available for the current platform", which is ambiguous between per-platform and per-version. #1449
  shows that `mise lock` fails rather than falling back. Whether `mise install` falls back to python-build was
  not tested.
- **Which Renovate datasource the mise manager queries for `core:python`** is not stated in the mirrored page,
  and whether it checks PBS availability is unknown.
- **The Renovate pep621 manager page** was surfaced by exa but not mirrored or read in full. The issues and
  discussions on extracting python and updating `requires-python` (#35534, #35488, #34793) were triaged but
  not read. Each is a PROPOSAL, not shipped behaviour.
- **How this repo's `python/uv.lock` gets Renovate lockFileMaintenance while `pep621` is absent from
  `enabledManagers`** (`renovate.json:66` claims lockFileMaintenance re-resolves it) was not checked.
- **The image-side uv interpreter choice was not probed.** Whether the devcontainer has a uv-managed CPython that
  would win over mise's, as it does on the host, is unknown. No container was started.
- **Whether mise PR #11747 (preserve the locked PBS release) is in the pinned mise version** (2026.9.8 per
  `findings.md`, an inherited and unverified figure) was not checked.

### Critic gaps (appended by the reconcile node)

- **Core claim that mise never delegates interpreter installs to uv is unverified.** `src/plugins/core/python.rs`
  was located but never read; the claim rests on docs silence. Next probe: read `python.rs` at the pinned tag
  (grep uv / python-preference / install paths), test `mise install python@<ver>` with uv present and
  `python.compile` unset, and check mise settings docs for a uv-install option.
- **Whether `mise install` falls back to python-build (compile) when the exact pin has no PBS asset** (the 3.14.8
  case) was not tested; only the `mise lock` failure from #1449 is cited. Next probe: in a scratch dir run
  `mise install python@3.14.8` with `python.compile` unset/0/1, record rc, error text and whether it compiles,
  and read the precompiled-availability logic in `python.rs`.
- **The headline finding (uv uses managed 3.14.0, not mise 3.14.7) was measured only on the host.** Devcontainer
  and CI interpreter selection were never probed, and the proposed fix (`python-preference = "only-system"`) was
  never tried. Next probe: run `uv python find --project python` and `python -V` in the image and a CI job; apply
  the setting in a scratch copy, verify it resolves to mise 3.14.7 and that `uv sync` still works (only-system also
  ignores uv-managed interpreters; check `UV_PYTHON` path vs preference).
- **Which Renovate datasource the mise manager uses for `core:python`** (python-version vs PBS github-releases),
  and whether it checks PBS asset availability, was not determined; this is the root cause of #1449. Next probe:
  read `lib/modules/manager/mise/` (backends / upgradeable-tooling mapping) in Renovate source, or run a
  `renovate --platform=local` dry-run; consider a `packageRules` datasource override.
- **Renovate pep621 docs were only an exa snippet**, never mirrored or read, and issues #35534/#35488/#34793 were
  triaged but unread; whether pep621 would touch `requires-python` or `.python-version` is second-hand. No Renovate
  manager check covers `.python-version`. Next probe: fetch the pep621 docs page in full, read the three issues,
  and check whether any manager matches `.python-version`.
- **Repo tension unexplained:** `renovate.json:66` claims lockFileMaintenance re-resolves `python/uv.lock` while
  pep621 is not in `enabledManagers`, so the uv.lock refresh may not run. Next probe: check Renovate logs and
  recent PRs for uv.lock lockFileMaintenance activity and read `renovate.json:60-70`.
- **Whether mise PR #11747 is in the repo's pinned mise version** is unverified (2026.9.8 is inherited from
  `findings.md`). Next probe: `mise --version`, the pin in shared/mise-system.toml, then
  `gh api repos/jdx/mise/pulls/11747` merged_at against the release tags.
- **PBS lag magnitude was never measured** (days from CPython tag to PBS asset), so any `minimumReleaseAge`
  value has no data; uv's own lag (frozen Python list per uv release) and uv 0.12.13 coverage of 3.14.7/3.14.8
  were not checked. Next probe: `gh api` over PBS releases plus cpython tag dates for the last 6 patch releases,
  and `uv python list --all-versions | grep 3.14`.
- **Mirrored link content was summarized by haiku mirror agents** and the load-bearing quotes were not
  independently re-verified against the live pages (the adjudicator re-read `links/1.md` and `links/2.md` and
  matched the cited passages, but not the live URLs). Next probe: spot-check each cited `links/N.md:line` quote
  with grep and curl, especially `links/1.md:204` and `links/2.md:216-219`.
- **Reciprocal shipped-vs-proposed status unconfirmed:** whether uv reads `mise.toml`/`.tool-versions` (uv#6574
  open) and whether mise can read `pyproject.toml` `requires-python` or `[tool.uv]` (discussion #12991) are
  cited only as proposals; uv `python-install-mirror` / PBS mirror options for lag were not examined. Next
  probe: grep current uv and mise changelogs for tool-versions / requires-python / idiomatic, and list `mise settings`.
- **Lockfile implications under the uv option are incomplete:** how `uv.lock` (`requires-python`,
  resolution-markers) reacts to an interpreter bump, and the drift between `python/.venv` (built on uv-managed
  3.14.0) and the pinned 3.14.7 for any gates, were not tested. Next probe: in a scratch copy change the
  interpreter patch version and run `uv lock --check` / `uv sync --locked`; check whether tests or gates assert
  the interpreter version.
- **Context7 and uv-discussions sources failed or were unverified-empty**, and no uv-side or Renovate-side issue
  search for "mise" + "python-preference" interop was completed. Next probe: re-run context7 for `/astral-sh/uv`
  and `/jdx/mise` with "python-preference system mise" / "UV_PYTHON mise", and `gh api` issue search in
  astral-sh/uv.

## Verification

Load-bearing claims were each re-probed by a refuter node, then adjudicated where the refuter flagged a
problem. Critic ran: yes (gaps appended above). Adjudicator ran: yes. Failed stages: none.

| # | claim | status | evidence / note |
|---|---|---|---|
| 1 | On the host uv does not use mise's Python: `uv python find --project python` gives uv-managed 3.14.0, `.venv` runs on it, mise pins 3.14.7; cause is default `python-preference = managed` | **confirmed** | Re-probed live (uv 0.12.13). Varying the flag confirms causation: `--python-preference system` / `only-system` return mise 3.14.7, `managed` returns 3.14.0. No `uv.toml`, `.python-version` or `UV_PYTHON_PREFERENCE`. Control: `uv python list --only-installed` lists mise 3.14.7. Minor omission: `.venv` was created by older uv 0.12.9; does not change the conclusion. |
| 2 | PBS has no 3.14.8 build in its latest four releases (20260825-20260929) although CPython tag `v3.14.8` exists | **UPHELD as misleading** (literally true) | Literal claim holds (0 vs 195/195/189/189 for 3.14.7). Omission: all four releases predate the `v3.14.8` tag (2026-09-30T17:55Z), and PBS PR #1308 (3.14.7 -> 3.14.8) merged 2026-10-01T13:50Z. The absence is no evidence of lag; actual lag is under about one day and a release is likely imminent. The inference in Recommendation 5 ("trailed ... across at least four releases") is struck and corrected above. |
| 3 | mise reads `.python-version` only after opt-in; `mise.toml` wins; uv reads `.python-version` by default | **overturned by the adjudicator** (refuter said misleading) | Quotes match `links/1.md:72-82` and `links/2.md:58-61`. The refuter's omission (the tools do not share a source and can diverge) is the report's own headline and Recommendation 3. Minor refinement: uv's `.python-version` search stops at project/workspace boundaries (`links/2.md:71`). |
| 4 | `mise.lock` locks exact per-platform PBS downloads (URL, sha256, attestation); `uv.lock` records only `requires-python >=3.14` and no interpreter lock | **overturned by the adjudicator** (refuter said misleading) | Re-read `mise.lock:742-779` and `uv.lock:3`; `python-build-standalone` has 0 hits in `uv.lock`. The refuter's omission (the locked interpreter is not what uv runs) is the report's headline (claim 1, Conflict 6, Recommendation 4). |
| 5 | Renovate pep621 is not enabled, so nothing would update `requires-python`; the mise manager reads `conf.d/*.toml` | **overturned by the adjudicator** (refuter said misleading) | `enabledManagers` has no pep621/pip; conf.d glob confirmed in docs. `.github/dependabot.yml` is a live pip updater for `/python` dependencies but does not raise `requires-python` (a Python-version constraint, not a dependency; the refuter did not probe this, the adjudicator read the config). Minor context only. |

How the conclusion changes: the recommendation (exact pin in mise, `requires-python` floor, no `.python-version`,
make uv use mise's interpreter) is unchanged. Only the PBS-lag narrative changes: the 3.14.8 gap is a
sub-day tag-to-asset window, not a multi-release lag, so the evidence for a long `minimumReleaseAge` soak is
withdrawn. The #1449 failure mode (a bump landing before the PBS build exists) still stands as the reason to
isolate the python bump.

## Recommendation

1. **Keep the exact interpreter pin in mise** (`shared.toml` → `core:python`). It is the only option that:
   - gives host and image one source;
   - locks the interpreter artifact by checksum and attestation for every platform (`mise.lock`);
   - is already tracked by the Renovate manager this repo enables.

   uv has no interpreter lockfile, so moving the pin to `.python-version` would trade that integrity for nothing.
2. **Keep `requires-python = ">=3.14"` as a floor, not an exact pin.** It is a compatibility statement that uv
   and `uv.lock` resolve against. Making it exact would duplicate the mise pin, create a second bump site, and
   expose `uv lock` to the same PBS lag. Renovate's pep621 manager is not enabled here, so nothing would update
   it anyway.
3. **Do not add `.python-version`.** mise ignores it unless you opt in. uv honours it by default and would select
   its own managed download, so it becomes a second, divergent source. That contradicts the mise docs'
   "Keep one authoritative project version source".
4. **Make uv use mise's interpreter**, so the pin actually governs `uv run --project python`. Options, smallest
   first:
   - `[tool.uv] python-preference = "only-system"` in `python/pyproject.toml`, with optional
     `python-downloads = "never"`. This is the pattern mise users report in uv#17253.
   - Or set `UV_PYTHON` to the mise install path. Per `links/1.md:204`, the bare-version form is not enough.

   Arm it: before the change, `uv python find --project python` → the `…/uv/python/cpython-3.14-…` path (today's
   result). After it, the same command must print `…/mise/installs/python/3.14.7/…`. Recreate `python/.venv`
   and confirm the version reads 3.14.7. Run the same probe in the devcontainer and in CI. This is a
   behavioural change to every gate's interpreter (3.14.0 → 3.14.7), so it needs its own decision and PR, not
   a rider on S29-00.
5. **Handle PBS lag in Renovate, not by moving the pin.** The S29-00 rule that puts python in its own `image
   python` group (`renovate.json:117-128`) contains the blast radius: a lagging python blocks only itself.
   - A follow-up worth evaluating is a `minimumReleaseAge` on that rule. The earlier claim that PBS "trailed
     CPython 3.14.8 across at least four releases" is STRUCK: those releases predate the 3.14.8 tag, so they
     show no lag. Observed lag is under about one day, and the lag duration is otherwise unmeasured, so a
     modest soak is plausible but has no supporting data yet.
   - The longer-term fix is a check that the bumped version actually has a PBS asset, as in this report's
     `gh api` probe.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:jdx/mise | general-purpose | sonnet | low |
| deps:astral-sh/uv | general-purpose | sonnet | low |
| deps:astral-sh/python-build-standalone | general-purpose | sonnet | low |
| deps:renovatebot/renovate | general-purpose | sonnet | low |
| mirror:1/3 | general-purpose | haiku | (default) |
| mirror:2/3 | general-purpose | haiku | (default) |
| mirror:3/3 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — core:python docs, idiomatic-file opt-in, uv venv integration, PBS lock preservation (#11743/#11747), PyPI sidecars (#13141/#13146/#13252), `.python-version` `system` (#13132)
- [astral-sh/uv](https://github.com/astral-sh/uv) — python-versions docs (`.python-version`, `requires-python`, `python-preference`, frozen lists), `.tool-versions` request (#6574), `UV_TOOL_PYTHON` / mise-user pattern (#17253)
- [astral-sh/python-build-standalone](https://github.com/astral-sh/python-build-standalone) — release asset probe (20260825–20260929; no 3.14.8), issue #1293 (3.14.7 archive names)
- [python/cpython](https://github.com/python/cpython) — `git ls-remote` tag probe: `v3.14.8` exists
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — mise manager docs (conf.d match, lock semantics, unsafe execution), pep621 docs (exa hit), issues #35534/#35488, discussion #34793, PRs #46407/#45903 (triaged, not read)
