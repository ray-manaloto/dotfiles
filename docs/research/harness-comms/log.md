# Directory Update Log

## 2026-11-07
* **Creation**: source maps of Claude Code 2.1.319 (binary extract) and Codex 0.167.0 (`rust-v0.167.0`), merged
  with three live runs: P1 (a client and a `--remote` TUI on one Codex thread), C1 (a Codex-side poster to a Claude
  inbox socket) and C2 (one Claude tab messaging another with SendMessage). Read only: no setting, plugin or config
  changed.
* **Addition**: `dead-tab-fallthrough.md`, from a C2 finding raised again by a side agent: a closed tab's name resolves
  to its Remote Control copy. Source shows no "prefer local" rule and a `uds:` address that cannot fall through.
* **Corrected**: earlier notes assumed a `codex mcp-server` with `codex`/`codex-reply` tools; 0.167.0 has none. The
  "5-minute hold for bypass" is the default approval-dialog timeout for mode-mismatch holds, not a bypass rule. The
  thread-resume subscribe code is at `request_processors/thread_lifecycle.rs:1166-1190`, not `:1176-1184`.
* **Rejected**: `codex exec` for agent steps (owner rule, and it runs its own in-process app-server, not the shared
  one); the Codex agent message board (under development, off, host-provisioned); Channels as a default path (needs
  `--dangerously-load-development-channels` or an allowlist).
* **Addition**: `approval-fanout.md`, from a side agent's note that a client joined to a Codex thread also receives its
  approval requests. Source confirms it for every request except `humanCommand` approvals and user-verification ceremonies (one owner, deleted on its disconnect, never replayed), and shows two things the
  note did not cover: a JSON-RPC error reply is acted on (command denied, empty permission grant, elicitation
  declined), and `turn/start` approval and sandbox overrides persist on the thread. The rules for the client are added
  to proposals A and C.
* **Corrected**: `codex-codex.md` said only "approval requests go to all subscribers"; it now names the request kinds
  and the error-reply rule.
* **Corrected (rev 3, review round 1):** an independent read-only Codex review raised 27 findings. Each one was
  checked against the source and all were confirmed. The main changes:
  - **Approvals:** the A/C client now has a strict method and field allowlist. `thread/resume` overrides do apply
    when an idle, unsubscribed loaded thread is rebuilt. A `humanCommand` approval with no eligible TUI ends as a
    denial and is not replayed. Verification callbacks are dropped on disconnect.
  - **Turns:** `turn/start` on a busy thread steers the owner's turn, so A needs a reserved thread and
    `clientUserMessageId` correlation. `turn/completed` has `items: []` on failed and interrupted turns, and a
    rollout ends in `task_complete` or `turn_aborted` (named `TurnAborted` here until rev 4). A Stop hook run is not terminal (a blocking handler continues
    the turn), so E needs a delivery contract.
  - **Claude identity and delivery:** Claude does not bind identity. It accepts an omitted `session_id`, and
    neither name nor `uds:` sends check the pid or start time. The rebound guard covers subagents only. A released
    hold sends a positive `delivered` notice.
  - **Claude details:**
    - Cloud events go to `/v1/sessions/<id>/events` (or `/v1/code/...`), and the one-way warning applies to Remote
      Control only conditionally.
    - Queue, buffer and drain limits are restated.
    - The timed dialog applies only to some holds.
    - Daemon exclusions, notification filters, socket-directory modes and the P1 transport are corrected.
  - **Plan rev 3:** d1, d2 and d4 are reworded around these gaps. t10 now comes before d5, and tests t11-t16 are
    added as not run.
* **Addition (rev 3, side-agent note):** the `turn/start` response is the same for a new turn and a steer
  (turn_processor.rs:717-767), so a client cannot detect afterwards that it steered. A reviewer the owner also types
  into is not a reserved thread (d1).
* **Corrected (rev 4, review round 2):** a second read-only Codex review raised 22 findings (0 blockers, 6 majors).
  Each was checked against the source. The main changes:
  - **A never interrupts.** `turn/interrupt` is off the allowlist: an empty `turnId` is a startup interrupt that
    skips the active-turn checks (turn_processor.rs:1475-1513).
  - **D needs an explicit final-reply marker.** Dequeue records carry no content (JS:L151308, L151491,
    L151515-151521), and C1 saw `idle` after a partial reply and Esc. The receiver ends its reply with
    `REPLY-END <nonce>`; no marker means `interrupted` or `unknown`.
  - **E is a `turn/completed` watcher, not a Stop hook.** A hook cannot see whether another Stop handler blocks.
  - **Names:** the rollout event is `turn_aborted` (serialized), not `TurnAborted`.
  - **Gates are passes, not runs:** A on t10, t11, t13 and t15; C on t13 and t14; D on t12; E on t16.
  - **Claude notices are best-effort** (eviction, dropped receipts, logged send failures, expiring subscriptions).
    Stock `SendMessage` has no `session_id` field, so only a raw client binds the session.
  - Smaller fixes: separate-turn and fallthrough observations scoped to C2, per-action control checks, a postponable
    hold timeout, cold-rebuild conditions, a second daemon exclusion, the verification-ceremony exception to fan-out,
    `experimentalApi` hiding only experimental notifications, and `codex queue` not dispatching after an interrupt.
  - **Plan rev 4:** tests t17-t24 added as not run.
