# Spec — ticket-bound resolution receipts

> # ⛔ NOT FOR BUILD
>
> **Decided 2026-07-31 (Ray): the automation in this document is DEFERRED. Nothing below §4 is
> being built.** What ships instead is `docs/receipts/TEMPLATE.md` — the receipt, hand-written —
> piloted on the next three `wayfinder:*` tickets. See § "Decision".
>
> This document remains the **design of record**: it is what would be built if the pilot shows the
> automation is worth its cost, and it carries the 42 reasons the first three attempts were not.
> Do not resurrect any layer from it without reading § "Decision" first.

**Status: revision 3, superseded by the pilot decision. No code was ever written.**

Three adversarial review rounds by Codex (GPT-5.6, cold, cross-family, no disk access) returned
`do-not-build` **every time**: 16 findings, then 13, then 13 — **42 in total, 42 accepted, 0
refuted**. All three are persisted verbatim with their disposition tables at
`docs/research/kb/reports/agents/codex-adversarial-449-receipt-spec.md`. §10 records what each round
changed.

That is the point of the exercise: **42 defects found at zero implementation cost.** Revision 3 is
materially smaller than revision 1 — two whole layers and the backfill were cut, not added — and it
was still not buildable.

Resolves scope items 1–4 of [#449](https://github.com/ray-manaloto/dotfiles/issues/449). Supersedes
nothing: `docs/specs/research-nudge-hooks.md` stays under its NO-SHIP banner as the design that was
tried, and its Appendices A–D are the evidence base this spec rests on.

**The claim in one sentence:** findings 1, 3 and 5 of the *earlier* review all want the same missing
artifact — a durable, ticket-keyed record of how a decision was reached — and of everything such a
record could contain, **exactly one part can be machine-verified**, so the design is built around
that part and honest about the rest.

---

## 0. What was measured before designing

Every number was taken this session, both arms armed. The design is downstream of them.

| Fact | Value | Control arm |
|---|---|---|
| Issues closed all-time | **57**, every one `stateReason=COMPLETED` | 96 open, so the query sees both states |
| Closed since 2026-07-01 | **35** | — |
| Closed by a commit/PR (auto-close) | **3 of 57** (#3, #8, #249) | the field *does* populate, so the other 54 nulls are a real negative, not a blind probe |
| `gh issue close` typed through a Claude Bash call | **30 commands / 436 transcripts / 8 project dirs** | `gh pr` → **853**, so the extractor is not blind |
| Of the **last 20** closed issues, seen by the hook | **11** (439, 435, 434, 433, 432, 397, 394, 369, 343, 299, 288) | — |
| …not seen | **9** (418, 400, 391, 380, 332, 327, 294, 290, 265) | widening the sweep 182 → 436 transcripts added **none** of the 9 ⇒ they were closed outside Claude entirely |
| Issues carrying any `wayfinder:*` label | **16** — 11 open, **5 closed** | 96 open total, so the filter is selective, not vacuous |
| …of those 5 closed, seen by the hook | **5 of 5** (439, 435, 434, 433, 432) | the same extractor reports 9 *un*seen closes, so it can produce the other answer |
| …of the 9 unseen closes, carrying `wayfinder:*` | **0 of 9** — they are `auto-queue`, `bug`, `question`, or unlabelled | the extractor found the label on 16 other issues, so it is not blind to it |
| `gh issue close` escape flags | `-r/--reason {completed \| not planned \| duplicate}`, `--duplicate-of <n>` | read from `--help`, not assumed |
| `hook_guard.py` output shapes today | **`deny` only** (`pretooluse_main`, `decide() -> str \| None`) | — |
| `docs/research/kb/reports/agents/` | **17** files; **2** carry a ticket number | — |

### What the 55% does and does not license

⚠️ **The headline "a hook sees ~55% of closes" describes a population this spec does not govern**, and
revision 1 wrongly used it to justify the audit layer. Measured: **0 of the 9 hook-unseen closes carry
a `wayfinder:*` label**, and all 5 closed wayfinder tickets went through a Claude `gh issue close`.
On the scoped population the observed miss rate is **0 of 5** — and n = 5 is far too small to call a
rate in either direction.

The audit layer (§4.2 L3) is justified by the **mechanism, never the rate**: close routes exist that a
PreToolUse hook structurally cannot see — the web UI, a human's own terminal, PR auto-close — and 9
real closes demonstrably took them. That argument needs no percentage and does not weaken if the
scoped rate stays at 0.

---

## 1. The artifact — a resolution receipt

### 1.1 Where it lives

```
docs/receipts/<issue-number>.md      # e.g. docs/receipts/449.md
```

**Tracked, one file per ticket, named by the bare issue number.**

- **Tracked — and *checked* to be tracked.** §4.2 L1 verifies the file is in the index with no
  uncommitted modifications. A receipt that exists only in a working tree is exactly as durable as no
  receipt at all.
- **Immutable once committed.** Nothing in this design writes to a receipt after its commit — see
  §1.4, which is where revision 2's worst bug lived.
- **Bare number, no slug** — the lookup is a total function of the issue number:
  `Path("docs/receipts/449.md").exists()`. No glob semantics to get wrong, no way to end up with two
  receipts for one ticket. The cost is a directory that reads as `433.md 449.md …`.
- **`docs/`, NOT `docs/research/kb/`** — and the repo already encodes why. `hk-common.pkl:52`
  excludes `docs/research/kb/**` from **every** hk builtin, on purpose, so a typo-fixer can never edit
  a **verbatim** persisted agent report. A receipt is *authored* content that should be linted like
  any other doc; filing it in the kb tree would silently opt it out of every markdown check. The
  exclusion's own comment says it: *"Authored docs under `docs/` are still checked."*

The receipt **links to** the verbatim evidence in `docs/research/kb/reports/agents/`; it never copies
it.

### 1.2 Schema

```yaml
---
issue: 449
kind: research | decision | task | none-required | pre-dates-policy
reason: >-                        # REQUIRED when kind == none-required
  Label applied for tracking only; the answer was already fixed by #435's resolution.
verdict: >-
  One sentence. This exact text is the body of the ticket's resolution comment.
provenance:
  branched_from: 5f90f99c1e4a…    # 40-char SHA. Provenance ONLY — never a staleness input.
  verified_at: 2026-07-31T14:02:11Z   # full ISO-8601; a date cannot order two same-day edits
sources:                          # what was ACTUALLY opened. Empty is illegal except pre-dates-policy.
  - local: hk-common.pkl
    sha: 8f2e1c9…                 # `git hash-object` of the blob AS READ
  - url: https://www.chezmoi.io/reference/configuration-file/hooks/
    fetched: 2026-07-31
    via: llms.txt                 # which step of research-doc-sources.md answered
prior_art:                        # GENERATED and RE-VERIFIED. See §1.3.
  query: "chezmoi hooks"
  corpus: docs/research/kb/reports/agents/
  corpus_sha: 60d2558…            # repo SHA the search ran against
  result_sha256: 3ab9…            # hash of the raw search output
  ran_at: 2026-07-31T14:02:11Z
  hits:                           # EVERY hit must be resolved — read it, or dismiss it in writing
    - path: docs/research/kb/reports/agents/deep-research-takeover-20260730.md
      resolution: in-sources
    - path: docs/research/kb/reports/agents/graphify-mining.md
      resolution: dismissed
      why: "Covers graph ingestion, not chezmoi's config surface."
review:
  lens: codex-reviewer | grok-reviewer | mattpocock-skills:code-review | none
  verdict: clean | needs-attention | not-run
  findings: 29
  disposition: docs/research/kb/reports/agents/codex-adversarial-449-receipt-spec.md
---
```

**Every field is REQUIRED. `none` / `not-run` / `none-required` are legal values; omission is not.**

That decision comes from a failure this repo already had: session 2026-07-31-c's Standards review axis
never delivered, and the gap was visible only because it was *written down as N/A* rather than left
implied. A schema permitting omission cannot distinguish "no adversarial review ran" from "someone
forgot the field."

**Presence is not enough.** These cross-field rules are validated too — revision 1 accepted
`lens: none` + `verdict: clean` + `findings: 5` + empty `disposition` as well-formed:

| Rule | Rejects |
|---|---|
| `lens: none` ⇒ `verdict: not-run` and `findings: 0` | a verdict from a review that never ran |
| `findings > 0` ⇒ `disposition` names an existing path | findings with nowhere to read them |
| `kind: none-required` ⇒ `reason` ≥ 40 chars | a one-token opt-out |
| **`prior_art` required for every kind except `pre-dates-policy`** | opting out of the one control that is not self-reported |
| every `prior_art.hits[]` has `resolution: in-sources` **and appears in `sources`**, or `dismissed` **with a `why`** | finding the prior art and never opening it |
| `kind: pre-dates-policy` ⇒ `sources`, `prior_art`, `review` **absent** | a reconstructed history presented as a record |

### 1.3 The one control that is not self-reported

Revision 1 claimed `prior_art` was prospective — that its fields "cannot be filled without running
the search." **False, and it was the spec's central claim.** Revision 2 made the block *generated*;
review round 2 correctly observed that "generated" had no machine-verifiable meaning, so an author
could type a plausible query, corpus SHA, hit list and random hash and pass every rule.

**Revision 3 closes it: `mise run resolve` re-runs the search itself and compares.**

The search is a local text search over a tracked corpus at a recorded `corpus_sha`. That is
**deterministic and cheap** — re-run it via `git show <corpus_sha>:<path>` and the output either
hashes to `result_sha256` or it does not. Fabrication becomes detectable **at acceptance**, not
merely reproducible afterwards by someone who thinks to check.

**What this still does not close, stated plainly:** a *genuine* search with a badly-chosen query
returns nothing useful and passes. Requiring every hit to be read or dismissed in writing closes the
"found it and ignored it" half; nothing machine-checkable closes "asked the wrong question." That is
a residual hole (§8.1), not a solved problem.

Everything else in the receipt is an **attestation, not a proof**. No gate can verify a cited source
was read or understood. Their value is that the claim must be written, lands in a reviewed diff, and
is falsifiable afterwards — the same epistemics as the `since` dates on the guard's rules, which
nothing verifies either and which work anyway.

### 1.4 The receipt is never written after it is committed

Revision 2 had L1 verify the receipt was committed, then write the posted comment's id back into it,
then close the ticket — leaving HEAD holding a receipt without the id and the only valid version in a
dirty working tree. **The sharpest finding of either round, and it was self-inflicted** by revision
2's own fix for comment identity.

The binding moves to the **comment**. Every resolution comment ends with:

```html
<!-- receipt: docs/receipts/449.md@8f2e1c9 -->
```

The footer names the receipt path and the blob SHA of the receipt as committed. That gives:

- **Identity** — the audit finds *the* resolution comment by an exact marker, not by text-matching a
  verdict sentence an older comment might also contain.
- **Idempotency** — "has this already been posted?" is "does a comment with this marker exist?", so a
  crashed run re-runs without duplicating.
- **Immutability** — the receipt is committed once and never touched again, so there is no window in
  which the committed and working copies disagree.

---

## 2. Binding to a ticket

Two routes: the **filename** (`docs/receipts/<n>.md`, what the gate resolves) and the frontmatter
**`issue: <n>`** (what the contract validates). A mismatch is a hard failure.

Both are written by the same scaffold in the same breath, so this is **not** independent redundancy
against authoring error — it guards against later hand-editing and against a copied receipt, which is
the realistic drift. Said plainly because revision 1 implied more than it delivers.

Today `docs/research/kb/reports/agents/` is topic+date named with **2 of 17** files carrying a ticket.
**That convention does not change** — renaming 17 verbatim archive files would edit records the
persistence rule exists to protect. A thin ticket-keyed layer sits alongside and links into it.

---

## 3. Staleness — a pre-close diagnostic, and nothing else

Revision 1's model was incoherent in three ways and revision 2's still contradicted itself. It is now
scoped down to what it can honestly do.

**What broke it:** a single `base` SHA diffed against HEAD meant citing a file and then editing it as
part of the same work made your own receipt stale; a valid 2026 receipt went stale forever the first
time an unrelated 2027 commit touched a cited file; a post-close clarification to a ticket body
invalidated a receipt that was correct when written; and revision 2 then had the audit report
staleness statistics for closed receipts it had just forbidden itself to check.

**The replacement:**

| Signal | How | Blocking? |
|---|---|---|
| `local:` source changed since read | current `git hash-object` ≠ the recorded per-source `sha` | **no — printed at resolve time** |
| `url:` source age | `fetched` date | **no — printed at resolve time** |
| ticket edited since the receipt | `verified_at` vs the ticket's `updated_at` | **yes — and only before close** |

Three rules:

1. **Per-source hash, not a global diff.** Each `local:` source records the blob hash *as read*. Edit
   the file afterwards, re-read it, and the scaffold re-records — so the receipt says what you
   actually read, which is the only thing staleness can honestly mean.
2. **Advisory except the ticket-edit rule.** A changed source is printed; it never blocks. A file
   changing does not mean the reading was wrong, and a check that cannot tell the difference must not
   hold a gate.
3. **Never checked after close, and never reported after close.** A closed ticket's receipt documents
   the evidence used *then*. Staleness is therefore **absent from the audit entirely** — revision 2
   promised a statistic it had no data to compute.

---

## 4. Enforcement

### 4.1 Two harness facts that forbid the obvious designs

`permissionDecisionReason` on `allow`/`ask` reaches **the user, not Claude** (hooks.md:1551, verbatim,
control-armed: `additionalContext` → 40 hits, a bogus token → 0). Only `deny` carries a reason back to
Claude, so a close-time `ask` can never tell Claude what to do about it — which killed the previous
design's tier 1.3.

And a **harness-side timeout kill never reaches `fail_open()`** — *a hook cannot record its own
death*. Anything load-bearing lives where failure is loud.

### 4.2 The layers — three, down from five

**L1 — `mise run resolve -- <n>`. The gate.**

Resolution stops being a raw `gh` command and becomes a mise task, exactly as `gh pr create` became
`mise run ship` — the repo's proven enforcement pattern reused rather than reinvented
(`.claude/rules/mise-tasks-only.md`). **The task has network**, which dissolves the offline/online
tension: it reads labels, validates against the live ticket, and acts.

**Every step is idempotent and the verb is resumable**; a partial run followed by a re-run converges
and never double-posts (the comment footer, §1.4, is what makes that decidable).

Order — and the order is load-bearing, because the least recoverable action goes **last**:

1. **Read the ticket.** No `wayfinder:*` label → skip every receipt check, require an explicit
   `--verdict "<text>"`, and jump to step 5. Nothing in steps 5–8 touches a receipt, so this branch is
   now coherent. *(Ray's decision, 2026-07-31: receipts bind wayfinder tickets only — ~1 per real
   decision, not ~35/month of near-empty files, which is precisely the reflex the earlier review
   predicted for the `ask` dialog.)*
2. **Receipt exists**, parses, `issue:` matches the filename.
3. **Receipt is committed and clean** — `git ls-files --error-unmatch` *and* `git diff --quiet HEAD --`.
4. **Schema valid** — every field, every cross-field rule (§1.2). Staleness printed, not enforced.
5. **Prior art re-verified** — re-run the recorded `query` against `corpus` at `corpus_sha` and
   compare `result_sha256`. Mismatch is a hard failure. This is the only step that verifies rather
   than reads (§1.3).
6. **Ticket freshness** — `updated_at` not newer than `verified_at`.
7. **Post the verdict** as the resolution comment, with the §1.4 footer.
8. **Append the map pointer** to Decisions-so-far. Skipped with a printed notice when the ticket is
   not a child of a `wayfinder:map` issue — #449 itself is deliberately not one.
9. **Re-check `updated_at` is unchanged since step 6**, then `gh issue close <n> --reason completed`.

Steps 7→9 put the map append *before* the close, because a failure after the close leaves the user
with no reason to re-run and the pointer permanently missing.

Failure prints the offending item and the remediation: **`mise run receipt -- <n>`**, which scaffolds
the file from the ticket with every field present, `provenance` filled, and `--prior-art "<query>"` to
generate that block. A fail-closed gate with no way forward is an outage, not enforcement — this repo
has shipped that mistake once, when `gh pr merge` redirected KB PRs to a dotfiles-only task.

**L2 — PreToolUse deny on `gh issue close`. Redirect only.**

One new rule in `hook_guard.py`'s existing table: `gh issue close` → *"use `mise run resolve -- <n>`"*.

**The guard's contract does not change.** It stays deny-or-silence: no `ask`, no `allow`, no
`additionalContext`, no new output shape, no change to `command_audit`'s classifier or to
`decide() -> str | None`. That is a large amount of new surface the previous design required and this
one does not.

Native escapes stay allowed at the hook — `--reason "not planned"`, `--reason duplicate`,
`--duplicate-of <n>`. A close that is not a completion should not be forced through a resolution verb.
**They are not a free pass**: L3 reads *every* closed wayfinder ticket regardless of reason, because
"hook allows non-completed" plus "audit reads only completed" composed into a second complete bypass.

Coverage on the scoped population is 5 of 5 (§0), n = 5. This layer stops *the agent* bypassing the
verb; it is not the coverage story.

**L3 — the standing audit. Every close route, on a named schedule.**

`dotfiles-setup receipts audit`:

- every **closed** wayfinder ticket — **any `stateReason`** — has a committed, well-formed receipt;
- selection is by **label history via the issue timeline**, not current labels, so removing the label
  before closing does not erase the requirement;
- every receipt names a real issue; no orphans; no duplicate `issue:`;
- every closed ticket has a comment carrying the §1.4 footer, and the footer's blob SHA matches the
  committed receipt;
- `kind: none-required` and `pre-dates-policy` rates reported. **No staleness** (§3).

⚠️ **Control-arm gap.** `labeled` events are observable here (13 in the last 100 issue events).
`unlabeled` → **0** — no label has ever been removed in this repo, so the removal half is
*documented but unobserved*. **Arm it before building**: add and remove a label on a scratch issue and
confirm the event appears. Do not ship on the documentation alone.

**Delivery — named triggers, not an aspiration.** The audit's findings are repo-wide debt an unrelated
PR did not cause; failing that PR's CI on inherited debt is stranding. So:

- **blocking** only on receipts the PR itself touches (schema, filename↔frontmatter, dead links) — an
  offline `suites.toml` contract;
- **scheduled** — the audit runs in the existing `refresh.yml`, on the same trigger that already
  upserts the `tool-currency` standing issue, and upserts its own;
- **`mise run land`** prints the current summary post-merge.

**L1 is the enforcement; L3 is detection across the routes L1 cannot see.** Its coverage is of
*routes*, not *moments* — it finds a bad close whenever it next runs, not as it happens.

---

## 5. Divergence from wayfinder, recorded deliberately

| | Wayfinder `SKILL.md` | This repo |
|---|---|---|
| Where the verdict goes | resolution comment (`:125`) | **same** — adopted verbatim |
| Where evidence goes | *"a throwaway `research/<name>` branch"* (`:115`) | **tracked `docs/`**, per `.claude/rules/agent-report-persistence.md` |
| Restating | *"a decision lives in exactly one place — its ticket"* (`:23`) | **same** — the receipt is the *method*, the comment is the *answer*; different content, not mirrored |

The reason for the one divergence: a throwaway branch does not survive a clone. Recorded so a future
session does not "fix" it back.

**Which half the gate reads:** the **file**. Not because the comment is less authoritative — for a
human it is more so — but because the file is the half a check can read. The two are kept from
drifting by the footer (§1.4), which names the exact committed blob the comment was posted for.

---

## 6. What this would have caught — and what it would not

Both observed misses were on **#436**, which carries `wayfinder:grilling`, so the scope binds them.

| Miss | Caught? | By what |
|---|---|---|
| Five #436 decisions taken before reading chezmoi's docs (it ships native `[hooks]`) | **Partially — and late.** | `sources:` must name chezmoi's docs or be visibly empty, and empty is illegal. It fires at *resolution*, not at *decision*: it converts an invisible miss into a visible one at a defined checkpoint. **It does not make research happen.** |
| chezmoi-vs-mise re-derived despite `deep-research-takeover-20260730.md` answering it | **Yes — conditional on the query.** | The search is generated *and re-verified*, and every hit must be read or dismissed in writing. A reasonable query surfaces that file and forces a written response to it. A bad query still passes (§1.3). |

**One control executes; everything else is a written claim a reviewer can check later.** That is the
whole spec, and stating it that plainly is what two review rounds bought.

## 7. Deliberately not proposed

- **`SubagentStart` injection (was L4).** Cut in revision 3: "the current ticket" was undefined for a
  session holding several, and the premise for prioritising it was already refuted — both observed
  misses launched **0** subagents (`6b4602f4`: Agent=0, control Bash=132; `d4299a7a`: 0/48) against
  **239** `Agent` launches project-wide. It would have fired zero times in the session it was proposed
  to fix.
- **`UserPromptSubmit` reminders (was L5).** Cut in revision 2 as surface without enforcement. For the
  record the reason is **not** the timeout the previous spec asserted: measured on the live guard
  wrapper, 20 clean runs on a loaded host, min 256 / median 1013 / max 1978 ms = **6.6% of the 30 s
  budget, ~15× headroom**. Timeout was never the risk; silent absence was.
- **Backfilling ordinary receipts for the 5 already-closed wayfinder tickets.** Writing `sources` and
  `prior_art` for decisions nobody now remembers manufactures provenance. If a baseline is wanted, it
  is `kind: pre-dates-policy` carrying only objectively recoverable facts — ticket id, close date, the
  existing resolution comment, links to surviving artifacts — and **nothing about how the decision was
  reached**.
- **Tier 2, the statusline context-budget sensor.** Split off per the earlier review.
- **A new rule file.** Already measured to have failed: the rule saying *research the tool's release
  notes first* is unscoped, therefore eager, therefore loaded — and it did not fire, twice.
- **Retro-fitting ticket keys onto `docs/research/kb/reports/agents/`.** §2.

## 8. Known holes — named, not papered over

1. **A badly-chosen prior-art query passes.** The search is verified to have *run*; its *relevance* is
   not machine-checkable. §1.3.
2. **Everything except `prior_art` is attestation, not proof.** Accepted ceiling.
3. **The scope is a hand-applied label, so exemption is the default.** 11 of 96 open issues carry
   `wayfinder:*`; nothing forces a decision-shaped ticket to be labelled one. L3's label-history
   selection closes the *removal* half; the *never-applied* half stays open by design.
4. **L2 redirects; it does not compel the emitter.** The wayfinder skill still emits a raw
   `gh issue close`, and updating `docs/issue-tracker.md` is instruction-following, not enforcement.
   The mechanism is precedented and working — that file is what the wayfinder skills read for tracker
   conventions and it already redirects `gh pr create` → `mise run ship` — and a `deny` reason reaches
   Claude, so a mid-sequence denial is recoverable. It is still the weakest link in the chain.
5. **The guard is a redirect guard, not a sandbox.** `$(…)`, `sh -c`, `eval`, aliases and base64 all
   fail open by documented design. This gate is discipline, not security.
6. **L3 is retrospective** — it detects, it does not prevent.
7. **PR auto-close bypasses L2 entirely** — 3 of 57 historically, 0 of the last 20. L3 catches it.
8. **The `unlabeled` timeline event is unobserved in this repo** and must be armed before the
   label-history fix is relied on. §4.2 L3.
9. **A standing issue nobody reads is a passive sink.** Named as a real risk by review round 2; the
   scheduled trigger fixes *delivery*, not *attention*.
10. **Nothing here makes `/clear`, `clear-prep`, `handoff`, `resume` or `wayfinder` invocable by
    Claude.** All are `disable-model-invocation: true` and `/clear` is a CLI command. Automation
    prepares and nudges; the keystroke stays human.

## 9. Build order

Each step is independently useful, independently revertible, and depends only on what precedes it —
revision 2's step 1 required a generator that did not ship until step 2.

| # | Ships | Why this order |
|---|---|---|
| 1 | `mise run receipt -- <n>` — scaffold + **`--prior-art` generation** | The generator must exist before any receipt can satisfy the schema. Useful alone: it makes the search reproducible even with nothing gating on it. |
| 2 | `docs/receipts/` + the schema + validator + **`449.md` as the first live instance**, produced by step 1's tool | Dogfooding #449 with its own generated receipt is the control arm: if the tool cannot produce a valid receipt for the ticket that specified it, nothing else is worth building. |
| 3 | `dotfiles-setup receipts audit`, advisory, + the `suites.toml` contract for PR-touched receipts + the `refresh.yml` schedule. **Includes arming the `unlabeled` control.** | Detection layer measured for false positives before anything leans on it. |
| 4 | `mise run resolve -- <n>` | The gate. Only after 1–3 exist. Carries the §4.2 L1 order, the footer, and prior-art re-verification. |
| 5 | `hook_guard.py` redirect + `since` date + test, **and `docs/issue-tracker.md` § Wayfinding operations updated in the same change** | A redirect whose target the documentation does not name sends the reader nowhere. The doc that tells the session what to run must change with the guard. |

Optional, separately decidable: a `pre-dates-policy` baseline for the 5 closed wayfinder tickets (§7).

## 10. Review history

| Round | Verdict | Findings | Accepted | Structural changes it forced |
|---|---|---|---|---|
| 1 | `do-not-build` | 16 | **16** | `prior_art` generated not typed; receipt must be committed; staleness rewritten; audit reads label history and every close reason; standing issue instead of a CI gate; `UserPromptSubmit` cut; the 55% re-measured |
| 2 | `do-not-build` | 13 | **13** | Receipt never written after commit (comment footer instead); prior art **re-verified**, not merely generated; every hit read or dismissed; staleness removed from the audit; map append before close; build order reordered; `SubagentStart` cut; backfill reduced to `pre-dates-policy` |

**29 of 29 accepted, zero refuted.** Revision 3 is smaller than revision 1: two enforcement layers and
the backfill were removed, and one verification step was added.

## Decision — pilot by hand, defer the build (2026-07-31)

Round 3 was asked directly whether the honest answer was "do it by hand three times first". It was
unambiguous:

> **"Yes: do it by hand for the next three wayfinder tickets.** Use a fixed template, manually record
> searches and resolutions, and measure actual repetition, review value, query drift, and failure
> modes. **Do not build the automation spine before that pilot."**

Two of its findings were upgraded from `unverified` to **measured**, and both are fatal to the
design as written:

1. **The freshness gate can only fail.** Posting a comment **advances an issue's `updated_at`**
   (#433: comment `2026-07-30T23:18:21Z`, issue updated `…:22Z`; #434 the same). L1 step 7 posts the
   verdict and step 9 then requires `updated_at` to be unchanged. That check can never pass — the
   exact defect `.claude/rules/probes-need-a-control-arm.md` exists to name, written into a spec that
   cites that rule.
2. **The one machine-verifiable control cannot resolve its corpus.**
   `git merge-base --is-ancestor feat/436-… origin/main` → **false** (control: `60d2558` → true).
   This repo squash-merges, so a `corpus_sha` recorded on a feature branch is unreachable from a
   fresh clone and `git show <corpus_sha>:<path>` fails. Prior-art re-verification — the only thing
   in the design that verified rather than attested — breaks by construction.

And the ceiling was never going to move: a *genuine* search with a badly-chosen query passes every
check. The machine can verify that **a** query ran, never that the **right** question was asked.

### What ships instead

| Artifact | What it is |
|---|---|
| `docs/receipts/TEMPLATE.md` | The receipt, hand-written. Every field that existed only to serve a verifier — blob SHAs, `corpus_sha`, `result_sha256`, the comment footer — is **gone**. What remains is what a human reads. |
| `docs/receipts/449.md` | Instance #1 — this ticket's own receipt, written from the template. |
| this file | The design of record, plus 42 reasons. |

**Nothing else.** No `mise run receipt`, no `mise run resolve`, no `hook_guard.py` rule, no audit
command, no `suites.toml` contract, no scheduled workflow, no standing issue.

### The pilot

Write a receipt by hand for the next **three** `wayfinder:*` tickets. Then answer, from data rather
than design:

1. Which fields were filled with something real, and which became ritual?
2. Did anyone ever read a receipt after the ticket closed?
3. Did query drift actually happen — did a search miss prior art that was there?
4. What did writing it by hand cost, per ticket?

Only then reconsider automation, and only for the parts the pilot proves. The layers below are
available to lift from — with their findings attached.

## 11. Questions review round 3 answered

| # | Question | Answer |
|---|---|---|
| 1 | Is the prior-art search deterministic at a fixed `corpus_sha`? | **No.** Only after defining a versioned canonical search protocol — engine and version, query semantics, ignored config, locale, corpus enumeration and sorting, encoding policy, newline rules, canonical serialisation. Hash canonical structured results, never tool stdout. That is a project in itself. |
| 2 | Does a legitimate corpus change break a valid receipt? | **Not if the old snapshot is searched exactly** — but the snapshot may not exist. See the squash-merge measurement in § "Decision". |
| 3 | Is the receipt's blob SHA a stable identity? | **The full OID is** stable across amend/rebase/squash while the bytes are unchanged. The 7-hex abbreviation shown in §1.4 was not, and a blob OID proves neither the path nor durable reachability. |
| 4 | Does cutting `SubagentStart` leave a regression to own? | **No — cutting it was correct.** It would not have fired for either observed failure and would not prove delegated research was read. Adding it would be theatre. |
| 5 | Is a genuine search with a bad query fatal? | **Fatal to the claim that the executed control prevents the observed failure.** Not fatal to a receipt's value as a reviewed manual record — which is precisely the split that produced the pilot decision. |
| 6 | Is the spine proportionate, or should this be done by hand three times first? | **By hand, three times first.** Quoted in full in § "Decision". |

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo this specifies;
  `hook_guard.py`, `hk-common.pkl`, `docs/issue-tracker.md`, `.claude/rules/*`, and the closed-issue,
  label, timeline and transcript measurements in §0.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the
  `sources/agent-harness-docs/docs/claude-code/hooks.md` mirror behind the `permissionDecisionReason`
  and `SubagentStart` claims.

---

## 12. Pilot verdict — from data, 2026-08-01

The pilot ran as §"The pilot" specified: three `wayfinder:*` tickets after this one — **#437, #438,
#440** — each with a hand-written receipt. Four receipts exist in total; #449 is instance #1 and is
this spec's own.

| receipt | bytes | review findings | disposition | prior-art rows |
|---|---|---|---|---|
| `449.md` (#1) | 7,084 | 42, over 3 rounds | 42 accepted, **0 refuted** | 6 |
| `437.md` (#2) | 14,217 | 11 (2 crit) | 8 acc / 3 partial / **0 refuted** | 13 |
| `438.md` (#3) | 29,980 | 14 (2 crit) | 11 acc / 3 partial / **0 refuted** | 14 |
| `440.md` (#4) | 21,201 | 20 (2 crit) | 13 acc / 6 partial / **1 refuted** | 9 |
| **total** | | **87** | **1 refuted (1.1%)** | |

> **Post-pilot data point, 2026-08-01 — the §12.5 prediction held.** `448.md` (#5) is the first
> receipt written under the new *settle-it-by-running* rule: **26 findings, 3 refuted (11.5%)**, and
> **every one of the three was settled by a probe** rather than by argument — `copy` preserves 0600,
> and #434's `rc=1` was re-derived live rather than inherited. That is a 10× refutation rate off one
> template edit, which supports §12.5's reading that 1.1% measured **under-defended receipts**, not
> a calibrated reviewer. It also produced the practice's sharpest result so far: the review
> **reversed the verdict outright** (the load-bearing claim had probed only implicit config
> discovery, not whether the repo could own the *entrypoint*). Running total: **113 findings, 4
> refuted**. This does not reopen §12's build/no-build verdict — the automation the pilot rejected
> would still not have caught any of the three.

> **Second post-pilot data point, 2026-08-01 — and it cuts against the refutation-rate story.**
> `436.md` (#6): **14 findings (4 critical), 12 accepted / 2 partial / 0 refuted**, under the same
> settle-it-by-running rule that produced #448's 11.5%. Running total: **127 findings, 4 refuted
> (3.1%)**. One receipt does not establish a rate, and the honest reading is that **#448's 11.5% is
> not yet a trend** — n=2 either side of the template edit.
>
> What *did* repeat is the more valuable signal: **the review reversed the verdict outright for the
> second consecutive receipt.** The draft had dropped two of the ticket's seven prior decisions as
> over-investment, citing #440's "host tier is detection only" — which is about the host **mise**
> config and says nothing about chezmoi hooks. The reviewer caught the misapplication, and the
> probes it prompted found **three more live bypasses in the shipped guard** than the ticket had
> ever recorded (`-S` / `--source` / `--config` are chezmoi *global* flags, so they precede the
> subcommand and escape a command-anchored regex). So the pattern worth tracking is not the
> refutation rate but **how often the review changes the recommendation**: 5 of 6 receipts now.
>
> Two process defects surfaced that no field currently catches. **A published control term stops
> being a control** — `zzqqxx`, the known-absent arm of #437/#438/#440, now returns 5 hits *because
> those receipts wrote it down*; the template should not name a fixed string. And **the probe's own
> reader is an unarmed component**: a probe here read the wrong attribute off a result object and
> reported "0 findings" for a host carrying 2 live errors, and that clean number was written down
> before the control arm caught it.

> **Third post-pilot data point, 2026-08-02 — the highest finding count yet, and the pattern held for
> a third consecutive receipt.** `441.md` (#7): **22 findings (5 critical, 15 major, 2 minor), 17
> accepted / 3 refuted by probe / 2 partial**. Running total: **149 findings, 7 refuted (4.7%)**.
> Post-template-edit the rate is 6 refuted of 62 (9.7%) against the pilot's 1 of 87 (1.1%), which is
> now n=3 either side and starting to look like a real effect rather than #448's single outlier —
> though every refutation still comes from the same lever, **settling a finding by running something
> instead of arguing**.
>
> **The review changed the recommendation for the third consecutive receipt — 6 of 7 overall**, and
> this one did it twice. It killed the draft's headline claim (that `fnox proxy run` catches fnox's
> silent fail-open) by identifying that the fixture's rule table referenced a top-only *and* a
> profile-only secret, so **no** single profile could satisfy it and all six arms were forced to
> rc=1; re-run realistically, a missing profile starts at rc=0. And it pointed at
> `fnox.<profile>.toml`, a **second** profile mechanism the draft had never tested, which turned out
> to be the thing the ticket was actually asking about — flipping the literal answer from "fnox has
> no such overlay" to "fnox has it and we cannot reach it".
>
> **The process defect this receipt adds is not caught by any control-arm rule, including the ones
> the last two receipts added.** Both of its bad fixtures were *armed* — each had working positive
> and negative controls — and both were still worthless, because **a fixture built to demonstrate a
> thing cannot test it**. The proxy fixture admitted only one outcome; the profile-file fixture ran
> inside a tree whose parent held a `fnox.toml`, so the config search silently merged a foreign file.
> Control arms verify that the *probe* can distinguish; they say nothing about whether the *fixture*
> allows both answers. The question that catches this class — and it belongs in the template — is
> **"could this fixture have produced the other result?"**, asked before reading the output. Neither
> instance was self-caught: the first came from the reviewer, the second only surfaced because the
> first forced a re-run.

> **Fourth post-pilot data point, 2026-08-02 — the first receipt with NO adversarial review, and the
> control group nobody planned.** `445.md` (#8) ran `lens: none` and recorded it in the field rather
> than omitting the section. Running total is therefore unchanged at **149 findings, 7 refuted
> (4.7%)** across **7** reviewed receipts; #445 sits outside that denominator, and "the review
> changed the recommendation" stays **6 of 7**.
>
> Its value is as the missing arm. The last three receipts each had the *reviewer* catch a reversal;
> this one had none — and **two claims were published to the user before being cross-checked, then
> self-corrected**. A `.zshenv` render was reported as a credential-stripping *blocker* (it is not:
> the rendered file ends with a live `_mise_hook` that re-derives the environment), and a
> `status --missing` gate was read as broken in both directions (it was the author's own pipe eating
> the exit code — `feedback_pipe_kills_exit_code`, in a session whose template warns about it). Both
> were caught, both by the author, both **after** the wrong version had been sent. So the honest
> reading of §1's "highest-value field" claim is narrower than it looked: the review's contribution
> is not that errors get caught, it is **that they get caught before publication**. Self-correction
> works and is cheap; it just arrives late, and a receipt closed a few minutes earlier would have
> shipped both errors.
>
> A third defect has no field at all and is not a receipt problem: **the probe's own output leaked a
> secret.** A `${(P)k}` expansion meant as a presence flag printed four live credential values into
> the session transcript. Every existing layer in this repo guards a *file write* or a *spawn*; none
> guards *stdout of a command an agent runs*. Filed as
> [#474](https://github.com/ray-manaloto/dotfiles/issues/474), deferred behind #431. Worth recording
> here only because it is the second consecutive receipt whose worst moment came from the probe
> apparatus rather than from the reasoning.

### 1. Which fields were real, which became ritual?

**Real, and the highest-value field in all four: the adversarial review.** It was never once
clean, and it changed the *recommendation* — not the wording — in #437, #438 and #440. In #440 it
did so twice: it moved the gate from the `[hooks]` key to the unscoped command, and it demolished
the "permanently kill" framing by pointing out that a warn-only host check prevents nothing.

**Real, and specifically the DISMISSAL column: prior art.** Its value is not the hit list, it is
the written reason each hit did not apply. #438: **10 of 10** non-zero upstream hits were term
collisions. #440: **6 of 7** non-zero hits were collisions on "hook" (devcontainer lifecycle,
Claude Code). Without the column, "9 hits found" reads as coverage; with it, the reader can see
most of them were noise.

**Real, and the only field that has ever caught its own section lying: the control arm.** In #440
the prior-art search was not thin, it was **broken** — zsh does not word-split an unquoted
variable, so the corpus list collapsed to one nonexistent path, `2>/dev/null` ate the error, and
every query returned 0. The control arm (`chezmoi` → 0 files, when it should be 51) is the only
reason this was caught rather than published as "no prior art exists".

**Ritual: `Kind`.** Four receipts, one observed value (`decision`). A field with no variance
carries no information.

**Ritual: `Resolved`.** Derivable from the close event.

**Drifting toward ritual: `Sources`.** 9, 9, 9, 11 bullets. Three consecutive receipts landing on
exactly nine is the shape of a habit-count rather than a measurement.

**Not honoured once: the "one sentence" verdict.** 0 of 4 complied; every verdict grew into a
paragraph, because the honest answer to a grilling ticket has conditions attached. Either drop the
constraint or stop pretending it exists.

### 2. Did anyone read a receipt after the ticket closed?

**Yes — three times, and each read changed something.** #437's receipt was re-read during #438, and
its finding-8 correction is what let that session recognise it had repeated the same misattribution.
This session re-read #438's receipt and map line for the `lease.rs` facts, and #437's 13-row
prior-art table to calibrate this one.

**The honest limit: every reader has been the same author, in an adjacent session on the same map.**
There is no evidence a receipt has been read by anyone outside the work that produced it. The field
is proven useful for *continuity*, not yet for *audit*.

### 3. Did query drift actually happen?

**Yes in #438 — and something worse in #440.** #438's review objected that four queries do not
establish absence; nine more were run and the objection was correct. #440 did not drift at all: its
search was **broken**, returning 0 for every query for a reason that had nothing to do with the
query text.

That is the pilot's sharpest design conclusion. **The query is not the thing worth checking; the
control arm is.** A drifted query returns too few real hits. A broken probe returns zero and looks
identical to a clean corpus. Only the control arm distinguishes them.

**The same failure then happened while writing this section, which is the strongest evidence in the
pilot that it is not a one-off.** Committing §12 tripped hk's `typos` step on two hyphenated
prefixes in the text above. Checking the file by hand said *clean* — twice over, for two
independent reasons: `typos --diff` emits **nothing** when a correction is ambiguous (the offending
prefix had two candidate expansions, so there was no single diff to print), and the `rc=0` read back
was `head`'s, not `typos`'. Two display bounds stacked, in a probe written by someone who had spent
the session documenting display bounds. The rule that catches it is mechanical, not attentional:
**never read an exit code through a pipe, and never accept a clean result from a checker without
seeding a failure it must catch.**

*(Writing this paragraph tripped the same step a third time — quoting the offending token, even
inside backticks, is still an occurrence of it. Hence the periphrasis.)*

### 4. What did writing it by hand cost?

Roughly **half a session** per ticket, consistently, across #438 and #440.

But the honest finding is that **this cost cannot be separated from the cost of doing the ticket
well.** The review *is* the answer-finding step, not a write-up step — in #440 it produced two of
the three substantive corrections, and the third came from re-running a probe *because* a finding
demanded it. So the receipt cannot be cost-justified as a distinct artifact, and any future
proposal that frames it as "documentation overhead" has modelled it wrongly.

### 5. The 0-refuted question this pilot was asked to answer

The ticket-2 handoff asked whether 0 refutations meant the review was well-calibrated or the
receipts were under-defended. With #440 the tally is **87 findings, 1 refuted — 1.1%**.

**The receipts are under-defended.** A reviewer that survives 99% of its claims against a written
artifact is not evidence of a supernatural reviewer; it is evidence the artifact is written with
less rigour than the review applies to it.

The corrective is visible in the one refutation. #440's finding #9 (the `--platform` result rests
on unproved comma-parsing) was **settled by running an arm, not by arguing** — and the arm both
refuted the finding and produced a *better* measurement than the original, showing per-platform
behaviour the first probe had missed entirely. Every other finding across four receipts was
disposed of by reasoning.

**Process change, worth more than any field: when a review finding is empirically settleable, run
the probe before disposing of it.** One of 87 dispositions did this, and it is the only one that
reversed.

### 6. What gets automated

**Still nothing.** The pilot does not overturn the 2026-07-31 decision; it narrows what a future
build could justify.

- The **review** is the value, and it is already a single CLI call. What cannot be automated is the
  **disposition**, which is judgement — and the disposition is where the value lands.
- The **control arm** is the one field that is both machine-checkable and empirically load-bearing
  (it caught a broken probe in 1 of 4 receipts). But round 3 already established that a verifier can
  only prove *a* query ran, and #440's failure was a query that *did* run and returned nothing. A
  verifier would have passed it. **So even the strongest candidate would not have caught the
  pilot's one real miss.**

That is the pilot's answer to §425 "Build order": **do not start it.**

### 7. Three edits to `TEMPLATE.md`, and nothing else

1. **Drop `Kind`** — no variance across four instances.
2. **Promote the control arm to a required field of its own**, with both arms' counts stated, out of
   its current parenthetical under Prior art. It is the only field that has caught its own section
   lying.
3. **Drop the "one sentence" constraint on Verdict** — 0 of 4 complied, and the non-compliance was
   correct each time.

Plus one line in the template's header, which is a process rule rather than a field: *if a review
finding can be settled by running something, run it before writing the disposition.*
