# Audit A — evidence grounding for issue #847

## Method

**Fixed offline evidence only.** I read the issue body, the specified 41 `main`
reports, the three `2026-08-30c-*` PR-branch reports, the prefetched open-issue
and open-PR censuses, `main-audit` at its recorded `origin/main` ref, and the
supplied PR-branch checkout at `6278d6c`. The
required starting sources establish both the research reconciliation boundary
(`2026-08-30b-SYNTHESIS.md:1-13`) and its one-lane-per-source coverage model
(`2026-08-30b-SOURCE-COVERAGE.md:1-10,12-54`).

**Verdicts.** `GROUNDED` means a report, prefetched tracker snapshot, shipped
code path, or fresh read-only probe supports the stated fact; `ASSERTED` means
none measures it; `CONTRADICTED` means fixed code/report evidence conflicts with
the wording. No network or GitHub query was used.

**Negative-search control.** For the one tracker field absent from the supplied
censuses, I ran unbounded `auto-merge|automerge` search across all 44 reports;
it returned 0. The identical report-path/search shape for `#841` returned
multiple hits, including the synthesis status note
(`2026-08-30b-SYNTHESIS.md:8-13`), so the null is a corpus result, not a broken
search. The prefetched PR census does not carry an auto-merge field
(`gh-open-prs.txt:1-4`).

## Domain

The issue contains **22**, not roughly 21, claims in the four requested blocks:
3 `What shipped` rows (`gh-issue-847.md:10-18`), 7 operator decisions
(`gh-issue-847.md:34-42`), 6 overturned conclusions
(`gh-issue-847.md:44-51`), and **6**, not 5, known-imperfect bullets
(`gh-issue-847.md:53-60`). The prompt's parenthetical omitted the
`GRAPHIFY_HOOK_STRICT` / strict-TTL bullet at issue line 60; this report audits
it. It distinguishes local Git-ref/code evidence from live PR/issue state.
Unless an absolute path is shown, #841 code paths resolve under `main-audit/`;
#846 code paths resolve under `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/`.

## Findings

### MEDIUM · CONTRADICTED · #841 is merged locally, but the row undercounts its follow-on repair sets as “+ 3” · `gh-issue-847.md:14`

**EVIDENCE.** The fixed `origin/main` ref and the `main-audit` worktree HEAD
both name `1e6a36821c94f276def99f262f108b9b03eedb74`
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/refs/remotes/origin/main:1`,
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/worktrees/main-audit/HEAD:1`). Its original configuration
change is present: the exact `16.2.0` pin and `linux/arm64` scope are in
`.devcontainer/mise-system.toml:63-68`. The post-pin code has **four** distinct
repair sets, not three:

1. the expected-tool parser filters the real config by architecture, with
   paired omit/keep tests (`tests/test_image_smoke.py:630-653,824-831`);
2. exec smoke derives its expectation from inspected image architecture and
   cross-checks that against in-container `uname` (`tests/test_image_smoke_exec.py:126-174,185-196`);
3. the `os=` mirror repairs alias/strict-token behavior and couples the literal
   gate to the accepted alias set (`python/src/dotfiles_setup/image.py:129-220`,
   `python/src/dotfiles_setup/platform_target.py:139-143`);
4. tier-3 receives and uses the arch-derived `conda_gxx` presence condition
   (`python/src/dotfiles_setup/image.py:820-864,975-994`).

This count also accords with the issue's own five-defect inventory: one
scope/pin premise followed by four separate assumptions that `conda:gxx`
exists on every architecture (`gh-issue-847.md:22-30`). The synthesis provides
an independent historical landing assertion for #841, although at its earlier
commit (`2026-08-30b-SYNTHESIS.md:8-13`).

**DISPOSITION.** `MERGED` is **GROUNDED for the fixed local ref**, not freshly
verified GitHub state. The pin/scope is **GROUNDED**. Replace “+ 3 follow-on
fixes” with “+ 4 follow-on repair sets,” or enumerate them to avoid another
ambiguous count. Current-GitHub merge metadata remains unverified offline.

### MEDIUM · ASSERTED (auto-merge only) · PR #846 is “open, auto-merge armed” · `gh-issue-847.md:15`

