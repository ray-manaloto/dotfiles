# graphify over markdown / memory / Obsidian vaults: what is indexed, what is searchable (2026-10-03)

> **Persistence note.** The tracked target
> `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-03l/docs/research/kb/reports/agents/graphify-markdown-memory-context-2026-10-03.md`
> was REFUSED by the Write tool partway through. The tool's own message was: "This session is isolated in the worktree
> …/coordinator-bgisolation. Edit the worktree copy of this file instead of the shared-checkout path."
>
> This copy is in the scratchpad. The coordinator must copy it verbatim to the tracked path.

Question: how do people use graphify (Graphify-Labs/graphify, formerly safishamsi/graphify, PyPI `graphifyy`) to cut
agent context over markdown/notes/memory directories, and does graphify index markdown BODY text and frontmatter
(`description:`) for query, or only titles/headings/links? Which mode indexes prose? Prior claim under test (lane G,
graphify 0.9.73): "only page/heading names + links are indexed; bodies and frontmatter descriptions are not searched."

## Answer

**The sweep is INCOMPLETE.** One mandatory gap: the planner's code-search PROBE-JSON line was not copied into the
synthesis input. The file it should have come from does exist
(`.agent/kb/raw/research-fanout/research--kb--reports--agents--graphify-markdown-memory-context-2026-10-03/plan/code-search.json`).
It shows all four queries returned 0, **including the must-hit query**, against the renamed `safishamsi/graphify`
slug. So that code search was never armed and answered nothing (see Gaps). context7 also errored.

Below, a claim marked SHIPS is backed by the pinned 0.9.73 source read on disk **and** a real run on a probe corpus.
A claim marked PROPOSED comes from an open PR. A claim marked THIRD PARTY comes from someone else's README.

1. **SHIPS: graphify's keyless (no-LLM) mode extracts markdown, but in a fixed, limited way.** `graphify update <dir>`
   prints "Re-extracting code files … (no LLM needed)", but it still sends `.md/.mdx/.qmd/.skill` through
   `extract_markdown`. That extractor emits:
   - one `page` node per file, with YAML frontmatter stored in a `frontmatter` attribute;
   - one `heading` node per heading, joined by `contains` edges;
   - a `references` edge for each inline link, reference-style link or `[[wikilink]]`. Links inside frontmatter count
     too, and a wikilink that misses its sibling path falls back to a lookup across the whole vault;
   - an INFERRED or EXTRACTED `references` edge from a heading or page to a code symbol, for each backtick code span
     that resolves to that symbol.

   **Ordinary body prose is not stored anywhere in `graph.json`.**
2. **SHIPS: `graphify query` does not search frontmatter.** It is stored on the node but never matched. The query
   scorer reads only:
   - `label`, `norm_label`, `source_file` and the node id;
   - `rationale`;
   - a node attribute named `attributes`, which only the Terraform extractor writes.

   The markdown extractor writes `frontmatter`, so `description:` text is invisible to query. Measured on 0.9.73: a
   word that appears only in the frontmatter `description` is present in `graph.json`, yet
   `graphify query "<word>"` returns "No matching nodes found." The positive control, a heading word, returns the
   heading. Upstream `v8` HEAD has the same shape: its `serve.py` contains `frontmatter` 0 times and
   `_node_attributes_text` 3 times.
3. **Verdict on lane G's claim: correct about searching, but stated too broadly.**
   - Correct: bodies and frontmatter descriptions are not searched by query in keyless mode.
   - Wrong if read literally as "only names and links are indexed". The page node does store frontmatter (it can be
     read through `explain` or the node JSON, though query cannot find it), and backtick code spans in body text
     become edges.
   - The CLAIMS input called lane G "PARTIALLY INCORRECT" because frontmatter is "parsed and included". That mixes up
     storing a field with being able to search it. **Storing it is not the same as searching it**, and on searching,
     lane G is right.
