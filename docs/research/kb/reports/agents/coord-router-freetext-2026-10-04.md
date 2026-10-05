# Coord-router free-text measurement and decision (2026-10-04)

Status: rev 3 draft and labelled corpus produced under fix brief rev 2;
the required measured-majority routing choice is **BLOCKED / NOT COMPLETE**.
The revised brief corrects the inbound-attachment source premise and cites
the completed S0 native-hook experiment. The earlier licensed-dissent stop
is preserved below as historical evidence. Corpus, candidate-tier metrics,
and the revised spec distinguish partial deterministic replay from unavailable
required tiers. No measured majority or working router is claimed.
No implementation, Claude sessions, repository validation gates, commits,
or pushes are authorized in this run.

## Current review findings (fix brief rev 2)

- The brief now explicitly permits peer `queued_command` attachments and
  tagged user-message duplicates, deduplicated by message ID. This resolves
  the earlier extractor-source contradiction; the positive control must
  still pass in the new extraction.
- S0 changed the proposed sender ingress: native `PreToolUse` on
  `SendMessage` with `updatedInput`, through the existing Python hook guard,
  replaces a `session.send` mod as the proposed enforcement mechanism. The
  config specialist checked the saved probe and exact current interfaces.
- No complete executable rev 2 grammar exists. A lexical baseline must be
  named as a reconstructed proxy. A sender-default baseline needs declared
  report-role evidence, and helper replay must not use the gold label as an
  oracle. An unrun LLM tier cannot supply a measured percentage or a measured
  combined-chain majority.
- Findings are persisted here within the explicit file allowlist. No root
  `findings.md`, Graphify gate, docs lint, or other repository gate runs in
  this review. The parent owns the separately mandated research receipt.

## Current corpus and measured routing tiers

Final corpus snapshot: **2026-10-05 01:44:08.715008 UTC** (October 4, 20:44 CDT):
`inbound-sample-2026-10-04.jsonl` SHA256
`5a49caed36239c48fad02ef6d09287d8725ba80c0b7c1c17fbbf74648c3e621b`.
171 hand-labelled rows comprise **163 primary peer messages from 27 coordinator
sessions** on local October 3/4 plus eight dated durable handoff-inbox records.
Those eight are a supplemental stratum excluded from routing denominators:
they have no native peer message ID, and semantic resend overlap is unresolved.
The 163 primary IDs are unique; the known control is present. The corpus
specialist's final analytical provenance/replay read exited 0: 193 enqueue /
remove queue copies were linked by exact same-file prompt and remove-command
UUID / attachment source UUID, with zero ambiguous queue links; 364 total
provenance records remain. No selected exact tagged-user duplicates matched;
157 unmatched tagged user records in the selected-session scan were excluded,
never counted as new events. This is a bounded attachment-primary corpus, not
a claim that every semantic representation/resend was recovered.

Sampling selects the first six deduplicated peer messages per coordinator
session, plus the known control as a seventh message in its session. The
single-reviewer labels use the full source body, while the shared artifact
retains sender, sanitized first 300 characters, ID/hash and source provenance.
This is an equal-session prefix sample with startup/prefix bias, not a random
or traffic-weighted population estimate. No held-out/tuning split or independent
second-label review was performed; the tiny question-batcher stratum cannot
support a class-specific reliability claim.

Extractor source boundary: root transcripts whose `custom-title` or
`agent-name` identifies `.coordinator` and `20261003` / `20261004`,
`type=attachment`, `attachment.type=queued_command`, `origin.kind=peer`;
record timestamp converted to CDT (UTC−05) on October 3/4. Body is
`origin.body` when present, otherwise `attachment.prompt`. Global peer
`origin.msg_id` deduplicates delivered attachments; the sender/body-SHA fallback
was needed for no selected primary message. Selection is chronological within
UUID-sorted coordinator sessions. Enqueue/remove and matching user-tag records
augment provenance rather than create rows. Token-looking lines are stripped
before saving the first-300-character excerpt. Full source messages supply
manual labels independently of candidate tier fields.

