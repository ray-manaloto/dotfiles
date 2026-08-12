# Adversarial critique — session-review Codex coverage (2026-08-11)

Record replayed against:

- live active root `019feca1-89a4-7a12-b0f1-317e4939755d`
- live wrong-root control `019ff0d8-5f48-74f0-bbec-8000069f34f7`
- `/private/tmp/session-review-canary-2.md`
- current candidate code and tests in this worktree
- fresh concurrent-root fixture under `/private/tmp/session-review-active-control`

The candidate moved during review. The initial live replay failed active-root,
bounded-output, and prevention enforcement; the current bytes correct those
three historical failures. Verdicts below apply to the re-read current bytes.

| # | Verdict | Proposal | Fires on its motivating cases? | Shape |
|---|---|---|---|---|
| 1 | KEEP, NARROWED | Dual-provider discovery and parsing | Yes: the live Codex canaries are now in the public packet | — |
| 2 | KEEP, NARROWED | `N=1` selects the active/current Codex root | Yes for the historical long-running-root case; no for a concurrent-root identity case | 7 |
| 3 | KEEP, NARROWED | Preserve form, attachment, compaction, subagent, tool, terminal, and authority evidence | Yes structurally; unresolved provenance fails loud | — |
| 4 | KEEP | Bound the public report and retain a separate evidence artifact | Yes: live report is exactly 65,536 bytes with a truncation marker | — |
| 5 | KEEP, NARROWED | Block a finding without a prevention disposition | Yes: the live missing finding now returns non-zero; receipt truth is not verified | 5 |
| 6 | KILL | Configurable collection iterations are the self-improvement loop | No: they emit `needs_agent_action` and perform zero improvement actions | 4, 5 |

## 1. Dual-provider discovery and parsing — KEEP, NARROWED

Restated: normalize native Claude and Codex transcript evidence instead of
mining Claude history only. The motivating defect was the predecessor's
Claude-only command-audit route.

Current `discover_sources()` instantiates both providers
(`session_ledger.py:467-483`). The current live public replay, with `N=1`,
contains the active Codex canary:

```text
rc=1
public_contains_canary=true
```

The direct correct-root control also fires:

```text
status=incomplete bytes=91931 events=8368 requirements=187 promises=39 findings=2 omissions=745 cutoffs=1
canary_user=True
session_review_question=True
open_turn=True
```

Keep it as a conservative evidence-normalization layer. It is not a semantic
review and does not establish that requirements are satisfied.

## 2. `N=1` active/current root — KEEP, NARROWED

Restated: select the current Codex root and its children, even when the root was
created before newer unrelated tasks. The motivating defect was exactly that
long-running-root substitution.

Historical replay before the correction:

```text
discover_sources(limit=1) Codex root=019ff0d8-5f48-74f0-bbec-8000069f34f7
matching_roots=64 active_root_rank=15 newer_roots=14 default5_includes=False
public rc=0 bytes=1941
public current-canary=<absent>
```

The corrected implementation ranks roots by their latest native user/turn
activity (`session_ledger.py:407-455`), and the current public replay now fires:

```text
rc=1
public_contains_canary=true
```

The control arm proves the selection method reads activity: the new test at
`tests/test_session_ledger.py:384-419` selects an older-started root with newer
task activity over a newer idle root.

Exact restriction: this selects the **most recently active** root, not the
caller's identity. A fresh concurrent-root replay still substitutes another
root if it receives later activity:

```text
selected=concurrent-other
caller_current_selected=False
```

Therefore keep this for the historical defect but do not call it identity-safe.
`CODEX_THREAD_ID`/native parent-root resolution or an explicit root id is still
needed if two same-repository tasks are active concurrently. This is shape 7:
activity recency ranks the historical winner correctly but can rank the actual
caller second under concurrency.

## 3. Structural evidence surfaces — KEEP, NARROWED

Restated: preserve direct-user, form, attachment, compaction, lineage, tool,
terminal, and authority evidence without treating opaque assistant content as
user authority.

Live active root plus same-session children replay:

```text
sources=104 status=incomplete bytes=483958 events=21721 requirements=275 promises=51 findings=2 omissions=5150 open_cutoffs=49
kinds=agent_message:579,assistant_message:1198,attachment:11,authority_context:482,compaction:114,form_answer:100,form_question:81,opaque_payload:66,terminal_state:379,tool_call:8279,tool_result:8277,unverifiable_user_message:1980,user_message:175
canary_user=True
session_review_question=True
```

