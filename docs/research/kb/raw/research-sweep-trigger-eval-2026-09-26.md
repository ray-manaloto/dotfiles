# research-sweep trigger eval — 2026-09-26

Harness: scratch project with the real skill folder under `.claude/skills/` (skill-creator run_eval.py registers candidates as `.claude/commands/`, which headless init lists as slash_commands only — its first run scored 0/5 by construction). Model claude-opus-5-5, 1 run/query, stop at first Skill tool_use or 3 non-message tools.

```
PASS True True True ['SendUserMessage', 'Skill(research-sweep)'] mise keeps printing 'WARN unknown field ... settings.not_a_r
PASS True True True ['SendUserMessage', 'Skill(research-sweep)'] did uv ever ship a way to keep dependency groups installed a
PASS True True True ['SendUserMessage', 'Skill(research-sweep)'] before I write my own wrapper: does renovate now support mis
PASS True True True ['SendUserMessage', 'Skill(research-sweep)'] what are people saying about the new hk 2.0 release in the l
PASS True True True ['SendUserMessage', 'Skill(research-sweep)'] how do other projects isolate docker buildx cache mounts bet
PASS False False True ['SendUserMessage', 'Bash', 'Bash', 'Bash'] fix the failing test in tests/test_session_state.py, it's as
PASS False False True ['SendUserMessage', 'ToolSearch', 'mcp__claude_ai_Context7__resolve-library-id', 'mcp__claude_ai_Context7__query-docs'] fetch the context7 docs for the pytest monkeypatch fixture s
PASS False False True ['SendUserMessage', 'mcp__claude_ai_Firecrawl__firecrawl_scrape', 'Bash', 'Write'] scrape https://mise.jdx.dev/configuration.html and save it a
PASS False False True ['SendUserMessage', 'Bash', 'Bash', 'Bash'] open a github issue on ray-manaloto/dotfiles describing the 
PASS False False True ['SendUserMessage', 'Skill(agentsview-finding-history)', 'Agent', 'SendUserMessage', 'Bash'] search my past claude sessions for why we pinned hk to 1.x
PASS True True True ['Skill(research-sweep)'] use the research-sweep skill to check whether jdx/mise has r
passed 11 / 11
rc=0
```

## Eval set
```json
[
 {
  "query": "mise keeps printing 'WARN unknown field ... settings.not_a_real_setting' from some pytest temp dir on every command. is there an upstream fix or setting for this? check their issues, PRs, discussions and the latest release notes",
  "should_trigger": true
 },
 {
  "query": "did uv ever ship a way to keep dependency groups installed across `uv sync`? I think there was an issue about --inexact but not sure if it landed in a release",
  "should_trigger": true
 },
 {
  "query": "before I write my own wrapper: does renovate now support mise.lock natively? look at their changelog, issues and what people are saying",
  "should_trigger": true
 },
 {
  "query": "what are people saying about the new hk 2.0 release in the last month, and are there known regressions reported on github?",
  "should_trigger": true
 },
 {
  "query": "how do other projects isolate docker buildx cache mounts between CI jobs? want evidence from a few sources, not just one blog post",
  "should_trigger": true
 },
 {
  "query": "fix the failing test in tests/test_session_state.py, it's asserting on the wrong PR state enum",
  "should_trigger": false
 },
 {
  "query": "fetch the context7 docs for the pytest monkeypatch fixture setenv api",
  "should_trigger": false
 },
 {
  "query": "scrape https://mise.jdx.dev/configuration.html and save it as markdown",
  "should_trigger": false
 },
 {
  "query": "open a github issue on ray-manaloto/dotfiles describing the mise tracked-configs pollution with the evidence from findings.md",
  "should_trigger": false
 },
 {
  "query": "search my past claude sessions for why we pinned hk to 1.x",
  "should_trigger": false
 },
 {
  "query": "use the research-sweep skill to check whether jdx/mise has released the tool purgatory back-off fix",
  "should_trigger": true,
  "control": true
 }
]```
