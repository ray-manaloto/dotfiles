# Cold review: 00901c16a54c474217d680b9424ea497fb47933e (parent 233e1e4)

feat(graphify): wrap affected + prs blast-radius tooling

## Findings

MEDIUM | `affected()` has no output-size cap, unlike `query()`'s deliberate
`_MAX_AGENT_OUTPUT_BYTES` (65,536 B) transport cap | python/src/dotfiles_setup/graphify.py:404-433
(affected) vs :349-368 (query, the `_MAX_AGENT_OUTPUT_BYTES` check at ~L351-356
of the file, exact block starting `output_bytes = result.stdout.encode()`).
`query()` explicitly bounds its own subprocess output before returning it to
an agent, citing "agent transport cap" in the error text. `affected()` has no
`--budget`-equivalent and no post-hoc size check at all — it returns
`result.stdout.strip()` unconditionally. Failure scenario: `mise run
graphify-affected -- "<widely-used-symbol>" --depth 3` (or any depth>2) on a
true god-node (a function/module referenced by hundreds of call sites) can
return an arbitrarily large text blob straight into an agent's context with
no truncation and no error — exactly the class of "return a success-shaped
result that is actually harmful" the query() cap exists to prevent. Verified
graphify's own `affected.py` has no truncation/budget logic of its own
(`grep -in "truncat\|MAX_\|limit" affected.py` → 0 hits), so nothing upstream
bounds it either. This is a real asymmetry between the two "mirrors query()"
functions, not cosmetic: the commit message says affected is "Health-gated
exactly like query()" but is silent about the other three checks query() also
performs (post-run health-drift re-check, non-empty-stderr-on-success ->
IncompleteError, and the TRUNCATED-marker check) — all three are omitted in
affected(), and only the byte cap has a plausible real trigger (the other two:
post-run drift is a nice-to-have but low-probability race; affected's own
CLI path never writes to stderr on a success rc=0, confirmed by grep — so
that specific omission is currently inert; graphify's `affected.py` carries
no TRUNCATED marker at all, confirmed by grep, so that check would be a
no-op if copied). Net: the byte-cap omission is the one gap with a real
failure scenario; flag it, the rest is inherited-shape drift worth noting but
not exploitable today.

LOW | exit-code 1 from `prs()` cannot distinguish "gh not authenticated" from
"PR #N not found in open PRs" — both surface as `GraphifyError`, rc 1 |
python/src/dotfiles_setup/graphify.py:508-511 (prs, generic
`result.returncode != 0` -> GraphifyError), graphify's own
`prs.py:718-721` (auth RuntimeError -> sys.exit(1)) vs `prs.py:733-736`
(`if not match: ... sys.exit(1)`). This is inherited from graphify's own CLI
(both paths already collapse to the same exit code upstream) rather than
introduced by this diff, and the brief in graphify.py:497-506 documents only
the auth-failure shape, not the PR-not-found one — so a caller scripting on
this wrapper's exit code alone genuinely cannot tell "you're logged out" from
"typo'd the PR number" without reading the message text. Not a new defect,
but the docstring/skill both imply exit codes are meaningfully typed the way
`affected_main`'s rc 3 vs rc 1 are, and for `prs` they are not.

## Areas read and cleared (no findings)

