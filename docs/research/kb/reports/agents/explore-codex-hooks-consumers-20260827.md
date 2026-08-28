# Explore agent report — consumers of `.codex/hooks.json` before its removal (2026-08-27, session ad30e818, #796)

Brief: `.codex/hooks.json` (only the two writer-lease hooks) is about to be deleted per Ray's decision; Claude's wiring in `.claude/settings.json` stays. Map every test, contract token and prose line that depends on the file so the follow-through can be specced. Persisted verbatim at receipt per `.claude/rules/agent-report-persistence.md`.

---

## 1. `tests/test_writer_lease.py` — the 7 `.codex/hooks.json` readers

All seven do the same extraction: `json.loads(project_root/".codex/hooks.json")` then `["hooks"]["PreToolUse"][0]["hooks"][0]["command"]`. **No test reads `matcher` or `timeout`.** Only one reads the PostToolUse command, and only to assert byte-equality with Pre. Every invocation is `subprocess.run(["/bin/sh","-c",command], cwd=<nested>, input=json.dumps(payload).encode(), capture_output=True, check=False, timeout=10)` — inherited env, no `env=`, and the payload always carries `"cwd": str(nested)` equal to the process cwd.

| # | Test (lines) | JSON read | Property proven | Runner-reachable? |
|---|---|---|---|---|
| 1229 | `test_pinned_system_runner_uses_real_project_runtime_and_drains_posttooluse` **:1207-1297** | Pre **and** Post `command`; asserts `pre_command == post_command` (:1232) | Builds a fake repo (venv symlink, copied `dotfiles_setup`, copied runner, `mise-system.lock`), nested cwd with its own `.git` at `nested/.git`. Owner Pre registers `runner-tool`, Post drains it (`_status(repo)["inflight"] == []`), hostile session denied | **Yes.** Nothing here is locator-specific except the Pre==Post identity assertion. Drive `/usr/bin/python3 -I -S <repo>/scripts/writer-lease-hook-runner.py` with the same payload. Note `nested/.git` exists, so the *locator* would pick `nested` — but `nested` has no `scripts/` so it falls through to `repo`; the runner's `_runtime()` (:89 `for candidate in (current, *current.parents)`) does the identical walk on `payload["cwd"]` |
| 1303 | `test_codex_hook_command_reaches_the_tracked_runner_from_nested_cwd` **:1300-1334** | Pre `command` | Shape assertions on the inline text (`arguments[:4] == ["/usr/bin/python3","-I","-S","-c"]`, `len==5`, no `/usr/bin/git`, `/bin/sh`, `PATH=`, ` env `) at :1306-1312, then runs from the real repo's `python/src/dotfiles_setup` and asserts a plain `deny`, not `enforcement failed closed` | **Half.** The argv-shape half is *purely* the inline locator's text and dies with the file. The behavioural half (nested cwd → deny, no fail-closed) is `_runtime()`'s walk |
| 1358 | `test_codex_hook_selects_inner_runner_beneath_unrelated_outer_repo` **:1337-1381** | Pre `command` | Outer git repo with **no** runner/hook; inner complete repo; cwd `inner/nested/session`. Outer `.git` must not shadow the inner runtime → deny, not fail-closed | **Yes.** `_runtime()` collects only *complete* candidates (:94-104 must open `.git`, `scripts/…runner.py`, `codex_writer_lease_hook.py`); the incomplete outer is skipped at :105-113 |
| 1420 | `test_codex_hook_blocks_ambiguous_complete_outer_runtime` **:1384-1459** | Pre `command` | Two complete runtimes (outer gets a decoy runner that would write a marker file + a decoy hook). Asserts `returncode == 2`, `stdout == b""`, `stderr == b"Writer lease tracked runtime is ambiguous.\n"`, marker absent (:1440-1443). Then deletes the outer hook and re-runs as a control arm (:1445-1459) | **No, not as written.** This is the locator's `len(roots)!=1` branch. `_runtime()` *does* replicate the detection (:115-121 `if len(candidates)==1` … `_fail("hook cwd has ambiguous complete writer-hook runtimes")`) but not the *shape*: a runner-driven ambiguity is caught in `main()` (:183-191) and surfaces as **exit 0 with a structured deny/stop JSON** carrying `"Writer lease enforcement failed closed: …"`, never exit 2 / stderr. Retarget requires flipping the assertions to the deny-JSON shape (and dropping the `"enforcement failed closed" not in …` control) |
| 1505 | `test_codex_hook_ignores_incomplete_outer_runtime_candidates` **:1462-1528** (parametrized `missing`, `wrong-type`, `symlink`, `parent-symlink` at :1462-1464) | Pre `command` | Outer candidate is disqualified per shape (dir instead of file, leaf symlink, parent-dir symlink) → still a single valid inner runtime → deny, not fail-closed | **Yes.** `_open_relative()` (:57-80) applies `O_NOFOLLOW` per component + the `S_ISREG` kind check at :69-75 — identical semantics to the inline `open_relative` |
| 1596 | `test_codex_hook_symlink_components_cannot_redirect_pre_post_lifecycle` **:1531-1624** (parametrized `parent-symlinks`, `git-symlink`) | Pre `command` (inline `json.loads(...)[...]` at :1595-1597) | Decoy outer runner/hook that `raise`s if executed, reached only via symlinked `scripts/`,`python/` or a symlinked outer `.git`. Real inner holder's Pre+Post both succeed with empty stdout and `inflight == []` | **Yes.** `_open_root()` rejects symlinked roots (:46-47) and the `.git` probe at :94 uses `O_NOFOLLOW`, so a symlinked outer `.git` disqualifies the outer candidate exactly as in the locator |
| 1683 | `test_codex_hook_blocks_when_no_complete_runtime_candidate_exists` **:1627-1706** (7 shapes: `no-marker`, `missing-runner`, `runner-wrong-type`, `runner-symlink`, `hook-symlink`, `parent-symlink`, `git-symlink`) | Pre `command` | Sole candidate is incomplete/redirected → `returncode == 2`, `stdout == b""`, `stderr == b"Writer lease tracked runtime is unavailable.\n"`, decoy marker never written | **No, not as written** — same mismatch as 1420. `_runtime()` has the equivalent branch (:122 `_fail("hook cwd has no complete tracked writer-hook runtime")`) but emits an exit-0 deny JSON. The "decoy runner never executed" half also weakens: the locator *executes* the located runner's bytes, whereas a runner-driven test already names the runner in argv, so `parent-symlink`/`runner-symlink`/`runner-wrong-type` become assertions about which *hook entrypoint* is bound (`hook_fd`, :100-104), not which runner is exec'd |

