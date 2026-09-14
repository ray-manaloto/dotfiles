# premise-verifier — plugin-health spec (2026-09-13)

Spec verified: `scratchpad/spec-plugin-health.md` (session dotfiles-20260913.002).
Persisted at receipt per `.claude/rules/agent-report-persistence.md`. The agent's
delivered result was TRUNCATED mid-sentence inside MISSING #1; the truncation is
marked inline below and the remainder was requested via SendMessage.

> Coordinator note: rows 1 and 15 are the load-bearing ones. I re-measured row 1
> myself from the captured `claude plugin list --json` and the verifier
> UNDER-called it — see "Coordinator re-measurement" at the bottom.

## Per-row verdicts (verbatim)

| # | Row | Verdict | Evidence |
|---|---|---|---|
| 1 | `L` `plugin list --json` → array of 271 rows, **each with exactly** those 8 keys | **REFUTED (partly)** | Array of 271: CONFIRMED (two runs, stable). "Exactly those keys": FALSE — **8 distinct key sets**. `projectPath` absent from **55** rows; one row is `{id,version,scope,enabled,installPath}` only (`claude-doctor@skills-dir`); extras `mcpServers` (6), `notes`+`noteDetails` (8). Also `scope` has a **third** value `local` (2 rows), and ids are **not unique** — `context7@context7-marketplace` appears 3×. |
| 2 | `L` `plugin details` has no `--json` | **CONFIRMED** | `claude plugin details --help` → `Options: -h, --help` only. |
| 3 | `L` `plugin list --help` lists exactly `--available` + `--json`; `--available` requires `--json` | **CONFIRMED** | Verbatim: `--available  Include available plugins from marketplaces (requires --json)`. |
| 4 | `I` `claude_doctor_main(...) -> int` at `claude_doctor.py:397` | **CONFIRMED** | `python/src/dotfiles_setup/claude_doctor.py:397`, signature exact. |
| 5 | `I` `codec.encode` :339 / `codec.decode[T]` :362 | **CONFIRMED** | `python/src/dotfiles_setup/codec.py:339`, `:362`; TID251 ban confirmed at `python/pyproject.toml:123-136`. |
| 6 | `I` registration `main.py:1504` / `:1520` / dispatch `:2577` | **CONFIRMED** | All three exact. Note the existing parser also adds a `--no-refresh` flag (`main.py:1526`) that the dispatch reads — a new subcommand with no flags is simpler, fine. |
| 7 | `I` hooks.json = `{description, modules:["./register.ts"]}` | **CONFIRMED** | `.claude/skills/claude-doctor/hooks/hooks.json`, and the `.agents` copy is byte-identical (`diff -r` rc=0). |
| 8 | `P` `register.ts` passes `DOTFILES_AMBIENT_PATH`, ignores rc, parses JSON | **CONFIRMED** | `readVerdict`, `.claude/skills/claude-doctor/hooks/register.ts`; comment `// rc is deliberately ignored`. |
| 9 | `L` logger convention `lock_integrity.py:58` | **CONFIRMED** | Exact. |
| 10 | `L` `_RUNNING_RE.search(text)` at `claude_doctor.py:223` | **CONFIRMED** | Exact. |
| 11 | `E` `report.code` bounded to six enum members, no PII | **CONFIRMED (by construction)** | Nothing in the design widens it. |
| 12 | `E` `missing/disabled/foreign_scope` are id strings, unbounded, no PII | **CONFIRMED, with a caveat** | Ids are safe, but `claude-doctor@skills-dir`-style ids and the `notes` strings are *not* the only unbounded field — see MISSING #3. |
| 13 | `E` `installPath`/`projectPath` carry `$HOME`, must not be emitted | **CONFIRMED** | Live rows carry `/Users/rmanaloto/...`, including **temp-dir and worktree paths** from other sessions. |
| 14 | `E` stderr diagnostic unbounded, truncate, never branch | **CONFIRMED** | Consistent with `claude_doctor.py:210-219`. |
| 15 | `A` `[plugins]` belongs in `doctor.toml` | **ASSUMED — and the assumption is weaker than stated** | `doctor.toml` is the right file, but see MISSING #1: the check itself probably belongs in `doctor.py`, not in a new module + new function hook. |

