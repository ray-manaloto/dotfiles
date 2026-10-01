# Leak prevention: betterleaks vs gitleaks, hk builtins, and the telemetry gap

Date: 2026-10-01. Synthesize node: opus, effort high. The input was the research-sweep fan-out for
`leak-prevention-betterleaks-hk-2026-10-01`, plus live probes this node ran itself. Those probes are
marked **[probed]** below, and each one lists its control arm.

## Answer

**Can betterleaks fully replace gitleaks here? Not today. It may also get *harder* to replace with the
next major release.**

The sweep is **complete with respect to its inputs**: there were no mandatory gaps, no mirror gaps and
no failed reads. Its **coverage** gaps are listed under Gaps. TruffleHog, ggshield, Nosey Parker,
detect-secrets and collector-side redaction got no primary-source evidence.

1. **Config compatibility is real in v1, and v2 removes it.**
   - What v1 SHIPS (source code, plus a [probed] `betterleaks dir --help` on the pinned 1.9.0):
     - it reads `.gitleaks.toml`, `GITLEAKS_CONFIG` and `GITLEAKS_CONFIG_TOML`;
     - it reads `.gitleaksignore`;
     - it honors the `gitleaks:allow` comment tag next to its own `betterleaks:allow` tag.
   - That is why this repo's `Builtins.betterleaks` step already inherits `.gitleaks.toml` through
     mise's `GITLEAKS_CONFIG` (`mise.toml:223`).
   - What v2 SHIPS (the **v2.0.0-rc.1 release notes, 2026-09-30, a prerelease**):
     - target-local config discovery and the `GITLEAKS_*` aliases are gone;
     - custom rules need a v2 config format;
     - `-v` now means *validate*;
     - SARIF output, baseline suppression and location-based ignores are gone (ignores become value
       fingerprints).
   - The consequence: a Renovate bump to 2.x would quietly make the hk builtin run on default config.
