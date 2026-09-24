# Codex CLI flag decisions: history and current-site compliance (Brief K, 2026-09-23)

Status: COMPLETE. Read-only lane. I ran no codex command and signalled no process. The only file I wrote is this report.
Scope: the flag DECISIONS history plus a compliance table for today's invocation sites. Briefs I and J cover the
call audit and the routing gap, so this report does not repeat them.

## Headline

1. **Ray ruled `--ephemeral` out twice, and neither ruling reached dotfiles' lane definitions.**
   - **2026-09-01 in knowledge-base.** The flag was removed from every pattern, and the `lane_recording` hk gate
     now enforces that.
   - **2026-09-15 in dotfiles.** Ray ruled that `sdlc_team` drops both `-s` and `--ephemeral`. That commit sits on
     a branch that never merged.
   - **2026-09-16, #1145.** This change re-derived only the `--ephemeral` half, and only for `sdlc_team`. It also
     wrote the per-lane hybrid ("drop it for any lane that delegates") into the rule. The 2026-09-01 advisor had
     rejected exactly that hybrid, with the warning that it "will drift".
   - **Today.** 12 of 12 `codex-{sol,astra}-*` agent definitions, `codex_lane.py`, and the rule's canonical argv
     block all still pass `--ephemeral`.
2. **A Ray ruling was lost in a squash.** On 2026-09-15, Ray ruled that `sdlc_team` must stop passing `-s` (session
   `4b5c48be` #546/#548). The commit was `38ed61f2`, on `docs/session-2026-09-15-preclear`, and it never got a PR.
   The next day the coordinator misreported what that branch contained (`52714f36` #799). `sdlc_team.py:747` still
   passes `-s read-only|workspace-write`.
3. **A complete `codex exec` flag audit (codex-cli 0.154.0, 27 options plus subcommands) also exists only on that
   unmerged branch**, at `codex-flag-audit-2026-09-15.md`. It adopts `--strict-config` and rejects `--ephemeral`
   for a second, independent reason: it suppresses the project `shell_environment_policy`. Main has no copy.

## Searches

AgentsView always ran with `--server http://127.0.0.1:8080 --server-token-file '<native-server-token>'` and
`--exclude-session a6750a24-…`. Embeddings are stalled, so prose searches used `--fts`. `--fts --scope top` is
rejected ("--scope requires --semantic or --hybrid", rc=1), so I dropped `--scope`.

| # | Probe | Mode | Result |
|---|---|---|---|
| p1 | `ephemeral` | fts | 20 hits. Led to the origin sessions `91a91cb9` (KB, 09-01), `4b5c48be` (09-15) and `52714f36` (09-16) |
| p2 | `danger-full-access` | fts | `8dac106f` (09-01 operator-lane decision) and `814c5c84` (09-12 implementer) |
| p3 | `reasoning effort xhigh` | fts | Effort pins across lanes. No contested ruling found |
| p4 | `full-auto` | fts | KB `999a320c` #115 (08-27 absence arm); dotfiles codex mirror `01a05e73` #429 ("unexpected argument", 0.152.0) |
| p5 | `dangerously-bypass-hook-trust` | plain, `--in tool_input,tool_result` | `f643887b` #45 (09-23): "Never `--dangerously-bypass-hook-trust` in launchers" |
| p6 | `stop overriding the machine sandbox` | plain | `4b5c48be` #599 (commit of `38ed61f`) and `52714f36` #10-14 (next-session listing) |
| p7 | `strict-config` | plain | Help-text echoes, plus `f643887b` #74/#80 (09-23 review-settings research) |
| p8 | `preclear` | fts | `4b5c48be` #419-454: the branch's gate runs and brief copies |
| p9 | `does not delegate` | fts | 0 relevant hits. No session records a deliberate decision to KEEP `--ephemeral` for non-delegating lanes |
| p10 | `drop ephemeral` | fts | `52714f36` #787-799: Ray: "I thought we dropped `--ephemeral`" |

Four message windows were read: `52714f36` #821-855 and #767-807, `91a91cb9` #320-433, `4b5c48be` #524-621, and
`8dac106f` #379-453.

Repository probes:
- `git log -S--ephemeral` on the rule, the agents, `codex_lane.py` and `sdlc_team.py`.
- `git merge-base --is-ancestor 38ed61f2 origin/main`, which returned NO.
- `gh pr list --head docs/session-2026-09-15-preclear`, which returned `[]`.
- `gh api '/search/issues?q=repo:ray-manaloto/dotfiles+ephemeral'`: 33 hits. The control term `graphify` returned
  459, so the search discriminates.
- `git grep -l -e --ephemeral`. As a control, `codex exec` shows up in 4 skill files while `--ephemeral` shows up in
  0 of them, so the grep can see those files.

## Strong Matches

- **KB `91a91cb9`** (Claude, 2026-09-01), #331-343 @337:
  - It measured `--ephemeral` → 0 new `~/.codex/sessions` files and non-ephemeral → +1 file (about 104 KB).
  - #343: "Our lanes all use it, so agentsview structurally cannot see any codex lane."
  - #344: the codex advisor (gpt-5.6-sol, xhigh) answered "Q1 — (a), drop `--ephemeral`". It rejected a per-lane
    hybrid: "a remembered hybrid policy contradicts 'all lanes' and will drift."
  - #386: an AskUserQuestion recommended "Drop --ephemeral everywhere". Ray chose to probe first and then drop.
  - #392-408: the side-effect probe found that the only cost is `resume --last` now landing on lane runs.
  - #428-430: `--thread-source` accepts invalid values and does not prevent that.
  - #433: "Proceeding with the flip."
  - The result is KB `c63e68d3` (#645). The KB rule `ai-cli-invocation.md:132` reads "`--ephemeral` IS NO LONGER IN
    THESE PATTERNS (2026-09-01, Ray)". The KB gate `lane_recording` lives at `hk.pkl:506-532` and
    `kb_setup/lane_recording.py:69`.
- **dotfiles `8dac106f`** (2026-09-01), #398-453:
  - A real `git tag` write was blocked under `workspace-write`, `--add-dir`, `--approve-for-me` and a worktree.
    Only `danger-full-access` allowed it.
  - #422: `--approve-for-me` cannot be combined with `--sandbox`.
  - #428: an AskUserQuestion recommended a repo-owned operator lane at `danger-full-access`. It shipped as
    `5b29c0f7` (#900).
- **dotfiles `4b5c48be`** (2026-09-15), #524-621:
  - Ray, #524: "stop limiting what we are doing / why is it read-only for gh". #533: "we've been discussing this to
    remove those sandbox settings".
  - #546: an AskUserQuestion asked "Remove the sandbox override from `sdlc_team.py`" (recommended: remove now).
    #548: "you've ruled, proceeding".
  - Ray, #575: "i dont see flag '--ephemeral' … search history again as that is a bug that we havent been fixing".
  - #585: an AskUserQuestion asked "Remove it too, same commit (Recommended)". #587 removed it.
  - #599 committed `38ed61f2`. #613 verified that a session was actually persisted.
- **dotfiles `52714f36`** (2026-09-16):
  - #787-799: a two-arm probe with one variable. Without `--ephemeral`: 0 `collab spawn failed`, 2 rollout files, and
    the child carries `parent_thread_id`. With it: 3 failures and 0 files.
  - #799: "I thought we dropped `--ephemeral`" is answered with "we didn't … What was dropped on the preclear branch
    (`e54d45e`, unmerged) was `-s`, not `--ephemeral`". **That is wrong.** `38ed61f2` dropped both flags, as its
    diff and commit body show.
  - #833/#851: Ray approved shipping the `--ephemeral` removal. The result is `0c2a2782` (#1145), which touched
    `sdlc_team.py` only.
- **dotfiles `f643887b`** (2026-09-23), #26-88: the codex exec review settings research, persisted as
  `codex-exec-review-settings-2026-09-23.md`.
  - #45: "Never `--dangerously-bypass-hook-trust` in launchers."
  - Its row 35 marks `--ephemeral` "L" confidence for review sub-agents and cites only `ai-cli-invocation.md`. The
    09-01 KB ruling and the 09-15 audit were never retrieved.

## Decision record

| Flag / setting | Decision | When / who | Why | Evidence |
|---|---|---|---|---|
| `--ephemeral` (all lanes) | **Remove from every lane pattern and gate against its return** | 2026-09-01, Ray (knowledge-base) | It only controls persistence and leaves no session file, so lanes are invisible to agentsview. The one cost is `resume --last` picking lane runs; use `resume <id>` instead | KB `91a91cb9` #331-433 @386; KB `c63e68d3`; KB rule `:132-147`; KB `hk.pkl:506-532` |
| `--ephemeral` (dotfiles launcher) | **Remove from "the dotfiles launcher" and add repo-local static coverage** | Filed 2026-09-11 from KB `kb-20260911.001`. Ray ruled that agentsview ownership belongs to dotfiles | No `turn_context` means model, effort and sandbox cannot be audited, and 13 `danger-full-access` sessions were found only because they persisted | #1016 (OPEN) |
| `--ephemeral` (`sdlc_team`) | **Remove** | 2026-09-15, Ray (`4b5c48be` #585-587). Lost; re-ruled 2026-09-16 (`52714f36` #833/#851) | It blocks every collab spawn and discards forensics | `38ed61f2` (lost), then `0c2a2782` (#1145, on main); `sdlc_team.py:748-768` |
| `--ephemeral` (non-delegating lanes) | **De facto KEPT by rule text** ("drop it for any lane that delegates"). **No session records a deliberate keep decision** (p9 = 0) | 2026-09-16, written by the coordinator in #1145 | Reason given: "a research or implementation lane does not delegate" | dotfiles `ai-cli-invocation.md:29-35` |
| `-s`/`--sandbox` (operator lane) | **`danger-full-access`** | 2026-09-01, Ray (`8dac106f` #428) | Only that mode permits git writes. It is already the user-config default | `5b29c0f7` (#900); `codex-sol-operator.md:23-27` |
| `-s` (implementer lane) | **`danger-full-access`**, overriding the plugin's "never" | 2026-09-12 (#1039) | Under `workspace-write` every repo gate fails on writes outside the working tree (lint log, `ps`, `~/.local/share/mise`) | `ef32573d`; `codex-sol-implementer.md:62-90` |
| `-s` (`sdlc_team`) | **Do not pass `-s`; inherit the machine's `danger-full-access`** | 2026-09-15, Ray (`4b5c48be` #524/#533/#546-548). **LOST** | Under `workspace-write`, `network_access` defaults to false, so `gh` and `mise` were blocked in both modes | `38ed61f2` on the unmerged branch; test `test_no_mode_passes_a_sandbox_or_ephemeral_flag` absent from main |
| `--approve-for-me` | **Never.** Cannot be combined with `-s` | 2026-09-01 (`8dac106f` #422) | It injects `workspace-write` and still blocks git writes | `codex-sol-operator.md:25,88`; `ai-cli-invocation.md` Codex facts |
| `--full-auto` | **Does not exist.** Never use it | 2026-08-27 (KB `999a320c` #115); re-armed 2026-09-01 and 2026-09-10 | Absent from `codex exec --help`, and 0.152.0 errors on it | `ai-cli-invocation.md` Codex facts |
| `--dangerously-bypass-approvals-and-sandbox` | **Reject** | 2026-09-15 audit (lost branch); task_plan 9.4 notes "banned in advisor docs" | A measured no-op here: `turn_context` is identical (never / danger-full-access), and the future meaning is hazardous | lost audit :81-94; `task_plan.md:258-265` |
| `--dangerously-bypass-hook-trust` | **Reject / never in launchers** | 2026-09-15 audit (lost); 2026-09-23 `f643887b` #45 | Hooks already run when trusted, so the flag only weakens provenance. **Conflict:** task_plan 9.4 cites KB `093aab0c` as saying it is "REQUIRED or codex hooks silently never fire" | lost audit :213; `task_plan.md:261-262` |
| `--strict-config` | **ADOPT for `sdlc_team`** (audit recommendation, **not a Ray ruling**) | 2026-09-15 audit (lost) | The project `.codex/config.toml` is loaded, and an unknown key gives rc=1. **Conflict:** task_plan 9.4 records "prior: useless as a feature oracle, rc=0 for bogus". That probably refers to `--enable <bogus>`; unverified | lost audit :32-79; `task_plan.md:259-260`; 09-23 report row 22 (it also strictly validates `-c`) |
| `--output-schema` + `-o` | **Adopt both for `codex-lane`** (#613). `--output-schema` is **silently ignored under `exec review`** | 2026-08-06 (#615); 2026-09-23 research | A typed verdict for the reaper. On the review path the schema is dropped (source-cited) | `5345bd5b`; `codex_lane.py:352-394`; 09-23 report row 31 |
| `--json` | **Conditional.** Needs stdout and stderr kept apart | 2026-09-15 audit (lost) | JSONL lacks `spawn_agent` events, and `sdlc_team` sends stderr to stdout | lost audit :158-186 |
| `-c model_reasoning_effort` | **`xhigh`** for codex lanes | `.claude/CLAUDE.md` ("codex effort = xhigh"); `sdlc_team` default `effort="xhigh"` (`:69`) | Standing configuration | `.claude/CLAUDE.md` |
| `--model` | **Explicit per lane family** (`gpt-5.6-sol` / `gpt-6-astra`) | 2026-09-12 (#1034, astra mirror) | Two model families | agent defs; `codex_lane.py:374` (optional) |
| trailing `-` / stdin | **Required.** Without it a positional prompt blocks on stdin forever | 2026-09-10 (memory `project_session_2026-09-10`: 28 min wedged); the rule's `codex-sdlc-team.md` "The trailing `-` is why the task exists" | The rule's facts section says a positional prompt is valid. The hang happens when stdin is inherited open. Both statements hold | `codex_lane.py:357-360` |
| `PLANNING_DISABLED=1` | **Keep for `codex_lane`** until Phase 10. **Not for `sdlc_team`** (lanes SEE the plan) | 2026-09-23, Ray rounds 5-6 | Stops pwf hooks handing the coordinator's plan to a lane | `task_plan.md:636-648`; `codex_lane.py:121-136` |
| `--skip-git-repo-check` | **Reject for SDLC** (audit) | 2026-09-15 audit (lost) | SDLC work requires a repository | lost audit :218 |
| `--ignore-user-config`, `--ignore-rules`, `--enable/--disable`, `-p`, `--oss` | **Reject** (audit) | 2026-09-15 audit (lost) | Drift, discarding the approved posture, or suppressing the project shell policy | lost audit :202-223 |

## Compliance table (current sites, origin/main plus working tree)

| Site | Flags passed | Verdict | Violated decision |
|---|---|---|---|
| `.claude/rules/ai-cli-invocation.md:15-20` (canonical block) | `mise exec -- codex exec --ephemeral -s read-only -`; `--ephemeral -s workspace-write -c model_reasoning_effort="xhigh" -` | **NON-COMPLIANT** | `--ephemeral` breaks the 09-01 KB ruling (the same rule stem, so the content has diverged; `rule-sync.toml:53-58` checks presence by STEM only), #1016, and 09-15. `-s workspace-write` for implementation contradicts #1039. Lines :29-35 turn the rejected hybrid into doctrine |
| `.claude/agents/codex-sol-{adversarial-critic:102, advisor:102, claude-code-expert:113, staleness-auditor:79}.md` + the astra mirrors (`:104, :104, :115, :81`) | `PLANNING_DISABLED=1 codex exec --ephemeral --sandbox read-only --model … -c model_reasoning_effort="xhigh" -o "$OUT" -` | **NON-COMPLIANT** (`--ephemeral`). Everything else complies | `--ephemeral` (09-01, #1016, 09-15). Caveat: read-only still has an execpolicy allow-rule hole for `git add`/`git commit` (09-23 report rows 13-14). Bare `codex`, not the rule's `mise exec -- codex` |
| `.claude/agents/codex-sol-operator.md:66`, `codex-astra-operator.md:68` | `--ephemeral --sandbox danger-full-access --model … -c …xhigh -o -` | **NON-COMPLIANT** (`--ephemeral`). The sandbox complies with 09-01 | A full-access lane that leaves no rollout is the "maximum privilege, zero forensics" combination `38ed61f2`'s body calls strictly worst |
| `.claude/agents/codex-sol-implementer.md:168`, `codex-astra-implementer.md:170` | `--ephemeral --sandbox danger-full-access … -o - > $LOG` | **NON-COMPLIANT** (`--ephemeral`). The sandbox complies with #1039 | Same as the operator row |
| `python/src/dotfiles_setup/codex_lane.py:380-394` (`mise run codex-lane`) | `codex exec --ephemeral --sandbox read-only --output-schema … -o … [--model] -` + env `PLANNING_DISABLED=1` | **NON-COMPLIANT** (`--ephemeral`, justified at `:364-366` by the pre-ruling "one transcript per review round forever"). `PLANNING_DISABLED` complies with round 6 | #1016's first line names "the dotfiles launcher". No `-c` effort, so it inherits the user config (not read; unverified) |
| `python/src/dotfiles_setup/sdlc_team.py:747-781` (`mise run sdlc-team`) | `<resolved codex> exec -s {read-only\|workspace-write} -c model_reasoning_effort="<xhigh>" -C <workdir> -o <out> -` | **PARTIAL.** `--ephemeral` absent: complies. **`-s` present: NON-COMPLIANT** with Ray's 09-15 ruling (lost). `--strict-config` absent (audit recommendation, unratified) | `-s` also sets `network_access=false` under workspace-write, and every repo gate fails under workspace-write (#1039). No `PLANNING_DISABLED`: complies with round 5 |
| `mise.toml:280-282, 720-735` | Thin callers (`dotfiles-setup sdlc-team` / `codex-lane`) | N/A: no argv | — |
| fable-orchestrator 1.21.0 `scripts/run-lane.sh:91-92` (codex-implementer) | `codex exec --model … -c effort --sandbox workspace-write --skip-git-repo-check --cd` | **Diverges** (third-party; Phase 10 retires it) | `workspace-write` goes against #1039; `--skip-git-repo-check` goes against the audit. No `--ephemeral`: complies |
| fable-orchestrator 1.21.0 `run-lane.sh:112-113` (codex-reviewer) | `codex exec review … -c 'sandbox_mode="read-only"' --json` | Complies on ephemeral. Read-only is porous | 09-23 report rows 13-14: allow rules let a sandboxed reviewer commit |
| openai-codex 1.0.6 `scripts/lib/codex.mjs:70, :1013, :1117` (`codex:rescue`) | app-server `ephemeral: options.ephemeral ?? true`; review `ephemeral: true`; task `persistThread ? false : true` | **Diverges** (third-party) | Ephemeral by default, so invisible to agentsview |
| knowledge-base `.claude/skills/kb-review/references/lanes.md:436` | `codex exec --ephemeral --sandbox read-only -` | **NON-COMPLIANT with KB's own 09-01 ruling** | Outside `lane_recording`'s DEFAULT_GLOBS (two agent directories plus the rule file) |
| `docs/specs/codex-sdlc-subagent-team.md` | Historical argv, marked REFUTED at `:170` | Complies (annotated) | — |
| `tests/test_codex_agent_parity.py:60` | A fixture containing `--ephemeral` | N/A: fixture text | No test pins presence or absence of `--ephemeral` for the agent definitions or `codex_lane`. Only `sdlc_team` has an absence test |

**Every site still passing a ruled-out flag:** the rule block (2 lines), 12 agent definitions, `codex_lane.py:383`
(`--ephemeral`), `sdlc_team.py:747/772-773` (`-s`), the `codex:rescue` plugin (`ephemeral` defaulting to true), and
KB `lanes.md:436`. The two critic runs tonight used `codex-astra-adversarial-critic`, and `:104` still passes
`--ephemeral`. Those rollouts were therefore not persisted, and agentsview cannot audit them (inferred from the flag;
not probed per run).

## Gaps

- **Why the rulings did not propagate:** (a) `rule-sync` checks rules by stem, not content. (b) Dotfiles has no
  equivalent of KB's `lane_recording` gate, even though #1016 asks for "repository-local static coverage". (c) The
  09-15 preclear branch was never shipped, and the 09-16 recovery misread its contents (`52714f36` #799).
  (d) The 09-23 review-settings research cited only dotfiles' rule and never found KB's 09-01 record. This is a
  retrieval failure of the same class the memory index flags for 2026-09-15.
- **Unrecovered artifacts on `docs/session-2026-09-15-preclear`, absent from main:**
  - `codex-flag-audit-2026-09-15.md`, `issue-triage-2026-09-15.md`, `codex-impl-2026-09-15.md`, and the
    final/round-2/round-3 preclear audits.
  - The briefs under `briefs-2026-09-15/` and `docs/claude-codex-harness-mapping.md`.
  - The `-s` removal and its test.
- **Unverified in this lane:**
  - Whether `~/.codex/config.toml` sets `model_reasoning_effort`. I did not read it; `codex_lane` inherits whatever
    it holds.
  - Whether `--ephemeral` breaks `exec review` sub-agents (09-23 row 35: unmeasured).
  - The `--strict-config` "rc=0 for bogus" conflict.
  - The `--dangerously-bypass-hook-trust` "REQUIRED" claim from KB `093aab0c`, which contradicts the 09-15 audit.
    Next probe: open the `093aab0c` window.
- **Not searched:** dotfiles transcripts before 2026-08-27 for `--ephemeral` origins. The rule has carried
  `--ephemeral` since `c5a0715f` (2026-03-29) with no recorded rationale.
- **Recommended next step (for the coordinator; no action taken here):**
  1. Recover `38ed61f2`'s `-s` removal and the lost audit onto a branch.
  2. Drop `--ephemeral` from the 12 agent definitions, `codex_lane.py` and the rule block.
  3. Port KB's `lane_recording` gate so #1016 closes.
  4. Fix KB `lanes.md:436`.
  5. Consider a content-level rule-sync check for `ai-cli-invocation`'s argv block.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): git history (`0c2a2782`, `38ed61f2`,
  `428a6ff7`, `ef32573d`, `5b29c0f7`, `5345bd5b`), issues #1016/#1112/#1142/#1145/#1296/#1297 (via search API),
  PR #1128 commit list, current invocation sites.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): local clone. `c63e68d3`, the rule
  `ai-cli-invocation.md:125-147`, `hk.pkl:500-532`, `kb_setup/lane_recording.py`, and
  `.claude/skills/kb-review/references/lanes.md:436`.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): not read directly. It is
  referenced only through `PLANNING_DISABLED` rulings in `task_plan.md`.
- fable-orchestrator 1.21.0 and openai-codex (`codex` plugin 1.0.6), read from the local plugin cache
  (`~/.claude/plugins/cache/…`). Upstream repos were not consulted.

## Appendix: incremental notes as written during the sweep


- N1 git: `0c2a2782` (2026-09-16, #1145) removed `--ephemeral` from `sdlc_team.py` argv only; rule got caveat "drop it for any lane that delegates"; canonical block KEPT `--ephemeral`.
- N2 AV `52714f36` #829-1033 @835: Claude coordinator researched why `--ephemeral` was added before removing; Ray approved via AskUserQuestion Q1 (#833) "one branch, both fixes"; #851 "six decisions, all settled".
- N3 AV KB `91a91cb9` #331-343 @337 (2026-09-01): measured ephemeral→0 session files, non-ephemeral→+1; #343 "Our lanes all use it, so agentsview structurally cannot see any codex lane". #344 codex advisor verdict: "Q1 — (a), drop `--ephemeral`" for ALL lanes; codex rejected a per-lane hybrid: "a remembered hybrid policy contradicts 'all lanes' and will drift".
- N4 current: 12/12 `.claude/agents/codex-{sol,astra}-*.md` still pass `--ephemeral`; `codex_lane.py:383` still passes it (docstring :364 rationale: avoid one transcript per review round forever); `sdlc_team.py:748` absent (compliant); rule canonical block `ai-cli-invocation.md:16,19` still passes it.
- N5 `sdlc_team.py` does NOT set `PLANNING_DISABLED` (compliant with Ray round-5 ruling task_plan.md:636 "sdlc_team lanes SEE the plan"); `codex_lane.py:136` keeps it (round-6 ruling task_plan.md:643-644).
- N6 AV KB `91a91cb9` #384-433: Ray answered AskUserQuestion (#386) "probe side effects first, then drop" + static hk guard; probe (#392-408) found only cost = `resume --last` picks lane runs; `--thread-source` not a mitigation (#428-430); #433 "Proceeding with the flip". KB commit `c63e68d3` (2026-09-01, #645) removed `--ephemeral` from KB patterns; KB rule `ai-cli-invocation.md:132` "`--ephemeral` IS NO LONGER IN THESE PATTERNS (2026-09-01, Ray)"; KB hk step `lane_recording` (`hk.pkl:506-532`, `kb_setup/lane_recording.py:69`) gates it. KB residual: `.claude/skills/kb-review/references/lanes.md:436` still instructs `codex exec --ephemeral` (outside the gate's DEFAULT_GLOBS).
- N7 dotfiles never mirrored the 2026-09-01 KB ruling; 2026-09-16 (#1145) chose the per-lane HYBRID ("drop it for any lane that delegates") that the 2026-09-01 codex advisor explicitly rejected as a drift risk.
- N8 `rule-sync.toml:44-58` syncs rules by STEM only ("Presence is by STEM, not by content"), so `ai-cli-invocation` content divergence KB vs dotfiles (ephemeral) is invisible to `mise run rule-sync`.
- N9 #1016 (OPEN, filed 2026-09-11 from KB session `kb-20260911.001`): first line "Remove the observed ephemeral invocation from the dotfiles launcher and add repository-local static coverage there"; Ray ruled agentsview ownership belongs in dotfiles. Still open; the static coverage KB has (`lane_recording`) does not exist in dotfiles.
- N10 commit `38ed61f2` (2026-09-15, "stop overriding the machine sandbox and stop discarding the transcript") removed BOTH `-s` and `--ephemeral` from sdlc_team argv, citing #1016 + the 2026-09-01 `danger-full-access` posture + network_access=false under workspace-write — it is ONLY on branch `docs/session-2026-09-15-preclear`, NOT an ancestor of origin/main (`git merge-base --is-ancestor` → NO). #1145 (0c2a2782, 2026-09-16) re-derived only the `--ephemeral` half; `sdlc_team.py:747` still passes `-s read-only|workspace-write`.
- N11 sandbox decisions: 2026-09-01 `8dac106f` #398-453 — measured git tag write: workspace-write, --add-dir, --approve-for-me, worktree all BLOCK; only danger-full-access permits; Ray approved repo-owned operator lane at danger-full-access (#428 Recommended; operator lane shipped `5b29c0f7` #900). 2026-09-12 `ef32573d` (#1039): implementer at danger-full-access because every repo gate fails under workspace-write (writes outside tree: ~/.local/state/dotfiles, `ps`, ~/.local/share/mise).
- N12 `--approve-for-me` mutually exclusive with `--sandbox` (8dac106f #422, 2026-09-01); `--full-auto` absent: KB `999a320c` #115 (2026-08-27) arm, dotfiles codex mirror `01a05e73` #429-430 (0.152.0 "unexpected argument"); rule `ai-cli-invocation.md` Codex facts.
- N13 f643887b (dotfiles, 2026-09-23 07:50) #26-88 @45: "Never `--dangerously-bypass-hook-trust` in launchers" (Fable/advisor proposal text — verify parent). task_plan.md:258-265 item 9.4 lists the flag with prior "REQUIRED or codex hooks silently never fire" (KB session `093aab0c`).
- N14 ⭐ RULINGS LOST IN A SQUASH: AV `4b5c48be` (dotfiles, 2026-09-15): #524 Ray "stop limiting what we are doing / why is it read-only for gh"; #533 Ray "we've been discussing this to remove those sandbox settings"; #546 AskUserQuestion "Remove the sandbox override from sdlc_team.py" (Recommended: remove now) → #548 "you've ruled, proceeding"; #575 Ray "i dont see flag '--ephemeral' ... search history again as that is a bug that we havent been fixing"; #585 AskUserQuestion "Remove it too, same commit (Recommended)" → #587 "Removing `--ephemeral` in the same change". Committed as `38ed61f2` on `docs/session-2026-09-15-preclear` with test `test_no_mode_passes_a_sandbox_or_ephemeral_flag`. That branch has NO PR (`gh pr list --head` → `[]`); PR #1128 (head `docs/session-2026-09-14e-reports`, merged 2026-09-16T04:47Z) squashed as `428a6ff7` whose sdlc_team.py still has `sandbox = ...` (:349) + `"--ephemeral"` (:353) + `"-s"` (:354). `git log -S test_no_mode_passes_a_sandbox origin/main` → empty.
- N15 ⭐ A COMPLETE FLAG AUDIT EXISTS ONLY ON THE LOST BRANCH: `docs/session-2026-09-15-preclear:docs/research/kb/reports/agents/codex-flag-audit-2026-09-15.md` (307 lines; codex-cli 0.154.0; brief `briefs-2026-09-15/brief-codex-flags.md`). Verdicts: ADOPT `--strict-config` (project `.codex/config.toml` IS loaded; unknown key → rc=1), `-c`, `-C`, `-o`, trailing `-`; REJECT `-s`, `--approve-for-me`, `--dangerously-bypass-approvals-and-sandbox` (measured no-op: identical turn_context never/danger-full-access), `--dangerously-bypass-hook-trust`, `--skip-git-repo-check`, `--ephemeral` (also "empirically suppresses application of project `shell_environment_policy`"), `--ignore-user-config`, `--ignore-rules`, `--enable/--disable`, `--oss`, `-p`, `--color`; CONDITIONAL `--output-schema`, `--json` (needs split stdout/stderr — `sdlc_team.py` merges stderr=STDOUT), `-m`, `--worktree`, `--add-dir`, `--thread-source`, `-i`. Recommended argv: `codex exec --strict-config -c 'model_reasoning_effort="<effort>"' -C <workdir> -o <output> -`. None of `docs/research/kb/reports/agents/{codex-flag-audit,issue-triage,codex-impl,final-preclear-audit,...}-2026-09-15.md` exist on main.
