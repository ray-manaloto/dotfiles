# Audit C — unexecuted scope

## Audit boundary and method

This is a read-only audit of the 44-report answer set named by issue #847: 41
`2026-08-30*.md` reports at `origin/main` plus the three
`2026-08-30c-*.md` reports on PR #846. The corpus split and the required
starting reports are recorded in `gh-issue-847.md:62-71`; a direct `rg --files ... | rg '/2026-08-30.*\\.md$' | wc -l` control counted 41 and the equivalent
PR-checkout command counted 3.

Commitments were derived from all 44 report bodies plus issue #847 using two
mechanical passes rather than impression. Pass 1 used `rg -n -i` over the same
45-file array for the commitment-language family `recommend(ed|ation)`, `next step`, `TODO`, `follow-up`, `candidate ticket`, `should`, `must`, `need to`,
`worth ... follow-up/investigating/adopting`, `pending`, `defer`, `open item/question/thread`, `supersede`, `prototype`, `ticketed`, and `unticketed`.
It returned **216 hit lines in 38 files**. Pass 2 rescanned every zero-hit report
with the broader family `must|need|worth|open|pending|defer|future|adopt|replace|verdict|conclusion`; this matters because, for example, the inline `aioregistry`
follow-up is prose rather than a TODO (`main-audit/docs/research/kb/reports/agents/2026-08-30b-indep-pylib-discovery.md:67-82`). The same `rg -n -e` command
shape over the same files, using the known-present control `^## GitHub repos touched`, returned **39 hits**. The source boundary itself is corroborated by
`gh-issue-847.md:64-71`.

The 216 textual hits normalize to **39 semantic commitments**, which is the
cardinality of the answer set below: repeated copies of one obligation are
collapsed, while independently executable parts are split. The classifications
are **12 DONE, 11 TICKETED, and 16 DROPPED**. Explicitly retracted, rejected, or
precondition-not-yet-met alternatives are accounted for under “Enumeration
completeness” but are not counted as live commitments. Dispositions were checked
against `origin/main` at `1e6a368`, PR #846 at `6278d6c`, and the prefetched
open-issue/open-PR lists; no network source was used (`gh-issue-847.md:62-71`).

## Commitment inventory

### DONE (12)

