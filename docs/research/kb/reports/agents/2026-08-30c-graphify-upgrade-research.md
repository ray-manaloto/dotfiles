# Graphify upgrade research (0.9.42 -> 0.9.53)

Session 2026-08-30. Read-only research; no repo file modified except this one. No
`graphify install`/`graphify codex install` was run anywhere inside
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`. All installer behaviour below
was established by reading the installed package's own source
(`python/.venv/lib/python3.14/site-packages/graphify/install.py`, pinned
`graphifyy==0.9.42`, byte-for-byte the version this repo currently runs) plus
PyPI/GitHub metadata for 0.9.43-0.9.53. Where 0.9.53's `install.py` could not be
fetched (no network access to a running 0.9.53 install; only its GitHub *release
notes* were reachable), that gap is called out explicitly per question.

## Q1 — correct install/update mechanism for both surfaces (Claude + codex/agents)

`graphify install --help` (0.9.42, this repo's venv) advertises 18 platforms,
including `claude`, `codex`, and `agents` as three **distinct** targets:

```
Usage: graphify install [--project] [--strict] [--platform P|P]
Platforms: claude, codex, opencode, kilo, aider, copilot, claw, droid, trae,
trae-cn, hermes, kiro, pi, codebuddy, antigravity, antigravity-windows,
windows, kimi, amp, agents, devin, gemini, cursor
```

Reading `graphify/install.py`'s `_PLATFORM_CONFIG` dict (the ground truth, more
current than any doc) gives the exact write targets, project-scoped
(`--project`) since that is the only mode the hard constraint permits here:

| Platform | Skill file written | Registers in |
|---|---|---|
| `claude` | `.claude/skills/graphify/SKILL.md` + `.claude/skills/graphify/references/*.md` (progressive bundle `"claude"`) + `.claude/skills/graphify/.graphify_version` | `.claude/CLAUDE.md` (`claude_md: True`) |
| `codex` | `.codex/skills/graphify/SKILL.md` + `.codex/skills/graphify/references/*.md` (bundle `"codex"`) + `.codex/skills/graphify/.graphify_version` | nothing (`claude_md: False`) |
| `agents` | `.agents/skills/graphify/SKILL.md` (project) / `~/.agents/skills/graphify/SKILL.md` (global) + references (bundle `"agents"`) + `.graphify_version` | nothing |

Two facts settle "what is correct" precisely:

1. **`codex` and `agents` are NOT the same platform, and neither writes to
   `.agents/`, except `agents` itself.** `codex install` writes to
   `.codex/skills/graphify/`, a path this repo does not have at all. The
   `.agents/skills/graphify/` directory that exists in this repo is the
   **`agents` platform's own output location** — not a generic "everything
   that isn't Claude" bucket, and not what a `codex install` would produce.
2. **Every platform, including `agents`, gets a `.graphify_version` stamp
   unconditionally** — `_copy_skill_file()` (`install.py:183-239`) writes
   `(skill_dst.parent / ".graphify_version").write_text(__version__, ...)`
   with no platform-specific opt-out. So "does this platform get a version
   stamp" is not a question the tool answers differently per platform at
   install time (see Q3 for the *refresh* asymmetry, which is different).

**On `--project`, and the hard-constraint's continued accuracy at 0.9.53:**
`graphify install --help` and `install.py` both confirm `--project` is a real,
first-class flag — `install(platform, *, project: bool, project_dir)` branches
on it throughout `_platform_skill_destination`, and a project install prints a
`git add` hint instead of touching `$HOME`. So the constraint in
`do-not.md` item 8 that global-scope install pollutes `~/.claude` is **accurate
and still the default** (`install(platform: str = "claude", ...)` defaults
`project=False`), but the workaround it prescribes ("run in a throwaway
directory outside this repo") is **stronger than necessary for the `claude` and
`agents` platforms specifically**: `graphify install --project --platform
claude` (or `agents`) run from *inside* this repo's root would write only
under `./`, matching exactly what the current `.claude/skills/graphify/` tree
already looks like (see Q2). The rule's caution is warranted for the *default*
invocation (bare `graphify install` / `graphify codex install`, which mutate
`~/.claude` or append to a root `AGENTS.md`), not for every invocation of the
tool. I could not run `graphify install --project` here myself to prove the
project-scoped path is side-effect-free beyond `./` — that would itself be
running the installer in this repo, which the mandate forbids — so this is a
source-code-verified claim, not an executed one.

I was not able to fetch 0.9.53's actual `graphify/install.py` (no PyPI wheel
extraction attempted beyond metadata, per the read-only mandate and effort
budget) to diff it against 0.9.42's. The 0.9.53 CHANGELOG (Q6) directly patches
this exact file twice — 0.9.44/0.9.45 change version-stamp refresh behaviour,
and 0.9.53 changes `graphify install`'s overwrite-safety — so the platform
table above is confirmed accurate for 0.9.42 and very likely stable in shape at
0.9.53 (same platform names, same directories), but two specific *behaviours*
inside `_copy_skill_file`/`_refresh_all_version_stamps` have changed; see Q3
and Q6.

## Q2 — is the current manual-copy approach correct?

**Verdict: `.claude/skills/graphify/` is genuine (if slightly modified)
installer output; `.agents/skills/graphify/` is NOT installer output at all —
it is a hand-authored wrapper.** These are two different situations and the
repo owner's suspicion is right about the second one, not really about the
first.

Evidence:

- `diff <(package skill.md) .claude/skills/graphify/SKILL.md` → **2 lines**
  different (one extra `raise SystemExit(1)` line, added deliberately per
  commit `9502422`'s message: *"graphify SKILL.md: raise SystemExit(1) when
  to_json refuses the shrink..."*). Otherwise byte-identical to the packaged
  `skill.md` for platform `claude`.
- `diff -rq <(package skills/claude/references) .claude/skills/graphify/references`
  → **zero differences**. The references sidecar is byte-identical to what
  `graphify install --platform claude` ships at 0.9.42.
- So `.claude/skills/graphify/` **is** the real installer's output for the
  `claude` platform, with one intentional one-line patch layered on top after
  the fact. That is a reasonable, defensible shape: install once (presumably
  via the throwaway-directory workaround, then copied in — or via a
  since-superseded in-repo run before the `do-not.md` rule existed, see the
  commit history below), patch narrowly, track the patch in the commit
  message. It is fragile only in that a raw re-install would silently drop
  the one-line patch — worth a comment in the file itself, which it currently
  lacks.
- `diff <(package skill-agents.md) .agents/skills/graphify/SKILL.md` → **730
  line diff**. The repo's `.agents/skills/graphify/SKILL.md` is 1043 bytes and
  reads *"Use the repository's reviewed tasks... Detailed upstream workflows
  remain in the generated Claude reference tree under
  `.claude/skills/graphify/references/`"* — this is a **repo-authored
  redirector**, not `agents`-platform installer output at all. It never went
  through `graphify install --platform agents`.

So the "manual copy" the repo owner suspects is real, but it is not a copy of
installer output — it is a from-scratch file that happens to *point at* the
real installer output living under `.claude/`. That is a defensible design
choice (one canonical reference tree, thin redirectors elsewhere) **provided
it is deliberate and documented**, but as shipped it is invisible: nothing
marks `.agents/skills/graphify/SKILL.md` as "hand-authored, not
installer-managed," so a future `graphify install --project --platform agents`
run would silently clobber it with the real 730-line `skill-agents.md`, and
nobody reading the file today would know to expect that.

## Q3 — why does .claude/ lack .graphify_version while .agents/ has it?

**This is a repo decision, not upstream behaviour**, and it is visible
directly in `.gitignore:67-69`:

```
# graphify per-install state (generated by `graphify install`/runs; not source)
.claude/skills/graphify/.graphify_version
.claude/skills/**/.graphify_root
```

`.claude/skills/graphify/.graphify_version` **is gitignored**. It almost
certainly exists on disk locally (the installer writes it unconditionally per
Q1) but is deliberately excluded from git, so it never appears in `git log`
or a fresh clone. `.agents/skills/graphify/.graphify_version` is **not**
gitignored and was added in the same commit
(`9502422`, "Upgrade Graphify to 0.9.42 (#748)") that added
`.agents/skills/graphify/SKILL.md` — both committed as source, containing the
literal string `0.9.42`.

Given Q2's finding that `.agents/skills/graphify/SKILL.md` was never produced
by the real `agents`-platform installer, its `.graphify_version` file is
equally hand-authored: a plain text file someone wrote (or a script wrote) to
record "this hand-maintained redirector is meant to track pin 0.9.42," not a
stamp `_copy_skill_file()` ever touched. So the asymmetry has two independent
causes layered together: (a) `.claude`'s real stamp is intentionally
gitignored as install-local state, and (b) `.agents`'s stamp is not a real
install stamp at all, it's a tracked marker the repo owner (or a prior
session) wrote by hand to shadow the pin.

**One upstream fact is relevant here and changes at 0.9.45+, not before:**
0.9.42's `install.py` has `_refresh_all_version_stamps()`
(`install.py:58-68`), called after every non-project install, which rewrites
`.graphify_version` for **every previously-installed platform whose skill file
still exists** — even platforms not touched by the current run — using the
*current* runtime's `__version__`. The 0.9.45 release notes (Q6) record this
as a bug and fix it: *"`graphify install <platform>` now advances the
`.graphify_version` stamp only for the platform it actually (re)writes,
instead of stamping every installed platform as current... (#2694)"*. At
0.9.42 (this repo's pin) the bug is present but inert for project-scoped
installs specifically, because `_refresh_all_version_stamps()` calls
`_platform_skill_destination(name)` **without `project=True`**, which resolves
to the *global* (`Path.home()`) destination for every platform — so a
project-scoped `.claude/` or `.agents/` stamp was never in this refresh's
blast radius at 0.9.42 regardless. This matters for the upgrade (Q8): after
bumping to 0.9.53, the fixed, narrower stamp-refresh behaviour applies, which
is strictly safer and requires no compensating action.

## Q4 — how does knowledge-base sibling repo manage graphify skills?

**Per the explicit instruction, this is reported, not adopted as
authoritative — and it should not be, because it differs from this repo in a
load-bearing way that needs its own scrutiny before anyone copies it.**

- `~/dev/github/ray-manaloto/knowledge-base/pyproject.toml:32` pins
  `"graphifyy[all]==0.9.50"`, but `pyproject.toml:238` overrides the source
  entirely: `graphifyy = { git = "https://github.com/ray-manaloto/graphify",
  rev = "0a2eb5fdd3110b821bc4fa2759bc964a8bc0a956" }` — **a private fork**
  (`ray-manaloto/graphify`, not `Graphify-Labs/graphify`), pinned by commit
  SHA, not a PyPI release. That is a materially different supply chain from
  this repo's plain `graphifyy[all]==0.9.42` PyPI pin, and it means "what
  0.9.50 does" in KB is not necessarily what PyPI's 0.9.50 does — the fork
  could carry patches PyPI's tagged release doesn't have, or vice versa.
- KB does have both `.claude/skills/graphify/` and `.agents/skills/graphify/`
  directories, plus its own `python/src/kb_setup/graphify_env.py`,
  `graphify_sdk.py`, `graphify_baseline.py`, `skill_refresh.py` — a
  substantially larger custom wrapper layer than this repo's single
  `graphify.py`. I did not read these files (out of scope for the effort
  budget here and explicitly not this lane's job to validate KB's internals),
  so I cannot say whether KB's larger wrapper is well-founded or itself
  compounds the same class of problem this report found in Q7 (a local
  schema/version assumption drifting from upstream). Flagging it as an open
  question rather than asserting either way.
- KB uses `graphify save-result` / `graphify reflect` for real: its
  `graphify-out/memory/` directory holds **dozens** of dated `query_*.md`
  files (e.g. `query_20260826_200608_what_did_the_2026_08_26_graphify_coverage_round_le.md`),
  which is live evidence of Q5's memory feature actually being exercised in
  that repo — this dotfiles repo has no `graphify-out/memory/` directory at
  all, so it has never used the feature.
- **Verdict: partially correct, not a template to copy blind.** The
  fork-pinned dependency is a deliberate, larger commitment than this repo has
  made and would need its own justification (why not track PyPI?) before
  dotfiles adopted it. The skill-directory *shape* (`.claude/` +
  `.agents/`) matches this repo's shape, which is weak positive evidence the
  two-directory pattern itself is intentional across both repos — but KB's
  `.agents/skills/graphify/` still needs the same "is this real installer
  output or a hand-authored redirector" check this report ran for dotfiles
  (Q2); I did not run that diff against KB's files.

## Q5 — graphify memory feature at 0.9.53

**A real, dedicated feature exists — this is not "describing something
adjacent."** From `graphify --help` (0.9.42, and named in the 0.9.53-current
`references/query.md` bundle installed under `.claude/skills/graphify/references/`,
so the feature is current, not deprecated):

```
save-result   save a Q&A result to graphify-out/memory/ for graph feedback loop
  --question Q --answer A --type T (query|path_query|explain)
  --nodes N1 N2 ... --outcome O (useful|dead_end|corrected)
  --correction TEXT --memory-dir DIR  (default: graphify-out/memory)

