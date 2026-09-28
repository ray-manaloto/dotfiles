---
name: codex-team-research
description: Research a Codex subagent team's roles, model and effort choices, tool access, and handoffs using the five-source research gate plus current OpenAI documentation. Use before proposing or revising a Codex team DAG; do not use for routine single-agent code edits.
---

# Codex team research

Produce a reviewable team recommendation, not a running team configuration. A
passing search receipt proves provider coverage; it does not approve roles or
prove that cited advice is current. Keep source research separate from the
delivery writer's checkout, evidence index, and native goal.

## Recover the decision boundary

Read the current request, prior approved team/merge decisions, and the target
project's `AGENTS.md`. Identify the sole writer, branch/worktree ownership,
required review lanes, and any unapproved DAG or merge amendment. If a Codex
chat was compacted, use its durable checkpoint and bounded native history to
recover direct user corrections; a summary alone is not acceptance evidence.

## Research every required route

1. Apply the installed OpenAI Docs skill first for the exact Codex subagent,
   model-selection, and reasoning-effort question. Search and open current
   official OpenAI documentation; use its model-selection reference only if
   needed. Cite the fetched official pages, not search snippets or a bundled
   model snapshot.
2. Use the project's native `research-fanout` under scoped fnox for **Exa,
   Context7, Last30Days, Firecrawl developer index and web search, and GitHub
   issues/discussions/releases**. The native `codex_research` profile supplies
   Exa and Firecrawl credentials. Do not infer missing credentials from the
   inherited shell, print their values, or copy them into reports.
3. Always require `--strict-five` for a team recommendation. When the global
   Codex research hook supplies a turn ID and output directory, use those as
   `--request-id` and `--out`. Otherwise create a unique request ID and output
   directory outside the repository. Supply an explicit JSON Last30Days plan
   with nonempty `subqueries`. Run the exact scoped form below, using a trusted
   dotfiles checkout that contains the canonical task:

   ```text
   fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C <dotfiles-checkout> run research-fanout -- <query> --repo <owner/repo> --strict-five --request-id <turn-id> --last30days-plan <plan.json> --out <output-dir>
   ```

   Keep stdout and the direct exit code. A failed arm is a blocker for a
   five-provider claim. A retry gets its own recorded outcome; never erase the
   failed route. Verify the manifest's per-source status and raw-file SHA-256.
4. Run targeted GitHub **repository code** search separately when the decision
   depends on an implementation detail. The fan-out GitHub arms cover issues,
   discussions, and releases; an `empty_verified` result does not establish
   how the code works. Use `gh search code` or `gh api` and inspect the exact
   source/ref. For Codex configuration, compare the current official docs with
   the matching `openai/codex` source.
5. Read the best primary hits from every route. Treat Last30Days and general
   web results as discovery and sentiment, not as the authority for a Codex
   model or config contract. Recheck load-bearing claims against OpenAI docs,
   official source, or merged upstream changes; mark gaps and contradictions.

## Recommend the smallest useful team

For each proposed role, state its input, output, model and supported effort,
allowed tools, write scope, exact owner, escalation rule, and whether it can
run in parallel. Start from the current official model guidance; use stronger
reasoning for ambiguous architecture, conflict resolution, security, and cold
review, and cheaper models for bounded extraction or receipt checks only when
their output can be verified. Do not infer served model identity from a
requested setting. Require one isolated worktree/branch per writer and keep
coupled source changes under the approved sole writer. Draw a DAG that shows
handoffs, gates, and the merge boundary; label it proposed until approved.

Give smaller-model agents a packet with exact base SHA, source pointers,
owned paths, ordered commands, expected receipt schema, positive/negative
controls, and stop conditions. Use independent reviewers and QA only where
they can test a completed exact head without writing over the author.

## Report what actually ran

Include a compact source/route table with each named provider, app/plugin/skill
or CLI actually invoked, direct outcome, receipt path, and any failed route.
Distinguish an installed skill read from a callable MCP tool, and a fan-out
provider call from a direct plugin invocation. Link primary evidence beside
each recommendation. Name untested model availability, agent-tool access,
hosted-CI results, and unapproved team activation as open rather than done.
