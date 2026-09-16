# Consolidated session review — 2026-09-14f

Reviewing branch `docs/session-2026-09-14e-reports` (commits `023580d..8f78891`)
before `/clear`. Three lanes: the codex SDLC team (dispatcher + 3 specialists),
a Claude Opus discovery sweep, and a gate-runner.

## Gate matrix (real rc read from files, not pipes)

| Gate | rc | Note |
|---|---|---|
| `mise run lint` | 0 | clean |
| `uv run --project python pytest tests/ -x -q` | 0 | 3146 passed, 11 deselected |
| `mise run verify` | **1** | `config.schema-vendor-drift` — see B2 |
| `mise run lint-docs` | 0 | clean |
| `mise run codex-agent-parity` | 0 | 12 lanes paired |
| `mise run codex-schema-check` | 0 | but the check cannot fail — see B3 |
| `mise run pin-actions` | 0 | clean |

## BLOCKERS

### B1 — 18 archived reports rewritten by a bare `ruff format`

`uv run --project python ruff format` with **no path argument**, run from the
repo root by the previous session, walked the whole tree and reformatted Python
fences inside archived markdown. Its transcript records `19 files reformatted,
1097 files left unchanged`.

Armed on a pristine copy of `premise-sweep-2026-09-14.md`:

```
443:        ["mise", "lock", "--bump", *tools],     <- pristine, matches image.py
443:(["mise", "lock", "--bump", *tools],)           <- after ruff format
```

Some rewrites change MEANING, so reports now quote code that does not exist in
the source they cite. hk is NOT the culprit: `hk-common.pkl` `excludePaths`
already lists `docs/research/kb/**`.

Rule: `.claude/rules/agent-artifact-conventions.md` rule 8 ("Do not normalize
records"); `.claude/rules/agent-report-persistence.md` rule 4 (verbatim).

### B2 — the vendored OpenAI codex schema is a newline-mutated copy

```
upstream https://learn.chatgpt.com/docs/config-schema.json  2e1fcf1c...  203671 B
recorded schemas/sources.toml                                2e1fcf1c...  (CORRECT)
committed schemas/codex-config.json                          b28908a7...  203672 B
```

JSON content identical; the committed file has a trailing newline (`...7d0a` vs
`...7d`). `schemas/` is absent from `hk-common.pkl` `excludePaths`, so
`Builtins.newlines` normalised a vendored record. Same class as B1.

The file is CLEAN in git and the committed blob also hashes `b28908a7`, so it
was never "corrupted later" — the recorded sha never matched the committed
bytes.

### B3 — `mise run schema-vendor-refresh` cannot run for codex

Armed: rc=1, `ValueError: schema_vendor: no source-URL template for tool
'codex'` (`schema_vendor.py:222`). `_source_url()` hardcodes templates for
`mise`, `ruff`, `typos` only. `sources.toml:55` ALREADY stores the URL, so the
fix is to read `entry.source`. `refresh.yml:485` invokes this on a schedule, so
the scheduled refresh is also broken; `refresh.yml:539` additionally omits the
codex artifacts from its PR path list.

### B4 — the doctor's codex "currency" check can only pass

Armed both directions:

```
FAIL-ARM (bogus 99.99.99): (True, "Schema is present for codex 99.99.99...")
PASS-ARM (real  0.154.0):  (True, "Schema is present for codex 0.154.0...")
```

Both return True, and the bogus version is echoed back as if it were the
schema's own. The generated bundle records no codex version at all (top-level
keys: `$schema`, `definitions`, `title`, `type`), so currency is unimplementable
as written. Three places claim otherwise: the function name
(`codex_schema.py:53`), `doctor.toml:274`, and `.gitignore`'s new comment.

Rule: `.claude/rules/probes-need-a-control-arm.md` rule 9.

### B5 — a fresh Claude session cannot discover the team

