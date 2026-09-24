# graphify operating guide (WORK IN PROGRESS — being written incrementally)

Installed version: `graphify 0.9.53` (both `uv run --project python graphify` and bare PATH `graphify`
resolve 0.9.53 as of 2026-09-02 — probe: `graphify --version` both ways).
Package source: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/lib/python3.14/site-packages/graphify`
(referred to below as `$GP`).

STATUS: skeleton written; sections filled in as probes complete.

---

## B. `graphify clone` vs `/graphify <url>` — ANSWER: use `graphify clone`, they are the SAME path

**They are not two paths. `/graphify <url>` *tells the agent to run* `graphify clone`.**

Evidence chain:

- `$GP/cli.py:1000` `def _clone_repo(url, branch=None, out_dir=None)` — the only clone
  implementation in the package.
- Call sites of `_clone_repo` (grep, control-armed against `_reenter_main` which correctly
  returned its 1 def + 1 call):
  - `$GP/cli.py:1000` — the definition
  - `$GP/cli.py:2755` — `local_path = _clone_repo(url, branch=branch, out_dir=out_dir)`,
    inside `elif cmd == "clone":` (`cli.py:2734`)
  - `$GP/__main__.py:123` — an **import re-export only**, not a call.
  So: exactly ONE caller, and it is the `clone` subcommand.
- The skill's Step 0 (`.claude/skills/graphify/SKILL.md:61-63`) does not clone anything itself —
  it defers to `references/github-and-merge.md`, whose Step 0 body is literally
  `LOCAL_PATH=$(graphify clone <github-url> [--branch <branch>])`.

**Verdict: invoke `graphify clone <url>` directly.** `/graphify <url>` is the same command with
9 more steps of prose wrapped around it.

### State it leaves (cleanup surface)

| Path | Written by | Notes |
|---|---|---|
| `~/.graphify/repos/<owner>/<repo>` | `clone` (default dest, `cli.py:1030`) | **shallow** (`git clone --depth 1`, `cli.py:1046`). Re-running `clone` on the same URL does `git -C <dest> pull` instead (`cli.py:1039-1041`) — it does NOT re-clone, so a stale clone silently persists. |
| `<repo>/graphify-out/` | later pipeline steps | lives inside the clone, so removing the clone removes it |
| `~/.graphify/global-graph.json` | ONLY if you pass `--global` to `extract`, or run `graphify global add` | opt-in; do not pass `--global` for a throwaway analysis |
| `~/.graphify/providers.json` | only `graphify provider add` | not touched by the analysis pipeline |

Cleanup for a throwaway third-party analysis is therefore one command:
`rm -rf ~/.graphify/repos/<owner>/<repo>`.

**Recommendation for this repo:** pass `--out` explicitly into the scratchpad rather than
accepting the `~/.graphify/repos/...` default, so the clone is session-scoped and cannot rot:

```bash
graphify clone https://github.com/<owner>/<repo> --out "$SCRATCH/<repo>"
```

Note `--branch` is validated against leading `-` (`cli.py:1032-1034`) but `--out` is not.

---

## E. The API-key / backend story, RESOLVED

### The contradiction dissolves: there are two extraction paths, not one

| Path | Who does the semantic extraction | Key needed? |
|---|---|---|
| **Agent-driven** — `/graphify <path>` skill, Steps 2-3 (`SKILL.md:107-392`) | **the host agent itself** reads the doc/image files and emits the extraction JSON | **No.** This is what `SKILL.md`'s "graphify needs no API key" means. |
| **Headless** — `graphify extract <path>` (`cli.py:3143-3144`: "calls extract_corpus_parallel directly using whichever backend has an API key set") | an LLM backend over the network | **Only if the corpus has non-code files.** |

### The exact rule (`cli.py:3616`)

```python
needs_llm = bool(semantic_files) or dedup_llm
```

`semantic_files = doc_files + paper_files + image_files` (`cli.py:3523`), classified by extension
in `detect.py:44-47`:

- **CODE** (local AST, never needs a key): `.py .ts .go .rs .java .c .cpp .rb .sh .sql .json .tf .hcl …`
- **DOC** → semantic: **`.md .mdx .qmd .skill .txt .rst .html .yaml .yml`**
- **PAPER** → semantic: `.pdf`
- **IMAGE** → semantic: `.png .jpg .jpeg .gif .webp .svg`

**`.md` and `.yaml`/`.yml` are DOC.** So virtually every real repo (README + CI yaml) has
`semantic_files != []` and therefore `graphify extract` **does** demand a backend. That is why
the observed behaviour is "hard-fails rc=1 with no key" — the no-key path is real but only
reachable on a pure-code corpus, or with `--code-only`.

Escape hatch, printed in the error itself (`cli.py:3635-3638`): `--code-only` drops the
doc/paper/image pass and needs no key at all (`cli.py:3528-3535` — it reports what it skipped
rather than silently dropping it).

### `detect_backend()` on THIS host: `gemini`, not bedrock — measured

`llm.py:3111-3141`, priority: `gemini → kimi → claude → openai → deepseek → azure → bedrock → ollama`.

Three-arm probe (2026-09-02), all three arms distinct so the probe discriminates:

| Arm | Command | Result |
|---|---|---|
| 1 — real env | `uv run --project python python -c "from graphify.llm import detect_backend; print(detect_backend())"` | **`gemini`** |
| 2 — `env -u GEMINI_API_KEY -u GOOGLE_API_KEY` | same | **`bedrock`** |
| 3 — arm 2 also minus `AWS_REGION`/`AWS_DEFAULT_REGION`/`AWS_PROFILE`/`AWS_ACCESS_KEY_ID` | same | **`None`** |

Presence-only env scan on this host (`${(P)v+x}` presence flags, no values printed):
`GEMINI_API_KEY` SET; `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID` all SET;
everything else absent.

**So the bedrock fall-through (`llm.py:3127-3128`, bare `AWS_REGION` is enough) is REAL but
currently MASKED by the gemini key.** It becomes live the moment `GEMINI_API_KEY` is absent —
e.g. inside a subprocess/container that does not inherit it. `cli.py:3665-3672` then sets
`allow_no_key = True` for bedrock on bare `AWS_PROFILE`/`AWS_REGION`/`AWS_DEFAULT_REGION`/
`AWS_ACCESS_KEY_ID`, so it will **proceed and try to call Bedrock** rather than erroring.

### THE RULE for choosing

1. **Prefer the agent-driven path** (`/graphify <path>` / the skill's Step 3): zero API spend,
   zero key, and the host agent is a better extractor than a cheap model.
2. **If you must run headless `graphify extract`, always pass `--backend` explicitly.**
   Never rely on auto-detect: here it silently resolves `gemini` (real money, real quota) and,
   in any environment without that key, silently resolves `bedrock`.
3. **For a pure structural map of a third-party repo, use `--code-only`.** No key, no spend,
   no network, and the AST graph is what `query`/`affected`/`god-nodes`/`path` actually traverse.
4. Only add the semantic pass when you specifically need the repo's *prose* (README/ADRs/specs)
   in the graph — and then decide the backend on purpose.

---

## F. Traps and footguns (measured 2026-09-02 against 0.9.53)

### F1 — REFUTED as briefed: `extract` on a FILE target does NOT write a 0-node graph at rc=0

All three file-target forms fail **loudly** at 0.9.53. Control arm in every case: the same file
inside a directory target extracts cleanly.

| Probe | Result |
|---|---|
| `graphify extract ./core.py --code-only` | `NotADirectoryError` traceback at `cli.py:3344` (`graphify_out.mkdir`), **rc=1**, no graph |
| `graphify extract ./core.py --code-only --out DIR` | warns "could not scan …", "found 0 code", "graph is empty — extraction produced no nodes", **rc=1**, **no graph written** |
| `graphify update ./core.py` | `NotADirectoryError` at `watch.py:182`, **rc=1** |
| CONTROL: `graphify extract . --code-only` (dir) | `5 nodes, 6 edges`, rc=0 |
| CONTROL: `graphify update .` (dir) | "Code graph updated", rc=0 |

⚠️ My first read of the `update` arm said rc=0 — that was `tail`'s exit code, because I piped it.
Re-run without the pipe: **rc=1**. Do not pipe a probe whose rc you intend to report.

**Still true and worth keeping:** always pass a DIRECTORY. The `--out` form is the dangerous one
in spirit — it gets far enough to create output dirs before discovering it has nothing.

### F2 — CONFIRMED and SHARPENED: `reflect` silently drops every lesson against the wrong graph

Mechanism, `cli.py:1499-1503`:

```python
graph_arg = opts.graph
if graph_arg is None:
    default_graph = Path(_GRAPHIFY_OUT) / "graph.json"
    if default_graph.exists():
        graph_arg = str(default_graph)
