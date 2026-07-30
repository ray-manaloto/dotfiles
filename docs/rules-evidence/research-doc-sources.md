# Evidence — `research-doc-sources`

Probe logs and corrections behind `.claude/rules/research-doc-sources.md`.
Extracted from the rule so the eager copy carries the preference chain itself and
this file carries the evidence for why each step is where it is — and why one
step was deleted outright.

## Why `mcp2cli` against per-repo mintlify MCPs is NOT in the chain

An earlier revision listed `mcp2cli https://mintlify.com/<owner>/<repo>/mcp
<tool>` as a fuzzy-search step. **That step does not work** and was removed.

Probe evidence (full log: `docs/research/mintlify-catalog-validation-log.md`):

- **The URLs are GET-only preview descriptors**, auto-generated for every repo
  Mintlify indexes. `curl GET` returns a JSON tool-schema descriptor; **POST** —
  which `mcp2cli` sends to speak MCP protocol — returns `404 Not found`. There is
  no live MCP server behind the descriptor. The descriptor's existence is exactly
  the trap: it *looks* like a live endpoint to a GET-shaped probe.
- **Live mintlify MCP servers exist only at the customer's own documentation
  domain** (e.g. `docs.anthropic.com/mcp`, `resend.com/docs/mcp`,
  `docs.perplexity.ai/mcp`). None of the 16 repos then in
  `docs/research/mintlify-catalog.md` host one anywhere — verified against their
  own domains (`chezmoi.io/mcp`, `starship.rs/mcp`, `mise.jdx.dev/mcp`), all of
  which return plain nginx 405/404, not MCP protocol.
- **Mintlify's central MCP** at `https://mintlify.com/docs/mcp` works, but is
  scope-limited to Mintlify's *own* platform docs (how to build a mintlify site,
  MDX syntax, agent workflows). It does not search the per-repo customer sites in
  the catalog — verified with a real query: `search-mintlify --query "mise
  shell_alias"` returned zero results from `jdx/mise`.
- **An API key does not unlock this path.** Mintlify API keys are
  organization-scoped: they authenticate you only against docs owned by the same
  Mintlify organization as the key. A key cannot reach `jdx/mise`,
  `twpayne/chezmoi`, or any other org's content.

`mcp2cli` itself remains in active use for **other** MCP servers (`@github`,
`@docker` shorthands, or a customer-domain MCP such as `docs.anthropic.com/mcp`).
The ban is specifically on per-repo mintlify subpath URLs, not on `mcp2cli`.

## The `ctx7` correction (2026-07-23)

Step 3 of the chain used to say `ctx7` was "a skill-management CLI … **not** a
direct doc-fetcher", which routed every lookup through a skill wrapper that adds
nothing.

Verified against `ctx7 --help` (0.5.5, the `mise.toml` pin): the documented
commands are `login / logout / whoami / setup / remove / library / docs /
upgrade`. It **is** a direct doc-fetcher, called in two steps.

The subtlety worth keeping: the `skills` subcommands **still run**
(`ctx7 skills list` → rc=0) but are hidden from `--help` and deprecated —
*"Skill commands are deprecated and will stop working in the next major
release."* So do not build on them, **and do not treat their absence from
`--help` as proof they are gone.** A command missing from help output is not a
command that does not exist; that is a display bound, in the sense of
`probes-need-a-control-arm.md` rule 3.

## The docs-domain guessing trap (session 2026-04-09c)

Do **not** guess a project's docs domain. `containers.dev/llms.txt` → 404. The
devcontainer spec / CLI / features / images docs are all hosted on mintlify at
`www.mintlify.com/devcontainers/<repo>/`, not on `containers.dev`. Grep the
cache or the catalog to find the right URL before curling anything.

## The MCP-registration relaxation (2026-07-19)

The rule used to carry a hard ban, machine-enforced by a `no_mcp_registration`
hk step. That step has been **removed**; native registration is now a documented
*preference*, not a gate.

The cost that still justifies the preference: registering an MCP server natively
injects every tool's JSON schema into Claude's system prompt for **every**
conversation, forever — even conversations that never call the tool. So for a
server you would query rarely, `mcp2cli`'s process-spawn is strictly cheaper. If
a plugin's value depends on Claude selecting its tools natively and you will use
it often, register it and accept the schema cost.

## The MCP schema tax is deferred, and the rule's figure was 33× too high (2026-07-30)

The rule justified its lane-2 preference with a cost claim: a registered server
"injects **every** one of its tool schemas into the system prompt of **every**
conversation, forever". Sessions kept contradicting it — MCP tools arrive as a
**names-only** deferred list, and a `ToolSearch` is offered to load a schema. The
claim was carried unmeasured for months, so it got measured.

### Method

`scratchpad/mcp_schema_cost.py` speaks JSON-RPC over stdio to each server this
repo declares in `.mcp.json` (`initialize` → `notifications/initialized` →
`tools/list`) and reports two numbers from **the same response**:

- **loaded** — `json.dumps(tools)` compact: what the model carries if the schemas
  are injected eagerly.
- **names** — the comma-joined `mcp__<server>__<tool>` list: what the deferred
  presentation actually costs.

Reading both arms off one `tools/list` is the point — a ratio between two
differently-sourced numbers would not be comparable.

### Result

| server | tools | loaded B | names B | ratio |
|---|---:|---:|---:|---:|
| memory | 9 | 10,750 | 262 | 41.0× |
| filesystem | 14 | 12,973 | 467 | 27.8× |
| exa | 2 | 2,202 | 49 | 44.9× |
| **TOTAL** | **25** | **25,925** | **778** | **33.3×** |

At the conventional 4 B/token that is **~6,481 tokens if eager vs ~195 deferred**
— about **6,286 tokens per conversation** that the rule assumed were being spent
and are not.

### What this does and does not license

The prescription barely moves; only its *reason* does. Preferring a `curl` over a
registration is still right for lane 2 — a server adds a spawned process, a pin,
an auth path and a failure mode — but "permanent context spend" was doing
argumentative work it had not earned, and it was being used to refuse
registrations.

### Caveats, stated so the number is not over-read

1. **4 B/token is a convention, not a tokenizer run.** The ratio is exact; the
   token figures are estimates. JSON schema text is punctuation-dense and likely
   tokenizes *worse* than 4 B/token, which would make the eager side larger, not
   smaller.
2. **Scope is the 3 servers `.mcp.json` declares.** Plugin-bundled servers and the
   `MCP_DOCKER` gateway are excluded; the gateway is large enough that the #418
   doctor had to add `Server.repo_owned` to stop it emitting 32 findings, so a
   whole-host total would be much bigger on both sides of the ratio.
3. **Deferral is harness behaviour observed on one day**, not a documented
   guarantee. It may be conditional (tool count, model, settings) and may change.
   Re-run the script before relying on it.
4. ⚠️ **The mechanism description that ships with the deferred list did not
   reproduce.** It states that calling a deferred tool directly "will fail with
   `InputValidationError`". Two direct calls **succeeded** without any
   `ToolSearch` — `mcp__memory__read_graph` (no args, so a weak arm) and then
   `mcp__memory__search_nodes` with its required `query` (the real arm). So
   whatever the loading mechanism is, "it will fail" is not a reliable
   description of it, and this evidence does not claim to explain it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `docs/research/mintlify-catalog.md`, the validation log.

_Named in the extracted text but **not** resolved during this extraction (carried
over from the rule, not re-probed): `jdx/mise`, `twpayne/chezmoi`, and the
mintlify / Context7 endpoints above. The probe results are dated; re-run them
before relying on a negative._