2. **Rule parity does not hold.** The rulesets have already diverged:
   - betterleaks 1.2.0 made `aws-access-token` a composite rule (it needs a nearby secret key), which
     hk had to accommodate (jdx/hk#1006).
   - This repo measured gitleaks 2 vs betterleaks 1 on the same synthetic dump (`hk.pkl:324-325`).
   - `betterleaks git` silently drops multi-part rules outside the changed lines (betterleaks#335),
     while `gitleaks git` and `betterleaks dir` report them.
   - The "same number of bytes" remark in betterleaks#280 is about **scan volume**, not about findings.
3. **The hk builtins (pinned hk 2.3.0, read from the shipped package source) [probed]:**
   - `Builtins.betterleaks` → `betterleaks dir --redact --verbose --no-banner {{files}}`. This is
     per-file, but it reloads config per path (betterleaks#343).
   - `Builtins.gitleaks` → by default `gitleaks dir … .`, which scans the **whole tree** and ignores
     `{{files}}` and `.gitignore`.
   - **`Builtins.gitleaks` also ships a hidden `scan = "staged"` mode**: `gitleaks git --pre-commit
     --redact --staged …`.
     - This is **not shown on the docs page** (which lists only the default), so the claim that
       "neither builtin uses git mode" is wrong for the shipped source.
     - [probed] staged secret → rc=1; unstaged-only secret → rc=0; `scan = "bogus"` → validation
       error.
   - `Builtins.kingfisher` → `kingfisher scan {{files}} --no-update-check --no-validate --quiet`.
   - `Builtins.detect_private_key` → `hk util detect-private-key`, which needs no external tool.
   - **hk 2.3.0 ships no builtin for TruffleHog, detect-secrets, ggshield or Nosey Parker.** This was
     verified from the package's own `builtins/` listing, with gitleaks matching as the control.
4. **The largest gap is not scanner choice. It is where the telemetry lands.**
   - Claude Code's `OTEL_LOG_RAW_API_BODIES=file:<dir>` writes **untruncated** request and response
     bodies, which hold the entire conversation history, to disk.
   - `.agent/` is allowlisted in `.gitleaks.toml:18`, and that same file feeds betterleaks through
     `GITLEAKS_CONFIG`. A sink under `.agent/telemetry/` would therefore be scanned by **neither**
     tool.
   - A compressed sink would be as invisible as `__MISE_DIFF` already is (0 findings on a compressed
     dump; see `no_env_dump`).

**Recommendation in one line:**
- Keep both scanners. Pin betterleaks below 2 until a deliberate v2 migration.
- Switch the **pre-commit** hook's gitleaks step to `scan = "staged"`, and keep the whole-tree `dir`
  scan for `check` and CI.
- Add a pre-push or CI history scan with `gitleaks git` over the push range.
- Keep telemetry **outside the worktree**, and scan it there on a schedule.
- Prefer not emitting raw bodies at all over redacting them later.

## Evidence

### Claims

| claim | URL or file:line | quote |
|---|---|---|
| hk builtin betterleaks scans the selected files in `dir` mode (docs page) | https://hk.jdx.dev/builtins.html (mirror `docs/research/kb/raw/leak-prevention-betterleaks-hk-2026-10-01/links/1.md:1648`) | "`betterleaks dir --redact --verbose --no-banner {{files}}`" |
| hk builtin gitleaks scans the whole tree by default (docs page) | same mirror `:1656` | "`gitleaks dir --redact --verbose --no-banner .`" |
| **SHIPPED (hk 2.3.0 source):** gitleaks builtin has a staged git mode [probed] | `hk@2.3.0.zip` → `builtins/gitleaks.pkl:7,13-24` (identical in 2.4.0) | "`hidden scan: \"dir\" \| \"staged\" = \"dir\"` … `List(\"gitleaks\",\"git\",\"--pre-commit\",\"--redact\",\"--staged\",\"--verbose\",\"--no-banner\")`" |
| Staged mode discriminates [probed] | scratchpad probe, `hk run pre-commit` with hk 2.3.0 and gitleaks 8.30.1 | staged secret: rc=1, "Finding: awsToken = REDACTED"; unstaged-only: rc=0, "0 commits scanned"; `scan = "bogus"`: rc=1 "expected \"dir\"\|\"staged\"" |
| hk 2.3.0 shipped gitleaks comment: dir takes one path | `builtins/gitleaks.pkl:8` | "gitleaks dir accepts exactly one path. Passing multiple files makes it silently scan \".\"." |
| Community diagnosis of that defect (discussion, not code) | https://github.com/jdx/hk/discussions/1246 | "gitleaks dir accepts exactly one path. With two or more positionals it silently discards them and scans . instead… betterleaks … accepts a list, iterates it" |
| hk kingfisher builtin, validation off | `builtins/kingfisher.pkl:18`; docs mirror `:1664` | "`kingfisher scan {{files}} --no-update-check --no-validate --quiet`" |
| hk detect-private-key needs no external tool | `builtins/detect_private_key.pkl:12`; docs mirror `:1802` | "`hk util detect-private-key {{files}}`" |
| Builtins do not install tools | docs mirror `:9` | "**Install the tools separately.** A builtin invokes executables from your environment; it does not install them." |
| The docs catalogue may differ from the pinned package | docs mirror `:31` | "The catalogue below describes the version of the source used to build this website; an older pinned package may differ." |
| No trufflehog/detect-secrets/ggshield/noseyparker builtin (absence) [probed] | `hk@2.3.0.zip` `builtins/` (161 files) | grep `leaks\|kingfisher\|trufflehog\|ggshield\|nosey\|detect` → only betterleaks, detect_private_key, gitleaks, kingfisher (control: gitleaks matched) |
| betterleaks honors both allow tags (SHIPPED, source) | https://github.com/betterleaks/betterleaks/blob/main/detect/detect.go | "`var allowSignatures = []string{\"betterleaks:allow\", \"gitleaks:allow\"}`" |
| betterleaks reads `.gitleaksignore` (SHIPPED, source) | https://github.com/betterleaks/betterleaks/blob/main/cmd/root.go | "findIgnoreFile looks for .betterleaksignore first, then .gitleaksignore" |
| betterleaks 1.9.0 config order includes the GITLEAKS_* env vars and `.gitleaks.toml` [probed] | `mise exec -- betterleaks dir --help` (pinned 1.9.0) | "2. env var BETTERLEAKS_CONFIG or GITLEAKS_CONFIG … 4. (target path)/.betterleaks.toml or .gitleaks.toml" |
| **v2 removes gitleaks compatibility** (release notes, prerelease) | https://github.com/betterleaks/betterleaks/releases/tag/v2.0.0-rc.1 | "target-local configuration discovery and `GITLEAKS_*` aliases are removed. Custom rules need the v2 configuration format … CSV, SARIF, JUnit, and template output are removed, as is baseline-report suppression." |
| v2 changes the meaning of `-v` | same | "**`-v` now enables validation instead of verbose output**" |
| v2 adds `git --staged` / `--unstaged` | same | "`git --staged` and `git --unstaged` scan added lines in local changes" |
| v2 broadens coverage (binary files, `.git`) | same | "files are no longer skipped solely because they look binary, and the default filters allow .git contents" |
| v2 is unstable | same | "Breaking changes to the CLI, configuration, report formats, and Go API may still land before v2.0.0." |
| v1.0.1 claimed drop-in replacement | betterleaks releases raw (`deps/betterleaks--betterleaks/3/github-releases.raw`) | "It's a drop-in replacement for Gitleaks." |
| `git --staged` and `--pre-commit` exist in both pinned binaries [probed] | `gitleaks git --help` (8.30.1), `betterleaks git --help` (1.9.0) | "--staged  scan staged commits (good for pre-commit)" (control `--zzbogusflag`: 0 matches) |
| Rule divergence: composite AWS rule (merged PR) | https://github.com/jdx/hk/pull/1006 | "Since betterleaks#53 (betterleaks 1.2.0), aws-access-token is a composite rule" |
| Rule divergence measured in this repo | `hk.pkl:324-325` | "on a synthetic plaintext dump gitleaks found 2 and betterleaks 1" |
| betterleaks git drops multi-part rules (open issue) | https://github.com/betterleaks/betterleaks/issues/335 | "betterleaks git never satisfies a multi-part rule when the required component is not inside the changed lines … so the finding is silently dropped. betterleaks dir on the same content reports it, and so does gitleaks git." |
| Default scan VOLUME matches; no migration guide yet | https://github.com/betterleaks/betterleaks/issues/280 | "Running both Gitleaks and Betterleaks with an empty config results in the same number of bytes." |
| Multi-path `dir` is slow | https://github.com/betterleaks/betterleaks/issues/343 | "Passing the same files as a single directory argument scans the same bytes about 100x faster" |
| File targets now inherit parent config (merged PR) | https://github.com/betterleaks/betterleaks/pull/88 | "fix sibling config discovery for file targets by resolving local .betterleaks.toml / .gitleaks.toml from the parent directory" |
| `betterleaks:allow` is undocumented; detect-secrets is called abandoned (issue author's claim) | https://github.com/betterleaks/betterleaks/issues/333 | "Yelp/detect-secrets is an open source secrets scanner that's been abandoned … (currently undocumented) betterleaks:allow comment" |
| betterleaks builtin added to hk (merged) | https://github.com/jdx/hk/pull/750 | "Add betterleaks as a new builtin secret scanner" |
| Expr filters, with legacy CEL accepted (docs) | https://github.com/betterleaks/betterleaks/blob/main/README.md | "legacy CEL-shaped configurations are supported for compatibility, new configurations should utilize Expr." |
| Prefilter/filter/validate stages (docs) | https://github.com/betterleaks/betterleaks/blob/main/docs/config.md | "Prefilter expressions run before regex matching, filter expressions run after regex matching … validate expressions verify if a detected secret is live." |
| Maintainership | https://github.com/betterleaks/betterleaks | "maintained by the folks who made Gitleaks, including the original author." |
| Raw API bodies written to disk untruncated (Claude Code docs) | `docs/research/kb/raw/claude-code-local-otel-sink-2026-10-01/links/1.md:105` | "`OTEL_LOG_RAW_API_BODIES` … Bodies include the entire conversation history … `file:<dir>` for untruncated bodies on disk" |
| Telemetry under `.agent/` is allowlisted (absence of scanning) | `.gitleaks.toml:18`; `mise.toml:223` | "`'''\.agent/''',`" / "`GITLEAKS_CONFIG = \"{{config_root}}/.gitleaks.toml\"`" |
| Compressed blobs are invisible to both scanners (repo measurement) | `hk.pkl:316-318` | "both score 0 on a compressed dump they both flag in plaintext" |
| THIRD PARTY: TruffleHog verifies credentials | https://appsecsanta.com/secret-scanning-tools | "800+ detectors that call the issuing API to confirm a secret is still active" |
| THIRD PARTY: `--only-verified` risk | https://rafter.so/blog/secrets/secret-scanning-tools-comparison | "`--only-verified` in pre-commit hooks means unverified secrets pass through silently" |
| THIRD PARTY: Kingfisher rule count | https://appsecsanta.com/secret-scanning-tools | "Kingfisher — 942 rules, live API validation, and `kingfisher revoke`" |
| VENDOR: Nosey Parker ML precision | https://www.praetorian.com/blog/nosey-parker-ai-secrets-scanner-release/ | "92.4% without ML and an impressive 98.5% with ML filtering … (0.4%) of truffleHog3 with entropy checks" |
| VENDOR via third party: Kingfisher speed | https://appsecsanta.com/secret-scanning-tools | "MongoDB's published benchmarks show it outpacing TruffleHog and Gitleaks" |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `betterleaks filename:hk.pkl` | query | planner | 51 | 0 |
| `betterleaks gitleaks config compatibility filename:README.md repo:betterleaks/betterleaks` | query | planner | 0 | 0 |
| `builtins betterleaks repo:jdx/hk` | query | planner | 3 | 0 |
| `repo:betterleaks/betterleaks filename:README.md` | must-hit | planner | 5 | 0 |
| `qzvxkplm9wjt3` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:betterleaks/betterleaks filename:README.md` | must-hit | workflow | 5 | 0 |
| `repo:jdx/hk filename:README.md` | must-hit | workflow | 10 | 0 |
| `repo:gitleaks/gitleaks filename:README.md` | must-hit | workflow | 5 | 0 |

Notes:
- No row was rate-limited.
- The must-hit and health rows all returned results, and the known-absent row returned 0, so the code
  search discriminates.
- The 0 for the README compatibility query is therefore a true zero for that phrasing. It is **not**
  evidence that compatibility is undocumented. The compatibility facts were found in `cmd/root.go`,
  `detect/detect.go`, the v2 release notes and `--help` instead.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| betterleaks/betterleaks | betterleaks gitleaks parity | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/leak-prevention-betterleaks-hk-2026-10-01/deps/betterleaks--betterleaks/1/manifest.json` (issues, discussions and releases all `empty_verified`) |
| betterleaks/betterleaks | hk | 0 | `…/deps/betterleaks--betterleaks/2/manifest.json` (issues: 1 hit, #343; discussions and releases `empty_verified`) |
| betterleaks/betterleaks | gitleaks | 0 | `…/deps/betterleaks--betterleaks/3/manifest.json` (issues 10, discussions 1 (#360), releases 3 incl. v2.0.0-rc.1) |
| jdx/hk | betterleaks | 0 | `.agent/kb/raw/research-fanout/leak-prevention-betterleaks-hk-2026-10-01/deps/Users/rmanaloto/…/deps/jdx--hk/1/manifest.json`. **This path is malformed and does not exist.** The content was read from the correct path `…/deps/jdx--hk/1/manifest.json` (issues 5, discussions 1 (#1246), releases 2). |
| gitleaks/gitleaks | betterleaks | 0 | `…/deps/gitleaks--gitleaks/1/manifest.json` (issues 10; discussions and releases `empty_verified`) |

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://hk.jdx.dev/builtins.html | `docs/research/kb/raw/leak-prevention-betterleaks-hk-2026-10-01/links/1.md` | 0 | 53936 | — |

## Conflicts resolved

1. **"Neither hk builtin uses git mode" (input claim, from the docs page) vs. the hk 2.3.0 source.**
   - **Trusted:** the source, plus a live probe. `builtins/gitleaks.pkl` in the pinned package has
     `scan = "staged"`, which runs `gitleaks git --pre-commit --staged`. The docs page itself warns
     that it shows *a* version and its defaults.
   - The docs claim is true only of the **default** value.
   - The betterleaks builtin has no such mode in 2.3.0 or 2.4.0. Both versions are byte-identical
     for all four scanner builtins.
2. **This repo's own comment (`hk-common.pkl:27-35`) vs. hk 2.3.0.**
   - The comment says "the builtin runs `gitleaks dir … {{ files }}`". That was measured on hk 1.57.
   - The pinned 2.3.0 builtin passes `.` explicitly and ignores `{{files}}`. Its observable effect is
     the same (a whole-tree scan), so the comment's conclusion still holds, but its mechanism is
     stale.
   - `batch = true` on that step (`hk-common.pkl:134-136`) now batches a command that takes no file
     list. Whether hk then runs the whole-tree scan once per batch was **not measured**; see Gaps.
3. **"Betterleaks supports gitleaks configs" (several input claims) vs. v2.0.0-rc.1.**
   - **Both are true, for different versions.**
     - Trusted for v1: the source code, plus the `--help` probe on 1.9.0.
     - Trusted for v2: the release notes, the newest evidence (2026-09-30).
   - v2 is a prerelease, so details may change again. The direction is explicit, though: the
     compatibility aliases are being removed.
4. **"Feature parity in defaults" (input claim from #280) vs. rule divergence.**
   - The #280 quote compares **bytes scanned**, not findings.
   - Merged evidence of rule divergence beats that reading: hk#1006 / betterleaks#53, this repo's
     measured 2-vs-1, and the open betterleaks#335.
   - Conclusion: there is **no rule parity**.
5. **"Drop-in replacement" (v1.0.1 release notes, 2026-02) vs. later behavior.**
   - The newer evidence wins: composite rules since 1.2.0, #335, and the v2 breaking changes. The
     "drop-in" claim describes the February 2026 launch state.
6. **Kingfisher rule count: "1,000+" (hk description) vs. "942" (AppSec Santa).**
   - These are two different third parties at undated points in time. Neither number was verified
     against Kingfisher's own rules directory, so both are recorded as unverified.
7. **"betterleaks git" vs. "gitleaks git" for history scans.**
   - betterleaks#335 is an open issue, not code. It includes a reproduction, and it claims
     `gitleaks git` reports what `betterleaks git` misses.
   - Until it is fixed, **prefer `gitleaks git` for any history or push-range scan**. That claim was
     not independently reproduced here; see Gaps.

## Gaps

Each item is a gap. None of them means "nothing found".

- **Bad input path:**
  - The planner's sixth manifest path (`.agent/kb/raw/…/deps/Users/rmanaloto/…/deps/jdx--hk/1/manifest.json`)
    is malformed and does not exist. The equivalent manifest at the correct path was read.
- **empty_verified sources** (the control passed, so these are true zeros for those exact queries):
  - betterleaks/1 issues, discussions and releases for "betterleaks gitleaks parity";
  - betterleaks/2 discussions and releases for "hk";
  - gitleaks/1 discussions and releases for "betterleaks".
- **Off-topic source:**
  - The `last30days` source in the telemetry manifest returned unrelated news.
  - Only its betterleaks repo hit (2.1K stars, 108 open issues) is relevant.
- **Tool coverage:**
  - No primary-source hits (repo, releases or source) were gathered for **TruffleHog, detect-secrets,
    ggshield, Nosey Parker or Kingfisher**.
  - Every TruffleHog, Kingfisher and Nosey Parker statement above is third-party or vendor-blog
    evidence.
  - detect-secrets being "abandoned" is one issue author's assertion (betterleaks#333).
  - Nothing was gathered on **ggshield**: not its SaaS data-egress model, its licensing, or any hk
    integration.
  - Nosey Parker's current maintenance status was **not checked**. The "Titus vs TruffleHog" triage
    link hints at a successor tool, but it was **not read**.
- **Workflow coverage:**
  - No source was read on **redaction at the collector**. Whether the OpenTelemetry Collector's
    redaction or transform processors can mask secret patterns in log bodies was not researched.
  - No source was read on scanning telemetry directories.
  - Whether secret regexes still match **JSON-escaped** content (`\n` inside a private key, escaped
    quotes) in OTel body files is **unmeasured**.
- **Staged-file coverage in betterleaks:**
  - `betterleaks git --staged` exists in 1.9.0 ([probed] in help). It is **not** wired into any hk
    builtin, and it was not live-armed here.
  - Given #335 (zero-context diffs), its multi-part-rule behavior in staged mode is suspect and
    unmeasured.
- **The code-search query** for the betterleaks README compatibility phrasing returned 0. That was
  answered from other files; see the note under the code search table.
- **The `batch = true` × `.` interaction** on `Builtins.gitleaks` under hk 2.3.0 is unmeasured. It
  could mean a redundant whole-tree scan per batch.
- **The v2 migration guide** (`docs/v2_migration.md` at v2.0.0-rc.1) was **not read**. Whether
  `--verbose` and `--no-banner` still exist in v2, both of which the hk builtin passes, is unknown.
  A v2 bump could break the builtin outright rather than only dropping the config.
- **#335 was not reproduced** against gitleaks 8.30.1 / betterleaks 1.9.0.
- **Caller link** https://hk.jdx.dev/builtins.html: read (mirror 1.md) and cited.

Critic gaps (appended by the reconcile node; each has a next probe):

- **Primary sources for the other scanners:** no primary source for TruffleHog, detect-secrets, ggshield,
  Nosey Parker or Kingfisher; Kingfisher's rule count (1,000+ vs 942) is unverified; Nosey Parker's
  maintenance status and a possible successor (Titus) were not read.
  Next probe: read each tool's own repo and latest release notes (trufflesecurity/trufflehog,
  Yelp/detect-secrets, GitGuardian/ggshield, praetorian-inc/noseyparker, mongodb/kingfisher); count
  Kingfisher rules from its rules directory; check ggshield's data-egress model and license, and whether
  Titus replaces Nosey Parker.
- **Collector-side redaction:** never researched. Unknown whether OTel Collector `redactionprocessor` or
  `transformprocessor` can mask secret patterns in log bodies, or whether masking would run before the
  file exporter writes `OTEL_LOG_RAW_API_BODIES`.
  Next probe: read both processor docs; live-probe a synthetic secret in a log body; check whether Claude
  Code's `file:<dir>` sink bypasses the collector at all.
- **JSON-escaped bodies:** whether secret regexes still match JSON-escaped content (escaped `\n` in
  private keys, escaped quotes) is unmeasured.
  Next probe: write a synthetic AWS key and a PEM key into a JSON-escaped body file; run `gitleaks dir`
  and `betterleaks dir` against it with a plaintext control and compare counts.
- **v2 migration guide:** `docs/v2_migration.md` was not read; unknown whether `--verbose` and
  `--no-banner` (both passed by the hk builtin) survive in v2. The v2 SARIF and location-ignore removals
  come from release notes alone.
  Next probe: fetch `docs/v2_migration.md` at `v2.0.0-rc.1`; run the rc binary with the exact hk builtin
  argv (`dir --redact --verbose --no-banner`) and record rc and output.
- **#335 not reproduced / staged betterleaks not armed:** the advice to prefer `gitleaks git` for history
  scans rests on an issue claim only.
  Next probe: build a synthetic AWS key-ID plus secret-key pair split across diff context; run
  gitleaks 8.30.1 `git` and betterleaks 1.9.0 `git` (including `--staged`) against `betterleaks dir` as
  the control.
- **`batch = true` with whole-tree `dir .`:** possible redundant whole-tree scan per batch, unmeasured.
  Next probe: run `hk run check` with many files and count gitleaks invocations (wrapper or strace) with
  `batch = true` versus `false`.
- **Staged-scan recommendation breadth:** probed only with a single-file secret. Partially staged hunks,
  renames, deletions, and the claim that pre-commit stops rescanning the whole tree were not measured;
  the hk 2.4.0 builtin's byte-identity to 2.3.0 was asserted, not diffed in the report.
  Next probe: probe a partial stage, a rename and a deletion with `scan = "staged"`; time pre-commit
  before and after; diff `builtins/gitleaks.pkl` between the 2.3.0 and 2.4.0 packages.
- **Push-range history scan:** `gitleaks git --log-opts origin/main..HEAD` was proposed, never run.
  Shallow clones, new branches without an origin ref and force-pushes are untested, as is whether hk's
  pre-push hook supplies the range.
  Next probe: run it in a scratch repo covering a new branch, a force-push and `fetch-depth=1`; read hk's
  pre-push docs for ref arguments.
- **Allowlist and telemetry paths beyond `.agent/`:** other allowlisted paths and the global hk exclude
  were not checked against verbatim reports or telemetry; Claude Code's default telemetry sink location
  is only inferred from the `OTEL_LOG_RAW_API_BODIES` docs.
  Next probe: enumerate every `[allowlist]` and global-exclude entry against likely sink paths, seed a
  secret in each, and confirm the default telemetry and transcript locations (`~/.claude/projects` etc.)
  against the docs.
- **Prerelease dependence:** the v2 behaviors come from a prerelease, and the Renovate hold-below-2.0.0
  advice assumes v2 stable keeps these breaks; the "`betterleaks:allow` undocumented" point rests on one
  issue (#333).
  Next probe: check betterleaks releases for a stable v2 or a later rc and diff against rc.1 notes; grep
  current README and docs for `betterleaks:allow`.

## Recommendation

Ordered by value per unit of cost. Each item notes its trade-off.

1. **Keep gitleaks plus betterleaks as two opinions. Do not consolidate.**
   - The rulesets disagree on real input (2 vs 1), so dual coverage is buying something.
   - **Add a Renovate rule holding `aqua:betterleaks/betterleaks` below 2.0.0** until a deliberate
     migration. At that point the builtin step needs an explicit `-c .gitleaks.toml`, or a
     `BETTERLEAKS_CONFIG` env var, and a v2-format config.
   - The `betterleaks_verbatim_trees` step already passes `-c` explicitly (`hk.pkl:349`), so it
     survives the discovery removal. It does not survive the config-format change.
   - Trade-off: we stay on a 1.x line, which will eventually stop getting rule updates.
2. **Pre-commit: run gitleaks on staged content** with `(Builtins.gitleaks) { scan = "staged" }` in
   the `pre-commit` hook only.
   - Keep `scan = "dir"` in the `check` hook (`mise run lint` ≡ CI) so the whole tree is still
     covered.
   - This scans exactly what will be committed, including partially staged hunks, and stops
     re-scanning the 45 MB tree on every commit.
   - Trade-off: the pre-commit and check hooks then differ, and `ci-local-parity` needs that written
     down.
   - Also fix the stale `{{ files }}` comment in `hk-common.pkl:27-35`, and measure whether
     `batch = true` should be dropped.
3. **Add a push-range history scan**, as a pre-push step and in CI:
   `gitleaks git --log-opts "origin/main..HEAD" --redact`.
   - This is the only layer that sees content committed with `--no-verify`, or committed before a
     rule existed.
   - Prefer gitleaks over betterleaks here because of #335.
   - Trade-off: it costs seconds, and it needs `fetch-depth` greater than 1 in CI.
4. **Telemetry:**
   - **(a)** Prefer not to set `OTEL_LOG_RAW_API_BODIES` at all. It implies consent to everything the
     user-prompt, tool-details and tool-content gates reveal, so every credential a tool ever printed
     lands in the body.
   - **(b)** If bodies are needed, write the `file:<dir>` sink **outside the worktree** (for example
     `~/.local/state/…`). Never put it under `.agent/`, which `.gitleaks.toml` allowlists, so neither
     scanner would see it.
   - **(c)** Run `betterleaks dir -c <cfg> <sink>` on a schedule, as a mise task wrapping Python per
     `zero-bash-logic`. Keep the sink **uncompressed**, or decompress before scanning.
   - **(d)** Treat collector-side redaction as defense in depth, never as the gate. It is unresearched;
     see Gaps.
   - Trade-off: off-worktree data falls outside every hk gate. Only the scheduled scan sees it.
5. **Verbatim agent reports:**
   - Already covered by `betterleaks_verbatim_trees` and `no_env_dump`.
   - Optionally add the cheap `Builtins.detect_private_key` there by path. It currently runs only on
     `{{files}}`, and the global exclude strips the verbatim trees.
6. **Optional third opinion:**
   - **`Builtins.kingfisher`** is the only other scanner hk ships a builtin for.
   - Keep `--no-validate`. Live validation sends candidate secrets to their issuers, which is
     network egress of credentials, and it is inappropriate in a hook.
   - Add it only after a [probed] whole-tree baseline like the one done for betterleaks (0 findings,
     199 ms).
   - TruffleHog and ggshield would need custom steps, and ggshield sends content to a SaaS service.
     Neither is recommended without primary-source research.
   - detect-secrets: do not adopt (called abandoned in betterleaks#333).

## Verification

Five load-bearing claims went through a refute pass (5 refuters), a critic pass and an opus adjudicator.
All steps ran; none returned null and no stage failed. UPHELD refuted claims: none. UPHELD misleading
claims: none (the refuters flagged three as misleading; the adjudicator overturned each).

| # | claim | status | evidence |
|---|---|---|---|
| 1 | hk 2.3.0 `Builtins.gitleaks` has a hidden `scan = "staged"` mode (`gitleaks git --pre-commit --redact --staged --verbose --no-banner`); default is `gitleaks dir ... .` ignoring files; staged secret rc=1, unstaged rc=0, bogus value fails validation | **confirmed** | Raw `pkl/builtins/gitleaks.pkl` at tag v2.3.0 declares `hidden scan: "dir" \| "staged" = "dir"` with exactly the cited argv; the step's own tests include "ignore unstaged files". Docs page shows only the default. Control: a nonexistent builtin path returned 404. The rc probes were not re-run by the refuter; they are corroborated by source and tests, and the 2.4.0 file was not checked by it. |
| 2 | betterleaks 1.9.0 reads `.gitleaks.toml`, `GITLEAKS_CONFIG` / `GITLEAKS_CONFIG_TOML`, honors `gitleaks:allow`, reads `.gitleaksignore`; this is how the builtin inherits `.gitleaks.toml` | **confirmed** | `betterleaks dir --help` on the pinned binary plus live canary probes: each mechanism flipped rc 1 to 0; with no config or with `--ignore-gitleaks-allow` it stayed rc=1. Qualification: the report cites `detect/detect.go` for the allow tags, but a grep of that file on main found nothing for those terms, so that citation is unsupported (the claim holds from `--help` and the probes). Betterleaks' own `.betterleaks.toml` / `.betterleaksignore` rank ahead of the gitleaks names, and `GITLEAKS_CONFIG` is set at `mise.toml:223` for the gitleaks builtin, so inheritance is incidental. The `betterleaks_verbatim_trees` step uses `-c .gitleaks.toml`, not the env var. |
| 3 | betterleaks v2.0.0-rc.1 (prerelease) removes target-local config discovery and `GITLEAKS_*` aliases, requires v2 config format, `-v` means validate, removes SARIF and baseline suppression; a 2.x bump would quietly drop the allowlist from the hk builtin step | **confirmed; refuter's "misleading" overturned by the adjudicator** | Release body quotes all factual parts. The refuter's omissions (prerelease, v1.x stays maintained, migration guide exists, `-c` step unaffected by discovery removal) are already in the report (Answer 1, Conflicts 3, Recommendation 1, Gaps). Qualify "quietly": it is a repo-specific inference, not stated by the release; the plain builtin could instead break outright (hk passes `--verbose`, which means validate in v2). The pin `aqua:betterleaks 1.9.0` means nothing bumps unless deliberately changed. |
| 4 | gitleaks and betterleaks rules are not at parity (composite `aws-access-token` since 1.2.0; repo's 2-vs-1; #335 multi-part rules on `git`; #280 compares scan volume) | **confirmed; refuter's "misleading" overturned by the adjudicator** | hk#1006 re-checked by the adjudicator: merged 2026-07-01 (the refuter called it "closed", imprecise); #335 open and scoped to `betterleaks git`; #280 comment says the byte counts match and finding counts differ. Qualify: the maintainer says the divergence is deliberate, not a defect; the 2-vs-1 is not shown to come from the aws rule (cause unattributed); the aws composite makes betterleaks stricter on a lone key; whether #335 affects hk's builtin (it runs `dir`) is not verified. Compatibility of CLI and config flags is a separate axis from rule parity. |
| 5 | hk 2.3.0 ships no builtin for trufflehog / detect-secrets / ggshield / noseyparker (only betterleaks, gitleaks, kingfisher, detect_private_key); `.agent/` is allowlisted so a `.agent/telemetry` sink is unscanned by either tool | **confirmed; refuter's "misleading" overturned by the adjudicator** | GitHub contents API listing (161 entries) agrees with the zip listing; `trufflehog.pkl` 404 vs `gitleaks.pkl` 200. Live probe: a planted token under `.agent/telemetry/` gave rc=0 for both tools, rc=1 outside it with the same config. Qualify: "either tool" means the two scanners this repo runs; kingfisher (not wired in, does not read `.gitleaks.toml`) was not tested against `.agent/`; hk's `{{files}}` list never includes gitignored `.agent/`; a docs-path sink would be covered by `betterleaks_verbatim_trees`; the allowlist is an editable config entry, not a tool limit. |

**How the conclusion changes:** it does not reverse. Two wording qualifications apply to the Answer: the
v2 allowlist loss is an inference (the builtin may also break outright), and rule non-parity is by
design, not a defect. The `detect/detect.go` citation in the Claims table should be read as unsupported;
`--help` and the live probes carry the claim. The sweep remains incomplete on coverage (see Gaps), not on
the five verified claims.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:betterleaks/betterleaks | general-purpose | sonnet | low |
| deps:jdx/hk | general-purpose | sonnet | low |
| deps:gitleaks/gitleaks | general-purpose | sonnet | low |
| mirror:1/1 | general-purpose | haiku | (default) |
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

Probes run by the synthesize node, in a scratchpad and never committed:
- downloaded `hk@2.3.0.zip` and `hk@2.4.0.zip` from jdx/hk releases and read `builtins/*.pkl`;
- ran `hk validate` with `scan = "staged"` (rc=0) and with the `"bogus"` control (rc=1);
- ran `hk run pre-commit` with a staged secret (rc=1) and with an unstaged-only secret (rc=0);
- ran `gitleaks git --help` and `betterleaks git --help`, grepping `--staged` (control `--zzbogusflag` → 0);
- ran `betterleaks dir --help`, which showed the config resolution order.

## GitHub repos touched

- [betterleaks/betterleaks](https://github.com/betterleaks/betterleaks): source (`detect/detect.go`,
  `cmd/root.go`), docs, issues #1/#12/#56/#87/#280/#333/#335/#343, PR #88, and the v2.0.0-rc.1 and
  v1.0.1 release notes.
- [jdx/hk](https://github.com/jdx/hk): builtins docs page, the `hk@2.3.0` and `hk@2.4.0` pkl release
  packages, PRs #750/#1006/#1194, and discussion #1246.
- [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks): issue and PR fan-out (#2089, #2124 and
  others); the `cmd/directory.go` one-path behavior as cited in hk#1246.
- [mongodb/kingfisher](https://github.com/mongodb/kingfisher): repo page claims (scan targets, binary
  size), via the fan-out; the hk builtin references its `.pre-commit-hooks.yaml` at v1.109.0.
- [cli/cli](https://github.com/cli/cli): code-search health control only.
- Triage-listed but **not read**: ruzickap/cks-notes (PR #40), huntridge-labs/argus (#190),
  oxsecurity/megalinter, Yelp/detect-secrets (only referenced inside betterleaks#333),
  trufflesecurity/trufflehog (only the vendor page and third-party blogs were read).