## MISSING premises (verbatim, TRUNCATED)

**1. A SessionStart plugin-health checker already exists, and the spec never mentions it.** `dotfiles-setup doctor` runs from the SessionStart **command** hook (`.claude/settings.json` → `DOTFILES_AMBIENT_PATH="$PATH" mise -C … run doctor`), has a 15-entry `CHECKS`/`LIVE_CHECKS` registry (`doctor.py:1268`, `:1284`), reads `doctor.toml`, and already contains **`enabled_plugin_ids(*settings)`** (`doctor.py:296`) which parses `enabledPlugins` with project-over-user precedence — the exact mechanism whose abse

*[result truncated here by the harness; remainder requested via SendMessage]*

## Coordinator re-measurement (2026-09-13, first-hand)

Row 1's refutation is correct and UNDER-called. Measured directly from the
captured `claude plugin list --json` payload:

| Fact | Measured |
|---|---|
| rows | 271 |
| distinct key sets | 8 |
| rows lacking `projectPath` | 55 |
| `scope` values | `project` 215, `user` 54, `local` 2 |
| duplicate ids | **35 ids**, max multiplicity **8** |
| `context7@context7-marketplace` rows | 3 |

The verifier cited context7 at 3x as the duplication example; the real worst
case is **8**. Any decode model with required `projectPath`, or any predicate
assuming one row per id, is wrong against this host's live data.

## Coordinator verification of MISSING #1

Confirmed first-hand rather than taken on trust:

- `enabled_plugin_ids(*settings)` exists in `python/src/dotfiles_setup/doctor.py`
  and returns `sorted(name for name, on in enabled.items() if on)` with "Later
  mappings win, so a project setting overrides the user one".
- `CHECKS` is a 12-entry tuple and `LIVE_CHECKS` a 2-entry tuple in the same file.

**The important distinction the verifier did not draw:** `enabled_plugin_ids`
reads what `settings.json` *DECLARES*. It cannot tell you whether the plugin is
actually installed and loadable — which is precisely why firecrawl being absent
from `enabledPlugins` entirely, and exa/context7 being `false`, produced no
finding. `claude plugin list --json` answers the *ACTUAL* side. So the new check
is COMPLEMENTARY, not duplicative: it reconciles declared against actual, and
that reconciliation is the thing that was missing.

This also retires premise row 15's `A`: the expectation should be DERIVED from
`enabled_plugin_ids(user_settings, project_settings)` rather than hand-listed in
a new `doctor.toml [plugins] required` array, because settings.json is already
the reviewed source of truth and a hand-kept second list would drift from it.

## GitHub repos touched

_None._ All evidence is this repository plus the local `claude` CLI.

## MISSING #1 and #2 (verbatim, second delivery)

*The agent's first delivery truncated inside MISSING #1; this is the resend. It
truncated again inside MISSING #2. Both fragments are preserved as received.*

**MISSING #1 — a SessionStart plugin-health mechanism already exists**

`dotfiles-setup doctor` runs at SessionStart today from a **command** hook in
`.claude/settings.json`: matcher `"startup|resume"` →
`DOTFILES_AMBIENT_PATH="$PATH" mise -C "$CLAUDE_PROJECT_DIR" run doctor`.

It has a 12-entry `CHECKS` registry (`doctor.py:1268`) plus 2 `LIVE_CHECKS`
(`:1284`), each `(name, Callable[[Setup], list[str]])`, driven by
`run_checks(collect(repo_root))` and rendered by `doctor_main` (`:1357`) — which
prints **human lines**, returns 0 unless `--strict`, and is silent when healthy.
Its baseline is `doctor.toml`, already sectioned `[fnox] [mcp] [listing]
[graphify] [path_drift] [claude]`.

Most importantly it **already contains the enablement logic**:
`enabled_plugin_ids(*settings)` at `doctor.py:296` returns the
`<plugin>@<marketplace>` ids enabled by any settings mapping, later mappings
winning — "the same precedence Claude Code applies". It is consumed by
`collect_servers` (`:376`) for MCP resolution, not for health. That is the exact
mechanism whose absence caused the motivating failure, sitting unused for this
purpose.

