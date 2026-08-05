# Market Scan — Multi-Agent Team Frameworks for Claude Code

**Agent:** market-scan · **Measured:** 2026-08-04 (UTC) · **Status:** COMPLETE

> **Headline:** 2,298 marketplace plugins, ~58 generic agent-team frameworks,
> and **not one of the 10 leading candidates uses Claude Code's dynamic-workflow
> primitive** — the one native mechanism that actually gives a reusable,
> DAG-parallelized, per-stage-model-routable team. See **§6**.

Scope: an independent sweep for existing multi-agent-team frameworks for Claude
Code, EXCLUDING those already covered by sibling agents (oh-my-claudecode,
cc-native, claude-code-harness, claude-code-kit, conductor-skills,
claude-self-reflect, claude-relay, claude-code-gauntlet, cc10x, cc-dm,
openai/symphony, stokowski, hatice, phonyhuman, itervox).

Goal being served: *a reusable, self-improving team of ~9 roles,
DAG-parallelized, able to offload work to a Codex CLI subscription.*

---

## 1. Official community marketplace enumeration

Source: `https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json`
— HTTP 200, 1,579,090 bytes, fetched 2026-08-04. Saved to `.agent/kb/raw/marketplace.json`.

Top-level keys: `name`, `owner`, `plugins`, `renames`.

| Measure | Count | Ratio |
|---|---|---|
| **Total plugins enumerated** | **2,298** | 100% |
| Broad keyword match (orchestrat·multi-agent·subagent·agent-team·swarm·squad·hive·crew·choreograph·conductor·ensemble·council·delegat·coordinat·parallel·fan-out·DAG·handoff·supervisor) | **326** | 14.2% |
| Strong match (multi-agent · subagent · agent team · swarm · squad · hivemind · agent crew · choreograph · conductor · orchestrat) | **216** | 9.4% |
| Hand-classified as a **generic** agent-team / orchestration framework (excludes domain plugins that merely use subagents — SEO audits, patent workflows, supply chain, chess coaching, etc.) | **~58** | 2.5% |

The enumeration was done by flattening every entry (`jq '.plugins[]'`) and
filtering — **not** by searching for names I expected. Full flattened corpus:
`.agent/kb/raw/marketplace-flat.tsv` (2,298 rows). Note `.source` is
polymorphic — usually an object with `.url`, sometimes a bare `owner/repo`
string — so a naive `.source.url` jq expression **errors out mid-stream**
(observed at byte offset 24080); the flattener handles both.

### 1a. Classification of the 216 strong matches

Five buckets. A plugin can sit in more than one; assignment is by primary claim.

**A. Generic multi-agent team / role frameworks (the direct competitors):**
`10x-team` (12 named roles as skills) · `agentic-swe` (135+ specialist
subagents) · `ai-team-os` (25 agents, 79 MCP tools, persistent team state) ·
`atelier` · `atelier-pipeline` (11 named personas) · `attacca` (7 specialists) ·
`blueprint-sdlc` (27 commands, parallel subagents) · `claude-alloy` (11 agents +
11 hooks) · `closedloop` · `dev-forge` (SQLite-backed, sprint contracts, bug
council) · `dev-squad` · `dominion-flow` (51 agents / 7 departments) ·
`eight-eyes` (8 hook-enforced roles) · `ensembra` (6 specialists + scribe) ·
`fellowship` (LotR: Gandalf + 9 companions, persistent memory) · `guild`
(self-evolving specialist team) · `harness` · `harness-architect` ·
`harness-boot` · `hive` (stigmergy/pheromone swarm) · `just-ship` (8 agents) ·
`karimo` · `larch` · `launchpad` (36 sub-agents) · `maister` (23 agents) ·
`mash` (4 personas) · `mexus-agent-team` · `mosaic` · `neko-gundan`
(Opus general → Sonnet manager → Sonnet workers) · `nxtg-forge` (33 agents;
invariant `verifier.agent != task.agent`) · `orchestrator` · 
`orchestrator-workflow-plugin` · `session-orchestration` ·
`session-orchestrator` (5 typed waves) · `shipwright` · `stackpilot` ·
`statsclaw` (**9 agents**: leader, planner, builder, tester, scriber, simulator,
distiller, reviewer, shipper) · `superpipelines` · `trinity` (Planner→Generator→
Evaluator in a worktree) · `tycono` · `virtual-team` (12 specialists) ·
`waterfall` (PM/OR/PO/TL/DV/RV/QA/DS) · `wmux-orchestrator` (dependency-aware
waves) · `wrightward` (multi-session write-conflict blocking + peer message bus).

**B. Cross-CLI / model-offload (relevant to the Codex-subscription goal):**
`claude-codex-loop` · `llm-gateway` · `nexus-agents` · `octo` (8 providers,
75% consensus gates) · `phone-a-friend` / `phone-a-friend-paf` · `tap` ·
`debate` · `khaki-sketcher` · `claude-cursor-orchestration` ·
`agent-discussion` · `mexus-agent-team` (Claude Code **and** Codex) ·
`superpipelines` (Claude Code, Cursor, Codex, OpenCode).

**C. Self-improvement / durable memory:** `compounded` (trust-gradient: skills
earn autonomy) · `guild` · `hive` (learns across sessions) · `sindri`
(overnight experiment loop, keeps wins as commits) · `goalkeeper`
(contract-driven, judge subagent) · `hipocampus` · `mind-glaive` ·
`mindwright` · `hivemind` / `deeplake-hivemind` · `stash` · `scaffold`
(Obsidian-backed) · `rpm` · `pskoett-ai-skills` (self-improving skill pipeline
with an explicit `agent-teams` skill).

**D. Multi-agent REVIEW only (narrower than a team):** `audit-project` (spawns
up to 10 specialist reviewers) · `audit-suite` (10 lenses) ·
`claude-deep-review` · `claude-review-loop` · `review-all` · `qa-orchestra`
(10 QA agents) · `challenger` (Skeptic/Sentinel/Architect/Pragmatist) ·
`devils-advocate` · `eight-eyes`.

**E. Domain plugins that happen to use subagents (NOT competitors):**
`claude-seo` (11 parallel SEO subagents) · `arcdeck` (13 agents for slide
decks) · `architecture-studio` (AEC) · `memoriant-patent-skills` ·
`sciqlab-supply-chain` · `chess-coach-ai` · `dj-claude` · `crowdcast` ·
`qlik-agents` · `salesforce-claude-code` · `viral-launch-pipeline` (21 agents) ·
`train-prep` · `local-seo-audit-system` · `ololand-dd` · `mmpm-cognitive-os` ·
`usap-skills` · `plausible-ba` · `the-pragmatic-pm-toolkit` · `pm-augmente` ·
`get-design-done` · `csitrep-generator` · ~60 more.

That ratio is the story: **2,298 plugins, 216 that mention agent
orchestration at all, ~58 that are actually generic agent-team frameworks, and
essentially all of them are one-person weekend projects.** See the maintenance
table below.

### 1b. Maintenance measurement (49 shortlisted repos, `gh api repos/<r>`, 2026-08-04)

