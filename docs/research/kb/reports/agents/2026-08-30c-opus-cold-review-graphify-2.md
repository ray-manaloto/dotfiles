# Cold review — `git diff origin/main...c90bcf2` (graphify branch, round 2)

Reviewer: opus-cold-review-graphify-2 (Opus 5). Read via `git show`/`git diff`
against `325271c`, `6d71b8b`, `853a506`, `c90bcf2`. No intent framing was
supplied and none was sought. The working tree was on a different branch
throughout; nothing was checked out or switched. All line numbers are
`git show c90bcf2:<path>`.

**"No findings" would NOT be honest.** Two HIGH, four MEDIUM, seven LOW, one
INFO below. One axis genuinely came back clean and is reported as such
(fail-closed enumeration).

---

## Findings

### HIGH-1 | The runtime stamp cannot detect the drift it was built to detect; the rule prose claims it can | `python/src/dotfiles_setup/graphify.py:230`, `.claude/rules/graphify-first.md:22`

`_runtime_stamp_problem`'s docstring (`graphify.py:237-245`) and
`graphify-first.md`'s new bullet both claim the stamp lets health "tell a graph
built by the drifted PATH binary from one built by this repo's pin". It cannot,
for two independent reasons:

1. **A PATH-built graph carries no stamp at all.** The only writer is `update()`
   (`graphify.py:473-489`), reached only through
   `mise run graphify-update` → `uv run --project python`. Someone who runs bare
   `graphify update` (the exact behaviour the rule forbids and the stamp claims
   to catch) writes nothing, and `graphify.py:248-249` returns `None` — "absent
   is not a fault" — so health reports **FRESH** for a 0.9.53-built graph on any
   clone that has never run the mise task.
2. **The stamped value can never be the drifted one.** Probed live, same process:
   `uv run --project python` prepends
   `/Users/rmanaloto/.../python/.venv/bin` to `PATH`; `graphify --version` under
   it → `graphify 0.9.42`, and `importlib.metadata.version("graphifyy")` →
   `0.9.42`. So `_builder_version()` and `_runtime_version()` resolve the *same*
   binary by construction. (Control arm: the PATH shim outside `uv run` is
   `/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.53/bin/graphify`
   → `graphify 0.9.53`, so the probe discriminates.)

Compounding: `graphify_health` short-circuits at `graphify.py:322`
(`if runtime != "0.9.42": VERSION_DRIFT`) **before** `_binding_problem`, so the
`stamp_version != runtime` compare at `graphify.py:263` can only ever run with
`runtime == "0.9.42"`. The branch is therefore reachable in exactly one real
scenario the docs do not name — **a pin bump** (pyproject + the `0.9.42` literal
move; an old stamp then correctly reports STALE). That is a useful check. It is
not the advertised one.

The binding that *is* real is the sha256 half: a graph mutated or rebuilt by
another binary **after** a stamped build is caught (`graphify.py:259`). The gap
is the un-stamped first build.

### HIGH-2 | The test asserting HIGH-1's scenario builds a fixture production cannot produce | `tests/test_graphify.py:710`

`test_graphify_health_rejects_runtime_stamp_version_mismatch` hand-writes
`{"runtime_version": "0.9.53", ...}` and its docstring names "the exact scenario
HIGH-2 in the 2026-08-30 cold review named". Per HIGH-1 no code path can write
that value: `update()` is the sole writer and always resolves 0.9.42. This is
`probes-need-a-control-arm.md` rule 8 — a fully-armed probe on a fixture the
world cannot reach. The test passes; the scenario stays uncovered.

The test *does* discriminate the production change (revert `_runtime_stamp_problem`
→ FRESH ≠ STALE), so it is not tautological. It is mis-captioned, and the
caption is what a later reader will trust.

### MEDIUM-1 | `_builder_version` ignores its exit code and stamps `"unknown"`, re-creating the STALE-forever defect round 1 fixed | `python/src/dotfiles_setup/graphify.py:460-470`

```python
result = _run(["graphify", "--version"], cwd=project_root)
return result.stdout.strip().removeprefix("graphify ") or "unknown"
```

`result.returncode` is never read. Any `--version` failure, or a version that
prints to stderr, yields `""` → `"unknown"`, which `update()` writes into the
stamp without comment. Every later `graphify_health` then returns **STALE**
(`"graph was built by graphify unknown…"`) for a perfectly good graph, until
someone re-runs the task successfully. Verified by evaluation:
`''.strip().removeprefix('graphify ') or 'unknown'` → `'unknown'`.

