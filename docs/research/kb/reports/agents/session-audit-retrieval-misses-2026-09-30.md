# Session-integrity review: retrieval misses (2026-09-30)

Status: COMPLETE

Method: `## Brief S (retrieval misses)` of `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md`
(the method only). Session: `7ad65526-9c43-49d4-89da-5efd32ad1c2c` ("dotfiles-20260929.002"). Ordinals `[N]` are 1-based
line numbers of the main JSONL. 475 tool calls were joined to their results and read in full. Lane: read-only.

⚠️ **Persistence limitation.** The lane could not write the tracked path. `branch_guard` denied the `Write` because
the checkout is on `main` (do-not #9). Branching the shared checkout while other lanes run was not this lane's call.
The report lives at the scratchpad path below, and the coordinator persists it verbatim to
`docs/research/kb/reports/agents/session-audit-retrieval-misses-2026-09-30.md`:
`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/7ad65526-9c43-49d4-89da-5efd32ad1c2c/scratchpad/session-audit-retrieval-misses-2026-09-30.md`

`$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.

## Findings

The exact lines are in **§ Lines to add (verbatim)**. They are kept out of the table so their `|` characters survive.

| # | Sev | Fact the session re-derived | Cost (ordinals) | Carrier (ONE file) | Control arm |
|---|---|---|---|---|---|
| S1 | HIGH | A mise pin bump that lands mid-session never reaches Claude Code's Bash tool. Every call re-sources a shell snapshot whose last line is a literal `export PATH`. knowledge-base already diagnosed this (memory `the-bash-tool-freezes-path-in-a-snapshot`, 2026-09-03) and already ships the refresh: `kb_setup/env_refresh.py` + `[tasks.kb-env-refresh]` write `$CLAUDE_ENV_FILE` (KB #702, KB PR #709). The dotfiles repo had nothing that pointed at either | At [3499]/[3505] a stale bare `firecrawl` (1.24.6 vs pin 1.25.0) was worked around with `mise exec`. The user replied "we should have solved this already" [3561]. The session then re-derived the root cause from scratch: [3569] path_drift.py, [3582] `$CC` grep, [3594]/[3600]/[3605] measurement, [3618] findings. It went on to a new spec [3625], an implementer dispatch [3629], a HOLD [3666] and a research workflow [3668]. The implementer found the KB prior art only at [3886], which forced a re-ruling [3893] and a re-task [3905] | `python/src/dotfiles_setup/path_drift.py`, module docstring. This is the file read at [3569], at the moment of diagnosis. It describes the symptom ("including Claude Code and its Bash tool") but not the snapshot mechanism or the KB fix | Present: `ls knowledge-base/python/src/kb_setup/env_refresh.py` exists. `knowledge-base/mise.toml:1896` is `[tasks.kb-env-refresh]`. `gh issue view 702 -R ray-manaloto/knowledge-base` returns OPEN "Refresh the Bash-tool environment…". Absent-arm: `#99999` returns "Could not resolve". In dotfiles, `git grep 'env_refresh\|kb-env-refresh\|#702'` finds 0 hits, and `CLAUDE_ENV_FILE` appears only in `scripts/web-setup.sh:69`. Dotfiles memory grep for `CLAUDE_ENV_FILE\|env_refresh` also finds 0 |
| S2 | MEDIUM | `mise run ship` cannot pass from a linked worktree (`dotfiles.worktrees/*`). (a) The main checkout's `mise.local.toml` port pin (`DEVCONTAINER_SSH_PORT=26233`) leaks in through the ambient shell, so the `sync-full` gate collides on the running main container. (b) Even with that unset, the worktree's `.git` is a FILE that points at `<main>/.git/worktrees/<wt>`, and that path is not mounted, so the smoke preflight fails. Its "verify safe.directory" hint misattributes the cause. **The carrier the session did read was WRONG:** handoff `session-2026-09-29b.md:58` says "ship from a clean sibling worktree" | Two failed full ship runs: [2837]→[2963] (port) and [3001]→[3072] (git). Diagnosis took [2967], [2972], [2977], [2990] and [3077]. Workaround: the worktree was removed and the branch was shipped from the main checkout [3200] | `.claude/skills/pr-workflow/SKILL.md`, § Failure modes table (:118-134). That skill owns ship. `grep -c -i worktree` on it gives 0, against 16 for `auto-merge` as the control | Armed now: `head -c 200 ../dotfiles.worktrees/research-enforcement-20260930/.git` gives `gitdir: /Users/…/dotfiles/.git/worktrees/research-enforcement-20260930`, while the main checkout's `.git` is a directory. `.devcontainer/devcontainer.json:121` mounts only `${localWorkspaceFolder}`. Log signatures: `ship-currency.log:944` "Bind for 0.0.0.0:26233 failed: port is already allocated"; `ship-currency2.log:1116` "FAIL: git cannot open the workspace…verify safe.directory". The new handoff `session-2026-09-30.md:19` repeats the trap, but it is gitignored and ephemeral |
| S3 | MEDIUM | The goal-history digest formula. It is `sha256` over the quoted goal lines with `> ` stripped, joined by `\n`, with no trailing newline. The validator is `session_review.goal_history_errors`, and `tests/test_session_review.py:303` already runs it against the tracked file, so the pytest gate covers it. The rule says only "A digest identifies exact goal text" | First append: [421] grep, [426] source read, [534] hand-rolled hash, [579]/[585]/[597]/[602] a hand-rolled validator with an arm (7 calls). Second append: [4016]/[4027], again hashed and validated by hand (2 calls) | `.claude/rules/goal-history.md`, after :11-12. This eager rule is read before every append | Re-derived now, not inherited: `goal_history_errors(real)` returns `()`. On the newest iteration the formula matches (`True`), and with a trailing `\n` it does not (`False`), so the probe discriminates. The session's own [602] mutation (`b0bed4e3`→`00bed4e3`) returned "Current goal digest does not match" |
| S4 | LOW | A new saved workflow must dry-run in `tests/test_workflows_js.py`, which runs every `.claude/workflows/*.js` under Bun with stubs. Each node label prefix must be in `KNOWN_LABEL_PREFIXES`, and each `agentType` must be a `.claude/agents` name or a builtin. Nothing said so where workflows are listed | 8 reads of the test harness before the first edit: [2266], [2272], [2284], [2290], [2297], [2336], [2348], [2353]. Then [2359] added 8 labels to the set | `.claude/CLAUDE.md:67`, the "Saved workflows" line. It is loaded every session | `tests/test_workflows_js.py:63-64` (`KNOWN_AGENT_TYPES`, `KNOWN_LABEL_PREFIXES`) and :264 (`test_every_saved_workflow_dry_runs_with_known_agents`). Positive arm: [2376] rc=0 after the labels were added. Note that `native-cli-installers.js` (unmerged branch `feat/native-cli-installers-workflow`) is not yet in the :67 list either |
| S5 | LOW | A Workflow task's `tasks/<id>.output` is ONE pretty-printed JSON object: `json.load(f)["result"]` is the script's return value. An Agent task's output file is a JSONL transcript instead | [2839] searched the raw text for `'{"mode":"plan"'`, which never matches because the JSON has a space after the colon, and failed with a JSONDecodeError. [2851] then detoured into `subagents/workflows/wf_*/journal.jsonl` | `.claude/rules/ai-cli-invocation.md`, § Background results (after :85-89, "Recover background output by `Read`ing the task's output file path…") | Re-derived now: all 9 `w*.output` files parse as JSON with keys `agentCount, logs, result, summary, totalTokens, totalToolCalls, workflowProgress`. The agent file `a9c35ab8c397e8e29.output` gives a JSONDecodeError (JSONL), so the probe discriminates |
| S6 | LOW | The `dotfiles-setup` CLI's subcommand parsers and dispatch table live in `python/src/dotfiles_setup/main.py`. There is no `cli.py` | [225] grepped `cli.py`, which is missing (ugrep warning). [238] and [244] then found `main.py:1531/1550/2816/2820` | `python/AGENTS.md`, § Key Files table (after :18) | `ls python/src/dotfiles_setup/cli.py` returns No such file, while `grep -n '"handoff-check": lambda' main.py` finds :2844. `python/AGENTS.md` mentions neither file |
| S7 | LOW | zsh treats an unquoted `?` in a `gh api` URL query string as a glob. It aborts with `no matches found` and rc=1 | [893] failed and [898] succeeded quoted (1 call). The fact was carried only in the UNINDEXED memory `project_session_2026-08-08.md:94` ("zsh aborts the WHOLE command on an unmatched glob") | `.claude/rules/gh-cli-watch.md`, § Canonical patterns block (after :37). It is the eager `gh` rule | The [893] result text is `(eval):1: no matches found: repos/cli/cli/commits?path=…&per_page=1`. The quoted [898] returned `e9542451…`. A MEMORY.md index grep for `no matches found` finds 0 hits. The control grep for `word-split` finds the indexed hook |
| S8 | LOW | Why a devcontainer "vanished": Docker Desktop was quit. The evidence is `Quitting whole Docker Desktop` in `~/Library/Containers/com.docker.docker/Data/log/host/electron-<date>.log`. `com.docker.backend.log` rotates every few hours, so it is usually gone by the time anyone asks | 6 calls to locate it: [1293], [1297], [1302], [1339], [1343], [1348]. A 4-call transcript sweep [1317]-[1327] ruled out an agent command | `doctor.toml` `[devcontainers]` "Why it exists" comment (:315-317). The doctor's finding is what the next agent sees first when an arch is down | Present arm: 1 hit in `electron-2026-09-29.log`. Absent arm: 0 in `supervisor.log`. Rotation: the 4 current `com.docker.backend.log*` files all date from 2026-09-30 (11:54, 14:15, 16:36 and 18:01). `git grep 'com.docker.docker/Data/log'` finds 0 hits in the repo, as does the memory grep; the control `desktop-linux` is in 20 files |

Count: HIGH 1, MEDIUM 2, LOW 5.

**Disposition (every row): FIX-NOW** with the matching `L-S<n>` below. All eight are tracked repo edits except the
second half of S2: the handoff line `session-2026-09-29b.md:58` is gitignored and historical, so leave it and let the
skill row supersede it. S1 changes a docstring only, with no behaviour, so it needs no test. S3, S5 and S7 grow eager
rules, so run `mise run lint-docs` and the `md_size_budget` check. S4 touches `.claude/CLAUDE.md`, but the line is not
one of `rule-sync.toml`'s mirrored lines (:33).

## Carried already, so no line to add

- **zsh does not word-split `$var`** ([2929] `set -- $spec` failed, and [2934] re-ran it under `bash -c`, 1 call). The
  indexed hook in MEMORY.md is `feedback_zsh_no_word_splitting.md`. It was in context and still missed. A line cannot
  fix this; only a guard rule could.
- **Unquoted `echo ====`** [118] and **`ruff … | head`** [2107]: both were denied by `hook_guard` with the remedy in
  the deny text, and each cost 1 call. The enforcement worked as designed.
- **graphify 0.9.73's user-global pin** ([3213]→[3229]): the task's own error line was "update the user-global mise
  pin", so the tool handed over the fix.

## Out of Brief S scope, handed to the coordinator (not retrieval misses)

- **Guard gap, armed now.** The guard treats a subshell-detached `mise run` differently from a plain detached one:
  - `mise run land -- 1467 > /tmp/x.log 2>&1 &` is **denied** ("backgrounded mise run").
  - `(mise run land -- 1467 > /tmp/x.log 2>&1; echo "rc=$?" >> /tmp/x.log) &` is **allowed** (empty guard output).
  - The session used exactly that subshell form at [3764], then had to `pkill` it at [3777] and relaunch at [3787].
  - Probe: a JSON payload fed through `scripts/pretooluse-guard.sh`.
  - The probe discriminates: `gh pr checks 1 --watch` and `echo ====` both returned `deny` through the same harness.
  - This belongs in the bugs or repeat-offenders brief.
- **Automation candidate.** The same ~12-line python "last non-blank assistant text of `tasks/<id>.output`" extractor
  was hand-rolled 8 times: [364], [682], [722], [747], [809], [1475], [1613], [1732].
  - The fact itself is carried (`agent-report-persistence.md:60`). What is missing is a task.
  - This is session-review lane 1 material, not a retrieval miss.
- **Not misses:**
  - The gh `eliminateDuplicates` research ([839]-[898]) was new and is now recorded at `pr_facts.py:129`.
  - `research_fanout.py` has no code-search source (`_SOURCE_NAMES` :62-71; the planner node's `codeSearch` does it),
    so the hand-rolled `gh api search/code` at [2913] filled a real capability gap. The session then researched and
    specced that gap ([3099], [3133]).

## Lines to add (verbatim)

**L-S1**: `python/src/dotfiles_setup/path_drift.py`, module docstring. Insert a new paragraph after the "Four
occurrences before this module existed (#596)…" paragraph (before :18, "Why this cannot live…"):

```text
Mid-session drift inside Claude Code's Bash tool has its own mechanism and an
existing fix: every Bash call re-sources a shell snapshot whose LAST line is a
literal ``export PATH`` captured at session start, so a pin bump never reaches
the running session (knowledge-base memory
``the-bash-tool-freezes-path-in-a-snapshot``, 2026-09-03). knowledge-base
already ships the refresh: ``kb_setup/env_refresh.py`` +
``[tasks.kb-env-refresh]`` write ``$CLAUDE_ENV_FILE`` on
startup|resume|clear|compact|fork (knowledge-base #702, PR #709). Reuse it; on
2026-09-30 Ray ruled that the ``mise hook-env`` refresh moves into ``kb_setup``
for both repos. Do not design a second one.
```

**L-S2**: `.claude/skills/pr-workflow/SKILL.md`, § Failure modes table. Add this row after the `ship: working tree
not clean` row (:123):

```text
| `Bind for 0.0.0.0:<port> failed: port is already allocated` in gate `sync-full` — or, with the port unset, `FAIL: git cannot open the workspace at /workspaces/<wt>; verify safe.directory` | You ran `ship` from a LINKED worktree (`dotfiles.worktrees/*`). The port is the main checkout's `mise.local.toml` pin leaking in via the ambient shell; the git failure is the worktree's `.git` FILE pointing at `<main>/.git/worktrees/<wt>`, which the container does not mount (the safe.directory hint misattributes it) | Ship from the MAIN checkout: `git worktree remove <wt>`, `git checkout <branch>` in the main clone, `mise run ship`. Measured 2026-09-30 (two failed ships); "ship from a clean sibling worktree" is wrong |
```

**L-S3**: `.claude/rules/goal-history.md`, after :12 ("not prove that the goal was completed."):

```text
The digest is `sha256` of the quoted goal lines with `> ` stripped, joined by
`\n`, no trailing newline (`_goal_text`/`_iteration_errors` in
`python/src/dotfiles_setup/session_review.py`); `tests/test_session_review.py`
validates the tracked file, so `mise run gate -- run pytest` is the check — do
not hand-roll a hasher or validator.
```

**L-S4**: `.claude/CLAUDE.md`, directly after :67 (the "Saved workflows" line):

```text
A new saved workflow must dry-run in `tests/test_workflows_js.py` (Bun, stubbed `agent`/`phase`/`log`): add its
node label prefixes to `KNOWN_LABEL_PREFIXES` (every `agentType` must be a `.claude/agents` name or a builtin), and
add it to the list above.
```

**L-S5**: `.claude/rules/ai-cli-invocation.md`, § Background results. Insert after the sentence ending "`-o <path>`." (:89):

```text
A Workflow task's output file is ONE pretty-printed JSON object —
`json.load(f)["result"]` is the script's return value (no string search: it is
indented); an Agent task's output file is its JSONL transcript instead.
```

**L-S6**: `python/AGENTS.md`, § Key Files table, after the `src/dotfiles_setup/` row (:18):

```text
| `src/dotfiles_setup/main.py` | The `dotfiles-setup` CLI: every subcommand's argparse parser and the name→handler dispatch table (there is no `cli.py`) |
```

**L-S7**: `.claude/rules/gh-cli-watch.md`, § Canonical patterns code block, after :37 (`gh run view … # one run`):

```text
gh api 'repos/cli/cli/commits?path=x&per_page=1' --jq '.[0].sha'  # QUOTE a query string: zsh globs `?` → "no matches found", rc=1
```

**L-S8**: `doctor.toml`, `[devcontainers]`, after :317 (the "Why it exists" comment's last line):

```text
# WHY Docker Desktop stopped: grep 'Quitting whole Docker Desktop'
# ~/Library/Containers/com.docker.docker/Data/log/host/electron-<YYYY-MM-DD>.log
# (com.docker.backend.log rotates every few hours, so it is usually gone).
```

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — audited session's repo; carrier files, guard harness, test registry
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — prior art for S1 (`kb_setup/env_refresh.py`, `[tasks.kb-env-refresh]`, issue #702 state via `gh issue view`)
- [cli/cli](https://github.com/cli/cli) — only as cited by the session's [839]-[898] research (`pkg/cmd/pr/checks/aggregate.go`); not re-fetched by this lane
