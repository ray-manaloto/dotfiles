# Codex exec flag and openai-developers audit — 2026-09-15

Status: complete

## Scope and evidence discipline

This audit covers every option and subcommand printed by the installed
`codex exec --help`, empirically tests whether repository-local
`.codex/config.toml` is loaded, and determines how the installed
`openai-developers` plugin can be required and verified for the six Codex SDLC
agents.

The required Graphify orientation command ran first and returned rc=3 because
the graph was built at `38ed61f2`, one commit behind checkout HEAD `63a76ec0`.
Refreshing it would change paths outside the task's file allowlist. Subsequent
evidence therefore uses targeted source reads and isolated public-interface
probes, and this report labels any conclusion that remains unverified.

## Evidence collected

- The task specification is
  `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/4b5c48be-fade-4708-aff8-2edec71aac2d/scratchpad/spec-codex-flags.md`.
- The checkout began clean at commit
  `63a76ec02c88dc6eb941b154f75ccf30c10e4804` on branch
  `docs/session-2026-09-15-preclear`.
- Three roster specialists were dispatched in parallel: configuration,
  Python/runtime, and documentation. No workflow or image specialist was
  needed because the allowed deliverables do not touch those domains.

Further sections are appended as the live probes and specialist reports settle.

## Project `.codex/config.toml`: loaded and applied for new threads

The CLI help is incomplete here. A fresh temporary Git repository containing
only this invalid project file:

```toml
definitely_unknown_project_probe_key_20260915 = true
```

failed `codex exec --strict-config -C <temp-repo> ...` at `thread/start`, named
the exact `<temp-repo>/.codex/config.toml:1:1` field, and returned Codex rc=1.
An independent invalid `$CODEX_HOME/config.toml` control also returned rc=1 and
named its own unknown field. Neither arm produced a last-message file.

A second fresh-thread probe proved that valid project settings affect tools,
rather than merely being syntax-checked. The copied project file set the fresh
variable `CODEX_PROJECT_CONFIG_SENTINEL_20260915="PROJECT_CONFIG"`; a required
shell call printed `PROJECT_CONFIG`, and Codex returned rc=0. A same-shape dotted
CLI override printed `CLI_CONTROL`, also with rc=0. The event files are under
`/tmp/codex-project-env-audit-20260915.C7ECZV/`.

This conclusion applies to new `codex exec` threads. A specialist's initial
`resume <fake-id>` arm was nondiscriminating: resume did not validate the
current directory's project file because it follows the resumed thread's
configuration path. The new-thread positive and negative arms corrected that
probe.

The repository's current project config is valid and sets
`shell_environment_policy` at `.codex/config.toml:1-12`. Therefore:

- **ADOPT `--strict-config`** for each new SDLC dispatch. Put it immediately
  after `exec`. It proves the project file is read and fails closed on unknown
  fields.
- Pin it with an exact argv test plus a public live/config-fixture contract:
  the valid copy passes and a fresh unknown project key fails with rc=1 and the
  copied path. The mutation arm removes `--strict-config`; the unknown-key run
  then must cease producing the expected strict failure.
- A Codex upgrade can make a formerly accepted field unknown and stop every
  lane. That is the intended fail-closed behavior, but the pinned CLI/schema
  upgrade must update configuration before dispatch resumes.
- `-p/--profile` is a named `$CODEX_HOME/<name>.config.toml` layer. It is useful
  for an explicitly selected user profile; it is not required to obtain
  per-project configuration, because the project file is empirically loaded.

The spec premise that `.claude/rules/codex-sdlc-team.md` itself claims project
config behavior is stale. At current HEAD, that rule mentions only the global
`~/.codex/config.toml` at lines 31-36 and agent TOML at lines 62-71. No current
rule text there claims project `shell_environment_policy` is honored.

## Approval/sandbox bypass is a measured no-op here

Two persisted, otherwise equivalent runs compared the inherited invocation and
`--dangerously-bypass-approvals-and-sandbox`. Both returned rc=0. Their
`turn_context` records were identical:

```json
{"approval_policy":"never","sandbox_policy":{"type":"danger-full-access"}}
```

The flag therefore changes nothing under today's approved user configuration.
It is **REJECTED**: retaining it would mask future configuration drift and could
silently widen permissions if the inherited posture becomes narrower.

## `openai-developers`: real surface and licensed dissent

`codex plugin list` returned rc=0 and reports
`openai-developers@openai-curated-remote` as installed and enabled at version
1.3.0, connector id
`plugin_connector_1p_32dba5a7095c8191adca04ee30276304`.

