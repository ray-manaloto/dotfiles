# premise-verifier report — rev 3 delta of docs/specs/llvm-major-detect-bump.md (2026-10-02, verbatim)

PREMISE REPORT: rev 3 delta of `docs/specs/llvm-major-detect-bump.md`

I am read-only, nothing is persisted, and the coordinator needs to save this report. I had no Bash tool, so I could not run `git diff HEAD`. Instead I read the full rev 3 spec and compared it with the rev 2 premise report (`docs/research/kb/reports/agents/premise-verifier-llvm-major-detect-bump-2026-10-02.md`). That means "changed lines" here comes from my reading of the IWYU-related text, not from a byte diff.

**ROWS:** 2 checked. 0 CONFIRMED / 0 REFUTED / 1 UNVERIFIABLE / 1 ASSUMED (0 checkable).

| Row | Verdict | Evidence |
|---|---|---|
| 24 (E) | UNVERIFIABLE (live probe, no file) | The local half is corroborated by `.devcontainer/mise-system.lock`. Its `conda:include-what-you-use` entry has `version = "0.26"` (:3502). linux-arm64 is `include-what-you-use-0.26-hfae3067_1.conda`, with conda_deps `libclang-cpp22.1-22.1.8…` and `libllvm22-22.1.8…` (:3510-3515). linux-x64 is `…-0.26-hecca717_1.conda`, with the same two (:3548-3553). So iwyu_ready(22)=True agrees with what is locked. Not backed by any file: the 45-file count, the osx libllvm21 builds, win-64 having no LLVM deps, the "main" label, the 404 control, and iwyu_ready(23)=False. |
| 23 (A) | ASSUMED (a resolved ruling, not a fact) | The cited lines hold: `mise-system.toml:74` `"conda:include-what-you-use" = "latest"`, and :58-60 "conda keeps it on the matching clang-22". The code does not contradict the ruling. The row's remaining "Spec is NOT dispatched until this is ruled" text is stale now that it says RESOLVED. |

**Q3: does mise's conda `"latest"` resolve newest by (version, build_number)? UNVERIFIABLE.** The repo has no mise conda-backend code. The lock is the only evidence, and it is one data point: 0.26 build `_1` on both linux subdirs. That fits "newest version, then highest build_number", but it cannot tell that rule apart from any other tie-break, and I cannot see whether a `_0` build exists. One more point: the image installs with `--locked`, so what actually ships is the lock's choice, not conda-forge's newest. `iwyu_ready` is a proxy for what a future `mise run lock-image` would pick.

**Q4: does rc 4 collide with an existing convention? No.**
- `gate_result.py:72-78` `STATUS_EXIT_CODES` is {0 pass, 1 fail, 127 tool missing, 124 timeout, 2 not a gate}. That map applies only to `GATE_COMMANDS` (:58-64), and llvm-* is not in it.
- 124 is also the timeout rc in `lint.py:61`, `bounded_wait.py:22`, `fnhook_gates.py:203` and `dag_project.py:570`.
- Precedent for an informational non-zero rc: `graphify.py:750-756` uses rc 3 for "graph unavailable". That is a different CLI with no shared registry, so llvm-detect's rc 3 = "bump due" does not conflict.
- rc 4 shows up only in a `plugin_health.py:213` comment, where it is pytest's usage rc (external).
- The hk step wraps only `llvm-parity` (rc 0/1), so rc 3 and rc 4 never reach lint.

**Internal consistency after the delta.** Pins stay at 22 consistently across the Objective (:13-17), Files (:53-55), Constraints (:196-197), Verification step 3/3b/4 and Commit (:245-246). The parity checks match `ARG LLVM_MAJOR=22`. The exceptions:

- **C1, Files :56.** `renovate.json` is still listed under "Modify" with no action, but :196 says Renovate stays at 22. This looks left over from rev 2. If a lane "modifies" it to 23, parity would catch it (suite must equal P), but the Files entry should say "unchanged; parity-checked" or be removed.
- **C2, step 6 :234-235 claims hits that the pattern cannot produce.** `ARG LLVM_MAJOR=22` does not match: `R=22` has no lowercase letter or `-` right before `22`. The four major-less pins (`libc++1`, `libc++abi1`, `libomp5`, `llvm-libunwind1`) also don't match, because their values are `1:22.1.8…`, where `:22.` is excluded. So "the 58 pins" really means 54 hit lines. This is harmless, since the list is an allow-list, but the text should be corrected.
- **C3, step 1 :214 versus the interface :129.** The test "only one subdir → False" conflicts with the interface rule that "a subdir with no files" RAISES. If the test means "only one subdir's newest build depends on libllvm{M}", it should say so. Otherwise the lane has to choose between the two.
- **C4, row 23** still carries its pre-ruling dispatch-block sentence (see the table).

