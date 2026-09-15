# Grilling record — codex SDLC subagent team (2026-09-14)

The decision trail behind `docs/specs/codex-sdlc-subagent-team.md`. Every row is a
question put to the operator via `AskUserQuestion`, his answer, and what the answer
changed. It exists because the answers otherwise live only in a session transcript
that `/clear` destroys — and this session's own coverage audit found that
decided-but-unrecorded is the failure mode that actually bites (nine findings were
tracked nowhere; the worst was the session's own rank-1 action, now #1116).

**Facts were the assistant's job, decisions the operator's.** Where a probe changed
the answer, the probe is cited.

## Round 1 — scope and mechanism

| Q | Question | Operator's answer | What it changed |
|---|---|---|---|
| Q1 | How should the codex config schema be wired for validation + settings discovery? | Generate version-exact via app-server — **plus** automate checking for a newer release, ship it as a skill, wire codex's native plugins, and add it to the doctor workflow | Became decision **D5**. ⚠️ The "generate version-exact" half was later **refuted by measurement**: `codex app-server generate-json-schema` emits the app-server PROTOCOL schemas, which contain no `mcp_servers` at all. The config schema is the separate published artifact, now vendored as `schemas/codex-config.json` |
| Q2 | We have 14 codex agents already. What shape should the SDLC team take? | Add SDLC specialists **alongside** the 14 | **D1**. The 14 are generator-mirrored and gated by `codex_agent_parity` + `codex_lane_mirror`; restructuring them was rejected |
| Q3 | Self-optimizing/self-healing/self-learning is not native. How to handle? | **Scope it out now; design it as its own piece** | **D6**. Codex "Memories" is a ChatGPT-account context feature, not per-agent performance learning (`app__settings.md:108-111`). NOT BUILT, deliberately |
| Q4 | What should the advisor produce, given the research was already done? | **Re-verify my research, then design** | Produced the 360-line `adv-sdlc-team-2026-09-14.md`, which corrected the assistant on precedence (see below) |

## Round 2 — after the plugin inventory

| Q | Question | Operator's answer | What it changed |
|---|---|---|---|
| Q5 | firecrawl and last30days appear absent from codex. Add them? | *"add as their native codex plugins/apps — as i keep telling you dont guess, research first before asking me questions"* | **The rebuke was correct.** Re-probed: all five are ALREADY installed and enabled. The earlier "absent" was a bounded probe twice over — searching `codex mcp list` (servers, not plugins) and truncating `codex plugin list` after 2 of **18** marketplaces. Became **D4** |
| Q6 | What triggers the schema currency check? | All three layers **plus a Claude function hook** for stale-dependency detection | **D5**'s four-layer currency design |
| Q7 | What SDLC roles should the team cover? | Advisor roster **+ artifact + gates + phases** (all four) | Forced the synthesis in Q8 — the axes cut differently and "specialist wherever possible" had to resolve to one non-overlapping `description` per agent |

## Round 3 — the synthesis

| Q | Question | Operator's answer | What it changed |
|---|---|---|---|
| Q8 | Artifact-keyed, gate-owned, phase-instructed — right shape? | *"build up a rebuilt set of agents from option 1, and have option 4 dynamically add/adjust the team as needed, with the ability to add more subagents when required"* | **D1 + D2.** One axis drives `description` (artifacts are disjoint; phases overlap), each agent owns a gate, phase lives in `developer_instructions`, and a dispatcher adjusts the team per task. ⚠️ This overruled the advisor, which recommended `AGENTS.md` blocks over a dispatcher — so the dispatcher was the untested half, which is why V3 exists |
| Q9 | `mcp_servers` inherits everything unless declared. How to set tool surfaces? | **Declare explicitly on every agent** | **D3**. ⚠️ Later **refuted by measurement**: `mcp_servers` is `"type": "object"` — it DEFINES servers and cannot select existing ones by name. An array made all six agents invalid and codex dropped them SILENTLY. D3 is not achievable through that key |
| Q12 | SDLC agents must be tracked AND not break `codex_agent_parity`; no name satisfies both. Which do we change? | *"this is our codebase, we can adjust the rules, dont limit yourself to what we setup before as it was all based on minimal and/or incorrect knowledged"* | Narrowed the gate: `LANE_PREFIXES` derived from `MODEL_BY_PREFIX`, replacing a bare `codex-` stem whose own comment revealed the stale assumption. Mutation-proven both arms |

## Where the operator overruled the assistant, and was right

1. **Q5** — "research first before asking me questions". All five plugins were already present; the assistant had asked a question one unbounded command would have answered.
2. **Q12** — refused to accept the existing gate as a constraint. The gate's scoping genuinely contradicted its own documented intent.
3. **Q10** (version sync) — chose to move all three claude-code version sites to 2.1.271 rather than leave the record lagging.

## Where the advisor overruled the assistant, and was right

**Precedence is not uniform.** The assistant claimed "agent-file value > explicit spawn > `[agents]` default > parent" universally. Actual, per `subagents.md:248-254`: the agent file pre-empts only for `model`/`model_reasoning_effort`; other settings resolve spawn > default > parent, and `mcp_servers`/`sandbox_mode`/`skills.config` **inherit from the parent when omitted**.

## Where the assistant overruled the advisor, with evidence

Its roster proposed **`gpt-5.3-spark`** for two of six agents. That model does not exist — the real name is `gpt-5.3-codex-spark`. Both agents would have failed on first spawn. Its Phase 2 also said to keep `[tools]` entries, which would have left the claude PATH shadowing in place.

## Still open

**D6 (self-learning) is NOT BUILT.** Scoped out at Q3. The team is reusable and
dispatcher-routed; it does not learn from its own performance. Calling it
self-optimizing would be false.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject of every decision above.
