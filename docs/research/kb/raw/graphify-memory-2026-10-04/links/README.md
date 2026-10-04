# Mirror index — graphify-memory-2026-10-04

| n | URL | how fetched | status |
|---|---|---|---|
| 1 | https://github.com/mycelium-hq/ai-brain-starter/blob/main/skills/graphify/SKILL.md | firecrawl rc=1 (Insufficient credits) → `curl` raw.githubusercontent.com HTTP 200 (control: bogus path → 404) | **NAMED GAP — not mirrored.** Dropped 2026-10-04 (Ray): betterleaks `generic-password` at line 754 of the third-party example text; no allowlist. Re-fetch from the URL to read it. |
| 2 | https://neoneye.github.io/agent-memory-atlas/systems/graphify/ | firecrawl rc=1 (credits) → `curl` HTTP 200 + `defuddle parse --markdown` rc=0 | 32,823 B |
| 3 | https://deepwiki.com/safishamsi/graphify/2.6-work-memory-and-reflection | firecrawl rc=1 (credits); `curl` HTTP 429 (Vercel Security Checkpoint, also with browser UA); WebFetch 429 → DeepWiki's own API: `mcp2cli --mcp https://mcp.deepwiki.com/mcp read-wiki-contents --repo-name safishamsi/graphify` rc=0 (349,962 B), section 2.6 extracted | 8,901 B |
