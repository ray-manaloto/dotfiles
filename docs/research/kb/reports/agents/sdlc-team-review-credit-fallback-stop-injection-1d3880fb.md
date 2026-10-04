**Review verdict: changes required. N2 is confirmed and must be fixed before acceptance. N1 is also confirmed; fixing its producer alone leaves an acceptance gap in receipt validation.**

Reviewed `636dd29708f61c3cd8b937d195f18f41dcc56616`. All three specialists completed. No repository gates, report writes, checkout modifications, commits, or live provider calls occurred. Final status checks returned **0** and confirmed both checkouts unchanged.

References below use:

- **fanout**: [research_fanout.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/credit-fallback/python/src/dotfiles_setup/research_fanout.py)
- **gate**: [codex-research-gate.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/credit-fallback/scripts/codex-research-gate.py)
- **workflow**: [research-sweep-run.js](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/credit-fallback/.claude/workflows/research-sweep-run.js)

### Confirmed findings

| Finding | Evidence and controlled reproduction |
|---|---|
| **N2: provider diagnostics enter Stop `reason`.** | Primary diagnostics at `fanout:1393–1399` and fallback bodies at `1433–1437` enter `_provisional_line()` at `1977–2002`, then the block reason at `gate:123–130`. The actual hook CLI returned `decision: block` containing both planted diagnostic strings verbatim. Benign diagnostics also blocked; an already-named answer and `stop_hook_active: true` each returned `{}`. |
| **N1: credit wording masks a successful-transport shape failure.** | `fanout:986–996` identifies the invalid response shape, but `1428–1437` searches its entire body without excluding 2xx responses. A Serper HTTP 200 body containing `knowledgeGraph.description: "How to handle Not enough credits errors"` became `skipped`, with strict validation **true**. The same shape containing ordinary wording remained `error`, with validation **false**. |
| **N1 consumer gap: fallback skip causes are not rederived.** | `fanout:2053–2082` checks routes and evidence hashes; `2120–2128` trusts fallback status labels without reclassifying their evidence. Relabeling the ordinary shape-error receipt and adjusting its primary binding made validation pass while preserving fallback bytes and hash. A producer-only amendment therefore leaves old or relabeled receipts acceptable. |

The locally mirrored, official-authored [hook documentation](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/hooks.md:923) says a Stop block reason becomes a new user-role continuation prompt. Its recorded document hash matched; its snapshot dates to July 2026. A second local mirror agrees. **The review reproduced emitted hook JSON, not installed Codex continuation behavior or model obedience.**

### Injection-path table

These are the identified paths within the reviewed research workflow. Conditional artifact reads and downstream propagation are distinguished from direct prompt insertion.

| Path | File:line evidence | Exposure |
|---|---|---|
| Credit diagnostics → provisional Stop reason | `fanout:1393–1399,1433–1437,1977–2002,2207–2226` → `gate:123–130` | Direct continuation channel under the documented contract. |
| Failed-receipt Stop reason | `fanout:1857–1878,1940–1956,2020–2216` → `gate:133–154` | Current wording uses fixed validation errors and validated source names; raw provider reasons are excluded. |
| Incomplete `systemMessage` | `gate:135–141`; hook docs `405–423` | Documented UI/event-stream warning, containing fixed failure wording here. No direct model-instruction exposure established. |
| UserPromptSubmit `additionalContext` | `gate:80–105`; hook docs `837–849` | Developer context, but no provider bytes: fixed policy, path, and validated identifiers. Stop `additionalContext` support was not established. |
| `last_assistant_message` matching | `gate:109–122` | No diagnostic reflection. Provider-derived quoted tokens can satisfy this presence check; it does not prove substantive disclosure. |
| Manifest diagnostics → copied `PROBE-JSON` | `fanout:2491–2493,2911–2918` → `workflow:180–186` | Visible to the copying agent and subsequently accepted as JSON. Encoding preserves instruction text. |
| Copied provisional strings → synthesis | `workflow:635–640,737,749` | Direct prompt insertion beneath instructions to name provisional routes. |
| Mirror primary diagnostic → synthesis | `fanout:2606–2610,2634–2640` → `workflow:498–499,638,747–749` | Provider failure text enters synthesis independently of the hook. |
| Ordinary fanout errors → dependency gaps | `fanout:699–704,1838–1850,2486,2508–2513` → `workflow:484–485,746,750` | Diagnostics enter tool output, artifacts, and synthesis gaps. |
| Mirror failures / redirect metadata → prompts | `fanout:2554–2556,2610,2648` → `workflow:497–503,679,747–748` | Failure text or returned final URLs enter reader/synthesis prompts. Webclaw nonzero stderr itself becomes a fixed rc message at `fanout:2528–2532`. |
| CLI summaries / strict result | `fanout:2923–2939,2986–2989` | Provider-bearing stdout becomes model-visible when consumed as tool output. |
| Mirror README diagnostics | `fanout:2704–2713,2742–2748` | Conditional exposure when the persisted README is read. |
| Retrieved results and documents → readers / claims | `fanout:571–585,1838–1850` → `workflow:616–626,657–703,741–742` | Intended intake of untrusted research evidence. |
| Derived prose → subsequent agents | `workflow:773–774,801,831–834,321–337,354–359` | Conditional propagation through refutation, adjudication, reconciliation, retrospect, and proposals. |
| Internal write-error stderr | `fanout:2906–2909,2981–2984` | Fixed exception-type diagnostics; no raw provider text identified. |

