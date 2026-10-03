# Cold review: research-sweep probe-recorded evidence (lane C)

- **Subject:** `4ba69bb77526cf6f7d39643ba429a5c8d107c983..a09aa2477e687dc9d79e224257dc86c605eeca52`. This is one commit, `a09aa247`, on branch `fix/research-sweep-1471-1514`.
- **Reviewer:** cold-reviewer (Opus). Review was diff-only and read-only on source.
- **Memory:** `.claude/agent-memory-local/cold-reviewer/` was empty at start.
- **Round shape:** OPEN HUNTING (round 1). An open round cannot end the loop by any outcome; it promotes to a bounded round.
- **Pinning (important):** during this review the working tree had **uncommitted edits by another writer** to 4 of the 6 subject files. `git diff --stat a09aa247` showed 162 insertions and 32 deletions across the workflow, `research_fanout.py`, and both test files. Every `file:line` below is from the **ref**, read with `git show a09aa247:<path>`, never from the working tree. Several of those uncommitted edits target findings below; they are marked *in-flight* and were **not reviewed**.
- **Live probes:** the live probes ran working-tree python. The functions they exercised (`_source_result`, `_empty_control`, `_github_discussions`, `_control_query`, `_scrape_payload`, `_fanout_manifest_probe`) are not in the working-tree delta. A grep of the delta for those definitions returned 0, while the control `_mirror_index_probe` returned a hit. So the probes measured ref-identical code.

## Status

COMPLETE (round 1, open hunting).

## Findings