1. **graphify.py error/empty/not-found/subprocess-failure branches** — every
   branch in `affected()`/`affected_main()`/`prs()`/`prs_main()` read.
   - `affected()` never fails silently: unhealthy graph -> `GraphifyIncompleteError`
     (rc 3) BEFORE any subprocess runs (verified `called is False` test at
     tests/test_graphify.py:869-891, and live: no-match query still ran the
     subprocess and returned rc 0 with the real "No unique node match for …"
     text, confirmed live at the real CLI: `graphify affected
     "totally_bogus_symbol_xyz123"` -> rc 0, exact text match).
   - Health-gate split (item 2 of the brief) is correct for what each function
     actually reads: `affected()` reads `graphify-out/graph.json` via a
     `--graph` argv flag it always passes (graphify.py:388, `build_affected_args`)
     so it MUST gate; `prs()` never passes `--graph` at all (`build_prs_args`,
     graphify.py:466-479, only ever emits `--repo`/`--base`/the bare PR digit) —
     graphify's own `prs.py:689` resolves the graph path itself via
     `_default_graph_json()` relative to the subprocess `cwd` (which `_run`
     always sets to `project_root`), and only touches it at all when
     `needs_impact` is true (`prs.py:735`, `graph_path.exists() and
     (pr_number is not None or do_triage or do_conflicts)`) — confirmed by
     reading `prs.py:681-736` directly. So there is NO path where the ungated
     `prs()` touches the graph without graphify's own internal existence
     check; the split is correct.
   - Exit codes, stated plainly: `affected_main` — rc 0 success (incl. the
     "no match" case, which IS success text, not an error), rc 1 graphify
     subprocess failure, rc 3 graph unavailable (`GraphifyIncompleteError`).
     `prs_main` — rc 0 success (dashboard or detail), rc 1 for ANY
     `GraphifyError` (auth failure, PR-not-found, or any other nonzero rc from
     the subprocess) — no rc 3 path since there is no health gate to fail.
     A caller CAN distinguish "found nothing" (rc 0, read the text) from
     "could not look" (rc 3, `affected` only) for `affected`; for `prs` all
     failure modes collapse to rc 1 (see LOW finding above).

2. **CLI wiring in main.py** — identical shape to the pre-existing
   `query`/`health`/`update`/`hook-guard` subcommands: same
   `graphify_sub.add_parser` + `add_argument` pattern
   (main.py:908-936), same `getattr(args, "graphify_command", None) ==
   "<name>"` dispatch chain appended in `handle_graphify()`
   (main.py:1832-1849), same `sys.exit(<x>_main(...))` call shape as the
   `query`/`health` cases immediately above it. No divergence in argument
   passing, error propagation, or exit-code shape found.

