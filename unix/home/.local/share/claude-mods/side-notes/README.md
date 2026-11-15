# side-notes

A Claude Code mod that runs its own side agent. Every few model steps (and once at the end of a turn that used tools)
it gives a cheap model (Haiku by default) a digest of the session and your rules, and asks for one thing only: a real
risk the agent or you may be missing. That means a wrong fact, an unsafe or irreversible action, one of your rules
broken, or a "done" the session contradicts. Never style.

- **Each note goes straight to the main agent**, marked as written by a separate model and to be verified before
  acting: at once while it works, or with your next prompt while it is idle. A toast shows you the line.
- **Each note quotes the session word for word.** A note whose quote is not in the session is dropped. A note is
  passed on once; the same note is not raised twice in a session.
- **Your answers count as your words** (0.3.3): when the agent asks you a question, your answer is kept in the digest
  as an owner message, so shortening old work never drops an "OK" you gave.
- **Lenient on form, strict on content** (0.3.4): a note may run to 60 words (the prompt asks for 40), and fields wrapped
  in `<…>` are unwrapped; the format's own placeholders echoed back are still rejected.
- **No copyable placeholders, long know notes kept** (0.3.10): the risk check's answer format describes its fields
  in prose, with one example, so there is no `NOTE: <…>` line to copy, and a reply that copies the prose is rejected.
  A know note over 60 words is cut at its last sentence or clause break and ends with "…", instead of being dropped.
- **Mid-turn messages read as the api view sends them** (0.3.11): a mid-turn message is its own unwrapped text block beside the tool result; inside a result, only a trailing `<system-reminder>` the harness appended counts, so a file, log or transcript that quotes the phrase is data. Parts of one message keep their written order (`#4.1`, `#4.2`), an unclosed `<hc>` stays the other agent's, and a deep check holds a quote to the session plus its mid-turn messages. A mid-turn message whose own row is not shown (no result beside it, a hidden row, or a call the digest does not have) is placed in session order (messages as they came, calls in call order): a hidden row (our own note) shows it in that row's place; otherwise with the nearest call before it that has a row, last if none comes after it, first if none comes before; never after later work (0.3.14, 0.3.17). On a row whose text is our own note, only that text is hidden; its calls and your answers stay, and a deep check never takes a quote from our own notes (0.3.18). A message beside several results goes with the last-called one (by the agent's call order, not the order results came back), so parallel calls shown as separate rows all come before it (0.3.15, 0.3.16).
- **Messages from other agents** (0.3.5): a message that reaches the agent mid-turn (an `hc send` or one typed while it works) is read from the api view and shown in the digest; messages from another tab or session are labelled `[message from <sender>]`, never `[owner]`, and a relayed decision counts as that sender's report.
- **Cost cap**: 2 checks per turn, and per session per UTC day 30 checks and 3M tokens (options `maxChecksPerSession`, `maxTokensPerDay`; both start again at 00:00 UTC, so a busy session is not silenced for good). About $0.006 per check at most with Haiku 5.5.
- **Option `wakeIdle`** (off): a note found after the agent stopped starts a turn of its own (0.3.8): at least 2 minutes apart, at most 1 in a row without a prompt you typed (task notices, schedules and other sessions' messages do not count), at most 10 per session per UTC day. The forwarder keeps the same limits, so a session sees at most 2 woken turns in a row and 20 a day from both.
- **Fails safe**: on an error it writes one line and stops checking for the session. It never runs processes.

Design: ../design.md. Run with `claude --plugin-dir <this folder>`. Tests: `claude plugin test <this folder>`.

## Know check (0.3.0)

At a turn's end, and every `everySteps` steps within a long turn, a second question goes to `knowModel` (default `sonnet`): "what should the owner know right now that
they probably haven't realised?" This is the built-in "You should know" kind of note. It may use the model's own
knowledge of the tools and domains, and it doesn't need a verbatim quote. Its notes arrive as kind `situation`. Built-in
notes are not passed in as raised, because the trial measures whether this check finds the same issues. A find
that repeats a built-in note the forwarder logged for this session is logged as `builtin-repeat` (a match) and not sent
again.

It runs at most once every `knowEveryMinutes` (30) per session, within `knowMaxTokensPerDay` (450,000, about $1 per
session per UTC day at Sonnet list price). That budget is separate from the risk check's caps. Set `knowModel` to `""`
to turn it off.

In the offline replay it raised 3 of the 13 built-in notes the risk check had missed. The risk check raised none.
