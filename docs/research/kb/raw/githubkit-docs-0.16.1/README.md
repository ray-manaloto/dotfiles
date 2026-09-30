# githubkit docs — offline mirror at v0.16.1 (2026-09-30)

- **Package:** githubkit **0.16.1** — the latest on PyPI (`https://pypi.org/pypi/githubkit/json` → `info.version = 0.16.1`,
  uploaded 2026-08-14; newest five uploads 0.15.3, 0.15.4, 0.15.5, 0.16.0, 0.16.1; a bogus package name → HTTP 404, so
  the probe discriminates). GitHub `releases/latest` = `v0.16.1`, published 2026-08-14T07:45:42Z.
- **Rendered site:** https://yanyongyu.github.io/githubkit/ — URL list from its `sitemap.xml` (18 URLs). The site has
  no `llms.txt` (404; a bogus page on the same host also 404s, the site root 200s).
- **Site = v0.16.1?** The site is built from `master`, which is 11 commits ahead of `v0.16.1`. No commit touches
  `docs/` since the tag (`gh api 'repos/yanyongyu/githubkit/commits?path=docs&since=2026-08-14T07:45:42Z'` → 0;
  control: the same query from 2026-01-01 returns 5 commits, newest 2026-07-29). So the rendered pages describe 0.16.1.
- **Date fetched:** 2026-09-30.
- **Two copies, one a control for the other:**
  - `site/` — the rendered pages, fetched with
    `firecrawl scrape <url> -f markdown --only-main-content -o site/<path>.md` (firecrawl CLI **1.25.0**, via
    `mise exec --`). File name = the URL path after `/githubkit/` with `/` → `_`.
  - `source/` — the upstream markdown sources at the tag, fetched with
    `gh api -H 'Accept: application/vnd.github.raw' 'repos/yanyongyu/githubkit/contents/docs/<path>?ref=v0.16.1'`
    (paths from `git/trees/v0.16.1?recursive=1`). These keep the admonitions and tabs the renderer flattens.
- **Status column:** the firecrawl CLI exit code (0 = fetched; it does not expose the origin HTTP code). Attempts > 1
  were firecrawl's own `Rate limit exceeded` (12 req/min on this plan), not origin failures.
- Scanned for GitHub token shapes (`ghp_`, `github_pat_`) after fetching: 0 hits.

Precedent: `docs/research/kb/raw/mise-dotfiles-2026-09-29/INDEX.md`.

## Rendered site (`site/`)

| URL | file | status | bytes | method | attempts |
|---|---|---|---|---|---|
| https://yanyongyu.github.io/githubkit/ | site/index.md | rc=0 | 3591 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/contributing/ | site/contributing.md | rc=0 | 2662 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/installation/ | site/installation.md | rc=0 | 5278 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/quickstart/ | site/quickstart.md | rc=0 | 1978 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/quickstart/calling-api-with-pat/ | site/quickstart_calling-api-with-pat.md | rc=0 | 2176 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/quickstart/connecting-to-github-enterprise/ | site/quickstart_connecting-to-github-enterprise.md | rc=0 | 2831 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/quickstart/github-app/ | site/quickstart_github-app.md | rc=0 | 5560 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/ | site/quickstart_oauth-device-flow.md | rc=0 | 6671 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/ | site/quickstart_oauth-web-flow.md | rc=0 | 7406 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/usage/auto-retry/ | site/usage_auto-retry.md | rc=0 | 3007 | firecrawl scrape | 1 |
| https://yanyongyu.github.io/githubkit/usage/error-handling/ | site/usage_error-handling.md | rc=0 | 3334 | firecrawl scrape | 3 |
| https://yanyongyu.github.io/githubkit/usage/graphql/ | site/usage_graphql.md | rc=0 | 4764 | firecrawl scrape | 2 |
| https://yanyongyu.github.io/githubkit/usage/rest-api/ | site/usage_rest-api.md | rc=0 | 14387 | firecrawl scrape | 2 |
| https://yanyongyu.github.io/githubkit/usage/unit-test/ | site/usage_unit-test.md | rc=0 | 5588 | firecrawl scrape | 2 |
| https://yanyongyu.github.io/githubkit/usage/webhooks/ | site/usage_webhooks.md | rc=0 | 3906 | firecrawl scrape | 2 |
| https://yanyongyu.github.io/githubkit/usage/getting-started/authentication/ | site/usage_getting-started_authentication.md | rc=0 | 16520 | firecrawl scrape | 2 |
| https://yanyongyu.github.io/githubkit/usage/getting-started/configuration/ | site/usage_getting-started_configuration.md | rc=0 | 13327 | firecrawl scrape | 2 |
| https://yanyongyu.github.io/githubkit/usage/getting-started/reusing-client/ | site/usage_getting-started_reusing-client.md | rc=0 | 2525 | firecrawl scrape | 2 |

## Upstream sources at `v0.16.1` (`source/`)

| path | bytes |
|---|---|
| `docs/contributing.md` | 2144 |
| `docs/index.md` | 3877 |
| `docs/installation.md` | 3337 |
| `docs/quickstart/calling-api-with-pat.md` | 1576 |
| `docs/quickstart/connecting-to-github-enterprise.md` | 2113 |
| `docs/quickstart/github-app.md` | 5129 |
| `docs/quickstart/index.md` | 1790 |
| `docs/quickstart/oauth-device-flow.md` | 6842 |
| `docs/quickstart/oauth-web-flow.md` | 7604 |
| `docs/usage/auto-retry.md` | 2511 |
| `docs/usage/error-handling.md` | 2757 |
| `docs/usage/getting-started/authentication.md` | 13819 |
| `docs/usage/getting-started/configuration.md` | 11427 |
| `docs/usage/getting-started/reusing-client.md` | 2010 |
| `docs/usage/graphql.md` | 4118 |
| `docs/usage/rest-api.md` | 13627 |
| `docs/usage/unit-test.md` | 5817 |
| `docs/usage/webhooks.md` | 3507 |
