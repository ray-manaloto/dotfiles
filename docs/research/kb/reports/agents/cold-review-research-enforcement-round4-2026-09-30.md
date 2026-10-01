# Cold review (round 4) — `git diff b5c089d8..d0e0618d` (feat/research-enforcement)

- Subject: `db37bddf` (round 4) + `d0e0618d` (round 4b). HEAD at review = `d0e0618d755082aa08d9a36fa2efee1681fabea1`.
  Every `file:line` cites the `d0e0618d` blob.
- Prior review: `docs/research/kb/reports/agents/cold-review-research-enforcement-round3-2026-09-30.md` (R1-R10).
- Scope (NARROW, per brief): (1) do R1 and R2 close — re-run the original failing scenarios N3 / N6;
  (2) new defects from R6 (`gh api -i` status parsing), R7 (shape checks, `shq()`, dot-only guard),
  R8 (bidirectional query check), and the round-4b `health` planner-role normalisation.
  Not re-litigated: F4/F5/F9/F11/F12/R9 (#1471/#1472/#1473).
- Reviewer: cold-reviewer (Opus). Memory consulted: `saved_workflow_js_review.md`, `mutation_harness.md`.
- Status: COMPLETE. Auto memory was enabled and consulted; the scratch worktree was removed after use.

## Method and controls

1. **Scenario driver over the real blobs** (`scratchpad/r4/drive4.py`, `scen4.py`). Three blobs run through
   one fixture: `base` = `b5c089d8` (its workflow is byte-identical to `955be9e6`, `git diff --quiet` rc=0),
   `mid` = `db37bddf`, `head` = `d0e0618d`. `agent()` records label, model, prompt and schema. `parallel()`
   maps a throwing thunk to `null`. The default deps responder returns `exists: {rc:0, status:200, fullName:<its own repo>}`.
   - Control C0: the healthy fixture reads `complete` with 0 gaps on all three blobs.
2. **Live probes** (authenticated `gh`, 2026-09-30) settle what `gh api -i` actually prints.
3. **Mutation table** in place on a scratch `git worktree add --detach <scratchpad>/wt d0e0618d`, restored
   with `git -C wt checkout --` after each row (see below).

### (1) R1 and R2 — the original failing scenarios, re-run

| Scenario | `b5c089d8` (base) | `db37bddf` | `d0e0618d` (head) | Closed? |
|---|---|---|---|---|
| C0 healthy | `complete`, 0 gaps | `complete` | `complete` | control |
| **N3** (R1): README 0 (unindexed), planner `query` 0 + `known-absent` 0, **no planner must-hit**, health 9 | **`complete`**, health row `role:"must-hit"` | `mandatory-gap`: `code search: no must-hit control returned a hit…`; health row `role:"health"` | same as `db37bddf` | **yes** |
| **N6** (R2): `repo: jdx/rtx`, `exists {rc:0,status:200,fullName:"jdx/mise"}` (the live values), README 0 | **`complete`** + "not indexed" note | `mandatory-gap`: `dependency repo jdx/rtx redirects to jdx/mise — re-run with repo/relatedRepos set to jdx/mise`; no note | same | **yes** |
| N6r: the rename on a RELATED repo (`relatedRepos: ["jdx/rtx"]`) | `complete` + note | `mandatory-gap`, same redirect gap | same | **yes** |

### Live probes — what `gh api -i repos/<r> --jq .full_name` prints

| Probe | rc | First line | Last line | stderr |
|---|---|---|---|---|
| `repos/jdx/rtx` (renamed) | 0 | `HTTP/2.0 200 OK` | `jdx/mise` | — |
| `repos/jdx/mise` (control) | 0 | `HTTP/2.0 200 OK` | `jdx/mise` | — |
| `repos/jdx/zz-nope-k4q9w2` (fresh absent) | 1 | `HTTP/2.0 404 Not Found` | the error JSON `{"message":"Not Found",…,"status":"404"}` (`--jq` is NOT applied) | `gh: Not Found (HTTP 404)` |

gh follows the 301 and prints only the FINAL response (no `Location` header in the output: 0 matches on all three),
so a rename arrives as `200` + a different `full_name`, which is exactly what `repoCheckGap` (`:375-381`) tests.
The 404 arm's last line is NOT a name. Its error JSON never reaches the compare, however, because `repoCheckGap`
tests `status` first. So the load-bearing half of the prompt (`:310-311`) is the status-parsing clause; the
"else \"\"" clause is not. Neither clause is pinned (M-R6d, L5).

### (2) New-behaviour scenarios (subject blob; base/mid where it discriminates)

| # | Scenario | `b5c089d8` | `db37bddf` | `d0e0618d` |
|---|---|---|---|---|
| R6-404 | `exists {rc:1,status:404,fullName:""}` (the live 404 shape) | `not found … (rc=1)` | — | `dependency repo example/repo not found via the repos API (HTTP 404)` |
| R6-200e | `exists {rc:0,status:200,fullName:""}` | `complete` | — | `could not check … (HTTP 200, rc=0, fullName "")` (implementer's dissent 2) |
| R6-0 | `exists {rc:1,status:0}` (no HTTP response) | `not found … (rc=1)` | — | `could not check example/repo via the repos API (HTTP 0)` |
| R6-trail | `exists {rc:0,status:200,fullName:"example/repo\n"}` | `complete` | — | **`mandatory-gap`: `dependency repo example/repo redirects to example/repo\n — re-run …`** (a redirect to itself; no `trim()`) |
| R8a | question slot = the related NAME `tool` | `complete` | — | gap `question-terms query "tool" is a repo name…` |
| R8slug | question slot = the related SLUG `other/tool` | `complete` | — | **`complete`** (not caught) |
| R8sq | cross-direction slot echoed as `'tool'` | false gap `(got "'tool'")` | — | `complete` (unquote fixed it) |
| R8case | cross-direction slot `Tool` for `tool` | false gap | — | false gap (unchanged; implementer's dissent 4) |
| **P4b** | planner's only non-control row is the health-control copy tagged `role:"health"` (+ must-hit 1, known-absent 0) | `mandatory-gap`: `code search: no planner query ran with rc=0` | **same gap** | **`complete`** — the row is re-tagged `query` and satisfies the planner-query requirement |
| P4bx | same, but tagged an unknown role `question` (control) | gap | — | gap (only `health` is re-tagged) |
| R7-dotdot | `reportPath …/agents/...md` → slug `..` | — | — | accepted; mirror `mkdir -p '/r/docs/research/kb/raw/../links'` (= `docs/research/kb/links/`), deps `--out .agent/kb/raw/research-fanout/../deps/…` |
| R7-dot | `reportPath …/agents/..md` → slug `.` | — | — | accepted; mirror dir `raw/./links` (shared by every such report) |
| R7-root | `repoRoot: "/tmp/a b;$(id)"` | — | — | command quoted (`mkdir -p '/tmp/a b;$(id)/docs/…'`), but the cwd line reads `root /tmp/a b;$(id) (so mise resolves …)` — unquoted |
| EB1 | planner fan-out rc=1, one link, `sourceDive:true`, link reader **null**, source-dive **null** | — | — | `links-only`; clause: `say the evidence base is: the 1 caller link(s) + hits triaged from the dependency-repo manifests + the example/repo source dive + the code-search rows` — both named reads FAILED |
| EB2 | planner null, `repo:""`, one link, its reader null | — | — | clause `the 1 caller link(s) + the code-search rows`; `codeSearch` is `[]` and the link was never read |

### Mutation table (in place on scratch worktree `d0e0618d`; `pytest tests/test_workflows_js.py -k "research_sweep or every_saved"`)

Every anchor asserted `count == 1` before writing; `git -C wt status --short` was empty after every restore; the
worktree was removed afterwards (`git worktree list` has no `wt4`). Re-derived count: **57 passed** pristine (the
implement report's 4b table says 56 — inherited, not re-checked further).

| Row | Mutation | Result | Failing tests |
|---|---|---|---|
| PRISTINE / PRISTINE-AFTER | none | green | — (57 passed) |
| CTRL | status drops `mandatory-gap` | **RED** | 10 tests |
| M-R1 | health row role `must-hit` again | RED | health_row_never_satisfies…, other_missing_stages, planner_health_role… |
| M-R2 | rename compare disabled | RED | renamed_repo…[example/renamed] |
| M-R6a | any `rc != 0` is "not found" | RED | unchecked_dependency_repo…[403/429/500] |
| **M-R6d** | deps prompt drops the whole `status = … FIRST line …; fullName = its LAST line when status is 200, else ""` instruction | **survived** | — (L5) |
| **M-R6f** | "could not check" keyed on `status !== 200` only (dissent 2 reverted) | **survived** | — (L5; the run then emits `redirects to  — re-run with repo/relatedRepos set to ` — scenario-confirmed) |
| M-R4 | README note regardless of health | RED | readme_note_needs_a_passing_health_control |
| M-R5b | evidence base ignores triage-null | RED | failed_stage_clause_names_what_was_read |
| **M-R5a** | evidence base drops the source-dive clause | **survived** | — (L3) |
| **M-R5c** | plan-null consequence emptied | **survived** | — (L3) |
| **M-R8b** | reverse check case-sensitive | **survived** | — (L4) |
| **M-R8c** | `unquote` strips double quotes only | **survived** | — (L4) |
| M-4b-drop | `health`→`query` normalisation removed | RED | planner_health_role_is_workflow_only |
| **CF-4b** | candidate fix: stray `health` → inert role `planner-health` | **RED** | planner_health_role_is_workflow_only — the test pins the fail-open `query` choice (`tests/test_workflows_js.py:1843`) |
| CF-R8 | candidate fix: reverse check on `nameOf(ran)` (catches a slug) | green | — free |
| CF-slug | candidate fix: dot-only report slug refused | green | — free |
| CF-root | candidate fix: `root ${shq(ROOT)}` | green | — free (`mirror_paths_are_quoted` checks only the firecrawl line) |
| CF-trim | candidate fix: `fullName.trim()` before compare | green | — free |

Every behaviour the commits claim goes red when reverted. The survivors are prompt clauses and secondary arms (L3-L5),
and every candidate fix except CF-4b costs no test edit.

## Findings

| # | Sev | Claim | file:line | Evidence |
|---|-----|-------|-----------|----------|
| L1 | LOW | **Round-4b normalisation fails open on the planner-query requirement.** A planner row tagged `health` is re-tagged `query` (not dropped or made inert), so a planner whose only non-control row is the health-control copy satisfies "at least one query of your own for the QUESTION". Base and `db37bddf` read `mandatory-gap`; `d0e0618d` reads `complete`. The test pins the `query` choice, so the fail-closed fix is red. | `.claude/workflows/research-sweep-run.js:394`, `:403`, `:118-121`; `tests/test_workflows_js.py:1843` | P4b: base `mandatory-gap` (`no planner query ran with rc=0`), mid the same, head `complete`. P4bx control (unknown role `question`) is still a gap on head, so only `health` is loosened. CF-4b (→ `planner-health`) RED. **Reachability:** `role` is constrained by the `PLAN_ROLES` enum (`:181`), and `$CC/workflows.md:311-313` says output failing schema validation is retried (5×) and then fails, so this fires in production only if the runtime ignores `enum` (UNVERIFIED). The bun stub does not enforce schemas (the commit says so), so it fires there. Fix: map a stray `health` to an inert role, or drop the row, and flip the assertion at `:1843`. |
| L2 | LOW | **R7: one interpolated value is neither shape-checked nor quoted.** `ROOT` (from `args.repoRoot`, or the `reportPath` prefix before `/docs/`, checked only for a leading `/`) is the cwd of the only command that writes files, and it goes into `root ${ROOT} …` raw. That makes the comment's "every shell command below interpolates only a constant, a shape-checked value … or a shq()-quoted one" true of the command string, but not of the cwd the agent must `cd` to. | `:114-115`, `:317`, `:130-131` | R7-root: the command is quoted, but the cwd line is `root /tmp/a b;$(id) (so mise resolves …)`. The implementer flagged this (dissent 6, "prose"). Caller-supplied, hence LOW. CF-root (`${shq(ROOT)}`, or fold `cd ${shq(ROOT)} &&` into the command) is free. |
| L2b | LOW | **R7: the dot-only guard round 4b added for repo segments is missing for the report slug.** `REPORT_SLUG` `..` (a `...md` report) or `.` (a `..md` report) passes `/^[A-Za-z0-9_.-]+$/`. The mirror then writes outside `raw/<slug>/`, into an ad-hoc tracked `docs/research/kb/links/` or a `raw/links/` shared by every such report, and the deps `--out` escapes `research-fanout/`. | `:110-112`, `:117`, `:302` | R7-dotdot / R7-dot scenarios (the rendered paths are in the table above). Contrived names, hence LOW. CF-slug is free. |
| L3 | LOW | **R5's `evidenceBase()` is derived from what was DISPATCHED, not what was READ.** It names caller links and the source dive whose readers returned null, and always appends "the code-search rows", even when `codeSearch` is `[]`. So the comment "what the report's evidence actually rests on … never a fixed sentence" and the SKILL's "the report states what the evidence actually rests on" overclaim, which is R5's own class. | `:516-523`, `:552`; `.claude/skills/research-sweep/SKILL.md` (`links-only` row) | EB1: both named reads FAILED, and both are still listed as the evidence base. EB2: no code-search row exists, and the clause still names them. Synth also receives FAILED READS, so the contradiction sits inside one prompt (dissent 5 acknowledges failed readers; the empty code search is not acknowledged). Q-FRESH: the base is not re-validated against `readResults` right before synthesis. M-R5a and M-R5c survive. |
| L4 | LOW | **R8's reverse check catches a bare repo NAME only.** A question-terms slot holding the related SLUG (`other/tool`) reads `complete`, while the SKILL says the other slot holds "question terms (never a repo name)". The case-insensitive and single-quote arms are unpinned. | `:345-349`, `:333-334`; SKILL `.claude/skills/research-sweep/SKILL.md` (dependency-agent sentence) | R8slug: `complete` on base and head. CF-R8 (`nameOf(ran)`) is free. M-R8b and M-R8c survive. (R8case is a false gap on both blobs, and dissent 4 makes it deliberate. It fails in the safe direction and is not raised.) |
| L5 | LOW | **R6's agent contract is unpinned, and its compare is brittle.** Deleting the whole status/last-line parse instruction stays green. Reverting dissent 2's `rc`/empty-`fullName` arm stays green and then emits `redirects to  — re-run … set to `. A whitespace-padded `fullName` claims a redirect to itself. | `:310-312`, `:377`, `:379` | M-R6d survives, M-R6f survives, R6-trail runs. The live probes show the logic itself is right: a rename is `200` + another `full_name`, and a 404's last line is the error JSON. Fix: pin the `FIRST line` / `when status is 200` clauses in `readme_zero…`'s prompt assertion (`tests/test_workflows_js.py:1278`), add a 200 + rc≠0 case to the parametrised test at `:1366`, and `trim()` the name. |
| L6 | LOW (ticket) | **Pre-existing sibling of F8/R7:** the shq() discipline stops at the workflow's own templates. Reader agents are handed a URL plus the template `mise exec -- firecrawl scrape <url> …` and build the command themselves, with no quoting instruction. This covers triaged URLs (from exa/firecrawl-search results, i.e. third-party text) and caller links whose mirror failed (`NO MIRROR`, read live), which is exactly F8's motivating `'`-bearing URL. | `:471`, `:484-487`, `:493-495` | The implementer's R7 sweep table lists these as "literal placeholders", which is true of the template and not of the command the agent runs. **Q-SCOPE:** not introduced by this diff, so recommend a ticket (one READ_RULES clause: "single-quote every URL, replacing `'` with `'\''`"). |

### Q-CLAIM — operator-facing strings this range adds or changes

| Clause | Enforcing line | Outcome |
|---|---|---|
| `dependency repo ${r} not found via the repos API (HTTP 404)` | `:376` `status === 404` | fine (live 404 shape) |
| `could not check ${r} … (HTTP n[ — rate-limited or forbidden])` | `:377`, `RATE_LIMIT_STATUS` `:374` | fine |
| `… (HTTP 200, rc=…, fullName "…")` | `:377` | fine, but unpinned (M-R6f, L5) |
| `dependency repo ${r} redirects to ${fullName} — re-run with …` | `:379` case-insensitive compare | fine for the live rename. False for a whitespace-padded name (L5) |
| note `… although ${r} exists — either … does not index it … or it has no README.md …; not a gap` | `:388-391` (`repoGap` empty, `healthOk`) | fine: "exists" now means "under its own name", and the note is gated on health (R3/R4 hold) |
| `question-terms query "${ran}" is a repo name, so ${r} was not searched for the QUESTION` | `:348` | fine for a bare name. A slug escapes it (L4) |
| `planner agent reported nothing (null) — no planner fan-out manifest reached triage` | `:423` | fine; round-3 R5's "no fan-out ran" overclaim is gone |
| consequence `no hit from any fan-out manifest (planner or dependency-repo) was triaged or read` | `:456` | fine |
| `say the evidence base is: ${evidenceBase()}` | `:517-523` | **overclaims** for failed readers and an empty code search (L3) |
| comment `:130-131` "every shell command … constant / shape-checked / shq()" | `:84`, `:112`, `shq` | true of the template strings. False for the cwd line (L2). The slug's "shape check" admits `..` (L2b) |
| comment `:118-120` "the only `health` row in codeSearch is the workflow's" / "can never satisfy the must-hit" | `:394`, `:404` | true. But the re-tag to `query` satisfies `:403` (L1) |
| comment `:72-73` "only a planner or README must-hit >0 satisfies the must-hit requirement" | `:404` | true (N3) |
| SKILL "a planner row tagged `health` is read as `query` — which never counts as the must-hit" | `:394` | true as written. It omits that the row DOES count as the planner's query (L1) |
| error text `… must be [A-Za-z0-9_.-]+.md` | `:112` | `.md` is not enforced (a `.txt` reportPath passes); trivial, not raised |
| comment `:60-61` "skipping it cannot read as `complete`" (the planner's own must-hit) | — | still false whenever any README is >0. That is the F4 class (#1471); not re-raised |

### Q-SCOPE

L1-L5 sit in the R5/R6/R7/R8/4b lines this range wrote, so they are in scope; all are LOW. L6 is pre-existing, so it gets a ticket.
F4/F5/F9/F11/F12/R9 (#1471/#1472/#1473) were not re-litigated.

## Verdict

**SHIP.** 0 HIGH, 0 MEDIUM, 7 LOW (L1, L2, L2b, L3, L4, L5, L6).

The brief's two enumerated questions are both answered.

1. **R1 and R2 close.** N3 and N6, and N6r on a related repo, each read `mandatory-gap` on `db37bddf`/`d0e0618d` where `b5c089d8`
   read `complete`. The R2 path is confirmed against live `gh api -i` output: a rename comes back as `200` plus `jdx/mise`, and the 404's last line is the error JSON.
2. **New-defect hunt over R6/R7/R8/4b.** Every finding is LOW. Five of the six candidate fixes cost no test edit. The exception is L1:
   its test pins the fail-open re-tag (`tests/test_workflows_js.py:1843`).

LOWs to ticket, or to ride along: L1 (inert role and a flipped assertion), L2/L2b (`shq(ROOT)` and a dot-only slug guard), L3
(build `evidenceBase` from `readResults` and from `codeSearch.length`), L4 (`nameOf(ran)`), L5 (pin the R6 prompt clauses and the
200+rc≠0 arm, then `trim()`), and L6 (a READ_RULES URL-quoting clause; pre-existing).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — control arm for `gh api -i repos/<r> --jq .full_name` (`200`, `jdx/mise`).
- [jdx/rtx](https://github.com/jdx/rtx) — the renamed repo: `gh api -i` follows the 301 and prints `200` with last line `jdx/mise`, rc=0.
