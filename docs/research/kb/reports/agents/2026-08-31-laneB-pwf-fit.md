# planning-with-files 3.12.0: fit for granular, small-context execution

## Scope and evidence

This is a read-only audit of the installed cache at `/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0` (abbreviated **PWF** below) and the current dotfiles checkout at HEAD `5f51d6922f82e0fdf476bcda59ff17730e7ddffa`. All `scripts/...`, `hooks/...`, `skills/...`, and `templates/...` citations are relative to that PWF cache root; `.gitignore` citations without a prefix refer to the dotfiles repository.

Graphify was attempted first as required, but `mise run graphify-health` exited 2 because `uv` could not initialize `/Users/rmanaloto/Library/Caches/uv` under the sandbox (`Operation not permitted`). Per the Graphify skill, no query was run against an unhealthy graph and source became the authority. The optional `plugin-eval` helper was also unavailable (`zsh: command not found: plugin-eval`). Neither failure limits the direct code measurements below.

Measurements ran the shipped `inject-plan.sh` and Claude dispatcher against the live ignored plan and isolated `/private/tmp` fixtures. “Model-visible bytes” means the UTF-8 byte length of decoded `additionalContext` or `systemMessage`; “wire bytes” means the complete hook JSON written on stdout. This is the closest exact cost the plugin exposes: `frame_file` computes byte length and emits text, and the dispatcher JSON-encodes that text; neither path names a model or calls a tokenizer (`scripts/inject-plan.sh:927-946`; `hooks/claude-hook.sh:37-46`). Therefore **an exact token count cannot be determined from this plugin or this request**: it requires a specified host/model tokenizer and the host's final message framing. I report exact measured bytes and do not turn them into estimated tokens.

## Executive verdict

- **Q1 — Partial, not the requested executor.** The plugin can persist a granular plan and rehydrate a cleared/fresh session from disk, but it does not decompose work into bounded task packets, open a fresh context per task, measure the context window, or enforce the operator's 20% ceiling. It is a state substrate plus reminders/hooks, not a small-context scheduler (`templates/task_plan.md:11-25`; `hooks/hooks.json:4-99`).
- **Q2 — Yes, selectively.** Tracking the human planning artifacts does not break resolution, injection, attestation, or ledgers; those mechanisms use ordinary files. Tracking the entire runtime directory is unsafe operationally: it carries a shared active pointer, session attachments, Stop counters, ledger watermarks, locks, and an attestation tied to exact working-tree bytes into clones and merges (`scripts/resolve-plan-dir.sh:207-268`; `scripts/check-complete.sh:183-215`).
- **Q3 — Material silent and wrong-result modes exist.** The most serious is an oracle split: plan injection checks attestation, while the gated Stop path does not. A controlled replay changed an attested plan to all-complete; injection reported `PLAN TAMPERED`, but Stop reported `ALL PHASES COMPLETE` and allowed termination. The gate dispatcher calls only `check-complete --gate`, whose decision path contains no hash/attestation check (`scripts/gate-stop.sh:19-32`; `scripts/check-complete.sh:50-72,74-109,132-252`).

## Q1 — Does it support granular, small-context task execution?

### Verdict: it supports state recovery, not automatic small-context task execution

The plan format supports 3–7 phases and one `Next Step`, but places no size/context constraint on a phase. Nothing in the executable hooks chooses one task, launches a new session, clears context, or rejects an oversized context. The hook inventory is lifecycle injection/reminders plus Stop checking (`templates/task_plan.md:11-25`; `hooks/hooks.json:4-99`).

The actual cross-context state is:

1. `task_plan.md` carries goal, phase statuses, decisions, and next step; `progress.md` carries the recent log; `findings.md` carries research (`skills/planning-with-files/SKILL.md:96-103`).
2. On startup, resume, clear, or compact, `SessionStart` runs the dispatcher. The dispatcher calls `session-catchup.py --no-history` and then injects the same bounded user-prompt view of plan/progress (`hooks/hooks.json:4-20`; `hooks/claude-hook.sh:60-83`).
3. `--no-history` returns before even detecting a host store. Thus automatic recovery is strictly whatever was flushed to project files; unrecorded conversation state is lost (`scripts/session-catchup.py:669-676`).
4. `findings.md` is not injected. The payload ends with an unscoped `Read findings.md` reminder, and the skill asks a resumed agent to read all three files; that manual read is unbounded by this plugin and can refill a new context with a large findings file (`scripts/inject-plan.sh:1231-1232`; `skills/planning-with-files/SKILL.md:38-45`). In scoped mode, that reminder and the PostToolUse reminder also omit the resolved directory, so the model must resolve the active plan before reading/updating the right files (`hooks/claude-hook.sh:106-110`).

