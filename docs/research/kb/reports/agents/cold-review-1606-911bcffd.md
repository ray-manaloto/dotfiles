# Cold review — 911bcffd (base e2f49ccd)

- Subject: `911bcffdf70e8b64c746724bea4c4c98fe40b0d5` "fix(hooks): deny EnterWorktree paths outside .claude/worktrees (#1606)"
- Base: `e2f49ccdcb9a986754f7319355db051a8ac124ef` (merge-base == base; single commit)
- Worktree: `.claude/worktrees/fix-1606` (HEAD == subject)
- Reviewer: cold-reviewer (Opus), diff-only, no ticket read, no gates run (per caller)
- Status: COMPLETE
- **Verdict: SHIP-WITH-FIXES** (F1-F3 MEDIUM; no HIGH; the guard is strictly better than base, which had none)

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | The guard ALLOWS any `path` lexically inside `<main>/.claude/worktrees/` even when it does not exist / is not a registered worktree, but Claude Code's `checkPermissions` PROMPTS for exactly that (realpath ENOENT → `vMr` catch → null → `behavior:"ask"`), so the #1606 park survives in that cell; the tests pin the allow as correct (`foo` never exists in the fixture), and the deny message's last clause ("only `EnterWorktree path=<allowed>/<name>` works", no "existing") steers a worktree-session model straight into it | `python/src/dotfiles_setup/worktree_guard.py:44-50`, `:55-56`; `tests/test_worktree_guard.py:80-85`, `:93-94` | E1, E2 row P1; repo's own `.claude/types/claude-code.d.ts:12440` ("Path to an EXISTING worktree… Must appear in `git worktree list`"); `$CC/agent-sdk__typescript.md:2941`. Binary-derived, not live-armed (no EnterWorktree tool in this lane) |
| F2 | MEDIUM | Relative `path` and the repo anchor are resolved against `CLAUDE_PROJECT_DIR`, which STAYS at the session start root, while Claude Code resolves against the session's CURRENT cwd (the payload `cwd`, which follows EnterWorktree and `cd`). `dispatch` discards that payload (`_`). Result: fail-open (P3: cwd `<main>/python`, `path=.claude/worktrees/a` → guard ALLOW, CC ask) and over-deny (P2: cwd in worktree b, `path=../a` → guard DENY, CC allow); a cwd in another repo gets the wrong managed dir entirely. `test_resolves_relative_paths_against_project_dir` passes the worktree AS project_dir, an input production never sends for a session that EnterWorktree'd | `python/src/dotfiles_setup/hook_dispatch.py:49`, `:56`; `python/src/dotfiles_setup/worktree_guard.py:29`, `:42-43`; `tests/test_worktree_guard.py:88-96` | E1 (`$u(oe(), e)`), E2 rows P2/P3; `$CC/hooks.md:626-629`, `$CC/worktrees.md:46-49` |
| F3 | MEDIUM | The edited coordinator-handoff step is not executable as written: it now writes the handoff branch in an `EnterWorktree name=` worktree but still says `mise run ship` "from the main checkout". In an EnterWorktree session Claude Code blocks Bash whose cwd is the main checkout and any `git -C`/`cd` redirect into it, and git refuses to check out the worktree-held branch in main; no ExitWorktree / `git switch --detach` step is given. A docs-only handoff ships fine from the worktree itself (ship only refuses a linked worktree when `needs_full_sync`). Same text in the `.agents` mirror | `.claude/skills/coordinator-handoff/SKILL.md:45-54`; `.agents/skills/coordinator-handoff/SKILL.md:45-54` | E5: `$CC/worktrees.md:83-95`; `python/src/dotfiles_setup/pr.py:598`, `:612`, `:619` |
| F4 | LOW | New sentence "The coordinator's own edits use `EnterWorktree name=` from the main checkout" puts the coordinator in an isolated worktree session, after which the very next block of the same section (`git -C <repo> worktree add …`) is a git redirect into the main checkout that Claude Code blocks; no ExitWorktree step | `.claude/skills/parallel-work-split/SKILL.md:87` (+ `:101-103`); `.agents/skills/parallel-work-split/SKILL.md:87` | `$CC/worktrees.md:89-91` ("Git redirects … through `git -C`") |
| F5 | LOW | Deny reason clause "External paths raise a permission prompt that parks --bg coordinators" is false under `bypassPermissions` (the one mode that skips the prompt); the guard never reads payload `permission_mode`, so it denies a call that would not have prompted. Acceptable if a uniform location policy is intended — then the reason should say so instead of citing the prompt | `python/src/dotfiles_setup/worktree_guard.py:53` | `$CC/worktrees.md:43`; `$CC/hooks.md:759` (`permission_mode` field) |
| F6 | LOW | `worktree_guard.handles()` has no production caller (dispatch inlines `tool_name == "EnterWorktree"`), yet the new contract makes `'def handles('` a required token — a contract binding a string with no consumer | `python/src/dotfiles_setup/worktree_guard.py:16-18`; `python/src/dotfiles_setup/hook_dispatch.py:55`; `python/verification/suites.toml:1340` | E7 |
| F7 | LOW | Matcher went 8 → 9 tools but two prose sites still say eight; the `hook_guard` docstring now lists EnterWorktree in a sentence about what `hook_guard` dispatches, though only `hook_dispatch` routes it | `docs/rules-evidence/mise-tasks-only.md:126`; `tests/TEST-INDEX.md:55`; `python/src/dotfiles_setup/hook_guard.py:33-37` | E6 |
| I1 | INFO | "a relative path from a worktree returned rc 2 on 2026-10-03" is a historical incident claim — UNVERIFIED here; consistent with `handoff.is_file()` → rc 2 "does not exist" | `.claude/skills/coordinator-handoff/SKILL.md:65-66` | `python/src/dotfiles_setup/coordinator_handoff.py:805-806` |

