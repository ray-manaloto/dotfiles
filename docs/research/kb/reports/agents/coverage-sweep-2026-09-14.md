# Coverage sweep — session 2026-09-14e

**Lane:** completeness audit (read-only; no source edited, no issue filed or closed).
**Question:** is every finding this session produced actually TRACKED in a GitHub
issue, or explicitly declared untracked?

**Verdict:** the session's record is **NOT complete**. The two largest gaps are
structural rather than incidental: the backlog's **rank 1** action (the Renovate
`matchFileNames` grouping) and the blind spots of the gate the session's own
merged PR shipped (`pin-parity`, #1094) have **zero GitHub issues between them**,
and both currently survive only in tracked reports plus a **gitignored** handoff.

## Method and control arms

All 322 OPEN issue bodies were cached (1,143,308 bytes; `grep -c '^@@@ISSUE'`
-> 322) and searched with an awk that attributes every match to its issue number.

| Arm | Probe | Result |
|---|---|---|
| known-absent, invented fresh for this run | `qvmzzt7x41` over all 322 bodies | **0** |
| known-present | `PLANNING_DISABLED` over all 322 bodies | **8** (all #1115) |
| known-absent, fresh | `wqk3zv9r` in `pin-parity.toml` | **0** |
| known-present | `shared.toml` in `pin-parity.toml` | **5** |
| known-absent, fresh | `xj4pqw8n` in the session memory file | **0** |
| known-present | `1110` in the session memory file | **4** |
| known-absent, fresh | `hb7zqx2m` in `persistence-gate-retry.md` | **0** |
| known-present | `dubious` in `persistence-gate-retry.md` | **3** |

Both probes discriminate in both directions. Every "0 occurrences" below was
taken in the same command shape as its live control arm. Control strings were
invented for this run and are now burned by appearing here.

Line counts, issue counts and file contents were re-derived here; none is
inherited from the brief.

## Load-bearing measurements (re-derived)

| Claim | Probe | Result |
|---|---|---|
| the `.agent/` handoff is not durable | `git check-ignore -v .agent/plans/session-2026-09-14-e.md` | `.gitignore:109:.agent/` rc=0; `git ls-files .agent/` -> **0 files**. Control: `git check-ignore AGENTS.md` -> rc=1 |
| all 28 corpus reports ARE durable | `git ls-files docs/research/kb/reports/agents/ \| grep 2026-09-14` | 28 files, all tracked |
| `pin-parity` in any open issue | search over 322 bodies | **0** |
| `matchFileNames` in any open issue | search over 322 bodies | **0** |
| `expected_install_method` in any open issue | search over 322 bodies | **0** |
| `check_one_process_per_event` / `matchers_exact` | search over 322 bodies | **0** / **0** |
| the F5 `-<scope>.md` path | search `<scope>` over 322 bodies | **0** |
| `require_control_arm` | search over 322 bodies | **0** (control `tautolog` -> 2, #1042/#850) |
| `pin-parity.toml`'s whole registry | `grep -nE '^\[' pin-parity.toml` | `[meta]`, `[tools.chezmoi]`, `[tools.hk]`, `[tools.mise]` — **three tools** |
| ...covers claude | `grep -c claude pin-parity.toml` | **0** (control `hk` -> 10) |
| ...covers a lockfile / `.d.ts` / `suites.toml` | three greps | **0 / 0 / 0** |
| the claude pin is STILL LIVE | `mise.toml:43` | `"github:anthropics/claude-code" = "2.1.270"` |
| the 8th surface is real | `python/verification/suites.toml:2665` | asserts `"// Written by Claude Code 2.1.270."` as a per-path contract token |
| hk's lockfile pin site | `.devcontainer/mise-system.lock:5050` | `[[tools.hk]]` |
| `doctor.toml` contradicts itself | `doctor.toml:248` vs `:264` | comment: *"Native installer owns claude. Not mise."* — assertion: `expected_install_method = "package-manager"` |
| the currency oracle is the thing that is behind | `claude_doctor.py:229-238` | `["mise", "latest", ORACLE_SPEC]`, `ORACLE_SPEC = "github:anthropics/claude-code"` (`:66`) |
| `pin_parity` DOES handle multi-match files | `pin_parity.py:105` | `re.findall(...)` — so the two `setup-mise/action.yml` hits (`:39`, `:44`) are both compared. **Not a gap; removed from the list.** |

## THE UNTRACKED LIST — ranked by what a future session would most regret

### A1. The session's rank-1 action has no issue at all

`matchFileNames` -> **0 of 322 open issue bodies.** The backlog triage ranks the
hk currency chain **rank 1** (`backlog-triage-2026-09-14.md:225`) and its
re-review confirms clause 2 — adding `hk.pkl`, `hk-common.pkl`, `hk-image.pkl` to
`renovate.json`'s `packageRules[0].matchFileNames` — as *"correct, not just
plausible"*, with new evidence (`adv-backlog-rereview-2026-09-14.md:120-137`;
`ci.yml:288-292` includes `hk-common.pkl`/`hk-image.pkl` but not `hk.pkl`).

It exists in exactly three places: the `/goal` text (a scratchpad path the handoff
itself flags as maybe gone), the handoff appendix (**gitignored**), and two tracked
reports. `gh issue list` — the surface a fresh session actually reads — shows
nothing.

**Its recurrence is separately untracked:** #1090 and #1093 are split *today*
exactly as #1079/#1063 were, so the gap returns at every future hk major
(`adv-backlog-rereview-2026-09-14.md:99-105`).

### A2. #1094 shipped `pin-parity` last night and has no follow-up ticket of any kind

`pin-parity` -> **0 of 322 open issue bodies.** Four distinct blind spots, each
measured above:

1. **Neither lockfile** is a registered site, and `.devcontainer/mise-system.lock:5050`
   carries hk. **#1063 dies on exactly a lockfile mismatch** (`hk@1.58.1 is not in
   the lockfile`, x4, per `adv-backlog-rereview-2026-09-14.md:57-62`), so this is
   the blind spot that is actively costing a PR.
2. **No `claude` entry at all**, while `.claude/types/claude-code.d.ts:1` and
   `suites.toml:2665` both carry the version string.
3. `suites.toml:2665`'s contract token means the `.d.ts` version is **gate-bound**:
   a bump must sequence the generator (`mise run fnhook-types-refresh`, which runs
   `claude`) against the contract, or the gate's own input goes stale.
4. The registry is **three tools**, so every other pinned tool is uncovered by
   construction — which the file's own header calls the blind spot it exists to end.

### A3. A live gate asserts the opposite of the decision it cites

`expected_install_method` -> **0 of 322 open issue bodies.**

- `doctor.toml:264` sets `expected_install_method = "package-manager"`. Its own
  comment block at `:248-263` records the grilling decision *"Native installer
  owns claude. Not mise."* and then states that *"a mise-provided claude reports
  `package-manager` … and neither is `native`."* So the assertion expects the state
  the decision forbids, and a mise-provided claude **passes**.
- `claude_doctor.latest_version` (`claude_doctor.py:229-238`) resolves "latest" via
  `mise latest github:anthropics/claude-code`. Measured live in
  `rec-fnhook-delivered-2026-09-14.md:175-190`: `verdict: ok`,
  `install_method: "package-manager"`, `latest_version: "2.1.270"` — while the
  native install is **2.1.271**. A currency check whose oracle is the component
  that is behind cannot report being behind.
- `doctor.toml:253-255` predicts the mise copy *"loses to `~/.local/bin/claude` on
  PATH order"*. Measured false on this host (`adv-claude-pin-2026-09-14.md:54-79`:
  `which -a claude` puts the mise install dir first).

### A4. The claude-pin decision is settled and unimplemented, and #1043 is stale in three ways

#1043 is the nearest issue, and its Fix option 3 *is* the settled direction — but:

- its anchor `mise.toml:26` names the retired **npm** pin; the live pin is
  `mise.toml:43` `"github:anthropics/claude-code" = "2.1.270"`;
- it says option 3 *"needs a way to name an exact version that `mise exec`
  accepts"* — the blocker this session **disproved** (`mise exec
  "github:anthropics/claude-code@2.1.270" -- claude --version` -> 2.1.270 rc=0 in a
  no-pin directory);
- it predates the 7/8-surface sizing, the grilling decisions, and the fact that the
  pin defeats the native auto-updater.

Nothing in any issue records that the decision is settled, what the surfaces are,
or that the proposed blocker is gone.

**Compounding:** the tracked report `adv-claude-pin-2026-09-14.md:167` ends
**"KEEP the pin"** — a verdict the operator overruled. The overrule lives only in
the gitignored handoff, so a future reader of that report gets the opposite answer
with nothing in the file to warn them. (`adv-config-simplify-2026-09-14.md:52`'s
Phase 2 is likewise flagged wrong only in the handoff, and both reports still ship
`"### Probes running..."` as their evidence section.)

### A5. cold-1112 F5 — the *other* shared advisor path the #1112 fix skipped

`<scope>` -> **0 of 322 open issue bodies.** `.agent/kb/raw/codex-{sol,astra}-advisor-<scope>.md`
(`.claude/agents/codex-sol-advisor.md:57`, `codex-astra-advisor.md:59`) was left
un-disambiguated by #1113's fix, and `cold-1113-r2-2026-09-14.md` R17 re-states it
as still open. It is the identical silent cross-contamination class #1112 exists to
close, on a path the fix did not touch. #1114 does not mention it.

### A6. Rank 2's deliverable has no issue — only its two prerequisites do

`check_one_process_per_event` -> **0**; `matchers_exact` -> **0**. #1099 (subset
semantics) and #1100 (graphify guard uncovered) file the two *prerequisite
defects*. The gate they unlock — whose own row in
`adv-hook-consolidation-2026-09-14.md:401` reads **"Currently enforced by:
Nothing."**, with the full proposed shape and fail-arm fixtures at `:403` — has
none.

### A7. `lock_shared.py` — no bring-up step and no timeout bound

`adv-goal-review-2026-09-14.md` Q4, citing `lock_shared.py:391` (routing) and
`:299` (subprocess): `lock-shared` routes into the devcontainer, has no `mise run
up`, and the `devcontainer exec` call is **unbounded**. `/goal` clause 3 works
around it; nothing fixes it. Three loose `lock-shared` hits in issues, none about
this.

### A8. Three watchdog-rules proposals were never filed

From `watchdog-rules-2026-09-14.md:77-113`: the **one-off frequency gate** (a
command recurring 50+ times must earn a mise task), a **`require_control_arm`**
contract handler (today a tautological test passes), and a **session-start
guard-health probe**. All -> 0 issue hits. Its proposal 3 (tool pin sync) is what
#1094 delivered; proposal 2 is #1101; proposal 1 is split across #1057/#1096/#1097.

### A9. The parallelization question was never answered, and is framed nowhere

Handoff lines 143-150. No issue frames it as open — #1112 cites the lane only as
collision evidence, #994 lists `gate-runner` as a roster row. The lane also left
**`adv/parallelization-plan-2026-09-14`** as a live local branch (`git branch
--list 'adv/*'` -> present) with uncommitted work.

### A10. The session memory file is stale, and MEMORY.md is load-bearing alone

`project_session_2026-09-14-e.md`: **0 hits** for `1111`, `1112`, `1113`, `1114`,
`1115`, `2.1.27`, `shadow`, `claude pin`, `orchestration`, `gate-runner`,
`codegen` (control `1110` -> 4; fresh `xj4pqw8n` -> 0). Every one of those facts
lives **only** in the `MEMORY.md` hook line — precisely the shape
`memory-index-curation` warns about ("shortening a hook silently destroys any fact
that lives only there"). **#1115 appears in neither file** (`grep -c 1115` -> 0 in
both).

The handoff's own filed-issue counts are stale in three places (16 at :17, 17 at
:224, 19 at :186) against the real 20 (#1096-#1115, #1109/#1113 being PRs).

### A11. Lower-regret, but real

| Finding | Evidence | Status |
|---|---|---|
| **`md_size_budget` does not govern `.claude/agents/**`** (cold-1112 F10) | named in **#1115**'s Provenance section as *"worth its own issue"*; handoff:139-141 says "NOT filed" | **PARTIAL — durable, not actionable.** It survives in an issue body, but no issue's "what fixed looks like" covers it |
| **cold-1112 F4's pruning half** — two permanent files per invocation, nothing prunes `.agent/kb/raw/` | #1114 R9 covers only the *announcement* half | UNTRACKED |
| **cold-1112 F6** — the fabricated `.claude/rules/codex-astra-advisor.md` citation at `adv-parallelization-plan-2026-09-14.md:45` | recorded in **#1112**'s "Unrelated observation" | **TRACKED as an observation**, with no action item |
| **cold-1112 F7/F8** — two `## GitHub repos touched` sections (`:34`, `:56`); a scratchpad-only subject id (`adv-goal-review:4`) | handoff:204-210 — `agent-artifact-conventions.md` §8 forbids rewriting archived records | UNTRACKED; the only remedy (an annotation) is unassigned |
| **`rec-fnhook-intent`'s four unresolved questions** (`:199-225`) — is "zero outdated dependencies" a requirement at all? why are plugin-health/dependency-currency informational? | its own recommendation says *"It must be stated explicitly in an issue"* | UNTRACKED — needs operator input, not engineering |
| **`adv-config-simplify` Phase 4** — index the pin registry at session start, after #1054 | `adv-config-simplify-2026-09-14.md` Phase 4 | UNTRACKED |
| **mise cannot read an external TOML for versions** (`read_file` returns raw text; `[vars]` cannot parse) | `adv-config-simplify-2026-09-14.md` Q3 | research fact, durable in a tracked report; no ticket needed |

## Checked and NOT gaps (do not re-report)

- **#1114** covers R4, R5, R6, R7, R8, R9, R10, R16 and R18 in full. R11-R15 and
  R17 are INFO confirmations with no action.
- **#1115** covers cold-1112 F9 and carries the `git archive`-mutation-is-void
  lesson in its own body.
- **#1110** tracks the `land -- 1109` *undiagnosability* and explicitly anticipates
  the `persistence-gate-retry.md` signature row; the cause being unknown is stated
  in the issue, so it is tracked-as-blocked rather than lost.
- **U1-U13 -> #1096-#1108** is complete and correct per `u-filing-2026-09-14.md`;
  U14 is genuinely #1056's class 2.
- **`pin_parity.py:105` uses `re.findall`**, so the twice-pinned
  `setup-mise/action.yml` is fully compared. Not a gap.
- **`.chezmoiversion`** IS a registered pin-parity site, so
  `rec-fnhook-delivered`'s Real Miss 1 is delivered; Real Miss 3 (mise multi-site)
  likewise.
- All 28 corpus reports are tracked by git.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository under audit: all 322 open issue bodies, issues #1043, #1056, #1057, #1099, #1103, #1107, #1110, #1112, #1114, #1115 read in full, and the source anchors `mise.toml`, `pin-parity.toml`, `doctor.toml`, `python/src/dotfiles_setup/{claude_doctor,pin_parity}.py`, `python/verification/suites.toml`, `.devcontainer/mise-system.lock`, `.claude/rules/persistence-gate-retry.md` re-resolved.