```

Omitting `--graph` does **not** run graph-less — it auto-attaches **`./graphify-out/graph.json`
relative to CWD**. Nodes absent from that graph are dropped (`reflect.py:390`, `reflect.py:211-220`).

Three-arm probe, same `--memory-dir`, two saved memories citing `Engine`/`orchestrate()`/
`helper()`/`.start()`:

| Arm | CWD graph | stdout | LESSONS.md |
|---|---|---|---|
| 1 — `--graph` correct | probe-repo | `Reflected 2 memories (2 useful, 0 dead ends, 0 corrected)` | **788 B**, all 4 nodes, grouped by community |
| 2 — auto-attach, disjoint corpus | a repo containing only `zzalpha()`/`zzbeta()` | **byte-identical line** | **388 B**, `## Lessons` → `_No marked outcomes yet._` |
| 3 — no graph anywhere | none | **byte-identical line** | 484 B, flat single section |

Three different documents; **one identical success message**. The summary counts memories *read*
(`agg['total']`, `cli.py:1529-1533`), never lessons *written*. Arm 2 even keeps
`Summary: 2 useful · 0 dead ends` while the Lessons body is empty.

⚠️ My first attempt at this probe was a **rigged fixture** — the "wrong" graph was a copy of the
right one, so all arms returned 788 B. A fixture has to admit both answers before the probe means
anything.

