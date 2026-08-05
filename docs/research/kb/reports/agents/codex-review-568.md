# Codex adversarial review — #568 ledger + agent-team corrections (verbatim)

**Lens:** `codex exec --ephemeral --sandbox read-only` (GPT-5, diff-only brief — told not to read disk). Invoked 2026-08-05 on the staged diff of PR branch `fix/568-ledger-agent-team-corrections`. Dispositions live in `docs/receipts/568.md`.

---

Verdict: request changes.

1. **High — the hung-node wording violates the brief.** Both the ledger and `docs/agent-team.md` say a hung node is “never recovered” and then say “recovery is attach-triggered.” The latter implies that attaching successfully recovers it, while the cited documentation only describes opening an unresponsive session. State only what is established: the heartbeat emits a stalled event, no automatic recovery occurs, and successful attach-driven recovery has not been demonstrated.

2. **High — dead-worker recovery is generalized beyond the evidence.** “The harness … auto-respawns a dead background node” omits the ledger’s own exclusions: terminal-on-disk, `no_task_contract`, missing cwd, `exec` workers, no flushed messages, and stale workers encountered during `adopt()`. Scope this to an eligible, active `--bg` worker monitored by a live supervisor. The broader “dead-node premise is retired” should become “the premise that no dead-worker detection exists is retired.”

3. **High — “conversation intact” contradicts the later loss row.** The kill/respawn row and correction block say the conversation remains intact, but another appended row says unresolved `tool_use` blocks are dropped, old turns are not resumed, and an unflushed session is unrecoverable. Use “same session with flushed history preserved, subject to interrupted-turn loss” instead.

4. **Medium — the `fallbackModel` evidence is unauditable as written.** The claim says 429 is excluded, while its evidence displays a set containing `429`. That may be an exclusion set, but the row does not show the predicate or call-site polarity. Billing exclusion is also not mapped to a cited condition. This cannot be `CONFIRMED` until the evidence explains how membership suppresses fallback.

5. **Medium — two verdicts are malformed.**

   - “`CronCreate` cannot be a watchdog” paired with `REFUTED (as a candidate)` is logically inverted. Either make the claim “`CronCreate` is a viable watchdog” and mark it `REFUTED`, or keep the current claim and mark it `CONFIRMED`.
   - “`CONFIRMED (code) / not probe-exercised`” is not a clean verdict. The runtime conclusion “unrecoverable” should be separated from the code-shape findings or remain `NEEDS-PROBE`.

6. **Medium — dozens of new `CONFIRMED` rows lack the ledger-required named control arm.** Examples include liveness timing, respawn policy and refusals, the no-watchdog claim, status-line behavior, compact calculations, model-routing claims, and plugin precedence. The strongest negative/universal claims especially need controls: “only surface,” “no pre-flight quota API,” “no native always-on watchdog,” and “every other array setting unions.” A binary symbol or documentation citation is evidence, but not a control arm.

7. **Medium — clear duplicates remain.**

   - `--bg` plus `--print` being a hard error already appears in the retained `claude --bg "<positional>"` row and is appended again.
   - Hidden `claude respawn` existence is already included in the corrected attach row and is repeated later.
   - The auto-compact formula row and the following “`Math.min` is why…” row should be one claim.
   
   The extra respawn row can retain the “conversation preserved/reset semantics” material after removing the duplicate existence claim and correcting “intact.”

8. **Medium — the receipt’s accounting is inconsistent.** The visible diff has 65 appended rows plus two in-place corrections: 67 ledger updates. The receipt instead says “65 landed, 2 as in-place corrections.” It also first describes two #565 fold-ins plus the respawn fact, then explicitly says there were three. State the accounting unambiguously as “67 updates: 65 appended and 2 corrected in place,” and reconcile that with the 66 drafted rows, deduplication, superseded row, and #565 substitutions/additions.

9. **Medium — the receipt is not reproducible or complete yet.** `Verdict`, `Resolved`, and every adversarial-review field remain placeholders. The displayed `grep` command also does not contain the exclusions the prose says were applied, nor the counting operation that produced six hits. Record the exact executed command, exclusions, output/count method, and exit codes. The external `md_budget.py` source should also be pinned to a repository revision if it supports a durable receipt claim.

The two in-place corrections are otherwise internally coherent: the attach correction preserves the overturned claim and explains the bad probe, while the plugin arithmetic is consistent—19 schema fields equals 12 retained plus seven lost, with `isolation` narrowing treated separately. The named retained ledger claims are not contradicted when the new plugin, respawn, environment, and remote-gate rows are read with their intended scopes.
## GitHub repos touched

_None._ The review ran on the staged diff supplied inline; no repository source or docs were fetched by the reviewer.
