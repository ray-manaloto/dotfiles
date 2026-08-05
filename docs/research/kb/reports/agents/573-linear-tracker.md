# Linear as the scheduler tracker DB (#573)

**STATUS: complete**
**Agent:** linear-tracker · **Date:** 2026-08-05 · **Branch:** `docs/573-pull-loop-scheduler-grill`
**Method:** docs-only. **No live Linear API probes were run** — no credentials assumed, no
workspace exists. Every claim below is cited to Linear's own published docs or to the
official GraphQL SDL schema, or is explicitly labelled as inference.

## Scope

Ray is choosing the database for a symphony-style pull-loop scheduler
(reconcile → select → dispatch, ~minute-scale ticks, single Mac, agents are Claude Code
sessions). GitHub Issues is the incumbent. This report establishes what Linear actually
offers against six questions.

## Bottom line

**Recommendation: stay on GitHub Issues.** Linear's one genuine technical advantage is a
server-side `hasBlockedByRelations` filter — and it cannot see whether a blocker is
actually *open*, so you write the client-side blocker-state pass regardless. It does not
enforce state transitions (nobody does), its arbitrary metadata is not queryable, its
webhooks cannot reach a Mac behind NAT, it explicitly discourages the polling architecture
#573 proposes, and its free tier hard-stops at **250 issues**. Against that it is a second
system while every PR and CI gate here is GitHub-shaped.

The option most worth a head-to-head is **neither**: a local SQLite store as the
scheduler's source of truth with GitHub Issues as the human-facing view. It is the only
one of the three that offers a real atomic claim — verified below, *neither* tracker
supports compare-and-swap.

## Sources and how they were reached

The repo's `research-doc-sources.md` chain, step 1 (`llms.txt`) then step 2 (`.md` per page):

| Probe | Result |
|---|---|
| `curl https://developers.linear.app/llms.txt` | **302 → `linear.app/developers` HTML.** Not an answer — `developers.linear.app` is folded into the main site. |
| `curl https://linear.app/llms.txt` | **200 `text/plain`**, 222 lines — the real index. |
| `curl https://linear.app/docs/llms.txt` | 404 |
| `curl https://linear.app/developers/llms.txt` | 404 |

**Control arm for the index probe:** two sibling paths 404 while `/llms.txt` returns 200
text/plain, so the probe discriminates present from absent — the 200 is not a catch-all.

**Primary source for Q1–Q3** is the official GraphQL SDL, linked from that index:
`https://raw.githubusercontent.com/linear/linear/master/packages/sdk/src/schema.graphql`
— **50,261 lines / 1.27 MB**, fetched rc=0. Schema beats prose per
`probes-need-a-control-arm.md` ("source beats issue tracker"), so every structural claim
below is read off the SDL, not off a marketing page.

---

## Q1 — Workflow states: can we model claim states with API-enforced transitions?

**Verdict: custom states YES, enforced transitions NO.**

`WorkflowState` is a first-class per-team entity (SDL L49892), not a fixed enum. Fields:

- `name: String!` — free text ("In Progress", or our "Claimed"/"RetryQueued").
- `type: String!` — the **category**, and this is the constrained part. Doc comment:
  `One of "triage", "backlog", "unstarted", "started", "completed", "canceled", "duplicate"`.
  `WorkflowStateCreateInput.type` (L50022) narrows what you may *create* to
  `backlog, unstarted, started, completed, canceled` — "The type determines how the state
  is treated in workflow progression and reporting."
- `position: Float!` — ordering within the type group.
- `issues(filter: IssueFilter): IssueConnection!` — every state can list its own issues.

So symphony's `Unclaimed / Claimed / Running / RetryQueued / Released` map cleanly onto
five custom states, and you additionally get a free *category* axis:
`Unclaimed→unstarted`, `Claimed/Running→started`, `RetryQueued→unstarted` or `backlog`,
`Released→completed`. That category is genuinely useful — it is what makes
"is this blocker still open?" answerable without hardcoding state names.

