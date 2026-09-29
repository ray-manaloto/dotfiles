# Session audit — Brief M, second 2026-09-28 session (`cc5eebbf-2629-4ae9-a9ee-f6d38df8c8c0`)

Auditor: session-handoff §1c Brief M lane. Coordinator ruling: this session's reports use the `b` suffix; the
same-named un-suffixed file is the FIRST 2026-09-28 session's audit (`fdd9ef53`/#1419) and is untouched. Status: COMPLETE (written incrementally; final 2026-09-28).

Auditor self-incident (recorded, fixed): this lane's first write used `cat >` and truncated the prior session's
323-line tracked audit; restored byte-for-byte from `git show HEAD:<path>` before any other step (`git status` clean
for the file afterwards except this append). Same class as the 2026-09-09 lane truncating the shared findings files.

## Method

- Parse main transcript + all subagent transcripts for `is_error` tool_results, non-zero `rc=`, WARN/DRIFT/FAIL
  lines, guard denials; then cross-check against `task_plan.md`, `progress.md`, `findings.md`, commits
  `fdd9ef53..HEAD`, and issues #1422 #1425 #1432 #1434 #1435.

## Findings (RECORDED-in-plan or DISMISSED/unrecorded only)

Ordinals are JSONL line numbers. `main:Lnnn` is the main transcript `cc5eebbf-….jsonl`, and `<agent-id>:Lnnn` is
`subagents/<agent-id>.jsonl`. The probe scripts live in the session scratchpad: `ext.py` pulls every `is_error` or
`rc=[1-9]` tool_result, and `cmds.py` greps tool_use inputs. `ext.py` found 50 hits in main and 51 across the ten
non-§1c subagents. Most of them are deliberate mutation or fail arms (e.g. `main:L269`, `L482`, `L1047`, `L1965`,
`L2469`), each followed by a restore and a green re-run. Those are not errors, and they are excluded below.

### Items that were FIXED in-session (not findings; listed so the walk is auditable)