This discriminates correctly: structural kinds are retained, while thousands
of actual inherited/developer/provenance records it cannot authenticate make
coverage `INCOMPLETE`. Keep the fail-loud restriction. Do not relabel that
result as complete session understanding.

## 4. Bounded public report plus evidence artifact — KEEP

Restated: cap the human/public packet globally and spill the machine evidence to
a separate artifact with source-prefix references.

Current real invocation:

```text
rc=1
   65536 /private/tmp/session-review-adversarial-current.md
22778718 /private/tmp/session-review-adversarial-current.md.evidence.json
     309 /private/tmp/session-review-adversarial-current.md.iteration.json
22844563 total
public_contains_canary=true
[TRUNCATED: use cutoff references and JSON evidence artifact]
```

The hard cap is implemented by `_cap_utf8()` and applied at render return
(`session_ledger.py:1819-1831`, `:1920`). The hostile 2,000-row test at
`tests/test_session_ledger.py:686-702` checks the actual byte bound and marker.
The source-prefix table preserves the route back to native bytes. This proposal
now catches both prior 91,931-byte and 483,958-byte motivating outputs.

## 5. Finding-to-prevention disposition — KEEP, NARROWED

Restated: any detected high-severity finding blocks until all four prevention
receipt fields exist.

Historical replay before correction:

```text
Coverage: COMPLETE
high-severity findings: 1
risk-credential-launcher-cf2a8b9510ca6aa19b04 | credential-launcher | unreviewed | missing
Omissions: None
```

Current `disposition_omissions()` no longer depends on a synthetic `SATISFIED`
status (`session_ledger.py:1771-1781`). The live replay now returns `rc=1`, and
the public-loop test records `needs_agent_action` for an unreviewed missing
finding (`tests/test_session_review.py:329-366`). The unreviewed mutation is
also explicit at `tests/test_session_ledger.py:654-662`.

Restriction: `PreventionDisposition.complete` validates only non-empty strings
(`session_ledger.py:183-195`). The existing positive control uses declarations
such as `test`, `mutation fails`, `normal gate passes`, and `issue #1`; it does
not verify that a carrier exists, the hostile replay failed, the normal gate
ran, or the issue receipt resolves. Keep this as a reviewed receipt-presence
gate, not proof that prevention is real. The saving throw is still reviewer
judgement for receipt truth.

## 6. Iterative self-improvement — KILL

Restated: configurable iterations cause the Codex agent team to review, fix,
adversarially replay, QA, add prevention, and repeat until stable.

The current public replay with `--max-iterations 5` is:

```text
{"number":1,"action":"needs_agent_action","unresolved_count":2,"disposition_count":0}
```

`_requirements_review()` stops immediately whenever the action is not
`PREVENTION_RECORDED` (`session_review.py:560-575`). It does not invoke an agent,
create a carrier, run a mutation, execute the normal gate, update an issue, or
reload a changed disposition. `advance_iteration()` is a useful resumable state
classifier, but every improvement action remains external.

What fires first is `NEEDS_AGENT_ACTION`, so iterations 2 through 5 are inert in
the motivating unresolved-finding case. This is shapes 4 and 5. Keep the state
packet under proposal 5; kill the claim that it is itself a self-improvement
loop. A surrounding orchestrator/skill still has to dispatch and verify the
specialized agent team.

## What survives, and what the survivors do NOT cover

The current candidate now catches the original Claude-only, long-running-root,
oversized-report, and missing-disposition defects. It still does not:

- identify the caller's root under concurrent same-repository activity;
- verify the truth of prevention receipt strings; or
- perform the agent-team improvement work requested by the user.

Those residuals must remain explicit blockers or tracked follow-up work; a
green parser suite is not evidence that Codex has self-improved.

## Re-verified before reporting

Re-read the current discovery, disposition, renderer, iteration state machine,
public-loop tests, and skill after the concurrent edits landed. The focused
suite passed `90 passed in 0.95s`. A live `N=1`, five-iteration public replay
then produced the 65,536-byte report, 22,778,718-byte evidence artifact,
`needs_agent_action`, non-zero status, and the current Codex canary.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — candidate and replay target
