# PR #1531 — Standards axis (c4faf5ba..63c0b6dd)

No inline suppressions: a grep of the diff for noqa, type: ignore, nosec and pylint returned 0 hits. That grep was not control-armed. No new `.sh` file. The committed cold-review report carries `## GitHub repos touched` (`_None._`, at :64). That satisfies research-repo-enumeration.

## (a) Documented-standard violations

1. **tests/TEST-INDEX.md not synced. Medium, near-hard.** The diff adds 8+ native-only tests to `test_path_drift.py` and 5 to `test_doctor.py`. The `test_path_drift.py` row at TEST-INDEX.md:73 still describes only the stale-version preflight. tests/AGENTS.md says the per-file index lives in TEST-INDEX.md. tool-currency-and-native-first.md rule 5 says to "Sync the describing docs/skills in the SAME change." The `test_doctor.py` row (:67, "All 7 checks") was already stale before this PR. Moving the count from 16 to 17 made it staler.
2. **Tests patch private internals. Judgement call.** tests/AGENTS.md says to test "through a public interface … never through implementation details". `test_doctor.py` `_native_setup` monkeypatches `doctor_path_drift._SYSTEM_MISE_DATA` and `run_mise_ls` in another module. `test_path_drift.py:327` patches `_SYSTEM_MISE_DATA` too. The cause is that `_SYSTEM_MISE_DATA` (path_drift.py:446) is a hardcoded module constant, not a parameter of `mise_data_dirs`. `environ`, `home` and `installs_root` are injected, but this path is not.

## (b) Smells (all judgement)

- **Duplicated Code.** `DEFAULT_NATIVE_ONLY` (path_drift.py:415-441) is a byte-for-byte twin of the three `[path_drift.native_only.*]` tables in doctor.toml. The rationale comment is repeated a third time in the `check_native_only` docstring. The suites.toml contract binds the toml tables precisely because the fallback hides drift. One source should own the data.
- **Divergent Change.** path_drift.py's module docstring (:2) is "does this shell resolve the tools mise currently pins?". It now also answers a different question: provenance and native-ness, through ~320 added lines. That is two reasons to change in one module. The comment at :414 already anticipates moving it into a shared table.
- **Primitive Obsession / Repeated Switches.** Severity is encoded as `"FAIL: "`/`"WARN: "` string prefixes. `NativeOnlyReport` splits them, then `doctor.check_native_only` re-flattens them (`return [*report.failures, *report.warnings]`, doctor.py:1294), and tests recover severity with `startswith("WARN:")`.
- **Long, overlapping conditionals.** In `native_only_findings` (:595-660), `is_native(hits[0], roots)` is evaluated three times. A Homebrew-only host emits two FAILs by design (`test_a_homebrew_only_host_fails_twice`). Computing a single `first_is_native` plus an early return per branch would read more clearly.
- **Data Clump.** `(tool, path_value, data_dirs, home)` travels together through `native_only_findings`, `uninstall_spec` and `_from_mise`. `data_dirs` is threaded through 5 functions.
- **Mysterious Name.** `declared or None` (doctor.py:1291) makes an empty TOML table silently mean "use the module defaults". That intent is not visible at the call site.

## Repos touched
_None._