Net: **5 of 7 retarget cleanly** onto `scripts/writer-lease-hook-runner.py` driven with the Claude command shape (`/usr/bin/python3 -I -S <root>/scripts/writer-lease-hook-runner.py`, payload `cwd` = nested). **1420 and 1683 need rewritten assertions** (exit 2 + fixed stderr → exit 0 + `"Writer lease enforcement failed closed: … ambiguous/no complete tracked writer-hook runtime"` in the decision reason), and **1303's argv-shape block (:1306-1312) has no successor** — the `-c`/no-git/no-PATH property is a fact about the inline string only.

Also note `_runtime()` walks `payload["cwd"]` while the locator walks `Path.cwd()`. Every one of these tests sets both to the same value, so no test currently distinguishes them.

## 2. Other readers

- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:2143` — `.codex/hooks.json` is in `paths` of the `workflow.writer-lease` suite (`handler = "require_tokens"`, `paths_required = true`, :2137-2138). **Deleting the file fails this gate**, both on the missing path and on the two `per_path_tokens` at :2155: `'"statusMessage": "Checking repository writer lease"'` and `'"statusMessage": "Draining repository writer lease mutation"'`.
- Same line **:2155**, `tests/test_writer_lease.py` tokens include five of these function names verbatim — `test_codex_hook_command_reaches_the_tracked_runner_from_nested_cwd(`, `…selects_inner_runner_beneath_unrelated_outer_repo(`, `…blocks_ambiguous_complete_outer_runtime(`, `…symlink_components_cannot_redirect_pre_post_lifecycle(`, `test_pinned_system_runner_uses_real_project_runtime_and_drains_posttooluse(`. Renaming or deleting any of them breaks the contract.
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.gitignore:55` — `!.codex/hooks.json` un-ignore rule; becomes dead.
- `docs/specs/codex-writer-lease.md:119` — the only prose path reference (see §3).
- No other reader. Grep for `Writer lease tracked runtime` hits only `.codex/hooks.json`, `tests/test_writer_lease.py` (:1442, :1705) and `docs/research/**` (excluded). `codex_writer_lease_hook` outside the package hits only `scripts/writer-lease-hook-runner.py:102,147` and `suites.toml:2148`.

## 3. Prose that becomes false

**`docs/specs/codex-writer-lease.md`**
- **:117-140** "Hook enforcement and background processes" — :119-121 "Both `.codex/hooks.json` and `.claude/settings.json` use the same tracked runner"; :126-136 the whole Codex-docs paragraph (commands run from session `cwd`, "Codex exposes no documented project-root variable, so its pinned Python command walks ancestors…", "two complete runtimes are ambiguous and exit `2` before mutation", "executes the runner bytes read from the already-admitted descriptor"). Only the last two sentences (:136-140, the runner's own descriptor walk + fail-closed bridge) survive.
- **:142-147** the Codex pre-lease bootstrap paragraph — the *shape* still lives in `codex_writer_lease_hook.py`, but "Codex allows" is no longer enforced by a Codex hook.
- **:157-161** the linked-worktree / `--dangerously-bypass-hook-trust` certification paragraph — pure Codex-hook process. ⚠️ `--dangerously-bypass-hook-trust` is a contract token for this file at `suites.toml:2155`; deleting :160 breaks the gate.
- **:255** evidence item 6 "Claude Bash and **Codex** Bash/apply-patch controls deny a second session".
- **:256-257** item 7 — the delayed-Bash drain is Codex unified-exec framed.
- **:260-267** item 9 — the largest casualty: "The same configured **Codex command** starts from a nested repository directory… requires exactly one complete runtime… exits `2`, the documented Codex blocking status." This is verbatim the 7 tests above.
- **:273-274** item 11 is Claude-only and stays.
- **Architecture mermaid :165-191** — node `PRE["Native PreToolUse"]` is fed by `T["Codex or Claude task"]` (:167), and `ROOT["Pinned Python: exactly one complete runtime"]` (:168) describes the locator. ⚠️ `Pinned Python: exactly one complete runtime` is a contract token at `suites.toml:2155` — do not delete that node text without updating the suite. (`RUNNER["Descriptor-bound tracked runner bytes"]` :169 stays true of the runner.)

**`.claude/rules/writer-lease.md`**
- **:85-94** — the entire Codex-locator paragraph ("Codex runs hook commands from the session working directory… The pinned system-Python hook command therefore walks ancestors… Missing or ambiguous complete candidates exit `2` before mutation. The locator binds the selected root inode and executes the runner bytes…"). Only the trailing runner clause (:92-94) survives.
- **:96-97** "Codex and Claude `PreToolUse` register…" — drop "Codex and". None of this file's three contract tokens sit in these sentences (they are `# Repository writer lease`, `immutable, content-addressed 64-event chunks`, `` `PostToolUseFailure` drains failed tools ``), so this edit is token-safe.

**`docs/agents/codex-task-orchestration.md:64-75`**
- :69-72 "The tracked **Codex and Claude** `PreToolUse` hooks bind… Their `PostToolUse` hooks drain those exact IDs" and :74-75 "Review changed **Codex hook hashes with `/hooks`** before treating the enforcement as active."
- ⚠️ **Token collision:** `` `PostToolUse` hooks drain those exact IDs `` (`suites.toml:2155`) is inside the sentence at **:71**. The other token for this file (`G --> WL["Successor acquires Git-common-dir writer lease"]`) is in the mermaid block, untouched.

**`.agents/skills/codex-task-orchestration/SKILL.md:175-186`**
- :179-181 "The repository's native `PreToolUse` hook must bind each mutation to the live holder and its `PostToolUse` hook must drain that exact tool ID" — false for a Codex successor.
- :183-185 "The successor must also confirm that the repository's native **Codex hook hash is trusted**; `/hooks` is the review surface…" — wholly false once the file is gone.
- ⚠️ **Token collision:** `` `PostToolUse` hook must drain `` (`suites.toml:2155`) is inside :180. `must acquire that Git-common-dir` (:177) is in the preceding, still-true sentence; `native writer-lease task` (:176) likewise safe.

## 4. `codex_writer_lease_hook.py` — stays

Confirmed. `scripts/writer-lease-hook-runner.py:147` builds `hook = root/"python"/"src"/"dotfiles_setup"/"codex_writer_lease_hook.py"` and execs it via the bootstrap at :148-164 — that is the Claude path too (`.claude/settings.json` → runner → this file). It is also required as a runtime *component* by `_runtime()` at :100-104: the ancestor walk refuses any root lacking it, so deleting it would make every Claude hook fail closed. It further carries two contract tokens at `suites.toml:2155` (`codex_pretooluse_decision(payload)`, `event in {"PostToolUse", "PostToolUseFailure"}`) and is a required path at `:2148`. Misleading name, load-bearing file — leave it (or rename it as a separate, coordinated change across `:102`, `:147`, and both `suites.toml` lines).

---

## GitHub repos touched

_None._ (local tree only)
