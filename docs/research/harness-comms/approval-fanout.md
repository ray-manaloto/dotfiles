---
okf_version: "0.2"
type: "report"
title: "Approval fan-out to a joined client"
description: "Why a client that joins a Codex thread also receives its approval requests, who answers under each policy, and which rules keep the client from answering."
---

# Approval fan-out to a joined client

A client that joins a Codex thread through the app-server receives that thread's approval requests ("may I run this
command?"), as the visible TUI does. The first answer from an eligible connection wins, and **an error reply counts
as an answer** (see below). Proposals A and C in [Claude <-> Codex](claude-codex.md) put such a client on the
reviewer's thread, so the client must never answer. This page is from Codex `rust-v0.167.0` (`086ccc833b`), read with
`git show`. t10 (reviewer `user`) and t26 (owner config, `never`) have run live and passed (see Not established).

## What reaches the client

| Claim | Where | Tag |
|---|---|---|
| A thread's server requests go to every subscribed connection; a connection that resumes the thread later gets the stored pending ones replayed (not user-verification ceremonies, outgoing_message.rs:695-697; not a `humanCommand` unless it declared `requiredHumanApproval`, 536-540). | app-server/src/outgoing_message.rs:183-194, 388-523, 525-560; request_processors/thread_lifecycle.rs:1283-1287 | VS |
| The thread requests are: command approval `item/commandExecution/requestApproval`, file change `item/fileChange/requestApproval`, permissions `item/permissions/requestApproval`, user input `item/tool/requestUserInput`, MCP elicitation `mcpServer/elicitation/request`, and the client-run tool `item/tool/call`, plus the deprecated `applyPatchApproval` / `execCommandApproval`. | app-server-protocol/src/protocol/common.rs:1850-1920 | VS |
| Only one kind is held back: a command approval of kind `humanCommand` (a managed checkpoint that "requires a fresh human decision") goes only to connections that declared `requiredHumanApproval`, and is not sent at all if none did: it is then not stored either, and the request ends as a denial (outgoing_message.rs:425-427). Ordinary `command` and `writeStdin` approvals go to everyone. | outgoing_message.rs:416-430, 1029-1032; v2/item.rs:1644-1652; protocol/src/approvals.rs:274-281; core/src/tools/approvals.rs:799-807 | VS |
| A user-verification elicitation goes to one owning connection only. | outgoing_message.rs:397-466 | VS |
| `requiredHumanApproval` is honoured only together with `experimentalApi`; the visible TUI declares both. | request_processors/initialize_processor.rs:144-148; tui/src/lib.rs:523, 739 | VS |

## Who answers: the thread's policy and reviewer

Fan-out happens only when the approval goes to a person. Two settings pick who answers (core/src/tools/approvals.rs
681-699; ext/guardian-reviewer/src/routing.rs:58-66, 139-150; core/src/exec_policy.rs:220-226):

| `approval_policy` | `approvals_reviewer` | An escalated command | What a joined client sees |
|---|---|---|---|
| `never` | any | rejected at once, no prompt, the auto-reviewer is not asked | no server request |
| `on-request` / `granular` | `user` | prompted | `item/commandExecution/requestApproval` on every subscriber (this page) |
| `on-request` / `granular` | `auto_review` | the auto-reviewer decides | `item/autoApprovalReview/started` and `completed` notices (common.rs:2046-2047), no request |

Exceptions to the last row: a `humanCommand` checkpoint always goes to a person (approvals.rs:686-687), and a
reviewer extension that answers "ask the user" when review is not required falls back to the prompt (routing.rs:139).
`untrusted` is retired in 0.167.0: a config that sets it makes the app-server exit
(core/src/config/mod.rs:232-235).

The owner's config sets `approval_policy = "never"` with `approvals_reviewer = "auto_review"`. Under `never` the
`auto_review` setting does nothing: the auto-reviewer runs only when the policy is `on-request` or `granular`
(routing.rs:58-66). Two other paths reach it, and neither applies under `never`:
- `strict_auto_review` comes only from a client's answer to a permissions request (bespoke_event_handling.rs:1982-2001),
  and `never` rejects that request before anyone is asked.
