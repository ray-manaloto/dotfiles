# Session audit 2026-10-01c — Brief S: retrieval misses

Audited session: `7133045d-9086-4a3f-8fa7-0a4df70f442a` (`dotfiles-20261001.000`). Method: Brief S of
`docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md`. Each row is a fact the session
re-derived from source, `--help`, logs or a failed first attempt, when a file it already reads at that point should
have handed it over. Ordinals are 0-based JSONL lines of the main transcript. The transcript was parsed with python
(`/tmp/claude-audit-s/dump.py`), which emitted 1,322 tool_use, tool_result and assistant-text rows, 10 of them
`is_error`.

Anchors were read against the audit worktree at `aeeb9164`. KB anchors were read against the KB main checkout at
`91a56a82`.

## Findings

### S1 (high): seven bg lanes parked ~11h45m on the EnterWorktree relocation prompt, which was documented on disk

- **Claim.** The lanes were launched from the main checkout, and each called `EnterWorktree` into
  `../dotfiles.worktrees/lane-*`. That path is outside `.claude/worktrees/`, so every lane hit the
  permission-root-relocation prompt. Auto mode does not suppress that prompt, and the lanes waited silently.
- **Cost.** About 11h45m of seven lanes (A, B, C, E, G, KB2, KB3), plus a diagnostic subagent (`lane-unstick`,
  ordinal 4602). The diagnosis is at 4638–4640.
- **Where the fact already lived.** The KB offline harness docs say so:
  `sources/agent-harness-docs/docs/claude-code/worktrees.md:43` reads "When Claude enters a path outside the
  repository's `.claude/worktrees/` directory, Claude Code asks for your approval first". This is a step-00
  question under `research-doc-sources.md`.
- **Control arm.** `grep -n relocat\|outside worktrees.md` returns line 43, so the corpus answers. In the shipped
  skill, `grep -n -i "relocation\|EnterWorktree" .claude/skills/parallel-work-split/SKILL.md` returns 0 lines. The
  same grep, run against the diff of the unshipped branch, does hit (see below), so the probe discriminates.
- **Disposition: FIX-NOW.** The fix is already written: local commit `faad62f8` on `docs/fanout-launch-fixes`.
  `git ls-remote origin refs/heads/docs/fanout-launch-fixes` returned nothing, while the same probe for `main`
  returned `aeeb9164de56`, so the branch is NOT on GitHub. Ship that branch's hunk unchanged. It replaces the
  paragraph starting `` `claude --bg` runs in the current directory, so launch it from inside the `` in
  `.claude/skills/parallel-work-split/SKILL.md` (and in its `.agents/` mirror). It also adds the brief-template
  `CWD:` line and the "check for `state == "blocked"`" paragraph. Combine it with S2 below.

### S2 (med): `claude --bg` refuses an untrusted worktree, and a `| grep -o` hid the refusal

- **Claim.** At ordinal 5466, the session launched two takeover sessions as `(cd <wt> && claude --bg … 2>&1 |
  grep -o 'backgrounded · …')`. The first (dotfiles `cc-repoint`) printed `backgrounded · 5361f892`. The second,
  in `harness-evolution-ledger.worktrees/native-codex-ci-20261002`, produced only `Exit code 1`, because the grep
  filtered out the message.
- **Cost.** Three calls. At 5470 the session `ls`-ed the worktree, suspecting a bad path. At 5474 it re-ran with
  file capture. At 5483 it got `Workspace not trusted. Run claude in … once and accept the trust prompt`. That
  session never started: it needs Ray, as the handoff at 5516 says.
- **Where the fact lived.** `$CC/agent-view.md:37` (trust dialog) and `$CC/worktrees.md:29` both say: "Interactive
  runs require workspace trust: if you haven't run Claude in the directory before, run `claude` once there".
- **Control arm.** The dotfiles worktree launched in the same command (rc 0, id `5361f892`), so the failure is
  specific to the directory, not to the flags.
