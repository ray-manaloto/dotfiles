# Cold review — graphify currency/upgrade restructure

**Diff under review:** `657a59dccb577fbc69a02d4e089f2429bea01377..a36b59847dd73ad847565063d6e0bc3cf7192dcd`
(branch `fix/graphify-update-skill-version-sync`, 35 files, +1408 / -1122)

`a36b5984` is also branch HEAD at review time. Authored by a codex (GPT-5.6 Sol)
lane; this is the required cross-family (Claude/Opus) cold lens.

Status: COMPLETE. 8 findings (4 HIGH, 3 MEDIUM, 1 LOW). Every invariant the
caller named was checked; five hold cleanly, three do not (F1 zero-token gate,
F3 lock-move path, F4 PATH axis).

## Findings

### F1 (HIGH) — the "zero LLM tokens" boundary has no machine gate; the argv-allowlist test is tautological

`tests/test_graphify_currency.py:405-442`
(`test_currency_subprocess_commands_are_allowlisted`) calls exactly four
functions with an injected `run=fake_run`, then asserts
`{args[0] for args in calls} == {"mise", "gh", "uv", "graphify"}`. The
allowlist is **derived from the four calls the test itself makes**, not
scanned over the module — so any token-spending subprocess added to a
function the test does not call is invisible.

**Mutation (proving arm), run in the `git archive` + `PYTHONPATH` harness:**
inserted two real LLM-CLI calls into `graphify_currency.graphify_upgrade_main`
immediately before the rebuild dispatch —

```python
subprocess.run(["agy", "--print", "--output-format", "text"], ...)
subprocess.run(["codex", "exec", "--ephemeral", "-s", "read-only", "-"], ...)
```

→ **22 passed, rc=0** (unchanged from the 22-passed baseline).

**Control arm (proving the harness discriminates):** restored the file and
instead swapped the update/rebuild order in the same function →
**2 failed, 20 passed, rc=1**
(`test_upgrade_stops_before_rebuild_when_update_fails`,
`test_upgrade_runs_update_before_rebuild`). So the harness is live and the
green result above is a real blind spot, not a broken probe.

Nothing else covers it. `git grep` over `python/verification/suites.toml` and
`hk.pkl` returns **zero** hits for `llm`, and the only contract naming the
module (`workflow.graphify-currency-wiring`, `suites.toml:1493-1538`) is a
`require_tokens` suite whose sole zero-token clause is a **markdown heading**:
`".claude/skills/graphify-currency/SKILL.md" = ["## Zero-token boundary"]`
(`suites.toml:1536`). A doc heading and a test that enumerates its own calls
are both checks that can only pass.

**It is worse than "derived": two of the four functions it calls are
test-only.** `git grep 'latest_version(\|path_binary_version('` over
`python/src/` returns **no production caller** for either
`graphify_currency.latest_version` (`:133`) or
`graphify_currency.path_binary_version` (`:177`) — production goes through the
private `_latest_probe` / `_path_binary_probe`. (The `claude_doctor.py` hits
are an unrelated same-named function.) So the allowlist is assembled from two
wrappers that exist only so this test can call them, plus `upgrade_lock` and
`release_notes_between`. It describes the test, not the module.

**Why it matters here specifically:** `graphify_upgrade_main` is the one
function the tests deliberately run with its children monkeypatched, so it is
the *least*-covered argv surface in the module and also the one a future
"just label the new nodes after rebuild" change would touch first.

**Suggested fix:** replace the derived assertion with a source-level scan —
parse `graphify_currency.py` (and `graphify_skill.py`, `graphify.py`) with
`ast`, collect every `subprocess.run`/`Popen` first-argument literal, and
assert the set is a subset of the allowlist. That form fails on a call the
test never invokes, which is the whole point.

### F2 (HIGH) — the release-notes receipt is written to a gitignored path, so it can never reach the PR the policy says a human reviews

`graphify_currency.py:31` — `RECEIPT_DIR = Path(".agent/graphify")`;
`write_release_receipt` (`:250-264`) writes
`.agent/graphify/release-notes-<high>.md`.

`.agent/` is gitignored. Verified live:

```
$ git check-ignore -v .agent/graphify/release-notes-0.9.66.md
.gitignore:124:.agent/	.agent/graphify/release-notes-0.9.66.md
```

The same diff rewrites `renovate.json`'s graphify packageRule description to
end with *"A human still reads the receipt before merging"* — but the receipt
is machine-local, absent from `git status`, absent from the PR diff, and swept
by `git clean -xdf`. A reviewer looking at the `python/uv.lock` hunk has **no
way to tell** a receipt-backed `mise run graphify-update` from a hand-run
`uv lock --upgrade-package graphifyy`, which writes the identical hunk.

This also contradicts `.claude/rules/agent-artifact-conventions.md`
("Promote anything a rule, eval, or later session will cite" — `renovate.json`
now cites it) and `.claude/rules/agent-report-persistence.md` rule 1's tracked
destination.

The fail-closed *ordering* is genuinely correct and tested
(`test_update_writes_receipt_before_native_uv_and_then_refreshes` asserts
`receipt.is_file()` inside the `uv lock` fake, and
`test_update_does_not_mutate_when_release_fetch_fails` asserts `uv` never
runs); the defect is purely that the artifact it produces is not durable or
reviewable.

**Suggested fix:** write the receipt under a tracked path
(`docs/research/kb/raw/graphify-release-notes-<high>.md` or
`docs/rules-evidence/`), or keep `.agent/` and delete the `renovate.json`
sentence that promises a reviewer will read it.

### F3 (HIGH) — removing the version literal from `pyproject.toml` moves graphifyy onto the one Renovate path its own packageRule cannot govern, and nothing detects a receipt-less lock move

`python/pyproject.toml:9` `"graphifyy[all]==0.9.65"` → `"graphifyy[all]"`;
`:55` `override-dependencies = ["graphifyy[all]==0.9.65"]` →
`["graphifyy[all]"]`.

With no version range left in any manifest, Renovate's uv/pep621 manager has
nothing to bump, so packageRule #4
(`{"matchPackageNames": ["graphifyy"], "automerge": false}`) has no dependency
update to attach to. The diff's own `renovate.json` text concedes this and
names the replacement: *"Renovate's enabled lockfile-maintenance … is the bot
path."* Confirmed live — `renovate.json` top level carries
`"lockFileMaintenance": {"enabled": true, "minimumReleaseAge": "1 hour"}`.

Consequences:

1. A lockfile-maintenance run regenerates `python/uv.lock`. Because graphifyy
   is now **unconstrained**, that re-resolution is free to move it to latest —
   with **no release-notes receipt**, which is exactly the state F2's ordering
   guarantee exists to prevent. The guarantee is enforced only *inside*
   `graphify_update_main`; every other route to the lock is ungated.
2. `graphify_currency.check` cannot see it. `_check_with_versions`
   (`:313-376`) compares locked/installed/latest/PATH/stamps/bytes and has
   **no receipt axis at all** — after a receipt-less bump, locked == latest, so
   `mise run graphify-check` prints `graphify currency current` and returns 0.
   Verified live on the current tree: `rc=0`, `graphifyy locked 0.9.65, latest
   0.9.65`, `graphify currency current`.
3. `UNVERIFIED (Renovate semantics):` whether a `matchPackageNames` rule binds
   a lockFileMaintenance branch is a Renovate-side question I did not settle
   against Renovate's docs. It does not change points 1-2, which hold either
   way: the receipt is not produced on that path and nothing checks for one.

**Suggested fix:** add a receipt axis to `check` — when the locked version's
`.agent/graphify/release-notes-<locked>.md` (or its tracked replacement, per
F2) is absent, report drift — and/or add
`{"matchUpdateTypes": ["lockFileMaintenance"], "automerge": false}` explicitly
rather than relying on rule #3 not matching.

### F4 (HIGH) — the `path-binary` axis cannot see the user-global binary it claims to check: it resolves the project venv's own `graphify`, so it can only pass

`graphify_currency.py:147-174` `_path_binary_probe` does
`shutil.which("graphify")`, then `run(["graphify", "--version"])`. Both run
inside `uv run --project python` (every caller does: `mise.toml:824`
`[tasks.graphify-check]` and `mise.toml:686` `[tasks.doctor]` are both
`uv run --project python dotfiles-setup …`), and `uv run` prepends the project
venv's `bin` to `PATH`.