The installed manifest describes OpenAI APIs, Agents API/SDK, ChatGPT Apps, and
API-key creation (`.codex-plugin/plugin.json:2-4,25-31`). It contributes five
skills (`README.md:10-15`), the `openai-platform` connector
(`.app.json:2-6`), and one MCP server. That MCP server exposes only
`confirm_openai_api_key_local_destination` (`mcp/server.mjs:4-6,148-186`). The
`$agents` skill is for building with the Agents API or Agents SDK
(`skills/agents/SKILL.md:2-3,12-22`). None of these surfaces documents the
Codex CLI, its configuration merge, or subagent runtime.

This is a capability contradiction in the requested mechanism: forcing this
plugin to answer “how to use Codex” would be misleading and would invoke API-key
or application guidance on unrelated repository tasks. The plugin must not be
dismissed; it should be enabled for every SDLC agent and required when a task
actually concerns its OpenAI API/Agents/Apps scope. Codex CLI questions should
use the installed `codex:codex-cli-runtime`/official OpenAI documentation
surface.

The version-exact derived agent schema supports this per-agent configuration:

```toml
[plugins.openai-developers]
enabled = true

[skills]
include_instructions = true

[[skills.config]]
name = "openai-developers:agents"
enabled = true
```

An isolated copy of all six roster files with that block passed
`python -m dotfiles_setup.codex_agent_validate <copy>` at rc=0. Replacing the
block with the invented `plugin_names = ["openai-developers"]` key failed every
file at rc=1. The schema evidence is `schemas/codex-agent.json`: top-level
`additionalProperties` is false at line 6, while `plugins`, `skills`, and
object-shaped `mcp_servers` are defined properties. This avoids the earlier
array-shaped `mcp_servers` defect that silently dropped all agents.

Static enforcement belongs in the existing agent validator: require the plugin
enablement, skills instructions, and a relevance-conditioned developer
instruction in all six parsed TOML files. Its fail arm removes one block and
must return rc=1 naming that agent. Static configuration proves availability;
it does not prove consultation.

Runtime verification should follow the plugin's own eval rule: “Record which
skill files were actually read” (`skills/agents/references/evals.md:3`). Capture
the new Codex parent thread id, walk only its descendant sessions, and require a
tool-call record that reads a `SKILL.md` beneath the installed
`openai-developers/<version>/skills/` path when the dispatch declares that
plugin relevant. A final-message claim or developer-instruction string does not
count. Positive, absent-read, wrong-parent, and prose-only fixtures must prove
the verifier's fail behavior. After implementation, a bounded live smoke should
spawn each of the six named agents on a relevant prompt and produce one
attributable skill-read record per agent.

## Structured final output and JSON events

The current self-report path reads the last Markdown message and applies
`_AGENT_LINE` at `python/src/dotfiles_setup/lane_result.py:92-97`. It accepts a
simple ``- `name` — role`` row but rejects Codex's observed
``- `name` as `/root/path` `` form. `--output-schema` should replace this regex
with a dedicated model-owned final-report schema containing `report_markdown`,
`specialists_spawned[]` (`name`, `task_path`, `role`), `spawn_failures[]`, and
`no_others_spawned`. Do not pass `schemas/lane-result.json` to the model because
that receipt also contains coordinator-owned sources, disagreements, and timing.

The structured response is still SELF_REPORT evidence. A live schema-valid
probe falsely claimed a spawn after the spawn had failed, proving that output
shape cannot establish runtime truth.

`--json` also does not directly solve observation in codex-cli 0.154.0. A
persisted successful child spawn appeared in the parent raw rollout and the
child's `parent_thread_id`, while stdout JSONL contained wait events but no
`spawn_agent` event. JSONL does provide `thread.started`, command events, and
machine-readable messages. It is useful for capturing the correct Codex parent
thread id and general telemetry, after which raw rollout or AgentsView ancestry
must supply the observed roster.

The current supervisor cannot safely consume JSONL: it redirects stderr into
stdout at `python/src/dotfiles_setup/sdlc_team.py:544-550`, and live runs emitted
plain-text OAuth diagnostics on stderr. Adopt `--json` only together with
separate stdout event and stderr diagnostic files. A control fake writes one
valid event to stdout and one plain diagnostic to stderr; reintroducing
`stderr=STDOUT` must make JSON decoding fail.

## Complete `codex exec` option audit

The installed mise-managed binaries report `codex-cli 0.154.0` and
`codex-cli-exec 0.154.0`; all four help commands returned rc=0. A specialist's
earlier bare-path plugin probe recorded 0.151.0 and is excluded from
current-version conclusions. The replacement mise-managed plugin-use probe
persisted `cli_version="0.154.0"`.

There are 27 top-level option entries in the displayed help. The table below
includes all of them; the positional prompt/stdin contract follows separately.