- Managed requirements can force a review (core/src/guardian/decision.rs:104-110), but the owner's machine has no
  requirements file (`/etc/codex`, `~/.codex/requirements.toml`).

So with this config:
- **Reviewer threads (read-only):** nothing escalates, and a write fails in the sandbox.
- **Worker threads (danger-full-access):** no person and no auto-reviewer checks any command. t26 (b) showed this
  live. The only check left is Codex's built-in dangerous-command list. It matches `rm` with a force flag, also behind `sudo`,
  `env` or `trap`; `sudo` itself is not on it, since for `sudo <cmd>` it checks `<cmd>`
  (shell-command/src/command_safety/is_dangerous_command.rs:132-160, 146-149). Under `never`
  a match is forbidden outright (exec_policy.rs:836-844), and every other command runs (exec_policy.rs:847-851). So
  `git push --force`, `git reset --hard` or a network download all run unchecked.

t10 runs on-request with reviewer `user` on purpose, so it covers only the middle row. The auto-review row is t25, and
the owner's setup is t26. Decision d8 picks which one real threads use.

A client can also override the auto-reviewer: `thread/approveGuardianDeniedAction` (common.rs:766-770) injects the
denied action back into the thread as "allowed" (core/src/session/handlers.rs:788-812). It is not on the allowlist
below and is named there as forbidden.

### Whose words authorize a command

The auto-reviewer treats only user and developer messages, `AGENTS.md` files and `request_user_input` answers as
trusted. Everything else, tool output and assistant text included, is untrusted evidence
(prompts/templates/guardian/policy_template.md:6-9). A message a client sends with `turn/start`, or that `hc send`
types into the TUI, is a user message. Nothing marks it as coming from another agent: `turnTrigger` is a free-form tag
for analytics (app-server-protocol/src/protocol/v2/turn.rs:183-186) and nothing under `core/src/guardian` reads a
client's value. Codex's own task messages between threads are different: the reviewer gets the sending thread's user
messages, labelled "not a transfer of permission" (core/src/agent/control/sender_context.rs:1-4,
core/src/context/guardian_sender_messages.rs:45). A Claude client has no such path, so on a worker thread Claude's
words count as the owner's.

The outcome rules (policy_template.md:66-77): low and medium risk run whatever the authorization, unless a policy
rule denies them or there is clear prompt injection; high risk runs when authorization is at least medium and the
action is narrow; critical is denied. t25 shows the authorization step: the test client's prompt "Run exactly this
shell command ... rm -f t25-victim.txt" was scored `userAuthorization: high`, risk low, with the rationale "The user
explicitly authorized deleting this specific local file".

So on a worker the auto-reviewer can stop a high-risk command that goes past what Claude asked for. It allows low- and
medium-risk actions whatever the authorization, unless a security-policy deny applies or there are clear signs of
malicious prompt injection (prompts/templates/guardian/policy_template.md:70-77), so it is not a scope check. It does not stop a bad instruction from Claude itself, including one that a
prompt injection into Claude's own session put there.

One Codex mechanism leaves Claude out of the decision. A rule with decision `prompt-user` makes a matching command
need a person (core/src/exec_policy.rs:428-451, execpolicy/src/decision.rs:12-16). Only a managed requirements file
can hold one: `[rules]` in `/etc/codex/requirements.toml`, a cloud bundle or managed preferences
(config/src/requirements_exec_policy.rs:20-49, config/src/loader/mod.rs:109-122, 735-736). A `.rules` file under
`~/.codex/rules/` accepts only `allow`, `prompt` and `forbidden` (execpolicy/src/decision.rs:22-29,
execpolicy/src/parser.rs:358-360), and its `prompt` goes to the configured reviewer, which is the auto-reviewer here. Such a request
skips the auto-reviewer and goes straight to the approval prompt (core/src/tools/approvals.rs:686-688). A
permission-request hook's allow cannot clear it (approvals.rs:605). Under `never` it is rejected (approvals.rs:521-527),
and so is it when strict auto-review is on, when requirements forbid reviewer `user`, or when they require
auto-review for the model (approvals.rs:530-539). Holding `[rules]` in a requirements file does not by itself reject it. A `forbidden` rule blocks
the command under every policy (exec_policy.rs:416). Rules match a command's leading words, so `git push --force`
does not match `git push origin main --force`. The owner's `~/.codex/rules/default.rules` holds five `allow` rules
and is not tracked in this repo.

