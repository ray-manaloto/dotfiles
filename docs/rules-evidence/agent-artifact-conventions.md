# Evidence — `agent-artifact-conventions`

Archaeology behind `.claude/rules/agent-artifact-conventions.md`. Extracted so
the eager copy carries the path tables and the operative rules, and this file
carries why the tree is named and ignored the way it is.

## The `.omc/` → `.agent/` rename (2026-07-25)

`.omc/` was named after the `oh-my-claudecode` plugin — which is **not enabled**.
A convention named for a tool nothing loads.

**`.agent/` was verified before adopting, not assumed.** Control-armed over
Claude Code's full docs corpus: `.agent/` → **0 hits**, while `CLAUDE.md` → 439.
The probe discriminates, so the zero is a real negative rather than a broken
search. Claude Code claims `.claude/**` exclusively and has no opinion about
`.agent/`.

## Why `.gitignore`, not `.git/info/exclude`

`.omc/*` was excluded via `.git/info/exclude`, which is **per-clone and does not
survive a fresh clone**. That is precisely why every artifact anyone actually
wanted tracked had to be force-added with `git add -f`.

**An ignore rule that exists on one machine is not a convention, it is an
accident.** `.agent/` is in the real `.gitignore`.

`.omc/` also remains ignored, for a live reason: the statusline HUD configured in
the **user-level** `~/.claude/settings.json` still recreates `.omc/state/` in
whichever repo is cwd. Retiring that is a user-config change this repo does not
make unasked (`feedback_no_user_level_file_updates`).

## Why promoting to tracked is the default

The migration surfaced the cost of not doing it: **five eager rules cited
research that had never been tracked**, so every reader outside this one machine
hit a dead link — and `doc_refs` could not see the breakage, because the whole
`.omc/` prefix sat in its allowlist.

**A citation to something only you can open is not a citation.** Anything an
eval, a rule, or a future session will cite belongs under `docs/`.

## Why `docs/rules-evidence/` exists

Every unscoped `.claude/rules/*.md` loads in full at session start. Measured
2026-07-28 with an `InstructionsLoaded` hook: unscoped rules are **~88% of the
eager corpus**.

Scoping cannot fix that (`md-size-budgets.md` § "the trigger test" — the rules
that dominate are behaviour- and creation-triggered, and a glob cannot predict a
decision). So the lever is moving case histories, provenance tables and
worked-failure logs into a tracked sibling the rule links by path. The rule keeps
its directive, its operative constraints, and **one** canonical worked example.
Nothing leaves git; it just stops being re-injected every session.

Measured across the whole pass: **132,683 → 105,648 B (−20.4%)**, covering 19 of
the 21 eager rules. `clarify-before-acting` and `clean-git-state` were left
untouched — both were already at the directive-plus-one-example floor, where an
extraction would add a file and a hop while saving a few hundred bytes.

⚠️ **The instrument that produced the 88% figure has no content field** — the
`InstructionsLoaded` hook reports *which* file loaded and *why*, never how big.
And it cannot see `MEMORY.md` at all (auto-memory is a separate channel, and the
file lives outside the repo, so `md-budget` misses it too). Real eager was
≈157 KB, not the 132,683 the rules-only measurement showed. A probe can be blind
to the largest thing it measures and will never say so.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `.gitignore`, `hk-common.pkl`'s `excludePaths`, PRs #412/#413/#414.

_Named in the extracted text but **not** resolved during this extraction: Claude
Code's documentation corpus (the `.agent/` control arm was run in an earlier
session) and the `oh-my-claudecode` plugin._
