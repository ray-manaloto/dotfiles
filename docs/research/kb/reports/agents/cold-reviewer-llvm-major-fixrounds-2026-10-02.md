# Cold review — LLVM major fix rounds 1+2 (4b56cf59, 682d626d)

- Reviewer: cold-reviewer (Claude Opus), BOUNDED round, 7 enumerated questions.
- Diff: `git diff 21b0b4ee 682d626d -- . ':!docs'` (9 files, +1112/-89).
- Resolved refs: base `21b0b4ee9a4da07ed0e5d3939bc50fcb1a923627`, fix1 `4b56cf59798ce18bf31ec6b685bde02041f3e643`,
  fix2 `682d626d2d5d79aa5c1641889227d80482d25d05`. HEAD `d77fbafa` differs from 682d626d only by one docs file
  (`git diff --stat 682d626d HEAD`), so working-tree source == 682d626d.
- Mode: static reading, git and grep only. No python, pytest, lint, verify, docker or network.
- Memory: consulted (`.claude/agent-memory-local/cold-reviewer/`).

## Status

COMPLETE. All 7 enumerated questions are answered. This was a BOUNDED round, so answering them ends the round.

## Verdict

| Q | Answer | Defect? |
|---|---|---|
| Q1 58 LLVM pins selected / 14 Ubuntu pins not | YES | no |
| Q2 F1-F6, F10, F12 closed by code | YES (all 8) | no |
| Q3 refresh can move IWYU off libllvm<P> with parity green | NO | no: parity fails on any such move |
| Q4 control path makes no anaconda call; detected bump rewrites IWYU once; post-write rc drops only the lock class | YES | no |
| Q5 `llvm-currency` job safety (6 criteria) | YES | no |
| Q6 standing-issue exact title / near-miss / `--close` no-op rc 0 | YES | no |
| Q7 skip / numeric / 23 stays ready beside a later 24 | YES | no |

No findings: no answer shows a defect. Q3's "NO" is the safe outcome. Three bounds are recorded below as notes, not
findings (Q3 `[0]`-only lock read, Q5 banner placement, Q6 default page size). None of them changes the enumeration,
so per the stop condition no further round is triggered.

Not run by this reviewer (forbidden by the brief): pytest, `mise run lint`, verify, actionlint/zizmor, pin-actions,
and any live network probe. Every runtime claim above comes from reading code. Where a claim depends on tool
behaviour (`mise run` propagating exit codes, hk running a glob-less step under `check --all`), the answer is written
so it holds without that assumption, or the assumption is named.

## Answers

### Q1 — 58 LLVM pins selected, 14 Ubuntu pins not: **YES**

Selection path: `llvm_pins` (`llvm_major.py:185-192`) = every `_PIN` match inside `_package_section` whose version
`_APT_LLVM_VERSION.match`es; `pinned_major` (`:195-209`) uses the same predicate. Regexes at `:39-44`.

- Section bound: `_package_section` (`:151-154`) spans `.devcontainer/mise-system.toml:152` to the blank line before
  `[settings]` at `:273` (the next line starting with `[`; the in-comment mentions of `[bootstrap.packages]` at `:14`,
  `:116` start with `#`, so `^\[` cannot stop there, and `re.search` takes the real header at `:151`).
- `_PIN` now uses `[ \t]*` in prefix, comment marker and `space` (`:40-41`), so no match can cross a newline.
- Inventory: `grep -c '"apt:'` = 72, no duplicate names (`sort | uniq -d` = 0). Active LLVM `:200-251` = 52;
  commented `:258-262` (5) + `:271` (1) = 6; Ubuntu `:152-155`, `:159-168` = 14.
- LLVM value: all 58 carry the byte-identical value `1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17`
  (`grep -c` of that exact quoted string = 58). Against `^\d+:\d+(?:\.\d+)*~\+\+\d{14}\+[0-9a-f]+-1~exp1~`:
  `1` `:` `22` `.1.8` `~` `++` `20260714015917` (14 digits) `+` `ca7933e47d3a` `-1~exp1~` — matches. Commented lines
  match `_PIN` through `prefix="# "`, `comment="# "`, so they are selected with `active=False`.
