# Lane G — standards review of c382f44a (9fdcaf4c...HEAD)

## Documented-standard breaches

1. **Tautological assertion (hard).** `tests/test_pr.py::test_gate_matrix_adds_sync_full_exactly_when_ship_would_refuse`: `assert has_gate is pr.needs_full_sync(paths)`. `gate_matrix` calls `needs_full_sync`, so the loop passes by construction and can never disagree with the code. This breaks `tests/AGENTS.md` § anti-patterns ("Tautological — expected values must come from an independent source"). Only the two trailing literal asserts are independent, and they skip the `README.md` row. Fix: pin a literal expected value for each of the three rows. The parametrized ship test already covers the ship side.
2. **Mocking our own modules (judgement; the file already does this).** `tests/AGENTS.md` § Mocking says "Never mock our own modules, internal collaborators". The new ship test patches `pr._current_branch`, `_working_tree_clean`, `changed_paths_vs_main` and `run_gates`. The end-to-end sync test patches `sync.resolve_names` and `_report_inflight`. `test_container_state_refuses_a_hung_daemon` patches the private `doctor._DOCKER_PS_TIMEOUT_S`, which couples the test to a constant in another module. This follows the existing pattern in test_pr.py (lines 267-490), so it is not a new kind of breach. An injected timeout parameter on `docker_container_rows` would be the seam the standard prefers.
3. **The fake-docker approach complies with the standard.** It uses `sh` as a real subprocess boundary (`tests/AGENTS.md` allows `sh`/`git`). The `git worktree` fixture is also allowed, and it isolates global config.

## Baseline smells (judgement calls)

- **Duplicated Code, half consolidated.** `sync.container_image_id` (sync.py ~515-524) still builds the same `docker ps … --filter label=workspace --filter label=arch` through `_run`, which swallows the rc. The query now has two implementations, one strict and one lenient. `observe()` probably calls `container_state` first, so this is not a correctness bug. But the doctor docstring's "The one implementation of this query" is now an overclaim.
- **Feature Envy / Divergent Change in `doctor.py`.** `pr.py` and `sync.py` now import their docker and git primitives (`docker_container_rows`, `DockerUnavailableError`, `is_linked_worktree`) from the 1600+-line diagnostics module. `doctor.py` will now change for sync and ship reasons too. These helpers belong in a small shared module (e.g. a `docker_probe` / `git_probe`).
- **Inconsistent seam in a test.** `test_container_state_filters_on_both_id_labels_not_local_folder` now mixes a `_run` capture with re-splitting the fake's `"$*"` log (`log.read_text().split()`). Whitespace splitting loses argv boundaries, which is fine for label substrings but fragile.
- **Env drift.** `sync._run` passes `env=child_env.without_git_context()`; `docker_container_rows` does not. The behaviour changed silently for this call. It is harmless for docker.
- **Fail-open choice.** `is_linked_worktree` returns False when git fails, so ship proceeds and later dies in `sync-full`. This matches its docstring, but in this caller "fail open" means "skip the early refusal". It is acceptable, but it should be stated at the call site.

Docs: both SKILL.md copies got the same row, so the mirror is in sync. No zero-bash-logic or use-tool-builtins issues.

---

_Annotation added at promotion (2026-10-03); the report text above is verbatim._

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — commit c382f44a reviewed against repo standards
