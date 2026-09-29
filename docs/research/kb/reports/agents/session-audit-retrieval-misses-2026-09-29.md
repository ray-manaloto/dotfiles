# Session-integrity review: retrieval misses (2026-09-29)

Status: see end of file

Method: Brief S of `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md`.
Session: `dcb0b106-0da4-46a8-9ce7-2e41e8ce5b9e` (native transcript + `subagents/`).
Lane: read-only except this file. Each row: the fact re-derived, cost, and the ONE file that should carry it,
with the exact line to add (coordinator applies as FIX-NOW).

## Findings

Exact lines to apply are in **§ Lines to add (verbatim)** below — kept out of the table so their `|` characters survive.

| # | Sev | Fact the session re-derived | Cost (transcript ordinals) | Carrier (ONE file) | Control arm |
|---|---|---|---|---|---|
| S1 | HIGH | `codex exec review` writes its final message itself with `-o <FILE>`; closed #1296 already recorded "`--json` and `-o` work" for reviews | 25 hand-typed `^codex$` log slices over 0.4-0.6 MB logs ([828] [834] [898] [938] [992] [1047] [1096] [1109] [1494] [1611] [1616] [1745] [1803] [1827] [1850] [1881] [2302] [2422] [2427] [2456] [2978] [3134] [3162] [3189] [3346]); the slice printed the final message twice ([1104] [1612] [2452]) | `.claude/skills/codex-sdlc-team/SKILL.md` § Review tiers (:187) | `codex exec review --help` (codex-cli 0.159.0) lists `-o, --output-last-message <FILE>`; a bogus flag in the same help: 0 hits; #1296 comment. Live arm NOT run (codex usage-limited until 2026-10-03), so UNVERIFIED-live this session |
| S2 | HIGH | `mise run gate -- run <name>` has existed since #1128 (2026-09-15). The gate's own rc (0/1/124/127/2) plus typed JSON and log in `.agent/gate-results/`. Named by no rule, skill or agent (git grep over `.claude` `.agents` `*.md`: 0 hits) | 21 hand-rolled `for g in "mise run lint" …; sh -c "$g"` batches ([636] [805] [936] [1047] [1336] [1553] [1702] [1827] [2080] [2279] [2391] [2761] [2875] [2946] [3134] [3294] [3540] [3614] [3870] [3946] [4035]). One was read as `grep '^rc=' && git commit`, which ran the commit with lint rc=1 ([2302] → [2344] → [2360]) and spent a codex lens on the old SHA | `.claude/rules/verify-before-advancing.md` "Always" block (:23-26). Eager, 121 lines / 7,168 B | `mise run gate -- run pin-actions` rc=0; `mise run gate -- run no-such-gate-zq` rc=2 `not_a_gate`. Side effect: rewrote the gitignored `.agent/gate-results/pin-actions.{json,log}`; my bogus json was removed |
| S3 | MEDIUM | A finished subagent's report is the last non-blank assistant text of the notification's `<output-file>`, a symlink to `subagents/agent-<id>.jsonl` | 13 pasted 12-line python loops ([362] [742] [1318] [1456] [2018] [2075] [2145] [3006] [3412] [3597] [3927] [3993] [4087]) | `.claude/rules/agent-report-persistence.md` rule 1 (:56-59; the PostToolUse(Agent) reminder lands here) | On `tasks/a746b3d4767ac16df.output` the jq extract is 2,637 chars (= [743] "ok 2637") and appears verbatim in `code-review-5df1c5c1-2026-09-28c.md`; the extract plus a fresh suffix does not appear |
| S4 | MEDIUM | Prior-session history is searchable through the `agentsview-finding-history` skill (the daemon is live) | 4 hand-written JSONL miners when Ray asked "review previous sessions" / "go back at least one week" ([163] [171] [183] [435]). [1651] is excluded: it read the brand-new headless child, which the archive may not have indexed | `.claude/skills/session-resume/SKILL.md` | `stale_plan_pointer`, `--since 7d`: 5 matches in 2 sessions. The fresh bogus `qzvxk-no-such-token-81`: 0 |
| S5 | MEDIUM | The lens `<SHA>` must be the literal SHA the commit step printed after its own rc=0 | 2 codex lenses reviewed the WRONG commit. `$(git rev-parse HEAD)` raced a background commit ([1722] → [1745]: reviewed 6b8832c7, not 10e5e806), then followed a hook-refused commit ([2302] → [2344]: reviewed a8e8e8d9 again). About 10 min each, spent from the codex budget that ran out at [3375] | `.claude/skills/codex-sdlc-team/SKILL.md` § Review tiers (beside S1) | [1746] `codex-lens-10e5e806.log: No such file` and [1752] newest lens log = 6b8832c7; [2344] `commit rc=1`, with HEAD printed as `a8e8e8d9` |
| S6 | MEDIUM | In an `install_args` subset job, a bare `mise run` first installs every missing root tool UNLOCKED, writing TOFU checksums into `mise.lock` (#963). So tasks run as `mise run --skip-tools`, and every tool a task shells out to must be listed. `schema_vendor` calls `hk util` (`schema_vendor.py:342-343`), already recorded in `hk-2-0-impact-2026-09-23.md:201` | #963 needed a 225-line diagnosis lane ([2657]). The fix then dropped hk from schema-refresh, caught only by `/code-review` F1 (high) and codex P1: one extra fix round ([3007] [3036] [3057] [3104]) | `.github/actions/setup-mise/action.yml`, the `install_args` description (:10-17). `.github/workflows/AGENTS.md` has no room (11,926 of 12,000 chars) | `git grep -- --skip-tools` hits only `refresh.yml` and one test/contract. In `action.yml`, `skip-tools` = 0 hits while `install_args` = 4 |
| S7 | LOW | Per-platform `mise.lock` entries are dotted-key tables, so tomllib reads `entry["platforms.linux-x64"]` | 1 blind probe: `e.get("platforms")` printed nothing ([2605]), then the dotted-key re-probe ([2612]) | `.claude/skills/lock-image/SKILL.md` (:80-82 give the TOML form only) | `mise.lock:4737` `[tools.aws-cli."platforms.linux-arm64"]`; outputs [2606] vs [2613] |
| S8 | LOW | A Renovate option's type/default at the pinned version is `.definitions.<option>` in `renovate-schema.json` (`.properties.<option>` is only a `$ref`) | 4 greps over `node_modules/renovate/dist` ([2374] [3506]; [3510] empty with single quotes; [3514]) | `.claude/skills/tool-currency-check/SKILL.md` | `updateNotScheduled` → `{"type":"boolean","default":true}` (matches [2396]); `.definitions.noSuchOptionZq` → `null` |
| S9 | LOW | `ship` has no `--body`: the PR body is `gh pr create --fill` (`pr.py:524`) | 2 greps of `pr.py` ([2310] [2316]); the evidence went out as a PR comment instead ([2461]) | `.claude/skills/pr-workflow/SKILL.md` (:24 mentions `--fill` for the title only) | `pr.py:524-526` read directly; `pr-workflow/SKILL.md` has 0 matches for `--body` |
| S10 | LOW | §3c brief coverage = every `Agent` tool_use `input.prompt` in the main transcript | 1 hand-written 15-line python extractor ([4275]) | `.claude/skills/session-handoff/SKILL.md` §3c (:229-238) | 21 descriptions = the 21 `## N.` headings in `session-2026-09-29-agent-briefs.md`; `.name=="AgentZq"` → 0 |
| S11 | CARRIED | Headless `claude -p` in brief mode: stdout is one line; the report is a `SendUserMessage` call (assistant text outside brief mode); the raw stream also holds the injected skill text | 3 runs, a jq rc=5 and a codex P2 ([1585] [1663] [1692] [1697] [1804] [1821]) | `.claude/skills/verify/SKILL.md`, already at :43-50 (#1439) | `fromjson` and `SendUserMessage` at :46, :48, :49. No action |
| S12 | CARRIED | `schema-vendor refresh` must re-derive `schemas/codex-agent.json` | `test_codex_schema` red ([2903]), a manual `codex-schema-generate` ([2933]), then codex P2 ([3057]) | fixed in code (#1445 `_rederive_codex_agent_schema`) | [3129] mutant rc=1, restored rc=0. No action |

## Lines to add (verbatim)

**L-S1**: `.claude/skills/codex-sdlc-team/SKILL.md`. Replace the command at :187 with the first line, and add the second under it:

```text
    `mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> -c 'sandbox_mode="read-only"' -o "$OUT" > "$LOG" 2>&1`
    The final message is `$OUT`, verbatim; persist THAT as the lens report. Never slice `$LOG` at its last `^codex$` line (#1296: `-o`/`--json` work for `exec review`; `--output-schema` is ignored).
```

**L-S2**: `.claude/rules/verify-before-advancing.md`, after :26 (the `dotfiles-setup verify run` bullet):

```text
- Run each as `mise run gate -- run <lint|pytest|verify|lint-docs|pin-actions>`: its rc IS the gate's (0 pass, 1 fail, 124 timeout, 127 tool missing, 2 unknown name), and the typed result + log land in `.agent/gate-results/<gate>.{json,log}`. Never hand-batch `for g in …; sh -c`, and never gate a commit on `grep '^rc='` — it succeeds whenever rc lines EXIST.
```

(Coordinator: `task_plan.md` S28-3 plans a plural `mise run gates`. Reconcile it with this: the singular task already exists.)

**L-S3**: `.claude/rules/agent-report-persistence.md`, appended to rule 1 (after :59):

```text
   The notification's `<output-file>` is a symlink to `subagents/agent-<id>.jsonl`; the report is its last non-blank assistant text: `jq -rsR '[split("\n")[]|fromjson?|select(.type=="assistant")|.message.content[]?|select(.type=="text" and (.text|test("\\S")))|.text]|last' <output-file>`.
```

**L-S4**: `.claude/skills/session-resume/SKILL.md`:

```text
To answer "why did an earlier session do X" or "review previous sessions", use the `agentsview-finding-history` skill first (`agentsview session search "<exact string>" --in tool_input,tool_result --since 7d --exclude-session <this id>`, with its `--server` flags). Hand-parse `~/.claude/projects/*.jsonl` only for a session the archive has not indexed yet.
```

**L-S5**: `.claude/skills/codex-sdlc-team/SKILL.md` § Review tiers, beside L-S1:

```text
    `<SHA>` is the literal SHA your `git commit` printed after its own `rc=0`: never `$(git rev-parse HEAD)` in a job that can start before the commit lands or outlive a hook-refused commit (2026-09-29: two lenses reviewed the previous commit).
```

**L-S6**: `.github/actions/setup-mise/action.yml`, appended to the `install_args` description:

```text
      With a subset, run tasks as `mise run --skip-tools <task>` (#963: a bare
      `mise run` installs every missing root tool UNLOCKED and writes TOFU
      checksums into mise.lock), and list every tool the task shells out to —
      `schema-vendor-refresh` needs `hk` (`hk util`).
```

**L-S7**: `.claude/skills/lock-image/SKILL.md`, after :82:

```text
In Python (`tomllib`) that is the dotted key `entry["platforms.linux-x64"]`, not `entry["platforms"]["linux-x64"]`.
```

**L-S8**: `.claude/skills/tool-currency-check/SKILL.md`:

```text
Renovate option default at the pinned version: `jq '.definitions.<option> | {type, default}' "$(mise where npm:renovate)/node_modules/renovate/renovate-schema.json"`.
```

**L-S9**: `.claude/skills/pr-workflow/SKILL.md`. Replace the comment on :24 with:

```text
mise run ship -- --title "..."     # override the PR title; the BODY is always `--fill` (commit messages, pr.py:524) — put extra evidence in the commit body or `gh pr comment <N>` after ship
```

**L-S10**: `.claude/skills/session-handoff/SKILL.md` §3c:

```text
Enumerate briefs with `jq -rR 'fromjson? | select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and .name=="Agent") | .input | "## \(.description) — `\(.subagent_type)`\n\n````text\n\(.prompt)\n````"' <session>.jsonl`.
```

## Evidence log

### Working notes (transcript ordinals `[N]` = line index in the main jsonl; pass 1 through [3637])

- C1 codex lens final message slices: 25 copies (see S1).
- C2 subagent report extraction loops: 13 copies (see S3).
- C3 headless `claude -p "/session-resume"` brief-mode report: 3 runs + a jq parse failure ([1585] plain stdout held 1 line; [1663] stream-json; [1692] jq rc=5 "Invalid numeric literal"; [1697] `jq -rR 'fromjson?'`; [1804] codex P2: non-brief text form missed).
- C4 lens pinned to `$(git rev-parse --short HEAD)` ran before the commit landed -> reviewed the previous commit ([1722] -> [1745]); and [2302] commit refused by pre-commit -> lens reviewed a8e8e8d9 again.
- C5 gate batch read by `grep '^rc=' log && git commit` -> commit attempted after lint rc=1 ([2302] -> [2344] -> [2360]); fixed by `nonzero: $(grep -c '^rc=[1-9]')` from [2391] on.
- C6 mise.lock per-platform shape: first tomllib probe read `e["platforms"]` -> empty ([2605]); second read dotted keys `platforms.linux-x64` ([2612]).
- C7 schema_vendor shells out to `hk util` (`schema_vendor.py:342-343`); `--skip-tools` removed its only hk install -> /code-review F1 high + codex P1 ([3007] [3036] [3057]).
- C8 codex-agent.json derived from codex-config.json; schema-vendor-refresh did not re-derive -> `test_codex_schema` red ([2903] -> [2933]); now fixed in code ([3104]).
- C9 pwf plugin internals: path glob + `attest-plan.sh --show` output format + hook whitespace set read from plugin source ([492] [748] [998]-[1024]).
- C10 Renovate option defaults read from installed dist: `mise where npm:renovate` then grep; single-quote grep found nothing ([3510]) before double-quote ([3514]).
- C11 prior-session transcript mining with ad-hoc python ([163] [171] [183] [435] [1651]).

## Checked and NOT counted as misses (with the arm that decided it)

- **`gh run view --attempt N --log-failed`** (brief's example): not a miss. After `mise run gha-rerun`, a bare
  `gh run view <id> --log-failed` already reads the LATEST attempt — run 36585903632: default → `fetch first` 1 /
  `Internal Server Error` 0; `--attempt 1` → 0 / 2; `--attempt 2` → 1 / 0 (`.attempt` = 2). The session read attempt 1
  before the re-run ([3762]) and passed `--attempt 2` explicitly after ([3810]); zero wasted calls.
- **Renovate rebase-checkbox PATCH recipe** ([4110]): composed correctly first time (fetch body via `gh api`, assert the
  `- [ ] <!-- rebase-check -->` anchor count == 1 and body > 500 B, PATCH `--input` JSON) — memory
  `feedback_issue_body_edit_needs_anchor_assert` carried the dangerous half. 0 extra cost. OPTIONAL carrier if Ray wants
  it reusable: `.claude/skills/pr-workflow/SKILL.md` § automerge, one line: ``To force a Renovate rebase, tick the
  `- [ ] <!-- rebase-check -->` box: fetch `gh api repos/<o>/<r>/pulls/<N> --jq .body`, assert that anchor occurs exactly
  once, then `gh api -X PATCH repos/<o>/<r>/pulls/<N> --input <{"body": …}.json>`.``
- **Where `schema_vendor` shells out to hk**: counted inside S6 (the carrier is the `install_args` doc, not a new
  schema_vendor docstring — `refresh.yml:535` already comments it at the one site).
- **`mise run --skip-tools` existence**: one `mise run --help | grep` ([2688]); the native flag was found on the first
  probe — the miss is the *consequence* documented in S6.
- **`echo ====` in 7 subagents** (a0ac3629, a2d1db9b, a472b5fc, a61a79bc, a66d4fad, a6a6422e, ac1415a8): each denied by
  `hook_guard` (#1388) at a cost of one call; the guard IS the carrier (subagents cannot read memory). Brief R territory.
- **`timeout` shim probe** (cold reviewer abe12c28 [64]): verifying a claim in the diff under review, not a re-derivation.
- **renovate 44.118.1 `re2.node` missing** ([2796]-[2948]): diagnosed as "still installing", unconfirmed — a
  dismissed-error question (Brief M), not retrieval.
- **pwf internals** (`attest-plan.sh --show` format, hook whitespace set; [492] [748] [998]-[1024]): each read answered a
  review finding and the answer now lives in `handoff_check.py` code; nothing for a doc to carry.
- **`gh pr diff <N> -- <path>`** ([3744]): `gh pr diff` takes no path filter and `2>/dev/null` hid the error; one call.
  Generic gh knowledge, below the bar.
- **host `ssh -T` "Permission denied (publickey)"** ([3817]-[3843]): a transient that cleared on retry; no fact to carry.

## Method

Main transcript `dcb0b106-…jsonl` flattened to one line per tool call/result (scratchpad `main.txt`, 1,124 rows) and
read end to end; every tool error in the 30 `subagents/agent-*.jsonl` listed with its call. Pattern counts measured by
exact-substring scans of Bash `input.command` (S1/S2/S3). Each proposed line was checked against the target file's
current text (none already present; S11/S12 already carried) and, where it contains a command, the command was run
with a positive and a fresh negative arm. Transcript ordinals `[N]` are 0-based line indexes of the main jsonl.

Status: COMPLETE (2026-09-29)

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #1296 (exec review `-o`), run 36585903632 logs, source/skills/rules read
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline `$CC/sub-agents.md` (subagent transcript path) grep
