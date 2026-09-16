# codex SDLC team — pre-/clear session review (run 4e6f6a4d042745beae6619557c630b70)

> **PERSISTED VERBATIM. Self-report RECONCILED and ACCURATE** — the first
> time for this team. It claimed three specialists with their agent paths;
> the descendant session files show exactly those three:
>
> | claimed | observed `agent_role` | `agent_path` | nickname |
> |---|---|---|---|
> | sdlc-python-specialist | sdlc-python-specialist | /root/python_review | Bacon |
> | sdlc-config-specialist | sdlc-config-specialist | /root/config_review | Heisenberg |
> | sdlc-documentation-specialist | sdlc-documentation-specialist | /root/documentation_review | Epicurus |
>
> All three carry `parent_thread_id: 01a0a8da-6d39-74e3-a8fc-fe66f5505378`.
> Real router errors in this run: **0** (control arm: the same pattern
> matches **4** in the failed run `2c97f4bc…`).
>
> Coordinator-verified findings: F4 (devcontainer runtime pin 2.1.270 vs
> sources.toml 2.1.273) and F3 (`mise run lint` reaches hk via
> `lint.py:66`, evading the literal `hk run` regex) both CONFIRMED.

---

# Review outcome

PR #1145 fixes the immediate `--ephemeral` spawn blocker, and this review directly observed three real child session records. It does **not** finish issue #1142: settlement still trusts model-written Markdown instead of reconciling persisted child sessions, several documents still treat refuted runs as proof, and the earlier Claude pin work missed both a consumed field and the devcontainer runtime.

## Highest-priority findings

1. **P0 — Specialist self-report can still falsely settle as success.**

   [sdlc_team.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sdlc_team.py:238) still permits fallback to generalist work after spawn failure, requires a `Specialists spawned:` list, and records that list as `SELF_REPORT` around line 493. [test_sdlc_team.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_sdlc_team.py:306) accepts bare Markdown claims without descendant-session evidence.

   The current run proves persisted reconciliation is feasible: the three children each contain the dispatcher’s `parent_thread_id` and their actual role/path. The settlement path nevertheless does not consume those records.

   Mechanical fix: carry the Codex parent thread ID into settlement, enumerate children, compare observed roles against the claimed list, and fail closed on missing or extra agents. The negative arm must claim one specialist while providing zero child records.

2. **P1 — `4d91064`’s workflow policy loses setup/run ordering.**

   [workflow_claude_code.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/workflow_claude_code.py:181) stores `uses` and `run` commands separately. Its policy therefore accepts:

   ```yaml
   - run: hk run check --all
   - uses: ./.github/actions/setup-claude-code
   ```

   The specialist’s public-function probe returned `violation_emitted=False`. Preserve ordered step records and add a reversed-order fail arm.

3. **P1 — The workflow policy misses the repository’s own lint wrapper.**

   Its regex recognizes literal `hk run`, but `mise run lint` reaches hk through [lint.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/lint.py:64). A future workflow can use the preferred wrapper without Claude setup and evade the gate.

   Mechanically recognize registered wrappers or explicitly prohibit indirect hk invocation in workflows. Test both forms.

4. **P1 — The claimed “one Claude pin” excludes the devcontainer runtime.**

   [mise-runtime.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:63) declares `claude-code = "latest"`; its lock resolves `2.1.270`, while [sources.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:51) records `2.1.273`. [pin-parity.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/pin-parity.toml:90) covers neither image-runtime site.

   Either bring the image runtime into the ownership/parity contract or explicitly scope “sole pin” to CI/plugin validation and document the independent image pin.

5. **P1 — `d540ebc` introduces an untested fail-open for malformed workflows.**

   [workflow_claude_code.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/workflow_claude_code.py:248) silently skips files on YAML, Unicode, or OS errors. The commit says the failure should name the file; the implementation emits nothing and can return clean.

   There is no malformed/unreadable-file test. Emit a file-named violation or propagate the failure, with malformed, unreadable, and valid-workflow arms.

6. **P1 — V3/V4 still use refuted ephemeral runs as routing proof.**

   [codex-sdlc-subagent-team.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/specs/codex-sdlc-subagent-team.md:235) still concludes routing worked “in practice”; V4 generalizes the same evidence around line 254. The underlying report records only the model’s claim, not child JSONLs.

   Mark V3/V4 refuted or unverified until rerun with durable parent/child paths. This review’s observed children could become such a receipt, but no report was written under review-mode constraints.

7. **P1 — The original `45868dd` parity arm did not mutate the field CI consumes.**

   It coupled the URL tag and README, but not `sources.toml`’s `version` field. The concurrently added `8b92edd` is a fifth, omitted follow-up commit that fixes precisely this defect.

   Structured parity tests should independently mutate every consumed field. A sibling URL match is not evidence that the version reader is protected.

## Additional findings

- **P2 — Pin currency is skipped when host health fails.**  
  [claude_doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/claude_doctor.py:315) returns before reaching the repository pin check around line 383. Host health and tracked-pin currency are independent axes; aggregate both. Add a missing-host × stale-pin test.

