<!-- Verbatim output of workflow wf_098e966c-fbb, 2026-07-27.
     25 agents. 20 findings, ALL 20 PASS verdicts overturned on adversarial review.
     Persisted unedited per .claude/rules/agent-report-persistence.md. -->

# knowledge-base — standalone readiness verdict

Reviewed at `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base`, branch `feat/kb-project-plugins` @ `6c41bc3`, CLI `claude 2.1.220`, `mise 2026.7.14`.

Every claim in the first-pass review was overturned on adversarial re-check. What follows is the corrected picture, re-derived here.

---

## 1. Verdict

### On THIS machine, right now: **YES, with two carve-outs**

A Claude Code session with cwd = knowledge-base and **no** `--add-dir dotfiles` loads `.claude/settings.json`, and its hooks execute correctly. Measured, control-armed:

```
$ cd /private/tmp   # neutral cwd, so nothing falls back to the KB project
$ echo '{"tool_name":"Bash","tool_input":{"command":"graphify add https://x.com"}}' \
    | uv run --project /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python kb-setup hookguard
{"hookSpecificOutput": {... "permissionDecision": "deny", ... "Use the mise task: mise run kb-add -- <url>" ...}}
rc=0
```
Control arm (`echo hello`) → empty stdout, rc=0. The probe discriminates.

Carve-outs:

- **`mise run cc` — the repo's own documented launcher — cannot run standalone.** `mise.toml:344` hardcodes `--sibling "$MISE_PROJECT_ROOT/../dotfiles"`; `launch.py:190-191` turns a missing sibling into a blocking problem and `launch.py:314-323` prints `[cc] refusing to launch — the environment would lie` and returns 1. This is the single hardest KB→dotfiles coupling in the repo.
- **`permissions.defaultMode: "auto"` works here for the wrong reason** — see §2.

### On a FRESH CLONE (new path, or a machine with no `~/.claude`): **NO**

Nine defects, three of them hard blockers. The worst is not a lost feature — it is an *outage*:

```
$ echo '{...}' | uv run --project /Users/rmanaloto/NOPE/knowledge-base/python kb-setup hookguard
error: Failed to spawn: `kb-setup`
rc=2
```
PreToolUse **rc=2 is Claude Code's blocking exit code**. A clone at any path other than `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base` would have every Bash call denied, not merely unguarded. The two sibling hooks fail differently but on the same cause:

```
$ mise exec -C /Users/rmanaloto/NOPE/knowledge-base -- graphify --version
mise ERROR Directory specified with --cd does not exist: ~/NOPE/knowledge-base
rc=1
```

The portable idiom was available and is used **two hooks lower in the same file** (`"${CLAUDE_PROJECT_DIR:-.}"`, `.claude/settings.json:48` and `:59`). Three hooks absolute, two portable, one file — drift, not design.

---

## 2. What still depends on dotfiles or on `~/.claude`