That means a human can manually make each phase small, update the files, issue `/clear`, and resume. The plugin does not do the decomposition or context rotation itself.

### Exact injection frequency and byte cost

Claude registers exactly one `UserPromptSubmit` hook, one `PreToolUse` hook matching `Write|Edit|Bash|Read|Glob|Grep`, and one `PostToolUse` hook matching `Write|Edit|Bash` (`hooks/hooks.json:21-67`). The dispatcher maps those to full `userprompt`, short `pretool`, and a fixed progress-update reminder respectively (`hooks/claude-hook.sh:93-111`). Therefore, for legacy mode:

```text
routine turn bytes = U
                   + P * count(Read, Glob, Grep, Write, Edit, Bash)
                   + 120 * count(Write, Edit, Bash)
```

Here `U` and `P` depend on the selected file bytes. Unmatched tool types add no PWF hook payload. A startup/resume/clear/compact event adds one SessionStart `U` before the normal next prompt; PreCompact separately emits a fixed reminder (`hooks/hooks.json:4-20,68-82`; `hooks/claude-hook.sh:112-115`).

| Measured case | UserPromptSubmit / turn start | PreToolUse per matched call | PostToolUse per Write/Edit/Bash | Evidence |
|---|---:|---:|---:|---|
| **Current dotfiles legacy plan**: plan 11,302 B/210 lines; progress 17,255 B/313 lines | **3,937 B visible; 4,105 B wire** | **1,519 B visible; 1,629 B wire** | **120 B visible; 141 B wire** | first 50/30 lines and last 20 progress lines are the selected inputs (`scripts/inject-plan.sh:1003-1025,1174-1228`); hook routing is `hooks/claude-hook.sh:93-111` |
| Current SessionStart on startup/resume/clear/compact | **3,937 B visible; 4,101 B wire** | n/a | n/a | SessionStart composes no-history catchup with userprompt injection (`hooks/claude-hook.sh:60-83`) |
| Stock 46-line/913 B plan + 18-line/300 B progress fixture | **2,141 B visible; 2,299 B wire** | **944 B visible; 1,054 B wire** | **120 B visible; 141 B wire** | default file bodies are created at `scripts/init-session.sh:186-282`; dispatcher at `hooks/claude-hook.sh:37-46,100-110` |
| Autonomous fixture, same 913 B plan, empty ledger | **2,040 B visible; 2,186 B wire** | **0 B visible; 0 B wire** | **120 B visible; 141 B wire** | autonomous/gated suppress pretool at `scripts/inject-plan.sh:826-847` and synthesize ledger context at `scripts/inject-plan.sh:1192-1215` |
| Gated + `inject-smart`, same plan | **1,483 B visible; 1,600 B wire** | **0 B visible; 0 B wire** | **120 B visible; 141 B wire** | smart selection is `scripts/inject-plan.sh:849-925`; mode still suppresses pretool at `scripts/inject-plan.sh:840-847` |
| Byte-cap fixture: 70,001 B one-line plan + 40,001 B one-line progress | **99,234 B visible; 99,328 B wire** | **65,875 B visible; 65,955 B wire** | **120 B visible; 141 B wire** | exact 65,536 B plan and 32,768 B progress caps are `scripts/inject-plan.sh:1010-1023,1176-1227` |

For the live plan, the frames themselves reported a 1,859 B plan view and 1,150 B progress view at turn start, and a 1,181 B plan view before tools, all `truncated=true`. Thus the current routine-turn equation is exactly `3,937 + 1,519*m + 120*w` visible PWF bytes, where `m` is the number of six matched tool calls and `w` is the Write/Edit/Bash subset (`scripts/inject-plan.sh:1174-1228`; `hooks/hooks.json:36-67`).

### How payload growth and truncation actually work

