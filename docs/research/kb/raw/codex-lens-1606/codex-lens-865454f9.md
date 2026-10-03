OpenAI Codex v0.160.0
--------
[1mworkdir:[0m /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[1mmodel:[0m gpt-6-astra
[1mprovider:[0m openai
[1mapproval:[0m never
[1msandbox:[0m read-only
[1mreasoning effort:[0m xhigh
[1mreasoning summaries:[0m none
[1msession id:[0m 01a10367-c544-7583-b2bf-a92dacbd2212
--------
[36muser[0m
commit 865454f
[1m[33mwarning:[0m[0m Under-development features enabled: chronicle. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /Users/rmanaloto/.codex/config.toml.
[1m[33mwarning:[0m[0m clamping SessionEnd hook timeout to 3s in /Users/rmanaloto/.codex/plugins/cache/openai-codex/codex/1.0.6/hooks/hooks.json
[2m2026-10-03T20:14:56.668449Z[0m [31mERROR[0m [2mcodex_rmcp_client::oauth::refresh_transaction[0m[2m:[0m [3merror[0m[2m=[0mfailed to refresh OAuth tokens for server graphify: OAuth refresh token was rejected: Server returned error response: invalid_grant: Refresh token reuse detected.
[2m2026-10-03T20:14:57.358992Z[0m [31mERROR[0m [2mcodex_rmcp_client::oauth::refresh_transaction[0m[2m:[0m [3merror[0m[2m=[0mfailed to refresh OAuth tokens for server exa: OAuth refresh token was rejected: Server returned error response: invalid_grant: Refresh token has been revoked
[1m[33mwarning:[0m[0m Under-development features enabled: chronicle. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /Users/rmanaloto/.codex/config.toml.
[1m[33mwarning:[0m[0m clamping SessionEnd hook timeout to 3s in /Users/rmanaloto/.codex/plugins/cache/openai-codex/codex/1.0.6/hooks/hooks.json
[2m2026-10-03T20:14:58.539230Z[0m [31mERROR[0m [2mcodex_rmcp_client::oauth::refresh_transaction[0m[2m:[0m [3merror[0m[2m=[0mfailed to refresh OAuth tokens for server graphify: OAuth refresh token was rejected: Server returned error response: invalid_grant: Refresh token reuse detected.
[2m2026-10-03T20:14:58.911753Z[0m [31mERROR[0m [2mcodex_rmcp_client::oauth::refresh_transaction[0m[2m:[0m [3merror[0m[2m=[0mfailed to refresh OAuth tokens for server exa: OAuth refresh token was rejected: Server returned error response: invalid_grant: Refresh token has been revoked
[35m[3mexec[0m[0m
[1m/bin/zsh -lc "pwd; git status --short; git show --stat --oneline --decorate --no-renames 865454f9; rg -n '1606|install-doctor|native-clis|plugin.health' /Users/rmanaloto/.codex/memories/MEMORY.md"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[32m succeeded in 1462ms:[0m
/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-BwRZ1LQu' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-RNQZc1QH' (errno=Operation not permitted)
?? docs/research/kb/reports/agents/cold-review-1606-0125fc4d.md
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Q9e9q9rN' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-0gIQlUSh' (errno=Operation not permitted)
865454f9 (HEAD -> fix/1606-enterworktree-guard) fix(hooks): keep host git config and hooks out of the #1606 selfcheck fixture
 python/src/dotfiles_setup/hook_selfcheck.py | 87 ++++++++++++++++++-----------
 tests/test_hook_selfcheck.py                | 43 ++++++++++++++
 2 files changed, 97 insertions(+), 33 deletions(-)
82:- install-doctor, native-clis check, claude-doctor reserved prefix, cc-plugin-you-should-know@builtin, default-groups codegen, shfmt --to-json, typed drift verdict, S29-00b, PR #1503, PR #1510, PR #1531
98:- Native devcontainer CLIs are Claude, Codex, and agy installed under `~/.local/bin`; final validation must run from the main checkout after a new image, with `native-clis check` rc=0 and no compatibility SKIP. [Task 3]
558:- claudex-loop@claudex-loop, plugin-inventory, plugin-remove --apply, plugin-health, doctor --strict, DOTFILES_AMBIENT_PATH, removed-plugins, #1318, #1386, #1388
616:- Use exact selector `claudex-loop@claudex-loop`. Verify inventory before/after, `plugin-health`, and doctor findings with `DOTFILES_AMBIENT_PATH="$PATH"`; `doctor --strict` may remain rc=1 for unrelated host drift, so require zero `removed-plugins` findings. The remove path may leave an empty cache parent invisible to inventory; remove that empty directory separately. [Task 2]
1454:# Task Group: dotfiles late-session reliability, plugin health, and ship diagnostics
1470:## Task 2: Add research-plugin health/dependency currency and unblock safe mise resolution
1475:- rollout_summaries/2026-09-14T11-46-29-Pe7V-plugin_health_dependency_currency_update_all_handoff.md (cwd=/Users/rmanaloto/dev/github/ray-manaloto/dotfiles, rollout_path=/Users/rmanaloto/.codex/sessions/2026/09/14/rollout-2026-09-14T06-46-29-01a09fbd-786d-7e20-9c0c-f7651094bcab.jsonl, updated_at=2026-09-14T04:07:55+00:00, thread_id=01a09fbd-786d-7e20-9c0c-f7651094bcab, plugin/dependency checks shipped; zero-outdated goal incomplete)
1479:- plugin-health, dependency-currency, claude plugin list --json, claude plugin validate, uv pip list --outdated --format json --python, MISE_LOCKFILE, uvx = false, graphifyy, skypilot, azure-cli, mise run -n update:all, graphify-update, claude-cli

[35m[3mexec[0m[0m
[1m/bin/zsh -lc 'git diff 865454f9''^ 865454f9 -- python/src/dotfiles_setup/hook_selfcheck.py tests/test_hook_selfcheck.py; printf '"'\\n--- guidance paths ---\\n'; find .. -name AGENTS.override.md -o -name AGENTS.md | head -80; printf '\\n--- fallback configuration ---\\n'; rg -n 'project_doc_fallback_filenames' /Users/rmanaloto/.codex/config.toml; printf '\\n--- memory lookup ---\\n'; rg -n 'hook.selfcheck|EnterWorktree|1606|worktree.*guard' /Users/rmanaloto/.codex/memories/MEMORY.md"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[32m succeeded in 2852ms:[0m
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-fFrBwAR1' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-36PdWoTE' (errno=Operation not permitted)
diff --git a/python/src/dotfiles_setup/hook_selfcheck.py b/python/src/dotfiles_setup/hook_selfcheck.py
index 93565b79..9366f49d 100644
--- a/python/src/dotfiles_setup/hook_selfcheck.py
+++ b/python/src/dotfiles_setup/hook_selfcheck.py
@@ -43,7 +43,7 @@ import sys
 import tempfile
 from pathlib import Path
 
-from dotfiles_setup import hook_guard
+from dotfiles_setup import hook_guard, process_env
 
 _PROBE_TIMEOUT_S = 60.0
 
@@ -477,15 +477,21 @@ def _worktree_fixture(tmp: Path, env: dict[str, str]) -> tuple[Path, Path, Path]
     The sibling is the a8d7baf5 shape (``<tmp>/repo.worktrees/lane``): it
     EXISTS and is REGISTERED, so a guard can only deny it for its location.
     Raises :class:`subprocess.CalledProcessError` when git cannot build it.
+
+    The fixture's git ignores global/system config and hooks: a host-wide hook
+    (hk's ``hook.hk-*`` in ``~/.gitconfig``) must not be able to reject the
+    fixture commit and turn both arms red for a reason unrelated to the guard.
     """
+    env = {**env, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
     main = tmp / "repo"
     managed = main / ".claude" / "worktrees" / "lane"
     sibling = tmp / "repo.worktrees" / "lane"
     main.mkdir()
-    ident = ["-c", "user.name=selfcheck", "-c", "user.email=selfcheck@invalid"]
+    cfg = ["-c", "user.name=selfcheck", "-c", "user.email=selfcheck@invalid"]
+    cfg += ["-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}"]
     for args in (
         ["init", "-b", "main"],
-        [*ident, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "x"],
+        [*cfg, "commit", "--allow-empty", "-m", "x"],
         ["worktree", "add", "-b", "managed", str(managed)],
         ["worktree", "add", "-b", "sibling", str(sibling)],
     ):
@@ -511,37 +517,12 @@ def _enterworktree(path: Path, cwd: Path) -> str:
     )
 
 
-def check_worktree_guard_endtoend(project_root: Path, wrapper: str) -> list[str]:
-    """Drive EnterWorktree through the REAL wrapper: deny, path allow, name allow.
-
-    Matcher membership alone cannot detect a dispatcher that ignores the tool.
-    The deny arm targets an existing REGISTERED sibling worktree and the path
-    arm an existing registered managed one, on a real temp repo, so a guard
-    that denies every ``path=`` fails the allow arm and one that allows every
-    ``path=`` fails the deny arm. The payload ``cwd`` anchors the guard to that
-    repo; ``CLAUDE_PROJECT_DIR`` stays explicit for a linked-worktree selfcheck.
-    """
+def _worktree_path_arm_failures(
+    denied: subprocess.CompletedProcess[str],
+    path_allowed: subprocess.CompletedProcess[str],
+) -> list[str]:
+    """Judge the sibling-deny and managed-allow ``path=`` arms."""
     failures: list[str] = []
-    # Inherited Git-local state (a hook's GIT_DIR) would aim git at another repo.
-    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
-    env["CLAUDE_PROJECT_DIR"] = str(project_root)
-    with tempfile.TemporaryDirectory(prefix="dotfiles-worktree-guard-") as tmp:
-        try:
-            main, managed, sibling = _worktree_fixture(Path(tmp).resolve(), env)
-        except (OSError, subprocess.SubprocessError) as exc:
-            return [f"EnterWorktree selfcheck could not build its git fixture: {exc}"]
-        denied = _run(
-            [_SYSTEM_BASH, wrapper],
-            stdin=_enterworktree(sibling, main),
-            cwd=project_root,
-            env=env,
-        )
-        path_allowed = _run(
-            [_SYSTEM_BASH, wrapper],
-            stdin=_enterworktree(managed, main),
-            cwd=project_root,
-            env=env,
-        )
     if denied.returncode != 0:
         failures.append(
             f"pretooluse wrapper exited {denied.returncode} on a sibling "
@@ -572,7 +553,47 @@ def check_worktree_guard_endtoend(project_root: Path, wrapper: str) -> list[str]
             ".claude/worktrees — the #1606 guard denies every path. "
             f"stdout={path_allowed.stdout.strip()!r}"
         )
+    return failures
+
 
+def check_worktree_guard_endtoend(project_root: Path, wrapper: str) -> list[str]:
+    """Drive EnterWorktree through the REAL wrapper: deny, path allow, name allow.
+
+    Matcher membership alone cannot detect a dispatcher that ignores the tool.
+    The deny arm targets an existing REGISTERED sibling worktree and the path
+    arm an existing registered managed one, on a real temp repo, so a guard
+    that denies every ``path=`` fails the allow arm and one that allows every
+    ``path=`` fails the deny arm. The payload ``cwd`` anchors the guard to that
+    repo; ``CLAUDE_PROJECT_DIR`` stays explicit for a linked-worktree selfcheck.
+    """
+    failures: list[str] = []
+    # Inherited Git-LOCAL state (a hook's GIT_DIR) would aim git at another
+    # repo; strip exactly the set git names, keeping config isolation such as
+    # GIT_CONFIG_GLOBAL (the fixture pins its own config isolation).
+    try:
+        local = process_env.git_local_env_names()
+    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
+        return [f"EnterWorktree selfcheck could not list git-local env vars: {exc}"]
+    env = {k: v for k, v in os.environ.items() if k not in local}
+    env["CLAUDE_PROJECT_DIR"] = str(project_root)
+    with tempfile.TemporaryDirectory(prefix="dotfiles-worktree-guard-") as tmp:
+        try:
+            main, managed, sibling = _worktree_fixture(Path(tmp).resolve(), env)
+        except (OSError, subprocess.SubprocessError) as exc:
+            return [f"EnterWorktree selfcheck could not build its git fixture: {exc}"]
+        denied = _run(
+            [_SYSTEM_BASH, wrapper],
+            stdin=_enterworktree(sibling, main),
+            cwd=project_root,
+            env=env,
+        )
+        path_allowed = _run(
+            [_SYSTEM_BASH, wrapper],
+            stdin=_enterworktree(managed, main),
+            cwd=project_root,
+            env=env,
+        )
+    failures.extend(_worktree_path_arm_failures(denied, path_allowed))
     allowed = _run(
         [_SYSTEM_BASH, wrapper],
         stdin=json.dumps(
diff --git a/tests/test_hook_selfcheck.py b/tests/test_hook_selfcheck.py
index f99abf3e..75e9a9b0 100644
--- a/tests/test_hook_selfcheck.py
+++ b/tests/test_hook_selfcheck.py
@@ -512,6 +512,49 @@ def test_worktree_guard_endtoend_passes_on_real_repo() -> None:
     assert hook_selfcheck.check_worktree_guard_endtoend(_REPO, wrapper) == []
 
 
+def test_worktree_guard_endtoend_ignores_host_git_hooks(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """A host-wide REJECTING pre-commit must not reach the selfcheck's fixture.
+
+    The hostile config is both ``GIT_CONFIG_GLOBAL`` and ``$HOME/.gitconfig``,
+    so stripping every ``GIT_*`` variable (falling back to HOME) and keeping
+    the inherited global config both let it run. Control arm: the same config
+    really does reject a commit in an ordinary repo.
+    """
+    hooks = tmp_path / "hooks"
+    hooks.mkdir()
+    pre_commit = hooks / "pre-commit"
+    pre_commit.write_text("#!/bin/sh\necho host-hook-rejected >&2\nexit 1\n")
+    pre_commit.chmod(0o755)
+    home = tmp_path / "home"
+    home.mkdir()
+    hostile = home / ".gitconfig"
+    hostile.write_text(
+        "[user]\n\tname = T\n\temail = t@example.com\n"
+        f"[core]\n\thooksPath = {hooks}\n"
+        '[hook "reject"]\n\tcommand = exit 1\n\tevent = pre-commit\n'
+    )
+    monkeypatch.setenv("HOME", str(home))
+    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
+
+    control = tmp_path / "control"
+    control.mkdir()
+    subprocess.run(["git", "init", "-q"], cwd=control, check=True, timeout=10)
+    rejected = subprocess.run(
+        ["git", "commit", "--allow-empty", "-m", "x"],
+        cwd=control,
+        capture_output=True,
+        text=True,
+        check=False,
+        timeout=10,
+    )
+    assert rejected.returncode != 0, rejected.stdout + rejected.stderr
+
+    wrapper = str(_REPO / hook_selfcheck.PRETOOLUSE_WRAPPER)
+    assert hook_selfcheck.check_worktree_guard_endtoend(_REPO, wrapper) == []
+
+
 def test_missing_instructions_loaded_fails(tmp_path: Path) -> None:
     """#917: the InstructionsLoaded observer hook must stay wired.
 

--- guidance paths ---
../coord-28f1a8f7/python/AGENTS.md
../coord-28f1a8f7/python/src/dotfiles_setup/AGENTS.md
../coord-28f1a8f7/tests/AGENTS.md
../coord-28f1a8f7/.devcontainer/AGENTS.md
../coord-28f1a8f7/.github/workflows/AGENTS.md
../coord-28f1a8f7/AGENTS.md
../agent-ac4032eba1703a858/python/AGENTS.md
../agent-ac4032eba1703a858/python/src/dotfiles_setup/AGENTS.md
../agent-ac4032eba1703a858/tests/AGENTS.md
../agent-ac4032eba1703a858/.devcontainer/AGENTS.md
../agent-ac4032eba1703a858/.github/workflows/AGENTS.md
../agent-ac4032eba1703a858/AGENTS.md
../codegen-default-group/python/AGENTS.md
../codegen-default-group/python/src/dotfiles_setup/AGENTS.md
../codegen-default-group/tests/AGENTS.md
../codegen-default-group/.devcontainer/AGENTS.md
../codegen-default-group/.github/workflows/AGENTS.md
../codegen-default-group/AGENTS.md
../handoff-automation-research/python/AGENTS.md
../handoff-automation-research/python/src/dotfiles_setup/AGENTS.md
../handoff-automation-research/tests/AGENTS.md
../handoff-automation-research/.devcontainer/AGENTS.md
../handoff-automation-research/.github/workflows/AGENTS.md
../handoff-automation-research/AGENTS.md
../L1-docs-rules/python/AGENTS.md
../L1-docs-rules/python/src/dotfiles_setup/AGENTS.md
../L1-docs-rules/tests/AGENTS.md
../L1-docs-rules/.devcontainer/AGENTS.md
../L1-docs-rules/.github/workflows/AGENTS.md
../L1-docs-rules/AGENTS.md
../L0-urgent-code/python/AGENTS.md
../L0-urgent-code/python/src/dotfiles_setup/AGENTS.md
../L0-urgent-code/tests/AGENTS.md
../L0-urgent-code/.devcontainer/AGENTS.md
../L0-urgent-code/.github/workflows/AGENTS.md
../L0-urgent-code/AGENTS.md
../fix-1606/python/AGENTS.md
../fix-1606/python/src/dotfiles_setup/AGENTS.md
../fix-1606/tests/AGENTS.md
../fix-1606/.devcontainer/AGENTS.md
../fix-1606/.github/workflows/AGENTS.md
../fix-1606/AGENTS.md

--- fallback configuration ---

--- memory lookup ---
104:- Do not use unscoped `pkill -f`, and do not launch sessions into sibling worktrees then call `EnterWorktree`; both caused cross-lane disruption/blocking. Start the session in its pre-created worktree and target only its processes. [Task 1][Task 3]
1739:- Fresh worktrees lack `.venv`, so a guard-changing lane cannot certify from that weaker surface. `kb-arms` mutates tracked files and is not a gate; use it separately and never inspect a tree mid-run. [Task 2]
1748:scope: Apply explicit tool/actor/output contracts and verify isolated worktree mutations without bypassing checkout guards.
1760:- Agent, general-purpose, Edit, worktree isolation, realpath, kb-settings-guard, MAIN_ORIGINAL, WORKTREE_EDIT, main checkout, mise.toml
1768:- Verify worktree edits with target content, `realpath`, target `git status --short`, and sibling checkout content/status. The linked worktree edit stayed local; a delegated lane cannot write the main checkout because `kb-settings-guard` protects its settings surface. [Task 1]
3017:- Scope lane/process checks to this project/worktree: combine `git worktree list --porcelain`, per-PID `lsof -a -p PID -d cwd`, guarded empty-PID handling, and argv fallback. Liveness requires artifact/rc inspection and two samples; machine-wide `pgrep` is unsafe. #688/U-G11 tracks `kb_setup.lanes` / `mise run kb-lanes`. [Task 3]

[35m[3mexec[0m[0m
[1m/bin/zsh -lc "printf '\\n--- instructions ---\\n'; for p in AGENTS.md python/AGENTS.md python/src/dotfiles_setup/AGENTS.md tests/AGENTS.md .claude/rules/graphify-first.md .claude/rules/real-integration-evidence.md .claude/rules/do-not.md; do echo \"--- "'$p"; nl -ba "$p"; done; printf '"'\\n--- overrides ---\\n'; find . -name AGENTS.override.md -o -name AGENTS.md; printf '\\n--- review skill ---\\n'; cat /Users/rmanaloto/.codex/plugins/cache/claude-plugins-official/mattpocock-skills/1.2.3/skills/engineering/code-review/SKILL.md"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[32m succeeded in 2931ms:[0m

--- instructions ---
--- AGENTS.md
     1	<!-- Generated: 2026-04-07 | Updated: 2026-06-28 -->
     2	
     3	# Dotfiles — macOS Developer Environment
     4	
     5	Chezmoi-managed dotfiles with devcontainer support targeting AMD64 Linux
     6	containers on macOS ARM hosts. Two build types:
     7	
     8	1. **Local linting** (hk + mise): `mise install && mise run lint`
     9	2. **Docker env image** (CI/CD → ghcr.io): published from `main` via GHA
    10	
    11	Registry: `ghcr.io/ray-manaloto/dotfiles-devcontainer`. CI: `ci.yml` (thin
    12	caller) → lint → contract-preflight → `changes` → reusable `build-publish.yml`
    13	(plan → base-prep → p2996-prep → dev-prep → build → smoke-test → dev-tag →
    14	manifest; the middle six fan out per leg — arch + a non-blocking
    15	runner-validation leg, #676/#736) → `ci-gate`;
    16	`promote` retags on main; benchmark + Trivy async in `image-analysis.yml`.
    17	
    18	## Quick Start
    19	
    20	```bash
    21	mise install                                 # Install all tools
    22	mise run lint                                # Run lint checks (hk under a hard timeout)
    23	mise run up / down                           # Bring up / tear down devcontainer (.devcontainer/AGENTS.md)
    24	mise run sync / ship / automerge / land -- <PR#>  # Gated PR loop; automerge = bot PRs (pr-workflow)
    25	mise run verify-container-latest             # Gate: container on latest + base
    26	uv run --project python pytest tests/ -x -q  # Run tests (see python/AGENTS.md)
    27	mise run verify                              # Structured verification contracts
    28	mise run pin-actions                         # Verify GHA actions are SHA-pinned
    29	mise run lint-docs                           # Validate agent documentation (agnix)
    30	mise run lock -- "<backend/name>"            # Re-lock ONE host tool (bare = destructive, #370)
    31	mise run lock-shared -- "<name>"             # shared.toml tools: linux-resolved, NOT host (#790)
    32	mise run lock-image                          # Regenerate the IMAGE locks (#650; routes to amd64)
    33	mise run schema-vendor-refresh               # Re-vendor upstream files (#1026)
    34	mise run plugin-health / dependency-currency # Doctor LIVE checks (rc=verdict)
    35	```
    36	
    37	The devloop is `mise run up` → work inside the container → `mise run down`
    38	(the official `@devcontainers/cli`, pinned in `mise.toml`) — not the legacy
    39	`dotfiles-setup docker up`/`down` subcommands.
    40	
    41	## Key Files
    42	
    43	| File | Purpose |
    44	|------|---------|
    45	| `mise.toml` + `.config/mise/conf.d/shared.toml` | Host tool versions + tasks; the tools shared with the image (hk, pkl, linters, python, uv, chezmoi, bun) live in the exact-pinned shared fragment both host and image merge (#160 T5) |
    46	| `mise.lock` | Locked tool versions for reproducible installs |
    47	| `mise.local.toml` | Gitignored per-clone overrides (e.g., `BASE_IMAGE`). See `mise.local.toml.example` |
    48	| `hk.pkl` | Project git hook config; imports `hk-common.pkl`; enforces `no_lint_skip`, `require_pipefail`, `bash_logic_budget`, `claude_md_import_stub`, `claude_agents_md_pairs` |
    49	| `hk-common.pkl` | Shared step definitions (hygiene, safety, security, typos) reused by `hk.pkl` and `hk-image.pkl` |
    50	| `hk-image.pkl` | Image-only hook config for devcontainer validation |
    51	| `docker-bake.hcl` | BuildKit bake config (`dev`, `dev-load` build targets + `base`/`p2996-cache` CI stages); `IMAGE_REF` consolidates registry+image |
    52	| `renovate.json` · `currency.toml` · `rule-sync.toml` | Declarative sets: Renovate deps; deep-tracked tools (`mise run tool-currency`); the cross-repo shared set (`mise run rule-sync`, #354) |
    53	| `AGENTS.md` | Agent-agnostic project instructions (this file) |
    54	| `CLAUDE.md` | Thin `@AGENTS.md` import stub for Claude Code |
    55	
    56	## Subdirectories
    57	
    58	`.devcontainer/`, `.github/workflows/`, `python/` and `tests/` each carry their
    59	own `AGENTS.md` (guaranteed by `claude_agents_md_pairs`) — read that, not a
    60	table here. Two exceptions worth knowing: `.claude/` has its own `CLAUDE.md` and
    61	is exempt from the stub check (so is `docs/research/kb/raw/**`, #1486); `home/`
    62	(chezmoi templates) lost its `AGENTS.md` in #80 deliberately.
    63	
    64	## Two Build Types
    65	
    66	- **Build Type 1 — Local Linting**: Tools managed by mise. Git hooks via hk.
    67	  Run `mise install` then `mise run lint` before every commit.
    68	- **Build Type 2 — Docker Image**: Multi-stage Dockerfile at `.devcontainer/Dockerfile`.
    69	  BuildKit bake via `docker-bake.hcl`. **CI-only** — never `mise run build` or
    70	  `docker buildx bake dev-load` locally; the base image is published to
    71	  `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` from `main` via GHA.
    72	  Local devcontainer flows pull `:dev` and build only the thin host-user overlay.
    73	
    74	## Split hk Architecture
    75	
    76	Three pkl files with a shared-import pattern:
    77	
    78	- `hk-common.pkl` — shared step definitions exported as `Mapping<String, Config.Step>`
    79	- `hk.pkl` — project pre-commit config; imports and spreads `hk-common.pkl` groups
    80	- `hk-image.pkl` — Docker image checks; imports and spreads `hk-common.pkl` groups
    81	
    82	hk's default pklr backend evaluates the import/spread config identically
    83	to the pkl CLI, and its pkl-eval cache is content-hashed — edits need no
    84	manual cache clearing.
    85	
    86	## Testing
    87	
    88	Commands are in **Quick Start** above; append a path for a single file
    89	(`uv run --project python pytest tests/test_audit.py -x -q`).
    90	
    91	Structured verification via `python/verification/suites.toml` runs as CI
    92	`contract-preflight`. The `mise run verify` gate is **distinct
    93	from** `mise run lint` — some contracts (e.g.,
    94	`build.no-stderr-suppression`) only run through the verify CLI. Run both
    95	locally before pushing Dockerfile changes.
    96	
    97	<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
    98	
    99	## Agent Instructions
   100	
   101	### Policies (read before working)
   102	
   103	- **Zero-skip**: Resolve every warning/error. Suppress only with explicit user
   104	  approval. See `.claude/rules/zero-skip-policy.md`.
   105	- **Zero inline suppressions**: The `no_lint_skip` hk step rejects
   106	  `noqa`/`type: ignore`/`pylint: disable`/`nosec` in Python source.
   107	- **MCP lanes**: required by a third-party plugin/skill → allowed; our work →
   108	  API or `mcp2cli` first. See `.claude/rules/research-doc-sources.md`.
   109	- **CI-local parity**: Every CI lint step has a local hk equivalent; every
   110	  hk tool is in `mise.toml`. See `.claude/rules/ci-local-parity.md`.
   111	- **Research before fixing**: Check docs, changelogs, and issues; don't guess at CI failures.
   112	- **Research coverage**: Use all five research sources via native `fnox exec`;
   113	  see `python/src/dotfiles_setup/AGENTS.md` for the receipt contract.
   114	- Follow `.claude/rules/graphify-first.md` and `.claude/rules/real-integration-evidence.md`.
   115	- **Bound long-running commands**: Run the lint gate via `mise run lint`
   116	  (hk under a hard timeout; hk has none) — never wait blind or capture via
   117	  `| tail` (masks exit codes). See `.claude/rules/long-running-command-hangs.md`.
   118	- **Clarify before acting**: On ambiguous, multi-path, or irreversible
   119	  work, ask (with a recommended option) until sure; proceed directly on
   120	  clear low-risk tasks. See `.claude/rules/clarify-before-acting.md`.
   121	- **Local validation first**: Run `mise run lint`, `pytest`, AND
   122	  `mise run verify` locally before pushing.
   123	- **Research existing tools/services before custom code (HARD GATE)**: prefer an
   124	  existing tool / native feature / CLI / service (`gh` auto-merge, `chezmoi.os`)
   125	  over ANY homegrown code (last resort + justification). See `.claude/rules/use-tool-builtins.md`.
   126	- **Chezmoi is devcontainer-only on this Mac**: `chezmoi apply`/`update`
   127	  blocked on host (enforced by `.claude/settings.json` deny rules); read-only ok.
   128	- **Notepad enforcement**: Agents write findings to notepad during work, not at session end. See `.claude/rules/notepad-enforcement.md`.
   129	- **Agent artifact conventions**: Use standard `.agent/` paths, no ad-hoc
   130	  directories. See `.claude/rules/agent-artifact-conventions.md`.
   131	- **Zero-bash logic**: Non-trivial logic (env detection, tool config,
   132	  validation) lives in `python/`. Bash is restricted to thin check/smoke
   133	  wrappers in `scripts/`.
   134	
   135	### Validate before committing
   136	
   137	```bash
   138	mise run lint                                 # Lint gate (hk under a hard timeout) — then proceed
   139	uv run --project python pytest tests/ -x -q   # All tests pass — then proceed
   140	mise run verify                     # Verification contracts pass — then proceed
   141	```
   142	
   143	Commit only after all three exit 0 — validate locally, don't push to test in CI.
   144	Before advancing to the next task or claiming done, EVERY applicable check must be green with evidence: `.claude/rules/verify-before-advancing.md`.
   145	
   146	### Tool management
   147	
   148	- **mise-first**: All tools declared in `mise.toml` (or the merged
   149	  `.config/mise/conf.d/shared.toml`); use mise binaries directly, not npx.
   150	- **uv for Python**: `uv run --project python` for all Python commands.
   151	  **Never `uv run --directory python`** — the latter changes cwd and
   152	  breaks relative test paths.
   153	- **hk for hooks**: `mise run lint` for the read-only lint gate (≡ CI;
   154	  guard redirects raw hk); `mise run fmt` (`hk fix`) to auto-fix. It fixes
   155	  modified AND untracked files, staged or not, but leaves the fixes UNSTAGED
   156	  (hk 2.3, measured 2026-09-27; only the pre-commit hook auto-stages):
   157	  review, then `git add` AFTER `mise run fmt`.
   158	
   159	### Devcontainer success criteria (durable, do NOT silently drop)
   160	Gated by `mise run verify-local`. Sessions touching `.devcontainer/` or `mise.toml [tasks.up]` MUST preserve all three. Mechanism: `.devcontainer/AGENTS.md`. Research: `docs/research/runs/research-20260407-ssh-devcontainer/report.md`.
   161	
   162	| Req | Criterion | Gate |
   163	|---|---|---|
   164	| **R1 inbound** | `ssh ${USER}@localhost -p $(mise run ssh-port)` opens a shell, no password | `mise run verify-ssh-inbound` |
   165	| **R2 outbound** | `ssh -T git@github.com` inside container → "successfully authenticated" | smoke tier 3 |
   166	| **R3 arch** | container reports the requested arch (`x86_64`/`amd64` default; `aarch64`/`arm64` via `MISE_ENV=arm64` + its local profile) on `uname -m`, `arch`, manifest | `mise run verify-arch` |
   167	
   168	### Environment variables
   169	
   170	| Variable | Value | Purpose |
   171	|----------|-------|---------|
   172	| `HK_MISE` | `1` | Enable mise integration for hk |
   173	| `CONTAINER_REGISTRY` | `ghcr.io` | Docker registry (use `CONTAINER_REGISTRY`, not `REGISTRY` — avoids HCL collision) |
   174	| `DEVCONTAINER_USER` | `${localEnv:USER}` (fallback: `devcontainer`) | Container user (UID 1000); passed through from host `USER` via `devcontainer.json`. |
   175	| `DEVCONTAINER_SSH_PORT` | derived | Host-side port for R1 inbound ssh (container sshd is hardcoded `2222`). **Unset by default (#677)** — derived per workspace+architecture so two clones and two arches never collide; `mise run ssh-port` / `names`. Pin per-clone via `mise.local.toml`. Detail: `.devcontainer/AGENTS.md`. |
   176	| `DOTFILES_PLATFORM` | pinned in `mise.toml` `[env]` | **The one platform parameter** (#673). Every `--platform` site resolves from it; unset, it falls back to the host's native triple. `no_platform_literals` rejects a literal elsewhere |
   177	| `DOCKER_DEFAULT_PLATFORM` | `{{ env.DOTFILES_PLATFORM }}` | Task-scoped export of the above — what docker itself reads |
   178	| `PLATFORM` | per-leg in CI (#676) | bake's HCL variable, overridden by the same-named env var. **All three content hashes read it too**, so a leg's build and its cache tags cannot describe different architectures |
   179	
   180	### Docker Runtimes
   181	
   182	**Docker Desktop is the supported runtime as of 2026-04-09** (verified
   183	via `docker context ls` → `desktop-linux *`). It exposes
   184	`/run/host-services/ssh-auth.sock` natively, which R2 outbound depends
   185	on. Colima lacks an equivalent (`abiosoft/colima#1330`, `#942`) — do
   186	NOT switch context without validating R2 on the target runtime.
   187	Colima is a deferred alternative tracked in issue #78. Research:
   188	`docs/research/runs/research-20260409c-dockerdesktop-ssh/report.md`.
   189	Benchmarks: `docs/research/trail/findings/docker-benchmarks/`.
   190	
   191	### Do not
   192	
   193	See `.claude/rules/do-not.md` for the authoritative list of project
   194	invariants; machine-enforced items also live in `hk.pkl`.
--- python/AGENTS.md
     1	<!-- Parent: ../AGENTS.md -->
     2	<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->
     3	
     4	# python/ — Python Package (dotfiles_setup)
     5	
     6	## Purpose
     7	
     8	Python package providing the `dotfiles-setup` CLI for bootstrap
     9	orchestration, structured verification contracts, and typed configuration.
    10	Requires **Python 3.14**.
    11	
    12	## Key Files
    13	
    14	| File | Purpose |
    15	|------|---------|
    16	| `pyproject.toml` | Package metadata; includes `[tool.ty]` section for ty type checker |
    17	| `uv.lock` | Reproducible dependency lockfile (managed by uv) |
    18	| `requirements.txt` | Legacy; prefer `uv sync` |
    19	| `src/dotfiles_setup/` | Package source; `DotfilesConfig(BaseSettings)` centralizes 16 env vars via Pydantic config DI |
    20	| `verification/suites.toml` | Structured verification contracts run by `dotfiles-setup verify run` (CI: contract-preflight) |
    21	
    22	## Working in this directory
    23	
    24	- **Dependency manager:** `uv`. Always `uv run --project python ...`
    25	  from the repo root. **Never `uv run --directory python`** — that
    26	  changes cwd and breaks relative test paths.
    27	- **Type checker:** `ty` (configured in `[tool.ty]`). Runs as part of
    28	  hk pre-commit.
    29	- **Linter/formatter:** `ruff` (configured in `pyproject.toml`). Runs
    30	  as part of hk pre-commit.
    31	- **Zero inline suppressions:** `noqa`, `type: ignore`, `pylint: disable`,
    32	  `nosec` are rejected by the `no_lint_skip` hk step.
    33	- **Comma-except (PEP 758, py3.14):** `except A, B:` (no `as`) catches
    34	  BOTH `A` and `B` — parens are optional style, and ruff actively strips
    35	  them to the no-paren form (verified: it does not rebind `B`, the old
    36	  Python-2 trap). Parens are still REQUIRED to bind multiple types:
    37	  `except (A, B) as e:`. See `feedback_python2_comma_except` memory.
    38	
    39	## Testing
    40	
    41	```bash
    42	uv run --project python pytest tests/ -x -q                # Run the test suite
    43	uv run --project python pytest tests/test_audit.py -x -q   # Single file
    44	```
    45	
    46	Tests live at repo-root `tests/`, **not** `python/tests/`. They cover
    47	config, audit, bootstrap, ghcr, image smoke, and shell integration.
    48	
    49	## Verification contracts
    50	
    51	`dotfiles-setup verify run` executes contracts defined in
    52	`verification/suites.toml`. This gate is **distinct** from `mise run
    53	lint` — some contracts (e.g., `build.no-stderr-suppression`)
    54	only run through the verify CLI. Run both locally before pushing
    55	Dockerfile changes.
    56	
    57	Two engine defaults bind every contract you write (#299):
    58	
    59	- **`paths_required` defaults to `true`** — a declared path that no longer
    60	  exists FAILS the suite, for every handler, enforced in `run_suite` before
    61	  dispatch. Opt out with an explicit `paths_required = false`. Without this,
    62	  *partial* path loss is silent: handlers resolve paths through
    63	  `_resolve_paths`, which drops what is gone, so a suite naming two files
    64	  keeps passing on the strength of the one that survives.
    65	- **Bare `tokens` is a UNION** (combined text): a token in ANY listed file
    66	  satisfies the contract for all of them. Use **`per_path_tokens`** to state
    67	  which file must carry which token — otherwise a contract has no opinion
    68	  about the files it names (`build.path-includes-mise-shims` named a file that
    69	  stopped wiring PATH and stayed green ~3.5 months).
    70	- **A single-path `require_tokens` suite MUST use `per_path_tokens`** (#397,
    71	  gated by `dotfiles-setup token-audit`). With one path the two forms mean the
    72	  same thing, but only `per_path_tokens` is read by the uniqueness audit — the
    73	  bare form silently exempts the suite. Ask the audit's question yourself when
    74	  adding a token: **how many places in that file match it?** More than one and
    75	  a stand-in can satisfy it. 33 of 33 tail rebindings closed a LIVE hole, and
    76	  in **11** of them the sole stand-in was a **comment** — so a file's own
    77	  documentation can satisfy a contract about its wiring.
    78	
    79	Contracts use handler types like `policy_doc` (references a doc file)
    80	and `regex_forbid` (pattern-based rejection). Note: static contract
    81	substring matches false-positive on prefixed ENV vars (e.g.,
    82	`CARGO_HOME=` matches `MISE_CARGO_HOME=`); prefer leading-space anchors
    83	or `regex_forbid` handlers. See `feedback_forbid_tokens_substring_fragile`.
    84	
    85	## Serialization: route every call through `codec` (#675)
    86	
    87	`msgspec` is the project's model system (#669). **Never call it directly** —
    88	use `dotfiles_setup.codec.encode` / `.decode`. Machine-enforced by ruff
    89	**TID251**, whose ban list covers all **14** msgspec entry points that accept a
    90	conversion hook (enumerated from the library, not hand-written: `Encoder`/
    91	`Decoder`, `convert` and `to_builtins` are the ones a from-memory list misses).
    92	`codec.py` carries the only per-file allowance.
    93	
    94	The reason is that msgspec's hooks are **per-call keyword arguments**, not a
    95	global registration — so a direct call works fine while carrying its own copy of
    96	the conversion table, and the copies drift. `pathlib.Path` is unsupported in
    97	**both** directions, and the decode half is the quiet one: it raises only
    98	because the annotation says `Path`, so a field annotated `str` accepts the value
    99	and hands you a string that behaves like a path until something calls `.parent`.
   100	
   101	Teach it a new type with `codec.register(T, encode=…, decode=…)` — both
   102	directions, because a half-registration encodes cleanly and loses the type at
   103	read time in another process. Never add a branch to the hook itself.
   104	
   105	**Scope: OUR serialization only** (Ray, 2026-09-30). A third-party library's own
   106	models — e.g. githubkit's pydantic response models — are allowed at that
   107	library's boundary; the `codec` rule governs the types and encodings we define.
   108	
   109	## Generated models and enums (#1329)
   110	
   111	Models and enums are **generated, never hand-written** (R16/D23):
   112	`schemas/<name>.schema.json` → a `[tool.datamodel-codegen]` job in
   113	`pyproject.toml` → `src/dotfiles_setup/generated/<name>.py`. Edit the schema,
   114	run `mise run codegen`, commit both. `mise run codegen-check` (hk
   115	`codegen_check`) fails on a hand edit, an unregenerated schema change, or a
   116	module in `generated/` that no job writes. The generator is the exact pin in
   117	the `codegen` dependency group, run `--locked`, never a PATH copy.
   118	
   119	## Dependencies
   120	
   121	Key packages: `msgspec` (models + serialization — via `codec` only, above),
   122	`pydantic` (config; leaving the tree in #683), `python-debian` (deb822 parsing
   123	for `apt_repo`; Ubuntu ships the same code as `python3-debian`), `pytest`
   124	(testing). Full lockfile at `uv.lock`.
   125	
   126	<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
--- python/src/dotfiles_setup/AGENTS.md
     1	# Research fetcher instructions
     2	
     3	For a live research request, use the strict five-provider receipt. Create a
     4	Last30Days plan whose `subqueries` list names only the active sources relevant
     5	to the question; payment-required or failed sources must remain visible as a
     6	failed receipt, never silently count as evidence.
     7	
     8	Run `fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C <dotfiles-checkout> run research-fanout -- QUERY --repo OWNER/REPO --strict-five --request-id TURN_ID --last30days-plan PLAN.json --out OUT_DIR`.
     9	The native `fnox exec` process receives only the existing Exa and Firecrawl
    10	keys from that profile. Fnox resolves its Doppler token internally with
    11	`env = false`.
    12	Use the native profile for secret injection, keep key values out of output,
    13	and verify availability inside that process rather than inferring it from an
    14	unset inherited environment variable.
    15	
    16	Treat `strict-five pass` and the same-turn manifest as the machine receipt,
    17	then verify material claims against primary documentation or source. GitHub
    18	issues, discussions, and releases are separate arms; empty results need their
    19	same-source control. If a required arm fails, report the exact route and
    20	`RESEARCH INCOMPLETE:` rather than claiming comprehensive research.
--- tests/AGENTS.md
     1	<!-- Parent: ../AGENTS.md -->
     2	<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->
     3	
     4	# tests/ — Pytest + Bats Test Suite
     5	
     6	## Purpose
     7	
     8	Repo-root-level test suite. Tests live here (not under `python/tests/`)
     9	because they exercise the repo as a whole, not just the python package.
    10	
    11	## Key Files
    12	
    13	The per-file index lives in `tests/TEST-INDEX.md` — read it when you need to
    14	know what a given test file covers, or before adding one.
    15	
    16	It is split out because agnix **AGM-003** caps an `AGENTS.md` at 12,000 chars
    17	for **Windsurf** compatibility (real and vendor-documented:
    18	<https://docs.windsurf.com/windsurf/cascade/memories> — "Limited to 12,000
    19	characters per file"; `AGENTS.md` is "processed by the same Rules engine").
    20	It is referenced, NOT `@import`ed: agnix rejects `@import` in an `AGENTS.md`
    21	(Claude-only syntax in an agent-agnostic file) and `claude_md_import_stub`
    22	requires every non-`.claude/` `CLAUDE.md` be solely `@AGENTS.md`. So the index
    23	is on-demand reference — which is what it should be anyway.
    24	
    25	Collected counts drift fast, so measure rather than quote them:
    26	`uv run --project python pytest tests/ --collect-only -q`. Default runs
    27	deselect the gated exec tests — `image_exec` (`mise run smoke-exec`, needs
    28	Docker + the `:dev` image) and `codex_exec` (`mise run codex-lane-e2e`,
    29	spawns the real `codex` CLI and **costs credits**); inspect one with
    30	`-m <marker> --collect-only`. Bats scenarios live under `infra/`.
    31	
    32	## Running tests
    33	
    34	```bash
    35	# Full pytest suite (from repo root):
    36	uv run --project python pytest tests/ -x -q
    37	
    38	# Single file:
    39	uv run --project python pytest tests/test_audit.py -x -q
    40	
    41	# Single test by nodeid:
    42	uv run --project python pytest tests/test_config.py::test_container_paths -x -q
    43	
    44	# Bats tests (require bats-core):
    45	bats tests/infra/
    46	```
    47	
    48	**Always `--project python`**, never `--directory python` — `--directory`
    49	changes cwd and breaks `Path(__file__).parent.parent` resolution in the
    50	test fixtures.
    51	
    52	## What a good test is here
    53	
    54	Tests verify behavior through a **public interface** — an exported function,
    55	a CLI's rc and output, a generated script's real execution — never through
    56	implementation details. Code can change entirely; the test shouldn't. The tell
    57	for an implementation-coupled test is that it breaks under a refactor while
    58	behavior hasn't changed.
    59	
    60	Three anti-patterns have already cost this repo real bugs. All are **silent
    61	false negatives**: they surface as a green suite, never as a failure, so only
    62	a deliberate probe finds them.
    63	
    64	- **Tautological** — the assertion recomputes the expected value the way the
    65	  code does, so it passes by construction and can never disagree with the
    66	  code. Expected values must come from an **independent source of truth**: a
    67	  known-good literal, a worked example, the real artifact.
    68	- **A probe with no control arm** — a check that can only pass is not a check.
    69	  Pin the FAIL direction next to the pass: tier-1 identity really fails on a
    70	  wrong hash, tier-3 on a wrong ref, and every `_inert_masked` case is paired
    71	  with a recall pin. A 2026-07-15 hook probe "passed" while its control proved
    72	  the hook had never fired at all.
    73	- **Both arms, one axis** — you pinned the true and the false branch of the
    74	  condition you changed, and stopped. That is not coverage: enumerate every
    75	  axis the condition *interacts with*, which is derivable with no judgement —
    76	  **the axes are the union of the function's own parameters and every subject
    77	  field read by any predicate it calls** (for `classify()`, that is its
    78	  parameters plus every `Node` field its predicates read). The `classifier_axes`
    79	  gate derives this for you — but only for **same-module predicates called by
    80	  bare name**; for an imported or method predicate it is blind, and you carry
    81	  the rule yourself. When the table gains a cell, add the axis; **never edit an expected value to make a test pass**,
    82	  which converts an independent expectation into a transcription of behaviour.
    83	  When deleting the fix breaks only the arm you just wrote, test space and fix
    84	  space are the same size — the condition under which an unenumerated
    85	  neighbouring cell exists — so enumerate the axes before calling it covered.
    86	  Keep mutation testing: the narrow blast radius is a fact about your axis
    87	  enumeration, not about the mutation
    88	  (`docs/research/kb/reports/session-20260806-review-loop-reflection.md`).
    89	
    90	## Mocking
    91	
    92	Mock at **system boundaries only** — the network (GHCR, `gh`, release feeds),
    93	Docker, the clock, the filesystem where `tmp_path` won't do. Never mock our
    94	own modules, internal collaborators, or anything we control: that couples the
    95	test to structure and is exactly how the implementation-coupled tell appears.
    96	
    97	At a boundary, prefer **injecting** the dependency over constructing it inside
    98	the function. `gcc_sha`'s injected fetcher and `hook_guard`'s pure `decide()`
    99	are the pattern already in use here — the seam is a parameter, so the test
   100	substitutes a value and needs no patching at all.
   101	
   102	## Working in this directory
   103	
   104	- **Imports from `python/src/`:** tests add
   105	  `python/src` to `sys.path` at module import. New tests should follow
   106	  the same pattern rather than requiring `pip install -e`.
   107	- **Zero inline suppressions:** `noqa`, `type: ignore`, `pylint: disable`,
   108	  `nosec` are rejected by the `no_lint_skip` hk step — applies to test
   109	  files too.
   110	- **Subprocess usage:** `test_audit.py` and `test_shell_integration.py`
   111	  shell out. Use absolute paths (`Path(__file__).parent.parent.absolute()`)
   112	  so tests pass regardless of pytest invocation cwd.
   113	- Beyond base-OS tools every environment has (`git`, `sh`/`bash`) and the runners themselves (`mise`, `uv`), a test may shell out only to a tool pinned in `.config/mise/conf.d/shared.toml` (host, image and CI all install it, e.g. `jq`); any other binary gives a Mac-only pass.
   114	- **Parametrize over hardcoding:** `test_bootstrap.py` and
   115	  `test_shell_integration.py` use `@pytest.mark.parametrize` over tool
   116	  name lists. Add new tools to those lists rather than copying tests.
   117	- **Named constants for magic numbers:** `test_image_smoke.py` uses
   118	  `_PLAIN_BYTES_VALUE = 512` etc. rather than inline literals.
   119	
   120	## CI integration
   121	
   122	- `contract-preflight` job runs `uv run --project python pytest tests/
   123	  -x -q` as a blocking gate.
   124	- `smoke-test` job runs the image smoke check separately (not pytest).
   125	- Test failures must be investigated, not suppressed. See
   126	  `.claude/rules/zero-skip-policy.md`.
   127	
   128	<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
--- .claude/rules/graphify-first.md
     1	# Graphify First
     2	
     3	Before broad source search, run `mise run graphify-health`.
     4	
     5	- `fresh`: use `mise run graphify-query -- "<question>"` and cite returned
     6	  source paths.
     7	- `missing`, `stale`, `corrupt`, version drift, warnings, or truncation: say the
     8	  graph is unavailable and fall back to source. Never translate these states to
     9	  an empty or complete answer. A `stale` graph names the fix in its own detail
    10	  line: `mise run graphify-rebuild`.
    11	- **Always the mise tasks, never a bare `graphify` on `PATH`.** Query with
    12	  `mise run graphify-query`, rebuild with `mise run graphify-rebuild` — never
    13	  `graphify query`/`graphify update` directly.
    14	- Use `mise run graphify-check` for read-only currency diagnosis plus a typed
    15	  health line; it resolves the PATH binary from the ambient agent-shell PATH
    16	  captured at SessionStart, not from the uv venv. Use `mise run
    17	  graphify-upgrade` when package/skills and graph must move together.
    18	- `permissions.deny` blocks any Bash string containing `graphify label`, even
    19	  inside a quoted grep; search for that phrase with the Grep tool instead.
    20	
    21	## What `fresh` means
    22	
    23	`_staleness_problem` decides it from two independent sources: Git says what
    24	changed after `built_at_commit` — a field **graphify itself** writes from HEAD
    25	at export time — while `graphify-out/manifest.json` says which relative paths
    26	Graphify scanned. Equality with HEAD is immediately fresh. Otherwise a
    27	manifest-listed path is stale for any change status; an unlisted path is stale
    28	only when newly added with an extension already present in the manifest. A
    29	modified or deleted unlisted path stays outside the corpus even when its
    30	extension matches a scanned file.
    31	
    32	⚠️ **Ancestry is deliberately not the test.** This repo squash-merges, so a graph
    33	built on a PR branch records a commit that never enters main's history — the
    34	2026-08-31 graph's `b75fa3b` has six commits unreachable from HEAD and no branch
    35	contains it. An "is it an ancestor" check would report `stale` on nearly every
    36	graph: the mirror of the defect. Git compares the two endpoint trees instead;
    37	if the build commit is unknown to Git, health fails closed as `stale`.
    38	
    39	A graph carrying no `built_at_commit` is `stale` too. The pinned runtime always
    40	writes it, so its absence means the bytes did not come from that runtime — and
    41	silence is what this axis exists to end. A missing or unreadable manifest and
    42	an unknown build commit are also `stale`. Uncommitted edits are out of scope:
    43	this answers "what committed corpus changed since the build", not "is the worktree
    44	dirty".
    45	
    46	## Nothing records WHICH graphify built the graph
    47	
    48	`graphify` on bare `PATH` resolves the **user-global** pin
    49	(`~/.config/mise/config.toml`, outside this repo's review); the mise tasks
    50	resolve **this repo's locked version** (`python/uv.lock`), which
    51	`graphify_health`'s `version drift` check compares against. `mise run
    52	pin-parity` binds every repository-owned pin site; the SessionStart doctor's
    53	offline check names the user-global fix when the PATH binary drifts from the
    54	lock.
    55	
    56	Health reads the graphify installed in the *checking* process. Nothing records
    57	which binary *built* the graph bytes, so a graph rebuilt by a drifted PATH
    58	binary (a bare `graphify update .`) is indistinguishable from one built by the
    59	pin.
    60	
    61	So the guarantee here is **procedural, not enforced**: always run
    62	`mise run graphify-query`/`graphify-rebuild`, never the bare binary, and
    63	`graphify-first.md`'s `version drift`/`stale` states only ever catch the
    64	*checking* process itself drifting (a broken `uv` env, a bad `uv.lock`
    65	edit) — not a graph built by the wrong installed graphify. Never run a
    66	global Graphify binary or installer as a substitute for the project tasks —
    67	the generated skill is reference material, repository tasks are
    68	authoritative, by convention, not by verification.
    69	
    70	A present KB-style build receipt (`graphify-out/build-receipt.json`) is
    71	still verified byte-for-byte when one exists, but its absence is not a
    72	fault: nothing in this repo writes one (that's the knowledge-base's
    73	committed-corpus pipeline; see `_receipt_problem`'s docstring in
    74	`python/src/dotfiles_setup/graphify.py` for why this repo cannot build one
    75	of its own for an on-demand graph).
    76	
    77	For every dependency/session review, check the latest Graphify release and the
    78	project's critical/currency dependencies. Review release notes and source diffs,
    79	record actionable changes, and explicitly record what the graph/source corpus
    80	still cannot answer so the next review compounds knowledge instead of repeating
    81	the same search.
--- .claude/rules/real-integration-evidence.md
     1	# Real Integration Evidence
     2	
     3	Do not use mocks, synthetic subprocesses, or self-authored receipts as the sole
     4	evidence that an integration works.
     5	
     6	Mocks are acceptable only as supplemental unit controls. A completion claim for
     7	an external CLI, hook, credential path, Graphify release, devcontainer, or
     8	cross-repository dependency requires at least one real invocation through the
     9	public project entrypoint plus its real failure/control arm. If that invocation
    10	cannot run, preserve the reason and mark the capability unverified; do not
    11	replace it with a mock and call the work complete.
--- .claude/rules/do-not.md
     1	# Do Not — Project Invariants
     2	
     3	This is the authoritative list of things agents (and humans) must not do
     4	in this repo. Control arms and case history for each entry:
     5	`docs/rules-evidence/do-not.md`.
     6	
     7	1. **Do NOT launch CLion or VS Code from the dock for devcontainer work.**
     8	   macOS GUI processes don't inherit terminal env, so `mise`, `uv`, and
     9	   `$SSH_AUTH_SOCK` are not available to `initializeCommand`
    10	   (`uv run … dotfiles-setup docker initialize-host`), which then fails.
    11	   Terminal only. See
    12	   `.devcontainer/AGENTS.md`.
    13	
    14	2. **Do NOT `mise run build` or `docker buildx bake dev-load` locally.**
    15	   CI-only. Base image is published by `main` workflow.
    16	
    17	3. **Do NOT use raw `docker` CLI for devcontainer lifecycle**
    18	   (`run/exec/stop/rm/build`). Use `@devcontainers/cli` so lifecycle
    19	   hooks run. Raw `docker ps/logs/info` for inspection are fine.
    20	
    21	4. **Do NOT add `2>/dev/null` to the Dockerfile.** The
    22	   `build.no-stderr-suppression` contract rejects it. Let errors be loud.
    23	
    24	5. **Do NOT bulk `git add .`** — previous sessions have left phantom
    25	   state files under `.agent/state/**` that should not be staged.
    26	
    27	6. **Do NOT run `gh run watch` or `gh pr checks --watch`** — guard-denied;
    28	   `--exit-status` has reported 0 prematurely. Read state one-shot:
    29	   `gh run view <id> --json conclusion` / `gh pr checks <n> --json name,bucket`.
    30	
    31	7. **Do NOT switch `docker context` away from `desktop-linux`.** The
    32	   SSH path is Docker-Desktop-only; silent drift caused session
    33	   2026-04-09c's debug goose-chase. See
    34	   `feedback_docker_desktop_runtime.md`.
    35	
    36	8. **Do NOT run `graphify install --project` in this repo either.** Without
    37	   `--project`, graphify mutates `~/.claude`; with it, the `claude` platform
    38	   still writes root `CLAUDE.md` plus settings hooks and the `codex` platform
    39	   writes root `AGENTS.md` plus `.codex/hooks.json`. Use
    40	   `mise run graphify-update`, whose repo-owned copy boundary manages only the
    41	   reviewed skill bytes and stamps. `CLAUDE_CONFIG_DIR` is not containment.
    42	   Never run `graphify hook install` or `graphify --watch`.
    43	
    44	   Only `graphify install --project --platform agents` is skill-only; the
    45	   separate `graphify agents install` subcommand also writes root `AGENTS.md`.
    46	   This repo keeps a smaller `DELIBERATE STUB`; installing either vendor bundle
    47	   would overwrite it. Run installer probes only in a throwaway directory.
    48	
    49	9. **Do NOT commit — or WRITE — onto the default branch. Branch FIRST.** Create
    50	   the branch *before* the first edit, then `mise run ship`. It has happened
    51	   three times, twice straight after `mise run land` (which **leaves you on
    52	   `main`**). Recovery is `git branch <new> && git reset --hard origin/main`;
    53	   uncommitted work carries across a `git checkout -b` untouched.
    54	
    55	   The gate is on the *write*, not the commit: hk is a git-hook system and never
    56	   sees an edit. Ray's standing instruction: *"all work should be on a branch
    57	   that can be on a PR"*.
    58	
    59	   Machine-enforced (#400) in four layers, earliest first: the **PreToolUse
    60	   `branch_guard`** denying `Edit`/`Write`/`NotebookEdit` on a repo file while
    61	   on the default branch (git-ignored paths and anything outside the repo stay
    62	   allowed, so `.agent/`, `mise.local.toml` and the scratchpad are unaffected);
    63	   hk's `no_commit_to_branch` in the **pre-commit** hook (on the Mac host only
    64	   once `hk install --global --mise` has run from this checkout — the doctor's
    65	   `hk-hooks` check reports when it has not; the devcontainer currently installs
    66	   no hk hooks, S27-9); the PreToolUse guard
    67	   denying `--no-verify` / `git commit -n` / a `HK_SKIP_HOOKS=` prefix (**no git
    68	   hook can catch those** — git skips the hook before it exists as a process);
    69	   and a repository **ruleset requiring a PR for `main`** — the only layer an
    70	   agent cannot skip.
    71	
    72	10. **Do NOT write an environment dump into a tracked file.** Not `env`, not
    73	    `printenv`, not `export -p`, not a debug log carrying them. The interactive
    74	    shell holds real credentials, and mise packs the whole delta into
    75	    `__MISE_DIFF` (zlib + base64) — a form **no secret scanner can read**
    76	    (measured: gitleaks 2 → 0, betterleaks 1 → 0). Write a dump to the
    77	    scratchpad and delete it. Gated by `no_env_dump`; see
    78	    `secrets-out-of-the-shell-env.md`.
    79	
    80	11. **Do NOT reach for MCP to solve one of OUR OWN problems.** For anything this
    81	    project builds, calls, or looks up: the tool's CLI or a plain HTTP **API**
    82	    first, then `mcp2cli`, and native registration only as a documented last
    83	    resort. Registering a server for a call a `curl` already makes adds a
    84	    process, a pin, an auth path and a failure mode for nothing.
    85	
    86	    ✅ **NOT a "do not": a third-party plugin or skill that REQUIRES MCP.**
    87	    Enabling one (bundled servers, `claude mcp add`, a project `.mcp.json`) is
    88	    allowed and needs no justification — there the schema tax buys a capability
    89	    we cannot build. The hard ban was relaxed 2026-07-19. **Unsure which case
    90	    you are in? You are in the first one.** See `research-doc-sources.md`
    91	    § "MCP: two lanes".
    92	
    93	## See also
    94	
    95	- `mise-tasks-only.md` — canonical mise tasks over one-off commands (hook-enforced)
    96	- `zero-skip-policy.md` — no warning/error shall be dismissed
    97	- `verify-before-advancing.md` — every applicable check green before the next task
    98	- `probes-need-a-control-arm.md` — a check that can only pass is not a check
    99	- `ci-local-parity.md` — keep local checks in sync with CI
   100	- `clean-git-state.md` — stage all changes before validation
   101	- `use-tool-builtins.md` — prefer tool builtins over homegrown logic
   102	- `research-doc-sources.md` — preference chain for doc fetching
   103	- `notepad-enforcement.md` — agents write findings to notepad as they go
   104	- `agent-artifact-conventions.md` — standard `.agent/` paths

--- overrides ---
./python/AGENTS.md
./python/src/dotfiles_setup/AGENTS.md
./tests/AGENTS.md
./.devcontainer/AGENTS.md
./.github/workflows/AGENTS.md
./AGENTS.md

--- review skill ---
---
name: code-review
description: "Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes: Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/spec asked for?). Runs both reviews in parallel sub-agents and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to \"review since X\"."
---

Two-axis review of the diff between `HEAD` and a fixed point the user supplies:

- **Standards**: does the code conform to this repo's documented coding standards?
- **Spec**: does the code faithfully implement the originating issue / spec?

Both axes run as **parallel sub-agents** so they don't pollute each other's context, then this skill aggregates their findings.

The issue tracker should have been provided to you. If `docs/agents/issue-tracker.md` is missing, tell the user to run `/setup-matt-pocock-skills`.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point (a commit SHA, branch name, tag, `main`, `HEAD~5`, etc.). If they didn't specify one, ask for it.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base). Also note the list of commits via `git log <fixed-point>..HEAD --oneline`.

Before going further, confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail here, not inside two parallel sub-agents.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in the commit messages (`#123`, `Closes #45`, GitLab `!67`, etc.), fetched via the workflow in `docs/agents/issue-tracker.md`.
2. A path the user passed as an argument.
3. A spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing is found, ask the user where the spec is. If they say there isn't one, the **Spec** sub-agent will skip and report "no spec available".

### 3. Identify the standards sources

Anything in the repo that documents how code should be written, such as `CODING_STANDARDS.md` or `CONTRIBUTING.md`.

On top of whatever the repo documents, the Standards axis always carries the **smell baseline** below: a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation. Like any standard here, skip anything tooling already enforces.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name**: a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy**: a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change**: one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality**: abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest**: a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

### 4. Spawn both sub-agents in parallel

**Standards sub-agent prompt** should include:

- The full diff command and commit list.
- The list of standards-source files you found in step 3, **plus the smell baseline from step 3** pasted in full (the sub-agent has no other access to it).
- The brief: "Report, per file/hunk where relevant, (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls: documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** should include:

- The diff command and commit list.
- The path or fetched contents of the spec.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec sub-agent and note this in the final report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings, because the two axes are deliberately separate (see _Why two axes_).

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes: that's the reranking the separation exists to prevent.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.

[35m[3mexec[0m[0m
[1m/bin/zsh -lc "cat python/src/dotfiles_setup/AGENTS.md; cat tests/AGENTS.md; sed -n '100,240p' python/AGENTS.md; cat python/src/dotfiles_setup/process_env.py; sed -n '1,200p' python/src/dotfiles_setup/hook_selfcheck.py; sed -n '400,700p' python/src/dotfiles_setup/hook_selfcheck.py; cat .claude/hooks/pretooluse-guard.sh"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[31m exited 1 in 3186ms:[0m
# Research fetcher instructions

For a live research request, use the strict five-provider receipt. Create a
Last30Days plan whose `subqueries` list names only the active sources relevant
to the question; payment-required or failed sources must remain visible as a
failed receipt, never silently count as evidence.

Run `fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C <dotfiles-checkout> run research-fanout -- QUERY --repo OWNER/REPO --strict-five --request-id TURN_ID --last30days-plan PLAN.json --out OUT_DIR`.
The native `fnox exec` process receives only the existing Exa and Firecrawl
keys from that profile. Fnox resolves its Doppler token internally with
`env = false`.
Use the native profile for secret injection, keep key values out of output,
and verify availability inside that process rather than inferring it from an
unset inherited environment variable.

Treat `strict-five pass` and the same-turn manifest as the machine receipt,
then verify material claims against primary documentation or source. GitHub
issues, discussions, and releases are separate arms; empty results need their
same-source control. If a required arm fails, report the exact route and
`RESEARCH INCOMPLETE:` rather than claiming comprehensive research.
<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->

# tests/ — Pytest + Bats Test Suite

## Purpose

Repo-root-level test suite. Tests live here (not under `python/tests/`)
because they exercise the repo as a whole, not just the python package.

## Key Files

The per-file index lives in `tests/TEST-INDEX.md` — read it when you need to
know what a given test file covers, or before adding one.

It is split out because agnix **AGM-003** caps an `AGENTS.md` at 12,000 chars
for **Windsurf** compatibility (real and vendor-documented:
<https://docs.windsurf.com/windsurf/cascade/memories> — "Limited to 12,000
characters per file"; `AGENTS.md` is "processed by the same Rules engine").
It is referenced, NOT `@import`ed: agnix rejects `@import` in an `AGENTS.md`
(Claude-only syntax in an agent-agnostic file) and `claude_md_import_stub`
requires every non-`.claude/` `CLAUDE.md` be solely `@AGENTS.md`. So the index
is on-demand reference — which is what it should be anyway.

Collected counts drift fast, so measure rather than quote them:
`uv run --project python pytest tests/ --collect-only -q`. Default runs
deselect the gated exec tests — `image_exec` (`mise run smoke-exec`, needs
Docker + the `:dev` image) and `codex_exec` (`mise run codex-lane-e2e`,
spawns the real `codex` CLI and **costs credits**); inspect one with
`-m <marker> --collect-only`. Bats scenarios live under `infra/`.

## Running tests

```bash
# Full pytest suite (from repo root):
uv run --project python pytest tests/ -x -q

# Single file:
uv run --project python pytest tests/test_audit.py -x -q

# Single test by nodeid:
uv run --project python pytest tests/test_config.py::test_container_paths -x -q

# Bats tests (require bats-core):
bats tests/infra/
```

**Always `--project python`**, never `--directory python` — `--directory`
changes cwd and breaks `Path(__file__).parent.parent` resolution in the
test fixtures.

## What a good test is here

Tests verify behavior through a **public interface** — an exported function,
a CLI's rc and output, a generated script's real execution — never through
implementation details. Code can change entirely; the test shouldn't. The tell
for an implementation-coupled test is that it breaks under a refactor while
behavior hasn't changed.

Three anti-patterns have already cost this repo real bugs. All are **silent
false negatives**: they surface as a green suite, never as a failure, so only
a deliberate probe finds them.

- **Tautological** — the assertion recomputes the expected value the way the
  code does, so it passes by construction and can never disagree with the
  code. Expected values must come from an **independent source of truth**: a
  known-good literal, a worked example, the real artifact.
- **A probe with no control arm** — a check that can only pass is not a check.
  Pin the FAIL direction next to the pass: tier-1 identity really fails on a
  wrong hash, tier-3 on a wrong ref, and every `_inert_masked` case is paired
  with a recall pin. A 2026-07-15 hook probe "passed" while its control proved
  the hook had never fired at all.
- **Both arms, one axis** — you pinned the true and the false branch of the
  condition you changed, and stopped. That is not coverage: enumerate every
  axis the condition *interacts with*, which is derivable with no judgement —
  **the axes are the union of the function's own parameters and every subject
  field read by any predicate it calls** (for `classify()`, that is its
  parameters plus every `Node` field its predicates read). The `classifier_axes`
  gate derives this for you — but only for **same-module predicates called by
  bare name**; for an imported or method predicate it is blind, and you carry
  the rule yourself. When the table gains a cell, add the axis; **never edit an expected value to make a test pass**,
  which converts an independent expectation into a transcription of behaviour.
  When deleting the fix breaks only the arm you just wrote, test space and fix
  space are the same size — the condition under which an unenumerated
  neighbouring cell exists — so enumerate the axes before calling it covered.
  Keep mutation testing: the narrow blast radius is a fact about your axis
  enumeration, not about the mutation
  (`docs/research/kb/reports/session-20260806-review-loop-reflection.md`).

## Mocking

Mock at **system boundaries only** — the network (GHCR, `gh`, release feeds),
Docker, the clock, the filesystem where `tmp_path` won't do. Never mock our
own modules, internal collaborators, or anything we control: that couples the
test to structure and is exactly how the implementation-coupled tell appears.

At a boundary, prefer **injecting** the dependency over constructing it inside
the function. `gcc_sha`'s injected fetcher and `hook_guard`'s pure `decide()`
are the pattern already in use here — the seam is a parameter, so the test
substitutes a value and needs no patching at all.

## Working in this directory

- **Imports from `python/src/`:** tests add
  `python/src` to `sys.path` at module import. New tests should follow
  the same pattern rather than requiring `pip install -e`.
- **Zero inline suppressions:** `noqa`, `type: ignore`, `pylint: disable`,
  `nosec` are rejected by the `no_lint_skip` hk step — applies to test
  files too.
- **Subprocess usage:** `test_audit.py` and `test_shell_integration.py`
  shell out. Use absolute paths (`Path(__file__).parent.parent.absolute()`)
  so tests pass regardless of pytest invocation cwd.
- Beyond base-OS tools every environment has (`git`, `sh`/`bash`) and the runners themselves (`mise`, `uv`), a test may shell out only to a tool pinned in `.config/mise/conf.d/shared.toml` (host, image and CI all install it, e.g. `jq`); any other binary gives a Mac-only pass.
- **Parametrize over hardcoding:** `test_bootstrap.py` and
  `test_shell_integration.py` use `@pytest.mark.parametrize` over tool
  name lists. Add new tools to those lists rather than copying tests.
- **Named constants for magic numbers:** `test_image_smoke.py` uses
  `_PLAIN_BYTES_VALUE = 512` etc. rather than inline literals.

## CI integration

- `contract-preflight` job runs `uv run --project python pytest tests/
  -x -q` as a blocking gate.
- `smoke-test` job runs the image smoke check separately (not pytest).
- Test failures must be investigated, not suppressed. See
  `.claude/rules/zero-skip-policy.md`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->

Teach it a new type with `codec.register(T, encode=…, decode=…)` — both
directions, because a half-registration encodes cleanly and loses the type at
read time in another process. Never add a branch to the hook itself.

**Scope: OUR serialization only** (Ray, 2026-09-30). A third-party library's own
models — e.g. githubkit's pydantic response models — are allowed at that
library's boundary; the `codec` rule governs the types and encodings we define.

## Generated models and enums (#1329)

Models and enums are **generated, never hand-written** (R16/D23):
`schemas/<name>.schema.json` → a `[tool.datamodel-codegen]` job in
`pyproject.toml` → `src/dotfiles_setup/generated/<name>.py`. Edit the schema,
run `mise run codegen`, commit both. `mise run codegen-check` (hk
`codegen_check`) fails on a hand edit, an unregenerated schema change, or a
module in `generated/` that no job writes. The generator is the exact pin in
the `codegen` dependency group, run `--locked`, never a PATH copy.

## Dependencies

Key packages: `msgspec` (models + serialization — via `codec` only, above),
`pydantic` (config; leaving the tree in #683), `python-debian` (deb822 parsing
for `apt_repo`; Ubuntu ships the same code as `python3-debian`), `pytest`
(testing). Full lockfile at `uv.lock`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
# Copyright (c) 2026 Raymond Manaloto
"""Explicit child-process boundaries for credentials and Git-local state.

Git deliberately exports repository-local variables to hooks. Those variables
must not escape into a test suite that creates disposable repositories: a
fixture's ``git init`` or ``git config`` can otherwise mutate the repository
whose pre-push hook launched pytest.

The isolation boundary derives Git's complete local-variable set from Git
itself, removes credentials, and changes only the child environment. It never
prints values or mutates its parent process.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from dotfiles_setup.child_env import clean_env

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

GITHUB_TOKEN_NAMES = frozenset({"GH_TOKEN", "GITHUB_TOKEN"})


def command_after_separator(command: Sequence[str]) -> tuple[str, ...]:
    """Normalize argparse ``REMAINDER`` while requiring a real command."""
    normalized = tuple(command[1:] if command and command[0] == "--" else command)
    if not normalized:
        msg = "a command is required after --"
        raise ValueError(msg)
    return normalized


def fnox_command(command: Sequence[str]) -> tuple[str, ...]:
    """Return the non-interactive fnox command for one bounded child."""
    return ("fnox", "exec", "--non-interactive", "--", *command)


def fnox_parent_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Remove stale GitHub-token precedence before fnox resolves its child.

    ``gh`` prefers ``GH_TOKEN`` over ``GITHUB_TOKEN``. A long-lived Desktop
    process can therefore carry an old token which wins over the scoped token
    fnox injects. Provider credentials remain available to fnox; no value is
    inspected or logged.
    """
    source = os.environ if base is None else base
    return {
        name: value for name, value in source.items() if name not in GITHUB_TOKEN_NAMES
    }


def run_with_fnox(command: Sequence[str], *, cwd: Path | None = None) -> int:
    """Run exactly one command with credentials resolved by fnox."""
    completed = subprocess.run(
        fnox_command(command), check=False, cwd=cwd, env=fnox_parent_env()
    )
    return completed.returncode


def git_local_env_names(*, cwd: Path | None = None) -> frozenset[str]:
    """Ask the installed Git which variables carry repository-local state.

    Git owns this list. Deriving it avoids a hand-maintained list that silently
    misses a variable added by a later Git release. Discovery itself cannot
    inherit Git-local state, and failure is closed because a partial scrub is
    the destructive state.
    """
    discovery_env = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    result = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=discovery_env,
    )
    if result.returncode != 0:
        msg = f"git rev-parse --local-env-vars failed rc={result.returncode}"
        raise RuntimeError(msg)
    names = frozenset(line for line in result.stdout.splitlines() if line)
    if not names:
        msg = "git rev-parse --local-env-vars returned no variables"
        raise RuntimeError(msg)
    return names


def git_isolated_env(
    base: Mapping[str, str] | None = None,
    *,
    local_names: frozenset[str] | None = None,
) -> dict[str, str]:
    """Return a credential-free environment without Git-local variables."""
    source = dict(os.environ if base is None else base)
    names = git_local_env_names() if local_names is None else local_names
    cleaned = clean_env(source)
    return {name: value for name, value in cleaned.items() if name not in names}


def run_git_isolated(command: Sequence[str], *, cwd: Path | None = None) -> int:
    """Run a test command unable to inherit its caller's Git repository."""
    completed = subprocess.run(command, check=False, cwd=cwd, env=git_isolated_env())
    return completed.returncode
# Copyright (c) 2026 Raymond Manaloto
"""Host-side hook self-check: exercise the WIRED hook entrypoints end-to-end.

``tests/test_hook_guard.py`` calls :func:`hook_guard.decide` *in process* — it
never drives the actual path the harness uses: ``.claude/settings.json`` ->
``scripts/pretooluse-guard.sh`` (the fail-open wrapper) -> ``dotfiles-setup
hook pretooluse``. This module closes that gap. It:

- asserts ``.claude/settings.json`` wires the project hooks
  (:data:`_SETTINGS_WIRING`): the ONE merged PreToolUse hook (the deny guard
  for ``Bash``, ``AskUserQuestion``, ``Edit``, ``Write`` and ``NotebookEdit``
  plus the ``EnterWorktree`` path guard and graphify's nudge for ``Grep``,
  ``Read`` and ``Glob``), the SessionStart
  web-setup bootstrap, the InstructionsLoaded observer, and the PostToolUse
  mise-config-context dispatcher, plus the unscoped SubagentStart contract and
  its parent-side PostToolUse/``Agent`` half — five events in all;
- drives the REAL PreToolUse wrapper end-to-end — a denied command must DENY,
  an allowed one must stay silent, and a graphify-only tool must never deny;
- drives the REAL subagent-contract module entrypoint end-to-end — start must
  inject every clause of the file-role contract, PostToolUse must remind the
  parent only for the ``Agent`` tool, and there must be NO SubagentStop
  response (a turn-forcing regression);
- ``bash -n`` syntax-checks the wired hook scripts (a parse error in
  ``web-setup.sh`` would brick a cold Claude-web session before the first Bash
  tool call).

``dotfiles-setup hook selfcheck`` runs it, and ``mise run ship`` / ``mise run
land`` gate on it (an always-run core gate, like lint/pytest/verify) so a hook
regression is caught automatically.

Each ``check_*`` helper returns a list of failure strings (empty == pass) so
the checks are unit-testable without capturing stdout;
:func:`hook_selfcheck_main` runs them all, prints a PASS/FAIL line per check,
and returns 0 iff every check passed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotfiles_setup import hook_guard, process_env

_PROBE_TIMEOUT_S = 60.0

# A representative denied command (has a canonical mise task) and an allowed
# one (a plain diagnostic). Driven through the REAL wrapper end-to-end; the
# full rule battery lives in tests/test_hook_guard.py.
_DENIED_SAMPLE = "gh pr create --fill"
_DENIED_HINT = "mise run ship"
_ALLOWED_SAMPLE = "git status --porcelain"

#: Public: the tests drive this wrapper and the off-root arm by name.
PRETOOLUSE_WRAPPER = "scripts/pretooluse-guard.sh"
_WEB_SETUP = "scripts/web-setup.sh"
#: The shell the wired hook names (never PATH `bash`, a mise shim on this host).
_SYSTEM_BASH = "/bin/bash"
_HOOK_SCRIPTS = (PRETOOLUSE_WRAPPER, _WEB_SETUP)

# Each settings.json hook event -> (command substrings that MUST appear in its
# wired command(s), required matchers or None). Keeps the project hooks from
# silently drifting out of .claude/settings.json (the wiring the end-to-end
# check then exercises).
#
# PreToolUse must stay scoped, and to ALL FIVE tools it guards: `Bash` (the
# mise-tasks-only redirects), `AskUserQuestion` (the ask-quality standard, Ray
# 2026-08-02 — see dotfiles_setup.ask_quality), and `Edit`/`Write`/
# `NotebookEdit` (the write-time default-branch guard, #400 — see
# dotfiles_setup.branch_guard). Each is asserted separately, because the
# matcher is one alternation string: a check that only looked for "Bash" would
# keep passing if AskUserQuestion were dropped from it, and the guard would go
# silently absent for that tool exactly as #343 did for off-root Bash.
#
# The assertion is exact ALTERNATION-TOKEN membership, never substring
# containment — "Edit" is a substring of "NotebookEdit", so a containment test
# let a matcher that dropped bare `Edit` report fully wired. See
# check_settings_wiring.
#
# The same PreToolUse entry also carries graphify's nudge (`Grep`, `Read`,
# `Glob`, plus `Bash`): one process per tool call instead of two uv chains
# (host-load review 2026-10-02). Its command must name `/bin/bash`, never a bare
# `bash` — on this host `bash` resolves to a mise shim that alone costs ~200 ms
# on every tool call in every session.
#
# There is deliberately NO SessionEnd row: the command-audit scan it carried was
# the largest attributable host load (seven concurrent ~814 MB scans) and is
# on demand now (`mise run command-audit`).
#
# SessionStart carries the two host-only checkups that no in-tree gate can do:
# the offline tool-currency drift check, and the #418 project doctor (declared
# setup vs this host). Both are silent when healthy and both always exit 0, so
# neither can disrupt a session; asserting them here is what keeps them from
# quietly falling out of settings.json, which is the only place they are wired.
SUBAGENT_CONTRACT_MODE = "subagent-contract"
#: The tools the deny guard decides on, then the ones only graphify nudges.
_GUARDED_TOOLS = ("Bash", "AskUserQuestion", "Edit", "Write", "NotebookEdit")
_GRAPHIFY_TOOLS = ("Grep", "Read", "Glob")
# EnterWorktree routes separately: its repo anchor is the payload `cwd`, falling
# back to the wrapper's project root when the payload carries none.
_WORKTREE_TOOLS = ("EnterWorktree",)
_SUBAGENT_CONTRACT_COMMAND = (
    f"python -m dotfiles_setup.hook_selfcheck {SUBAGENT_CONTRACT_MODE}"
)
_SETTINGS_WIRING: tuple[tuple[str, tuple[str, ...], tuple[str, ...] | None], ...] = (
    # All five guarded tools are required, not just the two the guard started
    # with. The three file-modifying ones route to `branch_guard` (#400); with
    # only ("Bash", "AskUserQuestion") required, narrowing the live matcher
    # back would silently kill the write-time default-branch gate while ship
    # and land both stayed green — a check that can only pass
    # (`probes-need-a-control-arm.md`).
    (
        "PreToolUse",
        (f"{_SYSTEM_BASH} ", PRETOOLUSE_WRAPPER),
        (*_GUARDED_TOOLS, *_GRAPHIFY_TOOLS, *_WORKTREE_TOOLS),
    ),
    (
        "SessionStart",
        (_WEB_SETUP, "CLAUDE_CODE_REMOTE", "run tool-currency-check", "run doctor"),
        None,
    ),
    # #917: the InstructionsLoaded observer. `None` matchers are deliberate,
    # not an oversight — a matcher would scope the hook to particular
    # `load_reason` values (session_start, path_glob_match, ...) and lose the
    # baseline the never-fired report depends on: every reason is wanted.
    (
        "InstructionsLoaded",
        ("python -m dotfiles_setup.instructions_observer",),
        None,
    ),
    # #919: the mise-config-context write-trigger dispatcher.
    # `tests/test_mise_config_context.py`'s
    # `test_settings_wires_this_hook_without_depending_on_a_mise_task` already
    # asserts this wiring (since PR #902) — this row's genuine delta is
    # PRECISION, not novelty: that test's matcher check is
    # `any("Write" in m and "Edit" in m for m in matchers)`, substring
    # containment, and `"Edit" in "NotebookEdit"` is True — so it cannot see a
    # matcher narrowed to `Write|NotebookEdit` (bare `Edit` dropped). This
    # row's alternation-token check (below) can. The matcher requirement is
    # scoped, not None: an unscoped PostToolUse would fire the dispatcher
    # after EVERY tool call, including Bash and Read, not just the three
    # write-shaped tools it exists for.
    (
        "PostToolUse",
        ("dotfiles-setup mise-config-context",),
        ("Edit", "Write", "NotebookEdit"),
    ),
    # #994: matcher omission is load-bearing. SubagentStart matchers filter on
    # agent TYPE, so any matcher would silently exclude a future built-in,
    # custom, or plugin-scoped delegate from this contract. `None` here only
    # means "this row asserts no matcher token"; UNSCOPED-ness is a separate
    # assertion, in _UNSCOPED_EVENTS below, because a `None` row is satisfied
    # by ANY matcher and so cannot see a narrowing (measured: narrowing this
    # to a single agent type left the whole suite green).
    #
    # The parent-side half is a PostToolUse row scoped to `Agent`, NOT a
    # SubagentStop hook — see build_subagent_contract_output for why re-adding
    # one is a regression. Its matcher requirement is real: an unscoped
    # PostToolUse would fire the reminder after every tool call.
    ("SubagentStart", (_SUBAGENT_CONTRACT_COMMAND,), None),
    ("PostToolUse", (_SUBAGENT_CONTRACT_COMMAND,), ("Agent",)),
)

#: Events that must NOT be wired at all, with the reason shown on failure.
#: The module already returns nothing for SubagentStop, but that only makes
#: THIS command inert there — it does not stop someone wiring a different one.
#: The forbid is at the wiring layer because that is where the regression lands.
_FORBIDDEN_EVENTS: tuple[tuple[str, str], ...] = (
    (
        "SubagentStop",
        (
            "it forces a model turn on EVERY delegation (measured: four "
            "continuations on one run) and the forced reply can displace the "
            "report the parent consumes — use the PostToolUse/Agent hook instead"
        ),
    ),
)

#: Events whose hook MUST stay unscoped. A `_SETTINGS_WIRING` row with `None`
#: matchers asserts nothing about the matcher, so without this a narrowed
#: matcher — the exact silent-exclusion failure the comment above warns about —
#: passes every check.
_UNSCOPED_EVENTS: tuple[tuple[str, str], ...] = (
    ("SubagentStart", _SUBAGENT_CONTRACT_COMMAND),
)

# Claude Code runs hooks "in the current directory", not the project root, and
# exports ${CLAUDE_PROJECT_DIR} so a hook can find its own repo anyway. A hook
# command that names a bare relative path therefore resolves against whatever
# directory the session happens to be in — and silently fails open there, since
# a non-zero non-2 PreToolUse exit is a NON-BLOCKING error that lets the tool
# call proceed. That is #343: 125 denied Bash calls executed unchecked while the
# cwd was a sibling repo. Every wired command must anchor its paths.
_PROJECT_DIR_ANCHOR = "CLAUDE_PROJECT_DIR"


def _run(
    failures.extend(check_offroot_arm(project_root, wrapper))
    return failures


def _ask_payload(*, cited: bool) -> str:
    """A single-select AskUserQuestion that differs ONLY in whether it cites.

    Both arms are otherwise compliant (recommendation first, PRO:/CON: on every
    option), so a difference in the wrapper's verdict can only come from the
    citation rule — the control arm for the deny.
    """
    where = "per `mise.toml`" if cited else "which do you prefer"
    return json.dumps(
        {
            "tool_name": "AskUserQuestion",
            "tool_input": {
                "questions": [
                    {
                        "question": f"Selfcheck probe — {where}?",
                        "header": "Probe",
                        "multiSelect": False,
                        "options": [
                            {
                                "label": "A (Recommended)",
                                "description": "PRO: a. CON: b.",
                            },
                            {"label": "B", "description": "PRO: c. CON: d."},
                        ],
                    }
                ]
            },
        }
    )


def check_ask_quality_endtoend(project_root: Path, wrapper: str) -> list[str]:
    """Drive the ask-quality gate through the REAL wrapper (deny + allow).

    The wiring check proves ``AskUserQuestion`` is in the matcher; this proves
    the guard actually decides on it. Without the allow arm the deny would be
    indistinguishable from a gate that denies every ask.
    """
    failures: list[str] = []

    denied = _run(
        [_SYSTEM_BASH, wrapper], stdin=_ask_payload(cited=False), cwd=project_root
    )
    if denied.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {denied.returncode} on a non-compliant "
            f"AskUserQuestion (must exit 0): {denied.stderr.strip()}"
        )
    elif '"permissionDecision": "deny"' not in denied.stdout:
        failures.append(
            "pretooluse wrapper did not DENY an uncited AskUserQuestion — the "
            f"ask-quality gate is not reachable. stdout={denied.stdout.strip()!r}"
        )

    allowed = _run(
        [_SYSTEM_BASH, wrapper], stdin=_ask_payload(cited=True), cwd=project_root
    )
    if allowed.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {allowed.returncode} on a compliant "
            f"AskUserQuestion: {allowed.stderr.strip()}"
        )
    elif allowed.stdout.strip():
        failures.append(
            "pretooluse wrapper was not silent on a COMPLIANT AskUserQuestion — "
            f"the gate denies every ask: {allowed.stdout.strip()!r}"
        )
    return failures


def _worktree_fixture(tmp: Path, env: dict[str, str]) -> tuple[Path, Path, Path]:
    """A real repo with one managed and one sibling linked worktree (#1606).

    The sibling is the a8d7baf5 shape (``<tmp>/repo.worktrees/lane``): it
    EXISTS and is REGISTERED, so a guard can only deny it for its location.
    Raises :class:`subprocess.CalledProcessError` when git cannot build it.

    The fixture's git ignores global/system config and hooks: a host-wide hook
    (hk's ``hook.hk-*`` in ``~/.gitconfig``) must not be able to reject the
    fixture commit and turn both arms red for a reason unrelated to the guard.
    """
    env = {**env, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    main = tmp / "repo"
    managed = main / ".claude" / "worktrees" / "lane"
    sibling = tmp / "repo.worktrees" / "lane"
    main.mkdir()
    cfg = ["-c", "user.name=selfcheck", "-c", "user.email=selfcheck@invalid"]
    cfg += ["-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}"]
    for args in (
        ["init", "-b", "main"],
        [*cfg, "commit", "--allow-empty", "-m", "x"],
        ["worktree", "add", "-b", "managed", str(managed)],
        ["worktree", "add", "-b", "sibling", str(sibling)],
    ):
        subprocess.run(
            ["git", *args],
            cwd=main,
            env=env,
            capture_output=True,
            check=True,
            timeout=_PROBE_TIMEOUT_S,
        )
    return main, managed, sibling


def _enterworktree(path: Path, cwd: Path) -> str:
    """An EnterWorktree payload whose session cwd anchors the guard's repo."""
    return json.dumps(
        {
            "tool_name": "EnterWorktree",
            "tool_input": {"path": str(path)},
            "cwd": str(cwd),
        }
    )


def _worktree_path_arm_failures(
    denied: subprocess.CompletedProcess[str],
    path_allowed: subprocess.CompletedProcess[str],
) -> list[str]:
    """Judge the sibling-deny and managed-allow ``path=`` arms."""
    failures: list[str] = []
    if denied.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {denied.returncode} on a sibling "
            f"EnterWorktree path (must exit 0): {denied.stderr.strip()}"
        )
    elif '"permissionDecision": "deny"' not in denied.stdout:
        failures.append(
            "pretooluse wrapper did not DENY a registered sibling worktree outside "
            ".claude/worktrees — the #1606 guard is not reachable or allows "
            f"every path. stdout={denied.stdout.strip()!r}"
        )
    elif "must be an existing worktree under" not in denied.stdout:
        failures.append(
            "pretooluse EnterWorktree deny was not the LOCATION deny (did "
            f"verification fail?): {denied.stdout.strip()!r}"
        )
    elif "#1606" not in denied.stdout or "EnterWorktree name=" not in denied.stdout:
        failures.append("pretooluse EnterWorktree deny lost its #1606 name= redirect")

    if path_allowed.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {path_allowed.returncode} on a managed "
            f"EnterWorktree path: {path_allowed.stderr.strip()}"
        )
    elif path_allowed.stdout.strip():
        failures.append(
            "pretooluse wrapper was not silent on a registered worktree under "
            ".claude/worktrees — the #1606 guard denies every path. "
            f"stdout={path_allowed.stdout.strip()!r}"
        )
    return failures


def check_worktree_guard_endtoend(project_root: Path, wrapper: str) -> list[str]:
    """Drive EnterWorktree through the REAL wrapper: deny, path allow, name allow.

    Matcher membership alone cannot detect a dispatcher that ignores the tool.
    The deny arm targets an existing REGISTERED sibling worktree and the path
    arm an existing registered managed one, on a real temp repo, so a guard
    that denies every ``path=`` fails the allow arm and one that allows every
    ``path=`` fails the deny arm. The payload ``cwd`` anchors the guard to that
    repo; ``CLAUDE_PROJECT_DIR`` stays explicit for a linked-worktree selfcheck.
    """
    failures: list[str] = []
    # Inherited Git-LOCAL state (a hook's GIT_DIR) would aim git at another
    # repo; strip exactly the set git names, keeping config isolation such as
    # GIT_CONFIG_GLOBAL (the fixture pins its own config isolation).
    try:
        local = process_env.git_local_env_names()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return [f"EnterWorktree selfcheck could not list git-local env vars: {exc}"]
    env = {k: v for k, v in os.environ.items() if k not in local}
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    with tempfile.TemporaryDirectory(prefix="dotfiles-worktree-guard-") as tmp:
        try:
            main, managed, sibling = _worktree_fixture(Path(tmp).resolve(), env)
        except (OSError, subprocess.SubprocessError) as exc:
            return [f"EnterWorktree selfcheck could not build its git fixture: {exc}"]
        denied = _run(
            [_SYSTEM_BASH, wrapper],
            stdin=_enterworktree(sibling, main),
            cwd=project_root,
            env=env,
        )
        path_allowed = _run(
            [_SYSTEM_BASH, wrapper],
            stdin=_enterworktree(managed, main),
            cwd=project_root,
            env=env,
        )
    failures.extend(_worktree_path_arm_failures(denied, path_allowed))
    allowed = _run(
        [_SYSTEM_BASH, wrapper],
        stdin=json.dumps(
            {"tool_name": "EnterWorktree", "tool_input": {"name": "selfcheck"}}
        ),
        cwd=project_root,
        env=env,
    )
    if allowed.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {allowed.returncode} on EnterWorktree "
            f"name=: {allowed.stderr.strip()}"
        )
    elif allowed.stdout.strip():
        failures.append(
            "pretooluse wrapper was not silent on EnterWorktree name=: "
            f"{allowed.stdout.strip()!r}"
        )
    return failures


def _offroot_env(project_root: Path) -> dict[str, str]:
    """The hook's environment with this process's own venv resolution removed.

    Drops ``VIRTUAL_ENV`` and every ``PATH`` entry inside the project, so the
    wrapper must resolve the guard through ``$CLAUDE_PROJECT_DIR`` rather than
    through a venv it happened to inherit. See :func:`check_offroot_arm`.

    ``UV_PROJECT_ENVIRONMENT`` is deliberately PRESERVED, and that is a
    correction, not an oversight. Stripping it broke the devcontainer, where
    ``devcontainer.json`` sets it to ``/home/$USER/.venvs/dotfiles-python`` on
    purpose: without it uv falls back to ``<project>/.venv`` inside the
    bind-mounted workspace and dies on the host's stale copy (``failed to remove
    directory python/.venv/lib: Directory not empty``). It is environment
    CONFIGURATION the container requires, not an answer leaked from this
    process — the distinction the first version got wrong, and only the
    in-container `sync-full` gate caught it.

    Bound worth stating: where that variable already points at a ready venv
    holding ``dotfiles-setup``, this arm verifies the wrapper is REACHABLE
    off-root rather than that it re-resolves its project. The resolution half is
    covered on the host, and statically everywhere by :func:`_unanchored_hooks`.
    """
    root = str(project_root)
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep) if p and not p.startswith(root)
    )
    env[_PROJECT_DIR_ANCHOR] = root
    return env


def check_offroot_arm(project_root: Path, wrapper: str) -> list[str]:
    """The same deny, driven from a cwd that is NOT the project root (#343).

    Both arms above run with ``cwd=project_root``, so they could not observe the
    defect that let 125 denied commands through: hooks execute in the session's
    current directory, and every relative path in the chain — settings.json's
    script path AND the wrapper's own ``uv run --project python`` — resolved
    against a sibling repo instead. Measured before the fix: rc=127 from the
    script path, rc=2 from the uv project. Both exit non-zero-non-2, which
    PreToolUse treats as a non-blocking error, so the call proceeded.

    A throwaway directory is the foreign cwd rather than a sibling clone: the
    arm must hold on any machine, including CI, where no second repo exists.

    THE ENVIRONMENT IS SCRUBBED, and that is what makes the arm able to fail.
    The first version inherited ``os.environ`` wholesale — and since the
    selfcheck itself runs under ``uv run --project python``, the child already
    had the project's venv on ``PATH``. So ``dotfiles-setup`` resolved no matter
    what the wrapper asked for, and the probe passed with the defect
    reintroduced. A probe that inherits a pre-resolved answer cannot observe the
    resolution it is testing.
    """
    with tempfile.TemporaryDirectory() as foreign:
        result = _run(
            [_SYSTEM_BASH, wrapper],
            stdin=_hook_payload(_DENIED_SAMPLE),
            cwd=Path(foreign),
            env=_offroot_env(project_root),
        )
    if result.returncode != 0:
        return [
            (
                f"pretooluse wrapper exited {result.returncode} when run from a "
                f"foreign cwd — it must resolve via ${_PROJECT_DIR_ANCHOR}: "
                f"{result.stderr.strip()}"
            )
        ]
    if '"permissionDecision": "deny"' not in result.stdout:
        return [
            (
                f"pretooluse wrapper did not DENY {_DENIED_SAMPLE!r} when run from "
                f"a foreign cwd — the guard fails OPEN off-root (#343). "
                f"stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}"
            )
        ]
    return []


def check_guard_decisions() -> list[str]:
    """In-process smoke of :func:`hook_guard.decide` (belt-and-braces)."""
    failures: list[str] = []
    if hook_guard.decide(_DENIED_SAMPLE) is None:
cat: .claude/hooks/pretooluse-guard.sh: No such file or directory

[35m[3mexec[0m[0m
[1m/bin/zsh -lc "cat scripts/pretooluse-guard.sh; sed -n '1,260p' python/src/dotfiles_setup/worktree_guard.py; sed -n '1,150p' tests/test_hook_selfcheck.py; sed -n '400,570p' tests/test_hook_selfcheck.py; sed -n '1,230p' tests/conftest.py; git show -s --format=fuller 865454f9; git --version; git rev-parse --local-env-vars; command -v uv; ls -ld python/.venv python/.venv/bin/python; rg -n 'GIT_TEMPLATE_DIR|GIT_CONFIG_COUNT|GIT_CONFIG_GLOBAL|git_local_env_names|GIT_AUTHOR_DATE|GIT_COMMITTER' python tests scripts hk.pkl .github/workflows .claude/rules"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[32m succeeded in 1465ms:[0m
#!/usr/bin/env bash
# scripts/pretooluse-guard.sh — the ONE per-tool-call PreToolUse hook: the
# mise-tasks-only/ask-quality/branch guard AND graphify's nudge, in a single
# Python process (python/src/dotfiles_setup/hook_dispatch.py). Fail-open shim.
#
# Fast path: the venv's own interpreter, no `uv` resolution per call (two uv
# chains per Bash call were ~1.2 s of process starts, host-load review
# 2026-10-02). `uv run` is the fallback, which also re-syncs a stale venv.
# FAILS OPEN (exit 0 = allow) when neither can run, so a cold Claude-web
# session before web-setup.sh is not bricked by every call being denied.
#
# EVERY PATH IS ANCHORED TO $CLAUDE_PROJECT_DIR, NOT THE CWD (#343): hooks run
# in the session's cwd, and a relative path silently resolved a sibling repo.
# AND EVERY FAIL-OPEN IS COUNTED: one nobody records is indistinguishable from
# enforcement. See .claude/rules/mise-tasks-only.md and issue #343.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-}"
[ -n "$ROOT" ] || ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${DOTFILES_GUARD_FAILOPEN_LOG:-$HOME/.local/state/dotfiles/guard-fail-open.log}"
VENV="${UV_PROJECT_ENVIRONMENT:-$ROOT/python/.venv}"

# Record, then allow — the exit 0 stands whether or not the line was written.
fail_open() {
  mkdir -p -- "$(dirname -- "$LOG")" 2>/dev/null &&
    printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$PWD" >>"$LOG" 2>/dev/null
  exit 0
}

# Builtin read, not $(cat): on this Mac `cat` is a mise shim (~200 ms a call).
# `python -P`: never put the session's cwd on sys.path (a stray json.py there
# would run on every call and fail the guard open).
IFS= read -r -d '' payload || true
if [ -x "$VENV/bin/python" ] &&
  out="$(printf '%s' "$payload" | "$VENV/bin/python" -P -m dotfiles_setup.hook_dispatch "$ROOT")"; then
  printf '%s' "$out"
  exit 0
fi
{ command -v uv && uv python find '>=3.14'; } >/dev/null 2>&1 || fail_open "interpreter-absent"
out="$(printf '%s' "$payload" | uv run --project "$ROOT/python" python -P -m dotfiles_setup.hook_dispatch "$ROOT")" ||
  fail_open "guard-error-rc=$?"
printf '%s' "$out"
# Copyright (c) 2026 Raymond Manaloto
"""Restrict EnterWorktree paths to existing managed worktrees (#1606).

Native ``name=`` creation uses the main checkout's ``.claude/worktrees/``.
The PreToolUse hook applies this location policy in every permission mode.
Only stdlib imports: git runs only when deciding an EnterWorktree path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def handles(tool_name: str) -> bool:
    """Whether this guard decides on the named tool."""
    return tool_name == "EnterWorktree"


def _deny_reason(target: Path, main: Path) -> str:
    checkout = str(main)
    allowed = f"{checkout}/.claude/worktrees"
    return (
        f"#1606: EnterWorktree path={target} must be an existing worktree under "
        f"{allowed}/, strictly inside that directory and registered with this repo. "
        "This location policy applies in every permission mode. "
        f"For NEW worktrees, from the main checkout ({checkout}), use "
        "`EnterWorktree name=<name>`. From inside a worktree session, use "
        f"`EnterWorktree path={allowed}/<name>` for an existing registered worktree, "
        "or ExitWorktree (keep) before creating a NEW worktree with name=."
    )


def _unverified_reason(target: Path, detail: str) -> str:
    """Fail closed when git cannot answer, naming why instead of a location."""
    cause = " ".join(detail.split())[:300] or "git printed no diagnostic"
    return (
        f"#1606: EnterWorktree path={target} was denied because the guard could "
        f"not verify it (fails closed): {cause}. Check the repository with "
        "`git worktree list`; for a NEW worktree, use `EnterWorktree name=<name>` "
        "from the main checkout."
    )


class _VerificationError(Exception):
    """Git could not answer; the guard fails closed and reports this cause."""


def _git(cmd: list[str], anchor: Path) -> str:
    """Run one git query from ``anchor``; any failure is a verification error."""
    try:
        proc = subprocess.run(
            cmd, cwd=anchor, capture_output=True, text=True, check=False, timeout=5
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise _VerificationError(str(exc)) from exc
    if proc.returncode != 0:
        raise _VerificationError(proc.stderr or f"{cmd} exited {proc.returncode}")
    return proc.stdout


def _main_checkout(anchor: Path) -> Path:
    """The main checkout owning ``anchor``'s repository (common dir's parent)."""
    common = _git(["git", "rev-parse", "--git-common-dir"], anchor).strip()
    if not common:
        msg = "git rev-parse --git-common-dir printed nothing"
        raise _VerificationError(msg)
    common_dir = Path(common)
    if not common_dir.is_absolute():
        common_dir = anchor / common_dir
    return common_dir.resolve().parent


def decide(
    tool_input: dict[str, object], project_dir: Path, cwd: Path | None = None
) -> str | None:
    """Require an existing managed worktree; deny paths we cannot verify."""
    path = tool_input.get("path")
    if not isinstance(path, str) or not path:
        return None
    target = Path(path)
    try:
        anchor = (cwd if cwd is not None else project_dir).resolve()
        main = _main_checkout(anchor)
        if not target.is_absolute():
            target = anchor / target
        target = target.resolve()
        allowed = main / ".claude" / "worktrees"
        if target != allowed and target.is_relative_to(allowed) and target.is_dir():
            listing = _git(["git", "worktree", "list", "--porcelain", "-z"], anchor)
            if any(
                Path(record.removeprefix("worktree ")).resolve() == target
                for record in listing.split("\0")
                if record.startswith("worktree ")
            ):
                return None
    except (OSError, ValueError, _VerificationError) as exc:
        return _unverified_reason(target, str(exc))
    return _deny_reason(target, main)
# Copyright (c) 2026 Raymond Manaloto
"""Tests for the host-side hook self-check (dotfiles_setup.hook_selfcheck).

The self-check drives the WIRED hook entrypoints end-to-end; it is the
ship/land ``hook-selfcheck`` gate. Unit tests cover the pure helpers (wiring
parse, JSON extraction, in-process decide smoke); one integration test runs
the whole thing against the real repo so a wiring/wrapper regression fails
the gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import hook_selfcheck

_REPO = Path(__file__).parent.parent
_REAL_SETTINGS = _REPO / ".claude" / "settings.json"


def test_real_settings_wiring_passes() -> None:
    assert hook_selfcheck.check_settings_wiring(_REAL_SETTINGS) == []


def test_guard_decisions_smoke_passes() -> None:
    assert hook_selfcheck.check_guard_decisions() == []


def _wiring(tmp_path: Path, settings: dict) -> list[str]:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(settings))
    return hook_selfcheck.check_settings_wiring(path)


def _hook(matcher: str | None, command: str) -> dict:
    entry: dict[str, object] = {"hooks": [{"type": "command", "command": command}]}
    if matcher is not None:
        entry["matcher"] = matcher
    return entry


_ANCHOR = '"${CLAUDE_PROJECT_DIR:-.}"'


def _full_settings() -> dict:
    """A minimally-complete, passing settings shape for tampering in tests.

    Every command anchors its paths to ``$CLAUDE_PROJECT_DIR`` — hooks run in
    the session's cwd, so the unanchored form silently fails open in a
    cross-repo session (#343).
    """
    return {
        "hooks": {
            "PreToolUse": [
                _hook(
                    "Bash|AskUserQuestion|Edit|Write|NotebookEdit|Grep|Read|Glob|EnterWorktree",
                    f"/bin/bash {_ANCHOR}/scripts/pretooluse-guard.sh",
                )
            ],
            "SessionStart": [
                _hook(
                    "startup|resume",
                    'if [ "$CLAUDE_CODE_REMOTE" = "true" ]; then '
                    f"bash {_ANCHOR}/scripts/web-setup.sh; else "
                    f"mise -C {_ANCHOR} run tool-currency-check; "
                    f"mise -C {_ANCHOR} run doctor; fi",
                )
            ],
            "InstructionsLoaded": [
                _hook(
                    None,
                    f'uv run --project "{_ANCHOR}/python" python -m '
                    "dotfiles_setup.instructions_observer",
                )
            ],
            "PostToolUse": [
                _hook(
                    "Edit|Write|NotebookEdit",
                    f'uv run --project "{_ANCHOR}/python" '
                    "dotfiles-setup mise-config-context",
                ),
                _hook(
                    "Agent",
                    f'uv run --project "{_ANCHOR}/python" python -m '
                    "dotfiles_setup.hook_selfcheck subagent-contract",
                ),
            ],
            "SubagentStart": [
                _hook(
                    None,
                    f'uv run --project "{_ANCHOR}/python" python -m '
                    "dotfiles_setup.hook_selfcheck subagent-contract",
                )
            ],
        }
    }


def test_synthetic_full_settings_passes(tmp_path: Path) -> None:
    assert _wiring(tmp_path, _full_settings()) == []


def test_missing_event_fails(tmp_path: Path) -> None:
    settings = _full_settings()
    del settings["hooks"]["PreToolUse"]
    failures = _wiring(tmp_path, settings)
    assert any("PreToolUse" in f for f in failures)


def test_missing_subagent_start_registration_fails(tmp_path: Path) -> None:
    """The control arm: deleting the start registration must fail selfcheck."""
    settings = _full_settings()
    del settings["hooks"]["SubagentStart"]
    failures = _wiring(tmp_path, settings)
    assert any("SubagentStart" in failure for failure in failures)


def test_missing_agent_posttooluse_registration_fails(tmp_path: Path) -> None:
    """Dropping the parent-side half must fail even though PostToolUse remains.

    The mise-config-context entry still wires PostToolUse, so a check that only
    asked "is this event present?" would stay green with the reminder gone.
    """
    settings = _full_settings()
    settings["hooks"]["PostToolUse"] = [
        entry
        for entry in settings["hooks"]["PostToolUse"]
        if "subagent-contract" not in entry["hooks"][0]["command"]
    ]
    assert settings["hooks"]["PostToolUse"], "fixture must keep the other entry"
    failures = _wiring(tmp_path, settings)
    assert any("PostToolUse" in failure for failure in failures)


@pytest.mark.parametrize("matcher", ["cold-reviewer", "Explore|Task"])
def test_narrowed_subagent_start_matcher_fails(tmp_path: Path, matcher: str) -> None:
    """A narrowed matcher silently excludes delegates, so it must go red.

    `_SETTINGS_WIRING`'s `None` asserts nothing about the matcher; without
    `check_unscoped_events` this mutation passed every check.
    """
    settings = _full_settings()
    settings["hooks"]["SubagentStart"][0]["matcher"] = matcher
    `startup` entry carries `scripts/web-setup.sh` and `CLAUDE_CODE_REMOTE`,
    the `resume` entry carries `run tool-currency-check` and `run doctor` —
    so a check that pools substrings across the event (round 1) or across
    "owning" entries (round 2) would report fully wired. Neither entry alone
    carries all four, so on a real `startup` session the #418 project doctor
    and the tool-currency check (wired ONLY here, per the comment above
    `_SETTINGS_WIRING`) never run. Mutation-proven: reverting to round 2's
    pooling makes `check_settings_wiring` report this fully wired and this
    test goes RED (see the C8 ledger in the #919 implementation report). The
    control arm is
    `test_synthetic_full_settings_passes`, where the same four substrings
    live on ONE `startup|resume` entry and the row passes cleanly.
    """
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [
        _hook(
            "startup",
            f'if [ "$CLAUDE_CODE_REMOTE" = "true" ]; then '
            f"bash {_ANCHOR}/scripts/web-setup.sh; fi",
        ),
        _hook(
            "resume",
            f"mise -C {_ANCHOR} run tool-currency-check; mise -C {_ANCHOR} run doctor",
        ),
    ]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f for f in failures)


def test_wrong_command_fails(tmp_path: Path) -> None:
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [_hook("startup|resume", "bash other.sh")]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f for f in failures)


def test_session_start_without_the_doctor_fails(tmp_path: Path) -> None:
    """The #418 project doctor is wired ONLY here, so only this can protect it.

    It reads ``~/.config/fnox`` and ``~/.claude``, so it can never be an hk step
    or a CI job — settings.json is its single point of failure.
    """
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [
        _hook("startup|resume", f"mise -C {_ANCHOR} run tool-currency-check")
    ]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f and "run doctor" in f for f in failures)


def test_session_start_without_the_currency_check_fails(tmp_path: Path) -> None:
    """Its sibling checkup — the doctor delegates pin drift to it, so it must run."""
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [
        _hook("startup|resume", f"mise -C {_ANCHOR} run doctor")
    ]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f and "tool-currency-check" in f for f in failures)


def test_real_hook_files_run_no_command_audit_at_session_end() -> None:
    """The retired SessionEnd scan stays retired, on the Claude AND codex side.

    Seven concurrent SessionEnd command-audit scans (~814 MB of transcripts
    each, four orphaned past SessionEnd's 60 s cap) were the largest
    attributable host load on 2026-10-02; the audit is on demand now.
    """
    for path in (_REAL_SETTINGS, _REPO / ".codex" / "hooks.json"):
        hooks = json.loads(path.read_text())["hooks"]
        for event in ("SessionEnd", "Stop"):
            commands = [
                hook["command"]
                for entry in hooks.get(event, [])
                for hook in entry["hooks"]
            ]
            assert not [c for c in commands if "command-audit" in c], (path, event)


def test_pretooluse_through_path_bash_fails(tmp_path: Path) -> None:
    """A bare `bash` resolves to a mise shim here (~200 ms on EVERY tool call)."""
    settings = _full_settings()
    settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = (
        f"bash {_ANCHOR}/scripts/pretooluse-guard.sh"
    )
    failures = _wiring(tmp_path, settings)
    assert any("PreToolUse" in f and "/bin/bash" in f for f in failures), failures


@pytest.mark.parametrize("tool", ["Grep", "Read", "Glob"])
def test_pretooluse_dropping_a_graphify_tool_fails(tmp_path: Path, tool: str) -> None:
    """The merged hook also carries graphify's nudge; each tool is required."""
    settings = _full_settings()
    entry = settings["hooks"]["PreToolUse"][0]
    entry["matcher"] = "|".join(t for t in entry["matcher"].split("|") if t != tool)
    failures = _wiring(tmp_path, settings)
    assert any("PreToolUse" in f and f"'{tool}'" in f for f in failures), failures


def test_pretooluse_dropping_enterworktree_fails(tmp_path: Path) -> None:
    """Dropping just EnterWorktree must fail the owning matcher check."""
    settings = _full_settings()
    entry = settings["hooks"]["PreToolUse"][0]
    entry["matcher"] = entry["matcher"].replace("|EnterWorktree", "")
    failures = _wiring(tmp_path, settings)
    assert len(failures) == 1, failures
    assert "PreToolUse" in failures[0]
    assert "'EnterWorktree'" in failures[0]


def test_worktree_guard_endtoend_passes_on_real_repo() -> None:
    """Pin both EnterWorktree arms through the wrapper, not just the matcher."""
    wrapper = str(_REPO / hook_selfcheck.PRETOOLUSE_WRAPPER)
    assert hook_selfcheck.check_worktree_guard_endtoend(_REPO, wrapper) == []


def test_worktree_guard_endtoend_ignores_host_git_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host-wide REJECTING pre-commit must not reach the selfcheck's fixture.

    The hostile config is both ``GIT_CONFIG_GLOBAL`` and ``$HOME/.gitconfig``,
    so stripping every ``GIT_*`` variable (falling back to HOME) and keeping
    the inherited global config both let it run. Control arm: the same config
    really does reject a commit in an ordinary repo.
    """
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    pre_commit = hooks / "pre-commit"
    pre_commit.write_text("#!/bin/sh\necho host-hook-rejected >&2\nexit 1\n")
    pre_commit.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    hostile = home / ".gitconfig"
    hostile.write_text(
        "[user]\n\tname = T\n\temail = t@example.com\n"
        f"[core]\n\thooksPath = {hooks}\n"
        '[hook "reject"]\n\tcommand = exit 1\n\tevent = pre-commit\n'
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))

    control = tmp_path / "control"
    control.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=control, check=True, timeout=10)
    rejected = subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "x"],
        cwd=control,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert rejected.returncode != 0, rejected.stdout + rejected.stderr

    wrapper = str(_REPO / hook_selfcheck.PRETOOLUSE_WRAPPER)
    assert hook_selfcheck.check_worktree_guard_endtoend(_REPO, wrapper) == []


def test_missing_instructions_loaded_fails(tmp_path: Path) -> None:
    """#917: the InstructionsLoaded observer hook must stay wired.

    Proves C7 by deleting the wiring line, not by renaming a symbol
    (`.claude/rules/probes-need-a-control-arm.md` rule 2).
    """
    settings = _full_settings()
    del settings["hooks"]["InstructionsLoaded"]
    failures = _wiring(tmp_path, settings)
    assert any("InstructionsLoaded" in f for f in failures)


def test_instructions_loaded_wrong_command_fails(tmp_path: Path) -> None:
# Copyright (c) 2026 Raymond Manaloto
"""Shared pytest configuration: the `host_only` CI skip and the composite's commands.

`host_only` marks the handful of tests asserting facts about a real
developer host — a host-installed CLI (`claude`, `codex`, `gemini`) or a
chezmoi-applied `~/.zshenv` under zsh. No amount of `mise install` on a
runner makes them pass, so they are skipped there and ONLY there; on the
Mac host (and under `mise run ship`) they run normally.

Why a hook and not `-m "not host_only"` in the CI step: `pytest.ini`'s
`addopts` already carries `-m "not image_exec and not codex_exec"`, and a
command-line `-m` REPLACES it rather than anding with it (last one wins).
A CI `-m` would therefore have to restate the whole expression, and would
silently re-enable the credit-spending `codex_exec` tests the day someone
adds a marker and forgets. This cannot drift.
"""

import os
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def isolated_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep tests independent of the developer's global and system Git config.

    A machine-level hook (hk v2's recommended `hk install --global` writes
    `hook.hk-*` into `~/.gitconfig`) otherwise runs inside every throwaway repo.
    The file is a SIBLING of `tmp_path`, like `isolated_mise_state`'s dir, so
    tests that assert a tmp dir's exact contents are unaffected.

    It carries the ONE scoped `safe.directory` entry the chezmoi-managed global
    gitconfig renders for this checkout (#1183, `home/dot_gitconfig.tmpl`):
    replacing the global file without it re-opens `dubious ownership` for every
    test that runs git against the real repo under the devcontainer's virtiofs
    uid-0 flicker (smoke tier 2 runs this suite in-container).
    """
    gitconfig = tmp_path.parent / f"{tmp_path.name}.gitconfig"
    gitconfig.write_text(
        "[user]\n\tname = T\n\temail = t@example.com\n"
        f"[safe]\n\tdirectory = {_REPO_ROOT}\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return gitconfig


@pytest.fixture(autouse=True)
def isolated_mise_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep every test's mise registry in its own disposable state directory.

    Without this, a test that runs the real `mise` against a throwaway
    `mise.toml` registers it in the HOST's `tracked-configs`, and every later
    host `mise` command re-parses it (#1169/#1248). Same fixture as
    knowledge-base#818 + #819 (the trust-store share).

    The directory is a SIBLING of `tmp_path`, not inside it: `git` resolves
    through a mise shim here, so any Git call creates the state dir, and inside
    `tmp_path` it would read as drift in tests that prove a tmp dir is empty or
    a fixture repo is clean.
    """
    ambient = _ambient_mise_state_dir()
    state_dir = tmp_path.parent / f"{tmp_path.name}.mise-state"
    state_dir.mkdir(exist_ok=True)
    # MISE_STATE_DIR moves TRUST records too. A host that trusts this checkout
    # via `mise trust` (rather than a global `trusted_config_paths`) would lose
    # that trust inside every test, and `mise env`/`mise run` would refuse the
    # repo config. Share the ambient trust store; isolate only tracking.
    ambient_trust = ambient / "trusted-configs"
    if ambient_trust.is_dir():
        (state_dir / "trusted-configs").symlink_to(ambient_trust)
    monkeypatch.setenv("MISE_STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture(autouse=True)
def isolated_host_locks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Give every test its own host-lock directory (``host_lock.LOCK_DIR_ENV``).

    The heavy-gate lock is HOST-wide by design, and the suite itself runs under
    it (the pre-push ``test-hook-isolated`` task holds it). A test that drives
    ``run_gate``/``ship_main`` against the real path would therefore wait on
    the very run executing it — and parallel workers would wait on each other.
    The inherited holder variables are dropped too, so a test never "re-enters"
    a lock its own runner holds. A sibling of ``tmp_path``, like the dirs above.
    """
    lock_dir = tmp_path.parent / f"{tmp_path.name}.locks"
    monkeypatch.setenv("DOTFILES_LOCK_DIR", str(lock_dir))
    for name in list(os.environ):
        if name.startswith("DOTFILES_LOCK_HOLDER_"):
            monkeypatch.delenv(name)
    return lock_dir


def _ambient_mise_state_dir() -> Path:
    """The state dir mise would use without the fixture (its documented order)."""
    if explicit := os.environ.get("MISE_STATE_DIR"):
        return Path(explicit)
    xdg = os.environ.get("XDG_STATE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "state") / "mise"


#: Workers for `-n auto` when PYTEST_XDIST_AUTO_NUM_WORKERS is unset: a cap
#: for a SHARED host (xdist's own default is every core — 12 here — and two
#: concurrent suites at that width drove the load average past 100).
DEFAULT_TEST_WORKERS = 4


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_auto_num_workers(config: pytest.Config) -> int | None:
    """`-n auto` -> DEFAULT_TEST_WORKERS, unless the native knob is set.

    Returning None when PYTEST_XDIST_AUTO_NUM_WORKERS is set hands the answer
    to xdist's own implementation, which reads that variable — so there is one
    knob, and it is xdist's.
    """
    _ = config
    if os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS"):
        return None
    return DEFAULT_TEST_WORKERS


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip `host_only` tests when running on a CI runner ($CI is set)."""
    # `== "true"`, matching rule_sync.py:223 rather than plain truthiness:
    # a stray `CI=false` must not silently skip these — a quiet loss of
    # coverage is the #808 failure mode itself. GitHub Actions sets
    # `CI=true`.
    if os.environ.get("CI") != "true":
        return
    skip = pytest.mark.skip(
        reason="host_only: needs a real developer host, not a CI runner"
    )
    for item in items:
        if "host_only" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def lock_refresh_commands() -> str:
    """Every shell command the lock-refresh composite actually runs.

    Parsed out of the YAML rather than grepped out of the file, so a comment
    can never satisfy an assertion about a command. That distinction is
    load-bearing and was mutation-proven by the fixture this replaces: the
    composite names its flags in prose directly above the step, so a
    whole-file substring check passes with the flag deleted from the command.
    Joining only the `run:` values keeps that property structurally, without
    a hand-rolled comment stripper.
    """
    action = (
        Path(__file__).parent.parent
        / ".github"
        / "actions"
        / "lock-refresh"
        / "action.yml"
    ).read_text()
    steps = yaml.safe_load(action)["runs"]["steps"]
    return "\n".join(step.get("run", "") for step in steps)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-fow9iuDs' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-8xjGNbW6' (errno=Operation not permitted)
commit 865454f943559941f8a57581f630995984f9cef7
Author:     Raymond Manaloto <ray.manaloto@gmail.com>
AuthorDate: Sat Oct 3 15:12:57 2026 -0500
Commit:     Raymond Manaloto <ray.manaloto@gmail.com>
CommitDate: Sat Oct 3 15:12:57 2026 -0500

    fix(hooks): keep host git config and hooks out of the #1606 selfcheck fixture
    
    The worktree-guard selfcheck stripped every GIT_* variable, which also
    removed GIT_CONFIG_GLOBAL/GIT_CONFIG_NOSYSTEM (tests/conftest.py's
    isolation) and let a host-wide pre-commit (hk's hook.hk-* in ~/.gitconfig)
    run on the fixture commit; a rejecting hook turned both arms red.
    
    - Strip only the git-local set git names (process_env.git_local_env_names).
    - The fixture's git runs with GIT_CONFIG_GLOBAL=/dev/null,
      GIT_CONFIG_NOSYSTEM=1 and core.hooksPath=/dev/null.
    - New test: a rejecting pre-commit via both core.hooksPath and a config
      hook, installed as GIT_CONFIG_GLOBAL and $HOME/.gitconfig, with a control
      arm proving it rejects an ordinary commit; the selfcheck must still pass.
      The a56683a3 selfcheck fails it ("could not build its git fixture").
    
    Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_014gngiWkKEqbzqXi7Bkm7Sz
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-eU95G7rm' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-zFIv74zz' (errno=Operation not permitted)
git version 2.54.0 (Apple Git-157)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-w5jeJCZr' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-nXeyVcfQ' (errno=Operation not permitted)
GIT_ALTERNATE_OBJECT_DIRECTORIES
GIT_CONFIG
GIT_CONFIG_PARAMETERS
GIT_CONFIG_COUNT
GIT_OBJECT_DIRECTORY
GIT_DIR
GIT_WORK_TREE
GIT_IMPLICIT_WORK_TREE
GIT_GRAFT_FILE
GIT_INDEX_FILE
GIT_NO_REPLACE_OBJECTS
GIT_REPLACE_REF_BASE
GIT_PREFIX
GIT_SHALLOW_FILE
GIT_COMMON_DIR
/Users/rmanaloto/.local/share/mise/installs/uv/0.12.13/uv-aarch64-apple-darwin/uv
drwxr-xr-x@ 9 rmanaloto  staff  288 Oct  3 13:12 python/.venv
lrwxr-xr-x@ 1 rmanaloto  staff   86 Oct  3 13:12 python/.venv/bin/python -> /Users/rmanaloto/.local/share/uv/python/cpython-3.14-macos-aarch64-none/bin/python3.14
.github/workflows/ci.yml:65:  # that actions/checkout's `git init` emits (#21). git reads GIT_CONFIG_COUNT/
.github/workflows/ci.yml:69:  GIT_CONFIG_COUNT: "1"
.github/workflows/gcc-sha-repair.yml:30:  # that actions/checkout's `git init` emits (#21). git reads GIT_CONFIG_COUNT/
.github/workflows/gcc-sha-repair.yml:34:  GIT_CONFIG_COUNT: "1"
.github/workflows/image-analysis.yml:39:  # that actions/checkout's `git init` emits (#21). git reads GIT_CONFIG_COUNT/
.github/workflows/image-analysis.yml:43:  GIT_CONFIG_COUNT: "1"
.github/workflows/build-publish.yml:71:  # that actions/checkout's `git init` emits (#21). git reads GIT_CONFIG_COUNT/
.github/workflows/build-publish.yml:75:  GIT_CONFIG_COUNT: "1"
.github/workflows/ghcr-cleanup.yml:36:  # that actions/checkout's `git init` emits (#21). git reads GIT_CONFIG_COUNT/
.github/workflows/ghcr-cleanup.yml:40:  GIT_CONFIG_COUNT: "1"
.github/workflows/refresh.yml:54:  # that actions/checkout's `git init` emits (#21). git reads GIT_CONFIG_COUNT/
.github/workflows/refresh.yml:58:  GIT_CONFIG_COUNT: "1"
.github/workflows/autofix.yml:24:  # that actions/checkout's `git init` emits (#21). git reads GIT_CONFIG_COUNT/
.github/workflows/autofix.yml:28:  GIT_CONFIG_COUNT: "1"
tests/test_git_config_isolation.py:76:    monkeypatch.delenv("GIT_CONFIG_GLOBAL")
python/src/dotfiles_setup/hook_selfcheck.py:485:    env = {**env, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
python/src/dotfiles_setup/hook_selfcheck.py:572:    # GIT_CONFIG_GLOBAL (the fixture pins its own config isolation).
python/src/dotfiles_setup/hook_selfcheck.py:574:        local = process_env.git_local_env_names()
tests/conftest.py:47:    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
tests/test_hook_selfcheck.py:520:    The hostile config is both ``GIT_CONFIG_GLOBAL`` and ``$HOME/.gitconfig``,
tests/test_hook_selfcheck.py:539:    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
tests/test_safe_directory.py:63:        "GIT_CONFIG_GLOBAL": str(gitconfig),
tests/test_image_smoke.py:1374:            "GIT_COMMITTER_NAME": "t",
tests/test_image_smoke.py:1375:            "GIT_COMMITTER_EMAIL": "t@t",
tests/test_doctor.py:1960:    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
tests/test_renovate_ignored_authors.py:105:        "          GIT_COMMITTER_EMAIL: other[bot]@example.com\n"
tests/test_pr.py:452:    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
tests/test_pr.py:695:    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
tests/test_hk_hooks.py:7:into THAT file (`GIT_CONFIG_GLOBAL`) and never the developer's `~/.gitconfig`.
tests/test_hk_hooks.py:29:    # Belt and braces for `--global`: refuse unless GIT_CONFIG_GLOBAL points into
tests/test_hk_hooks.py:34:        target = os.environ.get("GIT_CONFIG_GLOBAL", "")
python/src/dotfiles_setup/process_env.py:65:def git_local_env_names(*, cwd: Path | None = None) -> frozenset[str]:
python/src/dotfiles_setup/process_env.py:101:    names = git_local_env_names() if local_names is None else local_names
tests/test_process_env.py:135:        process_env.git_local_env_names()
tests/test_process_env.py:202:    local_names = process_env.git_local_env_names(cwd=outer)

[35m[3mexec[0m[0m
[1m/bin/zsh -lc "cat python/src/dotfiles_setup/child_env.py; cat tests/test_git_config_isolation.py; sed -n '1,270p' tests/test_process_env.py; sed -n '195,235p' python/src/dotfiles_setup/hook_selfcheck.py; sed -n '890,1040p' python/src/dotfiles_setup/hook_selfcheck.py; cat .claude/settings.json; cat pytest.ini; uv run --project python --no-sync --offline python -B -c 'print(\"python available\")'"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[31m exited 2 in 3104ms:[0m
# Copyright (c) 2026 Raymond Manaloto
"""Strip credentials from the environment of processes this repo spawns.

`fnox activate` exports real credentials into the interactive shell, and mise
records the whole delta in ``__MISE_DIFF`` (zlib+base64) so it can undo it on
directory exit. Both are inherited by every child process — including external
tools that write artifacts we then commit.

This is containment, not the fix. The fix is fnox's own ``env = "exec"``
(v1.30.0+), which keeps the secrets out of the shell in the first place; see
`.claude/rules/secrets-out-of-the-shell-env.md`. Until that is set, a tool this
repo launches has no business inheriting an AWS secret key, so it does not.

Two strengths, because they carry different risk:

- :func:`without_env_diff` drops **only** ``__MISE_DIFF``. Nothing but mise
  reads it, and mise re-derives it, so this is safe at every boundary and is
  what the spawn sites use by default. It removes the whole blob — the single
  variable that carries every other secret in one opaque field.
- :func:`clean_env` additionally drops every credential-shaped NAME. That can
  break a child that genuinely needs one, so it is opt-in per call site, with
  an explicit ``keep`` for the exceptions.

**Neither touches your shell.** Both build a copy handed to
:func:`subprocess.run`; mise still gets its ``__MISE_DIFF`` for directory exit.
"""

from __future__ import annotations

import os
import re

# The compressed env delta. Its entire content is the leak, and no child reads
# it — mise recomputes it from config.
ENV_DIFF_NAME = "__MISE_DIFF"
GIT_CONTEXT_NAMES = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    }
)

# Names that carry a credential. Matched on the NAME, so a provider we have
# never heard of is covered as long as it follows the usual convention.
CREDENTIAL_NAME = re.compile(
    r"(?:^|_)(?:SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY|"
    r"CREDENTIAL|CREDENTIALS|APP_PASSWORD|CLIENT_SECRET)(?:_|$)"
)


def is_credential(name: str) -> bool:
    """True when the variable NAME marks it as carrying a credential."""
    return name == ENV_DIFF_NAME or bool(CREDENTIAL_NAME.search(name))


def without_env_diff(base: dict[str, str] | None = None) -> dict[str, str]:
    """A copy of the environment with ``__MISE_DIFF`` removed, nothing else.

    The default strength for a spawn site: it cannot break a child, because no
    child reads the variable, and it removes the one field that carries every
    secret at once.
    """
    source = os.environ if base is None else base
    return {k: v for k, v in source.items() if k != ENV_DIFF_NAME}


def without_git_context(base: dict[str, str] | None = None) -> dict[str, str]:
    """Remove repository-routing variables before invoking public Git paths."""
    source = without_env_diff(base)
    return {k: v for k, v in source.items() if k not in GIT_CONTEXT_NAMES}


def clean_env(
    base: dict[str, str] | None = None, *, keep: frozenset[str] = frozenset()
) -> dict[str, str]:
    """A copy of the environment with every credential-bearing name removed.

    Args:
        base: Environment to filter. Defaults to the current process's.
        keep: Names to preserve even though they look like credentials — for a
            child that genuinely needs one. Pass it at the call site so the
            exception is visible in review rather than buried in a constant.

    Returns:
        A new dict. The caller's environment is never modified.
    """
    source = os.environ if base is None else base
    return {k: v for k, v in source.items() if k in keep or not is_credential(k)}


def dropped_names(base: dict[str, str] | None = None) -> list[str]:
    """The names :func:`clean_env` would remove — for logging. Never values."""
    source = os.environ if base is None else base
    return sorted(k for k in source if is_credential(k))
# Copyright (c) 2026 Raymond Manaloto
"""The autouse `isolated_git_config` fixture keeps machine-level git config out.

hk v2 recommends `hk install --global`, which writes `hook.hk-*` into
`~/.gitconfig`; without isolation every throwaway repo a test creates runs it
(the 2026-09-27 `test_branch_guard` failure). These tests contaminate `$HOME`
the way a real machine is, so deleting the fixture fails the first one.
"""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

_MARKER = "PROBE_GLOBAL_HOOK_RAN"


def _contaminated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(
        "[user]\n"
        "\tname = T\n"
        "\temail = t@example.com\n"
        '[hook "probe-pre-commit"]\n'
        # Quoted: an unquoted `;` starts a comment in git config, which
        # silently truncates the command to `echo` (exit 0).
        f'\tcommand = "echo {_MARKER} >&2; exit 1"\n'
        "\tevent = pre-commit\n"
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)


def _commit_in_throwaway_repo(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
    (repository / "tracked").write_text("fixture\n")
    subprocess.run(
        ["git", "-C", str(repository), "add", "tracked"],
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", "probe"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_a_global_hook_in_home_does_not_reach_a_test_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the fixture active, `$HOME/.gitconfig` is never read."""
    _contaminated_home(tmp_path, monkeypatch)

    result = _commit_in_throwaway_repo(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _MARKER not in result.stderr


def test_the_probe_sees_the_global_hook_without_the_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CONTROL ARM: undo the fixture's override and the same hook fires.

    Without this arm the test above could pass because the probe hook never
    runs at all, rather than because the fixture blocks it.
    """
    _contaminated_home(tmp_path, monkeypatch)
    monkeypatch.delenv("GIT_CONFIG_GLOBAL")

    result = _commit_in_throwaway_repo(tmp_path)

    assert result.returncode != 0
    assert _MARKER in result.stderr


def test_the_fixture_keeps_this_checkout_a_safe_directory() -> None:
    """#1183: the replaced global config still trusts this repository."""
    root = Path(__file__).resolve().parent.parent
    listed = subprocess.run(
        ["git", "config", "--global", "--get-all", "safe.directory"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert str(root) in listed
# Copyright (c) 2026 Raymond Manaloto
"""Tests for the Git-isolated pre-push child-process boundary."""

from __future__ import annotations

import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import process_env

_OPAQUE_VALUE = "opaque-value"


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed rc={result.returncode}: {result.stderr}"
        raise RuntimeError(msg)
    return result.stdout.strip()


def _init_repo(path: Path) -> None:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Env Safety Test")
    _git(path, "config", "user.email", "env-safety@example.invalid")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(path, "add", "tracked.txt")
    _git(path, "commit", "-m", "initial")


def _fingerprint(repo: Path) -> tuple[str, ...]:
    """Fingerprint every outer-repository surface the reproduced bug changed."""
    git_dir = Path(_git(repo, "rev-parse", "--absolute-git-dir"))
    common_dir = Path(_git(repo, "rev-parse", "--git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = (repo / common_dir).resolve()
    index = git_dir / "index"
    hook = git_dir / "hooks" / "pre-push"
    refs = tuple(
        (str(path.relative_to(git_dir)), path.read_bytes().hex())
        for path in sorted((git_dir / "refs").rglob("*"))
        if path.is_file()
    )
    packed_refs = git_dir / "packed-refs"
    return (
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "symbolic-ref", "HEAD"),
        str(git_dir),
        str(common_dir),
        (common_dir / "config").read_bytes().hex(),
        repr(refs),
        packed_refs.read_bytes().hex() if packed_refs.exists() else "ABSENT",
        index.read_bytes().hex(),
        hook.read_bytes().hex(),
        (repo / "tracked.txt").read_bytes().hex(),
        _git(repo, "status", "--porcelain=v1"),
    )


def _fingerprint_without_hook(repo: Path) -> tuple[str, str]:
    """Small fingerprint for the deliberately destructive isolated control."""
    git_dir = Path(_git(repo, "rev-parse", "--absolute-git-dir"))
    return (
        (git_dir / "config").read_bytes().hex(),
        _git(repo, "config", "--get", "core.bare"),
    )


@pytest.mark.parametrize("raw", [(), ("--",)])
def test_command_after_separator_requires_a_command(raw: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="command is required"):
        process_env.command_after_separator(raw)


def test_fnox_command_is_noninteractive_and_bounded() -> None:
    assert process_env.fnox_command(("git", "push")) == (
        "fnox",
        "exec",
        "--non-interactive",
        "--",
        "git",
        "push",
    )


def test_fnox_parent_env_removes_stale_gh_precedence_only() -> None:
    base = {
        "GH_TOKEN": "stale-first-precedence",
        "GITHUB_TOKEN": "stale-second-precedence",
        "DOPPLER_TOKEN": "provider-input",
        "PATH": "/usr/bin",
    }
    cleaned = process_env.fnox_parent_env(base)
    assert "GH_TOKEN" not in cleaned
    assert "GITHUB_TOKEN" not in cleaned
    assert set(cleaned) == {"DOPPLER_TOKEN", "PATH"}


def test_git_isolated_env_uses_the_derived_git_set_and_drops_credentials() -> None:
    local = frozenset({"GIT_DIR", "GIT_FUTURE_LOCAL_STATE"})
    base = {
        "PATH": "/usr/bin",
        "GIT_DIR": "/outer/.git",
        "GIT_FUTURE_LOCAL_STATE": "future",
        "GITHUB_TOKEN": _OPAQUE_VALUE,
        "ORDINARY": "kept",
    }
    cleaned = process_env.git_isolated_env(base, local_names=local)
    assert cleaned == {"PATH": "/usr/bin", "ORDINARY": "kept"}


def test_git_local_env_discovery_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        process_env.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "failure"),
    )
    with pytest.raises(RuntimeError, match="failed rc=1"):
        process_env.git_local_env_names()


def test_real_pre_push_poison_cannot_modify_outer_repository(tmp_path: Path) -> None:
    """The public pre-push task scrubs all Git-local variables before pytest."""
    outer = tmp_path / "outer"
    remote = tmp_path / "remote.git"
    disposable = tmp_path / "disposable"
    plugin_dir = tmp_path / "plugin"
    marker = tmp_path / "probe-ran"
    global_task_marker = tmp_path / "global-task-ran"
    global_mise = tmp_path / "global-mise.toml"
    task_root = tmp_path / "project-task"
    probe_test = tmp_path / "test_probe.py"
    runtime_global_mise = Path(
        os.environ.get(
            "MISE_GLOBAL_CONFIG_FILE",
            Path.home() / ".config" / "mise" / "config.toml",
        )
    )
    _init_repo(outer)
    disposable.mkdir()
    plugin_dir.mkdir()
    task_root.mkdir()
    probe_test.write_text("def test_probe():\n    pass\n", encoding="utf-8")
    console_dir = Path(sys.executable).parent
    isolated_command = " ".join(
        shlex.quote(str(part))
        for part in (
            console_dir / "dotfiles-setup",
            "process",
            "git-isolated",
            "--",
            console_dir / "pytest",
            "-q",
            "--collect-only",
            probe_test,
        )
    )
    (task_root / "mise.toml").write_text(
        f"[tasks.test-hook-isolated]\nrun = {isolated_command!r}\n",
        encoding="utf-8",
    )
    (plugin_dir / "poison_probe.py").write_text(
        "import os\n"
        "import subprocess\n"
        "from pathlib import Path\n"
        "def pytest_sessionstart(session):\n"
        '    subprocess.run(["git", "-C", os.environ["PROBE_REPO"], '
        '"-c", "core.bare=false", "init"], check=True)\n'
        '    Path(os.environ["PROBE_MARKER"]).write_text("ran\\n")\n',
        encoding="utf-8",
    )
    global_mise.write_text(
        "[tasks.test-hook-isolated]\n"
        "run = 'printf global > \"$GLOBAL_MISE_MARKER\"; exit 97 #'\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "--bare", str(remote)], check=True)
    _git(outer, "remote", "add", "origin", str(remote))
    _git(outer, "push", "-u", "origin", "HEAD")
    (outer / "tracked.txt").write_text("next\n", encoding="utf-8")
    _git(outer, "commit", "-am", "next")

    hook = Path(_git(outer, "rev-parse", "--git-path", "hooks/pre-push"))
    if not hook.is_absolute():
        hook = outer / hook
    local_names = process_env.git_local_env_names(cwd=outer)
    poison_lines = "\n".join(
        f'export {name}="$outer_git_dir"' for name in sorted(local_names)
    )
    hook.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        'outer_git_dir="$(git rev-parse --absolute-git-dir)"\n'
        f"{poison_lines}\n"
        f'export PYTHONPATH="{plugin_dir}"\n'
        'export PYTEST_PLUGINS="poison_probe"\n'
        f'export PROBE_REPO="{disposable}"\n'
        f'export PROBE_MARKER="{marker}"\n'
        f'export MISE_GLOBAL_CONFIG_FILE="{global_mise}"\n'
        f'export MISE_TRUSTED_CONFIG_PATHS="{task_root}{os.pathsep}{tmp_path}'
        f'{os.pathsep}{runtime_global_mise}"\n'
        f'export MISE_IGNORED_CONFIG_PATHS="{task_root}"\n'
        f'export MISE_PROJECT_ROOT="{task_root}"\n'
        # #1053: repointing MISE_GLOBAL_CONFIG_FILE above demotes the real
        # ~/.config/mise/config.toml to a non-global config, so mise auto-
        # installs ITS tools before running the task. That made this test
        # depend on the host's entire tool inventory resolving: mise 2026.9.7's
        # npm trust policy (trustPolicy=no-downgrade) started failing 4 of 36,
        # and mise aborted before the task ran, so the marker below was never
        # written. The task under test needs no mise-managed tool -- it runs
        # console scripts by absolute path -- so turn the install step off.
        "export MISE_TASK_RUN_AUTO_INSTALL=0\n"
        f'export GLOBAL_MISE_MARKER="{global_task_marker}"\n'
        'exec env -u MISE_IGNORED_CONFIG_PATHS mise --cd "$MISE_PROJECT_ROOT" '
        "run test-hook-isolated "
        "-- --collect-only\n",
        encoding="utf-8",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    before = _fingerprint(outer)

    _git(outer, "push", "--dry-run", "origin", "HEAD")

    assert _fingerprint(outer) == before
    assert (disposable / ".git").is_dir()
    assert marker.read_text(encoding="utf-8") == "ran\n"
    assert not global_task_marker.exists()

    hook.write_text(
        hook.read_text(encoding="utf-8").replace(
            'env -u MISE_IGNORED_CONFIG_PATHS mise --cd "$MISE_PROJECT_ROOT" '
            "run test-hook-isolated",
            "env -u MISE_IGNORED_CONFIG_PATHS mise run test-hook-isolated",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="failed rc=1"):
        _git(outer, "push", "--dry-run", "origin", "HEAD")
    assert global_task_marker.read_text(encoding="utf-8") == "global"


def test_poisoned_git_env_mutation_reaches_outer_without_scrub(tmp_path: Path) -> None:
    """Control: removing the isolation reproduces mutation of the outer repo."""
    outer = tmp_path / "outer"
    disposable = tmp_path / "disposable"
    _init_repo(outer)
    disposable.mkdir()
    before = _fingerprint_without_hook(outer)
    env = dict(os.environ)
    env["GIT_DIR"] = _git(outer, "rev-parse", "--absolute-git-dir")
    env["GIT_WORK_TREE"] = str(outer)

    subprocess.run(
# call proceed. That is #343: 125 denied Bash calls executed unchecked while the
# cwd was a sibling repo. Every wired command must anchor its paths.
_PROJECT_DIR_ANCHOR = "CLAUDE_PROJECT_DIR"


def _run(
    cmd: list[str],
    *,
    stdin: str | None = None,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=_PROBE_TIMEOUT_S,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "probe timed out")
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def _hook_payload(command: str) -> str:
    """The PreToolUse stdin JSON the harness sends the hook."""
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _event_entries(settings: dict, event: str) -> list[tuple[str, str]]:
    """(matcher, command) pairs wired for a settings.json hook event."""
    entries: list[tuple[str, str]] = []
    for entry in settings.get("hooks", {}).get(event, []):
        matcher = entry.get("matcher", "")
        matcher = matcher if isinstance(matcher, str) else ""
        entries.extend(
        result = _run(command, stdin=json.dumps(payload), cwd=project_root)
        if result.returncode != 0:
            failures.append(
                f"subagent-contract {name} arm exited {result.returncode}: "
                f"{result.stderr.strip()}"
            )
            continue
        if emits and any(token not in result.stdout for token in required):
            failures.append(
                f"subagent-contract {name} arm lost required output: "
                f"{result.stdout.strip()!r}"
            )
        # Nothing here may ever use the turn-forcing channels. `block` and
        # `additionalContext` BOTH keep a delegate running, so no presence- or
        # liveness-shaped assertion can separate them; only a forbid can (#994).
        if '"decision"' in result.stdout:
            failures.append(
                f"subagent-contract {name} arm must never use the decision/block "
                f"channel — it forces a model turn: {result.stdout.strip()!r}"
            )
        if not emits and result.stdout.strip():
            failures.append(
                "subagent-contract recursive-stop arm must be silent to avoid "
                f"a retry loop: {result.stdout.strip()!r}"
            )
    return failures


def check_script_syntax(project_root: Path) -> list[str]:
    """``bash -n`` every wired hook script — a parse error would brick a hook."""
    failures: list[str] = []
    for rel in _HOOK_SCRIPTS:
        res = _run(["bash", "-n", str(project_root / rel)])
        if res.returncode != 0:
            failures.append(f"{rel} failed `bash -n`: {res.stderr.strip()}")
    return failures


# Every route to the plugin's plan-SWITCH script. Attestation itself was opened
# to agents on 2026-09-26 (Ray: "fix the settings change so we can automate
# it"); switching WHICH plan is active stays denied — that is the 2026-09-22c
# wrong-plan class, a different boundary. Both the bare and the
# argument-carrying rule must be present, because a trailing `*` also matches
# the bare command ONLY when it is the rule's sole wildcard — and this one
# carries a leading one.
_PLAN_SWITCH_DENY_BASES: tuple[str, ...] = ("*set-active-plan.sh",)


def check_plan_switch_deny(settings_path: Path) -> list[str]:
    """The plan-switch boundary is a permission DENY, not a hook.

    ⚠️ **This is a presence check, and that is the honest limit of it.** The
    permission engine belongs to the harness; nothing here can invoke it, so
    unlike :func:`check_pretooluse_endtoend` this cannot drive a real deny. It
    proves the rules have not been silently removed or half-written — it does
    not prove the harness still honours them. The live arms were run by hand
    when the rules landed (2026-09-02) — then covering attestation too — and
    returned "has been denied" while `shasum -a 256 task_plan.md` and an
    unrelated mise task still ran.

    Why a permission rule rather than the PreToolUse guard: hard bans must never
    fail open, and the guard does exactly that on its own errors (#343,
    `.claude/rules/mise-tasks-only.md` § Enforcement layers).
    """
    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read {settings_path}: {exc}"]
    deny = set(settings.get("permissions", {}).get("deny", ()))
    required = [
        f"Bash({base}{suffix})"
        for base in _PLAN_SWITCH_DENY_BASES
        for suffix in ("", " *")
    ]
    return [
        f"settings.json permissions.deny is missing {rule!r} — switching the "
        "active plan is a boundary and both the bare and the argument form must "
        "be denied"
        for rule in required
        if rule not in deny
    ]


def hook_selfcheck_main(project_root: Path) -> int:
    """Run every host-side hook check; print PASS/FAIL per check; 0 iff clean."""
    settings_path = project_root / ".claude" / "settings.json"
    checks = (
        ("settings-wiring", lambda: check_settings_wiring(settings_path)),
        ("script-syntax", lambda: check_script_syntax(project_root)),
        ("guard-decisions", check_guard_decisions),
        ("pretooluse-endtoend", lambda: check_pretooluse_endtoend(project_root)),
        ("unscoped-events", lambda: check_unscoped_events(settings_path)),
        (
            "subagent-contract-endtoend",
            lambda: check_subagent_contract_endtoend(project_root),
        ),
        ("plan-switch-deny", lambda: check_plan_switch_deny(settings_path)),
    )
    ok = True
    for name, run in checks:
        failures = run()
        if failures:
            ok = False
            for failure in failures:
                sys.stdout.write(f"FAIL  hook-selfcheck[{name}]: {failure}\n")
        else:
            sys.stdout.write(f"PASS  hook-selfcheck[{name}]\n")
    if ok:
        sys.stdout.write("hook-selfcheck: OK — all wired host-side hooks pass\n")
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == [SUBAGENT_CONTRACT_MODE]:
        raise SystemExit(subagent_contract_main())
    sys.stderr.write(
        f"usage: python -m {__package__}.hook_selfcheck subagent-contract\n"
    )
    raise SystemExit(2)
{
  "$schema": "https://www.schemastore.org/claude-code-settings.json",
  "claudeMdExcludes": ["**/docs/research/kb/raw/**"],
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "33",
    "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD": "1",
    "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "20",
    "CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION": "200",
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "3",
    "CLAUDE_CODE_TASK_LIST_ID": "dotfiles-dag",
    "OTEL_LOG_RAW_API_BODIES": "0"
  },
  "permissions": {
    "allow": [
      "mcp__context7__resolve-library-id",
      "mcp__memory__create_entities",
      "mcp__memory__create_relations",
      "mcp__memory__add_observations",
      "mcp__memory__delete_entities",
      "mcp__memory__delete_observations",
      "mcp__memory__delete_relations"
    ],
    "deny": [
      "Bash(chezmoi apply:*)",
      "Bash(chezmoi update:*)",
      "mcp__filesystem__write_file",
      "mcp__filesystem__edit_file",
      "mcp__filesystem__create_directory",
      "mcp__filesystem__move_file",
      "Bash(*set-active-plan.sh)",
      "Bash(*set-active-plan.sh *)",
      "Read(~/.agentsview/config.toml)",
      "Read(~/.agentsview/config.toml.lock)",
      "Read(~/.codex/auth.json)",
      "Read(~/.config/gh/hosts.yml)",
      "Read(~/.docker/config.json)",
      "Read(~/.claude/.credentials.json)",
      "Read(~/.ssh/id_*)",
      "Read(~/.netrc)",
      "Read(~/.aws/credentials)",
      "Read(~/.git-credentials)",
      "Read(~/.npmrc)",
      "Read(~/.pypirc)",
      "Read(.env)",
      "Read(.env.*)",
      "Bash(*graphify label*)",
      "Bash(*.agentsview/config.toml*)",
      "Bash(*.codex/auth.json*)",
      "Bash(*gh/hosts.yml*)",
      "Bash(*.docker/config.json*)",
      "Bash(*.claude/.credentials.json*)",
      "Bash(*.ssh/id_rsa*)",
      "Bash(*.ssh/id_ed25519*)",
      "Bash(*.netrc*)",
      "Bash(*.aws/credentials*)",
      "Bash(*.git-credentials*)"
    ],
    "additionalDirectories": [
      "/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base"
    ]
  },
  "fallbackModel": [
    "opus",
    "sonnet"
  ],
  "disableClaudeAiConnectors": true,
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|AskUserQuestion|Edit|Write|NotebookEdit|Grep|Read|Glob|EnterWorktree",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash \"${CLAUDE_PROJECT_DIR:-.}/scripts/pretooluse-guard.sh\"",
            "timeout": 20
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --project \"${CLAUDE_PROJECT_DIR:-.}/python\" dotfiles-setup mise-config-context",
            "timeout": 20
          }
        ]
      },
      {
        "matcher": "Agent",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --project \"${CLAUDE_PROJECT_DIR:-.}/python\" python -m dotfiles_setup.hook_selfcheck subagent-contract",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "if [ \"${CLAUDE_CODE_REMOTE:-}\" = \"true\" ]; then bash \"${CLAUDE_PROJECT_DIR:-.}/scripts/web-setup.sh\"; else mise -C \"${CLAUDE_PROJECT_DIR:-.}\" run tool-currency-check; DOTFILES_AMBIENT_PATH=\"$PATH\" mise -C \"${CLAUDE_PROJECT_DIR:-.}\" run doctor; fi",
            "timeout": 600
          }
        ]
      }
    ],
    "InstructionsLoaded": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --project \"${CLAUDE_PROJECT_DIR:-.}/python\" python -m dotfiles_setup.instructions_observer",
            "timeout": 10
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --project \"${CLAUDE_PROJECT_DIR:-.}/python\" python -m dotfiles_setup.hook_selfcheck subagent-contract",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "enabledPlugins": {
    "code-review@claude-plugins-official": false,
    "code-simplifier@claude-plugins-official": false,
    "claude-md-management@claude-plugins-official": false,
    "commit-commands@claude-plugins-official": false,
    "skill-creator@claude-plugins-official": true,
    "claude-code-setup@claude-plugins-official": false,
    "pyright-lsp@claude-plugins-official": false,
    "pyright@claude-code-lsps": false,
    "explanatory-output-style@claude-plugins-official": false,
    "hookify@claude-plugins-official": false,
    "learning-output-style@claude-plugins-official": true,
    "octo@nyldn-plugins": false,
    "codex@openai-codex": true,
    "astral@astral-sh": false,
    "mattpocock-skills@mattpocock": true,
    "antigravity@antigravity-for-claude-code": true,
    "context7@context7-marketplace": true,
    "last30days@last30days-skill": true,
    "exa@exa": true,
    "firecrawl@firecrawl": true,
    "builder-skills@builder-skills": false,
    "eli5@claude-community": true,
    "i-have-adhd@i-have-adhd": true,
    "planning-with-files@planning-with-files": true
  },
  "extraKnownMarketplaces": {
    "firecrawl": {
      "source": {
        "source": "github",
        "repo": "firecrawl/firecrawl-claude-plugin"
      }
    },
    "exa": {
      "source": {
        "source": "github",
        "repo": "exa-labs/exa-mcp-server"
      }
    },
    "context7-marketplace": {
      "source": {
        "source": "github",
        "repo": "upstash/context7"
      }
    },
    "antigravity-for-claude-code": {
      "source": {
        "source": "github",
        "repo": "yuting0624/antigravity-for-claude-code"
      }
    },
    "last30days-skill": {
      "source": {
        "source": "github",
        "repo": "mvanhorn/last30days-skill"
      }
    },
    "openai-codex": {
      "source": {
        "source": "github",
        "repo": "openai/codex-plugin-cc"
      }
    },
    "builder-skills": {
      "source": {
        "source": "github",
        "repo": "BuilderIO/skills"
      }
    },
    "planning-with-files": {
      "source": {
        "source": "github",
        "repo": "OthmanAdi/planning-with-files"
      }
    }
  },
  "prefersReducedMotion": true,
  "switchModelsOnFlag": true,
  "teammateMode": "auto"
}
[pytest]
# Root pytest config so `addopts`/`markers` are discovered when pytest is run
# as `uv run --project python pytest tests/` from the repo root — pytest walks
# UP from `tests/` for the first inifile, and `python/pyproject.toml` is a
# sibling (never an ancestor), so config must live here.
markers =
    image_exec: containerized real-toolchain exec test (needs Docker + the :dev image; run via `mise run smoke-exec`)
    codex_exec: end-to-end Codex lane test — spawns the REAL `codex exec` and COSTS CREDITS (needs an authenticated codex CLI; run via `mise run codex-lane-e2e`)
    host_only: needs a real developer host — a host-installed CLI (claude/gemini) or a chezmoi-applied ~/.zshenv under zsh; auto-skipped when $CI is set (tests/conftest.py), runs everywhere else
# Deselect the exec tests by DEFAULT so `mise run test` and CI
# `contract-preflight` (no Docker, no :dev image, no codex auth, no budget for
# paid calls) never run them. `mise run smoke-exec` / `mise run codex-lane-e2e`
# pass an explicit `-m` which overrides this (last -m wins). See
# tests/test_image_smoke_exec.py and tests/test_codex_lane_e2e.py.
#
# Parallel by default (host-load review 2026-10-02): `-n auto` asks
# tests/conftest.py's pytest_xdist_auto_num_workers, which answers with the
# ONE knob, PYTEST_XDIST_AUTO_NUM_WORKERS (xdist's own variable), defaulting to
# 4 workers on a shared 12-core host. Raise it per clone in mise.local.toml
# [env] to parallelize more; `-n 0` runs serially. `--dist loadgroup` keeps
# tests marked `xdist_group(name=...)` on one worker.
addopts = -m "not image_exec and not codex_exec" -n auto --dist loadgroup
error: Failed to initialize cache at `/Users/rmanaloto/Library/Caches/uv`
  Caused by: failed to open file `/Users/rmanaloto/Library/Caches/uv/sdists-v9/.git`: Operation not permitted (os error 1)

[35m[3mexec[0m[0m
[1m/bin/zsh -lc "printf '\\n--- installed git docs ---\\n'; ls /Library/Developer/CommandLineTools/usr/share/man/man1/git-init* /Library/Developer/CommandLineTools/usr/share/man/man5/githooks* /Library/Developer/CommandLineTools/usr/share/man/man1/git-worktree*; printf '\\n--- boundary-related rules ---\\n'; cat .claude/rules/probes-need-a-control-arm.md; printf '\\n--- changed lines ---\\n'; nl -ba python/src/dotfiles_setup/hook_selfcheck.py | sed -n '468,626p'; printf '\\n--- template usage ---\\n'; rg -n 'templateDir|TEMPLATE_DIR|post-checkout|hooksPath' home python/src/dotfiles_setup tests/test_hook_selfcheck.py .config/mise/conf.d/shared.toml"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[32m succeeded in 1383ms:[0m

--- installed git docs ---
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
/Library/Developer/CommandLineTools/usr/share/man/man1/git-init-db.1
/Library/Developer/CommandLineTools/usr/share/man/man1/git-init.1
/Library/Developer/CommandLineTools/usr/share/man/man1/git-worktree.1
/Library/Developer/CommandLineTools/usr/share/man/man5/githooks.5

--- boundary-related rules ---
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
# Probes Need a Control Arm: A Check That Can Only Pass Is Not a Check

Before you believe a probe's answer — especially a NEGATIVE one ("not found",
"doesn't exist", "it's dead", "no leaks") — prove the probe **can** produce the
other answer. Run it against a case you know succeeds, or a case you know
fails. A probe with no control arm is not evidence; it is a coin that only has
one face.

`tests/AGENTS.md` already states this for **tests**. This rule generalises it to
**every ad-hoc probe**: a `find`, a `curl`, a liveness check, a `grep`, a shell
one-liner in a Bash tool call. Those are where it actually bites, because
nothing reviews them.

## Why this rule exists

Session 2026-07-15 produced **five false negatives in one session**, every one
from a probe that could not have succeeded. The canonical one:
`find … -name 'agent-*.jsonl'` reported "AGENT DEAD, no transcript" — teammate
transcripts are `<uuid>.jsonl`, so the glob **can never match**. The agent was
alive and had delivered a 34 KB report.

The **inverse** bites too. `cmd | grep -q PAT` under `set -o pipefail` returns
**141**, so the check fails *because the match succeeded* — a probe that can
only fail. That broke the #289 base build; see `no_grep_q_under_pipefail` in
`hk.pkl`.

## Cross-check: when two probes disagree, one of them is broken

The cheapest bug detector available is a **second probe of the same fact by a
different route**. No fixture, no reasoning: if two probes of one fact disagree
you have found a defect for free — and it is in a probe far more often than in
the world. Reach for it the moment a result surprises you, *before* you write up
the surprise.

It names *which* answer to distrust. A lone probe returning "MISSING" is
indistinguishable from a probe that cannot see; a second route returning
"PRESENT" proves the first one is blind.

**Source beats issue tracker; a tool's claim about a platform ages.** The
recurring shape is a *secondary* artifact (an unclosed issue, a dependency's
README) read as the current state of a *primary* one (the shipped source, the
platform's API). Issues stay open after the fix lands; vendored docs freeze at
their commit date. When a secondary source says "impossible" and it matters,
**go read the code or the owner's docs**.

Full case tables — five false negatives, five cross-check disagreements:
`docs/rules-evidence/probes-need-a-control-arm.md`.

## Rules

1. **Arm the negative.** Before reporting "X does not exist", run the same probe
   against something that **does** exist. If it can't find that either, your
   probe is broken, not the world.
2. **Arm the positive.** Before reporting "the gate works", reintroduce the bug
   and confirm it **fails**. A gate verified only on clean code is decoration.
   (Doing this caught a broken test harness in this very session — `pkl eval -x`
   returned empty, so `bash -c ""` "passed".)

   **Reintroduce the bug REALISTICALLY.** A mutation must actually *destroy*
   what the check looks for (renaming a symbol leaves the original as a
   substring, so a substring check is a no-op), and it must be a break that
   could **really happen** — usually deleting the wiring line that calls a
   function, not renaming the function. Ask "what would the regression actually
   look like?" before mutating.
3. **Bound-limited searches are suspect by construction.** `-maxdepth`,
   `head -N`, `--limit`, a time window, a `2>/dev/null`: each can turn "absent"
   into "unreachable". Either remove the bound or prove the target is inside it.

   Bounds come in more forms than they look: **display bounds** (`| head`,
   `| tail`, a bare `ls` of a large dir), **checking N exact paths** instead of
   asking "does it exist anywhere", **relative time bounds** that a given `find`
   cannot parse, **YOUR OWN PARSER** (a single-line regex over a multi-line
   record silently drops the tail — a `^: ts;(.*)$` read of `~/.zsh_history`
   hid the very command a 4-hour investigation was hunting, and the absence was
   published as a finding), and — most common of all — **a TOKEN SPELLING**. A
   session once grepped `lmstudio`/`lm_studio`, got 0, and reported the feature
   unsupported; it is spelled `LM Studio`, with a space.

   **The sneakiest bound is WHEN YOU RAN IT.** If the causal condition has
   already been repaired — often by your own earlier commands — the probe cannot
   reproduce it, and "cannot reproduce" is not "no cause". Before reporting a
   null, ask **"could this still be true right now?"** and say *"the condition
   has passed, so this probe cannot speak to it"* — which locates the ignorance
   in the probe — rather than *"unattributed"*, which locates it in the world.

   **Arm the component you actually depend on**, not an adjacent one: a control
   arm aimed at the wrong link certifies the one thing never in doubt.

   The habit that catches every one: **a 0-result grep is not an answer until a
   control arm has run.** Before reporting absence, grep a term you KNOW is
   present in the same corpus with the same command shape. If that also returns
   0, the probe is broken — not the world.

   **Invent the known-absent term FRESH every time — writing one down destroys
   it.** A control string published in a report or receipt is now IN the corpus,
   so the next run's "absent" arm returns hits and the probe silently stops
   discriminating. Measured 2026-08-01: `zzqqxx`, the arm three prior receipts
   all used, returned **5 files** — three of them those receipts.
4. **A redirect/timeout/parse-error is not a "no".** HTTP 301/000, a `jq` miss,
   an empty `grep` — distinguish "answered no" from "never asked".
5. **Say which arm you ran.** When reporting a probe result, state the control:
   "bogus-dist → 404 while resolute-22 → 200, so the probe discriminates." A
   result without its control is an opinion.
6. **An INHERITED number is not a measurement — re-derive it or label it.** A
   figure that arrives from a handoff, a prior session's table, or your own
   earlier message has *no control arm attached*. Repeating it converts someone
   else's unverified note into your finding, and the provenance is gone the
   moment you restate it.

   So: before repeating an inherited number, either (a) re-derive it and say you
   did, or (b) mark it explicitly as unverified and inherited. When the number
   ranks things, ask what the **noise floor** is — a difference smaller than the
   same-input variance is not a difference.

7. **Cross-check a surprise before you report it.** A second route to the same
   fact costs seconds and settles which side is broken. Disagreement is a
   finding, not noise — and the finding is usually your probe.

8. **Arm the FIXTURE too: "could this setup have produced the other result?"**
   Rules 1–7 verify the *probe* discriminates. They say nothing about whether
   the *world you built for it* admits both answers — and a fully-armed probe on
   a rigged fixture yields a confident wrong finding (a #441 fixture named two
   secrets no single profile could hold, forcing all six arms to one outcome).
   Ask the question *before* reading the output, and prefer a fixture that
   mirrors the real configuration over one that isolates the variable.

9. **When you must BUILD a check, assert the capability — never sniff for a
   symptom of its absence.** A symptom check binds something you do not own: a
   log string, a version number, a warning's wording. When that changes upstream
   your check silently becomes a no-op that can only pass, and nothing tells you.
   Instead feed the tool an input it **must fail on** and require the failure —
   the gate then carries its own control arm on every run, and it tests the
   thing you depend on rather than a proxy for it.

   Worked case (#644): `renovate-config-validator` warns *"RE2 not usable"* and
   **still exits 0**, so every regex went unchecked while the gate stayed green.
   The fix validates a canary config whose only flaw is a lookahead and demands
   a non-zero exit. **A canary tests the binary that RUNS; a version tests the
   one you believe you installed** — `mise which` reported the fixed version
   while `PATH` still resolved the stale one. The inversion makes the canary
   itself load-bearing: pin that it is still genuinely invalid, or a later
   "tidy-up" neuters the gate toward silence.

## Applies to

Every probe whose answer you act on or report: shell one-liners, `find`/`grep`
sweeps, HTTP checks, agent-liveness checks, "is it installed" checks, and the
FAIL direction of every gate added to `hk.pkl` or `suites.toml`.

## See also

- `tests/AGENTS.md` — the same principle for the test suite (tautological tests
  + probes with no control arm; both are silent false negatives).
- `.claude/rules/verify-before-advancing.md` — evidence discipline: read the
  real `rc`/`conclusion`, never a piped tail.
- `hk.pkl` `no_grep_q_under_pipefail` — the machine-enforced instance of the
  inverse (a probe that can only fail).
- Memory `feedback_agent_spawn_liveness` — the liveness probe this rule's
  headline example broke, now corrected.
- Memory `feedback_pipe_kills_exit_code` — the sibling: a success signal from a
  wrapper is not a success signal from the thing you care about.

--- changed lines ---
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
mise WARN  failed to write cache file: /Users/rmanaloto/Library/Caches/mise/vfox-jdx-vfox-eza/0.23.5/exec_env_778dacdb4c5cdbb8-e1804.msgpack.z Operation not permitted (os error 1)
   468	            "pretooluse wrapper was not silent on a COMPLIANT AskUserQuestion — "
   469	            f"the gate denies every ask: {allowed.stdout.strip()!r}"
   470	        )
   471	    return failures
   472	
   473	
   474	def _worktree_fixture(tmp: Path, env: dict[str, str]) -> tuple[Path, Path, Path]:
   475	    """A real repo with one managed and one sibling linked worktree (#1606).
   476	
   477	    The sibling is the a8d7baf5 shape (``<tmp>/repo.worktrees/lane``): it
   478	    EXISTS and is REGISTERED, so a guard can only deny it for its location.
   479	    Raises :class:`subprocess.CalledProcessError` when git cannot build it.
   480	
   481	    The fixture's git ignores global/system config and hooks: a host-wide hook
   482	    (hk's ``hook.hk-*`` in ``~/.gitconfig``) must not be able to reject the
   483	    fixture commit and turn both arms red for a reason unrelated to the guard.
   484	    """
   485	    env = {**env, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
   486	    main = tmp / "repo"
   487	    managed = main / ".claude" / "worktrees" / "lane"
   488	    sibling = tmp / "repo.worktrees" / "lane"
   489	    main.mkdir()
   490	    cfg = ["-c", "user.name=selfcheck", "-c", "user.email=selfcheck@invalid"]
   491	    cfg += ["-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}"]
   492	    for args in (
   493	        ["init", "-b", "main"],
   494	        [*cfg, "commit", "--allow-empty", "-m", "x"],
   495	        ["worktree", "add", "-b", "managed", str(managed)],
   496	        ["worktree", "add", "-b", "sibling", str(sibling)],
   497	    ):
   498	        subprocess.run(
   499	            ["git", *args],
   500	            cwd=main,
   501	            env=env,
   502	            capture_output=True,
   503	            check=True,
   504	            timeout=_PROBE_TIMEOUT_S,
   505	        )
   506	    return main, managed, sibling
   507	
   508	
   509	def _enterworktree(path: Path, cwd: Path) -> str:
   510	    """An EnterWorktree payload whose session cwd anchors the guard's repo."""
   511	    return json.dumps(
   512	        {
   513	            "tool_name": "EnterWorktree",
   514	            "tool_input": {"path": str(path)},
   515	            "cwd": str(cwd),
   516	        }
   517	    )
   518	
   519	
   520	def _worktree_path_arm_failures(
   521	    denied: subprocess.CompletedProcess[str],
   522	    path_allowed: subprocess.CompletedProcess[str],
   523	) -> list[str]:
   524	    """Judge the sibling-deny and managed-allow ``path=`` arms."""
   525	    failures: list[str] = []
   526	    if denied.returncode != 0:
   527	        failures.append(
   528	            f"pretooluse wrapper exited {denied.returncode} on a sibling "
   529	            f"EnterWorktree path (must exit 0): {denied.stderr.strip()}"
   530	        )
   531	    elif '"permissionDecision": "deny"' not in denied.stdout:
   532	        failures.append(
   533	            "pretooluse wrapper did not DENY a registered sibling worktree outside "
   534	            ".claude/worktrees — the #1606 guard is not reachable or allows "
   535	            f"every path. stdout={denied.stdout.strip()!r}"
   536	        )
   537	    elif "must be an existing worktree under" not in denied.stdout:
   538	        failures.append(
   539	            "pretooluse EnterWorktree deny was not the LOCATION deny (did "
   540	            f"verification fail?): {denied.stdout.strip()!r}"
   541	        )
   542	    elif "#1606" not in denied.stdout or "EnterWorktree name=" not in denied.stdout:
   543	        failures.append("pretooluse EnterWorktree deny lost its #1606 name= redirect")
   544	
   545	    if path_allowed.returncode != 0:
   546	        failures.append(
   547	            f"pretooluse wrapper exited {path_allowed.returncode} on a managed "
   548	            f"EnterWorktree path: {path_allowed.stderr.strip()}"
   549	        )
   550	    elif path_allowed.stdout.strip():
   551	        failures.append(
   552	            "pretooluse wrapper was not silent on a registered worktree under "
   553	            ".claude/worktrees — the #1606 guard denies every path. "
   554	            f"stdout={path_allowed.stdout.strip()!r}"
   555	        )
   556	    return failures
   557	
   558	
   559	def check_worktree_guard_endtoend(project_root: Path, wrapper: str) -> list[str]:
   560	    """Drive EnterWorktree through the REAL wrapper: deny, path allow, name allow.
   561	
   562	    Matcher membership alone cannot detect a dispatcher that ignores the tool.
   563	    The deny arm targets an existing REGISTERED sibling worktree and the path
   564	    arm an existing registered managed one, on a real temp repo, so a guard
   565	    that denies every ``path=`` fails the allow arm and one that allows every
   566	    ``path=`` fails the deny arm. The payload ``cwd`` anchors the guard to that
   567	    repo; ``CLAUDE_PROJECT_DIR`` stays explicit for a linked-worktree selfcheck.
   568	    """
   569	    failures: list[str] = []
   570	    # Inherited Git-LOCAL state (a hook's GIT_DIR) would aim git at another
   571	    # repo; strip exactly the set git names, keeping config isolation such as
   572	    # GIT_CONFIG_GLOBAL (the fixture pins its own config isolation).
   573	    try:
   574	        local = process_env.git_local_env_names()
   575	    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
   576	        return [f"EnterWorktree selfcheck could not list git-local env vars: {exc}"]
   577	    env = {k: v for k, v in os.environ.items() if k not in local}
   578	    env["CLAUDE_PROJECT_DIR"] = str(project_root)
   579	    with tempfile.TemporaryDirectory(prefix="dotfiles-worktree-guard-") as tmp:
   580	        try:
   581	            main, managed, sibling = _worktree_fixture(Path(tmp).resolve(), env)
   582	        except (OSError, subprocess.SubprocessError) as exc:
   583	            return [f"EnterWorktree selfcheck could not build its git fixture: {exc}"]
   584	        denied = _run(
   585	            [_SYSTEM_BASH, wrapper],
   586	            stdin=_enterworktree(sibling, main),
   587	            cwd=project_root,
   588	            env=env,
   589	        )
   590	        path_allowed = _run(
   591	            [_SYSTEM_BASH, wrapper],
   592	            stdin=_enterworktree(managed, main),
   593	            cwd=project_root,
   594	            env=env,
   595	        )
   596	    failures.extend(_worktree_path_arm_failures(denied, path_allowed))
   597	    allowed = _run(
   598	        [_SYSTEM_BASH, wrapper],
   599	        stdin=json.dumps(
   600	            {"tool_name": "EnterWorktree", "tool_input": {"name": "selfcheck"}}
   601	        ),
   602	        cwd=project_root,
   603	        env=env,
   604	    )
   605	    if allowed.returncode != 0:
   606	        failures.append(
   607	            f"pretooluse wrapper exited {allowed.returncode} on EnterWorktree "
   608	            f"name=: {allowed.stderr.strip()}"
   609	        )
   610	    elif allowed.stdout.strip():
   611	        failures.append(
   612	            "pretooluse wrapper was not silent on EnterWorktree name=: "
   613	            f"{allowed.stdout.strip()!r}"
   614	        )
   615	    return failures
   616	
   617	
   618	def _offroot_env(project_root: Path) -> dict[str, str]:
   619	    """The hook's environment with this process's own venv resolution removed.
   620	
   621	    Drops ``VIRTUAL_ENV`` and every ``PATH`` entry inside the project, so the
   622	    wrapper must resolve the guard through ``$CLAUDE_PROJECT_DIR`` rather than
   623	    through a venv it happened to inherit. See :func:`check_offroot_arm`.
   624	
   625	    ``UV_PROJECT_ENVIRONMENT`` is deliberately PRESERVED, and that is a
   626	    correction, not an oversight. Stripping it broke the devcontainer, where

--- template usage ---
tests/test_hook_selfcheck.py:535:        f"[core]\n\thooksPath = {hooks}\n"
python/src/dotfiles_setup/hook_selfcheck.py:491:    cfg += ["-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}"]
python/src/dotfiles_setup/workflow_claude_code.py:214:        "post-checkout",

[35m[3mexec[0m[0m
[1m/bin/zsh -c "/usr/bin/grep -n -A45 -B5 'GIT_TEMPLATE_DIR\\|TEMPLATE DIRECTORY' /Library/Developer/CommandLineTools/usr/share/man/man1/git-init.1; /usr/bin/grep -n -A28 -B5 'post-checkout\\|post.checkout' /Library/Developer/CommandLineTools/usr/share/man/man5/githooks.5; /usr/bin/grep -n -A20 -B5 'post.checkout' /Library/Developer/CommandLineTools/usr/share/man/man1/git-worktree.1; /usr/bin/git diff --check 865454f9"'^ 865454f9; /usr/bin/git status --short'[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[32m succeeded in 0ms:[0m
94-.RE
95-.RE
96-.PP
97-\fB\-\-template=\fR\fI<template\-directory>\fR
98-.RS 4
99:Specify the directory from which templates will be used\&. (See the "TEMPLATE DIRECTORY" section below\&.)
100-.RE
101-.PP
102-\fB\-\-separate\-git\-dir=\fR\fI<git\-dir>\fR
103-.RS 4
104-Instead of initializing the repository as a directory to either
105-\fB$GIT_DIR\fR
106-or \&.\fB/\&.git/\fR, create a text file there containing the path to the actual repository\&. This file acts as a filesystem\-agnostic Git symbolic link to the repository\&.
107-.sp
108-If this is a reinitialization, the repository will be moved to the specified path\&.
109-.RE
110-.PP
111-\fB\-b\fR \fI<branch\-name>\fR, \fB\-\-initial\-branch=\fR\fI<branch\-name>\fR
112-.RS 4
113-Use
114-\fI<branch\-name>\fR
115-for the initial branch in the newly created repository\&. If not specified, fall back to the default name (currently
116-\fBmaster\fR, but this will change to
117-\fBmain\fR
118-when Git 3\&.0 is released)\&. The default name can be customized via the
119-\fBinit\&.defaultBranch\fR
120-configuration variable\&.
121-.RE
122-.PP
123-\fB\-\-shared\fR[\fB=\fR(\fBfalse\fR|\fBtrue\fR|\fBumask\fR|\fBgroup\fR|\fBall\fR|\fBworld\fR|\fBeverybody\fR|\fI<perm>\fR)]
124-.RS 4
125-Specify that the Git repository is to be shared amongst several users\&. This allows users belonging to the same group to push into that repository\&. When specified, the config variable
126-\fBcore\&.sharedRepository\fR
127-is set so that files and directories under
128-\fB$GIT_DIR\fR
129-are created with the requested permissions\&. When not specified, Git will use permissions reported by
130-\fBumask\fR(2)\&.
131-.sp
132-The option can have the following values, defaulting to
133-\fBgroup\fR
134-if no value is given:
135-.PP
136-\fBumask\fR, \fBfalse\fR
137-.RS 4
138-Use permissions reported by
139-\fBumask\fR(2)\&. The default, when
140-\fB\-\-shared\fR
141-is not specified\&.
142-.RE
143-.PP
144-\fBgroup\fR, \fBtrue\fR
--
185-.RE
186-.sp
187-By default, the configuration flag \fBreceive\&.denyNonFastForwards\fR is enabled in shared repositories, so that you cannot force a non fast\-forwarding push into it\&.
188-.sp
189-If you provide a \fI<directory>\fR, the command is run inside it\&. If this directory does not exist, it will be created\&.
190:.SH "TEMPLATE DIRECTORY"
191-.sp
192-Files and directories in the template directory whose name do not start with a dot will be copied to the \fB$GIT_DIR\fR after it is created\&.
193-.sp
194-The template directory will be one of the following (in order):
195-.sp
196-.RS 4
197-.ie n \{\
198-\h'-04'\(bu\h'+03'\c
199-.\}
200-.el \{\
201-.sp -1
202-.IP \(bu 2.3
203-.\}
204-the argument given with the
205-\fB\-\-template\fR
206-option;
207-.RE
208-.sp
209-.RS 4
210-.ie n \{\
211-\h'-04'\(bu\h'+03'\c
212-.\}
213-.el \{\
214-.sp -1
215-.IP \(bu 2.3
216-.\}
217-the contents of the
218:\fB$GIT_TEMPLATE_DIR\fR
219-environment variable;
220-.RE
221-.sp
222-.RS 4
223-.ie n \{\
224-\h'-04'\(bu\h'+03'\c
225-.\}
226-.el \{\
227-.sp -1
228-.IP \(bu 2.3
229-.\}
230-the
231-\fBinit\&.templateDir\fR
232-configuration variable; or
233-.RE
234-.sp
235-.RS 4
236-.ie n \{\
237-\h'-04'\(bu\h'+03'\c
238-.\}
239-.el \{\
240-.sp -1
241-.IP \(bu 2.3
242-.\}
243-the default template directory:
244-\fB/usr/share/git\-core/templates\fR\&.
245-.RE
246-.sp
247-The default template directory includes some directory structure, suggested "exclude patterns" (see \fBgitignore\fR(5)), and sample hook files\&.
248-.sp
249-The sample hooks are all disabled by default\&. To enable one of the sample hooks rename it by removing its \&.\fBsample\fR suffix\&.
250-.sp
251-See \fBgithooks\fR(5) for more general info on hook execution\&.
252-.SH "EXAMPLES"
253-.PP
254-Start a new Git repository for an existing code base
255-.RS 4
256-.sp
257-.if n \{\
258-.RS 4
259-.\}
260-.nf
261-$ cd /path/to/my/codebase
262-$ git init      \fB(1)\fR
263-$ git add \&.     \fB(2)\fR
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-6AhdeGAT' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-asMZaCfa' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-WoD0NXJm' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-xbp2gMUU' (errno=Operation not permitted)
?? docs/research/kb/reports/agents/cold-review-1606-0125fc4d.md

[35m[3mexec[0m[0m
[1m/bin/zsh -c "/usr/bin/grep -n -A28 -B4 -F 'post\\-checkout' /Library/Developer/CommandLineTools/usr/share/man/man5/githooks.5; /usr/bin/grep -n -A15 -B5 -F 'post\\-checkout' /Library/Developer/CommandLineTools/usr/share/man/man1/git-worktree.1; /usr/bin/grep -n -A12 -B5 'hooksPath' /Library/Developer/CommandLineTools/usr/share/man/man5/githooks.5"[0m in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606
[32m succeeded in 0ms:[0m
121-This hook is meant primarily for notification, and cannot affect the outcome of \fBgit\fR \fBcommit\fR\&.
122-.SS "pre\-rebase"
123-.sp
124-This hook is called by \fBgit-rebase\fR(1) and can be used to prevent a branch from getting rebased\&. The hook may be called with one or two parameters\&. The first parameter is the upstream from which the series was forked\&. The second parameter is the branch being rebased, and is not set when rebasing the current branch\&.
125:.SS "post\-checkout"
126-.sp
127-This hook is invoked when a \fBgit-checkout\fR(1) or \fBgit-switch\fR(1) is run after having updated the worktree\&. The hook is given three parameters: the ref of the previous HEAD, the ref of the new HEAD (which may or may not have changed), and a flag indicating whether the checkout was a branch checkout (changing branches, flag=1) or a file checkout (retrieving a file from the index, flag=0)\&. This hook cannot affect the outcome of \fBgit\fR \fBswitch\fR or \fBgit\fR \fBcheckout\fR, other than that the hook\(cqs exit status becomes the exit status of these two commands\&.
128-.sp
129-It is also run after \fBgit-clone\fR(1), unless the \fB\-\-no\-checkout\fR (\fB\-n\fR) option is used\&. The first parameter given to the hook is the null\-ref, the second the ref of the new HEAD and the flag is always 1\&. Likewise for \fBgit\fR \fBworktree\fR \fBadd\fR unless \fB\-\-no\-checkout\fR is used\&.
130-.sp
131-This hook can be used to perform repository validity checks, auto\-display differences from the previous HEAD if different, or set working dir metadata properties\&.
132-.SS "post\-merge"
133-.sp
134-This hook is invoked by \fBgit-merge\fR(1), which happens when a \fBgit\fR \fBpull\fR is done on a local repository\&. The hook takes a single parameter, a status flag specifying whether or not the merge being done was a squash merge\&. This hook cannot affect the outcome of \fBgit\fR \fBmerge\fR and is not executed, if the merge failed due to conflicts\&.
135-.sp
136-This hook can be used in conjunction with a corresponding pre\-commit hook to save and restore any form of metadata associated with the working tree (e\&.g\&.: permissions/ownership, ACLS, etc)\&. See contrib/hooks/setgitperms\&.perl for an example of how to do this\&.
137-.SS "pre\-push"
138-.sp
139-This hook is called by \fBgit-push\fR(1) and can be used to prevent a push from taking place\&. The hook is called with two parameters which provide the name and location of the destination remote, if a named remote is not being used both values will be the same\&.
140-.sp
141-Information about what is to be pushed is provided on the hook\(cqs standard input with lines of the form:
142-.sp
143-.if n \{\
144-.RS 4
145-.\}
146-.nf
147-<local\-ref> SP <local\-object\-name> SP <remote\-ref> SP <remote\-object\-name> LF
148-.fi
149-.if n \{\
150-.RE
151-.\}
152-.sp
153-For instance, if the command \fBgit\fR \fBpush\fR \fBorigin\fR \fBmaster:foreign\fR were run the hook would receive a line like the following:
29-.\" -----------------------------------------------------------------
30-.SH "NAME"
31-githooks \- Hooks used by Git
32-.SH "SYNOPSIS"
33-.sp
34:$GIT_DIR/hooks/* (or `git config core\&.hooksPath`/*)
35-.SH "DESCRIPTION"
36-.sp
37-Hooks are programs you can place in a hooks directory to trigger actions at certain points in git\(cqs execution\&. Hooks that don\(cqt have the executable bit set are ignored\&.
38-.sp
39:By default the hooks directory is \fB$GIT_DIR/hooks\fR, but that can be changed via the \fBcore\&.hooksPath\fR configuration variable (see \fBgit-config\fR(1))\&.
40-.sp
41-Before Git invokes a hook, it changes its working directory to either $GIT_DIR in a bare repository or the root of the working tree in a non\-bare repository\&. An exception are hooks triggered during a push (\fIpre\-receive\fR, \fIupdate\fR, \fIpost\-receive\fR, \fIpost\-update\fR, \fIpush\-to\-checkout\fR) which are always executed in $GIT_DIR\&.
42-.sp
43-Environment variables, such as \fBGIT_DIR\fR, \fBGIT_WORK_TREE\fR, etc\&., are exported so that Git commands run by the hook can correctly locate the repository\&. If your hook needs to invoke Git commands in a foreign repository or in a different working tree of the same repository, then it should clear these environment variables so they do not interfere with Git operations at the foreign location\&. For example:
44-.sp
45-.if n \{\
46-.RS 4
47-.\}
48-.nf
49-local_desc=$(git describe)
50-foreign_desc=$(unset $(git rev\-parse \-\-local\-env\-vars); git \-C \&.\&./foreign\-repo describe)
51-.fi

[35m[3mcodex[0m[0m
The narrower environment filter introduces a path for template-installed host hooks to execute during fixture creation. Runtime validation was blocked by the read-only sandbox; the finding follows from the code and installed Git documentation.

Review comment:

- [P2] Disable template-installed hooks during worktree creation — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606/python/src/dotfiles_setup/hook_selfcheck.py:491-495
  When `GIT_TEMPLATE_DIR` points to a template containing an executable `hooks/post-checkout`, the new environment filter preserves it because Git does not list it in `--local-env-vars`; previously it was stripped. `git init` consequently copies that hook into the fixture, but `core.hooksPath=/dev/null` applies only to the commit. Both `git worktree add` commands can therefore execute the host hook, and a rejecting hook fails the selfcheck and blocks ship/land despite a functioning guard. Disable template inheritance or apply the hook override to every fixture Git invocation.
The narrower environment filter introduces a path for template-installed host hooks to execute during fixture creation. Runtime validation was blocked by the read-only sandbox; the finding follows from the code and installed Git documentation.

Review comment:

- [P2] Disable template-installed hooks during worktree creation — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606/python/src/dotfiles_setup/hook_selfcheck.py:491-495
  When `GIT_TEMPLATE_DIR` points to a template containing an executable `hooks/post-checkout`, the new environment filter preserves it because Git does not list it in `--local-env-vars`; previously it was stripped. `git init` consequently copies that hook into the fixture, but `core.hooksPath=/dev/null` applies only to the commit. Both `git worktree add` commands can therefore execute the host hook, and a rejecting hook fails the selfcheck and blocks ship/land despite a functioning guard. Disable template inheritance or apply the hook override to every fixture Git invocation.
rc=0