Both the codex team and the Opus sweep reached this independently. Grep for
`sdlc` across the whole eager instruction surface returns ONE hit — a comment
explaining why a gate skips these files. Nothing in root `CLAUDE.md` ->
`AGENTS.md`, `.claude/CLAUDE.md`, `.claude/rules/*`, or the settings hooks
mentions the team. The spec's own "generic invocation" still contains the
literal placeholder `<spawn-two-subagents prompt>`
(`codex-sdlc-subagent-team.md:152`).

## MAJOR

- **M1** `generate_schema()` never writes `codex-agent.json` — it only copies
  app-server bundles (`codex_schema.py:146`). The instruction printed in that
  file's own header ("Regenerate with `mise run codex-schema-generate`") is
  therefore false.
- **M2** `schemas/codex-agent.json` has ZERO consumers. Nothing validates the
  agent files against it, so the `#:schema` directive is decorative — the exact
  class that left six agents silently unloaded.
- **M3** The parity test EXCLUDES sdlc agents (`test_codex_agent_parity.py:479`),
  so no roster/count/load contract covers them.
- **M4** `doctor.toml:278` claims `codex-schema-check` is run by `mise run
  verify`. It is not — `verify` only calls `dotfiles-setup verify run`.
- **M5** Dispatcher routing names paths that do not exist: `python/tests/`
  (tests are at root `tests/`), `mise run pytest` (no such task), `renovate.pkl`
  (it is `renovate.json`). Config routing omits JSON and `schemas/`.
- **M6** The image specialist claims its gate proves R1/R3/persistence; those are
  `verify-local` steps, not `verify-container-latest`.
- **M7** Specs contradict the implementation — the main spec still says "NOT
  implemented" and still requires `mcp_servers`, which V1 recorded as invalid.
- **M8** A project memory `project_session_2026-09-14-sdlc-team.md` names the
  WRONG six agents and is unindexed in `MEMORY.md`.
- **M9** `.codex/hooks.json` carries the codex PreToolUse guard and SessionStart
  doctor but is gitignored (`.gitignore:59` `.codex/*`), so it does not survive
  a clone.
- **M10** `hook_guard` is Claude-only: a `codex exec` lane's shell commands are
  invisible to all 20 rules. This is how B1 would have been unstoppable had it
  come from a lane.
- **M11** The graph is stale (5 commits behind), so `graphify-first.md`'s
  mandatory-query hook fires on every search and cannot be satisfied.

## Verification promises: DONE vs NOT DONE

| Item | Verdict |
|---|---|
| V1 codex recognises the six agent files | DONE ONCE, not durable |
| V2 named specialist spawns | DONE ONCE |
| V3 dispatcher routes multi-domain | PARTIAL — gates were sandbox-blocked |
| V4 team reusable on a disjoint task | DONE for routing only |
| "schema makes V1 non-recurring" | NOT DONE (M2, M3) |
| D5 four-layer validation incl. Claude hook | NOT DONE — no such hook exists |
| Learning loop S1/S2/S3 + JSONL + delta writer | NOT DONE — design only |

The learning-loop doc is honest that it is design-only; the defect is absence of
implementation, not a false claim.

## What is fine

- `codex-agent.json` has genuine `required` + `additionalProperties: false`.
- The derivation-equality test has a real mutation/fail arm.
- Narrowing the older parity contract to Sol/Astra families is deliberate.
- The `.gitignore` decision to exclude the 688 KB/589 KB app-server bundles is
  reasoned and correct.
- The team DOES work: three dispatcher runs routed correctly and spawned exactly
  the selected specialists.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the review subject.
