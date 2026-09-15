## Verdict

Claude Code 2.1.273 should be adopted, but the spec’s proposed “change only `schemas/sources.toml:51`” update is not internally valid.

The host is already running native `2.1.273`. The committed devcontainer inputs would still install `2.1.270`. No Python hook or agent-state code needs changing, and the two agent-delivery fixes remain vendor claims until replayed through the real CLI/stream interface.

No files were modified and no repository gates, builds, lock refreshes, or network fetches were run.

## Licensed dissent: the one-field bump is incomplete

The repository couples a vendored version to its exact source URL:

- [sources.toml:51](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:51) records `2.1.272`.
- [sources.toml:52](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:52) points at tag `v2.1.272`.
- [schema_vendor.py:249](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/schema_vendor.py:249) derives that URL from the version.
- Drift checking does not detect a version/URL mismatch.

Changing only line 51 would leave false provenance at line 52. It also conflicts with [sources.toml:78](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:78), which currently says the version “IS the pin,” whereas the spec redefines it as only a release-review marker.

There is a second contradiction: the documentation says to use `schema-vendor-refresh`, but [schema_vendor.py:405](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/schema_vendor.py:405) feeds the existing Claude version back as the target and [schema_vendor.py:469](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/schema_vendor.py:469) discards CLI arguments. The documented command cannot advance 2.1.272 to 2.1.273.

The coherent choices are:

1. Preserve the existing provenance model and update version, source URL, and explanatory metadata together; or
2. Split “last reviewed release” from “vendored source version” into separately named fields.

## Documented traps affected by 2.1.273

### Agent-result delivery: partly stale, but not yet verified

Anthropic claims two directly relevant fixes:

- Completed subagents should no longer be reported failed or lose their result when the streamed reply lacks usage/model metadata ([release note 16](/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/e0321143-b348-4af2-ba87-bf8a28c1ea67/scratchpad/rel273.md:16)).
- SDK/`stream-json` should no longer drop messages and the final report after a subagent moves to the background ([release note 20](/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/e0321143-b348-4af2-ba87-bf8a28c1ea67/scratchpad/rel273.md:20)).

The overbroad stale language is in [feedback_agent_team_delivery_discipline.md:3](/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/feedback_agent_team_delivery_discipline.md:3):

- Lines 20–22: idle without reporting necessarily loses the work.
- Lines 32–38: the message path is “not worth relying on at all,” is merely a bonus, and disk recovery is required after every idle notification.

Those statements should eventually be scoped as “observed through 2.1.272; documented fixed in 2.1.273; retain disk fallback until replayed.”

No 2.1.273 fix makes [.claude/rules/agent-report-persistence.md:61](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/agent-report-persistence.md:61) obsolete. Incremental tracked persistence still protects against crashes, authentication failures, cleanup, context loss, and unrelated nondelivery. Its transcript-recovery warning at [line 114](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/agent-report-persistence.md:114) also remains correct.

A pre-existing inconsistency should be repaired separately: [lines 54–57](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/agent-report-persistence.md:54) say a parent-side `PostToolUse`/`Agent` hook was not added, while [settings.json:121](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:121) shows that it now exists.

### False-success task notifications: still a live trap

The release notes do not claim to fix notifications saying “exit code 0” when the underlying logged command returned nonzero. Therefore the direct-RC rules in [verify-before-advancing.md:83](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/verify-before-advancing.md:83) and `persistence-gate-retry.md:103` must remain.

The release fixes false-failed agent delivery and truncated streams—not false-success command-status reporting.

### Permission checker and `hook_guard`

The release changes two native behaviors:

- Unanalyzable Bash under `blockReadsOutsideWorkingDirectories` should prompt instead of skipping the prompt ([release note 6](/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/e0321143-b348-4af2-ba87-bf8a28c1ea67/scratchpad/rel273.md:6)).
- The 2.1.268 behavior that applied Read/Edit denies to unanalyzable `eval`/`env -C` Bash lines was reverted; they prompt again ([release note 25](/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/e0321143-b348-4af2-ba87-bf8a28c1ea67/scratchpad/rel273.md:25)).

