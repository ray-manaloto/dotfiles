# Research sweep — prompt-free `claude --bg` lanes in sibling worktrees (v2.1.288), 2026-10-03

Question: how can `claude --bg` sessions launched into sibling git worktrees (`../dotfiles.worktrees/<lane>`, outside
`<repo>/.claude/worktrees/`) start and run on v2.1.288 with no human prompts? It has four parts: (1) whether workspace trust
is inherited, and whether project allow rules and `additionalDirectories` apply; (2) the EnterWorktree relocation prompt;
(3) reading the session's own task output under `/private/tmp/claude-501/.../tasks/`; (4) idle-retire, keep-alive and relaunch.

Installed version: `claude --version` returned `2.1.288 (Claude Code)`. The offline corpus
(`$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`) has a changelog that
stops at **2.1.273** (`$CC/changelog.md:11`). For 2.1.274–2.1.288 this sweep used the live GitHub releases, persisted to
`.agent/kb/raw/research-fanout/synthesize/releases-v2.1.252-v2.1.288.txt`.

## Answer

The fan-out nodes ran **only the GitHub sources** (issues, releases, discussions, code search). This synthesize node then
read the offline harness docs, the live releases, `~/.claude.json` trust flags (booleans only), `~/.claude/daemon.log`,
and the 2.1.288 binary's strings. The **exa, context7, firecrawl and last30days lanes did not run.** Treat the sweep as
**incomplete for third-party and community evidence**. The four answers below rest on first-party docs, release notes,
and the shipped binary.

1. **Trust: the side agent's warning does not apply to sibling worktrees of a trusted repository.** The docs say trust
   is keyed on the git repository root, and "In a worktree, it uses the main checkout's root" (`$CC/permissions.md:648`).
   A sibling `git worktree add` path therefore inherits the main checkout's trust, and project `permissions.allow` /
   `additionalDirectories` apply there once the main checkout is trusted.
   - Measured: `~/.claude.json` has `projects["/Users/rmanaloto/dev/github/ray-manaloto/dotfiles"].hasTrustDialogAccepted = true`.
     It has **0** `worktrees` keys among its 41 project keys, even though sessions (this one included) run in
     `dotfiles.worktrees/*`. The worktree's `git rev-parse --git-common-dir` resolves to `.../dotfiles/.git`.
   - The real hazard is narrower. Since **v2.1.281**, `claude --bg` in an untrusted directory "now asks for trust first,
     or exits when not run interactively". A `claude respawn` into an untrusted cwd fails with
     `errorCode:"workspace_untrusted"` and queues the prompt (2.1.288 binary). A launcher should **preflight** the trust
     flag of the main checkout and fail loud, rather than add allow rules.
2. **EnterWorktree relocation prompt: avoid it structurally.** Neither an `EnterWorktree` permission rule nor "don't ask
   again" suppresses it; only `bypassPermissions` skips it (`$CC/worktrees.md:43`). The docs give a way around it:
   background sessions skip the worktree step "when the session is already inside a linked git worktree, whether Claude
   created it under `.claude/worktrees/` or you created it with `git worktree add` somewhere else"
   (`$CC/agent-view.md:494`).
   - The recipe: launch with cwd = the sibling worktree, plus `--disallowedTools EnterWorktree`. A bare tool name
     "removes the matching tools from Claude's context" (`$CC/cli-reference.md:84`), so the model cannot reach the prompt.
   - `worktree.bgIsolation: "none"` does **not** address this. It only lets background sessions edit the *working copy*
     without isolation, which defeats the point of lanes.
3. **Own task output: the Read tool should not prompt in a background session.** The auto-mode prompt before the first
   read outside the working directories "doesn't appear in non-interactive `-p` runs or background sessions; reads there
   run as before" (`$CC/permission-modes.md:423`).
   - The exception: `permissions.blockReadsOutsideWorkingDirectories` is on. Then file-reading Bash commands such as
     `cat` prompt "even in auto mode and `bypassPermissions` mode" (`$CC/permission-modes.md:43`).
   - That key is **absent** from both `~/.claude/settings.json` and the project `.claude/settings.json` (`grep -c` = 0,
     control `"permissions"` = 1 in each).
   - A Bash input redirect (`< file`) to a path outside the working directories "needs your approval unless an allow rule
     covers it" (`$CC/permissions.md:302`).
   - The observed prompt is therefore most likely a **Bash** read (redirect or path check), not the Read tool. That
     attribution is **unverified** in a live `--bg` session (Gaps).
