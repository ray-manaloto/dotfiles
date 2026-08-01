# Codex adversarial review — `docs/specs/ticket-bound-receipts.md` (2026-07-31)

Persisted verbatim per `.claude/rules/agent-report-persistence.md`. Run against the **first draft**
of the #449 receipt spec, before any code existed — the point of reviewing a design rather than an
implementation.

- **Reviewer:** `codex exec --ephemeral --sandbox read-only -c model_reasoning_effort="high"`,
  codex-cli 0.146.0 (GPT-5.6). Cross-family cold lens per
  `feedback_refuters_and_cold_review_find_disjoint_defects`.
- **Method:** the whole spec was piped in on stdin with an explicit *"do NOT read the disk, do NOT
  run tools, do NOT load skill files"* instruction, so every finding is grounded in a quoted line of
  the document and nothing is inherited from the repo. Codex was told to label anything it could not
  ground as `unverified` — it labelled 10 items, reproduced below.
- **Verdict: `do-not-build`.** 16 findings.

---

## Verbatim

VERDICT: do-not-build

FINDINGS:

1. **The staleness model makes legitimate work fail while letting a false `base` pass.**

   Scenario: work branches from commit A, edits `hk-common.pkl`, then reads and cites the finished file at commit B. Using the required branch point A makes the receipt stale because the cited file changed; using the scaffolded B passes but falsely claims B was the branch point.

   Attacked lines: “`base: ... # full 40-char SHA of the branch point the work was done from`”; “**`local:`** | stale iff the path appears in `git diff --name-only <base>..HEAD`”; “`base` filled from `git rev-parse HEAD`”.

2. **L1 can close a ticket using an untracked receipt that immediately disappears.**

   Scenario: an agent scaffolds `docs/receipts/449.md`, never commits it, runs `mise run resolve -- 449`, and then deletes the checkout. The issue is closed and commented, but the supposedly durable artifact never reaches the repository; L3 can only complain later.

   Attacked lines: “**Tracked, one file per ticket**”; “**Receipt exists** at `docs/receipts/<n>.md`, parses, `issue:` matches the filename.”

3. **Removing or omitting a label disables every receipt control, including the claimed full-coverage audit.**

   Scenario: a decision-shaped ticket is filed without `wayfinder:*`, or the label is removed immediately before closure. L1 skips validation and L3 no longer includes it in “every closed-as-completed `wayfinder:*` issue,” so the closure permanently passes without a receipt.

   Attacked lines: “**If it carries no `wayfinder:*` label → skip every receipt check**”; “The scope is a hand-applied label, so exemption is the default”; “including retroactively, since a label can be removed.”

4. **The allowed close reasons form a second complete bypass.**

   Scenario: a `wayfinder:*` ticket representing completed work is closed with `gh issue close 449 --reason "not planned"`. L2 explicitly permits it, while L3 audits only `closed-as-completed` issues, so no receipt is ever required.

   Attacked lines: “Native escapes stay native — `--reason "not planned"`, `--reason duplicate`, `--duplicate-of <n>` are **allowed unchanged**”; “every closed-as-completed `wayfinder:*` issue has a well-formed, non-stale receipt.”

5. **`prior_art` does not make research happen; it only makes fabrication slightly more verbose.**

   Scenario: without running any search, an author writes `query: "chezmoi hooks"`, `hits: 1`, a plausible control count, and a known report path. Every declared value validates, yet the allegedly prospective work never happened.

   Attacked line: “`hits` and `control` cannot be filled without running the search. This is the one field that makes the work happen rather than merely recording it.”

6. **The schema validates presence, not semantic coherence.**

   Scenario: a receipt says `review.lens: none`, `review.verdict: clean`, `review.findings: 5`, and `review.disposition: ""`. All fields are present, and the only explicit non-empty constraint applies to `sources`, so a contradictory receipt may be considered well formed.

   Attacked lines: “**Every field is REQUIRED. `none` / `not-run` / `none-required` are legal values; omission is not.**”; “**Every required field present**, `sources` non-empty unless `kind: none-required`.”

7. **`kind: none-required` is the reflexive checkbox the design claims to prevent.**

   Scenario: authors discover that selecting `none-required` avoids documenting sources and use it for routine closures. The gate accepts the value without requiring a reason, approver, ticket category, or objective eligibility test.

   Attacked lines: “`[]` is illegal; use `kind: none-required`”; “What stops it becoming the default answer, the way F3 predicted for the `ask` dialog?”

8. **The non-wayfinder path jumps to an operation whose input does not exist.**

   Scenario: `mise run resolve -- 123` reads an unlabeled ticket, skips the receipt checks, and jumps to step 5. Step 5 must post `verdict`, but no receipt was required or parsed, so the task must crash, post an empty value, or rely on behavior absent from the spec.

   Attacked lines: “If it carries no `wayfinder:*` label → skip every receipt check and go to step 5”; “Post `verdict` as the **resolution comment**.”

