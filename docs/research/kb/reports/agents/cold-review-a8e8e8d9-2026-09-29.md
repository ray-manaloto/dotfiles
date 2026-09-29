# Cold review — a8e8e8d9 (COMPLETE)

- Subject: `a8e8e8d98cea2396121f21bcf841720f83ea6772` (base `8454778caef6922a06eec17c8660db3bd6d0ecd6`)
- Author family: codex (codex-sol-implementer); reviewer: cold-reviewer (Opus), diff-only
- Governing spec: `docs/specs/s28b-1-p2996-single-literal.md` (added by this commit)
- Round: 1 (open hunting), so by the adversarial-review stop rule it cannot end the loop on any outcome. It promotes
  to one bounded round.
- Memory: consulted (`.claude/agent-memory-local/cold-reviewer/`: contract-token replay, mutation harness, gate
  locations, doc-sweep patterns)
- Constraints honoured: no source edits and no local image build. The only docker calls were `docker buildx bake --print`.

## Verdict

**SHIP after the two MEDIUMs are addressed in this unit of work.** Both fixes are cheap, doc/contract-shaped, and change no
build logic. The core mechanism is correct, and I checked it against Renovate's own source and its real dry-run output:

- the single literal;
- the extractor, scoped to bake;
- the ungrouped daily auto-merging PR;
- the Dockerfile with no default.

The claimed fail arms all reproduce.

## Findings

