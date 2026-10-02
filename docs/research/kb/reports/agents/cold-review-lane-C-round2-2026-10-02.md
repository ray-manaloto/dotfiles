# Cold review round 2: research-sweep fix-up (lane C)

- **Subject:** `a09aa2477e687dc9d79e224257dc86c605eeca52..25fc2d5ef1632ef679d089602c875ff1b9775e99`, which is one commit (`25fc2d5e`). It was read in the context of `4ba69bb7..25fc2d5e` on branch `fix/research-sweep-1471-1514`.
- **Reviewer:** cold-reviewer (Opus), read-only on source. I consulted my memory first; it holds three entries: pin-the-ref, the guard's probe shapes, and the research-sweep defect classes.
- **Pinning:** HEAD is `25fc2d5e`. `git diff --stat 25fc2d5e` was empty at the start and again before the live probes, so the working-tree python equals the ref. Every `file:line` comes from `git show 25fc2d5e:<path>`.
- **Round shape:** BOUNDED. The domain has two parts.
  1. The 19 round-1 findings, F1–F19. Each gets one disposition: FIXED, NARROWED-AS-DOCUMENTED, or STILL-OPEN.
  2. New defects introduced by the fix-up commit. Six surfaces were named first: the has_issues/has_discussions exemption, runId/`--expect-request-id`, the mirror-index stale check, the shapeOf OR/paren change, the repoRoot normalisation, and the no-`cd` mirror commands. After those, everything else the commit changed.
- **Suite at the ref:** `uv run --project python pytest tests/test_research_fanout_probe.py tests/test_workflows_js.py -q` reported 129 passed, rc=0.

## Status

COMPLETE (round 2, bounded). Every question in the domain has an answer below.

## Part 1 — round-1 dispositions (19 of 19)

| # | Disposition | Evidence (file:line @ 25fc2d5e) |
|---|---|---|
| F1 | FIXED for discussions. **Over-applied for issues** (N1). | `.claude/workflows/research-sweep-run.js:461-463,477-478`; `python/src/dotfiles_setup/research_fanout.py:1733-1740`. The discussions half is right: live, apache/kafka and rhysd/actionlint discussions both return `empty_unverified` with canary 0. My round-1 "(or Issues)" was never verified. It is wrong for any repo whose pull requests are on. |
| F2 | NARROWED-AS-DOCUMENTED | `.claude/skills/research-sweep/SKILL.md:64-76` now reads "computed by a probe, not interpreted by an agent" and "That echo catches a miscopied line, not a fabricated one". `readProbe` is unchanged (`research-sweep-run.js:182-190`). Residual: N10. |
| F3 | NARROWED (opt-in) | `research-sweep-run.js:137-138,408,414`; `research_fanout.py:1789-1795`. The check is exact only when the caller passes `runId`. Without it, freshness is still a 1-hour window, and SKILL.md:58-59 documents that. Python arm: `tests/test_research_fanout_probe.py:537-556`. |
| F4 | FIXED | `research-sweep-run.js:576` filters on `x.fresh`, and both the early exit (`:581`) and `evidenceBase` (`:691`) read the filtered list. |
| F5 | NARROWED (age only) | `research_fanout.py:1907-1920`. A probe older than 3600 s is listed as "stale probe from an earlier run". There is no run identity and no URL check. See N5. |
| F6 | FIXED | `research-sweep-run.js:426-427,602` no longer `cd`. The mirror and index paths are absolute and `shq`-quoted, and `_repo_root()` is `MISE_PROJECT_ROOT` (`research_fanout.py:2218-2219`). |
| F7 | FIXED for the stated scenario. The parenthesis change adds a new defect (N2). | `research-sweep-run.js:545-546`. Evaluated live in bun: `foo OR bar language:toml` gives shape `OR language:toml`, `mise language:toml` gives `language:toml`, so the query is unarmed. `mise OR rtx language:toml` arms it. |
| F8 | FIXED | `research_fanout.py:1850-1852` (`if markdown and not reason`). |
| F9 | **STILL-OPEN** on the derived-ROOT branch | `research-sweep-run.js:145-146` normalises only an explicit `repoRoot`. With no `repoRoot`, ROOT is `A.reportPath.slice(0, docsAt)`, un-normalised, and `:101` still allows empty segments. Take `reportPath=/Users/x//repo/docs/research/r.md` plus links. MIRROR_DIR keeps the `//`. Python's `str(Path(...))` returns `/Users/x/repo/...`: I ran it live, and the control without `//` printed the identical string. So `x.path === path` at `:487` fails, and every link becomes the mandatory gap "no PROBE-JSON line", although the mirror succeeded. Fix: apply the same `replace(/\/+/g,'/')` to the derived ROOT, or refuse an empty segment in `reportPath`. |
| F10 | FIXED, apart from `--limit` | `research_fanout.py:2009-2018`. `--limit` has a parser default, so passing it cannot be detected. |
| F11 | NARROWED-AS-DOCUMENTED (residual) | `research_fanout.py:2059-2064`. |
| F12 | FIXED | `research-sweep-run.js:475`. |
| F13 | FIXED for `synth-null` (`:732` passes `...common`; test `tests/test_workflows_js.py:2782-2803`). **STILL-OPEN for `triage-null`.** | `research-sweep-run.js:621` calls `withStatuses('triage-null', { plan, mandatoryGaps, fanoutGaps, routing })` without `stageGaps`, although `stageGaps` was already filled at `:586-590`. Take a null planner, fresh dependency manifests, no links, and a null triage. The result has `statuses:['triage-null','mandatory-gap']`, no `stage-gap`, and no `stageGaps` field. |
| F14 | NARROWED-AS-DOCUMENTED | SKILL.md:113-115 ("cannot be detected from the workflow"). The code at `research-sweep-run.js:359-360` is unchanged. |
| F15 | FIXED | SKILL.md:113 lists `write-failed`. |
| F16 | FIXED under `docs/`. NARROWED-AS-DOCUMENTED outside it. | `research-sweep-run.js:154-156`; SKILL.md:102-105. The residual now also collides retrospect files (N7). |
| F17 | FIXED | `research_fanout.py:1710-1713`; `research-sweep-run.js:195-196,500-502`. |
| F18 | FIXED for the shared directory. Small residue (N8). | `research-sweep-run.js:132-133`. |
| F19 | FIXED | `research-sweep-run.js:537`. |

