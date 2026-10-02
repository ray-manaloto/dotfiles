# Cold review — `5dfb7eef` (fix/plugin-health-builtin) — 2026-10-01

**Lane:** an Opus cold-reviewer, acting as the FALLBACK lens for a Claude-authored diff. The
doctrine routes a Claude-authored diff to a read-only codex lens. codex is unavailable until
2026-10-03, so this is a same-family pass and has the same-family blind-spot caveat. A codex lens
can re-run it once codex is back.

**Subject:** exactly one commit, `5dfb7eefce74b84cc6da6a2315796168fa50a341`. Its merge-base with
`origin/main` (`846f2006`) is `9f286354`. Diff: `9f286354..5dfb7eef`, 2 files, +41/-1
(`python/src/dotfiles_setup/plugin_health.py`, `tests/test_plugin_health.py`).
The review was by ref only, so no intent was supplied. Cold-reviewer local memory was consulted
(`plugin_state_removal_review`, `claude_plugin_update_cli_review`, `mutation_harness`).

**Round shape:** round 1, OPEN HUNTING, plus Q-FRESH, Q-SCOPE and Q-CLAIM. Per the
adversarial-review skill it cannot end the loop by itself. It found no HIGH or MEDIUM, so
a bounded round would only re-verify LOW wording.

## Verdict: **SHIP**

The motivating defect is real and is fixed. Premise checks:

- `claude plugin list --json` emits 0 `@builtin` rows (P2, armed).
- The two-module live arm moves the real payload from `code 1` to `code 0` (P7).
- The new tests have teeth: 5 of the 6 mutations go red (P8).
- `ruff`, `ruff format --check`, `ty` and `typos` pass (P9). `verify run` from a scratch worktree reports 166 passed, 0 failed (P10).

Every finding is LOW or INFO: docstring and SKILL wording, plus one residual false negative that the
base could not genuinely detect either. One pre-existing defect is routed to a ticket (T1).

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | LOW | The exemption keys on the suffix, not on existence. A declared `@builtin` id that names NO real built-in (a typo, or one a CC upgrade dropped) now reads `OK`, where base read `DRIFT`. The doctor LIVE adapter never renders `builtin_unobservable`, so in doctor the id vanishes. Mitigation: base flagged EVERY built-in, valid ones included, so a typo was never distinguishable there either. No real detection was lost, which is why this is LOW. | `python/src/dotfiles_setup/plugin_health.py:256-263`, `:326-343` | P7: `+cc-plugin-you-shuold-know@builtin` gives BASE `code 1` and HEAD `code 0`, `dni []`. |
| F2 | LOW (Q-CLAIM) | Overstated clause: "so the check cannot see their install state at all". `claude plugin details <id>@builtin` resolves 4 of the 11 built-ins the binary registers, and rejects a fresh absent id with rc=1. It is NOT a usable oracle: the other 7 registered built-ins read "not found" too. The exemption design is right. Narrow the sentence to "no reliable CLI route". | `python/src/dotfiles_setup/plugin_health.py:93-95` | P4, P5 |
| F3 | LOW (Q-CLAIM) | Stale docstring. `evaluate()` still says "Report with code DRIFT if any list is non-empty, OK otherwise", but the report now carries a fourth list that is non-empty under `OK`, and the new test asserts exactly that. | `python/src/dotfiles_setup/plugin_health.py:238-239` vs `tests/test_plugin_health.py:52-58` | read |
| F4 | LOW (doc drift) | Not updated by the diff: `plugin-health` SKILL.md § "Reading the report" still defines `declared_not_installed` as "settings enable it, no CLI row exists anywhere". That is now false for `@builtin`. The section also says nothing of the new `builtin_unobservable` key. Applies to the `.claude` file and its `.agents` mirror. | `.claude/skills/plugin-health/SKILL.md:42`; `.agents/skills/plugin-health/SKILL.md:42` | read |
| F5 | LOW (test gap / Q-CLAIM) | The control test's docstring says "only the @builtin suffix is exempt". The test cannot tell `@builtin` from `builtin`: mutation M3 (`BUILTIN_SUFFIX = "builtin"`, dropping the `@`) stays 16/16 green. A marketplace-side lookalike such as `x@notbuiltin` would pin it, and the mutation turns that id from `DRIFT` to silently exempt. | `tests/test_plugin_health.py:60-68`; `python/src/dotfiles_setup/plugin_health.py:96` | P8 M3 |
| F6 | INFO | The predicate is looser than the vendor's own. CC 2.1.287's built-in test is `e.endsWith("@builtin") && e.indexOf("@")===e.length-8 && e.length>8`: one `@`, non-empty name. The diff's `endswith` also exempts the malformed `@builtin` and `a@b@builtin`, which CC does not treat as built-ins. Base reported both as `DRIFT`; HEAD reports them as `OK`. | `python/src/dotfiles_setup/plugin_health.py:257` | P3 (binary offset 179464332, `jSn`), P11 |
| F7 | INFO | No contract binds the new behaviour. `workflow.plugin-health-gates` pins 5 test names and neither new test, so deleting both stays green in `verify`. | `python/verification/suites.toml:2974` | P12 |
| T1 | TICKET (pre-existing, out of scope) | The live SessionStart function hook types and reads `declared_not_effective` / `effective_not_declared`. The Python report has NEVER emitted those keys; it emits `declared_not_installed` / `declared_disabled_here` / `installed_not_declared`. So on `DRIFT` (rc=1) the hook pushes zero lines and SessionStart stays silent, both for the false positive this commit fixes and for every real drift. Present since #1061 (`ed656dd4`). No existing issue. | `.claude/skills/plugin-health/hooks/plugin-health.ts:12-17,73-83` | P6 |

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH:** N/A. The diff adds no decision→action pair. `evaluate()` is a pure reconciliation of one
  `read_rows()` snapshot, and no action follows it.