- **Disposition: FIX-NOW.** In `.claude/skills/parallel-work-split/SKILL.md` (plus its `.agents/` mirror):
  - **Old anchor:** `**A \`--bg\` session commits and pushes by default**, and may open a draft PR,`
  - **New text, inserted immediately BEFORE the anchor:**

    ```text
    **Trust first.** In a directory Claude has never run in, `claude --bg` exits 1 with `Workspace not trusted`
    (`$CC/worktrees.md:29`; measured 2026-10-02 on a harness-evolution-ledger worktree). Ray runs `claude` there
    once to accept. Capture launch output to a file. A `| grep -o 'backgrounded'` hid this refusal.
    ```

### S3 (med): KB signed-live-evidence classifier, and `enforce_admins`, re-derived twice by failure

- **Claim, first time (ordinals 1936–1957).** `gh pr merge` of KB #831 was refused with HTTP 405 ("3 of 3
  required status checks have not succeeded"). Only then did the session read `branches/main/protection` and learn
  `enforce_admins: true`. It then toggled that setting off and on around the merge. Several AskUserQuestion rounds
  (1728, 1781, 1887, 1932, 1953) were spent establishing what the gate requires.
- **Claim, second time (ordinal 5275).** The KB2 lane bisected main's classifier to learn that
  `python/src/kb_setup/cli.py` is in `SENSITIVE_EXACT` (`live_receipt_scope.py:17-36`) and that `\buv\b` in
  `MISE_SENSITIVE` (`:46-49`) matches new `run = "uv run …"` task lines. That brought another admin-merge ask at
  5285.
- **Where it should live.** Not one KB markdown file names the classifier or `enforce_admins`:
  - `git grep -n -i "live evidence\|live-evidence\|live_receipt" -- '*.md' ':!sources' ':!docs/research'` returns 0
    lines.
  - `git grep -l enforce_admins -- ':!sources'` returns 0 files.
  - **Control arm:** `git grep -c kb-ship -- '*.md'` hits 5 skill files, and `git grep SENSITIVE_EXACT` hits the
    `.py` file, so the probe sees both trees.
- **Disposition: FIX-NOW (KB repo, through its own `kb-ship`).** Edit
  `knowledge-base/.agents/skills/kb-review/SKILL.md` and `.claude/skills/kb-review/SKILL.md`. The two are
  byte-identical copies (`cmp` printed `SAME`), so edit both.
  - **Old anchor:** `and a receipt whose SHA does not match is not a receipt.`
  - **New text (append as the next paragraph):**

    ```text
    **Classify the diff for signed live evidence before shipping.** The required check
    runs MAIN's `python/src/kb_setup/live_receipt_scope.py` (`graphify-live-receipt.yml:42-52`
    shows the four input files). It prints `REQUIRED` for any path in `SENSITIVE_EXACT` /
    `SENSITIVE_PREFIXES` (including `cli.py`), for a `mise.toml` line that matches
    `MISE_SENSITIVE` (including `\buv\b`), or for a non-exempt `mise.lock` entry. Nothing
    produces that evidence today, so a REQUIRED PR needs Ray's admin merge. Main has
    `enforce_admins: true`, so `gh pr merge --admin` returns 405 until that is toggled off.
    ```

### S4 (med): `mise run ship` has no PR-body flag; re-derived from `pr.py`

- **Claim.** At ordinal 3969 the session ran `mise run ship -- --help | head`. The guard denied it (3970) because
  ship is a gate command. At 3974 the session grepped `python/src/dotfiles_setup/pr.py` for `body`. It then
  hand-wrote a chain at 3980 and again at 4102: `ship`, then `gh pr edit $P --body-file $B`, then `bounded-wait`,
  then `land`.
- **Cost.** Two calls and a guard deny.
- **Where the fact lived.** Half of it was already present.
  `.claude/skills/pr-workflow/SKILL.md:24` says "the BODY is always --fill (commit messages, pr.py:524)". The
  remedy (`gh pr edit --body-file` after ship) is not there.
