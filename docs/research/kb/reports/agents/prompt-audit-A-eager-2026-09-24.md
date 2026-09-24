# Prompt audit, slice A: the eager instruction surface

**Delivery note:** the harness refused to let me write the final report to `SP/report-A-eager.md` ("Subagents should return findings as text"), so this message is the report. That file holds only the incremental findings log I kept while working. The diff and patches are in the scratchpad: `SP/A-work/proposed-diff-A.md`, one patch per finding in `SP/A-work/patches/`, everything in one file at `SP/A-work/combined-A.patch`, and the script that generated and checked them at `SP/A-work/edits.py`. SP = `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/3dcf5ff5-f549-4bc8-bf1d-34788799b4a3/scratchpad/prompt-audit`. Nothing in the repo was changed.

**Assumptions.** The target model is Claude Opus 5.5. No file in this slice drives a sonnet or haiku subagent. The scope is `AGENTS.md`, `.claude/CLAUDE.md`, `.claude/token-routing.md`, all 27 `.claude/rules/*.md`, and the `AGENTS.md` in `.devcontainer/`, `.github/workflows/`, `python/` and `tests/`. Two of the rules, `ci-local-parity` and `md-size-budgets`, are loaded only for certain paths, so they are not eager, but I audited them too. `mise run graphify-health` reported the graph `fresh`, but the graph has no markdown nodes (#1054), so I read the source directly.

## Summary

There are 45 findings: 40 have proposed hunks and 5 are low-confidence flags.

| Group | Count | Findings |
|---|---|---|
| 1a Pressure language | 0 standalone | All-caps MUST/NEVER/ALWAYS-style words appear at most twice per file. ⚠️ markers cluster in the secrets rule (11) and the codex-sdlc-team rule (5); most of them carry a reason, so they stay. The only emphasis I'd trim is in F-A22. |
| 1b Scaffolds replaced by API features | 0 | The signal greps found nothing; a control word on the same corpus did match. |
| 1c Over-specification | 2 | F-A11, F-A33 |
| 1d Fossils (migration-relative text, text that contradicts enforcement) | 15 | F-A3, F-A6 (includes F-A42), F-A7, F-A16, F-A19, F-A23, F-A24, F-A27, F-A29, F-A30, F-A34, F-A40, F-A41, F-A43; F-A12 is a flag |
| 2 Brittle rule files (stale numbers, history narrative, copies that drifted) | 24 | F-A1, F-A2, F-A4, F-A5, F-A8, F-A10, F-A13, F-A14, F-A17, F-A18, F-A20, F-A21, F-A22, F-A25 (folded into F-A27), F-A26, F-A28, F-A31, F-A32, F-A35, F-A36, F-A38, F-A39, F-A44, F-A45; F-A9 and F-A15 are flags |
| 3 Under-description | 1 | F-A37 |
| 4 Request config | 0 | This slice has no request-building code. |

### The three findings that matter most

**1. F-A16: four eager files tell the model to run commands the PreToolUse guard denies.**
- `gh-cli-watch.md` teaches `gh pr checks 123 --watch`, `gh run watch … --exit-status` and `gh pr checks --watch` as its canonical patterns.
- `verify-before-advancing.md` says "Opened a PR → `gh pr checks <n> --watch`".
- `long-running-command-hangs.md` and `.github/workflows/AGENTS.md` repeat the same advice.
- `hook_guard.py:556-572` denies all of these, and `mise-tasks-only.md` and `do-not.md` #6 say the opposite.
- I ran both sides this session. `gh pr checks 999999 --watch --interval 30` was denied. The control, `gh pr checks 999999 --json name`, was allowed and returned rc=1 (no such PR).
- Opus 5.5 follows canonical examples literally, so this costs a denied tool call every time.

**2. F-A7 and F-A24: eager files contradict each other.**
- **Background work (F-A7):** `long-running-command-hangs.md` says Mac-side background work gets "REAPED" and prescribes an in-turn polling loop. `mise-tasks-only.md` endorses the harness background run instead.
  - The harness docs (`$CC/tools-reference.md:180`) say a command the main conversation starts keeps running after its final response.
  - A saved memory records `land` surviving 12m15s of idle with rc=0.
- **MCP cost (F-A24):** `do-not.md` #11 repeats "every tool's schema, forever". `research-doc-sources.md` calls that exact sentence false and says not to cite it.
- **`claude mcp add` (F-A24):** `AGENTS.md` still lists it as a do-not, but the ban was relaxed (`hk.pkl:623`).

**3. F-A27 and F-A28: the secrets rule is written as a diff against a posture the reader never saw.**
- It says "REVERSED" twice, plus "no longer", "The old first suspect is retired", "This file once claimed", and "the paragraph above is HISTORY".
- It gives the credential count as both 56 and 50. `doctor.toml` `env_true` has 56.
- My rewrite keeps every constraint and the rule numbering, because `hook_guard.py` cites "rule 7".
- I re-measured the keychain facts it depends on: `gh:github.com` rc=0, `doppler-cli` rc=0, a made-up name rc=44.

**Cheap, high-confidence fixes:** stale numbers and dangling references.
- **F-A1:** `.claude/CLAUDE.md` says AGENTS.md is at "200/200 lines". It has 195. The limit that actually binds is the 12,000-character cap, and the file is at 11,909 characters.
- **F-A14:** `.devcontainer/AGENTS.md` says "20 shared tools". `shared.toml` has 22.
- **F-A21:** `tests/AGENTS.md` says 3,116 tests. The suite now collects 3,783 of 3,794.
- **F-A20:** `tests/AGENTS.md` points to "the four `test_memory_index.py` bugs above". Nothing above mentions them.
- **F-A13:** `.devcontainer/AGENTS.md` and `do-not.md` #1 name an SSH-agent proxy that no longer exists.
- **F-A10:** the verification step in `ci-local-parity.md` can't tell a global tool from a project tool.

### How I checked the diff

- **Each hunk applies to the current tree.** All 40 per-finding patches pass `git apply --check`; a deliberately corrupted patch fails (rc=1).
- **They can all go in at once.** `combined-A.patch` applies cleanly: 24 files, 190 insertions, 347 deletions.
- **Some per-finding patches overlap.** They are each cut against the untouched tree. Where two findings touch neighbouring lines, use `git apply -3` or the combined patch:
  - F-A5, F-A8 and F-A16 in `long-running-command-hangs.md`
  - F-A10 and F-A11 in `ci-local-parity.md`
  - F-A36 and F-A37 in `graphify-first.md`
- **Every `suites.toml` contract on an edited file still holds after the full patch.** The check discriminates: its first run caught the grok heading, which is why F-A3 also changes `suites.toml:2412` and `tests/test_verify.py:181`. That test asserts the heading exists in the real `.claude/CLAUDE.md`.
- **Size caps still hold:**
  - `AGENTS.md`: 11,909 → 11,517 characters, 195 → 191 lines.
  - `.github/workflows/AGENTS.md`: 11,890 → 11,889 characters.
  - `.devcontainer/AGENTS.md`: 10,982 → 10,988 characters, still 200 lines.
- **Not run:** lint, pytest, verify and lint-docs on the patched tree, because this lane was read-only. Run them before shipping.

## Findings, highest confidence first

### High confidence

**F-A16** — `gh-cli-watch.md:1-5,9-12,18-19,25-50,66-68`; `verify-before-advancing.md:37,89-91,123`; `long-running-command-hangs.md:54-56,106,112`; `.github/workflows/AGENTS.md:148-149`
- **Evidence:** "use the built-in `--watch` flags"; `gh pr checks 123 --watch --interval 30`; `gh run watch 1234567890 --exit-status`; "| Opened a PR | `gh pr checks <n> --watch` until terminal"; "**Backgrounding stays correct for CI/remote waits** (`gh pr checks --watch`, `gh run watch`)".
- **Pattern:** 1d (contradicts enforcement); keep-list #8 exception (the copies disagree).
- **Why obsolete:** the guard denies these commands (both sides verified live), so a model that follows the rule literally makes a denied tool call.
- **Action:** rewrite.

**F-A23** — `agent-report-persistence.md:53-57`
- **Evidence:** "Parent-side injection would require a `PostToolUse` hook on the `Agent` tool, which this change does not add."
- **Pattern:** 1d, and the file contradicts itself.
- **Why obsolete:** `settings.json` has PostToolUse matchers `['Edit|Write|NotebookEdit','Agent']`, so the hook does exist. As a control, the same read showed SubagentStart `[None]` and SubagentStop `[]`, which match the rule's other claims. The file's own "Native carriage" section documents the hook.
- **Action:** remove.

**F-A24** — `do-not.md:81-83`; `AGENTS.md:191-195`
- **Evidence:** "taxes **every** conversation's system prompt with **every** tool's schema, forever"; `AGENTS.md` lists "`claude mcp add`" as a do-not.
- **Pattern:** keep-list #8 exception, and 1d.
- **Why obsolete:** `research-doc-sources.md:97-101` calls that sentence FALSE. `do-not.md` #11's own ✅ paragraph and `hk.pkl:623` say the `claude mcp add` ban was relaxed. The `AGENTS.md` list also omits do-not items #8–#11.
- **Action:** rewrite.

**F-A5** — `long-running-command-hangs.md:113`
- **Evidence:** "`ci-local-parity.md` — hk pkl-cache clearing after `hk.pkl` edits."
- **Pattern:** 2 (a copy that drifted).
- **Why obsolete:** it points at a rule that `ci-local-parity.md:52-58` marks RETIRED.
- **Action:** rewrite.

**F-A10** — `ci-local-parity.md:33`
- **Evidence:** "`mise which <tool>` should resolve under `~/.local/share/mise/installs/`".
- **Pattern:** 2 (the claim fails verification).
- **Why obsolete:** the check passes both a project tool and a global-only tool, so it can't catch the case the rule exists for. `mise ls --current` shows the source config and does tell them apart. Probe details are in "Probes and control arms" below.
- **Action:** rewrite.

**F-A13** — `.devcontainer/AGENTS.md:117-119,130-133`; `do-not.md:8-10`
- **Evidence:** "spawn / tear down the host SSH-agent proxy"; "fails to spawn the host-side SSH agent proxy".
- **Pattern:** 2 (stale specifics).
- **Why obsolete:** no proxy exists in the config or the setup code; the same search does find the Docker Desktop `ssh-auth.sock` socket that replaced it (see "Probes and control arms" below). `initializeCommand` now runs `uv run … dotfiles-setup docker initialize-host`. The underlying reason (apps launched from the dock don't get the terminal's environment) still holds; only the named consequence is stale.
- **Action:** rewrite.

**F-A14** — `.devcontainer/AGENTS.md:22`
- **Evidence:** "the 20 host↔image shared tools".
- **Pattern:** 2 (stale count).
- **Why obsolete:** `shared.toml` `[tools]` lists 22 entries (control: the same listing shows `hk = "1.57.0"`).
- **Action:** rewrite without the count.

**F-A20** — `tests/AGENTS.md:68-69`
- **Evidence:** "The four `test_memory_index.py` bugs above are this shape."
- **Pattern:** 2.
- **Why obsolete:** line 69 is the only mention in the file (control: `classifier_axes` is found by the same command). The bugs it refers to moved to `TEST-INDEX.md:55`.
- **Action:** rewrite.

**F-A21** — `tests/AGENTS.md:25-31`
- **Evidence:** "Total (measured 2026-09-14): **3,116 pytest tests** … 3,127 collected".
- **Pattern:** 2.
- **Why obsolete:** `pytest --collect-only -q` now reports "3783/3794 tests collected (11 deselected)", rc=0. The 11 gated tests still match and are kept.
- **Action:** rewrite.

**F-A1** — `.claude/CLAUDE.md:4`
- **Evidence:** "`AGENTS.md` is at 200/200 lines".
- **Pattern:** 2.
- **Why obsolete:** `wc -l` gives 195 (control: `.devcontainer/AGENTS.md` gives 200). The limit that actually binds is the 12,000-character AGM-003 cap, at 11,909.
- **Action:** rewrite.

### Medium confidence

**F-A7** — `long-running-command-hangs.md:35-39`
- **Evidence:** "background-and-idle gets them REAPED … What works is **in-turn polling**".
- **Pattern:** 2 (one bad session hardened into a rule); keep-list #8 exception.
- **Why obsolete:** it contradicts `mise-tasks-only.md:26`, the harness docs, and a saved measurement (both covered under finding 2 above). The "REAPED" measurement was taken on `&`-detached shells, which the guard now denies. A foreground subagent's commands do stop at its final response, and `session_review` treats the polling loop as mandatory, so the rewrite keeps the loop for subagents.
- **Action:** rewrite.

**F-A6** (includes F-A42) — `long-running-command-hangs.md:79-82`; `ci-local-parity.md:52-60`; `AGENTS.md:82-85`
- **Evidence:** "The old 'clear the pkl config cache' guidance is retired"; "RETIRED … Kept as a numbered rule so references to 'rule 5' stay valid"; "hk 1.49 … `HK_PKL_BACKEND=pkl` override is retired". hk is now at 1.57.0.
- **Pattern:** 1d and 2.
- **Why obsolete:** these are tombstones for practices the model has never seen. The only live instruction in them is "no cache clearing after edits". The only other reference to "rule 5" is in an evidence file.
- **Action:** rewrite to present tense; remove the tombstone section and renumber the next rule.

**F-A8** — `long-running-command-hangs.md:84-97`
- **Evidence:** "The ruff-error wedge is FIXED (#268) … learned by publishing the wrong diagnosis twice".
- **Pattern:** 2 (history narrative).
- **Why obsolete:** the bug is fixed and enforced by `no_hk_depends`, and the evidence file (`:78-96`) already holds the story.
- **Action:** rewrite, keeping the general lesson.

**F-A17** — `verify-before-advancing.md:66,76`; `mise-tasks-only.md:15`
- **Evidence:** "~38GB".
- **Pattern:** 2, and the copies disagree: `persistence-gate-retry.md` says ~21.5GB.
- **Why obsolete:** `docker image ls` shows `:dev` at 22GB.
- **Action:** rewrite. Outside this slice, `devcontainer-sync/SKILL.md:55` also says 38GB.

**F-A18** — `verify-before-advancing.md:109-115`
- **Evidence:** "This file is where the ≤12,000-char misattribution was born …".
- **Pattern:** 2, duplicated.
- **Why obsolete:** the evidence file (`:17-45`) has the same heading and story.
- **Action:** rewrite to one line.

**F-A19** — `python/AGENTS.md:51-55`; `AGENTS.md:94`
- **Evidence:** "distinct from `hk run pre-commit --all` … Run both".
- **Pattern:** 1d.
- **Why obsolete:** the guard (`hook_guard.py:419` and `:430`) redirects raw hk commands to `mise run lint`.
- **Action:** rewrite.

**F-A22** — `tests/AGENTS.md:85-96`
- **Evidence:** "**… is the SIGNATURE OF THE FAILURE** … All three mutation-verified fixes in #601's review loop … as a boast".
- **Pattern:** 2, and 1a (four bold or all-caps phrases in 12 lines).
- **Why obsolete:** the cited report holds the incident. The principle is kept, at normal volume.
- **Action:** rewrite.

**F-A27** (includes F-A25) — `secrets-out-of-the-shell-env.md:3-19,60-66,71-79,81-85,90-91,102,113-118`
- **Evidence:** "REVERSED 2026-08-02"; "This file is no longer …"; "REVERSED — secrets now live …"; "the old trap inverted"; "The old first suspect is retired"; "IT RECURRED THE SAME DAY"; "(This file once claimed …)"; "50 credentials … 12.5× larger" and "all 50" against "56 sanctioned".
- **Pattern:** 1d and 2.
- **Why obsolete:** the file reads as a diff the model never saw. `env_true` has 56 entries (read with tomllib; control: the file's keys came back as `['env','env_true']`). The evidence file already holds the posture history. `suites.toml:2109` binds this file only by path, not by content.
- **Action:** rewrite; every constraint is kept.

**F-A28** — `secrets-out-of-the-shell-env.md:21-43`
- **Evidence:** "Both entries were deleted …", then "BOTH ENTRIES ARE BACK … the paragraph above is HISTORY".
- **Pattern:** 2 and 1d.
- **Why obsolete:** the current state was re-measured this session (same results as in finding 3 above). The deletion story is not in the evidence file ('190 stuck' and 'delete-generic-password' both return 0 hits).
- **Action:** rewrite; move the deletion narrative to the evidence file.

**F-A3** — `.claude/CLAUDE.md:51-54,74-76`, plus `suites.toml:2412` and `tests/test_verify.py:181`
- **Evidence:** "### There is no `grok` here — codex lanes only, stop asking"; "With grok gone".
- **Pattern:** 1d.
- **Why obsolete:** it guards against an alternative nothing else in the slice mentions. The confusion it answered came from the table of the removed fable-orchestrator plugin (`suites.toml:2405`).
- **Action:** rewrite; the contract and test lines are updated in the same finding.

**F-A2** — `.claude/CLAUDE.md:46`
- **Evidence:** "(default `/model` is Opus 5)".
- **Pattern:** 2 (pinned model name).
- **Why obsolete:** it is already stale: the session default is Opus 5.5 and `settings.json` sets no `model`.
- **Action:** rewrite.

**F-A43** — `.claude/CLAUDE.md:66`
- **Evidence:** "New roster:".
- **Pattern:** 1d.
- **Action:** rewrite.

**F-A4** — `token-routing.md:3-6,40-44`
- **Evidence:** "Relocated out of … (#994) … ratified by the 2026-09-10 `/grilling` pass"; "Ray, 2026-09-11: … Before this, all five lanes hard-pinned sol …".
- **Pattern:** 2.
- **Why obsolete:** this file is pulled into every session through an `@` import. The behaviour and its enforcement are already stated.
- **Action:** remove.

**F-A11** — `ci-local-parity.md:31`
- **Evidence:** "Global mise tools are invisible to CI runners." (right after "(invisible to CI)").
- **Pattern:** 1c (repetition).
- **Action:** remove.

**F-A26** — `research-doc-sources.md:12-14`
- **Evidence:** "**36 source trees / 6,446 markdown files** (measured 2026-08-02)".
- **Pattern:** 2.
- **Why obsolete:** it now counts 100 directories and 40,916 markdown files.
- **Action:** rewrite.

**F-A29** — `notepad-enforcement.md:41-45`
- **Evidence:** "The former guidance named `oh-my-claudecode` notepad MCP tools …".
- **Pattern:** 1d.
- **Why obsolete:** the evidence file holds it (6 hits).
- **Action:** remove.

**F-A30** — `agent-artifact-conventions.md:7-10`
- **Evidence:** "Renamed from `.omc/` (2026-07-25)".
- **Pattern:** 1d.
- **Why obsolete:** the evidence file holds it (7 hits).
- **Action:** remove.

**F-A31** — `agent-artifact-conventions.md:94-98`
- **Evidence:** "Earlier wording here claimed … Corrected rather than re-anchored."
- **Pattern:** 2.
- **Why obsolete:** the evidence file doesn't hold it (0 hits).
- **Action:** move to the evidence file.

**F-A32** — `ai-cli-invocation.md:94-102`
- **Evidence:** "An earlier draft of this section credited Claude Code 2.1.261 with three environment variables …".
- **Pattern:** 2.
- **Why obsolete:** the evidence file holds it (3 hits).
- **Action:** rewrite to the one-line habit.

**F-A33** — `ai-cli-invocation.md:70-77`
- **Evidence:** "Do not restate this as 'a bare `agy` resolves the stale copy' … 1.1.24 … 1.1.12".
- **Pattern:** 1c (a ban on a claim nobody made can steer toward it) and 2 (version numbers).
- **Why obsolete:** the positive instruction already sits at `:66-68`.
- **Action:** rewrite.

**F-A34** — `research-doc-sources.md:97-101,110-111`
- **Evidence:** "The old '… forever' cost is FALSE here … Do not cite that sentence"; "Relaxed 2026-07-19; … not coming back."
- **Pattern:** 1d.
- **Why obsolete:** once F-A24 lands, this can be stated positively.
- **Action:** rewrite.

**F-A35** — `mise-tasks-only.md:38-55`
- **Evidence:** "KB PRs #1 and #2 were merged by hand"; "It recurred along a second axis … #138/#236/#386 sat green".
- **Pattern:** 2.
- **Why obsolete:** the evidence file holds both incidents.
- **Action:** rewrite.

**F-A36** — `graphify-first.md:21-33,49-55,65-86`
- **Evidence:** "reported `fresh` for thirteen days and 76 commits"; "Graphify 0.9.65 made equality alone too strict. Measured on 2026-09-22"; "aligned again as of 2026-09-21 — both 0.9.65"; "An earlier version of this rule claimed a rebuild stamp …".
- **Pattern:** 2.
- **Why obsolete:** implementation history in an eager rule. The working rules (what `fresh` means, what's out of scope, always use the mise tasks) are kept. No evidence file exists yet.
- **Action:** create `docs/rules-evidence/graphify-first.md` with the removed text and rewrite the rule. The hunk below covers the rule side only.

**F-A37** — `graphify-first.md:18-19`
- **Evidence:** "blocks the labeling command words anywhere in a Bash string, including the double-quoted grep shape whose backticks zsh ran".
- **Pattern:** 3 (unclear contract).
- **Why obsolete:** a reader can't act on it. The actual rule is `Bash(*graphify label*)` at `settings.json:56`.
- **Action:** rewrite.

**F-A38** — `codex-sdlc-team.md:3-6`
- **Evidence:** "A fresh Claude session had **no way to learn that** before this file existed …".
- **Pattern:** 2.
- **Action:** rewrite.

**F-A39** — `do-not.md:53-58`
- **Evidence:** "'Don't commit' was too late a gate. On 2026-08-03 …".
- **Pattern:** 2.
- **Why obsolete:** the evidence file doesn't hold it.
- **Action:** rewrite; move the incident to the evidence file.

**F-A40** — `AGENTS.md:37-39`
- **Evidence:** "The legacy `dotfiles-setup docker {up,down}` wrapper has been replaced …".
- **Pattern:** 1d, and inaccurate.
- **Why obsolete:** `dotfiles-setup docker --help` still lists `up` and `down`. The real rule is to use `mise run up`/`down` instead.
- **Action:** rewrite.

**F-A41** — `AGENTS.md:132,172`
- **Evidence:** "(the old `install.sh` bootstrap was retired)"; "the legacy `vscode` value has been replaced".
- **Pattern:** 1d.
- **Why obsolete:** `install.sh` no longer exists (0 hits; control: `devcontainer-smoke.sh` → 1).
- **Action:** remove.

**F-A44** — `md-size-budgets.md:55-66`
- **Evidence:** a three-commit chain where two commits are "no longer resolvable".
- **Pattern:** 2.
- **Why obsolete:** the evidence file doesn't hold the chain (0 hits for the commit hashes; control: 'Windsurf' → 2).
- **Action:** move the chain to the evidence file.

**F-A45** — `.github/workflows/AGENTS.md:8,61`
- **Evidence:** "4-stage CI pipeline" (the file then lists 7 stages); "hk pre-commit".
- **Pattern:** 2.
- **Why obsolete:** CI runs `hk run check --all` (`ci.yml:123`).
- **Action:** rewrite.

### Low confidence (flag only, no hunk)

- **F-A9** — `long-running-command-hangs.md:7-17`: the 7-hour-hang paragraph duplicates the evidence file, but it is the one worked failure the repo allows eager (`md-size-budgets.md:141-143`).
- **F-A12** — `ci-local-parity.md:12-14`: a one-sentence "why" dated to one session.
- **F-A15** — leftover generator comments: `<!-- Generated: … -->`, `<!-- MANUAL: … -->` and `<!-- PR blast radius … -->` in `AGENTS.md:1,98`, `.devcontainer/AGENTS.md:1-2,180-183`, `.github/workflows/AGENTS.md:1-2,193`, `python/AGENTS.md:1-2,112` and `tests/AGENTS.md:1-2,135`. The docs guarantee HTML comments are stripped only for CLAUDE.md files (`$CC/memory.md:163`).
- **`probes-need-a-control-arm.md:65-98`:** the incident examples and heavy caps each carry a reason and a real failure. I judged them load-bearing. The evidence file lacks the zsh_history and zzqqxx cases, so if they are trimmed they must be moved, not deleted.
- **"Why this rule is eager" sections** in `zero-skip-policy.md:59-65` and `clean-git-state.md:44-49`: redundant with `md-size-budgets.md`, but not contradictory. Left alone.
- **`.devcontainer/AGENTS.md:13,153-155,187`:** dated specifics ("Phase 2 … currently minimal", a hotfix PR list, "Runtime as of 2026-04-09").
- **`python/AGENTS.md:75-77`:** a one-off statistic ("33 of 33 … 11").
- **`python/AGENTS.md:19`:** "16 env vars" could not be verified; the config nests sub-configs, so any count is ambiguous.
- **`md-size-budgets.md:98-100`:** "reportedly" hedges a harness fact.
- **`.claude/CLAUDE.md:44`:** "Without being reminded, on ANY session model" is routing trigger text, synced byte-for-byte with knowledge-base and bound by `orchestration.trigger-armed`, so keep-list #6 applies.
- **`ai-cli-invocation.md:46`:** a version header that labels itself and tells the reader to re-probe.

### Outside this slice (for whoever owns hooks and skills)

- The graphify PreToolUse hook injects "MANDATORY … You MUST run `mise run graphify-query` … before grepping raw files" on every Bash call, including `wc`, `sed` and `security`. That is pressure language on a per-call cadence, and it is wrong for prose searches because the graph has no markdown nodes.
- `.claude/skills/devcontainer-sync/SKILL.md:55` also says "~38GB".
- The description at `suites.toml:2393` also says "Opus 5".

## Probes and control arms

These are the probes behind the findings that rest on a measurement rather than a quote.

- **F-A10 (mise which):**
  - `mise which hk`, a project tool, resolves to `~/.local/share/mise/installs/hk/1.57.0/hk`.
  - `mise which age`, a global-only tool, resolves to `~/.local/share/mise/installs/aqua-filo-sottile-age/1.3.2/age/age`. Both pass the rule's check.
  - `mise ls --current typos` prints the source config per row: global 1.50.2 against `shared.toml` 1.50.1. That column is what tells them apart.
- **F-A13 (SSH-agent proxy):**
  - `git grep -niE 'agent.?proxy|ssh.?proxy|socat'` over `devcontainer.json`, `python/src`, `scripts` and `mise.toml` returns 0 hits.
  - As a control, `ssh-auth.sock` returns 3 hits in the same files (`devcontainer.json:40,124,221`).
  - `initializeCommand` is defined at `devcontainer.json:235`.
- **F-A7 (background runs):**
  - `$CC/tools-reference.md:180`: "A command that the main conversation or a background subagent started keeps running after a final response". Control: `grep -c run_in_background` on that file → 1.
  - The saved memory `feedback_harness_background_run_survives_idle_and_cap` records `land` surviving 12m15s of idle with rc=0.

## Checked and found clean

- **Rules with no dated patterns:** `zero-bash-logic`, `real-integration-evidence`, `goal-history`, `research-repo-enumeration`, `tool-currency-and-native-first`, `local-devcontainer-first`.
- **`clarify-before-acting`:** every prohibition has a reason and is machine-enforced.
- **`persistence-gate-retry`:** its ~21.5GB matches the 22GB image.
- **`codex-sdlc-team`:** the body (everything except its intro) is context the model can't get elsewhere.
- **Spot-checked claims that held:**
  - "12 codex wrappers": `ls .claude/agents/codex-*.md` → 12.
  - `codex_lane.py` still passes `--ephemeral`: 2 hits.
  - `claude-advisor` is `model: fable`, `effort: xhigh`.
  - Three agents use `memory: local`.
- **Secrets rule 7's presence check:** `echo "${DOPPLER_TOKEN:+SET}"` printed only `SET`, and the `[ -n ]` form printed `SET` too. The recommended form works and neither exposed the value.
- **Group 1b and group 4 signals:** none.

## Proposed diff

All hunks are against the current `docs/prompt-audit-2026-09-24` tree, one block per finding, and each passes `git apply --check`. The blocks use `~~~~` fences because some hunks contain triple-backtick lines.

### F-A1

~~~~diff
--- a/.claude/CLAUDE.md
+++ b/.claude/CLAUDE.md
@@ -2,7 +2,7 @@
 
 Claude-only configuration. The root `CLAUDE.md` is byte-exactly `@AGENTS.md`
-(`claude_md_import_stub`) and `AGENTS.md` is at 200/200 lines, so anything that
-is Claude-specific and doesn't fit there lives here. `.claude/**` is exempt from
-the stub and pair checks precisely so this file can exist.
+(`claude_md_import_stub`) and `AGENTS.md` sits at agnix AGM-003's 12,000-char
+cap, so anything Claude-specific that doesn't fit there lives here. `.claude/**`
+is exempt from the stub and pair checks precisely so this file can exist.
 
 ## Agent skills, trackers and domain docs
~~~~

### F-A2

~~~~diff
--- a/.claude/CLAUDE.md
+++ b/.claude/CLAUDE.md
@@ -44,5 +44,5 @@
 - Without being reminded, on ANY session model: non-trivial implementation runs the architect-as-orchestrator flow — invoke this repo's routing-doctrine skill (`codex-sdlc-team` in dotfiles, `orchestrator-routing` in knowledge-base) before delegating and follow it as authoritative for routing, the spec contract, review tiers, and advisor escalation.
 
-The trigger is **deliberately UN-gated** (default `/model` is Opus 5) and is
+The trigger is **deliberately UN-gated** (it must fire on any session model) and is
 rule-synced byte-for-byte with knowledge-base. It replaced the fable-orchestrator
 plugin's trigger when that plugin was removed (#1310); the doctrine now lives in
~~~~

### F-A3

~~~~diff
--- a/.claude/CLAUDE.md
+++ b/.claude/CLAUDE.md
@@ -49,8 +49,8 @@
 the `codex-sdlc-team` skill, versioned and gated here.
 
-### There is no `grok` here — codex lanes only, stop asking
+### Lane routing — codex and Claude only
 
-`grok` is NOT installed (2026-09-01), so every lane resolves to codex or to
-Claude and nothing can fall back to grok. Route by this fixed table:
+Every lane resolves to codex or to Claude; no other agent CLI is installed.
+Route by this fixed table:
 
 | Lane | Use |
@@ -72,7 +72,7 @@
 
 ⚠️ **No `codex-*` lane is the cold-review lens for a codex diff** — same model
-family as the implementer, so it inherits its blind spots. With grok gone,
-Claude IS the other family, so an Opus cold pass on a codex diff is the full
-gate, not a degraded one.
+family as the implementer, so it inherits its blind spots. Claude is the
+other family, so an Opus cold pass on a codex diff is the full gate, not a
+degraded one.
 
 ⚠️ Permanent advisor-consult routing and escalation: see @token-routing.md.
--- a/python/verification/suites.toml
+++ b/python/verification/suites.toml
@@ -2410,5 +2410,5 @@
 paths = [".claude/CLAUDE.md"]
 lines = [
-    "### There is no `grok` here — codex lanes only, stop asking",
+    "### Lane routing — codex and Claude only",
     "| Implementation | `codex-{sol,astra}-implementer`, effort `xhigh` — OURS, at full access |",
     "| Cold review of a codex diff | an Opus subagent, diff-only (`Agent`, `model: \"opus\"`) |",
--- a/tests/test_verify.py
+++ b/tests/test_verify.py
@@ -179,5 +179,5 @@
 
 #: A whole line that really is in `.claude/CLAUDE.md` (the lane-table heading).
-_REAL_LINE = "### There is no `grok` here — codex lanes only, stop asking"
+_REAL_LINE = "### Lane routing — codex and Claude only"
 
 _TRIGGER = (
~~~~

### F-A43

~~~~diff
--- a/.claude/CLAUDE.md
+++ b/.claude/CLAUDE.md
@@ -64,5 +64,5 @@
 | Multi-domain SDLC review | codex-side team — [[codex-sdlc-team]] |
 
-New roster: `gate-runner`, `cold-reviewer`, `graphify-operator`, `graphify-researcher`,
+Repo-owned agents: `gate-runner`, `cold-reviewer`, `graphify-operator`, `graphify-researcher`,
 `spec-scribe`, `pwf-scribe`, `issue-filer`, `claude-advisor`, `premise-verifier`.
 Saved workflows: `/gated-implementation`, `/graphify-refresh`.
~~~~

### F-A4

~~~~diff
--- a/.claude/token-routing.md
+++ b/.claude/token-routing.md
@@ -1,7 +1,3 @@
 # Advisor-consult routing
-
-Relocated out of the Claude-specific project config (#994) to keep that file
-inside agnix's recommended token budget (CC-MEM-009); its permanent posture was
-ratified by the 2026-09-10 `/grilling` pass.
 
 **Advisor consults permanently route to a `codex-*-advisor` subagent** — its
@@ -38,7 +34,2 @@
 `mise run codex-lane-mirror` (`-- --check` gates the drift). Edit the sol lane
 and regenerate; an edit to an astra lane is overwritten and fails the check.
-
-Ray, 2026-09-11: "we want the ability to use both models". Before this, all five
-lanes hard-pinned sol while the user-global codex config had moved to astra —
-the pin was written to MATCH global inheritance and silently diverged from it
-when global changed.
~~~~

### F-A5

~~~~diff
--- a/.claude/rules/long-running-command-hangs.md
+++ b/.claude/rules/long-running-command-hangs.md
@@ -111,5 +111,5 @@
 - `python/src/dotfiles_setup/lint.py` — the guarded hk runner.
 - `gh-cli-watch.md` — sibling rule: use `--watch`, never sleep-poll.
-- `ci-local-parity.md` — hk pkl-cache clearing after `hk.pkl` edits.
+- `ci-local-parity.md` — every CI lint step has a local hk equivalent.
 - Memory: `feedback_long_running_tail_logs`, `feedback_pipe_kills_exit_code`.
 - CLAUDE.md → `AGENTS.md` "Validate before committing" — prefer `mise run lint`.
~~~~

### F-A6

~~~~diff
--- a/.claude/rules/long-running-command-hangs.md
+++ b/.claude/rules/long-running-command-hangs.md
@@ -79,6 +79,6 @@
 5. **hk specifics.** hk parallelises via per-file read/write locks
    *within* a run; a crashed/killed run can leave stale state under
-   `~/.local/state/hk/`. (The old "clear the pkl config cache" guidance is
-   retired — content-hashed since hk 1.47; `ci-local-parity.md` rule 5.)
+   `~/.local/state/hk/`. The pkl-eval cache is content-hashed, so editing
+   `hk.pkl` needs no cache clearing.
 
 6. **The ruff-error wedge is FIXED (#268), and it was never ruff.** Root
--- a/.claude/rules/ci-local-parity.md
+++ b/.claude/rules/ci-local-parity.md
@@ -50,13 +50,5 @@
 deps without changing cwd. This applies to hk.pkl steps and mise tasks.
 
-## Rule 5: Clear hk cache after editing hk.pkl
-
-RETIRED (#160 T12, hk 1.49): the pkl-eval cache is content-hashed since
-hk 1.47 (stale-serve impossible) and the default pklr backend evaluates
-import/spread identically to the pkl CLI (parity probe-verified), so the
-`HK_PKL_BACKEND=pkl` override was dropped. Kept as a numbered rule so
-references to "rule 5" stay valid.
-
-## Rule 6: Test new hk steps locally before committing
+## Rule 5: Test new hk steps locally before committing
 
 When adding a new step to hk.pkl:
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -80,8 +80,7 @@
 - `hk-image.pkl` — Docker image checks; imports and spreads `hk-common.pkl` groups
 
-hk 1.49's default pklr backend evaluates the import/spread config
-identically to the pkl CLI (parity probe-verified #160 T12; the
-`HK_PKL_BACKEND=pkl` override is retired). The pkl-eval cache is
-content-hashed since hk 1.47 — no manual cache clearing after edits.
+hk's default pklr backend evaluates the import/spread config identically
+to the pkl CLI, and its pkl-eval cache is content-hashed — edits need no
+manual cache clearing.
 
 ## Testing
~~~~

### F-A7

~~~~diff
--- a/.claude/rules/long-running-command-hangs.md
+++ b/.claude/rules/long-running-command-hangs.md
@@ -33,9 +33,11 @@
    Its deadline is mandatory and expiry returns rc=124 with the awaited target.
 
-   **EXCEPTION — Mac-side container ops: background-and-idle gets them
-   REAPED.** `mise run ship`/`land`, `verify-local`, `sync`, and image pulls
-   are killed if the turn goes idle waiting on them. What works is **in-turn
-   polling**: background the command, then keep the turn engaged reading its
-   log:
+   **Mac-side container ops** (`mise run ship`/`land`, `verify-local`,
+   `sync`, image pulls): from the main conversation, launch them with the
+   harness `run_in_background` and a file-captured rc
+   (`… > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`), then read the `rc=` line
+   when the completion notice arrives — the command keeps running after the
+   turn ends. A foreground subagent's background commands stop at its final
+   response, so a subagent keeps its turn engaged with a bounded poll:
 
    ```bash
~~~~

### F-A8

~~~~diff
--- a/.claude/rules/long-running-command-hangs.md
+++ b/.claude/rules/long-running-command-hangs.md
@@ -82,18 +82,9 @@
    retired — content-hashed since hk 1.47; `ci-local-parity.md` rule 5.)
 
-6. **The ruff-error wedge is FIXED (#268), and it was never ruff.** Root
-   cause was **`depends` + `fail_fast = false`** — hk never releases a
-   dependent whose dependency FAILED, so `ruff_format` sat at `waiting
-   for ruff` forever. `hk.pkl`'s `no_hk_depends` step blocks `depends`
-   from coming back.
-
-   Generalisation, learned by publishing the wrong diagnosis twice:
-   **a scary log line adjacent to a hang is not the hang** (`failed to
-   get write locks …` is a benign DEBUG retry; the wedge was one line
-   lower). Confirm a suspect by removing it and re-probing. Both red
-   herrings: `docs/rules-evidence/long-running-command-hangs.md`.
-
-   Durable habit: **when lint hangs, run `uv run --project python ruff
-   check` DIRECTLY** — seconds, and it never lies about your own code.
+6. **A scary log line next to a hang is not the hang.** Confirm a suspect by
+   removing it and re-probing (the #268 wedge was `depends` + `fail_fast =
+   false`, now blocked by `no_hk_depends`; its red herrings are in the evidence
+   file). When lint hangs, run `uv run --project python ruff check` directly —
+   it takes seconds and separates your own code from hk's scheduling.
 
 7. **Find the wedged step by name.** Grep the lint output for a
~~~~

### F-A10

~~~~diff
--- a/.claude/rules/ci-local-parity.md
+++ b/.claude/rules/ci-local-parity.md
@@ -31,5 +31,7 @@
 Global mise tools are invisible to CI runners.
 
-Verification: `mise which <tool>` should resolve under `~/.local/share/mise/installs/`.
+Verification: `mise ls --current <tool>` — the source column must name
+`mise.toml` or `.config/mise/conf.d/shared.toml`, never `~/.config/mise/config.toml`.
+(`mise which` cannot tell them apart: global and project tools share one install root.)
 
 ## Rule 3: Use mise binary names, never npx
~~~~

### F-A11

~~~~diff
--- a/.claude/rules/ci-local-parity.md
+++ b/.claude/rules/ci-local-parity.md
@@ -29,5 +29,4 @@
 installs both — parity holds. What must NOT be relied on is a tool present
 only in global `~/.config/mise/` (invisible to CI).
-Global mise tools are invisible to CI runners.
 
 Verification: `mise which <tool>` should resolve under `~/.local/share/mise/installs/`.
~~~~

### F-A13

~~~~diff
--- a/.devcontainer/AGENTS.md
+++ b/.devcontainer/AGENTS.md
@@ -116,6 +116,6 @@
 
 Bringing the container up is **always a terminal action**: `mise run
-up` (start) / `mise run down` (stop). Both spawn / tear down the host
-SSH-agent proxy via `initializeCommand`.
+up` / `mise run down`. `initializeCommand` (`uv run … dotfiles-setup docker
+initialize-host`) needs the terminal's `mise`/`uv` environment.
 
 Attaching an IDE to the running container:
@@ -130,6 +130,6 @@
 > ⚠️ **Never `Reopen in Container` (VS Code) or "create new dev
 > container" (CLion) from a dock-launched IDE.** macOS GUI processes
-> don't inherit terminal env; `initializeCommand` then fails to spawn
-> the host-side SSH agent proxy.
+> don't inherit terminal env, so `initializeCommand` cannot find `uv` and
+> fails.
 
 ## Mise Cookbook Paths
--- a/.claude/rules/do-not.md
+++ b/.claude/rules/do-not.md
@@ -7,6 +7,7 @@
 1. **Do NOT launch CLion or VS Code from the dock for devcontainer work.**
    macOS GUI processes don't inherit terminal env, so `mise`, `uv`, and
-   `$SSH_AUTH_SOCK` are not available to `initializeCommand`, which then
-   fails to spawn the host-side SSH agent proxy. Terminal only. See
+   `$SSH_AUTH_SOCK` are not available to `initializeCommand`
+   (`uv run … dotfiles-setup docker initialize-host`), which then fails.
+   Terminal only. See
    `.devcontainer/AGENTS.md`.
 
~~~~

### F-A14

~~~~diff
--- a/.devcontainer/AGENTS.md
+++ b/.devcontainer/AGENTS.md
@@ -20,5 +20,5 @@
 | `Dockerfile.host-user` | Thin overlay adding the host UID/GID; sets `USER`/`LOGNAME`/`HOME` ENV (`HOME=/home/${DEVCONTAINER_USER}` = the home-volume mount target) |
 | `devcontainer.json` | Devcontainer spec (containers.dev) — lifecycle hooks, features, volumes, dynamic naming |
-| `mise-system.toml` | BASE tool tier (#160 T9) → `/usr/local/share/mise/config.toml`. `[bootstrap.packages]` declares the apt set installed by `mise bootstrap packages apply` (#160 T4); the 20 host↔image shared tools come from the repo `.config/mise/conf.d/shared.toml` COPYd to `conf.d/` and merged (#160 T5) |
+| `mise-system.toml` | BASE tool tier (#160 T9) → `/usr/local/share/mise/config.toml`. `[bootstrap.packages]` declares the apt set installed by `mise bootstrap packages apply` (#160 T4); the host↔image shared tools come from the repo `.config/mise/conf.d/shared.toml` COPYd to `conf.d/` and merged (#160 T5) |
 | `mise-runtime.toml` | RUNTIME tool tier (#160 T9/T10) → `config.runtime.toml`, installed in the `devcontainer-runtime` stage under `MISE_ENV=runtime` (baked ENV). The interactive OVERLAY tier lives in `home/dot_config/mise/config.toml.tmpl`, eager-installed per-user by `on-create.sh` |
 | `mise-system.lock` + `mise-runtime.lock` + `P2996-CACHE.md` | Native mise lockfiles per tier, per tool **per published arch** (`linux-x64` + `linux-arm64` since #698, via `lockfile_platforms`). COPYd to `mise.lock` / `mise.runtime.lock`, consumed by `mise install --system --locked`; base digest feeds base-hash, runtime pair feeds dev-hash. Regenerate via `mise run lock-image`, never a hand-rolled `mise lock` (#650). A `shared.toml` bump ALSO needs `mise run lock-shared` — different file, and `lock-image` never touches it (#790) |
~~~~

### F-A16

~~~~diff
--- a/.claude/rules/gh-cli-watch.md
+++ b/.claude/rules/gh-cli-watch.md
@@ -1,14 +1,15 @@
-# gh CLI: Always use `--watch`, Never Hand-Roll Poll Loops
+# gh CLI: Let ship/land Wait on CI; Read State One-Shot
 
-When waiting on a GHA workflow run or PR check completion via the
-`gh` CLI, use the built-in `--watch` flags. Never hand-roll a
-`while ! gh ... | grep ...; do sleep; done` polling loop.
+Waiting on PR checks or a workflow run is owned by `mise run ship` (PR
+checks to bucket-verified green) and `mise run land -- <PR#>` (main CI). For
+a point-in-time read use a one-shot `--json` query. Do not hand-roll a wait:
+the PreToolUse guard denies `gh pr checks --watch`, `gh run watch`, and
+unbounded `while`/`until` + `sleep` loops.
 
 ## Why this rule exists
 
-`gh` has first-class live-monitoring with correct refresh intervals,
-exit codes, and table updates. A hand-rolled loop has none of that: it
-buries the real exit code (the `grep` becomes the shell's exit), races
-on multi-run queues, burns API quota, and shows the operator nothing.
+A hand-rolled loop buries the real exit code (the `grep` becomes the
+shell's exit), races on multi-run queues, burns API quota, and shows the
+operator nothing; the ship/land tasks read `--json` buckets instead.
 
 The canonical break: under `set -o pipefail`, `cmd | grep -q PAT`
@@ -16,6 +17,6 @@
 That is `hk.pkl`'s `no_grep_q_under_pipefail` step.
 
-⚠️ `gh run watch --exit-status` has reported **0 prematurely** — always
-cross-verify with `gh run view <id> --json conclusion`.
+`gh run watch --exit-status` has reported **0 prematurely** — one reason it
+is denied; the API `conclusion` field is the source of truth.
 
 Full rationale, the anti-pattern catalogue, and when Claude Code's
@@ -25,27 +26,9 @@
 ## Canonical patterns
 
-### Wait for all PR checks to finish
-
 ```bash
-# In a long-running terminal:
-gh pr checks 123 --watch --interval 30
-
-# In a script that should fail loud on any check failure:
-gh pr checks 123 --watch --fail-fast
-echo "exit=$?"
-```
-
-### Wait for a specific run
-
-```bash
-gh run watch 1234567890 --exit-status
-# Cross-verify per feedback_gh_run_watch.md:
-gh run view 1234567890 --json conclusion --jq '.conclusion'
-```
-
-### Watch the current branch's PR
-
-```bash
-gh pr checks --watch        # auto-detects from current branch
+mise run ship                        # opens the PR and waits for its checks
+mise run land -- 123                 # after merge: waits on main CI, validates
+gh pr checks 123 --json name,bucket  # one-shot read of PR checks
+gh run view 1234567890 --json conclusion --jq '.conclusion'  # one run
 ```
 
@@ -65,6 +48,5 @@
 
 All scripts, hooks, skills, agents, and ad-hoc Bash invocations in
-this repo. When `gh` documentation lists a `--watch` flag for any
-subcommand (`pr checks`, `run`, `workflow`, `pr status`), use it.
+this repo.
 
 ## See also
--- a/.claude/rules/verify-before-advancing.md
+++ b/.claude/rules/verify-before-advancing.md
@@ -35,5 +35,5 @@
 | Validating **through the devcontainer** (any change you test in-container) | `mise run verify-container-latest` — the running container must bind-mount THIS workspace (source = latest branch code) and pass smoke; **base-currency is a hard gate** (smoke tier-1 identity fails a base predating the current `mise-system.toml`). See "Validate against the latest branch code" below. |
 | `.claude/CLAUDE.md`, `.claude/settings.json`, `rule-sync.toml` | `mise run rule-sync` — the declared cross-repo set must hold in dotfiles AND knowledge-base. SKIPs loudly without the sibling clone; hard-FAILs in CI (#354 tier 0) |
-| Opened a PR | `gh pr checks <n> --watch` until terminal — every check `pass` or `skipping`, **0 fail** |
+| Opened a PR | `mise run ship` waits until terminal — every check `pass` or `skipping`, **0 fail**; confirm with a one-shot `gh pr checks <n> --json name,bucket` |
 | Merged to `main` | Await the main `ci.yml` run and confirm `conclusion == success` (incl. `promote` retagging `:dev`) |
 
@@ -87,6 +87,6 @@
   failure) and never a background-task "completed" notification's exit
   code. See memory `feedback_pipe_kills_exit_code`, and issue #142.
-- `gh run watch --exit-status` has reported 0 prematurely — cross-verify
-  with `gh run view <id> --json conclusion --jq .conclusion`. See
+- Read CI state from `gh run view <id> --json conclusion --jq .conclusion`
+  (`gh run watch --exit-status` has reported 0 prematurely). See
   `gh-cli-watch.md` and `feedback_gh_run_watch`.
 - A "skipped" job is a *valid terminal state* (e.g. warm-path
@@ -121,5 +121,5 @@
 - `long-running-command-hangs.md` — bound `mise run lint`; never wait blind.
 - Memory `feedback_pipe_kills_exit_code` — read the rc, not a piped tail.
-- `gh-cli-watch.md` — use `--watch`; cross-verify `gh run watch`.
+- `gh-cli-watch.md` — ship/land own CI waits; one-shot `--json` reads.
 - `do-not.md` — project invariants that never bend regardless of green checks.
 - CLAUDE.md → `AGENTS.md` "Validate before committing".
--- a/.claude/rules/long-running-command-hangs.md
+++ b/.claude/rules/long-running-command-hangs.md
@@ -52,7 +52,6 @@
    mise tasks; `&&` and `2>&1` remain allowed.
 
-   **Backgrounding stays correct for CI/remote waits** (`gh pr checks --watch`,
-   `gh run watch`) — those run on GitHub's infrastructure and nothing local
-   reaps them. The hazard is specifically local, long, Mac-side work.
+   **CI/remote waits** are owned by `mise run ship`/`land`, which watch
+   GitHub-side checks themselves (see `gh-cli-watch.md`).
 
    For `mise run lint`, the symlink
@@ -104,5 +103,5 @@
 
 `hk` (use `mise run lint`), `mise install`, `docker buildx`/`devcontainer
-up`, `gh` waits (use `--watch`, see `gh-cli-watch.md`), and any other
+up`, `gh` waits (see `gh-cli-watch.md`), and any other
 network- or IO-bound command an agent or human launches in this repo.
 
@@ -110,5 +109,5 @@
 
 - `python/src/dotfiles_setup/lint.py` — the guarded hk runner.
-- `gh-cli-watch.md` — sibling rule: use `--watch`, never sleep-poll.
+- `gh-cli-watch.md` — sibling rule: ship/land own CI waits; never sleep-poll.
 - `ci-local-parity.md` — hk pkl-cache clearing after `hk.pkl` edits.
 - Memory: `feedback_long_running_tail_logs`, `feedback_pipe_kills_exit_code`.
--- a/.github/workflows/AGENTS.md
+++ b/.github/workflows/AGENTS.md
@@ -146,6 +146,6 @@
 - **`uv run --project python`**, not `--directory` (changes cwd, breaks
   relative test paths).
-- **Use `--watch`, never sleep-poll**; `gh run watch --exit-status` is
-  unreliable, cross-verify `--json conclusion`. `.claude/rules/gh-cli-watch.md`.
+- **CI waits belong to `mise run ship`/`land`**; one-shot reads use `--json`
+  (`gh run view <id> --json conclusion`). `.claude/rules/gh-cli-watch.md`.
 - **No `type=gha` cache on `base`/`p2996-cache` targets**: registry tag +
   `Probe cache` IS the durable cache; `mode=max` gha export exceeds the 1h
~~~~

### F-A17

~~~~diff
--- a/.claude/rules/verify-before-advancing.md
+++ b/.claude/rules/verify-before-advancing.md
@@ -64,5 +64,5 @@
   `mise run dev-rebuild` (pulls the registry `:dev`; on a slow link this is
   a long buildkit pull — never classic `docker pull`, which wedges on the
-  ~38GB image, see `feedback_mise_local_toml_replaces_task`);
+  large image, see `feedback_mise_local_toml_replaces_task`);
 - **it runs** — smoke tiers 1-3 pass in the container.
 
@@ -74,5 +74,5 @@
 current `mise-system.toml`, so refreshing to it is the *only* way to test
 the latest code — there is no valid local shortcut. On a slow link the
-~38GB buildkit pull can take hours; that is expected and fine. Background
+multi-GB buildkit pull can take hours; that is expected and fine. Background
 it (`mise run dev-rebuild`, or a `docker buildx build --pull --output
 type=docker` of `:dev` — buildkit, never classic `docker pull` which
--- a/.claude/rules/mise-tasks-only.md
+++ b/.claude/rules/mise-tasks-only.md
@@ -13,5 +13,5 @@
 | bare `pytest` | `mise run test`, or `uv run --project python pytest <target>` (doc-level only: the permission engine unwraps runners, so a hook rule would also deny the canonical uv form) |
 | `devcontainer up` / `devcontainer build` | `mise run up` / `mise run dev-rebuild` (env + arch-scoped name resolution) |
-| `docker pull …dotfiles-devcontainer…` | `mise run sync` (buildkit, digest-aware, verifying; classic pull wedges on ~38GB) |
+| `docker pull …dotfiles-devcontainer…` | `mise run sync` (buildkit, digest-aware, verifying; classic pull wedges on the large image) |
 | `gh pr create` (+ push + gates by hand) | `mise run ship` |
 | `gh pr merge` (+ watch + validate by hand) | `mise run land -- <PR#>` (post-merge) |
~~~~

### F-A18

~~~~diff
--- a/.claude/rules/verify-before-advancing.md
+++ b/.claude/rules/verify-before-advancing.md
@@ -107,11 +107,7 @@
 confirming the delegate's checks actually passed).
 
-> **Carry a number with its CONDITION, not just its source.** This file is where
-> the ≤12,000-char misattribution was born: a real figure (Windsurf's, via agnix
-> AGM-003) travelled here without its source, was captioned to Anthropic, and was
-> then machine-enforced against files its real owner never governed. A true fact
-> without its provenance *or* its "true when" is indistinguishable from an
-> invented one. Three worked cases, and the habit that catches them:
-> `docs/rules-evidence/verify-before-advancing.md`.
+> **Carry a number with its CONDITION, not just its source** — a true figure
+> without its owner or its "true when" is indistinguishable from an invented
+> one. Worked cases: `docs/rules-evidence/verify-before-advancing.md`.
 
 ## See also
~~~~

### F-A19

~~~~diff
--- a/python/AGENTS.md
+++ b/python/AGENTS.md
@@ -50,6 +50,6 @@
 
 `dotfiles-setup verify run` executes contracts defined in
-`verification/suites.toml`. This gate is **distinct** from `hk run
-pre-commit --all` — some contracts (e.g., `build.no-stderr-suppression`)
+`verification/suites.toml`. This gate is **distinct** from `mise run
+lint` — some contracts (e.g., `build.no-stderr-suppression`)
 only run through the verify CLI. Run both locally before pushing
 Dockerfile changes.
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -92,5 +92,5 @@
 Structured verification via `python/verification/suites.toml` runs as CI
 `contract-preflight`. The `mise run verify` gate is **distinct
-from** `hk run check --all` — some contracts (e.g.,
+from** `mise run lint` — some contracts (e.g.,
 `build.no-stderr-suppression`) only run through the verify CLI. Run both
 locally before pushing Dockerfile changes.
~~~~

### F-A20

~~~~diff
--- a/tests/AGENTS.md
+++ b/tests/AGENTS.md
@@ -66,6 +66,5 @@
   code does, so it passes by construction and can never disagree with the
   code. Expected values must come from an **independent source of truth**: a
-  known-good literal, a worked example, the real artifact. The four
-  `test_memory_index.py` bugs above are this shape.
+  known-good literal, a worked example, the real artifact.
 - **A probe with no control arm** — a check that can only pass is not a check.
   Pin the FAIL direction next to the pass: tier-1 identity really fails on a
~~~~

### F-A21

~~~~diff
--- a/tests/AGENTS.md
+++ b/tests/AGENTS.md
@@ -23,11 +23,10 @@
 is on-demand reference — which is what it should be anyway.
 
-Total (measured 2026-09-14): **3,116 pytest tests** run by default (`pytest
-tests/` collects all `test_*.py` files) plus **11 gated exec tests** deselected
-by default — 5 `image_exec` (`mise run smoke-exec`, needs Docker + the `:dev`
-image) and 6 `codex_exec` (`mise run codex-lane-e2e`, spawns the real `codex`
-CLI and **costs credits** — 4 paid calls) — and Bats scenarios under `infra/`.
-3,127 collected in total; re-measure with `-m <marker> --collect-only` rather
-than trusting this line, which has drifted before.
+Collected counts drift fast, so measure rather than quote them:
+`uv run --project python pytest tests/ --collect-only -q`. Default runs
+deselect the gated exec tests — `image_exec` (`mise run smoke-exec`, needs
+Docker + the `:dev` image) and `codex_exec` (`mise run codex-lane-e2e`,
+spawns the real `codex` CLI and **costs credits**); inspect one with
+`-m <marker> --collect-only`. Bats scenarios live under `infra/`.
 
 ## Running tests
~~~~

### F-A22

~~~~diff
--- a/tests/AGENTS.md
+++ b/tests/AGENTS.md
@@ -83,15 +83,9 @@
   the rule yourself. When the table gains a cell, add the axis; **never edit an expected value to make a test pass**,
   which converts an independent expectation into a transcription of behaviour.
-  ⚠️ The mutation result that reads as proof is this shape's tell:
-  **"deleting the fix breaks ONLY the arm you just wrote" is the SIGNATURE OF
-  THE FAILURE, not evidence of quality** — it means test space and fix space
-  are the same size, which is exactly the condition under which an unenumerated
-  neighbouring cell exists. This is NOT a licence to skip mutation testing, and
-  it does not soften `probes-need-a-control-arm.md`: the mutation here is a
-  GOOD one — deleting the fix is the realistic regression — and its narrow
-  blast radius is a fact about your AXIS ENUMERATION, not about the mutation.
-  All three mutation-verified fixes in #601's review
-  loop directly caused the NEXT round's HIGH finding, and the phrase went into
-  three commit bodies as a boast
+  When deleting the fix breaks only the arm you just wrote, test space and fix
+  space are the same size — the condition under which an unenumerated
+  neighbouring cell exists — so enumerate the axes before calling it covered.
+  Keep mutation testing: the narrow blast radius is a fact about your axis
+  enumeration, not about the mutation
   (`docs/research/kb/reports/session-20260806-review-loop-reflection.md`).
 
~~~~

### F-A23

~~~~diff
--- a/.claude/rules/agent-report-persistence.md
+++ b/.claude/rules/agent-report-persistence.md
@@ -51,9 +51,4 @@
 registration tests are load-bearing. The required substrings must remain in
 one settings entry; splitting the contract across entries fails selfcheck.
-
-`SubagentStop` additional context reaches the **delegate**, not the
-coordinator. Parent-side injection would require a `PostToolUse` hook on the
-`Agent` tool, which this change does not add. The coordinator must still
-persist a delivered report at receipt.
 
 ## Rules
~~~~

### F-A24

~~~~diff
--- a/.claude/rules/do-not.md
+++ b/.claude/rules/do-not.md
@@ -79,7 +79,6 @@
     project builds, calls, or looks up: the tool's CLI or a plain HTTP **API**
     first, then `mcp2cli`, and native registration only as a documented last
-    resort. A registered server taxes **every** conversation's system prompt
-    with **every** tool's schema, forever — paying that for a call a `curl`
-    already makes is pure loss.
+    resort. Registering a server for a call a `curl` already makes adds a
+    process, a pin, an auth path and a failure mode for nothing.
 
     ✅ **NOT a "do not": a third-party plugin or skill that REQUIRES MCP.**
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -190,6 +190,3 @@
 
 See `.claude/rules/do-not.md` for the authoritative list of project
-invariants (dock launch, local base-image builds, raw docker CLI,
-stderr suppression, bulk `git add`, `gh run watch`, `claude mcp add`,
-docker context switch). Machine-enforced items also live in
-`hk.pkl`.
+invariants; machine-enforced items also live in `hk.pkl`.
~~~~

### F-A26

~~~~diff
--- a/.claude/rules/research-doc-sources.md
+++ b/.claude/rules/research-doc-sources.md
@@ -10,6 +10,6 @@
 
 00. **For AGENT-HARNESS behaviour, grep the knowledge-base's offline sources
-    FIRST.** `~/dev/github/ray-manaloto/knowledge-base/sources/` holds **36
-    source trees / 6,446 markdown files** (measured 2026-08-02), including
+    FIRST.** `~/dev/github/ray-manaloto/knowledge-base/sources/` holds the
+    offline source corpus, including
     `agent-harness-docs/docs/{claude-code,codex,cursor,opencode,pi}` — the
     **vendor's own docs**, on disk, greppable, zero round-trips.
~~~~

### F-A27

~~~~diff
--- a/.claude/rules/secrets-out-of-the-shell-env.md
+++ b/.claude/rules/secrets-out-of-the-shell-env.md
@@ -1,21 +1,18 @@
 # Secrets in the Shell Environment
 
-⚠️ **REVERSED 2026-08-02 by Ray, deliberately.** All credentials are now
-`env = true` (**56 sanctioned as of 2026-08-29**, with ONE deliberate carve-out:
+All credentials are `env = true` by Ray's decision (2026-08-02; the sanctioned
+set is `doctor.toml`'s `[fnox].env_true`), with ONE deliberate carve-out:
 `CLAUDE_CODE_OAUTH_TOKEN` is `env = "exec"` — it overrides `/login` in every new
 session and silently rebills to the old org, and it does NOT authenticate the
-Anthropic SDKs; see PR #811) — available in every terminal and inherited by every child process,
-including Claude Code, its subagents and any MCP server they spawn. The stated
-requirement was *"in sync and available to all terminals and ai/llm agents"*.
-This file is no longer "keep secrets out of the shell"; it is **the record of why
-that posture existed, what the reversal costs, and which parts still bind.**
+Anthropic SDKs; see PR #811. Every terminal and every child process — Claude
+Code, its subagents, any MCP server they spawn — inherits them. The stated
+requirement is *"in sync and available to all terminals and ai/llm agents"*.
 
-**Most of this rule survives the reversal, and rule 7 matters MORE.** What changed
-is one axis — where credentials live. What did not change: an environment dump is
-still unscannable and must never be committed (rule 1, gated by `no_env_dump`), a
-probe must still never print a value (rule 7, **partly** gated by `secret_value_substitution`),
-a non-secret must still not be marked secret (rule 3), and a clean scanner still
-means "ask what it can see" (rule 4). With 50 credentials in every child instead
-of 4, the blast radius of breaking any of those is **12.5× larger**, not smaller.
+So nothing confines a credential to a process, and rules 1, 4 and 7 below are
+the only line between every credential and a transcript or a commit: an
+environment dump is unscannable and must never be committed (rule 1, gated by
+`no_env_dump`), a probe must never print a value (rule 7, **partly** gated by
+`secret_value_substitution`), a non-secret must not be marked secret (rule 3),
+and a clean scanner means "ask what it can see" (rule 4).
 
 ⚠️ **A keychain credential can hang a background process forever — and that hang
@@ -58,36 +55,26 @@
    gitleaks 2 → 0, betterleaks 1 → 0 on the same content in two forms. That gap
    is why `no_env_dump` exists and why it is deliberately glob-less.
-2. ⚠️ **REVERSED — secrets now live in the shell by decision.** This rule used to
-   read *"a secret belongs to a process, not to a shell — reach for `fnox exec --`
-   rather than exporting."* That is no longer the posture (2026-08-02). The
-   consequence to internalise: `fnox exec` is no longer a confinement boundary,
-   because the parent shell already has everything. **Rules 1, 4 and 7 are now the
-   only things between 50 credentials and a transcript or a commit** — there is no
-   second line behind them any more.
+2. **No process-level confinement.** Secrets live in the shell by decision, so
+   `fnox exec` is not a confinement boundary — the parent shell already has
+   everything. Rules 1, 4 and 7 have no second line behind them.
 3. **Do not mark a non-secret as a secret.** Redaction is value-based, so a
    short or empty "secret" corrupts every log the tool writes.
 4. **When a scanner reports clean, ask what it can see.** Compression, encoding,
    and a path allowlist each turn "no findings" into "never looked".
-5. **A new SECRET is now the reviewed decision — the old trap inverted.** Under
-   `env = "exec"` the hazard was a *consumer* silently getting an empty `${VAR}`
-   and dropping to an anonymous tier (context7 MCP, 2026-07-29) — so **check a
-   consumer's authenticated identity, never its connection status** still holds
-   whenever anything is exec-only or absent. Under `env = true` that trap is gone
-   and the reviewed decision moves to the other end: **adding a secret to fnox now
-   puts it in every terminal and every agent by default**, so it must be added to
-   `doctor.toml`'s `env_true` set in the same reviewed diff, or the doctor
-   reports drift on the next session and someone "fixes" it back.
+5. **Adding a secret is a reviewed decision.** A secret added to fnox reaches
+   every terminal and every agent by default, so add it to `doctor.toml`'s
+   `env_true` set in the same reviewed diff, or the doctor reports drift next
+   session and someone "fixes" it back. For anything exec-only or absent,
+   **check a consumer's authenticated identity, never its connection status**:
+   an empty `${VAR}` silently drops a consumer to an anonymous tier (context7
+   MCP, 2026-07-29).
 6. **Diagnose by layer, and never run `fnox get` to do it** (it prints a value).
-   ⚠️ **The old first suspect is retired.** A present-under-`fnox exec` /
-   absent-in-shell split used to mean `env = "exec"` working as designed; under
-   `env = true` that outcome is **unreachable — except for the one carve-out
-   above**, so for any OTHER name an absent variable is a REAL failure — never
-   dismiss it. Order the new suspects: (a) a **hung `doppler` CLI**,
+   An absent variable is a REAL failure for every name except the carve-out
+   above — never dismiss it. Suspects, in order: (a) a **hung `doppler` CLI**,
    since fnox shells out to it and any uncached doppler-primary secret resolves
    through that child; (b) a stale **`MISE_ENV_CACHE`** entry, which can serve a
    dead name in ONE directory long after the config is byte-identically restored,
    and which `grep` cannot see because it is encrypted; (c) the declaration itself.
-   The recipes live in `docs/secrets-doppler-fnox-keychain.md` (rewritten to this
-   posture 2026-08-03).
+   The recipes live in `docs/secrets-doppler-fnox-keychain.md`.
 7. **⚠️ A probe's OWN STDOUT is an uncovered surface — print presence, never a
    value.** Every gate above guards a *file write* or a *spawn*; none guards the
@@ -100,5 +87,5 @@
    now gated (below), every other shape is carried by this rule alone.
 
-   ⚠️ **IT RECURRED THE SAME DAY — the safe form is only safe ALONE.**
+   ⚠️ **The safe form is only safe ALONE.**
    `${VAR:+SET}${VAR:-ABSENT}` opens with the form this rule recommends and is a
    **leak**: `:-` and `:=` are *value-emitting* substitutions, so a **set**
@@ -111,10 +98,8 @@
    still allows `${(P)k}` indirect expansion; this rule carries every other shape.
 
-   ⚠️ **There is no blast-radius cap any more.** Under `env = true` **all 50** are
-   printable by any probe, wrapped or not; `DOPPLER_TOKEN` is itself in the
-   sanctioned shell set. (This file once claimed "exactly the opt-in set" — already
-   false under `fnox exec`, and the reversal widened it to everything.) The
-   correction runs in the **worse** direction: assume every credential is reachable
-   from any shell. `docs/rules-evidence/secrets-out-of-the-shell-env.md`.
+   ⚠️ **There is no blast-radius cap.** Every credential is printable by any
+   probe, wrapped or not; `DOPPLER_TOKEN` is itself in the sanctioned shell
+   set. Assume every credential is reachable from any shell.
+   `docs/rules-evidence/secrets-out-of-the-shell-env.md`.
 
 8. **⚠️ A FILE can be the credential, and "it's config" is not evidence.** Rule 7
~~~~

### F-A28

~~~~diff
--- a/.claude/rules/secrets-out-of-the-shell-env.md
+++ b/.claude/rules/secrets-out-of-the-shell-env.md
@@ -21,25 +21,17 @@
 ⚠️ **A keychain credential can hang a background process forever — and that hang
 is NOT a locked keychain.** `security show-keychain-info` **prompts
-unconditionally**, so its hang proves nothing; believing it cost ~2 hours on
-2026-08-02. Arm it instead: **fnox reads a keychain secret in 0.03s**, which a
-locked keychain cannot do. What actually blocks is an *authorization* dialog for
-an item a non-GUI process may not read — and nothing can answer that dialog.
-Measured: `gh` and `doppler` both kept their tokens in the keychain and hung
-forever from background processes (**190 stuck processes**, load 13.5). The
-discriminating arm is the same command with an isolated config dir, which returns
-in **0.45s**. Both entries were deleted (`security delete-generic-password -s
-'gh:github.com'` / `-s 'doppler-cli'`) and both then fell through to their ENV
-token.
+unconditionally**, so its hang proves nothing; fnox reading a keychain secret
+in 0.03s is the arm that rules a lock out. What blocks is an *authorization*
+dialog for an item a non-GUI process may not read — nothing can answer it. The
+discriminating arm is the same command with an isolated config dir.
 
-⚠️ **BOTH ENTRIES ARE BACK — measured 2026-09-12, so the paragraph above is
-HISTORY, not current state.** `security find-generic-password -s` returns rc=0
-for `gh:github.com` (created 2026-08-26) and `doppler-cli` (2026-08-04);
-control arm, a bogus service name → rc=44, against 286 keychain entries.
-Something re-created them after the 2026-08-02 deletion. **The hang risk above
-is LIVE again**, which is why a mise `credential_command` must NOT be wired to
-`gh auth token` or `fnox get` (fnox is Doppler-primary for these names and
-shells out to the `doppler` CLI). Deleting them again is an OPERATOR action and
-wants its own triage — find what recreates them first, or it simply recurs.
-Evidence: `docs/research/kb/reports/agents/2026-09-12-gh-token-for-mise.md` §Q5.
+The `gh:github.com` and `doppler-cli` keychain entries are present (recreated
+after a 2026-08-02 deletion; `security find-generic-password -s` rc=0, bogus
+name rc=44, re-measured 2026-09-24), so **the hang risk is live**: never wire a
+mise `credential_command` to `gh auth token` or `fnox get` (fnox is
+Doppler-primary for these names and shells out to the `doppler` CLI).
+Deleting the entries is an OPERATOR action that needs its own triage — find
+what recreates them first. Evidence:
+`docs/research/kb/reports/agents/2026-09-12-gh-token-for-mise.md` §Q5.
 
 ⚠️ **This reaches fnox: its doppler provider SHELLS OUT to the `doppler` CLI**
~~~~

### F-A29

~~~~diff
--- a/.claude/rules/notepad-enforcement.md
+++ b/.claude/rules/notepad-enforcement.md
@@ -40,9 +40,4 @@
    tracked verbatim report.
 
-The former guidance named `oh-my-claudecode` notepad MCP tools. That plugin was
-disabled and those tools recorded zero invocations across 941 transcripts.
-They are removed only because the enabled plugin, root file, hooks, and
-read-only fallback now provide an observable replacement.
-
 ## Why
 
~~~~

### F-A30

~~~~diff
--- a/.claude/rules/agent-artifact-conventions.md
+++ b/.claude/rules/agent-artifact-conventions.md
@@ -4,8 +4,4 @@
 Anything that must survive a clone is tracked under `docs/`. Do not create
 ad-hoc directories in either tree.
-
-> **Renamed from `.omc/` (2026-07-25).** That name belonged to a plugin that
-> was not enabled. `.agent/` was control-armed before adoption; archaeology is
-> in `docs/rules-evidence/agent-artifact-conventions.md`.
 
 ## Two plan locations, two durability contracts
~~~~

### F-A31

~~~~diff
--- a/.claude/rules/agent-artifact-conventions.md
+++ b/.claude/rules/agent-artifact-conventions.md
@@ -92,9 +92,4 @@
    `SLASH_COMMAND_TOOL_CHAR_BUDGET` as a diagnostic/user setting, not a project
    workaround. Never rely on every installed skill being listed.
-
-   ⚠️ Earlier wording here claimed this budget is *shared with MCP tools*. The
-   corpus does not say that: `$CC/env-vars.md:466` scopes it to "skill metadata
-   shown to the Skill tool", and `$CC/skills.md:1050-1058` describes a
-   skill-listing budget throughout. Corrected rather than re-anchored.
 7. **Build reusable skills downward:** skill → mise task → Python library. The
    skill contains judgment; the task is the seam; mechanics are parameterized
~~~~

### F-A32

~~~~diff
--- a/.claude/rules/ai-cli-invocation.md
+++ b/.claude/rules/ai-cli-invocation.md
@@ -92,13 +92,6 @@
 is a reason to invent new argv here.
 
-⚠️ An earlier draft of this section credited Claude Code 2.1.261 with three
-environment variables. Two exist but neither is new nor about background
-output — `SLASH_COMMAND_TOOL_CHAR_BUDGET` is an explicitly *legacy* name for
-the skill-listing budget (`$CC/env-vars.md:466`) and `ENABLE_TOOL_SEARCH`
-governs MCP tool search (`$CC/agent-sdk__tool-search.md:32`). The third,
-`SLASH_COMMAND_TOOL_TOKEN_BUDGET`, **does not exist** — 0 hits across the
-corpus while the other two return hits on the same command. All three are
-absent from the saved 2.1.261 changelog. A plausible-looking variable name is
-the cheapest thing for a lane to invent; grep it before citing it.
+A plausible-looking environment-variable name is the cheapest thing for a lane
+to invent; grep the `$CC/` corpus for it before citing it.
 
 ## Re-probe rule
~~~~

### F-A33

~~~~diff
--- a/.claude/rules/ai-cli-invocation.md
+++ b/.claude/rules/ai-cli-invocation.md
@@ -68,12 +68,8 @@
 form rather than relying on lookup order.
 
-⚠️ **Do not restate this as "a bare `agy` resolves the stale copy" — measured
-2026-09-10, it does not.** Bare `agy --version` -> **1.1.24** (mise's install
-dir precedes `~/.local/bin` on this PATH) while `~/.local/bin/agy --version` ->
-**1.1.12**, so the stale copy is real but is NOT what runs here. `which -a agy`
-is the arm that settles it; PATH order is a property of the machine, not of the
-tool, so assert the explicit form and let the probe speak for the order. For raw
-Gemini, `gemini "prompt"` remains interactive and can hang; `-p`/`--prompt`
-selects headless mode and piped stdin is appended to that prompt.
+`which -a agy` shows which copy PATH order selects on this machine; keep the
+explicit form regardless. For raw Gemini, `gemini "prompt"` remains
+interactive and can hang; `-p`/`--prompt` selects headless mode and piped
+stdin is appended to that prompt.
 
 OpenCode accepts positional messages and `-m provider/model`; its `-p` means
~~~~

### F-A34

~~~~diff
--- a/.claude/rules/research-doc-sources.md
+++ b/.claude/rules/research-doc-sources.md
@@ -95,9 +95,8 @@
 ## MCP: two lanes. Which lane you are in decides the answer
 
-⚠️ **The old "every schema in every conversation, forever" cost is FALSE here**
-(measured 2026-07-30): Claude Code presents MCP tools **deferred — names only**,
-loading a schema on demand via `ToolSearch` — a **33×** difference. Do not cite
-that sentence, and never refuse a registration on its strength. Method and
-per-server table: `docs/rules-evidence/research-doc-sources.md`.
+Claude Code presents MCP tools **deferred — names only**, loading a schema on
+demand via `ToolSearch` (measured 33× smaller than eager schemas), so a
+registration's context cost is small; never refuse one on context grounds.
+Method and per-server table: `docs/rules-evidence/research-doc-sources.md`.
 
 The residual cost is small and the same either way. What actually differs
@@ -108,6 +107,5 @@
 whose features only work over MCP, is a normal thing to do. You are buying the
 plugin's value and paying its schema cost knowingly. Do not fight it, do not
-wrap it, do not refuse a useful plugin over this. Relaxed 2026-07-19; the
-`no_mcp_registration` hk step is gone and is not coming back.
+wrap it, do not refuse a useful plugin over this.
 
 **Lane 2 — anything THIS project builds, calls, or looks up: AVOID MCP.**
~~~~

### F-A35

~~~~diff
--- a/.claude/rules/mise-tasks-only.md
+++ b/.claude/rules/mise-tasks-only.md
@@ -36,22 +36,18 @@
 single-test `pytest path::test` via uv) are NOT wrapped and stay direct.
 
-**The `gh pr` redirects are REPO-AWARE (2026-07-23).** Dispatch is by the target
-repo, resolved from an explicit `-R`/`--repo`: dotfiles (or no `-R`, i.e. cwd) →
-`ship`/`land`; knowledge-base → `kb-ship`/`kb-land`; **any other repo → ALLOW**.
-Allowing the rest is deliberate — no canonical task exists for a sibling repo, so
-a deny would redirect to nothing and merely block real work. A real defect, not a
-hypothetical: the rules matched `gh pr merge` unconditionally, so a KB PR was
-denied and pointed at `mise run land` — a *dotfiles* task with no repo parameter,
-watching dotfiles' main CI. KB PRs #1 and #2 were merged by hand. **A guard whose
-redirect target cannot perform the redirected action is not enforcement, it is an
-outage.**
+**The `gh pr` redirects are REPO-AWARE.** Dispatch is by the target repo,
+resolved from an explicit `-R`/`--repo`: dotfiles (or no `-R`, i.e. cwd) →
+`ship`/`land`; knowledge-base → `kb-ship`/`kb-land`; **any other repo →
+ALLOW**, because no canonical task exists there and a deny would redirect to
+nothing. A guard whose redirect target cannot perform the redirected action
+is an outage, not enforcement.
 
-**It recurred along a second axis — PR PROVENANCE (#369).** Only `ship` arms
-auto-merge and a bot PR never runs it; `land` refuses an OPEN PR; `gh pr merge`
-redirected to `land`. #138/#236/#386 sat green, unmergeable. `automerge` is the
-missing verb: **bot-authored PRs ONLY**, armed and exited (required checks run
-against the merge RESULT, so a branch behind main is fine). `ship` gates the tree
-before arming and `automerge` does not, so one verb per provenance means no
-judgement call at the call site.
+**One verb per PR provenance.** Only `ship` arms auto-merge, a bot PR never
+runs it, and `land` refuses an OPEN PR — so `automerge` is the verb for
+**bot-authored PRs ONLY**, armed and exited (required checks run against the
+merge RESULT, so a branch behind main is fine). `ship` gates the tree before
+arming and `automerge` does not, so one verb per provenance means no
+judgement call at the call site. Incident history:
+`docs/rules-evidence/mise-tasks-only.md`.
 
 ## Enforcement layers (deep-research verified, 2026-07-07)
~~~~

### F-A37

~~~~diff
--- a/.claude/rules/graphify-first.md
+++ b/.claude/rules/graphify-first.md
@@ -16,6 +16,6 @@
   captured at SessionStart, not from the uv venv. Use `mise run
   graphify-upgrade` when package/skills and graph must move together.
-- Claude's permission deny also blocks the labeling command words anywhere in a
-  Bash string, including the double-quoted grep shape whose backticks zsh ran.
+- `permissions.deny` blocks any Bash string containing `graphify label`, even
+  inside a quoted grep; search for that phrase with the Grep tool instead.
 
 ## `fresh` now means "no scanned-corpus change since the build"
~~~~

### F-A36

This hunk covers only the rule side. The removed text also needs to go into a new file, `docs/rules-evidence/graphify-first.md`.

~~~~diff
--- a/.claude/rules/graphify-first.md
+++ b/.claude/rules/graphify-first.md
@@ -19,17 +19,7 @@
   Bash string, including the double-quoted grep shape whose backticks zsh ran.
 
-## `fresh` now means "no scanned-corpus change since the build"
+## What `fresh` means
 
-Health used to check only that the graph file existed, parsed, matched the schema,
-and that the INSTALLED graphify was the pinned version. **Nothing compared the
-graph to the code.** The graph in this clone was built 2026-08-31 and reported
-`fresh` for thirteen days and 76 commits, while this rule told every agent a
-`fresh` graph is citable and a PreToolUse hook made querying it MANDATORY before
-grepping. Two symbols a session needed that day — `plan_attest_main`,
-`claude_doctor_main` — were absent because their modules postdated the build,
-and the graph answered as though they did not exist. Measured against controls:
-`setup_parser` 76 hits, `handle_pr` 21, both subjects 0.
-
-`_staleness_problem` closes it with two independent sources: Git says what
+`_staleness_problem` decides it from two independent sources: Git says what
 changed after `built_at_commit` — a field **graphify itself** writes from HEAD
 at export time — while `graphify-out/manifest.json` says which relative paths
@@ -47,11 +37,4 @@
 if the build commit is unknown to Git, health fails closed as `stale`.
 
-Graphify 0.9.65 made equality alone too strict. Measured on 2026-09-22, a
-`mise.toml`-only commit advanced HEAD from `122a4de1` to `45e09803`, while both
-ordinary update and `--force` reported no topology change and left
-`built_at_commit` untouched. Because `mise.toml` is not a manifest key, that
-no-op rebuild is now correctly fresh; a newly added file with a scanned
-extension would still be stale.
-
 A graph carrying no `built_at_commit` is `stale` too. The pinned runtime always
 writes it, so its absence means the bytes did not come from that runtime — and
@@ -63,26 +46,16 @@
 ## Nothing records WHICH graphify built the graph
 
-**The two installs are aligned again as of 2026-09-21 — both 0.9.65.** `graphify`
-on bare `PATH` resolves the **user-global** pin
-(`~/.config/mise/config.toml`, outside this repo's review);
-`mise run graphify-query`/`graphify-rebuild` resolve **this repo's locked
-version** (`python/uv.lock`), which is what `graphify_health`'s
-`version drift` check compares against. `mise run pin-parity` now binds every
-repository-owned pin site, including the three tracked skill stamps. The
-user-global pin remains outside that registry by design; the shared checker
-compares the binary resolved from `DOTFILES_AMBIENT_PATH` with the lock and
-names the user-global mise fix when it drifts. SessionStart doctor invokes the
-offline form, so it never calls `mise latest` or probes graph health.
+`graphify` on bare `PATH` resolves the **user-global** pin
+(`~/.config/mise/config.toml`, outside this repo's review); the mise tasks
+resolve **this repo's locked version** (`python/uv.lock`), which
+`graphify_health`'s `version drift` check compares against. `mise run
+pin-parity` binds every repository-owned pin site; the SessionStart doctor's
+offline check names the user-global fix when the PATH binary drifts from the
+lock.
 
-The check reads whatever graphify package is installed in the process
-*checking* health right now. It says nothing about which binary actually
-*built* the graph bytes on disk — a graph rebuilt by a drifted PATH binary
-(a bare `graphify update .`) is indistinguishable from one built by the
-repo's pin, because nothing records who built it. **An earlier
-version of this rule claimed a rebuild stamp closed that gap; it did not —
-the stamp could only ever record whatever the rebuild itself always
-resolves, so the check it fed could never fail, and the one drift it
-existed to catch wrote no stamp at all. It was removed rather than kept as
-a check that always reports "fine".**
+Health reads the graphify installed in the *checking* process. Nothing records
+which binary *built* the graph bytes, so a graph rebuilt by a drifted PATH
+binary (a bare `graphify update .`) is indistinguishable from one built by the
+pin.
 
 So the guarantee here is **procedural, not enforced**: always run
~~~~

### F-A38

~~~~diff
--- a/.claude/rules/codex-sdlc-team.md
+++ b/.claude/rules/codex-sdlc-team.md
@@ -1,8 +1,5 @@
 # The codex SDLC Team: Six Specialists codex Itself Orchestrates
 
-This repo has a codex-side subagent team. A fresh Claude session had **no way to
-learn that** before this file existed: a grep for `sdlc` across the whole eager
-instruction surface returned ONE hit, in a comment explaining why a gate skips
-these files. The team was built, verified working, and invisible.
+This repo has a codex-side subagent team, which codex itself orchestrates.
 
 ## The roster
~~~~

### F-A39

~~~~diff
--- a/.claude/rules/do-not.md
+++ b/.claude/rules/do-not.md
@@ -51,10 +51,7 @@
    uncommitted work carries across a `git checkout -b` untouched.
 
-   ⚠️ **"Don't commit" was too late a gate.** On 2026-08-03 a whole session's
-   work — including two sub-agent reports — accumulated on `main` and nothing
-   said a word, because **hk is a git-hook system and never sees a write**. It
-   would only have fired at the commit. Ray's standing instruction is therefore
-   *"all work should be on a branch that can be on a PR"*, enforced *whenever
-   anything is modified*.
+   The gate is on the *write*, not the commit: hk is a git-hook system and never
+   sees an edit. Ray's standing instruction: *"all work should be on a branch
+   that can be on a PR"*.
 
    Machine-enforced (#400) in four layers, earliest first: the **PreToolUse
~~~~

### F-A40

~~~~diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -35,7 +35,7 @@
 ```
 
-The devloop is `mise run up` → work inside the container → `mise run down`.
-The legacy `dotfiles-setup docker {up,down}` wrapper has been replaced by
-the official `@devcontainers/cli` (pinned in `mise.toml`).
+The devloop is `mise run up` → work inside the container → `mise run down`
+(the official `@devcontainers/cli`, pinned in `mise.toml`) — not the legacy
+`dotfiles-setup docker up`/`down` subcommands.
 
 ## Key Files
~~~~

### F-A41

~~~~diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -130,5 +130,5 @@
 - **Zero-bash logic**: Non-trivial logic (env detection, tool config,
   validation) lives in `python/`. Bash is restricted to thin check/smoke
-  wrappers in `scripts/` (the old `install.sh` bootstrap was retired).
+  wrappers in `scripts/`.
 
 ### Validate before committing
@@ -170,5 +170,5 @@
 | `HK_MISE` | `1` | Enable mise integration for hk |
 | `CONTAINER_REGISTRY` | `ghcr.io` | Docker registry (use `CONTAINER_REGISTRY`, not `REGISTRY` — avoids HCL collision) |
-| `DEVCONTAINER_USER` | `${localEnv:USER}` (fallback: `devcontainer`) | Container user (UID 1000); passed through from host `USER` via `devcontainer.json`. Host-user migration is the current state — the legacy `vscode` value has been replaced. |
+| `DEVCONTAINER_USER` | `${localEnv:USER}` (fallback: `devcontainer`) | Container user (UID 1000); passed through from host `USER` via `devcontainer.json`. |
 | `DEVCONTAINER_SSH_PORT` | derived | Host-side port for R1 inbound ssh (container sshd is hardcoded `2222`). **Unset by default (#677)** — derived per workspace+architecture so two clones and two arches never collide; `mise run ssh-port` / `names`. Pin per-clone via `mise.local.toml`. Detail: `.devcontainer/AGENTS.md`. |
 | `DOTFILES_PLATFORM` | pinned in `mise.toml` `[env]` | **The one platform parameter** (#673). Every `--platform` site resolves from it; unset, it falls back to the host's native triple. `no_platform_literals` rejects a literal elsewhere |
~~~~

### F-A44

~~~~diff
--- a/.claude/rules/md-size-budgets.md
+++ b/.claude/rules/md-size-budgets.md
@@ -53,16 +53,9 @@
 misapply it to Claude-only files.
 
-The historical failure was provenance loss:
-
-1. `1f05365` created a 200-line gate with the correct source.
-2. `99a8506` (no longer resolvable in this repo) described an unenforced
-   12,000-character limit, likely copied from
-   agnix without its vendor bound.
-3. `010009d` (also no longer resolvable) changed code to match the prose and
-   credited Anthropic.
-
-   ⚠️ Only `1f05365` still resolves (`git cat-file -t` -> commit; the other two
-   -> unresolvable, same command, so the probe discriminates). The chain is
-   preserved as narrative, not as three followable refs.
+The historical failure was provenance loss: a correctly sourced 200-line gate
+(`1f05365`) later gained an unenforced 12,000-character limit copied from
+agnix without its vendor bound, and code was then changed to match the prose
+and credit Anthropic. The commit chain belongs in
+`docs/rules-evidence/md-size-budgets.md`.
 
 The initial correction also overreached: a zero-hit search in Anthropic's
~~~~

### F-A45

~~~~diff
--- a/.github/workflows/AGENTS.md
+++ b/.github/workflows/AGENTS.md
@@ -6,5 +6,5 @@
 ## Purpose
 
-GitHub Actions workflows implementing the 4-stage CI pipeline and
+GitHub Actions workflows implementing the CI pipeline and
 post-failure reporting.
 
@@ -59,5 +59,5 @@
 behavior unchanged):
 
-1. **lint** — mise install, hk pre-commit, agnix agent-doc validation
+1. **lint** — mise install, `hk run check --all`, agnix agent-doc validation
    (`agnix .`; `.agnix.toml` `severity = "Warning"` = non-blocking),
    `mise doctor --json`, `mise.lock` upload + cache. agnix uses the
~~~~

## GitHub repos touched

_None._ Everything was read from local clones: this repo, the knowledge-base offline harness docs under `$CC/`, and a user memory file. `gh pr checks 999999` was only a guard probe against this repo and returned "no such PR".