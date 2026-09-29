# Spec S28b-1: clang-p2996 has ONE pinned literal, its own Renovate PR, and a gate

**Status: RATIFIED 2026-09-29 (drafted by spec-scribe; rulings at the end). Implemented in PR #1441, squash-merged as `efc04995` (branch commit `a8e8e8d9`).** Branch
`fix/s28b-1-p2996-single-literal` off main `8454778c`. Issues #1434, #1435. Research:
`docs/research/kb/reports/agents/research-p2996-ref-tracking-2026-09-29.md` (**R** below) and
`docs/research/kb/reports/agents/sdlc-team-p2996-ref-currency-2026-09-28.md` (**S**).

Drafting lane notes: this lane has Read/Grep/Glob/Write/Edit and **no Bash**, so it ran no `git`, `gh`, `mise`, `docker`
or `renovate` command. Every command result below comes from the cited research, not from this lane. Those results are
marked `A` in PREMISES and listed under "Coordinator actions". I read agent memory
(`.claude/agent-memory-local/spec-scribe/`) and applied it. Its consumer-grep rule found the substring binding at
`tests/test_image_smoke_exec.py:237` (see §3.6).

## 1. Objective

Make `docker-bake.hcl`'s `variable "CLANG_P2996_REF"` default the **only** place the clang-p2996 commit SHA is written in
the repo. Specifically:

- Give that literal a Renovate extractor that actually matches it.
- Give it its own daily auto-merging PR, outside the `image-build inputs` group.
- Add a machine gate, with both arms, that fails if a second literal reappears or if the extractor stops matching.
- Bump the pin to the current upstream `p2996` head.
- Correct every piece of prose that claims a scheduled refresh or two-file lockstep.

Keep `mise run p2996-refresh` as a **manual, on-demand** bump (Ray 2026-09-29).

Out of scope: closing or repairing #1063, and `gitIgnoredAuthors`. These are coordinator follow-ups (see
"Coordinator actions"). Also out of scope: building a new upstream-lag checker (see §3.7).

## 2. Files

| # | File | Change |
|---|---|---|
| F1 | `.devcontainer/Dockerfile` | `:426` `ARG CLANG_P2996_REF=f349a2d8…` becomes `ARG CLANG_P2996_REF` (no default). Rewrite the `:421-425` comment (§3.1). Optional `test -n` guard: architect question Q1. |
| F2 | `docker-bake.hcl` | `:101` default: replace it with the upstream `p2996` head resolved at implementation time (§4 I6). Extend the `:98-99` comment to say this is the single literal. |
| F3 | `renovate.json` | customManager `:124-138`: new matchString, `managerFilePatterns` narrowed to bake, and a new description. Append one packageRule after the `image-build inputs` rule (`:18-32`). Exact JSON is in §3.2 and §3.3. |
| F4 | `python/verification/suites.toml` | `:429` token `"ARG CLANG_P2996_REF="` becomes `"\nARG CLANG_P2996_REF\n"` (§3.4). Leave `:433-443` (the bake suite) unchanged. |
| F5 | `tests/test_p2996_single_literal.py` | **New.** The gate (§3.5). |
| F6 | `tests/TEST-INDEX.md` | Add one row for F5. |
| F7 | `python/src/dotfiles_setup/image.py` | `:665` OK line reworded. The required substring is preserved (§3.6). |
| F8 | `python/src/dotfiles_setup/p2996_refresh.py` | Docstring `:1-21`: rewrite so it no longer claims a scheduled job (§3.8). No code change. |
| F9 | `mise.toml` | `:1467` `[tasks.p2996-refresh]` description (§3.8). |
| F10 | `.devcontainer/P2996-CACHE.md` | `:91-99` blockquote, `:111-115` bullet, `:135` and `:140-141` see-also lines (§3.8). |
| F11 | `.github/workflows/refresh.yml` | Comment only, `:21-24`. It says the Renovate regex "matches only the Dockerfile ARG, never bake's HCL default (#1434)". After this PR that is history, not the current state. Reword it to past tense and say the manager was fixed in this change. **Scope addition. It was not in the architect notes. Ratify: Q4.** |
| F12 | `.github/workflows/AGENTS.md` | `:18` "`CLANG_P2996_REF`: bake's default NOT auto-bumped (#1434)" becomes "`CLANG_P2996_REF`: Renovate git-refs bumps bake's default in its own daily PR (#1434)". **Scope addition. Ratify: Q4.** |

**Deliberately NOT changed:**

