[Skip to main content](https://daintree.org/docs/agents/states#main-content)

## Why States Exist

Delegating to several agents at once only works if you can tell, without reading any of them, which ones need you. That is the whole job of agent state: Daintree watches each agent's terminal output and reduces it to one of six values, plus a reason when the agent is stuck. Everything that ranks, filters, badges, or notifies in Daintree reads that one signal.

Nothing here is configured. State detection runs for every agent panel, including [plugin-contributed agents](https://daintree.org/docs/plugins), from the moment it launches.

## The Six States

| State | Label | Meaning |
| --- | --- | --- |
| **Idle** | idle | The agent's prompt is up and nothing is in flight. This is where a session starts and where it returns after a watchdog gives up on a stale wait. |
| **Working** | working | The agent is doing something — streaming a response, running a tool, executing a shell command. Daintree does not split these; from outside the CLI they are the same fact. |
| **Waiting** | waiting | The agent has settled and is blocked on you. The [waiting reason](https://daintree.org/docs/agents/states#waiting-reasons) says what kind of block it is. |
| **Directing** | directing | You are actively typing into that agent's terminal. It is a renderer-side state — it exists so a panel you are mid-sentence in does not sit in the "needs attention" list you are already attending to. |
| **Completed** | done | The agent finished a task, detected from its own completion output. |
| **Exited** | exited | The agent process ended — cleanly, by your kill, or by crashing. |

Note

There is no "Running" state. Earlier builds had one, as a pre-state-machine signal about the shell process, and older docs still list it. It was folded into **working**: any stored `running` value is read as `working`, and nothing produces it any more.

### How states move

The transitions are deliberately narrow, so a noisy terminal cannot walk an agent into a state it was never in:

- **idle** goes to working (on launch, output, or your input) or to exited.
- **working** goes to waiting (silence, once the agent has settled), completed (a completion pattern), or exited.
- **waiting** goes back to working (output or input), to completed, to exited, or — if a watchdog decides the wait is stale and no child process is alive — back to idle.
- **completed** goes to working, waiting, or exited.
- **exited** is terminal for that agent run. It returns to idle only when a new agent session starts in the same panel.

A user kill is the one hard reset: it returns the panel to idle from any state.

## The Four Waiting Reasons

"Waiting" alone does not tell you what it costs to unblock. A permission dialog is a keystroke; a rate limit is a different afternoon. So a waiting agent also carries a reason:

| Reason | Badge | What it means |
| --- | --- | --- |
| **approval** | Approval | A permission or approval selector is on screen — a tool approval, a y/n confirmation, a trust dialog. A specific choice is required, not free text. |
| **error** | Error | The agent settled after a blocking error: an auth failure, a rate limit, a network error, a failed command. Typing at it may not unblock it. |
| **question** | Question | The agent asked a free-form question. Read it before answering — this is the one that most rewards actually looking. |
| **prompt** | — | An empty input prompt is visible and nothing more specific was detected. It may just mean "ready for the next instruction". |

Only the first three earn a specific label. **prompt** is the classifier's fallback — it means no positive evidence was found — so every surface renders it as plain "waiting for input" rather than claiming a certainty the classifier does not have.

The same vocabulary is used everywhere, so one agent reads as one signal:

- The **panel header chip** carries the badge next to the state.
- The **waiting popover** in the layout lists every waiting agent with how long it has been waiting, and a reason badge on each row the classifier could label.
- **Fleet** pane badges and **Pilot** rows show it alongside the agent and branch.
- **OS notifications** use the sentence form — "Claude is waiting for approval", "Codex asked a question", "Grok is blocked by an error". A grouped notification only names a reason when every agent in the group shares it; a mixed group falls back to the generic wording rather than overclaiming for any member.

When several agents wait at once they are ordered by how much a second of your attention buys: **approval** first (one keystroke unblocks it), then **error** (hard-blocked and burning wall clock), then **question**, then a bare **prompt**. Within a reason, the longest wait comes first.

Only those first three print a badge. An agent waiting on a bare prompt shows its title and its wait time and nothing else — the empty space is the reading, not a missing badge: nothing in its output said what it wants.

View full size:![The waiting popover, headed ‘Waiting for input’ with an amber ‘3 agents’ count. Settlement migration, on atlas-ledger, carries an amber Approval badge and has waited 40s. Statement importer, on atlas-ledger, carries a red Error badge at 23s. Currency table, on atlas-ledger, is waiting as of now and carries no badge at all.](https://daintree.org/_app/immutable/assets/agents-states-waiting-popover.CFbjyyxP.jpeg) View full sizeTriage order, not arrival order: approval above error, and the unclassified wait last with no badge to give it

## How Detection Works

Two questions are answered separately: _which agent is this_, and _what is it doing_.

### Which agent

An agent panel's runtime identity is resolved from the **executable's image path** in the process tree, not from its window title or its `argv`. That is a deliberate correction: agent CLIs rewrite both, so title-and-argv heuristics confidently reported the wrong agent. The detector also folds in evidence from commands you type into the shell, applies hysteresis before committing a change, and holds the last committed identity when its signals disagree — which is why the chrome does not flicker during a launch or an exit.

### What it is doing

State comes from the PTY stream itself: output volume and temperature, per-agent output patterns for prompts, completions and approval dialogs, redraw structure for full-screen TUIs, and your own keystrokes. A settle window separates "the agent paused mid-thought" from "the agent is done and waiting", and the waiting reason is classified from the last dozen visible lines — wide enough to catch an approval dialog, whose question sits above its selector rows.

Where output goes silent but work continues — a compile, a test suite — process-tree CPU acts as a bounded backstop: it holds the current state rather than dropping to idle early. It never _creates_ activity on its own, and it expires, so a genuinely wedged process cannot be held in "working" forever by a busy child.

Note

**Why a state can lag.** Detection is inference over a byte stream, not a callback from the agent. Transitions are debounced on purpose — a half-second of silence is not a completed task, and a spinner frame is not a new state — so a state can trail reality by a second or two, and an agent idling for a long time is polled at a slower cadence until it makes a sound. The state chip's tooltip reports the trigger that caused the last change (input, output, heuristic, AI classification, timeout, exit, activity, or title) along with a confidence score when the trigger is not a certain one, so you can see what the reading is based on.

### Behaviors worth knowing

- **A crashed agent CLI reports as exited**, not as a wait that never ends. Before this, a CLI that died mid-turn left its panel stuck on "waiting" — indistinguishable from an agent politely asking a question, and the worst possible lie for a triage list to tell.
- **Scrolling does not flip state to working.** Wheeling through a mouse-reporting TUI sends input sequences to the process, which used to read as activity. Scrolling back through what an agent wrote is not the agent working, and no longer registers as it.
- **Directing clears itself.** It is held by a short debounce while you type, released on `Enter` or `Esc`, and swept by a wall-clock guard so a backgrounded window cannot strand a panel in it.

## The Quiet Band

"Working" is not one condition. An agent that has been working for forty minutes and printing steadily is healthy; an agent that has been working for forty minutes and silent for the last twelve is probably wedged. Rendering both identically as "working" is exactly the case where a fleet view stops being useful.

So a working run that has produced no output for over ten minutes leaves **working** for a band of its own: **quiet**. It ranks directly under **Waiting** and above **Ready for review**, because a stall nobody notices costs the rest of the morning and an unread hand-back costs a minute. Being a band is the whole change: it carries a count, a segment on [Pilot](https://daintree.org/docs/agents/all-agents)'s filter bar, a chip on the group heading of every project holding one, and its own footer sentence — "2 agents have gone quiet" — once nothing louder is asking. Before, it was an annotation on one row, so every count, filter and summary reported the one run worth finding as ordinary work in flight.

The silence is measured from the later of the run's last output and its entry into the current working stint. Anchoring on the stint rather than on output alone matters: a run resumed after waiting quietly for twenty minutes would otherwise be stamped quiet for twenty minutes before it had a chance to make a sound. Quiet is also the one band whose row puts a word in front of its clock, because it is the one band whose clock measures something other than how long the run has been in the state it is in.

**Quiet is not a demand.** Nobody is asking you for anything, so it stays outside the set that "3 agents need you" is allowed to count — folding it in would promise three conversations and deliver two. It belongs instead to the wider _attention_ set, which is the demands plus quiet, and which is what group chips and the footer summary read.

The word is _quiet_, not _stalled_. The fleet observes the silence and infers nothing about its cause: an agent halfway through a long compile and an agent wedged on a dead socket look identical from here, and only one of them is a problem. A healthy busy agent is simply not in the band; being in it is the signal, and it is never merely unknown.

## Park and Snooze

State is what the agent is doing. Park and snooze are what _you_ have decided about it, and they change how state is read without changing the state itself.

**Park** shelves a run you have already triaged. It leaves whatever band it was in for **Parked**, stops counting as demand everywhere — group counts, chips, the footer sentence — and carries a note in your own words so the row explains itself when you come back to it. Parked still gets a filter segment of its own, because "show me everything I shelved, with my notes" is a real question and a run parked while it was waiting has to be findable somewhere other than the bottom of the list. A park can be gated on another terminal: it releases itself, with a notification, the first time that terminal goes from busy to ready _after_ the park was made, and also if that terminal is trashed — a park that can no longer release has to resurface rather than hide its run forever. Otherwise it holds until you lift it, or until it goes stale: a park nobody has revisited in fourteen days is intent you no longer remember forming, and is dropped the next time the set is loaded. No more than 200 runs can be parked at once, a bound on a runaway caller rather than on you. The agent underneath keeps doing whatever it was doing.

**Snooze** defers a run that is not ready to be triaged yet: 15 minutes, 30 minutes, 6 hours, or unlimited. It withdraws the run's _demand_ on you and nothing else — a snoozed working agent still counts as running, a snoozed completed agent is still completed. Any typed input clears it, which is why "unlimited" is a ceiling rather than "forever": most snoozes end because you came back and answered the agent. Snoozes are wall-clock, so a machine that sleeps through the window wakes with the snooze already over.

The two are separate because they end differently: a park ends on a gate or by hand, a snooze ends on a clock or on your keystrokes. Both are documented in full, with the demand bands and filters they feed, at [Pilot](https://daintree.org/docs/agents/all-agents).

## Where States Surface

| Surface | What it uses state for |
| --- | --- |
| **Panel header chip** | Per-panel icon and color, the waiting-reason badge, the activity headline, elapsed time, the change trigger and confidence, and session cost where the agent reports it. |
| **[Worktree cards](https://daintree.org/docs/worktrees/cards)** | A state badge per card, showing the highest-priority state among that worktree's agents — working, then directing, waiting, completed, exited, idle. |
| **Sidebar filters** | The quick filter bar segments worktrees into working, waiting, and finished; the full filter popover adds "has terminals", completed, and exited as separate session filters with live counts. |
| **Waiting popover** | Every waiting agent across the window, reason-ranked, with jump-to and kill actions. |
| **[Fleet](https://daintree.org/docs/fleet)** | Pane state badges, including the waiting-reason badge, and the counts that say how much of the fleet wants something. |
| **[Pilot](https://daintree.org/docs/agents/all-agents)** | Nine attention bands over every run in every project, a seven-segment filter bar that partitions them, a per-band chip on each project's group heading, and — scoped to one project — the same rows regrouped by worktree. |
| **[Notifications](https://daintree.org/docs/notifications-and-sound)** | Waiting and completion notifications and their sounds, plus the title bar and dock badge counts, which clear when you focus the window. |
| **Quit and power** | Only _working_ agents trigger the quit confirmation and keep the system from suspending. Waiting and directing agents are paused, not in flight. |
| **Memory management** | Under cache pressure, idle views are evicted before views with active agents. View eviction still leaves PTYs running. Automatic project closure skips every project with a live terminal; explicit Sleep project has a separate process-reclaiming effect. |

### From state to band

Fleet and Pilot do not show raw states. They fold state, waiting reason, how long a run has been silent, and your own park and snooze decisions into one of nine bands, so a row's label, its tone, and its sort order can never disagree:

- **Parked** and **Snoozed** take precedence over every state, including a blocked run. Parking is you saying "this does not need me until further notice"; an attention model that second-guesses that the moment something looks urgent is one you would have to keep re-checking. They are ranked low — below Finished, above Idle — because nothing in them is asking for you.
- **Blocked** — waiting with the _error_ reason.
- **Waiting** — waiting for any other reason.
- **Quiet** — a live run that has said nothing for ten minutes. See [The Quiet Band](https://daintree.org/docs/agents/states#quiet-cue).
- **Ready for review** — completed and not yet acknowledged. Once the workspace's completion watermark has passed it, it becomes **Finished** and stops asking for anything.
- **Working** (or **Directing**) — a live run still printing, hued but making no demand.
- **Idle**, or **Exited** for a run whose process has ended.

Two groupings sit on top of those bands, and they are not the same set. **Blocked**, **Waiting** and **Ready for review** are the _demands_: a fleet holding none of them has nothing outstanding. **Quiet** joins them in the wider _attention_ set — the one a group chip and the footer summary read — because a silence is worth pointing at without being something anyone asked you for. The summary keeps them in separate sentences rather than one total, so pressing a sentence to filter down to it always reveals exactly the rows it counted.

Keyboard navigation reads state too: there are bindings to jump to the next waiting agent in the current project, the next waiting agent anywhere, and the next working agent, so a fleet is navigable without touching the sidebar. See [Keyboard Shortcuts](https://daintree.org/docs/keyboard-shortcuts).

## Plugin-Contributed Agents

An agent registered by a [plugin](https://daintree.org/docs/plugins) takes part in all of this. Output-volume detection works from the launch hint alone, so a plugin agent gets activity and waiting detection with no extra declaration. A completion state depends on recognizable completion evidence; it is not guaranteed for every CLI. A plugin can also declare output patterns for its agent, which sharpen prompt and completion detection to the same standard as a built-in. Detection stays passive observation of the terminal stream — Daintree never modifies an agent's own configuration to get a better reading out of it.