4. **Prose becomes searchable only through LLM semantic extraction (the `/graphify` skill or `graphify extract`).**
   This mode costs tokens. The model invents concept nodes and their labels, and it records "why" text in a `rationale`
   attribute, which the query scorer does read (the rationale tier). That is an LLM-written summary of the prose, not a
   full-text index of it.
   - SHIPS in code: the prompt and the scoring path.
   - NOT RUN here: no end-to-end semantic probe.

   Another code-level detail: for `.md` files the semantic cache hashes only the body below the frontmatter. So editing
   only a memory file's `description:` does not trigger re-extraction.
5. **How people use it (THIRD PARTY; only one of three real examples applies graphify to markdown memory):**
   - `albertludi/second-brain-claude` runs a weekly headless `claude -p /graphify` (the LLM mode) over the markdown
     notes Claude writes, then syncs the result to Obsidian.
   - `gavishap/omnia-vault` and `marcoz93/claude-code-memory-setup` run graphify over **code repos**. They keep
     markdown notes in a separate layer (a wiki catalog or the vault) and query the code graph first.
   - PROPOSED, not shipped: PR #1064, "memory-index export for LLM context retention", is OPEN and its command is
     absent from 0.9.73.

**Bottom line for a Claude Code auto-memory dir.** Keyless graphify over `memory/*.md` gives you a link graph: file,
heading and wikilink structure, plus edges to the code symbols named in backticks. It **cannot** answer a query whose
words appear only in a memory's `description:` or body. Getting that recall means either:
- paying for LLM extraction, which yields lossy concept and rationale summaries; or
- changing the memory format so that the words you search for appear in headings, link names or backtick spans.

## Evidence

