@@ -333,16 +333,16 @@
 [[invariants]]
 id = "do-not.danger-full-access"
 kind = "numbered"
-headline = "Do NOT run a repository lane at `--sandbox danger-full-access`."
+headline = "Do NOT run an ADVISORY or REVIEW lane above `read-only`; implementer lanes may run at `danger-full-access` (Ray, 2026-10-03)."
 enforced_by = []
 current_surface = "prose-only"
 disposition = "function-hook"
 evidence = "measured-this-session"
-rationale = "Control-armed zero - and #767 records 13 codex sessions that DID run at danger-full-access. The violation is measured, the enforcement absent, and codex-lane existing does not close it."
+rationale = "Ray's 2026-10-03 KB#863 /grilling ruling splits by lane type: implementers (kb-codex --write) may use danger-full-access; advisory and review lanes must stay read-only. The accepted risk is hook planting in writable .codex/ or .git/hooks/ while exec lanes bypass hook trust; reviews require an explicit sandbox_mode=read-only override. This row remains prose-only pending enforcement."
 [invariants.locator]
 anchor = "do-not.danger-full-access"
 reviewed_ordinal = 13
-reviewed_digest = "ae5405077906b0e5"
+reviewed_digest = "cc2a446f456d9510"
 
 
 # --- REGISTRATIONS ---------------------------------------------------------

[35m[3mcodex[0m[0m
Updated only [do-not.md #13](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base.worktrees/do-not-13/.claude/rules/do-not.md:166) and its [inventory entry](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base.worktrees/do-not-13/docs/guards/inventory.toml:334). The rewrite preserves the anchor, states the lane split and accepted hook risk, and replaces stale source citations. Inventory changes are limited to headline, rationale, and the repository-generated digest `cc2a446f456d9510`.

| Premise | Result and evidence |
|---|---|
| P1 | **CONFIRMED** — baseline `do-not.md:166-174`, also checked against `origin/main` |
| P2 | **CONFIRMED** — baseline `inventory.toml:334-345`, digest `ae5405077906b0e5` |
| P3 | **CONFIRMED** — unconditional exec hook-trust bypass at [codex_run.py:117](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base.worktrees/do-not-13/python/src/kb_setup/codex_run.py:117) |
| P4 | **CONFIRMED** — review sandbox override at [codex_run.py:515](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base.worktrees/do-not-13/python/src/kb_setup/codex_run.py:515) |

For `uv run --project python pytest tests/test_guard_inventory.py -q`:

| Arm | Real result |
|---|---|
| Updated rule | `EXIT=0` |
| Anchor temporarily deleted | `EXIT=1` — expected `ORPHAN` finding |
| Anchor restored | `EXIT=0` |

Both `git diff --check` runs returned `EXIT=0`. Lint and broader gates were deferred under the coordinator’s override. No commit, push, or PR was created.

The probe artifact tested `.git/config-probe`, rather than `.git/config`; the rewrite uses that actual target. The named dotfiles report was absent from the specified branch, so I verified the [original job artifact](/Users/rmanaloto/.claude/jobs/f4b75d61/tmp/proposals-kb-codex-sandbox-posture-2026-10-03-codex.md) and cited the [KB#863 ruling](https://github.com/ray-manaloto/knowledge-base/issues/863#issuecomment-5974896211).

Remaining command receipts:

| Command / inspection | Result |
|---|---|
| `kb-query` | `EXIT=2` — graph missing; source fallback used |
| Research schema search including absent `research_last30days.py` | `EXIT=2` |
| Target inspection ending with the evidence-directory search | `EXIT=1` — no convention found |
| Dotfiles `git show` for the report | `EXIT=128` — path absent |
| Clone `git describe --tags --exact-match` | `EXIT=128` — no exact tag |
| Refresh search including absent `python/pyproject.toml` | `EXIT=2` |
| Strict research fanout | `EXIT=1` |
| Manifest inspection/validator invocation | `EXIT=0`, validation returned **false** |
| All other executed inspection, digest, status, and diff commands | `EXIT=0` |

The initial Python and `gtimeout` wrapper requests were blocked before execution and have no process rc. Successful inspection batches also printed missing-file diagnostics for the worktree’s `permissions.rs` and `docs/guards/README.md`; canonical source and the repository API supplied the needed evidence.

**RESEARCH INCOMPLETE:** the mandatory [receipt](/Users/rmanaloto/.codex/research-coverage/01a10443-5f10-76c2-9215-ff0be0704e6d/01a10443-6224-7152-b391-7d3f8a1128db/manifest.json) records Firecrawl search failing with `exited 1: Error: Request failed with status code 402 |`. GitHub, Exa, Context7, Firecrawl developer, and Last30Days completed. Routes ran through `fnox`, `mise`, `uv`, `gh`, Exa HTTP, `ctx7`, Firecrawl HTTP/CLI, and the Last30Days plugin script. Graphify and Firecrawl skills were applied; orchestrator-routing was read as reference.

Proposed commit: `docs(do-not): #13 split sandbox by lane type (Ray 2026-10-03, KB#863)`.

