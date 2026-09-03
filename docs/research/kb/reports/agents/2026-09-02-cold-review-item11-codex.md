# Cold review — commit 96d7067 (ITEM 11 vendored schemas) — CODEX lens

Lane: `fable-orchestrator:codex-reviewer` (GPT-5.6 Sol, xhigh), 2026-09-02c.
Reviewed by REF: `96d7067` vs parent `df95413`. Cold — the brief withheld intent.
Persisted verbatim by the architect (the lane reported by message, not to a file).

Sibling lens, run on the same ref: `2026-09-02-cold-review-item11-opus.md`.
The two found **disjoint** defect sets; see the architect's note at the bottom.

---

## Critical — the byte-verbatim claim is unsubstantiated and unmonitored

**`check_drift` never compares content, only a version string, and nothing else in the diff does either.** `python/src/dotfiles_setup/schema_vendor.py:186-207` (`check_drift`) reads `schemas/sources.toml`'s recorded `version` and compares it against the *current pin* resolved from three unrelated local files (shared.toml / uv.lock / setup-mise action.yml). It never hashes or re-fetches the vendored JSON. `schemas/sources.toml` itself carries no checksum field (`schemas/sources.toml:1-29` — `tool`/`file`/`version`/`source`/`pin_source`, no `sha256`). The suite that wires this into `mise run verify` says so itself: `python/verification/suites.toml:2415` — *"WHAT THIS CONTRACT CANNOT DO: it cannot prove the vendored JSON is itself valid JSON Schema, or that taplo actually reads it… this suite only proves the recorded version has not gone stale."*

Consequence: if `schemas/mise.json` (or ruff.json/typos.json) is hand-edited or swapped for arbitrary content while `sources.toml`'s `version` field is left untouched, **every gate in this diff reports clean forever** — `check_drift` compares two facts neither of which is the file's own bytes, and the `refresh` path (`schema_vendor.py:246` `fetched != existing`) is CI-only, runs on a schedule/dispatch, and only fires when the *tool's pin* also happens to differ or drift is otherwise triggered — it is not a gate anyone is forced through on every commit. `hk-common.pkl:95-105` additionally removes even `check_added_large_files`/`detect_private_key` coverage from these three files (see below), so no other layer would notice a swap either. This is exactly the "comparison against a value derived from the same source it is validating" pattern the brief asked me to hunt for: `sources.toml` and the vendored JSON are both written by the same `refresh()` call, so the check can only ever validate self-consistency between two files this repo controls, never fidelity to upstream.

## Medium — the hk exclusion is broader than its stated justification

`hk-common.pkl:95-105` adds `schemas/{mise,ruff,typos}.json` to the **shared** `excludePaths` list, which — per the file's own header (`hk-common.pkl:19-38`) — feeds every builtin in the `hygiene` and `safety` groups (trailing whitespace, `check_added_large_files`, `detect_private_key`, `check_merge_conflict`, etc.), not just `typos`. The added comment justifies the exclusion solely by a `typos` false-positive on a ruff rule code. Practically low-risk today (mise.json 173 KB, ruff.json 200 KB, both likely under the large-file threshold; these aren't credential-shaped files), but the exclusion silences more scanners than the stated reason covers, and it's the second layer (after the drift-check gap above) that would have to catch a tampered vendor file and doesn't.

## Low — `schemas/` prefix exclusion in `platform_target.py` is directory-scoped, not file-scoped

`python/src/dotfiles_setup/platform_target.py:153-166` adds `"schemas/"` to `_SCAN_EXCLUDED_PREFIXES`, justified by the three vendored files' own `os`/`arch` example strings. Any future file placed under `schemas/` (not just the three vendored JSONs) inherits the exemption from the platform-literal scanner silently. Minor — the directory currently holds only the vendored files + `sources.toml`, and the rationale is documented, but the exclusion is wider than what it argues for.

## Config/workflow correctness — no defects found

`refresh.yml` `schema-refresh` job (`.github/workflows/refresh.yml:466-529`): `if: github.event_name != 'pull_request'`, `concurrency: {group: schema-refresh, cancel-in-progress: false}`, job-level `permissions: contents: read` with the App token separately minted at `permission-contents: write` / `permission-pull-requests: write` — structurally identical to the existing `lock-refresh` job and reuses the shared `open-refresh-pr` composite, which is a documented no-op when no tracked path changed (`open-refresh-pr/action.yml:60-67`). No loop risk, no `pull_request`-trigger self-fire risk. `create-github-app-token`/`checkout` SHAs match the pins used elsewhere in the same file (verified byte-for-byte) — not a supply-chain swap.

**Branches actually read to support "no defects found":**

- `.github/workflows/refresh.yml:466-529` (the full `schema-refresh` job body, trigger, permissions, concurrency, App-token mint step, checkout, install, refresh-run, PR-open step and its inline body).
- `.github/actions/open-refresh-pr/action.yml` in full (60 lines — the composite's inputs, the `create-pull-request` call, and the conditional auto-merge step) — confirmed the `if: steps.cpr.outputs.pull-request-number != ''` guard is what makes it a no-op on no drift, and that `add-paths` (not a blanket `git add`) scopes what gets committed.
- Diffed `create-github-app-token@<sha>` and `actions/checkout@<sha>` against their other two occurrences already in the file (`grep -n` across all four call sites) rather than trusting the diff hunk alone — same SHA reused, not newly introduced.
- Did **not** independently re-verify `peter-evans/create-pull-request`'s own SHA pin or its upstream behavior beyond reading this composite's usage of its outputs — that action predates this diff and isn't part of the change under review.

## Conceded after architect correction

- `hk.pkl:26`/`hk-image.pkl:26` top-level `exclude` is the correct citation — the lane checked only the group-level spread and should have gone one level up. Confirmed by reading both lines.
- The gitleaks mitigation holds: `hk-common.pkl:28-38`'s own header states the exclude list never constrained gitleaks (scoped separately by `.gitleaks.toml`, untouched by this diff), so secret-shaped content in the vendored files would still be caught. What is lost is specifically `detect_private_key` and hygiene/format-shaped checks, plus every other `{{files}}`-consuming step in the whole suite — not just hygiene/safety.

---

## Architect note

Both Medium and Low were **narrowed by measurement** in the refutation pass: only
`schemas/ruff.json` trips typos (one token, `CPY`), and only `schemas/mise.json`
carries a platform literal (1 hit). See the respec.

## GitHub repos touched

_None._ All reads were local to this repo.
