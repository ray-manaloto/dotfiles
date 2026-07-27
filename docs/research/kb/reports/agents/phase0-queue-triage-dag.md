<!-- Verbatim output of workflow wf_1055118a-aa2 (Phase 0 triage), 2026-07-27.
     34 agents, 29 findings, 4 survived adversarial review, 25 refuted.
     Persisted unedited per .claude/rules/agent-report-persistence.md. -->

# Build order (DAG) — graphify autonomous queue

**Method note.** Read-only pass. The repo PreToolUse hook demanded `graphify query` before grepping; the task's read-only rule forbids graphify subcommands, so every claim below is a direct file read or a control-armed probe. Where I re-derived a number myself I say so; where a figure is inherited from the review pass I label it.

---

## 0. Two blocking human decisions, before any code

| # | decision | why it blocks | evidence |
|---|---|---|---|
| **H1** | **The KB graphify pin: match 0.9.27 or hold at 0.9.26 with a recorded reason.** | Blocks all of Phase R, and blocks the only viable form of KB#34. `parity.toml:18-22` mandates making the other repo true *before* widening an axis; the repos disagree today, so a `pins` axis added now lands a red main. | `knowledge-base/mise.toml:23` = `0.9.26`; `dotfiles/mise.toml:53` = `0.9.27`; `knowledge-base/graphify-out/.currency-stamp.json` → `"version": "0.9.26"`, `built_at 2026-07-26T04:25:53+00:00`, `artifact_commit 12c0fd3` (all four re-read this session). |
| **H2** | **KB#21's mechanism.** The design written into the issue, the runbook, and two shipped artifacts is **impossible**. | Blocks #21 itself, and is the reason Phase 1 of the runbook cannot execute as written. | `graphify add <local-file>` cannot work: `ingest.py:228` calls `validate_url`, and `security.py:112-116` raises `ValueError` for any scheme outside `{http, https}` — a bare path parses to scheme `''`. Verified in the 0.9.26 tree KB pins. Yet `mise.toml:188` instructs "Hand the resulting file to `graphify add <file>`, whose slicing is lossless" and `fetch.py:440` prints the same broken advice. |

Two lesser sign-offs, non-blocking for everything else: **H3** KB#19's upstream wording review (recorded as a deliberate hold in `.agent/plans/session-2026-07-24-j.md:35-37`), and **H4** the build-token sign-off df#318 requires before a priced build.

---

## 1. The DAG

### Phase 0 — decisions + isolated one-liners (all parallel; disjoint files)

| item | file(s) | note |
|---|---|---|
| **P0-a** `.gitignore:64` `graphify-out/` → `graphify-out/*` | `dotfiles/.gitignore` | Live defect, not a dormant guard. Git cannot re-include a path under an excluded parent, so the `!graphify-out/wiki/` on `:65` is inert **today and after the wiki exists**. This is half of df#318's AC2. |
| **P0-b** fix spec §5a's PATH mitigation | `dotfiles/docs/specs/graphify-autonomous-queue.md:187-192` | The snippet strips `pipx-graphifyy/0.9.26/bin`. **Re-probed in this session's shell: the only entry is `0.9.25/bin`, at PATH position 32** (control arm: 2 `mise/shims` entries present, so the probe reads PATH). The premise "the hazard moved with the version" is wrong — the entry is frozen by `MISE_ENV_CACHE=1` at whatever was active when the session's env cache was populated (observed at 0.9.23 and 0.9.25 in `.agent/notepad.md:1708-1710`, `:2440-2442`). Fix version-agnostically: `grep -v 'pipx-graphifyy/[^/]*/bin'`. |
| **P0-c** df#316a — name the canonical task in the adoption note | `dotfiles/.claude/CLAUDE.md:37-40` | The note tells readers to run `graphify query` / `graphify update .` directly; `mise run graphify-query` (`dotfiles/mise.toml:535-542`) is named in **no** authored doc. Control-armed: `grep -n "mise" .claude/skills/graphify/SKILL.md` → 0 hits against 156 `graphify` hits in the same file. |
| **P0-d** df#312 reconcile | `dotfiles/mise.toml:44-46`, `.claude/rules/do-not.md:54` | Shipped state contradicts its own inline documentation: graphify's PreToolUse hook registration is live at `.claude/settings.json:21-38` (same shape as graphify's generator, `install.py:311-315`) while both files still forbid `graphify hook install`. `do-not.md` was last edited 2026-07-25, *after* PR #344 landed the hooks, so the prohibition is current, not superseded. |

