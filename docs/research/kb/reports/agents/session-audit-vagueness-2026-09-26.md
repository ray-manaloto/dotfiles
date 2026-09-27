# Session audit 2026-09-26 — vague or misinterpretable docs/plans (Brief P)

Scope: dotfiles `12a34e88..ffd13b0d` (HEAD `ffd13b0d`), knowledge-base `6957b0ac..6a4e4b2f`.
Read as a fresh session / codex lane would. Read-only except this file. Status: COMPLETE (32 findings: P1-P11, S1-S9, W1-W4, R1, K1-K4, D1-D2, O1).

## Findings

### A. `docs/specs/research-fanout.md` (rev 5) vs shipped `python/src/dotfiles_setup/research_fanout.py`

**P1 — Status line is stale: the spec reads as pending work.** `research-fanout.md:1-7` says "RATIFIED … rev 5" and §6
(`:174`) says "`caller`. Leave changes uncommitted" — but the work shipped as `e5ac3324` (#1391) on main. A fresh
session or codex lane reading it will treat §8/§9 as open work orders.
Rewrite line 3 to: `Status: SHIPPED in #1391 (squash e5ac3324, 2026-09-26). Rev 5 is the as-built contract; §8 and §9
are the review-round work orders that were applied and are kept as history — they are NOT open work.`

**P2 — §3 control-arm bullet contradicts itself on the firecrawl-developer canary.** `:91-96` first says
"exa/firecrawl-*/context7: `python`", then two sentences later "the firecrawl-developer canary keeps the `repos=`
filter when `--repo` was given (and then uses the repo's name as its query)". Code follows the second
(`research_fanout.py:1022-1023` returns the repo name before the `python` branch at `:1024-1025`).
Rewrite the canary list to: `… exa, firecrawl-search: `python`; firecrawl-developer: the repo's NAME part with the
`repos=` filter kept when `--repo` is given, else `python`; context7: `ctx7 library python` then `ctx7 docs <id> python`,
independent of `--repo` (§9.6); last30days: none → …`.

**P3 — §3 exit-code table omits 130.** `:101-102` lists only 0/1/2; §9.3 (`:258-260`) adds "exit 130 from `main`" on
Ctrl-C, and the code returns 130 (`research_fanout.py:1359-1360`). Also undocumented: an `OSError` writing output
returns 1 with `could not write output` (`:1363-1367`). Rewrite `:101-102` to: `- Exit: 0 if ≥1 source is `ok` or
`empty_verified`; 1 if every requested source is error/skipped/empty_unverified, if NO source was selected, or if the
output could not be written; 2 for usage errors; 130 on Ctrl-C (children's process groups are killed first, §9.3).`

**P4 — "Without it, GitHub sources return `skipped`" is only true when they are NAMED.** `:49-50` vs `:51` ("default =
every source whose prerequisites are present"). In the default set, `--repo` is a prerequisite, so without `--repo`
the github-* sources are silently ABSENT from stdout and the manifest, not `skipped` (`_parse_sources`,
`research_fanout.py:1224-1231` filters on `_prerequisite_reason`, which returns `needs --repo` at `:963-964`). A reader
expecting three `skipped` lines sees nothing. Rewrite `:49-50` to: `- `--repo`: scopes the GitHub sources and the
firecrawl developer index. Without it, GitHub sources are left OUT of the default set entirely (no line, no file); when
named explicitly in `--sources` they return `skipped` with reason `needs --repo`.` Same shape for every other
prerequisite-gated source (exa without `EXA_API_KEY`, etc.).

**P5 — §8.9 ("a query TERM") and §9.9 ("ALL terms") disagree, and §8.9 is not marked superseded.** `:226-229` vs
`:272-273`. The §3 row (`:65`) was patched to point at both, but a reader landing on §8.9 alone gets the ANY-term rule.
Append to §8.9: `**Superseded by §9.9 (ALL terms must match, Ray 2026-09-26).**`

**P6 — "round" numbering is ambiguous.** Title `:1` says "review rounds 1-2 applied; round 3 authorized"; §9 heading
`:243` says "Review round 2 — corrections (… a THIRD round …)". Is "round 3" the third IMPLEMENTATION round (=§9) or a
third REVIEW round still owed? Rewrite the title to: `# Spec (rev 5, 2026-09-26: premise rounds + two review rounds;
§8 = implementation round 2, §9 = implementation round 3, the last one Ray authorized) — …`

**P7 — Cited commits are pre-squash branch SHAs, not on main.** §8 (`:197`, "against commit `50ba9eec`") and §9's
source reports name `50ba9eec`/`0a908d9e`; `git merge-base --is-ancestor <sha> HEAD` → rc=1 for both (control:
`e5ac3324` → rc=0). They survive only on `origin/feat/research-fanout` (`git branch -a --contains 50ba9eec`); deleting
that branch leaves the citation dangling for every clone. Rewrite `:197` tail to: `… against `50ba9eec` — a commit on
branch `feat/research-fanout`, squashed into `e5ac3324` (#1391); it is NOT reachable from main.` (Same caveat belongs
in the `typos.toml` comment, see D1.)

**P8 — "the caller" / "the architect" are undefined owner terms.** `:7` ("authored separately by the architect"),
`:169` ("The architect then runs the live integration arm"), `:198` ("the caller already fixed …"), `:174`/`:203`
("`COMMIT: caller`"). A codex lane cannot tell whether "caller" means itself, the Claude session, or the mise task.
Add under the Status line: `Roles: "architect" = the Claude session that dispatched this spec (session
dotfiles-20260926.000); "caller" = the same session in its commit role (`COMMIT: caller` means the implementer leaves
the tree uncommitted). The implementer is the codex-sol-implementer lane.` — and state whether the §5 live
integration arm (`:169-170`) was actually run and where its evidence is (it is not cited anywhere in the spec).

**P9 — `--out` relative-path semantics unspecified.** Code resolves a relative `--out` against `repo_root`
(`research_fanout.py:1354-1355`), not the process cwd; `:52` is silent. Add: `A relative --out is resolved against the
repo root (MISE_PROJECT_ROOT), not the cwd.`

### B. `.claude/skills/research-sweep/SKILL.md` (byte-identical to `.agents/skills/research-sweep/SKILL.md`, `diff` rc=0)

**S1 — "run the saved workflow and stop here" conflicts with the Workflow opt-in boundary.** `SKILL.md:16-19` tells
any agent that sees the Workflow tool to launch it. The harness's own `workflow-authoring` skill description says it
"does not itself authorize running one" — a workflow is something the user opts into — and this workflow spawns up to
~7 Claude agents incl. an Opus/high node (`research-sweep.js:179`). A fresh session triggered by the skill's broad
description ("whether an upstream bug is fixed …") would spend that without asking. Rewrite `:16-19` to: `- **The
Workflow tool is available AND the user asked for a sweep (or approved one when you proposed it)** → run the saved
workflow and stop here. It fans out to ~5-7 agents including one Opus/high synthesis; for a single-source question use
the in-lane steps instead.`

**S2 — The workflow call omits two arguments and never defines `advisor`.** `:22-25` passes `advisor: false` without
saying what it does; the workflow also accepts `readMax` (default 6) and `verifyMax` (default 5)
(`research-sweep.js:29,31`). Add after the code block: `advisor: true adds a codex-sol-advisor second opinion (codex
tokens). Optional: readMax (URLs deep-read, default 6), verifyMax (claims refuted, default 5). question and an ABSOLUTE
reportPath are required — the workflow throws otherwise.`

**S3 — "recorded" has no destination.** `:44` "Done when every run's manifest path and real exit code are recorded."
Recorded where? `findings.md` (planning-with-files) is disabled in codex lanes (`PLANNING_DISABLED=1`,
`agent-report-persistence.md` rule 3). Rewrite: `Done when every run's manifest path and real exit code are written
into the report's Evidence section (and appended to findings.md when the planning files are enabled).`

**S4 — `last30days` is opt-in but the skill never says so.** `:41-43` routes sentiment questions to `last30days`, and
the `--sources <list>` in `:38` looks optional-by-example. The fetcher never runs last30days unless it is NAMED
(`research-fanout.md:70`, `research_fanout.py:70`), and it is the one source whose "no LLM" guarantee is qualified
(module docstring `:9-14`). Add to `:41-43`: `last30days runs ONLY when named in --sources (it is not in the default
set) and, when its host has an LLM key in `pass`, may use its own LLM planner — name it only for sentiment questions.`

**S5 — Source-dive location unspecified for the in-lane path.** `:52-55` "shallow-clone the repo at its latest release
tag" gives no destination; the workflow's version says `$TMPDIR` and "Delete the clone when done"
(`research-sweep.js:150-158`). A lane following the skill can clone into the repo tree, violating
`agent-artifact-conventions.md` rule 1 ("No ad-hoc directories"). Rewrite: `… shallow-clone the repo at its latest
release tag (`gh api repos/<r>/releases/latest --jq .tag_name`) into `$TMPDIR` (never inside this repo), read the
source, delete the clone, then check whether the default branch changed it since …`

**S6 — Report `<slug>` undefined, and it differs from the fetcher's slug.** `:57-58` uses
`docs/research/kb/reports/agents/<slug>.md`; the fetcher's slug is the QUERY slug (`research_fanout.py:1267-1269`), and
a run makes 1-3 query variants → 1-3 different slugs. Rewrite: `… at docs/research/kb/reports/agents/<question-slug>-<YYYY-MM-DD>.md
(a slug of the QUESTION, not of a query variant; lowercase, hyphens, ≤60 chars).`

**S7 — Two unlabelled inherited numbers.** `:74` "takes about 100 seconds" and `:72` "lags GitHub by hours" carry no
source or measurement condition (`verify-before-advancing.md`: carry a number with its CONDITION;
`probes-need-a-control-arm.md` rule 6). The evidence exists in `mise-warn-multisource-2026-09-26.md` (per-source
latency scorecard) — cite it: `… about 100 seconds (measured 2026-09-26, mise-warn-multisource-2026-09-26.md scorecard;
the fetcher's default cap is 180 s) …` and for the lag: `… can lag GitHub (observed 2026-09-26 on one PR; same report)
…`. If the report does not support "hours", drop the magnitude.

### C. `.claude/workflows/research-sweep.js` (header comments + prompts)

**W1 — The Plan prompt allows an inferred repo but then forbids passing it.** `:110` "GitHub sources will be skipped
unless you infer one with evidence" vs `:114-115` "For each variant run exactly: `mise run research-fanout -- "<query>"
--sources <comma list>`" (no `--repo` when `REPO` is empty). And `sourceDive` requires the workflow-level `REPO`
(`:117`, `:149`), so an inferred repo can never enable it. Pick one. Recommended rewrite of `:110`:
`'REPO: (none — do NOT pick github-* sources; if the question clearly names one project, say so in rationale and the
caller should re-run with args.repo)'`. (Alternative: keep inference, change `:115` to `--repo <inferred owner/repo>`
and add `repo` to the PLAN schema.)

**W2 — Header comment 1 overstates Explore's savings for the critic node.** `:16-19` says bulk reading runs as Explore
on haiku; the critic (`:191-195`) is Explore on **sonnet** at `effort: 'low'` and the meta phase table says
"Verify … (sonnet)". Not wrong, but the header's rule "cheap steps → Explore on haiku" is violated silently. Add to
comment 3: `The critic is Explore on sonnet (it reads one report, needs judgment, but no CLAUDE.md payload).`

**W3 — "~150 KB, measured 2026-09-26" has no method.** `:16-17`. Add the probe (e.g. `wc -c` over the eager set) or
the report that holds it, so the next reviewer can re-derive it rather than inherit it.

**S7 amendment (evidence located).** `mise-warn-multisource-2026-09-26.md:63` is the 100 s figure — measured with
`--emit=compact --plan`, NOT the fetcher's `--emit=json` without `--plan`; `:61` is the lag figure — ONE missed PR
(#13674), "lags by at least hours". So the rewrite must carry that condition: `about 100 s (one run, 2026-09-26, with
--plan; the fetcher's invocation is unmeasured and capped at 180 s)` and `can lag GitHub by at least hours (one PR,
#13674, missed 2026-09-26)`.

**S8 — The skill never mentions the overlapping knowledge-base research surface.** `research-skill-inventory-2026-09-26.md:93,116`
recommends the existing `aggregated-research` skill / `kb_setup.research` and says a new skill "goes against #509's
recorded decisions and `use-tool-builtins.md`"; the spec records Ray re-ruling for a new module (`research-fanout.md:4-6`)
but the SKILL.md a fresh session loads says nothing, so it will find two research skills and no tie-breaker. Add a
`## Relation to knowledge-base` line: `knowledge-base's aggregated-research / kb_setup.research overlaps this; Ray ruled
2026-09-26 (session dotfiles-20260926.000) that dotfiles uses research-sweep + research-fanout independently. Use this
skill in dotfiles; do not import kb_setup.research here (research-fanout.md §4).`

### A (cont.). More spec findings

**P10 — PREMISE 11's `--plan` half is dangling.** `research-fanout.md:190` records "`--plan` skips its internal LLM
planner", but neither §3 (`:70`) nor the code passes `--plan` (`research_fanout.py` `_last30days`: argv is
`["python3", script, query, "--emit=json"]` + optional `--github-repo`). A reader will assume the fetcher uses it — and
the only latency measurement (S7) was taken WITH it. Either add `--plan` to the §3 argv (if it genuinely disables the
planner without an LLM) or rewrite premise 11 to: `last30days --emit choices include json (plugin last30days.py:658).
(--plan was evaluated and NOT used: <reason>.)`

**P11 — The custom-module decision has no written justification.** `use-tool-builtins.md` rule 3: custom code is
justified only when "you record *why* … (which options you evaluated and why each was insufficient)". `:4-6` records
THAT Ray chose a new module over knowledge-base#509 `aggregated-research`/`kb_setup.research`, not WHY. Add: `Why not
kb_setup.research: <Ray's reason from the AskUserQuestion answer, verbatim>.` (Brief N owns recovering the verbatim
answer.)

**S9 — The skill skips the repo's doc-source preference chain.** `research-doc-sources.md` step 00 ("every question
about how the harness itself behaves" → grep the KB offline `agent-harness-docs` FIRST) and step 0 (mintlify cache
before any remote call) are mandatory "top-to-bottom". The skill's trigger list includes "whether a tool now does
something natively" and routes straight to `research-fanout` (`SKILL.md:33-43`). Add as step 0 of In-lane steps AND
to the workflow's Plan prompt: `0. **Local corpora first.** Harness questions (Claude Code / codex / cursor behaviour):
grep ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/<tool>/ first; libraries in
docs/research/mintlify-catalog.md: grep docs/research/mintlify-cache/ first (.claude/rules/research-doc-sources.md).
Fan out only for what those do not answer.`

### C (cont.). Workflow ↔ skill naming

**W4 — The skill and the workflow share the name `research-sweep`, and the workflow looks shadowed.** Both
`.claude/skills/research-sweep/SKILL.md` (`name: research-sweep`) and `.claude/workflows/research-sweep.js`
(`meta.name: 'research-sweep'`) register `/research-sweep` (`$CC/workflows.md:203`: a saved workflow "runs as
`/<name>`"). Probe: in this very session's skill listing, `research-sweep` appears ONCE, with the SKILL's description;
the workflow's `description`/`whenToUse` text is absent — while the other three `.claude/workflows/*.js`
(`gated-implementation`, `graphify-refresh`, `modernization-audit`) ARE listed with their workflow descriptions
(control arm: the listing does surface workflows). The trigger eval (`docs/research/kb/raw/research-sweep-trigger-eval-2026-09-26.md:3`)
installed only the skill folder, so the collision was never exercised. Whether `Workflow({ name: "research-sweep" })`
still resolves the script is UNVERIFIED. Recommended fix: rename the workflow `meta.name` to `research-sweep-run` (and
the file), update `SKILL.md:22` to `Workflow({ name: "research-sweep-run", … })`, then prove it with one live
`/reload-skills` + listing check.

### E. Rules / CLAUDE.md staleness introduced by this range

**R1 — `.claude/CLAUDE.md:67` "Saved workflows: `/gated-implementation`, `/graphify-refresh`."** Now omits
`research-sweep` (added this session) — and `modernization-audit`, which predates it. Rewrite: `Saved workflows
(.claude/workflows/*.js): /gated-implementation, /graphify-refresh, /modernization-audit, /research-sweep<-run per W4>.`
(`.claude/CLAUDE.md` is rule-synced — run `mise run rule-sync` in the same change.)

### F. knowledge-base `docs/plans/mise-state-isolation-spec.md` vs shipped #818/#819

**K1 — Status stale.** `:3` "Ratified" and `:72` "leave changes uncommitted on branch `fix/mise-state-isolation`" —
shipped as `39fb2340` (#818) + `6a4e4b2f` (#819). Rewrite `:3`: `Ratified … SHIPPED in #818 (39fb2340) and amended by
#819 (6a4e4b2f, shared trust store). This file is the as-built contract with §2/§4/§5 updated below; §6 is history.`

**K2 — State-dir location contradicts the code.** `:17-19` and `:53-54` say `tmp_path / "mise-state"` (and
`tmp_path/mise-state/tracked-configs` in the oracle); shipped `tests/conftest.py` uses a SIBLING,
`tmp_path.parent / f"{tmp_path.name}.mise-state"`, because a mise-shimmed `git` creates the dir and would read as drift
inside `tmp_path` (the docstring says so). Rewrite `:17-19`: `… creates the SIBLING dir tmp_path.parent /
f"{tmp_path.name}.mise-state" (not inside tmp_path: a mise-shimmed git creates it, which reads as drift in
empty-tmp-dir / clean-repo tests) and sets MISE_STATE_DIR …`; same for `:53-54`.

**K3 — Trust handling contradicts itself and the code.** `:27-28` says "the host's trust setting must stay shared";
`:40-41` says isolation isolates trust and prescribes per-test `MISE_TRUSTED_CONFIG_PATHS=<its tmp dir>` "never a broad
trust". Shipped #819 does neither: the fixture SYMLINKS the whole ambient `trusted-configs` store into every test's
state dir (conftest `ambient_trust.symlink_to`), and only the eval control arm uses `MISE_TRUSTED_CONFIG_PATHS`
(`eval_cases.py`, `_redaction_collision_control`), which §2 (`:20-24`) does not mention. Rewrite §4 bullet 2: `MISE_STATE_DIR
also moves trust records (trusted-configs). The test fixture therefore symlinks the ambient trusted-configs store into
the isolated dir (tracking isolated, trust shared — #819). The production eval control arm instead gets its own
MISE_TRUSTED_CONFIG_PATHS=<its temp dir>, so it stays ARMED on a host with no ambient trusted_config_paths.` and add
`MISE_TRUSTED_CONFIG_PATHS` to the §2 eval_cases bullet.

**K4 — Is the FAIL arm done, and is PREMISE 7 confirmed?** `:55-56` "actually executed by the architect" and `:84`
(Kind A, "re-grep to confirm") have no recorded outcome in the spec. A fresh session cannot tell if they are owed.
Append a `## 8. Verification record` with the arm's observed rc (both directions) and the premise-7 re-grep result, or
cite where they are recorded (the #818/#819 commit bodies record the #819 trust arms only).

### D. `typos.toml` and test-docstring prose

**D1 — `typos.toml` comment calls `50ba9eec` "the research-fanout commit".** It is a pre-squash commit on
`feat/research-fanout`, not reachable from main (see P7). Rewrite: `# `50ba9eec` is a pre-squash commit on branch
feat/research-fanout (squashed into e5ac3324, #1391) that the 2026-09-26 cold review and codex review lens were run
against; …`. Minor: `HOMEs` sits under `[default.extend-identifiers]`, so it is allowlisted repo-wide, not only in the
one verbatim report the comment names — say "allowlisted repo-wide (exact identifier)".

**D2 — dotfiles `tests/conftest.py` docstring: "Same fixture as knowledge-base#818."** The trust-store symlink it
carries came in knowledge-base#819, not #818. Rewrite: `Same fixture as knowledge-base#818 + #819 (trust-store share).`

### G. Unstated owner / next step

**O1 — knowledge-base#509 (`aggregated-research`) is still OPEN and nothing says what happens to it.**
`gh issue view 509 -R ray-manaloto/knowledge-base` → OPEN (control: dotfiles#1169 → CLOSED, so the probe reads state).
The dotfiles skill now covers the same ask; neither the spec, the skill, nor #509 records a disposition or owner. Next
step: comment on #509 with Ray's 2026-09-26 ruling and either close it as superseded-in-dotfiles or narrow it to the
knowledge-base breadth verbs (#581/#582) — Ray's call (clarify-before-acting: ask, recommending "narrow").

## Scope notes

- Verbatim agent reports and raw sources added in the range (`docs/research/kb/reports/agents/*-2026-09-26.md`,
  `docs/research/kb/raw/research-sweep-trigger-eval-2026-09-26.md`) were read as evidence only and NOT audited for
  rewrites: `agent-artifact-conventions.md` rule 8 ("Do not normalize records"). Test files were read only where their
  docstrings are prose a reader relies on (D2).
- `mise.toml` `[tasks.research-fanout]` (+5 lines) matches spec §2 exactly — no finding.
- `.agents/skills/research-sweep/SKILL.md` is byte-identical to the `.claude/` copy (`diff` rc=0) and gated by
  `skills_mirror_parity`, so every S-finding applies to both; edit the `.claude/` copy and regenerate the mirror.
- Probes and their control arms: SHA reachability (`merge-base --is-ancestor` 50ba9eec/0a908d9e/cbaa1c97 → rc=1;
  e5ac3324 → rc=0); `firecrawl scrape --help` contains `-f, --format` (the skill's flag is VALID; control
  `--only-main-content` also found); issue state (#509 OPEN vs #1169 CLOSED); CLAUDE.md `grep -c` for the two
  workflow names → 0 while `.claude/workflows/` lists four files.

## Priority

1. **W4** (name collision — the skill's primary path may not reach the workflow) and **S1** (unasked Opus-bearing run).
2. **P1 / K1** (stale status lines make shipped specs read as open work orders) and **K3** (trust contract contradicts
   code in both directions).
3. **P2–P5, P10, K2, S4, S9, W1** (spec/skill vs code contradictions a lane would act on).
4. The rest (undefined terms, unlabelled numbers, dangling SHAs, list staleness).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited range `12a34e88..ffd13b0d`; commit
  reachability of review SHAs via `gh api repos/…/commits`; issues #1169/#1248 state.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `docs/plans/mise-state-isolation-spec.md`
  and #818/#819 diffs; issue #509 state; offline `sources/agent-harness-docs/docs/claude-code/workflows.md` (`:203`).
