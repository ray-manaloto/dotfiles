# Coordinator-gate identity research (read-only lane)

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: Plan subagent (read-only), on Ray's
> request relayed by lane L0. Harness note on receipt: output matched an instruction-shaped pattern (settings-json),
> control tags neutralized; no directives acted on. Coordinator follow-up: `/tmp/null_unused_never` (timing output,
> 0 credential-pattern hits) was removed; the messaging-token exposure below was reported to Ray.

This lane was read-only, so nothing was persisted to `findings.md` or `progress.md`. The coordinator should save this report.

**Two process slips to disclose:**
- One probe ran `/usr/bin/time ... 2>/tmp/null_unused_never`. That created an empty file at `/tmp/null_unused_never`. I did not delete it, because deleting is also a write. Please remove it.
- An env-dump probe was meant to redact secrets with a `sed` filter, but BSD sed does not support `\|`, so it printed this session's `CLAUDE_CODE_MESSAGING_TOKEN` into my transcript. I have not repeated the value here. The exposure is low: on macOS the socket is limited to your OS user and the auth line is optional (`cross-session-messaging.md:275-281`).

### Verdict
Guarding against accidents is the right goal. But the current gate does **not** catch the most likely accident: a lane copying a command that carries the coordinator's id. Session ids routinely appear in prose. For example, the live coordinator's `~/.claude/jobs/28f1a8f7/state.json` `intent` field quotes the previous coordinator's full session id. An inline `CLAUDE_CODE_SESSION_ID=<coord> mise run handoff-inbox -- plan-apply ...` copied from a brief passes `require_newest_coordinator` (`python/src/dotfiles_setup/handoff_inbox.py:162-192`).

There is a second input the caller controls: `--jobs-dir` is accepted on every verb (`handoff_inbox.py:287-290`), so a copied command line can also redirect the job lookup.

Option (a), process ancestry, closes the copied-id hole for about 0.3 s per call. It reuses an existing pattern and is the same evidence the harness itself uses to recognise its own children.

### Probe evidence (live, 2026-10-03, claude 2.1.288)
- **Is the claude process an ancestor of a Bash child?** Yes, it is the direct parent. My Bash shell had `$PPID=50736`. The chain is `shell → 50736 "claude bg-spare --bg-spare …claim.sock" → 50705 "claude bg-pty-host" → 51541 "claude daemon run" → 1 launchd`.
  - The session process's command line does not contain the session id, so a pid-to-session lookup is required.
- **Can the pid be mapped to the job?**
  - `~/.claude/jobs/<id8>/state.json` has no pid field. Its keys include `sessionId`, `daemonShort`, `name`, `createdAt` and `respawnFlags`.
  - `claude agents --json` is documented (`cli-reference.md:28`) and already wrapped in this repo (`dag_tick.py:1048-1061`). It returns `{pid, sessionId, id, name, startedAt, ...}`. Rows seen: `50736 → 28f1a8f7…/dotfiles-20261003T144132.124570000-05.coordinator` and `16799 → 1d335db0…/dotfiles-20261003T143441.L0-urgent-code`. It took 0.21 s; a `ps` snapshot took 0.08 s.
  - `~/.claude/sessions/<pid>.json` holds the same mapping plus `procStart` and `jobId`. Docs mention it only in `changelog.md:1001`, so it is an undocumented internal file. Prefer `agents --json`.