**EVIDENCE.** The prefetched open-PR census lists #846 as non-draft
(`gh-open-prs.txt:1`), so **open is GROUNDED** as of that snapshot. The supplied
branch is locally and remotely pinned to `6278d6c`
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/refs/heads/fix/graphify-health-links-schema:1`,
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/refs/remotes/origin/fix/graphify-health-links-schema:1`),
so the implementation portion is inspectable. It accepts Graphify’s `links`
edge collection (`python/src/dotfiles_setup/graphify.py:102-113,204-209`), no
longer treats an absent receipt as stale (`python/src/dotfiles_setup/graphify.py:145-189,224-243`),
and the named rule explicitly says that the wrong-builder-version question is
not detectable and the protection is procedural (`.claude/rules/graphify-first.md:10-41`).
Thus “health tells the truth + rule made honest” is **GROUNDED narrowly for
the supplied branch's health behavior and `graphify-first.md`**.

There is a related intra-branch contradiction worth retaining: the new
`graphify-update` task still claims it “stamp[s] the graphify version” and
records a builder version so health can detect a wrong binary
(`mise.toml:736-744`), while the final rule says the stamp was removed because
that detection cannot work (`.claude/rules/graphify-first.md:23-41`) and the
implementation explains the same removal (`python/src/dotfiles_setup/graphify.py:163-177`).
That does not refute the named rule, but it prevents a blanket “all graphify
guidance is now honest” conclusion.

I applied the required correction hierarchy: the install-probe's top block
retracts its earlier contrary recommendation and confirms that `graphify codex
install` exists and the protective rule remains (`2026-08-30c-graphify-install-probe.md:5-23`);
it provides no PR-status evidence.

**DISPOSITION.** The implementation/rule claim and open state are **GROUNDED**,
with the `mise.toml` caveat. Only “auto-merge armed” is **ASSERTED**: neither the
prefetched census nor any report measures it (controlled negative search in the
Method). Do not run the stated future `land` step from this row alone; verify the
live PR first.

### LOW · GROUNDED · Issue #845 is open and `ready-for-agent` for the mise `os=` reimplementation debt · `gh-issue-847.md:16`

**EVIDENCE.** The prefetched complete open-issue census lists #845 with the
`ready-for-agent` label and the matching title (`gh-open-issues.txt:2`), which
grounds its existence, state, label, and scope as of the snapshot. The
underlying technical debt is independently **GROUNDED**: production code
parses TOML and predicts whether a tool should be installed from a host-side
`arch` argument (`python/src/dotfiles_setup/image.py:173-192`). Its own
contract admits the boundary: mise may apply backend-level platform
restrictions that this parsed-entry model cannot observe
(`python/src/dotfiles_setup/image.py:194-202`). The issue describes the
intended next step as stopping that prediction (`gh-issue-847.md:91-96`).

**DISPOSITION.** `in-scope-for-#847` — grounded against the supplied snapshot
and source; live status after that snapshot remains **UNVERIFIABLE (no
network)**.

## Decisions the operator made — 7 claims

### HIGH · CONTRADICTED · “Adopt the base-OS axis and `subaction/matrix` both at once, not sequenced” reverses the completed synthesis's timing verdict · `gh-issue-847.md:36`

**EVIDENCE.** The research does ground the bridge's feasibility: it derives a
GHA matrix from Bake's printed target graph (`2026-08-30b-SOURCE-COVERAGE.md:77-106`;
`2026-08-30b-SYNTHESIS.md:33-65`). But the same synthesis establishes that the
repo currently has one container base OS, not a base-OS axis
(`2026-08-30b-SYNTHESIS.md:90-132`), and its final recommendation is explicit:
the shipped Python enumeration is already one source of truth; adopt the bridge
**when and if** the wider axis becomes real, because adopting it now spends the
migration cost for a drift risk that does not yet exist
(`2026-08-30b-SYNTHESIS.md:380-397`). An earlier advisor independently said not
to add a base-image field until a second container base exists
(`2026-08-30-fable-advisor-and-lane-reports-consolidated.md:53-70`). Thus the
issue's direction is not merely uncited; it points Task 2 opposite the session's
adjudicated recommendation. Upstream action currentness is **UNVERIFIABLE (no
network)**, but this contradiction is fully answerable from the fixed corpus.

**DISPOSITION.** `in-scope-for-#847` — correct the decision record or attach the
later operator evidence that explicitly overrode the synthesis; do not spec
“both now” from #847 alone.

### LOW · GROUNDED · Use descriptive suffixes encoding every axis rather than opaque leg IDs · `gh-issue-847.md:37`