- Ubuntu values, each walked: `12.12ubuntu2.26.04.2`, `20260601~26.04.1`, `8.18.0-1ubuntu2.7`, `2.4.8-4ubuntu3.1`,
  `2.5.1-4`, `1.9.17p2-1ubuntu3.1`, `6.0-29ubuntu1`, `5.9-8ubuntu3`, `16-20260322-1ubuntu1`, `1.0.8-6ubuntu0.1`,
  `8.3-4`, `3.46.1-9ubuntu0.3`, `3.5.5-1ubuntu3.7` have no `<digits>:` epoch, so the leading `\d+:` fails. The one with
  an epoch, `1:1.3.dfsg+really1.3.1-1ubuntu3.1` (`:168`), passes `1:1` and `(?:\.\d+)*`=`.3`, then needs `~` but sees
  `.d` — fails. So 0 of 14 are selected.
- Name-token check on the 58 (`:205`, `(?:-|cpp|libllvm)(\d+)(?=-|$)`): every token is 22. The four major-less names
  (`libc++1`, `libc++abi1`, `libomp5`, `llvm-libunwind1`) yield no token, which matches the comment at `:203-204`.
  `libclang-cpp22` and `libclang-cpp22-dev` yield 22 through `cpp`; `libllvm22` through `libllvm`; `python3-*`'s `3`
  is preceded by `n`, so it is not a token.
- Anchor: `_anchor` (`:157-182`) finds exactly one `apt:clang-22` via tomllib (active) and exactly one via `_PIN` +
  `_ANCHOR` fullmatch (the commented `clang-22-doc`/`clang-22-examples` do not fullmatch `^clang-(\d+)$`).

Enumeration check (is 58/14 the right space?): the pin domain is every `"apt:` line in the section, which is 72 =
58 + 14. There is no third class of apt pin in the file. The only other `[bootstrap.packages]`-shaped pin family would
be a non-apt manager key, and `_PIN` hard-requires `"apt:`.

### Q2 — every in-scope first-review finding closed by code: **YES**

| F | Closed by | Evidence (682d626d) |
|---|---|---|
| F1 | `_FAMILY` deleted; LLVM pins are now chosen by the apt.llvm.org version signature in both `pinned_major` and `llvm_pins` | `llvm_major.py:44`, `:191`, `:199`. `git diff` shows the `_FAMILY` block removed. `libbolt-22-dev` (`mise-system.toml:207`) carries the signature, so a 23 token or a different snapshot value now raises (`:200-208`). |
| F2 | Ubuntu-archive versions never match the signature (no `~++<14 digits>+<hash>-1~exp1~`), so a future `apt:libunwind-dev` Ubuntu pin is excluded by data, not by name | `llvm_major.py:44`, `:199`; Q1 walk of all 14 Ubuntu values |
| F3 | `_PIN` uses `[ \t]*` in prefix, comment marker and `space`, so a match cannot start on a bare `#` line | `llvm_major.py:39-43` |
| F4 (a) | `plan_bump` runs `parity_violations` first and raises listing them | `llvm_major.py:642-644` (and `_bump` `:817-819`) |
| F4 (b) | Every rewrite is count-asserted inside `plan_bump`, before `write()` runs: each pin line exactly once (`counts`, `:656-672`); package table, `_.path`, IWYU, ARG, renovate suite and registryUrl through `_rewrite_once` (count != 1 raises) | `:624-635`, `:673-717`. `_.path`: the only quoted `"/usr/lib/llvm-22/bin"` is `mise-system.toml:353` (grep), so count is 1 today and a re-quoted variant now raises instead of silently skipping |
| F4 (c) | ARG regex `^(ARG LLVM_MAJOR=)\d+(\s*)$` accepts the trailing whitespace parity's `^ARG LLVM_MAJOR=(\d+)\s*$` accepts, and `\g<2>` re-emits it byte-for-byte | `llvm_major.py:695`, `:511` |
| F5 | Comment names `mise run apt-repo -- --toml --pin` for the current major ("defaults to the pinned major") and `llvm-bump` for a major change; "COMPLETE … BOTH image architectures" is now "checked by llvm-bump … at bump time" | `mise-system.toml:174-184`. Enforcement: `handle_apt_repo` defaults to `pinned_major` (`main.py:2732-2736`); `[tasks.apt-repo]` exists (`mise.toml:767`); `--toml`/`--pin` flags exist (`main.py:252`, `:257`); `_index_version` is the bump-time dual-arch check (`llvm_major.py:595-621`) |
| F6 | "Expose the apt LLVM-22 toolchain" → "Expose the apt LLVM toolchain" | `mise-system.toml:343`. `grep -n 'LLVM-2[0-9]'` finds no hit; the same grep hit three `/usr/lib/llvm-` lines, so it can see the file |
| F10 | Tied newest builds (same `(version, build_number)`) with different libllvm majors raise; equal majors pass | `llvm_major.py:293-307` |
| F12 | `handle_apt_repo(args, project_root)` reads the dispatched root; the `_project_root` import is removed | `main.py:2720`, `:2735`; dispatch `"apt-repo": … handle_apt_repo(args, project_root)` (`main.py:3076`) |

