# Standards review (mattpocock code-review, Standards axis) — #1329 `64fd545e...a9e633d1`

Reviewer: general-purpose subagent (Opus), read-only. Persisted verbatim by the coordinator.

---

**Standards review of a9e633d1 (#1329): no hard violations, two soft breaches of documented standards, three judgement calls**

I could not write `findings.md`, so please persist this report.

**Documented-standard breaches (soft)**

1. **`tests/test_codegen_check.py`, fixture `_generator_present` and `test_a_missing_generator_is_an_error_not_drift`.** Both call `monkeypatch.setattr(codegen_check, "generator_binary", ...)`.
   - This breaks `tests/AGENTS.md` § Mocking: "Never mock our own modules … At a boundary, prefer **injecting** the dependency."
   - `check()` already injects `run`, but the binary lookup is patched instead. Fix: add a `binary: Path` parameter to `check()`, defaulting to `generator_binary()`.
2. **No test runs the real generator.**
   - `.claude/rules/real-integration-evidence.md` asks for "at least one real invocation through the public project entrypoint plus its real failure/control arm". Every rc arm here comes from the injected `run`.
   - The hk `codegen_check` step does run the real path, so the pass arm exists outside the tests. The fail arm (a hand-edited `drift_verdict.py` giving rc=1) is not recorded anywhere in the diff.
   - Without it, the claim that the native `--check` really exits 1 on drift is unverified. It matters because `check()` maps the generator's raw rc straight onto `DriftVerdict`.

**Baseline smells (judgement calls)**

3. **Duplicated Code / Shotgun Surgery.** The new `DriftVerdict` (0 in sync / 1 drift / 2 error) duplicates two hand-written exit-code enums that already exist:
   - `CurrencyCode` in `dependency_currency.py:53` (`OK = 0`, `OUTDATED = 1`, `PROBE_UNAVAILABLE = 2`)
   - `PluginHealthCode` in `plugin_health.py:45` (`OK = 0`, `DRIFT = 1`, `CLI_UNAVAILABLE = 2`)

   The new python/AGENTS.md section says enums are "generated, never hand-written", so these two now contradict it. Neither is migrated, and no follow-up issue is cited. As a pilot that is defensible, but it should be tracked.
4. **Inconsistent invocation between the two new mise tasks.**
   - `codegen` uses `dir = "{{config_root}}/python"` with `--project .`, while `codegen-check` uses `--project python` and no `dir`.
   - The comment on `codegen` explains its own `dir`. The check gets the same cwd differently, through `cwd=(root / PYPROJECT).parent` in Python, so the cwd rule lives in two places.
5. **The `python/pyproject.toml` comment points outside the repo.** It says "see the comments there for why `use-annotated`/`field-constraints` and `disable-timestamp` are non-optional", where "there" is knowledge-base's pyproject. A reader in this repo can't follow it, and the reason can drift with no sign here. Inline one line per setting.

**Checked, no issue**
- **zero-bash-logic:** the logic is in `codegen_check.py` and the hk step is a thin wrapper.
- **use-tool-builtins:** the custom code is justified in writing in the module docstring (the stale-module gap the native `--check` misses).
- **mise-tasks-only:** a task is shipped.
- **ci-local-parity:** CI's hk run picks up the new step.
- **probes-need-a-control-arm:** both the stale arm and the reject arm are pinned.
- **Suite tokens:** they bind call sites. I did not run token-check, so uniqueness is unverified.
