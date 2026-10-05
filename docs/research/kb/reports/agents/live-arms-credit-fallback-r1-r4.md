# Live arms R1–R4 — credit-fallback @ e90833fd (2026-10-04 ~21:28–21:45 CDT)

Run by lane `credit-fallback-finish` from the worktree `.claude/worktrees/credit-fallback`, base spec
`spec-credit-fallback-rev2.1.md` §5.3 as amended by `spec-credit-fallback-projection-r1.md` §5.4 (R4 expects the U1
literal, block once). Every command's output and rc were captured to a file under the job scratchpad
(`$CLAUDE_JOB_DIR/tmp/rarms/`); excerpts below are verbatim. No key value was printed (presence flags only).
Firecrawl was at zero credits throughout (Ray's ruling), so the 402 condition was live.

Fnox prefix used where noted: `fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults
--no-daemon --non-interactive exec --`.

## R1 — substitution (Firecrawl 402 → Serper)

`<fnox> mise run research-fanout -- "mise tasks" --sources firecrawl-search --out …/r1` → **rc=0**

```
firecrawl-search  ok  7 items  2.142s  [provisional: firecrawl-search via serper (credits-exhausted)]
```

Manifest attempts: `firecrawl-search skipped (reason "Error: Request failed with status code 402")`, then
`serper ok http_status 200`. Row `route: serper`, `provisional: true`.

**No-fnox arm (Claude-side path).** In this shell `SERPER_API_KEY` and `SERP_API_KEY` are ABSENT
(`FIRECRAWL_API_KEY` SET), i.e. the Q9 `env_true` change (#1656) is not live in this shell's environment:

```
firecrawl-search  skipped  0 items  1.199s  [skipped: credits-exhausted; no fallback succeeded; serper: prerequisite; serpapi: prerequisite]
```
rc=1 — the expected behaviour when both fallback keys are missing (Q3: a credit-only skip stays rc 1).

## R2 — genuine failure still fails

`FIRECRAWL_API_KEY=<fresh-nonce invalid value> mise run research-fanout -- "mise tasks" --sources firecrawl-search
--out …/r2` → **rc=1**

```
firecrawl-search  error  0 items  0.562s  [process-failed]
```

Manifest reason `exited 1: Error: Request failed with status code 401`, `attempts: []` — no fallback attempted, not
provisional. The arm is not VOID: the reason is 401/auth, not credits, so the override reached the child. Control:
R1's identical command with the real key answered 402 and fell back.

## R3 — mirror (Firecrawl 402 → webclaw)

`mise run research-fanout -- --probe-out …/r3.json --mirror-url https://mise.jdx.dev/tasks/ --mirror-path …/r3.md`
→ **rc=0**

```
mirror  {"bytes": 5801, "code": "", "http_status": 0, "path": "…/r3.md", "provisional": true, "rc": 0, "route": "webclaw", "url": "https://mise.jdx.dev/tasks/"}
```

File written, 5801 bytes. **Control** (fresh-nonce 404 path `https://mise.jdx.dev/ed2f6ec1677-no-such-page/`): probe
rc=0 (the probe process always exits 0), row `code: "process-failed"`, `route: webclaw`, `provisional: false`,
`rc: 1`, `bytes: 0`, and **no file** written.

## R4 — strict receipt end-to-end through the real gate script

### Strict-five run

`env -u FORCE_COLOR NO_COLOR=1 <fnox> mise run research-fanout -- "mise tasks" --repo jdx/mise --strict-five
--request-id r4turn3 --last30days-plan plan.json --out <tmp HOME>/.codex/research-coverage/r4sess/r4turn3` →
**rc=0**

```
github-issues  ok  10 items  0.795s
github-discussions  ok  10 items  1.158s
github-releases  ok  10 items  3.426s
exa  ok  10 items  0.212s
context7  ok  5 items  5.004s
firecrawl-developer  ok  10 items  0.205s
firecrawl-search  ok  7 items  1.656s  [provisional: firecrawl-search via serper (credits-exhausted)]
last30days  ok  10 items  15.734s
strict-five  pass  [provisional: firecrawl-search via serper (credits-exhausted)]
```

⚠️ **Why `env -u FORCE_COLOR NO_COLOR=1`.** The first strict run (same command, ambient env) failed
`strict-five fail [context7 did not complete]`: the Claude Code shell sets `FORCE_COLOR=3`, ctx7 0.5.12 then colours
piped output, and `_context7_library_id` (unchanged since #1391, on main) captures the trailing `\x1b[39m` into the
library ID → `Library "/jdx/mise…" not found`. Reproduced with `--repo astral-sh/uv` too. Control:
`NO_COLOR=1 ctx7 library uv | od -c` gives a clean ID, the ambient form does not. Pre-existing and independent of
this branch; filed as **#1699**. (A first R4 attempt also failed last30days on a hand-written plan missing `intent` —
a fixture error in this lane, fixed with `{"intent":"how_to","freshness_mode":"evergreen_ok","cluster_mode":"none",
"subqueries":[…]}`.)

### Hook events piped into `scripts/codex-research-gate.py` (HOME = the temp home)

| Event | Output | rc |
|---|---|---|
| UserPromptSubmit `r4turn3` | `additionalContext` 729 chars, contains `strict-five-v2` | 0 |
| Stop `r4turn3`, answer does not name the route | `{"decision": "block", "reason": "Research receipt PROVISIONAL (credit-exhausted provider). Name PROVISIONAL and each of these in the answer: firecrawl-search via serper."}` | 0 |
| Stop `r4turn3`, same answer, `stop_hook_active: true` | `{}` (block once) | 0 |
| Stop `r4turn3`, answer names `PROVISIONAL` + `firecrawl-search via serper` | `{}` | 0 |
| UserPromptSubmit `r4turn` (the failed context7 receipt) | `additionalContext` 727 chars, `strict-five-v2` | 0 |
| Stop `r4turn` (fail arm) | `{"decision": "block", "reason": "Research coverage failed: context7 did not complete. Run the strict-five research command for request r4turn and verify all five provider groups. If a provider cannot run, start the final answer with `RESEARCH INCOMPLETE:` and report its exact blocker; do not claim the research is complete."}` | 0 |

The provisional block reason equals the projection spec's U1 literal and carries only validated identifiers (N2): no
provider body, stderr or diagnostic text.

**Not covered here:** the live Codex hook runs the `~/.codex/tools/dotfiles-research-gate` clone, so this behaviour is
inert in Codex until that clone is updated after merge (O1 / research-gate-sync).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue searches; filed #1697, #1698, #1699
- [jdx/mise](https://github.com/jdx/mise) — R4 `--repo` target (issues/discussions/releases arms)
- [astral-sh/uv](https://github.com/astral-sh/uv) — second R4 attempt `--repo` target (ctx7 reproduction)