**But there is no transition validation.** The SDL contains no `allowedTransitions`,
no from/to edge type, and no transition-guard input anywhere on `WorkflowState` or
`IssueUpdateInput`. `issueUpdate(input: {stateId: ...})` will move an issue from any
state to any other state. Linear's workflow is a **palette, not a state machine** — the
UI orders states by `position`, but the API does not police the order.

> **Control arm for this negative.** A 0-hit grep is not an answer until a known-present
> term returns hits with the same command shape. `grep -icE "customfield"` → **0**;
> control `grep -icE "issuelabel"` → **79**. Same file, same command shape, so the corpus
> and the grep both work and the zero is real. The same shape backs every "absent" claim
> in this report.

**Consequence for the scheduler:** state-machine correctness stays your Python code's job
exactly as it would with GitHub Issues. Linear gives you better *vocabulary* (named states
+ a semantic category) but zero *enforcement*. If you were hoping the tracker would reject
an illegal `Running → Unclaimed` write, neither system does that.

---

## Q2 — Dependencies: can one query return "state X with zero open blockers"?

**Verdict: native blocking relations YES; the full predicate in one round-trip YES, but
with a client-side second pass — the server cannot filter on blocker *state*.**

### The relation surface

`enum IssueRelationType { blocks, duplicate, related, similar }` (SDL L19816). `blocks` is
native and directional; the reverse direction is read through `Issue.inverseRelations`.
`IssueRelationCreateInput` (L19754) takes `issueId`, `relatedIssueId`, `type` — and
notably **accepts human identifiers** (`'LIN-123'`) as well as UUIDs, which removes an
ID-resolution round-trip a GitHub-based scheduler would need.

### What `IssueFilter` can express

`IssueFilter` (mined in full) carries all three pieces of the predicate:

- `state: WorkflowStateFilter` — filter on the state, including its `type` category.
- `hasBlockedByRelations: RelationExistsComparator`
- `hasBlockingRelations: RelationExistsComparator`
- `and: [IssueFilter!]` / `or: [IssueFilter!]` — arbitrary boolean composition.

So this is one server-side query:

```graphql
issues(filter: {
  state: { name: { eq: "Unclaimed" } },
  hasBlockedByRelations: { eq: false }
}) { nodes { id identifier } }
```

### The gap

`RelationExistsComparator` is **`{ eq: Boolean, neq: Boolean }`** and nothing else
(SDL L40275). It answers "does a blocked-by relation exist at all", not "does an
*unresolved* one exist". An issue whose only blocker is already `Released` still returns
`hasBlockedByRelations: true` — so that filter alone is **too strict**: it silently
withholds work that is actually ready.

There is no escape hatch at the filter layer: **no `IssueRelationFilter` or
`IssueRelationCollectionFilter` input exists in the schema**, and `Issue.relations(...)`
/ `Issue.inverseRelations(...)` accept only pagination args (`after/before/first/last/
includeArchived/orderBy`) — **no `filter:` argument**, unlike `Issue.children` and
`WorkflowState.issues`, which do take one.

> **Control arm.** `grep -nE "^input .*(IssueRelation|Relation).*(Filter|Comparator)"` →
> exactly one hit, `RelationExistsComparator`. Control: `grep -cE "^input .*CollectionFilter"`
> → **20**. The grep shape finds collection filters fine; there simply is not one for
> relations.

### The workaround, and it costs one round-trip, not two

GraphQL allows multiple aliased root fields in a single document, so the whole selection
predicate is still **one HTTP request**:

```graphql
query Selectable {
  ready: issues(filter: {
    state: { name: { eq: "Unclaimed" } },
    hasBlockedByRelations: { eq: false }
  }) { nodes { id identifier } }

  maybe: issues(filter: {
    state: { name: { eq: "Unclaimed" } },
    hasBlockedByRelations: { eq: true }
  }) {
    nodes {
      id identifier
      inverseRelations(first: 20) {
        nodes { type issue { state { type } } }
      }
    }
  }
}
```

