# Codex capacity & scaling research — sdlc-team run 8c454bf3 (2026-10-04)

Verbatim dispatcher output (`output.md`) of codex sdlc-team run `8c454bf32142434c8d5f178055f2839a`
(mode review, `gpt-6-astra`, effort xhigh; settled `completed`, rc=0, 1321s; specialists observed:
config, documentation, python). Requested by Ray 2026-10-04. Research only; nothing implemented.

---

RESEARCH INCOMPLETE: the strict-five rerun exited **1** because `firecrawl-search` returned **`exited 1: Error: Request failed with status code 402 |`**. `firecrawl-developer` recovered and returned 10 items. All required routes were attempted; coverage remains incomplete.

# Codex capacity, scaling, and research integration review

**Date:** 2026-10-04  
**Recommendation:** use native task-sized concurrency and explicit model routing first, then checkpoint-aware recovery. Improve the existing research skills and backend rather than build a second research system.

All three specialists finished. No checkout files were changed, report file written, repository gates run, commits created, or live-run processes disturbed. The mandatory research receipts were written outside the checkout.

## 1. Incident root cause

Run `311a6ebe2a2b4b5bbb30a1fa1fe80d45` used **Codex CLI 0.160.0**, **`gpt-6.1-sol`**, and dispatcher effort **`xhigh`**. Settlement records **rc=1**, **922.389871958 seconds**, and three observed specialists: two documentation specialists and one configuration specialist. Its log ends with the capacity error twice. [Incident log](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/.agent/sdlc-runs/311a6ebe2a2b4b5bbb30a1fa1fe80d45/codex.log:7083), [settlement](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/.agent/sdlc-runs/311a6ebe2a2b4b5bbb30a1fa1fe80d45/settlement.json:1).