- **Env-spoof arm:** I ran the resolver with `CLAUDE_CODE_SESSION_ID=1d335db0-…` (the L0 lane's id) forced into the env. Ancestry still resolved `root 50736 → job 28f1a8f7 → coordinator name`, while the env said `1d335db0`. So ancestry ignores the env, and a disagreement between the two can be detected.
- **Control arm (a different session must not match):** the L0 lane's Bash child, pid 70761, resolved to `root 16799 → job 1d335db0 → name …L0-urgent-code`, which is not a coordinator. Pid 16799 is not in my chain (`6584 50736 50705 51541 1` → NO).
- **Pid-reuse guard:** for spare-claimed background sessions, process start is earlier than `startedAt`. The coordinator's process started at 19:34:42Z but `startedAt` is 19:41:33.962Z (claimed 7 minutes after spawn); the L0 lane started at 19:15:20Z with `startedAt` 1791056084155 ms. The correct guard is therefore `ps lstart(root) <= startedAt`. A reused pid starts later and fails that check. Equality must not be required.
- **Subagent finding:** I am a subagent of the coordinator, and my Bash children have the coordinator's pid as parent and carry its `CLAUDE_CODE_SESSION_ID`. Neither env nor ancestry can tell coordinator subagents apart from the coordinator's main thread. Only hook input can: `agent_id` is present only inside a subagent (`hooks.md:267, 767`).

### Options, recommended first

**1. (a) Process ancestry, cross-checked against the env — RECOMMENDED**
How it works:
- Walk the `ps` ancestors of the gate process (`reap.ancestor_pids`, `reap.py:217`).
- Take the first ancestor whose pid appears in `claude agents --json`, rather than the regex.
- Require `ps lstart <= startedAt`, require that row's `sessionId` to equal the env `CLAUDE_CODE_SESSION_ID`, then run the existing name and newest-`createdAt` checks.

PRO:
- Stops the copied-env accident: the env-spoof probe above shows a lane resolves to its own job.
- The pattern already exists: `session_orphans._session_root` (`session_orphans.py:170-176, 317`).
- The harness uses process evidence itself to verify its own children (`cross-session-messaging.md:290-292`).
- Fails closed when there is no ancestor, e.g. after `setsid` or `nohup`.
- Enforced inside the program however it is invoked: mise, `uv run`, or a script.
- Cheap (about 0.3 s) and uses only documented CLI output.

CON:
- Not proof against a hostile same-uid process. The docstring caveat at `handoff_inbox.py:22-26` should be narrowed, not removed.
- Coordinator subagents pass; same as today.
- Depends on the `agents --json` row shape (keys `pid`, `sessionId`, `startedAt`) and on the CLI being on PATH.
- `/clear` rotates the session id (`env-vars.md:352`). Untested whether `agents --json` updates at the same moment; it needs an arm.
- The regex `session_orphans.py:27` (`(?:^|[/\s])claude(?:\s|$)`) would match a wrapper shell whose `-c` text contains ` claude `. That causes a false refusal, which is why it should match on the pid set and not reuse the regex.

**2. (c′) PreToolUse hook that checks the harness-supplied `session_id` / `agent_id` — optional second layer**
The hook would deny a Bash command naming a privileged handoff-inbox verb unless the stdin `session_id` is the newest coordinator. If you want to exclude subagents, it would also deny when `agent_id` is present.

PRO:
- The only harness-supplied identity a model cannot forge (`hooks.md:748-754, 767`).
- The only option that can tell the coordinator's main thread from its subagents.
- The guard is already wired (`.claude/settings.json:70-78` → `hook_guard.py`).

CON:
- It matches command text, so a script or alias gets past it. The docs say Bash rules are "not a security boundary" (`permissions.md:247`), and that applies equally to text matching in a hook.
- It fails open on a crash (`hook_guard.py:1104`).
- `decide_payload` (`hook_guard.py:1075`) receives only `tool_input`, so it needs plumbing to see `session_id`/`agent_id`.
- Adds latency to every Bash call.

**3. (e) Keep as is and document it**
PRO: no code. It stops lanes or superseded coordinators that run with their own env (the arms in `tests/test_handoff_inbox.py:135-142`).
CON: it does not stop the most likely accident (a copied id). `--jobs-dir` is a second input the caller controls. The current docstring is accurate but undersells the gap.

**4. (c) Permission rules in settings, per session**
Per-session settings are possible through `--settings` at launch; this repo's job `respawnFlags` already pass `--settings`. Lanes could be launched with `deny: ["Bash(mise run handoff-inbox -- plan-apply*)", …]`.
PRO: declarative, and enforced by the harness.
CON:
- Not a security boundary; `uv run python -m …` and other forms get past it (`permissions.md:239, 247, 281`).
- Fails open when a launcher forgets the flag.
- Deny beats allow, so you cannot write "deny all, allow coordinator" in shared project settings.
- `ask` would stall unattended background lanes.
- Project settings apply to the whole session (`sub-agents.md:236`).

**5. (d) Capability token file held by the coordinator under the main checkout's `.agent/state`**
PRO: simple.
CON:
- Every lane runs as the same uid and can read it.
- To use it, the coordinator must put the token on a command line, and from there it lands in transcripts and briefs. That is the same copy-accident as the env var.
- Bootstrapping who may mint or rotate it falls back to the env check, i.e. option (e).
- Stale tokens remain after a coordinator crash.
- Does not stop the accident.

**6. (b) An identity from the harness that a child process cannot forge — not available**
- Every identity the harness hands a Bash child is an env var and therefore forgeable: `CLAUDE_CODE_SESSION_ID` (`env-vars.md:352`), `CLAUDE_PID` and `CLAUDE_JOB_DIR` (`env-vars.md:401-402`), `CLAUDE_CODE_MESSAGING_SOCKET` and `CLAUDE_CODE_MESSAGING_TOKEN`.
- The messaging token is checked only by the harness, only for messages a session's own child posts to that session's own socket. It is optional on macOS (`cross-session-messaging.md:279-292`). There is no "verify this token" endpoint, and posting to the socket injects a message into the coordinator's conversation.
- The harness's own unforgeable evidence is process ancestry, which is option (a), plus hook stdin, which is option (c′).

### Does each option stop accidental impersonation (a lane copying an env var or command from a brief)?
- **(a): yes.** The probe shows the env is ignored or flagged as a mismatch.
- **(c′): yes** for the command forms it matches.
- **(c): partially.** Only lanes launched with the flag, and only the exact command form.
- **(d): no.** The token gets copied like the id.
- **(e): no.**
- **(b): not available.**

### Arms the implementation must add (for a)
1. Positive: the nearest session ancestor is the newest coordinator and the env agrees → pass.
2. **Env spoof:** env equals the newest coordinator's id but the ancestor resolves to a lane → refuse. This is the accident arm the tests lack today.
3. Reverse mismatch: env names a lane but the ancestor is the coordinator → refuse with a "mismatch" message.
4. No session ancestor, e.g. reparented to launchd or run from a plain terminal → refuse.
5. The ancestor's pid is not in `agents --json` → refuse.
6. Pid reuse: `ps lstart(root) > startedAt` → refuse. Also an arm for a spare-claimed session where `lstart < startedAt` → pass.
7. Superseded coordinator, resolved through ancestry → refuse (the existing arm, re-pinned).
8. A nested `claude -p` under a lane is the nearest listed ancestor → refuse. This pins the "nearest wins" rule.
9. `agents --json` fails, times out, or returns malformed output → refuse (fail closed).
10. A wrapper shell whose command text contains ` claude ` is not treated as the root, i.e. selection is by pid set and not by regex.
11. `--jobs-dir` cannot change the identity result: identity comes from ps plus `agents --json`. Tests inject the process table and agent rows through function parameters, not CLI flags. Consider dropping `--jobs-dir` from the three privileged verbs.
12. `/clear` session-id rotation: the row's `sessionId` matches the post-clear env.
13. A live integration test, skipped outside a claude session: the probe resolves to its own `CLAUDE_CODE_SESSION_ID`, and a different live session's pid is absent from its chain.
14. Decide and pin whether coordinator subagents may write. If they may not, that requires (c′).

### Open question for Ray
Should the coordinator's own subagents count as "the coordinator"? Today's env gate and option (a) both say yes. Only the hook layer (c′) can say no.

## GitHub repos touched
None. Read-only: no files edited, no commits, no PRs. The only side effect is the stray empty file `/tmp/null_unused_never`, disclosed above. Read from `ray-manaloto/dotfiles` (worktree `L0-urgent-code` @767ff5b7) and `ray-manaloto/knowledge-base` (harness docs).

### Critical Files for Implementation
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/L0-urgent-code/python/src/dotfiles_setup/handoff_inbox.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/L0-urgent-code/python/src/dotfiles_setup/session_orphans.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/L0-urgent-code/python/src/dotfiles_setup/reap.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/L0-urgent-code/python/src/dotfiles_setup/dag_tick.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/L0-urgent-code/tests/test_handoff_inbox.py