## Evidence log

### E1 — Claude Code's own "managed path" predicate (binary 2.1.288, decompiled; docs corpus bound 2.1.257)

`EnterWorktree.checkPermissions` (binary offset ~194788625): no `path` → allow;
`n = await vMr(path)`; `n?.managed` → allow with `path: n.targetReal`; otherwise
`behavior:"ask"` with reason "permission-root relocation … a model-supplied worktree
outside .claude/worktrees/", `classifierApprovable:false`.

`vMr` (offset ~188109920): `r = oe()` (current cwd: `function oe(){try{return gKt()}catch{return Ee()}}`),
`b = await kl($u(r, e))` where the module imports `realpath as kl` from `fs/promises` and
`resolve as $u` from `path`. Whole body is in `try{…}catch{return null}`. Managed iff
`K = join(root,".claude","worktrees")` is not a symlink (`bB(realpath(K),K)`) and `J2(K,b,{strictly:true})`.

So CC's predicate = realpath(resolve(**cwd**, path)) **exists** AND is strictly under
`<root>/.claude/worktrees` (root inferred = canonical/main checkout: the subagent message branch
`n!==s && n.startsWith(s+sep)` only makes sense if `Es(cwd)` is a strict prefix of a worktree cwd;
docs `worktrees.md:41` "switch directly to another one under `.claude/worktrees/`").

Docs: `$CC/hooks.md:621-629` / `worktrees.md:46-49` — `${CLAUDE_PROJECT_DIR}` STAYS at the session
start root; the payload `cwd` field follows EnterWorktree and `cd`.

### E2 — guard decision table vs CC (fixture `/tmp/cr1606.*`, guard loaded from the subject tree, `__file__` printed)