LOW · DONE — leg-keyed Bake cache scopes (#839) shipped · `main-audit/docker-bake.hcl:33-40,143-162`
  EVIDENCE: `LEG` is a first-class Bake variable and both GHA cache directions
  interpolate it; the implementation/review receipt confirms commit `42adee2`
  (`main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:120-150`).
  DISPOSITION: in-scope-for-#847

LOW · DONE — the third non-blocking `ubuntu-26.04-arm` validation leg (#840) shipped with cache and manifest isolation · `main-audit/python/src/dotfiles_setup/platform_target.py:188-202,280-308,336-367`
  EVIDENCE: the validation row is `role="validate"`, nonblocking, and
  cache-ineligible; workflow consumers gate probes/stamps and filter the publish
  matrix (`main-audit/.github/workflows/build-publish.yml:478-485,818-821,878,1043-1048,1128-1140`).
  DISPOSITION: in-scope-for-#847

LOW · DONE — GCC 16.2 arm64 scoping and the five follow-on assumption fixes shipped in PR #844 · `main-audit/.devcontainer/mise-system.toml:63-68`
  EVIDENCE: the exact arm64-only pin is present; the expected-set filter, exact
  mise arch matching, empty-list behavior, conditional compiler probe, and
  shared expected-set derivation are present at
  `main-audit/python/src/dotfiles_setup/image.py:146-249,627-644,1085-1092`;
  issue #847 identifies the merged ref as `1e6a368` (`gh-issue-847.md:14,22-32`).
  DISPOSITION: in-scope-for-#847

LOW · DONE — the requested codex implementation/codex review routing for #839 and #840 actually ran · `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:120-180`
  EVIDENCE: the report records both implementations, settlements, and both
  same-family cold reviews; this resolves the earlier process question recorded
  at `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:45-50`.
  DISPOSITION: in-scope-for-#847

LOW · DONE — the 20-lane Bake/Python-library research and synthesis were completed · `main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:12-24`
  EVIDENCE: the tracker marks the source lanes complete and the synthesis exists
  with a concrete architecture and per-source reconciliation
  (`main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:134-217,399-429`). The tracker’s older unchecked “synthesis” box is stale, not evidence
  of an unexecuted synthesis (`main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:52-56`).
  DISPOSITION: in-scope-for-#847

LOW · DONE — PR #846 implements truthful Graphify links/edges schema and optional-receipt health · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify.py:102-113,145-209,224-243`
  EVIDENCE: the implementation accepts Graphify’s `links` schema, treats an
  absent dotfiles receipt as non-faulting, and states exactly which guarantees
  are absent. Issue #847 records PR #846 as open rather than merged
  (`gh-issue-847.md:15`).
  DISPOSITION: in-scope-for-#847

LOW · DONE — PR #846 adds the sanctioned Graphify rebuild/task route and rewrites the hook nudge to it · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify.py:373-440`
  EVIDENCE: `mise.toml` exposes query, health, and update tasks
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:723-746`), and
  the hook wrapper anchors the uv project to `CLAUDE_PROJECT_DIR`
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/scripts/graphify-hook-guard.sh:11-28`).
  DISPOSITION: in-scope-for-#847

LOW · DONE — the ineffective Graphify runtime stamp was removed and the remaining limitation was documented · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/graphify-first.md:14-41`
  EVIDENCE: the rule explains why builder identity is unknowable, and the Python
  health code contains no stamp read/write path
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify.py:163-177`). Same-shape code control: `git grep` for
  `runtime[_ -]stamp|builder[_ -]version` found only that explanatory prose,
  while `version drift|runtime_version` found live health code at
  `graphify.py:71,81,139,227`.
  DISPOSITION: in-scope-for-#847

LOW · DONE — `do-not.md` item 8’s safety rule was retained rather than weakened · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/do-not.md:34-43`
  EVIDENCE: the architect correction establishes that the earlier weakening was
  wrong and retracted (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-install-probe.md:5-59,607-612`).
  DISPOSITION: in-scope-for-#847

LOW · DONE — the local devcontainer default remains amd64 · `main-audit/docker-bake.hcl:28-31`
  EVIDENCE: the default `PLATFORM` is still `linux/amd64/v2`, matching the
  accepted decision in `gh-issue-847.md:38`.
  DISPOSITION: in-scope-for-#847

LOW · DONE — `docker/github-builder` remains ruled out; the custom Bake workflow remains authoritative · `main-audit/.github/workflows/build-publish.yml:238,390,709`
  EVIDENCE: production still calls pinned `docker/bake-action` in the custom
  workflow. Same-shape control: `git grep` over `.github`, `docker-bake.hcl`, and
  `python/` found zero `docker/github-builder` references but found the cited
  `docker/bake-action` calls; the ruling is recorded at `gh-issue-847.md:46-47`.
  DISPOSITION: in-scope-for-#847

