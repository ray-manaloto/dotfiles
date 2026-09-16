# Codex SDLC subagent team — settled design

**Status:** design settled by operator grilling 2026-09-14. NOT implemented.
**Research:** `docs/research/kb/reports/agents/adv-sdlc-team-2026-09-14.md`
**Primary source:** `$KB/agent-harness-docs/docs/codex/agent-configuration__subagents.md`
where `$KB=~/dev/github/ray-manaloto/knowledge-base/sources`. Codex CLI **0.154.0**.

## Why this file exists

The decisions below were reached by grilling and would otherwise survive only in a
gitignored handoff. This session's own coverage audit found that its rank-1 action
had no durable record at all (now #1116), so a settled-but-unrecorded design is the
failure mode most worth preventing here.

## Verified mechanism — cite these, do not re-derive

| # | Fact | Evidence |
|---|---|---|
| 1 | Custom agents are standalone TOML under `.codex/agents/` (project) or `~/.codex/agents/` (personal) | `subagents.md:234` |
| 2 | Required fields: `name`, `description`, `developer_instructions` | `subagents.md:276` schema table |
| 3 | Agent files may also carry `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config` | `subagents.md:284` |
| 4 | `name` is the identity; filename is convention only | `subagents.md:286-288` |
| 5 | Built-ins `default`, `worker`, `explorer`; a custom agent with a built-in's name WINS | `subagents.md` §Global settings notes |
| 6 | `[agents]` globals: `enabled` (default true), `max_concurrent_threads_per_session` (legacy alias `max_threads`), `default_subagent_model`, `default_subagent_reasoning_effort`, `interrupt_message` (default true) | `subagents.md:258` table |
| 7 | Delegation is PROMPT-TRIGGERED. Codex itself spawns, routes, waits, and closes threads | `subagents.md:87-88`, §Orchestration |
| 8 | `multi_agent` is `stable true` by codex's OWN default, not set in our config | `codex features list`; control: 140 features, `code_mode` -> 6 |
| 9 | **Headless `codex exec` DOES spawn subagents** — measured, not assumed | see §Verification below |

### ⚠️ Precedence is NOT uniform — this was corrected during design

Verbatim, `subagents.md:248-254`:

> "If a custom agent file sets `model` or `model_reasoning_effort`, the value in the
> file takes precedence. **Otherwise**, Codex resolves each setting independently: an
> explicit spawn value, then the corresponding `[agents]` default, then the parent's
> value. … Other session settings, such as `sandbox_mode`, `mcp_servers`, and
> `skills.config`, **inherit from the parent when the custom agent file omits them**."

So: the agent file pre-empts only for `model`/`model_reasoning_effort`. **`mcp_servers`
inherits the parent's full set unless declared.** A coordinator's earlier claim that
the agent file wins universally was wrong.

### ⚠️ Model names — one proposed name does not exist

Real names, from the docs: `gpt-5.1-codex-max`, `gpt-5.2`, `gpt-5.3-codex`,
`gpt-5.3-codex-spark`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`, `gpt-5.6`,
`gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`.

The advisor's roster proposed **`gpt-5.3-spark`** for two agents. That is not a model;
the real name is **`gpt-5.3-codex-spark`**. Both would have failed on first spawn.

## Settled decisions

### D1 — Roster shape: artifact-keyed, gate-owned, phase-instructed

One agent per ARTIFACT, because `description` is what codex routes on and artifacts
are naturally disjoint where phases are not (`design` and `implement` overlap, and
description collision is the documented wrong-agent routing risk). Each agent OWNS a repo
gate, so its success signal is that gate's real rc. PHASE is expressed inside
`developer_instructions`, where it cannot cause wrong-agent routing.

Artifact axes present in this repo: `python/`, `*.pkl` + `hk.pkl`, `.github/`,
`.devcontainer/` + image, `docs/` + `.claude/rules/`, `tests/`.

### D2 — A dispatcher agent adjusts the team per task

Beyond the fixed base roster, a dispatcher agent selects and ADJUSTS the team for the
task at hand, and may add further subagents when required. This is additive to D1, not
a replacement.

⚠️ Tension to resolve at implementation time: the advisor recommended `AGENTS.md`
instruction blocks over a dispatcher, on the grounds that codex already routes by
description — and `.claude/rules/use-tool-builtins.md` requires written justification
before duplicating a native mechanism. The operator chose the dispatcher anyway, for
the dynamic add/adjust capability descriptions alone cannot provide. Record that
justification in the implementing PR.

### D3 — `mcp_servers` declared explicitly on EVERY agent

Because of the inherit-on-omit rule above, omitting the key silently grants the
parent's entire tool surface, which makes "specialist" fiction. Every agent file
declares its own.

### D4 — The five research plugins are ALREADY native, installed and enabled

Measured via `codex plugin list` across **18** configured marketplaces:

| plugin | status | source |
|---|---|---|
| `context7@context7-marketplace` | installed, enabled 1.0.1 | own marketplace |
| `exa@claude-plugins-official` | installed, enabled 3.4.1 | `exa-labs/exa-mcp-server.git` |
| `firecrawl@claude-plugins-official` | installed, enabled 1.0.9 | `firecrawl/firecrawl-claude-plugin.git` |
| `last30days@last30days-skill` | installed, enabled 3.24.0 | `mvanhorn/last30days-skill.git` |
| `openaiDeveloperDocs` | enabled (remote MCP) | `developers.openai.com/mcp` |

**Nothing needs adding.** An earlier claim that `firecrawl` and `last30days` were
absent came from two bounded probes: searching `codex mcp list` (servers, not plugins)
and truncating `codex plugin list` after the first two of 18 marketplaces.

### D5 — Schema: generate version-exact, ship as a skill, gate in doctor

`codex app-server generate-json-schema --out ./schemas` emits a bundle specific to the
exact codex version run (`app-server.md:112-116`) — preferred over the "latest" URL at
`config-file__config-reference.md:1603`, which can describe settings 0.154.0 lacks.
This also satisfies the requirement for a searchable inventory of every setting and
environment variable.

Currency is layered (operator chose all three, plus a fourth):
1. `currency.toml` + the shared engine (`mise run tool-currency`, `tool-currency-check`)
2. a `doctor.toml` assertion that the schema matches the installed codex version
3. Renovate carrying the codex pin bump
4. **a Claude function hook** that flags a stale/outdated dependency version

⚠️ **Trap:** a `# :schema` directive written WITH A SPACE is INERT (measured, session
2026-09-10c). Get the directive form right and pin it with a fail-arm test.