### Q3 — can the daily lock refresh move IWYU off libllvm<P> without parity failing? **NO (the gate holds; no finding)**

Trace:

1. TOML pin: `"conda:include-what-you-use" = "0.26"` (`mise-system.toml:70`). It is the only IWYU declaration in the repo
   (`git grep include-what-you-use -- . ':!docs' ':!*.lock' ':!tests'` → this line plus comments and code; control:
   the same grep does find `:70`). So the lock has exactly one IWYU entry (`mise-system.lock:3501`).
2. `_iwyu_pin_violations` (`llvm_major.py:542-546`) fails `"latest"`, a table form or any non-digits-and-dots value.
3. `iwyu_lock_state` (`:352-363`) reads `tools["conda:include-what-you-use"][0]`: the `version` string, plus the single
   `libllvm<N>` in `conda_deps` of `"platforms.linux-x64"` and `"platforms.linux-arm64"`. The lock uses those exact
   quoted keys (`mise-system.lock:3508`, `:3546`), and each has exactly one `libllvm22-…` dep (`:3516`, `:3554`).
4. `_iwyu_lock_violations` (`:549-565`) reports a violation when lock version != TOML pin, or when either platform
   major != P (the apt anchor). A parse failure, a missing platform key or a dep-count error is also a violation
   (`:555-556`), not a silent pass.
5. `parity_violations` includes it by default (`:568-577`). `llvm-parity` dispatches `parity_main(project_root)` with
   the default `include_iwyu_lock=True` (`main.py:3090`, `llvm_major.py:727`). hk `llvm_major_parity` runs that CLI
   with no glob (`hk.pkl:285-287`), inside `allSteps`, which the `check` hook spreads (`hk.pkl:852-854`).
6. CI `lint` runs `hk run check --all` (`ci.yml:116-119`), with no `if:` and no `pull_request` path filter
   (`ci.yml:27-28`, `:80`). `ci-gate` requires lint `success|skipped` (`ci.yml:359-384`), and the lock-refresh PR
   auto-merges only after ci-gate (`refresh.yml:25-30`).

Every way the refresh can move IWYU changes either the lock `version` (≠ `"0.26"`) or a linux `conda_deps` libllvm
(≠ 22). Both fail parity, so the PR cannot reach ci-gate green. The refresh commits lockfiles only (its `paths:` list,
`refresh.yml:136-143`), so it cannot move the TOML pin and the lock together. Even if it did, step 4's `!= P` arm
still fires.

