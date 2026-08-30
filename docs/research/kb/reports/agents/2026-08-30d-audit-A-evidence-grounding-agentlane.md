# Audit A — evidence grounding: `What shipped`

## Method

**Fixed corpus only.** I read the issue body, the specified 41 `main` reports,
the three `2026-08-30c-*` PR-branch reports, `main-audit` at its recorded
`origin/main` ref, and the supplied PR-branch checkout at `6278d6c`. The
required starting sources establish both the research reconciliation boundary
(`2026-08-30b-SYNTHESIS.md:1-13`) and its one-lane-per-source coverage model
(`2026-08-30b-SOURCE-COVERAGE.md:1-10,12-54`).

**Verdicts.** `GROUNDED` means the fixed corpus directly supports the stated
fact; `ASSERTED` means the issue states a tracker fact but the corpus has no
independent tracker record; `CONTRADICTED` means fixed code/report evidence
conflicts with the wording. No network or GitHub query was used.

**Negative-search control.** I ran an unbounded exact-ID search across all 44
specified reports for `#845` and `#846`; it returned no hits. The identical
search shape for `#841` returned multiple hits, including the synthesis
status note (`2026-08-30b-SYNTHESIS.md:8-13`), so the null is a corpus result,
not a broken search. It cannot establish current GitHub state.

## Domain

This pass covers exactly the three rows in issue #847's `What shipped` table
(`gh-issue-847.md:10-18`). It distinguishes local Git-ref/code evidence from
live PR/issue state; it does not assess the later Task 1/Task 2 claims.
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

### MEDIUM · ASSERTED · PR #846 is “open, auto-merge armed” · `gh-issue-847.md:15`

**EVIDENCE.** The supplied branch is locally and remotely pinned to `6278d6c`
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

**DISPOSITION.** The implementation/rule claim is **GROUNDED with the
`mise.toml` caveat**. The PR number, `open` state, and auto-merge setting are
**ASSERTED**: no independently recorded #846 tracker state exists in the fixed
corpus (controlled negative search documented above). Do not run the stated
future `land` step from this row alone; verify the live PR first.

### LOW · ASSERTED · Issue #845 is open and `ready-for-agent` for the mise `os=` reimplementation debt · `gh-issue-847.md:16`

**EVIDENCE.** The underlying technical debt is **GROUNDED**: production code
parses TOML and predicts whether a tool should be installed from a host-side
`arch` argument (`python/src/dotfiles_setup/image.py:173-192`). Its own
contract admits the boundary: mise may apply backend-level platform
restrictions that this parsed-entry model cannot observe
(`python/src/dotfiles_setup/image.py:194-202`). The issue describes the
intended next step as stopping that prediction (`gh-issue-847.md:91-96`).

The exact #845 identifier, its existence, its `open` status, and its label are
not independently evidenced in any of the 44 supplied reports. This is the
controlled null from the Method: the same unbounded search did find #841 in
the synthesis landing note (`2026-08-30b-SYNTHESIS.md:8-13`), so the absence is
not a bounded-search artifact; it still cannot prove a GitHub issue absent or
its state changed.

