# Spec — fix round 2 (rev 2): hold IWYU to the pinned major, and surface held/due bumps daily (cold-review F8)

Parent: `docs/specs/llvm-major-detect-bump.md` rev 3, and `docs/specs/llvm-major-detect-bump-fix1.md` (implemented in
4b56cf59). Ruling: the coordinator (2026-10-02) ruled that F8 is IN this PR, because it breaks Ray's intent of one
consistent clang major across apt and conda. Rev 2 applies the premise-verifier report
`docs/research/kb/reports/agents/premise-verifier-llvm-fix2-2026-10-02.md` (3 blockers + corrections). Lane llvm23.

## 1. Objective

The rev-3 IWYU gate holds apt LLVM back until IWYU is ready, but nothing holds IWYU back to apt.
`"conda:include-what-you-use" = "latest"` (`.devcontainer/mise-system.toml:69`) will drift. The daily `lock-refresh`
job (`refresh.yml:108` → `.github/actions/lock-refresh/action.yml:57` `mise run lock-image -- --no-container`) and
the Renovate-PR `image-lock-pr` job (`refresh.yml:367`) both call `image_lock.py:289` `mise lock --bump`. Either
would move IWYU to a libllvm23 build the day conda-forge ships one, while apt clang stays at 22. Nothing reports a
held or due bump either, because `llvm-detect` runs nowhere.

After this round:
(a) IWYU is pinned to the newest conda-forge version whose linux builds target libllvm{P}. The pin is DERIVED by
code, and an offline parity check fails when the lock's IWYU targets another libllvm.
(b) A real `llvm-bump` moves the IWYU pin together with apt.
(c) A daily `refresh.yml` job upserts one standing issue on llvm-detect rc 3 (due) or 4 (held), and closes it on 0.

## 2. Files

- `python/src/dotfiles_setup/llvm_major.py`
- `tests/test_llvm_major.py`
- `python/src/dotfiles_setup/standing_issue.py` (new) + `tests/test_standing_issue.py` (new)
- `python/src/dotfiles_setup/main.py`: register `standing-issue`; add `llvm-detect --markdown`. `parity_violations`
  scans main.py for LLVM literals, so the new code must not contain strings like `clang-<digits>`.
- `mise.toml`: a task `standing-issue` as a thin caller (house precedent: refresh jobs call python through
  `mise run <task>`, e.g. `refresh.yml:181`, `:367`, `:544`).
- `.devcontainer/mise-system.toml`: only the `conda:include-what-you-use` value (a plain string, not table form) and
  its comment (:52-56).
- `.github/workflows/refresh.yml`: a new job, `llvm-currency`.
- `tests/test_workflow_hooks.py`: add `(".github/workflows/refresh.yml", "llvm-currency")` to `EXPECTED_JOBS` (~:85-112,
  an exact set), and add it to `REAL_CASES` (~:70-76) as a non-git-writer (`False`), like `tool-currency`.
- `.devcontainer/mise-system.lock`: NO edit. It already holds iwyu 0.26 / libllvm22, and a "0.26" pin resolves to
  that entry. If any check disagrees, report it as a finding; do not run lock-image.

## 3. Interfaces / required behaviour

```python
_LIBLLVM = re.compile(r"^libllvm(\d+)\b")   # factor out of iwyu_ready (llvm_major.py ~:298-302); reuse everywhere

def iwyu_versions_for(major: int, fetch: Fetcher) -> list[str]
    # Same /files JSON and filtering as iwyu_ready (label "main"; subdirs linux-64 AND linux-aarch64). Group by
    # version. SKIP a version that lacks a main build in either subdir (0.17-0.20 have no linux-aarch64 build).
    # For each remaining version, take the newest build per subdir by `_iwyu_build_key` (with the fix1 F10 tie rule)
    # and apply the existing per-build shape checks: exactly one libllvm dep, else raise. Return, in numeric
    # ascending order, every version whose newest build in BOTH subdirs depends on libllvm{major}. Raise on non-200,
    # non-JSON, or zero usable versions overall.

def iwyu_ready(major, fetch) -> bool         # REDEFINED: bool(iwyu_versions_for(major, fetch))
def iwyu_pin_for(major, fetch) -> str       # max(iwyu_versions_for(major)); raise if empty

def iwyu_lock_state(lock_text: str) -> tuple[str, dict[str, int]]
    # OFFLINE, via tomllib: tools["conda:include-what-you-use"][0] → (its "version", {platform: libllvm major}) for
    # the platforms "platforms.linux-x64" and "platforms.linux-arm64" only. The -musl, -baseline and
    # -musl-baseline variants are ignored. Major comes from `conda_deps` entries such as
    # "libllvm22-22.1.8-h474f4eb_3" through _LIBLLVM. Raise if either platform is missing or does not have exactly
    # one libllvm dep.
```