**Rule: always pass `--graph` explicitly to `reflect`, and never run it from a directory other
than the corpus root.**

### F3 — CONFIRMED: `--mode deep` is a separate cache namespace, so it re-dispatches everything

`cache.py:1250` — "``cache/semantic-{mode}/`` instead, so deep-mode results never shadow"; also
`cache.py:939`, `cache.py:1402`, `llm.py:2646`. A `--mode deep` run cannot read the standard
semantic cache and re-sends the whole corpus to the LLM. Budget it as a **full-price re-extraction**,
not an increment.

### F4 — NEW: auto-detected backend spends real money without saying which one it picked

`graphify extract` with no `--backend` resolves via `detect_backend()`. On this host that is
**gemini** (measured, section E). Nothing in the output asks for confirmation before dispatching
the corpus. Always pass `--backend` or `--code-only`.

### F5 — NEW: the skill's Step 1 will `uv tool install` graphify globally

`SKILL.md:86-95` runs `uv tool install --upgrade graphifyy -q` when `import graphify` fails for
its detected interpreter. Running the skill's literal Step 1 can therefore mutate the **user-global**
uv tool set behind this repo's pinned 0.9.53. Skip Step 1 entirely and use
`uv run --project python graphify` (see section G).

### F6 — NEW: `clone` reuses a stale shallow clone instead of re-cloning

`cli.py:1038-1044`: if the destination exists, it runs `git -C <dest> pull` and, on failure, prints
`warning: git pull failed` and **continues with the stale tree**. Combined with `--depth 1`
(`cli.py:1046`), a repeat run on a force-pushed repo can analyse an old commit while reporting
success. Pass `--out` into a fresh scratchpad dir per analysis.

### F7 — NEW: `export wiki` before labeling produces `Community 0` / `Community 1` articles

