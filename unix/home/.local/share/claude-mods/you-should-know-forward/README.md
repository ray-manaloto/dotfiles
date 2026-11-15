# you-should-know-forward

A Claude Code mod that passes each note from the built-in "You should know" side agent ("✦ Heads up · …") to the
agent of the session where the note was shown. The agent receives it labeled as a separate model's claim to check
before acting on it.

- **While the session works:** the note is appended at once (`$.session.append`), and the agent reads it at its next step.
- **While the session is idle:** the note waits and goes with your next prompt, as context only the model reads
  (`prompt.submit` context). If a turn starts without a prompt, it is appended instead.
- **Each note is passed on once per session.** Your answer to a note is passed on too: "known" (Knew this already, Got
  it, Helpful), closed without "known", turned off, or an explanation you asked for. A note you sent yourself with
  "Chat in main session" is not sent again.
- **You see each delivery** (0.3.0): a toast "Side note sent to the agent · …", and the agent is asked to show you one
  "Side note received: … — checking" line before its next tool call.
- **A "known" mark on a note already passed on waits for your next prompt** (0.3.0). "Chat in main session" also marks
  it known seconds before your chat arrives, so the update is dropped when that prompt is the chat.
- **A delivered marker above the prompt** (0.4.0): "✓ Sent to the agent HH:MMZ · no need to paste it · <line>", then
  "answered HH:MMZ" once the agent's turn ends, under the built-in's own box. It goes when the built-in closes the note
  (known, dismissed, off) or after an hour.
- **Merge, never skip** (0.4.0): every built-in note is passed on. When side-notes raised a note in the last two hours that
  shares at least 30% of its words, it is named beside the built-in note with "if it is the same issue, answer both in
  one reply".
- **If the built-in's data changes shape,** the mod logs one line and stands down for the session.

Option `wakeIdle` (off by default): a note that arrives while the session is idle starts a turn of its own (0.4.1):
wakes are at least 2 minutes apart (one due sooner waits for the gap); at most 1 woken turn in a row without a prompt
you typed (or sent through Remote Control), so notes about woken turns cannot keep an idle session going; task notices,
schedules and other sessions' messages do not reset that; and at most 10 wakes per session per UTC day. side-notes keeps
the same limits on its wakes, so a session sees at most 2 in a row and 20 a day from both (the owner's bound). The day cap is a
backstop for messages this mod cannot tell from yours (`hc send` pastes into the prompt box). A note held back waits for
your next prompt. Each woken turn is billed.

Run it for one session with `claude --plugin-dir <this folder>`. Tests: `claude plugin test <this folder>`.