- **P2 — The documented schema refresh cannot advance Claude.**  
  [schema_vendor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/schema_vendor.py:405) reuses the recorded version and its entry point discards arguments around line 521. Yet `sources.toml` says never to hand-edit and to use refresh. Provide an atomic `--tool/--version` bump interface with unchanged-on-error protection.

- **P2 — The composite action’s version assertion is substring-based.**  
  [action.yml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/actions/setup-claude-code/action.yml:55) accepts any output containing the pin, including `2.1.2730`. Parse and compare the version token exactly; add wrong-prefix/suffix arms.

- **P2 — The active design document contradicts implementation.**  
  [codex-sdlc-subagent-team.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/specs/codex-sdlc-subagent-team.md:3) says “NOT implemented,” line 78 requires impossible `mcp_servers` fields that the document later disclaims, and line 296 lists already-implemented decisions as unresolved. Split historical design from the current contract.

- **P2 — The loaded dispatcher retains the broad retry premise.**  
  [codex-sdlc-dispatcher.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/agents/codex-sdlc-dispatcher.toml:45) still says spawn attempts can fail and retry, while `d540ebc` narrowed the generated prompt. Define this policy once and test exact agreement.

- **P2 — Changed-file routing cannot find files that should have changed.**  
  The pin work did not touch `.devcontainer/mise-runtime*`, so path-only routing never selected the image specialist. Route from registered consumers/owners as well as changed paths.

- **P2 — #1142 must remain open or be split.**  
  [Issue #1142](https://github.com/ray-manaloto/dotfiles/issues/1142) still contains unresolved self-report reconciliation and no-network citation-integrity decisions. [PR #1145](https://github.com/ray-manaloto/dotfiles/pull/1145) resolves root cause and persistence only.

- **P3 — Evidence references are not fresh-session-resolvable.**  
  Commit messages cite `app-server.md:291` and `plugins-reference.md:506` without repository/corpus roots or immutable revisions. The spawn evidence also uses truncated IDs without durable paths.

- **P3 — The review spec uses topic-branch SHAs without merged-SHA mapping.**  
  `cb0c613`, `4d91064`, and `45868dd` are not current-history ancestors. The durable squash equivalents are `428a6ff` for #1128 and `813df4f` for #1143. Record both original and landed SHAs.

- **P3 — Smaller stale surfaces remain.**  
  `mise.toml` still describes installation as belonging to only the `ci.yml` lint job; a test comment still says Claude is host-pinned in mise; the new `schema-vendor pin` public CLI has no direct success/error test.

## Commit disposition

- `cb0c613`: the direct-PATH correction is sound, but its public pin CLI lacks direct coverage and the evidence did not establish the actual Ubuntu installation path.
- `4d91064`: central setup covers today’s two direct hk jobs, but ordering, wrapper recognition, and exact-version checking invalidate the broader prevention claim.
- `45868dd`: central pin reading is useful, but the original parity arm missed the consumed version field, doctor short-circuits pin currency, and the image runtime remains outside “one pin.”
- `d540ebc`: the `--ephemeral` diagnosis is correct and live spawning now works. Automatic provenance reconciliation, truthful partial-failure settlement, documentation cleanup, and the YAML fail-open remain.
- `8b92edd`: this concurrent fifth commit repairs the version/tag parity omission; it does not resolve the image-runtime ownership gap.

## Repeated patterns to prevent mechanically

- Derive actor identity from persisted records, never narrative output.
- Preserve order when the contract is sequential; sets of predicates are insufficient.
- Build parity from all consumers, including omitted files, not merely the changed-file list.
- Test independent health dimensions independently.
- Every behavior-bearing branch needs its own realistic mutation/fail arm.
- When evidence is refuted, search and disposition every claim derived from the same premise.
- Require durable evidence paths and original-to-landed SHA mappings in `/clear` handoffs.

## Review evidence and constraints

No repository gate, pytest, hk, lint, or verification task was run. No checkout or report file was written by this review.

The mandatory Graphify query was attempted first and returned direct `rc=1` because mise could not create temporary state in the read-only sandbox. Raw source inspection was then used as the documented fallback.

During review, another process moved the checkout from `d540ebc` to `8b92edd` and created untracked `docs/research/kb/reports/agents/history-miner-2026-09-16.md`. Those changes were preserved and were not produced by this dispatcher or its specialists.

Observed session evidence:

- Parent: `01a0a8da-6d39-74e3-a8fc-fe66f5505378`
- Python child: `01a0a8db-de4d-7c93-a96f-8d001939aecd`
- Config child: `01a0a8db-fbb1-7db3-8384-978b2e8cd6a1`
- Documentation child: `01a0a8dc-1ee0-7e10-912c-70a417e45218`

All three child JSONLs recorded the parent ID, agent path, and named role.

Two attempts to spawn `sdlc-workflows-specialist` returned `agent thread limit reached`, including after a specialist completed. This was not the specified `no thread with id` failure, so the no-history retry rule did not apply. I completed the workflow/action review directly and reported both failures. No image specialist was selected initially because none of the requested commits changed an image-owned path; that routing blind spot is itself reported above.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/documentation_review`

No other specialists were spawned.

