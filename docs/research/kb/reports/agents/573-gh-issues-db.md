# #573 — GitHub Issues as the scheduler database

STATUS: complete
Date: 2026-08-05
Branch: `docs/573-pull-loop-scheduler-grill` (research only — nothing committed by this agent)
Repo under test: `ray-manaloto/dotfiles`

Scope: establish the mechanics of using GitHub Issues as THE scheduler DB for an
autonomous task DAG (symphony-style pull loop: reconcile → select → dispatch, tick ~60s).

## Method

Per `.claude/rules/research-doc-sources.md`: offline corpora first
(`~/dev/github/ray-manaloto/knowledge-base/sources/`, dotfiles mintlify cache),
then docs.github.com, then LIVE read-only probes via `gh api` against
`ray-manaloto/dotfiles`. Every probe carries a control arm
(`.claude/rules/probes-need-a-control-arm.md`).

### Corpus inventory (step 00)

- `knowledge-base/sources/` — 36 trees. **No GitHub-docs tree.** (Control arm:
  the same `ls` shows `agent-harness-docs`, `stokowski`, `symphony`,
  `OpenSymphony`, so the listing is not blind.) ⇒ GitHub API facts must come
  from live probes + docs.github.com, not from the KB.
- `stokowski` / `symphony` / `OpenSymphony` — present, and directly load-bearing
  for Q4 (the HTML-comment state-block pattern).

### Environment

- `gh` 2.97.0 (2026-07-31), mise-installed at
  `~/.local/share/mise/installs/github-cli/2.97.0/...`. **Not pinned in
  `mise.toml` or `.config/mise/conf.d/shared.toml`** (control arm: the same grep
  finds `ghalint = "1.5.6"` in the shared fragment, so the grep sees the file).

---

## Q1 — Native issue dependencies

### VERDICT: shipped, live on this repo, and the readiness predicate is a single inline field.

#### REST surface (probed live, 2026-08-05)

| Endpoint | Result |
|---|---|
| `GET /repos/{o}/{r}/issues/{n}/dependencies/blocked_by` | 200, array of full issue objects |
| `GET /repos/{o}/{r}/issues/{n}/dependencies/blocking` | 200, array of full issue objects |