### Phase 1 — KB ingestion. **SERIAL on `python/src/kb_setup/fetch.py`.** Not parallel.

Four issues edit the same two files. Worktree isolation does **not** help — they must land in an order, because each rewrites the other's hunks.

`python/src/kb_setup/fetch.py` + `tests/test_fetch.py`: **#21, #10, #22, #16**
`python/src/kb_setup/cli.py`: #21, #16 · `knowledge-base/mise.toml`: #21, #16 (+ #14-PR2, #20)

**If H2 is answered:** `#21 → #10 → #22 → #16`
**If H2 stalls:** `#10 → #22 → #16`, with #21 last. None of the other three depends on #21.

| step | scope | evidence |
|---|---|---|
| **#21** | Route `kb-add` through the lossless path. `mise.toml:179` is literally `run = "graphify add"` — zero kb_setup code in the path — and `hook_guard.py:64` maps `"add": "mise run kb-add -- <url>"`, so the guard funnels every ingest into the truncating branch. The chain must end in an extract/build step, not `graphify add <file>`. Also fix `fetch.py:440` and `mise.toml:188`, which both print the impossible advice. | verified above |
| **#10 residual** | Re-gate the **extracted** body. `gate()` has exactly one call site — `fetch.py:200`, on the RAW response — while `extract_markdown` (`fetch.py:419`) feeds `write_source` (`fetch.py:423`) with no volume re-check. A nav-only extraction is still written silently, which is #10's failure mode surviving in miniature. `extract_markdown` and `fetch_main` have **zero** tests in `tests/test_fetch.py`. | |
| **#22** | Expand `_UPSTREAM_RULES` (`fetch.py:272-276`). **Do the coverage first:** `_scrapy` and `_astro` have no tests, and the mapped-host/unmatched-path `None` branch (`fetch.py:371`) — the exact axis an expansion extends — is untested. Not a "data table": values are callables under the `_UpstreamRule` Protocol (`fetch.py:234-235`) and `_jest` hardcodes a 3-slug allowlist (`fetch.py:244-247`). Unbounded scope, no defined done-state. | |
| **#16** | Idempotency. Reduces to "warn/refuse instead of silently overwriting" *after* #21, because `write_source` (`fetch.py:223-231`) overwrites a deterministic `name_from_url` stem with timestamp-free bytes. Before #21, `ingest.py:262-265`'s counter loop writes a second file — a live instance exists on disk: `raw/claude_com_blog_building-verification-loops-…_1.md` beside its un-suffixed twin. | |

### Phase 2 — KB non-ingestion. **Genuinely parallel** (disjoint files).

| lane | issue | files | conflicts |
|---|---|---|---|
| **A** | **KB#13** — docs half only. Mandate `scriptPath` in `.claude/skills/kb-curator/SKILL.md` (`:45`, `:117-118` currently instruct by-name). The code fix is shipped **and proven-executed** (run metadata `wf_7844a520-27f.json`: `.args\|type == "string"`, status `completed`). | `.claude/skills/kb-curator/SKILL.md` | none |
| **B** | **KB#14 PR1** — delegation cap + re-characterise the Opus-5 fallback. | `.claude/skills/orchestrator-routing/SKILL.md`, `brain/lane-claude-fallback.md`, `brain/fallback-ladder.md`, possibly `.claude/settings.json` | shares SKILL.md with PR2 → PR1 before PR2 |
| **C** | **KB#23a** — promote the two research reports out of `.agent/kb/reports/` (untracked, `.gitignore:87`) into `dotfiles/docs/research/kb/reports/`; fix the issue's retired `.omc/` citations. | dotfiles `docs/research/kb/reports/` | none |
| **D** | **KB#14 PR2** — `--mode` on `brain-remember`. | `brain.py`, `tests/test_brain.py`, `mise.toml:251-254`, SKILL.md:107-110 | `mise.toml` with Phase 1 → worktree-isolate, land after #16 |