- **2026-11-07, rev 5 (side-agent note on the reviewer setting).** t10 runs with `approvals_reviewer = "user"`, and the
  owner's config uses `auto_review` with `approval_policy = "never"`. From source: `never` rejects escalation with no
  prompt and no auto-review; `on-request` with `auto_review` lets the auto-reviewer decide and joined clients see only
  `item/autoApprovalReview/*` notices; only `on-request` with `user` fans requests out. Added the "Who answers" table
  to approval-fanout.md, named `thread/approveGuardianDeniedAction` and `thread/shellCommand` as forbidden, scoped t10
  to reviewer `user`, and added t25 (auto_review), t26 (owner config) and decision d8. t10 part 1 recorded.
- **2026-11-07, t10 passed.** Part 2 used watch-only clients that resume the thread and nothing else. Five clients
  joined one after another, and the pending approval was replayed to each. It stayed pending until the owner
  answered in the TUI. Then the client got `serverRequest/resolved` and `turn/completed` (status `completed`).
  Plan rev 6 marks t10 pass.
- **2026-11-07, d8 and t26.** The owner chose their own config (`never` + `auto_review`) for reviewers and workers.
  t26 passed in both cases: reviewer read-only and worker full access. No approval request or auto-review notice
  reached the client. Plan rev 8.

## 2026-11-07, auto_review is inert under never

- Checked at rust-v0.167.0: the auto-reviewer runs only for `on-request` or `granular` (routing.rs:58-66).
  `strict_auto_review` comes only from a permissions answer, which `never` rejects, and this machine has no managed
  requirements file. So on the owner's config, worker threads (danger-full-access) get no review: only the built-in dangerous-command list (forced `rm`, also behind
  `sudo`, `env` or `trap`) is forbidden, and everything else runs.
  t26 (b) showed it live.
- approval-fanout.md and claude-codex.md now say so. d8 is reopened for workers; t25 is the candidate test again.

## 2026-11-07, d8 grill and t25

- Owner answers: workers go to on-request + `auto_review` with full access, set in the global config after t25 and the
  owner's OK. Reviewers launch with `-a never -s read-only`, and the client does not check the sandbox. Workers always
  get a visible tab, so proposal C is out for workers. The auto-reviewer may allow a forced `rm`, also behind `sudo`.
- t25 passed live (see approval-fanout.md, Not established).
- GLOSSARY.md gains Reviewer and Auto-reviewer.

## 2026-11-07, whose words the auto-reviewer trusts

- From the guardian policy at rust-v0.167.0 (prompts/templates/guardian/policy_template.md:6-9, 66-77), a client's
  `turn/start` text is a trusted user message. Low and medium risk run whatever the authorization, and high risk runs
  once authorization is medium. In t25 the test prompt was scored `userAuthorization: high`.
- So for workers the auto-reviewer stops scope drift and planted commands, not a bad instruction from Claude.
  approval-fanout.md has the section "Whose words authorize a command".
- The worktree was removed by a cleanup pass at 10:44 and restored from its saved copy onto main 0940dfa.

## 2026-11-07, grill on Claude's instructions

- Owner answers: keep d8, with its limit written down. `prompt-user` rules are the check on a bad instruction from
  Claude. The list covers history rewrites, cleanup and GitHub writes. The rules live in a tracked file linked into
  `~/.codex/rules/`. They go live with the on-request switch, after t27.
- GLOSSARY.md: the Auto-reviewer judges a command against the session's user messages, whoever sent them.
- Open: rules match leading words only, so reordered flags slip past.
- Correction: `prompt-user` is accepted only in a managed requirements file such as `/etc/codex/requirements.toml`
  (config/src/requirements_exec_policy.rs:20-49). A `~/.codex/rules/*.rules` file takes only allow, prompt and forbidden
  (execpolicy/src/decision.rs:22-29), and `prompt` goes to the auto-reviewer. The rules' home is open again.
- Owner answer: the rules go in `/etc/codex/requirements.toml`, from a tracked source, installed by the owner with sudo.
- Owner answer: rules list the common flag spellings; reordered and `git -C` forms are an accepted gap (rule.rs:23-26).

## 2026-11-07, reviewer corrections before commit

- `sudo` is not on the dangerous-command list: for `sudo <cmd>` Codex checks `<cmd>` (is_dangerous_command.rs:146-149).
  Fixed in approval-fanout.md, claude-codex.md and the entries above.
- The auto-reviewer allows low- and medium-risk actions whatever the authorization (policy_template.md:70-77), so it is
  not a scope check. Plain `git push` never reaches it on a full-access worker under on-request (exec_policy.rs:859-863).
- `prompt-user` is rejected under `never`, under a granular policy that disables rule approvals
  (exec_policy.rs:220-231), under strict auto-review, and under requirements that forbid reviewer `user` or require
  auto-review (approvals.rs:530-539); not merely because a requirements file exists.
- critique.md and codex-codex.md now record t10's pass and E as a `turn/completed` watcher.
- codex-codex.md's fan-out row now separates the live t10 result from the untested cases, and critique.md item 9
  records round 2.