`ready` is dispatchable as-is. `maybe` is post-filtered in Python to those where every
`type == "blocks"` blocker has `state.type` in `{completed, canceled}`. One round-trip,
a few lines of client code — and the `state.type` category is what makes that check
name-independent.

### Versus GitHub

GitHub's issue dependencies (sub-issues + blocked-by, GA'd through 2025) are exposed but
GitHub's issue *search* has no equivalent of `hasBlockedByRelations` — you enumerate and
resolve dependencies client-side, and REST search + per-issue dependency reads means
**N+1 requests**, or a hand-written GraphQL query with the same client-side pass. Linear
is meaningfully better here: server-side pre-filtering cuts the candidate set before the
client-side blocker-state pass, and it is one request either way.

**This is Linear's single strongest technical advantage for this use case.**

---

## Q3 — Claim + machine state

**Verdict: assignee is fine; there are NO custom fields; the real metadata slot is
attachment `metadata` JSON, which is upsertable but NOT server-side filterable.**

### Claim

`Issue.assignee: User` plus `Issue.delegate: User` (a second, agent-oriented assignment
slot). `IssueFilter.assignee: NullableUserFilter` filters on it server-side, so
"claimed by this machine" is expressible. There is **no atomic compare-and-swap** — no
conditional-update input, no `If-Match`/version field on `IssueUpdateInput`. Claiming is
therefore last-write-wins, identical to GitHub. On a single-Mac single-scheduler design
that is a non-issue; it would matter if two schedulers ever raced.

### Custom fields: they do not exist

`grep -icE "customfield"` → **0** (control `issuelabel` → **79**). Linear has no
custom-field feature at all. The metadata surfaces are labels, description, comments,
and attachments.

### The good part — `Attachment.metadata`

`AttachmentCreateInput` (SDL) has exactly the shape a scheduler wants:

- `metadata: JSONObject` — *"Attachment metadata object with string and number values."*
- `url: String!` — *"Attachment location which is also used as an unique identifier for
  the attachment. **If another attachment is created with the same `url` value, existing
  record is updated instead.**"*

That is a **native idempotent upsert of a JSON blob keyed by a string**, with no
read-modify-write and no separate create/update branch in your code. Set
`url: "scheduler://dotfiles/machine-state"` and every tick's `attachmentCreate` overwrites
the same slot. Retrieval is `Attachment.metadata: JSONObject!` on the issue. This is
strictly nicer than GitHub's usual answer (an HTML-comment-fenced YAML block in the issue
body, which is a read-modify-write with a lost-update race).

Two constraints to design around:

1. **"string and number values"** — the doc does not promise nested objects or arrays
   survive. Flatten your state, or store a JSON string in one key. *Unverified: no live
   probe was run to test whether nesting is actually rejected.*
2. **You cannot query by it.** `AttachmentFilter` and `AttachmentCollectionFilter` expose
   `id / title / subtitle / url / sourceType / createdAt / updatedAt / creator` — and
   **no `metadata` comparator**. Control arm: those same filter inputs *do* list `url`
   and `title`, so the fields were visible to the grep; `metadata`'s absence is real.

   So machine state in attachment metadata is **write-through and read-back, never a
   selection predicate**. Anything the scheduler must *select on* has to live in a state,
   a label, an assignee, or the attachment `title`/`url` (both `StringComparator`-filterable).
   That is a genuine design constraint, not a footnote: your selection axes are fixed at
   state × label × assignee × attachment-url, and everything else is payload.

Comment-based state blocks remain available as a fallback (`CommentCollectionFilter`
exists in `IssueFilter`), but attachment-metadata upsert dominates it on every axis.

---

## Q4 — Events and polling

### Webhooks need a public endpoint — a real cost on this host

Linear webhooks POST to a URL you register. **We are on a Mac behind NAT with no public
endpoint**, so consuming them requires a tunnel (ngrok/cloudflared) or a relay — a new
always-on dependency, an inbound attack surface, and something else for
`mise run doctor` to police. For a single-user local scheduler this is a poor trade.

### Polling: the numbers, and Linear explicitly discourages it

