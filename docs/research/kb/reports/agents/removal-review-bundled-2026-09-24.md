# Bundled `/code-review` (high) — removal branches (2026-09-24)

Verbatim findings returned by the forked bundled `code-review` skill, run at `high` over dotfiles
`3db81d8e..HEAD` and knowledge-base `origin/main..HEAD`.

1. `knowledge-base/.claude/workflows/kb-tool-review.js:189`. The review stage now sends a gap-analysis report
   directory to `kb-codex-astra-reviewer`. That agent only reviews git diffs (`kb-codex --review --base`), and its
   launch aborts unless the caller passes `KB_LANE`, which this workflow never does.
   *Failure:* every `kb-tool-review.js` run reaches the per-tool `review:<key>` step. The agent then either stops
   at `: "${KB_LANE:?...}"` or refuses because there is no committed diff to classify. `out.review` holds a
   refusal or error instead of a cold review.
2. `knowledge-base/.claude/agents/kb-codex-astra-reviewer.md:51`. The reviewer still says `cold:codex` is the
   default (line 13) and that `.claude/CLAUDE.md` declares `implementation lane = codex` (line 51). This diff
   deleted that line and made `cold:codex-astra` the default. The same stale text is at
   `.codex/agents/kb-codex-astra-reviewer.toml:85` and `kb-review/references/lanes.md:239`.
   *Failure:* the default review lane can bounce small diffs back to a lane whose only runner was the removed
   plugin, or refuse on a lane declaration that no longer exists.
3. `knowledge-base/.claude/agents/kb-codex-implementer.md:43`. The new implementer runs
   `cat spec | mise run kb-codex -- --write ... --timeout 3000` as one foreground Bash call. The harness caps a
   single Bash call at about 600s.
   *Failure:* a lane longer than 10 minutes is killed or auto-backgrounded while codex is still writing, so the
   agent runs gates against a half-applied tree.
4. `dotfiles/.claude/CLAUDE.md:60`. The new routing row for a Claude-authored diff gives
   `codex exec -s read-only --ignore-rules review --commit <SHA>` without the `-c 'sandbox_mode="read-only"'` that
   the `codex-sdlc-team` skill and `session-handoff` require.
   *Failure:* a review run from the eager table may execute at the machine default `danger-full-access`. Two
   authoritative docs give different commands.
5. `knowledge-base/.codex/agents/claude-advisor.toml:1`. A codex twin named `claude-advisor` calls itself the
   "Escalation-only Fable advisor", yet under codex it always runs on codex's GPT model.
   *Failure:* an escalation meant to reach a different model family is answered by the same OpenAI family,
   labelled Fable.
6. `dotfiles/python/src/dotfiles_setup/removed_plugins.py` (hooks branch). Hook-trust keys are reported even when
   the codex plugin is explicitly `enabled = false`. The marketplace check exempts a disabled plugin, but the
   hooks check does not.
   *Failure:* claudex-loop's ruled "disable" state would report at every SessionStart if its hooks were ever
   trusted.
7. `dotfiles/python/src/dotfiles_setup/removed_plugins.py` (`_load_json`). It swallows `JSONDecodeError` and
   returns `{}`, so a corrupt `installed_plugins.json` or `known_marketplaces.json` reports clean. The codex
   path, by contrast, reports a parse failure.
8. `dotfiles/python/src/dotfiles_setup/removed_plugins.py` (Claude side). The check ignores
   `~/.claude/plugins/cache/<name>` and settings `extraKnownMarketplaces`. The cache dir
   `~/.claude/plugins/cache/fable-orchestrator` still exists on this Mac.
9. `dotfiles/tests/test_workflows_js.py:21`. The roster gate matches only single-quoted `agentType: '...'`,
   while the KB twin accepts both quote styles.
   *Failure:* a double-quoted or template-literal dispatch of a plugin agent passes.
10. `dotfiles/python/verification/suites.toml:2405`. The `orchestration.codex-only-lanes` description still cites
    "`orchestration.mode-line-declared` above" and "the plugin skill's review-tier table". This diff deleted both.

## GitHub repos touched

_None._ Local clones only.
