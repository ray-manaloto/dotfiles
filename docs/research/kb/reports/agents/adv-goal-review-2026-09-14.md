# adv-goal-review-2026-09-14 — hk currency `/goal` artifact review

**Agent:** codex-astra-advisor (read-only sandbox, xhigh reasoning, gpt-6-astra)
**Scope:** the `/goal` string at `/private/tmp/claude-501/…/scratchpad/goal-corrected.txt` (hk currency, 3,921/4,000 chars, 5 clauses)
**Status:** COMPLETE

---

## Scope correction (v1 → v2)

**v1 (first attempt):** Codex analyzed Phase 2 dependency-currency goal (6 clauses, #1053 blocker) instead of hk currency goal. Root cause: brief referenced both `docs/specs/goal-writing-and-phase2-dependency-currency.md` (which contains its own `/goal` example) AND the scratchpad artifact, creating ambiguous input. Codex reviewed the goal inside the spec.

**v2 (second attempt):** Corrected prompt with hk goal inlined verbatim (6,481 chars). Codex analyzed successfully, produced verdict with answers to all six questions.

**Status:** Scope mismatch resolved. Advisor can now proceed on the correct artifact.

---

## VERDICT: SHIP WITH EDITS

The goal is **sound but requires three substantive edits** to resolve internal conflicts and explicit Q&A findings. Replacement text below reduces scope to "latest 1.x + 2.0 handoff" (3,856 chars, leaving 144-char headroom).

### Deciding risk

Conflict between delivery PR completion and probing completion: the current goal requires "full hk 2.0 readiness" (clause 4's two-arm probe + edits) **and** landing three live PRs together (clause 2). The 2.0 probe's "stop for operator" instruction (clause 4) contradicts delivering finished PRs (clauses 3, 5). Narrowing scope to "1.x current + 2.0 blocker handoff" resolves this by decoupling the operator's decision from the session's delivery.

---

## Answers to the six questions

**Q1: Clause satisfiable without work?**
No single clause satisfies without doing work. Baseline evidence (clause 1) appropriately asks for new inventory; clause 1 also contradicts itself by demanding a "failing" #1079 gate when its current state is "pending". Inventory omits #1093. Codex recommends clarifying the state snapshot.

**Q2: Unsatisfiable or self-contradictory?**
YES — three conflicts found:
1. Clause 4's "stop for operator" (do not edit files) contradicts clauses 3 and 5 (land PRs, prove delivery)
2. Clause 2's "dryrun is grouping evidence only" but no actual grouped PR is produced before clause 3 tries to use it
3. Clause 5 demands "every PR touched" armed-or-merged, but clause 2 may supersede open PRs → closed non-merged PRs cannot satisfy

**Q3: Clause 4 probe genuinely two-armed?** ✓ YES
Codex ran hk 2.0.0 against this repo:
- **With `HK_PKL_BACKEND=pkl`:** rc=1, error: "HK_PKL_BACKEND no longer selects an evaluator in hk v2; remove it or set it to `pklr`."
- **With `env -u HK_PKL_BACKEND`:** rc=1, different error: "Reached Pkl evaluation, then failed fetching `hk@1.57.0.zip` under network restriction." (Codex ran in read-only sandbox)

The **pkl arm discriminates** (names the removal). The **unset arm passes the backend check** and fails later (different error class). Probe works. Codex notes: hk does invoke `mise env` for step environments; do not generalize this result beyond `validate`. Specify **`validate`** in the goal.

**Q4: `mise run lock-shared -- "hk"` strand risk?** ✓ YES, BLOCKED IF CONTAINER DOWN
`lock-shared` routes to `devcontainer exec` with no bring-up step. Missing container returns rc≠0. Codex examined `/python/src/dotfiles_setup/lock_shared.py:391` (routing), `:299` (subprocess) and verified no timeout bound on the `devcontainer exec` call. **Clause 3 REQUIRES a running container.** Codex recommends adding `mise run up` when needed and explicit failure reporting.

Also: the skill requires **BOTH `lock-shared` AND `lock-image`** for shared-tool changes. Current `.devcontainer/mise-system.lock` contains another hk entry. Clause 3 must run both.

**Q5: Budget (79 chars headroom)?**
Confirmed 3,921 chars. The replacement text (below) is 3,856 chars (144 headroom) — well within budget.

**Q6: Failure handling sufficient?**
The final sentence "if any clause could not be completed, print which one and captured output" is present but should explicitly state **UNMET**; reporting a blocker must not substitute for completion evidence.

---

## Concrete replacement text

**Old goal (3,921 chars):**
```
Make hk current and hk-2.0-ready across every pin site and every surface. Met only when all evidence below is PRINTED IN THIS TRANSCRIPT from commands actually run, with real captured exit codes and PR head SHAs matching what shipped; file existence, issue references, prose, mocks or self-authored receipts cannot satisfy any clause. [... 5 clauses as provided ...]
```

**New goal (3,856 chars, 144 chars headroom):**
```
Update all repository hk pins to the latest 1.x; diagnose hk 2.0 for operator handoff. Print upstream target resolution. Require actual command output PRINTED IN THIS TRANSCRIPT with captured exit codes and tested SHAs matching delivery PR heads. Existence, prose, mocks or receipts alone do not count. (1) Print baseline commit and read all hk pins directly: .config/mise/conf.d/shared.toml, hk entries in .config/mise/mise.lock and .devcontainer/mise-system.lock, and all 8 hk@ URLs in hk.pkl, hk-common.pkl and hk-image.pkl (hk-common.pkl has imports, no amends; pin-parity.toml [tools.hk]). Print mise run pin-parity and mise run lint with rc. Print the live hk PR inventory (include 1063, 1079, 1090, 1093), head SHAs and actual CI status/logs: pending if pending; failed gate/error text if failed, including 1063's lockfile error when present. (2) Land a renovate.json-only PR adding hk.pkl, hk-common.pkl and hk-image.pkl to packageRules[0].matchFileNames. Describe how grouping shared.toml with these build inputs collapses two cold builds into one. Print its diff, mise run ship rc=0 and PR-number/AUTO-MERGE output; prove state MERGED before relying on the rule in live Renovate. Print a regrouped Renovate PR file list containing shared.toml AND all three pkl files, or mise run renovate-dryrun output demonstrating that grouping under the changed config. A dryrun is grouping evidence only: an actual grouped update PR is still required by (3). Print each superseded PR's disposition and replacement PR number. (3) Fix the lock mismatch on the actual grouped update PR. lock-shared requires a running devcontainer on macOS; if down, run mise run up and print rc/output; failure leaves this clause blocked. Bound container/lock commands; timeouts are BLOCKED, with output/rc. Print mise run lock-shared -- "hk" and mise run lock-image with rc=0, coverage summaries and resulting lock diffs at the target version, pushed to that PR. At its final clean head print git rev-parse HEAD, git status --porcelain, final pin values, mise run pin-parity, mise run lint, uv run --project python pytest tests/ -q and mise run verify with rc=0 and passing summaries, zero failures/errors and failed contracts. (4) MANDATORY probe even without a 2.0 bump: resolve and print hk 2.0's absolute path/version. Run that binary's validate against this repo's config twice, with HK_PKL_BACKEND=pkl and with env -u HK_PKL_BACKEND; set HK_CACHE=0 in both; keep HK_MISE and other inputs identical. Do not launch hk via mise run/exec: mise re-injects the variable from ~/.config/mise/config.toml. Print commands, outputs, captured rc values and proof of absence in the process that execs the unset arm. Discrimination means the pkl arm emits the removed-backend/replacement error and the unset arm passes that check; report any later failure separately, never as 2.0 readiness. Identical/shared unrelated failures are NON-DISCRIMINATING, blocker unconfirmed. Missing/skipped arms, unavailable binaries and timeouts do not count; report non-reproduction as such, never as cleared. Do not edit files outside this repository. If confirmed, print the exact user-config edit for the operator; this handoff does not prove remediation or excuse unfinished clauses. (5) For every touched PR print gh pr view -R ray-manaloto/dotfiles <n> --json number,url,headRefOid,files,state,autoMergeRequest. Retained delivery PRs must be MERGED or have non-null autoMergeRequest (the rule PR must be MERGED); superseded PRs may be CLOSED with their replacement identified. Match tested SHAs to delivery heads. ship rc=0 means ARMED, not merged. For each cold base build print its run ID and gh run view --json headSha,status,conclusion; unfinished is pending. Any unmet clause must be named with captured blocking output/rc: the goal remains UNMET, never satisfied by reporting the blocker.
```

**Changes:**
1. **Scope narrowed:** "latest 1.x; diagnose 2.0 for handoff" (removes "2.0-ready" delivery requirement)
2. **Clause 1:** Clarified state reporting (pending vs failed, added #1093)
3. **Clause 3:** Added container bring-up (`mise run up`), timeout bounds, explicit `lock-image` requirement
4. **Clause 4:** Changed to "MANDATORY probe even without a 2.0 bump" (no proof-of-fix requirement), specified `validate` verb, clarified that later failure is separate from backend check
5. **Clause 5:** Tightened PR state language, added clarification that `ship rc=0` is ARMED (not merged), required explicit "UNMET" statement for blockers

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — goal artifact, PRs #1063/#1079/#1090/#1093, files `.config/mise/conf.d/shared.toml`, `.devcontainer/mise-system.lock`, `hk.pkl`, `hk-common.pkl`, `hk-image.pkl`, `renovate.json`
- [jdx/hk](https://github.com/jdx/hk) — hk 2.0.0 validation probe (real invocation, `validate` subcommand)
