# Research Doc Sources: Preference Chain

When an agent or skill needs to fetch library/framework/tool documentation
during research, it MUST walk this preference chain top-to-bottom and use
the first option that returns the answer. Lower steps cost more tokens
(per-query or per-conversation) — never skip a step that would have
worked.

## Always (Ray, 2026-09-30 — items 2-4 are machine-enforced only inside the `research-sweep-run` workflow; in-lane and item 1 rely on this rule)

1. **Never guess.** Before building anything, research-sweep native tools and features first — mise,
   Claude Code and codex docs **and their issues**. Before diagnosing, search OUR OWN record too: this repo's issues
   (open and closed), `docs/specs/` decisions and `task_plan.md` RULING lines — recorded is not retrieved.
2. **Always GitHub code search** (`gh api -X GET search/code`), with a must-hit and a fresh known-absent control.
3. **Always the dependency repos' issues/PRs/discussions/releases** — pass `--repo`; `--list-sources`
   reporting `needs --repo` means usable, not absent.
4. **Always an offline firecrawl mirror of every link you are given**:
   `mise exec -- firecrawl scrape <url> --format markdown --only-main-content` into
   `docs/research/kb/raw/<report-slug>/links/`. A link that will not fetch is a named gap.

## The chain

00. **For AGENT-HARNESS behaviour, grep the knowledge-base's offline sources
    FIRST.** `~/dev/github/ray-manaloto/knowledge-base/sources/` holds the
    offline source corpus, including
    `agent-harness-docs/docs/{claude-code,codex,cursor,opencode,pi}` — the
    **vendor's own docs**, on disk, greppable, zero round-trips.

    ⚠️ **An unanswered question whose answer is already on this disk is pure
    loss** — a session once shipped a PreToolUse gate reporting two harness
    facts as "unproven" while both sat in `$CC/`. Why this is step 00:
    `docs/rules-evidence/research-doc-sources.md`.

    Step 0 below is a *different* corpus — mintlify docs for third-party
    libraries. Neither substitutes for the other.

0. **Grep the local cache first.** Every repo in
   `docs/research/mintlify-catalog.md` has both `llms.txt` and
   `llms-full.txt` pre-fetched under
   `docs/research/mintlify-cache/<owner>/<repo>/`. Zero latency,
   zero round-trips, greppable across the whole cache with
   `grep -rHi <topic> docs/research/mintlify-cache/`. Before running
   any `curl` against a docs domain, check whether the repo is in the
   catalog — if yes, the cache is the authoritative source and `curl`
   is only needed for per-page `.md` fetches or cache refresh.

   **Common trap:** do NOT guess a project's docs domain
   (`containers.dev/llms.txt` → 404; the devcontainer docs are on
   mintlify). Grep the cache or the catalog for the right URL first.

1. **`curl <site>/llms.txt`** — AI-optimized plain-text index, one entry
   per page. Cheapest possible *remote* lookup. Works for every repo in
   `docs/research/mintlify-catalog.md` and for many non-mintlify sites
   that publish an llms.txt (check the target site). Use `grep` on
   the output to pick the page(s) you want. Use this when step 0 is a
   cache miss or when the topic needs fresh content.

2. **`curl <site>/<path>.md`** — for mintlify-hosted sites, appending
   `.md` to any visible page URL returns clean markdown (no HTML
   chrome, no JS). Use this once step 1 has told you which page you
   want. This is the primary per-page fetch for mintlify content.

3. **`ctx7`** — for libraries whose docs live outside mintlify, or where
   `llms.txt`/`.md` doesn't cover what you need. It is a **direct
   doc-fetcher**; call it straight, in two steps:

   ```bash
   ctx7 library <name> [query]        # resolve a name -> Context7 library ID
   ctx7 docs <libraryId> <query>      # fetch the docs
   ```

   Do not build on the deprecated `skills` subcommands — and do not
   treat their absence from `--help` as proof they are gone (they still
   run). `.claude/skills/context7-cli/SKILL.md` is the setup reference.

4. **Raw HTML fetch** (`curl <url>` or `npx @teng-lin/agent-fetch <url>`) —
   **last resort only.** Pays the full HTML-parse cost in agent
   context. Use `defuddle` where available to clean HTML before
   parsing.

## Never `mcp2cli` a per-repo mintlify MCP URL

Probe history: `docs/rules-evidence/research-doc-sources.md`.

The ban is specific to per-repo mintlify subpath URLs. `mcp2cli` stays
in active use for real MCP servers (`@github`, `@docker`, or a
customer-domain MCP like `docs.anthropic.com/mcp`) — see
`.claude/skills/mcp2cli/SKILL.md`. Four probes, incl. the central-MCP
scope limit: `docs/rules-evidence/research-doc-sources.md`.

## MCP: two lanes. Which lane you are in decides the answer

A registration's context cost is small; never refuse one on context grounds.
Method and per-server table: `docs/rules-evidence/research-doc-sources.md`.

**Lane 1 — a third-party plugin or skill requires MCP: ALLOWED, no
justification needed.** Enabling a plugin that bundles an MCP server, or a tool
whose features only work over MCP, is a normal thing to do. You are buying the
plugin's value and paying its schema cost knowingly. Do not fight it, do not
wrap it, do not refuse a useful plugin over this.

**Lane 2 — anything THIS project builds, calls, or looks up: AVOID MCP.**
For our own doc lookups, tool calls and automation, exhaust these first, in
order:

1. the cache / `llms.txt` / `.md` steps above, or the tool's own CLI;
2. a plain HTTP **API** (`curl` + `gh api` + a documented endpoint);
3. **`mcp2cli`** — process-spawn, pays zero per-conversation schema cost;
4. native registration — **last resort**, and say in the commit body why 1–3
   could not do it.

**If you are unsure which lane you are in, you are in lane 2.** Lane 1 is
specifically "an external plugin/skill I did not write requires it"; everything
else is our own code, and our own code uses an API.

## See also

- `.claude/skills/mcp2cli/SKILL.md` — process-spawn MCP invocation.
- `.claude/skills/mintlify/SKILL.md` — mintlify URL surface.
- `.claude/rules/research-repo-enumeration.md` — sibling rule for
  recording which repos a research artifact touched.
- `.claude/rules/use-tool-builtins.md` — parent principle (prefer tool
  built-ins over homegrown logic); this rule is an instance of that
  principle for doc fetching.
- `feedback_no_mcp_registration.md` — auto-memory rule with rationale.
