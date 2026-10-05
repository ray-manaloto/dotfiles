# Coord-router evidence review and cited proposal (2026-10-04)

Status: proposal complete; external strict-five research remains incomplete
with the recorded blockers below. Documentation only. This proposal does
not authorize implementation, launch a router, or revise the specification.
Scope and prohibitions: `docs/specs/coord-router-evidence-review-2026-10-04.md:1-87`.

Evidence path convention: report basenames in citations resolve under
`docs/research/kb/reports/agents/`; `docs/specs/` and raw-artifact paths are
written explicitly. Statistics below name their reproduction command and its
real exit code; proposed measurements are marked as proposals.

## Recommendation and binding decisions

The evidence justifies measuring the ruled slim **router agent session** design;
it does not yet justify production rollout or a claim of net token savings.
Build on PR2 and prioritize specialist state custody plus explicit narrow
sender report contracts before enabling unrestricted free-text classification.
Evaluate the ruled router session in shadow mode before connecting it to
authority-bearing actions. This is a proposed sequencing of the ruled design:
the existing measurements do not establish production savings or justify
enabling the LLM tier now
(`coord-router-freetext-2026-10-04.md:85-105`; `coord-router-research-2026-10-04.md:266-300`;
`docs/specs/coord-router-2026-10-04.md:347-361`).

Preserve all binding rulings: build on PR2; router agent session; batcher plus
watcher's direct alert; containers out of scope v1; Q3 “neither”; one shipper
per repository; one heavy slot host-wide; coordinator ownership of plan/queue
writes; and spec-04 command-id custody. The router carries GO and ACK as PR2
events; spec 04 validates authority, lease generation and seen-command IDs;
`Unknown` means HOLD and a delivered GO is not an ACK
(`docs/specs/coord-router-2026-10-04.md:26-33,207-224,322-361`).

## What the measurements establish

The corpus contains 171 labelled rows, of which 163 are the declared primary
attachment sample from 27 coordinator sessions; the eight durable inbox records are excluded
from routing denominators because overlap is unresolved. The primary labels
come from full source bodies, while the saved classifier received sender plus
the first 300 characters. Selection takes each session's first six
deduplicated peer messages, with the positive control added as a seventh in
its session. This is a session-prefix convenience sample, with one reviewer,
no independent label audit and no held-out calibration
(`coord-router-freetext-2026-10-04.md:34-69`;
`coord-router-research-2026-10-04.md:268-273`).

**New provenance contradiction:** the free-text report says no selected primary
needed an ID fallback, yet eleven primary rows have `message_id` beginning
`provenance:`. Those rows are all labelled coordinator. Stop the assumption
that 163 means 163 native cross-session message IDs: the corpus mixes 152
native-ID rows with eleven fallback-ID deliveries. Keep the published 163
denominator for reproducing its results, but require separate transport-stratum
results and native ingress-ID reconciliation before implementation
(`coord-router-freetext-2026-10-04.md:63-65`;
`docs/research/kb/raw/coord-router/inbound-sample-2026-10-04.jsonl:36,81-84,95,119-120,125-126,131`;
fallback counter below, **rc 0**).

The documentation specialist counted fallback rows and labels without reading
or copying transcript bodies:

```bash
uv run --project python python - <<'PY'
from pathlib import Path
import json, collections
rows = [(i, json.loads(s)) for i, s in enumerate(Path('docs/research/kb/raw/coord-router/inbound-sample-2026-10-04.jsonl').read_text().splitlines(), 1)]
fallback = [(i, r) for i, r in rows if r['evaluation_denominator'] == 'primary-peer-163' and r['message_id'].startswith('provenance:')]
print({'fallback_rows': len(fallback), 'raw_lines': [i for i, r in fallback], 'labels': dict(collections.Counter(r['label'] for i, r in fallback))})
PY
```

Result: eleven of 163, at the cited raw lines, all eleven labelled coordinator.
This is a fixed-artifact metadata census; no sampling interval applies, and
misstating these as native IDs biases transport eligibility upward. Its effect
on specialist-label prevalence depends on whether handbacks belong in the
intended deployment frame (counter above, **rc 0**).

The 94/163 specialist labels (57.67%) are a taxonomy opportunity in that fixed
sample. They are not observed classifier coverage, message-volume savings,
token savings, or a reliable population ceiling
(`coord-router-freetext-2026-10-04.md:77-92`).

