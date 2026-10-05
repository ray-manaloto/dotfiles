# premise-verifier report — docs/specs/llvm-major-detect-bump-fix2.md (2026-10-02, verbatim)

PREMISE REPORT — docs/specs/llvm-major-detect-bump-fix2.md (worktree llvm23-20261002, HEAD includes 4b56cf59)
This lane is read-only and wrote nothing. The coordinator should persist this report.

ROWS: 7 checked — 4 CONFIRMED (0 provenance corrected) / 0 REFUTED / 0 UNVERIFIABLE / 2 ASSUMED (1 checkable) / 1 CONFIRMED with a citation-context correction (row 3)

| # | Verdict | Evidence |
|---|---|---|
| 1 L | CONFIRMED | `.devcontainer/mise-system.toml:69` is exactly `"conda:include-what-you-use" = "latest"`. The IWYU comment is at :52-56. The conda no-tracking note is at :41-47. |
| 2 L | CONFIRMED | `mise-system.lock:3501-3502`: `[[tools."conda:include-what-you-use"]]` / `version = "0.26"`. arm64 URL `…linux-aarch64/include-what-you-use-0.26-hfae3067_1.conda` (:3510), dep `"libllvm22-22.1.8-h680871c_3",` (:3515). x64 URL `…linux-64/include-what-you-use-0.26-hecca717_1.conda` (:3548), dep `"libllvm22-22.1.8-h474f4eb_3",` (:3553). The block really runs to :3616 and has six platforms (adds -musl, -baseline, -musl-baseline). |
| 3 L | CONFIRMED (the citation context is wrong) | The string at `refresh.yml:367` exists, but it belongs to the **image-lock-pr** job, which runs only on Renovate PRs (:273-277). The DAILY regeneration is `lock-refresh` → `$/.github/actions/lock-refresh` (:108) → `action.yml:57` `run: mise run lock-image -- --no-container`, with no `--skip-tools`. The objective's "daily lock-image refresh (refresh.yml ~:367)" cites the wrong job. The conclusion still holds: both paths call the same producer, `image_lock.py:289` `mise lock --bump`. |
| 4 P | CONFIRMED | `refresh.yml:161-230`: `if: github.event_name != 'pull_request'` (:167), `timeout-minutes: 30` (:169), `permissions: contents: read / issues: write` (:170-172), and checkout `@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` with `persist-credentials: false` (:175-177). The search-then-filter is `--search "in:title \"$title\""` plus jq `select(.title == \"$title\")` and `head -1` (:196-199, :210-213). Close-with-comment is at :201-202. Create with `--label dependencies,needs-triage` is at :221-222. The artifact upload uses `if: always()`, `upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1`, `if-no-files-found: ignore` (:224-230). |
| 5 E | CONFIRMED | Saved JSON: main-label versions run 0.17 to 0.26. Each version's linux builds carry a single `libllvm13`…`libllvm22` dep. 0.26 has `_0` and `_1` on linux-64 and linux-aarch64, all `libllvm22 >=22.1.0,<22.2.0a0`. No libllvm23 appears anywhere. |
| 6 A | ASSUMED | Not contradicted. The data fits one version per clang major: 0.17→13 … 0.26→22, and 0.21 `_0`/`_1` are both on 17. Not settleable from the repo: how mise resolves the partial pin "0.26" under `--bump` (prefix match, newest build). The new lock parity check is the only guard, because `tests/test_lock_coverage.py:34-38` only checks X.Y.Z pins, so "0.26" is never compared to the lock. |
| 7 A | ASSUMED (checkable) | `renovate.json:243-252` enabledManagers include `mise` but no conda manager. `mise-system.toml:41-47` records that Renovate's mise manager does not implement the `conda` backend. Not read: the `github>jdx/renovate-config` preset. Cheap settle: `mise run renovate-dryrun`. |