LOW · DONE — strict/TTL Graphify hook machinery was deliberately not enabled · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:1-11`
  EVIDENCE: same-file, same-shape `git grep` found zero
  `GRAPHIFY_HOOK_(STRICT|TTL)` entries; the positive control
  `CLAUDE_PROJECT_DIR` found active hook configuration at
  `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:46,56,66,78`. This matches the explicit no-action decision in
  `gh-issue-847.md:60`.
  DISPOSITION: in-scope-for-#847

### TICKETED (11)

MEDIUM · TICKETED — adopt the base-OS permutation axis, descriptive all-axis tags, and the Bake `subaction/matrix` bridge together · `gh-issue-847.md:34-38,91-94`
  EVIDENCE: issue #847 carries the accepted action. It is not DONE: a
  same-scope code search found no `subaction/matrix`; the positive control found
  current `docker/bake-action` calls at
  `main-audit/.github/workflows/build-publish.yml:238,390,709`, and the current
  Python source still owns enumeration (`main-audit/python/src/dotfiles_setup/platform_target.py:336-367`). The action API’s current live documentation is
  UNVERIFIABLE (no network); the corpus evidence is the synthesis architecture
  at `main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:151-200`.
  DISPOSITION: in-scope-for-#847

HIGH · TICKETED — upgrade Graphify to 0.9.53, install claude+codex+agents skills, and complete the skill → mise task → Python lifecycle · `gh-issue-847.md:39-42,84,94`
  EVIDENCE: the repo pin is still 0.9.42
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/pyproject.toml:7-9`),
  health still hardcodes 0.9.42
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify.py:224-243`), and a tree listing finds `.agents` and
  `.claude` Graphify skills but no `.codex/skills/graphify`; the same-command
  positive control is `.agents/skills/graphify/.graphify_version` and
  `SKILL.md`. The complete procedure is documented at
  `main-audit/docs/research/kb/reports/agents/2026-08-30c-graphify-upgrade-research.md:450-532`.
  DISPOSITION: in-scope-for-#847

MEDIUM · TICKETED — supersede Dependabot PR #837 and disposition the still-open dependency PRs #822/#821 · `gh-open-prs.txt:2-4`
  EVIDENCE: #837 still proposes 0.9.48 while the operator chose 0.9.53
  (`gh-issue-847.md:42`); #822 and #821 are also still open work items. None is
  DONE at this snapshot.
  DISPOSITION: in-scope-for-#847

HIGH · TICKETED — stop predicting mise `os=` behavior on the host and ask mise in the image · `gh-open-issues.txt:2`
  EVIDENCE: dedicated open issue #845 carries the obligation; issue #847 records
  the prediction failures it replaces (`gh-issue-847.md:22-32,95`).
  DISPOSITION: in-scope-for-#847

MEDIUM · TICKETED — run the scoped mise OCI per-tool-layer pilot · `gh-open-issues.txt:4`
  EVIDENCE: dedicated open issue #838 carries the pilot; the originating
  requirements log records the explicit decision to track it separately
  (`main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:31-36`).
  DISPOSITION: in-scope-for-#847

MEDIUM · TICKETED — track LLVM 23 until upstream publishes the required suite · `gh-open-issues.txt:3`
  EVIDENCE: open issue #841’s title explicitly includes “track LLVM 23 blocked
  on upstream.” This supersedes the earlier report-state claim that LLVM had no
  ticket (`main-audit/docs/research/kb/reports/agents/2026-08-30-codex-adversarial-audit-recheck.md:59,77`).
  DISPOSITION: in-scope-for-#847

MEDIUM · TICKETED — run repository landing for #844 and, after merge, #846 · `gh-issue-847.md:14-18`
  EVIDENCE: #847 explicitly records both owed land operations; #846 remains an
  open PR in the prefetched snapshot (`gh-open-prs.txt:1`). The #844 half is
  independently corroborated: local `refs/heads/main` is still `7f2b85a`
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/refs/heads/main:1`)
  while `refs/remotes/origin/main` is `1e6a368`
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/refs/remotes/origin/main:1`).
  DISPOSITION: in-scope-for-#847

MEDIUM · TICKETED — perform the anti-loss audit, re-run grilling as needed, then spec/ticket every surviving thread · `gh-issue-847.md:75-98`
  EVIDENCE: this is the operative Task 1 → Task 2 contract of open issue #847;
  the present report executes only this audit axis, not the later external issue
  mutations.
  DISPOSITION: in-scope-for-#847

LOW · TICKETED — prototype the Bake matrix shape if construction would settle the design faster · `gh-issue-847.md:98`
  EVIDENCE: open issue #847 explicitly names this as the prototype candidate;
  no report claims the prototype already ran.
  DISPOSITION: in-scope-for-#847

HIGH · TICKETED — close, rather than merely document, the repo-pin/user-global Graphify version divergence · `gh-issue-847.md:49,94`
  EVIDENCE: the full-lifecycle/drift task in #847 carries it, while the PR branch
  still pins 0.9.42 and documents a user-global 0.9.53
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/graphify-first.md:14-41`). The originating report explicitly says the
  divergence should be closed (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:208-243`).
  DISPOSITION: in-scope-for-#847

LOW · TICKETED — retain hook latency as an owned performance issue · `gh-open-issues.txt:84`
  EVIDENCE: #536 is the dedicated open hook-latency issue; the session measured
  the new Graphify path at about 0.27s versus 0.094s
  (`main-audit/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify-2.md:166-172`) and #847 keeps it live
  (`gh-issue-847.md:57`).
  DISPOSITION: in-scope-for-#847

### DROPPED (16)

For every DROPPED item below I ran the same ticket search shape,
`rg -n -i -e '<item terms>' gh-open-issues.txt`. The positive control
`rg -n -i -e '#847' gh-open-issues.txt` returned `gh-open-issues.txt:1`.
Each finding names the zero-result term arm; the prefetched list contains only
open-issue titles, so a hidden mention in an unavailable issue body remains an
enumeration limitation discussed below.

For candidate follow-ups, an informational bullet in #847’s “known-imperfect”
section is not treated as the requested filing: that section calls `image_exec`
a candidate (`gh-issue-847.md:53-60`), while Task 2 separately names what is
actually scheduled for spec/ticket conversion (`gh-issue-847.md:89-98`). This
distinction is necessary to answer “was one ever filed?” rather than making the
answer tautologically yes because the audit summary mentioned it.

HIGH · DROPPED — CI still does not run `image_exec`, and no follow-up ticket was filed · `main-audit/pytest.ini:7,10-15`
  EVIDENCE: CI deliberately passes no marker override, preserving the deselect
  (`main-audit/.github/workflows/ci.yml:227-237`); the cold review warned that the
  #844 arch fix therefore has one local execution route only
  (`main-audit/docs/research/kb/reports/agents/2026-08-30b-opus-cold-review-round2.md:215-220`). Ticket arm
  `image_exec|smoke[- ]exec|exec test` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`. Merely calling it a “candidate follow-up ticket” in
  `gh-issue-847.md:55` is not the filing of that follow-up.
  DISPOSITION: ticket recommendation — sibling dotfiles CI ticket

HIGH · DROPPED — the two pre-existing tier-3 exec tests remain unfixed and unticketed · `main-audit/tests/test_image_smoke_exec.py:221-254`
  EVIDENCE: both still call `build_tier3_script` without overriding the
  pre-conda default identified by the session (`gh-issue-847.md:56`). Ticket arm
  `tier3|compiler substrate|wrong ref` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`.
  DISPOSITION: ticket recommendation — sibling dotfiles test-fix ticket

HIGH · DROPPED — the real production failure on the `ubuntu-26.04-arm` validation smoke was never investigated or ticketed · `main-audit/docs/research/kb/reports/agents/2026-08-30-fable-advisor-and-lane-reports-consolidated.md:171-184`
  EVIDENCE: the report calls the failure real and “worth investigating in a
  future session.” Ticket arm `ubuntu-26\.04-arm|validation smoke` returned zero;
  the `#847` control returned `gh-open-issues.txt:1`.
  DISPOSITION: ticket recommendation — sibling dotfiles CI investigation

MEDIUM · DROPPED — `python-on-whales` was accepted as a legitimate replacement candidate but never evaluated in-repo or ticketed · `main-audit/docs/research/kb/reports/agents/2026-08-30b-pylib-python-on-whales.md:219-243`
  EVIDENCE: issue #847 carries the research conclusion but no work item
  (`gh-issue-847.md:51`). Same-scope code arm `python-on-whales` returned zero
  under `python/`; control `subprocess` found current hand-rolled calls, including
  `main-audit/python/src/dotfiles_setup/image.py:251-252,954`. Ticket arm
  `python-on-whales|buildx subprocess` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`.
  DISPOSITION: ticket recommendation — sibling dotfiles prototype/evaluation

LOW · DROPPED — the `aioregistry` follow-up grep was never run to settle whether the repo has a problem it solves · `main-audit/docs/research/kb/reports/agents/2026-08-30b-indep-pylib-discovery.md:67-82`
  EVIDENCE: the lane explicitly says the grep is still needed and adoption is
  conditional. Same-scope code arm `aioregistry` returned zero while control
  `subprocess` found current subprocess code at
  `main-audit/python/src/dotfiles_setup/image.py:251-252,954`. Ticket arm
  `aioregistry|manifest inspection` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`.
  DISPOSITION: ticket recommendation — sibling dotfiles research ticket only if the grep proves a call site

MEDIUM · DROPPED — the SessionStart currency remediation still points users at nonexistent `kb-currency`, with no owner · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:188-202`
  EVIDENCE: dotfiles itself exposes `tool-currency` and invokes
  `tool-currency-check` (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:72-80`), so the report’s proposed choices are a shared-
  engine message fix or a local alias. Ticket arm `kb-currency|tool-currency|dead pointer` returned zero; the `#847` control returned `gh-open-issues.txt:1`.
  DISPOSITION: ticket recommendation — sibling `ray-manaloto/knowledge-base` engine-message ticket, or explicitly choose a dotfiles alias