The published Sonnet run routed 18/163 at confidence ≥0.80, with 17 correct
and one wrong specialist destination. Thus 0.61% wrong among all messages and
5.56% wrong among routed messages describe the same error, with different
denominators. Ungated classification routed 59/163 with 19 wrong routes,
including ten shipper→handoff-scribe errors. Raising the threshold to 0.85
produced 15 routed and zero observed wrong routes, which does not establish
zero future error (`docs/research/kb/raw/coord-router/classifier-eval/score.txt:1-7`).

Historical deterministic replay covers a literal-prefix subset: two correct
routes out of 163. No complete grammar, independently declared specialist
sender contract or actual helper-generated envelope was available. The exact
shipper-role proxy routed 18 and got 14 wrong, showing why lane identity alone
cannot authorize a destination. These are replay/counterfactual results, not
production performance of the proposed complete chain
(`coord-router-freetext-2026-10-04.md:94-119`).

### Whole-population traffic census and sampling hypothesis

The statistics specialist's read-only counter below exited **0**. It scans 207
root JSONL files, identifies 32 coordinator files by their own-session
`agent-name`/`custom-title` metadata, and filters attachment timestamps rather
than restricting coordinator launch dates. That broader naming frame prevents
launch-date exclusion from silently dropping traffic (counter below, **rc 0**).

| Frozen counting window, America/Chicago | Eligible distinct attachment deliveries | Traffic-bearing coordinator sessions | Native message IDs / handbacks without native IDs | Lifetime first-six deliveries / all deliveries |
|---|---:|---:|---|---|
| Oct 3 00:00 through Oct 4 20:44:08.715008, matching corpus snapshot | 473 | 29 | 416 / 57 | 168 / 473 = 35.52% |
| Oct 3 00:00 through Oct 4 21:38:35, later fixed census | 549 | 31 | 490 / 59 | 180 / 549 = 32.79% |

The later census comprises 279 October 3 deliveries and 270 deliveries during
the observed portion of October 4; it is not a completed October 4 daily total.
Both windows have one attachment row per distinct counted delivery. Native
`origin.msg_id` keys and attachment `delivery_id` fallback keys are separate;
the fallback rows are `handback=true`. Counts refer to observed delivered
attachments, not semantic obligations, undelivered attempts or all other
transcript representations (counter below, **rc 0**).

Denominator/frame: all eligible queued peer attachment deliveries in the
metadata-identified root coordinator files, from local October 3 midnight to
the fixed endpoint. “First six” means chronological rank among each session's
lifetime deduplicated eligible deliveries through the endpoint, not rank
restarted at midnight. The original sample consists of 162 prefix deliveries
(six in each of 27 sampled sessions) plus the known control at lifetime rank
20, selected as that session's seventh sampled item. It includes 162 of the
168 prefix deliveries in the matching census frame. Therefore prefix
**undercoverage is measured**; different specialist prevalence in the omitted
later messages remains **untested**, with unknown bias direction. Do not
treat low population coverage as proof that the 57.67% label share is high or
low (census and documentation-specialist sample-rank counters below, **rc 0** each;
`coord-router-freetext-2026-10-04.md:50-57`).

No confidence interval applies to these exact snapshot counts: this is a
census of its stated file/attachment frame, not a random sample. Missing
transcripts, absent/other delivery representations and the partial-day endpoint
can undercount total real-world traffic; the direction of their effect on
the prefix share is unknown. The counter preserves metadata identity and
asserts the positive control; these checks validate the scanned frame, not
completeness outside it (counter below, **rc 0**).

Positive control: `f6f25455-60c8-4b52-9ee5-4317b5d0b0a5` appears once at
`/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/a629f1c6-a768-4d31-bfb0-554130b32258.jsonl:368`,
lifetime rank 20. The counter's real reversion fail arm uses the old
`type=user` schema and finds zero, while the required `type=attachment` schema
finds the known control. An earlier all-rows-have-`msg_id` counter exited **1**
and exposed the handback stratum; the corrected fallback-aware counter below
exited **0**. No transcript bodies were copied (counter below, **rc 0**;
statistics-specialist earlier counter receipt, **rc 1**).