| Cell | guard | CC (E1) | Direction |
|---|---|---|---|
| CTRL abs existing sibling `repo.worktrees/sib` | DENY | ask | agree (control) |
| CTRL abs existing `<main>/.claude/worktrees/a` | ALLOW | allow | agree (control) |
| P1 abs NONEXISTENT `<main>/.claude/worktrees/new-lane` | ALLOW | realpath ENOENT → catch → null → **ask** | **fail-open** |
| P2 rel `../a`, CLAUDE_PROJECT_DIR=main, cwd=`<main>/.claude/worktrees/b` | DENY | resolves to managed `a` → allow | over-deny |
| P3 rel `.claude/worktrees/a`, CLAUDE_PROJECT_DIR=main, cwd=`<main>/python` | ALLOW | `<main>/python/.claude/worktrees/a` ENOENT → **ask** | **fail-open** |

Controls discriminate (one DENY, one ALLOW), so the probe can produce both answers.

### E3 — strict `per_path_tokens` replay over the whole suites.toml (subject tree)

1406 tokens checked, **0 fails**. Control arm: BASE suites.toml tokens against SUBJECT files → exactly 3
expected fails (`workflow.ask-quality-enforcement` ×2, `workflow.branch-write-guard-wiring` ×1 — the old
`…|Glob"` / `…|Glob\`` matcher tokens), so the replay discriminates.

### E4 — `.agents` mirrors

`.agents/skills/{coordinator-handoff,parallel-work-split}/SKILL.md` are real blobs (100644), not symlinks.
`diff` vs the `.claude` copies at the subject shows only the known PER_FILE reversions
(`.claude/`→`.agents/` self-paths, "Ask Claude"→"Ask Codex"). Mirror is current.

### E5 — Claude Code worktree isolation vs the edited coordinator-handoff flow

`$CC/worktrees.md:83-95`: while a session is isolated in a worktree (incl. after `EnterWorktree`), CC blocks
Bash whose cwd resolves to the main checkout and any `git -C`/`cd` redirect into it.
`python/src/dotfiles_setup/pr.py:598-626`: ship ships `_current_branch(workspace)`; the comment at :619
records "Git refuses to check out a branch another worktree holds". Ship refuses a linked worktree ONLY
when `needs_full_sync(paths)` (:612) — a docs-only handoff ships fine from the worktree.
`git grep ExitWorktree` over `.claude/skills .claude/rules .agents/skills docs/specs` at the subject:
only the lane brief at parallel-work-split:143 ("Do NOT … call EnterWorktree/ExitWorktree"); the
coordinator path never mentions ExitWorktree.

### E6 — stale prose (not gated)

`git grep -nP 'NotebookEdit\|Grep\|Read\|Glob(?!\|EnterWorktree)'` → only `.codex/hooks.json:5` (codex has no
EnterWorktree tool; not a defect). "eight-tool" survives at `docs/rules-evidence/mise-tasks-only.md:126` and
`tests/TEST-INDEX.md:55` ("over the merged hook's eight tools").

### E7 — `handles()` callers

`git grep 'worktree_guard\.'`: production calls only `worktree_guard.decide` (`hook_dispatch.py:56`; dispatch
uses an inline `tool_name == "EnterWorktree"` at :55). `worktree_guard.handles` is called only by
`tests/test_worktree_guard.py:47`, and suites.toml:1340 binds `'def handles('` as a required token.


## Required questions

### Q-FRESH (decision → action re-validated against fresh inputs?)

One pair: the guard's decision (PreToolUse) → Claude Code's own `checkPermissions`/`call`. The guard
reads `git rev-parse --git-common-dir` and `Path.resolve()` fresh on every call (no cache). It is deny-only,
so a stale or wrong decision can only be a stale ALLOW, which Claude Code then handles with its own
re-derived check (realpath at `checkPermissions`) — i.e. it degrades into the F1/F2 cells, not a new
TOCTOU. No separate freshness finding.

### Q-SCOPE