### D6 — Self-learning: DESIGNED, not built

Codex "Memories" is a ChatGPT-account context feature, not per-agent performance
learning (`app__settings.md:108-111`, `chrome-extension.md:155`). No native
mechanism exists, so any loop is homegrown.

Scoped out of the build at grilling Q3; **designed** at the operator's later
ruling. See **`docs/specs/codex-sdlc-team-learning-loop.md`**.

Its load-bearing idea: D1 gave every specialist an owned gate, so routing accuracy
is measurable WITHOUT self-assessment — compare the dispatcher's selected team
against the artifacts `git diff --name-only` says were actually touched. An
untouched-but-selected specialist is an over-select; a touched-but-unselected one
is an under-select. Both fall out of the diff.

Two constraints the design fixes in advance: the signal must live in a **tracked**
path (`.agent/` is gitignored at `.gitignore:109`, so telemetry there dies with a
`git clean`), and the loop **proposes** an instruction change to a separate delta
file rather than editing an agent — the `pwf-scribe` shape, keeping every change a
reviewed diff.

⚠️ It is a design. Nothing in it has been run, and it explicitly warns against
starting at the proposal-generator step, which fed two data points would rewrite
instructions on noise.

### D6-original — why it was scoped out

Codex "Memories" is a ChatGPT-account feature for carrying context between chats, not
per-agent performance learning (`app__settings.md:108-111`, `chrome-extension.md:155`).
No native mechanism was found. Scoped out deliberately as its own design.

## Spawn reconciliation (2026-09-16)

