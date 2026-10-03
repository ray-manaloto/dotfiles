# The worktree-isolation refusals come from Claude Code itself, and the main bug is already reported upstream

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: general-purpose subagent (read-only),
> commissioned under Ray's ruling (a): "file upstream only after due diligence".

I changed no files and filed nothing, so this report needs persisting at `docs/research/kb/reports/agents/`.

**Verdict:** the refusal text is not in our repo; it is compiled into the installed Claude Code binary. Most of the refused commands never run git, and anthropics/claude-code already has at least 8 open issues for that. **Don't file a new issue. Comment on #95122 (or #97225) instead.** That comment should add three things: the `$?` shape, our 2.1.287 data, and the fact that the 2.1.257 and 2.1.259 changelog fixes did not hold.

Two premises from the 03f/03g handoffs did not survive the evidence:
- **"Unquoted `rc=$?` is the trigger" is not supported.** I checked the 38 refusals in watcher 998ab91b's subagents (all on 2.1.287). Of the 37 Bash ones, 29 contain no `rc=$?` at all. I found no case where a refused command passed after only quoting `rc=$?`. One 2.1.288 refusal hit a command whose `"rc=$?"` was already quoted (`git commit -F - <<'EOF' > log 2>&1; echo "rc=$?"`). Quoting is harmless, but it is not the fix. The real trigger is "a construct too complex to verify", which covers `VAR=…; cmd $VAR`, heredocs, `;` chains and `$(…)`.
- **The "coordinator/watcher refused main-checkout writes" part is documented behaviour, not a bug.** Once a session calls `EnterWorktree`, Edit/Write to the main checkout and Bash whose working directory is the main checkout are blocked by design (`worktrees.md:81-97`; `agent-view.md:488-511`). The ruling that watchers and coordinators never call EnterWorktree is the right fix. The only buggy-looking variant is EnterWorktree making the whole session isolated, including subagents. That is already filed as #89102, #91932 and #98307.

## 1. The text does not come from our repo (both arms checked)

I ran `git grep -l -F` over `python scripts .claude hk*.pkl`:

| Search string | Tracked files with a hit |
|---|---|
| `isolated in the worktree` | 0 |
| `worktree-isolated session` | 0 |
| `too complex to verify that it stays inside` | 0 |
| `Edit the worktree copy` | 0 |
| `cannot be shown not to be git` | 0 |
| **Control:** `Quote the separator` / `hand-rolled Codex SDLC dispatcher` | 1 / 2 (`python/src/dotfiles_setup/hook_guard.py`, `.claude/rules/codex-sdlc-team.md`) |

Our own hooks are not involved either:
- The repo's function hooks register only `session.measure`, `session.start`, `prompt.submit`, `classic.SessionStart` and `classic.PreToolUse`. None registers `tool.call` or `*`, which is the #92533 trigger. Those hooks live in `.claude/skills/{coordinator-handoff,install-doctor,session-start}/hooks/register.ts` and `.claude/skills/plugin-health/hooks/plugin-health.ts`.
- An unbounded scan of 4032 plugin-cache hook files found one `tool.call`/`*` registrant: `claude-plugins-official/code-modernization`. It is not enabled in project or user settings.

## 2. The text is in the installed harness

- **Version:** `claude --version` returns `2.1.288 (Claude Code)`. The binary is `~/.local/share/claude/versions/2.1.288`.
- **Binary hits** (`grep -c -a -F`, 0 for a freshly invented absent string):

| String | Hits |
|---|---|
| `isolated in the worktree` | 5 |
| `Edit the worktree copy of this file instead of the shared-checkout path` | 2 |
| `names git in a form too complex to verify` | 3 |
| `working directory resolved to the shared checkout` | 2 |

  The full sentence `a worktree-isolated session's git operations must target its own worktree` returned 0. It is probably assembled from fragments at runtime.
- **Vendor docs:**
  - KB copy (`$CC/worktrees.md:81-97`, "How Claude Code enforces isolation"): four checks — file edits, command working directory, git redirects, and command shape. On command shape it says: "blocks a Bash or Monitor command when it can't verify … that any git the command runs stays inside the worktree … You can't turn this check off."
  - KB copy (`$CC/agent-view.md:488-511`): background sessions move into a worktree before editing. `worktree.bgIsolation: "none"` turns isolation off per repository.
  - Newer mirror (`.agent/kb/raw/cc-docs-2026-10-01/ccdocs/errors.md:4258`, "Command blocked by the worktree isolation checks"): "A command that never names git can still be refused".
- **Changelog** (newer mirror; it goes up to 2.1.287):
  - 2.1.257: "Fixed worktree-isolated sessions refusing Bash loops, `$VAR` reads, `"$(…)"` and heredocs that never touch git".
  - 2.1.259: "Fixed … refusing common Bash loops, xargs pipelines and launcher-wrapped commands".
  - 2.1.274: "certain nested shell expansions … are now refused".
  - Our 2.1.287 transcripts still show the 2.1.257 shapes refused, so that fix did not hold.

