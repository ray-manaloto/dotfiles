# Codex adversarial review — receipt #565 (2026-08-05)

Lens: codex-reviewer (codex exec --ephemeral --sandbox read-only), prompt = receipt +
mechanically-abridged result.json. Verbatim output below; dispositions live in
`docs/receipts/565.md`.

1. **REAL** — “**The fleet gate is NOT a remote gate… reads only `CLAUDE_CODE_DISABLE_AGENT_VIEW` and… `disableAgentView`… no statsig/GrowthBook**.” The raw JSON tests only environment-variable behavior. It contains no binary excerpt, call graph, settings-key arm, GrowthBook arm, or server-side configuration arm. It cannot establish the absence of a remote decision path.

2. **REAL** — “**the off-state is a local, reviewable decision**.” Even a locally read settings key may be supplied through centrally managed settings. The raw evidence exercises only an environment variable, so it establishes neither the origin nor reviewability of every off-state.

3. **REAL** — “**With the gate off the whole surface goes**.” Live evidence covers only `logs`, `agents --json`, and `--bg`. It does not exercise `attach`, `stop`, `kill`, `respawn`, `rm`, `--background`, `--routine`, `/background`, `/subtask`, or `/fork`. “Whole surface” therefore depends on unprovided static evidence and is presented more broadly than the raw run supports.

4. **REAL** — “**A5… no job created**” and “**rejected before any job is created**.” The A5 raw record contains only argv, rc, stdout, and stderr. It has no immediately-before/after roster or census measurement. Empty final cleanup cannot exclude creation followed by automatic or later cleanup.

5. **REAL** — “**`"false"` does NOT trip… falsy strings parse as off**.” Only the literal string `"false"` was tested. This does not cover other conventionally falsy inputs such as `"0"`, `"no"`, `"off"`, the empty string, or an unset variable.

6. **REAL** — “**The terminal-state predicate is `state ∈ {done, failed, stopped} AND tempo ≠ "active"` (plus no `queuedPrompt`) — confirmed… by a 6/6 live enumeration.**” The live arms test only `tempo:"idle"` and `tempo:"active"` and never vary or even report `queuedPrompt`. They also do not exercise the separately acknowledged `tengu_bg_revival_guard`. Six selected cases corroborate those cases; they do not live-confirm the stated exact predicate or its sufficiency.

7. **REAL** — The receipt is internally incomplete about suppression conditions. The verdict and final consequences present `state` + `tempo` + no `queuedPrompt` as sufficient, while the Sources section says suppression additionally requires the `tengu_bg_revival_guard` gate. A default-true guard remains a failure mode unless its state is captured and its false arm is tested.

8. **REAL** — “**The framework CAN signal completion by file write**” / “**completion-by-file-write works**.” B1–B3 show that forged terminal fields prevented respawn after a subsequent `kill -9`. They do not show that the write alone settles a live node, that a consumer recognizes task completion, or that the state is semantically valid—the original `detail` still says the agents await clarification. The supported conclusion is narrower: these writes suppressed crash recovery under the observed conditions.

9. **REAL** — “**Results — every arm on-prediction**” overclaims B1–B3. Their predictions include outcomes `done`, `failed`, and `killed`, but every sampled roster outcome is `null` and then the record disappears. The Notes explicitly concede that the settle outcome mapping was not observed live. Therefore the full predictions did not receive live confirmation.

10. **REAL** — “**`killed` and `blocked` are never terminal**.” The raw run shows one `killed/idle` and one `blocked/idle` write did not suppress respawn in version 2.1.222. “Never” requires the unprovided static predicate and does not follow from one observation of each state.

11. **REAL** — “**`claude respawn <id>` on a stopped/settled node restores the conversation**.” By the receipt’s own account, C tested only an already-settled `done` node. `claude stop` was then a no-op: the state remained `done` and the roster remained empty. Recovery from an actually `stopped` node was not exercised.

12. **REAL** — “**`attempt` resets to 1 by construction**.” The planned attempt-2 setup explicitly “never happened.” Respawning a record whose prior observed attempt was already 1 and then seeing 1 cannot distinguish reset from preservation. The claimed construction depends on static evidence not present in the raw JSON.

13. **SUSPECT** — “**same transcript continues**” and “**conversation intact**.” The supplied raw evidence is truncated during A3 and contains no C record, transcript sizes, post-respawn exchange, or context-dependent answer. Even same `sessionId` and file growth would prove reuse/append behavior, not necessarily semantic restoration of conversation context.

14. **SUSPECT** — “**all 8 pre-existing background records intact**.” The raw evidence proves that the same eight IDs appear before and after and includes a derived `pre_existing_intact:true`; it does not expose record contents or fingerprints. “All IDs preserved” is supported, while byte- or field-level intactness is not independently auditable from the supplied data.