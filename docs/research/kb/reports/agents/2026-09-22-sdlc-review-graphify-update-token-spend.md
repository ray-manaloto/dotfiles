# codex SDLC team review — graphify-update token spend + fb89c433 (2026-09-22)

Verbatim copy of `.agent/sdlc-runs/graphify-update-token-review-20260921/output.md` (run id `graphify-update-token-review-20260921`, mode review, effort xhigh, 1100s). Settlement: `failed` on spawn RECONCILIATION only — three specialists were observed (python, config, documentation) but the dispatcher placed "No others were spawned." BEFORE the list under `Specialists spawned:`, so the parser claimed zero; the review content itself is complete. Coordinator annotations are marked `[coordinator]`.

---

# SDLC review: Graphify update and skill currency

The automated `mise run graphify-update` path is zero-model-token: it performs AST extraction followed by deterministic file/stamp synchronization. The captured Bash inventory also contains no token-spending command. The broader historical session is non-zero because a separate accidental `graphify label` consumed Gemini quota and the reporting subagent itself consumed agent tokens.

## Python specialist

### Medium — refresh overwrites the reviewed local safety patch

`refresh_skills()` compares and replaces the Claude/Codex vendor surfaces, with backup creation, after a successful rebuild ([graphify_skill.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify_skill.py:253), [graphify.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify.py:665)). The refreshed vendor skill removes the previous `raise SystemExit(1)` after a refused shrink, making its success message reachable after failure ([SKILL.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/graphify/SKILL.md:521)).

This is an accepted design choice in the diff, but it means routine currency can undo a repo-local fail-closed safeguard. The `.bak` preserves recovery, not enforcement.

### Low — idempotency is real, but the test does not prove “no second-run writes”

Production code compares skill bytes, references, and stamps before writing ([graphify_skill.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify_skill.py:228)); a converged second invocation therefore appears write-free.

The test only asserts that the second call returns `()` ([test_graphify_skill.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_graphify_skill.py:511)). A stronger realistic fail arm would patch `Path.write_*`, `shutil.copy*`, and replacement operations to raise during the second call, or assert unchanged mtimes.

### Low — several new doctor failure branches lack fail arms

The matching/drifted stamp and PATH-binary cases have useful positive and negative tests ([test_doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_doctor.py:1141)). Missing package metadata, absent stamps, subprocess timeout/OSError, nonzero `--version`, and malformed version output are implemented but not separately exercised ([doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/doctor.py:1142)).

### Positive implementation evidence

- Skill refresh has no LLM path and no subprocess reach. The test explicitly makes `run` and `Popen` fail if invoked ([test_graphify_skill.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_graphify_skill.py:497)).
- The Agents surface remains byte-identical to its stub; the mutation arm adding it to `MANAGED_PLATFORMS` fails ([test_graphify_skill.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_graphify_skill.py:600)).
- Check mode snapshots all bytes before and after ([test_graphify_skill.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_graphify_skill.py:558)).
- A failed graph rebuild is proven not to refresh skills; successful ordering and refresh failure propagation are also tested ([test_graphify.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_graphify.py:704)).
- Doctor uses public distribution metadata and `graphify --version`, not Graphify’s private Python API ([doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/doctor.py:1142)).
- The CLI exposes `skill-refresh [--check]` through direct Python dispatch ([main.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/main.py:1303)).

### Command-by-command token spend

The source inventory is [lines 21–39](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-av-graphify-update-bash-history.md:21).

| Ordinal | Command class | Token-spending? | Reason |
|---:|---|---|---|
| 22 | `graphify-health`, then `graphify-update` | No | Update is AST-only; no label/dedup path. |
| 28 | Health plus `graphify-query` | No | Deterministic graph traversal. |
| 30 | `graphify-query` | No | Same deterministic query path. |
| 34 | `jq` over `graph.json` | No | Local JSON reads. |
| 46 | Handoff check and progress-note append | No | Documents an earlier run; does not invoke Graphify. |
| 60 | Branch creation, stamp reads, task-definition search | No | Git and local file reads. |
| 62 | PyPI JSON request and source inspection | No | PyPI metadata, not a model endpoint. |
| 64 | Source read | No | No executable Graphify path. |
| 66 | Local Python placement/version probe | No | Metadata and filesystem comparison only. |
| 68 | Packaged-versus-repo diff | No | Byte comparison. |
| 70 | Local placement probe, file read, Git history | No | No model or agent command. |
| 82 | Findings/config/history reads | No | Documentation and configuration inspection. |
| 84 | GitHub PR lookup and local reads | No | GitHub REST, not a model provider. |
| 90 | Wrapper/CLI source reads | No | Inspection only. |
| 94 | CLI, hook, verification, and test-count reads | No | Inspection only. |
| 96 | Skill/source/workflow-document reads | No | Inspection only. |
| 98 | Doctor/workflow/source/listing reads | No | The workflow was read, not executed. |