- `python/pyproject.toml:36-39` says "Renovate's git-refs datasource bumps this the same way it bumps CLANG_P2996_REF".
  Once F3 lands, that sentence is **true** for the first time, so no edit is needed. Flagged as Q5.
- `python/src/dotfiles_setup/token_audit.py`. Its only clang-p2996 binding (`:188-192`) is the bake suite's
  `CLANG_P2996_REF = CLANG_P2996_REF`, and F4 leaves that token unchanged. A grep for `clang-p2996` in `token_audit.py`
  returns only `:189`, and the same grep finds that known entry, so the probe discriminates.
- `pin-parity.toml` / `hk.pkl:582-592`. The gate choice is explained in §4 I4.
- `python/src/dotfiles_setup/main.py:2155-2159`. The `p2996-refresh` help text makes no schedule claim.

## 3. Interfaces

### 3.1 Dockerfile (F1)

Replace `:421-426` with:

```dockerfile
# NO default, on purpose (S28b-1, #1434): docker-bake.hcl's
# `variable "CLANG_P2996_REF"` is the ONLY literal. Every build of this file
# goes through bake, which passes it as a build arg (dev + p2996-cache targets).
# Renovate's git-refs manager bumps that one literal in its own PR, and p2996_hash.py
# reads it from there. A default here was a second, silently-stale copy
# (#904 bumped only this line). Gated by tests/test_p2996_single_literal.py and
# the build.clang-p2996-reflection suite.
ARG CLANG_P2996_REF
```

Keep the `ARG` line exactly `ARG CLANG_P2996_REF` with nothing after it. The §3.4 token binds `\nARG CLANG_P2996_REF\n`.
No comment line may end in the bare phrase `ARG CLANG_P2996_REF`, because that would give the token a stand-in site.

### 3.2 Renovate customManager (F3; replaces `renovate.json:124-138`)