Format fragility is the same defect at a different angle: a click-style
`graphify, version 0.9.60` does not match the `"graphify "` prefix and stamps
the whole string → permanent STALE. Today's 0.9.42 prints `graphify 0.9.42`
(probed), so this is latent, not live. No test covers either path.

### MEDIUM-2 | `hook_guard_main`'s "fails open on ANY problem" is false; it catches only `OSError` | `python/src/dotfiles_setup/graphify.py:521-538`

The docstring says *"Fails open — rc 0, no output — on ANY problem"*. The
`try`/`except` at `graphify.py:531-534` covers `OSError` only.
`subprocess.run(..., text=True)` raises `UnicodeDecodeError` (a `ValueError`, not
an `OSError`) if graphify's stdout is not decodable in the ambient locale, and
`sys.stdout.write` can raise on a closed pipe. Neither is caught. The only thing
preventing an actual traceback in production is the bash `|| true` at
`scripts/graphify-hook-guard.sh:27` — i.e. the fail-open guarantee lives in the
layer the commit message says the logic was moved *out of*. Any future caller of
`hook_guard_main` without that wrapper inherits an unguarded crash.

### MEDIUM-3 | A successful rebuild can still crash `mise run graphify-update` | `python/src/dotfiles_setup/graphify.py:473-489`, `211-227`

`update()` runs the build, then unguarded calls `_builder_version()` (a
subprocess — `FileNotFoundError` if graphify vanished between calls) and
`_write_runtime_stamp()` (`Path.write_text` — `OSError` on a read-only or full
`graphify-out/`). Either propagates through `graphify_update_main`
(`graphify.py:491-502`, no try/except) as a traceback, discarding a rebuild that
already succeeded. `write_text` is also non-atomic: an interrupted write leaves a
truncated stamp, which `graphify.py:250-252` then reports as **CORRUPT** —
blocking every query until the user works out that deleting a file they have
never heard of is the fix. No test covers any of this.

### MEDIUM-4 | Every hook test stubs `_run`, so the one thing that can silently kill the nudge is untested | `tests/test_graphify.py:806-855`

`graphify hook-guard` reads the tool-call JSON from **stdin**
(`graphify/cli.py:615`, `sys.stdin.buffer.read()`). Correctness therefore depends
on stdin surviving `bash` → `uv run` → `dotfiles-setup` → `subprocess.run`.
All three `hook_guard_main` tests monkeypatch `_run`, so none exercises it. A
regression here produces *no output and rc 0* — indistinguishable from graphify
deciding not to nudge.

I armed it live rather than assume:

| Arm | Command | Result |
|---|---|---|
| Positive | `printf '{"tool_name":"Bash","tool_input":{"command":"grep -rn foo ."}}' \| _run(['graphify','hook-guard','search'])` | 269 bytes, full `_SEARCH_NUDGE` |
| Negative control | same, `{"command":"ls -la"}` | empty, rc 0 |

So it works today. Nothing in the suite would notice if it stopped
(`.claude/rules/real-integration-evidence.md`).

### LOW-1 | The wrapper anchors its own path to `$CLAUDE_PROJECT_DIR` but resolves the project relatively | `scripts/graphify-hook-guard.sh:27`

`bash "${CLAUDE_PROJECT_DIR:-.}/scripts/graphify-hook-guard.sh"` (settings.json:56,66)
invokes a script whose body is `uv run --project python …` — relative to *cwd*,
not to the anchored dir. Probed from the knowledge-base working directory:
`error: Failed to spawn: dotfiles-setup … (os error 2)`, rc=2, swallowed by
`|| true` → nudge silently gone. Fail-open, so no outage; but the fix is one
token: `--project "${CLAUDE_PROJECT_DIR:-.}/python"`.

### LOW-2 | `test_graphify_health_rejects_graph_missing_edge_collection` passes identically with and without the change | `tests/test_graphify.py:484`

With neither `links` nor `edges` present, `_edges_field` (`graphify.py:122`)
returns `"edges"` — the same literal the pre-change code hard-coded. Detail
string, status and assertion are byte-identical before and after. It is a valid
guard against the fallback over-accepting, but it does not cover the change it
sits beside; only `test_graphify_health_accepts_links_keyed_graph:452` does.

### LOW-3 | `test_graphify_health_accepts_matching_runtime_stamp` also passes if stamp checking is deleted entirely | `tests/test_graphify.py:690`