**Measured, both arms:**

```
# inside `uv run --project python`
shutil.which('graphify') -> /Users/…/dotfiles/python/.venv/bin/graphify
PATH[0]                  -> /Users/…/dotfiles/python/.venv/bin
DOTFILES_AMBIENT_PATH set -> False

# ambient shell
$ which -a graphify
/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.65/bin/graphify
/Users/rmanaloto/.local/share/mise/shims/graphify
/Users/rmanaloto/.local/bin/graphify
```

Two different binaries. The probe never reads the user-global one. Because
`graphifyy[all]` is a project dependency, its console script is *always* in the
venv, so `shutil.which` always hits the venv first — which means the reported
"PATH graphify" version is the **installed** version, which after `uv sync`
equals the **locked** version by construction. The comparison
`locked != path_probe.value` (`:358-368`) is therefore a check that can only
pass, and the `absent=True` branch (`:150`) is unreachable under the mise
tasks.

(The two happen to agree at 0.9.65 today, so a version comparison cannot
discriminate. The **path identity** is the discriminating evidence, and it is
unambiguous.)

**This is not a new bug — but the diff newly makes it load-bearing.** The
deleted `doctor._graphify_path_binary_findings` had the same `shutil.which`,
guarded by an explicit `path_binary_must_match_pin = true` opt-in. This diff
**deletes that opt-in from `doctor.toml`** and then asserts the check as the
guarantee for the seam in two places:

- `pin-parity.toml:52` — "The shared currency checker covers installed/latest/
  **PATH** drift."
- `.claude/rules/graphify-first.md` (eager) — "the user-global pin remains
  outside that registry by design; the shared `graphify-check`/doctor checker
  compares it with the lock and names the user-global mise fix when it drifts."

Neither is true. And the drift they promise to catch is **the diff's own
motivating incident** — `pin-parity.toml:47-49`: "On 2026-09-21 the user-global
PATH binary was graphify 0.9.65 while the repo still pinned 0.9.61, and no
machine gate noticed."

**This repo already solved this exact class and wrote a contract about it.**
`python/src/dotfiles_setup/path_drift.py:87` defines
`AMBIENT_PATH_ENV = "DOTFILES_AMBIENT_PATH"`, and `suites.toml:2510`
(`#596`) states the principle verbatim: `mise exec` and `mise run <task>`
"both REPLACE the stale install dir in PATH before the child starts … so a
preflight wired into `mise run lint` observes a repaired PATH and **can only
ever report clean**". The SessionStart hook captures the ambient PATH for
precisely this reason (`.claude/settings.json:138`
`DOTFILES_AMBIENT_PATH="$PATH" mise -C …`). `git grep DOTFILES_AMBIENT_PATH`
returns **0 hits** in `graphify_currency.py`.

**Suggested fix:** resolve the binary against `DOTFILES_AMBIENT_PATH` (reuse
`path_drift.resolve_ambient_path`, including its `Provenance.BLIND` branch, so
an uncaptured PATH is reported as a finding rather than a pass), and invoke the
**resolved path** (`[binary, "--version"]`) rather than the bare name — the
current code computes `binary` and then discards it, so the two can disagree.

### F5 (MEDIUM) — the SessionStart doctor now makes a 30s-timeout network call and will nag every session within hours of a graphify release

`doctor.py:1178` — `check_graphify_skill_surface` replaced its local stamp
comparison with
`findings.extend(drift.detail for drift in graphify_currency_check(setup.repo_root))`.

`graphify_currency.check` → `_check_with_versions` → `_latest_probe`, which
shells out to `mise latest pipx:graphifyy` with
`_LATEST_TIMEOUT_SECONDS = 30` (`graphify_currency.py:34, 109-130`).

The doctor is wired to SessionStart —
`.claude/settings.json:138`:
`… DOTFILES_AMBIENT_PATH="$PATH" mise -C "${CLAUDE_PROJECT_DIR:-.}" run doctor` —
and `.claude/CLAUDE.md:` states it "is silent when healthy". Two new
behaviours follow:

- **Offline / slow-network sessions get a finding**, not silence: a failed
  probe yields `Drift("lock-behind-latest", "UNVERIFIABLE: …")`
  (`:328-334`), which the doctor now prints. Correct per the fail-closed
  invariant for `graphify check`, but the doctor's contract is different — it
  is the always-on, silent-when-healthy surface.
- **A healthy repo goes noisy ~2× per day.** `renovate.json`'s own graphify
  rule records that graphifyy "ships ~2x/day as PATCH releases", and
  `lock-behind-latest` fires the moment latest > locked. Under a deliberate
  review-before-merge policy the lock is *expected* to trail latest, so this
  is a standing finding on a surface designed to stay quiet — the classic way
  a silent-when-healthy check stops being read.

The PATH-binary probe (`graphify --version`, 10s) is not new to the doctor;
the network probe is.

**Suggested fix:** split the axes — keep stamp/skill-bytes/installed-vs-locked
in the doctor, and leave the network-dependent `lock-behind-latest` to
`mise run graphify-check`, which is the operator-invoked surface where a
nonzero rc is the point.

### F6 (MEDIUM) — ten deleted doctor tests covered probe-failure branches that the new module reproduces and nobody tests

`tests/test_doctor.py` lost, among others:
`test_graphify_skill_surface_flags_a_version_timeout`,
`…_flags_a_version_spawn_error`, `…_flags_a_nonzero_version_exit`,
`…_flags_malformed_version_output`, `…_flags_missing_package_metadata`,
`…_flags_a_missing_stamp`, `…_accepts_a_matching_path_binary`,
`…_flags_a_drifted_path_binary`. They are replaced by a single
`test_graphify_skill_surface_delegates_currency_checks` (`:1130-1145`), which
correctly binds the delegation but asserts nothing about the probe branches.

The branches still exist, now in `graphify_currency.py`:
`_latest_probe`'s `OSError`/`TimeoutExpired` (`:118-119`), empty stdout
(`:124-125`), `InvalidVersion` (`:127-129`); `_path_binary_probe`'s
`OSError`/`TimeoutExpired` (`:159-160`), nonzero rc (`:163-167`), no-match
(`:168-169`), `InvalidVersion` (`:170-173`); `_json_documents`'s
`JSONDecodeError` (`:189-191`); `_skill_drifts`'s five-exception guard
(`:295-302`); `locked_version`'s `OSError`/`TOMLDecodeError` (`:77-79`) and
`InvalidVersion` (`:96-100`).

`tests/test_graphify_currency.py` contains **zero** matches for `Timeout`,
`OSError`, `TimeoutExpired`, `empty stdout`, `invalid version`, `no usable
version`, or `invalid JSON` (counted per-term). Only the nonzero-rc arms are
covered (`test_latest_version_returns_none_on_nonzero`,
`test_upgrade_lock_stops_before_sync_when_lock_fails`).

These are the arms that decide whether an unreachable network reads as
"UNVERIFIABLE" or as "current" — the exact property the fail-closed invariant
names. A regression in any of them is silent today.

### F7 (MEDIUM) — `do-not.md` #8's rewrite drops the `graphify <platform> install` warning and replaces it with an "agents is skill-only" claim that is false for that form

`.claude/rules/do-not.md:34-44` (eager rule). Verified against the **installed**
graphify 0.9.65 (`graphify/install.py`, read via `inspect.getsource`):

| New claim | Verdict | Evidence |
|---|---|---|
| `--project` + `claude` writes root `CLAUDE.md` + settings hooks | **TRUE** | `claude_install()` writes `(project_dir or Path(".")) / "CLAUDE.md"` then `_install_claude_hook(...)`; `_project_install` calls it for `claude`/`windows` |
| `--project` + `codex` writes root `AGENTS.md` + `.codex/hooks.json` | **TRUE** | `_project_install` → `_agents_install(project_dir, "codex", project=True)` → writes `project_dir/"AGENTS.md"` (`:1552`) and, at `:1568-1569`, `if platform == "codex": _install_codex_hook(...)` |
| "The vendor `agents` platform is skill-only" | **TRUE only for `install --platform agents`; FALSE for `graphify agents install`** | `_project_install`'s `("copilot","pi","kimi","agents")` branch is skill-only — but `_agents_platform_install` (`:1609-1620`), which is what `graphify agents install` dispatches to, is `_copy_skill_file("agents")` **+ `_agents_install(project_dir or Path("."), "agents")`**, i.e. it writes `./AGENTS.md`. Its own docstring draws the line: "The bare `graphify install --platform agents` path stays skill-only (via install())" |