reflect       aggregate graphify-out/memory/ outcomes into a deterministic lessons doc
  --memory-dir DIR --out FILE (default: graphify-out/reflections/LESSONS.md)
  --graph PATH --analysis PATH --labels PATH
  --half-life-days N (default 30)  --min-corroboration N (default 2)
```

Reading `graphify/reflect.py` (installed 0.9.42) confirms the mechanics:
`save-result` writes one Markdown doc per Q&A into `graphify-out/memory/`
(`parse_memory_doc`/`load_memory_docs` read them back by globbing `*.md`,
sorted by date). `reflect` aggregates every doc under `memory_dir`, applies a
**time-decay weight that halves every `half_life_days`** (`_decay`, default
30 days) and a **corroboration threshold** (`min_corroboration`, default 2
independent "useful" results before a lesson is trusted, `_finalize_sources`)
against the *current* graph's community structure, and writes a deterministic
`graphify-out/reflections/LESSONS.md`.

Answering the specific sub-questions:

- **Exact CLI**: `graphify save-result --question ... --answer ... --outcome
  useful|dead_end|corrected [--correction TEXT] --nodes N1 N2 ...` then later
  `graphify reflect`.
- **Where it persists**: flat Markdown files under `graphify-out/memory/`
  (project-relative, override via `--memory-dir`), aggregated output at
  `graphify-out/reflections/LESSONS.md`.
- **Per-project**: yes — it's scoped to whatever `graphify-out/` the command
  is run against; nothing global.
- **Survives a graph rebuild**: the memory *files themselves* are untouched by
  `graphify update`/`extract` (they live in a sibling directory, `memory/`,
  not `graph.json`), so a rebuild does not delete them. But `reflect`'s
  aggregation is graph-aware — it takes `--graph`/`--analysis`/`--labels` to
  group lessons by *current* community structure and, per the `reflect`
  helptext and `LESSONS.md`'s design, drops stale nodes no longer in the
  graph. So the raw memory survives a rebuild; the *rendered* lessons doc is
  re-derived against the graph that exists at `reflect` time, and any lesson
  whose cited nodes were removed by the rebuild loses that grounding.
- **Not used in this repo**: this dotfiles repo has no `graphify-out/memory/`
  directory and no `mise` task or `python/` call site touches
  `save-result`/`reflect` (checked `mise.toml` and
  `python/src/dotfiles_setup/graphify.py` — neither references it). KB, by
  contrast, has dozens of memory files (Q4) — this repo has adopted the
  deterministic `query`/`health` read path only, not the feedback-loop half of
  the tool.

## Q6 — release notes 0.9.43 through 0.9.53

Fetched via `https://api.github.com/repos/Graphify-Labs/graphify/releases`
(11 tagged releases, `v0.9.43`-`v0.9.53`; repo confirmed from PyPI metadata:
`Project-URL: Repository, https://github.com/Graphify-Labs/graphify`). Full
bodies retained in this session's scratch (`/tmp/release_notes.txt`, not
committed — see the artifact-conventions rule). Per-release summary, with
every entry touching schema/edges/corruption/migration/data-loss flagged:

