# Codex flags implementation report — 2026-09-15

This report records implementation of the accepted six-step Codex SDLC flag
delta: strict project configuration, plugin enablement, runtime consultation
verification, typed model output, JSON event capture, and documentation repair.
The build specification is
`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/4b5c48be-fade-4708-aff8-2edec71aac2d/scratchpad/spec-codex-impl.md`.

## Documentation lane opened

The required Graphify orientation ran before source inspection. Both focused
queries returned rc=3 with an explicit `TRUNCATED` result, so neither provided
usable symbol-level orientation. This lane proceeded through the accepted spec
and targeted reads of the named documentation contracts. The documentation
specialist owns only the eight paths assigned by the dispatcher and does not
edit `task_plan.md`, `findings.md`, or `progress.md`.

The repair preserves these evidence boundaries:

- `--strict-config` fails closed on project configuration unknown to the
  installed CLI.
- `--output-schema` makes the model's final report typed but remains
  `SELF_REPORT` evidence.
- `--json` provides a clean event stream and the real `thread.started` parent
  id; descendant rollout records provide consultation and participation proof.
- Static plugin availability never substitutes for a completed descendant
  command that reads an installed plugin `SKILL.md`.

Further implementation and gate results are appended below as the lane settles.

## Licensed dissent — typed relevance wiring stopped

Step 3 asks the dispatcher to extend `SdlcTeamRequest` with a relevance
declaration such as `required_plugin_skills`. That public type is governed by
the committed `schemas/sdlc-team-request.json`; the schema-equality contract in
`tests/test_sdlc_team.py` fails whenever the type and schema diverge. The schema
file is outside this implementation's file allowlist.

The requirements therefore contradict the allowed write surface. This build may
ship the standalone descendant-only consultation verifier and its fixtures, but
must not add or claim typed request integration without also regenerating and
reviewing `schemas/sdlc-team-request.json`. The coordinator stopped that portion
under licensed dissent rather than weakening the schema gate or guessing an
untyped trigger.

## Documentation repair applied

The documentation lane updated the eager rule and both skill copies with the
strict-config, typed-report, clean-JSONL, parent-thread, and plugin-capability
contracts. `research-doc-sources.md` now gives Codex questions an explicit
three-source order: the 125-file official offline corpus, installed CLI help,
then the version-exact generated configuration and agent schemas. It also
records the corpus lag control and keeps `openai-developers` scoped to OpenAI
developer products rather than Codex CLI behavior.

The durable design no longer calls the team unimplemented, prescribes the
invalid array-shaped `mcp_servers` selection, or leaves the roster and
dispatcher shape undecided. The harness mapping narrows the 0.152.1
model/effort finding and records the 0.154.0 loading arms separately. Historical
0.152.1 notes outside the allowlist remain unchanged and are annotated as
version-bound and refuted here and in the permitted plan delta.

Focused verification:

- `mise run skills-mirror -- --check`: rc=0 after rendering the Codex-facing
  copy through the repository generator.
- `mise run lint-docs`: rc=0, `No issues found`.
- stale-phrase search across all eight owned documentation paths: rc=1 with no
  matches, the expected no-match result.

## Runtime contract reconciliation

After the Python surface settled, the skill documentation was aligned to the
implemented names and files: `SdlcTeamReport`, `SpawnedSpecialist`,
`CodexEventSummary`, `parse_codex_events()`, `PluginSkillRequirement`,
`PluginConsultationOutcome`, `verify_plugin_consultation()`, and
`generate_team_report_schema()`. The default run artifacts are `report.json`,
clean stdout `codex.events.jsonl`, diagnostic stderr `codex.log`, and
`settlement.json`. The implemented argv order is:

```text
codex exec --strict-config -c <effort> -C <workdir>
  --output-schema <absolute schemas/sdlc-team-report.json>
  --json -o <report.json> -
```

Final documentation verification after that reconciliation:

- generated skill mirror parity: rc=0.
- `mise run lint-docs`: rc=0, `No issues found`.
- stale runtime-name/path search: rc=1 with no matches, the expected no-match
  result.

## Final lint repair

The full lint gate found a smart-quote normalization failure in the harness
mapping and then exposed that a byte-identical skill copy violates the generated
mirror contract. The mapping now uses ASCII quotes. The `.agents` skill was
rendered from its `.claude` source through `skills_mirror.render()`, which
applies the required Codex-facing path rewrites.

- `mise run skills-mirror -- --check`: rc=0.
- `mise run lint-docs`: rc=0.
- `mise run lint`: rc=0; `fix_smart_quotes` and `skills_mirror_parity` both
  passed.

## Python and configuration implementation

The dispatcher argv is now:

