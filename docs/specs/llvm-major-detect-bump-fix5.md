# Spec — fix round 5: release-branch FREEZE gate in the LLVM detector

Ruling: user (Ray), 2026-10-04, via AskUserQuestion: "Build freeze gate now", the option whose text defined the rule:
"M is ready only when release/M.x head equals its latest llvmorg-M tag AND the live -M suite build is that tag (or
tag+1) with no new build for >=2 weeks". Evidence: `docs/research/kb/reports/agents/llvm-apt-pin-churn-research-2026-10-03.md`
§ Recommendation, which found that an exact-pinned -23 breaks the base build about 1-2×/week until release/23.x freezes.
Lane llvm23, branch `feat/llvm-23-detect-bump` (HEAD 09e968a4). Pins stay at 22.

## 1. Objective

The detector today holds 23 only through the conda IWYU gate. The planned IWYU PR (`docs/specs/iwyu-source-build.md`)
redefines IWYU readiness, so that gate alone would lift the hold while apt.llvm.org's `-23` suite still rebuilds from
a moving branch. Add a second, independent readiness gate: a candidate major must be FROZEN. The hold must then survive
any change to how IWYU is sourced.

## 2. Files

`python/src/dotfiles_setup/llvm_major.py`, `tests/test_llvm_major.py`. Comment text only in
`.devcontainer/mise-system.toml`, to name the second gate where the IWYU gate is described (~:50-56). No workflow,
Renovate or pin change.

## 3. Interfaces / behaviour

```python
@dataclass(frozen=True)
class Freeze:            # one candidate major's freeze evidence
    major: int
    branch_head: str      # full SHA of release/<M>.x
    tag: str              # newest GA llvmorg-<M>.<x>.<y> (reuse the existing releases list; prerelease/draft excluded)
    tag_commit: str       # full SHA the tag points at (peeled), via gh api repos/llvm/llvm-project/commits/<tag>
    ahead_of_tag: int     # gh api repos/llvm/llvm-project/compare/<tag>...release/<M>.x → ahead_by
    apt_build: str        # 12-hex commit embedded in the live clang-<M> version "…+<sha12>-1~exp1~…"
    release_date: datetime  # the "Date:" line of dists/llvm-toolchain-<C>-<M>/Release (already fetched by the GATE)
    frozen: bool

def freeze_state(major, codename, fetch, gh, *, now) -> Freeze
    # frozen iff ALL of:
    #   (a) ahead_of_tag <= 1                     (head == tag, or tag + one commit, e.g. a version bump)
    #   (b) apt_build is the 12-char prefix of tag_commit OR of branch_head
    #   (c) now - release_date >= 14 days
    # A 404 for release/<M>.x, an unparsable version/Date, or any non-200 → RAISE (never-asked ≠ no).
```

- `detect`: a candidate N > P is selectable only if `iwyu_ready(N) and freeze_state(N).frozen`. P itself is never
  re-gated (fix2 rule). `Detection` gains `frozen: dict[int, bool]` and the `Freeze` evidence for every probed N > P.
- `held_on` / `reason`: list every gate that blocks the highest served major, in a fixed order: `held: IWYU`,
  `held: freeze`, or `held: IWYU, freeze`. Keep the existing prefix `"<M> GA+served, held: "`. Append a one-line freeze
  summary, e.g. `release/23.x 27 ahead of llvmorg-23.1.2; apt build 67f4a076a097 ≠ tag/head; built 2026-09-22`.
- Exit codes are unchanged: 0 / 3 / 4 / 1. `llvm-detect --markdown` shows the freeze evidence table.
- `now` is injectable (tests). The CLI uses UTC now.
- Reuse the existing fetchers (`default_fetcher` with timeout, the `gh api` releases helper). No new HTTP client, no
  anonymous api.github.com.

## 4. Constraints

- No pin, `_.path`, Dockerfile, Renovate, workflow or lockfile change.
- Zero inline suppressions. ruff, ruff format and ty clean. `parity_violations`' literal scan stays clean.
- Gates: ONLY targeted `uv run --project python pytest tests/test_llvm_major.py -x -q`, under a coordinator
  small-file exception, plus ruff/ty. No lint, full pytest, verify, docker or verify-apt-pins (HOLD).

## 5. Verification (each armed both ways)

1. Unit tests with injected fetch/gh/now, built from the live values below:
   - FROZEN control (the 22 shape): head == tag `ca7933e47d3a…`, ahead 0, apt build `ca7933e47d3a`, Release 2026-07-14,
     now 2026-10-04 → frozen.
   - NOT FROZEN (the 23 shape): ahead 27, apt build `67f4a076a097` (neither tag `85ac56026243…` nor head
     `21ef2ddb8060…`), Release 2026-09-22 → not frozen.
   - Each condition alone flips the result:
     - ahead 2 → not frozen;
     - build == head with ahead 1 → frozen;
     - Release date 13 days old → not frozen, 14 days → frozen.
   - Raises on a release-branch 404, an unparsable version, and a missing Date.
   - detect: IWYU-ready but not frozen → TARGET P, held_on M, reason contains `held: freeze`. Both blocked →
     `held: IWYU, freeze`. Both ready → TARGET M. A mutation removing the freeze conjunct from `detect` must fail a test.
2. Live: `mise run llvm-detect -- --json` → rc 4, frozen {23: false}, reason contains `held: IWYU, freeze`. Print it.
   Control: a direct live `freeze_state(22, …)` call → frozen True (it can say yes).
3. `mise run llvm-parity` rc 0. ruff, ruff format and ty rc 0.

## 6. Commit

`lane`: ONE commit, `feat(llvm): …`, with the dispatch's attribution lines. Never push.

## 7. PREMISES (live probe 2026-10-04 by the architect; script `/Users/rmanaloto/.claude/jobs/6fae0fec/tmp/freeze.sh`)

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | E | release/22.x head `ca7933e47d3a` (2026-06-15) == `llvmorg-22.1.8` commit; compare ahead 0 / behind 0; apt -22 build `ca7933e47d3a`; Release Date 2026-07-14 | probe |
| 2 | E | release/23.x head `21ef2ddb8060` (2026-09-30); newest GA `llvmorg-23.1.2` → commit `85ac56026243`; ahead 27 / behind 0; apt -23 build `67f4a076a097` = neither; Release Date 2026-09-22 | probe |
| 3 | E | `gh api …/branches/release/99.x` → 404 "Branch not found" (control) | probe |
| 4 | L | the apt version embeds the source commit as `+<sha12>-1~exp1~` | `.devcontainer/mise-system.toml` pins; probe rows 1-2 |
| 5 | I | the existing detector: `detect`, `Detection`, `iwyu_ready`, `default_fetcher`, the releases helper, held_on/reason, rc 0/3/4/1 | `python/src/dotfiles_setup/llvm_major.py` at 09e968a4 |
| 6 | A | a post-tag version-bump commit is the common "tag+1" shape; the ruling allows exactly one | ruling text |
