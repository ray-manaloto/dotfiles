# Session audit — retrieval misses (session 03414a92, 2026-10-01)

Lane: session-handoff §1c "retrieval misses". Method: Brief S of
`docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md` (method only).
Transcript: `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/03414a92-bb13-4324-83d2-fac74c0cd046.jsonl`.

Status: COMPLETE (written incrementally).

## Findings

Flat transcript dumps used: main session (3,257 records) + 18 subagent transcripts (14,055 records), built with `jq`
into the scratchpad. Line refs below are `flat.txt:<n>` (main) with ISO timestamps so they can be re-found.

### M1. `$?` read AFTER a `$(...)` in the same `echo` reports the substitution's rc, not the command's

- **Evidence:** `13:25:23Z` (flat.txt:916) the probe helper
  `run(){ … > $S/x.log 2>&1; echo "$1 $(basename $2) rc=$? rules=$(jq …)"; }` printed
  `gitleaks .gitleaks.toml rc=0 rules=github-pat` — rc=0 WITH a finding, i.e. `$?` was `basename`'s. The next
  command (`13:25:43Z`, flat.txt:918) silently switched to `…; r=$?; echo "… rc=$r …"`. The wrong rc was never
  called out; it was routed around. (The other ~60 `echo "x rc=$? n=$(wc …)"` probes in the session put `$?`
  BEFORE the substitution, so they were fine — this is a latent trap, not a habit.)
- **Cost:** one probe whose rc column was meaningless (5 rows), one re-run; risk of a published false "rc=0".
- **Control:** the same session's later probes `echo "no-deps rc=$? stderr_bytes=$(wc -c < $T/e)"` (flat.txt:1996)
  returned `rc=0 … control rc=0 stderr_bytes=125`, consistent with `$?` expanded first when it precedes `$(...)`.
- **Should carry it:** `.claude/rules/long-running-command-hangs.md`, rule 3 (the file-captured-rc recipe every
  probe copies). **Line to add** at the end of rule 3:
  > Capture the rc FIRST: `cmd …; r=$?; echo "rc=$r n=$(wc -l < f)"`. A `$?` written after any `$(...)` in the
  > same word reads the substitution's exit status, not `cmd`'s — measured 2026-10-01, `rc=0` printed beside a
  > finding.

### M2. `betterleaks dir` honours `.gitignore`; `gitleaks dir` does not

- **Evidence:** `13:23:57Z` SendUserMessage: "scanning the `.agent/` copy reported 0 bytes, because betterleaks
  `dir` honours `.gitignore`. I used a scratch copy of the files as the real arm." Recorded only in root
  `findings.md` (gitignored) at `13:25:56Z`.
- **Cost:** one scan that read 0 bytes (a would-be false "clean" on the held files) plus a scratch-tree rebuild.
- **Currently carried?** No. `git grep -i 'betterleaks.*gitignore'` over tracked files (excluding raw mirrors)
  returns only an unrelated cold-review row; control arm `git grep -c 'betterleaks dir'` hits `hk.pkl` and 4
  reports, so the grep can see the corpus. `.gitleaks.toml:1-6` states the OPPOSITE behaviour for gitleaks only,
  which is exactly the sentence a reader generalises to both scanners.
- **Should carry it:** `.gitleaks.toml` header (both scanners read this file; it is what a scanner-arm author opens).
  **Line to add** after line 6:
  > `# ⚠️ betterleaks is the opposite: `betterleaks dir` HONOURS .gitignore (measured 1.9.0, 2026-10-01: a scan of
  > # the gitignored .agent/ tree read 0 bytes). Arm a betterleaks probe on a scratch copy outside the repo, never
  > # on a gitignored path.`

### M3. Bare `mise exec -- <tool>` from a scratch dir outside the repo fails: no global version

- **Evidence:** `13:23:51Z` (flat.txt:740) `cd …/scratchpad/bl; mise exec -- gitleaks dir …` → `Exit code 2`,
  `jq: Could not open file gl.json`; diagnosed at `13:23:59Z` from the log: "Set a global default version with one of
  the following: mise use -g gitleaks@8.30.0". Re-run from the repo root at `13:24:06Z`. Later in the session the
  correct form was used unprompted (`mise -C ~ exec -- webclaw …`, flat.txt:2865).