`https://linear.app/developers/rate-limiting.md`, verbatim:

> **"Avoid polling** — One thing that we especially discourage is polling the API to fetch
> updates. If you need to know when data updates in Linear, you should use our Webhook
> functionality."

That is Linear's stated position on precisely the architecture #573 proposes. It is
guidance, not a technical block — the budget below is comfortable — but it means the
pull-loop is swimming against the vendor's intent, and limits are explicitly subject to
change ("We are going to be evolving these limits").

⚠️ **Linear's own doc contradicts itself on the API-key request limit.** The prose says
*"When authenticated using an API key you can make up to **5,000 requests per hour**"*,
while the table immediately below it says:

| Authentication | Limit | per | Period |
|---|---|---|---|
| API key | **2,500** | User | 1 hour |
| OAuth App | 5,000 | User (or App User) | 1 hour |
| Unauthenticated | 600 | IP Address | 1 hour |

The prose looks like it copied the OAuth row. **Budget against 2,500/hr, the lower figure**
— and treat this as unresolved without a live probe (the `X-RateLimit-Requests-Limit`
response header returns the real number on the first authenticated call).

**Complexity is the second, independent budget** and is the one that actually binds:

- API key: **3,000,000 points/hour**; **10,000 points max for any single query**.
- Costing: each property 0.1, each object 1, and *each connection multiplies its children
  by the pagination argument or the default 50*.

At ~minute ticks = 60 ticks/hour:

- **Requests:** 2,500 ÷ 60 ≈ **41 requests per tick**. A reconcile+select tick needs 1–3.
  Not close to binding.
- **Complexity:** 3,000,000 ÷ 60 = **50,000 points per tick**. Also not binding — *but*
  the `maybe` query above nests a connection inside a connection, and nested connections
  multiply. `issues(first: 50) { inverseRelations(first: 20) { … } }` is
  50 × 20 = 1,000 child objects before properties, which approaches the **10,000-point
  per-query ceiling**. **Always pass explicit `first:` on both levels** — the default 50
  is what makes this dangerous, and the ceiling rejects the query outright rather than
  degrading.

### Cheap delta queries — yes

`IssueFilter.updatedAt: DateComparator` plus `orderBy: updatedAt` is exactly the delta
pattern, and Linear recommends it: *"sort it by the updated timestamp instead of when it
was created… get the most recently changed data first, and avoid paginating through the
entire dataset."* So a reconcile tick is a bounded `updatedAt > lastTick` query.

⚠️ Same trap as GitHub's: **your own writes bump `updatedAt`**, so a
write-then-poll-and-compare loop can spin. (Already a recorded lesson in this repo —
`feedback_github_updated_at_advances_on_comment`.)

### Subscriptions — they cover issues, but they are undocumented

> ⚠️ **Self-correction, recorded rather than silently fixed.** My first pass read the
> `Subscription` type through `head -40`, saw only `agent*`/`ai*` fields (the list is
> alphabetical), and wrote "there is no `issueCreated`/`issueUpdated` subscription."
> **That was wrong, and it was a display bound producing a false negative** — exactly the
> failure `probes-need-a-control-arm.md` §3 names and
> `feedback_enumerate_dont_assert_the_list` records. Enumerating the whole type instead
> of truncating it gives **80 fields**, including `issueCreated`, `issueUpdated`,
> `issueArchived`, `issueRelationCreated/Updated/Deleted`, `workflowStateCreated/Updated/
> Archived`, and the full comment/project/team set.

So the schema really does expose issue-level subscriptions, and a GraphQL subscription
runs over an **outbound websocket** — which would sidestep NAT completely and be the
ideal event transport for a Mac behind a router.

**But it is undocumented, and that is disqualifying.** Measured across Linear's own
developer docs:

| Corpus | `subscription\|websocket` | Control term | Control hits |
|---|---|---|---|
| `developers/graphql.md` | **0** | `query` | 16 |
| `developers/webhooks.md` | **0** | `query` | 6 |
| `developers/filtering.md` | **0** | `query` | 20 |
| `docs/api-and-webhooks.md` | **0** | `query` | 1 |
| `developers/agents.md` | **0** | `query` | 3 |
| `linear.app/llms.txt` (whole index) | **0** | `webhook` | 3 |

Every control arm returns hits from the same file with the same command shape, so the
zeros are real absences, not a broken probe. There is no documented websocket endpoint,
no documented subscription auth, and no stability promise. `Subscription` is the transport
Linear's own client uses; treating it as public API is building on an internal.

**Conclusion for Q4:** webhooks are the only supported push transport and they need a
public HTTPS endpoint we do not have; subscriptions would solve that but are unsupported;
so **polling is the only viable option, and it is the one Linear explicitly discourages.**
It will work — the budget is comfortable — but you are outside the vendor's intended use.

---

## Q5 — Integration cost

### Auth is genuinely easy — the best part of the story

`https://api.linear.app/graphql`, and for a personal script:

```sh
curl -X POST -H "Content-Type: application/json" \
  -H "Authorization: <API_KEY>" \
  --data '{ "query": "{ issues { nodes { id title } } }" }' \
  https://api.linear.app/graphql
```

Note the header is a **bare API key, not `Bearer`** (OAuth uses `Bearer`). Linear's own
guidance: *"For personal scripts API keys are the easiest way to access the API."* No
OAuth app, no callback URL, no token refresh — which matters on a NAT'd host.