```json
{
  "customType": "regex",
  "description": "clang-p2996 pinned git SHA (tagless p2996 branch HEAD) — the SINGLE literal, docker-bake.hcl's `variable \"CLANG_P2996_REF\"` default (S28b-1, #1434). The .devcontainer/Dockerfile ARG deliberately has NO default. The previous matchString `CLANG_P2996_REF[\"= ]+…` could not cross the HCL block's brace/newline/`default =`, so it extracted 0 deps from bake and bumped only the Dockerfile copy (#904). `\\s` crosses newlines under RE2 with the regex manager's `g`-only flags. git-refs emits no releaseTimestamp, so minimumReleaseAge is inert for this dep (timestamp-optional proceeds immediately); its cadence comes from the packageRule's `schedule`. Gated by tests/test_p2996_single_literal.py.",
  "managerFilePatterns": [
    "/(^|/)docker-bake\\.hcl$/"
  ],
  "matchStrings": [
    "variable \"CLANG_P2996_REF\"\\s*\\{\\s*default\\s*=\\s*\"(?<currentDigest>[a-f0-9]{40})\""
  ],
  "depNameTemplate": "bloomberg/clang-p2996",
  "packageNameTemplate": "https://github.com/bloomberg/clang-p2996",
  "currentValueTemplate": "p2996",
  "datasourceTemplate": "git-refs"
}
```

The last four template fields are byte-identical to `renovate.json:134-137` today. Keep the ASCII `...` or the Unicode `…`
in the description to match the file's existing style. The implementer may use `\u2026` like the neighbouring
descriptions.

### 3.3 packageRule (F3; insert AFTER `renovate.json:18-32`, and after `:46-55` so it also wins over the generic digest rule)

Later packageRules override earlier ones. The safe place is **the end of `packageRules`**, after `:84-92`:

```json
{
  "description": "clang-p2996 (#1434/#1435, S28b-1): its OWN daily PR, pulled OUT of `image-build inputs` (packageRules[0] matches docker-bake.hcl by file name, which is what put the compiler into #1063). Each bump is a cold p2996 compile, so a once-a-day window bounds cost. minimumReleaseAge is INERT here: the git-refs datasource emits no releaseTimestamp, and this repo's timestamp-optional behaviour then proceeds immediately, so `schedule` is the only soak lever. Auto-merge is GitHub-native and waits on the required `ci-gate`, which needs build-publish; docker-bake.hcl is in ci.yml's build path filter, so build-publish cannot skip for this PR.",
  "matchDepNames": [
    "bloomberg/clang-p2996"
  ],
  "groupName": null,
  "schedule": [
    "before 6am"
  ],
  "automerge": true,
  "automergeType": "pr",
  "platformAutomerge": true
}
```

Field names are confirmed against the file as it is now. `groupName: null` has precedent at `:62`. `automerge` /
`automergeType: "pr"` / `platformAutomerge` appear at `:52-54`. The dep name `bloomberg/clang-p2996` is the
`depNameTemplate` at `:134`. The schedule timezone comes from the extended preset (America/Chicago per R:19-21; `A`).

### 3.4 suites.toml (F4)

```toml
per_path_tokens = { ".devcontainer/Dockerfile" = [
    "-DCMAKE_INSTALL_PREFIX=/opt/clang-p2996",
    "\nARG CLANG_P2996_REF\n",
    "COPY --from=clang-builder",
] }
```

Both arms come from the token itself:

- Re-adding `=<sha>` removes the `\n` right after `REF`, so the suite fails.
- `ARG CLANG_P2996_REPO=` (`Dockerfile:420`) does not contain the token.

Prove the token binds exactly one site with `mise run token-check -- .devcontainer/Dockerfile "<token>"`. How that task
takes an embedded newline is **unverified** (C-list).

### 3.5 The gate: `tests/test_p2996_single_literal.py` (F5)

Follow the conventions in `tests/AGENTS.md`: add `python/src` to `sys.path`, use `REPO_ROOT = Path(__file__).parent.parent`,
and make no inline suppressions. Imports: `json`, `re`, `subprocess`, `sys`, `pathlib.Path`, and
`from dotfiles_setup.p2996_hash import _extract_bake_variable`. That helper is already imported by `image.py:28`,
`p2996_refresh.py:32` and `tests/test_p2996_hash.py:26`.

Helpers:

- `_bake_ref() -> str`. Returns `_extract_bake_variable((REPO_ROOT / "docker-bake.hcl").read_text(), "CLANG_P2996_REF")`
  and asserts it `re.fullmatch(r"[0-9a-f]{40}", …)`.
- `_clang_manager() -> dict`. Loads `renovate.json` and returns the **single** `customManagers` entry whose
  `depNameTemplate == "bloomberg/clang-p2996"`. It asserts exactly one such entry exists.
- `_py_pattern(match_string: str) -> re.Pattern`. Translates RE2/JS named groups `(?<name>` to Python's `(?P<name>`
  with `re.sub(r"\(\?<([A-Za-z_]\w*)>", r"(?P<\1>", s)`, then compiles with **no flags**. This mirrors the regex
  manager's `g`-only flags (R:75-76; `A`). The docstring must say that Python `re` is a **proxy** for RE2. RE2
  *validity* is gated separately by the `renovate_config_validate` hk step's lookahead canary (`hk.pkl:533-546`). A
  pytest cannot drive Renovate's own extractor, because `npm:renovate` is host-only (`.config/mise/conf.d/shared.toml:18`),
  and a test may shell out only to shared-fragment tools.
- `_tracked_nondoc_files() -> list[str]`. Runs `git ls-files -z` with `cwd=REPO_ROOT` and `check=True`. It drops paths
  under `docs/` or `graphify-out/` and any path ending in `.md`, because historical records legitimately name old and
  current SHAs. `graphify-out/` is gitignored except `wiki/` (`.gitignore:104-105`). It reads each file with
  `errors="ignore"` and skips unreadable ones.

Tests. Every expected value comes from the real artifact, never from recomputing the code's logic:

1. `test_bake_default_is_the_only_tracked_copy_of_the_sha`: the list of files containing `_bake_ref()` equals
   `["docker-bake.hcl"]`.
2. `test_no_file_assigns_a_sha_literal_to_clang_p2996_ref`: no file from `_tracked_nondoc_files()` matches
   `r"CLANG_P2996_REF\s*[=:]\s*\"?[0-9a-f]{40}"`. Bake's form is `default = "…"`, so bake never matches. This catches
   the #904 shape with a **different** SHA, which test 1 cannot see. **Build any fixture that exercises this pattern by
   string concatenation**, or the test file itself becomes a hit.
3. `test_dockerfile_arg_has_no_default`: the Dockerfile's lines matching `^ARG CLANG_P2996_REF\b` (MULTILINE) equal
   exactly `["ARG CLANG_P2996_REF"]`.
4. `test_renovate_extracts_exactly_the_bake_pin`: `_py_pattern` of the manager's single matchString, run with
   `finditer` over `docker-bake.hcl`, yields exactly one match, and `group("currentDigest") == _bake_ref()`.
5. `test_renovate_matchstring_rejects_arg_forwarding_and_dockerfile`: 0 matches on `"CLANG_P2996_REF = CLANG_P2996_REF"`
   (the literal forwarding line at `docker-bake.hcl:139,239`) and 0 on the real `.devcontainer/Dockerfile` text.
6. `test_renovate_matchstring_tolerates_one_line_and_reflowed_blocks`: exactly one match on the one-line fixture form
   `variable "CLANG_P2996_REF" { default = "<40a>" }` (the shape `tests/test_p2996_hash.py` uses) and on a tab/blank-line
   reflow. Build `<40a>` as `"a" * 40`.
7. `test_renovate_manager_scoped_to_bake_only`: `managerFilePatterns == ["/(^|/)docker-bake\\.hcl$/"]` (the Python
   literal of the JSON value), `datasourceTemplate == "git-refs"`, and `currentValueTemplate == "p2996"`.
8. `test_clang_package_rule_leaves_the_image_group_after_it`: find the index of the rule with
   `groupName == "image-build inputs"` and the index of the rule whose `matchDepNames == ["bloomberg/clang-p2996"]`.
   Assert the second index is greater than the first, and greater than the index of the `matchUpdateTypes` digest
   automerge rule. Assert that rule has `"groupName" in rule and rule["groupName"] is None`, `schedule == ["before 6am"]`,
   `automerge is True`, `automergeType == "pr"`, and `platformAutomerge is True`.

The fail arms that the implementer must run are in §5.

### 3.6 image.py OK line (F7)

`python/src/dotfiles_setup/image.py:665` becomes:

```sh
  echo "OK: clang-p2996 ref $ACTUAL_P2996_REF matches pinned CLANG_P2996_REF (build==pin only; upstream freshness is tracked by Renovate, not checked here)"
```

**Consumer constraint:** `tests/test_image_smoke_exec.py:237` asserts the substring `"matches pinned CLANG_P2996_REF"`,
so keep that substring intact. The suffix avoids apostrophes because the line is shell inside a Python string. The
`:662` FAIL line and the `:646` header (bound by `tests/test_image_arch.py:452`) stay unchanged.

### 3.7 Upstream-lag reporting: proposal only, build nothing

The cheapest native signal already exists:

- **An open Renovate PR for `bloomberg/clang-p2996` is the lag report.** It exists exactly when the pin is behind the
  `p2996` head.
- `mise run renovate-status` (`mise.toml:971-972`, "Report Mend-hosted Renovate install + privileges + open update PRs")
  already lists open update PRs.
- ~~The Dependency Dashboard~~ — the extended preset sets `dependencyDashboard: false` (cold-review F10), so there is no dashboard signal.

So the recommended lag check is: after a day, `renovate-status` shows no clang PR, or shows one that is green or merging.
A clang PR open for more than about 2 days is the alarm. No new checker is built. If Ray later wants this in the
SessionStart doctor, it would be a `doctor.toml` row over `renovate-status`. That is a separate ruling.

### 3.8 Prose (F8–F10)

- `p2996_refresh.py:2`: "Auto-bump" becomes "Manually bump `CLANG_P2996_REF` to the latest `bloomberg/clang-p2996` HEAD
  (on demand)."
- `p2996_refresh.py:16-18`: replace with a paragraph saying:
  - Renovate's git-refs customManager is the automatic path. It opens its own daily PR (S28b-1, #1434).
  - This module is a manual/emergency bump run via `mise run p2996-refresh`.
  - The scheduled `refresh.yml` `p2996-refresh` job was retired in #169, and must not be re-wired to a schedule
    alongside Renovate, because that would put two writers on one pin.
- `mise.toml:1467`: "Bump CLANG_P2996_REF in docker-bake.hcl to the latest bloomberg/clang-p2996 p2996-branch HEAD, ON
  DEMAND (writes only on change). Renovate's git-refs manager is the automatic path (own daily PR); there is no
  scheduled job."
- `P2996-CACHE.md:91-99`: retitle the blockquote to **"Pin currency (#100, #1434)"** and say:
  - Renovate's git-refs manager tracks the `p2996` HEAD and opens its own daily auto-merging PR that rewrites the single
    `docker-bake.hcl` literal.
  - `mise run p2996-refresh` is the manual bump.
  - Drop `gh workflow run refresh.yml`, which no longer bumps anything.
- `P2996-CACHE.md:114-115`: replace "The scheduled `refresh.yml` … opens a PR on change." with "Renovate does this
  automatically in its own daily PR; use this task only for an out-of-band bump."
- `P2996-CACHE.md:135`: "auto-bump source" becomes "manual bump source (Renovate is the automatic path)".
- `P2996-CACHE.md:140-141`: drop "scheduled CLANG_P2996_REF bump (`p2996-refresh` job) +" and keep the `lock-refresh`
  clause.

## 4. Constraints and invariants

- **I1 One literal.** After this change, the 40-hex clang-p2996 SHA appears in exactly one tracked non-doc file,
  `docker-bake.hcl`. Tests 1 and 2 enforce this.
- **I2 Every build goes through bake.** Research R Q4 (`A`, R:171-188) lists every build entry point, and all of them
  are bake. Bake passes the arg in `dev` (`docker-bake.hcl:136-140`) and `p2996-cache` (`:237-240`). The `base` target
  (`:204-206`) never enters `clang-builder-cold`. Without bake, `git fetch --depth 1 origin "${CLANG_P2996_REF}"`
  (`Dockerfile:465`) receives an empty ref. R:196 said this fails loudly — REFUTED by the cold review (`cold-review-a8e8e8d9-2026-09-29.md` F1): `git fetch origin ""` succeeds and fetches the default branch, so the Q1 guard is load-bearing and is now bound by the `build.clang-p2996-reflection` suite. Q1 asks about an explicit
  guard.
- **I3 Cost is accepted.** `p2996_section_digest` (`p2996_hash.py:432-443`) hashes the Dockerfile's p2996 section, so
  editing F1 busts `:p2996-<hash>` by itself. The pin bump would bust it anyway. Expect **one** cold p2996 compile in
  this PR's CI (S:143 says 80–120 min cold; that is `A`, and no duration was measured).
- **I4 Gate choice: a new pytest, not `pin-parity`.** `pin_parity` compares **N ≥ 1 present** sites and treats a
  zero-match site as a failure (`pin_parity.py:72-75`, `:82-88`). It cannot express *absence*. Registering the
  Dockerfile would **require** the default Ray's ruling deletes. Registering bake alone degenerates to "the pattern
  matches", which says nothing about a second copy. A pytest runs in pre-push and in CI `contract-preflight` on **every**
  change, so the `hk.pkl:583-591` glob omission (no `docker-bake.hcl`, no `renovate.json`) cannot hide it. The S
  report's pin-parity recommendation (S:46-50, :148) assumed two surviving sites. Ray's single-literal ruling removes
  that premise, so there is no dissent to carry.
- **I5 minimumReleaseAge is inert for git-refs** (R:103-113, `A`). State this in both the customManager and the
  packageRule descriptions. Do not add a per-rule `minimumReleaseAge`.
- **I6 No hardcoded SHA in the spec.** The implementer resolves the head **at implementation time** with
  `gh api repos/bloomberg/clang-p2996/commits/p2996 --jq .sha` and records the command, its rc and its output in the PR
  body. Control arm: `gh api repos/bloomberg/clang-p2996/commits/nonexistent-branch-zz` must return non-zero, and the
  result must be 40 lowercase hex. Write only `docker-bake.hcl:101`. Preferably use `mise run p2996-refresh`, which
  writes exactly that site and raises unless exactly one default matches (`p2996_refresh.py:131-145`). That exercises
  the kept manual path for real. Then cross-check its SHA against the `gh api` output (two routes, one fact).
- **I7 No local base build** (do-not #2). No `mise run build` and no `docker buildx bake dev-load`. The only local
  container-tier probe is `--print` (§5 V7).
- **I8 Zero-skip.** No suppressions. No `--no-verify`. The OK-line substring stays, and the test's expected value is
  not edited to pass.
- **I9 Writable set for the lane:** F1–F12 only. No edits to `docs/research/**` records, `task_plan.md`, or `.github/`
  beyond the F11/F12 comment and doc lines. A codex lane is invisible to `hook_guard`, so this list is the whole
  boundary.

## 5. Verification (implementer runs; paste rc + evidence into the PR body)

Run these in order. V2 must run **before** the F2 pin bump.

| # | Check | Pass arm | Fail/control arm |
|---|---|---|---|
| V1 | `uv run --project python pytest tests/test_p2996_single_literal.py -q` | 8 passed | (a) Re-add `=<current bake sha>` to the Dockerfile ARG. Tests 1, 2 and 3 must FAIL. (b) Separately restore the old matchString `CLANG_P2996_REF[\"= ]+(?<currentDigest>[a-f0-9]{40})`. Test 4 must FAIL (0 matches on bake: the #1434 defect). (c) Move the new packageRule above `:18-32`. Test 8 must FAIL. `git add` the implementation first; `git checkout --` restores the **staged** version. Re-run green after each revert. |
| V2 | `mise run renovate-dryrun -- --json` (about 15 min), with F3 applied and the **old** `7220baff…` pin still in bake | One `bloomberg/clang-p2996` digest update, **not** in the `image-build inputs` branch | After F2 (pin at head), re-run and expect **no** clang update. This proves extraction reads the new pin. If the module's `--json` hides branch grouping, read the raw report it passes to Renovate (`renovate_dryrun.py:194`, `run_renovate(report_path)`) and record that. |
| V3 | `mise run lint > $LOG 2>&1; echo "rc=$?" >> $LOG` | rc=0 (includes `renovate_config_validate`: RE2 canary, then `--strict`) | The canary is the validator's built-in control. Research R:157-169 measured the patch at rc=0 and the lookahead canary at rc=1 (`A`). |
| V4 | `uv run --project python pytest tests/ -x -q` | all pass | Also V1. |
| V5 | `mise run verify` | 0 failed | Revert only F4's token while F1 stays applied. `build.clang-p2996-reflection` must FAIL. Then restore it. |
| V6 | `mise run token-check -- .devcontainer/Dockerfile "<F4 token>"` | binds exactly 1 site | Check the same token against the pre-change Dockerfile (`git show 8454778c:.devcontainer/Dockerfile` into scratch) and expect 0. |
| V7 | `mise exec -- docker buildx bake --print dev p2996-cache > $SCRATCH/bake-print.json` | Both targets show `args.CLANG_P2996_REF` equal to the new bake SHA | `CLANG_P2996_REF=<"b"*40> mise exec -- docker buildx bake --print p2996-cache` must show the override. That proves `--print` reflects variable resolution and is not a constant. Cannot show Dockerfile defaults; V1 test 3 and V5 cover those. |
| V8 | `mise run pin-actions` | rc=0 | Applies because of F11/F12 (`.github/**`). `renovate.json` itself is not a `.github` file. |
| V9 | `mise run lint-docs` | rc=0 | Applies because of F12 (`AGENTS.md`). |
| V10 | `mise run pin-parity` | rc=0, unchanged | Regression only: no clang entry was added. |
| V11 | CI on the PR | `ci-gate` success; build-publish blocking leg ran, not skipped, with smoke-test printing the new OK line with the new SHA | `ci.yml:16,297` put `docker-bake.hcl` in the build filter, so a *skipped* build-publish is a defect, not a pass. |

`mise run verify-local` / `verify-container-latest` cannot exhibit this change before merge, because the image comes
from CI. Run them through `mise run land -- <PR#>` after merge. That runs sync and smoke against the new `:dev` and
prints the §3.6 line.

## 6. Commit

**Caller.** The architect commits after verifying the evidence. Suggested subject:
`fix(p2996): one CLANG_P2996_REF literal, own Renovate PR, single-literal gate (#1434, #1435)`.

## Coordinator actions (not implementation)

- **C1 #1063 (issue #1435).** Once this PR merges, the compiler leaves the group. Close #1063 or get it rebased; decide
  who owns the repair and rebase. Do not adopt a blanket `gitIgnoredAuthors`: S:144 dissents, because
  `refresh.yml:409` relies on an unrecognized author.
- **C2 First scheduled Renovate run.** After merge, confirm the first `bloomberg/clang-p2996` PR opens inside the
  `before 6am` window, alone, and auto-merges on green `ci-gate` (§3.7). The steady state is that no PR exists because
  the pin is current.
- **C3** Update #1434 and #1435 with the merged PR and the V2 dryrun evidence.
- **C4** Run the unverified items: V6's newline-token handling, the dashboard setting in §3.7, and
  R's timezone/preset claims.
- **C5** Persist the ratified version of this spec before dispatch (`docs/specs/` is tracked).

## Questions for the architect (stop here for ratification)

- **Q1 Build-time guard.** Should `test -n "${CLANG_P2996_REF}" || { echo "FAIL: CLANG_P2996_REF unset; build via docker bake"; exit 1; }`
  go at the head of the `Dockerfile:463` RUN?
  - **Recommended: yes.** PRO: a clear message instead of an opaque git error, and it follows the repo's build-time
    self-check pattern (`.devcontainer/AGENTS.md` § Build-time self-checks). CON: one more line in a hashed section. That
    costs nothing extra, because I3 already busts the cache.
- **Q2 packageRule `matchDatasources: ["git-refs"]`.** R:127 includes it, but your notes do not.
  - **Recommended: omit.** PRO: keeps your field list exactly. CON: slightly broader matching, which is harmless because
    the dep name is templated and unique.
- **Q3 Exclusion set for test 1/2.** The tests exclude `docs/**`, `graphify-out/**` and `*.md`.
  - **Recommended: keep this set.** PRO: records may cite SHAs. CON: a SHA in tracked markdown prose goes unchecked. That
    prose is not a build input.
- **Q4 Scope additions F11/F12.** These are stale-after-merge comments in `.github/`. Adding them triggers V8/V9.
  - **Recommended: include.** Tool-currency rule 5 says to update describing docs in the same change.
- **Q5 `python/pyproject.toml:36-39`.** Leave it unchanged. Its claim becomes true once F3 lands.

## 7. PREMISES

Kind: **L** = read by this lane this run (file:line). **A** = assumed or inherited: this lane cannot verify it, because
it has no Bash and cannot run the command.

| # | Kind | Claim | Source |
|---|---|---|---|
| P1 | L | Bake pins `CLANG_P2996_REF` default `7220baffd57ea5b0f8cf59bee494dd5b7cc2b748` | `docker-bake.hcl:100-102` |
| P2 | L | Bake forwards the arg in `dev` and `p2996-cache`; `base` does not | `docker-bake.hcl:136-140`, `:237-240`, `:204-206` |
| P3 | L | Dockerfile has `ARG CLANG_P2996_REF=f349a2d8…` under a comment claiming Renovate "rewrites BOTH files in lockstep" | `.devcontainer/Dockerfile:421-426` |
| P4 | L | The Dockerfile consumes the ref only in `git fetch … "${CLANG_P2996_REF}"` | `.devcontainer/Dockerfile:463-466` (Grep of `CLANG_P2996` in that file: 5 hits, all at `:420-465`) |
| P5 | L | The customManager matchString is `CLANG_P2996_REF["= ]+(?<currentDigest>[a-f0-9]{40})` over bake plus Dockerfile; git-refs; depName `bloomberg/clang-p2996` | `renovate.json:124-138` |
| P6 | L | packageRules[0] groups `.devcontainer/Dockerfile` and `docker-bake.hcl` into `image-build inputs` | `renovate.json:18-32` |
| P7 | L | Digest updates automerge with `automergeType: "pr"`, `platformAutomerge: true`; `groupName: null` has precedent | `renovate.json:46-55`, `:56-63` |
| P8 | L | Global `minimumReleaseAge: "1 hour"`, `minimumReleaseAgeBehaviour: "timestamp-optional"`, schedule "at any time" | `renovate.json:6-10` |
| P9 | L | `build.clang-p2996-reflection` requires the token `ARG CLANG_P2996_REF=` in the Dockerfile | `python/verification/suites.toml:420-431` |
| P10 | L | The bake suite's tokens are `variable "CLANG_P2996_REF" {` and `CLANG_P2996_REF = CLANG_P2996_REF`; token_audit's only clang binding is the latter | `suites.toml:433-443`; `token_audit.py:188-192` |
| P11 | L | pin_parity fails a zero-match site and requires every site to agree; the registry has no clang entry | `pin_parity.py:72-75`, `:82-88`; `pin-parity.toml:46-135` (tools: graphify, chezmoi, hk, claude-code, mise) |
| P12 | L | The `pin_parity` hk glob omits `docker-bake.hcl` | `hk.pkl:582-592` |
| P13 | L | `renovate_config_validate` runs a lookahead RE2 canary before `--strict` validation | `hk.pkl:533-546`; `tests/test_renovate_validate.py:8-14` |
| P14 | L | `_extract_bake_variable(bake_text, name)` exists and is already imported by `image.py` and `p2996_refresh.py` | `p2996_hash.py:197-211`; `image.py:28`; `p2996_refresh.py:32` |
| P15 | L | p2996 hash includes the Dockerfile p2996-section digest and the bake ref | `p2996_hash.py:430-443` |
| P16 | L | `p2996_refresh.py` docstring claims a scheduled `refresh.yml` `p2996-refresh` job; `replace_pinned_ref` raises unless exactly one default matches | `p2996_refresh.py:16-18`, `:131-145` |
| P17 | L | `mise.toml` `p2996-refresh` description claims a scheduled job | `mise.toml:1466-1468` |
| P18 | L | P2996-CACHE.md claims auto-bump via `refresh.yml` | `.devcontainer/P2996-CACHE.md:91-99`, `:111-115`, `:135`, `:140-141` |
| P19 | L | pyproject's comment says Renovate git-refs bumps kb-setup "the same way it bumps CLANG_P2996_REF" | `python/pyproject.toml:36-39` |
| P20 | L | Smoke OK line text; the exec test asserts the substring `matches pinned CLANG_P2996_REF` | `image.py:646-668`; `tests/test_image_smoke_exec.py:229-237` |
| P21 | L | `refresh.yml` comment and `workflows/AGENTS.md` describe the regex as bake-blind / bake not auto-bumped | `.github/workflows/refresh.yml:21-24`; `.github/workflows/AGENTS.md:18` |
| P22 | L | The dispatch override exports `CLANG_P2996_REF` env for bake and the hash | `.github/workflows/build-publish.yml:45`, `:325` |
| P23 | L | `docker-bake.hcl` is in ci.yml's path filters | `.github/workflows/ci.yml:16`, `:297` |
| P24 | L | `npm:renovate` is host-only (not in the image/CI shared set) | `.config/mise/conf.d/shared.toml:18` |
| P25 | L | Tasks exist: `renovate-dryrun`, `renovate-status`, `pin-actions`, `pin-parity`, `validate` (bake), `build` (bake dev-load) | `mise.toml:936-969`, `:971-972`, `:1308-1310`, `:1700-1703`, `:1304-1306`, `:1292-1294` |
| P26 | L | `graphify-out/` is ignored except `wiki/` | `.gitignore:104-105` |
| P27 | L | No other tracked non-doc file assigns a 40-hex SHA to `CLANG_P2996_REF` today except the Dockerfile ARG | Grep `CLANG_P2996_REF.{0,30}[0-9a-f]{40}` excluding docs/worktrees/graphify-out: 1 hit, `.devcontainer/Dockerfile:426`. The hit is the control, so the probe discriminates. |
| P28 | A | RE2 `\s` crosses newlines; the regex manager compiles with `g` only; the new matchString extracts exactly 1 dep from bake and 0 from the Dockerfile | R:73-95. Measured by the research lane through Renovate's own extractor; not re-derived here (no Bash) |
| P29 | A | git-refs emits no `releaseTimestamp`, so minimumReleaseAge is inert under timestamp-optional | R:103-113 (Renovate dist source read by the research lane) |
| P30 | A | Nothing builds `.devcontainer/Dockerfile` except through bake | R:171-188. Grep over workflows/mise/python/scripts by the research lane. This lane read `mise.toml:1292-1306` (both bake) but did not re-run the full sweep |
| P31 | A | `renovate-config-validator --strict --no-global` passes the proposed patch (rc=0), and the canary fails (rc=1) | R:157-169 |
| P32 | A | `main` requires only the `ci-gate` status check | R:146-148 (`gh api …/protection`, research lane) |
| P33 | A | Preset timezone America/Chicago | R:19-21 (live preset fetch by the research lane) |
| P34 | A | Cold p2996 compile about 80–120 min | S:143 (repository estimate, unmeasured) |
| P35 | A→REFUTED | Empty `CLANG_P2996_REF` makes `git fetch` fail loudly | REFUTED by cold-review F1 (it fetches the default branch); the guard is load-bearing and token-bound |
| P36 | L | The current upstream head prefix `f17c8d6c7bfe` (per R and S) appears today only in `docs/**` files, so a bump to it cannot make test 1 fail because of an existing tracked non-doc copy | Grep `f17c8d6c7bfe` excluding worktrees/graphify-out: 3 files, all under `docs/`. The head itself must be re-resolved (I6) |


## Architect rulings (2026-09-29) — RATIFIED

Low-risk, reversible defaults, taken as the scribe recommended: **Q1 yes** — add the `test -n "${CLANG_P2996_REF}"` guard
at the start of the clang fetch RUN (probe `docker buildx bake --print` locally; no local base build). **Q2 no** —
no `matchDatasources`. **Q3 keep** the docs/graphify/`*.md` exclusion in the literal gate. **Q4 include** —
`.github/workflows/refresh.yml:21-24` and `.github/workflows/AGENTS.md:18` must describe the NEW state (Renovate bumps
bake's default via the scoped regex manager; one literal); keep `.github/workflows/AGENTS.md` under agnix's 12,000
chars (it is ~11,870 now — size-neutral wording, else report). **Q5 leave** `python/pyproject.toml:36-39` unchanged.