- **Cost:** 1 failed run + 1 diagnosis call.
- **Should carry it:** `.claude/rules/probes-need-a-control-arm.md` is too general; the place probes are recipe'd is
  memory `feedback_host_is_not_a_control_arm_for_ci.md` ("Name `<tool>@<version>`, never a bare shim"). Better
  home, read at the moment of writing a scratch probe: `.claude/rules/long-running-command-hangs.md` rule 3. **Line
  to add:**
  > A probe that `cd`s into the scratchpad loses the repo's mise config: run `mise -C <repo> exec -- <tool>` (or
  > `<tool>@<version>`), never a bare `mise exec -- <tool>` from outside the checkout.

- **M1 arm (this audit, 2026-10-01):** `false; echo "a=$(true) rc=$?"` → `rc=0`; `false; echo "rc=$? a=$(true)"` →
  `rc=1`, identical in zsh and `bash -c`. So the ordering, not the shell, decides it.

### M4. The step-00 Claude Code corpus is stale AND the rule points at the superseded copy; the session re-derived the code.claude.com fetch surface by hand

- **Evidence:** `18:56:41Z` (flat.txt:2647) the session `stat`ed `$CC/changelog.md` → `Sep 15`, found no `2.1.28x`,
  then probed `robots.txt`, `sitemap.xml` (218 `/docs/en`), `/docs/llms.txt` (409 lines) and `<page>.md`
  (`200 text/markdown`) at `18:56:55Z`, then built a 225-page mirror (`19:08:58Z`–`19:14:00Z`) by a union of
  sitemap + llms.txt + `webclaw --map`, finding 7 pages absent from the sitemap and 1 (`claude-tag`) that serves
  HTML only.
- **What was already on disk and not handed over:**
  1. KB `currency.toml:1132-1150` says `sources/agent-harness-docs/docs/claude-code` was **superseded on
     2026-08-24** by `sources/claude-code-docs` (and KB `sources/agent-harness-docs.manifest:5` repeats it). The
     dotfiles eager rule `.claude/rules/research-doc-sources.md:25,30` still hard-codes
     `CC=$KB/agent-harness-docs/docs/claude-code`, and `git grep -c 'agent-harness-docs/docs/claude-code'` hits
     **98** tracked dotfiles files vs **1** for `claude-code-docs/content`.
  2. Measured by this audit: NEITHER mirror is current — `claude-code-docs/.../changelog.md` tops out at
     **2.1.257** (file dated Sep 1), `agent-harness-docs/.../changelog.md` at **2.1.273** (Sep 15); the running
     harness is 2.1.287. So the "superseded" mirror is the staler one, and no task refreshes either from dotfiles.
  3. KB `sources/agent-harness-docs/scripts/fetch_claude_docs.py:32-34,348` already encodes the fetch surface:
     sitemap `https://code.claude.com/docs/sitemap.xml` → `f"{base_url}{path}.md"`.
- **Cost:** ~6 probe calls + two AskUserQuestion rounds on mirror design; the completeness facts (sitemap misses 7
  pages; `claude-tag` is HTML-only) are genuinely new and worth keeping.
- **Should carry it:** `.claude/rules/research-doc-sources.md` step 00 — the file loaded eagerly at exactly this
  moment. **Lines to add** directly after the `grep -rn "<topic>" "$CC/"` block:
  > ⚠️ The corpus is a PULLED snapshot, not live: before trusting it for a release newer than its changelog head
  > (`grep -m1 -E '2\.1\.[0-9]+' "$CC/changelog.md"`), compare against `claude --version`. On a gap, fetch the
  > page live: code.claude.com serves every page as `<url>.md` (`text/markdown`) and indexes them at
  > `https://code.claude.com/docs/llms.txt`; the sitemap omits some pages (7 on 2026-10-01), so discover from the
  > union of both.
  
  and fix the pointer itself (separate reviewed change; KB says the path moved): the
  `CC=` line should name whichever mirror the KB currently designates, not a hard-coded retired path.

### M5. `${!v}` (bash indirect expansion) in the zsh Bash tool → `bad substitution`

- **Evidence:** `18:57:08Z` (flat.txt ~2700) presence loop `for v in DISABLE_TELEMETRY …; do [ -n "${!v}" ] && …`
  → `Exit code 1`, `(eval):1: bad substitution`; re-run at `18:57:13Z` with `printenv $v >/dev/null && echo SET`.
- **Cost:** 1 failed call.
- **Already carried?** Half: `.claude/rules/secrets-out-of-the-shell-env.md` rule 7 recommends `printenv VAR
  >/dev/null` but only for a single named variable; it never says what to do in a loop over names, which is where
  `${!v}` gets reached for.