`SdlcTeamSettlement` now records the dispatcher's closing claimed roster and
the direct child sessions observed in Codex rollout metadata. Settlement fails
closed when the parent session id or observed source is unavailable, when no
children were observed, when a rollout written during the run is unreadable, or
when one-to-one pairing leaves a claim or non-review child unmatched; a claim
whose candidates do not all describe one child, or which carries two agent
paths, also fails. The pinned negative arm is a Codex rc=0 report claiming
`sdlc-python-specialist` with a valid parent banner but zero child rollouts:
its terminal status must be `failed`, never `completed`.
A roster token is satisfied by the child's `agent_role`, by the spawn name its
`agent_path` encodes, or vacuously when the child records no role at all and
the same claim's path candidate already anchors that child. Accepted limits: a
role-only claim reaches a path-only child only when its token is that path's
basename, a team run with zero observed specialists fails by design, and roster
identities stay lowercase-only. Terminators cover `no other`, `none`, and
`nothing else`; `No further specialists were spawned.` remains a claim and
fails closed.

## Verification already performed

> ⚠️ **REFUTED 2026-09-16 (#1142). The claim below is wrong, and the way it was
> wrong is the point.** `codex exec --ephemeral` does NOT spawn subagents. It
> means "Run without persisting session files to disk", and a spawned subagent
> IS a persisted thread (`app-server.md:291`, `:747`), so every spawn dies with
> `collab spawn failed: no thread with id`. Measured on one variable, with the
> evidence on disk instead of in a model's report:
>
> | arm | `collab spawn failed` | session files written |
> |---|---|---|
> | with `--ephemeral` | **3** | **0** |
> | without | **0** | **2** — child carries `"parent_thread_id":"<parent>"` |
>
> `--ephemeral` was removed from the dispatch argv in the same change; see the
> comment at `python/src/dotfiles_setup/sdlc_team.py`.
>
> **Why the original passed review.** Its control arms proved the *returned
> values* were correct — but one generalist lane doing the work itself returns
> those same correct values, so they never discriminated between "subagents ran"
> and "nothing spawned". The only thing asserting subagents was the model's own
> sentence, and that sentence is the fabrication pattern #1142 documents: on
> 2026-09-15 a lane reported four specialists whose "retry … succeeded" against
> four failures and zero successes in its own log.
>
> **It then became architecture.** "Spawn is not perfectly reliable … any
> orchestration must tolerate that" was derived from a fabricated retry and
> written into the dispatcher prompt as the retry-and-continue clause — which is
> what made the 2026-09-15 all-spawns-failed run read as sanctioned degradation
> rather than a broken team. A false premise did not just sit in a doc; it
> shaped the design that hid its own failure.
>
> The original text is kept below, struck through, as the record.

~~Headless spawn, on the path our lanes actually use:~~

```
printf '%s\n' "<spawn-two-subagents prompt>" | codex exec --ephemeral -s read-only -o <out> -
rc=0
```

~~Its report:~~ *"I actually spawned two subagents in parallel and waited for both. I did
not perform the checks myself. The initial spawn attempt failed, so I retried it
successfully before spawning the second agent."*

~~Control-armed: both returned values correct (`.claude/agents/` -> 23 files; README
first line `# Reproducible Dotfiles (AMD64)`), and 7 spawn/subagent mentions in the run
log.~~ **Design input:** ~~spawn is not perfectly reliable — the first attempt failed and
codex self-retried. Any orchestration must tolerate that.~~

## Verification: the team is FUNCTIONAL, not merely loadable

Three things were proven by running them, in this order, because each earlier one
turned out to be a precondition nobody had checked.

### V1 — the agents load at all

They did not, at first. All six declared `mcp_services`-style
`mcp_servers = ["context7", ...]` and **codex rejected every file silently**:
`codex exec` reported `sdlc-python-specialist` as "an unknown agent type" and fell
back to built-in `default` agents. Removing that one key made all six appear.

`mcp_servers` is `"type": "object"` in codex's own config schema — *"Definition
for MCP servers that Codex can reach out to"*. It DEFINES servers; it cannot
select existing ones by name. **The per-agent tool narrowing this spec's D3 asked
for is not achievable through that key.**

### V2 — a named specialist actually spawns

> ⚠️ **Same defect as the section above, same refutation (#1142).** Under
> `--ephemeral` nothing spawns, so "Agent types actually spawned" was the
> model's claim and not an observation. The control arm again proved only that
> the *values* were right — which a single lane doing the work itself also
> produces. The discriminating evidence nobody collected is on disk: a real
> spawn writes a second session file whose log carries
> `"parent_thread_id":"<parent>"`. Re-verify this the same way after the argv
> fix, and record the file pair, not the sentence.

```
codex exec --ephemeral -s read-only   # rc=0
"Agent types actually spawned: sdlc-python-specialist and
 sdlc-documentation-specialist."
```

~~Control-armed: both returned values correct (89 `.py` in
`python/src/dotfiles_setup/`, 26 `.md` in `.claude/rules/`).~~

### V3 — the DISPATCHER selects an appropriate team

The load-bearing test, because the operator chose a dispatcher over the advisor's
`AGENTS.md`-block recommendation. Task given: change `doc_refs.py` to log git's
stderr AND add a CI step to `ci.yml` — deliberately spanning two artifacts.

> "The dispatcher selected: `sdlc-python-specialist` — owns `doc_refs.py` behavior
> and Python tests. `sdlc-workflows-specialist` — owns `ci.yml` and workflow
> validation."
> "The dispatcher spawned exactly `sdlc-python-specialist` and
> `sdlc-workflows-specialist`. No other agents were spawned."

It selected correctly, did **not** over-select the config/image/documentation
specialists, and produced real `file:line` findings — including `doc_refs.py:198`,
which is the actual defect behind #1110. Unprompted, it also noted the check
already runs through hk, so an explicit CI step would execute it twice.

So artifact-keyed descriptions route correctly in practice, not just in theory.

### V4 — REUSABLE: a different task selects a different team

One passing test proves routing works once, not that it generalises. A second task
of a deliberately different shape — bump hk in `hk.pkl`/`hk-common.pkl` AND update
`.claude/rules/` + docs, with nothing in `python/` or `.github/`:

| task shape | team the dispatcher selected |
|---|---|
| `python/` + `.github/workflows/` | `sdlc-python-specialist` + `sdlc-workflows-specialist` |
| `*.pkl` + docs/rules | **`sdlc-config-specialist` + `sdlc-documentation-specialist`** |

> "It excluded the Python, workflows, and image specialists because their owned
> paths are outside the issue."

Two disjoint answers, with stated exclusion reasoning. The routing discriminates;
it is not selecting everything or defaulting to one team.

**And the team found real defects nobody asked it for**, which is the strongest
reusability evidence available:

- `AGENTS.md` sits at **11,999 bytes against agnix's 12,000-char cap** — one byte
  of headroom, so the next character added fails `lint-docs`. Confirmed by
  `wc -c`. Filed as **#1126**.
- `long-running-command-hangs.md:110` cross-references cache-clearing guidance
  that the same file's rule 5 states is retired. Confirmed by direct read. Filed
  with a sibling scoping finding as **#1127**.
- It also correctly understood this session's own `pin_parity` work unprompted,
  warning that changing only the two issue-named pkl files "may fail lint" because
  the check also covers `hk-image.pkl` and `shared.toml`.

### The schema is what makes V1 non-recurring

Every agent file carries `#:schema ../../schemas/codex-agent.json`. Fail arms:

| mutation | result |
|---|---|
| `mcp_servers = ["context7"]` | `error: ["context7"] is not of type "object"` rc=1 |
| drop `description` | `error: "description" is a required property` rc=1 |

That first row is the failure codex reports with no error, no warning and no exit
code. The directive converts it into a lint failure before codex ever sees it.

## Not yet decided

- The concrete agent names, descriptions, and `developer_instructions` per artifact.
- Which of the five plugins each role declares.
- Whether the dispatcher is an agent file, a skill, or an `AGENTS.md` block.
- Whether `CLAUDE_CODE_VERSION` (currently `2.1.270` in `mise.toml [env]`) should track
  the native install, now at 2.1.271.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject.
- [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) — source of the enabled `exa` codex plugin.
- [firecrawl/firecrawl-claude-plugin](https://github.com/firecrawl/firecrawl-claude-plugin) — source of the enabled `firecrawl` codex plugin.
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) — source of the enabled `last30days` codex plugin.