**Tally (19):**
- **9 FIXED:** F4, F6, F7 (stated scenario), F8, F10, F12, F15, F17, F19.
- **8 NARROWED or partly fixed, as documented:** F1, F2, F3, F5, F11, F14, F16, F18. The F1 and F18 residues are new defects N1 and N8.
- **2 STILL-OPEN in part:** F9 on the derived-ROOT branch, and F13 for `triage-null`.

## Part 2 — new defects introduced by a09aa247..25fc2d5e

| # | Sev | Claim | file:line | Failure scenario |
|---|---|---|---|---|
| N1 | **MED** | The `has_issues === false` exemption drops EVERY `github-issues` failure. But the `github-issues` source queries `search/issues` without `is:issue`, so it returns pull requests and answers fully on an issues-disabled repo whose PRs are on. The exemption therefore changes the verdict only when that search really failed. That re-opens #1473 ("releases answering must not hide an issues search that failed") for this class of repo, and the note it writes is false. | `.claude/workflows/research-sweep-run.js:462-463,477-478`; the source query is at `python/src/dotfiles_setup/research_fanout.py:594`; the repo-check fields are at `:1735-1740` | **Live, both arms.** `repos/apache/kafka` returns `has_issues=false, has_pull_requests=true`. The real `_source_result('github-issues', …repo='apache/kafka'…)` returned `ok` with 5 items. `search/issues q=repo:apache/kafka kafka` returned 19118 hits, every sampled item a PR, while `is:issue` returned 0. Control: `torvalds/linux` returns `has_issues=false, has_pull_requests=false`, and the same source returned `empty_unverified` with canary `linux`=0. Only that case is a dead tracker. **Scenario:** with `repo: apache/kafka`, a 403 secondary rate limit hits the dependency agent's issues search (F11 makes concurrent spend plausible). The manifest then holds `github-issues: error (…)`. The filter at `:478` drops it, `failed` is empty, the run gets `ok:true`, and no mandatory gap is raised. The run reads `complete` with the note "apache/kafka has issues disabled (repos API) — github-issues not searchable there; not a gap". The same blind spot covers apache/hadoop (`has_issues=false`) and the other projects that track issues in JIRA. **Fix:** exempt `github-issues` only when `has_issues === false && has_pull_requests === false`. The field is already in the `repos/<r>` body; record it in `_repo_check_probe`. **Untested:** the only test that sets the flag pins `hasIssues: true` (`tests/test_workflows_js.py:2716`, and the stub plumbing at `:213`), so the issues clause is never exercised. |
| N2 | LOW | `shapeOf` drops a qualifier that touches `(`. Two queries with different qualifier sets inside parentheses can then share a shape, so a 0 gets armed by a must-hit that never exercised that qualifier. The comment at `:543-544` says parentheses "are part of the shape too". | `research-sweep-run.js:543-546` | Evaluated live in bun: `(language:toml OR language:yaml) zzq` and `(path:src OR language:yaml) mise` both give `() OR language:yaml)`. A 0 for the first is armed although `language:toml` was never shown to match. The `()` marker also counts tokens rather than groups: `(foo bar) language:toml` gives `() () language:toml` and `(mise) language:toml` gives `() language:toml`, so that case stays unarmed. The planner prompt forbids parentheses (`:390`), which keeps this LOW. Fix: strip `()` from a token and still classify the remainder, or reject a planner row containing `(`. |
| N3 | LOW | `args.runId` passes `^[A-Za-z0-9_.-]+$` with a leading `-`, but argparse then rejects it as a value. With such an id, every dependency fan-out and probe fails, and the gaps blame the agent. | `research-sweep-run.js:138,408,414` | Live through `mise run research-fanout`. `--expect-request-id -run1` exits rc=2 with "argument --expect-request-id: expected one argument". The control `--expect-request-id run1` reaches the module's own usage check (rc=2, "--probe-out takes no … --repo"). Neither arm wrote a file. With `runId:'-run1'`, every dependency repo yields "wrote no manifest" and "no PROBE-JSON line … did not run or its line was not copied". Fix: require a leading `[A-Za-z0-9]`, or emit `--request-id=${RUN_ID}`. |
| N4 | LOW | When a manifest is recent but its request id does not match, the gap text says "is Ns old — not written by this run". The likely cause is an agent that dropped the trailing `--request-id` flag while copying the command. In that case the manifest WAS written by this run, so the text misdiagnoses it. | `research-sweep-run.js:472`; `research_fanout.py:1790-1795` | `runId:'r1'`. The agent runs the fan-out without `--request-id r1`, so the manifest has `request_id:null` and `age_s:12`. The gap reads "`…/manifest.json is 12s old — not written by this run`". The probe row already carries `request_id`, but the gap never names the mismatch. Fail-closed, but the operator chases the wrong cause. Also, "pass `runId` to stamp each fan-out" (SKILL.md:58) holds only for the dependency fan-outs: the planner fan-out at `:382` is never stamped, and its agent-reported manifests are never freshness-checked. That gap is older than this commit; ticket it. |
| N5 | LOW | The mirror index's new stale detection never reaches the workflow. `indexRow.missing` is not read anywhere, so a stale probe only changes a README row. SKILL.md:71-72 says "a stale … mirror probe from an earlier sweep is a gap, never evidence". | `research-sweep-run.js:618-619` (reads only `written`); `research_fanout.py:1907-1920,1962` | In practice a stale probe file means that link's mirror agent did not run this time, and `:488-491` already raises a mandatory gap. The escape is the F2 class: an agent that re-copies an earlier run's line for the same path. The workflow accepts it as mirrored, and readers read the old `<n>.md`. Meanwhile the index (python re-reading the disk, the one independent on-disk check) marks the row stale, and the workflow discards that. Within the 1 h window nothing flags it at all. Fix: gap on `indexRow.missing` exceeding the count of mirror-stage gaps, or say in the skill that the index check is advisory. |
| N6 | LOW | The `meta.phases` Retrospect string still says the proposal is saved "beside the report". The fix-up moved it to `docs/research/kb/reports/agents/research-sweep-retrospect-<slug>.md` whenever ROOT is known, which is almost every run. | `research-sweep-run.js:14` vs `:311-312` | The phase description shown to operators names the wrong location. The same string at a09aa247 (`:14`) was true then; the fix-up changed `RETRO_PATH` but not this line. |
| N7 | LOW | The `RETRO_PATH` change regresses uniqueness. The old path was derived from `reportPath`, so it was always unique per report. The new one is derived from the slug, which (F16 residual) is just the file name outside `docs/`. | `research-sweep-run.js:311-312,156` | Two reports, `/tmp/a/report.md` and `/tmp/b/report.md`, each with `repoRoot` set to this repo, both write `docs/research/kb/reports/agents/research-sweep-retrospect-report.md`. The second run silently overwrites the first run's tracked proposal. |
| N8 | LOW | The dedup is case-insensitive, but `depQueries` still compares case-sensitively (`o !== REPO`). A case variant that was folded out of DEP_REPOS still drives a self cross-direction run on REPO's own tracker. | `research-sweep-run.js:132-133,140` | Evaluated live in bun with `repo:'jdx/mise', relatedRepos:['jdx/Mise']`: DEP_REPOS is `["jdx/mise"]` and `depQueries` gives `[null,"Mise"]`, so jdx/mise is searched for its own name. The control (no variant) gives `[null]`. Harmless but noisy: the report's Dependency table lists a repo as related to itself. Two RELATED entries that differ only in case likewise run twice against REPO. |
| N9 | LOW | A disabled tracker is filtered out of `requiredFailed` without a trace in that row. Its note is routed into CODE SEARCH NOTES, so the "Dependency-repo fan-out" table shows nothing failed for a source that never answered. | `research-sweep-run.js:463,477-478,481,563`; synth table spec `:709` | For rhysd/actionlint, the dependency row reads `requiredFailed: []` with no indication that discussions were skipped. The explanation appears under the Code search table, which the prompt (`:708-709`) says is for code-search notes. Fix: add a `disabled` field to the dependency row. |
| N10 | LOW | The narrowed F2 claim, "the manifests on disk are the evidence a reader re-checks", is weaker than it reads. The code-search and repo-check probe manifests (`plan/code-search.json`, `deps/<r>/probe.json`) sit in the gitignored, clean-swept `.agent/` tree, and their paths never reach the synthesizer or the report. | SKILL.md:74-76; `research-sweep-run.js:159,369,403,708-711,718` | The report's Code search table carries counts with no path, so a reader on another clone, or after `git clean -xdf`, cannot re-check any mandatory code-search number. Fix: pass the probe paths into synthesis, or narrow the sentence to "on the producing machine". |
| N11 | LOW | The new `_mirror_probe` OSError branch ("cannot prepare …") is a local process failure, yet it is classed as a world failure: it lands in `mirrorGaps` (named), not `mandatoryGaps`. That contradicts the classification comment. | `research_fanout.py:1817-1830`; `research-sweep-run.js:497-498` | The mirror directory is not writable (permissions, or a file where a directory should be). The probe returns `rc:1, reason:'cannot prepare …: PermissionError'`, and the workflow reports "not mirrored (cannot prepare …)" as if the page could not be fetched. Contrived. |
| N12 | LOW | Health-control text after F17: an `incomplete` health row produces "returned INCOMPLETE results … the search timed out — gh auth, rate-limit or search is broken". The two causes contradict each other. | `research-sweep-run.js:501-502,506,508` | Fail-closed and cosmetic. Name only the timeout when `c.incomplete`. |