- **Second gap.** `mise.toml:974`, `[tasks.ship] description`, still reads "Gate matrix → push → open/update PR →
  watch checks to verified green". Ship arms auto-merge and returns. That description is the first thing
  `mise tasks` shows.
- **Control arm.** `grep -n body .claude/skills/pr-workflow/SKILL.md` matches only line 24. A grep for
  `body-file` returns 0.
- **Disposition: FIX-NOW.**
  - `.claude/skills/pr-workflow/SKILL.md`:
    - **Old text:** `` mise run ship -- --title "..."     # override the PR title; the BODY is always --fill (commit messages, pr.py:524) ``
    - **New text:** the same line, then this line:
      `` gh pr edit <N> --body-file <f>     # set a hand-written body AFTER ship: no push, so it cannot race auto-merge ``
  - `mise.toml:974`:
    - **Old text:** `description = "Gate matrix → push → open/update PR → watch checks to verified green"`
    - **New text:** `description = "Gate matrix → push → open/update PR → arm native auto-merge and return (body = --fill; edit with gh pr edit --body-file)"`

### S5 (med): ship's plain `git push` was refused after rebasing a previously pushed branch

- **Claim.** The second ship (log `ship-ncd2.log`) passed every gate, then printed `FAIL  ship: git push rc=1`
  (4091–4092). Branch `feat/native-cli-devcontainer` had been pushed at `fb4c674b` before it was rebased, and no PR
  existed. The session established that by hand at 4096: it ran `git ls-remote` and
  `gh pr list --head … --state all` (0 PRs), then `git push --force-with-lease=<b>:<old>`, then re-ran the full
  ship at 4102.
- **Cost.** Three calls, plus a full repeat of the gate matrix (about 10 minutes).
- **Where the fact lived.** `pr.py:586` runs `git push -u origin <branch>` with no lease, and the pr-workflow
  failure-mode table has no `git push rc=1` row.
- **Control arm.** In `pr-workflow/SKILL.md`, `grep -n "force-with-lease"` matches only the DIRTY row (line 128,
  a different cause), and `grep -n "push rc"` returns 0.
- **Disposition: FIX-NOW.** In `.claude/skills/pr-workflow/SKILL.md`, after the `` | `FAIL gate <name>` | `` row
  (line 124), add:

  ```text
  | `FAIL  ship: git push rc=1` after all gates PASS | The branch was pushed before and has since been rebased or amended; ship's push has no lease (pr.py:586) | Confirm there is no PR (`gh pr list --head <b> --state all`), read the old SHA with `git ls-remote origin refs/heads/<b>`, run `git push --force-with-lease=<b>:<old-sha> origin <b>`, then re-run ship. If a PR exists and auto-merge is armed, use a new branch instead (memory `feedback_amend_after_ship_races_automerge`) |
  ```

### S6 (low): the `verify-apt-pins` remedy was re-derived from a Renovate PR diff

- **Claim.** The ship gate `verify-apt-pins` failed with `E: Version '3.5.5-1ubuntu3.5' for 'libssl-dev' was not
  found` (4012). To find the replacement versions (`3.5.5-1ubuntu3.7`, and `sudo 1.9.17p2-1ubuntu3.1`), the session:
  - searched for the pin and for an open bump PR (4016);
  - read `gh pr diff 1449` and `mise run apt-repo -- --help` (4029–4030);
  - hand-edited with perl (4044).
- **Cost.** Four calls and one failed ship.
- **Where it should live.** The pr-workflow failure table (ship is where it fired). Memory
  `feedback_ubuntu_release_pocket_pins_dont_install` carries the cause but not the lookup.
