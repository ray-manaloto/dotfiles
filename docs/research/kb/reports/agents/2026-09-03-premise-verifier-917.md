# Premise verification — spec #917 (InstructionsLoaded load observer)

- **Lane:** premise-verifier (read-only), 2026-09-03
- **Spec under review:** `spec-917.md` (scratchpad, read fresh and in full)
- **Project root:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
- **Security tier:** the record writer interpolates a harness-supplied `session_id`
  into a filesystem path, and parallel subagent processes append to one file.
- **Headline:** 1 row REFUTED (it breaks the spec's own verification command),
  2 corrections, 7 MISSING premises.

## 1. Per-row verdicts

| # | Premise | Verdict | Evidence |
|---|---|---|---|
| 1 | `InstructionsLoaded` is a settings.json hook event; fires on CLAUDE.md and `.claude/rules/*.md` load, at session start and on lazy load | **CONFIRMED** | `hooks.md:56` (event table). The substantive sentence is `hooks.md:1263`; the spec's `:1261` is the `### InstructionsLoaded` heading |
| 2 | Payload fields `file_path`, `memory_type`, `load_reason`, `globs`, `trigger_file_path`, `parent_file_path`; `load_reason` ∈ 5 values | **CONFIRMED** | `hooks.md:1273-1278`. Independent second route: the matcher table at `hooks.md:323` lists the identical five load reasons |
| 3 | The matcher runs against `load_reason`, so omitting it captures all reasons | **CONFIRMED** | `hooks.md:1265` verbatim, incl. the `"path_glob_match\|nested_traversal"` example |
| 4 | No decision control; exit code ignored | **CONFIRMED** | `hooks.md:885` ("Exit code is ignored"), `:1025` (grouped with Setup/SessionEnd under "None"), `:1294`. `:1263` adds "It runs asynchronously for observability purposes" |
| 5 | Common fields incl. `session_id`, `cwd`, `transcript_path`, and (in subagents) `agent_id`/`agent_type` | **CONFIRMED, with correction** | `hooks.md:728` (`session_id`), `:737-742` (`agent_id`/`agent_type`). See Correction B |
| 6 | Installed Claude Code is 2.1.259 | **CONFIRMED** | `claude --version` re-run this session → `2.1.259 (Claude Code)` |
| 7 | `_SETTINGS_WIRING` maps an event to required command substrings + required matcher tokens, at `hook_selfcheck.py:85` | **CONFIRMED exactly** | `python/src/dotfiles_setup/hook_selfcheck.py:85` — the annotated assignment, type `tuple[tuple[str, tuple[str, ...], tuple[str, ...] \| None], ...]` matches the spec verbatim. Three entries at `:92-102` (PreToolUse, SessionStart, SessionEnd) |
| 8 | `_unanchored_hooks(settings)` fails any hook command lacking `CLAUDE_PROJECT_DIR`, across the whole hooks block, at `:196` | **CONFIRMED** | `hook_selfcheck.py:196-218`; the whole-block loop is `:207-217`; called from `check_settings_wiring` at `:192`. The spec's proposed command carries `${CLAUDE_PROJECT_DIR:-.}` → satisfied |
| 9 | `.claude/settings.json` wires PreToolUse, PostToolUse, SessionStart, SessionEnd and no `InstructionsLoaded` | **CONFIRMED** | Enumerated by parsing the JSON and printing every key of the `hooks` block (by SHAPE, not by grepping the names I expected — `feedback_enumerate_dont_assert_the_list`). Result: `['PreToolUse', 'PostToolUse', 'SessionStart', 'SessionEnd']` |
| 10 | Exactly 2 of 26 `.claude/rules/*.md` carry `paths:` frontmatter | **CONFIRMED; control-arm number corrected** | `ci-local-parity.md`, `md-size-budgets.md`. See Correction A |
| 11 | `paths:` is a YAML list of quoted globs under a `---` block | **CONFIRMED** | `.claude/rules/md-size-budgets.md:1-8` — five globs; the block closes at `:8`, not the spec's `:7` |
| 12 | `main.py` imports every subcommand module eagerly at top level | **CONFIRMED** | Top-level imports run past `:100` in a 2508-line file; the timing in row 13 settles the consequence |
| 13 | Startup: stdlib `uv run` 0.04s; `import dotfiles_setup.main` 0.27s | **CONFIRMED, reproduced** | stdlib `0.04 / 0.04 / 0.04`; `import dotfiles_setup.main` `0.26 / 0.24 / 0.23`. **New and load-bearing:** bare `import dotfiles_setup` = `0.04` ×3 — `__init__.py` imports only `pathlib`, so `python -m dotfiles_setup.instructions_observer` genuinely stays on the cheap path and pays no package-init tax |
| 14 | `md-budget` reports 64 instruction files checked | **CONFIRMED verbatim; the INFERENCE drawn from it is refuted** | `uv run --project python kb-setup md-budget` → `md-budget: 64 instruction files checked; eager context ~127482 bytes (~31870 tokens) every session`, rc=0. See M3 |
| 15 | `workflow.bash-logic-enforcement` is the precedent contract shape (P) | **CONFIRMED** | `python/verification/suites.toml:1362-1381`. The call-site trap the spec cites in C8 is in `workflow.apt-pins-enforcement`'s description at `:1863`, not in `bash-logic-enforcement`'s |
| E rows | `ts`, `session_id`, `file_path`, `memory_type`, `load_reason`, `globs`, `trigger_file_path`, `parent_file_path`, `agent_id`, `agent_type` provenance + PII class | **CONFIRMED**, two amendments | Consistent with the confirmed payload contract. Amendment 1: `globs` is documented "Present only for `path_glob_match` loads" (`hooks.md:1276`) — it is absent/None for the other four reasons. Amendment 2: Correction B |
| A row | Harness delivers the payload on stdin as a single JSON object | **CONFIRMED — upgrade from ASSUMED** | `hooks.md:724` verbatim: "Hook events receive these fields as JSON… For command hooks, this JSON arrives via stdin." This is a doc-level settlement of the uniform contract; keep §5's live arm anyway, since the doc does not prove *this build* honours it |

## 2. REFUTED

### `verify run --name <suite>` is not a real flag. It is `--suite`.

Spec §5 line 178 reads:

```
uv run --project python dotfiles-setup verify run --name workflow.instructions-observer-wiring
```

That command fails for every implementer. Both arms run, output captured to a
file and the real `rc` recorded (never a piped tail):

| Arm | Command | Output | rc |
|---|---|---|---|
| Positive | `uv run --project python dotfiles-setup verify run --suite workflow.bash-logic-enforcement` | `PASSED workflow.bash-logic-enforcement` / `1 passed, 0 failed, 0 skipped` | **0** |
| Negative | `uv run --project python dotfiles-setup verify run --name workflow.bash-logic-enforcement` | `dotfiles-setup: error: unrecognized arguments: --name workflow.bash-logic-enforcement` | **2** |

Definition: `python/src/dotfiles_setup/main.py:865`

```python
run_parser.add_argument("--suite", help="Run a specific suite by name")
```

The parser also accepts `--category` (repeatable) and `--json`; there is no
`--name` on `verify run` or on `verify list`.

**Correct invocation for §5:**

```bash
uv run --project python dotfiles-setup verify run --suite workflow.instructions-observer-wiring
```

The probe discriminates: the same command shape returned rc=0 on `--suite` and
rc=2 on `--name`, so this is not a broken-probe null.

## 3. Corrections

### Correction A — the control-arm number on the 2-of-26 row does not reproduce

The spec states: *"control arm: the same command shape counting `^# ` returned
24, so the probe discriminates."*

Measured this session: **all 26** rule files carry an H1 (`grep -l '^# '
.claude/rules/*.md | wc -l` → 26), not 24. The `paths:` arm returns 2
(`ci-local-parity.md`, `md-size-budgets.md`), confirmed two ways — a
frontmatter-aware scan requiring `---` on line 1 with `paths:` in the first 12
lines, and a plain `grep -l '^paths:'`; both return the same 2 files.

**The conclusion stands** (2 vs 26 discriminates just as well as 2 vs 24) but
the published figure is wrong. Do not carry `24` forward — an inherited number
repeated without re-derivation becomes someone else's unverified note wearing
your name (`probes-need-a-control-arm.md` rule 6).

### Correction B — `agent_type` is NOT subagent-only

The spec's E row says `agent_id` / `agent_type` are "present only inside
subagents", following `hooks.md:740-742`. That is the doc's claim; this repo
already holds a **bundle-source read that contradicts it**.

`docs/research/kb/reports/agents/wf-dag-context-gate.md:115-127` enumerated every
hook-payload construction site in the shipped binary by shape (64 hits) and
found they all spread one base builder, `$m()`:

```js
function $m(e,t,r){
  let n=t??Ot(), o=r?.agentType??nU(), i=r?.options?.mainLoopModel, s=r?.getAppState?.().effortValue;
  …
  return {session_id:n, transcript_path:jH(n), cwd:Mt(), prompt_id:YPt()??void 0,
          permission_mode:e, agent_id:r?.agentId, agent_type:o, effort:a};
}
```

`agent_type` is `r?.agentType ?? nU()` — a **fallback**, so it can be non-null on
the main thread. `agent_id` is `r?.agentId`, genuinely undefined off-subagent.

**Consequence for the implementer:** record both fields as the spec says, but do
not use a non-null `agent_type` as the discriminator for "this record came from
a subagent". Use `agent_id` for that, and say so in the report module.

The same source confirms two undocumented bonuses the spec could use free:
every payload also carries `prompt_id` and `permission_mode`.

## 4. MISSING premises

These are facts the spec relies on without stating them. Ordered by severity.

### M1 — Nothing states where `project_root` comes from on the hot path (SERIOUS)

`build_record(payload, *, project_root: Path, now: str)` takes `project_root` as
a parameter and `observe_main` never says where it gets one. The write path
`.agent/instructions-loaded/<id>.jsonl` is relative.

**Hooks do not run in the project root — they run in the session's current
directory.** That is documented in this repo, in the file the spec already
cites, as the root cause of #343:

`python/src/dotfiles_setup/hook_selfcheck.py:105-111`
> Claude Code runs hooks "in the current directory", not the project root, and
> exports `${CLAUDE_PROJECT_DIR}` so a hook can find its own repo anyway. A hook
> command that names a bare relative path therefore resolves against whatever
> directory the session happens to be in — and silently fails open there […]
> That is #343: 125 denied Bash calls executed unchecked while the cwd was a
> sibling repo.

The spec anchors the `--project` argument with `${CLAUDE_PROJECT_DIR:-.}` and
leaves the **write** path unanchored. Failure mode: the moment a session works
in a sibling repo, records land in `<sibling>/.agent/instructions-loaded/`, and
the never-fired report then reads a corpus with holes and reports rules as
never-fired that fired fine. That is a **false positive in exactly the
direction that makes the observer worse than nothing** — it manufactures the
signal it exists to detect.

Note also that payload `cwd` is *not* the project root either (`$m()` sets it
from `Mt()`, the current directory), so reading it from the payload does not fix
this.

**Required:** state that the observer derives its root from
`os.environ.get("CLAUDE_PROJECT_DIR")`, with a documented fallback when unset
(the spec's own `:-.}` default already concedes it may be), and add a test that
runs the observer from a foreign cwd and asserts the record still lands under
the project root.

### M2 — No `__main__` guard is specified

`python -m dotfiles_setup.instructions_observer` executes the module as
`__main__`. §3's interface list gives only:

```python
def observe_main(argv: list[str] | None = None) -> int: ...
```

A module with that function and no entry guard runs to completion having done
nothing, exits 0, and **passes C2's fail-open control arm for the wrong
reason** — malformed stdin produces rc=0 and no file, exactly as required, and
so does valid stdin. `feedback_test_right_answer_wrong_reason`.

**Required:** `if __name__ == "__main__": raise SystemExit(observe_main())`, and
the §5 positive arm (valid payload → record lands) is what discriminates.

### M3 — The ~64 fanout figure conflates two different file sets

C1's cost argument reads: *"With ~64 instruction files (`md-budget` reports 64
checked) that is ~2.5s vs ~17s of CPU per session start."*

The 64 is real (row 14) but it is **`md-budget`'s** set, not
`InstructionsLoaded`'s. `md-budget` checks instruction markdown by load class,
which includes `SKILL.md` files — **76 tracked** in this repo. `InstructionsLoaded`
fires only on "a `CLAUDE.md` or `.claude/rules/*.md` file" (`hooks.md:56`,
`:1263`); it does not fire on skills.

Measured tracked counts:

| Class | Count | Fires `InstructionsLoaded`? |
|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | 11 | yes |
| `.claude/rules/*.md` | 26 | yes |
| `SKILL.md` | 76 | no |

Eligible upper bound is **37**, and fewer at session start (nested CLAUDE.mds
load on traversal, not eagerly).

**The C1 conclusion survives comfortably** — 37 × 0.23 ≈ 8.5s vs 37 × 0.04 ≈
1.5s, still a 6× difference and still an argument for `python -m` + stdlib-only.
But the stated number is wrong and would become a cited figure. Correct it to
"~37 eligible instruction files (11 CLAUDE.md/AGENTS.md + 26 rules); `md-budget`'s
64 counts SKILL.md files this event does not fire on."

### M4 — C4's atomicity claim needs a size bound

C4 says: *"write ONE `json.dumps(...) + "\n"` in a single `write()` call so each
record is one atomic-enough append."*

One Python `write()` is **not** one `write(2)` syscall. `open(path, "a")` returns
a buffered text writer (default buffer 8192 bytes); a payload larger than the
remaining buffer space is flushed in **multiple** syscalls, and `O_APPEND`
atomicity is per-syscall. Two subagents interleaving mid-record produce a
corrupt JSONL line, which the report side will hit as a `json.JSONDecodeError`
on a line it cannot attribute.

Records are normally small, but **nothing in the spec bounds them**: `globs`
carries a rule's own `paths:` list (arbitrary repo content), and `file_path` /
`trigger_file_path` / `parent_file_path` are bounded only by `PATH_MAX`.

**Required:** either (a) open in binary unbuffered mode and issue one
`os.write(fd, blob)`, or (b) state a maximum line length, enforce it by
truncating or dropping the record, and test at the boundary. Say which.

### M5 — C3 covers a hostile `session_id` but not an absent one

C3 handles `/`, `..`, NUL, absolute prefixes, and length. It does not say what
happens when `session_id` is **missing or `None`**. The signature
`session_filename(session_id: object) -> str` hints the author was thinking
about it (`object`, not `str`), but the constraint never states it.

**Required:** state that a missing, `None`, or non-string `session_id` takes the
same fixed fallback (`unknown`) as a fully-sanitized-away one, and test all
three shapes, not just the traversal strings.

### M6 — Every timing is a warm-cache steady-state number

The 0.04s / 0.27s figures (and my reproduction of them) were measured with
`uv`'s environment already synced. If `python/uv.lock` has changed since the last
run, the first `uv run` of a session re-resolves and re-syncs, and the **first
`InstructionsLoaded` hook of that session pays it**.

This is not a blocker — the event is async and its exit code is ignored
(`hooks.md:885`, `:1263`), so a slow first hook degrades nothing. But "0.04s" is a
steady-state figure, and C1 should say so rather than let a later reader treat
it as a worst case.

### M7 — Nothing states whether `.claude/settings.json` is schema-validated here

Adding an unfamiliar event key to `settings.json` would be rejected by a stale
vendored JSON schema, if one existed. **It does not.** `schemas/sources.toml`
vendors exactly three schemas — `mise.json`, `ruff.json`, `typos.json` — none of
them Claude Code settings. Nothing in `hk.pkl` JSON-schema-validates
`.claude/settings.json`.

What *does* trigger: `.claude/settings.json` is in the `agnix` hk step's glob
(`hk.pkl:503`), so editing it makes `mise run lint-docs` / the agnix step run.
Non-blocking, but it means the settings edit is not a "free" change from the
gate's point of view.

Verified as clear; recorded so a later session does not spend the probe again.

## 5. The five extra items I was asked to hunt

| Item | Finding |
|---|---|
| Does `uv run --project <dir> python -m <module>` work given the package layout? | **YES.** `uv run --project python python -c "import dotfiles_setup, pathlib; print(...)"` resolves to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup` — the project is installed editable into the uv venv, so `src/` layout is not an obstacle. Control arm that the `-m` form itself works under this wrapper: `uv run --project python python -m json.tool --help` → rc=0. **Caveat: see M2** — the form works, but the module needs a `__main__` guard to do anything. |
| Does anything already write under `.agent/instructions-loaded/`, or would it collide? | **No collision.** Zero hits for `instructions-loaded`, `instructions_observer`, `instructions_report` or `InstructionsLoaded` across `python/`, `mise.toml`, `.claude/settings.json`, `tests/`. The only matches anywhere are prior research prose under `docs/research/kb/reports/agents/` (see §6). The live `.agent/` tree holds `command-audit.md`, `kb/`, `logs/`, `notepad.md`, `plans/`, `state/`, `telemetry/` and a pile of `session-review.md.*` JSON — no `instructions-loaded/`. `dotfiles-setup --help` lists 64 subcommands and `instructions-report` is not among them; `mise.toml` has no `[tasks.instructions-report]`. |
| Does `.gitignore` cover the new `.agent/` subdirectory? | **YES, by a blanket rule.** `.gitignore:106` is bare `.agent/`. Probed rather than assumed: `git check-ignore -v .agent/instructions-loaded/probe.jsonl` → `.gitignore:106:.agent/`, rc=0. No new ignore entry needed. |
| Is `verify run --name <suite>` real? | **NO — it is `--suite`.** Full detail and both arms in §2. `main.py:865`. |
| Is `dotfiles-setup hook selfcheck` the real subcommand spelling? | **YES.** `main.py:1285` registers the `"hook"` parser; `:1295` registers `"selfcheck"` under it; dispatch at `:1892-1893` → `hook_selfcheck_main(project_root)`; top-level dispatch table entry at `:2338`. Bonus for the implementer: `hook_selfcheck_main` runs five named checks — `settings-wiring`, `script-syntax`, `guard-decisions`, `pretooluse-endtoend`, `plan-attest-deny` (`hook_selfcheck.py:485-489`). Only `settings-wiring` will see the new `_SETTINGS_WIRING` entry; `script-syntax` `bash -n`s wired `.sh` scripts only (`:424-429`), so a `python -m` command adds no surface there and needs no new wrapper script. |

Also confirmed while hunting: `mise run token-check` (referenced by C8) is real —
`mise.toml:1295` `[tasks.token-check]`.

## 6. Prior art the spec does not cite

Two artifacts already in this repo cover ground the spec re-derives or leaves
open. Both are worth handing to the implementer lane.

- **`docs/research/kb/reports/agents/cc-expert-lazy-context.md`** — a **live
  3-arm `InstructionsLoaded` probe against this repo** at Claude Code 2.1.224,
  proving `paths:` frontmatter genuinely lazy-scopes a rule, on a disjoint-glob
  fixture that arms both directions (`mise.toml` → `ci-local-parity` only;
  `python/CLAUDE.md` → `md-size-budgets` only; `lint.py` → neither). It also
  records the five load reasons byte-scanned out of the shipped binary at 2.1.222
  and 2.1.224 (`:31-32`, `:111-116`, `:481`). This is the existence proof that the
  whole #916 premise (scoping works) holds, and it is *older evidence than the
  observer this ticket builds* — the observer's value is the never-fired
  direction, not the does-scoping-work direction.
- **`docs/research/kb/reports/agents/wf-dag-context-gate.md:115-127`** — the
  bundle-source payload construction. This is what settles Correction B, and it
  also tells the implementer that `prompt_id` and `permission_mode` are free in
  every payload if the report side ever wants them.

## 7. Summary for the architect

**Must fix before dispatch:**

1. §5 line 178: `--name` → `--suite` (REFUTED, breaks the spec's own command).
2. M1: state where `project_root` comes from, and test from a foreign cwd. This
   is #343's defect class pointed at the observer's own output.
3. M2: specify the `__main__` guard, or the module is a silent no-op that passes
   the fail-open arm.
4. M3: correct 64 → ~37, or the figure propagates.

**Should fix:**

5. M4: bound the record line, or write unbuffered binary.
6. M5: state the absent-`session_id` fallback.
7. Correction B: `agent_id`, not `agent_type`, discriminates a subagent record.
8. Correction A: drop the `24`; the control arm is 26.

**Informational:** M6 (warm-cache timings), M7 (no schema validation; agnix does
glob settings.json), §6 (prior art).

Everything else in the PREMISES block verified CONFIRMED against a fresh read,
and the one `A` row upgrades to CONFIRMED on `hooks.md:724`.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the
  vendor hook documentation (`hooks.md`) read offline from the knowledge-base
  source tree, for every `L` row about `InstructionsLoaded`, its payload, its
  matcher and its decision control.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under change: `hook_selfcheck.py`, `main.py`, `suites.toml`, `.claude/settings.json`,
  `.claude/rules/`, `mise.toml`, `hk.pkl`, `schemas/sources.toml`, `.gitignore`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  `sources/agent-harness-docs/docs/claude-code/hooks.md`, the offline vendor doc
  corpus (`research-doc-sources.md` step 00).