## Q-FRESH (new decision → action pairs)

- **Tracker exemption.** It is decided from the repo-check in the same probe invocation, which runs after the fan-outs, so the input is fresh. The defect is the predicate (N1), not its timing.
- **runId.** It is checked at probe time against the manifest on disk, so it is fresh.
- **Mirror-index stale check.** It re-reads each `<n>.probe.json` at index time, after the mirror stage, so it is fresh. Its result is then discarded by the workflow (N5).

## Q-SCOPE

- **In scope (this diff):** N1–N12, plus the F9 and F13 residues.
- **Ticket candidates (older than this commit, outside the diff):**
  - (a) Planner fan-out manifests are agent-reported paths with no freshness or run-id check (`research-sweep-run.js:382,577`).
  - (b) The round-1 sibling is still open: the `"<query>"` and question-terms placeholders are double-quoted (`:382,408`), which allows shell expansion of `$VAR` into GitHub search and the manifest.
  - (c) "From the repository root" (`:406`) is ambiguous for a report in another repo. An agent that `cd`s into that repo's root loses the `research-fanout` task.

## Q-CLAIM (new or changed operator-facing clauses with no full enforcing line)

- `research-sweep-run.js:463` "github-issues not searchable there; not a gap" is false when `has_pull_requests=true` (N1).
- SKILL.md:56-57 "a tracker the repos API reports DISABLED … is a note, not a gap" is over-broad for issues (N1).
- `research-sweep-run.js:472` "not written by this run" fires for this run's manifest when only the stamp is missing (N4).
- SKILL.md:58 "stamp each fan-out" covers only the dependency fan-outs (N4).
- SKILL.md:71-72 "a stale … mirror probe … is a gap, never evidence": the index check never feeds a gap (N5).
- SKILL.md:74-76 "the manifests on disk are the evidence a reader re-checks": the probe paths are machine-local and never reach the report (N10).
- `research-sweep-run.js:14` "beside the report" is stale (N6).
- `research-sweep-run.js:543-544` "parentheses are part of the shape too" holds only partly (N2).
- `research-sweep-run.js:497` "A link firecrawl could not fetch is the WORLD": the new OSError branch is not that (N11).
- Enforced: `:475` placeholder gap; `:502` incomplete text (`research_fanout.py:1712-1713`); `:537` README note; `research_fanout.py:1829` "cannot prepare"; `:2012` usage message; SKILL.md:70 "HTTP >= 400 … is not saved" (`research_fanout.py:1851`); SKILL.md:109-110 retrospect path (`research-sweep-run.js:311-312`).