- `parity_violations` adds two OFFLINE checks, each with its own violation class:
  - **IWYU pin**: the `conda:include-what-you-use` value must be a plain exact version (`^\d+(\.\d+)+$`); `"latest"`
    or table form is a violation.
  - **IWYU lock**: the lock version from `iwyu_lock_state` must equal the toml pin AND both platform majors must equal P.
    Otherwise report "IWYU lock stale or off-major: lock <ver>/libllvm<N>, toml <pin>, apt <P> — run `mise run lock-image`".
- **The `--major` dry-run control (blocker 2):** it keeps its contract (no detection, no gates, never fetches
  anaconda; `tests/test_llvm_major.py` ~:451-453 must still pass). The IWYU line is NOT planned in control mode; the
  plan header says `IWYU pin: not planned (explicit control; gates skipped)`. Therefore
  `llvm-bump --dry-run --major 23` stays rc 0.
- **A real bump (blocker 3):** `plan_bump(T)` in the detected path rewrites the IWYU pin to `iwyu_pin_for(T)` with a
  `_rewrite_once` occurrence assertion. After writing, `llvm-bump` runs parity EXCLUDING the IWYU-lock class (the
  lock cannot be current until `mise run lock-image` regenerates it) and returns that rc. It also prints
  `Next: mise run lock-image (IWYU lock is now stale by design)`. The full parity (hk `llvm_major_parity`, which
  includes the IWYU-lock class) stays red on the bump branch until lock-image runs. That is the intended forcing
  function: a bump PR must carry its regenerated lock. Name this flow in the mise-system.toml comment.
- `llvm-detect --markdown`: a short report built from `Detection` + `asdict` (pinned, newest GA, served map, iwyu map,
  target, held_on, reason). Exit codes unchanged (0/3/4/1). Keep the `"23 GA+served, held: IWYU"` prefix, and update
  the rest of the reason text (~:354-357), which still describes the old newest-only rule. Keep `detect_main`'s
  signature compatible with `tests/test_llvm_major.py` ~:631, or update that test.
- `standing-issue --repo R --title T (--body-file F | --close --close-comment C)`: a python port of tool-currency's
  upsert (`refresh.yml:182-222`). Behaviour:
  - Search with `gh issue list --search 'in:title "<T>"'`, then select by EXACT title equality.
  - If found: edit the body, or close it with the comment.
  - If not found and not `--close`: create with `--label dependencies,needs-triage`.
  - If not found and `--close`: a no-op, rc 0.
  - Argv lists only, through an injectable runner.
  Do NOT refactor the tool-currency job.
- `refresh.yml` job `llvm-currency`:
  - `if: github.event_name != 'pull_request'` (refresh.yml triggers on pull_request, :46-47); `runs-on:
    ubuntu-latest`; `timeout-minutes: 30`; `permissions: {contents: read, issues: write}`.
  - checkout `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` with `persist-credentials: false`;
    `uses: $/.github/actions/setup-mise` (the `$/` form, NOT `./`: see `refresh.yml:106,179`).
  - `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` and `REPO: ${{ github.repository }}` via `env:`.
  - Step `detect` (`id: detect`): `run: | set -uo pipefail; rc=0; mise run llvm-detect -- --markdown >
    /tmp/llvm-currency.md || rc=$?; echo "rc=$rc" >> "$GITHUB_OUTPUT"; case "$rc" in 0|3|4) ;; *) exit "$rc";; esac`.
  - Upsert step: `if: steps.detect.outputs.rc == '3' || steps.detect.outputs.rc == '4'`, running
    `mise run standing-issue -- --repo "$REPO" --title "LLVM major currency (daily)" --body-file /tmp/llvm-currency.md`.
  - Close step: `if: steps.detect.outputs.rc == '0'`, running `mise run standing-issue -- --repo "$REPO" --title
    "LLVM major currency (daily)" --close --close-comment "LLVM major current, nothing held."`.
  - Never interpolate `${{ steps.* }}` inside `run:`.
  - Artifact: `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1`, `if: always()`,
    `if-no-files-found: ignore`.
  - Do NOT copy these tokens, which suites.toml/token-audit bind to existing jobs: `tool-currency:\n    # Never on
    pull_request`, `mise run tool-currency >`, `Tool currency report (daily)`, `lock-refresh:`,
    `uses: $/.github/actions/lock-refresh`, `run: mise run --skip-tools lock-image -- --no-container`.
- `.devcontainer/mise-system.toml`: `"conda:include-what-you-use" = "<iwyu_pin_for(22), computed live>"` (expected
  "0.26"). The comment says the pin is derived, parity-held to the apt major, and moved by `llvm-bump` + `lock-image`.

## 4. Constraints

