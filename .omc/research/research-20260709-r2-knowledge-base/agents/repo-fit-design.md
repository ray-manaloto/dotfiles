# Run G / Angle 5 — Repo-fit synthesis: candidate KB architectures for THIS corpus

Analyst: repo-fit-design agent, 2026-07-09 (remote research container; Bash
blocked — all evidence via Read/Grep/Glob on the working tree and
WebSearch/WebFetch). Grounding:
`.omc/research/research-20260709-r2-inventory/report.md` plus the three
sibling Run-G angle reports (`agents/{graphify-deep,memory-field,industry-wiring}.md`),
which are cited below as persisted artifacts, with independent re-verification
of their load-bearing claims where this angle depends on them.

---

## Findings

### F1. Corpus characterization — four layers, bursty growth, half-built conventions

**Layer 1 — `.omc/research/**` (working research, per-clone-ignored on the Mac,
committable here).** This fresh clone holds only the current R2 round:
**36 markdown files** across 8 run directories (Glob `.omc/research/**/*.md`,
2026-07-09), structured as `research-20260709-r2-<domain>/{report.md,
synthesis-*.md, agents/*.md}`. Sampled artifact sizes: inventory report 133
lines, `memory-field.md` 206, `industry-wiring.md` 269, `graphify-deep.md` 275,
`full-secret-map.md` and `r2-topology/report.md` of comparable density
(evidence-table-heavy, ~150–400 lines). **Growth rate:** this one R2 round
produces ~42 files (7 domains × ~6 files); the previous day's unified-image run
on Ray's Mac was **104 agents** (inventory report:126-128). Growth is bursty —
tens of dense reports per research day, not a slow trickle.

**Layer 2 — `docs/research/**` (tracked).** Only **5 markdown artifacts**
(Glob), plus `trail/findings/` with 10 YAML + 2 JSON finding files from
2026-03, plus the **mintlify-cache**: 16 repos × (llms.txt + llms-full.txt),
whose llms-full line counts sum to **≈75,400 lines** (per the table in
`docs/research/mintlify-cache/README.md:42-59` — chezmoi alone is 22,330).

**Layer 3 — `.claude/rules/*.md`:** **18 distilled rule files** (Glob) — the
curated "lessons" tier.

**Layer 4 — OMC state:** `.omc/notepad.md`, `.omc/project-memory.json`
(per `omc-directory-conventions.md`).

**What already exists convention-wise** (this is the crucial repo-fit input):

- Cache-first grep is *mandated*, not habitual
  (`.claude/rules/research-doc-sources.md` step 0).
- Every artifact must end with a greppable `## GitHub repos touched`
  enumeration (`.claude/rules/research-repo-enumeration.md`) — verified
  present in **all 4** tracked `docs/research/*.md` artifacts (Grep
  `## GitHub repos touched`, 4 files matched).
- The external cache HAS an index (`docs/research/mintlify-catalog.md`), and
  its README even records per-file line counts + sha256s
  (`mintlify-cache/README.md:40-59`).
- Verbatim persistence at receipt is mandated
  (`.claude/rules/agent-report-persistence.md`), so the corpus will keep
  growing at full fidelity by rule.
- **The gap:** the *internal* corpus (research runs, tracked artifacts, trail
  findings) has **no index at all** — there is no single file an agent can
  grep to answer "which past report covered X?". The enumeration sections are
  a partial per-artifact index; `research-repo-enumeration.md` § Enforcement
  explicitly anticipates a future hk step for `docs/research/**/*.md` "when
  the first tracked research artifact lands" — that artifact landed
  (4 exist) and the step still doesn't.

**Enforcement infrastructure available to any candidate:** hk steps in
`hk.pkl` (`no_mcp_registration` at hk.pkl:301-303, `claude_md_size_limit`
:322, `claude_agents_md_pairs` :357) demonstrate the grep-shaped-check
pattern a corpus validator would reuse; the mise task surface has ~36 tasks
(Grep `^\[tasks\.` in mise.toml) including `lint-docs`; zero-bash-logic
(AGENTS.md § Agent Instructions) forces any generator into
`python/src/dotfiles_setup/`; `mise-tasks-only.md` requires a canonical task
per recurring workflow.