Measured: `cluster-only --no-label` leaves placeholders, and `export wiki` faithfully writes them
into `wiki/index.md` and every community article. The community NAME is most of the wiki's value to
an agent — generating the wiki before Step 5 labeling yields a navigational index with no semantics.
**Label first, export wiki second.**

### F8 — `--force` / `GRAPHIFY_FORCE=1` means two different things

On `update` it means "overwrite graph.json even if the rebuild has fewer nodes" (i.e. defeats a
safety check after a refactor deletes code). On `extract` it means "skip the incremental manifest
gate AND the semantic cache reads" — a full re-dispatch at full LLM price. Same flag name, same
env var, very different bills.

---

## A. The canonical pipeline for a cloned third-party repo

The skill's Steps 0-9 (`SKILL.md:61,65,107,147,151,393,456,482,532,552,558`) are confirmed as a
real sequence, but most of it is scaffolding for the *agent-driven* extraction path. Confirmed
against the CLI, the two useful sequences are much shorter.

### A key asymmetry I measured, which changes the recommendation

`update` and `extract` classify **markdown differently**:

| Same markdown-only corpus, all backend env vars stripped | Result |
|---|---|
| `graphify extract . --code-only` | "skipping 1 non-code file(s)", `found 0 code, 0 docs`, **graph is empty, rc=1** |
| `graphify update .` | **`Rebuilt: 4 nodes, 3 edges`, rc=0** — nodes are `DOC.md`, `Architecture`, `Ingest Layer`, `Storage Layer` |

`update` runs a **local markdown AST extractor** (`extractors/markdown.py`) that turns headings
into nodes, for free, with no key. `extract --code-only` throws that away because it classifies
`.md` as semantic (`detect.py:45`). So the free pipeline is `extract --code-only` **then**
`update .` — the second pass adds all the prose structure at zero cost.

### MINIMAL — zero API spend, zero key, ~seconds

```bash
SCRATCH=/private/tmp/.../scratchpad        # your session scratchpad
GFY="uv run --project /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python graphify"

$GFY clone https://github.com/<owner>/<repo> --out "$SCRATCH/<repo>"
cd "$SCRATCH/<repo>"
$GFY extract . --code-only                 # AST only -> graph.json + .graphify_analysis.json
$GFY update .                              # adds markdown structure, still no LLM
$GFY cluster-only . --no-label             # adds GRAPH_REPORT.md + graph.html
```

Then answer questions with `$GFY query "..." --budget 4000`.

### RECOMMENDED — the artifacts an agent actually navigates by

Same as above, plus the two steps that make the graph *semantic* rather than merely structural:

```bash
# 5. name the communities. Either:
#    (a) FREE — let the host agent do it (SKILL.md Step 5): read .graphify_analysis.json,
#        write 2-5 word names into graphify-out/.graphify_labels.json yourself; or
#    (b) PAID — one batched LLM call, backend named EXPLICITLY (never auto-detect):
$GFY label . --backend gemini --batch-size 100

# 6. the agent-facing artifact — MUST come after labeling (see trap F7)
$GFY export wiki                           # -> graphify-out/wiki/index.md + one article per
                                           #    community AND per god node

# 7. optional orientation
$GFY god-nodes --top 20 --json             # the load-bearing abstractions
$GFY benchmark                             # measures the actual token reduction you bought
```

**Only add the full semantic pass** (`extract .` without `--code-only`, an LLM reading every
README/ADR/spec) when you specifically need the repo's *prose claims* in the graph. It is the only
expensive step in the whole pipeline.

---

## C. Every subcommand, grouped by purpose

Two cost columns, because they are different questions: **$LLM** = network API spend;
**ctx** = tokens burned in the calling agent's context window.

### Build / extract

