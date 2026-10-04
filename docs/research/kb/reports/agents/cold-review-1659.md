# Cold review: 36ab6bba (PR #1659, docs/handoff 2026-10-04c) vs parent 60113afe

Status: COMPLETE

Write location: the requested path `docs/research/kb/reports/agents/cold-review-1659.md` was REFUSED by the
harness ("This subagent's parent bg session hasn't isolated yet, so writes to the shared checkout are blocked").
This report lives at `/tmp/cr-1659/cold-review-1659.md`; the coordinator must persist it. For the same reason
nothing was appended to `findings.md`/`progress.md`.

Scope: bugs only. That means factual errors (SHAs, PR numbers, paths, and commands that would fail or mislead
a successor) and contradictions with repo rules. Doc text is cited from `git show 36ab6bba:<path>`. Code facts
come from a scratch `git worktree add --detach /tmp/cr-1659/wt 36ab6bba`, which has since been removed. Memory
was consulted (`review_method`, `handoff_claim_checker_review`, `doc_sweep_review_patterns`,
`vendored_tree_and_workflow_order_review`).

Verdict: no SHA, PR# or issue# in the diff is wrong. That makes the handoff's own claim at `:122` ("Every
SHA, PR# and Ray answer above was verified correct") hold. There is 1 MEDIUM and 4 LOW, and all five are
claims about gate or command behaviour or about status.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| 1 | MEDIUM | The ship-location rule "Branches that touch session tooling or the image ship from the main checkout" gets the `needs_full_sync` predicate wrong in BOTH directions. Session tooling is not in `SURFACE_PATTERNS`, so handoff PR1 (89f6ce99) can ship from its worktree. rgs (291e0d15) and credit-fallback (e90833fd) are neither session tooling nor image, yet both get rc 2 from a worktree because they touch `mise.toml`. The handoff gives neither of them a ship location. bgisolation hit rc 2 through `python/verification/suites.toml`, not through its hook-guard or session files. The audit's F3 "second hazard" ("PR1 touches coordinator_handoff/session_start" so it ships from MAIN) repeats the wrong premise. | `docs/handoffs/session-2026-10-04c.md:93`; `docs/research/kb/reports/agents/handoff-audit-2026-10-04c.md:24` | I ran the real `dotfiles_setup.pr.needs_full_sync`, imported from the 36ab6bba worktree, over each branch's `git diff --name-only $(git merge-base origin/main REF) REF`. That uses the same three-dot semantics as `changed_paths_vs_main` (`pr.py:312-320`). Results: 89f6ce99 False (0 surface hits); c3569d61 True (`python/verification/suites.toml` only); 291e0d15 True (`mise.toml`); e90833fd True (`mise.toml`); 4a6ee2ab True; f9b56da5, 703e5612, b07ebd7b, 14a02f76, b79654d4 and ccf6234c False; b0774dc1, e078c542 and 15c1061d True (these three agree with the handoff's "from MAIN"). Controls: `.devcontainer/devcontainer.json` gives True and `docs/x.md` gives False. `SURFACE_PATTERNS` is `pr.py:99-120` and names no coordinator_handoff, hook_guard or session_* path. The refusal is at `pr.py:612-627` and returns `_RC_LINKED_WORKTREE` (=2, `:572`). `needs_full_sync` is also False for base-image-input diffs (`pr.py:283-290`), so "or the image" is only partly true. |
| 2 | LOW | "The ask-quality hook requires a backticked path, `#NNN` or URL in EVERY option" is false. The citation check runs once per QUESTION over one corpus: the question, the header, and every option's description and preview. The `[no prior evidence]` escape also satisfies it. Only `PRO:`/`CON:` are checked per option. This "trap reconfirmed" teaches a rule the gate does not have. | `docs/handoffs/session-2026-10-04c.md:110` | `_citation_corpus` (`ask_quality.py:119-124`) joins all the parts. `_check_question` runs `_CITATION_RE.search(corpus)` once (`:182-183`). Arms on the real `find_violations`: a citation in option 1 only gives 0 violations; a citation only in the question text gives 0; no citation anywhere (control) gives 1 "no citation" violation. The code matches `.claude/rules/clarify-before-acting.md` rule 2 ("Every question carries … A citation"). |
| 3 | LOW | Successor correction F2 is already stale in this commit. It still treats 0ca4b234 as unsettled: "persist its output", "do not remove this worktree until it is settled and persisted". That run settled at 06:15:58 CDT, before the ~06:30 corrections were written, and this commit persists its output. 0087b182 got a "settled" subsection and a "These go to Ray" line; 0ca4b234 got neither, so its verdict and its Proposal 1+3 recommendation never reach the handoff. Also, once the doc is on main, "THIS worktree's `.agent/sdlc-runs/`" reads as the main checkout, and 0ca4b234 does not exist there. | `docs/handoffs/session-2026-10-04c.md:131-134` | `.claude/worktrees/handoff-2026-10-04c/.agent/sdlc-runs/0ca4b2340ddb4d9ea0b53001bfd79c22/settlement.json` has `status=failed`, `finished_at=2026-10-04T11:15:58Z`, `duration_s=720.97` and `codex_returncode=0`. `ls` of the main checkout's `.agent/sdlc-runs/` shows only 0087b182. The persisted copy is `docs/research/kb/reports/agents/sdlc-team-review-retire-vs-harness-ship-0ca4b234.md` in 36ab6bba. Handoff `:154-163` covers 0087b182 only. |
| 4 | LOW | The committed codex-lane diagnosis states ROOT CAUSE A in the present tense ("CONTEXT7_API_KEY is NOT in this profile", `config.toml:90-95`). The fix had been applied, with Ray's approval, 43 min before the commit, and neither the report nor the handoff says so. A successor reading the report would think the fix is still owed. Persisting the report verbatim was correct, but `agent-report-persistence.md` rule 4 asks for a decision annotation AFTER the report, and none was added. The report also calls `.codex/config.toml` a "repo" file. It is gitignored (`.gitignore:59 .codex/*`), so it is machine-local and no PR can fix it. | `docs/research/kb/reports/agents/codex-lane-research-keys-diagnosis-2026-10-04.md:5,17,40` | A names-only scan of `~/.config/fnox/config.toml` shows `[profiles.codex_research.secrets]` at :90, now listing CONTEXT7_API_KEY at :95 (the range is now 90-96). File mtime is 06:19:39 CDT. Successor transcript `e67105a8-807e-4b1c-b60b-d19511058748.jsonl`: Ray approves at L484 (11:18:51Z), the edit is L499-500, and L543 reports "Context7 is fixed for codex lanes". The diagnosis was committed in 1e298cff at 07:02 CDT. `git check-ignore -v .codex/config.toml` points to `.gitignore:59`. |
| 5 | LOW | "Ticket it if it recurs" defers an uninvestigated change to a tracked lockfile with no ticket and no recorded approval. That contradicts `zero-skip-policy.md` rules 2 and 4. The +9 lines are real. The `linux-arm64-musl`, `linux-x64-musl` and `linux-x64-musl-baseline` zizmor platform blocks gained `url`s for the `*-unknown-linux-gnu` tarballs; whether that asset runs on musl is UNVERIFIED. The cause was never identified. | `docs/handoffs/session-2026-10-04c.md:63-66` | `diff <(git show abf75906:mise.lock) ~/.claude/jobs/1debf341/tmp/mise.lock.main-dirty` gives exactly 9 added lines: three checksum/url/url_api blocks naming `zizmor-{aarch64,x86_64}-unknown-linux-gnu.tar.gz`, under the musl platform headers (dirty copy ~L6713-6740). The diff against 4fdbac59 is also 9 lines. A tracker search for `repo:ray-manaloto/dotfiles musl` returns 12 hits, none about this (control: `zizmor` returns 24 hits). |

## Answered without a finding

- Q-SCOPE: all five findings are in scope (they are text this commit adds). I recommend tickets for none of them
  except #5's underlying lockfile anomaly, which should be a ticket per zero-skip rule 4.
- Q-CLAIM over the handoff's operator-facing commands: `gh pr list --head fix/coordinator-bgisolation-none --state all`,
  `claude rm <id>`, `kill -0 30424`, `mise run land -- 1656`, and handoff-inbox `plan-apply`/`queue-append`
  (subcommands of `[tasks.handoff-inbox]`, `mise.toml:1702-1706`). All of them exist and do what the handoff says.

## Verified correct (control arms)

- Every SHA in the handoff and the audit resolves to a commit (`git cat-file -t`): abf75906, 1ba74fab, 89f6ce99,
  291e0d15, e90833fd, c3569d61, b0774dc1, e078c542, f9b56da5, 703e5612, b07ebd7b, 15c1061d, 14a02f76, b79654d4,
  ccf6234c, 4a6ee2ab, a39cbc3e, 34b8651a. Control: a fabricated id → MISSING.
- MR-B-D 4a6ee2ab is rebased on abf75906 (`merge-base --is-ancestor` rc 0; control abf75906 vs 89f6ce99 rc 1).
- PR/issue numbers (`gh pr view` / `gh issue view`):
  - #1647 MERGED (agnix 0.56.4, mc 2cdcda45); #1650 MERGED, mc abf75906.
  - #1651–#1655 are OPEN issues; their titles match R4-1 / N3 / N4+F2 / K11-K12 / N1-N3.
  - #1656 MERGED, mc 4fdbac59, head `chore/serp-api-key-doctor`, at 10:56Z. That is before the 06:00 CDT handoff, and
    the settle condition "Merged, then land" stays valid.
  - #1648 OPEN; #1636/#1637/#1639 are OPEN issues; #1659's head is `docs/handoff-2026-10-04c`.
  - The 04b audit counts (1 HIGH, 6 MED, 5 LOW) match `git show abf75906:docs/handoffs/session-2026-10-04b.md:115`.
- KB: PR #874 MERGED, mc 26a84f7f; KB#872 OPEN; issuecomment-5978461251 belongs to KB#872. Control: a neighbouring
  bogus comment id → 404.
- The bgisolation PR is #1658, OPEN, head c3569d61 (control: a bogus `--head` → `[]`).
- `claude rm <id>` is a real 2.1.289 subcommand. c1a35607 and 9dcdab49 are the coordinators from the 10-03 evening
  (state `done`, cwd = main checkout; `claude agents --json --all`), matching queue item 3. The session names for
  1debf341 and e67105a8 match the handoff and the audit.
- In-flight paths exist: `bmavn1o1e.output`, `b7mhgay94.output` and `bmjwlp9kj.output` under the 1debf341 tasks
  dir; `~/.claude/jobs/1debf341/tmp/mise.lock.main-dirty`; `.agent/sdlc-specs/{rgs-rc143-review,retire-vs-harness-ship}.md`;
  0087b182 `settlement.json` (failed, 756.7 s, codex rc 0; the report says 757 s) and 0ca4b234 (failed, 721.0 s,
  codex rc 0). Census `.agent/state/coordinator-handoff/1debf341-….json` records pid 30424. It is now at :16 rather than
  the review's :14, because the file was rewritten at 06:32.
- `ship` refuses a non-empty porcelain status: `_working_tree_clean` is `pr.py:559-562` and the refusal `pr.py:602-607`.
  The audit's `:600-605` is 2 lines early (`:600` is the main/detached refusal); immaterial.
- `tests/test_install_doctor_hook.py` at 89f6ce99 has exactly 2 tests, which supports F8 (control file: 73).
- `docs/specs/research-gate-sync.md` exists only on 291e0d15 (absent at 36ab6bba), as the N4 text implies.
- Retire review: the table matches `_in_flight_blocks` and the `blocking` predicate at abf75906
  (`coordinator_handoff.py:1061-1078`, `:1119-1147`). `--accept-inflight` alone cannot bypass an unadopted live census
  pid. The anchors I spot-checked hold: `tests/test_coordinator_handoff.py:640-647`, `reap.py:178`, `$CC/agent-view.md:752`,
  `$CC/interactive-mode.md:336`, and live-arms Arm D at L16. Installed Claude Code is 2.1.289.
- rgs review: 291e0d15 has parent 34b8651a, 5 files, +381/−37, author time 04:40:47. The cited
  `https://learn.chatgpt.com/docs/non-interactive-mode` returns 200; `developers.openai.com/codex/noninteractive`
  308-redirects there, and the control path returns 404.
- Codex-lane diagnosis anchors hold at 36ab6bba: `research_fanout.py:823/:872` `clean_env(keep=…)`; `child_env.py:77-92`;
  `_prerequisite_reason` at :967, which checks only `EXA_API_KEY` for a key; KB codex docs
  `config-file__config-advanced.md:350-361` and `config-file__config-sample.md:408-410`; `inherit = "core"` at
  `.codex/config.toml:2` and `~/.codex/config.toml:702`.
- Context, not a finding: both SDLC runs have `status=failed` because of the spawn-reconciliation errors
  ("parent thread id not found in codex.log banner"). That is the open #1637 (codex 0.160 colours its exec banner),
  which neither the handoff nor the reports cite.

## Memory

The memory update was REFUSED by the same bg-isolation write guard (`.claude/agent-memory-local/cold-reviewer/`
is inside the shared checkout). The durable pattern note and its MEMORY.md index line are staged at
`/tmp/cr-1659/memory-handoff_doc_review.md` for whoever can write that directory. Scratch worktree and probe files
are deleted; only those two `/tmp/cr-1659/` files remain.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed commit, and PR/issue states via `gh`
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — PR #874, issue #872 and its comment via `gh`