- **Q-SCOPE:** F1-F7 concern the diff's own lines and are in scope. T1 is a pre-existing sibling defect
  in the hook consumer and goes to a ticket. Two siblings that also iterate enabled ids were checked and are
  clean: `doctor.collect_servers` → `plugin_mcp_path` and `listing_budget.collect_listing` → `plugin_root`.
  Both return `None` for a `@builtin` id, which has no marketplace dir and no cache dir, and skip it silently.
  The `.agents` mirror's "codex mcp list" rewrite at line 61 is the known skills-mirror
  defect (#1370), not this diff.
- **Q-CLAIM:** every clause this diff adds or changes:

  | String | Clause | Enforcing line / evidence | Outcome |
  |---|---|---|---|
  | module docstring | "listed under `builtin_unobservable`" | `:256-258` | ok |
  | module docstring | "never `declared_not_installed`" | `:261-263` | ok |
  | module docstring | "ship inside the Claude Code binary" | P3 `ove()` `rpe(...)` | ok |
  | module docstring | "`plugin list --json` emits no row for any of them" | P2: 0/285 | ok |
  | module docstring | "measured on 2.1.287 … while `diff` and `agents-md` were active" | author's measurement | **UNVERIFIED**; the active state at their time cannot be reproduced |
  | constant comment | "never emits a row for them" | P2 | ok |
  | constant comment | "cannot see their install state at all" | refuted for 4/11 by P4/P5 | F2 |
  | inline comment | "no CLI row by construction" | P2 | ok |
  | test docstring | "only the @builtin suffix is exempt; a lookalike is not" | the name-side lookalike is pinned; the marketplace-side one is not | F5 |
  | commit msg | "live plugin-health rc=1 -> rc=0" | P7 two-module arm (`code 1` → `0`) | ok |
  | commit msg | "reverting the exclusion fails both new tests" | P8 M1: 2 failed | ok |
  | commit msg | "control test keeps a lookalike `builtin@market` reported as missing" | P8 M2 red | ok |

## Probes run (each with its control)

- **P1 — refs.** `rev-parse 5dfb7eef` matches the worktree HEAD. `merge-base 5dfb7eef origin/main` = `9f286354`.
- **P2 — premise (0 `@builtin` rows).** `claude plugin list --json` (2.1.287) returned 285 rows, 0
  ending `@builtin`. `--available` also had 0 `@builtin` ids. **Control:** the same probe shape found the
  `@skills-dir` rows (`install-doctor@skills-dir`, `plugin-health@skills-dir`). CONFIRMED.
- **P3 — the built-in registry in the binary** (`~/.local/share/claude/versions/2.1.287`, mmap scan).
  `ove()` registers 11 names via `rpe(...)`: sec-default, agents-md, telemetry,
  plugin-authoring, mods-guide, tips, mermaid, responsive-mode, diff, you-should-know and claude-test.
  Some registrations are gated on `CLAUDE_CODE_ENTRYPOINT` (`local-agent` / `remote*`).
  `.claude/types/claude-code.d.ts:6193` confirms the `<name>@builtin` provenance for bundled plugins.
  The vendor predicate `jSn` is at offset 179464332.
- **P4 — is a nonexistent built-in detectable?** `claude plugin details cc-plugin-you-should-know@builtin`
  → rc=0. `claude plugin details vqhtrxk-absent@builtin` (fresh absent name) → rc=1 "not found".
- **P5 — is `details` reliable across all 11?** No. rc=0 for agents-md, telemetry,
  plugin-authoring and you-should-know. rc=1 for sec-default, mods-guide, tips, mermaid,
  responsive-mode, diff and claude-test, both with ambient `CLAUDE_CODE_ENTRYPOINT=cli` and with it unset.
  A `details`-based existence check would raise false DRIFT on 7/11. This vindicates the exemption
  design, not the F2 wording.
- **P6 — hook vs report keys.** `declared_not_effective` occurs 3× in the `.ts` and 0× in
  `plugin_health.py` at `ed656dd4`, `9f286354` and `5dfb7eef`. Issue search for it → 0. Must-hit control
  `declared_not_installed` → 1 (#1061). Fresh absent control → 0.
- **P7 — the two-module live arm.** BASE and HEAD `plugin_health.py` were loaded side by side
  (`importlib`, `__file__` checked: the scratchpad copies, not the installed package). Both ran `evaluate`
  on ONE live `read_rows()` payload (OK, 285 rows) with real user and project settings.
  - For both the dotfiles checkout and this worktree as `project_root`, BASE gave `code 1`,
    `dni=['cc-plugin-you-should-know@builtin']`, and HEAD gave `code 0`, `dni=[]`,
    `builtin_unobservable=['cc-plugin-you-should-know@builtin']`. `ddh`/`ind` were empty on both arms.
  - Adding the typo `cc-plugin-you-shuold-know@builtin`: BASE `code 1`, HEAD `code 0` (F1).
  - Declared-set parity: `_declared_from_settings` agreed across both modules.
- **P8 — mutation matrix.** Run in a scratch `git worktree add --detach` at `5dfb7eef`, against
  `tests/test_plugin_health.py` (16 tests). Each mutation was asserted unique (count==1) and applied, and
  the file was restored byte-equal.

  | Row | Mutation | Result |
  |---|---|---|
  | M0 | control (pristine) | 16 passed, rc=0 |
  | M1 | revert the exclusion | 2 failed (red) |
  | M2 | `"builtin" in plugin_id` substring | 1 failed (red) |
  | **M3** | **`BUILTIN_SUFFIX = "builtin"`** | **16 passed (SURVIVES → F5)** |
  | M4 | count `builtin_unobservable` as drift | 1 failed (red) |
  | M5 | drop the field from the report | 2 failed (red) |
  | M6 | exempt every declared id | 3 failed (red) |

- **P9 — static.** `ruff check` rc=0, `ruff format --check` rc=0, `ty check` rc=0 and `typos` rc=0 on both changed files.
- **P10 — contracts.** `uv run --project python dotfiles-setup verify run` from the scratch worktree:
  the module resolved to the worktree path (checked), and the run reported `166 passed, 0 failed, 4 skipped`, rc=0.
- **P11 — malformed ids.** HEAD `evaluate(['@builtin'])` and `evaluate(['a@b@builtin'])` both return
  `code 0`, and BASE returns `code 1` for both. Control: `x@notbuiltin` is `code 1` on both.
- **P12 — contract binding.** `grep -c` in `suites.toml`: `test_declared_builtin_is_unobservable_not_missing`
  → 0 and `test_builtin_exemption_does_not_hide` → 0. Must-hit control `test_firecrawl_regression_guard_silence` → 1.
- **Cleared — could a third-party marketplace be named `builtin`?** No. `claude plugin validate` on a
  scratch marketplace named `builtin` returned rc=1, "Marketplace name "builtin" is reserved for built-in
  plugins". Control `qwmk-ctl` returned rc=0. So the suffix cannot collide with a real marketplace. (The documented
  reserved list at `$CC/plugin-marketplaces.md:166` omits `builtin`; the binary enforces it anyway.)

The scratch worktree was removed (`git worktree remove`, rc=0). The caller's worktree is unchanged apart
from this report: HEAD `5dfb7eef`, and the only untracked file is this one.

## Recommendations (none blocking)

1. F2/F3/F4: narrow the constant comment, fix `evaluate()`'s return line, and update SKILL.md
   "Reading the report" to cover the `@builtin` carve-out and `builtin_unobservable`, in the same follow-up.
2. F5/F6: optionally adopt the vendor predicate shape (exactly one `@`, non-empty name). Add an
   `x@notbuiltin` lookalike to the control test so M3 goes red.
3. T1: file a ticket. The plugin-health SessionStart hook reads keys the report has never emitted
   (since #1061), so DRIFT is invisible at session start. The test shape is a TS-side read of a real
   `plugin-health` JSON. #1042 (no TypeScript test tier) is why nothing caught it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue search for an existing hook-schema ticket (none; #1061 is the must-hit control).