**EVIDENCE.** The live coverage record expressly calls the target name that
encodes every axis “Ray's chosen descriptive-tag scheme”
(`2026-08-30b-SOURCE-COVERAGE.md:157-169`). The synthesis then derives the
concrete additive format and examples (`2026-08-30b-SYNTHESIS.md:219-264`).
This is independent support for both the decision and its technical shape.

**DISPOSITION.** `in-scope-for-#847` — no correction needed.

### LOW · GROUNDED · The local devcontainer defaults to amd64, with arm64 opt-in; R3 preserves amd64 · `gh-issue-847.md:38`

**EVIDENCE.** The shipped default is `linux/amd64/v2`
(`mise.toml:140-152`); the repo documents the arm64 profile as an explicit
`MISE_ENV=arm64` opt-in (`.devcontainer/AGENTS.md:109-116`); and R3 requires
`x86_64`/`amd64` in the container (`AGENTS.md:154-162`). These three independent
surfaces match the issue claim.

**DISPOSITION.** `in-scope-for-#847` — no correction needed.

### MEDIUM · GROUNDED · Graphify platform scope is Claude + Codex + Agents · `gh-issue-847.md:39`

**EVIDENCE.** The upgrade research reads the installed platform table and
establishes `claude`, `codex`, and `agents` as three distinct targets with
different destinations (`2026-08-30c-graphify-upgrade-research.md:13-48`). The
later containment probe executed the project-scoped form for all three at both
installed versions and found the same contained write shape
(`2026-08-30c-graphify-install-probe.md:403-452,614-618`). This grounds the
three-platform scope technically. It does **not** make the install mechanical:
the existing `.agents` skill is hand-authored and clobber-prone; that omitted
premise is recorded under Question 2 below.

**DISPOSITION.** `in-scope-for-#847` — keep the decision, but link the
`.agents` preservation constraint before Task 2 implements it.

### MEDIUM · ASSERTED · Graphify library scope is “full lifecycle — skills + rebuild + health + drift” · `gh-issue-847.md:40`

**EVIDENCE.** No report in the 44-file corpus records this phrase or an
equivalent four-part operator decision. Unbounded `rg -i 'full lifecycle'`
over the same 44 paths returned 0. A second unbounded concept search for
`skills.*rebuild|rebuild.*skills|rebuild.*health|health.*drift|operator.*decision`
also found no Graphify four-part decision; its only relevant Graphify hit was a
version-drift implementation note, not an operator scope decision
(`2026-08-30c-graphify-upgrade-research.md:468-470`). Control arm: the identical
report-path/search shape for `subaction/matrix` returned 39 report lines, so the
corpus search discriminates. The branch contains individual
rebuild/health/query machinery, but shipped pieces do not prove that the
operator selected this future library boundary.

**DISPOSITION.** `in-scope-for-#847` — attach the operator answer/transcript or
mark this scope as pending `/grilling`; otherwise Task 2 would treat an asserted
architecture boundary as settled.

### LOW · GROUNDED · Remove the runtime stamp because it cannot detect PATH-builder drift; make the rule honest · `gh-issue-847.md:41`

**EVIDENCE.** The cold review proves both failure arms: a bare PATH build writes
no stamp, while the sanctioned writer can only stamp its own pinned version
(`2026-08-30c-opus-cold-review-graphify-2.md:17-50`). At `6278d6c`, the rule now
states that this binding is unobtainable and protection is procedural
(`.claude/rules/graphify-first.md:10-46`), and production records why the stamp
was removed (`python/src/dotfiles_setup/graphify.py:145-189`). One stale copy
survives: `mise.toml:736-744` still says the task stamps/detects the builder;
that is a completeness finding below, not evidence that the mechanism remains.

**DISPOSITION.** `in-scope-for-#847` — the decision is grounded; narrow “rule
made honest” to the named `graphify-first.md` until the stale task prose is fixed.

### LOW · GROUNDED · Supersede Dependabot #837 and upgrade directly to Graphify 0.9.53 · `gh-issue-847.md:42`

**EVIDENCE.** The prefetched open-PR census identifies #837 as an open
Dependabot bump only to 0.9.48 (`gh-open-prs.txt:2`). The upgrade report identifies
0.9.53 as the target and specifies the repo pin change plus all coupled version
literals (`2026-08-30c-graphify-upgrade-research.md:363-375,450-476`). Together
they ground why #837 is obsolete and why the direct target is 0.9.53. Live
tracker state after the prefetch remains **UNVERIFIABLE (no network)**.

