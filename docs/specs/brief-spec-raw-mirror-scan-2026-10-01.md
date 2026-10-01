# Spec — raw-mirror secret-scan allowlists + instruction-file exemption

Branch `fix/raw-mirror-scan-exemptions` (already checked out, at origin/main `3a861923`) in the MAIN checkout
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`. Ray's rulings 2026-10-01 (AskUserQuestion): (1) replace path-anchored
secret-scan allowlists for raw mirrors with CONTENT-ANCHORED entries scoped to `docs/research/kb/raw/**`; (2) EXEMPT
`docs/research/kb/raw/**` from `claude_md_import_stub` and `claude_agents_md_pairs` (mirrors stay byte-verbatim,
`.claude/rules/agent-artifact-conventions.md` rule 8). Related ticket: #1472 (reference it; do not close it — it also
covers the mirror destination question).

## 1. Objective

### A. `.gitleaks.toml` — content-anchored, RULE-SCOPED entries (both gitleaks 8.30.1 and betterleaks 1.9.0 read this file)
Add, each with a comment saying what was read and judged and why it is not a secret:
1. GitHub commit/tree/blob URL SHAs (gitleaks `sourcegraph-access-token` fires on the 40-hex):
   `condition="AND"`, `targetRules=["sourcegraph-access-token"]`, `regexTarget="line"`,
   `regexes=['''github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(commit|tree|blob)/[0-9a-f]{40}''']`,
   `paths=['''(^|/)docs/research/kb/raw/''']`.
2. Exact judged public values (`generic-api-key`): mise's PUBLIC minisign release key
   `^RWTC3g8W3z4RZK3V3qv7fa1QY4JEWyBtqIHW\+85QlJpZc5yG\+uNYNBSZ$` and the Algolia DocSearch SEARCH-ONLY key in mise's
   vitepress config `^ad09b96a7d2a30eddc2771800da7a1cf$` (DocSearch keys are shipped to every browser by design):
   `condition="AND"`, `targetRules=["generic-api-key"]`, `regexes=[…]`, `paths=['''(^|/)docs/research/kb/raw/''']`.
3. Showreel capture sha256 `"key"` lines: `condition="AND"`, `targetRules=["generic-api-key"]`, `regexTarget="line"`,
   `regexes=['''^\s*"key": "[0-9a-f]{64}",?\s*$''']`,
   `paths=['''(^|/)docs/research/kb/raw/.*/showreel/test/captures/[^/]+\.json$''']`.
4. `my_password` (betterleaks-only rule `generic-password`; gitleaks REFUSES an unknown `targetRules` name):
   a content-only entry `regexes=['''^my_password$''']` with NO `paths` and NO `targetRules`.
5. DELETE the two path-anchored 2026-09-29b mise entries (`…/mise-dotfiles-2026-09-29/mise-docs/mise-cookbook_docker.md`
   and `…/environments.md`) — entries 2 and 4 now cover the same values (the architect confirmed both files contain them).
   KEEP every other existing entry, including the Omarchy one.
6. Add a header comment recording the trap below (P1), so nobody "simplifies" an entry into a global one.

### B. Exempt raw mirrors from the instruction-file pair/stub checks
- `scripts/check-claude-md-stub.sh` and `scripts/check-claude-agents-md-pairs.sh`: widen the existing `.claude/`
  exclusion to also exclude `docs/research/kb/raw/` (e.g. `grep -v -E '^(\.claude|docs/research/kb/raw)/'`). The
  `bash_logic_budget` gate fails on line GROWTH: keep each file's line count ≤ its current count (edit in place,
  including the header comment line that names the exemption).
- Update the matching hk.pkl step comments and any other prose that enumerates these exemptions (grep for
  `.claude/\*\* is exempt` / "exempt" near these step names; root `AGENTS.md` "Subdirectories" paragraph mentions the
  `.claude/` exemption — root AGENTS.md is ~500 chars under agnix's 12,000 cap, so prefer `.claude/CLAUDE.md` or
  `docs/` if the text does not fit).
- ENUMERATE every other gate that reads tracked `AGENTS.md`/`CLAUDE.md` files (agnix `mise run lint-docs`,
  `md_size_budget` / kb-setup md-budget, python `doc_refs.py` or similar, verify contracts) and prove each one with the
  arm in §5. If any other gate also fails on a vendored mirror AGENTS.md/CLAUDE.md, STOP and report it with the
  evidence — do not widen another gate without the architect.

### C. Machine check (armed) — a pytest
New test(s) (e.g. `tests/test_gitleaks_raw_mirror_allowlist.py`) that build a temp tree laid out as
`<tmp>/docs/research/kb/raw/<slug>/…` and run `gitleaks dir -c <repo>/.gitleaks.toml` on it:
- judged-FP fixture (one line per entry 1-4) → rc=0, 0 findings;
- same tree + a planted `ghp_` + 36-alnum token → rc=1, `github-pat` (catches the P1 global-paths trap);
- planted token inside a `…/showreel/test/captures/x.json` → rc=1 (entry 3 must stay rule-scoped);
- a commit-URL SHA OUTSIDE `docs/research/kb/raw/` → still reported (scope holds).
Build EVERY fixture value at runtime by string concatenation so the test source itself never contains a literal any
scanner matches (the hk gitleaks step scans `tests/`). betterleaks is HOST-ONLY (`mise.toml:16`): check whether it
exists in CI and the image before using it in pytest; if it does not, test gitleaks in pytest and record the betterleaks
arm (same four cases) as a command + output in the report. No skips, no `pytest.skip`.

## 2. Files (allowlist)
`.gitleaks.toml`, `scripts/check-claude-md-stub.sh`, `scripts/check-claude-agents-md-pairs.sh`, `hk.pkl` (comments
only unless §B's enumeration proves otherwise — then STOP), the new test file, and at most one prose file for the
exemption note. Report: `docs/research/kb/reports/agents/implement-raw-mirror-scan-2026-10-01.md`.
NOT: `task_plan.md`, `hk-common.pkl` (a base-image build input), `python/src/**` (unless the enumeration finds a python
gate — then STOP), anything under `docs/research/kb/raw/` (do not commit the held files).

## 3. Interfaces
No CLI/API change. `.gitleaks.toml` stays loadable by BOTH gitleaks 8.30.1 and betterleaks 1.9.0 (gitleaks refuses
unknown `targetRules`).

## 4. Constraints
- Zero-skip; no `--no-verify`; hk pre-commit must pass on its own.
- Held files for arming: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/held-2026-09-30/` (8 files;
  paths under it mirror their intended repo paths; `link-4.md` is the cbm mirror). `betterleaks dir` and `gitleaks`
  scanning inside `.agent/` read NOTHING (gitignored / globally allowlisted) — copy to a scratch dir under
  `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/03414a92-bb13-4324-83d2-fac74c0cd046/scratchpad/`
  first. Never commit them. Never print or write a credential-shaped literal into a tracked file or the report.
- Stub/pairs arm: temporarily copy `held-2026-09-30/docs/research/kb/raw/mise-packslip-docs-2026-09-30/packslip/repo-v1.4.0/{AGENTS,CLAUDE}.md`
  into the repo at that path and `git add` them (both scripts read `git ls-files`), run both scripts (rc=0 with the fix,
  rc=1 with the fix reverted in place), then `git rm --cached` + delete them. `git status` must be clean of them before commit.
- `$?` capture: assign `rc=$?` IMMEDIATELY after the command — a `$(…)` before it resets `$?`.
- Never pipe a gate to `tail`; `mise run gate -- run <name>` per gate, one command each (no `for g in` loop).

## 5. Verification (report command, rc, summary)
- `mise run gate -- run lint`, `… pytest`, `… verify`, `… lint-docs` → each 0.
- `betterleaks dir --no-banner -c .gitleaks.toml docs/research/kb` and `… docs/research/runs` → rc=0 on the tracked tree
  AFTER deleting the two 09-29b entries (proves entries 2/4 replace them).
- Both scanners on the scratch copy of all 8 held files laid out under `docs/research/kb/raw/…` → rc=0; + planted
  token → rc=1 in BOTH.
- Mutations, in place (`git diff` clean after each restore): drop `targetRules` from entry 1 / 2 / 3 → the planted-token
  test goes RED (global-paths trap) or the FP test goes red — report which; delete entry 4 → FP test RED (betterleaks arm
  if gitleaks cannot see generic-password: report it); revert the stub/pairs grep → the staged vendored-file arm rc=1.

## 6. Commit
One commit, `fix(scan): content-anchored allowlists and instruction-file exemption for raw mirrors`, body naming Ray's
2026-10-01 rulings, the P1 trap, `Refs #1472`. Trailer:
```
Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Pya9WGydcD4EJHLg9goLPL
```
Stage by explicit path. Do NOT push/ship.

## 7. PREMISES (architect-verified 2026-10-01; re-check any you rely on)
| # | Premise | Evidence |
|---|---|---|
| P1 | A GLOBAL `[[allowlists]]` (no `targetRules`) with `paths` blinds gitleaks 8.30.1 to every file under that path even with `condition="AND"` + `regexes`; rule-scoped entries honour AND in both scanners | scratch probe: global variant → planted ghp_ NOT reported by gitleaks; rule-scoped variant → planted reported rc=1 by both, held FPs 0 |
| P2 | Held FPs: betterleaks 5 (generic-password ×1, generic-api-key ×4: showreel ×2, minisign, algolia); gitleaks 4 generic-api-key + 39 sourcegraph-access-token in link-4.md (all 40-hex SHAs inside `github.com/DeusData/codebase-memory-mcp/commit/<sha>`) | scratch scans, `findings.md` 2026-10-01 |
| P3 | The 09-29b mirror files contain the same minisign key / `my_password` | `grep -c` → 1 / 1 |
| P4 | Stub/pairs scripts exclude by `grep -v '^\.claude/'` over `git ls-files` | `scripts/check-claude-md-stub.sh`, `scripts/check-claude-agents-md-pairs.sh` |
| P5 | `bash_logic_budget` fails on line growth of allowlisted scripts | `.claude/rules/zero-bash-logic.md` |
| P6 | gitleaks is shared (host+image, `.config/mise/conf.d/shared.toml:35`); betterleaks is host-only (`mise.toml:16-21`) | files |

Write the report incrementally. If a premise is refuted or the spec contradicts the code, STOP and report.