| Repo | Stars | Last push | Alive |
|---|---:|---|---|
| revfactory/harness | **8,601** | 2026-07-24 | yes |
| nyldn/claude-octopus (`octo`) | **3,923** | 2026-08-04 | yes |
| CronusL-1141/AI-company (`ai-team-os`) | 334 | 2026-08-03 | yes |
| opensesh/KARIMO | 273 | 2026-05-11 | stale ~3mo |
| SkillPanel/maister | 194 | 2026-08-03 | yes |
| closedloop-ai/claude-plugins | 102 | 2026-08-04 | yes |
| statsclaw/statsclaw | 89 | 2026-07-22 | yes |
| ThierryN/fire-flow (`dominion-flow`) | 77 | 2026-06-18 | slowing |
| seongsu-kang/tycono | 50 | 2026-06-29 | slowing |
| Kanevry/session-orchestrator | 50 | 2026-08-04 | yes |
| robertsfeir/atelier-pipeline | 25 | 2026-06-17 | slowing |
| yves-s/just-ship | 24 | 2026-05-04 | stale ~3mo |
| nexus-substrate/nexus-agents ¹ | 17 | 2026-08-03 | yes |
| bonfire-systems/goalkeeper ¹ | 12 | 2026-06-22 | slowing |
| yofine/mexus-agent-team | 11 | 2026-06-04 | slowing |
| verivus-oss/llm-cli-gateway | 10 | 2026-08-04 | yes |
| Jaan-Mustafa/10x-Team | 10 | 2026-07-03 | yes |
| amirlehmam/wmux-orchestrator | 10 | 2026-07-17 | yes |
| lookatitude/guild | 6 | 2026-08-04 | yes |
| nxtg-ai/forge-plugin | 5 | 2026-08-04 | yes |
| ankitkr3/compounded | 5 | 2026-06-22 | slowing |
| gustavo-meilus/superpipelines | 4 | 2026-07-15 | yes |
| agentic-swe/agentic-swe ¹ | 3 | 2026-05-17 | stale |
| agent-sh/debate | 3 | 2026-07-22 | yes |
| mgallet92i/waterfall | 2 | 2026-07-16 | yes |
| AgentBuildersApp/eight-eyes | 2 | 2026-08-02 | yes |
| adihebbalae/Attacca | 2 | 2026-08-04 | yes |
| factorshin/mosaic | 2 | 2026-04-06 | stale ~4mo |
| dudgns0908/atelier | 2 | 2026-05-13 | stale |
| dmarchevsky/mash | 2 | 2026-05-22 | stale |
| cyrusxyl/agent-discussion | 2 | 2026-03-04 | stale ~5mo |
| OAI-Labs/vibe-flow | 1 | 2026-07-23 | yes |
| builtform/launchpad | 1 | 2026-08-03 | yes |
| KarolusD/fellowship | 1 | 2026-06-12 | slowing |
| HotRedMat/ensembra | 1 | 2026-04-24 | stale |
| aliksir/neko-gundan | 1 | 2026-07-24 | yes |
| yjn279/trinity | 0 | 2026-08-01 | yes |
| yn01/claude-plugins (`dev-forge`) | 0 | 2026-07-05 | slowing |
| CipherandRow/claude-hive-plugin | 0 | 2026-07-24 | yes |
| 9aoyang/stackpilot | 0 | 2026-07-09 | yes |
| 4KMetrics/sindri | 0 | 2026-06-27 | slowing |
| Apoorve8055/virtual-team | 0 | 2026-05-17 | stale |
| DuckrOverload/duckr-plugins | 0 | 2026-04-03 | stale |
| amitvijapur/orchestrator | 0 | 2026-04-17 | stale |
| skaisser/blueprint-plugin | 0 | 2026-03-27 | stale |
| Whisker17/claude-codex-loop | 0 | 2026-03-31 | stale ~4mo |
| **OMARVII/claude-alloy** | — | — | **404 — repo gone** |
| **KhakiSkech/KhakiSketcher** | — | — | **404 — repo gone** |
| **Joys-Dawn/toolwright** (`wrightward`) | — | — | **404 — repo gone** |

¹ GitHub redirected the marketplace-declared owner to a new one, i.e. the
project was transferred (nexus-agents → `nexus-substrate`, goalkeeper →
`bonfire-systems`, agentic-swe → its own org). None were archived.

**Finding: the official marketplace lists dead repos.** Three of 49 shortlisted
entries 404. Control arm run in the same command shape: `anthropics/claude-code`
→ 140,235 stars (probe sees), a freshly-invented bogus name → 404 (probe
discriminates). So those three are genuinely gone while still installable-by-
listing. Do not treat marketplace presence as evidence a project exists.

**Finding: the star distribution is a cliff.** Two projects above 3,000 stars,
then a 10× gap to 334, then everything else under 100. 30 of 49 are under 10
stars. There is no consolidated winner in this category — the field is
fragmented across ~58 near-identical solo projects.

## 2. Search beyond the marketplace

Twelve `gh search repos` queries, distinct spellings, `--sort stars`. Which
query found what is recorded, because the spellings do **not** overlap: the
single highest-value finding below (`Agent Teams` as a native Claude Code
feature with its own ecosystem) appears under `agent team` / `agent teams` and
is **completely invisible** to `multi-agent orchestration`, `swarm` and
`subagent orchestration`.

| Query | Rows | What it uniquely surfaced |
|---|---:|---|
| `claude code agent team` | 12+ | **the native Agent-Teams ecosystem** — clawport-ui, HydraTeams, Claude-Agent-Team-Manager, aws-samples reference impl, claude-teams-brain, zellij-claude-teams, kkirikkiri |
| `agent teams claude` | 10 | victordelrosal field manual, endorphin-ai/claude-code-teams, jagatsastry skills |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | 8 | **the evaluation repos** — ShawhinT/subagents-vs-teams, kar-ganap/ate-series; plus team-forge, AntAI GUI, kompallik docs |
| `claude code multi-agent orchestration` | 12 | claude-corps, Graybark-workflow, agentfiles, MeriaApp/conductor, AgentCall |
| `claude code subagent orchestration` | 6 | sdd-autopilot, recursive-claude-code-subagents, brenokern/dev-team-orchestration |
| `claude code swarm` | 12 | clnode (hooks + DuckDB coordination), sybra, ekamphuis82/claude-code-swarm, fullstack-swarm |
| `claude agent squad` | 4 | a1-ceo/claude-agent-squad and **M-yer/claude-agent-squad-codex** |
| `claude code orchestrator codex` | 5 | **tinytandem**, cc-claude-codex, orchestrate-skill, cross-model-code-review-skill |
| `claude code agent teams DAG` | **0** | — |
| `claude code parallel agents worktree` | **0** | — |

**Control arm for the two zero-result queries** (invented fresh for this run,
never previously written to disk): `quixotic-marmalade-7731` → 0 rows, same
command shape. Queries in the same shape returned 4–12 rows. So the probe
discriminates and those two zeros are real negatives *for those exact
phrasings* — not evidence that DAG-shaped or worktree-parallel projects don't
exist (they do; `wmux-orchestrator`, `stackpilot` and `trinity` from §1 are
exactly that, found under different words). This is the token-spelling trap in
miniature.

### 2a. The finding that matters most: Agent Teams is a NATIVE feature with its own ecosystem