The mise task explicitly describes AST-only extraction and excludes labeling or agent paths ([mise.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:803)). Its Python path invokes `graphify update`, then deterministic refresh after success ([graphify.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/graphify.py:650)). Graphify itself routes update through code rebuilding without LLM labeling ([cli.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/lib/python3.14/site-packages/graphify/cli.py:2403)).

## Configuration specialist

### Critical — the review reproduced the prohibited label path

A double-quoted search pattern containing backticks caused zsh to launch the user-global `graphify label`. The specialist interrupted it after approximately ten seconds; final rc was 130. Output showed batch 1/20 reaching the silent `claude -p` fallback, which then exited 1 during its SessionEnd hook.

Additional Claude-token spend is unknown: the failure output does not prove whether inference completed before the SessionEnd failure. Filesystem mutation is also not conclusively excluded because no before/after graph hash exists.

This is a new review-execution incident, separate from the historical Gemini incident.

### High — there is no enforced Codex-lane protection today

For Claude, `hook_guard` can return a PreToolUse JSON denial even in bypass-permissions mode ([hook_guard.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:2)). However, it explicitly documents that hook crashes fail open ([hook_guard.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:974)). It is therefore a precise redirect layer, not the hard fail-closed boundary.

The fail-closed Claude layer is `permissions.deny`; its current entries contain no bare-Graphify prohibition ([settings.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:24)). Recommended layering:

1. Add a precise raw-command `hook_guard` rule recognizing bare Graphify in command substitutions and redirecting sanctioned operations to mise tasks.
2. Add a hard permission denial for model-capable bare labeling so a hook failure cannot expose the backend.
3. Give Codex an executor/harness-level denial or allowlist that is actually enforced.

Although [.codex/hooks.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/hooks.json:1) mirrors the Claude wiring, the repository’s own SDLC rule states that Codex lane shell commands are invisible to `hook_guard` and depend only on prompt prohibitions ([codex-sdlc-team.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/codex-sdlc-team.md:66)). The live reproduction confirms that this is the operative reality.

A realistic fail arm should submit nested backtick and `$()` forms through each harness’s public command interface, with `graphify` replaced by a sentinel shim. The command must be denied and the sentinel remain untouched; removing the rule must touch it.

### Positive configuration evidence

- The Graphify tasks are thin, one-line Python callers, preserving zero-bash-logic ([mise.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:790)).
- Pin parity binds the two package declarations, live `EXPECTED_GRAPHIFY_VERSION`, and all three stamps; an unmatched pattern is explicitly a failure ([pin-parity.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/pin-parity.toml:36), [graphify entry](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/pin-parity.toml:46)).
- The lock diff is confined to Graphify’s pin/package metadata and its new Pillow optional dependency—no unrelated package version moved.
- `.gitignore` now ignores only `.graphify_root`, allowing the Claude `.graphify_version` stamp to be tracked like its siblings ([.gitignore](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.gitignore:110)).
- The 23-file commit inventory contains no `.github/` or `.devcontainer/` paths; workflow and image specialists were therefore N/A.

## Documentation specialist

### High — the inventory’s session-wide conclusion is stale and overbroad

The report is marked “IN PROGRESS” and covers only messages through the crawl point ([bash history](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-av-graphify-update-bash-history.md:6), [crawl scope](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-av-graphify-update-bash-history.md:12)). Its claim that no label invocation occurred “today” ([line 43](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-av-graphify-update-bash-history.md:43)) was invalidated by the later child-agent incident.

That incident ran `graphify label`, consumed Gemini free-tier quota, and changed 1,540 of 1,952 labels from hub/filename forms to concepts ([release research](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-graphify-0.9.62-0.9.65-release-research.md:236), [quota evidence](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-graphify-0.9.62-0.9.65-release-research.md:252)).

Correct scope: “Every command inventoried through ordinal 98 was zero-model-token.” It cannot say the complete session was zero-token.

### High — the documented Codex guard surface contradicts observed reality

The `.gitignore` commentary calls `.codex/hooks.json` a Codex-side guard surface, while the SDLC rule says Codex lanes cannot execute those hook rules. The two review-lane reproductions support the blind-spot statement, not the guard-surface claim. This prose needs reconciliation before `.codex/hooks.json` is treated as protection.

### High — inventory gaps could conceal additional spend

The report leaves 15 matching sessions unopened, does not inspect Codex-prefixed sessions, and does not completely verify the workflow source ([Gaps](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-av-graphify-update-bash-history.md:60)). It also explicitly records a token-spending Agent dispatch outside the Bash inventory ([line 41](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-21-av-graphify-update-bash-history.md:41)).

