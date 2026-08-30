# Cold review — `fix/graphify-health-links-schema` (composed `origin/main...HEAD`)

Reviewer: opus-cold-review-graphify (Claude Opus 5), cold — no design brief.
Refs: `325271c`, `6d71b8b`; reviewed as the composed `git diff origin/main...HEAD`.

Files read: `python/src/dotfiles_setup/graphify.py`, `python/src/dotfiles_setup/doc_refs.py`,
`tests/test_graphify.py`, `.claude/rules/graphify-first.md`, `.claude/CLAUDE.md`,
`.claude/rules/md-size-budgets.md`, `.claude/settings.json`, `scripts/graphify-hook-guard.sh`,
`mise.toml`, `python/.venv/lib/python3.14/site-packages/graphify/export.py`,
`../knowledge-base/python/src/kb_setup/graph.py`, both persisted audit reports in the diff.

**Verdict: "no findings" would NOT be an honest verdict.** The code change is correct and
well-motivated — the real `graphify-out/graph.json` in this repo is verifiably `links`-keyed
with 18,785 links and **no `edges` key at all**, so the old check made every graph here
permanently CORRUPT/STALE. Two HIGH findings concern what the change *gives up* and what the
accompanying prose *fails to reconcile*, not the fix itself.

---

## Probes run (with control arms)

| Claim under test | Probe | Result |
|---|---|---|
| two graphify versions installed | `which -a graphify`; `~/.config/mise/config.toml:288`; `python/pyproject.toml:9` | PATH → `~/.local/share/mise/installs/pipx-graphifyy/**0.9.53**/bin/graphify`. Repo venv → `python/.venv/bin/graphify`, `importlib.metadata.version("graphifyy")` = **0.9.42**. `shutil.which("graphify")` *inside* `uv run --project python` → the venv binary. **CLAIM CONFIRMED**, including that `mise run graphify-query` really does reach 0.9.42. |
| nothing in this repo writes `build-receipt.json` | `git grep -n "build-receipt\|GraphifyBuildReceipt"` | Hits only in `graphify.py` (reader), `doc_refs.py` (allowlist), `tests/test_graphify.py` (fixtures), docs. Control arm: identical grep shape for `GraphifyStatus` → 2 source files, so the grep is not blind. **CLAIM CONFIRMED.** |
| real graph shape | `json.load('graphify-out/graph.json')` | top keys `['built_at_commit','directed','graph','hyperedges','links','multigraph','nodes']`; `nodes` 13,344, `links` 18,785, `hyperedges` 0, **`edges` ABSENT**. |
| exporter really writes `links` | `graphify/export.py:301-304, 315, 329` | `node_link_data(G, edges="links")` inside a `try/except TypeError`; lines 315 and 329 then index `data["links"]` **unconditionally**. |
| `prune_dangling_edges` fallback | `graphify/export.py:380` | `links_key = "links" if "links" in graph_data else "edges"` — the diff's stated model of graphify's own defensive read is accurate. |
| md-size budgets | line/byte count vs `md-size-budgets.md` | `graphify-first.md` 29 lines / 1,723 B; `.claude/CLAUDE.md` 109 lines / 5,953 B — both far inside the 200-line / 24,000-B `rule_unscoped` and `eager_root` caps. **No budget issue.** |
| gates | `pytest tests/test_graphify.py -q` → `27 passed`, rc=0; `dotfiles-setup check-doc-refs` → rc=0 | Both green. |

---

## Findings

### HIGH | `.claude/CLAUDE.md:41` still orders a bare `graphify update .` one line below the new "never a bare `graphify` on `PATH`" bullet, and no task exists to redirect it to | `.claude/CLAUDE.md:40-41`, `.claude/rules/graphify-first.md:10-19`, `mise.toml:723,732`

The edited hunk reads:

```
- Codebase questions: follow `.claude/rules/graphify-first.md`
  (`mise run graphify-query`, never a bare `graphify` on `PATH`).
- After changing code: `graphify update .` (AST-only, no API cost).
```

The second bullet **is** a bare `graphify` on `PATH`, i.e. 0.9.53 — and it is the bullet that
*writes* `graphify-out/graph.json`. `mise.toml` defines only `[tasks.graphify-query]` (723) and
`[tasks.graphify-health]` (732); there is no `graphify-update` task, so an agent reading these
two bullets cold has no compliant way to perform the update. The surviving instruction is
therefore **not followable**, and the two eager files do not fully agree — the contradiction was
narrowed, not removed.

Notably this is a *known* line: the diff's own persisted audit
(`docs/research/kb/reports/agents/2026-08-30c-graphify-doc-audit.md:328-330`) quotes it and marks
it "verified CORRECT — do not fix", on the grounds that `graphify --help` documents `update` as
LLM-free. That verdict was reached before the "never a bare `graphify`" rule existed; it does not
survive the rule this PR adds.

### HIGH | Dropping the receipt requirement removes the ONLY binding between the graph on disk and the graphify version that built it — and the prose discloses only the byte-integrity half of that loss | `python/src/dotfiles_setup/graphify.py:159-181, 219, 227-235`, `.claude/rules/graphify-first.md:7`