4. **Idle retire is a fixed rule, and a session cron exempts a session.** Retirement is confirmed in the 2.1.288 binary:
   `if(w.includes("session_cron"))return{retired:!1,reason:"session-cron"}`, then
   `let I=n.bridgeSessionId?Math.max(e,s):e`. The grace is 1 h for a normal session and 8 h for one bridged to Remote
   Control.
   - `~/.claude/daemon.log` has 17 `bg retire` lines. QUALIFIED (verification): the 5 lines at 60m/61m are all `stale-spare`
     (unused pre-warmed spare workers on a separate code path), not idle user sessions. All 12 real-session retirements
     are at 8h, so the log gives **no evidence of the 1h branch for a real session**; the 1h/8h split by bridge status
     rests on the 2.1.288 code and `$CC/agent-view.md:748`. Under low memory the threshold drops to 60 s (`Je=60000`).
     Sessions are also exempt when in flight, `routine`, attached, recently input, or pinned, not only via session cron.
     The 1h/8h values are undocumented 2.1.288 internals.
   - A retired session is not lost: "the next time you attach or reply, the session resumes" (`$CC/agent-view.md:748`).
   - Keep-alive: a `CronCreate` session cron (recurring crons expire after 7 days, `$CC/scheduled-tasks.md:181`), or
     pinning with Ctrl+T.
   - Relaunch: `claude --resume <full-uuid> --bg "<prompt>"` (`$CC/agent-view.md:451`). Since v2.1.285,
     `claude --resume <id> "prompt"` on a session already running in the background is delivered as its next turn.
     `claude respawn <id>` restarts the session onto its saved conversation (`$CC/agent-view.md:695`). It is the right
     verb to pick up a new binary, and the wrong verb to deliver a new prompt.

## Evidence