**Supported diagnosis:** Codex classified the failure as server/model overload. Version 0.160.0 distinguishes `ServerOverloaded` from usage exhaustion, quota errors, rate limiting, and agent limits. Backend `server_is_overloaded` maps to `ServerOverloaded`; `slow_down` maps to `RateLimitExceeded`. [Error definitions](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/protocol/src/error.rs#L144), [backend mapping](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/codex-api/src/api_bridge.rs#L101).

That establishes the client’s error classification, not the underlying infrastructure cause.

### Retries and fallback

Codex 0.160.0 behaves differently across failure paths:

| Path | Verified upstream behavior |
|---|---|
| HTTP overload with `Retry-After` | Request retries can honor the advised delay. |
| Headerless HTTP 503 overload | Request retries can exhaust before the terminal capacity error. |
| SSE overload | Terminal in inspected tests, including an enclosing `Retry-After` header. |
| WebSocket overload | Terminal in inspected tests, without HTTP fallback. |

These are inspected implementation and test assertions, not tests executed during this review. [HTTP retry tests](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/tests/suite/retry_after.rs#L278), [HTTP exhaustion](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/tests/suite/retry_after.rs#L428), [SSE](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/tests/suite/retry_after.rs#L1297), [WebSocket](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/tests/suite/retry_after.rs#L1866).

Terminal classification returns before connection retries or transport fallback. Raising stream-retry settings does not override it. [Retry classification](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/protocol/src/error.rs#L385), [shared retry handler](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/src/responses_retry.rs#L86).

The local supervisor launches one Codex process, waits once, and settles. It has no retry, resume, or model-failover branch. Missing `output.md` caused additional reconciliation failures; those do not explain the original Codex rc=1. [Supervisor](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/python/src/dotfiles_setup/sdlc_team.py:997).

### Unknowns

- The incident log does not establish transport, response headers, request IDs, or network-attempt count. Two printed errors do not prove two requests.
- Parallel specialists plausibly increased demand, but their causal contribution is unproven.
- The protected second run was not inspected. Its overlap and contribution remain unverified.
- The log reports **43 of 108 decisions completed, leaving 65**. This review did not independently recount those files or verify the subsequent Opus completion. [Recorded progress](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/.agent/sdlc-runs/311a6ebe2a2b4b5bbb30a1fa1fe80d45/codex.log:7057).

Similar reports exist in [issue #46142](https://github.com/openai/codex/issues/46142) and [discussion #45848](https://github.com/openai/codex/discussions/45848). They are user reports, not backend diagnoses of this incident.

## 2. Native Codex mechanisms

The installed version and latest stable release both resolved to **0.160.0**, released **2026-10-01T20:19:13Z**. Version, main help, exec help, exec-resume help, and features-list probes all exited **0**. [Release](https://github.com/openai/codex/releases/tag/rust-v0.160.0).

| Mechanism | Practical consequence |
|---|---|
| Agent TOML `model`, `model_reasoning_effort` | Native per-role selection; role configuration wins over resolved spawn/default settings. |
| `agents.default_subagent_model`, `agents.default_subagent_reasoning_effort` | Native defaults for unspecified spawn settings. |
| `agents.max_concurrent_threads_per_session` | Public per-session cap excludes the primary; `agents.max_threads` remains a legacy alias. |
| `agents.max_depth` | V1 nesting control; V2 ignores it. |
| `codex exec resume SESSION_ID --model …` | Native recovery primitive, without transactional or duplicate-write guarantees. |
| `--profile NAME` | Loads `$CODEX_HOME/NAME.config.toml`; legacy profile tables stopped being read in 0.134.0. |
| Provider retry settings | Request/stream retries and timeouts govern specific paths, not arbitrary model failover. |

Sources: [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced), [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), [0.160 schema](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/config.schema.json).

All six local SDLC definitions pin effort to `high` and omit `model`. A dispatcher requesting lower effort therefore cannot assume it overrides the role. [Dispatcher definition](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/.codex/agents/codex-sdlc-dispatcher.toml:9).

Source defaults are six children for V1 and four total threads for V2. The V2-specific cap includes the parent; the public setting excludes it. This research environment explicitly allowed four total slots. These defaults do not establish the incident’s effective or account-wide limit. [Defaults](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/src/config/mod.rs#L254), [translation](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/src/config/mod.rs#L2760).

### Fallback qualifications

The 0.160 schema contains no keys named `fallback_model`, `fallback_models`, or `model_fallback`. That bounded finding does not mean Codex has no internal fallback: the older pinned source contains a narrow compaction fallback between previous and current models. [Compaction implementation](https://github.com/openai/codex/blob/6b9826e3aa83b1a5947db50f4332cb9c65f1b340/codex-rs/core/src/compact_model_fallback.rs#L8).

Current upstream Python SDK source provides opt-in `retry_on_overload()` with three attempts by default. It classifies RPC exceptions. A failed completed turn raises ordinary `RuntimeError`, which that classifier does not accept; the helper also does not select another model. It is not automatic recovery for this supervisor. [Helper](https://github.com/openai/codex/blob/main/sdk/python/src/openai_codex/retry.py#L12), [classifier](https://github.com/openai/codex/blob/main/sdk/python/src/openai_codex/errors.py#L86), [completed-turn failure](https://github.com/openai/codex/blob/main/sdk/python/src/openai_codex/_run.py#L60), [RPC wrapper](https://github.com/openai/codex/blob/main/sdk/python/src/openai_codex/client.py#L731).

Official guidance identifies Sol for complex work and Luna for focused, repeatable tasks. Account access remains deployment-dependent. Service-tier selection is separate; no reviewed source guarantees that changing tier fixes capacity refusal. [Models](https://learn.chatgpt.com/docs/models).

Relevant changes after 0.152.1:

- **0.156.0:** improved preservation of streamed answers/plans, resume behavior, and analytics. [Release](https://github.com/openai/codex/releases/tag/rust-v0.156.0).
- **0.159.0:** removed bundled `plugin-creator`. [Release](https://github.com/openai/codex/releases/tag/rust-v0.159.0).
- **0.160.0:** improved subagent environment preparation/error reporting, provider catalogs, and repeated plugin loading. [Release](https://github.com/openai/codex/releases/tag/rust-v0.160.0).

Installed `step_model_switching` was under development and disabled; it should not be presented as established autoscaling.

## 3. Ranked scaling and recovery proposals

### 1. Task-sized native fanout and explicit routing — recommended first

**Change:** select required roles from task scope and schedule them within an explicit cap. Evaluate focused models for mechanical slices while preserving all required specialist coverage.

**PRO:** uses existing controls; reduces unnecessary concurrent demand; makes model/effort choices reviewable.

**CON:** fewer workers can increase elapsed time; model quality/access require checks; current effort pins override dispatcher adjustments.

**Files:** `.codex/agents/codex-sdlc-*.toml`, canonical agent definitions, `.claude/rules/codex-sdlc-team.md`; `sdlc_team.py` and request schema if exposing a caller-owned cap.

**Verification:** an isolated real task must demonstrate required roles, resolved model/effort, and peak concurrency. Reverting routing/cap changes must fail the corresponding acceptance case.

This deliberately changes “spawn every applicable specialist immediately”; it must not silently omit required roles.

### 2. Checkpoint-aware native resume — recovery foundation

**Change:** retain completed-unit evidence, session identity, child state, and remaining work; reconcile them before native resume.

**PRO:** preserves successful work and directly addresses the incident’s partial completion.

**CON:** history is not a transaction log; active old writers or stale checkpoints can create conflicts.

**Files:** `sdlc_team.py`, request/settlement schemas, `tests/test_sdlc_team.py`, SDLC skill guidance.

**Verification:** public-entrypoint execution in isolated state must complete some units, fail, and resume only the remainder. Wrong session/workdir, active old writer, stale checkpoint, and missing child evidence must refuse recovery. Include real native resume evidence.

Coordinate ownership and specialist reconciliation with [existing issue #1165](https://github.com/ray-manaloto/dotfiles/issues/1165).

### 3. Bounded explicit model fallback — after reconciliation

**Change:** introduce an approved model chain, attempt/time budgets, typed error classification, and distinct receipts for every attempt.

**PRO:** supports auditable recovery and reduces manual restarts.

**CON:** alternatives may also be overloaded; capability, access, quality, and cost differ. Text-only matching and blind implementation replay are unsafe.

**Files:** `sdlc_team.py`, request/settlement schemas, corresponding tests, request guidance.

**Verification:** overload→success, overload→exhaustion, and noncapacity failures through public interfaces. Credentials, invalid requests, quota, policy failures, and specialist-spawn failures must not silently trigger switching. Retain failed-attempt evidence; supplement deterministic controls with a real integration.

### 4. Cross-run admission control — conditional

**Change:** reuse existing coordinator infrastructure to budget concurrent roots and children.

**PRO:** addresses aggregate demand beyond one session.

**CON:** adds fairness, lease, and stale-owner recovery complexity; cannot guarantee backend availability.

**Files:** `sdlc_team.py`, existing coordinator integration, schemas/tests.

**Verification:** two isolated public-entrypoint runs must queue/release correctly; crashes must not leave permanent reservations. Removing admission enforcement must violate the approved concurrency assertion.

Measure overlapping demand before adopting this as the incident’s remedy.

### 5. Named profiles and resolved execution evidence

**Change:** define approved operating profiles and record requested/resolved model, effort, tier, cap, CLI version, session, and attempt lineage.

**PRO:** repeatable task classes and stronger future diagnosis.

**CON:** profiles do not adapt automatically; explicit supervisor flags can override them.

**Files:** approved managed profile location, `sdlc_team.py`, schemas, documentation.

**Verification:** real isolated launches must demonstrate precedence and reject contradictory configuration. Requested tier must not be reported as proven effective tier.

## 4. Native skills, plugins, and MCP

Codex supports repository skills in `.agents/skills`, explicit `$skill-name` invocation, and implicit selection through descriptions. Optional `agents/openai.yaml` carries invocation policy and dependencies. [Official skills documentation](https://learn.chatgpt.com/docs/build-skills).

The installed `~/.codex/skills/` already includes OpenAI Docs and `codex-team-research`. Release 0.160.0’s installer still uses `$CODEX_HOME/skills`, defaulting to `~/.codex/skills`; migration is not justified solely by a documentation table emphasizing another location. [Installer source](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/skills/src/assets/samples/skill-installer/SKILL.md#L48).

Recommended SDLC guidance:

- **OpenAI Docs:** current Codex contracts.
- **codex-team-research:** team/model/workflow research.
- **research-sweep:** evidence collection, offline sources, and saved searches.
- **skill-creator / skill-installer:** approved authoring or genuinely missing capabilities.

Reference these through `developer_instructions` and AGENTS.md. Do not invent a TOML skills array or use `mcp_servers = ["name"]` to select inherited servers.

`codex plugin --help` exited **0**, exposing installation, listing, marketplace, and removal commands. Current packaging supports root `plugin.json`, `mcp.json`, and `skills/`; `.codex-plugin/plugin.json` remains compatible. [Packaging](https://developers.openai.com/plugins/build/plugins), [plugin loader](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core-plugins/src/loader.rs#L923).

**Proposal:** connect existing skills before packaging another plugin.

**PRO:** smallest change; native discovery and capabilities already exist.  
**CON:** activation still requires real trigger evaluation.  
**Files:** canonical SDLC instructions, `.codex/agents/codex-sdlc-*.toml`, relevant mirrors.  
**Verification:** real research and unrelated trivial prompts must select appropriate behavior; preserve explicit delegation in generated prompts.

The MCP rule remains: externally required plugin/skill MCP is allowed; project-owned research prefers offline/CLI, HTTP API, then `mcp2cli`. No new registration or installation was performed. [Repository policy](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/.claude/rules/research-doc-sources.md:106).

## 5. Research-fanout gap analysis

**The engine and Codex-facing entrypoints already exist.**

| Requirement | Finding |
|---|---|
| Codex research skill | `research-sweep` explicitly supports in-lane Codex/headless execution. |
| Five providers | Existing Python fanout implements eight source arms across the five groups. |
| GitHub issues/PRs/discussions/releases | Implemented; use `is:pr` for targeted PR retrieval. |
| Code-search controls | Implemented and exercised during review. |
| Saved tunable searches | Existing TOML schema and `record`, `rerun`, `status` CLI. |
| Offline optimized docs | Existing procedure reads KB clones and harness docs. |
| Recursive crawl | Distinct from existing search/page mirroring; not exposed by the inspected parser. |
| Strict-five consistency | Main gap: generic skill guidance does not consistently carry the stronger team-research contract. |

Evidence: [task bindings](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/mise.toml:885), [fanout](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/python/src/dotfiles_setup/research_fanout.py:2163), [Codex skill branch](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/.agents/skills/research-sweep/SKILL.md:142), [strict team-research guidance](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/.agents/skills/codex-team-research/SKILL.md:28).

### Verbatim source inventory

Plain `mise run research-fanout -- --list-sources` exited **0**:

```text
[research-fanout] $ uv run --project python python -m dotfiles_setup.research_fanout --list-sources
github-issues  gh api REST  gh on PATH + --repo  needs --repo
github-discussions  gh api graphql  gh on PATH + --repo  needs --repo
github-releases  gh api REST  gh on PATH + --repo  needs --repo
exa  HTTPS POST  EXA_API_KEY in process environment  absent
context7  ctx7 CLI  ctx7 on PATH  present
firecrawl-developer  HTTPS GET  none  present
firecrawl-search  firecrawl CLI  firecrawl on PATH  present
last30days  python3 script  last30days script found  present
```

The prescribed native `fnox` profile changed Exa’s inventory result to `present`, with **rc0**; authenticated sweeps returned Exa results. An inherited environment missing the key was not evidence that the user lacked it.

### Minimal design

Retain:

```text
research-sweep / codex-team-research
  → mise research-fanout → dotfiles_setup.research_fanout
  → mise research-saved-search → dotfiles_setup.saved_searches
```

Align canonical instructions and the Codex mirror around scoped `fnox`, applicable strict-five requirements, explicit Last30Days plans, request IDs, manifest/hash verification, primary-source checks, and review-mode restrictions.

**PRO:** reuses implementation, schemas, controls, and storage.  
**CON:** instructions cannot eliminate provider failures or guarantee activation.  
**Files:** canonical/mirrored research skills; an optional `research-fanout` skill should be only a thin alias.  
**Verification:** real skill activation, missing-plan/request controls, failed-provider acceptance, and isolated saved-search record→rerun with changed results.

Saved files already live in `docs/research/saved-searches/*.toml`; snapshots live in `.agent/kb/raw/saved-searches/`. Public commands support:

```text
mise run research-saved-search -- record --out FILE --fanout-manifest MANIFEST --probe-manifest PROBE
mise run research-saved-search -- rerun FILE
mise run research-saved-search -- status FILE
```

These examples were not executed during review. [Rerun implementation](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/python/src/dotfiles_setup/saved_searches.py:1051).

Older [issue #1502](https://github.com/ray-manaloto/dotfiles/issues/1502) names an N1 `watches.toml` registry. The [checked-in design](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/mintlify-scrub/docs/specs/research-saved-searches-1502.md:58) addresses N1 compatibility, and the workflow uses the existing directory. Do not create another registry; reconcile the older ruling before migration.

### Offline provenance

Offline-first inspection found Codex source pinned to **0.154.0**, older than installed **0.160.0**. The harness-docs manifest pin also differed from its actual clone HEAD; relevant pages retained July update dates, although their hashes matched.

The team stopped treating those copies as current authority and verified upstream. This mattered: the older source mapped `slow_down` differently. No corpus repair or retired documentation fetch was attempted.

## 6. Recommendation and phased plan

1. Approve task-sized scheduling, explicit model/effort policy, and richer receipts.
2. Align existing research skills and SDLC guidance with strict-five and saved-search requirements.
3. Design and verify checkpoint/session/child reconciliation.
4. Add bounded model recovery only after that foundation.
5. Consider cross-run admission, recursive crawl, or plugin packaging only when demonstrated needs justify them.

Ray’s subsequent implementation decision is needed for model/cost policy, concurrency changes, recovery semantics, registry migration, and packaging. No implementation was performed.

## 7. Sources and execution evidence

All cited sources were read on **2026-10-04**. Release-tagged source supports 0.160.0 findings; SDK `main` links describe current upstream code without implying local adoption.

### Strict-five rerun

The exact required command ran again for request `01a108b1-8b0d-7341-885d-73a67218ddec`, using the native research profile, explicit Last30Days plan, and hook output directory.

Latest manifest timestamp: **2026-10-04T21:11:36.768792+00:00**.

| Provider group | Verified outcome |
|---|---|
| GitHub | Issues `ok`; discussions/releases `empty_verified` with successful controls. Targeted follow-ups also succeeded. |
| Exa | `ok`, 10 items |
| Context7 | `ok`, 5 items |
| Firecrawl | Developer `ok`, 10 items; **search failed HTTP 402** |
| Last30Days | `ok`, 8 items; underlying GitHub and grounding statuses `ok` |

Request ID and policy matched. **All eight raw-file SHA-256 values matched.** Overall command **rc=1**; strict-five verdict: **`firecrawl-search did not complete`**. [Verified manifest](/Users/rmanaloto/.codex/research-coverage/01a108b1-5d1e-70d0-b830-0a6e1a03f7e9/01a108b1-8b0d-7341-885d-73a67218ddec/manifest.json).

The initial developer HTTP 502 failure recovered on rerun. The HTTP 402 search failure persisted; no unsupported billing or credential diagnosis is inferred from that status.

### Negative-search controls

| Scoped finding | Negative arm | Positive control |
|---|---|---|
| SDLC model pins absent | `^model\s*=`: rc1 | Effort pin: rc0, six matches |
| Named fallback schema keys absent | Three specified keys: 0 matches | Retry-setting keys: 2 matches |
| Supervisor recovery branch absent | Recovery terms: rc1 | `timeout|Popen|wait`: rc0; body inspected |
| Generic skill lacks strict guidance | `strict-five|fnox`: rc1 | Existing provider/task terms: rc0 |
| Dedicated skill name absent in scoped tree | Exact `research-fanout`: rc1 | Exact `research-sweep`: rc0 |
| Crawl/offline parser switches absent | Matching declarations: rc1 | Mirror/source switches: rc0 |
| GitHub code-search control | Fresh absent token: 0, rc0 | `ServerOverloaded`: 45, rc0 |

These establish bounded findings, not universal absence.

### Tools and failed routes

**Actually ran:** `fnox`, mise, uv/Python, Git, `rg`, `gh api` REST/GraphQL, Codex help/version/features/plugin-help, Exa HTTP, Context7 `ctx7`, Firecrawl HTTP/CLI, Last30Days Python engine, and official web search/open.

**Skills applied or inspected:** `codex-sdlc-team`, OpenAI Docs, `research-sweep`, `codex-team-research`, Last30Days instructions, and research verification guidance.

**No connector/MCP tools or plugin installations ran.**

Other recorded failures:

- `graphify-health`: **rc3**, graph missing; source fallback used.
- Obsolete/guessed upstream paths: **HTTP404 / gh rc1**; current paths were discovered successfully.
- Missing local configuration/guessed paths: failed lookups, not capability-absence evidence.
- A Python inspection emitted a `SyntaxWarning`; a corrected read-only probe exited 0.
- Truncated release-list output was replaced by individual release retrievals.

Python, configuration, and documentation repository gates were **NOT RUN by instruction**; no gate exit codes are claimed.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — source, SDK, issues, PR searches, discussions, releases.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — incident, implementation, instructions, prior decisions.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline corpus and manifests.
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs) — locally inspected documentation clone.

No others were spawned.

### Specialists spawned:

- `sdlc-python-specialist` — `/root/python_research`
- `sdlc-config-specialist` — `/root/config_research`
- `sdlc-documentation-specialist` — `/root/documentation_research`