| Signal | Evidence | Fix |
|---|---|---|
| zsh `=====` aborted `session-state; handoff-check` at resume (S27-14's 6th recurrence) | `main:L76` `(eval):1: ===== not found` | #1421 `zsh_equals_separator`. Later catches by the guard itself: `main:L2360`, `agent-a9979cd0d4e3396c2:L102`, workflow `agent-aab09cc52931a6ccc:L50` — each cost one turn and nothing more |
| `land -- 1421` rc=1: main promote STALE | `.agent/logs/land-1421.log:3169` | #1422 filed and fixed by #1423 (see F4 for the part left owed) |
| lint rc=1 (ruff E501/format) | `main:L362`, `L374` | fixed before commit; `ship-1422.log` rc=0 |
| ty `invalid-argument-type` in tests | `main:L1311`, `L1318`; the edit assert fired at `L1325` (3 hits, not 2) | fixed; #1423 landed rc=0 |
| graphify hook probe rc=126 | `main:L1972` | diagnosed as a probe defect (`0644` script, registered via `bash`); re-armed through the registered form at `L1982` rc=0 |
| arm64 verify-local rc=125 (`:dev` lacked linux/arm64) | `main:L2366` | #1429: sync now treats a missing platform as stale; arm64 + amd64 verify-local rc=0 |
| `typos` "unparseable" + `no_platform_literals` in a docstring | `main:L2767`, `L2777` | `L2789` typos rc=0, 135 passed |
| `sync --check` OUTDATED on both arches after land | `main:L2482`, `L2826` | filed #1432 and recorded at `task_plan.md:106` |
| cold-reviewer pytest rc=4 (paths carried a `47453338:` prefix) | `agent-a1371df559edd2e71:L401` | re-run with bare paths at `L408`, 471 passed |
| Write to `docs/specs/…` on `main` denied by `branch_guard` | `main:L3557` | branched at `L3572`. The guard worked (do-not #9 layer 1). The parallel `sdlc-team` dispatch failed closed with `spec_missing` (`L3566`) and was re-dispatched at `L3592` |
| antigravity-delegate 1,789 > 1,536 description cap | SessionStart `main:L7` | RECORDED `task_plan.md:728` (M-3, needs /grilling). Unchanged; no new finding |
| doppler currency stale since 2026-08-12; graphify upstream never recorded; `graphifyy` no exact pin | `main:L7` | RECORDED `task_plan.md:728-731` (M-3). Unchanged |

### Summary of findings

| # | Sev | Class | One line | Disposition |
|---|---|---|---|---|
| F1 | MED | recorded (S28-4), recurred, grew | graph `stale` all session: 69 → 110 → 134 changed files; main ran 0 `graphify-health`/`-query`/`-rebuild` | FIX-NOW `mise run graphify-rebuild`; PLAN: refresh the S28-4 numbers |
| F2 | MED | DISMISSED | the zsh NOMATCH half of #1388 was declared "no static signal, not built" and recurred ≥5× in non-audit subagents | PLAN, 1 /grilling Q |
| F3 | MED | recorded (item 26), recurred | codex-schema stale all session (0.157.1 vs 0.158.0) while #1426 edited six `.codex/agents/*.toml` | FIX-NOW `mise run codex-schema-generate`; PLAN: item 26 text |
| F4 | LOW-MED | recorded ONLY in gitignored progress.md | #1423's real CI arm (`already_current` on a behind-merge) is owed; #1422 is CLOSED; neither later promote took that branch | PLAN (task_plan line + #1422 comment) |
| F5 | LOW | DISMISSED/unrecorded | the in-image mise is 2026.9.8 while 2026.9.16 exists; WARN in 4 ship/land logs; Renovate #1131 autoclosed and has no successor | PLAN (+ `renovate-dryrun`, pairs with S27-17) |
| F6 | LOW | recorded (S28-3), recurred ×10 | gates hand-batched 10 times; one batch invented `mise run hook-selfcheck` and wasted a full gate cycle | PLAN: append to S28-3 |
| F7 | LOW | unrecorded | a failed `git checkout -b` joined with `;` let `cp`/`sed -i` write a repo file on `main`; `branch_guard` does not see Bash writes | PLAN |
| F8 | LOW | recorded (S27-2 item 5), number stale | graphify PATH is now 0.9.71; the plan says 0.9.70 | PLAN: refresh text |
| F9 | LOW | recorded (#1432), measurement missing | 4 of 5 lands this session rebuilt the container (`WARN rebuilding`) | PLAN: append to `task_plan.md:106` / #1432 |
| F10 | LOW | filed but not in task_plan | #1434 and #1435 (p2996 pin divergence; #1063 frozen) have no task_plan line; progress.md:1448 only | PLAN |
| F11 | LOW | unrecorded probe result | the vendored codex schema accepts any non-empty `model_reasoning_effort`; the cold reviewer's control arm showed it and left it out of its report | PLAN (fold into #1425's validator note) |

### F1 — MEDIUM — graph stale all session and never consulted (RECORDED S28-4, recurred and grew)

- Evidence: SessionStart carried S28-4 (`task_plan.md:1134`: stale at `bed7cbb2`, 69 files; run `graphify-rebuild`
  before graph-dependent work). The cold reviewer measured `graphify-health` rc=3, stale, **110** files at `47453338`
  (`agent-a1371df559edd2e71:L80`). This lane measured it again at HEAD `3ba79a67`: rc=3, stale, **134** corpus files
  (`graphify-health: stale (runtime=0.9.65) graph built at 9f5bd67a …`).
- Main transcript: `cmds.py` over main for `graphify-(query|rebuild|health|check|upgrade|update)` → 0 invocations of
  any of them. Control arm: the same probe finds the `graphify-hook-guard.sh` calls at `main:L1971`/`L1982` and the
  item-2 edits to `graphify.py` at `L1926`, so it discriminates. The session changed graphify's own hook nudge (#1427)
  without consulting or refreshing the graph.
- Disposition: **FIX-NOW** `mise run graphify-rebuild` (graphify-out/ is gitignored, so this is a local operation and
  needs no PR; bound it, `run_in_background`, file rc). **PLAN**: change S28-4 to "stale at `3ba79a67` (134 files,
  2026-09-28b); rebuild at session start" — or, if it recurs a third time, promote it to a SessionStart doctor check
  that reports `graphify-health` != fresh (the doctor currently reports graphify PATH drift but not graph staleness).

### F2 — MEDIUM — zsh NOMATCH (unmatched glob) half of #1388: dismissed as unbuildable, recurred ≥5×

- Evidence (real `(eval):1: no matches found`, non-audit agents, all after the `=` half shipped at `main:L1420`):
  `agent-a9979cd0d4e3396c2:L98` (`ls -d ~/…/*arm64*` aborted the rest of an inspection batch), `:L314`
  (`--include=*.md` unquoted); `/code-review` forks `agent-ab96f6b080de9a68b:L34` (`ship*.py`), `:L39`
  (`pr_workflow*.py`); `agent-af4ef1a0abde27268:L35` (`.config/mise/*.toml`). The §1c audit lanes hit it several more
  times (e.g. `agent-ab23499a5c2e991b7:L74,77,81`). Those are excluded from the count because their transcripts also
  quote the string.
- Control arm: the regex `no matches found` finds every one of these, and each was hand-read to confirm a real
  abort rather than quoted text. The `Quote the separator` regex found the three real `=` denies above, so the
  probe tells the two traps apart.
- Why it counts as dismissed: `main:L1420`'s #1388 comment and `task_plan.md:1109` say "unmatched-glob half NOT built
  (no static signal)", and no plan item carries it further. The premise is wrong. The PreToolUse payload carries `cwd`
  (`$CC/hooks.md:783`; `branch_guard.py:82-148` already runs git against a cwd), so the hook can expand each
  UNQUOTED glob word with Python `glob.glob` relative to `cwd` before the command runs. That is the same filesystem
  zsh will see a millisecond later.
- Disposition: **PLAN, one /grilling question, then build in #1388** (no /to-spec needed; it is one rule plus tests).
  Proposed task_plan text under S27-14:
  `- (S28b-2) #1388 glob half: the "no static signal" premise is false — PreToolUse has cwd. /grilling: (a) hook_guard
  expands each unquoted glob word via glob.glob(cwd) and denies on zero matches (suggest quoting or zsh (N)) [recommend];
  (b) user-level setopt NO_NOMATCH (Ray preferred the guard for =); (c) accept. Recurred ≥5× on 2026-09-28b
  (a9979:L98,L314; ab96f:L34,L39; af4ef:L35).`
  Arms for (a): `ls nonexist*` → deny; `ls python/*.toml`, which matches → allow; `echo '*.x'` → allow.

### F3 — MEDIUM — codex-schema stale all session while codex agent TOMLs were edited (RECORDED item 26, recurred)

- Evidence: SessionStart `main:L7` `DRIFT doctor[codex-schema]: … generated by codex 0.157.1, but codex 0.158.0 is
  installed`. `main:L3442` confirms `codex-cli 0.158.0`. This lane re-ran `mise run doctor` (rc=0, 5 findings) and
  the same codex-schema DRIFT is still present. The `cmds.py` probe for `codex-schema-generate` in main finds 0
  invocations; control: the same probe finds `graphify-hook-guard` calls. #1426 (`89b9e823`) edited six
  `.codex/agents/*.toml` (`cold-review-prompt-audit-C-2026-09-28.md:21`). The `codex-schema` skill says to run the
  schema check BEFORE editing any agent TOML, because codex drops an invalid agent file silently.
- Recorded: `task_plan.md:933` (item 26: every codex auto-update produces this DRIFT; the regen belongs in #571's
  harness-currency loop). Its text still cites 0.157.0→0.157.1.
- Disposition: **FIX-NOW** `mise run codex-schema-generate` (machine-local, gitignored output; then
  `mise run codex-schema-check` rc=0 as the arm). **PLAN**: append to item 26:
  `RECURRED 2026-09-28b (0.157.1→0.158.0, stale all session while #1426 edited six .codex/agents TOMLs).`

### F4 — LOW-MEDIUM — #1423's real CI arm is owed, and only gitignored progress.md says so

- Evidence: `progress.md:1446` reads "#1422 fixed via #1423 (land rc=0; promote skipped on its own merge — CI arm
  pending next behind-merge)". #1422 is CLOSED (`gh issue view 1422` → CLOSED). `grep -nE '1422|1423' task_plan.md`
  → 0 lines. Control: the same grep finds `#1432` at `:106` and `#1425` at `:831`.