MEDIUM · DROPPED — the Graphify query default still truncates broad questions and no budget-tuning ticket exists · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify.py:287-304,313-358`
  EVIDENCE: the CLI default remains 2000
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/main.py:874-880`), while issue #847 records the measured truncation
  (`gh-issue-847.md:58`). Ticket arm `graphify-query|query budget|truncation`
  returned zero; the `#847` control returned `gh-open-issues.txt:1`.
  DISPOSITION: ticket recommendation — sibling dotfiles tuning/evidence ticket

MEDIUM · DROPPED — the Graphify hook still lacks a real stdin/subprocess integration test · `main-audit/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify-2.md:108-125`
  EVIDENCE: the review proved the route works today but that every test stubs
  `_run`, so the silent-failure path remains unguarded. Ticket arm `stdin|hook integration` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`. Existing #536 covers latency, not this integration
  contract (`gh-open-issues.txt:84`).
  DISPOSITION: in-scope-for-#847 — include in the Graphify lifecycle spec

HIGH · DROPPED — the promised Graphify instruction corrections did not land: `graphify --watch` is still wrong and safe generic install is still conflated with dangerous platform install · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/do-not.md:34-43`
  EVIDENCE: the doc audit requires `graphify watch <path>`
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:348-362`), and the corrected install
  probe requires naming the two command shapes
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-install-probe.md:656-672`). Ticket arm
  `graphify --watch|install --platform|safe generic install` returned zero; the
  `#847` control returned `gh-open-issues.txt:1`.
  DISPOSITION: in-scope-for-#847 — fold into the Graphify upgrade spec