MISSING (unstated premises):
- **Version ordering in `iwyu_ready` (load-bearing).** "Newest by (version, build_number)" (:127) doesn't say how versions compare. A string sort ranks `0.9` above `0.26`, and conda-forge iwyu has historically published `0.x` versions with one- and two-digit minors. Row 24 says 45 files exist, so an older single-digit minor is plausible. The spec should require a conda/PEP 440-style numeric comparison and add a test (`0.9` vs `0.26`). The build_number test alone won't catch this.
- **Empty IWYU-filtered set (load-bearing for detect's correctness).** `TARGET = max N in SERVED with N == P or iwyu_ready(N)` (:138) is undefined when P is not served and no served N > P is IWYU-ready. The SERVED-empty raise at :136 doesn't cover this case. Specify RAISE and add a test arm.
- **Step 3 safety if the gate opens before the lane runs.** Running `llvm-bump` without `--dry-run` writes 23 if conda-forge publishes an iwyu built against clang 23 in the meantime. That would violate :196-197 and the one-commit/no-bump Commit section. Add "if `llvm-detect` rc ≠ 4, STOP and report; do not run `llvm-bump`."
- **Redirect behaviour of api.anaconda.org.** `iwyu_ready` uses the no-redirect Fetcher (:79-80). If the `/files` endpoint answers with a 3xx, the gate raises every time. Row 24 doesn't say whether its probe followed redirects. The lane must confirm a direct 200.
- **The `labels` and `attrs.depends` JSON shape** (:125-128) rests only on row 24's unfiled probe. The lane should save one raw response as a fixture or evidence.
- **The lock refresh after the gate opens.** `plan_bump` (:169-170) rewrites no lockfile, but iwyu is installed with `--locked` (lock :3501-3602 is pinned at 0.26). The future 23 bump also needs `mise run lock-image`, or the image keeps iwyu 0.26/clang 22 even though the gate is open. This doesn't affect this PR, but the "23 swap is a later `mise run llvm-bump`" text (:17) should name it.
- **`mise run` exit-code passthrough.** Step 3 expects `mise run llvm-detect` to return rc 4. That relies on mise passing the task's exact rc through, which I could not check here. Low risk, but read the rc from the file as usual.
- **No offline test for the rc mapping.** Nothing offline covers llvm-detect's 0/3/4/1 or `llvm-bump`'s held-path "writes nothing, rc 0". Only live step 3 covers them, so add CLI-level unit arms with injected fetchers.
- **Stale prose for the lane to neutralise.** `mise-system.toml:191` "`llvm-toolchain-resolute-23` is a 404" is false now. It is already inside the :173-217 range named in Files, so it is covered.

**VERDICT:** correct the spec first. Two gaps block. The version-ordering rule for `iwyu_ready` is unstated, and a string compare would silently pick the wrong "newest" build. TARGET is undefined when P is unserved and IWYU blocks everything above it. Add the step-3 "stop unless rc 4" guard at the same time, since without it the lane can commit the very bump this PR holds.

Non-blocking residuals:
- **Row 24 (UNVERIFIABLE):** a live fact that verification step 3's control arms (iwyu_ready(22)=True, (23)=False) re-measure, and the lock corroborates the 22 half.
- **Row 23 (ASSUMED):** a ratified ruling; the cited lines hold.
- **Q3 mise resolution (UNVERIFIABLE):** the lock fits it; the actual install path is `--locked` anyway.
- **C1/C2/C3/C4:** text corrections. Parity catches C1, and C2 is an allow-list over-statement. Fix C3 before dispatch so the lane doesn't have to pick a behaviour.
- **Redirect, JSON-shape and `mise run` rc premises:** a wrong guess fails loudly (raise or rc mismatch), never silently.

Files read: the spec, the rev 2 premise report, `.devcontainer/mise-system.toml:48-77,186-191`, `.devcontainer/mise-system.lock:3498-3563`, `python/src/dotfiles_setup/gate_result.py:55-93`, and grep hits in `lint.py`, `bounded_wait.py`, `graphify.py`, `plugin_health.py` and `fnhook_gates.py`. All are under `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002`.