### The refusal texts, verbatim from our transcripts

Paths are abbreviated to `<wt>`:
- `This session is isolated in the worktree <wt>, but this command names git in a form too complex to verify that it stays inside the worktree. Refusing to run it — a worktree-isolated session's git operations must target its own worktree. Split it into plain, separate commands and run them from <wt>.` (86 of 198)
- `… but this command is too complex to verify that it stays inside the worktree. Refusing to run it …` (26)
- `… but this command runs sed with a value computed at runtime (the variable F) where an option may stand (… put -- before it) …, so what it runs cannot be shown not to be git.`
- `… but this command's working directory resolved to the shared checkout (<main>). Refusing to run it there — a worktree-isolated session's commands must run inside its worktree. Re-run the command from <wt>.`
- `… but this command redirects git to the shared checkout via -C.`
- Write/Edit: `This session is isolated in the worktree <wt>. Edit the worktree copy of this file instead of the shared-checkout path.` The subagent form starts "This agent is isolated…".

### What the transcripts show

- **Volume:** 198 refusals across all dotfiles transcripts. By version: 2.1.280: 17, 2.1.281: 1, 2.1.284: 8, 2.1.287: 155, 2.1.288: 25. Two of the 2.1.288 hits were my own session printing the string, so 2.1.288 really has 9.
- **Watcher 998ab91b:** I measured 7 refusals in the main transcript and 38 in its subagents. The inherited "52 this session" figure is unverified; I could not reproduce it exactly.
- **Smallest git-free refusals** (all reported as "names git in a form too complex to verify"):
  - `curl -sfL https://raw.githubusercontent.com/jdx/pklr/main/CHANGELOG.md -o .agent/kb/raw/pklr-CHANGELOG.md; echo rc=$?` (2.1.280)
  - `curl -sS -o /tmp/dmcg-pyproject.toml https://raw.githubusercontent.com/…/pyproject.toml; echo rc=$?` (2.1.287)
  - `gh api -X GET repos/…/contents/pyproject.toml -f ref=0.83.0 -H 'Accept: application/vnd.github.raw' > /tmp/x.toml; echo rc=$?; wc -l /tmp/x.toml` (2.1.287)
  - `D=…/claude-code-docs; ls $D | head -3 >/dev/null; grep -rln '…' $D | head; echo '---'; …` (2.1.287; no `rc=$?` at all)
  - `P=…/task_plan.md; sed -n 2470,2547p $P | cut -c1-400`, reported as "runs sed with a value computed at runtime" (2.1.287)