| claim | URL or file:line | quote |
|---|---|---|
| Pinned version is 0.9.73 | `python/.venv/bin/graphify --version` → `/tmp/gfy-md-probe-1003/ver.log` | `graphify 0.9.73` / `rc=0` |
| `.md` routed to the deterministic extractor | `site-packages/graphify/extract.py:6771-6774` | `".md": extract_markdown, ".mdx": extract_markdown, ".qmd": extract_markdown, ".skill": extract_markdown,` |
| Page node carries frontmatter under key `frontmatter` | `site-packages/graphify/extractors/markdown.py:411-413` | `add_node(file_nid, path.name, 1, node_kind="page", extra={"frontmatter": frontmatter} if frontmatter else None)` |
| Frontmatter links still followed | `extractors/markdown.py:342-345` | "Leading YAML frontmatter is parsed onto the page node … Links inside it are still followed" |
| Body prose: only code spans are consumed | `extractors/markdown.py:509-513` | "Body prose: a code span cites a symbol on behalf of the enclosing heading … `for m in _MD_CODE_SPAN_RE.finditer(line_text): add_mention(owner, …)`" |
| Code-span mention needs a symbol-shaped span (no spaces) | `extractors/markdown.py:275-277` | `if not text or " " in text: return None` |
| Vault-wide wikilink fallback shipped | `extractors/markdown.py:112-121,250-260` | "Obsidian-style vaults resolve a [[wikilink]] by vault-global filename lookup … The fallback … only fires when the lexically resolved path does not exist" |
| Same-page `[[#Heading]]` not matched in 0.9.73 | `extractors/markdown.py:18` (regex excludes a leading `#`); PR #3348 OPEN | `_MD_WIKILINK_RE = re.compile(r'(?<!\!)\[\[([^\]|#]+?)…` |
| Query search text = label/id/source/rationale/`attributes` only | `site-packages/graphify/serve.py:432-448` | `fields = (norm_label, label_tokens, nid_text, source, source_tokens)` … `rationale` … `attr_norm, attr_tokens = _node_attributes_text(data)` |
| `attributes` reads key `attributes`, not `frontmatter` | `serve.py:342-344` | `attrs = data.get("attributes")` |
| Only Terraform writes `attributes` | `extractors/terraform.py:459` (sole writer found by grep) | `nodes_by_id[owner]["attributes"] = attrs` |
| Upstream v8 HEAD same shape | `gh api …/contents/graphify/serve.py?ref=v8` → `/tmp/gfy-md-probe-1003/serve-v8.py` (128,336 bytes) | `grep -n frontmatter` → 0 lines; control `grep -c _node_attributes_text` → 3 |
| Upstream v8 markdown still stores `frontmatter` | `/tmp/gfy-md-probe-1003/markdown-v8.py:430` | `extra={"frontmatter": frontmatter} if frontmatter else None)` |
| **Live probe: keyless update extracts markdown** | `/tmp/gfy-md-probe-1003/update.log` | "Re-extracting code files … (no LLM needed)" … "Rebuilt: 7 nodes, 6 edges, 3 communities" `rc=0` |
| Live probe: frontmatter stored | `/tmp/gfy-md-probe-1003/graphify-out/graph.json` node `notes_memo` | `'frontmatter': {'name': 'memo', 'description': 'the plovercask feature lives in frontmatter only'}` |
| Live probe: body prose NOT stored | `grep -c quillmarrow graph.json` | `0` (frontmatter term `plovercask` → `1`, heading term `Wobblestone` → `1`) |
| Live probe: wikilink + code-span edges | graph.json edges | `notes_memo - references -> notes_other EXTRACTED`; `notes_memo_gannet_wobblestone_heading - references -> thing_brisketwidget INFERRED` |
| **Live probe POSITIVE arm: heading term found** | `/tmp/gfy-md-probe-1003/q1.log` | `Start: ['Gannet Wobblestone Heading'] | 6 nodes found` `rc=0` |
| **Live probe: frontmatter-only term NOT found** | `/tmp/gfy-md-probe-1003/q2.log` | `No matching nodes found.` `rc=0` |
| Live probe: body-only term NOT found | `/tmp/gfy-md-probe-1003/q3.log` | `No matching nodes found.` `rc=0` |
| Semantic mode: LLM writes concept nodes + `rationale` | `site-packages/graphify/llm.py:482-489` | "Extract a knowledge graph fragment from the files provided … Rationale (WHY decisions were made …): store as a `rationale` attribute on the relevant node" |
| Rationale is a query tier | `serve.py:685-690` | "Rationale tier (#2293): recall for "why" questions whose words live only in the attribute." |
| Semantic cache ignores frontmatter edits | `site-packages/graphify/cache.py:178-190` (+ docstring at :443) | "Strip YAML frontmatter from Markdown content, returning only the body." |
| Two-pass model (docs = LLM, costs tokens) | https://raw.githubusercontent.com/Graphify-Labs/graphify/v8/docs/how-it-works.md (from CLAIMS input) | "Pass 3 — Docs, papers, images (Claude subagents, costs tokens): Claude runs in parallel over markdown, PDFs…" |
| PROPOSED: memory-index export | https://github.com/Graphify-Labs/graphify/pull/1064 (state `open`, merged=null) | "adds a new `graphify export memory-index` command … 97% token reduction (~55K → 2K tokens per session start)" |
| memory-index absent in 0.9.73 | `grep -c 'memory-index\|memory_index' cli.py export.py` → 0, 0; control `grep -c obsidian cli.py` → 12 | — |
| PR #2875 closed unmerged, yet vault fallback shipped by other route | `gh api …/pulls/2875` → `closed merged=null`; markdown-v8.py:153 cites `#3822` | "or ignored paths (#3822)." |
| THIRD PARTY: LLM `/graphify` over markdown memory notes | https://github.com/albertludi/second-brain-claude (WebFetch summary, small-model) | "Sunday 00:00 UTC | Headless graph rebuild (`claude -p /graphify`)"; "`graphify_auto_rebuild.sh # weekly rebuild + Obsidian sync`" |
| THIRD PARTY: graphify on code; notes in a separate layer | https://github.com/gavishap/omnia-vault (WebFetch summary) | "| `graphify` | any folder / repo / paper / video → queryable knowledge graph" ; layer 1 "Code graph `graphify query`" → layer 2 "Wiki catalog" |
| THIRD PARTY: code → graph → vault, AST default | https://github.com/marcoz93/claude-code-memory-setup (WebFetch summary) | "processed 100% locally via tree-sitter AST. No code content leaves your machine." |
| Usage friction: agents ignore the graph | https://github.com/Graphify-Labs/graphify/issues/1227 (closed) | "in real scenarios, claude code never uses graphify at all" |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:Graphify-Labs/graphify filename:README.md` | must-hit | workflow | 6 | 0 |
| `repo:safishamsi/graphify frontmatter description markdown` | query | plan/code-search.json (not copied into input) | 0 UNARMED | 0 |
| `repo:safishamsi/graphify obsidian vault markdown` | query | plan/code-search.json (not copied into input) | 0 UNARMED | 0 |
| `repo:safishamsi/graphify graphify` | must-hit | plan/code-search.json (not copied into input) | 0 UNARMED (must-hit failed) | 0 |
| `repo:safishamsi/graphify qwvzjkplx7r4mnb` | known-absent | plan/code-search.json (not copied into input) | 0 | 0 |
| `repo:safishamsi/graphify filename:README.md` | readme | deps/safishamsi--graphify/probe.json | 0 UNARMED | 0 |