| # | Severity | Claim | file:line | Evidence / control arm |
|---|---|---|---|---|
| F1 | MEDIUM | The new `test -n` guard is **load-bearing, not cosmetic**. Without it, an empty `CLANG_P2996_REF` makes `git fetch --depth 1 origin ""` **succeed** and build the remote's **default branch** (`purpose` for clang-p2996). The p2996 hash would still key that build on the canonical pinned-SHA tag, because `main.py:2716` treats empty as "use the pin". The spec records the opposite premise ("fails loudly") and justifies the guard as message quality only. No gate binds the guard, so a later tidy-up can delete it with every check green. | `.devcontainer/Dockerfile:465`; spec `docs/specs/s28b-1-p2996-single-literal.md:249` (I2), `:374` (P35), `:319-323` (Q1); `python/src/dotfiles_setup/main.py:2713-2716` | **Probe 3.** Local bare repo, default branch `purpose` plus `p2996`. `git fetch --depth 1 origin ""` → **rc=0, FETCH_HEAD = the `purpose` tip**. SHA arm → rc=0, the `p2996` tip. **Empty reaches the build even through bake:** `CLANG_P2996_REF= docker buildx bake --print p2996-cache` → `args.CLANG_P2996_REF == ''`. Meanwhile `main.py:2716` is `os.environ.get("CLANG_P2996_REF") or None`, commented "Empty/unset => the committed pin". **Unbound:** `git grep -F` for `CLANG_P2996_REF unset`, `test -n "${CLANG_P2996_REF}"` and `build via docker bake` over suites.toml, hk*.pkl, tests/ and python/src → 0 hits. Controls `COPY --from=clang-builder` and `DCMAKE_INSTALL_PREFIX=/opt/clang-p2996` → `suites.toml`:1 each. Mutation U6 (delete the guard) → 8/8 green. **Reachability:** CI exports the override only when non-empty (`build-publish.yml:322,467,609,881,1126`), and local base builds are banned, so today it needs a manual path or a future workflow edit. The smoke ref-pin (`image.py:660-664`) would fail the image afterwards, but only after a cold compile and after `:p2996-<hash>` is pushed. **Fix:** add a guard substring (e.g. `CLANG_P2996_REF unset`) to the `build.clang-p2996-reflection` `per_path_tokens`, and correct P35/I2/Q1 in the spec. |
| F2 | MEDIUM | This diff **inverts a live operator-facing claim it did not update.** `tool-currency-check` SKILL.md's custom-code inventory still says the Renovate git-refs manager covers the "Dockerfile `ARG` only; bake's default is untracked (#1434)". After this commit, the manager covers bake only and the Dockerfile has no default. This skill drives the "retire or keep custom code" decision. Read as written, it tells a currency audit that bake is untracked and invites re-wiring a scheduled `p2996-refresh` writer, the two-writer state that `refresh.yml:21-24` and `p2996_refresh.py:16-20` now forbid. The spec's objective says to "correct every piece of prose", but its §2 file list and "Deliberately NOT changed" list both miss this file. | `.claude/skills/tool-currency-check/SKILL.md:74`; mirror `.agents/skills/tool-currency-check/SKILL.md:74` (a real file, not a symlink, so it needs the mirror regenerated too) | The line was added by the base commit itself (`git log -S"bake's default is untracked"` → `8454778c`, #1439), so it was **true at base and false at HEAD**. Sweep: `git grep` over `p2996-refresh\|p2996_refresh\|CLANG_P2996_REF` excluding the research/spec/receipt records → this is the only stale current-state claim left. Its neighbours in the same sweep (P2996-CACHE.md, mise.toml, refresh.yml, the workflows/AGENTS.md row) all read correctly. |
| F3 | LOW | `test_clang_package_rule_leaves_the_image_group_after_it` checks the rule's **shape and position**, not whether it **takes effect**. Three realistic edits leave clang back in `image-build inputs`, or untracked, with 8/8 green: a mis-named extra matcher, a later file-name group rule, and `enabled:false`. The repo has already lived the first class (renovate.json's packageRules[7] description: "a guessed depName silently matches NOTHING"). | `tests/test_p2996_single_literal.py:130-156` | Mutation harness (`git archive a8e8e8d9` + `git init` + `PYTHONPATH`; baseline 8 passed):<br>• U1 `matchDatasources:["git"]` → **GREEN**<br>• U2 appended `{"matchFileNames":["docker-bake.hcl"],"groupName":"bake inputs"}` → **GREEN**<br>• U3 `enabled:false` → **GREEN**<br>The harness discriminates. Controls in the same harness all went RED: U4 drop `groupName:null`, U5 short depName, U8 `automerge:false`, U9 unanchored file pattern. **Hardening:** assert the rule's matcher keys are exactly `{matchDepNames}`, that `enabled` is absent, and that no later rule sets `groupName` or matches `docker-bake.hcl`. |
| F4 | LOW | `test_dockerfile_arg_has_no_default` asserts **exactly one** `ARG CLANG_P2996_REF` line. That makes a legitimate no-default re-declaration in a later stage (the standard way to reuse an ARG after `FROM`, e.g. for a LABEL) fail a test whose name says it checks "has no default". | `tests/test_p2996_single_literal.py:92-95` | U7: add `ARG CLANG_P2996_REF` after `FROM devcontainer AS devcontainer-runtime` → **RED** (`test_dockerfile_arg_has_no_default`). Tests 1-2 already catch the #904 shape they target (arm R1). An intent-preserving form: every matching line equals `ARG CLANG_P2996_REF`. |
| F5 | LOW | The TEST-INDEX row overclaims the test. It says "Renovate extracts exactly that HCL value" and that the rule "removes the dependency from `image-build inputs`". The test runs a **Python `re` proxy** (its own docstring says so) and checks rule order only; F3 shows that removal is not checked. | `tests/TEST-INDEX.md:87` | Q-CLAIM. "Renovate extracts" has no enforcing line: nothing in the file invokes Renovate, and `_py_pattern` (`:38-45`) is the proxy. "Removes … from image-build inputs" also has none (U2 stays green). |
| F6 | LOW | The guard's message names the wrong condition and the wrong remedy for one reachable case. `test -n` fires on **set-but-empty** as well as unset, and building "via docker bake" does not help when the ambient `CLANG_P2996_REF` is set to empty, because bake forwards the empty value. | `.devcontainer/Dockerfile:465` | Probe 3 bake arm: `CLANG_P2996_REF= … bake --print p2996-cache` → `''`. Suggested text: `CLANG_P2996_REF empty or unset; unset an empty env override and build via docker bake`. |
| F7 | LOW | `ci.yml`'s schedule comment still says `refresh.yml` "*changes* the pins", naming `CLANG_P2996_REF`, and says the 02:00 nightly picks up a "same-day pin bump" from its 00:00 run. `refresh.yml` has not bumped this ref since #169, and it is now Renovate's `before 6am` PR. The comment was already stale before this diff; the diff swept the other p2996 prose and missed this one. | `.github/workflows/ci.yml:4-8` | `refresh.yml:20-24` (this diff) says Renovate is the writer and forbids a second scheduled writer. `renovate.json` rule `schedule: ["before 6am"]`. Q-SCOPE: pre-existing, so fold it into this change or ticket it. |
| F8 | LOW | The tracked spec contradicts itself on its own status. The header reads "Status: DRAFT … **Not ratified**. Stop for the architect before dispatch", while the closing section is "Architect rulings (2026-09-29) — **RATIFIED**". A later reader of `docs/specs/` gets the wrong status from line 3. | `docs/specs/s28b-1-p2996-single-literal.md:3`, `:379` | Read directly. The commit message says "ratified 2026-09-29", which agrees with `:379`. |
| F9 | INFO | The only discriminating evidence for "clang is **not** in `image-build inputs`" (the spec's V2 pass arm) lives in a **gitignored** log. The tracked implementer report's V2 line says "one clang digest update" and never names the branch. | `docs/research/kb/reports/agents/codex-sol-implementer-s28b-1-2026-09-29.md` (V2 line); `.agent/logs/s28b-1/V2-pre-bump-renovate-report-mise.json` (gitignored) | I extracted it (probe 1): clang → `renovate/bloomberg-clang-p2996-digest`, with bake's other deps → `renovate/image-build-inputs` in the same report as the control. Put that one line in the PR body (agent-artifact-conventions: "promote anything a later session will cite"). |
| F10 | INFO | Spec §3.7 marks the Dependency Dashboard as a possible lag signal "if the extended preset enables it (**unverified**)". The preset disables it, so the open-PR check (`renovate-status`) is the only lag signal. The same fetch settles P33: the timezone is `America/Chicago`. | `docs/specs/s28b-1-p2996-single-literal.md:213` | Probe 5: `gh api repos/jdx/renovate-config/contents/default.json` → `"dependencyDashboard": false`, `"timezone": "America/Chicago"`, `"rebaseWhen": "conflicted"`. Control: a bogus path → rc=1. |

## Q-FRESH / Q-SCOPE / Q-CLAIM

**Q-FRESH** (is each decision re-validated just before its action?)

- **Build: pinned ref → `git fetch`.** The guard re-checks non-empty in the **same** `RUN`, immediately before the fetch
  (`Dockerfile:465-468`). Fresh. The hash/build disagreement on an empty override (F1) is a temporal-looking seam, but it is
  a resolution mismatch rather than staleness.
- **Renovate: upstream head moved → PR → auto-merge.** GitHub-native auto-merge waits on `ci-gate` at the PR's current
  head. A push inside the window restarts CI (`ci.yml:47-49` `cancel-in-progress` on PR refs). The preset's
  `rebaseWhen: "conflicted"` means a moving `main` does not force a rebase and cold-build restart. `strict=false`
  (research R:146-148, `A`) lets a behind-main PR merge on a result computed against an older merge base. That is
  repo-wide and not specific to this diff.
- **Smoke: EXPECTED vs ACTUAL.** CI reads the HEAD bake pin of the same commit it built (`image.py:87-100`). The
  local tier-3 check reads the merge-base pin (`image.py:2068-2086`). Both are fresh for their image.
- **Manual `p2996-refresh`.** It reads bake, runs `ls-remote`, and writes only on change (`p2996_refresh.py` `refresh`).
  There is no code change here.

**Q-SCOPE** (in scope for #1434/#1435, or a sibling?)

| Finding | Scope |
|---|---|
| F1–F6, F8 | In scope. Each touches an artifact this diff adds or changes. |
| F2 | In scope. It is the spec's own §1 objective. |
| F7 | Pre-existing. Fold in, or ticket. |
| F9, F10 | Evidence and spec hygiene. |
| `main.py:2716` | **Sibling ticket, not a change request here.** It treats an empty override as "use the pin" while bake treats it as a value, so the hash and the build can describe different refs. The guard now makes that case fail loudly rather than poison the cache, which is why F1 is to *bind the guard*, not to change `main.py`. |

**Q-CLAIM** (every clause of every operator-facing string this diff adds or changes, with its enforcing line)

| String | Clause | Enforcing line | Verdict |
|---|---|---|---|
| Dockerfile guard `echo` | "CLANG_P2996_REF unset" | `test -n` (`Dockerfile:465`) fires on empty too | **F6** |
| | "build via docker bake" | bake default (`docker-bake.hcl:101-103`), but only when the env var is unset | **F6** |
| image.py OK line | "matches pinned CLANG_P2996_REF" | `image.py:661` equality | ok |
| | "build==pin only" | no freshness logic in the smoke | ok |
| | "upstream freshness is tracked by Renovate" | renovate.json customManager + packageRule; ungrouping verified by real dry-run (probe 1) | ok (gate strength: F3) |
| mise.toml `p2996-refresh` description | "writes only on change" | `p2996_refresh.refresh` `new_ref == old_ref` return | ok |
| | "own daily PR" | `schedule: ["before 6am"]` + `groupName: null` | ok |
| | "no scheduled job" | refresh.yml has no p2996 job (sweep) | ok |
| renovate packageRule description | "minimumReleaseAge is INERT" | git-refs has 0 `releaseTimestamp` refs (control: github-tags has 6) | ok |
| | "build-publish cannot skip" | `ci.yml:297` filter + `:316-321` decide (non-`.md`) + `:339` `if:` | ok (note `ci-gate` accepts `skipped`, `:377`, so this clause carries weight and holds) |
| | "a once-a-day window bounds cost" | `schedule` gates creation **and** updates to a 6-hour window. An upstream push inside the window can update the branch and restart a cold build. | ok as "bounded"; not "one compile per day". Upstream commit cadence **UNVERIFIED**. |
| customManager description | "`\s` crosses newlines … `g`-only flags" | `modules/manager/custom/regex/strategies.js:9` `regEx(matchString, "g")` | ok |
| Dockerfile comment | "Every build of this file goes through bake" | every bake target that reaches `clang-builder-cold` carries the arg (probe 4) | ok (the empty-env caveat is F1/F6) |
| TEST-INDEX row | "Renovate extracts" / "removes from image-build inputs" | none | **F5** |

## Probes run

1. **Renovate `groupName: null` really ungroups: source plus a real run, both arms.**
   - Source (installed `npm:renovate` 44.117.1): `config/utils.js:14-17` merges each rule by object spread, so a later
     `groupName: null` replaces an earlier string. `workers/repository/updates/branch-name.js:42` enters the group path
     only on a truthy `groupName`, and ignores the preset's `groupSlug` when `groupName` is null.
   - `schedule` has no `mergeable` flag (`config/options/index.js:986-995`), so the rule's `["before 6am"]` replaces
     the global `["at any time"]` rather than being concatenated with it.
   - Real run: the implementer's pre-bump dry-run report (`.agent/logs/s28b-1/V2-pre-bump-renovate-report-mise.json`,
     gitignored) puts clang on `renovate/bloomberg-clang-p2996-digest`.
   - **Control arm, same report:** bake's two other deps, the shared.toml deps and the Dockerfile/mise-system deps all
     land on `renovate/image-build-inputs`. The field can show a grouped branch, so the ungrouping is real.
2. **The smoke OK line renders as valid shell.**
   - `build_tier3_script(expected_p2996_ref="f"*40, emulated=True)` emits
     `echo "OK: … matches pinned CLANG_P2996_REF ""(build==pin only; …)"`. The Python `\`+newline is a line
     continuation.
   - `bash -n` on the whole script returns rc=0.
   - The substring `tests/test_image_smoke_exec.py:237` asserts survives.
3. **Empty-ref behaviour** (F1/F6). Isolated git config (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`),
   `/usr/bin/git` 2.54.0.
   - Setup: a bare repo whose default branch is `purpose`, plus a `p2996` branch.
   - Empty-ref arm → rc=0, FETCH_HEAD = the `purpose` tip.
   - SHA arm → rc=0, the `p2996` tip.
   - Bake arm: `CLANG_P2996_REF= mise exec -- docker buildx bake --print p2996-cache` → `''`.