`_runtime_version()` (graphify.py:81-85) reads `importlib.metadata.version("graphifyy")` — the
**venv package** in the process running the check. It is 0.9.42 by construction and says nothing
about which binary produced `graph.json`. Pre-change, `FRESH` additionally required a receipt
whose `runtime_version` matched (`_receipt_matches`, line 147); post-change, `FRESH` requires only
that the venv pin equals the `"0.9.42"` literal and that the JSON parses.

Combined with the finding above, the concrete consequence on this host: the repo's own documented
update command runs **0.9.53**, and `graphify_health` will report the resulting graph `FRESH`.
`GraphifyStatus.VERSION_DRIFT` cannot catch it — that branch (line 227) compares the venv pin to a
hardcoded literal, never the graph.

The docstring at lines 171-177 is candid about one guarantee ("the graph bytes on disk are the
ones a specific build run produced, unmodified") but never states that the *builder-version*
binding goes with it — while `graphify-first.md:7` still instructs the agent to treat "version
drift" as a state it will be told about. Something is silently depending on the dropped guarantee:
that rule's own promise.

To be fair to the change: this binding never actually *functioned* in dotfiles, because no
producer existed — the gate was permanently red. The trade is a permanently-failing gate for a
permanently-passing one on this axis. That is defensible; it is the non-disclosure that is the
finding. One honest sentence in the docstring and in `graphify-first.md` would close it.

### MEDIUM | The docstring's residual reassurance ("if a receipt IS present it is still verified") describes a path whose only producer is broken by the identical defect this PR fixes | `python/src/dotfiles_setup/graphify.py:161-165, 174-177`; `../knowledge-base/python/src/kb_setup/graph.py:3053-3058, 3068, 3099, 3111`

The docstring names `kb_setup.graph` as the authoritative writer. That writer still keys on
`"edges"`:

```
kb_setup/graph.py:3053   for field in ("nodes", "edges", "hyperedges"):
kb_setup/graph.py:3057       raise SystemExit(f"[kb-build] refusing build receipt: graph field {field!r} is not an array")
kb_setup/graph.py:3068       edge_count=len(collections["edges"]),
```

so it **hard-refuses** (SystemExit) on exactly the `links`-keyed graph graphify writes.
`_current_build_receipt_matches` (3099, 3111) carries the same key. Verified against reality:
`../knowledge-base/graphify-out/graph.json` has top keys
`['built_at_commit','directed','graph','hyperedges','links','multigraph','nodes']` — `links`, no
`edges` — and `ls ../knowledge-base/graphify-out/ | grep -i receipt` returns **nothing** (rc=1).

So the fix is **half-applied across the two repos that share `GraphifyBuildReceipt`** (dotfiles
imports the type from `kb_setup.graph`, graphify.py:23). The scenario the docstring offers as
consolation — "carried over from a KB-style build" — cannot presently occur, and citing the KB
pipeline as the working writer without noting it carries the same unfixed bug overstates the
residual safety. The KB-side fix belongs in a follow-up ticket, but the docstring should not
imply the path works today.

### MEDIUM | An active PreToolUse hook injects the opposite instruction ("You MUST run `graphify query \"<question>\"`") into every Bash / Grep / Read call | `.claude/settings.json:53-70`, `scripts/graphify-hook-guard.sh:25`

The wrapper shells `mise exec -- graphify hook-guard "$kind"`, which resolves the **0.9.53** PATH
binary and emits, verbatim, into this session's tool results:

> `MANDATORY: graphify-out/graph.json exists. You MUST run `graphify query "<question>"` before grepping raw files.`

That is a bare `graphify query` — the exact form the new rule forbids — delivered per-tool-call,
which structurally outranks a once-per-session eager rule in salience. The new rule is
contradicted more often than it is read. The PR does not have to fix the vendored nudge, but a
rule that the harness contradicts on every call should say so and say what wins.

Two further un-updated instruction sites give the same bare form:
`.claude/agents/claude-code-expert.md:284` and `.claude/agents/staleness-auditor.md:122`
("Orient with graphify before grepping … `graphify query \"<question>\"`"). Both are agent
definitions that ride into delegated work, i.e. exactly the contexts least likely to have read
`graphify-first.md`.

Adjacent, and load-bearing for the new rule's own argument:
`scripts/graphify-hook-guard.sh:9-10` claims it "resolves graphify at runtime via mise
(host-pinned in **mise.toml**)". `grep -n "graphifyy" mise.toml` → no such pin; the pin is
user-global (`~/.config/mise/config.toml:288`). The audit report in this same diff
(FINDING 8, lines 208-240) proposed that exact correction; it was not applied.

### LOW | `test_graphify_health_rejects_graph_missing_edge_collection` passes identically with the production change reverted — it does not discriminate | `tests/test_graphify.py:462-489`

Reverting `_edges_field` in `_graph_schema_problem` restores `for field in ("nodes","edges","hyperedges")`.
The fixture payload is `{"nodes": [], "hyperedges": []}`, so the old code returns
`graph field 'edges' must be an array` → `CORRUPT`, detail containing `"edges"`. Both assertions
(`status is CORRUPT`, `"edges" in result.detail`) hold **before and after** the change. It is a
useful guard against a *future* hard-coding of `"links"`, but it is not evidence for this diff.

Two of its fixtures are also unreachable: `_graph_schema_problem` short-circuits at
graphify.py:225, before the version check (227) and the receipt check (229) — so the
`build-receipt.json` it writes and the `_runtime_version` monkeypatch it installs can never be
consulted. They read as an integration the test does not exercise.

The other two changed tests DO discriminate: `..._accepts_graph_without_build_receipt`
(299-318) returns `STALE` on revert vs the asserted `FRESH`; `..._accepts_links_keyed_graph`
(448-476) returns `CORRUPT` on revert vs the asserted `FRESH`.

### LOW | `GraphifyStatus.STALE` now has no reachable producer in this repo, while `graphify-first.md:7` still instructs the agent to handle it | `python/src/dotfiles_setup/graphify.py:192`, `.claude/rules/graphify-first.md:7`

After the change, `STALE` is returned only from `_receipt_problem`'s mismatch branch, which
requires `build-receipt.json` on disk — a file the diff itself establishes nothing here writes.
Pre-existing siblings in the same enum: `GraphifyStatus.INCOMPLETE` has **zero** assignments
anywhere (`grep -rn "GraphifyStatus.INCOMPLETE" python/src tests/` → 0 hits; control arm:
`GraphifyStatus` → 2 files, so the grep sees the module), and `QueryResult.truncated`
(graphify.py:63) is never set to `True`. Not introduced by this diff, but the rule's status
vocabulary now over-promises in three places.

### LOW | The missing-collection diagnostic names the wrong key for a graphify graph | `python/src/dotfiles_setup/graphify.py:121, 198-200`

`_edges_field` falls back to `"edges"` when neither key is present, so a genuinely broken
graphify graph reports `graph field 'edges' must be an array` — pointing the reader at a key
graphify never writes. `graph field 'links' (or 'edges') must be an array` would be actionable.

### INFO | The `_edges_field` docstring says the exporter "always calls `node_link_data(G, edges=\"links\")`"; it is a `try/except TypeError` | `python/src/dotfiles_setup/graphify.py:113-115` vs `graphify/export.py:301-304`

The conclusion survives — the `except` branch exists only for networkx versions that reject the
`edges=` kwarg, whose `node_link_data` default key was `links` anyway, and `export.py:315`/`329`
index `data["links"]` unconditionally, so graphify itself would crash on any other key. Only the
word "always" is imprecise.

### INFO | The `_ALLOWED_ABSENT` addition is as narrow as the mechanism allows and the gate is green, but "Same rationale" is not accurate | `python/src/dotfiles_setup/doc_refs.py:148-151`

Matching is exact-string (`doc_refs.py:235`, `if ref in _ALLOWED_ABSENT`), so an exact path is the
narrowest possible entry — it cannot shadow any other ref. `check-doc-refs` exits 0. The entry is
genuinely *necessitated* by prose the same commit adds (`graphify-first.md:20`), which is the
honest shape for an allowlist addition.

The scepticism worth recording: the neighbouring `graphify-out/graph.json` entry (147) is
justified as "gitignored and rebuilt per-clone, so it exists locally and never in CI" — a
**local/CI divergence**. The new entry's real justification is strictly weaker: the file exists
*nowhere*, so it is an ordinary unresolved ref, not a divergence. The comment's opening
"Same rationale" mis-describes that; the second clause ("and never written in this repo at all")
discloses it, so nothing is hidden — but a future reader scanning the comment heads will file it
under the wrong precedent.

### INFO | `test_graphify_health_accepts_links_keyed_graph` omits the `_runtime_version` monkeypatch its neighbours use | `tests/test_graphify.py:448-476`

It asserts `FRESH`, which requires `_runtime_version() == "0.9.42"` from the real venv. It passes
today (venv = 0.9.42) and matches a pre-existing pattern
(`test_graphify_health_rejects_forged_producer_receipt_fields`, 351-374, is also unpatched), so
this is consistency-noise rather than a defect. A future `graphifyy` bump turns it into a
`VERSION_DRIFT` failure whose message points nowhere near the links/edges behaviour it guards.

---

## Honest summary

The production change is right, is backed by the real artifact rather than by assumption, and its
two load-bearing factual claims both check out. What does not hold up cold is the surrounding
prose: one eager file still commands the thing the other now forbids and offers no compliant
alternative; the disclosed loss is half the actual loss; and the consolation clause points at a
sibling-repo writer that carries the same unfixed bug. None of that blocks the code; all of it
should be written down before merge, because each item is the kind that a later session will read
as settled.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the branch under review.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `kb_setup/graph.py`, the sole `build-receipt.json` writer, and its local `graphify-out/`.
- [ray-manaloto/graphifyy (pypi `graphifyy`)](https://github.com/ray-manaloto/dotfiles) — read the installed 0.9.42 `graphify/export.py` from `python/.venv`; upstream repo URL not established, so this row is UNVERIFIED as a repo link.
