# Cold review — `47453338` (prompt-audit C applied to the agent roster)

- **Subject (pinned by SHA):** `47453338f4f436b41e468621d7133f007f3f6169` — single commit, diff `caee507d..47453338`
- **Base:** `caee507d6ff911e3756b34e9453bd6cf3ca3e5f6` (`git rev-parse 47453338^`)
- **Branch at review time:** `fix/prompt-audit-c-agents` (tip was `47453338` for every probe; all `git show`/`git grep` reads below use the SHA, not `HEAD`)
- **Reviewer:** cold-reviewer (Claude Opus), diff-only, round 1 (open hunting — no enumerated domain, so this round cannot end the loop by itself)
- **Memory:** consulted (`memory: local` present)
- **Graph:** `mise run graphify-health` rc=3, `stale` (built at `9f5bd67a`) — fell back to source per `graphify-first.md`
- **Independence:** an untracked `codex-review-lens-prompt-audit-C-2026-09-28.md` exists beside this report; it was NOT read.
- **Status:** COMPLETE

## Findings

| # | Severity | Claim | Location | Evidence |
|---|---|---|---|---|
| 1 | MEDIUM | The commit message's verification claim "Every target phrase greps 0 across .claude/agents + .codex/agents" is true only for TRACKED files. The spec's own §5 command (`grep -rlF`) still hits 5 of the 7 phrases in 4 gitignored Codex-app exports that codex loads by name on this host — so the diff's stated objective ("agents stop acting on claims that are false today") is unmet for the codex-side copies: `graphify-operator.toml` still says "read line 8" (the C1 defect), and `adversarial-critic`/`staleness-auditor`/`claude-code-expert.toml` still say "All 50", "masks digits", "2026-08-03 run", "174 pages". The committed lane report in this same diff records those non-zero counts; the "15 hits" control arm cannot discriminate because `codex-lane-mirror` appears in no ignored export. | commit message of `47453338` ("Every target phrase greps 0 …"); `docs/specs/prompt-audit-C-apply.md` §5; residue at `.codex/agents/graphify-operator.toml:13` (gitignored, machine-local) | `grep -rlF 'read line 8 of' .codex/agents` → `.codex/agents/graphify-operator.toml`; same phrase `rg -lF` → rc=1 (0 hits — `rg` respects `.gitignore`, which is the discriminating arm); `git check-ignore -v` → `.gitignore:78:.codex/agents/*`; `.gitignore:70-80` names these files "Codex-app export output, regenerated wholesale"; per-phrase filesystem hits: All 50 ×3, read line 8 ×1, 2026-08-03 run ×2, 174 pages ×1, masks digits ×3; control `grep -rlF codex-lane-mirror … \| wc -l` = 15 = `git grep` count. Remedy (re-export or delete the stale exports) is outside the spec's §2 file list → ticket. |
| 2 | LOW | The C3 rewrite replaces a false count ("All 50") with a false universal: "Every fnox secret is in every shell by design". `CLAUDE_CODE_OAUTH_TOKEN` is the deliberate `env = "exec"` carve-out, so at least one fnox secret is NOT in the shell. Same line in 9 files. | `.claude/agents/adversarial-critic.md:147`; `staleness-auditor.md:120`; `claude-code-expert.md:291`; `codex-sol-adversarial-critic.md:266`; `codex-sol-staleness-auditor.md:240`; `codex-sol-claude-code-expert.md:271` (+astra `:268`, `:242`, `:273`) | `.claude/rules/secrets-out-of-the-shell-env.md:3-7` ("with ONE deliberate carve-out: `CLAUDE_CODE_OAUTH_TOKEN` is `env = "exec"`"); `doctor.toml` `env_true` parse = 56 names, `CLAUDE_CODE_OAUTH_TOKEN` absent; live presence-only probe `[ -n "$VAR" ]`: `CLAUDE_CODE_OAUTH_TOKEN` ABSENT while `AWS_REGION`, `AGE_PRIVATE_KEY` (both `env_true`) SET. Safety direction is conservative (overclaiming presence only makes the agent more careful), hence LOW. |
| 3 | LOW | An n=1 anecdote became an unsupported frequency rule. Base: "The one false alarm of that run was a claim read before the caller's edit landed". New: that is "the **usual** source of a false, urgent-sounding finding" — no evidence for "usual". The auditor pair's "A race … outranks a reasoning error" now stands with its only evidence (the same anecdote) deleted. | `.claude/agents/adversarial-critic.md:92`; `codex-sol-adversarial-critic.md:208` (+astra `:210`); `staleness-auditor.md:69`; `codex-sol-staleness-auditor.md:188` (+astra `:190`) | `git diff caee507d 47453338 -- .claude/agents/adversarial-critic.md` hunk `@@ -73,25 +73,23 @@`. Wording copied from the audit's proposed diff (`docs/research/kb/reports/agents/prompt-audit-C-agents-2026-09-24.md`, "C15 (adversarial-critic)" `@@ -92,3 +91,2 @@`), which cites no frequency evidence. |
| 4 | LOW | The C9b "Evidence:" citation does not carry the clauses it is cited for. The cited spawn-reconciliation report contains none of "weakened test", "dismissed red lint", "attempted `--no-verify`"; its only reference to the incident points at an UNTRACKED user auto-memory. The base text called that file "Lane history", not evidence. The one tracked record is `codex-call-audit-2026-09-23.md:149`, which itself labels the two-writer detail "INHERITED from memory … not re-derived". | `.claude/agents/codex-sol-implementer.md:28` (+`codex-astra-implementer.md:30`) | `grep -ci` on `docs/research/kb/reports/agents/codex-sol-implementer-spawn-reconciliation-2026-09-16.md`: `no-verify` 0, `too long` 0, `myself` 0 (control: `lint` 9, `haiku` 1); its `:3` header points to `feedback_haiku_lane_wrapper_abandons_codex_and_self_implements`; `docs/research/kb/reports/agents/codex-call-audit-2026-09-23.md:149`. |
| 5 | LOW (Q-SCOPE: sibling → ticket) | The C15 incident-story sweep is incomplete: `codex-sol-advisor.md` keeps two stories of exactly the class removed from five siblings ("An agent in a prior run *finished the work*, never delivered, and became unreachable"; "A prior advisor lane in the knowledge-base transition went idle without reporting"). The diff touched this file (C4) but not these lines. The miss originates in the audit, whose "Checked and clean" list gives `codex-sol-advisor` no other findings. | `.claude/agents/codex-sol-advisor.md:48-50`, `:64-65` (+astra `:50-52`, `:66-67`) | `git grep -n 'finished the work' 47453338 -- .claude/agents` → only the two advisor files; audit § "Checked and clean". |
| 6 | INFO | The commit message lists `codex-agent-validate` among its gates, but that gate globs `codex-sdlc-*.toml` only, so it never read any of the six TOMLs this diff changed. Direct validation closes the gap: all six are schema-valid. | `python/src/dotfiles_setup/codex_agent_validate.py:28` (`_AGENT_GLOB = "codex-sdlc-*.toml"`) | `mise run codex-agent-validate` → "6 SDLC agents valid"; direct `jsonschema` validation of the six changed TOMLs against `schemas/codex-agent.json` → 0 errors each; control `description = 123` → 1 error (the validator discriminates; note `model_reasoning_effort = "bogus"` → 0 errors, so the schema does not constrain effort — `codex_agent_parity` does). |
| 7 | INFO | The C1 template `- <N> nodes · <N> edges · <N> communities` does not match the real line exactly: `- 29969 nodes · 45857 edges · 1781 communities (1484 shown, 297 thin omitted)`. The fix direction is right (counts moved from line 8 to line 9), but which community count the delta uses (1781 vs 1484) is unspecified. | `.claude/agents/graphify-operator.md:23-25` | `graphify-out/GRAPH_REPORT.md:8-9`; no programmatic consumer (`git grep 'nodes ·' 47453338 -- .claude/workflows .claude/skills python/src` → 0). |
| 8 | INFO | The sol AND astra TOML descriptions each call themselves "**the** standing <role> lane", while `.claude/token-routing.md:28` says of the two families "**Neither is a default**". "Standing" is meant as codex-vs-Claude, so it is consistent with `:3-8`; the definite article on two agents is the only tension, and the md descriptions ("Standing … lane on codex gpt-X") avoid it. | `.codex/agents/codex-sol-adversarial-critic.toml:12` and the other five changed TOML `description` lines | `.claude/token-routing.md:3-8`, `:27-29`. |
| 9 | INFO | The committed lane report's verification links are absolute `/Users/rmanaloto/…/.agent/logs/prompt-audit-c/*.log` paths into a gitignored tree: dead on every other clone. It is a verbatim record (do not normalize, `agent-artifact-conventions.md` rule 8), so the remedy, if any, is promoting the logs, not editing the report. The spec likewise cites the gitignored `task_plan.md`. | `docs/research/kb/reports/agents/codex-sol-implementer-prompt-audit-C-2026-09-28.md` § Verification; `docs/specs/prompt-audit-C-apply.md:4` | `.agent/` is gitignored per `agent-artifact-conventions.md` § "Local, gitignored". |

