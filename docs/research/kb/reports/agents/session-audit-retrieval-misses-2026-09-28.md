# Session audit — retrieval misses (Brief S), session cc5eebbf, 2026-09-28

Lane: §1c Brief S (`docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md` § Brief S).
Source: main transcript `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/cc5eebbf-2629-4ae9-a9ee-f6d38df8c8c0.jsonl`
(6.6 MB) + `subagents/` (21 delegates). Read-only except this file. Status: COMPLETE.

## Method

See "Method (as run)" below.

## Findings

Running notes first (kept as written), then the final table.

### Running notes (main transcript, L1–L1614, 11:13–18:19)

- Candidate: codex review-lens final message buried in a 300 KB log — needed `grep -n '^codex$'` + `sed -n` per review
  (1388: L546+L553; 1422: L1203/L1217/L1260). Check whether the skill's § Review tiers command carries `-o <path>`.
- Candidate: codex implementer report read from the 52,846-line LOG via `sed -n '45771,45850p'` (L1485) although the
  wrapper named an OUT file. Check the OUT file's contents / wrapper doc.
- Candidate: `ship` PR number recovered by grepping its log twice with two different patterns (L678 URL regex; L1374
  `PR #[0-9]+`). Check what `ship` prints last and whether the pr-workflow skill documents it.
- Candidate: `gh run list --workflow ci.yml … select(.createdAt > "2026-09-27")` returned empty (L841), retried without
  the workflow filter (L847). Needs a probe before attributing.

### Method (as run)

Dumped the main transcript (1,291 condensed lines, 397 tool calls) and 10 subagent transcripts (triage, cold-review,
implementer, both mattpocock axes, five `/code-review` forks) with a scratch script; read every tool call and every
failed or re-tried step; for each candidate, checked whether a repo file ALREADY carried the fact at the time, and
re-probed the fact live today where it was cheap. Transcript anchors are `L<n>` = JSONL line of the main transcript
unless prefixed `triage L<n>` (subagent `a9979cd0d4e3396c2`) or `cold L<n>` (`a1371df559edd2e71`).

Control arms used below: `mise tasks ls` finds `handoff-check`/`bounded-wait` (1 each) but 0 `hook-selfcheck`; plain
`gh issue view 11` 760 bytes vs `--comments` 0 bytes; `grep -rl` finds the gate-runner export that `git grep -l`
misses (1 vs 0); `timeout 5 true` rc=1 while `true` resolves normally; this report's own path is untracked (0) while
39 other `session-audit-*` files are tracked (no #1419 filename collision).

## Findings

| # | Fact the session re-derived | Anchors | Cost | Status |
|---|---|---|---|---|
| S1 | `hook-selfcheck` is `uv run --project python dotfiles-setup hook selfcheck`, not a mise task | L1989 gate chain ran `mise run hook-selfcheck` → `no task hook-selfcheck found`; L2019–L2037 grep `pr.py:340` for the argv | 1 failed gate in a ~6 min chain + 3 calls | PARTIAL — #1433 verify skill row; `pr-workflow` still names it like a task |
| S2 | `sync --check` output + exit codes | L2476, L2481 grep `main.py`/`sync.py` for `--check`/`check_only` | 2 calls | NOT FIXED — `devcontainer-sync` SKILL.md:25,59-60 ALREADY had rc 1/rc 2 (not consulted); lacks rc 0 wording and #1429's platform rule |
| S3 | sync record path + shape | triage L230–L235; main L2847–L2872 (grep sync.py for the file name, `ls ~/.local/state/dotfiles`, `jq`) | 6 calls, derived TWICE in one session | PARTIAL — #1433 verify Gotchas name `sync-*.json` + `containers`; the sync skill does not |
| S4 | graphify hook probe: needs `tool_input`, run via `bash`, `read` vs `search` mode | L1971→L1982 (rc=126, script not executable); /verify probe without `tool_input` printed nothing (L2966 note); #1433 row first routed a Read payload to `search` — codex lens P2 L3486 → fix L3493 | 3 calls + 1 review round | FIXED — #1433 (`c2545365`) verify Gotchas + READ-mode row |
| S5 | `jq` is pinned in `.config/mise/conf.d/shared.toml`, so a test may shell out to it | L2712, L2717 | 2 calls | NOT FIXED |
| S6 | `gh issue view`: `--comments` is exclusive with `--json`, and non-TTY `--comments` prints ONLY comments (0 bytes when none, never the body) | main L2177 → `specify only one of --comments or --json`; triage L129 → 16/29 files 0 bytes, rest body-less; refetch L137 with `--json body,comments` | 1 failed call (main) + 2 calls + a rate-limit check (triage) | NOT FIXED |
| S7 | how `ship`/`land` report the PR number | L678 URL regex, L1374 `PR #` regex, reused L1796/L2273 | 0 failed calls; two ad-hoc regexes, later chains depend on the second | NOT FIXED (low cost) |
| S8 | codex review lens: the final message is the last `^codex$` block of a ~300 KB log | L546+L553 first derivation; L1203/L1217 misread a running lens as finished (empty `tail`, `pgrep`); pattern re-typed at L1260, L1623, L2152, L2705, L3486 and in 3 persistence commands | ~4 wasted calls + 8 re-typed extractions | NOT FIXED; `-o` UNVERIFIED on `exec review` |
| S9 | CLANG_P2996_REF is NOT auto-bumped: Renovate's regex extracts only the Dockerfile `ARG`, not bake's HCL default | L3528–L3550, L3694–L3702 (`git log -S`, `git log -L`, `gh pr diff 1063`, `gh pr view 188`) + a 603 s SDLC team run | ~6 calls + 10 min team review; the known file handed a WRONG fact | NOT FIXED — #1434/#1435 open |
| S10 | where the verify recipe lives / what it covers | /verify only on Ray's ask (L2931); session hand-built `scratchpad/verify-session.sh` (L2947) because the 2026-09-17 recipe covered none of its surfaces | a whole verify pass authored from scratch | FIXED — #1433 Recipe additions (trigger gap is Brief Q's) |
| S11 | `timeout` is a broken, unversioned mise shim on this Mac | triage L72–L80: `timeout 60 docker …` → `No version is set for shim: timeout`, jq parse error, `gtimeout` probe | 2 calls | NOT FIXED — memory `project_session_2026-09-12b.md:49` has it; the eager rule still endorses `timeout <n>` |
| S12 | `.codex/agents/` holds 11 GITIGNORED Codex-app exports that `git grep` cannot see | coordinator's phrase sweep (L1558, `git grep`) → false verification claim in `47453338`; cold review MEDIUM F1 (L1709); #1425 | 1 wrong claim in a commit message + a MEDIUM + an issue | NOT FIXED — #1425 open |
| S13 | mise lock per-platform tables are `[tools.<t>."platforms.linux-x64"]` | triage L249, L253, L258 → correct count only on L262 | 3 calls | NOT FIXED (low value) |
| S14 | a workflow's `journal.jsonl` has no model field; the model is `message.model` in its `agent-*.jsonl` | L3336 → L3342 | 1 call | NOT FIXED (low value) |