- Legacy turn start grows with the bytes in **the first 50 plan lines** and **the last 20 progress lines**, not with the entire files. The plan view caps at 65,536 B and the progress view at 32,768 B. Bytes added after plan line 50 or before the final 20 progress lines add zero injection bytes; enlarging a selected line grows the payload until the byte cap (`scripts/inject-plan.sh:1176-1189,1217-1227`).
- Legacy pretool grows with the first 30 plan lines, up to 65,536 B, and carries no progress (`scripts/inject-plan.sh:1003-1025`).
- `truncated=true` is set for semantic line truncation even when the byte view is small: plan >50 lines at turn start, plan >30 lines at pretool, or progress >20 lines. Byte truncation independently sets the same flag (`scripts/inject-plan.sh:949-962,1012-1020,1178-1186,1219-1224`).
- Smart mode selects title, Goal/Next Step/Current Phase, phase count, the complete first `in_progress` phase, and three decision rows. It therefore grows with those selected sections even if they occur after line 50, still stopping at 65,536 B. A large active phase can consume the full cap (`scripts/inject-plan.sh:849-925,1176-1189`).
- Before view truncation, the source snapshot has a separate hard ceiling: plan >4 MiB, progress >1 MiB, any ledger >262,144 B, or more than 32 ledger files makes that hook fire return no payload (`scripts/inject-plan.sh:803-810,1041-1075`).

The plugin therefore bounds its own injection, but its 99,234 B worst measured turn-start payload is not a guarantee of staying below 20% of any model context. It has no context-window measurement or token-budget gate in this path (`scripts/inject-plan.sh:927-962,1174-1233`).

## Q2 — Can the planning files be tracked in Git?

### Verdict: yes for durable content; do not indiscriminately track runtime state

Today the dotfiles repo ignores root `task_plan.md`, `findings.md`, `progress.md`, `.planning/`, and `.active_plan` (`.gitignore:89-99`). The plugin's own repository also ignores its development planning files and `.planning`/`.plan-attestation`, which shows the maintainer's working practice, but this is not a runtime precondition (`PWF/.gitignore:12-17,43-45`). Runtime code resolves, reads, hashes, and writes ordinary paths without asking Git whether they are tracked (`scripts/resolve-plan-dir.sh:207-268`; `scripts/inject-plan.sh:224-270,449-473`).

**What tracking improves.** A fresh clone containing a valid root plan, or a scoped plan plus valid `.planning/.active_plan`, is immediately resolvable once the plugin/hooks are installed. SessionStart injects it without transcript history, so goals/status/findings survive machine loss and can be reviewed alongside code (`hooks/claude-hook.sh:60-83`; `scripts/session-catchup.py:669-676`). Planning files alone are inert without an installed/active plugin; whether this repo's `enabledPlugins` setting auto-installs the plugin on a brand-new machine cannot be determined from the plugin code. A tracked attestation works when its stored SHA exactly matches the checked-out working-tree plan bytes (`scripts/attest-plan.sh:40-61,186-202`; `scripts/inject-plan.sh:964-991`).

**What tracking can break or confuse.** The safe unit is not “all of `.planning/`”:

