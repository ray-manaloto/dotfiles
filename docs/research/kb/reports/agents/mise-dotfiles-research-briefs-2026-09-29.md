# mise native dotfiles research — briefs (verbatim), 2026-09-29b

Requested by Ray (session `5545fa41`, AskUserQuestion answer): research mise's native dotfiles support to replace
chezmoi, bring the Mac's user-global `~/.config/mise` (config + scripts) into this repo, and plan it. Required:
`/research-sweep`; firecrawl the given URLs for offline viewing, following links; GitHub code-search examples with the
query criteria recorded; enhance our skills for that GitHub search pattern; summary of all links + which
agents/models/effort researched them; a Fable agent synthesizes the plan.

User-provided links: https://jdx.dev/posts/ , https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/ ,
https://mise.jdx.dev/ , https://mise.jdx.dev/dotfiles.html , https://mise.jdx.dev/bootstrap.html ,
GitHub code search `(path:**/mise.toml OR path:**/config.toml) "[dotfiles]"` and the same plus `".config/mise"`.

Step-0 local corpora (coordinator): `docs/research/mintlify-cache/jdx/mise/llms*.txt` has 0 hits for
`dotfiles.html`/`[dotfiles]` — the cache predates the feature. knowledge-base has `sources/mise`.

## Lane W — `research-sweep-run` workflow

`Workflow({name: "research-sweep-run", args: {question: <Q>, repo: "jdx/mise", reportPath:
"<abs>/docs/research/kb/reports/agents/mise-native-dotfiles-replacing-chezmoi-2026-09-29.md", advisor: false}})`
with Q = "How does mise's native dotfiles support ([dotfiles] config section, `mise dotfiles` commands, `mise
bootstrap`) work as of the latest mise release, what does it cover and not cover compared with chezmoi (templating,
per-OS/per-host differences, secrets, run-once scripts, file modes, symlink vs copy, drift detection), and how would a
user-global ~/.config/mise config plus scripts be managed from a git dotfiles repo with it?"

## Lane F — firecrawl offline mirror (general-purpose, sonnet)

See the prompt of the `Firecrawl offline mirror` agent below (identical text).

## Lane G — GitHub code-search examples (general-purpose, sonnet)

See the prompt of the `GitHub dotfiles examples` agent below (identical text).

## Lane S — Fable synthesis (claude-fable-5-1), launched after W, F, G

Prompt recorded at launch time in this file's `## Lane S prompt` section.

## Lane provenance (measured from `message.model` in each agent transcript, 2026-09-29b)

| Lane | Agent type | Model (measured) | Effort | Links covered | Output |
|---|---|---|---|---|---|
| W research-sweep-run: Plan+fanout | workflow node | claude-sonnet-5-5 | medium (workflow script) | fan-out: github-issues/discussions/releases, exa, context7, firecrawl-developer, last30days | `.agent/kb/raw/research-fanout/mise-dotfiles-{bootstrap,chezmoi}/` |
| W Triage / Read (×3) | Explore | claude-haiku-4-5 | default | mise.jdx.dev/dotfiles.html, jdx.dev dotfiles post, jdx/mise#13410, docs/history.md, jonpulsifer ADR-0011, cli/bootstrap/dotfiles/add.md | claims (58) |
| W Source dive | general-purpose | claude-sonnet-5-5 | (workflow script) | jdx/mise @ v2026.9.17 source | in report |
| W Synthesize | workflow node | claude-opus-5-5 | high (workflow script) | all of the above | `mise-native-dotfiles-replacing-chezmoi-2026-09-29.md` |
| W Verify / critic / reconcile | workflow nodes | claude-sonnet-5-5 | (workflow script) | checked 5 load-bearing claims, 0 refuted | same report |
| F firecrawl mirror | general-purpose | claude-sonnet-5-5 | harness default (not settable per Agent call) | https://jdx.dev/posts/ (36 pages incl. 2026-09-07 dotfiles post), https://mise.jdx.dev/ (414 incl. dotfiles.html, bootstrap.html, llms.txt), 12 one-hop links | `docs/research/kb/raw/mise-dotfiles-2026-09-29/` (463 files, 4.3 MB), `mise-dotfiles-firecrawl-mirror-2026-09-29.md` |
| G GitHub code search | general-purpose | claude-sonnet-5-5 | harness default (not settable per Agent call) | the two user github.com/search URLs (REST-split; 281 + 71 hits, 306 real `[dotfiles]` configs) + independent searches | `mise-dotfiles-github-examples-2026-09-29.md` |
| S synthesis → plan | general-purpose | claude-fable-5-1 (measured) | harness default (not settable per Agent call) | reads W, F, G outputs | `docs/specs/mise-native-dotfiles-plan.md` |