- **Should carry it:** `.claude/rules/secrets-out-of-the-shell-env.md` rule 7, after "read the rc". **Line to add:**
  > Looping over names: `printenv "$v" >/dev/null && echo "$v=SET" || echo "$v=ABSENT"`. `${!v}` is bash-only — the
  > Bash tool runs zsh, where it fails `bad substitution` (measured 2026-10-01).

### M6. `[deps.uv] auto = true` + an isolated `MISE_STATE_DIR` ⇒ `uv sync` runs before every `mise exec` and writes to stderr

- **Evidence:** `15:42:46Z` gate pytest rc=1, `test_fnhook_gates::…[bad-return-typecheck]` asserting
  `result.stderr == ""` got `[deps.uv] Resolved 153 packages … ✓ done`. Diagnosis took 7 calls (`15:42:51Z` →
  `15:45:34Z`): isolated re-run, stash control arm, `mise.toml` read, a `mise exec -- true` probe (stderr 0 bytes in
  the REAL state dir — so not reproducible outside the isolation), `mise deps --explain uv` with and without a temp
  `MISE_STATE_DIR` (`stale (no previous state)` vs `fresh`), then `mise exec --help` → `--no-deps`. Fix `0bbb6b2d`
  (`fnhook_gates.py:435-439` now carries the comment). A follow-on failure (`15:46:0xZ`, flat.txt:2015) came from the
  repo's own test asserting `argv[2]` is a `<tool>@<version>` spec; resolved by placing `--no-deps` after the spec
  (both positions work: flat.txt:2000 vs 2044).
- **Already carried?** Partly: memory `project_session_2026-09-26.md:22` says "`MISE_STATE_DIR` isolates tracking
  AND trust" but not deps state; `mise.toml:4-7` (`[deps.uv]`) has no comment at all. The `mise deps --help` text
  ("Providers with `auto = true` run before `mise exec` and `mise run` unless `--no-deps`") is the primary source and
  was only read at call 6.
- **Should carry it:** `mise.toml`, directly above `[deps.uv]` (the line every isolation author edits around).
  **Line to add:**
  > `# auto = true runs this before EVERY `mise exec`/`mise run` whose deps state is stale. An isolated
  > # MISE_STATE_DIR has no record, so it is ALWAYS stale and `uv sync` prints to stderr: pass `--no-deps`
  > # (fnhook_gates.py). Diagnose with `mise deps --explain uv`.`

### M7. `gh api …/actions/jobs/<id>/logs` refuses ANSI output; `gh run view --job <id> --log-failed` is the working route

- **Evidence:** `15:32:11Z` three `gh api repos/…/actions/jobs/$j/logs` calls → `rc=1 lines=1`; `15:32:20Z` cat shows
  `the response contains terminal escape sequences; pass --allow-escape-sequences to output it anyway`; `15:32:27Z`
  `gh run view -R … --job $j --log-failed` → rc=0, 353 lines.
- **Cost:** 2 calls.
- **Already carried?** `git grep -n 'log-failed' -- .claude` → checked below.
- **Should carry it:** `.claude/rules/gh-cli-watch.md` "Canonical patterns" block (the file loaded whenever a CI read
  is in progress). **Line to add** to the block:
  > `gh run view -R ray-manaloto/dotfiles --job <job-id> --log-failed > job.log  # NOT gh api …/jobs/<id>/logs: it refuses ANSI output (rc=1)`

### M8. Ray's two standing asks (local OTel sink; dotfiles owns `~/.config/mise/config.toml`) were asked AGAIN