Asserts `FRESH`, which is the outcome with *no* stamp logic at all. It is a
"does not false-positive" guard, not coverage of the mechanism.

### LOW-4 | One health test depends on the ambient venv rather than monkeypatching the runtime | `tests/test_graphify.py:452`

`test_graphify_health_accepts_links_keyed_graph` asserts `FRESH` without
`monkeypatch.setattr(..., _runtime_version, lambda: "0.9.42")`, unlike every
sibling added in the same commit (`:305`, `:690`, `:710`, `:740`, `:857`). It
passes only because the venv really is `graphifyy==0.9.42`, so it fails for an
unrelated reason on any environment drift.

### LOW-5 | `graphify-first.md` misattributes `version_drift` to the stamp | `.claude/rules/graphify-first.md:23-25`

> "that stamp is what `version drift`/`stale` are actually detecting"

`VERSION_DRIFT` is `runtime != "0.9.42"` at `graphify.py:322` — computed from
`importlib.metadata` alone, before any stamp is read, and it *short-circuits*
the stamp check. The stamp contributes to `STALE` only. In an eager rule this is
a fact a future session will act on.

### LOW-6 | ~3× per-tool-call latency on Bash|Grep|Read|Glob | `scripts/graphify-hook-guard.sh:27`

Measured warm, same shell: new `uv run --project python dotfiles-setup graphify
hook-guard search` = **0.270s** total; previous `mise exec -- graphify hook-guard
search` = **0.094s**. Not a defect, but it is paid on every matching tool call,
and a cold `uv` sync would be far worse. `uv` also takes a venv lock, so parallel
tool calls serialise here.

### LOW-7 | A fixture captioned "real graphify output, captured 2026-08-30" is abridged | `tests/test_graphify.py:775-783`

The `read_nudge` string omits the real `_READ_NUDGE`'s trailing sentence
("This rule applies to subagents too — include it in every subagent prompt
involving code exploration.", `graphify/cli.py:39-41`). Assertions still hold;
the provenance claim does not.

### INFO | `GraphifyStatus.INCOMPLETE` is unreachable — pre-existing, not introduced here | `python/src/dotfiles_setup/graphify.py:55`

`git grep -c "GraphifyStatus.INCOMPLETE" c90bcf2 -- python tests` → **0**.
Control arm: `GraphifyStatus.STALE` → 3 (graphify.py) + 5 (tests), so the probe
discriminates. Same result at `origin/main`, so this diff neither caused nor
worsened it. The enum value is only ever surfaced as the *exception class*
`GraphifyIncompleteError`, never as a `HealthResult.status`.

What *did* change: `STALE` used to be reachable trivially (missing receipt, i.e.
always). It is now reachable only through the stamp paths — see HIGH-1 for how
narrow that is.

---

## Fail-closed enumeration (PreToolUse) — clean, and I looked

Asked to enumerate ways this could block every tool call. I found none, and say
so rather than manufacture one:

| Vector | Verdict |
|---|---|
| Script exits non-zero | Impossible: `\|\| true` on the only command, terminal `exit 0`, `set -uo pipefail` **without `-e`** |
| `set -u` on an unset `$1` | Defaulted: `kind="${1:-search}"` (`:23`) |
| Missing script / missing `uv` | rc 127 or the `command -v` guard → falls through to `exit 0`; 127 ≠ 2, so non-blocking |
| Python traceback | Escapes `except OSError` (MEDIUM-2) but is absorbed by `\|\| true` |
| Malformed JSON on stdout (partial write, `uv` chatter) | Non-JSON PreToolUse stdout is context, not a decision → allow |
| Hook timeout on a cold `uv` sync | Cancelled, non-blocking |
| `permissionDecision: "deny"` passthrough | Real, but that is graphify's `_READ_DENY` strict mode, env-gated (`GRAPHIFY_HOOK_STRICT`) and documented at `scripts/graphify-hook-guard.sh:16-19`. Not accidental |
| Recursion (hook spawns a tool call) | None — the child is a raw subprocess, not a Bash *tool* call |

## Shell→Python rewrite equivalence

`sed 's/`graphify query/`mise run graphify-query --/g'` (853a506) vs
`str.replace` (`graphify.py:504-518`): both global, both un-anchored, both
one-pass. Differences that matter:

- **Coverage is complete against the real source.** Every bare mention in
  graphify 0.9.42's nudge constants is `` `graphify query `` (cli.py:23, 33, 47,
  63, 78) or `` `graphify update` `` (cli.py:48) — both spellings are handled.
  `graphify explain`/`graphify path` are deliberately left alone (no mise task
  exists), which the test asserts.
