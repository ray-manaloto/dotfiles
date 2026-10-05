# Codex takeover Phase A research — 2026-10-05

Evidence and design for W0–W5, umbrella [#1721](https://github.com/ray-manaloto/dotfiles/issues/1721).
This report is the incremental findings record. Phase A changes evidence and
specifications only; the caller owns committing. Parent scope:
`docs/specs/codex-takeover-2026-10-05.md:95-102`; Phase A acceptance:
`docs/specs/codex-takeover-phaseA-research.md:66-70` (read this run).

## Verdict and licensed dissent

**Recommend W0(b): keep the `CLAUDE.md` → `@AGENTS.md` stubs.** Claude AGENTS.md
support has shipped; the reason to retain stubs is documented fallback/nested
loader limitations, migration cost, and the missing replacement-load proof on
this host. The parent pre-grilling conclusion that the mod has not shipped is
superseded by the primary changelog. Do not use the installed-plugin list to
infer built-in activation.

**RESEARCH INCOMPLETE:** the exact mandated strict-five-v2 invocation exited **1**:
`github-discussions` is `empty_unverified`, reason `canary returned 0 items`;
the validator says `github-discussions did not complete`.
Final saved rerun also reports an OpenAI releases error: `fan-out did not verify this search`, count **-1**, not a measured zero. The repository metadata
confirms `anthropics/claude-code.has_discussions=false`; this is a capability gap,
not evidence of no relevant discussions. OpenAI discussions were searched
successfully, but they cannot retroactively pass the failed mandatory manifest.

**PROVISIONAL:** Firecrawl search exhausted credits (primary HTTP 402) and was
substituted with Serper HTTP 200. Five bare Firecrawl mirror requests exited **1**
with `Error: Insufficient credits to perform this request`. Validated Webclaw
fallback mirrors are explicitly marked provisional below. Credits exhaustion
does not establish that a key is missing or that a source is quiet.

**W4 enabled self-heal is stopped under licensed dissent.** The live watcher says
coordinator AUTO-LAUNCH is OFF until the relay-rule r3/#1681 resolver lands **and**
the lane authorizes the switch. Issue closure alone does not authorize enabling
it. Phase B may specify and test a disabled/report-only launcher. Source read by
Python specialist: main checkout `.agent/plans/handoff-inbox/watch.md:122`.

**W1/W4 inventory premise correction:** `claude agents --json --all` rc **0** returned 133 mappings. The universal keys are `cwd,id,kind,sessionId,startedAt,state`; `name` is **optional**, contrary to the Phase A spec. Unknown coordinator identity blocks takeover rather than inventing a name. Architect must correct the mandatory-name premise before Phase B dispatch. Raw `config/session-inventory-receipt.json`; `config/audit.md:206`.

**W5b coordinator mutation is held.** Existing authorization checks Claude's
session ID/job record and creation time; Codex must not spoof a Claude identity.
A provider identity extension and process-hardening parity are prerequisites for
Codex plan/queue mutation. Source read by Python specialist:
`python/src/dotfiles_setup/handoff_inbox.py:22-34`.

## Workstream decisions

| W | Verdict or concrete design | Evidence and prerequisite |
|---|---|---|
| W0 | Keep current stubs and `.claude/CLAUDE.md`; no zero-CLAUDE migration in Phase B. | Shipped support and remaining limits below; `hk.pkl:775-798`, `rule-sync.toml:33` |
| W1 | Reuse session ledger discovery and provider-qualified IDs; add `session_registry` projection and `lane-cards` public task. Cards carry paths, eligible state, tasks, unresolved questions and provenance. | Python specialist's existing-interface evidence; Phase B design |
| W2 | One issue per working/blocked/stopped session, collapse successor roles; skip done. Route proposed issue/plan deltas through coordinator. | Parent ratified scope `codex-takeover-2026-10-05.md:95-102`; no Phase A issue filing |
| W3 | Extend existing ledger-backed command-audit/session-review with since selector and normalized command shapes; do not implement a second rollout parser. | `session_ledger.py:1421-1482`, `:2119-2150`; `SessionStore` provider-qualified IDs `:116-119` |
| W4 | Read-only typed detector plus disabled launcher/15-minute launchd specification. Live-coordinator, lock, uniqueness and inbox evidence fail closed. | Watcher OFF ruling and provider authorization prerequisite above |
| W5a | Compact explicit bootstrap read of a policy index, then applicable `.claude/rules` and `.claude/CLAUDE.md`; reuse existing `.agents/skills` mirror. | Codex primary source/docs below; root budget measured below |
| W5b | Codex coordinator runbook covers main-checkout ship queue, SLOT GO, handoff and land; mutation blocked until identity/parity prerequisite. | Existing handoff-inbox authorization; Phase B design |

The interfaces, future file list, acceptance controls and disabled-state gates
are specified in `docs/specs/codex-takeover-phaseB-design.md`. They are proposals
for architect ratification, not enabled capabilities.

## W0: shipped support, active support and migration cost

The primary Claude [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
adds AGENTS.md support under **2.1.277** and expands it to Bedrock, Vertex,
Foundry, gateways and telemetry-disabled sessions under **2.1.281**. This run
fetched the changelog via native `fnox exec -- gh api`, rc **0**; raw anchors:
`docs/research/kb/raw/codex-takeover/claude-changelog.md:1057` and `:892`.
The [source PR #95409](https://github.com/anthropics/claude-code/pull/95409)
is merged (2026-09-18); its API body says tests ran with 2.1.276 and 2.1.277.
Feature request [#6235](https://github.com/anthropics/claude-code/issues/6235)
is closed. These are release/source facts, not local runtime load evidence.

Installed `claude --version` is **2.1.289**, rc **0**. The
[v2.1.289 release](https://github.com/anthropics/claude-code/releases/tag/v2.1.289)
was published 2026-10-03T23:07:17Z. The JSON installed-plugin list returned 312
entries, zero `agents-md` and zero `@builtin` rows. That establishes only the
installed-registry result. The README describes `/plugin` built-in listing;
config specialist's `claude plugin configure agents-md@builtin --json` rc **1**
says no *installed* plugin has that id. **A:** `agents-md@builtin` is active and
loads replacement instructions on this particular host; no isolated positive/
negative live load test was authorized within Phase A's write allowlist.

The [agents-md README](https://github.com/anthropics/claude-code/blob/main/mods/agents-md/README.md)
and mirrored implementation expose four `instructionFiles` values, with
`claude-md-or-agents-md` default. Options belong in user, explicit `--settings`,
or managed configuration, not project plugin options. In fallback mode any
project-owned `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` on the walk
stands the plugin down. In both mode it deduplicates imported files by path
then content. Verified raw source: `links/agents-md/README.md:5-23`, `:45-75`,
`hooks/names/claude-names.ts` and `hooks/names/agents-names.ts` beneath
`docs/research/kb/raw/codex-takeover/` (read this run).

Current README was fetched directly via gh API, rc0, and confirms the mirrored
limits (`claude-agents-md-current.md:131-158`). Remaining limits are explicitly
documented in README's “Where it still differs”:
nested attachment on text Read rather than all native triggers; changed nested
files do not receive the same mid-session announcement/compaction restoration;
path spelling differs for symlinks; added directories contribute no AGENTS.md;
`/memory` and `#` do not know the files; external import approval remains tied to
CLAUDE imports; non-fork subagents get nested instructions at their own first
Read. These are documented source limits, not newly reproduced defects.

| Primary GitHub record, fetched this run | Interpretation |
|---|---|
| [#98796](https://github.com/anthropics/claude-code/issues/98796), open | 2.1.287 report: nested AGENTS missing on prompt @mention while nested CLAUDE loads; agrees with README limit |
| [#96117](https://github.com/anthropics/claude-code/issues/96117), open | Reporter reproduces CLAUDE.local disabling default AGENTS fallback; reports import stub succeeds in control |
| [#97004](https://github.com/anthropics/claude-code/issues/97004), open | Reporter says /init writes CLAUDE.md and disables default AGENTS fallback |
| [#95589](https://github.com/anthropics/claude-code/issues/95589), open | 2.1.278 intermittent-load report; no claim it reproduces in installed 2.1.289 |
| [#95690](https://github.com/anthropics/claude-code/issues/95690), open | 2.1.277 remote-switch/telemetry complaint; 2.1.281 changelog supersedes provider restriction, not proof all reported failures fixed |
| [#97261](https://github.com/anthropics/claude-code/issues/97261), open | Reporter says /doctor ignores AGENTS/imported content; lint budget and explicit byte measurements remain necessary |

Repository impact favors retaining stubs. `claude_md_import_stub` validates thin
imports and `claude_agents_md_pairs` requires pairs, with `.claude/` exception;
removing all stubs would require intentional changes to both gates and tests.
`rule-sync.toml:33` mirrors whole lines across both repos' `.claude/CLAUDE.md`;
renaming that file affects knowledge-base consumers. The root is 11,978 UTF-8
bytes, **11,892 Unicode characters**, 194 lines: **108 characters** of headroom
under 12,000 characters, not 22 characters. `hk.pkl:660-666` is agnix's
AGM-003/Windsurf-oriented guidance budget, not a Claude truncation assertion.
Config evidence: `docs/research/kb/raw/codex-takeover/config/audit.md`.

A future zero-CLAUDE migration requires isolated positive/must-not-load controls,
root and nested Read/@mention/add-dir/fork cases, preserving imports, approved
exact settings diff, both-repo gate/sync updates, and rollback before deleting
stubs. Those changes are outside this Phase A implementation.

## W5a: the cheapest supported bridge

The [current AGENTS guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
was fetched through the native mirror probe: rc **0**, route Webclaw,
**provisional**, 8,063 bytes. It specifies global override/default selection,
Git-root-to-cwd ancestor traversal, at most one file per directory, and a
32 KiB default project-doc budget. Raw:
`docs/research/kb/raw/codex-takeover/links/codex-agents-md-fallback.md:16-21`.

Current [Codex source](https://github.com/openai/codex/blob/823ea830c0fd418b09ff02d36cad9a1fff66465b/codex-rs/core/src/agents_md.rs)
was fetched via gh API, rc **0**. It reads/truncates within remaining bytes
(`codex-agents-md.rs:133-168`), chooses the first existing file per directory
(`:242-259`), orders `AGENTS.override.md`, `AGENTS.md`, then fallbacks (`:272-276`),
and rejects fallback entries containing path separators (`:281-288`). Source
SHA **823ea830c0fd418b09ff02d36cad9a1fff66465b**, from the complete non-truncated
repository tree. Installed Codex is **codex-cli 0.160.0**, rc **0**; current-main
source evidence is not a claim about the exact installed binary. Initial old
`project_doc.rs` lookup returned HTTP 404; tree discovery found `agents_md.rs`.
An unquoted tree URL first failed zsh glob expansion (rc1); quoting it fetched
the complete tree (rc0). No pager pipeline masked these results.

| Candidate | Decision and concrete reason |
|---|---|
| `project_doc_fallback_filenames` | Reject as rules bridge: alternatives, not additive; root AGENTS wins and `.claude/rules/...` is not a filename |
| Nested `.claude/AGENTS.md` | Useful only when cwd ancestor chain enters `.claude`; not an eager root-session bridge |
| Root bootstrap + explicit policy index read | Recommend: reclaim root bytes, add one mandatory read of `docs/agents/codex-policy-index.md`; index orders eager rules and maps scoped rules to touched paths |
| `.codex/skills` duplicate mirrors | Avoid; current official docs specify `.agents/skills` ancestor discovery and existing mirror is verified |
| `instructions` config | Reject: official config docs reserve it for future use |
| `developer_instructions` | Supported additional text, but introduces separately maintained/trust-scoped config; optional bootstrap redundancy, not cheapest default |
| `model_instructions_file` | Avoid replacing built-in instructions to solve a project-document bridge |

Current official skills/config mirrors also completed via Webclaw, rc **0**,
**provisional**, 9,932/188,288 bytes. Current skill-path anchor:
`links/codex-skills-fallback.md:88-96`; config `developer_instructions` at
`links/codex-config-reference-fallback.md:435`, reserved `instructions` at `:769`,
`model_instructions_file` at `:1083`, fallback/budget at `:1599-1605`. Primary
source default is **32768** (`codex-defaults.toml:8-9`), fetched at the pinned
source SHA. These confirm the bridge choices without changing configuration.

Config reference was read from the existing offline primary corpus before network
fetches: `knowledge-base/sources/agent-harness-docs/docs/codex/config-file__config-reference.md:204-213`,
`:233-236`, `:1053-1061`; supported skills paths at `build-skills.md:135-142`.
These are local primary-document snapshots; latest mirror/source checks are
recorded separately. A Markdown link alone does not force a read: the bootstrap
must explicitly instruct reading the index before work. **A:** an instruction
will always be obeyed; actual Phase B positive/reverted-bootstrap tests remain
required. Do not describe a link index as automatic eager rule injection.

Config specialist measured 44 Claude skills, 46 `.agents` skills and one
`.codex` Graphify skill; `mise run skills-mirror -- --check` rc **0**. The
existing generator rewrites harness names and keeps the deliberate Graphify
stub; raw SHA equality is not the mirror contract. Source:
`skills_mirror.py:4-18,122-135,211-216`, gate `hk.pkl:734-738`.

## Research execution and saved-search contract

All network research processes used native
`fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- …`.
No secret value was printed or persisted. No issue filing, PR command, push,
production change, user settings write or ephemeral session was performed.
The developer explicitly required the one native receipt output beneath
`~/.codex/research-coverage/`; its allowlisted copy is `raw/codex-takeover/strict-five/`.

The exact required route ran `mise -C ~/.codex/tools/dotfiles-research-gate run
research-fanout` with `--strict-five`, request id
`01a10bf3-3b78-7e32-9de1-c11098181af2`, explicit Last30Days plan and the mandated
turn output directory. `strict-five/manifest.json` and `invocation.rc` preserve
rc **1** and every source/control/fallback. Root independently called the existing
validator and obtained `passed=false`, reason `github-discussions did not complete`.

| Source actually run | Exact observed result |
|---|---|
| GitHub issues/discussions/releases via gh API/GraphQL | Mandatory Anthro issues ok1, discussions empty_unverified0, releases empty_verified0; tuned AGENTS.md both repos below |
| Exa HTTP API | ok10, native fnox-injected key route |
| Context7 `ctx7 library` + `ctx7 docs` | ok5; leads checked against primary changelog/source |
| Firecrawl developer API | ok10 |
| Firecrawl search CLI | primary HTTP402; Serper fallback ok10 **PROVISIONAL credits-exhausted** |
| Last30Days plugin engine | ok10; explicit plan at `strict-five/last30days-plan.json`; raw engine source_status GitHub, grounding, HackerNews, Reddit, YouTube all ok |
| Five pinned `mise exec -- firecrawl scrape … --format markdown --only-main-content` mirrors | each rc1, Insufficient credits; stdout/stderr/rc per link |
| Native mirror probe | Codex AGENTS, skills and config docs Webclaw fallback rc0 **PROVISIONAL**; bytes8063/9932/188288, records under links/ |
| `mise run graphify-health` | rc3, missing runtime0.9.76 graph; source fallback used, not an empty answer |

### Explicitly requested strict-five rerun

A later Stop-hook request explicitly authorized **one** identical retry for
request `01a10bf3-3b78-7e32-9de1-c11098181af2`. The mandated query, repository,
Last30Days plan and output directory were reused. Refreshed manifest timestamp:
**2026-10-05T12:28:21.684602+00:00**. Exact public command rc **1**; native
`strict_five_verdict` rederivation invocation rc **0**, returned
`passed=false`, reason **`github-discussions did not complete`**. The first
receipt remains in `strict-five/attempt-1/`; `strict-five/manifest.json`
now contains the refreshed receipt. Captures: `attempt-2.stdout`,
`attempt-2.stderr`, `attempt-2.rc`, `attempt-2-verdict.json` and
`attempt-2-verdict.rc`.

| Provider group | Refreshed eight-source evidence | Verdict |
|---|---|---|
| GitHub | issues ok1; discussions empty_unverified0, reason `canary returned 0 items`; releases empty_verified0 | **FAIL**, discussions did not complete |
| Exa | ok10 | completed |
| Context7 | ok5 | completed |
| Firecrawl | developer ok10; search primary skipped, `Error: Request failed with status code 402`; Serper fallback HTTP200 ok10 | **PROVISIONAL**, credits-exhausted substitution |
| Last30Days | ok10; engine source_status GitHub, grounding, HackerNews, Reddit and YouTube all ok | completed |

**RESEARCH INCOMPLETE:** the refreshed GitHub discussion arm still fails its
canary. Anthropic metadata has discussions disabled; no control or row was
fabricated or removed. Neither four completed provider groups nor the
provisional Firecrawl substitution makes the overall receipt pass. The rerun
stderr also records a uv inherited `VIRTUAL_ENV` mismatch warning: the calling
worktree environment was ignored in favor of the research-gate project env.
It was not hidden or treated as the discussion failure's cause; the subsequent
native verifier ran without that warning. The public saved-search `record`
command exited **0**, updated the same three manifest-derived watches, added
none, and preserved all **13** watches. No additional retry is planned.

Apps/MCP connectors: **none**. Exa, Firecrawl, Context7 and Last30Days routes ran
through repository research CLI/native fnox; installed names alone are not
claimed as exercised tools. Additional CLIs actually run: gh, curl, claude,
codex, uv/Python, mise; config specialist's pinned Pkl/skills-mirror validation
is in `config/audit.md`. Skills read for this lane: Last30Days query-plan schema;
its public engine was invoked by the required fanout, not a standalone social
brief. The root applied `.agents/skills/codex-sdlc-team/SKILL.md` for specialist routing
and evidence, and read `research-sweep/SKILL.md` for receipt/control guidance;
no separate research workflow was invoked. Exa/Firecrawl skill workflows were
not independently invoked. The SDLC documentation role owns `lint-docs` after
writer readiness.

Every search is captured through `mise run research-saved-search record` and
`rerun`; TOML was never hand-written. Code watches were registered before they
ran. Network fanout queries were imported through `record --fanout-manifest`.
The generated TOML contains **13 watches**: four code watches and issues,
discussions and releases for the mandatory Anthro query and tuned `AGENTS.md`
queries in both repos. Code queries collect every result up to the API cap;
positive README controls, health control and fresh nonce absent controls are
preserved. Tune with the public recorder rather than hand-editing its generated
file. Re-run snapshots/report are isolated under this lane's raw directory.

Tuned AGENTS.md runs: OpenAI issues10/discussions10/releases2 all ok; Anthro
issues10/releases10 ok, discussions unverified because the canary is empty.
The GitHub issue-search surface includes issue and PR records; merged mod PR
#95409 was additionally read directly. OpenAI discussion coverage includes
[#50487](https://github.com/openai/codex/discussions/50487) and
[#47058](https://github.com/openai/codex/discussions/47058); they are discovery
leads, not evidence overriding the current source loader.

Codex primary issue bodies fetched this run:
[#43075](https://github.com/openai/codex/issues/43075), open long-file truncation
report; [#43309](https://github.com/openai/codex/issues/43309), open reload/freeze
feature request; [#12115](https://github.com/openai/codex/issues/12115), open
nested-instruction discoverability tracker. These motivate controls and clear
provenance; they are not live reproductions against installed 0.160.0.

## Verification and remaining gaps

First full saved-search rerun exited **1**: ok5, empty-verified1,
empty-unarmed1 (Anthro discussions). Controls: health9, absent0/0, must-hit51/29.
Raw `saved-search-rerun.md` and isolated snapshot preserve the result.
Final **13-watch** rerun exited **1**: ok9, empty-verified1, empty-unarmed2,
error1. Both Anthro discussion watches remain unarmed. OpenAI AGENTS releases
changed from baseline ok2 to **error count-1**, reason `fan-out did not verify
this search`; this failure establishes no absence and NEW/GONE is n/a. Raw
`saved-search-rerun-final.md`, `saved-search-rerun-final.rc`, and snapshot
`20261005T121430Z.json` preserve it. No retry was launched merely to obtain a green result. A subsequent explicit
Stop-hook request authorized one identical strict-five rerun; its rc **1**
and the first receipt are preserved under `strict-five/attempt-2.*` and
`strict-five/attempt-1/`. Native generated-file parser/status rc **0** and isolated invalid-enum
fail arm rc **2** verify TOML structure only (`config/saved-search-parser-receipt.json`).
**Documentation lint PASS:** after Python froze the design and config confirmed
consistency, the single required `mise run lint-docs` invocation exited **0**:
`agnix . --strict`, `No issues found`. Captures: `lint-docs.stdout`,
`lint-docs.stderr`, `lint-docs.rc` under this raw directory. No broad lint,
pytest or verification gate was run for this evidence-only change; the root
found no SLOT GO for heavy gates. Passing doc lint does not clear the failed
strict receipt or saved rerun.
Failed watches remain present; they are not removed to manufacture a green gate.

Remaining integration gaps: actual replacement-mod instruction load on this host;
Phase B bootstrap positive and removed-bootstrap controls; provider-authorized
Codex coordinator writes; OFF-to-enabled launch authorization; dependency
`process-hardening` guard parity; credit-fallback-finish
[#1577](https://github.com/ray-manaloto/dotfiles/issues/1577); existing
handoff-automation-research receipt 703e5612. These lanes are dependencies, not
reimplemented here. Graph/source corpus cannot prove actual unattended launch,
coordinator mutation, import approvals or exact installed-runtime behavior.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): parent specs,
  #1721 scope, live watcher/queue and existing modules; no issue/PR mutation.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base):
  read-only offline primary documentation and rule-sync impact.
- [anthropics/claude-code](https://github.com/anthropics/claude-code): saved code,
  issue/PR/release/discussion probes, current changelog, mod source and metadata.
- [openai/codex](https://github.com/openai/codex): saved code/issues/discussions/
  releases, current source tree and documentation; source SHA pinned above.
- [cli/cli](https://github.com/cli/cli): public saved-code-search health control.
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill): local
  plugin 3.26.0 plan-schema instructions, engine invoked by research-fanout.
