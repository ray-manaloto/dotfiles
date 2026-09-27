# Codex Astra implementation report: hk v2 migration

Date: 2026-09-27. Spec: `docs/specs/hk-v2-migration-dotfiles.md`, rev 3,
ratified by Ray. Branch: `chore/hk-v2.3-migration`. Commit owner: caller;
all work remains uncommitted.

Status: STOPPED — licensed dissent. Rev 3's assertion that the postinstall
prose is not contract-bound is contradicted by
`python/verification/suites.toml:849`. See the stop evidence below.
Command logs and separate real exit-code files live under
`.agent/logs/hk-v2-migration-astra-2026-09-27/`.

## Intake and premises

- Read the prior sol lane report before other repository files. Its stopped
  backend-key command is corrected in rev 3 to the config key
  `editorconfig-checker`.
- R1 VERIFIED: initial branch is `chore/hk-v2.3-migration`; exactly 16 tracked
  files are modified, all in spec section 2. Control: no tracked modification
  outside that allowlist. Five pre-existing untracked report/spec files are
  preserved.
- R2 VERIFIED: initial `git diff --numstat` records root `mise.lock` 0/59,
  shared `.config/mise/mise.lock` 0/49, image `.devcontainer/mise-system.lock`
  0/34 (added/deleted). The other changes match the prior report.
- R3 VERIFIED: corrected config-key invocation returned rc=0, restored
  editorconfig-checker 4.0.2 with 11 platform entries, and passed the wrapper's
  coverage check. Evidence: `lock-host.log` and `lock-host.rc` (0).
- R4 VERIFIED: `mise.toml:15` pins editorconfig-checker 4.0.2.
- R5 VERIFIED executable parity and section 5 step 10 control;
  `shared.toml:37` reads `hk = "2.3.0"`. Pin-parity passed at 2.3.0,
  failed with the temporary 1.57.0 mutation, and passed after byte-for-byte
  restoration. See the step 10 rc files.
- R6 VERIFIED executable arms: `mise which editorconfig-checker` resolves
  `/Users/rmanaloto/.local/share/mise/installs/editorconfig-checker/4.0.2/editorconfig-checker`
  (rc=0), and `hk validate` returns rc=0. hk reports 2.3.0.
- R7 VERIFIED both arms: audit line 9 initially recorded hk 1.57.0;
  `mise run hk-audit` returned rc=0 (`hk-audit.rc`) and line 9 now records
  hk 2.3.0. Available builtins changed from 152 to 160. Typos passed in the
  lint run, so no typos.toml entry was needed or added.
- R8 VERIFIED: focused parser/isolation file returned rc=0, 260 passed in
  2.62s, including the contaminated-config failure control and passing fixture
  arm. Evidence: `R8-parser-tests.log` and `R8-parser-tests.rc` (0).
- R9 VERIFIED: the requested inherited-variable probe printed SET before
  `unset HK_PKL_BACKEND`, ABSENT after. The initial read-only shells used
  their default login mode; their startup did not alter the measured 16-file
  state or the deleted blocks. All subsequent shells are non-login and start
  with the unset command. The presence probe necessarily precedes unset.
- R10 VERIFIED: running container observed: `be08239eeebb`,
  `dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233`, up 54 minutes.
  `mise run lock-shared -- "hk"` returned rc=0 (`lock-shared.rc`) through
  that container. `mise run up` was unnecessary.

## Source review

Graphify health and query both returned rc=3: graph built at `9f5bd67a`, HEAD
`453aa39b`, 12 changed corpus files. Source fallback follows the repository
rule; rebuilding the graph is outside this migration's allowlist.

Reviewed the existing diff for the pin/import/minimum versions, postinstall,
CI defense-in-depth prose, Renovate group, parser flag tables, smoke assertion,
and autouse Git isolation fixture and control test. Source confirms the audit
is generated, not hand-authored. No retained source-code edits were added in
this lane: the one builtin-fixture experiment was removed after failing.

The requested report serves as the incremental findings record, rather than
editing root findings.md outside the explicit file allowlist.

## Verification ledger