| Option | Verdict | Reason; placement and pin for adopted options |
|---|---|---|
| `-c`, `--config <key=value>` | **ADOPT** (existing) | Keep the single effort override immediately after `--strict-config`: `-c model_reasoning_effort="<effort>"`. `tests/test_sdlc_team.py` should assert exactly one such pair; deleting it or changing its key is the fail arm. Stable repository settings belong in project config rather than more ad hoc overrides. |
| `--enable <FEATURE>` | **REJECT** | Per-run feature toggles create unreviewed drift. Version feature changes in config/schema and test them explicitly. |
| `--disable <FEATURE>` | **REJECT** | Same drift problem as `--enable`; no current feature needs an exception. |
| `--strict-config` | **ADOPT** | Place immediately after `exec`. Exact argv plus fresh-thread valid/unknown project-config arms pin it; removing the flag must make the unknown-field strict failure disappear. The upgrade-breakage risk is intentional fail-closed behavior. |
| `-i`, `--image <FILE>...` | **CONDITIONAL** | Add only if `SdlcTeamRequest` gains typed, validated image inputs and the task needs them. It does not belong in every dispatch. |
| `-m`, `--model <MODEL>` | **CONDITIONAL** | Add only if the typed request becomes the authority for the dispatcher/root model. Current configuration pins effort and lets the configured Codex lane own model selection. |
| `--oss` | **REJECT** | The SDLC team is an OpenAI Codex lane; switching provider violates its runtime contract. |
| `--local-provider <OSS_PROVIDER>` | **REJECT** | Only meaningful with the rejected `--oss` path. |
| `-p`, `--profile <CONFIG_PROFILE_V2>` | **REJECT** for this dispatcher | It layers `$CODEX_HOME/<name>.config.toml`. That is a named user overlay, not the required per-project mechanism; persistent new threads already load and apply project `.codex/config.toml`. |
| `-s`, `--sandbox <SANDBOX_MODE>` | **REJECT** | Re-adding it reverses the measured 2026-09-15 fix, overrides the approved inherited posture, and can remove network access. Its absence is already pinned at `tests/test_sdlc_team.py:119-148`. |
| `--approve-for-me` | **REJECT** | It routes approvals through `workspace-write`, conflicting with the detached lane's inherited `approval_policy="never"` and `danger-full-access` posture. |
| `--dangerously-bypass-approvals-and-sandbox` | **REJECT** | Baseline and flagged persisted `turn_context` were identical (`never`, `danger-full-access`). It is a current no-op with a hazardous future meaning. |
| `--dangerously-bypass-hook-trust` | **REJECT** | Current hooks already execute, as the normal-run SessionEnd hook event proves. Bypassing persisted trust adds no required capability and weakens provenance. |
| `-C`, `--cd <DIR>` | **ADOPT** (existing) | Keep it after the effort override and before output options. The exact argv test must assert that its value is the resolved request workdir; changing/removing it is the fail arm. |
| `--worktree` | **CONDITIONAL** | Use only for a future typed request that deliberately selects Codex-managed isolation and tests artifact, allowlist, and cleanup semantics. The current lane owns the caller's checkout and must not silently relocate. |
| `--add-dir <DIR>` | **CONDITIONAL** | Accept only typed, resolved, allowlisted extra roots. Under the current `danger-full-access` posture it adds no capability and would otherwise obscure scope. |
| `--thread-source <SOURCE>` | **CONDITIONAL** | It may improve provenance, but accepted values and the consumer contract have not been verified. Do not add a decorative classification with no tested reader. |
| `--skip-git-repo-check` | **REJECT** | SDLC work requires a repository. Skipping the precondition is appropriate only for isolated probes. |
| `--ephemeral` | **REJECT** | It removes the rollout evidence needed for model/sandbox/ancestry verification and, empirically, suppresses application of project `shell_environment_policy`. Its absence remains coupled to the absence of `-s`. |
| `--ignore-user-config` | **REJECT** | It discards the approved user posture and, empirically, also suppresses application of the project shell-environment policy despite strict validation still discovering the file. |
| `--ignore-rules` | **REJECT** | It disables user/project execpolicy protections without a task requirement. |
| `--output-schema <FILE>` | **CONDITIONAL** | Live output conformed to a supplied schema, and this can replace the SELF_REPORT regex. Adopt only after adding a dedicated final-report schema, typed decoder, and malformed-output fail-closed tests. It cannot establish observed participation. |
| `--color <COLOR>` | **REJECT** | Redirected output already uses machine-safe automatic behavior; with future JSONL it is irrelevant. |
| `--json` | **CONDITIONAL** | It provides `thread.started` and other typed events but omitted a successful child spawn. Adopt only with split stdout/stderr, event decoding, and ancestry lookup keyed by the emitted parent thread id. |
| `-o`, `--output-last-message <FILE>` | **ADOPT** (existing) | Keep immediately before the terminal `-`; assert it points to the absolute resolved output. Removing or redirecting it makes the receipt input absent and must fail tests. |
| `-h`, `--help` | **REJECT** | Discovery-only, never a dispatch option. |
| `-V`, `--version` | **REJECT** | Discovery-only, never a dispatch option. |

