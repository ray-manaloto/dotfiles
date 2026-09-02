# Premise verification — ITEM 11 (schema references for Claude/Codex config)

Lane: `fable-orchestrator:premise-verifier` (Claude, read-only), 2026-09-02c.
Persisted by the architect: the lane has only Read/Grep/Glob, so it could not
write this file itself, and it could not re-probe the network rows (L1-L5).

Spec under verification:
`scratchpad/spec-item11-schemas.md` (session scratchpad, not tracked).

---

PREMISE REPORT
ROWS: 8 checked — 2 CONFIRMED (0 provenance corrected) / 0 REFUTED / 5 UNVERIFIABLE / 1 ASSUMED (1 checkable)

L1 — UNVERIFIABLE — no network tool in this lane; no on-disk artifact (`grep -r schemastore` across the repo → 1 unrelated hit, docs/research/runs/research-20260709-r2-web-env/agents/official-docs.md). Provenance "measured this session" is a prior probe, not a file:line.
L2 — UNVERIFIABLE — same; no offline schemastore cache (`docs/research/mintlify-cache/**/schemastore*` → 0 files).
L3 — UNVERIFIABLE — same. See MISSING M5 (shape).
L4 — UNVERIFIABLE — same.
L5 — UNVERIFIABLE — a negative catalog claim; no offline catalog copy exists to settle it.
I1 — CONFIRMED — `SENTINEL = "dotfiles-hand-authored-codex-lane"` at codex_agent_parity.py:90; `raw = _read(path)` at :216 then `if SENTINEL not in raw:` at :219 — whole-file substring, line position free. Also `_stems` filters on `STEM_PREFIX = "codex-"` (:81, :162), so only the five spec'd tomls are gated; the exporter mirrors are out of scope.
L6 — CONFIRMED — `$schema|#:schema` over all twelve → 0 hits; control arm (`mcpServers|autoCommit|severity|env_true|model_reasoning_effort|permissions|displayName|eval`, same command shape) → 16 hits across all twelve, so the probe discriminates.
A1 — ASSUMED (checkable) — the TOML-parser half is settled in-repo: `tomllib.loads(raw)` at codex_agent_parity.py:243 is fed the whole file including comments and the gate passes today, so a leading comment is inert. The taplo half is NOT an assumption and looks unsafe — see M2.

MISSING:
- M1 agnix, `--strict`, over BOTH .claude/settings.json and .agnix.toml — hk.pkl:498-505 (`check = "agnix . --strict"`, glob includes `.claude/settings.json` and `.agnix.toml`). The spec names only `hook selfcheck`. agnix exits 0 on warnings normally, but `--strict` makes warnings-as-errors, so ONE agnix opinion about an unknown `$schema` top-level key (or a new leading comment in its own config) turns `mise run lint` red. I cannot run agnix here. VERIFY: `agnix . --strict` on a scratch copy carrying the key, before dispatch.
- M2 taplo does NOT ignore `#:schema` — it is taplo's schema-ASSOCIATION directive (the spec says so itself at §3, line 35), which contradicts A1's "consumers ignore an unrecognized leading comment". hk.pkl:167 wires `Builtins.taplo` (batch=true, lint-only) and there is NO `.taplo.toml`/`taplo.toml` in the repo (Glob → only `.agnix.toml`), so taplo runs on defaults with schema handling enabled. Adding `#:schema` therefore makes `mise run lint` fetch and VALIDATE that file against the URL on every run — a new network dependency and a new failure mode, on files (`doctor.toml`, `.agnix.toml`) whose shapes are repo-invented and have no published schema at all. VERIFY: add one directive locally and run `mise run lint`, with a control arm (a deliberately wrong schema must make taplo fail).
- M3 (settles the architect's first question) the other `.claude/settings.json` readers are all SAFE, but none were listed: doctor.py:392 `load_json(...)` reads only `hooks`/`permissions`/`enabledPlugins` by name (:415, :439, :289); parity.py:91-96 `json.loads` reads `enabledPlugins` only; verify.py suites are `require_tokens` substring checks (suites.toml:1235, 1252, 1393, 1557, 1778, 1848, 1961, 2086). No reader enumerates top-level keys, so an added `$schema` is tolerated by every one. Add rows or accept as verified-here.
- M4 (settles the second question) NO gate asserts a byte count, line count, or first-line content for any of the twelve. The repo's only line-count gate is hk.pkl:161, scoped to `.devcontainer/Dockerfile.host-user`; `md_size_budget` is markdown-class only; `listing_budget.py:61-78` budgets skill/agent LISTING ROWS, not files. Non-blocking.
- M5 `.agents/plugins/marketplace.json` shape does not match a Claude Code marketplace: it is `{name, interface.displayName, plugins[].source.{source,path}, plugins[].policy.installation, plugins[].category}` (marketplace.json:1-20) — Codex/agents shape, not Claude Code's `{name, owner, plugins[].{name,source,description}}`. L3 pins a URL but no row claims it fits this file. §4's shape rule mitigates, but the row is missing.
- M6 `.agents/plugins/marketplace.json`, `.claude/ultrapowers-preferences.json` and `.agents/skills/codex-task-orchestration/evals/evals.json` are read by NOTHING in this repo (the only in-repo `marketplace.json` reader is doctor.py:310, and it reads `.claude-plugin/marketplace.json` inside plugin roots — a different path). So no in-repo breakage risk for those three; the only cost of a wrong URL is editor noise.
- M7 `.mcp.json` is `{"mcpServers": {}}` (.mcp.json:1-3) and doctor.py:326 reads only the `mcpServers` block — an added key would be tolerated, but the spec's "leave it alone" stands on L5, which is unverified.

VERDICT: correct the spec first — M2 blocks: `#:schema` is an ACTIVE taplo directive under a config-less `mise run lint` (hk.pkl:167), not the inert comment A1 assumes, and the spec offers no premise for what taplo then does; M1 blocks alongside it (`agnix --strict` over settings.json AND .agnix.toml, hk.pkl:498-505, unnamed by the spec and un-run here).

Non-blocking residuals, each named for accept-on-record: L1-L4 (the spec's own §4/§5 force a fresh 200+control-arm probe of every URL before it reaches the diff, so an unverified URL row cannot silently ship); L5 (a wrong negative only costs a missed opportunity — the outcome is "change nothing"); L6/I1 confirmed; M4 (verified absent, nothing to do); M5 (§4's shape rule already instructs "leave the file alone and say so"); M6/M7 (informational — no in-repo consumer to break).

---

## GitHub repos touched

_None._ All reads were local to this repo; the lane had no network tool.