Probe (`#573`, which is blocked by the completed probes #564/#565):

```
$ gh api repos/ray-manaloto/dotfiles/issues/573/dependencies/blocked_by --jq '.[] | "\(.number) \(.state)"'
564 closed
565 closed
$ gh api repos/ray-manaloto/dotfiles/issues/564/dependencies/blocking --jq '.[] | "\(.number) \(.state)"'
572 open
573 open
```

Both directions are readable, and the reverse edge is symmetric (#573 blocked_by #564 ⇔ #564 blocking #573).

#### ⭐ THE LOAD-BEARING FACT — `issue_dependencies_summary`

Every issue object carries an inline computed summary:

```json
"issue_dependencies_summary": {"blocked_by":0, "blocking":4, "total_blocked_by":2, "total_blocking":4}
```

That is `#573`, whose **two blockers are both CLOSED**. So:

- **`total_blocked_by`** = the edge count (all blockers, any state) = 2
- **`blocked_by`** = **the OPEN blocker count** = 0

⇒ **A CLOSED blocker counts as SATISFIED, and `blocked_by == 0` is the entire
readiness predicate.** No traversal, no per-blocker fetch.

**Control arm** (the field can produce the other answer — and it arrived from
real data, no fixture needed): on the same list call, `#579`–`#583` report
`"blocked_by":1` with `"total_blocked_by":1`. So the field is not stuck at 0;
it discriminates. Reported both arms: `#573 → 0` (blockers closed),
`#579 → 1` (blocker open).

#### ⭐ It is present on the LIST endpoint too

```
$ gh api "repos/ray-manaloto/dotfiles/issues?state=open&per_page=5" \
    --jq '.[] | "\(.number) deps=\(.issue_dependencies_summary)"'
583 deps={"blocked_by":1,"blocking":0,"total_blocked_by":1,"total_blocking":0}
582 deps={"blocked_by":1,"blocking":1,"total_blocked_by":1,"total_blocking":1}
...
```

⇒ **One paginated list call returns the whole ready-set.** The scheduler never
needs a per-candidate dependency fetch to decide readiness. This is the single
biggest fact for the rate budget (Q3).

Also inline on the same objects: `sub_issues_summary {total, completed,
percent_completed}` and `parent_issue_url` — so the parent/child hierarchy is
free on the same call as well.

#### GraphQL surface

`Issue` type introspection (`__type(name:"Issue"){fields{name}}`) filtered for
block/depend/parent:

```
blockedBy
blocking
issueDependenciesSummary
parent
subIssues
subIssuesSummary
```

**Control arm:** the same introspection with an exact-match grep returns
`title`, `number`, `state`, `assignees` — so the introspection is not blind and
the six names above are real fields, not a grep artifact.

#### `gh` CLI support — full, at the pinned 2.97.0

`gh` is **not pinned** in `mise.toml`/`shared.toml`; the installed mise build is
**2.97.0 (2026-07-31)**. It supports dependencies natively:

| Verb | Flags |
|---|---|
| `gh issue create` | `--blocked-by numbers`, `--blocking numbers` |
| `gh issue edit` | `--add-blocked-by`, `--add-blocking`, `--remove-blocked-by`, `--remove-blocking` |
| `gh issue list` / `view` | `--json blockedBy,blocking,parent,subIssues,subIssuesSummary` |

```
$ gh issue list --limit 3 --state open --json number,state,blockedBy,blocking
[{"blockedBy":{"nodes":[{"number":582,"state":"OPEN",...}],"totalCount":1},
  "blocking":{"nodes":[]},"number":583,"state":"OPEN"}, ...]
```

⚠️ **GAP: `issueDependenciesSummary` is NOT exposed to `gh --json`.**

```
$ gh issue list --limit 1 --json number,issueDependenciesSummary
Unknown JSON field: "issueDependenciesSummary"
```

**Control arm:** the same error prints the available-field list, which *does*
include `blockedBy`, `blocking`, `subIssuesSummary`, `parent` — so the field
name is genuinely unsupported by the CLI, not mistyped, and the probe can see
sibling fields.

⇒ Via `gh`, the scheduler must compute open-blocker count **client-side** from
`blockedBy.nodes[].state` (each node carries `state`, so it is a one-line
filter). Via raw REST/GraphQL, the precomputed `blocked_by` field is available.
Either is one round-trip; the `gh` path just moves the filter to the client.

---

## Q3 — Rate budget

### VERDICT: a 60s tick is essentially FREE. The binding constraint is not the core limit.

#### ⭐ Conditional GET works and a 304 costs ZERO

```
1) capture etag (a real 200)                        X-Ratelimit-Used: 25
2) five consecutive 304s, NO intervening 200:
   HTTP/2.0 304 Not Modified   X-Ratelimit-Used: 25
   ... (x5, all 25)
3) CONTROL ARM — a real 200 right after:            X-Ratelimit-Used: 26
```

Five 304s consumed **0** budget; the next 200 incremented by 1, so the counter
was live and the probe discriminates. `GET /repos/{o}/{r}/issues?state=open` on
this repo returns a weak ETag
(`W/"fe85a23c…"`), and `If-None-Match` yields 304.
**Second control arm:** a deliberately bogus `If-None-Match: W/"bogus0000"`
returned **200 OK**, proving the 304s were real cache hits and not an
unconditional response.

⇒ **An idle tick (nothing changed since last poll) costs nothing.** Only ticks
where the issue set actually changed spend budget.

#### Budget arithmetic (authenticated REST, core = 5000/hr)

At 60 ticks/hour, worst case (every tick sees change):

| Per tick | Requests | /hour |
|---|---|---|
| (a) list open issues + label filter, `per_page=100`, 1 page (repo has 132 open) | 2 | 120 |
| (b) dependency fetch for candidates | **0** — inline in (a) | 0 |
| (c) occasional mutations (claim/label/comment/close) | ~1–3 | ~60–180 |
| **Total** | | **~180–300/hr** |

That is **4–6% of the 5000/hr core budget**, and with ETags the realistic
figure is far lower. There is ~16–25× headroom.

⚠️ Note (b) is zero *only because* `issue_dependencies_summary` /
`blockedBy.nodes[].state` ride inline on the list response (Q1). A naive design
that fetched `/dependencies/blocked_by` per candidate would cost
`ticks × candidates` — at 60 ticks × 30 candidates that is 1800/hr, and it
would be the dominant cost for no benefit.

#### One round-trip for "open issues + their blockers' states": YES

Verified live:

```graphql
{ repository(owner:"ray-manaloto", name:"dotfiles") {
    issues(first:3, states:OPEN, orderBy:{field:UPDATED_AT, direction:DESC}) {
      totalCount
      nodes { number title state
        issueDependenciesSummary { blockedBy blocking totalBlockedBy totalBlocking }
        blockedBy(first:5) { totalCount nodes { number state } }
        assignees(first:3){nodes{login}}
        labels(first:5){nodes{name}} } } } }
```

→ returns, in one call:

```
573 sum={"blockedBy":0,...,"totalBlockedBy":2} blockedBy=[{565,CLOSED},{564,CLOSED}] labels=["wayfinder:grilling"]
```

⇒ number, state, readiness summary, every blocker with its state, assignee
(the claim field) and labels — **one request per tick** for the entire
reconcile+select input.

#### ⚠️ TRAP: the `/rate_limit` endpoint disagreed with the response headers

| Probe | core used | core remaining |
|---|---|---|
| `GET /rate_limit` body **and its own headers** | 3 | 4997 |
| `X-Ratelimit-*` on `GET /repos/.../issues` | 22–26 | 4978–4974 |

Both self-report `X-Ratelimit-Resource: core`. The `/rate_limit` figure stayed
frozen at 3 across a dozen real calls while the response headers tracked usage
correctly and monotonically.

⇒ **Self-throttle on `X-Ratelimit-Remaining` from the actual response, never on
`GET /rate_limit`.** A scheduler that polls `/rate_limit` to decide whether it
has budget would be reading a number that does not move.

#### The real constraint is the SEARCH bucket, not core

`GET /rate_limit` reports `search: {limit: 30}` — **30 requests/minute**. A 60s
tick using the Search API (`GET /search/issues`, or `gh issue list --search`)
sits inside a 30/min bucket rather than 5000/hr, i.e. ~2000× tighter per unit
time. It is still ample for one tick/minute, but it removes the headroom that
makes retries and multi-query ticks safe.

⇒ **Prefer `GET /repos/{o}/{r}/issues` (core) or GraphQL over the Search API**
for the tick. Use search only for genuinely cross-repo or full-text queries.

---

## Q1b — Closed / reopened blocker semantics (LIVE MUTATION PROBE)

### VERDICT: `blocked_by` is computed live from the blocker's CURRENT state. Closing satisfies; reopening re-blocks.

Fixture: scratch issue **#589** (`[probe-573] …`, created and cleaned up in this
session) attached as a blocker of the real open ticket **#571**, whose baseline
was `blocked_by=0, total_blocked_by=0`.

| Step | Action | `#571` summary | Reading |
|---|---|---|---|
| A | (baseline, no edge) | `blocked_by=0 total_blocked_by=0` | control: starts clean |
| B | add edge `#571 blocked_by #589`, **#589 OPEN** | `blocked_by=1 total_blocked_by=1` | an OPEN blocker blocks |
| C | **close #589** | `blocked_by=0 total_blocked_by=1` | ⭐ a CLOSED blocker is SATISFIED — and the edge survives (`total` stays 1) |
| D | **reopen #589** | `blocked_by=1 total_blocked_by=1` | ⭐ REOPENING RE-BLOCKS |

This probe is fully armed: the **same object produced both answers** (1 → 0 → 1)
under state changes alone, with no edge mutation. So `blocked_by` is a live
computation over the blockers' current states, not a latched flag.

**Design consequences:**

1. **Selection predicate = `blocked_by == 0`.** "No OPEN blockers" is exactly
   right, and GitHub computes it for you.
2. **`gh issue close` IS the completion signal** that releases dependents. No
   separate "mark satisfied" step exists or is needed.
3. ⭐ **Reopening is a free human veto / retraction.** A human who reopens a
   completed task automatically re-blocks everything downstream on the next
   tick. That is a genuinely valuable HITL affordance that falls out for free —
   but it also means the scheduler must tolerate a node going from
   ready→blocked **after** it was dispatched, and must not assume readiness is
   monotonic.
4. Edges are **permanent and independent of state** — `total_blocked_by` never
   moved. The DAG topology and the completion state are separate axes.

---

## Q1c — ⚠️ DAG integrity: cycle detection is SHALLOW

### VERDICT: GitHub rejects direct 2-node cycles and self-edges, but ACCEPTS transitive (3+ hop) cycles. The scheduler MUST do its own cycle detection.

**Rejected** (server-side validation, `rc=1`, no state change):

```
$ gh issue edit 589 --add-blocked-by 571      # while 571 is already blocked_by 589
Validation failed: this dependency would create a cycle where the target is
already blocked by the source (addBlockedBy)

$ gh issue edit 589 --add-blocked-by 589      # self
Validation failed: Target issue cannot be the same as the source issue (addBlockedBy)
```

**ACCEPTED** — the 3-hop case. Real pre-existing chain
`#583 blocked_by #582`, `#582 blocked_by #574`. Adding `#574 blocked_by #583`
closes the loop:

```
$ gh issue edit 574 --add-blocked-by 583
https://github.com/ray-manaloto/dotfiles/issues/574     # rc=0, SUCCESS

$ gh api .../issues/574/dependencies/blocked_by --jq '[.[]|"\(.number):\(.state)"]'
["573:open","583:open"]                                  # the cycle exists
```

⇒ **A 3-node cycle is a permanent deadlock**: all three nodes hold
`blocked_by > 0` forever, none can ever be selected, and nothing surfaces it.
The pull loop would simply skip them silently every tick, indefinitely.

**Mitigation:** the scheduler must run its own transitive cycle check — either
at edge-creation time, or as a reconcile-phase invariant that alarms when a
strongly-connected component of size > 1 appears in the blocked-by graph. The
whole graph is available cheaply (Q3), so an SCC pass per tick is affordable.

> Restored: the edge was removed with `--remove-blocked-by 583`; `#574` is back
> to `blocked_by=[573]`, summary `{blocked_by:1, blocking:2, total_blocked_by:1,
> total_blocking:2}`, and `#583 blocking` is back to `[]` — both verified against
> the pre-probe readings.

### ⚠️ Two more operational gotchas from the same probe

1. **The dependency summary is EVENTUALLY CONSISTENT.** Immediately after the
   successful write, `issue_dependencies_summary` still read
   `{blocked_by:1, total_blocked_by:1}` (stale) while the edge had in fact been
   created; a re-read ~3s later showed `{blocked_by:2, total_blocked_by:2}`.
   The `/dependencies/blocked_by` list endpoint was correct sooner than the
   inline summary. ⇒ **Do not read back your own write to confirm it.** A
   scheduler that writes then immediately re-reads will make decisions on stale
   data. Treat the tick's snapshot as authoritative and let the next tick
   reconcile.
2. **Adding an existing edge is NOT idempotent** — it errors:
   `Validation failed: Target issue has already been taken (addBlockedBy)`,
   `rc=1`. Reconcile logic must diff before writing, or tolerate this specific
   error as benign.

---

## Q2 — Claim mechanics

### VERDICT: there is NO conditional-write surface on issues. With a single scheduler process the race IS moot — say so and move on.

#### No compare-and-swap, confirmed with a control arm

```
$ gh api -X PATCH .../issues/589 -H 'If-Match: "<valid-or-bogus>"' -f 'body=…'
HTTP/2.0 400 Bad Request
{"message":"Bad Request","errors":["Conditional request headers are not allowed
 in unsafe requests unless supported by the endpoint"],"status":"400"}

# CONTROL ARM — same request, no If-Match:
HTTP/2.0 200 OK          # and the body really changed
```

Both a *valid* current ETag and a *bogus* one produced the identical 400, and
the control proves the command shape works. So the 400 is the endpoint refusing
preconditions outright — not a failed precondition. **`If-Match` on issues is
not "unsupported and ignored", it is a hard error.**

GraphQL is the same story:

| Input type | Precondition field? |
|---|---|
| `UpdateIssueInput` | none (`clientMutationId id title body assigneeIds assignees milestoneId labelIds labels state stateInput projectIds issueTypeId issueType agentAssignment`) |
| `AddAssigneesToAssignableInput` | none |
| `CloseIssueInput` | none |
| **`CreateCommitOnBranchInput`** (CONTROL) | **`expectedHeadOid`** ✅ |

**The control arm is decisive**: GitHub's GraphQL API *does* implement
compare-and-swap where it wants to (`expectedHeadOid` on commit creation), and
the same introspection sees it. Its absence on every issue mutation is a real
absence, not a blind probe.

#### Assignee is a SET, not a lock

- `POST /issues/{n}/assignees` is **additive and idempotent** — assigning the
  same user twice returns `rc=0` and no duplicate.
- Issues accept **up to 10 assignees**; `.assignee` is merely `assignees[0]`.
- ⇒ Two writers both "claiming" by assignee **both succeed**; you get two
  assignees, not a winner and a loser. Assignment can never be a mutex.

#### ⚠️ TRAP: a claim write can SILENTLY no-op

```
$ gh api -X POST .../issues/589/assignees -f "assignees[]=definitely-not-a-collaborator-zzq"
["sortakool"]            # rc=0, no error, assignee list UNCHANGED
```

GitHub silently drops assignees who lack push access. A claim that never landed
returns success. ⇒ **Verify the claim from the mutation's OWN response body**
(which contains the resulting assignee list) — not from `rc`, and not from a
re-read (see the eventual-consistency trap in Q1c).

#### Answer for this design: the race is moot, and that is load-bearing

With **one scheduler process doing all claiming**, there is no concurrent
writer, so the absence of CAS costs nothing. This is worth stating explicitly
in the design doc because it is the assumption that makes GitHub Issues viable
as a scheduler DB at all — **the single-writer constraint is not an
implementation detail, it is the concurrency model.** Two schedulers against
one repo would have no primitive to arbitrate between them.

Guardrails that follow:

1. **Enforce single-writer at the process level** — a local lockfile / launchd
   `KeepAlive` single instance. GitHub will not do it for you.
2. **Make dispatch idempotent anyway**, since the scheduler can crash between
   "claim" and "dispatch" and restart: derive intent from observed state each
   tick rather than from a remembered in-flight list.
3. If multi-writer ever becomes real, the standard patterns are: partition the
   work space so writers never contend (label/assignee-scoped shards), or move
   the lock off GitHub entirely (the repo already has a `flock` precedent). A
   "claim by comment then read-back-lowest-id" quorum over an eventually
   consistent store is **not** safe — see the Q1c lag measurement.

---

## Q4 — Where machine state should live

### VERDICT: LABELS for anything the selector reads; APPEND-ONLY COMMENTS for retry counts, terminal reasons and stall timestamps. Never the body.

#### The measurements

| Surface | Concurrent-edit safety | Visible to the tick? | Cost to read |
|---|---|---|---|
| **Labels** | ⭐ `POST` is **additive** (`["wayfinder:prototype"]` → `["wayfinder:map","wayfinder:prototype"]`), repeat is **idempotent** (rc=0, no dup), `DELETE /labels/{name}` is **surgical** (leaves the others) | ✅ inline in the list response | **free** |
| **Comments** | ⭐ **append-only — structurally cannot clobber**; every write is a new object with its own id | ✅ bumps `updated_at`, invalidates the list ETag | ⚠️ **+1 request per issue** — the list response carries only a comment *count* |
| **Body** | ❌ `PATCH` replaces the **whole** body; read-modify-write with no CAS (Q2) | ✅ inline | free |

Evidence for each:

```
# labels: additive + idempotent + surgical  (all rc=0)
POST labels[]=wayfinder:prototype   -> ["wayfinder:prototype"]
POST labels[]=wayfinder:map         -> ["wayfinder:map","wayfinder:prototype"]   # first preserved
POST labels[]=wayfinder:map (again) -> ["wayfinder:map","wayfinder:prototype"]   # no dup, rc=0
DELETE labels/wayfinder:map         -> ["wayfinder:prototype"]                    # surgical
DELETE labels/wayfinder:map (again) -> 404 "Label does not exist"                 # must tolerate

# server-side label filter narrows the tick for free
?state=open&labels=wayfinder:prototype -> 4        (control, unfiltered -> 100 of 132 open)

# comments are a COUNT in the list response, not bodies
.[0] -> {"number":589, "comments_is_a_COUNT":1, "has_comment_bodies":false}

# BODY CLOBBER, measured: one PATCH replaced a 250-char body with 13 chars, rc=0, no warning
{"body_now":"probe-control","len":13}
```

#### The stokowski / Sugar-Coffee pattern — verified, with one caveat

Source: `knowledge-base/sources/stokowski/stokowski/tracking.py:13-26`.

```python
STATE_PATTERN = re.compile(r"<!-- stokowski:state ({.*?}) -->")
GATE_PATTERN  = re.compile(r"<!-- stokowski:gate ({.*?}) -->")

def make_state_comment(state, run=1):
    payload = {"state": state, "run": run, "timestamp": datetime.now(timezone.utc).isoformat()}
    machine = f"<!-- stokowski:state {json.dumps(payload)} -->"
    human   = f"**[Stokowski]** Entering state: **{state}** (run {run})"
    return f"{machine}\n\n{human}"
```

Two design properties worth stealing outright:

1. **Each transition is a NEW comment, never an edit** — `parse_latest_tracking`
   (`tracking.py:72`) reads comments oldest-first and folds to the latest entry.
   The current state is a *fold over an append-only event log*, which is why it
   survives crashes and cannot be clobbered by a concurrent human.
2. **Machine payload + human sentence in the same comment.** The HTML comment is
   invisible in rendered markdown, so the thread stays readable to a human while
   staying parseable to the loop.

I reproduced it end-to-end on the scratch issue — write, then parse back:

```
posted: <!-- sched:state {"state":"running","attempt":1,"ts":"..."} --> + human line
parsed: {"state":"running","attempt":1,"ts":"2026-08-05T19:00:00Z"}
```

⚠️ **CAVEAT — stokowski runs on LINEAR, not GitHub.** `tracking.py:1` is
literally *"State machine tracking via structured Linear comments."* The pattern
transfers (comments are append-only on both), but no claim about GitHub
behaviour should be inherited from it. Everything above is measured on GitHub
directly.

#### Recommended split

- **Labels** — the scheduler's *selector* state, the small bounded vocabulary the
  tick filters on: `sched:ready`, `sched:running`, `sched:failed`,
  `sched:needs-human`. Free to read, server-side filterable, additive writes,
  and a human can retract one by clicking it off. Keep this set **small and
  mutually exclusive by convention**; nothing enforces exclusivity.
- **Comments** — the *unbounded / append-only* facts: retry counts, terminal
  reasons, stall timestamps, dispatch receipts. Full audit trail for free, and
  crash recovery by folding. Pay the +1 request only for issues the label filter
  already selected — never for the whole repo.
- **Body** — ❌ **never** for machine state. It is the one surface where a
  concurrent human edit and a scheduler write destroy each other, with no CAS to
  prevent it. This repo has already been bitten: memory
  `feedback_issue_body_edit_needs_anchor_assert` records an empty fetch
  replace-no-op'ing to `""` and pushing a **wiped body at rc=0**.

#### ⚠️ The scheduler's own writes defeat its ETag cache

Measured: posting one state comment changed the list ETag
(`W/"ad2d246d…"` → `W/"fb180533…"`) and bumped `updated_at`
(`19:34:13Z` → `19:34:36Z`).

⇒ Every tick that writes anything invalidates the next tick's free 304. Idle
ticks stay free; active ticks pay. This also means **`updated_at` cannot
distinguish a human's change from the scheduler's own** — corroborating the
existing memory `feedback_github_updated_at_advances_on_comment` ("a
post-then-compare gate can ONLY fail"). Track your own last-written marker if
you need to detect human edits.

---

## Q5 — Event-driven surfaces (scope extension: event loop, not fixed tick)

### VERDICT (stated up front): for ~minute-scale latency, **event forwarding is NOT worth its moving parts.** Use conditional polling + a periodic full reconcile. See "The verdict" below for why the deciding fact is Q5c, not the transport.

### Q5a — `gh webhook forward`: NOT available at the pinned version

```
$ gh webhook --help
unknown command "webhook" for "gh"
```

**Control arm:** `gh api --help` on the same binary prints its real help text, so
the binary and the probe work; `webhook` is genuinely absent from gh 2.97.0's
command list. It is not a built-in — it ships as the **`cli/gh-webhook`
extension**, and `gh extension list` here shows only `gh-copilot` and
`gh-stack`, so it is **not installed**.

**What I VERIFIED about the extension** (`gh api repos/cli/gh-webhook`):

| Fact | Value |
|---|---|
| Repo exists, not archived | ✅ `cli/gh-webhook` |
| Last pushed | **2025-10-21** — ~9.5 months stale as of 2026-08-05 |
| Stars | 42 |
| README | **124 bytes**, in full: *"An extension for the GitHub CLI to chatter with Webhooks. To install: `gh extension install cli/gh-webhook`"* |

**Control arm for that README claim:** an initial grep for
`forward|admin|token|scope|localhost|missed|replay|reconnect` returned nothing,
which is only meaningful once the fetch is proven to work — it decoded to 124
bytes containing `webhook` ×3. So the empty grep is a **true absence**: the
extension documents none of its own semantics.

⚠️ **LABELLED UNVERIFIED — I did NOT probe its runtime behaviour.** Doing so
requires installing the extension, minting an **admin-scoped** token and
**creating a real repo webhook** on `ray-manaloto/dotfiles`, all of which exceed
a read-only research pass. So the following are **reasoned expectations, not
measurements**, and must be re-derived before any design depends on them:
reconnect behaviour, whether events firing while the forwarder is down are
replayed, and the exact token scope required.

**But the verdict does not rest on them.** What it rests on is measured: an
undocumented, 9-months-untouched, 42-star extension whose reliability posture
**cannot be established from its own documentation** is a poor foundation for a
scheduler's correctness — and Q5c (below) shows the polling path is required
regardless, so the extension could only ever be a latency optimisation on top of
a mechanism that cannot be removed.

### Q5b — Conditional polling: measured, and cheap

**Do 304s count against the rate limit? NO** — measured in Q3 above: five
consecutive `If-None-Match` 304s left `X-Ratelimit-Used` frozen at 25, and the
next unconditional 200 incremented it to 26 (control arm: a bogus ETag returned
200, so the 304s were real).

Surface support, probed directly:

| Surface | ETag | `Last-Modified` | `X-Poll-Interval` |
|---|---|---|---|
| `GET /repos/{o}/{r}/issues` | ✅ `W/"fe85a23c…"` | ❌ **absent** (header count 0) | — (no floor) |
| `GET /repos/{o}/{r}/events` | ✅ `W/"fe8d85e6…"` | ✅ `Wed, 05 Aug 2026 19:35:41 GMT` (count 1) | ⚠️ **60** |
| `GET /notifications` | ✅ `W/"0f618867…"` | ✅ `Wed, 05 Aug 2026 19:39:48 GMT` | ⚠️ **60** |
| `GET /issues/{n}/timeline` | ✅ `W/"2fe08ac6…"` | — | — |

**Control arm for the "no `Last-Modified` on issues" claim:** the identical
`grep -ic '^last-modified'` returned **1** on the events endpoint and **0** on
the issues endpoint, so the probe can see the header when it is there. Issues
support **`If-None-Match` only**, not `If-Modified-Since`.

⇒ **Both the Events API and the Notifications API self-document a 60-second
polling floor** (`X-Poll-Interval: 60`). Polling either faster is abusive and can
get you throttled. The **issues list endpoint carries no `X-Poll-Interval`**, so
it has no declared floor — it is governed only by the core rate limit, which Q3
showed has 16–25× headroom.

**Notifications API is a poor fit regardless of its headers:** it only covers
threads you are *subscribed* to, and advancing its cursor (`last_read_at` /
marking read) is a **mutation**, so the read path has a write side-effect. For a
scheduler that must see every issue in the DAG — including ones nobody is
watching — subscription-scoped delivery is the wrong shape.

**Production tick shape confirmed.** The conditional GET works with the label
filter applied (query params are part of the cache key, so this needed its own
check):

```
GET /repos/.../issues?state=open&labels=wayfinder:prototype&per_page=100
  If-None-Match: <etag>  -> HTTP 304, X-Ratelimit-Used: 84
  If-None-Match: <etag>  -> HTTP 304, X-Ratelimit-Used: 84   # zero cost
  CONTROL, bogus etag    -> HTTP 200
```

⇒ For a ~60s target latency the issues-list conditional poll is the better
primitive: same latency as the Events API's own floor, no declared floor of its
own, zero cost when idle, and it returns the **full readiness state** (Q1)
rather than a delta you have to apply.

### Q5c — ⭐ THE DECIDING FACT: dependency changes emit NO event

Natural experiment with known ground truth: at **19:31:37** I added
`#571 blocked_by #589` and at **19:35:36** I removed it. Both are real,
timestamped, confirmed mutations.

**Per-issue timeline — PRESENT.** Both REST and GraphQL record them:

```
$ gh api repos/.../issues/571/timeline --jq '.[] | "\(.created_at) \(.event)"'
2026-08-05T19:31:37Z blocked_by_added
2026-08-05T19:35:36Z blocked_by_removed
```

GraphQL types them as `BlockedByAddedEvent` / `BlockedByRemovedEvent`. The
`IssueTimelineItems` union (51 members) contains `BlockedByAddedEvent`,
`BlockedByRemovedEvent`, `BlockingAddedEvent`, `BlockingRemovedEvent`
(control arm: the same introspection also returns the known members
`LabeledEvent`, `AssignedEvent`, `ClosedEvent`, `IssueComment`).

**Repo Events API — ABSENT.**

```
$ gh api "repos/.../events?per_page=100" \
    --jq '[.[] | select((.payload.issue.number//0) | .==571 or .==574) | …]'
NONE
```

**Control arm (this is what makes the negative trustworthy):** the *same call*,
over a window spanning `09:06:43Z → 19:35:40Z` (100 events), returns eleven
events for scratch issue `#589` at `19:31:25`–`19:35:41` — `opened`, `closed`,
`reopened`, `assigned`, `labeled` ×2, `unlabeled` ×2, and two
`IssueCommentEvent`s. Those timestamps **bracket** the two dependency edits.
So the Events API was demonstrably watching this repo, in this window, and
recording my activity — it simply does not emit dependency changes.

⇒ **Topology changes are discoverable ONLY by re-query. A periodic full
reconcile pass is MANDATORY, not optional.** No event transport — webhook
forwarding included — removes this requirement.

#### The nuance that matters for the design

The *state* change that releases a dependent **is** emitted; the *topology*
change is not. `#589 closed` and `#589 reopened` both appear as `IssuesEvent`s,
and those are exactly the transitions that flipped `#571.blocked_by` 1→0→1
(Q1b). So an event-driven loop can react promptly to **completions** — provided
it already holds the graph — but it can never learn that an **edge** was added
or removed except by asking.

Practical split:

- **Completion latency** → can be event-driven (an `IssuesEvent closed` arrives
  promptly), but only re-derives readiness correctly if the cached graph is current.
- **Topology latency** → bounded by the reconcile period, full stop.

Since the reconcile pass has to run anyway and already returns complete
readiness in one round-trip (Q3), it also covers completions — making the event
path redundant rather than complementary at minute scale.

### Q5d — `workflow_run` / `check_suite` as CI-completion signals

These are **webhook event types**, not issue events, and they are the correct
signal for "CI finished" — `workflow_run` with `action: completed` carries
`conclusion` (`success`/`failure`/`cancelled`), and `check_suite` likewise.
Neither appears in the repo Events API histogram from my probe window
(`CreateEvent, DeleteEvent, IssueCommentEvent, IssuesEvent, PullRequestEvent,
PullRequestReviewCommentEvent, PullRequestReviewEvent, PushEvent` — control arm:
`PushEvent` ×6 and `PullRequestEvent` ×11 are present, so the histogram sees CI-adjacent
activity), which is expected: the Events API deliberately excludes Actions events.

For this repo the pull-based equivalents already exist and are what the repo's
own rules mandate: `gh run list --json conclusion`, `gh pr checks <n> --json`,
and per `.claude/rules/gh-cli-watch.md` the `--watch` flags. Those are pull, they
carry no NAT requirement, and `verify-before-advancing.md` already requires
cross-verifying `gh run watch --exit-status` against
`gh run view --json conclusion` because the watch exit code has lied. Adding a
webhook transport for CI completion would introduce a second, less-trusted path
to a fact the repo already reads reliably by polling.

### The verdict

**Cheap conditional polling + a periodic full reconcile. Do not build event
forwarding.**

The reasoning is not "webhooks are hard" — it is that **Q5c makes the reconcile
pass non-optional**. Once you must poll to see topology at all, the event path
buys only sub-minute completion latency, and:

| | Conditional poll + reconcile | + `gh webhook forward` |
|---|---|---|
| Learns topology changes | ✅ | ❌ still needs the poll |
| Cost when idle | **0** (304) | 0, plus a live tunnel |
| Moving parts | one `gh api` call | extension + admin token + tunnel + repo webhook + reconnect/replay logic |
| Behind NAT | ✅ native | needs the forwarder up continuously |
| Missed-event recovery | inherent (next tick re-reads truth) | manual redelivery; **still needs the poll** |
| Latency | ~60s | ~seconds |

The design's stated target is **~minute-scale**, which the polling path already
meets — the Events API's own `X-Poll-Interval: 60` is the same number. Event
forwarding would trade a large increase in failure modes for latency the
requirement does not ask for.

**Recommended loop shape:**

1. **Tick every ~30–60s**: one conditional `GET /repos/{o}/{r}/issues?state=open&labels=…`
   with `If-None-Match`. A 304 (nothing changed) costs **zero** budget and ends
   the tick immediately.
2. **On 200**: the response already contains `issue_dependencies_summary`,
   labels, assignees and blocker states — run reconcile → select → dispatch off
   that single snapshot (Q1/Q3).
3. **Periodic deep reconcile** (every N ticks): re-read the full blocked-by
   graph and run the **SCC/cycle check** from Q1c, which nothing else will
   surface.
4. **Do not** trust a read-back of your own write (Q1c eventual consistency);
   let the next tick observe it.
5. Revisit event forwarding only if the latency target drops below ~10s.

---

## Cleanup / restoration

All live mutations were reverted and verified against pre-probe baselines:

| Object | Pre-probe | Post-probe | OK |
|---|---|---|---|
| `#571` summary | `{0,0,0,0}`, assignees `[]` | `{0,0,0,0}`, assignees `[]`, blocked_by list `[]` | ✅ |
| `#574` blocked_by | `[573]`, `{blocked_by:1,blocking:2,total_blocked_by:1,total_blocking:2}` | identical | ✅ |
| `#583` blocking | `[]` | `[]` | ✅ |
| `#589` (scratch) | n/a — created by this probe | **closed**, labels `[]`, no edges | ✅ |

---

## Summary of what makes this HARDER than expected

1. **Transitive cycles are accepted** (Q1c) — GitHub guards only the 2-node and
   self cases. A 3-node cycle is a silent permanent deadlock. Own the SCC check.
2. **No CAS anywhere on issues** (Q2) — single-writer is the concurrency model,
   not an optimization. Enforce it locally.
3. **Claim writes can silently no-op** (Q2) — verify from the response body.
4. **Eventual consistency on the dependency summary** (Q1c) — never read back
   your own write to confirm it.
5. **`gh --json` cannot see `issueDependenciesSummary`** (Q1) — compute open-blocker
   count client-side, or drop to raw REST/GraphQL.
6. **Your own writes evict your ETag cache** (Q4) and `updated_at` cannot
   separate your writes from a human's.
7. **The Search API is a 30/min bucket** (Q3) — stay on core/GraphQL for the tick.
8. ⭐ **Dependency changes emit NO event** (Q5c) — not in the Events API, not to
   any webhook. Only the per-issue timeline records them. A periodic full
   reconcile is therefore **mandatory**, and no event transport can remove it.
9. **`gh webhook` is not built in** (Q5a) — it is an undocumented, 9-months-stale
   extension, so event forwarding is both extra moving parts and unverifiable
   from its own docs.
10. **Events + Notifications APIs declare `X-Poll-Interval: 60`** (Q5b) — a
    60s floor on those surfaces; only the issues list is free of one.

## What makes it EASIER than expected

1. `blocked_by == 0` is a **precomputed, live, inline** readiness predicate —
   including on list responses. No traversal.
2. One GraphQL round-trip returns the entire reconcile+select input.
3. Idle ticks cost **zero** rate budget via ETag.
4. `gh issue close` is the completion signal; **reopen is a free human veto**
   that re-blocks the subtree.
5. Labels are additive/idempotent/surgical and server-side filterable.
6. **Idle ticks are free even in the real filtered shape** (Q5b) — the label-filtered
   conditional GET returns 304 at zero cost, so a NAT'd Mac daemon needs no
   inbound path at all.
7. **Completions (close/reopen) DO emit events** (Q5c) — so if sub-minute
   completion latency is ever needed, that half is available without solving the
   topology problem.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the live probe target: issues #556, #564, #565, #571, #573, #574, #582, #583, and scratch #589.
- [cli/cli](https://github.com/cli/cli) — `gh` 2.97.0 dependency flag surface, read via the installed binary's `--help` (release: <https://github.com/cli/cli/releases/tag/v2.97.0>); also confirmed `webhook` is absent from its command list.
- [cli/gh-webhook](https://github.com/cli/gh-webhook) — the webhook-forwarding extension (Q5a): repo metadata and its 124-byte README read via `gh api`; **not installed, runtime behaviour not probed**.
- [stokowski](https://github.com/ray-manaloto/knowledge-base) (vendored at `knowledge-base/sources/stokowski`) — the `<!-- stokowski:state {...} -->` structured-comment pattern (`stokowski/tracking.py`, `CLAUDE.md`); note it targets **Linear**, not GitHub.
