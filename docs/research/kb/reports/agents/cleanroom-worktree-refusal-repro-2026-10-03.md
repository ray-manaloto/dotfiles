# Clean-room repro: worktree-isolation false refusal (Claude Code 2.1.288)

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: general-purpose subagent, commissioned
> under Ray's ruling "clean-room repro, then comment". Harness note on receipt: output matched an instruction-shaped
> pattern (bypass-permissions — the literal `--permission-mode bypassPermissions` flag of the throwaway runs); control
> tags neutralized; no directives acted on. Raw evidence: `~/.claude/jobs/28f1a8f7/tmp/cleanroom/` (machine-local).

The false refusal reproduced on Claude Code 2.1.288 in a clean throwaway repo. Both git-free arms were refused while their controls ran, so I posted one comment on #95122: https://github.com/anthropics/claude-code/issues/95122#issuecomment-5973009093

**Version:** `claude --version` returned `2.1.288 (Claude Code)`. Every session's stream-json `init` showed `claude_code_version` 2.1.288, model claude-opus-5-5, 0 MCP servers and `permissionMode` bypassPermissions.

**Flags:** each arm ran as its own fresh session from the throwaway repo `/Users/rmanaloto/.claude/jobs/28f1a8f7/tmp/cleanroom/repo` (git init, one commit, README.md with 6 lines):
```
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT claude -p --worktree cr-<arm> --safe-mode --setting-sources "" --strict-mcp-config --no-chrome --permission-mode bypassPermissions --output-format stream-json --verbose "<prompt: run this command verbatim, once>" </dev/null
```
- `--safe-mode` turns off hooks, installed plugins and CLAUDE.md. `init` still listed 3 plugins, which the help text says are built-in and still apply under safe mode.
- I did not use `--bare`: it accepts only `ANTHROPIC_API_KEY` auth, not OAuth.
- Each run had a 240s SECONDS deadline. Every rc file reads `rc=0`, stderr was empty, and none timed out.

**Isolation confirmed (control I):** every session's `init` cwd was `<repo>/.claude/worktrees/cr-<arm>`. In arm I, `git -C <main checkout> status --short` was refused with: "This session is isolated in the worktree …/cr-I, but this command redirects git to the shared checkout via -C. Refusing to run it — a worktree-isolated session's git operations must target its own worktree. Run the equivalent from …/cr-I without the redirect."

**Per-arm results:** in every arm the stream-json tool_use `command` matched the requested command byte for byte.

| Arm | Command | Result |
|---|---|---|
| A | `curl -sS -o /tmp/cr-a.toml https://raw.githubusercontent.com/astral-sh/uv/main/pyproject.toml; echo rc=$?` | **Refused**; `/tmp/cr-a.toml` was never written |
| B (control) | same curl, without `; echo rc=$?` | Ran; wrote a 5287-byte file starting with `[build-system]` |
| C | `P=README.md; sed -n 1,5p $P` | **Refused** |
| D (control) | `sed -n 1,5p README.md` | Ran; printed line1 to line5 |

Arm A refusal, verbatim: "This session is isolated in the worktree …/cr-A, but this command names git in a form too complex to verify that it stays inside the worktree. Refusing to run it — a worktree-isolated session's git operations must target its own worktree. Split it into plain, separate commands and run them from …/cr-A."

Arm C refusal, verbatim: "This session is isolated in the worktree …/cr-C, but this command runs sed with a value computed at runtime (the variable P) where an option may stand (a value that is not double-quoted, or whose first character is matched or computed rather than spelled out, may begin with -; put -- before it) in a plain command, so what it runs cannot be shown not to be git. Refusing to run it — a worktree-isolated session's git operations must target its own worktree. Run the plain command from …/cr-C."

**What the A/B pair shows:**
- The URL contains the substring "git" (`raw.githubusercontent.com`), but B has the same URL and ran, so the substring alone isn't the trigger.
- Adding `; echo rc=$?` is enough to cause the refusal. That's the new minimal shape for upstream.
- Arm C's refusal text itself suggests `"$P"` or `--` would get it through. I didn't test that.

**The comment:**
- It went from the `sortakool` account; that's who `gh` is logged in as.
- I re-fetched the issue: it now has 2 comments and the last is ours, created 2026-10-03T20:07:25Z.
- It carries the setup, the table above and both verbatim refusals. Paths are shortened to `<repo>`.
- It adds the transcript evidence as non-clean-room: about 160 refusals on 2.1.287/2.1.288, the `gh api … > /tmp/x; echo rc=$?; wc -l /tmp/x` shape, and that the 2.1.257/2.1.259 fixes don't appear to hold. I corrected the draft's "about 190": the report's own numbers give about 164 on those two versions.
- I left out the draft's `cd <own worktree> && git log` working-directory claim, because the clean room didn't test it.
- I opened no issues and commented nowhere else.

**Cleanup:** the throwaway repo, including its `.claude/worktrees/cr-*`, and `/tmp/cr-b.toml` are deleted; I confirmed the repo directory is gone. The evidence stays in `/Users/rmanaloto/.claude/jobs/28f1a8f7/tmp/cleanroom/`: out-*.jsonl, rc-*.txt, err-*.txt, prompt-*.txt, run.sh, comment-95122.md and post.log.

**Persistence:** I appended a section headed "Clean-room repro of worktree-isolation false refusal" to the main checkout's `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md`, which is gitignored. The coordinator worktree has no findings.md. Nothing in the repo was modified. This report should be persisted verbatim under `docs/research/kb/reports/agents/`.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — one comment posted on #95122 (Ray-approved); issue re-fetched to verify.