3. **tests/test_graphify.py (~297 new lines)** — read every new assertion.
   None are tautological; each binds real behavior:
   - `test_build_affected_args_*` / `test_build_prs_args_*`: pure argv-shape
     assertions against literal lists — would fail immediately if arg order,
     flag names, or the relations-repeat behavior changed. Reverting the
     `--relation` handling (e.g. dropping the loop) fails
     `test_build_affected_args_preserves_repeatable_relations`.
   - `test_affected_refuses_unhealthy_graph_before_running_graphify` asserts
     `called is False` on the monkeypatched `_run` — this is the one test in
     the suite that would catch a regression to "gate exists but doesn't
     actually prevent the subprocess" (a real distinct bug class from "no
     gate at all"). Good.
   - `test_affected_returns_no_match_message_as_success_not_error` — reverting
     the "no-match is success, not error" design (e.g. by having `affected()`
     treat any recognizable "No unique node match" text as an error) would
     fail this test, since it asserts `result.text` equals the message rather
     than asserting a bare truthy value.
   - `test_prs_returns_dashboard_text_with_no_health_gate` — monkeypatches
     `graphify_health` to return MISSING and asserts `health_called is
     False`; if `prs()` were changed to call the gate, this test would fail
     (either on the assertion or via `GraphifyIncompleteError` propagating
     unhandled). Binds the "no gate" claim correctly — this is the strongest
     test in the file for exactly the design decision the brief flagged as
     needing scrutiny (item 1).
   - `test_prs_raises_graphify_error_on_gh_auth_failure` — fakes rc=1 with
     the real graphify auth-failure stderr text; asserts it surfaces as
     `GraphifyError`, not a raw traceback. Matches live behavior (graphify's
     `prs.py:718-721` catches `RuntimeError` and prints+exits itself, so the
     wrapper never sees a traceback either way — this test is really only
     checking rc-to-exception mapping, but that mapping is exactly what
     `prs()` adds, so it's a real assertion of the new code, not decoration).
   - No test touches real network, real `gh`, real user directories
     (all use `tmp_path`), or wall-clock timing. Every subprocess boundary is
     replaced via `monkeypatch.setattr("dotfiles_setup.graphify._run", ...)`.
     Control arm: grepped the whole new test block for `subprocess.run(`,
     `Path.home`, `time.sleep`, `requests.`, `gh ` — zero hits outside the
     `fake_run` fixtures' own fake `CompletedProcess` construction.

4. **`.claude/skills/blast-radius/SKILL.md`** — every factual claim checked
   against the real graphify source and/or a live run, not just prose review:
   - "`affected` reuses `graphify_health`... a missing/stale/corrupt/
     version-drifted graph raises... rc 3" — verified against
     `graphify.py:414-417` and the CLI exit-code table above. True.
   - `"No unique node match for <node>"` at rc 0 vs `"No affected nodes
     found."` (found the node, but nothing depends on it) as two DISTINCT
     messages — verified live in `graphify/affected.py:269` and `:278`
     (exact strings), and live-ran the no-match case (rc 0, exact text
     match). True, and this is a genuinely useful distinction the skill
     correctly calls out.
   - "graph-impact deep dive... fires only when you actually pass a number,
     `--triage`, or `--conflicts`" — verified against `prs.py:735`
     (`needs_impact = ... (pr_number is not None or do_triage or
     do_conflicts)`). True. (Our wrapper never exposes `--triage`/
     `--conflicts` at all — deliberate per commit message C4 — so from this
     wrapper's surface only the PR-number path can trigger it; the skill's
     wording "or `--triage`, or `--conflicts`" is technically describing
     graphify's underlying behavior rather than this wrapper's surface,
     which could read as those flags being reachable through `mise run
     graphify-prs` when they are not (`build_prs_args` has no path to emit
     them). Minor prose-precision nit, not a factual error about graphify
     itself — LOW, not listed as a numbered finding since nothing is false,
     just slightly ambiguous about which surface it describes.)
   - "No graph-health gate, and that's deliberate... the impact path checks
     `graph_path.exists()` internally and silently skips impact (not an
     error) when the graph is missing" — verified `prs.py:735-736`. True.
   - "Needs an authenticated `gh`, and makes network calls... never a
     traceback" — verified `prs.py:718-721` catches `RuntimeError` from
     `_gh()` (prs.py:210) and exits 1 with a printed message. True.
   - Ran both documented commands read-only against the real repo graph:
     `mise run graphify-affected -- "graphify_health"` → real caller list,
     rc 0; `dotfiles-setup graphify affected "totally_bogus_symbol_xyz123"`
     → exact "No unique node match for …" text, rc 0. Matches the commit
     message's own verification claims.
   - No omitted failure mode found beyond the byte-cap gap already reported
     under MEDIUM (which the skill doesn't mention for `affected`, but
     accurately mirrors what the code itself does — not a documentation bug
     independent of the code gap).

5. **mise.toml new tasks** — both `graphify-affected` and `graphify-prs` are
   thin one-line `run = 'uv run --project python dotfiles-setup graphify
   <cmd>'` callers, byte-identical in shape to the pre-existing
   `graphify-query`/`graphify-health`/`graphify-update` tasks (compared all
   five `run =` lines directly, mise.toml:730/734/746/756/767). No logic in
   either task. Args pass through the same way (`-- "<node>"` /
   `-- <PR#> --base main`) as documented for the existing tasks. No findings.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed commit and its history.
- graphify (vendored as an installed `graphifyy` package, `python/.venv/lib/python3.14/site-packages/graphify/`, not a repo checkout) — read `affected.py`, `prs.py`, `cli.py`, `paths.py` directly to verify every SKILL.md and docstring claim against real upstream source. No public repo URL resolved for it in this pass (not needed — read from the installed package on disk, which is the authoritative artifact this commit's code actually calls).
