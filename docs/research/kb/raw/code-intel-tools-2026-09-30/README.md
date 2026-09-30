# Offline mirror — code-intelligence tools links (2026-09-30)

Caller-supplied links, scraped with `mise exec -- firecrawl scrape <url> --format markdown --only-main-content -o link-N.md` (firecrawl-cli 1.25.0 via mise; the bare `firecrawl` on this shell PATH resolves a stale 1.24.6 install dir).

| # | url | result | bytes |
|---|---|---|---|
| 1 | https://www.reddit.com/r/LLMDevs/comments/1wp1szf/i_benchmarked_repowise_codegraph_serena_graphify/ | rc=1 | 0 bytes |
| 2 | https://x.com/somi_ai/status/2098217156785893857 | rc=0 | 2059 bytes |
| 3 | https://wavect.io/blog/ripwire-ai-repo-context-review-2026/ | rc=0 | 21871 bytes |
| 4 | https://github.com/DeusData/codebase-memory-mcp | rc=0 | 144624 bytes |
| 5 | https://www.google.com/search?q=%22codebase-memory-mcp%22+vs+%22graphify%22&tbs=qdr%3Am | rc=0 | 25841 bytes |

Gaps: link 1 (reddit) — firecrawl refuses the site ("we do not support this site"); old.reddit also refused; the reddit JSON API returned HTTP 403. The post is only reachable via the Google SERP snippet (link-5) or a reddit-capable source (last30days).
