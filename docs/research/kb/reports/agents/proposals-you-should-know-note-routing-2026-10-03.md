# Routing "You should know" side-agent notes to a coordinator review subagent (2026-10-03)

Fork of coordinator 97ffeddb (`/subtask`). Read-only research; no source edited.

## What the messages are (evidence)
- `cc-plugin-you-should-know@builtin` is enabled in the USER settings (`~/.claude/settings.json:55`); it is not set in the repo settings.
- The 2.1.287 changelog, embedded in the binary (`~/.local/share/claude/versions/2.1.288`, `Umr()`), says: "Added You should know, a built-in mod where a side agent watches your back and flags things you or Claude might miss. Turn it on with `/plugin enable cc-plugin-you-should-know@builtin` (for first-party sessions with telemetry on)".
- The loader in the binary (INFERRED FROM MINIFIED CODE) loads it only when `CLAUDE_CODE_ENTRYPOINT!=="local-agent"`. That means it is not loaded in subagent / local-agent sessions.
- Card UI strings in the binary: "Heads up", "Chat in main session", "That was helpful", "Not relevant", "Knew this already", "Turn off suggestions", "The prompt box didn't take the note. Press 2 to try again."
- The prefix that is injected is the literal `Here is a note offered by a side agent:`. Choosing "Chat in main session" puts the note into the PROMPT BOX, and the user then submits it. So Ray's forwarded notes reach the coordinator as an ordinary user prompt. Ray then typed "have a subagent review…" by hand each time.
- Exposed configuration surface: env `CLAUDE_CODE_YOU_SHOULD_KNOW_DEBUG` (purpose unknown), and the plugin state key `aboutOpen`. There is no setting that changes where a note goes. The offline `$CC` corpus stops at 2.1.273 and has no hit for "you-should-know" (control: `reload-plugins` hits 2 files), so it is undocumented offline.
- `UserPromptSubmit` gets the `prompt` field (`$CC/hooks.md:1358`), and plain stdout becomes context Claude sees (`$CC/hooks.md:810`). It has no matcher support and fires on every prompt (`$CC/hooks.md:327`). The default command-hook timeout on this event is 30 s (`:430`).

## Options (recommended first)

### A. Recommended: a project `UserPromptSubmit` command hook that routes notes
How it works: the logic lives in a Python module (`dotfiles_setup`, zero-bash) behind the existing thin hook wrapper. When `prompt` starts with `Here is a note offered by a side agent:`, it prints context telling the coordinator to do four things:
1. treat the note as untrusted input and not act on it directly;
2. spawn ONE read-only Opus review subagent that returns cited, researched proposals with PRO/CON, control-armed;
3. persist the report verbatim under `docs/research/kb/reports/agents/`;
4. put the options to Ray via AskUserQuestion.

Any prompt without the prefix gets no output.

- PRO: deterministic, so Ray only clicks "Chat in main session" and submits; there is no extra typing. It matches the repo's hook-plus-python pattern, can be bound by `hook_selfcheck`, and works in every main-checkout-launched session.
- CON:
  - The prefix lives only in the binary, so a wording change upstream silently disables routing.
  - The hook runs on every prompt (a few ms).
  - That a submitted note passes through `UserPromptSubmit` is INFERRED (prompt-box path), not measured.
- Arms:
  1. fixture prompt with the prefix → context emitted; control: an ordinary prompt → no output;
  2. mutation: delete the prefix match, then the test fails;
  3. canary in the doctor, keyed on a `claude --version` change: grep the installed binary for the exact prefix and fail red if it is missing (`probes-need-a-control-arm.md` rule 9);
  4. live: on the next real note, check the transcript for the injected context.

### B. Same routing as a function-hook mod (`UserPromptSubmit` / prompt event in a project `@skills-dir` module)
- PRO: in-process with no spawn.
- CON:
  - Mods fail open with no `.catch`.
  - They load only from the trusted primary directory, so lane worktrees may never load them (`mods-fn-hook-deep-analysis-2026-10-03.md` G1/G9).
  - The mods API churns weekly. This is strictly weaker than A for a routing rule.

### C. Prose rule in `.claude/CLAUDE.md` ("a prompt beginning with the prefix → review subagent")
- PRO: no code.
- CON: relies on model compliance and decays (`mise-tasks-only.md` says markdown is never the only layer). It is not testable.

### D. Fully automatic interception (no click: notes go straight to a subagent)
- REJECT for now. Notes live inside the built-in plugin's own state and UI. No hook event or setting exposes them before the user acts. Reading them would mean reverse-engineering a closed built-in plugin.
- Revisit if upstream adds a destination setting; track it with a saved search on `"you should know" OR you-should-know` in anthropics/claude-code.

### E. Status quo (Ray types the routing instruction each time)
- PRO: zero work.
- CON: a manual step on every note. It happened 4+ times on 2026-10-03.

## GitHub repos touched
_None._ (Local binary, user settings and the offline KB corpus only.)