MISSING:
- **Adding the job breaks the exact-set test.** `tests/test_workflow_hooks.py:85-112` pins `EXPECTED_JOBS` as an exact set, and the comment says "Adding or losing a job is a deliberate, reviewable diff". `llvm-currency` must be added there, and optionally to `REAL_CASES` (:70-76) as a non-git-writer. The spec does not list this file, and its gate runs only two test files. contract-preflight's full pytest would fail. **Blocking.**
- **The `--major` dry-run control no longer skips the IWYU gate.** `plan_bump` gets the new IWYU rewrite via `iwyu_pin_for(T)`. The explicit control is labelled "explicit dry-run control; detection and gates skipped" (`llvm_major.py:705`), and its tests assert it never fetches anaconda: `tests/test_llvm_major.py:451-453` raises `"explicit dry-run must skip both gates"`. Every plan test then fails. Also, `iwyu_pin_for(23)` raises today because no libllvm23 build exists, so `llvm-bump --dry-run --major 23` returns rc 1. The spec must decide whether the control fetches IWYU, skips the IWYU rewrite, or takes an injected pin. **Blocking.**
- **Every successful bump now fails its own parity check.** `_bump` returns `parity_main(root)` right after writing (`llvm_major.py:714-716`). The new lock check sees libllvm{P} against anchor T, so every successful write returns rc 1. The hk step `llvm_major_parity` (`hk.pkl:285-287`, no glob) also fails lint on the bump branch until `lock-image` runs, which is CI/amd64-only. The spec needs to state the intended post-write rc and the bump-PR flow. **Blocking.**
- **Older versions lack an arm64 build.** Versions 0.17-0.20 have no linux-aarch64 main build in the saved JSON. `iwyu_versions_for` must skip a version missing a subdir rather than raise. Today `iwyu_ready` raises only when a subdir has no builds at all (`llvm_major.py:290-292`). The spec's "Raises on the same shape errors" is ambiguous per version. The shape errors are also per-build: "exactly one libllvm" (:303-308) and "ambiguous newest" (:310-315). Should those apply to old versions too?
- **The spec's `uses:` form would be flagged.** Every in-repo action reference is `uses: $/.github/actions/setup-mise` (`refresh.yml:106,179,329,533`), not `./`. zizmor's `self-repository` audit rewrote them, and `.github/actionlint.yaml:17-34` suppresses actionlint's parse error only for the `$/` form. The spec text says `./.github/actions/setup-mise`; the lane must copy the `$/` form. There is no zizmor config file in the repo. The hk builtins are `actionlint`/`ghalint_workflow`/`ghalint_action`/`zizmor` (`hk.pkl:416-419`). ghalint requires job `timeout-minutes`, job `permissions` and `persist-credentials: false`, all of which the tool-currency shape meets.
- **The house pattern for CI calls is a mise task, not `uv run`.** Refresh jobs call python through mise tasks: `mise run tool-currency > /tmp/tool-currency.md` (:181), `mise run --skip-tools lock-image …` (:367), `mise run --skip-tools schema-vendor-refresh` (:544). `uv run --project python` appears there only for pytest (:343, :376). The spec's "as the other refresh jobs do" is backwards. `llvm-detect` already has a task (`mise.toml:789-791`), so `mise run llvm-detect -- --markdown > /tmp/llvm-currency.md` matches the precedent, and a `standing-issue` task is the consistent choice. Install choices:
  - Full install with no flag, as tool-currency does (:178-181).
  - A subset `install_args: "python uv"` plus `mise run --skip-tools`, as image-lock-pr (:329-331) and schema-refresh (:532-544) do. The #963 rule in `setup-mise/action.yml:17-20` applies here.
- **Template injection: follow the in-file precedent.** Step outputs are used in `if:` (`steps.drift-check.outcome == 'failure'`, :350, :443) and passed to `run:` only through `env:` (:476-479). The rc output should follow that, never `${{ steps.*.outputs.* }}` inside `run:`. Not repo-verified: the GHA default `bash -e` shell would abort step 1 on rc 3/4 unless captured, e.g. `… || rc=$?`.
- **refresh.yml does run on pull_request.** It triggers on `pull_request: branches: [main]` (:46-47), so the new job needs the `!= 'pull_request'` guard. No aggregate or summary job exists in refresh.yml, and nothing uses `needs:` there. `ci-gate` lives in ci.yml and cannot reference this workflow, so no extra wiring is needed.
- **Suites and the token audit.** The suites `ci.image-lock-pr-wired` (`suites.toml:848-867`), `ci.refresh-uses-app-token` (:834-846), `ci.lock-refresh-wired` (:869-881) and `workflow.tool-currency-wiring` (:2249-2295) bind refresh.yml tokens per path. `token-audit` (`hk.pkl:397-399`) fails on new multiplicity. The new job (including its comments) must not repeat these tokens:
  - `tool-currency:\n    # Never on pull_request`
  - `mise run tool-currency >`
  - `Tool currency report (daily)` (allowlisted at `token_audit.py:176-180`)
  - `lock-refresh:`
  - `uses: $/.github/actions/lock-refresh`
  - `run: mise run --skip-tools lock-image -- --no-container`

  No suite lists llvm CLI subcommands. Adding a wiring contract for the new job is optional.