| # | Sev | Claim | file:line (ref) | Concrete failure scenario |
|---|-----|-------|-----------------|---------------------------|
| F1 | HIGH | The dependency stage requires `github-discussions` (and `github-issues`) to be `ok` or `empty_verified`. No repo with Discussions (or Issues) disabled can ever meet that, so every sweep naming such a repo is permanently `mandatory-gap`/"INCOMPLETE". | `.claude/workflows/research-sweep-run.js:129,394`; `python/src/dotfiles_setup/research_fanout.py:1772-1778` (canary `:1030-1031`, verdict `:1127-1137`) | I ran the real source function live. `rhysd/actionlint` and `koalaman/shellcheck` (`gh api repos/<r>` → `has_discussions=false`) both returned `empty_unverified` with reason `canary returned 0 items` and `Control(query='actionlint', count=0)`. The control arm, `twpayne/chezmoi` (discussions on), returned `ok` with 10 items. `hadolint/hadolint` and `torvalds/linux` are also `has_discussions=false`; linux is also `has_issues=false`. So `repo: rhysd/actionlint` always produces the gap `github-discussions: empty_unverified (canary returned 0 items)`, and the Answer is forced to say the sweep is INCOMPLETE. Re-running cannot clear it. The repo-check probe already fetches `repos/<r>`, whose `has_discussions`/`has_issues` fields would tell the two cases apart, but nothing reads them. The test fixture `_RETRO_FINDINGS` (`tests/test_workflows_js.py`, retrospect tests) even uses "github-discussions was empty_unverified … probe has_discussions first" as its example. The class was known and shipped anyway. A gap that always fires turns `mandatory-gap` into noise that hides real gaps. |
| F2 | MED | The design claim "every mandatory number is recorded by a probe, not typed by an agent" has no enforcing line. The `probe_out` echo check can only catch a mis-copied line, never a fabricated one: the required value is printed in the agent's own prompt. | `.claude/workflows/research-sweep-run.js:171-179` (`readProbe`), `:168-169`; claim at `.claude/skills/research-sweep/SKILL.md:60-70` and the workflow header `:82-92` | `readProbe` accepts any JSON with `kind:'probe'`, `probe_out === out` and an array `probes`. `out` is literally in the command the agent is told to run. The repo's own test stub proves it: `PROBE_LINE` (`tests/test_workflows_js.py:175-177`) builds an accepted line from the prompt's `--probe-out` argument without running anything, and every passing test feeds such lines in. An agent that skips the command (or "tidies" a count while copying) and emits `{"kind":"probe","probe_out":"<given>","probes":[…count:5…]}` is indistinguishable from a real run. No downstream node re-reads the manifest files to compare. The synth prompt only says "cite the manifest paths". The header comment is honest ("What remains trusted is that an agent COPIED one line"), but the skill text overclaims. Fix options: have an independent node (triage already reads files) verify each probe manifest on disk byte-for-byte against the copied line, or narrow the skill claim. |
| F3 | MED | "Fresh" means "generated within 3600 s", not "written by this run". The manifest already records a `request_id` that the workflow never sets or checks. | `python/src/dotfiles_setup/research_fanout.py:1542,1770` (`--request-id` at `:1232`, persisted at `:1391`); `.claude/workflows/research-sweep-run.js:389,445` | The user re-runs the same `reportPath` 20 minutes after a degraded first run, so the slug is the same and so are the `deps/<r>/<k>/manifest.json` paths. A dep agent skips the fan-out commands (the motivating failure) but runs the probe. The old manifest is `age_s≈1200`, so `fresh=true`. Its `query` equals the cross-direction name, so the query check passes too. The stage reads as this run's evidence with no gap. Passing a per-run `--request-id` to every fan-out and checking it in `_fanout_manifest_probe` would make this exact. A tight `--max-age` would at least narrow it, since probe and fan-out run seconds apart in one agent. (Unverified: whether the workflow runtime offers `Date.now()`/`Math.random()` for minting the id.) |
| F4 | MED | A dependency manifest flagged stale (a mandatory gap) is **still fed to triage and synthesis as evidence**. | `.claude/workflows/research-sweep-run.js:540` (filters only on `query !== null`), consumed at `:545-547,571,655` | Same setup as F3, but past 3600 s. A gap reads "`… is 7200s old — not written by this run`", and yet `depManifests` includes that path. Triage then ranks the previous sweep's hits, and `evidenceBase` says "hits triaged from the dependency-repo manifests". The early-exit guard at `:545` also counts the stale manifest as something to work on. *In-flight:* the working tree adds `&& x.fresh` (unreviewed). |
| F5 | MED | The mirror README index is rendered from whatever `<n>.probe.json` files are on disk, with no freshness or URL check. A tracked artifact can therefore show a previous sweep's success for a link that failed or never ran this time. | `python/src/dotfiles_setup/research_fanout.py:1856-1875`; `.claude/workflows/research-sweep-run.js:566,582-583` | A second sweep with the same slug: mirror agent 2 returns null (a mandatory gap in the run result), but `links/2.probe.json` and `2.md` from the earlier run remain. The index probe lists row 2 as `rc 0, 42 bytes`, and the README text asserts "Every value below is read from the `<n>.probe.json` beside it". The durable file under `docs/research/kb/raw/` contradicts the run. If the caller reordered `links`, row n also pairs with the old URL, because the index gets only `--mirror-count`. *In-flight:* the working tree adds an age check (unreviewed; it does not add a URL check). |
| F6 | MED | At the ref, the mirror and index probes `cd` into ROOT before `mise run research-fanout`. A report in another repo (for example knowledge-base) therefore runs a task that does not exist there, and every link fails. | `.claude/workflows/research-sweep-run.js:164,406,566` | `reportPath=/…/knowledge-base/docs/research/x.md` gives `ROOT=/…/knowledge-base`, and the prompt becomes `cd '/…/knowledge-base' && mise run research-fanout -- …`. I grepped knowledge-base `mise.toml`: 0 `research-fanout` hits, with control 113 `tasks.` lines read. The task is missing, no PROBE-JSON comes back, and every caller link becomes a mandatory gap with the misleading reason "the probe did not run or its line was not copied". Plan and dep probes have no `cd`, so they still work, which hides the asymmetry. *In-flight:* the working tree removes `atRoot` (unreviewed). |
| F7 | MED | The arming shape ignores boolean operators and parentheses. A same-qualifier must-hit **without** `OR` arms an `OR` query's zero, yet the operator is exactly the untested part of #1471's own example. | `.claude/workflows/research-sweep-run.js:511,517-519`; pinned by `tests/test_workflows_js.py:1433` | Planner rows: `foo OR bar language:toml` = 0 and `mise language:toml` must-hit = 4. Both map to shape `language:toml`, so the zero is `armed:true` and reported as evidence of absence. If the legacy search treated `OR` as a literal term (or mis-parsed it), the zero is meaningless, and no row armed that grammar. The prompt also forbids parentheses (`:371`), but nothing enforces it. *In-flight:* the working tree adds operators to `shapeOf` (unreviewed). |
| F8 | LOW | The mirror probe writes an HTTP ≥ 400 error page into the tracked mirror directory. | `python/src/dotfiles_setup/research_fanout.py:1813-1815`; pinned by `tests/test_research_fanout_probe.py:393` | I ran a live 404 (`https://mise.jdx.dev/zz-cold-review-404-kq`) through the pinned firecrawl 1.25.1. It returned rc=0 with JSON keys `markdown`/`metadata`, `statusCode 404`, and 328 bytes; `_scrape_payload` returned `(404, 328-char md, 'HTTP 404')`. The status detection is therefore verified. But `if markdown:` still saves the "Error 404" body as `<n>.md` under `docs/research/kb/raw/`, and the plan prompt tells future planners to grep that tree (`:357-358`). The test asserts that the bytes landed, which enshrines the behaviour. *In-flight:* fixed in the working tree (unreviewed). |
| F9 | LOW | A `repoRoot`/`reportPath` containing `//` makes python's `Path()` normalise the echoed mirror `path`. The JS exact-match then fails, and the workflow blames the agent. | `.claude/workflows/research-sweep-run.js:101,135,458`; `python/src/dotfiles_setup/research_fanout.py:1946-1948` | The `.`/`..` check (`:101`) allows empty segments. `/Users/x//repo/docs/research/r.md` gives `ROOT=/Users/x//repo`, and `MIRROR_DIR` contains `//`. Python reports `path=/Users/x/repo/...`, so `x.path === path` is false, and every link becomes the mandatory gap "no PROBE-JSON line … not copied" although the probe succeeded. `repoRoot` gets no segment check at all. *In-flight:* ROOT normalisation was added in the working tree (unreviewed). |
| F10 | LOW | Probe mode silently ignores fan-out-only flags (`--repo`, `--out`, `--request-id`, `--last30days-plan`, `--limit`). | `python/src/dotfiles_setup/research_fanout.py:1950-1954` | `--probe-out p.json --repo x/y --code-search 'query=z'` exits 0. The `--repo` is dropped, while the inverse direction (probe flags in fan-out mode) is a usage error (`_validate_mode`). *In-flight:* partially fixed in the working tree (unreviewed). |
| F11 | LOW | `run_probes`' docstring says probes run SEQUENTIALLY so they do not spend the search bucket, but the workflow runs the planner probe and every dependency probe concurrently. | `python/src/dotfiles_setup/research_fanout.py:1986-1989`; `.claude/workflows/research-sweep-run.js:410-414` | Take a repo plus 9 related repos. That is 10 README controls, 1 health check and 3-7 planner code searches, all inside one minute against a 10/min bucket. The single retry after a ≤60 s reset clears one wave; a second wave returns `rate_limited`. This fails closed (unarmed or mandatory gap), but a run whose search is healthy reads as degraded. |
| F12 | LOW | The question-terms slot accepts the literal placeholder text. | `.claude/workflows/research-sweep-run.js:389,448` | An agent runs `research-fanout -- "<2-4 short search terms from the QUESTION>" …` verbatim. The issues search returns 0, the canary (the repo name) returns more than 0, so the status is `empty_verified`. The placeholder is not a repo name, so no gap fires, and "searched for the QUESTION" passes without any question term searched. Reject a `ran` that matches the placeholder or starts with `<`. |
| F13 | LOW | Early-exit `statuses` omit `links-only`/`stage-gap`, contradicting "statuses lists EVERY degraded state that applies". | `.claude/workflows/research-sweep-run.js:93-95,347,696` | A null planner with links and then a null synthesizer gives `statuses:['synth-null','mandatory-gap']`. `stageGaps` names the planner failure, but `links-only` is absent. |
| F14 | LOW | The retrospect "write-mismatch" check is another prompt-echo check, yet the commit says "a stray write path fails the phase" and the comment says "a writer that reports any other path wrote somewhere it was not asked to". | `.claude/workflows/research-sweep-run.js:337-343` | A writer that writes `.claude/workflows/research-sweep-run.js` but returns `path: RETRO_PATH, written: true` reads `written`. Only a writer that *reports* a different path fails. `written` is also agent-typed: the exact class #1514 removed from the mandatory stages. |
| F15 | LOW | The skill lists the `retrospect.status` values without `write-failed`, which the code produces. | `.claude/skills/research-sweep/SKILL.md:101-104` vs `.claude/workflows/research-sweep-run.js:343` | A writer returns `{written:false, path:RETRO_PATH}` → `write-failed`, a value the skill tells readers does not exist. |
| F16 | LOW | Report-slug uniqueness (#1513) holds only under `ROOT/docs/research/`. `docs/foo.md` and `docs/research/foo.md` both slug to `foo`, and any report outside `docs/` slugs to its bare file name. | `.claude/workflows/research-sweep-run.js:142-147`; claim at `SKILL.md:94-96` | Two reports `/tmp/a/report.md` and `/tmp/b/report.md`, each with `repoRoot` set, share `docs/research/kb/raw/report/links` and `.agent/kb/raw/research-fanout/report`. That is the #1513 overwrite again, and with F3 a manifest under 1 h old reads as fresh. |
| F17 | LOW | `_code_search_probe` ignores `incomplete_results`. | `python/src/dotfiles_setup/research_fanout.py:1686-1707` | A search that timed out server-side (`incomplete_results:true, total_count:0`) is recorded as an answered 0. Next to a same-shape must-hit, it is `armed` evidence of absence. |
| F18 | LOW | DEP_REPOS dedup is case-sensitive while the paths land on a case-insensitive FS. | `.claude/workflows/research-sweep-run.js:130,383-384` | With `repo: jdx/mise` and `relatedRepos: ['jdx/Mise']`, two parallel agents share `deps/jdx--mise/1/` on APFS. `_persist` unlinks owned files first, so one agent can delete the other's manifest, or a probe re-reads the other's query. |
| F19 | LOW | The README-control 0 is silently dropped (neither note nor gap) when health never ran. | `.claude/workflows/research-sweep-run.js:504-506` | The first dependency agent returns null, so `healthRow===null`, `healthOk=false`, `healthFailed=false`. A README 0 for another repo enters `codeSearch` as an unexplained must-hit of 0. *In-flight:* a note was added in the working tree (unreviewed). |

## Probes run (both arms)

| Probe | Positive / control arm | Result |
|---|---|---|
| Discussions canary on discussions-disabled repos (real `_source_result`) | `twpayne/chezmoi` → `ok`, 10 items | `rhysd/actionlint`, `koalaman/shellcheck` → `empty_unverified`, canary count 0. **F1 confirmed.** |
| `has_discussions`/`has_issues` via `gh api repos/<r>` | `jdx/mise` `[true,true]` | actionlint, shellcheck, hadolint `[false,true]`; linux `[false,false]` |
| mise re-quoting of appended args (injection through the task layer) | `'a b/c'` reached argparse as one word (`['a b/c']`, not "takes no QUERY") | `o'x$(echo hi)/t` arrived literal (`["o'x$(echo hi)/t"]`): **no injection via `mise run … --`** |
| firecrawl `--json` 404 shape | — | rc=0, `metadata.statusCode=404`, `_scrape_payload` → `HTTP 404`. **The 404 claim verified.** |
| knowledge-base has a `research-fanout` task | 113 `tasks.` lines read | 0 hits (F6) |
| Working-tree delta touches probed functions | `_mirror_index_probe` def found in delta | probed defs: 0 hits |

## Not verified

- The commit's "28/28 mutation arms caught" claim is **UNVERIFIED**. I did not re-run the suites: the working tree held another writer's uncommitted edits, so a run there would not test the ref.
- Whether the workflow runtime exposes `Date.now()`/`Math.random()` for a run id (F3 fix) is **UNVERIFIED**.

## Q-FRESH (decision → action re-validation)

- **Mirror probe → read-link agents.** The decision `mirrored(m)` comes from the agent-copied line (F2), and the file is not re-checked before readers are pointed at it. The window is short, so this is acceptable apart from F2.
- **Dependency freshness.** The decision uses a 1 h wall-clock window, not run identity (F3), and the stale result still flows to triage (F4).
- **Mirror index.** It renders from disk with no freshness check (F5).

## Q-SCOPE

- **In scope:** F1–F17, F19.
- **Sibling, pre-existing, ticket rather than diff change:** the question-terms placeholder and the planner `"<query>"` are **double-quoted** (`research-sweep-run.js:363,389`, unchanged from base). An agent filling in a question about `$GITHUB_TOKEN` gets shell expansion, which sends the value to GitHub search and into the manifest. This diff newly copies `m.query` into `dependencyRuns`, and from there into the tracked report table, which widens that sink. Recommend a ticket: single-quote the placeholder slot or route it through `shq`.
- **F18:** contrived input; a ticket is enough.

## Q-CLAIM (operator-facing clauses with no enforcing line)

- **SKILL.md:60** "Every mandatory number is recorded by a probe, not typed by an agent": no enforcing line (F2).
- **Commit message** "a stray write path fails the phase": only a *reported* path (F14).
- **Workflow `:93-95`** "statuses lists EVERY degraded state": false on early exits (F13).
- **Workflow `:445`** gap text "not written by this run": the inverse (fresh means written by this run) is what the code implicitly trusts, and it is false (F3).
- **Workflow `:433,460`** "the probe did not run or its line was not copied": it also fires when the probe ran and only a path mismatched (F6, F9).
- **README text** "Every value below is read from the `<n>.probe.json` beside it": true but stale-capable (F5).
- **SKILL.md:94-96** the slug guarantee: only under `docs/` (F16).
- **SKILL.md:101-104**: omits `write-failed` (F15).
- **research_fanout.py:1989** "Run every probe SEQUENTIALLY": per process only (F11).

## Verdict

**DO NOT SHIP.**

F1 is deterministic: every sweep about a repo with Discussions (or Issues) disabled reports `mandatory-gap`/INCOMPLETE. That includes three linters this repo pins. The main design claim (F2) is overstated in the operator-facing skill. F3 and F4 together let a skipped dependency run pass as fresh evidence for an hour, and keep stale evidence in the synthesis after that.

To reach SHIP-WITH-FIXES:
- **F1:** read `has_discussions`/`has_issues` from the repo-check and exempt disabled features.
- **F2:** add an independent on-disk check of each probe manifest, or narrow the claim.
- **F3:** stamp a per-run `--request-id` and check it.
- **F4–F7:** confirm the in-flight working-tree fixes in a fresh review of that new ref.

The LOW findings can be ticketed.

## GitHub repos touched

- [rhysd/actionlint](https://github.com/rhysd/actionlint): `has_discussions=false`; live discussions canary arm (F1)
- [koalaman/shellcheck](https://github.com/koalaman/shellcheck): `has_discussions=false`; live discussions canary arm (F1)
- [hadolint/hadolint](https://github.com/hadolint/hadolint): `has_discussions=false` (F1 scope)
- [torvalds/linux](https://github.com/torvalds/linux): `has_discussions=false, has_issues=false` (F1 scope)
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi): control arm, discussions on → `ok`
- [jdx/mise](https://github.com/jdx/mise): control arm for `has_discussions`; mise.jdx.dev 404 page for the firecrawl status probe
- [sphinx-doc/sphinx](https://github.com/sphinx-doc/sphinx): `has_discussions` check (true)