Firecrawl credits: 1,049 → 568 (plan limit 2 concurrent / ~34 req/min; key = fnox `FIRECRAWL_API_KEY`, verified by hash).

## Lane S prompt

Launched 2026-09-29b as `general-purpose`, `model: "fable"`, after W, F and G completed. Verbatim text is the
"Fable: mise dotfiles plan" Agent call in session `5545fa41` (transcript under
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/5545fa41-d28d-447c-98b6-1f0effb90ff8/subagents/`).
Summary: synthesize W+F+G into `docs/specs/mise-native-dotfiles-plan.md` — exec summary, link summary with
lane/model/effort, chezmoi→mise feature map, target layout + exact `[dotfiles]` TOML, gated migration phases +
chezmoi retirement tickets, AskUserQuestion-ready risks, and the GitHub-code-search skill ticket. Plan only.

## Lane O — Omarchy (general-purpose, sonnet), added 2026-09-29b on Ray's request

Ray: "the research should have mentioned omarchy and how it uses mise for dotfiles/bootstrap; use firecrawl to also
add those links for offline research … as we will eventually migrate this Mac's and the devcontainer images and
devcontainers to use mise dotfiles support and to track its history." Verbatim prompt: the "Omarchy mise dotfiles
research" Agent call in session `5545fa41`. Output: `mise-dotfiles-omarchy-2026-09-29.md` + mirror `omarchy/`.
Follow-up: the Fable planner (claude-fable-5-1) amends `docs/specs/mise-native-dotfiles-plan.md` with an Omarchy
section, history tracking, and devcontainer image + running-devcontainer scope.

## Plugins / skills / tools used for the research (Ray asked for this summary)

| Plugin / skill / tool | Used by | For |
|---|---|---|
| `research-sweep` skill → `research-sweep-run` workflow (Workflow tool) | lanes W, W2, the /ultrareview sweep | fan-out → triage → read → Opus synthesis → refute/critic → reconcile |
| `mise run research-fanout` (repo task; sources github-issues, github-discussions, github-releases, exa, context7, firecrawl-developer, firecrawl-search, last30days) | W, W2, X | no-model fetching of candidate URLs |
| firecrawl plugin (skills `firecrawl`, `firecrawl-scrape`, `firecrawl-crawl`, `firecrawl-map`) + `firecrawl` CLI 1.24.6 | F, O, X, review-docs mirror | offline mirrors (sitemap + per-URL `scrape --format markdown`) |
| `gh api` (REST `/search/code`, `/search/issues`, GraphQL discussions, contents, releases) | G, O, X, W readers | GitHub code/issue/PR/discussion search and thread capture |
| context7 (`ctx7`) / exa (plugins, via research-fanout) | W, W2 | docs lookup, web search |
| `last30days` skill (via research-fanout) | W, W2, X | community sentiment |
| KB offline corpus `agent-harness-docs/docs/claude-code/` | review-docs mirror (diff), coordinator | step-00 harness docs |
| Agent types: `general-purpose`, `Explore`, `cold-reviewer`; models haiku-4-5, sonnet-5-5, opus-5-5, fable-5-1 | all lanes | see Lane provenance table above |