| Artifact | Track? | Concrete consequence | Evidence |
|---|---|---|---|
| `task_plan.md`, `findings.md`, `progress.md` (or scoped equivalents) | **Yes** | Durable/reviewable. Ordinary concurrent edits receive ordinary Git textual merges; the plugin provides no semantic merge driver. Same phase/status/log hunks may conflict or auto-merge incorrectly. | files are direct working memory (`skills/planning-with-files/SKILL.md:96-103`); phase updates are text rewrites (`scripts/phase-status.sh:146-190`) |
| `.planning/<id>/.mode` | **Usually yes** if the team wants one shared mode | Carries autonomous/gated/smart behavior to clones. It is not covered by plan attestation, so changing it changes control behavior without a hash warning. | mode is plain token-grep input (`scripts/inject-plan.sh:826-864`; `scripts/check-complete.sh:134-140`) |
| `.attestation` / root `.plan-attestation` | **Only atomically with the exact plan** | A clone works if bytes match. Any merge, EOL conversion, or post-attestation plan edit produces a mismatch and blocks injection until re-attested. It cannot distinguish a legitimate collaborator edit from hostile tampering. | exact SHA comparison (`scripts/inject-plan.sh:964-1038`); attestation hashes the working file (`scripts/attest-plan.sh:51-60,107-108`) |
| `.planning/.active_plan` | **Prefer not** | It is one repository-wide last-writer pointer. Every named init overwrites it; two branches/worktrees choosing different plans contend on the same line, and merging a stale pointer can silently select another plan or fall through to newest-by-mtime. | overwrite at init (`scripts/init-session.sh:350-374`); pointer then mtime fallback (`scripts/resolve-plan-dir.sh:218-268`) |
| `ledger-<agent>.jsonl` | **Optional audit data, with discipline** | Unique agent filenames reduce overlap, but the same ledger path is append-contention and normal Git merge territory. Tick allocation is serialized only by an optional advisory `flock`; without it, or after its 5-second timeout, appends proceed unsynchronized. | per-agent files/global tick (`scripts/ledger-append.sh:27-33,180-197`); append/lock path (`scripts/ledger-append.sh:310-333`) |
| `.stop_blocks`, `.gate_last_ledger` | **No** | A fresh clone can inherit a reached cap or a ledger watermark equal to current line count, causing the gate to allow stop immediately as capped/stalled. These are reset only by init, not clone/startup. | init reset (`scripts/init-session.sh:151-173`); Stop reads persisted values (`scripts/check-complete.sh:183-215`) |
| `.planning/sessions/*.attached` | **No** | On a different absolute clone path/session ID the copied sentinel generally does not attach the new session; the presence of the directory arms isolation, producing a turn-level warning and no injection, while pretool stays silent. | digest binds canonical project + session ID (`scripts/inject-plan.sh:99-114,274-388`) |
| `.pwf-locks/`, `.ledger_lock`, `.attestation.lock` | **No** | They are process-local coordination. A committed stale phase lock has no owner-liveness recovery and makes `phase-status` wait then time out. | phase lock acquire/timeout (`scripts/phase-status.sh:80-125`); transient ledger lock (`scripts/ledger-append.sh:321-330`) |
| `.nonce` | **No current functional need** | `init-session` writes it, but `inject-plan` only assigns `NONCE_FILE`; framing derives its 24-hex nonce from payload content instead. Tracking `.nonce` neither preserves nor breaks current injection. | writer (`scripts/init-session.sh:133-173`); unused assignments (`scripts/inject-plan.sh:449-463`); actual nonce derivation (`scripts/inject-plan.sh:927-946`) |

Two people or two worktrees get no distributed locking. Different scoped IDs generally add different directories cleanly, but both initializers still edit `.active_plan`; two clones choosing the same date/name can independently create the same unsuffixed slug because collision detection sees only local directories, leading to add/add or content conflicts later (`scripts/init-session.sh:350-370`). Separate worktrees isolate live files, so hooks do not share state in real time; Git only reconciles their later commits. Append-at-EOF progress/shared-ledger changes may conflict; different agent ledger filenames avoid file collision, but branch-local max-tick scans can produce duplicate ticks (`scripts/ledger-append.sh:180-197,310-333`).

If task-plan branches merge, each branch's one-line attestation describes its own pre-merge bytes. The sidecar may itself conflict, or the surviving hash fails against merged bytes; re-attestation is required after either a textual conflict resolution or an automatic content merge (`scripts/attest-plan.sh:147-197`). The plugin contains no Git-aware reconciliation path.

The default regression guard does not solve Git/worktree concurrency. It is read-side, advisory, and detects only decreases in checked items/completed phases; equal-count lost prose, decisions, or a clobbered edit remain silent (`scripts/inject-plan.sh:1092-1112,1151-1170`). Its baseline is in a user cache keyed by absolute plan path, so it does not travel with Git and starts fresh in another clone (`scripts/inject-plan.sh:1133-1156`).

## Q3 — Real failure modes

### Gated mode and the Stop oracle

