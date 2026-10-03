# Spec — fix round 2: hold IWYU to the pinned major, and surface held/due bumps daily (cold-review F8)

Parent: `docs/specs/llvm-major-detect-bump.md` rev 3 + `docs/specs/llvm-major-detect-bump-fix1.md`. Ruling: the
coordinator (2026-10-02) ruled that F8 is IN this PR. It breaks Ray's intent of one consistent clang major across
apt and conda. Lane llvm23. Line numbers are at the branch HEAD after fix round 1; re-read them.

## 1. Objective

The rev-3 IWYU gate holds apt LLVM back until IWYU is ready, but nothing holds IWYU back to apt.
`"conda:include-what-you-use" = "latest"` (`.devcontainer/mise-system.toml` ~:69) plus the daily `lock-image` refresh
(`.github/workflows/refresh.yml` ~:367) will move IWYU to a libllvm23 build the day conda-forge ships one, while
apt clang stays at 22. Nothing reports a held or due bump either, because `llvm-detect` runs nowhere.

After this round:
(a) IWYU is pinned to the newest conda-forge version whose linux builds target libllvm{P}. The pin is DERIVED by
code, never hand-typed. An offline parity check fails if the lock's IWYU builds target any other libllvm.
(b) `llvm-bump` moves the IWYU pin together with apt.
(c) A daily `refresh.yml` job upserts one standing issue when llvm-detect returns 3 (due) or 4 (held), and closes it
on 0.

## 2. Files

- `python/src/dotfiles_setup/llvm_major.py`
- `tests/test_llvm_major.py`
- `python/src/dotfiles_setup/standing_issue.py` (new) + `tests/test_standing_issue.py` (new)
- `python/src/dotfiles_setup/main.py` (register `standing-issue`; add `llvm-detect --markdown`)
- `mise.toml` (task `standing-issue` thin caller, if a task is the house pattern for CI calls; else call the CLI
  through `uv run --project python dotfiles-setup …` as the other refresh jobs do; match the precedent)
- `.devcontainer/mise-system.toml`: the `conda:include-what-you-use` value only, plus its comment (~:50-56)
- `.github/workflows/refresh.yml`: a new job, `llvm-currency`
- `.devcontainer/mise-system.lock`: NO edit. The current lock already holds iwyu 0.26 / libllvm22, and a version pin
  of "0.26" resolves to the same entry. If `mise run lint`'s `mise_lock_integrity` or the parity check disagrees,
  report it as a finding; do not run lock-image locally.

## 3. Interfaces / required behaviour

```python
def iwyu_versions_for(major: int, fetch: Fetcher) -> list[str]
    # From the conda-forge /files JSON (same filtering as iwyu_ready: label "main", subdirs linux-64 AND
    # linux-aarch64). For EACH version V, and for EACH of the two subdirs, take the newest build of V by
    # build_number (tie handling as in fix1 F10). Return every V (numeric ascending order) whose newest builds
    # in BOTH subdirs depend on libllvm{major}. Raises on the same shape errors as iwyu_ready.

def iwyu_ready(major, fetch) -> bool          # REDEFINED: bool(iwyu_versions_for(major, fetch))
    # Rev 3 looked only at the NEWEST version. That turns the gate false for 23 forever once a clang-24 IWYU
    # (0.28) ships, even though 0.27 targets 23.

def iwyu_pin_for(major, fetch) -> str        # max(iwyu_versions_for(major)); RAISE if empty

def iwyu_lock_majors(lock_text: str) -> dict[str, int]
    # OFFLINE: for the lock's [tools."conda:include-what-you-use"] platform entries linux-x64 and linux-arm64
    # (the -musl variants are ignored, matching the image), the libllvm<N> major in conda_deps. Raise if either
    # platform is missing or has no single libllvm dep.
```

- `parity_violations` adds an OFFLINE check: `iwyu_lock_majors(.devcontainer/mise-system.lock)` must be {P, P}.
  Otherwise report "IWYU lock targets libllvm<N>, apt pins are <P>".
- `parity_violations` also requires the `conda:include-what-you-use` value to be an exact version (digits and dots).
  `"latest"` is a violation.
- `plan_bump(T)` also rewrites the IWYU pin to `iwyu_pin_for(T)`, with an occurrence assertion as in fix1 F4. The
  post-write "Next: mise run lock-image" line is already present; keep it.
- Add `llvm-detect --markdown`: a short report (pinned, newest GA, served map, iwyu map, target, held_on, reason).
  The exit codes are unchanged: 0 / 3 / 4 / 1.