- **Possible genuine 2.1.288 oddity:** `cd <its own worktree> && pwd && git log --oneline -2` was refused as "working directory resolved to the shared checkout". The check appears to use the starting directory, not the `cd` target. This matches #91932 and #89102.
- **The other refusal class (#92533):** 25 refusals said "isolation context for this agent was lost". 20 were our deliberate #92533 probes on 2.1.269 (2026-09-12, recorded in `docs/agents/goal-history.md:862-866`). 5 more appeared on 2.1.286 on 2026-10-01 and are **unexplained**: I found no active `tool.call` hook to account for them. They are worth a separate look.
- **What I could not do:** I did not run a live repro, because this session is not worktree-isolated and creating a worktree would mutate the repo. The evidence is real harness output recorded in transcripts, not a fresh controlled run.

## 3. Upstream search (anthropics/claude-code)

Control arms for issue search: `worktree` returned 3352; a fresh nonsense token returned 0.

| Query | Total |
|---|---|
| `"isolated in the worktree"` | 139 |
| `"too complex to verify"` | 35 |
| `"names git in a form too complex"` | 7 |
| `"worktree-isolated"` | 414 |
| `"Edit the worktree copy"` | 26 |
| `"working directory resolved to the shared checkout"` | 6 |
| `"rc=$?" worktree` | 74 (noise: Remote Control "rc" issues) |
| `worktree isolation author:ray-manaloto` | 0 |
| `worktree isolation is:pr` | 2 (unrelated) |

**Discussions:** 0 on all four GraphQL queries, because the repo has discussions turned off (`has_discussions=false`). The control `repo:cli/cli` search returned 577 discussions.

| Issue | State | Match | Note |
|---|---|---|---|
| [#95122](https://github.com/anthropics/claude-code/issues/95122) | open, has repro | **Strong** | Git-free Bash refused on 2.1.272/273: literal-assigned variables, `$(…)`, loops, heredocs. Cites the 2.1.257 fix as not holding; 1 comment (2.1.280 shapes). Best target. |
| [#97225](https://github.com/anthropics/claude-code/issues/97225) | open, has repro | Strong | macOS, 2.1.282, reproduced with hooks, plugins and MCP disabled; minimal repro. |
| [#97474](https://github.com/anthropics/claude-code/issues/97474) | open, labelled duplicate | Strong | 2.1.283, "cannot be shown not to be git" and "too complex". |
| [#87959](https://github.com/anthropics/claude-code/issues/87959) | open, enhancement | Strong | Every compound command refused; 8 comments. |
| [#90377](https://github.com/anthropics/claude-code/issues/90377), [#93193](https://github.com/anthropics/claude-code/issues/93193), [#97760](https://github.com/anthropics/claude-code/issues/97760), [#84182](https://github.com/anthropics/claude-code/issues/84182), [#90293](https://github.com/anthropics/claude-code/issues/90293), [#94040](https://github.com/anthropics/claude-code/issues/94040), [#96253](https://github.com/anthropics/claude-code/issues/96253) | open | Same family | String-executor/"git"-substring matching, env-var names, heredoc quoting. |
| [#89102](https://github.com/anthropics/claude-code/issues/89102), [#91932](https://github.com/anthropics/claude-code/issues/91932), [#98307](https://github.com/anthropics/claude-code/issues/98307), [#84493](https://github.com/anthropics/claude-code/issues/84493) | open | Coordinator/subagent case | EnterWorktree isolates the whole session and its subagents; working directory doesn't follow `cd`/EnterWorktree. |
| [#92533](https://github.com/anthropics/claude-code/issues/92533) | open, has repro | Different message | "isolation context … was lost" when a function hook registers on Bash `tool.call`; we confirmed it on 2.1.269. |

None of the 8 strongest issues mentions `$?` or `rc=$?`, and only #97474 and #97760 mention `curl`. I control-armed that body grep: `sed` and `heredoc` both returned non-zero counts on the same bodies.

## 4. Recommendation

1. **Don't open a new issue.** It would be a duplicate of #95122, #97225 and #87959.
2. **Comment on #95122**, the best fit because it already says the 2.1.257 fix didn't hold. The comment should carry:
   - our versions (2.1.280 through 2.1.288, macOS arm64) and the counts above;
   - the new minimal shape `curl -sS -o /tmp/f <url>; echo rc=$?`, refused as "names git in a form too complex" with no variable, loop, heredoc or git — the closest thing to a minimal repro we have;
   - the `cd <own worktree> && git log` working-directory refusal on 2.1.288, linking #91932.

   Before posting, do a clean-room repro: a throwaway repo, `claude -p --worktree`, with `--setting-sources ""` and hooks disabled as #97225 did. Run both arms: `curl … ; echo rc=$?` against `curl …` alone. This is needed because none of our evidence is a controlled run, and the real-integration rule requires one. It goes through `issue-filer` with `FILE ISSUES: yes`.
3. **Local workaround:** keep "watchers and coordinators never EnterWorktree". Replace "quote `"rc=$?"`" with: in isolated lanes, issue plain single commands, avoid `VAR=…; cmd $VAR` (write literal paths or `"$VAR"`), and write files with Write instead of heredocs. Quoting `rc=$?` alone did not prevent refusals.
4. **Optional check:** find the cause of the 5 unexplained "isolation context … was lost" refusals on 2.1.286 (2026-10-01).

### Draft comment for #95122 (only if the clean-room repro succeeds)

Title: none, it's a comment. Body:

> Still reproducing on **2.1.287 and 2.1.288** (macOS arm64, CLI, background sessions and `isolation: "worktree"` subagents). Across about 10 sessions from 2026-09-23 to 2026-10-03 there were about 190 Bash refusals in worktree-isolated sessions. Most are git-free commands that stay inside the worktree.
>
> A new shape smaller than the ones above, refused with *"names git in a form too complex to verify that it stays inside the worktree"*:
> ```
> curl -sS -o /tmp/f.toml https://raw.githubusercontent.com/<o>/<r>/<tag>/pyproject.toml; echo rc=$?
> ```
> It has no git, no variable, no loop and no heredoc. The only compound element is `; echo rc=$?`. [clean-room arms: with `; echo rc=$?` → refused / without → ran]
>
> Also refused on 2.1.287: `P=<abs path in worktree>; sed -n 1,80p $P` ("runs sed with a value computed at runtime … cannot be shown not to be git"), and `gh api … > /tmp/x; echo rc=$?; wc -l /tmp/x`.
>
> And on 2.1.288, `cd <the session's own worktree> && pwd && git log --oneline -2` is refused with "this command's working directory resolved to the shared checkout". The check seems to use the working directory before the `cd`; see #91932.
>
> The 2.1.257 and 2.1.259 changelog fixes ("`$VAR` reads … heredocs that never touch git", "common Bash loops") don't appear to hold on 2.1.287 or 2.1.288.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issue and PR search (variant queries), discussions GraphQL search (discussions turned off), and the bodies/comments of #92533, #95122, #97474, #97225, #98307, #89102, #91932, #90377, #87959, #93193, #97760
- [cli/cli](https://github.com/cli/cli) — control arm only: a discussions search that must hit (577)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local read-only `git grep` and the handoff/coordinator logs; no API calls
