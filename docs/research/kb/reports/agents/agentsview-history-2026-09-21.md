# AgentsView History Crawl — 2026-09-21

Task: search AgentsView archive for prior work on (A) codex access to
exa/last30days/context7/firecrawl, (B) herdr, (C) claudex-loop/chaseai-yt,
(D) codex CLI flag research, (E) fable-orchestrator removal/unification decisions.

Note: `--hybrid` was unavailable this run — embeddings index building (9% at
session start, per the daemon's own error message). All searches below use
`--fts` (prose) or plain `agentsview session search <term> --in tool_input,tool_result`
(identifiers), per the fallback instructions. The `messages` subcommand does not
accept `--exclude-session`; it was omitted there and results were filtered by eye.

## Control arm

`agentsview session search "fable-orchestrator" --fts --limit 8` → multiple hits
(e.g. `codex:019ff0d8-5f33-79a2-ac2c-d1054aa19736` ordinal 338-339, 2026-08-11,
discussing the plugin's cache/marketplace paths). FTS is live and discriminating —
a 0-result search below means absence, not a blind probe.

## Searches

- `fable-orchestrator` (fts) — control arm, hits confirmed.
- `last30days` / `exa` (`--in tool_input,tool_result`) — found the graphify-project
  codex session that lists all four research plugins.
- `codex mcp` (fts) — found the dotfiles session that measured codex's actual MCP
  registration state.
- `firecrawl` (`--in tool_input,tool_result`) — mostly self-session hits (forgot
  `--exclude-session` on that one call; filtered by eye), plus the same dotfiles
  session's findings.md append on the firecrawl gap.
- `codex MCP access` (fts) — turned up the codex-role/sandbox note (Topic D
  spillover) and an unrelated older session.
- `herdr` (fts) — found the graphify-project "communication substrate bakeoff"
  session (2026-09-13→15) that lists Herdr among live candidates.
- `claudex-loop` (`--in tool_input,tool_result`) and `chaseai-yt` (`--in
  tool_input,tool_result`) — found the dotfiles session where Ray cited the repo
  directly and a coordinator fetched and read it.
- `claudex` (fts) — corroborating hits in knowledge_base and dotfiles sessions.
- `dangerously-bypass-approvals-and-sandbox` (`--in tool_input,tool_result`) —
  found repeated `codex exec --help` dumps in the graphify-project session.
- `codex review` (fts) — found the knowledge-base session that measured `codex
  review` vs `codex exec review` and the hook-trust flag decision.
- `disable fable-orchestrator` / `unify codex offload` (fts) — weak/no direct
  hits on a full-plugin-removal decision; found a narrower "build our own
  advisor, disable theirs" decision scoped to `fable-advisor` only.

## Strong Matches

### Topic A — codex access to exa/last30days/context7/firecrawl

**`7f1c108c-d85d-49c5-a95c-e224c0b2bb2b` #474-570 (dotfiles, 2026-09-12)** — Ray's
explicit instruction (ordinal 474, verbatim): *"make sure codex subagents have
access to firecrawl, exa and context7 using codex's native plugins and should be
configured via .codex/config.toml and /verify that they are always available
going forward for any codex lane/subagent."*

Measured findings persisted to `findings.md` in that session (ordinal 497, 525):

| tool | Claude (dotfiles `.claude/settings.json`) | Codex (`codex mcp list`, `~/.codex/config.toml`) |
|---|---|---|
| context7 | ✅ `context7@context7-marketplace` | ✅ enabled, remote OAuth, `https://mcp.context7.com/mcp` |
| exa | ✅ `exa@exa` | ✅ enabled, remote OAuth, `https://mcp.exa.ai/mcp?client=agent-plugin` |
| last30days | ✅ `last30days@last30days-skill` | — (Claude skill only, no codex analogue) |
| **firecrawl** | ❌ NOT enabled in dotfiles (cache present) | ❌ plugin `enabled = true` at `~/.codex/config.toml:239-240`, but yields **no MCP server** |

⭐ Firecrawl is the one real gap, and it fails for **different reasons on each
side** — not enabled as a Claude plugin in dotfiles, and enabled as a codex
*plugin* that produces no MCP server (asymmetry vs context7/exa which are true
remote MCP servers).

⭐ A second axis, kept separate: a plugin being *enabled* gives **that session**
its skills; it does not put the plugin's **MCP tools** into a *subagent's* tool
pool. A general-purpose Claude subagent in the same session reported all three
MCP tools absent even with context7/exa enabled. So "available to codex" needs
three distinct facts: (a) plugin enabled, (b) MCP server registered in codex
config, (c) MCP tools actually present in a given lane's tool pool. Only (a) and
(b) are config-settable.

⭐ **Project `.codex/config.toml` IS read for `[mcp_servers]`** — measured with a
real control arm (ordinal 491, 497): appended a bogus `[mcp_servers.zxqprobe7]`
entry to the *project* config, ran `codex mcp list`, got PRESENT; arm B (a known
global server, `graphify`) also present, confirming the listing mechanism itself
works. Remote-server config shape is `url` + `auth`, not `command`/`args` (that's
the local-stdio-server shape).

⚠️ This proves `codex mcp list` **reads** project config — it does NOT prove a
running `codex exec` **connects** and exposes the tools to the model
(declared-vs-resolves, the same shape as the #354 defect class). The session's
own advisor-architect ("astra-program-architect") planned a work item, **#13 —
Codex MCP Access for Research Lanes**, with a two-half `/verify`: a static
`suites.toml` contract binding `[mcp_servers.*]` entries, plus a live probe that
runs `codex exec` and confirms in-session reachability with a **fresh** bogus
control name (`zxqprobe7` was burned by being published in the report).

**Report artifact still on disk**: `docs/research/kb/reports/agents/2026-09-12-astra-program-plan.md`
— section "WORK ITEM #13 — Codex MCP Access for Research Lanes (NEW)" (line ~305)
and "UPDATED — Work Item #13 (codex MCP) — Measured Asymmetry" (line ~374). This
plan item does **not** appear to have shipped as a concrete `.codex/config.toml`
diff or a `suites.toml` contract — `git log --all | grep -i firecrawl` in this
repo returns only an unrelated Claude-plugin-scope commit (`8d5265c2`), and there
is no tracked `.codex/config.toml` in the dotfiles repo (it's user-global at
`~/.codex/config.toml`, outside repo review). **Treat #13 as planned, measured,
but not verified-landed.**

**Separately**, `codex:01a09c55-c7c2-75c0-9e94-414372f69f96` (graphify project,
2026-09-13) is a live example of a codex lane (gpt-6-astra) actually **calling**
`mcp__exa__web_search_exa` and `mcp__context7__query_docs` mid-session (ordinals
14-20), plus reading `~/.codex/plugins/cache/last30days-skill/.../SKILL.md` —
concrete evidence that when the tools ARE registered, a codex lane can invoke
them, at least in that project's codex configuration.

### Topic B — herdr

**`codex:01a09d02-808a-74f2-a0a7-bc9f5728c2c4` (graphify project, spans
2026-09-13 23:24 → 2026-09-15 04:11)** — an extensive "grilling"-driven research
and bakeoff session titled around Claude↔Codex agent-communication substrates.
Herdr (`herdrdev/herdr`) is one of the named candidates from the start:

- Ordinal 63, 74, 102: repo-list probes explicitly enumerating `omnigent-ai/omnigent`,
  `herdrdev/herdr`, `block/buzz`, `stablyai/orca`, `traycerai/traycer` as
  candidates for a Claude↔Codex peer-messaging substrate.
- Ordinal 131 (first-tier decision): *"the first tier is now fixed: direct native
  sessions, Herdr, AgentBridge in safe preview mode, and Traycer."* Rationale
  given: *"Direct invocation preserves today's app; Herdr preserves terminal
  sessions; AgentBridge offers live injection; Traycer offers richer A2A by
  becoming the host."*
- Ordinal 135-137: **live local preflight of Herdr** — `command -v herdr &&
  herdr --version && herdr status --json` — result: *"Herdr 0.9.0 is running
  with a compatible local server and live-handoff support."*
- Ordinal 375-388: the session self-corrected after Ray flagged (*"still wrong,
  the first plan had tools like herdr, orca, etc"*) that a later plan replacement
  had silently dropped Herdr and other first-plan candidates. It recovered the
  original candidate ladder from the codex app's own thread history
  (`mcp__codex_app__read_thread`) and restored Herdr as a scored, first-tier
  candidate rather than letting later discoveries (`agmsg`, `hcom`, `Agent
  Message Queue`) silently replace it.
- Final restored ranking criteria (ordinal 386): delivery correctness 25%, native
  identity/wake 25%, safety/authority 20%, recovery/auditability 15%, maintenance
  evidence 10%, operational simplicity 5%; top five advance to a live
  subscription-authenticated bakeoff, with direct-native messaging as a mandatory
  control (not consuming a slot). The session references a linked issue "#672"
  for the deliverable, but that issue number does not resolve in either the
  dotfiles or graphify repo as checked here — **likely a knowledge-base or
  graphify-repo issue number not confirmed in this pass.**

No evidence found in this crawl of a **final** Herdr-vs-alternatives decision
being ratified/shipped — the session ends mid-bakeoff-redesign. Treat as an
open research thread, not a closed decision.

### Topic C — claudex-loop / chaseai-yt

**`7f1c108c-d85d-49c5-a95c-e224c0b2bb2b` #530-572 (dotfiles, 2026-09-12)** — Ray
directly cited it (ordinal 530, verbatim): *"use this as an example for tips and
tricks: https://github.com/chaseai-yt/claudex-loop or whatever knowledge-base
might be doing for codex fanning out — codex supports agent teams which we can
use. have codex astra adviser research this with a definitive answer that can be
cited. no guessing."*

The coordinator distrusted a sandboxed advisor lane's claims (it couldn't fetch
network/read source) and fetched+read the repo itself (ordinal 548-554):

- `chaseai-yt/claudex-loop`: ★1,802, Python, updated same day. Self-described as
  *"Claude Code skill: four-phase plan hardening (recon, interrogate, Codex
  adversarial review, cross-model build & inspection) — two AI models harden
  your plan before a line of code exists, then swap jobs to build it."*
- Ships **both** `.claude-plugin` and `.codex-plugin` directories.
- ⭐ **Definitive verdict (ordinal 554, 558)**: *"claudex-loop is NOT codex-native
  teams — it is EXTERNAL orchestration, and it is the pattern we already use."*
  Its `.codex-plugin` is Claude skills (`skills/codex-build`, `skills/codex-review`)
  that shell out to `codex` — the same architecture as this repo's own
  `codex-*-implementer`/`codex-*-reviewer` wrapper agents. The stated real
  contribution worth adopting is a discipline point: *"whoever built it never
  grades it"* — corroborating this repo's own cross-model-review rule (never let
  the implementer's model family also be the cold reviewer).
- No code/config was ported from claudex-loop in this session; it served as a
  design-pattern confirmation, not an adoption. Coordinator flagged one advisor
  claim as unsupported (`multi_agents_v2/spawn.rs:137` was report-sourced from a
  KB comment, not codex source — "discount one claim in the lane's report").

`codex:01a09803-*` and `105dc66e-*` (knowledge_base) sessions the same day show
parallel independent verification of the repo's existence and HEAD, consistent
with the dotfiles finding — no divergent conclusion found.

### Topic D — codex CLI flag research

Same `7f1c108c-...` session (#530-572) also settled several codex-flag/mechanism
questions while answering Ray's "codex supports agent teams" claim:

- ⭐ **`codex exec` has NO delegation flag** (0.154.0): grepped full `--help` for
  `agent|team|spawn|delegate|parallel|worker` — only singular-agent references (4
  hits; control arm confirms the grep discriminates).
- `codex agents` is a **TUI browser** over a shared local app-server daemon, not
  a spawner (`--remote`, `--enable <FEATURE>`, `--remote-auth-token-env`, `-c`).
- ⭐ **`features.multi_agent_v2` is REAL** — found by `strings -a` on the shipped
  0.154.0 binary (control arm run first: known string `danger-full-access` → 31
  hits, confirming the instrument works before trusting a feature-name grep).
  Full flag list surfaced: `features.apps`, `features.code_mode`,
  `features.code_mode_host`, `features.code_mode_only`,
  `features.exec_permission_approvals`, `features.multi_agent_v2`,
  `features.plugins`, `features.rollout_budget`, `features.token_budget`,
  `features.use_legacy_landlock`. All off by default (`~/.codex/config.toml:588`
  `[features]` empty).
- ⚠️ Even with `-c features.multi_agent_v2=true`, `codex exec --help` output is
  **unchanged** — the capability is compiled in but not reachable from `codex
  exec`; it lives behind the app-server daemon (consistent with `codex agents`
  browsing "sessions on the shared local app-server daemon").
- ⚠️⚠️ **`--strict-config` is USELESS as a feature-name-validity oracle** — both a
  real flag (`features.multi_agent_v2=true`) and a bogus one
  (`features.zqvbogus9=true`) return `rc=0`. It does not reject unknown
  `features.*` keys; a probe relying on it "validates → real" would be right only
  by luck. (`zqvbogus9` now burned as a control string.)
- **`--dangerously-bypass-approvals-and-sandbox`** (alias `--yolo`) confirmed
  present in `codex exec --help` across multiple sessions in `codex:01a09c55-...`
  (graphify project, 2026-09-13 through 15) — described there as *"Skip all
  confirmation prompts and exec[ute] every command without approval"*; one
  session explicitly advised *"avoid `--dangerously-bypass-approvals-and-sandbox`
  unless you are inside a dedicated sandbox VM."*

**`093aab0c-346e-4515-ab1b-872280983aea` (knowledge_base, 2026-09-02, ordinals
622-652)** — separate, earlier session that resolved `codex review` vs `codex
exec review` and the hook-trust flag by measurement (ordinal 628):
- **Both exist**: `codex --help` has a top-level `review` subcommand ("Run a code
  review non-interactive") AND `codex exec --help` documents `codex exec review`
  ("Run a code review against the current repository"). Ray had asserted both
  existed; the coordinator confirmed rather than assumed.
- Decision made via `/grilling`: *evaluate `codex exec review` once on a real
  diff and compare against the existing `codex-reviewer` subagent before
  adopting* — not immediate replacement.
- ⭐ **`--dangerously-bypass-hook-trust` is load-bearing, not optional**: a codex
  hook (`pre_tool_use`/`post_tool_use`) is **skipped until trusted**, and trust
  is keyed to the hook's hash. Measured: 3 trusted `pre_tool_use` entries for
  that repo, 0 for `post_tool_use`. Two-armed proof: with the flag, a lane got
  its ty diagnostic; without it, "I received no feedback after the edit". This
  directly explains a prior false belief in the same session — *"our guard stack
  already runs in every codex lane"* was asserted from reading
  `.codex/hooks.json` rather than from running it, and was wrong.
- A GH issue was filed at the end of this session — "Phase U — stop going in
  circles: make the claude/codex/graphify setup observable, enforced, and owned
  by tasks" — in the **knowledge-base** repo, capturing this and other
  read-vs-run failures as a durable inventory requirement. Not verified whether
  it is still open (out of scope for this dotfiles-focused crawl; flagged as a
  gap below).
- The session also settled a mise-task-shape decision for codex invocation: *"A
  mise task that owns the flags (Recommended): `mise run kb-codex -- "<prompt>"`
  wrapping a kb_setup module that always passes the correct flags for the lane
  type"* — consistent with this repo's `mise-tasks-only.md` and
  `ai-cli-invocation.md` doctrine.

### Topic E — fable-orchestrator plugin removal/unification

No direct hit found for a decision to remove or fully replace the
fable-orchestrator plugin, or to unify all codex offload under one skill, in
either FTS probe (`disable fable-orchestrator`, `unify codex offload`).

**Narrower, related decision found** — `093aab0c-346e-4515-ab1b-872280983aea`
(knowledge_base, 2026-09-02, ordinal 624): a `/grilling` round posed *"On
fable-advisor you said two different things — disable and tune it, and
separately build our own natively. Which?"* Ray's selection (recommended option,
marked chosen): **"Build ours, disable theirs"** — *"A project-owned advisor
agent in `.claude/agents/`, informed by what fable-advisor does well, tuned to
this repo. Then disable the plugin so there's one advisor, not three competing
ones... We already have `kb-advisor` and `kb-codex-advisor` — this likely means
fixing those rather than adding a fourth."* The alternative explicitly rejected
in the option text: *"Tune the plugin, don't replace it... we can't edit a
plugin's agent definition without writing to `~/.claude`, which do-not.md #11
forbids."*

This is scoped to the **`fable-advisor` sub-agent specifically**, in the
**knowledge-base** repo, not a whole-plugin removal in dotfiles. It is
consistent with — but narrower than — the routing doctrine already recorded in
this repo's `.claude/CLAUDE.md` (`codex-{sol,astra}-advisor` as the actual
consult path today), but this crawl found no session where the **dotfiles**
fable-orchestrator plugin itself was ordered removed or unified.

## Synthesis

1. **Topic A** has the strongest, most actionable evidence: Ray gave an explicit
   instruction (2026-09-12) to wire firecrawl/exa/context7 into codex via
   `.codex/config.toml`, the gap was measured precisely (context7+exa already
   work as remote-OAuth MCP servers; firecrawl's codex *plugin* is enabled but
   produces no MCP server), and a two-part `/verify` design (static contract +
   live `codex exec` reachability probe) was specified but — as far as this
   crawl can tell from `git log` and the absence of a tracked `.codex/config.toml`
   — not yet landed as a repo-owned diff. Worth checking with the operator
   whether this was done by hand outside version control, or is still open.
2. **Topic B (herdr)** was one of ~8-10 candidates in an ongoing, self-correcting
   "communication substrate bakeoff" for Claude↔Codex peer messaging, evaluated
   live (v0.9.0, working local server + handoff) and kept in the first tier
   alongside AgentBridge and Traycer. The research explicitly has not reached a
   final decision as of the latest session found (2026-09-15); it stops mid
   re-rank with a top-five live-bakeoff plan.
3. **Topic C (claudex-loop)** got a clean, sourced answer the same day Ray asked:
   it's external Claude-skill-shells-out-to-codex orchestration, not codex-native
   teams — validating (not replacing) this repo's existing wrapper-agent pattern.
   The main value extracted was the discipline point (don't let a model grade its
   own work).
4. **Topic D** produced the most durable, reusable facts: `codex exec` has no
   delegation flag; `features.multi_agent_v2` exists but is unreachable from
   `codex exec` (lives behind the app-server daemon); `--strict-config` cannot be
   used to validate feature names; both `codex review` and `codex exec review`
   exist; and `--dangerously-bypass-hook-trust` is required for codex hooks to
   fire at all pre-trust, which had silently neutered a hook in a prior session.
5. **Topic E** turned up only a scoped precedent (replace `fable-advisor` with a
   project-owned advisor, disable the plugin's) in a **different repo**
   (knowledge-base), not a dotfiles-wide fable-orchestrator removal decision.

## Gaps

- **Topic A**: whether Work Item #13 (codex MCP access for firecrawl/exa/context7)
  was ever actually shipped as a `.codex/config.toml` diff + `suites.toml`
  contract could not be confirmed — no matching commit found in `git log --all`
  for dotfiles, and `.codex/config.toml` here is untracked/user-global. Worth a
  direct check of the CURRENT `~/.codex/config.toml` state (not done in this
  crawl — out of repo scope) and whether GH issue #13-equivalent exists.
- **Topic B**: no session found reaching a *final* herdr-vs-alternatives verdict;
  the referenced tracking issue "#672" did not resolve in dotfiles or graphify as
  checked and may live in knowledge-base or under a different number by now
  (issues renumber/get superseded).
- **Topic D**: did not probe `--ephemeral` or plain `-s`/`--sandbox` semantics
  directly beyond what's already recorded in this repo's own
  `.claude/rules/ai-cli-invocation.md` (which already documents the
  `--ephemeral` collab-spawn conflict) — no new AgentsView evidence surfaced
  beyond what's already codified there.
- **Topic E**: no direct evidence found (in the 2 probes budgeted) of a decision
  to remove or unify the whole fable-orchestrator plugin in dotfiles; only the
  narrower, KB-repo-scoped fable-advisor replacement. A hybrid-search rerun once
  the embeddings index finishes building might surface prose-only discussion
  this FTS-only pass missed (FTS matches literal terms; "should we drop
  fable-orchestrator" phrased differently would not match `"disable
  fable-orchestrator"` or `"unify codex offload"`).
- Embeddings/hybrid search was unavailable the entire session (index building at
  9% at start); all results here are FTS/plain-search only, which is more
  literal-term-sensitive than semantic search would have been.

## GitHub repos touched

- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — read directly by a prior coordinator session (repo view + tree fetch) to determine its mechanism (Topic C).
- [herdrdev/herdr](https://github.com/herdrdev/herdr) — candidate in the communication-substrate bakeoff, live-preflighted locally (Topic B).
- [raysonmeng/agent-bridge](https://github.com/raysonmeng/agent-bridge) — competing candidate in the same bakeoff.
- [traycerai/traycer](https://github.com/traycerai/traycer) — competing candidate, referenced alongside herdr.
- [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent), [stablyai/orca](https://github.com/stablyai/orca), [block/buzz](https://github.com/block/buzz) — escalation/held candidates in the same bakeoff.
- [WebisityStudio/claude-codex-mcp-bridge](https://github.com/WebisityStudio/claude-codex-mcp-bridge) — retained as a receipt-semantics design reference; repo health (stars, CI) was checked via `gh api`.
- [fujibee/agmsg](https://github.com/fujibee/agmsg), [aannoo/hcom](https://github.com/aannoo/hcom), [avivsinai/agent-message-queue](https://github.com/avivsinai/agent-message-queue), [YuanpingSong/embassy](https://github.com/YuanpingSong/embassy), [dataforxyz/agent-intercom-claude](https://github.com/dataforxyz/agent-intercom-claude), [Co-Messi/agent-peers-mcp](https://github.com/Co-Messi/agent-peers-mcp) — additional candidates discovered later in the same bakeoff research, not independently verified in this crawl.
- [openai/codex](https://github.com/openai/codex) — its own source (`codex-rs/config/src/config_toml.rs`, `codex-rs/core/src/agent/role.rs`) was read by a prior session to settle role-level sandbox/MCP behavior.