Note: neither workflow row was rate-limited (`rateLimited=false`). The health arm (9) and the must-hit arm (6) both
discriminate, so the workflow probe of the **new** slug is armed.

Note: every `safishamsi/graphify` row has `incomplete_results: true`, and its must-hit row returned 0. GitHub code
search does not follow a repository rename, so the old slug cannot hit. Those zeros are UNARMED and mean "never asked",
not "absent".

### Dependency-repo fan-out

| repo | query | required sources failed | manifest |
|---|---|---|---|
| Graphify-Labs/graphify | graphify markdown memory context | none (issues ok; discussions empty_verified, control 10; releases empty_verified, control 1) | `.agent/kb/raw/research-fanout/research--kb--reports--agents--graphify-markdown-memory-context-2026-10-03/deps/Graphify-Labs--graphify/1/manifest.json` |
| safishamsi/graphify (not in DEPENDENCY RUNS input; found on disk) | graphify markdown memory notes | github-issues: error (HTTP 422); github-discussions: empty_unverified (canary 0) | `.agent/kb/raw/research-fanout/research--kb--reports--agents--graphify-markdown-memory-context-2026-10-03/deps/safishamsi--graphify/1/manifest.json` |

The top-level fan-out manifest is
`.agent/kb/raw/research-fanout/graphify-markdown-memory-obsidian-vault-context/manifest.json`. In it: exa ok,
firecrawl-developer ok, last30days ok, **context7 error (exited 1)**.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| _(no MIRRORS rows in input)_ | — | — | — | No link was mirrored, so there is no offline copy of the third-party READMEs. See Gaps. |

## Conflicts resolved

- **The CLAIMS input calls lane G "PARTIALLY INCORRECT"; the source code says lane G is correct about search.** I
  trusted the shipped 0.9.73 source and a live run with both control arms, over the CLAIMS row. That row read
  "parsed and included on the file node" as if it meant "searchable". `serve.py`'s search fields never read
  `frontmatter`, and the live query for a frontmatter-only word returned nothing while the heading-word arm hit.
  Resolution: lane G is right that query does not search frontmatter or body text, and wrong only if read as "nothing
  else is stored".
- **"Body text IS indexed" (CLAIMS) versus "bodies are not searched" (lane G).** Both are partly true. Only backtick
  spans shaped like symbols are consumed, and they become edges to code symbols, not searchable text. Ordinary prose is
  never written to `graph.json` (`quillmarrow` count 0). Source code and the live run beat both summaries.
