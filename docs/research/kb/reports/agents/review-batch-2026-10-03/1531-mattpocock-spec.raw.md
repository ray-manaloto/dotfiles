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