## Claims verified TRUE (control-armed)

- **C2 harness facts.** Default Bash timeout 120 s (`$CC/env-vars.md:185`, `$CC/tools-reference.md:158`), max 600 s (`$CC/env-vars.md:187`), a timed-out command is "moved to the background" (`$CC/agent-sdk__typescript.md:3423`). Neither `.claude/settings.json` `env` (9 keys enumerated — the control that the probe reads the block) nor `~/.claude/settings.json` sets `BASH_DEFAULT_TIMEOUT_MS`/`BASH_MAX_TIMEOUT_MS`. The slice sleeps ≤540 s, inside the new `600000` ms timeout. The other five sol wrappers already carried `600000`.
- **C4 flag facts at the installed codex.** `mise exec -- codex --version` → `codex-cli 0.158.0`. `codex exec --help`: `--full-auto` 0, `--full-context` 0, `--sandbox` 1 (control), `-p, --profile <CONFIG_PROFILE_V2>` present. `codex exec --full-auto --help` → `error: unexpected argument '--full-auto' found`, rc=2; control `codex exec --sandbox read-only --help` rc=0. The operator's now version-unbound restatement holds at 0.158.0.
- **C6.** "`[redacted]` … value-based redaction … a 1-char redacted value once masked every `1`" matches user memory `feedback_mise_run_masks_digits` (two 1-char telemetry values; the digit `1`).
- **C11.** `ls $CC/*.md | wc -l` = 196 (control: `$CC/hooks.md` resolves) — dropping "174" was right; remaining "174" hits are dated historical records (`claude-code-expert.md:21`, ledger rows dated 2026-08-05).
- **C14.** `RUSTUP_INIT_SKIP_EXISTENCE_CHECKS=yes` is exported in the `mise install` RUN: `.devcontainer/Dockerfile:341` (rationale `:324`). **C13** item 10: the only repo `HK_PKL_BACKEND` hit is a comment (`.devcontainer/mise-system.toml:377`).
- **C5 routing.** "Standing … lane; <X> is the explicit Claude/Opus alternative" matches `.claude/token-routing.md:3-8`. Description deltas +13..+36 chars (dockerfile-reviewer +185), all ≤ 320; `dotfiles-setup doctor --verbose` shows no listing-total finding (its only `listing-budget` DRIFT is a pre-existing third-party plugin description).
- **C10.** "the caller applies them" matches practice: ledger rows were folded by the caller in `70e61522` (#568) and `d6fc62bd` (#585); `claude-code-expert` has `disallowedTools: Edit`.
- **C7e.** pwf-scribe's new "Write the files first … return the paths you wrote" matches its body (findings/progress + a `task_plan` delta).
- **Scope.** The diff's 31 files are exactly the spec §2 list (17 hand-authored `.md` + 3 sol TOMLs) + 9 regenerated astra files + the spec + the lane report.
- **Commit-message grep claims** replayed with `git grep` at `47453338`: all seven phrases → 0 files; control 15. (See finding 1 for the filesystem arm.)

## Gates re-run (this review, tree at `47453338`, clean except the two untracked reports)

| Gate | rc | Note |
|---|---|---|
| `mise run codex-lane-mirror -- --check` | 0 | "12 generated file(s) match their sol source" |
| `uv run --project python dotfiles-setup codex-agent-parity` | 0 | 12 lanes paired, sentinel, xhigh, no-substitute prohibition |
| `mise run lint-docs` | 0 | agnix "No issues found" |
| `mise run lint` | 0 | file-captured rc |
| `uv run --project python dotfiles-setup verify run` | 0 | 167 passed, 0 failed, 4 skipped (non-`mise` invocation, so digits unmasked) |
| `pytest` subset (`test_codex_agent_parity`, `test_codex_agent_validate`, `test_codex_lane_mirror`, `test_doctor`, `test_hook_guard`, `test_skills_mirror` — every test file naming `.claude/agents`/`.codex/agents`) | 0 | 471 passed. Full suite NOT re-run (commit claims 4022; UNVERIFIED by this review). |
| `mise run codex-agent-validate` | 0 | covers `codex-sdlc-*` only — see finding 6 |
| strict `per_path_tokens` + `per_path_lines` replay over `suites.toml` at `47453338` | 0 fails | 1,355 tokens (7 on agent paths) + 11 lines; the scan is its own control arm |

## Q-FRESH / Q-SCOPE / Q-CLAIM

### Q-FRESH — decision→action pairs re-validated against fresh inputs?

The diff is prompt prose; the decision→action pairs it touches are instructions to agents:

| Pair | Re-validated fresh? | Where |
|---|---|---|
| graphify-operator: snapshot counts → report delta after each task | YES — "re-read that line" after every task | `graphify-operator.md:23-31` |
| implementer: slice → "still running / signal 1-3" | YES (unchanged) — `$LOG.rc` re-read every slice | `codex-sol-implementer.md:192-205` |
| ledger row → answer | YES, newly — "re-probe it when the answer matters and the installed version differs" | `claude-code-expert.md:160-163` |
| critic/auditor top finding → report | YES (kept) — "Re-read every artifact … right before you write them up" | `adversarial-critic.md:89-92`, `staleness-auditor.md:63-69` |
| **author's verification → commit-message claim** | **NO** — the "greps 0" decision was evaluated against a tracked/gitignore-respecting view, not the filesystem view codex loads | finding 1 |

### Q-SCOPE

| # | Scope |
|---|---|
| 1 | Claim in scope (commit message / PR body — correct it at squash time); remedy (re-export or delete the stale gitignored Codex-app exports) is OUT of the spec's §2 list → **ticket** |
| 2, 3, 4 | In scope — hunks this diff wrote (C3, C15, C9b) |
| 5 | Sibling — same class, file outside the C15 slice; the audit missed it → **ticket** (or a one-hunk follow-up) |
| 6 | Sibling — `codex_agent_validate` coverage gap predates this diff → optional ticket |
| 7, 8, 9 | In scope, INFO only |

### Q-CLAIM — every clause this diff adds or changes, with its enforcing/grounding line

| Clause | Grounding / enforcing line | Verdict |
|---|---|---|
| sol/astra md descriptions: "Standing <role> lane on codex gpt-X; <Claude agent> is the explicit Claude/Opus alternative" | `.claude/token-routing.md:3-8` | holds |
| "… and holds the ledger" (ccx) | `claude-code-expert.md:158` | holds |
| TOML descriptions: "the standing <role> lane" | `token-routing.md:3-8` vs `:28` | holds; article ambiguity → finding 8 |
| dockerfile-reviewer description (conventions list, "Read-only", "file:line") | body `:18-28`; `disallowedTools: Edit, Write, NotebookEdit`; new "What you return" | holds; "Use for a change to any image build input" is wider than the checklist (no enforcing line; judgement) |
| "read the `- <N> nodes · …` line under `## Summary`" | `GRAPH_REPORT.md:9` | holds with suffix → finding 7 |
| "moved to the background when it reaches its timeout (default 120 s, maximum 600 s)" | `$CC/env-vars.md:185,187`; `$CC/agent-sdk__typescript.md:3423` | holds |
| "`timeout` … `600000` (without it the 120 s default backgrounds the slice)" | same | holds |
| "The failure this prevents (measured 2026-09-16) … Evidence: the spawn-reconciliation report" | cited file does not carry the clauses | **finding 4** |
| "Every fnox secret is in every shell by design" | contradicted by `secrets-out-of-the-shell-env.md:3-7` + live probe | **finding 2** |
| "`[redacted]` … value-based redaction … once masked every `1`" | memory `feedback_mise_run_masks_digits` | holds |
| "`-p` is `--profile` … `--full-context` / `--full-auto` do not exist" | `codex exec --help` @0.158.0 | holds |
| operator: "`--full-auto` does not exist (`error: unexpected argument …`)" | live rc=2 probe | holds |
| "An agent that dies having written 4 of 9 / 7 of 12 … leaves 4 / 7" | illustrative | holds |
| "a finished critique/report that is never delivered is lost" | tautological | holds |
| "the usual source of a false, urgent-sounding finding" | none | **finding 3** |
| "A race … outranks a reasoning error …" | none left after the anecdote's deletion | **finding 3** |
| "Persisting only to the notepad does not count" | `agent-report-persistence.md` rule 1 | holds |
| ledger: "You do not edit this file … the caller applies them" | `disallowedTools: Edit` (partial: `Write` remains); practice #568/#585 | holds as prose |
| ccx: "you have no `Edit` tool" | `tools: Bash, Read, Grep, Glob, Write` | holds |
| premise-verifier header: "the only edits are … and the closing word cap replaced" | upstream plugin not in local cache | UNVERIFIED vs upstream; consistent with base header + this diff |
| claude-advisor / premise-verifier / scribes: "Only what the caller needs" / "Keep it compact" / "short summary" | instructions | no factual clause |
| dockerfile-reviewer item 7 "exported in the `mise install` RUN" | `.devcontainer/Dockerfile:341` | holds |
| dockerfile-reviewer item 10 "no `HK_PKL_BACKEND` override" | repo: comment only at `mise-system.toml:377` | holds (repo scope) |
| commit: "Every target phrase greps 0 across .claude/agents + .codex/agents" | tracked only; filesystem arm fails | **finding 1** |
| commit: "Gates: … codex-agent-validate — all rc=0" | rc=0 but covers none of the changed TOMLs | **finding 6** |
| commit: "pytest (4022), verify (167/0)" | verify re-derived 167/0/4; pytest subset 471 only | verify holds; pytest total UNVERIFIED |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline `$CC` Claude Code docs (`sources/agent-harness-docs/docs/claude-code`) used to verify C2.