- Neither later main promote exercised the new branch. Run 36496528510 (#1429) printed
  `amd64: … == …:dev-8b80682b78fb6dc2 … — current` and `arm64: … — current`, which is the normal path, not
  `already_current`. Run 36482940030 (#1427) was also `promote=success`, with no stale candidate.
- Disposition: **PLAN**: add under the remainder:
  `- (S28b-4) #1423 (#1422) CI arm owed: the first main promote after a PR merges BEHIND an image-input commit must
  print status=already_current and exit 0 (not STALE). Check it in that run's promote log; if it fails, reopen #1422.`
  Also post the same sentence as a #1422 comment, so the owed arm is visible outside a gitignored file.

### F5 — LOW — in-image mise is 2026.9.8 while 2026.9.16 exists; the WARN repeats in every rebuild and is unrecorded

- Evidence: `.agent/logs/land-1423.log:10076` shows `new mise version 2026.9.16 available, currently on 2026.9.8`
  (the in-container `mise doctor`). `mise WARN  mise version 2026.9.16 available` appears twice in each of
  `ship-1422.log`, `land-1423.log`, `ship-phaseC.log` and `land-phaseC.log`. `.devcontainer/Dockerfile:115`
  `ARG MISE_VERSION=2026.9.8` has a Renovate custom manager (`renovate.json:167-174`). Renovate PR #1131
  (→2026.9.12) was **autoclosed 2026-09-23** and has no successor. #1063's grouped table does not list jdx/mise.
- Control: `grep -nE '2026\.9\.8|MISE_VERSION' task_plan.md` → only `:2068`, an unrelated table. The same grep finds
  `2026.9.14` at `:949`/`:1046`, so the probe can see version strings. The image mise matters to N-F3
  (`task_plan.md:1046`), which waits for a mise newer than 2026.9.14 that carries jdx/mise#13674.
- Disposition: **PLAN**, fold into S27-17's `mise run renovate-dryrun`:
  `read what Renovate extracts for jdx/mise (Dockerfile ARG MISE_VERSION=2026.9.8; #1131 autoclosed 09-23, no successor;
  host runs 2026.9.16) and why no PR exists.`

### F6 — LOW — S28-3 (stop hand-batching gates) recurred ×10; one batch called a task that does not exist

- Evidence: 10 hand-written `lint;pytest;verify[;selfcheck]` chains in main (`L299, L519, L613, L1073, L1559,
  L1763, L1989, L2577, L2796, L3500`). The interim rule (an aggregate exit) was followed, which is good. But
  `L1989` invoked `mise run hook-selfcheck`, and `L2015` got `mise ERROR no task hook-selfcheck found` after a full
  ~6 min lint+pytest+verify cycle. The real entry point is `uv run --project python dotfiles-setup hook selfcheck`,
  used at `L2796`. Every batch also repeated the gate matrix that `mise run ship` then ran again
  (`pr.py:325-357`, per `findings.md:1222`).
- Recorded: `task_plan.md:1131` (S28-3). **PLAN**: append
  `RECURRED ×10 on 2026-09-28b; one batch invented 'mise run hook-selfcheck' (main:L2015) — the task would remove the
  argv the model has to remember.`

### F7 — LOW — a failed `git checkout -b` chained with `;` wrote a repo file on `main` (unrecorded)

- Evidence: `main:L1426` ran `git status --short && git checkout -q -b fix/prompt-audit-c-agents && … | tail -1; cp
  …/spec-prompt-audit-C-apply.md docs/specs/prompt-audit-C-apply.md && sed -i '' … docs/specs/…`. `L1429` shows
  checkout `fatal: Unable to create '.git/index.lock': File exists.`, yet `sed` output ran, so the spec was written
  and edited on `main`. `L1441` states "my `cp` then ran on `main`". `branch_guard` covers only
  Edit/Write/NotebookEdit (do-not #9), so a Bash write is invisible to it. The lock holder went unattributed:
  `L1442` probed after the lock had already gone ("the condition has passed").
- Harm: none. The file was untracked and carried onto the branch (`L1451`). The mistake shape is `;` after a
  `&&`-guarded branch step, which is the same "a separator hides a failed step" class as #1388.
- Disposition: **PLAN** (no /grilling needed):
  `- (S28b-7) hook_guard rule: deny a command where 'git checkout -b'/'git switch -c' is followed later by ';' (not
  '&&') — a failed branch step must stop the writes after it. Arms: 'git checkout -b x; cp a b' deny; 'git checkout -b
  x && cp a b' allow.`

### F8 — LOW — graphify PATH drift keeps rising; the plan's number is stale (RECORDED S27-2 item 5)

- Evidence: `main:L7` and this lane's `mise run doctor` both report
  `path-binary …/pipx-graphifyy/0.9.71/bin/graphify reports 0.9.71 != locked 0.9.65`. `task_plan.md:1070` still says
  0.9.70, and it records the user pin rising 0.9.68→0.9.69→0.9.70 in three days. It is now 0.9.71, the fourth
  bump in four days.
- Disposition: **PLAN**: change `:1070`'s "0.9.70" to "0.9.71 (2026-09-28b)". The existing Ray-owned decision
  (raise the lock via `graphify-upgrade`, or find what bumps the user pin) stands. The daily rise favours raising
  the lock, and pairs with F1's rebuild.

### F9 — LOW — #1432's cost is unmeasured in the record: docs-only lands rebuilt the container

- Evidence: `WARN  rebuilding: in-container sessions will be killed` appears in `land-1423.log:15015`,
  `land-itemC.log:4897`, `land-phaseC.log:15689` and `land-docs.log:4927`. `land-itemC` (#1426, agent prose only) and
  `land-docs` (#1433) merged commits that got no `CI` run on main: `gh run list --commit` for `89b9e823`/`6e690e0b`
  returns only `image-analysis`, because `ci.yml:13-26`'s path filter did not trigger. So no new `:dev` was
  published, yet both logs show `container: running  [CONTAINER OUTDATED]` (`land-itemC.log:4895`,
  `land-docs.log:4925`) and a full dev-rebuild ran. Control: `land-1427.log` has 0 `WARN  rebuilding` lines, so the
  grep can return an absence.
- Recorded: #1432 and `task_plan.md:106` ("fail-safe"). Neither records that the fail-safe costs a rebuild on every
  land, including docs-only ones.
- Disposition: **PLAN**: append to `:106`: `cost: 4/5 lands on 2026-09-28b rebuilt, incl. two with no new :dev
  (land-itemC, land-docs) — raises #1432's priority.` Post the same line as a #1432 comment.

### F10 — LOW — #1434 and #1435 are filed but have no task_plan line

- Evidence: `grep -nE '1434|1435|p2996' task_plan.md` → 0 hits for 1434/1435. `progress.md:1448` records the
  p2996 review as "in progress". Control: the same grep shape finds `#1432` at `:106`. #1434 itself names a gate
  that can only pass: "`pin_parity` never registered clang-p2996, and `hk.pkl:583` does not trigger parity on
  `docker-bake.hcl`". #1435 names a Renovate group red and frozen since 2026-09-14, which holds back hk/pixi/chezmoi/
  ubuntu digests.
- Disposition: **PLAN** (the coordinator applies it after the sdlc-team review settles):
  `- (S28b-10) #1434 (clang-p2996 12 commits behind; pin_parity blind to docker-bake.hcl) + #1435 (#1063 frozen by the
  gcc-sha-repair bot commit; red on hk@1.58.1 lock) — spec docs/specs/p2996-ref-currency-review.md; review report
  under docs/research/kb/reports/agents/; next: /grilling on the tracker design → /to-spec → /to-tickets.`

### F11 — LOW — the vendored codex agent schema accepts any `model_reasoning_effort`; the probe result went unreported

- Evidence: the cold reviewer's own control arm at `agent-a1371df559edd2e71:L412-413` printed
  `control description=int errors: 1` and `control effort=bogus errors: 0`. `schemas/codex-agent.json`
  `/definitions/ReasoningEffort` is `{"minLength": 1, "type": "string"}` ("advertised by the model"), so a typo such
  as `xhgih` validates. `codex_agent_validate.py:28` also globs only `codex-sdlc-*.toml` (6 of 29 files in
  `.codex/agents/`). The cold review's finding 6 (`cold-review-prompt-audit-C-2026-09-28.md:21`) reported the glob
  gap, and #1425 references `codex-agent-validate`. It did not report the effort result.
- Disposition: **PLAN** (fold into #1425's validator decision): `codex-agent-validate` should cover every
  `.codex/agents/*.toml` and check `model_reasoning_effort` against a closed set (the efforts the pinned models
  advertise: low|medium|high|xhigh, re-derived from `codex-schema-generate` output). Arms: a TOML with `xhgih`
  gives rc≠0; the current roster gives rc=0.

## Not findings (checked, correctly handled)

- Background-task notifications this session (`main:L362`, `L1311`, `L2015`, `L2366`, `L2767`) all reported the
  real non-zero exit; each batch ended in an aggregate exit, so no "notification lied" case occurred.
- `main:L2917` AskUserQuestion was rejected with "the user wants to clarify". That belongs to the missing-requests
  lane, not this one.
- `land-phaseC.log:5641` `mise-versions … 503 … fallback=true` was a transient upstream 503 with a working fallback,
  and land rc=0.
- `main:L1441-1449` `.git/index.lock` was transient; the harm is covered by F7.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #1056 #1063 #1131 #1388 #1422 #1425
  #1432 #1434 #1435; PR #1421 body; CI runs 36496528510 and 36482940030 (promote logs); workflow run lists for the
  session's main commits; Dependency Dashboard (#193, closed) lookup.