Decided 2026-11-07: `prompt-user` rules are the check on Claude's own instructions to a worker. They cover history
rewrites, cleanup and GitHub writes: `git push --force`, `git push -f`, `git reset --hard`, `git clean`, `git branch -D`,
`git worktree remove`, `rm -rf`, `rm -fr`, `gh pr merge` and `gh repo delete`. `rm -f` stays with the auto-reviewer, since a forced
`rm` is on the dangerous-command list and prompts (exec_policy.rs:836-844). Plain `git push` is not on it, so on a
danger-full-access worker under on-request it runs with no review at all (exec_policy.rs:859-863). The rules live in `[rules]` of `/etc/codex/requirements.toml`, from a source tracked in this repo, and the owner
installs it with sudo. It applies to every Codex session on the machine. On a reviewer under `never` a matching
command is rejected, which is harmless for a read-only session. They go live together with the on-request switch, after live test t27 shows a matching
command reaching the person's prompt with no auto-review. Rules match leading words in order, and a pattern token is one word or a list of alternatives with no wildcard
(execpolicy/src/rule.rs:23-26). Each rule lists the common spellings (`-f`, `--force`, `--force-with-lease`; `-rf`, `-fr`,
`-Rf`). A reordered or prefixed command such as `git push origin main --force`, `git -C dir reset --hard` or `rm -r -f`
is not caught. That gap is accepted: like the repo's other gates, these rules catch mistakes, not a forger.

## What counts as an answer

The first response or error from an eligible connection removes the callback (`take_connection_callback`,
outgoing_message.rs:563-686). An **error** reply is not ignored. Each handler turns it into a decision:

| Request | On a JSON-RPC error reply | Where |
|---|---|---|
| command approval | denied "approval request failed", item `failed` | bespoke_event_handling.rs:2134-2148 |
| file change | denied "approval request failed" | bespoke_event_handling.rs:2034-2042 |
| permissions | empty grant for the turn | bespoke_event_handling.rs:1954-1970 |
| user input | empty answers submitted | bespoke_event_handling.rs:1720-1736 |
| MCP elicitation | decline | bespoke_event_handling.rs:1857-1878 |

So a JSON-RPC library that auto-replies "method not found" to requests it doesn't know would deny the reviewer's
commands before the owner sees the prompt. A reply that passes `accept` would approve them. Either breaks the rule
that agents never answer permission prompts.

## What is safe

- **Not replying.** For ordinary shared requests (command, file change, permissions, user input, MCP elicitation other
  than user verification), the request stays pending, and the TUI shows it and can answer. These requests are not tied
  to the connection that received them. `connection_closed` drops the connection from the human-approval set, removes
  its verification ceremonies and its request contexts, and leaves the callbacks of ordinary requests in place
  (outgoing_message.rs:329-338). So a client that ignores such a request, or disconnects, leaves it to the TUI.
- **Not covered: user-verification ceremonies.** They are owned by one connection. Disconnect deletes that connection's
  callbacks (`disconnect_user_verification_connection`, user_verification_auth.rs:23-34), and they are never replayed
  to a joiner (outgoing_message.rs:695-697). The proposed client never owns one (it never enables the verification
  integration), so the safe rule above is not claimed for them.
- The P1 probe client never replied to a server request (`client.py` only matches responses to its own ids), and all 5
  cases passed, but no case asked for an approval.

## A second way in: per-turn overrides