The positional prompt contract is **ADOPT**: keep the literal `-` as the final
argument so the supervisor's prompt file is read from stdin. The existing exact
argv test must fail if it is absent or no longer last.

### Subcommands and their unique options

| Surface | Verdict | Reason |
|---|---|---|
| `resume [SESSION_ID] [PROMPT]` | **REJECT** | SDLC dispatch requires a fresh auditable thread. Resume also proved unsuitable for validating the current directory's project config. |
| `resume --last` | **REJECT** | Selects state nondeterministically. |
| `resume --all` | **REJECT** | Discovery/UI scope, not deterministic dispatch. |
| `fork <SESSION_ID> [PROMPT]` | **REJECT** | Introduces inherited context and lineage the typed request does not model. |
| `review [PROMPT]` | **REJECT** for the team dispatcher | The team's review mode is a routed multi-specialist prompt contract, not Codex's single review subcommand. |
| `review --uncommitted` | **CONDITIONAL** outside this dispatcher | Suitable only for a separate typed single-review entry point. |
| `review --base <BRANCH>` | **CONDITIONAL** outside this dispatcher | Same; require an exact base contract. |
| `review --commit <SHA>` | **CONDITIONAL** outside this dispatcher | Same; require an exact immutable SHA. |
| `review --title <TITLE>` | **CONDITIONAL** outside this dispatcher | Presentation metadata only for that separate review path. |
| `help` | **REJECT** | Discovery-only. |

Shared options printed under `resume`, `fork`, and `review` inherit the verdicts
above. Their help commands each returned rc=0.

## Runtime plugin-use proof on the audited version

The mise-managed 0.154.0 probe explicitly invoked
`openai-developers:agents`, returned Codex rc=0, and completed a command reading
the exact installed
`openai-developers/1.3.0/skills/agents/SKILL.md` before replying
`PLUGIN_USE_OK`. JSONL contained both started and completed command events; the
persisted rollout is
`~/.codex/sessions/2026/09/15/rollout-2026-09-15T20-17-43-01a0a7ca-886d-70d1-92b5-49f0b8e5f416.jsonl`, whose `session_meta`
reports `cli_version="0.154.0"`. The live negative baseline completed without
any plugin-skill read. This proves that runtime consultation is observable; it
does not remove the requirement to bind the verifier to the correct parent and
child threads.

## Documentation corrections outside this lane's allowlist

- `.claude/rules/codex-sdlc-team.md:31-36` discusses global config and does not
  contain the spec-attributed project-config claim.
- `docs/specs/codex-sdlc-subagent-team.md:3` says the team is not implemented;
  lines 78-82 require per-agent `mcp_servers`; lines 188-198 later record that
  this invalidated agents and cannot select tools; lines 272-278 still call
  names, instructions, and plugin assignments undecided. That document is
  internally stale and contradictory.
- `docs/claude-codex-harness-mapping.md:100` should keep the narrower measured
  claim that project `model`/`model_reasoning_effort` are not honored separate
  from the now-proven loading and shell-policy behavior of the project file.

## Verification

- `mise run lint-docs`: rc=0, no issues.
- `uv run --project python pytest tests/ -x -q`: rc=0, 3227 passed and
  11 deselected.
- `mise run verify`: rc=0, 155 passed, 0 failed, and 4 declared human-policy
  skips.
- `mise run lint`: the first two runs returned rc=1 only because Taplo timed
  out fetching `https://starship.rs/config-schema.json`. A direct HTTP control
  returned 200, the exact Taplo invocation then returned rc=0, and the final
  full lint run returned rc=0.
- `mise run codex-schema-check`: rc=0.
- `git diff --check` over the four allowlisted artifacts: rc=0.

## Recommended `sdlc_team.py` argv

The one immediately justified argv is:

```text
codex exec --strict-config -c 'model_reasoning_effort="<effort>"' -C <workdir> -o <output> -
```

`--strict-config` goes immediately after `exec`; the other entries retain their
current order, and `-` remains last. Pin the exact tuple, run the copied valid
project config as the positive arm, and mutate it with a fresh unknown key as
the rc=1 arm. A second environment-sentinel contract must keep both
`--ephemeral` and `--ignore-user-config` absent because either suppresses the
project shell policy. `--output-schema` and `--json` remain staged follow-up
work until their decoder, stream separation, and observed-ancestry contracts
exist.
