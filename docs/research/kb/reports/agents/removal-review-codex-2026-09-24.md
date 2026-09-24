# Codex cross-family review — removal branches (2026-09-24)

Verbatim `-o` output of `mise exec -- codex exec -s read-only --ignore-rules review --base <ref> -c sandbox_mode="read-only" -c model_reasoning_effort="xhigh"` (model gpt-6-astra per the log header). dotfiles base `3db81d8e` (via temp branch `tmp/review-base-fable`), HEAD `d4b0b5c4`; knowledge-base base `origin/main` `e8fe42ae`, HEAD `d94b0e82`. Note: in knowledge-base `mise exec -- codex` resolved **npm 0.154.0** (that repo still pins it); dotfiles resolved native 0.156.1. A first launch with a `-` prompt failed rc=2: `--base` cannot be combined with `[PROMPT]`.

## dotfiles

The new removal guard can falsely report clean state when registries are unreadable or a removed marketplace is restored through settings. Runtime verification was blocked by the read-only sandbox’s restrictions on mise and uv cache writes.

Full review comments:

- [P2] Surface registry read failures instead of reporting absence — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/removed_plugins.py:33-37
  If either Claude plugin registry is malformed or unreadable, this returns an empty mapping and the removed-plugin check reports no findings. The Codex reader similarly suppresses every `OSError`. Consequently, an inaccessible registry is indistinguishable from a verified clean installation. Treat missing files as empty, but report other read and parse failures as unchecked state, as the TOML parse-error branch already does.

- [P2] Check marketplace declarations in settings sources — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/removed_plugins.py:44-47
  If `extraKnownMarketplaces.fable-orchestrator` is restored in user, project, or local settings while the installed-state registries remain clean, this check returns no finding because it examines only `enabledPlugins`. That declaration can register the removed marketplace again on startup. The static token contract also misses a marketplace-only declaration because it contains neither forbidden token. Inspect `extraKnownMarketplaces` keys in each settings source as well as the materialized marketplace registry.
## knowledge-base

The reviewer substitution breaks the peer-tool workflow’s artifact-review contract. Graph queries and focused tests were blocked by graph-size and sandbox/cache restrictions, so this conclusion rests on source inspection.

Review comment:

- [P1] Use a report-scoped reviewer for peer-tool analyses — /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/workflows/kb-tool-review.js:189-189
  With the default `reportDir`, this stage reviews newly generated files under `docs/research/reports`. However, the replacement agent mandates a ref-based Git diff that explicitly [excludes `docs/research/**`](.claude/agents/kb-codex-astra-reviewer.md#L216-L222). It therefore cannot perform the requested artifact review under its instructions: it either refuses or reviews an unrelated branch diff, while the pipeline forwards its response into synthesis. Use a report-oriented Codex invocation or adapt the agent to accept the specific report as its review scope.