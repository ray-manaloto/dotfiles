# Spec — fix round 4: close the fix-round-3 cold-review LOWs (rows 1, 3-8)

Review: `docs/research/kb/reports/agents/cold-reviewer-llvm-fix3-4d6c666c-2026-10-03.md` (0 HIGH/MEDIUM, 8 LOW). Row 2
(automerge before arm64 serves the snapshot) is ticketed separately; it is out of scope here. Lane llvm23. Pins stay
at 22. The line numbers below are the review's, at 4d6c666c; re-read them.

## 1. Objective

Make every claim the fix-round-3 diff added true, and close the latent drift between its three encodings of one rule.

## 2. Files

`renovate.json`, `python/src/dotfiles_setup/apt_liveness.py`, `python/src/dotfiles_setup/llvm_major.py`,
`tests/test_apt_liveness.py`, `tests/test_llvm_major.py`, `tests/test_renovate_validate.py`.

## 3. Required behaviour

- **Row 1:** the LLVM rule's description (`renovate.json:116`) and any test or commit wording must NOT claim a
  minimumReleaseAge soak. The deb datasource emits no `releaseTimestamp`, and `timestamp-optional` proceeds when it is
  missing, so there is no soak. Say so plainly. If `tests/test_renovate_validate.py:227` asserts only the config value
  as if it proved a soak, rename or retarget it so it claims only what it checks. Do NOT add a soak mechanism (out of
  scope).
- **Row 3:** the customManager description (`renovate.json:240`) says 58 LLVM entries (52 active + 6 commented), plus
  the 14 Ubuntu entries.
- **Row 4:** the apt_liveness report footer (`apt_liveness.py:146`) says index presence is not installability, and
  that `verify-apt-pins` checks installability of ACTIVE pins on one platform only. No broader claim.
- **Row 5:** bind the Ubuntu pocket URLs. `parity_violations` (or a dedicated check it calls) requires exactly the three
  pocket registryUrls — release (archive), updates (archive), security (security), each `components=main`
  `binaryArch=amd64` — on the Ubuntu-pockets rule, with the codename derived the same way the LLVM template check
  derives it. Add both arms to the tests: delete the rule → violation; correct config → clean.
- **Row 6:** `apt_liveness` turns a truncated or corrupt gzip (`EOFError`, `zlib.error`, `gzip.BadGzipFile`) and a
  malformed paragraph (`KeyError`) into the same clean failure path as the other fetch and parse errors (rc 1, a
  message naming the URL). Add a test that feeds truncated gzip bytes with status 200 → rc 1, with no traceback.
- **Row 7:** ONE definition of the apt.llvm.org snapshot signature. Keep `llvm_major._APT_LLVM_VERSION` (anchored, epoch
  REQUIRED) as the truth. Make the Renovate `matchCurrentValue`, its `!/…/` negation and the `llvmMajor` capture agree
  with it (anchored where Renovate's semantics allow, epoch required). Add a parity check that the three renovate.json
  strings equal what `llvm_major` expects, and a test with an epoch-less snapshot-like value proving all three
  encodings classify it the same way.
- **Row 8:** `bootstrap_pins` RAISES on a duplicate package name (active or commented), naming both lines. Add a test.

## 4. Constraints

No pin, `_.path`, Dockerfile, lockfile, IWYU or workflow change. Zero inline suppressions; ruff, ruff format and ty
clean. Targeted pytest only: `tests/test_apt_liveness.py tests/test_llvm_major.py tests/test_renovate_validate.py
tests/test_p2996_single_literal.py tests/test_workflow_hooks.py`. Static: `uv run --project python dotfiles-setup
renovate-validate`, `token-audit`, `mise run llvm-parity`. No docker, verify-apt-pins, full pytest, lint or verify.

## 5. Verification

The unit arms listed above, each shown failing against the pre-fix code (mutation or a before/after run), plus
`mise run llvm-parity` rc 0 and `mise run apt-liveness -- --markdown` rc 0 live (72 published).

## 6. Commit

`lane`: ONE commit, `fix(llvm): …`, with the dispatch's attribution lines. Never push.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | E | deb datasource sets no releaseTimestamp; timestamp-optional proceeds without one | review row 1 (read from the pinned Renovate 44.132.2 dist) |
| 2 | L | the customManager description says "52 LLVM entries"; its matchStrings extract 58 | `renovate.json:240`; review row 3 |
| 3 | L | the footer claims verify-apt-pins checks installability broadly | `apt_liveness.py:146`; `apt_pins.py:96-108` |
| 4 | L | the Ubuntu pocket URLs are unbound by any gate | `llvm_major.py:553-560`; `renovate.json:73-84` |
| 5 | L | the except tuple misses EOFError, zlib.error and KeyError | `apt_liveness.py:69`, `:161-167` |
| 6 | L | three signature encodings disagree on an epoch-less value | `llvm_major.py:44`; `renovate.json:78,123,245` |
| 7 | L | bootstrap_pins keys by name, so a duplicate collapses silently | `llvm_major.py:185-200` |