**DISPOSITION.** `in-scope-for-#847` — no evidence correction needed; recheck
the PR live before mutating it.

## Findings that overturned earlier conclusions — 6 claims

### LOW · GROUNDED · Bake can own the permutation declaration through `subaction/matrix`, though HCL still cannot select runners · `gh-issue-847.md:46`

**EVIDENCE.** The coverage record describes the action's mechanism from its
full `action.yml`: `bake --print`, JSON parsing, target-field copying, and GHA
matrix output (`2026-08-30b-SOURCE-COVERAGE.md:77-106`). The synthesis
reconciles that mechanism against the earlier “Bake cannot help” conclusion and
preserves the crucial limitation that HCL does not place work on a runner
(`2026-08-30b-SYNTHESIS.md:15-88`). This supports the issue's technical
overturning. Current upstream action behavior is **UNVERIFIABLE (no network)**;
the verdict is about support in the fixed corpus.

**DISPOSITION.** `in-scope-for-#847` — technically grounded; keep separate from
the contradicted “adopt now” timing claim above.

### LOW · GROUNDED · `docker/github-builder` cannot express two same-platform arm64 legs on different runner labels · `gh-issue-847.md:47`

**EVIDENCE.** Two research lanes independently report that its `runner` map is
keyed only by platform prefix (`default`, `linux`, `linux/arm`,
`linux/arm64`), which cannot distinguish this repo's two `linux/arm64/v8`
runner-OS legs (`2026-08-30b-SOURCE-COVERAGE.md:146-173`). The synthesis reaches
the same exclusion (`2026-08-30b-SYNTHESIS.md:81-88,134-149`). Upstream
currentness is **UNVERIFIABLE (no network)**, but the issue accurately reflects
the corpus.

**DISPOSITION.** `in-scope-for-#847` — no evidence correction needed.

### MEDIUM · CONTRADICTED · `graphify codex install` does break the cap, but #847's 12,961 / 961-over arithmetic mixes bytes with a character limit · `gh-issue-847.md:48`

**EVIDENCE.** Fresh derivation on `6278d6c`: `wc -c AGENTS.md` = **11,831
bytes**, reproducing the issue; `wc -m AGENTS.md` = **11,743 characters**. The
packaged `agents-md.md` is 1,129 ASCII characters, and the installer's
append path adds one net separator character (`graphify/install.py:482-507`),
re-deriving the report's **+1,130** delta
(`2026-08-30c-graphify-install-probe.md:521-533`). But the repository documents
AGM-003 as a **12,000-character** rule, not a byte rule
(`.claude/rules/md-size-budgets.md:38-57`). Correct like-unit arithmetic is
11,743 + 1,130 = **12,873 characters**, **873 over**. The report and issue's
12,961 / 961-over result is byte arithmetic applied to a character cap
(`2026-08-30c-graphify-install-probe.md:535-549`). The core safety verdict still
stands. I also freshly counted the complete 0.9.42 help at **161 lines** and
0.9.53 at **174**; the `codex install` entry is outside the truncated first 40
lines exactly as the correction block says
(`2026-08-30c-graphify-install-probe.md:12-40,103-125`).

**DISPOSITION.** `in-scope-for-#847` — retain the blocker, replace the mixed-unit
overage with 12,873 characters / 873 over, and name 11,831 explicitly as bytes
only.

### LOW · GROUNDED · Two Graphify versions are installed and unsynchronised; the global one is outside CI's repo pin · `gh-issue-847.md:49`

**EVIDENCE.** Fresh direct probes returned 0.9.42 from
`python/.venv/bin/graphify` and 0.9.53 from the user-global mise install. The
two owners are independently visible at `python/pyproject.toml:9` and
`~/.config/mise/config.toml:288`. The report measures the same resolution split
and explains that the global config is outside repo review
(`2026-08-30c-graphify-doc-audit.md:208-243`); the containment probe separately
records both binaries and paths (`2026-08-30c-graphify-install-probe.md:61-91`).
CI consumes the checked-in Python environment, not the user-global config, so
the issue's visibility conclusion follows.

**DISPOSITION.** `in-scope-for-#847` — no evidence correction needed.