- **Evidence:** `19:37:44Z` Ray: "can we just add this check into the ~/.config/mise/config.toml as its own task";
  the session then asked (`19:40:50Z`) "Full OTel … Where should telemetry go?" and "The mod-exposure audit should run
  for every project on this Mac. How should it be built?". Ray (`19:44:07Z`): "i've asked for this repeatedly before"
  and "i've asked about this already, it might be in the task plan backlog … dotfiles should host all scripts for
  ~/.config/mise/config.toml". Only THEN (`19:44:11Z`) did the session `grep -n -i 'otel\|collector\|telemetry'
  task_plan.md` and `gh api '/search/issues?…otel'`, and it apologised at `19:44:37Z`: "I missed both prior asks.
  They're already in your plan … §5b … #1014–#1018 and #431".
- **What was on disk:** `task_plan.md:1960-1965` (§5b, operator: this project should own `~/.config/mise/config.toml`
  via mise's dotfiles support), `:2084-2092` ("OWNERSHIP IS SETTLED by Q23 … DOTFILES owns it"), `:2101-2114` (Q22:
  "The operator specifically suspects **OpenTelemetry settings we are not enabling**").
- **Cost:** one wasted AskUserQuestion round on a settled ruling, and the operator had to restate it — the costliest
  miss of the session.
- **Why no gate caught it:** `ask_quality` requires a citation, and the questions cited a fresh report
  (`claude-mods-refactor-plan-2026-10-01.md`), so the hook passed. It checks that a citation EXISTS, not that the
  backlog was searched.
- **Should carry it:** `.claude/rules/clarify-before-acting.md` rule 4 ("Verify discoverable facts yourself"), the
  rule loaded at the moment of asking. **Line to add** under rule 4:
  > Before asking about ANY topic, run `grep -n -i '<topic>' task_plan.md` and
  > `gh api '/search/issues?q=repo:ray-manaloto/dotfiles+is:open+<term>'`; if a ruling exists, cite it and ask only
  > the open remainder. 2026-10-01: Ray was re-asked two settled rulings (task_plan §5b Q22/Q23: local OTel,
  > dotfiles owns `~/.config/mise/config.toml`).

- **M7 coverage probe (this audit):** `git grep -n 'log-failed' -- .claude docs/rules-evidence .github/workflows/AGENTS.md`
  → 0 hits; control `git grep -c 'gh run view' -- .claude/rules/gh-cli-watch.md` → 1. Not carried.

### M9. Renovate `packageRules`: the clang-p2996 rule must stay LAST (later rules win) — learned from a red pytest

- **Evidence:** the S29-00 python rule was appended after clang; `15:51:1xZ` full pytest
  `FAILED tests/test_p2996_single_literal.py::test_clang_package_rule_leaves_the_image_group_after_it` (`1 failed,
  2757 passed … 3:03`); the test's own comment (`:162`) "LAST, so no later rule can re-group or re-schedule it
  (later rules win)". Fixed at `15:51:29Z` by moving python above clang.
- **Cost:** one ~3-minute full pytest + 2 edit calls. The gate worked; the information arrived late.
- **Currently carried?** Only in the test. The clang rule's own `description` in `renovate.json` (the text an editor
  reads when appending a rule) explains schedule/soak/auto-merge but never says it must be last; `grep -n -i
  'last\|later rule' renovate.json` → 0 hits (control: the same file's `description` was read and printed above).
  The S29-00b cold review F5 adds the converse hazard: a LATER rule can also re-split the image group.
- **Should carry it:** `renovate.json`, the clang-p2996 rule's `description`. **Sentence to append:**
  > Keep this rule LAST in packageRules: later rules win, so add any new rule ABOVE it
  > (tests/test_p2996_single_literal.py::test_clang_package_rule_leaves_the_image_group_after_it).

### M10. Tests that hardcode a tool pin break every Renovate PR that moves it

- **Evidence:** cold review S29-00 F2 (`cold-review-s29-00-2026-10-01.md:22,182`): `tests/test_image_smoke.py:802,813`
  hardcoded `python 3.14.7` and `:814` `hk 2.3.0`, so #1449's hk 2.4.0 bump would fail pytest even after the regroup.
  The coordinator's design and the dry-run proof missed it; only the reviewer's arm (edit shared.toml in a scratch
  worktree) found it. Fixed in `1b0f1338` (tests read shared.toml).
- **Where the fact lives now:** ONLY in the cold-reviewer's machine-local agent memory,
  `.claude/agent-memory-local/cold-reviewer/renovate_and_pin_literal_review.md:106-108` ("Pins hardcoded in tests break
  EVERY Renovate PR … `git grep '<old version>'` outside locks finds them"). That file is gitignored and is read only by
  the reviewer — the implementer/coordinator who writes the test never sees it. Same pattern holds for
  `mise_deps_auto_review.md` (M6) and `gitleaks_allowlist_review.md` (the global+paths trap): the lesson reaches the
  reviewer's memory and stops there.
- **Should carry it:** `tests/AGENTS.md` (read by whoever writes a test). **Line to add:**
  > Never assert a tool version literal: read it from `.config/mise/conf.d/shared.toml` (or the file that pins it). A
  > literal turns every Renovate bump of that tool red; before shipping a pin change run
  > `git grep -n '<old-version>' -- tests/` (S29-00 F2: `test_image_smoke.py` hardcoded python 3.14.7 / hk 2.3.0).

### M11. Unquoted `echo ======` separator: 10 guard denials in one session, one per context

- **Evidence:** PreToolUse deny "Quote the separator. zsh `=`-expands…" fired once in the main session (`13:21:05Z`,
  flat.txt:623) and once in each of 8 delegate transcripts (`agent-abdad20…` cold review 00:36Z,
  `agent-ab5f2b01…` 13:23Z, `agent-araw-mirror-scan-implementer…` 13:57Z, `agent-a2601a48…` 14:33Z,
  `agent-ab650702…` 15:59Z, `agent-amods-fable-synth…` 19:22Z, `agent-a95cb666…` vagueness audit 20:02Z, and this audit
  `agent-a53806340…` 20:02Z), plus one more unattributed continuation line. Each context hits it exactly ONCE, then
  complies — the signature of a fact delivered only by failure.
- **Cost:** ~10 round-trips. The guard (#1388) works; retrieval does not.
- **Currently carried:** `.claude/rules/mise-tasks-only.md` table row and memory `feedback_zsh_equals_expansion.md` —
  both present, both evidently not consulted when composing a multi-file `cat` probe.
- **Should carry it:** the `SubagentStart` injected contract, `python/src/dotfiles_setup/hook_selfcheck.py:530`
  (every delegate reads it before its first command; the main session would need the same line in
  `.claude/CLAUDE.md`). **Line to add:**
  > - The Bash tool runs zsh: quote any separator that starts with `=` (`echo '===='`); capture `r=$?` before any
  >   `$(...)`; `${!v}` does not exist (use `printenv "$v"`).

  (This one line also delivers M1 and M5 at the moment they bite.)

### M12. (Found by this audit's own probe) the Bash tool's `grep` is a shell function that SILENTLY returns nothing on text containing escape sequences

- **Evidence:** `type grep` → "grep is a shell function from ~/.claude/shell-snapshots/snapshot-zsh-….sh" (ugrep).
  On my 1.5 MB flattened subagent dump (`file`: "UTF-8 text … with escape sequences") `grep -c RESULT` printed
  NOTHING and returned rc=1; `grep -a -c RESULT` → 1043, `/usr/bin/grep -a -c` → 1043. My first three subagent
  searches returned "no hits" through this blind probe and had to be re-run. Memory
  `project_session_2026-09-08d.md:109` records only the sibling ugrep failure ("exceeds complexity limits" on
  multi-byte characters).
- **Why it matters for every session:** CI logs, `gh run view --log` output and transcripts all carry ANSI escapes;
  a `grep -c` / `grep -q` probe over them is a can-only-say-absent probe.
- **Should carry it:** `.claude/rules/probes-need-a-control-arm.md` rule 3 (bounds), after "a TOKEN SPELLING".
  **Line to add:**
  > **The `grep` itself**: in the Bash tool `grep` is the harness's ugrep shell function, which treats a file with ANSI
  > escapes as binary and prints NOTHING (rc=1) — not even a `-c` count. Use `grep -a` or `/usr/bin/grep -a` on logs
  > and transcripts (measured 2026-10-01: blank vs 1043).

## Examined and NOT counted as retrieval misses

| Item | Why excluded |
|---|---|
| gitleaks: a GLOBAL `[[allowlists]]` with `paths` blinds the path even with `condition="AND"`+`regexes` (`13:25:23Z`, two-arm scratch probe) | Genuinely new — no file held it before. Now carried at `.gitleaks.toml:86-91` with a planted-token test (`tests/test_gitleaks_raw_mirror_allowlist.py`). Correct disposition already applied. |
| `mise ls-remote … ; gh api …python-build-standalone…` → `HTTP 504` (`15:33:22Z`) | Transient upstream error, not knowledge. |
| Python 3.14.8 present on the host while PBS has no build (`16:25Z`, after Ray's note) | Re-derived in 1 call: mise compiled it from source (global config is not lock-checked). Already stated in the S29-00 research report; cheap. |
| 3 `ask_quality` denials (`19:01:39Z` no `(Recommended)`; `19:07:39Z` no `PRO:/CON:`; `19:33:18Z` no citation) | The standard is eager and the hook delivered it; these are compliance repeats (repeat-offenders lane), not missing knowledge. |
| "The plan's 09-29 recipe is stale" (S29-00, `15:34:16Z`) | Handoff/plan staleness — vagueness/staleness lane, not a retrieval gap. |
| Ray's "where are the saved-search/self-improvement phases?" (`19:46:48Z`) | Answered from the workflow source in 1 call; the features are unbuilt, not unretrieved. |

## Summary — one file per miss

| # | Fact | Cost in session | The ONE file | Carried today? |
|---|---|---|---|---|
| M1 | `$?` after `$(...)` in one `echo` is the substitution's rc | 1 meaningless rc column + re-run | `.claude/rules/long-running-command-hangs.md` rule 3 | No |
| M2 | `betterleaks dir` honours `.gitignore` (gitleaks does not) | 1 blind 0-byte scan + scratch rebuild | `.gitleaks.toml` header | No (header states only the gitleaks half) |
| M3 | bare `mise exec` from a scratch dir has no version → use `mise -C <repo> exec` | 1 failed run + diagnosis | `.claude/rules/long-running-command-hangs.md` rule 3 | No |
| M4 | step-00 CC corpus is stale and the rule names the superseded mirror; code.claude.com serves `<url>.md` + `/docs/llms.txt`; sitemap omits pages | ~6 probes + 2 ask rounds | `.claude/rules/research-doc-sources.md` step 00 | No — 98 tracked files cite the retired path |
| M5 | `${!v}` is bash-only; zsh → `bad substitution` | 1 failed call | `.claude/rules/secrets-out-of-the-shell-env.md` rule 7 | Half |
| M6 | `[deps.uv] auto` + isolated `MISE_STATE_DIR` ⇒ always stale ⇒ `--no-deps` | 7 diagnosis calls | `mise.toml` above `[deps.uv]` | Only in `fnhook_gates.py:435` + reviewer-local memory |
| M7 | `gh api …/jobs/<id>/logs` refuses ANSI; use `gh run view --job <id> --log-failed` | 2 calls | `.claude/rules/gh-cli-watch.md` canonical patterns | No (0 hits, control 1) |
| M8 | Ray's settled rulings: local OTel (Q22), dotfiles owns `~/.config/mise/config.toml` (§5b/Q23, #1014–#1018, #431) | a wasted ask round; operator restated "i've asked for this repeatedly" | `.claude/rules/clarify-before-acting.md` rule 4 | Rulings yes (`task_plan.md:1960-2114`); the search-before-ask step no |
| M9 | clang-p2996 packageRule must stay LAST | 1 full pytest (~3 min) | `renovate.json` clang rule `description` | Only in the test |
| M10 | tests must read pins from shared.toml, never literals | caught only by cold review F2 | `tests/AGENTS.md` | Only in reviewer-local memory |
| M11 | zsh `=`-expansion: quote `echo '===='` | ~10 guard denials, one per context | `hook_selfcheck.py:530` SubagentStart contract (+ `.claude/CLAUDE.md` for main) | Rule table + memory; not delivered |
| M12 | Bash-tool `grep` (ugrep fn) prints nothing on ANSI text; use `grep -a` | 3 blind searches in THIS audit | `.claude/rules/probes-need-a-control-arm.md` rule 3 | No |

**Cross-cutting pattern (M6, M10, gitleaks trap):** three of this session's lessons were captured in
`.claude/agent-memory-local/cold-reviewer/*.md` — gitignored, machine-local, and read only by the reviewer. The
implementer and coordinator who repeat the mistake never load that memory. A reviewer lesson that names an
implementer-side defect needs promoting to the implementer-facing file (the table's column 4) in the same round.

**Method note / control arms run by this audit:** M1 armed in zsh and bash (`rc=0` vs `rc=1`); M2/M7/M9/M12 negative
greps each paired with a positive control in the same corpus (stated inline); M4 freshness measured on both mirrors'
changelog heads (2.1.257 vs 2.1.273 vs running 2.1.287). Per the brief this lane wrote only this file (no
`findings.md`/`progress.md` append) — the coordinator should persist the condensed rows.

Status: COMPLETE.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — session transcript, rules, tests, `renovate.json`, `.gitleaks.toml`, task_plan, reviewer memory read.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `currency.toml:1125-1165` (mirror supersession), `sources/*.manifest`, offline CC corpora freshness.
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs) — vendored in KB `sources/`; README + `scripts/fetch_claude_docs.py` (sitemap → `.md` fetch surface).
- [thevibeworks/claude-code-docs](https://github.com/thevibeworks/claude-code-docs) — vendored in KB `sources/claude-code-docs`; changelog head measured (2.1.257).