| Command | What it is for | $LLM | ctx |
|---|---|---|---|
| `extract <dir>` | headless full extraction for CI/scripts (`cli.py:3143`) | **YES** unless `--code-only` or a pure-code corpus (`cli.py:3616`) | low |
| `extract <dir> --code-only` | AST-only index of code; **no key, no network** (`cli.py:3528`) | no | low |
| `update <dir>` | re-extract code **and markdown** AST; "no LLM needed" — armed with every backend var stripped, rc=0 | **no** | low |
| `cluster-only <dir>` | re-run clustering on an existing graph + regenerate GRAPH_REPORT.md | **yes**, for community naming — unless `--no-label` | low |
| `label <dir>` | (re)name communities only; `--missing-only` fills gaps | **YES** (that is its whole job) | low |
| `add <url>` | fetch a URL into `./raw` and update the graph | yes (it is a doc) | low |
| `watch <dir>` | daemon: rebuild on file change | no (AST path) | n/a |
| `check-update <dir>` | cron-safe "is semantic re-extraction pending?"; silent + rc=0 when clean | no | ~0 |

### Query / inspect — **all deterministic, all zero API spend**

| Command | What it is for | ctx |
|---|---|---|
| `query "<q>"` | keyword-seeded BFS/DFS over graph.json; emits `NODE`/`EDGE` lines with `src=`/`loc=` | **capped by `--budget`** (default 2000) |
| `path "A" "B"` | shortest path between two nodes | tiny (1 line) |
| `explain "X"` | one node + its neighbours, by relation and direction | tiny |
| `affected "X"` | reverse traversal — blast radius (`--depth`, `--relation`) | small |
| `god-nodes` | most-connected nodes = architectural hubs; `--json` | tiny |
| `diagnose multigraph` | same-endpoint edge-collapse risk; integrity gate | small |
| `benchmark` | measures token reduction vs naive full-corpus read | tiny |
| `prs` | PR dashboard — **shells out to `gh`, makes network calls** | medium |

### Output / export — **all read graph.json, zero API spend** (measured: all rc=0 with no keys)

| Command | Produces | Audience |
|---|---|---|
| `export wiki` | `wiki/index.md` + article per community **and per god node** | **AGENT** (the tool itself prints "index.md -> agent entry point") |
| `tree` | `GRAPH_TREE.html`, D3 collapsible tree | human |
| `export html` | `graph.html` force-directed viz | human |
| `export callflow-html` | Mermaid architecture/call-flow HTML | human |
| `export obsidian` | vault of notes + `graph.canvas` | human (Obsidian) |
| `export svg` | `graph.svg` | human (embeds in READMEs) |
| `export graphml` | GraphML for Gephi/yEd | human/tooling |
| `export neo4j` / `falkordb` | Cypher, or push to a live DB | tooling |

### Memory / feedback loop

| Command | What it is for | $LLM |
|---|---|---|
| `save-result` | record a Q&A + `--outcome useful\|dead_end\|corrected` into `graphify-out/memory/` | no |
| `reflect` | aggregate those into a deterministic `LESSONS.md` ("Deterministic; no LLM") | no |

### Lifecycle

| Command | What it is for | Notes |
|---|---|---|
| `clone <url>` | shallow-clone a GitHub repo, print the path | see B |
| `merge-graphs <g1> <g2> …` | union several graph.json into one cross-repo graph | free |
| `merge-driver` | git merge driver for graph.json conflicts | free |
| `install` / `<platform> install` | write skill + rules + hooks into a platform's config | **BANNED here — see G** |
| `uninstall [--purge]` | remove from all detected platforms | destructive |
| `hook install/uninstall/status` | git post-commit/post-checkout hooks | |
| `global add/remove/list/path` | the cross-project graph at `~/.graphify/global-graph.json` | opt-in |
| `provider list/show/add/remove` | custom LLM providers | |

---

## D. Which artifacts actually reduce an agent's future token spend

The operator's goal is *"reduce context/tokens trying to navigate reviewing its code and
instructions."* Ranked for an **agent** consumer:

| Rank | Artifact | Why | Verdict |
|---|---|---|---|
| **1** | **`query` itself** (no artifact) | The only output that is *demand-driven* and *budget-capped*. `--budget N` is a hard cap; every line carries `src=<file> loc=<Lnn>`, so the agent reads 2 files instead of 40. Nothing else has a knob. | **The primary win.** |
| **2** | **`wiki/` (`export wiki`)** — but **only after labeling** | Markdown, small (my 8-node repo: `index.md` 695 B, community articles ~500 B, god-node articles ~300-400 B), and *hierarchical*: index → community → god node. An agent can read `index.md` alone (~700 B) and know what the repo is made of. Each god-node article lists connections grouped by relation with EXTRACTED/INFERRED provenance. | **Best static artifact.** Worthless before Step 5 (trap F7). |
| **3** | `god-nodes --top N --json` | Tiny, machine-readable, answers "what are the load-bearing abstractions" in ~40 tokens. Ideal first call. | keep |
| **4** | `GRAPH_REPORT.md` | ~1.4 KB. Genuinely useful sections an agent can act on: **God Nodes**, **Surprising Connections** (cross-file call edges with both paths), **Import Cycles**, **Knowledge Gaps**. Weaker sections: Suggested Questions. | keep, read once |
| **5** | `affected` / `path` / `explain` | Zero-cost targeted follow-ups once `query` has oriented you. `path` output is a single line. | keep |
| 6 | `.graphify_analysis.json` | Machine input for labeling; not for reading. | internal |
| — | `GRAPH_TREE.html` (15 KB) | **HUMAN ONLY.** D3 + inline JS; an agent reading it pays 15 KB to recover data already in graph.json. | do not feed to an agent |
| — | `graph.html` (20 KB), `callflow-html` (23 KB), `graph.svg` (24 KB) | **HUMAN ONLY**, same reason, worse ratios. | do not feed to an agent |
| — | **Obsidian vault** | **HUMAN ONLY.** 10 notes for an 8-node graph, content near-identical to `wiki/` but with `.canvas` positioning junk, `.obsidian/` config, and filenames containing `()` and `dot-` prefixes that are awkward to reference. **The wiki strictly dominates it for an agent.** | skip unless a human wants Obsidian |
| — | `graph.graphml`, `neo4j`/`falkordb` Cypher | tooling handoff, not agent reading | skip |

**Practical rule:** for an agent, generate **wiki + report + god-nodes**, then answer everything
else through `query`. Skip every HTML/SVG/vault export unless a human asked for a picture.

`graphify benchmark` will quantify it for the specific repo — on my toy corpus it reported
`3.6x fewer tokens per query`; on a real repo the ratio is far higher because the naive baseline
grows with the corpus while `--budget` does not.

---

## G. Analysing a FOREIGN clone without violating this repo's rules

### The two constraints

- `.claude/rules/graphify-first.md`: use `mise run graphify-query` / `graphify-update`, **never a
  bare `graphify` on PATH** — because two graphify installs exist on this machine and only the
  mise tasks resolve this repo's pinned 0.9.53.
- `.claude/rules/do-not.md` #8: **never bare `graphify install`**; any `graphify <platform> install`
  must run in a throwaway dir outside this repo.

### The mise tasks CANNOT be pointed at a foreign clone — measured

`python/src/dotfiles_setup/main.py:2436`:

```python
project_root = Path(__file__).parent.parent.parent.parent
```

`project_root` is derived from the **installed source file's location**, not from cwd, and there is
no `--root` flag on `dotfiles-setup` or on its `graphify` subparser (checked `--help` on both).
Every wrapper then resolves `<project_root>/graphify-out/graph.json` (`graphify.py:226,329,420`)
and runs with `cwd=project_root` (`graphify.py:338,425,548`).

**Empirical control arm:** run from `$SCRATCH/probe-repo`, whose own `graphify-out/graph.json` has
**8 nodes**, `dotfiles-setup graphify query "Engine"` reported *"showing 6 of 23 nodes"* — it
queried the **dotfiles graph (14,751 nodes)**, ignoring cwd entirely.

### The resolution: the rules do not conflict, because they are about different graphs

Both rules are scoped to **this repo's own graph and this repo's config**:

- `graphify-first.md` exists so *the dotfiles project graph* is always built and queried by one
  pinned binary. A foreign clone in the scratchpad has no such invariant to protect.