HIGH · DROPPED — PR #846 removed the runtime stamp but left `mise graphify-update` promising to write and verify it · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:736-746`
  EVIDENCE: the task description still says “stamp the graphify version” and its
  comment says health can catch a graph built by the wrong binary, directly
  contradicting the corrected rule
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/graphify-first.md:23-41`) and issue decision (`gh-issue-847.md:41`). Ticket arm
  `runtime stamp|builder version|wrong binary` returned zero; the `#847` control
  returned `gh-open-issues.txt:1`.
  DISPOSITION: in-scope-for-#847 — correct before/with PR #846 landing

LOW · DROPPED — the generated Graphify skill’s apparent 714-line/41,300-byte budget violation was never settled · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:335-344`
  EVIDENCE: the report supplies the exact settling probe but labels it
  NEEDS-VERIFICATION. Ticket arm `graphify skill|skill budget|generated skill`
  returned zero; the `#847` control returned `gh-open-issues.txt:1`. Open issue
  #640 is about a different `md_size_budget` dependency-pin defect
  (`gh-open-issues.txt:57`), so it is not a carrier for this question.
  DISPOSITION: ticket recommendation — sibling cross-repo budget-enforcement investigation

LOW · DROPPED — the sibling knowledge-base private Graphify fork and wrapper layer were flagged for scrutiny but never examined · `main-audit/docs/research/kb/reports/agents/2026-08-30c-graphify-upgrade-research.md:173-197`
  EVIDENCE: the report explicitly says it did not read the wrapper files and
  leaves the supply-chain/schema question open. Ticket arm `private fork|graphify wrapper|supply chain` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`. Existing #712’s title is only “Promote a Graphify
  dependency and execution boundary” (`gh-open-issues.txt:34`); its body is
  unavailable, so exact coverage is UNVERIFIABLE rather than assumed.
  DISPOSITION: ticket recommendation — sibling `ray-manaloto/knowledge-base` review

HIGH · DROPPED — the knowledge-base build-receipt writer still rejects Graphify’s real `links` schema and no follow-up owns it · `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-opus-cold-review-graphify.md:83-105`
  EVIDENCE: the review identifies the cross-repo half-fix and explicitly assigns
  the KB-side repair to a follow-up ticket. Ticket arm `receipt writer|links edges` returned zero; the `#847` control returned `gh-open-issues.txt:1`.
  Existing #712 exact coverage is UNVERIFIABLE because only its title is
  available (`gh-open-issues.txt:34`).
  DISPOSITION: ticket recommendation — sibling `ray-manaloto/knowledge-base` defect