`turn/start` accepts `approvalPolicy`, `approvalsReviewer`, `sandboxPolicy` and `permissions`, each documented as
"for this turn and subsequent turns" (v2/turn.rs:240-255). P1 confirmed live that a `model` override sticks to the
thread. A client that sends any of these changes the reviewer's approval setup for every later turn, including the
owner's own.

The other start and resume methods take overrides too. `thread/start` takes `approvalPolicy`, `approvalsReviewer`,
`sandbox` (not `sandboxPolicy`), `permissions`, an arbitrary `config` map, `baseInstructions`, `developerInstructions`
and more (v2/thread.rs:88-106). `thread/resume` takes `model`, `modelProvider`, `serviceTier`, `cwd`, `approvalPolicy`,
`approvalsReviewer`, `sandbox`, `permissions`, `config`, `baseInstructions`, `developerInstructions` and `personality`
(v2/thread.rs:376-418). On resume of a loaded thread the server compares only the fields that are present with the
live settings (`collect_resume_override_mismatches`, thread_processor.rs:124-200); an empty-override resume has no
mismatch and changes no setting. On a mismatch, the thread is shut down, removed and rebuilt cold, so the overrides
apply, only if all of these hold: the thread accepts direct input (`can_accept_direct_input`, so not a parent-owned V2
child), it has no subscribers, its loaded status is exactly Idle, it is not running, and its shutdown completes
(thread_processor.rs:4704-4739). If any condition fails, or `wait_for_thread_shutdown` reports SubmitFailed or
TimedOut, the server only logs a warning ("overrides ignored for loaded thread") and rejoins the loaded thread with
its old settings (thread_processor.rs:4741-4756). So an unsubscribed idle reviewer thread can be reconfigured by a
resume; a thread that is subscribed, running, not Idle, a V2 child or slow to shut down cannot.

## Strict allowlist for the proposed client (A and C)

The client may send only these methods with only these fields. Every other field of these methods, and every other
method, is forbidden.

| Method | Fields allowed | Where | Tag |
|---|---|---|---|
| `initialize` | `clientInfo`, and `capabilities.experimentalApi: true` only. No `requiredHumanApproval`. `optOutNotificationMethods` is not sent (see rule 3). | initialize_processor.rs:80-88, 144-148 | VS |
| `thread/resume` | `threadId` only. `excludeTurns: true` is also allowed (read-only). | v2/thread.rs:354-355, 424-425 | VS |
| `turn/start` | `threadId`, `input`, `clientUserMessageId` only. | v2/turn.rs:174-182 | VS |
| `thread/read` (if needed) | `threadId`, optional `includeTurns`. | v2/thread.rs:1737-1744 | VS |

`turn/interrupt` is not on the allowlist: the client may not interrupt. The server does not authorize the caller. An
empty `turnId` is a "startup interrupt": it skips every active-turn check and submits `Op::Interrupt` to the thread
at once (turn_processor.rs:1475-1482, 1508-1512). A non-empty `turnId` is checked: if the thread has an active turn
with a different id the request fails with "expected active turn id X but found Y"; with no recorded active turn it
fails when the id equals the last terminal turn or the thread is not running (turn_processor.rs:1482-1497). That
check compares ids only, not who started the turn, and when the thread is running with no recorded active turn id the
request is accepted and interrupts. If the client ever must interrupt, it may do so only on a thread it started, with
a non-empty `turnId` that it recorded from the `item/started` of its own user message (`clientId` equal to the
`clientUserMessageId` it sent), and never with an empty `turnId`. This stays unproven until a test sends an
empty-id, a wrong-id and an other-thread interrupt.