**Committability nuance that shapes every candidate:** `.omc/**` is NOT
gitignored in the repo (only `.omc/state/`; inventory report:112-116), so
research runs are committable to a branch — but on Ray's Mac they are
per-clone-excluded. Today there is therefore **no single canonical corpus
location**: the Mac's historical `.omc/research` (e.g. the 104-agent run) is
invisible to fresh clones. Any KB architecture must first decide the corpus
boundary; the cheapest durable answer is "promote keep-worthy run outputs
(report.md + synthesis) into `docs/research/runs/`, leave agent working files
per-clone."

### F2. Candidate A — conventions++: generated index + front-matter + machine-validated enumeration

**Design.**

1. **`docs/research/INDEX.md`** (and a per-clone `.omc/research/INDEX.md`),
   *generated*, in llms.txt shape — the format is a 5-element spec: H1,
   summary blockquote, optional prose, then H2 sections of one-line link
   entries `- [Link title](url): Optional link details`
   ([llmstxt.org](https://llmstxt.org/), fetched 2026-07-09). One line per
   artifact: title, date, run slug, one-sentence claim scope. This is exactly
   the mechanic the industry converged on for agent-facing doc access — "a
   hand-curated, one-line-per-entry markdown index at a stable path, with
   every leaf fetchable as clean markdown" (sibling `industry-wiring.md`
   finding 2, with Mintlify/Svelte/FastHTML evidence) — and it turns blind
   corpus-wide grep into a two-hop lookup: grep INDEX → Read artifact.
2. **Front-matter on new artifacts** (YAML: `date`, `run`, `status:
   working|tracked|superseded`, `topics: []`, `repos: []` mirroring the
   enumeration section) so the index generator and future tools parse
   metadata without heuristics. Added to the report template in the skills
   that launch research agents; old artifacts are grandfathered (generator
   falls back to H1 + path date).
3. **Generator + validator in `python/`** (zero-bash-logic):
   `dotfiles-setup research index` writes INDEX.md;
   `dotfiles-setup research validate` checks (a) every
   `docs/research/**/*.md` artifact ends with `## GitHub repos touched`
   (finally implementing the enforcement promised in
   `research-repo-enumeration.md` § Enforcement), (b) INDEX.md is fresh
   (regenerate-and-diff). Wired as `mise run research-index` (per
   `mise-tasks-only.md`) and as an hk step alongside `claude_md_size_limit`
   (same whole-tree grep idiom, hk.pkl:322) — CI-local parity for free.
4. **Rule patch:** `research-doc-sources.md` gains a step 0.5 — "grep the
   corpus INDEX before corpus-wide grep"; `agent-report-persistence.md`
   gains "regenerate the index in the same commit that adds an artifact."

**Costs.** Setup: one PR (~1 python module + tests + hk step + task + two
rule edits). Per-session tokens: INDEX at one line/artifact is ~50–100 lines
today, a few hundred at year-end — loaded only on demand, never always-on
(the Cursor "tier 4: manual" discipline, `industry-wiring.md` finding 3).
Runtime: zero LLM, zero network, zero new tools.

**Evidence base.** This is the architecture the strongest recent evidence
supports for exactly this workload: Anthropic's context-engineering doctrine —
verified by direct fetch 2026-07-09 — recommends agents "maintain lightweight
identifiers (file paths, stored queries, web links, etc.) and use these
references to dynamically load data into context at runtime", names
structured note-taking (a NOTES.md the agent maintains) as the memory
primitive, and describes Claude Code's hybrid as "CLAUDE.md files are naively
dropped into context up front, while primitives like glob and grep allow it
to navigate its environment"
([anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
Both leading agentic-coding vendors abandoned pre-built retrieval indexes for
live search (`industry-wiring.md` finding 1: Cherny/Claude Code, Sourcegraph
Cody), and the grep-vs-vector papers land the same way for agentic harnesses
(`memory-field.md` F3: [arXiv:2605.15184](https://arxiv.org/abs/2605.15184)
"grep generally yields higher accuracy than vector retrieval";
[arXiv:2602.23368](https://arxiv.org/abs/2602.23368) keyword-agentic ≈ ">90%
of the performance" of RAG, best where updates are frequent — this corpus
changes every session).

**Failure modes.** (a) Synonym/conceptual misses remain — grep finds "sshd"
but not "remote login daemon"; unmitigated except by index descriptions and
consistent slugs; semtools is the named escape hatch (F4). (b) Cross-corpus
thematic synthesis ("recurring failure modes across all runs?") stays manual —
that is candidate B's slot. (c) Index staleness — mitigated by making the
validator an hk/lint gate, not a convention. (d) Corpus-boundary ambiguity
(F1) — the index makes it visible but doesn't fix it; the promote-to-tracked
decision is prerequisite work.

**Rules fit: perfect.** No MCP anywhere; generator in python (zero-bash-logic);
canonical mise task; hk validation mirrors existing steps (ci-local-parity);
no new tool pins; it *completes* an enforcement gap two rules already
describe.

### F3. Candidate B — graphify-as-synthesizer: periodic LLM graph builds, committed artifacts, grep-first retrieval unchanged

**Design.** On a cadence (after each research run, or monthly), on the Mac
(the `/graphify` skill is user-level, absent in the remote container —
inventory report:109-111): run graphify over `docs/research/` +
`.omc/research/` with `--update` (incremental SHA256 caching re-extracts only
changed files), **excluding `mintlify-cache/`** (≈75k lines of third-party
docs would dominate the LLM semantic pass for zero synthesis value —
`graphify-deep.md` §10). Commit outputs to `docs/research/graph/`:

- `GRAPH_REPORT.md` — god nodes, surprises, suggested questions: the
  human/agent-greppable synthesis artifact;
- `graph.html` — self-contained interactive community map;
- `graph.json` — verified safe to commit: "keys are stored as relative paths
  and re-anchored on load, so committing it is safe and avoids a full rebuild
  on first checkout", with a git **union-merge driver** for parallel commits
  (README fetched from
  [Graphify-Labs/graphify@v8](https://raw.githubusercontent.com/Graphify-Labs/graphify/v8/README.md),
  2026-07-09).

Day-to-day retrieval stays grep (+ INDEX from candidate A). Escape hatches
that cost nothing to keep available: `graphify query/path/explain` are
**deterministic local BFS/DFS with no LLM round-trips and a configurable
token budget** (`graphify-deep.md` §5, serve.py evidence; `--budget` flag
confirmed in README fetch), and the stdio one-shot MCP fits the mcp2cli
process-spawn shape if ever wanted. The `save-result`/`reflect` work-memory
loop (`graphify-deep.md` §6) is a later opt-in, not part of this candidate.

**Why periodic-synthesis is the economically correct slot:** Microsoft's own
trajectory — full GraphRAG's LLM-priced indexing → LazyGraphRAG at "0.1% of
the costs of full GraphRAG" by deferring LLM synthesis
([Microsoft Research blog, 2024-11-25](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/),
via `industry-wiring.md` finding 5). Graph value concentrates in
global/thematic questions; putting an LLM-built graph in the hot retrieval
path buys the staleness+cost profile the field just walked away from.

**Costs.** Setup: near-zero tool cost (skill already installed user-level) +
one thin `mise run research-graph` wrapper + a scope/exclude config. Build
cost: the markdown corpus is 100% LLM-extracted (no tree-sitter fast path);
the **`claude-cli` backend runs on Ray's subscription with no API key**
(README fetch: "Claude CLI (claude-cli): No API key; uses your Claude
subscription") — consistent with the repo's deliberate absence of
`ANTHROPIC_API_KEY` (`full-secret-map.md` F1). No published per-MB markdown
cost exists; graphify's own `cost.json` reports actuals per run
(`graphify-deep.md` §7), so a single pilot yields the real number.

**Failure modes / risks.** (a) **Maturity:** repo is ~3 months old, pre-1.0
(v0.9.x), ~157 releases at daily-ish pace, format-compat shims, one dominant
maintainer (`graphify-deep.md` §9) — a committed graph.json may need rebuilds
across upgrades. Mitigation: the *committed artifacts are plain md/html/json*;
exit cost is ~zero (delete `docs/research/graph/`, nothing else changes).
(b) **Mac-only cadence:** the claude-cli backend + user-level skill mean
synthesis can't run in CI/remote without introducing an API key the repo
deliberately doesn't have. Cadence is therefore manual/local — acceptable for
monthly, fragile for "after every run". (c) Query quality on 100%-prose
corpora is untested (`graphify-deep.md` uncertainties). (d) Repo-hygiene:
graph.html/graph.json are generated blobs in a repo whose hooks fight
generated drift; the union-merge driver needs a `.gitattributes` entry —
small but real friction.

**Rules fit: good.** CLI-only, no registration (three registration-free
paths, `graphify-deep.md` §10); wrapper task satisfies mise-tasks-only;
`tool-currency-and-native-first` requires the written justification — which
is exactly "grep cannot do cross-corpus thematic synthesis; LazyGraphRAG
economics say do it periodically."

### F4. Candidate C — queryable-KB adoption (basic-memory / cognee / semtools), CLI-only

**basic-memory** is the strongest variant. Verified via docs fetch
(2026-07-09, [docs.basicmemory.com CLI reference](https://docs.basicmemory.com/raw/reference/cli-reference.md)):
`bm project add research ~/…/docs/research` + `bm reindex --search` indexes
**pre-existing plain markdown with no special format required**; retrieval is
`bm tool search-notes "query"` (keyword FTS default, `--hybrid`/`--vector`
optional local semantic modes — a newer capability than the sibling
`memory-field.md` snapshot recorded) and `bm tool read-note`; **no LLM key
for core operations**; the store of record stays the markdown files, so exit
risk ≈ zero. Fit with no-registration is native (real CLI, no MCP needed).
Costs: a new tool pin; an index (SQLite) to keep fresh (`bm sync`/`bm status`
in a mise task); and — the real cost — a **second retrieval surface competing
with the machine-cultured grep-first chain**: `research-doc-sources.md` would
need a defined slot ("when does `bm` beat grep?") or agents will use it
inconsistently.

**cognee**: `cognee-cli` with v1.0 `remember/recall` verbs exists
([docs.cognee.ai/cognee-cli/overview](https://docs.cognee.ai/cognee-cli/overview));
notably the vendor's own thesis piece — ["Agents Don't Need Another Protocol.
They Need a Good CLI."](https://www.cognee.ai/blog/deep-dives/agents-dont-need-a-protocol-they-need-a-cli)
— independently endorses this repo's CLI-not-MCP stance. But it requires an
LLM key (absent by design here), a deliberate Extract-Cognify-Load build step
per corpus change, and dev-suffixed versions (`memory-field.md` F1/F4).

**semtools** (the minimal C): local model2vec embeddings, no key, no server,
unix-piped CLI an agent calls exactly like grep (`memory-field.md` F4/F1) —
adoptable in an afternoon *when a trigger fires*, with zero architectural
change.

**Why C is not now:** there is no evidence any of these beats grep on a
technical-markdown corpus of this size (`memory-field.md` F2: no benchmark
measures this workload; the conversational-memory benchmarks are broken as
decision inputs — Zep's corrected LoCoMo run had the **full-context baseline
(~73%) beating mem0's best (~68%)**,
[getzep blog](https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)).
Adopting a duplicative retrieval tool without a demonstrated grep failure
violates the spirit of `use-tool-builtins.md` /
`tool-currency-and-native-first.md` rule 6 (custom/extra machinery must carry
a written justification that a need exists).

### F5. Comparison table

| | A conventions++ | B graphify-as-synthesizer | C queryable KB (bm/cognee/semtools) |
|---|---|---|---|
| Setup cost | 1 PR (python module, hk step, task, rule edits) | ~0 tool install (skill exists) + wrapper task + pilot run | tool pin + index lifecycle task + rule surgery for a 2nd retrieval surface |
| Per-session token cost | 2-hop: grep INDEX (~50–100 lines) → Read artifact | unchanged (grep) + GRAPH_REPORT.md greppable; optional budgeted deterministic query | 1 CLI call/answer; results compact, but agents must learn when to use it |
| Recurring $ cost | zero | LLM build pass per cadence (claude-cli backend = subscription, no key); unknown per-run $ until pilot (cost.json) | bm/semtools: zero; cognee: LLM key required (design conflict) |
| Freshness | generated at commit time, hk-gated | stale between runs by design (synthesis, not retrieval) | index staleness unless sync is task-wired |
| Failure modes | synonym misses; no thematic synthesis | pre-1.0 churn; Mac-only cadence; prose-corpus quality untested | duplicative surface; unproven gain; (cognee) key requirement |
| no_mcp_registration | trivially clean | clean (CLI; stdio one-shot fits mcp2cli) | clean for bm/semtools/cognee-cli |
| mise-tasks-only / zero-bash-logic | native fit (dotfiles-setup subcommand) | thin wrapper task, logic stays in the tool | wrapper tasks fine; index-lifecycle logic → python |
| Exit cost | none (it's just markdown) | delete docs/research/graph/ | delete index; files untouched (bm) |

### F6. Recommendation — A now; B as a gated pilot with a fixed cadence; C deferred with a named trigger

**Adopt A (conventions++) as THE knowledge-base architecture.** It is the
evidence-backed default (Anthropic doctrine + both vendors' abandonment of
indexes + the grep papers), it costs one PR, it completes enforcement gaps
two existing rules already promise, and every heavier option benefits from it
existing first (a scoped, indexed, front-mattered corpus is also the ideal
graphify ingest input and the ideal `bm project add` target).

**Pilot B (graphify) in its economically correct slot — periodic synthesis —
and gate continuation on the pilot's numbers.** One local run over the
(indexed, mintlify-cache-excluded) corpus; read `cost.json` and judge
GRAPH_REPORT.md against ~10 real "what connects / what recurs" questions the
INDEX can't answer. If useful and affordable: `mise run research-graph`,
monthly or post-run, outputs committed under `docs/research/graph/` and
listed in INDEX.md. If not: drop with zero residue. Do **not** wire graphify
into the hot retrieval path regardless of pilot outcome (LazyGraphRAG
lesson).

**Defer C with a written trigger** (recorded in the rule edit): "when the
miss-log shows grep+INDEX failing on ≥N synonym/conceptual queries per month,
adopt semtools first (no key, afternoon-scale); consider basic-memory only if
wikilink traversal/typed relations become a wanted authoring convention."
Reject mem0 (wrong workload), defer graphiti (heaviest infra, no CLI) — per
`memory-field.md` verdicts, which this angle's independent probes support.

**Migration sketch (ordered, each step independently valuable):**

1. **Corpus boundary decision** (needs Ray, per `clarify-before-acting.md`):
   promote durable run outputs (`report.md`, `synthesis-*.md`) to
   `docs/research/runs/<run-slug>/`; agent working files stay in
   `.omc/research/` (committable-on-branch). This gives the KB one canonical,
   clone-portable corpus.
2. **PR 1 — candidate A:** `python/src/dotfiles_setup/research_index.py`
   (+ tests); `dotfiles-setup research index|validate`; `mise run
   research-index`; hk step `research_enumeration` (grep-shaped, same idiom
   as hk.pkl:322) validating enumeration sections + index freshness on
   `docs/research/**/*.md`; llms.txt-shaped `docs/research/INDEX.md`;
   front-matter template into the research-agent prompt/skill; rule edits
   (`research-doc-sources.md` step 0.5, `agent-report-persistence.md` index
   duty, `research-repo-enumeration.md` enforcement section updated from
   "planned" to "live").
3. **Pilot — candidate B** (Mac, manual): scoped graphify run, commit
   artifacts + cost evidence to the run report, go/no-go per F6 gate; if go,
   PR 2 adds `mise run research-graph` + `.gitattributes` union-merge entry
   + INDEX entries for graph artifacts.
4. **Standing review:** fold "prune stale INDEX entries + rules" into the
   existing tool-currency cadence (Anthropic recommends config review every
   3–6 months; `industry-wiring.md` finding 3).

**The specialized agent that reads/writes this KB** (the domain deliverable's
shape, from this angle's view): a `research-librarian` role invoked at (i)
artifact-persist time — write front-matter, append enumeration, regenerate
INDEX (mechanical, no LLM judgment beyond a one-line description); (ii)
retrieval time — two-hop INDEX-grep→Read, falling back to corpus grep, never
loading more than the artifacts a question names; (iii) synthesis time
(cadence) — seed load = `INDEX.md` files + previous `GRAPH_REPORT.md` +
`.omc/notepad.md` (a few hundred lines total, versus dozens of full reports),
then drive the graphify run and distill anything durable into
`.claude/rules/` per the existing curation pipeline.

## Uncertainties / gaps

- **Graphify build cost on THIS corpus is unmeasured** — no per-MB markdown
  figure exists; the pilot's `cost.json` is the only way to get it. The
  go/no-go threshold is a judgment call for Ray.
- **Corpus-boundary decision is unresolved** (F1): index coverage of the
  Mac-only historical `.omc/research` runs depends on step 1 of the
  migration; without it the KB indexes only what a given clone can see.
- **basic-memory's `--hybrid`/`--vector` modes**: verified to exist in the
  CLI reference, but whether they need a local embedding model download or
  external service was not probed; immaterial while C is deferred.
- **Grep's degradation threshold** (corpus size / synonym density at which
  the miss-log trigger would fire) has no published boundary
  (`memory-field.md` uncertainties); the trigger is therefore observational,
  not predictive.
- **Token-cost figures for the INDEX two-hop pattern are estimates** (line
  counts of the index), not measured session telemetry; the Milvus critique
  of grep token-burn was never tested at this corpus scale
  (`industry-wiring.md` uncertainties).
- **Sibling-report dependence:** maturity numbers (graphify stars/releases,
  candidate-tool stats) are taken from the persisted sibling artifacts dated
  2026-07-09/10; this angle independently re-verified graphify's
  committable-graph/backends claims and basic-memory's CLI claims, but not
  the star counts.
- The claude-plugins-community angle (#3 of this run) had not landed at
  write time; if it surfaces a maintained knowledge-graph plugin with a
  CLI-only surface, it would slot into the C comparison, not change the A/B
  recommendation.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — corpus characterization, rules, hk.pkl steps, mise tasks, mintlify catalog/cache, sibling Run-G reports (all read from the working tree).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — README @ v8 fetched raw: committable graph.json, union-merge driver, CLI commands, claude-cli no-key backend, query budget flag.
- [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) — docs.basicmemory.com llms.txt + CLI reference: plain-markdown indexing, `bm tool search-notes`, no-key core ops, hybrid/vector modes.
- [topoteretes/cognee](https://github.com/topoteretes/cognee) — cognee-cli overview + vendor "CLI not protocol" blog via search.
- [AnswerDotAI/llms-txt](https://github.com/AnswerDotAI/llms-txt) — llmstxt.org format spec for the INDEX.md shape.
- [getzep/graphiti](https://github.com/getzep/graphiti) — deferred-candidate facts relied on via the persisted sibling memory-field report (not independently re-probed this pass).
- [mem0ai/mem0](https://github.com/mem0ai/mem0) — rejected-candidate facts relied on via the persisted sibling memory-field report (not independently re-probed this pass).
- [run-llama/semtools](https://github.com/run-llama/semtools) — escape-hatch candidate facts via the persisted sibling memory-field report.
- [microsoft/graphrag](https://github.com/microsoft/graphrag) — LazyGraphRAG cost lesson (Microsoft Research blog) anchoring the periodic-synthesis slot for candidate B.
