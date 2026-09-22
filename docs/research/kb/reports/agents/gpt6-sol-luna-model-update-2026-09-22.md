# GPT-6 Sol/Luna model update — research + inventory (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. HTML entities restored. Coordinator note: the stray
> `mise.lock` aws-cli `blake3` checksum line the delegate reported was reverted with
> `git checkout -- mise.lock` (same recurring mise write as `stash@{0}`).

The announcement confirms only two new model IDs, `gpt-6-sol` and `gpt-6-luna`. There is no `gpt-6-terra`, and `gpt-6-astra` is still the current Astra. The repo's codex pin (0.154.0) can't see either new model, so the pin has to move to 0.156.0 before the model strings are switched.

**Side effect you need to handle:** tracked `mise.lock` in dotfiles is now modified, one added line (a `blake3` checksum under `[tools.aws-cli."platforms.macos-arm64"]`, file time 15:50:22). It is almost certainly mine. I ran `mise run graphify-health` to follow graphify-first; the run hung for about 3 minutes downloading agentsview artifacts and I stopped it (rc 144). I did not revert the line in case another session wrote it. If it's mine, `git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles checkout -- mise.lock` puts it back. So graphify was unavailable and I fell back to `git grep`, which is also the right tool for literal model strings. I wrote nothing else. This lane is read-only, so `findings.md`/`progress.md` were not updated and you need to save this report yourself.

## 1. Primary sources

**Announcement**
- Plain `curl -sL` of the URL got HTTP 403 (a 9.8 KB block page).
- The reader route `https://r.jina.ai/<url>` got HTTP 200 with 11 KB of markdown. That is the one that worked; firecrawl wasn't needed.

What it says:
- **API IDs:** "In the OpenAI API, they are available as `gpt-6-sol` and `gpt-6-luna`."
- **Availability:** ChatGPT Work and Codex "starting today" for Plus, Pro, Business, Enterprise and Edu; Luna also for Free and Go in the desktop app; rolling out gradually through the day.
- **Astra:** "GPT-6 Astra continues to be our best model across the board." It is not replaced.
- **Terra:** not mentioned anywhere. No `gpt-6-terra` exists.
- **Deprecations:** none stated. Prices are compared to "GPT-5.6 promotional pricing" (Sol $2/$10, Luna $0.10/$0.50 per million tokens).
- **Effort levels in the benchmarks:** low, medium, high, xhigh and max.