| # | Dependency | Evidence | Matters? |
|---|---|---|---|
| D1 | **`mise run cc` requires `../dotfiles`** | `mise.toml:344`; `launch.py:190-191`, `:314-323` | **Yes — blocker.** The canonical launcher is unusable standalone. |
| D2 | **3 hooks hardcode this clone's absolute path** | `.claude/settings.json:16,26,36` | **Yes — blocker.** rc=2 (blocking) on the `uv` hook, rc=1 on the two `mise exec` hooks. |
| D3 | **`astral@astral-sh` enabled, marketplace undeclared** | `.claude/settings.json:69` (enabled) vs `:73-92` (only 3 marketplaces). Absent from `~/.claude/settings.json` `extraKnownMarketplaces` (19 keys, no `astral-sh`); present only in machine-local `~/.claude/plugins/known_marketplaces.json` | **Yes.** The `astral:ruff`/`ty`/`uv` skills — core tooling for a uv/Python repo — do not resolve on a fresh clone. |
| D4 | **`pr-review-toolkit@claude-plugins-official` project entry unproven** | `.claude/settings.json:71`; also `true` in `~/.claude/settings.json` `enabledPlugins`; `claude plugin list` reports it `Scope: user` | Medium. Marketplace is CLI-bundled (auto-install, network + one-shot `officialMarketplaceAutoInstallAttempted` flag), so it *probably* resolves — but its working here is attributable to user settings, not the project file. |
| D5 | **`tmux` not pinned by KB** | `[tools]` in `mise.toml:13-46` has no tmux; `mise ls --current` → `tmux 3.7b … ~/.config/mise/config.toml`. `launch.py:196-197` makes a missing tmux a blocking preflight problem | **Yes** for `mise run cc`. User-level config supplies it. |
| D6 | **mise config trust comes from a chezmoi/dotfiles-managed user file** | `~/.config/mise/config.toml:3-5` "managed by chezmoi … Applied by: chezmoi apply", `:15 trusted_config_paths = ["/"]` | **Yes.** Without it, every `mise run` in a fresh clone errors with "Config files … are not trusted", including the SessionStart hook. |
| D7 | **`permissions.defaultMode: "auto"` is source-restricted** | `.claude/settings.json:7`; binary 2.1.220 strings: `"ignored as repo-controllable — only policy, user, and CLI-flag sources may grant auto mode"`; the settings validator's own list omits `auto`: `Valid modes: "acceptEdits" … "plan" … "bypassPermissions" … "default"`. Auto mode here actually comes from `~/.claude/settings.json` (`defaultMode: auto`) | **Yes.** The project line is inert at best; bundled-skill text says an ignored project entry can *shadow* the user-scope value. |
| D8 | **SessionEnd audit is a no-op on a fresh clone** | `brain.py:611-624` returns 0 on "no transcripts" **before** the `dest.parent.mkdir` at `:631`; transcript base is `CLAUDE_CONFIG_DIR` or `~/.claude/projects` (`brain.py:427`) | Low severity, but it means "it exits 0" is not "it works". |
| D9 | **graphify guard hooks are inert without the graph** | `.gitignore:22` ignores `graphify-out/graph.json`; the hooks' payload is emitted only when it exists | Medium. 2 of 5 hooks do nothing until a full `mise run kb-build`. |
| D10 | **3 dangling rule cross-references** | `.claude/rules/agent-report-persistence.md:78`, `md-size-budgets.md:122`, `notepad-enforcement.md:62` all cite `omc-directory-conventions.md`; that file does not exist — it was renamed to `agent-artifact-conventions.md`. Control arm: `git grep -c agent-artifact-conventions` → **0 hits repo-wide**, while `git grep -c notepad-enforcement -- .claude` → 2 files, so the probe discriminates | Low. Cosmetic, but fresh-clone-visible and cheap. |
| D11 | **`graphify` on raw PATH is the wrong version** | `command -v graphify` → `…/pipx-graphifyy/0.9.25/bin/graphify`, `graphify --version` → `0.9.25`, vs `mise.toml:23` pin `0.9.26`. `mise exec -- graphify --version` → `0.9.26` | Machine-local, but real: it is exactly the failure `launch.py` exists to prevent, and it is live in the current session. |

**Not a dependency (verified clean):** `~/.claude/settings.json` has **no `hooks` key**, so KB's 5 hooks are the entire hook surface. No `.claude/settings.local.json` exists. `~/.claude/skills/` is empty — none of dotfiles' 24 skills leak in. KB tracks all 38 of its `.claude/**` files (`git ls-files .claude | wc -l` → 38), including `settings.json`.

---

## 3. Fresh-clone bootstrap

Prerequisites the repo does **not** provide and cannot: `mise`, `uv`, Python ≥3.14 (`pyproject.toml:5`), `git`, `tmux`, `claude`, and a `~/.claude` directory.

