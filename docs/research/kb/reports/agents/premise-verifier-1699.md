# premise-verifier — spec-1699-ctx7-force-color.md (verbatim, received 2026-10-04)

PREMISE REPORT: spec-1699-ctx7-force-color.md (worktree ctx7-color-1699)
ROWS: 12 checked — 8 CONFIRMED (0 provenance-corrected), 0 REFUTED, 3 UNVERIFIABLE, 1 ASSUMED (0 checkable)

P1. CONFIRMED — research_fanout.py:344-350 `subprocess.Popen(argv, stdout=PIPE, stderr=PIPE, env=env, start_new_session=True)`; only Popen in the module (grep subprocess.run/Popen/check_output → only :344).
P2. CONFIRMED — research_fanout.py:872 `env = child_env.clean_env(keep=frozenset({"CONTEXT7_API_KEY"}))`; child_env.py:77-92 filters only `is_credential` names + `__MISE_DIFF`; FORCE_COLOR is not credential-shaped (regex :49-52) so it passes through.
P3. CONFIRMED — research_fanout.py:832 `r"Context7-compatible library ID:\s*(\S+)"`; ESC (0x1b) and `[39m` are non-space → captured.
P4. CONFIRMED (cite slightly off) — fan_out at :1209-1214 (`runner: Runner = default_runner, http: Http = default_http`); FanoutRequest at :143-151 (query, repo, sources, limit, timeout, last30days_plan=None). Test call is tests/test_research_fanout.py:1242-1246, not 1239-1242.
P5. CONFIRMED — tests/test_research_fanout.py:757-761 `default_runner([sys.executable, "-c", parent, ...], timeout=timeout, env={})`.
P6. CONFIRMED — tests/test_research_fanout.py:330-337 writes `#!/bin/sh\nexit 0\n`, chmod 755, `monkeypatch.setenv("PATH", str(tmp_path))` (note: PATH becomes ONLY tmp_path).
P7. CONFIRMED — child_env.py:67-68, :91-92 build new dict comprehensions; tests/test_child_env.py:76-81 `test_the_source_environment_is_never_modified` asserts `before == SAMPLE`.
P8. CONFIRMED — saved_searches.py:43-56 imports `default_runner` (:54); `_PacedRunner.__call__` :481-488 delegates `self.runner(argv, timeout=timeout, env=env)`; default `runner: Runner = default_runner` at :1173, wrapped at :1068. No direct subprocess calls in saved_searches.
P9. UNVERIFIABLE (live measurement, not code) — report docs/research/kb/reports/agents/ctx7-color-1699.md:5-13 records it as measured 2026-10-04; matches row (29 / 0 / 0).
P10. UNVERIFIABLE (live measurement) — report :16-21 matches (119 / 119 / 119 / 0). Minor imprecision: "FORCE_COLOR=3 alone → 0" (report :16) was measured with `--jq .full_name`, a different output shape from the plain `gh api` rows; does not affect the design (drops the name regardless).
P11. UNVERIFIABLE — requires `git show c86f5ac3:...`; cannot read with my tools. Only evidence is report :28-30 (an unchecked claim, not a code read). Architect should run the diff before dispatch if the collision argument matters.
P12. ASSUMED — consistent with call sites: ctx7 output regex-parsed (:830-862), gh/firecrawl/last30days via `_items_from_payload`. Nothing in code contradicts it.

MISSING:
- M1 Other spawn paths: none. Only Popen in research_fanout.py/saved_searches.py is :344; `_gh_env` (:544), `_last30days_env` (:924), firecrawl env (:823) all flow through `runner(...)`, so the seam covers them. HTTP arms (exa, firecrawl-developer) use urlopen (:419, :434) — unaffected. No other python/src importer of research_fanout's default_runner (grep: only saved_searches.py:43,59). Non-blocking.
- M2 `FakeHttp` exists — dataclass at tests/test_research_fanout.py:215-238 (`responses` dict); `FakeHttp({})` already used at :727, :853, :1245. Non-blocking.
- M3 Existing tests asserting exact env passed to Popen: none found. `fake_popen` at :804-806 ignores `**_options`; tests/test_graphify_skill.py:451 and test_fnhook_gates.py:240 are other modules' runners. Test at :757 passes `env={}` → becomes `{"NO_COLOR":"1"}`, child still runs. Non-blocking.
- M4 context7 path requires `shutil.which("ctx7")` (:979) to resolve via os.environ PATH; with `_install_path_tools` PATH is ONLY tmp_path, so the fake ctx7 script must use only /bin/sh builtins (printf, case, [) — no external binaries. Add a one-line row so the implementer knows.
- M5 An empty primary result triggers a context7 control run with `replace(request, repo=None)` and query "python" (:1034-1035, :1059-1061); the fake ctx7 must answer `library <anything>` with the same ID or a control run hits the not-found branch. Status.OK is set when items are non-empty (:1117). Non-blocking for the spec as written.
- M6 Mutation arm presumes the test process inherits FORCE_COLOR into `clean_env()` — it does: clean_env reads os.environ when base is None (:91), and `monkeypatch.setenv` mutates os.environ. Non-blocking.

VERDICT: READY TO DISPATCH — named residuals non-blocking: P9/P10 (live measurements, report matches; P10 --jq imprecision), P11 (unread; collision-only, not correctness), P12 (assumption, uncontradicted), M4/M5 (test-construction notes to pass to the implementer).

---
Architect annotation: P11 was verified by the architect this session (`git show c86f5ac3:python/src/dotfiles_setup/research_fanout.py` lines 506-532 printed and compared with main 340-366 — identical). M4/M5 + P4 cite folded into the spec before dispatch.