4. **Bake target coverage.** `docker buildx bake --print dev base p2996-cache dev-load validate help`:
   - `dev`, `dev-load`, `validate` and `p2996-cache` all carry `CLANG_P2996_REF=f17c8d6c…`.
   - `base` (stage `devcontainer-base`, `Dockerfile:33`) and `help` (call=targets) do not, and neither reaches
     `clang-builder-cold` (`:417`). The only consumers of that stage are `p2996-export` (`:546`) and then
     `devcontainer` (`:625`).
   - Non-bake builds: `git grep` for `buildx build|build-push-action|docker build` over non-doc files → one prose hit
     (`sync.py:46`, a docstring). Control: `buildx bake|bake-action` → hits in 5 files.
   - `devcontainer.json:92` builds `Dockerfile.host-user`, not this file.
5. **jdx preset.** `gh api repos/jdx/renovate-config/contents/default.json`, rc=0. Bogus-path control → rc=1.
6. **Mutation harness** (F3/F4). `git archive a8e8e8d9` into the scratchpad, then `git init` + `git add -A` (the test
   calls `git ls-files`), then `PYTHONPATH=<copy>/python/src`. Baseline: 8 passed.
   - Claimed arms reproduce: R1 duplicate pin → tests 1-3 red; R2 old matchString → tests 4 and 6 red; R3 rule moved
     first → test 8 red.
   - Unclaimed arms: U1/U2/U3/U6 green; U4/U5/U7/U8/U9 red.
   - One arm tripped the harness's own "did it apply" assertion (`test -n` occurs twice in the Dockerfile). I re-ran it
     with the guard-specific string. The final check reported all three files byte-restored.