```bash
# 0. Prereqs (host-level, one-time)
brew install tmux                      # KB pins no tmux; launch.py:196-197 requires it
curl https://mise.run | sh             # then ensure ~/.local/share/mise/shims precedes install dirs on PATH

# 1. Clone
git clone git@github.com:ray-manaloto/knowledge-base.git
cd knowledge-base

# 2. Trust the repo config (otherwise every `mise run` errors)
mise trust

# 3. Install the pinned toolchain (13 tools incl. conda:ffmpeg, pipx:graphifyy[all])
mise install                           # minutes, not seconds — exceeds the 30s SessionStart hook timeout on first run

# 4. Python env
uv sync

# 5. REQUIRED PATCHES — the clone is not usable as-shipped:
#    a) .claude/settings.json:16,26,36 — replace the hardcoded
#       /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base
#       with "${CLAUDE_PROJECT_DIR:-.}"  (matching lines 48 and 59)
#    b) .claude/settings.json:73 — add the missing marketplace:
#       "astral-sh": { "source": { "source": "github", "repo": "astral-sh/claude-code-plugins" } }
#    c) .claude/settings.json:6-8 — remove permissions.defaultMode:"auto" (ignored at project
#       scope) and instead set it in ~/.claude/settings.json, or pass --permission-mode auto
#    d) mise.toml:344 — either clone dotfiles as a sibling, or make --sibling optional

# 6. Build the graph (otherwise 2 of 5 hooks are inert)
mise run kb-build

# 7. Verify
mise run check
```

Step 5 is not optional polish — without (a) the clone's Bash tool is broken, and without (d) `mise run cc` refuses to start.

---

## 4. First-turn checks for a session

Each pair is an arm + a control arm. A check with only one arm is discarded.

**C1 — is the PreToolUse guard actually wired and deciding?**
```bash
cd /private/tmp   # neutral cwd: prevents uv falling back to the ambient project
echo '{"tool_name":"Bash","tool_input":{"command":"graphify add https://x.com"}}' \
  | uv run --project "$KB/python" kb-setup hookguard          # expect: deny JSON, rc=0
echo '{"tool_name":"Bash","tool_input":{"command":"echo hello"}}' \
  | uv run --project "$KB/python" kb-setup hookguard          # CONTROL: empty stdout, rc=0
```
Both arms differ ⇒ the guard discriminates. If the deny arm is silent, the guard is dead — treat every "no policy violation" result that session as unverified.

**C2 — is the guard wired *in the session*, not just callable?** (This is the gap nothing in the repo covers.)
```bash
env ZZPROBE=1 graphify zzz-nonexistent-subcommand
# expect: DENIED by the hook.  If it EXECUTES and prints "error: unknown command",
# the session-layer guard is inert even though C1 passed.
```
The adversarial pass measured exactly this failing in a session where KB was an added directory rather than the project root.

**C3 — does the graphify pin match what will actually run?**
```bash
mise exec -C "$KB" -- graphify --version     # expect: graphify 0.9.26 (mise.toml:23)
command -v graphify; graphify --version      # CONTROL: on this machine → 0.9.25, an install dir
```
Disagreement is expected here and is the point: it proves any bare `graphify` call in the session uses the wrong version.

**C4 — do the hooks point at THIS clone?**
```bash
grep -n "$PWD" .claude/settings.json | wc -l   # expect 3 if you are the original clone
grep -n 'Users/' .claude/settings.json         # expect 0 lines after the §3 patch
```

**C5 — is the graph present (do the graphify hooks do anything)?**
```bash
ls -l graphify-out/graph.json                  # absent ⇒ 2 of 5 hooks are no-ops
```

**C6 — do all `.md` cross-references in the rules resolve?**
```bash
git grep -oh '`[a-z0-9-]*\.md`' -- .claude/rules | tr -d '`' | sort -u \
  | while read f; do [ -e ".claude/rules/$f" ] || echo "DANGLING: $f"; done
