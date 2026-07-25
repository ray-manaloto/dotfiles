# SPEC-axis review — `feat/tool-currency-engine`

**Caveat first:** `session-2026-07-24.md` contains **no G1–G8 list** (only passing refs to
"G4" and "(D2/D3/G4)"). G2/G6/G7/G8 were judged against the diff's own recorded rationale,
not a verbatim spec line. Verified honoured: **D1** (skill invocable, hook calls step 1),
**D4/G6** (row every run, `has_content` gates the detail page), **D5** (all four issues +
the schema gap in `currency.toml`), **G2** (no cross-repo assertion).

## (a) MISSING / PARTIAL

1. **Step 2's "and update" is not implemented.** Spec: *"check if there is a new version
   **and update**"*. `run.py` only reports; `Verdict.auto_apply` is a boolean **nothing
   consumes**. The bump is prose in `SKILL.md` §4 telling the model to hand-edit
   `mise.toml` + the manifest. No code opens the G8 PR. Plainly narrower than asked.
2. **Step 1 ignores "generated outputs".** Spec: *"in sync w the ... graph **and generated
   outputs**"*. Only `graphify-out/graph.json` is fingerprinted. wiki/graphml/svg/obsidian/
   `GRAPH_REPORT.md` are unchecked, and `kb-artifacts` never re-stamps — regenerating views
   under a different graphify leaves no trace.
3. **"extensions tools" is thinner than the spec's own definition.** `-d` defines it as
   graphify's extras **+ `ffmpeg` (conda, host-only)**. `_check_extras` only compares
   `mise.toml` against `currency.toml`; `extra_probes` covers 3 packages; **`conda:ffmpeg`
   is not tracked at all**.
4. **Step 3's second half is absent.** Spec: *"check if changes affect projects **or if
   there are features we should accept**"*. Implemented as a 1200-char excerpt + a
   breaking-marker scan. Neither engine nor skill ever asks "does this affect us / should we
   adopt this feature" — only gate ambiguities reach `AskUserQuestion`.

## (b) SCOPE CREEP / D6 overshoot

5. **Stamp back-compat for a format that never shipped.** `_STAMP_VERSION = 2` plus a
   "v1 stamps still read" DRIFT branch — v1 existed only in commit 1 of this same unmerged
   branch. Dead migration code against *"minimal core now"* (D6).
6. **Size.** ~2,070 impl + 1,139 test lines, 7 modules, for one pilot tool; plus
   collision-suffixed detail filenames, `--verbose/--no-write/--json`, notes truncation.
   Defensible, but past "minimal".

## (c) IMPLEMENTED BUT WRONG

7. **`graph.py::_stamp_build` stamps the wrong tool.** `next((s for s in config.load(...)
   if s.stamp), None)` takes the *first* stamped tool, then writes `graphify --version` into
   it. Multi-tool config — the whole premise — silently corrupts the stamp.
8. **The configurability claim is false for two named tools.** `probe()` returns
   `reachable=False` when `pypi` is empty; **mise and hk are not PyPI packages**, so every
   run yields a permanent "upstream could not be checked" ambiguity — contradicting
   `config.py`'s *"mise, hk, uv, ruff and ty adopt the same shape with no engine change"*.
9. **SessionStart hook violates the repo's own mandate.** It hardcodes
   `/Users/rmanaloto/.../knowledge-base` (breaks on any other clone) and calls
   `uv run kb-setup currency check` directly instead of `mise run kb-currency-check`
   ("never run … by hand — drive it through a mise task").

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the reviewed diff (PR #4).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — `export.py` read as ground truth.
