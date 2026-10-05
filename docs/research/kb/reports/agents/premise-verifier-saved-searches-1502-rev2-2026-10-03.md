# premise-verifier — research-saved-searches-1502 spec rev 2 delta (2026-10-03)

Verbatim final report, persisted at receipt.

PREMISE REPORT: rev 2 delta (§4.2, §4.3, §4.5, §4.7, §4.9, §4.10, rows 26-31). Read-only, so nothing was persisted. The coordinator should save this verbatim.

ROWS: 6 checked. 6 CONFIRMED (0 provenance corrected), 0 REFUTED, 0 UNVERIFIABLE, 0 ASSUMED.
- 26: CONFIRMED. `tests/test_workflows_js.py`: `_wrapped_source` is at :335-346, bun via `mise exec -- bun` at :349-358, `_SWEEP_ROUTING` at :632-654, exact `routing == _SWEEP_ROUTING` at :679, `KNOWN_LABEL_PREFIXES` at :67-96, and `DEPS_QUERIES` splits on `mise run research-fanout -- "` at :188.
- 27: CONFIRMED. `hk.pkl:393-394` runs `dotfiles-setup token-audit`. `token_audit.py:351-355` counts with `text.count(token)` (expected 1), and `find_ambiguous` is at :358-367.
- 28: CONFIRMED. `research_fanout.py:969-973` is `elif shutil.which("gh") is None: reason = "needs gh"`, called from `fan_out` paths :1089, :1269 and :1288. `tests/test_research_fanout.py:330-337` is `_install_path_tools`.
- 29: CONFIRMED. `plan` is at :436 and `dependencyRuns` at :448. The first `finish()` call is at :584 and `underDocs` is at :155. Fresh rows carry `{manifest: m.path, fresh: m.fresh === true}` (:484), and stale or missing rows carry `fresh: false` (:472). Note: `depManifests` (:579) already holds exactly the fresh-and-ran set.
- 30: CONFIRMED. `python/pyproject.toml:75-77` has `select = ["ALL"]` and there is no `preview` key.
- 31: CONFIRMED. `pyproject.toml:229-266` has one job only (`drift-verdict`, :262-266), `extra-fields = "forbid"` at :245 and `use-generic-base-class = true` at :246. `generated/` holds only `drift_verdict.py`, which is an IntEnum.

Specific checks:
(a) Partly confirmed. On string enums, `use-specialized-enum = true` (`pyproject.toml:256`) gives StrEnum: KB report E43 quotes the 0.83.0 `preset.py:361-364` "Generate StrEnum/IntEnum for string/integer enums", and §3 says the feature is in use. On `$defs` plus nested Structs: the only working precedent is knowledge-base at **0.76.0**, not 0.83.0 (`knowledge-base/pyproject.toml:90`), with a near-identical config (:340-379). There, `generated/research_record.py` gets `class Tier(StrEnum)` and `class Hit(Struct)`, with a nested `list[Arm]` at :58. Dotfiles has never generated a Struct under 0.83.0 plus its custom template (`schemas/templates/msgspec.jinja2`). This holds by version-mismatched precedent only, and `codegen-check` will settle it. Two side facts from that precedent:
  - Optional fields come out as `X | UnsetType = UNSET`, not `None` (session_select.py:7,88). msgspec leaves UNSET out of encoded output, so the "drop None" step is harmless but mostly a no-op. Python code that builds models must use UNSET.
  - StrEnum member names come out lower-case (`cheap = "cheap"`).
(b) Confirmed.
  - `codec.decode` is `msgspec.json.decode(data, type=target, dec_hook=…)` (`codec.py:368-390`) and `codec.encode` is :345-365.
  - msgspec 0.21.1 (uv.lock:1414-1415) handles StrEnum and nested Structs natively, so no hook is needed. Repo precedent: StrEnum fields in `codec.Struct`s that go through `codec.decode` (`sdlc_team.py:56-63,83-87`, decoded at :912 and :1101).
  - codec has NO dict-to-model conversion. Its `__all__` (:72-84) is encode, decode, schema, register, unregister, the hooks and Struct, and `msgspec.convert`/`to_builtins` are TID251-banned (`pyproject.toml:135-136`). So the spec's `tomllib → json.dumps → codec.decode` round-trip is the only sanctioned path.
