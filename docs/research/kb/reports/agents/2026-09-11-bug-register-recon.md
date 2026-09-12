# Bug-register reconnaissance — 2026-09-11

Read-only reconnaissance of `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`,
commissioned by the team lead for a design discussion about where a "known bug +
its workaround" should be recorded so a later session does not re-diagnose it
from scratch. Facts only; no design proposed.

**Headline: this exact bug is already filed twice.** #877 (2026-08-31, labels
`bug` + `ready-for-agent`, parent #848, 1 comment) and #998 (2026-09-09, **no
labels, no comments**) are the same defect, 9 days apart, neither referencing the
other. #877's comment already contains the fix #998 "proposes".

---

## 1. Mechanisms that could carry a known-bug record

### `.claude/rules/*.md` — 26 files. **No rule about recording defects/workarounds.**

`grep -rn -i -E "workaround|known bug|known issue|known-broken" .claude/rules/*.md`
→ **1 hit**, and it is incidental prose (`agent-artifact-conventions.md:93`,
"project workaround" about a skill-listing budget).

*Control arm* (same command shape, same corpus): `-E "pipefail|control arm"` →
**15 hits**; fresh nonce `wqvbz7` → **0**. The probe discriminates, so the
absence is real.

The four named rules do adjacent things, none of them this:

- `zero-skip-policy.md:22-24` rule 4 — *"If the user explicitly approves
  deferring an issue, create a GitHub Issue via `gh issue create` with the full
  context"*. This is the closest thing to a register policy: the sink is
  **GitHub Issues**, and it fires only on a *deferral*, not on a
  diagnosed-and-worked-around bug.
- `verify-before-advancing.md` — evidence discipline; carries per-tool traps
  inline (`gh run watch` lies) but has no register.
- `notepad-enforcement.md` — findings go to root `findings.md` (gitignored,
  session-scoped) and `.agent/notepad.md`.
- `probes-need-a-control-arm.md` — how to trust a probe; its case tables live in
  `docs/rules-evidence/`.

### Auto-memory — **117 `feedback_*.md`** (of 317 files: 184 `project_*`, 12 `reference_*`, 3 `user_*`)

Path: `/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/`

Yes — this is the de facto known-bug register. Three concrete tool-bug-plus-workaround records:

| File | Content |
|---|---|
| `feedback_graphify_attached_graph_flag.md` | graphify silently **drops** `--graph=<path>` (attached form) and answers from the cwd default — from a repo root it exits 0 with a confident answer from the wrong corpus. Workaround: always `--graph <path>` with a space. Probed 2026-07-25 on graphify 0.9.25, with the rc=1 transcript inline. |
| `feedback_typos_diff_hides_ambiguous.md` | `typos --diff` prints **nothing** for an ambiguous correction while `typos` still exits 2, so hk fails with an empty log and a per-file `--diff` recheck reads clean. Workaround: plain `typos <file>`, read its own rc. Cost three round-trips on 2026-08-01. |
| `feedback_sshd_feature_options_silently_dropped.md` | `ghcr.io/devcontainers/features/sshd` accepts only `version` + `gatewayPorts`; `port`/`username`/`startNow` are **silently dropped**, no warning. Shipped a broken R1 through two handoffs that claimed COMPLETE. Workaround: curl the feature's `devcontainer-feature.json` and verify the option set first. |

Others in the same shape: `feedback_mise_local_toml_replaces_task` (a
`[tasks.x] env` override strips `run` → silent no-op at exit 0),
`feedback_mise_lock_whole_file_is_destructive`,
`feedback_hk_builtins_need_assignment` (bare `{}` is a silent no-op),
`feedback_mise_broken_git_workaround` (literally named "workaround"),
`feedback_background_task_notification_can_lie`,
`feedback_stop_hooks_force_a_turn`.

### `docs/rules-evidence/` — **19 files**

Purpose per `agent-artifact-conventions.md:69` (tracked table): *"One evidence
sibling per eager rule."* Tracked and clone-durable; it holds the case tables,
probe transcripts and archaeology that would blow the eager rules' size budgets.
It is organised **by rule**, not by defect — a bug only lands here if it
motivated a rule.

### `doctor.toml` (220 lines) + the project doctor — **yes, it can warn at SessionStart, and already does for host conditions**

Wiring, `.claude/settings.json` `SessionStart` (matcher `startup|resume`):