Gold rubric: approved heavy-run admission requests → slot-arbiter; delivery
readiness / PR shipping / worktree custody → shipper; pure completion / parked
facts → handoff-scribe; explicit unresolved user choice → question-batcher;
mixed responsibilities, authority changes, dispatch/plan/queue writer requests,
and retired-coordinator relays → coordinator. No label authorizes the action.

| Primary gold label | Count |
|---|---:|
| coordinator | 69 |
| slot-arbiter | 41 |
| shipper | 38 |
| handoff-scribe | 14 |
| question-batcher | 1 |

94/163 (**57.67%**) have a specialist gold label: taxonomy opportunity only,
not measured routing coverage, token savings or coordinator load reduction.
Real shipper-lane messages also request SLOT/authority changes; sender identity
alone is insufficient. Multi-intent records are conservatively coordinator.

Offload = specialist-routed /163. Misroute-all = wrong specialist destination
/163; conditional misroute = wrong /specialist-routed. Coordinator abstentions
do not count as specialist errors, so coverage must accompany error rates.

| Required candidate / observed replay | Offload | Misroute-all | Conditional misroute | Status |
|---|---:|---:|---:|---|
| Exact rev 2 keyword grammar | Unmeasured | Unmeasured | Unmeasured | BLOCKED: no complete grammar table exists. |
| Explicit literal `SLOT ` prefix subset | 2/163 = **1.227%** | 0/163 = 0% | 0/2 = 0% | Measured subset replay; rows 7 and 78. No inference from free-text labels. |
| Available declared sender-report destinations + unknown fallback | 0/163 = 0% | 0/163 = 0% | N/A: no specialist routes | Measured conservative replay; 18 primary messages have a declared coordinator destination, 145 have no report-destination contract. |
| Future specialist sender defaults | Unmeasured | Unmeasured | Unmeasured | BLOCKED: no independently declared narrow specialist report contract found. |
| Proposed exact shipper-role-name proxy | 18/163 = 11.043% | 14/163 = 8.589% | 14/18 = 77.778% | Measured counterfactual proxy; not historical policy or a declared report contract. |
| Actual helper-generated envelope | Unmeasured | Unmeasured | Unmeasured | Historical envelope eligibility 0/163; helper not built/run. No gold-label retrofit. |
| Python LLM + confidence/abstain | Unmeasured | Unmeasured | Unmeasured | No inference/auth route exercised; threshold, latency and cost unavailable. |
| Limited replay: literal subset → available declared defaults → coordinator | 2/163 = **1.227%** | 0/163 = 0% | 0/2 = 0% | Measured deterministic replay only, with future helper/LLM tiers inactive. |
| Literal subset → proposed shipper-role-name proxy → coordinator | 20/163 = 12.270% | 14/163 = 8.589% | 14/20 = 70% | Measured counterfactual proxy chain, not the full proposed chain. |
| Full proposed chain | Unmeasured | Unmeasured | Unmeasured | BLOCKED: unavailable tiers cannot be added or assumed to succeed. |

The declared coordinator-report evidence is
`.agent/plans/brief-kbship-20261003.md:3`; its destinations are not specialist
defaults. Counts of historical envelope absence / missing contracts describe
input eligibility, not the performance of a future helper or sender registry.
The role-name proxy targets only the exact sender
`kb-20261003T102535.932032000-05.ship`; its messages often ask for host slots,
authority/custody rulings or dispatch decisions. Misrouted artifact rows are
15, 27, 33, 39, 45, 91, 107, 109, 117, 121, 128, 142, 149 and 155.
Row 128 requests the KB #865 host slot; row 27 asks for a stash custody ruling.
These are realistic fail arms for accepting all shipper-sender text as shipper
work. They motivate the proposed narrow report-contract/ambiguity guard.
Exact-grammar evaluation and actual helper/LLM evaluation are stopped under
licensed dissent rather than replacing unavailable interfaces with inventions.

The documentation specialist independently counted the final artifact and
replayed its stored tier decisions with the following analytical command,
**exit 0**. It reproduced 171/163/27, label counts, 163 unique IDs, positive
control `true`, literal subset 2 correct specialist routes, sender-default
zero specialist routes, limited-chain 2 correct routes, role-name proxy
18 routes /14 errors and its combined proxy 20 routes /14 errors. This reads the
labelled artifact; it is not an implemented router or a repository gate.