F1, F2: in scope (the #1606 guard predicate itself). F3, F4: in scope (lines this commit added). F5: in
scope but may be a deliberate policy — if so, reword the reason (ticket only if the policy is contested).
F6, F7: in scope, cosmetic. I1: informational.

### Q-CLAIM — every clause this diff adds to an operator-facing string

| String / clause | Enforcing line | Holds? |
|---|---|---|
| reason: "EnterWorktree path={target} must be strictly inside {allowed}/" | `worktree_guard.py:49` | yes |
| reason: "External paths raise a permission prompt" | none (claim about CC) | true except `bypassPermissions` (F5); and its implied converse "inside ⇒ no prompt" is false (F1, F2) |
| reason: "that parks --bg coordinators" | none | incident claim, cited at `parallel-work-split/SKILL.md:120-121`; UNVERIFIED here |
| reason: "From the main checkout ({main}), use `EnterWorktree name=<name>`" | `:40` computes main from the common dir | yes (`$CC/tools-reference.md:31`) |
| reason: "From inside a worktree session, only `EnterWorktree path={allowed}/<name>` works" | none | incomplete — `<name>` must be an EXISTING registered worktree; omission feeds F1 |
| module docstring: "Permission allow rules cannot suppress the relocation prompt" | n/a | yes (`$CC/worktrees.md:43`) |
| selfcheck failure: "the #1606 guard is not reachable" | `hook_selfcheck.py` deny arm | yes |
| selfcheck failure: "deny lost its #1606 name= redirect" | token check `#1606` + `EnterWorktree name=` | yes |
| skill: "lands at `<main>/.claude/worktrees/…`" | CC creation path | yes |
| skill: "Ship it early … `mise run ship` from the main checkout" (now after an EnterWorktree) | none | not executable as written (F3) |
| skill: "`--handoff` must be an absolute path; relative returned rc 2 on 2026-10-03" | `coordinator_handoff.py:805-806` | UNVERIFIED history (I1) |

## What was NOT done (per caller)

No pytest, lint, verify or selfcheck run; no source edited. The only executions were read-only probes:
`git show/grep/diff`, an mmap scan of the installed Claude Code 2.1.288 binary, the token replay, and a
direct call of the SUBJECT's `worktree_guard.decide` on a scratch `/tmp` git fixture (global/system git
config isolated for fixture creation only). F1's Claude Code side is binary-derived, not live-armed.

## Suggested fixes (not applied)

- F1: allow only when the resolved target is a registered worktree (`git worktree list --porcelain`) or at
  least `is_dir()`; otherwise deny with "must be an EXISTING worktree; to create one, ExitWorktree then
  `EnterWorktree name=`". Flip `tests/test_worktree_guard.py:80-85,93-94` to existing targets and add the
  nonexistent-under-managed DENY arm.
- F2: thread the payload's `cwd` into `decide` (fallback `project_root`), anchor both the relative join and
  the `--git-common-dir` probe to it; give the selfcheck payload a `cwd`.
- F3: say "commit and `mise run ship` from the handoff worktree (docs-only, no full-sync)", or spell the
  ExitWorktree + `git switch --detach` + `git switch <branch>` sequence; keep the worktree alive until the
  successor has read `--handoff`.

## GitHub repos touched

_None._ (Local sources only: this repo at the subject ref, the knowledge-base offline Claude Code docs
corpus `$CC`, and the installed Claude Code 2.1.288 binary.)

## Memory

Memory was consulted (MEMORY.md + cc_doc_corpus, contract_token_and_mirror_replay, repo_gate_locations,
hook_guard_new_rule_corpus_replay). The post-review memory update was **blocked by the harness**
(`bgIsolation`: "This subagent's parent bg session hasn't isolated yet, so writes to the shared checkout
are blocked") — `.claude/agent-memory-local/cold-reviewer/` lives in the main checkout. Not bypassed. The
intended entry (`enterworktree_guard_review.md`) is reproduced in the hand-back for the coordinator.