Also note `("claude-doctor", check_claude_doctor)` is **already in CHECKS**
(`:1279`) *and* is what the existing function hook reports. The claude-doctor
verdict is therefore already announced twice per session. Adding plugin-health as
a second independent hook makes that pattern three-deep.

Reconciling with "it must be a SessionStart function hook": these are not in
conflict, because the duplication worth avoiding is the *judgement*, not the
*carrier*. Recommended shape: (1) judgement in `plugin_health.py` as pure
functions calling `doctor.enabled_plugin_ids` rather than re-deriving precedence;
(2) a thin `check_plugins(setup) -> list[str]` adapter in `doctor.py`'s `CHECKS`
— free baseline, crash isolation via `_record_crash`, silent-when-healthy, and it
runs even when function hooks are off; (3) keep the function hook but have it
call the **new JSON subcommand**, not `doctor` — `doctor_main` is not a JSON seam
(human lines, rc tied to `--strict`), so reusing it would force exactly the
text-scraping the spec exists to retire.

Net: one implementation, two carriers. If the operator wants only the function
hook, the spec must say so explicitly and skip step 2 — but then
`use-tool-builtins.md` requires a written justification for not extending the
native registry, which the spec's `A` row does not supply (it argues only about
*file placement* of the baseline, not *subsystem placement* of the check).

**MISSING #2 — the scope-filter rule is refuted by live data**

Spec said: "a row is relevant to this project only when `scope == "user"` or
`projectPath` equals the project root."

Measured twice, stable (271 rows both runs): `context7@context7-marketplace` and
`exa@exa` each get a `projectPath=/…/dotfiles` row; **`firecrawl@firecrawl` gets
none** — only a `user` row and a `knowledge-base` row. All three are `true` in
project `enabledPlugins` and `false` in user. Control arm: `astral@astral-sh`
(`false` in project settings) *does* get a dotfiles row with `enabled=false`, so
the probe can produce both outcomes. Same input, different row shape.

**The row set is not a function of `enabledPlugins`.** Any check whose relevance
test depends on a dotfiles-scoped row existing will report DRIFT for a
correctly-enabled plugin. Settings are the authority for "should be enabled
here"; the CLI rows answer the different question "is it insta

*[truncated again by the harness at the same size bound]*

## Coordinator re-measurement of MISSING #2 (first-hand)

| id | dotfiles-scoped row | user row | other rows |
|---|---|---|---|
| `firecrawl@firecrawl` | **NONE** | `enabled=True`, no `projectPath` key | project/knowledge-base `True` |
| `exa@exa` | `True` | `True` | knowledge-base `True` |
| `context7@context7-marketplace` | `True` | `True` | knowledge-base `True` |
| `astral@astral-sh` (control) | **`enabled=False`** | — | knowledge-base `False`, graphify `False` |

The refutation is CONFIRMED and the control arm holds: rows do faithfully carry
`enabled=false`, so the absence of a firecrawl dotfiles row is a real asymmetry,
not a reporting artifact.

⚠️ One correction to the verifier's account: it states all three are "`false` in
user", but firecrawl's **user row reads `enabled=True`**. That detail inverts the
severity. Under the refuted rule, firecrawl falls through to its user row, which
is `True`, so the rule would have PASSED on this host — by luck. Had that user
row been `False`, the rule would have reported DRIFT on a correctly-enabled
plugin. A rule that is right by luck is not right, and the luck is host-specific,
so the refutation stands and is arguably more dangerous than described: it would
have shipped green here and failed on another machine.

**Remediation dispatched to the live lane:** stop inferring a single "effective"
verdict per id. Settings alone are the authority for "should be enabled here";
CLI rows answer "is it installed, and what does each scope record". Report three
observable lists (`declared_not_installed`, `declared_disabled_here`,
`installed_not_declared`) and say NOTHING for a declared id that has no
project-scoped row but has rows elsewhere — the firecrawl shape, whose mechanism
is not understood, where silence is the correct output.