```bash
uv run --project python python - <<'PY'
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
import json
root=Path.home()/'.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles'
files=sorted(root.glob('*.jsonl')); sessions={}; control='f6f25455-60c8-4b52-9ee5-4317b5d0b0a5'; old_control=0
for path in files:
 rows=[(n,json.loads(line)) for n,line in enumerate(path.open(),1)]
 names=[r.get('agentName',r.get('customTitle','')) for _,r in rows if r.get('type') in ('agent-name','custom-title') and r.get('sessionId')==path.stem]
 if not any(name.endswith('.coordinator') for name in names):continue
 events=[]
 for line,r in rows:
  a=r.get('attachment',{});o=a.get('origin',{})
  old_control+=r.get('type')=='user' and o.get('msg_id')==control
  if r.get('type')=='attachment' and a.get('type')=='queued_command' and o.get('kind')=='peer':
   key=('msg_id',o['msg_id']) if o.get('msg_id') else ('delivery_id',a['delivery_id'])
   events.append((datetime.fromisoformat(r['timestamp'].replace('Z','+00:00')),line,key,o.get('handback',False)))
 sessions[path.stem]=sorted(events)
start=datetime(2026,10,3,tzinfo=ZoneInfo('America/Chicago'))
print('scope',len(files),'root files;',len(sessions),'metadata-identified coordinator files')
for cutoff in ('2026-10-05T01:44:08.715008+00:00','2026-10-05T02:38:35+00:00'):
 end=datetime.fromisoformat(cutoff);raw=Counter();seen_deliveries=set();ids=set();daily=Counter();first=0;handbacks=0;hits=[]
 for sid,events in sessions.items():
  seen=set()
  for t,line,key,handback in events:
   if t>end:continue
   fresh=key not in seen;seen.add(key)
   if not start<=t<=end:continue
   raw[sid]+=1
   if not fresh:continue
   assert key[1] is not None
   seen_deliveries.add((sid,key));first+=len(seen)<=6;handbacks+=handback;daily[t.astimezone(start.tzinfo).date().isoformat()]+=1
   if key[0]=='msg_id':ids.add(key[1])
   if key==('msg_id',control):hits.append((sid,line,len(seen)))
 print(cutoff,{'raw':sum(raw.values()),'unique':len(seen_deliveries),'sessions':len(raw),'msg_ids':len(ids),'handbacks':handbacks,'daily':dict(daily),'first_six_lifetime':first,'first_six_share_pct':100*first/len(seen_deliveries),'control':hits})
 assert hits
print('old_user_schema_control',old_control);assert old_control==0
PY
```

This command reads source records to count metadata only; it emits no bodies
and writes no file. Results are fixed by the timestamp cutoffs, while the
number of root files can change on a later rerun (command above, **rc 0**).

The documentation specialist independently reconstructed the sample's lifetime
positions with this read-only counting command, **rc 0**. Output: positions
1–6 each contain 27 sampled rows, position 20 contains the control, and 162
of the 163 sampled rows are prefix deliveries. It emits no transcript bodies.

```bash
uv run --project python python - <<'PY'
from pathlib import Path
from datetime import datetime
from collections import Counter
import json
raw=Path('docs/research/kb/raw/coord-router/inbound-sample-2026-10-04.jsonl');primary=[json.loads(s) for s in raw.read_text().splitlines() if json.loads(s)['evaluation_denominator']=='primary-peer-163']; ranks={}
for file in {r['provenance'][0]['file'] for r in primary}:
 events=[]
 for line in Path(file).read_text().splitlines():
  row=json.loads(line);a=row.get('attachment',{});o=a.get('origin',{})
  if row.get('type')=='attachment' and a.get('type')=='queued_command' and o.get('kind')=='peer':
   key=('msg_id',o['msg_id']) if o.get('msg_id') else ('delivery_id',a['delivery_id'])
   events.append((datetime.fromisoformat(row['timestamp'].replace('Z','+00:00')),key))
 seen=set()
 for _,key in sorted(events):
  if key not in seen:
   seen.add(key);ranks[(Path(file).stem,key)]=len(seen)
positions=[]
for r in primary:
 key=('delivery_id',r['delivery_id']) if r['message_id'].startswith('provenance:') else ('msg_id',r['message_id'])
 positions.append(ranks[(r['session_id'],key)])
print({'sample':len(primary),'sessions':len({r['session_id'] for r in primary}),'lifetime_positions':dict(Counter(positions)),'prefix_rows':sum(p<=6 for p in positions)})
PY
```

