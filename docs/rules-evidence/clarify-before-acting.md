# Clarify Before Acting — Evidence

Evidence extracted from `.claude/rules/clarify-before-acting.md`; the rule keeps
the directive and the 2026-06-29 worked failure eager.

## 2026-09-09 — audit refactor

**Findings applied:** `rule-clarify-before-acting-1` through `-3`.

**Native anchors re-read:** `sub-agents.md:379-384` says a normal subagent has
`AskUserQuestion` removed even when listed, while a fork skips tool filtering
and retains the main conversation's tool pool. `permissions.md:80-90`,
`permission-modes.md:465-469`, `hooks.md:1773`, and the saved verbatim
2.1.259 changelog entry at
`.agent/kb/raw/claude-code-changelog-2.1.258-2.1.266.md:206-209` (gitignored
and machine-local — unverifiable from a fresh clone) establish the other
no-prompt modes. `settings.md:646` documents project-setting reload, and
`hooks.md:1744-1745` documents that `deny` prevents the tool call.
(Matcher semantics are `hooks.md:285-297`, not `:1542` — see the
closing section.)

**Timeout anchor re-read:** `settings-reference.md:2759-2774` documents
`askUserQuestionTimeout` as USER-or-MANAGED, introduced in v2.1.200, with
values `60s|5m|10m|never`, default `never`, and
`CLAUDE_AFK_TIMEOUT_MS` as the per-session override. When it fires, already
selected options are submitted. `tools-reference.md:125-137` confirms the
same partial-answer semantics. Project `.claude/settings.json` has neither
`askUserQuestionTimeout` nor the rejected `plansDirectory` key.

**Gate probe:** `dotfiles_setup.ask_quality` remains wired to
`AskUserQuestion` in the single PreToolUse matcher and keeps both allow and
deny arms. The prose fallback deliberately cannot be machine-graded: it uses
the same recommendation, `PRO:`/`CON:`, citation, and free-form standard, then
stops.

**Motivating defect still caught:** the 2026-06-29 hk-timeout proposal was
impossible. The refactored rule still forces that infeasibility to surface and
the pivot to be confirmed before implementation, even in a subagent or
non-interactive mode where `AskUserQuestion` is unavailable.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  evidence note, and ask-quality hook.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base)
  — pinned Claude Code documentation corpus.

## The matcher is an exact-string list, not a regex (2026-09-09)

The A-2 draft asserted "hook matchers are regexes" and cited
`$CC/hooks.md:1542`. Both halves were wrong.

**The citation.** `hooks.md:1542` is inside the PreToolUse section, describing
which tool names *that event* matches. It says nothing about matcher syntax.

⚠️ **The first refutation published here used a broken control arm, and the
correction is the more useful lesson.** It ran `grep -n "regex" hooks.md` → 0
and reported "the word simply is not there". That is a **token-spelling bound**
— exactly the failure `probes-need-a-control-arm.md` §3 names — because the
corpus spells it `regular expression`, which returns **5** hits in the same
file, one of them the very row defining the regex path. The `grep -c "matcher"`
→ 82 arm proved only that the file is readable, not that the probe could find
the concept it was denying. **A control arm must be aimed at the thing your
claim is about.** The conclusion below survives; the probe that was offered for
it did not.

**The claim.** The real anchor is `hooks.md:285-297`, "Matcher patterns", and it
is conditional, not categorical:

| Matcher value | Evaluated as |
|---|---|
| `"*"`, `""`, omitted | match all |
| only letters, digits, `_`, `-`, spaces, `,`, `\|` | **exact** string, or `\|`/`,`-separated list of exact strings |
| contains any other character | unanchored JavaScript regular expression |

This repository's own matcher, `Bash\|AskUserQuestion\|Edit\|Write\|NotebookEdit`,
sits in the middle row — exact strings. So the rule was documenting its own gate
with a claim that is false of that gate.

It matters operationally: adding one `.` or `^` flips the entire value onto the
regex path, where `RegExp.prototype.test` matches anywhere in the value
(`hooks.md:297`) — `Edit.*` would then also fire for `NotebookEdit`. The
hyphenated-name caveat is the same trap with a version bound: before v2.1.195 a
matcher like `code-reviewer` took the regex path and also fired for
`senior-code-reviewer`.

**The lesson is the sibling of the fabricated-variable case in
`ai-cli-invocation.md`:** a lane restated a rule of thumb that is true of *most*
harnesses, attached a nearby line number, and produced something that reads as
sourced. A citation is only evidence if the cited line says the thing.
