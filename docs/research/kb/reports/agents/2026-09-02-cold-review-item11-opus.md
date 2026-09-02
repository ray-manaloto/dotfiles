# Cold review — commit 96d7067 (ITEM 11 vendored schemas) — OPUS lens

Lane: Claude Opus subagent, read-only, 2026-09-02c. Reviewed by REF:
`96d7067` vs parent `df95413`. Cold — the brief withheld intent and asked
specifically for OMISSION-type defects, which never appear in a findings list.
Persisted verbatim by the architect (the lane reported by message, not to a file).

Cross-family gate: the diff was authored by codex, so this is the third-family
lens the orchestration doctrine requires. Sibling: `2026-09-02-cold-review-item11-codex.md`.

---

## CRITICAL

**C1 — The new contract never runs in CI. It is a local-only gate.**
`python/verification/suites.toml:2413` sets `category = "config"`. CI's contract-preflight runs `verify run` twice and only for these categories: `--category build --category ci --category identity --category architecture` (`.github/workflows/ci.yml:215-217`) and `--category orchestration --category eval` (`ci.yml:219-221`). `grep -rn "verify run" .github/` returns exactly those two sites plus a doc mention. And `grep -n 'category = "config"' python/verification/suites.toml` returns **one** line — 2412 — so this is the only `config` suite in the file and nothing was ever going to pick it up. Consequence: `config.schema-vendor-drift` fires only on a human running `mise run verify` (`mise.toml:373`, which passes no `--category`). No PR and no main run enforces it. Fix is one word in the suite or one flag in ci.yml.

**C2 — Nothing anywhere notices a silently altered vendored schema, and a gutted one makes taplo validate nothing while passing.**
`check_drift` (`python/src/dotfiles_setup/schema_vendor.py:154-176`) reads `sources.toml`'s recorded `version` and the tool's current pin — it never opens the vendored JSON. `sources.toml` records no checksum (`schemas/sources.toml:9-29`). And `hk-common.pkl:98-107` adds all three files to `excludePaths`, which is the **top-level** hk exclude (`hk.pkl:26` and `hk-image.pkl:26` both do `exclude = common.excludePaths`), so no hk step touches them either.

Armed both directions, temp tree, `_project_root` patched:

```
baseline (untouched):                        []
after gutting ruff.json to '{}':             []
after replacing ruff.json with non-JSON:     []
```

And taplo's side, armed against a real schema (`taplo lint`, mise-pinned):

- `extend-exclude = 42` + real typos.json → **rc=1**, `42 is not of type "array"` (the probe discriminates)
- same TOML + `#:schema ./empty.json` where empty.json is `{}` → **rc=0**, silent
- same TOML + missing schema file → **rc=1** `failed to load schema` (deletion IS caught, by taplo and by `paths_required` at `verify.py:82-91`)

So the reachable "gate reports success having validated nothing" state is concrete: **a vendored schema that is valid JSON but permissive** (`{}`, or upstream serving a different/emptier document). Drift check: green. taplo: green. hk: excluded. Only a hand-written sha256 in `sources.toml`, checked by `check_drift`, closes it.

## HIGH

**H1 — `check_drift(root)` / `refresh(root)` ignore `root` for half their inputs, and five tests are silently bound to the live repo's tool pins.**
`schema_vendor.py:168` calls `current_pin(entry.tool)`, which routes to `_read_shared_toml_pin` / `_read_uv_lock_pin` / `_read_setup_mise_pin` (`:44`, `:56`, `:82`) — all three build paths from `_project_root()`, not from `root`. `load_sources(root)` honours it; the pin half does not. Probe: a **fully self-consistent** temp tree seeded at 9.9.9 everywhere returns three drift findings.

Five tests pass `tmp_path` without monkeypatching `_project_root`: `test_check_drift_clean_when_versions_match:186`, `test_check_drift_reports_a_stale_vendored_version:191`, `test_refresh_is_a_noop_when_nothing_drifted:246`, `test_refresh_rewrites_the_schema_and_sources_toml_on_drift:259`, `test_refresh_leaves_an_unresolvable_tool_vendored_and_uncounted:279`. They pass today only because the fixture literals `1.50.1` / `0.16.5` / `2026.9.0` happen to equal `.config/mise/conf.d/shared.toml:47`, `python/uv.lock:1745` and `.github/actions/setup-mise/action.yml:39`. Armed with `_project_root` pointed at a mirror tree where typos is 1.51.0 (i.e. one Renovate bump from now):