### Statistical scope and uncertainty

For every row below, the frame is the same fixed 163-row mixed-transport
session-prefix sample; conditional-error rows restrict the denominator to
the messages that that policy actually routed. Labels are single-reviewer,
classifier input is truncated, confidence is uncalibrated, and thresholds were
examined on this sample. Prefix selection overweights early-session traffic;
the direction of its effect on specialist prevalence, accuracy and achievable
savings is **unknown**, because later-message labels were not measured.
Truncation and label ambiguity likewise have unknown direction. The 95% Wilson
intervals are **iid-binomial diagnostics only**, not valid whole-day intervals:
they do not repair nonrandom selection, within-session clustering, label errors
or same-sample threshold exploration. There is no defensible population interval
from these artifacts alone (`coord-router-freetext-2026-10-04.md:50-57,85-92`;
`coord-router-research-2026-10-04.md:268-295`; scoring commands below, **rc 0**).

| Fixed-sample statistic | Numerator / denominator | Percent | Diagnostic Wilson 95% interval, percent |
|---|---|---:|---|
| Specialist gold labels | 94 / 163 sampled messages | 57.67 | 49.99–64.99 |
| Sonnet ungated routed | 59 / 163 sampled messages | 36.20 | 29.22–43.81 |
| Sonnet ungated correct specialist routes | 40 / 163 sampled messages | 24.54 | 18.57–31.68 |
| Sonnet ungated wrong / all | 19 / 163 sampled messages | 11.66 | 7.59–17.49 |
| Sonnet ungated wrong / routed | 19 / 59 routed messages | 32.20 | 21.69–44.90 |
| Sonnet ≥0.80 routed | 18 / 163 sampled messages | 11.04 | 7.10–16.78 |
| Sonnet ≥0.80 correct specialist routes | 17 / 163 sampled messages | 10.43 | 6.61–16.07 |
| Sonnet ≥0.80 wrong / all | 1 / 163 sampled messages | 0.61 | 0.11–3.39 |
| Sonnet ≥0.80 wrong / routed | 1 / 18 routed messages | 5.56 | 0.99–25.76 |
| Sonnet ≥0.85 routed/correct | 15 / 163 sampled messages | 9.20 | 5.66–14.63 |
| Sonnet ≥0.85 wrong / all | 0 / 163 sampled messages | 0 | 0–2.30 |
| Sonnet ≥0.85 wrong / routed | 0 / 15 routed messages | 0 | 0–20.39 |
| Literal prefix routed/correct | 2 / 163 sampled messages | 1.23 | 0.34–4.36 |
| Literal prefix wrong / all | 0 / 163 sampled messages | 0 | 0–2.30 |
| Literal prefix wrong / routed | 0 / 2 routed messages | 0 | 0–65.76 |
| Exact shipper-role-name proxy routed | 18 / 163 sampled messages | 11.04 | 7.10–16.78 |
| Exact shipper-role-name proxy wrong / all | 14 / 163 sampled messages | 8.59 | 5.19–13.90 |
| Exact shipper-role-name proxy wrong / routed | 14 / 18 routed messages | 77.78 | 54.79–91.00 |

Classifier rows reproduce
`docs/research/kb/raw/coord-router/classifier-eval/score.txt:1-5` and are
independently replayed by the statistics specialist's command below, **rc 0**.
The documentation specialist reran the displayed command after strengthening
its unique-prediction-ID assertion, **rc 0**.
It confirms 163 distinct prediction IDs matching gold labels and reports each
numerator, denominator, percentage and diagnostic interval:

The 171 total rows, 163 declared primary rows, 27 sampled sessions and
152/11 native/fallback-ID membership counts are exact metadata counts of this
fixed artifact, not population estimates; no sampling interval applies.
Eligibility and transport bias remain as described above (command below,
**rc 0**).