MEDIUM · DROPPED — the original non-Renovate tool/compiler currency audit has no execution receipt or ticket · `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:7-18`
  EVIDENCE: the later requirements audit calls this scope partial and says the
  general audit has no trace
  (`main-audit/docs/research/kb/reports/agents/2026-08-30-codex-audit-missed-requirements.md:7-11,81`). The pending PR portion
  is separately preserved by #822/#821 (`gh-open-prs.txt:3-4`); the dropped part
  here is specifically “anything not covered by Renovate.” Ticket arm
  `dependency audit|non-Renovate` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`.
  DISPOSITION: in-scope-for-#847 — recover or explicitly narrow the original currency audit

MEDIUM · DROPPED — the requirement to verify that `last30days` actually ran was never discharged · `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:12-19`
  EVIDENCE: the audit could neither verify nor refute invocation from the issue
  corpus (`main-audit/docs/research/kb/reports/agents/2026-08-30-codex-audit-missed-requirements.md:19,77`). Therefore this finding
  is a dropped **provenance receipt**, not a claim that the tool definitely did
  not run. Ticket arm `last30days invocation|research provenance` returned zero;
  the `#847` control returned `gh-open-issues.txt:1`.
  DISPOSITION: in-scope-for-#847 — resolve from the raw session transcript or label UNVERIFIED permanently

LOW · DROPPED — the three named `ubuntu-26.04-arm` adopter citations never reached the durable spec/issue record · `main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:21-24`
  EVIDENCE: the requirements audit names Pumpkin-MC/Pumpkin, google/binexport,
  and rust-lang/libc as missing from the published issues
  (`main-audit/docs/research/kb/reports/agents/2026-08-30-codex-audit-missed-requirements.md:27,79`). Ticket arm
  `Pumpkin|binexport|rust-lang` returned zero; the `#847` control returned
  `gh-open-issues.txt:1`.
  DISPOSITION: in-scope-for-#847 — evidence repair, not a code ticket

## Enumeration completeness

### Is this the right space?

**Yes for the supplied answer set; no for the unknowable full-session space.**
The 39 units cover every mechanically surfaced live obligation in the 44
reports and issue #847, including inline asides that a TODO-only grep misses.
That is the user-defined corpus boundary (`gh-issue-847.md:62-71`). It is not a
proof that the 44 reports themselves are lossless: the requirements log admits
it was reconstructed from conversation memory and that its auditing lane had no
original transcript (`main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:1-3`).

The following commitment-bearing places were **not** in the grep domain:

- **Raw session JSONL, tool calls, and compaction boundaries — UNVERIFIED.** The
  report corpus itself says the `last30days` question requires a transcript/tool-
  call check outside its issue-only audit (`main-audit/docs/research/kb/reports/agents/2026-08-30-codex-audit-missed-requirements.md:19`). A command may have
  been promised or run without a durable report sentence.