- `standing-issue --repo R --title T (--body-file F | --close --close-comment C)`: a python port of the existing
  `tool-currency` upsert logic (`refresh.yml` ~:182-222). It matches the EXACT title among open issues (search,
  then filter by equality). If one is found it edits the body or closes it; if none is found and not `--close`, it
  creates the issue with `--label dependencies,needs-triage`. All `gh` calls go through an injectable runner;
  argv only, never shell strings. Do NOT refactor the existing tool-currency job (scope).
- `refresh.yml` job `llvm-currency`: the same guards as `tool-currency`: `if: github.event_name != 'pull_request'`,
  `permissions: {contents: read, issues: write}`, `timeout-minutes: 30`, and the SAME pinned action SHAs as that job
  (checkout, `./.github/actions/setup-mise`). `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` is set for llvm-detect's gh api
  calls. Steps:
  1. Run `llvm-detect --markdown` into `/tmp/llvm-currency.md` and capture its rc in a step output. The job FAILS on
     rc 1 or any rc not in {0, 3, 4}.
  2. On rc 3 or 4: `standing-issue … --title "LLVM major currency (daily)" --body-file /tmp/llvm-currency.md`.
  3. On rc 0: `standing-issue … --close --close-comment "LLVM major current, nothing held."`.
  4. Upload the report as an artifact with `if: always()`, mirroring the tool-currency job.
- `.devcontainer/mise-system.toml`: set `"conda:include-what-you-use" = "<iwyu_pin_for(22)>"`, computed live by the
  lane and expected to be "0.26". Rewrite the comment to say the pin is derived and parity-held to the apt major.

## 4. Constraints

- No apt pin, `_.path`, Dockerfile ARG or Renovate change. No lockfile edit. No local lock-image, docker or
  `verify-apt-pins`.
- Zero inline suppressions. ruff, ruff format and ty clean. actionlint/zizmor-clean workflow YAML (they run in
  `mise run lint`, which the coordinator runs at ship; the lane may run `actionlint .github/workflows/refresh.yml`
  and `zizmor .github/workflows/refresh.yml` directly, because both are static).
- `mise run pin-actions` is static: run it.
- Gates: targeted pytest of `tests/test_llvm_major.py tests/test_standing_issue.py` only, under the coordinator's
  small-file exception.

## 5. Verification (each armed both ways)

1. Unit tests, built from the saved raw response
   `docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json`:
   - THE COORDINATOR'S ARM: add a synthetic 0.27 whose linux builds depend on libllvm23 → `iwyu_pin_for(22)` is still
     "0.26", and `iwyu_versions_for(23)` == ["0.27"].
   - Add a synthetic 0.28 on libllvm24 as well → `iwyu_ready(23)` is still True. This is the rev-3 regression arm:
     it must FAIL against the rev-3 newest-only implementation (show the mutation).
   - A lock fixture whose IWYU conda_deps say libllvm23 while P = 22 → a parity violation naming IWYU. The real lock
     → clean. `"latest"` as the IWYU value → a violation.
   - standing-issue: an exact-title match edits; a near-miss title (`… (daily) old`) is not touched and a new issue
     is created; `--close` with no match is a no-op returning rc 0; runner argv asserted.
   - CLI `llvm-detect --markdown` returns rc 4 on a held fixture with the reason in the body.
2. Live, read-only: `iwyu_pin_for(22)` → "0.26", printed; `mise run llvm-parity` → rc 0 after the pin edit;
   `mise run llvm-detect -- --markdown` → rc 4, body printed.
3. `mise run pin-actions` → rc 0; `actionlint .github/workflows/refresh.yml` and `zizmor .github/workflows/refresh.yml`
   → rc 0 (via `mise exec --`).

## 6. Commit

`lane`: ONE commit `fix(llvm): …`, with the attribution lines given in the dispatch. Never push.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | `"conda:include-what-you-use" = "latest"` | `.devcontainer/mise-system.toml:69` (after round 1) |
| 2 | L | lock iwyu 0.26 build `_1`, linux-x64 + linux-arm64, conda_deps libllvm22 | `.devcontainer/mise-system.lock:3501-3553` |
| 3 | L | refresh runs `mise run --skip-tools lock-image -- --no-container` | `.github/workflows/refresh.yml:367` |
| 4 | P | standing-issue upsert shape (exact-title filter, close-on-clean, create with labels) | `.github/workflows/refresh.yml:161-230` |
| 5 | E | conda-forge iwyu versions 0.17-0.26; 0.26 linux builds on libllvm22; none on libllvm23 | saved raw JSON (rev 3 row 24) |
| 6 | A | conda-forge maps one IWYU version to one clang major (0.25→21, 0.26→22, observed). A version pin therefore holds the major. The parity lock check is the backstop if a same-version rebuild ever retargets |
| 7 | A | Renovate does not manage `conda:` entries in mise-system.toml (`renovate.json` has no conda manager or rule). If it ever proposes an IWYU bump, the parity check fails that PR |