- No apt pin, `_.path`, Dockerfile ARG, Renovate or lockfile change. No lock-image, docker or verify-apt-pins.
- Zero inline suppressions. ruff, ruff format and ty clean.
- Static workflow checks the lane MAY run: `mise exec -- actionlint .github/workflows/refresh.yml`,
  `mise exec -- zizmor .github/workflows/refresh.yml`, `mise run pin-actions`, and
  `uv run --project python dotfiles-setup token-audit`.
- Targeted pytest ONLY: `tests/test_llvm_major.py tests/test_standing_issue.py tests/test_workflow_hooks.py`.

## 5. Verification (each armed both ways)

1. Unit tests, with fixtures from `docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json`:
   - THE COORDINATOR'S ARM: add a synthetic 0.27 with linux builds on libllvm23 → `iwyu_pin_for(22)` is still "0.26"
     and `iwyu_versions_for(23)` == ["0.27"]. A lock fixture whose IWYU conda_deps are libllvm23 (P = 22) → a parity
     violation naming IWYU; the real lock → clean.
   - Rev-3 regression: also add a synthetic 0.28 on libllvm24 → `iwyu_ready(23)` is still True. Show that this test
     FAILS against the newest-only rule (mutation).
   - 0.17-0.20 (no aarch64) are skipped, not raised on.
   - IWYU pin `"latest"` → violation; table form → violation; a lock version ≠ toml pin → violation.
   - Control: `plan_bump` in `--major` mode never calls the anaconda fetcher and reports "not planned".
     Detected-path bump: the IWYU pin is rewritten exactly once, the post-write rc excludes the lock class, and the
     "Next: mise run lock-image" line is printed.
   - standing-issue: an exact-title match is edited; a near-miss title is untouched and a new issue is created;
     `--close` with no match is a no-op returning rc 0; the runner argv is asserted.
   - CLI: `llvm-detect --markdown` returns rc 4 on a held fixture, with the reason in the body.
   - `tests/test_workflow_hooks.py` passes with the new job in `EXPECTED_JOBS`.
2. Live, read-only: print `iwyu_pin_for(22)` (expect "0.26") and `iwyu_versions_for(23)` (expect []). After the pin
   edit, `mise run llvm-parity` → rc 0, and `mise run llvm-detect -- --markdown` → rc 4 with the body printed.
3. actionlint, zizmor, pin-actions and token-audit as listed in §4 → rc 0 each.

## 6. Commit

`lane`: ONE commit, `fix(llvm): …`, with the dispatch's attribution lines. Never push.

## 7. PREMISES (verified rows from the premise-verifier report; line numbers at HEAD 4b56cf59 + spec commits)

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | `"conda:include-what-you-use" = "latest"`; comment :52-56 | `.devcontainer/mise-system.toml:69` |
| 2 | L | lock: version "0.26"; linux-aarch64 `…0.26-hfae3067_1.conda` with dep `libllvm22-22.1.8-h680871c_3`; linux-64 `…0.26-hecca717_1.conda` with dep `libllvm22-22.1.8-h474f4eb_3`; six platform entries (incl. -musl, -baseline, -musl-baseline) | `.devcontainer/mise-system.lock:3501-3616` |
| 3 | L | daily lock regen = `lock-refresh` → `action.yml:57` `mise run lock-image -- --no-container`; Renovate-PR regen = `image-lock-pr` `refresh.yml:367`; both → `image_lock.py:289` `mise lock --bump` | verifier row 3 |
| 4 | P | tool-currency guards/SHAs/upsert shape | `refresh.yml:161-230` |
| 5 | E | saved JSON: main versions 0.17-0.26, one libllvm per build, 0.26 `_0`/`_1` on libllvm22, no libllvm23; 0.17-0.20 lack linux-aarch64 | verifier row 5 + MISSING |
| 6 | A | conda-forge maps one IWYU version to one clang major (0.17→13 … 0.26→22). The lock parity check is the backstop for mise's partial-pin `--bump` semantics, which are unverified |
| 7 | A | Renovate has no conda manager here (`renovate.json:243-252`; `mise-system.toml:41-47`). The jdx preset is unread. A Renovate IWYU bump would fail parity |
| 8 | L | `EXPECTED_JOBS` is an exact set; `REAL_CASES` lists tool-currency as a non-writer | `tests/test_workflow_hooks.py:70-112` |
| 9 | L | `--major` control contract: "explicit dry-run control; detection and gates skipped" and a test that asserts no anaconda fetch | `llvm_major.py:705`; `tests/test_llvm_major.py:451-453` |
| 10 | L | post-write `_bump` returns `parity_main(root)`; hk step `llvm_major_parity` has no glob | `llvm_major.py:714-716`; `hk.pkl:285-287` |
| 11 | L | in-repo actions use the `$/` form; actionlint suppresses only that form | `refresh.yml:106,179`; `.github/actionlint.yaml:17-34` |
