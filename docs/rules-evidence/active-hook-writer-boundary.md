# Active hook writer boundary

P9 / [#1853](https://github.com/ray-manaloto/dotfiles/issues/1853) qualifies
existing writer controls. A coordinator reserves the native commit interval,
obtains cooperating workers' hold acknowledgements, and releases them only after
the owned Git/hk process group is quiescent. This operating control does not
establish a filesystem access-control boundary.

## Observed existing capabilities

Source baseline: `182f6f499a1254a536bccb80f55f5db35cf0ff49`. Qualification
worktree and `codex/five-stage-workflow` initially resolved to that same commit.
Installed version inventory observed Git 2.54.0 (Apple Git-157) and hk 2.3.0.
Effective `git hook list pre-commit` and `commit-msg` each returned their enabled
hk hook. Hook inventory alone does not prove a commit executed a hook.

| Existing public seam | Control and scope | Limit |
| --- | --- | --- |
| Coordinator write guard | Known coordinator's tracked main-checkout Write is denied through real hook stdin and registered wrapper fixture entrypoints; ignored paths are allowed. | Edit/Write/NotebookEdit only; linked worktrees, shell commands and unresolved identity/Git facts are outside this guard. |
| Handoff inbox | Public `plan-apply` allows newest coordinator; non-coordinators and superseded coordinators are refused. A takeover while awaiting the target lock produces rc2 with unchanged target bytes. | Per-target cooperating handoff writers only. Caller-supplied identity and direct writes are not an access-control boundary. |
| Host lock | Real second-process fixtures show acquire, bounded contention timeout, release after holder death, and intentional descendant reentry. | Advisory flock used by participating consumers; it does not exclude arbitrary file writes. |

The existing managed test runner executed the three corresponding test modules:
110 passed; native rc0; 25.164065 seconds. Fixtures isolate global/system Git
configuration, mise tracking and host-lock paths. The real hook entrypoints in
these tests receive synthetic identities in scratch Git repositories. These
controls establish that seam's behavior, not installed-client admission or a
universal concurrent-writer guarantee.

Code anchors at the source baseline:

- [coordinator guard](../../python/src/dotfiles_setup/coordinator_write_guard.py),
  module scope and `decide`.
- [handoff inbox](../../python/src/dotfiles_setup/handoff_inbox.py), documented
  limits and authorization inside `_locked_write`.
- [host lock](../../python/src/dotfiles_setup/host_lock.py), `held` and descendant
  reentry.
- [effective hook reader](../../python/src/dotfiles_setup/hk_hooks.py),
  `event_has_hk_hook`; [pre-commit configuration](../../hk.pkl) uses `stash = "git"`.
- [scratch isolation](../../tests/conftest.py) and existing
  [guard](../../tests/test_coordinator_write_guard.py),
  [handoff](../../tests/test_handoff_inbox.py), and
  [real-process lock](../../tests/test_host_lock.py) controls.

## Native interval qualification

Qualified operating interval: caller-owned P1 attempt
`0d128298-ee71-459d-9c50-039f88fc13c7`, START issued
`2026-10-13T00:52:49.410474+00:00`. Before START the coordinator recorded actual
lint/test/verify exits 0, source/log hashes and worker holds: P2 and P9 explicitly
acknowledged HOLD; the remaining named workers were finished/frozen. The caller
owned gate queue preceded this START; the command timeout was 600 seconds, within
the 3600-second active-attempt ceiling. One native commit attempt ran.

Literal command: `git commit -m "feat: add gated draft shipping (#1845)"`.
Git returned 0 and created `2fe94741f430774fe64681a6d9c07edaa07c3d06`.
Native stderr records actual pre-commit checks and commit-msg conventional-commit
validation, and the observer recorded two hk 2.3.0 descendants. Its pre-command
PATH inventory recorded `git --version` as 2.54.0 (Apple Git-157); process
executable names alone are not a version qualification.

The measured command/cleanup interval was 18.642408750 seconds: no timeout,
observer error or cleanup error; owned process group quiescent; final Git status
clean. All three selected source paths had identical before/after SHA256 values;
the caller's END checker bound those values to committed source bytes. No sampled
hash changes were observed. The coordinator released worker holds only after
verified END. This demonstrates the recorded cooperating hold and successful
native hook activity, not mechanical prevention of arbitrary writers.

The checkout began with only three staged modifications and no reported
unstaged changes. This control therefore does not exercise concurrent unstaged
edits, stash restoration or a writer race.

The saved v2 observer keeps the literal native command and its hook environment.
It starts only that command in a new session, records native stdout/stderr and
literal return code, samples selected P1 file hashes, and records descendant
PID/PPID/executable names. Timeout/error cleanup and normal-parent-exit cleanup
use the existing public `process_stream.terminate_group` helper. A separate
signal-zero check must observe the owned process group gone before release.
Hash sampling cannot attribute a write or prove that every external writer was
excluded.

Observer source SHA256:
`d29841b2c2fda4cfe422b8e92f5f58e8498d7ef30d6fb4a84c5af6c7fe7f1945`.
Cleanup helper SHA256:
`8966b071b24b911dfd48408c89bba2a9d5d742a8a788739c4f56087e756223a9`.
Development preflight verified native rc7 preservation, cleanup after a normal
parent leaves a descendant, timeout cleanup of TERM-ignoring parent/descendant,
and error cleanup. These development controls precede START and are not native
hook qualification.

## Disposition and retained limits

Apply coordinator-owned writer holds during native commit/hook activity and
retain the existing scoped controls. Mechanical exclusion of every linked
worker, shell process, client or external editor remains UNSUPPORTED. No new
guard is implemented: the bounded qualification must first identify a concrete
missing consumer and enforceable native contract. Further investigation remains
with existing [#1830](https://github.com/ray-manaloto/dotfiles/issues/1830):
version-pinned hk qualification and an isolated linked-worktree stash
interruption/concurrency control, currently UNMEASURED. That issue does not
promise exclusion of
arbitrary shell/editor writes and is not a new prevention-graph prerequisite.

The configured Git stash mode and observed Git path topology do not establish
that hk stash state is shared across worktrees or that the motivating race was
replayed. Neither claim is adopted. Hook bypasses, real-checkout rival writes,
global configuration/client changes and historical proof mutation are outside
this qualification.

## Machine-local receipts

These ignored artifacts are local inspection pointers. The durable observations
and exact source/helper bindings are recorded above; a future clone must run a
fresh qualification rather than infer native acceptance from a missing log.

- Existing controls:
  `.agent/gate-results/runs/pytest-p9-existing-controls-preflight-arm64-20261013T004420774451Z-b8744591/`
  in the P9 worktree: console, JUnit, report JSONL and runner exit 0.
- Native interval in
  `/Users/rmanaloto/.codex/worktrees/five-stage-draft-ship/dotfiles/`:
  `.agent/state/p1-native-commit-START-20261012.json`,
  `.agent/state/p1-native-commit-END-20261012.json` and
  `.agent/gate-results/p1-native-commit-01/{receipt.json,native.stdout,native.stderr,observer.py}`.
  START SHA256:
  `f5dbd29ab39347ce36873fbf4b7fe4433bc25fd5e889ed6f4f791c8e460d11d4`;
  receipt SHA256:
  `cd75981dd52ef8770bb4e703370b7d1f53a350c328cd8783d7ae0745707f8469`.
  P9 consumed the records after END and independently rehashed them.
- Saved-observer development controls:
  `.agent/logs/p9-observer-v2-development-14563a5029464e579c871d991c894f9a/controls.json`.
  The four controls retain actual native rc 7, rc 0, rc -9 on timeout and
  rc -15 on injected observation error; each owned process group was quiescent.
  Independent PID sentinels establish that the orphan/error commands created
  descendants before cleanup. The runner exited 0.
- Read-only native tracker search:
  `.agent/logs/p9-existing-writer-issues-20261012.json` and
  `.agent/logs/p9-existing-hk-followup-1830-20261012.json`;
  each command exited 0.
