# PROTOTYPE — throwaway code. Do not ship.

Everything under `python/prototypes/` is **throwaway**: written to answer one
question fast, then deleted. It is not imported by `dotfiles_setup`, has no
tests by design, and must never be depended on.

Per `.claude/rules/agent-artifact-conventions.md` this tree lives on a
`prototype/*` branch only — it is not merged to `main`. The *decision* a
prototype settles goes to its wayfinder ticket; the prototype itself stays on
its branch as a primary source.

| Prototype | Question | Ticket |
|---|---|---|
| `secrets_cli_shape/` | What shape is the secrets CLI, given the Claude Code and Codex plugins are its consumers? | [#432](https://github.com/ray-manaloto/dotfiles/issues/432) |