- [openai/codex](https://github.com/openai/codex) — codex CLI 0.154.0, the schema's subject.

---

# Appendix — the lane watcher, measured (2026-09-14)

Built and run against REAL sessions during this session. Prototype lives at
`<scratchpad>/lane_watcher.py`; productionising it into `python/` is open work.

## Substrate: agentsview

`agentsview` is the right substrate and the load-bearing question answered YES:
**it sees codex lanes fully.** `session list --since 2d --include-children
--include-automated --include-one-shot` returned 247 sessions — 186 `claude`,
59 `codex`, 2 `antigravity-cli` — and `session tool-calls <id> --json` returned
3,336 codex calls (2.33 MB in 0.2s) with `input_json` populated on all of them.
Claude Code SUBAGENTS appear individually, by name.

This matters because `hook_guard` is a Claude `PreToolUse` hook: a `codex exec`
lane's shell commands are invisible to all 20 of its rules. agentsview is the
only mechanism found that can see both families.

### Traps encoded (each measured)

- **Bare `agentsview` DOES NOT RUN here** — it is an orphan mise shim
  (`No version is set for shim`). A watcher must use the absolute install path
  `~/.local/share/mise/installs/github-kenn-io-agentsview/0.42.0/agentsview`,
  or the repo must pin the tool in `mise.toml [tools]`. **Pinning it is open work.**
- `--include-one-shot` is MANDATORY or the watcher sees nothing.
- `session watch <id>` streams NDJSON but is a TRIGGER, not a content feed —
  `input_preview` is truncated for Claude and EMPTY for codex. Discovery still
  needs a `session list` poll; content needs `session tool-calls`.
- Codex wraps the shell inside `tools.exec_command({cmd:"..."})`, so a matcher
  that assumes a bare command string sees NOTHING on the codex side — i.e. it
  silently covers only the half that already had a guard.
- Querying auto-starts a background daemon and writes `~/.agentsview/sessions.db`.

## Measured precision — and the finding that matters

51 sessions scanned over an 8h window.

| Rule | Hits (naive) | Hits (heredocs stripped) | Real |
|---|---|---|---|
| `bulk-git-add` | 16 | 15 | mostly real (`git add -A && mise run lint`) |
| `gate-piped-to-pager` | 13 | 13 | **over-broad** — see below |
| `no-verify` | 4 | **0** | 0 — all prose |
| `bare-ruff-format` | 4 | 3 | 1 |
| `chezmoi-on-host` | 2 | **0** | 0 — all prose |
| `hk-skip` | 1 | **0** | 0 — all prose |
| **total** | **41** | **32** | |

**The dominant false-positive source is structural, not incidental: this repo's
agents constantly write rule-evidence documents, so a report ABOUT
`git commit --no-verify` is itself a tool call whose payload contains that
string.** Every `no-verify`, `hk-skip` and `chezmoi` hit was a
`cat > report.md <<'EOF'` body — including, recursively, the report you are
reading.

Stripping heredoc BODIES while keeping their command lines removed all nine,
and was armed three ways:

```
PROSE-ONLY: clean     (false positive removed)
REAL CMD  : FLAGGED   (true positive preserved)
BOTH      : FLAGGED   (a real command after a prose heredoc is still caught —
                       the fix opens no evasion path)
```

**Control arm:** the watcher caught the previous session's genuine bare
`ruff format` — the command that corrupted the 18 reports — and it survived the
heredoc fix. Without that arm this whole result would be unfalsifiable.

## Known-remaining imprecision (open work, NOT fixed)

1. **Non-shell tool calls are scanned.** A `SendMessage` payload reading
   `"ruff is the corrupter"` was flagged as a bare `ruff format`. Fix: filter to
   `category in {Bash, exec}` before matching.
2. **`gate-piped-to-pager` is over-broad.** It fires on
   `grep -B5 FAILED /tmp/pytest.log | head -40` — reading a LOG, which is the
   behaviour the rule PRESCRIBES. The pattern matches the word `pytest` in a
   FILENAME. Fix: require the gate to be invoked, not merely named.

Both are precision bugs, not coverage bugs — the watcher's recall on the one
known-bad command was 1/1.

## Verdict

The mechanism works and closes the codex blind spot. It is NOT ready to gate
anything: a watcher that reports prose as violations stops being read, which is
how a fail-open guard dies quietly. Land it as a REPORTING tool first, measure
precision over a week, and only then consider enforcement.

---

# PR2 scope — schema declarations on ALL config files

Ratified by the operator 2026-09-14. **Split from PR1 deliberately**: PR1 is the
verified repair + discovery work; this is a coherent programme that deserves its
own review.

## The requirement

1. **Every config file declares its schema**, in every format that supports it.
2. **Third-party configs use the OFFICIAL upstream schema**, vendored through the
   existing `schemas/sources.toml` mechanism (which now works for non-tagged
   sources — see B3 above).
3. **Configs WE own get a schema WE generate**, to enforce zero drift.
4. **Protocol for the validator: find an hk NATIVE BUILTIN**, preferring
   implementations in native languages (Rust / C / C++ / Zig) over interpreted ones.
5. Fixtures are excluded **only when they exist to drive a NEGATIVE test**.

## What is already true (measured, not assumed)

- **taplo is wired** (`hk.pkl:167`, Rust) and ENFORCES `#:schema`. Armed:
  an added `not_a_real_codex_key` produced
  `Additional properties are not allowed` + `schema validation failed`.
  **So for TOML, one directive line = instant validation.**
- The convention is a **relative LOCAL path** (`./schemas/mise.json`,
  `../../schemas/codex-agent.json`) — never a remote URL, because taplo does not
  cache remote schemas between runs (`refresh.yml:534`).
- ⚠️ A `# :schema` with a SPACE is INERT. The directive is `#:schema`.

## The gap

**23 tracked TOML files carry no directive**, including all **12**
`codex-sol-*` / `codex-astra-*` agent files — for which
`schemas/codex-agent.json` ALREADY EXISTS and currently has **zero consumers**.
`codex-astra-*` are GENERATED (`mise run codex-lane-mirror`), so the generator
must emit the directive or it will be stripped on the next regeneration.

**0 of 18 YAML files** carry a `yaml-language-server` schema line.
Many JSON configs carry no `$schema`.

## Our own configs: generate, don't hand-write

| module | reads | state |
|---|---|---|
| `doctor.py` | `doctor.toml` | **typed** (4 models) |
| `pin_parity.py` | `pin-parity.toml` | **typed** (2 models) |
| `rule_sync.py` | `rule-sync.toml` | **typed** (2 models) |
| `verify.py` | `python/verification/suites.toml` | ⚠️ **raw dict parsing — THE MISS** |

**`msgspec` is already a dependency and `msgspec.json.schema()` emits JSON Schema
from a Struct natively** — armed, returns a proper `$defs` document. So the
generator needs no new tool, and the schema cannot drift from the parser because
it reads the same Struct.

`verify.py` must be TYPED FIRST — it is the highest-stakes config (a typo in
`suites.toml` silently defines no contract) and the only one without a model.

## Validator research still owed (do this FIRST in PR2)

`docs/hk-builtins-audit.md` dismissed two Rust builtins as redundant. Re-examine
BOTH against the schema axis, because redundancy was judged on linting, not
validation:

| builtin | audit verdict | question to settle |
|---|---|---|
| `ryl` | "Redundant with yamllint" | Does it do SCHEMA validation? `yamllint` does NOT. If ryl does, the verdict was wrong on this axis. |
| `tombi` | "Redundant with taplo" | Same question; taplo already covers TOML, so likely genuinely redundant. |
| `mdschema` | "Requires a schema file that does not exist yet (#160 T12)" | Now that we generate schemas, does this become viable? |

For JSON the audit shows only `devcontainer_json_validate`. `check-jsonschema`
(0.38.0) and `ajv` (5.0.0) are installed but are Python/JS — per the protocol,
prefer a native builtin if one exists; document the exception if not.

## Order of work

1. Settle the `ryl` / `tombi` / JSON-validator question against hk's builtin list.
2. Type `verify.py`; generate its schema from the model.
3. Generate schemas for `doctor.toml`, `pin-parity.toml`, `rule-sync.toml`.
4. Vendor third-party schemas (`.gitleaks.toml`, `starship.toml`,
   `python/pyproject.toml`, `.agnix.toml`) via `schema-vendor-refresh`.
5. Add `#:schema` to all 23 TOML files; teach `codex-lane-mirror` to emit it.
6. Add the JSON/YAML gate chosen in step 1.
7. A gate asserting EVERY config declares a schema, excluding only negative-test
   fixtures — with a fail arm that adds an undeclared config and expects rc!=0.