7. **Contracts.**
   - Strict `per_path_tokens` replay over the whole `suites.toml`: 1,348 tokens, 0 fails.
   - `"\nARG CLANG_P2996_REF\n"` count: 1 at HEAD, 0 at base (`8454778c`). Control: `ARG CLANG_P2996_REPO=` → 1 at HEAD
     (it is a different token and does not contain it).
8. **Real-repo gates, focused.**
   - `pytest` on `test_p2996_single_literal`, `test_p2996_hash`, `test_p2996_refresh`, `test_image_arch` and
     `test_renovate_validate` → 148 passed, rc=0.
   - `hadolint .devcontainer/Dockerfile` → rc=0.
   - `.github/workflows/AGENTS.md` = 11,819 chars (base 11,872), under the 12,000 ceiling.
   - Not re-run by me: the full `mise run lint`/`verify`/`pytest`, and V11 CI. Those figures are the implementer's and
     the architect's, **inherited, not re-derived**.
9. **Renovate-source claims.**
   - The regex manager compiles each matchString with `"g"` only (`strategies.js:9,16,32`).
   - `releaseTimestamp` hits: git-refs 0; github-tags 6 (control).

## Recommended disposition

1. **F1**
   - Bind the guard: add `"CLANG_P2996_REF unset"` (or the reworded F6 text) to the
     `build.clang-p2996-reflection` `per_path_tokens`, and prove it with `mise run token-check`.
   - Correct spec P35, I2 and the Q1 rationale.
2. **F2**
   - Rewrite `tool-currency-check/SKILL.md:74` to the new state, for example:
     *"Renovate `git-refs` manager — bake's `CLANG_P2996_REF` default only (the single literal, S28b-1 #1434);
     `p2996-refresh` is the manual path. A scheduled job would be a second writer."*
   - Regenerate the `.agents` mirror.
3. **F3–F8:** fix in this unit, or ticket F3 and F7 as test and prose follow-ups.
4. **Sibling ticket:** `main.py:2716` empty-override semantics diverge from bake's (Q-SCOPE).

## GitHub repos touched

- [jdx/renovate-config](https://github.com/jdx/renovate-config) — `default.json` preset: timezone, rebaseWhen,
  dependencyDashboard, grouping rules
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed commit and its consumers (local
  checkout)
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — source read from the installed npm package
  44.117.1 (`config/utils.js`, `branch-name.js`, `package-rules/index.js`, `custom/regex/strategies.js`,
  `datasource/git-refs`, `lookup/digest.js`)