`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is a first-class Claude Code mode, and
a whole tier of projects builds **on** it rather than reimplementing
orchestration. That is a different — and cheaper — architectural position than
the marketplace's 58 hand-rolled frameworks.

| Repo | Stars | Last push | What it is |
|---|---:|---|---|
| [JohnRiceML/clawport-ui](https://github.com/JohnRiceML/clawport-ui) | 899 | 2026-03-24 | Command-center UI for Claude Code agent teams (built on OpenClaw) |
| [DatafyingTech/Claude-Agent-Team-Manager](https://github.com/DatafyingTech/Claude-Agent-Team-Manager) | 142 | 2026-03-11 | Visual org-chart desktop app for managing agent teams + skills |
| [Pickle-Pixel/HydraTeams](https://github.com/Pickle-Pixel/HydraTeams) | 68 | 2026-02-08 | **Translation proxy making Agent Teams model-agnostic — any model as a teammate (GPT, Gemini, Ollama)** |
| [aws-samples/sample-claude-code-agent-team](https://github.com/aws-samples/sample-claude-code-agent-team) | 47 | **2026-07-29** | AWS reference implementation: specialist agents collaborating through a spec-driven process |
| [stanislc/zellij-claude-teams](https://github.com/stanislc/zellij-claude-teams) | 38 | 2026-07-14 | tmux→zellij shim so Agent Teams runs under zellij |
| [fivetaku/kkirikkiri](https://github.com/fivetaku/kkirikkiri) | 38 | 2026-07-06 | Natural-language team builder — describe a team in one sentence |
| [panaversity/claude-code-agent-teams-exercises](https://github.com/panaversity/claude-code-agent-teams-exercises) | 32 | 2026-02-11 | 6 exercises + 2 capstones on team creation and task coordination |
| [Gr122lyBr/claude-teams-brain](https://github.com/Gr122lyBr/claude-teams-brain) | 27 | 2026-03-15 | **Memory for agent teams — auto-injects role-specific context into every new teammate** |
| [ShawhinT/subagents-vs-teams](https://github.com/ShawhinT/subagents-vs-teams) | 10 | 2026-03-01 | **Benchmark comparing subagents vs. Agent Teams performance** |
| [shirleyfuxw/team-forge](https://github.com/shirleyfuxw/team-forge) | 1 | **2026-08-03** | **Meta-extension that auto-generates project-specific agent teams; 5-role work/verify coverage** |
| [kar-ganap/ate-series](https://github.com/kar-ganap/ate-series) | 0 | 2026-06-08 | "Agent Teams Eval" — teams vs. subagents across bug-fixing and feature work |
| [human-corey/AntAI](https://github.com/human-corey/AntAI) | 0 | 2026-02-25 | Open-source GUI canvas to orchestrate/monitor agent teams |
| [victordelrosal/agent-teams-claude-code](https://github.com/victordelrosal/agent-teams-claude-code) | 0 | 2026-02-26 | 28-file field manual for multi-agent systems in Claude Code, "written FOR AI instances" |

⚠️ **Note the dates.** Of the 13, seven last pushed in Feb–March 2026 and have
not moved since — including the two most-starred (clawport-ui 899★, frozen
2026-03-24; HydraTeams 68★, frozen 2026-02-08). Only four are current
(aws-samples 07-29, zellij shim 07-14, team-forge 08-03, kkirikkiri 07-06).
That is a **hype wave that crested in Feb–March 2026 and largely receded** —
consistent with the practitioner sentiment in §3.

### 2b. Codex-offload candidates (directly relevant to the subscription goal)

| Repo | Stars | Last push | What it does |
|---|---:|---|---|
| [Pickle-Pixel/HydraTeams](https://github.com/Pickle-Pixel/HydraTeams) | 68 | 2026-02-08 | Proxy that lets **any** model be a native Agent-Teams teammate — the cleanest architectural answer to "offload to Codex" (but frozen since Feb) |
| [leyuan0602-glitch/cc-claude-codex](https://github.com/leyuan0602-glitch/cc-claude-codex) | 9 | 2026-03-02 | Skill letting Claude Code orchestrate Codex via markdown relay files |
| [craigkitterman/cross-model-code-review-skill](https://github.com/craigkitterman/cross-model-code-review-skill) | 4 | 2026-03-17 | Multi-model consensus review across Codex + Gemini + any AI CLI |
| [a1-ceo/claude-agent-squad](https://github.com/a1-ceo/claude-agent-squad) | 2 | 2026-07-21 | Nested sub-agent squad — one orchestrator fans out to planner/builder/reviewer |
| [M-yer/claude-agent-squad-codex](https://github.com/M-yer/claude-agent-squad-codex) | 0 | 2026-07-21 | **Fork of the above where every sub-agent forwards its work to the Codex CLI instead of Claude** — the exact experiment, run by someone else |
| [chorious/AgentCall](https://github.com/chorious/AgentCall) | 1 | 2026-06-26 | Codex + Claude Code multi-agent orchestration workspace |
| [jonathanavni/tinytandem](https://github.com/jonathanavni/tinytandem) | 0 | 2026-06-30 | Minimalist two-agent harness: Claude orchestrates, Codex implements **and adversarially reviews** |
| [ZaMpAdAKiNg/orchestrate-skill](https://github.com/ZaMpAdAKiNg/orchestrate-skill) | 0 | 2026-07-10 | One skill exposing `/orchestrate` in Claude Code and `$orchestrate` in Codex — same control plane both sides |
| [giwarb/ps-edge-cli](https://github.com/giwarb/ps-edge-cli) | 0 | 2026-07-04 | A shipped CLI built with Claude-orchestrator + Codex-implementer, i.e. evidence the pattern produces artifacts |

Every one of these is a solo project under 10 stars except HydraTeams. **There
is no maintained, popular, general-purpose Claude↔Codex team framework** — the
pattern is widely reinvented and nowhere consolidated.

### 2c. Other notable finds

- [SierraDevsec/clnode](https://github.com/SierraDevsec/clnode) — 25★, 2026-02-06 — swarm coordination via **hooks + DuckDB**; the only project observed using a real database as the coordination substrate rather than markdown files.
- [Automaat/sybra](https://github.com/Automaat/sybra) — 7★, **2026-08-04** — local agent orchestrator for Claude Code swarms (Wails/Go/Svelte); actively developed today.
- [josephneumann/claude-corps](https://github.com/josephneumann/claude-corps) — 4★, 2026-04-01 — multi-agent orchestration with **parallel git worktrees** and autonomous task loops.
- [ekamphuis82/claude-code-swarm](https://github.com/ekamphuis82/claude-code-swarm) — 0★, 2026-07-26 — "deterministic, director-led swarm — parallel specialist agents, adversarial verification".
- [brenokern/dev-team-orchestration](https://github.com/brenokern/dev-team-orchestration) — 0★, **2026-08-04** — subagent team that takes a written plan and ships data→backend→frontend.
- [Shiyao-Huang/aids-tools](https://github.com/Shiyao-Huang/aids-tools) — 1★, 2026-05-19 — identity-aware trace & rating **across** Claude Code / Codex / Bash agents; the observability layer nobody else builds.
- [rubenzarroca/sdd-autopilot](https://github.com/rubenzarroca/sdd-autopilot) — 4★, 2026-05-09 — zero-stop spec→PR pipeline with metacognition scoring.

## 3. /last30days — practitioner sentiment (window 2026-07-05 → 2026-08-04)

🌐 last30days v3.18.4 · synced 2026-08-04

Run: `last30days "Claude Code agent teams and subagent orchestration"` with a
4-subquery plan (`primary` / `orchestration` / `abandoned` / `frameworks`),
`--x-handle=claudeai --x-related=alexalbert__,AnthropicAI`,
`--dedicated-subreddits=ClaudeAI,ClaudeCode`,
`--subreddits=ChatGPTCoding,LocalLLaMA,AI_Agents,singularity,PromptEngineering`,
`--github-repo=anthropics/claude-code`. 79.5s, 75 evidence items across 9 live
sources. Raw: `~/Documents/Last30Days/claude-code-agent-teams-and-subagent-orchestration-raw-v3.md`.

⚠️ **Partial coverage — do not read as silence.** Web grounding returned HTTP
422, TikTok and Instagram both returned **HTTP 402 Payment Required** (the
ScrapeCreators quota is exhausted). Those three sources were never asked, so
"nothing on TikTok" is unsupported. Reddit, X, HN, YouTube, Bluesky, GitHub,
Digg, arXiv and Techmeme all completed.

### What practitioners actually report

**The cost multiplier is the dominant complaint, and it is now quantified.**
[CloudZero](https://www.cloudzero.com/blog/claude-code-agents/) measures
multi-agent workflows at roughly **4-7× the tokens of a single-agent session**,
and Agent Teams specifically at **~15× standard usage**, because every
inter-agent message is a full model round trip. Subagents are the token-cheap
tier (they run inside the parent session and only report back);
Agent Teams are the capable-and-expensive tier.
[getpushtoprod](https://getpushtoprod.substack.com/p/30-tips-for-claude-code-agent-teams)
puts teams at ~7× a single session in plan mode and argues the productivity
gain still wins **for the right tasks** — which is the whole disagreement.

**The sharpest critique in the window says the parallelism usually isn't
there.** [@liustack](https://x.com/liustack/status/2082576866083536983)
(2026-07-29) writes that Claude Code and Codex both have teams, that Claude
Code's implementation uses dynamic workflow planning specifically to try to
dissolve communication cost, and that someone who tested it found the agents
**sent an enormous volume of useless inter-agent communication — all of it
tokens**. Then the load-bearing line: 按 google 的评测它们这些 teams 架构大多
数时候都是无效的，只是偶尔在高并行任务中效果比较好。可现实世界的任务大多数都不
具备很高的并行性 — *per Google's evaluation these team architectures are
ineffective most of the time, only occasionally good on highly-parallel tasks;
but most real-world tasks do not have high parallelism.* (Single-source, 1
reply — weigh accordingly, and the Google evaluation it cites is
**UNVERIFIED**, not traced to a paper in this run.)

**The observability objection, from the highest-engagement item in the
window.** [IndyDevDan](https://www.youtube.com/watch?v=WAFUMBLOjHo)
(2026-07-06, 32,449 views / 1,015 likes): *"An agent you can't SEE is an agent
you can't improve. Spinning up 20 agents in a loop and looking the other way
isn't agentic engineering, it's gambling with tokens, it's vibe coding."*
This is the single most-engaged piece of commentary the sweep found, and it is
a critique of exactly the "fan out 9 roles" shape.

**Academic work has already catalogued the failure modes of native Agent
Teams.** [arXiv:2607.22917v2](https://arxiv.org/abs/2607.22917v2), *"Agent Team
Work Zone: An Automated, Persistent Workspace for Long-Lived Claude Code Agent
Teams"* (Shouren Wang, submitted 2026-07-24, revised 07-30) names four:

1. **Irrecoverable agent teams** — working state is lost when processes end and cannot be resumed.
2. **Compaction erodes working detail** — conversation summaries lose precise working information.
3. **Agentic "technical debt"** — decisions and operations get trapped in compacted chats.
4. **Heavy prompt writing** — task assignment means repeatedly drafting long prompts.

Its remedy (ATWZ) is a **filesystem-based operations layer**: per-agent
"workstation" directories, periodic backups so knowledge survives compaction,
single-command team restoration after process death, and inter-agent document
sharing to cut prompt-composition burden. **Every one of those four is a
requirement for a "reusable, self-improving team" and none is solved by the
native feature.**

**The cross-CLI pattern is being run in production by individuals, today.**
[@GrimGreysson](https://x.com/GrimGreysson/status/2083704315320119402)
(2026-08-01) describes the exact architecture in the goal: *"run a session in
Claude Code and shelling out to other harnesses like Codex or Cursor-Agent or
OpenCode for adversarial review before executing with fanned-out subagents
using the teams feature before and dynamic workflows when it became
available."* Low engagement (2 likes) — it is a practitioner note, not a
consensus.

**The framing that is winning is "Claude Code is a 7-layer framework, not a
chat."** [@chiebukuroai.bsky.social](https://bsky.app/profile/chiebukuroai.bsky.social/post/3mr2ofemfis2b)
(2026-07-20) enumerates the layers as **CLAUDE.md, Skills, Subagents, Agent
Teams, Hooks, MCP, Plugins** and reports a claimed 700× spread in code output
between employees at one dev shop (that multiplier is a third-party claim,
**UNVERIFIED**). [@HeyAnjula](https://x.com/HeyAnjula/status/2083780677338902964)
(2026-08-02, 358 likes / 100 rt) and
[@RodmanAi](https://x.com/RodmanAi/status/2083936025731314057) (2026-08-02)
push the same thesis independently — that the architecture layers, not the
prompts, are what make agents survive outside a demo.

**Team standards as skills is an active thread right now.**
[tikalk/adlc-team-skills](https://github.com/tikalk/adlc-team-skills) — "Agent
skills that bring team coding standards to Claude Code **and Codex**" — hit
Hacker News on 2026-08-04 with 72 points and 39 comments. Same day as this
scan; it is the freshest signal in the window and it is cross-CLI by design.

**Also observed:** setups silently degrade and are hard to test —
[@ranjankumar](https://x.com/ranjankumar/status/2083902962196267307)
(2026-08-02) reports a Claude Code regression between March and April 2026 that
**skill evals could not catch**. That is a direct hit on the "self-improving"
half of the goal: the improvement loop needs an eval that can see the
regression, and skill-level evals demonstrably could not.

### Engine footer (verbatim)

```
✅ All agents reported back!
├─ 🟠 Reddit: 10 threads │ 2,335 upvotes │ 490 comments
├─ 🔵 X: 20 posts │ 24,310 likes │ 3,316 reposts
├─ 🔴 YouTube: 1 video │ 32,449 views │ 1/1 with transcripts
├─ 🟡 HN: 31 storys │ 1,361 points │ 707 comments
├─ 🦋 Bluesky: 3 posts │ 5 likes
├─ 🐙 GitHub: 1 item │ 140,234 stars │ 14,670 comments
├─ ⛏️ Digg: 4 clusters │ 22 posts │ 12 authors
├─ 📄 arXiv: 3 papers
├─ 📰 Techmeme: 2 headlines
├─ 🗣️ Top voices: @AnthropicAI, @alexalbert__, @patilvishi │ r/ClaudeAI, r/ClaudeCode, r/ChatGPTCoding
└─ 📎 Raw results saved to ~/Documents/Last30Days/claude-code-agent-teams-and-subagent-orchestration-raw-v3.md
```

### Supplemental web sources

- [CloudZero](https://www.cloudzero.com/blog/claude-code-agents/) — the 4-7× / ~15× token multipliers; Agent View, subagents, teams, parallel-session cost.
- [Charles Jones](https://charlesjones.dev/blog/claude-code-agent-teams-vs-subagents-parallel-development) — Agent Teams shipped in **Claude Code 2.1.32**; when teams beat subagents.
- [getpushtoprod — 30 Tips for Claude Code Agent Teams](https://getpushtoprod.substack.com/p/30-tips-for-claude-code-agent-teams) — ~7× tokens in plan mode; plan-approval read-only gate; sweet spot is genuinely-communicating multi-file work.
- [Hatchworks](https://hatchworks.com/blog/claude/claude-sub-agents-and-agent-teams/) — when to delegate inside Claude; "save sub-agents for work that is genuinely off-thread".
- [MindStudio](https://www.mindstudio.ai/blog/what-is-claude-code-agent-teams/) — teams coordinate through a **mailbox + shared task list**; subagents only report to their parent. That distinction is the architectural crux.
- [ksred](https://www.ksred.com/claude-code-agents-and-subagents-what-they-actually-unlock/) — "not every task needs five agents; most do not."

## 4. Candidate table

All rows measured **2026-08-04**. "Native" = does it build on Claude Code's own
primitives (`.claude/agents/`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, skills,
hooks) or reimplement orchestration itself? Probed directly via
`gh api repos/<r>/git/trees/HEAD?recursive=1` and `gh search code`, not from
README claims.

| Name | URL | What it is | Named roles | Parallelism | Native primitives | ★ | Last push | Maintained |
|---|---|---|---|---|---|---:|---|---|
| **harness** | [revfactory/harness](https://github.com/revfactory/harness) | Meta-tool: say "build a harness for this project" and it **generates** `.claude/agents/` + `.claude/skills/` for your repo | generated per-project, not fixed | delegates to the native Agent-Teams runtime | **yes, deeply** — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` in `docs/quickstart.md` + a dedicated `docs/experimental-dependency.md`; 44 files total, it is a generator not a framework | 8,601 | 2026-07-24 | yes |
| **octo / claude-octopus** | [nyldn/claude-octopus](https://github.com/nyldn/claude-octopus) | Multi-LLM orchestration: 8 providers (Codex, Gemini, Claude, Perplexity, OpenRouter, Copilot, Qwen, Ollama), Double Diamond workflow, 75% consensus gates | 10 in `.claude/agents/` (backend-architect, cloud-architect, code-reviewer, database-architect, debugger, docs-architect, …) + 30 more per marketplace | provider fan-out + consensus voting | **yes** — real `.claude/agents/` **and** a `scripts/agent-teams-bridge.sh` | 3,923 | **2026-08-04** | yes, actively |
| **session-orchestrator** | [Kanevry/session-orchestrator](https://github.com/Kanevry/session-orchestrator) | 5 typed waves (Discovery → Core → Polish → Quality → Finalization), inter-wave quality gates, verified close-out | **15**, each with a **JSON schema**: analyst, architect-reviewer, code-implementer, db-specialist, dialectic-deriver, docs-writer, **eval-judge**, **memory-proposal-collector**, qa-strategist, security-reviewer, session-reviewer, **skill-applied-judge**, test-writer, ui-developer, ux-evaluator | wave-based (a coarse DAG: each wave is a barrier) | **yes** — `docs/adr/0002-agent-teams-substrate.md` explicitly adopts Agent Teams as the substrate; `templates/_shared/rules/parallel-sessions.md`, `.claude/rules/loop-and-monitor.md` | 50 | **2026-08-04** | yes, actively |
| **statsclaw** | [statsclaw/statsclaw](https://github.com/statsclaw/statsclaw) | 13 workflows, two-pipeline design, from simple changes to Monte Carlo simulation studies | **exactly 9**: leader, planner, builder, tester, scriber, simulator, distiller, reviewer, shipper | pipeline stages | partial — `agents/*.md` at repo root (not `.claude/agents/`), teams flag only in `.claude/settings.json` | 89 | 2026-07-22 | yes |
| **guild** | [lookatitude/guild](https://github.com/lookatitude/guild) | Self-evolving team of specialists; plans before executing, assembles focused context, **improves its skills over time** | 10 meta-roles: command-builder, docs-writer, **eval-engineer**, hook-engineer, plugin-architect, research-digester, security-auditor, skill-author, **specialist-agent-writer**, tooling-engineer | delegated; `_shared/handoff-contract.md` defines the contract | **yes, deepest** — `.claude/agents/_shared/{handoff-contract,plan-anchors,methodology-skills}.md` **and a lifecycle hook** `hooks/agent-team/task-created.ts` | 6 | **2026-08-04** | yes, actively |
| **superpipelines** | [gustavo-meilus/superpipelines](https://github.com/gustavo-meilus/superpipelines) | 4 pipeline patterns — sequential, **parallel fan-out**, iterative-loop, human-gated — with structural write/review isolation + crash-safe state recovery; runs across Claude Code, Cursor, Codex, OpenCode | per-pipeline (`analyzer`/`reviewer`/`reporter` in the sample) | **explicit fan-out pattern**, the closest thing to a declared DAG | partial — nested `.claude/agents/<pipeline>/` **but no teams flag**: it reimplements orchestration on subagents | 4 | 2026-07-15 | yes |
| **wmux-orchestrator** | [amirlehmam/wmux-orchestrator](https://github.com/amirlehmam/wmux-orchestrator) | Decomposes tasks into parallel agents coordinated through **dependency-aware waves**, visual terminal panes, automated review | 1 generic `agents/wmux-worker.md` (workers are homogeneous) | **dependency-aware waves — a real DAG** | partial — no teams flag; own coordination layer | 10 | 2026-07-17 | yes |
| **aws-samples agent team** | [aws-samples/sample-claude-code-agent-team](https://github.com/aws-samples/sample-claude-code-agent-team) | AWS reference implementation of a spec-driven collaborating agent team | 5: coding, devops, fullstack, review, sa | native teams | **yes** — teams flag in `README.md` + `settings.json`; `agents/` + `skills/git-workflow/SKILL.md` | 47 | 2026-07-29 | yes |
| **team-forge** | [shirleyfuxw/team-forge](https://github.com/shirleyfuxw/team-forge) | Meta-extension that **auto-generates project-specific agent teams**; 5-role work/verify coverage | generated from `templates/workflow/profile.md.j2` | native teams | **yes** — teams flag in `hooks/session-start` and `skills/run/references/team.md` | 1 | **2026-08-03** | yes |
| **HydraTeams** | [Pickle-Pixel/HydraTeams](https://github.com/Pickle-Pixel/HydraTeams) | Translation proxy making native Agent Teams **model-agnostic** — any model as a teammate (GPT, Gemini, Ollama) | n/a (infrastructure) | rides native teams | **yes** — it IS a shim over the native feature | 68 | 2026-02-08 | **no — frozen 6 months** |
| **claude-agent-squad-codex** | [M-yer/claude-agent-squad-codex](https://github.com/M-yer/claude-agent-squad-codex) | Fork of claude-agent-squad where **every sub-agent forwards its work to the Codex CLI** | planner, builder, reviewer | nested sub-agent fan-out | subagents (not teams) | 0 | 2026-07-21 | solo, quiet |
| **tinytandem** | [jonathanavni/tinytandem](https://github.com/jonathanavni/tinytandem) | Minimalist two-agent harness: Claude orchestrates, **Codex implements and adversarially reviews** | 2 | none (serial pair) | n/a | 0 | 2026-06-30 | solo, quiet |
| **ATWZ** (paper) | [arXiv:2607.22917v2](https://arxiv.org/abs/2607.22917v2) | Filesystem operations layer for **long-lived** Agent Teams: per-agent workstation dirs, periodic backup, one-command team restore | n/a | n/a | native teams (fixes them) | n/a | 2026-07-30 | research artifact |
| **clnode** | [SierraDevsec/clnode](https://github.com/SierraDevsec/clnode) | Swarm coordination via **hooks + DuckDB** — the only DB-backed coordination substrate observed | — | swarm | hooks | 25 | 2026-02-06 | **no** |
| **dev-forge** | [yn01/claude-plugins](https://github.com/yn01/claude-plugins/tree/main/plugins/dev-forge) | **SQLite-backed** team orchestration: sprint contracts, wiki knowledge mgmt, automatic **bug council** escalation | orchestrator, team leads, implementers, evaluators | sprint contracts | — | 0 | 2026-07-05 | slowing |
| **nxtg-forge** | [nxtg-ai/forge-plugin](https://github.com/nxtg-ai/forge-plugin) | 33 agents / 32 skills / 7 hooks enforcing **`verifier.agent != task.agent`** — no agent grades its own homework | 33 | — | hooks | 5 | **2026-08-04** | yes |
| **goalkeeper** | [bonfire-systems/goalkeeper](https://github.com/bonfire-systems/goalkeeper) | Contract-driven **long-running** execution: after each checkpoint a **fresh-context judge subagent** reviews the diff against an explicit Definition of Done | judge | none | subagents | 12 | 2026-06-22 | slowing |
| **compounded** | [ankitkr3/compounded](https://github.com/ankitkr3/compounded) | **Trust-gradient**: every skill earns autonomy — new skills start `.proposed/`, get replayed on a real task by a verifier subagent | verifier | none | skills | 5 | 2026-06-22 | slowing |
| **sindri** | [4KMetrics/sindri](https://github.com/4KMetrics/sindri) | One-line goal ("reduce bundle_bytes 15%") → overnight loop: propose, apply in **fresh subagent contexts**, benchmark, keep wins as commits, revert losses | — | candidate fan-out | subagents | 0 | 2026-06-27 | slowing |
| **hive** | [CipherandRow/claude-hive-plugin](https://github.com/CipherandRow/claude-hive-plugin) | Bio-inspired swarm: stigmergy coordination, **pheromone scoring that learns across sessions**, adaptive concurrency; 16 mechanisms from ant/bee colonies | — | adaptive parallel subtasks | — | 0 | 2026-07-24 | yes |
| **claude-alloy** | (marketplace `claude-alloy`) | 11 agents (Steel orchestrates, Mercury searches, Tungsten executes) + 11 hooks | 11 | — | — | — | — | **repo 404 — gone** |

## 5. Top 5 ranked

Ranked against the stated goal: *a reusable, self-improving team of ~9 roles,
DAG-parallelized, able to offload work to a Codex CLI subscription.*

**1. [Kanevry/session-orchestrator](https://github.com/Kanevry/session-orchestrator)** — 50★, pushed 2026-08-04.
The closest structural match by a distance. It is the only project observed
that has **all four** of: (a) a fixed roster of named roles at the right
granularity — 15, trimmable to ~9; (b) a **JSON schema per role**
(`agents/schemas/*.schema.json`), which is what makes handoffs machine-checkable
rather than prose; (c) an explicit self-improvement loop as *first-class agents*
— `eval-judge`, `skill-applied-judge`, `memory-proposal-collector`,
`session-reviewer`; and (d) a written **ADR adopting Agent Teams as the
substrate** (`docs/adr/0002-agent-teams-substrate.md`) rather than reimplementing
it. Its wave model is a coarse DAG (barriers, not arbitrary edges), and it has
no Codex lane. Its repo conventions — `agents/AGENTS.md`, `.claude/rules/`,
`docs/adr/` — are the same shape as this repo, so the borrow cost is low.

**2. [revfactory/harness](https://github.com/revfactory/harness)** — 8,601★, pushed 2026-07-24.
The category winner by adoption, and the only one at consolidation scale. It is
a **generator**, not a framework: it reads your project and emits
`.claude/agents/` + `.claude/skills/`, then hands off to the native Agent-Teams
runtime. That is exactly the "reusable" axis — you would own the output rather
than depend on someone's runtime. It carries `docs/experimental-dependency.md`,
i.e. it is honest that it rides an experimental flag. No Codex lane, no DAG of
its own, no self-improvement loop. Read it for the generation approach; do not
adopt it wholesale.

**3. [gustavo-meilus/superpipelines](https://github.com/gustavo-meilus/superpipelines)** — 4★, pushed 2026-07-15.
The only project with **all four execution patterns declared as first-class**:
sequential, parallel fan-out, iterative-loop, human-gated — plus **structural
write/review isolation** and crash-safe state recovery, and it explicitly spans
**Claude Code, Cursor, Codex and OpenCode**. That is the DAG axis *and* the
Codex-offload axis in one project. The catch is real: 4 stars, one author, and
it **reimplements** orchestration on subagents (`.claude/agents/<pipeline>/`, no
teams flag), so it inherits none of the native runtime's improvements. Borrow
the pattern vocabulary, not the runtime.

**4. [lookatitude/guild](https://github.com/lookatitude/guild)** — 6★, pushed 2026-08-04.
The deepest native integration found: a **lifecycle hook on the agent-team task
event** (`hooks/agent-team/task-created.ts`) and a shared
`_shared/handoff-contract.md` / `plan-anchors.md` under `.claude/agents/`. Its
roster is *meta* — `skill-author`, `specialist-agent-writer`, `eval-engineer`,
`hook-engineer`, `plugin-architect` — i.e. it is a team that **builds and
improves Claude Code harnesses**, which is the self-improving axis expressed as
roles rather than as a bolt-on loop. Six stars; treat as a design source.

**5. [nyldn/claude-octopus](https://github.com/nyldn/claude-octopus)** — 3,923★, pushed 2026-08-04.
The only *popular and actively maintained* project that solves the Codex axis
properly: 8 providers behind one control plane, adversarial review, 75%
consensus gates, **and** a `scripts/agent-teams-bridge.sh` alongside real
`.claude/agents/`. Its weakness for this goal is that its unit of parallelism is
*providers*, not a task DAG, and its role set is a generic specialist library
rather than a designed team. Take the provider-routing and consensus mechanics.

**Honourable mentions, for one idea each:** `nxtg-forge` — the
`verifier.agent != task.agent` invariant, enforced by hooks; `goalkeeper` — a
**fresh-context** judge against an explicit Definition of Done at every
checkpoint; `compounded` — skills earn autonomy through a replay verifier;
`dev-forge` / `clnode` — a real database (SQLite / DuckDB) as the coordination
substrate instead of markdown files; `statsclaw` — a shipped 9-role roster to
diff a proposed roster against; **ATWZ ([arXiv:2607.22917v2](https://arxiv.org/abs/2607.22917v2))**
— read this *before* designing anything on native Agent Teams; it names the four
failure modes and its filesystem-workstation remedy is cheap to copy.

### What is NOT out there

- **No maintained, popular, general-purpose Claude↔Codex team framework.** Nine projects attempt it; the most-starred (HydraTeams, 68★) has been frozen since 2026-02-08 and the rest are ≤9★ solo repos.
- **No project observed declares a true task DAG with arbitrary edges.** The state of the art among third-party projects is *waves* / *barriers* (`session-orchestrator`, `wmux-orchestrator`) or *named patterns* (`superpipelines`). Nothing does dependency edges between individual role invocations. ⚠️ **But the substrate for exactly that already ships natively and nobody is using it — see §6.**
- **Nothing combines all four goal axes.** The best single project covers two.
- **Consolidation has not happened.** ~58 generic frameworks in the marketplace; two above 3,000★, everything else under 100; 30 of 49 shortlisted repos under 10★.

## 6. The gap the whole market is missing: dynamic workflows

Every framework in §1-§5 hand-rolls orchestration on top of **subagents** or
**agent teams**. Claude Code ships a **third** primitive that is a strictly
better fit for a DAG-parallelized team, and the field has not noticed.

Source: the vendor's own docs, on disk —
`$CC/workflows.md` ("Orchestrate subagents at scale with dynamic workflows"),
where `$CC` is the knowledge-base offline claude-code doc tree.

**A dynamic workflow is a JavaScript script that orchestrates subagents**,
executed by a runtime in an isolated environment separate from the
conversation. Claude writes the script; you can read, diff, edit and rerun it.
Requires **Claude Code v2.1.154+**, available on all paid plans, all providers
(Anthropic API, Bedrock, Google Cloud Agent Platform, Microsoft Foundry). On
Pro it is off by default — enable via the Dynamic workflows row in `/config`.

The vendor's own four-way comparison (`$CC/workflows.md`) is the decision table:

| | Subagents | Skills | **Agent teams** | **Workflows** |
|---|---|---|---|---|
| What it is | A worker Claude spawns | Instructions Claude follows | A lead agent supervising peer sessions | **A script the runtime executes** |
| Who decides what runs next | Claude, turn by turn | Claude, following the prompt | The lead agent, turn by turn | **The script** |
| Where intermediate results live | Claude's context window | Claude's context window | A shared task list | **Script variables** |
| What's repeatable | The worker definition | The instructions | The team definition | **The orchestration itself** |
| Scale | A few delegated tasks per turn | Same as subagents | A handful of long-running peers | **Dozens to hundreds of agents per run** |
| Interruption | Restarts the turn | Restarts the turn | Teammates keep running | **Resumable in the same session** |

Why this maps onto the stated goal better than anything in §5:

- **"DAG-parallelized" is just JavaScript control flow.** The saved script is plain JS with top-level `await`: `agent(prompt, {schema, label})` spawns one subagent, `pipeline(list, fn)` fans out one per item. Sequencing and dependency edges are ordinary `await`s between those calls — an arbitrary DAG, not a wave barrier. Structured output is native (`schema:` is a JSON Schema on the `agent()` call), which is the same idea `session-orchestrator` implements by hand as `agents/schemas/*.schema.json`.
- **"Reusable" is the explicit design point.** Saved to `.claude/workflows/<name>.js` with a `meta` block, distributable **in a plugin**, and parameterisable (`Pass input to a saved workflow`). What's repeatable is *the orchestration itself*, not just role definitions.
- **It solves ATWZ drawback #2 and #3 outright.** Intermediate results live in **script variables**, not a context window, so compaction cannot erode them and no decisions get trapped in a compacted chat. That is the arXiv paper's central complaint about Agent Teams, answered by a different primitive rather than by a filesystem workaround.
- **Adversarial review is called out as a first-class use.** The docs: a workflow "can have independent agents adversarially review each other's findings before they're reported, or draft a plan from several angles and weigh them against each other." That is the cross-model review pattern (§2b) expressed natively.
- **`/deep-research` is a bundled workflow** — a shipped, readable reference implementation of the multi-phase pattern.

**Constraints to design around** (`$CC/workflows.md` § Behavior and limits):

| Constraint | Consequence for a 9-role team |
|---|---|
| **No mid-run user input** (only permission prompts pause a run) | Human sign-off between stages means **one workflow per stage**, not one workflow for the whole pipeline |
| **No filesystem or shell access from the script itself** — agents read/write/run, the script only coordinates | The orchestrator is pure coordination; every side effect goes through a role agent. This is a *feature* for a write/review isolation design |
| **Up to 16 concurrent agents** (fewer on low-core machines) | A 9-role team fits comfortably; a wide fan-out over files does not |
| **1,000 agents total per run** | Bounds runaway loops |
| Resume replay: cached results **stop at the first agent that didn't finish**, and everything that started after it re-runs even if it completed | **Many small agents preserve more progress than one long agent** — a direct design constraint on role granularity |
| Resume works **only within the same session**; exiting Claude Code restarts the workflow fresh | Cross-session durability still needs your own layer (this is ATWZ drawback #1, unfixed) |
| Every agent uses the session model unless the script routes a stage, or `CLAUDE_CODE_SUBAGENT_MODEL` overrides both | **The per-stage model route is the Codex-offload seam** — a stage can be routed, per-stage, rather than the whole run |
| `Large workflow` advisory warning at >25 agents or >1.5M projected tokens (v2.1.203+); suppressed under `ultracode` | Budget signal, not a limit |

### Nobody in the surveyed field uses it — measured

| Probe | Result | Control arm |
|---|---|---|
| `.claude/workflows/` file count across the 10 top candidates (harness, octopus, session-orchestrator, guild, superpipelines, statsclaw, wmux-orchestrator, aws-samples, team-forge, nxtg-forge) | **0 / 10 — every one is zero** | the identical jq shape with the `.claude/agents/` prefix returned real file lists for guild (15) and octopus (10), so the probe discriminates |
| marketplace descriptions matching `dynamic workflow\|\.claude/workflows\|workflow tool` across all 2,298 | **1** | `agent teams` → 4 in the same corpus. Descriptions are short, so this arm is weak on its own; the repo-tree probe above is the load-bearing one |

**A positive control that it is real and usable:** the installed
`code-modernization` plugin's skills are explicitly gated on it — e.g.
`modernize-harden-scan`: *"Invoked by `/modernize-harden` **when the Workflow
tool is available**"*, and `modernize-uplift-migrate` describes
"dependency-aware escalating batches behind a per-batch circuit breaker", with
each unit's `deps` listing sibling unit names so "a unit and its dependency
never run in the same batch". **That is a real dependency DAG, expressed in a
shipped workflow, by Anthropic's own plugin authors.** It is the best available
worked example of the pattern the goal describes — and it came from the plugin
cache on this machine, not from any of the 2,298 marketplace entries.

**Recommendation:** design the ~9-role team as **role definitions in
`.claude/agents/` orchestrated by a dynamic workflow script**, one workflow per
human-gated stage, with per-stage model routing as the Codex seam — and borrow
`session-orchestrator`'s per-role JSON schemas as the `agent({schema})`
contracts. That combination does not exist in any of the ~58 frameworks
surveyed.

## Control arms

Every negative claim above was armed. Control terms were invented fresh for this
run and are recorded here only because the run is finished (a published control
term stops discriminating — do not reuse these).

| Probe | Negative result | Control arm | Verdict |
|---|---|---|---|
| `gh api repos/<r>` on 3 marketplace-listed repos | `OMARVII/claude-alloy`, `KhakiSkech/KhakiSketcher`, `Joys-Dawn/toolwright` → 404 | `anthropics/claude-code` → **140,235★** (probe sees); `zzq-nonexistent-xyzzy9/nope` → 404 (probe discriminates) | the three are genuinely gone |
| `gh search repos "claude code agent teams DAG"` | 0 rows | `quixotic-marmalade-7731` → 0 rows, same shape; sibling queries → 4-12 rows | real negative **for that phrasing only** — DAG-shaped projects exist under other words |
| `gh search repos "claude code parallel agents worktree"` | 0 rows | same as above | same |
| `gh search code <repo> CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `superpipelines`, `wmux-orchestrator` → no hits | same command returned hits for `harness`, `octopus`, `session-orchestrator`, `guild`, `team-forge`, `aws-samples` | real negative: those two reimplement rather than ride the native flag |
| `jq '.plugins[]'` enumeration | — | enumerated **all 2,298** then filtered; did **not** search for expected names. `.source` is polymorphic and a naive `.source.url` **errored at byte 24080** — caught, not silently dropped | count is trustworthy |
| /last30days source coverage | "no TikTok/Instagram/web discussion" | **NOT CLAIMED** — those three returned HTTP 402 / 422, i.e. never asked. Reddit/X/HN/YouTube/Bluesky/GitHub/Digg/arXiv/Techmeme completed | partial coverage stated, not silence |

**Labelled UNVERIFIED:** the "per Google's evaluation, teams architectures are
ineffective most of the time" claim (@liustack, single X post, 1 reply — the
underlying Google evaluation was not traced); the "700× spread in code output"
claim (Bluesky, third-party); the "someone tested it and found huge volumes of
useless inter-agent communication" claim (same post, test not linked).

## GitHub repos touched

- [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) — the official community marketplace; source of the 2,298-plugin enumeration.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — control arm for the `gh api` probe (140,235★); the platform whose primitives every candidate targets.
- [revfactory/harness](https://github.com/revfactory/harness) — top-ranked by adoption; probed for native-primitive usage and file count.
- [nyldn/claude-octopus](https://github.com/nyldn/claude-octopus) — multi-LLM orchestration; probed for `.claude/agents/` and the agent-teams bridge.
- [Kanevry/session-orchestrator](https://github.com/Kanevry/session-orchestrator) — top-ranked for this goal; role + schema enumeration, ADR on the agent-teams substrate.
- [lookatitude/guild](https://github.com/lookatitude/guild) — self-evolving specialist team; `.claude/agents/_shared/` and the agent-team lifecycle hook.
- [gustavo-meilus/superpipelines](https://github.com/gustavo-meilus/superpipelines) — four declared pipeline patterns across four CLIs; probed for the teams flag (absent).
- [statsclaw/statsclaw](https://github.com/statsclaw/statsclaw) — 9-role roster, enumerated for comparison.
- [amirlehmam/wmux-orchestrator](https://github.com/amirlehmam/wmux-orchestrator) — dependency-aware waves; probed for role count and teams flag.
- [aws-samples/sample-claude-code-agent-team](https://github.com/aws-samples/sample-claude-code-agent-team) — AWS reference implementation on native Agent Teams.
- [shirleyfuxw/team-forge](https://github.com/shirleyfuxw/team-forge) — auto-generates project-specific agent teams; probed for teams-flag wiring.
- [Pickle-Pixel/HydraTeams](https://github.com/Pickle-Pixel/HydraTeams) — model-agnostic Agent-Teams proxy; the cleanest Codex-offload architecture, measured frozen.
- [M-yer/claude-agent-squad-codex](https://github.com/M-yer/claude-agent-squad-codex) — every subagent forwards to the Codex CLI; the exact experiment run elsewhere.
- [a1-ceo/claude-agent-squad](https://github.com/a1-ceo/claude-agent-squad) — the parent of the above; nested orchestrator → planner/builder/reviewer.
- [jonathanavni/tinytandem](https://github.com/jonathanavni/tinytandem) — Claude orchestrates, Codex implements and adversarially reviews.
- [leyuan0602-glitch/cc-claude-codex](https://github.com/leyuan0602-glitch/cc-claude-codex) — Claude Code orchestrating Codex via markdown relay.
- [ZaMpAdAKiNg/orchestrate-skill](https://github.com/ZaMpAdAKiNg/orchestrate-skill) — one skill exposing the same control plane in Claude Code and Codex.
- [chorious/AgentCall](https://github.com/chorious/AgentCall) — Codex + Claude Code orchestration workspace.
- [craigkitterman/cross-model-code-review-skill](https://github.com/craigkitterman/cross-model-code-review-skill) — multi-model consensus review across Codex/Gemini.
- [giwarb/ps-edge-cli](https://github.com/giwarb/ps-edge-cli) — a shipped artifact built with the Claude-orchestrator/Codex-implementer pattern.
- [JohnRiceML/clawport-ui](https://github.com/JohnRiceML/clawport-ui) — 899★ agent-teams command centre; measured frozen since 2026-03-24.
- [DatafyingTech/Claude-Agent-Team-Manager](https://github.com/DatafyingTech/Claude-Agent-Team-Manager) — org-chart manager for agent teams.
- [Gr122lyBr/claude-teams-brain](https://github.com/Gr122lyBr/claude-teams-brain) — memory injection per teammate role.
- [ShawhinT/subagents-vs-teams](https://github.com/ShawhinT/subagents-vs-teams) — benchmark comparing subagents vs Agent Teams.
- [kar-ganap/ate-series](https://github.com/kar-ganap/ate-series) — Agent Teams Eval across bug-fixing and feature work.
- [victordelrosal/agent-teams-claude-code](https://github.com/victordelrosal/agent-teams-claude-code) — 28-file field manual for multi-agent Claude Code.
- [panaversity/claude-code-agent-teams-exercises](https://github.com/panaversity/claude-code-agent-teams-exercises) — teaching material for team creation and task coordination.
- [stanislc/zellij-claude-teams](https://github.com/stanislc/zellij-claude-teams) — tmux→zellij shim for Agent Teams.
- [fivetaku/kkirikkiri](https://github.com/fivetaku/kkirikkiri) — natural-language team builder.
- [human-corey/AntAI](https://github.com/human-corey/AntAI) — GUI canvas for orchestrating agent teams.
- [nxtg-ai/forge-plugin](https://github.com/nxtg-ai/forge-plugin) — the `verifier.agent != task.agent` invariant.
- [bonfire-systems/goalkeeper](https://github.com/bonfire-systems/goalkeeper) — fresh-context judge at every checkpoint.
- [ankitkr3/compounded](https://github.com/ankitkr3/compounded) — trust-gradient skill autonomy.
- [4KMetrics/sindri](https://github.com/4KMetrics/sindri) — overnight experiment loop keeping wins as commits.
- [CipherandRow/claude-hive-plugin](https://github.com/CipherandRow/claude-hive-plugin) — stigmergy/pheromone cross-session learning.
- [SierraDevsec/clnode](https://github.com/SierraDevsec/clnode) — hooks + DuckDB coordination substrate.
- [yn01/claude-plugins](https://github.com/yn01/claude-plugins) — hosts `dev-forge`, SQLite-backed team orchestration with a bug council.
- [tikalk/adlc-team-skills](https://github.com/tikalk/adlc-team-skills) — team coding standards as skills for Claude Code and Codex; HN 72pts on 2026-08-04.
- [Automaat/sybra](https://github.com/Automaat/sybra) — local swarm orchestrator, actively developed.
- [josephneumann/claude-corps](https://github.com/josephneumann/claude-corps) — parallel git-worktree orchestration.
- [ekamphuis82/claude-code-swarm](https://github.com/ekamphuis82/claude-code-swarm) — director-led swarm with adversarial verification.
- [brenokern/dev-team-orchestration](https://github.com/brenokern/dev-team-orchestration) — plan → data/backend/frontend subagent team.
- [Shiyao-Huang/aids-tools](https://github.com/Shiyao-Huang/aids-tools) — identity-aware trace/rating across Claude Code, Codex and Bash agents.
- [rubenzarroca/sdd-autopilot](https://github.com/rubenzarroca/sdd-autopilot) — zero-stop spec→PR pipeline with metacognition scoring.
- [OMARVII/claude-alloy](https://github.com/OMARVII/claude-alloy) — marketplace-listed, **404 at measurement**.
- [KhakiSkech/KhakiSketcher](https://github.com/KhakiSkech/KhakiSketcher) — marketplace-listed, **404 at measurement**.
- [Joys-Dawn/toolwright](https://github.com/Joys-Dawn/toolwright) — marketplace-listed (`wrightward`), **404 at measurement**.

_Non-repo sources are cited inline in §3 (arXiv, CloudZero, Charles Jones,
getpushtoprod, Hatchworks, MindStudio, ksred, and the X / Bluesky / YouTube
items) and in §6 (the vendor's offline claude-code doc tree — `$CC/workflows.md`
at `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/workflows.md`
— plus the locally-installed `code-modernization` plugin's workflow-gated
skills, which are not published in the community marketplace)._

## Raw material persisted

- `.agent/kb/raw/marketplace.json` — the fetched marketplace (1,579,090 B, HTTP 200).
- `.agent/kb/raw/marketplace-flat.tsv` — all 2,298 entries flattened to name / description / URL.
- `.agent/kb/raw/repo-metrics-2026-08-04.tsv` — the 49-repo `gh api` measurement.
- `.agent/kb/raw/last30days-agent-teams.md` — the full /last30days evidence dump.