- **Control arm.** In `pr-workflow/SKILL.md`, `grep -n apt` returns 0 lines.
- **Disposition: FIX-NOW.** Add a row after the S5 row in `.claude/skills/pr-workflow/SKILL.md`:

  ```text
  | `FAIL gate verify-apt-pins` with `E: Version '<v>' for '<pkg>' was not found` | An Ubuntu security or updates upload superseded the pin | Take the new version from the open Renovate apt PR (`gh pr diff <N> \| grep '^[-+]"apt:'`) or `mise run apt-repo -- --toml --pin`, bump `.devcontainer/mise-system.toml`, re-run `mise run verify-apt-pins`, then ship |
  ```

  Inherited and unverified: the session did not run `apt-repo --toml --pin` itself. It took the versions from #1449.

### S7 (low): `typos` rejects the coined abbreviation `HEL`; two failed handoff commits

- **Claim.** The session coined "HEL" for harness-evolution-ledger at 3364 and used it throughout. The handoff
  commit failed on typos twice:
  - At 5434, `HEL` should be `HELP`. The fix at 5437 was a case-sensitive `\bHEL\b` replacement.
  - At 5456, `hel` should be `help`. The lowercase `hel-20261002.native-codex` remained.

  A third commit attempt (5459) was in flight while context ran out. The session also skipped §4's
  "`mise run lint` before committing" and let the pre-commit hook find the problem.
- **Cost.** Two failed commits and three edit/commit calls, in the last minutes before context ran out.
- **Control arm.** The typos output at 5434 and 5456 names both spellings. `typos.toml` holds no `hel` entry: its
  allowlists are `HOMEs`, `fpr` and `CPY`.
- **Disposition: FIX-NOW.** In `.claude/skills/session-handoff/SKILL.md` §4:
  - **Old anchor:** `Stage specific paths (never \`git add .\` — phantom \`.agent/state/**\` files;`
  - **New text, inserted before it:**

    ```text
    Write repo names in full. `typos` rejects coined abbreviations (`HEL`/`hel` failed two handoff commits on
    2026-10-02). Run the lint above BEFORE `git commit`; don't let the pre-commit hook find it.
    ```

### S8 (low): `codex update`, the native self-update command, re-derived from `--help`

- **Claim.** At 1472 and 1495 the session probed `codex --help | grep update` and `~/.local/bin/codex update --help`
  to learn the native update verbs for the native-only migration.
- **Where it should live.** `.claude/rules/ai-cli-invocation.md:67` carries only `agy update`.
- **Control arm.** `git grep -n "codex update"` over `*.md`/`*.toml` (excluding `docs/research`) returns 0 lines,
  while `agy update` hits line 67.
- **Disposition: FIX-NOW.** In `.claude/rules/ai-cli-invocation.md`:
  - **Old text:** `self-updating via \`agy update\`; every mise name for it is in \`disable_tools\`).`
  - **New text:** `self-updating via \`agy update\` (codex: \`codex update\`, claude: \`claude update\`); every mise name for it is in \`disable_tools\`).`

  This is an eager rule, so check `md_size_budget` (the change adds about 45 characters).

### Already closed in-session (no action)

- **`claude --bg` flags and `crossSessionInbound`.** The session re-derived these from `claude --help` (1311–1353)
  and from the mirrored `settings-reference.md` (3571). Both are now carried by
  `.claude/skills/parallel-work-split/SKILL.md:99-115`, shipped in #1533 (`317d91e2`).
- **The guard denies `| head` on `mise run ship -- --help` (3970).** That is a repeat-offender item, not a
  retrieval miss. The guard did its job.

## Summary

Eight findings: 1 high (S1), 4 medium (S2–S5), 3 low (S6–S8). All are FIX-NOW:

- S1 ships an already-written unpushed commit (`faad62f8`).
- S3 needs a KB PR.
- The rest are small edits: the pr-workflow skill (S4–S6), `mise.toml` (S4), the parallel-work-split skill (S2),
  the session-handoff skill (S7) and the ai-cli-invocation rule (S8).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): audited the session's transcript, skills,
  rules, `mise.toml` and `pr.py`; ran `ls-remote` on the unpushed branch.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): read `live_receipt_scope.py`,
  `graphify-live-receipt.yml` and the kb-review skill, plus the offline Claude Code docs under `sources/`.