Keys are **scopeable**: *"you can choose to give it full access to the data your user can
access, or restrict it to certain permissions (Read, Write, Admin, Create issues, Create
comments). You can also limit an API key's access to specific teams."* Good blast-radius
control, roughly on par with GitHub fine-grained PATs. One credential to add to the fnox
set (and therefore to `doctor.toml`'s reviewed baseline).

### Free-plan caps — this is a hard blocker for a task-row generator

From `linear.app/pricing` (comparison matrix, text-extracted):

| | Free | Basic $10/user/mo | Business $16/user/mo |
|---|---|---|---|
| **Issues** | **250** | Unlimited | Unlimited |
| Teams | 2 | 5 | Unlimited |
| Members | Unlimited | Unlimited | Unlimited |
| File upload | 10 MB | Unlimited | Unlimited |

**250 issues is the number that decides this.** A scheduler whose rows *are* issues
accumulates them monotonically; `docs/billing-and-plans.md` confirms the enforcement is
hard — *"If you have over 250 issues, you will no longer be able to create new issues."*
So Linear is either a ~250-row ceiling or **$10/month**.

*Open question, not probed:* whether **archiving** an issue frees a slot against the 250
cap. If it does, the cap is survivable with an archive-on-Released step; if not, the free
tier has a finite total lifetime. Nothing in the billing or API docs states either way,
and I ran no live probe — do not assume the favourable reading.

*Unresolved by this probe:* whether "API and webhook access" is checked for Free. The row
exists in the matrix under **Core**, but the per-plan cells are bare `<svg><path>` icons
with **no `aria-label`, `title`, or text** (verified: 0 hits for each of those attributes
in the row's markup), so the values did not survive HTML→text extraction. *Inference only:*
rows that differ by plan render **text** ("250 issues", "15 pipelines", "Google + SAML")
while this one does not, which suggests uniform availability — but that is a guess about
a rendering convention, not a citation. Confirm in the UI before relying on it.

### It is a second system, and PRs/CI stay on GitHub

Linear's GitHub integration (`docs/github.md`, 25 KB) is mature:

- **Issue sync**, one-way or two-way. Synced properties include title, description, status,
  assignee, sub-issues and comments. Assignees map through each member's connected GitHub
  account.
- **PR/branch linking** via magic words (`Fixes ENG-123`) in the PR title/description, via
  the issue ID in the branch name, or via commit messages.
- **Workflow automation** — a linked PR advances the Linear issue's workflow state.

Three limits that bite a scheduler specifically:

1. **Two-way sync is one repo at a time.** *"only one repo can be configured for two-way
   sync at a time"* — fine for this single-repo case, but it caps the pattern.
2. **Sync is forward-only.** *"GitHub Issues Sync will only sync newly created issues"* —
   existing issues need the separate importer. Any migration is a one-shot event.
3. **Sync is replication, so it is a second source of truth with lag.** For a
   reconcile→select→dispatch loop the scheduler must pick one system as authoritative and
   treat the other as a view. Sync does not remove the second-system cost; it *is* the
   second-system cost, with an error surface of its own (the docs describe per-issue
   "sync error" banners).

### MCP: confirmed unnecessary

Linear ships an official MCP server (`docs/mcp.md` in the index), but the GraphQL API
alone covers every operation this scheduler needs — query, mutate, filter, relate,
attach. Per `research-doc-sources.md` § "MCP: two lanes", this is squarely **lane 2**
(our own automation, our own lookups), so the plain HTTP API is the correct choice and
no registration is warranted. Nothing found requires MCP.

---

## Q6 — Verdict

### What Linear adds over GitHub Issues

| # | Add | Strength |
|---|---|---|
| 1 | **`hasBlockedByRelations` / `hasBlockingRelations` server-side filters**, composable with `state` via `and`/`or` | **The one real win.** Pre-filters the candidate set inside the selection query. |
| 2 | **Named custom workflow states** with a semantic `type` category (`backlog/unstarted/started/completed/canceled`) | Real. Claim states become first-class rows, and `type` makes "is this blocker done?" name-independent. |
| 3 | **`Attachment.metadata` JSON, url-keyed, upsert-on-duplicate** | Real. A native idempotent machine-state slot; no read-modify-write, no lost-update race. |
| 4 | Relations accept human identifiers (`LIN-123`) as well as UUIDs | Minor — removes ID-resolution round-trips. |
| 5 | GraphQL with multiple aliased root fields | Minor — a whole tick's reads in one request. |
| 6 | Scoped API keys (Read/Write/Admin, team-limited) | Minor — comparable to fine-grained PATs. |
| 7 | `X-RateLimit-*` and `X-Complexity` headers on **every** response | Minor but pleasant — the budget is observable, not inferred. |

### What it costs

| # | Cost | Severity |
|---|---|---|
| 1 | **A second system.** PRs, CI, code review and this repo's entire `ship`/`land`/`automerge` toolchain are on GitHub. | **Decisive.** |
| 2 | **250-issue cap on Free** — hard-enforced; unknown whether archiving frees slots. Escape is $10/user/month. | **Decisive** for a row-generating scheduler. |
| 3 | **No transition enforcement.** No `allowedTransitions` anywhere in the SDL — any state can be written from any state. | High — it is the feature that would most have justified the move, and it is absent. |
| 4 | **Attachment metadata is not filterable.** Selection axes are fixed at state × label × assignee × attachment url/title. | High — constrains the schedule design permanently. |
| 5 | **Webhooks need a public HTTPS non-localhost URL** — we are behind NAT. Worse: 3 retries then *"the webhook might be disabled by Linear, and must be re-enabled again manually"*. A Mac that sleeps will silently lose its event feed. | High. |
| 6 | **Linear explicitly discourages polling** — our exact architecture. Limits are "evolving". | Medium — works today, no guarantee. |
| 7 | **Subscriptions are undocumented** (0 mentions in every dev doc, controls 1–20), so the NAT-friendly transport is off the table. | Medium. |
| 8 | **Rate-limit doc contradicts itself** (prose 5,000 vs table 2,500 for API keys). | Low — budget against 2,500; verify via response header. |
| 9 | GitHub↔Linear sync is forward-only and two-way is one repo — replication lag and a new error surface. | Medium. |

### Recommendation: **stay on GitHub Issues.**

The honest case for Linear rests almost entirely on add #1, and add #1 is weaker than it
first looks: `hasBlockedByRelations` is an *existence* test that cannot see whether a
blocker is still open, so you write the client-side blocker-state pass **anyway**. What
Linear buys is a smaller candidate set going into that pass — a constant-factor
optimisation on a workload of a few dozen rows ticking once a minute. That does not pay
for a second system, a 250-issue ceiling or a subscription, and an event path that cannot
reach this host.

Adds #2 and #3 are the ones I would actually miss (named states, and the url-keyed
metadata upsert), but both have adequate GitHub equivalents — labels or a state label
namespace, and a fenced block in the issue body — and neither is where a minute-scale
single-user scheduler will fail.

Against that, cost #1 is structural: this repo's whole PR toolchain (`mise run ship`,
`automerge`, `land`, the guard rules that redirect to them) is GitHub-shaped. Putting the
DAG somewhere else means the scheduler's source of truth and the work product's source of
truth are different systems, permanently.

