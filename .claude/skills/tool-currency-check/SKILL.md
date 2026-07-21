---
name: tool-currency-check
description: "Use when auditing whether the repo's pinned tools are current AND whether any hand-rolled custom code is now superseded by a native tool feature. Produces a retire/bump report from mise outdated + pkl/pin-vs-latest diff + a cache-first release-note scan."
user-invocable: true
type: learned-skill
extracted-from: session 2026-07-04 (devcontainer build-input program, epic #160)
applicability: any repo managing tools via mise + hk + Renovate
---

# Skill: Tool Currency Check


> Daily input signal: refresh.yml's `tool-currency` job upserts the
> standing issue "Tool currency report (daily)" (rendered by
> `mise run tool-currency`) whenever upstream moved — start the review
> there instead of re-deriving the outdated set.


Operationalizes `.claude/rules/tool-currency-and-native-first.md`: find
out-of-date pins AND custom code a tool now does natively, in one pass.

## When to use

- Starting a "get on latest tool versions" / "stop reinventing" task.
- Before writing new custom tooling around a managed tool (confirm it's not
  already native).
- Periodically, to catch custom code that a tool's newer release has superseded
  (the `mise_snapshot.py` → `mise.lock` class of finding).

## Procedure

1. **Version drift — `mise outdated --bump`.** Lists pinned-vs-latest for every
   `mise.toml` / `mise-system.toml` tool:

   ```bash
   mise outdated --bump --local   # host/project tools (root mise.toml)
   ```

   **`--bump` is mandatory here — bare `mise outdated` is a check that can only
   pass in this repo.** Every pin is *exact*, so the range that "matches the
   current config" IS the pin, and nothing can ever be reported outdated.
   Control-armed 2026-07-20: `mise outdated "pipx:graphifyy"` printed *"All
   tools are up to date"* while the pin sat at **0.9.20** against PyPI
   **0.9.22**; `mise outdated hk` said the same while `--bump` showed
   1.50.0 → 1.51.0. `tool_currency.py` already passes `--bump`; this step used
   to contradict it. `--local` skips the user's global
   `~/.config/mise/config.toml`, which otherwise leaks unrelated tools into the
   report.

   Two more native flags worth knowing: **`--dry-run-code`** exits **1** when
   anything is outdated (a gate needing no output parsing), and
   **`--minimum-release-age "90d"`** is a native cooldown — reach for it before
   hand-rolling any hold logic.

   Note which are intentionally held back (comments in `mise.toml`, e.g. `rtk`
   pinned for a lockfile bug) — those are decisions, not drift.

2. **Cross-file pin parity.** Some versions are pinned in more than one place
   and must move together. The load-bearing one is **hk**, pinned in the pkl
   `amends`/`import` URLs of all three pkl files AND in `mise.toml`:

   ```bash
   grep -rhoE 'hk@[0-9]+\.[0-9]+\.[0-9]+' hk.pkl hk-common.pkl hk-image.pkl | sort -u
   grep -E '^hk = ' mise.toml
   ```

   All must be identical. A mismatch is drift (the current 1.44.2-pkl /
   1.46-mise gap is a real example). Compare against the latest release via
   `mise outdated hk`.

3. **Custom-code inventory — "does the tool do this natively now?"** For each
   piece of hand-rolled machinery, re-check the tool's current capability:

   | Custom code | Tool feature to re-check |
   |---|---|
   | `python/.../p2996_hash.py` content-hash | mise SBOM / `mise bom` / any toolchain-fingerprint (none as of 2026-07) |
   | `mise-system-resolved.json` + `mise_snapshot.py` | `mise lock` conda `sha256` (rattler — native; RETIRED in #160 T1) |
   | `refresh.yml` `p2996-refresh` | Renovate `git-refs` datasource |
   | `renovate.json` customManagers | native mise/dockerfile/devcontainer managers + jdx preset |

4. **Release-note scan (cache-first).** For each outdated / custom-wrapped tool,
   read the CHANGELOG via the `research-doc-sources.md` chain — **do not** guess
   from the docs, which lag the code:

   ```bash
   # step 0: local cache
   grep -rHi <feature> docs/research/mintlify-cache/jdx/<tool>/
   # step 1/2: remote, only on cache miss
   curl -s https://raw.githubusercontent.com/jdx/<tool>/main/docs/... .md
   ```

   Look specifically for features that would let us **delete** custom code.

5. **Emit a retire/bump report.** One table:

   ```text
   | tool/code | pinned | latest | native-now? | action        |
   |-----------|--------|--------|-------------|---------------|
   | hk        | 1.44.2 | 1.49.0 | n/a         | bump (3 pkl + mise + lock) |
   | mise-snapshot.json | — | — | mise.lock conda sha256 | RETIRE |
   ```

   Actions: `bump`, `retire` (custom→native), `hold` (with reason), `keep`
   (custom still justified — record why per rule 6).

## Guardrails

- **Never introduce a `ubi:` pin.** The ubi backend is deprecated (warns since mise
  2026.4.0, REMOVED in 2027.1.0); its niche (prebuilt GitHub-release binary) is the
  `github:` backend — vfox is the *plugin-system* recommendation, not a ubi
  replacement. Verify any backend's live docs page
  (`mise.jdx.dev/dev-tools/backends/<name>.html`) before proposing a pin.

- **In-image config edits cascade.** Bumping a pin in `mise-system.toml` /
  `hk-image.pkl` / `hk-common.pkl` busts the base content-hash → cold rebuild.
  Batch those (Phase 1), don't drip them.
- **Retire in the same change** that adopts the native path, and sync the docs
  that describe the retired code (`P2996-CACHE.md`, the `AGENTS.md` files) — rule
  5.
- **Renovate already owns routine bumps.** This skill is for the judgment layer
  (custom→native retirement, cross-file parity) Renovate can't do, not for
  re-doing what a Renovate PR already proposes.

## Related

- `.claude/rules/tool-currency-and-native-first.md` — the rule this implements.
- `.claude/rules/use-tool-builtins.md` — prefer built-ins over inventing.
- `.claude/rules/research-doc-sources.md` — the cache-first doc chain step 4 walks.
- Memory: `feedback_research_release_notes_native_first`,
  `feedback_content_hash_must_cover_copy_inputs`.
