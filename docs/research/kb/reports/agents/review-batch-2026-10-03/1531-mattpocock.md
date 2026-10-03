# #1531 — /mattpocock-skills:code-review (Standards + Spec)

- Range: `c4faf5ba..63c0b6dd` (first parent → squash merge). The worktree was NOT checked out (auto-mode denied the detach), so both axes read git objects.
- Spec sources: commit bullets, cold-review F1-F8, `.claude/CLAUDE.md:81` ruling. No brief commissioned #1531; the spec agent checked three candidate briefs.
- Verdict: Standards 1 near-hard (TEST-INDEX) + smells; Spec 2 missing/partial (F7 unaddressed, stale F4 narrative), 2 scope, 1 wrong (agy symlink root = #1599 finding 2)

## Standards (verbatim, from `1531-mattpocock-standards.raw.md`)

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


## Spec (verbatim, from `1531-mattpocock-spec.raw.md`)

# PR #1531 — SPEC axis (63c0b6dd)

**Briefs:** none of the three briefs commissioned #1531. `session-2026-10-01c.md:47` only records the merge. `brief-native-cli-devcontainer…:51` ("doctor/install-doctor … provenance assertions") covers the container sibling. The governing specs are therefore the commit bullets, cold review F1–F8, and the ruling (`.claude/CLAUDE.md:81`, "agy, codex and claude come only from their native, self-updating installers on the Mac AND in the devcontainer"). The PR body adds nothing beyond the commit titles and a CodeRabbit summary.

## "re-created" vs F4: which governs
F4 governs. Bullet 1 says "WARN when … a mise install dir for one of these tools was re-created". F4 says "drop the unenforced 're-created' … clauses". F4 comes later in the same squash and explicitly supersedes bullet 1. The code matches F4: it warns when the directory **exists** (`path_drift.py:648-656`), and `doctor.toml:254` agrees ("An existing installs/<slug> … WARNS"). What remains is a defect in the commit message only: the squash message still carries the stale bullet-1 claim.

## (a) Missing / partial
1. **F7 not addressed, although the message claims "cold review F1-F8".** There is no F7 bullet. F7 reads: "Nothing in the doctor enforces the FAIL/WARN severity split … `--strict` exits 1 on either." The adapter still flattens both lists, at `doctor.py:1294` `return [*report.failures, *report.warnings]`. As a result, the bullet-1 FAIL/WARN distinction exists only as a text prefix.
2. **F4's folded narrative clause survives.** The cold review (E6 row: "The usual trigger is a stale pin in an old worktree's mise config … folded into F4") targeted it, but the WARN still says "If it comes back, look for a `{spec}` pin in an old worktree's mise config" (`path_drift.py:653-655`). Nothing enforces that sentence.

## (b) Scope creep
3. **One malformed table disables the whole check.** If any `[path_drift.native_only.X]` table lacks `native`, the adapter returns a single finding and checks none of the other binaries (`doctor.py:1281-1287`). Nothing in the spec asked for that. It is defensible, but it is wider than "reject that entry".
4. **A stale comment.** "`native_clis_container`, on a sibling branch; once both land…" (`path_drift.py:413-414`): that module is present at 63c0b6dd. The comment is harmless but already stale on merge.

## (c) Implemented but looks wrong
5. **F1 is not fully closed for agy.** F1 says "native is POSITIVE". However, `native_roots` calls `.resolve()` on the declared root (`path_drift.py:537-541`), and agy's root is the file `~/.local/bin/agy` itself. If `~/.local/bin/agy` is a symlink into a Homebrew cask or a bun or npm global, the root resolves to that foreign target, and `is_native` (`:544-547`) returns True. A mise-target symlink would still FAIL through the `_from_mise` branch (`:616`), but no branch catches a foreign-target symlink. codex and claude are not affected, because their roots are vendor-owned directories. This is static reasoning; I did not probe it live.
6. **F6 is a judgment call, not a defect.** The bullet says "Silent off macOS (the devcontainer has its own check)". The ruling covers the devcontainer too, and that coverage is delegated to `native_clis_container.py`, which exists at 63c0b6dd. The delegation is accepted.

Everything else is implemented as specified: F2 (`uninstall_spec` by slug, shim → `mise which`), F3 (tests at `test_doctor.py:2077-2128`), F5 (the spec lists in `doctor.toml`), F8 (the `suites.toml` contract), and the BLIND path reported as a finding (`doctor.py:1292-1293`).

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): PR #1531 body and source at 63c0b6dd.


## Summary

- Standards: 2 documented-standard findings + 6 smells; worst = `tests/TEST-INDEX.md` not updated for the new native-only tests.
- Spec: 6 findings; worst = F7 (FAIL/WARN severity split) unaddressed despite "cold review F1-F8" (`doctor.py:1294`).

## Disposition

- Spec 5 (agy symlink root) and Spec 3 (one bad table) were already filed as #1599 (findings 2 and 3).
- F7 severity merge and TEST-INDEX staleness: comment on #1599 (same check, same follow-up PR).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR #1531 body