| Section 5 step | Command / measurement | Result |
|---|---|---|
| 1 | mise install; hk --version; mise which editorconfig-checker | rc=0 each (`01-install.rc`, `01-hk-version.rc`, `01-ec-path.rc`); hk 2.3.0, ec 4.0.2 |
| 2 | mise run pin-parity | rc=0 (`02-pin-parity-initial.rc`); all five tools agree |
| 3 | hk validate | rc=0 (`03-hk-validate.rc`) |
| 4 | mise run lint | rc=1 (`04-lint-initial.rc`): contract token, ruff, and ruff-format failures |
| 5 | mise run fmt; editorconfig rewrite inventory | NOT RUN — licensed-dissent stop |
| 5b | scratch staged whitespace defect; cached/unstaged diffs | NOT RUN — licensed-dissent stop; no staging conclusion |
| 6 | uv run --project python pytest tests/ -x -q | NOT RUN — licensed-dissent stop; focused 260-test file passed separately |
| 7 | mise run verify | NOT RUN — licensed-dissent stop |
| 8 | mise run pin-actions; mise run lint-docs | NOT RUN — licensed-dissent stop |
| 9 | hk test | rc=1 (`09-hk-test.rc`): 9 builtin fixtures excluded by repository globs; fixture experiment also rc=1 (`09-hk-test-fixtures.rc`) and removed |
| 10 | parity fails at shared hk 1.57.0, passes after restoration | rc=1 control / rc=0 restored (`10-pin-control.rc`, `10-pin-restored.rc`) |
| 11 | inspect hk install references in mise.toml | rc=0 (`11-postinstall.rc`); only line 177 operator comment, postinstall remains mise reshim |
| 12 | real Git isolation test and failing hook control | rc=0 within `R8-parser-tests.rc`; both assertions passed |

Editorconfig-checker selected version: **4.0.2**. Live
`mise ls-remote editorconfig-checker` returned rc=0 (`ec-versions.rc`), with
4.0.0, 4.0.1, 4.0.2 as the listed 4.x releases. Host lock regenerated at 4.0.2.
Files rewritten by editorconfig-checker under fmt: **not measured; fmt was
not run**. This is not evidence that ec 4 would rewrite zero files.
Step 5b staging behavior: **not measured**; neither cached nor unstaged scratch
diff statistics exist. AGENTS.md remains unchanged (net growth 0 characters).

All executed section 5 commands have the real rc recorded in the named files.
No rc is fabricated for an unrun command. Section 5 step 12 was exercised as
part of the focused test file, not as a separate full-suite run. Its native
Git control asserts nonzero and its isolated arm asserts zero; the passing
pytest run proves those assertions held but does not print the control's
exact nonzero value.

## Diagnostics to retain

Live `hk --help` and `hk run --help` value-taking flags match the revised
tables. The installed 2.3.0 usage specification at line 109 retains hidden
`--hkrc <PATH>` only for migration guidance. Added flags remain exactly
`--junit-xml` (run) and `--hkrc` (global); no other new value-taking flags found.

Shared locking and the host install completed with rc=0. They briefly
overlapped in execution; subsequent lock/installation operations are serialized.
The generated shared hk block now says 2.3.0 with backend
`packslip:github.com/jdx/hk` and no platform table. The wrapper reports coverage
OK, but that alone is not evidence for the backend transition: its regression
check compares only tools that have platform tables on both sides. This native
backend result was investigated below; no checksums were hand-written.