```
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then bash .../scripts/web-setup.sh;
else mise -C ... run tool-currency-check; DOTFILES_AMBIENT_PATH="$PATH" mise -C ... run doctor; fi
```

Current checks — `python/src/dotfiles_setup/doctor.py:1216-1235`:

`mcp-env-opt-in`, `mcp-scope`, `fnox-baseline`, `fnox-exec-leak`, `mcp-pin`,
`mcp-guard-coverage`, `mcp-duplicate`, `pin-currency-wired`, `listing-budget`,
`path-drift`, `graphify-skill-surface`; plus `--live`-only `mcp-live-tools`,
`mcp-health`.

Every check is a claim about state **outside** the working tree
(`~/.config/fnox`, `~/.claude`, PATH) — that is the file's stated reason for
existing (`doctor.toml:11-14`). `[path_drift]` at `:212-220` is the closest
existing precedent to "warn about a known-broken host condition": it names five
`gate_tools` that *"have actually drifted at least once"*, each with its incident
date. Silent when healthy, always exits 0.

Other doctor.toml sections: `[fnox]` (`env = true` + the exhaustive 56-name
`env_true` set), `[mcp]` (`scope_servers = []`, `[mcp.mutating_tools]` empty),
`[listing]` (`max_chars = 41305` for the skill+agent listing budget),
`[graphify]` (required skill files, stub marker, `forbidden_agents_md_marker`),
`[path_drift]` (`gate_tools = ["hk", "uv", "python", "ruff", "npm:renovate"]`).

### GitHub labels — 24 total, **no `known-bug` / `workaround` / `upstream`**

Present: `bug`, `documentation`, `duplicate`, `enhancement`, `good first issue`,
`help wanted`, `invalid`, `question`, `wontfix`, `dependencies`, `python:uv`,
`mise-snapshot`, `lockfile`, `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wayfinder:map`, `wayfinder:prototype`, `wayfinder:research`,
`wayfinder:grilling`, `wayfinder:task`, `auto-queue`, `dag:needs-human`.

`docs/triage-labels.md:20-34` documents two orthogonal axes (state vs type) and
explicitly scopes the type axis to `enhancement`/`bug`/`dependencies`/`lockfile`.
Nothing distinguishes "open because nobody has fixed it" from "open, known,
worked around".

### No known-issues register exists

`git grep -lni "known issue"` → 4 files, all research reports + the vendored
chezmoi `llms-full.txt`. `"known bug"` → 5 files, all
`docs/research/kb/reports/**`. `"workaround"` → 59 files, top hits all research
artifacts (`modernization-audit-2026-09-09.toml`: 13, `.md`: 12) plus
`python/verification/suites.toml`: 2 and `docs/receipts/448.md`: 2.

Filename search `git ls-files | grep -iE "known|issues|register|gotcha|caveat|trap"`
returns only research reports and unrelated files (`bootstrap_packages.py`, a
`ssh-ignoreunknown` skill). *Control arm*: same shape with `rules-evidence` →
**19**, so the search can find files.

`docs/` top level: `adr/`, `agents/`, `handoffs/`, `receipts/` (22 files),
`research/`, `rules-evidence/` (19), `specs/`, `currency/`, `maestro/`,
`ultrapowers/`, plus `agent-team.md`, `ci-debugging.md`,
`claude-plugin-config-hygiene.md`, `devcontainer-lifecycle-hooks.md`,
`domain.md`, `graphify-local-embedding-pass.md`, `hk-builtins-audit.md`,
`issue-tracker.md`, `repowise-advisory.md`,
`secrets-doppler-fnox-keychain.md`, `skills-inventory.md`,
`triage-labels.md`, `web-brick-fix-handoff.md`. None is a defect register.

---

## 2. Recurrence measurement

**117 `feedback_*.md` memories. ~55 (≈47%) are "a tool/platform/shell/harness
misbehaves — here is the workaround."**

Classification basis: I read all 117 `description:` frontmatter lines and
bucketed by whether the memory's core content is (A) an external tool, CLI,
platform, shell or harness behaving wrongly or surprisingly, plus what to do
instead; (B) methodology/epistemics/Ray's process preferences; (C) a
project/infra fact or invariant. The A/B boundary is judgment at the margin —
e.g. `feedback_gh_run_watch` (a tool that lies) vs `feedback_gh_cli_watch_flag`
(use the flag) — so treat ~55 as ±5, not exact.

The A bucket by subsystem:

| Subsystem | Count | Examples |
|---|---|---|
| mise | 8 | `mise_lock_reuses_locked_version`, `mise_lock_whole_file_is_destructive`, `mise_local_toml_replaces_task`, `mise_depends_parallel`, `mise_run_masks_digits`, `mise_broken_git_workaround`, `mise_pins_no_v_prefix`, `nonexec_file_cannot_shadow_shell_lookup` |
| shell / POSIX | 5 | `zsh_no_word_splitting`, `pipe_kills_exit_code`, `presence_probe_value_leak`, `find_missing_startdir_trips_set_e`, `git_checkout_is_not_undo` |
| GitHub / gh | 5 | `gh_run_watch`, `github_updated_at_advances_on_comment`, `stacked_pr_merge_order`, `issue_body_edit_needs_anchor_assert`, `skipped_check_satisfies_required` |
| Claude Code harness | 5 | `background_task_notification_can_lie`, `stop_hooks_force_a_turn`, `cd_resets_shell_cwd`, `protocol_verbs_are_user_invoked_only`, `bundled_workflows_invoke_by_name` |
| OMC plugin | 5 | `omc_autoresearch_tmux`, `omc_hud_shim_discovery`, `omc_launch_required`, `omc_phantom_teammatemode`, `omc_plugin_dist_build` |
| devcontainer / docker | 4 | `sshd_feature_options_silently_dropped`, `image_smoke_mac_rosetta_tsan`, `devcontainer_path_via_mise_path`, `ubuntu_release_pocket_pins_dont_install` |
| hk | 3 | `hk_builtins_need_assignment`, `hk_stash_drop_unstaged`, `hk_stash_phantom_deleted` |
| chezmoi | 2 | `chezmoi_diff_needs_absolute_target`, `chezmoi_overwrites_templated_files` |
| codex | 2 | `codex_worktree`, `codex_review_protocol` |
| graphify | 2 | `graphify_attached_graph_flag`, `kb_graphify_claude_only` |
| our own ship/land | 2 | `amend_after_ship_races_automerge`, `ship_gates_before_push_automerge_race` |
| scattered | rest | `typos_diff_hides_ambiguous`, `fd_skips_hidden_dirs`, `fnox_env_three_states`, `npm_postinstall_bun_backend`, `apt_snapshot_removed`, `mintlify_cache_stale`, `codesmith_bot_commits_as_you`, `github_app_token_setup_gotchas`, `python2_comma_except`, `mise_backend_direction_research`, `agent_spawn_liveness`, `mise_strict_fake_env` |

**Two memories record bugs that were later fixed upstream** and are kept as
historical: `feedback_hk_stash_phantom_deleted` ("OBSOLETE since hk 1.46 (#927)")
and `feedback_mise_run_masks_digits` ("FIXED 2026-08-08"). So the corpus already
carries lifecycle state informally, in prose.

---

## 3. #998 verbatim

State **OPEN**, labels **`[]`**, comments **`[]`**.

Title: ``pre-push hook refuses every push from a non-activated shell: $MISE_PROJECT_ROOT is empty outside `mise activate` ``

````markdown
## What happened