No custom Python change follows:

- Sensitive paths already have explicit Read and Bash denies at [settings.json:42](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:42).
- The project guard intentionally treats `eval`, `sh -c`, substitutions, and aliases as fail-open because it is a redirect guard, not a sandbox ([hook_guard.py:641](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:641)).
- That decision has an explicit control test at [test_hook_guard.py:512](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_hook_guard.py:512).

Do not add a partial shell parser to `hook_guard.py`.

### Auto-compaction

The advisor-turn double-counting fix ([release note 17](/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/e0321143-b348-4af2-ba87-bf8a28c1ea67/scratchpad/rel273.md:17)) should make the existing threshold more accurate.

The `33` override at [settings.json:4](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:4) is an intentional ~30% workflow tripwire, not a workaround for the bug; [receipt 567:7](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/receipts/567.md:7) documents that design. Keep it unchanged and re-baseline advisor-heavy observations against 2.1.273.

### Outside-read blocking and memory directories

`permissions.blockReadsOutsideWorkingDirectories` and `autoMemoryDirectory` are absent from project settings; positive controls `additionalDirectories` and `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` are present at [settings.json:3](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:3) and [settings.json:67](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:67).

Therefore the protected-memory fix at release-note line 15 is not currently activated here and does not retire `memory_index.py`.

### `.git/info/exclude`

The local exclude file contains active Claude runtime exclusions at [.git/info/exclude:8](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/info/exclude:8). The vendor fix only prevents a long-running session from recreating a stub after `.git` is removed or relocated. No repo workaround for that behavior was found, so no change is needed.

### Other passive improvements

These require no repository changes:

- `/tui` no longer blocked by an already-finished teammate.
- MCP retry exhaustion now produces a useful notification.
- Scheduled tasks copied between worktrees should no longer attach to the wrong session.
- Long-session hook/subagent activity processing should be more responsive.

## What to adopt

The primary adoption is reliable background/`stream-json` delivery—but only after the two-version replay below. Once verified, disk recovery can return to being a fallback instead of the assumed primary delivery channel. Tracked incremental persistence should remain mandatory.

`OTEL_LOG_TOOL_DETAILS=1` is the strongest optional configuration candidate because 2.1.273 adds real agent, skill, plugin, and MCP names to cost/token metrics. Do not enable it automatically: first prove an exporter consumes the data and that the resulting label cardinality is acceptable. Keep `OTEL_LOG_RAW_API_BODIES=0`.

Do not adopt as part of this bump:

- Gateway hint headers: no repo-owned LLM gateway consumer was found.
- `blockReadsOutsideWorkingDirectories`: useful as a separate security decision, but it changes interactive access policy.
- A root mise Claude pin: [currency.toml:29](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/currency.toml:29) deliberately gives ownership to the native installer.
- An image native-installer migration: the current locked multi-architecture mise model is valid and reproducible.

## Exact repository change list

### Release metadata

1. [schemas/sources.toml:51](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:51): `2.1.272` → `2.1.273`.
2. [schemas/sources.toml:52](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:52): URL tag `v2.1.272` → `v2.1.273`.
3. Keep the SHA at [sources.toml:54](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:54) unchanged.
4. Leave `.claude/types/claude-code.d.ts` byte-identical, including its 2.1.271 banner.
5. Update [sources.toml:70](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:70) and [.claude/types/README.md:54](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/types/README.md:54): 2.1.271, 2.1.272, and 2.1.273 ship identical declarations; “lag by one release” is now false.
6. Repair the refresh interface or document an explicit narrow metadata-edit exception; the current canonical command cannot advance Claude’s self-pinned version.

### “Use 2.1.273 everywhere”

The host is already current: direct probe returned `2.1.273 (Claude Code)`.

The image is not:

- [.devcontainer/mise-runtime.toml:63](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:63) declares floating `latest`.
- [.devcontainer/mise-runtime.lock:583](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.lock:583) resolves all six Linux variants to 2.1.270.
- [Dockerfile:655](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:655) copies the runtime lock and installs with `--locked`.

Therefore:

7. Regenerate `.devcontainer/mise-runtime.lock` via `mise run lock-image`; do not hand-edit URLs, asset IDs, or checksums.
8. Confirm all six Claude platform entries resolve to 2.1.273.
9. No `.devcontainer/mise-runtime.toml`, Dockerfile, or workflow syntax change is required to consume the new lock.
10. Correct the stale `http:claude` backend comment at [mise-runtime.toml:59](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:59) if the refreshed lock continues to select `aqua:anthropics/claude-code`.
11. Build and publish through the normal PR/CI image path; the deployed container’s present version was not inspected.

### Documentation and automation debt

12. After runtime verification, version-scope the categorical delivery advice in `feedback_agent_team_delivery_discipline.md`; do not weaken the tracked persistence rule.
13. Add `.claude/types/claude-code.d.ts` to the schema-refresh PR paths at [refresh.yml:518](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/refresh.yml:518). This is latent for 2.1.273 because the bytes are unchanged, but the first real declaration change would otherwise be omitted.
14. Update workflow prose that still says three lockfiles even though the refresh handles four.
15. Do not rewrite historical 2.1.272 reports mechanically.

No changes are required in `hook_guard.py`, `hook_selfcheck.py`, `dag_tick.py`, `memory_index.py`, or their public interfaces.

## Verification required before declaring the traps fixed

1. Background delivery:

   - Run the same isolated prompt under 2.1.272 and 2.1.273.
   - Use real `claude -p --output-format stream-json --forward-subagent-text`.
   - Move the child to background mid-run and require ordered unique `BEGIN`, `MIDDLE`, and `END` markers plus the final report.
   - Foreground execution is the positive control.
   - A copied stream with `END` removed is the assertion fail arm.
   - The missing-usage/model-ID branch needs fault injection or a captured transport replay; an ordinary successful delegation cannot prove it.

2. False-success notifications:

   - Background one command returning 0 and one recording and returning 7.
   - Compare the notification and structured result with the separately captured direct RC.
   - Keep this distinct from result-delivery verification.

3. Permission behavior:

   - Use a disposable sentinel, never a real credential.
   - Direct Read and analyzable Bash arms must retain their expected verdicts.
   - `eval` and `env -C` variants must prompt under 2.1.273.
   - Adding an explicit Bash deny for the sentinel must change that arm to deny.
   - Benign `time -p true` is the allowed control.

4. Manifest integrity:

   - Add a check that a version-tagged source URL matches its recorded version.
   - Reverting only the URL to `v2.1.272` must fail.
   - Version/URL 2.1.273 with the unchanged declaration SHA must pass.

5. Image resolution:

   - Assert every generated Claude lock entry says 2.1.273.
   - Reverting one platform URL to 2.1.270 must fail the consistency check.
   - Confirm the built image’s `claude --version`, not merely command existence.

6. Optional OTEL adoption:

   - Compare `OTEL_LOG_TOOL_DETAILS=0` and `1` against a local collector.
   - Require names only in the enabled arm.
   - Confirm raw prompts, tool arguments, and bodies remain absent.

`★ Insight ─────────────────────────────────────`
The key distinction is between a release-review marker, source provenance, and an executable install. This repository currently has all three, and they advance through different mechanisms.
The two delivery fixes narrow one failure class; they do not convert asynchronous notifications into trustworthy gate evidence or make durable artifacts unnecessary.
`─────────────────────────────────────────────────`

The required Graphify query was attempted first and returned `rc=1` because the read-only sandbox prevented mise from creating its log/temp files. All findings above are therefore identified as local release-note claims, direct repository-file evidence, specialist inspection, or the explicit host-version probe.

One documentation-specialist spawn failed with `no thread with id`; the prescribed history-free retry succeeded.

Specialists spawned:

- `sdlc-documentation-specialist` — documentation staleness and verification design.
- `sdlc-python-specialist` — hooks, runtime consumers, and public-interface controls.
- `sdlc-config-specialist` — settings, provenance, version ownership, and exact delta.
- `sdlc-image-specialist` — devcontainer lock and image install path.
- `sdlc-workflows-specialist` — refresh and CI consumption paths.

No other specialists or agents were spawned.