**Not schedulable in Phase 2** (moved out, see §5):
- **KB#20** — needs re-scoping, not code. Its premise is false against the pinned graphify: `property_signature` occurs **0** times in `extract.py` (control arm: `method_signature` → 1, at `extract.py:734`), and JSDoc blocks match none of `_JS_RATIONALE_PREFIXES` (`extract.py:1176-1181`). And it is not independent of the fetch lane — `_astro()` already exists at `fetch.py:258-265`, reached from `fetch_main` at `fetch.py:398`.
- **KB#34** — blocked on H1. Only a `pins` axis on `dotfiles/parity.toml` can assert the invariant; the issue's own Option 1 is a measured no-op (`mise run -C <KB> kb-currency-check` re-roots into KB and reports "in sync" while dotfiles runs 0.9.27).
- **KB#19** — blocked on H3; landing it is a `[[tool.graphify.watch]] kind = "local"` entry in `knowledge-base/currency.toml:63-77`, not an upstream post.

### Phase 3 — dotfiles graphify epic (T1–T7)

Serial chain on `python/src/dotfiles_setup/graphify.py` + `main.py` + `tests/test_graphify.py` + `dotfiles/mise.toml`:

```
df#313-fix ──▶ df#314 (T3) ──▶ df#315 (T4, safety half) ──▶ df#317 (T5) ──▶ df#310 close
                    │                                          ▲
df#316a (P0-c) ─────┴──▶ df#316b ──────────────────────────────┘
df#315 (fixture-graph half) ── parallel with df#314
df#318a (P0-a) ── parallel · df#318b ── after H4
```

| item | state | evidence |
|---|---|---|
| **df#313-fix** | T2 is **wired-but-defective**, not shipped. `--context` is typed `int` "context depth" (`graphify.py:79`, `main.py:311-313`) but graphify treats it as a repeatable **edge-relation label string** (`cli.py:795-800`, `serve.py:637-681`, `723-737`). So `--context call` is rejected by argparse rc=2 and `--context 2` matches zero edges and returns a degraded seed-only answer at rc=0. Already wrong at the merge-time pin. Also: `build_query_args`' `--context`/`--dfs` branches have zero assertions (their only occurrence in `tests/test_graphify.py` is line 9, a docstring; control arm `--budget` → 3 hits). | |
| **df#314 (T3)** | **NOT-STARTED**, confirmed. `graphify.py` is 122 lines: `GraphifyError`, `QueryResult`, `_run`, `build_query_args`, `query`, `graphify_main`. No guard, no refresh, no `graphify-refresh` task. The similarly-named `run_guarded` at `lint.py:99` is hk's timeout wrapper, unrelated. | |
| **df#315 (T4)** | **PARTIAL**, not not-started. A real-binary, control-armed, gated `graphify query` smoke already ships as `tier1.graph-answers` (`eval_cases.py:286-296` → `kb_setup/evals.py:302-307`), control-armed by `_broken_graph_canary` (`eval_cases.py:198-211`), gated by `_graphify_installed` (`eval_cases.py:229-248`), wired to every ship at `pr.py:300`. Outstanding: committed fixture graph, source-citation assertion, pytest marker (`pytest.ini` declares only `image_exec`), and the T3-blocked safety test. `tests/fixtures/graphify-gold/` is the bake-off **input** corpus (`graph_bakeoff.py:77` → `main.py:879`), not a built graph. | |
| **df#317 (T5)** | **NOT-STARTED and correctly still blocked** by #315/#316 (its own body; its ACs require binding the skill/rule note T6 delivers). The gap is real and was measured empirically: on a scratchpad `git archive` copy, deleting `mise.toml:542`, `main.py:1237`, `graphify.py` and `tests/test_graphify.py` left `verify run` at **108 suites / 0 failed**; the control arm (deleting `mise.toml:472`) produced **1 failure**. | |
| **df#318b** | Central deliverable is **not started**: the existing graph is the free AST build. `GRAPH_REPORT.md:10` reads "Token cost: 0 input · 0 output"; all 3,597 nodes carry `_origin='ast'`, a tag graphify sets only on AST output (`extract.py:5433-5435`). No priced build has run, so the sign-off gate (AC4) was never exercised. `graphify-out/wiki/` does not exist. | |

