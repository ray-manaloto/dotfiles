# graphify over markdown memory directories: what `graphify query` can find (run 3, 2026-10-03)

Question: how do people use graphify (Graphify-Labs/graphify, formerly safishamsi/graphify, PyPI `graphifyy`) to cut
agent context over markdown, notes and memory directories, such as a Claude Code auto-memory dir of one-fact `.md` files
with a YAML `description:`? Does graphify 0.9.73/0.9.74 index markdown BODY text and frontmatter for query, or only
titles, headings and links? Which mode indexes prose? The answer decides between Tier 0 (plain grep over memory),
Tier 1 (a repo memory-query mise task over graphify) and deferring to Tier 2 (#997).

Synthesizer: opus / high. It re-verified the load-bearing claims itself, against the pinned source on disk, the live
GitHub API, and a real keyless `graphify update` + `graphify query` run. Both arms of that run are recorded below.

## Answer

**Mandatory gaps: none were reported for this sweep.** It is still not a full sweep. The firecrawl mirrors of all three
caller links failed (out of credits), and the third-party usage pages were found in triage but never read. Both are in
Gaps. This run fixes the two gaps the degraded run 1 left: the code search now uses the `Graphify-Labs/graphify` slug,
and its must-hit returned results (8 and 2); and the 0.9.74 check now ran.

1. **SHIPS (0.9.73, re-measured here; 0.9.74 and 0.9.75 checked by diff): keyless mode turns markdown into a structure
   graph, not a text index.** `graphify update <dir>` sends `.md` files through `extract_markdown`, with no LLM. That
   produces:
   - a `page` node per file, which carries the parsed YAML frontmatter under a `frontmatter` key;
   - a `heading` node per heading, with `contains` edges;
   - `references` edges for inline links, reference-style links and `[[wikilinks]]`. The wikilink lookup falls back
     across the whole vault, which shipped in v0.9.48 from PR #2875;
   - `references` edges to code symbols named in backtick spans.

   **Ordinary body prose is not stored in `graph.json`.**
2. **SHIPS: `graphify query` does not search frontmatter or body text.** The search text it builds (`serve.py:404-448`,
   `_node_search_text`) holds only: label, label tokens, node id, `source_file` and its tokens, `rationale`, and
   `attributes`. Only the Terraform extractor writes `attributes` (`extractors/terraform.py:459`). The markdown
   extractor writes `frontmatter`, and the scorer never reads that key.

   Live run on a two-file memory fixture:

   | query term | where it appears in the fixture | query result | count in `graph.json` |
   |---|---|---|---|
   | `zebrastripe` | a heading | **hit** | 4 |
   | `feedback` | the filename | **hit** | — |
   | `quokkafrontier` | only the `description:` | "No matching nodes found." | 1 (stored, not searched) |
   | `pelicanbody` | only the body | "No matching nodes found." | 0 (not stored) |
3. **SHIPS: the only mode that makes prose searchable is LLM semantic extraction.** That is the `/graphify` skill's
   Part B or `graphify extract`, and it costs tokens. It writes model-invented concept nodes and a `rationale` summary,
   which the scorer does read. That gives a lossy summary of the prose, not full-text recall. graphify's own
   `save-result` docstring says the same thing (`ingest.py:297-307`): its `## Outcome` body section "round-trips into
   the graph on the next **semantic** re-extraction".
4. **PROPOSED, not shipped:**
   - **PR #1064** (`graphify export memory-index`) is **OPEN, unmerged**. It summarizes the *code graph* to orient a
     session ("Key modules (top 15% by connectivity)"). It does not query a directory of memory files.
   - **PR #3348** (wikilink same-page anchors and heading fragments) is **OPEN, unmerged**. It changes links only.
5. **SHIPS, but a different kind of memory: graphify has its own "work memory".** `graphify save-result` writes Q&A
   files with frontmatter to `graphify-out/memory/`. `graphify reflect` then aggregates them, with no LLM, into
   `graphify-out/reflections/LESSONS.md` (`reflect.py:1-30`). This is graphify remembering its own query outcomes. It
   does not index a Claude Code auto-memory dir.
6. **THIRD PARTY (not read, so no claim):** the ai-brain-starter `SKILL.md`, the Agent Memory Atlas page and the
   DeepWiki "Work Memory & Reflection" page are in the triage list. None was read (Gaps).

**For the decision:** the auto-memory index is one fact per file, and the words that matter are in `description:` and
the body. Keyless graphify cannot answer a query whose words appear only there, and grep can. **Tier 0 (plain grep) is
the right tier now.** Tier 1 over keyless graphify would add the same recall that filenames plus grep already give. Its
only real extra value is link structure: who links to whom, through wikilinks.

## Evidence

| claim | URL or file:line | quote |
|---|---|---|
| The query search text omits frontmatter and body | `python/.venv/lib/python3.14/site-packages/graphify/serve.py:437-448` (graphifyy 0.9.73, `graphifyy-0.9.73.dist-info`) | `fields = (norm_label, label_tokens, nid_text, source, source_tokens)` … `rationale = _node_rationale_text(data)` … `attr_norm, attr_tokens = _node_attributes_text(data)` |
| The attributes tier reads only `attributes` | `serve.py:342-347` | `attrs = data.get("attributes")` / `if not isinstance(attrs, dict) or not attrs: return "", ""` |
| Only Terraform writes `attributes` | `extractors/terraform.py:459` (repo-wide grep `\[.attributes.\] *=` → 1 hit) | `nodes_by_id[owner]["attributes"] = attrs` |
| Markdown frontmatter is stored on the page node | `extractors/markdown.py:408-413` | `add_node(file_nid, path.name, 1, node_kind="page", extra={"frontmatter": frontmatter} if frontmatter else None)` |
| The markdown extractor emits pages, headings, link edges and code-span mentions only | `extractors/markdown.py:296-347` (docstring) | "Produces nodes for: - The file itself … - Each heading" / "Inline code spans on heading and body lines … are collected as `raw_calls`" |
| The semantic cache ignores frontmatter edits | `cache.py:178-190`, `cache.py:443-444` | "For Markdown files (.md), only the body below the YAML frontmatter is hashed, so metadata-only changes … do not invalidate the cache." |
| Prose needs the LLM path | `graphify/skill.md:161` | "This step has two parts: **structural extraction** (deterministic, free) and **semantic extraction** (LLM, costs tokens)." |
| Keyless update over a memory fixture | live: `/tmp/gfy-memprobe-47077/update.log` | "Re-extracting code files in . (no LLM needed)… Rebuilt: 4 nodes, 3 edges, 2 communities" |
| Heading term found (positive arm) | live: `/tmp/gfy-memprobe-47077/q-zebrastripe.txt` | "Start: ['Heading Zebrastripe'] \| 3 nodes found" |
| Description-only term not found, but stored | live: `q-quokkafrontier.txt`, plus `graph.json` page node | "No matching nodes found." / `{'name': 'alpha', 'description': 'Quokkafrontier lives only in this description field', 'type': 'feedback'}` |
| Body-only term not found and not stored | live: `q-pelicanbody.txt`; `grep -c -i pelicanbody graph.json` → 0 | "No matching nodes found." |
| 0.9.74 did not change query or frontmatter handling | `gh api …/compare/v0.9.73...v0.9.74`: 19 commits, `serve.py` not among changed files; the `markdown.py` patch only adds `.md` completion for dotted wikilink names | "A wikilink whose note name itself contains a dot (`[[note.en]]`, `[[v1.2 release]]`) gets the same `.md` completion" |
| 0.9.75 (2026-10-04) did not either | `compare/v0.9.74...v0.9.75`: the `serve.py` patch is a shortest-path reverse `contains` hop (#3878); `grep -c frontmatter` in it → 0 | "Add the implied reverse hop for traversal only" |
| PR #2875 shipped in v0.9.48 | https://github.com/Graphify-Labs/graphify/pull/2875 (live `gh api`: state=closed merged=false; comment by safishamsi 2026-08-20) | "Shipped in v0.9.48 via authorship-preserving cherry-pick. Thanks @BaeHyunJae!" |
| PR #2875 covers wikilinks only | https://github.com/Graphify-Labs/graphify/pull/2875 | "**wikilinks only** — vault-global lookup is a wikilink convention; inline `[text](path.md)` and reference-style links keep pure relative semantics" |
| The vault fallback is present in 0.9.73 | `extractors/markdown.py:112-121`, `:178` `_vault_lookup` | "Vault-wide wikilink fallback. Obsidian-style vaults resolve a [[wikilink]] by vault-global filename lookup" |
| PR #3348 is OPEN and changes links only | https://github.com/Graphify-Labs/graphify/pull/3348 (live: open, merged=false) | "Obsidian wikilinks `[[#Heading]]` and `[[Page#Heading\|alias]]` produced no graph edge before this change" |
| PR #1064 is OPEN and summarizes the code graph | https://github.com/Graphify-Labs/graphify/pull/1064 (live: open, merged=false) | "Key modules (top 15% by connectivity)" / "**Impact**: 97% token reduction (~55K → 2K tokens per session start)" |
| graphify's own work memory | `ingest.py:297-307`, `reflect.py:1-8` | "Save a Q&A result as markdown so it gets extracted into the graph on next --update" / "`graphify reflect` reads the Q&A memory docs that `graphify save-result` files back into the graph" |
| Releases are current | `gh api …/releases` | `v0.9.75 2026-10-04`, `v0.9.74 2026-10-02`, `v0.9.73 2026-09-30` |

Control arm for the live PR reads: `gh api repos/Graphify-Labs/graphify/pulls/999999999` → HTTP 404. So the probe can
tell a real PR from a missing one. #3822 also returned 404 as a *pull* and resolved as an *issue* (see Conflicts).

### Code search

Source: the research-fanout planner/workflow (CODE SEARCH input). No CODE SEARCH NOTES were supplied.

| query | role | source | count | rc |
|---|---|---|---|---|
| `repo:Graphify-Labs/graphify filename:serve.py frontmatter` | query | planner | 0 | 0 |
| `repo:Graphify-Labs/graphify extract_markdown frontmatter` | query | planner | 2 | 0 |
| `repo:Graphify-Labs/graphify memory index export` | query | planner | 17 | 0 |
| `repo:Graphify-Labs/graphify filename:serve.py score` | must-hit | planner | 2 | 0 |
| `repo:Graphify-Labs/graphify extract_markdown` | must-hit | planner | 8 | 0 |
| `repo:Graphify-Labs/graphify qzv9060000wkx` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:Graphify-Labs/graphify filename:README.md` | must-hit | workflow | 6 | 0 |

The 0 for `serve.py frontmatter` is **armed**: the `serve.py score` must-hit returned 2, so `serve.py` is in the index. A
local grep of the 0.9.73 `serve.py` also found no `frontmatter` token (the repo-wide `frontmatter` grep listed no
`serve.py` line). So two routes agree.

### Dependency-repo fan-out

| repo | query | required sources failed | manifest |
|---|---|---|---|
| Graphify-Labs/graphify | graphify markdown memory index | none (`requiredFailed: []`, ok, fresh) | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-03n/.agent/kb/raw/research-fanout/research--kb--reports--agents--graphify-markdown-memory-context-2026-10-03-run3/deps/Graphify-Labs--graphify/1/manifest.json` |

The planner-level manifest is
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-03n/.agent/kb/raw/research-fanout/graphify-markdown-memory-frontmatter-query/manifest.json`.
It recorded github-issues (#2217) and firecrawl-developer hits; exa found the triage URLs.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://github.com/Graphify-Labs/graphify/pull/2875 | `…/handoff-2026-10-03o/docs/research/kb/raw/research--kb--reports--agents--graphify-markdown-memory-context-2026-10-03-run3/links/1.md` | 1 | 0 | firecrawl: Insufficient credits to perform this request |
| https://github.com/Graphify-Labs/graphify/pull/3348 | `…/links/2.md` | 1 | 0 | firecrawl: Insufficient credits to perform this request |
| https://github.com/Graphify-Labs/graphify/pull/1064 | `…/links/3.md` | 1 | 0 | firecrawl: Insufficient credits to perform this request |

All three caller links were still **read live** with `gh api`, in this synthesis and by the read-link lane. The claims
above cite those live reads. Only the offline copies are missing.

## Conflicts resolved

1. **How did PR #2875's change ship: as #2875 by cherry-pick, or through "#3822"?** One input claim says the vault-wide
   fallback "is in 0.9.73 shipped by #3822, not via PR #2875". **Trusted: the maintainer comment on #2875.**
   - safishamsi, 2026-08-20: "Shipped in v0.9.48 via authorship-preserving cherry-pick".
   - The fallback is present in the 0.9.73 source (`markdown.py:112-121`).
   - #3822 is not a PR. It returns 404 from `/pulls`. As an issue it is a *closed bug*: "Markdown wikilink index
     (`_build_link_index`) ignores .graphifyignore, walks ignored dirs and hangs update". That is a later defect report
     against the shipped feature, not the route it shipped by.

   The rule applied: the source code plus a maintainer statement beat a secondary paraphrase.
2. **"Merged" vs "shipped" for #2875.** GitHub says `merged=false` because the change was cherry-picked. The PR is
   closed unmerged, and the code shipped anyway. Both statements are true. The feature claim rests on the source.
3. **graphify's docs vs its code on frontmatter.** `ingest.py:299-300` says memory files carry "YAML frontmatter that
   graphify's extractor reads as node metadata". That is true: it is stored on the node. It does not mean the
   frontmatter is searchable. The scorer (`serve.py:437-448`) and the live `quokkafrontier` miss settle it: **stored,
   not searched.** Code and a measurement beat the docstring's implication.
4. **0.9.73 vs 0.9.74/0.9.75.** Inherited claims cover 0.9.73 only. The release diffs show that neither later release
   touches the search fields or frontmatter. The newer source agrees with the older, so the 0.9.73 conclusion carries
   forward. This is by diff, not by a 0.9.74 run (Gaps).

## Verification

Five refuter lanes, a critic and an adjudicator ran. UPHELD set (refuted or misleading, upheld by the adjudicator):
**empty**. No claim in the Answer or Recommendation was corrected, struck or qualified as a result.

| # | load-bearing claim | status | evidence |
|---|---|---|---|
| 1 | `graphify query` does not search markdown frontmatter (0.9.73); page node stores it under `frontmatter`; search text reads only label, tokens, id, source, rationale, attributes; only Terraform writes `attributes` | **confirmed** (refuter's "misleading" overturned by the adjudicator) | `serve.py:342-347` and `:437-448`, `markdown.py:408-413`, `terraform.py:459`; package-wide grep finds no other writer; `q-quokkafrontier` misses while `graph.json` holds it, `q-zebrastripe` hits. The refuter's omission charge (body prose also unsearchable, data is stored not lost) is already stated in Answer item 2 and its table (`pelicanbody`, `quokkafrontier` "stored, not searched"). Scope is `query` and the page node only; `explain`, `path` and MCP serve were not tested (Gaps). |
| 2 | Keyless `graphify update` never stores body prose; only page, heading, link/wikilink and code-span nodes/edges; body-only word has 0 occurrences | **confirmed** (refuter's "misleading" overturned) | Refuter's own live re-run: `pelicanbody` 0, heading `Sub` 1, frontmatter word 1. Frontmatter storage and symbol-resolved code spans are already in Answer item 1. The refuter's "stale citation" charge was wrong: `markdown.py:296-347` is the `extract_markdown` def and docstring in 0.9.73. |
| 3 | Only LLM semantic extraction makes prose searchable; lossy, not full-text | **confirmed, with a reading note** (refuter's "refuted" overturned) | The refuter's counterexample (24449 heading-labelled `.md` nodes) is heading text, which the report already says is searchable keyless. "Prose" here means body and `description:` text. Body prose is not indexed full-text by either path (refuter concedes). Do not read this claim as "markdown is unsearchable without an LLM". |
| 4 | 0.9.74 and 0.9.75 change neither query search fields nor frontmatter handling | **confirmed** | `compare` diffs: `serve.py` untouched in 0.9.74; 0.9.75 `serve.py` is a shortest-path reverse `contains` hop (#3878), 0 `frontmatter` hits; 0.9.74 `markdown.py` adds dotted-wikilink `.md` completion only. CHANGELOG and tracker routes agree; controls armed. By diff, not by a 0.9.74 run. |
| 5 | PRs #1064 and #3348 OPEN/unmerged and not in 0.9.73/0.9.74; #1064 summarizes the code graph; #2875 fallback shipped in v0.9.48 by cherry-pick | **confirmed** | Live `gh api`: #1064 and #3348 open, merged=false; `memory_index.py` reads `graph.json`; maintainer comment and v0.9.48 release body cite #2875. Minor: #2875 is closed, not merged; v0.9.75 notes were not checked for these PRs. |
| 6 | Tier 0 (plain grep) is the right tier now | **unverified as a measurement** | Argued from a two-file synthetic fixture, not the real memory dir (critic gap). |
| 7 | Third-party usage; LLM-mode recall; upstream issues #295/#613/#131 | **unverified** | Never read or run (see Gaps). |

Steps: critic ran and returned 8 gaps (appended below). Adjudicator ran and returned 3 verdicts, all overturning the
refuters. Failed stages: none. Mandatory gaps: none.

**How the conclusion changes:** it does not. Tier 0 stands. The one added caution is claim 3's reading note: headings and
labels are searchable keyless; body and `description:` text are not.

## Gaps

- **MIRROR GAP:** https://github.com/Graphify-Labs/graphify/pull/2875 was not mirrored (firecrawl: Insufficient
  credits). Its content was read live, but no offline copy exists.
- **MIRROR GAP:** https://github.com/Graphify-Labs/graphify/pull/3348 was not mirrored (same failure). Read live only.
- **MIRROR GAP:** https://github.com/Graphify-Labs/graphify/pull/1064 was not mirrored (same failure). Read live only.
- **CODE SEARCH GAP (unverifiedEmpty):** `repo:Graphify-Labs/graphify filename:serve.py frontmatter` returned 0. The
  query was armed (the `serve.py score` must-hit = 2), and a local source grep corroborates the 0. Still, a
  code-search 0 is a gap, not proof of absence. The proof here rests on the source read and the live run.
- **unverifiedEmpty:** the known-absent control `qzv9060000wkx` returned 0, as expected. That is a control, not a
  finding. It is listed because the input lists it.
- **unverifiedEmpty:** github-discussions came back `empty_verified`. Its control (query `graphify`) returned 10, but
  no discussion matched the memory query. Discussions where people describe this use are therefore **unknown**, not
  absent.
- **Third-party usage was never read:**
  - https://github.com/mycelium-hq/ai-brain-starter/blob/main/skills/graphify/SKILL.md
  - https://neoneye.github.io/agent-memory-atlas/systems/graphify/
  - https://deepwiki.com/safishamsi/graphify/2.6-work-memory-and-reflection

  "How people use it" in practice is therefore answered only from graphify's own shipped features.
- **Related upstream threads were never read:**
  - https://github.com/Graphify-Labs/graphify/issues/295 (structural pre-extraction pass: wikilinks + frontmatter)
  - https://github.com/Graphify-Labs/graphify/issues/613 (Noema connector: frontmatter as ground truth)
  - https://github.com/safishamsi/graphify/issues/131 (frontmatter-aware cache)

  Any of them may be a ready-made upstream ask for making frontmatter searchable. Their state is unknown.
- **LLM-mode recall was not measured.** Whether semantic extraction keeps a `description:` keyword as a label or in a
  `rationale` field was not run. Claim 3's "lossy summary" comes from the code path, not from a measurement.
- **0.9.74 and 0.9.75 were not run.** They were checked by GitHub compare diff only. The live probe used the pinned
  0.9.73.
- **No search was run for `frontmatter` inside the three PR threads.** Their silence on body and frontmatter indexing
  is unsearched, not proven.

Critic gaps (each with its next probe):

- **Third-party usage unread** (ai-brain-starter SKILL.md, Agent Memory Atlas, DeepWiki Work Memory). Next probe: read
  the three URLs live; tag each claim as documented-by-others, not shipped.
- **LLM semantic mode recall unmeasured.** Next probe: run `graphify extract` (or skill Part B) with a key on the same
  two-file fixture, query `quokkafrontier` and `pelicanbody`, grep `graph.json` for label/rationale, record token cost.
- **0.9.74 never run.** Next probe: `uvx --from graphifyy==0.9.74` in an isolated env, rerun the fixture queries, grep
  `serve.py` for `frontmatter`.
- **Upstream issues #295, #613, #131 unread**, so the "optional upstream ask" may already exist. Next probe: `gh api` on
  each, plus an issue search for `frontmatter query` and `search attributes`, closed included.
- **Discussions empty and PR thread bodies unsearched; no real-world memory-dir usage reports found.** Next probe: search
  issues and discussions for `auto-memory`, `MEMORY.md`, `obsidian vault query`; grep PR #2875/#3348/#1064 comments for
  `frontmatter`.
- **Other query paths unchecked** (MCP serve tools, `explain`, `path`, embedding or semantic flags). Next probe: grep the
  CLI for query flags and vector options; run `explain` and the MCP query tool on the `quokkafrontier` fixture.
- **No Tier 0 vs Tier 1 comparison on the real memory dir.** Next probe: run `graphify update` on a copy of it, count
  page and edge nodes, and compare 5 real recall questions against grep for hit rate and token cost.
- **Offline mirrors of the PRs and pages absent** (firecrawl out of credits). Next probe: save `gh api` JSON for PRs
  #2875, #3348, #1064 into the raw dir, or re-run the mirror step once credits exist.

## Recommendation

1. **Choose Tier 0 now: plain `grep`/`rg` over the memory dir** (or `MEMORY.md` plus a targeted grep). It is the only
   option that matches `description:` and body words, and it is the native tool (`use-tool-builtins.md`).
2. **Do not build Tier 1 on keyless graphify for recall.** It would find filenames and headings, both of which grep
   already covers, and miss the description and body. Build it only if *link structure* across memories (wikilink
   backlinks) becomes a real need. If so, it is a thin mise task over `graphify update <memory-dir>` +
   `graphify query`, documented as structure-only.
3. **Defer anything prose-aware to Tier 2 (#997).** The ways to get prose recall are:
   - LLM semantic extraction: tokens, lossy, and the cache ignores frontmatter edits (`cache.py:443`);
   - an upstream change to read `frontmatter` in `_node_attributes_text`;
   - a real full-text index.

   All of these are Tier-2-sized.
4. **Optional upstream ask:** extend the `serve.py` attributes tier to read the markdown `frontmatter` attribute.
   Before filing, read issues #295 and #613, which may already carry it.
5. **Re-run to close the gaps** once firecrawl has credits: mirror the three caller links and the three third-party
   pages.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:Graphify-Labs/graphify | general-purpose | sonnet | low |
| mirror:1/3 | general-purpose | haiku | (default) |
| mirror:2/3 | general-purpose | haiku | (default) |
| mirror:3/3 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

Prior run: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-03n/docs/research/kb/reports/agents/graphify-markdown-memory-context-2026-10-03-degraded-run1.md`.
Its conclusions agree with this run. This run closes its two named gaps: it re-armed the code search on the correct
slug, and it checked 0.9.74.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — PRs #2875/#3348/#1064 read live, issue #3822,
  releases, and the v0.9.73…v0.9.75 compare diffs; pinned 0.9.73 source read on disk; code search
- [safishamsi/graphify](https://github.com/safishamsi/graphify) — the old slug; appears in the triage hits (`skill.md`
  v4, issue #131); not read
- [mycelium-hq/ai-brain-starter](https://github.com/mycelium-hq/ai-brain-starter) — third-party graphify skill, in
  triage only; not read
- [cli/cli](https://github.com/cli/cli) — code-search health control only