### MEDIUM · ASSERTED; UNVERIFIABLE (no network) · macOS hosted runners have no container runtime, with “0 Docker mentions in 261 lines vs 5” · `gh-issue-847.md:50`

**EVIDENCE.** No report in the supplied 44-file corpus contains the claimed
261-line / 0-vs-5 measurement or a captured macOS runner-readme probe. An
unbounded same-corpus search for `0 docker mentions|261 lines` returned 0;
the broader `macos.{0,80}(docker|container runtime)|(?:docker|container
runtime).{0,80}macos|261|runner-images` search found only Ubuntu runner-image
research (`2026-08-30-codex-research-736.md:98-116`), not the claimed macOS
measurement. Control arm with the identical report-path/search shape for
`subaction/matrix` returned 39 lines. The Rosetta half is locally
supported—image execution follows the selected image/platform, and the repo pin is `DOTFILES_PLATFORM`
(`2026-08-30b-opus-cold-review-d8fca05.md:58-83`)—but it does not establish the
GitHub-hosted-runner premise. The relevant live runner-image docs cannot be
fetched in this offline audit, so that external truth is **UNVERIFIABLE (no
network)** rather than guessed.

**DISPOSITION.** `in-scope-for-#847` — attach the missing captured source/report
or re-run the readme measurement with network access before using this as a
design exclusion.

### LOW · GROUNDED · `python-on-whales` is the viable wrapper candidate; docker-py, aiodocker, and dockertown are ruled out · `gh-issue-847.md:51`

**EVIDENCE.** The coverage report records the per-library measurements and the
independent null search: python-on-whales has first-class buildx/bake support;
docker-py and aiodocker expose the wrong API layer; dockertown is a stale fork;
and independent discovery found no better library
(`2026-08-30b-SOURCE-COVERAGE.md:175-217`). The synthesis preserves the same
four-way verdict (`2026-08-30b-SYNTHESIS.md:420-425`). Upstream project
currency is **UNVERIFIABLE (no network)**, but the issue accurately summarizes
the completed corpus research.

**DISPOSITION.** `in-scope-for-#847` — no evidence correction needed; any later
adoption still requires a live currency refresh.

## Known-imperfect things — 6 claims

### LOW · GROUNDED · CI deselects the `image_exec` tests · `gh-issue-847.md:55`

**EVIDENCE.** `pytest.ini:6-15` declares `image_exec` and makes the default
selection `not image_exec and not codex_exec`. The CI pytest step deliberately
passes no replacement marker expression and explains why at
`.github/workflows/ci.yml:227-237`. The issue's `ci.yml:233-237` citation is
narrow but points to the decisive comment and command.

**DISPOSITION.** `in-scope-for-#847` — grounded; widen the CI line citation for
retrieval precision.

### LOW · GROUNDED · Two exec tests fail because they inherit `gcc_latest=True` · `gh-issue-847.md:56`

**EVIDENCE.** Both call sites omit `gcc_latest`
(`tests/test_image_smoke_exec.py:221-232`,
`tests/test_image_smoke_exec.py:240-250`), so they inherit the builder's `True`
default (`python/src/dotfiles_setup/image.py:833-840`). The emitted script then
requires `/opt/gcc-latest/bin/g++` whenever that flag is true
(`python/src/dotfiles_setup/image.py:617-624`). The session independently
measured that the image used on this arm64 host is `linux/arm64` and that the
test runner supplies no platform override
(`2026-08-30b-opus-cold-review-d8fca05.md:58-83`). I did not rerun the Docker
exec tests in this read-only pass; the failure mechanism is nonetheless fixed
by shipped source plus the measured image architecture, rather than merely by
the tests' names.

**DISPOSITION.** `in-scope-for-#847` — grounded; the eventual repair belongs in
a sibling implementation ticket.

### LOW · ASSERTED (cause only), numeric values UNVERIFIED-INHERITED · Hook latency is about 0.27s versus 0.094s · `gh-issue-847.md:57`

**EVIDENCE.** A report records a warm same-shell comparison of `0.270s` for the
new `uv run --project python ...` invocation and `0.094s` for the former
`mise exec -- ...` invocation
(`2026-08-30c-opus-cold-review-graphify-2.md:166-172`). Thus the issue's
`~0.28s` is a loose approximation of a measured `0.270s`. I did not re-time it:
the available `uv run` path attempted cache/environment initialization, which
would violate this audit's read-only boundary. The numbers are therefore
**UNVERIFIED-INHERITED in this pass**, not fresh measurements. The causal
attribution is **ASSERTED**, however: the repo documents that the two commands
also resolve different Graphify versions (`scripts/graphify-hook-guard.sh:11-14`;
`.claude/rules/graphify-first.md:14-21`), so the comparison does not hold the
binary constant and cannot isolate launcher overhead. The removed builder stamp
is not a measured arm in that benchmark either.

