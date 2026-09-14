# How this repo should run graphify's deep extraction (2026-09-14)

Read-only research. graphify 0.9.61 installed at `python/.venv`; source at
`python/.venv/lib/python3.14/site-packages/graphify/`. No extraction was run.
Sourced against `graphify --help` (`uv run --project python graphify --help`)
and the installed package source. Every claim is labeled SOURCE (grepped from
the installed package), `--help` (CLI usage text), or INFERRED (reasoned from
the two, not directly read).

## Recommended path, and why the alternatives lose

**Recommended: invoke `graphify extract` directly via the venv-pinned binary
(`uv run --project python graphify extract ...`), NOT the `/graphify` skill,
and NOT a new mise task yet.**

Rejected alternatives:

1. **The `/graphify` skill** (`.claude/skills/graphify/SKILL.md`, read in full).
   SOURCE: its Step 3 "Part B — semantic extraction" dispatches **parallel
   Claude Code subagents** (`Agent` tool calls, `subagent_type="general-purpose"`,
   `.claude/skills/graphify/SKILL.md:196-287`) as the LLM backend when no
   `GEMINI_API_KEY`/`GOOGLE_API_KEY` is set — it does **not** shell out to
   `graphify extract` or the `claude-cli` backend at all. It is a *skill-driven
   reimplementation* of extraction, orchestrated by whatever agent invokes
   `/graphify`, with its own caching, chunking, and merge logic
   (`SKILL.md:216-357`). It is the right tool for an **interactive, agent-driven
   build** where dispatching subagents is cheap and desirable. It is the wrong
   tool for "one headless full extraction run for CI/scripts" — that phrase is
   `graphify extract --help`'s own description of the CLI subcommand
   (`--help` output: `extract <path>  headless full extraction (AST + semantic
   LLM) for CI/scripts`). The operator's ask ("deep extraction of this repo",
   run by an agent following a runnable procedure, not paying for N parallel
   subagent dispatches) matches the CLI's own stated purpose, not the skill's.
2. **A new mise task.** `mise.toml:784-793` ("`[tasks.graphify-update]`") states
   in a code comment that AST-only `graphify update` "is the ONLY sanctioned way
   to rebuild the graph in this repo." (SOURCE, `mise.toml:787-788`.) There is
   **no existing sanctioned task for `extract`** — grepped `python/src/dotfiles_setup/graphify.py`
   for `cmd_extract`/`extract(` and found zero matches (SOURCE, command run,
   empty output — control arm: the same grep for `cmd_update` in the same file
   returns hits, so the grep is not silently broken). Building a new task is a
   reviewable follow-up the operator should decide on, not something to invent
   under a read-only research brief; this report gives the exact command to run
   by hand (or to wrap) instead.

## `--help` vs source: what `--help` omits

`--help`'s one-line description of `extract` ("headless full extraction (AST +
semantic LLM) for CI/scripts") is accurate but the flag list in `--help` is
**complete for this command** — every flag documented below was also confirmed
in `cli.py`'s arg parser (`cli.py:3260-3313`, the `--mode`/`--max-workers`/
`--token-budget`/`--max-concurrency`/`--api-timeout` parsing block). The one
place `--help` under-documents real behavior is **what `--mode deep` and
`--max-concurrency` actually do downstream** — the help text says `--mode deep`
means "aggressive INFERRED-edge semantic extraction" and `--max-concurrency`
"parallel semantic chunks in flight (default: 4; set 1 for local LLMs)", but
does not mention that for the `claude-cli` backend, **concurrency is silently
forced to 1 regardless of the flag** (SOURCE, `llm.py:1692-1694`: `if backend
== "claude-cli" and os.environ.get("GRAPHIFY_CLAUDE_CLI_PARALLEL", "").strip()
!= "1": max_concurrency = 1`, with a comment explaining parallel `claude -p`
subprocesses would conflict over session state). So passing `--max-concurrency
4` on this backend is a documented-looking flag that is a silent no-op unless
`GRAPHIFY_CLAUDE_CLI_PARALLEL=1` is also exported — SOURCE.

## Exact command and per-flag justification

```bash
uv run --project python graphify extract . \
  --backend claude \
  --mode deep \
  --token-budget 60000 \
  --api-timeout 600 \
  --max-workers "$(sysctl -n hw.ncpu)"
```

Do **not** pass `--force`, `--code-only`, `--max-concurrency`, or `--global`.
Per-flag reasoning:

- `--backend claude` — SOURCE, `cli.py`'s backend registry entry for `claude`
  aliases the `claude-cli` code path (the architect's earlier session already
  decided this: `graphify/llm.py:209-221`, `default_model: "claude-code-plan"`,
  `pricing: {input 0.0, output 0.0}`, routes through the local `claude` CLI via
  Pro/Max subscription auth). This report does not re-litigate that decision,
  only confirms the flag name matches it (`--backend B  gemini|kimi|claude|...`,
  `--help`).