Not a finding, just a bound: only entry `[0]` is read. That is sound while there is one declaration (step 1). A second
IWYU declaration in another merged config would add an unchecked entry.

### Q4 — `--major` control never fetches anaconda; detected bump rewrites IWYU once and excludes only the lock class: **YES**

- Control path (`_bump`, `llvm_major.py:796-820`): `--major` requires `--dry-run` (`:796-798`). The detection is
  built without calling `detect()` (`:804-816`), so `_target_reason` → `iwyu_ready` is never reached. The only fetches
  are `codename_for_base_image` (changelogs.ubuntu.com, `:233-234`) and, inside `plan_bump`, `_index_version`
  (apt.llvm.org, `:598-602`). `plan_bump(..., explicit_control=True)` skips `iwyu_pin_for` (`:685-693`). The only
  readers of `_IWYU_URL` are `iwyu_versions_for` (`:312`) and its two callers `iwyu_ready`/`iwyu_pin_for`
  (`:338-349`), so the control path makes no anaconda call. The render prints "IWYU pin: not planned (explicit
  control; gates skipped)" (`:86-90`).
- Detected path: `plan_bump(..., explicit_control=False)` calls `iwyu_pin_for(target)` (raises when empty) and rewrites
  through `_rewrite_once(r'(?m)^("conda:include-what-you-use"[ \t]*=[ \t]*)"[^"]+"', …)`, which demands exactly one
  match before `write()` (`:686-693`, `:631-634`). The pattern can match only the active line `:70`; comment lines
  start with `#`.
- Post-write rc: `return parity_main(root, include_iwyu_lock=False)` (`:826`) → `parity_violations` skips only
  `_iwyu_lock_violations` (`:576-577`). Anchor/major (`pinned_major`), `_config_violations`, `_iwyu_pin_violations`
  and the four `_python_violations` scans all still run (`:572-581`). The `Next: mise run lock-image (IWYU lock is now
  stale by design)` line is printed (`:825`).

### Q5 — `llvm-currency` job safety: **YES**

