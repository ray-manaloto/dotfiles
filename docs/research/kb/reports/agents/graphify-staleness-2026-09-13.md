# graphify reports `fresh` on a 76-commit-stale graph (2026-09-13)

Found while answering: "did we store the plan-attest `--show` defect in graphify memory?"

## Answer: no, and it could not have been

`graphify-out/graph.json` built **2026-08-31 15:17**.
`python/src/dotfiles_setup/plan_attest.py` created **2026-09-03 00:10** (`b707fba`, #914).
The module postdates the graph by three days.

Since the build: **76 commits, 504 files changed, 16 new `python/src/**/*.py` modules.**

## Symbol probe, both arms

| symbol | hits in graph.json | arm |
|---|---|---|
| `plan_attest_main` | 0 | subject |
| `claude_doctor_main` | 0 | subject (added #1044, 2026-09-13) |
| `setup_parser` | 76 | control: known present |
| `handle_pr` | 21 | control: known present |
| `zqvbnx7` | 0 | control: invented known-absent, fresh this session |

Probe discriminates. The negatives are real.

## Why `graphify-health` says `fresh`

`graphify_health` — `python/src/dotfiles_setup/graphify.py:224-243` — checks five things:

1. `graph.json` exists
2. it parses
3. schema valid
4. installed runtime == `0.9.53`
5. `_receipt_problem` — if a `build-receipt.json` is present, verify it

**Nothing compares the graph to the source tree.** No mtime check, no commit check, no
file-set check. The only `STALE` return is `:200`, reachable only through the receipt.

`_receipt_problem`'s own docstring (`:145-187`) states this repo never writes a receipt and
the branch is "currently unreachable in practice". Confirmed: `graphify-out/build-receipt.json`
does not exist.

So on the staleness axis `graphify_health` is a check that can only pass —
`.claude/rules/probes-need-a-control-arm.md`, inside the subsystem whose job is retrieval.

Note the docstring already reasons carefully about a DIFFERENT can-only-pass check (the
removed rebuild stamp, for builder-version drift) and removed it for exactly this reason.
The age axis was never covered by either.

## Why it bites rather than sits idle

- `.claude/rules/graphify-first.md`: on `fresh`, "use `mise run graphify-query -- ...` and
  cite returned source paths."
- A PreToolUse hook fires on every Bash call: "MANDATORY: graphify-out/graph.json exists.
  You MUST run `mise run graphify-query` before grepping raw files."

Both route agents into an August graph and call the result authoritative.

## Corroborating tell

Query `plan_attest_main` resolved start nodes to `plan()`, `main()`, `Attestation` — the
symbol is absent. It also reported `setup_parser()` at `L1491`; the working tree has it at
`main.py:1835`. Line drift is the cheap visible symptom of the same staleness.

## Not yet established

- Whether the `--show` parse defect itself was known before today (two lanes searching).
- Whether `graphify-update` has been run at all since 2026-08-31 (no evidence found in the
  2026-09-* handoffs; absence not yet control-armed).

## GitHub repos touched

_None._ All evidence is local to `ray-manaloto/dotfiles`.