**DISPOSITION.** `in-scope-for-#847` — retain the observed timings, cite
`0.270s` exactly or label the rounding, and remove the causal sentence unless a
same-version control arm is measured.

### LOW · GROUNDED · Default-budget Graphify queries can return truncation errors · `gh-issue-847.md:58`

**EVIDENCE.** The wrapper default is 2,000 tokens and is always passed to the
CLI (`python/src/dotfiles_setup/graphify.py:31`,
`python/src/dotfiles_setup/graphify.py:287-309`); any `TRUNCATED:` line becomes
an error (`python/src/dotfiles_setup/graphify.py:352-370`). I freshly ran the
live checkout's pinned wrapper without changing files. A broad question
returned rc 3 with `TRUNCATED: showing 48 of 209 nodes (~2000-token budget),
161 cut`; the narrow control question `What does graphify_health do?` also
returned rc 3 with `TRUNCATED: showing 55 of 98 nodes (~2000-token budget), 43
cut`. The corpus search alone had no supporting runtime receipt: searching all
44 reports for `truncat` produced five hits, while the same-shape control search
for known-present `subaction|matrix` produced 39. The claim is grounded by the
fresh probe, not inherited from those five unrelated hits.

**DISPOSITION.** `in-scope-for-#847` — grounded; record a durable command receipt
before using the exact cut counts outside this audit.

### LOW · GROUNDED · The SessionStart currency nudge names a nonexistent task · `gh-issue-847.md:59`

**EVIDENCE.** The installed shared engine hardcodes `mise run kb-currency` in
its missing, malformed, and stale-cache messages
(`python/.venv/lib/python3.14/site-packages/kb_setup/currency/baseline.py:140-154`,
`python/.venv/lib/python3.14/site-packages/kb_setup/currency/baseline.py:227-233`).
The repo instead defines `[tasks.tool-currency]` and
`[tasks.tool-currency-check]` (`mise.toml:585-601`). Negative-search control:
the same exact-section search found both known-present task headers, then found
zero exact `[tasks.kb-currency]` headers; the `kb-currency` token at
`mise.toml:600` is only a comment.

**DISPOSITION.** `in-scope-for-#847` — the summary is grounded; parameterizing
the shared nudge is a sibling implementation ticket.

### LOW · GROUNDED · Strict hook mode and its TTL are available but deliberately unset · `gh-issue-847.md:60`

**EVIDENCE.** Installed Graphify reads `GRAPHIFY_HOOK_STRICT`
(`python/.venv/lib/python3.14/site-packages/graphify/cli.py:516-525`) and the
exact TTL name `GRAPHIFY_HOOK_STRICT_TTL`
(`python/.venv/lib/python3.14/site-packages/graphify/cli.py:540-546`). The repo
hook describes both as environment configuration
(`scripts/graphify-hook-guard.sh:16-19`). Negative-search control: the exact
strict-variable search returned zero entries in `.claude/settings.json:2-10`,
while the same-shaped exact search found the known-present
`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` at `.claude/settings.json:6`.

**DISPOSITION.** `in-scope-for-#847` — grounded; enabling strict mode would be a
separate operator decision.

## Question 2 — is the enumeration itself the right space? (load-bearing claims #847 omits)

### HIGH · The `.agents` installer-clobber hazard is absent from #847 · `2026-08-30c-graphify-upgrade-research.md:107-123`

**EVIDENCE.** The current `.agents/skills/graphify/SKILL.md` is a 1,043-byte
repo-authored redirector, not Agents-platform installer output; the package
payload differs by 730 lines, and a raw `graphify install --project --platform
agents` would silently replace it
(`2026-08-30c-graphify-upgrade-research.md:107-123`). That fact directly
constrains the issue's all-three-platform decision (`gh-issue-847.md:39`) but is
not recorded in any issue bullet. Negative-search control: unbounded
`rg -i 'clobber|redirector' gh-issue-847.md` returned 0, while the same issue
search for the known-present `platforms.*claude` returned line 39.

