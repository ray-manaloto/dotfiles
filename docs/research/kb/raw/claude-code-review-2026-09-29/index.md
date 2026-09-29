# Claude Code review docs offline mirror (2026-09-29)

Base: https://code.claude.com/docs/en/ . Method: `firecrawl scrape --format markdown` (FC, includes site nav chrome) unless noted. All HTTP 200 / rc=0.

| URL | File | Status | Bytes | Method |
|---|---|---|---|---|
| /ultrareview | ultrareview.md | ok | 26884 | FC |
| /ultrareview.md | ultrareview.raw.md | 200 | 18889 | curl (clean source; used for KB diff) |
| /code-review | code-review.md | ok | 45043 | FC |
| /code-review.md | code-review.raw.md | 200 | 33212 | curl (clean; used for KB diff) |
| / (index) | index.md | ok | 21952 | FC |
| /docs/llms.txt | llms-full-index.txt | 200 | 50458 | curl (/docs/en/llms.txt is 404) |
| /claude-code-on-the-web | claude-code-on-the-web.md | ok | 50951 | FC |
| /web-quickstart | web-quickstart.md | ok | 33833 | FC |
| /costs | costs.md | ok | 54154 | FC |
| /errors | errors.md | ok | 513775 | FC (large; ultrareview error anchors) |
| /github-actions | github-actions.md | ok | 40054 | FC |
| /github-enterprise-server | github-enterprise-server.md | ok | 30291 | FC |
| /routines | routines.md | ok | 44887 | FC |
| gh release v2.1.285 body | release-v2.1.285.json | rc=0 | 21439 | gh release view --json body |

Failures: none (no 429s). Not fetched (one-hop, lower relevance): admin-setup, slack, remote-control, gitlab-ci-cd, zero-data-retention, env-vars, settings.

> Coordinator note (2026-09-29b): `routines.md` was removed from this mirror — its official curl example carries an
> 18-char placeholder token that trips gitleaks/betterleaks `curl-auth-header`, and the page is peripheral to the
> review research (cloud routines). It remains online and in the KB corpus (`agent-harness-docs/docs/claude-code/`).