| Claim | URL or file:line | Quote |
|---|---|---|
| Trust is keyed on the main checkout's root for a worktree | `$CC/permissions.md:648` | "In a repository, Claude Code keys the trust on the git repository root … In a worktree, it uses the main checkout's root" |
| Project allow rules and `additionalDirectories` wait for trust; deny and ask rules do not | `$CC/permissions.md:644` | "`permissions.allow` rules and `permissions.additionalDirectories` entries … Claude Code applies them only after you accept the workspace trust dialog … `deny` and `ask` rules aren't affected" |
| Trusting a *parent folder* does not count for allow rules (this is distinct from the worktree case) | `$CC/permissions.md:652`, `:676` | "trusting a parent folder doesn't count for these rules" |
| Manual trust key | `$CC/permissions.md:682` | "set `projects[\"<path>\"].hasTrustDialogAccepted` to `true` in `~/.claude.json`, where `<path>` is the repository root" |
| Local (untracked) `settings.local.json` allow rules skip trust | `$CC/settings.md:467` | "Its allow rules don't wait for trust while the file stays untracked." |
| Measured: main checkout trusted; no per-worktree keys | `~/.claude.json` (jq, booleans only) | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles	true`; `grep -c worktrees` over project keys = 0 (control: `grep -c /` = 41) |
| `claude --bg` in an untrusted dir exits when non-interactive (v2.1.281) | https://github.com/anthropics/claude-code/releases/tag/v2.1.281 | "Fixed `claude --bg` starting a background session, and running its project hooks, in a directory that had not passed the workspace trust prompt; it now asks for trust first, or exits when not run interactively" |
| Respawn into an untrusted cwd is refused and the prompt queued | 2.1.288 binary strings (`/Users/rmanaloto/.local/share/claude/versions/2.1.288`) | `if(b.verdict==="untrusted"){p("job_respawn","workspace_untrusted",…);let B=!!r?.initialPrompt&&await SCe(…);return{ok:!1,…,queued:B,errorCode:"workspace_untrusted"…}` |
| EnterWorktree outside `.claude/worktrees/` always asks; only bypass skips it | `$CC/worktrees.md:43` | "An `EnterWorktree` permission rule or choosing 'don't ask again' doesn't suppress this prompt; only `bypassPermissions` mode skips it." |
| Bg sessions skip the worktree step when already in a linked worktree | `$CC/agent-view.md:494` | "The session is already inside a linked git worktree, whether Claude created it under `.claude/worktrees/` or you created it with `git worktree add` somewhere else" |
| `--disallowedTools` with a bare name removes the tool | `$CC/cli-reference.md:84` | "A bare tool name removes the matching tools from Claude's context" |
| `worktree.bgIsolation` only toggles working-copy isolation | `$CC/settings-reference.md:4965-4972`; https://github.com/anthropics/claude-code/releases (changelog `$CC/changelog.md:3067`) | "`\"none\"`: background jobs edit the working copy directly"; "Added `worktree.bgIsolation: \"none\"` setting … without `EnterWorktree`" |
| The relocation prompt stalls unattended agents (issue, **proposal** for an allow rule) | https://github.com/anthropics/claude-code/issues/77069 (OPEN) | "background build agents running unattended — each of which now stalls on a permission prompt until a human answers" |
| The dialog is not relayed to Remote Control, so a `--bg` session hangs silently | https://github.com/anthropics/claude-code/issues/96490 (OPEN) | "For a `--bg` session, the local TUI is the one place nobody is looking" |
| An approved path is not remembered; worktree→worktree switches are refused | https://github.com/anthropics/claude-code/issues/94265 (OPEN) | "An approved path is not remembered. Re-entering a path already approved in the session prompts again." |
| A non-nested EnterWorktree half-applies (Write/Edit binding is kept) | https://github.com/anthropics/claude-code/issues/95389 (OPEN) | "`Bash` cwd updates … but `Write`/`Edit` continue to enforce the *original* launch worktree" |
| Subagents in sibling worktrees count as outside the project | https://github.com/anthropics/claude-code/issues/92417 (OPEN) | "every `Edit`/`Write` they make in that worktree is outside the working-directory tree" |
| One directory can be stored under up to three path spellings, which splits trust | https://github.com/anthropics/claude-code/issues/88418 (OPEN) | title: "`.claude.json` stores one project directory under up to three different path spellings, splitting trust, MCP servers, and worktree state" |
| No first-read prompt in background sessions | `$CC/permission-modes.md:423` | "The prompt doesn't appear in non-interactive `-p` runs or background sessions; reads there run as before." |
| `blockReadsOutsideWorkingDirectories` makes Bash reads prompt even in auto and bypass mode | `$CC/permission-modes.md:43`; `$CC/settings-reference.md:1539` | "recognized file-reading Bash commands … prompt even in auto mode and `bypassPermissions` mode" |
| Bash input redirect outside the working dirs needs approval | `$CC/permissions.md:302` | "A target outside the working directories needs your approval unless an allow rule covers it." |
| Task-output path shape | `$CC/errors.md:3225` | "/private/tmp/claude-501/-Users-you-my-project/<uuid>/tasks/b7k2f9m3q.output" |
| A project `env` cannot set `CLAUDE_CODE_TMPDIR` | `$CC/changelog.md:869` | "project-level `.claude/settings.json` `env` … no longer set `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_TMPDIR`, or `TMPDIR`" |
| The per-job scratch dir is prompt-free for Write/Edit | `$CC/agent-view.md:765-767` | "`~/.claude/jobs/<id>/tmp/` … Claude's `Write` and `Edit` calls here don't prompt for permission"; `CLAUDE_JOB_DIR` |
| Idle stop after "about an hour"; a session paused on a dialog keeps running | `$CC/agent-view.md:747-748` | "Working, paused on a permission prompt or other dialog, or attached: the process keeps running" / "unattached for about an hour: the supervisor stops the process" |
| Bridged grace is 8 h; session cron exempts (binary, 2.1.288) | binary strings | `if(w.includes("session_cron"))return{retired:!1,reason:"session-cron"};if(n.routine)…;let I=n.bridgeSessionId?Math.max(e,s):e` |
| Retire durations observed (QUALIFIED: the 60m/61m lines are `stale-spare` workers, not sessions) | `~/.claude/daemon.log` (re-derived) | 17 `bg retire`: 5× `stale-spare` at 60m/61m, 12× `idle 8h` (real sessions) |
| `/loop` counts as `working` | `$CC/agent-view.md:724` | "between steps of work it drives on its own, such as a `/loop` iteration" |
| Recurring crons expire after 7 days | `$CC/scheduled-tasks.md:181` | "Recurring tasks automatically expire 7 days after creation." |
| Resume into a bg session | `$CC/agent-view.md:451` | `claude --resume 1f0e2c9a-… --bg "pick up where you left off…"` |
| `--resume` on a running bg session delivers the prompt (v2.1.285) | https://github.com/anthropics/claude-code/releases/tag/v2.1.285 | "a prompt given with `claude --resume <id> \"prompt\"` is sent to it as its next turn" |
| `claude respawn` semantics | `$CC/agent-view.md:695` | "Restart a session, running or stopped, e.g. to pick up an updated Claude Code binary. The restarted session resumes its saved conversation" |
| Flags survive retire→wake | `$CC/changelog.md:2589` | "Background sessions now preserve `--ide`, `--chrome`, `--bare`, `--remote-control`, and other flags across retire→wake" |
| `claude agents` may hide a pending permission prompt (fixed v2.1.287) | https://github.com/anthropics/claude-code/releases/tag/v2.1.287 | "Fixed `claude agents` sometimes not showing the permission prompt a background session is waiting on" |
| A bg pause loses background agents silently (Agent-tool subagents, not `--bg`) | https://github.com/anthropics/claude-code/issues/63023 (OPEN) | "no completion notification ever arrives for them" |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `EnterWorktree repo:anthropics/claude-code` | query | planner | 0 (armed; see note) | 0 |
| `bgIsolation repo:anthropics/claude-code` | query | planner | 0 (armed; **blind**, see Conflicts) | 0 |
| `claude repo:anthropics/claude-code` | must-hit | planner | 419 | 0 |
| `qvzkjw7xplm3rt repo:anthropics/claude-code` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |

Note: anthropics/claude-code has discussions disabled (repos API), so github-discussions is not searchable there. That
is not a gap.

### Dependency-repo fan-out

| repo | query | required sources failed | manifest |
|---|---|---|---|
| anthropics/claude-code | background session worktree trust | none (`[]`) | `.agent/kb/raw/research-fanout/research--kb--reports--agents--research-sweep-autostart-2026-10-03/deps/anthropics--claude-code/1/manifest.json` |

Topic manifests: `.agent/kb/raw/research-fanout/background-session-worktree-trust-prompt/manifest.json` and
`.agent/kb/raw/research-fanout/enterworktree-outside-claude-worktrees/manifest.json`.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| _(no links were supplied with the request; MIRRORS input was empty)_ | — | — | — | — |

## Conflicts resolved

1. **The side agent's "project settings stay off in a new worktree folder" against `$CC/permissions.md:648`.** I trusted
   the docs plus the measurement. The docs key trust on the **main checkout's root** for a worktree. `~/.claude.json` has
   no per-worktree key, while the main checkout is `true` and sessions run in `dotfiles.worktrees/*`.
   - The side agent conflated two cases. The "trusted only a parent folder" column (`$CC/permissions.md:676`) covers a
     *directory* inside a trusted parent. A worktree is a separate case.
   - Residual risk: the issue-thread claim attributed to #77069 ("Settings that skip permission prompts don't take
     effect in a new worktree folder…") is the **side agent's own note** echoed into the claims JSON. It does not appear
     in the live #77069 body: `grep -c 'stay off|until someone accepts'` = 0, control `unattended` = 1. It is also absent
     from every fan-out raw file. I discarded it as an issue claim.
2. **`--bg` in an untrusted dir.** The pre-2.1.281 behaviour (session started and hooks ran) is superseded by v2.1.281
   ("asks for trust first, or exits when not run interactively"). Newer wins.
3. **The code-search 0 for `bgIsolation` against the corpus.** `bgIsolation` is in the upstream CHANGELOG (mirrored at
   `$CC/changelog.md:3067`) and in shipped docs. The armed 0 is therefore a **blind probe**: GitHub code search did not
   index that content, likely because of a file-size limit. It is not absence. The same applies to `EnterWorktree`.
   Shipped docs and release notes beat the code-search count.
4. **"Idle about an hour" (docs) against "8 h" (logs).** Both hold. The binary picks `Math.max(e,s)` when
   `bridgeSessionId` is set. The docs describe only the unbridged case. The binary and daemon.log beat the doc's
   simplification.
5. **#63023 "background agents silently die".** This concerns Agent-tool `run_in_background` subagents on host sleep. It
   is older than `$CC/agent-view.md:136` ("Sessions are also preserved when your machine sleeps"), which covers `--bg`
   sessions. I kept it as an adjacent risk, not as evidence about `--bg` retire.
6. **Three kinds of claim kept apart.** What ships: the docs, release notes and binary rows. What is proposed: the
   #77069 allow-rule syntax `EnterWorktree(/path-*)`, which **does not exist**. What third parties document: the issue
   reporters' layouts.

## Verification

Five refuters, one critic and one adjudicator ran; none returned null. Failed stages: none. No refuted claim was upheld.

| # | Claim | Result |
|---|---|---|
| 1 | Sibling worktrees inherit the main checkout's trust; project allow rules and `additionalDirectories` apply | **Confirmed.** The refuter called it misleading (headless `-p`/SDK needs the exact folder trusted; user-level rules bypass trust; `settings.local.json` is held when tracked). The adjudicator OVERTURNED that: `permissions.md:648` keys a worktree on the main checkout's root, `git rev-parse --git-common-dir` from this worktree resolves to `.../dotfiles/.git`, and that key is `hasTrustDialogAccepted=true`. The 0-worktree-keys count is weak and is not the evidence; the doc line is. Holds only while the main-checkout key stays true and the path spelling matches (Gaps). |
| 2 | Since v2.1.281, non-interactive `claude --bg` in an untrusted dir exits; 2.1.288 respawn returns `workspace_untrusted` and queues the prompt | **Confirmed** (adjudicator overturned "misleading"). "Queues the prompt" holds only when an initial prompt was supplied. Trust can also be satisfied without a human via a persisted key (possibly an ancestor's) or `CLAUDE_CODE_SANDBOXED`; the preflight recommendation already relies on the persisted key. |
| 3 | No `EnterWorktree` rule or "don't ask again" suppresses the outside-`.claude/worktrees/` prompt; only `bypassPermissions`; `EnterWorktree(path)` syntax exists only as proposal #77069 | **Confirmed** (adjudicator overturned "misleading"). `worktrees.md:43` verbatim; docs have 0 hits for `EnterWorktree(`; #77069 open. Scope note: a bare `EnterWorktree` allow rule does work for ordinary approval; the claim concerns only the outside-path prompt. |
| 4 | A bg session already in a linked worktree skips the EnterWorktree isolation step; `--disallowedTools EnterWorktree` removes the tool | **Confirmed** (adjudicator overturned "misleading"). Scope note: in the MAIN checkout, removing EnterWorktree would block edits (`changelog.md:2590`); the recipe is valid only because cwd is already the linked worktree. Whether the flag survives retire/wake is unverified (Gaps). |
| 5 | 1h idle (8h bridged) retire, session cron exempt, no first-read prompt in bg | **UPHELD as misleading.** Code and doc parts are correct. Omissions: the daemon.log 60m lines are `stale-spare` workers, not sessions, so the log never shows a 1h real-session retire; low-memory 60 s threshold; other exemptions (inflight, routine, attached, pinned). The Answer and Recommendation 4 are now qualified accordingly. The first-read-prompt part is confirmed. |

Control arms (from the verifiers): fresh absent tokens returned 0 in the binary strings, `daemon.log`, and issue search while
present tokens hit; the `permissions.md` trust-failure paragraphs were found, so the doc probe can return the opposite verdict.

**How the conclusion changes:** the four recommendations stand (preflight main-checkout trust; launch inside the worktree with
`--disallowedTools EnterWorktree`; Read tool for task output; resume/respawn verbs). Only the keep-alive advice weakens:
the 1h figure is code-derived rather than log-confirmed, and a cron is not a guarantee under memory pressure or for other
exemption paths. The sweep remains **INCOMPLETE** for third-party and community evidence (exa, context7, firecrawl,
last30days did not run); no mandatory gap was reported by the harness.

## Gaps

- **Critic gap: no live arm of trust inheritance for a new sibling worktree.** Next probe: `git worktree add` a throwaway
  sibling, run `claude --bg` from it and require a running state in `claude agents --json --all`, not `workspace_untrusted`;
  control in a `mktemp -d` non-repo dir (must exit); repeat with the project allow rule present and removed.
- **Critic gap: Q3 attribution unverified.** No live `--bg` auto-mode reproduction of the "outside allowed working
  directories" prompt. Next probe: in a sibling-worktree `--bg` session run Read, `cat`, `tail` and `< file` on its own
  `/private/tmp/claude-501/.../tasks/*.output`, record pending prompts via `claude agents --json`, and repeat with
  `--add-dir /private/tmp/claude-501`.
- **Critic gap: `--disallowedTools EnterWorktree` never run.** Unknown whether it survives retire to wake or respawn
  (`changelog.md:2589` says only "other flags"). Next probe: retire a lane started with the flag, wake it by reply and by
  `claude respawn`, then ask it to call EnterWorktree; grep the 2.1.288 strings for the flag-persistence list.
- **Critic gap: no third-party or community evidence.** exa, context7, firecrawl and last30days never ran; only
  anthropics/claude-code was searched. Next probe: run them on "claude --bg worktree trust unattended", "EnterWorktree
  permission prompt headless", "claude agents idle retire keepalive", plus code search for `--disallowedTools EnterWorktree`
  and `hasTrustDialogAccepted` across other repos, each with a nonsense-token control.
- **Critic gap: issue/PR/release state not fully re-read.** Linked PRs and maintainer comments for #77069, #94265, #96490,
  #95389, #92417, #88418 were not queried; releases after 2.1.288 and whether 2.1.288 is latest were not confirmed. Next
  probe: `gh api repos/anthropics/claude-code/issues/<n>/timeline`, a PR search for worktree|trust|bg, and the releases API.
- **Critic gap: wake and resume semantics.** Not checked: whether a retired session wakes on `SendMessage`; whether the
  7-day cron expiry applies to exempt session cron; whether `claude --resume <sid> --bg` keeps the original permission mode
  and flags. Next probe: retire a test session, exercise each wake path and diff the session JSON.
- **Critic gap: path-spelling hazard (#88418).** A realpath vs `/private/tmp`/`/tmp` spelling may miss the stored trust key,
  so the jq preflight could pass on one spelling and runtime look up another. Next probe: launch from both spellings and
  compare `~/.claude.json` project key names (names and booleans only).
- **Verification gap (claim 5):** the 1h non-bridged retire for a real session is code-derived only; `daemon.log` has no
  such case, and the low-memory 60 s path is untested.
- **Not run: exa, context7, firecrawl, last30days.** There is no third-party or community evidence, and none of the
  "examples from other projects" the request asked for.
- **unverifiedEmpty: background-session-worktree-trust-prompt/github-discussions.** `empty_unverified`, control query
  `claude-code` count 0. Discussions are disabled on the repo, so the probe could not discriminate.
- **unverifiedEmpty: deps/anthropics--claude-code/1/github-discussions.** Same as above.
- **unverifiedEmpty: code-search `EnterWorktree repo:anthropics/claude-code`.** Count 0, armed, unverified, and shown
  blind by Conflict 3.
- **unverifiedEmpty: code-search `bgIsolation repo:anthropics/claude-code`.** Count 0, armed, unverified. Its existence
  is confirmed from docs and the changelog, not from source.
- **unverifiedEmpty: local corpus, exa, context7, firecrawl not probed by fan-out.** This node probed the local corpus.
  The others remain gaps.
- **No live arm of `claude --bg` in a brand-new sibling worktree.** Trust inheritance rests on the docs plus the absence
  of per-worktree keys. The arm is to create a throwaway `git worktree add`, run `claude --bg --exec true` from it, and
  require `claude agents --json --all` to show it running, not `workspace_untrusted`. The control is the same command in
  a fresh `mktemp -d` non-repo directory, which must exit.
- **Q3 attribution is unverified.** It is not known which tool or shape produced the "outside allowed working
  directories" prompt in a live `--bg` auto-mode session. One partial arm passed: in this *foreground subagent*, `Read`
  of my own `/private/tmp/claude-501/.../tasks/bkxth13w8.output` returned without a prompt. That proves nothing about
  `--bg` Bash reads.
- **Not confirmed: whether `--disallowedTools` is among the flags preserved across retire→wake/respawn.**
  `$CC/changelog.md:2589` says "and other flags" without listing them.
- **Not confirmed: whether a retired local session wakes on a `SendMessage`** rather than an attach or reply from
  `claude agents`.
- **The corpus changelog stops at 2.1.273.** 2.1.274–2.1.288 came from live releases only. The offline docs may lag.
- **Not checked: whether #88418's path-spelling split** (`/private/tmp` vs `/tmp`, symlinks) can make a `realpath`-
  launched worktree miss the main checkout's trust key.

## Recommendation

A launch recipe with no human step and no new allow rules:

1. **Preflight trust; do not add allow rules for it.** Before `claude --bg`, assert
   `jq -e '.projects["<main-checkout-realpath>"].hasTrustDialogAccepted == true' ~/.claude.json`. Read the boolean only;
   never print the file.
   - Resolve the main checkout with `git -C <wt> rev-parse --path-format=absolute --git-common-dir` and take its parent.
   - On failure, stop loudly. A non-interactive `claude --bg` there **exits** (v2.1.281), and a respawn returns
     `workspace_untrusted`.
   - Any allow rule that must hold irrespective of trust belongs in **user** settings (`~/.claude/settings.json`), which
     trust never gates. That edit is Ray's decision under the no-user-level-file-updates rule.
2. **Launch from inside the worktree and remove EnterWorktree:**
   `cd ../dotfiles.worktrees/<lane> && claude --bg --name <lane> --disallowedTools EnterWorktree "<brief>"`.
   - This makes isolation a no-op (`$CC/agent-view.md:494`), and the model cannot call the relocation tool.
   - Do **not** set `worktree.bgIsolation: "none"` and do **not** use `bypassPermissions`.
3. **Task output:** brief lanes to use the **Read tool** on the notification's output path, never `cat`/`<`/`tail` in
   Bash. Keep `blockReadsOutsideWorkingDirectories` unset. Lane-owned temp files go to `$CLAUDE_JOB_DIR/tmp`
   (prompt-free).
   - If Bash reads must stay, launch with `--add-dir /private/tmp/claude-501` (a CLI flag, not trust-gated).
   - Run the live arm from Gaps first.
4. **Keep-alive and relaunch:**
   - A lane waiting for GO either holds a `CronCreate` session cron (exempt via `session-cron`; renew before 7 days) or
     accepts the retire. Retire is not loss, because a reply or attach resumes it. Other exemptions exist (in-flight
     work, `routine`, attached, pinned); under low memory the grace drops to 60 s and even pinned sessions can be
     stopped (`$CC/agent-view.md:861`), so do not treat any keep-alive as guaranteed.
   - Deliver new work with `claude --resume <full-uuid> --bg "<prompt>"`, or with `claude --resume <id> "<prompt>"` on a
     running one (v2.1.285).
   - Reserve `claude respawn` for binary upgrades.
   - Detect state with `claude agents --json --all`, not `ListAgents`.
5. **Saved GitHub searches** to watch for future changes:
   - https://github.com/anthropics/claude-code/issues?q=is%3Aissue+EnterWorktree+%22.claude%2Fworktrees%22+sort%3Aupdated-desc
   - https://github.com/anthropics/claude-code/issues?q=is%3Aissue+%22workspace+trust%22+worktree+sort%3Aupdated-desc
   - https://github.com/anthropics/claude-code/issues?q=is%3Aissue+%22--bg%22+%28retire+OR+idle%29+sort%3Aupdated-desc
   - https://github.com/anthropics/claude-code/issues?q=is%3Aissue+%22outside+the+working+directories%22+OR+blockReadsOutsideWorkingDirectories
   - https://github.com/anthropics/claude-code/issues?q=is%3Aissue+bgIsolation
   - https://github.com/anthropics/claude-code/issues?q=is%3Aissue+%22Remote+Control%22+dialog+%22--bg%22
   - CLI form (control-armed): `gh api -X GET search/issues -f q='repo:anthropics/claude-code EnterWorktree "claude/worktrees"' --jq .total_count`.
     Pair it with a fresh nonsense-token query that must return 0. Do not use `gh search issues --repo`, which is broken
     here (memory).
   - Release feed: `gh api 'repos/anthropics/claude-code/releases?per_page=10' --jq '.[]|.tag_name'`, grepping the
     bodies for `worktree|trust|--bg|retire|respawn`.
   - Subscribe to #77069, #94265, #96490, #95389, #92417 and #88418. All were OPEN on 2026-10-03; the control was a
     bogus issue number returning 404.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| triage | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): issues #77069, #96490, #94265, #92417, #95389, #90638, #88418, #63023 and #90264 (live state read); releases v2.1.252–v2.1.288; CHANGELOG via the KB mirror; code search.
- [cli/cli](https://github.com/cli/cli): code-search health probe only.