Forbidden on every method, whatever its name: `approvalPolicy`, `approvalsReviewer`, `sandbox`, `sandboxPolicy`,
`permissions`, `config`, `baseInstructions`, `developerInstructions`, `personality`, `model`, `modelProvider`,
`serviceTier`, `serviceTierForTurn`, `effort`, `summary`, `cwd`, `runtimeWorkspaceRoots`, `environments`,
`additionalContext`, `disabledPluginIds`, `outputSchema`, `collaborationMode`, `toolOutput`, `history`, `path` and the
`responsesapiClientMetadata*` fields (v2/turn.rs:176-306, v2/thread.rs:88-114, 376-431). Every settings or config
write method is forbidden too: `thread/settings/update` (common.rs:713-718), `config/value/write` (common.rs:1514),
`config/batchWrite` (common.rs:1520) and any similar one. So are `thread/approveGuardianDeniedAction`
(common.rs:766-770), which turns an auto-review denial into an allow, and `thread/shellCommand` (common.rs:761-765). `thread/start` is not on the allowlist for A. Headless
threads (C) may add it with empty params only, since the owner's config sets the policy. A wrapper must build requests
from this allowlist and reject any other key before sending.

## Rules for the client (proposals A and C)

1. Never send a response or an error for a server request. Read frames, and drop requests after logging their method
   and id.
2. Use a hand-written reader, or a library set never to auto-reply to unknown methods.
3. `initialize` with `experimentalApi` only; never declare `requiredHumanApproval`. Do not opt out of notifications:
   `optOutNotificationMethods` and a missing `experimentalApi` both hide notifications from a connection
   (app-server/src/transport.rs:105-126).
4. Send only the methods and fields in the allowlist above. In particular never send `approvalPolicy`,
   `approvalsReviewer`, `sandbox`, `sandboxPolicy`, `permissions` or `config` on `thread/start`, `thread/resume` or
   `turn/start`.
5. Report the requests it saw (method, item id) in its result. A turn waiting on an approval then shows up as "waiting
   on the owner" instead of a silent hang.
6. Headless threads (C) have no TUI to answer. Their approval policy comes from the owner's config when the thread
   starts, never from the client. Two cases differ:
   - **Ordinary pending requests** (command, file change, permissions, user input, MCP elicitation) are stored and wait.
     A TUI that attaches later with `codex resume` / `--remote` and subscribes gets them replayed
     (outgoing_message.rs:525-560, 695-697).
   - **A `humanCommand` approval** with no eligible human connection (one that declared `requiredHumanApproval`
     and is subscribed) is never stored and never sent. The function returns early, drops the callback sender, and the
     waiting handler sees a closed channel (outgoing_message.rs:415-427; handler `Err(err)` branch,
     bespoke_event_handling.rs:2142-2147). The command is denied "approval request failed" and the item ends `failed`.
     Nothing remains to replay, and a TUI that attaches later cannot rescue it. Such a thread needs an eligible TUI
     attached before the checkpoint, or it ends as a denial.
   That is decision d4 in the plan.

## Not established

- t10 passed live on 2026-11-07, reviewer `user` only. The request reached the joined client 4.4 s into the turn. It
  stayed pending through client disconnects and about 8 hours with no answer. Each of five clients that joined later
  got it again on `thread/resume`. After the owner answered in the TUI, the client got `serverRequest/resolved
  {threadId, requestId}` and then `turn/completed` with status `completed`. The client sent no reply at any point.
  `turn.items` held only the agent message; the command came as an `item/completed` notice.
- t26 passed live on 2026-11-07 under the owner's config (`never` + `auto_review`). With a read-only sandbox, the
  model is told escalation is unavailable and the sandbox denies the write. With danger-full-access, the command just
  runs: no person and no auto-reviewer saw it. Neither case sent a server request or an `item/autoApprovalReview/*` notice to the joined client. In the
  read-only case the failed command produced no `commandExecution` item either; that is not explained.
- t25 passed live on 2026-11-07 for the worker setup chosen in d8: on-request + `auto_review` + danger-full-access.
  `rm -f` on a scratch file went to the auto-reviewer. The joined client saw `item/autoApprovalReview/started`, a
  `guardianWarning`, and `completed` with status approved and risk low. It got no server request, and the command
  ran. A plain `touch` ran with no review. A `humanCommand` checkpoint and an "ask the user" result were not
  triggered.
- Whether a request sent to a thread with no subscribers waits forever. Source suggests yes: an empty connection
  list sends nothing and keeps the callback.
- `item/tool/call` (client-run dynamic tools) only arises if a client registered dynamic tools. The proposed client
  registers none.