**DISPOSITION.** `ticket recommendation` — add the preservation requirement to
#847's Task 2 acceptance criteria; implement the backup/diff strategy in the
Graphify upgrade ticket.

### MEDIUM · Stale `graphify-update` prose still promises the removed stamp and impossible detection · `mise.toml:736-744`

**EVIDENCE.** The task description says it stamps the builder version and lets
health catch a graph built by the wrong binary (`mise.toml:736-744`). The final
rule says that exact inference is impossible and that the stamp was removed
(`.claude/rules/graphify-first.md:23-41`); production explains the same removal
(`python/src/dotfiles_setup/graphify.py:163-177`). #847 records only the corrected
rule conclusion (`gh-issue-847.md:41`), not the contradictory surviving operator
surface. Negative-search control: the exact stale phrases returned 0 in the
issue, while `runtime stamp` found the known-present line 41.

**DISPOSITION.** `ticket recommendation` — #847 should warn that the honesty fix
is incomplete; correcting the task prose belongs in the #846 follow-up or a
sibling documentation ticket.

### MEDIUM · Buildx binary selection is unpinned, and the corpus's six-site count misses a seventh CI site · `.github/workflows/build-publish.yml:232`

**EVIDENCE.** The synthesis identifies unpinned buildx resolution as a migration
risk and reports six `setup-buildx-action` sites
(`2026-08-30b-SYNTHESIS.md:326-340`). Fresh unbounded code search at fixed main
found **seven** action call sites: six in `build-publish.yml` at lines 232, 384,
491, 614, 1025, and 1142, plus `.github/workflows/ci.yml:445`. The action itself
is commit-pinned, but none of those steps supplies its `version` input; in the
seven matched step contexts, the same-shaped control search found all seven
`uses:` lines and zero `version:` lines. #847 contains no `setup-buildx`,
`buildx itself`, or `unpinned` mention; control search for the known-present
`bake` term finds `gh-issue-847.md:36,46,69,93,98`. Current upstream buildx
resolution is **UNVERIFIABLE (no network)**, but the repo's unpinned input and
seven-site cardinality are locally measurable.

**DISPOSITION.** `ticket recommendation` — record this as an acceptance
constraint for any Bake migration, and audit all seven sites in the sibling
implementation ticket.

## Question 3 — Q-SCOPE: is each finding in scope for #847, or a sibling ticket?

Each of the 22 claim findings carries its own disposition. Corrections to the
summary's truth status, wording, arithmetic, or citations are
`in-scope-for-#847`; actual code/config repairs are sibling tickets. The three
omitted premises above are `ticket recommendation` because #847 should preserve
them as constraints, while the Graphify and Bake implementation owners should
perform the mutations.

## Summary — disposition counts

- **15 GROUNDED:** one shipped row (#845), five operator decisions, four
  overturned findings, and five known-imperfect bullets.
- **4 ASSERTED:** #846's auto-merge subclaim, Graphify “full lifecycle” scope,
  the hook-latency causal attribution, and the macOS-runner premise/number. The
  last is also **UNVERIFIABLE (no network)**.
- **3 CONTRADICTED:** #841's “+3” repair count, the “adopt both at once” Bake
  timing decision, and the AGENTS cap arithmetic/units. Each retains a grounded
  core but its issue wording is wrong.
- **3 load-bearing omissions:** the `.agents` clobber hazard, stale stamp prose,
  and unpinned buildx across seven shipped call sites.

The highest-risk handoff error is the Bake timing inversion: #847 would send a
spec directly toward integration that the completed synthesis says to defer
until a real second base-OS axis exists
(`2026-08-30b-SYNTHESIS.md:380-397`). The highest-risk missing premise is the
`.agents` clobber hazard (`2026-08-30c-graphify-upgrade-research.md:107-123`).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues
  #847/#845/#841, PRs #844/#846/#837, the shipped source (`AGENTS.md`, `pytest.ini`, `.github/workflows/ci.yml`,
  `mise.toml`, `docker-bake.hcl`, `scripts/graphify-hook-guard.sh`,
  `.devcontainer/mise-system.toml`) and the 44-report corpus under
  `docs/research/kb/reports/agents/`, read across both the `origin/main` worktree and the
  live PR #846 checkout.

_None other consulted directly in this pass — all verification was against this repo's own
corpus, prefetched issue/PR snapshots, and shipped code; no external repo source or docs
were fetched._
