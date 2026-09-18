# codex SDLC specs — session dotfiles-20260917.000 (2026-09-17), verbatim

The four specs handed to `mise run sdlc-team` this session (runs `phase8-1183-safe-directory-20260917{,-r2,-respec1}` and `phase8-1171-harness-children-20260917{,-r2,-respec2}`), preserved verbatim per `.claude/rules/agent-report-persistence.md`. Lane outputs live in `.agent/sdlc-runs/<run>/output.md` (gitignored) and are summarised in `findings.md`; the resulting reviews are `cold-review-1183{,-r2}-2026-09-17.md` and `cold-review-1171-2026-09-17.md` beside this file.


---

## spec-1183.md

## Spec — #1183: make the workspace a git `safe.directory` in the devcontainer

### 1. Objective

Inside the devcontainer, git AND libgit2 consumers (hk, mise) must open
`/workspaces/<clone>` successfully from the FIRST second after a container
(re)create. Today Docker Desktop's virtiofs reports the bind-mount ROOT
directory as `0:0` for roughly five minutes after a re-create while the files
are `1000:1000`; git then exits 128 "detected dubious ownership" and libgit2
fails `Owner (-36)`. That has reddened `land`/`ship` gates five times and makes
the goal-history validator misreport a git failure as a deletion (#1173).
Failure scenario prevented: a healthy container failing smoke only because of
when the smoke ran.

When the condition does fire for any other reason, the smoke harness must name
it at the surface ("git cannot open the workspace"), before any tier runs, not
three tiers later as a generic "stale base?" hint.

### 2. Files

- `home/dot_gitconfig` (may become `home/dot_gitconfig.tmpl` — see Constraints)
- `scripts/devcontainer-smoke.sh`
- `python/src/dotfiles_setup/bash_budget.py` (only the `devcontainer-smoke.sh`
  allowance, if the script grows)
- `tests/` — a test binding the new stanza and the new probe (new or existing file)
- `.claude/rules/persistence-gate-retry.md`
- `docs/rules-evidence/persistence-gate-retry.md` (if the retired prose moves there)
- `docs/receipts/446.md` (dated correction only, lines ~121-124)
- `.devcontainer/AGENTS.md` (one line naming the mechanism, if it documents git/ownership)

### 3. Interfaces

- Resulting container `~/.gitconfig` contains a `[safe]` section whose
  `directory` equals the workspace folder the container mounts.
- Smoke probe: `git -C "${WORKSPACE_FOLDER}" rev-parse HEAD`, run BEFORE the
  tier-1 core is generated, failing loud with a message that contains the
  words `safe.directory` and the workspace path.

### 4. Constraints and invariants

- **Mechanism is PINNED by ruling** (Ray, 2026-09-17, recorded in
  `findings.md`): the chezmoi-managed global gitconfig, NOT `postStartCommand`,
  NOT the Dockerfile. Do not touch `.devcontainer/devcontainer.json` or
  `.devcontainer/Dockerfile`.
- Prefer a chezmoi built-in fact for the path over a literal, so a clone with a
  different basename still works (`workspaceFolder` is
  `/workspaces/${localWorkspaceFolderBasename}`). If you template the file,
  verify the rendered value in the container equals `/workspaces/dotfiles`; if
  no built-in yields it reliably, use the literal and say why in the commit
  body (`.claude/rules/use-tool-builtins.md`).
- Do NOT use `safe.directory = *`. Scope it to the workspace.
- The file is also the source for a Mac host that never applies chezmoi;
  nothing may break `chezmoi` read-only commands on darwin.
- The tier-1 CORE is python-generated and byte-identical with the CI no-mount
  smoke — the probe must NOT go into `dotfiles_setup.image` tier-1 generation;
  it is mount-dependent and belongs in the bash harness.
- `scripts/devcontainer-smoke.sh` is budgeted at 157 lines
  (`bash_budget.py`). Keep the probe minimal; any growth requires bumping that
  allowance with a one-line justification naming #1183.
- No `2>/dev/null`, no inline lint suppressions, `set -euo pipefail` semantics
  preserved; never `cmd | grep -q` under pipefail.
- Rule file: retire the sentence claiming the trigger "remains unattributed"
  and the "do not add it on this evidence" guidance; state the attributed
  cause (#1183, virtiofs mount-root ownership window) and the fix. Keep the
  retry-once table row but reclassify it as "should no longer occur; if it
  does, the stanza is missing — real defect". Respect the md size budget
  (move case history to `docs/rules-evidence/` rather than growing the rule).
- `docs/receipts/446.md`: do not rewrite the record; ADD a dated correction
  noting its container claim holds only outside the post-re-create window.
- Do not run `chezmoi apply/update` on the host. Do not run `mise run lint`,
  full pytest, or any devcontainer lifecycle command — the architect runs gates.
- Do not pipe any command into `tail`/`head`.

### 5. Verification (smallest bundle)

- `uv run --project python pytest tests/<the test file you touched> -x -q` → rc 0
- `uv run --project python dotfiles-setup bash-budget` → rc 0
- Fail arm: delete the `[safe]` stanza → the new test fails; restore.

Architect-run afterwards (outside the sandbox): lint, full pytest, verify,
lint-docs, `verify-local`, and the live arm — re-create the container and run
`git -C /workspaces/dotfiles rev-parse HEAD` inside the first minute.

### 6. Commit

COMMIT: caller

### 7. PREMISES

- L1 `home/dot_gitconfig` has no `[safe]` section — home/dot_gitconfig:1-23
- L2 `home/dot_gitconfig` is not excluded by any branch of `home/.chezmoiignore` — home/.chezmoiignore:1-56
- I1 chezmoi is applied from the workspace on every container create:
  `chezmoi init --apply --source="${WORKSPACE_FOLDER}" --no-tty --force` — .devcontainer/scripts/on-create.sh:41
- L3 tier-1 core is generated then eval'd, shared with the CI no-mount smoke — scripts/devcontainer-smoke.sh:21-35
- L4 smoke script allowance is 157 lines and the file is 157 lines — python/src/dotfiles_setup/bash_budget.py:88-92
- L5 `workspaceFolder` = `/workspaces/${localWorkspaceFolderBasename}` — .devcontainer/devcontainer.json:120
- L6 the rule says "The trigger remains unattributed. `safe.directory` is configured nowhere" — .claude/rules/persistence-gate-retry.md:83
- L7 receipt claims the bind mount never creates the condition — docs/receipts/446.md:121-124
- P1 MEASURED 2026-09-17 in the running container, fixture = a repo whose top
  DIR is `0:0` while `.git` and files are `1000:1000` (the #1183 shape):
  no safe.directory → `git rev-parse` rc=128 and `HK_FILE=/etc/hk/hk.pkl hk run
  pre-commit --all` rc=1 with `code=Owner (-36)`; after `git config --global
  --add safe.directory <repo>` → git rc=0, hk rc=0, zero owner messages. So the
  GLOBAL gitconfig is honoured by git and by hk's libgit2. A `mise run <task>`
  arm did not reproduce the failure in either arm, so mise is UNARMED here
  (A-row: it uses the same libgit2 ownership check hk does).
- P2 MEASURED same session: inside the container, with the source on-create
  uses, `chezmoi --source=/workspaces/dotfiles execute-template
  '{{ .chezmoi.workingTree }}'` → `/workspaces/dotfiles`
  (`.chezmoi.sourceDir` → `/workspaces/dotfiles/home`). WITHOUT `--source`
  chezmoi resolves `~/.local/share/chezmoi` instead — any check you write must
  pass the source explicitly. `chezmoi --source=… managed` lists `.gitconfig`,
  and the deployed `~/.gitconfig` is byte-identical to `home/dot_gitconfig`.
- A1 On the Mac host the template would render the host clone path; harmless
  because chezmoi apply is blocked on the host, but a darwin render must not error.

### 0. READ FIRST — you are ALREADY inside an `sdlc-team` run

You are the dispatcher of a run that `mise run sdlc-team` has already started.
Spawn your roster specialists with your NATIVE subagent spawning. NEVER run
`mise run sdlc-team`, never write an `SdlcTeamRequest` file, and do not follow
`.agents/skills/codex-sdlc-team/SKILL.md` or `.claude/skills/codex-sdlc-team/` —
those documents address an outside CALLER, not you. A previous attempt at this
exact task failed in 4 minutes by re-dispatching itself from inside the
sandbox (nested codex cannot start there). `mise run graphify-query` also
fails in your sandbox (uv cache) — do not retry it; read source directly.
Relevant specialists: config (chezmoi gitconfig, bash budget), python (tests),
documentation (rule, evidence, receipt).

---

## spec-1183-respec1.md

## Respec round 1 — #1183 (follows commit 86e0d3e on `fix/1183-safe-directory`)

### 0. READ FIRST — you are ALREADY inside an `sdlc-team` run

You are the dispatcher of a run `mise run sdlc-team` has already started. Spawn
roster specialists with your NATIVE subagent spawning. NEVER run
`mise run sdlc-team`, never write an `SdlcTeamRequest`, and do not follow
`.agents/skills/codex-sdlc-team/SKILL.md` — it addresses an outside caller.
`mise run graphify-query` fails in your sandbox; read source directly.
Relevant specialists: python (tests, pr.py), documentation (one evidence line).

### 1. Objective

A cold review of 86e0d3e confirmed that the tests guarding the fix cannot
detect the two ways it would really regress. Make them able to. What changed
from the previous spec: NO production behaviour changes — the template and the
smoke script are correct and must stay byte-identical.

Failure scenarios the tests must catch after this round:

a. `home/dot_gitconfig.tmpl` rendering `{{ .chezmoi.sourceDir }}` instead of
   `{{ .chezmoi.workingTree }}`. In production `.chezmoiroot` is `home`, so
   sourceDir is `<workspace>/home`, and a `safe.directory` naming that subdir
   does NOT clear the ownership error. Today's fixture is a bare directory,
   where both facts render the same string, so this mutation passes.
b. The rendered stanza failing to clear a REAL dubious-ownership refusal. Today
   the only failing-preflight test uses a not-a-repo directory, a different
   git 128. `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` reproduces the real condition
   with no root and no container.

And one gate gap: a follow-up PR touching only the template is currently
classified as non-devcontainer surface, so ship/land would skip the full local
verification for the file the container's validity now depends on.

### 2. Files

- `tests/test_safe_directory.py`
- `python/src/dotfiles_setup/pr.py` (SURFACE_PATTERNS only)
- `tests/test_pr.py` (only if an existing test enumerates or pins the surface set)
- `docs/rules-evidence/persistence-gate-retry.md` (line ~71 only)

### 3. Interfaces

- The render test's `--source` fixture mirrors production: a source dir
  containing a `.chezmoiroot` whose content is `home`, plus the `home/` subdir.
  It asserts the rendered `safe.directory` equals the fixture ROOT and is NOT
  the `home` subdir.
- A new end-to-end pair driving the real smoke script's preflight under
  `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` against a real committed fixture repo:
  - with `GIT_CONFIG_GLOBAL` pointing at a gitconfig with no `[safe]` entry →
    the preflight fails (rc 1, preflight marker present, Tier 1 never starts);
  - with `GIT_CONFIG_GLOBAL` pointing at the gitconfig RENDERED FROM THE REAL
    TEMPLATE for that fixture workspace → the preflight passes and the script
    proceeds to Tier 1 (reuse the existing uv-stub technique to stop it there).
  The second arm is what binds template → git behaviour; do not hand-write the
  gitconfig it uses.
- `SURFACE_PATTERNS` gains exactly one entry, `home/dot_gitconfig.tmpl`, with a
  comment naming #1183 and why (on-create renders it; the smoke preflight
  depends on it). Do NOT add `home/*` — that wider question is out of scope.

### 4. Constraints and invariants

- `home/dot_gitconfig.tmpl` and `scripts/devcontainer-smoke.sh` must be
  byte-identical to 86e0d3e when you finish (`git diff 86e0d3e -- <both>` empty).
- Tests use isolated state only: `tmp_path`, explicit `GIT_CONFIG_GLOBAL`, and
  also neutralise system config (`GIT_CONFIG_NOSYSTEM=1`) so a developer's or a
  runner's own `safe.directory = *` cannot make the failing arm pass. Never read
  or write the real `~/.gitconfig`.
- Every assertion must fail if the behaviour it guards is reverted. Prove (a)
  by temporarily mutating the template to `.chezmoi.sourceDir` and showing the
  render test fails, then restore from `git show 86e0d3e:home/dot_gitconfig.tmpl`
  (not `git checkout --`). Prove (b)'s passing arm by temporarily deleting the
  `[safe]` stanza and showing it fails, then restore the same way.
- New test files/functions need no new header; the file already carries
  `# Copyright (c) 2026 Raymond Manaloto` on line 1 — keep it first.
- ruff-clean, no inline suppressions, no `2>/dev/null`.
- `docs/rules-evidence/persistence-gate-retry.md`: the paragraph near line 71
  begins a line with `#1183`, which markdown reads as a malformed heading —
  reword so the line does not start with `#`. Nothing else in that file.
- Do not run `mise run lint`, full pytest, or any devcontainer/chezmoi-apply
  command. Do not pipe commands into `tail`/`head`.

### 5. Verification

- `uv run --project python pytest tests/test_safe_directory.py tests/test_pr.py -q` → rc 0
- the two mutation arms above, each reported with its real rc
- `git diff 86e0d3e -- home/dot_gitconfig.tmpl scripts/devcontainer-smoke.sh` → empty

### 6. Commit

COMMIT: caller

### 7. PREMISES

- P1 MEASURED this session on the host: a `--source` dir WITHOUT `.chezmoiroot`
  renders `.chezmoi.workingTree` and `.chezmoi.sourceDir` to the SAME path; a
  source WITH `.chezmoiroot` = `home` renders workingTree = `<root>` and
  sourceDir = `<root>/home`.
- L1 the render test builds its source with a bare `source.mkdir()` — tests/test_safe_directory.py:18-22
- L2 the failing-preflight test uses a non-git directory — tests/test_safe_directory.py:57-60
- L3 the template line is `directory = {{ .chezmoi.workingTree }}` — home/dot_gitconfig.tmpl:26
- L4 `SURFACE_PATTERNS` contains no `home/` entry — python/src/dotfiles_setup/pr.py:98-117
- L5 the preflight is `git -C "${WORKSPACE_FOLDER}" rev-parse HEAD >/dev/null` with git's stderr left visible — scripts/devcontainer-smoke.sh:20-24
- A1 `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` forces git's ownership check to fail
  for a repo the user owns (used the same way in docs/receipts/446.md:113-116);
  confirm it on the git version you run before relying on it, and report
  dissent if it does not.

---

## spec-1171.md

## Spec — #1171: session-orphans must be green on a healthy session

### 0. READ FIRST — you are ALREADY inside an `sdlc-team` run

You are the dispatcher of a run `mise run sdlc-team` has already started. Spawn
roster specialists with your NATIVE subagent spawning. NEVER run
`mise run sdlc-team`, never write an `SdlcTeamRequest`, and do not follow
`.agents/skills/codex-sdlc-team/SKILL.md` — it addresses an outside caller.
Relevant specialists: python (module + tests), documentation (two skills).
Your sandbox has no `ps`; do not try to run `mise run session-orphans` for
real — drive `build_plan`/`main` with constructed `reap.Process` tuples, as the
existing tests do.

### 1. Objective

`mise run session-orphans` is the handoff gate that blocks when anything other
than a reapable wait loop outlives the session. Today it exits 1 on EVERY
healthy session, so operators `--allow` by reflex — which is how a real orphan
will eventually slip through. Make a healthy session's dry run exit 0 WITHOUT
weakening what blocks.

Measured 2026-09-17 on a quiet session (root = the `claude` pid):
- `npm exec @modelcontextprotocol/server-pdf --stdio` — ppid = root
- `node /Users/<u>/.npm/_npx/<hash>/node_modules/.bin/mcp-pdf-server --stdio` — ppid = the npm row above
- `caffeinate -i -t 300` — ppid = root (its pid changes every ≤300 s, so a pid allowlist is inherently racy)
and, with one harness background wait loop running:
- the `zsh -c source …/shell-snapshots/snapshot-…` wrapper → already `WAIT-LOOP bounded` (correct)
- its child `/bin/sleep 5` (ppid = the wrapper) → `BLOCK OTHER` (the defect)

Failure scenarios to PREVENT while fixing that: a stray `codex exec`, a
`node`/`npm` process NOT parented by the harness, a `caffeinate` under some
shell, or a live `mise run ship` under a snapshot wrapper being waved through.
Those must all still BLOCK.

### 2. Files

- `python/src/dotfiles_setup/session_orphans.py`
- `tests/test_session_orphans.py`
- `.claude/skills/session-handoff/SKILL.md` and `.claude/skills/verify/SKILL.md`
  — only where they describe `--allow`-ing harness children; then regenerate
  the mirrors under `.agents/skills/` with the repo's mirror task IF your
  sandbox can run it; if it cannot, say so in a `SANDBOX:` line and leave the
  mirror to the architect.
- `python/verification/suites.toml` — only if an existing contract pins text
  you change.

### 3. Interfaces

- A typed, reviewable table of harness-child SHAPES in the module: each entry =
  a name, a command pattern, and a PARENT requirement. A process is `HARNESS`
  only when its command matches AND its parent is the session root or another
  `HARNESS` row (that is what admits the `node` server under the `npm exec`
  row and nothing else). Shapes to ship: MCP server launcher (`npm exec …`),
  MCP server process (`node … --stdio` under a HARNESS launcher), `caffeinate`.
  Keep patterns narrow and anchored; justify each in a comment.
- `OrphanPlan` gains a `harness` partition. `HARNESS` rows are rendered in the
  plan as their own section with the matched shape name, never block, and are
  NEVER signalled, with or without `--kill`.
- **CORRECTED after licensed dissent (round 1).** The previous text made EVERY
  descendant of a WAIT-LOOP row non-blocking, which contradicted the invariant
  that real work under a wrapper must block (a loop body can run real work:
  `while …; do mise run x; sleep 5; done`). Ancestry alone cannot establish
  ownership. Instead: a typed table of WAIT-LOOP-CHILD shapes, shipped with ONE
  entry — a narrowly anchored `sleep <duration>` (bare or absolute path, e.g.
  `/bin/sleep 5`; numeric duration with optional s/m/h suffix; nothing else on
  the line) whose DIRECT parent is a WAIT-LOOP row. Such a row is rendered under
  its loop (e.g. `WAIT-LOOP child`), never blocks, and — because
  `reap.Runtime.killer` is `os.kill` on individual pids with no process-group
  signalling (python/src/dotfiles_setup/reap.py:411) — MUST be included in the
  `--kill` selection together with its loop, or the sleep is orphaned to init
  when its parent dies. Every other descendant of a WAIT-LOOP row continues
  through HARNESS/OTHER classification and blocks if OTHER.
- Exit code contract unchanged: 1 iff a blocking OTHER remains or a reaped
  loop survived; 2 on the existing error paths.
- `--allow` keeps working for genuine OTHER rows.

### 4. Constraints and invariants

- Classification precedence must be explicit and tested: WAIT-LOOP >
  WAIT-LOOP child (typed shape + direct WAIT-LOOP parent) > HARNESS > OTHER. A process can land in exactly one partition.
- A HARNESS match must never be reachable by command text alone — the parent
  requirement is the security property. Test the negative for EVERY shape: same
  command, wrong parent → OTHER, rc 1.
- Do not add a rule that treats the whole subtree of a snapshot wrapper as
  harness-owned. A working subtree (e.g. `mise run ship` → uv → python → hk)
  under a wrapper must still BLOCK.
- The module docstring's sentence "a `zsh -c source ...snapshot...` wrapper is
  OTHER and is left to #1171" is stale (measured: it is WAIT-LOOP since #1180)
  — correct it.
- No bash, no inline lint suppressions, ruff/ty clean, Python 3.14. New test
  files need `# Copyright (c) 2026 Raymond Manaloto` on line 1 (ruff CPY001).
- Do not run `mise run lint`, full pytest, or pipe commands into `tail`/`head`.

### 5. Verification

- `uv run --project python pytest tests/test_session_orphans.py -q` → rc 0
- Fail arm (issue #1171): delete ONE shape entry → its fixture row flips to
  OTHER and `main` returns 1. Report the real rc, then restore from git.

### 6. Commit

COMMIT: caller

### 7. PREMISES

- L1 partitions today are `wait_loops`, `other`, `allowed_other`; blocking = other minus allowed — python/src/dotfiles_setup/session_orphans.py:34-49
- L2 wait-loop test = shell command AND `hook_guard.is_audit_wait_loop(mask_shell_syntax(cmd))` — python/src/dotfiles_setup/session_orphans.py:77-82
- L3 `--kill` builds a `reap.Selection` from `plan.wait_loops` only — python/src/dotfiles_setup/session_orphans.py:160-167
- L4 return is `1 if plan.blocking_other or survivors else 0` — python/src/dotfiles_setup/session_orphans.py:183
- I1 `reap.Process` carries `pid, ppid, age_s, state, command` — python/src/dotfiles_setup/reap.py:96-103
- L5 stale docstring sentence — python/src/dotfiles_setup/session_orphans.py:7-8
- P1 MEASURED 2026-09-17 (this session, real process table): the three harness
  rows and their parents as listed in the Objective; the wrapped-loop arm with
  the wrapper `WAIT-LOOP bounded` and `/bin/sleep 5` as `BLOCK OTHER`.
- L6 `Runtime.killer` defaults to `os.kill`; there is no `killpg`/`getpgid` anywhere in the module (grep: 0 hits) — python/src/dotfiles_setup/reap.py:411
- A1 Other MCP servers/harness helpers exist on other machines with different
  commands; this change ships only the measured shapes, and an unmatched one
  correctly stays OTHER until a reviewed entry is added.

### 8. Tests the correction requires (in addition to the above)

- wrapper WAIT-LOOP + `/bin/sleep 5` child → child is `WAIT-LOOP child`, rc 0 (with the harness rows present).
- SAME wrapper + a `mise run ship` child (and its own descendants) → those rows are OTHER, rc 1.
- `sleep 5` whose parent is NOT a WAIT-LOOP row → OTHER, rc 1.
- `sleep 5; rm -rf x`-style or `sleep` with non-duration args must not match the shape.
- `--kill`: the killer seam receives BOTH the loop pid and its sleep child pid, and NO HARNESS pid.

---

## spec-1171-respec2.md

## Respec round 2 — #1171 (uncommitted working tree on `feat/1171-session-orphans-harness-children`)

### 0. READ FIRST — you are ALREADY inside an `sdlc-team` run

Spawn roster specialists with your NATIVE subagent spawning. NEVER run
`mise run sdlc-team` or write an `SdlcTeamRequest`; do not follow
`.agents/skills/codex-sdlc-team/SKILL.md`. One specialist is enough: python.
The working tree already holds round 1's uncommitted implementation — build on
it, do not revert it. Your sandbox has no `ps`.

### 1. Objective

The live arm on a real process table found one defect the fixture-driven tests
could not: the MCP launcher row is still `BLOCK OTHER`, and therefore so is its
`node` child (whose parent must be HARNESS). Measured cause: `ps -o command=`
reports the launcher as

    'npm exec @modelcontextprotocol/server-pdf --stdio    '

— FOUR TRAILING SPACES (npm rewrites its process title and pads it). The shape
uses `fullmatch` with no tolerance for trailing whitespace. Everything else in
the live arm was correct (wrapper WAIT-LOOP + `sleep` child; `caffeinate`
HARNESS; a plain `sleep 70` under a non-loop wrapper still blocks).

Make a command's trailing whitespace irrelevant to shape matching — for ALL
shapes, harness and wait-loop-child alike — WITHOUT loosening anything else.

### 2. Files

- `python/src/dotfiles_setup/session_orphans.py`
- `tests/test_session_orphans.py`

### 3. Interfaces

No public shape changes. Matching must treat `cmd` and `cmd + "    "` identically.

### 4. Constraints and invariants

- Decide WHERE to normalise by reading the code: in the matcher here, not in
  `reap.snapshot`/`reap.Process` (other consumers print and compare the raw
  command; do not change `reap.py`). The rendered plan line may keep the raw
  command.
- Only TRAILING whitespace is forgiven. Leading whitespace, internal extra
  arguments, or a suffix like `--stdio; rm -rf x` / `--stdio extra` must still
  fail to match. Keep `fullmatch` semantics on the normalised string.
- The healthy-session fixture must use the MEASURED launcher string with its
  four trailing spaces, so the test fails if the tolerance is removed.
- ruff/ty clean, no inline suppressions; do not run lint/full pytest; no
  piping into `tail`/`head`.

### 5. Verification

- `uv run --project python pytest tests/test_session_orphans.py -q` → rc 0
- Fail arm: remove the normalisation → the padded-launcher test fails (report
  the real rc), then restore your change.

### 6. Commit

COMMIT: caller

### 7. PREMISES

- P1 MEASURED this session: `ps -o command= -p <npm pid>` → repr
  `'npm exec @modelcontextprotocol/server-pdf --stdio    \n'`; the live
  `mise run session-orphans` rendered that row and its `node` child as
  `BLOCK OTHER` while `caffeinate` rendered `HARNESS`.
- L1 harness shapes are matched with `shape.command_pattern.fullmatch(process.command)` —
  python/src/dotfiles_setup/session_orphans.py (working tree, `build_plan`)
- L2 the launcher pattern ends `--stdio$` — same file, `HARNESS_CHILD_SHAPES`
- L3 the server shape requires `process.ppid in harness_ids` — same file, `build_plan`

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the only repo read while writing these specs.