```bash
uv run --project python python - <<'PY'
from pathlib import Path
from collections import Counter
from math import sqrt
import json
base=Path('docs/research/kb/raw/coord-router');rows=[json.loads(s) for s in (base/'inbound-sample-2026-10-04.jsonl').read_text().splitlines()];primary=[r for r in rows if r['evaluation_denominator']=='primary-peer-163'];p=[json.loads(s) for s in (base/'classifier-eval/predictions.jsonl').read_text().splitlines()];gold={r['message_id']:r['label'] for r in primary}
assert len(p)==len({r['id'] for r in p})==len(primary)==len(gold)==163 and all(r['label']==gold[r['id']] for r in p)
def rate(k,n):
 z=1.959963984540054;q=k/n;d=1+z*z/n;c=(q+z*z/(2*n))/d;h=z*sqrt(q*(1-q)/n+z*z/(4*n*n))/d
 return (k,n,round(100*q,3),round(100*(c-h),3),round(100*(c+h),3))
print('corpus',len(rows),len(primary),len({r['session_id'] for r in primary}),dict(Counter(r['label'] for r in primary)));print('native/synthetic_primary_ids',sum(not r['message_id'].startswith('provenance:') for r in primary),sum(r['message_id'].startswith('provenance:') for r in primary));print('taxonomy',rate(94,163))
for th in (0,.8,.85):
 routed=[r for r in p if r['pred'] not in ('coordinator','unsure') and r['confidence']>=th];wrong=sum(r['pred']!=r['label'] for r in routed)
 print('threshold',th,'offload',rate(len(routed),163),'correct',rate(len(routed)-wrong,163),'wrong_all',rate(wrong,163),'wrong_routed',rate(wrong,len(routed)))
for name in ('keyword_literal_subset','sender_default','combined_limited_replay','sender_role_proxy','combined_role_proxy'):
 routed=[r for r in primary if r[name]!='coordinator'];wrong=sum(r[name]!=r['label'] for r in routed)
 print(name,'offload',rate(len(routed),163),'wrong_all',rate(wrong,163),'wrong_routed',rate(wrong,len(routed)) if routed else None)
PY
```

The documentation specialist independently reproduced deterministic rows and
the inventory sum with this read-only command, **rc 0**:

```bash
uv run --project python python - <<'PY'
from pathlib import Path
import json, math
rows = [json.loads(s) for s in Path('docs/research/kb/raw/coord-router/inbound-sample-2026-10-04.jsonl').read_text().splitlines()]
primary = [r for r in rows if r['evaluation_denominator'] == 'primary-peer-163']
def wilson(k, n):
    z = 1.959963984540054
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [round(100*(c-h), 2), round(100*(c+h), 2)]
for tier in ('keyword_literal_subset', 'sender_role_proxy'):
    routed = [r for r in primary if r[tier] != 'coordinator']
    wrong = [r for r in routed if r[tier] != r['label']]
    print(tier, len(routed), len(wrong), len(primary), wilson(len(routed), len(primary)), wilson(len(wrong), len(primary)), wilson(len(wrong), len(routed)))
print({'state_lines': 191+109+29+88+90+21, 'all_lines': 1374, 'state_pct': 100*(191+109+29+88+90+21)/1374})
PY
```

## Two benefits and the decision they inform