- **The parity scan covers main.py.** `parity_violations` scans `main.py` for LLVM literals (`llvm_major.py:501-504`, regex :43-46), so the new `standing-issue` and `--markdown` code in main.py must not contain strings like `clang-22`.
- **Lock parsing details.** The lock's platform keys are quoted dotted keys, `[tools."conda:include-what-you-use"."platforms.linux-x64"]`. tomllib gives `tools["conda:include-what-you-use"][0]["platforms.linux-x64"]["conda_deps"]`, a list of `name-version-build` strings (`"libllvm22-22.1.8-h474f4eb_3"`). The API's `depends` use the form `"libllvm22 >=22.1.0,<22.2.0a0"`. `iwyu_ready`'s `^libllvm(\d+)\b` matches both. The spec names only the -musl variants as ignored; the -baseline variants (:3564, :3600) also exist and should be named. `lock_integrity.tool_platforms` (`lock_integrity.py:92-98`) only lists platforms; it does not parse deps.
- **Fixture and test fallout in tests/test_llvm_major.py.** The fixture `repo` and `PIN_TEXT` (`tests/test_llvm_major.py:24-56`) have no mise-system.lock and no IWYU line. Every `parity_violations(repo) == []` assertion (e.g. :576, :588) breaks until the fixture is extended. `test_cli_detect` monkeypatches `detect_main` with `lambda root, *, json_output:` (:631), which breaks if dispatch passes a new `markdown` kwarg.
- **The hold reason text is stale.** It reads "newest linux builds do not both target" (`llvm_major.py:354-357`), which no longer describes the redefined `iwyu_ready`. Tests assert the prefix `"23 GA+served, held: IWYU"` (:671), so keep that prefix.
- **Helpers to reuse (item 8).**
  - Fetch and parse: `_body` (:204), `_IWYU_URL` (:35), `_iwyu_build_key` (:267, numeric version plus build number).
  - Rewrite and paths: `_rewrite_once` (:547, the fix1 F4 single-occurrence assertion for the IWYU pin rewrite), `_SYSTEM` (:33).
  - Parity: the `parity_violations` exception envelope (:497-507).
  - Detection output: `Detection` plus `asdict` (:49, :668) for `--markdown`.
  - Not yet a helper: the libllvm dep regex inside `iwyu_ready` (:298-302). Factor it out to share with `iwyu_lock_majors`.
- **A precedent for an exact conda pin.** `"conda:gxx" = { version = "16.2.0", os = ["linux/arm64"] }` (`mise-system.toml:63`). The "digits and dots" parity check should state whether table-form values are allowed.
- **Cosmetic:** the raw file is named …2026-10-03.json while today is 2026-10-02 (probably a UTC timestamp). Non-blocking.

VERDICT: **Correct the spec first.** Three blockers:
1. The full test suite will fail on `EXPECTED_JOBS` (`test_workflow_hooks.py:85-112`).
2. The `plan_bump` IWYU rewrite breaks the `--major` dry-run control contract and its tests, and raises for 23 today.
3. The post-write `parity_main` and the hk `llvm_major_parity` step will fail after every bump until lock-image runs.

Also fix two literal instructions in the spec text: use `$/` not `./`, and use the mise-task precedent, not `uv run`.

Non-blocking residuals for the architect to accept:
- Row 6: mise partial-pin `--bump` semantics are unverified in the repo; the lock parity is the backstop.
- Row 7: the jdx preset is unread; `renovate-dryrun` settles it.
- Row 3: the context correction only; the conclusion is unchanged.
- The -baseline naming.
- The fixture date.

## GitHub repos touched

_None._ (Local worktree files only.)
