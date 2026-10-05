# gfy-T3 standards review: `origin/main...HEAD` on feat/graphify-fleet

Scope: 6b4719f7, 8b3c3983, 6563119b, eb6fb8bd, 1e7a2911. This was a read-only review. Tooling-enforced items (ruff ALL, ty, typos, codegen-check) were skipped. Checks that came back clean: no inline suppressions in either file (grep rc=1; the control is hk.pkl, which returns 4 hits). The mise task is a thin caller. The native-first justification is in the module docstring. The skill mirror is byte-identical.

## Documented-standard breaches

1. **`tests/test_graphify_fleet.py` `Currency` class (judgement, leaning hard).** The test fakes `graphify_currency.locked_version`, `check` and `_path_binary_probe`. tests/AGENTS.md § Mocking says to "Never mock our own modules, internal collaborators". The `FleetProbes` seam is injection, which that file prefers. But what gets substituted is our own module, not a system boundary. Because of that, no test exercises the real offline `check()` result feeding `_dotfiles_leg`.
2. **`graphify_fleet.py:259` `if "UNVERIFIABLE" in drift.detail:` (judgement).** This sniffs another module's message text to classify the result. probes-need-a-control-arm.md rule 9 says "never sniff for a symptom … a log string … warning's wording". If someone rewords `graphify_currency`, the leg silently turns from unverifiable into drift. A typed field on `Drift` should carry this instead.
3. **`_Context`, `FleetRoots`, `_LegBuilder` and `PathProbe` are hand-written (judgement).** python/AGENTS.md says "Models and enums are generated, never hand-written". `_Context` is plan data returned from the public `gather()`, so it is model-shaped. `PathProbe` re-declares the shape of `graphify_currency._Probe` instead of sharing it.
4. **Line 53: `from dotfiles_setup.graphify_currency import _path_binary_probe` (judgement).** This makes a private name a cross-module API. No repo rule covers it, but it couples the two modules.

## Baseline smells (all judgement calls)

- **Duplicated Code.** `PlanStep(..., commands=[], human_gate=True, runnable=False)` appears 5 times. A `_human_step(leg, summary)` helper would cover it.
- **Duplicated Code / Divergent Change.** The host branch of `apply_leg` repeats the host step from `plan()` (`_host_commands` plus its own current check).
- **Mysterious Name / positional coupling.** `kb_behind = legs[1].state` (line 471) depends on list order. `by_name` already exists in `plan()`.
- **Repeated Switches.** `_SEVERITY`, `_EXIT` and the `leg.name` if/elif in `plan()` all switch on the same enums.
- **Primitive Obsession.** `drift.kind == "path-binary"` (line 256) compares against a bare string, which `graphify_currency` also uses. Findings encode state as an `"UNVERIFIABLE: "` string prefix.
- **Data Clumps.** `(run, roots)` and `(run, roots, probes)` are threaded through every probe.
- **Speculative Generality / Middle Man.** In `graphify_fleet_main`, `default_roots()` builds a `FleetRoots` and then the code rebuilds it field by field. `dataclasses.replace` would do this in one call.
- **Hard-coded environment.** `default_roots` hard-codes `~/dev/github/ray-manaloto`.

## GitHub repos touched

_None._