**Coordinator tokens from routing.** The evidence counts destinations, not
tokens or coordinator turns avoided. The recorded $1.49 for four batched calls
over 163 messages is a historical batch cost, not a standing router's measured
net cost. Full-message input and persistent session context change both
classification and cost; the failed Haiku default-context attempt does not
measure a slim router profile (`coord-router-research-2026-10-04.md:275-295`).
Cost frame: one reported historical run, four batched calls over 163 excerpts;
no interval: n too small. No independent billing receipt or production cost
comparison was supplied; batching/context bias relative to a standing session
is unmeasured, so its direction is unknown
(`coord-router-research-2026-10-04.md:291-295`).
Current primary docs confirm that an idle cross-session message can start a
new turn and sends the session's cached conversation context; messaging counts
toward usage. Moving a message therefore does not establish a fixed saving per
message. These docs were fetched under native `fnox` with `curl`, **rc 0** each
([cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging),
[costs](https://code.claude.com/docs/en/costs); primary-fetch receipt below).

**Coordinator handoff from specialist state ownership.** The inventory assigns
about 528 of 1,374 lines across 12 October 4 a–l handoffs to state that might
move or become derivable. This is a subjective section classification rather
than measured handoff reduction, and message routing does not move ownership
by itself. S4 and PR2's durable events address that separate opportunity
(`coord-router-inventory-2026-10-04.md:129-169`;
`docs/specs/coord-router-2026-10-04.md:207-224`).
Denominator and frame: 528 attributed state-section lines / 1,374 total lines
in the historical twelve a–l handoff files, 38.43%; the inventory's later m
handoff is excluded from that fraction. No interval: n too small (twelve
nonrandom same-day handoffs), and the subjective section attribution is not
independently validated. Attributing every such line as removable can bias the
claimed saving upward because coordinator summaries/oversight may remain;
excluding m has unknown effect on the fraction. Errata are not added to the
saving. No token or handoff-before/after reduction is measured (inventory
`coord-router-inventory-2026-10-04.md:132-169`; sum command above, **rc 0**).

## Smallest additional decision measurement

The smallest next study is a fresh offline paired replay; it can answer the
marginal routing question before PR2 or a production router is implemented.
Freeze (A) a deterministic policy from genuinely available precedence rules,
trusted helper metadata and independently declared narrow report contracts,
with coordinator fallback; (B) the same policy plus classification of residual
300-character excerpts; and (C) the same policy plus classification of the
same residual full bodies under a slim, fixed context. Unbuilt helpers and
undeclared sender contracts contribute no routes. Reuse the documented public
classifier invocation and scoring format rather than build a new transport or
SDK integration. This separates fuller-input effects from cheaper-rule coverage;
it does not prove persistent router-session performance or net savings
(`coord-router-research-2026-10-04.md:268-273`;
`docs/specs/coord-router-2026-10-04.md:123-179,185-196,353-356`).

Use a new temporal hold-out across at least five coordinator sessions, taking
all eligible messages throughout those sessions and meeting the existing
minimum of 150 distinct messages. Freeze the evaluation cutoff, ingress-ID
deduplication, policy, model/context profile and confidence rule before labels
or predictions are scored; have a second reviewer adjudicate mixed intents
from full bodies. Report early/late and sender strata, the number of residual
messages actually sent to the agent, abstentions, returned messages, correct
offload/all, wrong/all and wrong/routed, and clustered uncertainty. Do not tune
the threshold on the hold-out or interpret a model's self-score as a calibrated
probability. This is a proposed future measurement, not a
new transcript-body read or launch in this task
(`docs/specs/coord-router-2026-10-04.md:185-196`;
`docs/specs/coord-router-2026-10-04.md:148-153`;
`coord-router-freetext-2026-10-04.md:50-57,90-92`).

If full-body classification adds too little correct coverage, or introduces
errors that violate the unchanged acceptance criterion, the cheap study is
enough to defer a production router build while preserving the ruling.
If it is promising, a second, broader experiment is required: after PR2 and the
architecture amendment, replay the same workload through a paired isolated
coordinator baseline and the ruled persistent router workflow. Measure usage,
retry/return cost and latency through the public route/submit/return interfaces
with isolated PR2 state, including router prompts, residual notifications,
returns and specialist responses. A shadow replay can measure classifier cost
and *potential* avoided inbound tokens; it cannot establish actual net savings.
Separately compare handoff capsule lines/bytes with and without specialist-owned
obligations under the same replay; do not convert saved prose lines into tokens
without measurement. Existing batching cost and inventory lines cannot substitute
for these endpoints (`coord-router-research-2026-10-04.md:291-295`;
`coord-router-inventory-2026-10-04.md:129-169`;
`docs/specs/coord-router-2026-10-04.md:158-179,191-196,217-227`).

Proposed decision rule: make the coordinator-token/latency/cost objective and
acceptable uncertainty explicit before the broader experiment; those economic
thresholds have not been ruled or measured. Enable the residual agent only if
it adds correct routes beyond policy A, preserves custody and authority controls,
shows benefit on that predeclared objective, and meets the unchanged
spec acceptance of >50% correct off-coordinator routing with zero observed
specialist misroutes on the hold-out. If uncertainty crosses the predeclared
benefit or risk threshold, extend the hold-out rather than declare success.
If A is sufficient or the agent fails, keep its stage in shadow/disabled while
advancing S4 custody work under the existing ruling. This recommendation
changes launch readiness, not Ray's architecture choice
(`docs/specs/coord-router-2026-10-04.md:108-115,185-196,207-227,353-361`).

The future public-interface test arms must fail when the motivating behavior
is reverted: remove helper provenance validation and a forged envelope routes;
replace narrow report contracts with lane-name defaults and mixed slot/custody
requests misroute; remove return bypass and the same ingress ID loops; erase
pending custody after send refusal and reconcile cannot recover the obligation;
accept superseded/duplicate GO and spec-04 receiver validation fails. Use isolated
state and real permission/transport failure paths, not assertion copies of the
implementation. These are proposed controls, not tests run here
(`coord-router-freetext-2026-10-04.md:111-117`;
`docs/specs/coord-router-2026-10-04.md:134-171,191-196,270-278,322-345`).

## Licensed dissent and exact replacement wording

Stop classifier implementation at the architecture commitment boundary: S1
still specifies an optional Python Anthropic SDK classifier, but the later
binding ruling specifies a standing router agent session. Amend the proposal
before implementation so Python deterministic policy invokes PR2's custody
interfaces, while PR2 retains the durable custody/identity ledger, with
residual free text delivered to the resolved router role. The agent
forwards only after preserving PR2 custody; ambiguous cases return to the
coordinator. Do not silently replace the ruled agent with an SDK call
(`docs/specs/coord-router-2026-10-04.md:148-179,353-356`).

Replace the research report's “floor, not a ceiling” with: “This evaluates
300-character excerpts against full-body labels. Full-body classification is
unmeasured; added context can resolve ambiguity or reveal mixed obligations,
so the direction of the change is unknown.” Replace “~0 misroutes” with
“one wrong specialist route among 163 messages, or one among 18 routed.”
Replace “The ceiling is 58%” with “94 of 163 sampled messages received a
specialist gold label; this is a sample-specific taxonomy opportunity.”
These corrections are proposed text only; the report and spec remain untouched
(`coord-router-research-2026-10-04.md:293-300`;
`coord-router-freetext-2026-10-04.md:85-92`).

Replace S1's classifier interface with the ruled router-role delivery and return
flow, retaining Python deterministic policy, PR2 event custody, concrete current
role/epoch resolution and existing deny precedence. Keep the current acceptance
criterion explicitly corpus-scoped: zero observed hold-out errors is not a
guarantee of zero future errors, and the router stage is disabled until the
actual chain is evaluated (`docs/specs/coord-router-2026-10-04.md:108-115,134-179,353-356`).

Replace “zero takeover broadcasts” with “stable PR2 role addressing may remove
address-change broadcasts after the reachability/takeover obligation is amended
and verified.” The inventory itself records the unresolved every-lane-delivery
amendment; stable names alone do not discharge the current requirement
(`coord-router-inventory-2026-10-04.md:48,188-195`).

## Verification and research receipt

Only the allowlisted report is edited. Repository gates, tests, pushes,
commits and Claude launches are not run, as required by the review brief
(`docs/specs/coord-router-evidence-review-2026-10-04.md:43-57,78-80`).
**RESEARCH INCOMPLETE:** `github-discussions`: `canary returned 0 items`;
`firecrawl-search`: `exited 1: Error: Request failed with status code 402 |`.
The required fanout and hook-required rerun both ran under the same native
`fnox` command, request ID and output directory and each exited **1**. Successful routes
do not turn this into a completed strict-five audit. The current manifest is
`/Users/rmanaloto/.codex/research-coverage/01a109ea-882b-7f30-bffc-2f433a420c30/01a109ea-9160-76c3-aaa5-b2baee5b5c40/manifest.json`,
generated `2026-10-05T02:55:18.623440+00:00`, with matching request ID and
`strict-five-v1` policy. The dispatcher verified all bound raw-file SHA256
hashes with a read-only Python command, **rc 0**; the documentation specialist
independently parsed the manifest with `uv run --project python python`, **rc 0**.
After the hook-required rerun, the dispatcher rechecked request/policy identity,
the complete source set and all eight bound raw-file paths/hashes, **rc 0**;
the documentation specialist independently read the current manifest, **rc 0**.
The prior receipt, generated `2026-10-05T02:39:32.489144+00:00`, returned seven
Last30Days items; the current rerun returns six. Other route counts, statuses
and exact blockers are unchanged. Original primary-source and failed-mirror
artifacts remain the basis for those separately recorded claims.
The complete fanout command and current manifest are the source for these
route results:

```bash
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout -- 'Claude Code cross-session messaging routing confidence evaluation' --repo anthropics/claude-code --strict-five --request-id 01a109ea-9160-76c3-aaa5-b2baee5b5c40 --last30days-plan /Users/rmanaloto/.codex/research-coverage/01a109ea-882b-7f30-bffc-2f433a420c30/01a109ea-9160-76c3-aaa5-b2baee5b5c40/last30days-plan.json --out /Users/rmanaloto/.codex/research-coverage/01a109ea-882b-7f30-bffc-2f433a420c30/01a109ea-9160-76c3-aaa5-b2baee5b5c40
```

| Attempted route | Status | Returned items / exact blocker |
|---|---|---|
| GitHub issues via `gh` | `ok` | 3 |
| GitHub discussions via `gh` | `empty_unverified` | 0; `canary returned 0 items` |
| GitHub releases via `gh` | `empty_verified` | 0; positive control 1 |
| Exa HTTPS API | `ok` | 10 |
| Context7 `ctx7` CLI | `ok` | 5 |
| Firecrawl developer HTTPS API | `ok` | 10 |
| Firecrawl search CLI | `error` | 0; `exited 1: Error: Request failed with status code 402 \|` |
| Last30Days plugin Python engine, explicit plan | `ok` | 6 (earlier run: 7) |

These are exact retrieved-item counts from this query/run, not estimates of
the available literature; no sampling interval applies and relevance/recency
bias is uncontrolled (counting command above, **rc 1**, manifest parse **rc 0**).
The dispatcher also ran
`fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- gh api repos/anthropics/claude-code --jq '{full_name,has_discussions,html_url}'`,
**rc 0**, observing `has_discussions=false`. This explains the unavailable
discussion route without overriding the recorded strict-five failure.

Actual execution inventory: the dispatcher used the `codex-sdlc-team` skill;
research ran the native `fnox`, `mise` research-fanout task, `gh`, Exa HTTPS API,
`ctx7`, Firecrawl developer HTTPS API plus Firecrawl CLI, and the Last30Days
plugin Python script. Research apps/connectors and research MCP calls were
not used. Exa and Firecrawl credentials stayed inside the `codex_research`
profile; no secret value is printed or stored in this report (fanout command
and manifest above, **rc 1**; dispatcher execution receipt).

The dispatcher verified current primary content using native `fnox exec --
curl --fail --silent --show-error URL --output PATH`, **rc 0** for each of:

- `https://code.claude.com/docs/en/cross-session-messaging.md` → receipt-directory
  `primary-cross-session-messaging.md`, lines 59 and 76 (idle delivery/usage).
- `https://code.claude.com/docs/en/costs.md` → `primary-costs.md`, lines 358–361
  (full cached conversation context and idle peer-message turns).
- `https://raw.githubusercontent.com/anthropics/claude-code/main/mods/types/claude-code.d.ts`
  → `primary-claude-code.d.ts` (public source; `SessionMessage` at line 8964).

Each invocation used the same full native `fnox` profile prefix as the fanout
command, and outputs reside in its receipt directory. Primary reads succeeded;
the separately required Firecrawl offline mirrors of these three URLs each
failed, **rc 1**, with the exact blocker: `Error: Insufficient credits to perform this request. For more credits, you can upgrade your plan at https://firecrawl.dev/pricing or try changing the request limit to a lower value.`
The attempted command for each URL was the native profile prefix followed by
`exec -- mise exec -- firecrawl scrape URL --format markdown --only-main-content --output PATH`.
This is a mirror-route gap; it does not show that the user lacks credentials
(dispatcher primary/mirror command receipts, **rc 0/1** respectively).

GitHub repository code search also ran under the native profile with public
`gh api -X GET search/code`: the must-hit query
`PreToolUse repo:anthropics/claude-code` returned 33 results with
`incomplete_results=false`, **rc 0**; the absent control
`"coord-router-absent-01a109ea-9160-76c3-aaa5-b2baee5b5c40" repo:anthropics/claude-code`
returned zero with `incomplete_results=false`, **rc 0**. An initial README-phrase
query returned zero, **rc 0**, so it was replaced as the positive control.
These are exact search-response counts, with no population interval or
claim of exhaustive prior-art coverage (dispatcher `gh` command receipts).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local
  coord-router artifacts and proposal; no GitHub write, commit or push.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — read-only
  issues/discussions/releases research and repository metadata probe, recorded
  in the current strict-five manifest above; no GitHub write.