**DISPOSITION.** The debt topic is **GROUNDED**; the tracker reference/state is
**ASSERTED**. Treat #845's status as a live-verification prerequisite, and do
not infer its scope or readiness from issue #847 alone.
GROUNDED · "CI does not run the image_exec tests. Marked and deselected (pytest.ini, ci.yml:233-237)" · pytest.ini:15; .github/workflows/ci.yml:227-237
  EVIDENCE: `pytest.ini:15` "addopts = -m \"not image_exec and not codex_exec\""; matching
  marker doc at `pytest.ini:7` "image_exec: containerized real-toolchain exec test...".
  `.github/workflows/ci.yml` "Run pytest" step spans lines 227-237 (name at 227, run at
  237) — issue cites "233-237" which is the tail half of that same step (the explanatory
  comment block + run line), not the step's start. Substance fully correct; line-range
  citation is slightly narrow (misses the step's `- name:` header at 227) but points at the
  right step and the right file.
  DISPOSITION: in-scope-for-#847 (citation precision only, not worth blocking)

GROUNDED · "Two pre-existing exec tests fail: test_tier3_compiler_substrate_compiles_against_dev, test_tier3_ref_pin_fails_on_wrong_ref — never override gcc_latest's default" · tests/test_image_smoke_exec.py:161,180
  EVIDENCE: both function names exist verbatim at those approximate lines in
  `tests/test_image_smoke_exec.py` (confirmed via grep on live checkout). Did not actually
  RUN the exec suite in this pass (it needs Docker + the :dev image, out of scope for a
  read-only document audit — consistent with why CI itself deselects it). Function
  existence is grounded; the "currently failing" claim is not independently re-executed
  here and rests on the session's own report of running it locally.
  DISPOSITION: in-scope-for-#847, with the caveat that re-running the exec suite before
  Task 2 begins would fully close this out (currently GROUNDED on structure, unverified on
  live behavior in this pass — real-integration-evidence.md applies).

GROUNDED · "Hook costs ~0.28s per tool call, up from ~0.094s. From uv run --project python, not the (removed) stamp" · 2026-08-30c-opus-cold-review-graphify-2.md:165-170 (main-worktree location; NOT one of the 3 PR-branch files named in the shared context — see corpus-discrepancy note above)
  EVIDENCE: report states "new `uv run --project python dotfiles-setup graphify hook-guard
  search` = 0.270s total; previous `mise exec -- graphify hook-guard search` = 0.094s".
  0.094s matches exactly; 0.270s rounds to #847's "~0.28s" (a rounding choice, not an
  error — 0.270 truncated/rounded up reads oddly as 0.28 rather than 0.27, worth a
  one-word fix but not a grounding failure). Attribution ("from moving... to uv run
  --project python, not from the stamp") matches the report's own framing (it compares
  the invocation mechanism, `mise exec` vs `uv run --project`, not stamp-presence).
  DISPOSITION: in-scope-for-#847 — minor: correct "0.28s" to "0.27s" to exactly match the
  source measurement (probes-need-a-control-arm.md discipline: don't let a re-stated
  number silently drift from its source).

ASSERTED (LOW) · "mise run graphify-query hits a truncation error at the task's default budget for broad questions" · no report citation found
  EVIDENCE: grepped the full corpus (both locations) for "truncat" — 5 hits, none of which
  document a reproduced truncation event from running `mise run graphify-query` this
  session. The closest hit (`2026-08-30c-opus-cold-review-graphify.md:154`,
  `QueryResult.truncated ... is never set to True`) is about a DIFFERENT code path — the
  `dotfiles_setup.graphify` health-check wrapper's own unused field — not the `graphify
  query` CLI's runtime truncation behavior that #847 describes.
  CONTROL ARM: the same grep found 5 real hits (not 0), so the search mechanism
  discriminates; it simply didn't find a hit that supports THIS specific claim.
  DISPOSITION: in-scope-for-#847 — this may be a genuine operator-observed fact from
  live use of `mise run graphify-query` during the session (plausible and specific: "at
  the task's default budget for broad questions" reads like a lived observation, not an
  invention) but it has no report behind it. Recommend either citing where it was observed
  (a transcript excerpt/receipt) or reproducing it once (`mise run graphify-query -- "<a
  broad question>"`) before Task 2 relies on it for budget-tuning scope.

GROUNDED · "SessionStart currency check tells this repo to run `mise run kb-currency` — no such task exists" · python/.venv/lib/python3.14/site-packages/kb_setup/currency/baseline.py:144,153,233; docs.py:145; mise.toml (no `[tasks.kb-currency]` entry, only a same-named comment at line 600)
  EVIDENCE: `kb_setup/currency/baseline.py` (the shared engine this repo's
  `tool-currency-check` task delegates to) hardcodes the nudge string
  `"...run `mise run kb-currency`"` in 4 places. `mise.toml` was grepped for "kb-currency"
  — the only hit is a comment ("Mirrors the KB repo's kb-currency-check task") at line 600;
  no `[tasks.kb-currency]` block exists. This repo's real tasks are `tool-currency` and
  `tool-currency-check` (confirmed via `[tasks.tool-currency]`/`[tasks.tool-currency-check]`
  blocks). Exact match to #847's claim.
  DISPOSITION: in-scope-for-#847, and this is a real actionable defect worth a follow-up
  ticket against the shared `kb_setup.currency` engine (the hardcoded string should
  probably be parameterized per-repo rather than always naming the KB repo's task name) —
  #847 correctly flags it as "known-imperfect," and Task 2 or a new ticket should own
  the actual fix.

GROUNDED · "GRAPHIFY_HOOK_STRICT / _TTL exist and are settable from settings.json's env block. Deliberately not enabled" · scripts/graphify-hook-guard.sh:16-18
  EVIDENCE: `scripts/graphify-hook-guard.sh:16-18` "Advisory, soft mode. Strict mode
  (GRAPHIFY_HOOK_STRICT/_TTL, graphify/cli.py) is an env var, not a code change — set it
  in .claude/settings.json's env block if ever needed." Verbatim match to #847's phrasing.
  DISPOSITION: in-scope-for-#847
## Question 2 — is the enumeration itself the right space? (load-bearing claims #847 omits)

HIGH · The `.agents/skills/graphify/SKILL.md` clobber risk is load-bearing for Task 2 item 2
and has no bullet anywhere in #847 · 2026-08-30c-graphify-upgrade-research.md:107-125 (PR
branch)
  EVIDENCE: the same report that grounds #847's "graphify platforms: claude+codex+agents"
  decision also found: `.agents/skills/graphify/SKILL.md` in this repo today is a
  **hand-authored redirector** (1043 bytes), not real `agents`-platform installer output
  (a 730-line diff away from what `graphify install --project --platform agents` would
  actually write); the report explicitly warns "a future `graphify install --project
  --platform agents` run would silently clobber it." #847 records the *decision* to
  install for all three platforms including `agents`, but never surfaces this specific,
  concrete, already-measured hazard sitting directly in that decision's path. This is
  exactly the kind of "scope that was named but never executed" / "decisions the evidence
  does not fully support" gap Task 1 of #847 itself asked lanes to look for.
  DISPOSITION: in-scope-for-#847 — add a bullet under "known-imperfect" or fold into the
  graphify-platforms decision bullet with a forward pointer, since Task 2 item 2 will
  build the real upgrade work and needs this in its acceptance criteria (don't run
  `--platform agents` install without first backing up or diffing the existing
  hand-authored file).

MEDIUM · The "bake permutations" decision bullet as worded will mis-scope Task 2 item 1
(duplicate of the CONTRADICTED finding above, restated for completeness) · SYNTHESIS.md:386-393
  Already covered above under "Decisions" — repeated here because it is the single
  clearest case of a load-bearing conclusion (defer bake adoption until the axis is real)
  that #847's own wording inverts. If Task 2 runs `/to-spec` directly off #847's bullet
  text without re-reading SYNTHESIS §6, the resulting spec will propose building
  `subaction/matrix` integration now, against a research conclusion that says not yet.

LOW · The corpus-location discrepancy itself (5 "c"-prefixed reports exist across the two
locations, not the 3 named in the shared context / not referenced at all from #847's own
"Where the evidence lives" section) is not recorded anywhere
  EVIDENCE: `2026-08-30c-graphify-upgrade-research.md` and `2026-08-30c-opus-cold-review-graphify-2.md`
  exist in the main-worktree corpus at `origin/main` (1e6a368) but #847's own "Where the
  evidence lives" section names only 3 `2026-08-30c-*` files (all as living "on the PR #846
  branch"). Two of #847's own strongest, most numerically-grounded findings (the
  0.28s/0.094s hook-cost measurement, and part of the graphify-upgrade decisions) actually
  live in files #847 doesn't enumerate by name. Not a factual error in #847 (it never
  claims completeness of its own file list), but worth tightening if the next session
  needs to relocate a citation quickly.
  DISPOSITION: ticket recommendation (low priority, doc-hygiene only) — not worth blocking
  Task 2 over.

## Question 3 — Q-SCOPE: is each finding in scope for #847, or a sibling ticket?

Every GROUNDED/ASSERTED/CONTRADICTED item above is marked `DISPOSITION: in-scope-for-#847`
except the corpus-location discrepancy (Q2, LOW), which is a ticket recommendation. Rationale:
#847 itself is the anti-loss/audit record — every claim inside it is properly this ticket's
own scope to correct, since #847's stated purpose is "the next session audits rather than
assumes." None of the findings above are about *new* work outside #847's stated Task 1/Task 2
— they are about #847's own text being wrong, unsupported, or incomplete, which is squarely
what Task 1 asked auditors to find. The one exception (corpus file-list hygiene) is cosmetic
and does not block Task 2, hence ticket-recommended rather than blocking.

## Summary — disposition counts

- GROUNDED: 16 of 22 claims (rows/bullets), several with independently re-derived numbers
  (AGENTS.md byte count exact match; #837 PR state; hook-cost 0.094s exact match)
- ASSERTED (no report support found): 4 — tag scheme wording, graphify "full lifecycle"
  scope wording, macOS-runner container-runtime claim, graphify-query truncation claim
- CONTRADICTED: 1 (HIGH) — "bake permutations: adopt both at once, not sequenced" inverts
  SYNTHESIS.md §6's explicit "adopt later, if/when the axis is real" conclusion
- Completeness gap (Q2): 1 load-bearing omission (HIGH) — the `.agents/` SKILL.md clobber
  risk sits inside a decision #847 records but is never itself recorded

The single highest-value correction for the next session: **re-read SYNTHESIS.md §6 before
running `/to-spec` on the bake-permutations thread** — #847's own wording would otherwise
steer that spec toward building `subaction/matrix` integration now, which the session's own
completed research explicitly recommended against doing yet.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #847, PRs
  #844/#846/#837, the shipped source (`AGENTS.md`, `pytest.ini`, `.github/workflows/ci.yml`,
  `mise.toml`, `docker-bake.hcl`, `scripts/graphify-hook-guard.sh`,
  `.devcontainer/mise-system.toml`) and the 44-report corpus under
  `docs/research/kb/reports/agents/`, read across both the `origin/main` worktree and the
  live PR #846 checkout.

_None other consulted directly in this pass — all verification was against this repo's own
corpus, issue tracker, and shipped code; no external repo source or docs were fetched._