```text
codex exec --strict-config -c 'model_reasoning_effort="<effort>"'
  -C <workdir> --output-schema <absolute report schema>
  --json -o <report.json> -
```

The supervisor writes stdout to `codex.events.jsonl` and stderr to `codex.log`,
parses exactly one `thread.started` id, decodes `report.json` as the closed
`SdlcTeamReport` type, and changes a zero-return-code settlement to failed when
events or the report are malformed. The generated schema requires
`report_markdown`, typed `specialists_spawned` rows, `spawn_failures`, and
`no_others_spawned`; unknown fields are rejected. The report remains
`SELF_REPORT` evidence and is merged with observed ancestry and hook sources.

`verify_plugin_consultation()` walks only descendants of the captured parent
thread. It accepts a required agent only when a completed, zero-exit
`CommandExecution` record contains a parsed read of the installed plugin skill's
`SKILL.md`. Its public fixtures reject absent reads, prose-only claims,
wrong-parent sessions, failed commands, and missing required agents. The new
verification suite pins the public verifier and all five rejection arms without
claiming the blocked request integration.

All six agent TOMLs now enable `openai-developers`, include skill instructions,
and explicitly enable `openai-developers:agents`. Their developer instructions
carry the ordered Codex sources and the OpenAI developer capability boundary.
`codex_agent_validate` enforces the parsed TOML blocks, relevance phrases, and
source order. Its isolated mutation puts invented `plugin_names` at top level;
the public validator returns rc=1 and names the dispatcher file.

## Specialist synthesis

The Python, config, and documentation specialists implemented disjoint owned
surfaces in parallel. Workflow and image specialists then reviewed the final
declarations read-only. Both found no defects. The workflow reviewer confirmed
that no `.github/workflows/**` implementation was needed and ran `pin-actions`
at rc=0. The image reviewer confirmed that no `.devcontainer/**`, Dockerfile,
bake, image-task, or `mise.toml` surface changed, so
`verify-container-latest` was not applicable.

The first image-review spawn failed before an agent existed with
`agent thread limit reached`; the retry after the Python lane released its slot
succeeded. Every spawned specialist reported that it spawned no subagents.

## Coordinator probes and final gates

The installed CLI is Codex 0.154.0. The corrected four-arm project-config probe
returned: strict invalid rc=1 and named the copied project file;
`--ignore-user-config` invalid rc=0 and did not name it; `--ephemeral` invalid
rc=1 and named it; clean strict config rc=0. The first empty-stdin attempt was
nondiscriminating because every arm stopped at `No prompt provided`; it is not
used as evidence.

The offline official Codex corpus contains 125 Markdown files. Searches found
zero files for `--strict-config`, ten for `ephemeral`, four for
`dangerously-bypass`, and zero for an invented control token. This reproduces
the documented lag caveat.

Final file-captured direct results:

- targeted SDLC/receipt/agent tests: rc=0, 48 passed;
- `mise run codex-schema-check`: rc=0;
- `mise run codex-agent-validate`: rc=0, six agents valid;
- `mise run skills-mirror -- --check`: rc=0;
- `mise run lint-docs`: rc=0;
- `mise run lint`: rc=0;
- `uv run --project python pytest tests/ -x -q`: rc=0, 3240 passed,
  11 deselected by the repository's existing test configuration;
- `mise run verify`: rc=0, 156 passed, 0 failed, 4 declared policy skips;
- `mise run pin-actions`: rc=0 from the workflow specialist;
- `git diff --check`: rc=0.

The first full pytest run correctly rejected a standalone skill citation to the
new, still-untracked report schema after 908 passes. The redundant standalone
citation was removed while the operational `--output-schema` contract and
generator name remained documented; `tests/test_doc_refs.py` then passed 18/18
and the complete suite passed. Two attempted temporary-index diagnostics were
discarded: test-created Git fixtures inherited and replaced the temporary
index, making their corpus controls invalid. Both proved the real index hash
unchanged and neither is final gate evidence.

The scope audit found every task-created modification inside the user
allowlist. `docs/research/kb/reports/agents/codex-flag-audit-2026-09-15.md`
remains the same pre-existing untracked file observed at intake. No Git index,
branch, commit, push, or user-global configuration was changed.

## Remaining licensed-dissent boundary

The permitted implementation is complete and all applicable gates are green.
The six-step objective is not fully integrated: the request-level relevance
declaration and automatic invocation of `verify_plugin_consultation()` remain
stopped because the required generated request schema is outside the allowlist.
Consequently, the all-six-agent relevant live consultation smoke is also held;
running it without a typed request trigger would test an unreviewed prompt
convention rather than the requested public interface. The follow-up scope is
recorded in the plan delta.
