# Session-integrity review — vagueness lane (2026-10-01)

Method: `### Brief P` in `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md` (method only).
Scope: doc/plan/spec/rule/agent text changed by #1475 (`3a861923`), #1486 (`3a3ca862`), #1490 (`5d22d619`),
branch `fix/s29-00b-bot-pr-regenerate` (`git diff 5d22d619..HEAD` + `git diff --cached`), and `task_plan.md`
sections "2026-10-01 ORDER" / "2026-10-01 MODS PROGRAM". Verbatim agent reports are NOT normalized
(agent-artifact-conventions rule 8); they are read only as evidence.

Status: COMPLETE — see Summary.

## Findings

### V1 — HIGH — `task_plan.md` line-number anchors have rotted; "below" points ABOVE

- **Claim.** The Current Phase steers by bare line numbers that no longer name what they were written for. `:993/:997
  below` is written on line 1007 and points UP, at the "N0 DONE" bullet (993) and "RESTART this Claude Code session
  first" (997) — neither is the stale prose the sentence means to fix. `SUPERSEDES the :1021 order` lands on the
  "S29-H DONE" paragraph (1021), which carries no order at all. A fresh session cannot tell which order is superseded
  or which lines are stale.
- **Evidence.** `task_plan.md:991` ("SUPERSEDES the :1021 order"), `task_plan.md:1007` ("BEFORE hand-fixing :993/:997
  below"); targets read on disk: `:993` = "N0 DONE: research-enforcement #1475 MERGED", `:997` = "RESTART this Claude
  Code session first", `:1021` = "**S29-H DONE 2026-09-30 …**". The MODS block (`:996-1006`, 11 lines) was inserted
  above the anchors after they were written.
- **Control arm.** Same `sed -n` read shows the anchors' probable intended targets DO exist in the same file
  (`:1011` "IN FLIGHT: graphify 0.9.65 -> 0.9.73", `:1014` "IN FLIGHT (N0, …)"), so the probe can see stale prose —
  the anchors simply miss it.
- **Disposition: PLAN** (the plan's own `STILL OWED` line forbids a hand fix before the machine check; this audit
  must not edit `task_plan.md`). Exact text to replace `task_plan.md:1007`:
  > - STILL OWED: machine check for stale prose without `#NNNN` (delta §4) — it must flag, by CONTENT not line number,
  >   the 2026-09-30 QUEUE bullets "IN FLIGHT: graphify 0.9.65 -> 0.9.73" (landed #1467 `28a124a3`) and
  >   "IN FLIGHT (N0 …) research-enforcement" (landed #1475 `3a861923`); only then correct them. No bare `:NNN`
  >   anchors in this section — quote the bullet's first words. Codex lens >=2026-10-03.

  and replace "SUPERSEDES the :1021 order" in `:991` with "SUPERSEDES the 2026-09-30 QUEUE NEXT order and the
  2026-09-29b RULING order (S29-H → S29-0 → S29-00 → S29-K)".

### V2 — HIGH — the 2026-10-01 ORDER and the MODS PROGRAM give no combined sequence

- **Claim.** `:992` fixes the order `S29-00 -> N1a -> S29-0 -> N1 -> N2 -> N3 -> S29-K`. The MODS PROGRAM (`:996-1006`)
  says "RESTART first", and `:995` makes S29-00b (= the remainder of S29-00, head of the order) wait on MODS-D1. Where
  MODS-D0, D2, D3, the KB items, TELEMETRY and RESEARCH-SWEEP item 3 sit relative to N1a/S29-0/N1 is not stated.
  A fresh session can read "MODS first, all of it" or "D1 only, then the order" — two different weeks of work.
- **Evidence.** `task_plan.md:992`, `:995` ("Unblock = MODS-D1 rename below"), `:997` ("RESTART this Claude Code
  session first"), `:998-1005` (no ordering words between D0-D3/KB/TELEMETRY and the arrow chain).
- **Control arm.** The 2026-09-30 QUEUE (`:1012-1016`) DOES state order with `NEXT (N1)` / `NEXT (N2)` labels, so the
  plan's convention for order exists; the MODS block simply omits it.
- **Disposition: PLAN** (needs Ray's ordering ruling — not inferable). Exact text to replace `:992`:
  > RESTART (2.1.287) -> MODS-D1 (rename, unblocks S29-00b) -> S29-00b -> N1a (ty bump PR) -> [MODS-D0, D2, D3, KB,
  > TELEMETRY: POSITION OWED — ask Ray] -> S29-0 (pwf restructure) -> N1 github-watch -> N2 native CLIs -> N3
  > code-intel -> S29-K.

### V3 — HIGH — stale-mise-PATH work dropped from the order without a disposition

- **Claim.** Goal-history iteration 046's workflow is `research enforcement -> stale PATH (kb_setup hook-env) ->
  github-watch -> ty -> cbm -> native CLIs`. The 2026-10-01 ORDER has no stale-PATH step, yet the 2026-09-30 QUEUE
  still lists it as "IN FLIGHT … implementer PAUSED" with a worktree. Silently dropped or silently parked — the
  reader cannot tell, and no goal-history iteration records the order change (`goal-history.md` last entry is the
  2026-09-30 one; `.claude/rules/goal-history.md` requires one per accepted goal/order change).
- **Evidence.** `docs/agents/goal-history.md` (iteration 046 mermaid "stale PATH (kb_setup hook-env)"),
  `task_plan.md:992` (no PATH step), `task_plan.md:1015` ("IN FLIGHT: stale mise PATH … implementer PAUSED").
  `grep -n "^## 20" docs/agents/goal-history.md | tail -1` → `2009:## 2026-09-30 — session 7ad65526`.
- **Control arm.** `grep -n "stale mise PATH" task_plan.md` → 1 hit (`:1015`), so the grep sees the term; it is absent
  from the 2026-10-01 block, not mis-spelled.
- **Disposition: PLAN.** Add to the 2026-10-01 ORDER block:
  > - stale mise PATH (worktree `agent-shell-env-20260930`, sweep wf_963d1be9-095): POSITION OWED — Ray to rule
  >   whether it precedes N1a or is folded into N2 (native CLIs). Goal-history iteration 047 owed for the 2026-10-01
  >   order change (S29-00 split, N1a inserted, MODS program, stale-PATH disposition).

### V4 — MEDIUM — #1472 cited as the reason for #1486's exemption, yet still OPEN with no owner

- **Claim.** #1486 attributes its exemptions to #1472 in four places, and the plan marks #1486 "DONE", but #1472 is
  OPEN and the plan lists it only as an N0 "follow-up". A reader cannot tell whether #1486 closed it, partially fixed
  it, or is unrelated.
- **Evidence.** `.claude/CLAUDE.md:8` ("exempt too, so vendored mirrors stay byte-verbatim (#1472)"), `.gitleaks.toml`
  (#1486 header "Ray, 2026-10-01, AskUserQuestion; #1472"), `scripts/check-claude-md-stub.sh:16`, `hk.pkl:768-770`;
  `task_plan.md:993` ("Follow-ups #1471 #1472 #1473 #1474"), `task_plan.md:994` ("DONE: raw-mirror scan … #1486").
  `gh issue view 1472 --json state` → `OPEN` ("research-sweep-run mirrors in docs/research/kb/raw can block lint via
  betterleaks_verbatim_trees (F5)").
- **Control arm.** `gh issue view 1449` in the same loop returned `OPEN` and `#1471/#1473` `OPEN` — expected open — so
  the probe distinguishes nothing by itself; the discriminating fact is the PR body: `gh pr view 1486 --json body`
  contains no `closes`/`fixes #1472`.
- **Disposition: PLAN.** Replace `:993`'s "Follow-ups #1471 #1472 #1473 #1474" with:
  > Follow-ups #1471 #1473 #1474 OPEN; #1472 — #1486 shipped the allowlist + exemption half; owner to CLOSE it with
  > a comment citing `3a3ca862`, or state the remaining half here.

### V5 — MEDIUM — "TICKETS OWED (ask Ray)" still reads as owed after the tickets were filed

- **Claim.** The 2026-09-30 QUEUE still says five tickets are owed and need Ray; the 2026-10-01 ORDER says
  "#1477-#1482 filed" without saying they ARE those five. A fresh session will re-ask Ray or file duplicates.
- **Evidence.** `task_plan.md:1018` ("TICKETS OWED (ask Ray): `.miserc.toml` not honoured under `mise -C`;
  `sync.container_state` ignores docker rc; worktree sessions skip the arches check; ambient per-clone port pin leaks
  …; linked-worktree ship cannot pass sync-full"), `task_plan.md:1006` ("Tickets filed 2026-10-01: #1477 #1478 #1479
  #1480 #1481 #1482, KB#826"). `gh issue view`: #1477 ".miserc.toml (auto_env=false) is not honoured under `mise -C`",
  #1478 "sync.container_state ignores the docker exit code", #1479 "Worktree sessions skip the doctor
  devcontainer-arches check", #1480 "Ambient per-clone DEVCONTAINER_SSH_PORT pin … leaks into sibling worktrees",
  #1481 "MACHINE CHECK: `mise run ship` should refuse early from a linked worktree …" — a one-to-one match.
- **Control arm.** #1482 and KB#826 were fetched by the same loop and do NOT map to the owed list (Agent NATIVE-FIRST
  guard; currency engine for githubkit), so the probe distinguishes a match from a non-match.
- **Disposition: PLAN** (stale-prose machine check owed first, per `:1007`). Exact text for `:1018`:
  > - TICKETS FILED 2026-10-01 (were "owed"): #1477 (.miserc under `mise -C`), #1478 (container_state rc), #1479
  >   (worktree arches), #1480 (port-pin leak), #1481 (worktree ship vs sync-full).

  and `:1006` → "Tickets filed 2026-10-01: #1477-#1481 (the 2026-09-30 owed five), #1482 (Agent NATIVE-FIRST guard,
  decided AFTER N1/N2), KB#826 (currency engine for binaryless libs, N1 githubkit)."

### V6 — MEDIUM — 2026-09-30 QUEUE "IN FLIGHT" bullets contradict the 2026-10-01 DONE lines

- **Claim.** Two bullets still call landed work in flight, in the same Current Phase that says it is done.
- **Evidence.** `task_plan.md:1011` "IN FLIGHT: graphify 0.9.65 -> 0.9.73 currency PR" vs
  `docs/agents/goal-history.md` iteration 046 Evidence "graphify 0.9.73 #1467 (`28a124a3`)" (Landed);
  `task_plan.md:1014` "IN FLIGHT (N0 …): research-enforcement … Worktree `research-enforcement-20260930`" vs
  `task_plan.md:993` "N0 DONE: research-enforcement #1475 MERGED `3a861923`, landed rc=0".
- **Control arm.** `git merge-base --is-ancestor 3a861923 HEAD` → ANCESTOR (#1475 is in the branch base), so the
  DONE line, not the IN FLIGHT one, matches the tree.
- **Disposition: PLAN** (same as V1 — this is the stale prose the owed machine check must catch). Replacement text:
  > - DONE: graphify 0.9.65 -> 0.9.73, #1467 MERGED `28a124a3`.
  > - DONE (N0): research-enforcement, see the 2026-10-01 ORDER "N0 DONE" line.

### V7 — MEDIUM — MODS-D1 says "RENAME EVERYTHING" but names neither the new name nor the full rename set

- **Claim.** D1 is the unblocker for S29-00b, but a fresh session cannot execute it: the target name is not written
  (the Fable plan recommends `install-doctor`; the sweep proved `doctor-verdict` valid), and "plugin + mise task +
  python module" omits surfaces that carry the name — the `.agents/skills` mirror, the doctor check id referenced in
  `mise.toml:37` ("doctor's `claude-doctor` check (currency.toml:29-39)"), suites tokens, and tests.
- **Evidence.** `task_plan.md:999`; `docs/research/kb/reports/agents/claude-mods-refactor-plan-2026-10-01.md:60`,
  `:178` (option A `install-doctor`, "keep python module/doctor check names" — the opposite scope of "EVERYTHING");
  `docs/research/kb/reports/agents/claude-code-mods-2-1-287-sweep-2026-10-01.md:247` (`doctor-verdict` rc=0);
  `git ls-files | grep claude-doctor` → `.claude/skills/claude-doctor/…` AND `.agents/skills/claude-doctor/…`.
- **Control arm.** `claude plugin validate` arms in the sweep (`:247`): `claude-doctor` rc=1, `doctor-verdict` rc=0,
  `myclaude-x` rc=0 — the reserved-name premise is armed both ways; only the plan text is underspecified.
- **Disposition: PLAN** (needs Ray's name). Exact text for `:999`:
  > - MODS-D1: RENAME every `claude-doctor` surface to `<NAME — Ray to pick: install-doctor (Fable rec.) |
  >   doctor-verdict>`: `.claude/skills/claude-doctor/` (+ `plugin.json` name, harness import), the `.agents/skills`
  >   mirror (`mise run skills-mirror`), the mise task, the python module + `main.py` subcommand, the doctor check id
  >   (`doctor.toml`, `currency.toml:29-39`, `mise.toml:37`), suites tokens, tests. Done = `claude plugin validate`
  >   rc=0 on the renamed dir AND `fnhook_gates` green. Unblocks S29-00b.

### V8 — MEDIUM — MODS-D2's "task in the dotfiles-managed `~/.config/mise/config.toml`" has no delivery path on the Mac

- **Claim.** The global mise config IS chezmoi-sourced (`home/dot_config/mise/config.toml.tmpl`), but `chezmoi
  apply` is blocked on this host, and the host's `~/.config/mise/config.toml` is a plain 33 KB file, not a link. A
  task added to the template never reaches the host — where the mod-exposure audit of the host's `claude` must run.
  The plan does not say who writes the host file or how (Ray? a sanctioned install step?), and the standing
  no-user-level-file-updates memory forbids an agent doing it unasked.
- **Evidence.** `task_plan.md:1000`; `AGENTS.md` "Chezmoi is devcontainer-only on this Mac"; `git ls-files home |
  grep mise` → `home/dot_config/mise/config.toml.tmpl`; `ls -la ~/.config/mise/config.toml` → regular file, 33111 B.
- **Control arm.** The same `git ls-files home | grep -i mise` would list nothing if the template were absent — it
  lists one path, so "dotfiles-managed" is true for the SOURCE; the gap is only the host apply.
- **Disposition: PLAN.** Append to `:1000`:
  > Delivery: the task ships in `home/dot_config/mise/config.toml.tmpl` (devcontainer via chezmoi); the HOST copy is
  > applied by `<owner — Ray, or the §5b #1014 installer once it exists>`; until then the audit runs as
  > `mise run <task>` from this repo, not from the global config.

### V9 — MEDIUM — the 225-page docs mirror is recorded as living in the session scratchpad

- **Claim.** The MODS PROGRAM header and its KB item cite a "225/225" Claude Code docs mirror "in scratchpad", which
  is session-scoped (`/private/tmp/claude-501/<project>/<session>/scratchpad`) and gone after this session. The KB
  refresh item reads as "copy it" when a fresh session must actually re-fetch.
- **Evidence.** `task_plan.md:996` ("docs mirror 225/225 in scratchpad -> KB corpus"), `task_plan.md:1002` ("refresh
  `sources/agent-harness-docs/docs/claude-code` from the 225-page native-.md mirror").
- **Control arm.** N/A for disk presence (the auditor cannot see another session's scratchpad); the defect is that
  the plan names no durable path at all — `grep -n "225" task_plan.md` shows no path beside either mention.
- **Disposition: PLAN.** Replace "docs mirror 225/225 in scratchpad -> KB corpus" with:
  > docs mirror 225/225 was built in session scratchpad (NOT durable) — the KB item below RE-FETCHES it; or promote it
  > now to `<KB path>` and cite that path here.

### V10 — LOW — PARKED line's `refresh.yml:357` anchor is already wrong in the staged tree

- **Claim.** "Old `continue-on-error` at refresh.yml:357 (#887) awaits Ray's ruling" — line 357 is right only at
  `HEAD`; the staged round c moves it to 360, and the commit will make the plan point at the wrong line.
- **Evidence.** `task_plan.md:995`; `git show HEAD:.github/workflows/refresh.yml | grep -n continue-on-error` → `357`;
  working tree → `360` (`id: drift-check` step).
- **Control arm.** Both greps ran the same pattern against two revisions and each returned exactly one live
  `continue-on-error:` key line — the discriminating difference is the revision.
- **Disposition: PLAN.** Replace "refresh.yml:357" with "refresh.yml `image-lock-pr` step `id: drift-check`".

### V11 — MEDIUM — staged `refresh.yml` says the job's scope is "ONLY the two image locks", then adds a second half

- **Claim.** The job banner keeps the pre-S29-00b sentence "Scope is deliberately narrow: ONLY the two image locks"
  and, seven lines later, says "a second half of this job owns two more". A reader (or a reviewer checking
  `ci.image-lock-pr-wired`) gets two contradictory scopes in one comment block.
- **Evidence.** `.github/workflows/refresh.yml:244` ("Scope is deliberately narrow: ONLY the two image locks") vs
  `:251-253` ("S29-00b … a second half of this job owns two more"); the same `:244` line is at `HEAD` too, so it was
  correct before the branch and became stale through it.
- **Control arm.** `git show HEAD:… | grep -n "S29-00b (#1449; Ray"` → `251`, i.e. the branch's own addition is
  present in the probed revision; the probe can see the new half, so the "ONLY" sentence is genuinely co-resident.
- **Disposition: FIX-NOW** (branch-owned text, uncommitted round c). Replace `:244` opening with:
  > `# The IMAGE-LOCK half's scope is deliberately narrow: ONLY the two image locks, via`

### V12 — MEDIUM — an implementer self-ACCEPTED a cold-review LOW that can commit codex upstream churn

- **Claim.** The `artifact-drift` comment records "ACCEPTED limitation: an error INSIDE either CLI also exits 1 and
  reads as drift … a schema refresh can carry codex upstream churn into this PR's commit." No owner is named; the
  acceptance originates in the implementer report, not a Ray ruling. Under the zero-skip policy (rule 1/4) an
  acceptance needs user approval or an issue. A fresh reader takes "ACCEPTED" as ruled.
- **Evidence.** `.github/workflows/refresh.yml:536-541`; `docs/research/kb/reports/agents/implement-s29-00b-2026-10-01.md:148-149`
  ("documented as ACCEPTED in the `artifact-drift` comment"); `docs/research/kb/reports/agents/cold-review-s29-00b-2026-10-01.md:24`
  (F4) and `:62` (F2 "Alternatively, record the coupling explicitly as an accepted trade-off" — a reviewer option,
  not a ruling).
- **Control arm.** `grep -n -i "accepted" task_plan.md` region `:991-1007` returns no S29-00b acceptance — the plan
  records Ray's other rulings there (e.g. "(Ray)" on D0-D3), so a ruling would have been visible.
- **Disposition: PLAN** (needs Ray; then FIX the comment). Add to the PARKED S29-00b bullet (`task_plan.md:995`):
  > Ruling owed before ship: cold-review F4 — a transient in-CLI error reads as drift and can commit codex upstream
  > churn; refresh.yml's `artifact-drift` comment says "ACCEPTED" without a ruling. Ray: accept (comment gains
  > "(Ray, <date>)") or ticket the fix.

### V13 — LOW — "`schema-refresh` below" reads as a mise task that does not exist; "NOT_ADOPTED" undefined there

- **Claim.** "It runs the SAME producers `mise run hk-audit` and `schema-refresh` below use" mixes a mise task with a
  JOB name; there is no `schema-refresh` mise task (the producer is `schema-vendor-refresh`). "a NOT_ADOPTED audit
  failure" uses a python constant name with no gloss in a workflow comment.
- **Evidence.** `.github/workflows/refresh.yml:257-260`; `mise.toml:1475` `[tasks.schema-vendor-check]`, `:1479`
  `[tasks.schema-vendor-refresh]` (no `schema-refresh` task); `refresh.yml:650` job `schema-refresh:` running
  `mise run --skip-tools schema-vendor-refresh`; `NOT_ADOPTED` defined at `python/src/dotfiles_setup/hk_builtins_audit.py:75`.
- **Control arm.** The same `grep -n '^\[tasks\."\?schema'` found both `schema-vendor-*` tasks, so it can see schema
  tasks; `schema-refresh` is genuinely only a job.
- **Disposition: FIX-NOW** (staged branch text). Replace with:
  > `# fails on a bump). It runs the SAME producers as \`mise run hk-audit\` and the \`schema-refresh\` job below`
  > `# (\`mise run schema-vendor-refresh\`). The image-lock half commits and pushes FIRST,`
  > … `install, a network fetch, an audit failure on an un-dispositioned builtin (hk_builtins_audit.NOT_ADOPTED))`

### V14 — LOW — `.github/workflows/AGENTS.md` says `image-lock-pr` regenerates "`schemas/`"; it regenerates only the vendored writer set

- **Claim.** The table row says the job regenerates "`schemas/`", but the confine step's own comment says "Nothing
  broader -- schemas/ also holds repo-authored contract schemas no producer writes", and the writer set includes
  `.claude/types/claude-code.d.ts`, outside `schemas/`.
- **Evidence.** `.github/workflows/AGENTS.md:18`; `.github/workflows/refresh.yml:573-578` (confine comment).
- **Control arm.** N/A — a wording comparison of two lines this branch wrote.
- **Disposition: FIX-NOW.** Replace "regenerates image locks, hk audit, `schemas/` on Renovate PRs (S29-00b)" with:
  > regenerates the image locks, `docs/hk-builtins-audit.md` and the vendored schemas in `schemas/sources.toml`
  > (incl. `.claude/types/claude-code.d.ts`) on Renovate PRs (S29-00b)

### V15 — LOW — root `AGENTS.md` lists two stub/pairs exemptions; #1486 added a third

- **Claim.** "Two exceptions worth knowing" omits `docs/research/kb/raw/**`, now exempt from both
  `claude_md_import_stub` and `claude_agents_md_pairs`. A codex lane (which never loads `.claude/CLAUDE.md`, where
  the exemption IS stated) would believe a mirrored `CLAUDE.md` must be stubbed.
- **Evidence.** `AGENTS.md:59-61`; `scripts/check-claude-md-stub.sh:15-16`, `scripts/check-claude-agents-md-pairs.sh:16-17`,
  `.claude/CLAUDE.md:7-8`. `wc -c AGENTS.md` → 11937 of the 12,000 AGM-003 ceiling (63 chars headroom).
- **Control arm.** `grep -n "Two exceptions" AGENTS.md` → 1 hit (`:59`); the phrase the fix would replace exists once.
- **Disposition: FIX-NOW** (fits the budget; +~45 chars). Replace "`.claude/` has its own `CLAUDE.md` and is exempt
  from the stub check;" with:
  > `.claude/` has its own `CLAUDE.md` and is exempt from the stub check (so is `docs/research/kb/raw/**`, #1486);

  then re-run `mise run lint-docs` and `md_size_budget`. If the budget fails, PLAN instead (Phase: md-budget trim).

### V16 — LOW — research rule header says items 2-4 are "enforced", true only on the Workflow path

- **Claim.** `## Always (… items 2-4 enforced by the research-sweep-run workflow …)` can be read as "the repo
  enforces these". The in-lane path (codex lanes, headless runs: `mise run research-fanout`) has no enforcement — the
  skill only instructs it. A codex lane reading the header may assume a gate will catch an omission.
- **Evidence.** `.claude/rules/research-doc-sources.md:9`; `.claude/skills/research-sweep/SKILL.md` "No Workflow tool
  (a codex lane, a headless run) … run the in-lane steps below yourself" + in-lane step 1 ("Always run `--sources …`").
- **Control arm.** `docs/specs/research-enforcement-2026-09-30.md:18-19` changes `research_fanout.py` only for
  `--list-sources` labelling — no mandatory-stage check was added to the fan-out CLI, so the in-lane path is
  genuinely unenforced.
- **Disposition: FIX-NOW** (eager rule; re-run `mise run lint-docs`, `md_size_budget`, `mise run rule-sync`).
  Replace the heading with:
  > `## Always (Ray, 2026-09-30 — items 2-4 are machine-enforced only inside the \`research-sweep-run\` workflow; in-lane and item 1 rely on this rule)`

### V17 — LOW — the research-enforcement spec carries no status and describes pre-review behaviour as the design

- **Claim.** The spec still reads "Today three sweeps silently skipped …" and specifies "a must-hit control query",
  while the shipped design (four review rounds) split it into a workflow `health` control, a planner-or-README
  must-hit, and an existence check. A fresh session treating `docs/specs/` as the design of record will rebuild or
  "fix" toward the superseded shape.
- **Evidence.** `docs/specs/research-enforcement-2026-09-30.md:10`, `:28-29`; shipped shape in
  `.claude/skills/research-sweep/SKILL.md` "Three mandatory stages" paragraph (health role, README control,
  `gh api -i repos/<r>`), PR #1475 round-3/4 commit messages (R1-R3).
- **Control arm.** N/A — a text comparison of two tracked files.
- **Disposition: FIX-NOW.** Insert after the title:
  > **Status: SHIPPED in #1475 (`3a861923`).** §2's code-search clause was refined in review rounds 2-4: the as-built
  > contract (health control, planner-or-README must-hit, per-repo existence check) lives in
  > `.claude/skills/research-sweep/SKILL.md`; follow-ups #1471 #1473 #1474.

### V18 — LOW — generated `.agents` mirror renders "(Codex, codex, cursor)"

- **Claim.** The skills mirror's blanket `("Claude Code", "Codex")` rewrite turns "harness behaves (Claude Code,
  codex, cursor)" into "(Codex, codex, cursor)" — the reader loses which harness docs directory to grep (the path
  segment `<tool>` is `claude-code`). Pre-existing (`9f5bd67a`), but in a file #1475 regenerated.
- **Evidence.** `.agents/skills/research-sweep/SKILL.md:92`; `python/src/dotfiles_setup/skills_mirror.py:124`;
  `git log -S'harness behaves (Claude Code, codex, cursor)'` → `9f5bd67a`.
- **Control arm.** `diff .agents/… .claude/…` reported exactly ONE differing line (92), so the diff probe sees
  mirror drift and this is the only one in this file.
- **Disposition: PLAN** (fix the CLASS in the generator, not this instance). Task-plan text:
  > - skills_mirror: the `("Claude Code", "Codex")` rewrite garbles lists naming both harnesses (e.g.
  >   research-sweep in-lane step 0 → "(Codex, codex, cursor)"). Add a rule/exception + a test asserting no mirror
  >   line contains "Codex, codex"; regenerate.

## Not findings (checked and clean)

- `renovate.json` `packageRules[0]`/`[7]` index citations (#1490/S29-00b descriptions) still point at the described
  rules after the S29-00b insert (`jq '.packageRules|to_entries'`: [0] image-build inputs, [7] pixi/rumdl/agnix
  depName trap). Index citations remain fragile, but none is wrong today.
- `renovate.json` jdx/mise rule's "schemas/sources.toml's mise schema reads its pin from action.yml" — confirmed
  `schemas/sources.toml:23` `pin_source = ".github/actions/setup-mise/action.yml"`.
- `schema_vendor.py` docstrings (two CI callers) match `refresh.yml` (`schema-refresh` job `:650`, `image-lock-pr`).
- `python/AGENTS.md` msgspec scope note and `docs/specs/research-fanout.md` `--list-sources` states are consistent
  with each other.
- `docs/agents/goal-history.md` iteration 046 "(this PR)" is append-only history; not rewritable (goal-history rule).
- The injected session copy of `research-doc-sources.md` lacked the "Always" block, but the tree has it at `:9`; this
  is a stale session load, not a tree defect.

## Summary

| Disposition | Count | IDs |
|---|---|---|
| FIX-NOW | 6 | V11, V13, V14, V15, V16, V17 |
| PLAN | 12 | V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V12, V18 |
| Total | 18 | HIGH 3 (V1-V3), MEDIUM 8 (V4-V9, V11, V12), LOW 7 (V10, V13-V18) |

Status: COMPLETE.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited diffs; issues #1449 #1471-#1474
  #1477-#1482 and PR #1486/#1490 bodies read via `gh`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issue #826 state/title read via `gh`.
