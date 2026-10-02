**Engineering** 2026-07-209 min read

# AI Coding Agent Session States: Seven-State Taxonomy and Test Checklist

![](https://agent-island.dev/assets/blog/paper-editorial-covers-20260810/ai-coding-agent-session-state-taxonomy.png)

An AI coding agent session monitor should distinguish seven operational states: `inactive`, `running`, `waiting_for_user`, `completed`, `blocked`, `stalled`, and `unknown`. Events, files, processes, hooks, and notifications are evidence for those states, not states by themselves.

This article defines a provider-neutral taxonomy for session monitors. It is intended for maintainers of developer tools, researchers comparing coding-agent workflows, and teams writing operational guidance. The goal is not to make Claude Code, Codex, or another tool look identical. The goal is to make claims such as _running_, _waiting for the user_, and _stalled_ testable.

> A monitor should state what the available evidence supports now. It should not turn silence, file activity, or one old completion marker into certainty.

## Scope and unit of observation

The unit of observation is one local coding-agent session or thread. A provider-level badge can summarize several sessions, but it should not erase their identities. At minimum, each observation needs a provider, a stable session key, an observation time, and the newest relevant activity time.

This taxonomy describes operational state. It does not judge whether generated code is correct, whether tests pass, or whether a task is complete in the project-management sense.

## Seven primary states

| State | Minimum evidence | What it does not prove |
| --- | --- | --- |
| `inactive` | No fresh evidence of an active turn. | The session was intentionally closed. |
| `running` | Fresh start, progress, tool-use, or streaming activity tied to the current turn. | Useful work is being produced. |
| `waiting_for_user` | A fresh, explicit request for permission, elicitation, clarification, or another required user action. | The user has not already answered elsewhere. |
| `completed` | A terminal event for the current turn with no later activity that supersedes it. | The code is correct or the broader task is finished. |
| `blocked` | An explicit auth, quota, policy, provider, or execution failure that prevents normal continuation. | The failure is permanent. |
| `stalled` | The turn was running, then exceeded a documented silence threshold without a terminal or blocked event. | The process crashed or cannot recover. |
| `unknown` | Evidence is missing, contradictory, unsupported, or too old for another state. | Nothing is happening. |

`completed` and `waiting_for_user` may both map to a user-facing “your turn” treatment, but they should remain distinct in the evidence model. One means a turn ended; the other means the agent explicitly requested input before it can proceed.

## Keep modifiers out of the primary state

Products often create too many states by mixing cause, confidence, freshness, and presentation. Keep those as modifiers:

- **reason:** permission, elicitation, auth, rate limit, API error, process exit, or silence timeout.
- **freshness:** age of the semantic event at observation time.
- **confidence:** explicit, inferred, or fallback.
- **attention:** none, informational, user action, or urgent recovery.
- **turn identity:** the event or turn key that makes deduplication possible.
- **source:** lifecycle hook, structured session record, process signal, filesystem metadata, or heuristic.

This separation lets an interface say “blocked: authentication” without treating every failure reason as a new top-level state.

## Evidence hierarchy

When signals disagree, use the most specific fresh evidence that belongs to the current turn. A practical precedence order is:

1. Explicit semantic events tied to the current turn, such as a permission request, terminal event, or structured provider error.
2. Later user or agent activity that supersedes an earlier event.
3. Correlated process and session activity.
4. Filesystem modification time when a semantic timestamp is unavailable.
5. Silence-based inference, which can support `stalled` but never `completed`.

The ordering matters. A fresh completion event should beat a slightly older process sample. A later user prompt should revoke that completion. A file modification time should not override a structured error merely because bookkeeping touched the file afterward.

Session-state evidence and task-completion evidence solve adjacent problems. Manazir Ali's [Operating Standard for Harness-Based Agents](https://manazir.dev/blog/operating-standard-harness) extends this discipline to completion claims: require artifacts such as a commit hash, test output, and exit code before trusting a reported “done.”

## Reference transition model

```
observe(session, now):
  evidence = newest_semantic_evidence(session)

  if evidence is missing or contradictory:
      return unknown
  if explicit_blocker_is_fresh(evidence):
      return blocked(reason=evidence.reason)
  if explicit_user_action_is_fresh(evidence):
      return waiting_for_user(reason=evidence.reason)
  if terminal_event_is_fresh(evidence)
     and not superseded_by_later_activity(evidence):
      return completed(turn=evidence.turn_key)
  if execution_activity_is_fresh(evidence):
      return running
  if previously_running(session)
     and silence_exceeds_documented_threshold(session):
      return stalled(confidence="inferred")
  return inactive
```

The model needs two expiry policies: one for active evidence and one for attention. An old completed turn should not call the user back after a weekend. A stalled state should also age out instead of remaining an eternal warning.

## Evaluation checklist

A monitor is not robust because it recognizes a happy-path completion string. Evaluate it with at least these tests:

01. **Fresh start:** a new turn becomes `running` without inheriting the previous turn's terminal state.
02. **Duplicate observation:** the same event is processed twice but produces one notification.
03. **Supersession:** a later user prompt revokes an earlier `completed` or `waiting_for_user` state.
04. **Explicit input:** permission and elicitation requests are distinguished from ordinary completion.
05. **Provider error:** an error-shaped terminal envelope becomes `blocked`, not `completed`.
06. **Silence:** missing activity can become `stalled`, but never a fabricated success.
07. **Restart recovery:** restarting the monitor reconstructs current state from durable evidence.
08. **Multiple sessions:** one completed thread does not hide another running thread.
09. **Clock skew:** malformed or future timestamps degrade to a documented fallback.
10. **Partial write:** a truncated record becomes `unknown` or is retried; it does not crash the state engine.
11. **Expiry:** old terminal and stalled states return to `inactive`.
12. **Privacy:** the test verifies where raw session content is read, retained, and transmitted.

## Four evaluation levels

| Level | Capability | Required proof |
| --- | --- | --- |
| L0 Display | Shows provider or process presence. | Current process/session discovery. |
| L1 Event-aware | Recognizes start, input, completion, and explicit failure events. | Structured fixtures for each supported provider. |
| L2 Turn-aware | Tracks identity, freshness, supersession, and deduplication. | Transition tests and duplicate-event tests. |
| L3 Operational | Recovers after restart, handles several sessions, expires stale attention, and documents privacy boundaries. | Restart, multi-session, malformed-input, expiry, and data-flow tests. |

These levels are cumulative. They describe evidence quality, not product quality. A focused L1 tool can be useful; it should simply avoid making L3 claims.

## Implementation notes

Agent Island applies a local version of this model across Claude Code, Codex, Antigravity, Grok, and Cursor. It reads session artifacts already present on the machine, keeps the user-facing state set small, and does not upload session data to an Agent Island service. The current stable release is [v1.7.1](https://github.com/tristan666666/agent-island/releases/tag/v1.7.1).

For a deeper look at one transition, see [why a completion event is not a session state](https://agent-island.dev/blog/completion-event-session-state/). For the instrumentation tradeoff, see [Claude Code hooks vs persistent session monitoring](https://agent-island.dev/blog/claude-code-hooks-vs-session-monitoring/). To compare the broader tool landscape, use the [Agent Island comparison hub](https://agent-island.dev/compare/). The product's data boundary is documented on the [privacy page](https://agent-island.dev/privacy/).

## Suggested citation and update policy

Suggested citation: Tristan Tang, “AI Coding Agent Session State Taxonomy and Evaluation Checklist,” Agent Island, July 20, 2026, https://agent-island.dev/blog/ai-coding-agent-session-state-taxonomy/.

This resource is versioned by its publication and modification dates. Definitions will change only when a state can no longer be tested consistently across supported evidence sources. Provider-specific event names belong in implementation notes, not in the provider-neutral definitions.