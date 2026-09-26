<!-- verbatim output.md of codex SDLC team run 4960d777 (review mode, settled completed rc=0, specialists claimed=observed: python, config, documentation), session dotfiles-20260926.000 -->

## Q1

**Recommended fix: give every pytest test its own `MISE_STATE_DIR` in both repositories.** This redirects config registration while preserving real configuration loading and warnings. An upstream improvement may reduce repeated scans, but does not replace test isolation.

The installed binary was verified with isolated state:

```text
/Users/rmanaloto/.local/bin/mise --version
rc=0
stdout='2026.9.14 macos-arm64 (2026-09-25)\n'
stderr=''
```

All 15 releases from `v2026.9.0` through `v2026.9.14` were reviewed. Relevant changes:

| Release | Change | Shipment evidence |
|---|---|---|
| `2026.9.1` | [#12676](https://github.com/jdx/mise/pull/12676): prevents recursive deferred pruning and skips it for shell integration and `--no-config`. | Feature commit → release comparison: ahead 17, behind 0. |
| `2026.9.4` | [#13003](https://github.com/jdx/mise/pull/13003): tool pruning fails when confirmation is unavailable. It does not add config cleanup. | Ahead 10, behind 0. |
| `2026.9.14` | [#13602](https://github.com/jdx/mise/pull/13602): machine-wide tracked-config consumers use ignore rules from global/system/environment sources, excluding project-local rules. | Ahead 9, behind 0. |
| Merged, unreleased | [#13674](https://github.com/jdx/mise/pull/13674): postpones repeated checks of retained tool-purgatory receipts by 24 hours. | Merge commit `c97d47002ebe0820e1b23b74806fd333d7d24b43` → `v2026.9.14`: ahead 0, behind 41; absent from that release. |

The latest-release endpoint still returned `v2026.9.14`. Relevant earlier behavior already shipped in `2026.8.13`: [#12380](https://github.com/jdx/mise/pull/12380) filters and cleans tracking entries whose targets are not regular files. Existing regular pytest configs remain eligible for parsing.

Current-tag source establishes the mechanism:

- `MISE_STATE_DIR` overrides `XDG_STATE_HOME/mise`; tracked and trust-related directories derive from it. [env.rs:202](https://github.com/jdx/mise/blob/v2026.9.14/src/env.rs#L202), [dirs.rs:12](https://github.com/jdx/mise/blob/v2026.9.14/src/dirs.rs#L12)
- Successfully parsed active configs are registered through `Tracker::track`, which creates a hashed entry pointing to the config. That function has no conditional tracking-disable setting. **State redirection does not disable tracking.** [config/mod.rs:3387](https://github.com/jdx/mise/blob/v2026.9.14/src/config/mod.rs#L3387), [tracking.rs:14](https://github.com/jdx/mise/blob/v2026.9.14/src/config/tracking.rs#L14)
- No change to `tracking.rs` appeared between September 1 and `v2026.9.14`; the same commits query without the date restriction returned August changes, providing a positive control.

**Premise correction:** “Every host mise command re-parses them” is overbroad. Plain `mise ls --json` from an unrelated directory did not warn; `mise ls --all-sources --json` did. Ordinary commands can also trigger scans when deferred-pruning receipts are due. The source supports that conditional mechanism, but the host’s actual receipt state was not inspected. [ls.rs:455](https://github.com/jdx/mise/blob/v2026.9.14/src/cli/ls.rs#L455), [tool_purgatory.rs:123](https://github.com/jdx/mise/blob/v2026.9.14/src/tool_purgatory.rs#L123)

## Q2

The most relevant upstream discussions and changes are:

| Source | Finding |
|---|---|
| [Discussion #8307](https://github.com/jdx/mise/discussions/8307) | Direct report of temporary `mise.toml` files leaving persistent tracked-config links. `MISE_TRUSTED_CONFIG_PATHS` does not make registration temporary. |
| [Discussion #5199](https://github.com/jdx/mise/discussions/5199) | Distinguishes configuration discovery from state, data, and cache isolation; names `MISE_STATE_DIR`. |
| [Discussion #12246](https://github.com/jdx/mise/discussions/12246) | `/dev/null` is rejected as an unknown config type. It is unsuitable as an isolation workaround. |
| [Discussion #10292](https://github.com/jdx/mise/discussions/10292), [PR #10414](https://github.com/jdx/mise/pull/10414) | A separate concurrent symlink-creation problem, fixed through atomic replacement. |
| [Discussion #12673](https://github.com/jdx/mise/discussions/12673) | Recursive deferred cleanup, addressed by `2026.9.1`. |
| [Discussion #13600](https://github.com/jdx/mise/discussions/13600) | Project-local ignores affecting machine-wide pruning, addressed by `2026.9.14`. |
| [PR #13674](https://github.com/jdx/mise/pull/13674) | Repeated scans caused by retained due receipts; merged after the latest verified release. |

Search coverage used `gh api`, including GraphQL for discussions. All searches exited `0`:

| Search within `jdx/mise` | Results |
|---|---:|
| REST `"tracked-configs"` | 64 |
| REST `"MISE_STATE_DIR"` | 52 |
| REST `"tracked config" warning` | 65 |
| REST `"pytest"` | 7 |
| GraphQL discussions `tracked-configs` | 25 |
| GraphQL discussions `MISE_STATE_DIR` | 28 |

REST results were complete; discussion queries reported `hasNextPage=false`. These searches found known relevant positives, including #8307 and #12380. No direct pytest-registration fix was identified in this search coverage.

**`merged=false` is not evidence that behavior never shipped.** [#9701](https://github.com/jdx/mise/pull/9701) was not merged, but [#10414](https://github.com/jdx/mise/pull/10414) explicitly credits and implements its approach. The replacement commit is contained in `v2026.9.0`, verified by comparison: ahead 1,558, behind 0.

Repository issue reconciliation:

- [dotfiles#1169](https://github.com/ray-manaloto/dotfiles/issues/1169) correctly records native config pruning followed by separate removal of surviving entries.
- The claims in [dotfiles#1248](https://github.com/ray-manaloto/dotfiles/issues/1248) and [knowledge-base#419](https://github.com/ray-manaloto/knowledge-base/issues/419) that pruning does not clean config entries conflict with current tagged source.
- Their historical measurements remain useful, dated observations. No issues or comments were modified.

## Q3

The static inventory identified **five tests that send temporary configs to real mise**, including indirect subprocess paths:

| Repository / test | Execution path | Current isolation |
|---|---|---|
| dotfiles [test_process_env.py:138](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_process_env.py:138) | `test_real_pre_push_poison_cannot_modify_outer_repository`: writes project/global configs at lines 174/188; generated pre-push hook invokes mise at 230; real Git pushes at 238/255 execute it. | Inherited environment; hook preserves `MISE_STATE_DIR`. |
| dotfiles [test_session_review.py:1044](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_session_review.py:1044) | Writes hostile config at 1049; real mise calls at 1058/1089/1108. The last loads the temporary config. | Copies environment; `_mise_project_env` preserves the state variable. |
| dotfiles [test_fnhook_gates.py:225](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_fnhook_gates.py:225) | Writes config at 232; real `mise config ls` through `default_runner` at 234. | **Already explicitly isolated** using `mise_state_dir`. Runner wiring is at [fnhook_gates.py:167](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/fnhook_gates.py:167). |
| knowledge-base [test_evals.py:570](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/test_evals.py:570) | Writes `not_a_real_setting` at 581; calls the real `mise env --redacted --json` probe through [evals.py:293](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/evals.py:293). | Inherited environment; no state redirection. |
| knowledge-base [test_eval_cases.py:88](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/test_eval_cases.py:88) | Invokes the control arm in [eval_cases.py:715](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/eval_cases.py:715), which creates a temporary directory/config and invokes the same real probe. | Inherited environment; no state redirection. |

The literal-search premise holds: neither test tree contains `MISE_STATE_DIR`. However, the keyword-based fnhook test already exercises isolation. Searching only test-local `tmp_path` writes would also miss the knowledge-base control arm’s application-created config.

No literal `.mise.toml` occurrence was found in either test tree; searches for `mise.toml` found the positive examples above.

Other real mise paths were reviewed separately:

| Repository | Sites | Classification |
|---|---|---|
| dotfiles | [test_bootstrap.py:25](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_bootstrap.py:25) | Version and chezmoi execution; no temporary config. |
| dotfiles | [test_workflows_js.py:204](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_workflows_js.py:204), line 352; [test_claude_doctor_hook.py:21](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_claude_doctor_hook.py:21) | Mise/Bun calls use repository cwd. |
| dotfiles | [test_fnhook_gates.py:56](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_fnhook_gates.py:56), lines 85–97 | Collection-time TypeScript availability probe, before autouse fixtures; repository cwd. |
| dotfiles | [test_fnhook_gates.py:304](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_fnhook_gates.py:304), lines 330/361 | Typechecking through the already-isolated production runner. |
| dotfiles | [test_session_gate.py:21](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_session_gate.py:21), line 47 | Version/invalid-command controls; no temporary config passed to mise. |
| dotfiles | [test_renovate_validate.py:167](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_renovate_validate.py:167), lines 183/189 | Repository-root `mise where`/`exec`; temporary input is Renovate JSON. |
| dotfiles | [test_audit.py:17](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_audit.py:17), line 47 | Real audit including `mise doctor`; repository cwd. |
| knowledge-base | [test_tool_sync.py:386](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/test_tool_sync.py:386), [test_mcp_serve.py:154](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/test_mcp_serve.py:154) | Repository-root task/server calls. |
| knowledge-base | [test_launch.py:456](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/test_launch.py:456) | Real tmux-shim/`mise which` route; temporary pane cwd contains no mise config. |

Additional boundaries:

- Dotfiles shell-integration tests can activate mise or invoke shims; they inherit the environment and create no temporary mise config. Container smoke calls execute inside Docker without mounting host state.
- Config-writing parser, graph, lock, currency, and mocked-runner tests were excluded unless they actually execute mise. The fake-mise Renovate test is also excluded.
- Knowledge-base’s environment scrubber preserves public `MISE_*` variables; it removes private `__MISE_*` variables. Its `XDG_STATE_HOME` scrubber test mocks the subprocess.
- No identified real temporary-config path replaces or removes the proposed state variable.

**Live isolation proof**

Both arms used disposable configuration/cache/data/state directories. For the arm without `MISE_STATE_DIR`, `XDG_STATE_HOME` pointed to disposable storage, so the fail arm could not pollute host state. The real binary was bounded with Perl’s alarm.

Both registries initially contained zero links. Verbatim excerpts:

```text
ARM A default candidate omitted ARGV ['/Users/rmanaloto/.local/bin/mise', 'ls', '--json'] MISE_STATE_DIR ABSENT; XDG_STATE_HOME=xdg-state
rc= 0 stdout= '{}\n' stderr= 'mise WARN  unknown field in /private/var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/mise-state-probe.mfQfHt/project/mise.toml: settings.not_a_real_setting\n'
state= xdg-state/mise links= 1 entries= [{'symlink': True, 'target_exists': True, 'target_is_file': True, 'target_is_fixture': True}]
state= explicit-state links= 0 entries= []
ARM B candidate explicit ARGV ['/Users/rmanaloto/.local/bin/mise', 'ls', '--json'] MISE_STATE_DIR explicit-state
rc= 0 stdout= '{}\n' stderr= 'mise WARN  unknown field in /private/var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/mise-state-probe.mfQfHt/project/mise.toml: settings.not_a_real_setting\n'
state= xdg-state/mise links= 1 entries= [{'symlink': True, 'target_exists': True, 'target_is_file': True, 'target_is_fixture': True}]
state= explicit-state links= 1 entries= [{'symlink': True, 'target_exists': True, 'target_is_file': True, 'target_is_fixture': True}]
```

A second experiment established warning behavior through the tracked-config consumer:

| Arm | Command/result |
|---|---|
| Live malformed tracked config, unrelated cwd | `mise ls --all-sources --json`: rc `0`, warning emitted. |
| Repeat invocation | rc `0`, same warning emitted again. |
| Replace invalid setting with `jobs = 2` | rc `0`, empty stderr. |
| Delete only the scratch config target | rc `0`, empty stderr; dangling symlink remains. |

Verbatim host-state and cleanup observations:

```text
host_count_before= 1466 host_count_after= 1466 host_mapping_unchanged= True
scratch_deleted= True
```

Thus isolation preserves intentional warnings while redirecting their persistent registration.

## Q4

**Licensed dissent: no prune command was executed.** The specification requests a dry run in Q4 but explicitly prohibits running `mise prune` in its constraints. Cleanup execution stopped at that contradiction; source review continued.

At `v2026.9.14`:

- `--configs` exists and selects config cleanup. Ordinary prune also performs config cleanup unless restricted to tools. [prune.rs:47](https://github.com/jdx/mise/blob/v2026.9.14/src/cli/prune.rs#L47), [79](https://github.com/jdx/mise/blob/v2026.9.14/src/cli/prune.rs#L79)
- Config cleanup calls both `Tracker::clean()` and `Trust::clean()`, covering more than `tracked-configs`. [prune.rs:119](https://github.com/jdx/mise/blob/v2026.9.14/src/cli/prune.rs#L119)
- Tracking cleanup removes entries whose targets are not regular files. **Existing pytest config files survive.** [tracking.rs:74](https://github.com/jdx/mise/blob/v2026.9.14/src/config/tracking.rs#L74)
- Config dry-run only prints `pruned configuration links [dryrun]`; it does not enumerate candidates. `--dry-run-code` concerns tool candidates and cannot establish whether stale config entries exist.
- Generic CLI cache pruning precedes the deferred-pruning dry-run guard. A host invocation cannot be assumed entirely mutation-free merely because `--dry-run` was supplied. [cli/mod.rs:1128](https://github.com/jdx/mise/blob/v2026.9.14/src/cli/mod.rs#L1128)

Read-only host inventory, command rc `0`:

| Classification | Count |
|---|---:|
| Tracking entries | 1,466 |
| Dangling candidates | 1,259 |
| Of those, target path contains `pytest-` | 932 |
| Existing regular-file targets retained | 207 |
| Of those, target path contains `pytest-` | 3 |

These classify only `tracked-configs`, not native cleanup’s complete tracking/trust scope. Path classification does not independently prove which process created each link.

A future authorized cleanup should:

1. Prefer native `mise prune --configs` for obsolete entries after reviewing its broader scope.
2. Expect, from this snapshot and source semantics, 1,259 tracked-config removals and 207 retained entries.
3. Review the three still-existing pytest targets individually. Native pruning cannot remove their registrations while the files remain regular files.
4. Use an exact reviewed list for any further removal; avoid broad deletion of pytest roots or tracking directories.

No cleanup was performed.

## Q5

The proposed implementation changes are limited to:

- Dotfiles [tests/conftest.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/conftest.py).
- Knowledge-base [tests/conftest.py](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/conftest.py).
- One focused isolation regression module in each repository.
- Strengthening dotfiles [test_fnhook_gates.py:225](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_fnhook_gates.py:225).

**Fixture shape:** an unconditional, function-scoped autouse fixture named `isolated_mise_state`, accepting `tmp_path` and `monkeypatch`, creates `tmp_path / "mise-state"`, sets `MISE_STATE_DIR` to that directory, and returns its `Path`.

Use assignment, not `setdefault`: inherited host state must be overridden. Function scope prevents one test’s malformed config from affecting another. Worker-specific pytest temporary directories also separate concurrent workers.

Do not globally redirect `HOME`, configuration discovery, or installed-tool data directories for this defect. State isolation also isolates trust records; any tests relying on ambient trust will need explicit, narrowly scoped trust setup during implementation validation. Do not solve that by suppressing warnings or broadly trusting paths.

**Regression design**

Use a child pytest process, invoked through the current interpreter, against a scratch test tree that loads the actual repository conftest:

1. Seed a disposable outer “host” registry and snapshot its exact entry-name → target mapping.
2. Give the child that outer `MISE_STATE_DIR` plus a disposable `XDG_STATE_HOME` fallback.
3. Parameterize `mise.toml`/`.mise.toml` and inherited/copied subprocess environments.
4. Invoke real mise before checking isolation. Require rc `0`, the exact config target in the inner registry, and the outer mapping unchanged.
5. Retain an invalid-setting case that must still emit the expected warning.
6. Validate a realistic reversion in a disposable copy with the isolation fixture removed. The same test must fail, and the config must appear in the fake outer registry.

The child test should not require the fixture by name: otherwise removing it could produce “fixture not found” before mise runs, failing to demonstrate the original pollution. Likewise, assertions must follow the real invocation so the fail arm actually registers the config.

A live host count is useful corroboration, but an isolated exact mapping is the deterministic oracle: concurrent host work cannot invalidate it, and additions/removals cannot cancel numerically.

**Existing-test masking trap:** once the autouse fixture exists, removing `default_runner`’s own isolation could still leave host state unchanged. Strengthen its existing test to require the exact config link in the runner’s **explicitly supplied** state directory and no link in a separate ambient registry.

**Scope limit:** the import-time fnhook availability probe runs before fixtures. It currently loads repository configuration and creates no temporary config, so it is outside the demonstrated leak. Blanket collection isolation would require a separate fixture refactor.

No production subprocess wrapper is needed for the identified pytest leak. No implementation or regression tests were written or run.

## Evidence table

| Claim | Source URL or file:line | Probe + control arm |
|---|---|---|
| `MISE_STATE_DIR` redirects registration | [env.rs:202](https://github.com/jdx/mise/blob/v2026.9.14/src/env.rs#L202), [tracking.rs:14](https://github.com/jdx/mise/blob/v2026.9.14/src/config/tracking.rs#L14) | Omitted redirect grows disposable default registry; explicit redirect grows explicit registry. Both rc `0`. |
| Isolation preserves warnings | [mise_toml.rs:609](https://github.com/jdx/mise/blob/v2026.9.14/src/config/config_file/mise_toml.rs#L609) | Invalid setting warns; `jobs=2` is silent. |
| Non-active warning reproduction is command-dependent | [ls.rs:455](https://github.com/jdx/mise/blob/v2026.9.14/src/cli/ls.rs#L455) | Plain `ls` silent; `ls --all-sources` warns from the same tracked config. |
| Dangling entries can remain without warning | [tracking.rs:39](https://github.com/jdx/mise/blob/v2026.9.14/src/config/tracking.rs#L39) | Deleted target: symlink remains, stderr empty; live malformed target warns. |
| Native cleanup keeps existing pytest files | [tracking.rs:79](https://github.com/jdx/mise/blob/v2026.9.14/src/config/tracking.rs#L79) | Source predicate and live-file test; host snapshot distinguishes 1,259 dangling from 207 regular targets. |
| Config dry-run is not an inventory | [prune.rs:119](https://github.com/jdx/mise/blob/v2026.9.14/src/cli/prune.rs#L119) | Log-only dry-run branch versus actual cleanup branch. CLI execution stopped by specification conflict. |
| Unmerged PR does not prove unshipped behavior | [#9701](https://github.com/jdx/mise/pull/9701), [#10414](https://github.com/jdx/mise/pull/10414) | Original unmerged; replacement commit contained in release. |
| #13674 is not released in `v2026.9.14` | [#13674](https://github.com/jdx/mise/pull/13674) | Comparison behind 41; shipped #13602 comparison has behind 0. |
| Host tracking stayed unchanged during isolated consumer probe | Q3 transcript | Exact mapping unchanged; count 1,466 → 1,466. |
| Git-visible checkout state remained clean | Both repositories, final `git status --short` | Both rc `0`, empty output; does not cover the dependency-environment exception below. |

Specialist gate results:

| Specialist | Normal gate | This review |
|---|---|---|
| Python | pytest | **Not run**, as instructed |
| Config | `mise run lint` | **Not run**, as instructed |
| Documentation | `mise run lint-docs` | **Not run**, as instructed |

Docs research used the local cache, then a fresh `llms.txt` fetch, rc `0`. The prune `.md` endpoint returned 404/rc `56`; tagged source supplied the answer.

## GitHub repos touched

- `jdx/mise` — read-only release, source, commit, issue, PR, and discussion research.
- `ray-manaloto/dotfiles` — read-only test/configuration inspection and #1169/#1248 research.
- `ray-manaloto/knowledge-base` — read-only test/configuration inspection and #419 research, with the local dependency-environment exception below.

## Open questions

- **Cleanup remains blocked by the specification conflict.** No prune preview or cleanup ran.
- The three live pytest config targets need individual review before removal.
- #13674 addresses a source-proven repeated-scan mechanism; the host’s actual trigger remains unverified.
- Repository gates must validate the proposed fixture’s interaction with trust and environment handling during a later implementation.
- Dotfiles Graphify returned `rc=3`, stale; source inspection was used.

**Unexpected review side effect:** the required knowledge-base query invoked its automatic dependency sync, despite being intended as a read-only query. [mise.toml:250](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/mise.toml:250) defines `deps.uv` with `auto=true` and `uv sync --locked`; [mise.toml:807](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/mise.toml:807) runs the query.

The exact query was:

```text
perl -e 'alarm 50; exec @ARGV' mise run kb-query -- 'Which tests invoke real mise in temporary directories and where are their subprocess environment fixtures?'
```

It resolved 167 packages and uninstalled these 16:

```text
argcomplete 3.7.2; black 26.5.1; datamodel-code-generator 0.76.0;
genson 1.4.0; grpcio 1.83.1; grpcio-tools 1.83.1; inflect 7.5.0;
isort 8.0.1; jinja2 3.1.6; markupsafe 3.0.3; more-itertools 11.1.0;
mypy-extensions 1.1.0; pathspec 1.1.1; platformdirs 4.11.3;
pytokens 0.4.1; typeguard 4.6.0.
```

The default environment resolves to `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.venv`; uv did not explicitly print that path. The query then produced unusable Graphify output and was terminated by the alarm: **direct subprocess rc `-14`; capture-driver rc `0`**. A subsequent process check found no surviving match for the unique query.

Runtime work in that repository stopped. No restoration was attempted. Both Git working trees remain clean, but the dependency environment is **not restored**. No report files, source edits, commits, issue updates, or repository gates were produced.

All three specialists completed. No others were spawned.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_test_inventory`
- `sdlc-config-specialist` — `/root/config_tracking_probe`
- `sdlc-documentation-specialist` — `/root/upstream_research`