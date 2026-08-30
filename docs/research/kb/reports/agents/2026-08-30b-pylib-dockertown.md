# dockertown research

Task: assess duckietown/dockertown as a candidate to replace hand-rolled
Docker/BuildKit/bake subprocess calls in `python/src/dotfiles_setup/`.

## Lineage

Confirmed via `gh api repos/duckietown/dockertown`: `fork: true`,
`parent`/`source` = `gabrieldemarmiesse/python-on-whales`. It is a literal
GitHub fork, not an independent reimplementation.

- dockertown created: 2022-10-10
- dockertown last push: **2026-01-05** (~8 months stale as of 2026-08-30)
- dockertown description: "A decent Python wrapper for Docker CLI" (note:
  deliberately downgraded from upstream's "An awesome Python wrapper...")
- dockertown stats: **0 stargazers, 1 fork, 1 open issue**
- python-on-whales (upstream) last push: **2026-08-22** (8 days old at
  research time) — actively maintained
- python-on-whales stats: 710 stars, 130 forks, 57 open issues, MIT license,
  has_discussions=true

This alone is a strong signal: dockertown has essentially no independent
adoption (0 stars vs upstream's 710) and hasn't been touched in 8 months
while upstream ships regularly.

## Feature support: buildx bake / build / imagetools / multi-platform

Verified by reading `src/dockertown/components/buildx/cli_wrapper.py` and its
`imagetools/` subpackage directly (fetched via `gh api .../git/trees` +
`.../contents`):

- **`buildx bake`**: fully supported — `Buildx.bake(targets, builder, files,
  load, cache, print, progress, pull, push, set, variables, stream_logs)`.
  Signature and docstring are near byte-identical to upstream
  python-on-whales's `bake()` (same param names, same example docstring
  text) — this is a copied implementation, not an independent rewrite.
- **`buildx build`**: present (`Buildx.build(...)`), also `Buildx.create`
  (builder instance management), `list`, `use`, `remove`, `inspect`,
  `disk_usage`, `prune`, `version`, `is_installed`.
- **`imagetools`**: dedicated `buildx/imagetools/` subpackage with its own
  `cli_wrapper.py` and `models.py` — `docker buildx imagetools inspect`
  equivalent is present.
- **Multi-platform**: platforms are exposed on the `Builder` object
  (`.platforms` property) and pass-through `set`/build args cover
  `--platform`; no evidence of a platform-specific limitation vs upstream.
- Test fixtures include a real `docker-bake.hcl` + `Dockerfile` under
  `tests/dockertown/components/bake_tests/`, confirming bake is exercised in
  dockertown's own test suite (not just declared, actually tested at fork
  time).

Net: on pure feature surface, dockertown covers everything this repo's
`docker-bake.hcl` / `mise.toml` invocations need — because it inherited it
wholesale from python-on-whales. There is no dockertown-specific bake/build
capability upstream lacks.

## Maintenance health

| Signal | dockertown (fork) | python-on-whales (upstream) |
|---|---|---|
| Last push | 2026-01-05 (~8 months stale) | 2026-08-22 (8 days old) |
| Latest release | v0.2.9 (tag only; releases API shows v0.2.8 @ 2025-10-08) | v0.81.0 @ 2026-03-09, with steady prior cadence (v0.80.0 Jan '26, v0.79.0 Oct '25, v0.78.0 Jul '25, ~monthly-to-quarterly since 2020) |
| Stars / Forks | 0 / 1 | 710 / 130 |
| Open issues | 1 (`#2 "duckietown <- upstream"`, an automated upstream-sync tracking issue, not real feature/bug backlog) | 57 |
| Commits ahead/behind upstream | **+74 / -185** (git compare `python-on-whales:master...dockertown:master`) — 185 upstream commits never pulled in | n/a |
| Contributor base | Dominated by inherited history (539 commits from upstream's own author, `gabrieldemarmiesse`, baked into fork history); dockertown-specific work is a handful of commits from `Tuxliri`, `mdantonio`, `afdaniele`, and 8 commits authored by **GitHub Copilot** (agentic bug-fix commits, e.g. "Fix missing 'raise' keyword before ValueError in buildx bake method" — a real regression the fork itself introduced and then had to patch) | Single maintainer (`gabrieldemarmiesse`) driving continuous releases for 6 years |
| Why the fork exists | README states plainly: "this project is based on python-on-whales". Fork history shows Duckietown (a robotics/education org) needed a Pydantic v2 migration and a Docker-API-version-mismatch fix (`DTSW-7540`) faster than upstream merged/released them, and republished under their own PyPI name (`pip install dockertown`) rather than waiting on/contributing upstream | — |

**185 commits behind upstream is the load-bearing number.** dockertown is not
"upstream plus a few fixes" — it is a snapshot from roughly late 2025 that
picked up ~74 of its own commits (several of which are Copilot-authored fixes
for bugs the fork's own edits introduced) while upstream kept moving.
Anything fixed or improved in python-on-whales in the last 8 months (new CLI
flags, bug fixes, compatibility with newer Docker/buildx CLI output formats)
is absent here.

## Verdict

**Do not adopt dockertown. It is a stale fork of python-on-whales, and if
this repo wants a Docker/buildx wrapper library at all, python-on-whales
itself is the only candidate worth evaluating.**

Blunt reasoning:

1. **It adds nothing python-on-whales doesn't already have.** The
   `bake()`/`build()`/`imagetools` surface is a copy, param-for-param and
   docstring-for-docstring, of upstream. There is no dockertown-exclusive
   capability.
2. **It is 185 commits behind its own upstream and hasn't been pushed in ~8
   months**, against an upstream that shipped a release 8 days before this
   research and has 6 years of continuous single-maintainer cadence.
3. **Zero independent adoption** — 0 stars, 1 fork, versus upstream's 710
   stars / 130 forks. Its one open "issue" is an automated upstream-sync
   tracker, not a real user backlog — there is no community using this fork
   to file bugs against.
4. **It exists for a narrow, already-resolved reason** — a robotics-education
   org (Duckietown) needed a Pydantic v2 migration and a Docker API-version
   fix faster than upstream, and published under their own PyPI name instead
   of waiting or contributing back. That reason has no bearing on this repo.
5. Pinning a dependency this repo would depend on to a project whose only
   activity in the last 8 months is silence is a worse maintenance bet than
   either (a) staying with hand-rolled subprocess calls, which this repo
   fully controls and already gates with tests/contracts, or (b) adopting
   the actively-maintained upstream, `python-on-whales`, if a library really
   is wanted.

If the underlying question is "should `python/src/dotfiles_setup/` stop
shelling out to `docker`/`docker buildx bake` by hand and use a Python
wrapper instead", the answer this research supports is: **evaluate
python-on-whales on its own merits (separately) — dockertown is not in
contention.**

## GitHub repos touched

- [duckietown/dockertown](https://github.com/duckietown/dockertown) — subject repo: metadata, README, buildx/bake source, commits, releases, issues, contributors
- [gabrieldemarmiesse/python-on-whales](https://github.com/gabrieldemarmiesse/python-on-whales) — upstream repo the fork derives from; metadata + releases pulled for maintenance-health comparison