A realistic fail arm is an isolated child-session fixture containing a hidden label or agent invocation; the inventory must surface it. Reverting child-session traversal must fail the assertion.

### Medium — the Agents installation skill attributes the patch to the wrong bundle

[The Agents mirror](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agents/skills/graphify-skill-install/SKILL.md:43) says the removed `raise SystemExit(1)` was in the “Codex bundle.” The research evidence says Codex matched upstream while Claude carried the one-line delta. It should say “Claude bundle.”

The remaining new prose correctly describes Claude+Codex as fully managed, Agents as stamp-only, no label invocation, and `.bak` creation.

### Medium — backup cleanup is a manual residual

A changed vendor skill produces `SKILL.md.bak`, followed by manual inspection/removal instructions ([installation skill](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/graphify-skill-install/SKILL.md:42)). This is transparent but makes mutating hook/CI operation undesirable.

### Review limitation

An exhaustive stale-`0.9.61` prose search and `md_size_budget` verification were not completed after command execution was stopped. No claim of passing either check is made.

The documentation specialist also triggered bare `graphify` without a subcommand through backtick substitution. It printed help only; the surrounding search exited 2. This invocation appears non-model and non-mutating, but it still violated the review constraint.

## Pros and cons: zero-token graph and skill currency

| Shape | Pros | Cons |
|---|---|---|
| Current AST update plus deterministic skill copy | Zero model/API/agent tokens; deterministic; repo-pinned; idempotent implementation; managed Claude/Codex bytes and all stamps stay aligned. | Hub-derived labels are less semantic; refresh can overwrite local vendor patches; changed skills leave `.bak` cleanup. |
| Local labels with `--backend ollama` | No hosted quota or agent-subscription spend; produces conceptual labels; explicit backend avoids ambient-key selection. | Still performs model inference; requires a local service/model; Ollama is serial, making roughly 20 batches slow; output quality and bytes are nondeterministic. |
| Hosted Gemini/OpenAI labels | Best observed semantic improvement: 1,540/1,952 labels changed to concepts. | Non-zero quota/cost, rate limits, retries, and churn. Ambient credentials can select a hosted backend automatically; without keys Graphify can silently escalate to Claude CLI ([llm.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/lib/python3.14/site-packages/graphify/llm.py:3505)). |
| Hook/CI refresh | Check-only mode catches drift promptly and avoids forgotten currency work. | Mutating hooks surprise operators; CI needs bot commits to persist bytes; `.bak` files create residue; any future label-path regression would multiply spend across automated runs. |

Recommendation: keep AST-only rebuild plus deterministic skill/stamp refresh operator-invoked. Add `skill-refresh --check` to hook/CI enforcement, but do not mutate there. Keep labeling separate; when semantic labels are worth the latency, require explicit `--backend ollama`.

The deciding risk is silent backend escalation: a single accidentally reachable bare label command can consume hosted quota or Claude subscription tokens.

## Token-spend verdict

**Automation path: zero; original session overall: non-zero; this review may have incurred indeterminate additional Claude spend from the fresh interrupted label reproduction.**

No repository gates were run. The mandatory graph query was attempted twice but failed before Graphify started because the read-only sandbox prevented mise temporary-file creation (`rc=1`). No report file or checkout file was intentionally written; mutation from the fresh interrupted label attempt is unproven.

## Specialists spawned:

No others were spawned.

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/docs_review`

## [coordinator] Refutation pass (2026-09-22)

- Critical (self-incident: specialist reproduced bare `graphify label`, fell to `claude -p`, rc=130 after ~10s): CONFIRMED as event; graph files unchanged (mtime 18:47 = the first incident), no surviving processes. Second occurrence of one class in a day -> fail-closed `permissions.deny` for `Bash(*graphify label*)` specced in respec round 1; codex-lane coverage filed as an issue.
- Medium (refresh overwrites the hand patch) + docs Medium (wrong bundle): design is a ruling (vendor read-only); the JUSTIFICATION wording is wrong -> respec round 1.
- Low idempotency test, Low doctor fail arms: CONFIRMED -> respec round 1.
- High "inventory conclusion overbroad": PARTIALLY confirmed. The inventory answers the question asked (this session's graphify-update Bash commands = zero-token); token spend in this session came from the orchestration lanes (research/review), which is by design and outside graphify-update. The two accidental label runs are the only unplanned spend. Annotated, not rewritten (records are not normalized).
- High ".gitignore calls .codex/hooks.json a guard surface" vs codex-sdlc-team.md blind spot: CONFIRMED contradiction, PRE-EXISTING (2026-09-14) -> separate issue, out of this PR.
- Settlement reconciliation false-negative on list placement: tooling defect -> separate issue.

## GitHub repos touched

_None._ (reviewed local files and the installed graphifyy package only)