| Criterion | Evidence |
|---|---|
| No `${{ }}` inside `run:` | The only expressions in the job are `REPO: ${{ github.repository }}` (job `env:`, `refresh.yml:169`) and three `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` step `env:` lines (`:180`, `:190`, `:195`). The `run:` bodies use `$rc`, `$GITHUB_OUTPUT` and `"$REPO"` only (`:181-186`, `:191`, `:196`). The `if:` lines use bare expression syntax. |
| rc 1 / any non-{0,3,4} fails the job | `… > /tmp/llvm-currency.md \|\| rc=$?` captures rc under the default `bash -e` (no `defaults:`/`shell:` in the file; grep). `case "$rc" in 0\|3\|4) ;; *) exit "$rc";; esac` (`:186`) exits non-zero → step fails → later non-`always()` steps are skipped and the job fails. This holds even if `mise run` remapped codes, because a remap could only turn 3/4 into a failing 1, never turn 1 into 0/3/4. `detect_main` returns 1 on the caught classes (`llvm_major.py:745-756`); an uncaught exception exits Python with 1. |
| Guarded off `pull_request` | `if: github.event_name != 'pull_request'` (`:162`). Triggers are schedule, workflow_dispatch, pull_request only, with no `pull_request_target` (`refresh.yml:41-47`). |
| Least privilege | Job `permissions: {contents: read, issues: write}` (`:165-167`) replaces the workflow default `contents: write, pull-requests: write` (`:48-50`). `issues: write` is needed for create/edit/close, and `gh api …/releases` is a public read. |
| SHA-pinned | `actions/checkout@3d3c42e5…` v7.0.1 (`:172`) and `actions/upload-artifact@043fb46d…` v7.0.1 (`:199`) are the same SHAs the neighbouring `tool-currency` job uses (`:219`, `:270`). `$/.github/actions/setup-mise` is in-repo (house form, `:176`). |
| Token scoped | `GH_TOKEN` is set only on detect (`gh api` in `fetch_releases`, `llvm_major.py:139-141`), upsert and close. It is absent from checkout (`persist-credentials: false`, `:173-174`), setup-mise and upload-artifact. `setup-mise/action.yml` names no token (grep for `token` → none; control: the same file's `uses:` lines are found). |

Observation, outside the Q5 criteria and not a finding: the job is inserted between the "Tool-currency signal" banner
(`refresh.yml:152-160`) and `tool-currency:` (`:205`), so that banner now sits directly above `llvm-currency`.

### Q6 — standing-issue: exact title, near-miss untouched, `--close` no-match rc 0: **YES**

- Exact selection: `next((… for issue in issues if issue["title"] == title), None)` (`standing_issue.py:57-59`).
  The search string only narrows candidates (`:47-48`).
- Near-miss untouched: `edit` and `close` take only the `number` from that exact match (`:63-83`). A miss creates a
  new issue with the exact `title` (`:84-97`). No other mutating argv exists.
- `--close` with no match: `if body_file is None: if number is None: return 0` (`:60-62`), and `runner` is not
  called again. Close mode is entered as `--close --close-comment C`: the CLI passes `body_file=None`,
  `close_comment=C` (`main.py:3082-3089`); `--body-file`/`--close` form a required mutually exclusive group
  (`main.py:300-302`). `--close` without a comment, or `--body-file` with `--close-comment`, is refused with rc 1
  (`standing_issue.py:34-36`).
- Not a finding, just a bound: `gh issue list` runs without `--limit` (gh's default page), so with more than one page of
  open near-miss titles the exact issue could fall outside the page and a duplicate would be created. The
  `tool-currency` precedent has the same shape (`refresh.yml:240-242`, `:254-256`).

### Q7 — `iwyu_versions_for`/`iwyu_ready`: skip, numeric order, 23 stays ready with a later 24: **YES**

- Skip: files are grouped by version and subdir (main label, linux-64 / linux-aarch64 only, `llvm_major.py:316-321`).
  `usable` keeps only versions that have both subdirs (`:322-326`). Skipped versions never reach `_iwyu_newest_major`,
  so their shape is never checked and cannot raise. The function raises only when no version is usable (`:327-329`).
- Numeric: within a version, the newest build is chosen by `_iwyu_build_key` = (int-tuple of the version segments,
  int `build_number`) (`:275-281`, `:295`). Matching versions are sorted by `tuple(map(int, version.split(".")))`
  (`:335`), so `iwyu_pin_for` takes `versions[-1]`, the numeric maximum (`:343-349`).
- 23 with a later 24: each usable version is judged on its own newest per-subdir builds (`:330-334`), and
  `iwyu_ready(23) = bool(iwyu_versions_for(23))` (`:338-340`). A 0.27→libllvm23 version stays in the list no matter
  what 0.28 targets. The old rule judged only the newest version overall (removed hunk in
  `git diff 21b0b4ee 682d626d`).

## Findings

| Severity | Claim | file:line | Cited |
|---|---|---|---|
| — | None. Every question was answered in the non-defective direction. | — | Answers Q1-Q7 above |

## Notes (bounds, not findings; ticket only if the coordinator wants them)

- Q3: `iwyu_lock_state` reads only `tools["conda:include-what-you-use"][0]` (`llvm_major.py:354`). That is sound
  while `mise-system.toml:70` is the only declaration.
- Q5: the `llvm-currency` job splits the "Tool-currency signal" banner (`refresh.yml:152-160`) from its job
  (`:205`). This is cosmetic.
- Q6: `gh issue list` without `--limit` (`standing_issue.py:38-52`) returns gh's default page. The tool-currency
  precedent has the same shape.
- The hk claim in Q3 step 5 (a glob-less step runs under `hk run check --all`) relies on hk semantics. The same step
  (`hk.pkl:285-287`) existed before this diff and the first review already cited it as wired. Not re-probed here.

## GitHub repos touched

_None._