```bash
uv run --project python python - <<'PY'
from pathlib import Path
import json, collections
rows = [json.loads(line) for line in Path('docs/research/kb/raw/coord-router/inbound-sample-2026-10-04.jsonl').read_text().splitlines()]
primary = [r for r in rows if r['evaluation_denominator'] == 'primary-peer-163']
print({'rows': len(rows), 'primary': len(primary), 'sessions': len({r['session_id'] for r in primary}), 'labels': dict(collections.Counter(r['label'] for r in primary)), 'unique_ids': len({r['message_id'] for r in primary}), 'positive_control': any(r['message_id'] == 'f6f25455-60c8-4b52-9ee5-4317b5d0b0a5' for r in primary)})
for tier in ('keyword_literal_subset', 'sender_default', 'combined_limited_replay', 'sender_role_proxy', 'combined_role_proxy'):
    routed = [r for r in primary if r[tier] != 'coordinator']
    bad = [r for r in routed if r[tier] != r['label']]
    print(tier, {'routed': len(routed), 'wrong': len(bad), 'offload_pct': 100*len(routed)/len(primary), 'misroute_all_pct': 100*len(bad)/len(primary), 'misroute_routed_pct': 100*len(bad)/len(routed) if routed else None})
limited = [r for r in primary if r['keyword_literal_subset'] != 'coordinator' or r['sender_default'] != 'coordinator']
print('limited_replay', {'routed': len(limited), 'wrong': sum((r['keyword_literal_subset'] if r['keyword_literal_subset'] != 'coordinator' else r['sender_default']) != r['label'] for r in limited)})
PY
```

The preceding snapshot read recorded its then-current UTC/hash; the corpus
specialist's final snapshot/hash above supersedes that intermediate artifact.
The exact displayed counting command was rerun after the final raw update,
exit 0, and reproduces every measured row in the table with numeric percentages.
The corpus specialist initially observed `FileNotFoundError` for the control
recipient, rc 1; its subsequent narrow read found the same recipient at line
368, rc 0. These concurrently updated transcript observations are a transient
read gap, not evidence that the delivered control was absent or lost.

## Current hook decision and evidence

Rev 3 is a **DRAFT, NOT RATIFIED**. The proposed full chain is: precedence /
passthrough and coordinator-only obligations → trusted helper envelope →
published optional legacy grammar → independently declared, narrow sender
report default → optional Python classifier → concrete coordinator fallback.
The LLM tier remains disabled; no threshold, latency, numeric cost or majority
result is invented. Conflicting or mixed responsibilities abstain. Routing
never grants a heavy-run lease, shipper custody or coordinator queue admission.

S0 evidence changes the sender transport: mod readdress under auto mode
returned `isDelivered=false` with classifier "no verdict"
(`s0-probe/events.jsonl:7-8`); native PreToolUse rewrite reached the recipient
(`:68-69`). `s0-probe/pretool.py:6-7` preserves the entire input with `**ti`
before changing `to`. This proves a model tool send in that probe setup;
plugin `$.session.send`, production policy and every worktree are not proven.

Current repository integration is absent:
`.claude/settings.json:72` excludes `SendMessage`, `:77` has a 20-second
timeout; `scripts/pretooluse-guard.sh:35,40` calls `hook_dispatch`;
`hook_dispatch.py:39,50-72` excludes/ignores `SendMessage`;
`hook_guard.py:1081-1125` returns deny-or-silent, not an `updatedInput` object.
The brief's `hook_guard` shorthand must therefore be read as
wrapper → existing dispatch → **new, UNBUILT Python routing branch**, retaining
all existing deny precedence. Rev 3 corrects this seam explicitly.

