# 2026-09-12 Grilling Facts

## FACT 1 — can #995 honestly be closed?

**YES — the post-#1012 schedule run reads success on smoke-test, dev-tag AND manifest.**

- PR #1012 merged at `2026-09-11T18:24:32Z` (commit `e547c47aa08485af9ffd48d33881c237e10bd87f`). Command: `gh pr view 1012 --json mergedAt,mergeCommit`.
- Schedule-event `ci.yml` runs (`gh run list -R ray-manaloto/dotfiles --workflow ci.yml --event schedule --limit 20 --json databaseId,createdAt,conclusion,headSha`, rc=0): the newest run is `databaseId=34690912332`, `createdAt=2026-09-12T11:23:03Z`, `headSha=4b3b798ee619a6dd67a94c5c4d56d980412e255e` — this run is AFTER the #1012 merge.
- `gh run view 34690912332 -R ray-manaloto/dotfiles --json jobs` (rc=0), filtered for the three job families:

| Job | Conclusion |
|---|---|
| `build-publish / smoke-test (linux/arm64/v8, arm64, ubuntu-24.04-arm, arm64, publish, true, true)` | success |
| `build-publish / smoke-test (linux/arm64/v8, arm64, ubuntu-26.04-arm, arm64-runner2604, validate, false, false)` | success |
| `build-publish / smoke-test (linux/amd64/v2, amd64, ubuntu-latest, amd64, publish, true, true)` | success |
| `build-publish / dev-tag (linux/amd64/v2, amd64, ubuntu-latest, amd64, publish, true, true)` | success |
| `build-publish / dev-tag (linux/arm64/v8, arm64, ubuntu-24.04-arm, arm64, publish, true, true)` | success |
| `build-publish / dev-tag (linux/arm64/v8, arm64, ubuntu-26.04-arm, arm64-runner2604, validate, false, false)` | success |
| `build-publish / manifest` | success |

