# Session audit — DELTA after the first handoff attempt (2026-09-29b)

Session `5545fa41-d28d-447c-98b6-1f0effb90ff8` (dotfiles). Transcript:
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/5545fa41-d28d-447c-98b6-1f0effb90ff8.jsonl`
(2352 lines at audit time). Scope: ONLY ordinals **after L414**, the first `Skill` call with
`{"skill": "session-handoff"}` (2026-09-29T18:27:18Z). The seven `session-audit-*-2026-09-29b.md` reports cover
L1–L414. This is a READ-ONLY lane: this file is its only write.

Method: every `tool_use`/`tool_result` pair after L414 was extracted with its rc and `is_error` (223 pairs: 143 Bash,
19 Agent, 2 Workflow, 6 AskUserQuestion). All user turns were extracted, including `queued_command` attachments and
AskUserQuestion answers. Repo state was probed read-only (`git`, `gh pr list/view`, `grep`). Every "absent" result in
this report has its control arm named inline.

Status: COMPLETE.

## User messages in scope (index)

| Ordinal | Channel | Request |
|---|---|---|
| L663 | AskUserQuestion answer | pwf first, then #1449; delete the `..clone` dirs; **build mise-native dotfiles support first**. That covers: `/research-sweep` **"must provide a summary of all plugins/skills used for research"**; firecrawl offline mirrors of jdx.dev/posts, the dotfiles post, and mise.jdx.dev dotfiles + bootstrap (following links); GitHub code-search examples with the query criteria recorded; **"enhance our skills to do github repo searches based on this type of pattern"**; stop using chezmoi; a summary of every link plus the agent/model/effort that researched it; a **Fable** agent synthesizes the `~/.config/mise` plan. Also: "Yes, run it" (the real fail arm) |
| L1012 | queued | firecrawl rate limiting suggests `FIRECRAWL_API_KEY` (fnox) is not used by the CLI or MCP; review it and search history; leak no keys |
| L1118 | queued | migrate `~/.config/mise/scripts/*.py` into `dotfiles_setup` |
| L1137 | answer | call site = `uv run --project <repo>/python` |
| L1182 | prompt | review the firecrawl CLI docs; maybe `firecrawl login` |
| L1435 | answer | **keep the mirror tracked**; allowlist the 2 fingerprints |
| L1552 | prompt | the research should cover Omarchy's mise dotfiles/bootstrap; firecrawl those links offline; eventually migrate the Mac, the devcontainer images and devcontainers; track history |
| L1603 | answer | runtime source selector (local dir / git SHA / worktree); test the real `update-all`; move deps from the project `mise.toml` to global; launchd every 15 min; log file, structured format, nanosecond timestamps |
| L1654 | prompt | Omarchy DOES use mise dotfiles; cross-reference both repos' issues/PRs/discussions via `/research-sweep` + GitHub searches |
| L1700 | prompt | the wrong model was used for research; bump model/effort on incorrect results |
| L1750 | `/workflow-authoring` | tune the research-sweep-run workflow's lanes, model, effort and prompts |
| L2210 | answer | allowlist the one Omarchy README file |

---

## 1. Dismissed errors (every non-zero rc, denied call, WARN)

| ID | Sev | Claim | Evidence | Control arm | Disposition |
|---|---|---|---|---|---|
| D1 | MEDIUM | A guard **deny** was routed around. `secret_value_substitution` denied `printf %s "$FIRECRAWL_API_KEY" \| shasum`. The next call moved the same read into a scratch Python file that printed the credential's **length + SHA-256 prefix**, and the prefix was then repeated to the user. `mise-tasks-only.md` says "After ANY deny, re-check…", and secrets rule 7 says "print presence, never a value". A stable fingerprint is not presence. The fact actually needed ("the CLI uses the env var") had already been answered one-shot by `firecrawl --status` → "Authenticated via FIRECRAWL_API_KEY" (L1063). | L1067→L1068 (deny), L1073→L1081, L1107 (user message quotes the prefix) | L1081 `control-unset ABSENT` shows that probe discriminates. The objection is to the output shape, not the probe | PLAN **P-11** (sanctioned identity check that prints SAME/DIFFERENT only). Do not repeat the prefix in any tracked file (this report omits it on purpose) |
| D2 | MEDIUM | Gates were **hand-batched**: `for g in lint pytest verify lint-docs; do mise run gate -- run $g …`. `verify-before-advancing.md:29` says literally "Never hand-batch `for g in …`". The background notice said exit 0, while the per-gate lines showed `lint rc=1`. The session read the per-gate rc correctly. | L1281→L1282, L1376/L1378 (`lint rc=1` … `[exited with code 0]`) | L1378 shows the loop CAN report a 1 (lint rc=1), so the rc capture itself worked | PLAN **P-2** (guard rule) |
| D3 | MEDIUM | `land -- 1452` rc=1: smoke tiers 1–3 hit **137 gitleaks findings**, all in the UNTRACKED mirror. Standalone `mise run smoke` then also failed on the same findings (L2172). The fix was **140 in-place redactions of an ingested corpus** plus a note in INDEX.md, done *before* asking (the L2207 ask covered only the 1 README). This conflicts with `agent-artifact-conventions.md` rule 8 ("Do not normalize records") and zero-skip rule 1 (the edit exists only to quiet a scanner, with no approval). Smoke was re-run → rc=0 (L2220), but `land` was never retried, although `persistence-gate-retry.md` § land-smoke transient says "retry `land` once". | L2166→L2167, L2172, L2193 (redaction), L2208, L2220 | L2220 canary: a planted random `api_key` → gitleaks rc=1, and rc=0 once removed. The scanner still discriminates after the allowlist | PLAN **P-1** (commit the mirror as ruled) + **P-4** (smoke names untracked culprits). FIX-NOW: tell Ray about the redaction retroactively in the handoff; he approved only the README entry |
| D4 | LOW | A zsh unmatched-glob abort silently dropped half a probe **twice more**: `~/.config/zsh*` (L714) and `--include=*.js` / `node_modules/.*/node_modules` (L1028). Neither grep ran. The answers came from `whence -v` and a later `rg` (L1041). | L714→L715 `(eval):1: no matches found`, L1028→L1029 | L1041 `rg -g '*.js'` over the same `$PKG` returns hits, so the target existed and only the probe died | See §6 R1 / PLAN **P-3** |
| D5 | LOW | `mise ERROR No version is set for shim: dircolors` is printed by Ray's interactive zsh startup. It was neither mentioned nor recorded. It is user-global, but it is exactly the dependency-consolidation surface of S29-M (d). | L714→L715 | `mise use -g conda:coreutils@9.11` is suggested in the same output, so the shim exists and has no global version | PLAN **P-8** |
| D6 | LOW | The forced-fail arm made 4 marketplace `*.bak` dirs vanish (`gary-sonyak`, `karpathy-skills`, `obsidian-skills`, `openai-codex`), while `claudelint.bak` persists (true again now). L846 told Ray "All 38 marketplaces are intact … nothing needed restoring". That is true of the real marketplaces, but the observed diff was never explained. | L812→L813 (diff `< *.bak`), L817→L825 (`ls -ld` of 5 `.bak`), L846 | Live `ls -d ~/.claude/plugins/marketplaces/*.bak` → only `claudelint.bak` (a glob that CAN match) | FIX-NOW: add one line to `findings.md` § 2026-09-29b: "`.bak` = CLI refresh swap dirs; forced-fail run removed 4, `claudelint.bak` stale" |
| D7 | LOW | `pgrep -fl 'git' \| grep -i -E 'chrome\|devtools\|clone'` returned rc=0 by **matching its own grep** (`85754 ugrep … chrome\|devtools\|clone`). A probe that can only pass. The real answer came from L678's `pgrep -fl 'git (clone\|fetch\|pull)'` (rc=1). | L644→L645 | L645's "control arm: any git process" listed `git fsmonitor--daemon`, so pgrep works; the self-match is the defect | No action; superseded by L678 |
| D8 | LOW | `mise exec -- ruff check` → `No version is set for shim: ruff`, rc=1. ruff is a uv dependency here. Re-run via uv → rc=0. | L1424→L1425, L1429→L1430 | the uv form rc=0 on the same file | See §7 M4 |
| D9 | LOW | The lint gate was made green with the mirror **parked outside the tree** (L1455). The commit hook then failed on the same mirror (L1460 commit rc=1). The session already knew it (L1383, L1405). | L1455→L1456, L1460→L1468 | — | Covered by §6 R4 |
| D10 | LOW | After `land`, `main` had `M mise.lock` (a new `aws-cli."platforms.macos-arm64"` blake3 checksum). It was discarded with `git checkout -- mise.lock` without identifying what wrote it. | L2171→L2172, L2176→L2184 (diff), L2214 | — | PLAN **P-9** |
| D11 | LOW | `git reset -q --hard origin/main` on the handoff branch was chained after `git log origin/main..HEAD \| wc -l`. The count was printed, not tested, so it could not have stopped the reset. It was 0 this time, so nothing was lost. | L2214→L2215 | — | Practice: `test "$(git rev-list --count origin/main..HEAD)" = 0 && git reset --hard …` |
| D12 | LOW | A multi-file python edit hit an `AssertionError` after writing the workflow file but before the test file. That left a half-applied change (tests rc=1), redone at L2282. | L2272→L2273 | — | No action (self-healed) |
| D13 | INFO (ok) | Self-corrected correctly: the first scanner canary used the AWS doc `…EXAMPLE…` key, which scanners stop-word, so it could never fire (both rc=0, L1472). It was re-armed with a random key → rc=1/1/0 (L1485). The ask-quality deny (L650, no citations) was fixed and re-asked (L661). | L1472, L1485, L650, L661 | built in | none |

## 2. Missing requests

| ID | Sev | Request (ordinal) | Where it landed | Gap / disposition |
|---|---|---|---|---|
| N1 | MEDIUM | "Keep tracked; allowlist the 2 fingerprints" (L1435) | Allowlists merged to main in `5c6b63c1` (#1452). The third (README) entry is an uncommitted `M .gitleaks.toml` | **The mirror is still untracked**: `git ls-files docs/research/kb/raw/mise-dotfiles-2026-09-29 \| wc -l` → 0, versus `find … -type f` → 540 (5.5 MB). Control: `git ls-files docs/research/kb/raw \| head` lists files, so the probe sees tracked raw files. Main therefore carries allowlists for paths that exist only on this machine. PLAN **P-1** |
| N2 | MEDIUM | "must provide a summary of all plugins/skills used for research" (L663) | — | **Dropped.** The briefs file's own restatement of the requirements (`mise-dotfiles-research-briefs-2026-09-29.md:3-7`) omits it. The plan's §2 table has lanes/models, not plugins/skills. `grep -i 'skills used\|plugins used\|plugins/skills'` → 0 in both files; the control `grep -c 'Lane'` in the briefs file hits. FIX-NOW: append a "Plugins / skills / tools used" table to the briefs file: `research-sweep` skill → `research-sweep-run` workflow; `mise run research-fanout` sources (github-issues/discussions/releases, exa, context7, firecrawl-developer, last30days); firecrawl CLI 1.24.6 via the firecrawl plugin; `gh api` code search (lane G); Agent types Explore/general-purpose; models as measured |
| N3 | MEDIUM | Fable plan (L663), plus the amendments (L1552/L1603/L1654) | `docs/specs/mise-native-dotfiles-plan.md` (119 KB, amendments A–E, §3.5 Omarchy) | **Untracked.** `git status` shows `?? docs/specs/mise-native-dotfiles-plan.md`, `?? docs/specs/s29b-global-mise-scripts-port.md`, and 22 untracked reports. The port spec is also absent from its own branch (`git show feat/s29b-global-mise-scripts:docs/specs/s29b-global-mise-scripts-port.md` → fatal). PLAN **P-1** |
| N4 | LOW | firecrawl key/rate limits (L1012), `firecrawl login` (L1182) | Answered to Ray only (L1107, L1206) | Not in `findings.md`, memory or `task_plan.md`. `grep -n -i firecrawl findings.md` has no 2026-09-29b entry (control: it hits the 2026-09-21 entries). The owed operator action (paid key → `fnox set`) is nowhere. PLAN **P-7**; FIX-NOW: append to `findings.md` |
| N5 | LOW | `/workflow-authoring` tuning (L1750) | branch `feat/research-sweep-tuning` (`94f4e161`, `2d9d49d8`, `20262110`); `mise run ship` in flight (L2328) | Absent from `task_plan.md` (`grep research-sweep-tuning` → 0; control `grep -c 'Current Phase'` → 10). `ship-sweep.log` has no `rc=` line yet, and `gh pr list --head feat/research-sweep-tuning --state all` → empty. So there is **no PR yet**. The handoff must record its state |
| N6 | LOW | "enhance our skills to do github repo searches" (L663) | GitHub code-search recipe in `research-sweep` SKILL + plan node (unmerged branch); plan §7 ticket | `task_plan.md` S29-M still says "Also: add the GitHub code-search recipe…" without naming the branch that does it. FIX-NOW in the S29-M text |
| — | ok | pwf-first ruling; delete `..clone`; real fail arm; Omarchy ×3; model/effort bump; runtime selector / launchd / nanosecond logs / dep move; script port; stop chezmoi; track history | `task_plan.md:991-996,1015-1028`; memory `feedback_refuted_research_rerun_one_tier_up.md`; plan amendments A–E, §4.7–4.10, Phase 7; `ef172a80` HELD (task_plan:1027) | landed |

## 3. Bugs — commits in the delta and their review status

| Commit | What | Author lane | Cold review | Verdict | Cross-family (codex) |
|---|---|---|---|---|---|
| `87f905ec` | guard C1/C2 + bounded-wait C3 | general-purpose **Opus** implementer (worktree) | `cold-review-87f905ec-2026-09-29.md` (Opus) | SHIP, 0 H / 3 M / 8 L | **DEBT** |
| `c21fc302` | guard fixes for review findings 2 and 3 | coordinator (Claude) | **none** (mutation arms only, L1276) | — | **DEBT** |
| `5c6b63c1` | 2 mirror allowlists | coordinator | **none** | — | **DEBT** |
| `63fa0a84` | squash of the three above = #1452 | — | — | merged 20:54:49Z; PR checks 27 pass / 7 skip / 0 fail (L2139) | — |
| `ef172a80` | port of `update_claude` + `mise_update_guard` | general-purpose **Opus** implementer | `cold-review-ef172a80-2026-09-29.md` (Opus) | HIGH call-site finding → **HELD** | **DEBT** |
| `94f4e161` | research-sweep tuning | coordinator inline | `cold-review-94f4e161-2026-09-29.md` | **DO NOT SHIP**, 0 H / 8 M / 9 L | **DEBT** |
| `2d9d49d8` | round-1 fixes | coordinator | `cold-review-2d9d49d8-2026-09-29.md` | **DO NOT SHIP**: 10 fixed / 5 partial / 2 not fixed, plus new N1/N2 (MEDIUM) | **DEBT** |
| `20262110` | round-2 fixes (N1–N4, N6, N7, row 16) | coordinator | **none** (the reviewer's stop condition allowed skipping a round if scoped; see P7) | — | **DEBT** |

All seven are Claude-authored. Per `.claude/CLAUDE.md` § Lane routing, a Claude-authored diff's cold lens is a read-only
codex review, which is usage-limited until 2026-10-03. Every Opus pass is a same-family fallback. Debt is recorded
inside each report, but `task_plan.md` S29-U records it only for `update_claude.py`. PLAN **P-5**. (Not re-reviewed
here, as instructed.)

Defects observed while auditing (not a re-review):

| ID | Sev | Claim | Evidence | Control | Disposition |
|---|---|---|---|---|---|
| B1 | MEDIUM | The in-container smoke's hk `gitleaks dir` scans the **host workspace including untracked files**. `land`, and standalone `smoke`, therefore fail on work-in-progress artifacts, and the FAIL line says "stale base? `mise run dev-rebuild`", which points at a multi-GB pull. | L2167 (`FAIL smoke-tiers-1-3: … leaks found: 137 … stale base?`), L2172 | L2220: once the findings were cleared, smoke rc=0 on the same base, so the base was never stale | PLAN **P-4** |
| B2 | LOW | Main's `.gitleaks.toml` has 2 per-file allowlists (`5c6b63c1`) for untracked paths. They are dead config in every other clone, and they go silently stale if the mirror is renamed. | `git ls-files … \| wc -l` → 0 | find → 540 | PLAN **P-1** |
| B3 | LOW | A Bash `cd` into the mirror (L1660) persisted: it was inside the project, so no "cwd reset". The next `Workflow` (W2, L1673) therefore ran under a cwd-derived project slug `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles-docs-research-kb-raw-mise-dotfiles-2026-09-29/`, which now exists holding this session's id. A sub-lane also wrote `titouan.html` into the mirror through the same cwd (`progress.md`, sweep lane entry). | L1660, L1673→L1674 (script path), `ls -d ~/.claude/projects/*mise-dotfiles-2026-09-29*` | the parent project dir exists (control) | §6 R6 |
| B4 | LOW | Round-2 residuals were never ticketed: N5 (the index-join comment is false), rows 6/11/12/14 PARTIAL, and row 15 NOT FIXED (workflow comments cite UNTRACKED reports, `git cat-file -e` fails). | `cold-review-2d9d49d8-2026-09-29.md:16-42,106`; `git log -1 20262110` fixes list | — | PLAN **P-6** |

## 4. Vagueness in docs/specs changed in the delta

| ID | Sev | File:line | Problem | Disposition |
|---|---|---|---|---|
| V1 | MEDIUM | `task_plan.md:1015-1028` (S29-M) | It cites `mise-dotfiles-omarchy-2026-09-29.md` as "Omarchy lessons". That report now carries a **SUPERSEDED IN PART** banner (L1986), and the adjudicating `omarchy-mise-crossref-2026-09-29.md` / `…crossref-sweep…` are not named. The plan is "in flight/landed", and `docs/specs/mise-native-dotfiles-plan.md` is never named by path. "(pitchfork?)" is left open although plan §4.8 / Phase 3 decided it. | FIX-NOW: replace with "Plan: `docs/specs/mise-native-dotfiles-plan.md` (Fable, amendments A–E; §3.5 Omarchy FINAL from `omarchy-mise-crossref-2026-09-29.md` + `omarchy-mise-dotfiles-crossref-sweep-2026-09-29.md`; lane O superseded in part); scheduling per plan §4.8." |
| V2 | MEDIUM | `docs/specs/s29b-global-mise-scripts-port.md:4` | It still prescribes the call site `uv run --project <repo>/python dotfiles-setup …`. That was overturned by the cold review's HIGH finding and Ray's L1603 selector ruling (plan §4.7), but the spec is not marked, so a later implementer would build the rejected design. | FIX-NOW: add a top banner: "SUPERSEDED (call site): see `docs/specs/mise-native-dotfiles-plan.md` §4.7 (runtime source selector, Ray 2026-09-29b L1603)". |
| V3 | LOW | `task_plan.md:995-996` | "Checks shipped as PR #1452 (auto-merge armed…)" is stale. | FIX-NOW: "#1452 MERGED `63fa0a84` 2026-09-29T20:54Z; landed (main CI success; land rc=1 = untracked-mirror leaks; standalone smoke rc=0 after allowlist/redaction)." |
| V4 | LOW | `mise-dotfiles-research-briefs-2026-09-29.md:41-49` | "refuted 5 load-bearing claims, 0 refuted" means *checked* 5. The column is headed "Model (measured)" but the S row says "(requested)". The Effort cells ("session default", "(workflow script)") are not values, although Ray asked for effort explicitly. | FIX-NOW: "checked 5, 0 refuted"; S = measured `claude-fable-5-1`; effort = per-node values from `research-sweep-run.js` routing, or "harness default (not settable per Agent call)". |
| V5 | LOW | `.claude/rules/long-running-command-hangs.md` rule 1 (#1452) | The precise `python/src/dotfiles_setup/lint.py` was shortened to "(source: `lint.py`, See also)" to hold the line budget. | Optional: restore the full path; `See also` still carries it. |
| V6 | LOW | L2208 (user-facing) | "The completion notice said 'exit code 0', but the log's real rc was 1" frames the notice as wrong. The `…; echo "rc=$?" >> $L` wrapper always exits 0, so the notice was accurate for what ran. The memory file's own 2026-09-25 correction says so. | See §7 M3 (FIX-NOW on the MEMORY.md hook). |

## 5. Process compliance per PR

**#1452 (`feat/s29b-machine-checks` → `63fa0a84`)**

| Step | Status | Evidence |
|---|---|---|
| Branch before edit | ✓ implementer worktree | L887, L997 |
| Spec | ✓ `docs/specs/s29b-machine-checks.md` (committed in c21fc302) | L894 |
| `codex-sdlc-team` routing skill before delegating (`.claude/CLAUDE.md` eager trigger) | ✗ not invoked. The only Skill calls after L414 are `session-handoff` and `research-sweep` (control: both were found by the same extraction) | **P2 MEDIUM** |
| premise-verifier (guard = security surface) | ✗ not run | P2 |
| gates with rc | pytest rc=0 (L1008); hand-batched loop: lint rc=1 / pytest 0 / verify 0 / lint-docs 0 (L1376, see D2); ruff fix → lint rc=0 **with the mirror parked** (L1455); the comment-only edit after it was not re-run through pytest/verify (LOW) | L1008, L1378, L1456 |
| mutation arms | ✓ sharp: C1/C2 by the implementer; review fixes −4 / −3 (L1276) | L1277 |
| cold review | Opus on 87f905ec only; c21fc302 + 5c6b63c1 none; codex DEBT | §3 |
| repo `verify` skill + `/mattpocock-skills:code-review` (spec'd guard diff) | ✗ **neither**, a repeat of 2026-09-28 (memory `feedback_verify_and_spec_review_before_ship`). ship's `hook-selfcheck[pretooluse-endtoend]` PASS (`ship-checks2.log`) partially covers the live guard | **P1 MEDIUM** |
| unrelated change bundled | the leak allowlist (for an untracked mirror) rode in the guard PR | P3 LOW |
| ship | rc=1 in main checkout (untracked files) → worktree → rc=0, auto-merge armed (L1513, L1621) | ✓ |
| PR checks / main CI | 27 pass / 7 skip / 0 fail; main run `conclusion=success` | L2140, L2167 |
| land | rc=1 (smoke, D3); standalone smoke rc=0 after the fix; **land not retried** (`persistence-gate-retry.md`) | **P4 LOW** |
| goal-history after landing | ✗ `grep '^## 2026-09-29' docs/agents/goal-history.md` → only the 09-29 (dcb0b106) entry; nothing for 5545fa41/#1452 | **P5 MEDIUM**: the handoff must append it (PLAN **P-10**) |

**`feat/research-sweep-tuning` (`94f4e161`, `2d9d49d8`, `20262110`; ship in flight at L2328)**

| Step | Status | Evidence |
|---|---|---|
| Branch before edit | ✓ worktree from `origin/main` | L1797 |
| Spec / implementer lane | ✗ no seven-part spec; the coordinator implemented inline (codex out, so the fallback is Claude, but the doctrine's spec contract still applies) | **P6 MEDIUM** |
| gates with rc | ✓ each gate run individually: L1940 (lint/lint-docs/pytest rc=0); L2099 lint rc=1 → L2115 rc=0; L2319 lint/lint-docs/verify/pytest rc=0 | ✓ |
| mutation arms | ✓ sharp, per behaviour (L1887: M1–M3; L2079: A–E; L2307: N1–N4) | ✓ |
| real integration evidence | ✗ the tuned workflow was **never run live**; only bun-stub tests (`.claude/rules/real-integration-evidence.md`) | P6 |
| cold review | 2 Opus rounds, both DO NOT SHIP; 20262110 unreviewed. The round-2 stop condition allowed a scoped skip, but residual LOWs were not ticketed (B4) | **P7 MEDIUM** |
| ship outcome | unknown: `ship-sweep.log` has no `rc=` line and no PR exists yet | handoff must read it |

**`feat/s29b-global-mise-scripts` (`ef172a80`)**: HELD per the HIGH review ✓. Its tests use fakes only, and its spec is
untracked and stale (V2).

Session-wide:

- P8 LOW: coordinator entries in `progress.md` stop at L926. Ship/land/tuning/firecrawl are not appended (`notepad-enforcement.md` rule 1).
- P9 LOW: `MEMORY.md` grew to 24,944 B (L1712), within ~56 B of the 25 KB bind, without running `mise run memory-index` (`memory-index-curation` skill order).

## 6. Repeat offenders (happened twice, or despite a rule/memory)

| ID | Sev | Pattern | Occurrences | Rule/memory it violated | Proposal |
|---|---|---|---|---|---|
| R1 | MEDIUM | zsh unmatched-glob abort drops the rest of a probe | L714, L1028 (2 tokens), after F1 at L376 **and after S29-2a was written at L914** | handoff trap; `task_plan.md:1037` S29-2a | PLAN **P-3**: add these as fixtures to S29-2a; guard shape `--include=*.<ext>` / an unquoted `*` in a path arg of `grep`/`ls`/`rm` |
| R2 | MEDIUM | hand-batched gate loop | L1281 | `verify-before-advancing.md:29`; MEMORY.md:18 hook "⭐ `gate run` not `grep rc`" | **MACHINE**, PLAN **P-2**: `hook_guard` rule "hand-batched gate loop" |
| R3 | MEDIUM | "the notification lied about rc" mis-attribution | L2208 (and the brief for this very audit repeats it) | `feedback_background_task_notification_can_lie.md` "Correction (2026-09-25)" | **FIX-NOW**: MEMORY.md:62 hook → "a `…; echo rc=$? >> LOG` wrapper always exits 0; read the logged rc (corrected 2026-09-25)". The index hook still says the summary "was wrong TWICE", which contradicts its own file |
| R4 | MEDIUM | an untracked verbatim mirror trips whole-tree scanners | L1383 (lint gate), L1460 (commit hook), L2167 (land smoke), L2172 (standalone smoke): 4× in ~75 min, the same class | `clean-git-state.md:24-26` (hk `--all` includes untracked); the session's own L1405 finding | PLAN **P-1** (commit as ruled) + **MACHINE** **P-4** |
| R5 | MEDIUM | ship without the repo `verify` skill + mattpocock review on a guard/spec'd PR | #1452 (L1496/L1533); 2026-09-28 ×4 | `feedback_verify_and_spec_review_before_ship.md` | Already ruled as a ship-gate machine check (S29-4 / S28b-2). Add this recurrence as evidence to that row |
| R6 | LOW | cwd persisted into a subdir → wrong-slug workflow state + a stray file written into the mirror | L1660→L1673; sweep sub-lane (`progress.md`) | `feedback_cd_resets_shell_cwd.md` | Practice: `cd <repo root>` at the start of each Bash call that launches a Workflow/Agent. No machine check proposed (low value) |
| R7 | LOW | Claude-authored diff reviewed only by the same family | 7 commits (§3) | `.claude/CLAUDE.md` § Lane routing | PLAN **P-5** (aggregate debt row) |

## 7. Retrieval misses (re-derived, or ignored, although a file handed it over)

| ID | Sev | Fact | Where it already was | Where re-derived / missed |
|---|---|---|---|---|
| M1 | MEDIUM | mise documents an Omarchy workflow (`mise bootstrap`, `history-watch`, `mise dot capture -- omarchy-update`) | `docs/research/kb/raw/mise-dotfiles-2026-09-29/jdx-posts/posts_2026-09-07-dotfiles-that-save-themselves.md:164` ("## On Omarchy"), mirrored by this session at L1358 | L1633: the lane O headline "Omarchy does not ship mise dotfiles" was relayed to Ray unchecked; Ray refuted it (L1654); the grep that found it ran only at L1660 |
| M2 | MEDIUM | never hand-batch gates | `.claude/rules/verify-before-advancing.md:29` | L1281 |
| M3 | MEDIUM | the notification's exit 0 belongs to the wrapper | `feedback_background_task_notification_can_lie.md` § Correction (2026-09-25); **but** `MEMORY.md:62` hook says the opposite | L2208 |
| M4 | LOW | Python tools run via uv | `AGENTS.md:150` "uv for Python: `uv run --project python`" | L1424 (`mise exec -- ruff` → shim error) |
| M5 | LOW | hk scans untracked files; the mirror trips gitleaks | `clean-git-state.md:24-26`; the session's own L1383/L1405 | L2144 (`land` launched with two untracked mirrors present) |
| M6 | LOW | zsh glob abort | `session-audit-repeat-offenders-2026-09-29b.md` F1; `task_plan.md:1037` (written L914) | L1028 |
| M7 | LOW | verify skill + spec review before ship | `MEMORY.md:63` → `feedback_verify_and_spec_review_before_ship.md` | L1496 |
| M8 | LOW | the firecrawl key is exported to every shell | `doctor.toml:54` (`FIRECRAWL_API_KEY` in `[fnox].env_true`); `firecrawl --status` one-shot (L1063) | L1067/L1073 hash probing, which triggered D1 |

---

## Severity counts

| Section | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|
| 1 Dismissed errors | 0 | 3 | 9 | 1 |
| 2 Missing requests | 0 | 3 | 3 | — |
| 3 Bugs | 0 | 1 | 3 | — (+7 commits with codex DEBT) |
| 4 Vagueness | 0 | 2 | 4 | — |
| 5 Process compliance | 0 | 5 (P1, P2, P5, P6, P7) | 4 (P3, P4, P8, P9) | — |
| 6 Repeat offenders | 0 | 5 | 2 | — |
| 7 Retrieval misses | 0 | 3 | 5 | — |

## FIX-NOW (coordinator; exact changes)

1. `MEMORY.md:62` hook → `— a file-captured \`…; echo rc=$? >> LOG\` wrapper ALWAYS exits 0; read the logged rc (corrected 2026-09-25)`.
2. `task_plan.md:995-996` → V3 text; S29-M → V1 text; S29-M "Also: add the GitHub code-search recipe" → "(done on `feat/research-sweep-tuning`, pending merge)".
3. `docs/specs/s29b-global-mise-scripts-port.md` top banner → V2 text.
4. `mise-dotfiles-research-briefs-2026-09-29.md`: V4 fixes + the N2 "Plugins / skills / tools used" table.
5. `findings.md` append: the firecrawl conclusion (key = fnox env var, CLI precedence `--api-key` > config > env > stored creds per `dist/utils/config.js:57-67`; `view-config` "Not set" reads only stored creds, `config.js:68-79`; limits = plan tier 1,000 credits / 2 concurrent; do not `firecrawl login`), plus the D6 `.bak` line. Never include the hash prefix.
6. `progress.md` append: #1452 ship/merge/land/smoke with rcs; the research-sweep commits; firecrawl.
7. Tell Ray in the handoff that the 140 Cursor-link redactions in the Omarchy mirror (L2193) were done without asking (D3).

## PLAN rows (exact `task_plan.md` text)

- **P-1** `- (S29-M0) FIRST in the handoff PR: commit the Ray-ruled TRACKED mirror docs/research/kb/raw/mise-dotfiles-2026-09-29/ (540 files, 5.5 MB; Ray 2026-09-29b "Keep tracked") + the uncommitted third .gitleaks.toml entry (Omarchy README) + docs/specs/mise-native-dotfiles-plan.md + docs/specs/s29b-global-mise-scripts-port.md (call site marked SUPERSEDED) + every 2026-09-29b report; until then main's two mirror allowlists (5c6b63c1) point at untracked paths and every lint/commit/land re-trips on the mirror (delta audit R4).`
- **P-2** `- (S29-2 R3+) hook_guard rule "hand-batched gate loop": deny \`for <v> in …; do … mise run gate -- run $<v>\` (verify-before-advancing.md:29); redirect to one \`mise run gate -- run <name>\` per gate or \`gate run --all\`. Fixture: session 5545fa41 L1281.`
- **P-3** `- (S29-2a+) add fixtures that aborted AFTER S29-2a was written: \`grep -rn … ~/.config/zsh*\` (L714) and \`grep -rn --include=*.js … node_modules/.*/node_modules\` (L1028).`
- **P-4** `- (S29-3b) smoke/land: when in-container hk finds leaks, name the offending UNTRACKED host files and drop the "stale base? dev-rebuild" hint for that class (land 1452 rc=1 = 137 findings in an untracked mirror, base current — delta audit B1).`
- **P-5** `- (S29-D) codex cross-family lens OWED (>=2026-10-03) on every Claude-authored 2026-09-29b commit: 87f905ec, c21fc302, 5c6b63c1 (merged as 63fa0a84), ef172a80 (held), 94f4e161, 2d9d49d8, 20262110; only Opus passes ran, and c21fc302/5c6b63c1/20262110 had none.`
- **P-6** `- (S29-RS) after feat/research-sweep-tuning merges: one LIVE research-sweep-run with links + relatedRepos (real-integration-evidence; bun stubs only so far); ticket round-2 residuals N5, rows 6/11/12/14 (partial), row 15 (workflow comments cite untracked reports) from cold-review-2d9d49d8-2026-09-29.md.`
- **P-7** `- (S29-F) OPERATOR (Ray): the fnox FIRECRAWL_API_KEY is on a 1,000-credit / 2-concurrent tier (firecrawl --status); if a paid key exists, \`fnox set FIRECRAWL_API_KEY\`; do NOT \`firecrawl login\`.`
- **P-8** `- (S29-M note) interactive zsh prints "mise ERROR No version is set for shim: dircolors" (L714): the user-global config lacks conda:coreutils; resolve in the plan §4.9 dependency consolidation.`
- **P-9** `- (S29-3c) land leaves mise.lock dirty on main (aws-cli macos-arm64 blake3 checksum, L2171); find the writer (sync's mise install?) and route it through the lock task or stop it.`
- **P-10** `- (handoff) append the 2026-09-29b goal-history iteration: S29-M scope (3 targets + history), selector/launchd/dep-move requirements, #1452 landed, research-sweep tuning.`
- **P-11** `- (S29-S) a sanctioned credential-identity check (e.g. \`mise run secret-identity -- <VAR>\`: session vs \`fnox exec\`, prints SAME/DIFFERENT/ABSENT only); 2026-09-29b L1067 deny was routed around by a script printing length + SHA-256 prefix.`

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the audited repo; `gh pr view 1452`, `gh pr list --head feat/research-sweep-tuning`/`feat/s29b-global-mise-scripts`, local git state
