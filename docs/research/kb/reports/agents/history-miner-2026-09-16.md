# History Miner — recurring mistake patterns across dotfiles sessions

**Date:** 2026-09-16 · **Lane:** `history-miner` (read-only archive crawl)
**Corpus:** AgentsView remote daemon (`http://127.0.0.1:8080`), `--project dotfiles`,
`--include-children`, `--exclude-system`, `--since 3m`.
**Excluded:** `52714f36-fd54-4ad0-92f4-6cfe4f9e439d` (parent conversation) and
`agent-ahistory-miner-f29008b4a86d9343` (this lane's own echoes).

## Tooling notes (load-bearing — read before any number below)

1. **Semantic/hybrid is UNAVAILABLE on this archive.** Every `--hybrid`/`--semantic`
   call fails with
   `fatal: semantic search not available: enable [vector] in config.toml and run 'agentsview embeddings build'`.
   All findings are `--fts`. Announced, not silently downgraded.

2. **`--exclude-system` emits INVALID JSON.** With that flag the daemon returns
   snippets containing raw control characters (U+0000–U+001F) unescaped, so `jq`
   aborts: `parse error: Invalid string: control characters ... must be escaped`.
   Worked around with `json.JSONDecoder(strict=False)`. **agentsview bug, worth filing.**

3. **FTS is token-AND, and quoting gives true phrase match.** Armed both ways:
   `purple giraffe elevator` → **0 hits** (so it is not OR), and
   `"notification lied"` → 39 distinct sessions vs unquoted `notification lied` → 60.
   Every count below uses a **quoted phrase**. Unquoted multi-word probes are
   near-worthless here (`my probe was broken` → 282 sessions, i.e. four common tokens
   co-occurring) and are **not** reported as evidence.

4. **Control arm, invented fresh for this run and deliberately not reused:**
   `zzqqwwvv-nonexistent-token` → **0 hits** with the exclusion list applied, and
   exactly **1** without it — that one hit being this lane's own probe echo. So the
   probe discriminates *and* the exclusion list is doing real work.
   ⚠️ This control string is now IN the corpus by virtue of this file. **The next run
   must invent a new one.**

5. **Counts are distinct PARENT sessions, never hits.** `--limit 500` caps; anything
   returning exactly 500 is marked `CAPPED` and excluded from frequency claims. A hit
   marked `codex:` or `agent-` is **subordinate** (lane/subagent) and is counted
   separately, as supporting evidence only.

6. ⚠️ **Residual confound, stated rather than hidden.** This repo's eager rules and
   `MEMORY.md` are injected into sessions, so rule *vocabulary* is everywhere. The
   phrases below were chosen because they are **admission-shaped and absent from the
   rule text** (the memory hook reads "notification can lie"; "notification **lied**"
   is an event report, not a quote). Two of the three classes were additionally
   confirmed by reading a message window, cited below. Un-windowed counts are a
   **floor on discussion**, not a proven count of commissions.

## Searches

- `"reported a negative finding without running a control arm"` (hybrid) → **failed**, embeddings absent. Forced the FTS fallback.
- `"the notification claimed exit code 0 but the log showed rc=1"` (hybrid) → **failed**, same.
- `control arm` / `false negative` / `notification lied` / `poll loop` (fts, unquoted) → 261/236/64/124 distinct sessions, several **CAPPED@500**. Discarded: token-AND over common words, and dominated by rule text.
- `purple giraffe elevator` (fts) → 0. Established FTS is AND, not OR — made quoting meaningful.
- `"notification lied"` / `"a false negative"` / `"probe was broken"` / `"hand-rolled poll"` / `"waiting on Renovate"` (fts, quoted) → the usable instrument. Counts below.
- `zzqqwwvv-nonexistent-token` (fts) → 0. Control arm.

## Strong Matches

### A. `5140cb5c-d8fe-41de-af8b-38ff8a33ecf4` (dotfiles, claude, #459-490 @484, 2026-08-31) — **class 1, commission + self-catch**

A `Monitor` probe published a hard negative to the user:
`LANE NEVER LAUNCHED after ~120s — codex exec never appeared` (#478).
At #482 the assistant reversed it: *"My liveness probe was wrong — codex-cli 0.151.0
doesn't spawn `codex exec`."* At #484 it ran the control arm explicitly:

```
pgrep -f 'codex exec' >/dev/null && echo "'codex exec' MATCHES" \
  || echo "'codex exec' does NOT match — the probe was broken, not the lane"
```

and recorded at #488: *"I published 'LANE NEVER LAUNCHED' off it — **a false negative,
rule-1 shape from `probes-need-a-control-arm.md`, and the same shape as that rule's own
`agent-*.jsonl` example**."*

Two things make this the strongest single piece of evidence in the sweep:
- the defect recurred **in the exact shape the eager rule uses as its own headline
  example**, with the rule loaded — so the rule did not prevent it; and
- **the repo's own doctrine taught the broken probe**: *"the orchestration doctrine's
  own text still prescribes `pgrep -f 'codex exec'` — stale against this CLI version."*

Correct discriminator recorded in the same entry:
`ps aux | grep "[C]ODEX_COMPANION_SESSION_ID='<session-id>"`.

### B. `701c7573-ff53-4c43-a394-330809152bbe` (dotfiles, claude, #3-203 @42, 2026-09-13) — **class 2, caught by the file-rc discipline**

The harness emitted
`<status>completed</status> … Background command "Ship the branch as a gated PR" completed (exit code 0)` (#40).
The assistant at #42: *"the ship failed (real `rc=1`, **notification lied again**)."*

The catch was **mechanical, not attentive**: at #35 the ship was launched as
`… > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`, and #37/#39 polled that file in-turn for
`^rc=`. The file said `rc=1`; the notification said 0. The word *"again"* is itself
recurrence evidence.

### C. `agent-arev-telemetry-494c0c7860da10b6` (**subordinate**) → parent `6c26be81-8260-48af-b7c8-58eee272c87c` (#60-71, 2026-09-14) — **class 3, quantified, then partially REFUTED**

The lane reported from `.agent/command-audit.md` across **50 sessions / 19,226 Bash
commands**: `bypass=0` (clean), `one_off=4,363` (22.7%), and within that
**`while [` = 217 hand-rolled polling loops**, which it called *"the exact anti-pattern
`gh-cli-watch.md` bans"* and ranked as the top remediation candidate.

Per the subordinate-hit rule I corroborated against the parent. The parent **verified
every number at source** (#61-67: mtimes, `command-audit.md:6-13`, `:39-43` — all
CONFIRMED) and then **overturned the ranking** at #69-71:

> ⛔ *Correction 1 — the TOP candidate is refuted; it conflates two rules.*
> `.claude/rules/long-running-command-hangs.md:40-43` **PRESCRIBES** that exact shape
> for Mac-side container ops: `deadline=$((SECONDS+540)); while [ $SECONDS -lt $deadline ]; …`

So the 217 is a real, cross-session, measured count — but it is **not** 217 violations.
It is a mixture of the shape the repo bans (`gh` polling, which has native `--watch`)
and the shape the repo **mandates** (in-turn log polling of a local long-running task,
because backgrounded Mac-side `mise run` gets reaped).

Same report also measured **159 guard fail-opens, 158 of them `guard-error-rc=1`** —
159 windows in which `hook_guard` enforced nothing (#343).

### D. Frequency table (quoted phrases, distinct **parent** sessions, uncapped)

| Phrase | Parent sessions | Total distinct (incl. lanes) | Date span |
|---|---:|---:|---|
| `"a false negative"` | **22** | 75 | 2026-08-02 → 2026-09-15 |
| `"notification lied"` | **17** | 39 | 2026-08-30 → 2026-09-15 |
| `"probe was broken"` | **12** | 38 | 2026-08-02 → 2026-09-15 |
| `"hand-rolled poll"` | 3 | 13 | 2026-08-08 → 2026-09-14 |
| `zzqqwwvv-nonexistent-token` (control) | **0** | 0 | — |

All four content rows are **well under the 500 cap**, so these are measurements, not
floors-from-truncation. They remain a floor on *commission* (see confound 6).

## Synthesis

**All three classes recur across distinct sessions. None is a one-off.**

1. **Class 1 — negative findings published off an un-armed probe: RECURRING.**
   12 parent sessions say "probe was broken", 22 say "a false negative", spanning
   2026-08-02 → 2026-09-15 — i.e. it kept happening for six weeks *with
   `probes-need-a-control-arm.md` eager in every one of those sessions*. Session A is
   the proof-grade instance, and it is damning precisely because it reproduced the
   rule's own canonical example. **The rule is not failing to be read; it is failing to
   bind at the moment a 0-result is about to be reported.**

2. **Class 2 — trusting the harness notification over the log: RECURRING, and already
   mechanically defeated where the discipline is applied.**
   17 parent sessions, 2026-08-30 → 2026-09-15, and session B's own wording is
   *"lied **again**"*. The important asymmetry: in B the lie changed nothing, because
   the command had been launched in the `> "$LOG" 2>&1; echo "rc=$?"` shape. The failure
   mode is not "agents believe notifications" — it is "nothing forces the file-rc shape,
   so an agent that skips it has no second source."

3. **Class 3 — polling: recurring in volume (217 loops / 50 sessions), but the naive
   remediation is WRONG.**
   This is the subtlest finding and the one most likely to be re-derived incorrectly by
   a future session: two of this repo's own rules point in opposite directions on the
   same syntax. `gh-cli-watch.md` bans hand-rolled polling of `gh` (native `--watch`
   exists); `long-running-command-hangs.md` rule 2 **prescribes** in-turn `while [ … ]`
   log polling for Mac-side `mise run`, because backgrounding those gets them reaped.
   A blanket `while [` gate would deny the prescribed shape — and a telemetry lane
   already proposed exactly that before the parent caught it.

**Meta-pattern spanning all three (the one I would actually act on):** every instance
is *"a cheap signal was accepted in place of the authoritative one"* — `pgrep` output
in place of a discriminating liveness check, a notification summary in place of the
log's own `rc=`, a `grep` in place of `--watch`'s exit status. The repo's rules all
say "read the authoritative artifact". What is missing is anything that makes the
cheap signal *unavailable*.

## What would prevent each MECHANICALLY

Ordered by how enforceable it actually is. ⚠️ Note first that **`hook_guard` fails open
and did so 159 times in 50 sessions** (evidence C) — so anything that must never fail
open belongs in `permissions.deny`, per the repo's own #343 doctrine, not in the guard.

| Class | Mechanical fix | Why this one |
|---|---|---|
| 1 | **`hook_guard` rule denying the known-broken liveness shape** `pgrep -f 'codex exec'` / `pgrep -f 'codex exec'`-alikes, redirecting to a canonical `mise run lane-liveness -- <session-id>` wrapping the companion-shell discriminator. | The general "did you arm your probe?" is undecidable, but **this specific probe** is a known-broken string that has already burned one session and is still prescribed by stale doctrine. A command-line string is exactly what the guard can see. Pairs with `mise-tasks-only.md`'s "new redirect = new `_RULES` entry + a test + a table row". |
| 1 | **A `require_tokens`-style contract on the orchestration doctrine text** asserting it names `CODEX_COMPANION_SESSION_ID` and *not* `codex exec`. | Session A's own note: the doctrine *still taught the broken probe*. Fixing the agent without fixing the teacher guarantees recurrence. Use a **contiguous multi-line token**, per `project_session_2026-09-08c` — a bare substring check is satisfied by the string surviving anywhere. |
| 2 | **Strip or annotate the `(exit code N)` text in `<task-notification>` summaries** at the hook layer, so the untrustworthy number is never presented. | Removes the lying artifact at source rather than asking 17 sessions' worth of agents to remember to distrust it. Strictly better than a reminder: there is nothing left to misread. |
| 2 | **`hook_guard` rule requiring the file-rc shape on a backgrounded gate launch** — deny a background `mise run <gate>` that lacks `> <file> 2>&1` + `echo "rc=$?"`. | Session B proves the shape works; nothing currently forces it. The guard already denies `<gate> \| tail` for the same reason (`long-running-command-hangs.md` rule 3), so this is the missing sibling of a rule that already exists. |
| 3 | **A NARROW `hook_guard` rule: deny `while`-loop polling whose body calls `gh` (`gh pr checks`, `gh run`), redirect to `--watch` / `mise run land`. Explicitly ALLOW `while [ $SECONDS -lt $deadline ]` over a local log.** | This is the discrimination the telemetry lane got wrong and the parent had to correct by hand. Encoding it in the guard settles it once; leaving it in prose guarantees the next session re-litigates it. `bypass=0` today only means *no rule matches* `while [` at all — there is currently nothing to bypass. |
| all | **Raise the 159 guard fail-opens (#343) before adding any of the above.** | Every new guard rule inherits the fail-open. Adding rules to a guard that silently enforced nothing in 159 windows buys less than the rule count suggests. |

## Gaps / Follow-ups

- **Commission vs discussion is not fully separated.** The 22/17/12 counts are sessions
  where the phrase appears in an assistant message; I windowed 3 and all 3 were genuine
  commissions, but I did not window the other 48. Next narrower probe: search
  `--in tool_result` for `Monitor`/`pgrep` tool outputs that returned empty **and** were
  followed within the same `ordinal_range` by a user-facing negative claim.
- **Class 3 violation/compliance split is unmeasured.** The 217 is a mixture. The next
  probe should partition `.agent/command-audit.md`'s `while [` rows by whether the loop
  body calls `gh` (violation) or greps a local log (prescribed) — that single number
  decides whether the guard rule above is worth writing.
- **Telemetry is stale.** `.agent/telemetry/` covers only 2026-08-26 → 08-29; the
  command-audit corpus is 50 sessions with no date bound stated. Both numbers in
  evidence C are therefore un-refreshed since 2026-08-29.
- **Not searched:** the `knowledge_base` project, and anything before 2026-08-02
  (`--since 3m` bound). The class-1 date span starts exactly at the window edge, which
  is a hint the pattern predates the window rather than beginning there.
- **agentsview bug to file:** `--exclude-system` produces unparseable JSON (note 2).

## GitHub repos touched

_None._ This artifact was produced entirely from the local AgentsView archive and this
repository's own working tree; no external repository source or documentation was read.