| Failure | Actual behavior | Loud or silent? Would the operator notice? | Evidence |
|---|---|---|---|
| Plan changed after attestation to say all phases complete | Injection refuses the plan, but Stop counts the changed text, emits `ALL PHASES COMPLETE`, and allows stop. This was reproduced in the isolated control. | **Wrong result; no attestation warning at Stop.** The operator may see the all-complete advisory and believe it. | Stop calls only check-complete (`scripts/gate-stop.sh:19-32`); phase counting/decision has no hash check (`scripts/check-complete.sh:50-109,132-252`); injection separately checks SHA (`scripts/inject-plan.sh:964-1038`) |
| Gated plan has no ledger append after first block | First Stop blocks. Second Stop sees unchanged line count and allows stop as stalled. This was reproduced: block 1/20, then `no progress since last gate block — allowing stop.` | **Visible**, but much weaker persistence than “finish the plan”: absent explicit ledger use, it forces at most one continuation. | stall logic (`scripts/check-complete.sh:171-215`); hooks never append a ledger (`hooks/claude-hook.sh:93-127`) |
| Incomplete plan has only `pending`, no `in_progress`, or zero `### Phase` headings | Gate allows stop; zero-phase case emits nothing at all. | Pending case is advisory; zero-phase case is **silent**. | zero-phase exit (`scripts/check-complete.sh:104-109`); in-progress guard (`scripts/check-complete.sh:164-169`) |
| Block counter reaches cap, ledger line count equals the watermark, or ledger line count decreases | Gate allows stop at cap/equality; a decrease is treated as advancement because the check tests only equality. | Cap/equality are **visible** advisories; decrease wrongly passes as progress with no warning. | `scripts/check-complete.sh:183-215` |
| Writes to `.stop_blocks` or `.gate_last_ledger` fail | Errors are ignored. Counter/watermark can remain stale, so future block/cap/stall behavior is wrong; an unwritable fresh state can repeatedly look like block 1. | Usually **silent** because redirects suppress errors and `|| true`. | `scripts/check-complete.sh:247-252`; wrapper also suppresses stderr and converts failure to no block (`hooks/claude-hook.sh:117-126`) |
| Any gate script is absent/errors | Dispatcher exits 0 and Stop proceeds. | **Silent allow**. | `scripts/gate-stop.sh:21-32`; `hooks/claude-hook.sh:117-126` |

The gate's “progress” oracle is raw line count, not a parsed successful progress event. Any extra line, including malformed data, advances it; conversely real work with no ledger append looks stalled (`scripts/check-complete.sh:171-180,194-215`).

### Ledger

- Ledger writes are model/operator-invoked, not lifecycle-hook writes. The hook configuration contains no `ledger-append` call, so autonomous/gated mode can display an empty synthesized ledger indefinitely unless the operating procedure explicitly appends events (`hooks/hooks.json:4-99`; `scripts/ledger-append.sh:14-33`).
- The append path uses `flock -w 5 || true`; timeout deliberately continues without owning the lock. On platforms without `flock`, it always performs an unlocked read-max/increment/append. Concurrent writers can choose duplicate ticks, with no warning (`scripts/ledger-append.sh:180-197,310-333`).
- Append errors can be masked: the append function attempts the redirected JSON write and then prints the tick; with no `set -e`, that final successful print can make the script exit 0. A control in an unwritable fixture emitted `[ledger] tick 1 -> ./ledger-main.jsonl...` with `Permission denied` on stderr and created no ledger (`scripts/ledger-append.sh:35,310-337`).
- If resolution fails, `ledger-append` unconditionally falls back to `.`, even if no root plan exists, so it can write a plausible ledger beside the wrong/no plan (`scripts/ledger-append.sh:47-59,277-279`).
- Ledger summary does not parse JSON. It counts lines containing `"tick"` and regexes only the final line's event; malformed content can count as an entry or report `none` without declaring the ledger corrupt (`scripts/ledger-summary.sh:134-159`). Its phase fallback also differs from the Stop oracle: it uses inline statuses only when both primary complete and in-progress counts are zero, while Stop takes a per-status maximum, so mixed-format plans can display different completion state (`scripts/ledger-summary.sh:83-103`; `scripts/check-complete.sh:77-96`).
- Injection silently drops the entire userprompt payload if there are more than 32 ledger files, any ledger name is invalid, any ledger is a link/outside root, or any file exceeds 262,144 B (`scripts/inject-plan.sh:1056-1085`).

### Attestation