Offline official hooks documentation was read by the config specialist at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md`:
`:1597` exposes native `tool_use_id`, `:1808` says `updatedInput` replaces
the whole object, `:1811` specifies permission precedence, and `:869-874`
says timeout discards output and normal permission handling continues.
Native sender tool ID and recipient peer message ID are distinct; their PR2
mapping is UNBUILT. Cache decisions by durable ingress ID, retaining policy /
model / prompt revision, body hash, repository, sender provenance, confidence
and disposition; resolve the current concrete role name/epoch on notification.
Preserve the original body in PR2 custody before notification. A proposed
one-call `coord-router return --message-id ID --reason TEXT` records the return,
forces the coordinator destination and avoids specialist reclassification.
Reconcile effects before retrying; enqueue is not read/applied/complete.

Auth presence was actually checked by the config specialist under native
`fnox codex_research`, rc 0: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
`ANTHROPIC_PROFILE`, `IDENTITY_TOKEN`, `IDENTITY_TOKEN_FILE`,
`FEDERATION_RULE_ID`, `ORGANIZATION_ID`, and `CLAUDE_CODE_OAUTH_TOKEN` absent;
Anthropic active/default config paths absent. The project environment has
`anthropic 1.6.0`. This route-specific absence does not show that the user
lacks credentials. No Anthropic inference/auth route was exercised, and the
profile's Exa/Firecrawl injection does not authenticate that SDK. SDK default
600-second timeout and two retries require explicit override and a whole-call
deadline before enabling inference inside a 20-second hook.

## Current strict-five receipt and primary verification

**RESEARCH INCOMPLETE:** GitHub discussions returned `canary returned 0 items`;
Firecrawl search returned `exited 1: Error: Request failed with status code 402 |`.
The required research command ran initially and exited **1**. The research
stop hook then explicitly required a retry of the same strict-five request;
the parent reran the exact command below, again exiting **1**. All provider
routes were attempted on both runs; neither is a successful five-provider audit.

```bash
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout -- 'Claude Code SendMessage PreToolUse updatedInput hooks message routing' --repo anthropics/claude-code --strict-five --request-id 01a109af-8ac0-7460-b171-9e7bc1fd4f25 --last30days-plan /Users/rmanaloto/.codex/research-coverage/01a109af-7bc4-7542-bcbb-3ac837aca55c/01a109af-8ac0-7460-b171-9e7bc1fd4f25/last30days-plan.json --out /Users/rmanaloto/.codex/research-coverage/01a109af-7bc4-7542-bcbb-3ac837aca55c/01a109af-8ac0-7460-b171-9e7bc1fd4f25
```

Manifest: `/Users/rmanaloto/.codex/research-coverage/01a109af-7bc4-7542-bcbb-3ac837aca55c/01a109af-8ac0-7460-b171-9e7bc1fd4f25/manifest.json`.
The retry regenerated that path with
`generated_at=2026-10-05T01:50:10.905343+00:00`, preserving request ID
`01a109af-8ac0-7460-b171-9e7bc1fd4f25`. The parent inspected the initial
normalized manifest and raw evidence schema, rc 0. After retry, native
`fnox` / `uv` directly invoked the public `validate_strict_five` interface
and reviewed all eight normalized route rows and raw-evidence presence, rc 0.
The validator returned `(False, 'github-discussions did not complete')`;
the fanout diagnostic remained
`strict-five fail [github-discussions did not complete]`.
The table below describes the regenerated receipt. The first attempt returned
six Last30Days items; the retry returned five. Other route results and exact
blockers were unchanged.

| Route actually attempted | Status | Items / blocker |
|---|---|---|
| GitHub issues | `ok` | 2 |
| GitHub discussions | `empty_unverified` | 0; `canary returned 0 items` |
| GitHub releases | `empty_verified` | 0; control 1 |
| Exa HTTPS API | `ok` | 10 |
| Context7 `ctx7` | `ok` | 5 |
| Firecrawl developer HTTPS API | `ok` | 10 |
| Firecrawl search CLI | `error` | 0; HTTP 402 |
| Last30Days Python engine | `ok` | Retry 5 (first attempt 6); GitHub/grounding source status `ok` on both |

Fresh primary-source fallback ran under `fnox`/`uv` with `gh api`, rc 0:
official [hook-development skill source](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/hook-development/SKILL.md)
blob SHA `d1c0c199c70e8cef8fee8d3b792b0a27ff33046c`, `:149` `updatedInput`,
`:481-487` timeout. Official [issue #90725](https://github.com/anthropics/claude-code/issues/90725)
was fetched, rc 0: its Windows report describes full-input replacement in
2.1.251 / 2.1.248; treat it as a platform/version report, with local S0 and
official hooks docs supplying the relevant control. A direct primary HTTPS
read of `https://code.claude.com/docs/en/hooks.md` using
`urllib.request.urlopen(..., timeout=30)` under `fnox`/`uv` failed, rc 1:
`HTTP Error 403: Forbidden`. That failed route remains recorded despite the
GitHub fallback.