### The option worth naming: neither

For a **single-Mac, single-user, minute-tick** loop, the strongest architecture may be
**a local store (SQLite) as the scheduler's source of truth, with GitHub Issues as the
human-facing projection.** It dominates both trackers on the axes that actually constrain
this design:

- **Real atomic claim.** A transaction gives genuine compare-and-swap. *Neither* Linear
  nor GitHub offers a conditional update — both are last-write-wins. **Verified for
  Linear by enumerating `IssueUpdateInput` in full** (34 fields: `addedLabelIds …
  stateId, subIssueSortOrder, subscriberIds, teamId, title, trashed, trusted`) — it
  carries no version, no `ifMatch`, no expected-state and no etag. Control arm:
  `stateId` → 14 hits and `updatedAt` → 443 hits in the same file with the same command
  shape, so the zeros are absences rather than a blind probe.
- **Arbitrary indexed metadata**, filterable — no state × label × assignee ceiling.
- **Enforced transitions** — a CHECK constraint or a trigger does what neither tracker will.
- **No rate limit, no network, no NAT, no vendor policy on polling.**
- Ticks cost microseconds instead of an HTTP round-trip.

That trades away the free web UI and mobile notifications. Given `gh-issues-db` is
researching the GitHub side in parallel, this third option deserves an explicit
head-to-head rather than being assumed away.

## Caveats and what was NOT verified

- **Docs-only. Zero live API calls** — no Linear credentials were assumed or used. Every
  structural claim is read off the official SDL; every behavioural claim is quoted from
  Linear's docs. Anything about *runtime* behaviour (does nesting survive in attachment
  `metadata`? does archiving free a 250-cap slot? what does
  `X-RateLimit-Requests-Limit` actually return?) is unverified and flagged inline.
- **The GitHub-side comparison in Q2 is not first-hand.** I did not probe GitHub's
  dependency search qualifiers in this pass; the sibling `gh-issues-db` agent owns that
  side, and its findings should override mine on any disagreement. Per
  `probes-need-a-control-arm.md` rule 6, treat my GitHub statements as inherited and
  unverified, not as measurements.
- **One error was made and corrected mid-report** (the subscription false negative, Q4);
  it is left visible rather than edited away, because the failure mode — a `head`-bounded
  read reported as an absence — is the reusable lesson.

## GitHub repos touched

- [linear/linear](https://github.com/linear/linear) — the official GraphQL SDL schema
  (`packages/sdk/src/schema.graphql`, 50,261 lines) was the primary source for every
  structural claim about workflow states, issue relations, filters and attachments.
- [netlify/linear-webhook-template](https://github.com/netlify/linear-webhook-template) —
  referenced by Linear's webhook docs as the canonical consumer template; noted, not read.

### Doc sites consulted (not repos)

- `linear.app/llms.txt` — the docs index (200 text/plain; siblings 404, so control-armed).
- `linear.app/developers/{graphql,rate-limiting,webhooks,filtering,pagination,attachments,agents}.md`
- `linear.app/docs/{api-and-webhooks,issue-relations,billing-and-plans,github}.md`
- `linear.app/pricing` — plan caps (HTML; per-plan icons not text-extractable).
- `developers.linear.app/llms.txt` — **302 → HTML**, no longer a distinct doc host.