The text this replaced warned about exactly that subcommand form — "*Run any
`graphify <platform> install` in a throwaway directory outside this repo, never
here*" — because root `AGENTS.md` is at 200/200 lines under `md_size_budget`.
The rewrite narrows the subject to `graphify install --project` and then states
the skill-only property without its form qualifier, so a reader who runs
`graphify agents install` here is not warned. The surviving "Run installer
probes only in a throwaway directory" sentence still protects in practice, but
the specific hazard is no longer named.

**Suggested fix:** qualify it — "`graphify install --platform agents` is
skill-only; the separate `graphify agents install` subcommand also appends root
`AGENTS.md`."

### F8 (LOW) — the currency SKILL.md states the PATH probe and the rebuild executable are different binaries; they are the same one

`.claude/skills/graphify-currency/SKILL.md:77-79` (mirrored identically at
`.agents/skills/graphify-currency/SKILL.md`):

> The only deliberate PATH probe is `graphify --version` inside
> `graphify-check`; rebuild resolves the project-locked executable through
> `uv run --project python`.

Both resolve to `python/.venv/bin/graphify` — see F4's measurement. The
sentence reads as a contrast between a host binary and a project binary; there
is no such contrast. Fixing F4 makes this sentence true; leaving F4 makes it
the line a future reader will trust.

## Clean report

Verified live on the checked-out tree at `a36b5984` (each command redirected
to a file with its own `rc=`, never piped):

| Check | Result |
|---|---|
| `mise run graphify-check` | `rc=0` — `graphifyy locked 0.9.65, latest 0.9.65`, `graphify currency current` |
| `mise run graphify-health` | `rc=3` — `stale (runtime=0.9.65) … rebuild with` **`mise run graphify-rebuild`** (message correctly retargeted off `graphify-update`) |
| `dotfiles-setup pin-parity` | `rc=0`, `5 tool(s), every site agrees`. graphify row: `python/uv.lock: 0.9.65` + the three stamps, all `0.9.65`. The lock site reports **one** version, so the multiline pattern matches exactly once (contrast the `hk` row, which prints `1.57.0, 1.57.0, 1.57.0` for a 3-match site) |
| `dotfiles-setup skills-mirror --check` | `rc=0`, `.agents/skills matches the generator` |
| strict `per_path_tokens` replay over the whole `suites.toml` | **1296 tokens scanned, 0 failures** — the rewritten `workflow.graphify-currency-wiring` suite's tokens all resolve, and `tests/test_graphify_skill.py` (still present, 21 KB) still carries its required token |
| `pytest tests/test_graphify_currency.py` (archive harness) | 22 passed, rc=0 baseline |
| `pytest tests/ -q` (full suite, working tree) | **3733 passed, 11 deselected, rc=0** in 262s — no collateral damage from the `test_doctor.py` rewrite or the `test_graphify_skill.py`/`skills_mirror.py` deletions (`rc=` read from the redirected log, not the task notification) |
| `ruff check python/ tests/` | `All checks passed!`, rc=0 — no import left orphaned by the `doctor.py` deletions |
| `ty check` (graphify_currency, graphify, doctor, main) | `All checks passed!`, rc=0 |

Invariant-by-invariant:

- **Ordering enforced in Python, not mise `depends`** — ✅.
  `graphify_upgrade_main` (`graphify_currency.py:455-461`) calls
  `graphify_update_main` then, only on `update_rc == 0`,
  `graphify.graphify_rebuild_main`. `mise.toml [tasks.graphify-upgrade]` uses
  `run = 'uv run --project python dotfiles-setup graphify upgrade'` with **no
  `depends` key**, and carries the comment naming why. Mutation-proven: the
  order swap turns 2 tests red (above).