9. **The canonical verb is non-transactional but is described as fail-closed.**

   Scenario: posting the verdict succeeds, closing fails transiently, and retrying posts a duplicate comment. Worse, closing succeeds and the map append fails: the command reports failure after the ticket is already closed, with no rollback or resumable-state definition.

   Attacked lines: “It does, in order, failing closed at the first red step”; steps 5–7: “Post `verdict`,” “`gh issue close`,” then “**Append the context pointer**.”

10. **L3 is neither full coverage nor enforcement at closure time.**

   Scenario: a ticket is closed from the web without a receipt and no later `mise run land` occurs. The invalid closure is never examined. If a later unrelated PR lands, the audit runs only after that merge and can report damage it could not prevent.

   Attacked lines: “**L3 — the retrospective audit. Full coverage, after the fact.**”; “Wiring: run it inside `mise run land` (the repo's existing post-merge gate).”

11. **Auditing all historical receipts for current staleness guarantees accumulating false failures.**

   Scenario: a valid 2026 receipt cites `hk-common.pkl`. In 2027 that file changes for unrelated reasons. Every future audit now declares the historical receipt stale, even though it accurately records the evidence used for the 2026 decision. Repair requires rewriting history’s attestation or weakening the audit.

   Attacked lines: “every closed-as-completed `wayfinder:*` issue has a well-formed, **non-stale receipt**”; “stale iff the path appears in `git diff --name-only <base>..HEAD`.”

12. **Any later substantive ticket edit can invalidate a completed receipt indefinitely.**

   Scenario: after closure, the owner adds a clarification to the ticket body. The receipt’s base now predates the latest substantive edit, so future land operations fail even though the resolution process was valid when performed.

   Attacked line: “receipt `base` predates the ticket's last substantive body edit | ... | **yes**.”

13. **The audit cannot identify “the resolution comment” because the receipt stores no comment identity.**

   Scenario: an older discussion comment happens to contain the same verdict text, while L1’s actual comment post fails. The ticket is manually closed; L3 finds matching text somewhere in the comments and passes, unless it relies on an unspecified heuristic.

   Attacked lines: “every `verdict` matches its posted resolution comment”; “`verdict` in the receipt *is* the text L1 posts as the comment.”

14. **The build order has no migration plan and can strand unrelated work.**

   Scenario: step 3 audits the five already-closed wayfinder tickets, but step 1 creates only `449.md`. Turning that audit blocking later makes every land fail on inherited debt. Step 5 then denies the raw close command still emitted by the documented Wayfinder skill, but updating that skill is absent from the build order.

   Attacked lines: “`docs/receipts/449.md` as the worked first instance”; “`dotfiles-setup receipts audit` ... non-blocking at first”; “the skill will still emit the raw commands, and L2 denies one of them mid-sequence”; “Steps 1–5 are the spec's substance.”

15. **The headline 55% measurement does not measure the population being governed.**

   Scenario: all nine unseen recent closures may be non-wayfinder tickets, while the scoped history is 5-of-5 hook coverage. That does not prove L3 is unnecessary, but it does mean the cited measurement cannot quantify the scoped failure it is used to justify.

   Attacked lines: “a PreToolUse hook on `gh issue close` covers ~55% of *all* resolutions”; “on the population this spec actually binds, coverage is 5 of 5”; “The full-coverage layer (§4.2 L3) is justified by the 55%.”

16. **The design is over-built around attestations while its only prospective control remains unauditable.**

   Scenario: seven layers are implemented, but an author can still invent the `prior_art` values, choose `none-required`, remove the label, or use a non-completed reason. The reminders and subagent hooks add surface area without repairing the enforcement boundary.

   Attacked lines: “A receipt is an **attestation, not a proof**”; “If only one of the two ships, ship `prior_art`”; “Steps 1–5 are the spec's substance. 6–7 are additive.”

   A cheaper design would generate prior-art evidence through one executable command that records the exact query, corpus revision, tool version, and result hashes; require that generated receipt to be committed on the protected branch before closure; and validate closure through a GitHub-side event check. Cut L4 and L5 unless measured failures later justify them.

WHAT YOU COULD NOT CHECK:

- `unverified`: The issue counts, label counts, transcript counts, and 5-of-5 scoped coverage measurements.
- `unverified`: Whether the transcript extractor correctly distinguishes unseen closes from extraction failures.
- `unverified`: The claimed Claude hook output semantics, timeout behavior, and delivery of `permissionDecisionReason`.
- `unverified`: Whether `hook_guard.py` can reliably distinguish completed closes from the allowed native escape forms.
- `unverified`: Whether `mise run land` is truly post-merge and whether failures there block any meaningful state transition.
- `unverified`: Whether GitHub exposes enough history to determine a ticket’s “last substantive body edit.”
- `unverified`: The claimed existing repository rules, lint exclusions, Wayfinder behavior, and persistence guarantees.
- `unverified`: Whether map updates are local-file edits or GitHub mutations, and whether concurrent appends can lose data.
- `unverified`: How L3 selects the specific resolution comment or handles edited, deleted, duplicated, and reordered comments.
- `unverified`: Whether historical closed wayfinder tickets will be backfilled before the audit becomes blocking.
---

## Disposition by the main session

**All 16 accepted.** Not one was refuted. That is itself the finding: a one-pass design document
fails a cold adversarial lens comprehensively, and it cost zero implementation to learn.

| # | Claim | Disposition | Fix in the revised spec |
|---|---|---|---|
| 1 | Staleness model fails legitimate work / passes a false `base` | **ACCEPTED** | Global `base` demoted to provenance. Staleness is **per-source blob hash** recorded at read time, and is **advisory, never blocking**. §3 |
| 2 | L1 can close on an **uncommitted** receipt | **ACCEPTED — sharp** | L1 requires the receipt to be tracked *and* clean: `git ls-files --error-unmatch` + `git diff --quiet HEAD --`. §4.2 |
| 3 | Removing/omitting the label disables every control | **ACCEPTED** | L3 audits by label **history** via the timeline, not current labels. ⚠️ Control-arm gap: `labeled` events are observable (13 in the repo's last 100), but `unlabeled` → **0**, so the removal half is documented-but-unobserved here. Recorded as such. §4.2 L3 |
| 4 | `--reason "not planned"` is a second complete bypass | **ACCEPTED** | L3 audits **every** closed wayfinder ticket regardless of `stateReason`; a non-completed close on one is itself a finding. §4.2 L3 |
| 5 | `prior_art` is fabricable — it does not make research happen | **ACCEPTED — the most valuable finding** | The field is no longer typed. `mise run receipt -- <n> --prior-art "<query>"` **runs** the search and writes the query, corpus commit, hit paths and result hash. §1.2, §6 |
| 6 | Schema validates presence, not coherence | **ACCEPTED** | Explicit cross-field rules (`lens: none` ⇒ `verdict: not-run`; `findings > 0` ⇒ `disposition` non-empty). §1.2 |
| 7 | `kind: none-required` is the reflexive checkbox | **ACCEPTED** | It now requires a written `reason`, does **not** exempt `prior_art`, and its rate is reported. §1.2, §4.2 L3 |
| 8 | Non-wayfinder path jumps to a step whose input does not exist | **ACCEPTED — plain spec bug** | `resolve` takes `--verdict` for tickets that need no receipt. §4.2 L1 |
| 9 | The verb is non-transactional but described as fail-closed | **ACCEPTED** | Every step made **idempotent and resumable**; re-running completes the remainder. §4.2 L1 |
| 10 | L3 is neither full coverage nor at closure time | **ACCEPTED** | Reframed: L3 covers every close *route*, not every *moment*. Delivery changed to a **standing upserted issue** (the `tool-currency` pattern) plus PR-scoped blocking. §4.2 L3 |
| 11 | Historical receipts accumulate false staleness | **ACCEPTED** | A closed ticket's receipt is **frozen** — never re-staleness-checked. §3 |
| 12 | A later ticket edit invalidates a valid receipt forever | **ACCEPTED** | The ticket-edit check applies **only before close**. §3 |
| 13 | The audit cannot identify "the resolution comment" | **ACCEPTED** | L1 writes the posted comment's `id` back into the receipt. Probe-confirmed the identity exists and is retrievable (`issues/433/comments` → `id`, `html_url`). §1.2, §4.2 L1 |
| 14 | Build order strands the repo on inherited debt | **ACCEPTED** | Step 1 **backfills the 5 already-closed** wayfinder receipts; the audit never blocks on debt it did not introduce; `docs/issue-tracker.md` is updated in the same step as the hook redirect. §8 |
| 15 | The 55% does not measure the governed population | **ACCEPTED — and now measured, not conceded** | Codex could only say the 9 unseen closes *may* be non-wayfinder. Probed: **0 of 9 carry a `wayfinder:*` label** (`auto-queue`, `bug`, `question`, or none). So the scoped observed miss rate is **0 of 5**, and 55% is an upper bound from a different population. L3 is now justified by the **mechanism** (close routes the hook structurally cannot see), never by the rate. §0, §4.2 L3 |
| 16 | Over-built; the one prospective control is unauditable | **ACCEPTED in part** | Its concrete proposal (generate prior-art evidence by command) is adopted verbatim as the fix for #5. **L5 (`UserPromptSubmit`) is cut entirely**; L4 (`SubagentStart`) stays explicitly optional. |

### On the `unverified` list

All 10 are correctly labelled — Codex was denied disk access by design, so it could not check the
repo-side claims. Four were verified here afterwards: the label-event mechanism (#3, with the gap
noted), the comment identity (#13), the wayfinder-label population (#15), and `gh issue close`'s
native reason flags. The rest are repo facts cited with their sources in the spec.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the spec under review, and the
  issue/label/timeline probes behind the disposition table.

---

# Round 2 — same reviewer, revision 2 of the spec

Same invocation and same no-disk constraint as round 1. Codex was told round 1's 16 findings were
**all accepted** and shown the revision that answers them, with an explicit instruction not to
re-litigate a closed finding unless the fix was wrong or incomplete.

**Verdict: `do-not-build`.** 13 findings. Six of round 1's confirmed closed (F4, F6, F8's missing
input, F13's data model, F15, F16); the rest were re-opened as incompletely fixed.

## Verbatim

## VERDICT: `do-not-build`

Revision 2 is materially better, but it is not executable as specified. The primary resolution path invalidates its own committed-receipt prerequisite, the first build step requires tooling that does not exist until step 2, and the backfill would describe present-day reconstruction as historical decision provenance. More fundamentally, L1 blocks on paperwork completeness while allowing irrelevant sources and a deliberately useless but genuinely executed prior-art query.

## FINDINGS

1. **L1 dirties the receipt after verifying it is committed, then closes the ticket against an uncommitted receipt.**

   Scenario: Step 3 confirms `449.md` is clean. Step 5 posts the comment and writes its ID into `449.md`, making it dirty. Step 6 closes the issue immediately. HEAD still contains an empty `resolution_comment`; the working tree contains the only valid version. If the task instead stops for a commit, it is neither one-shot nor self-converging as claimed.

   Attacks: “**Receipt is committed** … `git diff --quiet HEAD -- docs/receipts/<n>.md`.” / “**write that id back into the receipt** as `resolution_comment`.” / “`gh issue close <n> --reason completed`.” / “re-running the verb completes whatever remains.”

2. **The unlabelled-ticket branch jumps to a step that requires the receipt it explicitly skipped.**

   Scenario: Resolve an ordinary unlabelled issue with `--verdict`. Step 1 skips every receipt check and jumps to step 5; step 5 must write `resolution_comment` into `docs/receipts/<n>.md`, which need not exist. Either the command fails, silently creates an out-of-scope receipt, or closes without recording the ID.

   Attacks: “**No `wayfinder:*` label → skip every receipt check**, require an explicit `--verdict "<text>"` argument, and go to step 5.” / “**write that id back into the receipt** as `resolution_comment`.”

3. **Build step 1 cannot satisfy the schema because generated `prior_art` does not exist until build step 2.**

   Scenario: Step 1 must create six valid receipts, while `prior_art` is required for every kind and may never be typed. The only authorized generator ships in step 2. Step 1 must therefore violate the schema, hand-manufacture purported tool output, or depend on unshipped code. It is not independently safe or useful.

   Attacks: “`prior_art`: **GENERATED by `mise run receipt -- <n> --prior-art`. Never typed.**” / “**`prior_art` is required for EVERY `kind`**.” / Build order step 1: “backfill all 5 … + `449.md`.” / Step 2: “`mise run receipt -- <n>` incl. `--prior-art` generation.”

4. **The backfill manufactures decision provenance that cannot now be known.**

   Scenario: An author opens a source and runs prior-art search today for #433. The receipt then truthfully records what was opened today, but the corpus treats it as “how a decision was reached” before that ticket closed. `review: not-run` does not repair fabricated historical `sources`, `prior_art`, or `verified_at` semantics.

   Attacks: “a durable, ticket-keyed record of **how a decision was reached**.” / “`sources:` — **what was ACTUALLY opened**.” / “backfill all 5 already-closed wayfinder tickets.”

5. **“Generated” has no machine-verifiable meaning in the proposed validator, so the central fabrication fix only relocates the lie.**

   Scenario: An author types a plausible query, corpus SHA, hit list, timestamp, and random `result_sha256`. Every field and cross-field rule passes. Neither L1 nor L3 is specified to rerun the search and compare its exact output. The act is more deliberate than filling revision 1’s field, but acceptance remains structurally identical.

   Attacks: “**`prior_art` is generated, never typed.**” / “Schema valid … `prior_art` generated.” / “This is still forgeable … reproducible-checkable after the fact.”

6. **Even an authentic generated block can be a valid no-op and does not establish that prior art was examined.**

   Scenario: Run the real generator with an irrelevant query such as a ticket number or generic phrase that yields zero useful hits. The receipt passes because the search genuinely executed. Alternatively, it finds the relevant report but the author never opens it; nothing requires a hit to appear in `sources`. The observed re-derivation failure remains possible.

   Attacks: “`--prior-art "<query>"`.” / “Running the search surfaces that file.” / “the only control worth anything is the one that executes.”

7. **The staleness model contradicts itself: L3 promises statistics that §3 forbids it from computing.**

   Scenario: L3 audits closed tickets and claims to report staleness. Section 3 says closed receipts are never re-staleness-checked. No close-time staleness result is stored, so L3 has neither permission nor persisted data from which to produce the statistic.

   Attacks: “Once a ticket is closed … **never re-staleness-checked**.” / L3: “`kind: none-required` rate, **and staleness, reported as statistics**.”

8. **L3 has no specified high-frequency trigger, so its route coverage may never execute.**

   Scenario: A web-UI or auto-close bypass occurs. Nobody manually runs the audit, and no PR is merged through `mise run land` afterward. The standing issue remains stale forever. Defining an audit command and an upsert destination is not a delivery schedule.

   Attacks: “**The standing audit. Every close route, at a high frequency.**” / “delivered as a **standing upserted issue**.” / “`mise run land` prints the current audit summary post-merge.”

9. **Crash recovery depends on an undefined receipt marker that conflicts with the exact-comment contract.**

   Scenario: The API creates the comment, then the process dies before recording its ID. On retry, the task must find a comment “carrying the receipt marker,” but the posted body is specified to be the exact `verdict`, and no marker format is defined. It either duplicates the comment or changes the body so it no longer exactly matches `verdict`.

   Attacks: “Posting checks for an existing comment **carrying the receipt marker**.” / “This exact text is posted as the ticket’s resolution comment.” / “Post `verdict` as the **resolution comment**.”

10. **The step-5 fix updates documentation but leaves the known raw-close emitter unchanged.**

    Scenario: Wayfinder follows its own emitted `gh issue close` command. The new hook denies it mid-sequence. Updating `docs/issue-tracker.md` may educate a human, but it does not change the skill output that the spec itself identifies as incompatible.

    Attacks: “the **wayfinder skill still emits the raw `gh issue close`, which L2 will deny mid-sequence**.” / “`docs/issue-tracker.md` … updated in the same change.”

11. **The map update happens after the irreversible remote outcome and has no durability gate.**

    Scenario: The comment is posted and the ticket closes; appending the map then fails or merely dirties a local file. The primary outcome has completed, the user has little reason to rerun, and neither L1 nor L3 checks whether the pointer was committed.

    Attacks: “`gh issue close <n> --reason completed`.” / “**Append the context pointer to the map’s Decisions-so-far**.”

12. **L1 has a race between validation and closure, while `verified_at` is only date-granular.**

    Scenario: The ticket body changes after step 4’s validation but before steps 5–6. The task posts and closes using a receipt verified against the earlier body. A date such as `2026-07-31` cannot order two same-day edits even without a race.

    Attacks: “`verified_at: 2026-07-31`.” / “`verified_at` predates the ticket’s last substantive body edit.” / “Order, failing closed at the first red step.”

13. **Step 6 can inject incorrect ticket context because “the current ticket” is undefined.**

    Scenario: A session delegates work unrelated to the active wayfinder issue—or has several tickets in context. Every subagent receives one receipt path and prior-art corpus without any specified ticket-resolution mechanism, contaminating unrelated work.

    Attacks: “Injects `additionalContext` into **every delegated agent: the receipt path for the current ticket**.”

## Round-1 findings genuinely closed

These revisions are real improvements:

- F4 is closed conceptually: the audit now includes every close reason.
- F6 is closed: review cross-field combinations are explicitly validated.
- F8’s missing input is closed: unlabelled tickets now require `--verdict`, although the new jump-to-step-5 bug remains.
- F13’s identity ambiguity is solved at the data-model level by storing the comment ID, although its write ordering is broken.
- F15 is closed: the 55% statistic is no longer misapplied to the scoped population.
- F16 is closed: L5 was removed.

F2, F3, F5, F9, F10/F14, and the staleness findings are not fully closed for the reasons above.

## Build-order safety

| Step | Assessment |
|---|---|
| 1 | **Unsafe:** impossible before the generator exists and historically misleading. |
| 2 | **Insufficient:** safe as scaffolding, but neither authenticity nor query relevance is enforced. |
| 3 | **Non-blocking but incomplete:** no invocation schedule; staleness reporting contradicts §3. |
| 4 | **Unsafe:** closes against a newly dirtied receipt and has an unlabelled-path failure. |
| 5 | **Unsafe:** activates a denial before the known raw-close emitter is actually changed. |
| 6 | **Not justified as written:** optional, unobserved benefit, and “current ticket” resolution is undefined. |

## Decisive answers to §11

1. **It relocates fabrication; it does not resist it at acceptance time.** Resistance requires L1 to rerun a deterministic, versioned search against a clean, identified corpus and compare the generated block.

2. **Advisory staleness can be useful as a pre-close diagnostic, but the post-close statistic is currently fiction.** Either store the close-time result or remove staleness from L3. URL age also needs a defined threshold before “stale” has meaning.

3. **Forty characters are a longer checkbox, not a substantive bar.** Use enumerated eligibility conditions, independent review, or accept that `none-required` is an unrestricted opt-out.

4. **Yes.** Without a scheduled invocation, named owner, response expectation, and escalation/closure rule, the standing issue is merely a passive sink.

5. **Steps 1–5 are too much machinery in their present form.** The issue is not merely “twice on one ticket”; the machinery’s only research control still permits a valid irrelevant search, while its primary state machine is unsafe. A much smaller corrected design might earn its cost, but this one has not.

6. **Yes, ordinary backfilled receipts poison the corpus.** Add a distinct `pre-dates-policy` kind or an explicit grandfathered baseline. Record only objective facts recoverable now—ticket identity, existing resolution comment ID, close state/date, and links to surviving artifacts. Do not populate historical `sources`, `prior_art`, review, or “how reached” claims.
## Disposition of round 2 by the main session

**All 13 accepted; one accepted in part.** Combined with round 1 that is **29 of 29** findings
accepted across two rounds without a single refutation — which is the strongest available evidence
that reviewing the design rather than the implementation was the right call.

| # | Claim | Disposition | Fix in revision 3 |
|---|---|---|---|
| 1 | L1 dirties the receipt after verifying it committed, then closes against it | **ACCEPTED — the sharpest finding of either round** | `resolution_comment` is **deleted from the schema**. The binding moves into the *comment*: a machine-readable footer `<!-- receipt: docs/receipts/<n>.md@<sha> -->`. The receipt is never mutated after it is committed. Kills #1, #2 and #9 together. |
| 2 | The unlabelled branch jumps to a step that writes the receipt it skipped | **ACCEPTED** | Dissolved by #1's fix — no step writes a receipt. |
| 3 | Build step 1 needs the generator that ships in step 2 | **ACCEPTED — plain ordering bug** | Order swapped: the generator ships first, then the schema's first live instance. |
| 4 | The backfill manufactures decision provenance | **ACCEPTED** | Backfill drops to `kind: pre-dates-policy` carrying **only objectively recoverable facts** — ticket id, close date, existing comment, surviving artifact links. **No `sources`, no `prior_art`, no `review`, no "how reached" claim.** Codex's §11 Q6 answer adopted verbatim. |
| 5 | "Generated" has no machine-verifiable meaning; the fix relocates the lie | **ACCEPTED — and the fix is now real** | `mise run resolve` **re-runs the prior-art search itself** against the recorded `corpus_sha` (deterministic: a local search over a tracked corpus at a fixed SHA) and compares `result_sha256`. Fabrication becomes detectable at acceptance, not merely afterwards. |
| 6 | An authentic search can be a valid no-op — irrelevant query, or hits never opened | **ACCEPTED** | Every `prior_art` hit must appear in `sources` **or** carry an explicit `dismissed:` reason. Closes the found-but-never-opened half. ⚠️ The irrelevant-query half **cannot be closed by machine** and is recorded as a residual hole, not papered over. |
| 7 | L3 promises staleness statistics §3 forbids it computing | **ACCEPTED — real self-contradiction** | Staleness removed from L3 entirely. It is a **pre-close diagnostic only**. |
| 8 | L3 has no invocation schedule, so its coverage may never run | **ACCEPTED** | Wired to the existing scheduled `refresh.yml`, the same trigger that upserts the `tool-currency` standing issue. A named trigger, not an aspiration. |
| 9 | Undefined marker conflicts with the exact-comment contract | **ACCEPTED** | Dissolved by #1's fix; the footer *is* the marker and it is defined. |
| 10 | Updating the doc does not change the skill's emitted raw close | **ACCEPTED IN PART** | True that it is instruction-following, not enforcement. But the mechanism is **precedented and working**: `docs/issue-tracker.md` is what the wayfinder skills read for tracker conventions, and it already redirects `gh pr create` → `mise run ship` the same way. The guard's deny reason reaches Claude, so a mid-sequence denial is recoverable rather than terminal. Recorded as a known weakness with its precedent, not as solved. |
| 11 | The map append happens after the irreversible close, with no durability gate | **ACCEPTED** | Order changed to validate → comment → **map append** → close. The least recoverable step goes last. |
| 12 | Validate/close race, and `verified_at` is date-granular | **ACCEPTED** | `verified_at` becomes a full ISO-8601 timestamp; the ticket's `updated_at` is re-checked immediately before close. |
| 13 | `SubagentStart`'s "current ticket" is undefined | **ACCEPTED** | **L4 is cut.** Combined with L5's removal in revision 2, the design is now only its enforcement spine. |

### On §11 Q5 — "is this too much machinery for a failure observed twice?"

Codex's answer: *"Steps 1–5 are too much machinery in their present form… A much smaller corrected
design might earn its cost, but this one has not."* Taken. Cutting L4, L5 and the backfill leaves
four things — generate prior art, verify it at resolve, redirect the close, report on a schedule.
That spine is what revision 3 specifies. The judgement that it earns its cost is the author's and is
flagged for Ray explicitly rather than assumed.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the spec under review across
  both rounds, and the issue/label/timeline/transcript probes behind the disposition tables.

---

# Round 3 — same reviewer, revision 3 of the spec

Same invocation, same no-disk constraint. Codex was shown §10's table of what rounds 1–2 forced and
told not to re-litigate closed findings. It was asked directly whether the honest answer to §11 Q6 is
"do it by hand three times first", and told to say so unambiguously if it was.

**Verdict: `do-not-build`.** 13 findings. Its closing line: *"Revision 3 is better than revision 2
because it removed ineffective layers and the post-commit mutation, but it introduced an incoherent
L1 branch and still lacks a reproducible, durable verification protocol."*

## Verbatim

VERDICT: `do-not-build`

## FINDINGS

1. **The non-wayfinder branch is internally impossible.** A non-wayfinder ticket jumps to step 5 without a receipt, but step 5 needs `prior_art`, step 6 needs `verified_at`, and step 7 requires a receipt footer. Scenario: `mise run resolve -- 418 --verdict "Done"` reaches step 5 and has no `corpus_sha` to search. Attacked: **“No `wayfinder:*` label → skip every receipt check … and jump to step 5. Nothing in steps 5–8 touches a receipt.”**

2. **The freshness check probably invalidates itself (`unverified`).** If posting a GitHub comment advances the issue’s `updated_at`, step 7 changes the value step 9 requires to remain unchanged; the first run posts but cannot close, while subsequent runs reject the receipt as stale because the tool’s own comment is newer than `verified_at`. Attacked: **“Re-check `updated_at` is unchanged since step 6.”**

3. **“Committed” is still not durable.** Step 3 accepts a receipt committed only on a local or disposable feature branch. Scenario: resolve posts the footer and closes the ticket, then the branch is abandoned or never pushed; the durable repository has neither receipt nor referenced blob. Attacked: **“Receipt is committed and clean — `git ls-files --error-unmatch` and `git diff --quiet HEAD --`.”**

4. **`result_sha256` is not reproducible because the byte protocol is unspecified.** “Raw search output” varies with search engine and version, regex interpretation, config files, locale, path order, path prefix, line endings, color, and final newline. Two correct implementations can reject each other’s valid receipts. Attacked: **“That is deterministic and cheap … the output either hashes to `result_sha256` or it does not.”**

5. **The verified hash does not bind the declared hit list.** The stated verifier compares only `result_sha256`; the schema merely requires every *listed* hit to have a resolution. Scenario: a real search finds an inconvenient report, the author deletes that item from `hits`, retains the genuine raw-output hash, and passes. Attacked: **“Re-run the recorded `query` … and compare `result_sha256`”** and **“Requiring every hit to be read or dismissed in writing closes the ‘found it and ignored it’ half.”**

6. **L3 does not execute the sole machine-verifiable control on the routes it exists to cover.** The audit checks for a “well-formed” receipt but does not say it re-runs prior-art verification. Scenario: a web close bypasses L1; a later hand-written receipt with a random hash satisfies schema and clears the retrospective audit. Attacked: **“Every closed wayfinder ticket … has a committed, well-formed receipt.”**

7. **Cutting the backfill contradicts the audit’s universal scope.** The optional baseline leaves all five existing closed wayfinder tickets in immediate violation. The first scheduled run therefore creates known inherited debt, undermining the claimed false-positive measurement and training users to ignore the standing issue. Attacked: **“Every closed wayfinder ticket … has a committed, well-formed receipt”** versus **“Optional, separately decidable: a `pre-dates-policy` baseline for the 5 closed wayfinder tickets.”**

8. **`corpus_sha` is not durable in the stated squash-merge workflow.** A receipt generated against a feature-branch commit can survive squash as a file while the recorded commit becomes unreachable from a fresh clone; `git show <corpus_sha>:<path>` then cannot reproduce anything. Attacked: **“Re-run it via `git show <corpus_sha>:<path>`”** and **“this repo squash-merges.”**

9. **The footer binds a blob marker, not the comment’s asserted verdict.** L3 checks that a comment contains the marker, but not that its body equals `verdict`; editing the comment while retaining the footer—or attaching the marker to unrelated text—passes. Attacked: **“The two are kept from drifting by the footer.”**

10. **The shown seven-hex footer is not an exact identity.** A short Git abbreviation can become ambiguous as the object database grows; it is also not enough to establish reachability at the recorded path. Use the full object ID and specify the Git object format. Attacked: **“Identity … by an exact marker”** and **“`<!-- receipt: docs/receipts/449.md@8f2e1c9 -->`.”**

11. **The map append has no specified idempotency key.** Scenario: step 8 succeeds and the process dies before step 9; rerunning can append the same pointer twice even though the comment is deduplicated. Attacked: **“Every step is idempotent and the verb is resumable.”**

12. **The final freshness check still has an unavoidable race.** A human can edit the ticket after step 9’s read but before `gh issue close`; the tool then closes against evidence verified for the previous state. Attacked: **“the order is load-bearing, because the least recoverable action goes last.”** The spec must either name this as residual TOCTOU or use a real conditional mutation if GitHub offers one.

13. **The implementation remains disproportionate to its evidence.** Two misses on one ticket do not justify two commands, a schema, validator, audit command, CI contract, scheduled workflow, standing issue, resolver, hook rule, and documentation mutation—especially when the only executed control accepts a bad query. Attacked: **“Steps 1–5 remain. Is the spine now proportionate…?”**

## §11 ANSWERS

1. **No.** It becomes deterministic only after defining a versioned canonical search protocol: engine and version, query semantics, ignored configuration, locale, corpus enumeration and sorting, encoding/error policy, output schema, newline rules, and canonical serialization. Hash canonical structured results, not tool stdout.

2. **A current corpus change should not break it if the old snapshot is searched exactly.** The receipt directory is outside the stated corpus. The real problem is availability: a feature-branch `corpus_sha` may disappear after squash or may not exist in another clone.

3. **A full blob OID is stable across amend, rebase, and squash if the receipt bytes remain identical.** The commit changing does not change the blob. But the shown short prefix is inadequate, and a blob OID proves neither path nor durable repository reachability. If the bytes change, the old comment binds the old receipt and a rerun may post a second resolution comment.

4. **No—cutting `SubagentStart` was correct.** It would not have fired for either observed failure and would not prove delegated research was read or understood. Delegation remains subject to the same receipt attestations; adding instrumentation would be theater.

5. **It is fatal to the claim that the executed control prevents the observed prior-art failure.** It is not fatal to a receipt’s value as a reviewed manual record. The machine verifies that *a query* ran, not that the necessary search happened.

6. **Yes: do it by hand for the next three wayfinder tickets.** Use a fixed template, manually record searches and resolutions, and measure actual repetition, review value, query drift, and failure modes. Do not build the automation spine before that pilot.

Revision 3 is better than revision 2 because it removed ineffective layers and the post-commit mutation, but it introduced an incoherent L1 branch and still lacks a reproducible, durable verification protocol.
---

## Disposition of round 3 by the main session

**All 13 accepted. Two were verified by direct probe, and both are decisive.**

### The two that end the build

**F2 — the freshness check can only fail. CONFIRMED BY MEASUREMENT.**
Codex marked this `unverified` because it could not reach GitHub. Probed:

| Issue | last comment `created_at` | issue `updated_at` |
|---|---|---|
| #433 | `2026-07-30T23:18:21Z` | `2026-07-30T23:18:22Z` |
| #434 | `2026-07-31T00:21:59Z` | `2026-07-31T00:22:03Z` |

Posting a comment **advances `updated_at`**. So L1 step 7 posts the verdict and step 9 then requires
`updated_at` to be *unchanged* — a gate that **can never pass**. That is precisely the failure class
`.claude/rules/probes-need-a-control-arm.md` exists to name ("a check that can only fail"), written
into a spec that cites that rule.

**F8 — `corpus_sha` is unreachable after a squash merge. CONFIRMED BY MEASUREMENT.**
`git merge-base --is-ancestor feat/436-builder-skills-and-research-loop origin/main` → **false**
(control: `60d2558` → true). This repo squash-merges, so a commit recorded on a feature branch is not
an ancestor of `main` and `git show <corpus_sha>:<path>` cannot resolve it in a fresh clone. The
prior-art re-verification — **the only machine-verifiable control in the entire design** — breaks by
construction under the repo's own merge strategy.

### The rest

| # | Claim | Disposition |
|---|---|---|
| 1 | The non-wayfinder branch is internally impossible — jumps to a step needing `prior_art`/`verified_at`/footer | **ACCEPTED.** Revision 3 renumbered the steps and left the branch pointing at the wrong one. Third revision, third incarnation of the same bug: the unlabelled path has never once been coherent. |
| 3 | "Committed" is not durable — a local or abandoned branch passes | **ACCEPTED.** The check proves the bytes are in *a* commit, not that they reach `main`. |
| 4 | `result_sha256` is unreproducible — engine, version, locale, ordering, newlines all unspecified | **ACCEPTED.** Fixing it needs a versioned canonical search protocol, which is a project in itself. |
| 5 | The hash does not bind the declared hit list — delete an inconvenient hit and the raw hash still matches | **ACCEPTED.** The verification and the schema check different objects. |
| 6 | L3 never re-runs the one verifiable control on the routes it exists to cover | **ACCEPTED.** |
| 7 | Cutting the backfill leaves all 5 closed wayfinder tickets in immediate violation | **ACCEPTED.** Removing the fiction re-created the debt. |
| 9 | The footer binds a blob, not the verdict text | **ACCEPTED.** |
| 10 | A 7-hex abbreviation is not an exact identity | **ACCEPTED.** |
| 11 | The map append has no idempotency key | **ACCEPTED.** |
| 12 | Residual TOCTOU between the last read and the close | **ACCEPTED** as residual and now unfixable-by-ordering, given F2. |
| 13 | The implementation is disproportionate to its evidence | **ACCEPTED — and it is the finding that decides the outcome.** |

### The answer to the proportionality question

Asked directly, the reviewer was unambiguous:

> **"Yes: do it by hand for the next three wayfinder tickets.** Use a fixed template, manually record
> searches and resolutions, and measure actual repetition, review value, query drift, and failure
> modes. **Do not build the automation spine before that pilot."**

And on the control that the whole design was built around:

> *"It is fatal to the claim that the executed control prevents the observed prior-art failure. It is
> not fatal to a receipt's value as a reviewed manual record. The machine verifies that* a *query ran,
> not that the necessary search happened."*

That is the recommendation carried forward: **adopt the receipt as a hand-written artifact, pilot it
on three tickets, and defer every line of automation** until the pilot says which part is worth
building. The spec remains the design of record for what would be built if it is.

## Running total across three rounds

| Round | Verdict | Findings | Accepted | Refuted |
|---|---|---|---|---|
| 1 | `do-not-build` | 16 | 16 | 0 |
| 2 | `do-not-build` | 13 | 13 | 0 |
| 3 | `do-not-build` | 13 | 13 | 0 |
| **Total** | — | **42** | **42** | **0** |

Every one found before a line of code existed.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the spec under review across all
  three rounds, and the issue/label/timeline/transcript/merge-base probes behind the dispositions.