### Phase R — retrieval. SERIAL, gated on H1. **And its content is now in doubt.**

```
H1 ──▶ kb-build (log `graphify --version` first) ──▶ uv run kb-setup eval --slow (re-baseline all 4 arms)
                                                              │
                                                              ▼
                                              DECISION: is P4/P6 worth building at all?
```

See §3 — I found no path by which either free lever can move the number on this corpus.

---

## 2. Close without building

| issue | action | evidence |
|---|---|---|
| **df#312 (T1)** | **Close with a recorded deviation** after P0-d lands. Provisioning is real and Renovate-carried: `mise.toml:53`, `mise.lock:5662-5667`, `_config_pin` (`tests/test_lock_coverage.py:60-68`) gates version drift, `devcontainer.json:150` excludes the root config, `mise ls` shows 0.9.27 active. No `~/.claude` contamination (`~/.claude/skills/` holds only `.DS_Store`; `~/.claude/CLAUDE.md` does not exist). **Do not close before P0-d** — two deviations from AC4 exist, one undocumented, and `_strip_extras` (`tests/test_lock_coverage.py:40`) matches **zero** of `mise.toml`'s 32 tool keys, so `extras = ["all"]` is ungated. |
| **df#313 (T2)** | **Do not close.** 3 of 6 ACs met. See df#313-fix above. |
| **KB#13 defect 2** | **Tick the box.** The `JSON.parse(cfg)` fix is committed (`4c944a3`) *and* proven-executed (`wf_7844a520-27f.json` → `completed`, 4 agents, string args). Its second box (does this affect other saved workflows?) stays open and is understated — the transcript shows the **caller** stringified args in all four `tool_use` blocks, so the shipped comment at `kb-extract.js:31-37` blaming "some invocation paths" is wrong. |
| **KB#10** | **Do NOT close as subsumed.** #21 does not meet its acceptance criterion ("no silent shells"), because `fetch_main` never re-gates the extracted body. Amend root cause (1): for the claude.com sources the article **is** in the server HTML (582 KB → 9,688 chars of real body); the loss is boilerplate-free markdownify + the 12k cut, not missing JS. Deprioritise the render-backend bullet — `sources/REGISTRY.md:81` records that a browser got nav-only too. |
| **KB#19** | **Do NOT close, do NOT relabel upstream-only.** `ingest.py` is byte-identical (md5 `051736d7…`) across 0.9.25 / 0.9.26 / 0.9.27, so the a83532b bump fixed neither half. It has an in-repo home: `currency.toml:63-77`'s `kind = "local"` precedent. |
| **KB#23** | **Split.** Close the archival half (promote + fix citations). **Do not close as moot** — the "graphify's file path already slices losslessly at heading boundaries" premise is only half true. `file_slice.py:89-90` guarantees contiguity; heading is one of three preferences (`_BOUNDARY_SEPARATORS`, `file_slice.py:34`) with a hard fallback (`return end`, `file_slice.py:83`) and **zero** fence awareness (0 hits for `fence`/```` ``` ````; control arm `heading` → 3). A probe of the shipped 0.9.27 module at the real `_FILE_CHAR_CAP = 20_000` split a fenced ```bash block across two slices, cutting at a `# step 630` shell comment. 375 of 5,466 `.md` files under `sources/` exceed the cap. **That is a new, concrete, schedulable defect** — file it and defer the survey angles. |
| **df#310** | Closes last. Its two "drift" concerns do not hold: "never wired to an automatic hook" scopes to the **priced build** (US #9, Out of Scope), and the bounded-first-build decision is un-overtaken because no priced build has ever run. |

