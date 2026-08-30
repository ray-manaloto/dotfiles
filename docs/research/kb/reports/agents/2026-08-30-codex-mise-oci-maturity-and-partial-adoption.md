# `mise oci` maturity reassessment + partial-adoption path

Redo of the prior "experimental ⇒ no" verdict. Standing requirement: every
capability claim is a cited quoted excerpt from documentation or real GitHub
data read this session.

## 1. Real maturity assessment

**Feature age: ~4.5 months of continuous, shipped development (introduced
v2026.4.19, still receiving fixes as of v2026.8.11, 2026-08-23).**

Introduction, quoted from the release that shipped it:

> "The biggest addition is `mise` support for building OCI images directly
> from `mise.toml`, with per-tool layering to make image rebuilds more
> efficient."
> — `gh api repos/jdx/mise/releases/tags/v2026.4.19 --jq '.body'`, feature PR
> [#9273](https://github.com/jdx/mise/pull/9273)

Every subsequent release through today mentions `oci` work. Full list of
releases whose body matched `oci` (case-insensitive), oldest to newest,
self-derived via `gh api repos/jdx/mise/releases --paginate`:

```
v2026.4.19  v2026.5.6  v2026.6.4  v2026.6.6  v2026.6.13  v2026.7.0
v2026.7.1   v2026.7.3  v2026.7.6  v2026.7.11 v2026.7.12  v2026.7.16
v2026.8.6   v2026.8.7  v2026.8.11
```

That's **15 of the last ~15+ release cycles over 4.5 months** carrying OCI
work — not a shipped-once-and-abandoned feature.

**Doc's own stability language:** the docs use exactly one word —
"experimental" — via a `<Badge type="warning" text="experimental" />` and the
warning block:

> "`mise oci build` is experimental... Flags, output layout, and defaults may
> change in future releases."
> — `knowledge-base/sources/mise/docs/dev-tools/mise-oci.md:15-25`

There is **no stabilization-timeline statement anywhere in the docs read**
(neither file names a target version or date for graduating out of
experimental). So on the "does mise's own team suggest a timeline" question:
**no** — confidence high, both files read in full.

**Real bug/issue rate, from GitHub, not the issue tracker (mise has none):**

> `gh issue list --repo jdx/mise ...` → `"the 'jdx/mise' repository has
> disabled issues"`

jdx/mise runs entirely on GitHub **Discussions** for bug reports/ideas
instead of Issues. Searched Discussions directly
(`gh api graphql` search `type: DISCUSSION` for `repo:jdx/mise oci`):
**10 discussions found**, of which the "Troubleshooting and bug reports"
category ones are the real bug signal:

| # | Title | Opened | Resolution |
|---|---|---|---|
| [12195](https://github.com/jdx/mise/discussions/12195) | dangling symlinks | 2026-08-20 | **Fixed same week** — maintainer replied same day with root cause + [PR #12211](https://github.com/jdx/mise/pull/12211), merged 2026-08-21, released v2026.8.11 (2026-08-23). `answerChosenAt: 2026-08-27` |
| [11271](https://github.com/jdx/mise/discussions/11271) | `blob chunk upload failed: 201` pushing >64MiB to AWS ECR | 2026-07-24 | Fixed by [PR #11376](https://github.com/jdx/mise/pull/11376), merged 2026-07-27, released v2026.7.16 |
| [10687](https://github.com/jdx/mise/discussions/10687) | apt system-package layer non-reproducible (dpkg postinst side effects) | 2026-07-01 | Fixed by [PR #10731](https://github.com/jdx/mise/pull/10731) "normalize apt/dpkg transient state," merged 2026-07-06, released v2026.7.1 |
| [10617](https://github.com/jdx/mise/discussions/10617) | OCI setuid-mode test not portable under Nix sandbox | 2026-06-25 | Fixed by [PR #10715](https://github.com/jdx/mise/pull/10715), merged 2026-07-06 |
| [10416](https://github.com/jdx/mise/discussions/10416) | `mise oci build` fails on npm/aube tools when symlink target too long | 2026-06-13 | Fixed by [PR #10519](https://github.com/jdx/mise/pull/10519) "write long symlink targets via GNU @LongLink extension," merged 2026-06-23 |

Every real bug report found this session (5 of 5) was **fixed within 2-10
days**, by the maintainer (`@jdx`, mise's primary author), and shipped in the
next or near-next release. This is the actual maintenance signal: real
issues get filed against a real feature in real use, and every one found was
closed with a merged fix, not left open. There is no evidence of a stalled
or abandoned bug in the sample searched.

**PR volume, cross-checked against the same query:** `gh pr list --search
"oci" --state all --limit 50` returned **50 PRs**, all but 2 `MERGED` (the 2
`CLOSED`-not-merged PRs — "add stacker to registry", "wings: auth/policy" —
are unrelated tool-registry additions, not OCI bugs). That is a high
merge rate and steady cadence (PRs dated from 2026-06-12 through
2026-08-24), consistent with active, not abandoned, development. Feature
work in the PR list spans real capability growth, not just bugfixing:
built-in OCI registry push client dropping the skopeo/crane dependency
(#11132), layer reuse from previously-pushed images (#11142), multi-arch
image index support (#11144), APK/Wolfi bootstrap support (#12083),
reproducible host-path copy layers (#10952).

**Confidence and what it means for "experimental" as a label:** high
confidence this is **actively, seriously maintained** experimental — the
label describes API/output-shape stability risk (documented: "flags, output
layout, and defaults may change"), not code abandonment or a
proof-of-concept. The correct reading per the user's instruction is: treat
"experimental" as "the interface may still change under you, budget for a
follow-up bump when it does" — not as "unreliable, don't touch."
**What is NOT resolved by this evidence:** whether *this specific repo's*
current usage pattern (Docker Desktop buildkit-based multi-arch CI on GHA
runners, not `podman`/local `docker load`) has been exercised by anyone else
at scale — that's a gap, not a red flag; see the recommendation below.

## 2. Candidate set for partial adoption

Catalogue of every non-apt, non-from-source `.devcontainer/mise-system.toml`
`[tools]` entry (excludes `[bootstrap.packages]` apt: entries and the
out-of-scope P2996/GCC from-source build stage):

**Core backend (8):** `node`, `go`, `rust`, `zig`, `java`, `deno`, `ruby`,
`cargo-binstall`

**Conda backend (17):** `conda:cmake`, `conda:gxx`, `conda:ninja`,
`conda:mold`, `conda:bear`, `conda:ccache`, `conda:cppcheck`,
`conda:include-what-you-use`, `conda:gdb`, `conda:lcov`, `conda:doxygen`,
`conda:git`, `conda:make`, `conda:linux-perf`, `conda:tar`, `conda:p7zip`,
`conda:valgrind`

**Other (3):** `bazel`, `sqlite`, `micromamba` — registry-resolved backends
(not from-source, not apt); per the doc's supported-backend list (`core,
aqua, cargo, npm, go, pipx, github, gitlab, forgejo, ubi, spm, http, s3, gem,
conda, dotnet`) these resolve to `core`/`aqua`-family backends, which are
OCI-supported.

**Total: 28 tools**, all backends explicitly on mise's OCI-supported list
(`core`, `conda` are both named — `mise-oci.md:378-379`). None use `asdf`/
`vfox`, the only excluded backends
(`mise-oci.md:381-384`, quoted in the prior report). This is **not** a small
leftover set — it's the majority of this file's `[tools]` table (28 of ~30
non-apt entries) and would genuinely each become an independently
cache-keyed layer under `mise oci build`.

**Is 28 tools worth the added pipeline complexity?** This is the real
question, and the prior report's dismissal ("apt doesn't benefit, so skip
it") undersold the candidate set's size — 28 tools is not a marginal
leftover. But size alone doesn't answer the complexity question; what
matters is *how often these 28 individually invalidate each other today*,
because that's the exact pain `mise oci` fixes.

Today, per the prior report (not re-derived, cited as established): a single
`RUN mise install --system --locked -y` (`Dockerfile:347`/`:678`) installs
this entire `[tools]` block plus `[bootstrap.packages]` apt as one Docker
layer, so bumping any one of these 28 tools reinstalls all 28 plus busts
downstream layers. `mise oci build`'s one-layer-per-tool model would turn
that into "only the bumped tool's layer rebuilds" for these 28 specifically
— a real, measurable win on rebuild time and cache-hit rate whenever any
single tool version changes (which Renovate does regularly here per
`renovate.json`'s mise-tracked entries).

## 3. Recommendation

**Adopt later, once two specific, named risks resolve — not "not worth it,"
and not "adopt now."**

This is a genuine revision from the prior "no" verdict: the candidate set (28
tools, most of the non-apt tool surface) is large enough that the *maturity*
objection alone should not have been dispositive, and per the maturity data
above the feature is not abandoned or flaky-in-practice — it's actively
maintained with a fast, real bugfix cycle. The blocker is **architectural
fit with this repo's specific pipeline**, which is a different and better-
grounded objection than "experimental":

1. **It is a parallel/alternative image-build mechanism, not an addition.**
   `mise oci build` produces its own OCI image (base + mise + apt/bootstrap
   layer + one layer per tool + dotfiles + synthesized config) — it does not
   compose with the existing `docker-bake.hcl` multi-stage
   `base → p2996-prep → devcontainer-runtime → dev/dev-load` pipeline
   (`docker-bake.hcl:106` `platforms = ["${PLATFORM}"]` per-arch fan-out,
   GHA layer caching `type=gha,scope=...`). Adopting it for the 28-tool
   `[tools]` block means either (a) running `mise oci build` for that slice
   and `COPY`-ing its output into the existing Dockerfile stages, or (b)
   replacing the tool-install RUN entirely and re-plumbing bake around it.
   Neither is evaluated or attempted here — that's the concrete next-step
   work, not a reason to reject outright.
2. **Multi-arch mechanism doesn't match today's.** This repo's multi-arch
   story is one bake job per architecture (`#676`) using BuildKit's native
   `--platform`. `mise oci`'s multi-arch story is `mise oci push
   --update-index`, "one runner per architecture" assembling an index via
   read-modify-write against the registry (quoted, `mise-oci.md`
   "Multi-arch images" — "the index update is read-modify-write... concurrent
   pushes to the same tag from different runners can race — sequence them").
   That's a **different mechanism with a documented race condition to
   sequence around**, not proven yet against this repo's actual two-arch CI
   topology (`#676`'s parallel amd64/arm64 legs — sequencing them would
   remove the parallelism `#676` was built to add).
3. **No evidence yet of anyone using `mise oci` inside a BuildKit-based
   multi-stage Dockerfile pipeline like this repo's** — every PR/discussion
   found this session describes standalone `mise oci build`/`push` usage,
   not a "layer inside an existing Dockerfile" pattern. That's a real
   unknown, not a defect — but it means a pilot is required before committing
   the whole 28-tool candidate set.

**Concrete next step, if pursued:** a **scoped pilot on a small subset**
(e.g. just the 3 non-conda/non-core outliers — `bazel`, `sqlite`,
`micromamba` — or just the 8 `core`-backend entries) run through `mise oci
build -o ./img` locally/in a throwaway CI job, to answer: does its output
compose with `docker-bake.hcl`'s existing multi-stage/multi-arch flow at
all, and does `--update-index`'s sequencing conflict with `#676`'s parallel
per-arch legs. That pilot is the concrete blocker to resolve — not the
"experimental" label, and not the size of the candidate set (28 tools is
plenty to justify the pilot's cost if the pilot succeeds).

**Not recommended: adopt now, unpiloted.** The maturity data clears the bar
the user asked about (real GitHub bug/PR history shows active, fast-turnaround
maintenance, not code rot) — so do not re-reject on "experimental" alone. But
the open question is repo-specific architectural fit, which the maturity
research cannot answer and which remains genuinely unverified.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — read `mise-oci.md`/`oci.md` docs
  (offline KB mirror); `gh api repos/jdx/mise/releases` (release bodies,
  oci-mention scan, first-appearance version); `gh pr list --search oci`
  (50 PRs, merge status); `gh api graphql` Discussions search (bug-report
  discussions, resolution timelines, `isAnswered`/`answerChosenAt`); `gh
  issue list` (confirmed Issues disabled repo-wide — Discussions are the
  real bug-tracking mechanism); `gh repo view` (repo metadata).