**openai/codex source** (control: `gh api repos/openai/codex` returned the repo, so a missing slug below means missing, not "couldn't reach it")
- The `rust-v0.156.0` tag (published 2026-09-22T19:51Z) has `codex-rs/models-manager/models.json` with: gpt-6-astra, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, gpt-daybreak-blue-latest, gpt-daybreak-red-latest, gpt-5.5, gpt-5.4, codex-auto-review. **No gpt-6-sol or gpt-6-luna.**
- `main` has them, added in commit `49e95cc73` / PR #47332, "Add GPT-6 Sol and Luna to the model catalog" (merged 2026-09-22T18:17Z). It also adds upgrade pointers:
  - `gpt-5.6-sol` → `gpt-6-sol`
  - **`gpt-5.6-terra` → `gpt-6-sol`** (Terra's successor is Sol)
  - `gpt-5.6-luna` → `gpt-6-luna`
- `rust-v0.157.0-alpha.9` does not have them either.
- The 0.156.0 release notes mention no Sol or Luna (the only relevant hits are catalog plumbing, e.g. #46508 and #46917). npm `latest` is 0.156.0.

**Installed CLIs, using `codex debug models` (`--bundled` is the offline catalog; bare refreshes it from the server)**

| Binary | Offline catalog | Server catalog |
|---|---|---|
| `~/.local/bin/codex` 0.156.0 | no gpt-6-sol or luna (matches the tag) | **gpt-6-astra, gpt-6-sol, gpt-6-luna**, gpt-reserve (hidden), gpt-5.6-sol/terra/luna, gpt-5.5, codex-auto-review |
| mise 0.154.0 (`.../npm-openai-codex/0.154.0/bin/codex`) | same as 0.156.0 plus gpt-5.4-mini and gpt-5.2 | gpt-6-astra, gpt-reserve, gpt-5.6-sol/terra/luna, gpt-5.5, codex-auto-review, **no gpt-6-sol or luna** |

- Same command, same account, minutes apart, different lists: the server filters by client version. That is the control that shows the difference is real.
- `~/.codex/models_cache.json` (fetched 20:51Z, `client_version: "0.155.0"`, probably the Desktop app) does include gpt-6-sol and luna. That suggests the cutoff is somewhere between 0.154 and 0.155. **Unverified:** I only have one 0.155 data point.
- **`PATH` resolves to 0.154.0.** Both bare `codex --version` and `mise exec -- codex --version` report `codex-cli 0.154.0`, and `which -a` lists mise's install first.
- Server entries:
  - `gpt-6-sol`: efforts low, medium, high, xhigh, max, ultra; default medium; context 272000; `supported_in_api: true`.
  - `gpt-6-luna`: same but **no `ultra`**.
  - `gpt-6-astra`: the server default effort is now medium (the offline copy says low).
  - `gpt-5.5` carries a retirement date of 2026-10-14. No gpt-5.6 model is marked retired yet.
- All current lanes use `xhigh`, which is valid for Sol, Luna and Astra.

## 2. Inventory

**Dotfiles** (tracked files, excluding `docs/research`, `docs/receipts` and locks: 101 hits).

The codex version pin comes first, because the model switch depends on it:

| file:line | now | should become | kind |
|---|---|---|---|
| `.config/mise/conf.d/shared.toml:44` | `"npm:@openai/codex" = { version = "0.154.0", … }` | `0.156.0` | authored; relock with `mise run lock-shared -- "npm:@openai/codex"` |
| `.config/mise/mise.lock:531+` | 0.154.0 entry | regenerated | generated |
| `.devcontainer/mise-system.lock:5209+` | 0.154.0 entry | regenerated | generated, via `mise run lock-image` |
| `.claude/skills/codex-schema/SKILL.md:43` and `.agents/skills/codex-schema/SKILL.md:43` | "schema matches 0.154.0" | 0.156.0 after `mise run codex-schema-generate` | the `.agents` copy is a mirror |
| `docs/specs/phase9-lane-dag.md:21` | "9.1 bump codex 0.154.0 to 0.155.1" | target 0.156.0 | authored plan |

Model strings:

| file:line | now | should become | kind |
|---|---|---|---|
| `python/src/dotfiles_setup/codex_lane_mirror.py:32` | `SOL_MODEL = "gpt-5.6-sol"` | `"gpt-6-sol"` | authored; drives the mirror |
| `codex_lane_mirror.py:33` | `ASTRA_MODEL = "gpt-6-astra"` | unchanged | — |
| `python/src/dotfiles_setup/codex_agent_parity.py:123` | `("codex-sol-", "gpt-5.6-sol")` | `"gpt-6-sol"` | authored gate map |
| `.claude/agents/codex-sol-{implementer:4,169; operator:4,67,83; advisor:4,14,103,122}.md` and the other three sol roles (adversarial-critic, claude-code-expert, staleness-auditor; 5 hits each) | `--model gpt-5.6-sol` plus prose | `gpt-6-sol` | **authored**, the source of truth |
| `.codex/agents/codex-sol-*.toml` (6 files; e.g. `advisor.toml:12,18`, `implementer.toml:11`) | prose and description only | `gpt-6-sol` | authored |
| `.claude/agents/codex-astra-*.md` and `.codex/agents/codex-astra-*.toml` | gpt-6-astra | nothing, but they must be re-rendered after the sol edit | **generated** by `mise run codex-lane-mirror` |
| `.claude/token-routing.md:17` | `gpt-5.6-sol` | `gpt-6-sol` | authored |
| `.claude/CLAUDE.md:90` | "GPT-5.6 Sol" | "GPT-6 Sol", but only if the plugin default changes (see below) | authored |
| `docs/agent-team.md:422` | copy of the plugin's `${MODEL:-gpt-5.6-sol}` | follow the plugin | authored doc |
| `docs/specs/phase9-lane-dag.md:86` | codex-sol-implementer on gpt-5.6-sol | gpt-6-sol | authored plan |
| `tests/test_codex_lane_mirror.py:29,31,36,53,63,88` and `tests/test_codex_agent_parity.py:61,302` | fixtures use gpt-5.6-sol | gpt-6-sol | tests; they'll break when the constants change |
| `tests/test_codex_lane.py:586-588`, `docs/specs/codex-sdlc-*.md:45-50`, `schemas/codex-*.json` (`gpt-5.1-codex-max` key), `.agents/.../evals.json:114` | historical or generic | leave | — |

- **Two stale statements.** `codex-sol-advisor.md:122` and `codex-sol-operator.md:83` say `--model` "resolves to `gpt-5.6-sol` by inheritance" from `~/.codex/config.toml`. That file says `gpt-6-astra` (line 2).
- **Existing gap (not new with this change):** no `.codex/agents/codex-sol-*.toml` sets `model =`. I checked with `[[:space:]]`; an earlier `\s` probe was blind and returned nothing even for `name =`, which I caught with a control grep. The `model_reasoning_effort` lines in the same files matched. Dotfiles' `.codex/config.toml` has no `default_subagent_model` either. So when codex spawns these files itself, a "sol" lane runs on **gpt-6-astra**, inherited from user config. The `.md` wrappers pin `--model` explicitly; the TOML lanes don't.
- There are no Luna or Terra lanes in either repo.

**knowledge-base** (243 hits; the authored ones)

| file:line | now | should become | kind |
|---|---|---|---|
| `mise.toml:239` | `"npm:@openai/codex" = "0.154.0"` | `0.156.0` | authored pin |
| `.codex/config.toml:22` | `default_subagent_model = "gpt-5.6-sol"` | `gpt-6-sol` | authored |
| `.claude/agents/kb-codex-advisor.md:11,96` and `.codex/agents/kb-codex-advisor.toml:8,59` | gpt-5.6-sol | gpt-6-sol | authored pair |
| `kb-codex-astra-{advisor,reviewer}` `.md` and `.toml` fallback prose (e.g. `advisor.toml:204`, `reviewer.toml:290,318`, `advisor.md:44,187`) | "fall back to … gpt-5.6-sol" | gpt-6-sol | authored |
| `kb-codex-astra-*` `model = "gpt-6-astra"` (`advisor.toml:38`, `reviewer.toml:14`) | gpt-6-astra | unchanged | — |
| `.claude/skills/kb-review/SKILL.md:160` and `references/lanes.md:199`, plus the `.agents` copies | gpt-5.6-sol in the Sol column and control row | gpt-6-sol | `.agents` is a mirror |
| `python/src/kb_setup/codex_run.py:94,672` and `lane_recording.py:114` | examples in docstrings and help text | gpt-6-sol | authored |
| `tests/test_codex_review_evidence.py` and `test_codex_lane.py:767,777` | fixture strings | leave, or update alongside | tests |
| `python/src/kb_setup/graphify_native_extract.py:261` and `tests/test_graphify_native_extract.py:867-895` | cite *graphify's* openai-cli default | leave; that's graphify's value, not ours | — |

**User and plugin files** (reported only, not edited)
- `~/.codex/config.toml`: `model = "gpt-6-astra"` (line 2) and `model_reasoning_effort = "xhigh"` (line 3). Still current.
- `~/.local/bin/codex` is 0.156.0 but sits after mise on `PATH`.
- User mise config line 12 excludes codex from `minimum_release_age`, so 0.156.0 (published today) won't be held back.
- `~/.claude/CLAUDE.md` and `~/CLAUDE.md` don't exist. `~/.codex/AGENTS.md` has no matches.
- **fable-orchestrator 1.21.0** (`~/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0`, last commit `78f9cb5`, 2026-08-13):
  - Hardcodes `gpt-5.6-sol` at `scripts/run-lane.sh:91,112`, `scripts/doctor.sh:57,71,82,84` and `agents/codex-implementer.md:30`.
  - The effort setting is the `fable-orchestrator: codex effort = xhigh` line in `.claude/CLAUDE.md`. It has no `ultra` level.
  - Model override: `run-lane.sh` arg 4 (`MODEL=${4:-}`); `codex-implementer.md:143` says "pass it as the fourth argument".
  - **Upstream can't be checked:** `gh api repos/mar3co/fable-orchestrator` returns 404 and `git ls-remote` says "Repository not found". It's a vendored plugin, so don't edit it. Either pass the model as argument 4 at dispatch or wait for a plugin update.

## 3. Verification plan

Order: bump the codex pin first, then change the models.

1. **Pin and locks:** `mise run lock-shared -- "npm:@openai/codex"`, then `mise run lock-image`, then `mise run pin-parity`. Arms:
   - `codex --version` and `mise exec -- codex --version` both print 0.156.0.
   - `mise exec -- codex debug models | jq -r '.models[].slug'` lists gpt-6-sol and gpt-6-luna.
   - Control: the 0.154.0 binary, same command, lists neither (already observed).
2. **Schema:** `mise run codex-schema-generate`; the doctor `codex-schema` check reads the 0.156.0 stamp.
3. **Mirror and parity:** edit the sol sources and `SOL_MODEL`/`MODEL_BY_PREFIX`, then:
   - `mise run codex-lane-mirror`, then `mise run codex-lane-mirror -- --check` returns rc 0;
   - `mise run codex-agent-parity` and `mise run codex-agent-validate` return rc 0.
   - Arm the fail side: temporarily put `gpt-5.6-sol` back in one sol `.md` and require parity to fail.
4. **Tests:** `uv run --project python pytest tests/test_codex_lane_mirror.py tests/test_codex_agent_parity.py tests/test_codex_schema.py -x -q`, then the full suite, `mise run lint`, `mise run verify` and `mise run lint-docs` (`.claude/**` changed). Then `mise run rule-sync`, because both repos' `.claude` change. In KB, its own pytest and lint.
5. **Remaining references:** `git grep -n 'gpt-5\.6-sol' -- ':!docs/research' ':!docs/receipts'` in both repos should return only intentional history. Control: the same grep for `gpt-6-astra` must still return hits.
6. **Live model calls (billable, not run; one each):**
   ```bash
   printf 'Reply with exactly: OK\n' | PLANNING_DISABLED=1 mise exec -- codex exec --ephemeral -s read-only \
     --model gpt-6-sol -c model_reasoning_effort='"xhigh"' -o "$OUT" -
   ```
   - Repeat with `--model gpt-6-luna` (xhigh) and `--model gpt-6-astra` as the known-good control.
   - **Negative arms:** `--model gpt-6-terra` must exit non-zero; `gpt-6-luna` with `model_reasoning_effort='"ultra"'` should be rejected (Luna has no ultra).
   - **Version arm:** the 0.154.0 binary with `--model gpt-6-sol`. Whether an old client can still use a model it doesn't list is **unverified**.
   - Confirm the model from the rollout session's `turn_context` model, not the startup banner. The banner shows the resolved config, so an inherited value looks the same as an explicit one. KB's `codex_review_evidence` already parses this.
   - Optionally re-run `/fable-orchestrator:doctor`, which still probes gpt-5.6-sol.

**Unverified:** the exact client-version cutoff; whether 0.154.0 accepts an unlisted `--model gpt-6-sol`; the retirement timeline for gpt-5.6 (none published yet).

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — the `models.json` catalog at `rust-v0.156.0`, `main` and 0.157.0-alpha.9; PR #47332; the 0.156.0 release notes and release list
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — tried for plugin currency; 404 and "Repository not found", so only the local 1.21.0 cache was read
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — inventory (local clone)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — inventory (local clone)