Backend investigation: upstream's [registry documentation](https://mise.jdx.dev/registry)
explicitly selects Aqua for hk versions before 1.58.1 and Packslip thereafter.
Its [Packslip documentation](https://mise.jdx.dev/dev-tools/backends/packslip.html)
says `mise lock` resolves the version without installing, while artifact
commitments require installation. Thus the generated backend change follows
native resolution; preserving the old Aqua backend would be a new policy
choice, not a checksum repair. The already-installed host hk reports 2.3.0.

Image lock regeneration completed rc=0 (`lock-image.rc`) through the existing
devcontainer, bounded by mise's native `--timeout 10m` option. No `timeout`
executable was involved. It converged on pass 1/5 with mise 2026.9.8 across six
platforms; both image locks changed, as allowed by section 2. The generator
also pruned stale tool versions and refreshed non-hk artifact data. No lock
checksums were edited manually.

`hk test` actually declares/runs builtin tests here. It failed nine tests:
three for `python_check_ast`, four for `python_debug_statements`, and two for
`hadolint`. Each says the step's file filters excluded its fixture. The other
builtin tests, including editorconfig-checker's check/fix arms, passed. These
are real failures, not a "no tests declared" case.

## Licensed-dissent stop and remaining defects

The rev 3 section 2 prose item explicitly says that the stale postinstall
prose is asserted by no test/contract. That premise is false:

- `python/verification/suites.toml:836` declares `ci.image-lock-pr-wired`.
- Its required token at line 849 is
  `enforces it on any new job.\n      HK_SKIP_HOOKS: pre-commit,pre-push`.
- The prior lane changed `.github/workflows/refresh.yml:288` to
  `enforces this on any new job.`. The hook setting itself is unchanged.
- The real lint run returns rc=1, with `contract_token_uniqueness` reporting
  zero matches for the required token (`04-lint-initial.log`).

Per the user's explicit STOP-on-spec/code-contradiction instruction, no further
implementation or verification gates were run after identifying this conflict.
The minimal proposed correction for the caller to ratify is to retain the
required wording `enforces it on any new job.` in the updated comment; changing
the verification suite is outside this spec's allowlist. This report does not
silently change either requirement or comment.

Other failures found before the stop:

1. `hk test` rc=1: inherited fixtures `test.py` / `Dockerfile` are outside
   the narrower globs at `hk.pkl:90-96,131-132`. No builtin tests were reset or
   suppressed. A local experiment explicitly selected those fixture paths,
   but `hk test` rejected string-valued `files` with
   `invalid type: string "test.py", expected a sequence` (rc=1). The pinned
   Pkl schema declares `StepTest.files` as `String | List<String>` at
   `.agent/kb/raw/hk-v2-builtins/v2.3.0/Config.pkl:1065`; this decoder mismatch
   is another observed integration limitation. The experiment was removed
   completely, returning hk.pkl to the prior lane's diff. A List-valued
   fixture selection is a candidate for the resumed lane, not a verified fix.
2. Ruff reports SLF001 for private access to `_hooks_in_command` at
   `tests/test_workflow_claude_code.py:329,334` and `_HK_RUN_FLAG_INDEX` at
   line 331. The new test must be rewritten through the public behavior
   boundary without inline suppression.
3. Ruff Q003 and ruff-format report the escaped outer-double-quoted hook
   config string at `tests/test_workflow_claude_code.py:354`. Format it with
   outer single quotes. No formatter was run before the stop.

The lint run used the unstaged working tree (`check --all`); its result is
failure evidence, not a claim of final staged-tree validation. No changes were
staged or committed. No hk installation/uninstallation, base-image build,
whole-file mise lock, or direct edit of host/user configuration was performed.

## Final worktree status

`git status --short` returned rc=0, captured in `final-status.log` and
`final-status.rc`. There are 18 modified tracked files, all within section 2,
and six untracked report/spec files (five pre-existing plus this report).
The runtime image lock and generated audit are the two additional tracked
modifications beyond the original 16. The caller still owns the commit.

```text
 M .config/mise/conf.d/shared.toml
 M .config/mise/mise.lock
 M .devcontainer/mise-runtime.lock
 M .devcontainer/mise-system.lock
 M .github/workflows/gcc-sha-repair.yml
 M .github/workflows/refresh.yml
 M docs/hk-builtins-audit.md
 M hk-common.pkl
 M hk-image.pkl
 M hk.pkl
 M mise.lock
 M mise.toml
 M python/src/dotfiles_setup/workflow_claude_code.py
 M python/src/dotfiles_setup/workflow_hooks.py
 M renovate.json
 M tests/conftest.py
 M tests/test_image_smoke.py
 M tests/test_workflow_claude_code.py
?? docs/research/kb/reports/agents/codex-astra-implementer-hk-v2-migration-2026-09-27.md
?? docs/research/kb/reports/agents/codex-sol-implementer-hk-v2-migration-2026-09-27.md
?? docs/research/kb/reports/agents/hk-v2-global-hooks-wrong-or-adapt-2026-09-27.md
?? docs/research/kb/reports/agents/hk-v2-migration-research-2026-09-27.md
?? docs/research/kb/reports/agents/premise-verifier-hk-v2-migration-2026-09-27.md
?? docs/specs/hk-v2-migration-dotfiles.md
```

The scoped host lock emitted format-version-0 warnings for root/shared
lockfiles, recommending `mise lock --upgrade`. No whole-file upgrade was run:
the explicit scope forbids it. Platform coverage still passed. This warning
is recorded, not suppressed; no claim of a warning-free run is made.
