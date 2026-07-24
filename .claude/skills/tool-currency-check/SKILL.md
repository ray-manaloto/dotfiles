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

## The shared engine does the version mechanics

Version currency — in-sync validation, release-note review, tracked-issue
movement, the six-gate auto-apply bar, the committed report — is the **shared
engine** (`kb_setup.currency`, a pinned `uv` git dep on the knowledge-base
package; **one implementation**, D2/G4). This skill's unique value is the
**judgment layer** the engine does not do: is a piece of custom code now
superseded by a native tool feature, and do cross-file pins still agree.

Drive the engine, don't re-derive its work:

```bash
mise run tool-currency                       # the daily report: deep verdicts + broad mise-outdated sweep
uv run --project python kb-setup currency run --tool graphify --json   # deep due-diligence on one tool
uv run --project python kb-setup currency apply --tool graphify        # apply an authorized patch bump (edits pin + manifest)
```

`daily` merges **deep** due-diligence on the tools in `currency.toml` (graphify
here) with a **broad `mise outdated --bump` sweep** of every other pin — so the
signal spans all tools, not just the deep set. `--bump` is mandatory (the engine
passes it): every pin is exact, so bare `mise outdated` can never report
movement (control-armed 2026-07-20: it said "up to date" while graphify sat at
0.9.20 vs PyPI 0.9.22). Tools intentionally held back (comments in `mise.toml`,
e.g. `rtk` for a lockfile bug) are decisions, not drift.

## Procedure

1. **Read the daily report / engine verdict first.** Start from
   `mise run tool-currency` (or the standing issue it feeds) rather than
   re-deriving the outdated set. A deep-tracked tool with an upgrade carries a
   verdict + release-note review already; the broad table lists the rest.

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