```
clean_when_versions_match:            FAIL  findings=1
reports_a_stale_vendored_version:     FAIL  findings=1   (asserts len==1 and "1.50.1" in it)
```

`test_check_drift_clean_when_versions_match` also survives stubbing `check_drift` to `return []` — it is not load-bearing today either.

**H2 — Renovate bumping typos/ruff/mise makes `mise run verify` red on the PR, and no job fixes it there.**
`schema-refresh` is gated `if: github.event_name != 'pull_request'` (`refresh.yml:466`). #887's whole point was `image-lock-pr` (`refresh.yml:252-273`), a `pull_request`-scoped job that pushes the regenerated artifact onto the Renovate branch. ITEM 11 reproduces the drift problem for schemas and ships no equivalent, so the drift lands on the very PR that causes it and only the next day's cron produces the fix — on a *separate* branch. (C1 currently masks this in CI; it bites anyone running the documented local gate before committing.)

## MEDIUM

**M1 — `refresh_main` exits 0 after failing to refresh a tool.** `schema_vendor.py:280-289` returns 0 unconditionally; the unresolvable-pin branch (`:249-257`) only `logger.error`s and continues. The CI `schema-refresh` job goes green having refreshed nothing for that tool, and the `open-refresh-pr` step then opens (or skips) a PR on the strength of that. The only backstop is `check_drift` reporting "could not resolve" later — which per C1 runs nowhere in CI.

**M2 — `dotfiles-setup schema-vendor` with no subcommand exits 0 having done nothing.** `main.py:1896-1905`; `handle_schema_vendor` falls through when `schema_vendor_command` is `None`. Probed: `rc=0`, no output. It matches `handle_hook`'s precedent, so it's a pre-existing shape, but it's a silent-success branch in a new command.

**M3 — The `#:schema` directives themselves are bound by nothing.** No `require_tokens` suite asserts line 1 of `mise.toml` / `ruff.toml` / `typos.toml`. The suite at `suites.toml:2416-2428` lists those three files in `paths`, but `handler = "schema_drift"` ignores `paths` entirely (`verify.py:651-657` reads only `entry["name"]`) — so their presence in the list reads as coverage and is decorative beyond the existence check. Armed: a TOML with no directive at all → `taplo lint` rc=0, silent. Delete the directive and every gate stays green while the feature is gone.

**M4 — The hk exclusion is three files wide for a one-file justification, and bypasses the tool's own narrower mechanism.** `hk-common.pkl:98-107` justifies the exclusion by a typos false positive on ruff's `CPY` rule code. Armed per-file: `typos schemas/ruff.json` → rc=2, three `CPY` hits; `typos schemas/mise.json` → **rc=0**; `typos schemas/typos.json` → **rc=0**. Only ruff.json needed anything, and `typos.toml`'s own `extend-exclude` / `extend-words` is the native mechanism (`.claude/rules/use-tool-builtins.md`) rather than a repo-wide hk exclude that also removes the files from every future step.

## LOW

**L1 — `_SETUP_MISE_VERSION_RE`'s own comment is factually wrong, and the control arm it promises does not exist.** `schema_vendor.py:73-76` says "an unrelated `version:` elsewhere in the file (there is exactly one today) would be caught by the module's own tests". `grep -n 'version:' .github/actions/setup-mise/action.yml` returns **two** (lines 39 and 44 — two separate `jdx/mise-action` calls). They agree today, so the first-match regex is right by luck; no test reads the real file, so nothing would notice if they diverged.