All three job families read `success` on every leg, literally, no interpretation. `promote`, `build-publish / dev-prep`, and `failure-report` show `skipped` (not part of the #995 wording, not counted here). #995 can honestly be closed on this evidence.

## FACT 2 — knowledge-base kb-settings-guard function hook

(pending)

Updated:

**Verbatim files** — `.claude-plugin/plugin.json`, `hooks/hooks.json`, `hooks/register.ts` all read and quoted below.

`plugin.json`:
```json
{
  "name": "kb-settings-guard",
  "version": "0.2.0",
  "description": "Denies a delegated agent lane any write to this repo's Claude settings files.",
  "author": { "name": "knowledge-base" }
}
```

`hooks/hooks.json`:
```json
{
  "description": "Deny a delegated lane any Edit/Write to .claude/settings*.json",
  "modules": ["./register.ts"]
}
```

`hooks/register.ts` (91 lines, `.claude/mods/kb-settings-guard/hooks/register.ts`) — full content read; key facts:

- **Events registered:** `on("tool.call", { tool }, handler)` for `tool` in `["Edit", "Write", "NotebookEdit"]` (`register.ts:88-92`, `WRITE_TOOLS` const at line ~63). This is the **native `tool.call`** event with a literal per-tool matcher — NOT a `classic.*` event. It deliberately never names `Bash` (the file's own comment cites `anthropics/claude-code#92533`: a pure-passthrough `tool.call` matcher on `Bash` breaks EVERY Bash call inside `Agent(isolation:"worktree")`, so the module avoids Bash entirely rather than relying on matcher literalness).
- **Handler return shape:** either `next(e)` (pass-through allow) or `{ deny: "<message>" }` (a plain object with a `deny` string field — not a `next(...)`/`return` variant beyond that). On internal error it also returns `{ deny: "...failing closed..." }` inside a `catch` block — fails closed, never open.
- **Typing:** **UNTYPED.** `handler($: any, e: any, next: any): Promise<any>`, `register(on: any): void`, `laneOf(event: { agentId?: unknown })` (this one has a narrow type), `targetInLinkedWorktree($: any, filePath: string)`. There is no `export const register: Register` declaration and no `import type { On }` from `claude-code`. It does not use the typed contract shape that `docs/research/reports/2026-09-10-function-hooks-research.md` describes upstream `mods/sec-default` as following.
- **Lane marker field:** `e.agentId` (camelCase) — the file's own comment (lines ~30-37) flags this as "THE SPELLING TRAP": the classic-hook/public-docs spelling is `agent_id` (snake_case), and a guard reading the wrong field gets `undefined` on every call and silently allows everything.

**Registration status: NOT REGISTERED / NOT LIVE.** `kb-settings-guard` does not appear in `enabledPlugins` or `extraKnownMarketplaces` in either `.claude/settings.json` or `.claude/settings.local.json` (`grep -rn "kb-settings-guard|extraKnownMarketplaces|enabledPlugins"` over both files — no `kb-settings-guard` hit in either; `enabledPlugins` lists 22 other plugins, none named this). This matches the module's own top-of-file comment: "NOT YET REGISTERED... Registration, readiness and liveness are ticket G04 (#757)." `schemas/guard-inventory.schema.json:349` states the same thing structurally: a 4-state model (declared/enabled/installed/exercised) where "Today `kb-settings-guard` is at `declared`: tracked, complete, and running nothing."

**What DOES gate it (extensive, all around DECLARATION not LIVENESS):**
- `docs/guards/inventory.toml` — three registration rows (`hook.toolcall.kb-settings-guard.edit/.write/.notebookedit`), each pointing at `register.ts` as the enforcing file.
- `python/src/kb_setup/guard_inventory.py` — `FUNCTION_HOOK_SOURCE_PATH`/`FUNCTION_HOOK_MANIFEST_PATH` constants; reconciles `register.ts`'s actual tool loop against the inventory rows (`reconcile_function_hook_registrations`-type logic around line 893-961).
- `python/src/kb_setup/guard_codegen.py` — regenerates `protected-paths.ts` (the TS array `register.ts` imports) from `schemas/guard-policy.schema.json`'s enum, and asserts (F1, `_register_ts_consumes_policy`) that `register.ts` still both imports AND uses that generated policy — a drift gate, not a liveness gate.
- `python/src/kb_setup/mod_runtime.py` — `kb-mod-runtime-check`, a **ship gate since 2026-09-12**, deliberately non-hermetic: runs `/plugin-types` against the actually-installed `claude` binary and reconciles fresh event/type declarations against a contract derived from `register.ts`'s own text (mise.toml:1928 area).
- mise tasks confirmed wired: `[tasks.kb-guard-inventory-check]` (mise.toml:1083), `[tasks.kb-guard-codegen-check]` (mise.toml:1106), `[tasks.kb-mod-runtime-check]` (mise.toml:1928, explicitly in `GATE_TASKS` per the surrounding comment, unlike the other two which are reached via `test`).
- Tests: `tests/test_guard_inventory.py`, `tests/test_settings_guard.py`, `tests/test_guard_codegen.py`.
- **None of this exercises the LIVE hook** — every one of these checks is static (declared-state / source-consistency), consistent with the schema comment's explicit "declared" classification and the plan reference `mise run kb-guard-arm -- --live --arms` as the still-open G03 item (`docs/research/reports/2026-09-11-function-hooks-astra-verdict-raw.md:122`) that would actually dispatch a lane and prove the deny fires.

**Control arm (probes-need-a-control-arm):** a freshly-invented, never-before-used token `zzqqxxNOPE9912` returns `git grep` rc=1 (0 matches) in the same repo — confirming the dozens of `kb-settings-guard` hits above are real content, not an artifact of a broken grep.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read PR #1012 merge metadata and schedule-event `ci.yml` run job conclusions via `gh`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — read `.claude/mods/kb-settings-guard/` source, `.claude/settings.json`/`settings.local.json`, `mise.toml`, `docs/guards/inventory.toml`, and `python/src/kb_setup/{guard_inventory,guard_codegen,mod_runtime,settings_guard}.py` (local clone, no network fetch — sibling working directory).
