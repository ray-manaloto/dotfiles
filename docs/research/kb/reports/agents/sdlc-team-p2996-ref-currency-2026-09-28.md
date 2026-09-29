# codex SDLC team review — CLANG_P2996_REF currency (2026-09-28)

Verbatim `output.md` of `mise run sdlc-team` run `fef427ecb37740aebdd76ff528dd1713` (review mode, xhigh; spec `docs/specs/p2996-ref-currency-review.md`). Settlement: completed, 603.6 s, 0 errors; specialists claimed = observed = {config, workflows, image, python}.

---

**The lag comes from broken extraction, missing parity coverage, and a stalled Renovate PR.** Keep Renovate’s native `git-refs` updater, repair both pin sites, and enforce parity before image builds. For autonomous currency, a separate daily compiler-update PR is the strongest recommendation, but it explicitly changes the current image-input grouping policy.

Reviewed checkout: `6e690e0bb22f042076ecdd5b9e9a4f2e3b5218e0`. All four specialists completed.

**Findings**

1. **P1 — Renovate misses the pin that controls Bake builds.**

   [renovate.json:132](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/renovate.json:132) uses:

   ```regex
   CLANG_P2996_REF["= ]+(?<currentDigest>[a-f0-9]{40})
   ```

   It matches `ARG CLANG_P2996_REF=<sha>` but cannot cross the braces, newline, and `default =` in the HCL declaration. Listing both filenames does not guarantee both contain an extracted dependency.

   Bake explicitly passes its value to the build at [docker-bake.hcl:139](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docker-bake.hcl:139) and `:239`, overriding the Dockerfile default. Docker documents that Bake `args` supplies build arguments. [Docker Bake reference](https://docs.docker.com/build/bake/reference/#targetargs)

   Live upstream head:

   ```text
   f17c8d6c7bfef5e02ccadcf33517fd2a53b51b6e
   ```

   | Site | Current SHA | Commits behind |
   |---|---|---:|
   | [Bake default](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docker-bake.hcl:101) | `7220baffd57ea5b0f8cf59bee494dd5b7cc2b748` | **12** |
   | [Dockerfile ARG](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:426) | `f349a2d801fbde1f2796dcc003db3d57b3f84515` | **6** |

   Both requested comparisons ran through native `fnox … exec --` and returned **rc=0**:

   ```text
   gh api repos/bloomberg/clang-p2996/compare/7220baffd57ea5b0f8cf59bee494dd5b7cc2b748...p2996 --jq .ahead_by
   12

   gh api repos/bloomberg/clang-p2996/compare/f349a2d801fbde1f2796dcc003db3d57b3f84515...p2996 --jq .ahead_by
   6
   ```

2. **P1 — The parity gate never registered clang-p2996.**

   [pin_parity.py:137](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pin_parity.py:137) iterates the registry; `pin-parity.toml` has no clang-p2996 entry. The existing checker already rejects differing values, missing files, and unmatched patterns once sites are registered.

   Independently, [hk.pkl:583](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl:583) omits `docker-bake.hcl` from the parity trigger. Both omissions need fixing. A regression test must also require the registration itself, because deleting it otherwise silently removes coverage.

3. **P1 — #1063 stopped updating after another bot committed to its branch.**

   [Renovate’s notification](https://github.com/ray-manaloto/dotfiles/pull/1063#issuecomment-5663353711) explicitly identifies an unrecognized last commit author and refuses further automatic rebasing.

   Live metadata returned **rc=0**: PR open, `DIRTY`, auto-merge enabled, head `3abd52d964e9f70ccd99328b9b7afe945cb71bb3`, last updated September 14. Its compiler target remains `0664c3f65dd5b198341412d7402b41f8e766b4b4`, an upstream commit dated September 12.

   The offending commit came from [gcc-sha-repair.yml:88](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/gcc-sha-repair.yml:88), using:

   ```text
   dotfiles-refresh-bot-org[bot]@users.noreply.github.com
   ```

   This explains the frozen target directly; it is not evidence that Renovate cannot track the branch.

4. **P1 — #1063’s red checks are tool/lock failures, before compiler validation.**

   Historical logs were retrieved with `gh run view … --log-failed`, each retrieval **rc=0**.

   | Check | Recorded failure |
   |---|---|
   | `lint` and `autofix` | mise could not install `packslip:github.com/jdx/hk@1.58.1`: `hk@1.58.1 is not in the lockfile`; job exit 1 |
   | `image-lock-pr` | Regeneration converged and five tests passed; containment then rejected changes to `.config/mise/mise.lock` and root `mise.lock`; exit 1 |
   | `ci-gate` | `RESULTS: failure skipped skipped skipped`; exit 1 |

   The containment violation included an hk backend/version rewrite and AWS/Docker checksum additions: **31 insertions, 29 deletions**. Preserve the containment check at [refresh.yml:392](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/refresh.yml:392).

   Evidence: [CI](https://github.com/ray-manaloto/dotfiles/actions/runs/34839072681), [autofix](https://github.com/ray-manaloto/dotfiles/actions/runs/34839072436), [image-lock repair](https://github.com/ray-manaloto/dotfiles/actions/runs/34839072275). The compiler build was skipped.

5. **P2 — Current refresh/build paths establish reproducibility, not upstream currency.**

   [refresh.yml:20](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/refresh.yml:20) retired the scheduled compiler updater in favor of Renovate. Nightly builds use committed pins. The `p2996_ref` workflow input exports a selected SHA consistently; it does not discover upstream head.

   The retired [p2996_refresh.py:148](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_refresh.py:148) fetches upstream head but writes **only Bake**. Restoring it unchanged would create the reverse divergence. Its CLI has no `--ref` option.

   Likewise, [image.py:646](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:646) correctly checks that the compiler matches the selected pin. Its successful message establishes neither cross-file parity nor upstream currency.

**Why #904 escaped**

`gh pr view 904 … --json …` and `git show e85c35be …` returned **rc=0**. The merged PR changed only:

```diff
-ARG CLANG_P2996_REF=060be17654102019e14810c3f948ef85a490755f
+ARG CLANG_P2996_REF=f349a2d801fbde1f2796dcc003db3d57b3f84515
```

`git log --oneline -S f349a2d -- docker-bake.hcl` returned **rc=0 with no output**.

The config specialist replayed the actual regex against both files in memory:

| Probe | Dockerfile matches | Bake matches | RC |
|---|---:|---:|---:|
| Existing matcher, observational probe | 1 | 0 | 0 |
| Proposed matchers, require both sites | 1 | 1 | 0 |
| Restore existing matcher, require both sites | 1 | 0 | **1** |

Renamed variables and malformed digests produced zero matches. These were JavaScript regex probes, not a native Renovate/RE2 integration run.

**Recommended change set**

| Files | Recommendation |
|---|---|
| `renovate.json` | Keep `git-refs`, `currentValueTemplate: "p2996"`, and captured `currentDigest`; replace the matcher with explicit Dockerfile and multiline-HCL expressions. |
| `docker-bake.hcl`, `.devcontainer/Dockerfile` | Reconcile both immutable SHAs in one candidate PR; correct the Dockerfile comment claiming automatic lockstep already works. |
| `pin-parity.toml`, `hk.pkl` | Register both compiler sites and include Bake in the parity trigger. |
| `tests/test_pin_parity.py`, `python/verification/suites.toml` | Require the registration, exact two paths, and trigger coverage; exercise the shipped patterns through public interfaces in isolated fixtures. |
| `p2996_refresh.py`, `tests/test_p2996_refresh.py`, `mise.toml` | Correct stale scheduling descriptions. If the manual command remains supported, validate and update both sites together, including when Bake is already current but Dockerfile differs. |
| `.github/workflows/refresh.yml`, `.github/workflows/AGENTS.md`, `.github/workflows/ci.yml` | State clearly which automation advances pins and which rebuilds committed pins. Preserve containment and required checks. |
| `.github/workflows/build-publish.yml` and workflow tests | Preserve selected-SHA propagation; test each override consumer rather than merely checking that the variable appears somewhere in the file. |

The proposed Renovate expressions, before JSON escaping, are:

```regex
(?:^|\n)ARG CLANG_P2996_REF=(?<currentDigest>[a-f0-9]{40})(?:\r?\n|$)
variable\s+"CLANG_P2996_REF"\s*\{\s*default\s*=\s*"(?<currentDigest>[a-f0-9]{40})"
```

Renovate documents branch tracking through `currentValue` plus `currentDigest`; its regex manager operates per file using RE2. No custom update service is needed. [git-refs documentation](https://docs.renovatebot.com/modules/datasource/git-refs/), [regex manager documentation](https://docs.renovatebot.com/modules/manager/regex/)

For ongoing automation:

- **Preferred design:** one Renovate-owned compiler PR, separate from GCC/mise repair writers, with a daily update window and required image/smoke checks before auto-merge. This is a proposed exception to the existing `image-build inputs` grouping, not an already-ratified change.
- **Minimal policy-preserving repair:** retain the group and fix extraction/parity now. Autonomous currency remains unresolved until the group’s repair/rebase ownership is repaired.
- Keep immutable SHAs. “Always current” should mean automatic convergence to the latest observed candidate after required checks pass, with visible lag when blocked.
- Do not rely on `minimumReleaseAge` for commit aging: `git-refs` supplies no release timestamp. Current `timestamp-optional` does not provide the configured one-hour guarantee.
- A Renovate schedule permits update windows; it does not schedule the hosted bot itself. `updateNotScheduled: false` constrains existing-branch updates too. Platform auto-merge does not honor `automergeSchedule`. [Renovate configuration](https://docs.renovatebot.com/configuration-options/)
- Dependabot supports defined ecosystems, including git submodules, but offers no equivalent generic extractor for these HCL/Dockerfile SHA literals. Keep its existing Python ownership. [GitHub’s ecosystem list](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)

**Licensed dissent**

Two premises must not carry into implementation:

- **Rebuild cost:** a compiler bump invalidates the compiler/final-image tiers, not inherently the independent base tier. [p2996_hash.py:7](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_hash.py:7) and [build-publish.yml:267](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:267) establish this. Repository estimates are 80–120 minutes cold and 15–30 minutes with warm ccache; no duration was measured here.
- **Repair authors:** [refresh.yml:409](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/refresh.yml:409) intentionally uses an unrecognized author to prevent Renovate from overwriting repaired locks. Blanket `gitIgnoredAuthors` would defeat that strategy. Native author recognition should be adopted only with demonstrated repair regeneration after rebases. [Renovate author handling](https://docs.renovatebot.com/configuration-options/#gitignoredauthors)

**Gate that would have caught the divergence**

The existing **`mise run pin-parity`**, extended with both sites and both file triggers, is the direct gate. Proposed acceptance arms—all **unrun** in this review:

| Behavior | Pass arm | Realistic fail arm |
|---|---|---|
| Two-site parity | Both valid SHAs equal → rc 0 | Replay #904’s Dockerfile-only change → rc 1 |
| Reverse divergence | Both equal → rc 0 | Change Bake only → rc 1 |
| Extraction completeness | Both declarations present | Remove/malform either declaration → nonzero |
| Mandatory coverage | Registry contains both required sites | Delete registration/site → regression test fails |
| Hook selection | Either file selects parity | Restore Bake omission → trigger test fails |
| Renovate extraction | Native extraction finds both sites | Restore current regex → fixture fails |
| Repair lifecycle | New upstream SHA advances candidate and repairs regenerate | Unknown author freezes update, or missing regeneration leaves stale artifacts → fails |

Parity must run before expensive compiler work. Preserve the independent built-SHA smoke check and add scheduled upstream-lag reporting; two equal pins can still be stale.

**Research, execution, and limitations**

The mandated `fnox … exec -- mise … research-fanout --strict-five` completed **rc=0**. Independent manifest validation also returned **rc=0**, including raw-evidence validation.

| Route | Result |
|---|---|
| GitHub issues / discussions | 10 / 10 results |
| GitHub releases | Empty, verified by a successful control query |
| Exa | 10 results |
| Context7 | 5 results |
| Firecrawl developer / search | 10 / 10 results |
| Last30Days | 5 results; GitHub and grounding sources both `ok` |

[Research manifest](/Users/rmanaloto/.codex/research-coverage/01a0eab3-e758-7102-a9ba-3772639b67b2/01a0eab3-ee05-7c91-93ad-d6c626515288/manifest.json)

Actually used: `codex-sdlc-team` and `research-sweep` skills; pin-parity and Last30Days references; `fnox`, `mise`, `uv`/Python, `gh`, `git`, `node`, `ctx7`, `firecrawl`, and local file tools. Exa and Firecrawl’s developer route used HTTP APIs; Last30Days used its installed Python engine. Official documentation was verified with web browsing. No connector app or MCP research route ran.

Recovered exploratory failures included a Renovate documentation 404, raw Markdown incorrectly parsed as JSON, an abbreviated-SHA HTTP 422, nonexistent-path searches, and zsh unmatched globs. None remained a required-source blocker.

**No repository gates, builds, commits, PR mutations, or workflow triggers ran.** No review report file was written. The planning hook required one entry in [progress.md:1448](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/progress.md:1448), contrary to the requested no-writes boundary; that exception is disclosed explicitly. Git status otherwise retained only the preexisting untracked specification.

No other specialists were spawned.

Specialists spawned:

- `sdlc-config-specialist` — `/root/config`
- `sdlc-workflows-specialist` — `/root/workflows`
- `sdlc-image-specialist` — `/root/image`
- `sdlc-python-specialist` — `/root/python`


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — pins, renovate.json, workflows, #904, #1063
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — p2996 branch head and compare