`git -C /path/to/dotfiles push origin --delete <branch>` from a shell that is not `mise activate`d (an agent's Bash tool in the sibling knowledge-base repo, 2026-09-09) is refused by the pre-push hook's `test` step:

```
test – env -u MISE_IGNORED_CONFIG_PATHS mise --cd "$MISE_PROJECT_ROOT" run test-hook-isolated
test – mise ERROR Directory specified with --cd does not exist:
error: failed to push some refs to 'github.com:ray-manaloto/dotfiles.git'
```

`hk.pkl:780` interpolates `$MISE_PROJECT_ROOT`, which only exists in a shell where `mise activate` exported it. Measured: `mise -C <dotfiles> exec -- sh -c 'echo "[$MISE_PROJECT_ROOT]"'` prints `[]` too, so `mise exec` does not set it either. The same push with the variable set by hand — `MISE_PROJECT_ROOT=<dotfiles> git -C <dotfiles> push origin --delete …` — runs the hook correctly (2923 passed in 68.81s) and the eight branch deletions went through.

## Why it matters

Every push from a non-activated context (an agent lane, `git -C` from another repo, a plain `sh`) fails on a hook that had nothing to test — the step printed *"No files to compare for remote branch deletion (0 files)"* and then hard-errored on the empty `--cd`. The failure reads as a test failure, not as a missing environment variable.

## Proposed fix

Resolve the project root inside the step rather than trusting an activation-only variable — e.g. `--cd "${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}"`, or hk's own workspace root if it exposes one — and add a FAIL arm: run the hook once with the variable unset and assert it still finds the project.

Found while executing knowledge-base #727's branch hygiene (the census-ruled deletions).
````

Note: #998 cites `hk.pkl:780`; at the time of this recon the step was at
**`hk.pkl:792`** (the file moved under it).

### #877 — the prior filing, verbatim

State **OPEN**, labels **`['bug', 'ready-for-agent']`**, 1 comment.

Title: `Pre-push hook's test step fails from a non-interactive shell (empty MISE_PROJECT_ROOT)`

````markdown
## Parent

#848

## What to build

`git push` from a plain non-interactive shell fails in the pre-push hook, because
the hook's `test` step expands an environment variable that is only set by an
interactive mise shell activation. With it unset the step invokes mise with an
empty directory argument and mise refuses:

```
test – env -u MISE_IGNORED_CONFIG_PATHS mise --cd "$MISE_PROJECT_ROOT" run test-hook-isolated
test – mise ERROR Directory specified with --cd does not exist:
✗ test – ERROR
```

Reproduced 2026-08-31 while deleting a remote branch: the push exited 1 and the
branch was not deleted. Re-running the identical command with the variable set
explicitly succeeded (`rc=0`, `- [deleted] proto/bake-matrix-fields`), so the
variable is the whole difference — a control-armed two-arm result.

This blocks any agent-driven or scripted push, which is every push that does not
originate from a human's activated shell.

**A second, smaller problem visible in the same run:** the hook ran the **full
2,559-test suite** for a *branch deletion*, immediately after its own `files`
step had reported `No files to compare for remote branch deletion (0 files)`. A
delete-only push changes no content, so there is nothing for the suite to
validate.

## Acceptance criteria

- [ ] The `test` step resolves the project root itself rather than depending on an ambient variable — or fails loudly with an actionable message when it cannot.
- [ ] A push from a plain non-interactive shell succeeds, with the failing arm pinned: the pre-fix invocation reproduces the error.
- [ ] A delete-only push does not run the content test suite, and the control arm holds — a push that *does* carry commits still runs it.
- [ ] The fix is verified by deleting the wiring line that calls the resolution, not by renaming a symbol whose original survives as a substring.

## Blocked by

None — can start immediately.
````

#### #877's comment, verbatim

Author `sortakool`, 2026-09-02T02:40:11Z:

````markdown
Reproduced live on 2026-09-01 while pushing a fix onto PR #902.

A bare `git push origin <branch>` from a plain (non-mise) shell fails in the pre-push hook:

```
❯ test
  test – env -u MISE_IGNORED_CONFIG_PATHS mise --cd "$MISE_PROJECT_ROOT" run test-hook-isolated
  test – mise ERROR Directory specified with --cd does not exist:
  test – Please check the path and try again.
✗ test – ERROR
error: failed to push some refs to 'github.com:ray-manaloto/dotfiles.git'
```

`MISE_PROJECT_ROOT` is unset outside a mise context, so the command becomes `mise --cd ""`.

**Why it stays hidden:** every successful push that session went through `mise run ship`, which supplies the variable. The hook only fails when you *don't* use the canonical verb — so the normal flow never surfaces it.

**Why it matters beyond ergonomics:** in this state the `test` step cannot run, so on a bare push it certifies nothing — it errors before reaching `test-hook-isolated`. That is a gate that can only fail rather than one that can only pass, but the effect is the same: it is not testing what it claims to test.

Suggested fix is a default in the step body, so the hook tests rather than errors:

```sh
mise --cd "${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}" run test-hook-isolated
```

Worth pairing with a control arm per `.claude/rules/probes-need-a-control-arm.md`: assert the step actually fails on a deliberately broken hook, so the fix cannot regress into a silent no-op.
````

`gh search issues --repo ray-manaloto/dotfiles "MISE_PROJECT_ROOT"` → exactly
these two open issues (#998, #877) plus closed #808.

---

## 4. Where the failing step is defined

**`hk.pkl:790-793`** (pre-fix state, as found) — the only hk step referencing the
variable:

```pkl
      ["test"] {
        exclusive = true
        check = "env -u MISE_IGNORED_CONFIG_PATHS mise --cd \"$MISE_PROJECT_ROOT\" run test-hook-isolated"
      }
```

**`mise.toml:234-236`** — the task it calls:

```toml
[tasks.test-hook-isolated]
description = "Run the Python suite without credentials or hook-exported Git-local variables"
run = "uv run --project python dotfiles-setup process git-isolated -- uv run --project python pytest tests/ -x -q"
```

### Is the fix one site or many? — **one production site, but four files to touch.**

Full tracked `git grep -n MISE_PROJECT_ROOT`, excluding `docs/`:

| Site | Affected? |
|---|---|
| `hk.pkl:792` | **YES** — the defect. The only hk step. |
| `mise.toml:1404,1408` (`cc`), `:1526`, `:1530`, `:1538` (`session-gate`) | **No** — these run *inside* `mise run <task>`, where mise itself exports the variable. The 2026-09-09 modernization audit control-armed this: set under `mise run`, **unset** under `mise exec --`. |
| `python/src/dotfiles_setup/session_gate.py:272` | **No** — already has the fallback: `Path(os.environ.get("MISE_PROJECT_ROOT", Path.cwd())).resolve()` |
| `python/src/dotfiles_setup/workflow_hooks.py:398` | **No, but brittle** — `"$MISE_PROJECT_ROOT"` is a literal element of the `FIRST_PARTY_GIT_WRITERS` argv tuple, exact-prefix-matched. Only binds the mise.toml session-gate argv, not hk.pkl. |
| `python/src/dotfiles_setup/path_drift.py:42` | No — docstring only. |
| **`tests/test_process_env.py:221, :238, :283`** | **YES** — three assertions pin the exact string `env -u MISE_IGNORED_CONFIG_PATHS mise --cd "$MISE_PROJECT_ROOT" run test-hook-isolated`, including `:283` which asserts it appears verbatim in `hk.pkl`. Any edit to `hk.pkl:792` breaks these. |
| `tests/test_session_gate.py:297` | No — `monkeypatch.setenv`. |

So: **1 line to fix, 3 test assertions to update**, and #877's second acceptance
criterion (skip the suite on a delete-only push) is an independent change in the
same step.

### Post-recon verification (branch `fix/877-pre-push-project-root`)

Re-probed after the team lead landed the fix as PR #1022:

- `hk.pkl:790+` now carries an explanatory `// #877:` comment block citing
  jdx/mise PR #9657 and `docs/hooks.md` for why a git pre-push hook is not a
  mise task execution context.
- `tests/test_process_env.py:343` now pins the **new** form,
  `\"${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}\"`, and `:310-327`
  add the two-arm test (`:312` "The real defect's arm: no MISE_PROJECT_ROOT
  anywhere, as in a bare push"; `:327` the supplied-sentinel arm). The three
  brittle pins flagged above were handled.

No correction to the lead's two claims: #877's comment does contain the fix, and
`hk.pkl` was the sole `--cd "$MISE_PROJECT_ROOT"` site.

---

## Verified vs unconfirmed

**Verified** (direct file reads / `gh` API): all file:line citations; the
26/117/19/22/24/11-check counts; #998 and #877 bodies, labels and comments; the
SessionStart wiring; the full `MISE_PROJECT_ROOT` tracked-tree enumeration; both
absence control arms; the post-fix state of `hk.pkl` and
`tests/test_process_env.py`.

**Not confirmed:**

- The **~55/117 classification is my judgment**, not a mechanical derivation. The
  117 count is exact; the split is not.
- **graphify could not answer** for question 4 —
  `mise run graphify-query -- "where is test-hook-isolated defined"` returned
  `graphify: incomplete: [!] TRUNCATED: showing 52 of 223 nodes` and
  `ERROR task failed`. Per `graphify-first.md` I report the graph as unavailable
  and fell back to source; the `git grep` results above are the authority. (A
  first attempt also died on `mise ERROR No version is set for shim: timeout`.)
- I did **not** read the bodies of all 117 memories, only their `description:`
  frontmatter plus four full files.
- I did not verify whether #848 (#877's parent) is open or what else it tracks.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under reconnaissance; issues #877, #998, #808 and the label list read via `gh`.
- [jdx/mise](https://github.com/jdx/mise) — PR #9657 cited in the landed fix's
  comment block as the anchor for `MISE_PROJECT_ROOT`'s task-only scope (read
  second-hand from the fix, not fetched by this lane).