## Probes run (both arms)

| Probe | Control arm | Result |
|---|---|---|
| `has_*` flags via `gh api repos/<r>` | jdx/mise `[true,true]` | apache/kafka `has_issues=false, has_discussions=false, has_pull_requests=true`; torvalds/linux all three false; apache/hadoop `[false,false]`; apache/spark `[true,false]` |
| `search/issues` on an issues-disabled repo | `repo:jdx/mise mise` → 8263 | `repo:apache/kafka kafka` → 19118, all PRs; `repo:apache/kafka is:issue` → 0; `repo:torvalds/linux is:pr` → 0 (`repos/torvalds/linux/pulls` → 404) |
| Real `_source_result` (in-process, `default_runner`) | rhysd/actionlint github-issues → `empty_verified`, canary 5 | apache/kafka github-issues → **`ok`, 5 items** (N1); torvalds/linux github-issues → `empty_unverified`, canary 0; discussions on kafka and actionlint → `empty_unverified`, canary 0 (F1 fix correct) |
| runId leading dash through `mise run research-fanout` | `run1` → module usage error, rc=2 | `-run1` → argparse "expected one argument", rc=2; no file written (N3) |
| `pathlib` `//` normalisation | the path without `//` → identical output | `/Users/x//repo/...` → `/Users/x/repo/...` (F9 still open on the derived ROOT) |
| `shapeOf` (bun, copied verbatim from `:545-546`) | `foo OR bar language:toml` vs `mise language:toml` → differ (F7 fixed) | the two paren queries collide (N2) |
| dedup vs `depQueries` (bun) | no variant → `[null]` | `jdx/Mise` variant → `[null,"Mise"]` (N8) |
| Test coverage of the issues exemption | `hasDiscussions` varies (`tests/test_workflows_js.py:2709-2716`) | `hasIssues` set only to `true`, at a single site (grep: 2 hits, both plumbing or that test) |
| Subject suites at the ref | — | 129 passed, rc=0 |