- `--mode deep` — the operator asked for a "deep" extraction; this is the flag
  that means it. SOURCE: sets `deep_mode = extract_mode == "deep"`
  (`cli.py:3364-3365`), which (a) appends `_DEEP_EXTRACTION_SUFFIX` to the
  system prompt — "include additional INFERRED edges only for concrete
  architectural signals... Avoid broad conceptual similarity edges. Mark
  uncertain ones AMBIGUOUS instead of omitting" (SOURCE, `llm.py:510-523`), and
  (b) routes cache reads/writes through a **separate namespace**,
  `cache/semantic-deep/`, instead of `cache/semantic/` (SOURCE, `cache.py:938,
  1151-1172`, comment: "Separate subdirectories prevent semantic cache
  [collision]"). `--mode deep` has **zero effect on the AST/code pass** — deep
  mode only changes the semantic (doc/paper/image) LLM prompt and cache
  namespace (SOURCE: `deep_mode` is threaded only into `_extraction_system`
  and the semantic cache calls, never into `graphify.extract`/AST code paths
  grepped in `cli.py`'s Part-A-equivalent AST block).
- `--token-budget 60000` — this is already the documented default
  (`--help`: "per-chunk token cap for semantic extraction (default: 60000)"),
  named explicitly rather than omitted so the command is self-documenting and
  immune to a future default change.
- `--api-timeout 600` — also the documented default (600s). Named explicitly
  for the same reason; a `claude -p` subprocess call can legitimately run long
  on a large chunk and 600s is graphify's own conservative choice.
- `--max-workers "$(sysctl -n hw.ncpu)"` — `--help`: "AST extraction subprocess
  count (default: cpu_count)". This is functionally the same as omitting the
  flag (default is already cpu_count) but names the value so the command
  doesn't rely on an implicit default the reader has to look up. AST extraction
  is deterministic, local, and unrelated to the `claude-cli` concurrency
  constraint below, so parallelism here is safe and desirable.
- **Omit `--max-concurrency`** — SOURCE (above): forced to 1 for `claude-cli`
  regardless of the flag's value. Passing it invites a false belief that a
  higher number speeds up the semantic pass; it does not, for this backend.
- **Omit `--force`** — see Incrementality below: forcing would skip the
  incremental manifest gate AND the semantic cache reads, re-dispatching every
  one of the corpus's ~1,109 doc/pdf files (measured this session,
  `find . -iname '*.md' -o -iname '*.pdf'` excluding `.git/`, `python/.venv/`,
  `node_modules/`, `plugins/`, `docs/research/mintlify-cache/`,
  `graphify-out/` → **1109** files) even on a warm cache. `--mode deep`
  already widens the semantic pass to the *full live* doc/paper/image set on
  its own (see next section) — `--force` is redundant for that and actively
  harmful for cache reuse.
- **Omit `--code-only`** — that flag would skip doc/paper/image extraction
  entirely (`--help`: "index code (local AST, no API key) and skip doc/paper/image
  files"), which defeats the stated goal (deep *semantic* extraction) since
  the AST-only pass was already run via the sanctioned `graphify-update` task
  this session.
- **Omit `--global`** — `--help`: "also merge the resulting graph into the
  global graph." No cross-repo global graph is in scope here; nothing in this
  research established one exists or should be touched. Omitting is the
  conservative default.

## Deep vs semantic vs standard — what actually selects deep mode

- **"Standard" extraction** = `graphify update` (AST only, already run this
  session) or `graphify extract` without `--mode deep` (AST + semantic, normal
  prompt, `cache/semantic/`).
- **"Deep" extraction** = `graphify extract --mode deep`. Selected purely by
  the CLI's `--mode` argument being the literal string `deep`
  (`cli.py:3271-3273` parses `--mode`/`--mode=`; `cli.py:3364`:
  `deep_mode = extract_mode == "deep"`; any other value hits the `error:
  unknown --mode` branch at `cli.py:3359`). There is no separate "semantic"
  mode name — "semantic" is the *category* of extraction (docs/papers/images
  via LLM) that deep mode modifies; it is not a third mode selectable on its
  own. `deep_mode` is a single boolean threaded through: the system prompt
  builder (`_extraction_system(deep=...)`, `llm.py:519-523`), the semantic
  cache key/namespace (`cache.py`, `mode="deep"` argument), and — deliberately
  — nothing in the AST/code path.

## Incrementality and safety — enrich, not clobber

**It will enrich the existing graph, not clobber it, PROVIDED `--force` is not
passed** — this is the default:

- SOURCE: `cli.py:3412`, `existing_graph_path = graphify_out / "graph.json"`;
  `cli.py:3421`, `incremental_mode = existing_graph_path.exists() if
  has_path else False`; `cli.py:3424`, `incremental_mode = incremental_mode
  and not force`. Since `graphify-out/graph.json` already exists (22,312 nodes,
  confirmed this session via `graphify-update`), a plain `extract` run without
  `--force` starts in incremental mode: only new/changed code files and
  new/changed semantic files are re-dispatched, and a **shrink guard** (#479 in
  graphify's own issue tracker, referenced repeatedly in `cli.py` around
  line 4009 and `4430-4460`) refuses to write a `graph.json` with fewer nodes
  than the one on disk, so an aborted or partial run cannot silently shrink the
  graph.
- **Deep mode's own carve-out widens the semantic pass on its own**, even
  incrementally: SOURCE, `cli.py:3574-3595` — "Deep mode reads/writes its own
  cache namespace (cache/semantic-deep/), so the manifest's changed-file gate
  is not a valid proxy for deep coverage: over a warm unchanged tree it
  dispatches zero files and `--mode deep` silently no-ops (#1894)." The code
  widens `semantic_files` to the **full live doc/paper/image set** from
  `files_by_type`, and lets the deep-namespaced cache (cold on first deep run)
  decide hits/misses. **This means the first `--mode deep` run will dispatch
  semantic extraction for all ~1,109 doc/pdf files** (not just what changed
  since the AST-only rebuild), because `cache/semantic-deep/` has never been
  populated. A second deep run on an unchanged tree would hit that cache and
  be fast.
- **Resume-on-interruption**: SOURCE, `llm.py:1697-1735` (`_checkpoint_chunk`),
  each completed chunk's semantic results are written to
  `cache/semantic-deep/` (or `cache/semantic/` for non-deep) **immediately**,
  not just at the end of the run — comment: "a run interrupted partway — a
  crash, a kill, or a claude-cli/API run that exits on a rate limit — loses
  every completed chunk and restarts from scratch [without this]. This is
  best-effort." So a killed/interrupted `--mode deep` extraction over ~44
  chunks (1109 files / chunk_size 20 default, SOURCE `llm.py:2556` `chunk_size:
  int = 20`) can simply be **re-run with the same command** — completed chunks
  are served from cache, only the remainder is dispatched. No `--resume` flag
  exists or is needed; re-invocation IS the resume mechanism.
- **What gets written, and gitignore status**: `graphify-out/` is
  git-ignored except `graphify-out/wiki/` (SOURCE, `.gitignore:88-90`:
  `graphify-out/` then `!graphify-out/wiki/`). Confirmed present on disk this
  session: `graph.json` (23.9 MB), `GRAPH_REPORT.md`, `graph.html`,
  `manifest.json`, `.graphify_labels.json[.sig]`, `.graphify_learning.json`,
  dated subdirectories, and `cache/` (currently only an `ast` cache directory
  present — `cache/semantic/` and `cache/semantic-deep/` do not yet exist,
  control arm: `ls graphify-out/cache` was run and only showed 4 entries, none
  named `semantic*`, consistent with no semantic extraction having run yet).
  None of `extract`'s output is tracked by git; a deep extraction changes only
  git-ignored artifacts (plus updating `cache/semantic-deep/`, also under the
  ignored `graphify-out/`).

## Failure modes to pre-empt

- **Rate limit / API failure from the `claude` CLI**: SOURCE, `llm.py:1598-1603`
  — "`claude -p` reports API failures (rate limits, auth) in the stdout JSON
  envelope with `is_error: true` and leaves stderr EMPTY — and on a rate limit
  [...] `_response_is_hollow` misread [it] as truncation and adaptive retry
  then bisected [...]." This was a real historical bug (referenced by number in
  the source comment) that graphify has since fixed by distinguishing a hollow
  response (rate limit, transport hiccup, refusal, or genuinely empty content)
  from a truncated one. Per `llm.py:1245-1296` (`_response_is_hollow`,
  `_mark_hollow`): a hollow response is **not bisected** (bisecting a
  rate-limited chunk would just multiply the number of rate-limited calls —
  comment at `llm.py:1283-1285` warns of "`2**max_retry_depth` billed calls —
  up to 15 per chunk at the default depth, all of them failing"); instead the
  *same* chunk is retried with backoff, then fails loudly if still hollow after
  retries exhaust (`llm.py:2458-2467`).
- **A chunk that fails outright** (exception, not hollow): SOURCE,
  `extract_corpus_parallel`'s docstring (`llm.py:2596-2597`): "Failed chunks
  are logged to stderr and skipped — one bad chunk does not abort the run."
  `cli.py`'s error handling additionally distinguishes "all chunks failed"
  (hard `sys.exit(1)`, `cli.py` around the `_chunk_stats["succeeded"] == 0`
  check) from "some chunks failed" (graph is written but incomplete, and the
  unstamped files are left for the next incremental run to re-queue — SOURCE,
  comment at `cli.py:3576-3583`... "over a warm unchanged tree" and the
  `_partial_semantic_files` tracking mentioned at `cli.py`'s manifest-stamping
  block near line 3868-3878, referencing issue #2015: "a detected file whose
  chunk failed or was omitted must stay unstamped so the next --update
  re-queues it, otherwise it is marked done and its content is lost forever").
- **Interrupted run (killed process, Ctrl-C, session timeout)**: see
  Incrementality above — per-chunk checkpointing to the semantic cache means
  re-running the identical command resumes from the last completed chunk.
- **Truncated output (`finish_reason == "length"`)**: adaptively bisected
  (chunk split in half, each half re-extracted) up to `max_retry_depth` levels
  (default 3, env override `GRAPHIFY_MAX_RETRY_DEPTH`) — SOURCE,
  `llm.py:2302-2467` (`_extract_with_adaptive_retry`) and `llm.py:439-450`
  (`_resolve_max_retry_depth`).

## `reflect` and generated artifacts

**Answerable directly, not a guess: nothing in this repo's flow (AST-only
`graphify-update`, nor the deep-extraction command above) writes to
`graphify-out/memory/`, so `graphify reflect` will no-op on an empty/absent
memory directory.** Control arm: `ls graphify-out/memory` and `ls
graphify-out/reflections` were both run this session and returned "No such
file or directory" (a freshly-invented check — the directory name itself,
`memory`, is exactly what would exist if it were populated, so this is not a
misspelled-token false negative). `graphify-out/memory/*.json` is written only
by `graphify save-result` (`--help`: "save a Q&A result to graphify-out/memory/
for graph feedback loop"), which is invoked when a human or agent explicitly
records a query outcome (`--question`, `--answer`, `--outcome
useful|dead_end|corrected`, etc. — `--help`). Grepped this repo's `mise.toml`
and `.claude/rules/*.md` for `save-result`/`save_result`/`reflect`: zero
matches (SOURCE, command run, empty output — control arm: the same grep
command for `graphify-update`/`graphify-query`, known to exist in those files,
returns many hits, so the grep itself is not broken). Neither `graphify update`
nor `graphify extract` calls `save-result` internally (grepped `save_semantic_cache`
and `save-result`/`save_result` separately in `cli.py`; only the cache-saving
calls exist, no `save-result`/memory-writing call site outside the dedicated
`cmd_save_result`-style CLI branch). **Conclusion: `reflect` is a live but
currently-empty capability for this repo — it will run without error but
produce a lessons doc with nothing in it, until something (a human, a skill, or
a new automation) starts calling `save-result` after queries.** That is outside
this report's scope; flagging it as a real, answerable gap rather than an
assumption.

## Summary — the runnable procedure

1. (Already done this session) `mise run graphify-update` — AST-only baseline,
   sanctioned, no LLM.
2. To layer deep semantic extraction on top, from the repo root:
   ```bash
   uv run --project python graphify extract . \
     --backend claude \
     --mode deep \
     --token-budget 60000 \
     --api-timeout 600 \
     --max-workers "$(sysctl -n hw.ncpu)"
   ```
   This is **not yet a sanctioned mise task** — `mise.toml` currently commits
   only to AST-only `graphify-update` as sanctioned. Running the command above
   is a deliberate one-off outside that sanction unless/until the operator asks
   for a wrapping task.
3. Expect a long, **serial** run: `claude-cli` backend forces concurrency to 1,
   and this repo has 1,109 doc/pdf files; a first `--mode deep` run dispatches
   the full live set (deep cache starts cold) in chunks of 20 files each
   (~56 chunks), each chunk an `api-timeout`-bounded `claude -p` subprocess
   call.
4. It is safe to interrupt and re-run identically — per-chunk caching resumes.
5. It will not clobber `graph.json` — incremental mode + the shrink guard
   protect it; only re-run with `--force` if an intentional full clobber is
   wanted (not recommended here).
6. `graphify reflect` will currently no-op — nothing populates
   `graphify-out/memory/` in this repo's flow.

## GitHub repos touched

- _None._ This research read only the locally-installed `graphifyy` package
  (`python/.venv/lib/python3.14/site-packages/graphify/`) and this repo's own
  files (`mise.toml`, `.gitignore`, `.graphifyignore`,
  `.claude/skills/graphify/SKILL.md`, `python/src/dotfiles_setup/graphify.py`).
  No GitHub repo was fetched or browsed.
