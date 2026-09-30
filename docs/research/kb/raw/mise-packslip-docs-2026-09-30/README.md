# Offline mirror — mise + packslip docs (2026-09-30)

Agent-optimized offline docs for the "mise agent features / packslip / skills" research (Ray 2026-09-30:
"this statement is wrong: 'mise has no feature built for agents'").

| part | source | how |
|---|---|---|
| `mise/llms.txt` | https://mise.jdx.dev/llms.txt (HTTP 200, 61,034 B; `llms-full.txt` is HTTP 404 upstream) | curl |
| `mise/docs-source/` | jdx/mise `docs/` at tag v2026.9.18 (latest release; 418 .md files) — the complete markdown source | git sparse clone |
| `mise/firecrawl-*.md` | 12 named pages (packslip resources/verification/backend, packslip + skills + mcp CLI, MCP guide) | `mise exec -- firecrawl scrape --format markdown --only-main-content` (firecrawl-cli 1.25.1) |
| `packslip/firecrawl-docs*.md` | 9 pages of https://packslip.dev/docs | firecrawl scrape (as above) |
| `packslip/repo-v1.4.0/` | jdx/packslip at tag v1.4.0 (latest): top-level *.md + docs/ | git clone |

Gaps: https://github.com/jdx/packslip via firecrawl — rate-limited (≈10-20 req/min on this key; 372/1000 credits
left this cycle); the repo's own markdown was mirrored from git instead. A full firecrawl crawl of mise.jdx.dev
(416 mapped pages) would exceed the remaining credits, so the docs source tree is the complete copy and firecrawl
covers the named pages.