- `do-not.md` #8 forbids `install` because it **mutates `~/.claude` and appends to
  `AGENTS.md`/`CLAUDE.md`**. The analysis pipeline never calls `install`.

So: **analyse a foreign clone with the direct CLI, invoked through this repo's uv pin, from a
directory outside this repo.**

```bash
GFY="uv run --project /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python graphify"
cd "$SCRATCH/<repo>"          # NOT inside the dotfiles repo
$GFY extract . --code-only
```

Why this satisfies `graphify-first.md`'s actual intent: `uv run --project python graphify` resolves
`python/.venv/.../graphify` — **byte-identically the same binary the mise tasks run** (both go
through the same uv project pin; verified `graphify --version` → 0.9.53 on both paths). It is not
the user-global PATH shim the rule warns about. Do **not** type a bare `graphify`.

### Rules to keep while doing it

1. Never run any `install` / `<platform> install` / `hook install` / `graphify --watch`. If you ever
   need the skill surface *in this repo*, the sanctioned path is `mise run graphify-skill-install -- claude`
   (`mise.toml:748-757`), which never touches `$HOME` or `AGENTS.md`.
2. Never run `extract` / `update` / `cluster-only` with this repo as the target — it has a live
   `graphify-out/` (14,751 nodes) and the only sanctioned rebuild is `mise run graphify-update`.
3. Do not pass `--global` and do not run `graphify global add` — that writes
   `~/.graphify/global-graph.json`, polluting a shared file with a throwaway repo.
4. Clone with `--out "$SCRATCH/<repo>"` so cleanup is `rm -rf` of one scratchpad dir rather than
   pruning `~/.graphify/repos/`.
5. Skip the skill's Step 1 entirely — it will `uv tool install --upgrade graphifyy` globally
   (`SKILL.md:86-95`, trap F5).

---

## Appendix — probes run for this guide

All against 0.9.53 on 2026-09-02, in `$SCRATCH`, never against the dotfiles repo.

| Claim | Probe | Control arm |
|---|---|---|
| `clone` has one caller | `grep -rn '_clone_repo'` | `_reenter_main` → correctly 1 def + 1 call; fresh known-absent string `qplzmv7` → 0 |
| `detect_backend()` → gemini here | in-process import, 3 arms | arm2 (`env -u GEMINI*`) → `bedrock`; arm3 (also `-u AWS_*`) → `None` |
| no-key hard fail is doc-driven | `extract .` no keys → rc=1 naming "1 doc/paper/image file(s)" | `extract . --code-only` same env → rc=0, 8 nodes |
| file target fails loudly | 3 forms, all rc=1 | dir target → rc=0 |
| `reflect` drops silently | 3 arms, identical stdout | 788 B / 388 B / 484 B docs — **first fixture was rigged and gave 788/788; rebuilt with a disjoint corpus** |
| `update` is AST-only | every backend var stripped → rc=0 | tool prints "no LLM needed" + a "Tip: set GEMINI_API_KEY" hint |
| `update` indexes markdown, `extract --code-only` does not | markdown-only corpus, both commands, no keys | `extract` → 0 nodes rc=1; `update` → 4 nodes rc=0 (`DOC.md`, `Architecture`, `Ingest Layer`, `Storage Layer`) |
| mise wrapper is repo-pinned | `dotfiles-setup graphify query` from probe-repo | reported 23 matching nodes; probe-repo's whole graph is 8 |
| exporters need no key | wiki/obsidian/svg/graphml/tree/callflow | all rc=0 |

**Two of my own probes were broken and caught by their control arms:** a `$var` command string that
zsh did not word-split (rc=127 on all five exporters), and an `rc=$?` read after a `| tail` that
reported 0 for a command whose real exit was 1.

## GitHub repos touched

- [safishamsi/graphify](https://github.com/safishamsi/graphify) — the tool under study; read the
  installed 0.9.53 package source (`cli.py`, `llm.py`, `detect.py`, `reflect.py`, `cache.py`) and
  its packaged `SKILL.md` + `references/*.md`. URL taken from the generator footer graphify itself
  writes into `wiki/index.md`.