- **Empty input**: `rewrite_hook_nudge("")` → `""`, and `hook_guard_main` returns
  before printing (`graphify.py:534-535`). Handled.
- **Non-UTF8**: `sed` is byte-transparent; `text=True` is not — see MEDIUM-2.
- **Partial match**: `` `graphify queryfoo `` → `` `mise run graphify-query --foo ``.
  Contrived; no such string exists upstream.

## Claims from the diff's own prose, verified

| Claim | Verdict | Evidence |
|---|---|---|
| Shell wrapper byte-equivalent in size to its pre-feature state | **TRUE for lines**, not bytes | `wc -l` per ref: origin/main **30**, 325271c 30, 6d71b8b 30, **853a506 36**, c90bcf2 **30**. The intermediate commit overran the budget and the final restored it. Content differs entirely, so byte counts are not equal; `bash_budget.py:106` is line-based, so the gate is satisfied — with **zero headroom** (file is exactly at 30) |
| No lint suppression remains | **TRUE** | The `# shellcheck disable=SC2016` added at `853a506:scripts/graphify-hook-guard.sh:28` is absent from c90bcf2. Grep over all seven changed non-doc files finds only three pre-existing `SC2086`s in `mise.toml` (lines 409, 1068, 1135), none touched by this diff |
| The version-mismatch path genuinely fails on a mismatch | **TRUE in the unit, MISLEADING in production** | `tests/test_graphify.py:710` really asserts STALE and would pass FRESH if reverted — but see HIGH-1/HIGH-2: the mismatch state is unreachable for the documented PATH-drift scenario |

## Prose cross-checks

- `.claude/CLAUDE.md:39-41`, `.claude/agents/claude-code-expert.md:284-288`,
  `.claude/agents/staleness-auditor.md:122-127` and
  `.claude/rules/graphify-first.md:10-21` now agree on "never a bare `graphify`".
  One cosmetic split: CLAUDE.md writes `mise run graphify-query` while the other
  three write `mise run graphify-query -- "<question>"`. **Both work** — probed:
  with and without `--`, mise passed the question through identically
  (`dotfiles-setup graphify query 'what …'` in both cases). No finding.
- **Budget**: `.claude/rules/graphify-first.md` goes 18 → **38 lines / 2,231
  bytes**. `md-size-budgets.md:93` gives `rule_unscoped` 200 lines / 24,000
  bytes. Comfortably inside. No finding.
- `doc_refs.py:148-152` adds `graphify-out/build-receipt.json` to
  `_ALLOWED_ABSENT`, which is *required* because `graphify-first.md:27-28` now
  names that path. Correct and necessary. `runtime-stamp.json` is never named
  with a path shape in tracked prose, so it needs no entry. `graphify-out/` is
  gitignored at `.gitignore:64`, so the new stamp cannot be committed.

## Races and semantics of the stamp

- **Build→stamp window**: `update()` runs `graphify update`, then a *second*
  subprocess (`graphify --version`), then reads the bytes it stamps
  (`graphify.py:483-488`). graphify's own hook-driven rebuild takes a per-repo
  lock (`_rebuild_code(..., block_on_lock=True)`, `cli.py:2113`) which is
  released before `update` returns — so a rebuild starting inside that window
  binds the stamp to bytes that are already being replaced. Narrow, real, and
  the resulting state is STALE (safe direction), not a false FRESH.
- **What the stamp does not assert**: it binds *bytes ↔ builder version*, never
  *bytes ↔ current source*. `update()` stamps whenever rc==0 and graph.json
  exists, including a no-op rebuild. graphify does `sys.exit(1)` on
  "Nothing to update or rebuild failed" (`cli.py:2129-2134`), which covers the
  obvious case; whether its fewer-nodes refusal also exits non-zero is
  **UNVERIFIED** (would require reading `graphify/watch.py::_rebuild_code`).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — cwd control arm for LOW-1; `kb_setup.graph.GraphifyBuildReceipt` is the type `_receipt_problem` decodes.
- graphify / `graphifyy` — **not a GitHub repo I read**; source consulted was the installed wheel at `python/.venv/lib/python3.14/site-packages/graphify/cli.py` (0.9.42). No upstream repo was fetched.