- Autonomous/gated init swallows any `attest-plan` failure with `|| true`, then prints a mode line that says `(attested, gate counter reset)` solely because mode is nonempty. Initialization can therefore claim success without an attestation; later injection emits the one-line `requires attested plan` refusal (`scripts/init-session.sh:175-183,350-387`; `scripts/inject-plan.sh:978-1031`).
- A normal hash mismatch is loud and blocks plan injection, which the operator will notice on a user prompt (`scripts/inject-plan.sh:964-1038`). An attestation symlink, oversized >128 B attestation, unavailable Python snapshot helper, unwritable snapshot cache, >4 MiB plan, or >1 MiB progress takes an earlier `exit 0` path and can make hooks simply emit nothing (`scripts/inject-plan.sh:474-519,803-823,1041-1053`).
- Attestation covers only `task_plan.md`. It does not bind `.mode`, `.active_plan`, progress, ledger, or the Stop oracle; legitimate phase edits also require re-attestation (`scripts/attest-plan.sh:24-49,51-60`; `scripts/phase-status.sh:4-12`).
- PostToolUse tells the agent to update `task_plan.md`, but does not tell it to re-attest. In v3, following that reminder makes the next injection report tampering until the model/operator separately runs attestation (`hooks/claude-hook.sh:106-110`; `scripts/inject-plan.sh:1028-1038`).

### Plan resolution and the shared active pointer

- Resolution order is `PLAN_ID`, `.active_plan`, newest directory mtime, then caller-specific root fallback. An invalid/nonexistent `PLAN_ID` does **not** fail closed; it silently falls through. A stale/invalid `.active_plan` also silently falls through to newest (`scripts/resolve-plan-dir.sh:207-268`).
- Newest selection compares directory mtimes with `>` and supplies no ambiguity warning. Equal mtimes retain the first glob candidate; otherwise an incidental directory mtime decides which plan is injected (`scripts/resolve-plan-dir.sh:236-263`).
- Named init always overwrites the shared `.planning/.active_plan` and only prints a suggestion to export `PLAN_ID`. Two terminals that do not actually pin it both switch to the most recently initialized/selected plan, silently defeating isolation (`scripts/init-session.sh:350-374`; `scripts/resolve-plan-dir.sh:265-268`).
- An invalid `PWF_PLAN_ROOT` is inconsistent across callers. Injection prints a turn-level refusal and exits, but `resolve-plan-dir` silently returns empty; `attest-plan`, `phase-status`, and ledger append can then use their own root fallbacks and operate on a different root plan (`scripts/inject-plan.sh:65-90`; `scripts/resolve-plan-dir.sh:20-45`; `scripts/attest-plan.sh:24-37`; `scripts/phase-status.sh:34-47`; `scripts/ledger-append.sh:47-59`).
- Nested-root ambiguity detection sees direct children only. At depth one it visibly refuses on userprompt but stays silent on pretool; a competing plan two levels down is intentionally undetected and can receive the parent's context (`scripts/inject-plan.sh:392-440`).
- Most hook/resolve failures are designed to exit 0, and the Claude dispatcher suppresses `inject-plan` stderr and drops failed/empty output. Silence therefore means either “no plan” or “mechanism failed” unless the operator manually runs diagnostics (`scripts/inject-plan.sh:26-27`; `hooks/claude-hook.sh:37-46`).

`plan-doctor` is not a reliable health gate: it always exits 0, only tests attestation presence rather than validity, and its invalid-root matcher looks for `PWF_PLAN_ROOT is not a directory`, while injection actually says `PWF_PLAN_ROOT is not a supported absolute local directory` (`scripts/plan-doctor.sh:17-18,66-116,147-148`; `scripts/inject-plan.sh:78-89`). A control with a definitely missing root exited 0 and printed `PASS resolver: legacy root plan` plus `PASS injection: emits plan context (143 bytes)`; those 143 bytes were the refusal, not plan context, because the unmatched message falls into doctor's generic nonempty-output PASS branch (`scripts/plan-doctor.sh:92-98`).

### Session catchup

