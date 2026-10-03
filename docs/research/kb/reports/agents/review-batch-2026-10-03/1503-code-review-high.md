# #1503 — /code-review high

- Target: merge SHA `64fd545ec32ea1acb54b7dca9a4dda7a1708ddac` (fix/1496 install doctor)
- Lens: built-in `/code-review high` (forked, task `a7578a72a603e6f94`, 29 tool uses, 228s)
- Verdict: **FINDINGS** — 8

## Verbatim result

I reviewed commit `64fd545e` (#1503, which renames `claude-doctor` to `install-doctor`) and found 8 issues. The rename itself is complete. Outside historical records, a search for the old name at that commit finds only two history notes: the `graphify.py` docstring and `docs/rules-evidence/graphify-first.md:18`. The same search for `install-doctor` finds 30+ lines, so the search works.

The serious issues are in the new reserved-name test and the gate around it:
- **CI never runs the new test.** The pytest job in CI does not install Claude Code, so the test skips there. It also skips in the devcontainer, which has the older Claude 2.1.283. Only the Mac host runs it.
- **The test can quietly turn itself off.** The version reader returns None on any parse failure, and None means skip.
- **The real gate trusts whatever `claude` is on PATH.** It never checks that binary against the pin, so lint in the container passes a plugin name that CI lint rejects.

I appended a short summary to the worktree's `findings.md`, which git ignores. The full report below still needs to be saved verbatim under `docs/research/kb/reports/agents/`.

```json
[
  {
    "file": "tests/test_fnhook_gates.py",
    "line": 385,
    "summary": "The new reserved-name test is never run in CI: the pytest job (ci.yml, contract-preflight, around line 191-247) does not install Claude Code, so `_needs_real_tools` skips it. The devcontainer (claude 2.1.283) skips it because the running version is below the pin.",
    "failure_scenario": "A later change that drops the reserved-name fixture's rejection, or a claude bump that rewords 'is reserved', leaves every unattended run green. The test's three outcomes are skip in CI, skip in the container, and run only on the self-updating Mac host. `pytest -q` hides the skip, and a bot PR (no `ship`) never exercises it at all."
  },
  {
    "file": "tests/test_fnhook_gates.py",
    "line": 397,
    "summary": "`if running is None or running < pin: pytest.skip(...)` treats an unreadable version as 'too old' and skips, so the test can turn itself off for good.",
    "failure_scenario": "If `claude --version` changes its format (e.g. 'Claude Code 2.1.290', '2.1.290-beta', or a leading banner), `head[0]` fails `int()`, which returns None and skips. If the binary exits non-zero, that also returns None and skips. The test then becomes a check that can only pass (probes-need-a-control-arm.md rule 9: 'assert the capability — never sniff for a symptom'). The skip message even says 'running claude None predates the pinned (2, 1, 287)', which is misleading. An unreadable version should fail, not skip."
  },
  {
    "file": "python/src/dotfiles_setup/fnhook_gates.py",
    "line": 268,
    "summary": "`validate_plugin` runs whatever `claude` is on PATH and never checks it against the pin in `schemas/sources.toml`. The commit itself shows that older binaries accept plugin names the pinned one rejects.",
    "failure_scenario": "A new production plugin named `claude-foo` passes `mise run lint` / hk `fnhook_gates` inside the devcontainer (claude 2.1.283 accepts the name) and only fails in CI's lint job, which installs the pin. That breaks the CI-local parity rule. The gate is green on a stale binary, which is the exact failure #1496 hit on main."
  },
  {
    "file": "python/src/dotfiles_setup/fnhook_gates.py",
    "line": 268,
    "summary": "Altitude: the reserved `claude-` prefix is only enforced through an external binary whose behaviour depends on its version. A plain Python check on manifest names in `discover_plugin_dirs`/`fnhook_gates_main` would enforce it on every host.",
    "failure_scenario": "The fix renamed one plugin and added a fixture that only the newest binary rejects, rather than fixing the class. Any later `.claude/skills/claude-*/.claude-plugin` or `.agents/skills/claude-*` plugin gets through every gate that runs an older claude (devcontainer, a host that has not updated yet). A deterministic name-prefix assertion with its own control-arm fixture would catch it everywhere, at no subprocess cost."
  },
  {
    "file": "python/verification/suites.toml",
    "line": 2955,
    "summary": "The fnhook contract's `paths` and `per_path_tokens` were not extended to the new `tests/fixtures/fnhook/reserved-name` fixture or to `def test_reserved_name_fixture_is_rejected_by_the_pinned_claude(`.",
    "failure_scenario": "The contract exists to make the whole fnhook chain fail when a piece is deleted. Deleting the new test, or the fixture's `claude-fnhook-fixture-reserved` name, leaves `mise run verify` at 0 failed. Since CI skips the test anyway (finding 1), nothing records that the #1496 regression arm is gone."
  },
  {
    "file": "tests/fixtures/fnhook/reserved-name/hooks/hooks.json",
    "line": 2,
    "summary": "The fixture's `hooks.json` says 'Valid typed function-hook module', and both `hooks.json` and `register.ts` are byte-for-byte copies of `tests/fixtures/fnhook/valid`.",
    "failure_scenario": "Two copies of the same module drift independently. A future edit to `valid/register.ts` (e.g. an escape-hatch or API change) must be repeated by hand, or the reserved-name fixture can start failing `validate` for an unrelated reason, while the test only checks `rc != 0` plus a substring. Better: build the fixture in `tmp_path` by copying `valid` and rewriting only `plugin.json`'s name, or at least fix the misleading description."
  },
  {
    "file": "tests/test_fnhook_gates.py",
    "line": 363,
    "summary": "`_running_claude_version` writes its own subprocess-plus-version parser instead of reusing what already exists: `install_doctor` has `_run` with a timeout and `_VERSION_RE`, and `_real_tools_available` already runs `claude --version` at import.",
    "failure_scenario": "That makes two separate `claude --version` spawns and two version parsers that can disagree (install_doctor's regex accepts formats this `int()` split rejects). The new subprocess call also has no timeout, unlike every runner in `fnhook_gates`/`install_doctor`, so a hung `claude --version` (for example during a self-update) hangs pytest indefinitely."
  },
  {
    "file": ".claude/skills/install-doctor/.claude-plugin/plugin.json",
    "line": 2,
    "summary": "The plugin was renamed from `claude-doctor@skills-dir` to `install-doctor@skills-dir` by renaming its directory, with no entry in doctor's `[removed_plugins]` guard and no cleanup of per-user enable/disable state for the old id.",
    "failure_scenario": "An operator who ran `claude plugin disable claude-doctor@skills-dir` (the documented off-switch) gets the hook back silently under the new id, and it can again deny tool calls. Checkouts and worktrees on older branches still load `claude-doctor@skills-dir`, which 2.1.287 now rejects. Nothing in doctor or plugin-health reports either state, unlike plugin removals that go through `mise run plugin-remove`."
  }
]
```

## Lane triage (second read) — appended after receipt

Re-read at `785c3708` (current main), where the code is unchanged.

| # | Severity | Second read | Disposition |
|---|---|---|---|
| 1 | MED | CONFIRMED. `.github/actions/setup-claude-code` is used only by the `lint` job (`ci.yml:107`). pytest runs in `contract-preflight` (`ci.yml:245`) with no claude, so `_needs_real_tools` (`tests/test_fnhook_gates.py:98`) skips the arm in CI | Issue C |
| 2 | MED | CONFIRMED. `_running_claude_version` (`tests/test_fnhook_gates.py:363-380`) returns None on a non-zero rc or a parse error, and `running is None` leads to `pytest.skip` | Issue C |
| 3 | MED | CONFIRMED. `validate_plugin` (`fnhook_gates.py:268`) runs `CLAUDE_BINARY` off PATH with no pin comparison, so an older binary accepts a `claude-` name that the pinned one rejects | Issue D |
| 4 | MED (fix for 3) | Deterministic manifest-name prefix check | Folded into D |
| 5 | MED | CONFIRMED. `grep reserved python/verification/suites.toml` → 0 hits, so the fnhook contract does not bind the new arm | Issue C |
| 6 | LOW | Fixture duplicates `valid/` and carries a misleading description | Folded into C as a note |
| 7 | LOW | Second version parser; its subprocess has no timeout | Folded into C |
| 8 | LOW | An operator's disable of the old `claude-doctor@skills-dir` id does not carry over to the renamed plugin. Per-user state, not repo state | No issue. Noted |

Duplicate search (`gh api /search/issues`): `reserved claude prefix`, `fnhook reserved` and `test_reserved_name` hit only #1496/#1503 (closed). `claude-doctor rename` returned 12 hits (the control arm), none of them a duplicate.

## GitHub repos touched

_None._ (local git objects only)

## Issues filed

- C → [#1595](https://github.com/ray-manaloto/dotfiles/issues/1595)
- D → [#1596](https://github.com/ray-manaloto/dotfiles/issues/1596)
