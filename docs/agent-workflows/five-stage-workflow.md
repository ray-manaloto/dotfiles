# Five-stage engineering workflow

This versioned protocol routes substantial implementation and recovery across
projects through **grill-with-docs → to-spec → to-tickets → implement-spec →
retro**. Read the selected installed instructions at each stage. The project
still decides its tracker, validation, publication, merge and delivery route.
Local-only projects need no PR; dotfiles retains its canonical gated tasks.

Design source: [approved prevention spec #1843][spec] and its
[durable-protocol ticket #1852][p8].

## Routing and standing authorization

The user authorized the complete selected five-stage chain as the standing
default for substantial work. Record that authorization and its source in the
task's plan; preserve it through handoffs and compaction. Do not request each
command again. Required reviews still settle design choices and the ticket graph.
Explicit task restrictions and human-only authority remain applicable.

Use the existing small/spec-saturated path for a trivial edit only when its
behavior, scope and acceptance are already settled, it is reversible, and it
does not change ambiguous behavior, shared global policy, credential policy or
frozen proof. A one-line hook/schema/policy change can still be substantial.
Record the routing rationale, applicable existing checks and result. If the
route is uncertain, resolve it through grilling before implementation.

## Selected instructions and honest execution

Inventory skill/tool availability first. For every selected stage retain the
installed package/version, exact instruction path or resource and content hash,
authorization, invocation mode, review decisions and output pointer. Preserve
the loaded version if a package updates during work; do not silently mix it into
an already approved stage.

Use native invocation when available and authorized. Native user-only invocation
restrictions are capability boundaries. When no Skill tool exists or the runtime
cannot invoke the selected verb, apply the exact installed instructions directly
under standing authorization and label **file-guided fallback**. Reading a file
is not native invocation. Report missing instructions or blocked routes honestly
and recover the required source before dependent work. Never modify plugin caches
to make a verb invocable. Preserve skill-specific requirements such as confirmed
test seams; this router does not replace the selected instructions.

Each stage retains its output and completion evidence:

1. `grill-with-docs`: document-backed decision tree, recommendations/tradeoffs,
   answered frontier and explicit shared understanding. Preserve review findings
   and their dispositions.
2. `to-spec`: approved behavior, user stories, implementation decisions,
   confirmed public seams, testing decisions and exclusions. Complete required
   spec review before ticketing.
3. `to-tickets`: reviewed context-sized slices, genuine blocking graph,
   integration branch per spec, ownership and publication record. Confirm
   granularity/dependencies before publishing.
4. `implement-spec`: ready tickets in isolated worktrees; scoped evidence,
   separate serial merger, whole-spec review, applicable final-ref gates and
   project delivery evidence.
5. `retro`: every learning has a linked concrete disposition, residual limits
   are explicit, and tracker closure matches actual project delivery.

The task record distinguishes designed, published, implemented, integrated,
reviewed, gated, hosted and delivered. A stage output or ticket label cannot
substitute for the next stage's evidence. Implementation uses the selected `tdd`
guidance at approved public seams; reversible documentation can reuse checks
without tests that merely mirror wording or generated copies.

## Frontier, ownership and integration

An implementation frontier contains tickets whose real prerequisites are
accepted and integrated into the relevant spec's integration tip. Track that
evidence separately from hosted OPEN/CLOSED status while a closing PR is draft.
Resource conflicts constrain scheduling; they do not create fake issue edges.

The coordinator assigns each worker a named branch/worktree from the integration
tip, exact path allowlist, shared-resource owner, permitted checks and handoff
location. Confirm the base before writing. Workers are not alone: preserve other
edits, reconcile the latest integration tip before completion, and report a tip
change that needs reconciliation. Obtain an ownership update before touching an
extra tracked path. Share context pointers rather than duplicate whole packets.

A **separate MERGER** verifies the changed-path set is a subset of that ticket's
allowlist, checks the base and actual evidence, reconciles conflicts without
discarding other work, and integrates one worker at a time. Unexpected paths or
unresolved ownership stop admission. Isolated worktrees are not an access-control
boundary. Workers do not perform coordinator-owned commits, publication, merges,
delivery or global activation unless explicitly assigned that authority.

One owner runs host-heavy integration gates; each repository has one shipper;
shared global policy has one writer. Hold competing writes to the owned checkout
through the entire commit/hook interval, including temporary hook transformations
and restoration. Record interval ownership and release after terminal evidence.
Existing coordinator guards/inboxes have limited scopes; they do not enforce
ticket allowlists or prove exclusion of every writer. Do not infer that hk stash
is shared across worktrees or claim mechanical race prevention from this rule.
Further native writer mechanisms need bounded qualification first.

## Proof, clocks and recovery

Development preflight precedes sealed START. Fix reversible development errors
autonomously within the ratified ticket. Save required verifier code and helpers,
compile syntax without importing product code, bind exact hashes in START, and
execute those admitted bytes. Required inline/stdin verifiers fail preflight.

Each ticket permits **at most THREE fresh sealed proof attempts**, each with a
new identity and artifact directory and **at most 60 active MINUTES**. Acquire
the required host slot before START. Declare a bounded queue-wait deadline and
record wait time separately; queued time is not active proof time. A timeout,
failure or interruption remains literal in its attempt's immutable record.
Never reset its clock, overwrite its directory or reclassify it as success.

New ratified recovery governs new attempts only. Preserve the old first-failure
STOP, interrupted settlement, source19/frozen product bytes and historical proof.
Hostile controls mutate copies. Fresh consumption of retained proof is fresh
consumer execution, not fresh execution of its historical producer phases.

Full caller-owned integration and delivery gates retain their named canonical
timeouts; a proof clock is not permission to truncate them. Allow at most three
attempts at a failed gate and retain each actual result and fix. In dotfiles use
the existing gate task and its typed records; the root owns full lint/test/verify
and applicable conditional gates before a native commit. Do not replace real
exits with tail/grep/notification success or weaken checks to fit the clock.

Continue ordinary reversible fixes within the approved contract and remaining
budget. Stop with honest partial status and escalate when that budget is
exhausted or material authority is unsupported: changed scope/contract/frozen
proof, destructive actions or unresolved human-only decisions. Preserve the
failed evidence and name the next decision; do not treat elapsed time as approval.

## Evidence and compact observation

Inventory existing interfaces before proposing a new projection framework. Use
SDLC `read_status`, typed dispatch/settlement records, lane `read_result`, and
gate `read` for routine observation. Return status, actual rc, bound paths/hashes,
missing required evidence and a concise limit. Expand bounded source/log excerpts
only for a concrete unresolved question. Raw artifacts remain accessible.

Label source inspection, scoped tests, synthetic integration controls and native
client qualification separately. A real detached supervisor with a synthetic
native runner tests its public boundary; it does not qualify every installed
client. Require actual trusted deny and safe allow for hook qualification and
fresh-session nonce/read provenance for global-pointer loading. A trust-bypass
flag or existing session's UI state is not that proof. Preserve actual child
exits, actor identities, rosters and missing capture; never reconstruct success.

Ordinary authorized research keeps strict provider coverage. A local/no-provider
task uses a caller-owned request/turn-bound declaration; mid-turn model text
cannot self-exempt. Report partial coverage and failed routes literally.
Portable fixtures retain only necessary nonsecret structural excerpts with
provenance/path mapping; original private journals and sealed packets stay out
of tracked fixtures. Missing optional paths are PENDING; missing required proof
is DENY. Expected enumeration comes from independent authoritative bound inputs
and normative completeness, so omission cannot shrink both sides of an oracle.

## Retrospective dispositions

`retro` links each learning to an implemented and verified fix, an explicit
combination with another candidate, or a deferred issue with owner, reason and
acceptance boundary. Do not call an issue's publication implementation. The
approved prevention program preserves these twelve concrete dispositions:

1. **Research scope — KEEP:** caller-bound local scope and ordinary research
   controls, [P2 #1846][p2].
2. **Broad environment stdout — KEEP NARROWED:** trusted per-client deny/allow,
   safe prefixes/presence/prose, [P3 #1847][p3].
3. **Saved verifier — KEEP NARROWED:** compile, hash-bind and execute exact
   saved bytes, [P4 #1848][p4].
4. **Reader contract — KEEP NARROWED:** typed independent oracle and portable
   hostile controls, [P5 #1849][p5].
5. **Scratch Git — KEEP NARROWED:** reuse full native isolation recipe; retain
   real checkout hooks, [P6 #1850][p6].
6. **Active-hook writers:** apply procedural exclusion now; qualify mechanisms
   and retain unsupported follow-up limits, [P9 #1853][p9].
7. **Evidence representations — MERGE INTO 4:** distinguish exact UTF-8/byte
   relations, decoded content and visible ACK provenance, [P5 #1849][p5].
8. **Structured observations — MERGE INTO 4:** typed paths/events and optional
   PENDING versus required DENY, [P5 #1849][p5].
9. **Tool economy:** apply compact readers in [P8 #1852][p8]; FILE generic
   machinery until a missing consumer/size contract is demonstrated.
10. **Receipt refusal — COMBINE WITH 11:** required publication errors yield
    FAILED, literal child rc retained, [P7 #1851][p7].
11. **Interrupted/missing capture — COMBINE WITH 10:** retain refusal/rosters/
    interruption; native diagnostic extensions deferred unless justified,
    [P7 #1851][p7].
12. **Durable protocol — KEEP:** authored/generated routing in [P8 #1852][p8],
    separately qualified global activation in [P10 #1854][p10].

These are approved work dispositions, not claims that all tickets are complete.
P9 native writer qualification and P10 fresh-session global deployment require
their own observed results. The originating research remained INCOMPLETE:
Context7 monthly quota; Firecrawl search used provisional Serper substitution
and primary mirrors used provisional webclaw. Do not relabel those as strict-five
success. The two delivered groups and historical PR1742 proof remain immutable.

## Maintenance and project delivery

The authored entrypoint is `.claude/skills/five-stage-workflow/SKILL.md`; its
`.agents/skills/` copy comes only from `mise run skills-mirror`, with `-- --check`
for parity. Keep the eager rule/pointer short and vendor-owned plugins intact.
Global pointers are a separate one-owner operation using reviewed versioned
source, reversible backup, compare-before-write and shared-client coordination.
Fresh-session loading evidence precedes activation claims; running sessions
retain their recorded startup state.

Dotfiles uses [its tracker](../issue-tracker.md) and canonical shipping tasks.
The prevention integration's first merge requires P1's qualified gated draft
route; whole-spec review precedes readiness and canonical final-head delivery.
Existing PR1742 needs no interim push solely because it is draft: retain its
branch/frozen proof, perform final-ref review and gates, then native readiness
and canonical ship/land. A draft, armed auto-merge or running CI is not delivery.
Other projects keep their own equivalent acceptance and closure rules.

Before full dotfiles shipping gates, run the actual GHCR prerequisite consumer
under the intended fnox profile. An explicit outer `--profile` does not set
`FNOX_PROFILE` for nested `fnox exec` calls. Propagate the profile to the child:

```zsh
env -u GH_TOKEN -u GITHUB_TOKEN FNOX_PROFILE=codex_publish \
  fnox --config ~/.config/fnox/config.toml \
  --profile codex_publish --no-defaults --no-daemon --non-interactive \
  exec -- uv run --project python dotfiles-setup ghcr-check
```

Require actual exit zero, then retain that profile environment for the canonical
ship invocation. Verify credential selection before proposing a key rotation:
a nested default route with no injected GitHub token can select `gh`'s saved
credential instead. Report only presence, scopes and consumer outcomes. Never
print token values, bypass the gate, or retry an exhausted attempt budget.

[spec]: https://github.com/ray-manaloto/dotfiles/issues/1843
[p2]: https://github.com/ray-manaloto/dotfiles/issues/1846
[p3]: https://github.com/ray-manaloto/dotfiles/issues/1847
[p4]: https://github.com/ray-manaloto/dotfiles/issues/1848
[p5]: https://github.com/ray-manaloto/dotfiles/issues/1849
[p6]: https://github.com/ray-manaloto/dotfiles/issues/1850
[p7]: https://github.com/ray-manaloto/dotfiles/issues/1851
[p8]: https://github.com/ray-manaloto/dotfiles/issues/1852
[p9]: https://github.com/ray-manaloto/dotfiles/issues/1853
[p10]: https://github.com/ray-manaloto/dotfiles/issues/1854