Actual routes/tools: parent used `codex-sdlc-team` skill and consulted
Last30Days plan/schema; fanout used the cached Last30Days plugin Python engine,
`fnox`, external `mise`, `uv`, `gh` REST/GraphQL, `ctx7`, Firecrawl CLI,
and Exa / Firecrawl developer HTTPS APIs. Primary fallback used `gh api` and
Python `urllib`. Specialists used `cat`, `rg`, read-only `git status`,
`uv run --project python python` analytical snippets and allowlisted document
patches. No connector app, MCP tool or Claude session ran. Mandatory external
research receipt/plan is the sole higher-priority exception to the requested
allowlist / no-mise-task scope; repository validation gates did not run.
No credential value was printed or persisted.

## Previous attempt: resolved source-premise dissent

The previous attempt stopped because its brief described inbound peer delivery
as a user-text record. The known control existed as a `queued_command` peer
attachment instead. The revised fix brief explicitly adopts that observed
representation and cross-representation deduplication; this source-premise
stop is superseded, while other measurement blockers remain independent.
Verbatim dispatcher history is preserved in
`docs/research/kb/reports/agents/sdlc-review-coord-router-freetext-9c669e3f.md`,
Blocks 4–8 and 9–10.

Control provenance, all under
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/`:

- Sender `fc5ba9a3-6f09-47c7-b6d8-a22cb04d5ff8.jsonl:921`: outgoing summary
  `coord-router deliverable: report, ranked specs, Ray decisions`; `:922`:
  success receipt, message ID `f6f25455-60c8-4b52-9ee5-4317b5d0b0a5`.
- Recipient `a629f1c6-a768-4d31-bfb0-554130b32258.jsonl:368`: queued peer
  attachment, sender `dotfiles-20261004T191624-05.coord-router`, same ID/body.
  `:348` / `:367` are enqueue/remove copies, not independent sample messages.
- Previous diagnostic inventory: 27 coordinator sessions, 148 tagged user-text
  records, 377 unique peer attachments. Those representations were not fully
  deduplicated against each other, hand-labelled or evaluated; the figures
  were historical inventory only and are superseded by this run's snapshot.

Previous API findings remain supported by local primary evidence:
`mod-api-session-send-receive.d.ts.txt:458-476` exposes classifier output
`string | undefined` without confidence, and `:316-345` lacks native router
`message_id`, `repo`, or `hops` fields. PR2 state/router/schema interfaces are
absent; their proposal is
`sdlc-review-coordinator-roles-a3d6e816.md:206-214`. The old spec also cited an
absent `handoff-relay-rule-r2-2026-10-04.md` and a `devcontainer.json:129`
workspace-folder field as messaging evidence. Rev 3 removes those premises;
containers remain out of scope by Ray's ruling.

Prior strict-five receipt (request `01a109a1-fe6b-7271-a196-97065ab7fce8`)
ran with exit 1: GitHub discussions canary zero, Firecrawl search HTTP 402.
That incomplete receipt did not supply a measured router or classifier. This
run's separate receipt and its same remaining failures are documented above.

## Current delivery status

The documentation specialist changed only the allowlisted spec and report;
the Python specialist owns the allowlisted labelled corpus. Rev 3 is a draft
interface correction. Required tier/combined-chain measurements and majority
acceptance remain blocked where evidence is missing. Ray rulings are preserved
verbatim. No S0–S5 implementation, repository validation gates, commits,
pushes or new Claude sessions ran. Documentation lint was explicitly prohibited,
so this report does not claim a green documentation gate or a complete fix.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — current
  issues/discussions/releases and provider search target, plus official hook
  skill and issue #90725 primary verification. Read-only; no GitHub mutation.