- **Lane dissent or follow-up messages never copied into a report —
  UNVERIFIED.** The architect log’s lane did not receive the original
  conversation (`main-audit/docs/research/kb/reports/agents/2026-08-30-architect-session-requirements-log.md:1-3`); any objection left
  only in agent chat is outside the answer set.
- **`.agent/` notes, command-audit output, scratchpads, and session handoffs —
  UNVERIFIED.** The active settings prove a SessionEnd command-audit file is a
  real recording surface (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:84-90`), but those artifacts were not among the 44 named
  reports.
- **PR descriptions, reviews, and comments — UNVERIFIED.** The supplied PR file
  contains only four title/state rows (`gh-open-prs.txt:1-4`); bodies and review
  threads for #846, #844, #837, #822, and #821 were not supplied.
- **Issue bodies/comments other than #847, plus closed issues — UNVERIFIED.**
  `gh-open-issues.txt` is title-only (`gh-open-issues.txt:1-4`), so an item
  hidden in #712’s body or in comments cannot honestly be called absent. This
  is why the DROPPED findings say “no open title carrier,” and why #712 is not
  guessed to cover the KB Graphify items (`gh-open-issues.txt:34`).
- **CI logs and landing/ship receipts not quoted by a report — UNVERIFIED.** The
  issue records current landing debt (`gh-issue-847.md:14-18`), but no complete
  historical action-log corpus was provided.

Keyword enumeration also has two structural traps demonstrated inside this
corpus. First, stale state text can lie: SOURCE-COVERAGE leaves synthesis
unchecked (`main-audit/docs/research/kb/reports/agents/2026-08-30b-SOURCE-COVERAGE.md:52-56`) even though the synthesis exists and
contains the recommendation (`main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:134-217`). Second, inline conditional prose carries
real scope without a conventional marker, as the `aioregistry` “worth a
follow-up grep” passage demonstrates (`main-audit/docs/research/kb/reports/agents/2026-08-30b-indep-pylib-discovery.md:67-82`). The second regex pass and
manual normalization are therefore part of the derivation, not optional polish.

### Deliberately excluded from the 39 live commitments

- The earlier recommendation to weaken `do-not.md` item 8 was explicitly
  retracted after the 161-line help was read correctly
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-install-probe.md:5-40,607-612`). Its final safety
  decision is counted as DONE; the retracted opposite is not a live commitment.
- The unflagged generic Graphify install was deliberately not run against the
  real home (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-30c-graphify-install-probe.md:55-56,630-634`). That
  is a safety boundary, not lost execution scope.
- The synthesis’s “wait until the wider set materializes” timing recommendation
  (`main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:380-397`)
  was superseded by the later operator decision to do both Bake axes together
  (`gh-issue-847.md:34-38`); only the final accepted action is counted.
- The older “mise OCI is not worth future exploration” position is superseded
  by the scoped pilot carried in #838 (`gh-open-issues.txt:4`), and the partial
  `docker/github-builder` direction is superseded by the final rejection
  (`gh-issue-847.md:46-47`).
- Future validation-leg promotion is explicitly conditional and “decided later
  and out of scope” (`main-audit/docs/research/kb/reports/agents/2026-08-30-codex-research-cache-hybrid.md:72-74`). Its trust precondition has
  not been declared met, so it is not a presently executable commitment.
- External documentation’s own normative “must/should” statements, quoted in
  research reports, are evidence about upstream behavior rather than promises
  this session made. Counting them would inflate the answer set with upstream
  authors’ obligations; the per-source separation is visible in the synthesis
  table (`main-audit/docs/research/kb/reports/agents/2026-08-30b-SYNTHESIS.md:399-429`).

## GitHub repos touched

- `ray-manaloto/dotfiles` — both shipped refs, the 44-report corpus, issue #847,
  and the prefetched open issue/PR state.

No external repository source or live documentation was fetched. Upstream
claims were read only through the committed report corpus; their current live
state is therefore UNVERIFIABLE (no network), not silently refreshed.