---

## 3. The retrieval gate

**Must a rebuild precede P4/P6? Yes for P4 — but for the shared reason, not the stated one. And it may not matter, because neither lever can work.**

**(a) The stated mechanism is wrong.** §5a argues the AST extractor changed, so a rebuild moves the graph P4 ranks over. Measured directly on `graphify-out/graph-prose.json`: the prose edge set contains **zero** AST-produced edges. `prose.py:145-149` (both endpoints must survive) plus the `_origin == "ast"` filter is the *firewall*, not the leak. The real coupling is `community`, recomputed over the full 128k-node graph at `_merge_docs.py:36-37` and stamped on every prose node — a **node** attribute the *existing* arms already use. P6 is unaffected outright: `captured_at` is a required chunk-schema field (`chunks.py:22`) and AST nodes never carry it.

**(b) The real precondition is the binary, and it is shared by all four arms.** `unscoped` and `prose` shell out to bare `graphify query` (`eval_cases.py:389`). Under the canonical `mise run eval` (`mise.toml:105`) that resolves to 0.9.26 today; under the bare `uv run kb-setup eval --slow` form §5a itself prescribes at line 179, it resolves to whatever is in front on PATH. So: **decide H1, rebuild, re-baseline all four arms together, then quote any new number.** That is the established remedy — `a83532b` did exactly this, and KB#12's P1 comment records "Measured on graphify 0.9.26 after re-baselining".

**(c) Risk to `RETRIEVAL_FLOOR` is lower than feared, and cannot redden a PR.**