- **`mise latest` stdout only** — ✅. `_latest_probe` reads
  `result.stdout.strip()` and ignores stderr;
  `test_latest_version_reads_stdout_only` feeds a stderr warning and requires
  the stdout value.
- **Failed probe never reported as "current"** — ✅ for `graphify check`.
  `_require_latest` raises `latest UNVERIFIABLE: …`; a `gh api` failure raises
  before `upgrade_lock` is reached
  (`test_update_does_not_mutate_when_release_fetch_fails` asserts the lock is
  unchanged, `.agent/graphify` never created, and `uv` never invoked);
  `release_notes_between` additionally raises when the target release row is
  absent from the API response, so a PyPI release without a GitHub release
  blocks the bump.
- **No `graphify.llm` import, no labeling/dedup subprocess, no
  `agy`/`codex`/`claude` in the current source** — ✅ as written. `git grep`
  for `graphify.llm` in the module returns nothing; the four shell-outs are
  `mise latest`, `gh api`, `uv lock`/`uv sync`, `graphify --version`. **But the
  test that is supposed to bind this does not** — see F1.
- **`.agents/skills/graphify/SKILL.md`** — ✅.
  `git diff main..a36b5984 -- .agents/skills/graphify/SKILL.md` is **empty**
  (byte-identical to `main`), it contains `DELIBERATE STUB`, and the directory
  holds only `SKILL.md` + `.graphify_version` — **no `references/`**.
- **`python/pyproject.toml` has no graphify version literal; `uv.lock` is the
  single pin; `pin-parity.toml` sites each match exactly once; health reads the
  locked version** — ✅ mechanically (see the pin-parity row above, and
  `graphify.py:325-343` `_locked_version_problem`, which replaced the deleted
  `EXPECTED_GRAPHIFY_VERSION` constant; `git grep` finds no live references to
  that name outside prior review reports). The *policy* consequence of the
  literal's removal is F3.
- **`hk.pkl` diff is comment-only** — ✅. Every changed line in
  `git diff 657a59dc..a36b5984 -- hk.pkl` is a `//` comment; a region diff of
  the `graphify_skill_surface` step body against `657a59dc` returns
  `IDENTICAL`.
- **`graphify-skill-install` skill removed from both trees** — ✅.
  `git diff --summary` shows `delete mode` for both
  `.claude/skills/graphify-skill-install/SKILL.md` and
  `.agents/skills/graphify-skill-install/SKILL.md`; neither directory exists,
  nor does a `.codex/` counterpart; its `PER_FILE` entry and both prose
  paragraphs are removed from `skills_mirror.py`, and the mirror check passes.

Two correctness details worth crediting, both checked against primary sources
rather than the diff's prose:

- **`python/pyproject.toml:52`'s corrected kb-setup figure is right.** The
  comment moved from "pins graphifyy 0.9.42" to "0.9.57" with **no change to
  the pinned git rev**, which reads like an invented edit. It is not:
  `git show e8fe42ae208fbae227e733d38356416223d83ba7:pyproject.toml` in the
  sibling knowledge-base clone declares `"graphifyy[all]==0.9.57"`. The old
  figure was the stale one.
- **`.claude/skills/graphify-currency/SKILL.md:72-75`'s `graphify.llm` line
  citation is accurate.** The installed 0.9.65 `graphify/llm.py` is 3544 lines;
  `:3513` is `if not backend and _claude_cli_available():` and `:3521` is
  `backend = "claude-cli"` — exactly the silent escalation the skill warns
  about, at the line it names. (It will rot on the next bump like any line
  citation, but it is true today.)

I also considered and **dismissed** one hypothesis: that `uv sync` inside
`graphify update` could leave the same process holding a stale `graphify`
module for the subsequent skill refresh. It cannot —
`graphify_skill.py:42`'s `from graphify import install as _graphify_install` is
**function-local**, so the first import happens inside `_refresh_skills`, after
`upgrade_lock` has completed.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository under review.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — read `pyproject.toml` at the pinned `kb-setup` rev to verify the graphifyy figure in F-adjacent note.
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — named as `GITHUB_REPO` for the release-notes fetch; its installed package source (`graphify/install.py`, `graphify/llm.py`) was read locally from the project venv, not fetched.