- **The keyless CLI message says "code files"; the code also extracts markdown.** The live run decides it: the page and
  heading nodes for `notes/*.md` were produced by `graphify update`. The message is misleading.
- **The docs say docs go to Claude subagents (pass 3); the code has a deterministic markdown extractor too.** Both
  ship. The AST pass gives structure, and only the LLM pass reads prose. The newer source and the live run outrank the
  how-it-works doc on what keyless mode covers.
- **PR #2875, "vault-wide wikilinks", is closed and unmerged, but the feature is in 0.9.73.** I trusted the shipped
  source (`_vault_lookup`, which cites #3822). The feature landed through another change, so the PR's state is not
  evidence that it is missing.
- **Third-party example summaries came from WebFetch's small model, not verbatim reads.** I treated them as weaker than
  first-party source and did not let them decide any indexing claim.

## Gaps

- **MANDATORY GAP:** code search has no PROBE-JSON line for `plan/code-search.json`, so the planner's code-search line
  was not copied into the input. The file exists on disk, but all four of its probes, including the must-hit, returned
  0 against the renamed slug. That code search is **unarmed and answered nothing**.
- **context7 errored** (`exited 1`), so its content is unknown.
- **safishamsi/graphify dependency run failed:**
  - github-issues failed with HTTP 422;
  - github-discussions was `empty_unverified`, because its canary returned 0;
  - so whatever those two sources hold under the old slug is unknown.
- **Empty but verified (control-armed), not gaps in themselves:**
  - github-discussions for Graphify-Labs: 0 hits, control 10;
  - github-releases for Graphify-Labs: 0 hits, control 1.

  Even so, I did not read any release note for the 0.9.73→0.9.74 change (0.9.74 is current on PyPI). Whether 0.9.74
  changes frontmatter search is **unverified** for the release. v8 HEAD `serve.py` was checked and has no frontmatter
  search.
- **No MIRRORS rows.** None of the third-party READMEs has an offline firecrawl mirror under `docs/research/kb/raw/`.
- **Semantic (LLM) mode was not run end to end.** Whether it makes the words of a `description:` searchable, through
  concept labels or rationale, is inferred from code and unmeasured. It also depends on the model.
- **Bash access was lost mid-sweep.** Partway through, a worktree-isolation guard began refusing every Bash command
  (and the Write to the tracked path) because the session's worktree had changed to `coordinator-bgisolation`. As a
  result:
  - the README fetches for the three examples fell back to WebFetch summaries, not verbatim `gh api` reads;
  - stale `/tmp/gfy-md-probe-1003/{omnia,albert,marcoz}.md` files, if any, are not evidence.
- **No GitHub code search ran for real-world `graphify` runs over `memory/` or vault directories** (for example,
  `graphify-out` committed next to `.obsidian/`). The number of examples is therefore a sample of 3, not a census.
- **Blog and secondary sources were not read:** stork.ai, ai-tldr.dev, the yingding fork, and skill.md v4.

### Critic gaps (appended by the reconcile node)

- **0.9.74 and its release notes were never read.** Only v8 HEAD `serve.py` was grepped, so whether frontmatter search or
  the memory-index export changed between 0.9.73 and 0.9.74 is unconfirmed. Next probe: download `graphifyy==0.9.74`,
  grep `serve.py` and `extractors/markdown.py` for `frontmatter`, re-run the plovercask/quillmarrow probe, and read the
  release notes with `gh release view`.
- **Semantic/LLM mode was never run end to end.** That a `description:` or body word becomes searchable through concept
  labels or `rationale` is inferred from code only. Next probe: on the same probe corpus run `graphify extract` (or
  `/graphify`) with a key, query the frontmatter-only and body-only terms, and record whether each hits and via label or
  rationale.
- **Real GitHub examples are thin and second-hand.** Only 3 repos, read through small-model WebFetch summaries, and only
  one (`albertludi/second-brain-claude`) runs graphify over markdown memory. Next probe: fetch the three READMEs verbatim
  (`gh api` contents or firecrawl into `docs/research/kb/raw/`), quote the exact graphify invocation and target dir, then
  run `gh search code` against `Graphify-Labs/graphify` and generally (`graphify-out` near `.obsidian`, `graphify update`
  with `memory/`).
- **Code search for the renamed slug was unarmed.** Every `safishamsi/graphify` probe returned 0, including the
  must-hit; the planner's `code-search.json` was never ingested; the safishamsi issues query returned HTTP 422 and
  discussions were `empty_unverified`. Next probe: re-run issue, discussion and code searches against
  `Graphify-Labs/graphify` only, each with a health control and a known-present control (terms: obsidian, frontmatter,
  memory, wikilink, description).
- **PR #1064 was read from its page only.** Its diff, the author's measurement method for the 97% token reduction, and
  whether a similar shipped feature exists (other export modes, a `query --budget` flag) were not checked. Next probe:
  `gh pr view 1064 --json files,body,comments`, grep 0.9.73 `cli.py` for export subcommands and budget/token flags, and
  search issues for token/context/memory.
- **No duplicate check for the suggested upstream issue.** Whether "extend `_node_attributes_text` to read frontmatter"
  already exists as an issue or PR is unchecked; #3625 and #3348 are cited as one-liners and not read. Next probe:
  search issues and PRs in `Graphify-Labs/graphify` for frontmatter, description, markdown search, query body, and read
  #3625 and #3348 for maintainer intent.
- **Other query surfaces were not tested.** MCP serve tools, `explain`, `path` and the `graph.html` viewer were not
  checked for frontmatter search (only the `graphify query` CLI was), and `docs/how-it-works.md` was read second-hand.
  Alternative memory-search tools (Obsidian MCP, qmd, basic-memory, claude-mem) were not compared. Next probe: grep the
  `serve.py` MCP handlers for `frontmatter`, read `docs/how-it-works.md` and the README at the v8 and 0.9.73 tags, and run
  a brief alternatives search.
- **context7 errored, so official docs via context7 were never consulted.** The stale-cache detail (the semantic cache
  hashes only the body, so a description-only edit does not re-extract) is from code reading only, not a run. Next probe:
  retry `resolve-library-id` for graphifyy/Graphify-Labs, and for the cache claim edit only a `description:` in the probe
  corpus, run the semantic extract, and confirm the file is served from cache.

## Recommendation

1. **Keep lane G's practical conclusion, with corrected wording.** Write "keyless graphify stores frontmatter on the
   page node but `graphify query` does not search it; body prose is not stored, only backtick code spans (as edges to
   code) and links". Do not write "only names and links are indexed".
2. **Do not count on graphify to shrink the context of the auto-memory index today.** Matching on
   `description:` / `MEMORY.md` hooks needs full-text search. `grep` / `rg` over the memory dir is the native tool
   that already does it.
3. If a graph over memory files is wanted anyway, run keyless `graphify update <memory-dir>` for **link and wikilink
   structure only**. Optionally, write the key nouns into a memory's H1/H2 so they become searchable labels.
4. Track upstream as follow-ups, not as dependencies:
   - PR #1064 (memory-index export), OPEN;
   - PR #3348 (same-page wikilinks), OPEN;
   - an upstream issue, possibly to file: extend `_node_attributes_text` to read the markdown `frontmatter` attribute,
     the same way the Terraform `attributes` tier #3625 did.

   Before filing, re-check 0.9.74's release notes and source.
5. Close the gaps: re-run the code search against `Graphify-Labs/graphify` (the safishamsi slug cannot hit), and
   mirror the three example READMEs with firecrawl.

## Verification

Five load-bearing claims were each refuted-or-confirmed by an independent refuter, then a critic and an adjudicator ran.
All stages ran; none returned null and none failed. The UPHELD list is empty: no claim was upheld as refuted or
misleading, so nothing in the Answer or Recommendation was struck or corrected.

| # | claim | status | evidence |
|---|---|---|---|
| 1 | `graphify query` (0.9.73) does not search markdown frontmatter | **confirmed** | `serve.py:342-344` reads only `attributes`; search text at `serve.py:432-448` has no `frontmatter`; only `terraform.py:459` writes `attributes`. Live: `plovercask` (frontmatter-only) is in `graph.json` once, query returns "No matching nodes found."; heading word `Wobblestone` hits. |
| 2 | Keyless update extracts markdown (page+frontmatter, headings, link/wikilink edges, code-span edges) | **confirmed** | `extract.py:6771-6774`, `extractors/markdown.py`; the probe `graph.json` holds a page node with frontmatter, heading nodes, a wikilink `references` edge and a heading to `BrisketWidget` INFERRED edge. Inline links, reference-style links, frontmatter links and the vault-wide fallback are verified from source only, not exercised by the probe. |
| 3 | Ordinary body prose is never written to `graph.json` in keyless mode | **confirmed (the refuter's "misleading" flag was overturned by the adjudicator)** | `markdown.py:509-513` only handles code spans on body lines; `quillmarrow` count 0 vs `BrisketWidget` 5, `Wobblestone` 1, `plovercask` 1. The refuter's omissions (frontmatter stored, headings, link and code-span edges, LLM mode) are already stated beside the claim in the Answer. I read `q3.log` but did not re-run the query. Scope: 0.9.73, keyless only. |
| 4 | Prose becomes searchable only through LLM extraction (concept labels plus `rationale`) | **confirmed (the refuter's "refuted" and "misleading" verdicts were overturned by the adjudicator)** | The refuter objected that headings are searchable without an LLM. The report treats headings separately from body prose, and no non-LLM field holds body text (`serve.py` search fields, no `rationale` or `attributes` from the markdown extractor). `llm.py:489` and `serve.py:685-690` confirmed. Caveat: ingest/export/extractors modules matching embedding/bm25/full-text grep were not opened, so a hidden full-text path is not fully ruled out, though it would have no body text to match. The LLM half remains unmeasured (NOT RUN). |
| 5 | v8 `serve.py` has 0 `frontmatter` (control `_node_attributes_text` = 3); PR #1064 OPEN and absent from 0.9.73 | **confirmed** | Re-fetched v8 `serve.py`: 0 and 3. Repo-wide `frontmatter` code search = 73 hits (discriminates). PR #1064 `state=open merged=false`. `memory-index` absent at tag v0.9.73 `__main__.py`. Caveats: the original grep targeted `cli.py`/`export.py`, but the PR touches `__main__.py` and a new `memory_index.py` (re-probed, still 0); 0.9.74 was not checked. |

Verifier omissions worth carrying: markdown search in keyless mode is limited to headings, file names and code spans;
the `frontmatter` field is readable by other tooling even though query cannot find it.

**How the conclusion changes: it does not.** Lane G is right about search, the "stated too broadly" correction stands,
and the Recommendation is unchanged. The sweep stays INCOMPLETE (mandatory code-search gap plus the critic gaps above).

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:Graphify-Labs/graphify | general-purpose | sonnet | low |
| triage | Explore | sonnet | low |
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

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — v8 `serve.py` + `extractors/markdown.py` source; PRs #1064, #2875, #3348; issues #1227, #3625
- [safishamsi/graphify](https://github.com/safishamsi/graphify) — former slug; code-search + dep fan-out probes (unarmed / 422)
- [gavishap/omnia-vault](https://github.com/gavishap/omnia-vault) — third-party layered-memory example (graphify on code)
- [albertludi/second-brain-claude](https://github.com/albertludi/second-brain-claude) — third-party example: `claude -p /graphify` over markdown memory notes
- [marcoz93/claude-code-memory-setup](https://github.com/marcoz93/claude-code-memory-setup) — third-party example: code → graph → Obsidian vault
- [cli/cli](https://github.com/cli/cli) — code-search health control arm only