**L2 — `_FETCH_TIMEOUT_S` is a connect timeout, not a fetch timeout.** `schema_vendor.py:38` and `:213` — `--connect-timeout` only; a body that stalls after connect runs to the job's `timeout-minutes: 20`. No `--max-time`, no `--retry`. Also no validation that the fetched bytes parse as JSON before they are written (`:265`) — an empty or garbage 200 is vendored verbatim. In practice `curl -f` catches 404 loudly and taplo catches an unparseable schema in the PR's lint, so this reaches only the C2 "valid but permissive" hole rather than opening a new one.

**L3 — Untested wiring, which is this repo's own recurring class.** `grep -rn "schema_vendor|schema-vendor|schema_drift"` outside `tests/test_schema_vendor.py` returns only the three suites.toml lines. Nothing tests `main.py:2339`'s `"schema-vendor"` dispatch entry, `handle_schema_vendor`, `verify.py:651`'s `_handle_schema_drift`, or the two `mise.toml:1335-1342` tasks. Per the repo's own `project_session_2026-09-01c` note ("reverting one dispatch line left the suite green"), the 18 green tests certify the module's logic and say nothing about its wiring. Related: `test_refresh_leaves_an_unresolvable_tool_vendored_and_uncounted:279` asserts only `"not-a-tool" not in changed` — it never checks the file is still there or the row survived, so it does not test the behaviour its name claims; and the `_source_url` parametrize (`:216-243`) asserts the code's literals against themselves, so an upstream path rename stays green in tests and surfaces only as a red CI refresh job.

## Categories I found nothing in

- **Error/exception handling through `verify`**: clean. `verify.py:93-101` catches `VerificationError` plus `TypeError/ValueError/KeyError/OSError/RuntimeError`, so a malformed `sources.toml` (`tomllib.TOMLDecodeError` is a `ValueError`; a missing key is a `KeyError`) fails that one suite rather than aborting the run. Read the runner and the handler.
- **Missing-file handling for the vendored schemas**: closed by `paths_required = true` (`suites.toml:2415`) + `verify.py:82-91`, armed by the missing-schema taplo run above.
- **404 / hard-fail fetch path**: `_curl_fetch` (`:210-222`) uses `-f` and raises `RuntimeError` on non-zero, the workflow step has no `if: always()`, so a failed fetch fails the job before `open-refresh-pr` runs. No bad PR from that branch.
- **The vendoring premise itself**: genuinely works. taplo schema validation is live and discriminates (rc=1 on a type violation, rc=0 on a valid one), and `taplo lint mise.toml ruff.toml typos.toml` is rc=0 today.
- **The remote `$schema` in `.claude/settings.json:2`**: URL is real — `https://www.schemastore.org/claude-code-settings.json` → 200, control `.../definitely-not-a-real-schema-xyz.json` → 404. It's inconsistent with the commit's own no-remote-schema rationale, but it's JSON, taplo never reads it, and it is on no gate's path.
- **`platform_target.py:163` adding `schemas/`**: justified and correct — `schemas/mise.json` really does carry `"linux/x64"` as an example of mise's os/arch grammar, and `schema_vendor.py` issues no `--platform`.
- **Inline lint suppressions**: none in the diff. Logic is in `python/`, the workflow calls a mise task wrapping the module, and both tasks exist in `mise.toml`. The repo's structural conventions are respected.

Riskiest branches actually read to support the clean claims: `verify.run_suite` (paths + exception handling), `schema_vendor.refresh`'s unresolvable-pin and byte-compare branches, `_curl_fetch`'s failure path, `handle_schema_vendor`'s fall-through, and the `schema-refresh` job's step ordering in `refresh.yml:466-529`.

**Recommendation: fix C1 first. Every other finding is a gate quality question; C1 means the gate does not run.**

---

## Architect note

C1 was verified and found to be **repo-wide**, not ITEM 11-specific: `workflow`
(41), `policy` (4) and `config` (1) are all absent from CI's `--category` flags —
**46 of 146 contracts**, including two added earlier the same day. Filed as **#911**.

This lens and the codex lens found **disjoint** defect sets. C1, H1, H2, M3 and L1
appear only here; the codex lane's `suites.toml:2415` self-blindness citation
appears only there. Run both.

## GitHub repos touched

_None._ All reads were local to this repo.