- Automatic SessionStart deliberately calls `--no-history`, and that mode returns before detecting stores. It never repairs state that was not already written to plan/progress/findings (`hooks/claude-hook.sh:65-80`; `scripts/session-catchup.py:669-676`).
- Explicit `--metadata`/`--replay` is best-effort. Missing stores, fewer than two sessions, no previous planning write, no later messages, JSON parse errors, and many I/O exceptions return no output. Metadata users often cannot distinguish “nothing unsynced” from a scanner failure (`scripts/session-catchup.py:141-166,312-353,356-437,684-742`).
- Claude session identity assumes the most recently modified JSONL is the current session and skips it. With concurrent sessions, mtime ordering can identify the wrong file as current and replay/omit the wrong interval (`scripts/session-catchup.py:141-145,698-735`).
- CWD identity is searched only in the first 50 JSONL lines. Missing/late identity quarantines that transcript; the quarantine notice is printed only in replay mode, so metadata may return silently after filtering (`scripts/session-catchup.py:148-166,226-274,690-696`).
- IDE detection prefers Claude whenever `~/.claude` exists unless `OPENCODE_DATA_DIR` is set. A machine using OpenCode but also containing `.claude` can scan the wrong store and silently find nothing (`scripts/session-catchup.py:30-49,678-688`).
- Replay caps each framed excerpt, and displays at most 100 messages/parts, but there is no one global byte cap over the whole report; up to 100 separately framed records can still be substantial context. Automatic recovery does not invoke replay (`scripts/session-catchup.py:184-203,641-660,744-777`).

## Fit assessment

**Classification: not as-is; usable with configuration plus an explicit/manual or external task-rotation protocol.** The plugin is a useful durable state layer, and its autonomous/smart configuration materially lowers recitation. It does not itself deliver “create small granular tasks, execute each in a small/fresh context, and stay below 20%.” There is no task-size check, tokenizer/context meter, automatic `/clear`, fresh-session launcher, or per-task handoff constructor in the lifecycle path (`hooks/hooks.json:4-99`; `templates/task_plan.md:11-25`).

To get the operator's workflow:

1. **Author a genuinely granular plan contract.** Make each phase/task contain only inputs, expected output, verification, and a one-line handoff/next step. The stock template's broad phases are organizational scaffolding, not context-bounded work packets (`scripts/init-session.sh:186-234`).
2. **Use a named scoped plan and pin every worker/session.** Export both `PWF_PLAN_ROOT=<absolute clone path>` and `PLAN_ID=<id>`; do not rely on `.active_plan` or mtime fallback (`scripts/resolve-plan-dir.sh:20-45,207-268`).
3. **Use `autonomous inject-smart` for the lowest routine recitation.** In the measured stock fixture it reduced turn-start context from 2,141 B to 1,483 B and eliminated the 944 B per-matched-tool plan copy; it still keeps the 120 B mutating-tool reminder (`scripts/inject-plan.sh:826-925`; `hooks/claude-hook.sh:100-110`). Use gated mode only after accepting its one-block/stall behavior or fixing/wrapping the Stop oracle to require a matching attestation.
4. **Rotate context externally after each task.** Before `/clear` or launching a new session, update task status, exact next step, progress, and findings; re-attest any changed plan. On resume, inject/read only the current task packet and targeted findings rather than blindly loading the whole findings file (`skills/planning-with-files/SKILL.md:117-146,173-195`; `scripts/inject-plan.sh:1231-1232`).
5. **Add an external context-budget gate.** The plugin can report its own byte frames, but only the host/model can count total tokens and enforce the operator's 20% limit (`scripts/inject-plan.sh:927-962`).
6. **Track durable content selectively.** Track plan/findings/progress and, if useful, `.mode`; track attestation only with exact plan bytes. Exclude `.active_plan`, `sessions/`, `.stop_blocks`, `.gate_last_ledger`, locks, and `.nonce`. If ledger audit history is tracked, use unique agent IDs and keep below the 32-file/262,144-B-per-file injection limits (`scripts/inject-plan.sh:1056-1075`; `scripts/ledger-append.sh:23-33`).
7. **Make ledger writes explicit if using the gate.** Append a validated progress/phase event after each continuation and verify the file exists; do not trust `ledger-append` stdout alone (`scripts/ledger-append.sh:215-337`; `scripts/check-complete.sh:171-215`).

With those controls, PWF can be the disk-backed handoff layer for small-context execution. The fresh-context scheduling, 20% budget enforcement, and attestation-aware termination decision remain outside the plugin and must be supplied by the operator's wrapper/orchestrator.

## GitHub repos touched

> Added by the architect at persistence time, not by the reporting lane. The
> lane did not emit this section; the entries below are the repositories its
> cited evidence demonstrably came from.

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the tree under audit.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — the plugin whose scripts, hooks and templates the lane read.