(c) Confirmed. `shWord` (`test_workflows_js.py:160-173`) strips a `'…'` span including spaces inside it, and handles `\'` via the backslash branch, so `'a'\''b'` becomes `a'b`. `argsOf` (:174) is `split(\` ${flag} \`).slice(1).map(shWord)`.
  - `--out`: the save prompt has exactly one ` --out `, so the stub echo works.
  - DEPS_QUERIES trap: if the split string becomes `mise run research-fanout -- ` with no quote, it also matches the `probeCmd` line (:179, :411) and adds a bogus query `--probe-out`. Split on `mise run research-fanout -- '` (keeping the quote) and run shWord on `"'" + part`. The `<…` placeholder test still works after unquoting.
(d) Confirmed absent today, so each will be unique once added.
  - `mise.toml`: no `saved_searches`, `saved-search` or `research-saved-search` matches. Control: `python -m dotfiles_setup.research_fanout'` matches at :888.
  - Workflow: no `SAVED_PATH`, `phase('Save')` or `saved-search-record` matches. Control: `phase('Retrospect')` matches at :319.
  - `phase('Save')` cannot match `phase('Saved…')` because the token ends in `')`.
  - Uniqueness caveat: if `kind === 'saved-search-record'` also appears in a log string, the count becomes 2.
(e) One pin exists. `test_workflows_js.py:688` has `assert phases[-1] == "Retrospect"`. It still holds because Save runs before `phase('Retrospect')` (:319). There is no phase-count or `meta.phases` pin in `tests/` (only other hit: :2563, a comment) and none in `suites.toml` (zero matches for Retrospect/phases/research-sweep-run; control: `.github/workflows/` matches at :92 and :627). The other pins the save run must satisfy:
  - routing exact equality (:679);
  - `[p.node for p in routing] == [c.label for c in calls]` (:682). This is satisfied because `run()` pushes to the same `routing` array that `finish()` receives (`research-sweep-run.js:218-223`, :584/:586).

MISSING:
- §4.2 count semantics contradict §4.4 and the real draft file. §4.2 says a `total_count`-only baseline ("draft issue files") shows `prev n/a`. §4.4 says take the baseline `count` from `count` OR `total_count`. In `orchestration-2026-10-02.toml`, the CODE results also carry only `total_count` (e.g. :389-394 `orch-code-claude-bg total_count = 6864`), and for code `count` IS `total_count`. So the issues-only label is wrong, and one rule has to be picked. Test 8 (the diff baseline fallback) depends on that choice.
- Schema range on `count`: §4.9 puts §3.1 ranges into the schema, but a failed code search records `count = -1` (§4.2, `research_fanout.py:1689-1714`). Any `minimum: 0` on `Result.count` or the snapshot `count` would reject legitimate rows.
- §4.5 ORIGIN uses `basename(reportPath)`, but the workflow has no `basename` helper. The local idiom is `A.reportPath.split('/').pop()` (:117, :156). This is a trivial wording fix.
- §4.2 cites `_GITHUB_QUERY` at `:70-74`, but it is defined at `research_fanout.py:73`, which row 12's `:73-77` already has right. Citation drift only.
- TOML decode path: `json.dumps(tomllib.loads(...))` raises on an unquoted TOML date or datetime. Every `date_run` in the current draft is a quoted string (no `= <bare date>` matches; quoted forms match at :382 and :517), but a hand-curated file with a bare date would crash the loader instead of returning rc 2.

VERDICT: ready to dispatch, with named non-blocking residuals:
- Fix the `total_count` rule (§4.2 vs §4.4) first: it is a one-line spec choice, and test 8 depends on it.
- (a) depends on 0.76.0 precedent; `mise run codegen-check` in the lane gates settles it.
- The `count` minimum and the DEPS_QUERIES split are implementer traps; each needs one sentence in the spec.
- The date-type crash is an edge case for curated files only.
- The citation drift does not affect correctness.

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/docs/specs/research-saved-searches-1502.md`, `.../python/pyproject.toml`, `.../python/src/dotfiles_setup/codec.py`, `.../tests/test_workflows_js.py`, `.../.claude/workflows/research-sweep-run.js`, `.../docs/research/saved-searches/orchestration-2026-10-02.toml`, `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/generated/research_record.py`.