- **0.9.43** (2026-08-14) — OCaml support; cross-file `uses` edge precision
  fix; nested function-declaration noding; Bash `source` path resolution
  hardening (a security fix — path traversal bounded to the tracked base);
  wiki link filename encoding fix; export path length budgeting for Windows.
  No schema/edges/corruption changes.
- **0.9.44** (2026-08-15) — `.graphifyrc` viz-node-limit baked into git
  hooks; **`graphify install` (Claude) now writes CLAUDE.md registration to
  `$CLAUDE_CONFIG_DIR` when set** (part 1 of the #2694 fix Q3 discusses);
  JS/TS generator-expression shadow fix; `.gitignore`-vs-tracked-file
  precedence fix; C++/Catch2 test-case recovery; `graphify affected`
  absolute-seed resolution fix. No schema/edges/corruption changes.
- **0.9.45** (2026-08-16) — ⚠️ **`.graphify_version` stamp fix (part 2 of
  #2694, directly relevant — see Q3)**: *"`graphify install <platform>` now
  advances the `.graphify_version` stamp only for the platform it actually
  (re)writes, instead of stamping every installed platform as current."*
  Also: incremental-rebuild `.graphify_root` marker validation fix (⚠️
  **prevents a whole-graph collapse** when the root marker and stored paths
  disagree — a real graph-corruption-class fix, though not this repo's
  symptom, see Q7); Go case-sensitive symbol disambiguation; **⚠️ id-less
  hyperedge crash fix** (`KeyError: 'id'` on load — a genuine load-path
  robustness fix, again not this repo's symptom).
- **0.9.46** (2026-08-17) — Unicode normalization fixpoint fix for node ids
  (existing graphs unaffected per the note); Java annotation edges; query
  underscore/hyphen tokenization; post-checkout hook no-op-on-same-HEAD fix;
  Markdown frontmatter parsing; Common Lisp support; **⚠️ query budget-vs-edges
  honesty fix** (edges are "never dropped from a complete answer" — reassuring
  re: edge integrity in query output specifically, not storage);
  `.gitignore` non-UTF-8 encoding fix; **hyperedge-member rewiring on dedup
  merge** (prevents a merge from silently dropping a hyperedge participant).
- **0.9.47** (2026-08-19) — Chunk-timeout bisection instead of whole-chunk
  failure; **⚠️ symlink cache-key collision fix** (a symlink alias no longer
  displaces its target from the graph on a warm cache — a real
  data-loss-class fix); sidecar write isolation from scan root; Windows
  drive-relative path guard-detection fix; Obsidian non-Latin tag fix;
  JS/TS factory-function member capture; **⚠️ `graph.json` field-order
  stability** (`graphify update` on an unchanged graph now produces a
  byte-identical file — directly relevant to any diffing/hashing of
  `graph.json`, e.g. this repo's `_receipt_matches` sha256 check); query
  header now names the opened graph + node count.
- **0.9.48** (2026-08-20) — **⚠️ control-character export crash fix**
  (GraphML/Obsidian exporters no longer abort the whole export on a bad
  label/id; `graph.json` itself untouched); **⚠️ missing `graph.html`
  regeneration fix** after `update`/`label`/`cluster-only`; `--no-dedup` flag;
  hollow-LLM-reply retry-with-backoff; reasoning-model narration-before-JSON
  recovery; declined-extraction manifest bookkeeping fix; C++ nested type
  retention; Obsidian wikilink vault-wide resolution.
- **0.9.49** (2026-08-24) — `merge-graphs` cross-repo `same_type_as` linking;
  C#/TS constructor-call and property-node features across several languages;
  C/C++/ObjC declaration-vs-definition node-merge site fix; bash/SQL
  extraction fixes; Zig/Julia/Common-Lisp/PowerShell extraction fixes;
  **⚠️ empty-semantic-result caching fix** (a degenerate LLM reply no longer
  permanently freezes a file out of re-extraction — a real "silent data
  never arrives" class fix, though about the semantic tier, not the base
  graph schema).
- **0.9.50** (2026-08-25) — Ruby method-name (`!`/`?`/`=`) id collision fix;
  Ruby qualified-constant receiver fix; CommonJS higher-order export capture;
  **⚠️ `merge-graphs` community-id offset fix** (prevents unrelated repos'
  community 0 from fusing on merge); **⚠️ Windows BOM `.graphify_root` marker
  fix** (a BOM-prefixed marker no longer breaks hook rebuilds or
  "silently mis-roots a scan" — directly the same *class* of root-marker
  hazard as 0.9.45's fix, still being hardened here); ignore-pattern
  performance rewrite; C#/TS enum-member nodes; `graphify watch` self-read
  loop fix; postgres tree-sitter-sql packaging fix.
- **0.9.51** (2026-08-28) — **⚠️ incomplete-build shrink-guard hardening**
  (a hollow/unparseable/omitting chunk can no longer silently overwrite the
  existing graph with a smaller one — the single most relevant fix in this
  whole window to "graph corruption/data loss," see Q7); `extract --force
  --code-only` full-rescan fix; **⚠️ dedup-survivor hyperedge remap on load**
  (a carried-forward hyperedge no longer dangles after a dedup merge); cache
  atexit no longer recreates a deliberately-deleted `graphify-out/`; Leiden
  clustering determinism fix (edge-endpoint canonicalization); TS/JS
  constructor-call edges; Elixir guard-clause extraction; Common Lisp id
  collision fix; perf (native `graspologic_native` binding); README git-hook
  docs.
- **0.9.52** (2026-08-29) — Markdown-link preservation during code-only
  rebuild; T-SQL ERROR-node recovery by name; `--help` completeness fix;
  pricing/docstring corrections; Razor/C# scope-aware resolution; MCP
  `prs`/`get_node` error-surfacing and resolver-agreement fixes; **⚠️
  `graphify install --project` hook-command fix** (a committed hook now
  resolves the interpreter at run time instead of pinning an absolute path —
  relevant if this repo ever installs graphify's git hooks, which it
  currently does not appear to); PHP constructor-call edges; C#/Java/ObjC
  inheritance-chain field-type resolution; Objective-C field-table
  re-keying after `update` id normalization; TS type-only-import fix.
- **0.9.53** (2026-08-30, latest) — Cross-language inheritance-edge batch fix
  (JS/PHP/Scala/Kotlin/C#/Go); Robot Framework extraction (new optional
  extra); prompt-injection defanging generalization for chat-template
  tokens; markdown-link preservation extension; **⚠️ semantic-node
  false-drop fix** (a node is no longer dropped when a run didn't actually
  re-extract the semantic tier); git hook-guard false-positive fix;
  **⚠️ `graphify install` now backs up a diverged `SKILL.md` before
  overwriting** instead of silently clobbering user edits — **directly
  relevant to this repo's Q2 finding**: the one-line manual patch on
  `.claude/skills/graphify/SKILL.md` would, at 0.9.53, trigger a backup+warning
  on re-install rather than being silently destroyed, which is a real safety
  improvement for exactly this repo's situation; `GRAPH_REPORT` count
  reconciliation fix; wiki truncation-notice fix.

**None of the 11 releases mention the literal `graph field 'edges' must be an
array` message, a graph `.json` key rename, or any migration step for an
existing `graph.json`.** The closest genuine "schema/data-loss" fixes are
0.9.45's/0.9.50's root-marker hardening, 0.9.47's symlink cache-collision and
field-order fixes, 0.9.49's empty-semantic-result caching fix, and 0.9.51's
incomplete-build shrink-guard — all are about *incremental update* correctness
(re-extraction, caching, merge), not the base `node_link_data` JSON shape. See
Q7 for why: the schema check that's failing is not upstream's.

## Q7 — is the 'edges must be an array' corruption a known upstream issue?

**No — and it is not evidence of real graph corruption or data loss either.**
This is the single most load-bearing finding in this report, so the full
chain of evidence:

1. The exact string `"graph field {field!r} must be an array"` is generated by
   **this repo's own code**: `python/src/dotfiles_setup/graphify.py:162-166`,
   function `_graph_schema_problem()`, which iterates
   `("nodes", "edges", "hyperedges")` and requires each to be a list in the
   loaded `graph.json` payload. It is not an upstream graphify error message —
   grepping GitHub search
   (`repo:Graphify-Labs/graphify "edges" "must be an array"`) returns **0**
   results.
2. The repo's live `graphify-out/graph.json` (14.5 MB, 13,344 nodes) has these
   top-level keys: `directed, multigraph, graph, nodes, links, hyperedges,
   built_at_commit`. **There is no `"edges"` key at all** — the edge list is
   under `"links"`. `payload.get("edges")` therefore returns `None`, which is
   not a list, which is exactly what trips `_graph_schema_problem`.
3. Reading the installed graphify package confirms this is the *correct,
   intentional* upstream shape: every JSON export/import call site in
   `graphify/export.py`, `cli.py`, `affected.py`, `global_graph.py`,
   `multigraph_compat.py`, `paths.py`, `serve.py`, `watch.py` uses
   `networkx.json_graph.node_link_data(G, edges="links")` /
   `node_link_graph(data, edges="links")` — networkx's own `node_link_data`
   API takes an `edges=` **parameter naming which JSON key to use**, and
   graphify has explicitly chosen `"links"` everywhere. `cli.py:2306` even
   carries a comment acknowledging the history: *"via node_link_data but
   older runs may have used 'edges' (#738)"* — confirming graphify's own key
   name **changed from `"edges"` to `"links"` at some point in the past**
   (tracked as graphify's own issue #738), and that upstream code already
   handles reading either key back in (`export.py:380`: `links_key = "links"
   if "links" in graph_data else "edges"`).
4. So the true defect is that `dotfiles_setup.graphify._graph_schema_problem`
   was written against the **old** `"edges"`-keyed schema and was never
   updated when graphify (at some release predating even 0.9.42, per #738)
   switched its default export key to `"links"`. The repo's own test fixtures
   (`tests/test_graphify.py`) all hand-construct graphs with `"edges": []`,
   reinforcing that the test suite encodes the same stale assumption as the
   production check — a green test suite here is not evidence the check is
   correct, because both sides share the wrong premise (a `probes-need-a-
   control-arm.md` "fixture rigged to only produce one answer" instance).
5. There is also no `graphify-out/build-receipt.json` on disk currently, so
   even past the schema check, `_receipt_problem()` would report `STALE`
   ("build receipt missing") — a second, independent reason `graphify-health`
   cannot currently report `FRESH`, unrelated to the edges/links question.

**Consequence for the planned rebuild**: rebuilding the graph (`graphify
update .` or a fresh `extract`) will **not** fix this by itself, because the
freshly-built `graph.json` will *also* use the `"links"` key (that's simply
how graphify writes JSON) and `_graph_schema_problem` will report the exact
same `"graph field 'edges' must be an array"` corruption on the new file too.
**The fix is in `dotfiles_setup/graphify.py`, not in the graphify package or
the pin.** The check needs to read `payload.get("links", payload.get("edges"))`
(mirroring graphify's own `export.py:380` fallback) or be updated to require
`"links"` outright, plus the matching update in `tests/test_graphify.py`'s
fixtures. This is a repo-code bug, not a "known upstream issue" — I searched
GitHub issues/search for `corrupt graph` (80 results) and `edges must be an
array` (0 results) on `Graphify-Labs/graphify` and found nothing matching this
symptom; the closest topically-related issues (#2191 "false corrupt warning
via external-import dangling edges", #2405 "silently swallows corrupt cache
entries") are about different code paths entirely (graphify's own internal
`diagnose_extraction`/cache, not a downstream consumer's schema check).

## Q8 — correct end-to-end upgrade procedure for this repo

Given Q1-Q7, the procedure, in order:

1. **Fix the schema check first, independent of the version bump.** Update
   `_graph_schema_problem()` in `python/src/dotfiles_setup/graphify.py` to
   accept `"links"` (graphify's actual, current export key) — at minimum
   `payload.get("links", payload.get("edges"))`, and update every `"edges":
   []` fixture in `tests/test_graphify.py` to `"links": []` to match. Do this
   as its own change with its own tests, since it is a real defect
   independent of the pin (Q7). Skipping this step means the post-upgrade
   rebuild will still report `corrupt`.
2. **Bump the pin.** `python/pyproject.toml:9`:
   `"graphifyy[all]==0.9.42"` → `"graphifyy[all]==0.9.53"`.
3. **Update the two hardcoded `"0.9.42"` literals that gate freshness.**
   `python/src/dotfiles_setup/graphify.py:193-194`:
   ```python
   if runtime != "0.9.42":
       return HealthResult(GraphifyStatus.VERSION_DRIFT, runtime, "expected 0.9.42")
   ```
   must become `"0.9.53"`, or `graphify-health` will report `version_drift`
   forever after the bump even on a perfectly fresh graph. `tests/test_graphify.py`
   has **11** occurrences of the literal `"0.9.42"` (lines 53, 74, 223, 238-239,
   323, 352, 380, 426, 432) that all need the same bump — grep
   `grep -n '0\.9\.42' python/src/dotfiles_setup/graphify.py tests/test_graphify.py`
   before considering this step done, since a missed occurrence fails silently
   (a stale assertion in a test just keeps passing against the old string).
4. **Regenerate the lockfile.** `uv lock` (or the project's usual
   `uv sync --project python` / whatever this repo's dependency-bump flow
   is — I did not find a dedicated `mise` task for a plain `uv lock` in
   `mise.toml`'s graphify section, so this is likely a bare `uv lock`
   inside `python/`, consistent with how `pyproject.toml` manages every
   other pinned dependency here).
5. **Refresh both skill surfaces, respecting the hard constraint.**
   - `.claude/skills/graphify/`: run `graphify install --project --platform
     claude` from a **throwaway directory outside this repo**, per `do-not.md`
     item 8, then copy the resulting `.claude/skills/graphify/{SKILL.md,
     references/}` into this repo, and **re-apply the one manual patch**
     (`raise SystemExit(1)` in the labeling step) that Q2 found layered on top
     — check the file after copying rather than assuming the patch survived.
     At 0.9.53, `graphify install` **will now detect that SKILL.md has
     diverged from the packaged one and back it up with a warning instead of
     silently overwriting** (0.9.53 release note, Q6) — so if this step is
     ever run as an in-place upgrade against an existing `.claude/skills/graphify/`
     rather than a copy-in, that new safety behaviour is exactly the guard
     that would have prevented losing the one-line patch, and its printed
     warning is worth reading rather than dismissing.
   - `.agents/skills/graphify/`: since Q2 established this is a hand-authored
     redirector, not real `agents`-platform installer output, there is **no
     installer command to run for it**. Decide deliberately whether to (a)
     keep it as a hand-maintained redirector and just bump the `.graphify_version`
     file's `0.9.42` text to `0.9.53` by hand (cheap, keeps current design), or
     (b) actually adopt real `agents`-platform installer output (via the same
     throwaway-directory + copy-in pattern as `.claude/`) if the fuller
     `skill-agents.md` content is now wanted. This is a design choice, not a
     mechanical step — flagging it for the repo owner rather than picking one
     unilaterally, per `clarify-before-acting.md`.
6. **Rebuild the graph.** `graphify update .` (AST-only, no LLM cost, per
   this repo's own `.claude/CLAUDE.md` graphify-first convention) or a full
   `mise run graphify-*` task if one exists for a cold build — I did not find
   a dedicated `mise run graphify-build` task in `mise.toml`, only
   `graphify-query`, `graphify-health`, and `graphify-bakeoff`
   (which explicitly writes *outside* the repo per its own comment, so it is
   not the rebuild step). The actual rebuild command is very likely run
   directly (`graphify update .` or `graphify <path>`) rather than through a
   `mise` task — worth confirming with the repo owner before running it,
   since no task wraps it today.
7. **Verify.** `mise run graphify-health` should now report `fresh` (after
   steps 1+3 fix both the schema-key mismatch and the version-drift gate).
   `mise run graphify-query -- "<a real question>"` should return grounded
   results. Then the standard repo-wide gates: `mise run lint`,
   `uv run --project python pytest tests/ -x -q` (covering the updated
   `test_graphify.py` fixtures), `mise run verify`.
8. **Nothing in this procedure requires violating the hard constraint** —
   every install-surface refresh in step 5 uses the documented
   throwaway-directory + copy-in workaround, matching how `.claude/skills/graphify/`
   was evidently produced originally (Q2). The one thing this report
   could **not** verify directly, because doing so would itself violate the
   constraint, is running `graphify install --project --platform claude`
   (or `agents`) against 0.9.53 and inspecting its real output byte-for-byte
   — everything about 0.9.53's installer behaviour here is inferred from its
   source-level release notes (Q6) plus 0.9.42's confirmed-current source,
   not executed. Whoever performs step 5 should diff the fresh 0.9.53 output
   against what this report describes and flag any surprise.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — primary target: fetched all 11 release bodies (v0.9.43-v0.9.53) via the Releases API, and ran two Issues/PR searches (`"edges" "must be an array"`, `corrupt graph`) to check for a known corruption issue (Q6, Q7). Also confirmed as the PyPI package's `Repository` project-url.
- [ray-manaloto/graphify](https://github.com/ray-manaloto/graphify) — not fetched directly, but identified as the private fork the sibling `knowledge-base` repo pins by commit SHA instead of the PyPI release (Q4); flagged as an open question, not verified further.