- The case is `slow=True` and `kb-ship` does not pass `--slow` (`eval_cases.py:759-775`) — **no CI or ship run can go red**. Only a deliberate local `--slow`.
- The floor is `max` over **all four** arms (`evals.py:895`, re-read this session), and the runner-up `prose+rrf` sits **exactly on** the floor at 4 (inherited from the KB#12 P2 comment and `eval_cases.py:352-353`). Breach therefore needs `prose+idf` −2 **and** `prose+rrf` −1 simultaneously: ≥3 pairs across two non-nested arms, not 2 pairs in one.
- The only measured rebuild-vs-recall datapoint (0.9.25→0.9.26, KB#32) moved recall by **0** pairs.
- Masking is real but not silent: the floor line prints the best arm's name and score (`evals.py:897-900`), and the per-arm table + deltas are emitted unconditionally on both pass and breach paths (`evals.py:986-1004`). §5a line 180 already says "re-baseline all four arms and record the table".

**(d) P4 cannot work on this corpus. I re-derived this myself.**

Measured on `graphify-out/graph-prose.json` (2,105 nodes / 2,644 links): **2,608 links (98.6%) are intra-document; 36 (1.4%) cross a document boundary**, touching 9 documents. The eval scores **document-level** recall (`eval_cases.py:500` returns `hit.source_file`), so an intra-document hop lands on a document already counted. **All 8 golden targets have zero cross-document edges in either direction** — control arm on the same probe: `yt-9CiOwbmOKdU-memory.md` 11, `README.md` 6, `ARCHITECTURE.md` 5, so the probe discriminates and the zeros are real. A 1-hop expansion is structurally incapable of introducing a target document. The review pass additionally simulated literal P4 through the real index and got **5/8 → 2/8** (below the floor), with three charitable variants all flat at 5/8; I did not re-run that simulation, so treat the −3 as inherited, but the zero-ceiling result above is mine and is sufficient on its own.

**(e) P6's signal is a batch id, not an age.** `captured_at` is stamped at **ingest** (`fetch.py:51`), not publication; `sources/REGISTRY.md:143` shows a whole batch sharing one value. Four distinct non-null values spanning three days plus 43 JSON nulls (**not** the literal string `"None"` — that occurs 0 times in either graph file). The existing freshness policy threshold is **> 1 month** (`sources/REGISTRY.md:204-206`) and the oldest node is six days old, so a flat curve today is expected by construction.

**Recommendation:** run the re-baseline (it is cheap and settles provenance), then treat P4 and P6 as **not-yet-buildable** and go straight to the costed P3/P5 proposal that decision 5 already contemplates. The 3 remaining misses sit at document ranks 15/32/36 of ~75 — a **ranking** deficit, which is exactly what `eval_cases.py:352-357` says fusion cannot fix without a genuine second scorer.

---

## 4. What changed versus the runbook's assumed order

**§5 Phase 1–2 did not hold up. §5 Phase 3–4 held up only partially. §5a is right to exist but is wrong in its details, and its own remediation is inert.**

| runbook claim (`docs/specs/graphify-autonomous-queue.md`) | verdict | correction |
|---|---|---|
| §5:141 "#10, #16 and #21 all modify `kb-add`… ~2 lanes with a hard prerequisite" | **Half held.** | The *serialization* is right and is stronger than stated — four issues (#21, #10, #22, #16) share `fetch.py` + `tests/test_fetch.py`. The *prerequisite* is not: #16 and #10 are independently actionable today (a mise `run` can be multi-line — KB's own `mise.toml:358` is — and `cli.py:17` already dispatches ~20 subcommands). |
| §5:144 "#21 wires the already-lossless kb-fetch path into kb-add" | **Refuted.** | The mechanism is impossible (`ingest.py:228` → `security.py:112-116`). #21 is **NEEDS-DESIGN**, not READY. Phase 1 cannot start until H2 is answered. |
| §5:144 "kb-fetch's file path is already lossless" | **Conflation.** | graphify's file slicing is lossless-by-contiguity (`file_slice.py:89-90`) but is reached only from `llm.py:2215` (`graphify extract` / `kb-build`); `ingest.py` never imports `file_slice`. It also splits code fences. |
| §5:145 "#21 may close #10 and #19 by construction" | **Refuted, both.** | #10's criterion still fails after #21 (`gate()` has one call site, `fetch.py:200`, on the raw response). #19 is upstream and unchanged across 0.9.25/26/27 (byte-identical `ingest.py`). |
| §5 Phase 2 "re-test before building… close #10/#19 as fixed-by-construction" | **Keep the re-probe, drop the expectation.** | Neither can close. #10's residual is a concrete code change; #19's is a `currency.toml` entry gated on H3. |
| §5 Phase 3 "parallel lanes: #16 #22 #20 #13 #14 #23 #34" | **Only #13, #14, #23a are parallel.** | #16 and #22 belong to the serial fetch lane. #20 and #34 are not code-ready. #19 is blocked on a human. |
| §5 Phase 4 "GATED on a re-baseline… P4 then P6" | **Gate right, content doubtful.** | See §3(d)/(e). |
| §5a:161 "graphify is 0.9.27 on PATH" | **True as written, misleading in practice.** | True from a dotfiles cwd via the shims. But `mise which` is cwd-dependent (KB cwd → 0.9.26), and a long-lived agent session carries a frozen `MISE_ENV_CACHE` entry — **this session's PATH holds `0.9.25/bin` at position 32 right now**. |
| §5a:187-192 the PATH-strip snippet | **Inert.** | Strips `0.9.26/bin`, which is absent; `0.9.25/bin` is present. Applied verbatim it removes nothing. Fix version-agnostically (P0-b). Impact is real because `kb-build` resolves bare `graphify` through PATH (`graph.py:86,137,251`; `graphify_env.py:65` passes PATH through unchanged; `sync.py:222` stamps via `shutil.which`). |

**Corrected top-level order:**

```
H1, H2 (human)  ──┬──▶ Phase 0 (P0-a…d, parallel)
                  │
                  ├──▶ Phase 1 fetch lane, SERIAL: [#21] → #10 → #22 → #16
                  │
                  ├──▶ Phase 2 parallel: A #13 · B #14-PR1 · C #23a   (then D #14-PR2)
                  │
                  ├──▶ Phase 3 dotfiles: #313-fix → #314 → #315 → #317 → #310
                  │
                  └──▶ Phase R (needs H1): rebuild → re-baseline 4 arms → RE-DECIDE P4/P6
```

---

## 5. Open questions for the human

1. **H1 — KB pin.** Match dotfiles at 0.9.27, or hold at 0.9.26 and record why? Undecidable from code: `sources/graphify.manifest` asserts pin-agreement but only the in-repo half is machine-enforced (`currency/sync.py:552-566`), and nothing asserts the cross-repo half.
2. **H2 — #21's mechanism.** `graphify add <file>` is impossible. Does a single new URL source enter `graph.json` via a full `kb-build`, or via an incremental route that does not exist yet? Also: `kb-fetch` writes to `sources/` (`fetch.py:423`) while `graphify add` writes to `raw/` (`cli.py:1422`) — which wins?
3. **P4/P6 — build, re-scope, or skip?** Decision 5 locked "free levers only (P4, P6)". The corpus says P4 has a zero gain ceiling on the golden set and P6's field is a batch id. Do you want them built anyway as citable negatives (the `prose+rrf` precedent), or do you want the budget spent on the costed P3/P5 proposal instead? **This is the largest deviation from a locked decision and I will not resolve it unilaterally.**
4. **H3 — KB#19 upstream wording.** Held pending your review since 2026-07-24.
5. **H4 — df#318 build-token sign-off.** No priced build has ever run; the gate has never been exercised.
6. **KB#20 scope.** Its premise (graphify AST-extracts every TS interface option with type/default/JSDoc) is false. Re-scope to "prefer authored source over rendered prose" — which `_astro()` already implements — or close?
7. **#22's done-state.** The issue names hosting *platforms* (Read the Docs, Mintlify, GitBook, Docusaurus, MDN) while the table is keyed on exact host (`fetch.py:368`) and `_jest` is even per-page. How many entries is "done"?

**Where the evidence is thin, stated plainly:**
- The per-arm scores (unscoped 1 / prose 3 / prose+idf 5 / prose+rrf 4) are **inherited** from the KB#12 P2 comment and `eval_cases.py:352-353`. I did not run `--slow` (read-only; it invokes graphify). Everything in §3(c) depends only on `prose+rrf ≥ floor` and `prose+rrf < prose+idf`, both of which the code's own docstring asserts.
- The P4 simulation result (5/8 → 2/8) is inherited. The zero-ceiling finding is mine and independently sufficient.
- df#315's "PARTIAL" rests on reading `eval_cases.py` / `evals.py`; I did not execute the eval to confirm `tier1.graph-answers` currently passes.
- KB#13's issue box 1 ("where does `name:` resolve from") is genuinely **unresolved** — the per-invocation snapshot files are outputs, not the cache. Mandating `scriptPath` is a workaround that redefines the acceptance criterion rather than meeting it; record it as such.
## GitHub repos touched



- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the 11 queued issues and `python/src/kb_setup/**`.

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the #310 epic (#312-#318), `parity.toml`, `.claude/settings.json`, the queue runbook.

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the installed 0.9.25/0.9.26/0.9.27 trees (`ingest.py`, `security.py`, `file_slice.py`, `extract.py`, `llm.py`).
