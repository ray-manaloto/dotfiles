# Evidence — `ai-cli-invocation`

Archaeology behind `.claude/rules/ai-cli-invocation.md`. Extracted so the eager
copy is just the invocation patterns, and this file carries why the rule is
un-scoped and why it no longer points at a canonical script.

## Why the rule is EAGER, and the accident that proved it

The rule guards an *action* — shelling out to an external AI CLI — not a file.
Path-scoped rules "trigger when Claude **reads** files matching the pattern", and
no glob predicts the moment you are about to run `codex`.

It was scoped to `AGENTS.md` / `.claude/**` / `scripts/**` / `.agent/**` until
2026-07-20, which meant **it could only fire by accident**. And it did: a session
invoked `codex exec "prompt"` positionally — the documented-wrong form — wasted a
probe on the resulting stdin hang, and only saw this rule *afterwards*, because
it happened to write into `.agent/**`.

That is the same defect `zero-skip-policy` and `clean-git-state` were un-scoped
for on 2026-07-15. See `md-size-budgets.md` § "Scoping: the trigger test":
behaviour-triggered rules stay eager.

## Why there is no canonical script to consult

The "Reference" section used to point at the octopus `orchestrate.sh` /
`get_agent_command()`.

**That file does not exist in this repo.** Control-armed: `find . -name
orchestrate.sh` → **0**, while `find . -maxdepth 1 -name hk-common.pkl` → **1**,
so the probe discriminates and the zero is a real negative. It lives only inside
the `octo@nyldn-plugins` plugin cache, which is `false` in **both**
`.claude/settings.json` and `~/.claude/settings.json`, and may vanish on plugin
GC. A reader could not have acted on the pointer.

Hence the rule's standing instruction: when a pattern looks wrong, **re-probe the
CLI itself** (`codex exec --help`, `gemini --help`) rather than hunting for a
canonical script. These flags change between releases — which is exactly how the
wrong forms got documented in the first place.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `.claude/settings.json`.

_Named in the extracted text but **not** resolved during this extraction: the
`octo@nyldn-plugins` plugin and the Codex / Gemini / OpenCode CLIs. The flag
forms in the rule are dated — re-probe `--help` before trusting one._