### Exact line to add, one file each

- **S1** `.claude/skills/pr-workflow/SKILL.md:35` — replace ``→ `hook-selfcheck` (always-run:`` with:
  ``→ hook-selfcheck (`uv run --project python dotfiles-setup hook selfcheck` — NOT a mise task; always-run:``
- **S2** `.claude/skills/devcontainer-sync/SKILL.md`, after the "Staleness = …" paragraph (under line 37):
  `Since #1429 the local tag is ALSO stale when THIS arch's platform is absent under it (docker image inspect --platform <triple> <ref> rc≠0). --check prints check: current (rc 0) · check: STALE — sync would rebuild / check: OUTDATED — sync would rebuild this architecture's container (rc 1) · check: UNKNOWN — registry unreachable (rc 2).`
- **S3** same skill, new bullet under "What it does":
  `Sync record: ~/.local/state/dotfiles/sync-<image ref, / and : → _>.json (e.g. sync-ghcr.io_ray-manaloto_dotfiles-devcontainer_dev.json); keys registry_digest, local_image_id, containers = {"<workspace-hash>:<arch>": "<overlay image id>"}; written by write_sync_record after a converge, read by container_current (#1432: ids can outlive their images).`
- **S4** none needed (fixed in #1433).
- **S5** `tests/AGENTS.md`, after the "Subprocess usage" bullet (line ~110):
  `- A test may shell out only to a tool pinned in .config/mise/conf.d/shared.toml (host, image and CI all install it: jq, hk, chezmoi, gitleaks, …); any other binary makes a Mac-only pass (feedback_host_is_not_a_control_arm_for_ci).`
- **S6** `.claude/rules/gh-cli-watch.md` § Canonical patterns (eager; every lane reads gh state through it):
  `gh issue view 123 -R o/r --json title,body,comments --jq '.body, (.comments[].body)'  # never --comments: non-TTY it prints ONLY comments (0 bytes when none) and it is exclusive with --json`
- **S7** `.claude/skills/pr-workflow/SKILL.md`, after line 61 ("ship prints the `mise run land` follow-up"):
  `Its success line is "ship: OK — PR #<n> open, local gates green, AUTO-MERGE enabled."; land's is "land: OK — PR #<n> merged, main green, Mac synced". Capture <n> with grep -oE 'PR #[0-9]+' <log> | tail -1.`
- **S8** `.claude/skills/codex-sdlc-team/SKILL.md:185` — make the command
  `mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> -c 'sandbox_mode="read-only"' -o .agent/logs/codex-review-<slug>.md`
  and add: `The final message is that file; fallback: the last ^codex$ block of the log. A lens is finished only when your rc= line is written — an empty tail means still running.`
  Caveat: `codex exec review --help` (0.158.0) lists `-o, --output-last-message <FILE>`, but `exec review` ignored
  `--output-schema` (#1296), so arm `-o` once on a real review before relying on it.
- **S9** `.github/workflows/AGENTS.md:18` — replace ``CLANG_P2996_REF`: Renovate git-refs.`` with:
  ``CLANG_P2996_REF`: NOT kept current today — #169 retired `p2996-refresh` believing Renovate bumps both sites, but its regex extracts only the Dockerfile `ARG`; bake's HCL default is invisible to it and #1063 is frozen (#1434, #1435).``
  (The `refresh.yml:20-23` comment makes the same false claim; the #1434 fix must correct both.)
- **S10** none needed (fixed in #1433).
- **S11** `.claude/rules/long-running-command-hangs.md:50`, after "wraps the loop with `timeout <n>` or `mise run bounded-wait`":
  `(⚠️ on this Mac host timeout is an unversioned mise shim — rc=1 "No version is set for shim: timeout"; bound host commands with mise run bounded-wait or a SECONDS deadline; timeout <n> only in-container or in CI)`
- **S12** `.claude/skills/codex-sdlc-team/SKILL.md`, in the "A `.codex/agents/*.toml` file is about to be written or edited" context:
  `⚠️ .codex/agents/ also holds ~11 GITIGNORED Codex-app exports of our Claude agents (#1425). git grep and git ls-files cannot see them: sweep phrases with grep -rF over the dir, and list them with git ls-files --others --ignored --exclude-standard .codex/agents.`
- **S13** `.claude/skills/lock-image/SKILL.md`:
  `Per-platform lock entries are TOML tables [tools.<tool>."platforms.linux-x64"] / [tools.<tool>."platforms.linux-arm64"] (conda: [conda-packages.linux-arm64."<pkg>"]); count coverage with grep -c '^\[tools\..*"platforms\.linux-arm64"\]'.`
- **S14** `.claude/skills/research-sweep/SKILL.md`:
  `A run's subagents/workflows/<wf>/journal.jsonl has no model field; the model each node ran on is message.model in that directory's agent-*.jsonl.`

### Checked and excluded (not retrieval misses)

- zsh `====` (L76, triage L102), zsh NOMATCH (L3132 blind grep, triage L98 and L314) and zsh non-splitting `$F`
  (L1038): the facts are recorded (memory, #1388). These are repeats for Brief R.
- `git rev-parse --short A B` → `fatal: Needed a single revision` (L84, L3043): a shell-usage slip, not a missing doc.
- Codex implementer "OUT" file: `.agent/kb/raw/codex-sol-implementer-result-implC-82574-1790617188.md` holds 10 lines of
  `RESEARCH INCOMPLETE: Context7 exited 1…`, not the report. The report had to be cut from log lines 45771–45850
  (L1485). This is a lane defect (a trailing research-gate turn displaced the `-o` last message), so it belongs to the
  bugs lens, not to a doc.
- `gh run list --workflow ci.yml … select(.createdAt > "2026-09-27")` returned empty at rc=0 (L841). My re-run of
  the identical command today returned empty once, then 13 lines, and 8 neighbouring variants were all non-empty. This
  is gh returning empty intermittently, not a retrieval gap; the session's control-armed retry (L846) was correct.
- `no_platform_literals` flagged docstring triples (L2771), `ty` dict invariance (L1315), the `typos` spelling fix (L2777),
  the transient `.git/index.lock` (L1429) and the sdlc-team `spec_missing` after a branch-guard-denied Write
  (L3557/L3566): gates doing their job, or Brief R, not retrieval.
- mattpocock `code-review` looked for `docs/agents/issue-tracker.md` (L3043): one `ls` and no real cost;
  `.claude/CLAUDE.md` names `docs/issue-tracker.md` and says not to run the setup skill.

### Cross-cutting observation

Three of the ten unfixed misses (S2, S3, S9) sit in files that EXIST and are the natural place to look: the
devcontainer-sync skill and the workflows AGENTS.md. S2 was already answered there and was not consulted. S9 was
answered WRONGLY there. #1429 changed sync semantics without updating the sync skill, which is the
`tool-currency-and-native-first.md` rule-5 drift ("sync the describing docs/skills in the SAME change"). A cheap
machine check would be a `suites.toml` contract binding `sync.py`'s `check: ` output literals to the skill text.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #11, #678, #1172, #1422, #1425, #1432, #1434, #1435 read via `gh`; `gh run list` probes of `ci.yml`