## Not verified

- Whether `has_pull_requests` is present on every `repos/<r>` response, for example older GitHub Enterprise versions, is **UNVERIFIED**. It is present on both github.com repos probed. The fix should treat an absent field as "PRs on", which fails closed.
- I did not mutation-test N1's missing test. The claim that the clause is unexercised rests on the grep above, with a control arm, because editing source is outside this lane.

## Verdict

**SHIP-WITH-FIXES.**

- **Fix before ship:** N1 (MED). It is a regression this diff introduces into the #1473 class, it comes with a false operator-facing note, and the fix is one condition: exempt `github-issues` only when `has_issues === false && has_pull_requests === false`. Record the field in `_repo_check_probe` and add a test arm where `hasIssues:false` with PRs on stays a gap.
- **Ticket or fix opportunistically:** F9 on the derived-ROOT branch (one `replace`), F13's `triage-null` exit (pass `stageGaps`), and N2–N12, all LOW.
- **Re-review:** another round is warranted only if fixing N1 changes the enumeration, for example by adding new repo-check fields to the exemption predicate. Scope it to that delta.

## GitHub repos touched

- [apache/kafka](https://github.com/apache/kafka): `has_issues=false, has_pull_requests=true`; issues search returns PRs (N1 positive arm)
- [torvalds/linux](https://github.com/torvalds/linux): issues and PRs disabled; issues source dead (N1 control arm)
- [apache/hadoop](https://github.com/apache/hadoop): `has_issues=false` (N1 scope)
- [apache/spark](https://github.com/apache/spark): `has_issues=true, has_discussions=false`
- [rhysd/actionlint](https://github.com/rhysd/actionlint): discussions disabled; issues `empty_verified` (control)
- [jdx/mise](https://github.com/jdx/mise): control arm for flags and issues search