# today: DANGLING: omc-directory-conventions.md   (3 citing files)
# CONTROL: the same loop must NOT flag notepad-enforcement.md, which exists
```

---

## 5. Declared but unverified

Config that asserts something nothing observes:

1. **`.claude/settings.json:7` `permissions.defaultMode: "auto"`** — provably ignored at project scope (binary 2.1.220: `"ignored as repo-controllable"`; the settings validator's valid-mode list omits `auto`). Dead line; possibly harmful (may shadow the user-scope value).
2. **`.claude/settings.json:93` `teammateMode: "auto"`** — the *values* are legal, but the binary places `teammateMode` in the `/config` global-config cluster and logs `[TeammateModeSnapshot] Captured from config:`. Whether project-scope `settings.json` is even read for this key is **unverified**; a runtime probe failed its control arm (an invented key produced no warning either), so it is evidence in neither direction. `~/.claude/settings.json` sets `teammateMode: tmux`, so this machine cannot demonstrate the project value working.
3. **`.claude/settings.json:2-5` env vars** — both names exist in the binary (control-armed: an invented `CLAUDE_CODE_TOTALLY_FAKE_VAR` → 0 hits). But `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is *also* set in `~/.claude/settings.json`, so its observed effect is not attributable to the project file. Only `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` is project-only. Neither has been shown to change behavior.
4. **`mise.toml:342` "Session name: `CC_TMUX_SESSION`, default the repo"** — `grep -rn CC_TMUX_SESSION` → 1 hit, that comment. No code reads it; `cc_main` always falls back to `repo_root.name`. (Control arm, same shape: `MISE_PROJECT_ROOT` → 3 hits.)
5. **`mise.toml:323` "auto mode"** in the `cc` description — `launch.py` emits no permission-mode flag anywhere (`grep -c "add-dir"` → 3 as control; `grep permission|bypass|dangerously` → 0).
6. **`launch_argv`'s rooting guarantee holds only for a *first* launch** — `launch.py:266-270` uses `tmux new-session -A` with a fixed session name (`repo_root.name`, `launch.py:304`). Measured: when the session already exists, `-A` attaches and silently discards `-c`, `-e PATH=`, and the `claude --add-dir` command. `tests/test_launch.py:192-205` asserts the argv *list* only and cannot see this. No test covers the pre-existing-session case.
7. **`_version_of` measures the ambient cwd, not `repo_root`** — `launch.py:235-246` calls `subprocess.run([binary, "--version"])` with no `cwd=`, while `pinned_version` reads `repo_root/mise.toml`. The two halves of the pin comparison answer about different directories. Since `[tasks.cc]` sets no `dir`, `mise run cc` from outside the KB tree refuses spuriously.
8. **No wiring contract exists.** `grep -rn "settings.json|PreToolUse|hookguard"` across `tests/` → nothing that asserts anything (control arm: `grep -rln hook_guard tests/` → 2 files). `git grep selfcheck` → **0 hits** (control: `git grep -ln hook_guard` → 10 files). `eval_cases.py:9-11` states the gap outright: tier 2 asks *"not is it wired (the settings.json hook), but does the wired guard DECIDE correctly?"* — and the "tier 0" it defers to does not exist in this repo. dotfiles ships `hook_selfcheck.py` as an always-run ship/land gate; KB has no equivalent. Renaming the `hookguard` subcommand (`cli.py:89`) or dropping the `Bash` matcher leaves all 34 fixtures + 35 unit tests green and the guard dead.

### Where evidence is thin

- **Skill/agent counts are worthless as stated.** Re-measured three times per arm, model-mediated `claude -p` counts gave 43/43/43 without `--add-dir` and 70/97/71 with it. The add-dir arm's own spread (27) is the size of the delta anyone would try to explain. Any "N skills load" figure in the earlier review should be discarded; `claude plugin list` rejects `--add-dir` (`error: unknown option`), so no deterministic route exists. Use targeted YES/NO presence probes for named skills instead — those reproduce.
- **`claude-plugins-official` auto-install** (`officialMarketplaceAutoInstallAttempted` in `~/.claude.json`) has ~10 documented skip/fail paths (enterprise policy, env opt-out, GCS unavailable, git unavailable, retry exhaustion). `already_attempted` is a *skip* reason, so a failed first attempt is never retried. I did not test a genuinely cold machine.
- **No fresh clone was actually driven end-to-end through Claude Code.** Every fresh-clone finding above is from executing the wired command strings by hand against non-existent paths, plus file reads. That is strong for the blockers (rc=2 and rc=1 are unambiguous) and weaker for anything about what a session *loads*.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `.claude/**`, `mise.toml`, `python/src/kb_setup/**`.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.claude/**` compared as the reference repo.