**Validated source/route fields are sufficient for the provisional Stop reason.** Exact source identities are enforced at `fanout:2185–2195`; allowed winning routes at `2026–2029`; attempt routes at `2053–2059`. Entries are constructed after validation at `2197–2211`. Invalid-source and invalid-route controls failed closed without echoing their sentinels.

That guarantee does not extend to the workflow probe. An isolated public `--probe-out --fanout-manifest` probe accepted both benign and forged source/route/diagnostic strings, **rc=0**. This establishes the weaker manifest/copied-line boundary; it does **not** establish that an honest provider can rename generated source constants.

### Fix proposals

**N2 — construct the continuation from validated identifiers.**

Use `verdict.provisional_entries` and fixed explanatory text. Render each validated source and optional `via <validated route>`. Exclude descriptive provisional lines, primary/attempt reasons, bodies, and stderr. Preserve the one-block, null-answer, and already-continued behavior.

- **PRO:** closes the reproduced channel using existing validation and preserves required disclosure.
- **CON:** detailed diagnostics leave the continuation; workflow and tool-output exposures remain.

For the sibling workflow paths, export bounded structured provenance and finite failure codes, validate them again at the copied-JSON consumer, and keep detailed diagnostics in evidence artifacts. Remove raw explanations from generated provenance and gap instructions. Explicit data-only guidance for retrieved content provides defense in depth, but does not replace that projection.

**N1 — correct classification and receipt validation together.**

Restrict fallback credit-phrase recognition to non-2xx provider failures, preferably recognized top-level `message`/`error` fields. Successful-transport JSON or shape failures must remain errors. Preserve genuine HTTP 402 and qualifying quota-429 behavior.

Rederive evidenced fallback credit skips during strict validation. Persist and bind the transport information needed for that decision; reject historical evidence that cannot establish it. Keep missing-key prerequisite skips distinct from provider credit determinations.

- **PRO:** prevents incidental content from masking failures and rejects stale classifications.
- **CON:** requires receipt compatibility decisions; genuine exhaustion encoded in 2xx responses would fail closed until a verified provider-specific rule exists.

### Tests that must pin the fixes

All tests should use isolated state and public interfaces. These tests and mutations are **proposed, not executed**.

| Test and control arms | Realistic mutation that must fail |
|---|---|
| Actual hook CLI with valid receipts containing separate primary/fallback sentinels: block, retain required identifiers, exclude sentinels. Changing diagnostic prose must leave the reason identical. | Restore `"; ".join(verdict.provisional)` or append a diagnostic. |
| Substituted/skipped receipts; named, unnamed, null, continued, and invalid-name controls. | Remove block enforcement, required tokens, source validation, or route validation. |
| Both fallback providers: malformed 2xx bodies with/without credit wording remain errors; valid results mentioning credits remain successful; genuine failed credit responses remain provisional. | Restore unrestricted whole-body/any-status matching. |
| Hash-valid historical receipt with erroneous fallback skip labels is rejected; genuine credit and missing-key controls discriminate. | Remove reader reclassification while retaining the producer fix. |
| Public probe projection and captured workflow prompts exclude diagnostic sentinels; reject invalid names/codes and excessive rows. | Restore `_provisional_line()` or each direct diagnostic interpolation. |
| `PROVISIONAL exactly` cannot acknowledge an `exa` source; `PROVISIONAL exa` can. | Delete token lookarounds. |

### N3–N5 interactions

- **N3:** installed ctx7 source confirms `HTTP error ${response.status}` rendering; the target classifier misses it. Live occurrence remains unverified. Avoid restoring broad bare-number matching.
- **N4:** safe Stop projection removes echoed query text from that continuation, but does not repair false credit classification. Parse actual CLI errors separately from echoed queries, including multiline queries.
- **N5:** character caps bound size, not authority. Pin the token-boundary regression while touching the hook. Retain independent cap and SerpApi empty-state tests; the previous mutation results were not rerun.

**Recommendation:** require N2’s validated continuation construction and N1’s producer-plus-consumer correction before acceptance. Include workflow diagnostic projection in the implementation scope, or explicitly retain those exposures as unresolved; a hook-only amendment cannot establish workflow-wide protection.

### Execution record

| Specialist | Normal gate | Review execution |
|---|---|---|
| Python | pytest | **Not run.** Corrected isolated behavioral probe **rc=0**. Initial fixture probe **rc=1** because relocated evidence bindings were invalid; corrected fixture passed. |
| Config | `mise run lint` | **Not run.** Isolated public probe **rc=0**. |
| Documentation | `mise run lint-docs` | **Not run.** Read-only documentation and installed-source inspection. |

Single-source `main()` fixture calls returned **1**; strict-five conclusions came from complete fixtures and `strict_five_verdict()`, not those subset exit codes. Read attempts using nonexistent abbreviated roster filenames or `scripts/AGENTS.md` returned **1**; corrected reads succeeded. An alternative ctx7-path read returned **2**, followed by a successful exact-file read.

Actual routes: `codex-sdlc-team` skill, native specialist spawning, Git, `rg`, file reads, SHA256 inspection, and offline `uv`/Python probes. No external apps, Exa, Firecrawl, Last30Days, Context7 API, GitHub search, or network fetch ran. No contradiction required stopping the review.

## GitHub repos touched

Local read-only inspection only:

- `ray-manaloto/dotfiles` — target code, tests, instructions, and prior review.
- `ray-manaloto/knowledge-base` — documentation manifests and mirrors.
- `mrkhachaturov/agent-harness-docs` — mirrored hook documentation.
- `chenrui333/codex-docs` — corroborating hook documentation.
- `upstash/context7` — installed ctx7 source.

Specialists spawned:

No others were spawned.

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/documentation_review`

